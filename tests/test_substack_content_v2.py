"""Tests for Substack content utilities (content_utils.py).

Tests cover:
  - ContentContext data loading and building
  - Banned term safety in visual templates
  - Visual element injection (funnel, theme scores, winners table)
  - Prompt formatting helpers
  - Text sanitization (internal → public terminology)
  - LLM output scrubbing
  - Content validation pipeline
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Module imports ────────────────────────────────────────────────────────────

# Shared utilities (from content_utils)
from substack.content_utils import (
    ContentContext,
    PostSpec,
    build_content_context,
    sanitize_text,
    scrub_llm_output,
    validate_post_content,
    build_scan_funnel_html,
    build_theme_scores_html,
    build_winners_table_html,
    inject_visual_elements,
    _format_themes_for_prompt,
    _format_signals_for_prompt,
    _format_winners_for_prompt,
    _format_assessed_for_prompt,
    _format_equity_stats,
    _format_theme_history,
)

from config.banned_terms import (
    ALL_BANNED,
    CRITICAL_BANNED,
    INTERNAL_TERMINOLOGY_MAP,
    check_banned_phrases,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmpdir():
    """Temporary directory for all file I/O in tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_themes():
    """Sample theme data for testing."""
    return [
        {
            "name": "AI Power Infrastructure & Grid Modernization",
            "classification": "PRIME",
            "composite_score": 8.6,
            "catalyst_score": 8.5,
            "momentum_score": 7.8,
            "crowding_score": 6.5,
            "runway_score": 9.0,
            "theme_type": "TREND",
            "thesis_summary": "Power availability has become the primary constraint on AI expansion.",
            "key_catalysts": ["Hyperscaler CapEx guidance", "Grid capacity auctions", "Nuclear restart announcements"],
        },
        {
            "name": "Defense Industrial Base Modernization",
            "classification": "INVESTABLE",
            "composite_score": 7.4,
            "catalyst_score": 7.0,
            "momentum_score": 6.5,
            "crowding_score": 5.0,
            "runway_score": 8.0,
            "theme_type": "BOTTLENECK",
            "thesis_summary": "Geopolitical tensions driving a multi-year modernization cycle.",
            "key_catalysts": ["NATO summit", "Defense budget vote"],
        },
    ]


@pytest.fixture
def sample_buy_signals():
    """Sample buy signals for testing."""
    return [
        {
            "symbol": "INOD",
            "price": 61.54,
            "theme": "AI Power Infrastructure & Grid Modernization",
            "final_decision": "PASS",
            "conviction": 8,
            "dd_elevator_pitch": "Leading provider of grid management software.",
            "dd_why_now": "Earnings catalyst in 3 weeks.",
            "dd_the_math": "Target $90 based on 25x forward PE.",
            "dd_bear_case": "Customer concentration risk.",
            "dd_risk_to_monitor": "Regulatory changes in utility markets.",
            "dd_action": "Enter Monday at market open.",
            "bullish_factors": ["Strong institutional buying", "Theme leader"],
            "risk_factors": ["High valuation", "Concentrated customer base"],
        },
    ]


@pytest.fixture
def sample_winners():
    """Sample portfolio winners for testing."""
    return [
        {"ticker": "STRL", "entry_price": 362.53, "highest_close": 437.77, "pnl_pct": 20.8, "theme": "AI Cooling", "entry_date": "2026-01-15", "show_entry": True},
        {"ticker": "VNET", "entry_price": 10.40, "highest_close": 13.80, "pnl_pct": 32.7, "theme": "Data Centers", "entry_date": "2026-01-10", "show_entry": True},
    ]


@pytest.fixture
def sample_stats():
    """Sample scan stats for testing."""
    return {
        "tickers_loaded": 885,
        "technical_signals": 44,
        "theme_confirmed": 17,
        "final_trade": 3,
    }


@pytest.fixture
def sample_equity():
    """Sample equity curve stats for testing."""
    return {
        "nav": 12500.0,
        "total_return_pct": 25.0,
        "spy_return_pct": 12.0,
        "alpha_pct": 13.0,
        "qqq_return_pct": 15.0,
        "alpha_vs_qqq_pct": 10.0,
        "open_count": 6,
        "date": "2026-02-14",
        "data_points": 12,
    }


