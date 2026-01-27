#!/usr/bin/env python3
"""
BoS MOMENTUM SCANNER - INTEGRATED PIPELINE (WEEKLY TIMEFRAME)
==============================================================

Complete pipeline for WEEKLY momentum trading:

ENTRY CRITERIA:
1. Weekly BoS Up signal fires (price breaks HMA structure high)
2. Stock is in a PRIME or INVESTABLE theme (Thematic Analyzer)
3. Theme fit is STRONG FIT or GOOD FIT
4. Optional: Run Momentum Assessor for final confirmation
5. Decision = PASS → Enter Monday at market open (generates TEAL signal)
6. Decision = CONSIDER → Smaller position or wait for better entry
7. Decision = SKIP → Don't trade

SIGNAL TERMINOLOGY (MASTER_TODO_v2):
- Internal: PASS, CONSIDER, SKIP (scanner decisions)
- Marketing: "TEAL signal" = PASS signal that cleared all 5 gates
- Never use "TRADE" in outputs - use "PASS" internally, "TEAL signal" for marketing

THEME CLASSIFICATION (from Thematic Analyzer):
- PRIME: High conviction theme with strong catalysts + momentum
- INVESTABLE: Good opportunity, standard position sizing
- SELECTIVE: Mixed signals - only best stocks in this theme
- AVOID: Fading momentum or overcrowded - do not invest

NOTE ON MOMENTUM FILTER:
Backtest across 4000+ stocks showed the 4-week momentum filter (<10%)
actually REDUCED returns from +9.2% to +6.1%. Filter has been removed.
4-week momentum is still tracked for informational purposes.

EXIT CRITERIA:
- PRIMARY: Weekly BoS Down signal (price breaks structure low)
- BACKUP: 20% trailing stop from highest close since entry

CONTEXT:
- Weekly timeframe for systematic entries and exits
- Average hold period: 4-8 weeks (can extend to months)
- Audience-neutral - no region-specific investment advice

Usage:
    python scanner.py                    # Full pipeline
    python scanner.py --no-llm           # Skip LLM gates (technical signals only)
    python scanner.py --no-email         # Skip email notification
    python scanner.py --top 100          # Only scan top 100 by beta
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

# Portfolio Manager Integration (unified trade tracking)
# Falls back to legacy CSV handling if portfolio_manager.py not found
try:
    from portfolio_manager import (
        PortfolioManager,
        get_portfolio_manager,
        add_trade_to_portfolio,
        check_portfolio_stops,
        get_open_position_symbols,
        update_portfolio_prices
    )
    PORTFOLIO_MANAGER_AVAILABLE = True
except ImportError:
    PORTFOLIO_MANAGER_AVAILABLE = False
    print("  ℹ️  portfolio_manager.py not found - using legacy CSV tracking")

# Output paths for weekly folder structure
try:
    from output_paths import (
        get_current_dir,
        get_week_dir,
        ensure_output_structure,
        get_relative_path
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False
    # Fallback functions
    def get_current_dir():
        return TRADES_DIR
    def get_week_dir():
        return TRADES_DIR
    def ensure_output_structure():
        return TRADES_DIR, TRADES_DIR
    def get_relative_path(p):
        return str(p)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TICKERS_FILE = BASE_DIR / "complete_tickers.txt"
TRADES_DIR = BASE_DIR / "trades"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
TRADES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Thresholds
BETA_MIN = 1.5           # Pre-filter threshold
BETA_SIGNAL = 1.5        # Signal requirement

# Banker thresholds (new scale: 0-100, centered at 50)
# 50 = at VWAP (neutral), >50 = above VWAP (accumulation)
BANKER_TIER1 = 70.0      # Strong accumulation (price ~4%+ above VWAP)
BANKER_TIER2 = 60.0      # Moderate accumulation (price ~2%+ above VWAP)
BANKER_TIER3 = 55.0      # Slight accumulation (price ~1%+ above VWAP)

# Note: 4-week momentum filter was removed based on backtest results
# Backtest showed filtering by momentum (<10%) actually REDUCED returns
# from +9.2% to +6.1% on average across 4000+ stocks
# Momentum is still tracked for informational purposes but not used as a gate

# Trading parameters
TRAILING_STOP_PCT = 20.0  # 20% trailing stop from highest close


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
    beta: float = 0.0
    banker: float = 0.0
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: dict = field(default_factory=dict)  # Debug info from BoS calculation
    return_20d: float = 0.0
    momentum_4w: float = 0.0  # 4-week momentum for anti-chase filter
    tier: str = ""
    # Thematic analyzer fields
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0
    theme_verdict: str = ""
    # Momentum assessor fields
    final_decision: str = ""  # PASS, CONSIDER, SKIP (use PASS not TRADE - MASTER_TODO_v2)
    conviction: int = 0
    sector_status: str = ""
    upside_potential: str = ""
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""
    # Gatekeeper fields
    catalyst_summary: str = ""
    red_flag_level: str = ""
    action: str = ""
    # Due Diligence fields (from dd_automator.py)
    dd_verdict: str = ""          # STRONG BUY / SPEC BUY / NO GO
    dd_conviction: int = 0        # 1-10 scale
    dd_position_size: str = ""    # FULL / REDUCED / PASS
    dd_analysis: str = ""         # Full analysis text
    dd_key_catalyst: str = ""     # Extracted key catalyst
    dd_fatal_flaw: str = ""       # Extracted fatal flaw (if NO GO)

    def meets_technical_criteria(self) -> bool:
        """Check if stock meets technical signal criteria."""
        return self.beta >= BETA_SIGNAL and self.bos_bullish
    
    def passes_momentum_filter(self) -> bool:
        """
        DEPRECATED: Momentum filter removed based on backtest results.
        Always returns True for backwards compatibility.
        Backtest showed momentum filter reduced returns from +9.2% to +6.1%.
        """
        return True
    
    def meets_all_technical_criteria(self) -> bool:
        """
        Check if stock meets ALL technical criteria.
        Note: Momentum filter removed - this now equals meets_technical_criteria()
        """
        return self.meets_technical_criteria()
    
    def get_tier(self) -> str:
        """Assign tier based on banker level."""
        if not self.meets_technical_criteria():
            return ""
        if self.banker > BANKER_TIER1:
            return "TIER1"
        elif self.banker > BANKER_TIER2:
            return "TIER2"
        elif self.banker > BANKER_TIER3:
            return "TIER3"
        return ""
    
    def passes_theme_gate(self) -> bool:
        """Check if passes thematic analyzer gate."""
        return self.theme_verdict in ["STRONG FIT", "GOOD FIT"]
    
    def passes_final_gate(self) -> bool:
        """Check if passes final momentum assessor gate (generates TEAL signal)."""
        # MASTER_TODO_v2: Standardize on PASS, keep TRADE for backwards compat only
        return self.final_decision in ["PASS", "CONSIDER", "TRADE"]


@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    beta_gte_1_8: int = 0
    beta_gte_2_0: int = 0
    bos_bullish: int = 0
    bos_bearish: int = 0
    banker_gt_5: int = 0
    banker_gt_3: int = 0
    banker_gt_2: int = 0
    meets_technical_gate: int = 0
    momentum_filtered: int = 0  # Stocks filtered by 4w momentum
    passes_momentum: int = 0    # Stocks that pass momentum filter
    tier1: int = 0
    tier2: int = 0
    tier3: int = 0
    theme_confirmed: int = 0
    final_trade: int = 0
    final_consider: int = 0
    final_skip: int = 0


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
        if len(aligned) < 60:
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


def calculate_banker(df: pd.DataFrame) -> float:
    """
    Calculate Banker indicator (institutional accumulation proxy).
    
    Formula: ((Current Price / 20-day VWAP) - 1) * 100 + 50
    
    Interpretation:
    - 50 = Price at VWAP (neutral)
    - >50 = Price above VWAP (accumulation)
    - <50 = Price below VWAP (distribution)
    - >70 = Strong accumulation
    - >90 = Very strong accumulation (parabolic)
    
    Range: 0-100 (uncapped for visibility, but normalized)
    """
    try:
        if len(df) < 20:
            return 0.0
        recent = df.tail(20)
        typical = (recent['High'] + recent['Low'] + recent['Close']) / 3
        vwap = (typical * recent['Volume']).sum() / recent['Volume'].sum()
        current = float(recent['Close'].iloc[-1])
        if vwap == 0:
            return 0.0
        # Calculate how far price is from VWAP as percentage
        # Then normalize to 0-100 scale centered at 50
        deviation_pct = ((current / vwap) - 1) * 100
        banker = 50 + (deviation_pct * 5)  # 1% above VWAP = 55, 2% = 60, etc.
        return round(max(0, min(100, banker)), 1)
    except Exception:
        return 0.0


def calculate_hma(series: pd.Series, length: int) -> pd.Series:
    """
    Calculate Hull Moving Average (HMA).
    HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    """
    import math
    half_length = max(1, length // 2)
    sqrt_length = max(1, int(math.sqrt(length)))
    
    # WMA helper
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
    Pivot high at bar i: series[i] > all values in [i-k, i+k] (excluding i)
    Pivot low at bar i: series[i] < all values in [i-k, i+k] (excluding i)
    
    Returns two series with pivot values (NaN elsewhere).
    Note: Pivots are confirmed k bars after they occur.
    """
    pivot_highs = pd.Series(index=series.index, dtype=float)
    pivot_lows = pd.Series(index=series.index, dtype=float)
    
    for i in range(k, len(series) - k):
        window = series.iloc[i-k:i+k+1]
        center_val = series.iloc[i]
        
        # Check if center is highest in window
        if center_val == window.max() and (window == center_val).sum() == 1:
            # Pivot high confirmed k bars later
            pivot_highs.iloc[i + k] = center_val
        
        # Check if center is lowest in window
        if center_val == window.min() and (window == center_val).sum() == 1:
            # Pivot low confirmed k bars later
            pivot_lows.iloc[i + k] = center_val
    
    return pivot_highs, pivot_lows


