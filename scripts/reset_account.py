"""
reset_account.py – Cancel all open orders and (optionally) close all positions.

USE WITH CARE on a paper account before a demo / judging session.

    python scripts/reset_account.py [--close-positions]
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config


def main():
    parser = argparse.ArgumentParser(description="Reset Alpaca paper account.")
    parser.add_argument("--close-positions", action="store_true", help="Also close all open positions")
    args = parser.parse_args()

    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import ClosePositionRequest

    client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)

    # Cancel all orders
    print("Cancelling all open orders …")
    try:
        client.cancel_orders()
        print("✅ All open orders cancelled.")
    except Exception as exc:
        print(f"⚠️  {exc}")

    if args.close_positions:
        print("Closing all open positions …")
        try:
            client.close_all_positions(cancel_orders=True)
            print("✅ All positions closed.")
        except Exception as exc:
            print(f"⚠️  {exc}")

    acct = client.get_account()
    print(f"\nAccount state after reset:")
    print(f"  Equity       : ${float(acct.equity or 0):,.2f}")
    print(f"  Cash         : ${float(acct.cash or 0):,.2f}")
    print(f"  Buying Power : ${float(acct.buying_power or 0):,.2f}")


if __name__ == "__main__":
    main()
