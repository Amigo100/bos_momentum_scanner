#!/usr/bin/env python3
"""
Portfolio Snapshot Card — HTML data graphic generator.

Generates a self-contained HTML portfolio snapshot for Substack notes.
Cowork calls generate_portfolio_snapshot(data) → HTML string, then
capture_static.py converts to PNG.

Design spec: COWORK_INSTRUCTIONS.md §7c
Fonts: Outfit (body), DM Serif Display (title), JetBrains Mono (data)
Width: 680px, white background, editorial style

Usage:
  # CLI
  python3 -m substack.tools.templates.portfolio_snapshot \\
      --input portfolio.json --output graphic.html

  # Python API
  from substack.tools.templates.portfolio_snapshot import generate_portfolio_snapshot
  html = generate_portfolio_snapshot(data_dict)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN CONSTANTS (from COWORK_INSTRUCTIONS.md §7c)
# ═══════════════════════════════════════════════════════════════════════════════

GOOGLE_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=DM+Serif+Display&"
    "family=JetBrains+Mono:wght@400;700&"
    "family=Outfit:wght@400;500;600&"
    "display=swap');"
)

# P&L colors
COLOR_POSITIVE = "#2e5e3e"
COLOR_NEGATIVE = "#a04030"
COLOR_STAT_LABEL = "#8b8680"
COLOR_STAT_BG = "#f8f7f5"
COLOR_PORTFOLIO_BAR = "#3d5a80"
COLOR_BENCHMARK_BAR = "#d1d5db"
COLOR_WINNER_BORDER = "#16a34a"


# ═══════════════════════════════════════════════════════════════════════════════
# CSS TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

CSS = f"""
{GOOGLE_FONTS_IMPORT}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    background: #ffffff;
    font-family: 'Outfit', sans-serif;
    -webkit-font-smoothing: antialiased;
}}

.card {{
    width: 680px;
    background: #ffffff;
    border: 1px solid #e8e4df;
    border-radius: 12px;
    overflow: hidden;
}}

.header {{
    padding: 24px 28px 20px;
}}

.header-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #3d5a80;
    margin-bottom: 6px;
}}

.header-title {{
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    color: #1a1a1a;
    line-height: 1.3;
}}

/* ── Stats Row ── */

.stats-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding: 0 28px 20px;
}}

.stat-card {{
    background: {COLOR_STAT_BG};
    border-radius: 8px;
    padding: 14px 16px;
    text-align: center;
}}

.stat-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 700;
    line-height: 1.2;
}}

.stat-value.positive {{
    color: #1a1a1a;
}}

.stat-value.negative {{
    color: {COLOR_NEGATIVE};
}}

.stat-label {{
    font-family: 'Outfit', sans-serif;
    font-size: 11px;
    color: {COLOR_STAT_LABEL};
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── Benchmark Bars ── */

.benchmarks {{
    padding: 0 28px 20px;
}}

.benchmarks-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {COLOR_STAT_LABEL};
    margin-bottom: 12px;
}}

.bench-row {{
    display: grid;
    grid-template-columns: 70px 1fr 60px;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}}

.bench-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #4a4540;
}}

.bench-bar-track {{
    height: 22px;
    background: #f0ece7;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}}

.bench-bar-fill {{
    height: 100%;
    border-radius: 4px;
    min-width: 2px;
}}

.bench-bar-fill.portfolio {{
    background: {COLOR_PORTFOLIO_BAR};
}}

.bench-bar-fill.benchmark {{
    background: {COLOR_BENCHMARK_BAR};
}}

.bench-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    text-align: right;
}}

.bench-value.positive {{
    color: {COLOR_POSITIVE};
}}

.bench-value.negative {{
    color: {COLOR_NEGATIVE};
}}

.alpha-badge {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
}}

.alpha-badge.positive {{
    background: #f0fdf4;
    color: {COLOR_POSITIVE};
    border: 1px solid #bbf7d0;
}}

.alpha-badge.negative {{
    background: #fef2f2;
    color: {COLOR_NEGATIVE};
    border: 1px solid #fecaca;
}}

/* ── Positions Table ── */

.positions {{
    padding: 0 28px;
}}

.positions table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

.positions thead th {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: {COLOR_STAT_LABEL};
    background: {COLOR_STAT_BG};
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid #e8e4df;
}}

.positions thead th:nth-child(n+3) {{
    text-align: right;
}}

.positions tbody tr {{
    border-bottom: 1px solid #f0ece7;
}}

.positions tbody tr:nth-child(even) {{
    background: #fafaf8;
}}

.positions tbody tr.winner {{
    border-left: 3px solid {COLOR_WINNER_BORDER};
}}

.positions tbody td {{
    padding: 10px 10px;
    vertical-align: middle;
}}

.positions tbody td:nth-child(n+3) {{
    text-align: right;
}}

.pos-ticker {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
}}

.pos-theme {{
    font-family: 'Outfit', sans-serif;
    font-size: 11px;
    color: {COLOR_STAT_LABEL};
    margin-top: 2px;
}}

.pos-price {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #4a4540;
}}

.pos-pnl {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 700;
}}

.pos-pnl.positive {{
    color: {COLOR_POSITIVE};
}}

.pos-pnl.negative {{
    color: {COLOR_NEGATIVE};
}}

/* ── Footer ── */

.footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 28px;
    margin-top: 4px;
    border-top: 1px solid #f0ece7;
}}

.footer-sources {{
    font-family: 'Outfit', sans-serif;
    font-size: 11px;
    color: #a09890;
    max-width: 480px;
}}

