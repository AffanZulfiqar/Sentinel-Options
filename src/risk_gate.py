"""
risk_gate.py – Deterministic risk gate.

Gemini (or any AI layer) can only *propose* trades.
THIS MODULE makes the final pass/fail decision based on hard rules.
It is intentionally written with no LLM calls – pure Python logic.

Each check returns a (passed: bool, reason: str) tuple.
The gate runs all checks and refuses the trade if ANY fails.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from alpaca.trading.client import TradingClient

from .config import Config
from .logger import get_logger, log_refused_trade

log = get_logger(__name__)


class RiskGate:
    def __init__(self, portfolio_tracker):
        # We need portfolio info to evaluate concentration & daily-loss limits
        self._portfolio = portfolio_tracker
        self._client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)

    # ── public entry point ────────────────────────────────────────────────────

    def approve(self, proposal: Dict) -> Tuple[bool, str]:
        """Run all risk checks.  Returns (True, 'APPROVED') or (False, reason)."""
        checks = [
            self._check_market_hours,
            self._check_position_count,
            self._check_daily_loss_limit,
            self._check_trade_cost,
            self._check_concentration,
            self._check_confidence,
            self._check_liquidity,
            self._check_spread,
            self._check_iv_limit,
        ]
        for check in checks:
            passed, reason = check(proposal)
            if not passed:
                self._record_refusal(proposal, reason)
                return False, reason

        log.info("✅ APPROVED: %s %s", proposal["option_type"].upper(), proposal["ticker"])
        return True, "APPROVED"

    def approve_all(self, proposals: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Split proposals into approved / refused lists."""
        approved, refused = [], []
        for p in proposals:
            ok, reason = self.approve(p)
            if ok:
                p["risk_decision"] = "APPROVED"
                approved.append(p)
            else:
                p["risk_decision"] = "REFUSED"
                p["refusal_reason"] = reason
                refused.append(p)
        return approved, refused

    # ── individual checks ─────────────────────────────────────────────────────

    def _check_market_hours(self, proposal: Dict) -> Tuple[bool, str]:
        """Refuse trades if the Alpaca Market Clock says the market is closed."""
        try:
            clock = self._client.get_clock()
            if not clock.is_open:
                return False, "Market is closed (Alpaca Clock)"
        except Exception as e:
            # If API fails, fail safe (refuse the trade)
            log.error("Failed to check Alpaca Market Clock: %s", e)
            return False, "Market Clock API Error"
            
        return True, ""

    def _check_position_count(self, proposal: Dict) -> Tuple[bool, str]:
        """Refuse if we already have MAX_POSITIONS open positions."""
        count = self._portfolio.open_position_count()
        if count >= Config.MAX_POSITIONS:
            return False, f"Max positions reached ({count}/{Config.MAX_POSITIONS})"
        return True, ""

    def _check_daily_loss_limit(self, proposal: Dict) -> Tuple[bool, str]:
        """Refuse if realised daily loss already hit the limit."""
        daily_loss = self._portfolio.daily_realized_loss()
        if daily_loss >= Config.MAX_DAILY_LOSS:
            return False, f"Daily loss limit hit (${daily_loss:.2f} >= ${Config.MAX_DAILY_LOSS:.2f})"
        return True, ""

    @staticmethod
    def _check_trade_cost(proposal: Dict) -> Tuple[bool, str]:
        """Refuse if estimated trade cost exceeds max-loss-per-trade."""
        cost = proposal.get("estimated_cost", 0)
        if cost > Config.MAX_LOSS_PER_TRADE:
            return False, (
                f"Trade cost ${cost:.2f} exceeds limit ${Config.MAX_LOSS_PER_TRADE:.2f}"
            )
        return True, ""

    def _check_concentration(self, proposal: Dict) -> Tuple[bool, str]:
        """Refuse if adding this trade would exceed per-ticker concentration."""
        ticker      = proposal["ticker"]
        cost        = proposal.get("estimated_cost", 0)
        portfolio_v = self._portfolio.total_value()
        if portfolio_v <= 0:
            return True, ""
        new_exposure = self._portfolio.ticker_exposure(ticker) + cost
        concentration = new_exposure / portfolio_v
        if concentration > Config.MAX_PORTFOLIO_CONCENTRATION:
            return False, (
                f"Concentration {concentration:.1%} > {Config.MAX_PORTFOLIO_CONCENTRATION:.1%} "
                f"for {ticker}"
            )
        return True, ""

    @staticmethod
    def _check_confidence(proposal: Dict) -> Tuple[bool, str]:
        """Refuse if Gemini's sentiment confidence is below threshold."""
        confidence = proposal.get("sentiment", {}).get("confidence", 0)
        if confidence < 0.65:
            return False, f"Confidence {confidence:.2f} < 0.65 threshold"
        return True, ""

    @staticmethod
    def _check_liquidity(proposal: Dict) -> Tuple[bool, str]:
        """Refuse if the option has zero bid or ask (illiquid)."""
        bid = proposal.get("bid", 0)
        ask = proposal.get("ask", 0)
        if bid <= 0 or ask <= 0:
            return False, "Zero liquidity (Bid or Ask is 0.0)"
        return True, ""

    @staticmethod
    def _check_spread(proposal: Dict) -> Tuple[bool, str]:
        """Refuse if the bid-ask spread is greater than 10% of the ask price."""
        bid = proposal.get("bid", 0)
        ask = proposal.get("ask", 0)
        if ask > 0:
            spread_pct = (ask - bid) / ask
            if spread_pct > 0.10:
                return False, f"Spread too wide ({spread_pct:.1%} > 10.0%)"
        return True, ""

    @staticmethod
    def _check_iv_limit(proposal: Dict) -> Tuple[bool, str]:
        """Refuse if Implied Volatility is extremely high (e.g. > 150%)."""
        iv = proposal.get("iv", 0)
        if iv > 1.50:
            return False, f"IV too high ({iv:.1%} > 150.0%)"
        return True, ""

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _record_refusal(proposal: Dict, reason: str) -> None:
        record = {
            "ticker":      proposal.get("ticker"),
            "option_type": proposal.get("option_type"),
            "symbol":      proposal.get("symbol"),
            "cost":        proposal.get("estimated_cost"),
            "reason":      reason,
            "sentiment":   proposal.get("sentiment", {}),
        }
        log.warning("❌ REFUSED %s %s – %s", record["option_type"], record["ticker"], reason)
        log_refused_trade(record)
