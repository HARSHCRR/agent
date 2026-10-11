import json
import logging
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from config import GEMINI_API_KEY, GEMINI_MODEL, THINKING_LEVEL_JUDGE
from models import BriefingPack, CaseOutput, JudgeOutput

logger = logging.getLogger(__name__)

# =====================================================================
# 1. CITATION VERIFICATION FIREWALL
# =====================================================================

def validate_citations(case: CaseOutput, valid_ids: Set[str]) -> Tuple[bool, List[str]]:
    """
    Programmatically verifies that every evidence_id cited in the analyst case
    strictly exists in the briefing pack valid ID set.
    Returns (is_valid, list_of_invalid_ids).
    """
    invalid_ids = []
    for driver in case.key_drivers:
        for eid in driver.evidence_ids:
            clean_eid = eid.strip().upper()
            if clean_eid not in valid_ids:
                invalid_ids.append(eid)
    return len(invalid_ids) == 0, invalid_ids


def verify_cases_with_retry(
    pack: BriefingPack,
    bull_case: CaseOutput,
    bear_case: CaseOutput,
    api_key: Optional[str] = None,
) -> Tuple[Optional[CaseOutput], Optional[CaseOutput], bool]:
    """
    Validates both analyst cases against the briefing pack.
    If an analyst hallucinated citations, attempts exactly 1 retry call.
    If validation still fails after retry, returns (None, None, False) to trigger safe fallback.
    """
    from analysts import generate_case

    valid_ids = pack.get_valid_evidence_ids()

    # Check Bull case
    bull_valid, bull_invalids = validate_citations(bull_case, valid_ids)
    if not bull_valid:
        logger.warning(
            f"Bull case failed citation check on IDs: {bull_invalids}. Initiating 1-retry loop..."
        )
        bull_case = generate_case("BULL", pack, api_key=api_key)
        bull_valid, bull_invalids = validate_citations(bull_case, valid_ids)
        if not bull_valid:
            logger.error(
                f"Bull case failed citation check again on: {bull_invalids}."
            )
            return None, None, False

    # Check Bear case
    bear_valid, bear_invalids = validate_citations(bear_case, valid_ids)
    if not bear_valid:
        logger.warning(
            f"Bear case failed citation check on IDs: {bear_invalids}. Initiating 1-retry loop..."
        )
        bear_case = generate_case("BEAR", pack, api_key=api_key)
        bear_valid, bear_invalids = validate_citations(bear_case, valid_ids)
        if not bear_valid:
            logger.error(
                f"Bear case failed citation check again on: {bear_invalids}."
            )
            return None, None, False

    return bull_case, bear_case, True


# =====================================================================
# 2. BLIND ANONYMIZER & ORDER SHUFFLER
# =====================================================================

def anonymize_and_randomize(
    bull_case: CaseOutput, bear_case: CaseOutput
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, str]]:
    """
    Strips BULL and BEAR labels and randomizes the order (Case X vs Case Y)
    with a 50/50 coin flip. This prevents position bias in the LLM judge.
    Returns: (case_x_dict, case_y_dict, mapping)
    where mapping looks like: {"X": "BULL", "Y": "BEAR"} or {"X": "BEAR", "Y": "BULL"}.
    """
    bull_dict = bull_case.model_dump()
    bear_dict = bear_case.model_dump()
    bull_dict.pop("side", None)
    bear_dict.pop("side", None)

    if random.choice([True, False]):
        case_x = bull_dict
        case_y = bear_dict
        mapping = {"X": "BULL", "Y": "BEAR"}
    else:
        case_x = bear_dict
        case_y = bull_dict
        mapping = {"X": "BEAR", "Y": "BULL"}

    return case_x, case_y, mapping


# =====================================================================
# 3. BLIND JUDGE PROMPT & EXECUTION (Gemini 3.8 Flash, Medium Thinking)
# =====================================================================

JUDGE_SYSTEM_PROMPT = """You are a neutral institutional risk reviewer. Two analysts wrote opposing cases about NAS100 (Nasdaq 100) for today's US cash session. You also see the original briefing pack. Decide whether the evidence points to bullish, bearish, or sideways for today.

Rules:
- Judge evidence quality, not rhetoric or confidence of tone.
- Check each claim against the briefing pack. Ignore or penalize any claim that is not supported by the cited evidence IDs.
- Prefer "sideways" when the evidence is mixed, thin, or dominated by unresolved scheduled events (for example, CPI or FOMC in the first hours).
- Use "high" confidence only when one case is clearly better supported and the other case's counterpoints are weak. Most days should be "low" or "medium".
- Do not give trade advice, entries, stops, or price targets.
- If [DATA_STATUS] shows failed sources, lower confidence and say so.
- Output JSON only, matching the required schema.
"""

