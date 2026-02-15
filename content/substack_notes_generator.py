#!/usr/bin/env python3
"""
SUBSTACK NOTES GENERATOR (LLM-powered)
========================================

Generates Tuesday and Thursday Substack Notes with professional medical-investor
voice for mid-week engagement.

- Tuesday Note: "Portfolio Pulse" — theme momentum, winners, market context
- Thursday Note: "Trade Spotlight" — new signals, selectivity, system proof

Uses Claude Sonnet for natural, engaging prose. Falls back to templates with --no-llm.

Usage:
    python -m content.substack_notes_generator              # Generate both (LLM)
    python -m content.substack_notes_generator --tuesday     # Tuesday only
    python -m content.substack_notes_generator --thursday    # Thursday only
    python -m content.substack_notes_generator --no-llm      # Template fallback
    python -m content.substack_notes_generator --dry-run     # Preview, don't save
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
    TRADES_DIR,
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
from config.marketing_vocabulary import validate_content

try:
    from config import MARKETING_THRESHOLDS
except ImportError:
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
    }

MIN_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
BIG_WIN_THRESHOLD = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

NOTES_SYSTEM_PROMPT = """You are the voice of Sterling Signals, a weekly momentum trading newsletter on Substack.

WHO WE ARE:
Three physicians who traded stethoscopes for stock screeners. We built a systematic momentum scanner that screens 1,800+ US stocks through a proprietary 5-gate system — because we believe the same evidence-based rigor that saves lives in medicine can generate alpha in markets. We diagnose momentum the way we once diagnosed patients: systematic screening, pattern recognition, ruling out false positives, and never letting emotion override data.

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
# ENGAGEMENT HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

TUESDAY_ENGAGEMENT_HOOKS = [
    "What themes are on your radar this week?",
    "Are you seeing the same sector rotation we are?",
    "What is your screening system telling you this week?",
    "Where are you seeing institutional flows right now?",
    "Which infrastructure names are you watching?",
    "What setups are you triaging for the week ahead?",
    "Is anyone else noticing this theme gaining momentum?",
    "What is one stock on your watchlist that nobody is talking about?",
    "Are you positioned for what is coming next in this rotation?",
    "What does your process say about the current setup?",
]

THURSDAY_ENGAGEMENT_HOOKS = [
    "What is your system telling you about this setup?",
    "Would you take this trade? Why or why not?",
    "Have you noticed this theme strengthening?",
    "What is the best signal your system has generated this year?",
    "Do you agree with our read on this sector?",
    "How do you handle weeks with no clean signals?",
    "What is your criteria for a high-conviction entry?",
    "Is patience or action the right call here?",
    "What is one lesson your worst trade taught you?",
    "How selective is your screening process?",
]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NoteContext:
    """Aggregated data for note generation."""
    week_number: int = 0
    date_str: str = ""
    spy_5d_pct: float = 0.0
    qqq_5d_pct: float = 0.0
    market_analysis_excerpt: str = ""
    open_count: int = 0
    winners: List[Dict] = field(default_factory=list)       # 15%+ gains
    big_winners: List[Dict] = field(default_factory=list)    # 25%+ gains (can show entry)
    top_performer: Optional[Dict] = None
    pass_signals: List[Dict] = field(default_factory=list)
    consider_signals: List[Dict] = field(default_factory=list)
    themes: List[Dict] = field(default_factory=list)
    scan_stats: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_week_dir() -> Path:
    """Get the current week's output directory (YYYY-WXX format)."""
    today = datetime.now()
    iso_cal = today.isocalendar()
    return TRADES_DIR / "weeks" / f"{iso_cal.year}-W{iso_cal.week:02d}"


def get_current_dir() -> Path:
    """Get the 'current' output directory for latest outputs."""
    return TRADES_DIR / "current"


