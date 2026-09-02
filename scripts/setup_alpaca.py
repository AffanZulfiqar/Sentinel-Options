"""
setup_alpaca.py – Validate Alpaca credentials and print account summary.

Run this FIRST to make sure your API keys work before starting the agent.

    python scripts/setup_alpaca.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config


def main():
    print("=" * 55)
    print("  Alpaca Paper Account Setup Validator")
    print("=" * 55)

    # Validate env
    try:
        Config.validate()
        print("[OK] All API keys present")
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        print("\nPlease fill in your .env file and try again.")
        sys.exit(1)

    # Try connecting
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)
        acct = client.get_account()
        print(f"\n[INFO] Account Details:")
        print(f"   Status          : {acct.status}")
        print(f"   Equity          : ${float(acct.equity or 0):>12,.2f}")
        print(f"   Cash            : ${float(acct.cash or 0):>12,.2f}")
        print(f"   Buying Power    : ${float(acct.buying_power or 0):>12,.2f}")
        print(f"   Portfolio Value : ${float(acct.portfolio_value or 0):>12,.2f}")
        print(f"\n[OK] Paper account connected successfully!")
    except Exception as exc:
        print(f"[FAIL] Failed to connect to Alpaca: {exc}")
        sys.exit(1)

    # Verify Gemini
    try:
        from google import genai
        client_ai = genai.Client(api_key=Config.GEMINI_API_KEY)
        # Quick test request to verify the key
        client_ai.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents="ping"
        )
        print(f"[OK] Gemini API connected  (model={Config.GEMINI_MODEL})")
    except Exception as exc:
        print(f"[FAIL] Gemini API error: {exc}")

    print("\n[READY] Ready to run: python -m src.agent_controller")
    print("=" * 55)


if __name__ == "__main__":
    main()
