#!/usr/bin/env python3
"""
Content Models — Shared data classes for tweet generation pipeline.

Used by: content/tweet_generator_v2.py, tests/test_tweet_generator_v2.py

Ref: STERLING_SIGNALS_PRD_v2.md section 3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET CATEGORIES (from PRD section 3.2)
# ═══════════════════════════════════════════════════════════════════════════════

TWEET_CATEGORIES: Dict[str, Dict] = {
    "SCANNER_RESULT": {
        "source": "Weekly scan PASS signals",
        "chart_required": True,
        "min_elements": ["$TICKER", "entry price", "thesis"],
    },
    "DAILY_SIGNAL": {
        "source": "Daily scan BoS buy signals",
        "chart_required": True,
        "min_elements": ["$TICKER", "price"],
    },
    "THEME_ANALYSIS": {
        "source": "Thematic groupings from scan",
        "chart_required": False,   # Recommended but not required
        "min_elements": ["theme name", "$TICKER"],
    },
    "PERFORMANCE": {
        "source": "Portfolio winners >= 25% and notable gains >= 10%",
        "chart_required": True,    # Attach winner charts (multi-image)
        "min_elements": ["$TICKER", "entry price", "current price", "% gain"],
    },
    "WATCHLIST": {
        "source": "CONSIDER signals, near-triggers",
        "chart_required": False,
        "min_elements": ["$TICKER", "price"],
    },
    "TECHNICAL_ANALYSIS": {
        "source": "Existing positions, key levels",
        "chart_required": False,   # Text-only TA tweets acceptable when no chart available
        "min_elements": ["$TICKER", "level"],
    },
    "EDUCATIONAL": {
        "source": "Methodology, indicator explainers",
        "chart_required": False,
        "min_elements": ["concrete example"],
    },
    "MARKET_COMMENTARY": {
        "source": "Market context, dip reactions",
        "chart_required": False,   # Recommended but not required
        "min_elements": ["context", "opportunity"],
    },
    "SELL_SIGNAL": {
        "source": "Daily/weekly BoS bearish pivots",
        "chart_required": True,
        "min_elements": ["$TICKER", "invalidation framing"],
    },
    "ENGAGEMENT": {
        "source": "Community building, milestones",
        "chart_required": False,
        "min_elements": [],  # Flexible
    },
    "NEWSLETTER_CTA": {
        "source": "Drive Substack traffic",
        "chart_required": False,
        "min_elements": ["value proposition"],
    },
    # ═══════════════════════════════════════════════════════════════
    # LIVE TWEET CATEGORIES (used by live_tweet_generator.py)
    # ═══════════════════════════════════════════════════════════════
    "MARKET_REACTION": {
        "source": "Live Grok context — real-time market moves",
        "chart_required": False,
        "min_elements": ["$TICKER", "price movement", "context"],
    },
    "RECEIPT": {
        "source": "Portfolio winners — entry vs current price",
        "chart_required": True,
        "min_elements": ["$TICKER", "entry price", "current price", "% gain"],
    },
    "SIGNAL_ALERT": {
        "source": "Scanner signals — new or recent",
        "chart_required": True,
        "min_elements": ["$TICKER", "entry price"],
    },
    "DIP_OPPORTUNITY": {
        "source": "Market dips — buying opportunity framing",
        "chart_required": False,
        "min_elements": ["context", "$TICKER", "opportunity"],
    },
    "THEME_MOMENTUM": {
        "source": "Theme breakouts with multiple tickers",
        "chart_required": False,
        "min_elements": ["theme name", "3+ $TICKERs with prices"],
    },
}

# Categories that REQUIRE a chart attachment
CHART_REQUIRED_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info["chart_required"]
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


@dataclass
class SlotAssignment:
    """A planned slot in the weekly/daily schedule."""

    day: str        # "monday", "tuesday", etc.
    slot: int       # 1-5 (weekly slots)
    category: str   # One of VALID_CATEGORIES
    data_key: str   # Key into the content data dict (e.g. "pass_signals", "winners")


@dataclass
class ContentData:
    """Aggregated data available for tweet generation."""

    # Weekly scan data
    pass_signals: List[Dict] = field(default_factory=list)
    consider_signals: List[Dict] = field(default_factory=list)
    themes: List[Dict] = field(default_factory=list)
    scan_stats: Dict = field(default_factory=dict)

    # Portfolio data
    winners: List[Dict] = field(default_factory=list)       # >= 25% gain
    notable_holdings: List[Dict] = field(default_factory=list)  # >= 10% gain, < 25%
    holdings: List[Dict] = field(default_factory=list)       # >= 0% gain, < 10%
    sell_signals: List[Dict] = field(default_factory=list)

    # Daily scan data (optional)
    daily_signals: List[Dict] = field(default_factory=list)
    daily_sells: List[Dict] = field(default_factory=list)
    daily_winners: List[Dict] = field(default_factory=list)

    # Market context (optional)
    market_data: Optional[Dict] = None

    # Metadata
    scan_date: str = ""
    newsletter_url: str = ""

    @property
    def has_winners(self) -> bool:
        return len(self.winners) > 0

    @property
    def has_notable_holdings(self) -> bool:
        return len(self.notable_holdings) > 0

    @property
    def has_holdings(self) -> bool:
        return len(self.holdings) > 0

    @property
    def has_consider_signals(self) -> bool:
        return len(self.consider_signals) > 0

    @property
    def has_pass_signals(self) -> bool:
        return len(self.pass_signals) > 0

    @property
    def has_themes(self) -> bool:
        return len(self.themes) > 0

    @property
    def has_daily_signals(self) -> bool:
        return len(self.daily_signals) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL TERMINOLOGY (for validation step 5)
# ═══════════════════════════════════════════════════════════════════════════════
#
# These internal terms must NEVER appear in public tweets.
# Imported from config.banned_terms for the actual list; duplicated
# here as regex patterns for the terminology-specific validation step.

INTERNAL_TERM_PATTERNS: List[str] = [
    # Legacy indicator terms
    r"\bHMA\b",
    r"\bBoS\b",
    r"\bBOS\b",
    r"\bBanker\b",
    r"\btier\s*[123]\b",
    r"\bTIER[123]\b",
    r"\bconviction\s*\d+\b",
    r"\bconviction\s+score\b",
    r"\bVWAP\b",
    r"\bgate\s*[1-5]\b",
    r"\b5-gate\b",
    r"\b5th\s+gate\b",
    r"\bgatekeeper\b",
    r"\bRSI\b",
    r"\bMACD\b",
    r"\bKDJ\b",
    # Sterling Grid terms (never reveal publicly)
    r"\bUC\b",
    r"\bundercurrent\b",
    r"\bExD\b",
    r"\bprofit\s+lock\b",
    r"\btiered\s+stop\b",
    r"\bgear\s+shift\b",
    r"\bprice\s+cap\b",
    r"\binvestment\s+gate\b",
    r"\bdeep\s+dd\b",
    r"\bSTRONG\s+BUY\b",
    r"\bSPEC\s+BUY\b",
    r"\bNO\s+GO\b",
    r"\bvaluation\s+regime\b",
    r"\bkill\s+switch\b",
]
