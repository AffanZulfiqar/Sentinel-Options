"""
portfolio_tracker.py – Tracks positions, P&L, and account metrics via Alpaca.

Used by the risk gate and dashboard.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass

from .config import Config
from .logger import get_logger, log_portfolio_snapshot

log = get_logger(__name__)


class PortfolioTracker:
    def __init__(self):
        self._client = TradingClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper=True,
        )
        # Intra-day running loss tracking (resets on new day)
        self._today          = date.today()
        self._daily_loss_usd = 0.0

    # ── account info ──────────────────────────────────────────────────────────

    def account(self) -> Dict:
        try:
            acct = self._client.get_account()
            return {
                "equity":          float(acct.equity or 0),
                "cash":            float(acct.cash or 0),
                "buying_power":    float(acct.buying_power or 0),
                "portfolio_value": float(acct.portfolio_value or 0),
            }
        except Exception as exc:
            log.error("Failed to fetch account: %s", exc)
            return {"equity": 0, "cash": 0, "buying_power": 0, "portfolio_value": 0}

    def total_value(self) -> float:
        return self.account()["portfolio_value"]

    # ── positions ────────────────────────────────────────────────────────────

    def open_positions(self) -> List[Dict]:
        try:
            positions = self._client.get_all_positions()
            return [
                {
                    "symbol":      p.symbol,
                    "qty":         float(p.qty or 0),
                    "avg_cost":    float(p.avg_entry_price or 0),
                    "market_val":  float(p.market_value or 0),
                    "unrealized_pl": float(p.unrealized_pl or 0),
                    "asset_class": str(p.asset_class),
                }
                for p in positions
            ]
        except Exception as exc:
            log.error("Failed to fetch positions: %s", exc)
            return []

    def open_position_count(self) -> int:
        return len(self.open_positions())

    def ticker_exposure(self, ticker: str) -> float:
        """Total market value of all positions in *ticker* (options + stock)."""
        total = 0.0
        for p in self.open_positions():
            if p["symbol"].startswith(ticker):
                total += abs(p["market_val"])
        return total

    # ── daily loss tracking ───────────────────────────────────────────────────

    def record_loss(self, amount: float) -> None:
        """Call this when a trade is closed at a loss."""
        if date.today() != self._today:
            # New trading day – reset counter
            self._today          = date.today()
            self._daily_loss_usd = 0.0
        if amount > 0:
            self._daily_loss_usd += amount
            log.info("Daily loss updated: $%.2f / $%.2f", self._daily_loss_usd, Config.MAX_DAILY_LOSS)

    def daily_realized_loss(self) -> float:
        if date.today() != self._today:
            return 0.0
        return self._daily_loss_usd

    # ── snapshots ─────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict:
        """Take a full snapshot and persist it to the portfolio history log."""
        acct      = self.account()
        positions = self.open_positions()
        record    = {**acct, "open_positions": len(positions), "positions": positions}
        log_portfolio_snapshot(record)
        return record
