#!/usr/bin/env python3
"""
SUBSTACK CONTENT GENERATOR
==========================

Generates formatted content for Substack posts following the Sterling Signals
color signal system (GREEN/RED/CONSIDER).

Content Calendar:
- Monday: Market Analysis - Market context + top performers
- Thursday: Theme Spotlight - Hot theme deep dive
- Saturday: Weekly Signals - Full GREEN/RED/CONSIDER recap
- Sunday: Deep Dive - Single stock analysis

Usage:
    python substack_content_generator.py --monday
    python substack_content_generator.py --thursday
    python substack_content_generator.py --saturday
    python substack_content_generator.py --sunday --ticker NVDA
    python substack_content_generator.py --all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    BASE_DIR,
    TRADES_DIR,
    SIGNAL_COLORS,
    CONVICTION_LANGUAGE,
    SUBSTACK_CONTENT,
    BRANDING,
    get_signal_emoji,
    get_conviction_text,
    can_show_entry_price,
)
from marketing_vocabulary import validate_content, APPROVED_VOCABULARY

# Output directory
SUBSTACK_DIR = TRADES_DIR / "substack_posts"


def load_signals() -> Dict:
    """Load the latest signals from signals.json."""
    signals_file = TRADES_DIR / "signals.json"
    if signals_file.exists():
        return json.loads(signals_file.read_text())
    return {}


def load_portfolio() -> List[Dict]:
    """Load open positions from portfolio.csv."""
    import csv
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if not portfolio_file.exists():
        return []

    positions = []
    with open(portfolio_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'OPEN':
                positions.append(row)
    return positions


def load_themes() -> List[Dict]:
    """Load themes from the latest signals."""
    signals = load_signals()
    return signals.get('themes', [])


def format_winner_line(position: Dict, show_entry: bool = False) -> str:
    """Format a winning position for display.

    Args:
        position: Position dict with ticker, entry_price, current_price, pnl_pct
        show_entry: Whether to include entry price

    Returns:
        Formatted line like "$TICKER: $XX.XX -> $XX.XX (+XX.X%)"
    """
    ticker = position.get('ticker', 'UNKNOWN')
    entry = float(position.get('entry_price', 0))
    current = float(position.get('current_price', entry))
    pnl = float(position.get('pnl_pct', 0))

    if show_entry and entry > 0:
        return f"${ticker}: ${entry:.2f} -> ${current:.2f} (+{pnl:.1f}%)"
    else:
        return f"${ticker}: +{pnl:.1f}%"


def generate_monday_market_analysis() -> str:
    """Generate Monday market analysis content.

    Content: Market context + top performers from the week.
    """
    signals = load_signals()
    positions = load_portfolio()
    themes = load_themes()

    # Get date range
    today = datetime.now()
    week_start = today.strftime("%B %d, %Y")

    content = f"""# Market Outlook: Week of {week_start}

{get_signal_emoji('GREEN')} **GREEN Signals Active**

## Market Context

The momentum scanner continues to identify high-conviction setups across
the equity market. This week's analysis focuses on theme alignment and
institutional flow patterns.

## Top Themes This Week

"""
    # Add top themes
    prime_themes = [t for t in themes if t.get('classification') == 'PRIME']
    investable_themes = [t for t in themes if t.get('classification') == 'INVESTABLE']

    if prime_themes:
        content += "### PRIME Themes (Highest Conviction)\n\n"
        for theme in prime_themes[:2]:
            name = theme.get('name', 'Unknown Theme')
            score = theme.get('composite_score', 0)
            thesis = theme.get('thesis_summary', '')
            content += f"**{name}** - Score: {score:.1f}/10\n"
            if thesis:
                content += f"> {thesis[:200]}...\n\n"

    if investable_themes:
        content += "### INVESTABLE Themes\n\n"
        for theme in investable_themes[:3]:
            name = theme.get('name', 'Unknown Theme')
            score = theme.get('composite_score', 0)
            content += f"- **{name}** - Score: {score:.1f}/10\n"
        content += "\n"

    # Add top performers
    winners = [p for p in positions if float(p.get('pnl_pct', 0)) > 0]
    winners.sort(key=lambda x: float(x.get('pnl_pct', 0)), reverse=True)

    if winners:
        content += "## Portfolio Highlights\n\n"
        for w in winners[:5]:
            pnl = float(w.get('pnl_pct', 0))
            # Only show entry if above threshold
            show_entry = pnl >= 25.0
            content += f"- {format_winner_line(w, show_entry)}\n"
        content += "\n"

    content += f"""
