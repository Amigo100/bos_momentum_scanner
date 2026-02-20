#!/usr/bin/env python3
"""
Backfill equity_curve.csv with historical data from portfolio inception.

Replays the NAV model from core/portfolio_manager.py for each trading day,
using historical stock prices from yfinance. This fills the gap between
portfolio inception (earliest entry_date) and the first equity_curve.csv entry.

Usage:
    python dashboard/scripts/backfill_equity_curve.py
"""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# Resolve paths — section-specific output directories
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PORTFOLIO_OUTPUT = PROJECT_ROOT / "portfolio" / "output"
PORTFOLIO_CSV = PORTFOLIO_OUTPUT / "portfolio.csv"
EQUITY_CSV = PORTFOLIO_OUTPUT / "equity_curve.csv"

# Legacy fallback paths (used if section dirs don't have the files yet)
LEGACY_TRADES_DIR = PROJECT_ROOT / "trades"
LEGACY_PORTFOLIO_CSV = LEGACY_TRADES_DIR / "portfolio.csv"
LEGACY_EQUITY_CSV = LEGACY_TRADES_DIR / "equity_curve.csv"

ALLOC_PER_TRADE = 5000.0  # £5,000 per position


def _resolve_portfolio_csv():
    """Find portfolio.csv: prefer section-specific, fallback to legacy trades/."""
    if PORTFOLIO_CSV.exists():
        return PORTFOLIO_CSV
    if LEGACY_PORTFOLIO_CSV.exists():
        return LEGACY_PORTFOLIO_CSV
    return PORTFOLIO_CSV  # Will error naturally if neither exists


def _resolve_equity_csv():
    """Find equity_curve.csv: prefer section-specific, fallback to legacy trades/."""
    if EQUITY_CSV.exists():
        return EQUITY_CSV
    if LEGACY_EQUITY_CSV.exists():
        return LEGACY_EQUITY_CSV
    return EQUITY_CSV  # Will be created if it doesn't exist


