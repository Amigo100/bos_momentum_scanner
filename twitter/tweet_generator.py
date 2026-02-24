#!/usr/bin/env python3
"""
Sterling Signals — Tweet Generator v2.0
========================================

Unified voice, style-guide compliant, data-driven content generation.

Replaces: reaction_generator.py (3-persona system)
Ref: STERLING_SIGNALS_PRD_v2.md section 3
Ref: FINTWIT_STYLE_GUIDE.md

Usage:
    from twitter.tweet_generator import generate_weekly_content, generate_daily_content

    summary = generate_weekly_content("scanner/output/signals.json", "portfolio/output/portfolio.csv")
    daily  = generate_daily_content("scanner/output/daily_signals.json", "portfolio/output/daily_portfolio.csv")

CLI:
    python -m twitter.tweet_generator --signals scanner/output/signals.json --portfolio portfolio/output/portfolio.csv
    python -m twitter.tweet_generator --daily --signals scanner/output/daily_signals.json
"""

import argparse
import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

from config.settings import (
    BASE_DIR,
    MODEL_TWEET,
    MAX_TOKENS,
    SLOT_TIMES_ET,
    COST_INPUT_PER_M,
    COST_OUTPUT_PER_M,
    MARKETING_THRESHOLDS,
    NEWSLETTER_URL,
)
from config import (
    TWITTER_OUTPUT,
    CHARTS_DIR,
    SIGNALS_FILE,
    PORTFOLIO_FILE,
    FAILED_TWEETS_FILE,
)
from config.banned_terms import (
    ALL_BANNED,
    CRITICAL_BANNED,
    check_banned_phrases,
)
from twitter.models import (
    Tweet,
    ValidationResult,
    SlotAssignment,
    ContentData,
    TWEET_CATEGORIES,
    CHART_REQUIRED_CATEGORIES,
    VALID_CATEGORIES,
    INTERNAL_TERM_PATTERNS,
)


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL = MODEL_TWEET
TWEET_MAX_TOKENS = MAX_TOKENS.get(MODEL, 4096)
MAX_TWEET_CHARS = 280
MAX_REPAIR_ATTEMPTS = 2
NOTABLE_WIN_THRESHOLD = 10.0  # Positions >= 10% get PERFORMANCE tweets

STYLE_GUIDE_PATH = BASE_DIR / "FINTWIT_STYLE_GUIDE.md"

# Days starting Saturday (day after weekly scan) through Friday
WEEKLY_DAYS = ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]

# Account queue files — identical content written to all three
ACCOUNT_QUEUES = {
    "main": "content_queue.json",
    "account2": "content_queue_account2.json",
    "account3": "content_queue_account3.json",
}

DAILY_ACCOUNT_QUEUES = {
    "main": "daily_content_queue.json",
    "account2": "daily_content_queue_account2.json",
    "account3": "daily_content_queue_account3.json",
}

# Weekly slots (1-5) per day
WEEKLY_SLOTS = [2, 3, 4, 5]

# Categories where every $TICKER must come from source data (not flexible)
DATA_DEPENDENT_CATEGORIES = {
    "SCANNER_RESULT", "SELL_SIGNAL", "DAILY_SIGNAL",
    "PERFORMANCE", "TECHNICAL_ANALYSIS", "WATCHLIST",
}

# Weekly repetition limits for flexible categories (prevents 8x EDUCATIONAL weeks)
CATEGORY_WEEKLY_LIMITS: Dict[str, int] = {
    "EDUCATIONAL": 3,
    "ENGAGEMENT": 4,
    "WATCHLIST": 2,
    "TECHNICAL_ANALYSIS": 3,
    "NEWSLETTER_CTA": 2,
    "THEME_ANALYSIS": 8,
    "MARKET_COMMENTARY": 4,
    "PERFORMANCE": 3,
}

# No category should appear more than twice per day
MAX_SAME_CATEGORY_PER_DAY = 2

# Categories that draw from the same underlying ticker pool (portfolio positions).
# Limit per day prevents the same tickers appearing in 3+ tweets on one day.
PORTFOLIO_POOL_CATEGORIES = {"PERFORMANCE", "THEME_ANALYSIS", "TECHNICAL_ANALYSIS"}
MAX_PORTFOLIO_POOL_PER_DAY = 2


