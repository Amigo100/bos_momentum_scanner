#!/usr/bin/env python3
"""
WINNER SHOWCASE GENERATOR
=========================

Generates winner showcase content with entry price display rules.
Only shows entry prices for positions above the 25% threshold.

This module handles the formatting and generation of winner-focused
content for tweets and other public-facing displays.

Usage:
    python winner_showcase_generator.py --tweet
    python winner_showcase_generator.py --json
    python winner_showcase_generator.py --list
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    SIGNAL_COLORS,
    get_signal_emoji,
    get_conviction_text,
    can_show_entry_price,
    ENTRY_PRICE_RULES,
    MARKETING_THRESHOLDS,
    BRANDING,
)


def load_portfolio() -> List[Dict]:
    """Load positions from portfolio.csv with numeric fields computed.

    Delegates to the canonical implementation in portfolio_manager.
    """
    from portfolio.manager import load_portfolio as _load
    return _load(compute_pnl=True)


def get_winners_for_showcase(
    threshold: float = 25.0,
    include_entry_price: bool = True,
    max_positions: int = 5
) -> List[Dict]:
    """
    Get winning positions for public showcase with optional entry prices.

    Only includes positions above threshold where entry price display is allowed.

    Args:
        threshold: Minimum P&L percentage for inclusion (default 25%)
        include_entry_price: Whether to include entry prices (only for 25%+)
        max_positions: Maximum number of positions to return

    Returns:
        List of winner dictionaries sorted by P&L descending
    """
    positions = load_portfolio()

    # Filter to OPEN and positive P&L above threshold
    winners = []
    for pos in positions:
        if pos.get('status') != 'OPEN':
            continue

        pnl = pos.get('pnl_pct', 0)
        if pnl < threshold:
            continue

        # Check if we can show entry price for this position
        can_show = can_show_entry_price(pos)

        winner = {
            'ticker': pos.get('ticker', 'UNKNOWN'),
            'entry_price': pos.get('entry_price', 0) if can_show else None,
            'current_price': pos.get('current_price', 0),
            'pnl_pct': pnl,
            'days_held': calculate_days_held(pos.get('entry_date', '')),
            'theme': pos.get('theme', ''),
            'conviction': pos.get('conviction', 3),
            'show_entry': can_show and include_entry_price,
        }
        winners.append(winner)

    # Sort by P&L descending
    winners.sort(key=lambda x: x['pnl_pct'], reverse=True)

    return winners[:max_positions]


def calculate_days_held(entry_date: str) -> int:
    """Calculate days held from entry date string."""
    if not entry_date:
        return 0
    try:
        entry = datetime.strptime(entry_date, '%Y-%m-%d')
        return (datetime.now() - entry).days
    except (ValueError, TypeError):
        return 0


def format_weeks_held(days: int) -> str:
    """Format days as weeks for display."""
    if days <= 0:
        return "held"
    elif days < 7:
        return f"{days} days"
    else:
        weeks = days // 7
        return f"{weeks}w held"


def format_winner_line(winner: Dict, show_entry: bool = True) -> str:
    """
    Format a winning position for display.

    Args:
        winner: Winner dict with ticker, entry_price, current_price, pnl_pct
        show_entry: Whether to show entry price (only if above 25%)

    Returns:
        Formatted line like "$TICKER: $XX.XX -> $XX.XX (+XX.X%)"
    """
    ticker = winner.get('ticker', 'UNKNOWN')
    entry = winner.get('entry_price', 0)
    current = winner.get('current_price', 0)
    pnl = winner.get('pnl_pct', 0)
    days = winner.get('days_held', 0)
    weeks_str = format_weeks_held(days)

    if show_entry and winner.get('show_entry') and entry and entry > 0:
        return f"${ticker}: ${entry:.2f} -> ${current:.2f} (+{pnl:.1f}%, {weeks_str})"
    else:
        return f"${ticker}: +{pnl:.1f}% ({weeks_str})"


def generate_winner_showcase_tweet() -> Optional[str]:
    """
    Generate a winner showcase tweet with entry prices for 25%+ positions.

    Returns:
        Tweet text or None if no winners above threshold
    """
    winners = get_winners_for_showcase(threshold=25.0, max_positions=5)

    if not winners:
        return None

    green_emoji = get_signal_emoji('GREEN')

    lines = [f"{green_emoji} GREEN Signal Winners\n"]
    lines.append("Top performers since entry:\n")

    for winner in winners:
        ticker = winner['ticker']
        pnl = winner['pnl_pct']
        conviction = winner.get('conviction', 3)
        conviction_text = get_conviction_text(conviction)

        if winner.get('show_entry') and winner.get('entry_price'):
            entry = winner['entry_price']
            current = winner['current_price']
            lines.append(f"${ticker}: ${entry:.2f} -> ${current:.2f} (+{pnl:.1f}%)")
        else:
            lines.append(f"${ticker}: +{pnl:.1f}%")

    lines.append("")
    lines.append("Entry prices shown for 25%+ gains.")
    lines.append("Returns measured from GREEN signal entry.")
    lines.append(f"\n{BRANDING['substack_url']}")

    tweet = "\n".join(lines)

    # Ensure under 280 characters
    if len(tweet) > 280:
        # Truncate to fewer winners
        return generate_winner_showcase_tweet_short(winners[:3])

    return tweet


def generate_winner_showcase_tweet_short(winners: List[Dict]) -> str:
    """Generate a shorter version of the winner showcase tweet."""
    green_emoji = get_signal_emoji('GREEN')

    lines = [f"{green_emoji} GREEN Winners\n"]

    for winner in winners[:3]:
        ticker = winner['ticker']
        pnl = winner['pnl_pct']
        lines.append(f"${ticker}: +{pnl:.1f}%")

    lines.append(f"\n{BRANDING['substack_url']}")

    return "\n".join(lines)


def generate_winner_json() -> Dict:
    """Generate JSON structure for winners."""
    winners = get_winners_for_showcase(threshold=15.0, max_positions=10)

    return {
        'generated_at': datetime.now().isoformat(),
        'threshold_pct': 15.0,
        'entry_price_threshold': ENTRY_PRICE_RULES['threshold_pct'],
        'winners': winners,
        'count': len(winners),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate winner showcase content"
    )
    parser.add_argument("--tweet", action="store_true",
                       help="Generate winner showcase tweet")
    parser.add_argument("--json", action="store_true",
                       help="Output winners as JSON")
    parser.add_argument("--list", action="store_true",
                       help="List all winners above 25%")
    parser.add_argument("--threshold", type=float, default=25.0,
                       help="Minimum P&L threshold (default: 25%%)")

    args = parser.parse_args()

    if not any([args.tweet, args.json, args.list]):
        parser.print_help()
        return

    print("=" * 60)
    print("  WINNER SHOWCASE GENERATOR")
    print("=" * 60)

    if args.list:
        winners = get_winners_for_showcase(threshold=args.threshold)
        if not winners:
            print(f"\nNo winners above {args.threshold}% threshold")
            return

        print(f"\nWinners above {args.threshold}%:\n")
        for w in winners:
            line = format_winner_line(w)
            entry_note = " [entry shown]" if w.get('show_entry') else ""
            print(f"  {line}{entry_note}")

    if args.tweet:
        tweet = generate_winner_showcase_tweet()
        if tweet:
            print(f"\nGenerated Tweet ({len(tweet)} chars):\n")
            print("-" * 40)
            print(tweet)
            print("-" * 40)
        else:
            print("\nNo winners above threshold for tweet")

    if args.json:
        data = generate_winner_json()
        print("\nJSON Output:\n")
        print(json.dumps(data, indent=2))

    print("\nDone!")


if __name__ == "__main__":
    main()
