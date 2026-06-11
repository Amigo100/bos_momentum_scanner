#!/usr/bin/env python3
"""
Content Models — Shared data classes for tweet generation pipeline.

Used by: twitter/live_tweet_generator.py, twitter/poster.py, tests/

Ref: STERLING_SIGNALS_PRD_v2.md section 3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET CATEGORIES (from PRD section 3.2)
# ═══════════════════════════════════════════════════════════════════════════════

TWEET_CATEGORIES: Dict[str, Dict] = {
    # ── Signal Categories ─────────────────────────────────────────
    "SELL_SIGNAL": {
        "source": "Exit signals in signals.json",
        "chart_required": True,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["$TICKER", "invalidation framing"],
    },
    "SIGNAL_ALERT": {
        "source": "Scanner signals (PASS + CONSIDER)",
        "chart_required": True,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["$TICKER", "entry price"],
        "sub_types": ["confirmed", "watching"],
    },
    "RECEIPT": {
        "source": "Portfolio winners with intraday moves",
        "chart_required": True,
        "thread_capable": True,   # Multi-winner threads
        "allows_external_tickers": False,
        "min_elements": ["$TICKER", "entry price", "current price", "% gain"],
    },
    # ── Market & Theme Categories ─────────────────────────────────
    "MARKET_COMMENTARY": {
        "source": "Market conditions — any mood (positive, negative, neutral)",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": True,
        "min_elements": ["context"],
    },
    "THEME_CATALYST": {
        "source": "Breaking theme + portfolio overlap",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["theme name", "$TICKER"],
    },
    "THEME_LIST": {
        "source": "Theme tickers (external + portfolio)",
        "chart_required": False,
        "thread_capable": True,   # Always thread format
        "allows_external_tickers": True,
        "min_elements": ["theme name", "3+ $TICKERs with prices"],
    },
    "TRENDING_TAKE": {
        "source": "FinTwit buzz intersecting tracked themes",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": True,
        "min_elements": ["trending topic", "thesis connection"],
    },
    # ── Position & Analysis Categories ────────────────────────────
    "TECHNICAL_ANALYSIS": {
        "source": "Position commentary with key levels",
        "chart_required": False,   # Recommended but not required
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["$TICKER", "level"],
    },
    # ── Content & Community Categories ────────────────────────────
    "EDUCATIONAL": {
        "source": "Methodology, trading psychology, indicator explainers",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["concrete example"],
    },
    "SUBSTACK_TEASER": {
        "source": "Today's Substack post topic + key insight",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": ["value proposition", "content hook"],
    },
    "ENGAGEMENT": {
        "source": "Community building, questions, milestones",
        "chart_required": False,
        "thread_capable": False,
        "allows_external_tickers": False,
        "min_elements": [],  # Flexible
    },
}

# Categories that REQUIRE a chart attachment
CHART_REQUIRED_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info["chart_required"]
}

# Categories that support thread format
THREAD_CAPABLE_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info.get("thread_capable")
}

# Categories that can reference tickers outside portfolio.csv
EXTERNAL_TICKER_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info.get("allows_external_tickers")
}

# All valid category names
VALID_CATEGORIES = set(TWEET_CATEGORIES.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Tweet:
    """A single generated tweet ready for validation and queuing."""

    text: str
    category: str
    chart_required: bool
    tickers_mentioned: List[str] = field(default_factory=list)
    chart_path: Optional[str] = None
    chart_paths: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def get_all_chart_paths(self) -> List[str]:
        """Return all chart paths (multi-chart first, then legacy single fallback)."""
        if self.chart_paths:
            return self.chart_paths
        if self.chart_path:
            return [self.chart_path]
        return []


@dataclass
class ValidationResult:
    """Result of running a tweet through the 7-step validation pipeline."""

    passed: bool
    failures: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


from config.banned_terms import INTERNAL_TERM_PATTERNS  # noqa: F401


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET UTILITIES
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
