import pytest
from models import BriefingPack, PriceMetrics, CalendarEvent, HeadlineItem, CaseOutput, CaseDriver
from judge import validate_citations, verify_cases_with_retry
from analysts import MockLLMClient

@pytest.fixture
def sample_pack():
    return BriefingPack(
        date_et="2026-10-19",
        price=PriceMetrics(prev_close=20000.0, vix=15.0),
        events_today=[
            CalendarEvent(id="E1", time_et="08:30", event="CPI", forecast="0.2%", previous="0.1%"),
            CalendarEvent(id="E2", time_et="10:00", event="PMI", forecast="50.0", previous="49.5"),
        ],
        headlines=[
            HeadlineItem(id="H1", time_et="08:00", source="Reuters", headline="Tech stocks steady"),
        ],
    )

def test_valid_citations(sample_pack):
    valid_ids = sample_pack.get_valid_evidence_ids()
    case = CaseOutput(
        side="BULL",
        headline="Tech stocks poised for upside momentum",
        key_drivers=[
            CaseDriver(point="Inflation easing", evidence_ids=["E1"], horizon="premarket"),
            CaseDriver(point="Low volatility baseline", evidence_ids=["PRICE"], horizon="us_session"),
            CaseDriver(point="Supportive headlines", evidence_ids=["H1"], horizon="multi_day"),
        ],
        strongest_counterpoint="Yields remain elevated",
        invalidation="Drop below yesterday low",
        data_gaps=[],
    )
    is_valid, invalids = validate_citations(case, valid_ids)
    assert is_valid is True
    assert len(invalids) == 0

def test_unknown_id(sample_pack):
    valid_ids = sample_pack.get_valid_evidence_ids()
    case = CaseOutput(
        side="BEAR",
        headline="Downside risk ahead of macro data",
        key_drivers=[
            CaseDriver(point="Phantom event risk", evidence_ids=["E99"], horizon="premarket"),
            CaseDriver(point="Price weakness", evidence_ids=["PRICE"], horizon="us_session"),
            CaseDriver(point="News pressure", evidence_ids=["H1"], horizon="multi_day"),
        ],
        strongest_counterpoint="VIX is calm",
        invalidation="Break above high",
        data_gaps=[],
    )
    is_valid, invalids = validate_citations(case, valid_ids)
    assert is_valid is False
    assert "E99" in invalids

def test_case_insensitive_citation(sample_pack):
    valid_ids = sample_pack.get_valid_evidence_ids()
    case = CaseOutput(
        side="BULL",
        headline="Case test",
        key_drivers=[
            CaseDriver(point="Low VIX", evidence_ids=["price"], horizon="us_session"),
            CaseDriver(point="CPI print", evidence_ids=["e1"], horizon="premarket"),
            CaseDriver(point="Headlines", evidence_ids=["h1"], horizon="multi_day"),
        ],
        strongest_counterpoint="Counter",
        invalidation="Invalidation",
        data_gaps=[],
    )
    is_valid, invalids = validate_citations(case, valid_ids)
    assert is_valid is True
    assert len(invalids) == 0

def test_malformed_empty_evidence_ids(sample_pack):
    valid_ids = sample_pack.get_valid_evidence_ids()
    case = CaseOutput(
        side="BULL",
        headline="Malformed test",
        key_drivers=[
            CaseDriver(point="Uncited point", evidence_ids=["   "], horizon="us_session"),
            CaseDriver(point="Valid point", evidence_ids=["E1"], horizon="premarket"),
            CaseDriver(point="Valid point 2", evidence_ids=["PRICE"], horizon="multi_day"),
        ],
        strongest_counterpoint="Counter",
        invalidation="Invalidation",
        data_gaps=[],
    )
    is_valid, invalids = validate_citations(case, valid_ids)
    assert is_valid is False
    assert "   " in invalids

def test_retry_then_fallback_path(sample_pack):
    bad_case = CaseOutput(
        side="BULL",
        headline="Bad case",
        key_drivers=[
            CaseDriver(point="Bad point", evidence_ids=["E999"], horizon="premarket"),
            CaseDriver(point="Bad point 2", evidence_ids=["E999"], horizon="premarket"),
            CaseDriver(point="Bad point 3", evidence_ids=["E999"], horizon="premarket"),
        ],
        strongest_counterpoint="Counter",
        invalidation="Invalidation",
        data_gaps=[],
    )
    mock_bad_client = MockLLMClient(canned_bull=bad_case, canned_bear=bad_case)
    b_case, r_case, is_valid = verify_cases_with_retry(
        sample_pack, bad_case, bad_case, llm_client=mock_bad_client
    )
    assert is_valid is False
    assert b_case is None
    assert r_case is None
