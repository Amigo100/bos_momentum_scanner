#!/usr/bin/env python3
"""
LIVE TWEET GENERATOR - Context-Aware Tweet Generation via Claude Sonnet
=======================================================================

Takes Grok's live market context + portfolio data, decides what type of
tweet to post based on current conditions, generates 3 account variants
via Claude Sonnet, validates through a 14-step pipeline, and writes to
the live content queue.

Diversity controls (ported from batch system):
- RecentTweetTracker: cross-cron-run state from live_content_queue.json
- get_diverse_tickers(): time-based rotation instead of static top-N
- Category balance enforcement via weekly targets
- Opening sentence + phrase cooldown injection into prompts
- Queue dedup, portfolio fabrication check, defeatist language filter

Usage:
    python -m content.live_tweet_generator                          # Full run
    python -m content.live_tweet_generator --dry-run                # Don't write queue
    python -m content.live_tweet_generator --force-type RECEIPT     # Force tweet type
    python -m content.live_tweet_generator --context PATH           # Custom context file

Environment Variables:
    ANTHROPIC_API_KEY  - Claude API key (required)
"""

import os
import sys
import csv
import json
import re
import random
import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from zoneinfo import ZoneInfo

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

from content.models import (
    Tweet, ValidationResult, VALID_CATEGORIES,
    CHART_REQUIRED_CATEGORIES, INTERNAL_TERM_PATTERNS,
)
from config.banned_terms import (
    ALL_BANNED, CRITICAL_BANNED, check_banned_phrases, check_loser_focus,
)
from content.live_context_gatherer import is_market_open, is_extended_hours

try:
    from core.portfolio_manager import fetch_current_prices
except ImportError:
    fetch_current_prices = None


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from config import (
        TRADES_DIR, LIVE_QUEUE_FILE,
        MAX_TWEETS_PER_DAY, MAX_SAME_TICKER_PER_DAY,
        MIN_HOURS_BETWEEN_SAME_TICKER, CONTEXT_STALENESS_HOURS,
        MODEL_LIVE_TWEET, WEEKEND_MAX_TWEETS, WEEKEND_CATEGORIES as _WEEKEND_CATS,
        PERSONAS, get_persona,
    )
    MODEL = MODEL_LIVE_TWEET
    WEEKEND_CATEGORIES = set(_WEEKEND_CATS)  # Config stores List, local needs Set
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TRADES_DIR = BASE_DIR / "trades"
    LIVE_QUEUE_FILE = TRADES_DIR / "live_content_queue.json"
    MODEL = "claude-sonnet-4-5-20250929"
    MAX_TWEETS_PER_DAY = 12
    WEEKEND_MAX_TWEETS = 4
    MAX_SAME_TICKER_PER_DAY = 3
    MIN_HOURS_BETWEEN_SAME_TICKER = 3
    CONTEXT_STALENESS_HOURS = 4
    WEEKEND_CATEGORIES = {"EDUCATIONAL", "ENGAGEMENT", "NEWSLETTER_CTA", "RECEIPT", "SIGNAL_ALERT"}

# Local-only constants (not in config)
PORTFOLIO_FILE = TRADES_DIR / "portfolio.csv"
SIGNALS_FILE = TRADES_DIR / "signals.json"
LIVE_CONTEXT_FILE = TRADES_DIR / "live_context.json"
FAILED_TWEETS_FILE = TRADES_DIR / "failed_tweets.json"
STYLE_GUIDE_PATH = Path(__file__).resolve().parent.parent / "FINTWIT_STYLE_GUIDE.md"

MAX_TOKENS = 1500
MAX_TWEET_CHARS = 280
MAX_REPAIR_ATTEMPTS = 2

# Live system valid categories (subset of VALID_CATEGORIES)
LIVE_VALID_CATEGORIES = {
    "MARKET_REACTION", "RECEIPT", "SIGNAL_ALERT", "DIP_OPPORTUNITY",
    "THEME_MOMENTUM", "ENGAGEMENT", "EDUCATIONAL", "NEWSLETTER_CTA",
    "SELL_SIGNAL", "TECHNICAL_ANALYSIS", "WATCHLIST",
}

# ── Category-specific few-shot examples for live tweet prompting ──────────────
# Adapted from batch system + FINTWIT_STYLE_GUIDE.md. Injected into build_user_prompt().
LIVE_CATEGORY_EXAMPLES: Dict[str, str] = {
    "SIGNAL_ALERT": (
        '1) "Friday scan done. $INOD at $61.54 and $RCAT at $13.25 cleared all gates. '
        'Institutional Accumulation Divergence confirmed. Full breakdown in the newsletter."\n'
        '2) "1,800 stocks. 5 gates. 2 survivors this week. '
        "Quality over quantity — that's the whole point.\""
    ),
    "SELL_SIGNAL": (
        '1) "$SMCI setup invalidated below $36. Win more than you lose. Moving on."\n'
        '2) "Lost on $VNET. Setup broke. System said exit, I exited. '
        "Can't win every trade. Next.\""
    ),
    "RECEIPT": (
        '1) "$RCAT from $8.50 to $13.25. +55.9% and counting. Drone tech thesis playing out."\n'
        '2) "We beat the market again this week.\\n\\n'
        '$STRL +47%\\n$MOD +32%\\n$FIX +28%\\n\\n'
        'Meanwhile... S&P 500 +1.2%"'
    ),
    "TECHNICAL_ANALYSIS": (
        '1) "$WCC holding above $281 entry. Watching $320 resistance for breakout '
        'continuation. Invalidated below $256. NFA"\n'
        '2) "$STRL cleared $400 resistance — Structural Pivot confirmed. '
        'Invalidation on close below $362 entry. NFA!"'
    ),
    "WATCHLIST": (
        '1) "On my radar: $IONQ at $42.15. Theme alignment is there. '
        'Waiting for momentum confirmation. NFA."\n'
        '2) "Watching closely: $QBTS at $6.20. Need one more gate to clear. '
        'Will update when it does."'
    ),
    "THEME_MOMENTUM": (
        '1) "If you missed Gold and Silver...\\n\\nThe Copper bull run might be next:\\n\\n'
        '$TMQ at $6.21\\n$FCX at $60.41\\n$SCCO at $184.30\\n\\n'
        'Probably want to save this post!"\n'
        '2) "AI Infrastructure keeps leading. $NVDA, $SMCI, $AVGO — institutional '
        'accumulation across the board. Structural trend confirmed."'
    ),
    "NEWSLETTER_CTA": (
        '1) "$RCAT from $8.50 to $13.25 (+55.9%). How we found it before the move — '
        'full breakdown in the newsletter."\n'
        '2) "1,800 stocks scanned. 5 gates. 2 survivors. '
        'The full analysis drops every Saturday. Link in bio."'
    ),
    "EDUCATIONAL": (
        '1) "Position sizing 101: If a loss makes you emotional, you sized too big. '
        'Risk-defined entries, always."\n'
        "2) \"Why 5 gates? Because 'good stock' is subjective. "
        "Gates are binary. Removes emotion. That's the point.\""
    ),
    "ENGAGEMENT": (
        "1) \"What's your biggest trading lesson this year? "
        'Mine: stop arguing with the data."\n'
        '2) "Bad day? Happens to everyone. What matters is not letting '
        'a bad day become a bad week."'
    ),
    "MARKET_REACTION": (
        '1) "SPY down 1.5% but our names holding relative strength. '
        '$STRL green, $RCAT flat. That tells you something about conviction."\n'
        '2) "Volatile day. VIX spiking. This is where discipline matters — '
        'no panic sells, trust the system."'
    ),
    "DIP_OPPORTUNITY": (
        '1) "Market pulling back hard. SPY -2%. But $RCAT holding its 20d MA — '
        'relative strength in a weak tape. Watching closely."\n'
        '2) "Sell the rip, buy the dip? Only if the structure is intact. '
        '$WCC still above entry. NFA."'
    ),
}

# Account variant mapping
ACCOUNT_VARIANTS = ["variant_1", "variant_2", "variant_3"]

# Import diversity constants (with fallbacks for safety)
try:
    from config import (
        CATEGORY_WEEKLY_TARGETS, MAX_SAME_CATEGORY_PER_DAY,
        QUEUE_DEDUP_HOURS, QUEUE_DEDUP_THRESHOLD,
        OPENING_DEDUP_THRESHOLD, MAX_OPENING_HISTORY,
    )
except ImportError:
    CATEGORY_WEEKLY_TARGETS = {
        "RECEIPT": 12, "SIGNAL_ALERT": 7, "MARKET_REACTION": 7,
        "THEME_MOMENTUM": 5, "EDUCATIONAL": 3, "ENGAGEMENT": 5,
        "NEWSLETTER_CTA": 2, "DIP_OPPORTUNITY": 4,
    }
    MAX_SAME_CATEGORY_PER_DAY = 3
    QUEUE_DEDUP_HOURS = 48
    QUEUE_DEDUP_THRESHOLD = 0.80
    OPENING_DEDUP_THRESHOLD = 0.70
    MAX_OPENING_HISTORY = 10


