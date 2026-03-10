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

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

from twitter.models import (
    Tweet, ValidationResult, VALID_CATEGORIES,
    CHART_REQUIRED_CATEGORIES, EXTERNAL_TICKER_CATEGORIES,
    INTERNAL_TERM_PATTERNS,
)
from config.banned_terms import (
    ALL_BANNED, CRITICAL_BANNED, check_banned_phrases,
)
from twitter.live_context_gatherer import is_market_open, is_extended_hours

try:
    from portfolio.manager import fetch_current_prices
except ImportError:
    fetch_current_prices = None


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from config import (
        LIVE_QUEUE_FILE, PORTFOLIO_FILE, SIGNALS_FILE, COWORK_QUEUE_FILE,
        LIVE_CONTEXT_FILE, FAILED_TWEETS_FILE,
        MAX_TWEETS_PER_DAY, MAX_SAME_TICKER_PER_DAY,
        MIN_HOURS_BETWEEN_SAME_TICKER, CONTEXT_STALENESS_HOURS, WEEKEND_CONTEXT_STALENESS_HOURS,
        MODEL_LIVE_TWEET, WEEKEND_MAX_TWEETS, WEEKEND_CATEGORIES as _WEEKEND_CATS,
        PERSONAS, get_persona, PERSONA_AFFINITY,
    )
    MODEL = MODEL_LIVE_TWEET
    WEEKEND_CATEGORIES = set(_WEEKEND_CATS)  # Config stores List, local needs Set
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    _TWITTER_OUTPUT = BASE_DIR / "twitter" / "output"
    _SCANNER_OUTPUT = BASE_DIR / "scanner" / "output"
    _PORTFOLIO_OUTPUT = BASE_DIR / "portfolio" / "output"
    LIVE_QUEUE_FILE = _TWITTER_OUTPUT / "live_content_queue.json"
    COWORK_QUEUE_FILE = _TWITTER_OUTPUT / "cowork_content_queue.json"
    PORTFOLIO_FILE = _PORTFOLIO_OUTPUT / "portfolio.csv"
    SIGNALS_FILE = _SCANNER_OUTPUT / "signals.json"
    LIVE_CONTEXT_FILE = _TWITTER_OUTPUT / "live_context.json"
    FAILED_TWEETS_FILE = _TWITTER_OUTPUT / "failed_tweets.json"
    MODEL = "claude-sonnet-4-5-20250929"
    MAX_TWEETS_PER_DAY = 12
    WEEKEND_MAX_TWEETS = 4
    MAX_SAME_TICKER_PER_DAY = 3
    MIN_HOURS_BETWEEN_SAME_TICKER = 3
    CONTEXT_STALENESS_HOURS = 4
    WEEKEND_CONTEXT_STALENESS_HOURS = 24
    WEEKEND_CATEGORIES = {"EDUCATIONAL", "ENGAGEMENT", "RECEIPT", "SIGNAL_ALERT", "SUBSTACK_TEASER", "THEME_LIST"}
    PERSONA_AFFINITY = {
        "variant_1": {"primary": set(), "secondary": set(), "avoids": set()},
        "variant_2": {"primary": set(), "secondary": set(), "avoids": set()},
        "variant_3": {"primary": set(), "secondary": set(), "avoids": set()},
    }
STYLE_GUIDE_PATH = Path(__file__).resolve().parent / "docs" / "FINTWIT_STYLE_GUIDE.md"

MAX_TOKENS = 1500
MAX_TWEET_CHARS = 280
MAX_REPAIR_ATTEMPTS = 2

# Live system valid categories (matches VALID_CATEGORIES from models.py)
LIVE_VALID_CATEGORIES = {
    "SELL_SIGNAL", "SIGNAL_ALERT", "RECEIPT", "MARKET_COMMENTARY",
    "THEME_CATALYST", "THEME_LIST", "TRENDING_TAKE",
    "TECHNICAL_ANALYSIS", "EDUCATIONAL", "SUBSTACK_TEASER", "ENGAGEMENT",
}

# ── Category-specific few-shot examples for live tweet prompting ──────────────
# Injected into build_user_prompt(). Aligned with 11-category taxonomy.
LIVE_CATEGORY_EXAMPLES: Dict[str, str] = {
    "SIGNAL_ALERT": (
        '1) "Friday scan done. $INOD at $61.54 and $RCAT at $13.25 cleared all gates. '
        'Institutional Accumulation Divergence confirmed. Full breakdown in the newsletter."\n'
        '2) "1,800 stocks. 5 gates. 2 survivors this week. '
        "Quality over quantity — that's the whole point.\"\n"
        '3) "On my radar: $IONQ at $42.15. Theme alignment is there. '
        'Waiting for momentum confirmation. NFA."'
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
    "MARKET_COMMENTARY": (
        '1) "SPY down 1.5% but our names holding relative strength. '
        '$STRL green, $RCAT flat. Conviction showing."\n'
        '2) "Russell 2000 outperforming S&P for the 3rd straight week. '
        'Small caps leading is exactly what we want to see for our names."\n'
        '3) "VIX below 15. Low volatility, steady grind higher. '
        '$WCC quietly holding above entry. Boring is beautiful in this tape."\n'
        '4) "Defense spending bill advancing. $LMT $RTX catching bids. '
        'Our defense thesis getting catalysts. NFA."\n'
        '5) "Portfolio outperforming S&P by 2.9% this week. '
        'Small cap exposure paying off while big tech consolidates. The system works."'
    ),
    "THEME_CATALYST": (
        '1) "AI Infrastructure keeps leading. $NVDA, $SMCI, $AVGO — institutional '
        'accumulation across the board. Structural trend confirmed."\n'
        '2) "Nuclear renaissance just got a catalyst. DOE funding announced — '
        'our $OKLO position was ahead of this."'
    ),
    "THEME_LIST": (
        '1) "If you missed Gold and Silver...\\n\\nThe Copper bull run might be next:\\n\\n'
        '$TMQ at $6.21\\n$FCX at $60.41\\n$SCCO at $184.30\\n\\n'
        'Probably want to save this post!"\n'
        '2) "Defense theme is heating up:\\n\\n'
        '$RCAT at $13.25 (+55%)\\n$KTOS at $28.40\\n$PLTR at $45.10\\n\\n'
        'Institutional flows say this is just getting started."'
    ),
    "TRENDING_TAKE": (
        '1) "Everyone talking about $NVDA earnings but nobody mentioning the power '
        'infrastructure play behind it. Our thesis since Week 3."\n'
        '2) "FinTwit buzzing about AI stocks. Here\'s what the scanner actually says '
        'about the sector right now — and it\'s not what you\'d expect."'
    ),
    "TECHNICAL_ANALYSIS": (
        '1) "$WCC holding above $281 entry. Watching $320 resistance for breakout '
        'continuation. Invalidated below $256. NFA"\n'
        '2) "$STRL cleared $400 resistance — Structural Pivot confirmed. '
        'Invalidation on close below $362 entry. NFA!"'
    ),
    "EDUCATIONAL": (
        '1) "Position sizing 101: If a loss makes you emotional, you sized too big. '
        'Risk-defined entries, always."\n'
        "2) \"Why 5 gates? Because 'good stock' is subjective. "
        "Gates are binary. Removes emotion. That's the point.\""
    ),
    "SUBSTACK_TEASER": (
        '1) "$RCAT from $8.50 to $13.25 (+55.9%). How we found it before the move — '
        'full breakdown in the newsletter."\n'
        '2) "1,800 stocks scanned. 5 gates. 2 survivors. '
        'The full analysis drops every Saturday. Link in bio."'
    ),
    "ENGAGEMENT": (
        "1) \"What's your biggest trading lesson this year? "
        'Mine: stop arguing with the data."\n'
        '2) "Bad day? Happens to everyone. What matters is not letting '
        'a bad day become a bad week."'
    ),
}

# ── Market mood tone adjustment for system prompt ──────────────────────────
MOOD_INSTRUCTIONS = {
    "bullish": (
        "MARKET MOOD: BULLISH — Confident, forward-looking tone. "
        "Celebrate relative strength. 'Momentum confirmed,' 'thesis validating.' "
        "Optimistic but grounded in specific numbers."
    ),
    "bearish": (
        "MARKET MOOD: BEARISH — Defensive, honest tone. "
        "Lead with market context before position updates. Never fake optimism. "
        "'Watching,' 'holding,' 'invalidation at.' "
        "If positions green in red tape, highlight relative strength. "
        "If positions red, skip RECEIPT or frame as 'testing support.'"
    ),
    "volatile": (
        "MARKET MOOD: VOLATILE — Cautious, measured tone. "
        "Acknowledge the chop. 'Cash is a position' is valid. "
        "Don't pump holdings during chaos. Focus on levels and invalidation. "
        "Prefer EDUCATIONAL and MARKET_COMMENTARY over RECEIPT."
    ),
    "quiet": (
        "MARKET MOOD: QUIET — Reflective, process-focused tone. "
        "Good for EDUCATIONAL content about methodology. "
        "THEME_CATALYST and TRENDING_TAKE suit this tape."
    ),
    "unknown": (
        "MARKET MOOD: UNKNOWN — Stick to portfolio facts (entry prices, P&L). "
        "Avoid claiming market direction. EDUCATIONAL and ENGAGEMENT safest."
    ),
}


def load_category_examples() -> Optional[Dict[str, Dict]]:
    """Load category configs from config/tweet_prompts/*.yaml files.

    Returns dict mapping uppercase category name to full config:
        { "SIGNAL_ALERT": { "examples": [...], "persona_examples": {...}, "banned_terms": [...], "bad_examples": [] }, ... }

    Returns None on failure (missing dir, parse error) for graceful fallback.
    """
    prompts_dir = Path(__file__).resolve().parent.parent / "config" / "tweet_prompts"
    if not prompts_dir.is_dir():
        logging.warning("YAML category configs: %s not found, using hardcoded fallback", prompts_dir)
        return None

    configs = {}
    try:
        for yaml_file in sorted(prompts_dir.glob("*.yaml")):
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)
            if not data or "category" not in data:
                continue
            cat_name = data["category"].upper()
            configs[cat_name] = {
                "examples": data.get("examples", []),
                "persona_examples": data.get("persona_examples", {}),
                "banned_terms": data.get("banned_terms", []),
                "bad_examples": data.get("bad_examples", []),
            }
    except Exception as e:
        logging.warning("YAML category configs: parse error (%s), using hardcoded fallback", e)
        return None

    if configs:
        logging.info("Loaded YAML category configs for %d categories", len(configs))
    else:
        logging.warning("YAML category configs: no valid files found, using hardcoded fallback")
        return None

    return configs


