#!/usr/bin/env python3
"""
SIGNAL TRACKER - Historical Signal Performance & Celebration Management
========================================================================

Tracks historical signals for big wins and manages celebration tracking
to avoid duplicate celebration posts.

Usage:
    from signal_tracker import (
        get_uncelebrated_wins,
        mark_as_celebrated,
        get_historical_winners,
        calculate_portfolio_vs_spy
    )
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import pandas as pd
import yfinance as yf

from config import (
    PORTFOLIO_FILE,
    CELEBRATIONS_FILE,
    MARKETING_THRESHOLDS,
    CELEBRATION_THRESHOLDS,
    CELEBRATION_KEYS,
    get_highest_uncelebrated_threshold,
)
from portfolio.manager import load_portfolio, fetch_current_prices


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class HistoricalSignal:
    """A historical signal with performance data."""
    ticker: str
    entry_date: str
    entry_price: float
    current_price: float
    pnl_pct: float
    theme: str
    conviction: int
    days_held: int
    status: str  # OPEN, CLOSED, STOPPED

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BigWin:
    """A big win ready for celebration."""
    ticker: str
    entry_date: str
    entry_price: float
    current_price: float
    pnl_pct: float
    theme: str
    threshold_crossed: float  # 25, 50, or 100
    celebration_type: str  # "big_win", "home_run", "hall_of_fame"

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# FILE PATHS
# =============================================================================

# PORTFOLIO_FILE and CELEBRATIONS_FILE imported from config


# =============================================================================
# PORTFOLIO LOADING
# =============================================================================

def load_portfolio() -> List[Dict]:
    """Load all trades from portfolio.csv.

    Delegates to the canonical implementation in portfolio_manager.
    """
    from portfolio.manager import load_portfolio as _load
    return _load()


def get_open_positions() -> List[Dict]:
    """Get only OPEN positions from portfolio."""
    trades = load_portfolio()
    return [t for t in trades if t.get('status', '').upper() == 'OPEN']


def get_closed_positions() -> List[Dict]:
    """Get CLOSED and STOPPED positions from portfolio."""
    trades = load_portfolio()
    return [t for t in trades if t.get('status', '').upper() in ['CLOSED', 'STOPPED']]


# fetch_current_prices imported from portfolio_manager (canonical implementation)

# =============================================================================
# PRICE FETCHING
# =============================================================================

def fetch_spy_return(days: int = 30) -> float:
    """Fetch SPY return over specified period."""
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period=f"{days}d")
        if len(hist) >= 2:
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return ((end_price / start_price) - 1) * 100
    except Exception as e:
        print(f"  Error fetching SPY: {e}")
    return 0.0


# =============================================================================
# HISTORICAL SIGNAL ANALYSIS
# =============================================================================

def load_historical_signals() -> List[HistoricalSignal]:
    """Load all historical signals with current prices and P&L."""
    trades = load_portfolio()
    if not trades:
        return []

    # Get unique tickers for open positions
    open_trades = [t for t in trades if t.get('status', '').upper() == 'OPEN']
    tickers = list(set(t.get('ticker', '').upper() for t in open_trades if t.get('ticker')))

    # Fetch current prices
    current_prices = fetch_current_prices(tickers) if tickers else {}

    signals = []
    for trade in trades:
        ticker = trade.get('ticker', '').upper()
        entry_price = float(trade.get('entry_price', 0) or 0)
        status = trade.get('status', '').upper()

        # Get current or exit price
        if status == 'OPEN':
            current_price = current_prices.get(ticker, entry_price)
        else:
            current_price = float(trade.get('exit_price', 0) or entry_price)

        # Calculate P&L
        pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0

        # Calculate days held
        entry_date = trade.get('entry_date', '')
        try:
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            if status == 'OPEN':
                days_held = (datetime.now() - entry_dt).days
            else:
                exit_date = trade.get('exit_date', '')
                exit_dt = datetime.strptime(exit_date, '%Y-%m-%d') if exit_date else datetime.now()
                days_held = (exit_dt - entry_dt).days
        except ValueError as e:
            # GAP 37 fix: Log warning instead of silently defaulting
            print(f"  ⚠️ Warning: Failed to parse date for {ticker}: entry_date='{entry_date}' - {e}")
            days_held = 0

        signals.append(HistoricalSignal(
            ticker=ticker,
            entry_date=entry_date,
            entry_price=entry_price,
            current_price=current_price,
            pnl_pct=pnl_pct,
            theme=trade.get('theme', ''),
            conviction=int(trade.get('conviction', 0) or 0),
            days_held=days_held,
            status=status
        ))

    return signals


def get_historical_winners(min_pnl: float = 0.0) -> List[HistoricalSignal]:
    """Get historical signals with P&L above threshold."""
    signals = load_historical_signals()
    return [s for s in signals if s.pnl_pct >= min_pnl]


def find_big_wins(signals: List[HistoricalSignal] = None) -> List[BigWin]:
    """Find signals that have crossed celebration thresholds."""
    if signals is None:
        signals = load_historical_signals()

    big_wins = []
    big_win_threshold = MARKETING_THRESHOLDS.get('big_win_threshold', 25.0)
    home_run_threshold = MARKETING_THRESHOLDS.get('home_run_threshold', 50.0)
    hall_of_fame_threshold = MARKETING_THRESHOLDS.get('hall_of_fame_threshold', 100.0)

    for signal in signals:
        if signal.pnl_pct >= big_win_threshold:
            # Determine celebration type
            if signal.pnl_pct >= hall_of_fame_threshold:
                celebration_type = "hall_of_fame"
                threshold_crossed = 100.0
            elif signal.pnl_pct >= home_run_threshold:
                celebration_type = "home_run"
                threshold_crossed = 50.0
            else:
                celebration_type = "big_win"
                threshold_crossed = 25.0

            big_wins.append(BigWin(
                ticker=signal.ticker,
                entry_date=signal.entry_date,
                entry_price=signal.entry_price,
                current_price=signal.current_price,
                pnl_pct=signal.pnl_pct,
                theme=signal.theme,
                threshold_crossed=threshold_crossed,
                celebration_type=celebration_type
            ))

    # Sort by P&L descending
    big_wins.sort(key=lambda x: x.pnl_pct, reverse=True)
    return big_wins


# =============================================================================
# CELEBRATION TRACKING
# =============================================================================

def load_celebrations() -> Dict[str, Dict]:
    """Load celebration tracking data."""
    if not CELEBRATIONS_FILE.exists():
        return {}

    try:
        with open(CELEBRATIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"  Error loading celebrations: {e}")
        return {}


def save_celebrations(celebrations: Dict[str, Dict]) -> None:
    """Save celebration tracking data."""
    try:
        CELEBRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CELEBRATIONS_FILE, 'w') as f:
            json.dump(celebrations, f, indent=2)
    except Exception as e:
        print(f"  Error saving celebrations: {e}")


def mark_as_celebrated(ticker: str, threshold: float) -> None:
    """Mark a threshold crossing as celebrated."""
    celebrations = load_celebrations()

    if ticker not in celebrations:
        celebrations[ticker] = {}

    key = CELEBRATION_KEYS.get(threshold)
    if key:
        celebrations[ticker][key] = datetime.now().strftime('%Y-%m-%d')
        save_celebrations(celebrations)
        print(f"  Marked {ticker} {threshold}% as celebrated")


def is_celebrated(ticker: str, threshold: float) -> bool:
    """Check if a threshold crossing has been celebrated."""
    celebrations = load_celebrations()
    ticker_celebrations = celebrations.get(ticker, {})
    key = CELEBRATION_KEYS.get(threshold)
    return bool(ticker_celebrations.get(key)) if key else False


def get_uncelebrated_wins() -> List[BigWin]:
    """Get big wins that haven't been celebrated yet."""
    big_wins = find_big_wins()
    celebrations = load_celebrations()

    uncelebrated = []
    for win in big_wins:
        ticker_celebrations = celebrations.get(win.ticker, {})

        # Check if this specific threshold has been celebrated
        highest_uncelebrated = get_highest_uncelebrated_threshold(
            win.pnl_pct,
            ticker_celebrations
        )

        if highest_uncelebrated:
            # Update the win with the actual uncelebrated threshold
            if highest_uncelebrated >= 100.0:
                celebration_type = "hall_of_fame"
            elif highest_uncelebrated >= 50.0:
                celebration_type = "home_run"
            else:
                celebration_type = "big_win"

            uncelebrated.append(BigWin(
                ticker=win.ticker,
                entry_date=win.entry_date,
                entry_price=win.entry_price,
                current_price=win.current_price,
                pnl_pct=win.pnl_pct,
                theme=win.theme,
                threshold_crossed=highest_uncelebrated,
                celebration_type=celebration_type
            ))

    return uncelebrated


