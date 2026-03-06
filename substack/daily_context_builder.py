#!/usr/bin/env python3
"""
Daily Context Builder — Sterling Signals
==========================================

Generates daily_context.md for Claude.ai chat sessions and
daily_notes_context.json for the notes generator.

No LLM calls. Reads from signals.json, portfolio data, market_analysis.md,
and content archives. Determines today's post category + topic and embeds
the exact prompt from the content prompt handbook.

Replaces: content_production_guide.py (858 lines)

Output:
    substack/output/current/daily_context.md
    substack/output/current/daily_notes_context.json
    substack/output/archive/{week}/daily_context.md
    substack/output/archive/{week}/daily_notes_context.json

Usage:
    python -m substack.daily_context_builder                    # Today
    python -m substack.daily_context_builder --day wednesday    # Override
    python -m substack.daily_context_builder --dry-run          # Preview
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ─── Project imports ──────────────────────────────────────────────────────────

from config import BASE_DIR, PORTFOLIO_FILE, BRANDING, get_conviction_text

from config.banned_terms import CRITICAL_BANNED, BANNED_PHRASES, INTERNAL_TERMINOLOGY_MAP

try:
    from config.output_paths import (
        get_substack_current_dir,
        get_substack_archive_dir,
        get_scanner_current_dir,
        ensure_output_structure,
        SCANNER_OUTPUT,
        SUBSTACK_OUTPUT,
        CLAUDE_CONTENT_DIR,
        list_weekly_archives,
        LIVE_CONTEXT_FILE,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False

from substack.content_utils import (
    build_content_context,
    ContentContext,
    load_signals,
    load_portfolio_winners,
    load_equity_curve,
    load_historical_themes,
    _format_themes_for_prompt,
    _format_signals_for_prompt,
    _format_winners_for_prompt,
    _format_assessed_for_prompt,
    _format_equity_stats,
    _format_theme_history,
)

SUBSTACK_URL = BRANDING.get("substack_url", "https://sterlingsignals.substack.com")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PostAssignment:
    """What post to write today."""
    category: str               # Ticker Deep Dive, Theme Rotation, Educational, Performance Review
    theme: str                  # "editorial" or "dashboard"
    topic: str                  # e.g. "Deep Dive — $RCAT"
    reason: str                 # Why this topic today
    prompt_key: str             # Key to extract from handbook
    ticker_data: Optional[Dict] = None
    theme_data: Optional[Dict] = None
    override_type: Optional[str] = None  # "milestone", "exit", None


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Category constants
CATEGORY_TICKER_DIVE = "Ticker Deep Dive"
CATEGORY_EDUCATIONAL = "Educational"
CATEGORY_THEME_ROTATION = "Theme Rotation"
CATEGORY_PERFORMANCE_REVIEW = "Performance Review"

# Category → HTML theme mapping
CATEGORY_THEMES = {
    CATEGORY_TICKER_DIVE: "editorial",
    CATEGORY_EDUCATIONAL: "editorial",
    CATEGORY_THEME_ROTATION: "dashboard",
    CATEGORY_PERFORMANCE_REVIEW: "dashboard",
}

# Note type rotation matrix (v2 — 12 archetypes)
NOTE_TYPE_MATRIX = {
    "saturday": [
        {"slot": 1, "type": "WINNER_RECEIPT", "time": "08:30 ET"},
        {"slot": 2, "type": "THEME_ROTATION", "time": "12:30 ET"},
    ],
    "sunday": [
        {"slot": 1, "type": "ALPHA_SCOREBOARD", "time": "08:30 ET"},
        {"slot": 2, "type": "READER_QUESTION", "time": "12:30 ET"},
    ],
    "monday": [
        {"slot": 1, "type": "MARKET_SNAPSHOT", "time": "08:30 ET"},
        {"slot": 2, "type": "THE_FILTER", "time": "12:30 ET"},
        {"slot": 3, "type": "PORTFOLIO_UPDATE", "time": "17:00 ET"},
    ],
    "tuesday": [
        {"slot": 1, "type": "SIGNAL_DROP", "time": "08:30 ET"},
        {"slot": 2, "type": "THEME_ROTATION", "time": "12:30 ET"},
        {"slot": 3, "type": "DATA_INSIGHT", "time": "17:00 ET"},
    ],
    "wednesday": [
        {"slot": 1, "type": "MARKET_SNAPSHOT", "time": "08:30 ET"},
        {"slot": 2, "type": "WINNER_RECEIPT", "time": "12:30 ET"},
        {"slot": 3, "type": "CATALYST_WATCH", "time": "17:00 ET"},
    ],
    "thursday": [
        {"slot": 1, "type": "SECTOR_FLOW", "time": "08:30 ET"},
        {"slot": 2, "type": "SIGNAL_DROP", "time": "12:30 ET"},
        {"slot": 3, "type": "READER_QUESTION", "time": "17:00 ET"},
    ],
    "friday": [
        {"slot": 1, "type": "MARKET_SNAPSHOT", "time": "08:30 ET"},
        {"slot": 2, "type": "PORTFOLIO_UPDATE", "time": "12:30 ET"},
        {"slot": 3, "type": "EXIT_DEBRIEF", "time": "17:00 ET"},
    ],
}

# Handbook prompt section headers (used to extract prompts)
HANDBOOK_SECTION_MAP = {
    "ticker_deep_dive": "## Category 1 — Ticker Deep Dive",
    "educational": "## Category 2 — Educational",
    "theme_rotation": "## Category 3 — Theme Rotation",
    "performance_review": "## Category 4 — Performance Review",
    "trade_alert_entry": "## Trade Alert — Entry",
    "trade_alert_exit": "## Trade Alert — Exit",
    "daily_notes": "## Notes Prompt",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_full_portfolio() -> List[Dict]:
    """Load ALL open positions with full metrics from PortfolioManager.

    Preserved from content_production_guide.py — provides richer data than
    content_utils.load_portfolio_winners() (includes stop levels, days held, etc.)
    """
    portfolio_path = PORTFOLIO_FILE
    if not portfolio_path.exists():
        return []

    try:
        from portfolio.manager import PortfolioManager

        pm = PortfolioManager()
        try:
            pm.update_prices()
        except Exception as e:
            print(f"  Warning: Could not fetch live prices: {e}")

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
    except Exception as e:
        print(f"  Warning: PortfolioManager unavailable ({e}), falling back to CSV")
        return load_portfolio_winners()


def load_portfolio_snapshot() -> Optional[Dict]:
    """Try to load portfolio_snapshot.json for milestone detection.

    Returns dict with 'open_positions' (list with prev_day_pnl_pct) and
    'recent_exits' if available. Returns None if file doesn't exist.
    """
    if not OUTPUT_PATHS_AVAILABLE:
        return None

    snapshot_path = get_substack_current_dir() / "portfolio_snapshot.json"
    if not snapshot_path.exists():
        return None

    try:
        with open(snapshot_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_live_market_data() -> Dict:
    """Load live market index data (SPY, QQQ, VIX).

    Tries yfinance for real-time data. Falls back to empty dict.
    """
    try:
        import yfinance as yf

        data = {}
        for symbol in ["SPY", "QQQ"]:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
            prev = info.get("regularMarketPreviousClose", 0)
            change_pct = ((price / prev) - 1) * 100 if prev > 0 else 0
            data[symbol.lower() + "_price"] = round(price, 2) if price else 0
            data[symbol.lower() + "_change_pct"] = round(change_pct, 2)

        # VIX
        vix = yf.Ticker("^VIX")
        vix_info = vix.info
        data["vix"] = round(vix_info.get("regularMarketPrice", 0) or 0, 1)

        return data
    except Exception as e:
        print(f"  Warning: Could not fetch live market data: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT CALENDAR LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def get_top_signal_or_position(ctx: ContentContext, portfolio: List[Dict]) -> Dict:
    """Get the best ticker for a Ticker Deep Dive post.

    Priority: new GREEN signal > top portfolio winner (15%+).
    """
    # New signals first
    if ctx.buy_signals:
        top = ctx.buy_signals[0]
        return {
            "symbol": top.get("symbol", "???"),
            "price": top.get("price", 0),
            "theme": top.get("theme", ""),
            "conviction": top.get("dd_conviction", top.get("conviction", 0)),
            "pitch": top.get("dd_elevator_pitch", top.get("catalyst_summary", "")),
            "is_new": True,
        }

    # Fall back to top portfolio position (15%+)
    for p in portfolio:
        if p.get("pnl_pct", 0) >= 15.0:
            return {
                "symbol": p["ticker"],
                "price": p.get("current_price", p.get("highest_close", 0)),
                "theme": p.get("theme", ""),
                "pnl_pct": p["pnl_pct"],
                "entry_price": p.get("entry_price", 0),
                "is_new": False,
            }

    # Last resort: any open position
    if portfolio:
        p = portfolio[0]
        return {
            "symbol": p["ticker"],
            "price": p.get("current_price", p.get("highest_close", 0)),
            "theme": p.get("theme", ""),
            "pnl_pct": p.get("pnl_pct", 0),
            "entry_price": p.get("entry_price", 0),
            "is_new": False,
        }

    return {"symbol": "N/A", "is_new": False}


def get_top_theme(ctx: ContentContext) -> Dict:
    """Get the best theme for a Theme Rotation post."""
    for theme in ctx.themes:
        classification = theme.get("classification", "")
        if classification in ("PRIME", "INVESTABLE"):
            return {
                "name": theme.get("name", "Market Themes"),
                "status": classification,
                "score": theme.get("composite_score", 0),
                "thesis": theme.get("thesis_summary", ""),
                "catalysts": theme.get("key_catalysts", []),
            }

    # Fallback: first theme regardless of classification
    if ctx.themes:
        t = ctx.themes[0]
        return {
            "name": t.get("name", "Market Themes"),
            "status": t.get("classification", ""),
            "score": t.get("composite_score", 0),
            "thesis": t.get("thesis_summary", ""),
            "catalysts": t.get("key_catalysts", []),
        }

    return {"name": "Market Themes", "status": "", "score": 0}


def get_second_theme(ctx: ContentContext, exclude_name: str) -> Optional[Dict]:
    """Get a second theme for Thursday flex, excluding the Wednesday theme."""
    for theme in ctx.themes:
        name = theme.get("name", "")
        classification = theme.get("classification", "")
        if name != exclude_name and classification in ("PRIME", "INVESTABLE"):
            return {
                "name": name,
                "status": classification,
                "score": theme.get("composite_score", 0),
                "thesis": theme.get("thesis_summary", ""),
                "catalysts": theme.get("key_catalysts", []),
            }
    return None


def check_event_overrides(portfolio: List[Dict], snapshot: Optional[Dict]) -> Optional[PostAssignment]:
    """Detect events that override the scheduled post category.

    Uses portfolio_snapshot.json for milestone detection (prev_day_pnl_pct).
    Falls back gracefully when snapshot unavailable.
    """
    # Milestone detection requires snapshot with prev_day_pnl_pct
    if snapshot:
        for pos in snapshot.get("open_positions", []):
            pnl_pct = pos.get("pnl_pct", 0)
            prev_pnl = pos.get("prev_day_pnl_pct", 0)

            # Hall of Fame: crossed +100%
            if pnl_pct >= 100 and prev_pnl < 100:
                return PostAssignment(
                    category=CATEGORY_PERFORMANCE_REVIEW,
                    theme="dashboard",
                    topic=f"HALL OF FAME — ${pos['symbol']} +{pnl_pct:.0f}%",
                    reason="Position crossed +100% milestone",
                    prompt_key="performance_review",
                    override_type="milestone",
                    ticker_data=pos,
                )

            # Home Run: crossed +50%
            if pnl_pct >= 50 and prev_pnl < 50:
                return PostAssignment(
                    category=CATEGORY_PERFORMANCE_REVIEW,
                    theme="dashboard",
                    topic=f"HOME RUN — ${pos['symbol']} +{pnl_pct:.0f}%",
                    reason="Position crossed +50% milestone",
                    prompt_key="performance_review",
                    override_type="milestone",
                    ticker_data=pos,
                )

        # Check for exits since yesterday
        today_str = datetime.now().strftime("%Y-%m-%d")
        recent_exits = [
            e for e in snapshot.get("recent_exits", [])
            if e.get("exit_date") == today_str
        ]
        if recent_exits:
            exit_pos = recent_exits[0]
            return PostAssignment(
                category=CATEGORY_TICKER_DIVE,
                theme="editorial",
                topic=f"Exit Alert — ${exit_pos['symbol']}",
                reason=f"Position exited today: {exit_pos.get('exit_reason', 'stop hit')}",
                prompt_key="exit_alert",
                override_type="exit",
                ticker_data=exit_pos,
            )
    else:
        print("  \u2139 portfolio_snapshot.json not available — milestone detection skipped (will work after portfolio spec)")

    return None


def determine_thursday_flex(
    ctx: ContentContext,
    portfolio: List[Dict],
    wednesday_theme_name: str,
) -> PostAssignment:
    """Determine Thursday's flex post per spec Section 3.2.

    Decision tree:
    1. New GREEN signals + theme shifted status → Theme Rotation (different theme)
    2. Portfolio has +50%/+100% milestone → Performance Review
    3. No signals this week (quiet week) → Educational
    4. Default → Ticker Deep Dive (second signal or portfolio position)
    """
    # 1. New signals + second PRIME/INVESTABLE theme available
    if ctx.pass_count > 0:
        second_theme = get_second_theme(ctx, wednesday_theme_name)
        if second_theme:
            return PostAssignment(
                category=CATEGORY_THEME_ROTATION,
                theme="dashboard",
                topic=f"Theme Rotation — {second_theme['name']}",
                reason=f"Second {second_theme['status']} theme (composite {second_theme['score']}/10)",
                prompt_key="theme_rotation",
                theme_data=second_theme,
            )

    # 2. Portfolio milestone (check without snapshot — use current P&L)
    for p in portfolio:
        if p.get("pnl_pct", 0) >= 50:
            return PostAssignment(
                category=CATEGORY_PERFORMANCE_REVIEW,
                theme="dashboard",
                topic=f"Portfolio Milestone — ${p['ticker']} +{p['pnl_pct']:.0f}%",
                reason="Position at +50%+ milestone",
                prompt_key="performance_review",
            )

    # 3. No signals → Educational
    if ctx.pass_count == 0:
        return PostAssignment(
            category=CATEGORY_EDUCATIONAL,
            theme="editorial",
            topic="Evergreen investing framework (topic via web search)",
            reason="Quiet week — no new GREEN signals",
            prompt_key="educational",
        )

    # 4. Default → Ticker Deep Dive on second signal or portfolio position
    ticker = get_top_signal_or_position(ctx, portfolio)
    label = "new signal" if ticker.get("is_new") else "portfolio position"
    return PostAssignment(
        category=CATEGORY_TICKER_DIVE,
        theme="editorial",
        topic=f"Deep Dive — ${ticker['symbol']}",
        reason=f"Second-priority {label}",
        prompt_key="ticker_deep_dive",
        ticker_data=ticker,
    )


def determine_todays_post(
    day: str,
    ctx: ContentContext,
    portfolio: List[Dict],
    snapshot: Optional[Dict] = None,
) -> Optional[PostAssignment]:
    """Determine what post to write today, if any.

    Returns None for days with no long-form post (Sunday, Monday, Friday).
    """
    day_lower = day.lower()

    # Check event overrides first (highest priority)
    override = check_event_overrides(portfolio, snapshot)
    if override:
        return override

    # Day-based schedule
    if day_lower == "saturday":
        return PostAssignment(
            category=CATEGORY_PERFORMANCE_REVIEW,
            theme="dashboard",
            topic="Weekly Newsletter — flagship recap",
            reason="Saturday = always weekly newsletter",
            prompt_key="performance_review",
        )

    elif day_lower == "tuesday":
        ticker = get_top_signal_or_position(ctx, portfolio)
        label = "new signal" if ticker.get("is_new") else "portfolio position"
        return PostAssignment(
            category=CATEGORY_TICKER_DIVE,
            theme="editorial",
            topic=f"Deep Dive — ${ticker['symbol']}",
            reason=f"Highest conviction {label}",
            prompt_key="ticker_deep_dive",
            ticker_data=ticker,
        )

    elif day_lower == "wednesday":
        theme = get_top_theme(ctx)
        return PostAssignment(
            category=CATEGORY_THEME_ROTATION,
            theme="dashboard",
            topic=f"Theme Rotation — {theme['name']}",
            reason=f"Top {theme['status'] or 'active'} theme (composite {theme['score']}/10)",
            prompt_key="theme_rotation",
            theme_data=theme,
        )

    elif day_lower == "thursday":
        # Need Wednesday's theme name for dedup
        wed_theme = get_top_theme(ctx)
        return determine_thursday_flex(ctx, portfolio, wed_theme["name"])

    else:
        # Sunday, Monday, Friday — no long-form post
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT EMBEDDING
# ═══════════════════════════════════════════════════════════════════════════════

def find_handbook_path() -> Optional[Path]:
    """Find the content prompt handbook in the repo."""
    candidates = [
        BASE_DIR / "substack" / "docs" / "content_prompt_handbook_v5.md",
        BASE_DIR / "substack" / "docs" / "content_prompt_handbook.md",
    ]
    # Also glob for any version
    docs_dir = BASE_DIR / "substack" / "docs"
    if docs_dir.exists():
        for p in sorted(docs_dir.glob("content_prompt_handbook*.md"), reverse=True):
            if p not in candidates:
                candidates.append(p)

    for p in candidates:
        if p.exists():
            return p
    return None


def extract_prompt_from_handbook(handbook_text: str, section_header: str) -> str:
    """Extract the prompt text from a handbook section.

    Finds the section header, then extracts the content between the first
    ``` code fence in that section and the closing ```.
    """
    # Find the section start
    idx = handbook_text.find(section_header)
    if idx == -1:
        return ""

    # Get text from section start to next ## header (or end)
    section_text = handbook_text[idx + len(section_header):]
    next_section = re.search(r'\n## ', section_text)
    if next_section:
        section_text = section_text[:next_section.start()]

    # Extract content between ``` fences
    # Look for ### Post Prompt or ### Notes Prompt subsection first
    prompt_match = re.search(r'```\n(.*?)```', section_text, re.DOTALL)
    if prompt_match:
        return prompt_match.group(1).strip()

    return ""


def load_prompt_for_category(prompt_key: str) -> str:
    """Load the exact prompt text from the content prompt handbook.

    Returns the full prompt ready for the user to copy-paste.
    """
    handbook_path = find_handbook_path()
    if not handbook_path:
        return f"[PROMPT NOT FOUND: {prompt_key} — check content_prompt_handbook location]"

    handbook_text = handbook_path.read_text()

    section_header = HANDBOOK_SECTION_MAP.get(prompt_key, "")
    if not section_header:
        return f"[PROMPT NOT FOUND: unknown key '{prompt_key}']"

    prompt_text = extract_prompt_from_handbook(handbook_text, section_header)
    if not prompt_text:
        return f"[PROMPT NOT FOUND: could not extract from section '{section_header}']"

    return prompt_text


def load_notes_prompt() -> str:
    """Load the universal daily notes prompt from the handbook."""
    return load_prompt_for_category("daily_notes")


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM CONTEXT (preserved from content_production_guide.py)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_system_context() -> str:
    """Generate the system context section for the daily context document.

    v2: Data-forward voice, honest transparency, white-background HTML.
    """
    banned_summary = [
        "Internal indicators: HMA, Banker, UC, Undercurrent, BoS, RSI, MACD, KDJ, ExD, VWAP, Beta >= 1.5",
        "System terms: Gatekeeper, Investment Gate, Deep DD, 5-gate, Tier 1/2/3, conviction scores (numeric), price cap, gear shift, profit lock, tiered stop",
        "Old signal branding: TEAL, VIOLET, AMBER, PASS signal, STRONG BUY, SPEC BUY, NO GO",
        "UK audience: UK ISA, GMT, BST, UK Time, GBP/USD",
        "US retirement: Roth IRA, PDT, 401k",
        "Leaked internal: Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria",
        "AI-sounding: Let's dive in, Here's the thing, It's worth noting, Interestingly enough, In today's market, The bottom line is",
    ]

    approved = [
        ("System description", '"our screening system" — keep it simple'),
        ("Entry signals", '"momentum confirmed", "structural pivot confirmation"'),
        ("Institutional signals", '"institutional accumulation patterns"'),
        ("Exit/Risk", '"systematic exit discipline", "the system triggered an exit"'),
        ("Signal branding", '"GREEN signal" for buys, "system exit" for sells'),
        ("Conviction", '"Extremely Bullish" (high), "Bullish" (medium), "Watching" (low) — NEVER numbers'),
    ]

    return f"""## SYSTEM CONTEXT

