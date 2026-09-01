"""
trade_executor.py – Places options orders through Alpaca Paper Trading.

Supports DRY_RUN mode where orders are logged but never submitted.
"""
from __future__ import annotations

from typing import Dict, Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from .config import Config
from .logger import get_logger, log_trade

log = get_logger(__name__)


class TradeExecutor:
    def __init__(self, portfolio_tracker=None):
        self._client    = TradingClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper=True,
        )
        self._portfolio = portfolio_tracker   # used to update daily-loss on fill

    # ── public ───────────────────────────────────────────────────────────────

    def execute(self, proposal: Dict) -> Optional[Dict]:
        """Submit a market order for *proposal*.

        Returns an order record dict or None on failure.
        """
        symbol    = proposal["symbol"]       # OCC option symbol
        qty       = proposal["contracts"]
        mid_price = proposal["mid_price"]

        if Config.DRY_RUN:
            log.info("[DRY RUN] Would buy %d x %s @ $%.2f", qty, symbol, mid_price)
            record = self._build_record(proposal, order_id="DRY_RUN", status="simulated")
            log_trade(record)
            return record

        try:
            # Use a limit order at the mid-price for better fills
            req = LimitOrderRequest(
                symbol       = symbol,
                qty          = qty,
                side         = OrderSide.BUY,
                time_in_force= TimeInForce.DAY,
                limit_price  = round(mid_price, 2),
            )
            order = self._client.submit_order(req)
            log.info(
                "✅ Order submitted: %s qty=%d id=%s status=%s",
                symbol, qty, order.id, order.status,
            )
            record = self._build_record(proposal, order_id=str(order.id), status=str(order.status))
            log_trade(record)
            return record

        except Exception as exc:
            log.error("Failed to submit order for %s: %s", symbol, exc)
            return None

    def execute_all(self, approved_proposals: list) -> list:
        results = []
        for p in approved_proposals:
            r = self.execute(p)
            if r:
                results.append(r)
        return results

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_record(proposal: Dict, order_id: str, status: str) -> Dict:
        return {
            "order_id":      order_id,
            "status":        status,
            "ticker":        proposal["ticker"],
            "option_type":   proposal["option_type"],
            "symbol":        proposal["symbol"],
            "expiration":    proposal["expiration"],
            "strike":        proposal["strike"],
            "contracts":     proposal["contracts"],
            "mid_price":     proposal["mid_price"],
            "estimated_cost":proposal["estimated_cost"],
            "sentiment":     proposal.get("sentiment", {}),
            "dry_run":       Config.DRY_RUN,
        }
