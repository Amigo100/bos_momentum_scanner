#!/usr/bin/env python3
"""
STERLING SIGNALS — WEEKLY CONTENT PRODUCTION GUIDE GENERATOR
==============================================================

Generates a weekly context document containing:
  1. System context (who we are, marketing rules, HTML templates)
  2. This week's data (scanner, themes, portfolio, equity)
  3. Weekly content schedule (4 categories across Sun-Sat)
  4. Reference to prompt handbook v5 for on-demand generation

The guide is designed to be attached to a Claude.ai chat (Opus 4.6 +
extended thinking) for on-demand, high-quality content generation.

The prompts themselves live in docs/content_prompt_handbook_v5.md — this
guide provides the DATA and SCHEDULE; the handbook provides the PROMPTS.

Output:
    substack/output/current/content_production_guide.md
    substack/output/current/content_schedule.json          (dashboard sidecar)
    substack/output/archive/{week}/content_production_guide.md
    substack/output/archive/{week}/content_schedule.json

Usage:
    python -m substack.content_production_guide           # Generate full guide
    python -m substack.content_production_guide --dry-run # Preview without saving

No LLM calls. Cost: $0.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─── Project imports ──────────────────────────────────────────────────────────

from config import BASE_DIR, PORTFOLIO_FILE, BRANDING, get_conviction_text

from config.banned_terms import CRITICAL_BANNED, BANNED_PHRASES, INTERNAL_TERMINOLOGY_MAP

try:
    from config.output_paths import (
        get_substack_current_dir,
        get_substack_archive_dir,
        ensure_output_structure,
        SCANNER_OUTPUT,
        SUBSTACK_OUTPUT,
        CLAUDE_CONTENT_DIR,
        list_weekly_archives,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False

# Reuse data loading from content generator
from substack.content_generator import (
    build_content_context,
    ContentContext,
    PostSpec,
    TEMPLATE_MAP,
    load_portfolio_winners,
    load_historical_themes,
    _format_themes_for_prompt,
    _format_signals_for_prompt,
    _format_winners_for_prompt,
    _format_assessed_for_prompt,
    _format_equity_stats,
    _format_theme_history,
)

# We no longer use the old template-based notes schedule — notes are generated
# on-demand each day using the Daily Notes prompt from the handbook

SUBSTACK_URL = BRANDING.get("substack_url", "https://sterlingsignals.substack.com")


# =============================================================================
# THE 4 POST CATEGORIES
# =============================================================================

CATEGORY_TICKER_DIVE = "TICKER_DEEP_DIVE"
CATEGORY_EDUCATIONAL = "EDUCATIONAL"
CATEGORY_THEME_ROTATION = "THEME_ROTATION"
CATEGORY_PERFORMANCE_REVIEW = "PERFORMANCE_REVIEW"

CATEGORY_THEMES = {
    CATEGORY_TICKER_DIVE: "editorial",
    CATEGORY_EDUCATIONAL: "editorial",
    CATEGORY_THEME_ROTATION: "dashboard",
    CATEGORY_PERFORMANCE_REVIEW: "dashboard",
}

CATEGORY_DESCRIPTIONS = {
    CATEGORY_TICKER_DIVE: "Ticker Deep Dive & 12-Month Price Targets",
    CATEGORY_EDUCATIONAL: "Educational — Strategy/Study for Growth Investors",
    CATEGORY_THEME_ROTATION: "Market Rotations & Growth Themes",
    CATEGORY_PERFORMANCE_REVIEW: "Performance Review (Weekly Newsletter)",
}

# Days we schedule posts (Sunday = newsletter, Mon-Fri = rotating, Saturday = notes only)
SCHEDULE_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

# Note type rotation matrix — ensures variety across the week
NOTE_TYPE_MATRIX = {
    "Sunday":    ["Community & Connection", "Journey & Milestones", "Week Preview"],
    "Monday":    ["Market Macro", "Winner Highlight", "Ticker News"],
    "Tuesday":   ["Geopolitics/Macro", "Theme Spotlight", "Community"],
    "Wednesday": ["Teaching & Wisdom", "Portfolio Insight", "Community"],
    "Thursday":  ["Market Midweek", "System Insight", "Ticker News"],
    "Friday":    ["Week Reflection", "Winner Recap", "Engagement"],
    "Saturday":  ["Journey", "Teaching", "Community"],
}

# Handbook prompt name for each category
CATEGORY_HANDBOOK_PROMPTS = {
    CATEGORY_TICKER_DIVE: "Category 1 — Ticker Deep Dive",
    CATEGORY_EDUCATIONAL: "Category 2 — Educational",
    CATEGORY_THEME_ROTATION: "Category 3 — Theme Rotation",
    CATEGORY_PERFORMANCE_REVIEW: "Category 4 — Performance Review (Sunday Newsletter)",
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_full_portfolio() -> List[Dict]:
    """Load ALL open positions with full metrics from PortfolioManager."""
    from portfolio.manager import PortfolioManager

    portfolio_path = PORTFOLIO_FILE
    if not portfolio_path.exists():
        return []

    pm = PortfolioManager()
    try:
        pm.update_prices()
    except Exception as e:
        print(f"  Warning: Could not fetch live prices: {e}")
        # Proceed with stale data — metrics still calculated from highest_close

    positions = []
    for t in pm.get_open_positions():
        positions.append({
            "ticker": t.ticker,
            "entry_date": t.entry_date,
            "entry_price": round(t.entry_price, 2),
            "current_price": round(t.current_price, 2) if t.current_price > 0 else round(t.highest_close, 2),
            "highest_close": round(t.highest_close, 2),
            "pnl_pct": round(t.pnl_pct, 1),
            "theme": t.theme,
            "tier": t.tier,
            "conviction": t.conviction,
            "days_held": t.days_held,
            "stop_level": round(t.stop_level, 2),
            "distance_to_stop_pct": round(t.distance_to_stop_pct, 1),
            "stop_alert": t.stop_alert,
            "signal_type": t.signal_type,
        })

    return sorted(positions, key=lambda x: x["pnl_pct"], reverse=True)


# =============================================================================
# WEEKLY SCHEDULE BUILDER (4 Categories)
# =============================================================================

def build_weekly_schedule(
    ctx: ContentContext,
    portfolio: List[Dict],
) -> List[Dict]:
    """
    Build the weekly content schedule using 4 categories.

    Logic:
      - Sunday: always PERFORMANCE_REVIEW
      - Mon-Fri: rotate through TICKER_DEEP_DIVE, EDUCATIONAL, THEME_ROTATION
        - New GREEN signals → schedule a Ticker Deep Dive (name the ticker)
        - Active themes → schedule a Theme Rotation piece (name the theme)
        - Remaining days → Educational (prompt finds topic via web search)
        - No consecutive same-category days

    Returns list of dicts: [{day, category, topic, theme_style, notes}]
    """
    schedule = []

    # ── Sunday: always Performance Review ────────────────────────────────────
    schedule.append({
        "day": "Sunday",
        "category": CATEGORY_PERFORMANCE_REVIEW,
        "topic": f"Week {ctx.week_number} Performance Review & Newsletter",
        "theme_style": "Dashboard (dark)",
    })

    # ── Build pool of topic ideas for Mon-Fri ────────────────────────────────
    ticker_dive_topics = []
    theme_rotation_topics = []

    # New GREEN signals → ticker dives
    for signal in ctx.buy_signals:
        ticker = signal.get("symbol", "???")
        theme = signal.get("theme", "")
        price = signal.get("price", 0)
        ticker_dive_topics.append({
            "ticker": ticker,
            "reason": f"New GREEN signal — ${ticker} at ${price:.2f} ({theme})",
        })

    # Top portfolio performers → ticker dives
    top_performers = [p for p in portfolio if p["pnl_pct"] >= 15.0]
    for w in top_performers[:3]:
        # Don't duplicate if already in signals
        if not any(t["ticker"] == w["ticker"] for t in ticker_dive_topics):
            theme_str = w['theme'] if w['theme'] else "Growth"
            ticker_dive_topics.append({
                "ticker": w["ticker"],
                "reason": f"Portfolio winner — ${w['ticker']} +{w['pnl_pct']:.1f}% ({theme_str})",
            })

    # Active themes → rotation pieces
    for theme in ctx.themes:
        name = theme.get("name", "")
        score = theme.get("composite_score", 0)
        classification = theme.get("classification", "")
        if classification in ("PRIME", "INVESTABLE") or score >= 6.0:
            theme_rotation_topics.append({
                "theme_name": name,
                "reason": f"{name} — {classification} ({score}/10)",
            })

    # ── Assign categories to Mon-Fri ─────────────────────────────────────────
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    ticker_idx = 0
    theme_idx = 0
    prev_category = None
    assigned_categories = []

    for day in weekdays:
        # Decision logic: pick category that isn't the same as yesterday
        candidates = []

        # Ticker dives available?
        if ticker_idx < len(ticker_dive_topics):
            candidates.append(CATEGORY_TICKER_DIVE)

        # Theme rotations available?
        if theme_idx < len(theme_rotation_topics):
            candidates.append(CATEGORY_THEME_ROTATION)

        # Educational always available
        candidates.append(CATEGORY_EDUCATIONAL)

        # Avoid consecutive same category
        if prev_category and prev_category in candidates and len(candidates) > 1:
            candidates.remove(prev_category)

        # Priority: ticker dive > theme rotation > educational
        if CATEGORY_TICKER_DIVE in candidates:
            chosen = CATEGORY_TICKER_DIVE
        elif CATEGORY_THEME_ROTATION in candidates:
            chosen = CATEGORY_THEME_ROTATION
        else:
            chosen = CATEGORY_EDUCATIONAL

        assigned_categories.append(chosen)

        # Build topic string
        if chosen == CATEGORY_TICKER_DIVE:
            t = ticker_dive_topics[ticker_idx]
            topic = t["reason"]
            ticker_idx += 1
        elif chosen == CATEGORY_THEME_ROTATION:
            t = theme_rotation_topics[theme_idx]
            topic = t["reason"]
            theme_idx += 1
        else:
            topic = "Topic identified via web search in Claude.ai (use Educational prompt from handbook)"

        theme_style = "Editorial (light)" if CATEGORY_THEMES[chosen] == "editorial" else "Dashboard (dark)"

        schedule.append({
            "day": day,
            "category": chosen,
            "topic": topic,
            "theme_style": theme_style,
        })

        prev_category = chosen

    # ── Ensure at least 1 Educational day per week ────────────────────────
    # If we filled all 5 weekdays without an Educational, swap the middle day
    if CATEGORY_EDUCATIONAL not in assigned_categories:
        # Pick the middle day (Wednesday = index 3 in schedule, since 0=Sunday)
        swap_idx = 3  # Wednesday in schedule list (Sun=0, Mon=1, Tue=2, Wed=3)
        schedule[swap_idx]["category"] = CATEGORY_EDUCATIONAL
        schedule[swap_idx]["topic"] = "Topic identified via web search in Claude.ai (use Educational prompt from handbook)"
        schedule[swap_idx]["theme_style"] = "Editorial (light)"

    # ── Saturday: notes only (no post) ──────────────────────────────────
    schedule.append({
        "day": "Saturday",
        "category": "NOTES_ONLY",
        "topic": "No post — notes only (Journey, Teaching, Community)",
        "theme_style": "N/A",
    })

    # ── Add note types and handbook prompt to each entry ────────────────
    for entry in schedule:
        day = entry["day"]
        cat = entry["category"]
        entry["note_types"] = NOTE_TYPE_MATRIX.get(day, [])
        entry["handbook_prompt"] = CATEGORY_HANDBOOK_PROMPTS.get(cat, "Daily Notes Prompt only")

    return schedule


# =============================================================================
# SECTION 1: SYSTEM CONTEXT
# =============================================================================

def generate_system_context() -> str:
    """Generate the static system context section."""

    # Build condensed banned terms list
    banned_summary = []
    banned_summary.append("Internal indicators: HMA, Banker, UC, Undercurrent, BoS, RSI, MACD, KDJ, ExD, VWAP, Beta >= 1.5")
    banned_summary.append("System terms: Gatekeeper, Investment Gate, Deep DD, 5-gate, Tier 1/2/3, conviction scores (numeric), price cap, gear shift, profit lock, tiered stop")
    banned_summary.append("Old signal branding: TEAL, VIOLET, AMBER, PASS signal, STRONG BUY, SPEC BUY, NO GO")
    banned_summary.append("UK audience: UK ISA, GMT, BST, UK Time, GBP/USD")
    banned_summary.append("US retirement: Roth IRA, PDT, 401k")
    banned_summary.append("Leaked internal: Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria")

    # Build approved alternatives
    approved = [
        ("System description", '"proprietary screening system", "our screening system"'),
        ("Entry signals", '"momentum confirmed", "structural pivot confirmation"'),
        ("Institutional signals", '"institutional accumulation divergence"'),
        ("Exit/Risk", '"systematic exit discipline", "trailing stop"'),
        ("Signal branding", '"GREEN signal" for buys, "system exit" for sells'),
        ("Conviction", '"Extremely Bullish" (high), "Bullish" (medium), "Watching" (low) — NEVER numbers'),
    ]

    return f"""# Sterling Signals — Weekly Content Production Guide

