#!/usr/bin/env python3
"""
STERLING SIGNALS - DD HTML POST GENERATOR
==========================================
Generates comprehensive standalone HTML pages per buy signal with full
Deep DD analysis. Output as HTML files + optional PNG screenshots for Substack.

Usage:
    python -m content.dd_post_generator                           # All PASS signals
    python -m content.dd_post_generator --ticker NVDA             # Specific ticker
    python -m content.dd_post_generator --signals path/to/signals.json
    python -m content.dd_post_generator --dry-run                 # Preview to stdout

Output: trades/current/substack_posts/dd_TICKER.html (+ weekly archive)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Config imports
from config import SIGNALS_FILE, get_conviction_text, CURRENCY_SYMBOL

# Marketing validation
from config.banned_terms import validate_content
from config.banned_terms import INTERNAL_TERMINOLOGY_MAP, CRITICAL_BANNED

# Output paths
try:
    from config.output_paths import (
        CHARTS_DIR,
        ensure_output_structure,
        get_scanner_current_dir,
        get_substack_current_dir,
        get_substack_archive_dir,
        save_to_substack_current_and_archive,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# COLORS & CONSTANTS (matching portfolio_visual.py / substack_content_generator.py)
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "teal": "#2DD4BF",
    "teal_bg": "#0D3B34",
    "teal_light": "#CCFBF1",
    "violet": "#A78BFA",
    "violet_bg": "#2E1065",
    "amber": "#FBBF24",
    "amber_bg": "#451A03",
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

BRANDING = {
    "substack_url": "https://sterlingsignals.substack.com",
    "tagline": "Proprietary screening system",
}


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

def _sanitize_text(text: str) -> str:
    """Replace internal terminology with public-facing alternatives."""
    if not text:
        return ""
    result = text
    for internal, public in INTERNAL_TERMINOLOGY_MAP.items():
        result = re.sub(re.escape(internal), public, result, flags=re.IGNORECASE)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# HTML HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _stat_box(value: str, label: str, color: str = "") -> str:
    """Create a summary stat box."""
    value_style = f"color:{color};" if color else f"color:{COLORS['text']};"
    return f"""<div style="background:{COLORS['card_bg']};border:1px solid {COLORS['border']};border-radius:8px;padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:700;{value_style}">{value}</div>
      <div style="font-size:12px;color:{COLORS['text_muted']};margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
    </div>"""


def _progress_bar(
    value: float,
    max_val: float = 10.0,
    label: str = "",
    color: str = ""
) -> str:
    """Generate an inline progress bar for theme scores."""
    if not color:
        color = COLORS["teal"]
    pct = min(value / max_val * 100, 100) if max_val > 0 else 0
    return f"""<div style="margin:6px 0;">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:{COLORS['text_muted']};">
        <span>{label}</span><span>{value:.1f}/{max_val:.0f}</span>
      </div>
      <div style="background:{COLORS['border']};border-radius:4px;height:8px;overflow:hidden;">
        <div style="background:{color};height:100%;width:{pct:.0f}%;border-radius:4px;"></div>
      </div>
    </div>"""


def _card(content: str, border_color: str = "") -> str:
    """Wrap content in a styled card. Optional left border accent."""
    border_style = f"border-left:4px solid {border_color};" if border_color else ""
    return f"""<div style="background:{COLORS['card_bg']};border:1px solid {COLORS['border']};border-radius:8px;padding:20px;margin:16px 0;{border_style}">
{content}
</div>"""


def _highlight_card(content: str, bg_color: str = "") -> str:
    """Wrap content in a highlighted card (gradient background)."""
    if not bg_color:
        bg_color = COLORS["teal_bg"]
    return f"""<div style="background:{bg_color};border:1px solid {COLORS['teal']};border-radius:8px;padding:20px;margin:16px 0;">
{content}
</div>"""


def _section_header(title: str) -> str:
    """Create a styled section header."""
    return f"""<h2 style="color:{COLORS['teal']};font-size:18px;margin:24px 0 12px 0;padding-bottom:8px;border-bottom:1px solid {COLORS['border']};">{title}</h2>"""


def _signal_badge(signal_type: str) -> str:
    """Create a colored signal badge using approved marketing language."""
    badge_map = {
        "PASS": ("GREEN SIGNAL", COLORS["teal"], COLORS["teal_bg"]),
        "TRADE": ("GREEN SIGNAL", COLORS["teal"], COLORS["teal_bg"]),
        "GREEN": ("GREEN SIGNAL", COLORS["teal"], COLORS["teal_bg"]),
        "CONSIDER": ("ON OUR RADAR", COLORS["amber"], COLORS["amber_bg"]),
        "CAUTION": ("ON OUR RADAR", COLORS["amber"], COLORS["amber_bg"]),
    }
    text, fg, bg = badge_map.get(signal_type.upper(), ("SIGNAL", COLORS["teal"], COLORS["teal_bg"]))
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:4px;'
        f'font-size:12px;font-weight:700;letter-spacing:0.5px;'
        f'background:{bg};color:{fg};border:1px solid {fg};">{text}</span>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DD POST GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dd_post(signal: Dict, themes: List[Dict] = None) -> str:
    """Generate a comprehensive DD HTML post for a single buy signal.

    Args:
        signal: Buy signal dict from signals.json
        themes: List of theme dicts from signals.json (for sub-score context)

    Returns:
        Complete self-contained HTML string.
    """
    ticker = signal.get("symbol", "???")
    price = signal.get("price", 0)
    decision = signal.get("final_decision", "PASS")
    theme_name = signal.get("theme", "N/A")
    theme_verdict = signal.get("theme_verdict", "")
    conviction_num = signal.get("dd_conviction") or signal.get("conviction", 0)
    conviction_text = get_conviction_text(conviction_num) or "Watching"

    # Deep DD fields
    elevator_pitch = _sanitize_text(signal.get("dd_elevator_pitch", ""))
    why_now = _sanitize_text(signal.get("dd_why_now", ""))
    the_math = _sanitize_text(signal.get("dd_the_math", ""))
    bear_case = _sanitize_text(signal.get("dd_bear_case", ""))
    risk_to_monitor = _sanitize_text(signal.get("dd_risk_to_monitor", ""))
    dd_action = _sanitize_text(signal.get("dd_action", ""))

    # Investment gate fallback fields
    gate_math = _sanitize_text(signal.get("gate_math", ""))
    gate_bear_case = _sanitize_text(signal.get("gate_bear_case", ""))
    bullish_factors = signal.get("bullish_factors", [])
    risk_factors = signal.get("risk_factors", [])

    # Theme sub-scores (find matching theme)
    theme_data = None
    if themes:
        theme_data = next((t for t in themes if t.get("name") == theme_name), None)

    date_str = datetime.now().strftime("%B %d, %Y")

    # ── Build sections ──

    sections = []

    # 1. HEADER
    sections.append(f"""
