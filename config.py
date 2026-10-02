import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# LLM & API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# Thinking configurations:
# Analysts use 'low' thinking effort to keep latency and cost down while strictly adhering to pack evidence.
# Judge uses 'medium' thinking effort to rigorously cross-reference citations and weigh counter-arguments.
THINKING_LEVEL_ANALYST = "low"
THINKING_LEVEL_JUDGE = "medium"

# Market & Scheduling Parameters
MARKET_TIMEZONE = "America/New_York"
PACK_CUTOFF_TIME = "09:15"
SESSION_OPEN_TIME = "09:30"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8544489986:AAF3WO1sSjj06pKu3M_wqJc0gVIHOs94B50")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8624502991")

# Database Path
DB_PATH = DATA_DIR / "verdicts.db"
