#!/usr/bin/env python3
"""
DAILY NOTES GENERATOR — v2 (Data-Forward Voice)
=================================================

Generates 2-3 Substack Notes per day with live market data.

Note Types (12 archetypes, replacing 7 broad types):
    MARKET_SNAPSHOT   — SPY/QQQ/VIX + specific portfolio impact
    SIGNAL_DROP       — New GREEN signal announcement
    WINNER_RECEIPT    — Single position spotlight (15%+ gain)
    PORTFOLIO_UPDATE  — Honest full-portfolio snapshot
    THEME_ROTATION    — One theme: score, catalysts, our positions
    THE_FILTER        — Screening funnel numbers
    CATALYST_WATCH    — Upcoming events for our positions
    SECTOR_FLOW       — Where money is moving, connected to themes
    EXIT_DEBRIEF      — Position closed: why, lesson
    ALPHA_SCOREBOARD  — Portfolio vs SPY/QQQ with numbers
    DATA_INSIGHT      — Counterintuitive investing stat, current context
    READER_QUESTION   — Data-seeded question for engagement

Usage:
    python -m substack.daily_notes_generator                       # Today's notes
    python -m substack.daily_notes_generator --day wednesday       # Override day
    python -m substack.daily_notes_generator --dry-run             # Preview without LLM
    python -m substack.daily_notes_generator --no-llm              # Template fallback only
    python -m substack.daily_notes_generator --html                # HTML output (default)
"""

import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ─── Project imports ──────────────────────────────────────────────────────────

from config import BRANDING, MODEL_NOTES, get_conviction_text
from config.banned_terms import check_banned_phrases, validate_content
from config.output_paths import (
    get_substack_current_dir,
    get_substack_archive_dir,
)

try:
    from config import MARKETING_THRESHOLDS
except ImportError:
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
    }

MIN_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
BIG_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)

# Shared note utilities
from substack.note_utils import (
    NoteContext,
    build_note_context,
    sanitize_note,
    validate_note,
    repair_note,
    save_note,
    ensure_output_dirs,
)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE TYPES (12 archetypes)
# ═══════════════════════════════════════════════════════════════════════════════

NOTE_TYPES = [
    "MARKET_SNAPSHOT",
    "SIGNAL_DROP",
    "WINNER_RECEIPT",
    "PORTFOLIO_UPDATE",
    "THEME_ROTATION",
    "THE_FILTER",
    "CATALYST_WATCH",
    "SECTOR_FLOW",
    "EXIT_DEBRIEF",
    "ALPHA_SCOREBOARD",
    "DATA_INSIGHT",
    "READER_QUESTION",
]

# Fallback mapping: if a conditional type can't fire, use this instead
FALLBACK_MAP = {
    "SIGNAL_DROP": "THE_FILTER",
    "WINNER_RECEIPT": "PORTFOLIO_UPDATE",
    "EXIT_DEBRIEF": "DATA_INSIGHT",
    "CATALYST_WATCH": "SECTOR_FLOW",
    "ALPHA_SCOREBOARD": "PORTFOLIO_UPDATE",
}


# ═══════════════════════════════════════════════════════════════════════════════
# NOTES SCHEDULE (12 archetypes across 7 days)
# ═══════════════════════════════════════════════════════════════════════════════

NOTES_SCHEDULE = {
    "saturday":  [("WINNER_RECEIPT", "08:30"), ("THEME_ROTATION", "12:30")],
    "sunday":    [("ALPHA_SCOREBOARD", "08:30"), ("READER_QUESTION", "12:30")],
    "monday":    [("MARKET_SNAPSHOT", "08:30"), ("THE_FILTER", "12:30"), ("PORTFOLIO_UPDATE", "17:00")],
    "tuesday":   [("SIGNAL_DROP", "08:30"), ("THEME_ROTATION", "12:30"), ("DATA_INSIGHT", "17:00")],
    "wednesday": [("MARKET_SNAPSHOT", "08:30"), ("WINNER_RECEIPT", "12:30"), ("CATALYST_WATCH", "17:00")],
    "thursday":  [("SECTOR_FLOW", "08:30"), ("SIGNAL_DROP", "12:30"), ("READER_QUESTION", "17:00")],
    "friday":    [("MARKET_SNAPSHOT", "08:30"), ("PORTFOLIO_UPDATE", "12:30"), ("EXIT_DEBRIEF", "17:00")],
}


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — v2 (Data-Forward + Anti-AI + Anti-Filler)
# ═══════════════════════════════════════════════════════════════════════════════

