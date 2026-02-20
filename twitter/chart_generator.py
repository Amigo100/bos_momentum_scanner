#!/usr/bin/env python3
"""
CHART GENERATOR - chart-img.com REST API Integration
=====================================================

Generates TradingView chart images via the chart-img.com API.
CI-compatible (no browser required, unlike chart_capture.py).

Called by live_tweet.yml workflow between tweet generation and posting.
Reads live_content_queue.json, generates charts for items with
chart_recommended=True, updates chart_path in-place.

Usage:
    python -m content.chart_generator                   # Process live queue
    python -m content.chart_generator --ticker AAPL     # Single chart
    python -m content.chart_generator --dry-run         # Preview only

Environment Variables:
    CHARTIMG_API_KEY          Required for chart generation
    TRADINGVIEW_LAYOUT_ID     Optional — renders saved private layout
    TRADINGVIEW_SESSION       Optional — TradingView session for private layouts
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # Handled gracefully below

# Import config constants
try:
    from config import (
        LIVE_QUEUE_FILE,
        CHARTS_DIR,
        CHARTIMG_API_URL,
        CHART_IMG_WIDTH,
        CHART_IMG_HEIGHT,
        CHART_IMG_INTERVAL,
        EXCHANGE_MAP,
    )
except ImportError:
    # Fallback for standalone testing
    BASE_DIR = Path(__file__).resolve().parent.parent
    _TWITTER_OUTPUT = BASE_DIR / "twitter" / "output"
    LIVE_QUEUE_FILE = _TWITTER_OUTPUT / "live_content_queue.json"
    CHARTS_DIR = _TWITTER_OUTPUT / "charts"
    CHARTIMG_API_URL = "https://api.chart-img.com/v2/tradingview/advanced-chart"
    CHART_IMG_WIDTH = 800
    CHART_IMG_HEIGHT = 450
    CHART_IMG_INTERVAL = "1W"
    EXCHANGE_MAP = {
        "WCC": "NYSE", "STRL": "NASDAQ", "MOD": "NYSE",
        "MATV": "NASDAQ", "LUMN": "NYSE", "FIX": "NYSE",
        "RCAT": "NASDAQ", "IBKR": "NASDAQ", "CGON": "NASDAQ",
        "TLN": "NYSE", "VNET": "NASDAQ",
        "IESC": "NYSE", "AAON": "NASDAQ", "AMSC": "NASDAQ",
        "AMPX": "NYSE", "APLD": "NASDAQ", "ASPI": "NASDAQ",
        "BITF": "NASDAQ", "SOFI": "NASDAQ", "HIVE": "NASDAQ",
        "EVTL": "NYSE", "NVDA": "NASDAQ", "AMD": "NASDAQ",
    }
API_TIMEOUT = 30  # seconds


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

def get_symbol(ticker: str) -> str:
    """Map ticker to 'EXCHANGE:TICKER' format for chart-img.com API.

    Uses EXCHANGE_MAP from config, defaults to NASDAQ.

    Args:
        ticker: Stock ticker symbol (e.g., "WCC", "AAPL")

    Returns:
        Exchange-prefixed symbol (e.g., "NYSE:WCC", "NASDAQ:AAPL")
    """
    exchange = EXCHANGE_MAP.get(ticker.upper(), "NASDAQ")
    return f"{exchange}:{ticker.upper()}"


# ═══════════════════════════════════════════════════════════════════════════════
# CHART GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_chart(
    ticker: str,
    interval: Optional[str] = None,
    layout_id: Optional[str] = None,
) -> Optional[str]:
    """Generate a chart image via chart-img.com REST API.

    NEVER raises exceptions — all errors are caught and return None.
    This is critical: chart failures must never block tweet posting.

    Args:
        ticker: Stock ticker symbol
        interval: TradingView interval (e.g., "1W", "1D"). Defaults to config.
        layout_id: TradingView saved layout ID for private layouts.

    Returns:
        Path string to saved chart image, or None on failure.
    """
    if requests is None:
        print("  WARN: requests library not installed, skipping chart generation")
        return None

    api_key = os.environ.get("CHARTIMG_API_KEY")
    if not api_key:
        print("  WARN: CHARTIMG_API_KEY not set, skipping chart generation")
        return None

    # Determine endpoint and parameters
    interval = interval or CHART_IMG_INTERVAL
    symbol = get_symbol(ticker)

    # Use /storage endpoint if layout_id provided (renders saved private layout)
    tv_layout = layout_id or os.environ.get("TRADINGVIEW_LAYOUT_ID")
    tv_session = os.environ.get("TRADINGVIEW_SESSION")

    if tv_layout and tv_session:
        url = f"{CHARTIMG_API_URL}/storage"
        params = {
            "key": api_key,
            "layout": tv_layout,
            "symbol": symbol,
            "interval": interval,
            "width": CHART_IMG_WIDTH,
            "height": CHART_IMG_HEIGHT,
            "session": tv_session,
        }
    else:
        url = CHARTIMG_API_URL
        params = {
            "key": api_key,
            "symbol": symbol,
            "interval": interval,
            "width": CHART_IMG_WIDTH,
            "height": CHART_IMG_HEIGHT,
        }

    try:
        print(f"  Generating chart: {symbol} ({interval})...")
        response = requests.get(url, params=params, timeout=API_TIMEOUT)

        if response.status_code != 200:
            print(f"  WARN: chart-img.com returned {response.status_code} for {ticker}")
            return None

        # Verify we got an image
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            print(f"  WARN: Unexpected content type: {content_type} for {ticker}")
            return None

        # Save chart
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        filename = f"live_{ticker.upper()}_{timestamp}.png"
        output_path = CHARTS_DIR / filename

        with open(output_path, "wb") as f:
            f.write(response.content)

        file_size_kb = output_path.stat().st_size / 1024
        print(f"  Chart saved: {output_path} ({file_size_kb:.1f} KB)")
        return str(output_path)

    except requests.exceptions.Timeout:
        print(f"  WARN: chart-img.com timeout for {ticker} ({API_TIMEOUT}s)")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  WARN: chart-img.com connection error for {ticker}")
        return None
    except Exception as e:
        print(f"  WARN: chart generation failed for {ticker}: {e}")
        return None


def check_tv_session() -> bool:
    """Health check: test if TradingView session is valid.

    Attempts to generate an AAPL chart. Returns True if successful.
    """
    result = generate_chart("AAPL", interval="1D")
    if result:
        # Clean up test chart
        try:
            os.remove(result)
        except OSError:
            pass
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def update_queue_chart_paths(queue_path: Optional[Path] = None) -> int:
    """Read live queue, generate charts for flagged items, update paths.

    Reads live_content_queue.json, finds items with chart_recommended=True
    and chart_path=None/null, generates charts, writes chart_path back.

    Args:
        queue_path: Path to queue file. Defaults to LIVE_QUEUE_FILE.

    Returns:
        Number of charts successfully generated.
    """
    queue_path = queue_path or LIVE_QUEUE_FILE

    if not queue_path.exists():
        print("  No live queue file found, nothing to do")
        return 0

    try:
        with open(queue_path, "r") as f:
            queue = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR: Failed to read queue: {e}")
        return 0

    # Find items needing charts (including items with stale/non-existent chart paths)
    needs_chart = [
        item for item in queue
        if item.get("chart_recommended", False)
        and item.get("status") == "pending"
        and (not item.get("chart_path") or not Path(item["chart_path"]).exists())
    ]

    if not needs_chart:
        print("  No pending items need charts")
        return 0

    print(f"\n  Generating charts for {len(needs_chart)} item(s)...")

    # Deduplicate tickers (avoid generating same chart multiple times)
    ticker_chart_map = {}
    generated = 0

    for item in needs_chart:
        ticker = item.get("primary_ticker", "").replace("$", "").upper()
        if not ticker:
            continue

        # Reuse chart if we already generated for this ticker
        if ticker in ticker_chart_map:
            item["chart_path"] = ticker_chart_map[ticker]
            generated += 1
            continue

        # Generate chart
        chart_path = generate_chart(ticker)
        if chart_path:
            item["chart_path"] = chart_path
            ticker_chart_map[ticker] = chart_path
            generated += 1
        # If generation fails, chart_path remains None — tweet posts as text-only

    # Save updated queue (atomic write)
    if generated > 0:
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".json",
            dir=queue_path.parent,
            prefix=".chart_queue_tmp_",
        )
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(queue, f, indent=2)
            shutil.move(temp_path, queue_path)
            print(f"\n  Updated {generated} chart path(s) in queue")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"  ERROR: Failed to save queue: {e}")

    return generated


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """CLI entry point for chart generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate TradingView charts via chart-img.com API")
    parser.add_argument("--ticker", type=str, help="Generate chart for a single ticker")
    parser.add_argument("--interval", type=str, default=None, help="TradingView interval (1W, 1D, etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--queue", type=str, default=None, help="Custom queue file path")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  CHART GENERATOR — chart-img.com API")
    print("=" * 60)

    # Single ticker mode
    if args.ticker:
        if args.dry_run:
            symbol = get_symbol(args.ticker)
            print(f"\n  DRY RUN: Would generate chart for {symbol}")
            print(f"  Interval: {args.interval or CHART_IMG_INTERVAL}")
            print(f"  Size: {CHART_IMG_WIDTH}x{CHART_IMG_HEIGHT}")
            return 0

        path = generate_chart(args.ticker, interval=args.interval)
        if path:
            print(f"\n  Success: {path}")
            return 0
        else:
            print("\n  Failed to generate chart")
            return 1

    # Queue mode (default)
    queue_path = Path(args.queue) if args.queue else None

    if args.dry_run:
        qp = queue_path or LIVE_QUEUE_FILE
        if not qp.exists():
            print(f"\n  DRY RUN: No queue file found at {qp}")
            return 0
        try:
            with open(qp) as f:
                queue = json.load(f)
            needs = [
                item for item in queue
                if item.get("chart_recommended", False)
                and not item.get("chart_path")
                and item.get("status") == "pending"
            ]
            print(f"\n  DRY RUN: {len(needs)} item(s) would get charts")
            for item in needs:
                ticker = item.get("primary_ticker", "?")
                print(f"    - {ticker} ({item.get('category', '?')})")
        except Exception as e:
            print(f"\n  DRY RUN: Error reading queue: {e}")
        return 0

    count = update_queue_chart_paths(queue_path)
    print(f"\n  Generated {count} chart(s)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
