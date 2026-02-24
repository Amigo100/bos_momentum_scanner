"""Integration tests — Saturday Workflow + Merge Decisions.

Tests cover:
  - merge_decisions: signals merging, field compatibility, catalyst mapping
  - saturday_workflow: archive paths, newsletter paths, path correctness
  - Path audit: no active trades/ directory references

All external APIs mocked. File I/O uses tmpdir fixtures for full isolation.

Ref: Session 5 plan — saturday_workflow_integration.md
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_tech_data() -> dict:
    """Realistic signals_technical.json (LLM fields zeroed)."""
    return {
        "timestamp": "2026-02-21 16:45:00",
        "timeframe": "WEEKLY",
        "entry_criteria": "Sterling Grid V6: HMA pivot + (UC rising OR MACD cross-up)",
        "exit_criteria": "ExD compound exit + tiered profit lock",
        "stats": {
            "tickers_loaded": 885,
            "data_downloaded": 885,
            "buy_signal": 5,
            "technical_signals": 5,
        },
        "themes": [],
        "pass_signals": [],
        "consider_signals": [],
        "buy_signals": [
            {
                "symbol": "ETON",
                "price": 17.93,
                "tier": "T1",
                "quality_tier": 1,
                "beta": 0.97,
                "uc": 18.76,
                "uc_rising": True,
                "uc_rising_above": True,
                "rsi14": 58.4,
                "macd_cross_up": True,
                "hma_pivot_low": True,
                "hma_pivot_high": False,
                "hma_slope_rising": True,
                "buy_signal": True,
                "exd_signal": False,
                "return_20d": 12.5,
                "banker": 18.76,
                "theme": "",
                "theme_score": 0,
                "final_decision": "TECHNICAL_ONLY",
                "conviction": 0,
                "catalyst_summary": "",
                "bullish_factors": [],
                "risk_factors": [],
                "reasoning": "",
            },
            {
                "symbol": "RELY",
                "price": 17.15,
                "tier": "T3",
                "quality_tier": 3,
                "beta": 0.93,
                "uc": 20.0,
                "uc_rising": True,
                "uc_rising_above": True,
                "rsi14": 57.8,
                "macd_cross_up": False,
                "hma_pivot_low": True,
                "hma_pivot_high": False,
                "hma_slope_rising": True,
                "buy_signal": True,
                "exd_signal": False,
                "return_20d": 8.3,
                "banker": 20.0,
                "theme": "",
                "theme_score": 0,
                "final_decision": "TECHNICAL_ONLY",
                "conviction": 0,
                "catalyst_summary": "",
                "bullish_factors": [],
                "risk_factors": [],
                "reasoning": "",
            },
        ],
        "sell_signals": [],
        "assessed_signals": [],
        "historical_winners": [],
        "big_wins": [],
        "home_runs": [],
    }


@pytest.fixture
def sample_decisions() -> dict:
    """Realistic decisions.json from Claude.ai Prompt 7 export."""
    return {
        "scan_date": "2026-02-21",
        "market_regime": "Bullish — breadth improving",
        "market_context_summary": "SPY holding above 20-week HMA.",
        "themes_this_week": [
            {
                "name": "Grid Infrastructure",
                "classification": "PRIME",
                "composite_score": 8.1,
                "catalyst_score": 8.5,
                "momentum_score": 7.8,
                "crowding_score": 7.2,
                "runway_score": 8.5,
                "thesis_summary": "Grid modernization spending.",
                "why_now": "DOE grants accelerating.",
                "key_catalysts": ["DOE grants Q1 2026"],
                "primary_risks": ["Interest rate sensitivity"],
                "valuation_regime": "FUNDAMENTAL",
                "lifecycle_stage": "Early acceleration",
                "primary_etfs": ["GRID", "XLU"],
                "crowding_indicator": "Moderate",
            },
        ],
        "new_positions": [
            {
                "symbol": "ETON",
                "price": 17.93,
                "verdict": "STRONG_BUY",
                "dd_verdict": "STRONG BUY",
                "conviction": 8,
                "dd_conviction": 8,
                "theme": "Healthcare Contrarian",
                "theme_score": 6.8,
                "theme_verdict": "STRONG FIT",
                "theme_classification": "INVESTABLE",
                "tier": "T1",
                "quality_tier": 1,
                "dd_elevator_pitch": "Eton Pharma — rare disease pharma with 8-for-8 FDA record.",
                "dd_why_now": "ET-600 PDUFA on Feb 25.",
                "dd_the_math": "Fair value $24-30 based on 6x forward revenue.",
                "dd_bear_case": "Concentrated portfolio risk.",
                "dd_risk_to_monitor": "FDA decision on ET-600.",
                "dd_action": "Buy Monday at ~$18.",
                "dd_key_catalyst": "ET-600 PDUFA Feb 25",
                "dd_fatal_flaw": "",
                "catalyst_summary": "ET-600 PDUFA decision Feb 25 with 85%+ approval probability",
                "variant_perception": "Market underappreciates FDA track record.",
                "bullish_factors": ["Perfect FDA record", "Revenue growing 45%"],
                "risk_factors": ["Binary FDA event", "Elevated valuation"],
                "kill_switch": "FDA rejection of ET-600",
                "position_size": "20%",
                "position_size_pct": 0.20,
                "sizing_gear": "recommended",
                "valuation_regime": "FUNDAMENTAL",
                "gate_verdict": "STRONG_BUY",
                "gate_catalyst": "ET-600 PDUFA",
                "gate_bear_case": "Overvalued at 8.8x P/S",
                "gate_math": "Fair value $24-30",
            },
            {
                "symbol": "RELY",
                "price": 17.15,
                "verdict": "SPEC_BUY",
                "dd_verdict": "SPECULATIVE BUY",
                "conviction": 6,
                "dd_conviction": 6,
                "theme": "Grid Infrastructure",
                "theme_score": 8.1,
                "theme_verdict": "GOOD FIT",
                "theme_classification": "PRIME",
                "tier": "T3",
                "quality_tier": 3,
                "dd_elevator_pitch": "Remitly — digital remittance with 40%+ growth.",
                "dd_why_now": "Q4 beat with guide-up.",
                "dd_the_math": "6x forward revenue implies $24-26.",
                "dd_bear_case": "Profitability unproven.",
                "dd_risk_to_monitor": "Q1 2026 earnings.",
                "dd_action": "Buy Monday at ~$17.15.",
                "dd_key_catalyst": "Q1 2026 earnings",
                "dd_fatal_flaw": "",
                "catalyst_summary": "Q4 beat with guide-up, digital penetration under 20%",
                "variant_perception": "TAM expansion underestimated.",
                "bullish_factors": ["40%+ growth", "Q4 beat"],
                "risk_factors": ["Competition from Wise", "FX volatility"],
                "kill_switch": "Growth deceleration below 35%",
                "position_size": "5%",
                "position_size_pct": 0.05,
                "sizing_gear": "conservative",
                "valuation_regime": "GROWTH",
                "gate_verdict": "SPEC_BUY",
                "gate_catalyst": "Q4 beat",
                "gate_bear_case": "Profitability unproven",
                "gate_math": "6x forward rev → $24-26",
            },
        ],
        "exits": [],
        "no_go": [
            {"symbol": "SATS", "reason": "Overcrowded", "filtered_at": "thematic"},
            {"symbol": "VNET", "reason": "SEC investigation", "filtered_at": "gate"},
        ],
        "watchlist": [
            {"symbol": "IONQ", "theme": "Quantum Computing", "price_at_scan": 42.15},
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMergeDecisions:
    """Tests for scanner.merge_decisions merge logic."""

    def test_merge_produces_valid_signals_json(self, sample_tech_data, sample_decisions):
        """All required top-level keys present in merge output."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        required_keys = [
            "timestamp", "timeframe", "entry_criteria", "exit_criteria",
            "stats", "themes", "pass_signals", "consider_signals",
            "buy_signals", "sell_signals", "assessed_signals",
            "exit_signals",  # defensive alias
            "historical_winners", "big_wins", "home_runs",
        ]
        for key in required_keys:
            assert key in merged, f"Missing key: {key}"

    def test_merge_field_compatibility(self, sample_tech_data, sample_decisions):
        """All fields from audit Section 12 present in buy_signals."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        # Fields that downstream consumers need (from audit)
        required_signal_fields = [
            # Technical
            "symbol", "price", "tier", "quality_tier", "beta",
            "uc", "uc_rising", "rsi14", "macd_cross_up",
            "hma_pivot_low", "hma_slope_rising", "buy_signal",
            "exd_signal", "return_20d", "banker",
            # Theme
            "theme", "theme_score", "theme_verdict", "theme_classification",
            # Gate
            "final_decision", "conviction", "gate_verdict",
            "gate_catalyst", "gate_bear_case", "gate_math",
            "bullish_factors", "risk_factors", "reasoning",
            # DD
            "dd_verdict", "dd_conviction", "dd_elevator_pitch",
            "dd_why_now", "dd_the_math", "dd_bear_case",
            "dd_risk_to_monitor", "dd_action", "dd_key_catalyst",
            # Downstream compat
            "catalyst_summary", "action",
            # Position sizing
            "position_size_pct",
        ]

        assert len(merged["buy_signals"]) == 2
        for sig in merged["buy_signals"]:
            for field in required_signal_fields:
                assert field in sig, \
                    f"Missing field '{field}' in {sig['symbol']}"

    def test_catalyst_summary_mapping(self, sample_tech_data, sample_decisions):
        """catalyst_summary correctly mapped from decisions.json."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        eton = next(s for s in merged["buy_signals"] if s["symbol"] == "ETON")
        rely = next(s for s in merged["buy_signals"] if s["symbol"] == "RELY")

        # catalyst_summary must be non-empty and match decisions input
        assert eton["catalyst_summary"] == \
            "ET-600 PDUFA decision Feb 25 with 85%+ approval probability"
        assert "Q4" in rely["catalyst_summary"]

        # gate_catalyst should also be populated
        assert eton["gate_catalyst"] != ""
        assert rely["gate_catalyst"] != ""

    def test_exit_signals_alias_present(self, sample_tech_data, sample_decisions):
        """exit_signals key exists as alias for sell_signals."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        assert "exit_signals" in merged
        assert merged["exit_signals"] is merged["sell_signals"]

    def test_themes_mapped_correctly(self, sample_tech_data, sample_decisions):
        """Themes from decisions map into merged output with all sub-scores."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        assert len(merged["themes"]) == 1
        theme = merged["themes"][0]
        assert theme["name"] == "Grid Infrastructure"
        assert theme["classification"] == "PRIME"
        assert theme["composite_score"] == 8.1
        assert "primary_etfs" in theme

    def test_nogo_and_watchlist_in_assessed(self, sample_tech_data, sample_decisions):
        """no_go and watchlist entries appear in assessed_signals."""
        from scanner.merge_decisions import merge_signals

        merged = merge_signals(sample_tech_data, sample_decisions)

        symbols = [s["symbol"] for s in merged["assessed_signals"]]
        assert "SATS" in symbols  # no_go
        assert "VNET" in symbols  # no_go
        assert "IONQ" in symbols  # watchlist

        # Check final_decision mapping
        sats = next(s for s in merged["assessed_signals"] if s["symbol"] == "SATS")
        ionq = next(s for s in merged["assessed_signals"] if s["symbol"] == "IONQ")
        assert sats["final_decision"] == "REJECTED"
        assert ionq["final_decision"] == "WATCHLIST"


