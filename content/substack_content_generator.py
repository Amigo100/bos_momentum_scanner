#!/usr/bin/env python3
"""
SUBSTACK CONTENT GENERATOR
==========================

Generates rich HTML content for Substack posts following the Sterling Signals
TEAL/VIOLET/AMBER signal system.

Outputs to trades/current/substack_posts/ (with weekly archive).

Content Calendar:
- Monday: Market Analysis - Market context + top performers
- Thursday: Theme Spotlight - Hot theme deep dive
- Saturday: Weekly Signals - Full signal recap (pairs with newsletter)
- Sunday: Deep Dive - Single stock analysis

Usage:
    python -m content.substack_content_generator --monday
    python -m content.substack_content_generator --thursday
    python -m content.substack_content_generator --saturday
    python -m content.substack_content_generator --sunday --ticker NVDA
    python -m content.substack_content_generator --all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
from config.marketing_vocabulary import validate_content, APPROVED_VOCABULARY

# Try to import output_paths for dual-write
try:
    from config.output_paths import (
        get_current_dir,
        get_week_dir,
        ensure_output_structure,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# BRAND COLORS (matching Sterling Signals identity)
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    'teal': '#2DD4BF',          # TEAL signals (buy)
    'teal_bg': '#0D3B34',       # Dark teal background
    'teal_light': '#CCFBF1',    # Light teal text
    'violet': '#A78BFA',        # VIOLET signals (exit)
    'violet_bg': '#2E1065',     # Dark violet background
    'amber': '#FBBF24',         # AMBER signals (watch)
    'amber_bg': '#451A03',      # Dark amber background
    'green_gain': '#22C55E',    # Positive P&L
    'red_loss': '#EF4444',      # Negative P&L
    'dark_bg': '#111827',       # Page background
    'card_bg': '#1F2937',       # Card background
    'border': '#374151',        # Border color
    'text': '#F9FAFB',          # Primary text
    'text_muted': '#9CA3AF',    # Muted text
    'gold': '#F59E0B',          # Gold accents
}


# ═══════════════════════════════════════════════════════════════════════════════
# HTML HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _html_wrapper(title: str, body: str) -> str:
    """Wrap body content in a styled HTML page."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {COLORS['dark_bg']}; color: {COLORS['text']}; max-width: 680px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
  h1 {{ color: {COLORS['teal']}; border-bottom: 2px solid {COLORS['teal']}; padding-bottom: 8px; }}
  h2 {{ color: {COLORS['text']}; margin-top: 28px; }}
  h3 {{ color: {COLORS['text_muted']}; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
  .signal-badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 13px; letter-spacing: 0.5px; }}
  .teal {{ background: {COLORS['teal_bg']}; color: {COLORS['teal']}; border: 1px solid {COLORS['teal']}; }}
  .violet {{ background: {COLORS['violet_bg']}; color: {COLORS['violet']}; border: 1px solid {COLORS['violet']}; }}
  .amber {{ background: {COLORS['amber_bg']}; color: {COLORS['amber']}; border: 1px solid {COLORS['amber']}; }}
  .card {{ background: {COLORS['card_bg']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 20px; margin: 16px 0; }}
  .winner-card {{ border-left: 4px solid {COLORS['green_gain']}; }}
  .theme-card {{ border-left: 4px solid {COLORS['teal']}; }}
  .exit-card {{ border-left: 4px solid {COLORS['violet']}; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th {{ text-align: left; padding: 10px 12px; background: {COLORS['card_bg']}; color: {COLORS['text_muted']}; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid {COLORS['border']}; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid {COLORS['border']}; }}
  .pnl-pos {{ color: {COLORS['green_gain']}; font-weight: 700; }}
  .pnl-neg {{ color: {COLORS['red_loss']}; font-weight: 700; }}
  .ticker {{ font-weight: 700; color: {COLORS['teal']}; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 16px 0; }}
  .stat-box {{ background: {COLORS['card_bg']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 16px; text-align: center; }}
  .stat-value {{ font-size: 28px; font-weight: 800; color: {COLORS['teal']}; }}
  .stat-label {{ font-size: 12px; color: {COLORS['text_muted']}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
  .funnel {{ width: 100%; margin: 16px 0; }}
  .funnel-row {{ display: flex; align-items: center; margin: 4px 0; }}
  .funnel-bar {{ height: 28px; border-radius: 4px; display: flex; align-items: center; padding: 0 12px; font-size: 13px; font-weight: 600; color: white; }}
  .divider {{ border: none; border-top: 1px solid {COLORS['border']}; margin: 24px 0; }}
  .footer {{ text-align: center; color: {COLORS['text_muted']}; font-size: 13px; margin-top: 32px; padding-top: 16px; border-top: 1px solid {COLORS['border']}; }}
  .footer a {{ color: {COLORS['teal']}; text-decoration: none; }}
  .highlight {{ background: linear-gradient(135deg, {COLORS['teal_bg']}, {COLORS['card_bg']}); border: 1px solid {COLORS['teal']}; border-radius: 10px; padding: 20px; margin: 16px 0; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 6px 0; }}
</style>
</head>
<body>
{body}
<div class="footer">
  <p><em>{BRANDING['signal_tagline']}</em></p>
  <p><a href="{BRANDING['substack_url']}">Sterling Signals on Substack</a></p>
</div>
</body>
</html>"""


def _pnl_span(pnl: float) -> str:
    """Format P&L as colored HTML span."""
    css = 'pnl-pos' if pnl >= 0 else 'pnl-neg'
    sign = '+' if pnl >= 0 else ''
    return f'<span class="{css}">{sign}{pnl:.1f}%</span>'


def _signal_badge(signal_type: str) -> str:
    """Create a colored signal badge."""
    badge_map = {
        'GREEN': ('TEAL SIGNAL', 'teal'),
        'RED': ('VIOLET ALERT', 'violet'),
        'CONSIDER': ('AMBER WATCH', 'amber'),
        'TEAL': ('TEAL SIGNAL', 'teal'),
        'VIOLET': ('VIOLET ALERT', 'violet'),
        'AMBER': ('AMBER WATCH', 'amber'),
    }
    text, css = badge_map.get(signal_type.upper(), ('SIGNAL', 'teal'))
    return f'<span class="signal-badge {css}">{text}</span>'


def _stat_box(value: str, label: str) -> str:
    """Create a stat box for the grid."""
    return f'<div class="stat-box"><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>'


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals() -> Dict:
    """Load the latest signals from signals.json."""
    signals_file = TRADES_DIR / "signals.json"
    if signals_file.exists():
        return json.loads(signals_file.read_text())
    return {}


def load_portfolio() -> List[Dict]:
    """Load open positions from portfolio.csv."""
    from core.portfolio_manager import load_portfolio as _load
    return _load(status_filter="OPEN")


def load_themes() -> List[Dict]:
    """Load themes from the latest signals."""
    signals = load_signals()
    return signals.get('themes', [])


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_monday_market_analysis() -> str:
    """Monday: Market context + top performers."""
    signals = load_signals()
    positions = load_portfolio()
    themes = load_themes()

    today = datetime.now()
    week_start = today.strftime("%B %d, %Y")

    # Separate winners/losers
    winners = sorted(
        [p for p in positions if float(p.get('pnl_pct', 0)) > 0],
        key=lambda x: float(x.get('pnl_pct', 0)), reverse=True
    )

    # Build winners table
    winners_html = ""
    if winners:
        rows = ""
        for w in winners[:8]:
            ticker = w.get('ticker', '?')
            pnl = float(w.get('pnl_pct', 0))
            theme = w.get('theme', '')
            entry = float(w.get('entry_price', 0))
            current = float(w.get('current_price', entry))
            show_entry = pnl >= 25.0

            price_cell = f"${entry:.2f} &rarr; ${current:.2f}" if show_entry and entry > 0 else f"${current:.2f}"
            rows += f'<tr><td class="ticker">${ticker}</td><td>{price_cell}</td><td>{_pnl_span(pnl)}</td><td>{theme}</td></tr>\n'

        winners_html = f"""
<h2>🏆 Portfolio Highlights</h2>
<div class="card winner-card">
<table>
<tr><th>Ticker</th><th>Price</th><th>P&L</th><th>Theme</th></tr>
{rows}
</table>
</div>"""

    # Theme cards
    prime_themes = [t for t in themes if t.get('classification') == 'PRIME']
    investable_themes = [t for t in themes if t.get('classification') == 'INVESTABLE']

    themes_html = ""
    for t in (prime_themes + investable_themes)[:4]:
        name = t.get('name', 'Unknown')
        score = t.get('composite_score', 0)
        classification = t.get('classification', 'INVESTABLE')
        thesis = t.get('thesis_summary', '')[:200]
        badge = 'teal' if classification == 'PRIME' else 'amber'
        themes_html += f"""
<div class="card theme-card">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <strong>{name}</strong>
    <span class="signal-badge {badge}">{classification}</span>
  </div>
  <div style="color: {COLORS['teal']}; font-size: 24px; font-weight: 800; margin: 8px 0;">{score:.1f}<span style="font-size: 14px; color: {COLORS['text_muted']};">/10</span></div>
  {f'<p style="color: {COLORS["text_muted"]}; font-size: 14px;">{thesis}</p>' if thesis else ''}
</div>"""

    # Stats
    stats = signals.get('stats', {})
    stats_html = ""
    if stats:
        total_scanned = stats.get('tickers_loaded', 0)
        green_signals = stats.get('final_trade', 0)
        stats_html = f"""
<div class="stat-grid">
  {_stat_box(str(total_scanned), 'Tickers Scanned')}
  {_stat_box(str(green_signals), 'TEAL Signals')}
  {_stat_box(str(len(winners)), 'Open Winners')}
  {_stat_box(str(len(positions)), 'Positions')}
</div>"""

    body = f"""
<h1>Market Outlook: Week of {week_start}</h1>
{_signal_badge('TEAL')}
{stats_html}

<h2>Top Themes This Week</h2>
{themes_html if themes_html else '<p style="color: ' + COLORS['text_muted'] + ';">Theme analysis pending...</p>'}

{winners_html}

<hr class="divider">
<p style="text-align: center; color: {COLORS['text_muted']};">
  The proprietary 5-gate screening system filtered {stats.get('tickers_loaded', '1,800+')} stocks to identify high-conviction setups.
</p>
"""
    return _html_wrapper(f"Market Outlook: Week of {week_start}", body)


def generate_thursday_theme_spotlight() -> str:
    """Thursday: Hot theme deep dive."""
    themes = load_themes()
    signals = load_signals()

    prime_themes = [t for t in themes if t.get('classification') == 'PRIME']
    if not prime_themes:
        prime_themes = [t for t in themes if t.get('classification') == 'INVESTABLE']

    if not prime_themes:
        body = '<h1>Theme Watch</h1><p>No high-conviction themes identified this week.</p>'
        return _html_wrapper("Theme Watch", body)

    top = prime_themes[0]
    name = top.get('name', 'Unknown')
    score = top.get('composite_score', 0)
    thesis = top.get('thesis_summary', '')
    catalysts = top.get('key_catalysts', [])
    theme_type = top.get('theme_type', 'TREND')
    classification = top.get('classification', 'INVESTABLE')

    # Sub-scores
    cat_score = top.get('catalyst_score', 0)
    mom_score = top.get('momentum_score', 0)
    crowd_score = top.get('crowding_score', 0)
    runway_score = top.get('runway_score', 0)

    scores_html = ""
    if any([cat_score, mom_score, crowd_score, runway_score]):
        scores_html = f"""
<div class="stat-grid">
  {_stat_box(f'{cat_score:.1f}', 'Catalyst (40%)')}
  {_stat_box(f'{mom_score:.1f}', 'Momentum (25%)')}
  {_stat_box(f'{crowd_score:.1f}', 'Crowding (20%)')}
  {_stat_box(f'{runway_score:.1f}', 'Runway (15%)')}
</div>"""

    catalysts_html = ""
    if catalysts:
        items = "".join(f"<li>{c}</li>" for c in catalysts[:5])
        catalysts_html = f"<h2>Key Catalysts</h2><ul>{items}</ul>"

    # Get stocks in this theme
    buy_signals = signals.get('buy_signals', [])
    theme_stocks = [s for s in buy_signals if s.get('theme', '').lower() == name.lower()]

    stocks_html = ""
    if theme_stocks:
        rows = ""
        for s in theme_stocks[:5]:
            ticker = s.get('symbol', '?')
            conv = s.get('conviction', 3)
            conv_text = get_conviction_text(conv)
            price = s.get('price', 0)
            rows += f'<tr><td class="ticker">${ticker}</td><td>${price:.2f}</td><td>{conv_text}</td></tr>\n'

        stocks_html = f"""
<h2>🟢 TEAL Signals in This Theme</h2>
<div class="card theme-card">
<table>
<tr><th>Ticker</th><th>Price</th><th>Conviction</th></tr>
{rows}
</table>
</div>"""

    body = f"""
<h1>Theme Watch: {name}</h1>

<div class="highlight">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <span class="signal-badge teal">{classification}</span>
      <span style="margin-left: 8px; color: {COLORS['text_muted']};">{theme_type}</span>
    </div>
    <div style="font-size: 36px; font-weight: 800; color: {COLORS['teal']};">{score:.1f}<span style="font-size: 16px; color: {COLORS['text_muted']};">/10</span></div>
  </div>
  <p style="margin-top: 12px;">{thesis}</p>
</div>

{scores_html}
{catalysts_html}
{stocks_html}
"""
    return _html_wrapper(f"Theme Watch: {name}", body)


def generate_saturday_weekly_signals() -> str:
    """Saturday: Full TEAL/VIOLET/AMBER recap for the week."""
    signals = load_signals()
    positions = load_portfolio()

    today = datetime.now()
    date_str = today.strftime("%B %d, %Y")

    # Stats funnel
    stats = signals.get('stats', {})
    funnel_html = ""
    if stats:
        scanned = stats.get('tickers_loaded', 0)
        bos_up = stats.get('weekly_bos_up', stats.get('bos_bullish', 0))
        tech = stats.get('technical_signals', stats.get('meets_technical_gate', 0))
        theme_conf = stats.get('theme_confirmed', 0)
        final = stats.get('final_trade', 0)

        max_val = max(scanned, 1)
        funnel_html = f"""
<h2>Scan Funnel</h2>
<div class="card">
  <div class="funnel">
    <div class="funnel-row"><div class="funnel-bar" style="width: 100%; background: {COLORS['border']};">{scanned:,} Tickers Scanned</div></div>
    <div class="funnel-row"><div class="funnel-bar" style="width: {max(bos_up/max_val*100, 8):.0f}%; background: {COLORS['text_muted']};">{bos_up} Weekly Momentum Up</div></div>
    <div class="funnel-row"><div class="funnel-bar" style="width: {max(tech/max_val*100, 6):.0f}%; background: {COLORS['amber']};">{tech} Technical Gate</div></div>
    <div class="funnel-row"><div class="funnel-bar" style="width: {max(theme_conf/max_val*100, 5):.0f}%; background: {COLORS['violet']};">{theme_conf} Theme Confirmed</div></div>
    <div class="funnel-row"><div class="funnel-bar" style="width: {max(final/max_val*100, 4):.0f}%; background: {COLORS['teal']};">{final} TEAL Signals</div></div>
  </div>
</div>"""

    # TEAL signals (buy)
    buy_signals = signals.get('buy_signals', [])
    teal_html = ""
    if buy_signals:
        rows = ""
        for s in buy_signals:
            ticker = s.get('symbol', '?')
            theme = s.get('theme', '')
            conv = s.get('conviction', 3)
            conv_text = get_conviction_text(conv)
            price = s.get('price', 0)
            if conv_text is None:
                continue  # Skip conviction 1
            rows += f'<tr><td class="ticker">${ticker}</td><td>${price:.2f}</td><td>{theme}</td><td>{conv_text}</td></tr>\n'

        if rows:
            teal_html = f"""
<h2>{_signal_badge('TEAL')} TEAL Signals — Full Entry</h2>
<div class="card winner-card">
<table>
<tr><th>Ticker</th><th>Entry Price</th><th>Theme</th><th>Conviction</th></tr>
{rows}
</table>
</div>"""

    # AMBER watchlist
    caution_signals = signals.get('caution_signals', [])
    consider_signals = [s for s in buy_signals if s.get('final_decision') == 'CONSIDER']
    watchlist = caution_signals + consider_signals

    amber_html = ""
    if watchlist:
        items = ""
        for s in watchlist[:5]:
            ticker = s.get('symbol', '?')
            reason = s.get('reason', s.get('catalyst_summary', 'Under review'))[:100]
            items += f"<li><strong>${ticker}</strong> — {reason}</li>"
        amber_html = f"""
<h2>{_signal_badge('AMBER')} AMBER Watchlist</h2>
<div class="card" style="border-left: 4px solid {COLORS['amber']};">
  <p style="color: {COLORS['text_muted']}; font-size: 14px;">Cleared 4 of 5 gates — watching for TEAL</p>
  <ul>{items}</ul>
</div>"""

    # VIOLET exits — frame positively
    sell_signals = signals.get('sell_signals', [])
    violet_html = ""
    if sell_signals:
        rows = ""
        for s in sell_signals:
            ticker = s.get('symbol', '?')
            pnl = float(s.get('pnl_pct', 0))
            reason = s.get('reason', 'Systematic exit')
            rows += f'<tr><td class="ticker">${ticker}</td><td>{_pnl_span(pnl)}</td><td>{reason}</td></tr>\n'

        violet_html = f"""
<h2>{_signal_badge('VIOLET')} Exit Alerts — System Working as Designed</h2>
<div class="card exit-card">
<table>
<tr><th>Ticker</th><th>P&L</th><th>Reason</th></tr>
{rows}
</table>
<p style="color: {COLORS['text_muted']}; font-size: 13px; margin-top: 12px;">
  Capital Preservation Protocol activated — systematic exits protect capital so we live to fight another day.
</p>
</div>"""

    # Portfolio performance table (winners only or all open)
    portfolio_html = ""
    if positions:
        winners = sorted(
            [p for p in positions if float(p.get('pnl_pct', 0)) > 0],
            key=lambda x: float(x.get('pnl_pct', 0)), reverse=True
        )
        if winners:
            rows = ""
            for w in winners[:10]:
                ticker = w.get('ticker', '?')
                pnl = float(w.get('pnl_pct', 0))
                theme = w.get('theme', '')
                entry = float(w.get('entry_price', 0))
                current = float(w.get('current_price', entry))
                show_entry = pnl >= 25.0
                price_cell = f"${entry:.2f} &rarr; ${current:.2f}" if show_entry and entry > 0 else f"${current:.2f}"
                rows += f'<tr><td class="ticker">${ticker}</td><td>{price_cell}</td><td>{_pnl_span(pnl)}</td><td>{theme}</td></tr>\n'

            portfolio_html = f"""
<h2>🏆 Open Winners</h2>
<div class="card winner-card">
<table>
<tr><th>Ticker</th><th>Price</th><th>P&L</th><th>Theme</th></tr>
{rows}
</table>
</div>"""

    body = f"""
<h1>TEAL Signals: {date_str}</h1>
<p style="color: {COLORS['text_muted']};">Weekly Signal Recap — Proprietary 5-Gate Screening System</p>

{funnel_html}
{teal_html}
{amber_html}
{violet_html}
{portfolio_html}
"""
    return _html_wrapper(f"TEAL Signals: {date_str}", body)


def generate_sunday_deep_dive(ticker: Optional[str] = None) -> str:
    """Sunday: Single stock deep dive."""
    signals = load_signals()
    buy_signals = signals.get('buy_signals', [])

    if not buy_signals:
        body = '<h1>Deep Dive</h1><p>No TEAL signals available for deep dive.</p>'
        return _html_wrapper("Deep Dive", body)

    # Find target stock
    target = None
    if ticker:
        target = next((s for s in buy_signals if s.get('symbol', '').upper() == ticker.upper()), None)
    if not target:
        buy_signals.sort(key=lambda x: x.get('conviction', 0), reverse=True)
        target = buy_signals[0]

    tkr = target.get('symbol', 'UNKNOWN')
    theme = target.get('theme', 'Unknown')
    conv = target.get('conviction', 3)
    conv_text = get_conviction_text(conv)
    price = target.get('price', 0)
    beta = target.get('beta', 0)
    catalyst = target.get('catalyst_summary', '')
    bullish = target.get('bullish_factors', [])
    risks = target.get('risk_factors', [])
    reasoning = target.get('reasoning', '')

    # Overview table
    overview_html = f"""
<div class="highlight">
  <div style="text-align: center;">
    <div style="font-size: 42px; font-weight: 800; color: {COLORS['teal']};">${tkr}</div>
    <div style="margin: 8px 0;">{_signal_badge('TEAL')}</div>
  </div>
  <table style="margin-top: 16px;">
    <tr><td style="color: {COLORS['text_muted']};">Entry Price</td><td style="text-align: right; font-weight: 700;">${price:.2f}</td></tr>
    <tr><td style="color: {COLORS['text_muted']};">Theme</td><td style="text-align: right;">{theme}</td></tr>
    <tr><td style="color: {COLORS['text_muted']};">Conviction</td><td style="text-align: right; color: {COLORS['teal']};">{conv_text}</td></tr>
    <tr><td style="color: {COLORS['text_muted']};">Beta</td><td style="text-align: right;">{beta:.2f}</td></tr>
  </table>
</div>"""

    # Thesis
    thesis_text = reasoning[:500] if reasoning else 'Cleared all 5 gates with strong theme alignment.'
    thesis_html = f"""
<h2>Thesis</h2>
<div class="card">
  <p>{thesis_text}</p>
</div>"""

    # Catalyst
    catalyst_html = ""
    if catalyst:
        catalyst_html = f"""
<h2>Catalyst Summary</h2>
<div class="card" style="border-left: 4px solid {COLORS['gold']};">
  <p>{catalyst}</p>
</div>"""

    # Bullish factors
    bullish_html = ""
    if bullish:
        items = "".join(f"<li>{f}</li>" for f in bullish[:5])
        bullish_html = f"""
<h2 style="color: {COLORS['green_gain']};">✅ Bullish Factors</h2>
<div class="card winner-card">
  <ul>{items}</ul>
</div>"""

    # Risk factors
    risks_html = ""
    if risks:
        items = "".join(f"<li>{f}</li>" for f in risks[:5])
        risks_html = f"""
<h2 style="color: {COLORS['amber']};">⚠️ Risk Factors</h2>
<div class="card" style="border-left: 4px solid {COLORS['amber']};">
  <ul>{items}</ul>
</div>"""

    body = f"""
<h1>Deep Dive: ${tkr}</h1>

{overview_html}
{thesis_html}
{catalyst_html}
{bullish_html}
{risks_html}

<div class="card" style="text-align: center; background: {COLORS['teal_bg']}; border: 1px solid {COLORS['teal']};">
  <p style="font-size: 18px; font-weight: 700; color: {COLORS['teal']};">
    ${tkr} cleared all 5 gates of our systematic screening process.
  </p>
  <p style="color: {COLORS['text_muted']};">
    Theme alignment + technical momentum + catalyst timing = high-conviction TEAL signal.
  </p>
</div>
"""
    return _html_wrapper(f"Deep Dive: ${tkr}", body)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_content(content: str, filename: str) -> Tuple[Path, Optional[Path]]:
    """Save content to current/substack_posts/ and weekly archive.

    Args:
        content: The generated HTML content
        filename: Output filename (e.g., 'monday_market_analysis.html')

    Returns:
        Tuple of (current_path, archive_path or None)
    """
    # Validate content before saving (strip HTML tags for validation)
    import re
    text_only = re.sub(r'<[^>]+>', '', content)
    is_valid, violations = validate_content(text_only)
    if not is_valid:
        print(f"  ⚠️  WARNING: Content contains banned terms: {violations}")

    if OUTPUT_PATHS_AVAILABLE:
        current_dir, week_dir = ensure_output_structure()
        current_path = current_dir / "substack_posts" / filename
        archive_path = week_dir / "substack_posts" / filename

        current_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        current_path.write_text(content)
        archive_path.write_text(content)

        return current_path, archive_path
    else:
        # Fallback
        output_dir = TRADES_DIR / "current" / "substack_posts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(content)
        return output_path, None


def generate_all() -> List[Tuple[str, Path]]:
    """Generate all Substack content for the week."""
    results = []

    # Monday
    content = generate_monday_market_analysis()
    path, _ = save_content(content, "monday_market_analysis.html")
    results.append(("Monday Market Analysis", path))

    # Thursday
    content = generate_thursday_theme_spotlight()
    path, _ = save_content(content, "thursday_theme_spotlight.html")
    results.append(("Thursday Theme Spotlight", path))

    # Saturday
    content = generate_saturday_weekly_signals()
    path, _ = save_content(content, "saturday_weekly_signals.html")
    results.append(("Saturday Weekly Signals", path))

    # Sunday
    content = generate_sunday_deep_dive()
    path, _ = save_content(content, "sunday_deep_dive.html")
    results.append(("Sunday Deep Dive", path))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate Substack content for Sterling Signals (rich HTML)"
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

    if not any([args.monday, args.thursday, args.saturday, args.sunday, args.all]):
        parser.print_help()
        return

    print("=" * 60)
    print("  SUBSTACK CONTENT GENERATOR (Rich HTML)")
    print("=" * 60)

    if args.all:
        print("\nGenerating all Substack content...")
        results = generate_all()
        print("\n  Generated files:")
        for name, path in results:
            print(f"    📄 {name}: {path}")
        print("\n  📅 Content Calendar:")
        print("     Monday    → Market Analysis")
        print("     Thursday  → Theme Spotlight")
        print("     Saturday  → Weekly Signals (pairs with newsletter)")
        print("     Sunday    → Deep Dive")
        return

    generators = {
        'monday': ("Monday Market Analysis", generate_monday_market_analysis, "monday_market_analysis.html"),
        'thursday': ("Thursday Theme Spotlight", generate_thursday_theme_spotlight, "thursday_theme_spotlight.html"),
        'saturday': ("Saturday Weekly Signals", generate_saturday_weekly_signals, "saturday_weekly_signals.html"),
    }

    for day, (label, gen_func, filename) in generators.items():
        if getattr(args, day):
            print(f"\n  Generating {label}...")
            content = gen_func()
            if args.dry_run:
                print(content)
            else:
                path, archive = save_content(content, filename)
                print(f"    📄 Current: {path}")
                if archive:
                    print(f"    📦 Archive: {archive}")

    if args.sunday:
        label = f"Sunday Deep Dive{' for ' + args.ticker if args.ticker else ''}"
        print(f"\n  Generating {label}...")
        content = generate_sunday_deep_dive(args.ticker)
        if args.dry_run:
            print(content)
        else:
            filename = f"sunday_deep_dive{'_' + args.ticker if args.ticker else ''}.html"
            path, archive = save_content(content, filename)
            print(f"    📄 Current: {path}")
            if archive:
                print(f"    📦 Archive: {archive}")

    print("\n  ✅ Done!")


if __name__ == "__main__":
    main()