# ═══════════════════════════════════════════════════════════════════════════════
# RECENT TWEET TRACKER (cross-cron-run state from live queue)
# ═══════════════════════════════════════════════════════════════════════════════

class RecentTweetTracker:
    """Derives diversity state from live_content_queue.json.

    Each cron invocation is stateless — this class scans the existing queue
    once at startup and builds lookup tables for diversity enforcement.
    Consolidates the ad-hoc functions (recently_tweeted, count_tweets_today, etc.)
    into a single queue scan.
    """

    def __init__(self, recent_tweets: List[Dict]):
        self._now_et = datetime.now(ZoneInfo("America/New_York"))
        self._today = self._now_et.date()

        # All counters
        self.tickers_today: Dict[str, int] = {}
        self.categories_today: Dict[str, int] = {}
        self.categories_this_week: Dict[str, int] = {}
        self.recent_openings: List[str] = []
        self.recent_tickers_by_account: Dict[str, List[Tuple[str, datetime]]] = {}
        self.last_category_per_account: Dict[str, str] = {}
        self.recently_used_phrases: Set[str] = set()
        self._tweets_today_count = 0

        week_start = self._now_et - timedelta(days=7)
        dedup_cutoff = self._now_et - timedelta(hours=QUEUE_DEDUP_HOURS)

        # Single scan of entire queue
        for t in recent_tweets:
            status = t.get("status", "")
            if status not in ("pending", "posted", "failed"):
                continue

            gen_str = t.get("generated_at", "2000-01-01")
            try:
                gen = datetime.fromisoformat(gen_str)
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                gen_et = gen.astimezone(ZoneInfo("America/New_York"))
            except (ValueError, TypeError):
                continue

            ticker = (t.get("primary_ticker") or "").lstrip("$")
            category = t.get("category", "")
            account = t.get("account", "")
            text = t.get("text", "")

            # Today counts (only pending/posted for cap enforcement)
            if gen_et.date() == self._today and status in ("pending", "posted"):
                self._tweets_today_count += 1
                if ticker:
                    self.tickers_today[ticker] = self.tickers_today.get(ticker, 0) + 1
                if category:
                    self.categories_today[category] = self.categories_today.get(category, 0) + 1

            # Weekly category counts
            if gen_et > week_start and status in ("pending", "posted"):
                if category:
                    self.categories_this_week[category] = self.categories_this_week.get(category, 0) + 1

            # Recent openings (last 48h, for dedup)
            if gen_et > dedup_cutoff and text:
                opening = text[:60]
                if len(self.recent_openings) < MAX_OPENING_HISTORY:
                    self.recent_openings.append(opening)

            # Per-account ticker history (last 48h)
            if gen_et > dedup_cutoff and account and ticker:
                if account not in self.recent_tickers_by_account:
                    self.recent_tickers_by_account[account] = []
                self.recent_tickers_by_account[account].append((ticker, gen_et))

            # Last category per account (most recent)
            if account and category:
                existing = self.last_category_per_account.get(account)
                if existing is None:
                    self.last_category_per_account[account] = category

            # Power phrases from last 48h
            if gen_et > dedup_cutoff and text:
                # Extract short punchy fragments (4-8 word sequences) for phrase cooldown
                words = text.split()
                for start in range(0, len(words) - 3):
                    phrase = " ".join(words[start:start + 5]).lower()
                    if len(phrase) >= 15:
                        self.recently_used_phrases.add(phrase)

    @property
    def tweets_today(self) -> int:
        return self._tweets_today_count

    def ticker_at_daily_limit(self, ticker: str) -> bool:
        ticker = ticker.lstrip("$")
        return self.tickers_today.get(ticker, 0) >= MAX_SAME_TICKER_PER_DAY

    def ticker_recent_for_account(self, ticker: str, account: str, hours: int = 3) -> bool:
        """Check if ticker was used by this account within N hours."""
        ticker = ticker.lstrip("$")
        cutoff = self._now_et - timedelta(hours=hours)
        for t, gen_et in self.recent_tickers_by_account.get(account, []):
            if t == ticker and gen_et > cutoff:
                return True
        return False

    def category_over_weekly_budget(self, category: str) -> bool:
        target = CATEGORY_WEEKLY_TARGETS.get(category, 999)
        return self.categories_this_week.get(category, 0) >= target

    def category_at_daily_limit(self, category: str) -> bool:
        return self.categories_today.get(category, 0) >= MAX_SAME_CATEGORY_PER_DAY

    def opening_too_similar(self, text: str) -> bool:
        """Check if opening of text is too similar to recent openings."""
        opening = text[:60].lower()
        for prev in self.recent_openings:
            similarity = SequenceMatcher(None, opening, prev.lower()).ratio()
            if similarity > OPENING_DEDUP_THRESHOLD:
                return True
        return False

    def tweet_too_similar_to_queue(self, text: str) -> bool:
        """Check if full tweet is too similar to any recent tweet."""
        text_lower = text.lower()
        # We only check openings list — full text dedup is in validate_tweet
        # This method is available for pre-generation checks
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}


def load_json_list(path: Path) -> list:
    """Load JSON file as list, return empty list if missing or invalid."""
    if not path.exists():
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def load_portfolio(path: Optional[Path] = None) -> List[Dict]:
    """Load open positions from portfolio.csv."""
    p = path or PORTFOLIO_FILE
    if not p.exists():
        return []
    positions = []
    with open(p, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'OPEN':
                row['entry_price'] = float(row.get('entry_price') or 0)
                positions.append(row)
    return positions


def load_recent_tweets() -> List[Dict]:
    """Load recent tweets from live content queue."""
    return load_json_list(LIVE_QUEUE_FILE)


def load_style_guide() -> str:
    """Load style guide from file or use embedded fallback."""
    if STYLE_GUIDE_PATH.exists():
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    return (
        "Write tweets in confident, casual FinTwit voice. <=280 chars. "
        "Always include specific tickers and prices. NFA. "
        "Sound like a real trader, not a corporate account."
    )


def build_allowed_tickers(portfolio: List[Dict], signals: dict) -> Set[str]:
    """Build set of all valid tickers from portfolio + signals."""
    tickers = set()
    for row in portfolio:
        t = row.get('ticker', '').upper()
        if t:
            tickers.add(t)
    for sig in signals.get('buy_signals', []):
        t = sig.get('symbol', '').upper()
        if t:
            tickers.add(t)
    for sig in signals.get('consider_signals', []):
        t = sig.get('symbol', '').upper()
        if t:
            tickers.add(t)
    return tickers


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION LOGIC (PRD Section 14)
# ═══════════════════════════════════════════════════════════════════════════════

def recently_tweeted(ticker: str, recent_tweets: List[Dict], hours: int = 3) -> bool:
    """Check if ticker was tweeted about in last N hours."""
    # Strip $ prefix if present
    ticker = ticker.lstrip('$')
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted", "failed"):
            continue
        pt = (t.get("primary_ticker") or "").lstrip('$')
        if pt == ticker:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def recently_tweeted_theme(theme: str, recent_tweets: List[Dict], hours: int = 6) -> bool:
    """Check if theme was tweeted about in last N hours."""
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    theme_lower = theme.lower()
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted", "failed"):
            continue
        text_lower = t.get("text", "").lower()
        if theme_lower in text_lower:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def recently_tweeted_type(tweet_type: str, recent_tweets: List[Dict], hours: int = 4) -> bool:
    """Check if this tweet type was used in last N hours."""
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted", "failed"):
            continue
        if t.get("category") == tweet_type:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def count_tweets_today(recent_tweets: List[Dict]) -> int:
    """Count tweets generated today."""
    today = datetime.now(ZoneInfo("America/New_York")).date()
    count = 0
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        try:
            gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
            if gen.date() == today:
                count += 1
        except (ValueError, TypeError):
            pass
    return count


def count_ticker_today(ticker: str, recent_tweets: List[Dict]) -> int:
    """Count how many times a ticker was tweeted today."""
    ticker = ticker.lstrip('$')
    today = datetime.now(ZoneInfo("America/New_York")).date()
    count = 0
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        pt = (t.get("primary_ticker") or "").lstrip('$')
        if pt == ticker:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.date() == today:
                    count += 1
            except (ValueError, TypeError):
                pass
    return count


def _count_category_this_week(category: str, recent_tweets: List[Dict]) -> int:
    """Count how many tweets of a given category were posted in the last 7 days."""
    week_start = datetime.now(ZoneInfo("America/New_York")) - timedelta(days=7)
    count = 0
    for t in recent_tweets:
        if t.get("category") != category:
            continue
        if t.get("status") not in ("pending", "posted"):
            continue
        try:
            gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=ZoneInfo("UTC"))
            if gen > week_start:
                count += 1
        except (ValueError, TypeError):
            pass
    return count


