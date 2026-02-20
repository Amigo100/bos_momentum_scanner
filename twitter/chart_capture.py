#!/usr/bin/env python3
"""
CHART CAPTURE - TradingView Screenshots with Playwright
========================================================

Captures TradingView charts with your custom Sterling Grid indicators
using a persistent Chrome session.

IMPORTANT: TradingView custom indicators require authentication.
- First run locally WITHOUT --headless to log in
- After login, your session is saved in .playwright_profile/
- Subsequent runs (including --headless) will use the saved session
- CI CANNOT capture TradingView charts (no GUI for login)

For CI, chart images should be captured locally using run_local_friday.sh.

Usage:
    # First time: Log in to TradingView
    python chart_capture.py --ticker GLXY

    # After login: Capture headless
    python chart_capture.py --tickers AAPL,NVDA,PLTR --headless --skip-wait

    # From signals file
    python chart_capture.py --tickers-from trades/signals.json --include-portfolio

Output:
    trades/charts/{TICKER}_{timeframe}_{date}.png (1400x900 for X cards)
    trades/charts/{TICKER}_{timeframe}_{date}_substack.png (1000x700 for Substack)
"""

import logging
import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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

BASE_DIR = Path(__file__).resolve().parent.parent
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

# Chart sizes - match TradingView full layout dimensions
# Using larger sizes to capture all indicator panes properly
CHART_SIZE_X = (1400, 900)       # X/Twitter card size (wider for full weekly view)
CHART_SIZE_SUBSTACK = (1000, 700)  # Substack embed size (larger for readability)

# JavaScript to hide TradingView UI elements (minimal - just declutter, keep visuals)
# NOTE: We WANT to show the chart with indicators visible - they're a marketing feature
# We only hide UI clutter, NOT the indicator visuals or pane labels
HIDE_UI_ELEMENTS_JS = """
() => {
    // Hide right-side panels (watchlist, news, etc.) - just declutter
    document.querySelectorAll('[class*="right-toolbar"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[class*="widgetbar"]').forEach(el => el.style.display = 'none');

    // Hide drawing toolbar - declutter
    document.querySelectorAll('[class*="drawingToolbar"]').forEach(el => el.style.display = 'none');

    // Hide cookie consent banner
    document.querySelectorAll('[class*="cookie"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[class*="consent"]').forEach(el => el.style.display = 'none');

    // Try to click "Don't allow" on cookie banner if present
    const cookieButtons = document.querySelectorAll('button');
    cookieButtons.forEach(btn => {
        if (btn.textContent.includes("Don't allow") || btn.textContent.includes("Reject")) {
            btn.click();
        }
    });

    // DO NOT hide indicator pane labels (Alpha, Bravo, Charlie) - these are generic names
    // DO NOT hide indicator visuals - these are the core marketing feature
    // The chart with BUY/SELL signals and colored areas is what we WANT to show

    return 'UI decluttered';
}
"""

# Wait times (adjust based on your connection speed)
PAGE_LOAD_WAIT_MS = 8000          # Wait for page to load
INDICATOR_LOAD_WAIT_MS = 10000    # Additional wait for indicators to render (increased)
LOGIN_WAIT_MS = 120000            # Time to allow manual login if needed (2 minutes)

# Cookie file for persisting TradingView session across runs
# This allows CI to use a pre-authenticated session
COOKIE_FILE = os.environ.get(
    "TRADINGVIEW_COOKIE_FILE",
    str(BASE_DIR / ".tradingview_cookies.json")
)


# ═══════════════════════════════════════════════════════════════════════════════
# CHART CAPTURE
# ═══════════════════════════════════════════════════════════════════════════════

def _get_tradingview_interval(timeframe: str) -> str:
    """Convert timeframe string to TradingView interval parameter.

    Args:
        timeframe: 'weekly' or 'daily'

    Returns:
        TradingView interval string for URL parameter
    """
    mapping = {
        "weekly": "W",
        "daily": "D",
        "monthly": "M",
    }
    return mapping.get(timeframe.lower(), "W")


