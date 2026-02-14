#!/usr/bin/env python3
"""
SUBSTACK CONTENT GENERATOR v2
==============================

Generates 2-3 rich, LLM-powered Substack posts per week using data from the
weekly scanner, portfolio, themes, and market analysis.

Content Calendar:
  When buy signals exist (PASS > 0):
    Saturday  : Weekly Recap + Market Analysis
    Tuesday   : DD Deep Dive (top signal narrative)
    Thursday  : Theme Deep Dive (#1 PRIME theme)

  When no buy signals (PASS = 0):
    Saturday  : Weekly Market Analysis (selectivity + themes)
    Tuesday   : Theme Deep Dive (#1 PRIME theme)
    Thursday  : Portfolio Spotlight (winners + benchmarks)

Usage:
    python -m content.substack_content_generator --all        # Auto-detect + generate
    python -m content.substack_content_generator --market      # Saturday weekly recap
    python -m content.substack_content_generator --theme       # Theme deep dive
    python -m content.substack_content_generator --dd          # DD deep dive(s)
    python -m content.substack_content_generator --portfolio   # Portfolio spotlight
    python -m content.substack_content_generator --dry-run     # Preview without LLM
    python -m content.substack_content_generator --no-llm      # Data-only fallback
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─── Project imports ───────────────────────────────────────────────────────────

from config import (
    BASE_DIR,
    TRADES_DIR,
    BRANDING,
    get_conviction_text,
    can_show_entry_price,
)
from config.banned_terms import (
    INTERNAL_TERMINOLOGY_MAP,
    ALL_BANNED,
    check_banned_phrases,
)
from config.marketing_vocabulary import validate_content

try:
    from config.output_paths import (
        ensure_output_structure,
        get_current_dir,
        get_week_dir,
        get_relative_path,
        list_weekly_archives,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False

try:
    from config import MARKETING_THRESHOLDS
except ImportError:
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
    }

# ─── Reuse proven functions from other modules ────────────────────────────────

try:
    from content.newsletter_compiler import (
        markdown_to_html,
        HTML_TEMPLATE,
        get_chart_as_base64,
    )
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000
SUBSTACK_URL = BRANDING.get("substack_url", "https://sterlingsignals.substack.com")
CHARTS_DIR = TRADES_DIR / "charts"
MIN_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
BIG_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PostSpec:
    """Specification for a single Substack post."""
    post_type: str          # WEEKLY_RECAP, THEME_DEEP_DIVE, DD_DEEP_DIVE, PORTFOLIO_SPOTLIGHT
    title: str
    publish_day: str        # Saturday, Tuesday, Thursday
    filename: str
    priority: int = 1       # 1 = must generate


@dataclass
class ContentContext:
    """All available data for content generation."""
    signals: Dict = field(default_factory=dict)
    market_analysis: str = ""
    themes: List[Dict] = field(default_factory=list)
    buy_signals: List[Dict] = field(default_factory=list)
    assessed_signals: List[Dict] = field(default_factory=list)
    portfolio_stats: Dict = field(default_factory=dict)
    historical_winners: List[Dict] = field(default_factory=list)
    benchmark: str = ""
    theme_details: str = ""
    theme_history: Dict = field(default_factory=dict)
    chart_manifest: Dict = field(default_factory=dict)
    week_number: int = 0
    pass_count: int = 0
    scan_stats: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals(signals_path: Optional[Path] = None) -> Dict:
    """Load signals.json from auto-detected or specified path."""
    paths_to_try = []
    if signals_path:
        paths_to_try.append(signals_path)
    if OUTPUT_PATHS_AVAILABLE:
        paths_to_try.append(get_current_dir() / "signals.json")
    paths_to_try.append(TRADES_DIR / "signals.json")

    for p in paths_to_try:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def load_market_analysis() -> str:
    """Load market analysis markdown from current outputs."""
    paths_to_try = []
    if OUTPUT_PATHS_AVAILABLE:
        paths_to_try.append(get_current_dir() / "market_analysis.md")
    paths_to_try.append(TRADES_DIR / "current" / "market_analysis.md")

    for p in paths_to_try:
        if p.exists():
            content = p.read_text()
            # Extract content after the header if present
            marker = "## \U0001f4ca Market Context"
            if marker in content:
                content = content[content.index(marker) + len(marker):]
            return content.strip()
    return ""


def load_portfolio_winners() -> List[Dict]:
    """Load open positions with positive P&L for showcase."""
    portfolio_path = TRADES_DIR / "portfolio.csv"
    if not portfolio_path.exists():
        return []

    import csv
    winners = []
    with open(portfolio_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").upper() != "OPEN":
                continue
            try:
                entry = float(row.get("entry_price", 0))
                highest = float(row.get("highest_close", 0))
                if entry > 0 and highest > 0:
                    pnl_pct = ((highest - entry) / entry) * 100
                    if pnl_pct >= MIN_WIN_THRESHOLD:
                        winners.append({
                            "ticker": row.get("ticker", ""),
                            "entry_price": entry,
                            "highest_close": highest,
                            "pnl_pct": round(pnl_pct, 1),
                            "theme": row.get("theme", ""),
                            "entry_date": row.get("entry_date", ""),
                            "show_entry": pnl_pct >= BIG_WIN_THRESHOLD,
                        })
            except (ValueError, TypeError):
                continue

    winners.sort(key=lambda w: w["pnl_pct"], reverse=True)
    return winners


def load_equity_curve() -> Dict:
    """Load portfolio stats from equity_curve.csv."""
    curve_path = TRADES_DIR / "equity_curve.csv"
    if not curve_path.exists():
        return {}

    import csv
    rows = []
    with open(curve_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return {}

    latest = rows[-1]
    try:
        return {
            "nav": float(latest.get("nav", 0)),
            "total_return_pct": float(latest.get("total_return_pct", 0)),
            "spy_return_pct": float(latest.get("spy_return_pct", 0)),
            "alpha_pct": float(latest.get("alpha_pct", 0)),
            "qqq_return_pct": float(latest.get("qqq_return_pct", 0)),
            "alpha_vs_qqq_pct": float(latest.get("alpha_vs_qqq_pct", 0)),
            "open_count": int(float(latest.get("open_count", 0))),
            "date": latest.get("date", ""),
            "data_points": len(rows),
        }
    except (ValueError, TypeError):
        return {}


def load_historical_themes() -> Dict[str, List[Dict]]:
    """Load theme data from the last 4 weekly archives for trend analysis."""
    if not OUTPUT_PATHS_AVAILABLE:
        return {}

    try:
        archives = list_weekly_archives()
    except Exception:
        return {}

    # Take last 4 weeks (excluding current)
    recent_weeks = sorted(archives)[-5:-1] if len(archives) > 4 else sorted(archives)[:-1]
    history = {}

    for week_id in recent_weeks:
        week_dir = TRADES_DIR / "weeks" / week_id
        signals_path = week_dir / "signals.json"
        if not signals_path.exists():
            continue

        try:
            with open(signals_path) as f:
                data = json.load(f)
            for theme in data.get("themes", []):
                name = theme.get("name", "")
                if name:
                    if name not in history:
                        history[name] = []
                    history[name].append({
                        "week": week_id,
                        "score": theme.get("composite_score", 0),
                        "classification": theme.get("classification", ""),
                    })
        except (json.JSONDecodeError, KeyError):
            continue

    return history


def load_chart_manifest() -> Dict[str, str]:
    """Load chart manifest mapping tickers to file paths."""
    manifest_path = CHARTS_DIR / "chart_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def build_content_context(signals_path: Optional[Path] = None) -> ContentContext:
    """Build the full content context from all available data sources."""
    ctx = ContentContext()

    # Load signals
    ctx.signals = load_signals(signals_path)
    ctx.themes = ctx.signals.get("themes", [])
    ctx.buy_signals = [
        s for s in ctx.signals.get("buy_signals", [])
        if s.get("final_decision", "").upper() in ("PASS", "TRADE", "STRONG_BUY", "SPEC_BUY")
    ]
    ctx.assessed_signals = ctx.signals.get("assessed_signals", ctx.signals.get("all_assessed", []))
    ctx.scan_stats = ctx.signals.get("stats", {})
    ctx.pass_count = len(ctx.buy_signals)

    # Week number
    ctx.week_number = datetime.now().isocalendar()[1]

    # Market analysis
    ctx.market_analysis = load_market_analysis()

    # Portfolio
    ctx.historical_winners = load_portfolio_winners()
    ctx.portfolio_stats = load_equity_curve()

    # Benchmark comparison — try importing from newsletter_compiler
    try:
        from content.newsletter_compiler import generate_benchmark_comparison
        ctx.benchmark = generate_benchmark_comparison()
    except (ImportError, Exception):
        ctx.benchmark = ""

    # Theme details
    try:
        from content.newsletter_compiler import load_theme_details
        ctx.theme_details = load_theme_details()
    except (ImportError, Exception):
        ctx.theme_details = ""

    # Historical themes for trend analysis
    ctx.theme_history = load_historical_themes()

    # Charts
    ctx.chart_manifest = load_chart_manifest()

    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT CALENDAR DECISION
# ═══════════════════════════════════════════════════════════════════════════════

def determine_content_calendar(ctx: ContentContext) -> List[PostSpec]:
    """Determine which posts to generate based on this week's data."""
    posts = []
    week = ctx.week_number
    date_str = datetime.now().strftime("%B %d, %Y")

    # Post 1: Always — Saturday weekly recap
    if ctx.pass_count > 0:
        title = f"Week {week}: {ctx.pass_count} New GREEN Signal{'s' if ctx.pass_count > 1 else ''}"
    else:
        top_theme = ctx.themes[0]["name"] if ctx.themes else "Market Update"
        title = f"Week {week}: Why We Passed This Week"

    posts.append(PostSpec(
        post_type="WEEKLY_RECAP",
        title=title,
        publish_day="Saturday",
        filename="saturday_weekly_recap.html",
    ))

    # Post 2: Always — Theme deep dive (Tuesday)
    if ctx.themes:
        theme_name = ctx.themes[0].get("name", "Market Themes")
    else:
        theme_name = "Market Themes"

    posts.append(PostSpec(
        post_type="THEME_DEEP_DIVE",
        title=f"Theme Watch: {theme_name}",
        publish_day="Tuesday",
        filename="tuesday_theme_deep_dive.html",
    ))

    # Post 3: Conditional — Thursday
    if ctx.pass_count > 0:
        # DD deep dive for top signal
        top_signal = ctx.buy_signals[0]
        ticker = top_signal.get("symbol", "???")
        posts.append(PostSpec(
            post_type="DD_DEEP_DIVE",
            title=f"Deep Dive: ${ticker}",
            publish_day="Thursday",
            filename=f"thursday_dd_{ticker}.html",
        ))
    else:
        # Portfolio spotlight
        posts.append(PostSpec(
            post_type="PORTFOLIO_SPOTLIGHT",
            title="Portfolio Spotlight: How the System is Performing",
            publish_day="Thursday",
            filename="thursday_portfolio_spotlight.html",
        ))

    return posts


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_text(text: str) -> str:
    """Replace internal terminology with public-facing alternatives."""
    if not text:
        return text
    for internal, public in INTERNAL_TERMINOLOGY_MAP.items():
        pattern = re.compile(re.escape(internal), re.IGNORECASE)
        text = pattern.sub(public, text)
    return text


