#!/usr/bin/env python3
"""
DATA LOADER - Centralized Data Loading Utilities
=================================================

Single source of truth for loading portfolio, signals, themes, and briefing data.
Eliminates duplicate CSV/JSON parsing implementations across the codebase.

Usage:
    from data_loader import (
        load_portfolio,
        load_signals,
        load_briefing_data,
        load_themes,
        load_chart_manifest,
        fetch_live_prices
    )

    # Load data
    trades = load_portfolio()
    signals = load_signals()
    themes = load_themes()
    prices = fetch_live_prices(['AAPL', 'NVDA', 'TSLA'])
"""

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import yfinance as yf
    import pandas as pd
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Import output_paths if available
try:
    from output_paths import get_output_paths, TRADES_DIR, get_current_dir
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False
    TRADES_DIR = Path(__file__).resolve().parent / "trades"

# Import config if available
try:
    from config import TRAILING_STOP_PCT, STOP_WARNING_PCT
except ImportError:
    TRAILING_STOP_PCT = 20.0
    STOP_WARNING_PCT = 5.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    """Simple trade data structure for content generation."""
    ticker: str
    status: str = "OPEN"
    entry_date: str = ""
    entry_price: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    highest_close: float = 0.0
    theme: str = ""
    tier: str = ""
    signal_type: str = "PASS"
    conviction: int = 0
    notes: str = ""
    # Calculated fields
    current_price: float = 0.0
    pnl_pct: float = 0.0
    days_held: int = 0
    stop_level: float = 0.0
    distance_to_stop_pct: float = 0.0


@dataclass
class SignalData:
    """Signal data from scanner output."""
    symbol: str
    tier: str = ""
    price: float = 0.0
    beta: float = 0.0
    banker: float = 0.0
    momentum_4w: float = 0.0
    return_20d: float = 0.0
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0
    theme_verdict: str = ""
    final_decision: str = ""
    conviction: int = 0
    catalyst_summary: str = ""
    red_flag_level: str = ""
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""
    action: str = ""
    dd_summary: str = ""


@dataclass
class ThemeData:
    """Theme data from thematic analyzer."""
    rank: int = 0
    name: str = ""
    classification: str = ""  # PRIME, INVESTABLE, SELECTIVE, AVOID
    theme_type: str = ""  # TREND, BOTTLENECK, CONTRARIAN
    composite_score: float = 0.0
    thesis_summary: str = ""
    key_catalysts: List[str] = field(default_factory=list)