JUDGE_USER_PROMPT = """BRIEFING PACK:
{pack_text}

CASE X:
{case_x_json}

CASE Y:
{case_y_json}

Deliver your neutral verdict now in strict JSON format.
"""


def evaluate_cases_blind(
    pack: BriefingPack,
    case_x: Dict[str, Any],
    case_y: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> JudgeOutput:
    """
    Calls Gemini 3.8 Flash with thinking_level='medium' and temperature=0.1
    to evaluate Case X vs Case Y blindly.
    """
    key = api_key or GEMINI_API_KEY
    model = model_name or GEMINI_MODEL
    pack_text = pack.to_briefing_text()
    user_prompt = JUDGE_USER_PROMPT.format(
        pack_text=pack_text,
        case_x_json=json.dumps(case_x, indent=2),
        case_y_json=json.dumps(case_y, indent=2),
    )

    if not key or key.strip() == "" or key == "your_gemini_api_key_here":
        logger.warning("No GEMINI_API_KEY found. Generating simulated neutral judge verdict.")
        return _generate_mock_judge(pack, case_x, case_y)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        config = types.GenerateContentConfig(
            system_instruction=JUDGE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=JudgeOutput,
            temperature=0.1,
            thinking_config=types.ThinkingConfig(
                thinking_budget=2048
            ) if "flash" in model.lower() else None,
        )

        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
        )
        return JudgeOutput.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"Error calling Gemini for Judge: {e}. Falling back to simulation.")
        return _generate_mock_judge(pack, case_x, case_y)


# =====================================================================
# 4. UNBLINDER & RESULT UNIFICATION
# =====================================================================

def unblind_verdict(judge_output: JudgeOutput, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Maps winning_case (X, Y, neither) back to actual market bias (BULL, BEAR, NEITHER).
    Returns the complete unblinded decision record.
    """
    winning_case = judge_output.winning_case
    if winning_case in ("X", "Y"):
        actual_winner = mapping.get(winning_case, "UNKNOWN")
    else:
        actual_winner = "NEITHER"

    return {
        "verdict": judge_output.verdict,
        "confidence": judge_output.confidence,
        "blind_winner": winning_case,
        "unblinded_winner": actual_winner,
        "mapping": mapping,
        "deciding_factors": judge_output.deciding_factors,
        "reasoning": judge_output.reasoning,
        "events_to_watch": judge_output.events_to_watch,
        "caveats": judge_output.caveats,
    }


def _generate_mock_judge(
    pack: BriefingPack, case_x: Dict[str, Any], case_y: Dict[str, Any]
) -> JudgeOutput:
    """Simulated neutral evaluation for testing/demonstrations."""
    has_morning_events = any(e.time_et <= "10:00" for e in pack.events_today)
    if has_morning_events:
        verdict = "sideways"
        confidence = "low"
        winner = "neither"
        reasoning = (
            "Evidence is balanced ahead of critical early macro releases. "
            "High catalyst uncertainty limits directional conviction into cash open."
        )
    else:
        verdict = "bullish"
        confidence = "medium"
        winner = "X"
        reasoning = (
            "Technical consolidation above key support and low volatility index "
            "provide slightly superior evidence support over macro yield concerns."
        )

    return JudgeOutput(
        verdict=verdict,
        confidence=confidence,
        winning_case=winner,
        deciding_factors=[
            "Morning economic release catalyst uncertainty",
            "Compression in VIX vs yield drag tension",
        ],
        reasoning=reasoning,
        events_to_watch=[e.event for e in pack.events_today[:2]] or ["Cash open price action"],
        caveats="Pending macro prints could trigger immediate invalidation across all key drivers.",
    )


if __name__ == "__main__":
    from collector import build_pack
    from analysts import run_dual_analysts

    print("Testing Step 4: Citation Firewall & Blind Judge Arbitration...")
    test_pack = build_pack()
    bull, bear = run_dual_analysts(test_pack)

    b_case, r_case, valid = verify_cases_with_retry(test_pack, bull, bear)
    assert valid, "Cases must be valid"
    print("Citation Firewall passed! All evidence IDs verified.")

    cx, cy, mapping = anonymize_and_randomize(b_case, r_case)
    print(f"Blind Mapping established: X={mapping.get('X')}, Y={mapping.get('Y')}")

    judge_res = evaluate_cases_blind(test_pack, cx, cy)
    print("\n--- JUDGE ARBITRATION OUTPUT ---")
    print(json.dumps(judge_res.model_dump(), indent=2))

    final_record = unblind_verdict(judge_res, mapping)
    print("\n--- UNBLINDED RESULT ---")
    print(f"Verdict: {final_record.get('verdict').upper()}")
    print(f"Confidence: {final_record.get('confidence').upper()}")
    print(f"Winning Bias: {final_record.get('unblinded_winner')}")
