#!/usr/bin/env python3
"""
CONFIG - Centralized Configuration Management
==============================================

Single source of truth for all configuration values across the codebase.
Uses environment variables for secrets, sensible defaults for everything else.

Usage:
    from src.common.config import (
        ANTHROPIC_API_KEY,
        TRAILING_STOP_PCT,
        MODEL_SONNET,
        TRADES_DIR
    )
"""

import os
from pathlib import Path
from typing import Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

# Project root (two levels up from src/common/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRADES_DIR = PROJECT_ROOT / "trades"
TICKERS_FILE = PROJECT_ROOT / "complete_tickers.txt"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


# ═══════════════════════════════════════════════════════════════════════════════
# SECRETS (from environment variables)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional requirement check."""
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Required environment variable not set: {key}")
    return value


# API Keys
ANTHROPIC_API_KEY = _get_env("ANTHROPIC_API_KEY")

# Twitter/X API (for automated posting)
TWITTER_API_KEY = _get_env("TWITTER_API_KEY")
TWITTER_API_SECRET = _get_env("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = _get_env("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = _get_env("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = _get_env("TWITTER_BEARER_TOKEN")

# Email (for notifications)
SMTP_SERVER = _get_env("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(_get_env("SMTP_PORT", "587"))
EMAIL_SENDER = _get_env("EMAIL_SENDER")
EMAIL_PASSWORD = _get_env("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = _get_env("EMAIL_RECIPIENTS", "").split(",") if _get_env("EMAIL_RECIPIENTS") else []


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

TRAILING_STOP_PCT: float = 20.0       # 20% trailing stop from highest close
STOP_WARNING_PCT: float = 5.0         # Warn when within 5% of stop
TIGHTEN_STOP_PCT: float = 15.0        # Tighten to 15% on BoS down

BETA_THRESHOLD: float = 1.5           # Minimum beta for entry
BANKER_TIER1: int = 70                # Tier 1 banker threshold
BANKER_TIER2: int = 60                # Tier 2 banker threshold
BANKER_TIER3: int = 55                # Tier 3 banker threshold (entry minimum)

HMA_PERIOD: int = 21                  # Hull Moving Average period
HMA_PIVOT_LOOKBACK: int = 1           # Pivot detection lookback


# ═══════════════════════════════════════════════════════════════════════════════
# LLM MODELS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_SONNET: str = "claude-sonnet-4-20250514"    # Cost-effective for most tasks
MODEL_OPUS: str = "claude-opus-4-5-20251101"      # Deep analysis (DD, complex tasks)

# Default model assignments by component
MODEL_THEMATIC: str = MODEL_SONNET
MODEL_GATEKEEPER: str = MODEL_SONNET
MODEL_TWEET: str = MODEL_SONNET
MODEL_NEWSLETTER: str = MODEL_SONNET
MODEL_MARKET: str = MODEL_SONNET
MODEL_DD_QUICK: str = MODEL_SONNET
MODEL_DD_FULL: str = MODEL_OPUS


# ═══════════════════════════════════════════════════════════════════════════════
# LLM API SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RETRIES: int = 5                      # Max retry attempts on failure
RATE_LIMIT_COOLDOWN: float = 60.0         # Seconds to wait on rate limit
INTER_STEP_DELAY: float = 30.0            # Delay between major pipeline steps
INTER_STOCK_DELAY: float = 8.0            # Delay between per-stock LLM calls
BACKOFF_FACTOR: float = 2.0               # Exponential backoff multiplier
BACKOFF_MAX_WAIT: float = 300.0           # Maximum wait time for backoff (5 min)
MIN_REQUEST_INTERVAL: float = 1.0         # Minimum seconds between requests

# Token limits by model
MAX_TOKENS: Dict[str, int] = {
    MODEL_SONNET: 8192,
    MODEL_OPUS: 8192,
}

# Default max tokens if model not in dict
DEFAULT_MAX_TOKENS: int = 4096

# Cost per 1M tokens (USD)
COST_INPUT_PER_M: Dict[str, float] = {
    MODEL_SONNET: 3.00,
    MODEL_OPUS: 15.00,
}
COST_OUTPUT_PER_M: Dict[str, float] = {
    MODEL_SONNET: 15.00,
    MODEL_OPUS: 75.00,
}
COST_WEB_SEARCH: float = 0.01  # Per search


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET SCHEDULING (Eastern Time)
# ═══════════════════════════════════════════════════════════════════════════════

SLOTS: Dict[int, str] = {
    1: "pre_market",     # 08:00 ET - Pre-market / Beat SPY / Roth IRA hooks
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

TWEETS_PER_DAY: int = 5
TWEETS_PER_WEEK: int = 35


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_TYPES = [
    # Original types
    "buy_signal",
    "theme_hot",
    "theme_cold",
    "closed_trade",
    "position_update",
    "sell_signal",
    "system_promo",
    "market_insight",
    "educational",
    "engagement",
    # US-focused types
    "beat_spy",
    "roth_ira",
    "pdt_friendly",
    "power_hour",
    "sector_rotation",
    "funnel_graphic",
    "post_mortem",
    "win_card",
    "alpha_card",
]


# ═══════════════════════════════════════════════════════════════════════════════
# THEME SCORING
# ═══════════════════════════════════════════════════════════════════════════════

THEME_SCORE_PRIME: float = 7.5         # >= for PRIME classification
THEME_SCORE_INVESTABLE: float = 6.0    # >= for INVESTABLE
THEME_SCORE_SELECTIVE: float = 4.5     # >= for SELECTIVE
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

YFINANCE_PERIOD: str = "1y"           # Data period for beta calculation
YFINANCE_INTERVAL: str = "1d"         # Data interval
MIN_TRADING_DAYS: int = 60            # Minimum data points for valid beta


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

CARD_WIDTH: int = 1200                # Twitter card width
CARD_HEIGHT: int = 675                # Twitter card height
CARD_BG_COLOR: str = "#1a1a2e"        # Dark theme background
CARD_TEXT_COLOR: str = "#ffffff"      # White text
CARD_ACCENT_GREEN: str = "#00ff88"    # Win/bullish accent
CARD_ACCENT_RED: str = "#ff4444"      # Loss/bearish accent


# ═══════════════════════════════════════════════════════════════════════════════
# URLS
# ═══════════════════════════════════════════════════════════════════════════════

SUBSTACK_URL: str = "https://sterlingsignals.substack.com"
TWITTER_PROFILE_URL: str = "https://twitter.com/SterlingSignals"
TRADINGVIEW_LAYOUT_ID: str = "rxC5j0SK"


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_api_key() -> bool:
    """Check if Anthropic API key is configured."""
    return bool(ANTHROPIC_API_KEY)


def validate_twitter_credentials() -> bool:
    """Check if Twitter credentials are configured."""
    return all([
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET
    ])


def validate_email_config() -> bool:
    """Check if email configuration is complete."""
    return all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS])


def get_model_max_tokens(model: str) -> int:
    """Get max tokens for a model with fallback to default."""
    return MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model API call."""
    input_cost = (input_tokens / 1_000_000) * COST_INPUT_PER_M.get(model, 3.0)
    output_cost = (output_tokens / 1_000_000) * COST_OUTPUT_PER_M.get(model, 15.0)
    return input_cost + output_cost


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Configuration Values")
    print("=" * 60)

    print(f"\nPaths:")
    print(f"  PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"  TRADES_DIR:   {TRADES_DIR}")
    print(f"  TICKERS_FILE: {TICKERS_FILE}")

    print(f"\nTrading Parameters:")
    print(f"  Trailing Stop:   {TRAILING_STOP_PCT}%")
    print(f"  Stop Warning:    {STOP_WARNING_PCT}%")
    print(f"  Beta Threshold:  {BETA_THRESHOLD}")

    print(f"\nLLM Models:")
    print(f"  Sonnet: {MODEL_SONNET}")
    print(f"  Opus:   {MODEL_OPUS}")

    print(f"\nTweet Schedule (ET):")
    for slot, time in SLOT_TIMES_ET.items():
        print(f"  Slot {slot}: {time} - {SLOTS[slot]}")

    print(f"\nAPI Key Status:")
    print(f"  Anthropic: {'✓ Set' if validate_api_key() else '✗ Not set'}")
    print(f"  Twitter:   {'✓ Set' if validate_twitter_credentials() else '✗ Not set'}")
    print(f"  Email:     {'✓ Set' if validate_email_config() else '✗ Not set'}")
