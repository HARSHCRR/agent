import sqlite3
import pytest
from pathlib import Path
from storage import init_db, save_run, record_eod_outcome, get_performance_stats

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_verdicts.db"
    init_db(db_file)
    return db_file

def test_save_verdict_record(temp_db):
    sample_result = {
        "verdict": "bullish",
        "confidence": "high",
        "blind_winner": "X",
        "unblinded_winner": "BULL",
        "mapping": {"X": "BULL", "Y": "BEAR"},
        "deciding_factors": ["VIX compression"],
        "reasoning": "Strong support above moving average",
        "events_to_watch": [],
        "caveats": "Thin volume",
    }
    row_id = save_run("2026-10-19", "pack", {"thesis": "bullish"}, {"thesis": "bearish"}, sample_result, db_path=temp_db)
    assert row_id == 1

    with sqlite3.connect(temp_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT run_date, verdict, confidence, unblinded_winner FROM verdicts WHERE id = ?", (row_id,))
        row = cur.fetchone()
        assert row == ("2026-10-19", "bullish", "high", "BULL")

def test_eod_reconciliation_accuracy(temp_db):
    # Case 1: Bullish prediction + Up market -> is_correct = 1
    res_bull = {
        "verdict": "bullish", "confidence": "high", "blind_winner": "X",
        "unblinded_winner": "BULL", "mapping": {"X": "BULL", "Y": "BEAR"},
        "deciding_factors": ["F1"], "reasoning": "R1", "events_to_watch": [], "caveats": "",
    }
    save_run("2026-10-20", "pack", {}, {}, res_bull, db_path=temp_db)
    record_eod_outcome("2026-10-20", 1.25, "up", db_path=temp_db)

    # Case 2: Bearish prediction + Up market -> is_correct = 0
    res_bear = {
        "verdict": "bearish", "confidence": "medium", "blind_winner": "Y",
        "unblinded_winner": "BEAR", "mapping": {"X": "BULL", "Y": "BEAR"},
        "deciding_factors": ["F1"], "reasoning": "R1", "events_to_watch": [], "caveats": "",
    }
    save_run("2026-10-21", "pack", {}, {}, res_bear, db_path=temp_db)
    record_eod_outcome("2026-10-21", 0.80, "up", db_path=temp_db)

    stats = get_performance_stats(db_path=temp_db)
    assert stats["total_runs"] == 2
    assert stats["overall"]["evaluated"] == 2
    assert stats["overall"]["correct"] == 1
    assert stats["overall"]["overall_win_rate"] == 50.0
