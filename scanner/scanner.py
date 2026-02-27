#!/usr/bin/env python3
"""
STERLING GRID MOMENTUM SCANNER V6 - PURE TECHNICAL SIGNAL DETECTOR (WEEKLY)
============================================================================

Detects weekly momentum entry/exit signals using Sterling Grid V6 indicators.
V6 backtest validated: Tiered 20/10/5 = +3294% return, -5.1% DD, 645x ret/DD.

ENTRY CRITERIA (V6: HMA pivot + OR-gated confirmation):
1. HMA(21) PIVOT LOW — V-bottom: HMA[i-2] > HMA[i-1] < HMA[i]
2. At least ONE confirmation gate:
   a. UC rising (UC > UC.shift(1)) — institutional accumulation  (OR)
   b. MACD(12,26,9) cross-up — timing confirmation (single bar event)
QUALITY TIERS (at signal bar):
- T1: UC rising AND MACD cross-up (both gates) → 20% of equity
- T2: MACD cross-up only (timing confirmed)    → 10% of equity
- T3: UC rising only (regime confirmed)         →  5% of equity
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

# Sterling Grid indicators (V6 — pivot entry, OR-gated, quality tiers)
from scanner.sterling_indicators import (
    resample_to_weekly,
    calculate_hma_pivots,
    generate_entry_signal,
    generate_exit_signal,
    check_profit_lock,
    calculate_position_size as calc_position_size,
)

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

# V6 tier allocation (% of equity per quality tier)
TIER_ALLOC = {"T1": 20, "T2": 10, "T3": 5}


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
    buy_signal: bool = False         # V6: HMA pivot + (UC OR MACD)
    exd_signal: bool = False         # V6: HMA pivot high + UC falling
    # Quality tier (V6: determined by which gates active at signal bar)
    quality_tier: int = 0            # 0=no signal, 1=T1 (both), 2=T2 (MACD), 3=T3 (UC)
    # Week date from data
    week_date: str = ""

    # ── Computed fields ────────────────────────────────────────────────────
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""

    def meets_technical_criteria(self) -> bool:
        """Check if stock meets Sterling Grid V6 technical entry criteria.

        V6 entry: HMA(21) pivot low AND (UC rising OR MACD cross-up)
        """
        return self.buy_signal

    def get_tier(self) -> str:
        """Return quality tier label based on which gates are active at signal bar.

        T1: UC rising AND MACD cross-up (both gates — 20% equity)
        T2: MACD cross-up only (timing confirmed — 10% equity)
        T3: UC rising only (regime confirmed — 5% equity)
        """
        if not self.meets_technical_criteria():
            return ""
        if self.quality_tier == 1:
            return "T1"
        elif self.quality_tier == 2:
            return "T2"
        elif self.quality_tier == 3:
            return "T3"
        # Fallback: classify from indicator state
        if self.uc_rising and self.macd_cross_up:
            self.quality_tier = 1
            return "T1"
        elif self.macd_cross_up:
            self.quality_tier = 2
            return "T2"
        elif self.uc_rising:
            self.quality_tier = 3
            return "T3"
        return "T3"  # Default to lowest tier if somehow unclassified


@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    # Sterling Grid V6 indicator stats
    hma_pivot_low: int = 0         # HMA(21) V-bottom pivot (V6 entry trigger)
    hma_slope_rising: int = 0      # HMA(21) slope rising (informational)
    macd_cross_up: int = 0         # MACD single-bar cross-up
    uc_rising: int = 0             # V6: UC > UC.shift(1) (no >0 req)
    buy_signal: int = 0            # V6: pivot + (UC OR MACD) + price
    exd_exit: int = 0              # V6: HMA pivot high + UC falling
    # Quality tier counts
    tier_t1: int = 0               # Both gates (UC + MACD)
    tier_t2: int = 0               # MACD only
    tier_t3: int = 0               # UC only
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
    1. Check price < $25 (fast filter)
    2. Resample daily → weekly
    3. Calculate V6 entry conditions via generate_entry_signal()
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
                data = yf.download(chunk, period="1y", progress=False, threads=True, group_by='ticker')

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

                            # Exit signal (V6 ExD: HMA pivot high + UC falling)
                            exit_data = generate_exit_signal(weekly)
                            cur_exit = exit_data.iloc[-1]

                            stock.uc_falling = bool(cur_exit['uc_falling'])
                            stock.exd_signal = bool(cur_exit['exd_signal'])
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


def check_sell_signals(stocks: Dict[str, Stock]) -> List[SellSignal]:
    """
    Check for sell signals on open positions using Sterling Grid V6 exit criteria.

    EXIT CRITERIA (first exit — whichever fires first):
    1. ExD compound exit (HMA PIVOT HIGH + UC falling on same bar) → EXIT immediately
    2. Tiered profit lock (based on CURRENT return, not peak) → EXIT immediately
       - Current return >= +200%: 15% trail from peak
       - Current return >= +100%: 20% trail from peak
       - Current return >= +50%:  25% trail from peak
       - Below +50%: Only ExD can trigger exit (no trailing stop)
    Both can fire on same bar → exit once with combined reason.
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

            # CHECK EXIT CRITERIA (first exit — whichever fires first)
            exit_reasons = []

            # 1. ExD compound exit (HMA pivot high + UC falling)
            if stock.exd_signal:
                exit_reasons.append(f"ExD exit (HMA pivot high + UC falling)")

            # 2. Tiered profit lock
            lock_result = check_profit_lock(trade.entry_price, current_price, trade.highest_close)
            if lock_result.get('triggered', False):
                tier_info = lock_result.get('active_tier', 'unknown')
                lock_level = lock_result.get('lock_level', 0)
                exit_reasons.append(f"Profit lock ({tier_info}, lock=${lock_level:.2f})")

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

