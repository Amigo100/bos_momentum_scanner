#!/usr/bin/env python3
"""
Integration test for the full tweet generation pipeline [4A.9.27].

Validates that generate_weekly_content() produces a correct, diverse,
fabrication-free tweet queue when given realistic mock data and a mocked
LLM client. No API keys or network calls required.

Asserts ALL of:
  1. Zero fabricated tickers in data-dependent tweets
  2. Zero LLM meta-language ("cannot generate", "$TICKER" literal, etc.)
  3. $MATV in ≤ 40% of tweets (overexposure prevention)
  4. ≥ 1 PERFORMANCE tweet
  5. ≥ 1 WATCHLIST tweet
  6. No chart_required=True + chart_path=None in output queue
  7. No duplicate opening phrases (first 60 chars unique)
  8. No slot 1 in weekly queue
  9. All SELL_SIGNAL tickers exist in portfolio
  10. ≥ 5 categories represented

Ref: TWEET_GEN_FIX_TODO.md [4A.9.27]
"""

import csv
import json
import os
import re
from pathlib import Path

import pytest

try:
    from twitter.tweet_generator import (
        generate_weekly_content,
        DATA_DEPENDENT_CATEGORIES,
    )
    _IMPORTS_OK = True
except ImportError:
    _IMPORTS_OK = False

skipif_no_imports = pytest.mark.skipif(
    not _IMPORTS_OK,
    reason="twitter.tweet_generator not importable",
)


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════════════════════════════════════════

MOCK_SIGNALS = {
    "timestamp": "2026-02-07",
    "buy_signals": [
        {
            "symbol": "MATV",
            "price": 14.55,
            "tier": "TIER1",
            "theme": "Materials",
            "theme_score": 7.8,
            "pure_play_score": 80,
            "theme_verdict": "STRONG FIT",
            "final_decision": "TRADE",
            "conviction": 4,
            "catalyst_summary": "Earnings in 2 weeks, sector rotation",
            "red_flag_level": "CLEAN",
            "bullish_factors": ["Sector rotation", "Institutional accumulation"],
            "risk_factors": ["Small cap volatility"],
            "reasoning": "Strong momentum confirmation",
            "action": "Enter Monday at market open",
        },
    ],
    "consider_signals": [
        {"symbol": "AAPL", "price": 225.00, "theme": "Tech", "action": "CONSIDER",
         "catalyst_summary": "Awaiting confirmation"},
        {"symbol": "GOOG", "price": 180.00, "theme": "AI", "action": "CONSIDER",
         "catalyst_summary": "Needs volume confirmation"},
    ],
    "sell_signals": [
        {"symbol": "LUMN", "price": 5.20, "reason": "Weekly BoS Down", "action": "SELL",
         "entry_price": 8.50, "pnl_pct": -38.8},
    ],
    "themes": [
        {"name": "Materials", "classification": "PRIME", "composite_score": 7.8,
         "thesis_summary": "Infrastructure spending cycle", "theme_type": "TREND"},
        {"name": "AI Infrastructure", "classification": "INVESTABLE", "composite_score": 7.2,
         "thesis_summary": "Data center buildout", "theme_type": "TREND"},
    ],
    "stats": {
        "tickers_loaded": 1800,
        "data_downloaded": 1795,
        "beta_gte_1_5": 485,
        "weekly_bos_up": 48,
        "technical_signals": 44,
        "theme_confirmed": 17,
        "final_trade": 1,
        "final_consider": 2,
    },
}

