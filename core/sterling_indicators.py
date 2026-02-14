#!/usr/bin/env python3
"""
Sterling Grid — Weekly Indicator Calculator (EXACT BACKTEST MATCH)
===================================================================
Every calculation verified line-by-line against the actual backtest source:
  - src/indicators.py    (HMA, RSI, MACD, Undercurrent)
  - src/v2_signals.py    (entry signal generation + corridor alternation)
  - src/v3_exits.py      (ExD exit + tiered profit lock)

CRITICAL CORRECTIONS vs earlier draft:
  1. Undercurrent is NOT a VWAP indicator — it is clip(1.5×(RSI(10)−50), 0, 20)
  2. MACD cross-up is a SINGLE BAR event, not a 3-bar lookback
  3. Profit lock tier is based on CURRENT return, not peak return (tiers degrade)
  4. Scanner's "Banker" (VWAP deviation) ≠ backtest "UC" (normalised RSI). 
     The scanner needs updating to use this RSI-derived UC.

Position Sizing: Conviction-Tiered (15×6 Recommended)
  - STRONG BUY conviction 8-10 → 20% of equity (max 2 positions)
  - STRONG BUY conviction 7    → 15% of equity (max 3 positions)
  - SPEC BUY conviction 4-6    → 8% of equity  (max 2 positions)
  - Maximum 6 concurrent positions, minimum 10% cash reserve
  - Adaptive gear-shift: conservative (10×8) / recommended (15×6) / aggressive (20×5)

Usage:
    python sterling_indicators.py TICKER [TICKER2 ...]
    python sterling_indicators.py MARA RKLB IONQ

Position check (with entry price):
    python sterling_indicators.py --check MARA:5.50 RKLB:12.00

Position check (with entry price and known peak):
    python sterling_indicators.py --check MARA:5.50:28.50

Portfolio status (equity + positions as ticker:entry:conviction):
    python sterling_indicators.py --portfolio 120000 MARA:5.50:9 RKLB:12.00:7

Position size calculator:
    python sterling_indicators.py --size 120000 8

Sizing gear override:
    python sterling_indicators.py --size 200000 5 --gear aggressive

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
RSI_PERIOD = 14           # RSI(14) for entry "rsi_above_50" condition
MACD_FAST = 12            # MACD fast EMA
MACD_SLOW = 26            # MACD slow EMA
MACD_SIGNAL = 9           # MACD signal EMA
PRICE_CAP = 25.0          # Maximum entry price

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

# ═══════════════════════════════════════════════════════════════
# POSITION SIZING — Conviction-Tiered (15×6 Recommended Config)
# ═══════════════════════════════════════════════════════════════

# Base sizing config (recommended starting configuration)
MAX_CONCURRENT_POSITIONS = 6
MIN_CASH_RESERVE_PCT = 0.10    # Always keep 10% cash

# Conviction tiers: (verdict, conviction_range, equity_pct, max_slots)
CONVICTION_TIERS = {
    'HIGH':     {'min_conviction': 8, 'max_conviction': 10, 'equity_pct': 0.20, 'max_slots': 2,
                 'label': 'STRONG BUY (high conviction)'},
    'STANDARD': {'min_conviction': 7, 'max_conviction': 7,  'equity_pct': 0.15, 'max_slots': 3,
                 'label': 'STRONG BUY (standard)'},
    'SPEC':     {'min_conviction': 4, 'max_conviction': 6,  'equity_pct': 0.08, 'max_slots': 2,
                 'label': 'SPEC BUY'},
}

# Gear-shift configurations
SIZING_GEARS = {
    'conservative': {'base_pct': 0.10, 'max_positions': 8,
                     'tiers': {'HIGH': 0.12, 'STANDARD': 0.10, 'SPEC': 0.06}},
    'recommended':  {'base_pct': 0.15, 'max_positions': 6,
                     'tiers': {'HIGH': 0.20, 'STANDARD': 0.15, 'SPEC': 0.08}},
    'aggressive':   {'base_pct': 0.20, 'max_positions': 5,
                     'tiers': {'HIGH': 0.25, 'STANDARD': 0.20, 'SPEC': 0.10}},
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


def calculate_hma_slope(weekly_df: pd.DataFrame,
                        period: int = HMA_PERIOD) -> pd.DataFrame:
    """
    HMA slope signals.
    Source: indicators.py compute_hma_slope() lines 313-320
    
    hma_rising  = hma[i] > hma[i-1]   (bullish entry component)
    hma_falling = hma[i] < hma[i-1]   (bearish exit component)
    """
    hl2 = (weekly_df['high'] + weekly_df['low']) / 2
    hma_vals = calculate_hma(hl2, period)

    result = pd.DataFrame(index=weekly_df.index)
    result['hma'] = hma_vals
    result['hma_prev'] = hma_vals.shift(1)
    result['hma_slope_rising'] = (hma_vals > hma_vals.shift(1)).fillna(False)
    result['hma_slope_falling'] = (hma_vals < hma_vals.shift(1)).fillna(False)
    return result


def calculate_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """
    RSI with Wilder's smoothing.
    Source: indicators.py pulse() lines 116-123
    
    Uses ewm(alpha=1/period, adjust=False) which is Wilder's smoothing.
    This is the RSI(14) used for the "rsi_above_50" entry condition.
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

    # Also compute hist_pos for reference (used by V1 entry "macd_hist_pos")
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
    
    UC entry condition "uc_rising_above" (v2_signals.py lines 65-68):
        UC > UC.shift(1) AND UC > 0
        In RSI terms: RSI(10) > 50 AND RSI(10) is increasing
    
    UC exit condition "uc_falling" (v3_exits.py line for ExD):
        UC < UC.shift(1)
        In RSI terms: RSI(10) momentum is decreasing
    
    NOTE: This is DIFFERENT from the production scanner's "Banker" indicator,
    which uses a VWAP deviation formula: ((Close/VWAP) - 1) × 100 + 50.
    Banker and UC are conceptually related (both measure momentum) but are
    mathematically different calculations. The scanner should be updated to
    use this RSI-derived UC for consistency with backtested results.
    """
    tf_divisor = {"daily": 1.0, "weekly": 5.0, "monthly": 21.0}.get(timeframe, 5.0)
    length = max(2, int(round(target_days / tf_divisor)))  # = 10 for weekly

    # RSI(10) with Wilder's smoothing — separate from the RSI(14) entry condition
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
    result['uc_rising'] = (uc > uc.shift(1)).fillna(False)
    result['uc_falling'] = (uc < uc.shift(1)).fillna(False)
    result['uc_above_zero'] = (uc > 0).fillna(False)
    # "uc_rising_above" — exact match to v2_signals.py lines 65-68
    result['uc_rising_above'] = (
        (uc > uc.shift(1)) & (uc > 0)
    ).fillna(False)

    return result


# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION (matching src/v2_signals.py exactly)
# ═══════════════════════════════════════════════════════════════

def generate_entry_signal(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sterling Grid V2 entry signal.
    Source: v2_signals.py generate_signals_v2() with V3/V4 config:
        signal_type = "slope"
        uc_cond     = "uc_rising_above"
        rsi_cond    = "rsi_above_50"
        macd_cond   = "macd_cross_up"
    
    BUY fires when ALL are true on the SAME weekly bar:
        1. HMA(21) slope rising — current HMA > previous HMA
        2. RSI(14) > 50
        3. MACD(12,26,9) cross up — MACD crosses above signal THIS bar
        4. UC rising above — UC > UC.shift(1) AND UC > 0
        5. Price < $25
    
    The backtest also applies corridor alternation (buy-sell-buy-sell
    enforcement) which prevents consecutive buy signals. This scanner
    checks one bar at a time so alternation isn't applied here — it's
    handled by only entering when not already in a position.
    """
    hma_data = calculate_hma_slope(weekly_df)
    rsi = calculate_rsi(weekly_df['close'])
    macd_data = calculate_macd(weekly_df['close'])
    uc_data = calculate_undercurrent(weekly_df)

    signals = pd.DataFrame(index=weekly_df.index)
    signals['close'] = weekly_df['close']
    signals['hma'] = hma_data['hma']
    signals['hma_slope_rising'] = hma_data['hma_slope_rising']
    signals['rsi14'] = rsi
    signals['rsi_above_50'] = (rsi > 50).fillna(False)
    signals['macd_line'] = macd_data['macd_line']
    signals['signal_line'] = macd_data['signal_line']
    signals['macd_histogram'] = macd_data['histogram']
    signals['macd_cross_up'] = macd_data['macd_cross_up']
    signals['uc'] = uc_data['uc']
    signals['uc_rsi10'] = uc_data['uc_rsi10']
    signals['uc_rising_above'] = uc_data['uc_rising_above']

    # Combined buy — all conditions AND'd (v2_signals.py lines 178-185)
    signals['buy_signal'] = (
        signals['hma_slope_rising'] &
        signals['rsi_above_50'] &
        signals['macd_cross_up'] &         # Single bar, not lookback
        signals['uc_rising_above'] &
        (signals['close'] < PRICE_CAP)
    )

    return signals


