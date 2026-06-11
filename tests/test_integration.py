"""Integration tests — Cross-module validation and subsystem integration.

Tests cover:
  - Banned terms and internal terminology smoke tests
  - QQQ benchmark and equity tracking
  - DD post generation

Ref: STERLING_SIGNALS_PRD_v2.md section 9
"""

import pytest

# ── Module imports (units under test) ────────────────────────────────────────

from config.banned_terms import ALL_BANNED, INTERNAL_TERM_PATTERNS


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


# TestDDPostGenerator removed — dd_post_generator archived to archive/substack_python_pipeline/
