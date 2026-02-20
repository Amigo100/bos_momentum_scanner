#!/usr/bin/env python3
"""
Tests for tweet generation audit fixes (Phase 4A.9).

Tests 1-10 (Phase A):
  [4A.1.1] _prepare_slot_data exhaustion + flexible-category behavior
  [4A.1.2] Generation loop skips None slots
  [4A.1.3] _validate_tweet meta-language detection
  [4A.1.4] _validate_tweet fabrication checks + flexible-category skip
  [4A.1.5] _write_queues chart-required drop logic
  [4A.2.1-2] _build_content_data notable_holdings population
  [4A.2.3] _pick_category PERFORMANCE with notable_holdings only

Tests 11-26 (Phase B+C):
  [4A.3] Schedule planning: fallback chains, repetition limits
  [4A.4] Overexposure: no scanner tickers in EDUCATIONAL/ENGAGEMENT
  [4A.5] Diversity: recent_openings injection
  [4A.6] New categories: WATCHLIST, NEWSLETTER_CTA, TECHNICAL_ANALYSIS
  [4A.7] Charts, temporal, routing: funnel fallback, year-end Q1, slot 1
  [4A.8] Style: category examples, style guide token limit

All 26 tests are pure unit tests — no LLM calls required.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest

try:
    from twitter.models import (
        ContentData,
        Tweet,
        ValidationResult,
        SlotAssignment,
        CHART_REQUIRED_CATEGORIES,
        VALID_CATEGORIES,
    )
    from twitter.tweet_generator import (
        _build_content_data,
        _prepare_slot_data,
        _validate_tweet,
        _write_queues,
        _pick_category,
        _build_user_prompt,
        _attach_chart_paths,
        _plan_weekly_schedule,
        _within_limits,
        ACCOUNT_QUEUES,
        WEEKLY_DAYS,
        WEEKLY_SLOTS,
        DATA_DEPENDENT_CATEGORIES,
        NOTABLE_WIN_THRESHOLD,
        CATEGORY_WEEKLY_LIMITS,
        CATEGORY_EXAMPLES,
        EMBEDDED_STYLE_GUIDE,
        MAX_SAME_CATEGORY_PER_DAY,
    )
    _IMPORTS_OK = True
except ImportError:
    _IMPORTS_OK = False

skipif_no_imports = pytest.mark.skipif(
    not _IMPORTS_OK,
    reason="twitter.models or twitter.tweet_generator not importable",
)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _empty_content_data(**overrides) -> "ContentData":
    """Return a ContentData with all lists empty, applying any overrides."""
    defaults = dict(
        pass_signals=[],
        consider_signals=[],
        themes=[],
        scan_stats={},
        winners=[],
        notable_holdings=[],
        holdings=[],
        sell_signals=[],
        scan_date="2026-02-07",
        newsletter_url="https://sterlingsignals.substack.com",
    )
    defaults.update(overrides)
    return ContentData(**defaults)


def _make_tweet(text, category, chart_required=False, chart_path=None,
                tickers=None, metadata=None):
    """Convenience factory for Tweet objects."""
    return Tweet(
        text=text,
        category=category,
        chart_required=chart_required,
        tickers_mentioned=tickers or [],
        chart_path=chart_path,
        metadata=metadata or {},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — [4A.9.1] _prepare_slot_data returns None when exhausted
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestPrepareSlotDataExhaustion:
    """_prepare_slot_data returns None when data-dependent categories run out."""

    def test_prepare_slot_data_returns_none_when_exhausted(self):
        data = _empty_content_data(
            sell_signals=[
                {"symbol": "LUMN", "price": 5.20, "reason": "Weekly BoS Down",
                 "entry_price": 6.00, "highest_close": 7.00},
            ],
        )
        used = {}

        # First call: should return a dict with sell_signals key
        result1 = _prepare_slot_data("SELL_SIGNAL", data, used)
        assert result1 is not None, "First SELL_SIGNAL call should return data"
        assert "sell_signals" in result1

        # Second call: data exhausted, should return None
        result2 = _prepare_slot_data("SELL_SIGNAL", data, used)
        assert result2 is None, "Second SELL_SIGNAL call should return None (exhausted)"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 — [4A.9.2] Flexible categories always return a dict
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestPrepareSlotDataFlexible:
    """Flexible categories (EDUCATIONAL, ENGAGEMENT, NEWSLETTER_CTA) never return None."""

    def test_prepare_slot_data_returns_dict_for_flexible_categories(self):
        data = _empty_content_data()  # Everything empty
        used = {}

        for category in ("EDUCATIONAL", "ENGAGEMENT", "NEWSLETTER_CTA"):
            result = _prepare_slot_data(category, data, used)
            assert result is not None, f"{category} should always return a dict, got None"
            assert isinstance(result, dict), f"{category} should return dict, got {type(result)}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 — [4A.9.3] Generation loop skips None slots
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestGenerationLoopSkipsNone:
    """When _prepare_slot_data returns None, the loop should skip that slot."""

    def test_generation_loop_skips_none_slots(self):
        # 4-slot fake schedule: 2x SELL_SIGNAL, 1x EDUCATIONAL, 1x ENGAGEMENT
        fake_schedule = [
            SlotAssignment(day="saturday", slot=2, category="SELL_SIGNAL", data_key="sell_signals"),
            SlotAssignment(day="saturday", slot=3, category="SELL_SIGNAL", data_key="sell_signals"),
            SlotAssignment(day="saturday", slot=4, category="EDUCATIONAL", data_key="educational"),
            SlotAssignment(day="saturday", slot=5, category="ENGAGEMENT", data_key="engagement"),
        ]

        data = _empty_content_data(
            sell_signals=[
                {"symbol": "VNET", "price": 10.80, "reason": "Weekly BoS Down",
                 "entry_price": 12.00, "highest_close": 14.00},
            ],
        )

        used_indices = {}
        slots_with_data = 0
        slots_skipped = 0

        for assignment in fake_schedule:
            slot_data = _prepare_slot_data(assignment.category, data, used_indices)
            if slot_data is None:
                slots_skipped += 1
                continue
            slots_with_data += 1

        # 1 SELL_SIGNAL has data, 1 exhausted, 2 flexible always have data
        assert slots_with_data == 3, f"Expected 3 slots with data, got {slots_with_data}"
        assert slots_skipped == 1, f"Expected 1 skipped slot, got {slots_skipped}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 — [4A.9.4] _validate_tweet catches meta-language
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestValidateMetaLanguage:
    """Step 2a: meta-language detection catches LLM placeholder/refusal text."""

    def test_validate_catches_meta_language(self):
        tweet = _make_tweet(
            text=(
                "Cannot generate SELL_SIGNAL tweet without ticker data. "
                "Please provide specific $TICKER information."
            ),
            category="SELL_SIGNAL",
            chart_required=True,
        )
        source_data = {"sell_signals": [{"symbol": "LUMN"}]}

        result = _validate_tweet(tweet, source_data)

        assert not result.passed, "Meta-language tweet should fail validation"
        meta_failures = [f for f in result.failures if "step2_meta" in f]
        assert len(meta_failures) > 0, (
            f"Should have step2_meta failures, got: {result.failures}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 5-6 — [4A.9.5-6] Fabricated vs real ticker validation
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestValidateFabricatedTickers:
    """Step 2b: data-dependent categories catch fabricated tickers; real tickers pass."""

    def test_validate_catches_fabricated_tickers(self):
        tweet = _make_tweet(
            text="$NVDA showing momentum at $850. Institutional accumulation confirmed. NFA!",
            category="SCANNER_RESULT",
            chart_required=True,
        )
        source_data = {"signals": [{"symbol": "MATV"}]}
        allowed_tickers = {"MATV", "LUMN"}

        result = _validate_tweet(tweet, source_data, allowed_tickers=allowed_tickers)

        fab_failures = [f for f in result.failures if "step2_fabrication" in f]
        assert len(fab_failures) > 0, (
            f"Should catch fabricated $NVDA, got: {result.failures}"
        )
        assert any("NVDA" in f for f in fab_failures), "Failure should name NVDA"

    def test_validate_allows_real_tickers(self):
        tweet = _make_tweet(
            text="$MATV at $22.50 — momentum confirmed. Structural trend confirmation. NFA!",
            category="SCANNER_RESULT",
            chart_required=True,
        )
        source_data = {"signals": [{"symbol": "MATV"}]}
        allowed_tickers = {"MATV", "LUMN"}

        result = _validate_tweet(tweet, source_data, allowed_tickers=allowed_tickers)

        ticker_failures = [f for f in result.failures
                           if "step2_fabrication" in f or "step2_ticker" in f]
        assert len(ticker_failures) == 0, (
            f"Real ticker $MATV should pass, but got: {ticker_failures}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7 — [4A.9.7] Flexible categories skip ticker fabrication checks
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestValidateFlexibleCategoryTickers:
    """Flexible categories skip ticker fabrication checks when source_tickers is empty."""

    def test_validate_skips_ticker_check_for_flexible_categories(self):
        tweet = _make_tweet(
            text="$AAPL discipline in action. Momentum builds over time. NFA!",
            category="EDUCATIONAL",
            chart_required=False,
        )
        source_data = {}  # Empty — no source tickers
        allowed_tickers = {"MATV"}

        result = _validate_tweet(tweet, source_data, allowed_tickers=allowed_tickers)

        fab_failures = [f for f in result.failures if "step2_fabrication" in f]
        assert len(fab_failures) == 0, (
            f"Flexible category EDUCATIONAL should not trigger fabrication check, "
            f"got: {fab_failures}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8 — [4A.9.8] _write_queues drops chart-required tweets without chart
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestWriteQueuesChartDrop:
    """_write_queues drops chart-required tweets that have no chart_path."""

    def test_chart_required_tweets_dropped_without_chart(self):
        tweets = [
            _make_tweet(
                text="$NVDA at $850 — momentum confirmed. NFA!",
                category="SCANNER_RESULT",
                chart_required=True,
                chart_path=None,  # Missing chart
                metadata={"day": "saturday", "slot": 2},
            ),
            _make_tweet(
                text="Discipline beats emotion every time. NFA!",
                category="EDUCATIONAL",
                chart_required=False,
                chart_path=None,
                metadata={"day": "saturday", "slot": 5},
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            _write_queues(tweets, ACCOUNT_QUEUES, tmpdir, "2026-02-07")

            # Read the main queue file
            queue_path = tmpdir / ACCOUNT_QUEUES["main"]
            assert queue_path.exists(), f"Queue file should exist: {queue_path}"

            with open(queue_path) as f:
                entries = json.load(f)

            assert len(entries) == 1, (
                f"Expected 1 entry (EDUCATIONAL only), got {len(entries)}"
            )
            assert entries[0]["category"] == "EDUCATIONAL", (
                f"Surviving tweet should be EDUCATIONAL, got {entries[0]['category']}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9 — [4A.9.9] _build_content_data populates notable_holdings
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestBuildContentDataNotableHoldings:
    """_build_content_data correctly splits positions into winners / notable / holdings."""

    def test_notable_holdings_populated(self):
        signals = {
            "timestamp": "2026-02-07",
            "buy_signals": [],
            "caution_signals": [],
            "themes": [],
            "stats": {},
            "sell_signals": [],
        }
        positions = [
            # +30% => winners (entry=10, current=13)
            {"ticker": "WIN", "status": "OPEN", "entry_price": 10.0,
             "current_price": 13.0, "highest_close": 13.0, "theme": "AI"},
            # +15% => notable_holdings (entry=10, current=11.5)
            {"ticker": "NOTE", "status": "OPEN", "entry_price": 10.0,
             "current_price": 11.5, "highest_close": 11.5, "theme": "Nuclear"},
            # +5% => holdings (entry=10, current=10.5)
            {"ticker": "HOLD", "status": "OPEN", "entry_price": 10.0,
             "current_price": 10.5, "highest_close": 10.5, "theme": "Grid"},
            # -10% => SKIPPED (entry=10, current=9.0)
            {"ticker": "LOSE", "status": "OPEN", "entry_price": 10.0,
             "current_price": 9.0, "highest_close": 10.0, "theme": "Bad"},
        ]

        data = _build_content_data(signals, positions)

        assert len(data.winners) == 1, f"Expected 1 winner (>=25%), got {len(data.winners)}"
        assert data.winners[0]["ticker"] == "WIN"

        assert len(data.notable_holdings) == 1, (
            f"Expected 1 notable (>=10%, <25%), got {len(data.notable_holdings)}"
        )
        assert data.notable_holdings[0]["ticker"] == "NOTE"

        assert len(data.holdings) == 1, (
            f"Expected 1 holding (>=0%, <10%), got {len(data.holdings)}"
        )
        assert data.holdings[0]["ticker"] == "HOLD"

        # Losers should be excluded entirely
        all_tickers = (
            [w["ticker"] for w in data.winners]
            + [n["ticker"] for n in data.notable_holdings]
            + [h["ticker"] for h in data.holdings]
        )
        assert "LOSE" not in all_tickers, "Losers should be excluded from all content data"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10 — [4A.9.10] _pick_category assigns PERFORMANCE with notable only
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestPickCategoryNotableHoldings:
    """_pick_category assigns PERFORMANCE when notable_holdings exist but winners is empty."""

    def test_performance_assigned_with_notable_only(self):
        data = _empty_content_data(
            notable_holdings=[
                {"ticker": "NOTE", "entry_price": 10.0, "current_price": 11.5,
                 "pnl_pct": 15.0, "theme": "Nuclear"},
            ],
        )

        # Verify properties
        assert data.has_notable_holdings is True
        assert data.has_winners is False

        # Call _pick_category with slot=2, day_performance_placed=False
        # Use day="monday" to avoid Saturday-specific rules
        category, data_key = _pick_category(
            day="monday",
            slot=2,
            data=data,
            day_engagement_used=False,
            day_performance_placed=False,
            newsletter_cta_count=0,
            theme_count=0,
            schedule=[],
        )

        assert category == "PERFORMANCE", f"Expected PERFORMANCE, got {category}"
        assert data_key == "winners", f"Expected data_key='winners', got {data_key}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 11-13 — Schedule Planning [4A.3]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestPickCategoryFallbacks:
    """_pick_category falls back when data is missing or exhausted."""

    def test_pick_category_falls_back_when_no_sells(self):
        """No sell signals → SELL_SIGNAL never assigned."""
        data = _empty_content_data(sell_signals=[])

        category, _ = _pick_category(
            day="wednesday",
            slot=3,
            data=data,
            day_engagement_used=False,
            day_performance_placed=False,
            newsletter_cta_count=0,
            theme_count=0,
            schedule=[],
        )

        assert category != "SELL_SIGNAL", (
            f"Expected fallback away from SELL_SIGNAL (no data), got {category}"
        )

    def test_pick_category_falls_back_when_signals_exhausted(self):
        """1 pass_signal already consumed → SCANNER_RESULT not assigned."""
        data = _empty_content_data(
            pass_signals=[
                {"symbol": "INOD", "price": 61.54, "theme": "AI"},
            ],
        )

        category, _ = _pick_category(
            day="saturday",
            slot=2,
            data=data,
            day_engagement_used=False,
            day_performance_placed=False,
            newsletter_cta_count=0,
            theme_count=0,
            schedule=[],
            planned_counts={"pass_signals": 1},  # Already consumed
        )

        assert category != "SCANNER_RESULT", (
            f"Expected fallback (signal exhausted), got {category}"
        )


@skipif_no_imports
class TestCategoryRepetitionLimits:
    """_within_limits enforces weekly and daily caps."""

    def test_category_repetition_limits(self):
        # Weekly limit: EDUCATIONAL max 3 → at 3, blocked
        assert _within_limits(
            "EDUCATIONAL",
            week_counts={"EDUCATIONAL": 3},
            day_counts={},
        ) is False, "EDUCATIONAL at 3/week should be blocked"

        # At 2 → still allowed
        assert _within_limits(
            "EDUCATIONAL",
            week_counts={"EDUCATIONAL": 2},
            day_counts={},
        ) is True, "EDUCATIONAL at 2/week should be allowed"

        # Daily limit: any category at MAX_SAME_CATEGORY_PER_DAY (2) → blocked
        assert _within_limits(
            "EDUCATIONAL",
            week_counts={},
            day_counts={"EDUCATIONAL": MAX_SAME_CATEGORY_PER_DAY},
        ) is False, "EDUCATIONAL at daily max should be blocked"

        # Category not in CATEGORY_WEEKLY_LIMITS → uses default 999
        assert _within_limits(
            "SCANNER_RESULT",
            week_counts={"SCANNER_RESULT": 10},
            day_counts={},
        ) is True, "Unlimited category should always pass weekly check"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 14-15 — Overexposure Prevention [4A.4]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestNoScannerTickersInFlexible:
    """EDUCATIONAL and ENGAGEMENT slot_data must not contain scanner tickers."""

    def test_educational_prompt_has_no_scanner_tickers(self):
        """EDUCATIONAL slot_data has no 'tickers' key; prompt has no $TICKER in data."""
        data = _empty_content_data(
            pass_signals=[
                {"symbol": "MATV", "price": 22.50, "theme": "AI"},
                {"symbol": "LUMN", "price": 5.20, "theme": "Telecom"},
            ],
            themes=[{"name": "AI Infrastructure", "classification": "PRIME"}],
        )

        slot_data = _prepare_slot_data("EDUCATIONAL", data, {})
        assert slot_data is not None
        assert "tickers" not in slot_data, (
            "EDUCATIONAL slot_data should not contain 'tickers' key"
        )
        assert "signals" not in slot_data, (
            "EDUCATIONAL slot_data should not contain 'signals' key"
        )

        # Build prompt and check no scanner tickers leaked
        slot = SlotAssignment(day="monday", slot=3, category="EDUCATIONAL", data_key="educational")
        prompt = _build_user_prompt("EDUCATIONAL", slot_data, slot)

        # The DATA section should not contain $MATV or $LUMN
        assert "$MATV" not in prompt, "Scanner ticker $MATV leaked into EDUCATIONAL prompt"
        assert "$LUMN" not in prompt, "Scanner ticker $LUMN leaked into EDUCATIONAL prompt"

    def test_engagement_prompt_has_no_ticker_data(self):
        """ENGAGEMENT slot_data has no 'tickers' or 'signals' key."""
        data = _empty_content_data(
            pass_signals=[
                {"symbol": "MATV", "price": 22.50, "theme": "AI"},
            ],
        )

        slot_data = _prepare_slot_data("ENGAGEMENT", data, {})
        assert slot_data is not None
        assert "tickers" not in slot_data, (
            "ENGAGEMENT slot_data should not contain 'tickers' key"
        )
        assert "signals" not in slot_data, (
            "ENGAGEMENT slot_data should not contain 'signals' key"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 16 — Diversity Tracking [4A.5]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestDiversityTracking:
    """recent_openings are injected into user prompts."""

    def test_diversity_tracking_injects_previous_openings(self):
        slot_data = {"context": "trading methodology"}
        slot = SlotAssignment(
            day="tuesday", slot=3, category="EDUCATIONAL", data_key="educational"
        )

        prompt = _build_user_prompt(
            "EDUCATIONAL",
            slot_data,
            slot,
            recent_openings=["The scanner", "This week"],
        )

        assert "DO NOT start" in prompt, (
            "Diversity constraint should be injected when recent_openings provided"
        )
        assert "The scanner" in prompt, "Opening 'The scanner' should appear in constraint"
        assert "This week" in prompt, "Opening 'This week' should appear in constraint"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 17-19 — New Categories [4A.6]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestNewCategories:
    """Newly activated categories: WATCHLIST, NEWSLETTER_CTA, TECHNICAL_ANALYSIS."""

    def test_watchlist_uses_consider_signals(self):
        """WATCHLIST assigned when consider_signals available in slot 4."""
        data = _empty_content_data(
            consider_signals=[
                {"symbol": "IONQ", "price": 42.15, "theme": "Quantum",
                 "action": "momentum confirmation"},
            ],
        )

        category, data_key = _pick_category(
            day="monday",
            slot=4,
            data=data,
            day_engagement_used=False,
            day_performance_placed=True,  # Already placed PERFORMANCE
            newsletter_cta_count=0,
            theme_count=2,
            schedule=[],
        )

        assert category == "WATCHLIST", f"Expected WATCHLIST for slot 4 with consider data, got {category}"

    def test_newsletter_cta_max_2_per_week(self):
        """NEWSLETTER_CTA not assigned when count already at 2."""
        data = _empty_content_data(
            newsletter_url="https://sterlingsignals.substack.com",
        )

        category, _ = _pick_category(
            day="sunday",
            slot=5,
            data=data,
            day_engagement_used=False,
            day_performance_placed=False,
            newsletter_cta_count=2,  # Already at max
            theme_count=0,
            schedule=[],
        )

        assert category != "NEWSLETTER_CTA", (
            f"NEWSLETTER_CTA at max 2/week should not be assigned, got {category}"
        )

    def test_technical_analysis_no_chart_required(self):
        """TECHNICAL_ANALYSIS is NOT in CHART_REQUIRED_CATEGORIES (text-only TA acceptable)."""
        assert "TECHNICAL_ANALYSIS" not in CHART_REQUIRED_CATEGORIES, (
            "TECHNICAL_ANALYSIS should NOT be in CHART_REQUIRED_CATEGORIES"
        )

        # A TA tweet with chart_required=False should pass step7
        tweet = _make_tweet(
            text="$RCAT holding above $12.00 support. Easy invalidation below $10.50. NFA!",
            category="TECHNICAL_ANALYSIS",
            chart_required=False,  # Correct — text-only TA is acceptable
            tickers=["RCAT"],
        )
        source_data = {"tickers": [{"symbol": "RCAT"}]}

        result = _validate_tweet(tweet, source_data)
        chart_failures = [f for f in result.failures if "step7_chart" in f]
        assert len(chart_failures) == 0, (
            f"TA tweet with chart_required=False should pass step7, got: {result.failures}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 20-21 — Chart Fallback [4A.7.1]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestChartFallback:
    """Funnel graphic fallback for SCANNER_RESULT/THEME_ANALYSIS only."""

    def test_chart_fallback_uses_funnel_for_scanner(self, tmp_path):
        """SCANNER_RESULT gets funnel graphic when no ticker chart matches."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create funnel file
        funnel_file = charts_dir / "funnel.png"
        funnel_file.write_bytes(b"\x89PNG" + b"\x00" * 50)

        # Create manifest with funnel_graphic
        manifest = {"charts": {"funnel_graphic": "funnel.png"}}
        (charts_dir / "chart_manifest.json").write_text(json.dumps(manifest))

        tweet = _make_tweet(
            text="$INOD at $61.54 — cleared all gates. NFA!",
            category="SCANNER_RESULT",
            chart_required=True,
            chart_path=None,
            tickers=["INOD"],
        )

        attached = _attach_chart_paths([tweet], charts_dir=charts_dir)

        assert tweet.chart_path is not None, (
            "SCANNER_RESULT should get funnel fallback when no ticker chart"
        )
        assert attached >= 1

    def test_chart_fallback_skipped_for_sell_signal(self, tmp_path):
        """SELL_SIGNAL does NOT get funnel fallback — stays None."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        funnel_file = charts_dir / "funnel.png"
        funnel_file.write_bytes(b"\x89PNG" + b"\x00" * 50)

        manifest = {"charts": {"funnel_graphic": "funnel.png"}}
        (charts_dir / "chart_manifest.json").write_text(json.dumps(manifest))

        tweet = _make_tweet(
            text="$LUMN setup invalidated. Win more than you lose. NFA!",
            category="SELL_SIGNAL",
            chart_required=True,
            chart_path=None,
            tickers=["LUMN"],
        )

        _attach_chart_paths([tweet], charts_dir=charts_dir)

        assert tweet.chart_path is None, (
            "SELL_SIGNAL should NOT get funnel fallback"
        )

    def test_performance_multi_chart_attachment(self, tmp_path):
        """PERFORMANCE tweets get multiple charts attached (one per ticker)."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create 3 chart files for winner tickers
        for ticker in ["WCC", "STRL", "MOD"]:
            chart_file = charts_dir / f"{ticker}_weekly_20260208.png"
            chart_file.write_bytes(b"\x89PNG" + b"\x00" * 50)

        manifest = {
            "charts": {
                "WCC": str(charts_dir / "WCC_weekly_20260208.png"),
                "STRL": str(charts_dir / "STRL_weekly_20260208.png"),
                "MOD": str(charts_dir / "MOD_weekly_20260208.png"),
            }
        }
        (charts_dir / "chart_manifest.json").write_text(json.dumps(manifest))

        tweet = _make_tweet(
            text="$WCC +11.9%. $STRL +10.7%. $MOD +16.8%. Scanner receipts. NFA!",
            category="PERFORMANCE",
            chart_required=True,
            tickers=["$WCC", "$STRL", "$MOD"],
        )

        attached = _attach_chart_paths([tweet], charts_dir=charts_dir)

        assert len(tweet.chart_paths) == 3, (
            f"PERFORMANCE should attach all 3 charts, got {len(tweet.chart_paths)}"
        )
        assert attached == 3
        # Backwards compat: chart_path is None (old field), chart_paths has all
        assert tweet.chart_path is None  # Old field not set for multi-chart
        assert all("weekly_20260208.png" in p for p in tweet.chart_paths)

    def test_performance_not_dropped_without_charts(self, tmp_path):
        """PERFORMANCE tweets are NOT dropped even without charts (soft requirement)."""
        from twitter.tweet_generator import _write_queues, ACCOUNT_QUEUES

        tweet = _make_tweet(
            text="$WCC +11.9%. Scanner receipts. NFA!",
            category="PERFORMANCE",
            chart_required=True,
            tickers=["$WCC"],
            metadata={"day": "saturday", "slot": 2},
        )
        # No chart_path or chart_paths set

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        _write_queues([tweet], ACCOUNT_QUEUES, out_dir, "2026-02-08")

        import json
        queue = json.loads((out_dir / "content_queue.json").read_text())
        assert len(queue) == 1, "PERFORMANCE tweet should NOT be dropped without charts"
        assert queue[0]["category"] == "PERFORMANCE"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 22-23 — Temporal Validation [4A.7.3]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestTemporalValidation:
    """Step 6b catches anachronistic temporal references."""

    def test_temporal_catches_year_end_in_q1(self):
        """'year-end' reference in Q1 (Feb 2026) triggers step_temporal failure."""
        tweet = _make_tweet(
            text="$NVDA positioning for year-end rally. Institutional accumulation. NFA!",
            category="EDUCATIONAL",
            chart_required=False,
        )
        source_data = {}

        result = _validate_tweet(tweet, source_data)

        temporal_failures = [f for f in result.failures if "step_temporal" in f]
        assert len(temporal_failures) > 0, (
            f"'year-end' in Q1 should trigger step_temporal, got: {result.failures}"
        )

    def test_temporal_passes_correct_refs(self):
        """Current quarter references (Q1 2026) should not fail."""
        from datetime import datetime as dt
        now = dt.now()
        current_q = (now.month - 1) // 3 + 1

        tweet = _make_tweet(
            text=f"$NVDA at $145 — strong Q{current_q} momentum. NFA!",
            category="EDUCATIONAL",
            chart_required=False,
        )
        source_data = {}

        result = _validate_tweet(tweet, source_data)

        temporal_failures = [f for f in result.failures if "step_temporal" in f]
        assert len(temporal_failures) == 0, (
            f"Current quarter Q{current_q} should pass, got: {temporal_failures}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 24 — Slot 1 Not in Weekly Schedule [4A.7.4]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestSlotRouting:
    """Slot 1 is reserved for daily queue and never appears in weekly schedule."""

    def test_slot_1_not_in_weekly_schedule(self):
        data = _empty_content_data(
            pass_signals=[
                {"symbol": "INOD", "price": 61.54, "theme": "AI"},
            ],
            themes=[
                {"name": "AI Infrastructure", "classification": "PRIME",
                 "composite_score": 8.2},
            ],
            winners=[
                {"ticker": "RCAT", "entry_price": 8.50, "current_price": 13.25,
                 "pnl_pct": 55.9, "theme": "Drone Tech"},
            ],
        )

        schedule = _plan_weekly_schedule(data)

        assert len(schedule) > 0, "Schedule should not be empty"
        for assignment in schedule:
            assert assignment.slot != 1, (
                f"Slot 1 found in weekly schedule: {assignment}"
            )
            assert assignment.slot in (2, 3, 4, 5), (
                f"Invalid slot {assignment.slot} in weekly schedule"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS 25-26 — Style Guide & Examples [4A.8]
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestStyleGuideAndExamples:
    """CATEGORY_EXAMPLES coverage and EMBEDDED_STYLE_GUIDE token budget."""

    def test_category_examples_exist(self):
        """CATEGORY_EXAMPLES covers at least 7 categories with non-empty strings."""
        assert isinstance(CATEGORY_EXAMPLES, dict), "CATEGORY_EXAMPLES should be a dict"

        expected_categories = [
            "SCANNER_RESULT", "THEME_ANALYSIS", "PERFORMANCE",
            "WATCHLIST", "SELL_SIGNAL", "EDUCATIONAL", "ENGAGEMENT",
        ]

        for cat in expected_categories:
            assert cat in CATEGORY_EXAMPLES, f"Missing CATEGORY_EXAMPLES entry for {cat}"
            assert isinstance(CATEGORY_EXAMPLES[cat], str), (
                f"CATEGORY_EXAMPLES[{cat}] should be a string"
            )
            assert len(CATEGORY_EXAMPLES[cat]) > 20, (
                f"CATEGORY_EXAMPLES[{cat}] is too short ({len(CATEGORY_EXAMPLES[cat])} chars)"
            )

    def test_embedded_style_guide_under_token_limit(self):
        """EMBEDDED_STYLE_GUIDE should be under 2000 tokens (word_count * 1.3)."""
        word_count = len(EMBEDDED_STYLE_GUIDE.split())
        approx_tokens = int(word_count * 1.3)

        assert approx_tokens < 2000, (
            f"EMBEDDED_STYLE_GUIDE is ~{approx_tokens} tokens "
            f"({word_count} words × 1.3), should be < 2000"
        )
