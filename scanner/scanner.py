#!/usr/bin/env python3
"""
STERLING GRID MOMENTUM SCANNER V6 - INTEGRATED PIPELINE (WEEKLY TIMEFRAME)
============================================================================

Complete pipeline for WEEKLY momentum trading using Sterling Grid indicators.
V6 backtest validated: Tiered 20/10/5 = +3294% return, -5.1% DD, 645x ret/DD.

ENTRY CRITERIA (V6: HMA pivot + OR-gated confirmation):
1. HMA(21) PIVOT LOW — V-bottom: HMA[i-2] > HMA[i-1] < HMA[i]
2. At least ONE confirmation gate:
   a. UC rising (UC > UC.shift(1)) — institutional accumulation  (OR)
   b. MACD(12,26,9) cross-up — timing confirmation (single bar event)
3. Price < $25 (price cap)
Plus: Theme fit (Thematic Analyzer) + Investment Gate PASS

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

SIGNAL TERMINOLOGY:
- Internal: PASS, CONSIDER, SKIP (scanner decisions)
- Marketing: "TEAL signal" = PASS signal that cleared all gates
- Gate verdicts: STRONG_BUY, SPEC_BUY, NO_GO (Investment Gate)

THEME CLASSIFICATION (from Thematic Analyzer):
- PRIME: High conviction theme with strong catalysts + momentum
- INVESTABLE: Good opportunity, standard position sizing
- SELECTIVE: Mixed signals - only best stocks in this theme
- AVOID: Fading momentum or overcrowded - do not invest

CONTEXT:
- Weekly timeframe for systematic entries and exits
- Average hold period: 4-8 weeks (can extend to months)
- Audience-neutral - no region-specific investment advice

Usage:
    python -m core.scanner                    # Full pipeline
    python -m core.scanner --no-llm           # Skip LLM gates (technical signals only)
    python -m core.scanner --no-email         # Skip email notification
    python -m core.scanner --top 100          # Only scan top 100 by UC
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
    BETA_THRESHOLD,
    TRAILING_STOP_PCT as _CFG_TRAILING_STOP_PCT,
    HMA_PERIOD,
    MIN_TRADING_DAYS,
    PRICE_CAP,
    LOCK_TIERS,
    QUALITY_TIERS,
    SIZING_GEARS,
    MAX_CONCURRENT_POSITIONS,
    DEFAULT_SIZING_GEAR,
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
PORTFOLIO_MANAGER_AVAILABLE = True  # Hard dependency as of audit remediation

# Output paths for weekly folder structure
try:
    from config.output_paths import (
        get_scanner_current_dir as get_current_dir,
        get_scanner_archive_dir as get_week_dir,
        ensure_output_structure,
        get_relative_path,
        SIGNALS_FILE,
        ANALYSIS_LOG,
        SCANNER_OUTPUT,
        PORTFOLIO_FILE,
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False
    _FALLBACK_OUTPUT = Path(__file__).resolve().parent / "output"
    SIGNALS_FILE = _FALLBACK_OUTPUT / "signals.json"
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

# Legacy thresholds — kept for daily_scanner backward compat
BETA_MIN = BETA_THRESHOLD
BETA_SIGNAL = BETA_THRESHOLD
TRAILING_STOP_PCT = float(_CFG_TRAILING_STOP_PCT)  # Used by daily scanner only

# Note: Weekly scanner uses Sterling Grid V6 indicators instead of BoS + Banker.
# Entry: HMA pivot low + (UC rising OR MACD cross-up) + Price < $25
# Exit: ExD (HMA pivot high + UC falling) OR tiered profit lock
# Tiers: T1 (both gates, 20%), T2 (MACD, 10%), T3 (UC, 5%)
TIER_ALLOC = {"T1": 20, "T2": 10, "T3": 5}  # % of equity per tier


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
    hma_slope_falling: bool = False  # Informational
    # RSI(14) — computed for display, NOT an entry gate in V6
    rsi14: float = 0.0
    rsi_above_50: bool = False       # Informational only
    # MACD timing gate (OR-gated with UC in V6)
    macd_cross_up: bool = False
    macd_line: float = 0.0
    macd_signal_line: float = 0.0
    macd_histogram: float = 0.0
    # Undercurrent (UC) — RSI(10)-based, NOT VWAP
    uc: float = 0.0
    uc_prev: float = 0.0
    uc_rising: bool = False          # V6: UC > UC.shift(1) — no >0 requirement
    uc_rising_above: bool = False    # V4 legacy: UC > prev AND UC > 0
    uc_falling: bool = False
    # Composite signals
    price_under_cap: bool = False    # Price < $25
    buy_signal: bool = False         # V6: HMA pivot + (UC OR MACD) + price
    exd_signal: bool = False         # V6: HMA pivot high + UC falling
    # Quality tier (V6: determined by which gates active at signal bar)
    quality_tier: int = 0            # 0=no signal, 1=T1 (both), 2=T2 (MACD), 3=T3 (UC)
    # Week date from data
    week_date: str = ""

    # ── Legacy fields (kept for backward compat with daily scanner) ──────────
    banker: float = 0.0
    banker_prev: float = 0.0
    banker_rising: bool = False
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: dict = field(default_factory=dict)

    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""

    # ── Thematic analyzer fields ─────────────────────────────────────────────
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0
    theme_verdict: str = ""
    theme_classification: str = ""    # PRIME / INVESTABLE / SELECTIVE / AVOID
    valuation_regime: str = ""        # OPTIONALITY / FUNDAMENTAL / TRANSITION

    # ── Investment Gate fields (replaces Gatekeeper) ─────────────────────────
    final_decision: str = ""  # PASS, CONSIDER, SKIP (backward compat)
    conviction: int = 0       # 1-10 scale (new), 1-5 (legacy)
    gate_verdict: str = ""    # STRONG_BUY, SPEC_BUY, NO_GO
    gate_conviction: int = 0  # 1-10 from Investment Gate
    gate_catalyst: str = ""   # Key catalyst from gate
    gate_bear_case: str = ""  # Bear case from gate
    gate_math: str = ""       # Return math from gate
    sector_status: str = ""
    upside_potential: str = ""
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""
    catalyst_summary: str = ""
    red_flag_level: str = ""
    action: str = ""

    # ── Position sizing fields ───────────────────────────────────────────────
    position_size_pct: float = 0.0    # % of equity allocated
    position_dollars: float = 0.0     # Dollar amount allocated
    position_tier: str = ""           # T1 / T2 / T3 (quality tier label)
    sizing_gear: str = ""             # conservative / recommended / aggressive

    # ── Deep DD fields (Opus + extended thinking) ────────────────────────────
    dd_verdict: str = ""          # STRONG BUY / SPEC BUY / NO GO
    dd_conviction: int = 0        # 1-10 scale
    dd_position_size: str = ""    # FULL / REDUCED / PASS
    dd_analysis: str = ""
    dd_key_catalyst: str = ""
    dd_fatal_flaw: str = ""
    # DD newsletter content
    dd_elevator_pitch: str = ""
    dd_why_now: str = ""
    dd_the_math: str = ""
    dd_bear_case: str = ""
    dd_risk_to_monitor: str = ""
    dd_action: str = ""

    def meets_technical_criteria(self) -> bool:
        """Check if stock meets Sterling Grid V6 technical entry criteria.

        V6 entry: HMA(21) pivot low AND (UC rising OR MACD cross-up) AND Price < $25
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
    
    def passes_theme_gate(self) -> bool:
        """Check if passes thematic analyzer gate."""
        return self.theme_verdict in ["STRONG FIT", "GOOD FIT"]
    
    def is_confirmed(self) -> bool:
        """Check if confirmed by Investment Gate (PASS, CONSIDER, or PENDING_DD)."""
        return self.final_decision in ["PASS", "CONSIDER", "PENDING_DD", "TRADE"]


@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    # Sterling Grid V6 indicator stats
    price_under_cap: int = 0       # Price < $25
    hma_pivot_low: int = 0         # HMA(21) V-bottom pivot (V6 entry trigger)
    hma_slope_rising: int = 0      # HMA(21) slope rising (informational)
    rsi_above_50: int = 0          # RSI(14) > 50 (informational, not a gate)
    macd_cross_up: int = 0         # MACD single-bar cross-up
    uc_rising: int = 0             # V6: UC > UC.shift(1) (no >0 req)
    uc_rising_above: int = 0       # V4 legacy: UC > prev AND UC > 0
    buy_signal: int = 0            # V6: pivot + (UC OR MACD) + price
    exd_exit: int = 0              # V6: HMA pivot high + UC falling
    # Quality tier counts
    tier_t1: int = 0               # Both gates (UC + MACD)
    tier_t2: int = 0               # MACD only
    tier_t3: int = 0               # UC only
    # Legacy stats (kept for backward compat)
    beta_gte_1_5: int = 0
    bos_bullish: int = 0
    bos_bearish: int = 0
    banker_rising: int = 0
    meets_technical_gate: int = 0
    momentum_filtered: int = 0
    passes_momentum: int = 0
    technical_signals: int = 0  # Stocks passing full technical gate (buy_signal)
    theme_confirmed: int = 0
    final_trade: int = 0
    final_consider: int = 0
    final_skip: int = 0


@dataclass
class PipelineCostTracker:
    """P3: Track timing and estimated costs across the full pipeline."""
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
        print(f"  PIPELINE COST & TIMING SUMMARY")
        print(f"  " + "─" * 66)
        for step, secs in self.step_times.items():
            pct = (secs / total * 100) if total > 0 else 0
            mins = secs / 60
            print(f"    {step:<30} {mins:>5.1f}m  ({pct:>4.1f}%)")
        print(f"  " + "─" * 66)
        total_mins = total / 60
        print(f"    {'TOTAL':<30} {total_mins:>5.1f}m")
        print(f"  " + "─" * 66)
        print(f"  💡 Individual gate costs shown above in their respective sections")
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


# Legacy indicator functions (calculate_banker, calculate_hma, find_pivots, calculate_bos)
# have been moved to core/legacy_indicators.py for use by the daily scanner.
# The weekly scanner now uses Sterling Grid indicators from core/sterling_indicators.py.


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

                    # Price cap check (fast filter)
                    stock.price_under_cap = stock.price < PRICE_CAP

                    # Sterling Grid indicators (weekly timeframe)
                    # Only calculate full indicators for stocks under price cap
                    if stock.price_under_cap:
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
                                stock.rsi_above_50 = bool(cur['rsi_above_50'])
                                stock.macd_cross_up = bool(cur['macd_cross_up'])
                                stock.macd_line = round(float(cur['macd_line']), 4) if pd.notna(cur['macd_line']) else 0.0
                                stock.macd_signal_line = round(float(cur['signal_line']), 4) if pd.notna(cur['signal_line']) else 0.0
                                stock.macd_histogram = round(float(cur['macd_histogram']), 4) if pd.notna(cur['macd_histogram']) else 0.0
                                stock.uc = round(float(cur['uc']), 2) if pd.notna(cur['uc']) else 0.0
                                stock.uc_rising = bool(cur['uc_rising'])
                                stock.uc_rising_above = bool(cur['uc_rising_above'])
                                stock.buy_signal = bool(cur['buy_signal'])
                                stock.quality_tier = int(cur['quality_tier']) if pd.notna(cur['quality_tier']) else 0

                                # Exit signal (V6 ExD: HMA pivot high + UC falling)
                                exit_data = generate_exit_signal(weekly)
                                cur_exit = exit_data.iloc[-1]

                                stock.hma_slope_falling = bool(cur_exit['hma_slope_falling'])
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
# THEMATIC ANALYZER GATE
# ═══════════════════════════════════════════════════════════════════════════════

