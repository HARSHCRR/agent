import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)
CSV_PATH = DATA_DIR / "daily_verdicts.csv"

FIELDNAMES = [
    "run_date",
    "created_at",
    "verdict",
    "confidence",
    "winning_case",
    "deciding_factors",
    "reasoning",
    "actual_return_pct",
    "actual_direction",
    "is_correct",
]


def init_storage(csv_path: Path = CSV_PATH) -> None:
    """Initializes the CSV ledger with headers if it does not exist."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def save_run(
    run_date: str,
    unblinded_result: Dict[str, Any],
    csv_path: Path = CSV_PATH,
) -> None:
    """Appends morning pre-market verdict to CSV."""
    init_storage(csv_path)
    now_str = datetime.now(timezone.utc).isoformat()

    row = {
        "run_date": run_date,
        "created_at": now_str,
        "verdict": unblinded_result.get("verdict", ""),
        "confidence": unblinded_result.get("confidence", ""),
        "winning_case": unblinded_result.get("unblinded_winner", ""),
        "deciding_factors": "; ".join(unblinded_result.get("deciding_factors", [])),
        "reasoning": unblinded_result.get("reasoning", ""),
        "actual_return_pct": "",
        "actual_direction": "",
        "is_correct": "",
    }

    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)
    logger.info("Saved morning verdict for %s to %s", run_date, csv_path)


def record_eod_outcome(
    run_date: str,
    actual_return_pct: float,
    actual_direction: str,
    csv_path: Path = CSV_PATH,
) -> None:
    """
    Updates the market close outcome at 16:00 ET and records accuracy (1=correct, 0=wrong).
    """
    init_storage(csv_path)
    rows: List[Dict[str, Any]] = []

    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["run_date"] == run_date and row["actual_return_pct"] == "":
                verdict = row["verdict"].strip().lower()
                direction = actual_direction.strip().lower()

                is_correct = 0
                if verdict == "bullish" and direction == "up":
                    is_correct = 1
                elif verdict == "bearish" and direction == "down":
                    is_correct = 1
                elif verdict == "sideways" and direction == "flat":
                    is_correct = 1

                row["actual_return_pct"] = str(actual_return_pct)
                row["actual_direction"] = actual_direction
                row["is_correct"] = str(is_correct)
            rows.append(row)

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Updated EOD outcome for %s in %s", run_date, csv_path)


def get_performance_stats(csv_path: Path = CSV_PATH) -> Dict[str, Any]:
    """Calculates overall win rate and accuracy from the CSV ledger."""
    init_storage(csv_path)
    total_runs = 0
    evaluated = 0
    correct = 0

    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_runs += 1
            if row["is_correct"] != "":
                evaluated += 1
                if row["is_correct"] == "1":
                    correct += 1

    win_rate = round((correct / evaluated) * 100, 1) if evaluated > 0 else 0.0
    return {
        "total_runs": total_runs,
        "evaluated": evaluated,
        "correct": correct,
        "win_rate_pct": win_rate,
    }
