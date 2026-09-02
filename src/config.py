"""
config.py – Central configuration loaded from environment variables.
All code imports from here; never read os.getenv() directly elsewhere.

Uses properties so environment variables are read at access time,
not at import time. This ensures Railway/Render injected vars work.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()  # local dev: reads .env file; on Railway: no-op (vars already set)


class _Config:
    """Singleton config that reads env vars lazily (on access, not import)."""

    # ── Alpaca ──────────────────────────────────────────────────────────────
    @property
    def ALPACA_API_KEY(self) -> str:
        return os.getenv("ALPACA_API_KEY", "")

    @property
    def ALPACA_SECRET_KEY(self) -> str:
        return os.getenv("ALPACA_SECRET_KEY", "")

    @property
    def ALPACA_BASE_URL(self) -> str:
        return os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # ── Google Gemini ─────────────────────────────────────────────────────
    @property
    def GEMINI_API_KEY(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    GEMINI_MODEL: str = "gemini-3.6-flash"

    # ── Trading Universe ────────────────────────────────────────────────────
    @property
    def WATCHLIST(self) -> List[str]:
        return os.getenv("WATCHLIST", "AAPL,TSLA,NVDA,MSFT,GOOGL").split(",")

    # ── Risk Limits ─────────────────────────────────────────────────────────
    @property
    def MAX_LOSS_PER_TRADE(self) -> float:
        return float(os.getenv("MAX_LOSS_PER_TRADE", 2000))

    @property
    def MAX_DAILY_LOSS(self) -> float:
        return float(os.getenv("MAX_DAILY_LOSS", 8000))

    @property
    def MAX_POSITIONS(self) -> int:
        return int(os.getenv("MAX_POSITIONS", 8))

    @property
    def MAX_PORTFOLIO_CONCENTRATION(self) -> float:
        return float(os.getenv("MAX_PORTFOLIO_CONCENTRATION", 0.15))

    # ── Position Exit Thresholds ─────────────────────────────────────────────
    @property
    def TAKE_PROFIT_PCT(self) -> float:
        return float(os.getenv("TAKE_PROFIT_PCT", 0.50))

    @property
    def STOP_LOSS_PCT(self) -> float:
        return float(os.getenv("STOP_LOSS_PCT", 0.40))

    @property
    def CLOSE_DTE_THRESHOLD(self) -> int:
        return int(os.getenv("CLOSE_DTE_THRESHOLD", 1))

    # ── Market Hours (Eastern) ──────────────────────────────────────────────
    @property
    def MARKET_OPEN(self) -> str:
        return os.getenv("MARKET_OPEN", "09:30")

    @property
    def MARKET_CLOSE(self) -> str:
        return os.getenv("MARKET_CLOSE", "15:30")

    # ── Agent Schedule ──────────────────────────────────────────────────────
    @property
    def RUN_INTERVAL_MINUTES(self) -> int:
        return int(os.getenv("RUN_INTERVAL_MINUTES", 30))

    # ── Mode ────────────────────────────────────────────────────────────────
    @property
    def DRY_RUN(self) -> bool:
        return os.getenv("DRY_RUN", "false").lower() == "true"

    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    # ── Paths ────────────────────────────────────────────────────────────────
    DATA_DIR             = "data"
    TRADES_LOG           = f"{DATA_DIR}/trades_log.json"
    REFUSED_TRADES_LOG   = f"{DATA_DIR}/refused_trades_log.json"
    SENTIMENT_LOG        = f"{DATA_DIR}/sentiment_log.json"
    PORTFOLIO_HISTORY    = f"{DATA_DIR}/portfolio_history.json"

    # ── Option-selection defaults ────────────────────────────────────────────
    MIN_DTE: int = 7
    MAX_DTE: int = 45
    TARGET_DELTA_MIN: float = 0.30
    TARGET_DELTA_MAX: float = 0.50

    def validate(self) -> bool:
        """Raise ValueError if any required API key is missing."""
        required = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "GEMINI_API_KEY"]
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        return True

    def ensure_data_dir(self) -> None:
        """Create data/ directory if it doesn't exist."""
        os.makedirs(self.DATA_DIR, exist_ok=True)


# Singleton — all other modules do `from .config import Config`
Config = _Config()
