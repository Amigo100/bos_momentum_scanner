"""Unit tests for scanner/sterling_indicators.py — the V10 doctrine.

V10 contract under test:
  ENTRY: buy_signal == bare HMA(21) pivot low on a completed weekly bar.
  EXIT : check_tiered_initial_35 only — -35% hard floor below +50% gain;
         tiered trailing lock from peak close above (+50%→25%, +100%→20%, +200%→15%).
  Everything else (RSI/MACD/UC/ATR) is informational context — never a gate.

Replaces the V6/V8-era suite (quality tiers, sizing, ExD exits — all removed by doctrine).
"""

import numpy as np
import pandas as pd
import pytest

from scanner.sterling_indicators import (
    HMA_PERIOD,
    RSI_PERIOD,
    LOCK_TIERS,
    INITIAL_STOP_PCT,
    MIN_WEEKLY_BARS,
    _wma,
    calculate_hma,
    calculate_hma_pivots,
    calculate_rsi,
    calculate_macd,
    calculate_undercurrent,
    calculate_atr_squeeze,
    generate_entry_signal,
    check_profit_lock,
    check_tiered_initial_35,
    compute_peak_close,
    resample_to_weekly,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def weekly_frame(closes, start="2024-01-05"):
    """Weekly OHLCV frame (W-FRI index) from a close series."""
    idx = pd.date_range(start, periods=len(closes), freq="W-FRI")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({
        "open": c.shift(1).fillna(c.iloc[0]),
        "high": c * 1.02,
        "low": c * 0.98,
        "close": c,
        "volume": 1_000_000.0,
    })


def daily_frame(dates, closes):
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({
        "Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6,
    })


def v_bottom_closes(n_flat=30, n_down=15, n_up=15, top=100.0, bottom=60.0):
    """A clean V with a flat lead-in long enough to clear the HMA warm-up
    (~23 weekly bars of NaN) so the pivot lands on computed HMA values."""
    flat = np.full(n_flat, top)
    down = np.linspace(top, bottom, n_down)
    up = np.linspace(bottom, top, n_up)
    return np.concatenate([flat, down[1:], up[1:]])


# ═══════════════════════════════════════════════════════════════════════════
# Core math
# ═══════════════════════════════════════════════════════════════════════════

class TestWMAandHMA:
    def test_wma_weights(self):
        s = pd.Series([1.0, 2.0, 3.0])
        # WMA(3) at the last bar = (1*1 + 2*2 + 3*3) / 6 = 14/6
        assert _wma(s, 3).iloc[-1] == pytest.approx(14 / 6)

    def test_wma_short_length_passthrough(self):
        s = pd.Series([5.0, 6.0])
        assert _wma(s, 1).iloc[-1] == pytest.approx(6.0)

    def test_hma_tracks_trend(self):
        closes = np.linspace(10, 100, 60)
        df = weekly_frame(closes)
        hl2 = (df["high"] + df["low"]) / 2
        hma = calculate_hma(hl2)
        # On a clean uptrend the HMA is rising at the tail
        assert hma.iloc[-1] > hma.iloc[-2] > hma.iloc[-3]

    def test_hma_nan_warmup(self):
        df = weekly_frame(np.linspace(10, 50, 40))
        hma = calculate_hma((df["high"] + df["low"]) / 2)
        assert hma.iloc[:5].isna().all()          # warm-up region
        assert not np.isnan(hma.iloc[-1])


class TestRSI:
    def test_rsi_extremes(self):
        up = calculate_rsi(pd.Series(np.linspace(10, 100, 50)))
        assert up.iloc[-1] > 90
        down = calculate_rsi(pd.Series(np.linspace(100, 10, 50)))
        assert down.iloc[-1] < 10

    def test_rsi_bounds(self):
        rng = np.random.default_rng(7)
        rsi = calculate_rsi(pd.Series(100 + rng.normal(0, 2, 200)).cumsum().abs() + 1)
        valid = rsi.dropna()
        assert ((valid >= 0) & (valid <= 100)).all()


class TestHMAPivots:
    def test_pivot_low_fires_on_v_bottom(self):
        df = weekly_frame(v_bottom_closes())
        piv = calculate_hma_pivots(df)
        assert piv["hma_pivot_low"].any(), "a clean V-bottom must produce a pivot low"
        assert not piv["hma_pivot_low"].iloc[:HMA_PERIOD].any(), "no pivots inside warm-up"

    def test_pivot_high_fires_on_v_top(self):
        closes = np.concatenate([np.full(30, 60.0), np.linspace(60, 100, 15)[1:],
                                 np.linspace(100, 60, 15)[1:]])
        piv = calculate_hma_pivots(weekly_frame(closes))
        assert piv["hma_pivot_high"].any()

    def test_no_lookahead(self):
        """Pivot flags at bar i must not change when future bars are appended."""
        closes = v_bottom_closes()
        full = calculate_hma_pivots(weekly_frame(closes))
        trunc = calculate_hma_pivots(weekly_frame(closes[:-5]))
        common = trunc.index
        pd.testing.assert_series_equal(
            full.loc[common, "hma_pivot_low"], trunc["hma_pivot_low"]
        )

    def test_slope_rising_on_uptrend_tail(self):
        df = weekly_frame(v_bottom_closes())
        piv = calculate_hma_pivots(df)
        assert piv["hma_slope_rising"].iloc[-1]
        # and every pivot-low bar has a rising slope by construction
        assert piv.loc[piv["hma_pivot_low"], "hma_slope_rising"].all()


class TestMACD:
    def test_columns_and_histogram(self):
        out = calculate_macd(pd.Series(np.linspace(10, 50, 80)))
        for col in ("macd_line", "signal_line", "macd_histogram", "macd_cross_up"):
            assert col in out.columns
        pd.testing.assert_series_equal(
            out["macd_histogram"], out["macd_line"] - out["signal_line"],
            check_names=False,
        )

    def test_single_bar_cross_up(self):
        closes = np.concatenate([np.linspace(100, 60, 30), np.linspace(60, 110, 30)[1:]])
        out = calculate_macd(pd.Series(closes))
        crosses = out["macd_cross_up"]
        assert crosses.any(), "a down-then-up series must produce a MACD cross-up"
        # single-bar semantics: at each cross bar, the prior bar was at/below the signal
        for i in np.flatnonzero(crosses.values):
            assert out["macd_line"].iloc[i] > out["signal_line"].iloc[i]
            if i > 0:
                assert out["macd_line"].iloc[i - 1] <= out["signal_line"].iloc[i - 1]


class TestUndercurrent:
    def test_bounds_and_rising(self):
        df = weekly_frame(v_bottom_closes())
        uc = calculate_undercurrent(df)
        valid = uc["uc"].dropna()
        assert ((valid >= 0) & (valid <= 20)).all()
        expect = (uc["uc"] > uc["uc"].shift(1)).fillna(False)
        pd.testing.assert_series_equal(uc["uc_rising"], expect, check_names=False)

    def test_floor_at_zero_in_downtrend(self):
        df = weekly_frame(np.linspace(100, 40, 50))
        uc = calculate_undercurrent(df)
        assert uc["uc"].iloc[-1] == pytest.approx(0.0)


class TestATRSqueeze:
    def test_rank_bounds_and_squeeze_rule(self):
        rng = np.random.default_rng(3)
        closes = 100 + np.cumsum(rng.normal(0, 1.5, 120))
        out = calculate_atr_squeeze(weekly_frame(np.abs(closes) + 20))
        valid = out["atr_rank"].dropna()
        assert ((valid >= 0) & (valid <= 100)).all()
        flagged = out.dropna(subset=["atr_rank"])
        assert (flagged.loc[flagged["atr_squeeze"], "atr_rank"] < 20).all()


# ═══════════════════════════════════════════════════════════════════════════
# Entry signal — the V10 identity
# ═══════════════════════════════════════════════════════════════════════════

class TestEntrySignal:
    def test_buy_signal_is_bare_pivot_low(self):
        df = weekly_frame(v_bottom_closes())
        s = generate_entry_signal(df)
        pd.testing.assert_series_equal(
            s["buy_signal"], s["hma_pivot_low"], check_names=False
        )
        assert s["buy_signal"].any()

    def test_context_columns_present(self):
        s = generate_entry_signal(weekly_frame(v_bottom_closes()))
        for col in ("close", "hma", "hma_pivot_low", "hma_pivot_high", "hma_slope_rising",
                    "rsi14", "macd_line", "signal_line", "macd_histogram", "macd_cross_up",
                    "uc", "uc_rising", "uc_falling", "atr", "atr_rank", "atr_squeeze",
                    "buy_signal"):
            assert col in s.columns, f"missing context column {col}"

    def test_context_never_gates(self):
        """Every pivot-low bar IS a buy signal, regardless of UC/MACD/ATR state."""
        df = weekly_frame(v_bottom_closes())
        s = generate_entry_signal(df)
        pivot_bars = s[s["hma_pivot_low"]]
        assert (pivot_bars["buy_signal"]).all()


# ═══════════════════════════════════════════════════════════════════════════
# Exit — tiered_initial_35
# ═══════════════════════════════════════════════════════════════════════════

class TestProfitLock:
    def test_inactive_below_50(self):
        r = check_profit_lock(10.0, 14.0, 14.5)   # +40% current
        assert r["triggered"] is False
        assert "none" in r["active_tier"]

    def test_tier_selection_and_levels(self):
        # +60% current → 25% trail from peak
        r = check_profit_lock(10.0, 16.0, 18.0)
        assert r["lock_level"] == pytest.approx(18.0 * 0.75)
        assert r["trail_pct"] == "25%"
        # +120% current → 20% trail
        r = check_profit_lock(10.0, 22.0, 25.0)
        assert r["lock_level"] == pytest.approx(25.0 * 0.80)
        # +250% current → 15% trail
        r = check_profit_lock(10.0, 35.0, 40.0)
        assert r["lock_level"] == pytest.approx(40.0 * 0.85)

    def test_trigger_at_lock_boundary(self):
        # peak 20, +25% trail → lock 15.0; close exactly 15.0 triggers (<=)
        r = check_profit_lock(10.0, 15.0, 20.0)
        assert r["triggered"] is True
        r = check_profit_lock(10.0, 15.01, 20.0)
        assert r["triggered"] is False

    def test_tier_degradation_uses_current_return(self):
        """Peak +150% but current +60% → the +50% tier (25% trail), not +100%."""
        r = check_profit_lock(10.0, 16.0, 25.0)
        assert r["trail_pct"] == "25%"

    def test_invalid_entry(self):
        assert check_profit_lock(0.0, 10.0, 10.0) == {"triggered": False}


class TestTieredInitial35:
    def test_initial_floor_boundary(self):
        # entry 10 → floor 6.50; close at the floor triggers (<=), just above doesn't
        assert check_tiered_initial_35(10.0, 6.50, 12.0)["triggered"] is True
        assert check_tiered_initial_35(10.0, 6.51, 12.0)["triggered"] is False

    def test_floor_level_and_labels(self):
        r = check_tiered_initial_35(10.0, 8.0, 11.0)
        assert r["lock_level"] == pytest.approx(6.5)
        assert r["tier_name"] == "initial"
        assert "35% floor" in r["trail_pct"]

    def test_routing_to_lock_at_plus_50(self):
        # +49% stays on the floor path; +50% routes to the trailing lock
        floor = check_tiered_initial_35(10.0, 14.9, 14.9)
        assert floor["tier_name"] == "initial"
        lock = check_tiered_initial_35(10.0, 15.0, 15.0)
        assert lock.get("tier_name") != "initial"
        assert lock["lock_level"] == pytest.approx(15.0 * 0.75)

    def test_lock_triggers_through_router(self):
        # current +70%, peak 24 → 25% trail → lock 18.0; close 17 → exit
        r = check_tiered_initial_35(10.0, 17.0, 24.0)
        assert r["triggered"] is True
        assert r["lock_level"] == pytest.approx(18.0)

    def test_invalid_entry_exact_shape(self):
        assert check_tiered_initial_35(0.0, 5.0, 5.0) == {"triggered": False}
        assert check_tiered_initial_35(-1.0, 5.0, 5.0) == {"triggered": False}


class TestComputePeakClose:
    def test_inclusive_entry_week(self):
        df = weekly_frame([10, 12, 11, 15, 13], start="2024-01-05")
        # entry mid-week before the 2024-01-12 bar's Friday → that week counts
        peak = compute_peak_close(df, "2024-01-09")
        assert peak == pytest.approx(15.0)
        # entry exactly on a Friday label includes that bar
        assert compute_peak_close(df, "2024-01-05") == pytest.approx(15.0)

    def test_window_excludes_pre_entry_highs(self):
        df = weekly_frame([20, 9, 10, 11], start="2024-01-05")
        peak = compute_peak_close(df, "2024-01-08")  # after the 20-close week
        assert peak == pytest.approx(11.0)

    def test_none_when_no_completed_bar_since_entry(self):
        df = weekly_frame([10, 11], start="2024-01-05")
        assert compute_peak_close(df, "2025-01-01") is None

    def test_none_on_unparseable_date(self):
        df = weekly_frame([10, 11])
        assert compute_peak_close(df, "not-a-date") is None


# ═══════════════════════════════════════════════════════════════════════════
# Weekly resample — partial-bar guard + determinism
# ═══════════════════════════════════════════════════════════════════════════

class TestResamplePartialWeek:
    def _week_of(self, monday, days, base=100.0):
        dates = pd.date_range(monday, periods=days, freq="B")
        return daily_frame(dates, np.linspace(base, base + days, days))

    def test_midweek_asof_drops_partial(self):
        # full week Mon 2024-01-08..Fri 01-12, then partial Mon 01-15..Wed 01-17
        df = pd.concat([self._week_of("2024-01-08", 5), self._week_of("2024-01-15", 3, 110)])
        weekly, dropped = resample_to_weekly(df, asof="2024-01-17")
        assert dropped == "2024-01-19"               # the in-progress week's Friday label
        assert str(weekly.index[-1].date()) == "2024-01-12"

    def test_friday_run_keeps_completed_week(self):
        df = self._week_of("2024-01-08", 5)
        weekly, dropped = resample_to_weekly(df, asof="2024-01-12")
        assert dropped is None
        assert str(weekly.index[-1].date()) == "2024-01-12"

    def test_post_week_reference_keeps_holiday_short_week(self):
        # week ends Thursday (holiday Friday); Saturday run keeps it (reference > label)
        df = self._week_of("2024-01-08", 4)
        weekly, dropped = resample_to_weekly(df, asof="2024-01-20")
        assert dropped is None
        assert str(weekly.index[-1].date()) == "2024-01-12"

    def test_drop_partial_false_keeps_everything(self):
        df = pd.concat([self._week_of("2024-01-08", 5), self._week_of("2024-01-15", 2, 110)])
        weekly, dropped = resample_to_weekly(df, asof="2024-01-16", drop_partial=False)
        assert dropped is None
        assert str(weekly.index[-1].date()) == "2024-01-19"

    def test_asof_truncation_is_deterministic(self):
        df = pd.concat([self._week_of("2024-01-08", 5), self._week_of("2024-01-15", 5, 110)])
        w1, _ = resample_to_weekly(df, asof="2024-01-12")
        w2, _ = resample_to_weekly(df.iloc[:5], asof="2024-01-12")
        pd.testing.assert_frame_equal(w1, w2)

    def test_empty_input(self):
        weekly, dropped = resample_to_weekly(daily_frame([], []), asof="2024-01-12")
        assert weekly.empty and dropped is None


# ═══════════════════════════════════════════════════════════════════════════
# Doctrine constants
# ═══════════════════════════════════════════════════════════════════════════

class TestConfigConstants:
    def test_hma_period(self):
        assert HMA_PERIOD == 21

    def test_rsi_period(self):
        assert RSI_PERIOD == 14

    def test_lock_tiers_exact(self):
        assert LOCK_TIERS == [(2.00, 0.15), (1.00, 0.20), (0.50, 0.25)]

    def test_initial_stop(self):
        assert INITIAL_STOP_PCT == 0.35

    def test_min_weekly_bars(self):
        assert MIN_WEEKLY_BARS == HMA_PERIOD + 10