# =============================================================================
# PORTFOLIO VS SPY COMPARISON
# =============================================================================

def calculate_portfolio_vs_spy(positions: List[Dict] = None) -> Dict:
    """
    Calculate portfolio performance vs SPY.

    Returns dict with:
    - portfolio_return: Average P&L of winning positions
    - spy_return: SPY return over matching period
    - outperformance: Difference (portfolio - SPY)
    - should_post_beat_spy: Boolean based on threshold
    """
    if positions is None:
        positions = get_open_positions()

    if not positions:
        return {
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'outperformance': 0.0,
            'should_post_beat_spy': False,
            'winners': [],
        }

    # Get current prices
    tickers = [p.get('ticker', '').upper() for p in positions if p.get('ticker')]
    current_prices = fetch_current_prices(tickers)

    # Safety check: if price fetch failed completely, assume safeguard should block
    # This is conservative - we don't want to post "beat SPY" if we can't verify prices
    if not current_prices and tickers:
        print("    ⚠ Price fetch failed - blocking beat_spy safeguard (conservative)")
        return {
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'outperformance': 0.0,
            'should_post_beat_spy': False,
            'winners': [],
            'error': 'price_fetch_failed',
        }

    # Calculate P&L for each position
    winners = []
    total_pnl = 0.0
    position_count = 0

    for pos in positions:
        ticker = pos.get('ticker', '').upper()
        entry_price = float(pos.get('entry_price', 0) or 0)
        current_price = current_prices.get(ticker, entry_price)

        if entry_price > 0:
            pnl_pct = ((current_price / entry_price) - 1) * 100
            total_pnl += pnl_pct
            position_count += 1

            if pnl_pct > 0:
                winners.append({
                    'ticker': ticker,
                    'pnl_pct': pnl_pct,
                    'entry_price': entry_price,
                    'current_price': current_price,
                })

    portfolio_return = total_pnl / position_count if position_count > 0 else 0.0

    # Use matched-period SPY comparison (fair alpha calculation)
    fair = calculate_fair_spy_comparison(positions)
    if fair.get('can_compare'):
        spy_return = fair['spy_return']
        outperformance = fair['alpha']
    else:
        # Fallback: 30-day calendar window (less accurate)
        spy_return = fetch_spy_return(30)
        outperformance = portfolio_return - spy_return

    # Check threshold
    threshold = MARKETING_THRESHOLDS.get('spy_outperformance_min', 5.0)
    should_post_beat_spy = outperformance >= threshold

    # Sort winners by P&L
    winners.sort(key=lambda x: x['pnl_pct'], reverse=True)

    return {
        'portfolio_return': portfolio_return,
        'spy_return': spy_return,
        'outperformance': outperformance,
        'should_post_beat_spy': should_post_beat_spy,
        'winners': winners[:5],  # Top 5 winners
        'comparison_type': 'matched_period' if fair.get('can_compare') else 'calendar_30d',
    }


