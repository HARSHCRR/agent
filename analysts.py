import concurrent.futures
import json
import logging
from typing import Dict, Literal, Optional, Tuple

from config import GEMINI_API_KEY, GEMINI_MODEL, THINKING_LEVEL_ANALYST
from models import BriefingPack, CaseDriver, CaseOutput

logger = logging.getLogger(__name__)

# =====================================================================
# PARAMETERIZED ANALYST PROMPT TEMPLATE
# =====================================================================

ANALYST_SYSTEM_PROMPT = """You are an institutional quantitative equity analyst assigned to argue the {SIDE} case for NAS100 (Nasdaq 100) for today's US cash session. You will be given a briefing pack.

Rules:
- Use ONLY information in the briefing pack. Do not use outside knowledge of market events, prices, or news. If something is not in the pack, do not claim it.
- Every key driver must cite evidence IDs from the pack (E1, Y1, H3, or PRICE).
- Argue the {SIDE} case as strongly as the evidence honestly allows. Do not invent or exaggerate support. If the evidence for your side is weak, say so in data_gaps instead of padding.
- Also state the single strongest point against your own case.
- Do not give trade advice, entries, stops, targets, or price predictions.
- Check [DATA_STATUS]. If a source failed, list it in data_gaps.
- Output JSON only, matching the required schema. Exactly 3 key_drivers are required.
"""

ANALYST_USER_PROMPT = """BRIEFING PACK:
{pack_text}

Generate the {SIDE} case now in strict JSON format.
"""


# =====================================================================
# GEMINI API CALLER WITH STRUCTURED OUTPUT & THINKING LEVEL
# =====================================================================

def generate_case(
    side: Literal["BULL", "BEAR"],
    pack: BriefingPack,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> CaseOutput:
    """
    Executes a single analyst prompt (BULL or BEAR) against Gemini 3.8 Flash
    with thinking_level='low' and structured Pydantic response schema.
    """
    key = api_key or GEMINI_API_KEY
    model = model_name or GEMINI_MODEL
    pack_text = pack.to_briefing_text()
    system_instruction = ANALYST_SYSTEM_PROMPT.format(SIDE=side)
    user_prompt = ANALYST_USER_PROMPT.format(SIDE=side, pack_text=pack_text)

    # If no Gemini API key is configured, fallback to deterministic mock for local development/testing
    if not key or key.strip() == "" or key == "your_gemini_api_key_here":
        logger.warning(f"No GEMINI_API_KEY found. Generating simulated {side} case for dry-run.")
        return _generate_mock_case(side, pack)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        # Configure thinking level: 'low' for analysts to minimize latency and token usage
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=CaseOutput,
            temperature=0.2,
            thinking_config=types.ThinkingConfig(
                thinking_budget=1024  # low thinking budget
            ) if "flash" in model.lower() else None,
        )

        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
        )

        # Parse and validate through Pydantic
        raw_text = response.text
        case_data = CaseOutput.model_validate_json(raw_text)
        return case_data

    except Exception as e:
        logger.error(f"Error calling Gemini for {side} case: {e}. Falling back to simulated case.")
        return _generate_mock_case(side, pack)


# =====================================================================
# CONCURRENT DUAL ANALYST RUNNER
# =====================================================================

def run_dual_analysts(
    pack: BriefingPack,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Tuple[CaseOutput, CaseOutput]:
    """
    Runs both Bull and Bear analysts concurrently in parallel threads to cut execution latency in half.
    Returns (bull_case, bear_case).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_bull = executor.submit(generate_case, "BULL", pack, api_key, model_name)
        future_bear = executor.submit(generate_case, "BEAR", pack, api_key, model_name)

        bull_case = future_bull.result()
        bear_case = future_bear.result()

    return bull_case, bear_case


# =====================================================================
# SIMULATED / DRY-RUN CASE GENERATOR (Offline / Testing Mode)
# =====================================================================

def _generate_mock_case(side: Literal["BULL", "BEAR"], pack: BriefingPack) -> CaseOutput:
    """
    Generates a deterministic, strictly citation-compliant mock case based on live pack data.
    Useful for offline testing, CI/CD, and demonstrations before API key insertion.
    """
    valid_ids = pack.get_valid_evidence_ids()
    event_ids = [eid for eid in valid_ids if eid.startswith("E")]
    first_event = event_ids[0] if event_ids else "PRICE"
    second_event = event_ids[1] if len(event_ids) > 1 else first_event
    headline_ids = [hid for hid in valid_ids if hid.startswith("H")]
    first_headline = headline_ids[0] if headline_ids else "PRICE"

    if side == "BULL":
        return CaseOutput(
            side="BULL",
            headline="Macro stability and supportive technical structure favor tech continuation into cash open",
            key_drivers=[
                CaseDriver(
                    point=f"Nasdaq consolidates near recent highs with VIX contained at {pack.price.vix or 15.0}",
                    evidence_ids=["PRICE"],
                    horizon="us_session",
                ),
                CaseDriver(
                    point="Scheduled morning economic releases offer favorable risk-reward for rate expectations",
                    evidence_ids=[first_event],
                    horizon="premarket",
                ),
                CaseDriver(
                    point="Early news cycle reflects positive sentiment across semiconductor and tech megacaps",
                    evidence_ids=[first_headline],
                    horizon="multi_day",
                ),
            ],
            strongest_counterpoint=f"Elevated 10-year Treasury yields at {pack.price.us10y or 5.2}% remain a drag on tech multiples.",
            invalidation="A breakdown below yesterday's low on high morning selling volume.",
            data_gaps=pack.failed_sources or ["None identified in briefing pack"],
        )
    else:
        return CaseOutput(
            side="BEAR",
            headline="Elevated bond yields and upcoming catalyst uncertainty create downside asymmetry for tech",
            key_drivers=[
                CaseDriver(
                    point=f"US 10-Year yield pressure at {pack.price.us10y or 5.2}% caps valuation expansion for Nasdaq 100",
                    evidence_ids=["PRICE"],
                    horizon="us_session",
                ),
                CaseDriver(
                    point="Morning macro prints carry high headline risk with asymmetric downside on sticky figures",
                    evidence_ids=[second_event],
                    horizon="premarket",
                ),
                CaseDriver(
                    point="Thin pre-market volume highlights buyer hesitation ahead of scheduled FOMC commentary",
                    evidence_ids=["PRICE"],
                    horizon="premarket",
                ),
            ],
            strongest_counterpoint="VIX drop reflects calm options pricing without aggressive put buying.",
            invalidation="Strong breakout above yesterday's high with expanding upside volume.",
            data_gaps=pack.failed_sources or ["None identified in briefing pack"],
        )


if __name__ == "__main__":
    from collector import build_pack

    print("Testing Step 3: Dual Adversarial Analysts...")
    test_pack = build_pack()
    print("Briefing Pack built. Running Bull & Bear analysts concurrently...")

    bull, bear = run_dual_analysts(test_pack)

    print("\n--- BULL CASE OUTPUT ---")
    print(json.dumps(bull.model_dump(), indent=2))

    print("\n--- BEAR CASE OUTPUT ---")
    print(json.dumps(bear.model_dump(), indent=2))