NOTES_SYSTEM_PROMPT = """You are writing Substack Notes for Sterling Signals, a momentum investing newsletter that screens 1,800+ US stocks weekly and publishes a transparent paper portfolio with real entry prices, exit levels, and P&L.

WHAT WE DO:
We run a systematic screening process — technical momentum confirmation, thematic alignment, and fundamental due diligence — and share everything transparently. Entry prices, current P&L, exit signals. When we're wrong, readers see it. When we're right, the numbers speak for themselves.

HOW TO WRITE:
- Lead with a specific number, price, or percentage. The data IS the hook.
- Name tickers with prices: "$RCAT at $13.25, up 55.9% from our $8.50 entry."
- State what happened, then what it means. Not the other way around.
- Be direct. "Defence is rotating in. Grid infrastructure is accelerating."
- Show the screening filter when relevant: "1,817 scanned. 48 passed technicals. 3 cleared all gates."
- When referencing the portfolio, include the entry price and current level.
- Losses are part of the system. Frame honestly: "$ANET at $85.50, down from our $89.00 entry — AI infrastructure hit by broader tech selling this week." Never hide them.
- Keep it conversational. Short sentences. Occasional one-liners that land.

ANTI-FABRICATION (CRITICAL):
- Use ONLY the data provided in the prompt. Do not invent dates, prices, percentages, historical comparisons, or time periods.
- If you are given "days held: 67" but no entry date, say "67 days" — do NOT calculate backwards to guess a calendar date.
- If you are not given historical theme scores, do NOT write "the highest score in six weeks" or any similar comparison.
- If you are not given information about a feature (dashboard, alerts, app), do NOT reference it.
- When in doubt, use what you have. Silence beats fabrication.

WHAT SUBSCRIBERS ACTUALLY GET (use only these in subscribe hooks):
- Saturday weekly newsletter with full portfolio breakdown, screening results, and theme analysis
- GREEN signal alerts published before Monday market open
- Every entry and exit documented with full reasoning on the Substack
- Weekly theme scoring across 1,800 stocks
Do NOT reference: dashboards, apps, real-time alerts, or any feature not listed above.

BANNED TERMS:
- Indicator names: HMA, RSI, MACD, KDJ, Banker, UC, Undercurrent, BoS, ExD
- System internals: Gatekeeper, Investment Gate, Deep DD, Tier 1/2/3, conviction scores, profit lock, tiered stop
- Old branding: TEAL, PASS, VIOLET, AMBER signal
- Geography: UK ISA, GMT, BST, Roth IRA, PDT
- Vague filler: "interesting setups", "keep an eye on", "more to come", "stay tuned", "some notable moves"
- Use "GREEN signal" for buys. "Our screening system" for the system.
- Conviction: "Extremely Bullish" / "Bullish" / "Watching" — never numbers.

SOUND LIKE A PERSON, NOT AN AI:
- Never start a note with a question. Start with a fact, a number, or a blunt statement.
- Never use "Let's dive in", "Here's the thing", "It's worth noting", "Interestingly enough", "In today's market", "Let me break this down", "The bottom line is".
- Never use three adjectives in a row. Pick one.
- Never explain what you're about to do. Just do it.
- Never use "This is what X looks like" or "That's the power of Y" or "This is why we Z". The reader draws their own conclusion.
- Vary sentence length dramatically. A five-word sentence after a long one creates rhythm.
- Use contractions. "We're" not "We are". "That's" not "That is".
- Occasionally be blunt. "Defence is working. Tech isn't. Simple week."
- Have an opinion. "We think this pullback is noise" is human. "The pullback may present opportunities" is AI.

NO FILLER PARAGRAPHS (CRITICAL):
- After presenting portfolio data, DO NOT add a paragraph restating what you just showed. If you wrote that $LUNR is up 140% and $RCAT is up 55.9%, do NOT follow with "These positions are banking gains while tech consolidates" — you already said that with numbers.
- DO NOT add a paragraph explaining what the data means in abstract terms. "This is momentum rotation in real time" is filler.
- DO NOT add closing lines that declare what the pattern is. "The rotation isn't noise — it's structural" is AI trying to sound punchy. The data already made the point.
- A good note shows the data, gives one forward-looking thought, and stops. No recap. No thesis statement at the end.

FORMAT:
- 150-280 words. Every word earns its place.
- No markdown headers. No bullet lists. Short paragraphs and standalone lines.
- $TICKER format with price or percentage always.
- One emoji maximum, only if it adds clarity.
- End with: "Not financial advice. Informational only."
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HTML NOTE TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

HTML_NOTE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body>
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
{body_html}
<p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
</div>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SUBSCRIBE HOOKS (replacing generic engagement hooks)
# ═══════════════════════════════════════════════════════════════════════════════

SUBSCRIBE_HOOKS = {
    "MARKET_SNAPSHOT": [
        "Every position, every entry price, every week — in the Saturday newsletter.",
        "We break down how every market move hits our portfolio. Full analysis every Saturday.",
    ],
    "SIGNAL_DROP": [
        "Subscribers got this signal before Monday's open. The next screening drops Friday.",
        "Full analysis — entry reasoning, theme alignment, and exit plan — in this week's newsletter.",
    ],
    "WINNER_RECEIPT": [
        "Subscribers got this signal at ${entry}. The next screening drops Friday.",
        "Full entry reasoning and exit plan in last Saturday's newsletter.",
        "We publish every signal before Monday's open. This was one of them.",
    ],
    "PORTFOLIO_UPDATE": [
        "Every entry and exit, with full reasoning, every Saturday.",
        "See the complete portfolio with entry prices and live P&L in the weekly newsletter.",
    ],
    "THEME_ROTATION": [
        "We score themes weekly across 1,800 stocks. Full breakdown every Saturday.",
        "Theme rankings, top tickers, and where capital is flowing — in the Saturday newsletter.",
    ],
    "THE_FILTER": [
        "Full screening results — what passed and what didn't — every Saturday.",
        "See which stocks cleared all gates this week in the newsletter.",
    ],
    "CATALYST_WATCH": [
        "We track catalysts for every position. Full calendar in the Saturday newsletter.",
    ],
    "SECTOR_FLOW": [
        "We map sector flows weekly. See where the money's going in the Saturday newsletter.",
    ],
    "EXIT_DEBRIEF": [
        "Every exit documented with full reasoning — Saturday newsletter.",
    ],
    "ALPHA_SCOREBOARD": [
        "Full portfolio breakdown vs benchmarks every Saturday.",
    ],
    "DATA_INSIGHT": [
        "We apply this to every screening decision. See how in the Saturday newsletter.",
    ],
    "READER_QUESTION": [],  # Pure engagement — no CTA
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_notes_context_json() -> Optional[Dict]:
    """Load daily_notes_context.json produced by daily_context_builder."""
    path = get_substack_current_dir() / "daily_notes_context.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return None


def build_note_context_from_daily(context: Dict) -> NoteContext:
    """Build a NoteContext from the daily_notes_context.json data."""
    now = datetime.now()

    live = context.get("live_market", context.get("live_data", {}))
    spy_pct = live.get("spy_change_pct", 0.0)
    qqq_pct = live.get("qqq_change_pct", 0.0)

    portfolio_data = context.get("portfolio", [])
    if isinstance(portfolio_data, dict):
        positions = portfolio_data.get("positions", [])
        open_count = portfolio_data.get("open_count", len(positions))
        top_performer = portfolio_data.get("top_performer")
    else:
        positions = portfolio_data
        open_count = len(positions)
        top_performer = positions[0] if positions else None

    big_winners = [p for p in positions if p.get("pnl_pct", 0) >= BIG_WIN_THRESHOLD]

    signals = context.get("signals", {})
    buy_signals = signals.get("buy_signals", signals.get("pass_signals", []))
    pass_signals = [s for s in buy_signals
                    if s.get("final_decision") in ("PASS", "TRADE")]
    consider_signals = [s for s in buy_signals
                        if s.get("final_decision") == "CONSIDER"]

    return NoteContext(
        week_number=now.isocalendar().week,
        date_str=now.strftime("%B %d, %Y"),
        spy_5d_pct=spy_pct,
        qqq_5d_pct=qqq_pct,
        market_analysis_excerpt=context.get("market_analysis_excerpt", ""),
        open_count=open_count,
        winners=positions,
        big_winners=big_winners,
        top_performer=top_performer,
        pass_signals=pass_signals,
        consider_signals=consider_signals,
        themes=context.get("themes", []),
        scan_stats=context.get("scan_stats", context.get("scanner_stats", {})),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HOOK SELECTION
# ═══════════════════════════════════════════════════════════════════════════════

_hooks_used_today: List[str] = []


def pick_subscribe_hook(note_type: str, ctx: Optional[NoteContext] = None) -> str:
    """Pick a subscribe hook for this note type, avoiding repeats within the day."""
    global _hooks_used_today
    hooks = SUBSCRIBE_HOOKS.get(note_type, [])
    if not hooks:
        return ""

    # For WINNER_RECEIPT, fill in entry price if available
    if note_type == "WINNER_RECEIPT" and ctx and ctx.top_performer:
        entry = ctx.top_performer.get("entry_price", ctx.top_performer.get("entry", 0))
        hooks = [h.replace("${entry}", f"${entry:.2f}") for h in hooks]

    unused = [h for h in hooks if h not in _hooks_used_today]
    if not unused:
        unused = hooks
    hook = random.choice(unused)
    _hooks_used_today.append(hook)
    return hook


# ═══════════════════════════════════════════════════════════════════════════════
# CONDITIONAL FIRING CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def can_fire(note_type: str, ctx: NoteContext) -> bool:
    """Check if a conditional note type has the data it needs."""
    if note_type == "SIGNAL_DROP":
        return len(ctx.pass_signals) > 0
    elif note_type == "WINNER_RECEIPT":
        return any(p.get("pnl_pct", 0) >= MIN_WIN_THRESHOLD for p in ctx.winners)
    elif note_type == "EXIT_DEBRIEF":
        # Would need recent_exits in context — fallback if not available
        return False  # TODO: enable when portfolio snapshot provides exit data
    elif note_type == "ALPHA_SCOREBOARD":
        return ctx.open_count > 0  # Need positions to show alpha
    elif note_type == "CATALYST_WATCH":
        return ctx.open_count > 0  # Need positions to watch
    return True  # Most types can always fire


def resolve_note_type(note_type: str, ctx: NoteContext) -> str:
    """Resolve a note type, falling back if it can't fire."""
    if can_fire(note_type, ctx):
        return note_type
    fallback = FALLBACK_MAP.get(note_type, note_type)
    if fallback != note_type and can_fire(fallback, ctx):
        print(f"    ℹ {note_type} → {fallback} (insufficient data)")
        return fallback
    return fallback  # Use fallback even if imperfect


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Format positions for prompts
# ═══════════════════════════════════════════════════════════════════════════════