@pytest.fixture
def full_context(sample_themes, sample_buy_signals, sample_winners, sample_stats, sample_equity):
    """Full ContentContext for testing."""
    return ContentContext(
        signals={"themes": sample_themes, "buy_signals": sample_buy_signals, "stats": sample_stats},
        market_analysis="Markets were mixed this week with tech outperforming.",
        themes=sample_themes,
        buy_signals=sample_buy_signals,
        assessed_signals=[
            {"symbol": "IONQ", "final_decision": "FAIL", "dd_fatal_flaw": "Valuation stretched"},
        ],
        portfolio_stats=sample_equity,
        historical_winners=sample_winners,
        benchmark="Portfolio +25.0% vs SPY +12.0% vs QQQ +15.0%",
        theme_details="Theme sub-scores available.",
        theme_history={
            "AI Power Infrastructure & Grid Modernization": [
                {"week": "2026-W05", "score": 7.5, "classification": "PRIME"},
                {"week": "2026-W06", "score": 8.6, "classification": "PRIME"},
            ]
        },
        chart_manifest={"INOD": "twitter/output/charts/INOD_weekly_20260214.png"},
        week_number=7,
        pass_count=1,
        scan_stats=sample_stats,
    )


@pytest.fixture
def no_signals_context(sample_themes, sample_winners, sample_stats, sample_equity):
    """ContentContext with zero buy signals."""
    stats = dict(sample_stats)
    stats["final_trade"] = 0
    return ContentContext(
        signals={"themes": sample_themes, "buy_signals": [], "stats": stats},
        market_analysis="Markets dipped this week; defensive sectors led.",
        themes=sample_themes,
        buy_signals=[],
        assessed_signals=[
            {"symbol": "IONQ", "final_decision": "FAIL", "dd_fatal_flaw": "Overextended"},
        ],
        portfolio_stats=sample_equity,
        historical_winners=sample_winners,
        benchmark="Portfolio +25.0% vs SPY +12.0%",
        theme_details="Theme sub-scores available.",
        theme_history={},
        chart_manifest={},
        week_number=7,
        pass_count=0,
        scan_stats=stats,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONTENT CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentContext:
    """Test data loading and context building."""

    def test_context_defaults(self):
        """ContentContext should have sensible defaults."""
        ctx = ContentContext()
        assert ctx.pass_count == 0
        assert ctx.themes == []
        assert ctx.buy_signals == []
        assert ctx.market_analysis == ""
        assert ctx.scan_stats == {}
        assert ctx.week_number == 0

    def test_context_with_signals(self, full_context):
        """Context with signals should have correct pass count."""
        assert full_context.pass_count == 1
        assert len(full_context.buy_signals) == 1
        assert full_context.buy_signals[0]["symbol"] == "INOD"

    def test_context_with_no_signals(self, no_signals_context):
        """Context with no signals should have zero pass count."""
        assert no_signals_context.pass_count == 0
        assert len(no_signals_context.buy_signals) == 0

    def test_context_themes_populated(self, full_context):
        """Context should have themes loaded."""
        assert len(full_context.themes) == 2
        assert full_context.themes[0]["name"] == "AI Power Infrastructure & Grid Modernization"
        assert full_context.themes[0]["classification"] == "PRIME"

    def test_context_winners_populated(self, full_context):
        """Context should have winners loaded."""
        assert len(full_context.historical_winners) == 2
        assert full_context.historical_winners[0]["ticker"] == "STRL"

    def test_context_equity_stats(self, full_context):
        """Context should have equity stats."""
        assert full_context.portfolio_stats["total_return_pct"] == 25.0
        assert full_context.portfolio_stats["spy_return_pct"] == 12.0

    def test_build_context_with_missing_files(self, tmpdir):
        """build_content_context should handle missing files gracefully."""
        # Point to a non-existent signals file
        fake_path = tmpdir / "nonexistent_signals.json"
        with patch("substack.content_utils.SIGNALS_FILE", tmpdir / "signals.json"):
            with patch("substack.content_utils.OUTPUT_PATHS_AVAILABLE", False):
                ctx = build_content_context(fake_path)
                assert ctx.signals == {}
                assert ctx.pass_count == 0

    def test_build_context_loads_signals_json(self, tmpdir):
        """build_content_context should load valid signals.json."""
        signals = {
            "themes": [{"name": "Test Theme", "classification": "PRIME", "composite_score": 8.0}],
            "buy_signals": [{"symbol": "TEST", "final_decision": "PASS", "price": 10.0}],
            "stats": {"tickers_loaded": 100, "final_trade": 1},
        }
        signals_path = tmpdir / "signals.json"
        signals_path.write_text(json.dumps(signals))

        with patch("substack.content_utils.SIGNALS_FILE", tmpdir / "signals.json"):
            with patch("substack.content_utils.OUTPUT_PATHS_AVAILABLE", False):
                with patch("substack.content_utils.load_portfolio_winners", return_value=[]):
                    with patch("substack.content_utils.load_equity_curve", return_value={}):
                        with patch("substack.content_utils.load_chart_manifest", return_value={}):
                            ctx = build_content_context(signals_path)
                            assert ctx.pass_count == 1
                            assert len(ctx.themes) == 1
                            assert ctx.themes[0]["name"] == "Test Theme"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST BANNED TERM SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

class TestBannedTermSafety:
    """Verify templates and utilities don't contain banned terms."""

    def test_funnel_html_uses_green_signals(self, sample_stats):
        """Scan funnel HTML should say GREEN Signals, not TEAL."""
        html = build_scan_funnel_html(sample_stats)
        assert "GREEN Signals" in html
        assert "TEAL" not in html

    def test_theme_scores_html_no_banned_terms(self, sample_themes):
        """Theme scores HTML should not contain banned terms."""
        html = build_theme_scores_html(sample_themes)
        for term in ["TEAL", "VIOLET", "AMBER", "HMA", "Banker", "BoS"]:
            assert term not in html, f"Banned term '{term}' found in theme scores HTML"

    def test_winners_table_no_banned_terms(self, sample_winners):
        """Winners table HTML should not contain banned terms."""
        html = build_winners_table_html(sample_winners)
        for term in ["TEAL", "VIOLET", "AMBER"]:
            assert term not in html

    def test_sanitize_replaces_internal_terms(self):
        """sanitize_text should replace internal terms with public alternatives."""
        text = "The TEAL signal confirmed with Banker rising."
        sanitized = sanitize_text(text)
        assert "TEAL" not in sanitized
        assert "Banker rising" not in sanitized

    def test_sanitize_handles_empty_string(self):
        """sanitize_text should handle empty string."""
        assert sanitize_text("") == ""
        assert sanitize_text(None) is None

    def test_validate_catches_banned_terms(self):
        """validate_post_content should catch banned terms."""
        is_valid, issues = validate_post_content("The HMA pivot triggered a TEAL signal.")
        assert not is_valid
        assert len(issues) > 0

    def test_validate_passes_clean_content(self):
        """validate_post_content should pass clean content."""
        is_valid, issues = validate_post_content(
            "The proprietary screening system identified a GREEN signal on $INOD."
        )
        assert is_valid
        assert len(issues) == 0

    def test_validate_allows_negative_pnl(self):
        """validate_post_content should allow negative P&L (transparency)."""
        is_valid, issues = validate_post_content("Position is currently at -5.2% P&L.")
        assert is_valid

    def test_validate_allows_stopped_mention(self):
        """validate_post_content should allow STOPPED mentions (transparency)."""
        is_valid, issues = validate_post_content("Position STOPPED out at $15.00.")
        assert is_valid


# ═══════════════════════════════════════════════════════════════════════════════
# TEST VISUAL ELEMENT INJECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualInjection:
    """Test HTML visual element injection."""

    def test_scan_funnel_html_structure(self, sample_stats):
        """Scan funnel should produce valid HTML with all stages."""
        html = build_scan_funnel_html(sample_stats)
        assert "<div" in html
        assert "Universe" in html
        assert "Technical Gates" in html
        assert "Theme Confirmed" in html
        assert "GREEN Signals" in html
        # Numbers should appear
        assert "885" in html
        assert "44" in html
        assert "17" in html
        assert "3" in html

    def test_scan_funnel_empty_stats(self):
        """Scan funnel should handle empty stats gracefully."""
        html = build_scan_funnel_html({})
        assert "<div" in html
        assert "0" in html

    def test_theme_scores_html_structure(self, sample_themes):
        """Theme scores should produce HTML cards for each theme."""
        html = build_theme_scores_html(sample_themes)
        assert "AI Power Infrastructure" in html
        assert "Defense Industrial Base" in html
        assert "PRIME" in html
        assert "INVESTABLE" in html
        assert "8.6" in html
        # Progress bars
        assert "width:" in html

    def test_theme_scores_empty(self):
        """Theme scores should return empty string for no themes."""
        assert build_theme_scores_html([]) == ""

    def test_theme_scores_max_4_themes(self):
        """Theme scores should show at most 4 themes."""
        themes = [{"name": f"Theme {i}", "classification": "INVESTABLE", "composite_score": 5.0} for i in range(6)]
        html = build_theme_scores_html(themes)
        assert "Theme 0" in html
        assert "Theme 3" in html
        assert "Theme 4" not in html  # Only first 4

    def test_winners_table_html_structure(self, sample_winners):
        """Winners table should produce valid HTML table."""
        html = build_winners_table_html(sample_winners)
        assert "<table" in html
        assert "$STRL" in html
        assert "$VNET" in html
        assert "+20.8%" in html
        assert "+32.7%" in html

    def test_winners_table_shows_entry_for_all(self, sample_winners):
        """All positions should display entry price (full transparency)."""
        html = build_winners_table_html(sample_winners)
        # Both positions show entry (transparency)
        assert "$10.40" in html
        assert "$362.53" in html

    def test_winners_table_empty(self):
        """Winners table should return empty string for no winners."""
        assert build_winners_table_html([]) == ""

    def test_winners_table_max_8_winners(self):
        """Winners table should show at most 8 positions."""
        winners = [
            {"ticker": f"TEST{i}", "pnl_pct": 20.0 + i, "theme": "Test", "entry_price": 10.0 + i, "show_entry": True}
            for i in range(10)
        ]
        html = build_winners_table_html(winners)
        assert "TEST0" in html
        assert "TEST7" in html
        assert "TEST8" not in html  # Only first 8

    def test_inject_replaces_scan_funnel(self, full_context):
        """inject_visual_elements should replace [SCAN_FUNNEL] marker."""
        md = "Here are the results:\n\n[SCAN_FUNNEL]\n\nMore text."
        result = inject_visual_elements(md, full_context)
        assert "[SCAN_FUNNEL]" not in result
        assert "<div" in result
        assert "Universe" in result

    def test_inject_replaces_theme_scores(self, full_context):
        """inject_visual_elements should replace [THEME_SCORES] marker."""
        md = "Themes:\n\n[THEME_SCORES]\n\nEnd."
        result = inject_visual_elements(md, full_context)
        assert "[THEME_SCORES]" not in result
        assert "AI Power Infrastructure" in result

    def test_inject_replaces_winners_table(self, full_context):
        """inject_visual_elements should replace [WINNERS_TABLE] marker."""
        md = "Winners:\n\n[WINNERS_TABLE]\n\nEnd."
        result = inject_visual_elements(md, full_context)
        assert "[WINNERS_TABLE]" not in result
        assert "$STRL" in result

    def test_inject_ignores_missing_markers(self, full_context):
        """inject_visual_elements should leave text unchanged if no markers."""
        md = "Just plain text with no markers."
        result = inject_visual_elements(md, full_context)
        assert result == md


# ═══════════════════════════════════════════════════════════════════════════════
# TEST PROMPT FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptFormatting:
    """Test prompt formatting helper functions."""

    def test_format_themes_for_prompt(self, sample_themes):
        """Themes should format with name, classification, and score."""
        result = _format_themes_for_prompt(sample_themes)
        assert "AI Power Infrastructure" in result
        assert "PRIME" in result
        assert "8.6/10" in result
        assert "Catalysts:" in result

    def test_format_themes_empty(self):
        """Empty themes should return descriptive message."""
        result = _format_themes_for_prompt([])
        assert "No themes" in result

    def test_format_signals_for_prompt(self, sample_buy_signals):
        """Signals should format with ticker, price, and conviction."""
        result = _format_signals_for_prompt(sample_buy_signals)
        assert "$INOD" in result
        assert "$61.54" in result

    def test_format_signals_empty(self):
        """Empty signals should return 'no GREEN signals' message."""
        result = _format_signals_for_prompt([])
        assert "No new GREEN signals" in result

    def test_format_winners_for_prompt(self, sample_winners):
        """Winners should format with ticker and P&L."""
        result = _format_winners_for_prompt(sample_winners)
        assert "$STRL" in result
        assert "+20.8%" in result
        assert "$VNET" in result
        assert "+32.7%" in result

    def test_format_winners_shows_entry_for_all(self, sample_winners):
        """All positions should include entry price (full transparency)."""
        result = _format_winners_for_prompt(sample_winners)
        # Both positions show entry (transparency)
        assert "$10.40" in result
        assert "$362.53" in result

    def test_format_winners_empty(self):
        """Empty winners should return descriptive message."""
        result = _format_winners_for_prompt([])
        assert "No open positions" in result

    def test_format_assessed_for_prompt(self):
        """Assessed signals should show why they failed."""
        assessed = [
            {"symbol": "IONQ", "final_decision": "FAIL", "dd_fatal_flaw": "Valuation stretched"},
        ]
        result = _format_assessed_for_prompt(assessed)
        assert "$IONQ" in result
        assert "Valuation stretched" in result

    def test_format_assessed_filters_non_failures(self):
        """Assessed should only show FAIL/NO_GO decisions."""
        assessed = [
            {"symbol": "GOOD", "final_decision": "PASS", "reasoning": "Strong"},
            {"symbol": "BAD", "final_decision": "FAIL", "dd_fatal_flaw": "Weak"},
        ]
        result = _format_assessed_for_prompt(assessed)
        assert "$GOOD" not in result
        assert "$BAD" in result

    def test_format_equity_stats(self, sample_equity):
        """Equity stats should format key performance metrics."""
        result = _format_equity_stats(sample_equity)
        assert "+25.0%" in result
        assert "S&P 500" in result
        assert "Alpha" in result
        assert "NASDAQ" in result

    def test_format_equity_stats_empty(self):
        """Empty equity stats should return descriptive message."""
        result = _format_equity_stats({})
        assert "not available" in result

    def test_format_theme_history_rising(self):
        """Theme history should detect rising trend."""
        history = {
            "Test Theme": [
                {"week": "2026-W05", "score": 6.0, "classification": "INVESTABLE"},
                {"week": "2026-W06", "score": 7.5, "classification": "PRIME"},
                {"week": "2026-W07", "score": 8.5, "classification": "PRIME"},
            ]
        }
        result = _format_theme_history("Test Theme", history)
        assert "rising" in result

    def test_format_theme_history_new_theme(self):
        """New theme should note first appearance."""
        result = _format_theme_history("New Theme", {})
        assert "First appearance" in result



# ═══════════════════════════════════════════════════════════════════════════════
# TEST TEXT SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTextSanitization:
    """Test internal terminology replacement."""

    def test_teal_to_green(self):
        """TEAL signal should be replaced with GREEN signal."""
        assert "GREEN signal" in sanitize_text("This is a TEAL signal.")

    def test_violet_to_red(self):
        """VIOLET signal should be replaced with RED signal."""
        assert "RED signal" in sanitize_text("VIOLET signal triggered.")

    def test_banker_to_accumulation(self):
        """Banker indicator should be replaced with accumulation language."""
        result = sanitize_text("The Banker indicator is strong.")
        assert "Banker indicator" not in result

    def test_strong_buy_to_green(self):
        """STRONG BUY should be replaced with GREEN signal."""
        result = sanitize_text("Verdict: STRONG BUY")
        assert "STRONG BUY" not in result
        assert "GREEN signal" in result

    def test_multiple_replacements(self):
        """Multiple internal terms should all be replaced."""
        text = "The TEAL signal shows Banker rising with ExD exit pending."
        result = sanitize_text(text)
        assert "TEAL" not in result
        assert "Banker rising" not in result
        assert "ExD exit" not in result

    def test_case_insensitive_replacement(self):
        """Replacement should be case-insensitive."""
        result = sanitize_text("The teal signal confirmed.")
        assert "teal" not in result.lower() or "GREEN" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST LLM OUTPUT SCRUBBING
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMOutputScrub:
    """Test post-LLM output scrubbing."""

    def test_scrub_preserves_negative_pnl(self):
        """Negative P&L should be preserved (transparency)."""
        text = "Portfolio is up. SPY declined -12.3% last quarter. Our system held strong."
        result = scrub_llm_output(text)
        assert "-12.3%" in result
        assert "Portfolio is up" in result

    def test_scrub_preserves_stopped_mentions(self):
        """STOPPED mentions should be preserved (transparency)."""
        text = "Winners are running. SMCI was STOPPED at $36. We focus on what works."
        result = scrub_llm_output(text)
        assert "STOPPED" in result
        assert "Winners are running" in result

    def test_scrub_preserves_positive_pnl(self):
        """Positive P&L should not be affected."""
        text = "Portfolio is up +25.0% year to date."
        result = scrub_llm_output(text)
        assert "+25.0%" in result

    def test_scrub_handles_empty_string(self):
        """Scrub should handle empty/None inputs."""
        assert scrub_llm_output("") == ""
        assert scrub_llm_output(None) is None

    def test_scrub_no_triple_newlines(self):
        """Scrub should not leave triple newlines after removals."""
        text = "Good paragraph.\n\nThis has -5.0% data.\n\nAnother good paragraph."
        result = scrub_llm_output(text)
        assert "\n\n\n" not in result

    def test_scrub_preserves_multiple_negatives(self):
        """Multiple negative P&L mentions should be preserved (transparency)."""
        text = "A lost -3.2%. B fell -7.5%. C gained +20.0%."
        result = scrub_llm_output(text)
        assert "-3.2%" in result
        assert "-7.5%" in result
        assert "+20.0%" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONTENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentValidation:
    """Test post content validation pipeline."""

    def test_clean_content_passes(self):
        """Clean marketing-compliant content should pass validation."""
        text = """
        This week, our proprietary screening system scanned 885 stocks and identified
        one GREEN signal. Momentum confirmed across AI infrastructure themes, with
        institutional accumulation driving the sector higher.
        """
        is_valid, issues = validate_post_content(text)
        assert is_valid, f"Clean content flagged: {issues}"

    def test_hma_fails_validation(self):
        """HMA mention should fail validation."""
        is_valid, _ = validate_post_content("The HMA pivot confirmed bullish structure.")
        assert not is_valid

    def test_conviction_score_fails(self):
        """Numeric conviction score should fail validation."""
        is_valid, _ = validate_post_content("Conviction score of 8/10.")
        assert not is_valid

    def test_negative_pnl_allowed(self):
        """Negative P&L should pass validation (transparency)."""
        is_valid, issues = validate_post_content("This position is at -12.5% from entry.")
        assert is_valid

    def test_stopped_position_allowed(self):
        """STOPPED position mentions should pass validation (transparency)."""
        is_valid, issues = validate_post_content("SMCI was STOPPED at $36.00.")
        assert is_valid

    def test_positive_pnl_passes(self):
        """Positive P&L should pass validation."""
        is_valid, _ = validate_post_content("Portfolio is up +25.0% year to date.")
        assert is_valid
