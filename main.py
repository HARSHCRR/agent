import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import pytz

from config import MARKET_TIMEZONE
from collector import build_pack
from analysts import run_dual_analysts
from judge import (
    verify_cases_with_retry,
    anonymize_and_randomize,
    evaluate_cases_blind,
    unblind_verdict,
)
from storage import save_run, record_eod_outcome, get_performance_stats
from notifier import format_telegram_message, send_telegram_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("WorkflowOrchestrator")


def run_workflow(
    target_date_str: Optional[str] = None,
    send_telegram: bool = True,
) -> Dict[str, Any]:
    """
    Executes the complete 5-stage Compound AI Workflow:
    1. Briefing Pack Ingestion (09:15 ET)
    2. Dual Adversarial Analysts (Bull vs Bear)
    3. Citation Firewall & Retry Loop
    4. Blind Anonymization & Randomization
    5. Neutral Judge Arbitration (Gemini 3.8 Flash, Medium Thinking)
    6. Unblinding, SQLite Ledger Persistence, and Telegram Dispatch
    """
    tz_et = pytz.timezone(MARKET_TIMEZONE)
    if target_date_str:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.now(tz_et).date()

    date_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"=== Starting Autonomous Pre-Market Workflow for {date_str} ===")

    # STAGE 1: Collect Briefing Pack
    logger.info("[Stage 1/6] Ingesting market metrics, economic calendar, and news...")
    pack = build_pack(target_date)
    pack_text = pack.to_briefing_text()
    logger.info(f"Briefing Pack compiled ({len(pack.get_valid_evidence_ids())} valid evidence tokens).")

    # STAGE 2: Run Dual Adversarial Analysts Concurrently
    logger.info("[Stage 2/6] Launching concurrent Bull and Bear analyst agents...")
    bull_case, bear_case = run_dual_analysts(pack)

    # STAGE 3: Citation Verification Firewall
    logger.info("[Stage 3/6] Verifying evidence citations against Briefing Pack...")
    b_case, r_case, is_valid = verify_cases_with_retry(pack, bull_case, bear_case)

    if not is_valid or b_case is None or r_case is None:
        logger.error("Citation validation failed after retry. Falling back to SAFE NO-VERDICT.")
        fallback_record = {
            "verdict": "sideways",
            "confidence": "low",
            "blind_winner": "neither",
            "unblinded_winner": "DATA_ERROR",
            "mapping": {},
            "deciding_factors": ["Citation verification failure: hallucinated evidence IDs detected"],
            "reasoning": "Analyst cases contained invalid citations outside the verified briefing pack.",
            "events_to_watch": [],
            "caveats": "Data integrity check failed. No trading bias issued.",
        }
        row_id = save_run(date_str, pack_text, bull_case.model_dump(), bear_case.model_dump(), fallback_record)
        if send_telegram:
            msg = format_telegram_message(date_str, fallback_record)
            send_telegram_alert(msg)
        return fallback_record

    # STAGE 4: Blind Anonymization & Order Randomization
    logger.info("[Stage 4/6] Anonymizing analyst cases and randomizing presentation order...")
    case_x, case_y, mapping = anonymize_and_randomize(b_case, r_case)
    logger.info(f"Blind mapping established: Case X={mapping['X']}, Case Y={mapping['Y']}")

    # STAGE 5: Neutral Blind Judge Arbitration
    logger.info("[Stage 5/6] Submitting cases to Neutral Blind Judge...")
    judge_output = evaluate_cases_blind(pack, case_x, case_y)

    # STAGE 6: Unblind, Persist & Notify
    logger.info("[Stage 6/6] Unblinding verdict, persisting to SQLite, and dispatching notification...")
    final_record = unblind_verdict(judge_output, mapping)

    # Save to SQLite database
    row_id = save_run(
        run_date=date_str,
        pack_text=pack_text,
        bull_case=b_case.model_dump(),
        bear_case=r_case.model_dump(),
        unblinded_result=final_record,
    )
    logger.info(f"Execution record saved to database (ID: {row_id}).")

    # Send Telegram alert
    if send_telegram:
        alert_msg = format_telegram_message(date_str, final_record)
        send_telegram_alert(alert_msg)

    logger.info(f"Workflow Complete | Verdict: {final_record['verdict'].upper()} | Confidence: {final_record['confidence'].upper()} | Winner: {final_record['unblinded_winner']}")
    return final_record


def evaluate_eod(date_str: str) -> None:
    """Evaluates actual EOD market close return (at 16:00 ET) and records ground-truth accuracy."""
    import yfinance as yf

    logger.info(f"Evaluating EOD outcome for {date_str}...")
    qqq = yf.Ticker("QQQ")
    hist = qqq.history(period="5d")
    if len(hist) < 2:
        logger.error("Insufficient price data to evaluate EOD outcome.")
        return

    latest = hist.iloc[-1]
    prev = hist.iloc[-2]
    ret_pct = ((float(latest["Close"]) - float(prev["Close"])) / float(prev["Close"])) * 100

    if ret_pct > 0.20:
        direction = "up"
    elif ret_pct < -0.20:
        direction = "down"
    else:
        direction = "flat"

    record_eod_outcome(date_str, round(ret_pct, 2), direction)
    logger.info(f"EOD Evaluated | Actual Return: {ret_pct:+.2f}% | Direction: {direction.upper()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NAS100 Compound AI Workflow Runner")
    parser.add_argument("--date", type=str, help="Run for specific date (YYYY-MM-DD)")
    parser.add_argument("--no-telegram", action="store_true", help="Suppress Telegram alert dispatch")
    parser.add_argument("--stats", action="store_true", help="Display forward-testing performance statistics")
    parser.add_argument("--eod", type=str, help="Evaluate post-market outcome for date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.stats:
        stats = get_performance_stats()
        print("\n=== FORWARD-TEST PERFORMANCE DASHBOARD ===")
        print(f"Total Pre-Market Runs: {stats['total_runs']}")
        overall = stats.get("overall", {})
        print(f"Evaluated Runs: {overall.get('evaluated', 0)}")
        print(f"Correct Predictions: {overall.get('correct', 0)}")
        print(f"Overall Directional Win Rate: {overall.get('overall_win_rate', 0.0)}%")
        print("\nBreakdown by Confidence Level:")
        for row in stats.get("by_confidence", []):
            print(f"  • Confidence: {row['confidence'].upper():<7} | Count: {row['count']} | Win Rate: {row['win_rate']*100:.1f}%")
        print("==========================================\n")
        sys.exit(0)

    if args.eod:
        evaluate_eod(args.eod)
        sys.exit(0)

    # Standard run
    res = run_workflow(target_date_str=args.date, send_telegram=not args.no_telegram)
    print("\n--- FINAL WORKFLOW OUTPUT ---")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