def should_post_newsletter_cta(recent_tweets: List[Dict], target_per_week: int = 2) -> bool:
    """Check if newsletter CTA is due (2x/week)."""
    week_start = datetime.now(ZoneInfo("America/New_York")) - timedelta(days=7)
    ctas = 0
    for t in recent_tweets:
        if t.get("category") != "NEWSLETTER_CTA":
            continue
        try:
            gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=ZoneInfo("UTC"))
            if gen > week_start:
                ctas += 1
        except (ValueError, TypeError):
            pass
    return ctas < target_per_week


def get_best_performing_tickers(portfolio: List[Dict], n: int = 1) -> List[str]:
    """Get the top N performing tickers from portfolio by P&L%.

    DEPRECATED: Use get_diverse_tickers() instead for diversity-aware selection.
    Kept for backward compatibility with any external callers.
    """
    scored = []
    for row in portfolio:
        entry = float(row.get('entry_price') or 0)
        highest = float(row.get('highest_close') or 0)
        if entry > 0 and highest > 0:
            pnl = ((highest - entry) / entry) * 100
            scored.append((row['ticker'], pnl))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:n]]


def get_diverse_tickers(
    portfolio: List[Dict],
    n: int = 1,
    tracker: Optional["RecentTweetTracker"] = None,
    exclude: Optional[Set[str]] = None,
) -> List[str]:
    """Get N performing tickers with diversity-aware rotation.

    Unlike get_best_performing_tickers() which always returns the same top N,
    this applies:
    1. Filter out tickers over daily limit (via tracker)
    2. Filter out explicit exclusions (tickers already assigned in current slot)
    3. Only positive P&L tickers (never losers)
    4. Time-based deterministic rotation offset — different tickers at different hours
    """
    exclude = exclude or set()

    # Score all positive positions
    scored = []
    for row in portfolio:
        entry = float(row.get('entry_price') or 0)
        highest = float(row.get('highest_close') or 0)
        if entry > 0 and highest > 0:
            pnl = ((highest - entry) / entry) * 100
            if pnl > 0:
                scored.append((row['ticker'], pnl))
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter out daily-limited and excluded tickers
    eligible = []
    for ticker, pnl in scored:
        if ticker in exclude:
            continue
        if tracker and tracker.ticker_at_daily_limit(ticker):
            continue
        eligible.append(ticker)

    if not eligible:
        # Fallback: return top by P&L ignoring limits (better than empty)
        return [t for t, _ in scored[:n]]

    # Time-based rotation offset — deterministic, not random
    # Different tickers surface at different 3-hour windows
    now_et = datetime.now(ZoneInfo("America/New_York"))
    offset = (now_et.hour // 3) % max(len(eligible), 1)

    # Rotate and return
    rotated = eligible[offset:] + eligible[:offset]
    return rotated[:n]


def find_tickers_for_theme(theme: str, portfolio: List[Dict], signals: dict) -> List[str]:
    """Find tickers matching a theme from portfolio and signals."""
    theme_lower = theme.lower()
    tickers = []
    for row in portfolio:
        if theme_lower in (row.get('theme') or '').lower():
            tickers.append(row['ticker'])
    for sig in signals.get('buy_signals', []):
        if theme_lower in (sig.get('theme') or '').lower():
            tickers.append(sig.get('symbol', ''))
    return [t for t in tickers if t][:3]


def _prepare_slot_data(
    decision: Dict, portfolio: List[Dict], signals: Dict,
    tracker: Optional["RecentTweetTracker"] = None,
) -> Dict[str, Dict]:
    """
    Prepare per-account slot assignments with diversity-aware ticker selection.

    Uses tracker to avoid:
    - Tickers already at daily limit
    - Same ticker on same account within MIN_HOURS_BETWEEN_SAME_TICKER
    - Same category consecutively on same account

    When <3 unique tickers remain, switches that variant to a non-ticker
    category (EDUCATIONAL/ENGAGEMENT) instead of reusing the same ticker.

    Returns:
        {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "EDUCATIONAL", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "MARKET_REACTION", "angle": "punchy-direct"},
        }
    """
    candidates = []

    # 1. Decision tickers (highest priority) — filtered by tracker
    for t in decision.get("tickers", []):
        t = t.lstrip('$')
        if t and not (tracker and tracker.ticker_at_daily_limit(t)):
            candidates.append(t)

    # 2. Portfolio winners via get_diverse_tickers (rotation-aware)
    diverse = get_diverse_tickers(
        portfolio, n=8, tracker=tracker,
        exclude=set(candidates),
    )
    for t in diverse:
        if t not in candidates:
            candidates.append(t)

    # 3. Fresh scanner buy_signals
    for sig in signals.get('buy_signals', []):
        sym = sig.get('symbol', '').upper()
        if sym and sym not in candidates:
            if not (tracker and tracker.ticker_at_daily_limit(sym)):
                candidates.append(sym)

    # Assign to 3 accounts — different tickers when possible
    category = decision.get("type", "ENGAGEMENT")
    angles = ["data-driven", "explains-why", "punchy-direct"]
    # Alternate categories for persona variety
    angle_categories = {
        "data-driven": category,
        "explains-why": "EDUCATIONAL" if category not in ("EDUCATIONAL", "ENGAGEMENT") else category,
        "punchy-direct": category,
    }

    slot_data = {}
    used_tickers = set()

    for i, variant in enumerate(ACCOUNT_VARIANTS):
        # Find next unused ticker, also checking per-account recency
        ticker = ""
        for c in candidates:
            if c in used_tickers:
                continue
            # Per-account recency check
            if tracker and tracker.ticker_recent_for_account(
                c, variant, hours=MIN_HOURS_BETWEEN_SAME_TICKER
            ):
                continue
            ticker = c
            used_tickers.add(c)
            break

        angle = angles[i]

        if not ticker:
            # No unique ticker available — switch to non-ticker category
            # instead of reusing (prevents identical tweets across accounts)
            non_ticker_cats = ["EDUCATIONAL", "ENGAGEMENT"]
            fallback_cat = non_ticker_cats[i % len(non_ticker_cats)]
            slot_data[variant] = {
                "ticker": "",
                "category": fallback_cat,
                "angle": angle,
            }
        else:
            # Check if same category as last tweet for this account
            acct_cat = angle_categories.get(angle, category)
            if tracker and tracker.last_category_per_account.get(variant) == acct_cat:
                # Rotate to a different category
                alt_cats = [c for c in LIVE_VALID_CATEGORIES
                            if c != acct_cat and not (tracker and tracker.category_at_daily_limit(c))]
                if alt_cats:
                    acct_cat = alt_cats[i % len(alt_cats)]

            slot_data[variant] = {
                "ticker": ticker,
                "category": acct_cat,
                "angle": angle,
            }

    return slot_data


def _is_category_over_budget(category: str, tracker: Optional["RecentTweetTracker"]) -> bool:
    """Check if a category has exceeded its weekly target or daily limit."""
    if tracker is None:
        return False
    return tracker.category_over_weekly_budget(category) or tracker.category_at_daily_limit(category)


def _get_time_context() -> str:
    """Return time-of-day framing guidance based on current ET hour."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    hour = now_et.hour
    is_weekend = now_et.weekday() >= 5

    if is_weekend:
        return "Markets closed — review, education, upcoming week prep"
    if hour < 9 or (hour == 9 and now_et.minute < 30):
        return "Pre-market — frame for the day ahead, what to watch at the open"
    if 15 <= hour < 16:
        return "Power Hour — relative strength matters now, who's holding gains?"
    if 16 <= hour < 18:
        return "After hours — daily wrap, how did positions close?"
    if hour >= 18:
        return "Evening — reflection, education, upcoming catalysts"
    return ""


def decide_tweet_type(
    context: Dict, portfolio: List[Dict], signals: Dict, recent_tweets: List[Dict],
    tracker: Optional["RecentTweetTracker"] = None,
) -> Dict:
    """
    Decide what type of tweet to post based on current market conditions.

    With tracker, enforces category balance — if a chosen type is over budget,
    falls through to next priority level.

    Returns: {"action": "tweet"|"skip", "type": str, "reason": str, "tickers": list, "urgency": str}
    """
    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    opportunities = context.get("tweet_opportunities", [])
    is_weekend = datetime.now(ZoneInfo("America/New_York")).weekday() >= 5

    # Check daily tweet count
    tweets_today = tracker.tweets_today if tracker else count_tweets_today(recent_tweets)
    max_today = WEEKEND_MAX_TWEETS if is_weekend else MAX_TWEETS_PER_DAY
    if tweets_today >= max_today:
        return {"action": "skip", "reason": f"Daily cap reached ({tweets_today}/{max_today})"}

    now_et = datetime.now(ZoneInfo("America/New_York"))

    # ── P0: Sell/exit signals (ALWAYS highest priority) ────────────────────
    if not _is_category_over_budget("SELL_SIGNAL", tracker):
        for sig in signals.get("sell_signals", []) + signals.get("exit_signals", []):
            ticker = sig.get("symbol", "").upper()
            if ticker and not recently_tweeted(ticker, recent_tweets, hours=12):
                if not (tracker and tracker.ticker_at_daily_limit(ticker)):
                    return {
                        "action": "tweet",
                        "type": "SELL_SIGNAL",
                        "reason": f"Exit signal: ${ticker} — {sig.get('reason', '')}",
                        "tickers": [ticker],
                        "urgency": "high",
                    }

    # ── P1: Fresh scanner signals (< 72h old PASS/buy signals) ─────────────
    # Extended from 48h to cover Sunday PM for Friday scans
    signal_timestamp = signals.get("timestamp", "")
    if signal_timestamp and not _is_category_over_budget("SIGNAL_ALERT", tracker):
        try:
            signal_time = datetime.strptime(signal_timestamp, "%Y-%m-%d %H:%M:%S")
            signal_time = signal_time.replace(tzinfo=ZoneInfo("America/New_York"))
            hours_since_scan = (now_et - signal_time).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_since_scan = 999

        if hours_since_scan < 72:
            for sig in signals.get("buy_signals", []):
                ticker = sig.get("symbol", "").upper()
                if ticker and not recently_tweeted(ticker, recent_tweets, hours=6):
                    if tracker and tracker.ticker_at_daily_limit(ticker):
                        continue
                    is_sunday_pm = now_et.weekday() == 6 and now_et.hour >= 15
                    return {
                        "action": "tweet",
                        "type": "SIGNAL_ALERT",
                        "reason": f"Fresh scanner signal: ${ticker} (scan {hours_since_scan:.0f}h ago)",
                        "tickers": [ticker],
                        "urgency": "high" if is_sunday_pm else "medium",
                    }

    # ── P2: Portfolio movers — positive (RECEIPT) ──────────────────────────
    for mover in movers:
        try:
            move_str = str(mover.get("move", "0")).replace("%", "").replace("+", "")
            pct = float(move_str)
        except (ValueError, TypeError):
            continue
        if pct < 2.0:
            continue
        ticker = mover.get("ticker", "").lstrip('$')
        if not ticker or recently_tweeted(ticker, recent_tweets, hours=MIN_HOURS_BETWEEN_SAME_TICKER):
            continue
        if tracker and tracker.ticker_at_daily_limit(ticker):
            continue
        if _is_category_over_budget("RECEIPT", tracker):
            continue
        return {
            "action": "tweet",
            "type": "RECEIPT",
            "reason": f"${ticker} moving {mover.get('move', '?')}: {mover.get('context', '')}",
            "tickers": [ticker],
            "urgency": "high",
        }

    # ── P3: Market reaction — negative movers / volatile mood ──────────────
    if not is_weekend:
        # Check negative movers first
        for mover in movers:
            try:
                move_str = str(mover.get("move", "0")).replace("%", "").replace("+", "")
                pct = float(move_str)
            except (ValueError, TypeError):
                continue
            if pct > -2.0:
                continue
            ticker = mover.get("ticker", "").lstrip('$')
            if not ticker or recently_tweeted(ticker, recent_tweets, hours=MIN_HOURS_BETWEEN_SAME_TICKER):
                continue
            if tracker and tracker.ticker_at_daily_limit(ticker):
                continue
            tweet_type = "DIP_OPPORTUNITY" if pct < -3 else "MARKET_REACTION"
            if _is_category_over_budget(tweet_type, tracker):
                continue
            return {
                "action": "tweet",
                "type": tweet_type,
                "reason": f"${ticker} moving {mover.get('move', '?')}: {mover.get('context', '')}",
                "tickers": [ticker],
                "urgency": "high",
            }

        # Market mood commentary (volatile/bearish)
        mood = market.get("market_mood", "quiet")
        if (mood in ("volatile", "bearish")
                and not recently_tweeted_type("MARKET_REACTION", recent_tweets, hours=4)
                and not _is_category_over_budget("MARKET_REACTION", tracker)):
            return {
                "action": "tweet",
                "type": "MARKET_REACTION",
                "reason": f"Market mood: {mood} — {market.get('headline', '')}",
                "tickers": [m.get("ticker", "").lstrip('$') for m in movers[:2] if m.get("ticker")],
                "urgency": "medium",
            }

    # ── P4: Theme breakout ─────────────────────────────────────────────────
    if not _is_category_over_budget("THEME_MOMENTUM", tracker):
        active_themes = [t for t in themes if t.get("status") == "breaking"]
        for theme in active_themes:
            if not recently_tweeted_theme(theme["theme"], recent_tweets, hours=6):
                return {
                    "action": "tweet",
                    "type": "THEME_MOMENTUM",
                    "reason": f"{theme['theme']} breaking: {theme.get('detail', '')}",
                    "tickers": find_tickers_for_theme(theme["theme"], portfolio, signals),
                    "urgency": "high",
                }

    # ── P5: Position commentary — catalysts/tailwinds on held positions ────
    if (not is_weekend
            and not _is_category_over_budget("TECHNICAL_ANALYSIS", tracker)
            and not recently_tweeted_type("TECHNICAL_ANALYSIS", recent_tweets, hours=4)):
        commentary_tickers = get_diverse_tickers(portfolio, n=1, tracker=tracker)
        if commentary_tickers:
            ticker = commentary_tickers[0]
            sig_data = next(
                (s for s in signals.get("buy_signals", [])
                 if s.get("symbol", "").upper() == ticker),
                {},
            )
            catalyst = sig_data.get("catalyst_summary", "")
            bullish = sig_data.get("bullish_factors", [])
            return {
                "action": "tweet",
                "type": "TECHNICAL_ANALYSIS",
                "reason": f"Position commentary: ${ticker} — {catalyst or 'catalyst/tailwind check'}",
                "tickers": [ticker],
                "urgency": "low",
                "catalyst": catalyst,
                "bullish_factors": bullish,
            }

    # ── P6: Watchlist — CONSIDER signals from scan ─────────────────────────
    if not _is_category_over_budget("WATCHLIST", tracker):
        for sig in signals.get("consider_signals", []):
            ticker = sig.get("symbol", "").upper()
            if ticker and not recently_tweeted(ticker, recent_tweets, hours=12):
                if not (tracker and tracker.ticker_at_daily_limit(ticker)):
                    return {
                        "action": "tweet",
                        "type": "WATCHLIST",
                        "reason": f"Consider signal: ${ticker}",
                        "tickers": [ticker],
                        "urgency": "low",
                    }

    # ── P7: Grok-identified opportunities ──────────────────────────────────
    urgency_rank = {"high": 0, "medium": 1, "low": 2}
    for opp in sorted(opportunities, key=lambda x: urgency_rank.get(x.get("urgency", "low"), 3)):
        if opp.get("urgency") in ("high", "medium"):
            opp_type = opp.get("type", "MARKET_REACTION")
            if not _is_category_over_budget(opp_type, tracker):
                return {
                    "action": "tweet",
                    "type": opp_type,
                    "reason": opp.get("reason", "Grok-identified opportunity"),
                    "tickers": opp.get("tickers", []),
                    "urgency": opp.get("urgency", "medium"),
                }

    # ── P8: Newsletter CTA (2x/week) ──────────────────────────────────────
    if should_post_newsletter_cta(recent_tweets) and not _is_category_over_budget("NEWSLETTER_CTA", tracker):
        return {
            "action": "tweet",
            "type": "NEWSLETTER_CTA",
            "reason": "Scheduled newsletter CTA",
            "tickers": get_diverse_tickers(portfolio, n=1, tracker=tracker),
            "urgency": "low",
        }

    # ── P9: Multi-ticker portfolio receipt ─────────────────────────────────
    winners = [
        r for r in portfolio
        if float(r.get('entry_price', 0) or 0) > 0
        and float(r.get('highest_close', 0) or 0) > float(r.get('entry_price', 0) or 1) * 1.05
    ]
    if (len(winners) >= 3
            and not recently_tweeted_type("RECEIPT", recent_tweets, hours=24)
            and not _is_category_over_budget("RECEIPT", tracker)):
        top_tickers = [
            w['ticker'] for w in sorted(
                winners,
                key=lambda x: float(x.get('highest_close', 0) or 0) / max(float(x.get('entry_price', 0) or 1), 0.01),
                reverse=True,
            )[:5]
        ]
        return {
            "action": "tweet",
            "type": "RECEIPT",
            "reason": "Multi-ticker portfolio receipt — showcase winners",
            "tickers": top_tickers,
            "urgency": "low",
            "multi_receipt": True,
        }

    # ── P10: Filler (quiet days — weekday or weekend) ──────────────────────
    if tweets_today < 4:
        if is_weekend:
            safe_cats = sorted(WEEKEND_CATEGORIES & {"EDUCATIONAL", "ENGAGEMENT", "RECEIPT", "WATCHLIST"})
            filler_type = next(
                (c for c in safe_cats if not _is_category_over_budget(c, tracker)),
                safe_cats[0] if safe_cats else "ENGAGEMENT",
            )
        else:
            filler_type = next(
                (c for c in ["TECHNICAL_ANALYSIS", "EDUCATIONAL", "ENGAGEMENT"]
                 if not _is_category_over_budget(c, tracker)),
                "ENGAGEMENT",
            )
        return {
            "action": "tweet",
            "type": filler_type,
            "reason": "Quiet market — filler content with live context",
            "tickers": get_diverse_tickers(portfolio, n=1, tracker=tracker),
            "urgency": "low",
        }

    # ── Minimum daily cadence fallback ──────────────────────────────────────
    diverse_tickers = get_diverse_tickers(portfolio, n=1, tracker=tracker)

    if diverse_tickers and not recently_tweeted_type("RECEIPT", recent_tweets, hours=8) and not _is_category_over_budget("RECEIPT", tracker):
        return {
            "action": "tweet",
            "type": "RECEIPT",
            "reason": "Cadence fallback — showcase winning position",
            "tickers": diverse_tickers,
            "urgency": "low",
        }

    if (not recently_tweeted_type("TECHNICAL_ANALYSIS", recent_tweets, hours=6)
            and not _is_category_over_budget("TECHNICAL_ANALYSIS", tracker)):
        return {
            "action": "tweet",
            "type": "TECHNICAL_ANALYSIS",
            "reason": "Cadence fallback — position commentary",
            "tickers": diverse_tickers or [],
            "urgency": "low",
        }

    if (_count_category_this_week("EDUCATIONAL", recent_tweets) < 3
            and not recently_tweeted_type("EDUCATIONAL", recent_tweets, hours=6)
            and not _is_category_over_budget("EDUCATIONAL", tracker)):
        return {
            "action": "tweet",
            "type": "EDUCATIONAL",
            "reason": "Cadence fallback — educational content",
            "tickers": diverse_tickers or [],
            "urgency": "low",
        }

    if not recently_tweeted_type("ENGAGEMENT", recent_tweets, hours=6):
        return {
            "action": "tweet",
            "type": "ENGAGEMENT",
            "reason": "Cadence fallback — engagement content",
            "tickers": diverse_tickers or [],
            "urgency": "low",
        }

    return {"action": "skip", "reason": "No tweetable events and all cadence fallbacks exhausted"}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS (PRD Section 6.3-6.4)
# ═══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(
    style_guide: str, slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
) -> str:
    """Build the Sonnet system prompt for tweet generation.

    Args:
        style_guide: FinTwit style guide text
        slot_assignments: Optional per-account slot data from _prepare_slot_data()
        tracker: Optional RecentTweetTracker for opening/phrase dedup injection
    """
    banned_sample = ", ".join(f'"{t}"' for t in CRITICAL_BANNED[:40])

    # Build persona instructions if slot data available
    persona_block = ""
    if slot_assignments:
        persona_lines = []
        account_map = {
            "variant_1": "main",
            "variant_2": "account2",
            "variant_3": "account3",
        }
        prd_names = {
            "main": "Alex",
            "account2": "Rozalia",
            "account3": "James",
        }
        for variant, slot in slot_assignments.items():
            acct_key = account_map.get(variant, "main")
            persona = get_persona(acct_key)
            prd_name = prd_names.get(acct_key, "Alex")
            voice = persona.get("voice", {})
            traits = ", ".join(voice.get("traits", []))
            tone = voice.get("tone", "professional")
            phrases = persona.get("signature_phrases", [])
            phrase_hint = f'Style hint: "{phrases[0]}"' if phrases else ""

            persona_lines.append(
                f"- {variant} ({prd_name} — {persona.get('archetype', 'Analyst')}): "
                f"Tone = {tone}, traits = [{traits}]. "
                f"Angle = {slot.get('angle', 'general')}. {phrase_hint}"
            )

        persona_block = f"""
PERSONA DIFFERENTIATION (CRITICAL — these must sound like 3 different traders):
{chr(10).join(persona_lines)}
Each variant MUST have a distinctly different voice matching its persona above.
variant_1 = data-driven analyst, variant_2 = approachable mentor, variant_3 = punchy practitioner.
DO NOT just rearrange words — write as if 3 different people are tweeting.
"""

    # Opening sentence dedup block (injected from tracker)
    opening_block = ""
    if tracker and tracker.recent_openings:
        openings_list = "\n".join(f'- "{o}"' for o in tracker.recent_openings[:MAX_OPENING_HISTORY])
        opening_block = f"""
OPENING SENTENCE COOLDOWN (CRITICAL — do NOT start any tweet with these openings, already used recently):
{openings_list}
Start each tweet with a FRESH opening that is distinctly different from all of the above.
"""

    # Power phrase rotation block (injected from tracker)
    phrase_block = ""
    if tracker and tracker.recently_used_phrases:
        # Sample up to 20 phrases to avoid bloating prompt
        sample_size = min(20, len(tracker.recently_used_phrases))
        sampled = sorted(tracker.recently_used_phrases)[:sample_size]
        phrases_list = ", ".join(f'"{p}"' for p in sampled)
        phrase_block = f"""
PHRASE COOLDOWN — do not reuse these phrases (used in last 48h):
{phrases_list}
Use fresh wording and different sentence structures.
"""

    return f"""You are the voice of Sterling Signals, a momentum trading newsletter on FinTwit.

STYLE RULES (non-negotiable):
{style_guide}
{persona_block}{opening_block}{phrase_block}
YOUR TASK:
Generate exactly 3 tweet variants for the same moment. Each variant must:
- Sound like a different human wrote it (not just rearranged words)
- Be <=280 characters
- Contain at least one specific element (ticker, price, %, or named theme)
- Match the tone of these reference accounts: confident but not arrogant, specific not vague, casual not corporate

FORMATTING RULES:
- Return ONLY valid JSON — no markdown, no commentary
- Format: {{"tweets": [{{"text": "...", "category": "...", "primary_ticker": "...", "chart_recommended": true/false, "account": "variant_1|variant_2|variant_3"}}, ...]}}
- Categories: MARKET_REACTION, RECEIPT, SIGNAL_ALERT, DIP_OPPORTUNITY, THEME_MOMENTUM, ENGAGEMENT, EDUCATIONAL, NEWSLETTER_CTA, SELL_SIGNAL, TECHNICAL_ANALYSIS, WATCHLIST
- chart_recommended: true if tweet references a specific ticker with price action

ABSOLUTE BANS (NEVER use these terms):
{banned_sample}

ADDITIONAL RULES:
- Never fabricate tickers, prices, or percentages not in the provided data
- Never use: "our scanner", "filtered X stocks"
- "Save this post" / "bookmark this" — use SPARINGLY as a CTA, NOT in every tweet
- Never use hashtags
- Never exceed 280 characters
- Never mention losses or negative P&L
- Never use UK references (BST, GMT, GBP, ISA)
- Never reference being an AI, bot, or automated system
- Keep "NFA" to <=1 of the 3 variants
- SELL_SIGNAL tweets: Frame as "setup invalidated" or "win more than you lose". Never show loss amounts.
- TECHNICAL_ANALYSIS tweets: Comment on position with price levels, catalysts, or tailwinds. Include invalidation level.
- WATCHLIST tweets: Frame as "on my radar" or "watching closely". Waiting for confirmation.
- Output ONLY the JSON — no explanations"""


def format_portfolio_for_prompt(portfolio: List[Dict], current_prices: Optional[Dict[str, float]] = None) -> str:
    """Format portfolio data for the user prompt with current prices when available."""
    lines = []
    for row in portfolio:
        ticker = row.get('ticker', '')
        entry = float(row.get('entry_price') or 0)
        highest = float(row.get('highest_close') or 0)
        theme = row.get('theme', '')
        current = (current_prices or {}).get(ticker, 0.0)
        if entry > 0 and current > 0:
            pnl = ((current - entry) / entry) * 100
            lines.append(f"${ticker}: entry ${entry:.2f}, current ${current:.2f} ({pnl:+.1f}%), high ${highest:.2f} — {theme}")
        elif entry > 0 and highest > 0:
            pnl = ((highest - entry) / entry) * 100
            lines.append(f"${ticker}: entry ${entry:.2f}, high ${highest:.2f} ({pnl:+.1f}%) — {theme}")
        else:
            lines.append(f"${ticker}: entry ${entry:.2f} — {theme}")
    return "\n".join(lines) if lines else "No open positions"


def build_user_prompt(
    decision: Dict, context: Dict, portfolio: List[Dict],
    slot_assignments: Optional[Dict[str, Dict]] = None,
    current_prices: Optional[Dict[str, float]] = None,
    signals: Optional[Dict] = None,
) -> str:
    """Build the user prompt with live market context.

    Args:
        decision: Tweet type decision dict
        context: Live market context
        portfolio: Portfolio data
        slot_assignments: Optional per-account slot data from _prepare_slot_data()
        current_prices: Optional dict of ticker→current price from yfinance
        signals: Optional signals dict (for funnel stats)
    """
    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    trending = context.get("fintwit_trending", [])

    movers_text = json.dumps(movers, indent=2) if movers else "No significant moves"
    themes_text = json.dumps(themes, indent=2) if themes else "All themes quiet"
    trending_text = ", ".join(trending) if trending else "Nothing specific"

    # Build per-account assignment instructions
    assignment_block = ""
    if slot_assignments:
        prd_names = {
            "variant_1": "Alex",
            "variant_2": "Rozalia",
            "variant_3": "James",
        }
        lines = []
        for variant, slot in slot_assignments.items():
            name = prd_names.get(variant, "Account")
            ticker = slot.get("ticker", "")
            cat = slot.get("category", decision.get("type", ""))
            angle = slot.get("angle", "general")
            ticker_str = f"${ticker}" if ticker else "best portfolio position"
            lines.append(f"  {variant} ({name}): Focus on {ticker_str} — {cat} — {angle} angle")

        assignment_block = f"""
PER-ACCOUNT ASSIGNMENTS (CRITICAL — each account gets a DIFFERENT focus):
{chr(10).join(lines)}
Each variant MUST focus on its assigned ticker. Do NOT give all 3 the same ticker unless assigned above.
"""

    generation_instruction = "Generate 3 variants now, each matching its assigned persona and ticker above." if slot_assignments else "Generate 3 variants now."

    decision_type = decision.get("type", "ENGAGEMENT")

    # Build enrichment blocks
    parts = []

    parts.append(f"""CURRENT MARKET STATE:
- SPY: {market.get('spy_move', 'N/A')} | QQQ: {market.get('qqq_move', 'N/A')} | VIX: {market.get('vix', 'N/A')}
- Mood: {market.get('market_mood', 'unknown')}
- Headline: {market.get('headline', '')}

YOUR PORTFOLIO MOVERS TODAY:
{movers_text}

THEME ACTIVITY:
{themes_text}

FINTWIT IS DISCUSSING:
{trending_text}

TWEET TYPE REQUESTED: {decision_type}
REASON: {decision.get('reason', '')}
FOCUS TICKER(S): {', '.join(f'${t}' for t in decision.get('tickers', []))}""")

    if assignment_block:
        parts.append(assignment_block)

    # Category-specific few-shot examples (Step 4)
    if decision_type in LIVE_CATEGORY_EXAMPLES:
        examples = LIVE_CATEGORY_EXAMPLES[decision_type]
        parts.append(f"\nREFERENCE EXAMPLES (match this style and data density):\n{examples}")

    # Funnel stats injection (Step 5a)
    if signals:
        stats = signals.get("stats", {})
        if stats and decision_type in ("SIGNAL_ALERT", "NEWSLETTER_CTA"):
            loaded = stats.get("tickers_loaded", 0)
            final = stats.get("final_trade", 0) + stats.get("final_consider", 0)
            if loaded > 0:
                parts.append(
                    f"\nFUNNEL STAT (powerful — use naturally): "
                    f"{loaded:,} stocks scanned → {final} survived all gates"
                )

    # Chart reference guidance (Step 5b)
    if decision_type in ("SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"):
        parts.append(
            "\nCHART: A chart will be attached. You can reference it naturally "
            "('Chart attached', 'Look at this setup') but don't force it."
        )

    # Time-of-day context (Step 5c)
    time_context = _get_time_context()
    if time_context:
        parts.append(f"\nTIME CONTEXT: {time_context}")

    # Catalyst/bullish factors for TECHNICAL_ANALYSIS (Step 5d)
    if decision.get("catalyst"):
        parts.append(f"\nCATALYST CONTEXT: {decision['catalyst']}")
    if decision.get("bullish_factors"):
        parts.append(f"BULLISH FACTORS: {', '.join(decision['bullish_factors'])}")

    # Multi-receipt format (Step 5e)
    if decision.get("multi_receipt"):
        parts.append(
            "\nMULTI-TICKER RECEIPT FORMAT — list ALL winners on separate lines:\n"
            "$TICKER1 +X% from $entry\n$TICKER2 +Y% from $entry\n"
            "Add a punchy opening hook and closing line. Let the numbers speak."
        )

    parts.append(f"""
PORTFOLIO CONTEXT (for accuracy — use ONLY these real numbers):
{format_portfolio_for_prompt(portfolio, current_prices=current_prices)}
{"Use CURRENT price for tweets, not HIGH price. HIGH is for context only." if current_prices else ""}

{generation_instruction}""")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# SONNET API CALL
# ═══════════════════════════════════════════════════════════════════════════════

def parse_json_response(text: str) -> Dict:
    """Parse JSON from Sonnet response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    return json.loads(cleaned)


def call_sonnet(
    decision: Dict, context: Dict, portfolio: List[Dict],
    style_guide: str, client: anthropic.Anthropic,
    slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    current_prices: Optional[Dict[str, float]] = None,
    signals: Optional[Dict] = None,
) -> List[Dict]:
    """Generate 3 tweet variants in a single Sonnet call."""
    system_prompt = build_system_prompt(style_guide, slot_assignments=slot_assignments, tracker=tracker)
    user_prompt = build_user_prompt(
        decision, context, portfolio,
        slot_assignments=slot_assignments,
        current_prices=current_prices,
        signals=signals,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text
    raw_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            raw_text += block.text

    # Parse JSON
    data = parse_json_response(raw_text)
    tweets = data.get("tweets", [])

    # Calculate cost
    usage = response.usage
    input_tokens = getattr(usage, 'input_tokens', 0) or 0
    output_tokens = getattr(usage, 'output_tokens', 0) or 0
    cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

    # Attach cost to each variant
    for t in tweets:
        t['_cost'] = cost / max(len(tweets), 1)

    return tweets


def repair_tweet(
    tweet_dict: Dict, failures: List[str], decision: Dict,
    context: Dict, portfolio: List[Dict],
    style_guide: str, client: anthropic.Anthropic,
) -> Optional[Dict]:
    """Attempt to repair a failed tweet by re-calling Sonnet with error feedback."""
    system_prompt = build_system_prompt(style_guide)
    failures_text = "\n".join(f"- {f}" for f in failures)

    user_prompt = f"""The following tweet FAILED validation:

"{tweet_dict.get('text', '')}"

Category: {tweet_dict.get('category', '')}
Failures:
{failures_text}

Rewrite this tweet to fix ALL the above issues.
Keep the same category ({tweet_dict.get('category', '')}) and general topic.
Use only tickers and prices from the portfolio data below.
Must be under 280 characters. Output ONLY the tweet text — no labels, no quotes, no JSON.

PORTFOLIO CONTEXT:
{format_portfolio_for_prompt(portfolio)}"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                text += block.text
        text = text.strip()

        # Strip wrapping quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        tickers = re.findall(r'\$([A-Z]{2,5})', text)
        primary = tickers[0] if tickers else tweet_dict.get('primary_ticker', '')

        return {
            "text": text,
            "category": tweet_dict.get("category", ""),
            "primary_ticker": primary,
            "chart_recommended": tweet_dict.get("chart_recommended", False),
            "account": tweet_dict.get("account", "variant_1"),
            "_repaired": True,
            "_cost": tweet_dict.get("_cost", 0),
        }
    except Exception as e:
        logger.error("Repair failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE (14 steps — PRD Section D29)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_tweet(
    tweet_dict: Dict,
    allowed_tickers: Set[str],
    all_variants: Optional[List[Dict]] = None,
    context: Optional[Dict] = None,
    recent_tweets: Optional[List[Dict]] = None,
    slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    portfolio: Optional[List[Dict]] = None,
) -> ValidationResult:
    """
    Run the 14-step validation pipeline on a tweet.

    Steps 1-10: Original pipeline
    Step 6b: Opening sentence diversity (NEW)
    Step 9b: Queue dedup — <80% similarity to any tweet in last 48h (NEW)
    Step 11: Meta-language detection (NEW)
    Step 12: Portfolio fabrication — verify claimed %gains match actual (NEW)
    Step 14: Winner framing — block defeatist language (NEW)

    Returns:
        ValidationResult with passed flag and failure list.
    """
    failures = []
    text = tweet_dict.get("text", "")
    category = tweet_dict.get("category", "")
    text_lower = text.lower()

    # Step 1: Category validation
    if category not in LIVE_VALID_CATEGORIES:
        failures.append(f"step1_category: '{category}' not in LIVE_VALID_CATEGORIES")

    # Step 2: Ticker fabrication check
    found_tickers = re.findall(r'\$([A-Z]{2,5})', text)
    if allowed_tickers:
        for ticker in found_tickers:
            if ticker not in allowed_tickers:
                failures.append(f"step2_fabrication: ${ticker} not in source data")

    # Step 3: Banned phrase check (word-boundary for short terms)
    for term in ALL_BANNED:
        term_lower = term.lower()
        if len(term) <= 4 and term.isascii():
            if re.search(r'\b' + re.escape(term_lower) + r'\b', text_lower):
                failures.append(f"step3_banned: '{term}'")
                break
        else:
            if term_lower in text_lower:
                failures.append(f"step3_banned: '{term}'")
                break

    # Step 4: Winners-only check
    negative_pcts = re.findall(r'(?<!\d)-\d+\.?\d*%', text)
    if negative_pcts:
        failures.append(f"step4_winners_only: negative percentage(s) {negative_pcts}")
    if check_loser_focus(text):
        failures.append("step4_winners_only: loser-focused language detected")

    # Step 5: Internal terminology check
    for pattern in INTERNAL_TERM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            failures.append(f"step5_internal: '{match.group()}' is internal terminology")
            break

    # Step 6: Character count
    if len(text) > MAX_TWEET_CHARS:
        failures.append(f"step6_chars: {len(text)} > {MAX_TWEET_CHARS}")

    # Step 6b: Opening sentence diversity (NEW — PRD D29)
    if tracker and tracker.opening_too_similar(text):
        failures.append("step6b_opening: opening too similar to recent tweet (>70% match)")

    # Step 7: Chart flag — recommend chart for any tweet with a specific ticker
    always_chart = {"SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"}
    chart_if_ticker = {"MARKET_REACTION", "DIP_OPPORTUNITY", "THEME_MOMENTUM",
                       "NEWSLETTER_CTA", "EDUCATIONAL", "WATCHLIST"}
    has_ticker = bool(tweet_dict.get("primary_ticker"))
    expected_chart = category in always_chart or (category in chart_if_ticker and has_ticker)
    if tweet_dict.get("chart_recommended") != expected_chart:
        tweet_dict["chart_recommended"] = expected_chart

    # Step 8: Cross-account dedup (if other variants provided) — PRD: <70% similarity
    if all_variants:
        for other in all_variants:
            if other.get("account") == tweet_dict.get("account"):
                continue
            similarity = SequenceMatcher(
                None, text_lower, other.get("text", "").lower()
            ).ratio()
            if similarity > 0.70:
                failures.append(
                    f"step8_dedup: {similarity:.0%} similar to {other.get('account', '?')}"
                )
                break

    # Step 8.5: Slot collision check (different tickers per account)
    if slot_assignments and all_variants:
        my_account = tweet_dict.get("account", "")
        my_ticker = (tweet_dict.get("primary_ticker") or "").lstrip('$')
        if my_ticker and my_account:
            assigned_tickers = {v: s.get("ticker", "") for v, s in slot_assignments.items()}
            unique_assigned = set(t for t in assigned_tickers.values() if t)
            shared_ticker_allowed = len(unique_assigned) < len(assigned_tickers)

            if not shared_ticker_allowed:
                for other in all_variants:
                    other_account = other.get("account", "")
                    if other_account == my_account:
                        continue
                    other_ticker = (other.get("primary_ticker") or "").lstrip('$')
                    if other_ticker and other_ticker == my_ticker:
                        failures.append(
                            f"step8_5_collision: ${my_ticker} used by both {my_account} and {other_account}"
                        )

    # Step 9: Context staleness check
    if context and category == "MARKET_REACTION":
        gathered_at = context.get("gathered_at", "")
        if gathered_at:
            try:
                gathered_time = datetime.fromisoformat(gathered_at)
                if gathered_time.tzinfo is None:
                    gathered_time = gathered_time.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - gathered_time).total_seconds() / 3600
                if age_hours > CONTEXT_STALENESS_HOURS:
                    failures.append(
                        f"step9_staleness: context {age_hours:.1f}h old, MARKET_REACTION blocked"
                    )
            except (ValueError, TypeError):
                pass
        if context.get("fallback_mode") or context.get("context_stale"):
            failures.append("step9_staleness: context is stale/fallback, MARKET_REACTION blocked")

    # Step 9b: Queue dedup — <80% similarity to any tweet in last 48h (NEW — PRD D28)
    if recent_tweets:
        dedup_cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=QUEUE_DEDUP_HOURS)
        for rt in recent_tweets:
            if rt.get("status") not in ("pending", "posted"):
                continue
            try:
                gen = datetime.fromisoformat(rt.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen < dedup_cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            similarity = SequenceMatcher(
                None, text_lower, rt.get("text", "").lower()
            ).ratio()
            if similarity > QUEUE_DEDUP_THRESHOLD:
                failures.append(
                    f"step9b_queue_dedup: {similarity:.0%} similar to recent tweet (id={rt.get('id', '?')})"
                )
                break

    # Step 10: Daily ticker repetition
    if recent_tweets and found_tickers:
        primary = found_tickers[0] if found_tickers else ""
        if primary:
            if tracker:
                ticker_count = tracker.tickers_today.get(primary, 0)
            else:
                ticker_count = count_ticker_today(primary, recent_tweets)
            if ticker_count >= MAX_SAME_TICKER_PER_DAY:
                failures.append(
                    f"step10_repetition: ${primary} already tweeted {ticker_count}x today (max {MAX_SAME_TICKER_PER_DAY})"
                )

    # Step 11: Meta-language detection (NEW — PRD D29)
    meta_patterns = [
        r'\[.*?\]',              # [placeholder] brackets
        r'TODO',                 # TODO markers
        r"I(?:'m| am) (?:an? )?(?:AI|bot|language model)",  # LLM self-reference
        r"(?:sorry|apologi[zs]e|I can't|I cannot)",         # LLM refusals
        r'INSERT|PLACEHOLDER',   # Template markers
    ]
    for pat in meta_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            failures.append(f"step11_meta: meta-language detected: '{match.group()}'")
            break

    # Step 12: Portfolio fabrication — verify claimed %gains match actual portfolio (NEW — PRD D29)
    if portfolio and found_tickers:
        pnl_claims = re.findall(r'\+(\d+\.?\d*)%', text)
        if pnl_claims:
            portfolio_lookup = {}
            for row in portfolio:
                entry = float(row.get('entry_price') or 0)
                highest = float(row.get('highest_close') or 0)
                if entry > 0 and highest > 0:
                    portfolio_lookup[row['ticker']] = ((highest - entry) / entry) * 100

            for claimed in pnl_claims:
                claimed_pct = float(claimed)
                # Check if any portfolio ticker has a P&L within 2% tolerance
                matched = False
                for ticker in found_tickers:
                    actual = portfolio_lookup.get(ticker, None)
                    if actual is not None and abs(actual - claimed_pct) <= 2.0:
                        matched = True
                        break
                if not matched and claimed_pct > 5.0:
                    # Only flag significant claims (>5%) that don't match
                    failures.append(
                        f"step12_fabrication: claimed +{claimed}% doesn't match any portfolio position"
                    )
                    break

    # Step 14: Winner framing — block defeatist language (NEW — PRD D29)
    defeatist_patterns = [
        r"rough (?:week|day|month)",
        r"portfolio (?:is )?down",
        r"bleeding",
        r"getting? (?:crushed|destroyed|wrecked|hammered)",
        r"bag ?hold",
        r"taking (?:a )?(?:loss|hit|beating)",
    ]
    for pat in defeatist_patterns:
        match = re.search(pat, text_lower)
        if match:
            failures.append(f"step14_framing: defeatist language: '{match.group()}'")
            break

    return ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE WRITING
# ═══════════════════════════════════════════════════════════════════════════════

def _prune_queue(queue: List[Dict], max_age_days: int = 7) -> List[Dict]:
    """Remove old posted/skipped/failed items. Keep all pending items.

    Prevents unbounded queue growth that causes git bloat and slow dedup.

    Args:
        queue: Full queue list
        max_age_days: Remove non-pending items older than this

    Returns:
        Pruned queue list
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    pruned = []
    removed = 0
    for item in queue:
        if item.get("status") == "pending":
            pruned.append(item)
            continue
        generated_at = item.get("generated_at", "")
        try:
            gen_time = datetime.fromisoformat(generated_at)
            if gen_time.tzinfo is None:
                gen_time = gen_time.replace(tzinfo=timezone.utc)
            if gen_time >= cutoff:
                pruned.append(item)
                continue
        except (ValueError, TypeError):
            pruned.append(item)  # Keep items with bad dates
            continue
        removed += 1
    if removed > 0:
        print(f"  🧹 Pruned {removed} items older than {max_age_days} days")
    return pruned


def write_to_live_queue(
    validated_tweets: List[Dict], decision: Dict, context: Dict, cost: float,
) -> Path:
    """Write validated tweets to the live content queue."""
    # Load existing queue and prune old items
    queue = load_json_list(LIVE_QUEUE_FILE)
    queue = _prune_queue(queue)

    now_utc = datetime.now(timezone.utc)
    now_et = datetime.now(ZoneInfo("America/New_York"))
    timestamp_str = now_et.strftime("%Y%m%d_%H%M%S")

    market = context.get("market_snapshot", {})

    for i, tweet in enumerate(validated_tweets):
        account = tweet.get("account", ACCOUNT_VARIANTS[i] if i < 3 else "variant_1")
        primary_ticker = tweet.get("primary_ticker", "")
        if not primary_ticker:
            tickers = re.findall(r'\$([A-Z]{2,5})', tweet.get("text", ""))
            primary_ticker = tickers[0] if tickers else ""

        entry = {
            "id": f"live_{timestamp_str}_v{i + 1}",
            "text": tweet["text"],
            "category": tweet.get("category", decision.get("type", "")),
            "primary_ticker": primary_ticker,
            "account": account,
            "chart_recommended": tweet.get("chart_recommended", False),
            "chart_path": None,
            "scheduled_time": now_et.isoformat(),
            "status": "pending",
            "context_snapshot": {
                "spy_at_generation": market.get("spy_move", "N/A"),
                "market_mood": market.get("market_mood", "unknown"),
                "context_stale": context.get("context_stale", False),
            },
            "generated_at": now_utc.isoformat(),
            "cost_usd": round(tweet.get("_cost", cost / max(len(validated_tweets), 1)), 6),
        }
        queue.append(entry)

    # Write atomically
    LIVE_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = LIVE_QUEUE_FILE.with_suffix(".tmp")
    with open(tmp_path, 'w') as f:
        json.dump(queue, f, indent=2)
    tmp_path.replace(LIVE_QUEUE_FILE)

    return LIVE_QUEUE_FILE


def log_failed_tweet(tweet_dict: Dict, failures: List[str]):
    """Log a failed tweet for debugging."""
    failed = load_json_list(FAILED_TWEETS_FILE)
    failed.append({
        "text": tweet_dict.get("text", ""),
        "category": tweet_dict.get("category", ""),
        "failures": failures,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last 100 entries
    failed = failed[-100:]
    with open(FAILED_TWEETS_FILE, 'w') as f:
        json.dump(failed, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_live_tweet(
    context_path: Optional[Path] = None,
    portfolio_path: Optional[Path] = None,
    signals_path: Optional[Path] = None,
    force_type: Optional[str] = None,
    dry_run: bool = False,
) -> Dict:
    """
    Main entry point. Decide, generate, validate, and queue live tweets.

    Returns:
        Status dict: {"status": "generated"|"skipped"|"failed", ...}
    """
    # 1. Load inputs
    context = load_json(context_path or LIVE_CONTEXT_FILE)
    portfolio = load_portfolio(portfolio_path)
    signals = load_json(signals_path or SIGNALS_FILE)
    style_guide = load_style_guide()
    recent_tweets = load_recent_tweets()
    allowed_tickers = build_allowed_tickers(portfolio, signals)

    # 1a. Fetch current prices for portfolio tickers (for prompt accuracy)
    current_prices: Dict[str, float] = {}
    if fetch_current_prices and portfolio:
        try:
            tickers = [r.get('ticker', '') for r in portfolio if r.get('ticker')]
            current_prices = fetch_current_prices(tickers) or {}
            logger.info("Fetched current prices for %d/%d tickers", len(current_prices), len(tickers))
        except Exception as e:
            logger.warning("Could not fetch current prices (non-fatal): %s", e)

    # 1b. Build diversity tracker from existing queue (cross-cron-run state)
    tracker = RecentTweetTracker(recent_tweets)
    logger.info(
        "Tracker: %d tweets today, %d tickers today, %d categories this week",
        tracker.tweets_today, len(tracker.tickers_today), len(tracker.categories_this_week),
    )

    if not context:
        logger.warning("No context data available")
        return {"status": "failed", "reason": "no_context"}

    # 2. Decide what to tweet (with category balance enforcement)
    if force_type:
        decision = {
            "action": "tweet",
            "type": force_type,
            "reason": f"Forced type: {force_type}",
            "tickers": get_diverse_tickers(portfolio, n=2, tracker=tracker),
            "urgency": "medium",
        }
    else:
        decision = decide_tweet_type(context, portfolio, signals, recent_tweets, tracker=tracker)

    # 3. If nothing worth tweeting, skip
    if decision["action"] == "skip":
        logger.info("Skipping: %s", decision["reason"])
        return {"status": "skipped", "reason": decision["reason"]}

    # 4. Check Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "failed", "reason": "ANTHROPIC_API_KEY not set"}
    client = anthropic.Anthropic(api_key=api_key)

    # 4b. Prepare per-account slot assignments (diversity-aware)
    slot_assignments = _prepare_slot_data(decision, portfolio, signals, tracker=tracker)
    logger.info("Slot assignments: %s", {v: s.get("ticker") for v, s in slot_assignments.items()})

    # 5. Generate tweets via Sonnet (with persona + slot data + opening/phrase dedup)
    try:
        raw_tweets = call_sonnet(
            decision, context, portfolio, style_guide, client,
            slot_assignments=slot_assignments, tracker=tracker,
            current_prices=current_prices, signals=signals,
        )
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Sonnet response: %s", e)
        return {"status": "failed", "reason": f"json_parse_error: {e}"}
    except anthropic.APIError as e:
        logger.error("Sonnet API error: %s", e)
        return {"status": "failed", "reason": f"api_error: {e}"}
    except Exception as e:
        logger.error("Unexpected error in Sonnet call: %s", e)
        return {"status": "failed", "reason": f"error: {e}"}

    if not raw_tweets:
        return {"status": "failed", "reason": "no_tweets_generated"}

    # 6. Validate all variants (14-step pipeline with tracker)
    validated = []
    total_cost = sum(t.get("_cost", 0) for t in raw_tweets)

    for tweet_dict in raw_tweets:
        result = validate_tweet(
            tweet_dict,
            allowed_tickers=allowed_tickers,
            all_variants=validated,
            context=context,
            recent_tweets=recent_tweets,
            slot_assignments=slot_assignments,
            tracker=tracker,
            portfolio=portfolio,
        )

        if result.passed:
            validated.append(tweet_dict)
            continue

        # Attempt repair
        for attempt in range(MAX_REPAIR_ATTEMPTS):
            logger.info(
                "Repairing %s tweet (attempt %d): %s",
                tweet_dict.get("account", "?"), attempt + 1, result.failures,
            )
            repaired = repair_tweet(
                tweet_dict, result.failures, decision,
                context, portfolio, style_guide, client,
            )
            if repaired is None:
                break

            result = validate_tweet(
                repaired,
                allowed_tickers=allowed_tickers,
                all_variants=validated,
                context=context,
                recent_tweets=recent_tweets,
                slot_assignments=slot_assignments,
                tracker=tracker,
                portfolio=portfolio,
            )
            if result.passed:
                validated.append(repaired)
                break
            tweet_dict = repaired  # Try repairing the repair
        else:
            # All repair attempts exhausted
            log_failed_tweet(tweet_dict, result.failures)
            logger.warning(
                "Dropped %s tweet after %d repair attempts: %s",
                tweet_dict.get("account", "?"), MAX_REPAIR_ATTEMPTS, result.failures,
            )

    # 7. Write to queue
    if not validated:
        logger.error("All variants failed validation")
        return {"status": "failed", "reason": "all_variants_failed"}

    if dry_run:
        return {
            "status": "dry_run",
            "count": len(validated),
            "tweets": validated,
            "decision": decision,
            "cost": total_cost,
        }

    queue_path = write_to_live_queue(validated, decision, context, total_cost)
    return {
        "status": "generated",
        "count": len(validated),
        "queue_path": str(queue_path),
        "decision_type": decision.get("type"),
        "cost": total_cost,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate live tweets via Claude Sonnet"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate but don't write to queue")
    parser.add_argument("--force-type", type=str, default=None,
                        help="Force tweet type (RECEIPT, MARKET_REACTION, etc.)")
    parser.add_argument("--context", type=str, default=None,
                        help="Custom context file path")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress banner output")
    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "=" * 60)
        print("  LIVE TWEET GENERATOR - Claude Sonnet")
        print("=" * 60)
        now_et = datetime.now(ZoneInfo("America/New_York"))
        print(f"\n  Time: {now_et.strftime('%Y-%m-%d %H:%M ET')}")
        print(f"  Market open: {is_market_open()}")
        if args.force_type:
            print(f"  Forced type: {args.force_type}")
        if args.dry_run:
            print("  Mode: DRY RUN")

    context_path = Path(args.context) if args.context else None

    result = generate_live_tweet(
        context_path=context_path,
        force_type=args.force_type,
        dry_run=args.dry_run,
    )

    if not args.quiet:
        status = result.get("status", "unknown")
        print(f"\n  Status: {status}")

        if status == "skipped":
            print(f"  Reason: {result.get('reason', '')}")

        elif status == "failed":
            print(f"  Reason: {result.get('reason', '')}")

        elif status in ("generated", "dry_run"):
            print(f"  Tweets: {result.get('count', 0)} variants")
            print(f"  Type: {result.get('decision_type', result.get('decision', {}).get('type', ''))}")
            print(f"  Cost: ${result.get('cost', 0):.4f}")

            if status == "dry_run" and result.get("tweets"):
                print("\n" + "-" * 60)
                for t in result["tweets"]:
                    print(f"\n  [{t.get('account', '?')}] {t.get('category', '?')}")
                    print(f"  {t.get('text', '')}")
                    print(f"  Ticker: {t.get('primary_ticker', 'N/A')} | "
                          f"Chart: {t.get('chart_recommended', False)}")
                print("\n" + "-" * 60)
                print("  (dry run — not queued)")

        if result.get("queue_path"):
            print(f"  Queue: {result['queue_path']}")

        print("\n" + "=" * 60 + "\n")

    return 0 if result.get("status") != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
