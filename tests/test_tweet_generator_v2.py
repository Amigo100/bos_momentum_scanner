#!/usr/bin/env python3
"""
Tests for content/tweet_generator.py (v2)

All 12 tests mock the LLM API — no API key required.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content.models import (
    CHART_REQUIRED_CATEGORIES,
    INTERNAL_TERM_PATTERNS,
    TWEET_CATEGORIES,
    VALID_CATEGORIES,
    ContentData,
    SlotAssignment,
    Tweet,
    ValidationResult,
)
from content.tweet_generator import (
    _build_content_data,
    _generate_tweet,
    _log_failed_tweet,
    _plan_weekly_schedule,
    _prepare_slot_data,
    _repair_tweet,
    _validate_tweet,
    _write_queues,
    ACCOUNT_QUEUES,
    CostTracker,
    MAX_TWEET_CHARS,
    WEEKLY_DAYS,
    WEEKLY_SLOTS,
)
from config.banned_terms import ALL_BANNED, CRITICAL_BANNED


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

def _mock_response(text: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return response


def _sample_signals() -> dict:
    """Return minimal but realistic signals.json data."""
    return {
        "timestamp": "2026-02-06",
        "stats": {
            "tickers_loaded": 1817,
            "technical_signals": 44,
            "final_trade": 3,
        },
        "themes": [
            {"name": "AI Infrastructure", "classification": "PRIME", "composite_score": 8.2},
            {"name": "Nuclear Renaissance", "classification": "INVESTABLE", "composite_score": 7.1},
        ],
        "buy_signals": [
            {"symbol": "NVDA", "price": 142.50, "theme": "AI Infrastructure",
             "catalyst_summary": "Data center CapEx surge", "tier": "TIER1", "conviction": 4},
            {"symbol": "INOD", "price": 61.54, "theme": "Power Grid",
             "catalyst_summary": "Grid modernisation", "tier": "TIER1", "conviction": 4},
            {"symbol": "AMPX", "price": 18.30, "theme": "Nuclear Renaissance",
             "catalyst_summary": "DOE contract", "tier": "TIER2", "conviction": 3},
        ],
        "sell_signals": [
            {"symbol": "VNET", "price": 10.80, "reason": "Weekly BoS Down",
             "entry_price": 12.00, "highest_close": 14.00},
        ],
        "caution_signals": [
            {"symbol": "IONQ", "price": 42.15, "action": "Wait for pullback"},
            {"symbol": "QUBT", "price": 8.90, "action": "Extended move"},
        ],
    }


def _sample_portfolio_csv(tmpdir: Path) -> Path:
    """Write a minimal portfolio.csv and return the path."""
    csv_path = tmpdir / "portfolio.csv"
    csv_path.write_text(
        "ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,current_price\n"
        "RCAT,OPEN,2025-12-29,8.50,,,12.19,Drone Technology,TIER1,TRADE,4,,13.25\n"
        "IBKR,OPEN,2025-12-29,65.00,,,72.93,Financials,TIER1,TRADE,5,,72.00\n"
        "LOSER,OPEN,2025-12-29,20.00,,,20.00,BadTheme,TIER3,TRADE,2,,15.00\n"
    )
    return csv_path


def _sample_content_data() -> ContentData:
    """Return a ContentData with realistic test values."""
    return ContentData(
        pass_signals=_sample_signals()["buy_signals"],
        consider_signals=_sample_signals()["caution_signals"],
        themes=_sample_signals()["themes"],
        scan_stats=_sample_signals()["stats"],
        winners=[
            {"ticker": "RCAT", "entry_price": 8.50, "current_price": 13.25,
             "pnl_pct": 55.9, "theme": "Drone Technology"},
        ],
        holdings=[
            {"ticker": "IBKR", "entry_price": 65.00, "current_price": 72.00,
             "pnl_pct": 10.8, "theme": "Financials"},
        ],
        sell_signals=_sample_signals()["sell_signals"],
        scan_date="2026-02-06",
        newsletter_url="https://sterlingsignals.substack.com",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Tweet contains ticker and price
# ═══════════════════════════════════════════════════════════════════════════════

class TestTweetContainsTickerAndPrice:
    """Generate a SCANNER_RESULT tweet with mock LLM, verify it has $TICKER + price."""

    def test_tweet_contains_ticker_and_price(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            "$NVDA at $142.50 — momentum confirmed in AI Infrastructure. "
            "Data center CapEx surge driving demand. NFA!"
        )

        cost_tracker = CostTracker()
        slot = SlotAssignment(day="saturday", slot=1, category="SCANNER_RESULT", data_key="pass_signals")
        slot_data = {"signals": [{"symbol": "NVDA", "price": 142.50, "theme": "AI Infrastructure",
                                   "catalyst_summary": "Data center CapEx surge"}]}

        tweet = _generate_tweet("SCANNER_RESULT", slot_data, slot, "test guide", mock_client, cost_tracker)

        # Must have at least one $TICKER
        assert re.search(r'\$[A-Z]{2,5}', tweet.text), f"No $TICKER found in: {tweet.text}"
        # Must have a price
        assert re.search(r'\$\d+\.?\d*', tweet.text) or re.search(r'\d+\.?\d*%', tweet.text), \
            f"No price/% found in: {tweet.text}"
        assert tweet.category == "SCANNER_RESULT"
        assert cost_tracker.api_calls == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: No banned phrases pass validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestTweetNoBannedPhrases:
    """Create a tweet containing each banned phrase, verify ALL are caught."""

    def test_tweet_no_banned_phrases(self):
        # Test a representative sample of banned phrases (full list is 100+ items)
        critical_samples = [
            "HMA", "Banker indicator", "BoS", "VWAP", "Gatekeeper",
            "TEAL signal", "UK ISA", "Roth IRA", "conviction score",
            "20% trailing stop", "Beta >= 1.5", "TIER1", "RSI", "MACD",
        ]
        vague_samples = [
            "system keeps working", "trust the process", "stay tuned",
            "some interesting setups", "big news coming",
        ]

        source_data = {"signals": [{"symbol": "NVDA", "price": 100}]}

        for phrase in critical_samples + vague_samples:
            tweet = Tweet(
                text=f"$NVDA at $100. {phrase} is great. NFA!",
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["$NVDA"],
            )
            result = _validate_tweet(tweet, source_data)

            step3_failures = [f for f in result.failures if f.startswith("step3_banned")]
            assert len(step3_failures) > 0, \
                f"Banned phrase '{phrase}' was NOT caught by validation"

    def test_all_banned_caught(self):
        """Every single entry in ALL_BANNED must be caught."""
        source_data = {"signals": [{"symbol": "TEST", "price": 100}]}

        for phrase in ALL_BANNED:
            tweet = Tweet(
                text=f"$TEST at $100. {phrase}. NFA!",
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["$TEST"],
            )
            result = _validate_tweet(tweet, source_data)
            step3_failures = [f for f in result.failures if f.startswith("step3_banned")]
            assert len(step3_failures) > 0, \
                f"ALL_BANNED entry '{phrase}' was NOT caught by validation"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Winners only — losers never appear
# ═══════════════════════════════════════════════════════════════════════════════

class TestTweetWinnersOnly:
    """Provide portfolio with winners and losers, verify losers never appear."""

    def test_tweet_winners_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            csv_path = _sample_portfolio_csv(tmpdir)

            positions = []
            import csv
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key in ("entry_price", "current_price", "highest_close"):
                        if row.get(key):
                            row[key] = float(row[key])
                    positions.append(row)

            signals = _sample_signals()
            data = _build_content_data(signals, positions)

            # LOSER has entry=20.00, current=15.00 → -25% — must be excluded
            all_tickers_in_data = set()
            for w in data.winners:
                all_tickers_in_data.add(w.get("ticker", ""))
            for h in data.holdings:
                all_tickers_in_data.add(h.get("ticker", ""))

            assert "LOSER" not in all_tickers_in_data, \
                "Losing position should be excluded from content data"
            assert "RCAT" in all_tickers_in_data, \
                "RCAT (55.9% winner) should be in winners"

    def test_negative_pct_fails_validation(self):
        """A tweet with negative percentage should fail step 4."""
        tweet = Tweet(
            text="$LOSER from $20 to $15 (-25%). Tough week. NFA!",
            category="PERFORMANCE",
            chart_required=True,
            tickers_mentioned=["$LOSER"],
        )
        result = _validate_tweet(tweet, {"winners": [{"ticker": "LOSER", "entry_price": 20}]})

        step4_failures = [f for f in result.failures if f.startswith("step4_")]
        assert len(step4_failures) > 0, "Negative percentage should be caught by winners-only check"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: No internal terminology
# ═══════════════════════════════════════════════════════════════════════════════

class TestTweetNoInternalTerminology:
    """Create tweets with internal terms, verify all are caught."""

    def test_tweet_no_internal_terminology(self):
        internal_terms = [
            ("HMA just triggered on $NVDA at $100", "HMA"),
            ("BoS confirmed bullish on $NVDA at $100", "BoS"),
            ("Banker score above 55 for $NVDA at $100", "Banker"),
            ("$NVDA is TIER1 at $100", "TIER1"),
            ("Conviction 5 on $NVDA at $100", "conviction"),
            ("VWAP deviation on $NVDA at $100", "VWAP"),
            ("Gate 3 cleared for $NVDA at $100", "gate"),
            ("RSI showing oversold on $NVDA at $100", "RSI"),
            ("MACD crossover on $NVDA at $100", "MACD"),
            ("KDJ golden cross on $NVDA at $100", "KDJ"),
            ("5-gate pipeline filtered $NVDA at $100", "5-gate"),
            ("Gatekeeper approved $NVDA at $100", "gatekeeper"),
        ]

        source_data = {"signals": [{"symbol": "NVDA", "price": 100}]}

        for text, term_label in internal_terms:
            tweet = Tweet(
                text=text,
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["$NVDA"],
            )
            result = _validate_tweet(tweet, source_data)
            step5_failures = [f for f in result.failures if f.startswith("step5_internal")]
            assert len(step5_failures) > 0, \
                f"Internal term '{term_label}' in '{text}' was NOT caught"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Category required elements
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryRequiredElements:
    """For each category with required elements, verify validation catches missing ones."""

    def test_category_required_elements(self):
        source_data = {}  # Empty source — focusing on element presence

        # Tweets missing required elements for their category
        missing_cases = [
            # SCANNER_RESULT needs $TICKER + price
            ("SCANNER_RESULT", "Momentum confirmed in AI sector. Great setup today!", True),
            # PERFORMANCE needs $TICKER + price + % gain
            ("PERFORMANCE", "What a week for the portfolio. Winners everywhere!", True),
            # SELL_SIGNAL needs $TICKER + invalidation framing
            ("SELL_SIGNAL", "We got stopped out today. Losses happen.", True),
            # DAILY_SIGNAL needs $TICKER + price
            ("DAILY_SIGNAL", "New daily buy signal detected in the tech sector!", True),
            # TECHNICAL_ANALYSIS needs $TICKER + level
            ("TECHNICAL_ANALYSIS", "Key levels being watched across the board.", True),
        ]

        for category, text, chart_req in missing_cases:
            tweet = Tweet(
                text=text,
                category=category,
                chart_required=chart_req,
                tickers_mentioned=[],
            )
            result = _validate_tweet(tweet, source_data)
            step1_failures = [f for f in result.failures if f.startswith("step1_category")]
            assert len(step1_failures) > 0, \
                f"Category '{category}' should fail on missing elements for: '{text}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Uniform voice — all accounts get identical content
# ═══════════════════════════════════════════════════════════════════════════════

class TestUniformVoiceAllAccounts:
    """Generate content, verify all 3 queue files contain identical tweet text."""

    def test_uniform_voice_all_accounts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            tweets = [
                Tweet(
                    text="$NVDA at $142.50 — momentum confirmed. NFA!",
                    category="SCANNER_RESULT",
                    chart_required=True,
                    tickers_mentioned=["$NVDA"],
                    metadata={"day": "saturday", "slot": 1, "data_key": "pass_signals"},
                ),
                Tweet(
                    text="$RCAT from $8.50 to $13.25 (+55.9%). Drone tech delivering. NFA!",
                    category="PERFORMANCE",
                    chart_required=True,
                    tickers_mentioned=["$RCAT"],
                    metadata={"day": "saturday", "slot": 2, "data_key": "winners"},
                ),
            ]

            _write_queues(tweets, ACCOUNT_QUEUES, tmpdir, "2026-02-06")

            # Read all 3 queue files
            queues = {}
            for account_id, queue_file in ACCOUNT_QUEUES.items():
                path = tmpdir / queue_file
                assert path.exists(), f"Queue file missing: {path}"
                with open(path) as f:
                    queues[account_id] = json.load(f)

            # All queues must have same number of tweets
            assert len(queues["main"]) == len(queues["account2"]) == len(queues["account3"])

            # Tweet text must be IDENTICAL across all accounts
            for i in range(len(queues["main"])):
                main_text = queues["main"][i]["text"]
                acc2_text = queues["account2"][i]["text"]
                acc3_text = queues["account3"][i]["text"]
                assert main_text == acc2_text == acc3_text, \
                    f"Tweet {i} text differs across accounts"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Chart flag set correctly
# ═══════════════════════════════════════════════════════════════════════════════

class TestChartFlagSetCorrectly:
    """Verify chart_required matches the style guide category table."""

    def test_chart_flag_set_correctly(self):
        # Categories that REQUIRE charts
        required = {"SCANNER_RESULT", "DAILY_SIGNAL", "PERFORMANCE",
                     "TECHNICAL_ANALYSIS", "SELL_SIGNAL"}

        # Categories that do NOT require charts
        not_required = {"THEME_ANALYSIS", "WATCHLIST", "EDUCATIONAL",
                        "MARKET_COMMENTARY", "ENGAGEMENT", "NEWSLETTER_CTA"}

        # Verify against CHART_REQUIRED_CATEGORIES
        assert CHART_REQUIRED_CATEGORIES == required, \
            f"Chart required mismatch: {CHART_REQUIRED_CATEGORIES} != {required}"

        # Verify a tweet's chart_required is set correctly
        for cat in required:
            tweet = Tweet(text="test", category=cat, chart_required=True)
            result = _validate_tweet(tweet, {})
            chart_failures = [f for f in result.failures if f.startswith("step7_chart")]
            assert len(chart_failures) == 0, \
                f"{cat} with chart_required=True should pass step 7"

        for cat in not_required:
            tweet = Tweet(text="test", category=cat, chart_required=False)
            result = _validate_tweet(tweet, {})
            chart_failures = [f for f in result.failures if f.startswith("step7_chart")]
            assert len(chart_failures) == 0, \
                f"{cat} with chart_required=False should pass step 7"

        # Verify wrong flag is caught
        tweet_wrong = Tweet(text="test", category="ENGAGEMENT", chart_required=True)
        result = _validate_tweet(tweet_wrong, {})
        chart_failures = [f for f in result.failures if f.startswith("step7_chart")]
        assert len(chart_failures) > 0, "ENGAGEMENT with chart_required=True should fail step 7"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Sell signal tweet — no loss amount
# ═══════════════════════════════════════════════════════════════════════════════

class TestSellSignalTweetNoLossAmount:
    """Generate a SELL_SIGNAL tweet, verify NO negative percentage appears."""

    def test_sell_signal_tweet_no_loss_amount(self):
        # A sell signal tweet with a negative percentage should fail validation
        tweet_bad = Tweet(
            text="$VNET setup invalidated below $10.80. Lost -15% on this one. Moving on.",
            category="SELL_SIGNAL",
            chart_required=True,
            tickers_mentioned=["$VNET"],
        )
        result = _validate_tweet(tweet_bad, {"sell_signals": [{"symbol": "VNET"}]})
        step4_failures = [f for f in result.failures if f.startswith("step4_")]
        assert len(step4_failures) > 0, "Sell signal with -15% should fail winners-only check"

        # A properly framed sell signal should pass step 4
        tweet_good = Tweet(
            text="$VNET setup invalidated below $10.80. Win more than you lose. NFA!",
            category="SELL_SIGNAL",
            chart_required=True,
            tickers_mentioned=["$VNET"],
        )
        result_good = _validate_tweet(tweet_good, {"sell_signals": [{"symbol": "VNET"}]})
        step4_failures_good = [f for f in result_good.failures if f.startswith("step4_")]
        assert len(step4_failures_good) == 0, \
            f"Clean sell signal should pass step 4, but got: {step4_failures_good}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: Data injection accuracy
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataInjectionAccuracy:
    """Verify every $TICKER in output matches source data exactly."""

    def test_data_injection_accuracy(self):
        source_data = {
            "signals": [
                {"symbol": "NVDA", "price": 142.50, "theme": "AI"},
                {"symbol": "INOD", "price": 61.54, "theme": "Power Grid"},
            ],
        }

        # A tweet that only mentions source tickers should pass
        tweet_valid = Tweet(
            text="$NVDA at $142.50 and $INOD at $61.54 — both cleared all gates. NFA!",
            category="SCANNER_RESULT",
            chart_required=True,
            tickers_mentioned=["$NVDA", "$INOD"],
        )
        result = _validate_tweet(tweet_valid, source_data)
        step2_failures = [f for f in result.failures if f.startswith("step2_ticker")]
        assert len(step2_failures) == 0, \
            f"Valid tickers should pass step 2, but got: {step2_failures}"

        # A tweet mentioning a fabricated ticker should fail
        tweet_fabricated = Tweet(
            text="$NVDA at $142.50 and $FAKE at $99.00 — both looking strong. NFA!",
            category="SCANNER_RESULT",
            chart_required=True,
            tickers_mentioned=["$NVDA", "$FAKE"],
        )
        result_bad = _validate_tweet(tweet_fabricated, source_data)
        step2_failures_bad = [f for f in result_bad.failures if f.startswith("step2_ticker")]
        assert len(step2_failures_bad) > 0, \
            "Fabricated ticker $FAKE should be caught by step 2"
        assert "FAKE" in str(step2_failures_bad), "Failure should identify $FAKE"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: Validation → repair flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationRepairFlow:
    """Mock LLM: first call returns banned phrase, second call returns clean tweet."""

    def test_validation_repair_flow(self):
        mock_client = MagicMock()

        # First call returns tweet with banned phrase
        bad_response = _mock_response(
            "$NVDA at $142.50. Trust the process, the system keeps working!"
        )
        # Second call (repair) returns clean tweet
        good_response = _mock_response(
            "$NVDA at $142.50 — momentum confirmed in AI Infrastructure. NFA!"
        )
        mock_client.messages.create.side_effect = [bad_response, good_response]

        cost_tracker = CostTracker()
        slot = SlotAssignment(day="saturday", slot=1, category="SCANNER_RESULT", data_key="pass_signals")
        source_data = {"signals": [{"symbol": "NVDA", "price": 142.50, "theme": "AI"}]}

        # Generate initial (bad) tweet
        tweet = _generate_tweet("SCANNER_RESULT", source_data, slot, "test", mock_client, cost_tracker)
        result = _validate_tweet(tweet, source_data)

        assert not result.passed, "First tweet should fail (has banned phrases)"
        assert any("trust the process" in f.lower() for f in result.failures), \
            "'trust the process' should be flagged"

        # Repair
        repaired = _repair_tweet(tweet, result.failures, source_data, "test", mock_client, cost_tracker)
        result2 = _validate_tweet(repaired, source_data)

        assert result2.passed, f"Repaired tweet should pass validation, failures: {result2.failures}"
        assert cost_tracker.api_calls == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: Max repair attempts → drop
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationMaxRepairAttempts:
    """Mock LLM to always return banned phrases → tweet should be dropped."""

    def test_validation_max_repair_attempts(self):
        mock_client = MagicMock()
        # All responses contain banned phrases
        bad_response = _mock_response(
            "$NVDA at $142.50. The system keeps working, trust the process!"
        )
        mock_client.messages.create.return_value = bad_response

        cost_tracker = CostTracker()
        slot = SlotAssignment(day="saturday", slot=1, category="SCANNER_RESULT", data_key="pass_signals")
        source_data = {"signals": [{"symbol": "NVDA", "price": 142.50, "theme": "AI"}]}

        # Generate + attempt repairs
        tweet = _generate_tweet("SCANNER_RESULT", source_data, slot, "test", mock_client, cost_tracker)
        result = _validate_tweet(tweet, source_data)

        repair_attempts = 0
        while not result.passed and repair_attempts < 2:
            tweet = _repair_tweet(tweet, result.failures, source_data, "test", mock_client, cost_tracker)
            result = _validate_tweet(tweet, source_data)
            repair_attempts += 1

        # Should still fail after 2 repair attempts
        assert not result.passed, "Tweet should still fail after max repairs"
        assert repair_attempts == 2
        # 1 generate + 2 repairs = 3 API calls
        assert cost_tracker.api_calls == 3

        # Log the failed tweet
        with tempfile.TemporaryDirectory() as tmpdir:
            _log_failed_tweet(tweet, result.failures, Path(tmpdir))
            failed_path = Path(tmpdir) / "failed_tweets.json"
            assert failed_path.exists(), "failed_tweets.json should be created"

            with open(failed_path) as f:
                failed = json.load(f)
            assert len(failed) == 1
            assert failed[0]["category"] == "SCANNER_RESULT"
            assert len(failed[0]["failures"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: Weekly schedule category rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeeklyScheduleCategoryRules:
    """Verify schedule planning obeys PRD section 4.1.3 rules."""

    def test_performance_at_least_one_per_day_when_winners_exist(self):
        """PERFORMANCE receipts: at least 1/day when winners exist."""
        data = _sample_content_data()
        assert data.has_winners, "Test data should have winners"

        schedule = _plan_weekly_schedule(data)

        for day in WEEKLY_DAYS:
            day_assignments = [s for s in schedule if s.day == day]
            perf_count = sum(1 for s in day_assignments if s.category == "PERFORMANCE")
            assert perf_count >= 1, \
                f"Day '{day}' has {perf_count} PERFORMANCE tweets (need >= 1 when winners exist)"

    def test_scanner_result_on_saturday(self):
        """SCANNER_RESULT should appear on Saturday (day after weekly scan)."""
        data = _sample_content_data()
        schedule = _plan_weekly_schedule(data)

        sat_assignments = [s for s in schedule if s.day == "saturday"]
        scanner_on_sat = sum(1 for s in sat_assignments if s.category == "SCANNER_RESULT")
        assert scanner_on_sat >= 1, \
            f"Saturday should have at least 1 SCANNER_RESULT, got {scanner_on_sat}"

    def test_theme_analysis_at_least_2_per_week(self):
        """THEME_ANALYSIS: at least 2/week."""
        data = _sample_content_data()
        schedule = _plan_weekly_schedule(data)

        theme_count = sum(1 for s in schedule if s.category == "THEME_ANALYSIS")
        assert theme_count >= 2, \
            f"Week should have at least 2 THEME_ANALYSIS, got {theme_count}"

    def test_engagement_max_one_per_day(self):
        """ENGAGEMENT: max 1/day."""
        data = _sample_content_data()
        schedule = _plan_weekly_schedule(data)

        for day in WEEKLY_DAYS:
            day_assignments = [s for s in schedule if s.day == day]
            eng_count = sum(1 for s in day_assignments if s.category == "ENGAGEMENT")
            assert eng_count <= 1, \
                f"Day '{day}' has {eng_count} ENGAGEMENT tweets (max 1)"

    def test_newsletter_cta_max_2_per_week(self):
        """NEWSLETTER_CTA: max 2/week."""
        data = _sample_content_data()
        schedule = _plan_weekly_schedule(data)

        cta_count = sum(1 for s in schedule if s.category == "NEWSLETTER_CTA")
        assert cta_count <= 2, \
            f"Week has {cta_count} NEWSLETTER_CTA tweets (max 2)"

    def test_no_winners_schedule(self):
        """When no winners exist, PERFORMANCE should not be assigned."""
        data = ContentData(
            pass_signals=_sample_signals()["buy_signals"],
            themes=_sample_signals()["themes"],
            scan_date="2026-02-06",
        )
        assert not data.has_winners

        schedule = _plan_weekly_schedule(data)

        perf_count = sum(1 for s in schedule if s.category == "PERFORMANCE")
        # Without winners, PERFORMANCE is not strictly required
        # (the scheduler only assigns it when data.has_winners)
        # But if it does appear, it should be 0 since there are no winners
        assert perf_count == 0, \
            f"Should have 0 PERFORMANCE without winners, got {perf_count}"

    def test_all_assignments_valid_categories(self):
        """Every slot assignment should have a valid category."""
        data = _sample_content_data()
        schedule = _plan_weekly_schedule(data)

        assert len(schedule) == len(WEEKLY_DAYS) * len(WEEKLY_SLOTS), \
            f"Schedule should have {len(WEEKLY_DAYS) * len(WEEKLY_SLOTS)} slots, got {len(schedule)}"

        for s in schedule:
            assert s.category in VALID_CATEGORIES, \
                f"Invalid category '{s.category}' in schedule"
