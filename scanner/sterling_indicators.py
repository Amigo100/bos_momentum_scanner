#!/usr/bin/env python3
"""
Sterling Grid V7 — Weekly Indicator Calculator (EXACT BACKTEST MATCH)
======================================================================
Every calculation verified line-by-line against the actual backtest source:
  - src/indicators.py    (HMA, RSI, MACD, Undercurrent)
  - src/v2_signals.py    (entry signal generation + corridor alternation)
  - src/v3_exits.py      (ExD exit + tiered profit lock)
  - v6/run_phase_b_tiered_sizing.py  (V6 pivot entry, OR-gated, quality tiers)

V7 CHANGES vs V6:
  1. Entry: Added ATR Percentile Rank filter (squeeze must be active)
     ATR(14) percentile rank over 52 weeks < 20th percentile = volatility hole
  2. All other entry/exit logic unchanged from V6

V6 CHANGES vs V4:
  1. Entry: HMA slope rising → HMA PIVOT LOW (V-bottom: HMA[i-2] > HMA[i-1] < HMA[i])
  2. RSI(14) > 50 gate REMOVED (computed but not filtered on)
  3. UC condition: uc_rising_above (UC > prev AND UC > 0) → uc_rising (UC > prev only)
  4. Gate logic: HMA_pivot_low AND (UC_rising OR MACD_cross_up)
  5. Exit: HMA slope falling → HMA PIVOT HIGH (V-top: HMA[i-2] < HMA[i-1] > HMA[i])
  6. Quality Tiers: T1 (both gates), T2 (MACD only), T3 (UC only)
  7. Position Sizing: T1=20%, T2=10%, T3=5% of equity, max 8 concurrent

Position Sizing: Quality-Tier Based (Tiered 20/10/5, max 8)
  - T1 (UC rising + MACD cross-up) → 20% of equity  (highest conviction)
  - T2 (MACD cross-up only)        → 10% of equity  (timing confirmed)
  - T3 (UC rising only)            → 5% of equity   (regime confirmed)
  - Maximum 8 concurrent positions
  - Adaptive gear-shift: conservative (12/8/3) / recommended (20/10/5) / aggressive (25/15/8)

Usage:
    python sterling_indicators.py TICKER [TICKER2 ...]
    python sterling_indicators.py MARA RKLB IONQ

Position check (with entry price):
    python sterling_indicators.py --check MARA:5.50 RKLB:12.00

Position check (with entry price and known peak):
    python sterling_indicators.py --check MARA:5.50:28.50

Portfolio status (equity + positions as ticker:entry:tier):
    python sterling_indicators.py --portfolio 120000 MARA:5.50:1 RKLB:12.00:2

Position size calculator:
    python sterling_indicators.py --size 120000 T1

Sizing gear override:
    python sterling_indicators.py --size 200000 T3 --gear aggressive

Dump full indicator history to CSV:
    python sterling_indicators.py --history MARA
"""

import sys
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Exact match to backtest parameters
# ═══════════════════════════════════════════════════════════════

HMA_PERIOD = 21           # Hull Moving Average period (on weekly HL2)
RSI_PERIOD = 14           # RSI(14) — computed but NOT an entry gate in V6
MACD_FAST = 12            # MACD fast EMA
MACD_SLOW = 26            # MACD slow EMA
MACD_SIGNAL = 9           # MACD signal EMA
# PRICE_CAP removed — no longer filtering by price

# Undercurrent parameters (from indicators.py undercurrent() defaults)
UC_TARGET_DAYS = 50       # Target days for internal RSI calculation
UC_SENSITIVITY = 1.5      # Scaling factor applied to (RSI - 50)
UC_TIMEFRAME = "weekly"   # Divisor = 5.0 → RSI length = round(50/5) = 10

# Profit lock thresholds (from v3_exits.py V3_EXIT_CONFIGS["ExD_lock_tiered"])
# CRITICAL: Tier determined by CURRENT return, not peak. Tiers can degrade.
LOCK_TIERS = [
    (2.00, 0.15),   # current_return >= +200% → 15% trail from peak
    (1.00, 0.20),   # current_return >= +100% → 20% trail from peak
    (0.50, 0.25),   # current_return >= +50%  → 25% trail from peak
]

# V8 exit (tiered_initial_35): a WIDE fixed initial floor active until +50% gain.
# Below +50% there is now a hard stop at -35% from entry (was: no stop pre-+50%, ExD only).
# At/above +50% the LOCK_TIERS trailing lock takes over. ExD is DROPPED as an exit trigger.
# Validated over 12 backtests (crash-inclusive, next-open fills): tiered_initial_35 delivered
# ~2.8x the live exit's risk-adjusted return (Sortino 5.06 vs 1.81).
INITIAL_STOP_PCT = 0.35   # -35% hard floor from entry, applied while current return < +50%

# ═══════════════════════════════════════════════════════════════
# POSITION SIZING — Quality-Tier Based (V7: 6-tier, ATR squeeze split)
# ═══════════════════════════════════════════════════════════════

MAX_CONCURRENT_POSITIONS = 8
MIN_TRADE_SIZE = 500.0

# Quality tier definitions: {tier_int: {pct, label, description}}
# T1-T3: V6 pivot + gate + ATR squeeze (volatility hole — highest edge)
# T4-T6: V6 pivot + gate, NO ATR squeeze (standard momentum — halved sizing)
QUALITY_TIERS = {
    1: {'equity_pct': 0.20,  'label': 'T1', 'description': 'Both gates + ATR squeeze',
        'backtest_wr': '80%', 'backtest_avg': '+65.6%'},
    2: {'equity_pct': 0.10,  'label': 'T2', 'description': 'MACD cross-up + ATR squeeze',
        'backtest_wr': '67%', 'backtest_avg': '+32.3%'},
    3: {'equity_pct': 0.05,  'label': 'T3', 'description': 'UC rising + ATR squeeze',
        'backtest_wr': '63%', 'backtest_avg': '+56.0%'},
    4: {'equity_pct': 0.10,  'label': 'T4', 'description': 'Both gates (no ATR squeeze)',
        'backtest_wr': '57%', 'backtest_avg': '+91.0%'},
    5: {'equity_pct': 0.05,  'label': 'T5', 'description': 'MACD cross-up only (no ATR squeeze)',
        'backtest_wr': '83%', 'backtest_avg': '+63.2%'},
    6: {'equity_pct': 0.025, 'label': 'T6', 'description': 'UC rising only (no ATR squeeze)',
        'backtest_wr': '69%', 'backtest_avg': '+75.8%'},
}

# Gear-shift configurations (scale all tier allocations proportionally)
SIZING_GEARS = {
    'conservative': {'max_positions': 10, 'label': 'Conservative',
                     'tiers': {1: 0.12, 2: 0.08, 3: 0.03, 4: 0.06, 5: 0.04, 6: 0.015}},
    'recommended':  {'max_positions': 8,  'label': 'Recommended',
                     'tiers': {1: 0.20, 2: 0.10, 3: 0.05, 4: 0.10, 5: 0.05, 6: 0.025}},
    'aggressive':   {'max_positions': 8,  'label': 'Aggressive',
                     'tiers': {1: 0.25, 2: 0.15, 3: 0.08, 4: 0.125, 5: 0.075, 6: 0.04}},
}


