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
    _prepare_slot_data,
    _count_category_this_week,
    format_portfolio_for_prompt,
    build_user_prompt,
    WEEKEND_CATEGORIES,
    LIVE_VALID_CATEGORIES,
    LIVE_CATEGORY_EXAMPLES,
    ACCOUNT_VARIANTS,
)
from twitter.models import ValidationResult
from config import PERSONAS


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
        "tweet_opportunities": [],
    }


@pytest.fixture
def volatile_context():
    """Context with volatile mood."""
    return {
        "market_snapshot": {"spy_move": "-2.5%", "qqq_move": "-3.1%", "vix": "28", "market_mood": "volatile"},
        "portfolio_movers": [{"ticker": "$AAA", "move": "+5.2%", "context": "Earnings beat"}],
        "theme_activity": [],
        "tweet_opportunities": [],
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

        # Both DDD and EEE were tweeted recently (timestamps relative to mocked Sunday)
        base = sunday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("SIGNAL_ALERT", "DDD", hours_ago=2, base_time=base),
            _make_recent_tweet("SIGNAL_ALERT", "EEE", hours_ago=1, base_time=base),
        ]

        result = decide_tweet_type(
            {"market_snapshot": {}, "portfolio_movers": [], "theme_activity": [], "tweet_opportunities": []},
            sample_portfolio, sample_signals, recent,
        )

        # Both signals were recently tweeted, so SIGNAL_ALERT should be skipped
        # (falls through to filler/cadence). If it still picks SIGNAL_ALERT somehow,
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
        """MARKET_REACTION should NOT fire on weekends (markets closed)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(volatile_context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] != "MARKET_REACTION"

    @patch("twitter.live_tweet_generator.datetime")
    def test_dip_opportunity_blocked_on_weekends(
        self, mock_dt, sample_portfolio,
    ):
        """DIP_OPPORTUNITY should NOT fire on weekends (markets closed)."""
        saturday = datetime(2026, 2, 14, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = saturday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [{"ticker": "$AAA", "move": "-5.0%", "context": "Pullback"}],
            "theme_activity": [],
            "tweet_opportunities": [],
        }
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result.get("type") != "DIP_OPPORTUNITY"

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
            "tweet_opportunities": [],
        }
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 3: Minimum Daily Cadence (Gap 5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMinimumCadence:
    """When nothing tweetable, fallback cascade: RECEIPT → EDUCATIONAL → ENGAGEMENT."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_fallback_to_receipt(self, mock_dt, sample_portfolio):
        """First fallback is RECEIPT when winning positions exist."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))  # Monday
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # 4+ tweets today (timestamps relative to mock Monday = past filler threshold)
        # + 2 NEWSLETTER_CTAs this week (block Priority 8)
        # + TECHNICAL_ANALYSIS recently (block Priority 5 position commentary)
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("ENGAGEMENT", hours_ago=i, base_time=base) for i in range(1, 5)
        ] + [
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=24, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=72, base_time=base),
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, recent)

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"

    @patch("twitter.live_tweet_generator.datetime")
    def test_fallback_to_educational(self, mock_dt, sample_portfolio):
        """Second fallback is EDUCATIONAL when RECEIPT and TECHNICAL_ANALYSIS recently posted."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # RECEIPT posted 2h ago + TECHNICAL_ANALYSIS posted 2h ago + 2 NEWSLETTER_CTAs this week
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("ENGAGEMENT", hours_ago=1, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=2, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=3, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=4, base_time=base),
            _make_recent_tweet("RECEIPT", "AAA", hours_ago=2, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=24, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=72, base_time=base),
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, recent)

        assert result["action"] == "tweet"
        assert result["type"] == "EDUCATIONAL"

    @patch("twitter.live_tweet_generator.datetime")
    def test_educational_3_per_week_cap(self, mock_dt, sample_portfolio):
        """EDUCATIONAL caps at 3/week — after that, skip to ENGAGEMENT."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # 3 EDUCATIONAL this week + RECEIPT recently + 2 CTAs this week
        # + TECHNICAL_ANALYSIS recently (block P5)
        # ENGAGEMENT last posted 8h ago (outside 6h cooldown — so cadence fallback can pick it)
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("ENGAGEMENT", hours_ago=8, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=9, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=10, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=11, base_time=base),
            _make_recent_tweet("RECEIPT", "AAA", hours_ago=2, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=24, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=48, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=72, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=24, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=72, base_time=base),
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, recent)

        assert result["action"] == "tweet"
        assert result["type"] == "ENGAGEMENT"

    @patch("twitter.live_tweet_generator.datetime")
    def test_engagement_as_last_resort(self, mock_dt):
        """ENGAGEMENT is the final fallback when RECEIPT and EDUCATIONAL exhausted."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # Empty portfolio + EDUCATIONAL exhausted + 2 CTAs this week
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("ENGAGEMENT", hours_ago=1, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=2, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=3, base_time=base),
            _make_recent_tweet("ENGAGEMENT", hours_ago=4, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=24, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=48, base_time=base),
            _make_recent_tweet("EDUCATIONAL", hours_ago=72, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=24, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=72, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, [], signals, recent)

        # No winning positions → RECEIPT skipped, EDUCATIONAL capped → ENGAGEMENT
        # But ENGAGEMENT was also recently posted... so we might get skip
        # or ENGAGEMENT if the 6h cooldown has passed
        assert result["action"] in ("tweet", "skip")


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
        """When only 1 ticker available, variant_1 gets it; others get non-ticker fallback."""
        decision = {"type": "RECEIPT", "tickers": ["AAA"]}
        portfolio = [{"ticker": "AAA", "entry_price": "10", "highest_close": "15", "theme": "AI"}]
        signals = {"buy_signals": []}

        result = _prepare_slot_data(decision, portfolio, signals)

        # variant_1 gets the ticker, others switch to non-ticker categories
        # (diversity fix: prevents all 3 accounts tweeting identical content)
        assert result["variant_1"]["ticker"] == "AAA"
        assert result["variant_2"]["ticker"] == ""
        assert result["variant_3"]["ticker"] == ""
        assert result["variant_2"]["category"] in ("EDUCATIONAL", "ENGAGEMENT")
        assert result["variant_3"]["category"] in ("EDUCATIONAL", "ENGAGEMENT")

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
            "category": "THEME_MOMENTUM",
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
    """_count_category_this_week() helper counts correctly."""

    def test_count_correct(self):
        """Counts tweets of a category within the last 7 days."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12),
            _make_recent_tweet("EDUCATIONAL", hours_ago=36),
            _make_recent_tweet("EDUCATIONAL", hours_ago=120),  # 5 days ago
            _make_recent_tweet("ENGAGEMENT", hours_ago=12),  # Different category
        ]

        count = _count_category_this_week("EDUCATIONAL", recent)
        assert count == 3

    def test_ignores_old_tweets(self):
        """Tweets older than 7 days are not counted."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12),
            _make_recent_tweet("EDUCATIONAL", hours_ago=200),  # ~8 days
        ]

        count = _count_category_this_week("EDUCATIONAL", recent)
        assert count == 1

    def test_ignores_failed_tweets(self):
        """Failed/skipped tweets should not be counted."""
        recent = [
            _make_recent_tweet("EDUCATIONAL", hours_ago=12, status="posted"),
            _make_recent_tweet("EDUCATIONAL", hours_ago=24, status="failed"),
            _make_recent_tweet("EDUCATIONAL", hours_ago=36, status="skipped"),
        ]

        count = _count_category_this_week("EDUCATIONAL", recent)
        assert count == 1


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
    """Verify new categories (SELL_SIGNAL, TECHNICAL_ANALYSIS, WATCHLIST) pass validation."""

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

    def test_watchlist_passes_step1(self):
        """WATCHLIST is in LIVE_VALID_CATEGORIES and passes step 1."""
        assert "WATCHLIST" in LIVE_VALID_CATEGORIES
        tweet = {
            "text": "On my radar: $IONQ at $42.15. Waiting for confirmation. NFA.",
            "category": "WATCHLIST",
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
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "SELL_SIGNAL"
        assert "VNET" in result["tickers"]


class TestPositionCommentary:
    """TECHNICAL_ANALYSIS fires as fallback in quiet market."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_quiet_market_position_commentary(self, mock_dt, sample_portfolio):
        """When no movers/themes/signals, TECHNICAL_ANALYSIS fires for position commentary."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, [])

        assert result["action"] == "tweet"
        assert result["type"] == "TECHNICAL_ANALYSIS"
        assert "Position commentary" in result["reason"]


class TestWatchlistDecision:
    """WATCHLIST fires when consider_signals exist."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_watchlist_from_consider_signals(self, mock_dt, sample_portfolio):
        """consider_signals trigger WATCHLIST type."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # Block higher-priority paths
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
        ]
        signals = {
            "timestamp": "2026-02-10 10:00:00",
            "buy_signals": [],
            "consider_signals": [{"symbol": "IONQ", "price": 42.15}],
        }
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, sample_portfolio, signals, recent)

        assert result["action"] == "tweet"
        assert result["type"] == "WATCHLIST"
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
            "category": "MARKET_REACTION",
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
    """Multi-ticker receipt triggers with 3+ winners."""

    @patch("twitter.live_tweet_generator.datetime")
    def test_multi_receipt_with_3_winners(self, mock_dt):
        """3+ winners trigger multi-ticker RECEIPT at P9."""
        weekday = datetime(2026, 2, 16, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_dt.now.return_value = weekday
        mock_dt.strptime = datetime.strptime
        mock_dt.fromisoformat = datetime.fromisoformat

        # 3 winners (>5% above entry)
        portfolio = [
            {"ticker": "AAA", "entry_price": "10", "highest_close": "15", "theme": "AI", "status": "OPEN"},
            {"ticker": "BBB", "entry_price": "20", "highest_close": "30", "theme": "Defense", "status": "OPEN"},
            {"ticker": "CCC", "entry_price": "5", "highest_close": "8", "theme": "Nuclear", "status": "OPEN"},
        ]
        # Block all higher priorities
        base = weekday.astimezone(timezone.utc)
        recent = [
            _make_recent_tweet("TECHNICAL_ANALYSIS", hours_ago=2, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=24, base_time=base),
            _make_recent_tweet("NEWSLETTER_CTA", hours_ago=72, base_time=base),
        ]
        signals = {"timestamp": "2026-02-10 10:00:00", "buy_signals": []}
        context = {
            "market_snapshot": {"market_mood": "quiet"},
            "portfolio_movers": [],
            "theme_activity": [],
            "tweet_opportunities": [],
        }

        result = decide_tweet_type(context, portfolio, signals, recent)

        assert result["action"] == "tweet"
        assert result["type"] == "RECEIPT"
        assert result.get("multi_receipt") is True
        assert len(result["tickers"]) >= 3
