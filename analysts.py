import concurrent.futures
import json
import logging
from typing import Dict, Literal, Optional, Protocol, Tuple

from config import GEMINI_API_KEY, GEMINI_MODEL, THINKING_LEVEL_ANALYST
from models import BriefingPack, CaseDriver, CaseOutput

logger = logging.getLogger(__name__)

# =====================================================================
# LLM CLIENT ABSTRACTION (FOR TESTING, REPLAY & INJECTION)
# =====================================================================

class LLMClient(Protocol):
    def generate_case(self, side: Literal["BULL", "BEAR"], pack: BriefingPack) -> CaseOutput:
        ...

class GeminiLLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL

    def generate_case(self, side: Literal["BULL", "BEAR"], pack: BriefingPack) -> CaseOutput:
        from google import genai
        from google.genai import types

        system_instruction = ANALYST_SYSTEM_PROMPT.format(SIDE=side)
        user_prompt = ANALYST_USER_PROMPT.format(SIDE=side, pack_text=pack.to_briefing_text())

        client = genai.Client(api_key=self.api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=CaseOutput,
            temperature=0.2,
            thinking_config=types.ThinkingConfig(
                thinking_budget=1024
            ) if "flash" in self.model.lower() else None,
        )

        response = client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )
        return CaseOutput.model_validate_json(response.text)

class MockLLMClient:
    def __init__(
        self,
        canned_bull: Optional[CaseOutput] = None,
        canned_bear: Optional[CaseOutput] = None,
    ):
        self.canned_bull = canned_bull
        self.canned_bear = canned_bear

    def generate_case(self, side: Literal["BULL", "BEAR"], pack: BriefingPack) -> CaseOutput:
        if side == "BULL" and self.canned_bull:
            return self.canned_bull
        if side == "BEAR" and self.canned_bear:
            return self.canned_bear
        return _generate_mock_case(side, pack)


# =====================================================================
# PARAMETERIZED ANALYST PROMPT TEMPLATE
# =====================================================================

ANALYST_SYSTEM_PROMPT = """You are an institutional quantitative equity analyst assigned to argue the {SIDE} case for NAS100 (Nasdaq 100) for today\'s US cash session. You will be given a briefing pack.

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
    client: Optional[LLMClient] = None,
) -> CaseOutput:
    """
    Executes a single analyst prompt (BULL or BEAR) against Gemini 3.8 Flash
    or an injected LLMClient.
    """
    if client is not None:
        return client.generate_case(side, pack)

    key = api_key or GEMINI_API_KEY
    if not key or key.strip() == "" or key == "your_gemini_api_key_here":
        logger.warning(f"No GEMINI_API_KEY found. Generating simulated {side} case for dry-run.")
        return _generate_mock_case(side, pack)

    try:
        gemini_client = GeminiLLMClient(api_key=key, model=model_name or GEMINI_MODEL)
        return gemini_client.generate_case(side, pack)
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
    client: Optional[LLMClient] = None,
) -> Tuple[CaseOutput, CaseOutput]:
    """
    Runs both Bull and Bear analysts concurrently in parallel threads to cut execution latency.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_bull = executor.submit(generate_case, "BULL", pack, api_key, model_name, client)
        future_bear = executor.submit(generate_case, "BEAR", pack, api_key, model_name, client)

        bull_case = future_bull.result()
        bear_case = future_bear.result()

    return bull_case, bear_case


# =====================================================================
# SIMULATED / DRY-RUN CASE GENERATOR (Offline / Testing Mode)
# =====================================================================

def _generate_mock_case(side: Literal["BULL", "BEAR"], pack: BriefingPack) -> CaseOutput:
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
            invalidation="A breakdown below yesterday\'s low on high morning selling volume.",
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
            invalidation="Strong breakout above yesterday\'s high with expanding upside volume.",
            data_gaps=pack.failed_sources or ["None identified in briefing pack"],
        )