# ═══════════════════════════════════════════════════════════════
# INDICATOR FUNCTIONS (matching src/indicators.py line-by-line)
# ═══════════════════════════════════════════════════════════════

def resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily OHLCV to weekly (Friday close).
    Matches the backtest's v2_cache.py weekly resampling.
    Returns lowercase column names to match backtest convention.
    """
    weekly = daily_df.resample('W-FRI').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    weekly.columns = [c.lower() for c in weekly.columns]
    return weekly


def _wma(series: pd.Series, length: int) -> pd.Series:
    """
    Weighted Moving Average.
    Source: indicators.py line 29-33
    Matches Pine ta.wma — weights are [1, 2, ..., length].
    """
    if length < 1:
        return series.copy()
    weights = np.arange(1, length + 1, dtype=float)
    return series.rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def calculate_hma(series: pd.Series, length: int = HMA_PERIOD) -> pd.Series:
    """
    Hull Moving Average.
    Source: indicators.py line 36-40 (hma function)
    
    HMA = WMA( 2 × WMA(n/2) − WMA(n), √n )
    Applied to HL2 = (high + low) / 2 on weekly data.
    """
    half = max(1, int(length / 2))         # int(21/2) = 10
    sqrt_len = max(1, int(np.sqrt(length)))  # int(√21) = 4
    diff = 2 * _wma(series, half) - _wma(series, length)
    return _wma(diff, sqrt_len)


def calculate_hma_pivots(weekly_df: pd.DataFrame,
                         period: int = HMA_PERIOD) -> pd.DataFrame:
    """
    HMA pivot detection — V6 entry/exit signal basis.
    Source: src/indicators.py compute_hma_pivots()
    Source: v6/run_phase_b_tiered_sizing.py generate_tiered_signals()
    
    REPLACES calculate_hma_slope() for entry/exit signal generation.
    
    pivot_low[i]  = (HMA[i-2] > HMA[i-1]) AND (HMA[i] > HMA[i-1])
                    → V-bottom: HMA dipped then recovered (BUY trigger)
    
    pivot_high[i] = (HMA[i-2] < HMA[i-1]) AND (HMA[i] < HMA[i-1])
                    → V-top: HMA peaked then declined (SELL trigger)
    
    Edge cases:
      - First 2 bars: always False (insufficient lookback)
      - NaN values: treated as False
    """
    hl2 = (weekly_df['high'] + weekly_df['low']) / 2
    hma_vals = calculate_hma(hl2, period)

    result = pd.DataFrame(index=weekly_df.index)
    result['hma'] = hma_vals

    # 3-bar pivot detection
    hma_prev1 = hma_vals.shift(1)   # HMA[i-1]
    hma_prev2 = hma_vals.shift(2)   # HMA[i-2]

    # Pivot low: V-bottom (dipped then recovered)
    result['hma_pivot_low'] = (
        (hma_prev2 > hma_prev1) &  # was falling
        (hma_vals > hma_prev1)      # now rising
    ).fillna(False)

    # Pivot high: V-top (peaked then declined)
    result['hma_pivot_high'] = (
        (hma_prev2 < hma_prev1) &  # was rising
        (hma_vals < hma_prev1)      # now falling
    ).fillna(False)

    # Also compute slope for informational/display purposes
    result['hma_slope_rising'] = (hma_vals > hma_vals.shift(1)).fillna(False)
    result['hma_slope_falling'] = (hma_vals < hma_vals.shift(1)).fillna(False)

    return result


def calculate_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """
    RSI with Wilder's smoothing.
    Source: indicators.py pulse() lines 116-123
    
    Uses ewm(alpha=1/period, adjust=False) which is Wilder's smoothing.
    
    NOTE (V6): RSI(14) is computed for display/reference but is NOT an entry gate.
    The V6 system removed the RSI > 50 requirement.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def calculate_macd(series: pd.Series,
                   fast: int = MACD_FAST,
                   slow: int = MACD_SLOW,
                   signal: int = MACD_SIGNAL) -> pd.DataFrame:
    """
    MACD with single-bar cross-up detection.
    Source: indicators.py tide() lines 134-141
    Cross-up: v2_signals.py _build_macd_mask("macd_cross_up") lines 98-100
    
    CRITICAL: macd_cross_up is a SINGLE BAR event.
    It fires when: macd > signal AND macd.shift(1) <= signal.shift(1)
    There is NO multi-bar lookback. The signal must fire on the exact
    same bar as all other entry conditions.
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    result = pd.DataFrame(index=series.index)
    result['macd_line'] = macd_line
    result['signal_line'] = signal_line
    result['histogram'] = histogram

    # Single-bar crossover — exact match to v2_signals.py line 99
    result['macd_cross_up'] = (
        (macd_line > signal_line) &
        (macd_line.shift(1) <= signal_line.shift(1))
    ).fillna(False)

    # Also compute hist_pos for reference
    result['macd_hist_pos'] = (histogram > 0).fillna(False)

    return result


def calculate_undercurrent(weekly_df: pd.DataFrame,
                           target_days: int = UC_TARGET_DAYS,
                           sensitivity: float = UC_SENSITIVITY,
                           timeframe: str = UC_TIMEFRAME) -> pd.DataFrame:
    """
    Undercurrent (UC) — normalised RSI derivative.
    Source: indicators.py undercurrent() lines 152-171
    
    THIS IS NOT A VWAP INDICATOR. The exact formula is:
    
        tf_divisor = 5.0  (for weekly)
        length = round(50 / 5.0) = 10
        rsi_10 = RSI(close, 10)  using Wilder's smoothing
        UC = clip(1.5 × (rsi_10 − 50), 0, 20)
    
    UC behaviour:
        RSI(10) <= 50.0  →  UC = 0.0   (bearish/neutral, clipped at floor)
        RSI(10) =  55.0  →  UC = 7.5   (mild bullish)
        RSI(10) =  60.0  →  UC = 15.0  (strong bullish)
        RSI(10) >= 63.3  →  UC = 20.0  (capped at ceiling)
    
    V6 UC entry condition "uc_rising" (v2_signals.py _build_uc_mask):
        UC > UC.shift(1)   — momentum accelerating (no >0 requirement)
    
    V6 UC exit condition "uc_falling" (v3_exits.py ExD):
        UC < UC.shift(1)   — momentum decelerating
    
    V4 DIFFERENCE: V4 used "uc_rising_above" = UC > UC.shift(1) AND UC > 0.
    V6 drops the UC > 0 requirement (uc_rising only needs UC > prev).
    
    NOTE: This is DIFFERENT from the production scanner's "Banker" indicator,
    which uses a VWAP deviation formula. Banker and UC are conceptually related
    but mathematically different. The scanner uses this RSI-derived UC.
    """
    tf_divisor = {"daily": 1.0, "weekly": 5.0, "monthly": 21.0}.get(timeframe, 5.0)
    length = max(2, int(round(target_days / tf_divisor)))  # = 10 for weekly

    # RSI(10) with Wilder's smoothing — separate from the RSI(14) display value
    delta = weekly_df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_uc = 100 - 100 / (1 + rs)

    # Normalise and clip — exact match to indicators.py line 167
    uc = np.clip(sensitivity * (rsi_uc - 50), 0.0, 20.0)

    result = pd.DataFrame(index=weekly_df.index)
    result['uc'] = uc
    result['uc_rsi10'] = rsi_uc  # The underlying RSI(10) for debugging
    result['uc_prev'] = uc.shift(1)

    # V6 entry condition: uc_rising — no >0 requirement
    result['uc_rising'] = (uc > uc.shift(1)).fillna(False)
    result['uc_falling'] = (uc < uc.shift(1)).fillna(False)
    result['uc_above_zero'] = (uc > 0).fillna(False)

    # V4 legacy condition (kept for reference/comparison)
    result['uc_rising_above'] = (
        (uc > uc.shift(1)) & (uc > 0)
    ).fillna(False)

    return result


# ═══════════════════════════════════════════════════════════════
# ATR PERCENTILE RANK — Volatility Hole Entry Filter (V7)
# ═══════════════════════════════════════════════════════════════

# ATR squeeze parameters (validated via 45-parameter sweep)
ATR_LEN = 14              # ATR period (weeks)
ATR_LOOKBACK = 52         # Rolling window for percentile rank (weeks = 1 year)
ATR_SQUEEZE_PCTILE = 20   # Percentile threshold — squeeze active below this


def calculate_atr_squeeze(weekly_df: pd.DataFrame,
                          atr_len: int = ATR_LEN,
                          lookback: int = ATR_LOOKBACK,
                          squeeze_pctile: float = ATR_SQUEEZE_PCTILE) -> pd.DataFrame:
    """
    ATR Percentile Rank — volatility hole detector (V7 entry filter).

    Measures current candle size (ATR) relative to its own history.
    Squeeze active when ATR rank drops below the Nth percentile.

    When ATR is in the bottom 20th percentile of its 52-week range,
    candles are abnormally small — statistically, a big move follows.
    The V6 buy signal provides the direction; the ATR squeeze provides the energy.

    Backtest evidence (49 tickers, 5 years):
        T1-T3 alone:        52.7% WR, +21.6% avg, 2.50x PF, 0.256 Sharpe
        T1-T3 + ATR squeeze: 68.4% WR, +52.3% avg, 5.88x PF, 0.483 Sharpe

    Parameters:
        weekly_df: pd.DataFrame — weekly OHLC data with columns: high, low, close
        atr_len: int — ATR period (default 14 weeks)
        lookback: int — rolling window for percentile rank (default 52 weeks)
        squeeze_pctile: float — threshold below which squeeze is active (default 20)

    Returns:
        pd.DataFrame with columns:
            atr            — ATR(14) value
            atr_rank       — percentile rank (0-100)
            atr_squeeze    — True when atr_rank < squeeze_pctile (volatility hole)
            atr_fire       — True on the bar squeeze ends (expansion begins)
            atr_fire_recent — True within 2 bars of a fire event
    """
    high = weekly_df['high']
    low = weekly_df['low']
    close = weekly_df['close']

    # True Range: max of (high-low, |high-prev_close|, |low-prev_close|)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    # Average True Range
    atr = tr.rolling(atr_len).mean()

    # Percentile rank over lookback window (0-100 scale)
    atr_rank = atr.rolling(lookback).rank(pct=True) * 100

    # Build output
    result = pd.DataFrame(index=weekly_df.index)
    result['atr'] = atr
    result['atr_rank'] = atr_rank
    result['atr_squeeze'] = (atr_rank < squeeze_pctile).fillna(False)

    # Fire: squeeze was active last bar, now it's not (expansion begins)
    result['atr_fire'] = (
        result['atr_squeeze'].shift(1).fillna(False) & ~result['atr_squeeze']
    )

    # Fire within 2 bars (current bar + 2 prior)
    result['atr_fire_recent'] = (
        result['atr_fire'].astype(float)
        .rolling(3, min_periods=1).max()
        .astype(bool)
    )

    return result


# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION — V7 (V6 pivot entry + ATR squeeze filter)
# ═══════════════════════════════════════════════════════════════

def generate_entry_signal(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sterling Grid V7 entry signal.
    Source: v6/run_phase_b_tiered_sizing.py generate_tiered_signals()
    V7 addition: ATR Percentile Rank squeeze splits tiers (T1-T3 vs T4-T6).
    
    BUY fires when ALL of these are true on the SAME weekly bar:
        1. HMA(21) pivot low — V-bottom: HMA[i-2] > HMA[i-1] < HMA[i]
        2. At least ONE confirmation gate:
           a. UC rising — UC > UC.shift(1)  (OR)
           b. MACD cross up — single-bar crossover event

    QUALITY TIER CLASSIFICATION (V7: 6-tier, ATR squeeze split):
        T1: UC rising AND MACD cross-up + ATR squeeze  (20% — highest conviction)
        T2: MACD cross-up only + ATR squeeze            (10% — timing + squeeze)
        T3: UC rising only + ATR squeeze                (5%  — regime + squeeze)
        T4: UC rising AND MACD cross-up, NO squeeze     (10% — halved T1)
        T5: MACD cross-up only, NO squeeze              (5%  — halved T2)
        T6: UC rising only, NO squeeze                  (2.5% — halved T3)
    """
    hma_data = calculate_hma_pivots(weekly_df)
    rsi = calculate_rsi(weekly_df['close'])       # Computed for display, NOT a gate
    macd_data = calculate_macd(weekly_df['close'])
    uc_data = calculate_undercurrent(weekly_df)
    atr_data = calculate_atr_squeeze(weekly_df)   # V7: volatility hole filter

    signals = pd.DataFrame(index=weekly_df.index)
    signals['close'] = weekly_df['close']

    # HMA pivot (V6 entry trigger)
    signals['hma'] = hma_data['hma']
    signals['hma_pivot_low'] = hma_data['hma_pivot_low']
    signals['hma_pivot_high'] = hma_data['hma_pivot_high']
    signals['hma_slope_rising'] = hma_data['hma_slope_rising']     # informational

    # RSI (V6: computed but NOT a gate)
    signals['rsi14'] = rsi
    signals['rsi_above_50'] = (rsi > 50).fillna(False)             # informational only

    # MACD (confirmation gate)
    signals['macd_line'] = macd_data['macd_line']
    signals['signal_line'] = macd_data['signal_line']
    signals['macd_histogram'] = macd_data['histogram']
    signals['macd_cross_up'] = macd_data['macd_cross_up']
    signals['macd_hist_positive'] = macd_data['macd_hist_pos']

    # UC (confirmation gate — V6 uses uc_rising, not uc_rising_above)
    signals['uc'] = uc_data['uc']
    signals['uc_rsi10'] = uc_data['uc_rsi10']
    signals['uc_rising'] = uc_data['uc_rising']
    signals['uc_falling'] = uc_data['uc_falling']
    signals['uc_rising_above'] = uc_data['uc_rising_above']        # V4 legacy, informational

    # ATR squeeze (V7 entry filter)
    signals['atr'] = atr_data['atr']
    signals['atr_rank'] = atr_data['atr_rank']
    signals['atr_squeeze'] = atr_data['atr_squeeze']
    signals['atr_fire'] = atr_data['atr_fire']
    signals['atr_fire_recent'] = atr_data['atr_fire_recent']

    # ── V8 buy signal = BARE HMA pivot low (fire wide; gates are sizing nudges only) ─
    # Backtesting (12 tests, crash-inclusive, next-open fills) showed UC/MACD/ATR *gates*
    # cut winner-leg recall ~40% for zero selection gain. V8 takes EVERY confirmed weekly
    # HMA pivot-up; the LLM does selection, and the gates / ATR squeeze now only inform the
    # quality tier (sizing), not eligibility. buy_signal_v6 is retained for diagnostics.
    signals['buy_signal_v6'] = (
        signals['hma_pivot_low'] &
        (signals['uc_rising'] | signals['macd_cross_up'])
    )
    signals['buy_signal_v8'] = signals['hma_pivot_low']
    signals['buy_signal'] = signals['buy_signal_v8']

    # ── Quality tier classification (V7: 6-tier) ───────────────
    # T1-T3: pivot + gate + ATR squeeze (volatility hole entry)
    # T4-T6: pivot + gate, NO ATR squeeze (standard momentum)
    signals['quality_tier'] = 0  # 0 = no signal

    # T1: both gates + ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['uc_rising'] & signals['macd_cross_up'] & signals['atr_squeeze'],
        'quality_tier'
    ] = 1
    # T2: MACD only + ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['macd_cross_up'] & ~signals['uc_rising'] & signals['atr_squeeze'],
        'quality_tier'
    ] = 2
    # T3: UC only + ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['uc_rising'] & ~signals['macd_cross_up'] & signals['atr_squeeze'],
        'quality_tier'
    ] = 3
    # T4: both gates, no ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['uc_rising'] & signals['macd_cross_up'] & ~signals['atr_squeeze'],
        'quality_tier'
    ] = 4
    # T5: MACD only, no ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['macd_cross_up'] & ~signals['uc_rising'] & ~signals['atr_squeeze'],
        'quality_tier'
    ] = 5
    # T6: UC only, no ATR squeeze
    signals.loc[
        signals['buy_signal_v6'] & signals['uc_rising'] & ~signals['macd_cross_up'] & ~signals['atr_squeeze'],
        'quality_tier'
    ] = 6

    # V8: a bare HMA pivot with NO UC/MACD gate is still a valid buy — classify it T6
    # (lowest sizing nudge). Gated pivots keep their richer T1–T5 classification above.
    signals.loc[signals['buy_signal'] & (signals['quality_tier'] == 0), 'quality_tier'] = 6

    # ── Tier label for display ──────────────────────────────────
    tier_labels = {0: '', 1: 'T1', 2: 'T2', 3: 'T3', 4: 'T4', 5: 'T5', 6: 'T6'}
    signals['tier_label'] = signals['quality_tier'].map(tier_labels)

    # ── Watchlist: HMA rising + at least one gate, but no buy signal ─
    # These are stocks in a bullish trend where a pivot hasn't fired yet
    signals['watchlist_signal'] = (
        signals['hma_slope_rising'] &
        (signals['uc_rising'] | signals['macd_hist_positive']) &
        ~signals['buy_signal']
    )

    return signals


