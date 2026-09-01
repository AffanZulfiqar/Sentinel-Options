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
        print("✅ All API keys present")
    except ValueError as exc:
        print(f"❌ {exc}")
        print("\nPlease fill in your .env file and try again.")
        sys.exit(1)

    # Try connecting
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)
        acct = client.get_account()
        print(f"\n📊 Account Details:")
        print(f"   Status          : {acct.status}")
        print(f"   Equity          : ${float(acct.equity or 0):>12,.2f}")
        print(f"   Cash            : ${float(acct.cash or 0):>12,.2f}")
        print(f"   Buying Power    : ${float(acct.buying_power or 0):>12,.2f}")
        print(f"   Portfolio Value : ${float(acct.portfolio_value or 0):>12,.2f}")
        print(f"\n✅ Paper account connected successfully!")
    except Exception as exc:
        print(f"❌ Failed to connect to Alpaca: {exc}")
        sys.exit(1)

    # Verify Claude
    try:
        import anthropic
        client_ai = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        msg = client_ai.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        print(f"✅ Claude API connected  (model={Config.CLAUDE_MODEL})")
    except Exception as exc:
        print(f"❌ Claude API error: {exc}")

    print("\n🚀 Ready to run: python -m src.agent_controller")
    print("=" * 55)


if __name__ == "__main__":
    main()
