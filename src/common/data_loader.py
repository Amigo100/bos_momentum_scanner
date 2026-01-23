#!/usr/bin/env python3
"""
DATA LOADER - Centralized Data Loading Utilities
=================================================

Single source of truth for loading portfolio, signals, themes, and briefing data.
Eliminates duplicate CSV/JSON parsing implementations across the codebase.

Usage:
    from src.common.data_loader import (
        load_portfolio,
        load_signals,
        load_themes,
        load_tickers,
        fetch_live_prices
    )

    trades = load_portfolio()
    signals = load_signals()
    themes = load_themes()
    prices = fetch_live_prices(['AAPL', 'NVDA', 'TSLA'])
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import (
    TRADES_DIR, TICKERS_FILE,
    TRAILING_STOP_PCT, STOP_WARNING_PCT
)
from .data_models import (
    Trade, TradeStatus, Theme, ScanStats,
    safe_float, safe_int
)
from .logging_config import log_warning

# ─────────────────────────────────────────────────────────────────────────────
# Optional Dependencies
# ─────────────────────────────────────────────────────────────────────────────

try:
    import yfinance as yf
    import pandas as pd
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_portfolio(
    portfolio_file: Optional[Path] = None,
    status_filter: Optional[str] = None,
    calculate_metrics: bool = True
) -> List[Trade]:
    """
    Load portfolio from CSV file.

    Args:
        portfolio_file: Path to portfolio CSV (defaults to trades/portfolio.csv)
        status_filter: Optional filter ('OPEN', 'CLOSED', 'STOPPED')
        calculate_metrics: Whether to calculate derived metrics

    Returns:
        List of Trade objects

    Example:
        trades = load_portfolio()
        open_trades = load_portfolio(status_filter='OPEN')
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

                trade = Trade.from_csv_row(row)

                if calculate_metrics and trade.entry_price > 0:
                    trade.calculate_metrics()

                trades.append(trade)
    except Exception as e:
        log_warning(f"Error loading portfolio: {e}")

    return trades


def load_open_positions(fetch_prices: bool = False) -> List[Trade]:
    """
    Load only open positions from portfolio.

    Args:
        fetch_prices: Whether to fetch live prices via yfinance

    Returns:
        List of open Trade objects
    """
    trades = load_portfolio(status_filter='OPEN')

    if fetch_prices and trades and YFINANCE_AVAILABLE:
        prices = fetch_live_prices([t.ticker for t in trades])
        for trade in trades:
            if trade.ticker in prices:
                trade.calculate_metrics(current_price=prices[trade.ticker])

    return trades


def get_open_symbols() -> set:
    """Get set of symbols with open positions."""
    trades = load_portfolio(status_filter='OPEN', calculate_metrics=False)
    return {t.ticker for t in trades}


