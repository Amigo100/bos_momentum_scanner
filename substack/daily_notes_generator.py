#!/usr/bin/env python3
"""
DAILY NOTES GENERATOR
======================

Generates 2-3 Substack Notes per day with live market data,
replacing the Friday-batch system (notes_batch_generator.py, 1,347 lines).

Note Types:
    PORTFOLIO_PULSE  — Winner receipts, alpha proof, system validation
    SIGNAL_ALERT     — New signals or selectivity narrative
    THEME_MOMENTUM   — Single theme focus, thesis, catalysts
    MARKET_REACTION  — Quick takes on SPY/QQQ, VIX, rates
    SYSTEM_PROOF     — Funnel stats, discipline, screening narrative
    LEARNING_NUGGET  — Educational content (evergreen)
    ENGAGEMENT_HOOK  — Community questions, polls, "what are you watching?"

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
# NOTES SCHEDULE (from spec Section 3.4)
# ═══════════════════════════════════════════════════════════════════════════════

NOTES_SCHEDULE = {
    "saturday":  [("PORTFOLIO_PULSE", "08:30"), ("THEME_MOMENTUM", "12:30")],
    "sunday":    [("LEARNING_NUGGET", "08:30"), ("ENGAGEMENT_HOOK", "12:30")],
    "monday":    [("MARKET_REACTION", "08:30"), ("SYSTEM_PROOF", "12:30"), ("PORTFOLIO_PULSE", "17:00")],
    "tuesday":   [("SIGNAL_ALERT", "08:30"), ("THEME_MOMENTUM", "12:30"), ("ENGAGEMENT_HOOK", "17:00")],
    "wednesday": [("MARKET_REACTION", "08:30"), ("PORTFOLIO_PULSE", "12:30"), ("LEARNING_NUGGET", "17:00")],
    "thursday":  [("THEME_MOMENTUM", "08:30"), ("SIGNAL_ALERT", "12:30"), ("ENGAGEMENT_HOOK", "17:00")],
    "friday":    [("MARKET_REACTION", "08:30"), ("SYSTEM_PROOF", "12:30"), ("PORTFOLIO_PULSE", "17:00")],
}

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
# SYSTEM PROMPT (ported from notes_batch_generator.py — single-note framing)
# ═══════════════════════════════════════════════════════════════════════════════

NOTES_SYSTEM_PROMPT = """You are the voice of Sterling Signals, a weekly momentum trading newsletter on Substack.

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
- Show ALL positions transparently — winners AND losers.
- Frame losses positively: "Stop hit = system working as designed."
- Always show entry prices for full transparency.

ANTI-FABRICATION RULE:
Use ONLY the data provided below. Do not invent any ticker, price, percentage, or date.
If data is missing, write about the system's philosophy instead of fabricating numbers.

Always end with: "Not financial advice. Informational only."
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HTML NOTE TEMPLATE (ported from notes_batch_generator.py)
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
# ENGAGEMENT HOOKS (60+ hooks, ported from notes_batch_generator.py)
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
    """Build a NoteContext from the daily_notes_context.json data.

    This bridges the daily context builder output to the NoteContext format
    expected by prompt builders and note_utils validation/repair.
    """
    now = datetime.now()

    # Extract live market data
    live = context.get("live_market", {})
    spy_pct = live.get("spy_change_pct", 0.0)
    qqq_pct = live.get("qqq_change_pct", 0.0)

    # Portfolio positions — portfolio may be a dict or a list
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

    # Signals
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
        scan_stats=context.get("scan_stats", {}),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HOOK SELECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Track hooks used in this run to avoid repeats within the same day
_hooks_used_today: List[str] = []


def pick_hook(note_type: str) -> str:
    """Pick an engagement hook not yet used today."""
    global _hooks_used_today
    available = ENGAGEMENT_HOOKS.get(note_type, ENGAGEMENT_HOOKS["ENGAGEMENT_HOOK"])
    unused = [h for h in available if h not in _hooks_used_today]
    if not unused:
        unused = available
    hook = random.choice(unused)
    _hooks_used_today.append(hook)
    return hook


# ═══════════════════════════════════════════════════════════════════════════════
# PER-TYPE PROMPT BUILDERS (ported from notes_batch_generator.py)
# ═══════════════════════════════════════════════════════════════════════════════