def run_thematic_gate(signals: List[Stock], use_web_search: bool = False) -> Tuple[List[Stock], str, List[dict]]:
    """Run thematic analyzer on signals. Returns stocks that pass theme gate, themes context, and themes data.
    
    The ThematicAnalyzer now prints comprehensive output directly to the terminal.
    This function coordinates the analysis and maps results back to Stock objects.
    
    Returns:
        Tuple of (confirmed_stocks, themes_context_string, themes_data_list)
    """
    
    if not signals:
        return [], "", []
    
    try:
        from scanner.thematic_analyzer import ThematicAnalyzer, Config
        
        print(f"\n  Initializing Thematic Analyzer...")
        if use_web_search:
            print(f"  ⚠️  Web search ENABLED - this adds ~$1-2 to run cost")
        else:
            print(f"  💰 Web search DISABLED (default) - using model knowledge only")
        
        config = Config()
        config.conservative_rate_limiting = True
        config.use_web_search = use_web_search  # Pass through web search setting
        
        # The analyzer prints comprehensive output for themes and tickers
        analyzer = ThematicAnalyzer(config=config, verbose=True)
        
        # Step 1: Identify themes (analyzer prints full comprehensive details)
        themes = analyzer.run_step_1()
        
        if not themes:
            print(f"  ⚠ No themes identified - passing all signals through")
            for s in signals:
                s.theme_verdict = "SKIPPED"
            return signals, "", []
        
        # Build themes context string for momentum assessor
        themes_context_lines = ["CURRENT HOT INVESTMENT THEMES (from prior thematic analysis):"]
        themes_context_lines.append("Use these themes - do NOT guess or invent different themes.\n")
        
        # Also build themes_data for newsletter briefing
        themes_data = []
        
        for t in themes:
            classification = getattr(t, 'classification', 'INVESTABLE')
            theme_type = getattr(t, 'theme_type', 'TREND')
            themes_context_lines.append(f"  #{t.rank} {t.name}")
            themes_context_lines.append(f"     Classification: {classification} | Type: {theme_type} | Score: {t.composite_score:.1f}/10")
            if t.thesis_summary:
                thesis_short = t.thesis_summary[:200] + "..." if len(t.thesis_summary) > 200 else t.thesis_summary
                themes_context_lines.append(f"     Thesis: {thesis_short}")
            themes_context_lines.append("")
            
            # Add to themes_data for newsletter
            themes_data.append({
                'name': t.name,
                'rank': t.rank,
                'classification': classification,
                'theme_type': theme_type,
                'composite_score': t.composite_score,
                'thesis_summary': getattr(t, 'thesis_summary', ''),
                'key_catalysts': getattr(t, 'key_catalysts', []),
                'momentum_score': getattr(t, 'momentum_score', 0),
                'catalyst_score': getattr(t, 'catalyst_score', 0),
                'valuation_regime': getattr(t, 'valuation_regime', ''),
            })
        
        themes_context = "\n".join(themes_context_lines)
        
        # Step 2: Analyze tickers (analyzer prints full comprehensive details)
        ticker_list = [s.symbol for s in signals]
        analyses = analyzer.run_step_2(ticker_list)
        
        # Map results back to Stock objects
        analysis_map = {a.ticker: a for a in analyses}
        
        confirmed = []
        rejected = []
        orphan_candidates = []  # Tickers that didn't fit top themes — candidates for rescue
        
        for stock in signals:
            if stock.symbol in analysis_map:
                a = analysis_map[stock.symbol]
                stock.theme = a.primary_theme or ""
                stock.theme_score = a.theme_score or 0.0
                stock.pure_play_score = a.pure_play_score
                stock.theme_verdict = a.verdict
                stock.theme_classification = getattr(a, 'theme_classification', 'INVESTABLE')

                # Look up valuation_regime from the Theme that matches this stock's theme
                for t in themes:
                    if t.name == stock.theme:
                        stock.valuation_regime = getattr(t, 'valuation_regime', '')
                        break

                # Check if passes gate
                if hasattr(a, 'passes_maturity_gate') and callable(a.passes_maturity_gate):
                    if a.passes_maturity_gate():
                        confirmed.append(stock)
                    else:
                        # Candidate for orphan rescue — didn't fit top themes
                        orphan_candidates.append(stock)
                        rejected.append(stock)
                elif a.passes_gate():
                    confirmed.append(stock)
                else:
                    # Candidate for orphan rescue — didn't fit top themes
                    orphan_candidates.append(stock)
                    rejected.append(stock)
            else:
                stock.theme_verdict = "NOT ANALYZED"
                orphan_candidates.append(stock)
                rejected.append(stock)
        
        # ─────────────────────────────────────────────────────────────────
        # Step 2b: ORPHAN RESCUE — Bottom-up theme discovery
        # For tickers that got WEAK/MODERATE FIT, check if they belong to
        # a different high-quality theme missed by the top-5 scan.
        # ─────────────────────────────────────────────────────────────────
        rescued_stocks = []
        if orphan_candidates:
            orphan_tickers = [s.symbol for s in orphan_candidates]
            try:
                rescued_analyses = analyzer.run_step_2b_orphan_rescue(orphan_tickers)
                rescued_map = {a.ticker: a for a in rescued_analyses if a.passes_gate()}
                
                for stock in orphan_candidates:
                    if stock.symbol in rescued_map:
                        a = rescued_map[stock.symbol]
                        # Update stock with rescued theme data
                        stock.theme = a.primary_theme or ""
                        stock.theme_score = a.theme_score or 0.0
                        stock.pure_play_score = a.pure_play_score
                        stock.theme_verdict = a.verdict + " [RESCUED]"
                        stock.theme_classification = getattr(a, 'theme_classification', 'INVESTABLE')
                        stock.valuation_regime = getattr(a, 'valuation_regime', '')
                        
                        # Move from rejected → confirmed
                        if stock in rejected:
                            rejected.remove(stock)
                        confirmed.append(stock)
                        rescued_stocks.append(stock)
            except Exception as e:
                print(f"  ⚠ Orphan rescue error (non-fatal): {e}")
                # Continue without rescue — original rejected list stands
        
        # Brief summary (detailed output already shown by analyzer)
        print(f"\n  {'═' * 70}")
        print(f"  THEMATIC GATE COMPLETE")
        print(f"  {'═' * 70}")
        print(f"    ✅ Passing to next stage: {len(confirmed)} stocks")
        if rescued_stocks:
            print(f"       (of which {len(rescued_stocks)} rescued via orphan path: {', '.join(s.symbol for s in rescued_stocks)})")
        print(f"    ❌ Filtered out: {len(rejected)} stocks")
        print(f"  {'─' * 70}")
        
        return confirmed, themes_context, themes_data
        
    except ImportError:
        print(f"  ⚠ thematic_analyzer.py not found - skipping theme gate")
        for s in signals:
            s.theme_verdict = "SKIPPED"
        return signals, "", []
    except RuntimeError as e:
        if "BILLING_ERROR" in str(e):
            print(f"\n  ❌ API BILLING ERROR DETECTED")
            print(f"     Your Anthropic API credit balance is too low.")
            print(f"     Please add credits at: https://console.anthropic.com/settings/billing")
            print(f"\n  ⏹️  Stopping pipeline to avoid wasted time.")
            print(f"\n  💡 TIP: Run with --no-llm to use technical signals only (FREE)")
            return [], "", []  # Return empty to stop pipeline
        raise
    except Exception as e:
        error_str = str(e).lower()
        # Check for billing errors in generic exceptions too
        if "credit balance" in error_str or "billing" in error_str:
            print(f"\n  ❌ API BILLING ERROR DETECTED")
            print(f"     Your Anthropic API credit balance is too low.")
            print(f"     Please add credits at: https://console.anthropic.com/settings/billing")
            print(f"\n  ⏹️  Stopping pipeline to avoid wasted time.")
            print(f"\n  💡 TIP: Run with --no-llm to use technical signals only (FREE)")
            return [], "", []  # Return empty to stop pipeline

        import traceback
        error_detail = traceback.format_exc()
        print(f"  ⚠ Theme analysis error: {e}")
        print(error_detail)

        # Log error to file for remote diagnosis
        try:
            from pathlib import Path
            error_log = Path("logs/thematic_error.log")
            error_log.parent.mkdir(exist_ok=True)
            from datetime import datetime
            with open(error_log, "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Thematic Analyzer Error: {datetime.now().isoformat()}\n")
                f.write(f"Error: {e}\n")
                f.write(error_detail)
        except Exception:
            pass

        # Retry once with fresh analyzer instance
        print(f"\n  🔄 Retrying thematic analysis with fresh instance...")
        try:
            config2 = Config()
            config2.conservative_rate_limiting = True
            config2.use_web_search = use_web_search
            analyzer2 = ThematicAnalyzer(config=config2, verbose=True)
            themes2 = analyzer2.run_step_1()
            if themes2:
                print(f"  ✅ Retry succeeded - {len(themes2)} themes identified")
                # Rebuild themes context and data
                themes_context_lines = ["CURRENT HOT INVESTMENT THEMES (from prior thematic analysis):"]
                themes_context_lines.append("Use these themes - do NOT guess or invent different themes.\n")
                themes_data = []
                for t in themes2:
                    classification = getattr(t, 'classification', 'INVESTABLE')
                    theme_type = getattr(t, 'theme_type', 'TREND')
                    themes_context_lines.append(f"  #{t.rank} {t.name}")
                    themes_context_lines.append(f"     Classification: {classification} | Type: {theme_type} | Score: {t.composite_score:.1f}/10")
                    if t.thesis_summary:
                        thesis_short = t.thesis_summary[:200] + "..." if len(t.thesis_summary) > 200 else t.thesis_summary
                        themes_context_lines.append(f"     Thesis: {thesis_short}")
                    themes_context_lines.append("")
                    themes_data.append({
                        'name': t.name, 'rank': t.rank, 'classification': classification,
                        'theme_type': theme_type, 'composite_score': t.composite_score,
                        'thesis_summary': getattr(t, 'thesis_summary', ''),
                        'key_catalysts': getattr(t, 'key_catalysts', []),
                        'momentum_score': getattr(t, 'momentum_score', 0),
                        'catalyst_score': getattr(t, 'catalyst_score', 0),
                    })
                themes_context = "\n".join(themes_context_lines)
                # Run step 2
                ticker_list = [s.symbol for s in signals]
                analyses = analyzer2.run_step_2(ticker_list)
                analysis_map = {a.ticker: a for a in analyses}
                confirmed = []
                rejected = []
                orphan_candidates2 = []
                for stock in signals:
                    if stock.symbol in analysis_map:
                        a = analysis_map[stock.symbol]
                        stock.theme = a.primary_theme or ""
                        stock.theme_score = a.theme_score or 0.0
                        stock.pure_play_score = a.pure_play_score
                        stock.theme_verdict = a.verdict
                        if hasattr(a, 'passes_maturity_gate') and callable(a.passes_maturity_gate):
                            if a.passes_maturity_gate():
                                confirmed.append(stock)
                            else:
                                orphan_candidates2.append(stock)
                                rejected.append(stock)
                        elif a.passes_gate():
                            confirmed.append(stock)
                        else:
                            orphan_candidates2.append(stock)
                            rejected.append(stock)
                    else:
                        stock.theme_verdict = "NOT ANALYZED"
                        orphan_candidates2.append(stock)
                        rejected.append(stock)
                # Orphan rescue on retry path
                if orphan_candidates2:
                    try:
                        orphan_tickers2 = [s.symbol for s in orphan_candidates2]
                        rescued2 = analyzer2.run_step_2b_orphan_rescue(orphan_tickers2)
                        rescued_map2 = {a.ticker: a for a in rescued2 if a.passes_gate()}
                        for stock in orphan_candidates2:
                            if stock.symbol in rescued_map2:
                                a = rescued_map2[stock.symbol]
                                stock.theme = a.primary_theme or ""
                                stock.theme_score = a.theme_score or 0.0
                                stock.pure_play_score = a.pure_play_score
                                stock.theme_verdict = a.verdict + " [RESCUED]"
                                stock.theme_classification = getattr(a, 'theme_classification', 'INVESTABLE')
                                stock.valuation_regime = getattr(a, 'valuation_regime', '')
                                if stock in rejected:
                                    rejected.remove(stock)
                                confirmed.append(stock)
                    except Exception:
                        pass  # Continue without rescue on retry
                return confirmed, themes_context, themes_data
        except Exception as e2:
            print(f"  ⚠ Retry also failed: {e2}")

        # Both attempts failed - pass stocks through with ERROR verdict
        for s in signals:
            s.theme_verdict = "ERROR"
        return signals, "", []


# ═══════════════════════════════════════════════════════════════════════════════
# INVESTMENT GATE - REGIME-AWARE QUALITY GATE
# ═══════════════════════════════════════════════════════════════════════════════

def run_investment_gate_step(signals: List[Stock], top_n: int = None, themes_context: str = "", use_web_search: bool = False, save_reports: bool = False) -> List[Stock]:
    """Run Investment Gate analysis for final STRONG_BUY/SPEC_BUY/NO_GO decision.

    Regime-aware quality gate that adapts analysis to valuation context:
    - OPTIONALITY: Milestone-based (pre-revenue, narrative-driven)
    - FUNDAMENTAL: Revenue/earnings-based (established companies)
    - TRANSITION: Shifting from milestone to revenue (highest risk)

    Args:
        signals: List of stocks that passed theme gate
        top_n: If set, only assess top N stocks by Banker score
        themes_context: Pre-identified themes from thematic analyzer
        use_web_search: If True, use web search for current data (recommended for production)
        save_reports: If True, save individual assessment reports

    Returns:
        List of stocks that PASS the gate (STRONG_BUY or SPEC_BUY)
    """

    if not signals:
        return []

    # If top_n specified, only assess highest conviction candidates
    if top_n and len(signals) > top_n:
        signals = sorted(signals, key=lambda s: -s.uc)[:top_n]
        print(f"\n  Assessing top {top_n} candidates by UC (accumulation strength)")

    try:
        from scanner.investment_gate import (
            run_investment_gate_batch, create_client, apply_results_to_stocks
        )

        client = create_client()

        # run_investment_gate_batch handles printing and per-stock display
        results = run_investment_gate_batch(
            client=client,
            stocks=signals,
            themes_context=themes_context,
            use_web_search=use_web_search,
            delay_between=8.0 if use_web_search else 3.0,
            save_reports=save_reports
        )

        # apply_results_to_stocks maps all fields back to Stock objects
        # (final_decision, conviction, catalyst_summary, red_flag_level, etc.)
        pass_stocks, fail_stocks = apply_results_to_stocks(signals, results)

        # Mark stocks not in pass/fail as ERROR
        passed_tickers = {s.symbol for s in pass_stocks}
        failed_tickers = {s.symbol for s in fail_stocks}
        for s in signals:
            if s.symbol not in passed_tickers and s.symbol not in failed_tickers:
                if not s.final_decision:
                    s.final_decision = "ERROR"
                    s.reasoning = "Investment Gate analysis failed"

        # Return PASS + CONSIDER (is_confirmed checks for both)
        confirmed = [s for s in signals if s.is_confirmed()]
        return confirmed

    except ImportError as e:
        print(f"  investment_gate.py not found - falling back to basic assessment")
        print(f"     Error: {e}")
        for s in signals:
            s.final_decision = "SKIPPED"
        return signals

    except RuntimeError as e:
        if "BILLING_ERROR" in str(e):
            print(f"\n  API BILLING ERROR DETECTED")
            print(f"     Your Anthropic API credit balance is too low.")
            print(f"     Please add credits at: https://console.anthropic.com/settings/billing")
            print(f"\n  Stopping Investment Gate analysis.")
        else:
            print(f"  Investment Gate error: {e}")
        for s in signals:
            s.final_decision = "NOT_ASSESSED"
        return []

    except Exception as e:
        print(f"  Investment Gate error: {e}")
        import traceback
        traceback.print_exc()
        for s in signals:
            s.final_decision = "ERROR"
        return signals


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
    if PORTFOLIO_MANAGER_AVAILABLE:
        try:
            return get_open_position_symbols()
        except Exception:
            return set()
    return set()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level pipeline cost tracker (P3)
