#!/usr/bin/env python3
"""
PORTFOLIO VISUAL DASHBOARD — HTML + PNG
========================================

Generates a dark-themed, self-contained HTML portfolio dashboard
and optional PNG screenshots for sharing on X/Twitter and Substack.

Features:
    - 6-box stat grid (NAV, Return, Win Rate, Alpha vs SPY, Alpha vs NASDAQ, Max DD)
    - Inline SVG equity curve chart (Portfolio vs SPY vs NASDAQ)
    - Enhanced positions table (Ticker, Theme, Entry, Current, Held, P&L, Stop Dist)
    - Recent exits table
    - All self-contained (inline CSS, no external deps)

Outputs:
    - trades/current/portfolio_visual.html  (+ weekly archive)
    - trades/charts/portfolio_dashboard.png          (1400x900, X/Twitter)
    - trades/charts/portfolio_dashboard_substack.png  (1000x700, Substack)

Usage:
    python -m content.portfolio_visual              # Full: HTML + PNG
    python -m content.portfolio_visual --html-only   # HTML only
    python -m content.portfolio_visual --dry-run      # Preview to stdout
"""

import argparse
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

# Base paths
from config.output_paths import (
    CHARTS_DIR,
    save_to_substack_current_and_archive,
    ensure_output_structure,
)

# Settings
from config.settings import (
    CURRENCY_SYMBOL,
    STARTING_CAPITAL_PER_POSITION,
    get_conviction_text,
)

# Marketing validation
from config.marketing_vocabulary import validate_content

# Portfolio data
from portfolio.manager import PortfolioManager, EquitySnapshot

# Playwright (optional — graceful fallback)
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# Color system (matches substack_content_generator.py)
COLORS = {
    "teal": "#2DD4BF",
    "teal_bg": "#0D3B34",
    "violet": "#A78BFA",
    "green_gain": "#22C55E",
    "red_loss": "#EF4444",
    "dark_bg": "#111827",
    "card_bg": "#1F2937",
    "border": "#374151",
    "text": "#F9FAFB",
    "text_muted": "#9CA3AF",
    "gold": "#F59E0B",
    "header_bg": "#0F172A",
}

# Screenshot dimensions (matching chart_capture.py conventions)
DASHBOARD_SIZE_X = (1400, 900)
DASHBOARD_SIZE_SUBSTACK = (1000, 700)

# Output filenames
DASHBOARD_HTML_FILENAME = "portfolio_visual.html"
DASHBOARD_PNG_FILENAME = "portfolio_dashboard.png"
DASHBOARD_PNG_SUBSTACK_FILENAME = "portfolio_dashboard_substack.png"

# Marketing
RECENT_EXIT_DAYS = 30  # Show exits from last N days

