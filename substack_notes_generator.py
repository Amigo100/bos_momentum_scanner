#!/usr/bin/env python3
"""
SUBSTACK NOTES GENERATOR
========================

Generates Tuesday and Thursday Substack Notes for mid-week engagement.

- Tuesday Note: "Portfolio Pulse" - YTD status, position updates
- Thursday Note: "Trade Spotlight" - New/ongoing trade highlights

Usage:
    python substack_notes_generator.py              # Generate both notes
    python substack_notes_generator.py --tuesday    # Generate Tuesday note only
    python substack_notes_generator.py --thursday   # Generate Thursday note only
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("Required: pip install yfinance pandas")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"

# Import marketing vocabulary for validation
try:
    from marketing_vocabulary import validate_content, BANNED_TERMS
    MARKETING_VOCABULARY_AVAILABLE = True
except ImportError:
    MARKETING_VOCABULARY_AVAILABLE = False
    BANNED_TERMS = []


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_week_dir() -> Path:
    """Get the current week's output directory (YYYY-WXX format)."""
    today = datetime.now()
    iso_cal = today.isocalendar()
    return TRADES_DIR / "weeks" / f"{iso_cal.year}-W{iso_cal.week:02d}"


def get_current_dir() -> Path:
    """Get the 'current' output directory for latest outputs."""
    return TRADES_DIR / "current"


def ensure_output_dirs() -> Tuple[Path, Path]:
    """
    Ensure both current/ and weeks/YYYY-WXX/ directories exist.
    Returns (current_dir, week_dir)
    """
    current_dir = get_current_dir()
    week_dir = get_current_week_dir()

    # Create directories
    (current_dir / "substack_notes").mkdir(parents=True, exist_ok=True)
    (week_dir / "substack_notes").mkdir(parents=True, exist_ok=True)

    return current_dir, week_dir


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_portfolio() -> List[Dict]:
    """Load portfolio from CSV."""
    import csv
    portfolio_file = TRADES_DIR / "portfolio.csv"

    if not portfolio_file.exists():
        return []

    trades = []
    with open(portfolio_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)

    return trades


def load_signals() -> Dict:
    """Load latest signals.json."""
    signals_file = TRADES_DIR / "signals.json"

    # Also check current/ directory
    current_signals = get_current_dir() / "signals.json"

    if current_signals.exists():
        with open(current_signals, 'r') as f:
            return json.load(f)
    elif signals_file.exists():
        with open(signals_file, 'r') as f:
            return json.load(f)

    return {}