def ensure_output_dirs() -> Tuple[Path, Path]:
    """
    Ensure both current/ and weeks/YYYY-WXX/ directories exist.
    Returns (current_dir, week_dir)
    """
    current_dir = get_current_dir()
    week_dir = get_current_week_dir()

    (current_dir / "substack_notes").mkdir(parents=True, exist_ok=True)
    (week_dir / "substack_notes").mkdir(parents=True, exist_ok=True)

    return current_dir, week_dir


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_portfolio() -> List[Dict]:
    """Load portfolio from CSV via canonical portfolio_manager."""
    from core.portfolio_manager import load_portfolio as _load
    return _load()


def load_signals() -> Dict:
    """Load latest signals.json."""
    current_signals = get_current_dir() / "signals.json"
    root_signals = TRADES_DIR / "signals.json"

    for path in [current_signals, root_signals]:
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
    return {}


def get_live_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch current prices for tickers via yfinance."""
    if not tickers:
        return {}

    prices = {}
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if len(tickers) == 1:
            prices[tickers[0]] = float(data['Close'].iloc[-1])
        else:
            for ticker in tickers:
                try:
                    prices[ticker] = float(data['Close'][ticker].iloc[-1])
                except (KeyError, IndexError):
                    pass
    except Exception as e:
        print(f"  Warning: Could not fetch prices: {e}")

    return prices


def get_index_performance() -> Tuple[float, float]:
    """Fetch SPY and QQQ 5-day percentage change."""
    spy_pct = 0.0
    qqq_pct = 0.0
    try:
        data = yf.download(["SPY", "QQQ"], period="10d", progress=False)
        if not data.empty and len(data) >= 2:
            for ticker, attr in [("SPY", "spy_pct"), ("QQQ", "qqq_pct")]:
                try:
                    closes = data['Close'][ticker].dropna()
                    if len(closes) >= 2:
                        pct = ((closes.iloc[-1] / closes.iloc[0]) - 1) * 100
                        if ticker == "SPY":
                            spy_pct = pct
                        else:
                            qqq_pct = pct
                except (KeyError, IndexError):
                    pass
    except Exception as e:
        print(f"  Warning: Could not fetch index performance: {e}")

    return spy_pct, qqq_pct


def load_market_analysis() -> str:
    """Load market analysis excerpt from trades/current/market_analysis.md."""
    path = get_current_dir() / "market_analysis.md"
    if path.exists():
        try:
            content = path.read_text()
            # Extract first 500 chars as context excerpt
            return content[:500].strip()
        except Exception:
            pass
    return ""


def calculate_portfolio_stats(portfolio: List[Dict], prices: Dict[str, float]) -> Dict:
    """Calculate portfolio performance statistics."""
    open_positions = [t for t in portfolio if t.get('status') == 'OPEN']
    closed_positions = [t for t in portfolio if t.get('status') in ['CLOSED', 'STOPPED']]

    position_pnl = []
    total_pnl_pct = 0

    for trade in open_positions:
        ticker = trade.get('ticker', '')
        entry_price = float(trade.get('entry_price') or 0)
        current_price = prices.get(ticker, entry_price)

        if entry_price > 0 and current_price > 0:
            pnl_pct = ((current_price / entry_price) - 1) * 100
            position_pnl.append({
                'ticker': ticker,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'theme': trade.get('theme', ''),
                'entry_date': trade.get('entry_date', '')
            })
            total_pnl_pct += pnl_pct

    position_pnl.sort(key=lambda x: x['pnl_pct'], reverse=True)

    winners = len([t for t in closed_positions
                   if float(t.get('exit_price') or 0) > float(t.get('entry_price') or 0)])
    win_rate = (winners / len(closed_positions) * 100) if closed_positions else 0

    top_performer = position_pnl[0] if position_pnl else None
    avg_pnl = total_pnl_pct / len(open_positions) if open_positions else 0

    return {
        'open_count': len(open_positions),
        'closed_count': len(closed_positions),
        'avg_pnl_pct': avg_pnl,
        'total_unrealized_pnl': total_pnl_pct,
        'win_rate': win_rate,
        'winners': winners,
        'top_performer': top_performer,
        'positions': position_pnl,
    }


def build_note_context() -> NoteContext:
    """Build aggregated context for note generation."""
    print("  Loading data...")

    portfolio = load_portfolio()
    signals = load_signals()

    open_tickers = [t['ticker'] for t in portfolio if t.get('status') == 'OPEN']
    print(f"    Portfolio: {len(portfolio)} trades ({len(open_tickers)} open)")

    # Fetch live prices
    print("  Fetching live prices...")
    prices = get_live_prices(open_tickers)
    print(f"    Got prices for {len(prices)} tickers")

    # Index performance
    print("  Fetching index performance...")
    spy_pct, qqq_pct = get_index_performance()
    print(f"    SPY 5d: {spy_pct:+.1f}%  |  QQQ 5d: {qqq_pct:+.1f}%")

    # Market analysis excerpt
    market_excerpt = load_market_analysis()

    # Portfolio stats
    stats = calculate_portfolio_stats(portfolio, prices)

    # Filter winners by threshold
    all_positions = stats.get('positions', [])
    winners = [p for p in all_positions if p.get('pnl_pct', 0) >= MIN_WIN_THRESHOLD]
    big_winners = [p for p in all_positions if p.get('pnl_pct', 0) >= BIG_WIN_THRESHOLD]

    # Signals
    buy_signals = signals.get('buy_signals', []) if signals else []
    pass_signals = [s for s in buy_signals
                    if s.get('final_decision') in ['PASS', 'TRADE']]
    consider_signals = [s for s in buy_signals
                        if s.get('final_decision') == 'CONSIDER']
    themes = signals.get('themes', []) if signals else []
    scan_stats = signals.get('stats', {}) if signals else {}

    ctx = NoteContext(
        week_number=datetime.now().isocalendar().week,
        date_str=datetime.now().strftime("%B %d, %Y"),
        spy_5d_pct=spy_pct,
        qqq_5d_pct=qqq_pct,
        market_analysis_excerpt=market_excerpt,
        open_count=stats['open_count'],
        winners=winners,
        big_winners=big_winners,
        top_performer=stats['top_performer'],
        pass_signals=pass_signals,
        consider_signals=consider_signals,
        themes=themes,
        scan_stats=scan_stats,
    )

    print(f"    Winners (15%+): {len(winners)}  |  Big winners (25%+): {len(big_winners)}")
    print(f"    GREEN signals: {len(pass_signals)}  |  Themes: {len(themes)}")

    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_tuesday_prompt(ctx: NoteContext) -> str:
    """Build the user prompt for Tuesday 'Portfolio Pulse' note."""

    # Format winners
    winners_text = "No positions above 15% gain currently."
    if ctx.winners:
        lines = []
        for w in ctx.winners[:5]:
            entry_info = ""
            if can_show_entry_price(w):
                entry_info = f" (entry ${w['entry_price']:.2f})"
            theme = w.get('theme', '')
            theme_info = f" — {theme}" if theme else ""
            lines.append(f"${ w['ticker'] } at +{w['pnl_pct']:.1f}%{theme_info}{entry_info}")
        winners_text = "\n".join(lines)

    # Format themes
    themes_text = "No theme data available."
    if ctx.themes:
        prime = [t for t in ctx.themes if t.get('classification') == 'PRIME']
        investable = [t for t in ctx.themes if t.get('classification') == 'INVESTABLE']
        parts = []
        for t in (prime + investable)[:3]:
            parts.append(f"{t.get('name', 'Unknown')} ({t.get('classification', 'N/A')})")
        themes_text = ", ".join(parts) if parts else "Themes under review."

    # Market context
    market_context = ""
    if ctx.market_analysis_excerpt:
        market_context = f"""
