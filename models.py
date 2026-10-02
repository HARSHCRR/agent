from typing import List, Literal, Optional, Set
from pydantic import BaseModel, Field, field_validator


# =====================================================================
# 1. BRIEFING PACK DATA STRUCTURES (Plain Data / Collector Models)
# =====================================================================

class PriceMetrics(BaseModel):
    prev_open: Optional[float] = None
    prev_high: Optional[float] = None
    prev_low: Optional[float] = None
    prev_close: Optional[float] = None
    volume_vs_20d_avg_pct: Optional[float] = Field(
        None, description="Volume vs 20-day moving average percentage"
    )
    overnight_futures_change_pct: Optional[float] = Field(
        None, description="Overnight NQ/NAS100 futures percentage change"
    )
    gap_vs_prev_close_pct: Optional[float] = Field(
        None, description="Gap at pre-market vs previous regular session close"
    )
    vix: Optional[float] = None
    vix_change: Optional[float] = None
    us10y: Optional[float] = None
    us10y_change: Optional[float] = None
    dxy: Optional[float] = None
    dxy_change: Optional[float] = None


class CalendarEvent(BaseModel):
    id: str = Field(..., description="Deterministic ID, e.g., 'E1', 'E2'")
    time_et: str = Field(..., description="Release time ET, e.g., '08:30'")
    event: str = Field(..., description="Name of economic event, e.g., 'CPI m/m'")
    forecast: str = Field("N/A", description="Market consensus forecast")
    previous: str = Field("N/A", description="Previous period reading")


class PastCalendarEvent(BaseModel):
    id: str = Field(..., description="Deterministic ID, e.g., 'Y1', 'Y2'")
    event: str = Field(..., description="Name of event")
    actual: str = Field(..., description="Actual outcome")
    expected: str = Field("N/A", description="Expected consensus")


class HeadlineItem(BaseModel):
    id: str = Field(..., description="Deterministic ID, e.g., 'H1', 'H2'")
    time_et: str = Field(..., description="Publication time ET, strictly before 09:15 ET")
    source: str = Field(..., description="Source outlet, e.g., 'Reuters'")
    headline: str = Field(..., description="Headline content")


class BriefingPack(BaseModel):
    date_et: str
    open_et: str = "09:30"
    pack_built_et: str = "09:15"
    price: PriceMetrics
    events_today: List[CalendarEvent] = Field(default_factory=list)
    events_yesterday: List[PastCalendarEvent] = Field(default_factory=list)
    headlines: List[HeadlineItem] = Field(default_factory=list)
    failed_sources: List[str] = Field(
        default_factory=list, description="List of failed API feeds or ['none']"
    )

    def get_valid_evidence_ids(self) -> Set[str]:
        """
        Returns the exact set of valid evidence citation IDs present in this briefing pack.
        Any analyst citing an ID outside this set will be flagged for hallucination.
        """
        valid_ids: Set[str] = {"PRICE"}
        for e in self.events_today:
            valid_ids.add(e.id)
        for y in self.events_yesterday:
            valid_ids.add(y.id)
        for h in self.headlines:
            valid_ids.add(h.id)
        return valid_ids

    def to_briefing_text(self) -> str:
        """Formats the briefing pack into the exact prompt-friendly structured string."""
        p = self.price
        price_str = (
            f"prev_day: O={p.prev_open} H={p.prev_high} L={p.prev_low} C={p.prev_close} | "
            f"volume_vs_20d_avg={p.volume_vs_20d_avg_pct}% overnight_futures_change={p.overnight_futures_change_pct}% | "
            f"gap_vs_prev_close={p.gap_vs_prev_close_pct}% VIX={p.vix} (chg {p.vix_change}) | "
            f"US10Y={p.us10y} (chg {p.us10y_change}) | DXY={p.dxy} (chg {p.dxy_change})"
        )

        events_today_str = (
            "\n".join(
                f"{e.id} | {e.time_et} | {e.event} | {e.forecast} | {e.previous}"
                for e in self.events_today
            )
            if self.events_today
            else "none"
        )

        events_yest_str = (
            "\n".join(
                f"{y.id} | {y.event} | {y.actual} | {y.expected}"
                for y in self.events_yesterday
            )
            if self.events_yesterday
            else "none"
        )

        headlines_str = (
            "\n".join(
                f"{h.id} | {h.time_et} | {h.source} | {h.headline}"
                for h in self.headlines
            )
            if self.headlines
            else "none"
        )

        failed_str = ", ".join(self.failed_sources) if self.failed_sources else "none"

        return (
            f"DATE_ET: {self.date_et} | OPEN_ET: {self.open_et} | PACK_BUILT_ET: {self.pack_built_et}\n\n"
            f"[PRICE]\n{price_str}\n\n"
            f"[EVENTS_TODAY] (time ET | event | forecast | previous)\n{events_today_str}\n\n"
            f"[EVENTS_YESTERDAY] (event | actual | expected)\n{events_yest_str}\n\n"
            f"[HEADLINES] (published before {self.pack_built_et} ET only)\n{headlines_str}\n\n"
            f"[DATA_STATUS] failed_sources: [{failed_str}]"
        )