<div style="text-align:center;padding:32px 0 24px 0;">
  <div style="font-size:48px;font-weight:800;color:{COLORS['teal']};letter-spacing:2px;">${ticker}</div>
  <div style="margin:12px 0;">{_signal_badge(decision)}</div>
  <div style="color:{COLORS['text_muted']};font-size:14px;">{date_str}</div>
</div>""")

    # 2. OVERVIEW CARD (2x2 stat grid)
    classification = ""
    if theme_verdict:
        classification = theme_verdict
    elif theme_data:
        classification = theme_data.get("classification", "")

    overview_grid = f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
  {_stat_box(f'{CURRENCY_SYMBOL}{price:.2f}' if price else 'N/A', 'Price')}
  {_stat_box(f'{theme_name}', 'Theme', COLORS['teal'])}
  {_stat_box(conviction_text, 'Conviction')}
  {_stat_box(classification or 'N/A', 'Classification')}
</div>"""
    sections.append(overview_grid)

    # 3. THE PITCH (teal highlight)
    pitch_content = elevator_pitch or "Analysis pending"
    sections.append(_section_header("The Pitch"))
    sections.append(_highlight_card(
        f'<p style="font-size:16px;line-height:1.7;color:{COLORS["teal_light"]};margin:0;">{pitch_content}</p>',
        COLORS["teal_bg"]
    ))

    # 4. WHY NOW (gold left border)
    why_now_content = why_now or "Analysis pending"
    sections.append(_section_header("Why Now"))
    sections.append(_card(
        f'<p style="color:{COLORS["text"]};line-height:1.7;margin:0;">{why_now_content}</p>',
        COLORS["gold"]
    ))

    # 5. THE MATH (stat card)
    math_content = the_math or gate_math or "Analysis pending"
    sections.append(_section_header("The Math"))
    sections.append(_card(
        f'<p style="color:{COLORS["text"]};line-height:1.7;margin:0;">{math_content}</p>',
        COLORS["teal"]
    ))

    # 6. BEAR CASE (amber left border)
    bear_content = bear_case or gate_bear_case or "Analysis pending"
    sections.append(_section_header("Bear Case"))
    sections.append(_card(
        f'<p style="color:{COLORS["text"]};line-height:1.7;margin:0;">{bear_content}</p>',
        COLORS["amber"]
    ))

    # 7. RISK TO MONITOR (red left border)
    risk_content = risk_to_monitor or "Analysis pending"
    sections.append(_section_header("Risk to Monitor"))
    sections.append(_card(
        f'<p style="color:{COLORS["text"]};line-height:1.7;margin:0;">{risk_content}</p>',
        COLORS["red_loss"]
    ))

    # 8. THEME CONTEXT (with progress bars if theme data available)
    if theme_data:
        composite = theme_data.get("composite_score", 0)
        catalyst = theme_data.get("catalyst_score", 0)
        momentum = theme_data.get("momentum_score", 0)
        crowding = theme_data.get("crowding_score", 0)
        runway = theme_data.get("runway_score", 0)
        thesis = _sanitize_text(theme_data.get("thesis_summary", ""))
        catalysts = theme_data.get("key_catalysts", [])

        bars_html = _progress_bar(composite, 10.0, "Composite Score", COLORS["teal"])
        bars_html += _progress_bar(catalyst, 10.0, "Catalyst Score", COLORS["gold"])
        bars_html += _progress_bar(momentum, 10.0, "Momentum Score", COLORS["green_gain"])
        bars_html += _progress_bar(crowding, 10.0, "Crowding Score", COLORS["violet"])
        bars_html += _progress_bar(runway, 10.0, "Runway Score", COLORS["amber"])

        theme_body = f"""
<h3 style="color:{COLORS['teal']};margin:0 0 8px 0;">{theme_name}</h3>
<div style="color:{COLORS['text_muted']};font-size:13px;margin-bottom:12px;">
  {theme_data.get('classification', '')} | {theme_data.get('theme_type', '')}
</div>
{bars_html}"""

        if thesis:
            theme_body += f'<p style="color:{COLORS["text"]};line-height:1.6;margin:12px 0 0 0;font-size:14px;">{thesis}</p>'

        if catalysts:
            bullets = "".join(
                f'<li style="color:{COLORS["text"]};margin:4px 0;">{_sanitize_text(c)}</li>'
                for c in catalysts[:5]
            )
            theme_body += f'<ul style="padding-left:20px;margin:8px 0 0 0;">{bullets}</ul>'

        sections.append(_section_header("Theme Context"))
        sections.append(_card(theme_body))

    # 9. QUALITY ASSESSMENT (bullish/risk factors)
    if bullish_factors or risk_factors:
        gate_body = ""
        if bullish_factors:
            items = "".join(
                f'<li style="color:{COLORS["green_gain"]};margin:4px 0;">{_sanitize_text(f)}</li>'
                for f in bullish_factors
            )
            gate_body += f'<div style="margin-bottom:12px;"><strong style="color:{COLORS["green_gain"]};">Bullish Factors</strong><ul style="padding-left:20px;margin:6px 0;">{items}</ul></div>'

        if risk_factors:
            items = "".join(
                f'<li style="color:{COLORS["amber"]};margin:4px 0;">{_sanitize_text(f)}</li>'
                for f in risk_factors
            )
            gate_body += f'<div><strong style="color:{COLORS["amber"]};">Risk Factors</strong><ul style="padding-left:20px;margin:6px 0;">{items}</ul></div>'

        sections.append(_section_header("Quality Assessment"))
        sections.append(_card(gate_body))

    # 10. ACTION (teal highlight)
    action_content = dd_action or "Analysis pending"
    sections.append(_section_header("Action"))
    sections.append(_highlight_card(
        f'<p style="font-size:16px;line-height:1.7;color:{COLORS["teal_light"]};margin:0;">{action_content}</p>',
        COLORS["teal_bg"]
    ))

    # 11. FOOTER
    sections.append(f"""
<div style="text-align:center;padding:32px 0 16px 0;color:{COLORS['text_muted']};font-size:13px;">
  <div style="margin-bottom:8px;">{BRANDING['tagline']}</div>
  <div>Filters 1,800 stocks to 3-5 actionable signals</div>
  <div style="margin-top:12px;">
    <a href="{BRANDING['substack_url']}" style="color:{COLORS['teal']};text-decoration:none;">
      Subscribe to Sterling Signals
    </a>
  </div>
  <div style="margin-top:16px;font-size:11px;color:{COLORS['border']};">
    This is for informational purposes only and does not constitute financial advice.
  </div>
</div>""")

    # ── Assemble full HTML ──
    body = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sterling Signals DD: ${ticker}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;margin:0;padding:24px;background:{COLORS['dark_bg']};color:{COLORS['text']};">
  <div style="max-width:680px;margin:0 auto;">
{body}
  </div>
