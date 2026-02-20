#!/usr/bin/env python3
"""
STERLING SIGNALS - CENTRALISED HTML TEMPLATE SYSTEM
=====================================================
Provides two design themes for Substack posts:

  EDITORIAL  (serif, light background)
    - Stock deep dives, price targets, educational posts
    - Georgia/Times serif headings, system sans-serif body
    - Warm neutral palette adapted from ASPI design

  DASHBOARD  (dark, teal accents)
    - Market analysis, theme breakdowns, portfolio showcases
    - System sans-serif throughout
    - Dark card-based layout with teal/green/amber accents

All HTML is self-contained with inline styles or a single <style> block
per wrapper function. Substack strips external CSS, so everything must
be embedded. Max container width: 680px. System fonts only.

Usage:
    from substack.html_templates import (
        editorial_wrap, editorial_masthead, editorial_target_banner,
        dashboard_wrap, dashboard_hero, dashboard_stat_grid,
        footer_cta, disclaimer,
    )

No external dependencies -- pure Python with typing.
"""

from typing import Dict, List, Optional


# =============================================================================
# COLOUR PALETTES
# =============================================================================

EDITORIAL_COLORS = {
    "bg": "#fafaf8",
    "container": "#fff",
    "text": "#1a1a1a",
    "text_muted": "#6b6b6b",
    "label": "#8a7f72",
    "date": "#a09890",
    "ticker": "#6b5e50",
    "border": "#e0ddd8",
    # Price target banners
    "bear_bg": "#fdf6f4",
    "bear_label": "#a0522d",
    "bear_price": "#8b3a1a",
    "base_bg": "#f4f7fa",
    "base_label": "#3d5a80",
    "base_price": "#1b3a5c",
    "bull_bg": "#f4faf5",
    "bull_label": "#4a7c59",
    "bull_price": "#2e5e3e",
    # P&L
    "positive": "#2e5e3e",
    "negative": "#a04030",
    # Table
    "table_header_bg": "#2c2520",
    "table_header_text": "#f0ebe4",
    "table_alt_bg": "#faf9f7",
    "table_total_bg": "#f0ebe4",
    # Callouts
    "callout_border": "#c8bfb4",
    "callout_bg": "#faf9f7",
    "warning_border": "#c0833e",
    "warning_bg": "#fdf8f1",
    "key_border": "#3d5a80",
    "key_bg": "#f4f7fa",
    # Catalysts
    "catalyst_up": "#4a7c59",
    "catalyst_down": "#a04030",
}

DASHBOARD_COLORS = {
    "dark_bg": "#111827",
    "card_bg": "#1F2937",
    "border": "#374151",
    "text": "#F9FAFB",
    "text_muted": "#9CA3AF",
    "text_dim": "#6B7280",
    "teal": "#2DD4BF",
    "teal_bg": "#0D3B34",
    "teal_light": "#CCFBF1",
    "green": "#22C55E",
    "gold": "#F59E0B",
    "amber": "#FBBF24",
    "red": "#EF4444",
    "violet": "#A78BFA",
    "header_bg": "#0F172A",
}

# Shared font stacks
SERIF_FONT = "Georgia, 'Times New Roman', Times, serif"
SANS_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


# =============================================================================
# EDITORIAL THEME
# =============================================================================