def build_portfolio_pulse_prompt(ctx: NoteContext) -> str:
    """Winner receipts, benchmark alpha, system validation."""
    winners_text = "No open positions currently."
    if ctx.winners:
        lines = []
        for w in ctx.winners[:4]:
            entry_info = f" (entry ${w.get('entry_price', 0):.2f})"
            theme = w.get('theme', '')
            theme_info = f" — {theme}" if theme else ""
            pnl = w.get('pnl_pct', 0)
            pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
            lines.append(f"${w.get('ticker', '???')} at {pnl_str}{theme_info}{entry_info}")
        winners_text = "\n".join(lines)

    hook = pick_hook("PORTFOLIO_PULSE")

    return f"""Write a "Portfolio Pulse" Substack Note ({ctx.date_str}).

MARKET CONTEXT:
SPY 5-day: {ctx.spy_5d_pct:+.1f}%  |  QQQ 5-day: {ctx.qqq_5d_pct:+.1f}%

PORTFOLIO:
Open positions: {ctx.open_count}

POSITIONS (all open — full transparency):
{winners_text}

INSTRUCTIONS:
1. Lead with the portfolio's strongest result. Make it concrete — the number IS the hook.
2. Weave positions into flowing prose. Show winners as system validation; frame any losses positively: "Stop hit = system working as designed."
3. Compare to SPY/QQQ if we are outperforming — show the alpha gap.
4. Keep it clinical and confident, not boastful. "The data was clear. We followed protocol."
5. End with this engagement question (rephrase naturally): "{hook}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs. Medical-investor voice."""


def build_signal_alert_prompt(ctx: NoteContext) -> str:
    """New signals or selectivity narrative."""
    if ctx.pass_signals:
        sig = ctx.pass_signals[0]
        bullish = sig.get('bullish_factors', [])
        bullish_text = ", ".join(bullish[:3]) if bullish else "Multiple factors aligned."
        conv_text = get_conviction_text(sig.get('conviction', 0))

        signal_section = f"""CONTENT PATH: NEW GREEN SIGNAL

Signal: ${sig['symbol']}
Theme: {sig.get('theme', 'N/A')}
Outlook: {conv_text}
Bullish factors: {bullish_text}
Total GREEN signals this week: {len(ctx.pass_signals)}

Focus on what the system diagnosed: theme alignment, structural confirmation, institutional accumulation patterns."""
    else:
        past_winner_text = ""
        if ctx.winners:
            pw = ctx.winners[0]
            past_winner_text = f"\nReference: ${pw.get('ticker', '???')} at +{pw.get('pnl_pct', 0):.1f}% shows the system works when it fires."

        signal_section = f"""CONTENT PATH: SELECTIVITY (NO NEW SIGNALS)

Scan stats: {ctx.scan_stats.get('tickers_loaded', 1817)} stocks scanned → {ctx.scan_stats.get('technical_signals', 0)} passed technicals → 0 cleared every screening stage.
{past_winner_text}
Frame zero signals as a FEATURE. A good doctor does not prescribe when there is nothing to treat. Our system does the same."""

    hook = pick_hook("SIGNAL_ALERT")

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


def build_theme_momentum_prompt(ctx: NoteContext) -> str:
    """One theme per note — thesis, catalysts, momentum."""
    if ctx.themes:
        theme = ctx.themes[0]
        name = theme.get('name', 'Unknown')
        classification = theme.get('classification', 'N/A')
        score = theme.get('composite_score', 0)
        thesis = theme.get('thesis_summary', 'Theme momentum building.')
        catalysts = theme.get('key_catalysts', [])
        catalysts_text = "; ".join(catalysts[:3]) if catalysts else "Multiple catalysts converging."

        # Find tickers in this theme
        theme_tickers = [w for w in ctx.winners if w.get('theme', '') == name]
        ticker_text = ""
        if theme_tickers:
            parts = [f"${t.get('ticker', '???')} +{t.get('pnl_pct', 0):.1f}%" for t in theme_tickers[:2]]
            ticker_text = f"\nOur positions in this theme: {', '.join(parts)}"

        theme_section = f"""Theme: {name}
Classification: {classification}
Score: {score}/10
Thesis: {thesis}
Key catalysts: {catalysts_text}{ticker_text}"""
    else:
        theme_section = """No scored themes available. Write about sector rotation in general — where institutional money appears to be flowing based on market breadth and recent strength."""

    hook = pick_hook("THEME_MOMENTUM")

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


