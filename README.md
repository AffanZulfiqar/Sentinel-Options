# Sentinel Options

An autonomous options trading agent that monitors news sentiment and executes options trades on Alpaca Paper Trading.

## How it works

The agent runs on a 30-minute loop during market hours. Each cycle it:

1. Pulls recent headlines from Google News for a configurable watchlist of tickers
2. Sends them through Claude (Anthropic) to get a structured sentiment signal — bullish, bearish, neutral — along with a confidence score
3. Looks up the live option chain on Alpaca and selects the nearest ATM contract in the 7–45 DTE window
4. Runs the proposal through a deterministic risk gate before anything gets placed
5. Submits a DAY limit order at the bid-ask midpoint if the gate passes
6. At the start of every cycle, checks open positions and closes any that have hit the take-profit, stop-loss, or near-expiry thresholds

The design principle is simple: the AI reads and interprets, the code decides and acts. Claude has no ability to place orders or bypass any of the risk checks.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ANTHROPIC_API_KEY=...
```

Verify your Alpaca connection:

```bash
python scripts/setup_alpaca.py
```

## Running

Start the trading agent:

```bash
python -m src.agent_controller
```

Launch the dashboard (separate terminal):

```bash
streamlit run dashboard/dashboard.py
```

## Risk controls

All limits are enforced in `src/risk_gate.py`. None of them can be overridden by the AI layer.

| Control | Value |
|---------|-------|
| Max loss per trade | $2,000 |
| Max daily loss | $8,000 |
| Max open positions | 8 |
| Max concentration per ticker | 15% |
| Market hours | 09:30–15:30 ET |
| Min sentiment confidence | 0.65 |

Position exits are handled separately in `src/position_monitor.py`:

| Rule | Threshold |
|------|-----------|
| Take-profit | +50% unrealized gain |
| Stop-loss | -40% unrealized loss |
| Near-expiry close | DTE ≤ 1 day |

## Project structure

```
src/
  agent_controller.py   – main loop and scheduler
  config.py             – environment config
  news_fetcher.py       – Google News RSS
  sentiment_analyzer.py – Claude integration
  trade_proposer.py     – option chain selection (live ATM targeting)
  risk_gate.py          – deterministic risk checks
  position_monitor.py   – exit logic (take-profit, stop-loss, expiry)
  trade_executor.py     – Alpaca order placement
  portfolio_tracker.py  – P&L and position tracking
  logger.py             – JSON audit log

dashboard/
  dashboard.py          – Streamlit UI

scripts/
  setup_alpaca.py       – credential validation
  test_trade.py         – single test order
  reset_account.py      – paper account reset helper

data/                   – runtime JSON logs (git-ignored)
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `ALPACA_API_KEY` | Alpaca paper trading key |
| `ALPACA_SECRET_KEY` | Alpaca paper trading secret |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `WATCHLIST` | Comma-separated tickers (default: AAPL,TSLA,NVDA,MSFT,GOOGL) |
| `DRY_RUN` | Set to `true` to log trades without submitting orders |
| `TAKE_PROFIT_PCT` | Exit threshold for gains (default: 0.50) |
| `STOP_LOSS_PCT` | Exit threshold for losses (default: 0.40) |

## License

MIT
