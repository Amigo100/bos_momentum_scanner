#!/usr/bin/env python3
"""
SUBSTACK NOTES BATCH GENERATOR
================================

Generates 14-21 Substack Notes per week (2-3/day) across 7 note types,
replacing the old 2-notes-per-week system for maximum organic growth.

Note Types:
    PORTFOLIO_PULSE  — Winner receipts, alpha proof, system validation
    SIGNAL_ALERT     — New signals or selectivity narrative
    THEME_MOMENTUM   — Single theme focus, thesis, catalysts
    MARKET_REACTION  — Quick takes on SPY/QQQ, VIX, rates
    SYSTEM_PROOF     — Funnel stats, discipline, screening narrative
    LEARNING_NUGGET  — Educational content from learning library
    ENGAGEMENT_HOOK  — Community questions, polls, "what are you watching?"

Usage:
    python -m substack.notes_batch_generator                          # Full week (21 notes)
    python -m substack.notes_batch_generator --days 3                 # Next 3 days
    python -m substack.notes_batch_generator --day wednesday          # Single day
    python -m substack.notes_batch_generator --day monday --html      # HTML output for Monday
    python -m substack.notes_batch_generator --html                   # Full week as HTML
    python -m substack.notes_batch_generator --dry-run                # Preview without LLM
    python -m substack.notes_batch_generator --no-llm                 # Template fallback only
"""

import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("Required: pip install yfinance pandas")
    sys.exit(1)

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# ─── Project imports ──────────────────────────────────────────────────────────

from config import (
    BASE_DIR,
    BRANDING,
    MODEL_NOTES,
    get_conviction_text,
    can_show_entry_price,
)
from config.banned_terms import (
    ALL_BANNED,
    CRITICAL_BANNED,
    check_banned_phrases,
    check_loser_focus,
)
from config.banned_terms import validate_content

try:
    from config import MARKETING_THRESHOLDS
except ImportError:
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
    }

MIN_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
BIG_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)

# Shared note utilities (extracted from legacy notes_generator.py)
from substack.note_utils import (
    NoteContext,
    build_note_context,
    sanitize_note,
    validate_note,
    repair_note,
    save_note,
    ensure_output_dirs,
    get_current_dir,
)

# Learning content library (archived — graceful fallback)
try:
    from substack.learning_content_library import (
        LEARNING_TOPICS,
        get_random_topic,
        get_topics_by_category,
    )
except ImportError:
    LEARNING_TOPICS = []
    get_random_topic = lambda **kwargs: None
    get_topics_by_category = lambda *args, **kwargs: []


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

NOTE_TYPES = [
    "PORTFOLIO_PULSE",
    "SIGNAL_ALERT",
    "THEME_MOMENTUM",
    "MARKET_REACTION",
    "SYSTEM_PROOF",
    "LEARNING_NUGGET",
    "ENGAGEMENT_HOOK",
]


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


