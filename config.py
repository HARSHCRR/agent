import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "daily_verdicts.csv"

# Models and APIs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.8-flash"
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# Gemini Thinking Levels
THINKING_LEVEL_ANALYST = "low"
THINKING_LEVEL_JUDGE = "medium"

# Market Timing (US Eastern Time)
MARKET_TIMEZONE = "America/New_York"
PREMARKET_TIME = "09:15"
PACK_CUTOFF_TIME = "09:15"
SESSION_OPEN_TIME = "09:30"
MARKET_CLOSE_TIME = "16:00"
