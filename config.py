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

from pathlib import Path
from typing import Dict, List

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
TICKERS_FILE = BASE_DIR / "complete_tickers.txt"


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
    'self_quote',        # Renamed to milestone_alerts
]


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

TRAILING_STOP_PCT = 20.0      # 20% trailing stop from highest close
STOP_WARNING_PCT = 5.0        # Warn when within 5% of stop
TIGHTEN_STOP_PCT = 15.0       # Tighten to 15% on BoS down

BETA_THRESHOLD = 1.5          # Minimum beta for entry
BANKER_TIER1 = 70             # Tier 1 banker threshold
BANKER_TIER2 = 60             # Tier 2 banker threshold
BANKER_TIER3 = 55             # Tier 3 banker threshold (entry minimum)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM MODELS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_SONNET = "claude-sonnet-4-20250514"   # Cost-effective for most tasks
MODEL_OPUS = "claude-opus-4-5-20251101"     # Deep analysis (DD, complex tasks)

# Default model for each component
MODEL_THEMATIC = MODEL_SONNET
MODEL_GATEKEEPER = MODEL_SONNET
MODEL_TWEET = MODEL_SONNET
MODEL_NEWSLETTER = MODEL_SONNET
MODEL_MARKET = MODEL_SONNET
MODEL_DD_QUICK = MODEL_SONNET
MODEL_DD_FULL = MODEL_OPUS


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