# =============================================================================
# FAIR SPY COMPARISON (CRIT-4: Matched Holding Periods)
# =============================================================================

def calculate_fair_spy_comparison(positions: List[Dict] = None) -> Dict:
    """
    Calculate SPY comparison using MATCHED holding periods (CRIT-4 fix).

    Unlike calculate_portfolio_vs_spy() which uses a fixed 30-day window,
    this function compares each position's return to SPY's return over
    the EXACT same holding period.

    Returns:
        Dict with:
        - can_compare: Boolean indicating if comparison is valid
        - portfolio_return: Weighted average position return
        - spy_return: Weighted average SPY return over matched periods
        - alpha: Portfolio return - SPY return
        - comparison_type: Always 'matched_period'
        - positions: List of individual position comparisons
        - should_post_beat_spy: Boolean based on threshold
    """
    if positions is None:
        positions = get_open_positions()

    if not positions:
        return {
            'can_compare': False,
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'alpha': 0.0,
            'comparison_type': 'matched_period',
            'should_post_beat_spy': False,
            'positions': [],
        }

    # Get current prices for all positions
    tickers = [p.get('ticker', '').upper() for p in positions if p.get('ticker')]
    current_prices = fetch_current_prices(tickers)

    results = []

    # ── Fetch SPY data ONCE covering the earliest entry date ─────────────────
    # Bug fix: Previously fetched SPY per-position inside the loop (N+1 calls).
    # Now we fetch once from the earliest entry date and slice per position.
    entry_dates = []
    for pos in positions:
        ed = pos.get('entry_date')
        if ed:
            entry_dates.append(ed)

    if not entry_dates:
        return {
            'can_compare': False,
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'alpha': 0.0,
            'comparison_type': 'matched_period',
            'should_post_beat_spy': False,
            'positions': [],
        }

    earliest_date = min(entry_dates)
    try:
        spy_hist = yf.download("SPY", start=earliest_date, progress=False)
        if spy_hist.empty:
            print("    ⚠ SPY download returned empty — cannot compare")
            return {
                'can_compare': False,
                'portfolio_return': 0.0,
                'spy_return': 0.0,
                'alpha': 0.0,
                'comparison_type': 'matched_period',
                'should_post_beat_spy': False,
                'positions': [],
            }
        if isinstance(spy_hist.columns, pd.MultiIndex):
            spy_hist.columns = spy_hist.columns.get_level_values(0)
        if 'Close' not in spy_hist.columns:
            print("    ⚠ SPY data missing 'Close' column — cannot compare")
            return {
                'can_compare': False,
                'portfolio_return': 0.0,
                'spy_return': 0.0,
                'alpha': 0.0,
                'comparison_type': 'matched_period',
                'should_post_beat_spy': False,
                'positions': [],
            }
    except Exception as e:
        print(f"    ⚠ Failed to download SPY data: {e}")
        return {
            'can_compare': False,
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'alpha': 0.0,
            'comparison_type': 'matched_period',
            'should_post_beat_spy': False,
            'positions': [],
        }

    spy_end_price = spy_hist['Close'].iloc[-1]

    # ── Per-position alpha calculation (no additional API calls) ─────────────
    valid_position_count = 0
    for pos in positions:
        ticker = pos.get('ticker', '').upper()
        entry_date = pos.get('entry_date')
        entry_price = float(pos.get('entry_price', 0) or 0)
        current_price = current_prices.get(ticker, 0)

        if not entry_date or entry_price <= 0 or current_price <= 0:
            continue

        valid_position_count += 1

        # Calculate position return
        pos_return = ((current_price / entry_price) - 1) * 100

        # Slice SPY history from this position's entry date onward
        try:
            spy_slice = spy_hist.loc[entry_date:]
            if len(spy_slice) < 2:
                continue

            spy_start = spy_slice['Close'].iloc[0]
            spy_return = ((spy_end_price / spy_start) - 1) * 100

            alpha = pos_return - spy_return

            results.append({
                'ticker': ticker,
                'entry_date': entry_date,
                'pos_return': pos_return,
                'spy_return': spy_return,
                'alpha': alpha,
                'days_held': len(spy_slice),
            })
        except Exception as e:
            print(f"    ⚠ Failed to slice SPY data for {ticker}: {e}")
            continue

    # ── Require minimum 50% of positions to have valid SPY comparison ────────
    # Bug fix: Previously marked can_compare=True even if only 1 of 5 positions
    # had valid SPY data. Now require at least half.
    min_compared = max(1, valid_position_count // 2)
    if len(results) < min_compared:
        return {
            'can_compare': False,
            'portfolio_return': 0.0,
            'spy_return': 0.0,
            'alpha': 0.0,
            'comparison_type': 'matched_period',
            'should_post_beat_spy': False,
            'positions': results,
            'note': f'Only {len(results)}/{valid_position_count} positions had valid SPY data (need {min_compared}+)',
        }

    # Calculate averages (equal weight)
    avg_pos_return = sum(r['pos_return'] for r in results) / len(results)
    avg_spy_return = sum(r['spy_return'] for r in results) / len(results)
    avg_alpha = avg_pos_return - avg_spy_return
    avg_days_held = sum(r['days_held'] for r in results) // len(results)

    # Check threshold for beat_spy posting
    threshold = MARKETING_THRESHOLDS.get('spy_outperformance_min', 5.0)
    should_post = avg_alpha >= threshold

    return {
        'can_compare': True,
        'portfolio_return': avg_pos_return,
        'spy_return': avg_spy_return,
        'alpha': avg_alpha,
        'comparison_type': 'matched_period',
        'avg_days_held': avg_days_held,
        'should_post_beat_spy': should_post,
        'positions': sorted(results, key=lambda x: x['alpha'], reverse=True),
        'comparison_note': f"Returns compared over matched holding periods (avg {avg_days_held} days)",
    }


# =============================================================================
# SAFEGUARD FUNCTIONS (used by poster.py + live_tweet_generator.py)
# =============================================================================

def should_post_beat_spy() -> bool:
    """Check if we should post beat_spy content based on performance."""
    result = calculate_portfolio_vs_spy()
    return result.get('should_post_beat_spy', False)


def has_enough_wins(positions: List[Dict] = None, min_winners: int = None, min_pnl: float = None) -> bool:
    """Check if we have enough winners for top_performers content.

    Phase 9: Updated terminology from weekly_wins to top_performers.

    Args:
        positions: List of position dicts (if None, loads from portfolio.csv)
        min_winners: Minimum number of winners required
        min_pnl: Minimum P&L percentage to count as winner

    Returns:
        True if we have enough winners above threshold
    """
    if min_winners is None:
        min_winners = int(MARKETING_THRESHOLDS.get('min_winners_for_top_performers', 2))
    if min_pnl is None:
        min_pnl = 0.0  # Transparency: count any positive P&L as a winner

    if positions is None:
        positions = get_open_positions()

    if not positions:
        return False

    # Count winners above threshold
    winner_count = 0
    for pos in positions:
        # Check if P&L is already calculated
        pnl_pct = pos.get('pnl_pct')

        if pnl_pct is None:
            # Calculate P&L from entry/current prices
            entry_price = float(pos.get('entry_price', 0) or 0)
            current_price = float(pos.get('current_price', 0) or 0)

            if entry_price > 0 and current_price > 0:
                pnl_pct = ((current_price / entry_price) - 1) * 100
            else:
                continue

        if pnl_pct >= min_pnl:
            winner_count += 1

    return winner_count >= min_winners


def has_uncelebrated_wins() -> bool:
    """Check if there are any uncelebrated big wins."""
    uncelebrated = get_uncelebrated_wins()
    return len(uncelebrated) > 0


def has_winning_closed_trades() -> bool:
    """
    Check if there are any winning closed trades to highlight.
    GAP 36 fix: Safeguard for closed_trade category.

    Returns:
        True if at least one closed trade has positive P&L
    """
    closed = get_closed_positions()
    if not closed:
        return False

    winners = 0
    for trade in closed:
        entry = float(trade.get('entry_price') or 0)
        exit_price = float(trade.get('exit_price') or 0)
        if entry > 0 and exit_price > entry:
            winners += 1

    # Require at least one winner to post closed_trade content
    return winners > 0


def filter_public_positions(positions: List[Dict]) -> List[Dict]:
    """
    Filter positions to only include winners for public content.
    CRITICAL: Never expose losing positions publicly.

    Args:
        positions: List of position dicts (may have pnl_pct pre-calculated)

    Returns:
        Filtered list with only positive P&L positions
    """
    if not positions:
        return []

    # Check if we need to fetch prices (if pnl_pct not provided)
    needs_prices = any(p.get('pnl_pct') is None for p in positions)

    current_prices = {}
    if needs_prices:
        tickers = [p.get('ticker', '').upper() for p in positions if p.get('ticker')]
        current_prices = fetch_current_prices(tickers)

    public_positions = []
    for pos in positions:
        # CRIT-3: Never show stopped positions publicly
        status = pos.get('status', 'OPEN')
        if status == 'STOPPED':
            continue

        # Check if P&L is already calculated
        pnl_pct = pos.get('pnl_pct')

        # Coerce to float, handling string values from CSV
        if pnl_pct is not None:
            try:
                pnl_pct = float(pnl_pct)
            except (TypeError, ValueError):
                pnl_pct = None

        if pnl_pct is None:
            # Calculate P&L from prices
            ticker = pos.get('ticker', '').upper()
            entry_price = float(pos.get('entry_price', 0) or 0)
            current_price = current_prices.get(ticker, entry_price)

            if entry_price > 0:
                pnl_pct = ((current_price / entry_price) - 1) * 100
            else:
                continue

        # Skip if pnl_pct still could not be determined
        if pnl_pct is None:
            continue

        # Only include positions with positive P&L
        if pnl_pct >= 0:
            pos_copy = dict(pos)
            pos_copy['pnl_pct'] = pnl_pct
            public_positions.append(pos_copy)

    # Sort by P&L descending
    public_positions.sort(key=lambda x: x.get('pnl_pct', 0), reverse=True)
    return public_positions


def get_public_winners(min_pnl: float = 0.0) -> List[Dict]:
    """Get winning positions above threshold for public display."""
    positions = get_open_positions()
    public_positions = filter_public_positions(positions)
    return [p for p in public_positions if p.get('pnl_pct', 0) >= min_pnl]


def get_winners_for_showcase(
    threshold: float = 25.0,
    include_entry_price: bool = True,
    max_positions: int = 5
) -> List[Dict]:
    """
    Get winning positions for public showcase with entry prices.

    Full transparency: always shows entry prices for all qualifying positions.

    Args:
        threshold: Minimum P&L percentage for inclusion
        include_entry_price: Whether to include entry prices
        max_positions: Maximum number of positions to return

    Returns:
        List of winner dicts with entry prices always included
    """
    positions = filter_public_positions(get_open_positions())

    winners = []
    for pos in positions:
        pnl = pos.get('pnl_pct', 0)
        if pnl < threshold:
            continue

        # Calculate days held
        entry_date = pos.get('entry_date', '')
        days_held = 0
        if entry_date:
            try:
                entry = datetime.strptime(entry_date, '%Y-%m-%d')
                days_held = (datetime.now() - entry).days
            except (ValueError, TypeError):
                pass

        winner = {
            'ticker': pos.get('ticker', 'UNKNOWN'),
            'entry_price': pos.get('entry_price') if include_entry_price else None,
            'current_price': pos.get('current_price', pos.get('entry_price', 0)),
            'pnl_pct': pnl,
            'days_held': days_held,
            'theme': pos.get('theme', ''),
            'conviction': pos.get('conviction', 3),
            'show_entry': include_entry_price,
        }
        winners.append(winner)

    return sorted(winners, key=lambda x: x['pnl_pct'], reverse=True)[:max_positions]


def get_recent_closes(days: int = 14, winners_only: bool = True) -> List[Dict]:
    """
    Get positions closed within the specified number of days.

    Phase 10: MASTER_TODO.md compliance - get_recent_closes() function.

    Args:
        days: Look back this many days for recent closes (default: 14)
        winners_only: If True, only return profitable closes (default: True)

    Returns:
        List of closed position dicts with calculated P&L, sorted by exit date (newest first)
    """
    closed = get_closed_positions()
    if not closed:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for pos in closed:
        exit_date = pos.get('exit_date', '')
        if not exit_date:
            continue

        try:
            exit_dt = datetime.strptime(exit_date, '%Y-%m-%d')
            if exit_dt < cutoff:
                continue
        except ValueError:
            continue

        # Calculate P&L
        entry_price = float(pos.get('entry_price', 0) or 0)
        exit_price = float(pos.get('exit_price', 0) or 0)

        if entry_price > 0 and exit_price > 0:
            pnl_pct = ((exit_price / entry_price) - 1) * 100
        else:
            pnl_pct = 0.0

        # Filter based on winners_only
        if winners_only and pnl_pct <= 0:
            continue

        pos_copy = dict(pos)
        pos_copy['pnl_pct'] = pnl_pct
        pos_copy['exit_dt'] = exit_dt
        recent.append(pos_copy)

    # Sort by exit date (newest first)
    recent.sort(key=lambda x: x['exit_dt'], reverse=True)

    # Remove the datetime object before returning (not JSON serializable)
    for pos in recent:
        del pos['exit_dt']

    return recent


def get_early_movers(max_age_days: int = 14, min_gain: float = 5.0) -> List[Dict]:
    """
    Get new signals (< max_age_days old) showing early strength.

    Phase 10: MASTER_TODO.md compliance - get_early_movers() function.
    Used for the 'early_movers' content category.

    Args:
        max_age_days: Maximum position age to qualify as "early" (default: 14)
        min_gain: Minimum P&L percentage to show "early strength" (default: 5.0)

    Returns:
        List of position dicts that are young and showing gains, sorted by P&L descending
    """
    positions = get_open_positions()
    if not positions:
        return []

    # Get current prices
    tickers = [p.get('ticker', '').upper() for p in positions if p.get('ticker')]
    current_prices = fetch_current_prices(tickers) if tickers else {}

    cutoff = datetime.now() - timedelta(days=max_age_days)
    early_movers = []

    for pos in positions:
        entry_date = pos.get('entry_date', '')
        if not entry_date:
            continue

        # Check if position is young enough
        try:
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            if entry_dt < cutoff:
                continue
            days_held = (datetime.now() - entry_dt).days
        except ValueError:
            continue

        # Calculate P&L
        ticker = pos.get('ticker', '').upper()
        entry_price = float(pos.get('entry_price', 0) or 0)
        current_price = current_prices.get(ticker, entry_price)

        if entry_price > 0:
            pnl_pct = ((current_price / entry_price) - 1) * 100
        else:
            continue

        # Check if showing early strength
        if pnl_pct < min_gain:
            continue

        pos_copy = dict(pos)
        pos_copy['pnl_pct'] = pnl_pct
        pos_copy['current_price'] = current_price
        pos_copy['days_held'] = days_held
        early_movers.append(pos_copy)

    # Sort by P&L descending
    early_movers.sort(key=lambda x: x['pnl_pct'], reverse=True)
    return early_movers


def filter_expired_watchlist_signals(signals: List[Dict], max_age_days: int = 21) -> List[Dict]:
    """
    Remove CONSIDER/watchlist signals older than max_age_days.

    Prevents stale watchlist stocks from accumulating and being
    mentioned repeatedly in tweets.

    Args:
        signals: List of CONSIDER signal dicts
        max_age_days: Maximum age in days before expiry (default: 21)

    Returns:
        Filtered list with only signals newer than cutoff
    """
    if not signals:
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    valid_signals = []

    for sig in signals:
        # Try multiple date field names
        signal_date = sig.get('signal_date') or sig.get('entry_date') or sig.get('date', '')

        if signal_date:
            try:
                sig_dt = datetime.strptime(signal_date, '%Y-%m-%d')
                if sig_dt >= cutoff:
                    valid_signals.append(sig)
                else:
                    ticker = sig.get('ticker', sig.get('symbol', 'Unknown'))
                    print(f"    ⚠ Expired CONSIDER signal: {ticker} (dated {signal_date})")
            except ValueError:
                # Keep signals with unparseable dates (safer to include)
                valid_signals.append(sig)
        else:
            # Keep signals without dates (safer to include)
            valid_signals.append(sig)

    if len(signals) != len(valid_signals):
        print(f"    Filtered {len(signals) - len(valid_signals)} expired CONSIDER signals")

    return valid_signals


# Backward-compat alias (old name)
filter_expired_consider_signals = filter_expired_watchlist_signals


# =============================================================================
# COLD STREAK DETECTION
# =============================================================================

def check_cold_streak(lookback_days: int = 14, threshold: int = 3) -> Dict:
    """
    Check if recent closed trades indicate a cold streak.

    A cold streak is defined as having >= threshold consecutive losses
    in the lookback period. Used to add caution to marketing content
    or reduce posting frequency during poor performance.

    Args:
        lookback_days: Days to look back for recent closes (default: 14)
        threshold: Number of losses to trigger cold streak (default: 3)

    Returns:
        Dict with:
            - in_cold_streak: bool
            - recent_losses: int (count of losses in period)
            - recent_trades: int (total closed trades in period)
            - should_reduce_posting: bool (recommendation)
            - reason: str (explanation)
    """
    try:
        from portfolio.manager import PortfolioManager
        pm = PortfolioManager()
    except ImportError:
        return {
            'in_cold_streak': False,
            'recent_losses': 0,
            'recent_trades': 0,
            'should_reduce_posting': False,
            'reason': 'portfolio_manager not available'
        }

    cutoff = datetime.now() - timedelta(days=lookback_days)

    # Get recently closed trades
    recent_closed = []
    for trade in pm.get_closed_trades():
        if trade.exit_date:
            try:
                exit_dt = datetime.strptime(trade.exit_date, '%Y-%m-%d')
                if exit_dt >= cutoff:
                    recent_closed.append(trade)
            except ValueError:
                continue

    if len(recent_closed) < threshold:
        return {
            'in_cold_streak': False,
            'recent_losses': 0,
            'recent_trades': len(recent_closed),
            'should_reduce_posting': False,
            'reason': f'insufficient data ({len(recent_closed)} trades in period)'
        }

    # Sort by exit date (most recent first)
    recent_closed.sort(key=lambda x: x.exit_date, reverse=True)

    # Count losses in most recent trades
    losses = sum(1 for t in recent_closed[:threshold] if t.pnl_pct < 0)
    total_losses = sum(1 for t in recent_closed if t.pnl_pct < 0)

    in_cold_streak = losses >= threshold
    win_rate = 1 - (total_losses / len(recent_closed)) if recent_closed else 0

    return {
        'in_cold_streak': in_cold_streak,
        'recent_losses': total_losses,
        'recent_trades': len(recent_closed),
        'consecutive_losses': losses,
        'win_rate': win_rate,
        'should_reduce_posting': in_cold_streak,
        'reason': f'{losses} of last {threshold} trades were losses' if in_cold_streak
                  else f'win rate {win_rate:.0%} in last {lookback_days} days'
    }


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    """Run signal tracker analysis."""
    print("=" * 60)
    print("SIGNAL TRACKER - Historical Performance Analysis")
    print("=" * 60)

    # Load historical signals
    print("\n📊 Loading historical signals...")
    signals = load_historical_signals()
    print(f"  Found {len(signals)} signals in portfolio")

    # Show performance summary
    if signals:
        open_signals = [s for s in signals if s.status == 'OPEN']
        closed_signals = [s for s in signals if s.status != 'OPEN']

        print(f"\n  Open positions: {len(open_signals)}")
        print(f"  Closed positions: {len(closed_signals)}")

        if open_signals:
            avg_pnl = sum(s.pnl_pct for s in open_signals) / len(open_signals)
            print(f"\n  Average open P&L: {avg_pnl:+.1f}%")

            # Show top performers
            top_performers = sorted(open_signals, key=lambda x: x.pnl_pct, reverse=True)[:5]
            print("\n  Top 5 performers:")
            for s in top_performers:
                print(f"    {s.ticker}: {s.pnl_pct:+.1f}% ({s.theme})")

    # Check big wins
    print("\n🏆 Checking for big wins...")
    big_wins = find_big_wins()
    if big_wins:
        print(f"  Found {len(big_wins)} big wins:")
        for win in big_wins[:5]:
            print(f"    {win.ticker}: {win.pnl_pct:+.1f}% ({win.celebration_type})")
    else:
        print("  No big wins found")

    # Check uncelebrated wins
    print("\n🎉 Checking for uncelebrated wins...")
    uncelebrated = get_uncelebrated_wins()
    if uncelebrated:
        print(f"  Found {len(uncelebrated)} uncelebrated wins:")
        for win in uncelebrated:
            print(f"    {win.ticker}: {win.pnl_pct:+.1f}% (threshold: {win.threshold_crossed}%)")
    else:
        print("  All big wins have been celebrated")

    # Portfolio vs SPY
    print("\n📈 Portfolio vs SPY comparison...")
    comparison = calculate_portfolio_vs_spy()
    print(f"  Portfolio return: {comparison['portfolio_return']:+.1f}%")
    print(f"  SPY return (30d): {comparison['spy_return']:+.1f}%")
    print(f"  Outperformance: {comparison['outperformance']:+.1f}%")
    print(f"  Should post beat_spy: {comparison['should_post_beat_spy']}")

    # Safeguard status
    print("\n🛡️ Safeguard checks:")
    print(f"  should_post_beat_spy(): {should_post_beat_spy()}")
    print(f"  has_enough_wins(): {has_enough_wins()}")
    print(f"  has_uncelebrated_wins(): {has_uncelebrated_wins()}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