_pipeline_timer = PipelineCostTracker()

def run_scan(skip_llm: bool = False, skip_momentum: bool = False, assess_top_n: int = None, top_n: int = None, use_web_search: bool = False, verbose: bool = False) -> Tuple[List[Stock], List[Stock], List[SellSignal], ScanStats, List[Stock], List[dict]]:
    """Run the complete scan pipeline. Returns (confirmed_buys, all_assessed, sell_signals, stats, momentum_rejected, themes_data).

    Args:
        skip_llm: Skip ALL LLM gates (technical only)
        skip_momentum: Skip momentum assessor but keep theme analysis
        verbose: Show detailed diagnostic output (10 items vs 3)
        assess_top_n: Only run momentum assessor on top N stocks
        top_n: Only scan top N stocks by beta
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
        return [], [], [], stats, [], []
    
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
            return [], [], [], stats, [], []
        
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        if 'Close' not in spy.columns:
            print("  ✗ SPY data missing 'Close' column after download")
            return [], [], [], stats, [], []

        benchmark_returns = spy['Close'].pct_change().dropna()
        print(f"  ✓ SPY data: {len(benchmark_returns)} days")
    except Exception as e:
        print(f"  ✗ Benchmark error: {e}")
        return [], [], [], stats, [], []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Download Data & Calculate Indicators
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 3: Downloading Data & Calculating Indicators (Sterling Grid)")
    print("─" * 70)
    
    # GAP 30 fix: Add error handling for data download
    try:
        stocks = download_and_process(tickers, benchmark_returns)
        stats.data_downloaded = len(stocks)

        # Validate we got a reasonable amount of data
        expected_count = len(tickers)
        if len(stocks) < expected_count * 0.3:  # Less than 30% downloaded
            print(f"  ⚠️ WARNING: Only {len(stocks)}/{expected_count} tickers downloaded ({len(stocks)/expected_count*100:.1f}%)")
            print(f"     This may indicate yfinance API issues")
    except Exception as e:
        print(f"  ❌ ERROR: Data download failed: {e}")
        print(f"     Cannot continue without stock data")
        return [], [], [], stats, [], []

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Calculate Statistics (Sterling Grid indicators)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 4: Sterling Grid Indicator Statistics")
    print("─" * 70)

    # Count Sterling Grid V6 indicator stats
    eligible_stocks = []  # Stocks under price cap (eligible for entry)

    for stock in stocks.values():
        if stock.price_under_cap:
            stats.price_under_cap += 1
            eligible_stocks.append(stock)
        if stock.hma_pivot_low:
            stats.hma_pivot_low += 1
        if stock.hma_slope_rising:
            stats.hma_slope_rising += 1
        if stock.rsi_above_50:
            stats.rsi_above_50 += 1
        if stock.macd_cross_up:
            stats.macd_cross_up += 1
        if stock.uc_rising:
            stats.uc_rising += 1
        if stock.uc_rising_above:
            stats.uc_rising_above += 1
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
        # Legacy stats for backward compat
        if stock.beta >= BETA_MIN:
            stats.beta_gte_1_5 += 1

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
        print(f"  Price < ${PRICE_CAP:.0f}:            {stats.price_under_cap:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  HMA pivot low (V6):       {stats.hma_pivot_low:>6}")
        print(f"  HMA slope rising:         {stats.hma_slope_rising:>6}  (informational)")
        print(f"  RSI(14) > 50:             {stats.rsi_above_50:>6}  (informational)")
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
        print(f"  Price qualified:          {stats.price_under_cap:>6}")
        print(f"  ────────────────────────────────────")
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
            print(f"      {s.symbol:<6} ${s.price:<8.2f} UC={s.uc:.1f} HMA={'⌃' if s.hma_pivot_high else '↓' if s.hma_slope_falling else '↑'}")

    # Entry candidates under price cap with buy signal
    buy_under_cap = [s for s in eligible_stocks if s.buy_signal]
    if verbose:
        print(f"\n  ⭐ ENTRY CANDIDATES (V6 Signal + <${PRICE_CAP:.0f}): {len(buy_under_cap)}")
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
    print(f"\n  📊 Entry (V6): HMA pivot↓ + (UC rising OR MACD cross-up) + Price<${PRICE_CAP:.0f}")

    technical_signals = []
    momentum_rejected = []  # Kept for backwards compatibility (always empty)

    for stock in eligible_stocks:
        if stock.meets_technical_criteria():
            stats.meets_technical_gate += 1
            stock.tier = stock.get_tier()
            if stock.tier:
                technical_signals.append(stock)
                stats.technical_signals += 1

    print(f"\n  STERLING GRID V6 GATE RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Price < ${PRICE_CAP:.0f} eligible:      {len(eligible_stocks):>5}")
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
        return [], [], sell_signals, stats, momentum_rejected, []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Thematic Analyzer Gate
    # ─────────────────────────────────────────────────────────────────────────
    _pipeline_timer.stop()  # Stop Steps 1-5 timing
    themes_data = []  # Initialize for newsletter briefing

    if skip_llm:
        print(f"\n  Steps 6-7: SKIPPED (--no-llm)")
        theme_confirmed = technical_signals
        themes_context = ""
        for s in theme_confirmed:
            s.theme_verdict = "SKIPPED"
    else:
        print("\n" + "─" * 70)
        print("  STEP 6: Thematic Analyzer Gate")
        print("─" * 70)
        
        _pipeline_timer.start("Step 6: Thematic Gate")
        theme_confirmed, themes_context, themes_data = run_thematic_gate(technical_signals, use_web_search=use_web_search)
        _pipeline_timer.stop()  # Stop thematic timing
        stats.theme_confirmed = len(theme_confirmed)
        
        print(f"\n  THEME GATE RESULTS:")
        print(f"  ────────────────────────────────────")
        print(f"  Technical signals:         {len(technical_signals):>5}")
        print(f"  Theme confirmed:           {len(theme_confirmed):>5}")
        
        if len(technical_signals) > 0:
            rate = len(theme_confirmed) / len(technical_signals) * 100
            print(f"  Confirmation rate:         {rate:>4.1f}%")
    
    if not theme_confirmed:
        print("\n  No signals passed theme gate")
        sell_signals = check_sell_signals(stocks)
        return [], [], sell_signals, stats, momentum_rejected, themes_data
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Momentum Assessor Final Decision
    # ─────────────────────────────────────────────────────────────────────────
    if skip_llm or skip_momentum:
        # Set decisions (step header already shown if skip_llm)
        confirmed = theme_confirmed
        for s in confirmed:
            if skip_llm:
                s.final_decision = "TECHNICAL_ONLY"
            else:
                s.final_decision = "THEME_CONFIRMED"

        # Only show step 7 header if we ran step 6 (skip_momentum but not skip_llm)
        if skip_momentum and not skip_llm:
            print(f"\n  Step 7: SKIPPED (--no-momentum)")

        # Show candidates summary
        print(f"\n  📊 ENTRY CANDIDATES: {len(confirmed)} passed filters")
        sorted_confirmed = sorted(confirmed, key=lambda x: -x.uc)
        for s in sorted_confirmed[:5]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"     {s.symbol:<6} | {s.tier} | UC={s.uc:.1f} | RSI={s.rsi14:.0f} | MACD={'✓' if s.macd_cross_up else '✗'} | 20d={s.return_20d:+.1f}%{held_flag}")
        if len(sorted_confirmed) > 5:
            print(f"     ... and {len(sorted_confirmed) - 5} more")
    else:
        print("\n" + "─" * 70)
        print("  STEP 7: Investment Gate - Regime-Aware Quality Gate")
        print("─" * 70)
        
        # Cooldown after thematic analyzer to avoid rate limits
        cooldown_seconds = 30 if use_web_search else 15
        print(f"\n  Rate limit cooldown: waiting {cooldown_seconds}s before Investment Gate...")
        time.sleep(cooldown_seconds)
        
        # Run Investment Gate - regime-aware quality gate
        _pipeline_timer.start("Step 7: Investment Gate")
        confirmed = run_investment_gate_step(
            theme_confirmed,
            top_n=assess_top_n,
            themes_context=themes_context,
            use_web_search=use_web_search
        )
        _pipeline_timer.stop()
        
        for s in theme_confirmed:
            if s.final_decision in ["PASS", "TRADE"]:
                stats.final_trade += 1
            elif s.final_decision == "CONSIDER":
                stats.final_consider += 1
            elif s.final_decision != "NOT_ASSESSED":
                stats.final_skip += 1
        
        print(f"\n  FINAL DECISION RESULTS:")
        print(f"  ────────────────────────────────────")
        print(f"  Theme confirmed:           {len(theme_confirmed):>5}")
        print(f"  PASS (GREEN signals):      {stats.final_trade:>5}")
        print(f"  CONSIDER:                  {stats.final_consider:>5}")
        print(f"  SKIP:                      {stats.final_skip:>5}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Check Sell Signals (ExD compound exit OR tiered profit lock)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 8: Checking Sell Signals (ExD Pivot High exit OR Tiered Profit Lock)")
    print("─" * 70)
    
    sell_signals = check_sell_signals(stocks)
    
    if sell_signals:
        print(f"  ⚠ {len(sell_signals)} SELL SIGNAL(S):")
        for s in sell_signals:
            print(f"    🔴 {s.symbol} @ ${s.price:.2f} - {s.reason}")
    else:
        print(f"  ✓ No sell signals")
    
    # ─────────────────────────────────────────────────────────────────────────
    # NOTE: Portfolio updates now happen AFTER DD step in main()
    # This ensures only DD-PASS signals get added to portfolio
    # ─────────────────────────────────────────────────────────────────────────
    
    # Return: confirmed (PASS/CONSIDER), all_assessed (theme_confirmed), sell_signals, stats, momentum_rejected
    return confirmed, theme_confirmed, sell_signals, stats, momentum_rejected, themes_data


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def print_final_report(confirmed: List[Stock], sell_signals: List[SellSignal], stats: ScanStats):
    """Print final summary report with full details (no truncation)."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "FINAL REPORT".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    if confirmed:
        # Separate by decision — P0: PENDING_DD is its own bucket
        trades = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        pending_dd = [s for s in confirmed if s.final_decision == "PENDING_DD"]
        considers = [s for s in confirmed if s.final_decision == "CONSIDER"]
        
        # P2: Split trades into BUY NOW (STRONG_BUY) vs BUY ON PULLBACK (SPEC_BUY)
        buy_now = [s for s in trades if s.gate_verdict == "STRONG_BUY"]
        buy_pullback = [s for s in trades if s.gate_verdict == "SPEC_BUY"]
        buy_other = [s for s in trades if s.gate_verdict not in ("STRONG_BUY", "SPEC_BUY")]
        
        def _print_stock_detail(s, label_override=None):
            """Print a single stock's full details with tier sizing."""
            conv = min(s.conviction, 10)
            stars = "★" * conv + "☆" * (10 - conv)
            alloc = TIER_ALLOC.get(s.tier, 0)
            rescued_tag = " [RESCUED]" if "[RESCUED]" in (s.theme_verdict or "") else ""
            
            print(f"\n  {s.symbol} | {s.tier} ({alloc}% equity) | ${s.price:.2f}{rescued_tag}")
            print(f"  Conviction: {stars} ({conv}/10)")
            if s.gate_verdict:
                gate_label = label_override or s.gate_verdict.replace("_", " ")
                print(f"  Gate: {gate_label} | UC={s.uc:.1f} | RSI={s.rsi14:.0f} (info)")
                print(f"  V6 Entry: Pivot={'✓' if s.hma_pivot_low else '✗'} | UC_rising={'✓' if s.uc_rising else '✗'} | MACD={'✓' if s.macd_cross_up else '✗'}")
            print(f"  Theme: {s.theme or 'N/A'} ({s.theme_verdict})")
            if s.gate_catalyst or s.catalyst_summary:
                print(f"  📅 Catalyst: {s.gate_catalyst or s.catalyst_summary}")
            if s.red_flag_level:
                print(f"  🚦 Red Flags: {s.red_flag_level}")
            if s.bullish_factors:
                print(f"  ✅ Key Bullish:")
                for factor in s.bullish_factors[:3]:
                    print(f"     • {factor}")
            if s.reasoning:
                print(f"  📝 Analysis:")
                _print_wrapped(s.reasoning, indent=5, width=70)
            if s.action:
                print(f"  ➡️  Action: {s.action}")
        
        # ── BUY NOW section (STRONG_BUY — immediate entry) ──
        if buy_now:
            print(f"\n  🟢 BUY NOW ({len(buy_now)}) — Enter Monday open:")
            print("  " + "─" * 66)
            for s in buy_now:
                _print_stock_detail(s, "STRONG BUY")
        
        # ── BUY ON PULLBACK section (SPEC_BUY — conditional entry) ──
        if buy_pullback:
            print(f"\n  🟡 BUY ON PULLBACK ({len(buy_pullback)}) — Wait for entry level:")
            print("  " + "─" * 66)
            for s in buy_pullback:
                _print_stock_detail(s, "SPEC BUY")
        
        # ── Other trades (gate_verdict not STRONG/SPEC — shouldn't happen often) ──
        if buy_other:
            print(f"\n  🟢 PASS ({len(buy_other)}) - Ready for entry:")
            print("  " + "─" * 66)
            for s in buy_other:
                _print_stock_detail(s)

        # ── P0: PENDING DD section — passed gates but DD failed/skipped ──
        if pending_dd:
            print(f"\n  ⚠️  PENDING DD ({len(pending_dd)}) — DO NOT TRADE until DD completes:")
            print("  " + "─" * 66)
            print("  These stocks passed technical + thematic + investment gates but")
            print("  Deep DD failed or was skipped. Re-run with DD before entering.")
            for s in pending_dd:
                alloc = TIER_ALLOC.get(s.tier, 0)
                conv = min(s.conviction, 10)
                stars = "★" * conv + "☆" * (10 - conv)
                dd_reason = s.dd_verdict if s.dd_verdict else "Not run"
                print(f"\n  {s.symbol} | {s.tier} ({alloc}% equity) | ${s.price:.2f}")
                print(f"  Conviction: {stars} ({conv}/10) | DD: {dd_reason}")
                print(f"  Gate: {s.gate_verdict or 'N/A'}")
                print(f"  Theme: {s.theme or 'N/A'} ({s.theme_verdict})")
                if s.gate_catalyst or s.catalyst_summary:
                    print(f"  📅 Catalyst: {s.gate_catalyst or s.catalyst_summary}")
                if s.action:
                    print(f"  ➡️  Action (from gate): {s.action}")

        # ── CONSIDER section ──
        if considers:
            print(f"\n  🟡 CONSIDER ({len(considers)}) - Wait or size down:")
            print("  " + "─" * 66)

            for s in considers:
                conv = min(s.conviction, 10)
                stars = "★" * conv + "☆" * (10 - conv)
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"\n  {s.symbol} | {s.tier} ({alloc}% equity) | ${s.price:.2f}")
                print(f"  Conviction: {stars} ({conv}/10)")
                print(f"  Theme: {s.theme or 'N/A'} ({s.theme_verdict})")
                if s.catalyst_summary:
                    print(f"  📅 Catalyst: {s.catalyst_summary}")
                if s.risk_factors:
                    print(f"  ⚠️ Concerns:")
                    for risk in s.risk_factors[:3]:
                        print(f"     • {risk}")
                if s.reasoning:
                    print(f"  📝 Analysis:")
                    _print_wrapped(s.reasoning, indent=5, width=70)
                if s.action:
                    print(f"  ➡️  Action: {s.action}")
        
        # ── ACTION SUMMARY with sizing ──
        print("\n  " + "─" * 66)
        print(f"\n  ACTION SUMMARY:")
        if buy_now:
            for s in buy_now:
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"    🟢 BUY NOW:     {s.symbol:<8} {s.tier} ({alloc}% equity)")
        if buy_pullback:
            for s in buy_pullback:
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"    🟡 ON PULLBACK: {s.symbol:<8} {s.tier} ({alloc}% equity)")
        if buy_other:
            for s in buy_other:
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"    🟢 PASS:        {s.symbol:<8} {s.tier} ({alloc}% equity)")
        if pending_dd:
            for s in pending_dd:
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"    ⚠️  PENDING DD:  {s.symbol:<8} {s.tier} ({alloc}% equity) — re-run DD before trading")
        if considers:
            for s in considers:
                alloc = TIER_ALLOC.get(s.tier, 0)
                print(f"    🟡 CONSIDER:    {s.symbol:<8} {s.tier} ({alloc}% equity)")
        if not (buy_now or buy_pullback or buy_other or pending_dd or considers):
            print("    No actionable signals this week")
        
        # Total allocation summary
        total_alloc = sum(TIER_ALLOC.get(s.tier, 0) for s in buy_now)
        total_alloc_pullback = sum(TIER_ALLOC.get(s.tier, 0) for s in buy_pullback)
        total_alloc_pending = sum(TIER_ALLOC.get(s.tier, 0) for s in pending_dd)
        if total_alloc or total_alloc_pullback or total_alloc_pending:
            parts = []
            if total_alloc:
                parts.append(f"{total_alloc}% immediate")
            if total_alloc_pullback:
                parts.append(f"{total_alloc_pullback}% on pullback")
            if total_alloc_pending:
                parts.append(f"{total_alloc_pending}% pending DD")
            print(f"\n    💰 Total equity deployment: {' + '.join(parts)}")
        
    else:
        print("\n  NO CONFIRMED BUY SIGNALS")
        print("\n  Pipeline summary:")
        print(f"    • {stats.tickers_loaded} tickers scanned")
        print(f"    • {stats.price_under_cap} under ${PRICE_CAP:.0f} price cap")
        print(f"    • {stats.buy_signal} with full buy signal (V6 pivot + gate)")
        print(f"    • {stats.meets_technical_gate} met technical gate")
        print(f"    • {stats.theme_confirmed} passed theme gate")
        print(f"    • {stats.final_trade} PASS (GREEN), {stats.final_consider} CONSIDER, {stats.final_skip} SKIP")
    
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


