#!/usr/bin/env python3
"""
CHART CAPTURE - TradingView Screenshots with Playwright
========================================================

Captures TradingView charts with your custom BoS/Banker indicators
using a persistent Chrome session (no login required).

Usage:
    python chart_capture.py --tickers AAPL,NVDA,PLTR
    python chart_capture.py --tickers-from trades/latest_signals.json
    python chart_capture.py --ticker AAPL --headless

Output:
    trades/charts/{TICKER}_{date}.png (1200x630 for X cards)
    trades/charts/{TICKER}_{date}_substack.png (800x500 for Substack)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Playwright import - install with: pip install playwright && playwright install chromium
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext
except ImportError:
    print("ERROR: playwright not installed. Run:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
CHARTS_DIR = BASE_DIR / "trades" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# TradingView Configuration
TRADINGVIEW_LAYOUT_ID = os.environ.get("TRADINGVIEW_LAYOUT_ID", "rxC5j0SK")

# Playwright browser profile path (separate from your main Chrome to avoid conflicts)
# This creates a dedicated profile for chart capture that won't conflict with running Chrome
PLAYWRIGHT_USER_DATA_DIR = os.environ.get(
    "PLAYWRIGHT_USER_DATA_DIR",
    str(BASE_DIR / ".playwright_profile")
)

# Chart sizes
CHART_SIZE_X = (1200, 630)       # X/Twitter card size
CHART_SIZE_SUBSTACK = (800, 500)  # Substack embed size

# Wait times (adjust based on your connection speed)
PAGE_LOAD_WAIT_MS = 8000          # Wait for page to load
INDICATOR_LOAD_WAIT_MS = 5000     # Additional wait for indicators
LOGIN_WAIT_MS = 60000             # Time to allow manual login if needed (60s)


# ═══════════════════════════════════════════════════════════════════════════════
# CHART CAPTURE
# ═══════════════════════════════════════════════════════════════════════════════

def capture_chart(
    page,
    ticker: str,
    output_dir: Path,
    date_str: str,
    sizes: List[tuple] = None
) -> List[Path]:
    """
    Capture chart for a single ticker at specified sizes.
    
    Args:
        page: Playwright page object
        ticker: Stock symbol
        output_dir: Directory to save charts
        date_str: Date string for filename
        sizes: List of (width, height) tuples
    
    Returns:
        List of saved file paths
    """
    if sizes is None:
        sizes = [CHART_SIZE_X, CHART_SIZE_SUBSTACK]
    
    saved_files = []
    
    # Navigate to chart with your layout
    url = f"https://www.tradingview.com/chart/{TRADINGVIEW_LAYOUT_ID}/?symbol={ticker}"
    print(f"  📊 Loading {ticker}...")
    
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(PAGE_LOAD_WAIT_MS)
        
        # Wait for indicators to load
        # You may need to adjust this selector based on your chart
        page.wait_for_timeout(INDICATOR_LOAD_WAIT_MS)
        
        # TradingView selectors - try multiple options as DOM changes frequently
        chart_selectors = [
            "canvas",                          # Main chart canvas
            ".chart-markup-table",             # Chart markup container
            "[data-name='legend-source-item']", # Chart legend area
            ".chart-container",                # Generic container
            ".layout__area--center",           # Center layout area
        ]

        chart_element = None
        for selector in chart_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    chart_element = element
                    break
            except Exception:
                continue

        if chart_element is None:
            # Fall back to full page screenshot
            print(f"    ⚠ No chart element found, capturing full page")
            chart_element = page

        for width, height in sizes:
            # Set viewport size
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(500)  # Let it resize
            
            # Generate filename
            size_suffix = "" if (width, height) == CHART_SIZE_X else "_substack"
            filename = f"{ticker}_{date_str}{size_suffix}.png"
            filepath = output_dir / filename
            
            # Capture screenshot
            if chart_element == page:
                page.screenshot(path=str(filepath), full_page=False)
            else:
                chart_element.screenshot(path=str(filepath))
            saved_files.append(filepath)
            print(f"    ✓ Saved: {filepath.name} ({width}x{height})")
            
    except Exception as e:
        print(f"    ✗ Error capturing {ticker}: {e}")
    
    return saved_files


def capture_charts(
    tickers: List[str],
    headless: bool = False,
    output_dir: Path = None,
    skip_wait: bool = False
) -> dict:
    """
    Capture charts for multiple tickers.

    Args:
        tickers: List of stock symbols
        headless: Run browser in headless mode
        output_dir: Override default output directory
        skip_wait: Skip the login wait (use after first successful login)

    Returns:
        Dict mapping tickers to their chart file paths
    """
    if output_dir is None:
        output_dir = CHARTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    
    results = {}
    
    print(f"\n  📸 Capturing charts for {len(tickers)} tickers...")
    print(f"  📁 Output: {output_dir}")
    print(f"  🎨 Layout: {TRADINGVIEW_LAYOUT_ID}")
    print("")
    
    with sync_playwright() as p:
        # Launch with persistent context in a dedicated profile directory
        # This avoids conflicts with your running Chrome browser
        # First run: you may need to login to TradingView manually
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_USER_DATA_DIR,
            headless=headless,
            viewport={"width": CHART_SIZE_X[0], "height": CHART_SIZE_X[1]},
            args=["--disable-blink-features=AutomationControlled"]  # Reduce bot detection
        )

        page = browser_context.new_page()

        # Navigate to TradingView first to check if login is needed
        print(f"  ⏳ Loading TradingView (up to 60s)...")
        page.goto("https://www.tradingview.com/chart/" + TRADINGVIEW_LAYOUT_ID, timeout=60000, wait_until="domcontentloaded")

        if skip_wait:
            # Quick wait for page to stabilize
            print(f"  ⏩ Skipping login wait (--skip-wait flag)")
            page.wait_for_timeout(5000)
        else:
            # Check if login prompt appears (give user time to login manually)
            print(f"  ⏳ Waiting {LOGIN_WAIT_MS//1000}s for manual login if needed...")
            print(f"     (If you see a login prompt, please log in now)")
            page.wait_for_timeout(LOGIN_WAIT_MS)
        print(f"  ✓ Continuing with chart capture...\n")

        for ticker in tickers:
            files = capture_chart(page, ticker, output_dir, date_str)
            if files:
                # Store primary (X card) size path
                results[ticker] = str(files[0])
        
        browser_context.close()
    
    print(f"\n  ✅ Captured {len(results)}/{len(tickers)} charts")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_tickers_from_json(filepath: Path) -> List[str]:
    """Load tickers from a JSON file (scanner output format)."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    tickers = []
    
    # Handle different JSON structures
    if isinstance(data, list):
        # List of signal objects
        for item in data:
            if isinstance(item, dict) and 'ticker' in item:
                tickers.append(item['ticker'])
            elif isinstance(item, str):
                tickers.append(item)
    elif isinstance(data, dict):
        # Dict with signals lists
        for key in ['pass_signals', 'buy_signals', 'signals', 'tickers']:
            if key in data:
                for item in data[key]:
                    if isinstance(item, dict) and 'ticker' in item:
                        tickers.append(item['ticker'])
                    elif isinstance(item, str):
                        tickers.append(item)
    
    return list(set(tickers))  # Dedupe