---

*{BRANDING['signal_tagline']}*

Full analysis and GREEN signals: {BRANDING['substack_url']}
"""

    return content


def generate_thursday_theme_spotlight() -> str:
    """Generate Thursday theme spotlight content.

    Content: Deep dive on the hottest theme of the week.
    """
    themes = load_themes()
    signals = load_signals()

    # Get the top theme
    prime_themes = [t for t in themes if t.get('classification') == 'PRIME']
    if not prime_themes:
        prime_themes = [t for t in themes if t.get('classification') == 'INVESTABLE']

    if not prime_themes:
        return "# Theme Watch\n\nNo high-conviction themes identified this week."

    top_theme = prime_themes[0]
    theme_name = top_theme.get('name', 'Unknown Theme')
    theme_type = top_theme.get('theme_type', 'TREND')
    score = top_theme.get('composite_score', 0)
    thesis = top_theme.get('thesis_summary', '')
    catalysts = top_theme.get('key_catalysts', [])

    content = f"""# Theme Watch: {theme_name}

{get_signal_emoji('GREEN')} **Theme Classification: {top_theme.get('classification', 'INVESTABLE')}**

## Overview

**Theme Type:** {theme_type}
**Composite Score:** {score:.1f}/10

{thesis}

## Key Catalysts

"""
    for catalyst in catalysts[:5]:
        content += f"- {catalyst}\n"

    # Get stocks in this theme
    buy_signals = signals.get('buy_signals', [])
    theme_stocks = [s for s in buy_signals if s.get('theme', '').lower() == theme_name.lower()]

    if theme_stocks:
        content += f"""
## {get_signal_emoji('GREEN')} GREEN Signals in This Theme

"""
        for stock in theme_stocks[:5]:
            ticker = stock.get('symbol', 'UNKNOWN')
            conviction = stock.get('conviction', 3)
            conviction_text = get_conviction_text(conviction)
            content += f"- **${ticker}** - {conviction_text}\n"

    content += f"""
---

*The 5-Gate System continues to identify high-conviction setups.*

{BRANDING['substack_url']}
"""

    return content


def generate_saturday_weekly_signals() -> str:
    """Generate Saturday weekly signals recap.

    Content: Full GREEN/RED/CONSIDER recap for the week.
    """
    signals = load_signals()
    positions = load_portfolio()

    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")

    content = f"""# GREEN Signals: {date_str}

## Weekly Signal Recap

