#!/usr/bin/env python3
"""
STERLING GRID MOMENTUM SCANNER V7 - PURE TECHNICAL SIGNAL DETECTOR (WEEKLY)
============================================================================

Detects weekly momentum entry/exit signals using Sterling Grid V7 indicators.
V7 adds ATR Percentile Rank filter to V6 entry criteria for volatility hole entries.

ENTRY CRITERIA (V7: HMA pivot + OR-gated confirmation, 6-tier):
1. HMA(21) PIVOT LOW — V-bottom: HMA[i-2] > HMA[i-1] < HMA[i]
2. At least ONE confirmation gate:
   a. UC rising (UC > UC.shift(1)) — institutional accumulation  (OR)
   b. MACD(12,26,9) cross-up — timing confirmation (single bar event)
3. ATR squeeze determines tier (does NOT block entry):
   - ATR(14) percentile rank < 20th over 52 weeks → T1-T3 (full sizing)
   - Otherwise → T4-T6 (halved sizing)
QUALITY TIERS (at signal bar):
- T1: UC + MACD + ATR squeeze  → 20% of equity
- T2: MACD only + ATR squeeze  → 10% of equity
- T3: UC only + ATR squeeze    →  5% of equity
- T4: UC + MACD, no squeeze    → 10% of equity
- T5: MACD only, no squeeze    →  5% of equity
- T6: UC only, no squeeze      → 2.5% of equity
Maximum 8 concurrent positions.

EXIT CRITERIA (first exit — whichever fires first):
1. ExD compound exit (HMA PIVOT HIGH + UC falling on same bar) → immediate exit
2. Tiered profit lock:
   - Current return >= +200%: 15% trail from peak
   - Current return >= +100%: 20% trail from peak
   - Current return >= +50%:  25% trail from peak
   - Below +50%: only ExD can trigger exit (no trailing stop)

CONTEXT:
- Pure technical signal detector — no LLM API calls ($0.00 cost)
- Thematic analysis + Investment Gate run in Claude.ai chat (Saturday workflow)
- merge_decisions.py combines chat decisions with signals_technical.json → signals.json

Usage:
    python -m scanner.scanner                    # Full pipeline
    python -m scanner.scanner --no-email         # Skip email notification
    python -m scanner.scanner --top 100          # Only scan top 100 by UC
    python -m scanner.scanner --verbose          # Detailed diagnostics
"""

import os
import sys
import json
import csv
import time
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf

# Import thresholds from centralized config (single source of truth)
from config import (
    HMA_PERIOD,
    MIN_TRADING_DAYS,
    LOCK_TIERS,
)

# Sterling Grid indicators (V8 — bare-pivot entry, tiered_initial_35 exit)
from scanner.sterling_indicators import (
    resample_to_weekly,
    calculate_hma_pivots,
    generate_entry_signal,
    generate_exit_signal,
    check_profit_lock,
    check_tiered_initial_35,
    calculate_position_size as calc_position_size,
)

# yfinance fundamentals + profile enrichment (run only on flagged signals)
from scanner.enrichment import enrich_stock

# Portfolio Manager Integration (unified trade tracking)
from portfolio.manager import (
    PortfolioManager,
    get_portfolio_manager,
    add_trade_to_portfolio,
    check_portfolio_stops,
    get_open_position_symbols,
    update_portfolio_prices
)

