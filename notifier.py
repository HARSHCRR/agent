import logging
from typing import Any, Dict
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def format_telegram_message(run_date: str, result: Dict[str, Any]) -> str:
    """Formats the unblinded arbitrator verdict into an executive Telegram alert."""
    verdict = result.get("verdict", "sideways").upper()
    confidence = result.get("confidence", "low").upper()
    unblinded_winner = result.get("unblinded_winner", "NEITHER")
    blind_winner = result.get("blind_winner", "neither")
    reasoning = result.get("reasoning", "")
    caveats = result.get("caveats", "")
    deciding_factors = result.get("deciding_factors", [])
    events_to_watch = result.get("events_to_watch", [])

    # Verdict Icon
    if verdict == "BULLISH":
        badge = "🟢 BULLISH"
    elif verdict == "BEARISH":
        badge = "🔴 BEARISH"
    else:
        badge = "🟡 SIDEWAYS / NEUTRAL"

    factors_str = "\n".join(f"  • {f}" for f in deciding_factors) if deciding_factors else "  • Balanced evidence"
    events_str = ", ".join(events_to_watch) if events_to_watch else "None reported"

    msg = (
        f"📊 *NAS100 PRE-MARKET VERDICT* | `{run_date}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Verdict:* {badge}\n"
        f"*Confidence:* `{confidence}`\n"
        f"*Winning Case:* `{unblinded_winner}` _(Blind Case {blind_winner})_\n\n"
        f"⚖️ *Deciding Factors:*\n{factors_str}\n\n"
        f"🧠 *Rationale:*\n{reasoning}\n\n"
        f"👀 *Events to Watch:* {events_str}\n\n"
        f"⚠️ *Caveats:* {caveats}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 _Autonomous Dual-Analyst AI Workflow_"
    )
    return msg


def send_telegram_alert(message: str, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID) -> bool:
    """
    Sends the formatted alert to Telegram chat via Bot API.
    Gracefully logs and avoids crashing if token or chat_id is invalid.
    """
    if not token or not chat_id or "your_" in token:
        logger.warning("Telegram credentials not configured. Skipping live alert dispatch.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram alert delivered successfully.")
            return True
        else:
            logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to deliver Telegram alert: {e}")
        return False


if __name__ == "__main__":
    print("Testing Step 5: Telegram Notifier...")
    sample_res = {
        "verdict": "bullish",
        "confidence": "medium",
        "blind_winner": "X",
        "unblinded_winner": "BULL",
        "deciding_factors": ["VIX compression to 15.31", "Supportive pre-market price action"],
        "reasoning": "Technical stability above key moving averages offsets elevated bond yield concerns.",
        "events_to_watch": ["Average Hourly Earnings", "Non-Farm Payrolls"],
        "caveats": "Sticky inflation prints at 08:30 ET could invalidate bullish momentum.",
    }
    sample_msg = format_telegram_message("2026-10-12", sample_res)
    print("\n--- FORMATTED TELEGRAM MESSAGE ---")
    print(sample_msg)
    print("\nAttempting delivery to configured chat...")
    delivered = send_telegram_alert(sample_msg)
    print("Delivery status:", delivered)
