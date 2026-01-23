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


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

TWEETS_PER_DAY = 5
TWEETS_PER_WEEK = 35

# Content types for tweets
CONTENT_TYPES: List[str] = [
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
