# 🦅 Quant AI Workflow: Dual-Agent Market Debate Engine with Blind Arbitration

[![Language: Python](https://img.shields.io/badge/Language-Python%203.11+-blue.svg)](https://www.python.org/)
[![Language: C++20](https://img.shields.io/badge/Language-C%2B%2B20-orange.svg)](https://en.cppreference.com/w/cpp/20)
[![LLM: Gemini 3.8 Flash](https://img.shields.io/badge/LLM-Gemini%203.8%20Flash-green.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An autonomous **Compound AI Workflow & Multi-Agent Orchestration Engine** designed for quantitative equity regime forecasting on **NAS100 (Nasdaq 100)** prior to the US cash open (09:15 ET).

Rather than relying on a single monolithic prompt that suffers from LLM sycophancy, position bias, and hallucinations, this system orchestrates two parallel adversarial analyst agents (**Bull vs. Bear**) across a strictly curated pre-market briefing pack, passes their structured outputs through a deterministic code-level citation firewall, and submits them to an order-randomized **Blind Judge** for objective arbitration.

Implemented in both **Python (Pydantic V2 + GenAI SDK)** and **High-Performance C++20 (CMake, libcurl, SQLite3, std::async)**.

---

## 🏛️ System Architecture

```
                       ┌──────────────────────────────────────────────┐
                       │  Stage 1: Briefing Pack Collector (09:15 ET) │
                       │  - QQQ (O,H,L,C, 20d Volume), VIX, US10Y, DXY │
                       │  - US Macro Calendar (E1..En, Y1..Yn)        │
                       │  - News (<09:15 ET: H1..Hn), [DATA_STATUS]   │
                       └───────────────────────┬──────────────────────┘
                                               │
                       ┌───────────────────────┴──────────────────────┐
                       ▼                                              ▼
            ┌─────────────────────┐                        ┌─────────────────────┐
            │ Stage 2: BULL Agent │                        │ Stage 2: BEAR Agent │
            │ Gemini 3.8 Flash    │                        │ Gemini 3.8 Flash    │
            │ (thinking: low)     │                        │ (thinking: low)     │
            └──────────┬──────────┘                        └──────────┬──────────┘
                       │                                              │
                       └───────────────────────┬──────────────────────┘
                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Stage 3: Deterministic Citation Firewall     │
                       │ - Verifies all cited IDs in Briefing Pack    │
                       │ - Automated 1-Retry Loop on hallucination    │
                       │ - Safe "No-Verdict" fallback if invalid      │
                       └───────────────────────┬──────────────────────┘
                                               │
                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Stage 4: Blind Anonymizer & Order Shuffler   │
                       │ - Strips "BULL" / "BEAR" labels              │
                       │ - 50/50 Coin Flip: Case X vs Case Y          │
                       │ - Eliminates LLM positional presentation bias│
                       └───────────────────────┬──────────────────────┘
                                               │
                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Stage 5: Neutral Blind Judge                 │
                       │ Gemini 3.8 Flash (thinking: medium, T=0.1)   │
                       │ - Evaluates evidence quality over rhetoric   │
                       │ - Defaults to "sideways" under catalyst risk │
                       └───────────────────────┬──────────────────────┘
                                               │
                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Stage 6: Unblinder, Ledger & Telegram Alert  │
                       │ - Unblinds X/Y -> Real Market Bias           │
                       │ - Immutable SQLite Audit Trail (verdicts.db) │
                       │ - Actionable Telegram Alert to Bot           │
                       │ - 16:00 ET Ground-Truth Win Rate Evaluator   │
                       └──────────────────────────────────────────────┘
```

---

## ⚡ Key Highlights

* **Adversarial Debate Pattern**: Eliminates non-committal answers and single-model confirmation bias by forcing two partisan agents to dig up verifiable evidence for their assigned side.
* **Deterministic Code Firewall**: Python & C++ AST verification ensuring that every cited ID (`PRICE`, `E1`, `Y1`, `H1`) strictly exists in the briefing pack. Rejects hallucinations programmatically.
* **Positional Bias Mitigation (Blind Arbitration)**: Anonymizes and randomizes the order of cases (`Case X` vs `Case Y`) using high-entropy coin flips so the judge evaluates evidence quality rather than prompt order.
* **Asymmetric Thinking Budgets**:
  * **Analysts**: `thinking_level="low"` (1,024 tokens) for low latency and efficient information extraction.
  * **Judge**: `thinking_level="medium"` (2,048 tokens, $T=0.1$) for deep cross-examination and repeatable verdicts.
* **Forward-Testing Audit Trail**: Every pre-market execution logs the raw briefing pack, analyst claims, blind mapping, and judge reasoning into a local SQLite database, automatically reconciling against actual 16:00 ET cash market returns.

---

## 🗂️ Project Structure

```
project_agent/
├── config.py                 # Central configuration, market cutoffs, and environment loader
├── models.py                 # Pydantic schemas: BriefingPack, CaseOutput, JudgeOutput
├── collector.py              # 09:15 ET Ingestion engine (Quotes, Macro Calendar, Headlines)
├── analysts.py               # Concurrent Bull & Bear adversarial engine (Gemini 3.8 Flash)
├── judge.py                  # Citation verification firewall, blind shuffler, and neutral judge
├── storage.py                # SQLite3 persistent audit ledger & performance dashboard
├── notifier.py               # Telegram Bot API formatted alert dispatcher
├── main.py                   # Executive CLI orchestrator (--stats, --eod, --no-telegram)
├── requirements.txt          # Pinned Python dependencies
├── .env.example              # Secrets and configuration template
└── cpp/                      # High-Performance C++20 Implementation
    ├── CMakeLists.txt        # Modern CMake build configuration
    ├── include/
    │   ├── json.hpp          # nlohmann/json compile-time serialization
    │   ├── config.hpp        # Zero-dependency .env loader & system constants
    │   ├── models.hpp        # Modern C++20 structs for data models
    │   ├── http_client.hpp   # RAII-wrapped libcurl HTTP client
    │   ├── collector.hpp     # C++ market data and economic calendar ingestion
    │   ├── analysts.hpp      # Parallel std::async Bull & Bear agent engine
    │   ├── judge.hpp         # Citation firewall & Mersenne Twister blind shuffler
    │   ├── storage.hpp       # Native SQLite3 C-API ledger with prepared statements
    │   └── notifier.hpp      # C++ Telegram alert dispatcher
    └── src/
        └── main.cpp          # C++20 Executive CLI orchestrator
```

---

## 🚀 Quickstart: Python Workflow

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/HARSHCRR/agent.git
cd agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Key variables:
* `GEMINI_API_KEY`: Google Gemini API Key (defaults to automated simulated testing if omitted).
* `FMP_API_KEY`: Financial Modeling Prep API Key (optional).
* `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Telegram credentials for live alerts.

### 3. Execution Commands
```bash
# Run the complete live pre-market workflow
python main.py

# Run in test mode without dispatching Telegram alerts
python main.py --no-telegram

# View forward-testing win rates and performance dashboard
python main.py --stats

# Reconcile post-market outcome at 16:00 ET (e.g. for Oct 12, 2026)
python main.py --eod 2026-10-12
```

---

## ⚡ Quickstart: High-Performance C++20 Engine

The repository includes a complete, standalone **C++20** engine engineered for low-latency quantitative environments:

### 1. Build using CMake:
```bash
cd cpp
mkdir -p build && cd build
cmake ..
make -j4
```

### 2. Run the C++ Binary:
```bash
# Execute the full autonomous pre-market workflow
./quant_agent

# Run without sending Telegram alerts
./quant_agent --no-telegram

# View forward-test win-rate dashboard
./quant_agent --stats

# Record EOD ground-truth market return (e.g., +0.85% Up)
./quant_agent --eod 2026-10-12 0.85 up
```

---

## 📊 Sample Telegram Pre-Market Alert

When executed prior to market open, the orchestrator dispatches an alert formatted as follows:

```text
📊 NAS100 PRE-MARKET VERDICT | 2026-10-12
━━━━━━━━━━━━━━━━━━━━━━
Verdict: 🟢 BULLISH
Confidence: MEDIUM
Winning Case: BULL (Blind Case X)

⚖️ Deciding Factors:
  • VIX compression to 15.31 reflecting calm equity options pricing
  • Supportive pre-market price consolidation above key moving averages

🧠 Rationale:
Technical stability and benign volatility index readings provide superior support compared to macro yield drag concerns.

👀 Events to Watch: Cash open volume expansion, FOMC Member Hammack Speech

⚠️ Caveats: Thin holiday trading volumes (-37.9% vs 20d average) may exaggerate intra-day moves.
━━━━━━━━━━━━━━━━━━━━━━
🤖 Autonomous Dual-Analyst AI Workflow
```

---

## 📈 Performance Tracking & Forward Testing

Unlike toy chatbot demos, every single pre-market decision is stored in an SQLite audit ledger (`data/verdicts.db`):

```sql
SELECT 
    confidence,
    COUNT(*) AS total_calls,
    ROUND(AVG(is_correct) * 100, 1) AS win_rate_pct
FROM verdicts 
WHERE is_correct IS NOT NULL
GROUP BY confidence;
```

This allows quantitative verification of:
1. **Directional Accuracy**: Whether the system beats baseline benchmarks like *"Always Bullish"* or *"Yesterday's Trend"*.
2. **Confidence Calibration**: Whether *"HIGH"* confidence predictions achieve a statistically higher win rate than *"LOW"* confidence predictions.

---

## 💼 Interview Talking Points & Resume Bullets

### Suggested Resume Description:
* **Quant AI Workflow Orchestrator (C++20, Python, Gemini 3.8 Flash, libcurl, SQLite3)**:
  * *Architected an autonomous multi-agent quantitative workflow orchestrating dual adversarial LLM analysts (Bull vs. Bear) and a neutral blind arbitrator for daily Nasdaq 100 regime classification.*
  * *Eliminated presentation position bias and LLM sycophancy by implementing randomized blind arbitration (`Case X` vs `Case Y`) and low-temperature cross-examination.*
  * *Engineered a deterministic citation firewall in Python and modern C++20, enforcing strict compile-time and runtime contracts that reject hallucinated macro data.*
  * *Developed a forward-testing audit ledger in SQLite with automated 16:00 ET ground-truth matching and real-time Telegram webhook dispatching.*

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