def save_chart_manifest(results: dict, output_dir: Path):
    """Save a manifest of captured charts for other scripts to use."""
    manifest = {
        "captured_at": datetime.now().isoformat(),
        "charts": results
    }
    
    manifest_file = output_dir / "chart_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"  📋 Manifest saved: {manifest_file}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Capture TradingView charts with Playwright")
    parser.add_argument("--ticker", type=str, help="Single ticker to capture")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of tickers")
    parser.add_argument("--tickers-from", type=str, help="JSON file with tickers")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--skip-wait", action="store_true", help="Skip the 60s login wait (use after first successful login)")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()
    
    # Determine tickers to capture
    tickers = []
    
    if args.ticker:
        tickers = [args.ticker.upper()]
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif args.tickers_from:
        tickers = load_tickers_from_json(Path(args.tickers_from))
    else:
        print("ERROR: Specify --ticker, --tickers, or --tickers-from")
        print("Example: python chart_capture.py --tickers AAPL,NVDA,PLTR")
        sys.exit(1)
    
    if not tickers:
        print("ERROR: No tickers to capture")
        sys.exit(1)
    
    # Validate configuration
    if TRADINGVIEW_LAYOUT_ID == "YOUR_LAYOUT_ID":
        print("ERROR: Set TRADINGVIEW_LAYOUT_ID in environment or code")
        print("Find your layout ID in your TradingView chart URL:")
        print("  https://www.tradingview.com/chart/XXXXXXX/?symbol=...")
        print("  The XXXXXXX part is your layout ID")
        sys.exit(1)
    
    # Output directory
    output_dir = Path(args.output) if args.output else CHARTS_DIR
    
    # Run capture
    print("\n" + "═" * 60)
    print("  CHART CAPTURE - TradingView with Playwright")
    print("═" * 60)
    
    results = capture_charts(tickers, headless=args.headless, output_dir=output_dir, skip_wait=args.skip_wait)
    
    # Save manifest
    if results:
        save_chart_manifest(results, output_dir)
    
    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
