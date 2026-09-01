"""
agent_controller.py – Main autonomous loop.

Orchestrates the full pipeline every RUN_INTERVAL_MINUTES:
  1. Fetch news
  2. Analyze sentiment (Claude)
  3. Propose trades (option chain)
  4. Risk gate
  5. Execute approved trades
  6. Snapshot portfolio

Run with:
    python -m src.agent_controller
"""
import signal
import sys
import time
from datetime import datetime

import pytz
import schedule

from .config import Config
from .logger import get_logger
from .news_fetcher import fetch_news_for_watchlist
from .sentiment_analyzer import SentimentAnalyzer
from .trade_proposer import TradeProposer
from .risk_gate import RiskGate
from .trade_executor import TradeExecutor
from .portfolio_tracker import PortfolioTracker
from .position_monitor import PositionMonitor

log = get_logger(__name__)

ET = pytz.timezone("America/New_York")


class AgentController:
    def __init__(self):
        log.info("═" * 60)
        log.info("  News-Sentiment Options Trading Agent  v%s", "1.0.0")
        log.info("  Mode: %s", "DRY RUN" if Config.DRY_RUN else "LIVE PAPER")
        log.info("  Watchlist: %s", ", ".join(Config.WATCHLIST))
        log.info("═" * 60)

        Config.validate()
        Config.ensure_data_dir()

        self.portfolio  = PortfolioTracker()
        self.analyzer   = SentimentAnalyzer()
        self.proposer   = TradeProposer()
        self.risk_gate  = RiskGate(self.portfolio)
        self.executor   = TradeExecutor(self.portfolio)
        self.monitor    = PositionMonitor(self.portfolio)

    # ── main cycle ────────────────────────────────────────────────────────────

    def run_cycle(self) -> None:
        now_et = datetime.now(ET)
        log.info("── Cycle start %s ──", now_et.strftime("%Y-%m-%d %H:%M ET"))

        # 0. Position monitor – close exits before deploying new capital
        log.info("Step 0/5 → Monitoring open positions for exits …")
        closed = self.monitor.run()
        if closed:
            log.info("%d position(s) closed by monitor.", closed)

        # 1. News
        log.info("Step 1/5 → Fetching news …")
        news = fetch_news_for_watchlist(Config.WATCHLIST)

        # 2. Sentiment
        log.info("Step 2/5 → Analyzing sentiment …")
        sentiments = self.analyzer.analyze_all(news)
        if not sentiments:
            log.info("No actionable sentiment signals – skipping cycle.")
            return

        # 3. Trade proposals
        log.info("Step 3/5 → Building trade proposals …")
        proposals = self.proposer.propose_all(sentiments)
        if not proposals:
            log.info("No trade proposals generated.")
            # Still snapshot portfolio
        else:
            # 4. Risk gate
            log.info("Step 4/5 → Running risk gate on %d proposal(s) …", len(proposals))
            approved, refused = self.risk_gate.approve_all(proposals)
            log.info(
                "Risk gate result: %d approved, %d refused",
                len(approved), len(refused),
            )

            # 5. Execute
            if approved:
                log.info("Step 5/5 → Executing %d trade(s) …", len(approved))
                self.executor.execute_all(approved)
            else:
                log.info("Step 5/5 → No trades to execute.")

        # Always snapshot
        snap = self.portfolio.snapshot()
        log.info(
            "Portfolio snapshot: equity=$%.2f, cash=$%.2f, positions=%d",
            snap.get("equity", 0), snap.get("cash", 0), snap.get("open_positions", 0),
        )
        log.info("── Cycle complete ──\n")

    # ── scheduler ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduled loop.  Blocks until interrupted."""
        log.info(
            "Scheduling agent to run every %d minutes …",
            Config.RUN_INTERVAL_MINUTES,
        )
        # Run immediately on start
        self.run_cycle()

        schedule.every(Config.RUN_INTERVAL_MINUTES).minutes.do(self.run_cycle)

        def _handle_sigint(sig, frame):
            log.info("Received SIGINT – shutting down gracefully.")
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_sigint)

        while True:
            schedule.run_pending()
            time.sleep(30)


def main():
    controller = AgentController()
    controller.start()


if __name__ == "__main__":
    main()
