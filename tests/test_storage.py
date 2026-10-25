import sqlite3
import pytest
from pathlib import Path
from storage import init_db, save_run, record_eod_outcome, get_performance_stats

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_verdicts.db"
    init_db(db_file)
    return db_file

def test_append_only_trigger_blocks_delete(temp_db):
    sample_result = {
        "verdict": "bullish",
        "confidence": "high",
        "blind_winner": "X",
        "unblinded_winner": "BULL",
        "mapping": {"X": "BULL", "Y": "BEAR"},
        "deciding_factors": ["F1"],
        "reasoning": "R1",
        "events_to_watch": [],
        "caveats": "C1",
    }
    row_id = save_run("2026-10-19", "pack", {"b": 1}, {"r": 1}, sample_result, db_path=temp_db)
    assert row_id == 1

    # Attempt to DELETE must fail via trigger
    with sqlite3.connect(temp_db) as conn:
        cur = conn.cursor()
        with pytest.raises(sqlite3.DatabaseError) as exc_info:
            cur.execute("DELETE FROM verdicts WHERE id = ?", (row_id,))
        assert "Deletes are strictly prohibited" in str(exc_info.value)

def test_append_only_trigger_blocks_core_update(temp_db):
    sample_result = {
        "verdict": "bullish",
        "confidence": "high",
        "blind_winner": "X",
        "unblinded_winner": "BULL",
        "mapping": {"X": "BULL", "Y": "BEAR"},
        "deciding_factors": ["F1"],
        "reasoning": "R1",
        "events_to_watch": [],
        "caveats": "C1",
    }
    row_id = save_run("2026-10-19", "pack", {"b": 1}, {"r": 1}, sample_result, db_path=temp_db)

    # Attempt to tamper with pre-market verdict or reasoning must fail via trigger
    with sqlite3.connect(temp_db) as conn:
        cur = conn.cursor()
        with pytest.raises(sqlite3.DatabaseError) as exc_info:
            cur.execute("UPDATE verdicts SET verdict = 'bearish' WHERE id = ?", (row_id,))
        assert "Pre-market verdict fields are immutable" in str(exc_info.value)

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

    # Ensure second attempt to modify already reconciled EOD is blocked
    with sqlite3.connect(temp_db) as conn:
        cur = conn.cursor()
        with pytest.raises(sqlite3.DatabaseError):
            cur.execute("UPDATE verdicts SET actual_return_pct = 99.9 WHERE run_date = '2026-10-20'")