MOCK_PORTFOLIO_ROWS = [
    {
        "ticker": "WCC", "status": "OPEN", "entry_date": "2026-01-13",
        "entry_price": "281", "exit_date": "", "exit_price": "",
        "highest_close": "320", "theme": "Infrastructure", "tier": "TIER1",
        "signal_type": "TRADE", "conviction": "4", "notes": "",
        "current_price": "315",
    },
    {
        "ticker": "STRL", "status": "OPEN", "entry_date": "2026-01-13",
        "entry_price": "362", "exit_date": "", "exit_price": "",
        "highest_close": "410", "theme": "Construction", "tier": "TIER1",
        "signal_type": "TRADE", "conviction": "4", "notes": "",
        "current_price": "401",
    },
    {
        "ticker": "MOD", "status": "OPEN", "entry_date": "2026-01-13",
        "entry_price": "184", "exit_date": "", "exit_price": "",
        "highest_close": "220", "theme": "Energy", "tier": "TIER2",
        "signal_type": "TRADE", "conviction": "3", "notes": "",
        "current_price": "215",
    },
    {
        "ticker": "LUMN", "status": "OPEN", "entry_date": "2026-01-13",
        "entry_price": "8.50", "exit_date": "", "exit_price": "",
        "highest_close": "9.00", "theme": "Telecom", "tier": "TIER3",
        "signal_type": "TRADE", "conviction": "2", "notes": "",
        "current_price": "5.20",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK LLM TWEETS — one per category, all pass validation
# ═══════════════════════════════════════════════════════════════════════════════

# Multiple variants per category to avoid duplicate openings.
# The mock client cycles through these with a counter.

MOCK_TWEET_VARIANTS = {
    "SCANNER_RESULT": [
        "$MATV at $14.55 — cleared all gates. Materials momentum confirmed. NFA!",
        "1,800 stocks scanned. $MATV survived all 5 gates at $14.55. Full details in the newsletter.",
        "Friday scan complete. $MATV at $14.55 is this week's signal. Materials theme strong.",
    ],
    "THEME_ANALYSIS": [
        "Materials theme gaining momentum. $MATV leading the infrastructure spending cycle.",
        "AI Infrastructure accelerating. $MATV positioned in the supply chain buildout.",
        "Two themes on radar this week. $MATV riding the Materials wave. Sector flow aligned.",
        "Infrastructure spending fueling Materials. $MATV at the center. Momentum confirmed.",
    ],
    "PERFORMANCE": [
        "$WCC in at $281, now $315. +12% and trailing stop locked. NFA!",
        "$STRL from $362 to $401. Patience paying off. Trailing stop secured. NFA!",
        "$MOD entry at $184, sitting at $215. +17% momentum intact. NFA!",
        "Portfolio update: $WCC +12%, $STRL +11%, $MOD +17%. Trailing stops in place.",
        "Three open positions, all green. $WCC leading at +12%. Discipline paying off.",
        "$STRL making moves from $362 entry. Now $401. Not selling winners early.",
        "Entry on $MOD at $184, currently $215. +17% and the trend is intact. NFA!",
        "$WCC proving the thesis. Entry $281, now $315. Stop locked. Let it ride. NFA!",
        "$STRL +11% since entry. $362 to $401. Momentum confirmed. Patience wins. NFA!",
        "$MOD at $215 from $184 entry. +17% gain. Trailing stop doing its job. NFA!",
    ],
    "WATCHLIST": [
        "Watching $AAPL at $225. Needs one more confirmation to signal. NFA!",
        "$GOOG at $180 on the radar. Close to triggering but not there yet.",
        "$AAPL and $GOOG on the watchlist. Waiting for confirmation before acting.",
    ],
    "SELL_SIGNAL": [
        "$LUMN setup invalidated. Structural trend broken. Capital preserved. NFA!",
        "$LUMN exit triggered. Structural trend confirmation failed. Moving on. NFA!",
    ],
    "EDUCATIONAL": [
        "Position sizing matters more than stock picking. Risk-defined entries, always.",
        "Five gates exist because 'good stock' is subjective. Gates are binary.",
        "Why weekly timeframe? Less noise, fewer decisions, better sleep.",
        "Trailing stops protect what you've earned. Not about maximizing — about keeping.",
        "Win rate matters less than win size. Make more when right, lose less when wrong.",
        "The scanner doesn't care about opinions. That's the whole point. Data over ego.",
        "Discipline means executing the plan even when it feels wrong. Especially then.",
        "One trade won't make your year. One bad habit will break it. Focus on process.",
        "People ask how many trades per week. Answer: as many as pass all 5 gates. Sometimes zero.",
        "Risk management isn't about avoiding losses. It's about surviving them.",
    ],
    "ENGAGEMENT": [
        "Biggest lesson from 2025: stop arguing with the data. What's yours?",
        "Bad day in the market? Everyone has them. Don't let it become a bad week.",
        "What trading lesson took you the longest to learn? Mine was patience.",
        "New traders: what's the hardest part so far? Drop it below.",
        "If you could tell your past self one trading lesson, what would it be?",
        "Lazy Sunday question: what got you into trading?",
    ],
    "NEWSLETTER_CTA": [
        "This week's scanner found 1 signal from 1,800 stocks. Full breakdown in the newsletter.",
        "Every Friday: scan, filter, signal. This week's results are now live.",
        "1,800 stocks. 5 gates. 1 survivor. Read the full analysis in the newsletter.",
    ],
    "TECHNICAL_ANALYSIS": [
        "$STRL holding above $390 support. Entry at $362. Invalidation below $380. NFA!",
        "$WCC key level at $300. Holding strong above it. Trailing stop locked in. NFA!",
        "$MOD testing $210 support from $184 entry. Invalidation below $200. NFA!",
    ],
    "MARKET_COMMENTARY": [
        "Choppy tape this week. Days like this reward patience, not FOMO.",
        "Quiet morning usually means afternoon fireworks. Or nothing. We wait and see.",
        "Rotation happening in real time. Following the flows, not the noise.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK ANTHROPIC CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class _MockUsage:
    input_tokens = 500
    output_tokens = 80


class _MockContent:
    def __init__(self, text: str):
        self.text = text


class _MockResponse:
    def __init__(self, text: str):
        self.content = [_MockContent(text)]
        self.usage = _MockUsage()


class _MockMessages:
    """Mock for client.messages — returns pre-written tweets based on category in prompt."""

    def __init__(self):
        self._counters = {}  # Track how many times each category has been called

    def create(self, **kwargs):
        user_msg = kwargs.get("messages", [{}])[0].get("content", "")

        # Detect category from the prompt text
        # _build_user_prompt starts with "Generate a single {CATEGORY} tweet."
        # _repair_tweet includes "CATEGORY: {category}"
        detected_category = None

        # Try exact category match (order matters — check longer names first)
        ordered_categories = [
            "SCANNER_RESULT", "THEME_ANALYSIS", "TECHNICAL_ANALYSIS",
            "MARKET_COMMENTARY", "NEWSLETTER_CTA", "SELL_SIGNAL",
            "DAILY_SIGNAL", "PERFORMANCE", "WATCHLIST",
            "EDUCATIONAL", "ENGAGEMENT",
        ]
        for cat in ordered_categories:
            if cat in user_msg:
                detected_category = cat
                break

        if detected_category is None:
            detected_category = "EDUCATIONAL"

        # Get the variant list and cycle through
        variants = MOCK_TWEET_VARIANTS.get(detected_category, MOCK_TWEET_VARIANTS["EDUCATIONAL"])
        idx = self._counters.get(detected_category, 0)
        tweet_text = variants[idx % len(variants)]
        self._counters[detected_category] = idx + 1

        return _MockResponse(tweet_text)


class _MockClient:
    """Mock Anthropic client that returns pre-written tweets."""

    def __init__(self, **kwargs):
        self.messages = _MockMessages()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _write_signals_json(tmp_dir: Path) -> Path:
    """Write mock signals to a temp JSON file."""
    path = tmp_dir / "signals.json"
    with open(path, "w") as f:
        json.dump(MOCK_SIGNALS, f, indent=2)
    return path


def _write_portfolio_csv(tmp_dir: Path) -> Path:
    """Write mock portfolio to a temp CSV file."""
    path = tmp_dir / "portfolio.csv"
    fieldnames = list(MOCK_PORTFOLIO_ROWS[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in MOCK_PORTFOLIO_ROWS:
            writer.writerow(row)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════════════

@skipif_no_imports
class TestFullPipelineIntegration:
    """
    End-to-end integration test: generate_weekly_content() with mocked LLM.

    Validates ALL 10 quality assertions from TWEET_GEN_FIX_TODO.md [4A.9.27].
    """

    def test_full_pipeline_integration(self, tmp_path, monkeypatch):
        """Run full pipeline with mock data and assert all 10 quality criteria."""

        # ── Setup: write mock data files ──────────────────────────────────
        signals_path = _write_signals_json(tmp_path)
        portfolio_path = _write_portfolio_csv(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # ── Mock: Anthropic client → _MockClient ─────────────────────────
        # Patch at the module level where it's imported
        monkeypatch.setattr(
            "twitter.tweet_generator.anthropic.Anthropic",
            _MockClient,
        )

        # Ensure ANTHROPIC_API_KEY is set so generate_weekly_content doesn't bail
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-integration")

        # ── Mock: _attach_chart_paths → simulate chart attachment ────────
        # In tests, no real chart files exist. Replace _attach_chart_paths
        # so chart-required tweets get a dummy chart_path instead of being
        # dropped by _write_queues.
        def _mock_attach_charts(tweets, charts_dir=None):
            attached = 0
            for tweet in tweets:
                if tweet.chart_required and not tweet.chart_path:
                    tweet.chart_path = f"/tmp/mock_charts/{tweet.category.lower()}.png"
                    attached += 1
            return attached

        monkeypatch.setattr(
            "twitter.tweet_generator._attach_chart_paths",
            _mock_attach_charts,
        )

        # ── Run the pipeline ─────────────────────────────────────────────
        result = generate_weekly_content(
            signals_path=str(signals_path),
            portfolio_path=str(portfolio_path),
            output_dir=str(output_dir),
        )

        # ── Load the output queue ────────────────────────────────────────
        queue_path = output_dir / "content_queue.json"
        assert queue_path.exists(), f"Queue file not created at {queue_path}"

        with open(queue_path, "r") as f:
            queue = json.load(f)

        assert len(queue) > 0, "Queue is empty — no tweets generated"

        # ── Allowed tickers from source data ─────────────────────────────
        allowed_tickers = {"MATV", "AAPL", "GOOG", "LUMN", "WCC", "STRL", "MOD"}
        portfolio_tickers = {"WCC", "STRL", "MOD", "LUMN"}

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 1: Zero fabricated tickers in data-dependent tweets
        # ═════════════════════════════════════════════════════════════════
        for entry in queue:
            if entry["category"] in DATA_DEPENDENT_CATEGORIES:
                for ticker in entry.get("mentioned_tickers", []):
                    clean = ticker.lstrip("$")
                    assert clean in allowed_tickers, (
                        f"FABRICATED ticker {ticker} in {entry['category']} tweet: "
                        f"{entry['text'][:80]}..."
                    )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 2: Zero LLM meta-language
        # ═════════════════════════════════════════════════════════════════
        meta_patterns = [
            "cannot generate", "please provide", "$TICKER",
            "i need the specific", "i don't have",
        ]
        for entry in queue:
            text_lower = entry["text"].lower()
            for pat in meta_patterns:
                assert pat.lower() not in text_lower, (
                    f"Meta-language '{pat}' found in tweet: {entry['text'][:80]}..."
                )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 3: $MATV in ≤ 40% of tweets (overexposure prevention)
        # ═════════════════════════════════════════════════════════════════
        matv_count = sum(1 for e in queue if "$MATV" in e["text"])
        max_matv = int(len(queue) * 0.4) + 1  # Allow rounding grace
        assert matv_count <= max_matv, (
            f"$MATV overexposure: appears in {matv_count}/{len(queue)} tweets "
            f"({matv_count / len(queue) * 100:.0f}%), max allowed ~40%"
        )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 4: ≥ 1 PERFORMANCE tweet
        # ═════════════════════════════════════════════════════════════════
        categories = [e["category"] for e in queue]
        assert "PERFORMANCE" in categories, (
            f"No PERFORMANCE tweet generated. Categories: {set(categories)}"
        )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 5: ≥ 1 WATCHLIST tweet
        # ═════════════════════════════════════════════════════════════════
        assert "WATCHLIST" in categories, (
            f"No WATCHLIST tweet generated. Categories: {set(categories)}"
        )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 6: No chart_required=True + chart_path=None in queue
        # ═════════════════════════════════════════════════════════════════
        for entry in queue:
            if entry.get("chart_required", False):
                # _write_queues already drops these, so none should appear
                assert entry.get("chart_path") is not None, (
                    f"Chart required but missing for {entry['category']}: "
                    f"{entry['text'][:60]}..."
                )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 7: No duplicate opening phrases (first 60 chars)
        # ═════════════════════════════════════════════════════════════════
        openings = [e["text"][:60] for e in queue]
        duplicates = [o for o in openings if openings.count(o) > 1]
        assert len(set(duplicates)) == 0, (
            f"Duplicate opening phrases found: {set(duplicates)}"
        )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 8: No slot 1 in weekly queue
        # ═════════════════════════════════════════════════════════════════
        for entry in queue:
            assert entry["slot"] != 1, (
                f"Slot 1 found in weekly queue: {entry['id']}"
            )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 9: All SELL_SIGNAL tickers exist in portfolio
        # ═════════════════════════════════════════════════════════════════
        for entry in queue:
            if entry["category"] == "SELL_SIGNAL":
                for ticker in entry.get("mentioned_tickers", []):
                    clean = ticker.lstrip("$")
                    assert clean in portfolio_tickers, (
                        f"SELL_SIGNAL ticker {ticker} not in portfolio "
                        f"(valid: {portfolio_tickers})"
                    )

        # ═════════════════════════════════════════════════════════════════
        # ASSERTION 10: ≥ 5 categories represented
        # ═════════════════════════════════════════════════════════════════
        unique_categories = set(categories)
        assert len(unique_categories) >= 5, (
            f"Only {len(unique_categories)} categories represented: "
            f"{unique_categories}. Expected ≥ 5."
        )

        # ── Summary report ───────────────────────────────────────────────
        print(f"\n{'=' * 60}")
        print(f"INTEGRATION TEST PASSED")
        print(f"{'=' * 60}")
        print(f"  Total tweets in queue: {len(queue)}")
        print(f"  Categories: {dict((c, categories.count(c)) for c in unique_categories)}")
        print(f"  $MATV exposure: {matv_count}/{len(queue)} ({matv_count / len(queue) * 100:.0f}%)")
        print(f"  Pipeline result: {result}")
        print(f"{'=' * 60}")