def capture_chart(
    page,
    ticker: str,
    output_dir: Path,
    date_str: str,
    timeframe: str = "weekly",
    sizes: Optional[List[tuple]] = None
) -> List[Path]:
    """
    Capture chart for a single ticker at specified sizes and timeframe.

    Args:
        page: Playwright page object
        ticker: Stock symbol
        output_dir: Directory to save charts
        date_str: Date string for filename
        timeframe: Chart timeframe — 'weekly' (default) or 'daily'
        sizes: List of (width, height) tuples

    Returns:
        List of saved file paths (empty list on failure — never crashes)
    """
    if sizes is None:
        sizes = [CHART_SIZE_X, CHART_SIZE_SUBSTACK]

    saved_files = []

    # Build URL with timeframe interval parameter
    interval = _get_tradingview_interval(timeframe)
    url = (
        f"https://www.tradingview.com/chart/{TRADINGVIEW_LAYOUT_ID}/"
        f"?symbol={ticker}&interval={interval}"
    )
    logger.info("Capturing %s on %s timeframe", ticker, timeframe)
    print(f"  📊 Loading {ticker} ({timeframe})...")

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

        # Wait for indicators to load
        page.wait_for_timeout(INDICATOR_LOAD_WAIT_MS)

        # Hide UI elements that reveal strategy (indicator names, panels, etc.)
        try:
            page.evaluate(HIDE_UI_ELEMENTS_JS)
            print(f"    ✓ Hidden indicator names and panels")
            page.wait_for_timeout(500)  # Let DOM update
        except Exception as e:
            print(f"    ⚠ Could not hide UI elements: {e}")

        # TradingView selectors - try multiple options as DOM changes frequently
        chart_selectors = [
            ".layout__area--center",           # Center layout area (best for full chart)
            ".chart-markup-table",             # Chart markup container
            ".chart-container",                # Generic container
            "canvas",                          # Main chart canvas (fallback)
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

            # Generate filename — includes timeframe
            size_suffix = "" if (width, height) == CHART_SIZE_X else "_substack"
            filename = f"{ticker}_{timeframe}_{date_str}{size_suffix}.png"
            filepath = output_dir / filename

            # Capture screenshot
            if chart_element == page:
                page.screenshot(path=str(filepath), full_page=False)
            else:
                chart_element.screenshot(path=str(filepath))
            saved_files.append(filepath)
            print(f"    ✓ Saved: {filepath.name} ({width}x{height})")

    except Exception as e:
        logger.warning("Failed to capture %s (%s): %s", ticker, timeframe, e)
        print(f"    ✗ Error capturing {ticker}: {e}")

    return saved_files


def capture_charts(
    tickers: List[str],
    headless: bool = False,
    output_dir: Optional[Path] = None,
    skip_wait: bool = False,
    save_cookies_after: bool = False,
    use_cookies: bool = True,
    timeframe: str = "weekly"
) -> dict:
    """
    Capture charts for multiple tickers (all on the same timeframe).

    Args:
        tickers: List of stock symbols
        headless: Run browser in headless mode
        output_dir: Override default output directory
        skip_wait: Skip the login wait (use after first successful login)
        save_cookies_after: Save cookies after successful capture (for CI setup)
        use_cookies: Try to load cookies from file first
        timeframe: Chart timeframe — 'weekly' (default) or 'daily'

    Returns:
        Dict mapping tickers to their chart file paths
    """
    # Delegate to batch function with uniform timeframe
    pairs = [(t, timeframe) for t in tickers]
    return capture_charts_batch(
        tickers_with_timeframe=pairs,
        headless=headless,
        output_dir=output_dir,
        skip_wait=skip_wait,
        save_cookies_after=save_cookies_after,
        use_cookies=use_cookies,
    )


def capture_charts_batch(
    tickers_with_timeframe: List[Tuple[str, str]],
    headless: bool = False,
    output_dir: Optional[Path] = None,
    skip_wait: bool = False,
    save_cookies_after: bool = False,
    use_cookies: bool = True,
) -> Dict[str, Optional[str]]:
    """
    Capture charts for (ticker, timeframe) pairs in a single browser session.

    This is the primary batch capture function. Each ticker can have its own
    timeframe (e.g. weekly for signals, daily for intraday alerts).

    If capture fails for any ticker, that ticker's value is None in the
    returned dict — the batch does NOT crash.

    Args:
        tickers_with_timeframe: List of (ticker, timeframe) tuples
            e.g. [("NVDA", "weekly"), ("AAPL", "daily")]
        headless: Run browser in headless mode
        output_dir: Override default output directory
        skip_wait: Skip the login wait (use after first successful login)
        save_cookies_after: Save cookies after successful capture
        use_cookies: Try to load cookies from file first

    Returns:
        Dict mapping ticker to relative chart path (str) or None on failure
    """
    if output_dir is None:
        output_dir = CHARTS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    results: Dict[str, Optional[str]] = {}
    total = len(tickers_with_timeframe)

    print(f"\n  📸 Capturing charts for {total} tickers...")
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

        # Try to load saved cookies (for CI)
        cookies_loaded = False
        if use_cookies:
            cookies_loaded = load_cookies(browser_context)

        # Navigate to TradingView first to check if login is needed
        print(f"  ⏳ Loading TradingView (up to 60s)...")
        page.goto("https://www.tradingview.com/chart/" + TRADINGVIEW_LAYOUT_ID, timeout=60000, wait_until="domcontentloaded")

        # Wait for page to load
        page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

        # Check if indicators loaded (requires authentication)
        indicators_ok, indicator_msg = check_indicators_loaded(page)
        print(f"  📊 Indicator check: {indicator_msg}")

        if not indicators_ok and not skip_wait:
            # Need manual login
            print(f"  ⚠️ Indicators not loading properly!")
            print(f"  🔑 Please log in to TradingView in the browser window...")
            print(f"  ⏳ Waiting {LOGIN_WAIT_MS//1000}s for manual login...")
            print(f"     (After login, the chart should refresh automatically)")
            page.wait_for_timeout(LOGIN_WAIT_MS)
            # Reload after login
            page.reload()
            page.wait_for_timeout(PAGE_LOAD_WAIT_MS + INDICATOR_LOAD_WAIT_MS)
            # Check again
            indicators_ok, indicator_msg = check_indicators_loaded(page)
            print(f"  📊 Post-login check: {indicator_msg}")
        elif skip_wait and not indicators_ok:
            print(f"  ⏩ Skipping login wait (--skip-wait flag) - indicators may not render")

        print(f"  ✓ Continuing with chart capture...\n")

        for i, (ticker, timeframe) in enumerate(tickers_with_timeframe):
            try:
                files = capture_chart(page, ticker, output_dir, date_str, timeframe=timeframe)
                if files:
                    # Store primary (X card) size path as RELATIVE path (for CI compatibility)
                    try:
                        rel_path = files[0].relative_to(BASE_DIR)
                        results[ticker] = str(rel_path)
                    except ValueError:
                        # If not relative to BASE_DIR, use filename with trades/charts prefix
                        results[ticker] = f"trades/charts/{files[0].name}"
                else:
                    logger.warning("No files returned for %s (%s)", ticker, timeframe)
                    results[ticker] = None
            except Exception as e:
                # Graceful fallback — log and continue to next ticker
                logger.error("Unexpected error capturing %s (%s): %s", ticker, timeframe, e)
                print(f"    ✗ Skipping {ticker} due to error: {e}")
                results[ticker] = None

            # Rate-limit delay between captures (avoid TradingView throttling)
            if i < total - 1:
                time.sleep(1.5)

        # Save cookies for future CI runs
        if save_cookies_after and any(v is not None for v in results.values()):
            save_cookies(browser_context)

        browser_context.close()

    captured = sum(1 for v in results.values() if v is not None)
    print(f"\n  ✅ Captured {captured}/{total} charts")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# COOKIE MANAGEMENT (for CI authentication)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_chrome_cookies(domain: str = "tradingview.com") -> list:
    """
    Extract cookies from Chrome's cookie database for a specific domain.

    NOTE: Chrome must be CLOSED for this to work (database is locked while running).

    Returns:
        List of cookie dicts in Playwright format
    """
    import sqlite3
    import shutil
    import tempfile

    chrome_cookie_path = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/Cookies"
    )

    if not os.path.exists(chrome_cookie_path):
        print("  ⚠️ Chrome cookies database not found")
        return []

    # Copy database to temp file (Chrome locks the original)
    temp_dir = tempfile.mkdtemp()
    temp_cookie_path = os.path.join(temp_dir, "Cookies")

    try:
        shutil.copy2(chrome_cookie_path, temp_cookie_path)

        conn = sqlite3.connect(temp_cookie_path)
        cursor = conn.cursor()

        # Query cookies for the domain
        cursor.execute("""
            SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE ?
        """, (f"%{domain}%",))

        cookies = []
        for row in cursor.fetchall():
            host_key, name, value, path, expires_utc, is_secure, is_httponly = row

            # Chrome stores expires_utc as microseconds since 1601-01-01
            # Convert to Unix timestamp
            if expires_utc > 0:
                # Chrome epoch is 11644473600 seconds before Unix epoch
                expires = (expires_utc / 1000000) - 11644473600
            else:
                expires = -1

            cookies.append({
                "name": name,
                "value": value,
                "domain": host_key,
                "path": path,
                "expires": expires,
                "httpOnly": bool(is_httponly),
                "secure": bool(is_secure),
                "sameSite": "None" if is_secure else "Lax"
            })

        conn.close()
        print(f"  🍪 Extracted {len(cookies)} cookies from Chrome for {domain}")
        return cookies

    except Exception as e:
        print(f"  ⚠️ Failed to extract Chrome cookies: {e}")
        print("  💡 Make sure Chrome is completely closed")
        return []
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)