MARKET ANALYSIS EXCERPT (use for a unique mid-week observation):
{ctx.market_analysis_excerpt}
"""

    engagement = random.choice(TUESDAY_ENGAGEMENT_HOOKS)

    prompt = f"""Write a Tuesday "Portfolio Pulse" Substack Note for Week {ctx.week_number} ({ctx.date_str}).

MARKET DATA:
SPY 5-day change: {ctx.spy_5d_pct:+.1f}%
QQQ 5-day change: {ctx.qqq_5d_pct:+.1f}%
{market_context}
PORTFOLIO DATA:
Open positions: {ctx.open_count}
Scan stats: {ctx.scan_stats.get('tickers_loaded', 1817)} stocks scanned, {len(ctx.pass_signals)} cleared all 5 gates

WINNERS (15%+ gains only — these are the ONLY positions you may mention):
{winners_text}

HOT THEMES:
{themes_text}

INSTRUCTIONS:
1. Open with a scroll-stopping hook that contrasts what the crowd is doing vs what our system sees.
2. Weave in the winners naturally — prose, not bullet lists.
3. Reference SPY/QQQ performance to show alpha if our positions are outperforming.
4. Add ONE forward-looking observation not found in Saturday's newsletter. Use the market analysis excerpt for inspiration.
5. End with this engagement question (or rephrase naturally): "{engagement}"
6. Close with: "Full analysis every Saturday in Sterling Signals."
7. Final line must be: "Not financial advice. Informational only."

