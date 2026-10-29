import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH

logger = logging.getLogger(__name__)


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes the standard SQLite database schema for logging daily verdicts."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS verdicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                pack_text TEXT NOT NULL,
                bull_case TEXT NOT NULL,
                bear_case TEXT NOT NULL,
                blind_mapping TEXT NOT NULL,
                blind_winner TEXT NOT NULL,
                unblinded_winner TEXT NOT NULL,
                verdict TEXT NOT NULL,
                confidence TEXT NOT NULL,
                deciding_factors TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                events_to_watch TEXT NOT NULL,
                caveats TEXT NOT NULL,
                actual_return_pct REAL DEFAULT NULL,
                actual_direction TEXT DEFAULT NULL,
                is_correct INTEGER DEFAULT NULL
            )
            """
        )
        conn.commit()


def save_run(
    run_date: str,
    pack_text: str,
    bull_case: Dict[str, Any],
    bear_case: Dict[str, Any],
    unblinded_result: Dict[str, Any],
    db_path: Path = DB_PATH,
) -> int:
    """
    Saves a snapshot of the pre-market execution into SQLite.
    Returns the newly inserted row ID.
    """
    init_db(db_path)
    now_str = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO verdicts (
                run_date, created_at, pack_text, bull_case, bear_case,
                blind_mapping, blind_winner, unblinded_winner,
                verdict, confidence, deciding_factors, reasoning,
                events_to_watch, caveats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_date,
                now_str,
                pack_text,
                json.dumps(bull_case),
                json.dumps(bear_case),
                json.dumps(unblinded_result.get("mapping", {})),
                unblinded_result.get("blind_winner", ""),
                unblinded_result.get("unblinded_winner", ""),
                unblinded_result.get("verdict", ""),
                unblinded_result.get("confidence", ""),
                json.dumps(unblinded_result.get("deciding_factors", [])),
                unblinded_result.get("reasoning", ""),
                json.dumps(unblinded_result.get("events_to_watch", [])),
                unblinded_result.get("caveats", ""),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def record_eod_outcome(
    run_date: str,
    actual_return_pct: float,
    actual_direction: str,
    db_path: Path = DB_PATH,
) -> None:
    """
    Updates the post-session market outcome (at 16:00 ET) and computes accuracy.
    """
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, verdict FROM verdicts WHERE run_date = ? AND actual_return_pct IS NULL", (run_date,))
        rows = cursor.fetchall()

        for row_id, verdict in rows:
            is_correct = 0
            if verdict.lower() == "bullish" and actual_direction.lower() == "up":
                is_correct = 1
            elif verdict.lower() == "bearish" and actual_direction.lower() == "down":
                is_correct = 1
            elif verdict.lower() == "sideways" and actual_direction.lower() == "flat":
                is_correct = 1

            cursor.execute(
                """
                UPDATE verdicts
                SET actual_return_pct = ?, actual_direction = ?, is_correct = ?
                WHERE id = ?
                """,
                (actual_return_pct, actual_direction, is_correct, row_id),
            )
        conn.commit()


def get_performance_stats(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Calculates forward-testing win rates and accuracy grouped by confidence level.
    """
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total FROM verdicts")
        total_runs = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT 
                confidence,
                COUNT(*) as count,
                AVG(is_correct) as win_rate
            FROM verdicts
            WHERE is_correct IS NOT NULL
            GROUP BY confidence
            """
        )
        confidence_breakdown = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT 
                COUNT(*) as evaluated,
                SUM(is_correct) as correct,
                ROUND(AVG(is_correct) * 100, 1) as overall_win_rate
            FROM verdicts
            WHERE is_correct IS NOT NULL
            """
        )
        overall = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT
                ROUND(AVG(CASE WHEN actual_direction = 'up' THEN 1.0 ELSE 0.0 END) * 100, 1) as always_bullish_win_rate
            FROM verdicts
            WHERE is_correct IS NOT NULL
            """
        )
        baseline_row = cursor.fetchone()
        always_bullish = baseline_row["always_bullish_win_rate"] if baseline_row else None

    return {
        "total_runs": total_runs,
        "overall": overall,
        "by_confidence": confidence_breakdown,
        "baselines": {
            "always_bullish_win_rate": always_bullish
        }
    }