def build_market_reaction_prompt(ctx: NoteContext) -> str:
    """Quick takes on SPY/QQQ, VIX, rates, rotation."""
    market_excerpt = ctx.market_analysis_excerpt or "Market data unavailable."

    hook = pick_hook("MARKET_REACTION")

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


def build_system_proof_prompt(ctx: NoteContext) -> str:
    """Funnel stats, discipline, screening narrative."""
    tickers_loaded = ctx.scan_stats.get('tickers_loaded', 1817)
    tech_signals = ctx.scan_stats.get('technical_signals', 0)
    final_trade = ctx.scan_stats.get('final_trade', 0)
    final_consider = ctx.scan_stats.get('final_consider', 0)

    winner_proof = ""
    if ctx.winners:
        w = ctx.winners[0]
        winner_proof = f"\nProof it works: ${w.get('ticker', '???')} at +{w.get('pnl_pct', 0):.1f}% — diagnosed by the same screening system."

    hook = pick_hook("SYSTEM_PROOF")

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


def build_learning_nugget_prompt(ctx: NoteContext) -> str:
    """Educational content — evergreen, no live data needed."""
    hook = pick_hook("LEARNING_NUGGET")

    # Rotate through educational topics
    topics = [
        ("Position Sizing", "Teach why position sizing matters more than stock picking. Use a medical analogy: 'A surgeon does not treat every patient the same way — dosage matters.'"),
        ("Risk Management", "Explain why protecting capital is the most important skill. Use: 'In medicine, the first rule is do no harm. In markets, the first rule is preserve capital.'"),
        ("Systematic vs Discretionary", "Compare systematic investing to evidence-based medicine. Why protocols beat intuition."),
        ("The Power of Patience", "Explain why waiting for high-quality setups is a competitive advantage. Use: 'A doctor who operates on every patient is not thorough — they are reckless.'"),
        ("Understanding Sector Rotation", "Teach how capital flows between sectors and why recognizing these patterns early matters."),
        ("Compounding Returns", "Explain the math of compounding and why consistency beats occasional big wins."),
        ("Confirmation Bias", "Teach how to recognize and avoid confirmation bias in investing. Use: 'In medicine, we seek to disprove our diagnosis, not confirm it.'"),
        ("Win Rate vs Expectancy", "Explain why win rate alone is misleading. A 40% win rate with 3:1 reward-to-risk beats 80% with 0.5:1."),
    ]
    topic_title, topic_instruction = random.choice(topics)

    return f"""Write an educational Substack Note ({ctx.date_str}).

TOPIC: {topic_title}

{topic_instruction}

INSTRUCTIONS:
1. Open with a scroll-stopping hook — a surprising fact, a counterintuitive claim, or a provocative question.
2. Teach the concept in 2-3 flowing paragraphs. No jargon, no textbook tone.
3. Frame it through the medical-investor lens where natural: "Like a diagnostic protocol..."
4. Make it concrete with a relatable example.
5. End with: "{hook}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line: "Not financial advice. Informational only."

150-300 words. No markdown headers. No bullet lists. Flowing paragraphs."""


def build_engagement_hook_prompt(ctx: NoteContext) -> str:
    """Community questions, polls, open discussion."""
    hook = pick_hook("ENGAGEMENT_HOOK")

    # Pick a light data point to seed the conversation
    data_seed = ""
    if ctx.winners:
        w = ctx.winners[0]
        data_seed = f"Our top performer ${w.get('ticker', '???')} is at +{w.get('pnl_pct', 0):.1f}%. "
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

def template_portfolio_pulse(ctx: NoteContext) -> str:
    """Template fallback for PORTFOLIO_PULSE notes."""
    lines = [f"Portfolio update — {ctx.date_str}", ""]

    if ctx.winners:
        w = ctx.winners[0]
        pnl = w.get('pnl_pct', 0)
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        lines.append(f"${w.get('ticker', '???')} is at {pnl_str} from a ${w.get('entry_price', 0):.2f} entry. Our screening system diagnosed this setup early and the thesis is playing out.")
        lines.append("")
        if len(ctx.winners) > 1:
            w2 = ctx.winners[1]
            lines.append(f"${w2.get('ticker', '???')} is also delivering at +{w2.get('pnl_pct', 0):.1f}%. The system continues to identify structural momentum before the crowd.")
            lines.append("")

    lines.append(f"With {ctx.open_count} positions open, the portfolio is navigating this market with systematic discipline.")
    lines.append("")
    lines.append(pick_hook("PORTFOLIO_PULSE"))
    lines.append("")
    lines.append("Full analysis every Saturday in Sterling Signals.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")
    return "\n".join(lines)