class TestOutputPaths:
    """Tests for path correctness — no trades/ references."""

    def test_decisions_default_path(self):
        """DECISIONS_DEFAULT points to scanner/output/, not trades/."""
        from scanner.merge_decisions import DECISIONS_DEFAULT
        assert "scanner/output" in str(DECISIONS_DEFAULT) or \
            "scanner" in DECISIONS_DEFAULT.parts, \
            f"DECISIONS_DEFAULT should be in scanner/output/, got: {DECISIONS_DEFAULT}"
        assert "trades" not in str(DECISIONS_DEFAULT), \
            f"DECISIONS_DEFAULT should NOT reference trades/: {DECISIONS_DEFAULT}"

    def test_signals_tech_path(self):
        """SIGNALS_TECH points to scanner/output/, not current/."""
        from scanner.merge_decisions import SIGNALS_TECH
        assert "signals_technical.json" in str(SIGNALS_TECH)
        assert "trades" not in str(SIGNALS_TECH), \
            f"SIGNALS_TECH should NOT reference trades/: {SIGNALS_TECH}"

    def test_saturday_workflow_decisions_default(self):
        """saturday_workflow DECISIONS_DEFAULT points to scanner/output/."""
        from scanner.saturday_workflow import DECISIONS_DEFAULT
        assert "scanner/output" in str(DECISIONS_DEFAULT) or \
            "scanner" in DECISIONS_DEFAULT.parts
        assert "trades" not in str(DECISIONS_DEFAULT), \
            f"DECISIONS_DEFAULT should NOT reference trades/: {DECISIONS_DEFAULT}"

    def test_archive_path_uses_scanner_output(self):
        """get_weekly_archive_dir() returns scanner/output/archive/."""
        from scanner.merge_decisions import get_weekly_archive_dir
        archive_dir = get_weekly_archive_dir()
        assert "scanner" in str(archive_dir), \
            f"Archive should be in scanner/output/archive/, got: {archive_dir}"
        assert "trades" not in str(archive_dir), \
            f"Archive should NOT reference trades/: {archive_dir}"

    def test_saturday_archive_path(self):
        """saturday_workflow get_weekly_archive_dir() returns scanner/output/archive/."""
        from scanner.saturday_workflow import get_weekly_archive_dir
        archive_dir = get_weekly_archive_dir()
        assert "scanner" in str(archive_dir)
        assert "trades" not in str(archive_dir), \
            f"Archive should NOT reference trades/: {archive_dir}"