# ═══════════════════════════════════════════════════════════════════════════════
# COST TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class CostTracker:
    """Track LLM API usage and cost across a generation run."""

    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.api_calls: int = 0

    def record(self, response) -> None:
        """Record token usage from an Anthropic API response."""
        usage = getattr(response, "usage", None)
        if usage:
            self.input_tokens += getattr(usage, "input_tokens", 0)
            self.output_tokens += getattr(usage, "output_tokens", 0)
        self.api_calls += 1

    @property
    def total_cost(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * COST_INPUT_PER_M.get(MODEL, 3.0)
        output_cost = (self.output_tokens / 1_000_000) * COST_OUTPUT_PER_M.get(MODEL, 15.0)
        return round(input_cost + output_cost, 4)

    def summary(self) -> str:
        return (
            f"API calls: {self.api_calls} | "
            f"Input: {self.input_tokens:,} tokens | "
            f"Output: {self.output_tokens:,} tokens | "
            f"Cost: ${self.total_cost:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE GUIDE LOADING
# ═══════════════════════════════════════════════════════════════════════════════

# Embedded style guide used when FINTWIT_STYLE_GUIDE.md doesn't exist on disk.
# Derived from STERLING_SIGNALS_PRD_v2.md sections 3.1–3.6.

EMBEDDED_STYLE_GUIDE = """
# Sterling Signals — Tweet Style Cheat Sheet

## Core Philosophy
- Value in EVERY tweet. No filler. If it doesn't teach, show receipts, or give a trade idea — don't post it.
- Winners only. Show gains ≥25% with entry → current. Never show losses. Sell signals = "setup invalidated."
- Specificity wins. $TICKER + price + context beats vague commentary every time.
- Receipts culture. Show entries, show exits, show the process. Let the numbers do the talking.

## Tweet Categories

| Category | Chart? | Must Include |
|----------|--------|-------------|
| SCANNER_RESULT | YES | $TICKER + entry price + thesis |
| DAILY_SIGNAL | YES | $TICKER + price + context |
| THEME_ANALYSIS | Rec. | Theme name + $TICKER(s) + prices |
| PERFORMANCE | YES | $TICKER + entry → current + %gain |
| WATCHLIST | Opt. | $TICKER(s) + prices + trigger |
| TECHNICAL_ANALYSIS | YES | $TICKER + level + invalidation |
| EDUCATIONAL | Opt. | Concrete example + lesson |
| MARKET_COMMENTARY | Rec. | Context + opportunity |
| SELL_SIGNAL | YES | $TICKER + "setup invalidated" |
| ENGAGEMENT | No | Trading-adjacent hook |
| NEWSLETTER_CTA | Opt. | Value prop + URL |

## Winners-Only Rules
- ≥25% gain: Show as receipt ($TICKER from $entry to $current (+X%))
- ≥0% but <25%: Mention in watchlist/theme context (no P&L)
- <0%: NEVER mention
- Sell signals: "setup invalidated below $level" — NO loss amount
- Stopped out: "Lost on $TICKER. Win more than you lose." — NO amount

## Power Phrases (PREFER these)
- "momentum confirmed"
- "institutional accumulation"
- "structural trend confirmation"
- "cleared all gates"
- "setup invalidated" (for exits)
- "win more than you lose"
- "NFA"
- "volatility expansion"
- "sector flow alignment"
- "theme alignment"
- "trailing stop locked"
- "strong accumulation"
- "receipts"
- "following institutional flows"
- "capital preservation"
- "risk-defined entries"
- "data doesn't lie"
- "no ego, just execution"
- "proprietary 5-gate screening"
- "the filter is tight for a reason"

## Sentence Style
- Short lines. One idea per sentence. Let data speak.
- Open with a hook: question, stat, $TICKER, or bold statement. Never "just wanted to share."
- Close with NFA or a question. Never "stay tuned" or "more to come."
- Mix formats: single-stat, lists, receipt tweets, thread starters.

## BANNED (NEVER output these)
- Internal indicators: HMA, BoS, BOS, Banker, VWAP, RSI, MACD, KDJ
- System terms: Gatekeeper, gate 1-5, 5-gate, tier 1/2/3, conviction score
- Old branding: TEAL, VIOLET, AMBER, PURPLE signals
- UK refs: UK ISA, GMT, BST, UK Time, GBP
- US retirement: Roth IRA, PDT, 401k
- Vague filler: "system keeps working", "theme keeps delivering", "trust the process",
  "some interesting setups", "stay tuned", "big news coming", "more to come",
  "keep an eye on", "you won't believe", "interesting developments"
- Loser focus: "still bleeding", "dragging down", "biggest loser"
- Leaked internals: "Capital Preservation Protocol", "Forensic Audit",
  "Volatility Expansion Criteria", "PASS signal"

## Data Injection Rule
Use EXACTLY the tickers and prices provided. Do NOT invent data.
Every tweet must contain at least one $TICKER with a price or percentage.
Exception: ENGAGEMENT and EDUCATIONAL may omit tickers if methodology-focused.
""".strip()

# ── Category-specific reference examples for few-shot prompting ──────────────
# Source: examples/tweet_examples.json + FINTWIT style guide
# Injected into _build_user_prompt() to guide LLM voice and data density.

CATEGORY_EXAMPLES: Dict[str, str] = {
    "SCANNER_RESULT": (
        '1) "Friday scan done. $INOD at $61.54 and $RCAT at $13.25 cleared all gates. '
        'Full breakdown in the newsletter."\n'
        '2) "1,800 stocks. 5 gates. 2 survivors this week. '
        "Quality over quantity — that's the whole point.\""
    ),
    "THEME_ANALYSIS": (
        '1) "AI Infrastructure keeps leading. $NVDA, $SMCI, $AVGO — institutional '
        'accumulation across the board. Structural trend confirmed."\n'
        "2) \"Nuclear renaissance isn't slowing. $OKLO $SMR — "
        'momentum confirmed, sector flow alignment. NFA."'
    ),
    "PERFORMANCE": (
        '1) "$RCAT from $8.50 to $13.25 (+55.9%). Drone tech thesis playing out. '
        'Trailing stop locked in."\n'
        "2) \"+47% closed on $AMPX. Held 6 weeks. Patience is boring until it isn't.\""
    ),
    "WATCHLIST": (
        '1) "On my radar: $IONQ at $42.15, $VNET at $10.80. '
        'Need one more confirmation for entry. NFA."\n'
        '2) "Watching closely: $QBTS at $6.20. Theme alignment is there. '
        'Waiting for momentum confirmation."'
    ),
    "SELL_SIGNAL": (
        '1) "$SMCI setup invalidated below $36. Win more than you lose. Moving on."\n'
        '2) "Lost on $VNET. Setup broke. System said exit, I exited. Next."'
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
    "TECHNICAL_ANALYSIS": (
        '1) "$WCC holding above $281 entry. Watching $320 resistance for breakout '
        'continuation. Setup invalidated below $256. NFA"\n'
        '2) "$STRL cleared $400 resistance — structural pivot confirmed. '
        'Invalidation on close below $362 entry. NFA!"'
    ),
}


# Closing CTA phrases — rotated to prevent "Save this post" monotony.
# Used when a tweet has 3+ tickers. None = no CTA (end naturally).
CLOSING_CTA_OPTIONS: List[Optional[str]] = [
    "Save this post",
    "Revisit this soonish",
    "Bookmark this",
    None,
]


def _pick_closing_cta(recent_closings: Optional[List[str]] = None) -> Optional[str]:
    """Pick a closing CTA not found in the last 5 tweet closings."""
    used: Set[Optional[str]] = set()
    if recent_closings:
        named_opts = [o for o in CLOSING_CTA_OPTIONS if o is not None]
        for closing in recent_closings:
            closing_lower = closing.lower()
            matched = False
            for opt in named_opts:
                if opt.lower() in closing_lower:
                    used.add(opt)
                    matched = True
            # If no named CTA matched, this closing had no CTA (= None option used)
            if not matched:
                used.add(None)

    for opt in CLOSING_CTA_OPTIONS:
        if opt not in used:
            return opt

    # All recently used — cycle back to first non-None
    for opt in CLOSING_CTA_OPTIONS:
        if opt is not None:
            return opt
    return None


def _load_style_guide() -> str:
    """Load the FinTwit style guide text. Falls back to embedded version."""
    if STYLE_GUIDE_PATH.exists():
        logger.info("Loading style guide from %s", STYLE_GUIDE_PATH)
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    logger.info("FINTWIT_STYLE_GUIDE.md not found — using embedded style guide")
    return EMBEDDED_STYLE_GUIDE


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def _load_signals(signals_path: str) -> Dict:
    """Load signals.json and return the parsed dict."""
    path = Path(signals_path)
    if not path.exists():
        logger.warning("Signals file not found: %s", path)
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _load_portfolio(portfolio_path: str) -> List[Dict]:
    """Load portfolio.csv and return list of position dicts."""
    import csv

    path = Path(portfolio_path)
    if not path.exists():
        logger.warning("Portfolio file not found: %s", path)
        return []

    positions: List[Dict] = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Coerce numeric fields
            for key in ("entry_price", "exit_price", "highest_close", "current_price"):
                if row.get(key):
                    try:
                        row[key] = float(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0.0
            positions.append(row)
    return positions


def _build_content_data(
    signals: Dict,
    positions: List[Dict],
    market_data: Optional[Dict] = None,
) -> ContentData:
    """Build a ContentData object from raw signals and portfolio data."""
    big_win_threshold = MARKETING_THRESHOLDS.get("big_win_threshold", 25.0)

    # Extract from signals
    pass_signals = signals.get("pass_signals", []) or signals.get("buy_signals", [])
    consider_signals = signals.get("consider_signals", []) or signals.get("caution_signals", [])
    themes = signals.get("themes", [])
    stats = signals.get("stats", {})
    sell_sigs = signals.get("sell_signals", [])
    scan_date = signals.get("timestamp", datetime.now().strftime("%Y-%m-%d"))[:10]

    # Fetch current prices for open positions missing current_price
    open_tickers_needing_price = [
        pos.get("ticker", "")
        for pos in positions
        if pos.get("status", "").upper() == "OPEN"
        and not float(pos.get("current_price", 0) or 0) > 0
    ]
    if open_tickers_needing_price:
        logger.info("Fetching prices for %d positions via yfinance", len(open_tickers_needing_price))
        try:
            from portfolio.manager import fetch_current_prices
            live_prices = fetch_current_prices(open_tickers_needing_price)
            for pos in positions:
                ticker = pos.get("ticker", "")
                if ticker in live_prices and not float(pos.get("current_price", 0) or 0) > 0:
                    pos["current_price"] = live_prices[ticker]
        except Exception as e:
            logger.warning("Could not fetch live prices: %s — continuing with available data", e)

    # Split positions into winners / notable / holdings / losers
    winners: List[Dict] = []
    notable_holdings: List[Dict] = []
    holdings: List[Dict] = []

    for pos in positions:
        if pos.get("status", "").upper() != "OPEN":
            continue
        entry = float(pos.get("entry_price", 0) or 0)
        current = float(pos.get("current_price", 0) or 0)
        if entry <= 0 or current <= 0:
            continue
        pnl_pct = ((current / entry) - 1) * 100
        pos["pnl_pct"] = pnl_pct
        if pnl_pct >= big_win_threshold:
            winners.append(pos)
        elif pnl_pct >= NOTABLE_WIN_THRESHOLD:
            notable_holdings.append(pos)
        elif pnl_pct >= 0:
            holdings.append(pos)
        # pnl_pct < 0: SKIP — never mention losers

    return ContentData(
        pass_signals=pass_signals,
        consider_signals=consider_signals,
        themes=themes,
        scan_stats=stats,
        winners=winners,
        notable_holdings=notable_holdings,
        holdings=holdings,
        sell_signals=sell_sigs,
        market_data=market_data,
        scan_date=scan_date,
        newsletter_url=NEWSLETTER_URL,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY SCHEDULE PLANNING
# ═══════════════════════════════════════════════════════════════════════════════

def _plan_weekly_schedule(data: ContentData, account_id: str = "main") -> List[SlotAssignment]:
    """
    Plan category allocation across 7 days x 4 slots.

    Rules (from PRD section 4.1.3):
      - PERFORMANCE receipts: at least 1/day when winners exist
      - SCANNER_RESULT: Saturday (day after weekly scan)
      - THEME_ANALYSIS: at least 2/week
      - ENGAGEMENT: max 1/day, max 5/week
      - EDUCATIONAL: max 5/week
      - Any category: max 2/day
      - NEWSLETTER_CTA: max 2/week

    Tracks planned data consumption and category repetition to prevent
    over-scheduling categories beyond available data.

    Args:
        data: ContentData with available signals, themes, etc.
        account_id: Account identifier — used to seed slot order shuffle
                    so each account gets a consistently different schedule.
    """
    schedule: List[SlotAssignment] = []
    newsletter_cta_count = 0
    theme_count = 0
    planned_counts: Dict[str, int] = {}       # Tracks data consumption
    week_category_counts: Dict[str, int] = {}  # Tracks category repetition

    _CONSUME_MAP = {
        "SCANNER_RESULT": "pass_signals",
        "SELL_SIGNAL": "sell_signals",
        "THEME_ANALYSIS": "themes",
    }

    # Seed slot ordering per account for schedule variation.
    # Each account gets a reproducibly different processing order,
    # which causes _pick_category() to make different choices.
    rng = random.Random(hash(account_id))

    for day in WEEKLY_DAYS:
        day_engagement_used = False
        day_performance_placed = False
        day_category_counts: Dict[str, int] = {}  # Reset per day
        day_portfolio_pool_count = 0  # Track portfolio-pool categories per day

        # Shuffle slot processing order per account for category variation
        day_slots = list(WEEKLY_SLOTS)
        rng.shuffle(day_slots)

        for slot in day_slots:
            assert slot != 1, "Slot 1 must not appear in weekly schedule (reserved for daily queue)"
            category, data_key = _pick_category(
                day=day,
                slot=slot,
                data=data,
                day_engagement_used=day_engagement_used,
                day_performance_placed=day_performance_placed,
                newsletter_cta_count=newsletter_cta_count,
                theme_count=theme_count,
                schedule=schedule,
                planned_counts=planned_counts,
                week_category_counts=week_category_counts,
                day_category_counts=day_category_counts,
                day_portfolio_pool_count=day_portfolio_pool_count,
            )

            schedule.append(SlotAssignment(
                day=day,
                slot=slot,
                category=category,
                data_key=data_key,
            ))

            # Existing tracking
            if category == "ENGAGEMENT":
                day_engagement_used = True
            if category == "PERFORMANCE":
                day_performance_placed = True
            if category == "NEWSLETTER_CTA":
                newsletter_cta_count += 1
            if category == "THEME_ANALYSIS":
                theme_count += 1

            # Update repetition counts
            week_category_counts[category] = week_category_counts.get(category, 0) + 1
            day_category_counts[category] = day_category_counts.get(category, 0) + 1

            # Track portfolio pool usage per day
            if category in PORTFOLIO_POOL_CATEGORIES:
                day_portfolio_pool_count += 1

            # Track planned data consumption
            if category in _CONSUME_MAP:
                key = _CONSUME_MAP[category]
                planned_counts[key] = planned_counts.get(key, 0) + 1

    # Enforcement pass: ensure at least 2 THEME_ANALYSIS per week
    if theme_count < 2 and data.has_themes:
        _inject_category(schedule, "THEME_ANALYSIS", "themes", 2 - theme_count)

    return schedule


def _data_available(
    category: str,
    data: ContentData,
    planned_counts: Dict[str, int],
) -> bool:
    """Check if a data-dependent category has unplanned data remaining."""
    if category == "SELL_SIGNAL":
        return planned_counts.get("sell_signals", 0) < len(data.sell_signals)
    if category == "SCANNER_RESULT":
        return planned_counts.get("pass_signals", 0) < len(data.pass_signals)
    if category == "PERFORMANCE":
        return data.has_winners or data.has_notable_holdings
    if category == "THEME_ANALYSIS":
        return planned_counts.get("themes", 0) < len(data.themes)
    if category == "WATCHLIST":
        return bool(data.consider_signals)
    if category == "TECHNICAL_ANALYSIS":
        return bool(data.holdings)
    if category == "MARKET_COMMENTARY":
        return data.market_data is not None
    if category == "NEWSLETTER_CTA":
        return bool(data.newsletter_url)
    return True  # Flexible categories always available


def _within_limits(
    category: str,
    week_counts: Dict[str, int],
    day_counts: Dict[str, int],
) -> bool:
    """Check if a category is within its weekly and daily repetition limits."""
    weekly_limit = CATEGORY_WEEKLY_LIMITS.get(category, 999)
    if week_counts.get(category, 0) >= weekly_limit:
        return False
    if day_counts.get(category, 0) >= MAX_SAME_CATEGORY_PER_DAY:
        return False
    return True


def _try_assign(
    category: str,
    data_key: str,
    data: ContentData,
    planned_counts: Dict[str, int],
    week_counts: Dict[str, int],
    day_counts: Dict[str, int],
) -> Optional[Tuple[str, str]]:
    """Try to assign a category. Returns (category, data_key) or None."""
    if not _data_available(category, data, planned_counts):
        return None
    if not _within_limits(category, week_counts, day_counts):
        return None
    return (category, data_key)


def _pick_category(
    *,
    day: str,
    slot: int,
    data: ContentData,
    day_engagement_used: bool,
    day_performance_placed: bool,
    newsletter_cta_count: int,
    theme_count: int,
    schedule: List[SlotAssignment],
    planned_counts: Optional[Dict[str, int]] = None,
    week_category_counts: Optional[Dict[str, int]] = None,
    day_category_counts: Optional[Dict[str, int]] = None,
    day_portfolio_pool_count: int = 0,
) -> Tuple[str, str]:
    """Pick the best category for a given day/slot based on rules, data, and limits.

    Uses _try_assign() to check data availability and repetition limits
    before assigning a category. Falls back through defined chains when
    the preferred category is exhausted or over-limit.
    """
    pc = planned_counts or {}
    wc = week_category_counts or {}
    dc = day_category_counts or {}

    def _try(cat: str, key: str) -> Optional[Tuple[str, str]]:
        # Gate portfolio-pool categories to prevent same-ticker saturation per day
        if cat in PORTFOLIO_POOL_CATEGORIES and day_portfolio_pool_count >= MAX_PORTFOLIO_POOL_PER_DAY:
            return None
        return _try_assign(cat, key, data, pc, wc, dc)

    def _fallback(
        preferred: str,
        preferred_key: str,
        chain: List[Tuple[str, str]],
    ) -> Optional[Tuple[str, str]]:
        """Try preferred, then each fallback. Log when falling back."""
        result = _try(preferred, preferred_key)
        if result:
            return result
        for fb_cat, fb_key in chain:
            result = _try(fb_cat, fb_key)
            if result:
                logger.debug(
                    "Category %s unavailable for %s/%s, falling back to %s",
                    preferred, day, slot, fb_cat,
                )
                return result
        return None

    # Saturday slot 2: SCANNER_RESULT (day after weekly scan)
    if day == "saturday" and slot == 2:
        result = _fallback("SCANNER_RESULT", "pass_signals", [
            ("WATCHLIST", "consider_signals"),
            ("THEME_ANALYSIS", "themes"),
            ("EDUCATIONAL", "educational"),
        ])
        if result:
            return result

    # Saturday slot 3: second SCANNER_RESULT or THEME_ANALYSIS
    if day == "saturday" and slot == 3:
        result = _fallback("SCANNER_RESULT", "pass_signals", [
            ("THEME_ANALYSIS", "themes"),
            ("EDUCATIONAL", "educational"),
        ])
        if result:
            return result

    # Slot 2: PERFORMANCE receipt if winners/notable exist
    if slot == 2 and not day_performance_placed:
        result = _fallback("PERFORMANCE", "winners", [
            ("TECHNICAL_ANALYSIS", "holdings"),
            ("THEME_ANALYSIS", "themes"),
        ])
        if result:
            return result

    # Slot 4: PERFORMANCE if not yet placed today
    if slot == 4 and not day_performance_placed:
        result = _fallback("PERFORMANCE", "winners", [
            ("TECHNICAL_ANALYSIS", "holdings"),
            ("THEME_ANALYSIS", "themes"),
        ])
        if result:
            return result

    # Sell signals
    if slot == 3:
        result = _fallback("SELL_SIGNAL", "sell_signals", [
            ("TECHNICAL_ANALYSIS", "holdings"),
            ("EDUCATIONAL", "educational"),
        ])
        if result:
            return result

    # Theme analysis
    if slot == 2 and theme_count < 6:
        result = _fallback("THEME_ANALYSIS", "themes", [
            ("EDUCATIONAL", "educational"),
        ])
        if result:
            return result

    # Watchlist
    if slot == 3:
        result = _try("WATCHLIST", "consider_signals")
        if result:
            return result

    # Technical analysis
    if slot == 3:
        result = _try("TECHNICAL_ANALYSIS", "holdings")
        if result:
            return result

    # Watchlist also eligible for slot 4 (secondary content)
    if slot == 4:
        result = _try("WATCHLIST", "consider_signals")
        if result:
            return result

    # Technical analysis also for slot 4 on weekdays
    if slot == 4 and day not in ("saturday", "sunday"):
        result = _try("TECHNICAL_ANALYSIS", "holdings")
        if result:
            return result

    # Market commentary
    if slot == 2:
        result = _try("MARKET_COMMENTARY", "market_data")
        if result:
            return result

    # Newsletter CTA (max 2/week, prefer Sunday and Thursday)
    if newsletter_cta_count < 2 and day in ("sunday", "thursday") and slot == 5:
        result = _try("NEWSLETTER_CTA", "newsletter_url")
        if result:
            return result

    # Educational
    if slot == 4:
        result = _try("EDUCATIONAL", "educational")
        if result:
            return result

    # Engagement (max 1/day — day_engagement_used is separate from day_counts)
    if slot == 5 and not day_engagement_used:
        result = _try("ENGAGEMENT", "engagement")
        if result:
            return result

    # Terminal fallbacks — prefer data-rich categories over filler
    for cat, key in [
        ("SCANNER_RESULT", "pass_signals"),
        ("PERFORMANCE", "winners"),
        ("THEME_ANALYSIS", "themes"),
        ("MARKET_COMMENTARY", "market_data"),
        ("WATCHLIST", "consider_signals"),
        ("NEWSLETTER_CTA", "newsletter_url"),
        ("ENGAGEMENT", "engagement"),
        ("EDUCATIONAL", "educational"),
    ]:
        result = _try(cat, key)
        if result:
            return result

    # Last resort: THEME_ANALYSIS ignoring weekly limit (themes recycle with varied LLM output)
    # But still respect the per-day portfolio pool limit to prevent ticker monotony
    pool_ok = day_portfolio_pool_count < MAX_PORTFOLIO_POOL_PER_DAY
    if data.has_themes and pool_ok:
        logger.warning("All limits exhausted — assigning THEME_ANALYSIS overflow")
        return "THEME_ANALYSIS", "themes"

    logger.warning("All categories exhausted — assigning EDUCATIONAL overflow")
    return "EDUCATIONAL", "educational"


def _inject_category(
    schedule: List[SlotAssignment],
    category: str,
    data_key: str,
    count: int,
) -> None:
    """Replace lowest-priority slots to meet minimum category requirements."""
    replaceable = ["ENGAGEMENT", "EDUCATIONAL", "MARKET_COMMENTARY"]
    replaced = 0
    for assignment in reversed(schedule):
        if replaced >= count:
            break
        if assignment.category in replaceable:
            assignment.category = category
            assignment.data_key = data_key
            replaced += 1


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET GENERATION (LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system_prompt(style_guide: str) -> str:
    """Build the system prompt for tweet generation."""

    # Build banned terms block (first 60 most critical)
    banned_block = "\n".join(f"  - {term}" for term in CRITICAL_BANNED[:60])

    today = datetime.now()
    quarter = (today.month - 1) // 3 + 1
    date_line = f"Today is {today.strftime('%A, %B %d, %Y')}. Current quarter: Q{quarter} {today.year}."

    return f"""\
You are the social media voice of Sterling Signals, a weekly momentum trading scanner \
for US stocks. Generate tweets that are data-rich, specific, and compliant with the \
style guide below.

{date_line}

STYLE GUIDE:
{style_guide}

ADDITIONAL BANNED PHRASES (NEVER output any of these):
{banned_block}

RULES:
1. Use EXACTLY the tickers and prices provided. Do NOT invent data.
2. Every tweet must contain at least one $TICKER with a price or percentage.
   Exception: ENGAGEMENT and EDUCATIONAL tweets may omit tickers if methodology-focused.
3. Never mention negative P&L. Never reveal loss amounts. Sell signals use "setup invalidated" only.
4. Never use internal terms: HMA, BoS, Banker, tier, conviction, VWAP, gate references.
5. Keep tweets under 280 characters.
6. Output ONLY the tweet text — no labels, no quotes, no explanation.
7. VARIETY: Never reuse openings. Alternate questions/statements/imperatives. Mix short and long.
"""


def _build_user_prompt(
    category: str,
    slot_data: Dict,
    slot: SlotAssignment,
    recent_openings: Optional[List[str]] = None,
    recent_closings: Optional[List[str]] = None,
) -> str:
    """Build the user prompt for a specific tweet, injecting structured data."""

    cat_info = TWEET_CATEGORIES.get(category, {})
    required = cat_info.get("min_elements", [])

    prompt_parts = [
        f"Generate a single {category} tweet.",
        f"Day: {slot.day.capitalize()}, Slot: {slot.slot} ({SLOT_TIMES_ET.get(slot.slot, '??:??')} ET)",
        f"Required elements: {', '.join(required) if required else 'flexible'}",
        "",
        "DATA (use EXACTLY these values):",
    ]

    # Inject category-specific data
    if category == "SCANNER_RESULT" and "signals" in slot_data:
        for sig in slot_data["signals"][:3]:
            prompt_parts.append(
                f"  ${{ticker}}: ${sig.get('symbol', '??')} at ${sig.get('price', 0):.2f} "
                f"| Theme: {sig.get('theme', 'N/A')} | Thesis: {sig.get('catalyst_summary', 'momentum confirmed')}"
            )
        _cta = _pick_closing_cta(recent_closings)
        if _cta:
            prompt_parts.append(f"  If listing 3+ tickers, end with: '{_cta}'")
        else:
            prompt_parts.append("  End naturally with NFA or a concise hook.")

    elif category == "PERFORMANCE" and ("winners" in slot_data or "notable" in slot_data):
        all_positions = slot_data.get("winners", []) + slot_data.get("notable", [])
        for w in all_positions[:3]:
            entry = float(w.get("entry_price", 0) or 0)
            current = float(w.get("current_price", 0) or 0)
            pnl = w.get("pnl_pct", 0)
            prompt_parts.append(
                f"  ${w.get('ticker', '??')} from ${entry:.2f} to ${current:.2f} (+{pnl:.1f}%)"
                f" | Theme: {w.get('theme', 'N/A')}"
            )
        _cta = _pick_closing_cta(recent_closings)
        cta_instruction = f" If showing 3+ tickers, end with: '{_cta}'" if _cta else ""
        prompt_parts.append(
            "  Show ALL these positions as receipts with entry → current → % gain. "
            "Multi-ticker receipt format preferred when 2+ tickers available."
            + cta_instruction
        )

    elif category == "THEME_ANALYSIS" and "themes" in slot_data:
        for th in slot_data["themes"][:2]:
            prompt_parts.append(
                f"  Theme: {th.get('name', '??')} ({th.get('classification', 'INVESTABLE')})"
                f" | Score: {th.get('composite_score', 0)}/10"
            )
        if "portfolio_holdings" in slot_data:
            prompt_parts.append("  Portfolio positions in related themes:")
            for t in slot_data["portfolio_holdings"][:4]:
                prompt_parts.append(
                    f"    ${t['symbol']} at ${t['price']:.2f} "
                    f"(+{t['pnl_pct']}% from ${t['entry_price']:.2f}) "
                    f"| Theme: {t['theme']}"
                )
            _cta = _pick_closing_cta(recent_closings)
            cta_instruction = f" If 3+ tickers, end with: '{_cta}'" if _cta else ""
            prompt_parts.append(
                "  CRITICAL: Use ONLY the portfolio tickers listed above. "
                "Do NOT invent or add any tickers not shown here. "
                "Structure: Theme observation → each ticker with entry→current→% on its own line → closing hook."
                + cta_instruction
            )
        if "tickers" in slot_data:
            prompt_parts.append("  Scanner signals in this theme:")
            for t in slot_data["tickers"][:4]:
                prompt_parts.append(f"    ${t.get('symbol', '??')} at ${t.get('price', 0):.2f}")
            prompt_parts.append(
                "  You may reference these scanner tickers too, but do NOT invent others."
            )

    elif category == "SELL_SIGNAL" and "sell_signals" in slot_data:
        for ss in slot_data["sell_signals"][:2]:
            prompt_parts.append(
                f"  ${ss.get('symbol', '??')} — setup invalidated. "
                f"No loss amounts. Frame as: 'Win more than you lose.'"
            )

    elif category == "WATCHLIST" and "consider" in slot_data:
        for cs in slot_data["consider"][:3]:
            prompt_parts.append(
                f"  ${cs.get('symbol', '??')} at ${cs.get('price', 0):.2f}"
                f" | Theme: {cs.get('theme', 'N/A')}"
                f" | Watching for: {cs.get('action', 'momentum confirmation')}"
            )
        _cta = _pick_closing_cta(recent_closings)
        cta_instruction = f" If listing 3+ tickers, end with: '{_cta}'" if _cta else ""
        prompt_parts.append(
            "  Write a watchlist tweet. Open with a hook like 'On my radar:' or "
            "'Watching closely:'. List each ticker with price. "
            "Close with what needs to happen for entry."
            + cta_instruction
            + " End with NFA."
        )

    elif category == "NEWSLETTER_CTA":
        prompt_parts.append(f"  Newsletter URL: {slot_data.get('newsletter_url', NEWSLETTER_URL)}")
        if slot_data.get("recent_wins"):
            for w in slot_data["recent_wins"][:2]:
                prompt_parts.append(
                    f"  Recent win: ${w.get('ticker', '??')} +{w.get('pnl_pct', 0):.0f}%"
                )
        if slot_data.get("portfolio_stats"):
            prompt_parts.append(
                f"  Tracking {slot_data['portfolio_stats'].get('open_positions', 0)} positions"
            )
        prompt_parts.append(
            "  Write a newsletter promotion. Lead with value (what the reader gets). "
            "Reference recent wins if available. Include the URL. "
            "Genuine and conversational, not salesy. End with NFA."
        )

    elif category == "DAILY_SIGNAL" and "daily_signals" in slot_data:
        for ds in slot_data["daily_signals"][:3]:
            prompt_parts.append(
                f"  ${ds.get('symbol', '??')} at ${ds.get('price', 0):.2f}"
                f" | Daily buy signal | Theme: {ds.get('theme', 'N/A')}"
            )

    elif category == "TECHNICAL_ANALYSIS" and "tickers" in slot_data:
        for t in slot_data["tickers"][:2]:
            prompt_parts.append(
                f"  ${t.get('symbol', '??')} at ${t.get('price', 0):.2f}"
                f" | Entry: ${t.get('entry_price', 0):.2f}"
                f" | Stop: ${t.get('stop_level', 0):.2f}"
                f" | Theme: {t.get('theme', 'N/A')}"
            )
        prompt_parts.append(
            "  Write a technical analysis tweet. Reference a specific price level "
            "and invalidation criteria. Short and punchy. "
            "Example style: '$TICKER holding above $X.XX support. "
            "Easy invalidation on close below $Y.YY. NFA!'"
        )

    elif category == "EDUCATIONAL":
        if slot_data.get("context"):
            prompt_parts.append(f"  Context: {slot_data['context']}")
        if slot_data.get("portfolio_stats"):
            stats = slot_data["portfolio_stats"]
            profitable = stats.get("profitable_count", 0)
            prompt_parts.append(
                f"  Portfolio: {stats.get('open_positions', 0)} open positions, "
                f"{profitable} currently profitable"
            )
            if profitable > 0:
                prompt_parts.append(
                    f"  IMPORTANT: Do NOT claim the portfolio has zero gains, "
                    f"is at breakeven, or has no winners. "
                    f"{profitable} positions are currently profitable."
                )
        if slot_data.get("theme_names"):
            prompt_parts.append(f"  Active themes: {', '.join(slot_data['theme_names'])}")
        prompt_parts.append(
            "  Write about trading concepts. Do NOT reference specific tickers "
            "unless from portfolio data."
        )

    elif category == "ENGAGEMENT":
        if slot_data.get("context"):
            prompt_parts.append(f"  Context: {slot_data['context']}")
        if slot_data.get("portfolio_stats"):
            stats = slot_data["portfolio_stats"]
            prompt_parts.append(
                f"  Portfolio: {stats.get('open_positions', 0)} open positions"
            )
        prompt_parts.append(
            "  Write an engaging community tweet. No specific tickers required."
        )

    elif category == "MARKET_COMMENTARY":
        if slot_data.get("context"):
            prompt_parts.append(f"  Context: {slot_data['context']}")
        if slot_data.get("tickers"):
            for t in slot_data["tickers"][:2]:
                prompt_parts.append(
                    f"  Reference: ${t.get('symbol', '??')} at ${t.get('price', 0):.2f}"
                )

    if category in CATEGORY_EXAMPLES:
        prompt_parts.append("")
        prompt_parts.append(
            "REFERENCE EXAMPLES (match style and data density, not exact words):"
        )
        prompt_parts.append(CATEGORY_EXAMPLES[category])

    if recent_openings:
        prompt_parts.append("")
        prompt_parts.append(
            "CRITICAL — DO NOT start your tweet with any of these "
            "(already used this week):"
        )
        for opening in recent_openings:
            prompt_parts.append(f'  - "{opening}"')
        prompt_parts.append("Use a completely different opening structure.")

    prompt_parts.append("")
    prompt_parts.append("Output ONLY the tweet text (under 280 characters). No labels or quotes.")

    return "\n".join(prompt_parts)


def _prepare_slot_data(category: str, data: ContentData, used_indices: Dict) -> Optional[Dict]:
    """Prepare the data payload for a specific tweet generation call.

    Returns None when the requested category has exhausted its data,
    signalling the generation loop to skip this slot.  Flexible categories
    (EDUCATIONAL, ENGAGEMENT, MARKET_COMMENTARY, NEWSLETTER_CTA) always
    return a dict.
    """
    slot_data: Dict = {}

    if category == "SCANNER_RESULT":
        idx = used_indices.get("pass_signals", 0)
        if idx >= len(data.pass_signals):
            return None  # No more signals to show
        slot_data["signals"] = data.pass_signals[idx:idx + 2]
        used_indices["pass_signals"] = idx + 1

    elif category == "PERFORMANCE":
        idx = used_indices.get("winners", 0)
        combined = data.winners + data.notable_holdings
        if not combined:
            return None  # No winners or notable holdings to showcase
        slot_data["winners"] = combined[idx:idx + 2]
        if data.notable_holdings:
            slot_data["notable"] = data.notable_holdings
        used_indices["winners"] = (idx + 1) % max(len(combined), 1)

    elif category == "THEME_ANALYSIS":
        idx = used_indices.get("themes", 0)
        if idx >= len(data.themes):
            return None  # No more themes
        slot_data["themes"] = data.themes[idx:idx + 2]
        used_indices["themes"] = idx + 1
        # Add tickers from pass_signals that match the theme
        if data.pass_signals:
            slot_data["tickers"] = data.pass_signals[:4]
        # Enrich with portfolio holdings (winners + notable) grouped by theme
        portfolio_tickers = []
        for pos in data.winners + data.notable_holdings:
            p_entry = float(pos.get("entry_price", 0) or 0)
            p_current = float(pos.get("current_price", 0) or 0)
            p_pnl = pos.get("pnl_pct", 0)
            if p_entry > 0 and p_current > 0:
                portfolio_tickers.append({
                    "symbol": pos.get("ticker", "??"),
                    "price": p_current,
                    "entry_price": p_entry,
                    "pnl_pct": round(p_pnl, 1),
                    "theme": pos.get("theme", "N/A"),
                })
        if portfolio_tickers:
            slot_data["portfolio_holdings"] = portfolio_tickers

    elif category == "SELL_SIGNAL":
        idx = used_indices.get("sell_signals", 0)
        if idx >= len(data.sell_signals):
            return None  # No more sell signals
        slot_data["sell_signals"] = data.sell_signals[idx:idx + 1]
        used_indices["sell_signals"] = idx + 1

    elif category == "WATCHLIST":
        if not data.consider_signals:
            return None  # No consider signals for watchlist
        slot_data["consider"] = data.consider_signals[:3]

    elif category == "DAILY_SIGNAL":
        idx = used_indices.get("daily_signals", 0)
        if idx >= len(data.daily_signals):
            return None  # No more daily signals
        slot_data["daily_signals"] = data.daily_signals[idx:idx + 2]
        used_indices["daily_signals"] = idx + 1

    elif category == "TECHNICAL_ANALYSIS":
        # Combine all open positions for TA (winners + notable + holdings)
        ta_positions = data.winners + data.notable_holdings + data.holdings
        if not ta_positions:
            return None  # No open positions for technical analysis
        idx = used_indices.get("ta_holdings", 0)
        selected = ta_positions[idx % len(ta_positions):idx % len(ta_positions) + 2]
        if not selected:
            selected = ta_positions[:2]
        used_indices["ta_holdings"] = idx + 1
        slot_data["tickers"] = []
        for h in selected:
            entry = float(h.get("entry_price", 0) or 0)
            current = float(h.get("current_price", 0) or 0)
            highest = float(h.get("highest_close", 0) or 0)
            stop_level = highest * 0.80 if highest > 0 else 0  # Capital preservation level (approximate)
            slot_data["tickers"].append({
                "symbol": h.get("ticker", "??"),
                "price": current,
                "entry_price": entry,
                "highest_close": highest,
                "stop_level": round(stop_level, 2),
                "theme": h.get("theme", "N/A"),
            })

    # Flexible categories — always return a dict (never None)
    elif category == "NEWSLETTER_CTA":
        slot_data["newsletter_url"] = data.newsletter_url
        # Add recent wins for social proof
        if data.winners:
            slot_data["recent_wins"] = [
                {"ticker": w.get("ticker", "??"), "pnl_pct": w.get("pnl_pct", 0)}
                for w in data.winners[:2]
            ]
        elif data.notable_holdings:
            slot_data["recent_wins"] = [
                {"ticker": n.get("ticker", "??"), "pnl_pct": n.get("pnl_pct", 0)}
                for n in data.notable_holdings[:2]
            ]
        open_count = len(data.winners) + len(data.notable_holdings) + len(data.holdings)
        slot_data["portfolio_stats"] = {"open_positions": open_count}

    elif category == "EDUCATIONAL":
        slot_data["context"] = "trading methodology and discipline"
        open_count = len(data.winners) + len(data.notable_holdings) + len(data.holdings)
        profitable_count = len(data.winners) + len(data.notable_holdings)
        slot_data["portfolio_stats"] = {
            "open_positions": open_count,
            "winners": len(data.winners),
            "notable": len(data.notable_holdings),
            "profitable_count": profitable_count,
        }
        if data.themes:
            slot_data["theme_names"] = [t.get("name", "") for t in data.themes[:3]]

    elif category == "ENGAGEMENT":
        slot_data["context"] = "community building and milestones"
        open_count = len(data.winners) + len(data.notable_holdings) + len(data.holdings)
        slot_data["portfolio_stats"] = {
            "open_positions": open_count,
            "winners": len(data.winners),
        }

    elif category == "MARKET_COMMENTARY":
        slot_data["context"] = json.dumps(data.market_data) if data.market_data else "general market conditions"
        if data.pass_signals:
            slot_data["tickers"] = [
                {"symbol": s.get("symbol", "??"), "price": s.get("price", 0)}
                for s in data.pass_signals[:2]
            ]

    return slot_data


def _generate_tweet(
    category: str,
    slot_data: Dict,
    slot: SlotAssignment,
    style_guide: str,
    client,
    cost_tracker: CostTracker,
    recent_openings: Optional[List[str]] = None,
    recent_closings: Optional[List[str]] = None,
) -> Tweet:
    """
    Make a single LLM call to generate one tweet.

    Args:
        category: The tweet category (e.g. SCANNER_RESULT)
        slot_data: Structured data for this tweet (tickers, prices, %)
        slot: The SlotAssignment for this tweet
        style_guide: Full style guide text
        client: Anthropic client instance
        cost_tracker: Running cost tracker
        recent_openings: First 60 chars of recent tweet openings to avoid repetition
        recent_closings: Last lines of recent tweets to avoid CTA repetition

    Returns:
        Tweet object with text, category, chart_required, tickers_mentioned
    """
    system_prompt = _build_system_prompt(style_guide)
    user_prompt = _build_user_prompt(category, slot_data, slot, recent_openings=recent_openings, recent_closings=recent_closings)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,  # Single tweet never needs more
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    cost_tracker.record(response)

    text = response.content[0].text.strip()
    # Strip any wrapping quotes the LLM might add
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    chart_required = category in CHART_REQUIRED_CATEGORIES
    tickers = re.findall(r'\$[A-Z]{2,5}', text)

    return Tweet(
        text=text,
        category=category,
        chart_required=chart_required,
        tickers_mentioned=tickers,
        metadata={
            "day": slot.day,
            "slot": slot.slot,
            "data_key": slot.data_key,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE (PRD section 3.6)
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_tweet(
    tweet: Tweet,
    source_data: Dict,
    allowed_tickers: Optional[Set[str]] = None,
) -> ValidationResult:
    """
    Run the 7-step validation pipeline on a single tweet.

    Steps:
        1. Category check
        2. Ticker + price check
        3. Banned phrase check
        4. Winners-only check
        5. Internal terminology check
        6. Character count
        7. Chart flag
    """
    failures: List[str] = []
    details: Dict = {}

    # ── Step 1: Category check ─────────────────────────────────────────────
    if tweet.category not in VALID_CATEGORIES:
        failures.append(f"step1_category: invalid category '{tweet.category}'")
    else:
        cat_info = TWEET_CATEGORIES[tweet.category]
        required = cat_info.get("min_elements", [])
        text_lower = tweet.text.lower()

        # Check for $TICKER presence (required for most categories)
        has_ticker = bool(re.search(r'\$[A-Z]{2,5}', tweet.text))
        if "$TICKER" in required or "entry price" in required or "price" in required:
            if not has_ticker:
                failures.append("step1_category: missing required $TICKER")

        # Check for price/percentage
        has_price = bool(re.search(r'\$\d+\.?\d*', tweet.text))
        has_pct = bool(re.search(r'[+-]?\d+\.?\d*%', tweet.text))
        if "entry price" in required or "current price" in required or "price" in required:
            if not has_price and not has_pct:
                failures.append("step1_category: missing required price or percentage")

        # Check for theme name in THEME_ANALYSIS
        if tweet.category == "THEME_ANALYSIS" and "theme name" in required:
            # Theme name check is loose — any capitalised multi-word will do
            pass  # Hard to validate without knowing exact theme names

        # Check for invalidation framing in SELL_SIGNAL
        if tweet.category == "SELL_SIGNAL" and "invalidation framing" in required:
            invalidation_terms = ["invalidat", "setup broke", "win more than you lose"]
            if not any(t in text_lower for t in invalidation_terms):
                failures.append("step1_category: SELL_SIGNAL missing invalidation framing")

        # Check for newsletter reference in NEWSLETTER_CTA
        if tweet.category == "NEWSLETTER_CTA":
            has_url = "sterlingsignals" in text_lower or "substack" in text_lower
            has_cta_word = any(w in text_lower for w in ("newsletter", "subscribe", "sign up", "free"))
            if not has_url and not has_cta_word:
                failures.append(
                    "step1_category: NEWSLETTER_CTA missing newsletter reference or CTA"
                )

    # ── Step 2a: Meta-language detection ───────────────────────────────────
    META_PATTERNS = [
        r"(?i)cannot generate",
        r"(?i)please provide",
        r"(?i)i need the specific",
        r"(?i)i don't have",
        r"\$TICKER",  # Literal placeholder
        r"(?i)to generate (?:a|this)",
        r"(?i)could you (?:please )?provide",
        r"(?i)no (?:ticker|price|data) (?:was |were )?provided",
    ]
    for pattern in META_PATTERNS:
        if re.search(pattern, tweet.text):
            failures.append(f"step2_meta: LLM meta-language detected matching '{pattern}'")

    # ── Step 2b: Ticker + price accuracy check ───────────────────────────
    tickers_in_tweet = re.findall(r'\$([A-Z]{2,5})', tweet.text)

    # Build source ticker set from slot data (backward compat)
    source_tickers: Set[str] = set()
    for key in ("signals", "winners", "consider", "sell_signals", "tickers",
                "daily_signals", "portfolio_holdings", "notable"):
        items = source_data.get(key, [])
        if isinstance(items, list):
            for item in items:
                sym = item.get("symbol") or item.get("ticker") or ""
                if sym:
                    source_tickers.add(sym.upper())

    # Merge with explicit allowed set if provided
    effective_allowed = (allowed_tickers or set()) | source_tickers

    if tickers_in_tweet and tweet.category in DATA_DEPENDENT_CATEGORIES:
        # Strict check: every ticker MUST exist in source data
        for ticker in tickers_in_tweet:
            if not effective_allowed or ticker not in effective_allowed:
                failures.append(f"step2_fabrication: ${ticker} not in source data")
                details["fabricated_tickers"] = details.get("fabricated_tickers", []) + [ticker]
    elif tickers_in_tweet:
        # Flexible categories: only check against source if we have source data
        for ticker in tickers_in_tweet:
            if source_tickers and ticker not in source_tickers:
                failures.append(f"step2_ticker: ${ticker} not in source data")
                details["fabricated_tickers"] = details.get("fabricated_tickers", []) + [ticker]

    # ── Step 3: Banned phrase check ────────────────────────────────────────
    text_lower = tweet.text.lower()
    for phrase in ALL_BANNED:
        phrase_lower = phrase.lower()
        if len(phrase) <= 4 and phrase.isascii():
            # Short terms need word-boundary matching to avoid false positives
            # e.g. "BST" matching inside "substack", "HMA" inside "PHARMA"
            if re.search(r'\b' + re.escape(phrase_lower) + r'\b', text_lower):
                failures.append(f"step3_banned: '{phrase}'")
        else:
            if phrase_lower in text_lower:
                failures.append(f"step3_banned: '{phrase}'")

    # ── Step 4: Winners-only check ─────────────────────────────────────────
    # No negative P&L percentages
    negative_pcts = re.findall(r'-\d+\.?\d*%', tweet.text)
    if negative_pcts:
        failures.append(f"step4_winners_only: negative percentage(s) found: {negative_pcts}")

    # ── Step 4b: Portfolio status fabrication check ──────────────────────
    if tweet.category == "EDUCATIONAL" and source_data.get("portfolio_stats"):
        stats = source_data["portfolio_stats"]
        profitable = stats.get("profitable_count", 0)
        if profitable > 0:
            fabrication_phrases = [
                "zero gains", "no winners", "0 showing profit", "breakeven",
                "no positions showing gains", "zero positions showing gains",
                "0 showing gains", "no gains yet", "haven't shown gains",
            ]
            text_lower_fab = tweet.text.lower()
            for phrase in fabrication_phrases:
                if phrase in text_lower_fab:
                    failures.append(
                        f"step_portfolio_fabrication: Claims '{phrase}' but "
                        f"{profitable} positions are profitable"
                    )
                    break

    # ── Step 5: Internal terminology check ─────────────────────────────────
    for pattern in INTERNAL_TERM_PATTERNS:
        match = re.search(pattern, tweet.text, re.IGNORECASE)
        if match:
            failures.append(f"step5_internal: '{match.group()}' is internal terminology")

    # ── Step 6: Character count ────────────────────────────────────────────
    if len(tweet.text) > MAX_TWEET_CHARS:
        failures.append(f"step6_chars: {len(tweet.text)} > {MAX_TWEET_CHARS}")

    # ── Step 6b: Temporal check ────────────────────────────────────────────
    now = datetime.now()
    current_quarter = (now.month - 1) // 3 + 1
    if current_quarter == 1 and re.search(r'year[\s-]?end', tweet.text, re.IGNORECASE):
        failures.append("step_temporal: References 'year-end' in Q1")
    for future_q in range(current_quarter + 1, 5):
        if re.search(rf'Q{future_q}\s*{now.year}', tweet.text, re.IGNORECASE):
            failures.append(f"step_temporal: References future Q{future_q} {now.year}")

    # ── Step 7: Chart flag check ───────────────────────────────────────────
    expected_chart = tweet.category in CHART_REQUIRED_CATEGORIES
    if tweet.chart_required != expected_chart:
        failures.append(
            f"step7_chart: chart_required={tweet.chart_required} "
            f"but expected {expected_chart} for {tweet.category}"
        )

    return ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
        details=details,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REPAIR (LLM re-generation with feedback)
# ═══════════════════════════════════════════════════════════════════════════════

def _repair_tweet(
    tweet: Tweet,
    failures: List[str],
    slot_data: Dict,
    style_guide: str,
    client,
    cost_tracker: CostTracker,
) -> Tweet:
    """
    Re-generate a tweet with specific feedback about validation failures.

    Makes a second LLM call including the failed tweet and error details.
    """
    system_prompt = _build_system_prompt(style_guide)

    repair_prompt = f"""\
The following tweet FAILED validation and must be rewritten.

FAILED TWEET:
{tweet.text}

VALIDATION ERRORS:
{chr(10).join(f'  - {f}' for f in failures)}

CATEGORY: {tweet.category}

Rewrite the tweet to fix ALL validation errors listed above.
Keep the same category ({tweet.category}) and use the same data.
Output ONLY the corrected tweet text (under 280 characters). No labels or quotes.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": repair_prompt}],
    )
    cost_tracker.record(response)

    text = response.content[0].text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    tickers = re.findall(r'\$[A-Z]{2,5}', text)
    chart_required = tweet.category in CHART_REQUIRED_CATEGORIES

    return Tweet(
        text=text,
        category=tweet.category,
        chart_required=chart_required,
        tickers_mentioned=tickers,
        metadata={**tweet.metadata, "repaired": True},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHART PATH ATTACHMENT
# ═══════════════════════════════════════════════════════════════════════════════


def _attach_chart_paths(tweets: List[Tweet], charts_dir: Optional[Path] = None) -> int:
    """
    Attach chart file paths to tweets that require them.

    Reads chart_manifest.json (generated by chart_capture.py and funnel_graphic.py)
    and matches chart paths to tweets by ticker.  Funnel graphics are matched to the
    first SCANNER_RESULT tweet without a specific ticker.

    Args:
        tweets: List of Tweet objects (modified in-place)
        charts_dir: Directory containing chart_manifest.json (default: CHARTS_DIR)

    Returns:
        Number of tweets that had chart paths attached
    """
    manifest_dir = charts_dir or CHARTS_DIR
    manifest_file = manifest_dir / "chart_manifest.json"

    if not manifest_file.exists():
        logger.info("No chart manifest found at %s — skipping chart attachment", manifest_file)
        return 0

    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read chart manifest: %s", e)
        return 0

    charts = manifest.get("charts", {})
    if not charts:
        logger.info("Chart manifest is empty — no charts to attach")
        return 0

    attached = 0
    funnel_used = False

    for tweet in tweets:
        if not tweet.chart_required or tweet.chart_path or tweet.chart_paths:
            continue  # Already has a chart or doesn't need one

        # PERFORMANCE: multi-chart — attach up to 4 winner charts
        if tweet.category == "PERFORMANCE":
            for ticker in tweet.tickers_mentioned[:4]:
                clean_ticker = ticker.lstrip("$").upper()
                chart_path = charts.get(clean_ticker)
                if chart_path and isinstance(chart_path, str):
                    full_path = BASE_DIR / chart_path if not os.path.isabs(chart_path) else Path(chart_path)
                    if not full_path.exists():
                        logger.warning("Chart file missing on disk for $%s: %s", clean_ticker, chart_path)
                        continue
                    tweet.chart_paths.append(chart_path)
                    attached += 1
                    logger.debug("Attached chart for $%s: %s (multi)", clean_ticker, chart_path)
            matched = bool(tweet.chart_paths)
        else:
            # Single-chart: existing behavior (break after first match)
            matched = False
            for ticker in tweet.tickers_mentioned:
                clean_ticker = ticker.lstrip("$").upper()
                chart_path = charts.get(clean_ticker)
                if chart_path and isinstance(chart_path, str):
                    # Verify chart file exists on disk
                    full_path = BASE_DIR / chart_path if not os.path.isabs(chart_path) else Path(chart_path)
                    if not full_path.exists():
                        logger.warning("Chart file missing on disk for $%s: %s", clean_ticker, chart_path)
                        continue  # Skip — don't attach a broken path
                    tweet.chart_path = chart_path
                    attached += 1
                    matched = True
                    logger.debug("Attached chart for $%s: %s", clean_ticker, chart_path)
                    break

        # For SCANNER_RESULT tweets about overall stats (no specific tickers), use funnel graphic
        if not matched and not funnel_used and tweet.category == "SCANNER_RESULT" and not tweet.tickers_mentioned:
            funnel = charts.get("funnel_graphic")
            if funnel:
                funnel_path = funnel.get("path") if isinstance(funnel, dict) else funnel
                if funnel_path:
                    tweet.chart_path = str(funnel_path)
                    attached += 1
                    funnel_used = True
                    logger.debug("Attached funnel graphic to SCANNER_RESULT tweet")

    # ── Fallback pass: funnel graphic for SCANNER_RESULT / THEME_ANALYSIS ──
    funnel_path = None
    funnel_entry = charts.get("funnel_graphic") or charts.get("funnel")
    if funnel_entry:
        funnel_path = funnel_entry.get("path") if isinstance(funnel_entry, dict) else funnel_entry

    if funnel_path:
        for tweet in tweets:
            if tweet.chart_required and not tweet.chart_path:
                if tweet.category in ("SCANNER_RESULT", "THEME_ANALYSIS"):
                    tweet.chart_path = str(funnel_path)
                    attached += 1
                    logger.debug("Funnel fallback for %s tweet", tweet.category)
                # PERFORMANCE: exempt from drop (multi-chart, soft requirement)
                # TECHNICAL_ANALYSIS, SELL_SIGNAL: no fallback — dropped later

    logger.info("Attached charts to %d / %d chart-required tweets", attached,
                sum(1 for t in tweets if t.chart_required))
    return attached


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE WRITING
# ═══════════════════════════════════════════════════════════════════════════════

def _write_queues(
    tweets: List[Tweet],
    queue_map: Dict[str, str],
    output_dir: Optional[Path] = None,
    scan_date: str = "",
) -> None:
    """
    Write tweet list to account queue(s).

    Each entry matches the format used by distribution/twitter_poster.py.
    When called with a single-account queue_map, writes to just that account.
    """
    out_dir = output_dir or TWITTER_OUTPUT
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build queue entries (drop chart-required tweets without charts)
    entries: List[Dict] = []
    dropped_no_chart = 0
    for i, tweet in enumerate(tweets):
        # Drop chart-required tweets that have no chart
        # PERFORMANCE exempt: receipt tweets are still valuable without charts
        has_any_chart = tweet.chart_path or tweet.chart_paths
        if tweet.chart_required and not has_any_chart and tweet.category != "PERFORMANCE":
            logger.warning(
                "DROP %s tweet (chart required but missing): %.60s...",
                tweet.category, tweet.text,
            )
            dropped_no_chart += 1
            continue

        day = tweet.metadata.get("day", "saturday")
        slot = tweet.metadata.get("slot", 1)
        if slot == 1:
            logger.warning(
                "SKIP slot 1 tweet in weekly queue (reserved for daily): %.60s...",
                tweet.text,
            )
            continue
        slot_time = SLOT_TIMES_ET.get(slot, "08:00")

        entries.append({
            "id": f"{day}_{slot}_{i}",
            "day": day.capitalize(),
            "slot": slot,
            "time": slot_time,
            "text": tweet.text,
            "category": tweet.category,
            "scheduled_date": _calculate_scheduled_date(scan_date, day) if scan_date else "",
            "status": "pending",
            "posted": False,
            "char_count": len(tweet.text),
            "mentioned_tickers": tweet.tickers_mentioned,
            "chart_required": tweet.chart_required,
            "chart_path": tweet.chart_path,
            "chart_paths": tweet.chart_paths,
            "timestamp": datetime.now().isoformat(),
        })

    if dropped_no_chart:
        logger.info("Dropped %d tweets missing required charts", dropped_no_chart)

    # Write content to account queue(s)
    for account_id, queue_file in queue_map.items():
        path = out_dir / queue_file
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)
        logger.info("Saved %d tweets to %s", len(entries), path)


def _calculate_scheduled_date(scan_date: str, day_name: str) -> str:
    """Calculate the scheduled date for a tweet given the scan date and day."""
    try:
        base = datetime.strptime(scan_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        base = datetime.now()
    offset = WEEKLY_DAYS.index(day_name.lower()) if day_name.lower() in WEEKLY_DAYS else 0
    return (base + timedelta(days=offset)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# FAILED TWEET LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _log_failed_tweet(tweet: Tweet, failures: List[str], output_dir: Optional[Path] = None) -> None:
    """Append a failed tweet to failed_tweets.json for manual review."""
    out_dir = output_dir or TWITTER_OUTPUT
    failed_path = Path(out_dir) / "failed_tweets.json"

    existing: List[Dict] = []
    if failed_path.exists():
        try:
            with open(failed_path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.append({
        "text": tweet.text,
        "category": tweet.category,
        "failures": failures,
        "metadata": tweet.metadata,
        "timestamp": datetime.now().isoformat(),
    })

    with open(failed_path, "w") as f:
        json.dump(existing, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY: WEEKLY CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_weekly_content(
    signals_path: str,
    portfolio_path: str,
    market_data: Optional[Dict] = None,
    output_dir: Optional[str] = None,
    account_id: str = "main",
) -> Dict:
    """
    Generate a full week of tweets (7 days x 4 slots = 28 tweets).

    Reads weekly signals.json and portfolio.csv, plans category allocation,
    generates tweets via LLM, validates, repairs if needed, and writes
    content to the specified account's queue file.

    When called 3× with different account_id values, the LLM naturally varies
    output and the schedule shuffles per account for differentiation.

    Args:
        signals_path: Path to signals.json
        portfolio_path: Path to portfolio.csv
        market_data: Optional market context dict
        output_dir: Output directory (default: twitter/output/)
        account_id: Which account to generate for ("main", "account2", "account3")

    Returns:
        Summary dict: {total_tweets, by_category, failed_count, chart_required_count}
    """
    if anthropic is None:
        logger.error("anthropic package not installed")
        return {"total_tweets": 0, "error": "anthropic not installed"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"total_tweets": 0, "error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    logger.info("=== Generating weekly content for account: %s ===", account_id)

    # 1. Load style guide
    style_guide = _load_style_guide()
    logger.info("Style guide loaded (%d chars)", len(style_guide))

    # 2. Load data
    signals = _load_signals(signals_path)
    positions = _load_portfolio(portfolio_path)
    data = _build_content_data(signals, positions, market_data)
    logger.info(
        "Data loaded: %d pass signals, %d winners, %d notable, %d themes, %d sell signals",
        len(data.pass_signals), len(data.winners), len(data.notable_holdings),
        len(data.themes), len(data.sell_signals),
    )

    # Build global allowed-ticker set from all source data
    all_tickers: Set[str] = set()
    for sig in data.pass_signals:
        sym = sig.get("symbol") or sig.get("ticker") or ""
        if sym:
            all_tickers.add(sym.upper())
    for sig in data.consider_signals:
        sym = sig.get("symbol") or sig.get("ticker") or ""
        if sym:
            all_tickers.add(sym.upper())
    for sig in data.sell_signals:
        sym = sig.get("symbol") or sig.get("ticker") or ""
        if sym:
            all_tickers.add(sym.upper())
    for pos in data.winners + data.notable_holdings + data.holdings:
        sym = pos.get("ticker") or pos.get("symbol") or ""
        if sym:
            all_tickers.add(sym.upper())
    logger.info("Allowed tickers for validation: %s", all_tickers)

    # 3. Plan schedule (seeded by account_id for category variation)
    schedule = _plan_weekly_schedule(data, account_id=account_id)
    logger.info("Schedule planned: %d slots across %d days (account=%s)", len(schedule), len(WEEKLY_DAYS), account_id)

    # 4. Generate + validate + repair
    valid_tweets: List[Tweet] = []
    recent_openings: List[str] = []  # Track tweet openings for diversity
    recent_closings: List[str] = []  # Track closing CTAs for variety
    failed_count = 0
    by_category: Dict[str, int] = {}
    used_indices: Dict[str, int] = {}

    for assignment in schedule:
        slot_data = _prepare_slot_data(assignment.category, data, used_indices)

        # Skip slots where data is exhausted (prevents fabrication)
        if slot_data is None:
            logger.warning(
                "SKIP %s/%s %s — no data available (exhausted)",
                assignment.day, assignment.slot, assignment.category,
            )
            continue

        # Generate
        tweet = _generate_tweet(
            category=assignment.category,
            slot_data=slot_data,
            slot=assignment,
            style_guide=style_guide,
            client=client,
            cost_tracker=cost_tracker,
            recent_openings=recent_openings,
            recent_closings=recent_closings,
        )

        # Validate
        result = _validate_tweet(tweet, slot_data, allowed_tickers=all_tickers)

        # Repair loop (max 2 attempts)
        repair_attempts = 0
        while not result.passed and repair_attempts < MAX_REPAIR_ATTEMPTS:
            logger.info(
                "Repairing %s tweet (%s/%s, attempt %d): %s",
                assignment.category, assignment.day, assignment.slot,
                repair_attempts + 1, result.failures[:2],
            )
            tweet = _repair_tweet(
                tweet, result.failures, slot_data, style_guide, client, cost_tracker,
            )
            result = _validate_tweet(tweet, slot_data, allowed_tickers=all_tickers)
            repair_attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category[tweet.category] = by_category.get(tweet.category, 0) + 1
            # Track opening for diversity (first 60 chars of first line)
            opening = tweet.text.split("\n")[0][:60]
            recent_openings.append(opening)
            if len(recent_openings) > 10:
                recent_openings = recent_openings[-10:]
            # Track closing phrase for CTA variety (last line, first 60 chars)
            closing = tweet.text.strip().split("\n")[-1][:60]
            recent_closings.append(closing)
            if len(recent_closings) > 5:
                recent_closings = recent_closings[-5:]
        else:
            logger.warning(
                "DROPPED tweet after %d repairs: %s/%s %s — %s",
                MAX_REPAIR_ATTEMPTS, assignment.day, assignment.slot,
                assignment.category, result.failures[:3],
            )
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Summary of generation phase
    skipped = len(schedule) - len(valid_tweets) - failed_count
    logger.info(
        "Generated %d tweets, failed %d, skipped %d (insufficient data)",
        len(valid_tweets), failed_count, skipped,
    )

    # 5. Attach chart paths from manifest (generated by chart_capture.py)
    charts_attached = _attach_chart_paths(valid_tweets)
    logger.info("Chart paths attached: %d", charts_attached)

    # 6. Write queue for this account only
    out = Path(output_dir) if output_dir else TWITTER_OUTPUT
    account_queue = {account_id: ACCOUNT_QUEUES[account_id]}
    _write_queues(valid_tweets, account_queue, out, data.scan_date)

    chart_required_count = sum(1 for t in valid_tweets if t.chart_required)
    chart_attached_count = sum(1 for t in valid_tweets if t.chart_path or t.chart_paths)

    logger.info(
        "Weekly generation complete: %d tweets, %d failed, %d charts required, %d charts attached",
        len(valid_tweets), failed_count, chart_required_count, chart_attached_count,
    )
    logger.info("Cost: %s", cost_tracker.summary())

    return {
        "total_tweets": len(valid_tweets),
        "by_category": by_category,
        "failed_count": failed_count,
        "chart_required_count": chart_required_count,
        "chart_attached_count": chart_attached_count,
        "cost": cost_tracker.summary(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY: DAILY CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_content(
    daily_signals_path: str,
    daily_portfolio_path: str,
    output_dir: Optional[str] = None,
    account_id: str = "main",
) -> Dict:
    """
    Generate daily tweets for new daily scan signals, sell signals, and winners.

    - Up to 5 DAILY_SIGNAL tweets (one per signal)
    - SELL_SIGNAL tweets for any daily exits
    - PERFORMANCE tweets for daily winners >= 25%

    When called 3× with different account_id values, the LLM naturally varies
    output for differentiation between accounts.

    Args:
        daily_signals_path: Path to daily_signals.json
        daily_portfolio_path: Path to daily_portfolio.csv
        output_dir: Output directory (default: twitter/output/)
        account_id: Which account to generate for ("main", "account2", "account3")

    Returns:
        Summary dict: {total_tweets, by_category, failed_count, chart_required_count}
    """
    if anthropic is None:
        logger.error("anthropic package not installed")
        return {"total_tweets": 0, "error": "anthropic not installed"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"total_tweets": 0, "error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()
    style_guide = _load_style_guide()

    logger.info("=== Generating daily content for account: %s ===", account_id)

    # Load daily signals
    daily_signals_raw = _load_signals(daily_signals_path)
    daily_buy_signals = daily_signals_raw.get("buy_signals", [])[:5]
    daily_sell_signals = daily_signals_raw.get("sell_signals", [])

    # Load daily portfolio for winners
    daily_positions = _load_portfolio(daily_portfolio_path)
    big_win = MARKETING_THRESHOLDS.get("big_win_threshold", 25.0)
    daily_winners = []
    for pos in daily_positions:
        if pos.get("status", "").upper() != "OPEN":
            continue
        entry = float(pos.get("entry_price", 0) or 0)
        current = float(pos.get("current_price", 0) or 0)
        if entry > 0 and current > 0:
            pnl = ((current / entry) - 1) * 100
            if pnl >= big_win:
                pos["pnl_pct"] = pnl
                daily_winners.append(pos)

    # Build content data for daily context
    data = ContentData(
        daily_signals=daily_buy_signals,
        daily_sells=daily_sell_signals,
        daily_winners=daily_winners,
        scan_date=datetime.now().strftime("%Y-%m-%d"),
        newsletter_url=NEWSLETTER_URL,
    )

    valid_tweets: List[Tweet] = []
    failed_count = 0
    by_category: Dict[str, int] = {}
    used_indices: Dict[str, int] = {}

    # Generate DAILY_SIGNAL tweets (one per signal, max 5)
    for i, sig in enumerate(daily_buy_signals):
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=5,  # Daily signals go to slot 5 (17:00 ET)
            category="DAILY_SIGNAL",
            data_key="daily_signals",
        )
        slot_data = {"daily_signals": [sig]}

        tweet = _generate_tweet("DAILY_SIGNAL", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["DAILY_SIGNAL"] = by_category.get("DAILY_SIGNAL", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Generate SELL_SIGNAL tweets
    for ss in daily_sell_signals:
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=5,
            category="SELL_SIGNAL",
            data_key="sell_signals",
        )
        slot_data = {"sell_signals": [ss]}

        tweet = _generate_tweet("SELL_SIGNAL", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["SELL_SIGNAL"] = by_category.get("SELL_SIGNAL", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Generate PERFORMANCE tweets for daily winners >= 25%
    for w in daily_winners:
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=1,  # Morning slot for receipts
            category="PERFORMANCE",
            data_key="winners",
        )
        slot_data = {"winners": [w]}

        tweet = _generate_tweet("PERFORMANCE", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["PERFORMANCE"] = by_category.get("PERFORMANCE", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Attach chart paths from manifest
    charts_attached = _attach_chart_paths(valid_tweets)

    # Write daily queue for this account only
    out = Path(output_dir) if output_dir else TWITTER_OUTPUT
    daily_account_queue = {account_id: DAILY_ACCOUNT_QUEUES[account_id]}
    _write_queues(valid_tweets, daily_account_queue, out, data.scan_date)

    chart_required_count = sum(1 for t in valid_tweets if t.chart_required)
    chart_attached_count = sum(1 for t in valid_tweets if t.chart_path or t.chart_paths)

    logger.info(
        "Daily generation complete: %d tweets, %d failed, %d charts attached",
        len(valid_tweets), failed_count, chart_attached_count,
    )
    logger.info("Cost: %s", cost_tracker.summary())

    return {
        "total_tweets": len(valid_tweets),
        "by_category": by_category,
        "failed_count": failed_count,
        "chart_required_count": chart_required_count,
        "chart_attached_count": chart_attached_count,
        "cost": cost_tracker.summary(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY HELPERS (backwards-compat with v1 imports in tests)
# ═══════════════════════════════════════════════════════════════════════════════

def get_tweet_char_count(text: str) -> int:
    """Calculate Twitter character count (handles Unicode).

    Emojis and characters above U+FFFF count as 2 characters on Twitter.
    """
    count = 0
    for char in text:
        if ord(char) > 0xFFFF:
            count += 2
        else:
            count += 1
    return count


def validate_tweet_length(text: str, max_length: int = 280) -> bool:
    """Check if tweet is within character limit."""
    return get_tweet_char_count(text) <= max_length


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """CLI entry point for tweet generation."""
    parser = argparse.ArgumentParser(
        description="Sterling Signals Tweet Generator v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--signals", default=str(SIGNALS_FILE),
        help="Path to signals.json (weekly) or daily_signals.json",
    )
    parser.add_argument(
        "--portfolio", default=str(PORTFOLIO_FILE),
        help="Path to portfolio.csv or daily_portfolio.csv",
    )
    parser.add_argument(
        "--output", default=str(TWITTER_OUTPUT),
        help="Output directory for queue files",
    )
    parser.add_argument(
        "--daily", action="store_true",
        help="Generate daily content instead of weekly",
    )
    parser.add_argument(
        "--account", default="all",
        choices=["all", "main", "account2", "account3"],
        help="Which account to generate for (default: all = run 3×)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Determine which accounts to generate for
    if args.account == "all":
        accounts = ["main", "account2", "account3"]
    else:
        accounts = [args.account]

    all_results: List[Dict] = []

    for acct in accounts:
        print(f"\n{'─' * 60}")
        print(f"  Generating for account: {acct}")
        print(f"{'─' * 60}")

        if args.daily:
            result = generate_daily_content(
                daily_signals_path=args.signals,
                daily_portfolio_path=args.portfolio,
                output_dir=args.output,
                account_id=acct,
            )
        else:
            result = generate_weekly_content(
                signals_path=args.signals,
                portfolio_path=args.portfolio,
                output_dir=args.output,
                account_id=acct,
            )
        all_results.append({"account": acct, **result})

    # Print summary
    print(f"\n{'=' * 60}")
    print("TWEET GENERATOR v2.0 — RESULTS")
    print(f"{'=' * 60}")
    for r in all_results:
        acct_label = r.get("account", "?")
        print(f"\n  Account: {acct_label}")
        print(f"  Total tweets:        {r.get('total_tweets', 0)}")
        print(f"  Failed (dropped):    {r.get('failed_count', 0)}")
        print(f"  Charts required:     {r.get('chart_required_count', 0)}")
        print(f"  Cost:                {r.get('cost', 'N/A')}")
        print(f"  By category:")
        for cat, count in sorted(r.get("by_category", {}).items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