def wrap_note_html(markdown_content: str, title: str = "Sterling Signals Note") -> str:
    """
    Wrap a markdown note in self-contained HTML for Substack.

    Converts markdown-style content into HTML paragraphs with inline styles.
    Handles common patterns: headers, bold, line breaks, paragraphs.
    """
    import re as _re

    lines = markdown_content.strip().split("\n")
    html_parts = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (paragraph break)
        if not stripped:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            continue

        # Skip the disclaimer line — we add it via the template
        if stripped.lower().startswith("not financial advice"):
            continue

        # Headers
        if stripped.startswith("### "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[4:]
            html_parts.append(
                f'<h3 style="font-size: 16px; font-weight: 700; margin: 16px 0 8px 0; color: #1a1a1a;">{text}</h3>'
            )
            continue
        if stripped.startswith("## "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[3:]
            html_parts.append(
                f'<h2 style="font-size: 18px; font-weight: 700; margin: 18px 0 8px 0; color: #1a1a1a;">{text}</h2>'
            )
            continue
        if stripped.startswith("# "):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = stripped[2:]
            html_parts.append(
                f'<h1 style="font-size: 20px; font-weight: 700; margin: 20px 0 10px 0; color: #1a1a1a;">{text}</h1>'
            )
            continue

        # CTA line (contains "Full analysis" or "Subscribe" or "Sterling Signals")
        if any(phrase in stripped for phrase in ["Full analysis every", "Subscribe to", "Sterling Signals"]):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            # Convert markdown bold
            text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_parts.append(
                f'<p style="color: #6b6b6b; font-size: 14px; margin-top: 14px; font-style: italic;">{text}</p>'
            )
            continue

        # Regular paragraph text
        if not in_paragraph:
            html_parts.append('<p style="margin: 0 0 12px 0;">')
            in_paragraph = True
        else:
            html_parts.append("<br>")

        # Convert markdown bold/italic
        text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
        text = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        html_parts.append(text)

    if in_paragraph:
        html_parts.append("</p>")

    body_html = "\n".join(html_parts)
    return HTML_NOTE_TEMPLATE.format(title=title, body_html=body_html)

# Weekly rotation matrix: day → [(type, post_time_ET)]
WEEKLY_NOTES_SCHEDULE = {
    "saturday":  [("PORTFOLIO_PULSE", "08:30"), ("THEME_MOMENTUM", "12:30"), ("ENGAGEMENT_HOOK", "17:30")],
    "sunday":    [("LEARNING_NUGGET", "09:00"), ("ENGAGEMENT_HOOK", "13:00"), ("MARKET_REACTION", "17:00")],
    "monday":    [("MARKET_REACTION", "08:30"), ("SYSTEM_PROOF", "12:30"), ("PORTFOLIO_PULSE", "17:30")],
    "tuesday":   [("SIGNAL_ALERT", "08:30"), ("THEME_MOMENTUM", "12:30"), ("ENGAGEMENT_HOOK", "17:30")],
    "wednesday": [("MARKET_REACTION", "08:30"), ("PORTFOLIO_PULSE", "12:30"), ("LEARNING_NUGGET", "17:30")],
    "thursday":  [("THEME_MOMENTUM", "08:30"), ("SIGNAL_ALERT", "12:30"), ("ENGAGEMENT_HOOK", "17:30")],
    "friday":    [("MARKET_REACTION", "08:30"), ("SYSTEM_PROOF", "12:30"), ("PORTFOLIO_PULSE", "17:30")],
}

DAY_ORDER = ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

BATCH_NOTES_SYSTEM_PROMPT = """You are the voice of Sterling Signals, a weekly momentum trading newsletter on Substack.

WHO WE ARE:
Three physicians who traded stethoscopes for stock screeners. We built a systematic momentum scanner that screens 1,800+ US stocks through a proprietary screening system — because we believe the same evidence-based rigor that saves lives in medicine can generate alpha in markets. We diagnose momentum the way we once diagnosed patients: systematic screening, pattern recognition, ruling out false positives, and never letting emotion override data.

OUR VOICE:
- Clinical precision meets market conviction. We "triage" setups, "diagnose" trends, and let our system "prescribe" entries and exits.
- We think in probabilities, not certainties. Like differential diagnosis, we weigh evidence and update our outlook as data changes.
- Contrarian by training — medicine taught us to question consensus.
- Process over prediction. Our screening system is our clinical protocol.
- Direct and specific. Every claim comes with a number.

SUBSTACK NOTES FORMAT:
- 150-300 words. Short social posts, NOT articles.
- NO markdown headers (no #, ##). Use line breaks and sparse emoji for structure.
- NO bullet point lists (no •, -, *). Flowing paragraphs and single-line statements only.
- Start with a scroll-stopping hook.
- End with engagement — a question or challenge for the community.
- $TICKER format with price or percentage when mentioning stocks.

MARKETING RULES (CRITICAL):
- "GREEN signal" for buys. NEVER use: TEAL, PASS, VIOLET, AMBER.
- NEVER use: HMA, RSI, MACD, KDJ, Banker, UC, Undercurrent, BoS, ExD, profit lock, tiered stop, Gatekeeper, Investment Gate, conviction 1-10, Tier 1/2/3, Roth IRA, PDT.
- System: "proprietary screening system" or "our screening system".
- Conviction: "Extremely Bullish" / "Bullish" / "Watching" — NEVER numbers.
- NEVER mention losing positions or negative P&L.
- Only show entry prices for closed winners or positions with 25%+ gain.
- Only highlight positions with 15%+ gains.

Always end with: "Not financial advice. Informational only."
"""


# ═══════════════════════════════════════════════════════════════════════════════
# ENGAGEMENT HOOKS (expanded — 60+ hooks across all note types)
# ═══════════════════════════════════════════════════════════════════════════════

ENGAGEMENT_HOOKS = {
    "PORTFOLIO_PULSE": [
        "What themes are driving your portfolio right now?",
        "Are you seeing alpha in the same sectors we are?",
        "How are you positioning for the rest of this quarter?",
        "Which of your positions has surprised you the most?",
        "What is your screening system telling you this week?",
        "Are you outperforming the index? If so, what is driving it?",
        "How do you decide when to let a winner run vs take profits?",
        "What does your portfolio tell you about where money is flowing?",
    ],
    "SIGNAL_ALERT": [
        "Would you take this trade? Why or why not?",
        "How selective is your screening process?",
        "What is the best signal your system has generated this year?",
        "How do you handle weeks with no clean signals?",
        "What criteria separate a great setup from a good one?",
        "Do you stay disciplined when the system says no?",
        "What makes you override a signal from your system?",
        "Have you ever passed on a signal and regretted it?",
    ],
    "THEME_MOMENTUM": [
        "Is anyone else noticing this theme gaining momentum?",
        "Which themes are on your radar right now?",
        "Have you noticed this sector rotation pattern?",
        "What themes do you think are overhyped vs underappreciated?",
        "Where do you see institutional money flowing next?",
        "Do you agree with our read on this sector?",
        "What is the next multi-year theme that nobody is talking about?",
        "Are you positioned for this theme or waiting on the sidelines?",
    ],
    "MARKET_REACTION": [
        "How are you reading today's market action?",
        "What does the breadth data tell you about this move?",
        "Is this a rotation you are leaning into or fading?",
        "How are you managing risk in this environment?",
        "What is the market telling us that headlines are not?",
        "Do you see this as a pullback to buy or a reason to reduce?",
        "How important is the VIX level for your decision-making?",
        "What is your framework for navigating choppy weeks?",
    ],
    "SYSTEM_PROOF": [
        "Do you track your screening rejection rate?",
        "What is the most important filter in your system?",
        "How does your process handle crowded trades?",
        "What gives you confidence in your screening methodology?",
        "How do you measure whether your system is working?",
        "What would make you change your screening criteria?",
        "Do you believe in systematic or discretionary approaches?",
        "What is the hardest part about trusting a process?",
    ],
    "LEARNING_NUGGET": [
        "What is one concept that changed how you invest?",
        "How do you apply this principle in your own process?",
        "What was the most expensive lesson you ever learned in markets?",
        "Did you know this before you started investing?",
        "How would you explain this concept to a beginner?",
        "What is one book or resource that shaped your investment approach?",
        "How do you think about risk differently from most investors?",
        "What framework helps you stay disciplined?",
    ],
    "ENGAGEMENT_HOOK": [
        "What are you watching this week?",
        "Quick poll: what is your biggest position right now?",
        "One word to describe the current market. Go.",
        "What is the best trade you have made in the last 90 days?",
        "Agree or disagree: small caps will outperform large caps this year.",
        "What sector are you most bullish on for the rest of 2026?",
        "Name a stock under $25 that nobody is talking about.",
        "What is your number one rule for managing risk?",
        "If you could only hold 5 stocks, what would they be?",
        "What advice would you give to your investing self from 3 years ago?",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUP TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DedupTracker:
    """Track tickers, themes, and hooks used across the batch to prevent repetition."""
    tickers_used: Dict[str, int] = field(default_factory=dict)   # ticker → count
    themes_used: Dict[str, int] = field(default_factory=dict)    # theme → count
    hooks_used: List[str] = field(default_factory=list)          # hooks already picked
    topics_used: List[str] = field(default_factory=list)         # learning topic IDs used
    last_day_tickers: List[str] = field(default_factory=list)    # tickers in previous note today

    MAX_TICKER_PER_WEEK = 3
    MAX_THEME_PER_WEEK = 4

    def can_use_ticker(self, ticker: str) -> bool:
        return self.tickers_used.get(ticker, 0) < self.MAX_TICKER_PER_WEEK

    def can_use_theme(self, theme: str) -> bool:
        return self.themes_used.get(theme, 0) < self.MAX_THEME_PER_WEEK

    def record_ticker(self, ticker: str):
        self.tickers_used[ticker] = self.tickers_used.get(ticker, 0) + 1

    def record_theme(self, theme: str):
        self.themes_used[theme] = self.themes_used.get(theme, 0) + 1

    def pick_hook(self, note_type: str) -> str:
        """Pick an engagement hook not yet used this batch."""
        available = ENGAGEMENT_HOOKS.get(note_type, ENGAGEMENT_HOOKS["ENGAGEMENT_HOOK"])
        unused = [h for h in available if h not in self.hooks_used]
        if not unused:
            # All used — reset and pick from full list
            unused = available
        hook = random.choice(unused)
        self.hooks_used.append(hook)
        return hook

    def pick_learning_topic(self):
        """Pick a learning topic not yet used this batch."""
        topic = get_random_topic(exclude_ids=self.topics_used)
        if topic:
            self.topics_used.append(topic.id)
        return topic

    def start_new_day(self):
        """Reset same-day adjacency tracker."""
        self.last_day_tickers = []


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE SPEC
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NoteSpec:
    """Specification for a single note to generate."""
    day: str                # e.g. "wednesday"
    slot: int               # 1, 2, or 3
    note_type: str          # e.g. "PORTFOLIO_PULSE"
    post_time: str          # e.g. "08:30"
    filename: str = ""      # e.g. "wednesday_1_market_reaction.md"
    html_output: bool = False  # When True, output .html instead of .md

    def __post_init__(self):
        if not self.filename:
            ext = ".html" if self.html_output else ".md"
            self.filename = f"{self.day}_{self.slot}_{self.note_type.lower()}{ext}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS (one per note type)
# ═══════════════════════════════════════════════════════════════════════════════

def build_portfolio_pulse_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Winner receipts, benchmark alpha, system validation."""
    # Select winners respecting dedup
    available_winners = []
    for w in ctx.winners:
        ticker = w.get('ticker', '')
        if dedup.can_use_ticker(ticker) and ticker not in dedup.last_day_tickers:
            available_winners.append(w)

    winners_text = "No positions above 15% gain currently."
    if available_winners:
        lines = []
        for w in available_winners[:4]:
            entry_info = ""
            if can_show_entry_price(w):
                entry_info = f" (entry ${w['entry_price']:.2f})"
            theme = w.get('theme', '')
            theme_info = f" — {theme}" if theme else ""
            lines.append(f"${w['ticker']} at +{w['pnl_pct']:.1f}%{theme_info}{entry_info}")
            dedup.record_ticker(w['ticker'])
            dedup.last_day_tickers.append(w['ticker'])
        winners_text = "\n".join(lines)

    hook = dedup.pick_hook("PORTFOLIO_PULSE")

    return f"""Write a "Portfolio Pulse" Substack Note ({ctx.date_str}).

MARKET CONTEXT:
SPY 5-day: {ctx.spy_5d_pct:+.1f}%  |  QQQ 5-day: {ctx.qqq_5d_pct:+.1f}%

PORTFOLIO:
Open positions: {ctx.open_count}

WINNERS (15%+ gains — the ONLY positions you may mention):
{winners_text}

INSTRUCTIONS:
1. Lead with a winner receipt or alpha number. Make it concrete — the number IS the hook.
2. Weave 1-3 winners into flowing prose. Frame as system validation: "The screening system diagnosed this early."
3. Compare to SPY/QQQ if we are outperforming — show the alpha gap.
4. Keep it clinical and confident, not boastful. "The data was clear. We followed protocol."
5. End with this engagement question (rephrase naturally): "{hook}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs. Medical-investor voice."""


def build_signal_alert_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """New signals or selectivity narrative."""
    if ctx.pass_signals:
        # Pick a signal respecting dedup
        sig = None
        for s in ctx.pass_signals:
            if dedup.can_use_ticker(s['symbol']) and s['symbol'] not in dedup.last_day_tickers:
                sig = s
                break
        if not sig:
            sig = ctx.pass_signals[0]

        bullish = sig.get('bullish_factors', [])
        bullish_text = ", ".join(bullish[:3]) if bullish else "Multiple factors aligned."
        conv_text = get_conviction_text(sig.get('conviction', 0))
        dedup.record_ticker(sig['symbol'])
        dedup.last_day_tickers.append(sig['symbol'])

        signal_section = f"""CONTENT PATH: NEW GREEN SIGNAL

Signal: ${sig['symbol']}
Theme: {sig.get('theme', 'N/A')}
Outlook: {conv_text}
Bullish factors: {bullish_text}
Total GREEN signals this week: {len(ctx.pass_signals)}

Focus on what the system diagnosed: theme alignment, structural confirmation, institutional accumulation patterns."""
    else:
        # Selectivity narrative
        past_winner_text = ""
        if ctx.winners:
            pw = ctx.winners[0]
            past_winner_text = f"\nReference: ${pw['ticker']} at +{pw['pnl_pct']:.1f}% shows the system works when it fires."

        signal_section = f"""CONTENT PATH: SELECTIVITY (NO NEW SIGNALS)

Scan stats: {ctx.scan_stats.get('tickers_loaded', 1817)} stocks scanned → {ctx.scan_stats.get('technical_signals', 0)} passed technicals → 0 cleared every screening stage.
{past_winner_text}
Frame zero signals as a FEATURE. A good doctor does not prescribe when there is nothing to treat. Our system does the same."""

    hook = dedup.pick_hook("SIGNAL_ALERT")

    return f"""Write a "Signal Alert" Substack Note ({ctx.date_str}).

{signal_section}

INSTRUCTIONS:
1. Open with a scroll-stopping hook about what the system just diagnosed (or chose NOT to prescribe).
2. Use medical-analytical lens: "The chart showed symptoms of..." or "Our screening triaged 1,800 stocks and..."
3. Be specific with numbers — funnel stats, theme alignment, what made this pass (or fail) our gates.
4. End with: "{hook}"
5. Close with: "Full analysis every Saturday in Sterling Signals."
6. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_theme_momentum_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """One theme per note — thesis, catalysts, momentum."""
    # Pick a theme respecting dedup
    theme = None
    for t in ctx.themes:
        name = t.get('name', '')
        if dedup.can_use_theme(name):
            theme = t
            break
    if not theme and ctx.themes:
        theme = ctx.themes[0]

    if theme:
        name = theme.get('name', 'Unknown')
        classification = theme.get('classification', 'N/A')
        score = theme.get('composite_score', 0)
        thesis = theme.get('thesis_summary', 'Theme momentum building.')
        catalysts = theme.get('key_catalysts', [])
        catalysts_text = "; ".join(catalysts[:3]) if catalysts else "Multiple catalysts converging."

        dedup.record_theme(name)

        # Find tickers in this theme
        theme_tickers = []
        for w in ctx.winners:
            if w.get('theme', '') == name and dedup.can_use_ticker(w['ticker']):
                theme_tickers.append(w)
        ticker_text = ""
        if theme_tickers:
            parts = []
            for t in theme_tickers[:2]:
                dedup.record_ticker(t['ticker'])
                dedup.last_day_tickers.append(t['ticker'])
                parts.append(f"${t['ticker']} +{t['pnl_pct']:.1f}%")
            ticker_text = f"\nOur positions in this theme: {', '.join(parts)}"

        theme_section = f"""Theme: {name}
Classification: {classification}
Score: {score}/10
Thesis: {thesis}
Key catalysts: {catalysts_text}{ticker_text}"""
    else:
        theme_section = """No scored themes available. Write about sector rotation in general — where institutional money appears to be flowing based on market breadth and recent strength."""

    hook = dedup.pick_hook("THEME_MOMENTUM")

    return f"""Write a "Theme Momentum" Substack Note ({ctx.date_str}).

{theme_section}

INSTRUCTIONS:
1. Open with a strong observation about this theme's momentum — make it feel like a diagnosis.
2. Explain the thesis in 2-3 sentences: WHY is capital flowing here?
3. Name 1-2 catalysts on the horizon that could accelerate (or decelerate) this theme.
4. If we have positions, mention them as validation — "Our screening system prescribed exposure early."
5. End with: "{hook}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_market_reaction_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Quick takes on SPY/QQQ, VIX, rates, rotation."""
    market_excerpt = ctx.market_analysis_excerpt or "Market data unavailable."

    hook = dedup.pick_hook("MARKET_REACTION")

    return f"""Write a "Market Reaction" Substack Note ({ctx.date_str}).

MARKET DATA:
SPY 5-day: {ctx.spy_5d_pct:+.1f}%
QQQ 5-day: {ctx.qqq_5d_pct:+.1f}%

MARKET ANALYSIS EXCERPT:
{market_excerpt}

OUR PORTFOLIO:
{ctx.open_count} open positions

INSTRUCTIONS:
1. Open with a punchy observation about what the market just told us — like a doctor reading vitals.
2. Reference SPY and QQQ performance with specific numbers.
3. Comment on what this means for momentum stocks, small caps, or sector rotation.
4. Add one forward-looking remark: what are we watching next?
5. Do NOT mention any specific positions or tickers unless they are 15%+ winners.
6. End with: "{hook}"
7. Close with: "Full analysis every Saturday in Sterling Signals."
8. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_system_proof_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Funnel stats, discipline, screening narrative."""
    tickers_loaded = ctx.scan_stats.get('tickers_loaded', 1817)
    tech_signals = ctx.scan_stats.get('technical_signals', 0)
    final_trade = ctx.scan_stats.get('final_trade', 0)
    final_consider = ctx.scan_stats.get('final_consider', 0)

    winner_proof = ""
    if ctx.winners:
        w = ctx.winners[0]
        winner_proof = f"\nProof it works: ${w['ticker']} at +{w['pnl_pct']:.1f}% — diagnosed by the same screening system."

    hook = dedup.pick_hook("SYSTEM_PROOF")

    return f"""Write a "System Proof" Substack Note ({ctx.date_str}).

SCREENING FUNNEL:
{tickers_loaded} stocks scanned
→ {tech_signals} passed technical screening
→ {final_trade} cleared every screening stage (GREEN signals)
→ {final_consider} on watchlist

Rejection rate: {((1 - final_trade / max(tickers_loaded, 1)) * 100):.1f}%
{winner_proof}
INSTRUCTIONS:
1. Open with the funnel numbers — they ARE the hook. "{tickers_loaded} stocks. {final_trade} survived."
2. Frame our selectivity as a competitive advantage. Most traders chase setups; our system rejects 99%+.
3. Use a medical metaphor: "A screening test that catches everything is useless. Specificity is what matters."
4. If winner proof exists, reference it as validation of the screening process.
5. End with: "{hook}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_learning_nugget_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Educational content drawn from learning content library."""
    topic = dedup.pick_learning_topic()

    if topic:
        return f"""Write an educational Substack Note based on this topic ({ctx.date_str}).

TOPIC: {topic.title}
CATEGORY: {topic.category}

HOOK (use as inspiration for your opening):
{topic.hook}

KEY CONCEPT:
{topic.key_concept}

EXAMPLE:
{topic.example}

ENGAGEMENT QUESTION:
{topic.engagement_question}

INSTRUCTIONS:
1. Open with the hook or a variation of it — make it scroll-stopping.
2. Teach the key concept in 2-3 flowing paragraphs. No jargon, no textbook tone.
3. Use the example to make it concrete and relatable.
4. Frame it through our medical-investor lens where natural: "Like a diagnostic protocol..."
5. End with the engagement question.
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""
    else:
        # Fallback: generic educational topic
        hook = dedup.pick_hook("LEARNING_NUGGET")
        return f"""Write an educational Substack Note about position sizing and risk management ({ctx.date_str}).

Teach one concept about why position sizing matters more than stock picking. Use a medical analogy: "A surgeon does not treat every patient the same way — dosage matters."

End with: "{hook}"
Close with: "Full analysis every Saturday in Sterling Signals."
Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_engagement_hook_prompt(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Community questions, polls, open discussion."""
    hook = dedup.pick_hook("ENGAGEMENT_HOOK")

    # Pick a light data point to seed the conversation
    data_seed = ""
    if ctx.winners:
        w = ctx.winners[0]
        data_seed = f"Our top performer ${w['ticker']} is at +{w['pnl_pct']:.1f}%. "
    elif ctx.themes:
        t = ctx.themes[0]
        data_seed = f"Our system scored {t.get('name', 'a theme')} at {t.get('composite_score', 0)}/10 this week. "

    return f"""Write a short, engagement-focused Substack Note ({ctx.date_str}).

This note is designed to start a conversation. Keep it UNDER 200 words.

DATA SEED (optional — use if it naturally fits):
{data_seed}

CORE QUESTION:
{hook}

INSTRUCTIONS:
1. Open with a bold statement, quick observation, or contrarian take (1-2 sentences max).
2. Add 1-2 sentences of context that make the question relevant right now.
3. Ask the engagement question clearly — make it easy to answer.
4. Do NOT write a mini-article. This is a conversation starter, not an essay.
5. Close with: "Full analysis every Saturday in Sterling Signals."
6. Final line: "Not financial advice. Informational only."

100-200 words. No markdown headers. No bullet lists. Conversational and direct."""


# Map note types to prompt builders
PROMPT_BUILDERS = {
    "PORTFOLIO_PULSE": build_portfolio_pulse_prompt,
    "SIGNAL_ALERT": build_signal_alert_prompt,
    "THEME_MOMENTUM": build_theme_momentum_prompt,
    "MARKET_REACTION": build_market_reaction_prompt,
    "SYSTEM_PROOF": build_system_proof_prompt,
    "LEARNING_NUGGET": build_learning_nugget_prompt,
    "ENGAGEMENT_HOOK": build_engagement_hook_prompt,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE FALLBACKS (--no-llm)
# ═══════════════════════════════════════════════════════════════════════════════

def template_portfolio_pulse(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for PORTFOLIO_PULSE notes."""
    lines = []
    lines.append(f"Portfolio update — {ctx.date_str}")
    lines.append("")

    if ctx.winners:
        w = ctx.winners[0]
        entry_info = ""
        if can_show_entry_price(w):
            entry_info = f" from a ${w['entry_price']:.2f} entry"
        lines.append(f"${w['ticker']} is running at +{w['pnl_pct']:.1f}%{entry_info}. Our screening system diagnosed this setup early and the thesis is playing out.")
        lines.append("")
        if len(ctx.winners) > 1:
            w2 = ctx.winners[1]
            lines.append(f"${w2['ticker']} is also delivering at +{w2['pnl_pct']:.1f}%. The system continues to identify structural momentum before the crowd.")
            lines.append("")

    lines.append(f"With {ctx.open_count} positions open, the portfolio is navigating this market with systematic discipline.")
    lines.append("")
    hook = dedup.pick_hook("PORTFOLIO_PULSE")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_signal_alert(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for SIGNAL_ALERT notes."""
    lines = []

    if ctx.pass_signals:
        sig = ctx.pass_signals[0]
        lines.append(f"GREEN signal on ${sig['symbol']} — our screening system just cleared this setup.")
        lines.append("")
        lines.append(f"Theme alignment: {sig.get('theme', 'N/A')}. The screening system identified structural momentum confirmation and institutional accumulation patterns that suggest this is more than noise.")
        lines.append("")
        lines.append(f"Out of {ctx.scan_stats.get('tickers_loaded', 1817)} stocks scanned, {len(ctx.pass_signals)} made it through every screening stage this week.")
    else:
        loaded = ctx.scan_stats.get('tickers_loaded', 1817)
        tech = ctx.scan_stats.get('technical_signals', 0)
        lines.append(f"{loaded} stocks scanned. Zero new GREEN signals.")
        lines.append("")
        lines.append(f"Only {tech} passed the initial technical screen. None cleared every screening stage. That is the system working as designed — a screening test with high specificity rejects noise.")
        if ctx.winners:
            w = ctx.winners[0]
            lines.append("")
            lines.append(f"Meanwhile, ${w['ticker']} continues to run at +{w['pnl_pct']:.1f}%. Patience pays when the system is right.")

    lines.append("")
    hook = dedup.pick_hook("SIGNAL_ALERT")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_theme_momentum(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for THEME_MOMENTUM notes."""
    lines = []

    if ctx.themes:
        t = ctx.themes[0]
        name = t.get('name', 'Unknown')
        score = t.get('composite_score', 0)
        classification = t.get('classification', 'N/A')
        thesis = t.get('thesis_summary', 'Momentum building across this sector.')

        lines.append(f"{name} scores {score}/10 in our sector flow analysis — classified as {classification}.")
        lines.append("")
        lines.append(thesis[:200])
        lines.append("")

        catalysts = t.get('key_catalysts', [])
        if catalysts:
            lines.append(f"Key catalysts: {'; '.join(catalysts[:2])}.")
            lines.append("")

        dedup.record_theme(name)
    else:
        lines.append("Sector rotation continues to create opportunities for systematic investors who track institutional flows.")
        lines.append("")
        lines.append("Our screening system maps capital movement across themes — identifying where the smart money is positioning before it becomes consensus.")
        lines.append("")

    hook = dedup.pick_hook("THEME_MOMENTUM")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_market_reaction(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for MARKET_REACTION notes."""
    lines = []
    lines.append(f"Market vitals — SPY {ctx.spy_5d_pct:+.1f}%, QQQ {ctx.qqq_5d_pct:+.1f}% over the last 5 sessions.")
    lines.append("")
    lines.append("The question is not what the market did, but what it is telling us about where capital is rotating next.")
    lines.append("")
    lines.append(f"With {ctx.open_count} positions open, we are watching breadth, sector strength, and our screening system for the next structural signal.")
    lines.append("")
    hook = dedup.pick_hook("MARKET_REACTION")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_system_proof(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for SYSTEM_PROOF notes."""
    loaded = ctx.scan_stats.get('tickers_loaded', 1817)
    tech = ctx.scan_stats.get('technical_signals', 0)
    final = ctx.scan_stats.get('final_trade', 0)

    lines = []
    lines.append(f"{loaded} stocks. {final} survived every screening stage.")
    lines.append("")
    lines.append(f"Our screening system rejected {loaded - final} setups this week. That is not a failure — that is specificity working exactly as designed.")
    lines.append("")
    lines.append("Like a diagnostic test, the value is not in what it catches — it is in what it correctly rules out. Most traders chase every setup. Our system is built to wait.")
    lines.append("")

    if ctx.winners:
        w = ctx.winners[0]
        lines.append(f"The proof? ${w['ticker']} at +{w['pnl_pct']:.1f}%. Diagnosed by the same screening system that says no to 99% of what it screens.")
        lines.append("")

    hook = dedup.pick_hook("SYSTEM_PROOF")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_learning_nugget(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for LEARNING_NUGGET notes."""
    topic = dedup.pick_learning_topic()

    if topic:
        return topic.note_template
    else:
        # Generic fallback
        lines = []
        lines.append("Position sizing is the most underrated skill in investing.")
        lines.append("")
        lines.append("A surgeon does not administer the same dosage to every patient. The treatment depends on the diagnosis, the risk profile, and the patient's history. Investing works the same way.")
        lines.append("")
        lines.append("High conviction? Larger position. Speculative? Smaller allocation. The math of compounding rewards discipline more than it rewards boldness.")
        lines.append("")
        lines.append("What is one concept that changed how you size your positions?")
        lines.append("")
        lines.append("Full analysis every Saturday in Sterling Signals.")
        lines.append("")
        lines.append("Not financial advice. Informational only.")
        return "\n".join(lines)


def template_engagement_hook(ctx: NoteContext, dedup: DedupTracker) -> str:
    """Template fallback for ENGAGEMENT_HOOK notes."""
    hook = dedup.pick_hook("ENGAGEMENT_HOOK")

    data_seed = ""
    if ctx.winners:
        w = ctx.winners[0]
        data_seed = f"Our top performer ${w['ticker']} is at +{w['pnl_pct']:.1f}% and climbing."

    lines = []
    if data_seed:
        lines.append(data_seed)
        lines.append("")
    lines.append("The market never stops teaching. Every week we learn something new about how capital flows, how themes rotate, and how discipline separates consistent performers from the crowd.")
    lines.append("")
    lines.append(hook)
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


TEMPLATE_FALLBACKS = {
    "PORTFOLIO_PULSE": template_portfolio_pulse,
    "SIGNAL_ALERT": template_signal_alert,
    "THEME_MOMENTUM": template_theme_momentum,
    "MARKET_REACTION": template_market_reaction,
    "SYSTEM_PROOF": template_system_proof,
    "LEARNING_NUGGET": template_learning_nugget,
    "ENGAGEMENT_HOOK": template_engagement_hook,
}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_note_llm(spec: NoteSpec, ctx: NoteContext, dedup: DedupTracker) -> Tuple[str, float]:
    """Generate a single note via Claude Sonnet. Returns (content, cost)."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed. Use --no-llm.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Use --no-llm.")

    client = anthropic.Anthropic(api_key=api_key)

    builder = PROMPT_BUILDERS.get(spec.note_type)
    if not builder:
        raise ValueError(f"Unknown note type: {spec.note_type}")

    user_prompt = builder(ctx, dedup)

    response = client.messages.create(
        model=MODEL_NOTES,
        max_tokens=800,
        system=BATCH_NOTES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content[0].text.strip()

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    return content, cost


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════════

def save_manifest(notes: List[Dict], output_dir: Path):
    """Save notes_manifest.json tracking all generated notes."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "week_number": datetime.now().isocalendar().week,
        "total_notes": len(notes),
        "notes": notes,
    }

    manifest_path = output_dir / "substack_notes" / "notes_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    return manifest_path


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def build_note_specs(
    days: Optional[List[str]] = None,
    html_output: bool = False,
) -> List[NoteSpec]:
    """Build list of NoteSpec objects for requested days."""
    if days is None:
        days = DAY_ORDER  # Full week

    specs = []
    for day in days:
        day_lower = day.lower()
        if day_lower not in WEEKLY_NOTES_SCHEDULE:
            print(f"  Warning: Unknown day '{day}', skipping.")
            continue

        slots = WEEKLY_NOTES_SCHEDULE[day_lower]
        for i, (note_type, post_time) in enumerate(slots, 1):
            specs.append(NoteSpec(
                day=day_lower,
                slot=i,
                note_type=note_type,
                post_time=post_time,
                html_output=html_output,
            ))

    return specs


def generate_batch(
    days: Optional[List[str]] = None,
    no_llm: bool = False,
    dry_run: bool = False,
    html_output: bool = False,
) -> Dict[str, Path]:
    """
    Generate a batch of Substack Notes.

    Args:
        days: List of day names to generate for (default: full week).
        no_llm: Use template fallback (no API cost).
        dry_run: Print to stdout, don't save.
        html_output: Output notes as .html files instead of .md.

    Returns:
        Dict of {filename: path} for generated files.
    """
    print("\n" + "=" * 70)
    print("  SUBSTACK NOTES BATCH GENERATOR")
    if no_llm:
        print("  Mode: TEMPLATE FALLBACK (no LLM)")
    else:
        print("  Mode: LLM-POWERED (Claude Sonnet)")
    if html_output:
        print("  Output: HTML files")
    print("=" * 70)

    # Build specs
    specs = build_note_specs(days, html_output=html_output)
    print(f"\n  Notes to generate: {len(specs)}")
    for spec in specs:
        print(f"    {spec.day.capitalize():12s} Slot {spec.slot}: {spec.note_type:20s} ({spec.post_time} ET)")

    # Ensure output directories
    current_dir, week_dir = ensure_output_dirs()
    if not dry_run:
        print(f"\n  Output directories:")
        print(f"    Current: {current_dir}/substack_notes/")
        print(f"    Archive: {week_dir}/substack_notes/")

    # Build context (shared across all notes)
    print("\n  Building context...")
    ctx = build_note_context()

    # Initialize dedup tracker
    dedup = DedupTracker()

    results = {}
    manifest_entries = []
    total_cost = 0.0
    generated = 0
    failed = 0

    current_day = None

    for spec in specs:
        # Reset same-day adjacency when moving to a new day
        if spec.day != current_day:
            dedup.start_new_day()
            current_day = spec.day

        label = f"{spec.day.capitalize()} #{spec.slot} ({spec.note_type})"
        print(f"\n  [{generated + failed + 1}/{len(specs)}] Generating {label}...")

        content = None
        cost = 0.0

        if no_llm:
            # Template fallback
            fallback_fn = TEMPLATE_FALLBACKS.get(spec.note_type)
            if fallback_fn:
                content = fallback_fn(ctx, dedup)
                print(f"    Generated via template ({len(content.split())} words)")
            else:
                print(f"    ✗ No template for {spec.note_type}")
                failed += 1
                continue
        else:
            # LLM generation with validation + repair loop
            try:
                raw_content, cost = generate_note_llm(spec, ctx, dedup)
                total_cost += cost
                content = sanitize_note(raw_content)
                print(f"    Generated via LLM ({len(content.split())} words, ${cost:.4f})")

                # Validate
                is_valid, issues = validate_note(content)

                if not is_valid:
                    print(f"    ⚠️  Validation issues: {issues}")
                    print(f"    Attempting repair...")

                    try:
                        repaired, repair_cost = repair_note(
                            content, issues, spec.note_type.lower(), ctx
                        )
                        total_cost += repair_cost
                        repaired = sanitize_note(repaired)

                        is_valid_2, issues_2 = validate_note(repaired)
                        if is_valid_2:
                            content = repaired
                            print(f"    ✓ Repair successful (${repair_cost:.4f})")
                        else:
                            print(f"    ✗ Repair failed: {issues_2}")
                            print(f"    Falling back to template...")
                            fallback_fn = TEMPLATE_FALLBACKS.get(spec.note_type)
                            if fallback_fn:
                                content = fallback_fn(ctx, dedup)
                            else:
                                content = None
                    except Exception as e:
                        print(f"    ✗ Repair error: {e}")
                        fallback_fn = TEMPLATE_FALLBACKS.get(spec.note_type)
                        if fallback_fn:
                            content = fallback_fn(ctx, dedup)
                        else:
                            content = None
                else:
                    print(f"    ✓ Validation passed")

            except Exception as e:
                print(f"    ✗ LLM error: {e}")
                print(f"    Falling back to template...")
                fallback_fn = TEMPLATE_FALLBACKS.get(spec.note_type)
                if fallback_fn:
                    content = fallback_fn(ctx, dedup)
                else:
                    content = None

        if content is None:
            print(f"    ✗ Failed to generate {label}")
            failed += 1
            continue

        # Wrap in HTML if requested
        if html_output and content:
            title = f"{spec.day.capitalize()} — {spec.note_type.replace('_', ' ').title()}"
            content = wrap_note_html(content, title=title)

        # Output
        if dry_run:
            print(f"\n{'─' * 60}")
            print(f"  {label} — DRY RUN PREVIEW")
            print(f"{'─' * 60}")
            print(content)
            print(f"{'─' * 60}")
        else:
            current_path, week_path = save_note(
                content, spec.filename, current_dir, week_dir
            )
            results[spec.filename] = current_path
            print(f"    ✓ Saved: {spec.filename}")

        # Track in manifest
        manifest_entries.append({
            "day": spec.day,
            "slot": spec.slot,
            "note_type": spec.note_type,
            "post_time": spec.post_time,
            "filename": spec.filename,
            "word_count": len(content.split()),
            "cost": cost,
        })

        generated += 1

    # Save manifest
    if not dry_run and manifest_entries:
        manifest_path = save_manifest(manifest_entries, current_dir)
        # Also save to week archive
        save_manifest(manifest_entries, week_dir)
        print(f"\n  Manifest: {manifest_path}")

    # Also generate legacy tuesday/thursday notes for backward compatibility
    if not dry_run and days is None:
        _generate_legacy_notes(ctx, dedup, current_dir, week_dir, no_llm, html_output=html_output)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  BATCH {'PREVIEW' if dry_run else 'COMPLETE'}")
    print(f"{'=' * 70}")
    print(f"  Generated: {generated}/{len(specs)} notes")
    if failed:
        print(f"  Failed:    {failed}")
    if total_cost > 0:
        print(f"  LLM Cost:  ${total_cost:.4f}")

    if not dry_run and results:
        print(f"\n  Files ready for Substack:")
        for filename, path in sorted(results.items()):
            print(f"    {filename}")

    # Dedup summary
    if dedup.tickers_used:
        print(f"\n  Ticker frequency:")
        for ticker, count in sorted(dedup.tickers_used.items(), key=lambda x: -x[1]):
            print(f"    ${ticker}: {count}x")
    if dedup.themes_used:
        print(f"\n  Theme frequency:")
        for theme, count in sorted(dedup.themes_used.items(), key=lambda x: -x[1]):
            print(f"    {theme}: {count}x")

    print("")

    return results


def _generate_legacy_notes(
    ctx: NoteContext,
    dedup: DedupTracker,
    current_dir: Path,
    week_dir: Path,
    no_llm: bool,
    html_output: bool = False,
):
    """Generate legacy tuesday_note.md and thursday_note.md for backward compatibility."""
    ext = ".html" if html_output else ".md"
    # Look for the tuesday and thursday notes in the batch output
    for day, legacy_base in [("tuesday", "tuesday_note"), ("thursday", "thursday_note")]:
        legacy_name = f"{legacy_base}{ext}"
        # Find the first note for that day
        day_slots = WEEKLY_NOTES_SCHEDULE.get(day, [])
        if day_slots:
            note_type = day_slots[0][0]  # First slot of the day
            batch_name = f"{day}_1_{note_type.lower()}{ext}"
            batch_path = current_dir / "substack_notes" / batch_name

            if batch_path.exists():
                content = batch_path.read_text()
                # Save as legacy name
                legacy_current = current_dir / "substack_notes" / legacy_name
                legacy_week = week_dir / "substack_notes" / legacy_name
                legacy_current.write_text(content)
                legacy_week.write_text(content)
                print(f"  Legacy compat: {legacy_name} → copied from {batch_name}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Substack Notes batch (2-3/day, 21/week)"
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="Generate for next N days (default: full week)"
    )
    parser.add_argument(
        "--day", type=str, default=None,
        help="Generate for a single day (e.g. wednesday)"
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Use template fallback (no API cost)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output without saving"
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Output notes as self-contained HTML files instead of Markdown"
    )

    args = parser.parse_args()

    # Determine which days to generate
    if args.day:
        days = [args.day.lower()]
    elif args.days:
        # Next N days starting from today
        today = datetime.now()
        days = []
        for i in range(args.days):
            d = today + timedelta(days=i)
            days.append(d.strftime("%A").lower())
    else:
        days = None  # Full week

    generate_batch(
        days=days,
        no_llm=getattr(args, 'no_llm', False),
        dry_run=getattr(args, 'dry_run', False),
        html_output=getattr(args, 'html', False),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
