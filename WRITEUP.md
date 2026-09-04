# Sentinel Options — Hackathon One-Page Write-Up

**Project**: Sentinel Options  
**Hackathon**: Alpaca AI Trading Agents Hackathon (lablab.ai)  
**Starting Balance**: $100,000 (Alpaca Paper Trading Account)  
**Core Strategy**: News-driven sentiment trading of At-The-Money (ATM) options (7–45 DTE).

---

## 1. AI Logic (Bounded Signal Generation)

Sentinel Options utilizes AI strictly for unstructured data extraction, ensuring the LLM is isolated from execution and portfolio access. 

1. **Ingestion**: A scraper pulls the 10 most recent headlines per ticker (AAPL, TSLA, NVDA, MSFT, GOOGL) from Google News RSS.
2. **Analysis**: An LLM (Google Gemini) receives the headlines via a structured prompt and outputs a deterministic JSON signal containing a `sentiment` (BULLISH/BEARISH/NEUTRAL), a `confidence` score (0.0 to 1.0), and a `suggested_trade` (CALL/PUT).
3. **Thresholding**: Only signals with a confidence score of **≥ 0.65** are passed downstream to the Trade Proposer. 

*Crucial Design Principle: The AI's role is strictly bounded to signal generation. It never touches money, the broker, or execution logic.*

---

## 2. Risk Gates (Zero AI Involvement)

Between the AI's trade proposal and Alpaca execution sits a strictly deterministic Risk Gate. This layer is written purely in Python math with **zero AI involvement**, ensuring it can veto any AI-proposed trade that violates safety constraints.

The Risk Gate evaluates every proposed option contract against the following hard limits:

| Rule | Threshold |
|------|-----------|
| **Market Hours Check** | Trades execute only when Alpaca's Market Clock reports the market as open. |
| **Max Cost per Trade** | No single trade can cost more than $2,000. |
| **Max Open Positions** | The portfolio cannot exceed 8 concurrent open positions. |
| **Max Daily Loss** | If daily realized losses hit $8,000, the system halts. |
| **Concentration Cap** | No single ticker can make up > 15% of portfolio equity. |
| **Take-Profit / Stop-Loss** | Open positions automatically exit at +50% or -40%. |

If *any* rule fails, the trade is explicitly refused and logged for auditing.

---

## 3. Alpaca Infrastructure

The entire platform is powered by Alpaca's developer ecosystem:

1. **Trading API**: Used to query live option chains (selecting contracts within the 7–45 DTE window) and to submit Limit Orders via paper trading.
2. **Market Data API**: Used to retrieve real-time bid-ask pricing for accurate Limit Order placement at the midpoint.
3. **Official Alpaca CLI Execution**: To fulfill the strict hackathon CLI requirement, order execution explicitly routes through `subprocess` calls to the official Alpaca CLI (`alpaca order submit`). The Alpaca Python SDK is used for market-data and account operations, while order execution is explicitly routed through the official Alpaca CLI.
4. **Audit Logging**: Every action (executed orders and risk-gate refusals) is recorded to a local, append-only JSON audit trail for real-time telemetry rendering on the interactive Streamlit dashboard.
