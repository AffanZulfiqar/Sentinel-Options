"""
trade_proposer.py – Converts a sentiment signal into a concrete options trade proposal.

Fetches the live option chain from Alpaca and selects the best contract
matching our DTE and delta targets.

A proposal dict:
  {
    "ticker":          str,
    "option_type":     "call" | "put",
    "symbol":          str,         # OCC symbol, e.g. "AAPL260117C00200000"
    "expiration":      str,         # YYYY-MM-DD
    "strike":          float,
    "bid":             float,
    "ask":             float,
    "mid_price":       float,
    "contracts":       int,
    "estimated_cost":  float,       # mid_price * 100 * contracts
    "sentiment":       dict,        # original sentiment payload
  }
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Dict, List, Optional

from alpaca.trading.client import TradingClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest, StockLatestQuoteRequest
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import ContractType

from .config import Config
from .logger import get_logger

log = get_logger(__name__)


class TradeProposer:
    def __init__(self):
        self._trading = TradingClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper=True,
        )
        self._stock_data = StockHistoricalDataClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
        )
        self._option_data = OptionHistoricalDataClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
        )

    # ── public ───────────────────────────────────────────────────────────────

    def propose(self, sentiment: Dict) -> Optional[Dict]:
        """Return a trade proposal for *sentiment* or None if no good contract found."""
        ticker      = sentiment["ticker"]
        trade_dir   = sentiment.get("suggested_trade")   # "CALL" | "PUT" | None

        if not trade_dir:
            return None

        option_type = trade_dir.lower()   # "call" or "put"

        # Date window
        today      = date.today()
        min_expiry = today + timedelta(days=Config.MIN_DTE)
        max_expiry = today + timedelta(days=Config.MAX_DTE)

        # Fetch live spot price for true ATM selection
        spot_price = self._get_spot_price(ticker)
        if spot_price:
            log.info("Spot price for %s: $%.2f", ticker, spot_price)
        else:
            log.warning("No spot price for %s – falling back to median strike.", ticker)

        try:
            req = GetOptionContractsRequest(
                underlying_symbols=[ticker],
                expiration_date_gte=min_expiry,
                expiration_date_lte=max_expiry,
                type=ContractType.CALL if option_type == "call" else ContractType.PUT,
                limit=200,
            )
            contracts = self._trading.get_option_contracts(req)
        except Exception as exc:
            log.error("Failed to fetch option chain for %s: %s", ticker, exc)
            return None

        if not contracts or not contracts.option_contracts:
            log.warning("No option contracts found for %s (%s)", ticker, option_type)
            return None

        # Pick the contract closest to ATM within our DTE range
        best = self._select_best_contract(contracts.option_contracts, spot_price)
        if not best:
            return None

        # Use close_price as starting point; try live quote for fresher bid/ask
        mid = float(best.close_price or 0)
        bid, ask = 0.0, 0.0
        try:
            quote = self._get_option_quote(best.symbol)
            if quote:
                bid = float(quote.bid_price or 0)
                ask = float(quote.ask_price or 0)
                if bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
        except Exception:
            pass  # fall back to close_price

        if mid <= 0:
            log.warning("Cannot determine price for %s contract.", ticker)
            return None

        contracts_qty = max(1, math.floor(Config.MAX_LOSS_PER_TRADE / (mid * 100)))
        contracts_qty = min(contracts_qty, 20)   # hard cap

        proposal = {
            "ticker":         ticker,
            "option_type":    option_type,
            "symbol":         best.symbol,
            "expiration":     str(best.expiration_date),
            "strike":         float(best.strike_price or 0),
            "bid":            bid,
            "ask":            ask,
            "mid_price":      mid,
            "contracts":      contracts_qty,
            "estimated_cost": round(mid * 100 * contracts_qty, 2),
            "sentiment":      sentiment,
        }
        log.info(
            "Proposed %s %s (exp=%s strike=%.2f cost=$%.2f)",
            option_type.upper(), ticker,
            proposal["expiration"], proposal["strike"], proposal["estimated_cost"],
        )
        return proposal

    def propose_all(self, sentiments: List[Dict]) -> List[Dict]:
        """Return proposals for every sentiment signal that has a trade direction."""
        proposals = []
        for s in sentiments:
            p = self.propose(s)
            if p:
                proposals.append(p)
        return proposals

    # ── private ──────────────────────────────────────────────────────────────

    def _get_option_quote(self, symbol: str) -> Optional[object]:
        """Fetch the latest quote for an option symbol."""
        try:
            req = OptionLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._option_data.get_option_latest_quote(req)
            return quotes.get(symbol)
        except Exception as exc:
            log.debug("Could not fetch option quote for %s: %s", symbol, exc)
            return None

    def _get_spot_price(self, ticker: str) -> Optional[float]:
        """Fetch the latest ask price for *ticker* from Alpaca market data."""
        try:
            req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quotes = self._stock_data.get_stock_latest_quote(req)
            q = quotes.get(ticker)
            if q:
                # Use mid of bid/ask, fall back to ask or bid
                bid = float(q.bid_price or 0)
                ask = float(q.ask_price or 0)
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
                return ask or bid
        except Exception as exc:
            log.warning("Could not fetch spot price for %s: %s", ticker, exc)
        return None

    def _select_best_contract(self, contracts, spot_price: Optional[float]):
        """
        Select the best contract:
        1. If spot_price is available, find the strike closest to spot (ATM).
           Among ties, prefer contracts within the configured delta range if
           delta is available, and prioritize contracts with Open Interest > 0.
        2. Without spot_price, fall back to the median-strike heuristic.
        """
        if not contracts:
            return None

        try:
            sorted_c = sorted(contracts, key=lambda c: float(c.strike_price or 0))

            if spot_price and spot_price > 0:
                # Find contract with strike closest to spot
                def atm_distance(c):
                    return abs(float(c.strike_price or 0) - spot_price)

                def score(c):
                    dist = atm_distance(c)
                    delta = abs(float(getattr(c, "delta", 0) or 0))
                    in_range = Config.TARGET_DELTA_MIN <= delta <= Config.TARGET_DELTA_MAX
                    
                    # Check for basic liquidity via open interest (if available)
                    oi = float(getattr(c, "open_interest", 0) or 0)
                    has_liquidity = oi > 0
                    
                    # Score tuple: 
                    # 1. Dist to ATM (lower is better)
                    # 2. Has liquidity (0 is better than 1)
                    # 3. Delta in range (0 is better than 1)
                    return (dist, 0 if has_liquidity else 1, 0 if in_range else 1)

                return min(sorted_c, key=score)
            else:
                # Fallback: median strike
                return sorted_c[len(sorted_c) // 2]

        except Exception as exc:
            log.warning("Contract selection error: %s", exc)
            return contracts[0] if contracts else None
