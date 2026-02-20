#!/usr/bin/env python3
"""
Legacy Indicators — Old BoS/Banker calculations preserved for daily_scanner.py

The WEEKLY scanner has been upgraded to use Sterling Grid indicators
(core/sterling_indicators.py). These legacy functions are kept ONLY for
the daily scanner, which continues to use the old HMA Pivot BoS + Banker
approach.

DO NOT use these in the weekly pipeline. Use core/sterling_indicators.py instead.

Extracted from core/scanner.py during Sterling Grid upgrade (2026-02).
"""

import numpy as np
import pandas as pd
from typing import Tuple

from config import (
    BANKER_CENTER,
    BANKER_SCALE_FACTOR,
    VWAP_PERIOD,
    HMA_PERIOD,
)


def calculate_banker(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Calculate Banker indicator (institutional accumulation proxy) for current
    and previous bars.

    Formula: ((Close / 20-day VWAP) - 1) * 100 + 50

    Returns:
        Tuple[float, float]: (current_bar_value, previous_bar_value)
    """
    try:
        if len(df) < VWAP_PERIOD + 1:
            return 0.0, 0.0

        def _banker_for_slice(slice_df: pd.DataFrame) -> float:
            typical = (slice_df['High'] + slice_df['Low'] + slice_df['Close']) / 3
            vwap = (typical * slice_df['Volume']).sum() / slice_df['Volume'].sum()
            close = float(slice_df['Close'].iloc[-1])
            if vwap == 0:
                return 0.0
            deviation_pct = ((close / vwap) - 1) * 100
            banker = BANKER_CENTER + (deviation_pct * BANKER_SCALE_FACTOR)
            return round(max(0, min(100, banker)), 1)

        current_slice = df.tail(VWAP_PERIOD)
        current_val = _banker_for_slice(current_slice)

        prev_slice = df.iloc[-(VWAP_PERIOD + 1):-1]
        prev_val = _banker_for_slice(prev_slice)

        return current_val, prev_val
    except Exception:
        return 0.0, 0.0


def calculate_hma(series: pd.Series, length: int = HMA_PERIOD) -> pd.Series:
    """
    Calculate Hull Moving Average (HMA).
    HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    """
    import math
    half_length = max(1, length // 2)
    sqrt_length = max(1, int(math.sqrt(length)))

    def wma(s, n):
        weights = np.arange(1, n + 1)
        return s.rolling(n).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    wma_half = wma(series, half_length)
    wma_full = wma(series, length)

    raw_hma = 2 * wma_half - wma_full
    hma = wma(raw_hma, sqrt_length)

    return hma


def find_pivots(series: pd.Series, k: int = 1) -> Tuple[pd.Series, pd.Series]:
    """
    Find pivot highs and lows on a series.
    Returns two series with pivot values (NaN elsewhere).
    """
    pivot_highs = pd.Series(index=series.index, dtype=float)
    pivot_lows = pd.Series(index=series.index, dtype=float)

    for i in range(k, len(series) - k):
        window = series.iloc[i-k:i+k+1]
        center_val = series.iloc[i]

        if center_val == window.max() and (window == center_val).sum() == 1:
            pivot_highs.iloc[i + k] = center_val

        if center_val == window.min() and (window == center_val).sum() == 1:
            pivot_lows.iloc[i + k] = center_val

    return pivot_highs, pivot_lows


def calculate_bos(df: pd.DataFrame, hma_length: int = HMA_PERIOD, pivot_k: int = 1) -> Tuple[bool, bool, dict]:
    """
    Calculate Break of Structure signals using HMA PIVOT method.

    Returns: (bos_up, bos_down, debug_info)
    """
    debug_info = {}

    try:
        if len(df) < 60:
            return False, False, debug_info

        weekly = df.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        if len(weekly) < hma_length + pivot_k + 5:
            return False, False, debug_info

        hl2 = (weekly['High'] + weekly['Low']) / 2
        hma = calculate_hma(hl2, hma_length)
        pivot_highs, pivot_lows = find_pivots(hma, pivot_k)

        upper = pd.Series(index=weekly.index, dtype=float)
        lower = pd.Series(index=weekly.index, dtype=float)

        last_ph = np.nan
        last_pl = np.nan

        for i in range(len(weekly)):
            if not pd.isna(pivot_highs.iloc[i]):
                last_ph = pivot_highs.iloc[i]
            if not pd.isna(pivot_lows.iloc[i]):
                last_pl = pivot_lows.iloc[i]
            upper.iloc[i] = last_ph
            lower.iloc[i] = last_pl

        if len(weekly) < 2:
            return False, False, debug_info

        current_upper = upper.iloc[-1]
        prev_upper = upper.iloc[-2]
        current_lower = lower.iloc[-1]
        prev_lower = lower.iloc[-2]
        current_close = weekly['Close'].iloc[-1]

        bos_up = (not pd.isna(current_lower) and not pd.isna(prev_lower) and
                  current_lower != prev_lower)

        bos_down = (not pd.isna(current_upper) and not pd.isna(prev_upper) and
                    current_upper != prev_upper)

        debug_info = {
            'weekly_bars': len(weekly),
            'hma_current': float(hma.iloc[-1]) if not pd.isna(hma.iloc[-1]) else None,
            'upper_step': float(current_upper) if not pd.isna(current_upper) else None,
            'lower_step': float(current_lower) if not pd.isna(current_lower) else None,
            'prev_upper': float(prev_upper) if not pd.isna(prev_upper) else None,
            'prev_lower': float(prev_lower) if not pd.isna(prev_lower) else None,
            'current_close': float(current_close),
            'last_date': str(weekly.index[-1].date()),
            'signal_type': 'HMA_PIVOT',
        }

        return bos_up, bos_down, debug_info

    except Exception as e:
        debug_info['error'] = str(e)
        return False, False, debug_info
