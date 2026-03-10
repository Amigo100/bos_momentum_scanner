#!/usr/bin/env python3
"""
Catalyst Calendar — HTML data graphic generator.

Generates a self-contained HTML catalyst calendar for Substack notes.
Cowork calls generate_catalyst_calendar(data) → HTML string, then
capture_static.py converts to PNG.

Design spec: COWORK_INSTRUCTIONS.md §7c
Fonts: Outfit (body), DM Serif Display (title), JetBrains Mono (data)
Width: 680px, white background, editorial style

Usage:
  # CLI
  python3 -m substack.tools.templates.catalyst_calendar \\
      --input events.json --output graphic.html

  # Python API
  from substack.tools.templates.catalyst_calendar import generate_catalyst_calendar
  html = generate_catalyst_calendar(data_dict)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


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

IMPACT_STYLES = {
    "CRITICAL": {"bg": "#fef2f2", "text": "#dc2626", "border": "#fecaca"},
    "HIGH":     {"bg": "#fdf6f4", "text": "#b45309", "border": "#fed7aa"},
    "MEDIUM":   {"bg": "#f4f7fa", "text": "#3d5a80", "border": "#dbeafe"},
}

PORTFOLIO_TAG_STYLE = {"bg": "#f0fdf4", "text": "#16a34a", "border": "#bbf7d0"}


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

.events {{
    padding: 0 28px;
}}

.event-row {{
    display: grid;
    grid-template-columns: 90px 1fr auto;
    align-items: start;
    gap: 16px;
    padding: 16px 0;
    border-top: 1px solid #f0ece7;
}}

.event-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #3d5a80;
    padding-top: 2px;
}}

.event-detail {{
    min-width: 0;
}}

.event-ticker {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
    display: inline;
}}

.event-description {{
    font-family: 'Outfit', sans-serif;
    font-size: 14px;
    color: #4a4540;
    line-height: 1.5;
    margin-top: 4px;
}}

.event-badges {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    padding-top: 2px;
    white-space: nowrap;
}}

.badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border-radius: 4px;
    border-width: 1px;
    border-style: solid;
}}

.badge-critical {{
    background: {IMPACT_STYLES["CRITICAL"]["bg"]};
    color: {IMPACT_STYLES["CRITICAL"]["text"]};
    border-color: {IMPACT_STYLES["CRITICAL"]["border"]};
}}

.badge-high {{
    background: {IMPACT_STYLES["HIGH"]["bg"]};
    color: {IMPACT_STYLES["HIGH"]["text"]};
    border-color: {IMPACT_STYLES["HIGH"]["border"]};
}}

.badge-medium {{
    background: {IMPACT_STYLES["MEDIUM"]["bg"]};
    color: {IMPACT_STYLES["MEDIUM"]["text"]};
    border-color: {IMPACT_STYLES["MEDIUM"]["border"]};
}}

.badge-portfolio {{
    background: {PORTFOLIO_TAG_STYLE["bg"]};
    color: {PORTFOLIO_TAG_STYLE["text"]};
    border-color: {PORTFOLIO_TAG_STYLE["border"]};
}}

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
# HTML GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _render_impact_badge(impact: str) -> str:
    """Render an impact level badge (CRITICAL, HIGH, MEDIUM)."""
    level = impact.upper()
    css_class = f"badge-{level.lower()}"
    if level not in IMPACT_STYLES:
        css_class = "badge-medium"
    return f'<span class="badge {css_class}">{level}</span>'


def _render_portfolio_tag(status: Optional[str]) -> str:
    """Render a portfolio status tag (HOLDING, SIGNAL), or empty string."""
    if not status:
        return ""
    label = status.upper()
    if label == "SIGNAL":
        label = "\U0001f7e2 SIGNAL"
    return f'<span class="badge badge-portfolio">{label}</span>'


def _render_event_row(event: Dict) -> str:
    """Render a single event row."""
    date = event.get("date", "")
    ticker = event.get("ticker", "")
    description = event.get("description", "")
    impact = event.get("impact", "MEDIUM")
    portfolio_status = event.get("portfolio_status")

    impact_badge = _render_impact_badge(impact)
    portfolio_tag = _render_portfolio_tag(portfolio_status)

    badges_html = impact_badge
    if portfolio_tag:
        badges_html += f"\n            {portfolio_tag}"

    return f"""
        <div class="event-row">
            <div class="event-date">{date}</div>
            <div class="event-detail">
                <span class="event-ticker">{ticker}</span>
                <div class="event-description">{description}</div>
            </div>
            <div class="event-badges">
                {badges_html}
            </div>
        </div>"""


def generate_catalyst_calendar(data: Dict) -> str:
    """Generate a self-contained HTML catalyst calendar graphic.

    Args:
        data: Dict with keys:
            week_label: str ("Week of March 10, 2026")
            events: List[dict], each with:
                date: str ("Wed 12")
                ticker: str ("$RCAT")
                description: str
                impact: str (CRITICAL | HIGH | MEDIUM)
                portfolio_status: str or None (HOLDING | SIGNAL | None)
            sources: str ("SEC filings, congressional calendar, FCC docket")

    Returns:
        Complete HTML string with Google Fonts + <style> block.
    """
    week_label = data.get("week_label", "This Week")
    events = data.get("events", [])
    sources = data.get("sources", "")

    # Render event rows
    event_rows = "".join(_render_event_row(e) for e in events)

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
            <div class="header-label">Catalyst Watch</div>
            <div class="header-title">{week_label}</div>
        </div>
        <div class="events">
{event_rows}
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
        description="Generate a catalyst calendar HTML graphic"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to JSON file with event data"
    )
    parser.add_argument(
        "--output", default="catalyst_calendar.html",
        help="Output HTML file path (default: catalyst_calendar.html)"
    )
    args = parser.parse_args()

    # Load input data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r") as f:
        data = json.load(f)

    # Generate HTML
    html = generate_catalyst_calendar(data)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"  \u2713 Generated: {output_path} ({len(data.get('events', []))} events)")


if __name__ == "__main__":
    main()