def _format_positions_for_prompt(positions: List[Dict], max_positions: int = 8) -> str:
    """Format portfolio positions as a clean text block for LLM prompts."""
    if not positions:
        return "  No open positions."
    lines = []
    for p in positions[:max_positions]:
        ticker = p.get("ticker", p.get("symbol", "???"))
        entry = p.get("entry_price", p.get("entry", 0))
        current = p.get("current_price", p.get("current", 0))
        pnl = p.get("pnl_pct", 0)
        theme = p.get("theme", "")
        days = p.get("days_held", p.get("days", "?"))
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        theme_str = f" — {theme}" if theme else ""
        lines.append(f"  ${ticker}: entry ${entry:.2f}, now ${current:.2f} ({pnl_str}){theme_str}, {days} days held")
    return "\n".join(lines)


def _get_showcase_winner(ctx: NoteContext) -> Optional[Dict]:
    """Get the best winner for showcase (15%+)."""
    for p in ctx.winners:
        if p.get("pnl_pct", 0) >= MIN_WIN_THRESHOLD:
            return p
    return ctx.top_performer if ctx.top_performer else (ctx.winners[0] if ctx.winners else None)


# ═══════════════════════════════════════════════════════════════════════════════
# PER-TYPE PROMPT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_market_snapshot_prompt(ctx: NoteContext) -> str:
    """SPY/QQQ/VIX + specific portfolio impact."""
    positions_text = _format_positions_for_prompt(ctx.winners)
    market_excerpt = ctx.market_analysis_excerpt or "No market analysis available."
    hook = pick_subscribe_hook("MARKET_SNAPSHOT", ctx)

    return f"""Write a MARKET_SNAPSHOT note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  SPY: {ctx.spy_5d_pct:+.1f}% | QQQ: {ctx.qqq_5d_pct:+.1f}%
  Market context: {market_excerpt}

  Portfolio ({ctx.open_count} positions):
{positions_text}

DATA YOU DO NOT HAVE (do not reference or guess):
  - Entry dates (you have days held, not calendar dates)
  - Historical comparisons to previous weeks
  - Intraday prices or after-hours moves

Connect today's market move to our specific positions. Which held up? Which felt it? Why?

After showing positions with numbers, go straight to one forward-looking line about what we're watching. No recap paragraph.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_signal_drop_prompt(ctx: NoteContext) -> str:
    """New GREEN signal announcement."""
    sig = ctx.pass_signals[0]
    stats = ctx.scan_stats
    loaded = stats.get("tickers_loaded", stats.get("universe_size", 1817))
    tech = stats.get("technical_signals", stats.get("technical_pass", 0))
    theme_pass = stats.get("theme_confirmed", stats.get("theme_pass", 0))
    green = stats.get("final_trade", stats.get("green_signals", len(ctx.pass_signals)))
    conv_text = get_conviction_text(sig.get("conviction", sig.get("dd_conviction", 0)))
    hook = pick_subscribe_hook("SIGNAL_DROP", ctx)

    return f"""Write a SIGNAL_DROP note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  New GREEN signal: ${sig.get('symbol', '???')} at ${sig.get('price', 0):.2f}
  Theme: {sig.get('theme', 'N/A')} (score: {sig.get('theme_score', 0)}/10)
  Outlook: {conv_text}
  Funnel: {loaded} scanned → {tech} passed technicals → {theme_pass} theme-confirmed → {green} GREEN

