"""
test_trade.py – Place a single test options trade to verify the full pipeline.

Useful for verifying everything works before running the autonomous agent.

    python scripts/test_trade.py --ticker AAPL --type call --dry-run
    python scripts/test_trade.py --ticker AAPL --type call
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Place a single test options trade.")
    parser.add_argument("--ticker",  default="AAPL",  help="Ticker symbol (default: AAPL)")
    parser.add_argument("--type",    default="call",   choices=["call","put"], help="Option type")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without placing order")
    args = parser.parse_args()

    # Override DRY_RUN if flag set
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    from src.config import Config
    Config.validate()

    print(f"🔬 Test trade: {args.type.upper()} on {args.ticker} | DRY_RUN={Config.DRY_RUN}")

    from src.portfolio_tracker import PortfolioTracker
    from src.trade_proposer import TradeProposer
    from src.risk_gate import RiskGate
    from src.trade_executor import TradeExecutor

    portfolio = PortfolioTracker()
    proposer  = TradeProposer()
    gate      = RiskGate(portfolio)
    executor  = TradeExecutor(portfolio)

    # Build a mock sentiment signal
    mock_sentiment = {
        "ticker":          args.ticker,
        "sentiment":       "BULLISH" if args.type == "call" else "BEARISH",
        "confidence":      0.80,
        "reasoning":       "Test trade – manually triggered.",
        "key_headlines":   [],
        "suggested_trade": args.type.upper(),
    }

    print("\n1. Proposing trade from option chain …")
    proposal = proposer.propose(mock_sentiment)
    if not proposal:
        print("❌ No suitable option contract found.")
        sys.exit(1)
    print(f"   Proposal: {proposal['symbol']} exp={proposal['expiration']} strike={proposal['strike']} cost=${proposal['estimated_cost']:.2f}")

    print("\n2. Running risk gate …")
    ok, reason = gate.approve(proposal)
    print(f"   Result: {'✅ APPROVED' if ok else '❌ REFUSED – ' + reason}")

    if ok:
        print("\n3. Executing trade …")
        result = executor.execute(proposal)
        if result:
            print(f"   Order: {result.get('order_id')} status={result.get('status')}")
        else:
            print("   ❌ Execution failed.")

    print("\nDone.")


if __name__ == "__main__":
    main()
