#!/usr/bin/env python3
"""
CONFIG - Centralized Configuration Constants
=============================================

Single source of truth for all configuration values used across the codebase.

Usage:
    from config import (
        TRAILING_STOP_PCT, MODEL_SONNET, SLOTS, SLOT_TIMES_ET
    )
"""

import os
import re
from pathlib import Path
from typing import Dict, List

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent  # Project root (one level up from config/)
TICKERS_FILE = BASE_DIR / "scanner" / "complete_tickers.txt"

# Section output roots (canonical definitions in config/output_paths.py)
from config.output_paths import (
    SCANNER_OUTPUT, PORTFOLIO_OUTPUT, SUBSTACK_OUTPUT, TWITTER_OUTPUT,
    SIGNALS_FILE, ANALYSIS_LOG,
    PORTFOLIO_FILE, SHEETS_EXPORT_FILE, EQUITY_CURVE_FILE,
    PORTFOLIO_BACKUP_DIR,
    LIVE_QUEUE_FILE, COWORK_QUEUE_FILE, LIVE_CONTEXT_FILE, LIVE_COST_LOG_FILE,
    CHARTS_DIR, FAILED_TWEETS_FILE, WORKFLOW_STATUS_FILE,
    TWEET_TRACKING_FILE, CELEBRATIONS_FILE,
)

# Legacy alias — DEPRECATED, kept for backward compat
TRADES_DIR = BASE_DIR / "trades"


# ═══════════════════════════════════════════════════════════════════════════════
# TARGET AUDIENCE (MASTER_TODO_v2 Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