_YAML_CATEGORY_CONFIGS = load_category_examples()


def load_voice_guides() -> Optional[Dict[str, Dict]]:
    """Load extended voice guides from config/persona_voice_guides.yaml.

    Returns dict mapping variant key to guide data:
        { "variant_1": { "name": "Alex", "role": "...", "voice_guide": "...", "rhythm_examples": [...], "never": [...] }, ... }

    Returns None on failure for graceful fallback to default persona descriptions.
    """
    vg_path = Path(__file__).resolve().parent.parent / "config" / "persona_voice_guides.yaml"
    if not vg_path.is_file():
        logging.warning("Voice guides: %s not found, using default persona descriptions", vg_path)
        return None

    try:
        with open(vg_path, "r") as f:
            data = yaml.safe_load(f)
        personas = data.get("personas", {})
        if not personas:
            logging.warning("Voice guides: no personas found in %s", vg_path)
            return None
        logging.info("Loaded voice guides for %d personas", len(personas))
        return personas
    except Exception as e:
        logging.warning("Voice guides: parse error (%s), using default persona descriptions", e)
        return None


_VOICE_GUIDES = load_voice_guides()


def load_engagement_data() -> Optional[Dict]:
    """Load engagement metrics from state/engagement.json.

    Returns dict with per-account, per-category engagement averages,
    or None if file missing/empty/unpopulated (scaffold).
    Used by decide_tweet_type() for engagement-weighted category selection.
    """
    eng_path = Path(__file__).resolve().parent.parent / "state" / "engagement.json"
    if not eng_path.is_file():
        logging.info("Engagement data: %s not found — no engagement weighting", eng_path)
        return None

    try:
        data = json.loads(eng_path.read_text())
        if not data or data.get("last_updated") is None:
            logging.info("Engagement data: scaffold only (last_updated=null) — no engagement weighting")
            return None
        logging.info("Engagement data loaded: last_updated=%s", data.get("last_updated"))
        return data
    except Exception as e:
        logging.warning("Engagement data: parse error (%s) — no engagement weighting", e)
        return None


_ENGAGEMENT_DATA = load_engagement_data()


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
        "RECEIPT": 5, "MARKET_COMMENTARY": 7, "SIGNAL_ALERT": 7,
        "TRENDING_TAKE": 5, "THEME_CATALYST": 5, "ENGAGEMENT": 5,
        "TECHNICAL_ANALYSIS": 5, "SUBSTACK_TEASER": 4, "THEME_LIST": 3,
        "EDUCATIONAL": 4, "SELL_SIGNAL": 3,
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
        self._recent_tweets = recent_tweets
        self.last_p2_category: Optional[str] = None
        self._last_p2_time = datetime.min.replace(tzinfo=ZoneInfo("UTC"))

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

            # Track most recent P2-level category for alternation
            if category in ("RECEIPT", "MARKET_COMMENTARY") and status in ("pending", "posted"):
                if gen_et > self._last_p2_time:
                    self.last_p2_category = category
                    self._last_p2_time = gen_et

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

    def category_over_weekly_budget(self, category: str, overrides: Optional[Dict[str, int]] = None) -> bool:
        targets = overrides if overrides else CATEGORY_WEEKLY_TARGETS
        target = targets.get(category, CATEGORY_WEEKLY_TARGETS.get(category, 999))
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

    def _parse_time(self, tweet: Dict) -> Optional[datetime]:
        """Parse generated_at from a tweet dict into ET-aware datetime."""
        try:
            gen = datetime.fromisoformat(tweet.get("generated_at", "2000-01-01"))
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=ZoneInfo("UTC"))
            return gen.astimezone(ZoneInfo("America/New_York"))
        except (ValueError, TypeError):
            return None

    def type_recently_used(self, tweet_type: str, hours: int = 4) -> bool:
        """Check if tweet type was used within N hours."""
        cutoff = self._now_et - timedelta(hours=hours)
        for t in self._recent_tweets:
            if t.get("status") not in ("pending", "posted", "failed"):
                continue
            if t.get("category") == tweet_type:
                gen_et = self._parse_time(t)
                if gen_et and gen_et > cutoff:
                    return True
        return False

    def theme_recently_used(self, theme: str, hours: int = 6) -> bool:
        """Check if theme was tweeted about within N hours."""
        cutoff = self._now_et - timedelta(hours=hours)
        theme_lower = theme.lower()
        for t in self._recent_tweets:
            if t.get("status") not in ("pending", "posted", "failed"):
                continue
            if theme_lower in t.get("text", "").lower():
                gen_et = self._parse_time(t)
                if gen_et and gen_et > cutoff:
                    return True
        return False

    def ticker_recently_tweeted(self, ticker: str, hours: int = 3) -> bool:
        """Check if ticker was tweeted about (any account) within N hours."""
        ticker = ticker.lstrip("$")
        cutoff = self._now_et - timedelta(hours=hours)
        for t in self._recent_tweets:
            if t.get("status") not in ("pending", "posted", "failed"):
                continue
            pt = (t.get("primary_ticker") or "").lstrip("$")
            if pt == ticker:
                gen_et = self._parse_time(t)
                if gen_et and gen_et > cutoff:
                    return True
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
    """Load recent tweets from live and cowork content queues for dedup."""
    live = load_json_list(LIVE_QUEUE_FILE)
    cowork = load_json_list(COWORK_QUEUE_FILE)
    return live + cowork


def load_style_guide() -> str:
    """Load style guide from file or use embedded fallback."""
    if STYLE_GUIDE_PATH.exists():
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    return (
        "Write tweets in confident, casual FinTwit voice. <=280 chars. "
        "Always include specific tickers and prices. NFA. "
        "Sound like a real trader, not a corporate account."
    )


def build_allowed_tickers(
    portfolio: List[Dict], signals: dict,
) -> Set[str]:
    """Build set of valid tickers from portfolio + signals (base set)."""
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


def build_context_tickers(context: Optional[Dict] = None) -> Set[str]:
    """Build set of tickers from context (theme_tickers from context gatherer).

    These are external tickers not in portfolio/signals — allowed only for
    EXTERNAL_TICKER_CATEGORIES (MARKET_COMMENTARY, THEME_LIST, TRENDING_TAKE).
    """
    tickers = set()
    if context:
        for theme_data in context.get("theme_tickers", []):
            for t in theme_data.get("tickers", []):
                sym = t.get("symbol", "").lstrip("$").upper()
                if sym:
                    tickers.add(sym)
    return tickers


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION LOGIC (PRD Section 14)
# ═══════════════════════════════════════════════════════════════════════════════

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


def _find_best_persona(category: str, affinity: Dict[str, Dict]) -> str:
    """Return the variant with strongest affinity for category.

    Priority: primary > secondary > first variant as tiebreaker.
    """
    for variant in ACCOUNT_VARIANTS:
        if category in affinity.get(variant, {}).get("primary", set()):
            return variant
    for variant in ACCOUNT_VARIANTS:
        if category in affinity.get(variant, {}).get("secondary", set()):
            return variant
    return ACCOUNT_VARIANTS[0]


def _pick_available_category(
    primary: set, secondary: set, avoids: set,
    tracker: Optional["RecentTweetTracker"] = None,
    exclude: Optional[set] = None,
    overrides: Optional[Dict[str, int]] = None,
) -> str:
    """Pick the best available category from persona's pools.

    Tries primary pool first, then secondary, skipping avoided
    categories and any in the exclude set. Falls back to any
    non-avoided valid category if pools are empty/exhausted.
    """
    exclude = exclude or set()

    # Try primary pool first
    for cat in sorted(primary):  # sorted for deterministic order
        if cat in exclude or cat in avoids:
            continue
        if _is_category_over_budget(cat, tracker, overrides=overrides):
            continue
        return cat

    # Then secondary
    for cat in sorted(secondary):
        if cat in exclude or cat in avoids:
            continue
        if _is_category_over_budget(cat, tracker, overrides=overrides):
            continue
        return cat

    # Fallback: any valid category not avoided or excluded
    for cat in sorted(LIVE_VALID_CATEGORIES):
        if cat in exclude or cat in avoids:
            continue
        if _is_category_over_budget(cat, tracker, overrides=overrides):
            continue
        return cat

    # Ultimate fallback
    return "ENGAGEMENT"


