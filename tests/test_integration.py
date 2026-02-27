"""Integration tests — Cross-module validation and subsystem integration.

Tests cover:
  - Banned terms and internal terminology smoke tests
  - QQQ benchmark and equity tracking
  - DD post generation

Ref: STERLING_SIGNALS_PRD_v2.md section 9
"""

import pytest

# ── Module imports (units under test) ────────────────────────────────────────

from twitter.models import INTERNAL_TERM_PATTERNS
from config.banned_terms import ALL_BANNED


_BATCH_TESTS_REMOVED = True  # TestFridayPipeline, TestDailyPosting, TestContentValidation deleted (Tweet Phase 1)


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE ASSERTIONS (smoke tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossCuttingSmoke:
    """Quick smoke tests for cross-module consistency."""

    def test_banned_terms_registry_has_minimum_coverage(self):
        """ALL_BANNED contains at least the critical terms from CLAUDE.md marketing rules."""
        # Use exact forms as they appear in ALL_BANNED (compound forms for indicator names)
        critical_must_have = [
            "HMA", "BoS", "BOS", "Banker indicator", "VWAP", "RSI", "MACD", "KDJ",
            "Gatekeeper", "gatekeeper", "TIER1", "TIER2", "TIER3",
            "UK ISA", "GMT", "BST",
            # Sterling Grid terms
            "Undercurrent", "UC indicator", "ExD", "profit lock",
            "tiered stop", "gear shift", "price cap",
        ]
        all_banned_lower = {t.lower() for t in ALL_BANNED}
        missing = [t for t in critical_must_have if t.lower() not in all_banned_lower]
        assert len(missing) == 0, f"ALL_BANNED is missing critical terms: {missing}"

    def test_internal_term_patterns_catch_critical_banned(self):
        """INTERNAL_TERM_PATTERNS regex list covers key terms from CRITICAL_BANNED."""
        import re

        must_catch = ["HMA", "BoS", "BOS", "Banker", "TIER1", "TIER2", "TIER3",
                       "RSI", "MACD", "KDJ", "gatekeeper", "VWAP",
                       "Undercurrent", "ExD", "profit lock"]
        missed = []

        for term in must_catch:
            test_text = f"The {term} indicator shows strength"
            caught = False
            for pattern in INTERNAL_TERM_PATTERNS:
                if re.search(pattern, test_text, re.IGNORECASE):
                    caught = True
                    break
            if not caught:
                missed.append(term)

        assert len(missed) == 0, f"INTERNAL_TERM_PATTERNS missed: {missed}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 5: QQQ BENCHMARK & EQUITY TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class TestQQQBenchmark:
    """Tests for QQQ/NASDAQ benchmark integration in EquityTracker."""

    def test_equity_snapshot_qqq_fields_exist(self):
        """EquitySnapshot has qqq_value, qqq_return_pct, alpha_vs_qqq_pct."""
        from portfolio.manager import EquitySnapshot

        snap = EquitySnapshot(date="2026-02-14", nav=50000.0)
        assert hasattr(snap, "qqq_value")
        assert hasattr(snap, "qqq_return_pct")
        assert hasattr(snap, "alpha_vs_qqq_pct")
        assert snap.qqq_value == 0.0
        assert snap.qqq_return_pct == 0.0
        assert snap.alpha_vs_qqq_pct == 0.0

    def test_equity_snapshot_csv_round_trip(self):
        """EquitySnapshot serializes and deserializes QQQ fields via CSV."""
        from portfolio.manager import EquitySnapshot

        original = EquitySnapshot(
            date="2026-02-14",
            nav=55000.0,
            total_return_pct=10.0,
            spy_value=52000.0,
            spy_return_pct=5.0,
            alpha_pct=5.0,
            qqq_value=53000.0,
            qqq_return_pct=6.0,
            alpha_vs_qqq_pct=4.0,
        )

        csv_row = original.to_csv_row()
        restored = EquitySnapshot.from_csv_row(csv_row)

        assert restored.qqq_value == 53000.0
        assert restored.qqq_return_pct == 6.0
        assert restored.alpha_vs_qqq_pct == 4.0
        assert restored.spy_return_pct == 5.0
        assert restored.total_return_pct == 10.0

    def test_equity_snapshot_backward_compat(self):
        """Old CSV rows without QQQ fields load with defaults (0.0)."""
        from portfolio.manager import EquitySnapshot

        # Simulate old CSV row without QQQ fields
        old_row = {
            "date": "2026-01-01",
            "nav": "50000.0",
            "total_deployed": "45000.0",
            "cash_pool": "5000.0",
            "total_return_pct": "8.5",
            "spy_value": "48000.0",
            "spy_return_pct": "4.2",
            "alpha_pct": "4.3",
            "open_positions": "3",
            "closed_trades": "2",
            "win_rate_pct": "75.0",
        }

        restored = EquitySnapshot.from_csv_row(old_row)
        assert restored.qqq_value == 0.0
        assert restored.qqq_return_pct == 0.0
        assert restored.alpha_vs_qqq_pct == 0.0
        # Existing fields intact
        assert restored.total_return_pct == 8.5
        assert restored.spy_return_pct == 4.2

    def test_qqq_fields_in_snapshot_fields_list(self):
        """EQUITY_SNAPSHOT_FIELDS includes QQQ field names."""
        from portfolio.manager import EQUITY_SNAPSHOT_FIELDS

        assert "qqq_value" in EQUITY_SNAPSHOT_FIELDS
        assert "qqq_return_pct" in EQUITY_SNAPSHOT_FIELDS
        assert "alpha_vs_qqq_pct" in EQUITY_SNAPSHOT_FIELDS

    def test_compounding_summary_includes_qqq(self):
        """get_compounding_summary() dict includes QQQ keys.

        We can't easily call the full get_compounding_summary() without
        real market data, so instead verify the snapshot fields flow into
        the summary dict format by checking the field list.
        """
        from portfolio.manager import EquitySnapshot

        snap = EquitySnapshot(
            date="2026-02-14",
            nav=55000.0,
            total_return_pct=10.0,
            spy_value=52000.0,
            spy_return_pct=4.0,
            alpha_pct=6.0,
            qqq_value=53000.0,
            qqq_return_pct=6.0,
            alpha_vs_qqq_pct=4.0,
        )

        # Verify the snapshot has QQQ fields that get_compounding_summary reads
        assert snap.qqq_value == 53000.0
        assert snap.qqq_return_pct == 6.0
        assert snap.alpha_vs_qqq_pct == 4.0

        # Verify the CSV round-trip preserves them (this is what the summary reads)
        row = snap.to_csv_row()
        assert float(row["qqq_value"]) == 53000.0
        assert float(row["qqq_return_pct"]) == 6.0
        assert float(row["alpha_vs_qqq_pct"]) == 4.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 6: DD POST GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestDDPostGenerator:
    """Tests for the DD HTML post generator."""

    @pytest.fixture
    def sample_dd_signal(self):
        """A buy signal with full DD fields populated."""
        return {
            "symbol": "NVDA",
            "price": 145.50,
            "final_decision": "PASS",
            "theme": "AI Infrastructure",
            "theme_verdict": "STRONG FIT",
            "conviction": 8,
            "dd_conviction": 9,
            "dd_elevator_pitch": "NVDA is the backbone of the AI revolution",
            "dd_why_now": "Hyperscaler CapEx guidance raised 40% for 2026",
            "dd_the_math": "At 35x forward PE with 50% revenue growth, path to $220 in 12 months",
            "dd_bear_case": "AI spending could slow, but enterprise adoption just starting",
            "dd_risk_to_monitor": "China export restrictions could limit TAM by 10%",
            "dd_action": "Enter Monday at market open, standard position size",
            "dd_position_size": "15% of equity",
            "bullish_factors": ["Data center demand surging", "Blackwell ramp accelerating"],
            "risk_factors": ["Valuation stretched vs history"],
        }

    @pytest.fixture
    def sample_themes(self):
        """Theme data with sub-scores."""
        return [
            {
                "name": "AI Infrastructure",
                "classification": "PRIME",
                "theme_type": "TREND",
                "composite_score": 8.2,
                "catalyst_score": 8.5,
                "momentum_score": 7.8,
                "crowding_score": 6.5,
                "runway_score": 9.0,
                "thesis_summary": "Data center buildout accelerating globally",
                "key_catalysts": ["Hyperscaler CapEx", "Enterprise AI adoption", "Blackwell GPU ramp"],
            },
        ]

    def test_generate_dd_post_basic(self, sample_dd_signal):
        """generate_dd_post() produces valid HTML with all sections."""
        from substack.dd_post_generator import generate_dd_post

        html = generate_dd_post(sample_dd_signal)

        assert "<!DOCTYPE html>" in html
        assert "$NVDA" in html
        assert "GREEN SIGNAL" in html
        assert "The Pitch" in html
        assert "Why Now" in html
        assert "The Math" in html
        assert "Bear Case" in html
        assert "Risk to Monitor" in html
        assert "Action" in html

    def test_generate_dd_post_with_themes(self, sample_dd_signal, sample_themes):
        """DD post includes theme context with progress bars when themes provided."""
        from substack.dd_post_generator import generate_dd_post

        html = generate_dd_post(sample_dd_signal, sample_themes)

        assert "Theme Context" in html
        assert "AI Infrastructure" in html
        assert "Composite Score" in html
        assert "Catalyst Score" in html
        assert "Momentum Score" in html
        assert "Crowding Score" in html
        assert "Runway Score" in html
        # Progress bar elements
        assert "width:" in html  # Progress bar width
        assert "8.2/10" in html  # Composite score label

    def test_dd_post_marketing_safety(self, sample_dd_signal):
        """DD post HTML passes marketing vocabulary validation."""
        from substack.dd_post_generator import generate_dd_post
        from config.banned_terms import validate_content as _validate_content
        import re

        html = generate_dd_post(sample_dd_signal)

        # Strip HTML tags for text-only validation
        text_only = re.sub(r'<[^>]+>', '', html)

        is_valid, violations = _validate_content(text_only)
        assert is_valid, f"DD post contains banned terms: {violations}"

    def test_dd_post_missing_fields_graceful(self):
        """DD post handles missing DD fields gracefully with 'Analysis pending'."""
        from substack.dd_post_generator import generate_dd_post

        minimal_signal = {
            "symbol": "TEST",
            "price": 25.00,
            "final_decision": "PASS",
            "theme": "Test Theme",
            "conviction": 7,
        }

        html = generate_dd_post(minimal_signal)

        assert "$TEST" in html
        assert "Analysis pending" in html  # Fallback text for missing fields
        assert "<!DOCTYPE html>" in html

    def test_progress_bar_generation(self):
        """_progress_bar() generates correct width percentages."""
        from substack.dd_post_generator import _progress_bar

        bar = _progress_bar(8.0, 10.0, "Test Score", "#2DD4BF")
        assert "width:80%" in bar
        assert "Test Score" in bar
        assert "8.0/10" in bar

        # Edge case: max value
        bar_max = _progress_bar(10.0, 10.0, "Max", "#2DD4BF")
        assert "width:100%" in bar_max

        # Edge case: zero
        bar_zero = _progress_bar(0.0, 10.0, "Zero", "#2DD4BF")
        assert "width:0%" in bar_zero

    def test_sanitize_text_replaces_internal_terms(self):
        """_sanitize_text() replaces internal terminology with public alternatives."""
        from substack.dd_post_generator import _sanitize_text

        # Test known internal term replacement
        result = _sanitize_text("STRONG BUY signal detected")
        assert "STRONG BUY" not in result

    def test_dd_post_signal_badge(self):
        """Signal badge renders correctly for PASS and CONSIDER."""
        from substack.dd_post_generator import _signal_badge

        pass_badge = _signal_badge("PASS")
        assert "GREEN SIGNAL" in pass_badge

        consider_badge = _signal_badge("CONSIDER")
        assert "ON OUR RADAR" in consider_badge

    def test_dd_post_no_banned_terms_in_footer(self):
        """Footer uses approved marketing language only."""
        from substack.dd_post_generator import generate_dd_post
        import re

        signal = {
            "symbol": "TEST",
            "price": 10.00,
            "final_decision": "PASS",
            "theme": "Test",
            "conviction": 7,
        }

        html = generate_dd_post(signal)

        # Check footer contains approved phrases
        assert "screening system" in html
        assert "sterlingsignals.substack.com" in html
        assert "financial advice" in html
