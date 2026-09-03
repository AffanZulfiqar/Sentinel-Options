import argparse
import sys
import json
from src.config import Config
from src.news_fetcher import NewsFetcher
from src.sentiment_analyzer import SentimentAnalyzer
from src.trade_proposer import TradeProposer
from src.risk_gate import RiskGate
from src.trade_executor import TradeExecutor
from src.portfolio_tracker import PortfolioTracker


def print_banner():
    print("=========================================")
    print("      Sentinel Options Agent CLI         ")
    print("=========================================")


def analyze_ticker(ticker: str):
    print(f"Fetching news for {ticker}...")
    fetcher = NewsFetcher()
    articles = fetcher.fetch_for_ticker(ticker)
    
    if not articles:
        print(f"No articles found for {ticker}.")
        return

    print(f"Found {len(articles)} articles. Analyzing sentiment...")
    analyzer = SentimentAnalyzer()
    sentiment = analyzer.analyze(ticker, articles)
    
    if not sentiment:
        print("Analysis failed or returned empty (possibly due to API limits).")
        return
        
    print("\n--- Sentiment Result ---")
    print(f"Ticker:     {sentiment.get('ticker')}")
    print(f"Sentiment:  {sentiment.get('sentiment')}")
    print(f"Confidence: {sentiment.get('confidence')}")
    print(f"Trade:      {sentiment.get('suggested_trade')}")
    print(f"Reasoning:  {sentiment.get('reasoning')}")


def run_full_cycle():
    print("Running full autonomous cycle from CLI...\n")
    import src.agent_controller
    # The agent controller runs an infinite schedule loop if run as main,
    # but we can just trigger one cycle.
    src.agent_controller.run_cycle()
    print("\nCycle complete. Check the data/logs for details.")


def main():
    parser = argparse.ArgumentParser(description="Sentinel Options Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: analyze
    parser_analyze = subparsers.add_parser("analyze", help="Analyze a specific ticker")
    parser_analyze.add_argument("ticker", type=str, help="Stock ticker symbol (e.g. AAPL)")

    # Command: run
    parser_run = subparsers.add_parser("run", help="Run one full autonomous trading cycle")

    # Command: status
    parser_status = subparsers.add_parser("status", help="Check Alpaca portfolio status")

    args = parser.parse_args()

    print_banner()

    if args.command == "analyze":
        analyze_ticker(args.ticker.upper())
    elif args.command == "run":
        run_full_cycle()
    elif args.command == "status":
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        
        client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)
        acct = client.get_account()
        
        print(f"Portfolio Value: ${float(acct.portfolio_value):.2f}")
        print(f"Buying Power:    ${float(acct.buying_power):.2f}")
        
        print("\n--- Open Positions ---")
        positions = client.get_all_positions()
        if not positions:
            print("No open positions.")
        for p in positions:
            print(f"{p.symbol}: {p.qty} contracts | Unrealized P&L: ${float(p.unrealized_pl):.2f}")
            
        print("\n--- Today's Pending Orders ---")
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = client.get_orders(req)
        if not orders:
            print("No pending orders.")
        for o in orders:
            print(f"{o.symbol}: {o.qty} contracts | Status: {o.status.name}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