REMEMBER: 150-300 words. No markdown headers. No bullet lists. Flowing paragraphs. Medical-investor voice.
"""
    return prompt


def build_thursday_prompt(ctx: NoteContext) -> str:
    """Build the user prompt for Thursday 'Trade Spotlight' note."""

    engagement = random.choice(THURSDAY_ENGAGEMENT_HOOKS)

    # Determine content path
    if ctx.pass_signals:
        # Path A: Feature the top GREEN signal
        sig = ctx.pass_signals[0]
        bullish = sig.get('bullish_factors', [])
        bullish_text = ", ".join(bullish[:3]) if bullish else "Multiple technical and fundamental factors aligned."
        theme = sig.get('theme', 'N/A')
        conviction_text = get_conviction_text(sig.get('conviction', 0))

        signal_section = f"""CONTENT PATH: NEW GREEN SIGNAL(S)

Featured signal: ${sig['symbol']}
Theme: {theme}
Conviction: {conviction_text}
Bullish factors: {bullish_text}
Total GREEN signals this week: {len(ctx.pass_signals)}

INSTRUCTIONS:
1. Open with a hook about what our screening system just diagnosed.
2. Feature ${sig['symbol']} — weave the bullish factors into natural prose with a medical-analytical lens. Think: "The chart showed symptoms of institutional accumulation long before the crowd noticed."
3. Mention the theme as a macro tailwind.
4. If multiple GREEN signals, briefly note the count and shared thesis.
5. Reference our 5-gate system as the reason we caught this before others."""

    elif ctx.big_winners:
        # Path C: Lead with a big winner receipt
        bw = ctx.big_winners[0]
        entry_info = f" (entry ${bw['entry_price']:.2f})" if can_show_entry_price(bw) else ""

        signal_section = f"""CONTENT PATH: BIG WINNER SPOTLIGHT

Top winner: ${bw['ticker']} at +{bw['pnl_pct']:.1f}%{entry_info}
Theme: {bw.get('theme', '')}

INSTRUCTIONS:
1. Open with the receipt — lead with the number. "+{bw['pnl_pct']:.1f}% is what happens when the system prescribes and you follow the protocol."
2. Explain WHY the system caught this — what made it pass all 5 gates.
3. Frame this as proof that systematic screening works.
4. Do NOT gloat — be clinical about it. "The data was clear. We followed the process."
5. Mention we are always scanning for the next setup."""

    else:
        # Path B: No signals — selectivity is a feature
        # Show a past winner as proof
        past_winner_text = ""
        if ctx.winners:
            pw = ctx.winners[0]
            past_winner_text = f"\nMention our current winner ${pw['ticker']} at +{pw['pnl_pct']:.1f}% as proof the system works when it fires."

        signal_section = f"""CONTENT PATH: NO NEW SIGNALS (SELECTIVITY)

