#!/usr/bin/env python3
"""
Shared utilities for Substack note generation.

Extracted from notes_generator.py to support notes_batch_generator.py
after the original module was archived.

Exports:
    NoteContext          — Aggregated data for note generation
    build_note_context   — Load portfolio/signals/prices and build NoteContext
    sanitize_note        — Clean up LLM output for Substack Notes
    validate_note        — Three-layer validation for generated notes
    repair_note          — LLM repair of a failed note
    save_note            — Save note to current/ and archive directories
    ensure_output_dirs   — Create current/ and weekly archive directories
    get_current_dir      — Get the substack 'current' output directory
    NOTES_SYSTEM_PROMPT  — System prompt for note generation/repair
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from config import SIGNALS_FILE, BRANDING, MODEL_NOTES
from config.output_paths import (
    get_scanner_current_dir,
    get_substack_current_dir,
    get_substack_archive_dir,
)
from config.banned_terms import check_banned_phrases, validate_content

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
- Show ALL positions transparently — winners AND losers.
- Frame losses positively: "Stop hit = system working as designed."
- Always show entry prices for full transparency.

Always end with: "Not financial advice. Informational only."
"""


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
    winners: List[Dict] = field(default_factory=list)
    big_winners: List[Dict] = field(default_factory=list)
    top_performer: Optional[Dict] = None
    pass_signals: List[Dict] = field(default_factory=list)
    consider_signals: List[Dict] = field(default_factory=list)
    themes: List[Dict] = field(default_factory=list)
    scan_stats: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_week_dir() -> Path:
    """Get the current week's substack archive directory (YYYY-WXX format)."""
    return get_substack_archive_dir()


def get_current_dir() -> Path:
    """Get the substack 'current' output directory for latest outputs."""
    return get_substack_current_dir()


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
    from portfolio.manager import load_portfolio as _load
    return _load()


def load_signals() -> Dict:
    """Load latest signals.json."""
    current_signals = get_scanner_current_dir() / "signals.json"
    root_signals = SIGNALS_FILE

    for path in [current_signals, root_signals]:
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
    return {}


def get_live_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch current prices for tickers via yfinance."""
    if not tickers or yf is None:
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
    if yf is None:
        return spy_pct, qqq_pct
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
    """Load market analysis excerpt from current/market_analysis.md."""
    path = get_current_dir() / "market_analysis.md"
    if path.exists():
        try:
            content = path.read_text()
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


def build_note_context(live_data: Optional[Dict] = None) -> NoteContext:
    """Build aggregated context for note generation.

    Args:
        live_data: Optional dict with pre-fetched live market data.
                   Keys: spy_change_pct, qqq_change_pct.
                   When provided, skips yfinance fetch for index performance.
    """
    print("  Loading data...")

    portfolio = load_portfolio()
    signals = load_signals()

    open_tickers = [t['ticker'] for t in portfolio if t.get('status') == 'OPEN']
    print(f"    Portfolio: {len(portfolio)} trades ({len(open_tickers)} open)")

    # Fetch live prices
    print("  Fetching live prices...")
    prices = get_live_prices(open_tickers)
    print(f"    Got prices for {len(prices)} tickers")

    # Index performance — use live_data if provided
    if live_data:
        spy_pct = live_data.get("spy_change_pct", 0.0)
        qqq_pct = live_data.get("qqq_change_pct", 0.0)
        print(f"    SPY 5d: {spy_pct:+.1f}%  |  QQQ 5d: {qqq_pct:+.1f}% (from live_data)")
    else:
        print("  Fetching index performance...")
        spy_pct, qqq_pct = get_index_performance()
        print(f"    SPY 5d: {spy_pct:+.1f}%  |  QQQ 5d: {qqq_pct:+.1f}%")

    # Market analysis excerpt
    market_excerpt = load_market_analysis()

    # Portfolio stats
    stats = calculate_portfolio_stats(portfolio, prices)

    # Show all positions (full transparency)
    all_positions = stats.get('positions', [])
    winners = all_positions
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

    print(f"    Positions: {len(winners)}  |  Big winners (25%+): {len(big_winners)}")
    print(f"    GREEN signals: {len(pass_signals)}  |  Themes: {len(themes)}")

    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION + SANITIZATION
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

    # Layer 2: Banned phrases
    banned_found = check_banned_phrases(content)
    if banned_found:
        issues.extend([f"Banned phrase: {p}" for p in banned_found])

    # Layer 3: Custom structural checks
    # No markdown headers
    if re.search(r'^#{1,3}\s', content, re.MULTILINE):
        issues.append("Contains markdown headers (# or ##)")

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
- Show all positions transparently; frame losses positively
- NEVER use banned terms: HMA, RSI, MACD, KDJ, Banker, UC, Undercurrent, BoS, ExD, profit lock, tiered stop, Gatekeeper, Investment Gate, conviction scores
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