def scrub_llm_output(text: str) -> str:
    """Post-LLM scrub to remove content the LLM should not have generated.

    Even with strong system prompts, LLMs sometimes include negative P&L,
    banned phrases, or STOPPED mentions. This function strips them as a
    last line of defence before validation.
    """
    if not text:
        return text

    # Strip sentences containing negative P&L (e.g., "-12.3%")
    # Replace whole sentences that contain a negative percentage
    text = re.sub(
        r'[^.!?\n]*-\d+\.?\d*%[^.!?\n]*[.!?]?',
        '',
        text,
    )

    # Remove STOPPED mentions (whole sentences)
    text = re.sub(
        r'[^.!?\n]*\bSTOPPED\b[^.!?\n]*[.!?]?',
        '',
        text,
    )

    # Clean up any double blank lines left by removals
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def validate_post_content(text: str) -> Tuple[bool, List[str]]:
    """Validate post content for banned terms and marketing compliance."""
    issues = []

    # Check banned phrases
    violations = check_banned_phrases(text)
    if violations:
        issues.extend(violations)

    # Check for negative P&L mentions
    neg_pnl = re.findall(r'-\d+\.?\d*%', text)
    if neg_pnl:
        issues.append(f"Negative P&L found: {neg_pnl}")

    # Check for STOPPED mentions
    if re.search(r'\bSTOPPED\b', text):
        issues.append("STOPPED position mentioned")

    # Validate via marketing vocabulary
    is_valid, term_issues = validate_content(text)
    if not is_valid:
        issues.extend(term_issues)

    return (len(issues) == 0, issues)


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL ELEMENT HELPERS (HTML components injected post-LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def build_scan_funnel_html(stats: Dict) -> str:
    """Build HTML scan funnel visualization from scanner stats."""
    tickers = stats.get("tickers_loaded", 0)
    technical = stats.get("technical_signals", stats.get("buy_signal", 0))
    theme_confirmed = stats.get("theme_confirmed", 0)
    final = stats.get("final_trade", 0)

    stages = [
        ("Universe", tickers, "#6366F1"),
        ("Technical Gates", technical, "#8B5CF6"),
        ("Theme Confirmed", theme_confirmed, "#A78BFA"),
        ("GREEN Signals", final, "#22C55E"),
    ]

    html = '<div style="margin: 24px 0;">\n'
    max_val = max(tickers, 1)
    for label, value, color in stages:
        width_pct = max(int((value / max_val) * 100), 4)
        html += f'''  <div style="display: flex; align-items: center; margin: 6px 0;">
    <div style="width: 140px; font-size: 13px; color: #666; text-align: right; padding-right: 12px;">{label}</div>
    <div style="background: {color}; height: 30px; width: {width_pct}%; border-radius: 4px; display: flex; align-items: center; padding: 0 12px;">
      <span style="color: white; font-weight: 700; font-size: 13px;">{value:,}</span>
    </div>
  </div>\n'''
    html += '</div>\n'
    return html


def build_theme_scores_html(themes: List[Dict]) -> str:
    """Build HTML theme score cards with progress bars."""
    if not themes:
        return ""

    html = ""
    for theme in themes[:4]:  # Top 4 themes
        name = theme.get("name", "Unknown")
        classification = theme.get("classification", "")
        composite = theme.get("composite_score", 0)
        catalyst = theme.get("catalyst_score", 0)
        momentum = theme.get("momentum_score", 0)
        thesis = theme.get("thesis_summary", "")[:300]

        badge_color = "#22C55E" if classification == "PRIME" else "#F59E0B"

        html += f'''<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin: 16px 0;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <strong style="font-size: 16px;">{name}</strong>
    <span style="background: {badge_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">{classification}</span>
  </div>
  <div style="font-size: 28px; font-weight: 800; color: #1a1a1a;">{composite}<span style="font-size: 14px; color: #666;">/10</span></div>
  <div style="display: flex; gap: 16px; margin: 12px 0;">
    <div style="flex: 1;">
      <div style="font-size: 11px; color: #666; text-transform: uppercase;">Catalyst</div>
      <div style="background: #e5e7eb; height: 6px; border-radius: 3px; margin-top: 4px;">
        <div style="background: {badge_color}; height: 6px; border-radius: 3px; width: {min(catalyst * 10, 100)}%;"></div>
      </div>
    </div>
    <div style="flex: 1;">
      <div style="font-size: 11px; color: #666; text-transform: uppercase;">Momentum</div>
      <div style="background: #e5e7eb; height: 6px; border-radius: 3px; margin-top: 4px;">
        <div style="background: {badge_color}; height: 6px; border-radius: 3px; width: {min(momentum * 10, 100)}%;"></div>
      </div>
    </div>
  </div>
  <p style="color: #666; font-size: 14px; margin: 8px 0 0 0;">{thesis}</p>
</div>\n'''

    return html


def build_winners_table_html(winners: List[Dict]) -> str:
    """Build HTML table showcasing winning positions."""
    if not winners:
        return ""

    html = '<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">\n'
    html += '<tr style="background: #f5f5f5;"><th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Ticker</th>'
    html += '<th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Theme</th>'
    html += '<th style="padding: 10px; text-align: right; border: 1px solid #ddd;">P&L</th></tr>\n'

    for w in winners[:8]:
        ticker = w["ticker"]
        pnl = w["pnl_pct"]
        theme = w.get("theme", "")
        entry_str = ""
        if w.get("show_entry"):
            entry_str = f" (${w['entry_price']:.2f} entry)"
        html += f'<tr><td style="padding: 10px; border: 1px solid #ddd; font-weight: 700;">${ticker}{entry_str}</td>'
        html += f'<td style="padding: 10px; border: 1px solid #ddd;">{theme}</td>'
        html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: right; color: #16a34a; font-weight: 700;">+{pnl:.1f}%</td></tr>\n'

    html += '</table>\n'
    return html


def inject_visual_elements(md_content: str, ctx: ContentContext) -> str:
    """Replace visual element markers in markdown with HTML components."""
    # Scan funnel
    if "[SCAN_FUNNEL]" in md_content:
        funnel_html = build_scan_funnel_html(ctx.scan_stats)
        md_content = md_content.replace("[SCAN_FUNNEL]", funnel_html)

    # Theme scores
    if "[THEME_SCORES]" in md_content:
        scores_html = build_theme_scores_html(ctx.themes)
        md_content = md_content.replace("[THEME_SCORES]", scores_html)

    # Winners table
    if "[WINNERS_TABLE]" in md_content:
        winners_html = build_winners_table_html(ctx.historical_winners)
        md_content = md_content.replace("[WINNERS_TABLE]", winners_html)

    return md_content


# ═══════════════════════════════════════════════════════════════════════════════
# LLM PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the editor of Sterling Signals, a weekly momentum trading newsletter.
Your writing style is professional, data-driven, and confident. You use specific numbers and
percentages. You explain complex concepts clearly without talking down to the reader.

CRITICAL MARKETING RULES — FOLLOW EXACTLY:

1. SIGNAL BRANDING: Use "GREEN signal" for buy signals. NEVER use "TEAL", "PASS", "VIOLET",
   "AMBER", or "purple". Exit signals are just "exit" or "system exit".

2. BANNED TERMS (never use these): HMA, Hull Moving Average, Banker, Banker indicator,
   UC, Undercurrent, BoS, Break of Structure, RSI, MACD, KDJ, Beta >= 1.5, VWAP,
   ExD, profit lock, tiered stop, gear shift, Gatekeeper, Investment Gate, Deep DD,
   conviction score, conviction 1-10 (any number), theme scoring, 5-gate,
   20% trailing stop, tiered stop, Tier 1/2/3, TEAL, VIOLET, AMBER, Roth IRA, PDT, UK ISA.

3. APPROVED ALTERNATIVES:
   - System description: "proprietary screening system" or "5-gate screening system"
   - Entry signals: "momentum confirmed", "structural pivot confirmation"
   - Institutional signals: "institutional accumulation divergence"
   - Risk management: "systematic exit discipline", "trailing stop"
   - Conviction: "Extremely Bullish" (high), "Bullish" (medium), "Watching" (low) — NEVER numbers

4. ENTRY PRICE RULES:
   - Only show entry prices for closed winners or open positions with 25%+ gains
   - For positions under 25% gain, show P&L percentage only (no entry price)

5. WINNER-ONLY POLICY:
   - NEVER mention losing positions, negative P&L, or underwater trades
   - NEVER show a number with a minus sign followed by a percent (e.g., -5.2%)
   - If portfolio is down, focus on methodology and patience instead
   - Only showcase positions with 15%+ gains

6. FORMATTING:
   - Use markdown headers (##, ###) for sections
   - Include [CHART: TICKER] where a chart image should appear
   - Include [SCAN_FUNNEL] where the scan funnel visualization should appear
   - Include [THEME_SCORES] where theme score cards should appear
   - Include [WINNERS_TABLE] where the winners table should appear
   - Use blockquotes (>) for key insights or callouts
   - Use tables for structured data comparisons
   - Write 800-1500 words of substantive analysis prose

7. TONE: Confident but not arrogant. Data-first. Educational. The reader should learn
   something from every post, not just see signal data.

8. FOOTER: End every post with a call-to-action linking to the newsletter."""


def _format_themes_for_prompt(themes: List[Dict]) -> str:
    """Format theme data for inclusion in LLM prompts."""
    if not themes:
        return "No themes identified this week."

    lines = []
    for t in themes:
        name = t.get("name", "Unknown")
        classification = t.get("classification", "")
        score = t.get("composite_score", 0)
        thesis = t.get("thesis_summary", "")[:400]
        catalysts = t.get("key_catalysts", [])
        cat_str = "; ".join(catalysts[:3]) if catalysts else "None identified"
        lines.append(f"- **{name}** ({classification}, {score}/10): {thesis}\n  Catalysts: {cat_str}")

    return "\n".join(lines)


def _format_signals_for_prompt(signals: List[Dict]) -> str:
    """Format buy signals for inclusion in LLM prompts."""
    if not signals:
        return "[No new GREEN signals this week — the system found zero stocks that cleared all gates]"

    lines = []
    for s in signals:
        ticker = s.get("symbol", "???")
        price = s.get("price", 0)
        theme = s.get("theme", "")
        conv = s.get("dd_conviction", s.get("conviction", 0))
        conv_text = get_conviction_text(conv) or "Watching"
        pitch = s.get("dd_elevator_pitch", s.get("catalyst_summary", ""))[:300]
        lines.append(f"- **${ticker}** at ${price:.2f} | Theme: {theme} | Outlook: {conv_text}\n  {pitch}")

    return "\n".join(lines)


def _format_winners_for_prompt(winners: List[Dict]) -> str:
    """Format winners for inclusion in LLM prompts."""
    if not winners:
        return "No positions currently above the 15% highlight threshold."

    lines = []
    for w in winners[:6]:
        ticker = w["ticker"]
        pnl = w["pnl_pct"]
        theme = w.get("theme", "")
        if w.get("show_entry"):
            lines.append(f"- ${ticker}: ${w['entry_price']:.2f} entry, +{pnl:.1f}% ({theme})")
        else:
            lines.append(f"- ${ticker}: +{pnl:.1f}% ({theme})")

    return "\n".join(lines)


def _format_assessed_for_prompt(assessed: List[Dict]) -> str:
    """Format assessed-but-failed signals for 'why we passed' content."""
    if not assessed:
        return ""

    lines = []
    for s in assessed[:5]:
        ticker = s.get("symbol", "???")
        decision = s.get("final_decision", "")
        reason = s.get("dd_fatal_flaw", s.get("reasoning", ""))[:200]
        if decision.upper() in ("FAIL", "NO_GO", "NO GO"):
            lines.append(f"- ${ticker}: Did not clear our screening — {reason}")

    return "\n".join(lines) if lines else ""


def _format_equity_stats(stats: Dict) -> str:
    """Format equity curve stats for prompts."""
    if not stats:
        return "Portfolio statistics not available."

    lines = [
        f"- Portfolio Return: +{stats.get('total_return_pct', 0):.1f}%",
        f"- S&P 500 Return: {stats.get('spy_return_pct', 0):+.1f}%",
        f"- Alpha vs SPY: +{stats.get('alpha_pct', 0):.1f}%",
    ]
    if stats.get("qqq_return_pct"):
        lines.append(f"- NASDAQ Return: {stats['qqq_return_pct']:+.1f}%")
        lines.append(f"- Alpha vs NASDAQ: +{stats.get('alpha_vs_qqq_pct', 0):.1f}%")
    lines.append(f"- Open Positions: {stats.get('open_count', 0)}")
    return "\n".join(lines)


def _format_theme_history(theme_name: str, history: Dict) -> str:
    """Format theme trend data across weeks."""
    if theme_name not in history:
        return "First appearance this week — no prior history."

    entries = history[theme_name]
    scores = [e["score"] for e in entries]
    if len(scores) < 2:
        return f"Appeared in {len(scores)} prior week(s). Latest score: {scores[-1]}/10."

    trend = "rising" if scores[-1] > scores[0] else "falling" if scores[-1] < scores[0] else "stable"
    avg = sum(scores) / len(scores)
    return f"Trend over {len(scores)} weeks: {trend} (avg {avg:.1f}/10, latest {scores[-1]}/10)"


# ─── Post-specific user prompts ───────────────────────────────────────────────

def build_weekly_recap_prompt(ctx: ContentContext) -> str:
    """Build the user prompt for the Saturday weekly recap post."""
    return f"""Write the Saturday Substack post for Sterling Signals — Week {ctx.week_number}.

## MARKET CONTEXT (lightly edit, keep data intact)
{ctx.market_analysis if ctx.market_analysis else "[No market analysis available — focus on scanner results and themes]"}

## SCAN RESULTS
- Tickers scanned: {ctx.scan_stats.get('tickers_loaded', 0):,}
- Passed technical gates: {ctx.scan_stats.get('technical_signals', ctx.scan_stats.get('buy_signal', 0))}
- Theme confirmed: {ctx.scan_stats.get('theme_confirmed', 0)}
- GREEN signals: {ctx.pass_count}

Include [SCAN_FUNNEL] after describing the scan results.

## THEMES THIS WEEK
{_format_themes_for_prompt(ctx.themes)}

Include [THEME_SCORES] after the theme discussion.

## NEW SIGNALS
{_format_signals_for_prompt(ctx.buy_signals)}

## STOCKS THAT DIDN'T MAKE THE CUT
{_format_assessed_for_prompt(ctx.assessed_signals)}

## WIN HIGHLIGHTS (positions above 15%)
{_format_winners_for_prompt(ctx.historical_winners)}

Include [WINNERS_TABLE] if there are winners to showcase.

## BENCHMARK PERFORMANCE
{ctx.benchmark if ctx.benchmark else _format_equity_stats(ctx.portfolio_stats)}

---

Write a 1200-1500 word post. Structure:
1. Opening paragraph — market context summary (2-3 sentences)
2. What our scanner found this week — scan funnel + results
3. Themes driving momentum — analysis of top themes
4. {"New GREEN signals — why these stocks cleared all gates" if ctx.pass_count > 0 else "Why we passed — selectivity as a feature, not a bug"}
5. Portfolio performance — wins and benchmarks
6. Looking ahead — next week catalysts
7. Footer — subscribe CTA

For each signal with a chart, include [CHART: TICKER].
End with: **Subscribe to Sterling Signals for the full weekly analysis:** {SUBSTACK_URL}"""


def build_theme_deep_dive_prompt(ctx: ContentContext) -> str:
    """Build the user prompt for the theme deep dive post."""
    if not ctx.themes:
        return "Write a 800-word post about current market themes and sector rotation."

    theme = ctx.themes[0]
    name = theme.get("name", "Unknown")
    classification = theme.get("classification", "")
    score = theme.get("composite_score", 0)
    thesis = theme.get("thesis_summary", "")
    catalysts = theme.get("key_catalysts", [])
    theme_type = theme.get("theme_type", "TREND")

    # Stocks mapped to this theme
    theme_stocks = []
    for s in ctx.buy_signals + ctx.assessed_signals:
        if s.get("theme", "").lower() == name.lower():
            theme_stocks.append(f"${s.get('symbol', '???')}")

    # Historical trend
    trend_info = _format_theme_history(name, ctx.theme_history)

    # Other themes for comparison
    other_themes = ""
    if len(ctx.themes) > 1:
        others = [f"{t['name']} ({t.get('composite_score', 0)}/10)" for t in ctx.themes[1:3]]
        other_themes = f"Other themes this week: {', '.join(others)}"

    return f"""Write a Tuesday Substack post — a deep dive into this week's top investment theme.

## THEME: {name}
- Classification: {classification}
- Composite Score: {score}/10
- Type: {theme_type}
- Thesis: {thesis}
- Key Catalysts: {'; '.join(catalysts)}
- Stocks in this theme: {', '.join(theme_stocks) if theme_stocks else 'None passed all gates'}
- Trend: {trend_info}
- {other_themes}

## THEME SCORING BREAKDOWN (from our scanner)
{ctx.theme_details if ctx.theme_details else "Detailed sub-scores not available."}

Include [THEME_SCORES] after discussing the scoring breakdown.

---

Write an 800-1200 word educational post. Structure:
1. Opening — why this theme matters RIGHT NOW (specific catalyst or data point)
2. The investment thesis — explain the theme dynamics in accessible language
3. Scoring breakdown — what our system sees (use approved marketing language only)
4. Key catalysts — specific events, dates, and data driving this theme
5. Risks to the thesis — balanced analysis (but not bearish)
6. What we're watching — specific triggers or data points for next week
7. Footer — subscribe CTA

This should read like a sector research note from a sharp analyst, not a data dump.
End with: **Get weekly theme analysis and GREEN signals:** {SUBSTACK_URL}"""


def build_dd_deep_dive_prompt(ctx: ContentContext) -> str:
    """Build the user prompt for the DD deep dive post."""
    if not ctx.buy_signals:
        return build_portfolio_spotlight_prompt(ctx)

    signal = ctx.buy_signals[0]
    ticker = signal.get("symbol", "???")
    price = signal.get("price", 0)
    theme = signal.get("theme", "")
    conv = signal.get("dd_conviction", signal.get("conviction", 0))
    conv_text = get_conviction_text(conv) or "Watching"

    # DD fields
    pitch = signal.get("dd_elevator_pitch", signal.get("catalyst_summary", ""))
    why_now = signal.get("dd_why_now", "")
    the_math = signal.get("dd_the_math", signal.get("gate_math", ""))
    bear_case = signal.get("dd_bear_case", signal.get("gate_bear_case", ""))
    risk = signal.get("dd_risk_to_monitor", "")
    action = signal.get("dd_action", "")
    bullish = signal.get("bullish_factors", [])
    risks = signal.get("risk_factors", [])

    return f"""Write a Thursday Substack post — a narrative deep dive on our latest GREEN signal.

## SIGNAL: ${ticker}
- Price: ${price:.2f}
- Theme: {theme}
- Outlook: {conv_text}

## THE PITCH
{pitch}

## WHY NOW
{why_now}

## THE MATH (Return Potential)
{the_math}

## BEAR CASE
{bear_case}

## KEY RISK TO WATCH
{risk}

## BULLISH FACTORS
{chr(10).join('- ' + b for b in bullish[:5])}

## RISK FACTORS
{chr(10).join('- ' + r for r in risks[:5])}

## RECOMMENDED ACTION
{action}

---

Include [CHART: {ticker}] after the analysis section.

Write an 800-1200 word narrative post. Structure:
1. Opening hook — why this stock caught our attention (make it compelling)
2. The thesis — what makes this a GREEN signal (use all DD data, in your own words)
3. The math — return potential and valuation context
4. The bear case — honest assessment + why we're still bullish
5. Risk to monitor — the one thing that could derail this
6. Our view — confident summary with action guidance
7. Footer — subscribe CTA

This should read like an investment memo, not a data card. Tell the STORY of this stock.
End with: **Subscribe for weekly GREEN signals and deep dives:** {SUBSTACK_URL}"""


def build_portfolio_spotlight_prompt(ctx: ContentContext) -> str:
    """Build the user prompt for the portfolio spotlight post."""
    return f"""Write a Thursday Substack post — a portfolio performance spotlight.

## PORTFOLIO PERFORMANCE
{_format_equity_stats(ctx.portfolio_stats)}

## BENCHMARK COMPARISON
{ctx.benchmark if ctx.benchmark else "Benchmark data unavailable."}

## TOP WINNERS (positions above 15% gain)
{_format_winners_for_prompt(ctx.historical_winners)}

Include [WINNERS_TABLE] after discussing performance.

## THEMES IN PORTFOLIO
{_format_themes_for_prompt(ctx.themes[:3])}

## THIS WEEK'S SCAN
- Scanned {ctx.scan_stats.get('tickers_loaded', 0):,} stocks
- GREEN signals: {ctx.pass_count} (selectivity is the point)

---

Write an 800-1200 word post. Structure:
1. Opening — portfolio update summary (how we're performing vs benchmarks)
2. Top winners — spotlight 3-5 positions, explain the themes behind them
3. Performance vs benchmarks — SPY and NASDAQ comparison
4. System discipline — why patience and selectivity matter (no FOMO)
5. What we're watching — themes and setups for next week
6. Footer — subscribe CTA

CRITICAL: Only mention winning positions. NEVER show losses, negative P&L, or stopped positions.
Focus on the system's discipline and the power of letting winners run.
End with: **Track our portfolio performance live:** {SUBSTACK_URL}"""


# ═══════════════════════════════════════════════════════════════════════════════
# LLM GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

PROMPT_BUILDERS = {
    "WEEKLY_RECAP": build_weekly_recap_prompt,
    "THEME_DEEP_DIVE": build_theme_deep_dive_prompt,
    "DD_DEEP_DIVE": build_dd_deep_dive_prompt,
    "PORTFOLIO_SPOTLIGHT": build_portfolio_spotlight_prompt,
}


def generate_post_llm(post_spec: PostSpec, ctx: ContentContext) -> Tuple[str, float]:
    """Generate a single Substack post via Claude Sonnet 4.

    Returns: (markdown_content, cost_usd)
    """
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    prompt_builder = PROMPT_BUILDERS.get(post_spec.post_type)
    if not prompt_builder:
        raise ValueError(f"Unknown post type: {post_spec.post_type}")

    user_prompt = prompt_builder(ctx)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content[0].text

    # Estimate cost
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    return content, cost


def generate_post_fallback(post_spec: PostSpec, ctx: ContentContext) -> str:
    """Generate a data-only post without LLM (fallback mode)."""
    title = post_spec.title
    date_str = datetime.now().strftime("%B %d, %Y")

    sections = [f"# {title}\n", f"*{date_str}*\n"]

    if post_spec.post_type == "WEEKLY_RECAP":
        if ctx.market_analysis:
            sections.append(f"## Market Context\n\n{ctx.market_analysis[:600]}\n")
        sections.append("## Scanner Results\n")
        sections.append(f"This week we scanned {ctx.scan_stats.get('tickers_loaded', 0):,} stocks ")
        sections.append(f"and found {ctx.pass_count} GREEN signal{'s' if ctx.pass_count != 1 else ''}.\n")
        sections.append("\n[SCAN_FUNNEL]\n")
        if ctx.themes:
            sections.append("## Top Themes\n")
            sections.append("[THEME_SCORES]\n")
        if ctx.historical_winners:
            sections.append("## Win Highlights\n")
            sections.append("[WINNERS_TABLE]\n")

    elif post_spec.post_type == "THEME_DEEP_DIVE":
        if ctx.themes:
            t = ctx.themes[0]
            sections.append(f"## {t.get('name', 'Unknown')}\n")
            sections.append(f"**Classification:** {t.get('classification', '')}\n")
            sections.append(f"**Score:** {t.get('composite_score', 0)}/10\n")
            sections.append(f"\n{t.get('thesis_summary', '')}\n")
            catalysts = t.get("key_catalysts", [])
            if catalysts:
                sections.append("\n### Key Catalysts\n")
                for c in catalysts:
                    sections.append(f"- {c}\n")
        sections.append("\n[THEME_SCORES]\n")

    elif post_spec.post_type == "PORTFOLIO_SPOTLIGHT":
        if ctx.portfolio_stats:
            sections.append(f"## Performance\n\n{_format_equity_stats(ctx.portfolio_stats)}\n")
        if ctx.historical_winners:
            sections.append("\n## Top Winners\n\n[WINNERS_TABLE]\n")

    elif post_spec.post_type == "DD_DEEP_DIVE":
        if ctx.buy_signals:
            s = ctx.buy_signals[0]
            ticker = s.get("symbol", "???")
            sections.append(f"## ${ticker}\n")
            if s.get("dd_elevator_pitch"):
                sections.append(f"\n{s['dd_elevator_pitch']}\n")

    sections.append(f"\n---\n\n**Subscribe:** [{SUBSTACK_URL}]({SUBSTACK_URL})\n")
    sections.append("\n*This is for informational purposes only and does not constitute financial advice.*\n")

    return "".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# HTML CONVERSION & SAVE
# ═══════════════════════════════════════════════════════════════════════════════

def convert_to_html(md_content: str, chart_manifest: Dict) -> str:
    """Convert markdown + injected HTML to final HTML document."""
    if HTML_AVAILABLE:
        html_body = markdown_to_html(md_content, chart_manifest)
        return HTML_TEMPLATE.format(content=html_body, substack_url=SUBSTACK_URL)
    else:
        # Simple fallback: wrap in basic HTML
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Sterling Signals</title>
<style>body {{ font-family: sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; line-height: 1.6; }}</style>
</head><body>{md_content}</body></html>"""


def save_post(html: str, filename: str) -> Tuple[Optional[Path], Optional[Path]]:
    """Save post to current/substack_posts/ and weekly archive."""
    current_path = None
    archive_path = None

    if OUTPUT_PATHS_AVAILABLE:
        current_dir, week_dir = ensure_output_structure()

        current_posts = current_dir / "substack_posts"
        current_posts.mkdir(parents=True, exist_ok=True)
        current_path = current_posts / filename
        current_path.write_text(html)

        archive_posts = week_dir / "substack_posts"
        archive_posts.mkdir(parents=True, exist_ok=True)
        archive_path = archive_posts / filename
        archive_path.write_text(html)
    else:
        # Fallback: write to trades/current/substack_posts/
        posts_dir = TRADES_DIR / "current" / "substack_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        current_path = posts_dir / filename
        current_path.write_text(html)

    return current_path, archive_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all_posts(
    ctx: ContentContext,
    post_types: Optional[List[str]] = None,
    dry_run: bool = False,
    no_llm: bool = False,
) -> List[Dict]:
    """Generate all Substack posts for the week.

    Args:
        ctx: Content context with all loaded data.
        post_types: Specific post types to generate, or None for auto-detect.
        dry_run: If True, show what would be generated without LLM calls.
        no_llm: If True, generate data-only posts without LLM.

    Returns:
        List of dicts with generation results.
    """
    # Determine content calendar
    calendar = determine_content_calendar(ctx)

    # Filter if specific types requested
    if post_types:
        calendar = [p for p in calendar if p.post_type in post_types]

    if not calendar:
        print("  \u2139\ufe0f  No posts to generate.")
        return []

    print(f"\n  \U0001f4c5 Content Calendar (Week {ctx.week_number}):")
    print(f"     PASS signals: {ctx.pass_count}")
    for p in calendar:
        print(f"     {p.publish_day:10s} | {p.post_type:25s} | {p.title}")

    if dry_run:
        print("\n  \U0001f50d DRY RUN — no LLM calls or files written.")
        return [{"post_type": p.post_type, "title": p.title, "status": "dry_run"} for p in calendar]

    results = []
    total_cost = 0.0

    for post_spec in calendar:
        print(f"\n  \u270d\ufe0f  Generating: {post_spec.title}")

        # Generate content
        try:
            if no_llm or not os.environ.get("ANTHROPIC_API_KEY"):
                md_content = generate_post_fallback(post_spec, ctx)
                cost = 0.0
                print(f"     Mode: data-only (no LLM)")
            else:
                md_content, cost = generate_post_llm(post_spec, ctx)
                total_cost += cost
                print(f"     Mode: LLM (cost: ${cost:.3f})")
        except Exception as e:
            print(f"     \u26a0\ufe0f  LLM failed: {e}")
            print(f"     Falling back to data-only mode...")
            md_content = generate_post_fallback(post_spec, ctx)
            cost = 0.0

        # Sanitize internal terminology
        md_content = sanitize_text(md_content)

        # Scrub LLM output — strip negative P&L, STOPPED mentions
        md_content = scrub_llm_output(md_content)

        # Inject visual HTML elements
        md_content = inject_visual_elements(md_content, ctx)

        # Validate
        is_valid, issues = validate_post_content(md_content)
        if not is_valid:
            print(f"     \u26a0\ufe0f  Validation warnings: {issues[:3]}")

        # Convert to HTML
        html = convert_to_html(md_content, ctx.chart_manifest)

        # Save
        current_path, archive_path = save_post(html, post_spec.filename)

        if current_path:
            rel = get_relative_path(current_path) if OUTPUT_PATHS_AVAILABLE else str(current_path)
            print(f"     \u2705 Saved: {rel}")

        results.append({
            "post_type": post_spec.post_type,
            "title": post_spec.title,
            "filename": post_spec.filename,
            "publish_day": post_spec.publish_day,
            "cost": cost,
            "valid": is_valid,
            "issues": issues if not is_valid else [],
            "current_path": str(current_path) if current_path else None,
            "archive_path": str(archive_path) if archive_path else None,
            "status": "generated",
        })

    if total_cost > 0:
        print(f"\n  \U0001f4b0 Total LLM cost: ${total_cost:.3f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Substack posts (2-3/week, LLM-powered)"
    )

    # Post type selection
    parser.add_argument("--all", action="store_true",
        help="Auto-detect and generate all appropriate posts (default)")
    parser.add_argument("--market", action="store_true",
        help="Generate Saturday weekly recap post")
    parser.add_argument("--theme", action="store_true",
        help="Generate theme deep dive post")
    parser.add_argument("--dd", action="store_true",
        help="Generate DD deep dive post(s)")
    parser.add_argument("--portfolio", action="store_true",
        help="Generate portfolio spotlight post")

    # Backward compatibility aliases
    parser.add_argument("--monday", dest="market", action="store_true",
        help=argparse.SUPPRESS)
    parser.add_argument("--saturday", dest="market", action="store_true",
        help=argparse.SUPPRESS)
    parser.add_argument("--thursday", dest="theme", action="store_true",
        help=argparse.SUPPRESS)
    parser.add_argument("--sunday", dest="dd", action="store_true",
        help=argparse.SUPPRESS)

    # Options
    parser.add_argument("--dry-run", action="store_true",
        help="Show what would be generated without LLM calls")
    parser.add_argument("--no-llm", action="store_true",
        help="Generate data-only posts without LLM")
    parser.add_argument("--signals", type=str, default=None,
        help="Path to signals.json (auto-detected by default)")

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  SUBSTACK CONTENT GENERATOR v2")
    print(f"{'=' * 60}")

    # Determine which post types to generate
    post_types = None
    if args.market or args.theme or args.dd or args.portfolio:
        post_types = []
        if args.market:
            post_types.append("WEEKLY_RECAP")
        if args.theme:
            post_types.append("THEME_DEEP_DIVE")
        if args.dd:
            post_types.append("DD_DEEP_DIVE")
        if args.portfolio:
            post_types.append("PORTFOLIO_SPOTLIGHT")

    # Build context
    signals_path = Path(args.signals) if args.signals else None
    print(f"\n  Loading data sources...")
    ctx = build_content_context(signals_path)

    print(f"    Signals: {ctx.pass_count} GREEN, {len(ctx.themes)} themes")
    print(f"    Winners: {len(ctx.historical_winners)} positions above {MIN_WIN_THRESHOLD}%")
    print(f"    Market analysis: {'available' if ctx.market_analysis else 'not available'}")
    print(f"    Equity curve: {'available' if ctx.portfolio_stats else 'not available'}")

    # Generate
    results = generate_all_posts(
        ctx,
        post_types=post_types,
        dry_run=args.dry_run,
        no_llm=args.no_llm,
    )

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  GENERATION COMPLETE")
    print(f"{'=' * 60}")

    generated = [r for r in results if r["status"] == "generated"]
    if generated:
        print(f"\n  Generated {len(generated)} post(s):")
        for r in generated:
            status = "\u2705" if r["valid"] else "\u26a0\ufe0f"
            print(f"    {status} {r['publish_day']:10s} | {r['title']}")
            if r.get("current_path"):
                print(f"       \U0001f4c4 {r['current_path']}")
    else:
        print(f"\n  No posts generated.")

    print(f"\n  \U0001f4cb Publishing Calendar:")
    for r in results:
        print(f"     {r['publish_day']:10s} \u2192 {r['title']}")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    main()