DATA YOU DO NOT HAVE (do not reference or guess):
  - Historical theme scores or "highest in X weeks" comparisons
  - Analyst targets or institutional holdings
  - Price targets for this signal

Announce the signal. Ticker, price, theme. Show the funnel. One or two sentences on why this theme matters.

After the funnel and thesis, stop. Don't add a paragraph about how selective the process is — the funnel already showed that.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_winner_receipt_prompt(ctx: NoteContext) -> str:
    """Single position spotlight with entry, current, P&L."""
    w = _get_showcase_winner(ctx)
    if not w:
        return build_portfolio_update_prompt(ctx)

    ticker = w.get("ticker", w.get("symbol", "???"))
    entry = w.get("entry_price", w.get("entry", 0))
    current = w.get("current_price", w.get("current", 0))
    pnl = w.get("pnl_pct", 0)
    days = w.get("days_held", w.get("days", "?"))
    theme = w.get("theme", "")

    other_text = _format_positions_for_prompt(
        [p for p in ctx.winners if p.get("ticker", p.get("symbol")) != ticker], max_positions=4
    )

    hook_raw = pick_subscribe_hook("WINNER_RECEIPT", ctx)
    hook = hook_raw.replace("${entry}", f"${entry:.2f}")

    return f"""Write a WINNER_RECEIPT note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  Spotlight: ${ticker} — entry ${entry:.2f}, now ${current:.2f}
  P&L: +{pnl:.1f}% over {days} days
  Theme: {theme}

  Other positions:
{other_text}

DATA YOU DO NOT HAVE (do not reference or guess):
  - The calendar date we entered (you have days held only)
  - Price targets or analyst ratings
  - Any subscriber feature beyond the Saturday newsletter

Lead with entry and current price. Show percentage and timeframe in days.

1-2 sentences on the thesis — what structural trend is this riding.

Mention the rest of the portfolio honestly. Winners exist alongside red positions.

After the data, go straight to one forward thought. No recap paragraph.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_portfolio_update_prompt(ctx: NoteContext) -> str:
    """Honest full-portfolio snapshot."""
    positions_text = _format_positions_for_prompt(ctx.winners)
    hook = pick_subscribe_hook("PORTFOLIO_UPDATE", ctx)

    green_count = sum(1 for p in ctx.winners if p.get("pnl_pct", 0) > 0)
    red_count = len(ctx.winners) - green_count

    return f"""Write a PORTFOLIO_UPDATE note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  {ctx.open_count} positions open. {green_count} green, {red_count} red.
  SPY: {ctx.spy_5d_pct:+.1f}% | QQQ: {ctx.qqq_5d_pct:+.1f}%

  All positions:
{positions_text}

DATA YOU DO NOT HAVE (do not reference or guess):
  - Entry dates (you have days held only)
  - Historical performance comparisons

Walk through the portfolio honestly. Top to bottom. Show every position with its entry price and current P&L.

Green positions: state the gain matter-of-factly.
Red positions: acknowledge them directly. What sector are they in? Is the thesis intact?

One forward-looking line at the end.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_theme_rotation_prompt(ctx: NoteContext) -> str:
    """One theme: score, catalysts, our positions."""
    if ctx.themes:
        theme = ctx.themes[0]
        name = theme.get("name", "Unknown")
        classification = theme.get("classification", "N/A")
        score = theme.get("composite_score", 0)
        thesis = theme.get("thesis_summary", "")
        catalysts = theme.get("key_catalysts", [])
        catalysts_text = "; ".join(catalysts[:3]) if catalysts else "Multiple catalysts converging."

        theme_tickers = [w for w in ctx.winners if w.get("theme", "") == name]
        ticker_text = ""
        if theme_tickers:
            parts = []
            for t in theme_tickers[:2]:
                tk = t.get("ticker", t.get("symbol", "???"))
                pnl = t.get("pnl_pct", 0)
                entry = t.get("entry_price", t.get("entry", 0))
                parts.append(f"${tk} at {pnl:+.1f}% from ${entry:.2f} entry")
            ticker_text = f"\n  Our positions in this theme: {', '.join(parts)}"

        theme_block = f"""  Theme: {name}
  Classification: {classification}
  Score: {score}/10
  Thesis: {thesis}
  Catalysts: {catalysts_text}{ticker_text}"""
    else:
        theme_block = "  No scored themes available. Write about sector rotation using market context."

    hook = pick_subscribe_hook("THEME_ROTATION", ctx)

    return f"""Write a THEME_ROTATION note for {ctx.date_str}.

DATA YOU HAVE (use only this):
{theme_block}

DATA YOU DO NOT HAVE (do not reference or guess):
  - Historical theme score changes or "up from last week" comparisons
  - ETF flow numbers (unless provided above)
  - Analyst recommendations

Name the theme. State the score. 1-2 catalysts driving it. If we hold positions in this theme, name them with entry prices.

One forward thought: what event or data point would accelerate or derail this theme.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_the_filter_prompt(ctx: NoteContext) -> str:
    """Screening funnel numbers."""
    stats = ctx.scan_stats
    loaded = stats.get("tickers_loaded", stats.get("universe_size", 1817))
    tech = stats.get("technical_signals", stats.get("technical_pass", 0))
    theme_pass = stats.get("theme_confirmed", stats.get("theme_pass", 0))
    green = stats.get("final_trade", stats.get("green_signals", 0))

    winner_line = ""
    if ctx.winners:
        w = ctx.winners[0]
        tk = w.get("ticker", w.get("symbol", "???"))
        pnl = w.get("pnl_pct", 0)
        if pnl >= MIN_WIN_THRESHOLD:
            winner_line = f"\n  Proof: ${tk} at +{pnl:.1f}% — found by the same screening process."

    hook = pick_subscribe_hook("THE_FILTER", ctx)

    return f"""Write a THE_FILTER note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  {loaded} stocks scanned
  → {tech} passed technical screening
  → {theme_pass} cleared thematic alignment
  → {green} earned GREEN signals
  Rejection rate: {((1 - green / max(loaded, 1)) * 100):.1f}%{winner_line}