def save_portfolio(
    trades: List[Trade],
    portfolio_file: Optional[Path] = None,
    backup: bool = True
) -> Path:
    """
    Save portfolio to CSV file.

    Args:
        trades: List of Trade objects to save
        portfolio_file: Path to portfolio CSV
        backup: Whether to create backup before saving

    Returns:
        Path to saved file
    """
    if portfolio_file is None:
        portfolio_file = TRADES_DIR / "portfolio.csv"

    portfolio_file.parent.mkdir(parents=True, exist_ok=True)

    # Create backup
    if backup and portfolio_file.exists():
        backup_dir = TRADES_DIR / "portfolio_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"portfolio_{timestamp}.csv"

        import shutil
        shutil.copy(portfolio_file, backup_file)

    # Write portfolio
    fieldnames = [
        'ticker', 'status', 'entry_date', 'entry_price', 'exit_date',
        'exit_price', 'highest_close', 'theme', 'tier', 'signal_type',
        'conviction', 'notes'
    ]

    with open(portfolio_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade.to_csv_row())

    return portfolio_file


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_signals(signals_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load signals.json from scanner output.

    Args:
        signals_file: Path to signals JSON (defaults to current/signals.json)

    Returns:
        Full signals dictionary with stats, buy_signals, sell_signals, themes

    Example:
        data = load_signals()
        buy_signals = data.get('buy_signals', [])
        stats = data.get('stats', {})
    """
    if signals_file is None:
        # Try current/ folder first
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
        log_warning(f"Error loading signals: {e}")
        return {}


def load_scan_stats(signals_file: Optional[Path] = None) -> ScanStats:
    """
    Load scan statistics from signals.json.

    Args:
        signals_file: Path to signals.json

    Returns:
        ScanStats dataclass with all statistics
    """
    data = load_signals(signals_file)
    stats_dict = data.get('stats', {})

    return ScanStats(
        timestamp=stats_dict.get('timestamp', datetime.now().isoformat()),
        tickers_loaded=safe_int(stats_dict.get('tickers_loaded')),
        data_downloaded=safe_int(stats_dict.get('data_downloaded')),
        download_failures=safe_int(stats_dict.get('download_failures')),
        beta_gte_1_5=safe_int(stats_dict.get('beta_gte_1_5')),
        weekly_bos_up=safe_int(stats_dict.get('weekly_bos_up')),
        banker_gte_55=safe_int(stats_dict.get('banker_gte_55')),
        technical_signals=safe_int(stats_dict.get('technical_signals')),
        theme_confirmed=safe_int(stats_dict.get('theme_confirmed')),
        gatekeeper_pass=safe_int(stats_dict.get('gatekeeper_pass')),
        gatekeeper_caution=safe_int(stats_dict.get('gatekeeper_caution')),
        gatekeeper_fail=safe_int(stats_dict.get('gatekeeper_fail')),
        final_trade=safe_int(stats_dict.get('final_trade')),
        final_consider=safe_int(stats_dict.get('final_consider')),
        total_cost=safe_float(stats_dict.get('total_cost'))
    )


def save_signals(
    data: Dict[str, Any],
    signals_file: Optional[Path] = None
) -> Path:
    """
    Save signals data to JSON file.

    Args:
        data: Signals dictionary to save
        signals_file: Path to save to

    Returns:
        Path to saved file
    """
    if signals_file is None:
        signals_file = TRADES_DIR / "current" / "signals.json"

    signals_file.parent.mkdir(parents=True, exist_ok=True)

    with open(signals_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return signals_file


# ═══════════════════════════════════════════════════════════════════════════════
# THEMES LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_themes(
    source: str = "auto",
    signals_file: Optional[Path] = None,
    cache_file: Optional[Path] = None
) -> List[Theme]:
    """
    Load themes from signals.json or themes cache.

    Args:
        source: 'signals', 'cache', or 'auto' (try signals first)
        signals_file: Path to signals.json
        cache_file: Path to themes_cache.json

    Returns:
        List of Theme objects

    Example:
        themes = load_themes()
        prime_themes = [t for t in themes if t.is_prime()]
    """
    themes = []

    # Try signals.json first (most recent)
    if source in ('auto', 'signals'):
        data = load_signals(signals_file)
        if 'themes' in data:
            for t in data['themes']:
                theme = Theme(
                    rank=safe_int(t.get('rank')),
                    name=t.get('name', ''),
                    classification=t.get('classification', ''),
                    theme_type=t.get('theme_type', ''),
                    composite_score=safe_float(t.get('composite_score')),
                    thesis_summary=t.get('thesis_summary', ''),
                    key_catalysts=t.get('key_catalysts', []),
                    primary_etfs=t.get('primary_etfs', []),
                    catalyst_score=safe_float(t.get('catalyst_score')),
                    momentum_score=safe_float(t.get('momentum_score')),
                    crowding_score=safe_float(t.get('crowding_score')),
                    runway_score=safe_float(t.get('runway_score')),
                    crowding_indicator=t.get('crowding_indicator', 'Moderate')
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
                        theme = Theme(
                            rank=safe_int(t.get('rank')),
                            name=t.get('name', ''),
                            classification=t.get('classification', ''),
                            theme_type=t.get('theme_type', ''),
                            composite_score=safe_float(t.get('composite_score')),
                            thesis_summary=t.get('thesis_summary', ''),
                            key_catalysts=t.get('key_catalysts', [])
                        )
                        themes.append(theme)
            except Exception as e:
                log_warning(f"Error loading themes cache: {e}")

    return themes


def get_themes_by_classification(
    themes: Optional[List[Theme]] = None
) -> Dict[str, List[Theme]]:
    """
    Group themes by classification.

    Args:
        themes: List of Theme objects (loads from signals if not provided)

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
# TICKERS LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_tickers(tickers_file: Optional[Path] = None) -> List[str]:
    """
    Load tickers from text file.

    Args:
        tickers_file: Path to tickers file (default: complete_tickers.txt)

    Returns:
        List of ticker symbols

    Example:
        tickers = load_tickers()
        # Returns: ['AAPL', 'NVDA', 'TSLA', ...]
    """
    if tickers_file is None:
        tickers_file = TICKERS_FILE

    if not tickers_file.exists():
        log_warning(f"Tickers file not found: {tickers_file}")
        return []

    try:
        with open(tickers_file, 'r') as f:
            return [line.strip().upper() for line in f if line.strip()]
    except Exception as e:
        log_warning(f"Error loading tickers: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_live_prices(
    tickers: List[str],
    period: str = "5d"
) -> Dict[str, float]:
    """
    Fetch current prices for tickers via yfinance.

    Args:
        tickers: List of ticker symbols
        period: Data period to fetch (default: 5d for latest price)

    Returns:
        Dict mapping ticker -> current price

    Example:
        prices = fetch_live_prices(['AAPL', 'NVDA'])
        # Returns: {'AAPL': 150.25, 'NVDA': 450.00}
    """
    if not YFINANCE_AVAILABLE:
        log_warning("yfinance not available")
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
        log_warning(f"Error fetching prices: {e}")

    return prices


def fetch_spy_return(period_days: int = 30) -> float:
    """
    Get S&P 500 return over specified period.

    Args:
        period_days: Number of days for return calculation

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
        start_idx = min(period_days, len(data) - 1)
        start_price = data['Close'].iloc[-start_idx - 1]

        return ((end_price / start_price) - 1) * 100
    except Exception as e:
        log_warning(f"Error fetching SPY return: {e}")
        return 0.0


def fetch_spy_benchmark() -> Dict[str, float]:
    """
    Get SPY benchmark data for comparison.

    Returns:
        Dict with 'ytd', 'mtd', 'wtd' returns
    """
    if not YFINANCE_AVAILABLE:
        return {'ytd': 0.0, 'mtd': 0.0, 'wtd': 0.0}

    try:
        data = yf.download("SPY", period="1y", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if data.empty:
            return {'ytd': 0.0, 'mtd': 0.0, 'wtd': 0.0}

        now = datetime.now()
        current_price = data['Close'].iloc[-1]

        # YTD
        year_start = data[data.index >= f"{now.year}-01-01"]
        ytd_start = year_start['Close'].iloc[0] if not year_start.empty else current_price
        ytd = ((current_price / ytd_start) - 1) * 100

        # MTD
        month_start = data[data.index >= f"{now.year}-{now.month:02d}-01"]
        mtd_start = month_start['Close'].iloc[0] if not month_start.empty else current_price
        mtd = ((current_price / mtd_start) - 1) * 100

        # WTD (last 5 trading days)
        wtd_start = data['Close'].iloc[-5] if len(data) >= 5 else current_price
        wtd = ((current_price / wtd_start) - 1) * 100

        return {'ytd': ytd, 'mtd': mtd, 'wtd': wtd}
    except Exception as e:
        log_warning(f"Error fetching SPY benchmark: {e}")
        return {'ytd': 0.0, 'mtd': 0.0, 'wtd': 0.0}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

def load_content_queue(queue_file: Optional[Path] = None) -> List[Dict]:
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
        log_warning(f"Error loading content queue: {e}")
        return []


def save_content_queue(
    queue: List[Dict],
    queue_file: Optional[Path] = None
) -> Path:
    """
    Save tweet content queue to JSON.

    Args:
        queue: List of tweet objects
        queue_file: Path to content_queue.json

    Returns:
        Path to saved file
    """
    if queue_file is None:
        queue_file = TRADES_DIR / "content_queue.json"

    queue_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        log_warning(f"Error saving content queue: {e}")

    return queue_file


# ═══════════════════════════════════════════════════════════════════════════════
# CHART MANIFEST
# ═══════════════════════════════════════════════════════════════════════════════

def load_chart_manifest(manifest_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Load chart manifest mapping tickers to chart paths.

    Args:
        manifest_path: Path to chart_manifest.json

    Returns:
        Dict mapping ticker -> chart file path
    """
    if manifest_path is None:
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
        log_warning(f"Error loading chart manifest: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Data loader utilities")
    parser.add_argument("--portfolio", action="store_true", help="Load portfolio")
    parser.add_argument("--signals", action="store_true", help="Load signals")
    parser.add_argument("--themes", action="store_true", help="Load themes")
    parser.add_argument("--tickers", action="store_true", help="Load tickers")
    parser.add_argument("--prices", nargs="+", help="Fetch prices for tickers")
    parser.add_argument("--spy", action="store_true", help="Fetch SPY benchmark")

    args = parser.parse_args()

    if args.portfolio:
        print("\n=== Portfolio ===")
        trades = load_portfolio()
        open_trades = [t for t in trades if t.status == "OPEN"]
        print(f"  Total trades: {len(trades)}")
        print(f"  Open positions: {len(open_trades)}")
        for t in open_trades[:5]:
            print(f"    {t.ticker}: ${t.entry_price:.2f} ({t.theme})")

    if args.signals:
        print("\n=== Signals ===")
        data = load_signals()
        stats = load_scan_stats()
        print(f"  Tickers loaded: {stats.tickers_loaded}")
        print(f"  Final trade: {stats.final_trade}")
        print(f"  Buy signals: {len(data.get('buy_signals', []))}")

    if args.themes:
        print("\n=== Themes ===")
        themes = load_themes()
        grouped = get_themes_by_classification(themes)
        for classification, theme_list in grouped.items():
            print(f"  {classification}: {len(theme_list)}")
            for t in theme_list[:2]:
                print(f"    - {t.name} ({t.composite_score:.1f})")

    if args.tickers:
        print("\n=== Tickers ===")
        tickers = load_tickers()
        print(f"  Loaded {len(tickers)} tickers")
        print(f"  First 10: {tickers[:10]}")

    if args.prices:
        print("\n=== Live Prices ===")
        prices = fetch_live_prices(args.prices)
        for ticker, price in prices.items():
            print(f"  {ticker}: ${price:.2f}")

    if args.spy:
        print("\n=== SPY Benchmark ===")
        benchmark = fetch_spy_benchmark()
        print(f"  YTD: {benchmark['ytd']:+.1f}%")
        print(f"  MTD: {benchmark['mtd']:+.1f}%")
        print(f"  WTD: {benchmark['wtd']:+.1f}%")

    if not any([args.portfolio, args.signals, args.themes, args.tickers, args.prices, args.spy]):
        print("Data Loader - Use --portfolio, --signals, --themes, --tickers, --prices, or --spy")
        print("\n  ✓ Module loaded successfully")