def _prepare_slot_data(
    decision: Dict, portfolio: List[Dict], signals: Dict,
    tracker: Optional["RecentTweetTracker"] = None,
) -> Dict[str, Dict]:
    """
    Prepare per-account slot assignments with persona affinity routing.

    The decision's category goes to the best-fit persona (via PERSONA_AFFINITY).
    Other personas get different categories from their own primary/secondary pools.
    Ticker selection uses diversity-aware rotation.

    Uses tracker to avoid:
    - Tickers already at daily limit
    - Same ticker on same account within MIN_HOURS_BETWEEN_SAME_TICKER
    - Same category consecutively on same account

    When no ticker available for a ticker-requiring category, falls back to
    a non-ticker category instead of reusing the same ticker.

    Returns:
        {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "EDUCATIONAL", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "MARKET_COMMENTARY", "angle": "punchy-direct"},
        }
    """
    decision_cat = decision.get("type", "ENGAGEMENT")

    # ── Step 1: Build ticker candidates (unchanged) ──────────────────────
    candidates = []

    # 1a. Decision tickers (highest priority) — filtered by tracker
    for t in decision.get("tickers", []):
        t = t.lstrip('$')
        if t and not (tracker and tracker.ticker_at_daily_limit(t)):
            candidates.append(t)

    # 1b. Portfolio winners via get_diverse_tickers (rotation-aware)
    diverse = get_diverse_tickers(
        portfolio, n=8, tracker=tracker,
        exclude=set(candidates),
    )
    for t in diverse:
        if t not in candidates:
            candidates.append(t)

    # 1c. Fresh scanner buy_signals
    for sig in signals.get('buy_signals', []):
        sym = sig.get('symbol', '').upper()
        if sym and sym not in candidates:
            if not (tracker and tracker.ticker_at_daily_limit(sym)):
                candidates.append(sym)

    # ── Step 2: Assign decision category to best-fit persona ─────────────
    best_persona = _find_best_persona(decision_cat, PERSONA_AFFINITY)

    # ── Step 3: Assign categories for all variants ───────────────────────
    assigned_categories: Dict[str, str] = {}
    assigned_categories[best_persona] = decision_cat

    for variant in ACCOUNT_VARIANTS:
        if variant == best_persona:
            continue
        affinity = PERSONA_AFFINITY.get(variant, {})
        alt_cat = _pick_available_category(
            primary=affinity.get("primary", set()),
            secondary=affinity.get("secondary", set()),
            avoids=affinity.get("avoids", set()),
            tracker=tracker,
            exclude=set(assigned_categories.values()),
        )
        assigned_categories[variant] = alt_cat

    # ── Step 4: Assign tickers per variant ───────────────────────────────
    angles = {
        "variant_1": "numbers-first, max 2-3 sentences, lead with $TICKER at $PRICE",
        "variant_2": "open with question or insight, 3-4 sentences, teaching voice",
        "variant_3": "short fragments with line breaks, max 4 lines, trader slang",
    }
    # Categories that need a specific ticker to be meaningful
    ticker_requiring_cats = {
        "RECEIPT", "SIGNAL_ALERT", "SELL_SIGNAL",
        "TECHNICAL_ANALYSIS", "THEME_CATALYST",
    }

    slot_data = {}
    used_tickers: Set[str] = set()

    for variant in ACCOUNT_VARIANTS:
        cat = assigned_categories[variant]

        # Find next unused ticker, also checking per-account recency
        ticker = ""
        for c in candidates:
            if c in used_tickers:
                continue
            if tracker and tracker.ticker_recent_for_account(
                c, variant, hours=MIN_HOURS_BETWEEN_SAME_TICKER
            ):
                continue
            ticker = c
            used_tickers.add(c)
            logger.debug("Slot dedup: $%s claimed for %s", c, variant)
            break

        # No-ticker fallback: switch to non-ticker category
        if not ticker and cat in ticker_requiring_cats:
            non_ticker_cats = ["EDUCATIONAL", "ENGAGEMENT"]
            cat = non_ticker_cats[ACCOUNT_VARIANTS.index(variant) % len(non_ticker_cats)]
            logger.info("Slot dedup: %s switched to %s (no available ticker)", variant, cat)

        # Same-category-consecutively check
        if tracker and tracker.last_category_per_account.get(variant) == cat:
            alt_cats = [c for c in sorted(LIVE_VALID_CATEGORIES)
                        if c != cat and not _is_category_over_budget(c, tracker, overrides=None)]
            if alt_cats:
                cat = alt_cats[ACCOUNT_VARIANTS.index(variant) % len(alt_cats)]

        slot_data[variant] = {
            "ticker": ticker,
            "category": cat,
            "angle": angles[variant],
        }

    return slot_data


def _is_category_over_budget(
    category: str,
    tracker: Optional["RecentTweetTracker"],
    overrides: Optional[Dict[str, int]] = None,
) -> bool:
    """Check if a category has exceeded its weekly target or daily limit.

    Args:
        overrides: Optional dict of {category: adjusted_target} that temporarily
                   replaces CATEGORY_WEEKLY_TARGETS for the weekly budget check.
                   Used by low-position mode to shift distribution.
    """
    if tracker is None:
        return False
    return tracker.category_over_weekly_budget(category, overrides=overrides) or tracker.category_at_daily_limit(category)


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


def _notable_market_condition(context: Dict) -> bool:
    """Check if market conditions warrant a MARKET_COMMENTARY tweet.

    Fires on positive AND negative conditions (key change from old system).
    """
    market = context.get("market_snapshot", {})
    mood = market.get("market_mood", "quiet")

    # Any non-quiet mood
    if mood in ("volatile", "bearish", "bullish", "mixed"):
        return True

    # SPY or QQQ move > ±1%
    for key in ("spy_move", "qqq_move"):
        move_str = str(market.get(key, "0")).replace("%", "").replace("+", "")
        try:
            if abs(float(move_str)) >= 1.0:
                return True
        except (ValueError, TypeError):
            pass

    # VIX extreme
    try:
        vix = float(str(market.get("vix", "17")).replace("%", ""))
        if vix > 20 or vix < 13:
            return True
    except (ValueError, TypeError):
        pass

    # High-impact news events
    for event in context.get("news_events", []):
        if event.get("impact") == "high" or event.get("relevance") == "high":
            return True

    return False


