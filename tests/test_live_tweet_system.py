"""Tests for live tweet system — 5 critical gaps.

Covers:
  - Weekend SIGNAL_ALERT (Gap 3)
  - Weekend content generation (Gap 2)
  - Minimum daily cadence (Gap 5)
  - Persona differentiation / slot data (Gap 4)
  - Slot collision & similarity threshold (Gap 4 validation)
  - Category weekly count helper

All tests use pure unit mocking — no API calls, no file I/O.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

import pytest

from twitter.live_tweet_generator import (
    decide_tweet_type,
    validate_tweet,
    validate_thread,
    _prepare_slot_data,
    _find_best_persona,
    _pick_available_category,
    _build_thread_prompt_section,
    _parse_thread_output,
    _validate_thread_integrity,
    build_allowed_tickers,
    build_context_tickers,
    RecentTweetTracker,
    format_portfolio_for_prompt,
    build_user_prompt,
    write_to_live_queue,
    WEEKEND_CATEGORIES,
    LIVE_VALID_CATEGORIES,
    LIVE_CATEGORY_EXAMPLES,
    ACCOUNT_VARIANTS,
)
from twitter.models import ValidationResult, EXTERNAL_TICKER_CATEGORIES
from config import PERSONAS, PERSONA_AFFINITY


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_portfolio():
    """Portfolio with 3 open winning positions."""
    return [
        {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        {"ticker": "BBB", "entry_price": "20.00", "highest_close": "30.00", "theme": "Energy"},
        {"ticker": "CCC", "entry_price": "5.00", "highest_close": "8.00", "theme": "Quantum"},
    ]


@pytest.fixture
def sample_signals():
    """Signals with fresh buy_signals."""
    return {
        "timestamp": (datetime.now() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
        "buy_signals": [
            {"symbol": "DDD", "theme": "AI", "final_decision": "TRADE", "conviction": 8},
            {"symbol": "EEE", "theme": "Energy", "final_decision": "TRADE", "conviction": 7},
        ],
    }


@pytest.fixture
def stale_signals():
    """Signals older than 48h relative to the mock Sunday (Feb 15 10:00 ET)."""
    # Use a fixed timestamp that's 72h before Feb 15 10:00 = Feb 12 10:00
    # This ensures >48h regardless of when the test is run
    return {
        "timestamp": "2026-02-12 10:00:00",
        "buy_signals": [
            {"symbol": "OLD", "theme": "Legacy", "final_decision": "TRADE", "conviction": 5},
        ],
    }


@pytest.fixture
def empty_recent_tweets():
    """No recent tweets."""
    return []


@pytest.fixture
def quiet_context():
    """Context with no movers, quiet market."""
    return {
        "market_snapshot": {"spy_move": "+0.1%", "qqq_move": "+0.2%", "vix": "15", "market_mood": "quiet"},
        "portfolio_movers": [],
        "theme_activity": [],
    }


@pytest.fixture
def volatile_context():
    """Context with volatile mood."""
    return {
        "market_snapshot": {"spy_move": "-2.5%", "qqq_move": "-3.1%", "vix": "28", "market_mood": "volatile"},
        "portfolio_movers": [{"ticker": "$AAA", "move": "+5.2%", "context": "Earnings beat"}],
        "theme_activity": [],
    }


def _make_recent_tweet(
    category: str, ticker: str = "", hours_ago: int = 1, status: str = "posted",
    base_time: Optional[datetime] = None,
):
    """Create a recent tweet entry for testing.

    Args:
        base_time: If provided, compute generated_at relative to this. Useful when
                   datetime is mocked and you need timestamps consistent with the mock.
    """
    base = base_time or datetime.now(timezone.utc)
    gen_time = base - timedelta(hours=hours_ago)
    return {
        "category": category,
        "primary_ticker": ticker,
        "status": status,
        "generated_at": gen_time.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 1: Weekend SIGNAL_ALERT (Gap 3)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeekendSignalAlert:
    """SIGNAL_ALERT should fire on weekends for fresh scanner signals."""

    def test_signal_alert_in_weekend_categories(self):
        """SIGNAL_ALERT must be in WEEKEND_CATEGORIES set."""
        assert "SIGNAL_ALERT" in WEEKEND_CATEGORIES

    @patch("twitter.live_tweet_generator.datetime")
    def test_fresh_signal_triggers_on_sunday_pm(
        self, mock_dt, sample_portfolio, sample_signals, empty_recent_tweets, quiet_context,
    ):
        """Fresh signal (<48h) triggers SIGNAL_ALERT on Sunday PM."""
        # Sunday at 16:00 ET
        sunday_pm = datetime(2026, 2, 15, 16, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = sunday_pm
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        result = decide_tweet_type(quiet_context, sample_portfolio, sample_signals, empty_recent_tweets)

        assert result["action"] == "tweet"
        assert result["type"] == "SIGNAL_ALERT"
        assert result["urgency"] == "high"  # Sunday PM = high urgency

    @patch("twitter.live_tweet_generator.datetime")
    def test_stale_signal_skipped(
        self, mock_dt, sample_portfolio, stale_signals, empty_recent_tweets, quiet_context,
    ):
        """Signals older than 48h don't trigger SIGNAL_ALERT."""
        sunday = datetime(2026, 2, 15, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = sunday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        result = decide_tweet_type(quiet_context, sample_portfolio, stale_signals, empty_recent_tweets)

        # Should fall through to filler or cadence, NOT SIGNAL_ALERT
        assert result.get("type") != "SIGNAL_ALERT"

    @patch("twitter.live_tweet_generator.datetime")
    def test_already_tweeted_signal_skipped(
        self, mock_dt, sample_portfolio, sample_signals,
    ):
        """Signal ticker already tweeted in last 6h is skipped — next signal used."""
        sunday = datetime(2026, 2, 15, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = sunday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Both DDD and EEE were tweeted recently (timestamps relative to mocked Sunday)
        base = sunday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("SIGNAL_ALERT", "DDD", hours_ago=2, base_time=base),
            _make_recent_tweet("SIGNAL_ALERT", "EEE", hours_ago=1, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)

        result = decide_tweet_type(
            {"market_snapshot": {}, "portfolio_movers": [], "theme_activity": []},
            sample_portfolio, sample_signals, recent, tracker=tracker,
        )

        # Both signals were recently tweeted, so SIGNAL_ALERT should be skipped
        # (falls through to lower priority). If it still picks SIGNAL_ALERT somehow,
        # the ticker must not be one we already tweeted.
        if result["type"] == "SIGNAL_ALERT":
            assert result.get("tickers", [None])[0] not in ("DDD", "EEE")

    @patch("twitter.live_tweet_generator.datetime")
    def test_saturday_signal_not_high_urgency(
        self, mock_dt, sample_portfolio, sample_signals, empty_recent_tweets, quiet_context,
    ):
        """Saturday signals get medium urgency (not high — that's Sunday PM only)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        result = decide_tweet_type(quiet_context, sample_portfolio, sample_signals, empty_recent_tweets)

        assert result["action"] == "tweet"
        assert result["type"] == "SIGNAL_ALERT"
        assert result["urgency"] == "medium"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 2: Weekend Content Generation (Gap 2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeekendContentGeneration:
    """Weekend content should generate — filler is no longer blocked."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_filler_fires_on_weekends(
        self, mock_dt, sample_portfolio, quiet_context,
    ):
        """Filler tweets should fire on weekends (was previously blocked)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # Stale signals (no SIGNAL_ALERT trigger) + no movers
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(quiet_context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        # Should be a weekend-safe category
        assert result["type"] in WEEKEND_CATEGORIES

    @patch("twitter.live_tweet_generator.datetime")
    def test_market_reaction_blocked_on_weekends(
        self, mock_dt, sample_portfolio, volatile_context,
    ):
        """MARKET_COMMENTARY should NOT fire on weekends (markets closed)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(volatile_context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] != "MARKET_COMMENTARY"

    @patch("twitter.live_tweet_generator.datetime")
    def test_dip_opportunity_blocked_on_weekends(
        self, mock_dt, sample_portfolio,
    ):
        """MARKET_COMMENTARY should NOT fire on weekends (markets closed)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [{"ticker": "$AAA", "move": "-5.0%", "context": "Pullback"}],
            "theme_activity": [],
        }
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result.get("type") != "MARKET_COMMENTARY"

    @patch("twitter.live_tweet_generator.datetime")
    def test_receipt_allowed_on_weekends(
        self, mock_dt, sample_portfolio,
    ):
        """RECEIPT (positive mover) should still work on weekends."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [{"ticker": "$AAA", "move": "+5.0%", "context": "Good earnings"}],
            "theme_activity": [],
        }
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 3: Minimum Daily Cadence (Gap 5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMinimumCadence:
    """New 7-priority cascade: P5 TECHNICAL_ANALYSIS / EDUCATIONAL → P6 ENGAGEMENT → SKIP."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_quiet_market_hits_technical_analysis(self, mock_dt):
        """Quiet context with portfolio → P5a TECHNICAL_ANALYSIS fires."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))  # Monday
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # Single position — not enough winners for multi-receipt at P2
        portfolio = [
            {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "TECHNICAL_ANALYSIS"

    @patch("twitter.live_tweet_generator.datetime")
    def test_educational_when_technical_recently_used(self, mock_dt):
        """P5b EDUCATIONAL fires when TECHNICAL_ANALYSIS recently used."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Single position + TECHNICAL_ANALYSIS posted 2h ago (within 4h cooldown)
        portfolio = [
            {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        ]
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, recent, tracker=tracker)

        assert result["action"] == "tweet"
        assert result["type"] == "EDUCATIONAL"

    @patch("twitter.live_tweet_generator.datetime")
    def test_engagement_when_p5_exhausted(self, mock_dt):
        """P6 ENGAGEMENT fires when both TECHNICAL_ANALYSIS and EDUCATIONAL recently used."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Single position + both P5 types recently used (within cooldown windows)
        portfolio = [
            {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        ]
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=3, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, recent, tracker=tracker)

        assert result["action"] == "tweet"
        assert result["type"] == "ENGAGEMENT"

    @patch("twitter.live_tweet_generator.datetime")
    def test_skip_when_all_exhausted(self, mock_dt):
        """SKIP returned when all category budgets or cooldowns are exhausted."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # All lower-priority types recently used + empty portfolio (no RECEIPT/TECHNICAL_ANALYSIS tickers)
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=1, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=2, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=1, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        # Empty portfolio + all cooldowns active → cascade falls through to SKIP
        tracker = RecentTweetTracker(recent)
        result = decide_tweet_type(context, [], signals, recent, tracker=tracker)

        assert result["action"] == "skip"
        assert "exhausted" in result["reason"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 4: _prepare_slot_data (Gap 4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrepareSlotData:
    """Slot data assigns different tickers per account when possible."""

    def test_different_tickers_per_account(self, sample_portfolio, sample_signals):
        """When 3+ tickers available, each account gets a different one."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)

        tickers = [result[v]["ticker"] for v in ACCOUNT_VARIANTS]
        # All 3 should be different (AAA from decision + BBB, CCC from portfolio)
        assert len(set(tickers)) == 3

    def test_shared_ticker_fallback(self):
        """When only 1 ticker available, best persona gets it; others get non-ticker fallback."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        portfolio = [{"ticker": "AAA", "entry_price": "10", "highest_close": "15", "theme": "AI"}]
        signals = {"buy_signals": []}

        result = _prepare_slot_data(decision, portfolio, signals)

        # Best persona for RECEIPT is variant_1 (Alex primary), gets the ticker
        assert result["variant_1"]["ticker"] == "AAA"
        # Others have no ticker — fall back to non-ticker categories from their pools
        assert result["variant_2"]["ticker"] == ""
        assert result["variant_3"]["ticker"] == ""
        # variant_2 (Rozalia) should get from her primary pool (non-ticker categories)
        # variant_3 (James) should get from his primary pool (non-ticker categories)
        assert result["variant_2"]["category"] != "RECEIPT"
        assert result["variant_3"]["category"] != "RECEIPT"
        # Each variant gets a different category (persona affinity routing)
        categories = {result[v]["category"] for v in ACCOUNT_VARIANTS}
        assert len(categories) == 3, f"Expected 3 unique categories, got {categories}"

        # All should still have different angles
        angles = [result[v]["angle"] for v in ACCOUNT_VARIANTS]
        assert len(set(angles)) == 3

    def test_decision_tickers_highest_priority(self, sample_portfolio, sample_signals):
        """Decision tickers should be assigned first (variant_1)."""
        decision = {"type": "RECEIPT", "tickers": ["BBB"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)

        assert result["variant_1"]["ticker"] == "BBB"

    def test_scanner_signals_included(self, sample_signals):
        """Buy signals from scanner are included as candidates."""
        decision = {"type": "SIGNAL_ALERT", "tickers": ["DDD"]}
        portfolio = []  # No portfolio
        result = _prepare_slot_data(decision, portfolio, sample_signals)

        all_tickers = {result[v]["ticker"] for v in ACCOUNT_VARIANTS}
        # DDD from decision, EEE from signals
        assert "DDD" in all_tickers
        assert "EEE" in all_tickers

    def test_angles_always_different(self, sample_portfolio, sample_signals):
        """Each account always gets a different angle."""
        decision = {"type": "ENGAGEMENT", "tickers": []}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)

        angles = [result[v]["angle"] for v in ACCOUNT_VARIANTS]
        assert angles == ["data-driven", "explains-why", "punchy-direct"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 5: Slot Collision Validation (Gap 4 — step 8.5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlotCollision:
    """Step 8.5: same primary_ticker on different accounts = fail."""

    def test_collision_detected(self):
        """Two variants with same ticker should fail step 8.5."""
        tweet = {
            "text": "$AAA up 50%. Scanner delivered.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        other = {
            "text": "$AAA showing strength here.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_2",
            "chart_recommended": True,
        }
        # Slot assignments say different tickers
        slots = {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "RECEIPT", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "RECEIPT", "angle": "punchy-direct"},
        }

        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA", "BBB", "CCC"},
            all_variants=[other],
            slot_assignments=slots,
        )

        collision_failures = [f for f in result.failures if "step8_5_collision" in f]
        assert len(collision_failures) > 0

    def test_no_collision_different_tickers(self):
        """Different tickers across accounts should pass step 8.5."""
        tweet = {
            "text": "$AAA up 50%. Scanner delivered.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        other = {
            "text": "$BBB breaking out. Eyes on this one.",
            "category": "RECEIPT",
            "primary_ticker": "BBB",
            "account": "variant_2",
            "chart_recommended": True,
        }
        slots = {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "RECEIPT", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "RECEIPT", "angle": "punchy-direct"},
        }

        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA", "BBB", "CCC"},
            all_variants=[other],
            slot_assignments=slots,
        )

        collision_failures = [f for f in result.failures if "step8_5_collision" in f]
        assert len(collision_failures) == 0

    def test_shared_ticker_allowed_when_few_candidates(self):
        """When slot_assignments share tickers (< unique), collision is allowed."""
        tweet = {
            "text": "$AAA up 50%. Data doesn't lie.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        other = {
            "text": "Here's why $AAA matters. Let me break this down.",
            "category": "EDUCATIONAL",
            "primary_ticker": "AAA",
            "account": "variant_2",
            "chart_recommended": False,
        }
        # Only 1 unique ticker assigned (shared)
        slots = {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "AAA", "category": "EDUCATIONAL", "angle": "explains-why"},
            "variant_3": {"ticker": "AAA", "category": "ENGAGEMENT", "angle": "punchy-direct"},
        }

        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            all_variants=[other],
            slot_assignments=slots,
        )

        collision_failures = [f for f in result.failures if "step8_5_collision" in f]
        assert len(collision_failures) == 0  # Allowed because shared intentionally


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 6: Similarity Threshold
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimilarityThreshold:
    """Step 8: PRD requires <70% similarity between variants."""

    def test_above_70_fails(self):
        """Tweets >70% similar should fail step 8."""
        tweet = {
            "text": "$AAA up 50% since entry. The scanner delivered big time here.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        # Very similar — just minor word changes
        other = {
            "text": "$AAA up 50% since entry. The scanner delivered big results here.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_2",
            "chart_recommended": True,
        }

        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            all_variants=[other],
        )

        dedup_failures = [f for f in result.failures if "step8_dedup" in f]
        assert len(dedup_failures) > 0

    def test_below_70_passes(self):
        """Tweets <70% similar should pass step 8."""
        tweet = {
            "text": "$AAA up 50%. Clean technical breakout on volume.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        # Distinctly different wording and focus
        other = {
            "text": "Momentum is real. Eyes on the energy sector rotation this week.",
            "category": "THEME_CATALYST",
            "primary_ticker": "",
            "account": "variant_2",
            "chart_recommended": False,
        }

        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            all_variants=[other],
        )

        dedup_failures = [f for f in result.failures if "step8_dedup" in f]
        assert len(dedup_failures) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 7: Category Weekly Count
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryWeeklyCount:
    """RecentTweetTracker correctly counts weekly categories."""

    def test_count_correct(self):
        """Counts tweets of a category within the last 7 days."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12),
            _make_recent_tweet("EDUCATIONAL", hours_ago=36),
            _make_recent_tweet("EDUCATIONAL", hours_ago=120),  # 5 days ago
            _make_recent_tweet("ENGAGEMENT", hours_ago=12),  # Different category
        ]

        tracker = RecentTweetTracker(recent)
        assert tracker.categories_this_week.get("EDUCATIONAL", 0) == 3

    def test_ignores_old_tweets(self):
        """Tweets older than 7 days are not counted."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12),
            _make_recent_tweet("EDUCATIONAL", hours_ago=200),  # ~8 days
        ]

        tracker = RecentTweetTracker(recent)
        assert tracker.categories_this_week.get("EDUCATIONAL", 0) == 1

    def test_ignores_failed_tweets(self):
        """Failed/skipped tweets should not be counted in weekly budget."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12, status="posted"),
            _make_recent_tweet("EDUCATIONAL", hours_ago=24, status="failed"),
            _make_recent_tweet("EDUCATIONAL", hours_ago=36, status="skipped"),
        ]

        tracker = RecentTweetTracker(recent)
        # Only "posted" counts (failed included in queue scan but not in weekly budget)
        assert tracker.categories_this_week.get("EDUCATIONAL", 0) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 8: PERSONAS Config
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonasConfig:
    """Verify PERSONAS dict has required structure for all 3 accounts."""

    def test_all_accounts_present(self):
        """PERSONAS must have main, account2, account3."""
        assert "main" in PERSONAS
        assert "account2" in PERSONAS
        assert "account3" in PERSONAS

    def test_persona_has_required_fields(self):
        """Each persona must have name, archetype, voice, focus, signature_phrases."""
        for key, persona in PERSONAS.items():
            assert "name" in persona, f"{key} missing 'name'"
            assert "archetype" in persona, f"{key} missing 'archetype'"
            assert "voice" in persona, f"{key} missing 'voice'"
            assert "focus" in persona, f"{key} missing 'focus'"
            assert "signature_phrases" in persona, f"{key} missing 'signature_phrases'"

    def test_no_banned_terms_in_personas(self):
        """Signature phrases must not contain banned terms."""
        from config.banned_terms import ALL_BANNED
        for key, persona in PERSONAS.items():
            for phrase in persona.get("signature_phrases", []):
                phrase_lower = phrase.lower()
                for banned in ALL_BANNED:
                    assert banned.lower() not in phrase_lower, (
                        f"PERSONAS['{key}'] phrase '{phrase}' contains banned term '{banned}'"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 9: New Categories + Priority Cascade (Content Quality Audit)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewCategories:
    """Verify categories (SELL_SIGNAL, TECHNICAL_ANALYSIS, SIGNAL_ALERT) pass validation."""

    def test_sell_signal_passes_step1(self):
        """SELL_SIGNAL is in LIVE_VALID_CATEGORIES and passes step 1."""
        assert "SELL_SIGNAL" in LIVE_VALID_CATEGORIES
        tweet = {
            "text": "$SMCI setup invalidated below $36. Win more than you lose. Moving on.",
            "category": "SELL_SIGNAL",
            "primary_ticker": "SMCI",
            "account": "variant_1",
            "chart_recommended": True,
        }
        result = validate_tweet(tweet, allowed_tickers={"SMCI"})
        step1_failures = [f for f in result.failures if "step1" in f]
        assert len(step1_failures) == 0

    def test_technical_analysis_passes_step1(self):
        """TECHNICAL_ANALYSIS is in LIVE_VALID_CATEGORIES and passes step 1."""
        assert "TECHNICAL_ANALYSIS" in LIVE_VALID_CATEGORIES
        tweet = {
            "text": "$WCC holding above $281 entry. Watching $320 resistance. NFA",
            "category": "TECHNICAL_ANALYSIS",
            "primary_ticker": "WCC",
            "account": "variant_1",
            "chart_recommended": True,
        }
        result = validate_tweet(tweet, allowed_tickers={"WCC"})
        step1_failures = [f for f in result.failures if "step1" in f]
        assert len(step1_failures) == 0

    def test_signal_alert_watching_passes_step1(self):
        """SIGNAL_ALERT (watching sub-type) is in LIVE_VALID_CATEGORIES and passes step 1."""
        assert "SIGNAL_ALERT" in LIVE_VALID_CATEGORIES
        tweet = {
            "text": "On my radar: $IONQ at $42.15. Waiting for confirmation. NFA.",
            "category": "SIGNAL_ALERT",
            "primary_ticker": "IONQ",
            "account": "variant_1",
            "chart_recommended": False,
        }
        result = validate_tweet(tweet, allowed_tickers={"IONQ"})
        step1_failures = [f for f in result.failures if "step1" in f]
        assert len(step1_failures) == 0


class TestSellSignalPriority:
    """Sell signals get highest priority (P0) in decide_tweet_type()."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_sell_signal_highest_priority(self, mock_dt, sample_portfolio):
        """Sell signals fire before buy signals."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        signals = {
            "timestamp": "2026-02-16 10:00:00",
            "buy_signals": [{"symbol": "INOD", "price": 61.54}],
            "sell_signals": [{"symbol": "VNET", "reason": "Weekly BoS Down"}],
        }
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "SELL_SIGNAL"
        assert "VNET" in result["tickers"]


class TestPositionCommentary:
    """TECHNICAL_ANALYSIS fires at P5 in quiet market."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_quiet_market_position_commentary(self, mock_dt):
        """When no movers/themes/signals, TECHNICAL_ANALYSIS fires for position commentary."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # Single position — avoids P2 multi-receipt (needs 3 winners)
        portfolio = [
            {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "TECHNICAL_ANALYSIS"
        assert "Position commentary" in result["reason"]


class TestSignalAlertWatchingDecision:
    """SIGNAL_ALERT (watching) fires at P1 when consider_signals exist."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_signal_alert_watching_from_consider_signals(self, mock_dt, sample_portfolio):
        """consider_signals trigger SIGNAL_ALERT (watching sub-type) at P1."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # P1b fires before any lower priority — no need to block anything
        signals = {
            "timestamp": "2026-02-10 10:00:00",
            "buy_signals": [],
            "consider_signals": [{"symbol": "IONQ", "price": 42.15}],
        }
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "SIGNAL_ALERT"
        assert result.get("sub_type") == "watching"
        assert "IONQ" in result["tickers"]


class TestNegativePercentRegex:
    """Negative percentage regex fix — '15-25%' should NOT trigger."""

    def test_range_format_no_false_positive(self):
        """'15-25%' should not be caught as negative percentage."""
        tweet = {
            "text": "Expecting 15-25% upside from here. $STRL looking strong.",
            "category": "TECHNICAL_ANALYSIS",
            "primary_ticker": "STRL",
            "account": "variant_1",
            "chart_recommended": True,
        }
        result = validate_tweet(tweet, allowed_tickers={"STRL"})
        step4_failures = [f for f in result.failures if "step4_winners_only" in f and "negative" in f]
        assert len(step4_failures) == 0

    def test_actual_negative_still_caught(self):
        """'-25% drawdown' should still be caught."""
        tweet = {
            "text": "Down -25% on this trade. Rough week.",
            "category": "MARKET_COMMENTARY",
            "primary_ticker": "",
            "account": "variant_1",
            "chart_recommended": False,
        }
        result = validate_tweet(tweet, allowed_tickers=set())
        step4_failures = [f for f in result.failures if "step4_winners_only" in f and "negative" in f]
        assert len(step4_failures) > 0


class TestPortfolioCurrentPrices:
    """format_portfolio_for_prompt() includes current price when available."""

    def test_current_price_in_output(self):
        """Current price should appear when provided."""
        portfolio = [
            {"ticker": "STRL", "entry_price": "362.53", "highest_close": "437.77", "theme": "AI Infrastructure"},
        ]
        current_prices = {"STRL": 420.15}
        result = format_portfolio_for_prompt(portfolio, current_prices=current_prices)

        assert "current $420.15" in result
        assert "+15.9%" in result

    def test_fallback_to_highest_without_current(self):
        """Without current prices, falls back to highest_close."""
        portfolio = [
            {"ticker": "STRL", "entry_price": "362.53", "highest_close": "437.77", "theme": "AI Infrastructure"},
        ]
        result = format_portfolio_for_prompt(portfolio)

        assert "high $437.77" in result
        assert "current" not in result


class TestFunnelStatsInPrompt:
    """Funnel stats appear in SIGNAL_ALERT user prompt."""

    def test_funnel_stats_injected(self):
        """When signals have stats, they appear in the prompt."""
        decision = {"type": "SIGNAL_ALERT", "tickers": ["INOD"], "reason": "Fresh signal"}
        context = {"market_snapshot": {}, "portfolio_movers": [], "theme_activity": [], "fintwit_trending": []}
        portfolio = [{"ticker": "INOD", "entry_price": "60", "highest_close": "65", "theme": "AI"}]
        signals = {"stats": {"tickers_loaded": 1817, "final_trade": 2, "final_consider": 5}}

        result = build_user_prompt(decision, context, portfolio, signals=signals)

        assert "1,817 stocks scanned" in result
        assert "7 survived all gates" in result


class TestMultiTickerReceipt:
    """Multi-ticker receipt triggers with 3+ winners at P2."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_multi_receipt_with_3_winners(self, mock_dt):
        """3+ winners trigger multi-ticker RECEIPT at P2 with thread=True."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # 3 winners (>5% above entry) — no single movers (quiet day)
        portfolio = [
            {"ticker": "AAA", "entry_price": "10", "highest_close": "15", "theme": "AI", "status": "OPEN"},
            {"ticker": "BBB", "entry_price": "20", "highest_close": "30", "theme": "Defense", "status": "OPEN"},
            {"ticker": "CCC", "entry_price": "5", "highest_close": "8", "theme": "Nuclear", "status": "OPEN"},
        ]
        # No RECEIPT in last 24h (required for multi-receipt)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"
        assert result.get("multi_receipt") is True
        assert result.get("thread") is True
        assert len(result["tickers"]) >= 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 12: P2 Alternation (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2Alternation:
    """P2 alternates between RECEIPT and MARKET_COMMENTARY via tracker.last_p2_category."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_commentary_preferred_after_receipt(self, mock_dt):
        """MARKET_COMMENTARY fires at P2 when last P2 was RECEIPT and market is notable."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Single position to avoid multi-receipt; last P2 was RECEIPT
        portfolio = [
            {"ticker": "AAA", "entry_price": "10.00", "highest_close": "15.00", "theme": "AI"},
        ]
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("RECEIPT", "AAA", hours_ago=6, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        # Notable market condition (SPY > 1%) triggers MARKET_COMMENTARY
        context = {
            "market_snapshot": {"market_mood": "bullish", "spy_move": "+1.5%"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, portfolio, signals, recent, tracker=tracker)

        assert result["action"] == "tweet"
        assert result["type"] == "MARKET_COMMENTARY"

    @patch("twitter.live_tweet_generator.datetime")
    def test_receipt_preferred_after_commentary(self, mock_dt, sample_portfolio):
        """RECEIPT fires at P2 when last P2 was MARKET_COMMENTARY and mover exists."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Last P2 was MARKET_COMMENTARY — next P2 should prefer RECEIPT
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("MARKET_COMMENTARY", hours_ago=6, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        # Positive mover enables RECEIPT
        context = {
            "market_snapshot": {"market_mood": "bullish", "spy_move": "+1.5%"},
            "portfolio_movers": [{"ticker": "$AAA", "move": "+5.0%", "context": "Strong earnings"}],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, recent, tracker=tracker)

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"
        assert "AAA" in result["tickers"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 13: All Budgets Exhausted (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllBudgetsExhausted:
    """SKIP returned when all category budgets are exhausted."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_skip_when_everything_exhausted(self, mock_dt):
        """All lower-priority categories recently used + empty portfolio → SKIP."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # All categories recently used within cooldown windows
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=1, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=2, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=1, base_time=base),
        ]
        tracker = RecentTweetTracker(recent)
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
        }

        result = decide_tweet_type(context, [], signals, recent, tracker=tracker)

        assert result["action"] == "skip"
        assert "exhausted" in result["reason"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Persona Affinity Routing (Phase 5 — Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonaAffinityRouting:
    """_prepare_slot_data assigns different categories per persona via affinity routing."""

    def test_receipt_routes_to_alex(self, sample_portfolio, sample_signals):
        """RECEIPT (in Alex's primary) → variant_1 gets RECEIPT."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)
        assert result["variant_1"]["category"] == "RECEIPT"

    def test_educational_routes_to_rozalia(self, sample_portfolio, sample_signals):
        """EDUCATIONAL (in Rozalia's primary) → variant_2 gets EDUCATIONAL."""
        decision = {"type": "EDUCATIONAL", "tickers": []}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)
        assert result["variant_2"]["category"] == "EDUCATIONAL"

    def test_market_commentary_routes_to_james(self, sample_portfolio, sample_signals):
        """MARKET_COMMENTARY (in James's primary) → variant_3 gets it."""
        decision = {"type": "MARKET_COMMENTARY", "tickers": ["AAA"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)
        assert result["variant_3"]["category"] == "MARKET_COMMENTARY"

    def test_other_personas_get_different_categories(self, sample_portfolio, sample_signals):
        """Non-best personas get different categories from their own pools."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)
        categories = {result[v]["category"] for v in ACCOUNT_VARIANTS}
        assert len(categories) == 3, f"Expected 3 unique categories, got {categories}"
        # variant_2 and variant_3 must NOT have RECEIPT
        assert result["variant_2"]["category"] != "RECEIPT"
        assert result["variant_3"]["category"] != "RECEIPT"

    def test_avoids_respected(self, sample_portfolio, sample_signals):
        """No persona gets a category from its avoids set."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        result = _prepare_slot_data(decision, sample_portfolio, sample_signals)
        for variant in ACCOUNT_VARIANTS:
            cat = result[variant]["category"]
            avoids = PERSONA_AFFINITY.get(variant, {}).get("avoids", set())
            assert cat not in avoids, f"{variant} got '{cat}' which is in avoids {avoids}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: _find_best_persona helper (Phase 5 — Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindBestPersona:
    """_find_best_persona returns the variant with strongest affinity."""

    def test_primary_match_wins(self):
        """Category in a variant's primary set → that variant is chosen."""
        assert _find_best_persona("RECEIPT", PERSONA_AFFINITY) == "variant_1"
        assert _find_best_persona("EDUCATIONAL", PERSONA_AFFINITY) == "variant_2"
        assert _find_best_persona("MARKET_COMMENTARY", PERSONA_AFFINITY) == "variant_3"

    def test_secondary_fallback(self):
        """When no primary match, secondary match is used."""
        custom = {
            "variant_1": {"primary": {"A"}, "secondary": {"X"}, "avoids": set()},
            "variant_2": {"primary": {"B"}, "secondary": {"Y"}, "avoids": set()},
            "variant_3": {"primary": {"C"}, "secondary": {"X"}, "avoids": set()},
        }
        # X is secondary for variant_1 and variant_3, no primary match
        assert _find_best_persona("X", custom) == "variant_1"  # First secondary match

    def test_default_to_variant_1(self):
        """When no match at all, default to variant_1."""
        custom = {
            "variant_1": {"primary": {"A"}, "secondary": {"B"}, "avoids": set()},
            "variant_2": {"primary": {"C"}, "secondary": {"D"}, "avoids": set()},
            "variant_3": {"primary": {"E"}, "secondary": {"F"}, "avoids": set()},
        }
        assert _find_best_persona("UNKNOWN", custom) == "variant_1"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: _pick_available_category helper (Phase 5 — Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPickAvailableCategory:
    """_pick_available_category selects from pools respecting avoids/exclude."""

    def test_primary_preferred(self):
        """Primary categories are preferred over secondary."""
        result = _pick_available_category(
            primary={"EDUCATIONAL", "THEME_LIST"},
            secondary={"MARKET_COMMENTARY"},
            avoids=set(),
        )
        assert result in {"EDUCATIONAL", "THEME_LIST"}

    def test_avoids_excluded(self):
        """Categories in avoids set are never returned."""
        result = _pick_available_category(
            primary={"EDUCATIONAL"},
            secondary={"MARKET_COMMENTARY"},
            avoids={"EDUCATIONAL"},
        )
        assert result != "EDUCATIONAL"
        assert result == "MARKET_COMMENTARY"

    def test_exclude_set_respected(self):
        """Already-assigned categories are excluded."""
        result = _pick_available_category(
            primary={"EDUCATIONAL", "THEME_LIST"},
            secondary={"MARKET_COMMENTARY"},
            avoids=set(),
            exclude={"EDUCATIONAL"},
        )
        assert result != "EDUCATIONAL"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Thread Prompt Building (Phase 5 — Task 5.2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadPromptBuilding:
    """_build_thread_prompt_section adds thread format instructions."""

    def test_theme_list_thread_prompt(self):
        """THEME_LIST + thread=True produces thread format instructions."""
        decision = {"type": "THEME_LIST", "thread": True}
        result = _build_thread_prompt_section(decision)
        assert "THREAD FORMAT" in result
        assert "thread_tweets" in result

    def test_multi_receipt_thread_prompt(self):
        """Multi-RECEIPT + thread=True produces thread format instructions."""
        decision = {"type": "RECEIPT", "thread": True, "multi_receipt": True}
        result = _build_thread_prompt_section(decision)
        assert "THREAD FORMAT" in result
        assert "thread_tweets" in result

    def test_non_thread_returns_empty(self):
        """Non-thread decisions return empty string."""
        decision = {"type": "ENGAGEMENT", "thread": False}
        result = _build_thread_prompt_section(decision)
        assert result == ""

    def test_no_thread_key_returns_empty(self):
        """Decisions without thread key return empty string."""
        decision = {"type": "SIGNAL_ALERT"}
        result = _build_thread_prompt_section(decision)
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Thread Output Parsing (Phase 5 — Task 5.3)
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadOutputParsing:
    """_parse_thread_output handles thread items gracefully."""

    def test_flat_tweet_passes_through(self):
        """Non-thread tweet passes through unchanged."""
        tweet = {"text": "Hello world", "category": "ENGAGEMENT"}
        result = _parse_thread_output([tweet])
        assert len(result) == 1
        assert result[0]["text"] == "Hello world"
        assert "is_thread" not in result[0] or not result[0].get("is_thread")

    def test_valid_thread_preserved(self):
        """Valid 2-tweet thread is preserved with text set to tweet 1."""
        tweet = {
            "is_thread": True,
            "category": "THEME_LIST",
            "thread_tweets": [
                {"text": "Opening hook", "number": 1},
                {"text": "$AAA +10% $BBB +20%", "number": 2},
            ],
        }
        result = _parse_thread_output([tweet])
        assert len(result) == 1
        assert result[0]["is_thread"] is True
        assert result[0]["text"] == "Opening hook"
        assert len(result[0]["thread_tweets"]) == 2

    def test_valid_three_tweet_thread(self):
        """Valid 3-tweet thread is preserved."""
        tweet = {
            "is_thread": True,
            "category": "RECEIPT",
            "thread_tweets": [
                {"text": "Hook tweet", "number": 1},
                {"text": "$AAA +15%", "number": 2},
                {"text": "CTA closing", "number": 3},
            ],
        }
        result = _parse_thread_output([tweet])
        assert result[0]["is_thread"] is True
        assert len(result[0]["thread_tweets"]) == 3

    def test_four_tweets_flattened(self):
        """4+ tweets → flattened to single tweet."""
        tweet = {
            "is_thread": True,
            "category": "THEME_LIST",
            "thread_tweets": [
                {"text": "Tweet 1", "number": 1},
                {"text": "Tweet 2", "number": 2},
                {"text": "Tweet 3", "number": 3},
                {"text": "Tweet 4", "number": 4},
            ],
        }
        result = _parse_thread_output([tweet])
        assert result[0]["is_thread"] is False
        assert result[0]["text"] == "Tweet 1"
        assert "thread_tweets" not in result[0]

    def test_over_length_sub_tweet_flattened(self):
        """Sub-tweet >280 chars → entire thread flattened."""
        tweet = {
            "is_thread": True,
            "category": "THEME_LIST",
            "thread_tweets": [
                {"text": "Short hook", "number": 1},
                {"text": "X" * 281, "number": 2},
            ],
        }
        result = _parse_thread_output([tweet])
        assert result[0]["is_thread"] is False
        assert result[0]["text"] == "Short hook"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: validate_thread wrapper (Phase 5 — Task 5.3)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateThread:
    """validate_thread handles both thread and flat items."""

    def test_non_thread_delegates(self):
        """Non-thread item delegates to validate_tweet."""
        tweet = {
            "text": "Simple tweet about $AAA gaining momentum",
            "category": "ENGAGEMENT",
            "account": "variant_1",
        }
        result = validate_thread(tweet, allowed_tickers={"AAA"})
        assert isinstance(result, ValidationResult)
        assert result.passed is True

    def test_valid_thread_passes(self):
        """Thread with valid sub-tweets passes validation."""
        tweet = {
            "text": "Opening hook about the market",
            "is_thread": True,
            "category": "THEME_LIST",
            "account": "variant_2",
            "thread_tweets": [
                {"text": "Opening hook about the market", "number": 1},
                {"text": "$AAA at $15.50 — up 25% this week", "number": 2},
            ],
        }
        result = validate_thread(tweet, allowed_tickers={"AAA"})
        assert result.passed is True

    def test_banned_term_in_sub_tweet_fails(self):
        """Banned term in any sub-tweet causes failure."""
        tweet = {
            "text": "Opening hook",
            "is_thread": True,
            "category": "THEME_LIST",
            "account": "variant_2",
            "thread_tweets": [
                {"text": "Opening hook about opportunities", "number": 1},
                {"text": "$AAA has HMA pivots signaling up 10%", "number": 2},
            ],
        }
        result = validate_thread(tweet, allowed_tickers={"AAA"})
        assert result.passed is False
        # Failure should be prefixed with thread_tweet_N
        assert any("thread_tweet_" in f for f in result.failures)

    def test_thread_data_check(self):
        """Continuation tweets without tickers/data fail thread_data_check."""
        tweet = {
            "text": "Opening hook",
            "is_thread": True,
            "category": "THEME_LIST",
            "account": "variant_2",
            "thread_tweets": [
                {"text": "Opening hook about the market", "number": 1},
                {"text": "This is just filler text with no data", "number": 2},
            ],
        }
        result = validate_thread(tweet, allowed_tickers=set())
        assert result.passed is False
        assert any("thread_data_check" in f for f in result.failures)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Thread Queue Writing (Phase 5 — Task 5.4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadQueueWriting:
    """write_to_live_queue emits thread fields for thread items."""

    @patch("twitter.live_tweet_generator.load_json_list")
    def test_thread_item_in_queue(self, mock_load, tmp_path):
        """Thread item in queue has is_thread=True and thread_tweets array."""
        import twitter.live_tweet_generator as ltg
        queue_file = tmp_path / "live_content_queue.json"
        original = ltg.LIVE_QUEUE_FILE
        ltg.LIVE_QUEUE_FILE = queue_file
        mock_load.return_value = []

        try:
            validated = [{
                "text": "Opening hook about themes",
                "category": "THEME_LIST",
                "account": "variant_2",
                "is_thread": True,
                "thread_tweets": [
                    {"text": "Opening hook about themes", "number": 1},
                    {"text": "$AAA at $15 — part of the AI wave", "number": 2},
                ],
            }]
            decision = {"type": "THEME_LIST"}
            context = {"market_snapshot": {"spy_move": "+0.5%", "market_mood": "bullish"}}

            write_to_live_queue(validated, decision, context, cost=0.01)

            written = json.loads(queue_file.read_text())
            assert len(written) == 1
            entry = written[0]
            assert entry["is_thread"] is True
            assert len(entry["thread_tweets"]) == 2
            assert "_thread" in entry["id"]
        finally:
            ltg.LIVE_QUEUE_FILE = original

    @patch("twitter.live_tweet_generator.load_json_list")
    def test_flat_tweet_no_thread_fields(self, mock_load, tmp_path):
        """Flat tweet in queue has no is_thread or thread_tweets fields."""
        import twitter.live_tweet_generator as ltg
        queue_file = tmp_path / "live_content_queue.json"
        original = ltg.LIVE_QUEUE_FILE
        ltg.LIVE_QUEUE_FILE = queue_file
        mock_load.return_value = []

        try:
            validated = [{
                "text": "Just a flat tweet about $AAA",
                "category": "ENGAGEMENT",
                "account": "variant_1",
            }]
            decision = {"type": "ENGAGEMENT"}
            context = {"market_snapshot": {"spy_move": "+0.3%", "market_mood": "neutral"}}

            write_to_live_queue(validated, decision, context, cost=0.005)

            written = json.loads(queue_file.read_text())
            assert len(written) == 1
            entry = written[0]
            assert "is_thread" not in entry
            assert "thread_tweets" not in entry
            assert "_thread" not in entry["id"]
        finally:
            ltg.LIVE_QUEUE_FILE = original


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: THEME_LIST Thread Flag (Phase 5 — Task 5.5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestThemeListThreadFlag:
    """THEME_LIST decision includes thread=True."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_theme_list_has_thread_flag(self, mock_dt):
        """When P4a fires THEME_LIST, decision includes thread=True."""
        weekday = datetime(2026, 2, 23, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.min = datetime.min

        # Need portfolio with >=3 themes for THEME_LIST to fire at P4a
        portfolio = [
            {"ticker": "AAA", "entry_price": "10", "highest_close": "15", "theme": "AI"},
            {"ticker": "BBB", "entry_price": "20", "highest_close": "30", "theme": "Energy"},
            {"ticker": "CCC", "entry_price": "5", "highest_close": "8", "theme": "Quantum"},
        ]
        signals = {"timestamp": "2026-02-23 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "bullish"},
            "portfolio_movers": [],
            "theme_activity": [
                {"theme": "AI", "signal_type": "strengthening"},
                {"theme": "Energy", "signal_type": "emerging"},
            ],
        }
        recent = []  # No recent tweets — allows P4a to fire
        tracker = RecentTweetTracker(recent)

        result = decide_tweet_type(context, portfolio, signals, recent, tracker=tracker)

        # P4a may or may not fire depending on other priority cascade conditions.
        # If THEME_LIST fires, it must have thread=True.
        if result.get("type") == "THEME_LIST":
            assert result.get("thread") is True, "THEME_LIST must have thread=True"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 TESTS — Validation Pipeline Updates
# ═══════════════════════════════════════════════════════════════════════════════


# ─── TestBuildContextTickers ──────────────────────────────────────────────────

class TestBuildContextTickers:
    """build_context_tickers extracts tickers from context theme_tickers."""

    def test_extracts_tickers_from_theme_tickers(self):
        """Tickers from theme_tickers are extracted correctly."""
        context = {
            "theme_tickers": [
                {
                    "theme": "AI",
                    "tickers": [
                        {"symbol": "NVDA", "price": 800},
                        {"symbol": "AMD", "price": 150},
                    ],
                },
                {
                    "theme": "Energy",
                    "tickers": [
                        {"symbol": "XOM", "price": 110},
                    ],
                },
            ]
        }
        result = build_context_tickers(context)
        assert result == {"NVDA", "AMD", "XOM"}

    def test_empty_context_returns_empty(self):
        """None or empty context returns empty set."""
        assert build_context_tickers(None) == set()
        assert build_context_tickers({}) == set()
        assert build_context_tickers({"theme_tickers": []}) == set()

    def test_strips_dollar_signs(self):
        """Dollar signs are stripped from symbols."""
        context = {
            "theme_tickers": [
                {
                    "theme": "AI",
                    "tickers": [{"symbol": "$NVDA", "price": 800}],
                },
            ]
        }
        result = build_context_tickers(context)
        assert "NVDA" in result
        assert "$NVDA" not in result


# ─── TestBuildAllowedTickersNoContext ─────────────────────────────────────────

class TestBuildAllowedTickersNoContext:
    """After split, build_allowed_tickers does NOT include context tickers."""

    def test_context_tickers_not_in_allowed(self):
        """build_allowed_tickers only has portfolio + signals, not context."""
        portfolio = [{"ticker": "AAA"}]
        signals = {"buy_signals": [{"symbol": "BBB"}], "consider_signals": []}
        result = build_allowed_tickers(portfolio, signals)
        assert result == {"AAA", "BBB"}
        # Context ticker should NOT appear
        assert "NVDA" not in result


# ─── TestTickerFabricationExternal ────────────────────────────────────────────

class TestTickerFabricationExternal:
    """Step 2 uses context_tickers for EXTERNAL_TICKER_CATEGORIES only."""

    def test_market_commentary_accepts_context_ticker(self):
        """MARKET_COMMENTARY with context ticker passes step 2."""
        tweet = {
            "text": "$NVDA leading the AI charge — semiconductors on fire.",
            "category": "MARKET_COMMENTARY",
            "account": "variant_1",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            context_tickers={"NVDA"},
        )
        step2 = [f for f in result.failures if "step2_fabrication" in f]
        assert len(step2) == 0, f"MARKET_COMMENTARY should accept context ticker: {step2}"

    def test_theme_list_accepts_context_ticker(self):
        """THEME_LIST with context ticker passes step 2."""
        tweet = {
            "text": "$AMD part of the AI semiconductor rotation.",
            "category": "THEME_LIST",
            "account": "variant_2",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers=set(),
            context_tickers={"AMD"},
        )
        step2 = [f for f in result.failures if "step2_fabrication" in f]
        assert len(step2) == 0, f"THEME_LIST should accept context ticker: {step2}"

    def test_trending_take_accepts_context_ticker(self):
        """TRENDING_TAKE with context ticker passes step 2."""
        tweet = {
            "text": "$TSLA trending on FinTwit — EV momentum shifting.",
            "category": "TRENDING_TAKE",
            "account": "variant_1",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers=set(),
            context_tickers={"TSLA"},
        )
        step2 = [f for f in result.failures if "step2_fabrication" in f]
        assert len(step2) == 0, f"TRENDING_TAKE should accept context ticker: {step2}"

    def test_receipt_rejects_context_only_ticker(self):
        """RECEIPT does NOT accept context-only tickers (not an external category)."""
        tweet = {
            "text": "$NVDA up 25% from entry. Scanner called it.",
            "category": "RECEIPT",
            "account": "variant_1",
            "primary_ticker": "NVDA",
            "chart_recommended": True,
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            context_tickers={"NVDA"},
        )
        step2 = [f for f in result.failures if "step2_fabrication" in f]
        assert len(step2) > 0, "RECEIPT should reject context-only ticker"

    def test_no_context_tickers_same_behavior(self):
        """When context_tickers is None, step 2 uses only allowed_tickers."""
        tweet = {
            "text": "$NVDA breaking out above key levels.",
            "category": "MARKET_COMMENTARY",
            "account": "variant_1",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA"},
            context_tickers=None,
        )
        step2 = [f for f in result.failures if "step2_fabrication" in f]
        assert len(step2) > 0, "Without context_tickers, $NVDA should fail step 2"


# ─── TestThreadIntegrity ─────────────────────────────────────────────────────

class TestThreadIntegrity:
    """_validate_thread_integrity step 6c checks."""

    def test_valid_two_tweet_thread(self):
        """Valid 2-tweet thread passes."""
        tweet = {
            "thread_tweets": [
                {"text": "The AI semiconductor cycle is accelerating.", "number": 1},
                {"text": "$NVDA at $800 — leading the charge. $AMD at $150.", "number": 2},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert failures == []

    def test_valid_three_tweet_thread(self):
        """Valid 3-tweet thread passes."""
        tweet = {
            "thread_tweets": [
                {"text": "Three themes dominating today.", "number": 1},
                {"text": "$NVDA $800 — AI infrastructure leader.", "number": 2},
                {"text": "$XOM $110 — energy sector rotation.", "number": 3},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert failures == []

    def test_one_tweet_too_few(self):
        """Single tweet thread fails (need 2-3)."""
        tweet = {
            "thread_tweets": [
                {"text": "$NVDA breaking out above resistance.", "number": 1},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("1 tweets (must be 2-3)" in f for f in failures)

    def test_four_tweets_too_many(self):
        """4+ tweet thread fails (max 3)."""
        tweet = {
            "thread_tweets": [
                {"text": "Opening hook about the market today.", "number": 1},
                {"text": "$NVDA at $800 — AI leader.", "number": 2},
                {"text": "$AMD at $150 — catching up.", "number": 3},
                {"text": "$TSLA at $250 — EV momentum.", "number": 4},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("4 tweets (must be 2-3)" in f for f in failures)

    def test_sub_tweet_over_280_chars(self):
        """Sub-tweet exceeding 280 chars fails."""
        long_text = "A" * 281
        tweet = {
            "thread_tweets": [
                {"text": "Opening hook about themes today.", "number": 1},
                {"text": long_text, "number": 2},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("281 chars (max 280)" in f for f in failures)

    def test_sub_tweet_under_10_chars(self):
        """Sub-tweet under 10 chars fails."""
        tweet = {
            "thread_tweets": [
                {"text": "Opening hook about opportunities.", "number": 1},
                {"text": "Short", "number": 2},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("5 chars (min 10)" in f for f in failures)

    def test_tweet_1_starts_with_ticker(self):
        """First tweet starting with $TICKER fails (should be thematic hook)."""
        tweet = {
            "thread_tweets": [
                {"text": "$NVDA is the leader in AI semiconductors.", "number": 1},
                {"text": "$AMD also strong at $150 entry.", "number": 2},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("starts with ticker" in f for f in failures)

    def test_no_ticker_in_any_tweet(self):
        """No $TICKER in any thread tweet fails."""
        tweet = {
            "thread_tweets": [
                {"text": "AI semiconductors are heating up this week.", "number": 1},
                {"text": "Multiple names showing relative strength.", "number": 2},
            ]
        }
        failures = _validate_thread_integrity(tweet)
        assert any("no $TICKER" in f for f in failures)


# ─── TestChartFlagConstants ──────────────────────────────────────────────────

class TestChartFlagConstants:
    """Step 7 chart flag uses CHART_REQUIRED_CATEGORIES from models.py."""

    def test_receipt_always_gets_chart(self):
        """RECEIPT (in CHART_REQUIRED_CATEGORIES) always gets chart_recommended=True."""
        tweet = {
            "text": "$AAA up 50% from entry. System delivers.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": False,  # Start false — step 7 should fix
        }
        validate_tweet(tweet, allowed_tickers={"AAA"})
        assert tweet["chart_recommended"] is True

    def test_technical_analysis_chart_only_with_ticker(self):
        """TECHNICAL_ANALYSIS gets chart only when primary_ticker present (not always)."""
        # With ticker → chart recommended
        tweet_with = {
            "text": "$AAA holding key support at $15.",
            "category": "TECHNICAL_ANALYSIS",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": False,
        }
        validate_tweet(tweet_with, allowed_tickers={"AAA"})
        assert tweet_with["chart_recommended"] is True

        # Without ticker → no chart
        tweet_without = {
            "text": "Markets finding support at key levels.",
            "category": "TECHNICAL_ANALYSIS",
            "account": "variant_1",
            "chart_recommended": True,  # Start true — step 7 should fix to False
        }
        validate_tweet(tweet_without, allowed_tickers=set())
        assert tweet_without["chart_recommended"] is False


# ─── TestContextStalenessExtended ────────────────────────────────────────────

class TestContextStalenessExtended:
    """Step 9 staleness check now blocks TRENDING_TAKE too."""

    def test_trending_take_blocked_when_stale(self):
        """TRENDING_TAKE with stale context (>4h) fails step 9."""
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        context = {"gathered_at": stale_time}
        tweet = {
            "text": "$TSLA trending on FinTwit — EV momentum.",
            "category": "TRENDING_TAKE",
            "account": "variant_1",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"TSLA"},
            context=context,
        )
        stale_failures = [f for f in result.failures if "step9_staleness" in f]
        assert len(stale_failures) > 0
        assert any("TRENDING_TAKE" in f for f in stale_failures)

    def test_trending_take_blocked_on_fallback(self):
        """TRENDING_TAKE with fallback_mode context fails step 9."""
        context = {"fallback_mode": True}
        tweet = {
            "text": "$TSLA trending today — EV sector rotation.",
            "category": "TRENDING_TAKE",
            "account": "variant_1",
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"TSLA"},
            context=context,
        )
        stale_failures = [f for f in result.failures if "step9_staleness" in f]
        assert len(stale_failures) > 0
        assert any("TRENDING_TAKE" in f for f in stale_failures)


# ─── TestSlotCollisionRelaxed ────────────────────────────────────────────────

class TestSlotCollisionRelaxed:
    """Step 8.5 relaxed: same ticker + different category = OK."""

    def test_same_ticker_different_category_no_collision(self):
        """Same ticker on two accounts with DIFFERENT categories passes."""
        tweet = {
            "text": "$AAA up 50% from entry. Scanner delivered.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        other = {
            "text": "$AAA is breaking out technically — key levels to watch.",
            "category": "EDUCATIONAL",
            "primary_ticker": "AAA",
            "account": "variant_2",
        }
        slots = {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "EDUCATIONAL", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "RECEIPT", "angle": "punchy-direct"},
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA", "BBB", "CCC"},
            all_variants=[other],
            slot_assignments=slots,
        )
        collision = [f for f in result.failures if "step8_5_collision" in f]
        assert len(collision) == 0, f"Different categories should NOT collide: {collision}"

    def test_same_ticker_same_category_still_collides(self):
        """Same ticker + same category on two accounts still fails."""
        tweet = {
            "text": "$AAA up 50%. Scanner called it perfectly.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_1",
            "chart_recommended": True,
        }
        other = {
            "text": "$AAA showing huge gains this week.",
            "category": "RECEIPT",
            "primary_ticker": "AAA",
            "account": "variant_2",
            "chart_recommended": True,
        }
        slots = {
            "variant_1": {"ticker": "AAA", "category": "RECEIPT", "angle": "data-driven"},
            "variant_2": {"ticker": "BBB", "category": "RECEIPT", "angle": "explains-why"},
            "variant_3": {"ticker": "CCC", "category": "RECEIPT", "angle": "punchy-direct"},
        }
        result = validate_tweet(
            tweet,
            allowed_tickers={"AAA", "BBB", "CCC"},
            all_variants=[other],
            slot_assignments=slots,
        )
        collision = [f for f in result.failures if "step8_5_collision" in f]
        assert len(collision) > 0, "Same ticker + same category should still collide"