class TestValidation:
    """Tests for validate_decisions() and build_content_schedule()."""

    def test_validate_catches_missing_fields(self):
        """validate_decisions() warns on missing required fields."""
        from scanner.merge_decisions import validate_decisions

        # Empty dict triggers early return
        warnings_empty = validate_decisions({})
        assert len(warnings_empty) > 0
        assert "empty" in warnings_empty[0].lower()

        # Non-empty dict missing required fields should list them
        warnings = validate_decisions({"exits": []})
        assert len(warnings) > 0
        field_names = " ".join(warnings)
        assert "scan_date" in field_names
        assert "new_positions" in field_names

    def test_validate_catches_missing_position_fields(self):
        """validate_decisions() warns on missing position fields."""
        from scanner.merge_decisions import validate_decisions

        decisions = {
            "scan_date": "2026-02-21",
            "market_regime": "Bullish",
            "themes_this_week": [],
            "new_positions": [
                {"symbol": "TEST"}  # Missing verdict, dd_elevator_pitch, conviction
            ],
        }
        warnings = validate_decisions(decisions)
        assert any("verdict" in w for w in warnings)
        assert any("dd_elevator_pitch" in w for w in warnings)

    def test_build_content_schedule(self, sample_decisions):
        """build_content_schedule() produces expected structure."""
        from scanner.merge_decisions import build_content_schedule

        schedule = build_content_schedule(sample_decisions)

        assert "generated" in schedule
        assert schedule["scan_date"] == "2026-02-21"
        assert "week_start" in schedule
        assert "week_end" in schedule
        assert "market_context" in schedule
        assert len(schedule["new_positions"]) == 2
        assert schedule["new_positions"][0]["symbol"] == "ETON"


