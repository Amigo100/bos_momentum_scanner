"""Tests for core/daily_scanner.py — Daily Timeframe Scanner.

All tests use mocked data so they never hit yfinance or real markets.
"""

import csv
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ── Module under test ─────────────────────────────────────────────────────────
from scanner.daily_scanner import (
    DailySignal,
    DailyTrade,
    calculate_bos_daily,
    check_daily_sell_signals,
    deduplicate,
    load_daily_portfolio,
    run_daily_scan,
    save_daily_portfolio,
    save_daily_signals,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

def _make_df(n: int = 120, base_price: float = 100.0, trend: float = 0.001) -> pd.DataFrame:
    """Create a synthetic daily OHLCV DataFrame.

    Args:
        n: number of bars
        base_price: starting close price
        trend: daily drift (positive = uptrend)
    """
    dates = pd.bdate_range(end=datetime.now(), periods=n, freq="B")
    np.random.seed(42)
    noise = np.random.normal(0, 0.01, n)
    cumulative = np.exp(np.cumsum(np.array([trend + noise[i] for i in range(n)])))
    close = base_price * cumulative
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    opens = close * (1 + np.random.normal(0, 0.002, n))
    volume = np.random.randint(100_000, 10_000_000, n).astype(float)
    return pd.DataFrame(
        {"Open": opens, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )


def _make_spy_returns(n: int = 120) -> pd.Series:
    """Synthetic SPY daily returns."""
    dates = pd.bdate_range(end=datetime.now(), periods=n, freq="B")
    np.random.seed(99)
    return pd.Series(np.random.normal(0.0004, 0.01, n), index=dates)


def _make_candidate(ticker: str, price: float, beta: float, banker: float):
    """Helper to build a (ticker, price, beta, banker) tuple as run_daily_scan uses internally."""
    return (ticker, price, beta, banker)


def _write_csv(path: Path, rows: list, fieldnames: list):
    """Write a list of dicts to CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDailyScannerMax5Signals:
    """Test 1: Only top 5 signals by Banker score are returned."""

    @patch("scanner.daily_scanner.download_daily_data")
    @patch("scanner.daily_scanner.download_spy_returns")
    @patch("scanner.daily_scanner.load_tickers")
    @patch("scanner.daily_scanner._get_ticker_info", return_value=("Technology", "Software"))
    def test_daily_scanner_max_5_signals(
        self, mock_info, mock_tickers, mock_spy, mock_download
    ):
        # 10 tickers that all pass technical gates
        tickers = [f"SYM{i}" for i in range(10)]
        mock_tickers.return_value = tickers

        spy_ret = _make_spy_returns(120)
        mock_spy.return_value = spy_ret

        # Build frames that will pass all gates:
        # High beta, high banker, BoS up
        frames = {}
        for i, sym in enumerate(tickers):
            df = _make_df(120, base_price=50 + i * 10, trend=0.002)
            frames[sym] = df
        mock_download.return_value = frames

        # Patch indicator functions so all 10 pass
        with (
            patch("scanner.daily_scanner.calculate_beta", return_value=2.0),
            patch("scanner.daily_scanner.calculate_banker", side_effect=lambda df: (60 + hash(str(df.index[0])) % 20, 50)),
            patch("scanner.daily_scanner.calculate_bos_daily", return_value=(True, False, {})),
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                dp_path = Path(tmpdir) / "daily_portfolio.csv"
                wp_path = Path(tmpdir) / "portfolio.csv"
                sig_path = Path(tmpdir) / "daily_signals.json"

                signals = run_daily_scan(
                    daily_portfolio_path=dp_path,
                    weekly_portfolio_path=wp_path,
                    signals_output_path=sig_path,
                )

                # Max 5 signals
                assert len(signals) <= 5, f"Expected <=5, got {len(signals)}"
                assert len(signals) == 5, f"Expected exactly 5, got {len(signals)}"


class TestDailyScannerDedupWeekly:
    """Test 2: Tickers with OPEN weekly positions are excluded."""

    @patch("scanner.daily_scanner.download_daily_data")
    @patch("scanner.daily_scanner.download_spy_returns")
    @patch("scanner.daily_scanner.load_tickers")
    @patch("scanner.daily_scanner._get_ticker_info", return_value=("Tech", "Software"))
    def test_daily_scanner_dedup_weekly(
        self, mock_info, mock_tickers, mock_spy, mock_download
    ):
        tickers = ["AAPL", "MSFT", "GOOG"]
        mock_tickers.return_value = tickers
        mock_spy.return_value = _make_spy_returns()
        mock_download.return_value = {t: _make_df() for t in tickers}

        with (
            patch("scanner.daily_scanner.calculate_beta", return_value=2.0),
            patch("scanner.daily_scanner.calculate_banker", return_value=(70.0, 60.0)),
            patch("scanner.daily_scanner.calculate_bos_daily", return_value=(True, False, {})),
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                dp_path = Path(tmpdir) / "daily_portfolio.csv"
                wp_path = Path(tmpdir) / "portfolio.csv"
                sig_path = Path(tmpdir) / "daily_signals.json"

                # Write AAPL as OPEN in weekly portfolio
                _write_csv(
                    wp_path,
                    [{"ticker": "AAPL", "status": "OPEN", "entry_date": "2026-01-01",
                      "entry_price": "150.00", "exit_date": "", "exit_price": "",
                      "highest_close": "160.00", "theme": "", "tier": "",
                      "signal_type": "", "conviction": "", "notes": "", "stop_pct": ""}],
                    ["ticker", "status", "entry_date", "entry_price", "exit_date",
                     "exit_price", "highest_close", "theme", "tier", "signal_type",
                     "conviction", "notes", "stop_pct"],
                )

                signals = run_daily_scan(
                    daily_portfolio_path=dp_path,
                    weekly_portfolio_path=wp_path,
                    signals_output_path=sig_path,
                )

                signal_tickers = {s.ticker for s in signals}
                assert "AAPL" not in signal_tickers, "AAPL should be excluded (weekly OPEN)"
                assert "MSFT" in signal_tickers or "GOOG" in signal_tickers


class TestDailyScannerDedupRecent:
    """Test 3: Tickers signalled within lookback are excluded; outside lookback are included."""

    def test_daily_scanner_dedup_recent(self):
        today = datetime.now()

        # MSFT signalled 3 days ago, still OPEN → should be excluded
        trade_recent = DailyTrade(
            ticker="MSFT",
            entry_date=(today - timedelta(days=3)).strftime("%Y-%m-%d"),
            status="OPEN",
        )

        # TSLA signalled 6 days ago, still OPEN → outside 5-day lookback → included
        trade_old = DailyTrade(
            ticker="TSLA",
            entry_date=(today - timedelta(days=6)).strftime("%Y-%m-%d"),
            status="OPEN",
        )

        daily_trades = [trade_recent, trade_old]

        result = deduplicate(
            tickers=["MSFT", "TSLA", "NVDA"],
            daily_trades=daily_trades,
            weekly_open=set(),
            lookback_days=5,
        )

        assert "MSFT" not in result, "MSFT signalled 3 days ago should be excluded"
        assert "TSLA" in result, "TSLA signalled 6 days ago should be included"
        assert "NVDA" in result, "NVDA never signalled should be included"


class TestDailyScannerDedupAfterSell:
    """Test 4: Ticker re-eligible after an intervening sell signal."""

    def test_daily_scanner_dedup_after_sell(self):
        today = datetime.now()

        # GOOG signalled 2 days ago, then stopped → should be eligible again
        trade_stopped = DailyTrade(
            ticker="GOOG",
            entry_date=(today - timedelta(days=2)).strftime("%Y-%m-%d"),
            status="STOPPED",
            exit_date=(today - timedelta(days=1)).strftime("%Y-%m-%d"),
            exit_price=150.0,
            exit_reason="Trailing stop",
        )

        daily_trades = [trade_stopped]

        result = deduplicate(
            tickers=["GOOG"],
            daily_trades=daily_trades,
            weekly_open=set(),
            lookback_days=5,
        )

        assert "GOOG" in result, "GOOG should be eligible — intervening sell resets dedup"


class TestDailySellSignalBearishPivot:
    """Test 5: BoS bearish pivot should CLOSE the position immediately."""

    def test_daily_sell_signal_bearish_pivot(self):
        trade = DailyTrade(
            ticker="TEST",
            entry_date="2026-01-20",
            entry_price=100.0,
            highest_close=120.0,
            stop_pct=20.0,
            status="OPEN",
        )

        df = _make_df(120, base_price=115.0)  # close above trailing stop level

        # Mock BoS returning bearish signal
        with patch("scanner.daily_scanner.calculate_bos_daily", return_value=(False, True, {})):
            sells = check_daily_sell_signals([trade], {"TEST": df})

        # BoS Down should CLOSE the trade immediately
        assert trade.status == "STOPPED", f"Expected STOPPED, got {trade.status}"
        assert len(sells) == 1, "BoS Down should produce exactly one sell signal"
        assert sells[0].ticker == "TEST"
        assert "BoS Down" in sells[0].exit_reason
        assert sells[0].exit_price > 0


class TestDailyBoSDownPriority:
    """BoS Down takes priority over trailing stop (no double-exit)."""

    def test_bos_down_takes_priority_over_trailing_stop(self):
        """If price is below trailing stop AND BoS fires, only one exit."""
        trade = DailyTrade(
            ticker="TEST",
            entry_date="2026-01-01",
            entry_price=50.0,
            highest_close=100.0,
            stop_pct=20.0,
            status="OPEN",
        )

        df = _make_df(120, base_price=79.0)

        with patch("scanner.daily_scanner.calculate_bos_daily", return_value=(False, True, {})):
            sells = check_daily_sell_signals([trade], {"TEST": df})

        assert len(sells) == 1, f"Expected 1 sell signal, got {len(sells)}"
        assert "BoS Down" in sells[0].exit_reason
        assert trade.status == "STOPPED"


class TestDailySellSignalTrailingStop:
    """Test 6: Price below trailing stop marks position STOPPED."""

    def test_daily_sell_signal_trailing_stop(self):
        trade = DailyTrade(
            ticker="TEST",
            entry_date="2026-01-01",
            entry_price=50.0,
            highest_close=100.0,
            stop_pct=20.0,
            status="OPEN",
        )

        # Create df where close is $79 (below $80 = 100 * 0.80)
        df = _make_df(120, base_price=79.0, trend=0.0)
        # Override the last close to exactly 79
        df.iloc[-1, df.columns.get_loc("Close")] = 79.0

        with patch("scanner.daily_scanner.calculate_bos_daily", return_value=(False, False, {})):
            sells = check_daily_sell_signals([trade], {"TEST": df})

        assert trade.status == "STOPPED", f"Expected STOPPED, got {trade.status}"
        assert len(sells) == 1
        assert sells[0].ticker == "TEST"
        assert sells[0].exit_price == 79.0


class TestDailyPortfolioAtomicWrites:
    """Test 7: Atomic write doesn't corrupt original CSV on failure."""

    def test_daily_portfolio_atomic_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "daily_portfolio.csv"
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            # Write initial portfolio
            original_trades = [
                DailyTrade(ticker="AAPL", entry_price=150.0, status="OPEN"),
            ]
            save_daily_portfolio(original_trades, path)

            # Verify it was written
            loaded = load_daily_portfolio(path)
            assert len(loaded) == 1
            assert loaded[0].ticker == "AAPL"

            # Now simulate a crash during write by patching os.replace to fail
            with patch("scanner.daily_scanner.os.replace", side_effect=OSError("Simulated crash")):
                new_trades = [
                    DailyTrade(ticker="MSFT", entry_price=300.0, status="OPEN"),
                    DailyTrade(ticker="GOOG", entry_price=150.0, status="OPEN"),
                ]
                with pytest.raises(OSError, match="Simulated crash"):
                    save_daily_portfolio(new_trades, path)

            # Original file should be intact
            loaded_after = load_daily_portfolio(path)
            assert len(loaded_after) == 1, "Original CSV should be intact after crash"
            assert loaded_after[0].ticker == "AAPL"


class TestDailySignalsJsonOutput:
    """Test 8: daily_signals.json has correct structure."""

    def test_daily_signals_json_output_format(self):
        signals = [
            DailySignal(ticker="AAPL", price=185.50, beta=1.72, banker_score=68, sector="Technology", industry="Consumer Electronics"),
            DailySignal(ticker="NVDA", price=450.00, beta=2.10, banker_score=75, sector="Technology", industry="Semiconductors"),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = Path(f.name)

        try:
            save_daily_signals(signals, out_path)
            with open(out_path) as f:
                data = json.load(f)

            assert "scan_date" in data
            assert data["timeframe"] == "daily"
            assert "buy_signals" in data
            assert len(data["buy_signals"]) == 2

            sig = data["buy_signals"][0]
            assert sig["ticker"] == "AAPL"
            assert sig["price"] == 185.50
            assert sig["beta"] == 1.72
            assert sig["banker_score"] == 68
            assert sig["sector"] == "Technology"
            assert sig["industry"] == "Consumer Electronics"
        finally:
            out_path.unlink(missing_ok=True)


class TestDailyScanEmptyResults:
    """Test 9: No signals → empty list, no crash, portfolio unchanged."""

    @patch("scanner.daily_scanner.download_daily_data")
    @patch("scanner.daily_scanner.download_spy_returns")
    @patch("scanner.daily_scanner.load_tickers")
    def test_daily_scan_empty_results(self, mock_tickers, mock_spy, mock_download):
        mock_tickers.return_value = ["AAPL", "MSFT"]
        mock_spy.return_value = _make_spy_returns()
        mock_download.return_value = {t: _make_df() for t in ["AAPL", "MSFT"]}

        # All tickers fail technical gate (beta too low)
        with patch("scanner.daily_scanner.calculate_beta", return_value=0.5):
            with tempfile.TemporaryDirectory() as tmpdir:
                dp_path = Path(tmpdir) / "daily_portfolio.csv"
                wp_path = Path(tmpdir) / "portfolio.csv"
                sig_path = Path(tmpdir) / "daily_signals.json"

                # Pre-populate daily portfolio to ensure it isn't corrupted
                existing = [DailyTrade(ticker="TSLA", entry_price=200.0, status="OPEN")]
                save_daily_portfolio(existing, dp_path)

                signals = run_daily_scan(
                    daily_portfolio_path=dp_path,
                    weekly_portfolio_path=wp_path,
                    signals_output_path=sig_path,
                )

                assert signals == [], "Should return empty list"

                # Portfolio should remain unchanged (TSLA still there)
                loaded = load_daily_portfolio(dp_path)
                assert len(loaded) == 1
                assert loaded[0].ticker == "TSLA"


class TestDailySellNotificationCalled:
    """Test 10: send_sell_notification() called when trailing stop triggers."""

    def test_daily_sell_notification_called(self):
        trade = DailyTrade(
            ticker="RCAT",
            entry_date="2026-01-15",
            entry_price=10.00,
            highest_close=15.00,
            stop_pct=20.0,
            theme="Drone Technology",
            status="OPEN",
        )

        # Close at $11.50, below stop of $12.00 (15 * 0.80)
        df = _make_df(120, base_price=11.5, trend=0.0)
        df.iloc[-1, df.columns.get_loc("Close")] = 11.50

        with patch("scanner.daily_scanner.calculate_bos_daily", return_value=(False, False, {})):
            sells = check_daily_sell_signals([trade], {"RCAT": df})

        assert len(sells) == 1
        assert sells[0].status == "STOPPED"

        # Now test that _send_daily_sell_notifications calls send_sell_notification
        from scanner.daily_scanner import _send_daily_sell_notifications

        with patch("utils.notifications.send_sell_notification") as mock_notify:
            _send_daily_sell_notifications(sells)

            mock_notify.assert_called_once()
            kwargs = mock_notify.call_args.kwargs
            assert kwargs["ticker"] == "RCAT"
            assert kwargs["timeframe"] == "daily"
            assert kwargs["entry_price"] == 10.00
            assert kwargs["theme"] == "Drone Technology"