# =====================================================================
# 2. ANALYST CASE SCHEMAS (Bull & Bear Structured Output)
# =====================================================================

class CaseDriver(BaseModel):
    point: str = Field(..., description="Core argument statement")
    evidence_ids: List[str] = Field(
        ..., description="Must cite valid evidence IDs from the pack (e.g. ['E1', 'H3'] or ['PRICE'])"
    )
    horizon: Literal["premarket", "us_session", "multi_day"] = Field(
        ..., description="Expected impact horizon"
    )


class CaseOutput(BaseModel):
    side: Literal["BULL", "BEAR"] = Field(
        ..., description="Assigned side: strictly BULL or BEAR"
    )
    headline: str = Field(..., description="High impact headline, max 20 words")
    key_drivers: List[CaseDriver] = Field(
        ..., description="Exactly 3 key evidence-backed drivers"
    )
    strongest_counterpoint: str = Field(
        ..., description="The single strongest point against your own case"
    )
    invalidation: str = Field(
        ..., description="What event or move would prove this case wrong"
    )
    data_gaps: List[str] = Field(
        default_factory=list,
        description="Acknowledged weaknesses, thin evidence, or failed sources",
    )

    @field_validator("key_drivers")
    @classmethod
    def validate_key_drivers_count(cls, v: List[CaseDriver]) -> List[CaseDriver]:
        if len(v) != 3:
            raise ValueError(f"Requirement failed: Exactly 3 key_drivers required, received {len(v)}")
        return v

    @field_validator("headline")
    @classmethod
    def validate_headline_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 20:
            raise ValueError(f"Headline exceeds 20 words limit (contains {len(words)} words)")
        return v


# =====================================================================
# 3. BLIND JUDGE SCHEMAS (Neutral Arbitrator Structured Output)
# =====================================================================

class JudgeOutput(BaseModel):
    verdict: Literal["bullish", "bearish", "sideways"] = Field(
        ..., description="Overall market session expectation"
    )
    confidence: Literal["low", "medium", "high"] = Field(
        ..., description="Confidence rating based on evidence robustness"
    )
    winning_case: Literal["X", "Y", "neither"] = Field(
        ..., description="Winner based strictly on blind Case X vs Case Y"
    )
    deciding_factors: List[str] = Field(
        ..., description="Top 2 deciding factors separating the cases"
    )
    reasoning: str = Field(
        ..., description="Concise rationale, max 80 words"
    )
    events_to_watch: List[str] = Field(
        default_factory=list, description="Crucial intra-day events to monitor"
    )
    caveats: str = Field(
        ..., description="Risk factors, data gaps, or failed source warnings"
    )

    @field_validator("deciding_factors")
    @classmethod
    def validate_deciding_factors(cls, v: List[str]) -> List[str]:
        if len(v) < 1:
            raise ValueError("Must provide at least 1 deciding factor (ideally 2)")
        return v

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 85:  # small grace buffer for word count variations
            raise ValueError(f"Reasoning exceeds 80 words limit (contains {len(words)} words)")
        return v