def generate_exit_signal(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    V6 ExD exit signal.
    Source: v3_exits.py run_compound_exit() + V6 spec Section 7.1
    
    ExD fires when BOTH are true on the same weekly bar:
        1. HMA(21) PIVOT HIGH — V-top: HMA[i-2] < HMA[i-1] > HMA[i]
        2. UC falling — UC < UC.shift(1)
    
    V4→V6 CHANGE:
        - V4 used HMA slope falling (HMA < HMA.shift(1))
        - V6 uses HMA pivot high (3-bar V-top detection)
        This is a less sensitive exit trigger — requires a confirmed peak
        rather than just any downward tick.
    """
    hma_data = calculate_hma_pivots(weekly_df)
    uc_data = calculate_undercurrent(weekly_df)

    # RSI(14) + its SMA(14) signal line — matches the TradingView "RSI" indicator exactly
    # (Wilder RSI via calculate_rsi == ta.rma; signal == SMA(14) of RSI). Used to CONDITION the
    # legacy HMA-down exit: see rsi_death_cross_recent below.
    rsi = calculate_rsi(weekly_df['close'])
    rsi_ma = rsi.rolling(RSI_PERIOD, min_periods=1).mean()
    below = rsi < rsi_ma
    death_cross = below & ~below.shift(1, fill_value=False)   # RSI crosses below its signal line
    # Recent + PERSISTENT death cross: crossed on the prior bar and is still below, OR crossed two
    # bars back and has stayed below since. (Mirrors rsi_confluence_test.py's definition exactly —
    # the conditioning that ~halved bare HMA-down's premature sells in backtesting.)
    rsi_death_cross_recent = (
        (death_cross.shift(1, fill_value=False) & below) |
        (death_cross.shift(2, fill_value=False) & below.shift(1, fill_value=False) & below)
    ).fillna(False)

    signals = pd.DataFrame(index=weekly_df.index)
    signals['close'] = weekly_df['close']
    signals['hma'] = hma_data['hma']
    signals['hma_pivot_high'] = hma_data['hma_pivot_high']
    signals['hma_slope_falling'] = hma_data['hma_slope_falling']   # informational
    signals['uc'] = uc_data['uc']
    signals['uc_falling'] = uc_data['uc_falling']
    signals['rsi14'] = rsi                                          # informational / display
    signals['rsi_ma'] = rsi_ma                                      # SMA(14) signal line
    signals['rsi_death_cross'] = death_cross.fillna(False)          # single-bar cross event
    signals['rsi_death_cross_recent'] = rsi_death_cross_recent      # legacy-exit condition

    # V6 ExD = HMA pivot high AND UC falling (same bar)
    signals['exd_signal'] = (
        signals['hma_pivot_high'] &
        signals['uc_falling']
    )

    return signals


def check_profit_lock(entry_price: float,
                      current_close: float,
                      peak_close: float) -> dict:
    """
    Tiered profit lock.
    Source: v3_exits.py _check_protection() lines 76-89 (profit_lock_tiered)
    
    CRITICAL: Tier is determined by CURRENT return, NOT peak return.
    
    From v3_exits.py:
        current_return = (bar_close - entry_price) / entry_price
        if current_return >= 2.0:
            lock_level = peak_close * (1 - 0.15)
        elif current_return >= 1.0:
            lock_level = peak_close * (1 - 0.20)
        elif current_return >= 0.5:
            lock_level = peak_close * (1 - 0.25)
        else:
            return False  # no lock active
        if bar_close <= lock_level:
            → EXIT
    
    This means tiers can DEGRADE. If a stock peaks at +250% (15% trail)
    then pulls back to +180% current return, the tier loosens to 20% trail.
    If it pulls further to +90%, it loosens again to 25% trail. If it drops
    below +50% current return, the lock deactivates entirely.
    
    UNCHANGED from V4 — profit lock logic is identical in V6.
    """
    if entry_price <= 0:
        return {'triggered': False}

    current_return = (current_close - entry_price) / entry_price
    peak_return = (peak_close - entry_price) / entry_price

    # Find active tier based on CURRENT return
    active_tier = None
    for threshold, trail_pct in LOCK_TIERS:
        if current_return >= threshold:
            active_tier = (threshold, trail_pct)
            break  # Tightest applicable tier

    if active_tier is None:
        return {
            'triggered': False,
            'gain_pct': round(current_return * 100, 1),
            'peak_gain_pct': round(peak_return * 100, 1),
            'active_tier': f'none (current +{current_return*100:.0f}% < +50%)',
        }

    threshold, trail_pct = active_tier
    lock_level = peak_close * (1 - trail_pct)
    triggered = current_close <= lock_level

    return {
        'triggered': triggered,
        'tier_name': f"+{int(threshold * 100)}%",
        'trail_pct': f"{int(trail_pct * 100)}%",
        'lock_level': round(lock_level, 2),
        'peak_close': round(peak_close, 2),
        'gain_pct': round(current_return * 100, 1),
        'peak_gain_pct': round(peak_return * 100, 1),
        'active_tier': f"current +{current_return*100:.0f}% → {int(trail_pct*100)}% trail from ${peak_close:.2f}",
    }


def check_tiered_initial_35(entry_price: float,
                            current_close: float,
                            peak_close: float) -> dict:
    """
    V8 exit — tiered_initial_35 (the live exit going forward).

    Two regimes, decided on the WEEKLY CLOSE (act at next candle open):
      • current return < +50%  → HARD STOP at entry * (1 - 0.35)  [wide -35% initial floor]
      • current return >= +50% → hand off to the tiered trailing lock (check_profit_lock)

    ExD (HMA pivot high + UC falling) is NOT used — it clipped winners on the first pullback
    on every universe tested. This function replaces the old "ExD OR profit-lock" live exit.

    Returns the same dict shape as check_profit_lock (triggered / lock_level / active_tier / …)
    so existing callers and printouts keep working unchanged.
    """
    if entry_price <= 0:
        return {'triggered': False}

    current_return = (current_close - entry_price) / entry_price

    # At/above +50% → the trailing profit lock owns the exit (initial floor switches off)
    if current_return >= 0.50:
        return check_profit_lock(entry_price, current_close, peak_close)

    # Below +50% → wide -35% initial floor from entry
    stop_level = entry_price * (1 - INITIAL_STOP_PCT)
    triggered = current_close <= stop_level
    return {
        'triggered': triggered,
        'tier_name': 'initial',
        'trail_pct': f"{int(INITIAL_STOP_PCT * 100)}% floor",
        'lock_level': round(stop_level, 2),
        'peak_close': round(peak_close, 2),
        'gain_pct': round(current_return * 100, 1),
        'peak_gain_pct': round((peak_close - entry_price) / entry_price * 100, 1),
        'active_tier': f"-{int(INITIAL_STOP_PCT * 100)}% initial floor (pre-+50%, stop ${stop_level:.2f})",
    }


# ═══════════════════════════════════════════════════════════════
# SCANNER — Check any ticker for current signals
# ═══════════════════════════════════════════════════════════════

def scan_ticker(ticker: str, verbose: bool = True) -> dict:
    """Scan a single ticker for Sterling Grid V6 entry/exit signals."""
    df = yf.download(ticker, period="2y", progress=False)

    if df.empty or len(df) < 100:
        if verbose:
            print(f"  Warning: {ticker} — insufficient data")
        return {'ticker': ticker, 'error': 'Insufficient data'}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    weekly = resample_to_weekly(df)

    if len(weekly) < HMA_PERIOD + 10:
        return {'ticker': ticker, 'error': 'Insufficient weekly bars'}

    entry_signals = generate_entry_signal(weekly)
    exit_signals = generate_exit_signal(weekly)

    cur = entry_signals.iloc[-1]
    cur_exit = exit_signals.iloc[-1]

    quality_tier = int(cur['quality_tier']) if pd.notna(cur['quality_tier']) else 0
    tier_label = cur['tier_label'] if quality_tier > 0 else ''

    result = {
        'ticker': ticker,
        'date': str(weekly.index[-1].date()),
        'close': round(float(cur['close']), 2),
        'hma': round(float(cur['hma']), 4) if pd.notna(cur['hma']) else None,
        # V6 pivot signals
        'hma_pivot_low': bool(cur['hma_pivot_low']),
        'hma_pivot_high': bool(cur['hma_pivot_high']),
        'hma_slope_rising': bool(cur['hma_slope_rising']),
        # RSI (informational — NOT a gate in V6)
        'rsi14': round(float(cur['rsi14']), 1) if pd.notna(cur['rsi14']) else None,
        'rsi_above_50': bool(cur['rsi_above_50']),
        # MACD (confirmation gate)
        'macd_line': round(float(cur['macd_line']), 4) if pd.notna(cur['macd_line']) else None,
        'signal_line': round(float(cur['signal_line']), 4) if pd.notna(cur['signal_line']) else None,
        'macd_histogram': round(float(cur['macd_histogram']), 4) if pd.notna(cur['macd_histogram']) else None,
        'macd_cross_up': bool(cur['macd_cross_up']),
        # UC (confirmation gate — V6 uses uc_rising, not uc_rising_above)
        'uc': round(float(cur['uc']), 2) if pd.notna(cur['uc']) else None,
        'uc_rsi10': round(float(cur['uc_rsi10']), 1) if pd.notna(cur['uc_rsi10']) else None,
        'uc_rising': bool(cur['uc_rising']),
        # ATR squeeze (V7 entry filter)
        'atr': round(float(cur['atr']), 4) if pd.notna(cur['atr']) else None,
        'atr_rank': round(float(cur['atr_rank']), 1) if pd.notna(cur['atr_rank']) else None,
        'atr_squeeze': bool(cur['atr_squeeze']),
        'atr_fire': bool(cur['atr_fire']),
        'atr_fire_recent': bool(cur['atr_fire_recent']),
        # Composite signals
        'buy_signal': bool(cur['buy_signal']),
        'buy_signal_v6': bool(cur['buy_signal_v6']),
        'quality_tier': quality_tier,
        'tier_label': tier_label,
        'watchlist_signal': bool(cur['watchlist_signal']),
        'exd_exit_signal': bool(cur_exit['exd_signal']),
    }

    if verbose:
        _print_scan_result(result, cur_exit)

    return result


def _print_scan_result(result: dict, cur_exit) -> None:
    """Pretty-print a scan result for terminal output."""
    ticker = result['ticker']
    qt = result['quality_tier']
    tier_info = QUALITY_TIERS.get(qt, {})

    print(f"\n{'=' * 62}")
    print(f"  {ticker} — V7 Weekly Signal Check ({result['date']})")
    print(f"{'=' * 62}")
    print(f"  Close: ${result['close']}")
    print()

    # Entry conditions (V7)
    print(f"  ENTRY CONDITIONS (V7: pivot + OR-gated + ATR squeeze):")
    print(f"    HMA(21) pivot low:     {'YES' if result['hma_pivot_low'] else 'no ':>3}  HMA={result['hma']}")
    print(f"    ── At least ONE gate: ──")
    print(f"    UC rising:             {'YES' if result['uc_rising'] else 'no ':>3}  UC={result['uc']} (RSI10={result['uc_rsi10']})")
    print(f"    MACD cross up (1 bar): {'YES' if result['macd_cross_up'] else 'no ':>3}  MACD={result['macd_line']}, Sig={result['signal_line']}")
    print(f"    ── Volatility filter: ──")
    atr_rank_str = f"{result['atr_rank']:.0f}" if result['atr_rank'] is not None else 'N/A'
    print(f"    ATR squeeze (<20 pct): {'YES' if result['atr_squeeze'] else 'no ':>3}  ATR rank={atr_rank_str}{'  🔥 FIRE' if result.get('atr_fire') else ''}")
    print(f"    RSI(14):               {result['rsi14']:.0f}  (informational — not a gate)")
    print()

    # V6 signal status (diagnostic)
    if result.get('buy_signal_v6') and not result['buy_signal']:
        print(f"  ⚠ V6 buy signal would fire — blocked by ATR squeeze filter (rank={atr_rank_str})")
        print()

    if result['buy_signal']:
        tier_desc = tier_info.get('description', 'Unknown')
        tier_pct = tier_info.get('equity_pct', 0) * 100
        atr_note = "ATR squeeze confirmed — volatility hole entry" if result['atr_squeeze'] else "No ATR squeeze — standard momentum (halved sizing)"
        print(f"  >> BUY SIGNAL — {result['tier_label']} ({tier_desc}) <<")
        print(f"     Sizing: {tier_pct:.1f}% of equity | Execute next week open")
        print(f"     {atr_note}")
        print(f"     Send to LLM gate pipeline for final assessment")
    elif result['watchlist_signal']:
        missing = []
        if not result['hma_pivot_low']:
            missing.append('HMA pivot low')
        if not result['uc_rising'] and not result['macd_cross_up']:
            missing.append('UC rising or MACD cross-up')
        waiting_for = ', '.join(missing) if missing else 'HMA pivot'
        print(f"  >> WATCHLIST — Bullish trend, waiting for: {waiting_for} <<")
        print(f"     HMA trending up — watch for V-bottom pivot next week")
    else:
        missing = []
        if not result['hma_pivot_low']:
            missing.append('HMA pivot')
        if not result['uc_rising'] and not result['macd_cross_up']:
            missing.append('UC or MACD gate')
        print(f"  -- No buy signal. Missing: {', '.join(missing)} --")

    print()
    print(f"  EXIT CHECK (for open positions):")
    hma_pivot_high = bool(cur_exit['hma_pivot_high']) if pd.notna(cur_exit.get('hma_pivot_high', None)) else False
    uc_falling = bool(cur_exit['uc_falling']) if pd.notna(cur_exit.get('uc_falling', None)) else False
    print(f"    HMA pivot high:        {'YES' if hma_pivot_high else 'no '}")
    print(f"    UC falling:            {'YES' if uc_falling else 'no '}")
    print(f"    ExD exit (both):       {'EXIT' if result['exd_exit_signal'] else 'hold'}")


def check_position(ticker: str, entry_price: float,
                   peak_price: float = None) -> dict:
    """Check an open position for V6 ExD exit + tiered profit lock."""
    df = yf.download(ticker, period="2y", progress=False)
    if df.empty:
        return {'ticker': ticker, 'error': 'No data'}

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    weekly = resample_to_weekly(df)
    exit_signals = generate_exit_signal(weekly)

    current_close = float(weekly['close'].iloc[-1])
    if peak_price is None:
        peak_price = float(weekly['close'].max())
    if current_close > peak_price:
        peak_price = current_close

    exd = bool(exit_signals['exd_signal'].iloc[-1])   # informational only in V8 (ExD dropped)
    lock = check_tiered_initial_35(entry_price, current_close, peak_price)
    gain_pct = ((current_close - entry_price) / entry_price) * 100

    action = 'HOLD'
    if lock.get('triggered', False):
        action = f"EXIT — {lock.get('active_tier', 'V8 tiered_initial_35')}"

    print(f"\n  {ticker}: ${current_close} ({gain_pct:+.1f}% from ${entry_price})")
    print(f"    Peak: ${peak_price} | Lock: {lock.get('active_tier', 'none')}")
    if lock.get('lock_level'):
        status = 'BELOW — TRIGGERED' if lock['triggered'] else 'above — safe'
        print(f"    Lock level: ${lock['lock_level']} | Current ${current_close} {status}")
    print(f"    ExD exit: {'YES' if exd else 'no'} (informational — not used in V8)")
    print(f"    >> {action}")

    return {
        'ticker': ticker,
        'entry_price': entry_price,
        'current_close': round(current_close, 2),
        'peak_close': round(peak_price, 2),
        'gain_pct': round(gain_pct, 1),
        'exd_exit': exd,
        'lock_triggered': lock.get('triggered', False),
        'lock_detail': lock,
        'action': action,
    }


def dump_history(ticker: str) -> pd.DataFrame:
    """Dump full weekly indicator history to CSV for verification."""
    df = yf.download(ticker, period="5y", progress=False)
    if df.empty:
        print(f"  No data for {ticker}")
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    weekly = resample_to_weekly(df)
    entry = generate_entry_signal(weekly)
    exit_sig = generate_exit_signal(weekly)

    history = pd.DataFrame(index=weekly.index)
    history['close'] = weekly['close']
    history['hma'] = entry['hma']
    # V6 pivot signals
    history['hma_pivot_low'] = entry['hma_pivot_low']
    history['hma_pivot_high'] = entry['hma_pivot_high']
    history['hma_slope_rising'] = entry['hma_slope_rising']
    # RSI (informational)
    history['rsi_14'] = entry['rsi14']
    # MACD
    history['macd'] = entry['macd_line']
    history['macd_signal'] = entry['signal_line']
    history['macd_hist'] = entry['macd_histogram']
    history['macd_cross_up'] = entry['macd_cross_up']
    # UC
    history['uc'] = entry['uc']
    history['uc_rsi_10'] = entry['uc_rsi10']
    history['uc_rising'] = entry['uc_rising']
    # ATR squeeze (V7)
    history['atr'] = entry['atr']
    history['atr_rank'] = entry['atr_rank']
    history['atr_squeeze'] = entry['atr_squeeze']
    history['atr_fire'] = entry['atr_fire']
    # Composite
    history['buy_signal'] = entry['buy_signal']
    history['buy_signal_v6'] = entry['buy_signal_v6']
    history['quality_tier'] = entry['quality_tier']
    history['tier_label'] = entry['tier_label']
    history['watchlist_signal'] = entry['watchlist_signal']
    history['exd_exit'] = exit_sig['exd_signal']

    filename = f"{ticker}_weekly_indicators_v7.csv"
    history.to_csv(filename)
    print(f"  Saved {len(history)} weeks to {filename}")
    return history


# ═══════════════════════════════════════════════════════════════
# PORTFOLIO SIZING — Quality-Tier Calculator (V6)
# ═══════════════════════════════════════════════════════════════

def calculate_position_size(equity: float, quality_tier: int,
                            gear: str = 'recommended') -> dict:
    """
    Calculate position size based on portfolio equity and quality tier.
    
    V6 sizing is driven by the quality tier assigned at signal time,
    not by a downstream conviction score. Conviction scoring from the
    Investment Gate pipeline can be used to REJECT signals (NO GO) but
    does not change the tier-based allocation.

    Args:
        equity: Current total portfolio equity (cash + positions MTM)
        quality_tier: 1 (T1), 2 (T2), or 3 (T3) from entry signal
        gear: 'conservative', 'recommended', or 'aggressive'

    Returns:
        dict with tier, equity_pct, dollar_amount, and sizing details
    """
    gear_config = SIZING_GEARS.get(gear, SIZING_GEARS['recommended'])

    if quality_tier not in (1, 2, 3, 4, 5, 6):
        return {
            'tier': 0,
            'tier_label': 'INVALID',
            'equity_pct': 0.0,
            'dollar_amount': 0.0,
            'gear': gear,
            'action': 'INVALID TIER — must be 1, 2, or 3',
        }

    tier_info = QUALITY_TIERS[quality_tier]
    equity_pct = gear_config['tiers'][quality_tier]
    dollar_amount = equity * equity_pct

    if dollar_amount < MIN_TRADE_SIZE:
        return {
            'tier': quality_tier,
            'tier_label': tier_info['label'],
            'equity_pct': equity_pct,
            'dollar_amount': round(dollar_amount, 2),
            'gear': gear,
            'action': f'SKIP — ${dollar_amount:,.0f} below ${MIN_TRADE_SIZE:,.0f} minimum',
        }

    return {
        'tier': quality_tier,
        'tier_label': tier_info['label'],
        'description': tier_info['description'],
        'equity_pct': equity_pct,
        'dollar_amount': round(dollar_amount, 2),
        'gear': gear,
        'max_positions': gear_config['max_positions'],
        'action': f"Enter {tier_info['label']} at {equity_pct*100:.0f}% = ${dollar_amount:,.0f}",
    }


def show_portfolio_status(equity: float, positions: list,
                          gear: str = 'recommended'):
    """
    Display current portfolio deployment status with V6 quality tiers.

    Args:
        equity: Current total portfolio equity
        positions: List of dicts with keys: ticker, entry_price, quality_tier,
                   current_price (optional), peak_price (optional)
        gear: Current sizing gear
    """
    gear_config = SIZING_GEARS.get(gear, SIZING_GEARS['recommended'])

    print(f"\n{'=' * 68}")
    print(f"  STERLING GRID V7 — PORTFOLIO STATUS")
    print(f"  Gear: {gear_config['label']} | Max positions: {gear_config['max_positions']}")
    print(f"  Portfolio equity: ${equity:,.0f}")
    print(f"{'=' * 68}")

    # Count positions by tier
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    total_deployed = 0.0
    total_deployed_pct = 0.0

    if positions:
        print(f"\n  OPEN POSITIONS:")
        print(f"  {'Ticker':<8} {'Tier':<6} {'Entry':>8} {'Current':>8} "
              f"{'Return':>8} {'Size%':>6} {'Size$':>10}")
        print(f"  {'-'*62}")

        for pos in positions:
            qt = pos.get('quality_tier', 3)
            tier_counts[qt] = tier_counts.get(qt, 0) + 1
            pct = gear_config['tiers'].get(qt, 0.05)
            dollar = equity * pct
            total_deployed += dollar
            total_deployed_pct += pct

            current = pos.get('current_price', pos['entry_price'])
            ret = ((current - pos['entry_price']) / pos['entry_price']) * 100
            tier_label = QUALITY_TIERS[qt]['label']

            print(f"  {pos['ticker']:<8} {tier_label:<6} "
                  f"${pos['entry_price']:>7.2f} ${current:>7.2f} "
                  f"{ret:>+7.1f}% {pct*100:>5.0f}% ${dollar:>9,.0f}")

    n_positions = len(positions) if positions else 0
    slots_free = gear_config['max_positions'] - n_positions
    cash_pct = 1.0 - total_deployed_pct
    cash_dollar = equity * cash_pct

    print(f"\n  DEPLOYMENT SUMMARY:")
    print(f"    Positions: {n_positions} / {gear_config['max_positions']} "
          f"({slots_free} slots available)")
    print(f"    Deployed:  {total_deployed_pct*100:.0f}% (${total_deployed:,.0f})")
    print(f"    Cash:      {cash_pct*100:.0f}% (${cash_dollar:,.0f})")

    print(f"\n  TIER CAPACITY (V7 quality-based):")
    for qt in [1, 2, 3, 4, 5, 6]:
        info = QUALITY_TIERS[qt]
        pct = gear_config['tiers'][qt]
        used = tier_counts.get(qt, 0)
        print(f"    {info['label']}  {pct*100:>4.0f}% = ${equity * pct:>9,.0f} per position | "
              f"{used} open | WR={info['backtest_wr']}, Avg={info['backtest_avg']}")

    if slots_free > 0:
        print(f"\n  NEXT SIGNAL SIZING:")
        for qt in [1, 2, 3, 4, 5, 6]:
            sizing = calculate_position_size(equity, qt, gear)
            info = QUALITY_TIERS[qt]
            print(f"    {info['label']} signal → {sizing['equity_pct']*100:.0f}% = ${sizing['dollar_amount']:,.0f}")

    print(f"\n{'=' * 68}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sterling Grid V8 — Weekly Indicator Calculator")
        print("  Entry: bare HMA(21) pivot low (fire wide — no UC/MACD/ATR gate)")
        print("  Tiers: gates/ATR squeeze now inform SIZING only (T1 high … T6 bare pivot)")
        print("  Exit:  tiered_initial_35 — -35% floor until +50%, then trailing lock (ExD dropped)")
        print("  Decide on weekly close, act at next candle open (buy AND sell)")
        print()
        print("Scan for buy signals:")
        print("  python sterling_indicators.py MARA RKLB IONQ")
        print("  python sterling_indicators.py MARA RKLB IONQ --exclude-open MARA,RKLB")
        print()
        print("Check open positions (ticker:entry_price):")
        print("  python sterling_indicators.py --check MARA:5.50 RKLB:12.00")
        print()
        print("Check with known peak (ticker:entry:peak):")
        print("  python sterling_indicators.py --check MARA:5.50:28.50")
        print()
        print("Portfolio status (equity + positions as ticker:entry:tier):")
        print("  python sterling_indicators.py --portfolio 120000 MARA:5.50:1 RKLB:12.00:2 IONQ:8.25:3")
        print()
        print("Position size calculator (equity + tier):")
        print("  python sterling_indicators.py --size 120000 T1")
        print("  python sterling_indicators.py --size 120000 T2 --gear aggressive")
        print()
        print("Dump full indicator history to CSV:")
        print("  python sterling_indicators.py --history MARA")
        print()
        print("Sizing gears: --gear conservative|recommended|aggressive (default: recommended)")
        print("Exclude open positions from scan: --exclude-open MARA,RKLB,IONQ")
        sys.exit(1)

    # Parse optional --gear and --exclude-open flags from anywhere in args
    gear = 'recommended'
    exclude_open = set()
    filtered_args = []
    skip_next = False
    for i, arg in enumerate(sys.argv[1:], 1):
        if skip_next:
            skip_next = False
            continue
        if arg == '--gear' and i < len(sys.argv) - 1:
            gear = sys.argv[i + 1]
            skip_next = True
        elif arg == '--exclude-open' and i < len(sys.argv) - 1:
            exclude_open = {t.strip().upper() for t in sys.argv[i + 1].split(',')}
            skip_next = True
        else:
            filtered_args.append(arg)

    if filtered_args and filtered_args[0] == '--check':
        print("=" * 68)
        print("  STERLING GRID V6 — POSITION CHECK")
        print("=" * 68)
        for arg in filtered_args[1:]:
            parts = arg.split(':')
            if len(parts) < 2:
                print(f"  Invalid: {arg} (use TICKER:ENTRY or TICKER:ENTRY:PEAK)")
                continue
            ticker = parts[0].upper()
            entry_price = float(parts[1])
            peak_price = float(parts[2]) if len(parts) > 2 else None
            check_position(ticker, entry_price, peak_price)
        print(f"\n{'=' * 68}")

    elif filtered_args and filtered_args[0] == '--portfolio':
        if len(filtered_args) < 2:
            print("Usage: --portfolio EQUITY [TICKER:ENTRY:TIER ...]")
            print("  Example: --portfolio 120000 MARA:5.50:1 RKLB:12.00:2")
            sys.exit(1)

        equity = float(filtered_args[1])
        positions = []
        for arg in filtered_args[2:]:
            parts = arg.split(':')
            if len(parts) < 3:
                print(f"  Warning: {arg} needs TICKER:ENTRY:TIER format, skipping")
                continue
            ticker = parts[0].upper()
            entry_price = float(parts[1])
            quality_tier = int(parts[2])

            # Try to fetch current price
            try:
                df = yf.download(ticker, period="5d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                current_price = float(df['Close'].iloc[-1]) if not df.empty else entry_price
            except Exception:
                current_price = entry_price

            positions.append({
                'ticker': ticker,
                'entry_price': entry_price,
                'quality_tier': quality_tier,
                'current_price': round(current_price, 2),
            })

        show_portfolio_status(equity, positions, gear)

    elif filtered_args and filtered_args[0] == '--size':
        if len(filtered_args) < 3:
            print("Usage: --size EQUITY TIER [--gear conservative|recommended|aggressive]")
            print("  TIER = T1-T6 (or 1-6)")
            print("  T1-T3: ATR squeeze confirmed | T4-T6: no ATR squeeze (halved sizing)")
            print("  Example: --size 120000 T1")
            print("  Example: --size 200000 T5 --gear aggressive")
            sys.exit(1)

        equity = float(filtered_args[1])
        tier_arg = filtered_args[2].upper().replace('T', '')
        try:
            quality_tier = int(tier_arg)
        except ValueError:
            print(f"  Invalid tier: {filtered_args[2]} (use T1, T2, T3 or 1, 2, 3)")
            sys.exit(1)

        sizing = calculate_position_size(equity, quality_tier, gear)

        print(f"\n{'=' * 52}")
        print(f"  V6 POSITION SIZE CALCULATOR")
        print(f"{'=' * 52}")
        print(f"  Portfolio equity:  ${equity:,.0f}")
        print(f"  Quality tier:      {sizing.get('tier_label', '?')} — {sizing.get('description', '?')}")
        print(f"  Sizing gear:       {gear}")
        print(f"  Allocation:        {sizing['equity_pct']*100:.0f}% of equity")
        print(f"  Position size:     ${sizing['dollar_amount']:,.0f}")
        print(f"  >> {sizing['action']}")
        print(f"{'=' * 52}")

    elif filtered_args and filtered_args[0] == '--history':
        for ticker in filtered_args[1:]:
            dump_history(ticker.upper())

    else:
        print("=" * 68)
        print("  STERLING GRID V7 — WEEKLY SIGNAL SCAN")
        print(f"  Entry: HMA pivot + (UC rising OR MACD cross-up)")
        print(f"  Tiers: T1-T3 (ATR squeeze) / T4-T6 (no ATR squeeze)")
        print(f"  Sizing: {gear} gear ({SIZING_GEARS[gear]['label']})")
        print("=" * 68)

        buy_signals = []
        watchlist_signals = []
        for ticker in filtered_args:
            result = scan_ticker(ticker.upper())
            if result.get('buy_signal'):
                label = f"{result['ticker']} ({result['tier_label']})"
                if result['ticker'] in exclude_open:
                    label += ' [open]'
                buy_signals.append(label)
            elif result.get('watchlist_signal'):
                if result['ticker'] not in exclude_open:
                    watchlist_signals.append(result['ticker'])

        print(f"\n{'=' * 68}")
        if buy_signals:
            print(f"  BUY SIGNALS: {', '.join(buy_signals)}")
            print(f"  -> Send to LLM gate pipeline for final assessment")
            print(f"  -> Execute confirmed trades next week open")
            print(f"  -> Sizing: T1=20%, T2=10%, T3=5% (ATR) | T4=10%, T5=5%, T6=2.5%")
        else:
            print(f"  No buy signals this week.")
        print()
        if watchlist_signals:
            print(f"  WATCHLIST: {', '.join(watchlist_signals)}")
            print(f"  -> Bullish trend forming — watch for HMA pivot low next week")
        else:
            print(f"  No watchlist signals.")
        print(f"{'=' * 68}")