.footer-brand {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #3d5a80;
}}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HTML GENERATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pnl_class(value: float) -> str:
    """Return CSS class for positive/negative values."""
    return "positive" if value >= 0 else "negative"


def _pnl_text(value: float) -> str:
    """Format P&L percentage with sign."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def _render_stat_card(value: str, label: str, css_class: str = "positive") -> str:
    """Render a single summary stat card."""
    return f"""
            <div class="stat-card">
                <div class="stat-value {css_class}">{value}</div>
                <div class="stat-label">{label}</div>
            </div>"""


def _render_benchmark_bar(
    label: str, value: float, max_val: float, is_portfolio: bool = False
) -> str:
    """Render a single horizontal benchmark bar."""
    width_pct = abs(value) / max_val * 100 if max_val > 0 else 0
    width_pct = min(width_pct, 100)
    bar_class = "portfolio" if is_portfolio else "benchmark"
    val_class = _pnl_class(value)

    return f"""
            <div class="bench-row">
                <div class="bench-label">{label}</div>
                <div class="bench-bar-track">
                    <div class="bench-bar-fill {bar_class}" style="width: {width_pct:.1f}%"></div>
                </div>
                <div class="bench-value {val_class}">{_pnl_text(value)}</div>
            </div>"""


def _render_position_row(pos: Dict) -> str:
    """Render a single position table row."""
    ticker = pos.get("ticker", "")
    theme = pos.get("theme", "")
    entry_price = pos.get("entry_price", 0)
    current_price = pos.get("current_price", 0)
    pnl_pct = pos.get("pnl_pct", 0)

    row_class = "winner" if pnl_pct > 0 else ""
    pnl_css = _pnl_class(pnl_pct)

    return f"""
                <tr class="{row_class}">
                    <td>
                        <div class="pos-ticker">{ticker}</div>
                        <div class="pos-theme">{theme}</div>
                    </td>
                    <td><span class="pos-price">${entry_price:.2f}</span></td>
                    <td><span class="pos-price">${current_price:.2f}</span></td>
                    <td><span class="pos-pnl {pnl_css}">{_pnl_text(pnl_pct)}</span></td>
                </tr>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_portfolio_snapshot(data: Dict) -> str:
    """Generate a self-contained HTML portfolio snapshot graphic.

    Args:
        data: Dict with keys:
            date: str ("March 10, 2026")
            positions: List[dict], each with:
                ticker: str
                theme: str
                entry_price: float
                current_price: float
                pnl_pct: float
                holding_days: int
            benchmarks: dict with spy_ytd: float, qqq_ytd: float
            portfolio_return: float
            sources: str (optional)

    Returns:
        Complete HTML string with Google Fonts + <style> block.
    """
    date = data.get("date", "")
    positions = data.get("positions", [])
    benchmarks = data.get("benchmarks", {})
    portfolio_return = data.get("portfolio_return", 0.0)
    sources = data.get("sources", f"Portfolio as of {date}")

    spy_ytd = benchmarks.get("spy_ytd", 0.0)
    qqq_ytd = benchmarks.get("qqq_ytd", 0.0)

    # ── Compute summary stats ──
    positions_count = len(positions)
    winners = [p for p in positions if p.get("pnl_pct", 0) > 0]
    win_rate = (len(winners) / positions_count * 100) if positions_count else 0
    holding_days_list = [p.get("holding_days", 0) for p in positions]
    avg_holding = (
        round(sum(holding_days_list) / len(holding_days_list))
        if holding_days_list
        else 0
    )
    alpha = portfolio_return - spy_ytd

    # ── Stats row ──
    stats_html = "".join([
        _render_stat_card(
            _pnl_text(portfolio_return), "Total Return",
            _pnl_class(portfolio_return),
        ),
        _render_stat_card(str(positions_count), "Positions"),
        _render_stat_card(f"{avg_holding}d", "Avg Hold"),
        _render_stat_card(f"{win_rate:.0f}%", "Win Rate"),
    ])

    # ── Benchmark bars ──
    max_val = max(abs(portfolio_return), abs(spy_ytd), abs(qqq_ytd), 1)
    alpha_class = _pnl_class(alpha)
    alpha_text = _pnl_text(alpha)

    benchmarks_html = (
        _render_benchmark_bar("Portfolio", portfolio_return, max_val, is_portfolio=True)
        + _render_benchmark_bar("SPY YTD", spy_ytd, max_val)
        + _render_benchmark_bar("QQQ YTD", qqq_ytd, max_val)
    )

    # ── Positions table ──
    position_rows = "".join(_render_position_row(p) for p in positions)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
{CSS}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="header-label">Portfolio Snapshot</div>
            <div class="header-title">{date}</div>
        </div>

        <div class="stats-row">
{stats_html}
        </div>

        <div class="benchmarks">
            <div class="benchmarks-title">
                vs Benchmarks
                <span class="alpha-badge {alpha_class}">Alpha {alpha_text}</span>
            </div>
{benchmarks_html}
        </div>

        <div class="positions">
            <table>
                <thead>
                    <tr>
                        <th>Position</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P&amp;L</th>
                    </tr>
                </thead>
                <tbody>
{position_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <div class="footer-sources">{sources}</div>
            <div class="footer-brand">STERLING SIGNALS</div>
        </div>
    </div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate a portfolio snapshot HTML graphic"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to JSON file with portfolio data"
    )
    parser.add_argument(
        "--output", default="portfolio_snapshot.html",
        help="Output HTML file path (default: portfolio_snapshot.html)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r") as f:
        data = json.load(f)

    html = generate_portfolio_snapshot(data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"  \u2713 Generated: {output_path} ({len(data.get('positions', []))} positions)")


if __name__ == "__main__":
    main()