</body>
</html>"""

    return html


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals(signals_path: Optional[Path] = None) -> Dict:
    """Load signals.json and return the full data dict."""
    if signals_path and signals_path.exists():
        with open(signals_path, "r") as f:
            return json.load(f)

    # Try current/ folder first, then root trades/
    if OUTPUT_PATHS_AVAILABLE:
        current = get_scanner_current_dir() / "signals.json"
        if current.exists():
            with open(current, "r") as f:
                return json.load(f)

    root = SIGNALS_FILE
    if root.exists():
        with open(root, "r") as f:
            return json.load(f)

    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE & OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_dd_post(html: str, ticker: str) -> Tuple[Path, Optional[Path]]:
    """Save DD post HTML to current/substack_posts/ and weekly archive.

    Returns:
        Tuple of (current_path, archive_path or None)
    """
    filename = f"dd_{ticker}.html"

    # Validate before saving
    text_only = re.sub(r'<[^>]+>', '', html)
    is_valid, violations = validate_content(text_only)
    if not is_valid:
        print(f"  WARNING: DD post for {ticker} contains banned terms: {violations}")

    if OUTPUT_PATHS_AVAILABLE:
        current_path, archive_path = save_to_substack_current_and_archive(
            html, filename, subdir="substack_posts"
        )
        return current_path, archive_path
    else:
        output_dir = get_substack_current_dir() / "substack_posts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(html)
        return output_path, None


def capture_screenshot(html_path: Path, output_path: Path) -> bool:
    """Capture PNG screenshot of the DD post via Playwright.

    Returns True on success, False if Playwright is unavailable.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            page.goto(f"file://{html_path.absolute()}")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(output_path), full_page=True)
            browser.close()
        return True
    except Exception as e:
        print(f"  WARNING: Screenshot failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate DD HTML posts for Sterling Signals buy signals"
    )
    parser.add_argument(
        "--ticker", type=str,
        help="Generate DD post for a specific ticker only"
    )
    parser.add_argument(
        "--signals", type=str,
        help="Path to signals.json (default: auto-detect)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print HTML to stdout without saving"
    )
    parser.add_argument(
        "--screenshot", action="store_true",
        help="Also generate PNG screenshots (requires Playwright)"
    )

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("  DD POST GENERATOR - Sterling Signals")
    print(f"{'=' * 60}")

    # Load signals
    signals_path = Path(args.signals) if args.signals else None
    data = load_signals(signals_path)

    if not data:
        print("\n  No signals.json found. Run the scanner first.")
        print("    python -m core.scanner --web-search")
        sys.exit(1)

    buy_signals = data.get("buy_signals", [])
    themes = data.get("themes", [])

    # Filter to PASS signals only (not CONSIDER)
    pass_signals = [
        s for s in buy_signals
        if s.get("final_decision") in ("PASS", "TRADE")
    ]

    if args.ticker:
        pass_signals = [s for s in pass_signals if s.get("symbol") == args.ticker.upper()]
        if not pass_signals:
            # Also check all buy signals (in case it's a CONSIDER)
            pass_signals = [s for s in buy_signals if s.get("symbol") == args.ticker.upper()]

    if not pass_signals:
        print(f"\n  No {'matching' if args.ticker else 'PASS'} signals found.")
        sys.exit(0)

    print(f"\n  Generating DD posts for {len(pass_signals)} signal(s)...")

    generated = []
    for signal in pass_signals:
        ticker = signal.get("symbol", "???")
        print(f"\n  [{ticker}]")

        html = generate_dd_post(signal, themes)

        if args.dry_run:
            print(html)
            generated.append(ticker)
            continue

        current_path, archive_path = save_dd_post(html, ticker)
        print(f"    Current: {current_path}")
        if archive_path:
            print(f"    Archive: {archive_path}")
        generated.append(ticker)

        # Optional screenshot
        if args.screenshot:
            png_path = CHARTS_DIR / f"dd_{ticker}.png"
            png_path.parent.mkdir(parents=True, exist_ok=True)
            if capture_screenshot(current_path, png_path):
                print(f"    Screenshot: {png_path}")
            else:
                print(f"    Screenshot: skipped (Playwright not available)")

    print(f"\n{'=' * 60}")
    print(f"  Generated {len(generated)} DD post(s): {', '.join(generated)}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