"""

    # GREEN signals (PASS)
    buy_signals = signals.get('buy_signals', [])
    if buy_signals:
        content += f"### {get_signal_emoji('GREEN')} GREEN Signals (Full Entry)\n\n"
        for signal in buy_signals:
            ticker = signal.get('symbol', 'UNKNOWN')
            theme = signal.get('theme', 'Unknown')
            conviction = signal.get('conviction', 3)
            conviction_text = get_conviction_text(conviction)
            price = signal.get('price', 0)

            content += f"**${ticker}** at ${price:.2f}\n"
            content += f"- Theme: {theme}\n"
            content += f"- Conviction: {conviction_text}\n\n"

    # CONSIDER signals (watchlist)
    caution_signals = signals.get('caution_signals', [])
    consider_signals = [s for s in signals.get('buy_signals', [])
                       if s.get('final_decision') == 'CONSIDER']

    watchlist = caution_signals + consider_signals
    if watchlist:
        content += f"### {get_signal_emoji('CONSIDER')} CONSIDER Watchlist\n\n"
        content += "These stocks cleared 4/5 gates - watching for GREEN:\n\n"
        for signal in watchlist[:5]:
            ticker = signal.get('symbol', 'UNKNOWN')
            reason = signal.get('reason', signal.get('catalyst_summary', 'Under review'))
            content += f"- **${ticker}** - {reason[:100]}\n"
        content += "\n"

    # RED alerts (exits)
    sell_signals = signals.get('sell_signals', [])
    profitable_exits = [s for s in sell_signals if float(s.get('pnl_pct', 0)) > 0]

    if profitable_exits:
        content += f"### {get_signal_emoji('RED')} RED Alerts (Exits)\n\n"
        for signal in profitable_exits:
            ticker = signal.get('symbol', 'UNKNOWN')
            pnl = float(signal.get('pnl_pct', 0))
            reason = signal.get('reason', 'Systematic exit')
            content += f"- **${ticker}** +{pnl:.1f}% - {reason}\n"
        content += "\n"

    # Stats
    stats = signals.get('stats', {})
    if stats:
        content += f"""## Scan Statistics

- Tickers Scanned: {stats.get('tickers_loaded', 'N/A')}
- Weekly Momentum Up: {stats.get('weekly_bos_up', 'N/A')}
- Theme Confirmed: {stats.get('theme_confirmed', 'N/A')}
- Final GREEN Signals: {stats.get('final_trade', 0)}

"""

    content += f"""---

*{BRANDING['signal_tagline']}*

Full analysis: {BRANDING['substack_url']}
"""

    return content


def generate_sunday_deep_dive(ticker: Optional[str] = None) -> str:
    """Generate Sunday deep dive content.

    Content: Single stock analysis for the top GREEN signal.

    Args:
        ticker: Optional specific ticker to analyze. If None, uses top signal.
    """
    signals = load_signals()
    buy_signals = signals.get('buy_signals', [])

    if not buy_signals:
        return "# Deep Dive\n\nNo GREEN signals available for deep dive."

    # Find the target stock
    target = None
    if ticker:
        target = next((s for s in buy_signals if s.get('symbol', '').upper() == ticker.upper()), None)

    if not target:
        # Use the highest conviction signal
        buy_signals.sort(key=lambda x: x.get('conviction', 0), reverse=True)
        target = buy_signals[0]

    ticker = target.get('symbol', 'UNKNOWN')
    theme = target.get('theme', 'Unknown')
    conviction = target.get('conviction', 3)
    conviction_text = get_conviction_text(conviction)
    price = target.get('price', 0)
    beta = target.get('beta', 0)
    catalyst_summary = target.get('catalyst_summary', '')
    bullish_factors = target.get('bullish_factors', [])
    risk_factors = target.get('risk_factors', [])
    reasoning = target.get('reasoning', '')

    content = f"""# Deep Dive: ${ticker}

{get_signal_emoji('GREEN')} **GREEN Signal Analysis**

## Overview

| Metric | Value |
|--------|-------|
| Price | ${price:.2f} |
| Theme | {theme} |
| Conviction | {conviction_text} |
| Beta | {beta:.2f} |

## Thesis

{reasoning[:500] if reasoning else 'Cleared all 5 gates with strong theme alignment.'}

## Catalyst Summary

{catalyst_summary if catalyst_summary else 'Near-term catalysts identified through systematic analysis.'}

## Bullish Factors

"""
    for factor in bullish_factors[:5]:
        content += f"- {factor}\n"

    content += "\n## Risk Factors\n\n"
    for factor in risk_factors[:5]:
        content += f"- {factor}\n"

    content += f"""
## Bottom Line

${ticker} has cleared all 5 gates of our systematic screening process.
The combination of theme alignment, technical momentum, and catalyst timing
makes this a high-conviction GREEN signal.

---

*{BRANDING['signal_tagline']}*

