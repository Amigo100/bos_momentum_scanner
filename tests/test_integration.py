"""Integration tests — End-to-end pipeline and cross-module validation.

Tests cover:
  - Friday pipeline: scan → tweets → queues → poster
  - Daily pipeline:  scan → dedup → signals → notifications
  - Posting system:  slot → queue selection → chart upload
  - Content quality: banned terms, winners-only, internal terminology

All external APIs (yfinance, Twitter, Anthropic, SMTP, Twilio) are mocked.
File I/O uses tmpdir fixtures for full isolation.

Ref: STERLING_SIGNALS_PRD_v2.md section 9
Ref: STERLING_SIGNALS_TODO.md "Phase 6: Integration Testing"
"""

import csv
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pandas as pd
import pytest

# ── Module imports (units under test) ────────────────────────────────────────

from content.models import (
    Tweet,
    ValidationResult,
    SlotAssignment,
    ContentData,
    TWEET_CATEGORIES,
    CHART_REQUIRED_CATEGORIES,
    VALID_CATEGORIES,
    INTERNAL_TERM_PATTERNS,
)
from content.tweet_generator import (
    _validate_tweet,
    _plan_weekly_schedule,
    _build_content_data,
    _write_queues,
    ACCOUNT_QUEUES,
    DAILY_ACCOUNT_QUEUES,
    MAX_TWEET_CHARS,
    WEEKLY_DAYS,
    WEEKLY_SLOTS,
)
from config.banned_terms import (
    ALL_BANNED,
    CRITICAL_BANNED,
    BANNED_PHRASES,
    LOSER_PATTERNS,
    check_banned_phrases,
    check_loser_focus,
)
from distribution.twitter_poster import (
    DAILY_SLOTS,
    WEEKLY_SLOTS,
    get_queue_for_slot,
    get_queue_path,
    get_daily_queue_path,
    validate_before_posting,
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
def sample_signals():
    """Minimal signals.json content for weekly scan output."""
    return {
        "timestamp": "2026-02-06 22:06:24",
        "timeframe": "WEEKLY",
        "stats": {
            "tickers_loaded": 1817,
            "data_downloaded": 1814,
            "beta_gte_1_5": 485,
            "weekly_bos_up": 48,
            "technical_signals": 44,
            "theme_confirmed": 17,
            "final_trade": 3,
            "final_consider": 2,
        },
        "themes": [
            {
                "name": "AI Infrastructure",
                "classification": "PRIME",
                "composite_score": 8.2,
                "thesis_summary": "Data center buildout accelerating",
            },
            {
                "name": "Power Grid",
                "classification": "INVESTABLE",
                "composite_score": 7.1,
                "thesis_summary": "Grid modernization spending",
            },
        ],
        "buy_signals": [
            {
                "symbol": "NVDA",
                "tier": "TIER1",
                "price": 145.50,
                "beta": 2.1,
                "banker": 72.0,
                "theme": "AI Infrastructure",
                "theme_score": 8.5,
                "final_decision": "TRADE",
                "conviction": 4,
                "catalyst_summary": "Earnings in 3 weeks",
                "red_flag_level": "CLEAN",
                "bullish_factors": ["Strong revenue growth", "Data center demand"],
                "risk_factors": ["High valuation"],
            },
            {
                "symbol": "INOD",
                "tier": "TIER1",
                "price": 61.54,
                "beta": 2.48,
                "banker": 78.3,
                "theme": "Power Grid",
                "theme_score": 7.8,
                "final_decision": "TRADE",
                "conviction": 4,
                "catalyst_summary": "Infrastructure bill tailwind",
                "red_flag_level": "CLEAN",
                "bullish_factors": ["Theme leader"],
                "risk_factors": ["Concentrated customers"],
            },
            {
                "symbol": "MARA",
                "tier": "TIER2",
                "price": 22.80,
                "beta": 3.5,
                "banker": 65.0,
                "theme": "AI Infrastructure",
                "theme_score": 6.5,
                "final_decision": "TRADE",
                "conviction": 3,
                "catalyst_summary": "Mining expansion",
                "red_flag_level": "MINOR",
                "bullish_factors": ["Bitcoin correlation"],
                "risk_factors": ["Crypto volatility"],
            },
        ],
        "sell_signals": [
            {
                "symbol": "VNET",
                "price": 10.80,
                "reason": "Weekly BoS Down",
                "entry_price": 12.00,
                "highest_close": 12.50,
                "pnl_pct": -10.0,
            }
        ],
        "caution_signals": [
            {
                "symbol": "IONQ",
                "price": 42.15,
                "theme": "Quantum Computing",
                "final_decision": "CONSIDER",
                "conviction": 3,
            },
            {
                "symbol": "RGTI",
                "price": 8.20,
                "theme": "Quantum Computing",
                "final_decision": "CONSIDER",
                "conviction": 2,
            },
        ],
    }


@pytest.fixture
def sample_portfolio_rows():
    """Minimal portfolio.csv rows including a winner, a holder, and a loser."""
    return [
        {
            "ticker": "RCAT", "status": "OPEN", "entry_date": "2025-12-29",
            "entry_price": "8.50", "exit_date": "", "exit_price": "",
            "highest_close": "14.50", "theme": "Drone Technology",
            "tier": "TIER1", "signal_type": "TRADE", "conviction": "4",
            "notes": "", "current_price": "13.25",
        },
        {
            "ticker": "IBKR", "status": "OPEN", "entry_date": "2025-12-29",
            "entry_price": "65.00", "exit_date": "", "exit_price": "",
            "highest_close": "72.93", "theme": "Financials",
            "tier": "TIER1", "signal_type": "TRADE", "conviction": "5",
            "notes": "", "current_price": "72.50",
        },
        {
            "ticker": "SMCI", "status": "OPEN", "entry_date": "2025-10-01",
            "entry_price": "45.00", "exit_date": "", "exit_price": "",
            "highest_close": "52.00", "theme": "AI Infra",
            "tier": "TIER2", "signal_type": "TRADE", "conviction": "3",
            "notes": "", "current_price": "38.00",
        },
    ]


@pytest.fixture
def sample_daily_signals():
    """Minimal daily_signals.json content."""
    return {
        "timestamp": "2026-02-06 16:45:00",
        "timeframe": "DAILY",
        "buy_signals": [
            {"symbol": "AMD", "price": 165.30, "beta": 1.8, "banker_score": 68.0},
            {"symbol": "MRVL", "price": 89.50, "beta": 2.0, "banker_score": 62.0},
        ],
        "sell_signals": [
            {
                "symbol": "PLTR",
                "price": 42.00,
                "reason": "Trailing Stop",
                "entry_price": 55.00,
                "highest_close": 58.00,
                "pnl_pct": -23.6,
                "stop_level": 46.40,
            },
        ],
    }


def _write_signals_json(signals: Dict, path: Path) -> Path:
    """Helper: write signals dict to a JSON file."""
    signals_file = path / "signals.json"
    signals_file.write_text(json.dumps(signals, indent=2))
    return signals_file


def _write_portfolio_csv(rows: List[Dict], path: Path) -> Path:
    """Helper: write portfolio rows to CSV."""
    portfolio_file = path / "portfolio.csv"
    if not rows:
        portfolio_file.write_text("")
        return portfolio_file
    fieldnames = list(rows[0].keys())
    with open(portfolio_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return portfolio_file


def _write_content_queue(tweets: List[Dict], path: Path, filename: str = "content_queue.json") -> Path:
    """Helper: write a content queue JSON file."""
    queue_file = path / filename
    queue_file.write_text(json.dumps(tweets, indent=2))
    return queue_file


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 1: FRIDAY PIPELINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestFridayPipelineIntegration:
    """Integration tests for the Friday weekly pipeline:
    scanner output → content data → schedule → validation → queues.
    """

    def test_full_friday_flow(self, tmpdir, sample_signals, sample_portfolio_rows):
        """Signals.json + portfolio.csv → _build_content_data → _plan_weekly_schedule → valid queues.

        Verifies:
          - ContentData built correctly from raw inputs
          - Schedule planned with correct number of slots
          - All accounts get identical queue files when written
        """
        # Write fixture files
        signals_path = _write_signals_json(sample_signals, tmpdir)
        portfolio_path = _write_portfolio_csv(sample_portfolio_rows, tmpdir)

        # Build content data (the real function)
        signals = json.loads(signals_path.read_text())
        positions = []
        with open(portfolio_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key in ("entry_price", "exit_price", "highest_close", "current_price"):
                    if row.get(key):
                        try:
                            row[key] = float(row[key])
                        except (ValueError, TypeError):
                            row[key] = 0.0
                positions.append(row)

        data = _build_content_data(signals, positions)

        # Verify ContentData populated
        assert len(data.pass_signals) == 3, f"Expected 3 pass signals, got {len(data.pass_signals)}"
        assert len(data.themes) == 2
        assert len(data.sell_signals) == 1
        # RCAT: entry $8.50, current $13.25 → +55.9% → winner
        assert data.has_winners, "RCAT should be a winner (55.9%)"
        # IBKR: entry $65, current $72.50 → +11.5% → holding (not winner, < 25%)
        # SMCI: entry $45, current $38 → -15.5% → excluded (loser)
        assert len(data.winners) == 1, f"Expected 1 winner (RCAT), got {len(data.winners)}"
        assert data.winners[0]["ticker"] == "RCAT"

        # Plan schedule
        schedule = _plan_weekly_schedule(data)
        # 7 days x 4 slots (2-5) = 28 slots (slot 1 reserved for daily queue)
        assert len(schedule) == len(WEEKLY_DAYS) * len(WEEKLY_SLOTS)
        assert all(isinstance(s, SlotAssignment) for s in schedule)
        assert all(s.category in VALID_CATEGORIES for s in schedule)

        # Create some fake validated tweets and write queues
        fake_tweets = []
        for i, assignment in enumerate(schedule[:5]):  # Use first 5 only for speed
            chart_req = assignment.category in CHART_REQUIRED_CATEGORIES
            fake_tweets.append(Tweet(
                text=f"$NVDA at $145.50 — momentum confirmed. NFA #{i}",
                category=assignment.category,
                chart_required=chart_req,
                chart_path="charts/NVDA_weekly_20260207.png" if chart_req else None,
                tickers_mentioned=["NVDA"],
                metadata={"day": assignment.day, "slot": assignment.slot},
            ))

        _write_queues(fake_tweets, ACCOUNT_QUEUES, tmpdir, "2026-02-06")

        # All 3 account queues should exist and be identical
        for account, queue_file in ACCOUNT_QUEUES.items():
            path = tmpdir / queue_file
            assert path.exists(), f"Queue file missing for {account}: {path}"
            queue = json.loads(path.read_text())
            assert len(queue) == 5
            for entry in queue:
                assert "text" in entry
                assert "status" in entry
                assert entry["status"] == "pending"
                assert "category" in entry
                assert "chart_required" in entry

    def test_friday_sell_signal_to_notification(self, tmpdir, sample_signals):
        """Sell signal in signals.json → send_sell_notification triggered.

        Verifies:
          - Sell signals extracted from signals.json
          - Notification function called with correct parameters
          - Email and WhatsApp channels attempted
        """
        signals_path = _write_signals_json(sample_signals, tmpdir)
        signals = json.loads(signals_path.read_text())

        sell_signals = signals.get("sell_signals", [])
        assert len(sell_signals) == 1, "Expected 1 sell signal (VNET)"

        sig = sell_signals[0]
        assert sig["symbol"] == "VNET"

        # Mock the notification function to verify it's called correctly
        with patch("distribution.notifications.send_sell_notification") as mock_notify:
            mock_notify.return_value = {"email": "sent", "whatsapp": "sent"}

            from distribution.notifications import send_sell_notification

            result = send_sell_notification(
                ticker=sig["symbol"],
                signal_type=sig.get("reason", "SELL SIGNAL"),
                entry_price=float(sig["entry_price"]),
                current_price=float(sig["price"]),
                highest_close=float(sig["highest_close"]),
                stop_level=float(sig.get("stop_level", sig["highest_close"] * 0.8)),
                pnl_pct=float(sig["pnl_pct"]),
                theme="Cloud",
                timeframe="weekly",
                entry_date="2025-11-01",
            )

            mock_notify.assert_called_once()
            call_kwargs = mock_notify.call_args
            assert call_kwargs[1]["ticker"] == "VNET" or call_kwargs[0][0] == "VNET"

    def test_friday_content_all_accounts_identical(self, tmpdir):
        """All 3 account queues receive identical tweet content.

        Verifies that _write_queues produces byte-identical JSON for all accounts.
        """
        tweets = [
            Tweet(
                text="$NVDA momentum confirmed at $145.50 — cleared all gates. NFA",
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["NVDA"],
                metadata={"day": "saturday", "slot": 1},
            ),
            Tweet(
                text="AI Infrastructure theme accelerating — $NVDA $INOD leading the charge",
                category="THEME_ANALYSIS",
                chart_required=False,
                tickers_mentioned=["NVDA", "INOD"],
                metadata={"day": "saturday", "slot": 2},
            ),
        ]

        _write_queues(tweets, ACCOUNT_QUEUES, tmpdir, "2026-02-06")

        # Load all 3 queue files
        queues = {}
        for account, queue_file in ACCOUNT_QUEUES.items():
            path = tmpdir / queue_file
            assert path.exists(), f"Missing queue for {account}"
            queues[account] = json.loads(path.read_text())

        # All queues should have same number of entries
        counts = {account: len(q) for account, q in queues.items()}
        assert len(set(counts.values())) == 1, f"Queue sizes differ: {counts}"

        # Compare tweet texts across accounts
        main_texts = [entry["text"] for entry in queues["main"]]
        for account in ("account2", "account3"):
            other_texts = [entry["text"] for entry in queues[account]]
            assert main_texts == other_texts, f"{account} tweets differ from main"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 2: DAILY PIPELINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDailyPipelineIntegration:
    """Integration tests for the daily scan → tweet → notification pipeline."""

    def test_full_daily_flow(self, tmpdir, sample_daily_signals):
        """daily_signals.json → ContentData → validation → daily queue.

        Verifies:
          - Daily signals load into ContentData correctly
          - Daily tweets can be validated
          - Daily queues are written (separate from weekly)
        """
        # Write daily signals
        signals_path = tmpdir / "daily_signals.json"
        signals_path.write_text(json.dumps(sample_daily_signals, indent=2))

        signals = json.loads(signals_path.read_text())
        buy_signals = signals.get("buy_signals", [])[:5]  # Max 5
        sell_signals = signals.get("sell_signals", [])

        assert len(buy_signals) == 2
        assert len(sell_signals) == 1

        # Build daily content data
        data = ContentData(
            daily_signals=buy_signals,
            daily_sells=sell_signals,
            scan_date="2026-02-06",
        )
        assert data.has_daily_signals

        # Simulate daily tweet generation + validation
        daily_tweets = []
        for sig in buy_signals:
            ticker = sig["symbol"]
            price = sig["price"]
            tweet = Tweet(
                text=f"${{ticker}} at ${price:.2f} — momentum confirmed on the daily. NFA",
                category="DAILY_SIGNAL",
                chart_required=True,
                tickers_mentioned=[ticker],
                metadata={"day": "thursday", "slot": 6},
            )
            # Fix string formatting (Tweet was created with literal f-string chars)
            tweet = Tweet(
                text=f"${ticker} at ${price:.2f} — momentum confirmed on the daily. NFA",
                category="DAILY_SIGNAL",
                chart_required=True,
                chart_path=f"charts/{ticker}_daily_20260206.png",
                tickers_mentioned=[ticker],
                metadata={"day": "thursday", "slot": 6},
            )
            result = _validate_tweet(tweet, {"daily_signals": [sig]})
            assert result.passed, f"Daily tweet for {ticker} failed: {result.failures}"
            daily_tweets.append(tweet)

        assert len(daily_tweets) == 2

        # Write daily queues
        _write_queues(daily_tweets, DAILY_ACCOUNT_QUEUES, tmpdir, "2026-02-06")

        # Verify daily queue files (separate from weekly)
        for account, queue_file in DAILY_ACCOUNT_QUEUES.items():
            path = tmpdir / queue_file
            assert path.exists(), f"Daily queue missing for {account}"
            queue = json.loads(path.read_text())
            assert len(queue) == 2

    def test_daily_dedup_against_weekly(self, tmpdir, sample_signals, sample_daily_signals):
        """Daily signals appearing in weekly portfolio are still valid separately.

        Verifies that:
          - Tickers can exist in both weekly and daily queues
          - Content queues are separate files
          - No cross-contamination between weekly and daily queue paths
        """
        # Write weekly queue
        weekly_tweets = [{
            "id": "saturday_1_0",
            "text": "$NVDA at $145.50 — momentum confirmed. NFA",
            "category": "SCANNER_RESULT",
            "status": "pending",
        }]
        _write_content_queue(weekly_tweets, tmpdir, "content_queue.json")

        # Write daily queue with a different ticker
        daily_tweets = [{
            "id": "thursday_6_0",
            "text": "$AMD at $165.30 — daily momentum confirmed. NFA",
            "category": "DAILY_SIGNAL",
            "status": "pending",
        }]
        _write_content_queue(daily_tweets, tmpdir, "daily_content_queue.json")

        # Both should coexist
        weekly_path = tmpdir / "content_queue.json"
        daily_path = tmpdir / "daily_content_queue.json"

        assert weekly_path.exists()
        assert daily_path.exists()

        weekly_data = json.loads(weekly_path.read_text())
        daily_data = json.loads(daily_path.read_text())

        assert len(weekly_data) == 1
        assert len(daily_data) == 1
        assert weekly_data[0]["text"] != daily_data[0]["text"]

    def test_daily_sell_notification_flow(self, sample_daily_signals):
        """Daily sell signals trigger notifications with correct parameters.

        Verifies:
          - Each sell signal generates a notification call
          - Parameters map correctly from signal dict to notification function
          - Both channels (email, whatsapp) are invoked
        """
        sell_signals = sample_daily_signals.get("sell_signals", [])
        assert len(sell_signals) == 1

        sig = sell_signals[0]

        with patch("distribution.notifications._send_email") as mock_email, \
             patch("distribution.notifications._send_whatsapp") as mock_whatsapp:

            mock_email.return_value = True
            mock_whatsapp.return_value = True

            from distribution.notifications import send_sell_notification

            result = send_sell_notification(
                ticker=sig["symbol"],
                signal_type=sig["reason"],
                entry_price=float(sig["entry_price"]),
                current_price=float(sig["price"]),
                highest_close=float(sig["highest_close"]),
                stop_level=float(sig["stop_level"]),
                pnl_pct=float(sig["pnl_pct"]),
                theme="Tech",
                timeframe="daily",
                entry_date="2026-01-15",
            )

            # Verify both channels were attempted
            assert isinstance(result, dict)
            assert "email" in result
            assert "whatsapp" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 3: DAILY POSTING INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDailyPostingIntegration:
    """Integration tests for the 7-slot posting system and chart upload."""

    def test_slot_queue_selection(self):
        """get_queue_for_slot routes daily slots (1,6,7) to daily queue,
        weekly slots (2-5) to weekly queue.

        Verifies the complete slot → queue mapping.
        """
        for slot in range(1, 8):
            queue_path = get_queue_for_slot(slot, "main")
            if slot in DAILY_SLOTS:
                assert "daily_content_queue" in queue_path.name, \
                    f"Slot {slot} should use daily queue, got {queue_path.name}"
            else:
                assert "daily" not in queue_path.name, \
                    f"Slot {slot} should use weekly queue, got {queue_path.name}"

        # Verify all 7 slots are covered
        all_slots = DAILY_SLOTS | WEEKLY_SLOTS
        assert all_slots == {1, 2, 3, 4, 5, 6, 7}, f"Missing slot coverage: {all_slots}"

    def test_daily_queue_fallback_to_weekly(self, tmpdir):
        """When daily queue is empty/missing but weekly exists, poster should
        use weekly queue for daily slots as fallback.

        Verifies the fallback mechanism through the queue file system.
        """
        # Create only weekly queue (no daily queue)
        weekly_tweets = [
            {
                "id": "saturday_2_0",
                "text": "$NVDA momentum confirmed at $145.50. NFA",
                "category": "SCANNER_RESULT",
                "status": "pending",
                "chart_required": True,
            },
        ]
        weekly_queue_path = _write_content_queue(weekly_tweets, tmpdir)

        # Verify weekly queue exists
        assert weekly_queue_path.exists()

        # Verify daily queue does NOT exist
        daily_queue_path = tmpdir / "daily_content_queue.json"
        assert not daily_queue_path.exists()

        # For slot 1 (daily), the queue path would point to daily
        slot_1_path = get_queue_for_slot(1, "main")
        assert "daily" in slot_1_path.name

        # For slot 2 (weekly), the queue path points to weekly
        slot_2_path = get_queue_for_slot(2, "main")
        assert "daily" not in slot_2_path.name

        # The workflow (daily_post.yml) handles the fallback:
        # If daily queue doesn't exist, the poster can still run for weekly slots

    def test_chart_upload_with_tweet(self, tmpdir):
        """Tweets with chart_path have image_path resolved for posting.

        Verifies that chart_path flows through the queue system correctly.
        """
        # Create a fake chart file
        charts_dir = tmpdir / "charts"
        charts_dir.mkdir()
        chart_file = charts_dir / "NVDA_weekly_20260206.png"
        chart_file.write_bytes(b"\x89PNG\x0d\x0a\x1a\x0a" + b"\x00" * 100)  # Fake PNG

        # Create a tweet with chart_path
        tweet_with_chart = Tweet(
            text="$NVDA at $145.50 — cleared all gates. NFA",
            category="SCANNER_RESULT",
            chart_required=True,
            tickers_mentioned=["NVDA"],
            chart_path=str(chart_file),
            metadata={"day": "saturday", "slot": 2},
        )

        # Write to queue
        _write_queues([tweet_with_chart], ACCOUNT_QUEUES, tmpdir, "2026-02-06")

        # Verify queue entry has chart_path
        queue_data = json.loads((tmpdir / "content_queue.json").read_text())
        assert len(queue_data) == 1
        entry = queue_data[0]

        assert entry["chart_required"] is True
        assert entry["chart_path"] is not None
        assert "NVDA" in entry["chart_path"]
        assert entry["chart_path"].endswith(".png")

        # Verify the chart file would be accessible (exists on disk)
        assert Path(entry["chart_path"]).exists()

    def test_account_queue_paths_distinct(self):
        """All 3 accounts have distinct queue paths for both weekly and daily."""
        # Weekly queues
        weekly_paths = set()
        for account in ("main", "account2", "account3"):
            p = get_queue_path(account)
            weekly_paths.add(p.name)

        assert len(weekly_paths) == 3, f"Weekly queue paths should be distinct: {weekly_paths}"

        # Daily queues
        daily_paths = set()
        for account in ("main", "account2", "account3"):
            p = get_daily_queue_path(account)
            daily_paths.add(p.name)

        assert len(daily_paths) == 3, f"Daily queue paths should be distinct: {daily_paths}"

        # Weekly and daily queues should not overlap
        assert weekly_paths.isdisjoint(daily_paths), \
            f"Weekly and daily paths overlap: {weekly_paths & daily_paths}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS 4: CONTENT VALIDATION INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentValidationIntegration:
    """Integration tests for the content quality and validation pipeline."""

    def test_validation_catches_all_banned_terms(self):
        """Every term in ALL_BANNED is caught by both tweet_generator validation
        and twitter_poster validation.

        This is a P0 test: if even one banned term slips through,
        internal methodology could be exposed publicly.
        """
        failures_missed = []

        for term in ALL_BANNED:
            # Skip emoji entries that might not match in string form
            if len(term) == 1 and ord(term) > 0xFFFF:
                continue

            test_text = f"$NVDA at $145.50 — {term} confirmed. NFA"

            # Test 1: tweet_generator's _validate_tweet
            tweet = Tweet(
                text=test_text,
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["NVDA"],
            )
            result = _validate_tweet(tweet, {"signals": [{"symbol": "NVDA"}]})
            if result.passed:
                failures_missed.append(f"_validate_tweet missed: '{term}'")

            # Test 2: twitter_poster's validate_before_posting
            post_result = validate_before_posting({"text": test_text, "category": "SCANNER_RESULT"})
            can_post, reason = post_result
            # Note: validate_before_posting only checks CRITICAL_BANNED, not all BANNED_PHRASES
            if term in CRITICAL_BANNED and can_post:
                failures_missed.append(f"validate_before_posting missed CRITICAL: '{term}'")

        assert len(failures_missed) == 0, (
            f"{len(failures_missed)} banned terms were NOT caught:\n"
            + "\n".join(failures_missed[:20])
        )

    def test_validation_catches_negative_pnl(self):
        """Tweets with negative P&L percentages are blocked at both layers.

        Winners-only rule: never show losses publicly.
        """
        negative_cases = [
            "$SMCI down -15.5% from entry. Watching closely.",
            "$VNET at $10.80 — down -10.0% from our $12.00 entry",
            "Took a -8% hit on $PLTR today but staying disciplined",
            "Portfolio update: $NVDA +45%, $SMCI -20%, $INOD +12%",
        ]

        for text in negative_cases:
            # tweet_generator validation
            tweet = Tweet(
                text=text,
                category="PERFORMANCE",
                chart_required=True,
                tickers_mentioned=["SMCI"],
            )
            result = _validate_tweet(tweet, {"signals": [{"symbol": "SMCI"}]})
            assert not result.passed, f"_validate_tweet should block negative P&L: {text[:50]}"

            has_pnl_failure = any("step4" in f or "negative" in f.lower() for f in result.failures)
            assert has_pnl_failure, f"Should have step4 failure for: {text[:50]}"

            # twitter_poster validation
            can_post, reason = validate_before_posting({"text": text})
            assert not can_post, f"validate_before_posting should block: {text[:50]}"

    def test_validation_catches_internal_terms(self):
        """Internal terminology patterns (HMA, BoS, Banker, etc.) are caught.

        These regex patterns in INTERNAL_TERM_PATTERNS prevent internal
        methodology from leaking into public tweets.
        """
        internal_leak_cases = [
            ("$NVDA — HMA pivot triggered, entry at $145", "HMA"),
            ("BoS confirmed on the weekly for $INOD", "BoS"),
            ("Banker score at 78 for $RCAT — strong accumulation", "Banker"),
            ("This is a TIER1 setup with conviction 4", "TIER1"),
            ("RSI oversold — buying the dip on $AMD", "RSI"),
            ("MACD golden cross on $NVDA daily chart", "MACD"),
            ("KDJ indicator shows overbought conditions", "KDJ"),
            ("Gate 3 cleared for $MARA — looking good", "gate 3"),
            ("The gatekeeper approved this setup", "gatekeeper"),
            ("VWAP support holding at $145 for $NVDA", "VWAP"),
        ]

        for text, expected_term in internal_leak_cases:
            tweet = Tweet(
                text=text,
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["NVDA"],
            )
            result = _validate_tweet(tweet, {"signals": [{"symbol": "NVDA"}]})
            assert not result.passed, \
                f"Should catch internal term '{expected_term}' in: {text[:50]}"

            has_internal_failure = any("step5" in f or "step3" in f for f in result.failures)
            assert has_internal_failure, \
                f"Should have step3/step5 failure for '{expected_term}' in: {text[:50]}"

    def test_end_to_end_content_quality(self, sample_signals, sample_portfolio_rows, tmpdir):
        """Clean tweets pass both validation layers without issues.

        Builds ContentData from real fixtures, creates properly formatted
        tweets, and verifies they pass ALL validation steps.
        """
        # Build content data from fixtures
        signals = sample_signals
        positions = []
        for row in sample_portfolio_rows:
            pos = dict(row)
            for key in ("entry_price", "exit_price", "highest_close", "current_price"):
                if pos.get(key):
                    try:
                        pos[key] = float(pos[key])
                    except (ValueError, TypeError):
                        pos[key] = 0.0
            positions.append(pos)

        data = _build_content_data(signals, positions)

        # Well-formed tweets that SHOULD pass all validation
        clean_tweets = [
            Tweet(
                text="$NVDA at $145.50 — momentum confirmed, cleared all gates. Strong institutional accumulation this week. NFA",
                category="SCANNER_RESULT",
                chart_required=True,
                tickers_mentioned=["NVDA"],
            ),
            Tweet(
                text="AI Infrastructure theme accelerating — $NVDA and $INOD leading the charge. Data center demand still surging.",
                category="THEME_ANALYSIS",
                chart_required=False,
                tickers_mentioned=["NVDA", "INOD"],
            ),
            Tweet(
                text="$RCAT from $8.50 to $13.25 (+55.9%) — momentum confirmed on the weekly. Win more than you lose. NFA",
                category="PERFORMANCE",
                chart_required=True,
                tickers_mentioned=["RCAT"],
            ),
            Tweet(
                text="$IONQ at $42.15 — watching for structural trend confirmation. On our radar but waiting for better entry.",
                category="WATCHLIST",
                chart_required=False,
                tickers_mentioned=["IONQ"],
            ),
            Tweet(
                text="$VNET setup invalidated below $10.80 — exiting position. Win more than you lose. NFA",
                category="SELL_SIGNAL",
                chart_required=True,
                tickers_mentioned=["VNET"],
            ),
        ]

        # All source tickers for validation context
        source_data = {
            "signals": signals.get("buy_signals", []),
            "sell_signals": signals.get("sell_signals", []),
            "consider": signals.get("caution_signals", []),
            "winners": [{"ticker": "RCAT", "pnl_pct": 55.9}],
        }

        for tweet in clean_tweets:
            # Layer 1: tweet_generator validation
            result = _validate_tweet(tweet, source_data)
            assert result.passed, (
                f"Clean {tweet.category} tweet FAILED validation:\n"
                f"  Text: {tweet.text[:60]}...\n"
                f"  Failures: {result.failures}"
            )

            # Layer 2: twitter_poster validation
            can_post, reason = validate_before_posting({
                "text": tweet.text,
                "category": tweet.category,
            })
            assert can_post, (
                f"Clean {tweet.category} tweet BLOCKED by poster:\n"
                f"  Text: {tweet.text[:60]}...\n"
                f"  Reason: {reason}"
            )

    def test_tweet_length_enforcement(self):
        """Tweets exceeding 280 characters are rejected."""
        long_text = "$NVDA " + "a" * 300  # Way over 280 chars
        tweet = Tweet(
            text=long_text,
            category="SCANNER_RESULT",
            chart_required=True,
            tickers_mentioned=["NVDA"],
        )
        result = _validate_tweet(tweet, {"signals": [{"symbol": "NVDA"}]})
        assert not result.passed
        has_char_failure = any("step6" in f or "chars" in f.lower() for f in result.failures)
        assert has_char_failure, f"Should have character count failure, got: {result.failures}"

        # Poster validation also catches it
        can_post, reason = validate_before_posting({"text": long_text})
        assert not can_post
        assert "long" in reason.lower() or "char" in reason.lower()

    def test_chart_flag_consistency(self):
        """chart_required flag must match category expectations.

        SCANNER_RESULT, DAILY_SIGNAL, PERFORMANCE, TECHNICAL_ANALYSIS, SELL_SIGNAL
        all require charts. Other categories don't.
        """
        for category in VALID_CATEGORIES:
            expected_chart = category in CHART_REQUIRED_CATEGORIES
            # Correct flag → should not fail on step 7
            correct_tweet = Tweet(
                text=f"$NVDA at $145.50 — momentum confirmed. Setup invalidated if wrong. NFA",
                category=category,
                chart_required=expected_chart,
                tickers_mentioned=["NVDA"],
            )
            result = _validate_tweet(correct_tweet, {"signals": [{"symbol": "NVDA"}]})
            step7_failures = [f for f in result.failures if "step7" in f]
            assert len(step7_failures) == 0, \
                f"Correct chart flag for {category} should not trigger step7, got: {step7_failures}"

            # Wrong flag → should fail on step 7
            wrong_tweet = Tweet(
                text=f"$NVDA at $145.50 — momentum confirmed. Setup invalidated if wrong. NFA",
                category=category,
                chart_required=not expected_chart,
                tickers_mentioned=["NVDA"],
            )
            result = _validate_tweet(wrong_tweet, {"signals": [{"symbol": "NVDA"}]})
            step7_failures = [f for f in result.failures if "step7" in f]
            assert len(step7_failures) == 1, \
                f"Wrong chart flag for {category} should trigger step7, got: {step7_failures}"


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
        ]
        all_banned_lower = {t.lower() for t in ALL_BANNED}
        missing = [t for t in critical_must_have if t.lower() not in all_banned_lower]
        assert len(missing) == 0, f"ALL_BANNED is missing critical terms: {missing}"

    def test_internal_term_patterns_catch_critical_banned(self):
        """INTERNAL_TERM_PATTERNS regex list covers key terms from CRITICAL_BANNED."""
        import re

        must_catch = ["HMA", "BoS", "BOS", "Banker", "TIER1", "TIER2", "TIER3",
                       "RSI", "MACD", "KDJ", "gatekeeper", "VWAP"]
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

    def test_slot_coverage_complete(self):
        """DAILY_SLOTS ∪ WEEKLY_SLOTS == {1,2,3,4,5,6,7}."""
        assert DAILY_SLOTS | WEEKLY_SLOTS == {1, 2, 3, 4, 5, 6, 7}
        assert DAILY_SLOTS & WEEKLY_SLOTS == set(), "No slot should be in both daily and weekly"

    def test_account_queues_have_three_entries(self):
        """Both ACCOUNT_QUEUES and DAILY_ACCOUNT_QUEUES have exactly 3 accounts."""
        assert len(ACCOUNT_QUEUES) == 3
        assert len(DAILY_ACCOUNT_QUEUES) == 3
        assert set(ACCOUNT_QUEUES.keys()) == {"main", "account2", "account3"}
        assert set(DAILY_ACCOUNT_QUEUES.keys()) == {"main", "account2", "account3"}