def calculate_bos(df: pd.DataFrame, hma_length: int = 21, pivot_k: int = 1) -> Tuple[bool, bool, dict]:
    """
    Calculate Break of Structure signals using HMA PIVOT method.
    
    This matches the TradingView BoS/ChoCH indicator's VISUAL MARKERS:
    - BUY signal (bullish): HMA makes a pivot LOW (lower step line changes)
    - SELL signal (bearish): HMA makes a pivot HIGH (upper step line changes)
    
    These signals ALTERNATE properly (B-S-B-S) making them suitable for trading.
    
    NOTE: This is different from the "price crossing step line" signals
    which do NOT alternate and are not suitable for entry/exit trading.
    
    Parameters:
        df: Daily OHLCV DataFrame
        hma_length: HMA period (default 21)
        pivot_k: Pivot window, bars on each side (default 1)
    
    Returns: (bos_up, bos_down, debug_info)
        bos_up: True if bullish pivot (BUY) confirmed on most recent bar
        bos_down: True if bearish pivot (SELL) confirmed on most recent bar
        debug_info: Dict with HMA, step lines, etc. for verification
    """
    debug_info = {}
    
    try:
        if len(df) < 60:
            return False, False, debug_info
        
        # Resample daily to weekly (Friday close)
        weekly = df.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        if len(weekly) < hma_length + pivot_k + 5:
            return False, False, debug_info
        
        # Calculate HL2 (typical price midpoint)
        hl2 = (weekly['High'] + weekly['Low']) / 2
        
        # Calculate HMA of HL2
        hma = calculate_hma(hl2, hma_length)
        
        # Find pivots on HMA
        pivot_highs, pivot_lows = find_pivots(hma, pivot_k)
        
        # Build step lines (carry forward last pivot value)
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
        
        # HMA PIVOT signals (what creates the visual markers):
        # - Bullish (BUY): Lower step line changes = new pivot low on HMA
        # - Bearish (SELL): Upper step line changes = new pivot high on HMA
        
        if len(weekly) < 2:
            return False, False, debug_info
        
        current_upper = upper.iloc[-1]
        prev_upper = upper.iloc[-2]
        current_lower = lower.iloc[-1]
        prev_lower = lower.iloc[-2]
        current_close = weekly['Close'].iloc[-1]
        
        # BUY signal: lower step changed (new bullish pivot formed)
        bos_up = (not pd.isna(current_lower) and not pd.isna(prev_lower) and 
                  current_lower != prev_lower)
        
        # SELL signal: upper step changed (new bearish pivot formed)  
        bos_down = (not pd.isna(current_upper) and not pd.isna(prev_upper) and 
                    current_upper != prev_upper)
        
        # Build debug info
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
            'bos_up_reason': f"Lower step changed: {prev_lower:.2f} → {current_lower:.2f}" if bos_up else "Lower step unchanged",
            'bos_down_reason': f"Upper step changed: {prev_upper:.2f} → {current_upper:.2f}" if bos_down else "Upper step unchanged",
        }
        
        return bos_up, bos_down, debug_info
        
    except Exception as e:
        debug_info['error'] = str(e)
        return False, False, debug_info


def calculate_bos_simple(df: pd.DataFrame) -> Tuple[bool, bool]:
    """Simple wrapper for calculate_bos that returns just the signals."""
    bos_up, bos_down, _ = calculate_bos(df)
    return bos_up, bos_down