def get_live_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch current prices for tickers."""
    if not tickers:
        return {}

    prices = {}
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if len(tickers) == 1:
            prices[tickers[0]] = float(data['Close'].iloc[-1])
        else:
            for ticker in tickers:
                try:
                    prices[ticker] = float(data['Close'][ticker].iloc[-1])
                except (KeyError, IndexError):
                    pass
    except Exception as e:
        print(f"  Warning: Could not fetch prices: {e}")

    return prices


def calculate_portfolio_stats(portfolio: List[Dict], prices: Dict[str, float]) -> Dict:
    """Calculate portfolio performance statistics."""
    open_positions = [t for t in portfolio if t.get('status') == 'OPEN']
    closed_positions = [t for t in portfolio if t.get('status') in ['CLOSED', 'STOPPED']]

    # Calculate P&L for each open position
    position_pnl = []
    total_pnl_pct = 0

    for trade in open_positions:
        ticker = trade.get('ticker', '')
        entry_price = float(trade.get('entry_price') or 0)
        current_price = prices.get(ticker, entry_price)

        if entry_price > 0 and current_price > 0:
            pnl_pct = ((current_price / entry_price) - 1) * 100
            position_pnl.append({
                'ticker': ticker,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'theme': trade.get('theme', ''),
                'entry_date': trade.get('entry_date', '')
            })
            total_pnl_pct += pnl_pct

    # Sort by P&L
    position_pnl.sort(key=lambda x: x['pnl_pct'], reverse=True)

    # Calculate win rate from closed trades
    winners = len([t for t in closed_positions if float(t.get('exit_price') or 0) > float(t.get('entry_price') or 0)])
    losers = len(closed_positions) - winners
    win_rate = (winners / len(closed_positions) * 100) if closed_positions else 0

    # Find top and bottom performers
    top_performer = position_pnl[0] if position_pnl else None
    bottom_performer = position_pnl[-1] if position_pnl else None

    # Calculate average P&L (simple average across positions)
    avg_pnl = total_pnl_pct / len(open_positions) if open_positions else 0

    return {
        'open_count': len(open_positions),
        'closed_count': len(closed_positions),
        'total_count': len(portfolio),
        'avg_pnl_pct': avg_pnl,
        'total_unrealized_pnl': total_pnl_pct,
        'win_rate': win_rate,
        'winners': winners,
        'losers': losers,
        'top_performer': top_performer,
        'bottom_performer': bottom_performer,
        'positions': position_pnl
    }


def get_spy_ytd_return() -> float:
    """Get S&P 500 YTD return for comparison."""
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="1y")

        # Find first trading day of year
        year_start = datetime(datetime.now().year, 1, 1)
        ytd_data = hist[hist.index >= pd.Timestamp(year_start)]

        if len(ytd_data) >= 2:
            return ((ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1) * 100
    except Exception:
        pass

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_week_number() -> int:
    """Get current ISO week number."""
    return datetime.now().isocalendar().week


def generate_tuesday_note(portfolio: List[Dict], prices: Dict[str, float]) -> str:
    """
    Generate Tuesday 'Portfolio Pulse' note.

    Focus: YTD performance, position updates, quick stats.
    """
    stats = calculate_portfolio_stats(portfolio, prices)
    spy_ytd = get_spy_ytd_return()
    week_num = get_week_number()

    # Build the note
    lines = []
    lines.append(f"Portfolio Pulse - Week {week_num}")
    lines.append("")

    # Performance header
    if stats['avg_pnl_pct'] != 0:
        pnl_emoji = "📈" if stats['avg_pnl_pct'] > 0 else "📉"
        lines.append(f"{pnl_emoji} Average Position P&L: {stats['avg_pnl_pct']:+.1f}%")

    lines.append(f"📊 Open Positions: {stats['open_count']}")

    if stats['closed_count'] > 0:
        lines.append(f"🎯 Win Rate: {stats['win_rate']:.0f}% ({stats['winners']}W / {stats['losers']}L)")

    lines.append("")

    # Top performer
    if stats['top_performer']:
        top = stats['top_performer']
        lines.append(f"⭐ Top Performer: ${top['ticker']} ({top['pnl_pct']:+.1f}%)")
        lines.append(f"   Theme: {top['theme']}")

    lines.append("")

    # Position summary table
    if stats['positions']:
        lines.append("Current Positions:")
        for pos in stats['positions'][:5]:  # Top 5 positions
            emoji = "🟢" if pos['pnl_pct'] > 0 else "🔴" if pos['pnl_pct'] < 0 else "⚪"
            lines.append(f"{emoji} ${pos['ticker']}: {pos['pnl_pct']:+.1f}%")

    lines.append("")

    # SPY comparison
    if spy_ytd != 0:
        alpha = stats['avg_pnl_pct'] - spy_ytd
        alpha_emoji = "✅" if alpha > 0 else "❌"
        lines.append(f"📊 S&P 500 YTD: {spy_ytd:+.1f}%")
        lines.append(f"{alpha_emoji} Alpha: {alpha:+.1f}%")

    lines.append("")
    lines.append("Full analysis in Saturday's Sterling Signals newsletter →")

    return "\n".join(lines)


def generate_thursday_note(signals: Dict, portfolio: List[Dict], prices: Dict[str, float]) -> str:
    """
    Generate Thursday 'Trade Spotlight' note.

    Focus: New signals, ongoing trade highlights, week outlook.
    """
    week_num = get_week_number()

    lines = []
    lines.append(f"Trade Spotlight - Week {week_num}")
    lines.append("")

    # Get TRADE signals from this week's scan
    buy_signals = signals.get('buy_signals', [])
    trade_signals = [s for s in buy_signals if s.get('final_decision') == 'TRADE']
    consider_signals = [s for s in buy_signals if s.get('final_decision') == 'CONSIDER']

    # Highlight a trade signal
    if trade_signals:
        signal = trade_signals[0]  # Feature first TRADE signal
        lines.append(f"🎯 This Week's Signal: ${signal['symbol']}")
        lines.append(f"Theme: {signal.get('theme', 'N/A')}")
        lines.append(f"Conviction: {signal.get('conviction', 'N/A')}/5")
        lines.append("")

        # Key points
        bullish = signal.get('bullish_factors', [])
        if bullish:
            lines.append("Why we like it:")
            for factor in bullish[:3]:  # Top 3 factors
                # Truncate long factors
                factor_short = factor[:80] + "..." if len(factor) > 80 else factor
                lines.append(f"• {factor_short}")

        lines.append("")

        # Risk note
        risks = signal.get('risk_factors', [])
        if risks:
            lines.append(f"⚠️ Key risk: {risks[0][:80]}...")

    elif consider_signals:
        # Highlight a watchlist signal instead
        signal = consider_signals[0]
        lines.append(f"👀 On the Watchlist: ${signal['symbol']}")
        lines.append(f"Theme: {signal.get('theme', 'N/A')}")
        lines.append(f"Status: CONSIDER (not yet actionable)")
        lines.append("")
        lines.append(f"Reasoning: {signal.get('reasoning', '')[:150]}...")

    else:
        lines.append("📊 No new signals this week")
        lines.append("")
        lines.append("Scanner found limited setups meeting our criteria.")
        lines.append("Sometimes the best trade is no trade.")

    lines.append("")

    # Scan stats
    stats = signals.get('stats', {})
    if stats:
        lines.append("📈 This Week's Scan:")
        lines.append(f"• {stats.get('tickers_loaded', 0)} stocks scanned")
        lines.append(f"• {stats.get('technical_signals', 0)} passed technical gate")
        lines.append(f"• {stats.get('final_trade', 0)} TRADE signals")
        lines.append(f"• {stats.get('final_consider', 0)} CONSIDER signals")

    lines.append("")

    # Portfolio context
    open_positions = [t for t in portfolio if t.get('status') == 'OPEN']
    if open_positions:
        stats_calc = calculate_portfolio_stats(portfolio, prices)
        lines.append(f"📊 Portfolio: {len(open_positions)} positions")
        if stats_calc['top_performer']:
            top = stats_calc['top_performer']
            lines.append(f"🏆 Leading: ${top['ticker']} ({top['pnl_pct']:+.1f}%)")

    lines.append("")
    lines.append("Full analysis in Saturday's Sterling Signals newsletter →")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_note(content: str, filename: str, current_dir: Path, week_dir: Path):
    """Save note to both current/ and weekly archive directories."""
    # Validate content for banned marketing terms
    if MARKETING_VOCABULARY_AVAILABLE:
        is_valid, violations = validate_content(content)
        if not is_valid:
            print(f"  ⚠️  WARNING: Note '{filename}' contains banned terms: {violations}")
            print("      Review content before publishing to Substack.")

    # Save to current/
    current_path = current_dir / "substack_notes" / filename
    with open(current_path, 'w') as f:
        f.write(content)

    # Save to weekly archive
    week_path = week_dir / "substack_notes" / filename
    with open(week_path, 'w') as f:
        f.write(content)

    return current_path, week_path


def generate_all_notes() -> Dict[str, Path]:
    """
    Generate both Tuesday and Thursday notes.

    Returns dict of {note_name: path} for generated files.
    """
    print("\n" + "=" * 60)
    print("  SUBSTACK NOTES GENERATOR")
    print("=" * 60)

    # Ensure output directories exist
    current_dir, week_dir = ensure_output_dirs()
    print(f"\n  Output directories:")
    print(f"    Current: {current_dir}/substack_notes/")
    print(f"    Archive: {week_dir}/substack_notes/")

    # Load data
    print("\n  Loading data...")
    portfolio = load_portfolio()
    signals = load_signals()

    # Get tickers for price lookup
    open_tickers = [t['ticker'] for t in portfolio if t.get('status') == 'OPEN']

    print(f"    Portfolio: {len(portfolio)} trades ({len(open_tickers)} open)")
    print(f"    Signals: {len(signals.get('buy_signals', []))} buy signals")

    # Fetch prices
    print("\n  Fetching live prices...")
    prices = get_live_prices(open_tickers)
    print(f"    Got prices for {len(prices)} tickers")

    results = {}

    # Generate Tuesday note
    print("\n  Generating Tuesday note (Portfolio Pulse)...")
    tuesday_content = generate_tuesday_note(portfolio, prices)
    tuesday_current, tuesday_archive = save_note(
        tuesday_content, "tuesday_note.md", current_dir, week_dir
    )
    results['tuesday'] = tuesday_current
    print(f"    ✓ Saved to {tuesday_current}")

    # Generate Thursday note
    print("\n  Generating Thursday note (Trade Spotlight)...")
    thursday_content = generate_thursday_note(signals, portfolio, prices)
    thursday_current, thursday_archive = save_note(
        thursday_content, "thursday_note.md", current_dir, week_dir
    )
    results['thursday'] = thursday_current
    print(f"    ✓ Saved to {thursday_current}")

    # Print preview
    print("\n" + "=" * 60)
    print("  TUESDAY NOTE PREVIEW")
    print("=" * 60)
    print(tuesday_content)

    print("\n" + "=" * 60)
    print("  THURSDAY NOTE PREVIEW")
    print("=" * 60)
    print(thursday_content)

    print("\n" + "=" * 60)
    print("  SUBSTACK NOTES COMPLETE")
    print("=" * 60)
    print(f"\n  Files ready for Substack:")
    print(f"    Tuesday:  {results['tuesday']}")
    print(f"    Thursday: {results['thursday']}")
    print("")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Substack Notes for mid-week engagement"
    )
    parser.add_argument(
        "--tuesday", action="store_true",
        help="Generate Tuesday note only"
    )
    parser.add_argument(
        "--thursday", action="store_true",
        help="Generate Thursday note only"
    )

    args = parser.parse_args()

    # Load common data
    portfolio = load_portfolio()
    signals = load_signals()
    open_tickers = [t['ticker'] for t in portfolio if t.get('status') == 'OPEN']
    prices = get_live_prices(open_tickers)
    current_dir, week_dir = ensure_output_dirs()

    if args.tuesday:
        content = generate_tuesday_note(portfolio, prices)
        save_note(content, "tuesday_note.md", current_dir, week_dir)
        print(content)
    elif args.thursday:
        content = generate_thursday_note(signals, portfolio, prices)
        save_note(content, "thursday_note.md", current_dir, week_dir)
        print(content)
    else:
        # Generate both
        generate_all_notes()

    return 0


if __name__ == "__main__":
    sys.exit(main())