### Who We Are
Sterling Signals is a momentum investing newsletter on Substack. We screen 1,800+ US stocks weekly through a systematic process and share everything transparently — entry prices, current P&L, exit signals. When we're wrong, readers see it. When we're right, the numbers speak for themselves.

### Our Niche
Small-cap growth stocks (under $25) with momentum and thematic alignment. We're looking for the next $NVDA-in-2022 — right stock, right sector, right time. We track institutional capital flows across themes and only enter when technical momentum, thematic alignment, and fundamental screening all confirm.

### Our System (Public Description)
Systematic screening that filters ~1,800 stocks through:
1. Technical screening — momentum confirmation, structural trend analysis
2. Thematic alignment — sector flow analysis, institutional capital tracking
3. Fundamental screening — due diligence to filter red flags
4. Final selection — 0-3 GREEN signals per week

We reject 99%+ of what we screen. That selectivity is the edge.

### Voice & Writing Rules
- Lead with specific numbers, prices, and percentages. The data IS the hook.
- Name tickers with prices: "$RCAT at $13.25, up 55.9% from our $8.50 entry."
- Be direct and opinionated. "Defence is rotating in. Grid infrastructure is accelerating."
- Use contractions. Vary sentence length. Write like a person, not a marketing department.
- Never use vague phrases: "interesting setups", "keep an eye on", "stay tuned"
- Never use AI-sounding phrases: "Let's dive in", "Here's the thing", "It's worth noting"
- Never add filler paragraphs that restate data you just showed
- After presenting data, go straight to a forward-looking thought. No recap.