def run_scan(top_n: int = 0, verbose: bool = False) -> Tuple[List[Stock], List[SellSignal], ScanStats]:
    """Run the complete scan pipeline (pure technical — no LLM gates).

    Returns (technical_signals, sell_signals, stats).

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
        spy = yf.download("SPY", period="1y", progress=False)
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
        if stock.buy_signal:
            stats.buy_signal += 1
            # Count by quality tier
            if stock.quality_tier == 1:
                stats.tier_t1 += 1
            elif stock.quality_tier == 2:
                stats.tier_t2 += 1
            elif stock.quality_tier == 3:
                stats.tier_t3 += 1
        if stock.exd_signal:
            stats.exd_exit += 1

    # Sort eligible stocks by UC (strongest accumulation first)
    eligible_stocks.sort(key=lambda x: -x.uc)

    if top_n and len(eligible_stocks) > top_n:
        eligible_stocks = eligible_stocks[:top_n]
        print(f"  (Limited to top {top_n} by UC)")

    print(f"\n  STERLING GRID V6 FILTER RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Total tickers scanned:    {stats.tickers_loaded:>6}")
    print(f"  Data downloaded:          {stats.data_downloaded:>6}")
    if verbose:
        # Internal terminology for debugging
        print(f"  HMA pivot low (V6):       {stats.hma_pivot_low:>6}")
        print(f"  HMA slope rising:         {stats.hma_slope_rising:>6}  (informational)")
        print(f"  MACD cross-up:            {stats.macd_cross_up:>6}")
        print(f"  UC rising (V6):           {stats.uc_rising:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  BUY signal (V6):          {stats.buy_signal:>6}")
        if stats.buy_signal > 0:
            print(f"    T1 (both gates):        {stats.tier_t1:>6}")
            print(f"    T2 (MACD only):         {stats.tier_t2:>6}")
            print(f"    T3 (UC only):           {stats.tier_t3:>6}")
        print(f"  ExD exit signal:          {stats.exd_exit:>6}")
    else:
        # Marketing-safe terminology
        print(f"  Structural pivot (V6):    {stats.hma_pivot_low:>6}")
        print(f"  Timing confirmed:         {stats.macd_cross_up:>6}")
        print(f"  Accumulation rising:      {stats.uc_rising:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  Full entry signal:        {stats.buy_signal:>6}")
        print(f"  Exit signals:             {stats.exd_exit:>6}")

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

    # Buy signals (V6: HMA pivot + OR-gated confirmation)
    buy_signal_stocks = [s for s in stocks.values() if s.buy_signal]
    if verbose:
        print(f"\n  🟢 BUY SIGNALS (V6 pivot + gate): {len(buy_signal_stocks)}")
    else:
        print(f"\n  🟢 FULL ENTRY SIGNALS: {len(buy_signal_stocks)}")
    if buy_signal_stocks and verbose:
        for s in sorted(buy_signal_stocks, key=lambda x: -x.uc)[:sample_size]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            tier_label = s.get_tier() or "?"
            print(f"      {s.symbol:<6} ${s.price:<8.2f} {tier_label} UC={s.uc:.1f} RSI={s.rsi14:.0f} HMA={'⌄' if s.hma_pivot_low else '↑' if s.hma_slope_rising else '↓'}{held_flag}")

    # ExD exit signals
    exd_stocks = [s for s in stocks.values() if s.exd_signal]
    if verbose:
        print(f"  🔴 ExD EXIT: {len(exd_stocks)} (HMA pivot high + UC falling)")
    else:
        print(f"  🔴 EXIT SIGNALS: {len(exd_stocks)} (positions closed)")
    if exd_stocks and verbose:
        for s in exd_stocks[:sample_size]:
            print(f"      {s.symbol:<6} ${s.price:<8.2f} UC={s.uc:.1f} HMA={'⌃' if s.hma_pivot_high else '↓'}")

    # Entry candidates under price cap with buy signal
    buy_under_cap = [s for s in eligible_stocks if s.buy_signal]
    if verbose:
        print(f"\n  ⭐ ENTRY CANDIDATES (V6 Signal): {len(buy_under_cap)}")
    else:
        print(f"\n  ⭐ ENTRY CANDIDATES (Gate Qualified): {len(buy_under_cap)}")
    if buy_under_cap:
        for s in sorted(buy_under_cap, key=lambda x: -x.uc)[:sample_size]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            tier_label = s.get_tier() or "?"
            print(f"      {s.symbol:<6} ${s.price:<8.2f} {tier_label} UC={s.uc:.1f} RSI={s.rsi14:.0f} MACD={'✓' if s.macd_cross_up else '✗'}{held_flag}")

    if not verbose:
        print(f"\n  💡 Use --verbose for detailed diagnostics")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Apply Sterling Grid Technical Gates
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 5: Applying Sterling Grid Technical Gates")
    print("─" * 70)
    print(f"\n  📊 Entry (V6): HMA pivot↓ + (UC rising OR MACD cross-up)")

    technical_signals = []

    for stock in eligible_stocks:
        if stock.meets_technical_criteria():
            stats.meets_technical_gate += 1
            stock.tier = stock.get_tier()
            if stock.tier:
                technical_signals.append(stock)
                stats.technical_signals += 1

    print(f"\n  STERLING GRID V6 GATE RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Eligible stocks:           {len(eligible_stocks):>5}")
    print(f"  Buy signal (V6 pivot):     {stats.meets_technical_gate:>5}")
    print(f"  ────────────────────────────────────")
    print(f"  TECHNICAL SIGNALS:         {stats.technical_signals:>5}")
    if stats.technical_signals > 0:
        print(f"    T1 (UC + MACD, 20%):     {stats.tier_t1:>5}")
        print(f"    T2 (MACD only, 10%):     {stats.tier_t2:>5}")
        print(f"    T3 (UC only, 5%):        {stats.tier_t3:>5}")
    print(f"  ────────────────────────────────────")

    if technical_signals:
        print(f"\n  ✅ TECHNICAL SIGNALS:")
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"    {s.tier}  {s.symbol:<6} ${s.price:>8.2f}  UC={s.uc:.1f}  RSI={s.rsi14:.0f}  MACD={'✓' if s.macd_cross_up else '✗'}  HMA={'⌄' if s.hma_pivot_low else '↑'}{held_flag}")

    if not technical_signals:
        print("\n  No technical signals to process")
        sell_signals = check_sell_signals(stocks)
        return [], sell_signals, stats

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Technical signals ready (LLM gates → Claude.ai chat)
    # ─────────────────────────────────────────────────────────────────────────
    _pipeline_timer.stop()  # Stop Steps 1-5 timing

    # Show candidates summary
    print(f"\n  📊 ENTRY CANDIDATES: {len(technical_signals)} passed technical filters")
    sorted_signals = sorted(technical_signals, key=lambda x: -x.uc)
    for s in sorted_signals[:5]:
        held_flag = " [HELD]" if s.symbol in open_positions else ""
        print(f"     {s.symbol:<6} | {s.tier} | UC={s.uc:.1f} | RSI={s.rsi14:.0f} | MACD={'✓' if s.macd_cross_up else '✗'} | 20d={s.return_20d:+.1f}%{held_flag}")
    if len(sorted_signals) > 5:
        print(f"     ... and {len(sorted_signals) - 5} more")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Check Sell Signals (ExD compound exit OR tiered profit lock)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 7: Checking Sell Signals (ExD Pivot High exit OR Tiered Profit Lock)")
    print("─" * 70)

    sell_signals = check_sell_signals(stocks)

    if sell_signals:
        print(f"  ⚠ {len(sell_signals)} SELL SIGNAL(S):")
        for s in sell_signals:
            print(f"    🔴 {s.symbol} @ ${s.price:.2f} - {s.reason}")
    else:
        print(f"  ✓ No sell signals")

    # NOTE: Portfolio updates now happen AFTER review in Claude.ai chat

    return technical_signals, sell_signals, stats


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def print_final_report(technical_signals: List[Stock], sell_signals: List[SellSignal], stats: ScanStats):
    """Print final summary report."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "FINAL REPORT".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if technical_signals:
        print(f"\n  ⭐ ENTRY CANDIDATES ({len(technical_signals)}) — pending Claude.ai analysis:")
        print("  " + "─" * 66)
        print(f"  {'TIER':<5} {'SYMBOL':<7} {'PRICE':>8} {'UC':>6} {'RSI':>5} {'MACD':>5} {'20D':>7}")
        print("  " + "-" * 50)
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            macd = "✓" if s.macd_cross_up else "✗"
            print(f"  {s.tier:<5} {s.symbol:<7} ${s.price:>7.2f} {s.uc:>5.1f} {s.rsi14:>5.0f} {macd:>5} {s.return_20d:>+6.1f}%")

        # Total allocation summary
        total_alloc = sum(TIER_ALLOC.get(s.tier, 0) for s in technical_signals)
        if total_alloc:
            print(f"\n    💰 Potential equity deployment: {total_alloc}% (pending analysis)")
    else:
        print("\n  NO TECHNICAL ENTRY SIGNALS")
        print(f"\n  Pipeline summary:")
        print(f"    • {stats.tickers_loaded} tickers scanned")
        print(f"    • {stats.buy_signal} with full buy signal (V6 pivot + gate)")
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
    print(f"  EXIT STRATEGY (first exit — whichever fires first):")
    print(f"    • ExD compound exit (HMA pivot high + UC falling) = immediate exit")
    print(f"    • Tiered profit lock (>=+200%→15%, >=+100%→20%, >=+50%→25% trail)")
    print(f"    • Below +50% return: only ExD can trigger exit")
    print(f"    • Whichever fires first closes the position")
    print("  " + "═" * 66)


