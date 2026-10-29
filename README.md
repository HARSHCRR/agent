# 🦅 Quant AI Workflow: Dual-Agent Market Debate Engine

[![Language: Python](https://img.shields.io/badge/Language-Python%203.11+-blue.svg)](https://www.python.org/)
[![LLM: Gemini 3.8 Flash](https://img.shields.io/badge/LLM-Gemini%203.8%20Flash-green.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An autonomous multi-agent Python pipeline that analyzes the **NASDAQ-100 (QQQ)** before market open (09:15 ET). 

Instead of asking a single AI model for a generic prediction, this project pits two competing AI agents (**Bull vs. Bear**) against each other, verifies their facts with a Python citation check, and uses an impartial **Blind Judge** to determine which side has the stronger evidence.

---

## 💡 The Core Idea (In 60 Seconds)

If you ask ChatGPT *"Where is the stock market going today?"*, you get vague, non-committal answers or hallucinations.

This project solves that using a simple **3-step workflow**:

1. **The Adversarial Debate**: At 09:15 ET, we pull market data (QQQ price, VIX volatility, economic calendar, news). One AI agent is forced to build the **Bullish case**, and another is forced to build the **Bearish case**.
2. **The Fact Check**: Each agent must cite specific IDs from our data (e.g., `PRICE`, `NEWS_1`). A Python function verifies that every cited ID actually exists in the morning data, catching any hallucinated numbers.
3. **The Blind Judge**: We randomly flip a coin to swap Case A and Case B and strip directional labels ("Bull"/"Bear"). A third AI judge reads both cases blindly and picks the winner purely based on evidence quality.
4. **Daily Logging**: The decision is saved into a local SQLite database (`verdicts.db`). At market close (16:00 ET), we record the actual market move to track accuracy over time.

---

## 🏛️ System Architecture

```
                  ┌────────────────────────────────────────┐
                  │ 1. Collect Morning Market Data         │
                  │    QQQ Price, VIX, Macro News & Events │
                  └───────────────────┬────────────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        ┌─────────────────────┐               ┌─────────────────────┐
        │  Bull Analyst (AI)  │               │  Bear Analyst (AI)  │
        │  Finds reasons to   │               │  Finds reasons to   │
        │  be optimistic      │               │  be cautious        │
        └──────────┬──────────┘               └──────────┬──────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 2. Fact Check (Python)                 │
                  │    Verifies all cited IDs exist in data│
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 3. Blind Randomizer (Coin Flip)        │
                  │    Swaps Case A & B; strips labels     │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 4. Blind Judge (AI)                    │
                  │    Picks Case A, Case B, or Sideways   │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 5. SQLite Database (verdicts.db)       │
                  │    Stores verdict & checks accuracy EOD│
                  └────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

The project is kept simple with clean, modular Python files:

```
project_agent/
├── collector.py      # Fetches QQQ prices, VIX, and news into a clean dictionary
├── analysts.py       # Calls Gemini twice (once Bull prompt, once Bear prompt)
├── judge.py          # Checks citations, swaps cases, and gets Judge verdict
├── storage.py        # Saves predictions to SQLite and records EOD accuracy
├── notifier.py       # Optional Telegram alert sender
├── main.py           # CLI orchestrator that runs the entire workflow
├── config.py         # Configuration settings & environment variables
├── models.py         # Pydantic schemas for data validation
├── tests/            # 9 automated unit tests and offline replay data
│   ├── data/sample_pack.json
│   ├── test_firewall.py
│   ├── test_shuffler.py
│   └── test_storage.py
└── pytest.ini        # Test runner configuration
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

### 2. Configure Credentials
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your `GEMINI_API_KEY`. (If left empty, you can still run in offline replay mode).

### 3. Run Commands

```bash
# Run the live morning workflow
python main.py

# Run in offline replay mode (runs instantly with canned data, no API key needed)
python main.py --replay tests/data/sample_pack.json --no-telegram

# Check historical accuracy and statistics
python main.py --stats

# Record market close results at 16:00 ET (e.g., QQQ finished +0.85% Up)
python main.py --eod 2026-10-30 0.85 up
```

---

## 🧪 Automated Testing

Run the unit test suite:
```bash
pytest -v
```
All 9 unit tests run offline in under 0.2 seconds, testing:
* Citation verification (valid IDs, missing IDs, retry fallback)
* Blind case shuffling and unblinding logic
* SQLite database insertion and EOD accuracy calculation

---

## 🎯 Interview Q&A (How to Defend This)

#### Q1: "Why use two agents (Bull & Bear) instead of one prompt asking for pros and cons?"
> *"When a single prompt writes both pros and cons, the second half of the response is influenced by what the model wrote first due to attention bias. By making two completely independent calls, both agents produce genuinely strong, uncompromised arguments without knowing what the other is saying."*

#### Q2: "How do you prevent the AI from making up numbers?"
> *"Every data point in our morning briefing has an ID (like `PRICE` or `NEWS_1`). In the prompt, agents are required to cite these IDs for every claim. A Python validator checks that every cited ID exists in our input dictionary before passing the argument to the judge."*

#### Q3: "Why randomly swap the cases before the judge sees them?"
> *"LLMs have natural positional bias—they often favor whichever option is presented first. By randomly flipping a coin (`random.choice`) to swap Case A and Case B and removing the words 'Bull' and 'Bear', the judge is forced to evaluate pure argument quality rather than position or market direction."*

#### Q4: "Why native Python instead of LangChain or CrewAI?"
> *"Frameworks like CrewAI add unnecessary prompt overhead and complex conversational loops. For a quantitative workflow, we needed strict data validation, predictable latency, and simple unit tests. Native Python with Pydantic was cleaner, faster, and 100% testable."*

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