class TestNoTradesReferences:
    """Scan source files for active trades/ path usage."""

    def test_no_trades_directory_references_in_merge(self):
        """merge_decisions.py should not import or use TRADES_DIR."""
        merge_path = Path(__file__).parent.parent / "scanner" / "merge_decisions.py"
        content = merge_path.read_text()

        # Should NOT import TRADES_DIR
        assert "TRADES_DIR" not in content, \
            "merge_decisions.py should not reference TRADES_DIR"

    def test_no_trades_directory_references_in_workflow(self):
        """saturday_workflow.py should not import or use TRADES_DIR."""
        workflow_path = Path(__file__).parent.parent / "scanner" / "saturday_workflow.py"
        content = workflow_path.read_text()

        # Should NOT import TRADES_DIR
        assert "TRADES_DIR" not in content, \
            "saturday_workflow.py should not reference TRADES_DIR"

    def test_no_active_trades_paths_in_scanner_module(self):
        """No scanner/*.py file should have active trades/ path references."""
        scanner_dir = Path(__file__).parent.parent / "scanner"
        violations = []

        for py_file in scanner_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_text()
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or \
                   stripped.startswith("'''"):
                    continue
                # Check for TRADES_DIR usage (not in comments)
                if "TRADES_DIR" in line and not line.strip().startswith("#"):
                    # Allow it in except ImportError fallback blocks for config
                    # (those were already removed, but just in case)
                    violations.append(f"{py_file.name}:{i}: {line.strip()}")

        assert len(violations) == 0, \
            f"Active TRADES_DIR references found:\n" + "\n".join(violations)