def save_cookies(context, filepath: str = COOKIE_FILE) -> None:
    """Save browser cookies to file for reuse in CI."""
    cookies = context.cookies()
    with open(filepath, 'w') as f:
        json.dump(cookies, f, indent=2)
    print(f"  💾 Saved {len(cookies)} cookies to {filepath}")


def load_cookies(context, filepath: str = COOKIE_FILE) -> bool:
    """Load cookies from file if available."""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print(f"  🍪 Loaded {len(cookies)} cookies from {filepath}")
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to load cookies: {e}")
        return False


def check_indicators_loaded(page) -> tuple:
    """
    Check if custom indicators rendered properly.

    Returns:
        (is_ok: bool, message: str) - Whether indicators loaded and diagnostic message
    """
    try:
        # Take a short pause for DOM to stabilize
        page.wait_for_timeout(1000)

        # Look for various error indicators
        # 1. Runtime error popups (subscription limit) - look for the error icon with !
        # TradingView uses svg icons with specific attributes for errors
        error_icons_svg = page.locator('svg[class*="icon-"][fill*="var(--tv-warning"]').count()
        error_icons_title = page.locator('[title*="error" i]').count()
        error_icons_aria = page.locator('[aria-label*="error" i]').count()

        # 2. Look for the actual error message text
        runtime_errors = page.locator('text="Runtime error"').count()
        study_limit = page.locator('text="maximum number of studies"').count()
        loading_errors = page.locator('text="Loading error"').count()

        # 3. Count pane legend items with ! icon (indicator name followed by error)
        # These show as the indicator name with a warning symbol
        pane_legend_errors = page.locator('.pane-legend-item-value-wrap .apply-common-tooltip svg').count()

        # 4. Check for login prompts
        login_prompts = page.locator('button:has-text("Sign in")').count()
        login_links = page.locator('a:has-text("Sign in")').count()

        # Build diagnostic info
        total_errors = runtime_errors + study_limit + loading_errors

        if runtime_errors > 0:
            return False, f"Runtime error detected (subscription limit - need TradingView Plus or higher)"

        if study_limit > 0:
            return False, "Study limit reached for subscription tier"

        if loading_errors > 0:
            return False, "Loading errors on indicators"

        if login_prompts > 0 or login_links > 1:
            return False, "Login required to view indicators"

        # If we can't detect errors but also can't confirm success, be cautious
        # Check if indicator data is actually visible (lines, areas, etc.)
        indicator_visuals = page.locator('.study-renderer').count()
        if indicator_visuals == 0:
            # No rendered studies - likely an auth or subscription issue
            return False, "No indicator visuals rendered (may need login or higher subscription)"

        return True, f"Indicators loaded ({indicator_visuals} study renderers found)"
    except Exception as e:
        return True, f"Check failed (assuming OK): {e}"  # Assume OK if check fails


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
            if isinstance(item, dict):
                # Try common ticker field names
                ticker = item.get('ticker') or item.get('symbol')
                if ticker:
                    tickers.append(ticker)
            elif isinstance(item, str):
                tickers.append(item)
    elif isinstance(data, dict):
        # Dict with signals lists - check all relevant keys
        signal_keys = [
            'pass_signals', 'buy_signals', 'signals', 'tickers',
            'sell_signals', 'caution_signals', 'consider_signals'
        ]
        for key in signal_keys:
            if key in data:
                for item in data[key]:
                    if isinstance(item, dict):
                        ticker = item.get('ticker') or item.get('symbol')
                        if ticker:
                            tickers.append(ticker)
                    elif isinstance(item, str):
                        tickers.append(item)

    return list(set(tickers))  # Dedupe


