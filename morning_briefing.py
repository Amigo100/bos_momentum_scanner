#!/usr/bin/env python3
"""
Morning Briefing Generator
===========================
Transforms raw scanner JSON + portfolio data into a structured narrative
briefing for the Editorial Board. This is the single source of truth that
both the Editorial Board and Writer Room consume.
"""

from typing import List


def generate_morning_briefing(
    scanner_data: dict,
    portfolio_data: dict,
    day_name: str,
    week_tracker: dict = None,
) -> str:
    """
    Convert raw data into a readable narrative briefing.

    Args:
        scanner_data: Output from scanner (pass_signals, consider_signals, themes, etc.)
        portfolio_data: Output from portfolio manager (positions, closed_trades, vs_spy)
        day_name: Day of the week
        week_tracker: Optional dict tracking what's been covered earlier in the week
    """

    pass_signals = scanner_data.get('pass_signals', [])
    consider_signals = scanner_data.get('consider_signals', [])
    prime_themes = scanner_data.get('prime_themes', [])
    investable_themes = scanner_data.get('investable_themes', [])
    cold_themes = scanner_data.get('cold_themes', [])
    scan_stats = scanner_data.get('scan_stats', {})

    positions = portfolio_data.get('positions', [])
    closed = portfolio_data.get('closed_trades', [])
    vs_spy = portfolio_data.get('vs_spy', 0)

    winners = [p for p in positions if p.get('pnl_pct', 0) >= 25]
    green = [p for p in positions if 0 < p.get('pnl_pct', 0) < 25]
    red = [p for p in positions if p.get('pnl_pct', 0) < 0]

    # Week coverage notes
    coverage_notes = ""
    if week_tracker:
        already_covered = week_tracker.get('tickers_featured', {})
        if already_covered:
            coverage_notes = "\nALREADY COVERED THIS WEEK:\n"
            for ticker, count in already_covered.items():
                coverage_notes += f"  - ${ticker}: featured {count}x (ease off)\n"

    briefing = f"""
MORNING BRIEFING - {day_name}
{'=' * 60}

SCANNER RESULTS (Friday's Close):
- Stocks Scanned: {scan_stats.get('stocks_scanned', '~1,800')}
- Passed All Gates: {len(pass_signals)}
- On Watchlist (Consider): {len(consider_signals)}

NEW SIGNALS:
{_format_signals(pass_signals)}

WATCHLIST (Not Yet Triggered):
{_format_signals(consider_signals)}

THEME ANALYSIS:
- Hot Themes: {_format_theme_names(prime_themes + investable_themes)}
- Cold Themes: {_format_theme_names(cold_themes)}

{'─' * 60}

PORTFOLIO STATE:
- Total Positions: {len(positions)}
- Green: {len(winners) + len(green)} | Red: {len(red)}
- vs SPY: {'+' if vs_spy > 0 else ''}{vs_spy:.1f}%

BIG WINNERS (25%+):
{_format_positions(winners)}

OTHER GREEN:
{_format_positions(green)}

RED (be honest about these):
{_format_positions(red)}

RECENTLY CLOSED:
{_format_closed(closed)}

{'─' * 60}
{coverage_notes}
AVAILABLE TICKERS FOR TODAY:
{_build_ticker_menu(pass_signals, consider_signals, positions)}

CONTENT ANGLES:
{_suggest_angles(pass_signals, consider_signals, winners, green, red, prime_themes, day_name)}

{'=' * 60}
"""
    return briefing


def _format_signals(signals: list) -> str:
    if not signals:
        return "  (None this week)"
    lines = []
    for s in signals:
        ticker = s.get('ticker', '?')
        price = s.get('close_price') or s.get('price', '?')
        theme = s.get('theme', '')
        lines.append(f"  ${ticker} @ ${price} - {theme}")
    return '\n'.join(lines)


def _format_theme_names(themes: list) -> str:
    if not themes:
        return "None identified"
    names = []
    for t in themes:
        if isinstance(t, dict):
            names.append(t.get('name', str(t)))
        else:
            names.append(str(t))
    return ', '.join(names)


def _format_positions(positions: list) -> str:
    if not positions:
        return "  (None)"
    lines = []
    for p in positions:
        ticker = p.get('ticker', '?')
        pnl = p.get('pnl_pct', 0)
        days = p.get('days_held', '?')
        entry = p.get('entry_price')
        entry_str = f" (entry ${entry})" if entry else ""
        lines.append(f"  ${ticker}: {pnl:+.1f}% over {days} days{entry_str}")
    return '\n'.join(lines)


def _format_closed(closed: list) -> str:
    if not closed:
        return "  (None recently)"
    lines = []
    for c in closed[:3]:
        ticker = c.get('ticker', '?')
        pnl = c.get('pnl_pct', 0)
        reason = c.get('exit_reason', '')
        lines.append(f"  ${ticker}: {pnl:+.1f}%{' - ' + reason if reason else ''}")
    return '\n'.join(lines)


def _build_ticker_menu(pass_signals, consider_signals, positions):
    """List all tickers available for content with suggested angles."""
    lines = []
    for s in pass_signals:
        lines.append(f"  ${s['ticker']} [NEW SIGNAL] - {s.get('theme', '?')}")
    for s in consider_signals:
        lines.append(f"  ${s['ticker']} [WATCHLIST] - {s.get('theme', '?')}")
    for p in positions:
        pnl = p.get('pnl_pct', 0)
        label = "WINNER" if pnl >= 25 else ("GREEN" if pnl > 0 else "RED")
        lines.append(f"  ${p['ticker']} [{label} {pnl:+.1f}%]")
    return '\n'.join(lines) if lines else "  (No tickers available)"


def _suggest_angles(pass_signals, consider_signals, winners, green, red, themes, day_name):
    """Suggest content angles based on available data."""
    angles = []

    if pass_signals:
        tickers = ', '.join(f"${s['ticker']}" for s in pass_signals)
        angles.append(f"New signals: {tickers} — what the scanner found")

    if consider_signals:
        tickers = ', '.join(f"${s['ticker']}" for s in consider_signals)
        angles.append(f"Watchlist analysis: {tickers} — what's missing for a full signal")

    if winners:
        angles.append(f"Winner story: ${winners[0]['ticker']} journey — patience/process angle")

    if red:
        angles.append(f"Honesty angle: ${red[0]['ticker']} is down — show discipline")

    if themes:
        name = themes[0].get('name', str(themes[0])) if isinstance(themes[0], dict) else str(themes[0])
        angles.append(f"Theme deep-dive: {name}")

    # Day-specific angles
    day_angles = {
        'Saturday': "Weekend reflection, newsletter just dropped",
        'Sunday': "Light day, prep for the week, mindset content",
        'Monday': "Fresh start energy, what matters this week",
        'Tuesday': "Check-in, educational moments",
        'Wednesday': "Midweek pulse, engagement questions",
        'Thursday': "Building anticipation for Friday's scan",
        'Friday': "Scan day energy, power hour, results anticipation",
    }
    if day_name in day_angles:
        angles.append(day_angles[day_name])

    return '\n'.join(f"  - {a}" for a in angles) if angles else "  - General market observations"
