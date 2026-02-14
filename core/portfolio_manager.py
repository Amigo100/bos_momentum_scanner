#!/usr/bin/env python3
"""
PORTFOLIO MANAGER - Unified Trade Tracking
==========================================

Single source of truth for all trades (open + closed) with Google Sheets integration.

Features:
- Unified portfolio.csv combining open and closed positions
- Live price updates via yfinance when running scanner
- Google Sheets export with GOOGLEFINANCE formulas for live tracking
- Automatic S&P 500 benchmark comparison
- Performance metrics across multiple timeframes

CSV Structure:
    ticker, status, entry_date, entry_price, exit_date, exit_price, 
    highest_close, theme, tier, signal_type, conviction, notes

Google Sheets adds live columns via formulas:
    current_price, pnl_pct, pnl_usd, stop_level, days_held, distance_to_stop

Usage:
    # As module (called by scanner.py)
    from portfolio_manager import PortfolioManager
    pm = PortfolioManager()
    pm.add_trade(stock)
    pm.flag_exit(symbol, exit_price, reason)
    pm.update_prices()  # Fetches live prices
    pm.export_to_sheets()  # Creates Google Sheets-ready file
    
    # Standalone
    python portfolio_manager.py --update          # Update prices
    python portfolio_manager.py --export          # Export for Google Sheets
    python portfolio_manager.py --migrate         # Migrate from old format
    python portfolio_manager.py --report          # Print summary to terminal
"""

import os
import re
import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("Required: pip install yfinance pandas --break-system-packages")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
TRADES_DIR = BASE_DIR / "trades"
TRADES_DIR.mkdir(exist_ok=True)

PORTFOLIO_FILE = TRADES_DIR / "portfolio.csv"
SHEETS_EXPORT_FILE = TRADES_DIR / "portfolio_google_sheets.csv"
BACKUP_DIR = TRADES_DIR / "portfolio_backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Old files for migration
OLD_OPEN_POSITIONS = TRADES_DIR / "open_positions.csv"
OLD_TRADE_LOG = TRADES_DIR / "trade_log.csv"

# Trading parameters — imported from config.py (single source of truth)
try:
    from config import (
        TRAILING_STOP_PCT, STOP_WARNING_PCT,
        DEFAULT_POSITION_SHARES, MAX_PORTFOLIO_BACKUPS,
        STARTING_CAPITAL_PER_POSITION, CURRENCY_SYMBOL, EQUITY_CURVE_FILE,
        LOCK_TIERS,
    )
    from core.sterling_indicators import check_profit_lock
except ImportError:
    # Fallback if config.py not available (e.g. standalone use)
    TRAILING_STOP_PCT = 20.0
    STOP_WARNING_PCT = 5.0
    DEFAULT_POSITION_SHARES = 100
    MAX_PORTFOLIO_BACKUPS = 30
    STARTING_CAPITAL_PER_POSITION = 5000.0
    CURRENCY_SYMBOL = "£"
    EQUITY_CURVE_FILE = "equity_curve.csv"
    LOCK_TIERS = [(2.00, 0.15), (1.00, 0.20), (0.50, 0.25)]
    check_profit_lock = None  # Will be imported at use site if needed


# ═══════════════════════════════════════════════════════════════════════════════
# TICKER VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_ticker_valid(ticker: str) -> bool:
    """
    Check if a ticker is still valid/actively trading.

    Used to detect delisted stocks in the portfolio.

    Args:
        ticker: Stock symbol to check

    Returns:
        True if ticker appears valid, False if likely delisted/invalid
    """
    try:
        info = yf.Ticker(ticker).info
        # Check for indicators of a valid, trading stock
        # marketCap > 0 indicates the stock is trading
        # regularMarketPrice indicates current trading activity
        has_market_cap = info.get('marketCap', 0) > 0
        has_price = info.get('regularMarketPrice') is not None
        has_exchange = info.get('exchange') is not None

        return has_market_cap or has_price or has_exchange
    except Exception:
        return False


def check_portfolio_for_invalid_tickers(tickers: List[str]) -> List[str]:
    """
    Check a list of tickers for any that appear delisted/invalid.

    Args:
        tickers: List of ticker symbols to check

    Returns:
        List of invalid/delisted tickers
    """
    invalid = []
    for ticker in tickers:
        if not is_ticker_valid(ticker):
            invalid.append(ticker)
            print(f"    ⚠ Ticker {ticker} appears delisted or invalid")
    return invalid


class TradeStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"      # Manual exit (profit taking, strategic)
    STOPPED = "STOPPED"    # Hit trailing stop


