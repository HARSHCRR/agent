import pytest
from unittest.mock import patch
from models import CaseOutput, CaseDriver, JudgeOutput
from judge import anonymize_and_randomize, unblind_verdict

@pytest.fixture
def mock_cases():
    bull = CaseOutput(
        side="BULL",
        headline="Bull case",
        key_drivers=[
            CaseDriver(point="P1", evidence_ids=["PRICE"], horizon="premarket"),
            CaseDriver(point="P2", evidence_ids=["PRICE"], horizon="us_session"),
            CaseDriver(point="P3", evidence_ids=["PRICE"], horizon="multi_day"),
        ],
        strongest_counterpoint="C1",
        invalidation="I1",
        data_gaps=[],
    )
    bear = CaseOutput(
        side="BEAR",
        headline="Bear case",
        key_drivers=[
            CaseDriver(point="P1", evidence_ids=["PRICE"], horizon="premarket"),
            CaseDriver(point="P2", evidence_ids=["PRICE"], horizon="us_session"),
            CaseDriver(point="P3", evidence_ids=["PRICE"], horizon="multi_day"),
        ],
        strongest_counterpoint="C1",
        invalidation="I1",
        data_gaps=[],
    )
    return bull, bear

def test_unblinding_maps_correct_side(mock_cases):
    bull, bear = mock_cases
    case_x, case_y, mapping = anonymize_and_randomize(bull, bear)
    
    # Check that side key is stripped from cases sent to judge
    assert "side" not in case_x
    assert "side" not in case_y
    
    # Test unblinding Case X
    judge_win_x = JudgeOutput(
        verdict="bullish" if mapping["X"] == "BULL" else "bearish",
        confidence="high",
        winning_case="X",
        deciding_factors=["F1", "F2"],
        reasoning="Good evidence",
        events_to_watch=[],
        caveats="None",
    )
    unblinded_x = unblind_verdict(judge_win_x, mapping)
    assert unblinded_x["unblinded_winner"] == mapping["X"]

    # Test unblinding Case Y
    judge_win_y = JudgeOutput(
        verdict="bearish" if mapping["Y"] == "BEAR" else "bullish",
        confidence="medium",
        winning_case="Y",
        deciding_factors=["F1", "F2"],
        reasoning="Good evidence",
        events_to_watch=[],
        caveats="None",
    )
    unblinded_y = unblind_verdict(judge_win_y, mapping)
    assert unblinded_y["unblinded_winner"] == mapping["Y"]

    # Test unblinding neither
    judge_neither = JudgeOutput(
        verdict="sideways",
        confidence="low",
        winning_case="neither",
        deciding_factors=["F1", "F2"],
        reasoning="Mixed",
        events_to_watch=[],
        caveats="None",
    )
    unblinded_neither = unblind_verdict(judge_neither, mapping)
    assert unblinded_neither["unblinded_winner"] == "NEITHER"

def test_both_orders_reachable(mock_cases):
    bull, bear = mock_cases
    
    with patch("secrets.choice", return_value=True):
        _, _, map_true = anonymize_and_randomize(bull, bear)
        assert map_true == {"X": "BULL", "Y": "BEAR"}
        
    with patch("secrets.choice", return_value=False):
        _, _, map_false = anonymize_and_randomize(bull, bear)
        assert map_false == {"X": "BEAR", "Y": "BULL"}
