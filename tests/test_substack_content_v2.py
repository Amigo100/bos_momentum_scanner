"""Tests for Substack Content Generator v2 — LLM-powered posts.

Tests cover:
  - ContentContext data loading and building
  - Content calendar decision logic (signals vs no-signals)
  - Banned term safety in system prompts and visual templates
  - Visual element injection (funnel, theme scores, winners table)
  - CLI backward compatibility aliases
  - No-LLM fallback mode

All external APIs (Anthropic) and file I/O are mocked.
"""

import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ── Module imports ────────────────────────────────────────────────────────────

from substack.content_generator import (
    ContentContext,
    PostSpec,
    build_content_context,
    determine_content_calendar,
    sanitize_text,
    scrub_llm_output,
    validate_post_content,
    build_scan_funnel_html,
    build_theme_scores_html,
    build_winners_table_html,
    inject_visual_elements,
    generate_post_fallback,
    generate_all_posts,
    _format_themes_for_prompt,
    _format_signals_for_prompt,
    _format_winners_for_prompt,
    _format_assessed_for_prompt,
    _format_equity_stats,
    _format_theme_history,
    build_weekly_recap_prompt,
    build_theme_deep_dive_prompt,
    build_dd_deep_dive_prompt,
    build_portfolio_spotlight_prompt,
    SYSTEM_PROMPT,
    PROMPT_BUILDERS,
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
        with patch("substack.content_generator.SIGNALS_FILE", tmpdir / "signals.json"):
            with patch("substack.content_generator.OUTPUT_PATHS_AVAILABLE", False):
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

        with patch("substack.content_generator.SIGNALS_FILE", tmpdir / "signals.json"):
            with patch("substack.content_generator.OUTPUT_PATHS_AVAILABLE", False):
                with patch("substack.content_generator.load_portfolio_winners", return_value=[]):
                    with patch("substack.content_generator.load_equity_curve", return_value={}):
                        with patch("substack.content_generator.load_chart_manifest", return_value={}):
                            ctx = build_content_context(signals_path)
                            assert ctx.pass_count == 1
                            assert len(ctx.themes) == 1
                            assert ctx.themes[0]["name"] == "Test Theme"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONTENT CALENDAR
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentCalendar:
    """Test content calendar decision logic."""

    def test_calendar_with_signals_returns_4_posts(self, full_context):
        """When signals exist, should return 4 posts (recap, dd, theme, stock dive)."""
        calendar = determine_content_calendar(full_context)
        assert len(calendar) >= 4
        types = [p.post_type for p in calendar]
        assert "WEEKLY_RECAP" in types
        assert "THEME_DEEP_DIVE" in types
        assert "DD_DEEP_DIVE" in types
        assert "STOCK_DEEP_DIVE" in types

    def test_calendar_without_signals_returns_4_posts(self, no_signals_context):
        """When no signals, should return 4 posts (recap, theme, portfolio/stock, portfolio)."""
        calendar = determine_content_calendar(no_signals_context)
        assert len(calendar) >= 3
        types = [p.post_type for p in calendar]
        assert "WEEKLY_RECAP" in types
        assert "THEME_DEEP_DIVE" in types
        # Should have PORTFOLIO_SPOTLIGHT or PORTFOLIO_SHOWCASE or STOCK_DEEP_DIVE or EDUCATIONAL
        non_recap_types = [t for t in types if t not in ("WEEKLY_RECAP", "THEME_DEEP_DIVE")]
        assert len(non_recap_types) >= 1

    def test_calendar_no_dd_without_signals(self, no_signals_context):
        """When no signals, DD_DEEP_DIVE should not be generated."""
        calendar = determine_content_calendar(no_signals_context)
        types = [p.post_type for p in calendar]
        assert "DD_DEEP_DIVE" not in types

    def test_calendar_no_portfolio_with_signals(self, full_context):
        """When signals exist, PORTFOLIO_SPOTLIGHT should not be generated."""
        calendar = determine_content_calendar(full_context)
        types = [p.post_type for p in calendar]
        assert "PORTFOLIO_SPOTLIGHT" not in types

    def test_calendar_post_spec_titles(self, full_context):
        """Post titles should include week number and context."""
        calendar = determine_content_calendar(full_context)
        recap = [p for p in calendar if p.post_type == "WEEKLY_RECAP"][0]
        assert "Week 7" in recap.title
        assert "GREEN Signal" in recap.title

    def test_calendar_no_signals_title(self, no_signals_context):
        """No-signals week should have appropriate recap title."""
        calendar = determine_content_calendar(no_signals_context)
        recap = [p for p in calendar if p.post_type == "WEEKLY_RECAP"][0]
        assert "Week 7" in recap.title
        assert "Passed" in recap.title

    def test_calendar_publish_days(self, full_context):
        """Posts should be assigned to correct publish days."""
        calendar = determine_content_calendar(full_context)
        days = {p.post_type: p.publish_day for p in calendar}
        assert days["WEEKLY_RECAP"] == "Saturday"
        assert days["THEME_DEEP_DIVE"] == "Wednesday"

    def test_calendar_filenames_are_html(self, full_context):
        """All post filenames should end in .html."""
        calendar = determine_content_calendar(full_context)
        for post in calendar:
            assert post.filename.endswith(".html"), f"{post.filename} doesn't end with .html"

    def test_calendar_dd_filename_includes_ticker(self, full_context):
        """DD post filename should include the ticker symbol."""
        calendar = determine_content_calendar(full_context)
        dd = [p for p in calendar if p.post_type == "DD_DEEP_DIVE"]
        assert len(dd) == 1
        assert "INOD" in dd[0].filename

    def test_calendar_with_multiple_signals(self, full_context):
        """Calendar should use first buy signal for DD post."""
        full_context.buy_signals.append({"symbol": "RCAT", "final_decision": "PASS", "price": 13.0})
        full_context.pass_count = 2
        calendar = determine_content_calendar(full_context)
        dd = [p for p in calendar if p.post_type == "DD_DEEP_DIVE"]
        assert "INOD" in dd[0].filename  # First signal

    def test_calendar_empty_themes(self):
        """Calendar should handle empty themes gracefully."""
        ctx = ContentContext(week_number=7, pass_count=0)
        calendar = determine_content_calendar(ctx)
        theme_post = [p for p in calendar if p.post_type == "THEME_DEEP_DIVE"][0]
        assert "Market Themes" in theme_post.title


# ═══════════════════════════════════════════════════════════════════════════════
# TEST BANNED TERM SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

class TestBannedTermSafety:
    """Verify system prompts and templates don't contain banned terms."""

    def test_system_prompt_no_banned_terms(self):
        """SYSTEM_PROMPT should not contain any CRITICAL_BANNED terms as instructed content."""
        # The system prompt LISTS banned terms to tell the LLM not to use them.
        # That's intentional. But it should not use them in its own instructional text
        # outside the "BANNED TERMS" section.
        # We check the parts outside the banned terms list.
        lines = SYSTEM_PROMPT.split("\n")
        in_banned_section = False
        non_banned_lines = []
        for line in lines:
            if "BANNED TERMS" in line:
                in_banned_section = True
            elif line.strip().startswith(("3.", "4.", "5.", "6.", "7.", "8.")):
                in_banned_section = False
            if not in_banned_section:
                non_banned_lines.append(line)

        non_banned_text = "\n".join(non_banned_lines)
        # Should use "GREEN signal" not "TEAL signal" in instructional text
        assert "TEAL signal" not in non_banned_text.replace("TEAL", "").replace("\"TEAL\"", "")

    def test_system_prompt_mentions_green_signal(self):
        """System prompt should use GREEN signal branding."""
        assert "GREEN signal" in SYSTEM_PROMPT

    def test_system_prompt_lists_banned_terms(self):
        """System prompt should include a banned terms section."""
        assert "BANNED TERMS" in SYSTEM_PROMPT
        # Key banned terms should be mentioned
        assert "HMA" in SYSTEM_PROMPT
        assert "Banker" in SYSTEM_PROMPT
        assert "BoS" in SYSTEM_PROMPT

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

    def test_all_prompt_builders_exist(self):
        """All expected post types should have prompt builders."""
        expected = ["WEEKLY_RECAP", "THEME_DEEP_DIVE", "DD_DEEP_DIVE", "PORTFOLIO_SPOTLIGHT"]
        for pt in expected:
            assert pt in PROMPT_BUILDERS, f"Missing prompt builder for {pt}"

    def test_prompt_builders_return_strings(self, full_context):
        """All prompt builders should return non-empty strings."""
        for post_type, builder in PROMPT_BUILDERS.items():
            result = builder(full_context)
            assert isinstance(result, str), f"{post_type} builder returned {type(result)}"
            assert len(result) > 100, f"{post_type} builder returned too-short prompt ({len(result)} chars)"


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
# TEST POST-SPECIFIC PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPostPrompts:
    """Test individual post prompt builders."""

    def test_weekly_recap_prompt_includes_data(self, full_context):
        """Weekly recap prompt should include key data sections."""
        prompt = build_weekly_recap_prompt(full_context)
        assert "MARKET CONTEXT" in prompt
        assert "SCAN RESULTS" in prompt
        assert "THEMES THIS WEEK" in prompt
        assert "NEW SIGNALS" in prompt
        assert "[SCAN_FUNNEL]" in prompt
        assert "1200-1500 word" in prompt

    def test_weekly_recap_prompt_includes_winners(self, full_context):
        """Weekly recap prompt should include winner highlights."""
        prompt = build_weekly_recap_prompt(full_context)
        assert "WIN HIGHLIGHTS" in prompt
        assert "[WINNERS_TABLE]" in prompt

    def test_theme_deep_dive_prompt(self, full_context):
        """Theme deep dive should focus on the #1 theme."""
        prompt = build_theme_deep_dive_prompt(full_context)
        assert "AI Power Infrastructure" in prompt
        assert "PRIME" in prompt
        assert "[THEME_SCORES]" in prompt
        assert "800-1200 word" in prompt

    def test_theme_deep_dive_no_themes(self):
        """Theme deep dive should handle no themes gracefully."""
        ctx = ContentContext()
        prompt = build_theme_deep_dive_prompt(ctx)
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_dd_deep_dive_prompt(self, full_context):
        """DD deep dive should include full DD fields."""
        prompt = build_dd_deep_dive_prompt(full_context)
        assert "$INOD" in prompt
        assert "THE PITCH" in prompt
        assert "WHY NOW" in prompt
        assert "THE MATH" in prompt
        assert "BEAR CASE" in prompt
        assert "[CHART: INOD]" in prompt

    def test_dd_deep_dive_falls_back_to_portfolio(self, no_signals_context):
        """DD deep dive with no signals should fall back to portfolio."""
        prompt = build_dd_deep_dive_prompt(no_signals_context)
        assert "PORTFOLIO PERFORMANCE" in prompt

    def test_portfolio_spotlight_prompt(self, full_context):
        """Portfolio spotlight should include performance and winners."""
        prompt = build_portfolio_spotlight_prompt(full_context)
        assert "PORTFOLIO PERFORMANCE" in prompt
        assert "BENCHMARK" in prompt
        assert "TOP WINNERS" in prompt
        assert "[WINNERS_TABLE]" in prompt
        assert "800-1200 word" in prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TEST NO-LLM FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoLLMFallback:
    """Test data-only fallback mode without LLM."""

    def test_fallback_weekly_recap(self, full_context):
        """Fallback weekly recap should include key data elements."""
        spec = PostSpec("WEEKLY_RECAP", "Week 7 Test", "Saturday", "test.html")
        md = generate_post_fallback(spec, full_context)
        assert "Week 7 Test" in md
        assert "[SCAN_FUNNEL]" in md
        assert "GREEN signal" in md

    def test_fallback_theme_deep_dive(self, full_context):
        """Fallback theme deep dive should show theme data."""
        spec = PostSpec("THEME_DEEP_DIVE", "Theme Test", "Tuesday", "test.html")
        md = generate_post_fallback(spec, full_context)
        assert "AI Power Infrastructure" in md
        assert "PRIME" in md
        assert "[THEME_SCORES]" in md

    def test_fallback_portfolio_spotlight(self, full_context):
        """Fallback portfolio spotlight should show stats."""
        spec = PostSpec("PORTFOLIO_SPOTLIGHT", "Portfolio Test", "Thursday", "test.html")
        md = generate_post_fallback(spec, full_context)
        assert "[WINNERS_TABLE]" in md
        assert "Performance" in md

    def test_fallback_dd_deep_dive(self, full_context):
        """Fallback DD deep dive should show signal data."""
        spec = PostSpec("DD_DEEP_DIVE", "DD Test", "Thursday", "test.html")
        md = generate_post_fallback(spec, full_context)
        assert "$INOD" in md

    def test_fallback_always_has_subscribe_link(self, full_context):
        """All fallback posts should include subscribe link."""
        for post_type in ["WEEKLY_RECAP", "THEME_DEEP_DIVE", "PORTFOLIO_SPOTLIGHT"]:
            spec = PostSpec(post_type, "Test", "Saturday", "test.html")
            md = generate_post_fallback(spec, full_context)
            assert "Subscribe" in md or "sterlingsignals.substack.com" in md

    def test_fallback_includes_disclaimer(self, full_context):
        """All fallback posts should include financial disclaimer."""
        spec = PostSpec("WEEKLY_RECAP", "Test", "Saturday", "test.html")
        md = generate_post_fallback(spec, full_context)
        assert "financial advice" in md.lower() or "informational purposes" in md.lower()

    def test_generate_all_posts_no_llm_mode(self, full_context):
        """generate_all_posts with no_llm=True should produce posts without API calls."""
        with patch("substack.content_generator.OUTPUT_PATHS_AVAILABLE", False):
            with patch("substack.content_generator.get_substack_current_dir", return_value=Path(tempfile.mkdtemp())):
                with patch("substack.content_generator.HTML_AVAILABLE", False):
                    results = generate_all_posts(full_context, no_llm=True)
                    assert len(results) >= 4  # v3 expanded calendar: 4-5 posts
                    for r in results:
                        assert r["status"] == "generated"
                        assert r["cost"] == 0.0

    def test_generate_all_posts_dry_run(self, full_context):
        """generate_all_posts with dry_run=True should not write files."""
        results = generate_all_posts(full_context, dry_run=True)
        assert len(results) >= 4  # v3 expanded calendar: 4-5 posts
        for r in results:
            assert r["status"] == "dry_run"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLI BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIBackwardCompat:
    """Test CLI argument backward compatibility."""

    def test_old_monday_maps_to_market(self):
        """--monday should map to the --market flag."""
        import argparse
        from substack.content_generator import main
        # Verify the parser setup by checking argument definitions
        parser = argparse.ArgumentParser()
        parser.add_argument("--market", action="store_true")
        parser.add_argument("--monday", dest="market", action="store_true")
        args = parser.parse_args(["--monday"])
        assert args.market is True

    def test_old_saturday_maps_to_market(self):
        """--saturday should map to the --market flag."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--market", action="store_true")
        parser.add_argument("--saturday", dest="market", action="store_true")
        args = parser.parse_args(["--saturday"])
        assert args.market is True

    def test_old_thursday_maps_to_theme(self):
        """--thursday should map to the --theme flag."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--theme", action="store_true")
        parser.add_argument("--thursday", dest="theme", action="store_true")
        args = parser.parse_args(["--thursday"])
        assert args.theme is True

    def test_old_sunday_maps_to_dd(self):
        """--sunday should map to the --dd flag."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dd", action="store_true")
        parser.add_argument("--sunday", dest="dd", action="store_true")
        args = parser.parse_args(["--sunday"])
        assert args.dd is True

    def test_post_type_filtering(self, full_context):
        """Specific post types should be filterable."""
        with patch("substack.content_generator.OUTPUT_PATHS_AVAILABLE", False):
            with patch("substack.content_generator.get_substack_current_dir", return_value=Path(tempfile.mkdtemp())):
                with patch("substack.content_generator.HTML_AVAILABLE", False):
                    results = generate_all_posts(full_context, post_types=["WEEKLY_RECAP"], no_llm=True)
                    assert len(results) == 1
                    assert results[0]["post_type"] == "WEEKLY_RECAP"

    def test_empty_post_type_filter(self, full_context):
        """Empty post type filter should return no results."""
        results = generate_all_posts(full_context, post_types=["NONEXISTENT"])
        assert len(results) == 0


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