# Marketing-safe exit reason mapping
EXIT_REASON_MAP = {
    "STOPPED": "Systematic exit",
    "CLOSED": "Position closed",
    "TRAILING STOP": "Capital preservation triggered",
    "BEARISH PIVOT": "Structural exit",
    "Weekly BoS Down": "Structural exit",  # Legacy (pre-Sterling Grid)
    "Daily BoS Down": "Structural exit",   # Legacy (pre-Sterling Grid)
    "ExD exit": "Structural exit",
    "Profit lock": "Capital preservation triggered",
    "EXD EXIT": "Structural exit",
    "PROFIT LOCK": "Capital preservation triggered",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════


def _load_dashboard_data() -> Dict:
    """Load all data needed for the portfolio dashboard.

    Returns:
        Dict with keys:
            open_positions: List[Trade] sorted by pnl_pct descending
            recent_exits: List[Trade] from last 30 days
            compounding: Dict from get_compounding_summary()
            performance: Dict from get_performance_summary()
            equity_snapshots: List[EquitySnapshot] from equity curve
            max_drawdown: float from get_max_drawdown()
            date_str: Formatted date string
            total_open: int
    """
    pm = PortfolioManager()
    pm.update_prices()

    # Open positions sorted by P&L descending
    open_positions = sorted(
        pm.get_open_positions(),
        key=lambda t: t.pnl_pct,
        reverse=True,
    )

    # Recent exits (last 30 days)
    cutoff = (datetime.now() - timedelta(days=RECENT_EXIT_DAYS)).strftime("%Y-%m-%d")
    recent_exits = [
        t
        for t in pm.get_closed_trades()
        if t.exit_date and t.exit_date >= cutoff
    ]
    recent_exits.sort(key=lambda t: t.exit_date, reverse=True)

    # Compounding summary
    compounding = {}
    try:
        compounding = pm.get_compounding_summary()
    except Exception as e:
        logger.warning("Could not load compounding summary: %s", e)

    # Performance summary
    performance = {}
    try:
        performance = pm.get_performance_summary()
    except Exception as e:
        logger.warning("Could not load performance summary: %s", e)

    # Equity curve snapshots
    equity_snapshots = []
    max_drawdown = 0.0
    try:
        equity_snapshots = pm.equity_tracker.snapshots
        max_drawdown = pm.equity_tracker.get_max_drawdown()
    except Exception as e:
        logger.warning("Could not load equity snapshots: %s", e)

    return {
        "open_positions": open_positions,
        "recent_exits": recent_exits,
        "compounding": compounding,
        "performance": performance,
        "equity_snapshots": equity_snapshots,
        "max_drawdown": max_drawdown,
        "date_str": datetime.now().strftime("%B %d, %Y"),
        "total_open": len(open_positions),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HTML HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _pnl_color(pnl: float) -> str:
    """Return hex color for P&L value."""
    return COLORS["green_gain"] if pnl >= 0 else COLORS["red_loss"]


def _pnl_text(pnl: float) -> str:
    """Format P&L as +X.X% or -X.X%."""
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.1f}%"


def _stat_box(value: str, label: str, color: str = "") -> str:
    """Create a summary stat box."""
    value_style = f"color:{color};" if color else f"color:{COLORS['text']};"
    return f"""<div style="background:{COLORS['card_bg']};border:1px solid {COLORS['border']};border-radius:8px;padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:700;{value_style}">{value}</div>
      <div style="font-size:12px;color:{COLORS['text_muted']};margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
    </div>"""


def _safe_exit_reason(trade) -> str:
    """Map exit reason to marketing-safe language."""
    # Check status first
    if trade.status == "STOPPED":
        return EXIT_REASON_MAP.get("STOPPED", "Systematic exit")
    if trade.status == "CLOSED":
        return EXIT_REASON_MAP.get("CLOSED", "Position closed")

    # Check notes for specific reasons
    notes = (trade.notes or "").strip()
    for key, safe_label in EXIT_REASON_MAP.items():
        if key.lower() in notes.lower():
            return safe_label

    return "Position closed"


# ═══════════════════════════════════════════════════════════════════════════════
# EQUITY CURVE SVG CHART
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_equity_curve_svg(
    snapshots: List[EquitySnapshot],
    width: int = 860,
    height: int = 280,
) -> str:
    """Generate an inline SVG equity curve chart.

    Plots three lines: Portfolio (teal), SPY (muted), QQQ (violet).
    All self-contained — no JavaScript or external dependencies.

    Args:
        snapshots: List of EquitySnapshot objects (sorted by date).
        width: SVG viewport width in pixels.
        height: SVG viewport height in pixels.

    Returns:
        SVG HTML string ready for embedding.
    """
    if len(snapshots) < 2:
        return f"""<div style="background:{COLORS['card_bg']};border:1px solid {COLORS['border']};border-radius:8px;padding:40px;text-align:center;color:{COLORS['text_muted']};">
          <p style="margin:0;font-size:14px;">Equity curve requires at least 2 data points.</p>
          <p style="margin:8px 0 0 0;font-size:12px;">Run the scanner a few times to build history.</p>
        </div>"""

    # Margins for axes labels
    margin_left = 60
    margin_right = 20
    margin_top = 30
    margin_bottom = 40
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # Extract data series
    dates = [s.date for s in snapshots]
    portfolio_returns = [s.total_return_pct for s in snapshots]
    spy_returns = [s.spy_return_pct for s in snapshots]
    qqq_returns = [s.qqq_return_pct for s in snapshots]

    # Combine all values for Y-axis scaling
    all_vals = portfolio_returns + spy_returns + qqq_returns
    y_min = min(all_vals)
    y_max = max(all_vals)

    # Add 10% padding
    y_range = y_max - y_min if y_max != y_min else 10.0
    y_min -= y_range * 0.1
    y_max += y_range * 0.1
    y_range = y_max - y_min

    n = len(snapshots)

    def x_pos(i):
        return margin_left + (i / (n - 1)) * plot_w if n > 1 else margin_left + plot_w / 2

    def y_pos(val):
        return margin_top + (1 - (val - y_min) / y_range) * plot_h if y_range > 0 else margin_top + plot_h / 2

    def polyline_points(values):
        pts = []
        for i, v in enumerate(values):
            pts.append(f"{x_pos(i):.1f},{y_pos(v):.1f}")
        return " ".join(pts)

    # Build SVG elements
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;margin:0 auto;">'
    ]

    # Background
    svg_parts.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{COLORS["card_bg"]}" rx="8"/>'
    )

    # Grid lines (horizontal)
    num_gridlines = 5
    for i in range(num_gridlines + 1):
        gy = margin_top + (i / num_gridlines) * plot_h
        gval = y_max - (i / num_gridlines) * y_range
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{gy:.1f}" x2="{width - margin_right}" y2="{gy:.1f}" '
            f'stroke="{COLORS["border"]}" stroke-width="0.5" stroke-dasharray="4,4"/>'
        )
        svg_parts.append(
            f'<text x="{margin_left - 8}" y="{gy + 4:.1f}" text-anchor="end" '
            f'fill="{COLORS["text_muted"]}" font-size="10" font-family="sans-serif">{gval:+.1f}%</text>'
        )

    # Zero line
    if y_min < 0 < y_max:
        zero_y = y_pos(0)
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{zero_y:.1f}" x2="{width - margin_right}" y2="{zero_y:.1f}" '
            f'stroke="{COLORS["text_muted"]}" stroke-width="0.5" opacity="0.5"/>'
        )

    # X-axis date labels (show first, last, and a few middle ones)
    label_indices = [0, n - 1]
    if n > 4:
        label_indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    for idx in label_indices:
        if idx < n:
            lx = x_pos(idx)
            date_label = dates[idx][5:]  # MM-DD format
            svg_parts.append(
                f'<text x="{lx:.1f}" y="{height - 8}" text-anchor="middle" '
                f'fill="{COLORS["text_muted"]}" font-size="10" font-family="sans-serif">{date_label}</text>'
            )

    # Data lines
    line_configs = [
        (spy_returns, COLORS["text_muted"], "1.5", "S&P 500"),
        (qqq_returns, COLORS["violet"], "1.5", "NASDAQ"),
        (portfolio_returns, COLORS["teal"], "2.5", "Portfolio"),
    ]

    for values, color, stroke_w, _label in line_configs:
        points = polyline_points(values)
        svg_parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_w}" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    # Latest value dots
    for values, color, _sw, _label in line_configs:
        last_x = x_pos(n - 1)
        last_y = y_pos(values[-1])
        svg_parts.append(
            f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="{color}"/>'
        )

    # Legend
    legend_x = margin_left + 10
    legend_y = margin_top + 8
    legend_items = [
        (COLORS["teal"], "Portfolio"),
        (COLORS["text_muted"], "S&P 500"),
        (COLORS["violet"], "NASDAQ"),
    ]
    for i, (color, label) in enumerate(legend_items):
        lx = legend_x + i * 100
        svg_parts.append(
            f'<line x1="{lx}" y1="{legend_y}" x2="{lx + 20}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<text x="{lx + 25}" y="{legend_y + 4}" fill="{COLORS["text"]}" '
            f'font-size="11" font-family="sans-serif">{label}</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# HTML GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


def generate_dashboard_html(data: Dict) -> str:
    """Generate the complete self-contained HTML portfolio dashboard.

    Args:
        data: Dict from _load_dashboard_data()

    Returns:
        Complete HTML string with inline CSS.
    """
    open_positions = data["open_positions"]
    recent_exits = data["recent_exits"]
    compounding = data.get("compounding", {})
    performance = data.get("performance", {})
    equity_snapshots = data.get("equity_snapshots", [])
    max_drawdown = data.get("max_drawdown", 0.0)
    date_str = data["date_str"]
    total_open = data["total_open"]

    # ── Extract summary values ─────────────────────────────────────────────
    currency = compounding.get("currency", CURRENCY_SYMBOL)
    nav = compounding.get("current_nav", 0)
    total_return = compounding.get("total_return_pct", 0)
    alpha_spy = compounding.get("alpha_pct", 0)
    alpha_qqq = compounding.get("alpha_vs_qqq_pct", 0)
    win_rate = performance.get("win_rate", 0)
    inception = compounding.get("inception_date", "")

    # ── Summary stat boxes (3+3 grid) ────────────────────────────────────
    nav_str = f"{currency}{nav:,.0f}" if nav else "—"
    return_str = _pnl_text(total_return) if nav else "—"
    win_rate_str = f"{win_rate:.0f}%" if performance and win_rate > 0 else "N/A"
    alpha_spy_str = f"+{alpha_spy:.1f}%" if alpha_spy >= 0 else f"{alpha_spy:.1f}%"
    alpha_qqq_str = f"+{alpha_qqq:.1f}%" if alpha_qqq >= 0 else f"{alpha_qqq:.1f}%"
    dd_str = f"{max_drawdown:.1f}%" if max_drawdown < 0 else "0.0%"

    stats_html = f"""<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0;">
      {_stat_box(nav_str, "Portfolio NAV")}
      {_stat_box(return_str, "Total Return", _pnl_color(total_return))}
      {_stat_box(win_rate_str, "Win Rate")}
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 20px 0;">
      {_stat_box(alpha_spy_str, "Alpha vs S&P 500", _pnl_color(alpha_spy))}
      {_stat_box(alpha_qqq_str, "Alpha vs NASDAQ", _pnl_color(alpha_qqq))}
      {_stat_box(dd_str, "Max Drawdown", COLORS["red_loss"] if max_drawdown < 0 else COLORS["text_muted"])}
    </div>"""

    # ── Equity curve chart ────────────────────────────────────────────────
    equity_chart_html = ""
    if equity_snapshots and len(equity_snapshots) >= 2:
        svg = _generate_equity_curve_svg(equity_snapshots)
        equity_chart_html = f"""
    <div style="margin:0 0 24px 0;">
      <h2 style="color:{COLORS['teal']};font-size:18px;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid {COLORS['border']};">
        Equity Curve
      </h2>
      {svg}
    </div>"""
    elif equity_snapshots and len(equity_snapshots) < 2:
        equity_chart_html = f"""
    <div style="margin:0 0 24px 0;">
      <h2 style="color:{COLORS['teal']};font-size:18px;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid {COLORS['border']};">
        Equity Curve
      </h2>
      {_generate_equity_curve_svg(equity_snapshots)}
    </div>"""

    # ── Open positions table (enhanced) ──────────────────────────────────
    th_style = f"padding:8px 12px;text-align:left;color:{COLORS['text_muted']};font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;"
    th_style_center = f"padding:8px 12px;text-align:center;color:{COLORS['text_muted']};font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;"
    th_style_right = f"padding:8px 12px;text-align:right;color:{COLORS['text_muted']};font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;"

    position_rows = ""
    for i, t in enumerate(open_positions):
        bg = COLORS["card_bg"] if i % 2 == 0 else COLORS["dark_bg"]

        # Entry price — always show
        entry_str = f"${t.entry_price:.2f}" if t.entry_price > 0 else "—"

        # Current price
        current_str = f"${t.current_price:.2f}" if t.current_price > 0 else "—"

        # P&L
        pnl_html = f'<span style="color:{_pnl_color(t.pnl_pct)};font-weight:700;">{_pnl_text(t.pnl_pct)}</span>'

        # Theme (truncate if long)
        theme_str = (t.theme[:18] + "..") if len(t.theme) > 20 else t.theme

        # Stop distance
        stop_dist = getattr(t, 'distance_to_stop_pct', 0.0) or 0.0
        if stop_dist > 0:
            stop_color = COLORS["green_gain"] if stop_dist > 15 else (COLORS["gold"] if stop_dist > 10 else COLORS["red_loss"])
            stop_str = f'<span style="color:{stop_color};">{stop_dist:.0f}%</span>'
        else:
            stop_str = f'<span style="color:{COLORS["text_muted"]};">—</span>'

        position_rows += f"""<tr style="background:{bg};">
          <td style="padding:10px 12px;font-weight:700;color:{COLORS['teal']};">${t.ticker}</td>
          <td style="padding:10px 12px;color:{COLORS['text_muted']};">{theme_str}</td>
          <td style="padding:10px 12px;">{entry_str}</td>
          <td style="padding:10px 12px;">{current_str}</td>
          <td style="padding:10px 12px;text-align:center;">{t.days_held}d</td>
          <td style="padding:10px 12px;text-align:right;">{pnl_html}</td>
          <td style="padding:10px 12px;text-align:center;">{stop_str}</td>
        </tr>"""

    positions_section = ""
    if open_positions:
        positions_section = f"""
    <div style="margin:24px 0;">
      <h2 style="color:{COLORS['teal']};font-size:18px;margin:0 0 12px 0;padding-bottom:8px;border-bottom:1px solid {COLORS['border']};">
        Open Positions ({total_open})
      </h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="border-bottom:2px solid {COLORS['border']};">
            <th style="{th_style}">Ticker</th>
            <th style="{th_style}">Theme</th>
            <th style="{th_style}">Entry</th>
            <th style="{th_style}">Current</th>
            <th style="{th_style_center}">Held</th>
            <th style="{th_style_right}">P&L</th>
            <th style="{th_style_center}">Stop Dist</th>
          </tr>
        </thead>
        <tbody>
          {position_rows}
        </tbody>
      </table>
    </div>"""
    else:
        positions_section = f"""
    <div style="margin:24px 0;padding:32px;text-align:center;color:{COLORS['text_muted']};background:{COLORS['card_bg']};border-radius:8px;">
      <p style="font-size:16px;">No open positions. Patience is edge.</p>
    </div>"""

    # ── Recent exits section ───────────────────────────────────────────────
    exits_section = ""
    if recent_exits:
        exit_rows = ""
        for i, t in enumerate(recent_exits):
            bg = COLORS["card_bg"] if i % 2 == 0 else COLORS["dark_bg"]
            reason = _safe_exit_reason(t)
            pnl_html = f'<span style="color:{_pnl_color(t.pnl_pct)};font-weight:700;">{_pnl_text(t.pnl_pct)}</span>'

            exit_rows += f"""<tr style="background:{bg};">
              <td style="padding:10px 12px;font-weight:700;color:{COLORS['violet']};">${t.ticker}</td>
              <td style="padding:10px 12px;color:{COLORS['text_muted']};">{t.exit_date}</td>
              <td style="padding:10px 12px;text-align:right;">{pnl_html}</td>
              <td style="padding:10px 12px;color:{COLORS['text_muted']};">{reason}</td>
            </tr>"""

        exits_section = f"""
    <div style="margin:24px 0;">
      <h2 style="color:{COLORS['violet']};font-size:18px;margin:0 0 4px 0;padding-bottom:8px;border-bottom:1px solid {COLORS['border']};">
        Recent Exits
      </h2>
      <p style="color:{COLORS['text_muted']};font-size:12px;margin:0 0 12px 0;">Stops hit = system working as designed</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="border-bottom:2px solid {COLORS['border']};">
            <th style="{th_style}">Ticker</th>
            <th style="{th_style}">Exit Date</th>
            <th style="{th_style_right}">P&L</th>
            <th style="{th_style}">Reason</th>
          </tr>
        </thead>
        <tbody>
          {exit_rows}
        </tbody>
      </table>
    </div>"""

    # ── Inception line ─────────────────────────────────────────────────────
    inception_html = ""
    if inception:
        inception_html = f'<span style="color:{COLORS["text_muted"]};font-size:13px;"> | Since {inception}</span>'

    # ── Timestamp ──────────────────────────────────────────────────────────
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Full HTML ──────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sterling Signals Portfolio</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;margin:0;padding:24px;background:{COLORS['dark_bg']};color:{COLORS['text']};">
  <div style="max-width:900px;margin:0 auto;">

    <!-- HEADER -->
    <div style="text-align:center;padding:28px 0 20px 0;border-bottom:2px solid {COLORS['teal']};">
      <h1 style="margin:0;font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.5px;">
        <span style="color:{COLORS['teal']};">Sterling Signals</span> Portfolio
      </h1>
      <p style="margin:8px 0 0 0;color:{COLORS['text_muted']};font-size:14px;">
        {date_str} | {total_open} Open Position{"s" if total_open != 1 else ""}{inception_html}
      </p>
      <p style="margin:4px 0 0 0;color:{COLORS['border']};font-size:11px;">
        Generated: {generated_at} ET | Refresh: python -m content.portfolio_visual
      </p>
    </div>

    <!-- SUMMARY STATS -->
    {stats_html}

    <!-- EQUITY CURVE -->
    {equity_chart_html}

    <!-- OPEN POSITIONS -->
    {positions_section}

    <!-- RECENT EXITS -->
    {exits_section}

    <!-- FOOTER -->
    <div style="text-align:center;padding:20px 0 8px 0;margin-top:24px;border-top:1px solid {COLORS['border']};">
      <p style="margin:0;color:{COLORS['text_muted']};font-size:13px;">
        sterlingsignals.substack.com
      </p>
      <p style="margin:4px 0 0 0;color:{COLORS['border']};font-size:11px;">
        Proprietary 5-gate screening system | No ego, just execution
      </p>
    </div>

  </div>
</body>
</html>"""

    return html


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


def _validate_dashboard(html: str) -> bool:
    """Validate generated HTML for banned terms.

    Strips HTML tags and runs through marketing vocabulary validator.

    Returns:
        True if clean, False if violations found (logged as warnings).
    """
    # Strip HTML tags for text-only validation
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    is_valid, violations = validate_content(text)
    if not is_valid:
        for v in violations:
            logger.warning("Dashboard banned term violation: %s", v)
        print(f"  WARNING: {len(violations)} banned term(s) found in dashboard")
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════


def save_dashboard(html: str) -> Tuple[Path, Optional[Path]]:
    """Save HTML to trades/current/ and weekly archive.

    Uses output_paths.save_to_current_and_archive() for dual-write.

    Returns:
        Tuple of (current_path, archive_path)
    """
    ensure_output_structure()
    current_path, archive_path = save_to_substack_current_and_archive(
        html, DASHBOARD_HTML_FILENAME
    )
    print(f"  HTML saved: {current_path}")
    print(f"  Archived:   {archive_path}")
    return current_path, archive_path


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT
# ═══════════════════════════════════════════════════════════════════════════════


def capture_dashboard_screenshot(
    html_path: Path,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """Capture PNG screenshots of the HTML dashboard via Playwright.

    Opens a local file:// URL (no login needed). Generates two sizes:
      - 1400x900 for X/Twitter
      - 1000x700 for Substack

    Args:
        html_path: Path to the saved HTML file.
        output_dir: Output directory (default: trades/charts/).

    Returns:
        List of saved PNG paths. Empty list if Playwright unavailable.
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("  Playwright not installed — skipping PNG screenshot")
        print("  Install with: pip install playwright && playwright install chromium")
        return []

    if output_dir is None:
        output_dir = CHARTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    file_url = f"file://{html_path.resolve()}"
    saved: List[Path] = []

    sizes = [
        (DASHBOARD_SIZE_X, DASHBOARD_PNG_FILENAME),
        (DASHBOARD_SIZE_SUBSTACK, DASHBOARD_PNG_SUBSTACK_FILENAME),
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for (width, height), filename in sizes:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(file_url, wait_until="networkidle")
                page.wait_for_timeout(500)  # Let fonts render

                out_path = output_dir / filename
                page.screenshot(path=str(out_path), full_page=False)
                saved.append(out_path)
                print(f"  PNG saved: {out_path} ({width}x{height})")
                page.close()

            browser.close()

    except Exception as e:
        logger.error("Screenshot capture failed: %s", e)
        print(f"  Screenshot error: {e}")

    return saved


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    """Generate visual portfolio dashboard (HTML + optional PNG)."""
    parser = argparse.ArgumentParser(
        description="Generate visual portfolio dashboard (HTML + PNG)"
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Generate HTML only, skip PNG screenshot",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print HTML to stdout without saving",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output directory for PNG",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print()
    print("=" * 60)
    print("  PORTFOLIO VISUAL DASHBOARD")
    print("=" * 60)

    # ── Load data ──────────────────────────────────────────────────────────
    print("\n  Loading portfolio data...")
    try:
        data = _load_dashboard_data()
    except Exception as e:
        print(f"\n  ERROR: Failed to load portfolio data: {e}")
        logger.error("Failed to load portfolio data: %s", e)
        return 1

    print(f"  {data['total_open']} open positions, {len(data['recent_exits'])} recent exits")
    print(f"  {len(data.get('equity_snapshots', []))} equity curve snapshots")

    # ── Generate HTML ──────────────────────────────────────────────────────
    print("\n  Generating HTML dashboard...")
    html = generate_dashboard_html(data)

    # ── Validate ───────────────────────────────────────────────────────────
    _validate_dashboard(html)

    # ── Output ─────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n  ── DRY RUN: HTML output ──\n")
        print(html)
        return 0

    current_path, _ = save_dashboard(html)

    # ── Screenshot ─────────────────────────────────────────────────────────
    if not args.html_only:
        print("\n  Capturing PNG screenshots...")
        output_dir = Path(args.output) if args.output else None
        screenshots = capture_dashboard_screenshot(current_path, output_dir)
        if screenshots:
            print(f"  {len(screenshots)} screenshot(s) captured")
        else:
            print("  No screenshots captured (Playwright may not be available)")

    print(f"\n  Done.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