# Slot timing in UTC (for GitHub Actions cron - assuming EST, not EDT)
SLOT_TIMES_UTC: Dict[int, str] = {
    1: "13:00",   # 08:00 ET = 13:00 UTC (EST)
    2: "15:00",   # 10:00 ET = 15:00 UTC (EST)
    3: "17:30",   # 12:30 ET = 17:30 UTC (EST)
    4: "20:30",   # 15:30 ET = 20:30 UTC (EST)
    5: "23:00"    # 18:00 ET = 23:00 UTC (EST)
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

TWEETS_PER_DAY = 5
TWEETS_PER_WEEK = 25  # MOD-1: Fixed from 35 (Sat=5, Sun=5, Mon=5, Tue=5, Wed=5 = 25)

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
    'min_win_to_highlight': 15.0,       # Minimum % gain to include in top_performers
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

# Signal classifications for content
SIGNAL_CLASSIFICATIONS: Dict[str, str] = {
    'PASS': 'Cleared all 5 gates - full TEAL recommendation',
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
SIGNAL_BRAND = "TEAL signal"  # Instead of "PASS signal"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: SIGNAL_TYPES - Full nested structure from MASTER_TODO
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_TYPES: Dict[str, Dict] = {
    'PASS': {
        'description': 'Cleared all 5 gates - full TEAL signal',
        'public_name': 'TEAL Signal',
        'gates_required': [1, 2, 3, 4, 5],
        'show_publicly': True,
    },
    'CONSIDER': {
        'description': 'Cleared gates 1-4, watching for gate 5',
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
# PHASE 10: BANNED_TERMS - Never use these in public content
# ═══════════════════════════════════════════════════════════════════════════════

BANNED_TERMS: List[str] = [
    # Strategy internals (keep secret)
    'HMA', 'Hull Moving Average', 'HMA Pivot',
    'Banker indicator', 'Banker >= 55', 'Banker score',
    '20% trailing stop', '20% stop',
    'Beta >= 1.5',
    'Break of Structure', 'BoS', 'BOS',
    'Tier 1', 'Tier 2', 'Tier 3',
    'Gatekeeper',

    # Geographic (US-focused audience)
    'UK ISA', 'ISA account', 'GMT', 'BST', 'UK Time',

    # Branding consistency
    'PASS signal',      # Use "TEAL signal"
    'weekly winners',   # Misleading - positions held months
    'this week we nailed',  # Misleading timeframe

    # Technical indicators we don't want to reveal
    'RSI', 'MACD', 'KDJ',

    # MASTER_TODO_v2: Internal terms that leaked
    'Capital Preservation Protocol',
    'Forensic Audit',
    'Volatility Expansion Criteria',
    '5th Gate',               # Say "cleared all gates" instead
    'Gate 5',                 # Say "cleared all gates" instead

    # MASTER_TODO_v2: Non-branded signal terms - MUST use "TEAL signal"
    'buy signal',             # Use "TEAL signal"
    'proprietary entry',      # Use "TEAL signal"
    'proprietary signal',     # Use "TEAL signal"

    # MASTER_TODO_v2: US-specific (wrong audience)
    'Roth IRA', 'Roth',
    'PDT', 'PDT rule', 'pattern day trader',
    '401k', '401(k)',
]


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVED PUBLIC TERMS (Marketing Vocabulary) - MASTER_TODO_v2
# ═══════════════════════════════════════════════════════════════════════════════

APPROVED_TERMS: Dict[str, List[str]] = {
    'signals': [
        'TEAL signal',
        'TEAL signal fires',
        'triggers a TEAL signal',
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


def enforce_teal_branding(text: str) -> str:
    """Replace non-branded signal terms with TEAL branding.

    MASTER_TODO_v2: All signal references MUST use 'TEAL signal'.

    Args:
        text: Text to process

    Returns:
        Text with TEAL branding applied
    """
    replacements = {
        'buy signal': 'TEAL signal',
        'Buy signal': 'TEAL signal',
        'BUY SIGNAL': 'TEAL SIGNAL',
        'proprietary entry': 'TEAL signal',
        'proprietary signal': 'TEAL signal',
        'our signal': 'TEAL signal',
        'new signal': 'TEAL signal',
        'passes our criteria': 'triggers a TEAL signal',
        'cleared our system': 'triggers a TEAL signal',
        'PASS signal': 'TEAL signal',
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
        (2, 'thread_buy_signal'),  # Deep dive on top TEAL signal
        (3, 'theme_hot'),
        (4, 'funnel_graphic'),
        (5, 'engagement'),
    ],
    'Sunday': [
        (1, 'buy_signal'),         # All TEAL signals
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
    'signal_name': 'TEAL signal',
    'signal_tagline': 'TEAL means go.',
    'system_name': '5-Gate System',
    'buy_color': 'TEAL',
    'sell_color': 'VIOLET',
    'substack_url': 'https://sterlingsignals.substack.com',
    'twitter_handle': '@SterlingSignals',
}


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL COLOR SYSTEM (Marketing Upgrade)
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_COLORS: Dict[str, Dict] = {
    'TEAL': {
        'emoji': '🟢',
        'meaning': 'BUY',
        'internal_status': 'PASS',
        'public_name': 'TEAL Signal',
    },
    'VIOLET': {
        'emoji': '🟣',
        'meaning': 'EXIT',
        'internal_status': 'STOPPED',
        'public_name': 'Exit Alert',
    },
    'AMBER': {
        'emoji': '🟠',
        'meaning': 'WATCH',
        'internal_status': 'CONSIDER',
        'public_name': 'On Our Radar',
    },
}

CONVICTION_LANGUAGE: Dict[int, str] = {
    5: 'Extremely Bullish',
    4: 'Bullish',
    3: 'Watching',
    2: 'Cautious',
    1: None,  # Do not post publicly
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
        'title_format': 'TEAL Signals: {date}',
        'filename': 'saturday_weekly_signals.html',
    },
    'sunday': {
        'type': 'deep_dive',
        'title_format': 'Deep Dive: ${ticker}',
        'filename': 'sunday_deep_dive.html',
    },
}


def get_signal_emoji(signal_type: str) -> str:
    """Get emoji for signal type (TEAL, VIOLET, AMBER).

    Args:
        signal_type: The signal type key (TEAL, VIOLET, AMBER)

    Returns:
        Emoji string for the signal type, empty string if not found
    """
    return SIGNAL_COLORS.get(signal_type, {}).get('emoji', '')


def get_conviction_text(score: int) -> str:
    """Convert conviction score to public-facing language.

    Args:
        score: Conviction score (1-5)

    Returns:
        Public-facing text ('Extremely Bullish', 'Bullish', 'Watching', etc.)
        Returns 'Watching' as default for invalid scores
    """
    return CONVICTION_LANGUAGE.get(score, 'Watching')


def can_show_entry_price(position: dict) -> bool:
    """Check if entry price can be shown publicly for a position.

    Entry prices are shown for:
    - Closed winning positions
    - Open positions with gains above threshold (25%)

    Args:
        position: Position dict with 'status', 'pnl_pct' keys

    Returns:
        True if entry price can be shown publicly
    """
    status = position.get('status', 'OPEN')
    pnl_pct = position.get('pnl_pct', 0)

    # Closed winners - always show
    if status == 'CLOSED' and pnl_pct > 0:
        return ENTRY_PRICE_RULES['show_for_closed_winners']

    # Open positions above threshold
    if status == 'OPEN' and pnl_pct >= ENTRY_PRICE_RULES['threshold_pct']:
        return ENTRY_PRICE_RULES['show_for_open_above_threshold']

    return False


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

    Args:
        text: Text to check

    Returns:
        True if any banned term is found
    """
    text_lower = text.lower()
    for term in BANNED_TERMS:
        if term.lower() in text_lower:
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
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """Print current configuration values."""
    print("Configuration Values")
    print("=" * 60)
    print(f"\nTrading Parameters:")
    print(f"  Trailing Stop:   {TRAILING_STOP_PCT}%")
    print(f"  Stop Warning:    {STOP_WARNING_PCT}%")
    print(f"  Beta Threshold:  {BETA_THRESHOLD}")
    print(f"\nLLM Models:")
    print(f"  Sonnet: {MODEL_SONNET}")
    print(f"  Opus:   {MODEL_OPUS}")
    print(f"\nTweet Schedule (ET):")
    for slot, slot_time in SLOT_TIMES_ET.items():
        print(f"  Slot {slot}: {slot_time} - {SLOTS[slot]}")


if __name__ == "__main__":
    main()