Lead with the funnel numbers. They're the hook.

Briefly explain what each stage filters for — without using banned indicator names. Frame selectivity as the edge. Most traders chase everything. This system rejects 99%+.

If winner proof exists, mention it once. Don't belabour it.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_catalyst_watch_prompt(ctx: NoteContext) -> str:
    """Upcoming events for positions we hold."""
    positions_text = _format_positions_for_prompt(ctx.winners, max_positions=5)
    hook = pick_subscribe_hook("CATALYST_WATCH", ctx)

    return f"""Write a CATALYST_WATCH note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  Portfolio positions:
{positions_text}

  Themes we're tracking: {', '.join(t.get('name', '') for t in ctx.themes[:3]) or 'N/A'}

DATA YOU DO NOT HAVE (do not reference or guess):
  - Specific earnings dates or FDA dates (unless provided above)
  - Conference schedules

Based on the themes and sectors our positions are in, identify what types of catalysts could be coming: earnings seasons, sector-specific policy events, contract announcements. Frame as "what we're watching" rather than predicting specific dates.

Keep it concrete to our positions and themes, not generic market events.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_sector_flow_prompt(ctx: NoteContext) -> str:
    """Where money is moving — one sector gaining, one losing."""
    market_excerpt = ctx.market_analysis_excerpt or ""
    positions_text = _format_positions_for_prompt(ctx.winners, max_positions=4)
    hook = pick_subscribe_hook("SECTOR_FLOW", ctx)

    themes_text = ""
    if ctx.themes:
        parts = [f"{t.get('name', '?')} ({t.get('classification', '?')}, {t.get('composite_score', 0)}/10)" for t in ctx.themes[:3]]
        themes_text = "\n  Theme scores: " + ", ".join(parts)

    return f"""Write a SECTOR_FLOW note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  SPY: {ctx.spy_5d_pct:+.1f}% | QQQ: {ctx.qqq_5d_pct:+.1f}%
  Market context: {market_excerpt}{themes_text}

  Portfolio:
{positions_text}

Identify a rotation happening: one sector or theme strengthening, another weakening. Connect it to our positions.

Be opinionated. "Capital is leaving X and entering Y. Our portfolio reflects that." Don't hedge with "may" and "could."

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_exit_debrief_prompt(ctx: NoteContext) -> str:
    """Position closed — why, lesson. Falls back to DATA_INSIGHT if no exits."""
    # This will typically fallback since exit data isn't always in context
    return build_data_insight_prompt(ctx)


def build_alpha_scoreboard_prompt(ctx: NoteContext) -> str:
    """Portfolio vs SPY/QQQ with numbers."""
    positions_text = _format_positions_for_prompt(ctx.winners, max_positions=5)
    hook = pick_subscribe_hook("ALPHA_SCOREBOARD", ctx)

    avg_pnl = sum(p.get("pnl_pct", 0) for p in ctx.winners) / max(len(ctx.winners), 1)

    return f"""Write an ALPHA_SCOREBOARD note for {ctx.date_str}.

DATA YOU HAVE (use only this):
  Portfolio: {ctx.open_count} positions
  Average P&L: {avg_pnl:+.1f}%
  SPY recent: {ctx.spy_5d_pct:+.1f}% | QQQ recent: {ctx.qqq_5d_pct:+.1f}%
  Week {ctx.week_number}

  Positions:
{positions_text}

DATA YOU DO NOT HAVE (do not reference or guess):
  - YTD portfolio return (use only what's above)
  - Exact alpha figures unless calculable from the data provided

Show the portfolio's performance against the benchmarks using the numbers provided. If we're outperforming, state it plainly. If we're not, acknowledge it.

Name the top contributor and the laggard. Both with entry prices.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_data_insight_prompt(ctx: NoteContext) -> str:
    """Counterintuitive investing stat connected to current context."""
    topics = [
        "Position sizing matters more than stock picking. A portfolio of average picks with great sizing outperforms great picks with random sizing.",
        "The average investor underperforms the funds they invest in by 1-2% annually because they buy after gains and sell after losses.",
        "Stocks above their 200-day moving average historically return 12% annualized vs -2% for those below it. Trend following isn't fancy, but it works.",
        "The best-performing accounts at most brokerages belong to people who forgot their passwords. Doing less beats doing more.",
        "Small caps have outperformed large caps in 60% of rolling 10-year periods since 1926. The volatility is the premium.",
        "90% of a portfolio's return comes from asset allocation and timing, not stock selection. Yet most investors spend 90% of their time on stock selection.",
        "Momentum strategies have worked in every asset class, in every country, across every time period tested. It's one of the most robust anomalies in finance.",
        "The stocks that fall the most in a correction are rarely the ones that lead the next rally. New leaders emerge.",
    ]

    # Try to connect to portfolio context
    portfolio_context = ""
    if ctx.winners:
        w = ctx.winners[0]
        tk = w.get("ticker", w.get("symbol", "???"))
        pnl = w.get("pnl_pct", 0)
        if pnl >= MIN_WIN_THRESHOLD:
            portfolio_context = f"\n\nCONNECTION TO OUR PORTFOLIO:\n${tk} at +{pnl:.1f}% is a live example. Reference it briefly if it naturally connects to the topic."

    topic = random.choice(topics)
    hook = pick_subscribe_hook("DATA_INSIGHT", ctx)

    return f"""Write a DATA_INSIGHT note for {ctx.date_str}.

