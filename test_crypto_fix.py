#!/usr/bin/env python3
"""
Quick test script to verify crypto sentinel fixes.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.crypto_sentinel.agent import get_crypto_sentinel


async def test_crypto_sentinel():
    """Test the crypto sentinel agent."""
    print("Testing Crypto Sentinel Agent...")

    try:
        agent = get_crypto_sentinel()
        print("Agent initialized successfully")

        # Test morning brief generation
        print("Generating morning brief...")
        brief = await agent.generate_morning_brief()

        print("✅ Morning brief generated successfully!")
        print(f"   - Signals generated: {len(brief.signals)}")
        print(f"   - Market summary: {brief.market_summary.get('total_market_cap', 'N/A')}")
        print(f"   - News items: {len(brief.news_highlights)}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_crypto_sentinel())
    sys.exit(0 if success else 1)