{BRANDING['substack_url']}
"""

    return content


def save_content(content: str, filename: str) -> Path:
    """Save content to the substack_posts directory.

    Args:
        content: The generated content
        filename: Output filename

    Returns:
        Path to the saved file
    """
    SUBSTACK_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SUBSTACK_DIR / filename

    # Validate content before saving
    is_valid, violations = validate_content(content)
    if not is_valid:
        print(f"  WARNING: Content contains banned terms: {violations}")

    output_path.write_text(content)
    return output_path


def generate_all():
    """Generate all Substack content for the week."""
    today = datetime.now()
    date_suffix = today.strftime("%Y%m%d")

    results = []

    # Monday market analysis
    content = generate_monday_market_analysis()
    path = save_content(content, f"monday_market_analysis_{date_suffix}.md")
    results.append(("Monday Market Analysis", path))

    # Thursday theme spotlight
    content = generate_thursday_theme_spotlight()
    path = save_content(content, f"thursday_theme_spotlight_{date_suffix}.md")
    results.append(("Thursday Theme Spotlight", path))

    # Saturday weekly signals
    content = generate_saturday_weekly_signals()
    path = save_content(content, f"saturday_weekly_signals_{date_suffix}.md")
    results.append(("Saturday Weekly Signals", path))

    # Sunday deep dive
    content = generate_sunday_deep_dive()
    path = save_content(content, f"sunday_deep_dive_{date_suffix}.md")
    results.append(("Sunday Deep Dive", path))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate Substack content for Sterling Signals"
    )
    parser.add_argument("--monday", action="store_true",
                       help="Generate Monday market analysis")
    parser.add_argument("--thursday", action="store_true",
                       help="Generate Thursday theme spotlight")
    parser.add_argument("--saturday", action="store_true",
                       help="Generate Saturday weekly signals recap")
    parser.add_argument("--sunday", action="store_true",
                       help="Generate Sunday deep dive")
    parser.add_argument("--ticker", type=str,
                       help="Ticker for Sunday deep dive (optional)")
    parser.add_argument("--all", action="store_true",
                       help="Generate all content types")
    parser.add_argument("--dry-run", action="store_true",
                       help="Print content without saving")

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.monday, args.thursday, args.saturday, args.sunday, args.all]):
        parser.print_help()
        return

    print("=" * 60)
    print("  SUBSTACK CONTENT GENERATOR")
    print("=" * 60)

    today = datetime.now()
    date_suffix = today.strftime("%Y%m%d")

    if args.all:
        print("\nGenerating all Substack content...")
        results = generate_all()
        print("\nGenerated files:")
        for name, path in results:
            print(f"  {name}: {path}")
        return

    if args.monday:
        print("\nGenerating Monday Market Analysis...")
        content = generate_monday_market_analysis()
        if args.dry_run:
            print(content)
        else:
            path = save_content(content, f"monday_market_analysis_{date_suffix}.md")
            print(f"  Saved to: {path}")

    if args.thursday:
        print("\nGenerating Thursday Theme Spotlight...")
        content = generate_thursday_theme_spotlight()
        if args.dry_run:
            print(content)
        else:
            path = save_content(content, f"thursday_theme_spotlight_{date_suffix}.md")
            print(f"  Saved to: {path}")

    if args.saturday:
        print("\nGenerating Saturday Weekly Signals...")
        content = generate_saturday_weekly_signals()
        if args.dry_run:
            print(content)
        else:
            path = save_content(content, f"saturday_weekly_signals_{date_suffix}.md")
            print(f"  Saved to: {path}")

    if args.sunday:
        print(f"\nGenerating Sunday Deep Dive{' for ' + args.ticker if args.ticker else ''}...")
        content = generate_sunday_deep_dive(args.ticker)
        if args.dry_run:
            print(content)
        else:
            ticker_suffix = f"_{args.ticker}" if args.ticker else ""
            path = save_content(content, f"sunday_deep_dive{ticker_suffix}_{date_suffix}.md")
            print(f"  Saved to: {path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