def editorial_wrap(body: str, title: str) -> str:
    """Full HTML document wrapper with complete CSS in <style> block.

    Args:
        body: Inner HTML content (all editorial_* helper output concatenated).
        title: Page <title> value.

    Returns:
        Complete self-contained HTML document string.
    """
    c = EDITORIAL_COLORS
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)} - Sterling Signals</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: {SANS_FONT};
      background: {c['bg']};
      color: {c['text']};
      line-height: 1.7;
      -webkit-font-smoothing: antialiased;
    }}
    .ed-container {{
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 24px;
      background: {c['container']};
    }}
    .ed-container p {{
      font-size: 16px;
      line-height: 1.7;
      color: {c['text']};
      margin: 14px 0;
    }}
    .ed-container a {{
      color: {c['base_label']};
      text-decoration: underline;
    }}
    .ed-container ul, .ed-container ol {{
      padding-left: 24px;
      margin: 12px 0;
    }}
    .ed-container li {{
      font-size: 15px;
      line-height: 1.7;
      margin: 6px 0;
    }}
    .ed-container strong {{
      font-weight: 700;
    }}
    @media (max-width: 600px) {{
      .ed-container {{
        padding: 20px 16px;
      }}
      .ed-target-grid {{
        flex-direction: column !important;
        gap: 12px !important;
      }}
      .ed-target-col {{
        width: 100% !important;
      }}
      .ed-stat-row {{
        flex-wrap: wrap !important;
      }}
      .ed-stat-box {{
        min-width: 140px !important;
        flex: 1 1 45% !important;
      }}
      .ed-table-wrap {{
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <div class="ed-container">
{body}
  </div>
</body>
</html>"""


def editorial_masthead(
    title: str,
    subtitle: str = "",
    date: str = "",
    ticker: str = "",
    price: str = "",
) -> str:
    """Centered masthead with brand, date, title, optional ticker line.

    Args:
        title: Main headline text.
        subtitle: Optional subtitle below the title.
        date: Optional date string (e.g., 'February 18, 2026').
        ticker: Optional ticker symbol (e.g., 'NVDA').
        price: Optional price string (e.g., '$125.40').

    Returns:
        HTML string for the masthead block.
    """
    c = EDITORIAL_COLORS
    parts = []

    # Brand line
    parts.append(
        f'<div style="text-align:center;padding:8px 0 24px 0;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:{c["label"]};">Sterling Signals</div>'
    )

    # Date
    if date:
        parts.append(
            f'<div style="font-size:13px;color:{c["date"]};margin-top:6px;">{_esc(date)}</div>'
        )

    # Ticker + price line
    if ticker:
        ticker_html = (
            f'<div style="margin-top:16px;font-size:14px;font-weight:600;'
            f'letter-spacing:1px;color:{c["ticker"]};">'
            f'${_esc(ticker.upper())}'
        )
        if price:
            ticker_html += f' &middot; {_esc(price)}'
        ticker_html += '</div>'
        parts.append(ticker_html)

    # Title
    parts.append(
        f'<h1 style="font-family:{SERIF_FONT};font-size:32px;font-weight:700;'
        f'line-height:1.25;color:{c["text"]};margin-top:16px;">{_esc(title)}</h1>'
    )

    # Subtitle
    if subtitle:
        parts.append(
            f'<div style="font-size:16px;color:{c["text_muted"]};margin-top:8px;'
            f'line-height:1.5;">{_esc(subtitle)}</div>'
        )

    parts.append('</div>')

    # Divider
    parts.append(
        f'<hr style="border:none;border-top:1px solid {c["border"]};margin:0 0 24px 0;">'
    )

    return "\n".join(parts)


def editorial_target_banner(bear: Dict, base: Dict, bull: Dict) -> str:
    """3-column price target banner.

    Args:
        bear: Dict with 'price' (str) and 'upside' (str) keys.
        base: Dict with 'price' (str) and 'upside' (str) keys.
        bull: Dict with 'price' (str) and 'upside' (str) keys.

    Returns:
        HTML string for the price target banner.
    """
    c = EDITORIAL_COLORS

    def _col(label: str, data: Dict, bg: str, label_color: str, price_color: str) -> str:
        return (
            f'<div class="ed-target-col" style="flex:1;background:{bg};'
            f'border-radius:8px;padding:20px 16px;text-align:center;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:1px;'
            f'text-transform:uppercase;color:{label_color};">{label}</div>'
            f'<div style="font-size:28px;font-weight:800;color:{price_color};'
            f'margin:8px 0 4px 0;">{_esc(str(data.get("price", "")))}</div>'
            f'<div style="font-size:13px;color:{label_color};">'
            f'{_esc(str(data.get("upside", "")))}</div>'
            f'</div>'
        )

    return (
        f'<div class="ed-target-grid" style="display:flex;gap:16px;margin:24px 0;">'
        f'{_col("Bear Case", bear, c["bear_bg"], c["bear_label"], c["bear_price"])}'
        f'{_col("Base Case", base, c["base_bg"], c["base_label"], c["base_price"])}'
        f'{_col("Bull Case", bull, c["bull_bg"], c["bull_label"], c["bull_price"])}'
        f'</div>'
    )


def editorial_stat_row(items: List[Dict]) -> str:
    """Flex row of stat boxes.

    Args:
        items: List of dicts, each with 'label' (str) and 'value' (str) keys.

    Returns:
        HTML string for the stat row.
    """
    c = EDITORIAL_COLORS
    boxes = []
    for item in items:
        label = _esc(str(item.get("label", "")))
        value = _esc(str(item.get("value", "")))
        boxes.append(
            f'<div class="ed-stat-box" style="flex:1;text-align:center;'
            f'padding:16px 12px;border:1px solid {c["border"]};border-radius:8px;'
            f'background:{c["container"]};">'
            f'<div style="font-size:11px;font-weight:600;letter-spacing:0.5px;'
            f'text-transform:uppercase;color:{c["label"]};margin-bottom:6px;">'
            f'{label}</div>'
            f'<div style="font-family:{SERIF_FONT};font-size:22px;font-weight:700;'
            f'color:{c["text"]};">{value}</div>'
            f'</div>'
        )

    return (
        f'<div class="ed-stat-row" style="display:flex;gap:12px;margin:20px 0;">'
        f'{"".join(boxes)}'
        f'</div>'
    )


def editorial_callout(text: str, variant: str = "default") -> str:
    """Left-border callout box.

    Args:
        text: Content of the callout (plain text or HTML).
        variant: One of 'default', 'warning', 'key'.

    Returns:
        HTML string for the callout block.
    """
    c = EDITORIAL_COLORS
    variant_map = {
        "default": (c["callout_border"], c["callout_bg"]),
        "warning": (c["warning_border"], c["warning_bg"]),
        "key": (c["key_border"], c["key_bg"]),
    }
    border_color, bg_color = variant_map.get(variant, variant_map["default"])

    return (
        f'<div style="border-left:4px solid {border_color};background:{bg_color};'
        f'padding:16px 20px;margin:20px 0;border-radius:0 6px 6px 0;">'
        f'<div style="font-size:15px;line-height:1.7;color:{c["text"]};">{text}</div>'
        f'</div>'
    )


def editorial_financial_table(
    headers: List[str],
    rows: List[List[str]],
    total_row: Optional[List[str]] = None,
) -> str:
    """Table with dark header, alternating rows.

    Args:
        headers: List of header strings.
        rows: List of row lists (each row is a list of cell strings).
        total_row: Optional total/summary row (list of cell strings).

    Returns:
        HTML string for the table.
    """
    c = EDITORIAL_COLORS

    # Header
    header_cells = "".join(
        f'<th style="padding:10px 14px;text-align:left;font-size:12px;'
        f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
        f'color:{c["table_header_text"]};white-space:nowrap;">{_esc(h)}</th>'
        for h in headers
    )

    # Body rows
    body_rows = []
    for i, row in enumerate(rows):
        bg = c["table_alt_bg"] if i % 2 == 1 else c["container"]
        cells = "".join(
            f'<td style="padding:10px 14px;font-size:14px;'
            f'border-bottom:1px solid {c["border"]};">{_esc(cell)}</td>'
            for cell in row
        )
        body_rows.append(f'<tr style="background:{bg};">{cells}</tr>')

    # Total row
    total_html = ""
    if total_row:
        total_cells = "".join(
            f'<td style="padding:12px 14px;font-size:14px;font-weight:700;">'
            f'{_esc(cell)}</td>'
            for cell in total_row
        )
        total_html = (
            f'<tr style="background:{c["table_total_bg"]};">{total_cells}</tr>'
        )

    return (
        f'<div class="ed-table-wrap" style="margin:20px 0;border-radius:8px;'
        f'overflow:hidden;border:1px solid {c["border"]};">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="background:{c["table_header_bg"]};">'
        f'{header_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}{total_html}</tbody>'
        f'</table></div>'
    )


def editorial_catalyst_list(items: List[str], direction: str = "up") -> str:
    """Styled bullet list with colored dots.

    Args:
        items: List of catalyst description strings.
        direction: 'up' for green dots or 'down' for red dots.

    Returns:
        HTML string for the catalyst list.
    """
    c = EDITORIAL_COLORS
    dot_color = c["catalyst_up"] if direction == "up" else c["catalyst_down"]

    bullets = []
    for item in items:
        bullets.append(
            f'<li style="list-style:none;padding:6px 0;font-size:15px;'
            f'line-height:1.6;color:{c["text"]};">'
            f'<span style="display:inline-block;width:8px;height:8px;'
            f'border-radius:50%;background:{dot_color};margin-right:10px;'
            f'vertical-align:middle;"></span>'
            f'{_esc(item)}</li>'
        )

    return (
        f'<ul style="list-style:none;padding:0;margin:16px 0;">'
        f'{"".join(bullets)}</ul>'
    )


def editorial_risk_block(title: str, text: str) -> str:
    """Risk discussion block with bold title and paragraph.

    Args:
        title: Risk block heading.
        text: Risk description paragraph.

    Returns:
        HTML string for the risk block.
    """
    c = EDITORIAL_COLORS
    return (
        f'<div style="margin:20px 0;">'
        f'<div style="font-family:{SERIF_FONT};font-size:18px;font-weight:700;'
        f'color:{c["text"]};margin-bottom:8px;">{_esc(title)}</div>'
        f'<p style="font-size:15px;line-height:1.7;color:{c["text_muted"]};'
        f'margin:0;">{_esc(text)}</p>'
        f'</div>'
    )


def editorial_section(title: str) -> str:
    """Section header (H2 style -- uppercase, small, letter-spaced).

    Args:
        title: Section title text.

    Returns:
        HTML string for the section header.
    """
    c = EDITORIAL_COLORS
    return (
        f'<h2 style="font-size:12px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:{c["label"]};margin:36px 0 16px 0;'
        f'padding-bottom:10px;border-bottom:1px solid {c["border"]};">'
        f'{_esc(title)}</h2>'
    )


def editorial_subsection(title: str) -> str:
    """Subsection header (H3 style -- serif, large).

    Args:
        title: Subsection title text.

    Returns:
        HTML string for the subsection header.
    """
    c = EDITORIAL_COLORS
    return (
        f'<h3 style="font-family:{SERIF_FONT};font-size:22px;font-weight:700;'
        f'color:{c["text"]};margin:28px 0 12px 0;">{_esc(title)}</h3>'
    )


def editorial_sources(text: str) -> str:
    """Source footnotes section.

    Args:
        text: Sources/footnotes content (plain text or HTML).

    Returns:
        HTML string for the sources block.
    """
    c = EDITORIAL_COLORS
    return (
        f'<div style="margin-top:36px;padding-top:16px;'
        f'border-top:1px solid {c["border"]};">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;color:{c["label"]};margin-bottom:8px;">'
        f'Sources</div>'
        f'<div style="font-size:12px;line-height:1.6;color:{c["text_muted"]};">'
        f'{text}</div></div>'
    )


def editorial_disclaimer() -> str:
    """Standard disclaimer footer for editorial theme.

    Returns:
        HTML string for the disclaimer.
    """
    c = EDITORIAL_COLORS
    return (
        f'<div style="margin-top:36px;padding-top:16px;'
        f'border-top:1px solid {c["border"]};text-align:center;">'
        f'<p style="font-size:11px;line-height:1.6;color:{c["date"]};margin:0;">'
        f'This is for informational purposes only and does not constitute '
        f'financial advice. All investment decisions should be made based on '
        f'your own research and risk tolerance. Past performance does not '
        f'guarantee future results.</p></div>'
    )


# =============================================================================
# DASHBOARD THEME
# =============================================================================

def dashboard_wrap(body: str, title: str) -> str:
    """Full HTML document wrapper with dark theme CSS.

    Args:
        body: Inner HTML content (all dashboard_* helper output concatenated).
        title: Page <title> value.

    Returns:
        Complete self-contained HTML document string.
    """
    c = DASHBOARD_COLORS
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)} - Sterling Signals</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: {SANS_FONT};
      background: {c['dark_bg']};
      color: {c['text']};
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}
    .db-container {{
      max-width: 680px;
      margin: 0 auto;
      padding: 24px;
    }}
    .db-container p {{
      font-size: 15px;
      line-height: 1.7;
      color: #D1D5DB;
      margin: 10px 0;
    }}
    .db-container a {{
      color: {c['teal']};
      text-decoration: none;
    }}
    .db-container a:hover {{
      text-decoration: underline;
    }}
    .db-container ul, .db-container ol {{
      padding-left: 20px;
      margin: 10px 0;
    }}
    .db-container li {{
      font-size: 14px;
      line-height: 1.7;
      color: #D1D5DB;
      margin: 4px 0;
    }}
    .db-container strong {{
      color: {c['text']};
    }}
    @media (max-width: 600px) {{
      .db-container {{
        padding: 16px;
      }}
      .db-stat-grid {{
        grid-template-columns: 1fr 1fr !important;
      }}
      .db-two-col {{
        grid-template-columns: 1fr !important;
      }}
    }}
  </style>
</head>
<body>
  <div class="db-container">
{body}
  </div>
</body>
</html>"""


def dashboard_hero(
    title: str,
    subtitle: str = "",
    date: str = "",
    badge: str = "",
) -> str:
    """Gradient hero section with badge, title, subtitle.

    The title may include text wrapped in <span> tags which will render
    in teal. For convenience, any text between {teal} and {/teal} markers
    will automatically be wrapped in a teal-coloured <span>.

    Args:
        title: Main headline. Use {teal}text{/teal} for teal emphasis.
        subtitle: Optional description below the title.
        date: Optional date line.
        badge: Optional badge text (e.g., 'Sterling Signals Weekly').

    Returns:
        HTML string for the hero section.
    """
    c = DASHBOARD_COLORS

    # Convert {teal}...{/teal} markers to spans
    rendered_title = title.replace(
        "{teal}", f'<span style="color:{c["teal"]};">'
    ).replace("{/teal}", "</span>")

    parts = []
    parts.append(
        f'<div style="text-align:center;padding:48px 24px 40px;'
        f'background:linear-gradient(135deg, {c["header_bg"]} 0%, #1a2744 50%, '
        f'{c["header_bg"]} 100%);border-bottom:2px solid {c["teal"]};'
        f'margin:-24px -24px 0 -24px;">'
    )

    if badge:
        parts.append(
            f'<div style="display:inline-block;padding:4px 14px;border-radius:4px;'
            f'font-size:11px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;background:rgba(45,212,191,0.15);'
            f'color:{c["teal"]};border:1px solid {c["teal"]};margin-bottom:16px;">'
            f'{_esc(badge)}</div>'
        )

    parts.append(
        f'<h1 style="font-size:32px;font-weight:800;line-height:1.2;'
        f'color:{c["text"]};margin-bottom:12px;">{rendered_title}</h1>'
    )

    if subtitle:
        parts.append(
            f'<p style="font-size:16px;color:{c["text_muted"]};line-height:1.5;'
            f'max-width:520px;margin:0 auto;">{_esc(subtitle)}</p>'
        )

    if date:
        parts.append(
            f'<p style="font-size:13px;color:{c["text_dim"]};margin-top:16px;">'
            f'{_esc(date)}</p>'
        )

    parts.append('</div>')

    return "\n".join(parts)


def dashboard_stat_grid(items: List[Dict], cols: int = 3) -> str:
    """CSS Grid stat boxes.

    Args:
        items: List of dicts with 'value' (str), 'label' (str),
               and optional 'color' (str, CSS color) keys.
        cols: Number of grid columns (default 3).

    Returns:
        HTML string for the stat grid.
    """
    c = DASHBOARD_COLORS

    boxes = []
    for item in items:
        value = _esc(str(item.get("value", "")))
        label = _esc(str(item.get("label", "")))
        color = item.get("color", c["text"])
        boxes.append(
            f'<div style="background:{c["card_bg"]};border:1px solid {c["border"]};'
            f'border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="font-size:28px;font-weight:800;color:{color};">'
            f'{value}</div>'
            f'<div style="font-size:11px;color:{c["text_muted"]};margin-top:4px;'
            f'text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
            f'</div>'
        )

    return (
        f'<div class="db-stat-grid" style="display:grid;'
        f'grid-template-columns:repeat({cols}, 1fr);gap:12px;margin:24px 0;">'
        f'{"".join(boxes)}</div>'
    )


def dashboard_theme_card(
    name: str,
    classification: str,
    score: float,
    subscores: Optional[Dict] = None,
    description: str = "",
    catalysts: str = "",
) -> str:
    """Theme card with badge, score, optional progress bars for subscores.

    Args:
        name: Theme name.
        classification: Theme classification (e.g., 'PRIME', 'INVESTABLE').
        score: Composite score (0-10).
        subscores: Optional dict of subscore name -> value (0-10).
        description: Optional theme thesis text.
        catalysts: Optional catalysts text (displayed in a callout).

    Returns:
        HTML string for the theme card.
    """
    c = DASHBOARD_COLORS

    badge_colors = {
        "PRIME": (c["green"], "#052e16"),
        "INVESTABLE": (c["gold"], "#451A03"),
        "SELECTIVE": (c["violet"], "#1e1b4b"),
        "AVOID": (c["red"], "#450a0a"),
    }
    badge_bg, badge_text = badge_colors.get(
        classification.upper(), (c["text_muted"], c["dark_bg"])
    )

    # Determine accent color from classification
    accent = c["green"] if classification.upper() == "PRIME" else c["gold"]

    parts = []

    # Card open with left border
    parts.append(
        f'<div style="background:{c["card_bg"]};border:1px solid {c["border"]};'
        f'border-left:4px solid {accent};border-radius:10px;padding:20px;'
        f'margin:12px 0;">'
    )

    # Header row: name + badge
    parts.append(
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:10px;">'
        f'<strong style="font-size:16px;color:{c["text"]};">{_esc(name)}</strong>'
        f'<span style="padding:3px 10px;border-radius:12px;font-size:11px;'
        f'font-weight:700;letter-spacing:0.5px;background:{badge_bg};'
        f'color:{badge_text};">{_esc(classification.upper())}</span>'
        f'</div>'
    )

    # Score display
    parts.append(
        f'<div style="font-size:32px;font-weight:800;color:{c["text"]};'
        f'margin:4px 0;">{score:.1f}'
        f'<span style="font-size:14px;color:{c["text_dim"]};">/10</span></div>'
    )

    # Subscores progress bars
    if subscores:
        parts.append(
            '<div style="display:flex;gap:12px;margin:10px 0;">'
        )
        for sub_name, sub_val in subscores.items():
            pct = min(float(sub_val) / 10.0 * 100, 100)
            parts.append(
                f'<div style="flex:1;">'
                f'<div style="font-size:11px;color:{c["text_muted"]};'
                f'text-transform:uppercase;letter-spacing:0.3px;display:flex;'
                f'justify-content:space-between;">'
                f'<span>{_esc(sub_name)}</span>'
                f'<span>{sub_val:.0f}/10</span></div>'
                f'<div style="background:{c["border"]};border-radius:4px;'
                f'height:6px;overflow:hidden;margin-top:4px;">'
                f'<div style="background:{accent};height:100%;width:{pct:.0f}%;'
                f'border-radius:4px;"></div></div></div>'
            )
        parts.append('</div>')

    # Description
    if description:
        parts.append(
            f'<p style="font-size:14px;margin-top:8px;color:#D1D5DB;'
            f'line-height:1.6;">{_esc(description)}</p>'
        )

    # Catalysts callout
    if catalysts:
        parts.append(
            f'<div style="margin-top:12px;background:rgba({_hex_to_rgb(accent)},0.08);'
            f'border:1px solid rgba({_hex_to_rgb(accent)},0.3);border-radius:8px;'
            f'padding:12px 16px;font-size:14px;line-height:1.6;'
            f'color:{c["teal_light"]};">'
            f'<strong style="color:{accent};">Key Catalysts:</strong> '
            f'{_esc(catalysts)}</div>'
        )

    parts.append('</div>')

    return "\n".join(parts)


def dashboard_rotation_bars(sectors: List[Dict]) -> str:
    """Horizontal bar chart for sector rotation.

    Supports both positive and negative values. Negative values are
    rendered right-aligned within the track.

    Args:
        sectors: List of dicts with 'name' (str), 'value' (float or str
                 for display), and 'color' (str, CSS color) keys.
                 Optionally include 'pct' (float, 0-100) for bar width;
                 if absent, abs(value) is used as percentage of the
                 largest absolute value.

    Returns:
        HTML string for the rotation bar chart.
    """
    c = DASHBOARD_COLORS

    # Determine maximum absolute value for scaling if no 'pct' provided
    abs_values = []
    for s in sectors:
        v = s.get("value", 0)
        if isinstance(v, (int, float)):
            abs_values.append(abs(v))
    max_abs = max(abs_values) if abs_values else 100

    bars = []
    for s in sectors:
        name = _esc(str(s.get("name", "")))
        color = s.get("color", c["teal"])
        value = s.get("value", 0)

        # Display label
        if isinstance(value, (int, float)):
            display = f"{value:+.1f}%" if value != 0 else "0%"
            is_negative = value < 0
            pct = s.get("pct", abs(value) / max_abs * 100 if max_abs > 0 else 0)
        else:
            display = str(value)
            is_negative = str(value).startswith("-")
            pct = s.get("pct", 50)

        pct = min(max(pct, 4), 100)  # Clamp between 4-100

        if is_negative:
            fill_html = (
                f'<div style="position:absolute;right:0;height:100%;'
                f'width:{pct:.0f}%;background:{color};border-radius:4px;'
                f'display:flex;align-items:center;justify-content:flex-start;'
                f'padding-left:8px;font-size:11px;font-weight:700;'
                f'color:{c["text"]};min-width:40px;">{_esc(display)}</div>'
            )
        else:
            fill_html = (
                f'<div style="height:100%;width:{pct:.0f}%;background:{color};'
                f'border-radius:4px;display:flex;align-items:center;'
                f'justify-content:flex-end;padding-right:8px;font-size:11px;'
                f'font-weight:700;color:{c["text"]};min-width:40px;">'
                f'{_esc(display)}</div>'
            )

        bars.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0;'
            f'font-size:13px;">'
            f'<div style="width:130px;text-align:right;color:{c["text_muted"]};'
            f'font-size:12px;flex-shrink:0;">{name}</div>'
            f'<div style="flex:1;background:{c["border"]};height:22px;'
            f'border-radius:4px;overflow:hidden;position:relative;">'
            f'{fill_html}</div></div>'
        )

    return (
        f'<div style="background:{c["card_bg"]};border:1px solid {c["border"]};'
        f'border-radius:8px;padding:20px;margin:16px 0;">'
        f'{"".join(bars)}</div>'
    )


def dashboard_funnel(stages: List[Dict]) -> str:
    """Numbered funnel steps.

    Args:
        stages: List of dicts with 'number' (int or str), 'count' (int or str),
                and 'label' (str) keys.

    Returns:
        HTML string for the funnel visualization.
    """
    c = DASHBOARD_COLORS

    # Colour gradient from dim to teal
    gradient = [
        f"{c['border']}", "#374151", "#1e3a5f", "#1e3a5f", c["teal_bg"],
    ]

    text_colors = [
        c["text_muted"], "#D1D5DB", "#60A5FA", "#93C5FD", c["teal"],
    ]

    steps = []
    for i, stage in enumerate(stages):
        number = _esc(str(stage.get("number", i + 1)))
        count = _esc(str(stage.get("count", "")))
        label = _esc(str(stage.get("label", "")))
        bg = gradient[min(i, len(gradient) - 1)]
        fg = text_colors[min(i, len(text_colors) - 1)]

        steps.append(
            f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0;">'
            f'<div style="width:32px;height:32px;border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-weight:700;font-size:14px;flex-shrink:0;'
            f'background:{bg};color:{fg};">{number}</div>'
            f'<div style="font-size:14px;color:#D1D5DB;">'
            f'<strong style="color:{c["text"]};">{count}</strong> {label}</div>'
            f'</div>'
        )

    return (
        f'<div style="background:{c["card_bg"]};border:1px solid {c["border"]};'
        f'border-radius:8px;padding:20px;margin:16px 0;">'
        f'{"".join(steps)}</div>'
    )


def dashboard_pullquote(text: str) -> str:
    """Teal left-border italic large text.

    Args:
        text: Quote text.

    Returns:
        HTML string for the pullquote.
    """
    c = DASHBOARD_COLORS
    return (
        f'<div style="border-left:3px solid {c["teal"]};padding:12px 20px;'
        f'margin:20px 0;font-size:17px;font-weight:600;color:{c["text"]};'
        f'line-height:1.5;font-style:italic;">{_esc(text)}</div>'
    )


def dashboard_winners_table(winners: List[Dict]) -> str:
    """Dark table with ticker, theme, P&L, days columns.

    Args:
        winners: List of dicts with keys: 'ticker' (str), 'theme' (str),
                 'pnl' (str or float), and optionally 'days' (int or str).

    Returns:
        HTML string for the winners table.
    """
    c = DASHBOARD_COLORS

    header = (
        f'<thead><tr>'
        f'<th style="background:{c["border"]};color:#D1D5DB;font-weight:600;'
        f'text-align:left;padding:10px 12px;font-size:11px;'
        f'text-transform:uppercase;letter-spacing:0.5px;">Ticker</th>'
        f'<th style="background:{c["border"]};color:#D1D5DB;font-weight:600;'
        f'text-align:left;padding:10px 12px;font-size:11px;'
        f'text-transform:uppercase;letter-spacing:0.5px;">Theme</th>'
        f'<th style="background:{c["border"]};color:#D1D5DB;font-weight:600;'
        f'text-align:right;padding:10px 12px;font-size:11px;'
        f'text-transform:uppercase;letter-spacing:0.5px;">P&amp;L</th>'
        f'<th style="background:{c["border"]};color:#D1D5DB;font-weight:600;'
        f'text-align:right;padding:10px 12px;font-size:11px;'
        f'text-transform:uppercase;letter-spacing:0.5px;">Days</th>'
        f'</tr></thead>'
    )

    rows = []
    for w in winners:
        ticker = _esc(str(w.get("ticker", "")))
        theme = _esc(str(w.get("theme", "")))
        pnl_raw = w.get("pnl", "")
        days = _esc(str(w.get("days", "")))

        # Format P&L with color
        if isinstance(pnl_raw, (int, float)):
            pnl_color = c["green"] if pnl_raw >= 0 else c["red"]
            pnl_display = f"+{pnl_raw:.1f}%" if pnl_raw >= 0 else f"{pnl_raw:.1f}%"
        else:
            pnl_str = str(pnl_raw)
            pnl_color = c["green"] if not pnl_str.startswith("-") else c["red"]
            pnl_display = _esc(pnl_str)

        rows.append(
            f'<tr>'
            f'<td style="padding:10px 12px;border-bottom:1px solid {c["border"]};'
            f'font-weight:700;color:{c["text"]};letter-spacing:0.5px;">'
            f'${ticker}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid {c["border"]};'
            f'color:#D1D5DB;">{theme}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid {c["border"]};'
            f'text-align:right;color:{pnl_color};font-weight:700;">'
            f'{pnl_display}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid {c["border"]};'
            f'text-align:right;color:#D1D5DB;">{days}</td>'
            f'</tr>'
        )

    return (
        f'<div style="background:{c["card_bg"]};border:1px solid {c["border"]};'
        f'border-radius:8px;overflow:hidden;margin:16px 0;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;">'
        f'{header}<tbody>{"".join(rows)}</tbody></table></div>'
    )


def dashboard_card(
    content: str,
    border_color: Optional[str] = None,
    highlight: bool = False,
) -> str:
    """Card wrapper with optional left border color.

    Args:
        content: Inner HTML content.
        border_color: Optional CSS color for a 4px left border accent.
        highlight: If True, uses teal background instead of card_bg.

    Returns:
        HTML string for the card.
    """
    c = DASHBOARD_COLORS

    if highlight:
        bg = c["teal_bg"]
        border_style = f"border:1px solid {c['teal']};"
    else:
        bg = c["card_bg"]
        border_style = f"border:1px solid {c['border']};"

    left_border = f"border-left:4px solid {border_color};" if border_color else ""

    return (
        f'<div style="background:{bg};{border_style}{left_border}'
        f'border-radius:8px;padding:20px;margin:16px 0;">'
        f'{content}</div>'
    )


def dashboard_two_col(left: str, right: str) -> str:
    """Two-column CSS Grid layout.

    Args:
        left: HTML content for the left column.
        right: HTML content for the right column.

    Returns:
        HTML string for the two-column layout.
    """
    return (
        f'<div class="db-two-col" style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;">'
        f'<div>{left}</div><div>{right}</div></div>'
    )


def dashboard_section(title: str) -> str:
    """Section header with teal color and bottom border.

    Args:
        title: Section title text.

    Returns:
        HTML string for the section header.
    """
    c = DASHBOARD_COLORS
    return (
        f'<h2 style="color:{c["teal"]};font-size:18px;margin:32px 0 12px 0;'
        f'padding-bottom:8px;border-bottom:1px solid {c["border"]};">'
        f'{_esc(title)}</h2>'
    )


# =============================================================================
# SHARED COMPONENTS
# =============================================================================

def footer_cta(
    substack_url: str = "https://sterlingsignals.substack.com",
) -> str:
    """Subscribe CTA footer. Works with both themes.

    Args:
        substack_url: URL for the subscribe link.

    Returns:
        HTML string for the CTA footer.
    """
    return (
        f'<div style="text-align:center;padding:32px 0 16px 0;">'
        f'<div style="font-size:13px;color:#9CA3AF;margin-bottom:8px;">'
        f'Proprietary screening system</div>'
        f'<div style="font-size:13px;color:#9CA3AF;">'
        f'Filters 1,800 stocks to 3-5 actionable signals</div>'
        f'<div style="margin-top:12px;">'
        f'<a href="{_esc(substack_url)}" style="color:#2DD4BF;'
        f'text-decoration:none;font-weight:600;">'
        f'Subscribe to Sterling Signals</a></div></div>'
    )


def disclaimer() -> str:
    """Standard disclaimer text. Works with both themes.

    Returns:
        HTML string for the disclaimer.
    """
    return (
        '<div style="margin-top:16px;text-align:center;font-size:11px;'
        'line-height:1.6;color:#6B7280;">'
        'This is for informational purposes only and does not constitute '
        'financial advice. All investment decisions should be made based on '
        'your own research and risk tolerance. Past performance does not '
        'guarantee future results.</div>'
    )


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _esc(text: str) -> str:
    """Minimal HTML entity escaping for dynamic text insertion.

    Only escapes &, <, > to prevent HTML injection while allowing
    intentional HTML to pass through when functions accept HTML content.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert a hex color like '#2DD4BF' to an 'r,g,b' string for rgba().

    Args:
        hex_color: Hex color string (with or without '#').

    Returns:
        Comma-separated RGB string, e.g., '45,212,191'.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    except (ValueError, IndexError):
        return "128,128,128"