### Marketing Rules (CRITICAL)

**Signal Branding:** Use "GREEN signal" for buy signals. NEVER use TEAL, PASS, VIOLET, AMBER.

**BANNED Terms:**
{chr(10).join(f"- {b}" for b in banned_summary)}

**Approved Alternatives:**
{chr(10).join(f"- {name}: {alt}" for name, alt in approved)}

**Portfolio Display Rules (Honest Transparency):**
- **15%+ gain**: Showcase with entry price and P&L percentage
- **Under 15% (positive)**: Can mention in updates, no spotlight
- **Negative P&L**: Acknowledge honestly. "$ANET at $85.50, down from our $89.00 entry — thesis intact, watching the $82 level." NEVER use the word "loss" or frame negatively. State the facts.
- **Performance Reviews**: Show ALL positions with entry prices. Transparency builds trust.
- **Notes**: Only spotlight 15%+ winners. Red positions only in PORTFOLIO_UPDATE and MARKET_SNAPSHOT types.

**Subscribe Hooks (vary these — don't use the same one twice in a day):**
- "Every GREEN signal, every entry, every exit — documented weekly: {SUBSTACK_URL}"
- "Subscribers got this signal before Monday's open. The next screening drops Friday."
- "Every position, every entry price, every week — in the Saturday newsletter."
- "We score themes weekly across 1,800 stocks. Full breakdown every Saturday."

End every note with: "Not financial advice. Informational only."

### HTML Themes (White Background for All)
**Editorial** (all post types): White bg #ffffff, Georgia serif headings, system sans-serif body 16px, line-height 1.7
- Price targets: Bear (#fdf6f4, #dc2626 border), Base (#f4f7fa, #2563eb border), Bull (#f4faf5, #16a34a border)
- Tables: #f8f7f5 header, #fafaf8 alt rows, #e8e4df borders
- Callouts: 3px left border #3d5a80, bg #f4f7fa
**Theme Rotation accent**: teal #0d9488 borders, #f0fdfa highlight bg
**Performance Review accent**: stat cards bg #f8f7f5, 28px bold numbers
**Notes**: transparent bg, system sans 16px, #1a1a1a text
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT HISTORY (anti-repetition)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_content_history() -> str:
    """Scan archives for recent published content to avoid repetition.

    Preserved from content_production_guide.py.
    """
    if not OUTPUT_PATHS_AVAILABLE:
        return "### Recent Content\nArchive not available.\n"

    output = "### Recent Content (anti-repetition)\n\n"

    try:
        substack_archives = list_weekly_archives("substack")
    except Exception:
        substack_archives = []

    recent_weeks = sorted(substack_archives)[-2:] if substack_archives else []

    for week_id in recent_weeks:
        week_dir = SUBSTACK_OUTPUT / "archive" / week_id
        if not week_dir.exists():
            continue

        output += f"**{week_id}:**\n"

        # Posts
        posts_dir = week_dir / "substack_posts"
        if posts_dir.exists():
            posts = sorted(posts_dir.glob("*.html"))
            if posts:
                for p in posts:
                    output += f"- Post: {p.stem}\n"

        # Notes count
        notes_dir = week_dir / "substack_notes"
        if notes_dir.exists():
            notes = list(notes_dir.glob("*.html")) + list(notes_dir.glob("*.md"))
            if notes:
                output += f"- Notes: {len(notes)} published\n"

        output += "\n"

    # Claude.ai content
    if CLAUDE_CONTENT_DIR.exists():
        claude_files = sorted(CLAUDE_CONTENT_DIR.glob("*.html"))
        if claude_files:
            output += "**Claude.ai content (last 7):**\n"
            for f in claude_files[-7:]:
                output += f"- {f.name}\n"
            output += "\n"

    return output


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY CONTEXT DOCUMENT (markdown output)
# ═══════════════════════════════════════════════════════════════════════════════

def build_daily_context(
    day: str,
    ctx: ContentContext,
    portfolio: List[Dict],
    assignment: Optional[PostAssignment],
    market_data: Dict,
) -> str:
    """Build the complete daily_context.md document."""
    now = datetime.now()
    day_title = day.capitalize()

    sections = []

    # ── Header ────────────────────────────────────────────────────────────
    sections.append(f"# Sterling Signals — {day_title} {now.strftime('%B %d, %Y')}\n")

    # ── Today's Post ──────────────────────────────────────────────────────
    if assignment:
        override_note = ""
        if assignment.override_type == "milestone":
            override_note = "\n> **EVENT OVERRIDE:** This replaces the scheduled category."
        elif assignment.override_type == "exit":
            override_note = "\n> **EXIT ALERT:** This replaces the scheduled category."

        sections.append(f"""## TODAY'S POST
**Category:** {assignment.category}
**Topic:** {assignment.topic}
**Theme:** {'Editorial (light)' if assignment.theme == 'editorial' else 'Dashboard (dark)'}
**Why this topic:** {assignment.reason}{override_note}

---
""")
    else:
        sections.append(f"""## TODAY'S POST
**No long-form post today** ({day_title}).
Focus on notes only — use the Daily Notes Prompt below.

---
""")

    # ── Your Prompt ───────────────────────────────────────────────────────
    if assignment:
        prompt_text = load_prompt_for_category(assignment.prompt_key)
        sections.append(f"""## YOUR PROMPT

Copy everything below and paste into Claude.ai (Opus 4.6 + extended thinking):

---

{prompt_text}

---
""")

    # ── Notes Prompt ──────────────────────────────────────────────────────
    notes_prompt = load_notes_prompt()
    if notes_prompt:
        sections.append(f"""## NOTES PROMPT

After the post, copy this prompt to generate today's 3 notes:

---

{notes_prompt}

---
""")

    # ── Market Context ────────────────────────────────────────────────────
    market_section = "## MARKET CONTEXT"
    if market_data:
        spy_str = f"SPY ${market_data.get('spy_price', 0):.2f} ({market_data.get('spy_change_pct', 0):+.2f}%)"
        qqq_str = f"QQQ ${market_data.get('qqq_price', 0):.2f} ({market_data.get('qqq_change_pct', 0):+.2f}%)"
        vix_str = f"VIX {market_data.get('vix', 0):.1f}"
        market_section += f"\n**Live data ({now.strftime('%H:%M ET')}):** {spy_str} | {qqq_str} | {vix_str}\n"
    else:
        market_section += "\n*Live market data not available — use web search in Claude.ai for current prices.*\n"

    if ctx.market_analysis:
        market_section += f"\n{ctx.market_analysis[:2000]}\n"

    sections.append(market_section)

    # ── Signal Data ───────────────────────────────────────────────────────
    stats = ctx.scan_stats
    tickers = stats.get("tickers_loaded", 0)
    technical = stats.get("technical_signals", stats.get("buy_signal", 0))
    theme_confirmed = stats.get("theme_confirmed", 0)

    sections.append(f"""## SIGNAL DATA

### Scanner Results
- Tickers scanned: {tickers:,}
- Passed technical gates: {technical}
- Theme confirmed: {theme_confirmed}
- **GREEN signals: {ctx.pass_count}**
- Rejection rate: {((1 - ctx.pass_count / max(tickers, 1)) * 100):.1f}%

### New Signals
{_format_signals_for_prompt(ctx.buy_signals)}

### Stocks That Didn't Make the Cut
{_format_assessed_for_prompt(ctx.assessed_signals) or "No assessed signals available."}
""")

    # ── Portfolio Snapshot ────────────────────────────────────────────────
    total = len(portfolio)
    avg_pnl = sum(p.get("pnl_pct", 0) for p in portfolio) / max(total, 1) if portfolio else 0
    big_winners = [p for p in portfolio if p.get("pnl_pct", 0) >= 25.0]

    portfolio_section = f"## PORTFOLIO SNAPSHOT\n"
    portfolio_section += f"Open: {total} positions | Avg P&L: {avg_pnl:+.1f}% | Big winners (25%+): {len(big_winners)}\n"

    # Equity stats
    equity = _format_equity_stats(ctx.portfolio_stats)
    if equity and "not available" not in equity.lower():
        portfolio_section += f"\n{equity}\n"

    # Benchmark
    if ctx.benchmark:
        portfolio_section += f"\n{ctx.benchmark}\n"

    # Positions table
    if portfolio:
        portfolio_section += "\n### Open Positions\n"
        portfolio_section += "| Ticker | Current | Entry | P&L | Days | Theme | Stop |\n"
        portfolio_section += "|--------|---------|-------|-----|------|-------|------|\n"
        for p in portfolio:
            current = f"${p.get('current_price', 0):.2f}"
            entry = f"${p.get('entry_price', 0):.2f}"
            pnl = f"{p.get('pnl_pct', 0):+.1f}%"
            days = str(p.get("days_held", 0))
            stop = f"${p.get('stop_level', 0):.2f}" if p.get("stop_level", 0) > 0 else "ExD"
            portfolio_section += f"| ${p.get('ticker', '?')} | {current} | {entry} | {pnl} | {days} | {p.get('theme', '')} | {stop} |\n"

    # Showcase-ready winners
    portfolio_section += "\n### Showcase-Ready Winners\n"
    portfolio_section += _format_winners_for_prompt(ctx.historical_winners) + "\n"

    sections.append(portfolio_section)

    # ── Theme Summary ─────────────────────────────────────────────────────
    sections.append(f"""## THEME SUMMARY

{_format_themes_for_prompt(ctx.themes)}
""")

    # Theme history
    theme_history = load_historical_themes()
    if theme_history:
        sections.append("### Theme Trends (last 4 weeks)\n")
        for name, entries in sorted(theme_history.items()):
            trend_str = _format_theme_history(name, theme_history)
            sections.append(f"- **{name}**: {trend_str}")
        sections.append("")

    # ── Content History ───────────────────────────────────────────────────
    sections.append(generate_content_history())

    # ── Today's Notes ─────────────────────────────────────────────────────
    day_lower = day.lower()
    note_schedule = NOTE_TYPE_MATRIX.get(day_lower, [])
    if note_schedule:
        notes_section = "## TODAY'S NOTES\n\n"
        notes_section += f"**{len(note_schedule)} notes** for {day_title}:\n"
        for note in note_schedule:
            notes_section += f"- Slot {note['slot']} ({note['time']}): {note['type']}\n"
        notes_section += "\n*Full HTML notes generated via the Notes Prompt above.*\n"
        sections.append(notes_section)

    # ── Footer ────────────────────────────────────────────────────────────
    sections.append(f"""---

*Attach this file to Claude.ai (Opus 4.6 + extended thinking). Paste the prompt
from the "YOUR PROMPT" section. The response will be publishable HTML.*

*Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} | Week {ctx.week_number}*
""")

    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTINUITY TRACKING (recent notes for anti-repetition)
# ═══════════════════════════════════════════════════════════════════════════════

def load_recent_notes_summary() -> Dict:
    """Load yesterday's notes manifest for continuity tracking.

    Returns a dict with:
        yesterday_types: list of note types generated yesterday
        yesterday_tickers: list of tickers mentioned yesterday
        tickers_last_2_days: combined ticker list to avoid repetition
    """
    result = {
        "yesterday_types": [],
        "yesterday_tickers": [],
        "tickers_last_2_days": [],
    }

    if not OUTPUT_PATHS_AVAILABLE:
        return result

    try:
        # Check current/notes/notes_manifest.json (most recent generation)
        current_dir = get_substack_current_dir()
        manifest_path = current_dir / "notes" / "notes_manifest.json"

        if not manifest_path.exists():
            return result

        manifest = json.loads(manifest_path.read_text())
        generated_at = manifest.get("generated_at", "")

        # Only use if generated in the last 48 hours
        if generated_at:
            try:
                gen_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(gen_time.tzinfo) - gen_time).total_seconds() / 3600
                if age_hours > 48:
                    return result
            except (ValueError, TypeError):
                pass

        # Extract types and tickers from manifest
        notes = manifest.get("notes", [])
        types = []
        tickers = []

        for note in notes:
            note_type = note.get("type", note.get("scheduled_type", ""))
            if note_type:
                types.append(note_type)

            # Extract tickers from note text
            text = note.get("text", "")
            if text:
                # Find $TICKER patterns
                found = re.findall(r'\$([A-Z]{2,5})\b', text)
                tickers.extend(found)

        result["yesterday_types"] = types
        result["yesterday_tickers"] = list(set(tickers))
        result["tickers_last_2_days"] = list(set(tickers))

        # Also check archive for day-before-yesterday
        try:
            archive_dir = get_substack_archive_dir()
            archive_manifest = archive_dir / "notes" / "notes_manifest.json"
            if archive_manifest.exists() and archive_manifest != manifest_path:
                older = json.loads(archive_manifest.read_text())
                for note in older.get("notes", []):
                    text = note.get("text", "")
                    if text:
                        found = re.findall(r'\$([A-Z]{2,5})\b', text)
                        result["tickers_last_2_days"].extend(found)
                result["tickers_last_2_days"] = list(set(result["tickers_last_2_days"]))
        except Exception:
            pass

    except Exception as e:
        print(f"  Warning: Could not load recent notes summary: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY NOTES CONTEXT (JSON sidecar)
# ═══════════════════════════════════════════════════════════════════════════════

def build_notes_context_json(
    day: str,
    ctx: ContentContext,
    portfolio: List[Dict],
    market_data: Dict,
) -> Dict:
    """Build the daily_notes_context.json document.

    v2: Enriched positions, full theme data, market analysis, continuity tracking.
    """
    now = datetime.now()
    day_lower = day.lower()

    # ── Portfolio: FULL position data (not stripped) ──────────────────────
    portfolio_summary = {
        "open_count": len(portfolio),
        "win_rate": 0.0,
        "total_pnl_pct": 0.0,
        "top_performer": None,
        "positions": [],
    }

    if portfolio:
        winners = [p for p in portfolio if p.get("pnl_pct", 0) > 0]
        portfolio_summary["win_rate"] = round(
            len(winners) / len(portfolio) * 100, 1
        ) if portfolio else 0.0
        portfolio_summary["total_pnl_pct"] = round(
            sum(p.get("pnl_pct", 0) for p in portfolio) / len(portfolio), 1
        )

        top = portfolio[0]  # Already sorted by pnl_pct desc
        portfolio_summary["top_performer"] = {
            "symbol": top.get("ticker", ""),
            "pnl_pct": top.get("pnl_pct", 0),
            "entry": top.get("entry_price", 0),
            "current": top.get("current_price", 0),
            "theme": top.get("theme", ""),
            "days_held": top.get("days_held", 0),
        }

        # ENRICHED: include all available fields per position
        portfolio_summary["positions"] = [
            {
                "symbol": p.get("ticker", ""),
                "entry_price": p.get("entry_price", 0),
                "current_price": p.get("current_price", 0),
                "pnl_pct": p.get("pnl_pct", 0),
                "theme": p.get("theme", ""),
                "days_held": p.get("days_held", 0),
                "conviction": p.get("conviction", 0),
                "stop_level": p.get("stop_level", 0),
                "distance_to_stop_pct": p.get("distance_to_stop_pct", 0),
                "stop_alert": p.get("stop_alert", False),
            }
            for p in portfolio
        ]

    # ── Signals: include full signal data ────────────────────────────────
    signals_summary = {
        "new_this_week": [],
        "pass_count": ctx.pass_count,
        "buy_signals": [],
        "themes": [],
    }

    # Include signal tickers for quick reference
    for s in ctx.buy_signals:
        signals_summary["new_this_week"].append(s.get("symbol", ""))
        signals_summary["buy_signals"].append({
            "symbol": s.get("symbol", ""),
            "price": s.get("price", 0),
            "theme": s.get("theme", ""),
            "theme_score": s.get("theme_score", 0),
            "conviction": s.get("dd_conviction", s.get("conviction", 0)),
            "catalyst_summary": s.get("catalyst_summary", ""),
            "final_decision": s.get("final_decision", ""),
        })

    # ENRICHED: include thesis and catalysts for each theme
    for t in ctx.themes:
        signals_summary["themes"].append({
            "name": t.get("name", ""),
            "status": t.get("classification", ""),
            "composite": t.get("composite_score", 0),
            "thesis_summary": t.get("thesis_summary", ""),
            "key_catalysts": t.get("key_catalysts", []),
            "primary_etfs": t.get("primary_etfs", []),
        })

    # ── Scanner stats ────────────────────────────────────────────────────
    stats = ctx.scan_stats
    scanner_stats = {
        "universe_size": stats.get("tickers_loaded", 0),
        "technical_pass": stats.get("technical_signals", stats.get("buy_signal", 0)),
        "theme_pass": stats.get("theme_confirmed", 0),
        "green_signals": ctx.pass_count,
    }

    # ── Market analysis excerpt ──────────────────────────────────────────
    market_excerpt = ""
    if OUTPUT_PATHS_AVAILABLE:
        analysis_path = get_substack_current_dir() / "market_analysis.md"
        if analysis_path.exists():
            try:
                full_text = analysis_path.read_text()
                # Take first 1000 chars as excerpt (covers key findings)
                market_excerpt = full_text[:1000].strip()
                if len(full_text) > 1000:
                    market_excerpt += "..."
            except Exception:
                pass

    # ── Continuity: recent notes data ────────────────────────────────────
    recent_notes = load_recent_notes_summary()

    # ── Live context from tweet pipeline (if available) ──────────────────
    ticker_events = []
    try:
        live_ctx_path = LIVE_CONTEXT_FILE if OUTPUT_PATHS_AVAILABLE else Path("twitter/output/live_context.json")
        if live_ctx_path.exists():
            live_ctx = json.loads(live_ctx_path.read_text())
            # Extract any ticker-specific opportunities/events
            opps = live_ctx.get("tweet_opportunities", [])
            for opp in opps:
                ticker = opp.get("ticker", "")
                if ticker and any(p.get("ticker", "") == ticker for p in portfolio):
                    ticker_events.append({
                        "symbol": ticker,
                        "event": opp.get("angle", opp.get("headline", "")),
                        "category": opp.get("category", ""),
                    })
    except Exception:
        pass

    return {
        "day": day_lower,
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat() + "Z",
        "note_schedule": NOTE_TYPE_MATRIX.get(day_lower, []),

        # Live market data
        "live_data": market_data,

        # Enriched portfolio (Phase 2)
        "portfolio": portfolio_summary,

        # Enriched signals + themes (Phase 2)
        "signals": signals_summary,

        # Scanner stats
        "scanner_stats": scanner_stats,

        # Market analysis excerpt (Phase 2 — NEW)
        "market_analysis_excerpt": market_excerpt,

        # Continuity tracking (Phase 2 — NEW)
        "recent_notes": recent_notes,

        # Ticker events from tweet pipeline (Phase 2 — NEW, opportunistic)
        "ticker_events": ticker_events,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Generate the daily context document and notes JSON."""
    parser = argparse.ArgumentParser(description="Generate daily context for Claude.ai")
    parser.add_argument("--day", type=str, help="Override day (e.g., wednesday)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--signals", type=str, help="Path to signals.json")
    parser.add_argument("--skip-market", action="store_true", help="Skip live market data fetch")
    args = parser.parse_args()

    # Determine day
    if args.day:
        day = args.day.lower()
    else:
        day = datetime.now().strftime("%A").lower()

    print("=" * 70)
    print("  STERLING SIGNALS — DAILY CONTEXT BUILDER")
    print(f"  {day.capitalize()} {datetime.now().strftime('%B %d, %Y')}")
    print("=" * 70)
    print()

    # Load data
    signals_path = Path(args.signals) if args.signals else None
    print("  Loading data...")
    ctx = build_content_context(signals_path)
    portfolio = load_full_portfolio()
    snapshot = load_portfolio_snapshot()

    print(f"  \u2713 Signals: {ctx.scan_stats.get('tickers_loaded', 0):,} scanned, {ctx.pass_count} GREEN")
    print(f"  \u2713 Portfolio: {len(portfolio)} open positions")
    print(f"  \u2713 Themes: {len(ctx.themes)}")
    print(f"  \u2713 Snapshot: {'loaded' if snapshot else 'not available'}")

    # Live market data
    if args.skip_market:
        market_data = {}
        print("  \u2713 Market data: skipped")
    else:
        print("  Fetching live market data...")
        market_data = load_live_market_data()
        if market_data:
            print(f"  \u2713 SPY ${market_data.get('spy_price', 0):.2f} | QQQ ${market_data.get('qqq_price', 0):.2f} | VIX {market_data.get('vix', 0):.1f}")
        else:
            print("  \u2713 Market data: not available (use web search in Claude.ai)")

    # Determine today's post
    assignment = determine_todays_post(day, ctx, portfolio, snapshot)

    if assignment:
        print(f"\n  \u2192 POST: {assignment.category}")
        print(f"    Topic: {assignment.topic}")
        theme_display = "Editorial (light)" if assignment.theme == "editorial" else "Dashboard (dark)"
        print(f"    Theme: {theme_display}")
        print(f"    Reason: {assignment.reason}")
        if assignment.override_type:
            print(f"    Override: {assignment.override_type}")
    else:
        print(f"\n  \u2192 No long-form post today ({day.capitalize()}) — notes only")

    # Notes schedule
    note_schedule = NOTE_TYPE_MATRIX.get(day, [])
    print(f"\n  Notes: {len(note_schedule)} scheduled")
    for note in note_schedule:
        print(f"    Slot {note['slot']} ({note['time']}): {note['type']}")

    # Build outputs
    print("\n  Building daily context...")
    context_md = build_daily_context(day, ctx, portfolio, assignment, market_data)
    notes_json = build_notes_context_json(day, ctx, portfolio, market_data)

    print(f"  \u2713 daily_context.md: {len(context_md):,} chars ({len(context_md.splitlines()):,} lines)")
    print(f"  \u2713 daily_notes_context.json: {len(json.dumps(notes_json)):,} chars")

    if args.dry_run:
        print(f"\n  DRY RUN — preview:\n")
        # Show first 500 chars
        print(context_md[:500])
        print("  ...")
        return

    # Save to current
    if OUTPUT_PATHS_AVAILABLE:
        ensure_output_structure()
        current_dir = get_substack_current_dir()
    else:
        current_dir = get_substack_current_dir()
        current_dir.mkdir(parents=True, exist_ok=True)

    context_path = current_dir / "daily_context.md"
    context_path.write_text(context_md)
    print(f"\n  \u2713 Saved: {context_path}")

    json_path = current_dir / "daily_notes_context.json"
    json_path.write_text(json.dumps(notes_json, indent=2))
    print(f"  \u2713 Saved: {json_path}")

    # Archive to weekly
    if OUTPUT_PATHS_AVAILABLE:
        archive_dir = get_substack_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "daily_context.md").write_text(context_md)
        (archive_dir / "daily_notes_context.json").write_text(json.dumps(notes_json, indent=2))
        print(f"  \u2713 Archived: {archive_dir}")

    print("\n  Done!")


if __name__ == "__main__":
    main()