def _normalize_date(date_str: str) -> str:
    """Normalize date strings to YYYY-MM-DD format.

    Handles:
      - YYYY-MM-DD (already correct)
      - DD/MM/YYYY (UK format found in portfolio.csv)
    """
    if not date_str or not date_str.strip():
        return ''
    date_str = date_str.strip()
    # Already in correct format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    # DD/MM/YYYY
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3 and len(parts[2]) == 4:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{year:04d}-{month:02d}-{day:02d}"
    return date_str


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """Represents a single trade (open or closed)."""
    ticker: str
    status: str = "OPEN"
    entry_date: str = ""
    entry_price: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    highest_close: float = 0.0
    theme: str = ""
    tier: str = ""
    signal_type: str = "PASS"  # PASS or CONSIDER
    conviction: int = 0
    notes: str = ""
    stop_pct: float = 0.0  # Per-trade trailing stop %; 0 = use global default
    # Sterling Grid position sizing fields
    position_size_pct: float = 0.0   # % of equity allocated (from conviction tier)
    position_dollars: float = 0.0    # Dollar amount allocated
    sizing_gear: str = ""            # conservative / recommended / aggressive

    # Calculated fields (not stored in CSV, computed on load)
    current_price: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    stop_level: float = 0.0
    days_held: int = 0
    distance_to_stop_pct: float = 0.0
    stop_alert: bool = False
    
    def __post_init__(self):
        """Initialize calculated fields."""
        if not self.entry_date:
            self.entry_date = datetime.now().strftime("%Y-%m-%d")
        if self.highest_close == 0 and self.entry_price > 0:
            self.highest_close = self.entry_price
    
    def calculate_metrics(self, current_price: float = None):
        """Calculate all derived metrics."""
        if current_price is not None:
            self.current_price = current_price
            
            # Update highest close for open positions
            if self.status == "OPEN" and current_price > self.highest_close:
                self.highest_close = current_price
        
        # Use exit price for closed trades, current price for open
        price_for_calc = self.exit_price if self.status != "OPEN" else self.current_price
        
        if self.entry_price > 0 and price_for_calc > 0:
            self.pnl_pct = ((price_for_calc / self.entry_price) - 1) * 100
            self.pnl_usd = (price_for_calc - self.entry_price) * DEFAULT_POSITION_SHARES
        
        # Stop level — tiered profit lock (Sterling Grid)
        # Below +50% return: only ExD can exit (no trailing stop → stop_level = 0)
        # Above +50%: trailing stop based on return tier
        self.stop_level = 0.0
        if self.entry_price > 0 and self.highest_close > 0 and check_profit_lock is not None:
            lock_result = check_profit_lock(self.entry_price, price_for_calc, self.highest_close)
            if lock_result.get('active', False):
                self.stop_level = lock_result.get('lock_level', 0.0)

        # Distance to stop (0 if no profit lock active — only ExD can exit)
        if self.status == "OPEN" and self.current_price > 0 and self.stop_level > 0:
            self.distance_to_stop_pct = ((self.current_price - self.stop_level) / self.current_price) * 100
            self.stop_alert = self.distance_to_stop_pct <= STOP_WARNING_PCT
        elif self.status == "OPEN":
            self.distance_to_stop_pct = 0.0  # No profit lock active
            self.stop_alert = False
        
        # Days held
        if self.entry_date:
            try:
                entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
                if self.status == "OPEN":
                    self.days_held = (datetime.now() - entry).days
                elif self.exit_date:
                    exit_dt = datetime.strptime(self.exit_date, "%Y-%m-%d")
                    self.days_held = (exit_dt - entry).days
            except ValueError:
                pass
    
    def validate(self) -> List[str]:
        """Validate business rules. Returns list of warning strings (empty = valid)."""
        warnings: List[str] = []

        if self.entry_price < 0:
            warnings.append(f"{self.ticker}: negative entry_price ({self.entry_price})")
        if self.exit_price < 0:
            warnings.append(f"{self.ticker}: negative exit_price ({self.exit_price})")
        if self.highest_close < 0:
            warnings.append(f"{self.ticker}: negative highest_close ({self.highest_close})")

        if self.entry_date and self.exit_date:
            try:
                entry_dt = datetime.strptime(self.entry_date, "%Y-%m-%d")
                exit_dt = datetime.strptime(self.exit_date, "%Y-%m-%d")
                if exit_dt < entry_dt:
                    warnings.append(
                        f"{self.ticker}: exit_date ({self.exit_date}) before entry_date ({self.entry_date})"
                    )
            except ValueError:
                pass  # Malformed dates are a separate issue

        if self.status == "OPEN" and self.entry_price > 0 and self.highest_close > 0:
            if self.highest_close < self.entry_price:
                warnings.append(
                    f"{self.ticker}: highest_close ({self.highest_close:.2f}) < entry_price ({self.entry_price:.2f})"
                )

        if self.status == "STOPPED" and not self.exit_price:
            warnings.append(f"{self.ticker}: STOPPED status requires exit_price")

        return warnings

    def to_csv_row(self) -> Dict:
        """Convert to CSV row (stored fields only)."""
        return {
            'ticker': self.ticker,
            'status': self.status,
            'entry_date': self.entry_date,
            'entry_price': f"{self.entry_price:.2f}" if self.entry_price else "",
            'exit_date': self.exit_date,
            'exit_price': f"{self.exit_price:.2f}" if self.exit_price else "",
            'highest_close': f"{self.highest_close:.2f}" if self.highest_close else "",
            'theme': self.theme,
            'tier': self.tier,
            'signal_type': self.signal_type,
            'conviction': str(self.conviction) if self.conviction else "",
            'notes': self.notes,
            'stop_pct': f"{self.stop_pct:.1f}" if self.stop_pct > 0 else "",
            'position_size_pct': f"{self.position_size_pct:.1f}" if self.position_size_pct > 0 else "",
            'position_dollars': f"{self.position_dollars:.0f}" if self.position_dollars > 0 else "",
            'sizing_gear': self.sizing_gear,
        }
    
    @classmethod
    def from_csv_row(cls, row: Dict) -> 'Trade':
        """Create Trade from CSV row."""
        return cls(
            ticker=row.get('ticker', '').upper(),
            status=row.get('status', 'OPEN'),
            entry_date=_normalize_date(row.get('entry_date', '')),
            entry_price=float(row.get('entry_price') or 0),
            exit_date=_normalize_date(row.get('exit_date', '')),
            exit_price=float(row.get('exit_price') or 0),
            highest_close=float(row.get('highest_close') or 0),
            theme=row.get('theme', ''),
            tier=row.get('tier', ''),
            signal_type=row.get('signal_type', 'PASS'),
            conviction=int(row.get('conviction') or 0),
            notes=row.get('notes', ''),
            stop_pct=float(row.get('stop_pct') or 0),
            position_size_pct=float(row.get('position_size_pct') or 0),
            position_dollars=float(row.get('position_dollars') or 0),
            sizing_gear=row.get('sizing_gear', ''),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOUNDING EQUITY TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EquitySnapshot:
    """A point-in-time snapshot of portfolio NAV for the equity curve."""
    date: str = ""
    nav: float = 0.0               # Net Asset Value (cash + open position values)
    cash: float = 0.0              # Uninvested cash from closed trade profits
    invested: float = 0.0          # Current value of open positions
    total_deployed: float = 0.0    # Total capital ever allocated (£5k × N trades)
    open_count: int = 0            # Number of open positions
    total_return_pct: float = 0.0  # NAV / total_deployed - 1
    spy_value: float = 0.0         # What total_deployed in SPY would be worth
    spy_return_pct: float = 0.0    # SPY return since inception
    alpha_pct: float = 0.0         # total_return_pct - spy_return_pct
    qqq_value: float = 0.0         # What total_deployed in QQQ would be worth
    qqq_return_pct: float = 0.0    # QQQ (NASDAQ) return since inception
    alpha_vs_qqq_pct: float = 0.0  # total_return_pct - qqq_return_pct

    def to_csv_row(self) -> Dict:
        return {
            'date': self.date,
            'nav': f"{self.nav:.2f}",
            'cash': f"{self.cash:.2f}",
            'invested': f"{self.invested:.2f}",
            'total_deployed': f"{self.total_deployed:.2f}",
            'open_count': str(self.open_count),
            'total_return_pct': f"{self.total_return_pct:.2f}",
            'spy_value': f"{self.spy_value:.2f}",
            'spy_return_pct': f"{self.spy_return_pct:.2f}",
            'alpha_pct': f"{self.alpha_pct:.2f}",
            'qqq_value': f"{self.qqq_value:.2f}",
            'qqq_return_pct': f"{self.qqq_return_pct:.2f}",
            'alpha_vs_qqq_pct': f"{self.alpha_vs_qqq_pct:.2f}",
        }

    @classmethod
    def from_csv_row(cls, row: Dict) -> 'EquitySnapshot':
        return cls(
            date=row.get('date', ''),
            nav=float(row.get('nav') or 0),
            cash=float(row.get('cash') or 0),
            invested=float(row.get('invested') or 0),
            total_deployed=float(row.get('total_deployed') or 0),
            open_count=int(row.get('open_count') or 0),
            total_return_pct=float(row.get('total_return_pct') or 0),
            spy_value=float(row.get('spy_value') or 0),
            spy_return_pct=float(row.get('spy_return_pct') or 0),
            alpha_pct=float(row.get('alpha_pct') or 0),
            qqq_value=float(row.get('qqq_value') or 0),
            qqq_return_pct=float(row.get('qqq_return_pct') or 0),
            alpha_vs_qqq_pct=float(row.get('alpha_vs_qqq_pct') or 0),
        )


EQUITY_SNAPSHOT_FIELDS = [
    'date', 'nav', 'cash', 'invested', 'total_deployed',
    'open_count', 'total_return_pct', 'spy_value', 'spy_return_pct', 'alpha_pct',
    'qqq_value', 'qqq_return_pct', 'alpha_vs_qqq_pct',
]


class EquityTracker:
    """Tracks compounding portfolio equity over time.

    Model: £5,000 per position. Closed trade profits flow into a cash pool.
    New trades draw from the pool when sufficient, otherwise new capital is deployed.
    NAV = cash_pool + sum(open position current values).
    Total deployed = £5,000 × number of unique trade allocations.
    """

    def __init__(self, starting_per_position: float = None, equity_file: Path = None):
        self.starting_per_position = starting_per_position or STARTING_CAPITAL_PER_POSITION
        self.equity_file = equity_file or (TRADES_DIR / EQUITY_CURVE_FILE)
        self.snapshots: List[EquitySnapshot] = []
        self._load_curve()

    def _load_curve(self) -> None:
        """Load historical equity curve from CSV."""
        if not self.equity_file.exists():
            return
        try:
            with open(self.equity_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.snapshots = [EquitySnapshot.from_csv_row(row) for row in reader]
        except Exception as e:
            print(f"  ⚠ Error loading equity curve: {e}")
            self.snapshots = []

    def _save_curve(self) -> None:
        """Save equity curve to CSV."""
        try:
            with open(self.equity_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=EQUITY_SNAPSHOT_FIELDS)
                writer.writeheader()
                for snap in self.snapshots:
                    writer.writerow(snap.to_csv_row())
        except Exception as e:
            print(f"  ⚠ Error saving equity curve: {e}")

    def _get_inception_date(self, trades: List[Trade]) -> str:
        """Get the earliest entry date across all trades."""
        dates = []
        for t in trades:
            if t.entry_date:
                try:
                    dates.append(datetime.strptime(t.entry_date, "%Y-%m-%d"))
                except ValueError:
                    continue
        return min(dates).strftime("%Y-%m-%d") if dates else ""

    def calculate_nav(self, trades: List[Trade], spy_data: pd.DataFrame = None,
                      qqq_data: pd.DataFrame = None) -> EquitySnapshot:
        """Calculate current NAV using the compounding replay model.

        Replays all trade events chronologically:
        1. Sort trades by entry_date
        2. For each trade, allocate starting_per_position (draw from cash pool
           if available, otherwise deploy new capital)
        3. For closed trades, return capital × (1 + trade_return) to cash
        4. For open trades, current value = allocation × (1 + unrealized_return)
        5. NAV = cash + open position values

        Returns:
            EquitySnapshot with current portfolio state.
        """
        if not trades:
            return EquitySnapshot(date=datetime.now().strftime("%Y-%m-%d"))

        alloc_per_trade = self.starting_per_position
        cash_pool = 0.0
        total_deployed = 0.0  # Total new capital ever injected
        trade_allocations = {}  # ticker -> allocated amount for open trades

        # Sort trades by entry date for chronological replay
        sorted_trades = sorted(trades, key=lambda t: t.entry_date or "9999")

        for trade in sorted_trades:
            if not trade.entry_date:
                continue

            # Determine allocation for this trade
            if cash_pool >= alloc_per_trade:
                # Draw from compounded profits
                allocation = alloc_per_trade
                cash_pool -= alloc_per_trade
            else:
                # Deploy new capital (partially from pool if available)
                new_capital_needed = alloc_per_trade - cash_pool
                allocation = alloc_per_trade
                cash_pool = 0.0
                total_deployed += new_capital_needed

            if trade.status in ("CLOSED", "STOPPED"):
                # Trade is closed — return capital with gains/losses to cash pool
                if trade.entry_price > 0 and trade.exit_price > 0:
                    trade_return = (trade.exit_price / trade.entry_price) - 1
                    returned_capital = allocation * (1 + trade_return)
                else:
                    returned_capital = allocation  # No price data, return flat
                cash_pool += returned_capital
            else:
                # Trade is open — track allocation
                trade_allocations[trade.ticker] = allocation

        # Calculate current value of open positions
        invested_value = 0.0
        open_count = 0
        for trade in trades:
            if trade.status == "OPEN" and trade.ticker in trade_allocations:
                allocation = trade_allocations[trade.ticker]
                if trade.entry_price > 0 and trade.current_price > 0:
                    current_value = allocation * (trade.current_price / trade.entry_price)
                elif trade.entry_price > 0 and trade.highest_close > 0:
                    # Fallback to highest_close if no current_price
                    current_value = allocation * (trade.highest_close / trade.entry_price)
                else:
                    current_value = allocation  # No price data, assume flat
                invested_value += current_value
                open_count += 1

        nav = cash_pool + invested_value

        # Ensure total_deployed is at least one position's worth
        if total_deployed <= 0:
            total_deployed = alloc_per_trade

        total_return_pct = ((nav / total_deployed) - 1) * 100

        # SPY comparison: what would total_deployed in SPY be worth since inception?
        inception_date = self._get_inception_date(trades)
        spy_value = total_deployed  # Default: flat
        spy_return_pct = 0.0

        if spy_data is not None and not spy_data.empty and inception_date:
            try:
                start_dt = pd.Timestamp(inception_date)
                spy_after_start = spy_data[spy_data.index >= start_dt]
                if len(spy_after_start) >= 2:
                    spy_start_price = spy_after_start['Close'].iloc[0]
                    spy_end_price = spy_after_start['Close'].iloc[-1]
                    if spy_start_price > 0:
                        spy_return_pct = ((spy_end_price / spy_start_price) - 1) * 100
                        spy_value = total_deployed * (1 + spy_return_pct / 100)
            except Exception:
                pass

        alpha_pct = total_return_pct - spy_return_pct

        # QQQ (NASDAQ) comparison: same logic as SPY
        qqq_value = total_deployed  # Default: flat
        qqq_return_pct = 0.0

        if qqq_data is not None and not qqq_data.empty and inception_date:
            try:
                start_dt = pd.Timestamp(inception_date)
                qqq_after_start = qqq_data[qqq_data.index >= start_dt]
                if len(qqq_after_start) >= 2:
                    qqq_start_price = qqq_after_start['Close'].iloc[0]
                    qqq_end_price = qqq_after_start['Close'].iloc[-1]
                    if qqq_start_price > 0:
                        qqq_return_pct = ((qqq_end_price / qqq_start_price) - 1) * 100
                        qqq_value = total_deployed * (1 + qqq_return_pct / 100)
            except Exception:
                pass

        alpha_vs_qqq_pct = total_return_pct - qqq_return_pct

        return EquitySnapshot(
            date=datetime.now().strftime("%Y-%m-%d"),
            nav=round(nav, 2),
            cash=round(cash_pool, 2),
            invested=round(invested_value, 2),
            total_deployed=round(total_deployed, 2),
            open_count=open_count,
            total_return_pct=round(total_return_pct, 2),
            spy_value=round(spy_value, 2),
            spy_return_pct=round(spy_return_pct, 2),
            alpha_pct=round(alpha_pct, 2),
            qqq_value=round(qqq_value, 2),
            qqq_return_pct=round(qqq_return_pct, 2),
            alpha_vs_qqq_pct=round(alpha_vs_qqq_pct, 2),
        )

    def record_snapshot(self, snapshot: EquitySnapshot) -> None:
        """Append snapshot to equity curve, deduplicating by date."""
        # Remove existing snapshot for same date
        self.snapshots = [s for s in self.snapshots if s.date != snapshot.date]
        self.snapshots.append(snapshot)
        # Sort by date
        self.snapshots.sort(key=lambda s: s.date)
        self._save_curve()

    def get_latest(self) -> Optional[EquitySnapshot]:
        """Get most recent equity snapshot."""
        return self.snapshots[-1] if self.snapshots else None

    def get_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak NAV in equity curve history.

        Returns:
            Max drawdown as negative percentage (e.g. -15.3 for 15.3% drawdown).
            Returns 0.0 if no drawdown or insufficient data.
        """
        if len(self.snapshots) < 2:
            return 0.0

        peak = self.snapshots[0].nav
        max_dd = 0.0

        for snap in self.snapshots:
            if snap.nav > peak:
                peak = snap.nav
            if peak > 0:
                dd = ((snap.nav - peak) / peak) * 100
                if dd < max_dd:
                    max_dd = dd

        return round(max_dd, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class PortfolioManager:
    """Manages the unified portfolio CSV and Google Sheets export."""
    
    CSV_FIELDNAMES = [
        'ticker', 'status', 'entry_date', 'entry_price', 'exit_date', 'exit_price',
        'highest_close', 'theme', 'tier', 'signal_type', 'conviction', 'notes', 'stop_pct',
        'position_size_pct', 'position_dollars', 'sizing_gear'
    ]
    
    def __init__(self, portfolio_file: Optional[Path] = None):
        self.portfolio_file = portfolio_file or PORTFOLIO_FILE
        self.trades: List[Trade] = []
        self.spy_data: pd.DataFrame = None
        self.qqq_data: pd.DataFrame = None
        self.equity_tracker = EquityTracker()
        self._load()
    
    def _load(self) -> None:
        """Load trades from CSV."""
        if not self.portfolio_file.exists():
            self.trades = []
            return
        
        try:
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.trades = [Trade.from_csv_row(row) for row in reader]
            # Validate loaded trades
            for trade in self.trades:
                for w in trade.validate():
                    print(f"  ⚠ WARNING (load): {w}")
        except Exception as e:
            print(f"  ⚠ Error loading portfolio: {e}")
            self.trades = []
    
    def _save(self) -> None:
        """Save trades to CSV using atomic write (temp file + rename)."""
        import tempfile
        import shutil

        # Create backup first
        if self.portfolio_file.exists():
            backup_file = BACKUP_DIR / f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            shutil.copy(self.portfolio_file, backup_file)

            # Cleanup old backups
            backups = sorted(BACKUP_DIR.glob("portfolio_*.csv"))
            if len(backups) > MAX_PORTFOLIO_BACKUPS:
                for old in backups[:-MAX_PORTFOLIO_BACKUPS]:
                    old.unlink()

        # Atomic write: write to temp file then rename
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', dir=str(self.portfolio_file.parent),
                suffix='.csv', delete=False, newline='', encoding='utf-8'
            ) as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDNAMES)
                writer.writeheader()
                for trade in self.trades:
                    for w in trade.validate():
                        print(f"  ⚠ WARNING (save): {w}")
                    writer.writerow(trade.to_csv_row())
                temp_path = f.name
            os.replace(temp_path, str(self.portfolio_file))
        except Exception:
            # Clean up temp file on failure
            import pathlib
            if 'temp_path' in locals() and pathlib.Path(temp_path).exists():
                pathlib.Path(temp_path).unlink()
            raise
    
    # ───────────────────────────────────────────────────────────────────────────
    # TRADE MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────
    
    def add_trade(self, ticker: str, entry_price: float, theme: str = "",
                  tier: str = "", signal_type: str = "PASS", conviction: int = 0,
                  notes: str = "", position_size_pct: float = 0.0,
                  position_dollars: float = 0.0, sizing_gear: str = "") -> Trade:
        """Add a new trade to the portfolio."""

        # Check if already exists as open position
        existing = self.get_open_position(ticker)
        if existing:
            print(f"  ⚠ {ticker} already has an open position")
            return existing

        trade = Trade(
            ticker=ticker.upper(),
            status="OPEN",
            entry_date=datetime.now().strftime("%Y-%m-%d"),
            entry_price=entry_price,
            highest_close=entry_price,
            theme=theme,
            tier=tier,
            signal_type=signal_type,
            conviction=conviction,
            notes=notes,
            position_size_pct=position_size_pct,
            position_dollars=position_dollars,
            sizing_gear=sizing_gear,
        )

        self.trades.append(trade)
        self._save()

        return trade

    def add_trade_from_stock(self, stock) -> Trade:
        """Add trade from a Stock object (scanner integration)."""
        return self.add_trade(
            ticker=stock.symbol,
            entry_price=stock.price,
            theme=getattr(stock, 'theme', ''),
            tier=getattr(stock, 'tier', ''),
            signal_type=getattr(stock, 'final_decision', 'PASS'),
            conviction=getattr(stock, 'conviction', 0),
            notes="",
            position_size_pct=getattr(stock, 'position_size_pct', 0.0),
            position_dollars=getattr(stock, 'position_dollars', 0.0),
            sizing_gear=getattr(stock, 'sizing_gear', ''),
        )
    
    def flag_exit(self, ticker: str, exit_price: float, reason: str = "Manual exit") -> Optional[Trade]:
        """Flag a trade as exited."""
        trade = self.get_open_position(ticker)
        if not trade:
            print(f"  ⚠ No open position found for {ticker}")
            return None
        
        # Determine status based on reason
        if "stop" in reason.lower() or "trailing" in reason.lower():
            trade.status = "STOPPED"
        else:
            trade.status = "CLOSED"
        
        trade.exit_date = datetime.now().strftime("%Y-%m-%d")
        trade.exit_price = exit_price
        trade.notes = f"{trade.notes}; Exit: {reason}".strip("; ")
        trade.calculate_metrics()
        
        self._save()
        return trade
    
    def get_open_position(self, ticker: str) -> Optional[Trade]:
        """Get open position for a ticker."""
        ticker = ticker.upper()
        for trade in self.trades:
            if trade.ticker == ticker and trade.status == "OPEN":
                return trade
        return None
    
    def get_open_positions(self) -> List[Trade]:
        """Get all open positions."""
        return [t for t in self.trades if t.status == "OPEN"]
    
    def get_closed_trades(self) -> List[Trade]:
        """Get all closed trades."""
        return [t for t in self.trades if t.status != "OPEN"]
    
    def get_open_symbols(self) -> set:
        """Get set of symbols with open positions."""
        return {t.ticker for t in self.trades if t.status == "OPEN"}
    
    # ───────────────────────────────────────────────────────────────────────────
    # PRICE UPDATES
    # ───────────────────────────────────────────────────────────────────────────
    
    def update_prices(self, stocks_dict: Optional[Dict] = None, check_delisted: bool = True) -> List[Trade]:
        """
        Update current prices for all open positions.

        Args:
            stocks_dict: Optional dict of {symbol: Stock} from scanner
                        If not provided, fetches prices via yfinance
            check_delisted: If True, validate tickers aren't delisted (slower)

        Returns:
            List of trades with stop alerts
        """
        open_trades = self.get_open_positions()
        if not open_trades:
            return []

        alerts = []

        # Optional: Check for delisted tickers (adds API calls, use sparingly)
        if check_delisted:
            symbols = [t.ticker for t in open_trades]
            invalid = check_portfolio_for_invalid_tickers(symbols)
            if invalid:
                print(f"  ⚠️ DELISTED TICKERS DETECTED: {', '.join(invalid)}")
                print(f"     Consider removing these from portfolio.csv")
                # Add notes to invalid trades
                for trade in open_trades:
                    if trade.ticker in invalid:
                        trade.notes = f"[DELISTED?] {trade.notes}".strip()

        if stocks_dict:
            # Use prices from scanner
            for trade in open_trades:
                if trade.ticker in stocks_dict:
                    stock = stocks_dict[trade.ticker]
                    trade.calculate_metrics(stock.price)
                    if trade.stop_alert:
                        alerts.append(trade)
        else:
            # Fetch prices via yfinance
            symbols = [t.ticker for t in open_trades]
            try:
                data = yf.download(symbols, period="5d", progress=False)
                
                if isinstance(data.columns, pd.MultiIndex):
                    for trade in open_trades:
                        try:
                            price = data['Close'][trade.ticker].iloc[-1]
                            if pd.notna(price):
                                trade.calculate_metrics(float(price))
                                if trade.stop_alert:
                                    alerts.append(trade)
                        except (KeyError, IndexError):
                            pass
                elif len(symbols) == 1:
                    # Single ticker case
                    try:
                        price = data['Close'].iloc[-1]
                        if pd.notna(price):
                            open_trades[0].calculate_metrics(float(price))
                            if open_trades[0].stop_alert:
                                alerts.append(open_trades[0])
                    except (KeyError, IndexError):
                        pass
            except Exception as e:
                print(f"  ⚠ Error fetching prices: {e}")
        
        self._save()
        return alerts
    
    def check_stop_signals(self, stocks_dict: Dict) -> List[Trade]:
        """
        Check for positions that hit their tiered profit lock.

        Sterling Grid exit: tiered profit lock only (ExD is handled by scanner).
        Below +50% return: no trailing stop (only ExD can exit).

        Returns list of trades that should be flagged as STOPPED.
        """
        triggered = []

        for trade in self.get_open_positions():
            if trade.ticker not in stocks_dict:
                continue

            stock = stocks_dict[trade.ticker]
            current_price = stock.price

            # Update highest close
            if current_price > trade.highest_close:
                trade.highest_close = current_price

            # Check tiered profit lock (Sterling Grid)
            if check_profit_lock is not None and trade.entry_price > 0:
                lock_result = check_profit_lock(trade.entry_price, current_price, trade.highest_close)
                if lock_result.get('triggered', False):
                    tier_info = lock_result.get('active_tier', 'unknown')
                    lock_level = lock_result.get('lock_level', 0)
                    trade.status = "STOPPED"
                    trade.exit_date = datetime.now().strftime("%Y-%m-%d")
                    trade.exit_price = current_price
                    trade.notes = f"{trade.notes}; Profit lock ({tier_info}) at ${current_price:.2f}, lock=${lock_level:.2f}".strip("; ")
                    trade.calculate_metrics()
                    triggered.append(trade)
                    continue

            # Not triggered — update metrics
            trade.calculate_metrics(current_price)

        if triggered:
            self._save()

        return triggered
    
    # ───────────────────────────────────────────────────────────────────────────
    # PERFORMANCE METRICS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _load_spy_data(self) -> None:
        """Load S&P 500 data for benchmarking."""
        if self.spy_data is None:
            try:
                self.spy_data = yf.download("SPY", period="2y", progress=False)
                if isinstance(self.spy_data.columns, pd.MultiIndex):
                    self.spy_data.columns = self.spy_data.columns.get_level_values(0)
            except Exception as e:
                print(f"  ⚠ Error loading SPY data: {e}")
                self.spy_data = pd.DataFrame()

    def _load_qqq_data(self) -> None:
        """Load NASDAQ-100 (QQQ) data for benchmarking."""
        if self.qqq_data is None:
            try:
                self.qqq_data = yf.download("QQQ", period="2y", progress=False)
                if isinstance(self.qqq_data.columns, pd.MultiIndex):
                    self.qqq_data.columns = self.qqq_data.columns.get_level_values(0)
            except Exception as e:
                print(f"  ⚠ Error loading QQQ data: {e}")
                self.qqq_data = pd.DataFrame()
    
    def get_spy_return(self, days: int) -> float:
        """Get S&P 500 return over specified calendar days (backward from today)."""
        self._load_spy_data()
        if self.spy_data.empty:
            return 0.0

        try:
            end_price = self.spy_data['Close'].iloc[-1]
            start_idx = min(days, len(self.spy_data) - 1)
            start_price = self.spy_data['Close'].iloc[-start_idx - 1]
            return ((end_price / start_price) - 1) * 100
        except (IndexError, KeyError):
            return 0.0

    def get_spy_return_for_period(self, start_date: str, end_date: str = None) -> float:
        """Get S&P 500 return over a specific date range (matched to trade holding period).

        Args:
            start_date: Start date string (YYYY-MM-DD), typically trade entry date.
            end_date: End date string (YYYY-MM-DD), or None for today.

        Returns:
            SPY percentage return over that exact period.
        """
        self._load_spy_data()
        if self.spy_data.empty:
            return 0.0

        try:
            start_dt = pd.Timestamp(start_date)
            end_dt = pd.Timestamp(end_date) if end_date else pd.Timestamp(datetime.now().strftime("%Y-%m-%d"))

            # Find closest trading day on or after start_date
            spy_after_start = self.spy_data[self.spy_data.index >= start_dt]
            spy_before_end = self.spy_data[self.spy_data.index <= end_dt]

            if spy_after_start.empty or spy_before_end.empty:
                return 0.0

            start_price = spy_after_start['Close'].iloc[0]
            end_price = spy_before_end['Close'].iloc[-1]

            if start_price <= 0:
                return 0.0

            return ((end_price / start_price) - 1) * 100
        except Exception:
            return 0.0
    
    def get_spy_ytd_return(self) -> float:
        """Get S&P 500 YTD return."""
        self._load_spy_data()
        if self.spy_data.empty:
            return 0.0
        
        try:
            year_start = datetime(datetime.now().year, 1, 1)
            ytd_data = self.spy_data[self.spy_data.index >= pd.Timestamp(year_start)]
            if len(ytd_data) < 2:
                return 0.0
            return ((ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1) * 100
        except (IndexError, KeyError):
            return 0.0
    
    def calculate_portfolio_return(self, days: Optional[int] = None, ytd: bool = False) -> Tuple[float, int]:
        """
        Calculate portfolio return over specified period.
        
        Returns: (return_pct, num_trades)
        """
        closed = self.get_closed_trades()
        if not closed:
            return 0.0, 0
        
        # Filter by date (with error handling for malformed dates)
        def parse_exit_date(trade):
            """Safely parse exit date, returns None if malformed."""
            try:
                return datetime.strptime(trade.exit_date, "%Y-%m-%d")
            except (ValueError, AttributeError):
                return None

        if ytd:
            year_start = datetime(datetime.now().year, 1, 1)
            relevant = [t for t in closed if (dt := parse_exit_date(t)) and dt >= year_start]
        elif days:
            cutoff = datetime.now() - timedelta(days=days)
            relevant = [t for t in closed if (dt := parse_exit_date(t)) and dt >= cutoff]
        else:
            relevant = closed
        
        if not relevant:
            return 0.0, 0
        
        # Calculate average return
        returns = [t.pnl_pct for t in relevant if t.pnl_pct != 0]
        if not returns:
            return 0.0, 0
        
        return sum(returns) / len(returns), len(returns)
    
    def _matched_spy_alpha(self, trades: List[Trade]) -> float:
        """Calculate alpha vs SPY using matched holding periods for each trade.

        For each trade, computes SPY return over that trade's exact
        entry→exit (closed) or entry→today (open) window, then returns
        the average (portfolio_return - spy_return) across all trades.
        """
        if not trades:
            return 0.0

        alphas = []
        for t in trades:
            if not t.entry_date or t.pnl_pct == 0:
                continue
            end_date = t.exit_date if t.status != "OPEN" and t.exit_date else None
            spy_ret = self.get_spy_return_for_period(t.entry_date, end_date)
            alphas.append(t.pnl_pct - spy_ret)

        return sum(alphas) / len(alphas) if alphas else 0.0

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance metrics."""
        open_trades = self.get_open_positions()
        closed_trades = self.get_closed_trades()

        # Calculate dollar-weighted unrealized P&L for open positions
        open_with_pnl = [t for t in open_trades if t.pnl_pct != 0 and t.entry_price > 0]
        if open_with_pnl:
            # Weight by entry_price (proxy for position value since no share count)
            total_weight = sum(t.entry_price for t in open_with_pnl)
            if total_weight > 0:
                unrealized_pnl = sum(t.pnl_pct * t.entry_price for t in open_with_pnl) / total_weight
            else:
                unrealized_pnl = 0.0
        else:
            unrealized_pnl = 0.0

        # Win rate
        winners = [t for t in closed_trades if t.pnl_pct > 0]
        losers = [t for t in closed_trades if t.pnl_pct < 0]
        win_rate = len(winners) / len(closed_trades) * 100 if closed_trades else 0

        # Average winner/loser
        avg_winner = sum(t.pnl_pct for t in winners) / len(winners) if winners else 0
        avg_loser = sum(t.pnl_pct for t in losers) / len(losers) if losers else 0

        # Period returns (for closed trades exiting within window)
        ret_7d, n_7d = self.calculate_portfolio_return(days=7)
        ret_30d, n_30d = self.calculate_portfolio_return(days=30)
        ret_90d, n_90d = self.calculate_portfolio_return(days=90)
        ret_180d, n_180d = self.calculate_portfolio_return(days=180)
        ret_ytd, n_ytd = self.calculate_portfolio_return(ytd=True)
        ret_365d, n_365d = self.calculate_portfolio_return(days=365)

        # SPY returns — calendar-window for backward compat display
        spy_7d = self.get_spy_return(7)
        spy_30d = self.get_spy_return(30)
        spy_90d = self.get_spy_return(90)
        spy_180d = self.get_spy_return(180)
        spy_ytd = self.get_spy_ytd_return()
        spy_365d = self.get_spy_return(365)

        # Matched-period alpha (accurate per-trade comparison)
        all_trades_with_pnl = [t for t in self.trades if t.pnl_pct != 0 and t.entry_date]
        matched_alpha = self._matched_spy_alpha(all_trades_with_pnl)

        return {
            'open_positions': len(open_trades),
            'closed_trades': len(closed_trades),
            'total_trades': len(self.trades),
            'unrealized_pnl_pct': unrealized_pnl,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'winners': len(winners),
            'losers': len(losers),
            'matched_alpha': matched_alpha,
            'periods': {
                '7d': {'portfolio': ret_7d, 'spy': spy_7d, 'alpha': ret_7d - spy_7d, 'trades': n_7d},
                '30d': {'portfolio': ret_30d, 'spy': spy_30d, 'alpha': ret_30d - spy_30d, 'trades': n_30d},
                '90d': {'portfolio': ret_90d, 'spy': spy_90d, 'alpha': ret_90d - spy_90d, 'trades': n_90d},
                '180d': {'portfolio': ret_180d, 'spy': spy_180d, 'alpha': ret_180d - spy_180d, 'trades': n_180d},
                'ytd': {'portfolio': ret_ytd, 'spy': spy_ytd, 'alpha': ret_ytd - spy_ytd, 'trades': n_ytd},
                '1y': {'portfolio': ret_365d, 'spy': spy_365d, 'alpha': ret_365d - spy_365d, 'trades': n_365d},
            }
        }
    
    # ───────────────────────────────────────────────────────────────────────────
    # COMPOUNDING EQUITY
    # ───────────────────────────────────────────────────────────────────────────

    def update_equity_curve(self) -> EquitySnapshot:
        """Calculate current NAV and record to equity curve.

        Loads SPY and QQQ data for benchmarks, computes compounding NAV,
        and appends snapshot to equity_curve.csv.
        """
        self._load_spy_data()
        self._load_qqq_data()
        snapshot = self.equity_tracker.calculate_nav(
            self.trades, self.spy_data, self.qqq_data
        )
        self.equity_tracker.record_snapshot(snapshot)
        return snapshot

    def get_compounding_summary(self) -> Dict:
        """Get compounding portfolio summary for newsletter/display.

        Updates prices, calculates NAV, and returns a dict with all
        compounding metrics including SPY comparison and alpha.
        """
        self.update_prices()
        snapshot = self.update_equity_curve()
        inception = self.equity_tracker._get_inception_date(self.trades)
        max_dd = self.equity_tracker.get_max_drawdown()

        return {
            'starting_per_position': self.equity_tracker.starting_per_position,
            'total_deployed': snapshot.total_deployed,
            'current_nav': snapshot.nav,
            'total_return_pct': snapshot.total_return_pct,
            'cash': snapshot.cash,
            'invested': snapshot.invested,
            'open_count': snapshot.open_count,
            'spy_value': snapshot.spy_value,
            'spy_return_pct': snapshot.spy_return_pct,
            'alpha_pct': snapshot.alpha_pct,
            'qqq_value': snapshot.qqq_value,
            'qqq_return_pct': snapshot.qqq_return_pct,
            'alpha_vs_qqq_pct': snapshot.alpha_vs_qqq_pct,
            'max_drawdown_pct': max_dd,
            'inception_date': inception,
            'currency': CURRENCY_SYMBOL,
        }

    # ───────────────────────────────────────────────────────────────────────────
    # GOOGLE SHEETS EXPORT
    # ───────────────────────────────────────────────────────────────────────────

    def export_for_google_sheets(self, output_file: Optional[Path] = None) -> Path:
        """
        Export portfolio in a format optimized for Google Sheets.
        
        Creates a CSV that when imported to Google Sheets, can have 
        GOOGLEFINANCE formulas added for live price tracking.
        """
        output_file = output_file or SHEETS_EXPORT_FILE
        
        # Update prices first
        self.update_prices()
        
        # Columns for Google Sheets (includes calculated fields as starting values)
        sheets_fieldnames = [
            'ticker', 'status', 'entry_date', 'entry_price', 'exit_date', 'exit_price',
            'current_price', 'highest_close', 'stop_level', 'pnl_pct', 'pnl_usd',
            'days_held', 'distance_to_stop', 'stop_alert', 'theme', 'tier', 
            'signal_type', 'conviction', 'notes'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sheets_fieldnames)
            writer.writeheader()
            
            for trade in self.trades:
                trade.calculate_metrics()
                writer.writerow({
                    'ticker': trade.ticker,
                    'status': trade.status,
                    'entry_date': trade.entry_date,
                    'entry_price': f"{trade.entry_price:.2f}" if trade.entry_price else "",
                    'exit_date': trade.exit_date,
                    'exit_price': f"{trade.exit_price:.2f}" if trade.exit_price else "",
                    'current_price': f"{trade.current_price:.2f}" if trade.current_price else "",
                    'highest_close': f"{trade.highest_close:.2f}" if trade.highest_close else "",
                    'stop_level': f"{trade.stop_level:.2f}" if trade.stop_level else "",
                    'pnl_pct': f"{trade.pnl_pct:.1f}%" if trade.pnl_pct else "",
                    'pnl_usd': f"{trade.pnl_usd:.2f}" if trade.pnl_usd else "",
                    'days_held': str(trade.days_held) if trade.days_held else "",
                    'distance_to_stop': f"{trade.distance_to_stop_pct:.1f}%" if trade.distance_to_stop_pct else "",
                    'stop_alert': "⚠️" if trade.stop_alert else "",
                    'theme': trade.theme,
                    'tier': trade.tier,
                    'signal_type': trade.signal_type,
                    'conviction': str(trade.conviction) if trade.conviction else "",
                    'notes': trade.notes
                })
        
        return output_file
    
    def generate_google_sheets_template(self) -> str:
        """
        Generate instructions and formulas for Google Sheets setup.
        
        Returns markdown with setup instructions.
        """
        template = """# Google Sheets Portfolio Setup

## Step 1: Import CSV
1. Open Google Sheets
2. File → Import → Upload `portfolio_google_sheets.csv`
3. Select "Replace current sheet"

## Step 2: Add Live Price Formula Column
After column G (current_price), the formula should reference ticker in column A.

**For OPEN positions only**, replace the static current_price with this formula in G2:
```
=IF(B2="OPEN", GOOGLEFINANCE(A2, "price"), G2)
```
Then drag down for all rows.

## Step 3: Add Calculated Columns with Formulas

Replace these columns with formulas (assuming row 2 is first data row):

### Column I - Stop Level (uses per-trade stop_pct if set, else 20%):
```
=IF(B2="OPEN", IF(S2<>"", H2*(1-S2/100), H2*0.8), "")
```

### Column J - P&L % :
```
=IF(B2="OPEN", (G2-D2)/D2, IF(F2<>"", (F2-D2)/D2, ""))
```

### Column K - P&L $ (assuming 100 shares):
```
=IF(B2="OPEN", (G2-D2)*100, IF(F2<>"", (F2-D2)*100, ""))
```

### Column L - Days Held:
```
=IF(B2="OPEN", TODAY()-C2, IF(E2<>"", E2-C2, ""))
```

### Column M - Distance to Stop %:
```
=IF(B2="OPEN", (G2-I2)/G2, "")
```

### Column N - Stop Alert:
```
=IF(AND(B2="OPEN", M2<0.05), "⚠️ CLOSE TO STOP", "")
```

## Step 4: Add Performance Summary Section

Below your trade data, add a summary section:

### Portfolio Stats:
```
Open Positions:    =COUNTIF(B:B, "OPEN")
Closed Trades:     =COUNTIF(B:B, "CLOSED") + COUNTIF(B:B, "STOPPED")
Win Rate:          =COUNTIF(J:J, ">0") / (COUNTIF(J:J, ">0") + COUNTIF(J:J, "<0"))
Avg Winner:        =AVERAGEIF(J:J, ">0")
Avg Loser:         =AVERAGEIF(J:J, "<0")
```

### S&P 500 Comparison:
```
SPY Price:         =GOOGLEFINANCE("SPY", "price")
SPY 7D Change:     =GOOGLEFINANCE("SPY", "changepct") / 100
SPY 52W Change:    =GOOGLEFINANCE("SPY", "change52") / GOOGLEFINANCE("SPY", "price")
```

## Step 5: Conditional Formatting

1. Select the P&L % column
2. Format → Conditional formatting
3. Add rules:
   - Green background if > 0
   - Red background if < 0

4. Select the Stop Alert column
5. Add rule:
   - Red background if contains "⚠️"

## Auto-Refresh
Google Sheets updates GOOGLEFINANCE every 15-20 minutes during market hours.
For manual refresh: Ctrl+Shift+E (or Cmd+Shift+E on Mac)
"""
        return template
    
    # ───────────────────────────────────────────────────────────────────────────
    # MIGRATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def migrate_from_old_format(self) -> List[Trade]:
        """Migrate from separate open_positions.csv and trade_log.csv to unified format."""
        
        migrated = []
        seen_tickers = set()
        
        # Load open positions
        if OLD_OPEN_POSITIONS.exists():
            print(f"  Migrating from {OLD_OPEN_POSITIONS}...")
            with open(OLD_OPEN_POSITIONS, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get('symbol', row.get('ticker', '')).upper()
                    if not ticker or ticker in seen_tickers:
                        continue
                    
                    trade = Trade(
                        ticker=ticker,
                        status="OPEN",
                        entry_date=row.get('entry_date', ''),
                        entry_price=float(row.get('entry_price') or 0),
                        highest_close=float(row.get('highest_close') or row.get('entry_price') or 0),
                        theme=row.get('theme', ''),
                        tier=row.get('tier', ''),
                        signal_type=row.get('decision', row.get('signal_type', 'PASS')),
                        conviction=int(row.get('conviction') or 0),
                        notes=f"Migrated from open_positions.csv"
                    )
                    migrated.append(trade)
                    seen_tickers.add(ticker)
            
            print(f"    ✓ Loaded {len(migrated)} open positions")
        
        # Note: trade_log.csv contains all signals, not just trades actually taken
        # We'll note this but not automatically import as closed trades
        if OLD_TRADE_LOG.exists():
            print(f"  ℹ Found {OLD_TRADE_LOG} - contains signal history (not importing as trades)")
            print(f"    To import closed trades, add them manually to portfolio.csv")
        
        if migrated:
            self.trades = migrated
            self._save()
            print(f"\n  ✅ Migration complete: {len(migrated)} trades in portfolio.csv")
            
            # Backup old files
            if OLD_OPEN_POSITIONS.exists():
                backup = BACKUP_DIR / f"open_positions_backup_{datetime.now().strftime('%Y%m%d')}.csv"
                import shutil
                shutil.copy(OLD_OPEN_POSITIONS, backup)
                print(f"  📁 Backed up old file to {backup}")
        else:
            print("  ℹ No trades to migrate")
        
        return migrated
    
    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────
    
    def print_summary(self) -> None:
        """Print portfolio summary to terminal."""
        
        self.update_prices()
        stats = self.get_performance_summary()
        
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " STERLING SIGNALS PORTFOLIO ".center(68) + "║")
        print("║" + datetime.now().strftime("%B %d, %Y").center(68) + "║")
        print("╚" + "═" * 68 + "╝")
        
        # Open Positions
        open_trades = self.get_open_positions()
        print(f"\n  📈 OPEN POSITIONS ({len(open_trades)})")
        print("  " + "─" * 66)
        
        if open_trades:
            print(f"  {'Ticker':<8} {'Entry':>10} {'Current':>10} {'P&L':>10} {'Stop':>10} {'Alert':<8}")
            print("  " + "─" * 66)
            for t in open_trades:
                alert = "⚠️" if t.stop_alert else ""
                print(f"  {t.ticker:<8} ${t.entry_price:>8.2f} ${t.current_price:>8.2f} {t.pnl_pct:>+9.1f}% ${t.stop_level:>8.2f} {alert:<8}")
        else:
            print("  No open positions")
        
        # Performance vs S&P
        print(f"\n  📊 PERFORMANCE vs S&P 500")
        print("  " + "─" * 66)
        print(f"  {'Period':<12} {'Portfolio':>12} {'S&P 500':>12} {'Alpha':>12} {'Trades':>10}")
        print("  " + "─" * 66)
        
        for period, data in stats['periods'].items():
            if data['trades'] > 0:
                alpha_str = f"{data['alpha']:+.1f}%" if data['alpha'] else "N/A"
                print(f"  {period:<12} {data['portfolio']:>+11.1f}% {data['spy']:>+11.1f}% {alpha_str:>12} {data['trades']:>10}")
        
        # Statistics
        print(f"\n  📈 STATISTICS")
        print("  " + "─" * 66)
        print(f"  Win Rate: {stats['win_rate']:.1f}% │ Avg Winner: {stats['avg_winner']:+.1f}% │ Avg Loser: {stats['avg_loser']:+.1f}%")
        print(f"  Total Trades: {stats['total_trades']} │ Winners: {stats['winners']} │ Losers: {stats['losers']}")
        if stats.get('matched_alpha') is not None:
            print(f"  Matched-Period Alpha vs SPY: {stats['matched_alpha']:+.1f}%")

        # Compounding Equity
        try:
            snapshot = self.update_equity_curve()
            inception = self.equity_tracker._get_inception_date(self.trades)
            max_dd = self.equity_tracker.get_max_drawdown()

            print(f"\n  💰 COMPOUNDING EQUITY (Since {inception})")
            print("  " + "─" * 66)
            print(f"  Capital Per Position: {CURRENCY_SYMBOL}{self.equity_tracker.starting_per_position:,.0f}")
            print(f"  Total Deployed:       {CURRENCY_SYMBOL}{snapshot.total_deployed:,.0f}")
            print(f"  Current NAV:          {CURRENCY_SYMBOL}{snapshot.nav:,.2f}  ({snapshot.total_return_pct:+.1f}%)")
            print(f"  Cash Pool:            {CURRENCY_SYMBOL}{snapshot.cash:,.2f}")
            print(f"  Invested:             {CURRENCY_SYMBOL}{snapshot.invested:,.2f}  ({snapshot.open_count} positions)")
            print(f"  SPY Equivalent:       {CURRENCY_SYMBOL}{snapshot.spy_value:,.2f}  ({snapshot.spy_return_pct:+.1f}%)")
            print(f"  Alpha vs SPY:         {snapshot.alpha_pct:+.1f}%")
            if max_dd < 0:
                print(f"  Max Drawdown:         {max_dd:.1f}%")
        except Exception as e:
            print(f"\n  ⚠ Equity tracking: {e}")

        print("")


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNER INTEGRATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_portfolio(status_filter: str = None, compute_pnl: bool = False) -> List[Dict]:
    """Load trades from portfolio.csv as a list of dicts.

    Canonical implementation — import this instead of writing ad-hoc CSV readers.

    Args:
        status_filter: If set (e.g. "OPEN"), only return trades matching that status.
        compute_pnl: If True, convert numeric fields and compute pnl_pct in-memory.

    Returns:
        List of trade dicts, one per CSV row.
    """
    if not PORTFOLIO_FILE.exists():
        return []

    trades = []
    try:
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if status_filter and row.get('status') != status_filter:
                    continue
                if compute_pnl:
                    row['entry_price'] = float(row.get('entry_price') or 0)
                    row['current_price'] = float(row.get('current_price') or row.get('entry_price') or 0)
                    row['highest_close'] = float(row.get('highest_close') or 0)
                    row['conviction'] = int(row.get('conviction') or 0)
                    row['pnl_pct'] = (
                        ((row['current_price'] / row['entry_price']) - 1) * 100
                        if row['entry_price'] > 0 else 0.0
                    )
                trades.append(row)
    except Exception as e:
        print(f"  Error loading portfolio: {e}")
        return []

    return trades


def get_portfolio_manager() -> PortfolioManager:
    """Get singleton portfolio manager instance."""
    return PortfolioManager()


def add_trade_to_portfolio(stock) -> Trade:
    """Add a confirmed trade to the portfolio. Called by scanner."""
    pm = get_portfolio_manager()
    return pm.add_trade_from_stock(stock)


def check_portfolio_stops(stocks_dict: Dict) -> List[Trade]:
    """Check for stop triggers. Called by scanner."""
    pm = get_portfolio_manager()
    return pm.check_stop_signals(stocks_dict)


def get_open_position_symbols() -> set:
    """Get symbols with open positions. Called by scanner."""
    pm = get_portfolio_manager()
    return pm.get_open_symbols()


def update_portfolio_prices(stocks_dict: Optional[Dict] = None) -> None:
    """Update prices for open positions. Called by scanner."""
    pm = get_portfolio_manager()
    pm.update_prices(stocks_dict)
    pm.export_for_google_sheets()


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED PRICE/BENCHMARK FUNCTIONS (canonical implementations)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_current_prices(tickers: List[str], warn_threshold: float = 0.5) -> Dict[str, float]:
    """Fetch current prices for a list of tickers via yfinance.

    This is the canonical implementation — other modules should import from here.

    Args:
        tickers: List of ticker symbols to fetch
        warn_threshold: Warn if fewer than this fraction of tickers have valid prices

    Returns:
        Dict mapping ticker symbols to current prices
    """
    if not tickers:
        return {}

    prices = {}
    failed_tickers = []

    try:
        data = yf.download(
            tickers,
            period="1d",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if len(tickers) == 1:
            ticker = tickers[0]
            if not data.empty and 'Close' in data.columns:
                prices[ticker] = round(float(data['Close'].iloc[-1]), 2)
            else:
                failed_tickers.append(ticker)
        else:
            if not data.empty and 'Close' in data.columns:
                for ticker in tickers:
                    try:
                        price = data['Close'][ticker].iloc[-1]
                        if not (price != price):  # Check for NaN
                            prices[ticker] = round(float(price), 2)
                        else:
                            failed_tickers.append(ticker)
                    except (KeyError, IndexError):
                        failed_tickers.append(ticker)
            else:
                failed_tickers = list(tickers)

    except Exception as e:
        print(f"  ❌ Error fetching prices: {e}")
        failed_tickers = list(tickers)

    # Validate completeness
    if tickers:
        success_rate = len(prices) / len(tickers)
        if success_rate < warn_threshold:
            print(f"  ⚠️ WARNING: Price fetch incomplete - only {len(prices)}/{len(tickers)} tickers ({success_rate*100:.1f}%)")
            if failed_tickers:
                sample = failed_tickers[:5]
                remaining = len(failed_tickers) - 5
                print(f"     Failed tickers: {', '.join(sample)}{f' +{remaining} more' if remaining > 0 else ''}")

    return prices


def get_spy_ytd_return() -> float:
    """Get SPY YTD return for benchmark comparison.

    This is the canonical implementation — other modules should import from here.

    Returns:
        SPY year-to-date return as percentage (e.g. 12.5 for +12.5%)
    """
    try:
        import pandas as pd

        spy = yf.Ticker("SPY")
        hist = spy.history(period="1y")

        year_start = datetime(datetime.now().year, 1, 1)
        ytd_data = hist[hist.index >= pd.Timestamp(year_start)]

        if len(ytd_data) >= 2:
            return ((ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1) * 100
    except ImportError:
        print("  Note: yfinance not available for SPY comparison")
    except Exception as e:
        print(f"  Warning: Could not fetch SPY data: {e}")

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse
    
    parser = argparse.ArgumentParser(description="Portfolio Manager - Unified Trade Tracking")
    parser.add_argument("--update", action="store_true", help="Update prices for open positions")
    parser.add_argument("--export", action="store_true", help="Export for Google Sheets")
    parser.add_argument("--migrate", action="store_true", help="Migrate from old format")
    parser.add_argument("--report", action="store_true", help="Print portfolio summary")
    parser.add_argument("--equity", action="store_true", help="Show compounding equity summary")
    parser.add_argument("--setup", action="store_true", help="Print Google Sheets setup instructions")
    parser.add_argument("--add", type=str, metavar="TICKER", help="Add a new trade")
    parser.add_argument("--price", type=float, help="Entry price for --add")
    parser.add_argument("--theme", type=str, default="", help="Theme for --add")
    parser.add_argument("--exit", type=str, metavar="TICKER", help="Exit a position")
    parser.add_argument("--exit-price", type=float, help="Exit price for --exit")
    
    args = parser.parse_args()
    
    pm = PortfolioManager()
    
    if args.migrate:
        print("\n  Migrating to unified portfolio format...")
        pm.migrate_from_old_format()
    
    elif args.add:
        if not args.price:
            print("  Error: --price required when adding trade")
            return 1
        trade = pm.add_trade(args.add, args.price, theme=args.theme)
        print(f"\n  ✅ Added {trade.ticker} at ${trade.entry_price:.2f}")
    
    elif args.exit:
        if not args.exit_price:
            print("  Error: --exit-price required when exiting")
            return 1
        trade = pm.flag_exit(args.exit, args.exit_price)
        if trade:
            print(f"\n  ✅ Exited {trade.ticker} at ${trade.exit_price:.2f} ({trade.pnl_pct:+.1f}%)")
    
    elif args.update:
        print("\n  Updating prices...")
        alerts = pm.update_prices()
        print(f"  ✅ Updated {len(pm.get_open_positions())} positions")
        if alerts:
            print(f"\n  ⚠️ STOP ALERTS:")
            for t in alerts:
                print(f"     {t.ticker}: ${t.current_price:.2f} ({t.distance_to_stop_pct:.1f}% from stop)")
    
    elif args.export:
        output = pm.export_for_google_sheets()
        print(f"\n  ✅ Exported to {output}")
        print(f"     Import this file to Google Sheets and add GOOGLEFINANCE formulas")
    
    elif args.setup:
        print(pm.generate_google_sheets_template())

    elif args.equity:
        print("\n  Calculating compounding equity...")
        try:
            summary = pm.get_compounding_summary()
            print(f"\n  💰 COMPOUNDING EQUITY (Since {summary['inception_date']})")
            print("  " + "─" * 60)
            print(f"  Capital Per Position: {summary['currency']}{summary['starting_per_position']:,.0f}")
            print(f"  Total Deployed:       {summary['currency']}{summary['total_deployed']:,.0f}")
            print(f"  Current NAV:          {summary['currency']}{summary['current_nav']:,.2f}  ({summary['total_return_pct']:+.1f}%)")
            print(f"  Cash Pool:            {summary['currency']}{summary['cash']:,.2f}")
            print(f"  Invested:             {summary['currency']}{summary['invested']:,.2f}  ({summary['open_count']} positions)")
            print(f"  SPY Equivalent:       {summary['currency']}{summary['spy_value']:,.2f}  ({summary['spy_return_pct']:+.1f}%)")
            print(f"  Alpha vs SPY:         {summary['alpha_pct']:+.1f}%")
            if summary['max_drawdown_pct'] < 0:
                print(f"  Max Drawdown:         {summary['max_drawdown_pct']:.1f}%")
            print("")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            import traceback
            traceback.print_exc()

    elif args.report:
        pm.print_summary()
    
    else:
        # Default: show summary
        pm.print_summary()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