def load_tickers_from_portfolio(filepath: Path) -> List[str]:
    """Load open position tickers from portfolio.csv."""
    import csv

    tickers = []

    if not filepath.exists():
        return tickers

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status', '').upper() == 'OPEN':
                ticker = row.get('ticker')
                if ticker:
                    tickers.append(ticker)

    return tickers


def save_chart_manifest(results: dict, output_dir: Path) -> None:
    """Save/merge captured charts into the manifest (preserves existing entries)."""
    manifest_file = output_dir / "chart_manifest.json"

    # Load existing manifest (preserve funnel graphic and prior captures)
    if manifest_file.exists():
        try:
            with open(manifest_file) as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            manifest = {"charts": {}}
    else:
        manifest = {"charts": {}}

    # Merge new results into existing charts
    manifest["captured_at"] = datetime.now().isoformat()
    manifest.setdefault("charts", {}).update(results)

    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"  📋 Manifest saved: {manifest_file}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Capture TradingView charts with Playwright")
    parser.add_argument("--ticker", type=str, help="Single ticker to capture")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of tickers")
    parser.add_argument("--tickers-from", type=str, help="JSON file with tickers")
    parser.add_argument("--include-portfolio", action="store_true", help="Also capture charts for open portfolio positions")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--skip-wait", action="store_true", help="Skip the 60s login wait (use after first successful login)")
    parser.add_argument("--save-cookies", action="store_true", help="Save cookies after capture (for CI setup)")
    parser.add_argument("--no-cookies", action="store_true", help="Don't load saved cookies")
    parser.add_argument("--extract-chrome-cookies", action="store_true", help="Extract cookies from Chrome (must close Chrome first)")
    parser.add_argument("--timeframe", type=str, default="weekly",
                        choices=["weekly", "daily", "monthly"],
                        help="Chart timeframe (default: weekly)")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    # Handle cookie extraction command
    if args.extract_chrome_cookies:
        print("\n" + "═" * 60)
        print("  EXTRACTING TRADINGVIEW COOKIES FROM CHROME")
        print("═" * 60)
        print("\n  ⚠️  Make sure Chrome is COMPLETELY CLOSED before running this!\n")

        cookies = extract_chrome_cookies("tradingview.com")
        if cookies:
            with open(COOKIE_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"  ✅ Saved {len(cookies)} cookies to {COOKIE_FILE}")
            print("  💡 Now run: python chart_capture.py --ticker GLXY --headless")
        else:
            print("  ❌ No cookies found. Make sure you're logged into TradingView in Chrome.")
        print("\n" + "═" * 60)
        return

    # Determine tickers to capture
    tickers = []

    if args.ticker:
        tickers = [args.ticker.upper()]
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif args.tickers_from:
        tickers = load_tickers_from_json(Path(args.tickers_from))

    # Add portfolio positions if requested
    if args.include_portfolio:
        portfolio_path = BASE_DIR / "trades" / "portfolio.csv"
        portfolio_tickers = load_tickers_from_portfolio(portfolio_path)
        if portfolio_tickers:
            print(f"  📁 Adding {len(portfolio_tickers)} open positions from portfolio")
            tickers.extend(portfolio_tickers)
            tickers = list(set(tickers))  # Dedupe

    if not tickers:
        print("ERROR: Specify --ticker, --tickers, or --tickers-from")
        print("Example: python chart_capture.py --tickers AAPL,NVDA,PLTR")
        print("         python chart_capture.py --tickers-from trades/signals.json --include-portfolio")
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

    results = capture_charts(
        tickers,
        headless=args.headless,
        output_dir=output_dir,
        skip_wait=args.skip_wait,
        save_cookies_after=args.save_cookies,
        use_cookies=not args.no_cookies,
        timeframe=args.timeframe
    )
    
    # Save manifest
    if results:
        save_chart_manifest(results, output_dir)
    
    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
