# ⚡ Sentinel Options

**Autonomous AI Options Trading Agent — Alpaca × lablab.ai Hackathon 2026**

> AI reads the news. Code picks the contract. Math decides the risk. No human in the loop.

Sentinel Options is a fully autonomous options trading agent that ingests real-time financial news, extracts actionable sentiment signals using an LLM, selects ATM option contracts via the Alpaca Trading API, enforces strict deterministic risk controls, and executes paper trades — all without human intervention.

**Live Dashboard**: [Railway Deployment URL]  
**Hackathon**: Alpaca AI Trading Agents Hackathon (Aug 28 – Sep 4, 2026)  
**Starting Balance**: $100,000 (Alpaca Paper Trading)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINEL OPTIONS ENGINE                       │
│                   (runs every 30 minutes)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐   ┌──────────┐   ┌──────────────┐               │
│   │ Step 0   │   │ Step 1   │   │   Step 2     │               │
│   │ Position │──▶│  News    │──▶│    NLP       │               │
│   │ Monitor  │   │ Scraper  │   │  Sentiment   │               │
│   └──────────┘   └──────────┘   └──────┬───────┘               │
│        │              │                 │                        │
│   Check exits    Google News     LLM structured                 │
│   TP/SL/Expiry   RSS feeds      JSON analysis                   │
│                                        │                        │
│                                        ▼                        │
│   ┌──────────┐   ┌──────────┐   ┌──────────────┐               │
│   │ Step 5   │   │ Step 4   │   │   Step 3     │               │
│   │ Alpaca   │◀──│  Risk    │◀──│    Trade     │               │
│   │ Executor │   │  Gate    │   │   Proposer   │               │
│   └──────────┘   └──────────┘   └──────────────┘               │
│        │              │                 │                        │
│  Official CLI    Deterministic     ATM option                   │
│  → Trading API   mathematical      selection                    │
│  → Paper Acct    rules (NO AI)     7-45 DTE                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principle

**The AI is the least-trusted component.** It can only read news and output a structured JSON signal. It has no access to the broker, no ability to place orders, and no way to bypass the risk gate. Every dollar decision is made by deterministic code.

---

## Pipeline Details

### Step 0 — Position Monitor
Scans all open option positions before deploying new capital. Automatically closes positions that have hit:
- **Take-profit**: +50% unrealized gain
- **Stop-loss**: -40% unrealized loss
- **Near-expiry**: ≤ 1 day until expiration

### Step 1 — News Scraper
Pulls 10 recent headlines per ticker from **Google News RSS** for each symbol in the watchlist (AAPL, TSLA, NVDA, MSFT, GOOGL).

### Step 2 — NLP Sentiment Analyzer
Sends headlines to an LLM with a structured prompt. The model returns a JSON object:
```json
{
  "sentiment": "BULLISH",
  "confidence": 0.82,
  "suggested_trade": "CALL",
  "reasoning": "Multiple sources report strong Q3 earnings beat..."
}
```
Only signals with **confidence ≥ 0.65** proceed to trade proposal.

### Step 3 — Trade Proposer
Queries the **Alpaca Trading API** for the live option chain. Selects the nearest at-the-money (ATM) contract within a 7–45 DTE window. Calculates position size based on risk limits.

### Step 4 — Deterministic Risk Gate
Pure mathematical rules — **no AI in this layer**:

| Rule | Threshold |
|------|-----------|
| Market hours only | 09:30–15:30 ET |
| Max cost per trade | $2,000 |
| Max open positions | 8 |
| Max daily loss | $8,000 |
| Single-ticker concentration | ≤ 25% of portfolio |
| Min sentiment confidence | 0.65 |

### Step 5 — Alpaca Executor
The execution path guarantees compliance by explicitly routing the trade through the official Alpaca CLI. The pipeline flow is:
`Python Trade Executor` → `Alpaca Official CLI (subprocess)` → `Alpaca Trading API` → `Paper Account`.
Logs the real Alpaca order ID and full trade details to an append-only JSON audit trail.

---

## Live Dashboard

The Streamlit dashboard provides:

- **Real-time portfolio equity curve** with Plotly charts
- **Metric cards**: equity, P&L, executed trades, risk gate refusals, open positions
- **Scrolling sentiment ticker** with live signal data
- **Architecture & Pipeline tab** documenting the full system for judges
- **Risk Gate Audit tab** showing every refused trade with reasons
- **Sentiment Intelligence tab** with per-ticker breakdown charts
- **Interactive AI Sandbox** — test any ticker on-demand through the full pipeline
- **One-click cycle trigger** — run the full 6-stage pipeline from the UI

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Broker | Alpaca Trading API (Paper) |
| Market Data | Alpaca Market Data API |
| NLP Engine | LLM (structured sentiment extraction) |
| News Source | Google News RSS |
| Risk Layer | Deterministic Python (no AI) |
| Dashboard | Streamlit + Plotly |
| Deployment | Railway |
| Logging | JSON audit trail |

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file:

```
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
GEMINI_API_KEY=your_key
```

Verify connection:

```bash
python scripts/setup_alpaca.py
```

### Alpaca CLI Dependency
Order execution strictly requires the official Alpaca CLI, which is explicitly called via `subprocess.run()`. Since it is a system binary, it is not included in `requirements.txt`.

To install it locally for testing:
- **macOS/Linux**: `brew install alpacahq/tap/cli` (or download the binary from the [Alpaca GitHub Release page](https://github.com/alpacahq/cli/releases))
- **Windows**: Download the `.exe` from the [GitHub Release page](https://github.com/alpacahq/cli/releases) and place `alpaca.exe` in this project's root folder.

*Note: For cloud deployments (like Railway), the CLI binary is automatically downloaded during the build step (or gracefully ignored if the environment does not support it).*

## Running

You can interact with Sentinel Options via the **Dashboard** or the **Operator Tool**.

### 1. The Operator Tool (Local Management)
Order execution strictly routes through **Alpaca's official CLI** (`alpaca order submit`) to fulfill the hackathon compliance requirement. `operator.py` is a separate, dedicated operator tool used for quick status checks and manual analysis.

```bash
# Check your Alpaca portfolio status
python operator.py status

# Run sentiment analysis on a specific ticker
python operator.py analyze AAPL

# Trigger one full autonomous pipeline cycle
python operator.py run
```

### 2. The Dashboard & Background Agent
Launch the interactive dashboard (separate terminal):

```bash
streamlit run dashboard/dashboard.py
```

Start the autonomous agent in the background (runs every 30 mins):

```bash
python -m src.agent_controller
```

---

## Project Structure

```
src/
  agent_controller.py   – main autonomous loop & scheduler
  config.py             – environment config & validation
  news_fetcher.py       – Google News RSS scraper
  sentiment_analyzer.py – LLM sentiment extraction
  trade_proposer.py     – Alpaca option chain selection (ATM targeting)
  risk_gate.py          – deterministic risk checks (no AI)
  position_monitor.py   – exit logic (take-profit, stop-loss, expiry)
  trade_executor.py     – Alpaca order placement
  portfolio_tracker.py  – P&L and position tracking
  logger.py             – JSON audit log

dashboard/
  dashboard.py          – Streamlit interactive dashboard

scripts/
  setup_alpaca.py       – credential validation
  test_trade.py         – single test order
  reset_account.py      – paper account reset

data/                   – runtime JSON logs (git-ignored)
```

## License

MIT