def template_signal_alert(ctx: NoteContext) -> str:
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
            lines.append(f"Meanwhile, ${w.get('ticker', '???')} continues to run at +{w.get('pnl_pct', 0):.1f}%. Patience pays when the system is right.")

    lines.extend(["", pick_hook("SIGNAL_ALERT"), "", "Full analysis every Saturday in Sterling Signals.", "", "Not financial advice. Informational only."])
    return "\n".join(lines)


def template_theme_momentum(ctx: NoteContext) -> str:
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
    else:
        lines.append("Sector rotation continues to create opportunities for systematic investors who track institutional flows.")
        lines.append("")
        lines.append("Our screening system maps capital movement across themes — identifying where the smart money is positioning before it becomes consensus.")
        lines.append("")

    lines.extend([pick_hook("THEME_MOMENTUM"), "", "Full analysis every Saturday in Sterling Signals.", "", "Not financial advice. Informational only."])
    return "\n".join(lines)


def template_market_reaction(ctx: NoteContext) -> str:
    """Template fallback for MARKET_REACTION notes."""
    lines = [
        f"Market vitals — SPY {ctx.spy_5d_pct:+.1f}%, QQQ {ctx.qqq_5d_pct:+.1f}% over the last 5 sessions.",
        "",
        "The question is not what the market did, but what it is telling us about where capital is rotating next.",
        "",
        f"With {ctx.open_count} positions open, we are watching breadth, sector strength, and our screening system for the next structural signal.",
        "",
        pick_hook("MARKET_REACTION"),
        "",
        "Full analysis every Saturday in Sterling Signals.",
        "",
        "Not financial advice. Informational only.",
    ]
    return "\n".join(lines)


def template_system_proof(ctx: NoteContext) -> str:
    """Template fallback for SYSTEM_PROOF notes."""
    loaded = ctx.scan_stats.get('tickers_loaded', 1817)
    final = ctx.scan_stats.get('final_trade', 0)
    lines = [
        f"{loaded} stocks. {final} survived every screening stage.",
        "",
        f"Our screening system rejected {loaded - final} setups this week. That is not a failure — that is specificity working exactly as designed.",
        "",
        "Like a diagnostic test, the value is not in what it catches — it is in what it correctly rules out. Most traders chase every setup. Our system is built to wait.",
        "",
    ]
    if ctx.winners:
        w = ctx.winners[0]
        lines.append(f"The proof? ${w.get('ticker', '???')} at +{w.get('pnl_pct', 0):.1f}%. Diagnosed by the same screening system that says no to 99% of what it screens.")
        lines.append("")

    lines.extend([pick_hook("SYSTEM_PROOF"), "", "Full analysis every Saturday in Sterling Signals.", "", "Not financial advice. Informational only."])
    return "\n".join(lines)


def template_learning_nugget(ctx: NoteContext) -> str:
    """Template fallback for LEARNING_NUGGET notes."""
    lines = [
        "Position sizing is the most underrated skill in investing.",
        "",
        "A surgeon does not administer the same dosage to every patient. The treatment depends on the diagnosis, the risk profile, and the patient's history. Investing works the same way.",
        "",
        "High conviction? Larger position. Speculative? Smaller allocation. The math of compounding rewards discipline more than it rewards boldness.",
        "",
        pick_hook("LEARNING_NUGGET"),
        "",
        "Full analysis every Saturday in Sterling Signals.",
        "",
        "Not financial advice. Informational only.",
    ]
    return "\n".join(lines)