TOPIC SEED (use as starting point, not verbatim):
{topic}{portfolio_context}

DATA YOU DO NOT HAVE:
  - The exact source study (don't cite a specific paper unless you're certain)
  - Precise percentages beyond what's in the topic seed

Start with the surprising stat or finding. Explain briefly why it matters. If there's a portfolio connection, make it in one sentence. Don't stretch the connection if it doesn't fit naturally.

Close with: "{hook}"
Then: "Not financial advice. Informational only."

150-280 words."""


def build_reader_question_prompt(ctx: NoteContext) -> str:
    """Data-seeded question for genuine engagement."""
    # Build a data seed based on what's available
    data_seeds = []
    if ctx.winners:
        w = ctx.winners[0]
        pnl = w.get("pnl_pct", 0)
        theme = w.get("theme", "")
        if pnl >= MIN_WIN_THRESHOLD and theme:
            data_seeds.append(f"{theme} is up significantly in our portfolio while other sectors lag.")
    if ctx.themes:
        t = ctx.themes[0]
        data_seeds.append(f"Our system scored {t.get('name', 'a theme')} at {t.get('composite_score', 0)}/10 this week.")
    if ctx.scan_stats:
        loaded = ctx.scan_stats.get("tickers_loaded", ctx.scan_stats.get("universe_size", 0))
        green = ctx.scan_stats.get("final_trade", ctx.scan_stats.get("green_signals", 0))
        if loaded > 0:
            data_seeds.append(f"Our scanner rejected {((1 - green / max(loaded, 1)) * 100):.1f}% of stocks this week.")

    seed = random.choice(data_seeds) if data_seeds else "Markets are rotating between sectors."

    return f"""Write a READER_QUESTION note for {ctx.date_str}.

DATA SEED:
{seed}

Write a short note (under 150 words) that:
1. Opens with a blunt observation grounded in the data seed.
2. Adds 1-2 sentences of context.
3. Asks ONE specific question that's easy to reply to.

The question should be grounded in real data, not generic. 
BAD: "What are you watching this week?"
GOOD: "Defence is up 18% in six weeks while AI is flat. Are you rotating or staying put?"

No subscribe hook. This is pure engagement.

End with: "Not financial advice. Informational only."