> **Attach this entire document to your Claude.ai chat (Opus 4.6 + extended thinking).**
> Then copy the relevant prompt from `docs/content_prompt_handbook_v5.md` to generate your post and notes.

---

## 1. SYSTEM CONTEXT

### Who We Are
Sterling Signals is a weekly momentum trading newsletter on Substack. We are physicians who built a systematic momentum scanner — because the same evidence-based rigor that saves lives in medicine can generate alpha in markets. We diagnose momentum the way we once diagnosed patients: systematic screening, pattern recognition, ruling out false positives, and never letting emotion override data.

### Our Niche
- **Small caps** (price < $25) — finding the next multibaggers before Wall Street
- **Growth stocks** — revenue acceleration, margin expansion, compound returns
- **Momentum** — riding structural trends, not chasing tips
- **Sector rotation** — following institutional capital flows between themes
- **High-conviction themes** — AI infrastructure, defense, energy transition, healthcare innovation

### Our System (Public Description)
Proprietary multi-stage screening system that filters ~1,800 stocks through:
1. Technical screening — momentum confirmation, structural trend analysis
2. Sector flow analysis — identifying which themes are attracting institutional capital
3. Forensic screening — due diligence audit to filter out red flags
4. Final selection — 0-3 actionable GREEN signals per week

