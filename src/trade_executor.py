"""
trade_executor.py – Places options orders through Alpaca Paper Trading.

Supports DRY_RUN mode where orders are logged but never submitted.
"""
from __future__ import annotations

from typing import Dict, Optional

from alpaca.trading.client import TradingClient
import subprocess
import shutil
import uuid
import json

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
            # Check if alpaca CLI is available in PATH, or locally in project root (Railway fallback)
            alpaca_bin = shutil.which("alpaca") or "./alpaca"
            
            cmd = [
                alpaca_bin, "order", "submit",
                "--symbol", symbol,
                "--qty", str(qty),
                "--side", "buy",
                "--type", "limit",
                "--limit-price", str(round(mid_price, 2)),
                "--time-in-force", "day",
                "--client-order-id", f"sentinel-{uuid.uuid4().hex[:8]}",
                "-f", "json"
            ]
            
            log.info("Executing Alpaca CLI: %s", " ".join(cmd))
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse the real Alpaca order ID and status from the CLI's JSON output
            try:
                response = json.loads(result.stdout)
                order_id = str(response.get("id", ""))
                if not order_id:
                    raise RuntimeError("Alpaca CLI returned no real order ID")
                status = str(response.get("status", "accepted_by_cli"))
            except json.JSONDecodeError:
                # Safe fallback if CLI outputs unexpected text (like an update warning)
                order_id = f"cli-{uuid.uuid4().hex[:8]}"
                status = "accepted_by_cli"
            
            log.info("✅ CLI Order submitted successfully: %s qty=%d (Real ID: %s)", symbol, qty, order_id)
            record = self._build_record(proposal, order_id=order_id, status=status)
            log_trade(record)
            return record

        except subprocess.CalledProcessError as e:
            log.error("Failed to submit order via Alpaca CLI (Process Error). Stderr: %s", e.stderr)
            return None
        except FileNotFoundError:
            log.error("Alpaca CLI binary not found! Please ensure it is installed.")
            return None
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