def template_engagement_hook(ctx: NoteContext) -> str:
    """Template fallback for ENGAGEMENT_HOOK notes."""
    hook = pick_hook("ENGAGEMENT_HOOK")
    data_seed = ""
    if ctx.winners:
        w = ctx.winners[0]
        data_seed = f"Our top performer ${w.get('ticker', '???')} is at +{w.get('pnl_pct', 0):.1f}% and climbing."

    lines = []
    if data_seed:
        lines.extend([data_seed, ""])
    lines.extend([
        "The market never stops teaching. Every week we learn something new about how capital flows, how themes rotate, and how discipline separates consistent performers from the crowd.",
        "",
        hook,
        "",
        "Full analysis every Saturday in Sterling Signals.",
        "",
        "Not financial advice. Informational only.",
    ])
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
# HTML WRAPPING (ported from notes_batch_generator.py)
# ═══════════════════════════════════════════════════════════════════════════════

def wrap_note_html(markdown_content: str, title: str = "Sterling Signals Note") -> str:
    """Wrap a markdown note in self-contained HTML for Substack.

    Converts markdown-style content into HTML paragraphs with inline styles.
    Handles common patterns: headers, bold, line breaks, paragraphs.
    """
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

        # Headers (strip them — notes should not have headers)
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

        # CTA line
        if any(phrase in stripped for phrase in ["Full analysis every", "Subscribe to", "Sterling Signals"]):
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
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
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        html_parts.append(text)

    if in_paragraph:
        html_parts.append("</p>")

    body_html = "\n".join(html_parts)
    return HTML_NOTE_TEMPLATE.format(title=title, body_html=body_html)


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY GATES (spec Section 17.1)
# ═══════════════════════════════════════════════════════════════════════════════

def fix_ticker_format(text: str) -> str:
    """Ensure tickers use $TICKER format. Regex fix for common LLM omissions."""
    # Match bare uppercase tickers (2-5 chars) that look like stock symbols
    # preceded by whitespace or start-of-string, not already prefixed with $
    text = re.sub(r'(?<!\$)\b([A-Z]{2,5})\b(?=\s+(?:at|is|was|hit|up|down|rose|fell|gained|lost|\+|-|\d))',
                  r'$\1', text)
    return text


def validate_and_repair(
    raw_content: str,
    note_type: str,
    ctx: NoteContext,
    max_repairs: int = 2,
) -> Optional[str]:
    """Validate a note and attempt LLM repair if needed.

    Returns validated content or None if unrecoverable.
    """
    content = sanitize_note(raw_content)

    # Auto-fix ticker format
    content = fix_ticker_format(content)

    # Auto-append disclaimer if missing
    if "not financial advice" not in content.lower():
        content = content.rstrip() + "\n\nNot financial advice. Informational only."

    # Validate
    is_valid, issues = validate_note(content)
    if is_valid:
        return content

    # Attempt repair
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

    # All repairs failed — try template fallback
    print(f"    ✗ Repair failed after {max_repairs} attempts. Using template fallback.")
    fallback_fn = TEMPLATE_FALLBACKS.get(note_type)
    if fallback_fn:
        return fallback_fn(ctx)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LLM GENERATION
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
# SAVE
# ═══════════════════════════════════════════════════════════════════════════════

def save_note_html(
    content: str,
    day: str,
    slot: int,
    note_type: str,
    html_output: bool = True,
) -> Path:
    """Save a note to both current/ and archive/ directories.

    Returns the path to the current/ file.
    """
    current_dir, week_dir = ensure_output_dirs()
    date_str = datetime.now().strftime("%Y%m%d")

    if html_output:
        # Wrap in HTML
        title = f"{day.capitalize()} — {note_type.replace('_', ' ').title()}"
        html_content = wrap_note_html(content, title=title)
        filename = f"note_{slot}_{note_type.lower()}_{date_str}.html"
    else:
        html_content = content
        filename = f"note_{slot}_{note_type.lower()}_{date_str}.md"

    # Ensure notes subdirectory exists
    (current_dir / "notes").mkdir(parents=True, exist_ok=True)
    (week_dir / "notes").mkdir(parents=True, exist_ok=True)

    current_path = current_dir / "notes" / filename
    week_path = week_dir / "notes" / filename

    current_path.write_text(html_content)
    week_path.write_text(html_content)

    return current_path