We reject 99%+ of what we screen. That selectivity IS the edge.

### Our Voice
- Confident, data-driven, educational
- Medical-investor analogies: "Like a good clinician, we diagnose before we prescribe"
- "We triage setups, diagnose trends, and let our system prescribe entries and exits"
- Process over prediction, probabilities not certainties
- Direct and specific — every claim backed by a number

### Marketing Rules (CRITICAL — FOLLOW EXACTLY)

**Signal Branding:**
- Use "GREEN signal" for buy signals
- NEVER use: TEAL, PASS, VIOLET, AMBER, purple

**BANNED Terms (NEVER use any of these):**
{chr(10).join(f"- {b}" for b in banned_summary)}

**Approved Alternatives:**
{chr(10).join(f"- {name}: {alt}" for name, alt in approved)}

**Entry Price Display Rules:**
- Only show entry prices for closed winners or open positions with **25%+ gains**
- Only showcase/highlight positions with **15%+ gains**
- For positions under 25% gain: show P&L percentage only, no entry price

**Winners-Only Policy:**
- NEVER mention losing positions, negative P&L, or underwater trades
- NEVER show a number with a minus sign followed by a percent (e.g., -5.2%)
- If portfolio is down overall, focus on methodology, patience, and selectivity
- Only spotlight positions with 15%+ gains