Scan stats: {ctx.scan_stats.get('tickers_loaded', 1817)} stocks scanned, {ctx.scan_stats.get('technical_signals', 0)} passed technical gates, 0 cleared all 5 gates.
{past_winner_text}
INSTRUCTIONS:
1. Open with a medical metaphor about selectivity: "A good doctor does not prescribe when there is nothing to treat. A good screening system does the same."
2. Frame zero signals as a FEATURE, not a bug. Our 5-gate system is designed to reject noise.
3. Show the funnel: 1,800 stocks → X passed technicals → 0 cleared all gates. This IS the system working.
4. If there is a past winner, reference it as proof that patience pays.
5. Contrast with traders who chase setups every week."""

    prompt = f"""Write a Thursday "Trade Spotlight" Substack Note for Week {ctx.week_number} ({ctx.date_str}).

{signal_section}

6. End with this engagement question (or rephrase naturally): "{engagement}"
7. Close with: "Full analysis every Saturday in Sterling Signals."
8. Final line must be: "Not financial advice. Informational only."

REMEMBER: 150-300 words. No markdown headers. No bullet lists. Flowing paragraphs. Medical-investor voice.
"""
    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# LLM GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_note_llm(note_type: str, ctx: NoteContext) -> Tuple[str, float]:
    """Generate a note via Claude Sonnet. Returns (content, cost)."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed. Use --no-llm.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Use --no-llm.")

    client = anthropic.Anthropic(api_key=api_key)

    if note_type == "tuesday":
        user_prompt = build_tuesday_prompt(ctx)
    else:
        user_prompt = build_thursday_prompt(ctx)

    response = client.messages.create(
        model=MODEL_NOTES,
        max_tokens=800,
        system=NOTES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content[0].text.strip()

    # Calculate cost
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

    return content, cost


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_note(content: str) -> Tuple[bool, List[str]]:
    """
    Three-layer validation for generated notes.
    Returns (is_valid, list_of_issues).
    """
    issues = []

    # Layer 1: Marketing vocabulary check
    is_valid_marketing, marketing_violations = validate_content(content)
    if not is_valid_marketing:
        issues.extend([f"Marketing: {v}" for v in marketing_violations])

    # Layer 2: Banned phrases + loser focus
    banned_found = check_banned_phrases(content)
    if banned_found:
        issues.extend([f"Banned phrase: {p}" for p in banned_found])

    if check_loser_focus(content):
        issues.append("Content appears focused on losing positions")

    # Layer 3: Custom structural checks
    # No markdown headers
    if re.search(r'^#{1,3}\s', content, re.MULTILINE):
        issues.append("Contains markdown headers (# or ##)")

    # No negative percentages (losers)
    if re.search(r'-\d+\.?\d*%', content):
        issues.append("Contains negative percentage (potential loser mention)")

    # No numeric conviction scores
    if re.search(r'conviction\s+\d+', content, re.IGNORECASE):
        issues.append("Contains numeric conviction score")

    # Word count check (80-400)
    word_count = len(content.split())
    if word_count < 80:
        issues.append(f"Too short ({word_count} words, minimum 80)")
    elif word_count > 400:
        issues.append(f"Too long ({word_count} words, maximum 400)")

    # Must contain disclaimer
    if "not financial advice" not in content.lower():
        issues.append("Missing disclaimer: 'Not financial advice. Informational only.'")

    return (len(issues) == 0, issues)


def sanitize_note(content: str) -> str:
    """Clean up LLM output for Substack Notes."""
    # Strip markdown headers
    content = re.sub(r'^#{1,3}\s+.*$', '', content, flags=re.MULTILINE)

    # Remove bullet points at start of lines
    content = re.sub(r'^[\s]*[•\-\*]\s+', '', content, flags=re.MULTILINE)

    # Ensure disclaimer is present
    if "not financial advice" not in content.lower():
        content = content.rstrip()
        content += "\n\nNot financial advice. Informational only."

    # Remove excess blank lines (max 2 consecutive)
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    # Trim
    content = content.strip()

    return content


def repair_note(content: str, issues: List[str], note_type: str, ctx: NoteContext) -> Tuple[str, float]:
    """Attempt one LLM repair of a failed note. Returns (repaired_content, cost)."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("Cannot repair without anthropic package")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    violations_text = "\n".join(f"- {issue}" for issue in issues)

    repair_prompt = f"""The following Substack Note has validation issues. Please rewrite it to fix ALL violations while keeping the same message and data points.

VIOLATIONS FOUND:
{violations_text}

ORIGINAL NOTE:
{content}

RULES REMINDER:
- NO markdown headers (no #, ##)
- NO bullet point lists (no •, -, *)
- 150-300 words, flowing paragraphs only
- NEVER mention losing positions or negative P&L
- NEVER use banned terms: HMA, RSI, MACD, KDJ, Banker, UC, Undercurrent, BoS, ExD, TEAL, PASS, VIOLET, AMBER, Gatekeeper, Investment Gate, conviction scores
- Must end with: "Not financial advice. Informational only."
- Use "GREEN signal" for buys, "our screening system" for the system

Rewrite the note now. Output ONLY the corrected note text."""

    response = client.messages.create(
        model=MODEL_NOTES,
        max_tokens=800,
        system=NOTES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": repair_prompt}],
    )

    repaired = response.content[0].text.strip()
    cost = (response.usage.input_tokens * 3.0 / 1_000_000) + (response.usage.output_tokens * 15.0 / 1_000_000)

    return repaired, cost


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE FALLBACK (--no-llm)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tuesday_note_template(ctx: NoteContext) -> str:
    """
    Generate Tuesday 'Theme Momentum' note (template fallback).

    Focus: Hot themes, scanner stats, GREEN signals.
    NOTE: Per marketing overhaul - NO portfolio P&L display, NO losing positions.
    """
    lines = []
    lines.append(f"Theme Momentum - Week {ctx.week_number}")
    lines.append("")

    # Hot themes (public-facing)
    prime_themes = [t for t in ctx.themes if t.get('classification') == 'PRIME']
    if prime_themes:
        lines.append("Hot Themes This Week:")
        for theme in prime_themes[:3]:
            name = theme.get('name', 'Unknown')
            lines.append(f"{name}")
        lines.append("")

    # GREEN signals count
    if ctx.pass_signals:
        lines.append(f"{len(ctx.pass_signals)} GREEN Signal(s) Active")
        lines.append("Our 5-gate system identified these opportunities.")
        lines.append("")

    # Win highlights ONLY (no losses) - filter to 15%+ gains
    if ctx.winners:
        lines.append("Win Highlights:")
        for win in ctx.winners[:3]:
            theme = win.get('theme', '')
            theme_text = f" ({theme})" if theme else ""
            lines.append(f"${win['ticker']}: +{win['pnl_pct']:.1f}%{theme_text}")
        lines.append("")

    # Scanner stats
    lines.append("This Week's Scan:")
    lines.append(f"{ctx.scan_stats.get('tickers_loaded', 1817)} stocks analyzed")
    lines.append(f"{len(ctx.pass_signals)} cleared all 5 gates")
    lines.append("")

    lines.append("Full analysis in Saturday's Sterling Signals newsletter.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")

    return "\n".join(lines)


def generate_thursday_note_template(ctx: NoteContext) -> str:
    """
    Generate Thursday 'Trade Spotlight' note (template fallback).

    Focus: New signals, ongoing trade highlights, week outlook.
    """
    lines = []
    lines.append(f"Trade Spotlight - Week {ctx.week_number}")
    lines.append("")

    if ctx.pass_signals:
        sig = ctx.pass_signals[0]
        if len(ctx.pass_signals) == 1:
            lines.append(f"This Week's GREEN Signal: ${sig['symbol']}")
        else:
            lines.append(f"{len(ctx.pass_signals)} GREEN Signals This Week")
            for s in ctx.pass_signals[:5]:
                lines.append(f"${s['symbol']} ({s.get('theme', 'N/A')})")
            lines.append("")
            lines.append(f"Featured: ${sig['symbol']}")
        lines.append(f"Theme: {sig.get('theme', 'N/A')}")
        conviction_text = get_conviction_text(sig.get('conviction', 0))
        lines.append(f"Outlook: {conviction_text}")
        lines.append("")

        bullish = sig.get('bullish_factors', [])
        if bullish:
            lines.append("Why we like it:")
            for factor in bullish[:3]:
                factor_short = factor[:80] + "..." if len(factor) > 80 else factor
                lines.append(factor_short)
        lines.append("")

    elif ctx.consider_signals:
        sig = ctx.consider_signals[0]
        lines.append(f"On the Watchlist: ${sig['symbol']}")
        lines.append(f"Theme: {sig.get('theme', 'N/A')}")
        lines.append(f"Status: Watching (not yet actionable)")
        lines.append("")

    else:
        lines.append("No new signals this week")
        lines.append("")
        lines.append("Scanner found limited setups meeting our criteria.")
        lines.append("Sometimes the best trade is no trade.")

    lines.append("")

    # Scan stats
    if ctx.scan_stats:
        lines.append("This Week's Scan:")
        lines.append(f"{ctx.scan_stats.get('tickers_loaded', 0)} stocks analyzed")
        lines.append(f"{ctx.scan_stats.get('technical_signals', 0)} passed technical gates")
        lines.append(f"{ctx.scan_stats.get('final_trade', 0)} GREEN signals (full clearance)")
        lines.append(f"{ctx.scan_stats.get('final_consider', 0)} on watchlist")

    lines.append("")

    # Top winner only
    if ctx.top_performer and ctx.top_performer.get('pnl_pct', 0) >= MIN_WIN_THRESHOLD:
        top = ctx.top_performer
        lines.append(f"Top Winner: ${top['ticker']} (+{top['pnl_pct']:.1f}%)")

    lines.append("")
    lines.append("Full analysis in Saturday's Sterling Signals newsletter.")
    lines.append("")
    lines.append("Not financial advice. Informational only.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_note(content: str, filename: str, current_dir: Path, week_dir: Path):
    """Save note to both current/ and weekly archive directories."""
    # Save to current/
    current_path = current_dir / "substack_notes" / filename
    with open(current_path, 'w') as f:
        f.write(content)

    # Save to weekly archive
    week_path = week_dir / "substack_notes" / filename
    with open(week_path, 'w') as f:
        f.write(content)

    return current_path, week_path


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all_notes(
    no_llm: bool = False,
    dry_run: bool = False,
    tuesday_only: bool = False,
    thursday_only: bool = False,
) -> Dict[str, Path]:
    """
    Generate Tuesday and/or Thursday notes.

    Args:
        no_llm: Use template fallback (no API cost)
        dry_run: Print to stdout, don't save
        tuesday_only: Generate Tuesday note only
        thursday_only: Generate Thursday note only

    Returns:
        Dict of {note_name: path} for generated files.
    """
    print("\n" + "=" * 60)
    print("  SUBSTACK NOTES GENERATOR")
    if no_llm:
        print("  Mode: TEMPLATE (no LLM)")
    else:
        print("  Mode: LLM-POWERED (Claude Sonnet)")
    print("=" * 60)

    # Ensure output directories
    current_dir, week_dir = ensure_output_dirs()
    if not dry_run:
        print(f"\n  Output directories:")
        print(f"    Current: {current_dir}/substack_notes/")
        print(f"    Archive: {week_dir}/substack_notes/")

    # Build context
    ctx = build_note_context()

    # Determine which notes to generate
    note_types = []
    if tuesday_only:
        note_types = ["tuesday"]
    elif thursday_only:
        note_types = ["thursday"]
    else:
        note_types = ["tuesday", "thursday"]

    results = {}
    total_cost = 0.0

    for note_type in note_types:
        filename = f"{note_type}_note.md"
        label = "Tuesday (Portfolio Pulse)" if note_type == "tuesday" else "Thursday (Trade Spotlight)"

        print(f"\n  Generating {label}...")

        if no_llm:
            # Template fallback
            if note_type == "tuesday":
                content = generate_tuesday_note_template(ctx)
            else:
                content = generate_thursday_note_template(ctx)
            print(f"    Generated via template ({len(content.split())} words)")
        else:
            # LLM generation
            try:
                content, cost = generate_note_llm(note_type, ctx)
                total_cost += cost
                content = sanitize_note(content)
                print(f"    Generated via LLM ({len(content.split())} words, ${cost:.4f})")

                # Validate
                is_valid, issues = validate_note(content)

                if not is_valid:
                    print(f"    ⚠️  Validation issues: {issues}")
                    print(f"    Attempting repair...")

                    try:
                        repaired, repair_cost = repair_note(content, issues, note_type, ctx)
                        total_cost += repair_cost
                        repaired = sanitize_note(repaired)

                        is_valid_2, issues_2 = validate_note(repaired)
                        if is_valid_2:
                            content = repaired
                            print(f"    ✓ Repair successful (${repair_cost:.4f})")
                        else:
                            print(f"    ✗ Repair failed: {issues_2}")
                            print(f"    Falling back to template...")
                            if note_type == "tuesday":
                                content = generate_tuesday_note_template(ctx)
                            else:
                                content = generate_thursday_note_template(ctx)
                    except Exception as e:
                        print(f"    ✗ Repair error: {e}")
                        print(f"    Falling back to template...")
                        if note_type == "tuesday":
                            content = generate_tuesday_note_template(ctx)
                        else:
                            content = generate_thursday_note_template(ctx)
                else:
                    print(f"    ✓ Validation passed")

            except Exception as e:
                print(f"    ✗ LLM error: {e}")
                print(f"    Falling back to template...")
                if note_type == "tuesday":
                    content = generate_tuesday_note_template(ctx)
                else:
                    content = generate_thursday_note_template(ctx)

        # Output
        if dry_run:
            print(f"\n{'=' * 60}")
            print(f"  {label.upper()} — DRY RUN PREVIEW")
            print(f"{'=' * 60}")
            print(content)
            print(f"{'=' * 60}\n")
        else:
            current_path, week_path = save_note(content, filename, current_dir, week_dir)
            results[note_type] = current_path
            print(f"    ✓ Saved to {current_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SUBSTACK NOTES {'PREVIEW' if dry_run else 'COMPLETE'}")
    print(f"{'=' * 60}")

    if not dry_run and results:
        print(f"\n  Files ready for Substack:")
        for note_type, path in results.items():
            print(f"    {note_type.capitalize()}:  {path}")

    if total_cost > 0:
        print(f"\n  LLM Cost: ${total_cost:.4f}")

    print("")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Substack Notes for mid-week engagement"
    )
    parser.add_argument(
        "--tuesday", action="store_true",
        help="Generate Tuesday note only"
    )
    parser.add_argument(
        "--thursday", action="store_true",
        help="Generate Thursday note only"
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Use template fallback (no API cost)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output without saving"
    )

    args = parser.parse_args()

    generate_all_notes(
        no_llm=getattr(args, 'no_llm', False),
        dry_run=getattr(args, 'dry_run', False),
        tuesday_only=args.tuesday,
        thursday_only=args.thursday,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
