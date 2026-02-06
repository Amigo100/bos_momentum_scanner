#!/usr/bin/env python3
"""
TRADINGVIEW LOGIN HELPER
========================

Opens a Playwright browser window for you to log in to TradingView.
After logging in, the session is saved for chart_capture.py to use.

Usage:
    python tradingview_login.py

After login:
    python chart_capture.py --ticker GLXY --headless --skip-wait
"""

import os
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
PLAYWRIGHT_USER_DATA_DIR = str(BASE_DIR / ".playwright_profile")


def login_to_tradingview():
    """Open browser for TradingView login."""

    print("\n" + "═" * 60)
    print("  TRADINGVIEW LOGIN HELPER")
    print("═" * 60)
    print("""
  This will open a browser window. Please:

  1. Click "Sign in" on TradingView
  2. Log in with your TradingView account
  3. Wait for your chart layout to load with indicators
  4. Once indicators show correctly, close the browser window

  Your session will be saved for future chart captures.
""")
    print("═" * 60 + "\n")

    input("  Press Enter to open the browser...")

    with sync_playwright() as p:
        # Launch with persistent context - this saves the login
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_USER_DATA_DIR,
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser_context.new_page()

        # Navigate to TradingView chart
        layout_id = os.environ.get("TRADINGVIEW_LAYOUT_ID", "rxC5j0SK")
        url = f"https://www.tradingview.com/chart/{layout_id}/?symbol=GLXY"

        print(f"  Opening: {url}")
        page.goto(url, timeout=60000)

        print("\n  ✅ Browser opened!")
        print("  📌 Please log in to TradingView now.")
        print("  📌 After your indicators load, close the browser window.")
        print("\n  Waiting for you to close the browser...\n")

        # Wait for user to close the browser
        try:
            # This will block until the context is closed
            page.wait_for_timeout(600000)  # 10 minute max
        except Exception:
            pass

        browser_context.close()

    print("\n  ✅ Session saved!")
    print("  💡 Now run: python chart_capture.py --ticker GLXY --headless --skip-wait")
    print("\n" + "═" * 60 + "\n")


if __name__ == "__main__":
    login_to_tradingview()