def calculate_bos_daily(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Legacy daily BoS calculation (kept for reference).
    Returns (bullish, bearish).
    """
    try:
        if len(df) < 20:
            return False, False
        recent = df.tail(20)
        high_20 = float(recent['High'].max())
        low_20 = float(recent['Low'].min())
        current = float(recent['Close'].iloc[-1])
        prev_high = float(recent['High'].iloc[-2])
        
        is_bullish = current > high_20 * 0.98 and current > prev_high
        is_bearish = current < low_20 * 1.02
        return is_bullish, is_bearish
    except Exception:
        return False, False


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD & PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def download_and_process(tickers: List[str], benchmark_returns: pd.Series) -> Dict[str, Stock]:
    """Download data and calculate all indicators."""
    stocks = {}
    chunk_size = 50
    chunks = [tickers[i:i+chunk_size] for i in range(0, len(tickers), chunk_size)]
    failed_downloads = []  # Buffer failed downloads

    # Suppress yfinance error output during download
    import io
    import contextlib

    for i, chunk in enumerate(chunks):
        pct = (i + 1) / len(chunks) * 100
        print(f"\r  Downloading: {pct:3.0f}% ({i+1}/{len(chunks)} chunks)", end="", flush=True)

        try:
            # Capture stderr to buffer yfinance errors
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
                    
                    returns = df['Close'].pct_change().dropna()
                    stock.beta = calculate_beta(returns, benchmark_returns)
                    
                    if stock.beta >= BETA_MIN:
                        stock.banker = calculate_banker(df)
                        stock.bos_bullish, stock.bos_bearish, stock.bos_debug = calculate_bos(df)
                        stock.tier = stock.get_tier()
                        
                        # Calculate 4-week momentum (anti-chase filter)
                        # Uses weekly data to match the weekly trading timeframe
                        try:
                            weekly = df.resample('W-FRI').agg({
                                'Close': 'last'
                            }).dropna()
                            if len(weekly) >= 5:
                                close_now = float(weekly['Close'].iloc[-1])
                                close_4w_ago = float(weekly['Close'].iloc[-5])  # 4 weeks back
                                stock.momentum_4w = round((close_now / close_4w_ago - 1) * 100, 1)
                        except Exception:
                            stock.momentum_4w = 0.0
                    
                    stocks[symbol] = stock
                    
                except Exception:
                    continue
                    
        except Exception:
            failed_downloads.extend(chunk)
            continue

        time.sleep(0.3)

    # Clear progress line and show summary
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
        from thematic_analyzer import ThematicAnalyzer, Config
        
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
            })
        
        themes_context = "\n".join(themes_context_lines)
        
        # Step 2: Analyze tickers (analyzer prints full comprehensive details)
        ticker_list = [s.symbol for s in signals]
        analyses = analyzer.run_step_2(ticker_list)
        
        # Map results back to Stock objects
        analysis_map = {a.ticker: a for a in analyses}
        
        confirmed = []
        rejected = []
        
        for stock in signals:
            if stock.symbol in analysis_map:
                a = analysis_map[stock.symbol]
                stock.theme = a.primary_theme or ""
                stock.theme_score = a.theme_score or 0.0
                stock.pure_play_score = a.pure_play_score
                stock.theme_verdict = a.verdict
                
                # Check if passes gate
                if hasattr(a, 'passes_maturity_gate') and callable(a.passes_maturity_gate):
                    if a.passes_maturity_gate():
                        confirmed.append(stock)
                    else:
                        rejected.append(stock)
                elif a.passes_gate():
                    confirmed.append(stock)
                else:
                    rejected.append(stock)
            else:
                stock.theme_verdict = "NOT ANALYZED"
                rejected.append(stock)
        
        # Brief summary (detailed output already shown by analyzer)
        print(f"\n  {'═' * 70}")
        print(f"  THEMATIC GATE COMPLETE")
        print(f"  {'═' * 70}")
        print(f"    ✅ Passing to next stage: {len(confirmed)} stocks")
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
        
        print(f"  ⚠ Theme analysis error: {e}")
        import traceback
        traceback.print_exc()
        for s in signals:
            s.theme_verdict = "ERROR"
        return signals, "", []


# ═══════════════════════════════════════════════════════════════════════════════
# GATEKEEPER - FINAL QUALITY GATE
# ═══════════════════════════════════════════════════════════════════════════════

def run_gatekeeper(signals: List[Stock], top_n: int = None, themes_context: str = "", use_web_search: bool = False) -> List[Stock]:
    """Run thorough Gatekeeper analysis for final PASS/CAUTION/FAIL decision.
    
    This is the FINAL quality gate before entry. Each stock gets individual
    deep analysis to find:
    - Catalysts (earnings, events, product launches)
    - Red flags (dilution, insider selling, governance issues)
    - Analyst sentiment and short interest
    
    Focus: Identifying stocks with 50-100%+ return potential over 3-8 months.
    
    Args:
        signals: List of stocks that passed theme gate
        top_n: If set, only assess top N stocks by Banker score
        themes_context: Pre-identified themes from thematic analyzer
        use_web_search: If True, use web search for current data (recommended for production)
    
    Returns:
        List of stocks that PASS the gatekeeper (ready to trade)
    """
    
    if not signals:
        return []
    
    # If top_n specified, only assess highest conviction candidates
    if top_n and len(signals) > top_n:
        signals = sorted(signals, key=lambda s: -s.banker)[:top_n]
        print(f"\n  📊 Assessing top {top_n} candidates by Banker score")
    
    try:
        from gatekeeper import run_gatekeeper_batch, create_client, GateDecision, print_gatekeeper_summary
        
        print(f"\n  Running GATEKEEPER - Final Quality Gate")
        print(f"  " + "═" * 60)
        print(f"  🎯 Target: 50-100%+ return potential over 3-8 months")
        print(f"  🔍 Checking: Catalysts, Red Flags, Analyst Sentiment")
        if use_web_search:
            print(f"  🌐 Web search ENABLED - current data (6 searches per stock)")
            print(f"  💰 Cost: ~$0.15-0.25 per stock")
        else:
            print(f"  💰 Web search DISABLED - using model knowledge (testing mode)")
            print(f"  💰 Cost: ~$0.02-0.03 per stock")
        print(f"  📊 Analyzing {len(signals)} stocks individually")
        print(f"  " + "─" * 60)
        
        client = create_client()
        
        # Build stock list for gatekeeper
        stock_list = []
        for s in signals:
            stock_list.append({
                "ticker": s.symbol,
                "theme": s.theme or "Unknown",
                "theme_fit": s.theme_verdict or "GOOD",
                "price": s.price,
                "beta": s.beta,
                "banker": s.banker
            })
        
        # Run gatekeeper on all stocks
        results = run_gatekeeper_batch(
            client=client,
            stocks=stock_list,
            themes_context=themes_context,
            delay_between=8.0 if use_web_search else 3.0,  # Shorter delay without web search
            use_web_search=use_web_search
        )
        
        # Map results back to Stock objects
        result_map = {r.ticker: r for r in results}
        confirmed = []
        
        for stock in signals:
            if stock.symbol in result_map:
                r = result_map[stock.symbol]
                
                # Map GateDecision to final_decision (CRIT-1: Use PASS not TRADE)
                if r.decision == GateDecision.PASS:
                    stock.final_decision = "PASS"
                elif r.decision == GateDecision.CAUTION:
                    stock.final_decision = "CONSIDER"
                else:
                    stock.final_decision = "FAIL"
                
                stock.conviction = r.conviction
                stock.sector_status = r.analyst_trend
                stock.upside_potential = "High (50%+)" if r.catalyst_present else "Uncertain"
                stock.bullish_factors = r.key_bullish
                stock.risk_factors = r.key_risks
                stock.reasoning = r.reasoning
                
                # Store additional gatekeeper data
                stock.catalyst_summary = r.catalyst_summary
                stock.red_flag_level = r.red_flag_level
                stock.action = r.action
                
                if stock.passes_final_gate():
                    confirmed.append(stock)
            else:
                stock.final_decision = "ERROR"
                stock.reasoning = "Gatekeeper analysis failed"
        
        # Print summary
        print(f"\n")
        print_gatekeeper_summary(results)
        
        return confirmed
        
    except ImportError as e:
        print(f"  ⚠ gatekeeper.py not found - falling back to basic assessment")
        print(f"     Error: {e}")
        for s in signals:
            s.final_decision = "SKIPPED"
        return signals
        
    except RuntimeError as e:
        if "BILLING_ERROR" in str(e):
            print(f"\n  ❌ API BILLING ERROR DETECTED")
            print(f"     Your Anthropic API credit balance is too low.")
            print(f"     Please add credits at: https://console.anthropic.com/settings/billing")
            print(f"\n  ⏹️  Stopping gatekeeper analysis.")
        else:
            print(f"  ⚠ Gatekeeper error: {e}")
        for s in signals:
            s.final_decision = "NOT_ASSESSED"
        return []
        
    except Exception as e:
        print(f"  ⚠ Gatekeeper error: {e}")
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
    Check for sell signals on open positions.
    
    Uses portfolio_manager.py if available, otherwise falls back to legacy CSV.
    
    EXIT CRITERIA:
    1. PRIMARY: Weekly BoS Down signal
    2. BACKUP: 20% trailing stop from highest close since entry
    """
    
    # Use portfolio_manager if available
    if PORTFOLIO_MANAGER_AVAILABLE:
        return _check_sell_signals_portfolio_manager(stocks)
    else:
        return _check_sell_signals_legacy(stocks)


def _check_sell_signals_portfolio_manager(stocks: Dict[str, Stock]) -> List[SellSignal]:
    """Check sell signals using portfolio_manager (unified tracking)."""
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
            
            # Calculate drawdown
            if trade.highest_close > 0:
                drawdown_pct = ((trade.highest_close - current_price) / trade.highest_close) * 100
            else:
                drawdown_pct = 0
            
            # CHECK EXIT CRITERIA
            sell_reason = None
            
            # PRIMARY: Weekly BoS Down
            if stock.bos_bearish:
                sell_reason = f"Weekly BoS Down (price breaking structure low)"
            
            # BACKUP: 20% trailing stop
            elif drawdown_pct >= TRAILING_STOP_PCT:
                sell_reason = f"Trailing stop hit ({drawdown_pct:.1f}% from high of ${trade.highest_close:.2f})"
            
            if sell_reason:
                sell_signals.append(SellSignal(
                    symbol=symbol,
                    price=current_price,
                    reason=sell_reason,
                    entry_price=trade.entry_price,
                    highest_close=trade.highest_close,
                    drawdown_pct=drawdown_pct
                ))
                # Flag the trade as exited in portfolio
                pm.flag_exit(symbol, current_price, reason=sell_reason)

        # Note: Prices will be updated in main() when export_for_google_sheets() is called
        # No need for duplicate pm.update_prices() here

        return sell_signals
        
    except Exception as e:
        print(f"  ⚠ Error checking sell signals (portfolio_manager): {e}")
        import traceback
        traceback.print_exc()
        return []


def _check_sell_signals_legacy(stocks: Dict[str, Stock]) -> List[SellSignal]:
    """Check sell signals using legacy open_positions.csv."""
    open_positions_file = TRADES_DIR / "open_positions.csv"
    
    if not open_positions_file.exists():
        return []
    
    sell_signals = []
    updated_positions = []
    
    try:
        with open(open_positions_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            symbol = row.get('symbol', row.get('ticker', '')).upper()
            entry_price = float(row.get('entry_price', 0))
            highest_close = float(row.get('highest_close', entry_price))
            
            if symbol not in stocks:
                updated_positions.append(row)
                continue
            
            stock = stocks[symbol]
            current_price = stock.price
            
            if current_price > highest_close:
                highest_close = current_price
            
            if highest_close > 0:
                drawdown_pct = ((highest_close - current_price) / highest_close) * 100
            else:
                drawdown_pct = 0
            
            sell_reason = None
            
            if stock.bos_bearish:
                sell_reason = f"Weekly BoS Down (price breaking structure low)"
            elif drawdown_pct >= TRAILING_STOP_PCT:
                sell_reason = f"Trailing stop hit ({drawdown_pct:.1f}% from high of ${highest_close:.2f})"
            
            if sell_reason:
                sell_signals.append(SellSignal(
                    symbol=symbol,
                    price=current_price,
                    reason=sell_reason,
                    entry_price=entry_price,
                    highest_close=highest_close,
                    drawdown_pct=drawdown_pct
                ))
            else:
                updated_row = row.copy()
                updated_row['highest_close'] = str(highest_close)
                updated_row['current_price'] = str(current_price)
                updated_row['drawdown_pct'] = f"{drawdown_pct:.1f}"
                updated_positions.append(updated_row)
        
        if rows:
            fieldnames = list(rows[0].keys())
            if 'highest_close' not in fieldnames:
                fieldnames.append('highest_close')
            if 'current_price' not in fieldnames:
                fieldnames.append('current_price')
            if 'drawdown_pct' not in fieldnames:
                fieldnames.append('drawdown_pct')
            
            with open(open_positions_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_positions)
        
        return sell_signals
        
    except Exception as e:
        print(f"  ⚠ Error checking sell signals (legacy): {e}")
        return []


def add_to_open_positions(stock: Stock):
    """Add a confirmed trade to open positions for tracking.
    
    Uses portfolio_manager.py if available, otherwise falls back to legacy CSV.
    """
    
    # Use portfolio_manager if available
    if PORTFOLIO_MANAGER_AVAILABLE:
        try:
            add_trade_to_portfolio(stock)
            return
        except Exception as e:
            print(f"  ⚠ Portfolio manager error, falling back to legacy: {e}")
    
    # Legacy CSV handling
    open_positions_file = TRADES_DIR / "open_positions.csv"
    write_header = not open_positions_file.exists()
    
    with open(open_positions_file, 'a', newline='') as f:
        fieldnames = ['symbol', 'entry_date', 'entry_price', 'highest_close', 'tier', 
                      'theme', 'decision', 'conviction', 'current_price', 'drawdown_pct']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()
        
        writer.writerow({
            'symbol': stock.symbol,
            'entry_date': datetime.now().strftime("%Y-%m-%d"),
            'entry_price': stock.price,
            'highest_close': stock.price,
            'tier': stock.tier,
            'theme': stock.theme,
            'decision': stock.final_decision,
            'conviction': stock.conviction,
            'current_price': stock.price,
            'drawdown_pct': '0.0'
        })


def load_open_positions() -> set:
    """Load symbols from open positions for flagging in scanner output.
    
    Uses portfolio_manager.py if available, otherwise falls back to legacy CSV.
    """
    
    # Use portfolio_manager if available
    if PORTFOLIO_MANAGER_AVAILABLE:
        try:
            return get_open_position_symbols()
        except Exception:
            pass  # Fall through to legacy
    
    # Legacy CSV handling
    open_positions_file = TRADES_DIR / "open_positions.csv"

    if not open_positions_file.exists():
        return set()

    try:
        with open(open_positions_file, 'r') as f:
            reader = csv.DictReader(f)
            return {row.get('symbol', '').upper() for row in reader if row.get('symbol')}
    except Exception:
        return set()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

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
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Load Tickers
    # ─────────────────────────────────────────────────────────────────────────
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
        
        benchmark_returns = spy['Close'].pct_change().dropna()
        print(f"  ✓ SPY data: {len(benchmark_returns)} days")
    except Exception as e:
        print(f"  ✗ Benchmark error: {e}")
        return [], [], [], stats, [], []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Download Data & Calculate Indicators
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 3: Downloading Data & Calculating Indicators (WEEKLY BoS)")
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
    # STEP 4: Calculate Statistics
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 4: Filtering & Statistics")
    print("─" * 70)
    
    high_beta_stocks = []
    
    for stock in stocks.values():
        if stock.beta >= BETA_MIN:
            stats.beta_gte_1_8 += 1
            high_beta_stocks.append(stock)
        if stock.beta >= BETA_SIGNAL:
            stats.beta_gte_2_0 += 1
        
        if stock.beta >= BETA_MIN:
            if stock.bos_bullish:
                stats.bos_bullish += 1
            if stock.bos_bearish:
                stats.bos_bearish += 1
            if stock.banker > BANKER_TIER1:
                stats.banker_gt_5 += 1
            if stock.banker > BANKER_TIER2:
                stats.banker_gt_3 += 1
            if stock.banker > BANKER_TIER3:
                stats.banker_gt_2 += 1
    
    high_beta_stocks.sort(key=lambda x: -x.beta)
    
    if top_n and len(high_beta_stocks) > top_n:
        high_beta_stocks = high_beta_stocks[:top_n]
        print(f"  (Limited to top {top_n} by beta)")
    
    print(f"\n  FILTER RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Total tickers scanned:    {stats.tickers_loaded:>6}")
    print(f"  Data downloaded:          {stats.data_downloaded:>6}")
    if verbose:
        # Internal terminology for debugging
        print(f"  Beta >= 1.5:              {stats.beta_gte_1_8:>6}")
        print(f"  Beta >= 2.0:              {stats.beta_gte_2_0:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  HMA Pivot BUY (entry):    {stats.bos_bullish:>6}")
        print(f"  HMA Pivot SELL (caution): {stats.bos_bearish:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  Banker > 70 (Strong):     {stats.banker_gt_5:>6}")
        print(f"  Banker > 60 (Moderate):   {stats.banker_gt_3:>6}")
        print(f"  Banker > 55 (Slight):     {stats.banker_gt_2:>6}")
    else:
        # Marketing-safe terminology
        print(f"  Volatility Expansion:     {stats.beta_gte_1_8:>6}")
        print(f"  High Volatility:          {stats.beta_gte_2_0:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  Structural Breakouts:     {stats.bos_bullish:>6}")
        print(f"  Caution Signals:          {stats.bos_bearish:>6}")
        print(f"  ────────────────────────────────────")
        print(f"  Strong Accumulation:      {stats.banker_gt_5:>6}")
        print(f"  Moderate Accumulation:    {stats.banker_gt_3:>6}")
        print(f"  Slight Accumulation:      {stats.banker_gt_2:>6}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DIAGNOSTIC: Show sample tickers (controlled by --verbose flag)
    # ═══════════════════════════════════════════════════════════════════════════
    sample_size = 10 if verbose else 3

    # Get week ending date once (from any stock with bos_debug)
    week_date = "N/A"
    for s in stocks.values():
        if s.bos_debug and s.bos_debug.get('last_date'):
            week_date = s.bos_debug['last_date']
            break

    print(f"\n  📅 Week ending: {week_date}")

    if verbose:
        print(f"\n  ┌─────────────────────────────────────────────────────────────────┐")
        print(f"  │  DIAGNOSTIC: Sample Tickers (--verbose mode)                    │")
        print(f"  └─────────────────────────────────────────────────────────────────┘")

    # Structural breakout signals (entry candidates)
    bos_up_stocks = [s for s in stocks.values() if s.bos_bullish]
    bos_up_high_beta = [s for s in high_beta_stocks if s.bos_bullish]
    if verbose:
        print(f"\n  🟢 HMA PIVOT BUY: {len(bos_up_stocks)} total, {len(bos_up_high_beta)} with β≥1.5")
    else:
        print(f"\n  🟢 STRUCTURAL BREAKOUTS: {len(bos_up_stocks)} total, {len(bos_up_high_beta)} high-volatility")
    if bos_up_stocks and verbose:
        for s in bos_up_stocks[:sample_size]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"      {s.symbol:<6} β={s.beta:.2f}  ${s.price:<8.2f} Banker={s.banker:.0f}{held_flag}")

    # Caution signals
    bos_down_stocks = [s for s in stocks.values() if s.bos_bearish]
    if verbose:
        print(f"  🔴 HMA PIVOT SELL: {len(bos_down_stocks)} (caution signals)")
    else:
        print(f"  🔴 CAUTION SIGNALS: {len(bos_down_stocks)} (tighten stops)")
    if bos_down_stocks and verbose:
        for s in bos_down_stocks[:sample_size]:
            print(f"      {s.symbol:<6} β={s.beta:.2f}  ${s.price:<8.2f} Banker={s.banker:.0f}")

    # Entry candidates summary
    if verbose:
        print(f"\n  ⭐ ENTRY CANDIDATES (BUY + β≥1.5 + Banker≥55): {len([s for s in bos_up_high_beta if s.banker >= 55])}")
    else:
        print(f"\n  ⭐ ENTRY CANDIDATES (5-Gate Qualified): {len([s for s in bos_up_high_beta if s.banker >= 55])}")
    if bos_up_high_beta:
        for s in sorted(bos_up_high_beta, key=lambda x: -x.banker)[:sample_size]:
            if s.banker >= 55:
                held_flag = " [HELD]" if s.symbol in open_positions else ""
                print(f"      {s.symbol:<6} β={s.beta:.2f}  ${s.price:<8.2f} Banker={s.banker:.0f}  4wMom={s.momentum_4w:+.1f}%{held_flag}")

    if not verbose:
        print(f"\n  💡 Use --verbose for detailed diagnostics")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Apply Technical Signal Gates (BoS + Beta + Banker)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 5: Applying Technical Gates (Beta + BoS + Banker)")
    print("─" * 70)
    print(f"\n  📊 Note: Momentum filter removed based on backtest results")
    print(f"     Backtest showed filtering hurt returns (+9.2% → +6.1%)")
    
    technical_signals = []
    momentum_rejected = []
    
    for stock in high_beta_stocks:
        if stock.meets_technical_criteria():
            stats.meets_technical_gate += 1
            stock.tier = stock.get_tier()
            if stock.tier:
                technical_signals.append(stock)
                if stock.tier == "TIER1":
                    stats.tier1 += 1
                elif stock.tier == "TIER2":
                    stats.tier2 += 1
                elif stock.tier == "TIER3":
                    stats.tier3 += 1
    
    print(f"\n  TECHNICAL GATE RESULTS:")
    print(f"  ────────────────────────────────────")
    print(f"  Beta >= 1.5 AND BoS UP signal: {stats.meets_technical_gate:>4}")
    print(f"  ────────────────────────────────────")
    print(f"  TIER 1 (Banker > 70):        {stats.tier1:>5}")
    print(f"  TIER 2 (Banker > 60):        {stats.tier2:>5}")
    print(f"  TIER 3 (Banker > 55):        {stats.tier3:>5}")
    print(f"  ────────────────────────────────────")
    print(f"  TOTAL TECHNICAL SIGNALS:     {len(technical_signals):>5}")
    
    # Note: momentum_rejected is kept for backwards compatibility but will always be empty
    # as momentum filter was removed based on backtest results
    
    if technical_signals:
        print(f"\n  ✅ TECHNICAL SIGNALS:")
        for s in technical_signals:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"    {s.tier}  {s.symbol:<6} ${s.price:>8.2f}  β={s.beta:.2f}  Banker={s.banker:.1f}  4wMom={s.momentum_4w:+.1f}%{held_flag}")
    
    if not technical_signals:
        print("\n  No technical signals to process")
        sell_signals = check_sell_signals(stocks)
        return [], [], sell_signals, stats, momentum_rejected, []
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Thematic Analyzer Gate
    # ─────────────────────────────────────────────────────────────────────────
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
        
        theme_confirmed, themes_context, themes_data = run_thematic_gate(technical_signals, use_web_search=use_web_search)
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
        sorted_confirmed = sorted(confirmed, key=lambda x: -x.banker)
        for s in sorted_confirmed[:5]:
            held_flag = " [HELD]" if s.symbol in open_positions else ""
            print(f"     {s.symbol:<6} | {s.tier} | Banker={s.banker:.0f} | 20d={s.return_20d:+.1f}%{held_flag}")
        if len(sorted_confirmed) > 5:
            print(f"     ... and {len(sorted_confirmed) - 5} more")
    else:
        print("\n" + "─" * 70)
        print("  STEP 7: Gatekeeper - Final Quality Gate (50-100%+ Return Potential)")
        print("─" * 70)
        
        # Cooldown after thematic analyzer to avoid rate limits
        cooldown_seconds = 30 if use_web_search else 15
        print(f"\n  ⏳ Rate limit cooldown: waiting {cooldown_seconds}s before Gatekeeper...")
        time.sleep(cooldown_seconds)
        
        # Run Gatekeeper - thorough analysis of each stock
        confirmed = run_gatekeeper(
            theme_confirmed, 
            top_n=assess_top_n, 
            themes_context=themes_context,
            use_web_search=use_web_search
        )
        
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
        print(f"  PASS (TEAL signals):       {stats.final_trade:>5}")
        print(f"  CONSIDER:                  {stats.final_consider:>5}")
        print(f"  SKIP:                      {stats.final_skip:>5}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Check Sell Signals (Weekly BoS Down OR 20% Trailing Stop)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  STEP 8: Checking Sell Signals (BoS Down OR 20% Trailing Stop)")
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
        # Separate by decision
        trades = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        considers = [s for s in confirmed if s.final_decision == "CONSIDER"]
        
        if trades:
            print(f"\n  🟢 PASS ({len(trades)}) - Ready for entry:")
            print("  " + "─" * 66)
            
            for s in trades:
                stars = "★" * s.conviction + "☆" * (5 - s.conviction)
                print(f"\n  {s.symbol} | {s.tier} | ${s.price:.2f}")
                print(f"  Conviction: {stars}")
                print(f"  Theme: {s.theme or 'N/A'} ({s.theme_verdict})")
                if s.catalyst_summary:
                    print(f"  📅 Catalyst: {s.catalyst_summary}")
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
        
        if considers:
            print(f"\n  🟡 CAUTION ({len(considers)}) - Wait or size down:")
            print("  " + "─" * 66)
            
            for s in considers:
                stars = "★" * s.conviction + "☆" * (5 - s.conviction)
                print(f"\n  {s.symbol} | {s.tier} | ${s.price:.2f}")
                print(f"  Conviction: {stars}")
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
        
        print("\n  " + "─" * 66)
        print(f"\n  ACTION SUMMARY:")
        if trades:
            print(f"    🟢 PASS (enter): {', '.join(s.symbol for s in trades)}")
        if considers:
            print(f"    🟡 CAUTION (wait/size down): {', '.join(s.symbol for s in considers)}")
        
    else:
        print("\n  NO CONFIRMED BUY SIGNALS")
        print("\n  Pipeline summary:")
        print(f"    • {stats.tickers_loaded} tickers scanned")
        print(f"    • {stats.beta_gte_2_0} with Beta >= 2.0")
        print(f"    • {stats.bos_bullish} with HMA Pivot BUY")
        print(f"    • {stats.meets_technical_gate} met technical gate")
        print(f"    • {stats.theme_confirmed} passed theme gate")
        print(f"    • {stats.final_trade} PASS (TEAL), {stats.final_consider} CONSIDER, {stats.final_skip} SKIP")
    
    if sell_signals:
        print(f"\n  ⚠️ CAUTION SIGNALS ({len(sell_signals)}) - Consider Tightening Stops:")
        print("  " + "─" * 66)
        for s in sell_signals:
            print(f"\n  🔴 {s.symbol} @ ${s.price:.2f}")
            print(f"     Reason: {s.reason}")
            if s.entry_price > 0:
                pnl = ((s.price / s.entry_price) - 1) * 100
                print(f"     Entry: ${s.entry_price:.2f} | High: ${s.highest_close:.2f} | P&L: {pnl:+.1f}%")
            print(f"     ⚠️  This is NOT an automatic exit - use trailing stop")
    
    print(f"\n  " + "═" * 66)
    print(f"  EXIT STRATEGY (Backtested +539% avg vs +294% with signal exits):")
    print(f"    • USE: {TRAILING_STOP_PCT:.0f}% trailing stop from highest weekly close")
    print(f"    • CAUTION: HMA Pivot SELL = tighten stop to 15%, don't exit")
    print(f"    • DO NOT automatically exit on SELL signal")
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
    considers = [s for s in confirmed if s.final_decision == "CONSIDER"] if confirmed else []
    technical_only = [s for s in confirmed if s.final_decision == "TECHNICAL_ONLY"] if confirmed else []
    theme_confirmed = [s for s in confirmed if s.final_decision == "THEME_CONFIRMED"] if confirmed else []
    
    lines = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("=" * 72)
    lines.append("  BoS MOMENTUM SCANNER - WEEKLY REPORT")
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
    
    total_signals = len(trades) + len(considers) + len(technical_only) + len(theme_confirmed)
    if total_signals > 0:
        lines.append(f"  ✅ {total_signals} entry signal(s) identified")
        if trades:
            lines.append(f"     • {len(trades)} PASS (TEAL signals) - High conviction, enter Monday open")
        if considers:
            lines.append(f"     • {len(considers)} CONSIDER - Smaller position recommended")
        if theme_confirmed:
            lines.append(f"     • {len(theme_confirmed)} THEME CONFIRMED - Pending momentum assessment")
        if technical_only:
            lines.append(f"     • {len(technical_only)} TECHNICAL ONLY - Pending LLM analysis")
    else:
        lines.append("  ⚪ No entry signals this week")
    
    if sell_signals:
        lines.append(f"  ⚠️  {len(sell_signals)} caution signal(s) - Consider tightening stops")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCAN STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  SCAN STATISTICS")
    lines.append("─" * 72)
    lines.append(f"  Universe scanned:          {stats.tickers_loaded:>6}")
    lines.append(f"  Data retrieved:            {stats.data_downloaded:>6}")
    lines.append(f"  High beta (≥1.5):          {stats.beta_gte_1_8:>6}")
    lines.append("")
    lines.append(f"  BoS BUY signals:           {stats.bos_bullish:>6}")
    lines.append(f"  Met technical gate:        {stats.meets_technical_gate:>6}")
    lines.append(f"  Theme confirmed:           {stats.theme_confirmed:>6}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY SIGNALS
    # ═══════════════════════════════════════════════════════════════════════════
    if trades or considers or technical_only or theme_confirmed:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ENTRY SIGNALS")
        lines.append("─" * 72)

        # Table header
        lines.append("")
        lines.append(f"  {'TIER':<6} {'SYMBOL':<7} {'PRICE':>9} {'BETA':>6} {'BANKER':>7} {'4W MOM':>8} {'THEME':<20}")
        lines.append("  " + "-" * 68)

        all_entry_signals = trades + considers + technical_only + theme_confirmed
        all_entry_signals.sort(key=lambda x: (-{'TIER1': 3, 'TIER2': 2, 'TIER3': 1}.get(x.tier, 0), -x.banker))
        
        for s in all_entry_signals:
            theme_short = (s.theme[:18] + "..") if s.theme and len(s.theme) > 20 else (s.theme or "N/A")
            lines.append(f"  {s.tier:<6} {s.symbol:<7} ${s.price:>7.2f} {s.beta:>6.2f} {s.banker:>7.1f} {s.momentum_4w:>+7.1f}% {theme_short:<20}")
        
        # Detailed breakdown for each signal
        lines.append("")
        lines.append("  SIGNAL DETAILS:")
        lines.append("  " + "-" * 68)
        
        for s in all_entry_signals:
            decision_label = s.final_decision if s.final_decision else "PASSED"
            lines.append(f"")
            lines.append(f"  ■ {s.symbol} ({s.tier}) - {decision_label}")
            lines.append(f"    Price: ${s.price:.2f} | Beta: {s.beta:.2f} | Banker: {s.banker:.1f}")
            lines.append(f"    4-Week Momentum: {s.momentum_4w:+.1f}% | 20-Day Return: {s.return_20d:+.1f}%")
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
    # CAUTION SIGNALS (Sell signals from existing positions)
    # ═══════════════════════════════════════════════════════════════════════════
    if sell_signals:
        lines.append("")
        lines.append("─" * 72)
        lines.append("  ⚠️  CAUTION SIGNALS - Consider Tightening Stops")
        lines.append("─" * 72)
        lines.append("  These are NOT automatic exit signals. Based on backtesting,")
        lines.append("  trailing stops outperform signal-based exits (+539% vs +294%).")
        lines.append("")
        
        for s in sell_signals:
            lines.append(f"  ■ {s.symbol} @ ${s.price:.2f}")
            lines.append(f"    Reason: {s.reason}")
            if s.entry_price > 0:
                pnl = ((s.price / s.entry_price) - 1) * 100
                lines.append(f"    Entry: ${s.entry_price:.2f} | High: ${s.highest_close:.2f} | P&L: {pnl:+.1f}%")
            lines.append(f"    Action: Tighten stop to 15% from high, do NOT exit automatically")
            lines.append("")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXIT STRATEGY REMINDER
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  EXIT STRATEGY")
    lines.append("─" * 72)
    lines.append(f"  PRIMARY:  {TRAILING_STOP_PCT:.0f}% trailing stop from highest weekly close")
    lines.append("  CAUTION:  HMA Pivot SELL = tighten stop to 15%, do NOT auto-exit")
    lines.append("")
    lines.append("  Based on backtesting across 8 trending stocks:")
    lines.append("    • Signal-based exits: +294% average return")
    lines.append("    • Trailing stop exits: +539% average return")
    lines.append("  The trailing stop keeps you in strong trends longer.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENTRY CRITERIA REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("─" * 72)
    lines.append("  ENTRY CRITERIA REFERENCE")
    lines.append("─" * 72)
    lines.append("  1. HMA Pivot BUY (lower step line changes = bullish structure)")
    lines.append("  2. Beta ≥ 1.5 (high momentum stock)")
    lines.append("  3. Banker > 55 (institutional accumulation)")
    lines.append("  4. Strong/Good theme fit (in hot sector)")
    lines.append("")
    lines.append("  TIER ASSIGNMENT:")
    lines.append("    • TIER 1: Banker > 70 (highest conviction)")
    lines.append("    • TIER 2: Banker > 60 (strong conviction)")
    lines.append("    • TIER 3: Banker > 55 (moderate conviction)")
    
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
        # Separate PASS (TEAL signals) and CONSIDER signals
        # MASTER_TODO_v2: Use PASS internally, "TEAL signal" for marketing
        trades = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        considers = [s for s in confirmed if s.final_decision == "CONSIDER"]
        technical_only = [s for s in confirmed if s.final_decision in ["TECHNICAL_ONLY", "THEME_CONFIRMED"]]
        
        if trades:
            lines.append("### 🟢 PASS - Ready for Entry (TEAL Signals)")
            lines.append("")
            for s in trades:
                lines.append(f"#### {s.symbol}")
                lines.append("")
                lines.append(f"| Metric | Value |")
                lines.append(f"|--------|-------|")
                lines.append(f"| **Price** | ${s.price:.2f} |")
                lines.append(f"| **Theme** | {s.theme or 'N/A'} ({s.theme_verdict}) |")
                lines.append(f"| **Tier** | {s.tier} |")
                lines.append(f"| **Beta** | {s.beta:.2f} |")
                lines.append(f"| **Banker** | {s.banker:.0f} |")
                lines.append(f"| **Conviction** | {'★' * s.conviction}{'☆' * (5 - s.conviction)} |")
                if s.catalyst_summary:
                    lines.append(f"| **Catalyst** | {s.catalyst_summary} |")
                if s.red_flag_level:
                    lines.append(f"| **Red Flags** | {s.red_flag_level} |")
                lines.append("")
                
                if s.bullish_factors:
                    lines.append("**Bullish Factors:**")
                    for factor in s.bullish_factors[:3]:
                        lines.append(f"- {factor}")
                    lines.append("")
                
                if s.risk_factors:
                    lines.append("**Risk Factors:**")
                    for risk in s.risk_factors[:3]:
                        lines.append(f"- {risk}")
                    lines.append("")
                
                if s.reasoning:
                    lines.append("**Analysis:**")
                    lines.append(f"> {s.reasoning}")
                    lines.append("")
                
                if s.action:
                    lines.append(f"**Recommended Action:** {s.action}")
                    lines.append("")
                
                lines.append(f"📸 **[CHART: {s.symbol}]** - *Add TradingView screenshot*")
                lines.append("")
                lines.append("---")
                lines.append("")
        
        if considers:
            lines.append("### 🟡 CAUTION - Wait or Size Down")
            lines.append("")
            for s in considers:
                lines.append(f"#### {s.symbol}")
                lines.append("")
                lines.append(f"| Metric | Value |")
                lines.append(f"|--------|-------|")
                lines.append(f"| **Price** | ${s.price:.2f} |")
                lines.append(f"| **Theme** | {s.theme or 'N/A'} ({s.theme_verdict}) |")
                lines.append(f"| **Tier** | {s.tier} |")
                lines.append(f"| **Conviction** | {'★' * s.conviction}{'☆' * (5 - s.conviction)} |")
                if s.catalyst_summary:
                    lines.append(f"| **Catalyst** | {s.catalyst_summary} |")
                lines.append("")
                
                if s.risk_factors:
                    lines.append("**Concerns:**")
                    for risk in s.risk_factors[:3]:
                        lines.append(f"- {risk}")
                    lines.append("")
                
                if s.reasoning:
                    lines.append("**Analysis:**")
                    lines.append(f"> {s.reasoning}")
                    lines.append("")
                
                if s.action:
                    lines.append(f"**Recommended Action:** {s.action}")
                    lines.append("")
                
                lines.append(f"📸 **[CHART: {s.symbol}]** - *Add TradingView screenshot*")
                lines.append("")
                lines.append("---")
                lines.append("")
        
        if technical_only:
            lines.append("### ⚪ PENDING DUE DILIGENCE")
            lines.append("")
            lines.append("*These stocks passed technical and thematic gates but require manual due diligence:*")
            lines.append("")
            for s in technical_only:
                lines.append(f"- **{s.symbol}** - ${s.price:.2f} | {s.theme or 'N/A'} | Tier {s.tier} | Banker {s.banker:.0f}")
            lines.append("")
            lines.append("---")
            lines.append("")
    else:
        lines.append("*No new signals this week*")
        lines.append("")
        if stats:
            lines.append("**Pipeline Summary:**")
            lines.append(f"- Tickers scanned: {stats.tickers_loaded}")
            lines.append(f"- Weekly BoS Up: {stats.bos_bullish}")
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
        open_positions_file = TRADES_DIR / "open_positions.csv"
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
    # SELL/CAUTION SIGNALS
    # ─────────────────────────────────────────────────────────────────────────
    if sell_signals:
        lines.append("### ⚠️ Caution Signals (Consider Tightening Stops)")
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
        lines.append("*Note: These are CAUTION signals, not automatic exits. Based on backtesting, trailing stops outperform signal-based exits.*")
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

    # Also save to legacy location for backwards compatibility
    latest_file = TRADES_DIR / "latest_newsletter_briefing.md"
    with open(latest_file, 'w') as f:
        f.write(briefing)

    # Save dated archive only if --archive flag (legacy format)
    if archive:
        briefing_file = TRADES_DIR / f"newsletter_briefing_{date_str}.md"
        with open(briefing_file, 'w') as f:
            f.write(briefing)

    print(f"\n  📰 Newsletter briefing:")
    print(f"     • {rel_path(briefing_current)} (current week)")
    print(f"     • {rel_path(briefing_archive)} (archived)")
    if archive:
        print(f"     • {rel_path(briefing_file)} (dated)")

    return latest_file


def generate_grok_prompts(
    briefing_file: Path,
    confirmed: List[Stock] = None,
    sell_signals: List[SellSignal] = None,
    themes_data: List[dict] = None,
    stats: ScanStats = None
):
    """
    Generate 21 Grok prompts for weekly X/Twitter content.
    
    This function creates contextual prompts based on scanner outputs that can be
    copied into Grok to generate ready-to-post tweets.
    """
    try:
        from grok_prompts_generator import (
            PortfolioData, 
            parse_briefing_markdown, 
            load_open_positions_csv,
            load_themes_cache,
            generate_weekly_prompts,
            save_prompts,
            OUTPUT_DIR
        )
    except ImportError:
        print("\n  ⚠️  grok_prompts_generator.py not found - skipping Grok prompt generation")
        print("     Place grok_prompts_generator.py in the same directory as scanner.py")
        return
    
    print("\n" + "─" * 70)
    print("  GROK PROMPTS GENERATION")
    print("─" * 70)
    
    # Parse briefing to get portfolio data
    data = parse_briefing_markdown(briefing_file)
    
    # Supplement with direct data if available
    if confirmed:
        # Add PASS signals
        for s in confirmed:
            if s.final_decision in ["PASS", "TRADE"] and s.symbol not in [x.get('ticker') for x in data.pass_signals]:
                data.pass_signals.append({
                    'ticker': s.symbol,
                    'price': s.price,
                    'theme': s.theme or 'Unknown',
                    'catalyst': s.catalyst_summary or '',
                    'reasoning': s.reasoning or ''
                })
            elif s.final_decision == "CONSIDER" and s.symbol not in [x.get('ticker') for x in data.caution_signals]:
                data.caution_signals.append({
                    'ticker': s.symbol,
                    'price': s.price,
                    'theme': s.theme or 'Unknown',
                    'concerns': s.risk_factors or [],
                    'reasoning': s.reasoning or ''
                })
    
    if sell_signals:
        for s in sell_signals:
            if s.symbol not in [x.get('ticker') for x in data.sell_signals]:
                data.sell_signals.append({
                    'ticker': s.symbol,
                    'price': s.price,
                    'reason': s.reason,
                    'entry_price': s.entry_price,
                    'highest_close': s.highest_close,
                    'pnl': f"{((s.price / s.entry_price) - 1) * 100:+.1f}%" if s.entry_price > 0 else "+0%"
                })
    
    if themes_data:
        for t in themes_data:
            classification = t.get('classification', 'INVESTABLE')
            theme_dict = {'name': t.get('name', 'Unknown'), 'classification': classification}
            
            if classification == 'PRIME' and theme_dict not in data.prime_themes:
                data.prime_themes.append(theme_dict)
            elif classification == 'INVESTABLE' and theme_dict not in data.investable_themes:
                data.investable_themes.append(theme_dict)
            elif classification == 'SELECTIVE' and theme_dict not in data.selective_themes:
                data.selective_themes.append(theme_dict)
            elif classification == 'AVOID' and theme_dict not in data.avoid_themes:
                data.avoid_themes.append(theme_dict)
    
    if stats:
        data.scan_stats = {
            'tickers_scanned': stats.tickers_loaded,
            'bos_bullish': stats.bos_bullish,
            'technical_signals': stats.meets_technical_gate,
            'theme_confirmed': stats.theme_confirmed
        }
    
    # Also load from CSV/cache if available
    if not data.open_positions:
        csv_positions = load_open_positions_csv(TRADES_DIR)
        if csv_positions:
            data.open_positions = csv_positions
    
    if not data.prime_themes and not data.investable_themes:
        themes_cache = load_themes_cache(BASE_DIR)
        for theme in themes_cache:
            classification = theme.get('classification', 'INVESTABLE')
            if classification == 'PRIME':
                data.prime_themes.append(theme)
            elif classification == 'INVESTABLE':
                data.investable_themes.append(theme)
            elif classification == 'SELECTIVE':
                data.selective_themes.append(theme)
            elif classification == 'AVOID':
                data.avoid_themes.append(theme)
    
    # Generate prompts
    prompts = generate_weekly_prompts(data)
    
    # Save to output directory
    output_dir = TRADES_DIR / "grok_prompts"
    main_file = save_prompts(prompts, data, output_dir)
    
    # Helper for relative paths
    def rel_path(p: Path) -> str:
        return str(p.relative_to(Path.cwd())) if str(p).startswith(str(Path.cwd())) else str(p)

    # Summary
    print(f"\n  ✅ Generated {len(prompts)} Grok prompts for the week")
    print(f"\n  📁 Grok prompts: {rel_path(output_dir)}/latest_grok_prompts.md")
    print("")
    print("  📅 Weekly Schedule:")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        day_prompts = [p for p in prompts if p.day == day]
        titles = [p.title[:22] for p in sorted(day_prompts, key=lambda x: x.slot)]
        if titles:
            print(f"     {day:10} | {' | '.join(titles)}")
    print("")
    print("  💡 Copy prompts to Grok (X's AI) to generate ready-to-post tweets")

    # ─────────────────────────────────────────────────────────────────────────
    # PRINT FULL PROMPTS IN TERMINAL
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  FULL GROK PROMPTS (21 FOR THE WEEK)")
    print("═" * 70)

    for day in days:
        day_prompts = sorted([p for p in prompts if p.day == day], key=lambda x: x.slot)
        if day_prompts:
            print(f"\n  ╔{'═' * 66}╗")
            print(f"  ║  {day.upper():^62}  ║")
            print(f"  ╚{'═' * 66}╝")

            for p in day_prompts:
                slot_times = {1: "08:00 AM", 2: "12:00 PM", 3: "06:00 PM"}
                slot_time = slot_times.get(p.slot, f"Slot {p.slot}")

                print(f"\n  ┌─ {slot_time} │ {p.title} {'─' * max(1, 50 - len(p.title) - len(slot_time))}┐")
                print(f"  │ Category: {p.category}")
                if p.ticker:
                    print(f"  │ Ticker: ${p.ticker}")
                if p.theme:
                    print(f"  │ Theme: {p.theme}")
                print(f"  │ Visual: {p.visual_suggestion}")
                print(f"  └{'─' * 68}┘")
                print("")
                print("  PROMPT:")
                print("  " + "─" * 68)
                # Indent and wrap prompt text
                for line in p.prompt.strip().split('\n'):
                    # Wrap long lines
                    while len(line) > 64:
                        print(f"  │ {line[:64]}")
                        line = line[64:]
                    print(f"  │ {line}")
                print("  " + "─" * 68)

    print("\n" + "═" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE GROK PROMPTS SUMMARY TO TEXT FILE
    # ─────────────────────────────────────────────────────────────────────────
    summary_lines = []
    summary_lines.append("=" * 72)
    summary_lines.append("  GROK PROMPTS SUMMARY - 21 WEEKLY X/TWITTER PROMPTS")
    summary_lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("=" * 72)
    summary_lines.append("")
    summary_lines.append("  Copy prompts to Grok (X's AI) to generate ready-to-post tweets.")
    summary_lines.append("")
    summary_lines.append("  📅 WEEKLY SCHEDULE:")
    summary_lines.append("  " + "-" * 68)
    for day in days:
        day_prompts = [p for p in prompts if p.day == day]
        titles = [p.title[:22] for p in sorted(day_prompts, key=lambda x: x.slot)]
        if titles:
            summary_lines.append(f"     {day:10} | {' | '.join(titles)}")
    summary_lines.append("  " + "-" * 68)
    summary_lines.append("")

    for day in days:
        day_prompts = sorted([p for p in prompts if p.day == day], key=lambda x: x.slot)
        if day_prompts:
            summary_lines.append("")
            summary_lines.append("=" * 72)
            summary_lines.append(f"  {day.upper()}")
            summary_lines.append("=" * 72)

            for p in day_prompts:
                slot_times = {1: "08:00 AM", 2: "12:00 PM", 3: "06:00 PM"}
                slot_time = slot_times.get(p.slot, f"Slot {p.slot}")

                summary_lines.append("")
                summary_lines.append("-" * 72)
                summary_lines.append(f"  {slot_time} | {p.title}")
                summary_lines.append("-" * 72)
                summary_lines.append(f"  Category: {p.category}")
                if p.ticker:
                    summary_lines.append(f"  Ticker: ${p.ticker}")
                if p.theme:
                    summary_lines.append(f"  Theme: {p.theme}")
                summary_lines.append(f"  Visual: {p.visual_suggestion}")
                summary_lines.append("")
                summary_lines.append("  PROMPT:")
                summary_lines.append("")
                for line in p.prompt.strip().split('\n'):
                    summary_lines.append(f"    {line}")
                summary_lines.append("")

    summary_lines.append("")
    summary_lines.append("=" * 72)
    summary_lines.append("  END OF GROK PROMPTS")
    summary_lines.append("=" * 72)

    # Save to text file
    summary_file = output_dir / "grok_prompts_summary.txt"
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary_lines))

    print(f"\n  📄 Summary saved: {rel_path(summary_file)}")


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
    print("    3. DD outputs for each PASS signal (from due_diligence_prompts.py)")
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

**5. WATCHLIST** (if any 🟡 CAUTION signals)
- Stocks worth watching and why waiting

**6. PORTFOLIO UPDATE**
- Open positions with current P&L
- Any caution/sell signals

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

    # Build signals JSON data
    signals_data = {
        "timestamp": timestamp,
        "timeframe": "WEEKLY",
        "entry_criteria": "Weekly BoS Up + Hot Theme + PASS decision (generates TEAL signal)",
        "exit_criteria": f"Weekly BoS Down OR {TRAILING_STOP_PCT}% trailing stop",
        "stats": {
            "tickers_loaded": stats.tickers_loaded,
            "data_downloaded": stats.data_downloaded,
            "beta_gte_2_0": stats.beta_gte_2_0,
            "weekly_bos_up": stats.bos_bullish,
            "technical_signals": stats.meets_technical_gate,
            "theme_confirmed": stats.theme_confirmed,
            "final_trade": stats.final_trade,  # Count of PASS signals (TEAL signals)
            "final_consider": stats.final_consider,
        },
        # Themes data for tweet generator
        "themes": themes_data if themes_data else [],
        # PHASE 10: Separated pass_signals (TEAL signals) from consider_signals per MASTER_TODO
        "pass_signals": [
            {
                "symbol": s.symbol,
                "tier": s.tier,
                "price": s.price,
                "beta": s.beta,
                "banker": s.banker,
                "return_20d": s.return_20d,
                "theme": s.theme,
                "theme_score": s.theme_score,
                "pure_play_score": s.pure_play_score,
                "theme_verdict": s.theme_verdict,
                "final_decision": "PASS",  # Normalize to PASS for downstream
                "conviction": s.conviction,
                "sector_status": s.sector_status,
                "upside_potential": s.upside_potential,
                "bullish_factors": s.bullish_factors,
                "risk_factors": s.risk_factors,
                "reasoning": s.reasoning,
                "action": "Enter Monday at market open",
                "dd_verdict": s.dd_verdict,
                "dd_conviction": s.dd_conviction,
                "dd_position_size": s.dd_position_size,
                "dd_key_catalyst": s.dd_key_catalyst,
                "dd_fatal_flaw": s.dd_fatal_flaw
            }
            for s in confirmed if s.final_decision in ["PASS", "TRADE"]  # TRADE for backwards compat
        ],
        "consider_signals": [
            {
                "symbol": s.symbol,
                "tier": s.tier,
                "price": s.price,
                "beta": s.beta,
                "banker": s.banker,
                "return_20d": s.return_20d,
                "theme": s.theme,
                "theme_score": s.theme_score,
                "pure_play_score": s.pure_play_score,
                "theme_verdict": s.theme_verdict,
                "final_decision": s.final_decision,
                "conviction": s.conviction,
                "sector_status": s.sector_status,
                "upside_potential": s.upside_potential,
                "bullish_factors": s.bullish_factors,
                "risk_factors": s.risk_factors,
                "reasoning": s.reasoning,
                "action": "Consider smaller position - watching for gate 5",
                "dd_verdict": s.dd_verdict,
                "dd_conviction": s.dd_conviction,
                "dd_position_size": s.dd_position_size,
                "dd_key_catalyst": s.dd_key_catalyst,
                "dd_fatal_flaw": s.dd_fatal_flaw
            }
            for s in confirmed if s.final_decision == "CONSIDER"
        ],
        # Legacy: buy_signals includes all confirmed for backwards compatibility
        "buy_signals": [
            {
                "symbol": s.symbol,
                "tier": s.tier,
                "price": s.price,
                "beta": s.beta,
                "banker": s.banker,
                "return_20d": s.return_20d,
                "theme": s.theme,
                "theme_score": s.theme_score,
                "pure_play_score": s.pure_play_score,
                "theme_verdict": s.theme_verdict,
                "final_decision": s.final_decision,
                "conviction": s.conviction,
                "sector_status": s.sector_status,
                "upside_potential": s.upside_potential,
                "bullish_factors": s.bullish_factors,
                "risk_factors": s.risk_factors,
                "reasoning": s.reasoning,
                "action": (
                    "Enter Monday at market open" if s.final_decision in ["PASS", "TRADE"]
                    else "Consider smaller position" if s.final_decision == "CONSIDER"
                    else "Pending LLM analysis" if s.final_decision in ["TECHNICAL_ONLY", "THEME_CONFIRMED"]
                    else "Review required"
                ),
                "dd_verdict": s.dd_verdict,
                "dd_conviction": s.dd_conviction,
                "dd_position_size": s.dd_position_size,
                "dd_key_catalyst": s.dd_key_catalyst,
                "dd_fatal_flaw": s.dd_fatal_flaw
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
                "drawdown_pct": s.drawdown_pct
            }
            for s in sell_signals
        ],
        # NEW: Historical wins tracking (marketing overhaul)
        "historical_winners": [],
        "big_wins": [],
        "home_runs": [],
    }

    # Populate historical wins from signal_tracker (if available)
    try:
        from signal_tracker import load_historical_signals, find_big_wins
        from config import MARKETING_THRESHOLDS

        historical = load_historical_signals()
        signals_data["historical_winners"] = [
            {
                "ticker": h.ticker,
                "entry_price": h.entry_price,
                "current_price": h.current_price,
                "pnl_pct": h.pnl_pct,
                "signal_date": h.signal_date,
                "theme": h.theme,
            }
            for h in historical if h.pnl_pct >= MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)
        ]

        big_wins = find_big_wins(threshold=MARKETING_THRESHOLDS.get('big_win_threshold', 25.0))
        signals_data["big_wins"] = [
            {
                "ticker": w.ticker,
                "entry_price": w.entry_price,
                "current_price": w.current_price,
                "pnl_pct": w.pnl_pct,
                "signal_date": w.signal_date,
                "theme": w.theme,
                "threshold_crossed": w.threshold_crossed,
            }
            for w in big_wins
        ]

        home_runs = find_big_wins(threshold=MARKETING_THRESHOLDS.get('home_run_threshold', 50.0))
        signals_data["home_runs"] = [
            {
                "ticker": w.ticker,
                "entry_price": w.entry_price,
                "current_price": w.current_price,
                "pnl_pct": w.pnl_pct,
                "signal_date": w.signal_date,
                "theme": w.theme,
                "threshold_crossed": w.threshold_crossed,
            }
            for w in home_runs
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

    # Also save to legacy location for backwards compatibility
    signals_file = TRADES_DIR / "signals.json"
    with open(signals_file, 'w') as f:
        f.write(signals_json)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPREHENSIVE ANALYSIS LOG - ALL assessed stocks for back-analysis
    # ═══════════════════════════════════════════════════════════════════════════
    analysis_log = TRADES_DIR / "analysis_log.csv"
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
                'passed_all_gates': 'YES' if s.final_decision in ['PASS', 'TRADE', 'CONSIDER'] else 'NO'
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

    # Also save to legacy location for backwards compatibility
    latest_report = TRADES_DIR / "latest_report.txt"
    with open(latest_report, 'w') as f:
        f.write(report)

    # Save dated archive file only if --archive flag (legacy format)
    if archive:
        report_file = TRADES_DIR / f"report_{date_str}.txt"
        with open(report_file, 'w') as f:
            f.write(report)

    print(f"\n  📁 Results saved:")
    print(f"     • {rel_path(signals_current)} (current week)")
    print(f"     • {rel_path(signals_archive)} (archived)")
    print(f"     • {rel_path(signals_file)} (legacy)")
    print(f"     • {rel_path(analysis_log)}")
    print(f"     • {rel_path(report_current)} (current week)")
    if archive:
        print(f"     • {rel_path(report_file)} (dated archive)")

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE NEWSLETTER BRIEFING
    # ═══════════════════════════════════════════════════════════════════════════
    save_newsletter_briefing(confirmed, sell_signals, themes_data, stats, archive=archive, current_dir=current_dir, week_dir=week_dir)

    return report  # Return report for email use


def send_notification(confirmed: List[Stock], sell_signals: List[SellSignal], stats: ScanStats, report: str = None):
    """Send email notification with formatted report."""
    try:
        from email_notifier import send_email, load_config
        
        config = load_config()
        if not config:
            print("  ⚠ Email not configured (run: python email_notifier.py setup)")
            return
        
        # Generate subject line
        if confirmed or sell_signals:
            trades = len([s for s in confirmed if s.final_decision in ["PASS", "TRADE", "TECHNICAL_ONLY", "THEME_CONFIRMED"]]) if confirmed else 0
            considers = len([s for s in confirmed if s.final_decision == "CONSIDER"]) if confirmed else 0
            cautions = len(sell_signals) if sell_signals else 0
            
            parts = []
            if trades:
                parts.append(f"{trades} Entry")
            if considers:
                parts.append(f"{considers} Consider")
            if cautions:
                parts.append(f"{cautions} Caution")
            
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
    parser.add_argument("--no-momentum", action="store_true", help="Skip gatekeeper (keep theme analysis) - faster but less thorough")
    parser.add_argument("--assess-top", type=int, metavar="N", help="Only run gatekeeper on top N stocks by Banker score")
    parser.add_argument("--no-email", action="store_true", help="Skip email notification")
    parser.add_argument("--no-prompts", action="store_true", help="Skip printing DD and newsletter prompts at the end")
    # Keep --no-dd-prompts as alias for backwards compatibility
    parser.add_argument("--no-dd-prompts", action="store_true", dest="no_prompts", help=argparse.SUPPRESS)
    parser.add_argument("--no-grok-prompts", action="store_true", help="Skip generating Grok/X prompts")
    parser.add_argument("--top", type=int, help="Only scan top N stocks by beta")
    parser.add_argument("--web-search", action="store_true", help="Enable web search for Thematic Analyzer AND Gatekeeper. Recommended for production scans.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed diagnostic output (10 items per category instead of 3)")
    parser.add_argument("--archive", action="store_true", help="Save dated archive files in addition to latest_* files")
    # Due Diligence options (DD runs by default now)
    parser.add_argument("--no-dd", action="store_true", help="Skip automated due diligence (NOT recommended - portfolio won't be updated)")
    parser.add_argument("--full-dd", action="store_true", help="Run FULL due diligence using Opus (slower, deeper analysis)")
    parser.add_argument("--dd-top", type=int, metavar="N", help="Only run DD on top N stocks by conviction")
    parser.add_argument("--save-dd", action="store_true", help="Save DD reports to reports/ directory")
    # Keep --dd for backwards compatibility (now a no-op since DD is default)
    parser.add_argument("--dd", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    
    # Header
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "BoS MOMENTUM SCANNER - WEEKLY TIMEFRAME".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Show entry/exit criteria (marketing-safe by default, detailed with --verbose)
    if args.verbose:
        print("\n  ENTRY: BoS UP + Beta ≥1.5 + Banker ≥55 + Theme Gate")
        print(f"  EXIT:  {TRAILING_STOP_PCT:.0f}% Trailing Stop from highest close")
        print("         (SELL signal = caution only, NOT automatic exit)")
    else:
        print("\n  ENTRY: 5-Gate Screening (Volatility + Institutional + Theme + Forensic Audit)")
        print("  EXIT:  Capital Preservation Protocol (systematic risk management)")
        print("         (Caution signals = tighten stops, NOT automatic exit)")
    
    # Show pipeline based on options
    if args.no_llm:
        print("\n  Pipeline: Technical signals only (ALL LLM gates skipped)")
        print("  Cost: $0.00 (free)")
    elif args.no_momentum:
        print("\n  Pipeline: Technical → Thematic Analyzer (gatekeeper skipped)")
        web_cost = " + web search" if args.web_search else ""
        print(f"  Cost: ~$0.15/run{web_cost}")
    elif args.assess_top:
        print(f"\n  Pipeline: Technical → Thematic → Gatekeeper (top {args.assess_top} only)")
        if args.web_search:
            print(f"  Cost: ~${0.15 + (args.assess_top * 0.20):.2f}/run (with web search)")
        else:
            print(f"  Cost: ~${0.15 + (args.assess_top * 0.03):.2f}/run (no web search - testing)")
    else:
        print("\n  Pipeline: Technical → Thematic → Gatekeeper (thorough)")
        if args.web_search:
            print("  Cost: ~$1-3/run (web search enabled)")
        else:
            print("  Cost: ~$0.30-0.50/run (no web search - testing)")
        print("  Schedule: Run WEEKLY (signals only change on Friday close)")
    
    if args.web_search:
        print("\n  🌐 Web search ENABLED:")
        print("     • Thematic: Current theme momentum")
        print("     • Gatekeeper: 6 searches per stock (catalysts, red flags, etc.)")
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

    # Step 7.5: Automated Due Diligence (runs by default now)
    # DD is required for portfolio updates - only DD-PASS signals get added
    dd_results = []
    dd_pass_stocks = []
    dd_fail_stocks = []

    if not args.no_dd and confirmed and not args.no_llm:
        pass_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if pass_stocks:
            print("\n" + "─" * 70)
            print("  STEP 7.5: AUTOMATED DUE DILIGENCE")
            print("─" * 70)
            print("  📋 DD is REQUIRED before adding to portfolio")
            print("     Only STRONG BUY / SPEC BUY verdicts will be added")

            try:
                from dd_automator import run_automated_dd

                # Limit stocks if --dd-top specified
                dd_stocks = pass_stocks[:args.dd_top] if args.dd_top else pass_stocks

                # Run DD
                dd_results = run_automated_dd(
                    stocks=dd_stocks,
                    quick_mode=not args.full_dd,
                    use_web_search=args.web_search,
                    save_reports=args.save_dd,
                    max_stocks=args.dd_top
                )

                # Apply DD results back to Stock objects
                dd_lookup = {r.ticker: r for r in dd_results}
                for stock in confirmed:
                    if stock.symbol in dd_lookup:
                        result = dd_lookup[stock.symbol]
                        stock.dd_verdict = result.dd_verdict
                        stock.dd_conviction = result.dd_conviction
                        stock.dd_position_size = result.dd_position_size
                        stock.dd_analysis = result.dd_analysis
                        stock.dd_key_catalyst = result.dd_key_catalyst
                        stock.dd_fatal_flaw = result.dd_fatal_flaw

                        # Categorize by DD result
                        if result.dd_verdict in ["STRONG BUY", "SPEC BUY", "SPECULATIVE BUY"]:
                            dd_pass_stocks.append(stock)
                        elif result.dd_verdict == "NO GO":
                            dd_fail_stocks.append(stock)

                # Add only DD-PASS stocks to portfolio
                if dd_pass_stocks:
                    print(f"\n  ✅ Adding {len(dd_pass_stocks)} DD-PASS signal(s) to portfolio...")
                    for stock in dd_pass_stocks:
                        add_to_open_positions(stock)
                        print(f"     • {stock.symbol} - {stock.dd_verdict} ({stock.dd_conviction}/10)")

                if dd_fail_stocks:
                    print(f"\n  ❌ {len(dd_fail_stocks)} signal(s) FAILED DD (not added to portfolio):")
                    for stock in dd_fail_stocks:
                        print(f"     • {stock.symbol} - NO GO: {stock.dd_fatal_flaw or 'See analysis'}")

            except ImportError:
                print("  ⚠️  dd_automator.py not found - skipping automated DD")
                print("     Portfolio will NOT be updated without DD")
            except Exception as e:
                print(f"  ⚠️  DD error: {e}")
                print("     Portfolio will NOT be updated without DD")

    elif args.no_dd and confirmed:
        # DD skipped - warn user that portfolio won't be updated
        pass_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if pass_stocks:
            print("\n  ⚠️  DD SKIPPED (--no-dd flag)")
            print(f"     {len(pass_stocks)} TRADE signal(s) will NOT be added to portfolio")
            print("     Run without --no-dd to perform DD and update portfolio")

    # Print report
    print_final_report(confirmed, sell_signals, stats)
    
    # Print due diligence prompts for stocks that passed
    if confirmed and not args.no_prompts and not args.no_llm:
        # Only print for TRADE (PASS) signals, not CONSIDER (CAUTION)
        pass_stocks = [s for s in confirmed if s.final_decision in ["PASS", "TRADE"]]
        if pass_stocks:
            try:
                from due_diligence_prompts import print_dd_prompts_for_stocks
                print_dd_prompts_for_stocks(pass_stocks)
            except ImportError:
                print("\n  ⚠️  due_diligence_prompts.py not found - skipping DD prompt generation")
    
    # Save results and generate report (save if any stocks were assessed OR sell signals OR momentum filtered)
    report = None
    briefing_file = None
    try:
        if all_assessed or sell_signals or momentum_rejected:
            report = save_results(confirmed, all_assessed, sell_signals, stats, momentum_rejected, themes_data, archive=args.archive)
            briefing_file = TRADES_DIR / "latest_newsletter_briefing.md"
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
        except Exception as e:
            print(f"  ⚠ Portfolio summary error: {e}")
    
    # Print newsletter generation prompts (market context + compilation)
    if not args.no_prompts:
        try:
            print_newsletter_prompts(briefing_file)
        except Exception as e:
            print(f"  ⚠ Error printing newsletter prompts: {e}")

    # Generate Grok/X prompts for weekly social media content
    if not args.no_grok_prompts and briefing_file:
        try:
            generate_grok_prompts(briefing_file, confirmed, sell_signals, themes_data, stats)
        except Exception as e:
            print(f"  ⚠ Error generating Grok prompts: {e}")
            import traceback
            traceback.print_exc()

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
    print(f"\n  Completed in {duration:.1f} seconds")
    print("═" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
