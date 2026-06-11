#!/usr/bin/env python3
"""
STERLING GRID INDICATORS — V10
==============================

Pure indicator math + signal/exit primitives. No network calls, no file IO,
no position state. Everything here is deterministic and unit-testable.

V10 DOCTRINE (decided 2026-06-11):
  ENTRY  : bare HMA(21) pivot low on a COMPLETED weekly bar. Fire wide; the
           LLM pipeline does selection. No UC/MACD/ATR gating of eligibility.
  EXIT   : tiered_initial_35 ONLY —
             gain < +50%  → hard floor at entry × (1 − 0.35)
             gain ≥ +50%  → trailing lock from peak close (+50%→25%,
                            +100%→20%, +200%→15%)
           There is NO HMA-down exit, NO ExD, NO RSI conditioning.
  SIZING : none. Every BUY is one full equal-weight position (model-portfolio
           layer's concern, not the scanner's). No tiers, no watchlist,
           no tranches.

REMOVED in V10 (vs V8.1 file): quality tiers T1–T6, tier labels, watchlist
signal, buy_signal_v6 diagnostics, ExD / generate_exit_signal, RSI death-cross
machinery, calculate_position_size, show_portfolio_status, ad-hoc CLI helpers.
UC / MACD / ATR-squeeze are RETAINED as informational context columns for the
LLM layer — they no longer gate or classify anything.

PROVENANCE (unchanged math): _wma/calculate_hma ← indicators.py:29-40 (Pine
ta.wma/ta.hma parity); pivots ← src/indicators.py compute_hma_pivots(); RSI
Wilder ← indicators.py pulse():116-123; MACD single-bar cross ←
v2_signals.py:98-100; UC ← indicators.py undercurrent():152-171 (RSI(10)
derivative, NOT VWAP/Banker); ATR squeeze ← 45-parameter sweep, V7; lock
tiers ← v3_exits.py V3_EXIT_CONFIGS["ExD_lock_tiered"]; −35% initial floor ←
V8 round-trip backtests (tiered ≈ +89% expectancy / 17% hit-3x vs HMA-down
≈ +4% / 0%).
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

# ── Parameters (single source of truth — scanner imports from here) ──────────

HMA_PERIOD = 21           # Hull Moving Average period (weekly HL2)
RSI_PERIOD = 14           # RSI(14) — informational display only
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

UC_TARGET_DAYS = 50       # Undercurrent internal RSI target days
UC_SENSITIVITY = 1.5      # UC = clip(1.5 × (RSI10 − 50), 0, 20)
UC_TIMEFRAME = "weekly"   # divisor 5.0 → RSI length 10

ATR_LEN = 14              # ATR period (weeks)
ATR_LOOKBACK = 52         # percentile-rank window (weeks)
ATR_SQUEEZE_PCTILE = 20   # squeeze active below this rank

# Exit: tiered trailing lock (current-return tiers; trail measured from peak close)
LOCK_TIERS = [
    (2.00, 0.15),   # current return ≥ +200% → 15% trail from peak
    (1.00, 0.20),   # current return ≥ +100% → 20% trail from peak
    (0.50, 0.25),   # current return ≥ +50%  → 25% trail from peak
]
INITIAL_STOP_PCT = 0.35   # −35% hard floor from entry while current return < +50%

MIN_WEEKLY_BARS = HMA_PERIOD + 10   # minimum completed weekly bars to compute signals


# ═══════════════════════════════════════════════════════════════════════════
# WEEKLY RESAMPLE — with as-of truncation and partial-week guard
# ═══════════════════════════════════════════════════════════════════════════

def resample_to_weekly(
    daily_df: pd.DataFrame,
    asof: Optional[pd.Timestamp] = None,
    drop_partial: bool = True,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """Resample daily OHLCV → W-FRI weekly bars, deterministically.

    asof: reference date for the scan. Daily rows after `asof` are dropped
          first, so the same call with the same `asof` is replayable forever.
          If None, the last available daily date is used as the reference
          (conservative: a holiday-shortened final week may then be treated
          as partial — the scanner always passes an explicit asof).

    Partial-week rule: the final weekly bar (labelled with its Friday) is
    PARTIAL iff the reference date is on/before the label Friday AND the last
    daily row is before that Friday. Partial bars are dropped when
    drop_partial=True, so signals are only ever computed on completed weeks.
    A Saturday run after a Good-Friday holiday correctly keeps the week
    (reference > label even though Friday has no row).

    Returns (weekly_df_with_lowercase_columns, dropped_label_or_None).
    """
    df = daily_df
    if asof is not None:
        asof = pd.Timestamp(asof).normalize()
        df = df[df.index.normalize() <= asof]
    if df.empty:
        return df.copy(), None

    weekly = df.resample("W-FRI").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna()
    weekly.columns = [c.lower() for c in weekly.columns]
    if weekly.empty:
        return weekly, None

    dropped = None
    if drop_partial:
        label = weekly.index[-1].normalize()                 # the bar's Friday
        last_daily = df.index.max().normalize()
        reference = asof if asof is not None else last_daily
        if reference <= label and last_daily < label:
            dropped = str(label.date())
            weekly = weekly.iloc[:-1]
    return weekly, dropped


# ═══════════════════════════════════════════════════════════════════════════
# CORE INDICATORS (math unchanged from V8.1 — see provenance header)
# ═══════════════════════════════════════════════════════════════════════════

def _wma(series: pd.Series, length: int) -> pd.Series:
    """Weighted Moving Average — Pine ta.wma parity (weights 1..length)."""
    if length < 1:
        return series.copy()
    weights = np.arange(1, length + 1, dtype=float)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def calculate_hma(series: pd.Series, length: int = HMA_PERIOD) -> pd.Series:
    """Hull MA: WMA(2×WMA(n/2) − WMA(n), √n), applied to weekly HL2."""
    half = max(1, int(length / 2))            # int(21/2) = 10
    sqrt_len = max(1, int(np.sqrt(length)))   # int(√21) = 4
    diff = 2 * _wma(series, half) - _wma(series, length)
    return _wma(diff, sqrt_len)


def calculate_hma_pivots(weekly_df: pd.DataFrame, period: int = HMA_PERIOD) -> pd.DataFrame:
    """3-bar HMA pivot detection on weekly HL2.

    pivot_low[i]  = HMA[i-2] > HMA[i-1] AND HMA[i] > HMA[i-1]   (V-bottom → BUY)
    pivot_high[i] = HMA[i-2] < HMA[i-1] AND HMA[i] < HMA[i-1]   (V-top — INFORMATIONAL
                    ONLY in V10; it is not an exit and not a signal)
    """
    hl2 = (weekly_df["high"] + weekly_df["low"]) / 2
    hma_vals = calculate_hma(hl2, period)

    out = pd.DataFrame(index=weekly_df.index)
    out["hma"] = hma_vals
    p1, p2 = hma_vals.shift(1), hma_vals.shift(2)
    out["hma_pivot_low"] = ((p2 > p1) & (hma_vals > p1)).fillna(False)
    out["hma_pivot_high"] = ((p2 < p1) & (hma_vals < p1)).fillna(False)
    out["hma_slope_rising"] = (hma_vals > p1).fillna(False)
    return out


def calculate_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """RSI with Wilder's smoothing (ewm alpha=1/period). Informational only."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def calculate_macd(series: pd.Series, fast: int = MACD_FAST,
                   slow: int = MACD_SLOW, signal: int = MACD_SIGNAL) -> pd.DataFrame:
    """MACD with SINGLE-BAR cross-up detection (informational context in V10)."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    out = pd.DataFrame(index=series.index)
    out["macd_line"] = macd_line
    out["signal_line"] = signal_line
    out["macd_histogram"] = macd_line - signal_line
    out["macd_cross_up"] = (
        (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    ).fillna(False)
    return out


def calculate_undercurrent(weekly_df: pd.DataFrame, target_days: int = UC_TARGET_DAYS,
                           sensitivity: float = UC_SENSITIVITY,
                           timeframe: str = UC_TIMEFRAME) -> pd.DataFrame:
    """Undercurrent — normalised RSI(10) derivative (NOT VWAP, NOT 'Banker').

    UC = clip(1.5 × (RSI10 − 50), 0, 20). Informational context in V10:
    uc_rising / uc_falling no longer gate or classify anything.
    """
    tf_divisor = {"daily": 1.0, "weekly": 5.0, "monthly": 21.0}.get(timeframe, 5.0)
    length = max(2, int(round(target_days / tf_divisor)))   # 10 for weekly

    delta = weekly_df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rsi_uc = 100 - 100 / (1 + (avg_gain / avg_loss))

    uc = np.clip(sensitivity * (rsi_uc - 50), 0.0, 20.0)
    out = pd.DataFrame(index=weekly_df.index)
    out["uc"] = uc
    out["uc_rsi10"] = rsi_uc
    out["uc_rising"] = (uc > uc.shift(1)).fillna(False)
    out["uc_falling"] = (uc < uc.shift(1)).fillna(False)
    return out


def calculate_atr_squeeze(weekly_df: pd.DataFrame, atr_len: int = ATR_LEN,
                          lookback: int = ATR_LOOKBACK,
                          squeeze_pctile: float = ATR_SQUEEZE_PCTILE) -> pd.DataFrame:
    """ATR percentile rank — volatility-hole detector. Informational in V10.

    Backtest evidence retained for reference (49 tickers, 5y):
    pivot+gates alone 52.7% WR / +21.6% avg; + squeeze 68.4% WR / +52.3% avg.
    """
    high, low, close = weekly_df["high"], weekly_df["low"], weekly_df["close"]
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_len).mean()
    atr_rank = atr.rolling(lookback).rank(pct=True) * 100

    out = pd.DataFrame(index=weekly_df.index)
    out["atr"] = atr
    out["atr_rank"] = atr_rank
    out["atr_squeeze"] = (atr_rank < squeeze_pctile).fillna(False)
    out["atr_fire"] = (out["atr_squeeze"].shift(1).fillna(False) & ~out["atr_squeeze"])
    out["atr_fire_recent"] = (
        out["atr_fire"].astype(float).rolling(3, min_periods=1).max().astype(bool)
    )
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY SIGNAL — V10: bare pivot, informational context, nothing else
# ═══════════════════════════════════════════════════════════════════════════

def generate_entry_signal(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """buy_signal = HMA(21) pivot low on a completed weekly bar. Full stop.

    Every other column is CONTEXT for the LLM selection layer — none of it
    gates eligibility, sets a tier, or feeds a watchlist (all removed in V10).
    """
    hma_data = calculate_hma_pivots(weekly_df)
    macd_data = calculate_macd(weekly_df["close"])
    uc_data = calculate_undercurrent(weekly_df)
    atr_data = calculate_atr_squeeze(weekly_df)

    s = pd.DataFrame(index=weekly_df.index)
    s["close"] = weekly_df["close"]
    s["hma"] = hma_data["hma"]
    s["hma_pivot_low"] = hma_data["hma_pivot_low"]
    s["hma_pivot_high"] = hma_data["hma_pivot_high"]          # informational
    s["hma_slope_rising"] = hma_data["hma_slope_rising"]      # informational
    s["rsi14"] = calculate_rsi(weekly_df["close"])            # informational
    for col in ("macd_line", "signal_line", "macd_histogram", "macd_cross_up"):
        s[col] = macd_data[col]
    for col in ("uc", "uc_rsi10", "uc_rising", "uc_falling"):
        s[col] = uc_data[col]
    for col in ("atr", "atr_rank", "atr_squeeze", "atr_fire_recent"):
        s[col] = atr_data[col]

    s["buy_signal"] = s["hma_pivot_low"]
    return s


# ═══════════════════════════════════════════════════════════════════════════
# EXIT — tiered_initial_35 (the ONLY exit in V10)
# ═══════════════════════════════════════════════════════════════════════════

def check_profit_lock(entry_price: float, current_close: float, peak_close: float) -> dict:
    """Tiered trailing lock. Tier set by CURRENT return (tiers can degrade);
    trail measured from PEAK close. Inactive below +50% current return."""
    if entry_price <= 0:
        return {"triggered": False}

    current_return = (current_close - entry_price) / entry_price
    peak_return = (peak_close - entry_price) / entry_price

    active_tier = None
    for threshold, trail_pct in LOCK_TIERS:
        if current_return >= threshold:
            active_tier = (threshold, trail_pct)
            break

    if active_tier is None:
        return {
            "triggered": False,
            "gain_pct": round(current_return * 100, 1),
            "peak_gain_pct": round(peak_return * 100, 1),
            "active_tier": f"none (current +{current_return*100:.0f}% < +50%)",
        }

    threshold, trail_pct = active_tier
    lock_level = peak_close * (1 - trail_pct)
    return {
        "triggered": current_close <= lock_level,
        "tier_name": f"+{int(threshold * 100)}%",
        "trail_pct": f"{int(trail_pct * 100)}%",
        "lock_level": round(lock_level, 2),
        "peak_close": round(peak_close, 2),
        "gain_pct": round(current_return * 100, 1),
        "peak_gain_pct": round(peak_return * 100, 1),
        "active_tier": f"current +{current_return*100:.0f}% → {int(trail_pct*100)}% trail from ${peak_close:.2f}",
    }


def check_tiered_initial_35(entry_price: float, current_close: float, peak_close: float) -> dict:
    """V10 exit. Decided on the WEEKLY CLOSE; act at next candle open.

      current return < +50%  → hard floor at entry × (1 − 0.35)
      current return ≥ +50%  → tiered trailing lock (check_profit_lock)

    No HMA-down, no ExD, no RSI conditioning — removed by doctrine (the
    pivot-high exit pre-empted the lock and clipped the multibaggers it
    exists to capture)."""
    if entry_price <= 0:
        return {"triggered": False}

    current_return = (current_close - entry_price) / entry_price
    if current_return >= 0.50:
        return check_profit_lock(entry_price, current_close, peak_close)

    stop_level = entry_price * (1 - INITIAL_STOP_PCT)
    return {
        "triggered": current_close <= stop_level,
        "tier_name": "initial",
        "trail_pct": f"{int(INITIAL_STOP_PCT * 100)}% floor",
        "lock_level": round(stop_level, 2),
        "peak_close": round(peak_close, 2),
        "gain_pct": round(current_return * 100, 1),
        "peak_gain_pct": round((peak_close - entry_price) / entry_price * 100, 1),
        "active_tier": f"-{int(INITIAL_STOP_PCT * 100)}% initial floor (pre-+50%, stop ${stop_level:.2f})",
    }


def compute_peak_close(weekly_df: pd.DataFrame, entry_date) -> Optional[float]:
    """Highest COMPLETED weekly close on/after entry_date. Deterministic and
    replayable — peak is derived from price history, never carried as mutable
    state. Returns None if no completed weekly bar exists since entry yet."""
    try:
        ts = pd.Timestamp(entry_date).normalize()
    except Exception:
        return None
    closes = weekly_df.loc[weekly_df.index >= ts, "close"]
    if closes.empty:
        return None
    return float(closes.max())