def load_trades():
    """Load all trades from portfolio.csv."""
    portfolio_path = _resolve_portfolio_csv()
    trades = []
    with open(portfolio_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("ticker"):
                continue
            trades.append({
                "ticker": row["ticker"],
                "status": row.get("status", "OPEN"),
                "entry_date": row.get("entry_date", ""),
                "entry_price": float(row.get("entry_price") or 0),
                "exit_date": row.get("exit_date", ""),
                "exit_price": float(row.get("exit_price") or 0),
                "highest_close": float(row.get("highest_close") or 0),
            })
    return trades


def load_existing_curve():
    """Load existing equity_curve.csv entries as a dict keyed by date."""
    existing = {}
    equity_path = _resolve_equity_csv()
    if equity_path.exists():
        with open(equity_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("date"):
                    existing[row["date"]] = row
    return existing


def get_inception_date(trades):
    """Find the earliest entry_date across all trades."""
    dates = []
    for t in trades:
        if t["entry_date"]:
            try:
                dates.append(datetime.strptime(t["entry_date"], "%Y-%m-%d"))
            except ValueError:
                continue
    return min(dates) if dates else None


def download_prices(tickers, start_date, end_date):
    """Download daily close prices for all tickers via yfinance."""
    all_tickers = list(set(tickers + ["SPY", "QQQ"]))
    print(f"  Downloading prices for {len(all_tickers)} tickers from {start_date} to {end_date}...")

    data = yf.download(
        all_tickers,
        start=start_date,
        end=end_date + timedelta(days=3),  # buffer for weekends
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        print("  ERROR: No data downloaded")
        return {}

    # Extract close prices
    prices = {}
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data["Close"] if "Close" in data.columns.get_level_values(0) else data
    else:
        close_data = data

    for ticker in all_tickers:
        try:
            if ticker in close_data.columns:
                series = close_data[ticker].dropna()
                prices[ticker] = series
        except (KeyError, TypeError):
            continue

    print(f"  Got prices for {len(prices)} tickers")
    return prices


def get_price_on_date(prices, ticker, target_date):
    """Get the close price for a ticker on or before a given date."""
    if ticker not in prices:
        return None
    series = prices[ticker]
    # Find the closest date on or before target
    ts = pd.Timestamp(target_date)
    before = series[series.index <= ts]
    if len(before) > 0:
        return float(before.iloc[-1])
    return None


def calculate_nav_for_date(trades, prices, target_date, inception_date):
    """Calculate NAV for a specific date using the compounding replay model."""
    target_str = target_date.strftime("%Y-%m-%d")

    # Sort trades by entry_date for chronological replay
    sorted_trades = sorted(trades, key=lambda t: t["entry_date"] or "9999")

    cash_pool = 0.0
    total_deployed = 0.0
    trade_allocations = {}  # ticker -> allocation

    for trade in sorted_trades:
        entry_date = trade["entry_date"]
        if not entry_date or entry_date > target_str:
            continue  # Trade hasn't started yet on this date

        # Allocate capital
        if cash_pool >= ALLOC_PER_TRADE:
            allocation = ALLOC_PER_TRADE
            cash_pool -= ALLOC_PER_TRADE
        else:
            new_capital = ALLOC_PER_TRADE - cash_pool
            allocation = ALLOC_PER_TRADE
            cash_pool = 0.0
            total_deployed += new_capital

        exit_date = trade["exit_date"]
        if exit_date and exit_date <= target_str:
            # Trade was closed by this date
            if trade["entry_price"] > 0 and trade["exit_price"] > 0:
                trade_return = (trade["exit_price"] / trade["entry_price"]) - 1
                cash_pool += allocation * (1 + trade_return)
            else:
                cash_pool += allocation
        else:
            # Trade is still open on this date
            trade_allocations[trade["ticker"]] = {
                "allocation": allocation,
                "entry_price": trade["entry_price"],
            }

    # Calculate current value of open positions
    invested_value = 0.0
    open_count = 0
    for ticker, info in trade_allocations.items():
        current_price = get_price_on_date(prices, ticker, target_date)
        if current_price and info["entry_price"] > 0:
            current_value = info["allocation"] * (current_price / info["entry_price"])
        else:
            current_value = info["allocation"]
        invested_value += current_value
        open_count += 1

    nav = cash_pool + invested_value
    if total_deployed <= 0:
        total_deployed = ALLOC_PER_TRADE
    total_return_pct = ((nav / total_deployed) - 1) * 100

    # SPY benchmark from inception
    spy_start = get_price_on_date(prices, "SPY", inception_date)
    spy_current = get_price_on_date(prices, "SPY", target_date)
    spy_return_pct = 0.0
    spy_value = total_deployed
    if spy_start and spy_current and spy_start > 0:
        spy_return_pct = ((spy_current / spy_start) - 1) * 100
        spy_value = total_deployed * (1 + spy_return_pct / 100)

    # QQQ benchmark from inception
    qqq_start = get_price_on_date(prices, "QQQ", inception_date)
    qqq_current = get_price_on_date(prices, "QQQ", target_date)
    qqq_return_pct = 0.0
    qqq_value = total_deployed
    if qqq_start and qqq_current and qqq_start > 0:
        qqq_return_pct = ((qqq_current / qqq_start) - 1) * 100
        qqq_value = total_deployed * (1 + qqq_return_pct / 100)

    alpha_pct = total_return_pct - spy_return_pct
    alpha_vs_qqq_pct = total_return_pct - qqq_return_pct

    return {
        "date": target_str,
        "nav": f"{nav:.2f}",
        "cash": f"{cash_pool:.2f}",
        "invested": f"{invested_value:.2f}",
        "total_deployed": f"{total_deployed:.2f}",
        "open_count": str(open_count),
        "total_return_pct": f"{total_return_pct:.2f}",
        "spy_value": f"{spy_value:.2f}",
        "spy_return_pct": f"{spy_return_pct:.2f}",
        "alpha_pct": f"{alpha_pct:.2f}",
        "qqq_value": f"{qqq_value:.2f}",
        "qqq_return_pct": f"{qqq_return_pct:.2f}",
        "alpha_vs_qqq_pct": f"{alpha_vs_qqq_pct:.2f}",
    }


def main():
    print("=" * 60)
    print("  Equity Curve Backfill")
    print("=" * 60)

    portfolio_path = _resolve_portfolio_csv()
    if not portfolio_path.exists():
        print(f"  ERROR: portfolio.csv not found at {PORTFOLIO_CSV} or {LEGACY_PORTFOLIO_CSV}")
        sys.exit(1)
    print(f"  Portfolio CSV: {portfolio_path}")

    trades = load_trades()
    print(f"  Loaded {len(trades)} trades from portfolio.csv")

    inception = get_inception_date(trades)
    if not inception:
        print("  ERROR: No trades with valid entry dates")
        sys.exit(1)
    print(f"  Portfolio inception: {inception.strftime('%Y-%m-%d')}")

    existing = load_existing_curve()
    print(f"  Existing equity curve: {len(existing)} entries")

    # Get all unique tickers
    tickers = list(set(t["ticker"] for t in trades if t["ticker"]))
    end_date = datetime.now()

    # Download all price data
    prices = download_prices(tickers, inception - timedelta(days=5), end_date)
    if not prices:
        print("  ERROR: Failed to download prices")
        sys.exit(1)

    # Generate snapshots for each trading day
    trading_days = pd.bdate_range(inception, end_date)
    print(f"  Generating snapshots for {len(trading_days)} trading days...")

    all_snapshots = {}

    for day in trading_days:
        date_str = day.strftime("%Y-%m-%d")

        # Reuse existing entry only if it has valid QQQ data
        if date_str in existing:
            qqq_val = float(existing[date_str].get("qqq_value") or 0)
            if qqq_val > 0:
                all_snapshots[date_str] = existing[date_str]
                continue
            # else: recalculate — stale entry from before QQQ benchmark was added

        snapshot = calculate_nav_for_date(trades, prices, day.to_pydatetime(), inception)
        all_snapshots[date_str] = snapshot

    # Sort by date and write
    sorted_dates = sorted(all_snapshots.keys())
    fieldnames = [
        "date", "nav", "cash", "invested", "total_deployed", "open_count",
        "total_return_pct", "spy_value", "spy_return_pct", "alpha_pct",
        "qqq_value", "qqq_return_pct", "alpha_vs_qqq_pct",
    ]

    # Ensure output directory exists
    EQUITY_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(EQUITY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date_str in sorted_dates:
            writer.writerow(all_snapshots[date_str])

    print(f"  Written {len(sorted_dates)} entries to {EQUITY_CSV}")
    print(f"  Date range: {sorted_dates[0]} to {sorted_dates[-1]}")
    print("  Done!")


if __name__ == "__main__":
    main()