TARGET_AUDIENCE: Dict[str, any] = {
    'region': 'Global',
    'account_type': 'Any',  # Audience-neutral - no specific account types
    'restrictions': [
        'No Roth IRA content',       # US-specific
        'No PDT rule content',       # US-specific
        'No 401k content',           # US-specific
        'No UK ISA content',         # UK-specific
        'No country-specific tax advice',
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# TICKER FREQUENCY LIMITS (MASTER_TODO_v2 Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

TICKER_LIMITS: Dict[str, int] = {
    'max_mentions_per_week': 4,        # Max times a ticker can appear in weekly tweets
    'max_consecutive_days': 2,         # Max consecutive days mentioning same ticker
    'cooldown_after_milestone': 2,     # Days to wait after milestone before mentioning again
}


# ═══════════════════════════════════════════════════════════════════════════════
# KILLED CATEGORIES (MASTER_TODO_v2 Phase 0) - DO NOT USE
# ═══════════════════════════════════════════════════════════════════════════════

KILLED_CATEGORIES: List[str] = [
    'roth_ira',          # Wrong audience (UK investors, not US)
    'pdt_friendly',      # Wrong audience (UK investors, not US)
    'position_update',   # Shows individual P&L - merged to top_performers
    'weekly_wins',       # Renamed to top_performers (misleading terminology)
]


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Legacy parameters (used by portfolio manager) ─────────────────────────────
TRAILING_STOP_PCT = 20.0      # 20% trailing stop
STOP_WARNING_PCT = 5.0        # Warn when within 5% of stop

# ── Sterling Grid Indicator Parameters (canonical source: sterling_indicators.py) ──
# Re-exported from the backtest-verified indicator module so downstream modules
# can continue using `from config import HMA_PERIOD` etc.
from scanner.sterling_indicators import (  # noqa: E402
    HMA_PERIOD,
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL as MACD_SIGNAL_PERIOD,  # config uses MACD_SIGNAL_PERIOD alias
    UC_TARGET_DAYS,
    UC_SENSITIVITY,
    UC_TIMEFRAME,
    LOCK_TIERS,
    MAX_CONCURRENT_POSITIONS,
    MIN_TRADE_SIZE,
    QUALITY_TIERS,
    SIZING_GEARS,
)

# ── Position Sizing — Additional Config ───────────────────────────────────────
MIN_CASH_RESERVE_PCT = 0.10   # Always keep 10% cash

# Legacy conviction tiers (kept for backward compat with existing portfolio/content systems)
CONVICTION_TIERS = {
    'HIGH':     {'min_conviction': 8, 'max_conviction': 10, 'equity_pct': 0.20, 'max_slots': 2,
                 'label': 'STRONG BUY (high conviction)'},
    'STANDARD': {'min_conviction': 7, 'max_conviction': 7,  'equity_pct': 0.15, 'max_slots': 3,
                 'label': 'STRONG BUY (standard)'},
    'SPEC':     {'min_conviction': 4, 'max_conviction': 6,  'equity_pct': 0.08, 'max_slots': 2,
                 'label': 'SPEC BUY'},
}

# QUALITY_TIERS, SIZING_GEARS imported from scanner.sterling_indicators above
DEFAULT_SIZING_GEAR = 'recommended'

# Portfolio tracking
DEFAULT_POSITION_SHARES = 100  # Assumed shares per position for notional P&L
MAX_PORTFOLIO_BACKUPS = 30     # Keep last N portfolio backups
PORTFOLIO_PRICE_STALENESS_HOURS = 8       # Re-fetch prices if older than this
PORTFOLIO_SNAPSHOT_CLOSED_TRADES_LIMIT = 20  # Max closed trades in snapshot

# ═══════════════════════════════════════════════════════════════════════════════
# COMPOUNDING PORTFOLIO SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

STARTING_CAPITAL_PER_POSITION = 5000.0  # £5,000 per position
CURRENCY_SYMBOL = "£"
# EQUITY_CURVE_FILE imported from config.output_paths (full Path to portfolio/output/equity_curve.csv)

# Universe size (for funnel graphic default)
DEFAULT_UNIVERSE_SIZE = 1817   # Approximate total ticker count


# ═══════════════════════════════════════════════════════════════════════════════
# LLM MODELS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_SONNET = "claude-sonnet-4-20250514"   # Cost-effective for most tasks
MODEL_OPUS = "claude-opus-4-5-20251101"     # Deep analysis (DD, complex tasks)

# Default model for each component
MODEL_THEMATIC = MODEL_SONNET
MODEL_TWEET = MODEL_SONNET
MODEL_NEWSLETTER = MODEL_SONNET
MODEL_MARKET = MODEL_SONNET
MODEL_NOTES = MODEL_SONNET       # Substack Notes generation

# Sterling Grid LLM gates
MODEL_INVESTMENT_GATE = MODEL_SONNET   # Investment Gate (replaces Gatekeeper + DD Automator)
MODEL_DEEP_DD = MODEL_OPUS             # Deep DD (Opus + extended thinking, 1-3 stocks only)
DEEP_DD_THINKING_BUDGET = 10000        # Max tokens for extended thinking in Deep DD

# Legacy model aliases — removed in Sterling Grid upgrade (Feb 2026)
# If you see import errors for MODEL_GATEKEEPER or MODEL_DD_QUICK,
# use MODEL_INVESTMENT_GATE or MODEL_DEEP_DD instead.


# ═══════════════════════════════════════════════════════════════════════════════
# LLM API SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RETRIES = 5                   # Max retry attempts on failure
RATE_LIMIT_COOLDOWN = 60.0        # Seconds to wait on rate limit
INTER_STEP_DELAY = 30.0           # Delay between major pipeline steps
INTER_STOCK_DELAY = 8.0           # Delay between per-stock LLM calls
BACKOFF_FACTOR = 2.0              # Exponential backoff multiplier
BACKOFF_MAX_WAIT = 300.0          # Maximum wait time for backoff (5 min)

# Token limits by model
MAX_TOKENS = {
    MODEL_SONNET: 8192,
    MODEL_OPUS: 8192,
}

# Cost per 1M tokens (USD)
COST_INPUT_PER_M = {
    MODEL_SONNET: 3.00,
    MODEL_OPUS: 15.00,
}
COST_OUTPUT_PER_M = {
    MODEL_SONNET: 15.00,
    MODEL_OPUS: 75.00,
}
COST_WEB_SEARCH = 0.01  # Per search


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-ACCOUNT X/TWITTER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TWITTER_ACCOUNTS: Dict[str, Dict] = {
    'main': {
        'env_prefix': 'X1',
        'offset_minutes': 0,
        'variation_style': 'original',
    },
    'account2': {
        'env_prefix': 'X2',
        'offset_minutes': 10,
        'variation_style': 'conversational',
    },
    'account3': {
        'env_prefix': 'X3',
        'offset_minutes': 20,
        'variation_style': 'data_driven',
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT PERSONAS - Voice/tone definitions for multi-account content
# ═══════════════════════════════════════════════════════════════════════════════

PERSONAS: Dict[str, Dict] = {
    'main': {
        'name': 'The System',
        'archetype': 'Analyst',
        'voice': {
            'tone': 'authoritative',
            'formality': 'professional',
            'traits': ['data-driven', 'precise', 'confident'],
        },
        'focus': ['scanner_results', 'signal_announcements', 'system_performance'],
        'signature_phrases': [
            "The scanner doesn't lie.",
            "Data drives decisions.",
            "That's the system in action.",
            "Precision matters. Always.",
        ],
    },
    'account2': {
        'name': 'The Mentor',
        'archetype': 'Teacher',
        'voice': {
            'tone': 'conversational',
            'formality': 'approachable',
            'traits': ['helpful', 'patient', 'encouraging'],
        },
        'focus': ['educational', 'process_explanation', 'trading_psychology'],
        'signature_phrases': [
            "Here's why this matters...",
            "Let me break this down.",
            "The lesson here:",
            "Most traders miss this.",
        ],
    },
    'account3': {
        'name': 'The Trader',
        'archetype': 'Practitioner',
        'voice': {
            'tone': 'direct',
            'formality': 'casual',
            'traits': ['action-oriented', 'confident', 'punchy'],
        },
        'focus': ['real_time_market_color', 'power_hour', 'theme_momentum'],
        'signature_phrases': [
            "Eyes on this one.",
            "The close matters.",
            "Momentum is real.",
            "Let's see how this plays out.",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA CATEGORY AFFINITY — Controls which categories each persona prefers
# Each persona has primary (strongest), secondary, and avoids (never assigned).
# Used by _prepare_slot_data() to route the decision category to the best persona
# and assign different categories to the remaining personas.
# ═══════════════════════════════════════════════════════════════════════════════

PERSONA_AFFINITY: Dict[str, Dict] = {
    "variant_1": {  # Alex — The System (Analyst)
        "primary": {"SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"},
        "secondary": {"THEME_CATALYST", "MARKET_COMMENTARY"},
        "avoids": {"ENGAGEMENT", "EDUCATIONAL"},
    },
    "variant_2": {  # Rozalia — The Mentor (Teacher)
        "primary": {"EDUCATIONAL", "THEME_LIST", "SUBSTACK_TEASER", "THEME_CATALYST"},
        "secondary": {"MARKET_COMMENTARY", "RECEIPT"},
        "avoids": {"SELL_SIGNAL"},
    },
    "variant_3": {  # James — The Trader (Practitioner)
        "primary": {"MARKET_COMMENTARY", "TRENDING_TAKE", "RECEIPT", "ENGAGEMENT"},
        "secondary": {"TECHNICAL_ANALYSIS", "THEME_CATALYST"},
        "avoids": {"EDUCATIONAL"},
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DAY-AWARE CONTENT RULES
# ═══════════════════════════════════════════════════════════════════════════════

DAY_CONTENT_RULES: Dict[str, Dict] = {
    'Saturday': {
        'context': 'Newsletter dropped, weekend recap',
        'allowed_phrases': ['Friday close', 'This week', 'Weekend', 'Saturday morning'],
        'blocked_phrases': ['Today', 'Right now', 'Power hour', 'Into the close'],
        'time_reference': "Friday's close",
    },
    'Sunday': {
        'context': 'Prep for week ahead',
        'allowed_phrases': ['This week', 'Looking ahead', 'Weekend', 'Next week'],
        'blocked_phrases': ['Today', 'Power hour', 'Into the close'],
        'time_reference': "Friday's close",
    },
    'Monday': {
        'context': 'Week kickoff',
        'allowed_phrases': ['This week', 'Based on Friday', 'New week'],
        'blocked_phrases': ['Weekend homework', 'Saturday'],
        'time_reference': "Friday's close",
    },
    'Tuesday': {
        'context': 'Mid-early week',
        'allowed_phrases': ['This week', 'Early movers', 'Building'],
        'blocked_phrases': ['Weekend', 'Friday close', 'Saturday'],
        'time_reference': "the weekly scan",
    },
    'Wednesday': {
        'context': 'Mid-week check-in',
        'allowed_phrases': ['Mid-week', 'This week', 'Halfway'],
        'blocked_phrases': ['Weekend', 'Friday close', 'Saturday'],
        'time_reference': "the weekly scan",
    },
    'Thursday': {
        'context': 'Building to Friday scan',
        'allowed_phrases': ['Tomorrow', 'Friday scan', 'Almost Friday'],
        'blocked_phrases': ['Weekend homework', 'Last Friday', 'Saturday'],
        'time_reference': "tomorrow's scan",
    },
    'Friday': {
        'context': 'Scan day',
        'allowed_phrases': ['Today', "Today's close", 'Power hour', 'Scanner running', 'Fresh scan'],
        'blocked_phrases': ['Last week', 'Weekend homework', 'Next Friday'],
        'time_reference': "today's close",
    },
}


def get_day_context(day: str) -> Dict:
    """Get content rules for a specific day."""
    return DAY_CONTENT_RULES.get(day, DAY_CONTENT_RULES['Saturday'])


def get_persona(account_id: str) -> Dict:
    """Get persona definition for an account."""
    return PERSONAS.get(account_id, PERSONAS['main'])


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET SCHEDULING (Eastern Time)
# ═══════════════════════════════════════════════════════════════════════════════

SLOTS: Dict[int, str] = {
    1: "pre_market",     # 08:00 ET - Pre-market / Beat SPY hooks
    2: "morning",        # 10:00 ET - 30min after market open
    3: "midday",         # 12:30 ET - Lunch break engagement
    4: "power_hour",     # 15:30 ET - CRITICAL: Power Hour reaction
    5: "after_hours"     # 18:00 ET - After-hours / engagement
}

SLOT_TIMES_ET: Dict[int, str] = {
    1: "08:00",
    2: "10:00",
    3: "12:30",
    4: "15:30",
    5: "18:00"
}

def get_slot_times_utc() -> Dict[int, str]:
    """Convert ET slot times to UTC, accounting for EST/EDT automatically.

    Uses ZoneInfo to determine current UTC offset for America/New_York.
    EST (Nov-Mar): UTC-5  |  EDT (Mar-Nov): UTC-4
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    et_tz = ZoneInfo("America/New_York")
    now_et = datetime.now(et_tz)
    utc_offset_hours = now_et.utcoffset().total_seconds() / 3600  # -5 or -4

    result = {}
    for slot, et_time in SLOT_TIMES_ET.items():
        hour, minute = map(int, et_time.split(":"))
        utc_hour = int(hour - utc_offset_hours) % 24
        result[slot] = f"{utc_hour:02d}:{minute:02d}"
    return result


# Slot timing in UTC — dynamically computed from ET times + current timezone
SLOT_TIMES_UTC: Dict[int, str] = get_slot_times_utc()


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

TWEETS_PER_DAY = 5
TWEETS_PER_WEEK = 35  # 5 slots × 7 days

# Content types for tweets
# NOTE: roth_ira, pdt_friendly, position_update are KILLED - see KILLED_CATEGORIES
CONTENT_TYPES: List[str] = [
    # Signal categories
    "buy_signal",
    "thread_buy_signal",
    "consider_spotlight",
    # Theme categories
    "theme_hot",
    "theme_cold",
    "sector_rotation",
    # Performance categories (safeguarded - winners only)
    "top_performers",      # Replaced weekly_wins
    "early_movers",        # New signals showing strength
    "milestone_alerts",    # Celebrations at 25%, 50%, 100%
    "recent_wins",         # Closed winning trades
    "beat_spy",            # Portfolio vs SPY comparison
    # Content categories
    "educational",
    "engagement",
    "power_hour",
    "funnel_graphic",
    # Rarely used
    "closed_trade",
    "sell_signal",
    "system_promo",
    "market_insight",
    "post_mortem",
    "win_card",
    "alpha_card",
]


# ═══════════════════════════════════════════════════════════════════════════════
# THEME SCORING
# ═══════════════════════════════════════════════════════════════════════════════

THEME_SCORE_PRIME = 7.5         # >= for PRIME classification
THEME_SCORE_INVESTABLE = 6.0    # >= for INVESTABLE
THEME_SCORE_SELECTIVE = 4.5     # >= for SELECTIVE
# Below 4.5 = AVOID

THEME_WEIGHTS: Dict[str, float] = {
    "catalyst": 0.40,    # Upcoming catalysts (40% weight)
    "momentum": 0.25,    # Price/flow momentum (25% weight)
    "crowding": 0.20,    # Positioning/crowding (20% weight)
    "runway": 0.15       # Future potential (15% weight)
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

YFINANCE_PERIOD = "1y"        # Data period for beta calculation
YFINANCE_INTERVAL = "1d"      # Data interval
MIN_TRADING_DAYS = 60         # Minimum data points for valid beta


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

CARD_WIDTH = 1200             # Twitter card width
CARD_HEIGHT = 675             # Twitter card height
CARD_BG_COLOR = "#1a1a2e"     # Dark theme background
CARD_TEXT_COLOR = "#ffffff"   # White text
CARD_ACCENT_GREEN = "#00ff88" # Win/bullish accent
CARD_ACCENT_RED = "#ff4444"   # Loss/bearish accent


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING SAFEGUARDS & THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

# Performance thresholds for content generation
MARKETING_THRESHOLDS: Dict[str, float] = {
    # Win Highlighting
    'big_win_threshold': 25.0,           # Trigger standalone self_quote tweet
    'home_run_threshold': 50.0,          # Celebration post, pin candidate
    'hall_of_fame_threshold': 100.0,     # Thread-worthy, reference repeatedly

    # SPY Comparison
    'spy_outperformance_min': 5.0,       # Must beat SPY by this % to use beat_spy content

    # Content Generation (Phase 9: Renamed for clarity)
    'min_winners_for_top_performers': 2, # Need at least 2 winners to post top_performers

    # Loss Filtering (CRITICAL - never expose losses publicly)
    'max_loss_to_mention': -5.0,         # Never mention positions worse than this

    # Cold Streak Circuit Breaker
    'cold_streak_threshold': 3,          # Number of consecutive losses to trigger
    'cold_streak_lookback_days': 14,     # Days to look back for recent losses

    # Ticker Mention Limits (prevent engagement fatigue)
    'max_ticker_mentions_per_week': 4,   # Max times same ticker can appear in weekly content
}

# Newsletter configuration
NEWSLETTER_URL = os.environ.get(
    "NEWSLETTER_URL", "https://sterlingsignals.substack.com"
)

# Signal classifications for content
SIGNAL_CLASSIFICATIONS: Dict[str, str] = {
    'PASS': 'Cleared all 5 gates - full GREEN recommendation',
    'CONSIDER': 'Cleared gates 1-4, watching for gate 5',
    'WATCHLIST': 'Strong technical setup, theme alignment pending',
    'CAUTION': 'Open position showing weakness',
    'EXIT': 'Stop triggered or thesis broken',
}

# Categories that require safeguard checks before generation
# Phase 9: Renamed weekly_wins -> top_performers for accurate terminology
SAFEGUARDED_CATEGORIES: Dict[str, str] = {
    'top_performers': 'has_enough_wins',   # Must have 2+ winners above 15%
    'beat_spy': 'should_post_beat_spy',    # Must outperform SPY by 5%+
    'self_quote': 'has_uncelebrated_wins', # Must have big wins not yet celebrated
    'closed_trade': 'has_winning_closed_trades',  # GAP 36 fix: Must have at least 1 winning closed trade
}

# Fallback categories when safeguards fail
# Phase 9: Renamed weekly_wins -> top_performers for accurate terminology
CATEGORY_FALLBACKS: Dict[str, str] = {
    'top_performers': 'theme_hot',
    'beat_spy': 'engagement',
    'self_quote': 'consider_spotlight',
    'closed_trade': 'educational',  # GAP 36 fix: Fallback when no winning closed trades
}

# Celebration thresholds for self_quote tweets
CELEBRATION_THRESHOLDS: List[float] = [25.0, 50.0, 100.0]

# Keys for celebration tracking in celebrations.json
CELEBRATION_KEYS: Dict[float, str] = {
    25.0: '25_pct_celebrated',
    50.0: '50_pct_celebrated',
    100.0: '100_pct_celebrated',
}

# Signal branding (public-facing)
SIGNAL_BRAND = "GREEN signal"  # Instead of "PASS signal"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: SIGNAL_TYPES - Full nested structure from MASTER_TODO
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_TYPES: Dict[str, Dict] = {
    # ── Sterling Grid verdicts (Investment Gate) ──
    'STRONG_BUY': {
        'description': 'Investment Gate STRONG BUY — full conviction entry',
        'public_name': 'GREEN Signal',
        'show_publicly': True,
    },
    'SPEC_BUY': {
        'description': 'Investment Gate SPEC BUY — speculative entry',
        'public_name': 'GREEN Signal',
        'show_publicly': True,
    },
    'NO_GO': {
        'description': 'Investment Gate NO GO — do not enter',
        'public_name': None,
        'show_publicly': False,
    },
    # ── Legacy verdicts (backward compat with existing portfolio) ──
    'PASS': {
        'description': 'Cleared all 5 gates - full GREEN signal (legacy)',
        'public_name': 'GREEN Signal',
        'gates_required': [1, 2, 3, 4, 5],
        'show_publicly': True,
    },
    'CONSIDER': {
        'description': 'Cleared gates 1-4, watching for gate 5 (legacy)',
        'public_name': 'On Our Radar',
        'gates_required': [1, 2, 3, 4],
        'show_publicly': True,
    },
    'WATCHLIST': {
        'description': 'Strong technicals, theme alignment pending',
        'public_name': None,
        'gates_required': [1, 2, 3],
        'show_publicly': False,
    },
    'CAUTION': {
        'description': 'Open position showing weakness',
        'public_name': None,
        'gates_required': None,
        'show_publicly': False,
    },
    'EXIT': {
        'description': 'Stop triggered or thesis broken',
        'public_name': None,
        'gates_required': None,
        'show_publicly': False,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: BANNED_TERMS — Re-exported from config/banned_terms.py (canonical)
# ═══════════════════════════════════════════════════════════════════════════════

from config.banned_terms import ALL_BANNED as BANNED_TERMS  # noqa: F811


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVED PUBLIC TERMS (Marketing Vocabulary) - MASTER_TODO_v2
# ═══════════════════════════════════════════════════════════════════════════════

APPROVED_TERMS: Dict[str, List[str]] = {
    'signals': [
        'GREEN signal',
        'GREEN signal fires',
        'triggers a GREEN signal',
        'cleared all 5 gates',
    ],
    'system': [
        '5-Gate System',
        'our scanner',
        'systematic approach',
    ],
    'gates': [
        'Structural Pivot Confirmation',
        'Institutional Accumulation Divergence',
        'Sector Flow Analysis',
        # Don't publicly name all gates
    ],
    'risk': [
        'trailing stop',
        'systematic stop',
        'risk management',
        'defined risk',
    ],
}


def enforce_green_branding(text: str) -> str:
    """Replace non-branded signal terms with GREEN branding.

    All signal references MUST use 'GREEN signal'.

    Args:
        text: Text to process

    Returns:
        Text with GREEN branding applied
    """
    replacements = {
        'TEAL signal': 'GREEN signal',
        'TEAL SIGNAL': 'GREEN SIGNAL',
        'PASS signal': 'GREEN signal',
        'proprietary entry': 'GREEN signal',
        'proprietary signal': 'GREEN signal',
        'passes our criteria': 'triggers a GREEN signal',
        'cleared our system': 'triggers a GREEN signal',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def check_ticker_frequency(ticker: str, existing_tweets: list) -> bool:
    """Check if ticker can be mentioned again this week.

    Args:
        ticker: Ticker symbol to check
        existing_tweets: List of tweets already in queue

    Returns:
        True if ticker can be mentioned, False if at limit
    """
    mentions = sum(1 for t in existing_tweets if ticker.upper() in t.get('text', '').upper())
    return mentions < TICKER_LIMITS['max_mentions_per_week']


def validate_not_killed_category(category: str) -> bool:
    """Validate category is not in KILLED_CATEGORIES.

    Args:
        category: Category name to check

    Returns:
        True if category is allowed

    Raises:
        ValueError: If category is killed
    """
    if category in KILLED_CATEGORIES:
        raise ValueError(f"Category '{category}' has been killed. Do not use. See KILLED_CATEGORIES.")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: IMAGE_PATTERNS - Standardized filename patterns
# ═══════════════════════════════════════════════════════════════════════════════

IMAGE_PATTERNS: Dict[str, str] = {
    'top_performers': 'top_performers_{date}.png',
    'beat_spy': 'beat_spy_{date}.png',
    'funnel': 'funnel_{date}.png',
    'theme_card': 'theme_{theme}_{date}.png',
    'milestone': 'milestone_{ticker}_{date}.png',
    'consider': 'consider_{date}.png',
    'chart': '{ticker}_{date}.png',
    'early_movers': 'early_movers_{date}.png',
    'sector_rotation': 'sector_rotation_{date}.png',
    'portfolio_dashboard': 'portfolio_dashboard_{date}.png',  # Internal only
}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: WEEKLY_SCHEDULE - Day-by-day content schedule
# ═══════════════════════════════════════════════════════════════════════════════

WEEKLY_SCHEDULE: Dict[str, List[tuple]] = {
    'Saturday': [
        (1, 'top_performers'),     # Safeguarded
        (2, 'thread_buy_signal'),  # Deep dive on top GREEN signal
        (3, 'theme_hot'),
        (4, 'funnel_graphic'),
        (5, 'engagement'),
    ],
    'Sunday': [
        (1, 'buy_signal'),         # All GREEN signals
        (2, 'consider_spotlight'), # On Our Radar stocks
        (3, 'beat_spy'),           # Safeguarded
        (4, 'theme_hot'),
        (5, 'engagement'),
    ],
    'Monday': [
        (1, 'theme_hot'),
        (2, 'milestone_alerts'),   # Safeguarded - celebration posts
        (3, 'educational'),
        (4, 'power_hour'),         # CRITICAL - market reaction
        (5, 'engagement'),
    ],
    'Tuesday': [
        (1, 'early_movers'),       # New signals showing strength
        (2, 'theme_hot'),
        (3, 'educational'),
        (4, 'power_hour'),
        (5, 'engagement'),
    ],
    'Wednesday': [
        (1, 'consider_spotlight'),
        (2, 'milestone_alerts'),   # Safeguarded
        (3, 'sector_rotation'),
        (4, 'power_hour'),
        (5, 'engagement'),
    ],
    'Thursday': [
        (1, 'theme_hot'),
        (2, 'buy_signal'),
        (3, 'educational'),
        (4, 'power_hour'),
        (5, 'engagement'),
    ],
    'Friday': [
        (1, 'recent_wins'),        # Closed winners
        (2, 'theme_hot'),
        (3, 'sector_rotation'),
        (4, 'power_hour'),
        (5, 'engagement'),
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# BRANDING - Public-facing identity
# ═══════════════════════════════════════════════════════════════════════════════

BRANDING: Dict[str, str] = {
    'signal_name': 'GREEN signal',
    'signal_tagline': 'GREEN means go.',
    'system_name': '5-Gate System',
    'buy_color': 'GREEN',
    'sell_color': 'RED',
    'substack_url': 'https://sterlingsignals.substack.com',
    'twitter_handle': '@AlexSterlingGBR',
}


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL COLOR SYSTEM (Marketing Upgrade)
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_COLORS: Dict[str, Dict] = {
    'GREEN': {
        'emoji': '🟢',
        'meaning': 'BUY',
        'internal_status': 'PASS',
        'public_name': 'GREEN Signal',
    },
    'RED': {
        'emoji': '🔴',
        'meaning': 'EXIT',
        'internal_status': 'STOPPED',
        'public_name': 'Exit Alert',
    },
    'CONSIDER': {
        'emoji': '🟡',
        'meaning': 'WATCH',
        'internal_status': 'CONSIDER',
        'public_name': 'On Our Radar',
    },
}

CONVICTION_LANGUAGE: Dict[int, str] = {
    10: 'Extremely Bullish',
    9: 'Extremely Bullish',
    8: 'Extremely Bullish',
    7: 'Bullish',
    6: 'Watching',
    5: 'Watching',
    4: 'Watching',
    3: None,   # Do not post publicly
    2: None,   # Do not post publicly
    1: None,   # Do not post publicly
    # Legacy 1-5 backward compatibility (existing portfolio entries)
}

ENTRY_PRICE_RULES: Dict[str, any] = {
    'show_for_closed_winners': True,
    'show_for_open_above_threshold': True,
    'threshold_pct': 25.0,
}

SUBSTACK_CONTENT: Dict[str, Dict] = {
    'monday': {
        'type': 'market_analysis',
        'title_format': 'Market Outlook: Week of {date}',
        'filename': 'monday_market_analysis.html',
    },
    'thursday': {
        'type': 'theme_spotlight',
        'title_format': 'Theme Watch: {theme_name}',
        'filename': 'thursday_theme_spotlight.html',
    },
    'saturday': {
        'type': 'weekly_signals',
        'title_format': 'GREEN Signals: {date}',
        'filename': 'saturday_weekly_signals.html',
    },
    'sunday': {
        'type': 'deep_dive',
        'title_format': 'Deep Dive: ${ticker}',
        'filename': 'sunday_deep_dive.html',
    },
}


def get_signal_emoji(signal_type: str) -> str:
    """Get emoji for signal type (GREEN, RED, CONSIDER).

    Args:
        signal_type: The signal type key (GREEN, RED, CONSIDER)

    Returns:
        Emoji string for the signal type, empty string if not found
    """
    return SIGNAL_COLORS.get(signal_type, {}).get('emoji', '')


def get_conviction_text(score: int) -> str:
    """Convert conviction score to public-facing language.

    Supports both new 1-10 scale and legacy 1-5 scale.

    Args:
        score: Conviction score (1-10 new scale, 1-5 legacy)

    Returns:
        Public-facing text ('Extremely Bullish', 'Bullish', 'Watching', etc.)
        Returns 'Watching' as default for invalid scores.
        Returns None for scores that should not be posted publicly (1-3).
    """
    return CONVICTION_LANGUAGE.get(score, 'Watching')


def can_show_entry_price(position: dict) -> bool:
    """Check if entry price can be shown publicly for a position.

    Portfolio transparency: always show entry prices for all positions.
    Full transparency builds trust — show winners AND losers.

    Args:
        position: Position dict (kept for backward compatibility)

    Returns:
        Always True — full portfolio transparency
    """
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# CELEBRATION_TIERS - Milestone celebration definitions
# ═══════════════════════════════════════════════════════════════════════════════

CELEBRATION_TIERS: Dict[str, Dict] = {
    'standard': {
        'threshold': 25.0,
        'template': 'milestone_standard',
        'emoji': '📈',
        'headline': 'MILESTONE ALERT',
    },
    'home_run': {
        'threshold': 50.0,
        'template': 'milestone_home_run',
        'emoji': '🚀',
        'headline': 'HOME RUN',
    },
    'hall_of_fame': {
        'threshold': 100.0,
        'template': 'milestone_hall_of_fame',
        'emoji': '🏆',
        'headline': 'HALL OF FAME',
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: TIMEFRAME-AWARE WIN CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

# Win category definitions - replaces misleading "weekly_wins" terminology
WIN_CATEGORIES: Dict[str, Dict] = {
    'top_performers': {
        'description': 'Best open positions by TOTAL return since signal entry',
        'threshold': 15.0,
        'min_positions': 2,
        'public_name': 'Top Performers',
        'tweet_frequency': 'weekly',
    },
    'early_movers': {
        'description': 'NEW signals (< 2 weeks old) showing early strength',
        'max_age_days': 14,
        'threshold': 5.0,
        'public_name': 'Early Momentum',
        'tweet_frequency': 'when_available',
    },
    'milestone_alerts': {
        'description': 'Positions crossing key thresholds (25%, 50%, 100%)',
        'thresholds': [25, 50, 100],
        'public_name': 'Milestone Alert',
        'tweet_frequency': 'when_crossed',
    },
    'recent_wins': {
        'description': 'Positions CLOSED in profit within last 14 days',
        'threshold': 15.0,
        'lookback_days': 14,
        'public_name': 'Recent Wins',
        'tweet_frequency': 'when_available',
    },
}

# Timeframe disclaimers for different contexts
TIMEFRAME_DISCLAIMERS: Dict[str, str] = {
    'short': 'Returns since signal entry.',
    'medium': 'Total gain since entry, not weekly movement.',
    'long': 'Sterling Signals targets 50-100% returns over 3-8 month holds. Returns shown are total since signal entry.',
}

# CRIT-3: Stopped Position Rules - NEVER show stopped positions publicly
STOPPED_POSITION_RULES: Dict[str, bool] = {
    'show_in_public_content': False,
    'show_in_newsletter': False,
    'show_in_top_performers': False,
    'show_in_any_tweet': False,
    'internal_tracking': True,  # Continue tracking for metrics
    'mention_discipline_publicly': False,  # Don't mention "system working" with losses
}

# CRIT-4: SPY Comparison Method - Always use matched holding periods
SPY_COMPARISON_METHOD = 'matched_period'  # Options: 'matched_period', '30_day', 'ytd'


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETING HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_marketing_threshold(key: str, default: float = 0.0) -> float:
    """Get a marketing threshold value by key with fallback default."""
    return MARKETING_THRESHOLDS.get(key, default)


def get_fallback_category(category: str) -> str:
    """Get the fallback category when safeguards fail."""
    return CATEGORY_FALLBACKS.get(category, 'engagement')


def is_safeguarded_category(category: str) -> bool:
    """Check if a category requires safeguard validation."""
    return category in SAFEGUARDED_CATEGORIES


def get_celebration_key(pnl_pct: float) -> str:
    """Get the celebration key for a given P&L percentage."""
    for threshold in sorted(CELEBRATION_THRESHOLDS, reverse=True):
        if pnl_pct >= threshold:
            return CELEBRATION_KEYS[threshold]
    return None


def get_highest_uncelebrated_threshold(pnl_pct: float, celebrated: dict) -> float:
    """Get the highest threshold that hasn't been celebrated yet."""
    for threshold in sorted(CELEBRATION_THRESHOLDS, reverse=True):
        if pnl_pct >= threshold:
            key = CELEBRATION_KEYS[threshold]
            if not celebrated.get(key):
                return threshold
    return None


def get_highlight_threshold(days_held: int) -> float:
    """Return age-based threshold for position highlighting.

    Younger positions need lower returns to be highlighted (just need to be green).
    Mature positions need stronger returns to be worth mentioning.

    Args:
        days_held: Number of days the position has been held

    Returns:
        Minimum P&L percentage required for highlighting
    """
    if days_held <= 7:
        return 3.0    # New positions: just need to be green
    elif days_held <= 14:
        return 5.0    # Early momentum: showing promise
    elif days_held <= 30:
        return 10.0   # Building position: solid start
    elif days_held <= 60:
        return 15.0   # Standard threshold
    else:
        return 20.0   # Mature positions: need stronger returns


def format_holding_period(days_held: int) -> str:
    """Format days held into human-readable period.

    Args:
        days_held: Number of days the position has been held

    Returns:
        Formatted string like '3 days', '2 weeks', '3 months'
    """
    if days_held <= 0:
        return "held"
    elif days_held <= 7:
        return f"{days_held} days"
    elif days_held <= 30:
        weeks = days_held // 7
        return f"{weeks} week{'s' if weeks > 1 else ''}"
    else:
        months = days_held // 30
        return f"{months} month{'s' if months > 1 else ''}"


def get_position_age_category(entry_date: str) -> str:
    """Categorize position by age for appropriate handling.

    Args:
        entry_date: Entry date string in 'YYYY-MM-DD' format

    Returns:
        'early' for new positions (<14 days)
        'developing' for maturing positions (14-60 days)
        'mature' for established positions (>60 days)
    """
    from datetime import datetime

    try:
        days_held = (datetime.now() - datetime.strptime(entry_date, '%Y-%m-%d')).days
    except (ValueError, TypeError):
        # Default to developing if date parsing fails
        return 'developing'

    if days_held <= 14:
        return 'early'      # For early_movers category
    elif days_held <= 60:
        return 'developing' # Standard handling
    else:
        return 'mature'     # Should be performing


def contains_banned_term(text: str) -> bool:
    """Check if text contains any banned terms.

    Uses word-boundary matching for short terms to avoid false positives
    (e.g. 'BoS' in 'Bostonian').

    Args:
        text: Text to check

    Returns:
        True if any banned term is found
    """
    text_lower = text.lower()
    short_terms = {'RSI', 'MACD', 'KDJ', 'BoS', 'BOS', 'GMT', 'BST',
                   'HMA', 'PDT', 'TEAL', 'teal', 'AMBER', 'amber'}
    for term in BANNED_TERMS:
        if term.lower() in text_lower:
            if term in short_terms:
                if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                    return True
            else:
                return True
    return False


def get_image_filename(pattern_key: str, **kwargs) -> str:
    """Generate standardized image filename from pattern.

    Args:
        pattern_key: Key from IMAGE_PATTERNS dict
        **kwargs: Format values (date, ticker, theme, etc.)

    Returns:
        Formatted filename string
    """
    pattern = IMAGE_PATTERNS.get(pattern_key)
    if not pattern:
        return f"unknown_{kwargs.get('date', 'unknown')}.png"
    return pattern.format(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# TICKER ALIASES (Historical ticker name changes)
# ═══════════════════════════════════════════════════════════════════════════════

# Map old ticker names to current names
TICKER_ALIASES: Dict[str, str] = {
    # Social Media / Tech
    'FB': 'META',       # Facebook -> Meta (Oct 2021)
    'TWTR': 'X',        # Twitter -> X (Jul 2023)

    # Mergers / Spinoffs
    'GOOGL': 'GOOG',    # Both valid but standardize
    'BRK.A': 'BRK-A',   # Berkshire Hathaway format
    'BRK.B': 'BRK-B',

    # Add more as discovered
}


def normalize_ticker(ticker: str) -> str:
    """Normalize a ticker symbol, handling historical name changes.

    Args:
        ticker: The ticker symbol to normalize

    Returns:
        The current/canonical ticker name
    """
    if not ticker:
        return ticker
    upper_ticker = ticker.upper().strip()
    return TICKER_ALIASES.get(upper_ticker, upper_ticker)


def get_ticker_history(ticker: str) -> List[str]:
    """Get all known historical names for a ticker.

    Args:
        ticker: Current or historical ticker name

    Returns:
        List of all known names (current + historical)
    """
    ticker = ticker.upper().strip()
    names = [ticker]

    # Check if this is a current name with old aliases
    old_names = [k for k, v in TICKER_ALIASES.items() if v == ticker]
    names.extend(old_names)

    # Check if this is an old name
    if ticker in TICKER_ALIASES:
        current = TICKER_ALIASES[ticker]
        if current not in names:
            names.append(current)

    return names


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TWEET SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# xAI / Grok models
MODEL_CONTEXT = "grok-4-fast-non-reasoning"
MODEL_LIVE_TWEET = "claude-sonnet-4-5-20250929"
XAI_BASE_URL = "https://api.x.ai/v1"

# Cost controls
DAILY_COST_LIMIT_USD = 1.00               # Hard limit — kills generation if exceeded
MONTHLY_COST_LIMIT_USD = 30.00            # Alert threshold
COST_LOG_FILE = LIVE_COST_LOG_FILE  # Alias for backward compat

# Content controls
MAX_TWEETS_PER_DAY = 12                   # Hard cap across all accounts
MAX_SAME_TICKER_PER_DAY = 3              # Max tweets about same ticker per day
CONTEXT_STALENESS_HOURS = 4              # Stale threshold for MARKET_COMMENTARY
WEEKEND_CONTEXT_STALENESS_HOURS = 24     # Relaxed threshold on weekends (markets closed)
MIN_HOURS_BETWEEN_SAME_TICKER = 3        # Min gap between same-ticker tweets

# Diversity controls (ported from batch system — prevents repetitive tweets)
CATEGORY_WEEKLY_TARGETS: Dict[str, int] = {
    "RECEIPT": 5,              # ~9% — reduced from 7, quality over frequency
    "MARKET_COMMENTARY": 7,    # 16% — any-mood market context (was MARKET_REACTION)
    "SIGNAL_ALERT": 7,         # 16% — now includes CONSIDER sub-type
    "TRENDING_TAKE": 5,        # 11% — new: FinTwit overlap content
    "THEME_CATALYST": 5,       # 11% — renamed from THEME_MOMENTUM
    "ENGAGEMENT": 5,           # 11%
    "TECHNICAL_ANALYSIS": 5,   # 11%
    "SUBSTACK_TEASER": 7,      # 16% — 1+ per post day (5 post days Tue–Sat)
    "THEME_LIST": 3,           # 7% — new: thread-only format
    "EDUCATIONAL": 4,          # ~8% — increased from 3, grounded in real examples
    "SELL_SIGNAL": 3,          # 7% — exit signals
}
MAX_SAME_CATEGORY_PER_DAY = 3            # No more than 3 of same category per day
QUEUE_DEDUP_HOURS = 48                   # Similarity window for dedup
QUEUE_DEDUP_THRESHOLD = 0.80             # Max similarity ratio to recent tweets
OPENING_DEDUP_THRESHOLD = 0.70           # Max similarity for opening sentences
MAX_OPENING_HISTORY = 10                 # Track last N openings for dedup

# Chart-img.com integration (REST API — CI-compatible, no browser needed)
CHARTIMG_API_URL = "https://api.chart-img.com/v1/tradingview/advanced-chart"
CHART_IMG_WIDTH = 1200                    # pixels (Chart-IMG Pro tier, 16:9 for X/Twitter)
CHART_IMG_HEIGHT = 675                    # pixels
CHART_IMG_INTERVAL = "1W"                 # Default weekly

# LIVE_QUEUE_FILE imported from config.output_paths

# Weekend behavior
WEEKEND_MAX_TWEETS = 4
WEEKEND_CATEGORIES: List[str] = [
    "EDUCATIONAL", "ENGAGEMENT", "RECEIPT", "SIGNAL_ALERT",
    "SUBSTACK_TEASER", "THEME_LIST",
]

# Exchange mapping for chart-img.com (ticker → exchange prefix)
EXCHANGE_MAP: Dict[str, str] = {
    # Original
    "WCC": "NYSE", "STRL": "NASDAQ", "MOD": "NYSE",
    "MATV": "NASDAQ", "LUMN": "NYSE", "FIX": "NYSE",
    "RCAT": "NASDAQ", "IBKR": "NASDAQ", "CGON": "NASDAQ",
    "TLN": "NYSE", "VNET": "NASDAQ",
    # Portfolio additions
    "IESC": "NYSE", "AAON": "NASDAQ", "AMSC": "NASDAQ",
    "AMPX": "NYSE", "APLD": "NASDAQ", "ASPI": "NASDAQ",
    "BITF": "NASDAQ", "SOFI": "NASDAQ", "HIVE": "NASDAQ",
    "EVTL": "NYSE", "NVDA": "NASDAQ", "AMD": "NASDAQ",
}

# Centralized API pricing (per million tokens)
API_PRICING: Dict[str, Dict[str, float]] = {
    "grok-3-fast": {"input": 0.20, "output": 0.50},
    "grok-4-fast-non-reasoning": {"input": 0.20, "output": 0.50},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}
TOOL_CALL_COST = 0.005  # Per search/tool call


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """Print current configuration values."""
    print("Configuration Values")
    print("=" * 60)
    print(f"\nTrading Parameters:")
    print(f"  Trailing Stop:   {TRAILING_STOP_PCT}%")
    print(f"\nLLM Models:")
    print(f"  Sonnet: {MODEL_SONNET}")
    print(f"  Opus:   {MODEL_OPUS}")
    print(f"\nTweet Schedule (ET):")
    for slot, slot_time in SLOT_TIMES_ET.items():
        print(f"  Slot {slot}: {slot_time} - {SLOTS[slot]}")


if __name__ == "__main__":
    main()
