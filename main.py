import argparse
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
import pytz
import schedule
import yfinance as yf

from config import MARKET_TIMEZONE, PREMARKET_TIME, MARKET_CLOSE_TIME
from collector import build_pack
from analysts import run_dual_analysts
from judge import (
    verify_cases_with_retry,
    anonymize_and_randomize,
    evaluate_cases_blind,
    unblind_verdict,
)
from storage import save_run, record_eod_outcome, get_performance_stats, CSV_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MarketPipeline")


def run_morning_workflow(target_date_str: Optional[str] = None) -> Dict[str, Any]:
    """Runs the 09:15 ET pre-market debate and saves prediction to CSV."""
    tz = pytz.timezone(MARKET_TIMEZONE)
    now = datetime.now(tz)
    run_date = target_date_str or now.strftime("%Y-%m-%d")

    logger.info("=== Starting Morning Pre-Market Workflow for %s ===", run_date)

    # 1. Collect market data
    pack = build_pack(run_date)
    logger.info("Briefing Pack collected: %s", pack.date_et)

    # 2. Run Bull & Bear analysts
    bull_case, bear_case = run_dual_analysts(pack)

    # 3. Verify citations
    bull_case, bear_case = verify_cases_with_retry(bull_case, bear_case, pack)

    # 4. Anonymize and randomly swap cases
    case_x, case_y, mapping = anonymize_and_randomize(bull_case, bear_case)

    # 5. Blind Judge evaluates
    judge_output = evaluate_cases_blind(pack, case_x, case_y)
    unblinded_result = unblind_verdict(judge_output, mapping)

    # 6. Save prediction to CSV
    save_run(run_date, unblinded_result)

    print("\n" + "=" * 50)
    print(f" MORNING PRE-MARKET VERDICT: {run_date}")
    print("=" * 50)
    print(f" Verdict:      {unblinded_result['verdict'].upper()}")
    print(f" Confidence:   {unblinded_result['confidence'].upper()}")
    print(f" Winning Case: {unblinded_result['unblinded_winner']}")
    print(f" Reasoning:    {unblinded_result['reasoning']}")
    print(f" Saved to:     {CSV_PATH}")
    print("=" * 50 + "\n")

    return unblinded_result


def run_eod_reconciliation(target_date_str: Optional[str] = None) -> None:
    """Runs at 16:00 ET market close to fetch QQQ performance and update CSV accuracy."""
    tz = pytz.timezone(MARKET_TIMEZONE)
    now = datetime.now(tz)
    run_date = target_date_str or now.strftime("%Y-%m-%d")

    logger.info("=== Reconciling Market Close for %s ===", run_date)

    try:
        ticker = yf.Ticker("QQQ")
        hist = ticker.history(period="5d")
        if hist.empty:
            logger.error("No price data retrieved for QQQ")
            return

        today_bar = hist.iloc[-1]
        open_p = float(today_bar["Open"])
        close_p = float(today_bar["Close"])
        pct_change = round(((close_p - open_p) / open_p) * 100, 2)

        if pct_change > 0.15:
            direction = "up"
        elif pct_change < -0.15:
            direction = "down"
        else:
            direction = "flat"

        record_eod_outcome(run_date, pct_change, direction)
        print(f"\n[EOD Reconciled] {run_date} | QQQ: {pct_change}% ({direction.upper()}) | Saved to {CSV_PATH}\n")
    except Exception as e:
        logger.error("Error during EOD reconciliation: %s", e)


def print_stats() -> None:
    """Prints the historical accuracy from the CSV sheet."""
    stats = get_performance_stats()
    print("\n" + "=" * 45)
    print("     PRE-MARKET PREDICTION ACCURACY (CSV)    ")
    print("=" * 45)
    print(f" Total Days Logged:    {stats['total_runs']}")
    print(f" Days Evaluated:       {stats['evaluated']}")
    print(f" Correct Predictions:  {stats['correct']}")
    print(f" Overall Win Rate:     {stats['win_rate_pct']}%")
    print(f" CSV Location:         {CSV_PATH}")
    print("=" * 45 + "\n")


def start_scheduler() -> None:
    """Runs continuously and automatically triggers at market open (09:15 ET) and close (16:00 ET)."""
    print("\n" + "=" * 60)
    print(" AUTOMATIC SCHEDULER STARTED (US Eastern Time)")
    print(f" - Morning Pre-Market Debate:  Every trading day at {PREMARKET_TIME} ET")
    print(f" - EOD Accuracy Evaluation:   Every trading day at {MARKET_CLOSE_TIME} ET")
    print(f" - Results CSV:               {CSV_PATH}")
    print(" Press Ctrl+C to stop.")
    print("=" * 60 + "\n")

    schedule.every().day.at("09:15").do(run_morning_workflow)
    schedule.every().day.at("16:00").do(run_eod_reconciliation)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Market Regime Pipeline")
    parser.add_argument("--date", type=str, help="Run morning debate for specific date (YYYY-MM-DD)")
    parser.add_argument("--eod", type=str, help="Reconcile market close for specific date (YYYY-MM-DD)")
    parser.add_argument("--stats", action="store_true", help="Print overall prediction accuracy from CSV")
    parser.add_argument("--auto", action="store_true", help="Start automatic scheduler for 09:15 ET and 16:00 ET")

    args = parser.parse_args()

    if args.stats:
        print_stats()
    elif args.eod:
        run_eod_reconciliation(args.eod)
    elif args.auto:
        start_scheduler()
    else:
        run_morning_workflow(args.date)