def save_manifest(notes: List[Dict], day: str):
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
# MAIN GENERATION FLOW (spec Section 6.3)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_notes(
    day: str,
    context: Optional[Dict] = None,
    dry_run: bool = False,
    no_llm: bool = False,
    html_output: bool = True,
) -> List[Dict]:
    """Generate 2-3 notes for today using live context.

    Args:
        day: Day of the week (e.g. "monday").
        context: Pre-loaded context dict (from daily_notes_context.json).
                 If None, loads from file or builds fresh via note_utils.
        dry_run: Preview without saving.
        no_llm: Use template fallback instead of LLM.
        html_output: Save as HTML (default True).

    Returns:
        List of note dicts with type, slot, filepath, text.
    """
    global _hooks_used_today
    _hooks_used_today = []  # Reset for this run

    day = day.lower()

    # 1. Determine today's note types from schedule
    schedule = NOTES_SCHEDULE.get(day, [])
    if not schedule:
        print(f"  No notes scheduled for {day}")
        return []

    # 2. Build NoteContext
    if context is not None:
        ctx = build_note_context_from_daily(context)
    else:
        # Try daily_notes_context.json first, then fall back to live fetch
        daily_ctx = load_notes_context_json()
        if daily_ctx:
            ctx = build_note_context_from_daily(daily_ctx)
            print("  ✓ Loaded context from daily_notes_context.json")
        else:
            print("  ℹ No daily_notes_context.json — building fresh context...")
            ctx = build_note_context()

    # 3. Generate each note
    notes = []
    total_cost = 0.0

    for slot, (note_type, time_et) in enumerate(schedule, 1):
        label = f"Slot {slot} ({note_type}, {time_et} ET)"

        if dry_run:
            print(f"  [{slot}/{len(schedule)}] {label} — DRY RUN")
            notes.append({
                "type": note_type,
                "slot": slot,
                "time_et": time_et,
                "text": f"[DRY RUN: {note_type} — {time_et} ET]",
            })
            continue

        print(f"  [{slot}/{len(schedule)}] Generating {label}...")

        content = None
        cost = 0.0

        if no_llm:
            # Template fallback
            fallback_fn = TEMPLATE_FALLBACKS.get(note_type)
            if fallback_fn:
                content = fallback_fn(ctx)
                print(f"    Generated via template ({len(content.split())} words)")
            else:
                print(f"    ✗ No template for {note_type}")
                continue
        else:
            # LLM generation
            try:
                raw_content, cost = generate_single_note(note_type, ctx)
                total_cost += cost
                print(f"    Generated via LLM ({len(raw_content.split())} words, ${cost:.4f})")

                # Validate + repair
                content = validate_and_repair(raw_content, note_type, ctx)
            except Exception as e:
                print(f"    ✗ LLM error: {e}")
                print(f"    Falling back to template...")
                fallback_fn = TEMPLATE_FALLBACKS.get(note_type)
                if fallback_fn:
                    content = fallback_fn(ctx)
                else:
                    content = None

        if content is None:
            print(f"    ✗ Failed to generate {label}")
            continue

        # Save
        filepath = save_note_html(content, day, slot, note_type, html_output=html_output)
        print(f"    ✓ Saved: {filepath.name}")

        notes.append({
            "type": note_type,
            "slot": slot,
            "time_et": time_et,
            "filepath": str(filepath),
            "text": content,
            "word_count": len(content.split()),
            "cost": cost,
        })

    # Save manifest
    if not dry_run and notes:
        save_manifest(notes, day)

    # Summary
    if total_cost > 0:
        print(f"\n  LLM cost: ${total_cost:.4f}")

    return notes


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Notes Generator")
    parser.add_argument("--day", type=str, default=None,
                        help="Override day (e.g., wednesday)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without LLM or saving")
    parser.add_argument("--no-llm", action="store_true",
                        help="Use template fallback (no API cost)")
    parser.add_argument("--html", action="store_true", default=True,
                        help="HTML output (default)")

    args = parser.parse_args()

    # Determine day
    if args.day:
        day = args.day.lower()
    else:
        day = datetime.now().strftime("%A").lower()

    day_title = day.capitalize()
    now = datetime.now()

    print("\n" + "=" * 70)
    print(f"  STERLING SIGNALS — DAILY NOTES GENERATOR")
    print(f"  {day_title} {now.strftime('%B %d, %Y')}")
    if getattr(args, 'no_llm', False):
        print("  Mode: TEMPLATE FALLBACK (no LLM)")
    elif getattr(args, 'dry_run', False):
        print("  Mode: DRY RUN (preview only)")
    else:
        print("  Mode: LLM-POWERED (Claude Sonnet)")
    print("=" * 70 + "\n")

    # Show schedule
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