100-150 words."""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS MAP
# ═══════════════════════════════════════════════════════════════════════════════

PROMPT_BUILDERS = {
    "MARKET_SNAPSHOT": build_market_snapshot_prompt,
    "SIGNAL_DROP": build_signal_drop_prompt,
    "WINNER_RECEIPT": build_winner_receipt_prompt,
    "PORTFOLIO_UPDATE": build_portfolio_update_prompt,
    "THEME_ROTATION": build_theme_rotation_prompt,
    "THE_FILTER": build_the_filter_prompt,
    "CATALYST_WATCH": build_catalyst_watch_prompt,
    "SECTOR_FLOW": build_sector_flow_prompt,
    "EXIT_DEBRIEF": build_exit_debrief_prompt,
    "ALPHA_SCOREBOARD": build_alpha_scoreboard_prompt,
    "DATA_INSIGHT": build_data_insight_prompt,
    "READER_QUESTION": build_reader_question_prompt,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE FALLBACKS (--no-llm mode)
# ═══════════════════════════════════════════════════════════════════════════════

def _tpl_market_snapshot(ctx: NoteContext) -> str:
    lines = [f"SPY {ctx.spy_5d_pct:+.1f}%, QQQ {ctx.qqq_5d_pct:+.1f}%."]
    if ctx.winners:
        w = ctx.winners[0]
        tk = w.get("ticker", w.get("symbol", "???"))
        pnl = w.get("pnl_pct", 0)
        entry = w.get("entry_price", w.get("entry", 0))
        lines.append(f"\n${tk} at {pnl:+.1f}% from our ${entry:.2f} entry. Holding through the noise.")
    lines.append(f"\n{ctx.open_count} positions open.")
    lines.append(f"\n{pick_subscribe_hook('MARKET_SNAPSHOT', ctx)}")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


def _tpl_portfolio_update(ctx: NoteContext) -> str:
    lines = [f"{ctx.open_count} positions open."]
    for p in ctx.winners[:4]:
        tk = p.get("ticker", p.get("symbol", "???"))
        entry = p.get("entry_price", p.get("entry", 0))
        pnl = p.get("pnl_pct", 0)
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        lines.append(f"\n${tk} at {pnl_str} from ${entry:.2f} entry.")
    lines.append(f"\n{pick_subscribe_hook('PORTFOLIO_UPDATE', ctx)}")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


def _tpl_the_filter(ctx: NoteContext) -> str:
    loaded = ctx.scan_stats.get("tickers_loaded", ctx.scan_stats.get("universe_size", 1817))
    green = ctx.scan_stats.get("final_trade", ctx.scan_stats.get("green_signals", 0))
    lines = [f"{loaded} stocks scanned. {green} survived."]
    lines.append(f"\nThe screening system rejected {loaded - green}. That's the edge — selectivity over volume.")
    lines.append(f"\n{pick_subscribe_hook('THE_FILTER', ctx)}")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


def _tpl_theme_rotation(ctx: NoteContext) -> str:
    if ctx.themes:
        t = ctx.themes[0]
        lines = [f"{t.get('name', 'Unknown')} scores {t.get('composite_score', 0)}/10 — classified {t.get('classification', 'N/A')}."]
        thesis = t.get("thesis_summary", "")
        if thesis:
            lines.append(f"\n{thesis[:200]}")
    else:
        lines = ["Tracking sector rotation across our theme universe."]
    lines.append(f"\n{pick_subscribe_hook('THEME_ROTATION', ctx)}")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


def _tpl_data_insight(ctx: NoteContext) -> str:
    lines = ["Momentum has worked in every asset class, every country, every time period tested. It's one of the most robust anomalies in finance."]
    lines.append("\nMost investors know this intellectually but can't execute it emotionally. The system removes the emotion.")
    lines.append(f"\n{pick_subscribe_hook('DATA_INSIGHT', ctx)}")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


def _tpl_reader_question(ctx: NoteContext) -> str:
    seed = ""
    if ctx.themes:
        seed = f"{ctx.themes[0].get('name', 'A theme')} is scoring high in our system."
    lines = [seed or "Markets are rotating."]
    lines.append("\nGenuine question — what sectors are you leaning into this quarter, and what made you decide?")
    lines.append("\nNot financial advice. Informational only.")
    return "\n".join(lines)


TEMPLATE_FALLBACKS = {
    "MARKET_SNAPSHOT": _tpl_market_snapshot,
    "SIGNAL_DROP": _tpl_the_filter,  # Falls back to filter
    "WINNER_RECEIPT": _tpl_portfolio_update,  # Falls back to portfolio
    "PORTFOLIO_UPDATE": _tpl_portfolio_update,
    "THEME_ROTATION": _tpl_theme_rotation,
    "THE_FILTER": _tpl_the_filter,
    "CATALYST_WATCH": _tpl_theme_rotation,  # Falls back to theme
    "SECTOR_FLOW": _tpl_theme_rotation,
    "EXIT_DEBRIEF": _tpl_data_insight,
    "ALPHA_SCOREBOARD": _tpl_portfolio_update,
    "DATA_INSIGHT": _tpl_data_insight,
    "READER_QUESTION": _tpl_reader_question,
}


# ═══════════════════════════════════════════════════════════════════════════════
# HTML WRAPPING (preserved from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def wrap_note_html(markdown_content: str, title: str = "Sterling Signals Note") -> str:
    """Wrap a markdown note in self-contained HTML for Substack."""
    lines = markdown_content.strip().split("\n")
    html_parts = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            continue

        if stripped.lower().startswith("not financial advice"):
            continue

        if stripped.startswith("### "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[4:]
            html_parts.append(f'<h3 style="font-size: 16px; font-weight: 700; margin: 16px 0 8px 0; color: #1a1a1a;">{text}</h3>')
            continue
        if stripped.startswith("## "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[3:]
            html_parts.append(f'<h2 style="font-size: 18px; font-weight: 700; margin: 18px 0 8px 0; color: #1a1a1a;">{text}</h2>')
            continue
        if stripped.startswith("# "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[2:]
            html_parts.append(f'<h1 style="font-size: 20px; font-weight: 700; margin: 20px 0 10px 0; color: #1a1a1a;">{text}</h1>')
            continue

        # Subscribe hook lines (styled as subtle CTA)
        if any(phrase in stripped for phrase in ["Saturday newsletter", "screening drops Friday", "every Saturday", "Monday's open"]):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_parts.append(f'<p style="color: #6b6b6b; font-size: 14px; margin-top: 14px; font-style: italic;">{text}</p>')
            continue

        if not in_paragraph:
            html_parts.append('<p style="margin: 0 0 12px 0;">')
            in_paragraph = True
        else:
            html_parts.append("<br>")

        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        html_parts.append(text)

    if in_paragraph:
        html_parts.append("</p>")

    body_html = "\n".join(html_parts)
    return HTML_NOTE_TEMPLATE.format(title=title, body_html=body_html)


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY GATES (preserved from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def fix_ticker_format(text: str) -> str:
    """Ensure tickers use $TICKER format."""
    text = re.sub(r'(?<!\$)\b([A-Z]{2,5})\b(?=\s+(?:at|is|was|hit|up|down|rose|fell|gained|lost|\+|-|\d))',
                  r'$\1', text)
    return text


def validate_and_repair(
    raw_content: str,
    note_type: str,
    ctx: NoteContext,
    max_repairs: int = 2,
) -> Optional[str]:
    """Validate a note and attempt LLM repair if needed."""
    content = sanitize_note(raw_content)
    content = fix_ticker_format(content)

    if "not financial advice" not in content.lower():
        content = content.rstrip() + "\n\nNot financial advice. Informational only."

    is_valid, issues = validate_note(content)
    if is_valid:
        return content

    for attempt in range(max_repairs):
        print(f"    ⚠ Validation issues: {issues}")
        print(f"    Attempting repair ({attempt + 1}/{max_repairs})...")
        try:
            repaired, repair_cost = repair_note(content, issues, note_type.lower(), ctx)
            repaired = sanitize_note(repaired)
            repaired = fix_ticker_format(repaired)

            if "not financial advice" not in repaired.lower():
                repaired = repaired.rstrip() + "\n\nNot financial advice. Informational only."

            is_valid_2, issues_2 = validate_note(repaired)
            if is_valid_2:
                print(f"    ✓ Repair successful (${repair_cost:.4f})")
                return repaired
            else:
                content = repaired
                issues = issues_2
        except Exception as e:
            print(f"    ✗ Repair error: {e}")
            break

    print(f"    ✗ Repair failed after {max_repairs} attempts. Using template fallback.")
    fallback_fn = TEMPLATE_FALLBACKS.get(note_type)
    if fallback_fn:
        return fallback_fn(ctx)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LLM GENERATION (preserved interface from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_single_note(note_type: str, ctx: NoteContext) -> Tuple[str, float]:
    """Generate a single note via Claude Sonnet. Returns (content, cost)."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed. Use --no-llm.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Use --no-llm.")

    client = anthropic.Anthropic(api_key=api_key)

    builder = PROMPT_BUILDERS.get(note_type)
    if not builder:
        raise ValueError(f"Unknown note type: {note_type}")

    user_prompt = builder(ctx)

    response = client.messages.create(
        model=MODEL_NOTES,
        max_tokens=800,
        system=NOTES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content[0].text.strip()

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    return content, cost


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE (preserved from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def save_note_html(content, day, slot, note_type, html_output=True):
    """Save a note to both current/ and archive/ directories."""
    current_dir, week_dir = ensure_output_dirs()
    date_str = datetime.now().strftime("%Y%m%d")

    if html_output:
        title = f"{day.capitalize()} — {note_type.replace('_', ' ').title()}"
        html_content = wrap_note_html(content, title=title)
        filename = f"note_{slot}_{note_type.lower()}_{date_str}.html"
    else:
        html_content = content
        filename = f"note_{slot}_{note_type.lower()}_{date_str}.md"

    (current_dir / "notes").mkdir(parents=True, exist_ok=True)
    (week_dir / "notes").mkdir(parents=True, exist_ok=True)

    current_path = current_dir / "notes" / filename
    week_path = week_dir / "notes" / filename

    current_path.write_text(html_content)
    week_path.write_text(html_content)

    return current_path


def save_manifest(notes, day):
    """Save notes_manifest.json for today's generated notes."""
    current_dir, week_dir = ensure_output_dirs()

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "day": day,
        "total_notes": len(notes),
        "notes": notes,
    }

    for base_dir in [current_dir, week_dir]:
        manifest_path = base_dir / "notes" / "notes_manifest.json"
        (base_dir / "notes").mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION FLOW (updated with conditional firing + fallbacks)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_notes(
    day: str,
    context: Optional[Dict] = None,
    dry_run: bool = False,
    no_llm: bool = False,
    html_output: bool = True,
) -> List[Dict]:
    """Generate 2-3 notes for today using live context."""
    global _hooks_used_today
    _hooks_used_today = []

    day = day.lower()

    schedule = NOTES_SCHEDULE.get(day, [])
    if not schedule:
        print(f"  No notes scheduled for {day}")
        return []

    # Build NoteContext
    if context is not None:
        ctx = build_note_context_from_daily(context)
    else:
        daily_ctx = load_notes_context_json()
        if daily_ctx:
            ctx = build_note_context_from_daily(daily_ctx)
            print("  ✓ Loaded context from daily_notes_context.json")
        else:
            print("  ℹ No daily_notes_context.json — building fresh context...")
            ctx = build_note_context()

    # Generate each note
    notes = []
    total_cost = 0.0

    for slot, (scheduled_type, time_et) in enumerate(schedule, 1):
        # Resolve conditional types
        actual_type = resolve_note_type(scheduled_type, ctx)
        label = f"Slot {slot} ({actual_type}, {time_et} ET)"
        if actual_type != scheduled_type:
            label += f" [was {scheduled_type}]"

        if dry_run:
            print(f"  [{slot}/{len(schedule)}] {label} — DRY RUN")
            notes.append({
                "type": actual_type,
                "scheduled_type": scheduled_type,
                "slot": slot,
                "time_et": time_et,
                "text": f"[DRY RUN: {actual_type} — {time_et} ET]",
            })
            continue

        print(f"  [{slot}/{len(schedule)}] Generating {label}...")

        content = None
        cost = 0.0

        if no_llm:
            fallback_fn = TEMPLATE_FALLBACKS.get(actual_type)
            if fallback_fn:
                content = fallback_fn(ctx)
                print(f"    Generated via template ({len(content.split())} words)")
            else:
                print(f"    ✗ No template for {actual_type}")
                continue
        else:
            try:
                raw_content, cost = generate_single_note(actual_type, ctx)
                total_cost += cost
                print(f"    Generated via LLM ({len(raw_content.split())} words, ${cost:.4f})")
                content = validate_and_repair(raw_content, actual_type, ctx)
            except Exception as e:
                print(f"    ✗ LLM error: {e}")
                print(f"    Falling back to template...")
                fallback_fn = TEMPLATE_FALLBACKS.get(actual_type)
                if fallback_fn:
                    content = fallback_fn(ctx)
                else:
                    content = None

        if content is None:
            print(f"    ✗ Failed to generate {label}")
            continue

        filepath = save_note_html(content, day, slot, actual_type, html_output=html_output)
        print(f"    ✓ Saved: {filepath.name}")

        notes.append({
            "type": actual_type,
            "scheduled_type": scheduled_type,
            "slot": slot,
            "time_et": time_et,
            "filepath": str(filepath),
            "text": content,
            "word_count": len(content.split()),
            "cost": cost,
        })

    if not dry_run and notes:
        save_manifest(notes, day)

    if total_cost > 0:
        print(f"\n  LLM cost: ${total_cost:.4f}")

    return notes


# ═══════════════════════════════════════════════════════════════════════════════
# CLI (preserved from v1)
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Notes Generator v2")
    parser.add_argument("--day", type=str, default=None, help="Override day (e.g., wednesday)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without LLM or saving")
    parser.add_argument("--no-llm", action="store_true", help="Use template fallback (no API cost)")
    parser.add_argument("--html", action="store_true", default=True, help="HTML output (default)")

    args = parser.parse_args()

    if args.day:
        day = args.day.lower()
    else:
        day = datetime.now().strftime("%A").lower()

    day_title = day.capitalize()
    now = datetime.now()

    print("\n" + "=" * 70)
    print(f"  STERLING SIGNALS — DAILY NOTES GENERATOR v2")
    print(f"  {day_title} {now.strftime('%B %d, %Y')}")
    if getattr(args, 'no_llm', False):
        print("  Mode: TEMPLATE FALLBACK (no LLM)")
    elif getattr(args, 'dry_run', False):
        print("  Mode: DRY RUN (preview only)")
    else:
        print("  Mode: LLM-POWERED (Claude Sonnet)")
    print("=" * 70 + "\n")

    schedule = NOTES_SCHEDULE.get(day, [])
    if not schedule:
        print(f"  No notes scheduled for {day_title}.")
        return 0

    print(f"  Schedule for {day_title}: {len(schedule)} notes")
    for slot, (note_type, time_et) in enumerate(schedule, 1):
        print(f"    Slot {slot} ({time_et} ET): {note_type}")
    print()

    notes = generate_daily_notes(
        day=day,
        dry_run=getattr(args, 'dry_run', False),
        no_llm=getattr(args, 'no_llm', False),
        html_output=getattr(args, 'html', True),
    )

    print(f"\n{'=' * 70}")
    print(f"  {'PREVIEW' if args.dry_run else 'COMPLETE'}: {len(notes)}/{len(schedule)} notes generated")
    print(f"{'=' * 70}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
