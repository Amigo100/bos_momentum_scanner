#!/usr/bin/env python3
"""
SELF-QUOTE TRACKER
==================

Tracks original signal tweet IDs for creating quote tweets
when positions hit milestones (25%, 50%, 100%).

This module enables the self-quote threading system where milestone
celebrations can reference the original GREEN signal announcement.

Data stored in: twitter/output/tweet_tracking.json

Usage:
    # Register a new signal tweet
    register_signal_tweet('NVDA', '1234567890', 500.00, '2026-01-15')

    # Get original tweet ID for quoting
    tweet_id = get_original_tweet_id('NVDA')

    # Mark milestone as celebrated
    mark_milestone_quoted('NVDA', '25_pct', '9876543210')

    # Get positions with uncelebrated milestones
    milestones = get_unquoted_milestones()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import config for paths
try:
    from config import TWEET_TRACKING_FILE, TWITTER_OUTPUT, CELEBRATION_THRESHOLDS
except ImportError:
    TWITTER_OUTPUT = Path(__file__).resolve().parent.parent / "twitter" / "output"
    TWEET_TRACKING_FILE = TWITTER_OUTPUT / "tweet_tracking.json"
    CELEBRATION_THRESHOLDS = [25.0, 50.0, 100.0]


def load_tracking_data() -> Dict:
    """Load tweet tracking data from JSON file.

    Returns:
        Dict with 'signals' key containing ticker -> tracking data mapping
    """
    if TWEET_TRACKING_FILE.exists():
        try:
            return json.loads(TWEET_TRACKING_FILE.read_text())
        except json.JSONDecodeError:
            return {"signals": {}}
    return {"signals": {}}


def save_tracking_data(data: Dict) -> None:
    """Save tweet tracking data to JSON file.

    Args:
        data: Dict to save (must have 'signals' key)
    """
    TWITTER_OUTPUT.mkdir(parents=True, exist_ok=True)
    TWEET_TRACKING_FILE.write_text(json.dumps(data, indent=2))


def register_signal_tweet(
    ticker: str,
    tweet_id: str,
    entry_price: float,
    signal_date: str
) -> None:
    """
    Save original signal tweet ID for future quoting.

    Called when a GREEN signal tweet is posted, so we can later
    quote it when the position hits milestones.

    Args:
        ticker: Stock ticker symbol
        tweet_id: Twitter tweet ID of the signal announcement
        entry_price: Entry price at signal
        signal_date: Date of signal (YYYY-MM-DD format)
    """
    data = load_tracking_data()

    data["signals"][ticker.upper()] = {
        "tweet_id": tweet_id,
        "entry_price": entry_price,
        "signal_date": signal_date,
        "registered_at": datetime.now().isoformat(),
        "milestones_quoted": {
            "25_pct": None,
            "50_pct": None,
            "100_pct": None,
        }
    }

    save_tracking_data(data)
    print(f"  Registered {ticker} signal tweet {tweet_id} for quote tracking")


def get_original_tweet_id(ticker: str) -> Optional[str]:
    """
    Get original signal tweet ID for a ticker.

    Used when creating quote tweets for milestone celebrations.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Tweet ID string if found, None otherwise
    """
    data = load_tracking_data()
    return data.get("signals", {}).get(ticker.upper(), {}).get("tweet_id")


def get_signal_data(ticker: str) -> Optional[Dict]:
    """
    Get full signal tracking data for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with tweet_id, entry_price, signal_date, milestones_quoted
    """
    data = load_tracking_data()
    return data.get("signals", {}).get(ticker.upper())


def mark_milestone_quoted(
    ticker: str,
    milestone: str,
    quote_tweet_id: str
) -> None:
    """
    Mark a milestone as celebrated with quote tweet.

    Called after successfully posting a quote tweet for a milestone.

    Args:
        ticker: Stock ticker symbol
        milestone: Milestone key ('25_pct', '50_pct', '100_pct')
        quote_tweet_id: Twitter tweet ID of the quote tweet
    """
    data = load_tracking_data()

    if ticker.upper() in data.get("signals", {}):
        data["signals"][ticker.upper()]["milestones_quoted"][milestone] = {
            "quoted_at": datetime.now().isoformat(),
            "quote_tweet_id": quote_tweet_id
        }
        save_tracking_data(data)
        print(f"  Marked {ticker} {milestone} milestone as quoted")


def is_milestone_quoted(ticker: str, milestone: str) -> bool:
    """
    Check if a milestone has already been quoted.

    Args:
        ticker: Stock ticker symbol
        milestone: Milestone key ('25_pct', '50_pct', '100_pct')

    Returns:
        True if milestone has been quoted, False otherwise
    """
    data = load_tracking_data()
    signal = data.get("signals", {}).get(ticker.upper(), {})
    milestones = signal.get("milestones_quoted", {})
    return milestones.get(milestone) is not None


def get_unquoted_milestones() -> List[Dict]:
    """
    Get positions that hit milestones but haven't been quoted yet.

    Cross-references tweet tracking data with current portfolio P&L
    to find positions where we can post quote tweets.

    Returns:
        List of dicts with ticker, pnl_pct, original_tweet_id, milestone_key
    """
    try:
        from twitter.signal_tracker import get_open_positions, filter_public_positions
    except ImportError:
        return []

    data = load_tracking_data()
    positions = filter_public_positions(get_open_positions())

    unquoted = []
    for pos in positions:
        ticker = pos.get('ticker', '').upper()
        pnl = pos.get('pnl_pct', 0)

        # Check if we're tracking this ticker
        signal_data = data.get("signals", {}).get(ticker)
        if not signal_data:
            continue

        original_tweet_id = signal_data.get("tweet_id")
        if not original_tweet_id:
            continue

        milestones_quoted = signal_data.get("milestones_quoted", {})

        # Check each threshold
        for threshold in sorted(CELEBRATION_THRESHOLDS, reverse=True):
            if pnl >= threshold:
                milestone_key = f"{int(threshold)}_pct"
                if milestones_quoted.get(milestone_key) is None:
                    unquoted.append({
                        'ticker': ticker,
                        'pnl_pct': pnl,
                        'threshold': threshold,
                        'milestone_key': milestone_key,
                        'original_tweet_id': original_tweet_id,
                        'entry_price': signal_data.get('entry_price'),
                        'signal_date': signal_data.get('signal_date'),
                    })
                    break  # Only report highest unquoted milestone

    return unquoted


def get_all_tracked_signals() -> Dict[str, Dict]:
    """Get all tracked signals with their milestone status."""
    data = load_tracking_data()
    return data.get("signals", {})


def remove_signal(ticker: str) -> bool:
    """
    Remove a ticker from tracking (e.g., after position closed).

    Args:
        ticker: Stock ticker symbol

    Returns:
        True if removed, False if not found
    """
    data = load_tracking_data()
    if ticker.upper() in data.get("signals", {}):
        del data["signals"][ticker.upper()]
        save_tracking_data(data)
        return True
    return False


def main():
    """CLI for testing self-quote tracker."""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Quote Tracker")
    parser.add_argument("--list", action="store_true", help="List all tracked signals")
    parser.add_argument("--unquoted", action="store_true", help="Show unquoted milestones")
    parser.add_argument("--register", nargs=4,
                       metavar=('TICKER', 'TWEET_ID', 'PRICE', 'DATE'),
                       help="Register a signal tweet")

    args = parser.parse_args()

    if not any([args.list, args.unquoted, args.register]):
        parser.print_help()
        return

    print("=" * 60)
    print("  SELF-QUOTE TRACKER")
    print("=" * 60)

    if args.list:
        signals = get_all_tracked_signals()
        if not signals:
            print("\nNo signals tracked yet.")
        else:
            print(f"\nTracked Signals ({len(signals)} total):\n")
            for ticker, data in signals.items():
                tweet_id = data.get('tweet_id', 'N/A')
                entry = data.get('entry_price', 0)
                milestones = data.get('milestones_quoted', {})
                quoted_count = sum(1 for m in milestones.values() if m)
                print(f"  ${ticker}: tweet={tweet_id[:10]}... entry=${entry:.2f} milestones={quoted_count}/3")

    if args.unquoted:
        unquoted = get_unquoted_milestones()
        if not unquoted:
            print("\nNo unquoted milestones found.")
        else:
            print(f"\nUnquoted Milestones ({len(unquoted)} total):\n")
            for m in unquoted:
                print(f"  ${m['ticker']}: +{m['pnl_pct']:.1f}% ({m['milestone_key']}) - tweet {m['original_tweet_id'][:10]}...")

    if args.register:
        ticker, tweet_id, price, date = args.register
        register_signal_tweet(ticker, tweet_id, float(price), date)
        print(f"\nRegistered ${ticker}")

    print("\nDone!")


if __name__ == "__main__":
    main()