**Banned Phrases (avoid vague/generic content):**
- "theme keeps delivering", "system keeps working", "trust the process"
- "some interesting setups", "a few tickers", "interesting developments"
- "stay tuned", "more to come", "keep an eye on", "picks and shovels"
- NEVER use "loser", "still bleeding", "dragging down"

**Footer:**
End every post with a call-to-action: **Subscribe to Sterling Signals:** {SUBSTACK_URL}
End every note with: "Not financial advice. Informational only."

### HTML Output Format

When generating Substack posts, produce **complete self-contained HTML documents** with all styles in a `<style>` block. Substack strips external CSS, so everything must be embedded. Max container width: **680px**. System fonts only (no Google Fonts).

**Two themes available:**

**EDITORIAL THEME** (for ticker deep dives, educational posts):
- Serif headings (Georgia, Times New Roman), sans-serif body
- Light background (#fafaf8), warm neutral palette
- Components: masthead, price target banner (bear/base/bull), stat rows, callout boxes, financial tables, catalyst lists, risk blocks

**DASHBOARD THEME** (for market rotations, performance review):
- Sans-serif throughout (system fonts)
- Dark background (#111827), teal accents (#2DD4BF)
- Components: gradient hero section, stat grids, theme cards with progress bars, rotation bars, funnel steps, pullquotes, winners tables, cards, two-column layouts

**Key Color Values:**
- Dashboard: bg=#111827, card=#1F2937, teal=#2DD4BF, green=#22C55E, red=#EF4444, text=#F9FAFB
- Editorial: bg=#fafaf8, container=#fff, positive=#2e5e3e, negative=#a04030, text=#1a1a1a
"""


# =============================================================================
# SECTION 2: THIS WEEK'S DATA
# =============================================================================

def generate_weekly_data(ctx: ContentContext, portfolio: List[Dict]) -> str:
    """Generate the data section with scanner, themes, portfolio, equity."""
    week = ctx.week_number
    now = datetime.now()

    # Scanner stats
    stats = ctx.scan_stats
    tickers = stats.get("tickers_loaded", 0)
    technical = stats.get("technical_signals", stats.get("buy_signal", 0))
    theme_confirmed = stats.get("theme_confirmed", 0)
    green_signals = ctx.pass_count

    # Portfolio stats
    total = len(portfolio)
    avg_pnl = sum(p["pnl_pct"] for p in portfolio) / max(total, 1) if portfolio else 0
    avg_days = sum(p.get("days_held", 0) for p in portfolio) / max(total, 1) if portfolio else 0
    profit_locked = [p for p in portfolio if p.get("stop_level", 0) > 0]
    near_stop = [p for p in portfolio if p.get("stop_alert", False)]
    big_winners = [p for p in portfolio if p["pnl_pct"] >= 25.0]

    output = f"""
---

## 2. THIS WEEK'S DATA (Week {week}, generated {now.strftime('%B %d, %Y')})

### Scanner Results
- Tickers scanned: {tickers:,}
- Passed technical gates: {technical}
- Theme confirmed: {theme_confirmed}
- **GREEN signals: {green_signals}**
- Rejection rate: {((1 - green_signals / max(tickers, 1)) * 100):.1f}%

### Top Themes
{_format_themes_for_prompt(ctx.themes)}

### New Signals
{_format_signals_for_prompt(ctx.buy_signals)}

### Stocks That Didn't Make the Cut
{_format_assessed_for_prompt(ctx.assessed_signals) or "No assessed signals available."}

### Portfolio Overview ({total} open positions)
"""
    if portfolio:
        output += "| Ticker | Current | Entry | P&L | Days Held | Theme | Stop Level | Stop Dist | Alert |\n"
        output += "|--------|---------|-------|-----|-----------|-------|------------|-----------|-------|\n"
        for p in portfolio:
            current = f"${p.get('current_price', 0):.2f}"
            entry = f"${p['entry_price']:.2f}"
            pnl = f"{p['pnl_pct']:+.1f}%"
            days = str(p.get("days_held", 0))
            stop = f"${p['stop_level']:.2f}" if p.get("stop_level", 0) > 0 else "ExD only"
            stop_dist = f"{p['distance_to_stop_pct']:.1f}%" if p.get("stop_level", 0) > 0 else "—"
            alert = "ALERT" if p.get("stop_alert") else ""
            output += f"| ${p['ticker']} | {current} | {entry} | {pnl} | {days} | {p['theme']} | {stop} | {stop_dist} | {alert} |\n"

        output += f"\n**Position Detail** (for newsletter narrative):\n"
        for p in portfolio:
            current = p.get("current_price", 0) or p.get("highest_close", 0)
            ticker = p["ticker"]
            pnl = p["pnl_pct"]
            days = p.get("days_held", 0)
            theme = p["theme"]
            if pnl >= 0:
                if p.get("stop_level", 0) > 0:
                    narrative = f"Stop at ${p['stop_level']:.2f} ({p['distance_to_stop_pct']:.1f}% cushion). System working — letting winners run."
                else:
                    narrative = "Below profit lock threshold — ExD exit only. Building position."
            else:
                narrative = "Down but managing risk — disciplined exits in place."

            output += f"- ${ticker}: Entry ${p['entry_price']:.2f}, now ${current:.2f} ({pnl:+.1f}%), held {days} days. {theme}.\n"
            output += f"  {narrative}\n"

        output += f"\n**Summary:**\n"
        output += f"- Total open: {total} | Average P&L: {avg_pnl:+.1f}% | Average hold: {avg_days:.0f} days\n"
        output += f"- Positions with profit lock: {len(profit_locked)} | Near-stop alerts (<5%): {len(near_stop)}\n"
        output += f"- Big winners (25%+): {len(big_winners)} positions\n"
    else:
        output += "No open positions.\n"

    # Showcase-ready winners
    output += "\n### Showcase-Ready Winners (for use in posts)\n"
    output += _format_winners_for_prompt(ctx.historical_winners) + "\n"

    # Equity curve
    output += "\n### Portfolio Performance\n"
    output += _format_equity_stats(ctx.portfolio_stats) + "\n"

    # Benchmark
    if ctx.benchmark:
        output += f"\n### Benchmark Comparison\n{ctx.benchmark}\n"

    # Market analysis
    if ctx.market_analysis:
        output += f"\n### Market Analysis (from Friday scanner)\n{ctx.market_analysis[:2000]}\n"

    return output


# =============================================================================
# SECTION 2B: CONTENT HISTORY (for continuity)
# =============================================================================

def generate_content_history() -> str:
    """Generate content history from archives + Claude content + theme persistence."""
    if not OUTPUT_PATHS_AVAILABLE:
        return "\n---\n\n### Content History\nArchive not available.\n"

    output = "\n---\n\n### Content History (Last 4 Weeks)\n\n"

    # Scan substack archives for published content
    try:
        substack_archives = list_weekly_archives("substack")
    except Exception:
        substack_archives = []

    recent_weeks = sorted(substack_archives)[-4:] if substack_archives else []

    for week_id in recent_weeks:
        week_dir = SUBSTACK_OUTPUT / "archive" / week_id
        if not week_dir.exists():
            continue

        output += f"**{week_id}**:\n"

        # Check for newsletter
        newsletter = week_dir / "newsletter.html"
        if newsletter.exists():
            # Try to extract title from HTML
            try:
                content = newsletter.read_text()[:500]
                import re
                title_match = re.search(r'<title>([^<]+)</title>', content)
                if not title_match:
                    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
                title = title_match.group(1).strip() if title_match else "Newsletter"
                output += f"- Newsletter: \"{title}\"\n"
            except Exception:
                output += f"- Newsletter: published\n"
        else:
            output += "- Newsletter: not found\n"

        # Check for posts
        posts_dir = week_dir / "substack_posts"
        if posts_dir.exists():
            posts = sorted(posts_dir.glob("*.html"))
            if posts:
                post_names = [p.stem for p in posts]
                output += f"- Posts: {', '.join(post_names)}\n"

        # Check for notes
        notes_dir = week_dir / "substack_notes"
        if notes_dir.exists():
            notes = sorted(list(notes_dir.glob("*.html")) + list(notes_dir.glob("*.md")))
            if notes:
                output += f"- Notes: {len(notes)} published\n"

        # Check scanner archive for themes that week
        scanner_signals = SCANNER_OUTPUT / "archive" / week_id / "signals.json"
        if scanner_signals.exists():
            try:
                with open(scanner_signals) as f:
                    data = json.load(f)
                themes = data.get("themes", [])
                theme_strs = []
                for t in themes:
                    name = t.get("name", "")
                    classification = t.get("classification", "")
                    if name and classification in ("PRIME", "INVESTABLE"):
                        theme_strs.append(f"{name} ({classification})")
                if theme_strs:
                    output += f"- Themes: {', '.join(theme_strs)}\n"
            except Exception:
                pass

        output += "\n"

    # Claude.ai-produced content
    if CLAUDE_CONTENT_DIR.exists():
        claude_files = sorted(CLAUDE_CONTENT_DIR.glob("*.html"))
        if claude_files:
            output += "**Claude.ai Content Archive:**\n"
            for f in claude_files[-10:]:  # Last 10 files
                output += f"- {f.name}\n"
            output += "\n"

    # Theme persistence table (4-week trend)
    theme_history = load_historical_themes()
    if theme_history:
        output += "### Theme Persistence (4-week trend)\n\n"
        output += "| Theme | " + " | ".join(recent_weeks[-4:]) + " | Trend |\n"
        output += "|-------|" + "|".join(["---"] * min(len(recent_weeks), 4)) + "|-------|\n"

        for theme_name, entries in sorted(theme_history.items()):
            weeks_map = {e["week"]: e.get("classification", "") for e in entries}
            row = f"| {theme_name} "
            for wk in recent_weeks[-4:]:
                cls = weeks_map.get(wk, "—")
                row += f"| {cls} "
            # Determine trend
            scores = [e.get("score", 0) for e in entries]
            if len(scores) >= 2:
                if scores[-1] > scores[0]:
                    trend = "Building"
                elif scores[-1] < scores[0]:
                    trend = "Fading"
                else:
                    trend = "Stable"
            else:
                trend = "New"
            row += f"| {trend} |\n"
            output += row

        output += "\n"

    return output


# =============================================================================
# SECTION 3: WEEKLY CONTENT SCHEDULE
# =============================================================================

def generate_weekly_schedule(schedule: List[Dict]) -> str:
    """Generate the weekly content schedule — days, categories, topics, notes."""

    output = """
---

## 3. WEEKLY CONTENT SCHEDULE

> **How to use:** Each day, copy the prompt for today's category from
> `docs/content_prompt_handbook_v5.md`. The handbook has 4 category prompts
> (Ticker Deep Dive, Educational, Theme Rotation, Performance Review) plus
> 1 universal Daily Notes Prompt. No placeholders to fill — the prompts
> read this context document automatically.

| Day | Category | Topic | Theme |
|-----|----------|-------|-------|
"""

    for entry in schedule:
        day = entry["day"]
        cat = entry["category"]
        cat_desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        topic = entry["topic"]
        theme = entry["theme_style"]
        output += f"| **{day}** | {cat_desc} | {topic} | {theme} |\n"

    output += "\n### Daily Breakdown\n\n"

    for entry in schedule:
        day = entry["day"]
        cat = entry["category"]
        cat_desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
        topic = entry["topic"]
        theme = entry["theme_style"]
        note_types = entry.get("note_types", [])
        handbook_prompt = entry.get("handbook_prompt", "")

        output += f"#### {day}\n"

        if cat == "NOTES_ONLY":
            output += "**Post:** None (notes-only day)\n"
        else:
            output += f"**Post:** {cat_desc}\n"
            output += f"- Topic: {topic}\n"
            output += f"- HTML Theme: {theme}\n"
            output += f"- **Handbook prompt:** {handbook_prompt}\n"

        # Note types for this day
        if note_types:
            output += f"\n**Notes** (use **Daily Notes Prompt** from handbook):\n"
            for i, nt in enumerate(note_types, 1):
                output += f"- Note {i}: {nt}\n"
        output += "\n"

    return output


# =============================================================================
# SECTION 4: PROMPT REFERENCE
# =============================================================================

def generate_prompt_reference() -> str:
    """Brief section pointing to the handbook."""

    return """
---

## 4. HOW TO USE THIS DOCUMENT

**All prompts are in `docs/content_prompt_handbook_v5.md`.**

Each day:
1. Open **Claude.ai** (Opus 4.6 + extended thinking)
2. **Attach** this context document
3. Check the schedule above for today's **category** (e.g., "Ticker Deep Dive")
4. Copy that category's **Post Prompt** from the handbook and send
5. Copy the **Daily Notes Prompt** from the handbook and send (generates 3 HTML notes)

No placeholders to fill — the prompts read this context document automatically.

| Category | Handbook Section |
|----------|------------------|
| Ticker Deep Dive & Price Targets | Category 1 |
| Educational | Category 2 |
| Market Rotations & Growth Themes | Category 3 |
| Performance Review (Sunday) | Category 4 |
| Trade Alert — Entry (ad-hoc) | Trade Alert — Entry |
| Trade Alert — Exit (ad-hoc) | Trade Alert — Exit |
| Daily Notes (3 HTML notes) | Daily Notes Prompt |

**Saturday:** Notes only — skip the post prompt, just send the Daily Notes Prompt.

**Trade Alerts:** When entering or exiting a position, use the Trade Alert prompt
instead of the scheduled category. These are the only prompts requiring a ticker symbol.
"""


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def main():
    """Generate the complete content production guide."""
    parser = argparse.ArgumentParser(description="Generate weekly content production guide")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--signals", type=str, help="Path to signals.json")
    args = parser.parse_args()

    print("=" * 70)
    print("  STERLING SIGNALS — CONTENT PRODUCTION GUIDE GENERATOR")
    print("=" * 70)
    print()

    # Load data
    signals_path = Path(args.signals) if args.signals else None
    print("  Loading data...")
    ctx = build_content_context(signals_path)
    portfolio = load_full_portfolio()
    print(f"  ✓ Signals: {ctx.scan_stats.get('tickers_loaded', 0):,} scanned, {ctx.pass_count} GREEN")
    print(f"  ✓ Portfolio: {len(portfolio)} open positions")
    print(f"  ✓ Themes: {len(ctx.themes)}")
    print(f"  ✓ Winners: {len(ctx.historical_winners)}")

    # Build weekly schedule (4 categories)
    schedule = build_weekly_schedule(ctx, portfolio)
    print(f"  ✓ Weekly schedule: {len(schedule)} days planned")
    for entry in schedule:
        cat_short = CATEGORY_DESCRIPTIONS.get(entry["category"], entry["category"])[:40]
        print(f"      {entry['day']}: {cat_short}")

    # Generate all sections
    print("\n  Generating guide...")
    sections = []
    sections.append(generate_system_context())
    sections.append(generate_weekly_data(ctx, portfolio))
    sections.append(generate_content_history())
    sections.append(generate_weekly_schedule(schedule))
    sections.append(generate_prompt_reference())

    guide = "\n".join(sections)

    # Add generation timestamp
    guide += f"\n\n---\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Week {ctx.week_number}*\n"

    if args.dry_run:
        print(f"\n  DRY RUN — guide would be {len(guide):,} characters ({len(guide.splitlines()):,} lines)")
        print(f"  First 300 chars:\n{guide[:300]}")
        return

    # Save to current
    if OUTPUT_PATHS_AVAILABLE:
        ensure_output_structure()
        current_dir = get_substack_current_dir()
    else:
        current_dir = get_substack_current_dir()
        current_dir.mkdir(parents=True, exist_ok=True)

    guide_path = current_dir / "content_production_guide.md"
    guide_path.write_text(guide)
    print(f"  ✓ Saved: {guide_path}")

    # Save JSON sidecar (for dashboard consumption)
    schedule_data = {
        "week": ctx.week_number,
        "generated": datetime.now().isoformat(),
        "schedule": schedule,
    }
    json_path = current_dir / "content_schedule.json"
    json_path.write_text(json.dumps(schedule_data, indent=2))
    print(f"  ✓ Saved: {json_path}")

    # Archive to weekly
    if OUTPUT_PATHS_AVAILABLE:
        archive_dir = get_substack_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / "content_production_guide.md"
        archive_path.write_text(guide)
        archive_json = archive_dir / "content_schedule.json"
        archive_json.write_text(json.dumps(schedule_data, indent=2))
        print(f"  ✓ Archived: {archive_path}")
    else:
        archive_dir = get_substack_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / "content_production_guide.md"
        archive_path.write_text(guide)
        archive_json = archive_dir / "content_schedule.json"
        archive_json.write_text(json.dumps(schedule_data, indent=2))
        print(f"  ✓ Archived: {archive_path}")

    print(f"\n  Guide size: {len(guide):,} characters ({len(guide.splitlines()):,} lines)")
    print("  Done!")


if __name__ == "__main__":
    main()
