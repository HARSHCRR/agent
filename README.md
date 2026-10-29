# 🦅 Quant AI Workflow: Dual-Agent Market Debate Engine

[![Language: Python](https://img.shields.io/badge/Language-Python%203.11+-blue.svg)](https://www.python.org/)
[![LLM: Gemini 3.8 Flash](https://img.shields.io/badge/LLM-Gemini%203.8%20Flash-green.svg)](https://ai.google.dev/)
[![Storage: CSV / Excel](https://img.shields.io/badge/Storage-CSV%20%2F%20Excel-brightgreen.svg)](data/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An automated multi-agent Python pipeline that analyzes the **NASDAQ-100 (QQQ)** before market open and logs daily predictions and accuracy into an Excel-friendly CSV spreadsheet.

Instead of asking a single AI model for a generic prediction, this project pits two competing AI agents (**Bull vs. Bear**) against each other, verifies their facts with a Python citation check, and uses an impartial **Blind Judge** to decide which side has the stronger evidence.

---

## 💡 The Core Workflow

1. **Morning Market Open (09:15 ET)**: 
   - Pulls morning market data: QQQ prices, VIX volatility index, US economic calendar, and pre-market headlines.
   - Prompts one Gemini model to build the **Bull case** and a second Gemini model to build the **Bear case**.
   - A Python validator checks that every cited number or headline actually exists in the morning briefing.
   - Flips a coin (`random.choice`) to swap Case A and Case B (stripping "Bull" and "Bear" labels) so the Judge cannot have positional or directional bias.
   - A third **Blind Judge** reads both cases and picks the winner based purely on evidence quality.
   - Appends the morning verdict and reasoning directly to `data/daily_verdicts.csv`.

2. **Market Close (16:00 ET)**:
   - Fetches the closing QQQ return from Yahoo Finance.
   - Automatically compares the day's actual move to the morning prediction and logs `is_correct` (1 = correct, 0 = wrong) into the same CSV row.

---

## 📊 CSV Ledger (`data/daily_verdicts.csv`)

All daily predictions and accuracy are tracked in a simple CSV spreadsheet that can be opened in Microsoft Excel, Google Sheets, or Python pandas:

| run_date | verdict | confidence | winning_case | deciding_factors | reasoning | actual_return_pct | actual_direction | is_correct |
| :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: |
| **2026-10-28** | BULLISH | HIGH | BULL | VIX compressed below 16; Volume expansion | Supportive technical momentum outweighs yield drag | +0.85% | UP | **1** |
| **2026-10-29** | SIDEWAYS | LOW | NEITHER | High catalyst risk; Fed meeting ahead | Macro uncertainty limits directional conviction | +0.05% | FLAT | **1** |

---

## 🗂️ Clean Project Structure

```
project_agent/
├── collector.py      # Fetches QQQ prices, VIX, macro events, and news headlines
├── analysts.py       # Calls Gemini twice (Bull agent vs. Bear agent)
├── judge.py          # Fact-checks citations, swaps cases, and runs Blind Judge
├── storage.py        # Appends morning predictions and updates EOD accuracy in CSV
├── main.py           # CLI orchestrator & automatic daily scheduler
├── config.py         # Market cutoff constants & API keys
├── models.py         # Pydantic schemas for data validation
├── requirements.txt  # Project dependencies
└── data/
    └── daily_verdicts.csv  # Excel/CSV accuracy ledger
```

---

## 🚀 Quickstart

### 1. Setup Environment
```bash
git clone https://github.com/HARSHCRR/agent.git
cd agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Gemini API Key
Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`:
```bash
cp .env.example .env
```

### 3. Usage Commands

```bash
# 1. Run the morning workflow manually (pulls live data, debates, and logs to CSV)
python main.py

# 2. Automatically run every day at 09:15 ET (morning) and 16:00 ET (market close)
python main.py --auto

# 3. View overall win rate and accuracy stats from the CSV
python main.py --stats

# 4. Manually reconcile market close for a specific date (e.g., QQQ finished +0.85% Up)
python main.py --eod 2026-10-30
```

---

## 🎯 Interview Talking Points (Easy to Defend)

* **Why two agents instead of one prompt?**
  *"When a single prompt writes both pros and cons, the second half is biased by what the model wrote first. By making two completely independent calls, both agents produce genuinely strong, uncompromised arguments."*
* **How do you prevent hallucinations?**
  *"Every data point in the morning data has an ID (like `PRICE` or `NEWS_1`). The prompt forces agents to cite these IDs, and Python verifies that every cited ID exists in our input dictionary."*
* **Why swap Case A and Case B?**
  *"LLMs have natural positional bias—they often favor whichever option is presented first. Randomly swapping Case A and Case B and stripping 'Bull' and 'Bear' labels ensures the judge evaluates evidence rather than position."*
* **How is performance tracked?**
  *"All verdicts are logged to a CSV spreadsheet. At 16:00 ET, an automated function checks the closing price on Yahoo Finance and scores whether the prediction was correct, allowing easy accuracy tracking over time."*

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
