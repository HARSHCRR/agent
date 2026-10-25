# 🦅 Quant AI Workflow: Dual-Agent Market Debate Engine with Blind Arbitration

[![Language: Python](https://img.shields.io/badge/Language-Python%203.11+-blue.svg)](https://www.python.org/)
[![LLM: Gemini 3.8 Flash](https://img.shields.io/badge/LLM-Gemini%203.8%20Flash-green.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An autonomous **Compound AI Workflow & Multi-Agent Orchestration Engine** designed for quantitative equity regime analysis on **NAS100 (Nasdaq 100)** prior to the US cash open (09:15 ET).

Rather than relying on a single monolithic prompt that suffers from LLM sycophancy, position bias, and ungrounded hallucinations, this system orchestrates two parallel adversarial analyst agents (**Bull vs. Bear**) across a strictly curated pre-market briefing pack, passes their structured outputs through a deterministic code-level citation firewall, and submits them to an order-randomized **Blind Judge** for objective arbitration.

Implemented in **Python 3.11+ (Pydantic V2 + Google GenAI SDK)** with an offline replay engine and comprehensive test harness.

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
                       │ - Set-membership check of cited IDs in Pack  │
                       │ - Automated 1-Retry Loop on hallucination    │
                       │ - Safe "No-Verdict" fallback if invalid      │
                       └───────────────────────┬──────────────────────┘
                                               │
                                               ▼
                       ┌──────────────────────────────────────────────┐
                       │ Stage 4: Blind Anonymizer & Order Shuffler   │
                       │ - Strips "BULL" / "BEAR" labels              │
                       │ - Random coin flip: Case X vs Case Y         │
                       │ - Mitigates LLM positional presentation bias │
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
                       │ - Append-only SQLite Ledger (verdicts.db)    │
                       │ - Actionable Telegram Alert to Bot           │
                       │ - 16:00 ET Ground-Truth Win Rate Evaluator   │
                       └──────────────────────────────────────────────┘
```

---

## ⚡ Key Highlights

* **Adversarial Debate Pattern**: Mitigates non-committal answers and single-model confirmation bias by forcing two partisan agents to dig up verifiable evidence for their assigned side.
* **Deterministic Code Firewall**: Runtime set-membership verification ensuring that every cited ID (`PRICE`, `E1`, `Y1`, `H1`) strictly exists in the briefing pack. Rejects hallucinated citations programmatically and validates payload schemas via Pydantic V2.
* **Positional Bias Mitigation (Blind Arbitration)**: Anonymizes and randomizes the order of cases (`Case X` vs `Case Y`) using cryptographic PRNG (`secrets.choice`) so the judge evaluates evidence quality rather than prompt order.
* **Asymmetric Thinking Budgets**:
  * **Analysts**: `thinking_level="low"` (1,024 tokens) for low latency and focused information extraction.
  * **Judge**: `thinking_level="medium"` (2,048 tokens, $T=0.1$) for deep cross-examination and repeatable verdicts.
* **Append-Only SQLite Ledger**: Every pre-market execution logs the raw briefing pack, analyst claims, blind mapping, and judge reasoning into an SQLite database with triggers enforcing immutability on core decision fields.

---

## ⚙️ Design Notes

* **Workload Characteristics**: The pipeline execution is network-bound on external LLM inference and financial API endpoints (~1.5–4.0s wall-clock time). Local data validation, shuffling, and database insertion take under 5 milliseconds.
* **Offline Replay Mode**: The entire pipeline can execute deterministically without API keys or network calls via `--replay <path/to/pack.json>`, mocking the LLM responses for CI/CD and regression testing.
* **Modular LLM Client Protocol**: Analysts and Judge depend on abstract protocols (`LLMClient`, `JudgeLLMClient`), allowing drop-in test doubles and multi-model evaluations.

---

## ⚠️ Limitations & Realism

1. **Sample Size & Statistical Power**: Because this pipeline produces at most one prediction per trading day (~252 sessions/year), calculating a statistically significant win rate or Sharpe ratio requires several months of live forward testing ($N \ge 100$). Short-term win rates are statistically noisy.
2. **No Claim of Market Edge**: LLM reasoning summarizes and stresses existing public data; this pipeline does not claim an alpha edge or predictive superiority over market baselines.
3. **Non-Deterministic Outputs**: Even with low temperature ($T=0.1$) and fixed seeds, current commercial LLM API outputs remain non-deterministic across calls.

---

## 🗂️ Project Structure

```
project_agent/
├── config.py                 # Central configuration, market cutoffs, and environment loader
├── models.py                 # Pydantic schemas: BriefingPack, CaseOutput, JudgeOutput
├── collector.py              # 09:15 ET Ingestion engine (Quotes, Macro Calendar, Headlines)
├── analysts.py               # Concurrent Bull & Bear adversarial engine (Gemini 3.8 Flash)
├── judge.py                  # Citation verification firewall, blind shuffler, and neutral judge
├── storage.py                # Append-only SQLite3 audit ledger & performance dashboard
├── notifier.py               # Telegram Bot API formatted alert dispatcher
├── main.py                   # Executive CLI orchestrator (--replay, --stats, --eod, --no-telegram)
├── requirements.txt          # Pinned Python dependencies
├── pytest.ini                # Pytest configuration
├── .env.example              # Secrets and configuration template
├── scripts/
│   └── ablation_shuffle.py   # Empirical position-bias ablation evaluator
└── tests/                    # Comprehensive unit tests
    ├── conftest.py
    ├── data/
    │   └── sample_pack.json  # Canned briefing pack for offline replay
    ├── test_firewall.py      # Citation validation & retry logic tests
    ├── test_shuffler.py      # PRNG shuffler & unblinding tests
    └── test_storage.py       # SQLite trigger & immutability tests
```

---

## 🚀 Quickstart: Python Workflow

### 1. Environment Setup
```bash
git clone https://github.com/HARSHCRR/agent.git
cd agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Key variables:
* `GEMINI_API_KEY`: Google Gemini API Key (defaults to deterministic mock mode if omitted).
* `FMP_API_KEY`: Financial Modeling Prep API Key (optional).
* `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Telegram credentials for live alerts.

### 3. Execution Commands
```bash
# Run the complete live pre-market workflow
python main.py

# Run in offline replay mode with a canned briefing pack (no API key required)
python main.py --replay tests/data/sample_pack.json --no-telegram

# Run in test mode without dispatching Telegram alerts
python main.py --no-telegram

# View forward-testing win rates and performance dashboard
python main.py --stats

# Reconcile post-market outcome at 16:00 ET (e.g. for Oct 12, 2026)
python main.py --eod 2026-10-12
```

---

## 📊 Sample Telegram Pre-Market Alert

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

## 🔬 Ablation Studies & Empirical Bias Measurement

An ablation script (`scripts/ablation_shuffle.py`) measures the sensitivity of the LLM judge to presentation order (swapping `Case X` and `Case Y` on identical inputs) and computes the empirical **Verdict-Flip Rate**:

```bash
# Run ablation study across N evaluations (offline replay mode)
python scripts/ablation_shuffle.py --n 20 --replay tests/data/sample_pack.json

# Run live ablation study with real Gemini API
python scripts/ablation_shuffle.py --n 20
```

---

## 🧪 Testing & CI/CD

The test suite runs automatically on every push via GitHub Actions (`.github/workflows/ci.yml`).

### Running Python Tests (Pytest)
```bash
pytest -v
```
*Tests citation set-membership firewall, edge cases, retry-then-fallback path, PRNG shuffler unblinding, and SQLite append-only triggers (10 unit tests).*

---

## 📈 Performance Tracking & Forward Testing

Pre-market predictions are persisted to an append-only SQLite ledger (`data/verdicts.db`), enforced via triggers preventing `DELETE` operations or alterations to pre-market fields.

```sql
SELECT 
    confidence,
    COUNT(*) AS total_calls,
    ROUND(AVG(is_correct) * 100, 1) AS win_rate_pct
FROM verdicts 
WHERE is_correct IS NOT NULL
GROUP BY confidence;
```

---

## 📊 Forward-Test Results

> *Note: This table tracks forward-tested pre-market predictions evaluated against 16:00 ET market closes.*

| Metric | System Result | Always Bullish Baseline | Yesterday's Direction Baseline | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Evaluated ($N$)** | — | — | — | *Not yet populated ($N < 100$)* |
| **Overall Win Rate** | — | — | — | *Not yet populated* |
| **High Confidence Win Rate** | — | — | — | *Not yet populated* |
| **Medium Confidence Win Rate**| — | — | — | *Not yet populated* |
| **Low Confidence Win Rate** | — | — | — | *Not yet populated* |

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