def fetch_yfinance_context(symbol: str) -> Optional[Dict]:
    """Fetch fresh market data for a single ticker via yfinance.

    Returns dict with price, change, volume info, or None on failure.
    Used to enrich fallback context when Grok is unavailable.
    """
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        info = tk.info
        if not info or "currentPrice" not in info:
            return None
        price = info.get("currentPrice", info.get("regularMarketPrice", 0))
        prev_close = info.get("previousClose", 0)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        avg_vol = info.get("averageVolume", 0)
        cur_vol = info.get("volume", 0)
        vol_ratio = round(cur_vol / avg_vol, 1) if avg_vol else 0
        return {
            "price": round(price, 2),
            "change_pct": round(change_pct, 1),
            "volume_ratio": vol_ratio,
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector", ""),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        logger.debug("yfinance fetch failed for %s: %s", symbol, e)
        return None


def _build_fallback_context(portfolio: List[Dict], signals: Dict) -> Dict:
    """Build minimal context from portfolio + signals when Grok context is unavailable.

    This ensures the decision cascade can still produce SIGNAL_ALERT, RECEIPT,
    EDUCATIONAL, SUBSTACK_TEASER, TECHNICAL_ANALYSIS, and ENGAGEMENT tweets
    even without live market data from Grok.

    Returns empty dict if no usable data is available.
    """
    if not portfolio and not signals:
        return {}

    # Build portfolio_movers from open positions
    movers = []
    for pos in (portfolio or []):
        if pos.get("status") != "OPEN":
            continue
        ticker = pos.get("ticker", "")
        if not ticker:
            continue
        pnl = pos.get("pnl_pct", pos.get("return_pct", ""))
        movers.append({
            "ticker": f"${ticker}",
            "move": f"{pnl}%" if pnl else "N/A",
            "price": str(pos.get("current_price", pos.get("entry_price", "?"))),
            "context": pos.get("theme", "portfolio position"),
        })

    # Enrich movers with fresh yfinance data where portfolio data is stale
    for mover in movers:
        raw_ticker = mover["ticker"].replace("$", "")
        if mover.get("move") in ("N/A", "", None) or mover.get("price") in ("?", "", None):
            yf_data = fetch_yfinance_context(raw_ticker)
            if yf_data:
                mover["price"] = str(yf_data["price"])
                mover["move"] = f"{yf_data['change_pct']:+.1f}%"
                if yf_data.get("sector"):
                    mover["context"] = f"{mover.get('context', '')} ({yf_data['sector']})"
                logger.info("yfinance enriched fallback for %s: $%s %s", raw_ticker, yf_data["price"], mover["move"])

    # Build theme_activity from signals themes
    theme_activity = []
    for theme in (signals or {}).get("themes", []):
        name = theme.get("name", "")
        if name:
            theme_activity.append({
                "theme": name,
                "status": theme.get("classification", "active"),
                "detail": theme.get("thesis_summary", ""),
            })

    if not movers and not theme_activity:
        return {}

    logger.info(
        "Built fallback context: %d movers, %d themes",
        len(movers), len(theme_activity),
    )
    return {
        "market_snapshot": {"market_mood": "unknown", "spy_move": "N/A"},
        "portfolio_movers": movers[:5],
        "theme_activity": theme_activity[:5],
        "theme_tickers": [],
        "fintwit_theme_overlaps": [],
        "news_events": [],
        "fallback_mode": True,
    }


def _fintwit_overlaps_themes(context: Dict) -> Optional[Dict]:
    """Check if FinTwit trending topics overlap with tracked themes.

    Returns first overlap found, or None.
    """
    overlaps = context.get("fintwit_theme_overlaps", [])
    if overlaps:
        return overlaps[0]
    return None


def _theme_has_external_tickers(context: Dict, min_count: int = 5) -> Optional[Dict]:
    """Check if any active theme has enough external tickers for a THEME_LIST."""
    for td in context.get("theme_tickers", []):
        if len(td.get("tickers", [])) >= min_count:
            return td
    return None


def _is_post_day() -> bool:
    """Check if today is a Substack post day."""
    day = datetime.now(ZoneInfo("America/New_York")).strftime("%A")
    return day in ("Tuesday", "Wednesday", "Thursday", "Saturday")


def _get_today_post_topic() -> Optional[str]:
    """Read today's post topic from daily_context.md."""
    try:
        from config.output_paths import DAILY_CONTEXT_FILE
        context_path = DAILY_CONTEXT_FILE
    except ImportError:
        context_path = Path("substack/output/current/daily_context.md")

    if not context_path.exists():
        return None
    try:
        content = context_path.read_text(encoding="utf-8")
        match = re.search(r"\*\*Topic:\*\*\s*(.+)", content)
        return match.group(1).strip() if match else None
    except (OSError, UnicodeDecodeError):
        return None


def _get_category_engagement_score(category: str) -> float:
    """Get aggregate engagement score for a category across all accounts.

    Score = avg_likes + avg_retweets * 2 + avg_replies * 3
    (replies weighted highest as they indicate true engagement)

    Returns 0.0 if no data available.
    """
    if not _ENGAGEMENT_DATA:
        return 0.0
    total = 0.0
    count = 0
    for variant, acct_data in _ENGAGEMENT_DATA.get("accounts", {}).items():
        cat_data = acct_data.get("by_category", {}).get(category, {})
        if cat_data and cat_data.get("count", 0) > 0:
            total += (
                cat_data.get("avg_likes", 0)
                + cat_data.get("avg_retweets", 0) * 2
                + cat_data.get("avg_replies", 0) * 3
            )
            count += 1
    return round(total / count, 1) if count > 0 else 0.0


def decide_tweet_type(
    context: Dict, portfolio: List[Dict], signals: Dict, recent_tweets: List[Dict],
    tracker: Optional["RecentTweetTracker"] = None,
) -> Dict:
    """
    Decide what type of tweet to post based on current market conditions.

    7-priority cascade (Phase 4): P0 SELL_SIGNAL → P1 SIGNAL_ALERT →
    P2 RECEIPT / MARKET_COMMENTARY → P3 THEME_CATALYST / TRENDING_TAKE →
    P4 THEME_LIST / SUBSTACK_TEASER → P5 TECHNICAL_ANALYSIS / EDUCATIONAL →
    P6 ENGAGEMENT → SKIP.

    Budget-gated at every level — if over budget, falls through to next.
    No filler, no cadence fallbacks. SKIP when all budgets exhausted.

    Returns: {"action": "tweet"|"skip", "type": str, "reason": str, "tickers": list, "urgency": str}
    """
    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    now_et = datetime.now(ZoneInfo("America/New_York"))
    is_weekend = now_et.weekday() >= 5

    # Check daily tweet count
    tweets_today = tracker.tweets_today if tracker else 0
    max_today = WEEKEND_MAX_TWEETS if is_weekend else MAX_TWEETS_PER_DAY
    if tweets_today >= max_today:
        return {"action": "skip", "reason": f"Daily cap reached ({tweets_today}/{max_today})"}

    # Low-position mode: shift category preferences when portfolio is thin
    portfolio_count = len([p for p in portfolio if float(p.get('entry_price', 0) or 0) > 0])
    is_low_position = portfolio_count < 5

    # Budget overrides for low-position mode: suppress ticker-heavy categories,
    # boost theme/educational content that doesn't depend on open positions.
    low_pos_overrides = None
    if is_low_position:
        low_pos_overrides = {
            "RECEIPT": 3,            # down from 5 — fewer positions to showcase
            "TECHNICAL_ANALYSIS": 2, # down from 5 — fewer charts to discuss
            "THEME_LIST": 5,         # up from 3 — themes don't need positions
            "EDUCATIONAL": 6,        # up from 4 — principles over tickers
        }

    # ── P0: Sell/exit signals (ALWAYS highest priority) ────────────────────
    if not _is_category_over_budget("SELL_SIGNAL", tracker, overrides=low_pos_overrides):
        for sig in signals.get("sell_signals", []):
            ticker = sig.get("symbol", "").upper()
            if not ticker:
                continue
            if tracker and tracker.ticker_recently_tweeted(ticker, hours=12):
                continue
            if tracker and tracker.ticker_at_daily_limit(ticker):
                continue
            return {
                "action": "tweet",
                "type": "SELL_SIGNAL",
                "reason": f"Exit signal: ${ticker} — {sig.get('reason', '')}",
                "tickers": [ticker],
                "urgency": "high",
            }

    # ── P1: Fresh scanner signals (buy + consider) ─────────────────────────
    if not _is_category_over_budget("SIGNAL_ALERT", tracker, overrides=low_pos_overrides):
        # P1a: Fresh buy signals (< 72h old)
        signal_timestamp = signals.get("timestamp", "")
        hours_since_scan = 999
        if signal_timestamp:
            try:
                signal_time = datetime.strptime(signal_timestamp, "%Y-%m-%d %H:%M:%S")
                signal_time = signal_time.replace(tzinfo=ZoneInfo("America/New_York"))
                hours_since_scan = (now_et - signal_time).total_seconds() / 3600
            except (ValueError, TypeError):
                pass

        if hours_since_scan < 72:
            for sig in signals.get("buy_signals", []):
                ticker = sig.get("symbol", "").upper()
                if not ticker:
                    continue
                if tracker and tracker.ticker_recently_tweeted(ticker, hours=6):
                    continue
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

        # P1b: CONSIDER signals (watching sub-type, 12h cooldown)
        for sig in signals.get("consider_signals", []):
            ticker = sig.get("symbol", "").upper()
            if not ticker:
                continue
            if tracker and tracker.ticker_recently_tweeted(ticker, hours=12):
                continue
            if tracker and tracker.ticker_at_daily_limit(ticker):
                continue
            return {
                "action": "tweet",
                "type": "SIGNAL_ALERT",
                "sub_type": "watching",
                "reason": f"Consider signal: ${ticker}",
                "tickers": [ticker],
                "urgency": "low",
            }

    # ── P2: RECEIPT alternating with MARKET_COMMENTARY ─────────────────────
    last_p2 = tracker.last_p2_category if tracker else None

    # Determine try order: alternate away from last used
    # Low-position mode: always prefer MARKET_COMMENTARY to avoid ticker repetition
    if is_low_position:
        p2_order = ["MARKET_COMMENTARY", "RECEIPT"]
    elif last_p2 == "RECEIPT":
        p2_order = ["MARKET_COMMENTARY", "RECEIPT"]
    elif last_p2 == "MARKET_COMMENTARY":
        p2_order = ["RECEIPT", "MARKET_COMMENTARY"]
    else:
        # No P2 history — try RECEIPT first (concrete > abstract)
        p2_order = ["RECEIPT", "MARKET_COMMENTARY"]

    # Engagement-weighted reorder (soft bias — 70/30 when data available)
    if _ENGAGEMENT_DATA:
        score_r = _get_category_engagement_score("RECEIPT")
        score_mc = _get_category_engagement_score("MARKET_COMMENTARY")
        if score_r > 0 and score_mc > 0:
            higher = "RECEIPT" if score_r >= score_mc else "MARKET_COMMENTARY"
            lower = "MARKET_COMMENTARY" if higher == "RECEIPT" else "RECEIPT"
            if random.random() < 0.7:
                p2_order = [higher, lower]
            else:
                p2_order = [lower, higher]
            logger.debug(
                "P2 engagement weighting: RECEIPT=%.1f, MARKET_COMMENTARY=%.1f → trying %s first",
                score_r, score_mc, p2_order[0],
            )

    for p2_type in p2_order:
        if _is_category_over_budget(p2_type, tracker, overrides=low_pos_overrides):
            continue

        if p2_type == "RECEIPT":
            # Single mover receipt (>=2% move)
            for mover in movers:
                try:
                    move_str = str(mover.get("move", "0")).replace("%", "").replace("+", "")
                    pct = float(move_str)
                except (ValueError, TypeError):
                    continue
                if pct < 3.0:
                    continue
                ticker = mover.get("ticker", "").lstrip("$")
                if not ticker:
                    continue
                if tracker and tracker.ticker_recently_tweeted(ticker, hours=MIN_HOURS_BETWEEN_SAME_TICKER):
                    continue
                if tracker and tracker.ticker_at_daily_limit(ticker):
                    continue
                return {
                    "action": "tweet",
                    "type": "RECEIPT",
                    "reason": f"${ticker} moving {mover.get('move', '?')}: {mover.get('context', '')}",
                    "tickers": [ticker],
                    "urgency": "high",
                }

            # Multi-receipt: 3+ winners > 5%, no RECEIPT in 24h
            winners = [
                r for r in portfolio
                if float(r.get("entry_price", 0) or 0) > 0
                and float(r.get("highest_close", 0) or 0)
                > float(r.get("entry_price", 0) or 1) * 1.05
            ]
            if len(winners) >= 3:
                recently_had_receipt = (
                    tracker.type_recently_used("RECEIPT", hours=24) if tracker else False
                )
                if not recently_had_receipt:
                    top_tickers = [
                        w["ticker"]
                        for w in sorted(
                            winners,
                            key=lambda x: float(x.get("highest_close", 0) or 0)
                            / max(float(x.get("entry_price", 0) or 1), 0.01),
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
                        "thread": True,
                    }

        elif p2_type == "MARKET_COMMENTARY":
            if not _notable_market_condition(context):
                continue
            if tracker and tracker.type_recently_used("MARKET_COMMENTARY", hours=4):
                continue
            mood = market.get("market_mood", "quiet")
            headline = market.get("headline", "")
            mover_tickers = [
                m.get("ticker", "").lstrip("$") for m in movers[:2] if m.get("ticker")
            ]
            return {
                "action": "tweet",
                "type": "MARKET_COMMENTARY",
                "reason": f"Market mood: {mood} — {headline}",
                "tickers": mover_tickers,
                "urgency": "medium",
            }

    # ── P3: THEME_CATALYST or TRENDING_TAKE ────────────────────────────────
    # TODO Sprint 7: engagement-weighted reorder when both P3a/P3b are eligible
    # P3a: Breaking themes → THEME_CATALYST
    if not _is_category_over_budget("THEME_CATALYST", tracker, overrides=low_pos_overrides):
        active_themes = [t for t in themes if t.get("status") == "breaking"]
        for theme in active_themes:
            theme_name = theme.get("theme", "")
            if not theme_name:
                continue
            if tracker and tracker.theme_recently_used(theme_name, hours=6):
                continue
            return {
                "action": "tweet",
                "type": "THEME_CATALYST",
                "reason": f"{theme_name} breaking: {theme.get('detail', '')}",
                "tickers": find_tickers_for_theme(theme_name, portfolio, signals),
                "urgency": "high",
            }

    # P3b: FinTwit overlap → TRENDING_TAKE
    if not _is_category_over_budget("TRENDING_TAKE", tracker, overrides=low_pos_overrides):
        overlap = _fintwit_overlaps_themes(context)
        if overlap:
            overlap_theme = overlap.get("theme", "")
            if not (tracker and tracker.theme_recently_used(overlap_theme, hours=6)):
                overlap_tickers = [
                    t.get("symbol", "").lstrip("$")
                    for t in overlap.get("tickers", [])
                    if t.get("symbol")
                ][:3]
                if not overlap_tickers:
                    overlap_tickers = find_tickers_for_theme(
                        overlap_theme, portfolio, signals
                    )
                return {
                    "action": "tweet",
                    "type": "TRENDING_TAKE",
                    "reason": f"FinTwit overlap: {overlap_theme} — {overlap.get('detail', '')}",
                    "tickers": overlap_tickers,
                    "urgency": "medium",
                }

    # ── P4: THEME_LIST or SUBSTACK_TEASER ──────────────────────────────────
    # TODO Sprint 7: engagement-weighted reorder when both P4a/P4b are eligible
    # P4a: Theme with external tickers → THEME_LIST (min 3 in low-position, 5 otherwise)
    if not _is_category_over_budget("THEME_LIST", tracker, overrides=low_pos_overrides):
        theme_min = 3 if is_low_position else 5
        theme_data = _theme_has_external_tickers(context, min_count=theme_min)
        if theme_data:
            theme_name = theme_data.get("theme", "")
            if not (tracker and tracker.theme_recently_used(theme_name, hours=6)):
                ext_tickers = [
                    t.get("symbol", "").lstrip("$")
                    for t in theme_data.get("tickers", [])
                    if t.get("symbol")
                ][:5]
                return {
                    "action": "tweet",
                    "type": "THEME_LIST",
                    "reason": f"Theme list: {theme_name} — {len(theme_data.get('tickers', []))} names in play",
                    "tickers": ext_tickers,
                    "urgency": "low",
                    "thread": True,
                }

    # P4b: Substack teaser on post days
    if not _is_category_over_budget("SUBSTACK_TEASER", tracker, overrides=low_pos_overrides):
        if _is_post_day():
            topic = _get_today_post_topic()
            reason = f"Substack teaser — today's post: {topic}" if topic else "Scheduled Substack teaser"
            return {
                "action": "tweet",
                "type": "SUBSTACK_TEASER",
                "reason": reason,
                "tickers": get_diverse_tickers(portfolio, n=1, tracker=tracker),
                "urgency": "low",
                "post_topic": topic,
            }

    # ── P5: TECHNICAL_ANALYSIS or EDUCATIONAL ──────────────────────────────
    # TODO Sprint 7: engagement-weighted reorder when both P5a/P5b are eligible
    # P5a: Low-position mode redirect — prefer EDUCATIONAL over TA to diversify
    if is_low_position and not is_weekend:
        if not _is_category_over_budget("EDUCATIONAL", tracker, overrides=low_pos_overrides):
            if not (tracker and tracker.type_recently_used("EDUCATIONAL", hours=4)):
                edu_tickers = get_diverse_tickers(portfolio, n=1, tracker=tracker) or []
                return {
                    "action": "tweet",
                    "type": "EDUCATIONAL",
                    "reason": "Educational content (low-position mode — diversifying from TA)",
                    "tickers": edu_tickers,
                    "urgency": "low",
                }

    # P5b: Position commentary
    if not is_weekend and not _is_category_over_budget("TECHNICAL_ANALYSIS", tracker, overrides=low_pos_overrides):
        if not (tracker and tracker.type_recently_used("TECHNICAL_ANALYSIS", hours=4)):
            commentary_tickers = get_diverse_tickers(portfolio, n=1, tracker=tracker)
            if commentary_tickers:
                ticker = commentary_tickers[0]
                sig_data = next(
                    (
                        s
                        for s in signals.get("buy_signals", [])
                        if s.get("symbol", "").upper() == ticker
                    ),
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

    # P5c: Educational content (every 3rd becomes a thread)
    if not _is_category_over_budget("EDUCATIONAL", tracker, overrides=low_pos_overrides):
        if not (tracker and tracker.type_recently_used("EDUCATIONAL", hours=6)):
            edu_count = tracker.categories_this_week.get("EDUCATIONAL", 0) if tracker else 0
            is_edu_thread = edu_count > 0 and (edu_count % 3 == 0)
            return {
                "action": "tweet",
                "type": "EDUCATIONAL",
                "reason": "Educational content — methodology / trading lessons",
                "tickers": get_diverse_tickers(portfolio, n=1, tracker=tracker) or [],
                "urgency": "low",
                "thread": is_edu_thread,
            }

    # ── P6: ENGAGEMENT ─────────────────────────────────────────────────────
    if not _is_category_over_budget("ENGAGEMENT", tracker, overrides=low_pos_overrides):
        if not (tracker and tracker.type_recently_used("ENGAGEMENT", hours=6)):
            return {
                "action": "tweet",
                "type": "ENGAGEMENT",
                "reason": "Community engagement content",
                "tickers": get_diverse_tickers(portfolio, n=1, tracker=tracker) or [],
                "urgency": "low",
            }

    # ── SKIP: All budgets exhausted ────────────────────────────────────────
    return {"action": "skip", "reason": "All category budgets exhausted"}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS (PRD Section 6.3-6.4)
# ═══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(
    style_guide: str, slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    is_thread: bool = False,
    market_mood: str = "unknown",
) -> str:
    """Build the Sonnet system prompt for tweet generation.

    Args:
        style_guide: FinTwit style guide text
        slot_assignments: Optional per-account slot data from _prepare_slot_data()
        tracker: Optional RecentTweetTracker for opening/phrase dedup injection
        is_thread: Whether this is a thread generation
        market_mood: Current market mood for tone adjustment (bullish/bearish/volatile/quiet/unknown)
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

    # Extended voice guides (from persona_voice_guides.yaml)
    voice_guide_block = ""
    if _VOICE_GUIDES and slot_assignments:
        vg_lines = []
        for variant in slot_assignments:
            guide = _VOICE_GUIDES.get(variant)
            if guide:
                vg_text = guide.get("voice_guide", "").strip()
                rhythm = guide.get("rhythm_examples", [])
                never = guide.get("never", [])
                pname = guide.get("name", variant)
                section = f"{variant} ({pname}) VOICE GUIDE:\n{vg_text}"
                if rhythm:
                    section += "\nRhythm examples (match this cadence):\n" + "\n".join(f"  - {ex}" for ex in rhythm)
                if never:
                    section += "\nNEVER:\n" + "\n".join(f"  - {item}" for item in never)
                vg_lines.append(section)
        if vg_lines:
            voice_guide_block = "\n\nEXTENDED VOICE GUIDES:\n" + "\n\n".join(vg_lines) + "\n"

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

    # Market mood tone adjustment
    mood_block = f"\n{MOOD_INSTRUCTIONS.get(market_mood, MOOD_INSTRUCTIONS['unknown'])}\n"

    # Structural persona differentiation (enforced, not suggested)
    structural_block = """
STRUCTURAL DIFFERENTIATION (CRITICAL — enforced per variant):

variant_1 (Alex — The System):
- MUST open with a number (price, percentage, count, or ratio)
- Maximum 3 sentences. No exceptions.
- No exclamation marks. No questions. Statements only.
- Never address the reader directly.
- Rhythm: short — short — medium.

variant_2 (Rozalia — The Mentor):
- MUST connect the ticker/event to a broader theme or structural shift
- Use "we" at least once. Community voice.
- Include WHY the number matters, not just the number.
- Flowing sentences that build specific to structural.
- Can be the longest of the three variants.

variant_3 (James — The Trader):
- MUST be the shortest variant. Max 4 lines, each under 60 characters.
- Uses line breaks between thoughts. Short fragments, not full sentences.
- Casual language: fragments OK, contractions required, drops articles.
- NEVER explains WHY. States WHAT and WHAT NEXT.
- Can address reader directly. Gets NFA allocation when used.

CROSS-VARIANT RULES:
- Each variant MUST use a different opening word/phrase. Check: if the first 3 words are similar, rewrite.
- Each variant MUST have a different sentence count (e.g., 2, 3, 1 — not 2, 2, 2).
- If all 3 variants mention the same ticker, at least one must frame it from a DIFFERENT angle (market context vs thesis vs price action).
- Never use the same adjective in two variants.
"""

    return f"""You are generating tweets for Sterling Signals, a momentum trading system on FinTwit that screens 1,800+ stocks through 5 gates and publishes entry/exit prices transparently.

STYLE RULES (non-negotiable):
{style_guide}
{persona_block}{voice_guide_block}{structural_block}{opening_block}{phrase_block}
YOUR TASK:
Generate exactly 3 tweet variants for the same moment. Each variant must:
- Sound like a different human wrote it (not just rearranged words)
- Be <=280 characters
- Contain at least one specific element (ticker, price, %, or named theme)
- Match the tone of these reference accounts: confident but not arrogant, specific not vague, casual not corporate

FORMATTING RULES:
- Return ONLY valid JSON — no markdown, no commentary
- Format: {{"tweets": [{{"text": "...", "category": "...", "primary_ticker": "...", "chart_recommended": true/false, "account": "variant_1|variant_2|variant_3"}}, ...]}}
- Categories: SELL_SIGNAL, SIGNAL_ALERT, RECEIPT, MARKET_COMMENTARY, THEME_CATALYST, THEME_LIST, TRENDING_TAKE, TECHNICAL_ANALYSIS, EDUCATIONAL, SUBSTACK_TEASER, ENGAGEMENT
- chart_recommended: true ONLY when tweet references specific price action on a single ticker
{"- For THREAD format: Use thread_tweets array with is_thread: true. Each tweet in thread must be <=280 chars independently. Hook first, data second, CTA third." if is_thread else ""}
ABSOLUTE BANS (NEVER use these terms):
{banned_sample}

ADDITIONAL RULES:
- Never fabricate tickers, prices, or percentages not in the provided data
- Never use: "our scanner", "filtered X stocks"
- "Save this post" / "bookmark this" — use SPARINGLY as a CTA, NOT in every tweet
- Never use hashtags
- Never exceed 280 characters
- Never mention losses or negative P&L (except SELL_SIGNAL: frame as "setup invalidated")
- Never use UK references (BST, GMT, GBP, ISA)
- Never reference being an AI, bot, or automated system
- NFA in maximum 1 of 3 variants (assign to James unless specified otherwise)
- Never use: "exciting," "amazing," "incredible," "our proprietary system," "our algorithm"
- Never open with: "In the world of," "When it comes to," "Let's dive into," "Let's explore"
- Never use: "landscape," "navigate," "journey," "unpack" (as metaphor)
- SELL_SIGNAL tweets: Frame as "setup invalidated" or "win more than you lose". Never show loss amounts.
- TECHNICAL_ANALYSIS tweets: Comment on position with price levels, catalysts, or tailwinds. Include invalidation level.
- SIGNAL_ALERT (watching sub-type): Frame as "on my radar" or "watching closely". Waiting for confirmation.
{mood_block}
Output ONLY the JSON."""


def _build_thread_prompt_section(decision: Dict) -> str:
    """Build thread-specific prompt instructions when decision has thread=True.

    Returns thread format block for THEME_LIST or multi-RECEIPT threads.
    Returns empty string for non-thread decisions.
    """
    if not decision.get("thread"):
        return ""

    decision_type = decision.get("type", "")

    if decision_type == "THEME_LIST":
        return (
            '\nTHREAD FORMAT (CRITICAL — this is a 2-3 tweet THREAD, not a single tweet):\n'
            'Generate a thread with 2-3 tweets. Each tweet MUST be <=280 characters independently.\n\n'
            'Thread structure for THEME_LIST:\n'
            '- Tweet 1 (hook): Opening line about the theme — compelling, no tickers needed\n'
            '- Tweet 2 (data): Ticker list with current prices, one per line ($TICKER at $XX.XX)\n'
            '- Tweet 3 (connection): Portfolio position in this theme + CTA (save this, link in bio)\n\n'
            'Output format — use "thread_tweets" array with "is_thread": true:\n'
            '{\n'
            '  "tweets": [\n'
            '    {\n'
            '      "thread_tweets": [\n'
            '        {"text": "Hook tweet (1/3)", "number": 1},\n'
            '        {"text": "$TICK1 at $XX\\n$TICK2 at $YY\\n$TICK3 at $ZZ (2/3)", "number": 2},\n'
            '        {"text": "Portfolio connection + CTA (3/3)", "number": 3}\n'
            '      ],\n'
            '      "category": "THEME_LIST",\n'
            '      "primary_ticker": "TICK1",\n'
            '      "chart_recommended": false,\n'
            '      "account": "variant_X",\n'
            '      "is_thread": true\n'
            '    }\n'
            '  ]\n'
            '}'
        )

    elif decision_type == "RECEIPT" and decision.get("multi_receipt"):
        return (
            '\nTHREAD FORMAT (CRITICAL — this is a 2-3 tweet THREAD, not a single tweet):\n'
            'Generate a thread with 2-3 tweets. Each tweet MUST be <=280 characters independently.\n\n'
            'Thread structure for multi-RECEIPT:\n'
            '- Tweet 1 (hook): Opening hook about portfolio performance — punchy, attention-grabbing\n'
            '- Tweet 2 (data): Winner list with entry prices and % gains, one per line ($TICKER +XX% from $entry)\n'
            '- Tweet 3 (close): Closing tagline — system credibility, methodology, or CTA\n\n'
            'Output format — use "thread_tweets" array with "is_thread": true:\n'
            '{\n'
            '  "tweets": [\n'
            '    {\n'
            '      "thread_tweets": [\n'
            '        {"text": "Hook about winning (1/3)", "number": 1},\n'
            '        {"text": "$AAA +50% from $10\\n$BBB +30% from $20\\n$CCC +25% from $5 (2/3)", "number": 2},\n'
            '        {"text": "System credibility + CTA (3/3)", "number": 3}\n'
            '      ],\n'
            '      "category": "RECEIPT",\n'
            '      "primary_ticker": "AAA",\n'
            '      "chart_recommended": false,\n'
            '      "account": "variant_X",\n'
            '      "is_thread": true\n'
            '    }\n'
            '  ]\n'
            '}'
        )

    elif decision_type == "EDUCATIONAL":
        return (
            '\nTHREAD FORMAT (CRITICAL — this is a 2-3 tweet THREAD, not a single tweet):\n'
            'Generate a thread with 2-3 tweets. Each tweet MUST be <=280 characters independently.\n\n'
            'Thread structure for EDUCATIONAL:\n'
            '- Tweet 1 (hook): A specific stat or question from our system — grounded in real data\n'
            '- Tweet 2 (explanation): How the system handles this, with real numbers from this week\n'
            '- Tweet 3 (takeaway): The principle applied + what we actually did\n\n'
            'Output format — use "thread_tweets" array with "is_thread": true:\n'
            '{\n'
            '  "tweets": [\n'
            '    {\n'
            '      "thread_tweets": [\n'
            '        {"text": "Hook with specific system stat (1/3)", "number": 1},\n'
            '        {"text": "How the system handles it with real numbers (2/3)", "number": 2},\n'
            '        {"text": "Principle + what we did this week (3/3)", "number": 3}\n'
            '      ],\n'
            '      "category": "EDUCATIONAL",\n'
            '      "primary_ticker": "...",\n'
            '      "chart_recommended": false,\n'
            '      "account": "variant_X",\n'
            '      "is_thread": true\n'
            '    }\n'
            '  ]\n'
            '}'
        )

    return ""


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

    # Category-specific few-shot examples (Step 4) — YAML-first, hardcoded fallback
    _examples_added = False
    if _YAML_CATEGORY_CONFIGS and decision_type in _YAML_CATEGORY_CONFIGS:
        yaml_cfg = _YAML_CATEGORY_CONFIGS[decision_type]
        examples_list = yaml_cfg.get("examples", [])
        if examples_list:
            numbered = "\n".join(f'{i+1}) "{ex}"' for i, ex in enumerate(examples_list))
            parts.append(f"\nREFERENCE EXAMPLES (match this style and data density):\n{numbered}")
            _examples_added = True
        # Persona-specific examples (if slot_assignments present)
        if slot_assignments:
            persona_ex = yaml_cfg.get("persona_examples", {})
            for variant_key in slot_assignments:
                variant_examples = persona_ex.get(variant_key, [])
                if variant_examples:
                    pname = {"variant_1": "Alex", "variant_2": "Rozalia", "variant_3": "James"}.get(variant_key, variant_key)
                    ex_text = "\n".join(f'  - "{ex}"' for ex in variant_examples)
                    parts.append(f"\n{pname}-specific examples:\n{ex_text}")
        # Bad examples — what NOT to do (from YAML)
        bad_ex = yaml_cfg.get("bad_examples", [])
        if bad_ex:
            bad_text = "\n".join(f'  - BAD: "{ex}"' for ex in bad_ex[:3])
            parts.append(f"\nAVOID THESE PATTERNS (bad tweets for this category — do NOT write like this):\n{bad_text}")
    if not _examples_added and decision_type in LIVE_CATEGORY_EXAMPLES:
        examples = LIVE_CATEGORY_EXAMPLES[decision_type]
        parts.append(f"\nREFERENCE EXAMPLES (match this style and data density):\n{examples}")

    # Funnel stats injection (Step 5a)
    if signals:
        stats = signals.get("stats", {})
        if stats and decision_type in ("SIGNAL_ALERT", "SUBSTACK_TEASER"):
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

    # Multi-receipt format (Step 5e — only for non-thread single tweets)
    if decision.get("multi_receipt") and not decision.get("thread"):
        parts.append(
            "\nMULTI-TICKER RECEIPT FORMAT — list ALL winners on separate lines:\n"
            "$TICKER1 +X% from $entry\n$TICKER2 +Y% from $entry\n"
            "Add a punchy opening hook and closing line. Let the numbers speak."
        )

    # Thread format instructions (Phase 5 — Task 5.2)
    thread_section = _build_thread_prompt_section(decision)
    if thread_section:
        parts.append(thread_section)

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


def _parse_thread_output(raw_tweets: List[Dict]) -> List[Dict]:
    """Process raw Sonnet output, handling thread items gracefully.

    Thread items have is_thread=True and thread_tweets array.
    Invalid threads (wrong length, over-length sub-tweets) are flattened
    to single tweets using tweet 1 text — they degrade gracefully rather
    than failing.

    For valid threads, sets the top-level ``text`` field to tweet 1's text
    so downstream flat-validation compatibility is maintained.
    """
    processed = []
    for item in raw_tweets:
        if not item.get("is_thread") or not item.get("thread_tweets"):
            processed.append(item)
            continue

        thread_tweets = item.get("thread_tweets", [])

        # Thread-level: must be 2-3 tweets
        if len(thread_tweets) < 2 or len(thread_tweets) > 3:
            logger.warning(
                "Thread has %d tweets (expected 2-3), flattening to single tweet",
                len(thread_tweets),
            )
            item["text"] = thread_tweets[0].get("text", "") if thread_tweets else ""
            item["is_thread"] = False
            item.pop("thread_tweets", None)
            processed.append(item)
            continue

        # Validate each sub-tweet length
        all_valid = True
        for sub in thread_tweets:
            if len(sub.get("text", "")) > MAX_TWEET_CHARS:
                logger.warning(
                    "Thread sub-tweet %d exceeds %d chars (%d), flattening",
                    sub.get("number", 0), MAX_TWEET_CHARS, len(sub.get("text", "")),
                )
                all_valid = False

        if not all_valid:
            item["text"] = thread_tweets[0].get("text", "")
            item["is_thread"] = False
            item.pop("thread_tweets", None)
            processed.append(item)
            continue

        # Valid thread — set text to tweet 1 for flat validation compat
        item["text"] = thread_tweets[0].get("text", "")
        processed.append(item)

    return processed


def call_sonnet(
    decision: Dict, context: Dict, portfolio: List[Dict],
    style_guide: str, client: anthropic.Anthropic,
    slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    current_prices: Optional[Dict[str, float]] = None,
    signals: Optional[Dict] = None,
) -> List[Dict]:
    """Generate 3 tweet variants in a single Sonnet call."""
    is_thread = decision.get("thread", False)
    market_mood = context.get("market_snapshot", {}).get("market_mood", "unknown")
    system_prompt = build_system_prompt(
        style_guide, slot_assignments=slot_assignments,
        tracker=tracker, is_thread=is_thread,
        market_mood=market_mood,
    )
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

    # Process thread outputs — validate structure, flatten invalid threads
    tweets = _parse_thread_output(tweets)

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


def _safe_parse_date(ts: str):
    """Parse ISO timestamp to date, return None on failure."""
    try:
        return datetime.fromisoformat(ts).date()
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE (14 steps — PRD Section D29)
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_thread_integrity(tweet_dict: Dict) -> List[str]:
    """Step 6c: Thread structure validation.

    Checks:
    - Thread has 2-3 tweets (reject <2 or >3)
    - Each tweet ≤280 chars and ≥10 chars
    - Tweet 1 must not start with a ticker (hooks should be thematic)
    - At least one tweet must contain a $TICKER reference
    """
    failures: List[str] = []
    thread_tweets = tweet_dict.get("thread_tweets", [])
    count = len(thread_tweets)

    if count < 2 or count > 3:
        failures.append(f"step6c_thread: {count} tweets (must be 2-3)")
        return failures  # Can't validate further without valid structure

    for idx, sub in enumerate(thread_tweets, start=1):
        text = sub.get("text", "")
        if len(text) > 280:
            failures.append(f"step6c_thread: tweet {idx} is {len(text)} chars (max 280)")
        if len(text) < 10:
            failures.append(f"step6c_thread: tweet {idx} is {len(text)} chars (min 10)")

    # Tweet 1 should not start with $TICKER (hooks should be thematic)
    first_text = thread_tweets[0].get("text", "").lstrip()
    if first_text.startswith("$"):
        failures.append("step6c_thread: tweet 1 starts with ticker (hook should be thematic)")

    # At least one tweet must contain a $TICKER
    has_ticker = any(
        re.search(r'\$[A-Z]{2,5}', sub.get("text", ""))
        for sub in thread_tweets
    )
    if not has_ticker:
        failures.append("step6c_thread: no $TICKER in any thread tweet")

    return failures


def validate_thread(
    tweet_dict: Dict,
    allowed_tickers: Set[str],
    all_variants: Optional[List[Dict]] = None,
    context: Optional[Dict] = None,
    recent_tweets: Optional[List[Dict]] = None,
    slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    portfolio: Optional[List[Dict]] = None,
    context_tickers: Optional[Set[str]] = None,
) -> ValidationResult:
    """Validate a tweet, with thread-aware handling for thread items.

    For thread items (is_thread=True + thread_tweets array):
        - Step 6c thread integrity check (structure, lengths, hooks)
        - Runs 14-step validate_tweet() on each sub-tweet individually
        - Thread-level checks: tweets 2-3 must contain tickers or data
        - Prefixes failures with ``thread_tweet_N:`` for debugging

    For non-thread items: delegates directly to validate_tweet().
    """
    if not tweet_dict.get("is_thread") or not tweet_dict.get("thread_tweets"):
        return validate_tweet(
            tweet_dict, allowed_tickers, all_variants, context,
            recent_tweets, slot_assignments, tracker, portfolio,
            context_tickers=context_tickers,
        )

    # --- Thread validation ---
    thread_tweets = tweet_dict.get("thread_tweets", [])
    all_failures: List[str] = []

    # Step 6c: Thread integrity (structural check before per-tweet validation)
    all_failures.extend(_validate_thread_integrity(tweet_dict))

    for idx, sub_tweet in enumerate(thread_tweets, start=1):
        # Build a pseudo tweet_dict for each sub-tweet so validate_tweet works
        sub_dict = {
            **tweet_dict,
            "text": sub_tweet.get("text", ""),
            # Strip thread fields so validate_tweet treats it as flat
            "is_thread": False,
        }
        sub_dict.pop("thread_tweets", None)

        sub_result = validate_tweet(
            sub_dict, allowed_tickers,
            all_variants=all_variants,
            context=context,
            recent_tweets=recent_tweets,
            slot_assignments=slot_assignments,
            tracker=tracker,
            portfolio=portfolio,
            context_tickers=context_tickers,
        )
        for f in sub_result.failures:
            all_failures.append(f"thread_tweet_{idx}: {f}")

    # Thread-level check: tweets 2+ should contain tickers or data (prices/percentages)
    data_pattern = re.compile(r'(\$[A-Z]{2,5}|\d+\.?\d*%|\$\d+)')
    for idx, sub_tweet in enumerate(thread_tweets[1:], start=2):
        text = sub_tweet.get("text", "")
        if not data_pattern.search(text):
            all_failures.append(
                f"thread_tweet_{idx}: thread_data_check: no tickers or data found in continuation tweet"
            )

    return ValidationResult(
        passed=len(all_failures) == 0,
        failures=all_failures,
    )


def validate_tweet(
    tweet_dict: Dict,
    allowed_tickers: Set[str],
    all_variants: Optional[List[Dict]] = None,
    context: Optional[Dict] = None,
    recent_tweets: Optional[List[Dict]] = None,
    slot_assignments: Optional[Dict[str, Dict]] = None,
    tracker: Optional["RecentTweetTracker"] = None,
    portfolio: Optional[List[Dict]] = None,
    context_tickers: Optional[Set[str]] = None,
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
    if allowed_tickers or context_tickers:
        # External categories (MARKET_COMMENTARY, THEME_LIST, TRENDING_TAKE) may use context tickers
        if category in EXTERNAL_TICKER_CATEGORIES and context_tickers:
            full_allowed = allowed_tickers | context_tickers
        else:
            full_allowed = allowed_tickers
        for ticker in found_tickers:
            if ticker not in full_allowed:
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

    # Step 3b: Category-specific YAML banned terms
    if _YAML_CATEGORY_CONFIGS and category in _YAML_CATEGORY_CONFIGS:
        yaml_banned = _YAML_CATEGORY_CONFIGS[category].get("banned_terms", [])
        for term in yaml_banned:
            if term.lower() in text_lower:
                failures.append(f"step3b_yaml_banned: '{term}' (category-specific)")
                break

    # Step 4: Winners-only check
    negative_pcts = re.findall(r'(?<!\d)-\d+\.?\d*%', text)
    if negative_pcts:
        failures.append(f"step4_winners_only: negative percentage(s) {negative_pcts}")

    # Step 5: Internal terminology check
    for pattern in INTERNAL_TERM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            failures.append(f"step5_internal: '{match.group()}' is internal terminology")
            break

    # Step 6: Character count
    if len(text) > MAX_TWEET_CHARS:
        failures.append(f"step6_chars: {len(text)} > {MAX_TWEET_CHARS}")

    # Step 6c: Thread integrity (belt-and-suspenders for direct callers)
    if tweet_dict.get("is_thread") and tweet_dict.get("thread_tweets"):
        failures.extend(_validate_thread_integrity(tweet_dict))

    # Step 6b: Opening sentence diversity (NEW — PRD D29)
    if tracker and tracker.opening_too_similar(text):
        failures.append("step6b_opening: opening too similar to recent tweet (>70% match)")

    # Step 7: Chart flag — recommend chart based on category definitions
    always_chart = CHART_REQUIRED_CATEGORIES  # {"SELL_SIGNAL", "SIGNAL_ALERT", "RECEIPT"}
    chart_if_ticker = LIVE_VALID_CATEGORIES - CHART_REQUIRED_CATEGORIES
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
                my_category = tweet_dict.get("category", "")
                for other in all_variants:
                    other_account = other.get("account", "")
                    if other_account == my_account:
                        continue
                    other_ticker = (other.get("primary_ticker") or "").lstrip('$')
                    other_category = other.get("category", "")
                    # Same ticker + same category = collision; different category = OK (persona affinity)
                    if other_ticker and other_ticker == my_ticker and other_category == my_category:
                        failures.append(
                            f"step8_5_collision: ${my_ticker} + {my_category} on both {my_account} and {other_account}"
                        )

    # Step 8.6: Cross-account ticker assignment enforcement
    # Catches LLM ignoring slot assignment and using another account's ticker
    if slot_assignments:
        my_account_86 = tweet_dict.get("account", "")
        my_ticker_86 = (tweet_dict.get("primary_ticker") or "").lstrip('$')
        my_assigned = (slot_assignments.get(my_account_86, {}).get("ticker", "") or "").lstrip('$')
        if my_ticker_86 and my_account_86 and my_assigned:
            if my_ticker_86 != my_assigned:
                # Check if this ticker was assigned to another account
                claimed_by = None
                for variant, slot in slot_assignments.items():
                    if variant != my_account_86 and (slot.get("ticker", "") or "").lstrip('$') == my_ticker_86:
                        claimed_by = variant
                        break
                if claimed_by:
                    failures.append(
                        f"step8_6_cross_dedup: ${my_ticker_86} assigned to {claimed_by}, "
                        f"not {my_account_86} (assigned ${my_assigned})"
                    )
                    logger.info("Step 8.6: $%s used by %s but assigned to %s", my_ticker_86, my_account_86, claimed_by)
                else:
                    logger.debug("Step 8.6: $%s not in any assignment — allowing (unassigned ticker)", my_ticker_86)
            else:
                logger.debug("Step 8.6: $%s correctly matches assignment for %s", my_ticker_86, my_account_86)

    # Step 9: Context staleness check (relaxed on weekends — markets closed)
    if context and category in {"MARKET_COMMENTARY", "TRENDING_TAKE"}:
        gathered_at = context.get("gathered_at", "")
        if gathered_at:
            try:
                gathered_time = datetime.fromisoformat(gathered_at)
                if gathered_time.tzinfo is None:
                    gathered_time = gathered_time.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - gathered_time).total_seconds() / 3600
                now_et = datetime.now(ZoneInfo("America/New_York"))
                staleness_limit = WEEKEND_CONTEXT_STALENESS_HOURS if now_et.weekday() >= 5 else CONTEXT_STALENESS_HOURS
                if age_hours > staleness_limit:
                    failures.append(
                        f"step9_staleness: context {age_hours:.1f}h old (limit {staleness_limit}h), {category} blocked"
                    )
            except (ValueError, TypeError):
                pass
        if context.get("fallback_mode") or context.get("context_stale"):
            failures.append(f"step9_staleness: context is stale/fallback, {category} blocked")

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
                # Inline fallback (standalone count_ticker_today deleted in Phase 4)
                today = datetime.now(ZoneInfo("America/New_York")).date()
                ticker_count = sum(
                    1 for t in (recent_tweets or [])
                    if t.get("status") in ("pending", "posted")
                    and (t.get("primary_ticker") or "").lstrip("$") == primary
                    and _safe_parse_date(t.get("generated_at", "")) == today
                )
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

        is_thread = tweet.get("is_thread", False) and bool(tweet.get("thread_tweets"))

        entry = {
            "id": f"live_{timestamp_str}_v{i + 1}{'_thread' if is_thread else ''}",
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

        # Thread fields — matches poster.py post_thread() expected schema
        if is_thread:
            entry["is_thread"] = True
            entry["thread_tweets"] = tweet["thread_tweets"]

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

def _has_pending_cowork_items(account: str) -> bool:
    """Check if Cowork already provided pending tweets for this account today.

    Checks the dedicated cowork queue file first, then falls back to the
    live queue for already-merged items.
    """
    from config.output_paths import COWORK_QUEUE_FILE

    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

    def _check_queue(queue_data, require_not_merged=False):
        if not queue_data or not isinstance(queue_data, list):
            return False
        return any(
            item.get("source") == "cowork"
            and item.get("status") == "pending"
            and item.get("account") == account
            and item.get("generated_at", "").startswith(today)
            and (not require_not_merged or not item.get("merged"))
            for item in queue_data
        )

    try:
        # Check dedicated cowork queue first (un-merged items)
        if COWORK_QUEUE_FILE.exists():
            cowork_queue = load_json(COWORK_QUEUE_FILE)
            if _check_queue(cowork_queue, require_not_merged=True):
                return True
        # Fallback: check live queue for already-merged cowork items
        live_queue = load_json(LIVE_QUEUE_FILE)
        return _check_queue(live_queue)
    except Exception:
        return False


def _count_pending_cowork_accounts() -> List[str]:
    """Return list of accounts that have pending Cowork tweets today."""
    accounts_with_cowork = []
    for account in ACCOUNT_VARIANTS:
        if _has_pending_cowork_items(account):
            accounts_with_cowork.append(account)
    return accounts_with_cowork


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
    # 0. Check if Cowork already provided content for all accounts today
    cowork_accounts = _count_pending_cowork_accounts()
    if cowork_accounts and not force_type:
        if len(cowork_accounts) == len(ACCOUNT_VARIANTS):
            logger.info(
                "Cowork content available for all accounts — skipping generation"
            )
            return {
                "status": "skipped",
                "reason": f"cowork_content_pending ({', '.join(cowork_accounts)})",
            }
        else:
            logger.info(
                "Cowork content available for %s — generation will proceed for remaining accounts",
                ", ".join(cowork_accounts),
            )

    # 1. Load inputs
    context = load_json(context_path or LIVE_CONTEXT_FILE)
    portfolio = load_portfolio(portfolio_path)
    signals = load_json(signals_path or SIGNALS_FILE)
    style_guide = load_style_guide()
    recent_tweets = load_recent_tweets()
    allowed_tickers = build_allowed_tickers(portfolio, signals)
    context_tickers = build_context_tickers(context)

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
        logger.warning("No Grok context — building fallback from portfolio + signals")
        context = _build_fallback_context(portfolio, signals)
        if not context:
            # Last resort: try yfinance directly for portfolio tickers
            if portfolio:
                tickers = [r.get("ticker", "") for r in portfolio if r.get("status") == "OPEN" and r.get("ticker")][:3]
                yf_movers = []
                for t in tickers:
                    yf_data = fetch_yfinance_context(t)
                    if yf_data:
                        yf_movers.append({
                            "ticker": f"${t}",
                            "move": f"{yf_data['change_pct']:+.1f}%",
                            "price": str(yf_data["price"]),
                            "context": yf_data.get("sector", "portfolio position"),
                        })
                if yf_movers:
                    logger.info("Built yfinance-only context for %d tickers", len(yf_movers))
                    context = {
                        "market_snapshot": {"market_mood": "unknown", "spy_move": "N/A"},
                        "portfolio_movers": yf_movers,
                        "theme_activity": [],
                        "theme_tickers": [],
                        "fintwit_theme_overlaps": [],
                        "news_events": [],
                        "fallback_mode": True,
                    }
            if not context:
                logger.warning("All context sources exhausted — no data available")
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

    # Engagement observation logging
    selected_category = decision.get("type", "")
    if selected_category:
        eng_score = _get_category_engagement_score(selected_category)
        if _ENGAGEMENT_DATA:
            logger.info(
                "Category selected: %s (engagement score: %.1f)",
                selected_category, eng_score,
            )
        else:
            logger.info("Category selected: %s (no engagement data yet)", selected_category)

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
        is_thread_item = tweet_dict.get("is_thread", False)

        result = validate_thread(
            tweet_dict,
            allowed_tickers=allowed_tickers,
            all_variants=validated,
            context=context,
            recent_tweets=recent_tweets,
            slot_assignments=slot_assignments,
            tracker=tracker,
            portfolio=portfolio,
            context_tickers=context_tickers,
        )

        if result.passed:
            validated.append(tweet_dict)
            continue

        # Skip repair loop for thread items (thread repair is complex; log as failed)
        if is_thread_item:
            log_failed_tweet(tweet_dict, result.failures)
            logger.warning(
                "Dropped %s thread (no repair for threads): %s",
                tweet_dict.get("account", "?"), result.failures,
            )
            continue

        # Attempt repair (flat tweets only)
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

            result = validate_thread(
                repaired,
                allowed_tickers=allowed_tickers,
                all_variants=validated,
                context=context,
                recent_tweets=recent_tweets,
                slot_assignments=slot_assignments,
                tracker=tracker,
                portfolio=portfolio,
                context_tickers=context_tickers,
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
                        help="Force tweet type (RECEIPT, MARKET_COMMENTARY, etc.)")
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