@dataclass
class BriefingData:
    """Parsed newsletter briefing data."""
    # Performance
    unrealized_pnl: str = ""
    win_rate: str = ""
    avg_winner: str = ""
    avg_loser: str = ""

    # Themes
    prime_themes: List[Dict] = field(default_factory=list)
    investable_themes: List[Dict] = field(default_factory=list)
    selective_themes: List[Dict] = field(default_factory=list)
    avoid_themes: List[Dict] = field(default_factory=list)

    # Signals
    pass_signals: List[Dict] = field(default_factory=list)
    caution_signals: List[Dict] = field(default_factory=list)
    sell_signals: List[Dict] = field(default_factory=list)

    # Positions
    open_positions: List[Dict] = field(default_factory=list)
    recently_closed: List[Dict] = field(default_factory=list)

    # Stats
    scan_stats: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_portfolio(
    portfolio_file: Path = None,
    status_filter: str = None,
    calculate_metrics: bool = True
) -> List[TradeData]:
    """
    Load portfolio from CSV file.

    Args:
        portfolio_file: Path to portfolio CSV (defaults to trades/portfolio.csv)
        status_filter: Optional filter ('OPEN', 'CLOSED', 'STOPPED')
        calculate_metrics: Whether to calculate derived metrics

    Returns:
        List of TradeData objects
    """
    if portfolio_file is None:
        portfolio_file = TRADES_DIR / "portfolio.csv"

    if not portfolio_file.exists():
        return []

    trades = []
    try:
        with open(portfolio_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get('status', 'OPEN')

                # Apply filter if specified
                if status_filter and status != status_filter:
                    continue

                trade = TradeData(
                    ticker=row.get('ticker', '').upper(),
                    status=status,
                    entry_date=row.get('entry_date', ''),
                    entry_price=float(row.get('entry_price') or 0),
                    exit_date=row.get('exit_date', ''),
                    exit_price=float(row.get('exit_price') or 0),
                    highest_close=float(row.get('highest_close') or 0),
                    theme=row.get('theme', ''),
                    tier=row.get('tier', ''),
                    signal_type=row.get('signal_type', 'PASS'),
                    conviction=int(row.get('conviction') or 0),
                    notes=row.get('notes', '')
                )

                if calculate_metrics and trade.entry_price > 0:
                    _calculate_trade_metrics(trade)

                trades.append(trade)
    except Exception as e:
        print(f"  ⚠ Error loading portfolio: {e}")

    return trades


def load_open_positions(fetch_prices: bool = False) -> List[TradeData]:
    """
    Load only open positions from portfolio.

    Args:
        fetch_prices: Whether to fetch live prices via yfinance

    Returns:
        List of open TradeData objects
    """
    trades = load_portfolio(status_filter='OPEN')

    if fetch_prices and trades and YFINANCE_AVAILABLE:
        prices = fetch_live_prices([t.ticker for t in trades])
        for trade in trades:
            if trade.ticker in prices:
                trade.current_price = prices[trade.ticker]
                _calculate_trade_metrics(trade)

    return trades


def get_open_symbols() -> set:
    """Get set of symbols with open positions."""
    trades = load_portfolio(status_filter='OPEN', calculate_metrics=False)
    return {t.ticker for t in trades}


def _calculate_trade_metrics(trade: TradeData) -> None:
    """Calculate derived metrics for a trade."""
    # Use exit price for closed trades, current price for open
    price_for_calc = trade.exit_price if trade.status != "OPEN" else trade.current_price

    if trade.entry_price > 0 and price_for_calc > 0:
        trade.pnl_pct = ((price_for_calc / trade.entry_price) - 1) * 100

    # Stop level (20% below highest close)
    if trade.highest_close > 0:
        trade.stop_level = trade.highest_close * (1 - TRAILING_STOP_PCT / 100)

    # Distance to stop
    if trade.status == "OPEN" and trade.current_price > 0 and trade.stop_level > 0:
        trade.distance_to_stop_pct = ((trade.current_price - trade.stop_level) / trade.current_price) * 100

    # Days held
    if trade.entry_date:
        try:
            entry = datetime.strptime(trade.entry_date, "%Y-%m-%d")
            if trade.status == "OPEN":
                trade.days_held = (datetime.now() - entry).days
            elif trade.exit_date:
                exit_dt = datetime.strptime(trade.exit_date, "%Y-%m-%d")
                trade.days_held = (exit_dt - entry).days
        except ValueError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals(signals_file: Path = None) -> Dict[str, Any]:
    """
    Load signals.json from scanner output.

    Args:
        signals_file: Path to signals JSON (defaults to current/signals.json)

    Returns:
        Full signals dictionary with stats, buy_signals, sell_signals, themes
    """
    if signals_file is None:
        # Try current/ folder first
        if OUTPUT_PATHS_AVAILABLE:
            signals_file = get_current_dir() / "signals.json"
        else:
            signals_file = TRADES_DIR / "current" / "signals.json"

        # Fallback to legacy location
        if not signals_file.exists():
            signals_file = TRADES_DIR / "signals.json"

    if not signals_file.exists():
        return {}

    try:
        with open(signals_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠ Error loading signals: {e}")
        return {}


def load_buy_signals(signals_file: Path = None) -> List[SignalData]:
    """
    Load buy signals as SignalData objects.

    Args:
        signals_file: Path to signals JSON

    Returns:
        List of SignalData objects
    """
    data = load_signals(signals_file)
    signals = []

    for s in data.get('buy_signals', []):
        signal = SignalData(
            symbol=s.get('symbol', ''),
            tier=s.get('tier', ''),
            price=float(s.get('price', 0)),
            beta=float(s.get('beta', 0)),
            banker=float(s.get('banker', 0)),
            momentum_4w=float(s.get('momentum_4w', 0)),
            return_20d=float(s.get('return_20d', 0)),
            theme=s.get('theme', ''),
            theme_score=float(s.get('theme_score', 0)),
            pure_play_score=int(s.get('pure_play_score', 0)),
            theme_verdict=s.get('theme_verdict', ''),
            final_decision=s.get('final_decision', ''),
            conviction=int(s.get('conviction', 0)),
            catalyst_summary=s.get('catalyst_summary', ''),
            red_flag_level=s.get('red_flag_level', ''),
            bullish_factors=s.get('bullish_factors', []),
            risk_factors=s.get('risk_factors', []),
            reasoning=s.get('reasoning', ''),
            action=s.get('action', ''),
            dd_summary=s.get('dd_summary', '')
        )
        signals.append(signal)

    return signals


def load_scan_stats(signals_file: Path = None) -> Dict[str, int]:
    """
    Load scan statistics from signals.json.

    Returns:
        Dict with keys like 'tickers_loaded', 'weekly_bos_up', 'final_trade', etc.
    """
    data = load_signals(signals_file)
    return data.get('stats', {})


# ═══════════════════════════════════════════════════════════════════════════════
# THEMES LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_themes(
    source: str = "auto",
    signals_file: Path = None,
    cache_file: Path = None
) -> List[ThemeData]:
    """
    Load themes from signals.json or themes cache.

    Args:
        source: 'signals', 'cache', or 'auto' (try signals first)
        signals_file: Path to signals.json
        cache_file: Path to themes_cache.json

    Returns:
        List of ThemeData objects
    """
    themes = []

    # Try signals.json first (most recent)
    if source in ('auto', 'signals'):
        data = load_signals(signals_file)
        if 'themes' in data:
            for t in data['themes']:
                theme = ThemeData(
                    rank=int(t.get('rank', 0)),
                    name=t.get('name', ''),
                    classification=t.get('classification', ''),
                    theme_type=t.get('theme_type', ''),
                    composite_score=float(t.get('composite_score', 0)),
                    thesis_summary=t.get('thesis_summary', ''),
                    key_catalysts=t.get('key_catalysts', [])
                )
                themes.append(theme)

    # Fallback to cache
    if not themes and source in ('auto', 'cache'):
        if cache_file is None:
            cache_file = TRADES_DIR.parent / "themes_cache.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for t in data.get('themes', []):
                        theme = ThemeData(
                            rank=int(t.get('rank', 0)),
                            name=t.get('name', ''),
                            classification=t.get('classification', ''),
                            theme_type=t.get('theme_type', ''),
                            composite_score=float(t.get('composite_score', 0)),
                            thesis_summary=t.get('thesis_summary', ''),
                            key_catalysts=t.get('key_catalysts', [])
                        )
                        themes.append(theme)
            except Exception as e:
                print(f"  ⚠ Error loading themes cache: {e}")

    return themes


def get_themes_by_classification(themes: List[ThemeData] = None) -> Dict[str, List[ThemeData]]:
    """
    Group themes by classification.

    Returns:
        Dict with keys: 'PRIME', 'INVESTABLE', 'SELECTIVE', 'AVOID'
    """
    if themes is None:
        themes = load_themes()

    grouped = {
        'PRIME': [],
        'INVESTABLE': [],
        'SELECTIVE': [],
        'AVOID': []
    }

    for theme in themes:
        if theme.classification in grouped:
            grouped[theme.classification].append(theme)

    return grouped


# ═══════════════════════════════════════════════════════════════════════════════
# BRIEFING PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def load_briefing_data(briefing_path: Path = None) -> BriefingData:
    """
    Parse newsletter briefing markdown to extract portfolio data.

    Args:
        briefing_path: Path to briefing markdown file

    Returns:
        BriefingData with all parsed sections
    """
    if briefing_path is None:
        if OUTPUT_PATHS_AVAILABLE:
            briefing_path = get_current_dir() / "newsletter_briefing.md"
        else:
            briefing_path = TRADES_DIR / "current" / "newsletter_briefing.md"

        # Fallback to legacy location
        if not briefing_path.exists():
            briefing_path = TRADES_DIR / "latest_newsletter_briefing.md"

    data = BriefingData()

    if not briefing_path.exists():
        print(f"  ⚠ Briefing file not found: {briefing_path}")
        return data

    try:
        content = briefing_path.read_text(encoding='utf-8')

        # Parse performance summary
        data.unrealized_pnl = _extract_pattern(r'Unrealized P&L:\s*([^\n]+)', content)
        data.win_rate = _extract_pattern(r'Win Rate[^:]*:\s*([^\n]+)', content)
        data.avg_winner = _extract_pattern(r'Avg Winner:\s*([^\n|]+)', content)
        data.avg_loser = _extract_pattern(r'Avg Loser:\s*([^\n]+)', content)

        # Parse themes by section
        data.prime_themes = _parse_theme_section(content, "PRIME")
        data.investable_themes = _parse_theme_section(content, "INVESTABLE")
        data.selective_themes = _parse_theme_section(content, "SELECTIVE")
        data.avoid_themes = _parse_theme_section(content, "AVOID")

        # Parse signals
        data.pass_signals = _parse_signal_section(content, "PASS")
        data.caution_signals = _parse_signal_section(content, "CAUTION")

        # Parse sell signals
        sell_match = re.search(r'## Sell Signals?\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if sell_match:
            data.sell_signals = _parse_positions_table(sell_match.group(1))

        # Parse open positions
        positions_match = re.search(r'## Open Positions?\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if positions_match:
            data.open_positions = _parse_positions_table(positions_match.group(1))

        # Parse recently closed
        closed_match = re.search(r'## Recently Closed\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if closed_match:
            data.recently_closed = _parse_positions_table(closed_match.group(1))

        # Parse scan stats
        stats_match = re.search(r'## Scan Statistics?\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if stats_match:
            stats_text = stats_match.group(1)
            data.scan_stats = {
                'tickers_scanned': int(_extract_pattern(r'Tickers scanned:\s*(\d+)', stats_text) or 0),
                'weekly_bos_up': int(_extract_pattern(r'Weekly BoS Up:\s*(\d+)', stats_text) or 0),
                'technical_signals': int(_extract_pattern(r'Technical signals:\s*(\d+)', stats_text) or 0),
                'theme_confirmed': int(_extract_pattern(r'Theme confirmed:\s*(\d+)', stats_text) or 0),
                'pass_signals': int(_extract_pattern(r'PASS signals:\s*(\d+)', stats_text) or 0),
                'caution_signals': int(_extract_pattern(r'CAUTION signals:\s*(\d+)', stats_text) or 0),
            }
    except Exception as e:
        print(f"  ⚠ Error parsing briefing: {e}")

    return data


def _extract_pattern(pattern: str, text: str) -> str:
    """Extract first match from pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_theme_section(content: str, classification: str) -> List[Dict]:
    """Parse themes from a classification section."""
    themes = []

    # Find section with this classification
    pattern = rf'###?\s*{classification}\s+Themes?.*?\n(.*?)(?=\n###?|\Z)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        section = match.group(1)

        # Parse individual themes
        theme_pattern = r'\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*.*?Score:\s*([\d.]+)'
        for m in re.finditer(theme_pattern, section, re.IGNORECASE):
            themes.append({
                'name': m.group(1).strip(),
                'type': m.group(2).strip(),
                'score': float(m.group(3)),
                'classification': classification
            })

    return themes


def _parse_signal_section(content: str, decision: str) -> List[Dict]:
    """Parse signals from PASS or CAUTION sections."""
    signals = []

    pattern = rf'## {decision}\s*[-–]\s*.*?\n(.*?)(?=\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        section = match.group(1)

        # Find each ticker section
        ticker_pattern = r'### (\$?\w+)\s*\n(.*?)(?=\n###|\Z)'
        for m in re.finditer(ticker_pattern, section, re.DOTALL):
            ticker = m.group(1).replace('$', '').upper()
            details = m.group(2)

            signal = {
                'ticker': ticker,
                'price': _extract_pattern(r'Price[^:]*:\s*\$?([\d.]+)', details),
                'theme': _extract_pattern(r'Theme[^:]*:\s*([^\n|]+)', details),
                'tier': _extract_pattern(r'Tier[^:]*:\s*(\w+)', details),
                'conviction': _extract_pattern(r'Conviction[^:]*:\s*(\d)', details),
                'decision': decision
            }
            signals.append(signal)

    return signals


def _parse_positions_table(text: str) -> List[Dict]:
    """Parse positions from markdown table."""
    positions = []

    # Find table rows (skip header)
    rows = re.findall(r'\|\s*(\$?\w+)\s*\|([^|]+\|)+', text)

    for row_match in re.finditer(r'\|\s*(\$?\w+)\s*\|([^\n]+)', text):
        row = row_match.group(0)
        cells = [c.strip() for c in row.split('|') if c.strip()]

        if len(cells) >= 2 and cells[0].replace('$', '').isalpha():
            ticker = cells[0].replace('$', '').upper()

            # Skip header row
            if ticker.upper() == 'TICKER':
                continue

            positions.append({
                'ticker': ticker,
                'cells': cells[1:]  # Remaining cells
            })

    return positions


# ═══════════════════════════════════════════════════════════════════════════════
# CHART MANIFEST
# ═══════════════════════════════════════════════════════════════════════════════

def load_chart_manifest(manifest_path: Path = None) -> Dict[str, str]:
    """
    Load chart manifest mapping tickers to chart paths.

    Returns:
        Dict mapping ticker -> chart file path
    """
    if manifest_path is None:
        if OUTPUT_PATHS_AVAILABLE:
            manifest_path = get_current_dir() / "charts" / "chart_manifest.json"
        else:
            manifest_path = TRADES_DIR / "current" / "charts" / "chart_manifest.json"

        # Fallback to legacy location
        if not manifest_path.exists():
            manifest_path = TRADES_DIR / "charts" / "chart_manifest.json"

    if not manifest_path.exists():
        return {}

    try:
        with open(manifest_path, 'r') as f:
            data = json.load(f)
            return data.get('charts', {})
    except Exception as e:
        print(f"  ⚠ Error loading chart manifest: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_live_prices(tickers: List[str], period: str = "5d") -> Dict[str, float]:
    """
    Fetch current prices for tickers via yfinance.

    Args:
        tickers: List of ticker symbols
        period: Data period to fetch (default: 5d for latest price)

    Returns:
        Dict mapping ticker -> current price
    """
    if not YFINANCE_AVAILABLE:
        print("  ⚠ yfinance not available")
        return {}

    if not tickers:
        return {}

    prices = {}

    try:
        data = yf.download(tickers, period=period, progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            # Multiple tickers
            for ticker in tickers:
                try:
                    price = data['Close'][ticker].iloc[-1]
                    if pd.notna(price):
                        prices[ticker] = float(price)
                except (KeyError, IndexError):
                    pass
        elif len(tickers) == 1:
            # Single ticker
            try:
                price = data['Close'].iloc[-1]
                if pd.notna(price):
                    prices[tickers[0]] = float(price)
            except (KeyError, IndexError):
                pass
    except Exception as e:
        print(f"  ⚠ Error fetching prices: {e}")

    return prices


def fetch_spy_return(days: int = 30) -> float:
    """
    Get S&P 500 return over specified days.

    Args:
        days: Number of days for return calculation

    Returns:
        Return percentage (e.g., 5.2 for +5.2%)
    """
    if not YFINANCE_AVAILABLE:
        return 0.0

    try:
        data = yf.download("SPY", period="2y", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if data.empty:
            return 0.0

        end_price = data['Close'].iloc[-1]
        start_idx = min(days, len(data) - 1)
        start_price = data['Close'].iloc[-start_idx - 1]

        return ((end_price / start_price) - 1) * 100
    except Exception as e:
        print(f"  ⚠ Error fetching SPY return: {e}")
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TICKERS LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_tickers(tickers_file: Path = None) -> List[str]:
    """
    Load tickers from text file.

    Args:
        tickers_file: Path to tickers file (default: complete_tickers.txt)

    Returns:
        List of ticker symbols
    """
    if tickers_file is None:
        tickers_file = TRADES_DIR.parent / "complete_tickers.txt"

    if not tickers_file.exists():
        print(f"  ⚠ Tickers file not found: {tickers_file}")
        return []

    try:
        with open(tickers_file, 'r') as f:
            return [line.strip().upper() for line in f if line.strip()]
    except Exception as e:
        print(f"  ⚠ Error loading tickers: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

def load_content_queue(queue_file: Path = None) -> List[Dict]:
    """
    Load tweet content queue from JSON.

    Args:
        queue_file: Path to content_queue.json

    Returns:
        List of tweet objects
    """
    if queue_file is None:
        queue_file = TRADES_DIR / "content_queue.json"

    if not queue_file.exists():
        return []

    try:
        with open(queue_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠ Error loading content queue: {e}")
        return []


def save_content_queue(queue: List[Dict], queue_file: Path = None) -> None:
    """
    Save tweet content queue to JSON.

    Args:
        queue: List of tweet objects
        queue_file: Path to content_queue.json
    """
    if queue_file is None:
        queue_file = TRADES_DIR / "content_queue.json"

    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"  ⚠ Error saving content queue: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Test data loading functions."""
    import argparse

    parser = argparse.ArgumentParser(description="Data loader utilities")
    parser.add_argument("--portfolio", action="store_true", help="Load portfolio")
    parser.add_argument("--signals", action="store_true", help="Load signals")
    parser.add_argument("--themes", action="store_true", help="Load themes")
    parser.add_argument("--briefing", action="store_true", help="Load briefing")
    parser.add_argument("--prices", nargs="+", help="Fetch prices for tickers")

    args = parser.parse_args()

    if args.portfolio:
        print("\n=== Portfolio ===")
        trades = load_portfolio()
        open_trades = [t for t in trades if t.status == "OPEN"]
        print(f"Total trades: {len(trades)}")
        print(f"Open positions: {len(open_trades)}")
        for t in open_trades[:5]:
            print(f"  {t.ticker}: ${t.entry_price:.2f} ({t.theme})")

    if args.signals:
        print("\n=== Signals ===")
        data = load_signals()
        print(f"Stats: {data.get('stats', {})}")
        print(f"Buy signals: {len(data.get('buy_signals', []))}")

    if args.themes:
        print("\n=== Themes ===")
        themes = load_themes()
        for t in themes[:5]:
            print(f"  {t.classification}: {t.name} ({t.composite_score:.1f})")

    if args.briefing:
        print("\n=== Briefing Data ===")
        data = load_briefing_data()
        print(f"Unrealized P&L: {data.unrealized_pnl}")
        print(f"Win Rate: {data.win_rate}")
        print(f"Prime Themes: {len(data.prime_themes)}")
        print(f"PASS Signals: {len(data.pass_signals)}")

    if args.prices:
        print("\n=== Live Prices ===")
        prices = fetch_live_prices(args.prices)
        for ticker, price in prices.items():
            print(f"  {ticker}: ${price:.2f}")

    if not any([args.portfolio, args.signals, args.themes, args.briefing, args.prices]):
        print("Data Loader - Use --portfolio, --signals, --themes, --briefing, or --prices")


if __name__ == "__main__":
    main()