def generate_exit_signal(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    ExD exit signal.
    Source: v3_exits.py run_compound_exit() lines 162-163
    
    ExD fires when BOTH are true on the same weekly bar:
        1. HMA(21) slope falling (from v2_signals sell = hma_falling)
        2. UC falling (UC < UC.shift(1))
    
    Exact code from v3_exits.py:
        uc_falling = (uc_series < uc_series.shift(1)).fillna(False)
        exd_sell = sell_signal & uc_falling
    """
    hma_data = calculate_hma_slope(weekly_df)
    uc_data = calculate_undercurrent(weekly_df)

    signals = pd.DataFrame(index=weekly_df.index)
    signals['close'] = weekly_df['close']
    signals['hma'] = hma_data['hma']
    signals['hma_slope_falling'] = hma_data['hma_slope_falling']
    signals['uc'] = uc_data['uc']
    signals['uc_falling'] = uc_data['uc_falling']

    # ExD = HMA bearish AND UC falling (same bar)
    signals['exd_signal'] = (
        signals['hma_slope_falling'] &
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
    
    This is intentional: it gives stocks room to recover from pullbacks
    rather than locking in with an aggressively tight trail.
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


# ═══════════════════════════════════════════════════════════════
# SCANNER — Check any ticker for current signals
# ═══════════════════════════════════════════════════════════════

def scan_ticker(ticker: str, verbose: bool = True) -> dict:
    """Scan a single ticker for Sterling Grid entry/exit signals."""
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

    result = {
        'ticker': ticker,
        'date': str(weekly.index[-1].date()),
        'close': round(float(cur['close']), 2),
        'hma': round(float(cur['hma']), 4) if pd.notna(cur['hma']) else None,
        'hma_slope_rising': bool(cur['hma_slope_rising']),
        'rsi14': round(float(cur['rsi14']), 1) if pd.notna(cur['rsi14']) else None,
        'rsi_above_50': bool(cur['rsi_above_50']),
        'macd_line': round(float(cur['macd_line']), 4) if pd.notna(cur['macd_line']) else None,
        'signal_line': round(float(cur['signal_line']), 4) if pd.notna(cur['signal_line']) else None,
        'macd_histogram': round(float(cur['macd_histogram']), 4) if pd.notna(cur['macd_histogram']) else None,
        'macd_cross_up': bool(cur['macd_cross_up']),
        'uc': round(float(cur['uc']), 2) if pd.notna(cur['uc']) else None,
        'uc_rsi10': round(float(cur['uc_rsi10']), 1) if pd.notna(cur['uc_rsi10']) else None,
        'uc_rising_above': bool(cur['uc_rising_above']),
        'buy_signal': bool(cur['buy_signal']),
        'exd_exit_signal': bool(cur_exit['exd_signal']),
        'price_under_25': float(cur['close']) < PRICE_CAP,
    }

    if verbose:
        print(f"\n{'=' * 62}")
        print(f"  {ticker} — Weekly Signal Check ({result['date']})")
        print(f"{'=' * 62}")
        print(f"  Close: ${result['close']}")
        print()
        print(f"  ENTRY CONDITIONS:")
        print(f"    HMA(21) slope rising:  {'YES' if result['hma_slope_rising'] else 'no ':>3}  HMA={result['hma']}")
        print(f"    RSI(14) > 50:          {'YES' if result['rsi_above_50'] else 'no ':>3}  RSI={result['rsi14']}")
        print(f"    MACD cross up (1 bar): {'YES' if result['macd_cross_up'] else 'no ':>3}  MACD={result['macd_line']}, Sig={result['signal_line']}")
        print(f"    UC rising & > 0:       {'YES' if result['uc_rising_above'] else 'no ':>3}  UC={result['uc']} (RSI10={result['uc_rsi10']})")
        print(f"    Price < $25:           {'YES' if result['price_under_25'] else 'no ':>3}  ${result['close']}")
        print()

        if result['buy_signal']:
            print(f"  >> BUY SIGNAL ACTIVE — Send to LLM gate pipeline <<")
        else:
            missing = []
            if not result['hma_slope_rising']: missing.append('HMA slope')
            if not result['rsi_above_50']: missing.append('RSI>50')
            if not result['macd_cross_up']: missing.append('MACD cross')
            if not result['uc_rising_above']: missing.append('UC rising')
            if not result['price_under_25']: missing.append('Price<$25')
            print(f"  -- No buy signal. Missing: {', '.join(missing)} --")

        print()
        print(f"  EXIT CHECK (for open positions):")
        print(f"    HMA slope falling:     {'YES' if not result['hma_slope_rising'] else 'no '}")
        uc_falling = bool(cur_exit['uc_falling']) if pd.notna(cur_exit.get('uc_falling', None)) else False
        print(f"    UC falling:            {'YES' if uc_falling else 'no '}")
        print(f"    ExD exit (both):       {'EXIT' if result['exd_exit_signal'] else 'hold'}")

    return result


def check_position(ticker: str, entry_price: float,
                   peak_price: float = None) -> dict:
    """Check an open position for ExD exit + tiered profit lock."""
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

    exd = bool(exit_signals['exd_signal'].iloc[-1])
    lock = check_profit_lock(entry_price, current_close, peak_price)
    gain_pct = ((current_close - entry_price) / entry_price) * 100

    action = 'HOLD'
    if exd and lock.get('triggered', False):
        action = f"EXIT — ExD + Profit lock ({lock['active_tier']})"
    elif exd:
        action = 'EXIT — ExD (trend reversal confirmed)'
    elif lock.get('triggered', False):
        action = f"EXIT — Profit lock ({lock['active_tier']})"

    print(f"\n  {ticker}: ${current_close} ({gain_pct:+.1f}% from ${entry_price})")
    print(f"    Peak: ${peak_price} | Lock: {lock.get('active_tier', 'none')}")
    if lock.get('lock_level'):
        status = 'BELOW — TRIGGERED' if lock['triggered'] else 'above — safe'
        print(f"    Lock level: ${lock['lock_level']} | Current ${current_close} {status}")
    print(f"    ExD exit: {'YES — EXIT' if exd else 'no'}")
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
    history['hma_slope_rising'] = entry['hma_slope_rising']
    history['rsi_14'] = entry['rsi14']
    history['rsi_above_50'] = entry['rsi_above_50']
    history['macd'] = entry['macd_line']
    history['macd_signal'] = entry['signal_line']
    history['macd_hist'] = entry['macd_histogram']
    history['macd_cross_up'] = entry['macd_cross_up']
    history['uc'] = entry['uc']
    history['uc_rsi_10'] = entry['uc_rsi10']
    history['uc_rising_above'] = entry['uc_rising_above']
    history['buy_signal'] = entry['buy_signal']
    history['exd_exit'] = exit_sig['exd_signal']

    filename = f"{ticker}_weekly_indicators.csv"
    history.to_csv(filename)
    print(f"  Saved {len(history)} weeks to {filename}")
    return history


# ═══════════════════════════════════════════════════════════════
# PORTFOLIO SIZING — Conviction-Tiered Calculator
# ═══════════════════════════════════════════════════════════════

def calculate_position_size(equity: float, conviction: int,
                            gear: str = 'recommended') -> dict:
    """
    Calculate position size based on portfolio equity, conviction score,
    and current sizing gear.

    Args:
        equity: Current total portfolio equity (cash + positions MTM)
        conviction: Gate pipeline conviction score (1-10)
        gear: 'conservative', 'recommended', or 'aggressive'

    Returns:
        dict with tier, equity_pct, dollar_amount, and sizing details
    """
    gear_config = SIZING_GEARS.get(gear, SIZING_GEARS['recommended'])

    if conviction >= 8:
        tier_key = 'HIGH'
    elif conviction == 7:
        tier_key = 'STANDARD'
    elif conviction >= 4:
        tier_key = 'SPEC'
    else:
        return {
            'tier': 'NO GO',
            'conviction': conviction,
            'equity_pct': 0.0,
            'dollar_amount': 0.0,
            'gear': gear,
            'action': 'DO NOT ENTER — conviction too low',
        }

    equity_pct = gear_config['tiers'][tier_key]
    dollar_amount = equity * equity_pct
    tier_info = CONVICTION_TIERS[tier_key]

    return {
        'tier': tier_key,
        'tier_label': tier_info['label'],
        'conviction': conviction,
        'equity_pct': equity_pct,
        'dollar_amount': round(dollar_amount, 2),
        'gear': gear,
        'max_positions': gear_config['max_positions'],
        'max_tier_slots': tier_info['max_slots'],
        'action': f"Enter at {equity_pct*100:.0f}% = ${dollar_amount:,.0f}",
    }


def show_portfolio_status(equity: float, positions: list,
                          gear: str = 'recommended'):
    """
    Display current portfolio deployment status with conviction tiers.

    Args:
        equity: Current total portfolio equity
        positions: List of dicts with keys: ticker, entry_price, conviction,
                   current_price (optional), peak_price (optional)
        gear: Current sizing gear
    """
    gear_config = SIZING_GEARS.get(gear, SIZING_GEARS['recommended'])

    print(f"\n{'=' * 68}")
    print(f"  STERLING GRID — PORTFOLIO STATUS")
    print(f"  Gear: {gear.upper()} | Max positions: {gear_config['max_positions']}")
    print(f"  Portfolio equity: ${equity:,.0f}")
    print(f"{'=' * 68}")

    # Count positions by tier
    tier_counts = {'HIGH': 0, 'STANDARD': 0, 'SPEC': 0}
    total_deployed = 0.0
    total_deployed_pct = 0.0

    if positions:
        print(f"\n  OPEN POSITIONS:")
        print(f"  {'Ticker':<8} {'Tier':<10} {'Entry':>8} {'Current':>8} "
              f"{'Return':>8} {'Size%':>6} {'Size$':>10}")
        print(f"  {'-'*60}")

        for pos in positions:
            conv = pos.get('conviction', 7)
            if conv >= 8:
                tier_key = 'HIGH'
            elif conv == 7:
                tier_key = 'STANDARD'
            else:
                tier_key = 'SPEC'

            tier_counts[tier_key] += 1
            pct = gear_config['tiers'][tier_key]
            dollar = equity * pct
            total_deployed += dollar
            total_deployed_pct += pct

            current = pos.get('current_price', pos['entry_price'])
            ret = ((current - pos['entry_price']) / pos['entry_price']) * 100

            print(f"  {pos['ticker']:<8} {tier_key:<10} "
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
    if cash_pct < MIN_CASH_RESERVE_PCT:
        print(f"    WARNING: Cash below {MIN_CASH_RESERVE_PCT*100:.0f}% minimum reserve!")

    print(f"\n  TIER CAPACITY:")
    for tier_key, info in CONVICTION_TIERS.items():
        used = tier_counts[tier_key]
        cap = info['max_slots']
        avail = cap - used
        pct = gear_config['tiers'][tier_key]
        print(f"    {tier_key:<10} {used}/{cap} used | "
              f"{'Can add ' + str(avail) if avail > 0 else 'FULL'} | "
              f"{pct*100:.0f}% = ${equity * pct:,.0f} per position")

    if slots_free > 0:
        print(f"\n  NEXT POSITION SIZING (if signal fires):")
        for conv_label, conv_val in [("High conviction (8-10)", 9),
                                      ("Standard (7)", 7),
                                      ("Spec buy (4-6)", 5)]:
            sizing = calculate_position_size(equity, conv_val, gear)
            if sizing['tier'] != 'NO GO':
                tier_key = sizing['tier']
                slots_left = CONVICTION_TIERS[tier_key]['max_slots'] - tier_counts[tier_key]
                status = f"${sizing['dollar_amount']:,.0f}" if slots_left > 0 else "TIER FULL"
                print(f"    {conv_label}: {sizing['equity_pct']*100:.0f}% = {status}")

    print(f"\n{'=' * 68}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sterling Grid — Weekly Indicator Calculator")
        print("  (Exact match to V1-V4 backtest calculations)")
        print("  Recommended sizing: 15×6 with conviction tiers")
        print()
        print("Scan for buy signals:")
        print("  python sterling_indicators.py MARA RKLB IONQ")
        print()
        print("Check open positions (ticker:entry_price):")
        print("  python sterling_indicators.py --check MARA:5.50 RKLB:12.00")
        print()
        print("Check with known peak (ticker:entry:peak):")
        print("  python sterling_indicators.py --check MARA:5.50:28.50")
        print()
        print("Portfolio status (equity + positions as ticker:entry:conviction):")
        print("  python sterling_indicators.py --portfolio 120000 MARA:5.50:9 RKLB:12.00:7 IONQ:8.25:5")
        print()
        print("Position size calculator (equity + conviction score):")
        print("  python sterling_indicators.py --size 120000 8")
        print()
        print("Dump full indicator history to CSV:")
        print("  python sterling_indicators.py --history MARA")
        print()
        print("Sizing gears: --gear conservative|recommended|aggressive (default: recommended)")
        sys.exit(1)

    # Parse optional --gear flag from anywhere in args
    gear = 'recommended'
    filtered_args = []
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--gear' and i + 1 < len(sys.argv):
            gear = sys.argv[i + 1]
            # Skip the next arg too
        elif i > 1 and sys.argv[i - 1] == '--gear':
            continue  # This is the gear value, already captured
        else:
            filtered_args.append(arg)

    if filtered_args and filtered_args[0] == '--check':
        print("=" * 68)
        print("  STERLING GRID — POSITION CHECK")
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
            print("Usage: --portfolio EQUITY [TICKER:ENTRY:CONVICTION ...]")
            print("  Example: --portfolio 120000 MARA:5.50:9 RKLB:12.00:7")
            sys.exit(1)

        equity = float(filtered_args[1])
        positions = []
        for arg in filtered_args[2:]:
            parts = arg.split(':')
            if len(parts) < 3:
                print(f"  Warning: {arg} needs TICKER:ENTRY:CONVICTION format, skipping")
                continue
            ticker = parts[0].upper()
            entry_price = float(parts[1])
            conviction = int(parts[2])

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
                'conviction': conviction,
                'current_price': round(current_price, 2),
            })

        show_portfolio_status(equity, positions, gear)

    elif filtered_args and filtered_args[0] == '--size':
        if len(filtered_args) < 3:
            print("Usage: --size EQUITY CONVICTION [--gear conservative|recommended|aggressive]")
            print("  Example: --size 120000 8")
            print("  Example: --size 200000 5 --gear aggressive")
            sys.exit(1)

        equity = float(filtered_args[1])
        conviction = int(filtered_args[2])
        sizing = calculate_position_size(equity, conviction, gear)

        print(f"\n{'=' * 52}")
        print(f"  POSITION SIZE CALCULATOR")
        print(f"{'=' * 52}")
        print(f"  Portfolio equity:  ${equity:,.0f}")
        print(f"  Conviction score:  {conviction}/10")
        print(f"  Sizing gear:       {gear}")
        print(f"  Tier:              {sizing.get('tier_label', sizing['tier'])}")
        print(f"  Allocation:        {sizing['equity_pct']*100:.0f}% of equity")
        print(f"  Position size:     ${sizing['dollar_amount']:,.0f}")
        print(f"  >> {sizing['action']}")
        print(f"{'=' * 52}")

    elif filtered_args and filtered_args[0] == '--history':
        for ticker in filtered_args[1:]:
            dump_history(ticker.upper())

    else:
        print("=" * 68)
        print("  STERLING GRID — WEEKLY SIGNAL SCAN")
        print(f"  Sizing: {gear} gear (15×6 base)")
        print("=" * 68)

        buy_signals = []
        for ticker in filtered_args:
            result = scan_ticker(ticker.upper())
            if result.get('buy_signal'):
                buy_signals.append(result['ticker'])

        print(f"\n{'=' * 68}")
        if buy_signals:
            print(f"  BUY SIGNALS: {', '.join(buy_signals)}")
            print(f"  -> Send to LLM gate pipeline for conviction scoring")
            print(f"  -> Then run: --size EQUITY CONVICTION to calculate position size")
        else:
            print(f"  No buy signals this week.")
        print(f"{'=' * 68}")