def _print_wrapped(text: str, indent: int = 5, width: int = 70):
    """Helper to print text with word wrapping."""
    words = text.split()
    line = " " * indent
    for word in words:
        if len(line) + len(word) + 1 > width:
            print(line)
            line = " " * indent + word
        else:
            line += " " + word if line.strip() else " " * indent + word
    if line.strip():
        print(line)


def generate_report(confirmed: List[Stock], all_assessed: List[Stock], 
                   sell_signals: List[SellSignal], stats: ScanStats,
                   momentum_rejected: List[Stock] = None) -> str:
    """
    Generate a comprehensive, professional report of scan results.
    
    Returns formatted text suitable for email and file output.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_display = datetime.now().strftime("%A, %B %d, %Y")
    
    # Separate by decision type
    trades = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]] if confirmed else []
    pending_dd = [s for s in confirmed if s.final_decision == "PENDING_DD"] if confirmed else []
    considers = [s for s in confirmed if s.final_decision == "CONSIDER"] if confirmed else []
    technical_only = [s for s in confirmed if s.final_decision == "TECHNICAL_ONLY"] if confirmed else []
    theme_confirmed = [s for s in confirmed if s.final_decision == "THEME_CONFIRMED"] if confirmed else []
    
    # P2: Split trades into BUY NOW vs BUY ON PULLBACK
    buy_now = [s for s in trades if s.gate_verdict == "STRONG_BUY"]
    buy_pullback = [s for s in trades if s.gate_verdict == "SPEC_BUY"]
    buy_other = [s for s in trades if s.gate_verdict not in ("STRONG_BUY", "SPEC_BUY")]
    
    lines = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("=" * 72)
    lines.append("  BoS MOMENTUM SCANNER V6 - WEEKLY REPORT")
    lines.append(f"  {date_display}")
    lines.append(f"  Generated: {timestamp}")
    lines.append("=" * 72)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  EXECUTIVE SUMMARY")
    lines.append("─" * 72)
    
    total_signals = len(trades) + len(pending_dd) + len(considers) + len(technical_only) + len(theme_confirmed)
    if total_signals > 0:
        lines.append(f"  ✅ {total_signals} entry signal(s) identified")
        if buy_now:
            allocs = [f"{s.symbol} ({s.tier}, {TIER_ALLOC.get(s.tier, 0)}%)" for s in buy_now]
            lines.append(f"     • {len(buy_now)} BUY NOW: {', '.join(allocs)}")
        if buy_pullback:
            allocs = [f"{s.symbol} ({s.tier}, {TIER_ALLOC.get(s.tier, 0)}%)" for s in buy_pullback]
            lines.append(f"     • {len(buy_pullback)} BUY ON PULLBACK: {', '.join(allocs)}")
        if buy_other:
            lines.append(f"     • {len(buy_other)} PASS (GREEN signals)")
        if pending_dd:
            lines.append(f"     • ⚠ {len(pending_dd)} PENDING DD - Do NOT trade until DD completes")
        if considers:
            lines.append(f"     • {len(considers)} CONSIDER - Smaller position recommended")
        if theme_confirmed:
            lines.append(f"     • {len(theme_confirmed)} THEME CONFIRMED - Pending momentum assessment")
        if technical_only:
            lines.append(f"     • {len(technical_only)} TECHNICAL ONLY - Pending LLM analysis")
    else:
        lines.append("  ⚪ No entry signals this week")
    
    if sell_signals:
        lines.append(f"  🔴 {len(sell_signals)} exit signal(s) - Positions closed")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCAN STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  SCAN STATISTICS")
    lines.append("─" * 72)
    lines.append(f"  Universe scanned:          {stats.tickers_loaded:>6}")
    lines.append(f"  Data retrieved:            {stats.data_downloaded:>6}")
    lines.append(f"  Price < ${PRICE_CAP:.0f}:             {stats.price_under_cap:>6}")
    lines.append("")
    lines.append(f"  HMA pivot low (V6):        {stats.hma_pivot_low:>6}")
    lines.append(f"  MACD cross-up:             {stats.macd_cross_up:>6}")
    lines.append(f"  UC rising (V6):            {stats.uc_rising:>6}")
    lines.append(f"  Buy signal (V6):           {stats.buy_signal:>6}")
    lines.append(f"  Met technical gate:        {stats.meets_technical_gate:>6}")
    lines.append(f"  Theme confirmed:           {stats.theme_confirmed:>6}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY SIGNALS
    # ═══════════════════════════════════════════════════════════════════════════
    if trades or pending_dd or considers or technical_only or theme_confirmed:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ENTRY SIGNALS")
        lines.append("─" * 72)

        # Table header — P2: added ALLOC% column
        lines.append("")
        lines.append(f"  {'TIER':<6} {'%EQ':>4} {'SYMBOL':<7} {'PRICE':>9} {'UC':>6} {'MACD':>5} {'UC↑':>4} {'STATUS':<12} {'THEME':<16}")
        lines.append("  " + "-" * 72)

        all_entry_signals = trades + pending_dd + considers + technical_only + theme_confirmed
        all_entry_signals.sort(key=lambda x: -x.uc)

        for s in all_entry_signals:
            theme_short = (s.theme[:14] + "..") if s.theme and len(s.theme) > 16 else (s.theme or "N/A")
            macd_flag = "✓" if s.macd_cross_up else "✗"
            uc_flag = "✓" if s.uc_rising else "✗"
            alloc = TIER_ALLOC.get(s.tier, 0)
            # Determine status label
            if s.final_decision == "PENDING_DD":
                status = "PENDING DD"
            elif s.gate_verdict == "STRONG_BUY":
                status = "BUY NOW"
            elif s.gate_verdict == "SPEC_BUY":
                status = "PULLBACK"
            elif s.final_decision in ("PASS", "TRADE"):
                status = "PASS"
            elif s.final_decision == "CONSIDER":
                status = "CONSIDER"
            else:
                status = s.final_decision or "PASSED"
            lines.append(f"  {s.tier:<6} {alloc:>3}% {s.symbol:<7} ${s.price:>7.2f} {s.uc:>6.1f} {macd_flag:>5} {uc_flag:>4} {status:<12} {theme_short:<16}")

        # Detailed breakdown for each signal
        lines.append("")
        lines.append("  SIGNAL DETAILS:")
        lines.append("  " + "-" * 72)

        for s in all_entry_signals:
            alloc = TIER_ALLOC.get(s.tier, 0)
            if s.final_decision == "PENDING_DD":
                decision_label = "PENDING DD — re-run DD before trading"
            elif s.gate_verdict == "STRONG_BUY":
                decision_label = "BUY NOW"
            elif s.gate_verdict == "SPEC_BUY":
                decision_label = "BUY ON PULLBACK"
            else:
                decision_label = s.final_decision if s.final_decision else "PASSED"
            lines.append(f"")
            lines.append(f"  ■ {s.symbol} ({s.tier}, {alloc}% equity) - {decision_label}")
            lines.append(f"    Price: ${s.price:.2f} | UC: {s.uc:.1f} | RSI: {s.rsi14:.0f} (info) | MACD: {'cross-up' if s.macd_cross_up else 'no'}")
            lines.append(f"    V6: Pivot={'✓' if s.hma_pivot_low else '✗'} | UC_rising={'✓' if s.uc_rising else '✗'} | MACD={'✓' if s.macd_cross_up else '✗'} | 20d: {s.return_20d:+.1f}%")
            if s.theme:
                lines.append(f"    Theme: {s.theme}")
                lines.append(f"    Theme Verdict: {s.theme_verdict} | Pure Play: {s.pure_play_score}%")
            if s.reasoning:
                # Wrap reasoning text
                reasoning = s.reasoning[:200] + "..." if len(s.reasoning) > 200 else s.reasoning
                lines.append(f"    Analysis: {reasoning}")
            if s.bullish_factors:
                lines.append(f"    Bullish: {'; '.join(s.bullish_factors[:3])}")
            if s.risk_factors:
                lines.append(f"    Risks: {'; '.join(s.risk_factors[:3])}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MOMENTUM FILTERED (Rejected for chasing)
    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    # EXIT SIGNALS (Sell signals from existing positions)
    # ═══════════════════════════════════════════════════════════════════════════
    if sell_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  🔴 EXIT SIGNALS - Positions Closed")
        lines.append("─" * 72)
        lines.append("  First exit strategy: whichever fires first closes the position.")
        lines.append("")

        for s in sell_signals:
            lines.append(f"  ■ {s.symbol} @ ${s.price:.2f}")
            lines.append(f"    Reason: {s.reason}")
            if s.entry_price > 0:
                pnl = ((s.price / s.entry_price) - 1) * 100
                lines.append(f"    Entry: ${s.entry_price:.2f} | High: ${s.highest_close:.2f} | P&L: {pnl:+.1f}%")
            lines.append(f"    Action: Position closed at current price")
            lines.append("")

    # ═══════════════════════════════════════════════════════════════════════════
    # EXIT STRATEGY REMINDER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  EXIT STRATEGY (first exit — whichever fires first)")
    lines.append("─" * 72)
    lines.append("  1. ExD compound exit (HMA PIVOT HIGH + UC falling) = immediate exit")
    lines.append("  2. Tiered profit lock (return-based trailing stop):")
    lines.append("     • >= +200% return: 15% trail from peak")
    lines.append("     • >= +100% return: 20% trail from peak")
    lines.append("     • >= +50% return:  25% trail from peak")
    lines.append("     • Below +50%: only ExD can trigger exit")
    lines.append("")
    lines.append("  Whichever fires first closes the position.")

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY CRITERIA REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  ENTRY CRITERIA REFERENCE (Sterling Grid V6)")
    lines.append("─" * 72)
    lines.append(f"  1. Price < ${PRICE_CAP:.0f} (price cap)")
    lines.append("  2. HMA(21) PIVOT LOW — V-bottom confirmation")
    lines.append("  3. At least ONE confirmation gate:")
    lines.append("     a. UC rising (institutional accumulation)")
    lines.append("     b. MACD(12,26,9) cross-up (timing confirmation)")
    lines.append("  RSI(14) computed for informational display, NOT an entry gate.")
    lines.append("")
    lines.append("  QUALITY TIERS (at signal bar):")
    lines.append("  T1: UC rising AND MACD cross-up → 20% equity")
    lines.append("  T2: MACD cross-up only          → 10% equity")
    lines.append("  T3: UC rising only               →  5% equity")
    lines.append("  Max 8 concurrent positions.")
    lines.append("")
    lines.append("  V6 entry fires on pivot + gate. Plus theme + Investment Gate.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("=" * 72)
    lines.append("  End of Report")
    lines.append("=" * 72)
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# NEWSLETTER BRIEFING GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_newsletter_briefing(
    confirmed: List[Stock], 
    sell_signals: List[SellSignal], 
    themes_data: List[dict] = None,
    stats: ScanStats = None
) -> str:
    """
    Generate a markdown document for the weekly newsletter.
    
    This document is designed to be:
    1. Pasted into Claude for due diligence analysis
    2. Used as a template for the Substack newsletter
    
    Args:
        confirmed: List of stocks that passed all gates
        sell_signals: List of sell signals for open positions
        themes_data: List of theme dictionaries from thematic analyzer
        stats: Scan statistics
    
    Returns:
        Markdown formatted string
    """
    from datetime import datetime
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    week_ending = datetime.now().strftime("%B %d, %Y")
    
    lines = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append(f"# Weekly Scanner Briefing - Week Ending {week_ending}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET CONTEXT PLACEHOLDER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 📊 Market Context")
    lines.append("")
    lines.append("> **[PLACEHOLDER - Add market analysis via Claude web interface]**")
    lines.append(">")
    lines.append("> Suggested topics to cover:")
    lines.append("> - S&P 500 / NASDAQ weekly performance")
    lines.append("> - Key macro events (Fed, economic data)")
    lines.append("> - Sector rotation observations")
    lines.append("> - VIX / volatility environment")
    lines.append("> - Any notable earnings or news from the week")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOT THEMES
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 🔥 Hot Themes This Week")
    lines.append("")
    
    if themes_data:
        # Separate PRIME and INVESTABLE themes
        prime_themes = [t for t in themes_data if t.get('classification') == 'PRIME']
        investable_themes = [t for t in themes_data if t.get('classification') == 'INVESTABLE']
        
        if prime_themes:
            lines.append("### PRIME Themes (Highest Conviction)")
            lines.append("")
            for t in prime_themes:
                theme_type = t.get('theme_type', 'TREND')
                score = t.get('composite_score', 0)
                lines.append(f"**{t.get('name', 'Unknown')}** ({theme_type})")
                lines.append(f"- Score: {score:.1f}/10")
                if t.get('thesis_summary'):
                    thesis = t['thesis_summary'][:300] + "..." if len(t.get('thesis_summary', '')) > 300 else t.get('thesis_summary', '')
                    lines.append(f"- Thesis: {thesis}")
                if t.get('key_catalysts'):
                    catalysts = t['key_catalysts'][:3] if isinstance(t['key_catalysts'], list) else []
                    if catalysts:
                        lines.append(f"- Catalysts: {', '.join(str(c) for c in catalysts)}")
                lines.append("")
        
        if investable_themes:
            lines.append("### INVESTABLE Themes (Good Opportunities)")
            lines.append("")
            for t in investable_themes:
                theme_type = t.get('theme_type', 'TREND')
                score = t.get('composite_score', 0)
                lines.append(f"- **{t.get('name', 'Unknown')}** ({theme_type}) - Score: {score:.1f}/10")
            lines.append("")
    else:
        lines.append("*Theme data not available - run scanner with LLM gates enabled*")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGNAL CANDIDATES
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 🎯 Signal Candidates (Passed All Gates)")
    lines.append("")
    
    if confirmed:
        # Separate PASS (GREEN signals), PENDING_DD, and CONSIDER signals
        trades = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        pending_dd = [s for s in confirmed if s.final_decision == "PENDING_DD"]
        considers = [s for s in confirmed if s.final_decision == "CONSIDER"]
        technical_only = [s for s in confirmed if s.final_decision in ["TECHNICAL_ONLY", "THEME_CONFIRMED"]]
        
        # P2: Split trades into BUY NOW vs BUY ON PULLBACK
        buy_now = [s for s in trades if s.gate_verdict == "STRONG_BUY"]
        buy_pullback = [s for s in trades if s.gate_verdict == "SPEC_BUY"]
        buy_other = [s for s in trades if s.gate_verdict not in ("STRONG_BUY", "SPEC_BUY")]
        
        def _newsletter_stock_card(s, show_dd=True):
            """Generate newsletter markdown card for a stock."""
            card = []
            alloc = TIER_ALLOC.get(s.tier, 0)
            card.append(f"#### {s.symbol}")
            card.append("")
            card.append(f"| Metric | Value |")
            card.append(f"|--------|-------|")
            card.append(f"| **Price** | ${s.price:.2f} |")
            card.append(f"| **Theme** | {s.theme or 'N/A'} ({s.theme_verdict}) |")
            card.append(f"| **Tier / Sizing** | {s.tier} — {alloc}% of equity |")
            card.append(f"| **Beta** | {s.beta:.2f} |")
            card.append(f"| **UC** | {s.uc:.0f} (rising={'✓' if s.uc_rising else '✗'}) |")
            card.append(f"| **Conviction** | {'★' * s.conviction}{'☆' * (5 - s.conviction)} |")
            if s.gate_verdict:
                card.append(f"| **Gate Verdict** | {s.gate_verdict.replace('_', ' ')} |")
            if s.catalyst_summary:
                card.append(f"| **Catalyst** | {s.catalyst_summary} |")
            if s.red_flag_level:
                card.append(f"| **Red Flags** | {s.red_flag_level} |")
            card.append("")
            
            if s.bullish_factors:
                card.append("**Bullish Factors:**")
                for factor in s.bullish_factors[:3]:
                    card.append(f"- {factor}")
                card.append("")
            
            if s.risk_factors:
                card.append("**Risk Factors:**")
                for risk in s.risk_factors[:3]:
                    card.append(f"- {risk}")
                card.append("")
            
            if s.reasoning:
                card.append("**Analysis:**")
                card.append(f"> {s.reasoning}")
                card.append("")
            
            if s.action:
                card.append(f"**Recommended Action:** {s.action}")
                card.append("")

            # Deep DD newsletter content (populated after Opus analysis)
            if show_dd and s.dd_elevator_pitch:
                card.append("**The Pitch:**")
                card.append(f"> {s.dd_elevator_pitch}")
                card.append("")
            if show_dd and s.dd_why_now:
                card.append(f"**Why Now:** {s.dd_why_now}")
                card.append("")
            if show_dd and s.dd_the_math:
                card.append(f"**The Math:** {s.dd_the_math}")
                card.append("")
            if show_dd and s.dd_bear_case:
                card.append(f"**Bear Case:** {s.dd_bear_case}")
                card.append("")
            if show_dd and s.dd_risk_to_monitor:
                card.append(f"**Risk to Monitor:** {s.dd_risk_to_monitor}")
                card.append("")
            if s.valuation_regime:
                card.append(f"**Valuation Regime:** {s.valuation_regime}")
                card.append("")

            card.append(f"📸 **[CHART: {s.symbol}]** - *Add TradingView screenshot*")
            card.append("")
            card.append("---")
            card.append("")
            return card
        
        # BUY NOW section (STRONG_BUY)
        if buy_now:
            lines.append("### 🟢 BUY NOW — Enter Monday Open")
            lines.append("")
            for s in buy_now:
                lines.extend(_newsletter_stock_card(s))
        
        # BUY ON PULLBACK section (SPEC_BUY)
        if buy_pullback:
            lines.append("### 🟡 BUY ON PULLBACK — Wait for Entry Level")
            lines.append("")
            for s in buy_pullback:
                lines.extend(_newsletter_stock_card(s))
        
        # Other PASS trades (fallback)
        if buy_other:
            lines.append("### 🟢 PASS - Ready for Entry (GREEN Signals)")
            lines.append("")
            for s in buy_other:
                lines.extend(_newsletter_stock_card(s))

        # PENDING DD section
        if pending_dd:
            lines.append("### ⚠️ PENDING DUE DILIGENCE — Do NOT Trade Yet")
            lines.append("")
            lines.append("*These stocks passed technical, thematic, and investment gates but Deep DD failed or was skipped. Re-run scanner with DD enabled before trading.*")
            lines.append("")
            for s in pending_dd:
                alloc = TIER_ALLOC.get(s.tier, 0)
                lines.append(f"- **{s.symbol}** - ${s.price:.2f} | {s.theme or 'N/A'} | {s.tier} ({alloc}% equity) | Gate: {s.gate_verdict or 'N/A'} | DD: {s.dd_verdict or 'Not run'}")
            lines.append("")
            lines.append("---")
            lines.append("")

        if considers:
            lines.append("### 🟡 CONSIDER - Wait or Size Down")
            lines.append("")
            for s in considers:
                lines.extend(_newsletter_stock_card(s, show_dd=False))
                lines.append("---")
                lines.append("")
        
        if technical_only:
            lines.append("### ⚪ PENDING DUE DILIGENCE")
            lines.append("")
            lines.append("*These stocks passed technical and thematic gates but require manual due diligence:*")
            lines.append("")
            for s in technical_only:
                lines.append(f"- **{s.symbol}** - ${s.price:.2f} | {s.theme or 'N/A'} | {s.tier} | UC {s.uc:.0f}")
            lines.append("")
            lines.append("---")
            lines.append("")
    else:
        lines.append("*No new signals this week*")
        lines.append("")
        if stats:
            lines.append("**Pipeline Summary:**")
            lines.append(f"- Tickers scanned: {stats.tickers_loaded}")
            lines.append(f"- V6 buy signals: {stats.buy_signal}")
            lines.append(f"- Technical signals: {stats.meets_technical_gate}")
            lines.append(f"- Theme confirmed: {stats.theme_confirmed}")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PORTFOLIO UPDATE
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 📈 Portfolio Update")
    lines.append("")

    # Load portfolio data from portfolio_manager (preferred) or legacy CSV
    open_positions = []
    closed_trades = []
    performance_summary = None

    if PORTFOLIO_MANAGER_AVAILABLE:
        try:
            pm = get_portfolio_manager()
            # Refresh prices before getting data
            pm.update_prices()

            for trade in pm.get_open_positions():
                open_positions.append({
                    'symbol': trade.ticker,
                    'entry_date': trade.entry_date,
                    'entry_price': trade.entry_price,
                    'highest_close': trade.highest_close,
                    'current_price': trade.current_price if trade.current_price > 0 else trade.entry_price,
                    'pnl_pct': trade.pnl_pct,
                    'pnl_usd': trade.pnl_usd,
                    'days_held': trade.days_held,
                    'stop_level': trade.stop_level,
                    'distance_to_stop': trade.distance_to_stop,
                    'theme': trade.theme,
                    'tier': trade.tier
                })

            # Get recently closed trades (last 7 days)
            for trade in pm.get_closed_trades():
                if trade.exit_date:
                    try:
                        exit_dt = datetime.strptime(trade.exit_date, "%Y-%m-%d")
                        if (datetime.now() - exit_dt).days <= 7:
                            closed_trades.append({
                                'symbol': trade.ticker,
                                'entry_date': trade.entry_date,
                                'exit_date': trade.exit_date,
                                'entry_price': trade.entry_price,
                                'exit_price': trade.exit_price,
                                'pnl_pct': trade.pnl_pct,
                                'pnl_usd': trade.pnl_usd,
                                'theme': trade.theme,
                                'status': trade.status
                            })
                    except Exception:
                        pass

            # Get performance summary
            performance_summary = pm.get_performance_summary()
        except Exception as e:
            pass

    # Fallback to legacy open_positions.csv if portfolio_manager unavailable or empty
    if not open_positions:
        open_positions_file = BASE_DIR / "trades" / "open_positions.csv"  # Legacy location
        if open_positions_file.exists():
            try:
                with open(open_positions_file, 'r') as f:
                    reader = csv.DictReader(f)
                    open_positions = list(reader)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # PORTFOLIO PERFORMANCE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    if performance_summary or open_positions:
        lines.append("### 📊 Performance Summary")
        lines.append("")

        if performance_summary:
            # Calculate total unrealized P&L
            total_unrealized_pnl = sum(p.get('pnl_pct', 0) for p in open_positions)
            total_unrealized_usd = sum(p.get('pnl_usd', 0) for p in open_positions)

            lines.append("**Current Portfolio:**")
            lines.append(f"- Open Positions: {len(open_positions)}")
            lines.append(f"- Unrealized P&L: {total_unrealized_pnl:+.1f}% (${total_unrealized_usd:+,.0f})")
            lines.append("")

            if performance_summary.get('closed_trades', 0) > 0:
                lines.append("**Closed Trades (All Time):**")
                lines.append(f"- Win Rate: {performance_summary.get('win_rate', 0):.0f}%")
                lines.append(f"- Avg Winner: {performance_summary.get('avg_winner', 0):+.1f}%")
                lines.append(f"- Avg Loser: {performance_summary.get('avg_loser', 0):+.1f}%")
                lines.append(f"- Total Closed: {performance_summary.get('closed_trades', 0)}")
                lines.append("")
        else:
            lines.append(f"- Open Positions: {len(open_positions)}")
            lines.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # COMPOUNDING EQUITY (Portfolio vs S&P 500 since inception)
    # ─────────────────────────────────────────────────────────────────────────
    try:
        from portfolio.manager import PortfolioManager as _PM
        _pm = _PM()
        _pm.update_prices()
        compounding = _pm.get_compounding_summary()

        if compounding and compounding.get('inception_date'):
            lines.append("### 💰 Portfolio Equity (Compounding)")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| **Inception** | {compounding['inception_date']} |")
            lines.append(f"| **Capital Per Position** | {compounding['currency']}{compounding['starting_per_position']:,.0f} |")
            lines.append(f"| **Total Deployed** | {compounding['currency']}{compounding['total_deployed']:,.0f} |")
            lines.append(f"| **Current NAV** | {compounding['currency']}{compounding['current_nav']:,.2f} |")
            lines.append(f"| **Total Return** | {compounding['total_return_pct']:+.1f}% |")
            lines.append(f"| **SPY Equivalent** | {compounding['currency']}{compounding['spy_value']:,.2f} ({compounding['spy_return_pct']:+.1f}%) |")
            lines.append(f"| **Alpha** | {compounding['alpha_pct']:+.1f}% |")
            if compounding['max_drawdown_pct'] < 0:
                lines.append(f"| **Max Drawdown** | {compounding['max_drawdown_pct']:.1f}% |")
            lines.append("")
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # RECENTLY CLOSED TRADES (This Week)
    # ─────────────────────────────────────────────────────────────────────────
    if closed_trades:
        lines.append("### 🏁 Recently Closed (Last 7 Days)")
        lines.append("")
        lines.append("| Ticker | Exit Date | Entry | Exit | P&L | Status |")
        lines.append("|--------|-----------|-------|------|-----|--------|")
        for trade in closed_trades:
            symbol = trade.get('symbol', 'N/A')
            exit_date = trade.get('exit_date', 'N/A')
            entry_price = float(trade.get('entry_price', 0))
            exit_price = float(trade.get('exit_price', 0))
            pnl_pct = trade.get('pnl_pct', 0)
            status = trade.get('status', 'CLOSED')
            status_emoji = "🛑" if status == "STOPPED" else "✅"
            lines.append(f"| {symbol} | {exit_date} | ${entry_price:.2f} | ${exit_price:.2f} | {pnl_pct:+.1f}% | {status_emoji} {status} |")
        lines.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # EXIT SIGNALS
    # ─────────────────────────────────────────────────────────────────────────
    if sell_signals:
        lines.append("### 🔴 Exit Signals")
        lines.append("")
        # CRIT-12.5: Entry prices for OPEN positions are PRIVATE
        # Only show: Ticker, Current Price, Reason, P&L - NOT entry price or highest close
        lines.append("| Ticker | Current | Reason | P&L |")
        lines.append("|--------|---------|--------|-----|")
        for s in sell_signals:
            pnl = ((s.price / s.entry_price) - 1) * 100 if s.entry_price > 0 else 0
            pnl_str = f"{pnl:+.1f}%"
            lines.append(f"| {s.symbol} | ${s.price:.2f} | {s.reason[:40]} | {pnl_str} |")
        lines.append("")
        lines.append("*Exit signals: position closed on whichever fired first (HMA fracture or trailing stop).*")
        lines.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # OPEN POSITIONS WITH LIVE DATA
    # ─────────────────────────────────────────────────────────────────────────
    if open_positions:
        lines.append("### 📈 Open Positions (Live Data)")
        lines.append("")
        # CRIT-12.5: Entry prices for OPEN positions are PRIVATE
        # Show: Ticker, Theme, Tier, Current P&L%, Holding Period - NOT entry price
        lines.append("| Ticker | Theme | P&L | Days Held | Stop Distance |")
        lines.append("|--------|-------|-----|-----------|---------------|")
        for pos in open_positions:
            symbol = pos.get('symbol', 'N/A')
            entry_price = float(pos.get('entry_price', 0))
            current_price = float(pos.get('current_price', entry_price))
            pnl_pct = pos.get('pnl_pct', 0)
            if pnl_pct == 0 and entry_price > 0:
                pnl_pct = ((current_price / entry_price) - 1) * 100
            days_held = pos.get('days_held', 0)
            distance_to_stop = pos.get('distance_to_stop', 20)
            theme = pos.get('theme', 'N/A')[:20]

            # Color code stop distance
            stop_indicator = "🟢" if distance_to_stop > 15 else "🟡" if distance_to_stop > 10 else "🔴"

            lines.append(f"| {symbol} | {theme} | {pnl_pct:+.1f}% | {days_held}d | {stop_indicator} {distance_to_stop:.1f}% |")
        lines.append("")
        lines.append("*Stop Distance: 🟢 >15% safe | 🟡 10-15% watch | 🔴 <10% alert*")
        lines.append("")
    else:
        lines.append("### 📈 Open Positions")
        lines.append("")
        lines.append("*No open positions*")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DUE DILIGENCE SECTION
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 📋 Due Diligence")
    lines.append("")
    lines.append("*Run due diligence separately in Claude web interface using the prompts from `due_diligence_prompts.py`*")
    lines.append("")
    
    if confirmed:
        trade_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if trade_stocks:
            lines.append("### Stocks Requiring DD:")
            lines.append("")
            for s in trade_stocks:
                lines.append(f"- [ ] **{s.symbol}** - {s.theme or 'Unknown theme'}")
            lines.append("")
            lines.append("### DD Output Placeholders:")
            lines.append("")
            for s in trade_stocks:
                lines.append(f"#### {s.symbol} Due Diligence")
                lines.append("")
                lines.append("> **[PASTE DD OUTPUT HERE]**")
                lines.append(">")
                lines.append("> Key items to extract:")
                lines.append("> - Elevator pitch")
                lines.append("> - Specific catalysts with dates")
                lines.append("> - Bear case and rebuttal")
                lines.append("> - Math to 50%")
                lines.append("> - Final verdict")
                lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("## 📝 Disclaimer")
    lines.append("")
    lines.append("*This newsletter is for informational purposes only and does not constitute financial advice. ")
    lines.append("All investment decisions should be made based on your own research and risk tolerance. ")
    lines.append("Past performance is not indicative of future results.*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by BoS Momentum Scanner*")
    
    return "\n".join(lines)


def save_newsletter_briefing(
    confirmed: List[Stock],
    sell_signals: List[SellSignal],
    themes_data: List[dict] = None,
    stats: ScanStats = None,
    archive: bool = False,
    current_dir: Path = None,
    week_dir: Path = None
):
    """Save the newsletter briefing to a markdown file."""

    date_str = datetime.now().strftime("%Y%m%d")

    # Use provided dirs or get them
    if current_dir is None or week_dir is None:
        current_dir, week_dir = ensure_output_structure()

    # Helper for relative paths
    def rel_path(p: Path) -> str:
        return get_relative_path(p) if OUTPUT_PATHS_AVAILABLE else str(p)

    briefing = generate_newsletter_briefing(confirmed, sell_signals, themes_data, stats)

    # Save to current/ and weekly archive
    briefing_current = current_dir / "newsletter_briefing.md"
    briefing_archive = week_dir / "newsletter_briefing.md"
    with open(briefing_current, 'w') as f:
        f.write(briefing)
    with open(briefing_archive, 'w') as f:
        f.write(briefing)

    print(f"\n  📰 Newsletter briefing:")
    print(f"     • {rel_path(briefing_current)} (current week)")
    print(f"     • {rel_path(briefing_archive)} (archived)")

    return briefing_current


def print_newsletter_prompts(briefing_file: Path = None):
    """Print the market context and newsletter compilation prompts for easy copy/paste."""
    
    from datetime import timedelta
    
    today = datetime.now()
    
    # Find Friday of this week
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0 and today.weekday() != 4:
        days_since_friday = 7
    friday = today - timedelta(days=days_since_friday)
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " NEWSLETTER GENERATION PROMPTS ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print("")
    print("  Use these prompts in Claude web interface to generate your weekly newsletter.")
    print("  Copy each prompt, paste into a new Claude conversation, and save the output.")
    print("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROMPT 1: MARKET CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════
    print("─" * 80)
    print("  [PROMPT 1] MARKET CONTEXT GENERATION")
    print("─" * 80)
    print("  Run this FIRST to generate the market analysis section.")
    print("  Save the output for use in Prompt 2.")
    print("─" * 80)
    print("")
    print(">>> COPY FROM HERE >>>")
    print("")
    
    market_prompt = f'''# MARKET CONTEXT GENERATION

You are writing the market analysis section for a weekly investment newsletter focused on US momentum/growth stocks. The newsletter is aimed at US active investors and swing traders seeking systematic momentum opportunities.

**Today's Date:** {today.strftime("%B %d, %Y")}
**Week Ending:** {friday.strftime("%B %d, %Y")}

## YOUR TASK

Search for and synthesize the following into a cohesive 3-4 paragraph market summary:

### Required Data Points (Search for each):
1. **Index Performance This Week:**
   - S&P 500 weekly change (% and points)
   - NASDAQ Composite weekly change
   - Russell 2000 weekly change (small caps sentiment)

2. **Key Events This Week:**
   - Federal Reserve announcements or commentary
   - Major economic data releases (jobs, CPI, retail sales, etc.)
   - Significant earnings reports from bellwether companies

3. **Sector Rotation:**
   - Which sectors led this week?
   - Which sectors lagged?
   - Any notable rotation patterns?

4. **Volatility & Sentiment:**
   - VIX level and weekly change
   - General market sentiment (risk-on/risk-off)

5. **Looking Ahead:**
   - Key events next week (Fed meetings, major earnings, economic data)
   - Any looming risks or catalysts

## OUTPUT FORMAT

Write in this structure (markdown):

## 📊 Market Context

[Opening paragraph: Overall market performance this week - what happened and why]

[Second paragraph: Sector dynamics - what's leading, what's lagging, any rotation]

[Third paragraph: Key events that moved markets - Fed, data, earnings]

[Fourth paragraph: Looking ahead - what to watch next week, setup for momentum stocks]

## STYLE GUIDELINES
- Professional but accessible tone
- Specific numbers (e.g., "S&P 500 rose 1.2% to 4,850")
- Connect macro to momentum stock implications
- US investor perspective (mention DXY/dollar index only if significant macro impact)
- No disclaimers (those come later)

Generate the market context section now.'''
    
    print(market_prompt)
    print("")
    print("<<< COPY TO HERE <<<")
    print("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROMPT 2: NEWSLETTER COMPILATION
    # ═══════════════════════════════════════════════════════════════════════════
    print("─" * 80)
    print("  [PROMPT 2] NEWSLETTER COMPILATION")
    print("─" * 80)
    print("  Run this AFTER you have:")
    print("    1. Market context (from Prompt 1)")
    print("    2. Scanner briefing (trades/latest_newsletter_briefing.md)")
    print("    3. DD outputs for each PASS signal (from core/deep_dd.py)")
    print("")
    if briefing_file:
        print(f"  📄 Your briefing file: {briefing_file}")
    print("─" * 80)
    print("")
    print(">>> COPY FROM HERE >>>")
    print("")
    
    compile_prompt = '''# WEEKLY NEWSLETTER COMPILATION

You are the editor compiling the final weekly edition of "BoS Momentum Scanner" - a Substack newsletter for momentum stock investors. You have all the raw materials below and need to produce a polished, publication-ready newsletter.

## NEWSLETTER IDENTITY
- **Name:** BoS Momentum Scanner Weekly
- **Audience:** US active investors and swing traders seeking systematic momentum opportunities
- **Frequency:** Weekly (published Saturday/Sunday)
- **Tone:** Professional, data-driven, actionable
- **Platform:** Substack

---

## RAW INPUTS

### 1. MARKET CONTEXT

[PASTE YOUR MARKET CONTEXT OUTPUT HERE]

### 2. SCANNER BRIEFING (Themes & Signals)

[PASTE CONTENTS OF trades/latest_newsletter_briefing.md HERE]

### 3. DUE DILIGENCE OUTPUTS

[PASTE ALL YOUR DD OUTPUTS HERE - one after another]

---

## YOUR TASK

Compile these inputs into a polished Substack newsletter with the following structure:

### REQUIRED SECTIONS

**1. TITLE & HOOK**
- Compelling title that captures this week's key theme/signal
- One-line subtitle/hook

**2. MARKET CONTEXT**
- Use the market context provided
- Light editing for flow only

**3. THIS WEEK'S THEMES**
- Extract PRIME and INVESTABLE themes from scanner briefing
- Brief explanation of why each theme is hot NOW

**4. NEW SIGNALS**
For each stock that passed all gates (🟢 PASS):
- **Ticker & Company** (header)
- **The Setup** (2-3 sentences from scanner data)
- **Why Now** (key catalyst from DD)
- **The Math** (path to 50%+ from DD)
- **Risk to Monitor** (main concern)
- **Action:** Entry price, position sizing
- **[CHART: TICKER]** placeholder for screenshot

**5. WATCHLIST** (if any 🟡 CONSIDER signals)
- Stocks worth watching and why waiting

**6. PORTFOLIO UPDATE**
- Open positions with current P&L
- Any exit signals

**7. LOOKING AHEAD**
- What to watch next week
- Upcoming catalysts

**8. FOOTER**
- Standard disclaimer
- Next scan date

---

## FORMATTING RULES
- Use markdown (headers, bold, tables, bullets)
- Chart placeholders: `[CHART: TICKER]`
- Keep it scannable - busy readers get gist from headers
- Specific numbers always (price, %, dates)

## LENGTH TARGET
- 1,500-2,500 words
- 8-12 minute read

---

Generate the complete newsletter in markdown format, ready to paste into Substack.'''
    
    print(compile_prompt)
    print("")
    print("<<< COPY TO HERE <<<")
    print("")
    print("═" * 80)
    print("")


def save_results(confirmed: List[Stock], all_assessed: List[Stock], sell_signals: List[SellSignal], stats: ScanStats, momentum_rejected: List[Stock] = None, themes_data: List[dict] = None, archive: bool = False):
    """Save results to files - includes ALL assessed stocks for back-analysis."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y%m%d")

    # Ensure weekly folder structure exists
    current_dir, week_dir = ensure_output_structure()

    # Helper for relative paths in output
    def rel_path(p: Path) -> str:
        return get_relative_path(p) if OUTPUT_PATHS_AVAILABLE else str(p)

    # Build signals JSON data — helper to create signal dict
    def _signal_dict(s: Stock) -> dict:
        """Build a signal dict for a single stock with Sterling Grid V6 fields."""
        return {
            "symbol": s.symbol,
            "tier": s.tier,
            "quality_tier": s.quality_tier,
            "price": s.price,
            # Sterling Grid V6 indicators
            "uc": s.uc,
            "uc_rising": s.uc_rising,
            "rsi14": s.rsi14,
            "macd_cross_up": s.macd_cross_up,
            "hma_pivot_low": s.hma_pivot_low,
            "hma_pivot_high": s.hma_pivot_high,
            "hma_slope_rising": s.hma_slope_rising,
            "buy_signal": s.buy_signal,
            "exd_signal": s.exd_signal,
            # Legacy (backward compat for tweet generator / content systems)
            "beta": s.beta,
            "banker": s.uc,  # Map UC → banker key for downstream compat
            "return_20d": s.return_20d,
            "uc_rising_above": s.uc_rising_above,  # V4 legacy
            # Theme
            "theme": s.theme,
            "theme_score": s.theme_score,
            "pure_play_score": s.pure_play_score,
            "theme_verdict": s.theme_verdict,
            "theme_classification": s.theme_classification,
            # Gate
            "final_decision": s.final_decision,
            "conviction": s.conviction,
            "gate_verdict": s.gate_verdict,
            "gate_conviction": s.gate_conviction,
            "gate_catalyst": s.gate_catalyst,
            "gate_bear_case": s.gate_bear_case,
            "gate_math": s.gate_math,
            "valuation_regime": s.valuation_regime,
            "sector_status": s.sector_status,
            "upside_potential": s.upside_potential,
            "bullish_factors": s.bullish_factors,
            "risk_factors": s.risk_factors,
            "reasoning": s.reasoning,
            # Position sizing
            "position_size_pct": s.position_size_pct,
            "position_dollars": s.position_dollars,
            "position_tier": s.position_tier,
            # Deep DD
            "dd_verdict": s.dd_verdict,
            "dd_conviction": s.dd_conviction,
            "dd_position_size": s.dd_position_size,
            "dd_key_catalyst": s.dd_key_catalyst,
            "dd_fatal_flaw": s.dd_fatal_flaw,
            "dd_elevator_pitch": s.dd_elevator_pitch,
            "dd_why_now": s.dd_why_now,
            "dd_the_math": s.dd_the_math,
            "dd_bear_case": s.dd_bear_case,
            "dd_risk_to_monitor": s.dd_risk_to_monitor,
            "dd_action": s.dd_action,
        }

    signals_data = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": f"Sterling Grid V6: HMA pivot↓ + (UC rising OR MACD cross-up) + Price<${PRICE_CAP:.0f} + Theme + Investment Gate PASS",
        "exit_criteria": "ExD compound exit (HMA pivot high + UC falling) OR tiered profit lock (+200%→15%, +100%→20%, +50%→25%)",
        "stats": {
            "tickers_loaded": stats.tickers_loaded,
            "data_downloaded": stats.data_downloaded,
            "price_under_cap": stats.price_under_cap,
            "hma_pivot_low": stats.hma_pivot_low,
            "hma_slope_rising": stats.hma_slope_rising,
            "rsi_above_50": stats.rsi_above_50,
            "macd_cross_up": stats.macd_cross_up,
            "uc_rising": stats.uc_rising,
            "uc_rising_above": stats.uc_rising_above,
            "buy_signal": stats.buy_signal,
            "tier_t1": stats.tier_t1,
            "tier_t2": stats.tier_t2,
            "tier_t3": stats.tier_t3,
            "technical_signals": stats.meets_technical_gate,
            "theme_confirmed": stats.theme_confirmed,
            "final_trade": stats.final_trade,
            "final_consider": stats.final_consider,
            # Legacy keys (backward compat)
            "beta_gte_1_5": stats.beta_gte_1_5,
            "weekly_bos_up": stats.buy_signal,  # Map buy_signal → legacy key
        },
        # Themes data for tweet generator
        "themes": themes_data if themes_data else [],
        # Separated pass_signals (GREEN signals) from consider_signals
        "pass_signals": [
            {**_signal_dict(s), "final_decision": "PASS", "action": "Enter Monday at market open"}
            for s in confirmed if s.final_decision in ["PASS", "TRADE"]
        ],
        "consider_signals": [
            {**_signal_dict(s), "action": "Consider smaller position - watching for Investment Gate"}
            for s in confirmed if s.final_decision == "CONSIDER"
        ],
        # Legacy: buy_signals includes all confirmed for backwards compatibility
        "buy_signals": [
            {
                **_signal_dict(s),
                "action": (
                    "Enter Monday at market open" if s.final_decision in ["PASS", "TRADE"]
                    else "Consider smaller position" if s.final_decision == "CONSIDER"
                    else "Pending LLM analysis" if s.final_decision in ["TECHNICAL_ONLY", "THEME_CONFIRMED"]
                    else "Review required"
                ),
            }
            for s in confirmed
        ],
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
        # All assessed tickers (theme-confirmed but not necessarily PASS/CONSIDER)
        # Used by reaction_generator.py for richer theme-to-ticker mapping
        "assessed_signals": [
            {
                "symbol": s.symbol,
                "price": s.price,
                "theme": s.theme,
                "theme_score": s.theme_score,
                "theme_verdict": s.theme_verdict,
                "final_decision": s.final_decision,
                "tier": s.tier,
            }
            for s in all_assessed
            if s.theme and s.final_decision not in ("PASS", "TRADE", "CONSIDER")
        ],
        # NEW: Historical wins tracking (marketing overhaul)
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
            for h in historical if h.pnl_pct >= MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
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
                "threshold_crossed": w.threshold_crossed,
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
                "threshold_crossed": w.threshold_crossed,
            }
            for w in all_big_wins if w.pnl_pct >= home_run_threshold
        ]

        print(f"  📊 Historical tracking: {len(signals_data['historical_winners'])} winners, {len(signals_data['big_wins'])} big wins, {len(signals_data['home_runs'])} home runs")

    except ImportError:
        print("  ⚠️ signal_tracker not available - historical wins not populated")
    except Exception as e:
        print(f"  ⚠️ Error loading historical wins: {e}")

    # Save signals JSON to current/ and weekly archive
    signals_json = json.dumps(signals_data, indent=2)
    signals_current = current_dir / "signals.json"
    signals_archive = week_dir / "signals.json"
    with open(signals_current, 'w') as f:
        f.write(signals_json)
    with open(signals_archive, 'w') as f:
        f.write(signals_json)

    # Also save to canonical scanner output location
    signals_file = SIGNALS_FILE
    with open(signals_file, 'w') as f:
        f.write(signals_json)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPREHENSIVE ANALYSIS LOG - ALL assessed stocks for back-analysis
    # ═══════════════════════════════════════════════════════════════════════════
    analysis_log = ANALYSIS_LOG
    write_header = not analysis_log.exists()
    
    with open(analysis_log, 'a', newline='') as f:
        fieldnames = [
            'timestamp', 'symbol', 'price', 'beta', 'banker', 'momentum_4w', 'return_20d', 'tier',
            # Theme analysis
            'theme', 'theme_score', 'pure_play_score', 'theme_verdict',
            # Momentum assessment
            'final_decision', 'conviction', 'sector_status', 'upside_potential',
            'bullish_factors', 'risk_factors', 'reasoning',
            # Outcome
            'passed_all_gates'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()
        
        for s in all_assessed:
            # Clean text fields for CSV
            bullish = '; '.join(s.bullish_factors) if s.bullish_factors else ''
            risks = '; '.join(s.risk_factors) if s.risk_factors else ''
            reasoning = s.reasoning.replace(',', ';').replace('\n', ' ').replace('"', "'") if s.reasoning else ''
            
            writer.writerow({
                'timestamp': timestamp,
                'symbol': s.symbol,
                'price': s.price,
                'beta': s.beta,
                'banker': s.banker,
                'momentum_4w': s.momentum_4w,
                'return_20d': s.return_20d,
                'tier': s.tier,
                'theme': s.theme or '',
                'theme_score': s.theme_score,
                'pure_play_score': s.pure_play_score,
                'theme_verdict': s.theme_verdict or '',
                'final_decision': s.final_decision or '',
                'conviction': s.conviction,
                'sector_status': s.sector_status or '',
                'upside_potential': s.upside_potential or '',
                'bullish_factors': bullish[:200],  # Truncate for CSV
                'risk_factors': risks[:200],
                'reasoning': reasoning[:300],
                'passed_all_gates': 'PENDING_DD' if s.final_decision == 'PENDING_DD' else ('YES' if s.final_decision in ['PASS', 'TRADE', 'CONSIDER'] else 'NO')
            })
    
    # Note: trade_log.csv removed - analysis_log.csv contains all data with passed_all_gates flag
    # Filter analysis_log for passed_all_gates='YES' to get confirmed trades

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE AND SAVE REPORT
    # ═══════════════════════════════════════════════════════════════════════════
    report = generate_report(confirmed, all_assessed, sell_signals, stats, momentum_rejected)

    # Save report to current/ and weekly archive
    report_current = current_dir / "report.txt"
    report_archive = week_dir / "report.txt"
    with open(report_current, 'w') as f:
        f.write(report)
    with open(report_archive, 'w') as f:
        f.write(report)

    # (Legacy root copies removed — use trades/current/report.txt)

    print(f"\n  📁 Results saved:")
    print(f"     • {rel_path(signals_current)} (current week)")
    print(f"     • {rel_path(signals_archive)} (archived)")
    print(f"     • {rel_path(signals_file)} (legacy)")
    print(f"     • {rel_path(analysis_log)}")
    print(f"     • {rel_path(report_current)} (current week)")
    if archive:
        print(f"     • {rel_path(report_archive)} (dated archive)")

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE NEWSLETTER BRIEFING
    # ═══════════════════════════════════════════════════════════════════════════
    save_newsletter_briefing(confirmed, sell_signals, themes_data, stats, archive=archive, current_dir=current_dir, week_dir=week_dir)

    return report  # Return report for email use


def send_notification(confirmed: List[Stock], sell_signals: List[SellSignal], stats: ScanStats, report: str = None):
    """Send email notification with formatted report."""
    try:
        from utils.email_notifier import send_email, load_config
        
        config = load_config()
        if not config:
            print("  ⚠ Email not configured (run: python email_notifier.py setup)")
            return
        
        # Generate subject line
        if confirmed or sell_signals:
            trades = len([s for s in confirmed if s.final_decision in ["PASS", "TRADE", "TECHNICAL_ONLY", "THEME_CONFIRMED"]]) if confirmed else 0
            pending_dd = len([s for s in confirmed if s.final_decision == "PENDING_DD"]) if confirmed else 0
            considers = len([s for s in confirmed if s.final_decision == "CONSIDER"]) if confirmed else 0
            exits = len(sell_signals) if sell_signals else 0

            parts = []
            if trades:
                parts.append(f"{trades} Entry")
            if pending_dd:
                parts.append(f"{pending_dd} Pending DD")
            if considers:
                parts.append(f"{considers} Consider")
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
  Weekly BoS Up:      {stats.bos_bullish}
  Technical signals:  {stats.meets_technical_gate}
  Theme confirmed:    {stats.theme_confirmed}
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
    parser = argparse.ArgumentParser(description="BoS Momentum Scanner - Weekly Timeframe")
    parser.add_argument("--no-llm", action="store_true", help="Skip ALL LLM gates (technical signals only)")
    parser.add_argument("--no-momentum", action="store_true", help="Skip Investment Gate (keep theme analysis) - faster but less thorough")
    parser.add_argument("--assess-top", type=int, metavar="N", help="Only run Investment Gate on top N stocks by UC (accumulation strength)")
    parser.add_argument("--no-email", action="store_true", help="Skip email notification")
    parser.add_argument("--no-prompts", action="store_true", help="Skip printing DD and newsletter prompts at the end")
    # Keep --no-dd-prompts as alias for backwards compatibility
    parser.add_argument("--no-dd-prompts", action="store_true", dest="no_prompts", help=argparse.SUPPRESS)
    parser.add_argument("--no-grok-prompts", action="store_true", help=argparse.SUPPRESS)  # Legacy flag, grok prompts removed
    parser.add_argument("--top", type=int, help="Only scan top N stocks by beta")
    parser.add_argument("--web-search", action="store_true", help="Enable web search for Thematic Analyzer AND Investment Gate. Recommended for production scans.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed diagnostic output (10 items per category instead of 3)")
    parser.add_argument("--archive", action="store_true", help="Save dated archive files in addition to latest_* files")
    # Deep DD options (runs by default on Investment Gate passes)
    parser.add_argument("--no-dd", action="store_true", help="Skip Deep DD (NOT recommended - portfolio won't be updated)")
    parser.add_argument("--save-dd", action="store_true", help="Save Deep DD reports to reports/ directory")
    # Keep legacy flags for backwards compatibility (now no-ops)
    parser.add_argument("--full-dd", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dd-top", type=int, metavar="N", help=argparse.SUPPRESS)
    parser.add_argument("--dd", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    
    # Header
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "BoS MOMENTUM SCANNER V6 - WEEKLY TIMEFRAME".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Show entry/exit criteria (marketing-safe by default, detailed with --verbose)
    if args.verbose:
        print(f"\n  ENTRY (V6): HMA pivot↓ + (UC rising OR MACD cross-up) + Price<${PRICE_CAP:.0f}")
        print("  TIERS: T1 (both, 20%) | T2 (MACD, 10%) | T3 (UC, 5%) | Max 8 positions")
        print("  EXIT:  ExD (HMA pivot↑ + UC↓) OR tiered profit lock (+200%→15%, +100%→20%, +50%→25%)")
    else:
        print("\n  ENTRY (V6): Pivot + Confirmation Gate Screening (Structural + Timing/Accumulation + Price)")
        print("  EXIT:  Capital Preservation Protocol (first exit — whichever fires first)")
    
    # Show pipeline based on options
    if args.no_llm:
        print("\n  Pipeline: Technical signals only (ALL LLM gates skipped)")
        print("  Cost: $0.00 (free)")
    elif args.no_momentum:
        print("\n  Pipeline: Technical → Thematic Analyzer (Investment Gate skipped)")
        web_cost = " + web search" if args.web_search else ""
        print(f"  Cost: ~$0.15/run{web_cost}")
    elif args.assess_top:
        print(f"\n  Pipeline: Technical → Thematic → Investment Gate (top {args.assess_top} only)")
        if args.web_search:
            print(f"  Cost: ~${0.15 + (args.assess_top * 0.20):.2f}/run (with web search)")
        else:
            print(f"  Cost: ~${0.15 + (args.assess_top * 0.03):.2f}/run (no web search - testing)")
    else:
        print("\n  Pipeline: Technical → Thematic → Investment Gate (thorough)")
        if args.web_search:
            print("  Cost: ~$1-3/run (web search enabled)")
        else:
            print("  Cost: ~$0.30-0.50/run (no web search - testing)")
        print("  Schedule: Run WEEKLY (signals only change on Friday close)")
    
    if args.web_search:
        print("\n  🌐 Web search ENABLED:")
        print("     • Thematic: Current theme momentum")
        print("     • Investment Gate: 5 searches per stock (red flags, catalysts, return math)")
    else:
        print("\n  💰 Web search DISABLED (testing mode):")
        print("     • Using model knowledge only - data may be outdated")
        print("     • Use --web-search for production scans")
    
    # Portfolio status
    if PORTFOLIO_MANAGER_AVAILABLE:
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
    
    # Run scan
    confirmed, all_assessed, sell_signals, stats, momentum_rejected, themes_data = run_scan(
        skip_llm=args.no_llm,
        skip_momentum=args.no_momentum,
        assess_top_n=args.assess_top,
        top_n=args.top,
        use_web_search=args.web_search,
        verbose=args.verbose
    )

    # Step 7.5: Deep Due Diligence (Opus + Extended Thinking)
    # DD is required for portfolio updates - only DD-PASS signals get added
    dd_results = []
    dd_pass_stocks = []
    dd_fail_stocks = []

    if not args.no_dd and confirmed and not args.no_llm:
        pass_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if pass_stocks:
            print("\n" + "─" * 70)
            print("  STEP 7.5: DEEP DUE DILIGENCE (Opus + Extended Thinking)")
            print("─" * 70)
            print("  Deep DD is REQUIRED before adding to portfolio")
            print("     Only STRONG BUY / SPEC BUY verdicts will be added")

            try:
                from scanner.deep_dd import run_deep_dd_batch, apply_dd_to_stocks

                # Run Deep DD on all gate passes (typically 1-3 stocks)
                _pipeline_timer.start("Step 7.5: Deep DD")
                dd_results = run_deep_dd_batch(
                    stocks=pass_stocks,
                    use_web_search=args.web_search,
                    save_reports=args.save_dd
                )
                _pipeline_timer.stop()

                # apply_dd_to_stocks maps dd_verdict, dd_conviction, dd_position_size,
                # dd_analysis (elevator_pitch), dd_key_catalyst (why_now), dd_fatal_flaw
                dd_pass_stocks, dd_fail_stocks = apply_dd_to_stocks(confirmed, dd_results)

                # Map additional Deep DD newsletter fields to Stock objects
                dd_lookup = {r.ticker: r for r in dd_results}
                for stock in confirmed:
                    if stock.symbol in dd_lookup:
                        r = dd_lookup[stock.symbol]
                        stock.dd_elevator_pitch = r.elevator_pitch
                        stock.dd_why_now = r.why_now
                        stock.dd_the_math = r.the_math
                        stock.dd_bear_case = r.bear_case
                        stock.dd_risk_to_monitor = r.risk_to_monitor
                        stock.dd_action = r.action_recommendation

                # Add only DD-PASS stocks to portfolio
                if dd_pass_stocks:
                    print(f"\n  Adding {len(dd_pass_stocks)} DD-PASS signal(s) to portfolio...")
                    for stock in dd_pass_stocks:
                        add_to_open_positions(stock)
                        print(f"     {stock.symbol} - {stock.dd_verdict} ({stock.dd_conviction}/10)")

                if dd_fail_stocks:
                    print(f"\n  {len(dd_fail_stocks)} signal(s) FAILED DD (not added to portfolio):")
                    for stock in dd_fail_stocks:
                        print(f"     {stock.symbol} - NO GO: {stock.dd_fatal_flaw or 'See analysis'}")

                # P0 FIX: Mark any PASS stocks that didn't get a DD verdict
                # (individual stock errors within a batch that otherwise succeeded)
                dd_covered = {r.ticker for r in dd_results}
                for stock in pass_stocks:
                    if stock.symbol not in dd_covered and not stock.dd_verdict:
                        stock.dd_verdict = "DD_ERROR"
                        stock.final_decision = "PENDING_DD"
                        print(f"     ⚠ {stock.symbol} - DD error, marked PENDING_DD")

            except ImportError:
                _pipeline_timer.stop()
                print("  deep_dd.py not found - skipping Deep DD")
                print("     Portfolio will NOT be updated without DD")
                for stock in pass_stocks:
                    stock.dd_verdict = "DD_SKIPPED"
                    stock.final_decision = "PENDING_DD"
            except Exception as e:
                _pipeline_timer.stop()
                print(f"  Deep DD error: {e}")
                import traceback
                traceback.print_exc()
                print("     Portfolio will NOT be updated without DD")
                # P0 FIX: Mark ALL pass stocks as PENDING_DD on batch-level error
                for stock in pass_stocks:
                    if not stock.dd_verdict:  # Don't overwrite if some succeeded before error
                        stock.dd_verdict = "DD_ERROR"
                        stock.final_decision = "PENDING_DD"
                print(f"     ⚠ {len([s for s in pass_stocks if s.final_decision == 'PENDING_DD'])} stock(s) marked PENDING_DD")

    elif args.no_dd and confirmed:
        # DD skipped - warn user that portfolio won't be updated
        pass_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if pass_stocks:
            print("\n  DD SKIPPED (--no-dd flag)")
            print(f"     {len(pass_stocks)} PASS signal(s) will NOT be added to portfolio")
            print("     Run without --no-dd to perform Deep DD and update portfolio")
            for stock in pass_stocks:
                stock.dd_verdict = "DD_SKIPPED"
                stock.final_decision = "PENDING_DD"

    # Print report
    print_final_report(confirmed, sell_signals, stats)
    
    # DD is handled earlier in pipeline via core/deep_dd.run_deep_dd_batch()
    # (Legacy manual DD prompt generation has been removed)
    
    # Save results and generate report (save if any stocks were assessed OR sell signals OR momentum filtered)
    report = None
    briefing_file = None
    try:
        if all_assessed or sell_signals or momentum_rejected:
            report = save_results(confirmed, all_assessed, sell_signals, stats, momentum_rejected, themes_data, archive=args.archive)
            briefing_file = get_current_dir() / "newsletter_briefing.md"
        else:
            # Still generate newsletter briefing for weeks with no signals
            briefing_file = save_newsletter_briefing(confirmed, sell_signals, themes_data, stats, archive=args.archive)
    except Exception as e:
        print(f"  ⚠ Error saving results: {e}")
        import traceback
        traceback.print_exc()
    
    # Portfolio summary and Google Sheets export
    if PORTFOLIO_MANAGER_AVAILABLE:
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
    
    # Print newsletter generation prompts (market context + compilation)
    if not args.no_prompts:
        try:
            print_newsletter_prompts(briefing_file)
        except Exception as e:
            print(f"  ⚠ Error printing newsletter prompts: {e}")

    # (Grok prompts generation removed — replaced by tweet_generator v2)

    # Send email with the formatted report
    if not args.no_email:
        try:
            print("\n" + "─" * 70)
            print("  EMAIL NOTIFICATION")
            print("─" * 70)
            send_notification(confirmed, sell_signals, stats, report)
        except Exception as e:
            print(f"  ⚠ Error sending email notification: {e}")
    
    duration = time.time() - start_time
    
    # P3: Pipeline timing summary
    _pipeline_timer.print_summary()
    
    print(f"\n  Completed in {duration:.1f} seconds")
    print("═" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