# Output paths for weekly folder structure
try:
    from config.output_paths import (
        get_scanner_current_dir as get_current_dir,
        get_scanner_archive_dir as get_week_dir,
        ensure_output_structure,
        get_relative_path,
        SIGNALS_TECH_FILE,
        ANALYSIS_LOG,
        SCANNER_OUTPUT,
        PORTFOLIO_FILE,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False
    _FALLBACK_OUTPUT = Path(__file__).resolve().parent / "output"
    SIGNALS_TECH_FILE = _FALLBACK_OUTPUT / "signals_technical.json"
    ANALYSIS_LOG = _FALLBACK_OUTPUT / "analysis_log.csv"
    SCANNER_OUTPUT = _FALLBACK_OUTPUT
    PORTFOLIO_FILE = Path(__file__).resolve().parent.parent / "portfolio" / "output" / "portfolio.csv"
    # Fallback functions
    def get_current_dir():
        return _FALLBACK_OUTPUT / "current"
    def get_week_dir():
        return _FALLBACK_OUTPUT
    def ensure_output_structure():
        _current = get_current_dir()
        _current.mkdir(parents=True, exist_ok=True)
        return _current, _FALLBACK_OUTPUT
    def get_relative_path(p):
        return str(p)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
TICKERS_FILE = BASE_DIR / "scanner" / "complete_tickers.txt"
LOGS_DIR = BASE_DIR / "logs"

# Ensure output directories exist
SCANNER_OUTPUT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# V7 tier allocation (% of equity per quality tier)
TIER_ALLOC = {"T1": 20, "T2": 10, "T3": 5, "T4": 10, "T5": 5, "T6": 2.5}

# V8 legacy re-anchor: pre-2026 holds are managed discretionarily — flag a sell only on the
# next technical sell signal (HMA pivot high + UC falling) plus a wide disaster backstop.
# (Full per-name re-anchor levels are produced by portfolio_transition.py.)
LEGACY_CUTOFF_DATE = "2026-01-01"
LEGACY_REANCHOR_FLOOR = 0.50   # -50% from entry — wide backstop so a value hold can't bleed to zero


def rel_path(p: Path) -> str:
    """Convert path to relative path for cleaner output."""
    try:
        return str(p.relative_to(Path.cwd()))
    except ValueError:
        return str(p)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Stock:
    symbol: str
    price: float = 0.0
    beta: float = 0.0  # Informational only — no longer an entry gate

    # ── Sterling Grid indicator fields (V6 backtest) ─────────────────────
    # HMA pivot signals (V6 entry/exit triggers)
    hma_value: float = 0.0
    hma_pivot_low: bool = False      # V-bottom: HMA[i-2] > HMA[i-1] < HMA[i]
    hma_pivot_high: bool = False     # V-top: HMA[i-2] < HMA[i-1] > HMA[i]
    hma_slope_rising: bool = False   # Informational (used for watchlist)
    # RSI(14) — computed for display, NOT an entry gate in V6
    rsi14: float = 0.0
    rsi_death_cross_recent: bool = False  # RSI crossed below SMA(14) signal in last 1-2 bars, persistent (legacy-exit condition)
    # MACD timing gate (OR-gated with UC in V6)
    macd_cross_up: bool = False
    macd_line: float = 0.0
    macd_signal_line: float = 0.0
    macd_histogram: float = 0.0
    # Undercurrent (UC) — RSI(10)-based, NOT VWAP
    uc: float = 0.0
    uc_prev: float = 0.0
    uc_rising: bool = False          # V6: UC > UC.shift(1) — no >0 requirement
    uc_falling: bool = False
    # Composite signals
    buy_signal: bool = False         # V8: bare HMA pivot low (gates/ATR squeeze inform tier only)
    exd_signal: bool = False         # V6: HMA pivot high + UC falling
    # Quality tier (V6: determined by which gates active at signal bar)
    quality_tier: int = 0            # 0=no signal, 1=T1 (both), 2=T2 (MACD), 3=T3 (UC)
    # ATR squeeze (V7 entry filter)
    atr: float = 0.0
    atr_rank: float = 0.0
    atr_squeeze: bool = False        # V7: ATR(14) percentile rank < 20 over 52 weeks
    buy_signal_v6: bool = False      # V6 signal (without ATR filter) for diagnostics
    # Week date from data
    week_date: str = ""

    # ── Computed fields ────────────────────────────────────────────────────
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""

    # ── yfinance enrichment (populated only for flagged signals, post-scan) ──
    enrichment: dict = field(default_factory=dict)

    def meets_technical_criteria(self) -> bool:
        """Check if stock meets Sterling Grid V7 technical entry criteria.

        V7 entry: HMA(21) pivot low AND (UC rising OR MACD cross-up)
        ATR squeeze determines tier (T1-T3 vs T4-T6), not eligibility.
        """
        return self.buy_signal

    def get_tier(self) -> str:
        """Return quality tier label based on gates + ATR squeeze status.

        V7 6-tier system:
        T1: UC rising AND MACD cross-up + ATR squeeze  (20%)
        T2: MACD cross-up only + ATR squeeze            (10%)
        T3: UC rising only + ATR squeeze                (5%)
        T4: UC rising AND MACD cross-up, no squeeze     (10%)
        T5: MACD cross-up only, no squeeze              (5%)
        T6: UC rising only, no squeeze                  (2.5%)
        """
        if not self.meets_technical_criteria():
            return ""
        tier_map = {1: 'T1', 2: 'T2', 3: 'T3', 4: 'T4', 5: 'T5', 6: 'T6'}
        if self.quality_tier in tier_map:
            return tier_map[self.quality_tier]
        # Fallback: classify from indicator state + ATR squeeze
        if self.uc_rising and self.macd_cross_up:
            self.quality_tier = 1 if self.atr_squeeze else 4
        elif self.macd_cross_up:
            self.quality_tier = 2 if self.atr_squeeze else 5
        elif self.uc_rising:
            self.quality_tier = 3 if self.atr_squeeze else 6
        else:
            self.quality_tier = 6
        return tier_map.get(self.quality_tier, 'T6')


@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    # Sterling Grid V6 indicator stats
    hma_pivot_low: int = 0         # HMA(21) V-bottom pivot (V6 entry trigger)
    hma_slope_rising: int = 0      # HMA(21) slope rising (informational)
    macd_cross_up: int = 0         # MACD single-bar cross-up
    uc_rising: int = 0             # V6: UC > UC.shift(1) (no >0 req)
    buy_signal: int = 0            # V7: pivot + (UC OR MACD) + ATR squeeze
    buy_signal_v6: int = 0         # V6: pivot + (UC OR MACD) without ATR filter
    exd_exit: int = 0              # V6 ExD (HMA pivot high + UC falling) — retained for JSON only
    hma_pivot_high: int = 0        # V8.1 HMA exit: bare HMA(21) V-top pivot ("HMA down")
    atr_squeeze: int = 0           # V7: ATR percentile rank < 20
    # Quality tier counts
    tier_t1: int = 0               # Both gates + ATR squeeze
    tier_t2: int = 0               # MACD only + ATR squeeze
    tier_t3: int = 0               # UC only + ATR squeeze
    tier_t4: int = 0               # Both gates, no ATR squeeze
    tier_t5: int = 0               # MACD only, no ATR squeeze
    tier_t6: int = 0               # UC only, no ATR squeeze
    # Aggregate
    meets_technical_gate: int = 0
    technical_signals: int = 0     # Stocks passing full technical gate (buy_signal)


@dataclass
class PipelineCostTracker:
    """Track timing across the full pipeline."""
    step_times: dict = field(default_factory=dict)  # step_name -> seconds
    _current_step: str = ""
    _step_start: float = 0.0

    def start(self, step_name: str):
        """Mark the start of a pipeline step."""
        self._current_step = step_name
        self._step_start = time.time()

    def stop(self):
        """Mark the end of the current step."""
        if self._current_step and self._step_start > 0:
            elapsed = time.time() - self._step_start
            self.step_times[self._current_step] = self.step_times.get(self._current_step, 0) + elapsed
            self._current_step = ""
            self._step_start = 0.0

    def print_summary(self):
        """Print pipeline timing summary."""
        if not self.step_times:
            return
        total = sum(self.step_times.values())
        print(f"\n  " + "═" * 66)
        print(f"  PIPELINE TIMING SUMMARY")
        print(f"  " + "─" * 66)
        for step, secs in self.step_times.items():
            pct = (secs / total * 100) if total > 0 else 0
            mins = secs / 60
            print(f"    {step:<30} {mins:>5.1f}m  ({pct:>4.1f}%)")
        print(f"  " + "─" * 66)
        total_mins = total / 60
        print(f"    {'TOTAL':<30} {total_mins:>5.1f}m")
        print(f"  " + "═" * 66)


# ═══════════════════════════════════════════════════════════════════════════════
# TICKER LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def load_tickers() -> List[str]:
    """Load tickers from complete_tickers.txt."""
    if not TICKERS_FILE.exists():
        print(f"  ✗ File not found: {TICKERS_FILE}")
        print(f"  Create complete_tickers.txt with one ticker per line")
        return []

    tickers = set()
    with open(TICKERS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.replace(',', ' ').replace('\t', ' ').split()
            for part in parts:
                ticker = part.strip().strip('"\'').upper()
                if ticker in ['TICKER', 'SYMBOL', 'NAME', 'COMPANY', '']:
                    continue
                if 1 <= len(ticker) <= 6 and any(c.isalpha() for c in ticker):
                    if all(c.isalnum() or c in '-.' for c in ticker):
                        tickers.add(ticker)

    return sorted(list(tickers))


# ═══════════════════════════════════════════════════════════════════════════════
# INDICATOR CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate beta vs benchmark."""
    try:
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < MIN_TRADING_DAYS:
            return 0.0
        aligned.columns = ['stock', 'bench']
        cov = aligned['stock'].cov(aligned['bench'])
        var = aligned['bench'].var()
        if var == 0 or pd.isna(var):
            return 0.0
        beta = cov / var
        return round(float(beta), 2) if not pd.isna(beta) else 0.0
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD & PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def download_and_process(tickers: List[str], benchmark_returns: pd.Series) -> Dict[str, Stock]:
    """Download data and calculate Sterling Grid V6 indicators for all tickers.

    For each ticker:
    1. Resample daily → weekly
    2. Calculate V6 entry conditions via generate_entry_signal()
       (HMA pivot + OR-gated UC/MACD + quality tier classification)
    4. Calculate V6 exit conditions via generate_exit_signal()
       (HMA pivot high + UC falling)
    5. Beta calculated for informational display (not a gate)
    """
    stocks = {}
    chunk_size = 50
    chunks = [tickers[i:i+chunk_size] for i in range(0, len(tickers), chunk_size)]
    failed_downloads = []

    import io
    import contextlib

    for i, chunk in enumerate(chunks):
        pct = (i + 1) / len(chunks) * 100
        print(f"\r  Downloading: {pct:3.0f}% ({i+1}/{len(chunks)} chunks)", end="", flush=True)

        try:
            with contextlib.redirect_stderr(io.StringIO()):
                data = yf.download(chunk, period="2y", progress=False, threads=True, group_by='ticker')

            if data.empty:
                failed_downloads.extend(chunk)
                continue

            for symbol in chunk:
                try:
                    if len(chunk) == 1:
                        df = data.copy()
                    else:
                        if symbol not in data.columns.get_level_values(0):
                            continue
                        df = data[symbol].copy()

                    if 'Close' not in df.columns:
                        continue

                    df = df.dropna(subset=['Close'])
                    if len(df) < 60:
                        continue

                    stock = Stock(symbol=symbol)
                    stock.price = round(float(df['Close'].iloc[-1]), 2)

                    if len(df) >= 20:
                        stock.return_20d = round((df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100, 1)

                    # Beta (informational — no longer an entry gate)
                    returns = df['Close'].pct_change().dropna()
                    stock.beta = calculate_beta(returns, benchmark_returns)

                    # Sterling Grid indicators (weekly timeframe)
                    try:
                        weekly = resample_to_weekly(df)

                        if len(weekly) >= HMA_PERIOD + 10:
                            # Entry signal (V6: pivot + OR-gated)
                            entry_data = generate_entry_signal(weekly)
                            cur = entry_data.iloc[-1]

                            stock.hma_value = round(float(cur['hma']), 4) if pd.notna(cur['hma']) else 0.0
                            stock.hma_pivot_low = bool(cur['hma_pivot_low'])
                            stock.hma_pivot_high = bool(cur['hma_pivot_high'])
                            stock.hma_slope_rising = bool(cur['hma_slope_rising'])
                            stock.rsi14 = round(float(cur['rsi14']), 1) if pd.notna(cur['rsi14']) else 0.0
                            stock.macd_cross_up = bool(cur['macd_cross_up'])
                            stock.macd_line = round(float(cur['macd_line']), 4) if pd.notna(cur['macd_line']) else 0.0
                            stock.macd_signal_line = round(float(cur['signal_line']), 4) if pd.notna(cur['signal_line']) else 0.0
                            stock.macd_histogram = round(float(cur['macd_histogram']), 4) if pd.notna(cur['macd_histogram']) else 0.0
                            stock.uc = round(float(cur['uc']), 2) if pd.notna(cur['uc']) else 0.0
                            stock.uc_rising = bool(cur['uc_rising'])
                            stock.buy_signal = bool(cur['buy_signal'])
                            stock.quality_tier = int(cur['quality_tier']) if pd.notna(cur['quality_tier']) else 0

                            # ATR squeeze (V7 entry filter)
                            stock.atr = round(float(cur['atr']), 4) if pd.notna(cur.get('atr', None)) else 0.0
                            stock.atr_rank = round(float(cur['atr_rank']), 1) if pd.notna(cur.get('atr_rank', None)) else 0.0
                            stock.atr_squeeze = bool(cur.get('atr_squeeze', False))
                            stock.buy_signal_v6 = bool(cur.get('buy_signal_v6', False))

                            # Exit signal (V6 ExD: HMA pivot high + UC falling)
                            exit_data = generate_exit_signal(weekly)
                            cur_exit = exit_data.iloc[-1]

                            stock.uc_falling = bool(cur_exit['uc_falling'])
                            stock.exd_signal = bool(cur_exit['exd_signal'])
                            stock.rsi_death_cross_recent = bool(cur_exit['rsi_death_cross_recent'])
                            stock.uc_prev = round(float(exit_data['uc'].iloc[-2]), 2) if len(exit_data) > 1 and pd.notna(exit_data['uc'].iloc[-2]) else 0.0

                            stock.week_date = str(weekly.index[-1].date())
                            stock.tier = stock.get_tier()

                            # 4-week momentum (informational)
                            if len(weekly) >= 5:
                                close_now = float(weekly['close'].iloc[-1])
                                close_4w_ago = float(weekly['close'].iloc[-5])
                                stock.momentum_4w = round((close_now / close_4w_ago - 1) * 100, 1)
                    except Exception:
                        pass  # Keep stock with partial data

                    stocks[symbol] = stock

                except Exception:
                    continue

        except Exception:
            failed_downloads.extend(chunk)
            continue

        time.sleep(0.3)

    print(f"\r  ✓ Data for {len(stocks)} stocks" + " " * 30)
    if failed_downloads:
        print(f"  ⚠ {len(failed_downloads)} ticker(s) failed to download")

    return stocks


# ═══════════════════════════════════════════════════════════════════════════════
# SELL SIGNAL CHECKER & POSITION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SellSignal:
    symbol: str
    price: float
    reason: str
    entry_price: float = 0.0
    highest_close: float = 0.0
    drawdown_pct: float = 0.0


def _position_exit_rule(trade) -> str:
    """Return the exit rule for an open position.

    'legacy_reanchor' for holds entered before LEGACY_CUTOFF_DATE (pre-2026) — these are
    managed discretionarily (wait for the next technical sell signal + a wide backstop).
    'tiered_initial_35' for everything else (the V8 default).

    Defensive: any parsing issue falls back to the V8 rule, so a missing/oddly-typed
    entry_date can never crash the weekly sell check.
    """
    try:
        ed = getattr(trade, 'entry_date', None)
        if ed is not None:
            ds = str(ed)[:10]
            parts = ds.split('-')
            if len(parts) >= 3:
                from datetime import date
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                cy, cm, cd = (int(x) for x in LEGACY_CUTOFF_DATE.split('-'))
                if date(y, m, d) < date(cy, cm, cd):
                    return 'legacy_reanchor'
    except Exception:
        pass
    return 'tiered_initial_35'


def check_sell_signals(stocks: Dict[str, Stock]) -> List[SellSignal]:
    """
    Check for sell signals on open positions using Sterling Grid V8.1 exit rules.

    ALL positions flag a sell on an HMA exit — the HMA pivot high ("HMA down" rollover),
    bare (no UC-falling condition; this is no longer the old ExD compound).

    On top of that, capital protection differs by position age:
      NEW positions (entry >= 2026-01-01) → tiered trailing lock for runners
         (+200%→15%, +100%→20%, +50%→25%) with a -35%-from-entry floor while gain < +50%.
      LEGACY holds (entry < 2026-01-01) → a wide -50%-from-entry disaster backstop only
         (discretionary value holds: wait for the HMA exit, don't let them bleed to zero).
    So the effective exit is "HMA down OR tiered lock/floor", whichever fires first.
    ExD is no longer used. Decided on the weekly close; execute at next candle open.
    """
    pm = get_portfolio_manager()
    sell_signals = []

    try:
        open_trades = pm.get_open_positions()

        if not open_trades:
            return []

        for trade in open_trades:
            symbol = trade.ticker.upper()

            if symbol not in stocks:
                continue

            stock = stocks[symbol]
            current_price = stock.price

            # Update highest close
            if current_price > trade.highest_close:
                trade.highest_close = current_price

            # Calculate drawdown for display
            if trade.highest_close > 0:
                drawdown_pct = ((trade.highest_close - current_price) / trade.highest_close) * 100
            else:
                drawdown_pct = 0

            # CHECK EXIT CRITERIA — the exit rule is POSITION-DEPENDENT.
            #   • New positions ride the tiered trailing lock ALONE. No HMA-down: round-trip
            #     backtests show the HMA pivot-high almost always fires before the lock engages,
            #     pre-empting it and clipping the multibaggers the lock exists to capture
            #     (tiered ≈ +89% expectancy / 17% hit-3x vs HMA-down ≈ +4% / 0%).
            #   • Legacy holds (pre-2026, phasing out) exit on a CONDITIONED HMA-down — pivot-high
            #     gated on a recent persistent RSI death cross — plus a wide -50% disaster floor.
            # Decided on the weekly close; act at next candle open.
            exit_reasons = []

            rule = _position_exit_rule(trade)
            if rule == 'legacy_reanchor':
                # Pre-2026 discretionary holds, phasing out. Sell into the rollover, but only when
                # momentum confirms it: HMA pivot-high AND a recent, persistent RSI death cross (RSI
                # crossed below its SMA(14) signal on the prior bar or the one before, and stayed
                # below since). Conditioning the HMA-down on the RSI rollover fires ~40% less than
                # bare HMA-down, clipping far fewer winners (~2x the risk-adjusted return in
                # backtesting) while still giving a clean discrete exit to retire the position. A
                # wide -50%-from-entry backstop stops a value hold bleeding to zero while we wait.
                if stock.hma_pivot_high and stock.rsi_death_cross_recent:
                    exit_reasons.append("Legacy HMA exit (HMA pivot high + recent RSI death cross)")
                backstop = trade.entry_price * (1 - LEGACY_REANCHOR_FLOOR)
                if trade.entry_price > 0 and current_price <= backstop:
                    exit_reasons.append(
                        f"disaster backstop (<= ${backstop:.2f}, "
                        f"-{int(LEGACY_REANCHOR_FLOOR*100)}% from entry)"
                    )
            else:
                # New positions: tiered trailing lock ONLY (+200%→15%, +100%→20%, +50%→25%), with a
                # -35%-from-entry floor while gain < +50%. No HMA-down — runners ride the lock.
                exit_result = check_tiered_initial_35(trade.entry_price, current_price, trade.highest_close)
                if exit_result.get('triggered', False):
                    exit_reasons.append(exit_result.get('active_tier', 'tiered lock'))

            if exit_reasons:
                sell_reason = " + ".join(exit_reasons)
                sell_signals.append(SellSignal(
                    symbol=symbol,
                    price=current_price,
                    reason=sell_reason,
                    entry_price=trade.entry_price,
                    highest_close=trade.highest_close,
                    drawdown_pct=drawdown_pct
                ))
                pm.flag_exit(symbol, current_price, reason=sell_reason)
                print(f"    ✗ {symbol}: EXIT at ${current_price:.2f} — {sell_reason}")

        return sell_signals

    except Exception as e:
        print(f"  ⚠ Error checking sell signals: {e}")
        import traceback
        traceback.print_exc()
        return []


def add_to_open_positions(stock: Stock):
    """Add a confirmed trade to open positions for tracking via PortfolioManager."""
    add_trade_to_portfolio(stock)


def load_open_positions() -> set:
    """Load symbols from open positions for flagging in scanner output."""
    try:
        return get_open_position_symbols()
    except Exception:
        return set()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level pipeline cost tracker
_pipeline_timer = PipelineCostTracker()

def run_scan(top_n: int = 0, verbose: bool = False) -> Tuple[List[Stock], List[SellSignal], ScanStats, Dict[str, Stock]]:
    """Run the complete scan pipeline (pure technical — no LLM gates).

    Returns (technical_signals, sell_signals, stats, stocks).

    Args:
        top_n: Only scan top N stocks by UC (0 = all)
        verbose: Show detailed diagnostic output (10 items vs 3)
    """

    stats = ScanStats()
    _pipeline_timer.step_times.clear()  # Reset for new scan

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Load Tickers
    # ─────────────────────────────────────────────────────────────────────────
    _pipeline_timer.start("Steps 1-5: Data & Technical")
    print("\n" + "─" * 70)
    print("  STEP 1: Loading Tickers")
    print("─" * 70)

    tickers = load_tickers()
    stats.tickers_loaded = len(tickers)

    if not tickers:
        print("  ✗ No tickers loaded")
        return [], [], stats

    print(f"  ✓ Loaded {len(tickers)} tickers from complete_tickers.txt")

    # Load open positions to flag existing holdings in output
    open_positions = load_open_positions()
    if open_positions:
        print(f"  ✓ Tracking {len(open_positions)} open position(s): {', '.join(sorted(open_positions))}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Download Benchmark
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 2: Downloading SPY Benchmark")
    print("─" * 70)

    try:
        spy = yf.download("SPY", period="2y", progress=False)
        if spy.empty:
            print("  ✗ Failed to download SPY")
            return [], [], stats

        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        if 'Close' not in spy.columns:
            print("  ✗ SPY data missing 'Close' column after download")
            return [], [], stats

        benchmark_returns = spy['Close'].pct_change().dropna()
        print(f"  ✓ SPY data: {len(benchmark_returns)} days")
    except Exception as e:
        print(f"  ✗ Benchmark error: {e}")
        return [], [], stats

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Download Data & Calculate Indicators
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 3: Downloading Data & Calculating Indicators (Sterling Grid)")
    print("─" * 70)

    try:
        stocks = download_and_process(tickers, benchmark_returns)
        stats.data_downloaded = len(stocks)

        # Validate we got a reasonable amount of data
        expected_count = len(tickers)
        if len(stocks) < expected_count * 0.3:
            print(f"  ⚠️ WARNING: Only {len(stocks)}/{expected_count} tickers downloaded ({len(stocks)/expected_count*100:.1f}%)")
            print(f"     This may indicate yfinance API issues")
    except Exception as e:
        print(f"  ❌ ERROR: Data download failed: {e}")
        print(f"     Cannot continue without stock data")
        return [], [], stats

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Calculate Statistics (Sterling Grid indicators)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 4: Sterling Grid Indicator Statistics")
    print("─" * 70)

    # Count Sterling Grid V6 indicator stats
    eligible_stocks = list(stocks.values())

    for stock in stocks.values():
        if stock.hma_pivot_low:
            stats.hma_pivot_low += 1
        if stock.hma_slope_rising:
            stats.hma_slope_rising += 1
        if stock.macd_cross_up:
            stats.macd_cross_up += 1
        if stock.uc_rising:
            stats.uc_rising += 1
        if stock.atr_squeeze:
            stats.atr_squeeze += 1
        if stock.buy_signal_v6:
            stats.buy_signal_v6 += 1
        if stock.buy_signal:
            stats.buy_signal += 1
            # Count by quality tier
            if stock.quality_tier == 1:
                stats.tier_t1 += 1
            elif stock.quality_tier == 2:
                stats.tier_t2 += 1
            elif stock.quality_tier == 3:
                stats.tier_t3 += 1
            elif stock.quality_tier == 4:
                stats.tier_t4 += 1
            elif stock.quality_tier == 5:
                stats.tier_t5 += 1
            elif stock.quality_tier == 6:
                stats.tier_t6 += 1
        if stock.exd_signal:
            stats.exd_exit += 1
        if stock.hma_pivot_high:
            stats.hma_pivot_high += 1

    # Sort eligible stocks by UC (strongest accumulation first)
    eligible_stocks.sort(key=lambda x: -x.uc)

    if top_n and len(eligible_stocks) > top_n:
        eligible_stocks = eligible_stocks[:top_n]
        print(f"  (Limited to top {top_n} by UC)")

    print(f"\n  STERLING GRID V8.1 FILTER RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Total tickers scanned:    {stats.tickers_loaded:>6}")
    print(f"  Data downloaded:          {stats.data_downloaded:>6}")
    if verbose:
        # Component diagnostics (informational — none of these gate entry in V8)
        print(f"  HMA slope rising:         {stats.hma_slope_rising:>6}  (informational)")
        print(f"  MACD cross-up:            {stats.macd_cross_up:>6}  (informational)")
        print(f"  UC rising:                {stats.uc_rising:>6}  (informational)")
        print(f"  ATR squeeze:              {stats.atr_squeeze:>6}  (informational)")
        print(f"  ────────────────────────────────────")
        print(f"  HMA entries (pivot low):  {stats.hma_pivot_low:>6}  ← bare HMA pivot up = buy signal")
        print(f"  HMA exits (pivot high):   {stats.hma_pivot_high:>6}  ← HMA pivot down = sell flag")
    else:
        # Marketing-safe terminology
        print(f"  Structural pivot:         {stats.hma_pivot_low:>6}")
        print(f"  Timing confirmed:         {stats.macd_cross_up:>6}")
        print(f"  Accumulation rising:      {stats.uc_rising:>6}")
        print(f"  Volatility squeeze (V7):  {stats.atr_squeeze:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  HMA entries (pivot up):   {stats.hma_pivot_low:>6}")
        print(f"  HMA exits (pivot down):   {stats.hma_pivot_high:>6}")

    # ═══════════════════════════════════════════════════════════════════════════
    # DIAGNOSTIC: Show sample tickers (controlled by --verbose flag)
    # ═══════════════════════════════════════════════════════════════════════════
    sample_size = 10 if verbose else 3

    # Get week ending date from any stock that has it
    week_date = "N/A"
    for s in stocks.values():
        if s.week_date:
            week_date = s.week_date
            break

    print(f"\n  📅 Week ending: {week_date}")

    if verbose:
        print(f"\n  ┌─────────────────────────────────────────────────────────────────┐")
        print(f"  │  DIAGNOSTIC: Sample Tickers (--verbose mode)                    │")
        print(f"  └─────────────────────────────────────────────────────────────────┘")

    # Buy signals (V8: bare HMA pivot up)
    buy_signal_stocks = [s for s in stocks.values() if s.buy_signal]
    if verbose:
        print(f"\n  🟢 HMA ENTRIES (bare HMA pivot up): {len(buy_signal_stocks)}")
    else:
        print(f"\n  🟢 HMA ENTRIES: {len(buy_signal_stocks)}")
    if buy_signal_stocks and verbose:
        for s in sorted(buy_signal_stocks, key=lambda x: -x.uc)[:sample_size]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            squeeze_flag = "SQ" if s.atr_squeeze else "--"
            print(f"      {s.symbol:<6} ${s.price:<8.2f} UC={s.uc:.1f} RSI={s.rsi14:.0f} ATR={s.atr_rank:.0f}%[{squeeze_flag}] HMA={'⌄' if s.hma_pivot_low else '↑' if s.hma_slope_rising else '↓'}{held_flag}")

    # HMA exits (bare HMA pivot high / "HMA down")
    hma_exit_stocks = [s for s in stocks.values() if s.hma_pivot_high]
    if verbose:
        print(f"  🔴 HMA EXITS (HMA pivot high / HMA down): {len(hma_exit_stocks)}")
    else:
        print(f"  🔴 HMA EXITS: {len(hma_exit_stocks)} (sell flag on open positions)")
    if hma_exit_stocks and verbose:
        for s in hma_exit_stocks[:sample_size]:
            print(f"      {s.symbol:<6} ${s.price:<8.2f} UC={s.uc:.1f} HMA={'⌃' if s.hma_pivot_high else '↓'}")

    # Entry candidates with buy signal
    buy_candidates = [s for s in eligible_stocks if s.buy_signal]
    print(f"\n  ⭐ ENTRY CANDIDATES (HMA pivot up): {len(buy_candidates)}")
    if buy_candidates:
        for s in sorted(buy_candidates, key=lambda x: -x.uc)[:sample_size]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"      {s.symbol:<6} ${s.price:<8.2f} UC={s.uc:.1f} RSI={s.rsi14:.0f} MACD={'✓' if s.macd_cross_up else '✗'} ATR={s.atr_rank:.0f}%{held_flag}")

    if not verbose:
        print(f"\n  💡 Use --verbose for detailed diagnostics")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Apply Sterling Grid Technical Gates
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 5: Applying Sterling Grid Technical Gates")
    print("─" * 70)
    print(f"\n  📊 Entry (V8): bare HMA pivot up — fire wide (no UC/MACD/ATR gate); LLM selects")

    technical_signals = []

    for stock in eligible_stocks:
        if stock.meets_technical_criteria():
            stats.meets_technical_gate += 1
            stock.tier = stock.get_tier()
            if stock.tier:
                technical_signals.append(stock)
                stats.technical_signals += 1

    print(f"\n  STERLING GRID V8.1 GATE RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Eligible stocks:           {len(eligible_stocks):>5}")
    print(f"  HMA entries (pivot up):    {stats.meets_technical_gate:>5}")
    print(f"  ATR squeeze (sizing nudge):{stats.atr_squeeze:>5}")
    print(f"  ────────────────────────────────────")
    print(f"  TECHNICAL SIGNALS:         {stats.technical_signals:>5}")
    print(f"  ────────────────────────────────────")

    if technical_signals:
        print(f"\n  ✅ HMA ENTRY SIGNALS:")
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            squeeze_flag = "SQ" if s.atr_squeeze else "--"
            print(f"    {s.symbol:<6} ${s.price:>8.2f}  UC={s.uc:.1f}  RSI={s.rsi14:.0f}  MACD={'✓' if s.macd_cross_up else '✗'}  ATR={s.atr_rank:.0f}%[{squeeze_flag}]  HMA={'⌄' if s.hma_pivot_low else '↑'}{held_flag}")

    if not technical_signals:
        print("\n  No technical signals to process")
        sell_signals = check_sell_signals(stocks)
        return [], sell_signals, stats

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5b: Enrich signals (yfinance fundamentals + profile)
    # Only the flagged signals are enriched — fundamentals need per-ticker
    # yf.Ticker calls (slow/flaky), so we never run them across the full universe.
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 5b: Enriching Signals (yfinance fundamentals + profile)")
    print("─" * 70)

    for i, stock in enumerate(technical_signals, 1):
        print(f"\r  Enriching: {i}/{len(technical_signals)} ({stock.symbol})    ", end="", flush=True)
        try:
            stock.enrichment = enrich_stock(stock.symbol)
        except Exception as e:
            stock.enrichment = {"data_warnings": [f"enrich_error: {type(e).__name__}: {e}"]}
        time.sleep(0.3)  # be gentle on Yahoo

    low_conf = sum(1 for s in technical_signals
                   if s.enrichment.get("profile_confidence") == "low")
    liq_fail = sum(1 for s in technical_signals
                   if "liquidity_fail" in s.enrichment.get("hard_disqualifiers", []))
    print(f"\r  ✓ Enriched {len(technical_signals)} signal(s)" + " " * 24)
    if low_conf:
        print(f"  ⚠ {low_conf} low-confidence profile (generic/missing sector — use business_summary)")
    if liq_fail:
        print(f"  ⚠ {liq_fail} flagged liquidity_fail (below tradable avg $ volume)")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Technical signals ready (LLM gates → Claude.ai chat)
    # ─────────────────────────────────────────────────────────────────────────
    _pipeline_timer.stop()  # Stop Steps 1-5 timing

    # Show candidates summary
    print(f"\n  📊 ENTRY CANDIDATES: {len(technical_signals)} passed technical filters")
    sorted_signals = sorted(technical_signals, key=lambda x: -x.uc)
    for s in sorted_signals[:5]:
        held_flag = " [HELD]" if s.symbol in open_positions else ""
        print(f"     {s.symbol:<6} | UC={s.uc:.1f} | RSI={s.rsi14:.0f} | MACD={'✓' if s.macd_cross_up else '✗'} | ATR={s.atr_rank:.0f}% | 20d={s.return_20d:+.1f}%{held_flag}")
    if len(sorted_signals) > 5:
        print(f"     ... and {len(sorted_signals) - 5} more")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Check Sell Signals (HMA exit OR tiered lock / disaster floor)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 7: Checking Sell Signals (V8.1 HMA exit OR tiered lock | legacy = HMA exit + backstop)")
    print("─" * 70)

    sell_signals = check_sell_signals(stocks)

    if sell_signals:
        print(f"  ⚠ {len(sell_signals)} SELL SIGNAL(S):")
        for s in sell_signals:
            print(f"    🔴 {s.symbol} @ ${s.price:.2f} - {s.reason}")
    else:
        print(f"  ✓ No sell signals")

    # NOTE: Portfolio updates now happen AFTER review in Claude.ai chat

    return technical_signals, sell_signals, stats, stocks


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt_money(x) -> str:
    """Compact dollar formatting: $16.4B, $470M, $202K, n/a."""
    if not isinstance(x, (int, float)):
        return "n/a"
    ax = abs(x)
    if ax >= 1e9:
        return f"${x/1e9:.1f}B"
    if ax >= 1e6:
        return f"${x/1e6:.0f}M"
    if ax >= 1e3:
        return f"${x/1e3:.0f}K"
    return f"${x:,.0f}"


def _fmt_pct(x) -> str:
    """Signed percent from a fraction: +8%, -63%, n/a."""
    if not isinstance(x, (int, float)):
        return "n/a"
    return f"{x*100:+.0f}%"


def _fundamentals_table(technical_signals: List[Stock]) -> List[str]:
    """Build fundamentals table lines from each signal's enrichment dict.

    Shared by the terminal report and the archived/email report so both stay
    in sync. Enrichment is populated in STEP 5b; missing values render as n/a.
    """
    lines = []
    lines.append(
        f"  {'SYMBOL':<7} {'COMPANY':<22} {'SECTOR':<18} {'MKTCAP':>8} "
        f"{'REVYoY':>7} {'GRMGN':>7} {'CASH':>8} {'RUNWAY':>7} {'DILUT':>7} {'FLAGS':<22}"
    )
    lines.append("  " + "-" * 116)
    # Tier ascending (T1 highest conviction first), then strongest accumulation
    for s in sorted(technical_signals, key=lambda x: (x.tier, -x.uc)):
        e = s.enrichment or {}
        company = (e.get("company") or "")[:20]
        sector = (e.get("sector") or "")[:16]
        mc = _fmt_money(e.get("market_cap"))
        rev = _fmt_pct(e.get("revenue_yoy_growth"))
        gm = _fmt_pct(e.get("gross_margin"))
        cash = _fmt_money(e.get("cash_st"))
        runway = e.get("runway_months")
        rw = f"{runway:.0f}m" if isinstance(runway, (int, float)) else "n/a"
        dil = _fmt_pct(e.get("dilution_yoy"))
        flags = list(e.get("hard_disqualifiers", [])) + list(e.get("risk_flags", []))
        if e.get("data_warnings"):
            flags.append("fetch_err")
        flag_str = (",".join(flags))[:20] if flags else "-"
        lines.append(
            f"  {s.symbol:<7} {company:<22} {sector:<18} {mc:>8} "
            f"{rev:>7} {gm:>7} {cash:>8} {rw:>7} {dil:>7} {flag_str:<22}"
        )
    return lines


def print_final_report(technical_signals: List[Stock], sell_signals: List[SellSignal], stats: ScanStats):
    """Print final summary report."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "FINAL REPORT".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if technical_signals:
        print(f"\n  ⭐ ENTRY CANDIDATES ({len(technical_signals)}) — pending Claude.ai analysis:")
        print("  " + "─" * 66)
        print(f"  {'SYMBOL':<7} {'PRICE':>8} {'UC':>6} {'RSI':>5} {'MACD':>5} {'ATR%':>5} {'20D':>7}")
        print("  " + "-" * 55)
        for s in sorted(technical_signals, key=lambda x: (-1 if x.atr_squeeze else 0, -x.uc)):
            macd = "✓" if s.macd_cross_up else "✗"
            atr_str = f"{s.atr_rank:.0f}" if s.atr_rank else "--"
            print(f"  {s.symbol:<7} ${s.price:>7.2f} {s.uc:>5.1f} {s.rsi14:>5.0f} {macd:>5} {atr_str:>5} {s.return_20d:>+6.1f}%")

        # Total allocation summary
        total_alloc = sum(TIER_ALLOC.get(s.tier, 0) for s in technical_signals)
        if total_alloc:
            print(f"\n    💰 Potential equity deployment: {total_alloc:.1f}% (pending analysis)")

        # Fundamentals (from STEP 5b enrichment) — profile + financials per signal
        print(f"\n  📑 FUNDAMENTALS (yfinance enrichment):")
        print("  " + "─" * 116)
        for line in _fundamentals_table(technical_signals):
            print(line)
    else:
        print("\n  NO TECHNICAL ENTRY SIGNALS")
        print(f"\n  Pipeline summary:")
        print(f"    • {stats.tickers_loaded} tickers scanned")
        print(f"    • {stats.buy_signal} HMA entries (bare pivot up)")
        print(f"    • {stats.technical_signals} met technical gate")

    if sell_signals:
        print(f"\n  🔴 EXIT SIGNALS ({len(sell_signals)}) - Positions Closed:")
        print("  " + "─" * 66)
        for s in sell_signals:
            print(f"\n  🔴 {s.symbol} @ ${s.price:.2f}")
            print(f"     Reason: {s.reason}")
            if s.entry_price > 0:
                pnl = ((s.price / s.entry_price) - 1) * 100
                print(f"     Entry: ${s.entry_price:.2f} | High: ${s.highest_close:.2f} | P&L: {pnl:+.1f}%")
            print(f"     Position closed — first exit triggered")

    print(f"\n  " + "═" * 66)
    print(f"  EXIT STRATEGY (V8.1 — decide on weekly close, act next candle open):")
    print(f"    • HMA exit: HMA pivot high (HMA down) — flagged for every position, runners included")
    print(f"    • Runners: tiered trailing lock (+200%→15%, +100%→20%, +50%→25% from peak)")
    print(f"    • New positions: -35%-from-entry floor while gain < +50%")
    print(f"    • Legacy holds (pre-2026): HMA exit + -50% disaster backstop")
    print("  " + "═" * 66)


def generate_report(technical_signals: List[Stock], sell_signals: List[SellSignal],
                   stats: ScanStats) -> str:
    """Generate scan summary report for email notification and archival."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_display = datetime.now().strftime("%A, %B %d, %Y")

    lines = []
    lines.append("=" * 72)
    lines.append(f"  STERLING GRID V8.1 — WEEKLY SCAN REPORT")
    lines.append(f"  {date_display}")
    lines.append(f"  Generated: {timestamp}")
    lines.append("=" * 72)

    # Scan funnel
    lines.append("")
    lines.append(f"  Tickers scanned:     {stats.tickers_loaded:>6}")
    lines.append(f"  Data downloaded:     {stats.data_downloaded:>6}")
    lines.append(f"  ATR squeeze:         {stats.atr_squeeze:>6}  (sizing nudge)")
    lines.append(f"  HMA entries (up):    {stats.hma_pivot_low:>6}  ← bare HMA pivot up = buy signal")
    lines.append(f"  HMA exits (down):    {stats.hma_pivot_high:>6}  ← HMA pivot high = sell flag")

    # Entry candidates
    if technical_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ENTRY CANDIDATES (pending Claude.ai analysis)")
        lines.append("─" * 72)
        lines.append(f"  {'SYMBOL':<7} {'PRICE':>8} {'UC':>6} {'RSI':>5} {'MACD':>5} {'20D':>7}")
        lines.append("  " + "-" * 50)
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            macd = "✓" if s.macd_cross_up else "✗"
            lines.append(f"  {s.symbol:<7} ${s.price:>7.2f} {s.uc:>5.1f} {s.rsi14:>5.0f} {macd:>5} {s.return_20d:>+6.1f}%")

        # Fundamentals (from STEP 5b enrichment)
        lines.append("")
        lines.append("─" * 72)
        lines.append("  FUNDAMENTALS (yfinance enrichment)")
        lines.append("─" * 72)
        lines.extend(_fundamentals_table(technical_signals))
    else:
        lines.append("")
        lines.append("  No technical entry signals this week.")

    # Exit signals
    if sell_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  EXIT SIGNALS")
        lines.append("─" * 72)
        for s in sell_signals:
            pnl = ((s.price / s.entry_price) - 1) * 100 if s.entry_price > 0 else 0
            lines.append(f"  🔴 {s.symbol} @ ${s.price:.2f} | {s.reason} | P&L: {pnl:+.1f}%")

    # Next steps
    lines.append("")
    lines.append("─" * 72)
    lines.append("  NEXT: Review signals_technical.json in Claude.ai chat")
    lines.append("  (Thematic analysis → Investment Gate → Deep DD)")
    lines.append("=" * 72)

    return "\n".join(lines)


def save_results(technical_signals: List[Stock], sell_signals: List[SellSignal],
                stats: ScanStats, archive: bool = False):
    """Save technical scan results to signals_technical.json and analysis log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ensure weekly folder structure exists
    current_dir, week_dir = ensure_output_structure()

    # Helper for relative paths in output
    def _rel(p: Path) -> str:
        return get_relative_path(p) if OUTPUT_PATHS_AVAILABLE else str(p)

    # Build signal dicts — technical fields only
    def _tech_signal(s: Stock) -> dict:
        return {
            "symbol": s.symbol,
            "price": s.price,
            "tier": s.tier,
            "quality_tier": s.quality_tier,
            "beta": s.beta,
            "uc": s.uc,
            "uc_rising": s.uc_rising,
            "rsi14": s.rsi14,
            "macd_cross_up": s.macd_cross_up,
            "hma_pivot_low": s.hma_pivot_low,
            "hma_pivot_high": s.hma_pivot_high,
            "hma_slope_rising": s.hma_slope_rising,
            "buy_signal": s.buy_signal,
            "buy_signal_v6": s.buy_signal_v6,
            "exd_signal": s.exd_signal,
            "atr": s.atr,
            "atr_rank": s.atr_rank,
            "atr_squeeze": s.atr_squeeze,
            "return_20d": s.return_20d,
            "momentum_4w": s.momentum_4w,
            "week_date": s.week_date,
            # yfinance fundamentals + profile (None/empty if enrichment unavailable)
            "enrichment": s.enrichment,
            # Legacy compat keys for downstream systems
            "banker": s.uc,
            "uc_rising_above": False,  # V4 legacy — always False in V6+
        }

    signals_data = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": "Sterling Grid V8.1: bare HMA(21) pivot up (no UC/MACD/ATR gate); gates inform sizing only",
        "exit_criteria": "Sterling Grid V8.1: HMA exit (HMA pivot high / HMA down, all positions) OR tiered trailing lock for runners; -35% floor < +50% (new) / -50% backstop (legacy); ExD no longer used",
        "stats": {
            "tickers_loaded": stats.tickers_loaded,
            "data_downloaded": stats.data_downloaded,
            "hma_pivot_low": stats.hma_pivot_low,
            "macd_cross_up": stats.macd_cross_up,
            "uc_rising": stats.uc_rising,
            "atr_squeeze": stats.atr_squeeze,
            "buy_signal_v6": stats.buy_signal_v6,
            "buy_signal": stats.buy_signal,
            "tier_t1": stats.tier_t1,
            "tier_t2": stats.tier_t2,
            "tier_t3": stats.tier_t3,
            "tier_t4": stats.tier_t4,
            "tier_t5": stats.tier_t5,
            "tier_t6": stats.tier_t6,
            "exd_exit": stats.exd_exit,
            "technical_signals": stats.technical_signals,
        },
        "buy_signals": [_tech_signal(s) for s in technical_signals],
        "sell_signals": [
            {
                "symbol": s.symbol,
                "price": s.price,
                "reason": s.reason,
                "entry_price": s.entry_price,
                "highest_close": s.highest_close,
                "drawdown_pct": s.drawdown_pct,
                "pnl_pct": round(((s.price / s.entry_price) - 1) * 100, 2) if s.entry_price > 0 else 0.0,
            }
            for s in sell_signals
        ],
        # Historical tracking for content systems
        "historical_winners": [],
        "big_wins": [],
        "home_runs": [],
    }

    # Populate historical wins from signal_tracker (if available)
    try:
        from twitter.signal_tracker import load_historical_signals, find_big_wins
        from config import MARKETING_THRESHOLDS

        historical = load_historical_signals()
        signals_data["historical_winners"] = [
            {
                "ticker": h.ticker,
                "entry_price": h.entry_price,
                "current_price": h.current_price,
                "pnl_pct": h.pnl_pct,
                "signal_date": h.entry_date,
                "theme": h.theme,
            }
            for h in historical
        ]

        all_big_wins = find_big_wins()
        big_win_threshold = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)
        home_run_threshold = MARKETING_THRESHOLDS.get('home_run_threshold', 50.0)

        signals_data["big_wins"] = [
            {
                "ticker": w.ticker,
                "entry_price": w.entry_price,
                "current_price": w.current_price,
                "pnl_pct": w.pnl_pct,
                "signal_date": w.entry_date,
                "theme": w.theme,
            }
            for w in all_big_wins if w.pnl_pct >= big_win_threshold
        ]

        signals_data["home_runs"] = [
            {
                "ticker": w.ticker,
                "entry_price": w.entry_price,
                "current_price": w.current_price,
                "pnl_pct": w.pnl_pct,
                "signal_date": w.entry_date,
                "theme": w.theme,
            }
            for w in all_big_wins if w.pnl_pct >= home_run_threshold
        ]

        print(f"  📊 Historical tracking: {len(signals_data['historical_winners'])} positions, {len(signals_data['big_wins'])} big wins, {len(signals_data['home_runs'])} home runs")

    except ImportError:
        print("  ⚠️ signal_tracker not available - historical wins not populated")
    except Exception as e:
        print(f"  ⚠️ Error loading historical wins: {e}")

    # Write outputs
    signals_json = json.dumps(signals_data, indent=2)

    with open(SIGNALS_TECH_FILE, 'w') as f:
        f.write(signals_json)

    signals_current = current_dir / "signals_technical.json"
    with open(signals_current, 'w') as f:
        f.write(signals_json)

    signals_archive = week_dir / "signals_technical.json"
    with open(signals_archive, 'w') as f:
        f.write(signals_json)

    # NOTE: signals.json is produced by merge_decisions.py (Saturday workflow),
    # NOT by scanner.py. Scanner only writes signals_technical.json.

    # ── Analysis log (CSV) — technical fields only ──
    analysis_log = ANALYSIS_LOG
    write_header = not analysis_log.exists()

    with open(analysis_log, 'a', newline='') as f:
        fieldnames = [
            'timestamp', 'symbol', 'price', 'beta', 'uc', 'uc_rising',
            'rsi14', 'macd_cross_up', 'hma_pivot_low', 'buy_signal',
            'quality_tier', 'tier', 'momentum_4w', 'return_20d', 'exd_signal',
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        for s in technical_signals:
            writer.writerow({
                'timestamp': timestamp,
                'symbol': s.symbol,
                'price': s.price,
                'beta': s.beta,
                'uc': s.uc,
                'uc_rising': s.uc_rising,
                'rsi14': s.rsi14,
                'macd_cross_up': s.macd_cross_up,
                'hma_pivot_low': s.hma_pivot_low,
                'buy_signal': s.buy_signal,
                'quality_tier': s.quality_tier,
                'tier': s.tier,
                'momentum_4w': s.momentum_4w,
                'return_20d': s.return_20d,
                'exd_signal': s.exd_signal,
            })

    # ── Generate and save report ──
    report = generate_report(technical_signals, sell_signals, stats)

    report_current = current_dir / "report.txt"
    report_archive = week_dir / "report.txt"
    with open(report_current, 'w') as f:
        f.write(report)
    with open(report_archive, 'w') as f:
        f.write(report)

    print(f"\n  📁 Results saved:")
    print(f"     • {_rel(SIGNALS_TECH_FILE)} (PRIMARY — signals_technical.json)")
    print(f"     • {_rel(signals_current)} (current week)")
    print(f"     • {_rel(signals_archive)} (archived)")
    print(f"     • {_rel(analysis_log)}")
    print(f"     • {_rel(report_current)} (report)")

    return report


def send_notification(technical_signals: List[Stock], sell_signals: List[SellSignal], stats: ScanStats, report: str = None):
    """Send email notification with formatted report."""
    try:
        from utils.email_notifier import send_email, load_config

        config = load_config()
        if not config:
            print("  ⚠ Email not configured (run: python email_notifier.py setup)")
            return

        # Generate subject line
        if technical_signals or sell_signals:
            entries = len(technical_signals) if technical_signals else 0
            exits = len(sell_signals) if sell_signals else 0

            parts = []
            if entries:
                parts.append(f"{entries} Entry")
            if exits:
                parts.append(f"{exits} Exit")

            subject = f"BoS Scanner: {', '.join(parts)}" if parts else "BoS Scanner: Weekly Report"
        else:
            subject = "BoS Scanner: No Signals This Week"

        # Use provided report or generate a minimal one
        if report:
            body = report
        else:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            body = f"""BoS Momentum Scanner - Weekly Report
{date_str}

No detailed report available.

SCAN STATS:
  Tickers scanned:    {stats.tickers_loaded}
  Buy signals (V6):   {stats.buy_signal}
  Technical signals:  {stats.technical_signals}
"""

        if send_email(subject, body):
            recipients = config.get("recipients", [config.get("to_email", "")])
            print(f"  ✓ Email sent to {len(recipients)} recipient(s)")
            print(f"     Subject: {subject}")
        else:
            print("  ✗ Email send failed")

    except ImportError:
        print("  ⚠ email_notifier.py not found")
    except Exception as e:
        print(f"  ⚠ Email error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Sterling Grid V7 — Pure Technical Signal Detector (Weekly)")
    parser.add_argument("--top", type=int, help="Only scan top N stocks by UC")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed diagnostic output (10 items per category instead of 3)")
    parser.add_argument("--archive", action="store_true", help="Save dated archive files in addition to latest files")
    parser.add_argument("--no-email", action="store_true", help="Skip email notification")
    args = parser.parse_args()

    # Header
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "STERLING GRID V8.1 — WEEKLY TECHNICAL SCANNER".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Show entry/exit criteria (marketing-safe by default, detailed with --verbose)
    if args.verbose:
        print(f"\n  ENTRY (V8.1): bare HMA(21) pivot up — fire wide, no UC/MACD/ATR gate")
        print("  EXIT (V8.1): HMA exit (HMA pivot high / HMA down, every position) OR tiered lock for runners")
        print("    • runners: trailing lock (+200%→15%, +100%→20%, +50%→25%); new: -35% floor < +50%")
        print("  LEGACY (pre-2026 holds): HMA exit (HMA pivot high) + -50% disaster backstop")
    else:
        print("\n  ENTRY (V8.1): HMA pivot up — fire wide, LLM selects")
        print("  EXIT (V8.1): HMA pivot down OR tiered lock (act next candle open)")

    print("\n  Pipeline: Pure Technical Signal Detector (no LLM API calls)")
    print("  Cost: $0.00 (free)")
    print("  Schedule: Run WEEKLY (signals only change on Friday close)")
    print("  Next: Review signals_technical.json → Claude.ai chat for thematic + investment analysis")

    # Portfolio status
    try:
        pm = get_portfolio_manager()
        open_count = len(pm.get_open_positions())
        if open_count > 0:
            print(f"\n  📊 Portfolio: {open_count} open position(s) tracked")
            print(f"     • {rel_path(pm.portfolio_file)}")
            print(f"     • Google Sheets export on completion")
    except Exception:
        pass

    start_time = time.time()

    # Run scan (pure technical — no LLM API calls)
    technical_signals, sell_signals, stats, stocks = run_scan(
        top_n=args.top,
        verbose=args.verbose
    )

    # Print report
    print_final_report(technical_signals, sell_signals, stats)

    # Save results and generate report (always write, even with empty signals)
    report = None
    try:
        report = save_results(technical_signals, sell_signals, stats, archive=args.archive)
    except Exception as e:
        print(f"  ⚠ Error saving results: {e}")
        import traceback
        traceback.print_exc()

    # Portfolio summary and Google Sheets export
    try:
        pm = get_portfolio_manager()

        print("\n" + "─" * 70)
        print("  PORTFOLIO UPDATE")
        print("─" * 70)

        # Update portfolio prices from scanner's yfinance data
        if stocks:
            open_symbols = pm.get_open_symbols()
            matched = open_symbols & set(stocks.keys())
            update_portfolio_prices(stocks)
            # Reload to get persisted state
            pm = get_portfolio_manager()
            print(f"  ✓ Live prices updated for {len(matched)}/{len(open_symbols)} open positions (from scanner data)")

            # Fallback: fetch prices for portfolio tickers not in scanner data
            missing = open_symbols - set(stocks.keys())
            if missing:
                print(f"  ℹ {len(missing)} portfolio ticker(s) not in scanner data, fetching separately...")
                from portfolio.manager import fetch_current_prices
                fallback_prices = fetch_current_prices(list(missing))
                for sym, price in fallback_prices.items():
                    trade = next((t for t in pm.get_open_positions() if t.ticker == sym), None)
                    if trade and price > 0:
                        trade.calculate_metrics(price)
                if fallback_prices:
                    pm._save()
                    pm.export_for_google_sheets()
                    print(f"  ✓ Fallback prices updated for {len(fallback_prices)} ticker(s)")

        open_positions = pm.get_open_positions()
        closed_trades = pm.get_closed_trades()

        print(f"  ✓ Portfolio: {len(open_positions)} open, {len(closed_trades)} closed")
        print(f"  ✓ CSV: {rel_path(pm.portfolio_file)}")

        sheets_file = pm.export_for_google_sheets()
        print(f"  ✓ Google Sheets export: {rel_path(sheets_file)}")

        # Performance summary
        if closed_trades:
            perf = pm.get_performance_summary()
            win_rate = perf.get('closed_win_rate', 0)
            avg_win = perf.get('avg_winner', 0)
            avg_loss = perf.get('avg_loser', 0)
            print(f"\n  📊 Performance (closed trades):")
            print(f"     Win Rate: {win_rate:.0f}% │ Avg Win: +{avg_win:.1f}% │ Avg Loss: {avg_loss:.1f}%")

        # Stop alerts
        alerts = [t for t in open_positions if t.stop_alert]
        if alerts:
            print(f"\n  ⚠️  STOP ALERTS ({len(alerts)} positions within 5% of stop):")
            for t in alerts:
                print(f"     • {t.ticker}: ${t.current_price:.2f} (stop: ${t.stop_level:.2f})")

        # Record compounding equity curve
        try:
            from config import CURRENCY_SYMBOL
            snapshot = pm.update_equity_curve()
            print(f"\n  💰 Equity (Compounding):")
            print(f"     NAV: {CURRENCY_SYMBOL}{snapshot.nav:,.2f} ({snapshot.total_return_pct:+.1f}%)")
            print(f"     SPY: {CURRENCY_SYMBOL}{snapshot.spy_value:,.2f} ({snapshot.spy_return_pct:+.1f}%)")
            print(f"     Alpha: {snapshot.alpha_pct:+.1f}%")
        except Exception as e:
            print(f"  ⚠ Equity tracking: {e}")
    except Exception as e:
        print(f"  ⚠ Portfolio summary error: {e}")

    # Next steps guidance
    print("\n" + "─" * 70)
    print("  NEXT STEPS")
    print("─" * 70)
    print("  1. Review signals_technical.json for buy/sell signals")
    print("  2. Open Claude.ai → attach sterling_prompt_library.md")
    print("  3. Run thematic analysis + investment gate in chat")
    print("  4. Update portfolio with final decisions")

    # Send email with the formatted report
    if not args.no_email:
        try:
            print("\n" + "─" * 70)
            print("  EMAIL NOTIFICATION")
            print("─" * 70)
            send_notification(technical_signals, sell_signals, stats, report)
        except Exception as e:
            print(f"  ⚠ Error sending email notification: {e}")

    duration = time.time() - start_time

    # Pipeline timing summary
    _pipeline_timer.print_summary()

    print(f"\n  Completed in {duration:.1f} seconds")
    print("═" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