def generate_report(technical_signals: List[Stock], sell_signals: List[SellSignal],
                   stats: ScanStats) -> str:
    """Generate scan summary report for email notification and archival."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_display = datetime.now().strftime("%A, %B %d, %Y")

    lines = []
    lines.append("=" * 72)
    lines.append(f"  STERLING GRID V6 — WEEKLY SCAN REPORT")
    lines.append(f"  {date_display}")
    lines.append(f"  Generated: {timestamp}")
    lines.append("=" * 72)

    # Scan funnel
    lines.append("")
    lines.append(f"  Tickers scanned:     {stats.tickers_loaded:>6}")
    lines.append(f"  Data downloaded:     {stats.data_downloaded:>6}")
    lines.append(f"  HMA pivot low:       {stats.hma_pivot_low:>6}")
    lines.append(f"  Buy signal (V6):     {stats.buy_signal:>6}")
    lines.append(f"    T1 (UC + MACD):    {stats.tier_t1:>6}")
    lines.append(f"    T2 (MACD only):    {stats.tier_t2:>6}")
    lines.append(f"    T3 (UC only):      {stats.tier_t3:>6}")
    lines.append(f"  ExD exit signals:    {stats.exd_exit:>6}")

    # Entry candidates
    if technical_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ENTRY CANDIDATES (pending Claude.ai analysis)")
        lines.append("─" * 72)
        lines.append(f"  {'TIER':<5} {'SYMBOL':<7} {'PRICE':>8} {'UC':>6} {'RSI':>5} {'MACD':>5} {'20D':>7}")
        lines.append("  " + "-" * 50)
        for s in sorted(technical_signals, key=lambda x: -x.uc):
            macd = "✓" if s.macd_cross_up else "✗"
            lines.append(f"  {s.tier:<5} {s.symbol:<7} ${s.price:>7.2f} {s.uc:>5.1f} {s.rsi14:>5.0f} {macd:>5} {s.return_20d:>+6.1f}%")
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
            "exd_signal": s.exd_signal,
            "return_20d": s.return_20d,
            "momentum_4w": s.momentum_4w,
            "week_date": s.week_date,
            # Legacy compat keys for downstream systems
            "banker": s.uc,
            "uc_rising_above": False,  # V4 legacy — always False in V6
        }

    signals_data = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": "Sterling Grid V6: HMA pivot + (UC rising OR MACD cross-up)",
        "exit_criteria": "ExD compound exit + tiered profit lock",
        "stats": {
            "tickers_loaded": stats.tickers_loaded,
            "data_downloaded": stats.data_downloaded,
            "hma_pivot_low": stats.hma_pivot_low,
            "macd_cross_up": stats.macd_cross_up,
            "uc_rising": stats.uc_rising,
            "buy_signal": stats.buy_signal,
            "tier_t1": stats.tier_t1,
            "tier_t2": stats.tier_t2,
            "tier_t3": stats.tier_t3,
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
    parser = argparse.ArgumentParser(description="Sterling Grid V6 — Pure Technical Signal Detector (Weekly)")
    parser.add_argument("--top", type=int, help="Only scan top N stocks by UC")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed diagnostic output (10 items per category instead of 3)")
    parser.add_argument("--archive", action="store_true", help="Save dated archive files in addition to latest files")
    parser.add_argument("--no-email", action="store_true", help="Skip email notification")
    args = parser.parse_args()

    # Header
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "STERLING GRID V6 — WEEKLY TECHNICAL SCANNER".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Show entry/exit criteria (marketing-safe by default, detailed with --verbose)
    if args.verbose:
        print(f"\n  ENTRY (V6): HMA pivot↓ + (UC rising OR MACD cross-up)")
        print("  TIERS: T1 (both, 20%) | T2 (MACD, 10%) | T3 (UC, 5%) | Max 8 positions")
        print("  EXIT:  ExD (HMA pivot↑ + UC↓) OR tiered profit lock (+200%→15%, +100%→20%, +50%→25%)")
    else:
        print("\n  ENTRY (V6): Pivot + Confirmation Gate Screening (Structural + Timing/Accumulation + Price)")
        print("  EXIT:  Capital Preservation Protocol (first exit — whichever fires first)")

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
    technical_signals, sell_signals, stats = run_scan(
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
        open_positions = pm.get_open_positions()
        closed_trades = pm.get_closed_trades()

        print("\n" + "─" * 70)
        print("  PORTFOLIO UPDATE")
        print("─" * 70)
        print(f"  ✓ Portfolio: {len(open_positions)} open, {len(closed_trades)} closed")
        print(f"  ✓ CSV: {rel_path(pm.portfolio_file)}")

        # Export for Google Sheets
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
