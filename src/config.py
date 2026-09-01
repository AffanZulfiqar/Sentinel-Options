"""
config.py – Central configuration loaded from environment variables.
All code imports from here; never read os.getenv() directly elsewhere.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Alpaca ──────────────────────────────────────────────────────────────
    ALPACA_API_KEY:    str = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL:   str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # ── Anthropic Claude ────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL:      str = "claude-3-5-sonnet-20241022"

    # ── Trading Universe ────────────────────────────────────────────────────
    WATCHLIST: List[str] = os.getenv("WATCHLIST", "AAPL,TSLA,NVDA,MSFT,GOOGL").split(",")

    # ── Risk Limits ─────────────────────────────────────────────────────────
    MAX_LOSS_PER_TRADE:          float = float(os.getenv("MAX_LOSS_PER_TRADE", 2000))
    MAX_DAILY_LOSS:              float = float(os.getenv("MAX_DAILY_LOSS", 8000))
    MAX_POSITIONS:               int   = int(os.getenv("MAX_POSITIONS", 8))
    MAX_PORTFOLIO_CONCENTRATION: float = float(os.getenv("MAX_PORTFOLIO_CONCENTRATION", 0.15))

    # ── Position Exit Thresholds ─────────────────────────────────────────────
    # Take-profit: close position when unrealized gain >= this fraction of cost
    TAKE_PROFIT_PCT:      float = float(os.getenv("TAKE_PROFIT_PCT", 0.50))   # 50%
    # Stop-loss: close position when unrealized loss >= this fraction of cost
    STOP_LOSS_PCT:        float = float(os.getenv("STOP_LOSS_PCT",   0.40))   # 40%
    # Near-expiry: close if DTE <= this many days (avoid pin risk / worthless expiry)
    CLOSE_DTE_THRESHOLD:  int   = int(os.getenv("CLOSE_DTE_THRESHOLD", 1))

    # ── Market Hours (Eastern) ──────────────────────────────────────────────
    MARKET_OPEN:  str = os.getenv("MARKET_OPEN",  "09:30")
    MARKET_CLOSE: str = os.getenv("MARKET_CLOSE", "15:30")

    # ── Agent Schedule ──────────────────────────────────────────────────────
    RUN_INTERVAL_MINUTES: int = int(os.getenv("RUN_INTERVAL_MINUTES", 30))

    # ── Mode ────────────────────────────────────────────────────────────────
    DRY_RUN:   bool = os.getenv("DRY_RUN", "false").lower() == "true"
    LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO")

    # ── Paths ────────────────────────────────────────────────────────────────
    DATA_DIR             = "data"
    TRADES_LOG           = f"{DATA_DIR}/trades_log.json"
    REFUSED_TRADES_LOG   = f"{DATA_DIR}/refused_trades_log.json"
    SENTIMENT_LOG        = f"{DATA_DIR}/sentiment_log.json"
    PORTFOLIO_HISTORY    = f"{DATA_DIR}/portfolio_history.json"

    # ── Option-selection defaults ────────────────────────────────────────────
    # Target days-to-expiry window when picking a contract
    MIN_DTE: int = 7
    MAX_DTE: int = 45
    # Target delta range (absolute value)
    TARGET_DELTA_MIN: float = 0.30
    TARGET_DELTA_MAX: float = 0.50

    @classmethod
    def validate(cls) -> bool:
        """Raise ValueError if any required API key is missing."""
        required = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ANTHROPIC_API_KEY"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        return True

    @classmethod
    def ensure_data_dir(cls) -> None:
        """Create data/ directory if it doesn't exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
