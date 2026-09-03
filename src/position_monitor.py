"""
position_monitor.py – Monitors open option positions and closes them
when exit criteria are met.

Exit rules (deterministic, no AI involvement):
  - Take-profit : unrealized P&L >= +TAKE_PROFIT_PCT  (default 50%)
  - Stop-loss   : unrealized P&L <= -STOP_LOSS_PCT    (default 40%)
  - Near-expiry : DTE <= CLOSE_DTE_THRESHOLD days     (default 3)

Runs as part of every agent cycle BEFORE the news/trade loop so that
capital is freed up before new proposals are evaluated.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from .config import Config
from .logger import get_logger, log_trade

log = get_logger(__name__)


class PositionMonitor:
    """Checks every open option position and closes those hitting exit rules."""

    def __init__(self, portfolio_tracker):
        self._client = TradingClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper=True,
        )
        self._portfolio = portfolio_tracker

    # ── public ───────────────────────────────────────────────────────────────

    def run(self) -> int:
        """Evaluate all open option positions. Returns count of positions closed."""
        positions = self._portfolio.open_positions()
        # Filter to options only: OCC symbols contain C or P after at least 6 chars
        option_positions = [
            p for p in positions
            if self._is_option(p["symbol"])
        ]

        if not option_positions:
            log.info("PositionMonitor: no open option positions to evaluate.")
            return 0

        log.info("PositionMonitor: evaluating %d option position(s) …", len(option_positions))
        closed = 0
        for pos in option_positions:
            should_close, reason = self._should_close(pos)
            if should_close:
                success = self._close_position(pos, reason)
                if success:
                    closed += 1

        log.info("PositionMonitor: closed %d position(s) this cycle.", closed)
        return closed

    # ── exit decision ─────────────────────────────────────────────────────────

    def _should_close(self, pos: Dict) -> Tuple[bool, str]:
        """Return (True, reason) if position should be closed, else (False, '')."""
        avg_cost   = pos["avg_cost"]
        qty        = pos["qty"]
        unrealized = pos["unrealized_pl"]
        symbol     = pos["symbol"]

        cost_basis = avg_cost * qty * 100  # option multiplier
        if cost_basis <= 0:
            return False, ""

        pct_change = unrealized / cost_basis

        # Take-profit
        if pct_change >= Config.TAKE_PROFIT_PCT:
            return True, f"Take-profit hit ({pct_change:.1%} gain)"

        # Stop-loss
        if pct_change <= -Config.STOP_LOSS_PCT:
            return True, f"Stop-loss hit ({pct_change:.1%} loss)"

        # Near-expiry: parse expiry from OCC symbol
        expiry = self._parse_expiry(symbol)
        if expiry is not None:
            dte = (expiry - date.today()).days
            if dte <= Config.CLOSE_DTE_THRESHOLD:
                return True, f"Near-expiry (DTE={dte})"

        return False, ""

    # ── order submission ──────────────────────────────────────────────────────

    def _close_position(self, pos: Dict, reason: str) -> bool:
        """Submit a market sell order to close the position."""
        symbol = pos["symbol"]
        qty    = int(pos["qty"])

        log.info("🔔 Closing %s x%d – %s", symbol, qty, reason)

        if Config.DRY_RUN:
            log.info("[DRY RUN] Would sell %d x %s", qty, symbol)
            self._record_close(pos, reason, order_id="DRY_RUN", status="simulated")
            if pos["unrealized_pl"] < 0:
                self._portfolio.record_loss(abs(pos["unrealized_pl"]))
            return True

        try:
            req = MarketOrderRequest(
                symbol        = symbol,
                qty           = qty,
                side          = OrderSide.SELL,
                time_in_force = TimeInForce.DAY,
            )
            order = self._client.submit_order(req)
            log.info(
                "✅ Close order submitted: %s qty=%d id=%s status=%s reason=%s",
                symbol, qty, order.id, order.status, reason,
            )
            self._record_close(pos, reason, order_id=str(order.id), status=str(order.status))
            if pos["unrealized_pl"] < 0:
                self._portfolio.record_loss(abs(pos["unrealized_pl"]))
            return True

        except Exception as exc:
            log.error("Failed to close position %s: %s", symbol, exc)
            return False

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_option(symbol: str) -> bool:
        """Heuristic: OCC option symbols are longer than 6 chars and contain C or P."""
        return len(symbol) > 6 and any(ch in symbol[6:] for ch in ("C", "P"))

    @staticmethod
    def _parse_expiry(symbol: str) -> Optional[date]:
        """
        Parse expiry date from OCC option symbol.
        Format: AAPL260117C00200000
                      ^^^^^^ YYMMDD immediately before C or P
        """
        try:
            for i, ch in enumerate(symbol):
                if ch in ("C", "P") and i >= 6:
                    date_str = symbol[i - 6: i]   # 6 chars before C/P = YYMMDD
                    year  = 2000 + int(date_str[0:2])
                    month = int(date_str[2:4])
                    day   = int(date_str[4:6])
                    return date(year, month, day)
        except Exception:
            pass
        return None

    @staticmethod
    def _record_close(pos: Dict, reason: str, order_id: str, status: str) -> None:
        record = {
            "action":        "CLOSE",
            "order_id":      order_id,
            "status":        status,
            "symbol":        pos["symbol"],
            "qty":           pos["qty"],
            "avg_cost":      pos["avg_cost"],
            "market_val":    pos["market_val"],
            "unrealized_pl": pos["unrealized_pl"],
            "close_reason":  reason,
            "dry_run":       Config.DRY_RUN,
        }
        log_trade(record)
