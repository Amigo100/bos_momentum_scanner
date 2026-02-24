#!/usr/bin/env python3
"""
DAILY TIMEFRAME SCANNER — Technical BoS Signals on Daily Bars
==============================================================

Lightweight scanner that runs Monday-Friday after market close.
Identifies BoS buy signals on daily bars using the SAME indicator
functions as the weekly scanner (imported from scanner.scanner).

Differences from weekly scanner:
  - HMA / BoS computed on daily bars (no weekly resample)
  - NO thematic analysis, NO gatekeeper, NO due diligence
  - Max 5 new signals per day (ranked by Banker score)
  - Separate portfolio: portfolio/output/daily_portfolio.csv
  - Sell signals trigger notifications via distribution.notifications

Usage:
    python -m core.daily_scanner                # Full daily scan
    python -m core.daily_scanner --dry-run      # Show signals without writing
    python -m core.daily_scanner --top 100      # Limit universe to top 100 by beta
"""

import csv
import json
import logging
import os
import tempfile
import time
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS — reuse indicator functions from weekly scanner
# ═══════════════════════════════════════════════════════════════════════════════

from scanner.scanner import (
    calculate_beta,
    load_tickers,
)
# Legacy indicators preserved for daily scanner (weekly uses sterling_indicators)
from scanner.legacy_indicators import (
    calculate_banker,
    calculate_hma,
    find_pivots,
)
from config import (
    BETA_THRESHOLD,
    TRAILING_STOP_PCT,
    HMA_PERIOD,
    DAILY_SIGNAL_MAX,
    DAILY_DEDUP_LOOKBACK_DAYS,
    DAILY_DOWNLOAD_PERIOD,
    DAILY_MIN_BARS,
    DAILY_PORTFOLIO_FILE,
    DAILY_SIGNALS_FILE,
    PORTFOLIO_FILE,
    DAILY_PORTFOLIO_BACKUP_DIR,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS (imported from config.output_paths via config)
# ═══════════════════════════════════════════════════════════════════════════════

# DAILY_PORTFOLIO_FILE, DAILY_SIGNALS_FILE, PORTFOLIO_FILE, DAILY_PORTFOLIO_BACKUP_DIR
# are all imported from config above.

WEEKLY_PORTFOLIO_FILE = PORTFOLIO_FILE  # Alias for clarity in this module
DAILY_BACKUP_DIR = DAILY_PORTFOLIO_BACKUP_DIR  # Alias for clarity in this module

# Ensure output directories exist
DAILY_PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
DAILY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MAX_DAILY_BACKUPS = 30


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DailySignal:
    """A single daily buy/sell signal."""
    ticker: str
    price: float = 0.0
    beta: float = 0.0
    banker_score: float = 0.0
    sector: str = ""
    industry: str = ""


@dataclass
class DailyTrade:
    """One row in daily_portfolio.csv."""
    ticker: str
    entry_date: str = ""
    entry_price: float = 0.0
    highest_close: float = 0.0
    stop_pct: float = 20.0
    theme: str = ""
    timeframe: str = "daily"
    status: str = "OPEN"
    exit_date: str = ""
    exit_price: float = 0.0
    exit_reason: str = ""

    CSV_FIELDS = [
        "ticker", "entry_date", "entry_price", "highest_close", "stop_pct",
        "theme", "timeframe", "status", "exit_date", "exit_price", "exit_reason",
    ]

    def to_csv_row(self) -> Dict:
        return {
            "ticker": self.ticker,
            "entry_date": self.entry_date,
            "entry_price": f"{self.entry_price:.2f}" if self.entry_price else "",
            "highest_close": f"{self.highest_close:.2f}" if self.highest_close else "",
            "stop_pct": f"{self.stop_pct:.2f}",
            "theme": self.theme,
            "timeframe": self.timeframe,
            "status": self.status,
            "exit_date": self.exit_date,
            "exit_price": f"{self.exit_price:.2f}" if self.exit_price else "",
            "exit_reason": self.exit_reason,
        }

    @classmethod
    def from_csv_row(cls, row: Dict) -> "DailyTrade":
        return cls(
            ticker=row.get("ticker", "").upper(),
            entry_date=row.get("entry_date", ""),
            entry_price=float(row.get("entry_price") or 0),
            highest_close=float(row.get("highest_close") or 0),
            stop_pct=float(row.get("stop_pct") or 20.0),
            theme=row.get("theme", ""),
            timeframe=row.get("timeframe", "daily"),
            status=row.get("status", "OPEN"),
            exit_date=row.get("exit_date", ""),
            exit_price=float(row.get("exit_price") or 0),
            exit_reason=row.get("exit_reason", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY BoS — same maths, no weekly resample
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_bos_daily(
    df: pd.DataFrame,
    hma_length: int = HMA_PERIOD,
    pivot_k: int = 1,
) -> Tuple[bool, bool, dict]:
    """Calculate Break of Structure on *daily* bars.

    Uses the same HMA + pivot logic as the weekly scanner but operates
    directly on daily OHLCV data without resampling to weekly.

    Returns:
        (bos_up, bos_down, debug_info)
    """
    debug_info: dict = {}

    try:
        if len(df) < DAILY_MIN_BARS:
            return False, False, debug_info

        # HL2 on daily bars (not weekly)
        hl2 = (df["High"] + df["Low"]) / 2

        # HMA of HL2 — imported from scanner.scanner
        hma = calculate_hma(hl2, hma_length)

        # Pivots on HMA — imported from scanner.scanner
        pivot_highs, pivot_lows = find_pivots(hma, pivot_k)

        # Build step lines (carry forward last pivot value)
        upper = pd.Series(index=df.index, dtype=float)
        lower = pd.Series(index=df.index, dtype=float)

        last_ph = np.nan
        last_pl = np.nan

        for i in range(len(df)):
            if not pd.isna(pivot_highs.iloc[i]):
                last_ph = pivot_highs.iloc[i]
            if not pd.isna(pivot_lows.iloc[i]):
                last_pl = pivot_lows.iloc[i]
            upper.iloc[i] = last_ph
            lower.iloc[i] = last_pl

        if len(df) < 2:
            return False, False, debug_info

        current_upper = upper.iloc[-1]
        prev_upper = upper.iloc[-2]
        current_lower = lower.iloc[-1]
        prev_lower = lower.iloc[-2]

        bos_up = (
            not pd.isna(current_lower)
            and not pd.isna(prev_lower)
            and current_lower != prev_lower
        )
        bos_down = (
            not pd.isna(current_upper)
            and not pd.isna(prev_upper)
            and current_upper != prev_upper
        )

        debug_info = {
            "daily_bars": len(df),
            "hma_current": float(hma.iloc[-1]) if not pd.isna(hma.iloc[-1]) else None,
            "upper_step": float(current_upper) if not pd.isna(current_upper) else None,
            "lower_step": float(current_lower) if not pd.isna(current_lower) else None,
            "prev_upper": float(prev_upper) if not pd.isna(prev_upper) else None,
            "prev_lower": float(prev_lower) if not pd.isna(prev_lower) else None,
            "current_close": float(df["Close"].iloc[-1]),
            "last_date": str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1]),
            "signal_type": "HMA_PIVOT_DAILY",
        }

        return bos_up, bos_down, debug_info

    except Exception as exc:
        debug_info["error"] = str(exc)
        return False, False, debug_info


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO I/O — atomic CSV reads/writes
# ═══════════════════════════════════════════════════════════════════════════════

def load_daily_portfolio(path: Optional[Path] = None) -> List[DailyTrade]:
    """Load daily_portfolio.csv, returning list of DailyTrade objects."""
    path = path or DAILY_PORTFOLIO_FILE
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [DailyTrade.from_csv_row(row) for row in csv.DictReader(f)]
    except Exception as exc:
        logger.error("Error loading daily portfolio: %s", exc)
        return []


def save_daily_portfolio(
    trades: List[DailyTrade],
    path: Optional[Path] = None,
) -> None:
    """Atomic write of daily_portfolio.csv (tempfile + os.replace)."""
    path = path or DAILY_PORTFOLIO_FILE

    # Backup current file
    if path.exists():
        backup = DAILY_BACKUP_DIR / f"daily_portfolio_{datetime.now():%Y%m%d_%H%M%S}.csv"
        import shutil
        shutil.copy(path, backup)
        # Prune old backups
        backups = sorted(DAILY_BACKUP_DIR.glob("daily_portfolio_*.csv"))
        for old in backups[:-MAX_DAILY_BACKUPS]:
            old.unlink()

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=str(path.parent), suffix=".csv",
            delete=False, newline="", encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(f, fieldnames=DailyTrade.CSV_FIELDS)
            writer.writeheader()
            for trade in trades:
                writer.writerow(trade.to_csv_row())
            tmp = f.name
        os.replace(tmp, str(path))
    except Exception:
        # Clean up temp file on failure
        if "tmp" in locals() and Path(tmp).exists():
            Path(tmp).unlink()
        raise


def load_weekly_open_symbols(path: Optional[Path] = None) -> set:
    """Return set of tickers with OPEN weekly positions."""
    path = path or WEEKLY_PORTFOLIO_FILE
    if not path.exists():
        return set()
    symbols = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "OPEN":
                    symbols.add(row.get("ticker", "").upper())
    except Exception:
        pass
    return symbols


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def _recently_signalled(
    ticker: str,
    daily_trades: List[DailyTrade],
    lookback_days: int = DAILY_DEDUP_LOOKBACK_DAYS,
) -> bool:
    """Check if ticker was signalled within the last N days with no
    intervening sell (STOPPED/CLOSED).

    If the most recent trade for this ticker within the lookback window
    is still OPEN, it's considered a duplicate.  If it was STOPPED or
    CLOSED, the dedup resets and the ticker is eligible again.
    """
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # Gather trades for this ticker within window, newest first
    relevant = sorted(
        [t for t in daily_trades if t.ticker == ticker and t.entry_date >= cutoff],
        key=lambda t: t.entry_date,
        reverse=True,
    )

    if not relevant:
        return False

    # Most recent trade: if still OPEN → duplicate; if exited → eligible
    return relevant[0].status == "OPEN"


def deduplicate(
    tickers: List[str],
    daily_trades: List[DailyTrade],
    weekly_open: set,
    lookback_days: int = DAILY_DEDUP_LOOKBACK_DAYS,
) -> List[str]:
    """Remove tickers already in weekly portfolio or recently signalled daily."""
    result = []
    for t in tickers:
        if t in weekly_open:
            continue
        if _recently_signalled(t, daily_trades, lookback_days):
            continue
        result.append(t)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def download_daily_data(
    tickers: List[str],
    period: str = DAILY_DOWNLOAD_PERIOD,
) -> Dict[str, pd.DataFrame]:
    """Download daily OHLCV data for tickers via yfinance.

    Returns dict of {ticker: DataFrame} with enough history for
    HMA(21) + pivot lookback.
    """
    import yfinance as yf
    import io
    import contextlib

    frames: Dict[str, pd.DataFrame] = {}
    chunk_size = 50
    chunks = [tickers[i : i + chunk_size] for i in range(0, len(tickers), chunk_size)]

    for ci, chunk in enumerate(chunks):
        pct = (ci + 1) / len(chunks) * 100
        print(f"\r  Downloading daily bars: {pct:3.0f}% ({ci+1}/{len(chunks)} chunks)", end="", flush=True)

        try:
            with contextlib.redirect_stderr(io.StringIO()):
                data = yf.download(chunk, period=period, progress=False, threads=True, group_by="ticker")

            if data.empty:
                continue

            for sym in chunk:
                try:
                    if len(chunk) == 1:
                        df = data.copy()
                    else:
                        if sym not in data.columns.get_level_values(0):
                            continue
                        df = data[sym].copy()

                    if "Close" not in df.columns:
                        continue
                    df = df.dropna(subset=["Close"])
                    if len(df) < DAILY_MIN_BARS:
                        continue

                    frames[sym] = df
                except Exception:
                    continue
        except Exception:
            continue

        time.sleep(0.3)

    print(f"\r  \u2713 Daily data for {len(frames)} stocks" + " " * 30)
    return frames


def download_spy_returns(period: str = DAILY_DOWNLOAD_PERIOD) -> pd.Series:
    """Download SPY daily returns for beta calculation."""
    import yfinance as yf

    try:
        spy = yf.download("SPY", period=period, progress=False)
        if spy.empty:
            return pd.Series(dtype=float)
        close = spy["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.pct_change().dropna()
    except Exception as exc:
        logger.error("Failed to download SPY: %s", exc)
        return pd.Series(dtype=float)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTOR / INDUSTRY LOOKUP
# ═══════════════════════════════════════════════════════════════════════════════

def _get_ticker_info(ticker: str) -> Tuple[str, str]:
    """Fetch sector and industry for a ticker from yfinance (best-effort)."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get("sector", ""), info.get("industry", "")
    except Exception:
        return "", ""


# ═══════════════════════════════════════════════════════════════════════════════
# SELL SIGNAL CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def check_daily_sell_signals(
    trades: List[DailyTrade],
    frames: Dict[str, pd.DataFrame],
) -> List[DailyTrade]:
    """Check open daily positions for sell signals.

    First exit strategy — whichever fires first closes the position:
      1. Update highest_close if today's close is higher.
      2. Check BoS on daily bars — if bearish pivot → EXIT immediately.
      3. Check trailing stop — if close < highest_close * (1 - stop_pct/100) → EXIT immediately.
      4. If both fire on same bar, exit once with combined reason.

    Returns list of trades that triggered a sell signal.
    """
    sell_signals: List[DailyTrade] = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for trade in trades:
        if trade.status != "OPEN":
            continue
        if trade.ticker not in frames:
            continue

        df = frames[trade.ticker]
        current_close = float(df["Close"].iloc[-1])

        # Update highest_close
        if current_close > trade.highest_close:
            trade.highest_close = current_close

        # Check both exit conditions (first exit — whichever fires first)
        exit_reasons = []

        # Check BoS on daily bars
        _, bos_down, _ = calculate_bos_daily(df)
        if bos_down:
            exit_reasons.append(f"Daily BoS Down at ${current_close:.2f}")

        # Check trailing stop
        stop_level = trade.highest_close * (1 - trade.stop_pct / 100)
        if current_close <= stop_level:
            exit_reasons.append(f"Trailing stop ({trade.stop_pct:.0f}%) at ${current_close:.2f}")

        if exit_reasons:
            trade.status = "STOPPED"
            trade.exit_date = today_str
            trade.exit_price = current_close
            trade.exit_reason = " + ".join(exit_reasons)
            sell_signals.append(trade)
            logger.info(
                "%s: EXIT at $%.2f — %s",
                trade.ticker, current_close, trade.exit_reason,
            )

    return sell_signals


def _send_daily_sell_notifications(sell_signals: List[DailyTrade]) -> None:
    """Fire sell-signal notifications for daily positions."""
    try:
        from utils.notifications import send_sell_notification
    except ImportError:
        logger.warning("utils.notifications not available — skipping sell notifications")
        return

    for trade in sell_signals:
        pnl_pct = 0.0
        if trade.entry_price > 0:
            pnl_pct = ((trade.exit_price / trade.entry_price) - 1) * 100

        if trade.exit_reason and "bos down" in trade.exit_reason.lower():
            signal_type = "BEARISH PIVOT"
        elif "trailing stop" in (trade.exit_reason or "").lower():
            signal_type = "TRAILING STOP"
        else:
            signal_type = "EXIT"

        try:
            send_sell_notification(
                ticker=trade.ticker,
                signal_type=signal_type,
                entry_price=trade.entry_price,
                current_price=trade.exit_price,
                highest_close=trade.highest_close,
                stop_level=trade.highest_close * (1 - trade.stop_pct / 100),
                pnl_pct=pnl_pct,
                theme=trade.theme,
                timeframe="daily",
                entry_date=trade.entry_date,
            )
        except Exception as exc:
            logger.error("Failed to send sell notification for %s: %s", trade.ticker, exc)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_daily_signals(
    signals: List[DailySignal],
    path: Optional[Path] = None,
    sell_signals: Optional[List] = None,
) -> Path:
    """Write daily_signals.json.

    Uses ``buy_signals`` / ``sell_signals`` keys so that
    ``tweet_generator.generate_daily_content()`` can read them directly.
    """
    path = path or DAILY_SIGNALS_FILE
    output = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "timeframe": "daily",
        "buy_signals": [
            {
                "ticker": s.ticker,
                "symbol": s.ticker,
                "price": s.price,
                "beta": s.beta,
                "banker_score": s.banker_score,
                "sector": s.sector,
                "industry": s.industry,
                "theme": s.sector or s.industry or "",
            }
            for s in signals
        ],
        "sell_signals": [
            {
                "symbol": t.ticker,
                "ticker": t.ticker,
                "price": t.exit_price,
                "reason": t.exit_reason or "Trailing stop",
                "entry_price": t.entry_price,
                "highest_close": t.highest_close,
                "pnl_pct": round(((t.exit_price / t.entry_price) - 1) * 100, 2) if t.entry_price > 0 else 0.0,
                "theme": t.theme,
                "entry_date": t.entry_date,
            }
            for t in (sell_signals or [])
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCAN
# ═══════════════════════════════════════════════════════════════════════════════

def run_daily_scan(
    *,
    dry_run: bool = False,
    top_n: Optional[int] = None,
    daily_portfolio_path: Optional[Path] = None,
    weekly_portfolio_path: Optional[Path] = None,
    signals_output_path: Optional[Path] = None,
) -> List[DailySignal]:
    """Execute the full daily scan pipeline.

    Steps:
        1. Load tickers
        2. Download SPY benchmark + daily bars
        3. Compute Beta, Banker, HMA BoS on daily bars
        4. Filter: Beta >= 1.5, Banker >= 55, BoS bullish
        5. Deduplicate vs weekly portfolio + recent daily signals
        6. Rank by Banker descending, take top DAILY_SIGNAL_MAX
        7. Output daily_signals.json
        8. Add new signals to daily_portfolio.csv
        9. Check existing daily positions for sell signals
       10. Send sell-signal notifications

    Returns:
        List of DailySignal objects for new buy signals.
    """
    dp_path = daily_portfolio_path or DAILY_PORTFOLIO_FILE
    wp_path = weekly_portfolio_path or WEEKLY_PORTFOLIO_FILE

    print()
    print("=" * 70)
    print("  DAILY BoS SCANNER")
    print(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # ── 1. Load tickers ──────────────────────────────────────────────────────
    tickers = load_tickers()
    if not tickers:
        print("  No tickers loaded — aborting")
        return []
    print(f"\n  Tickers loaded: {len(tickers)}")

    if top_n:
        tickers = tickers[:top_n]
        print(f"  Limited to top {top_n}")

    # ── 2. Download data ─────────────────────────────────────────────────────
    print("\n  Downloading SPY benchmark...")
    spy_returns = download_spy_returns()
    if spy_returns.empty:
        print("  \u2717 Failed to download SPY — aborting")
        return []

    print(f"  SPY: {len(spy_returns)} daily returns")

    frames = download_daily_data(tickers)
    if not frames:
        print("  \u2717 No data downloaded — aborting")
        return []

    # ── 3. Compute indicators ────────────────────────────────────────────────
    print("\n  Computing indicators on daily bars...")

    candidates: List[Tuple[str, float, float, float]] = []  # (ticker, price, beta, banker)

    for sym, df in frames.items():
        try:
            price = float(df["Close"].iloc[-1])
            returns = df["Close"].pct_change().dropna()
            beta = calculate_beta(returns, spy_returns)

            if beta < BETA_THRESHOLD:
                continue

            banker, banker_prev = calculate_banker(df)
            if banker <= banker_prev:  # Not rising — skip
                continue

            bos_up, _, _ = calculate_bos_daily(df)
            if not bos_up:
                continue

            candidates.append((sym, price, beta, banker))
        except Exception:
            continue

    print(f"  Technical gate passed: {len(candidates)}")

    if not candidates:
        print("  No signals today.")
        # Still check existing positions for sell signals
        daily_trades = load_daily_portfolio(dp_path)
        if daily_trades:
            sell_signals = check_daily_sell_signals(
                [t for t in daily_trades if t.status == "OPEN"], frames
            )
            if sell_signals and not dry_run:
                save_daily_portfolio(daily_trades, dp_path)
                _send_daily_sell_notifications(sell_signals)
                print(f"  Sell signals: {len(sell_signals)}")
        return []

    # ── 4. Deduplicate ───────────────────────────────────────────────────────
    daily_trades = load_daily_portfolio(dp_path)
    weekly_open = load_weekly_open_symbols(wp_path)

    candidate_tickers = [c[0] for c in candidates]
    eligible = set(deduplicate(candidate_tickers, daily_trades, weekly_open))

    candidates = [c for c in candidates if c[0] in eligible]
    print(f"  After dedup: {len(candidates)}")

    # ── 5. Rank and limit ────────────────────────────────────────────────────
    candidates.sort(key=lambda c: c[3], reverse=True)  # by banker desc
    top = candidates[:DAILY_SIGNAL_MAX]

    # ── 6. Build signals ─────────────────────────────────────────────────────
    signals: List[DailySignal] = []
    for sym, price, beta, banker in top:
        sector, industry = _get_ticker_info(sym)
        signals.append(DailySignal(
            ticker=sym,
            price=round(price, 2),
            beta=round(beta, 2),
            banker_score=round(banker, 1),
            sector=sector,
            industry=industry,
        ))

    print(f"\n  NEW DAILY SIGNALS ({len(signals)}):")
    for sig in signals:
        print(f"    {sig.ticker:<6} ${sig.price:>8.2f}  Beta:{sig.beta:.2f}  Banker:{sig.banker_score:.0f}  {sig.sector}")

    if dry_run:
        print("\n  [DRY RUN] No files written.")
        return signals

    # ── 7. Add new signals to daily portfolio ────────────────────────────────
    today_str = datetime.now().strftime("%Y-%m-%d")
    for sig in signals:
        daily_trades.append(DailyTrade(
            ticker=sig.ticker,
            entry_date=today_str,
            entry_price=sig.price,
            highest_close=sig.price,
            stop_pct=TRAILING_STOP_PCT,
            theme=sig.sector or sig.industry,
            timeframe="daily",
            status="OPEN",
        ))

    # ── 8. Check existing positions for sell signals ─────────────────────────
    open_trades = [t for t in daily_trades if t.status == "OPEN" and t.entry_date != today_str]
    sell_signals = check_daily_sell_signals(open_trades, frames)

    # ── 9. Output signals JSON (after sell check so both are included) ───────
    out = save_daily_signals(signals, signals_output_path, sell_signals=sell_signals)
    print(f"\n  Signals: {out}")

    # ── 10. Save portfolio + send notifications ──────────────────────────────
    save_daily_portfolio(daily_trades, dp_path)
    print(f"  Portfolio: {dp_path}")

    if sell_signals:
        _send_daily_sell_notifications(sell_signals)
        print(f"  Sell signals: {len(sell_signals)}")

    print(f"\n  Done. {len(signals)} new signal(s), {len(sell_signals)} sell signal(s).")
    print("=" * 70)

    return signals


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Daily BoS Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Print signals only, don't write files")
    parser.add_argument("--top", type=int, default=None, help="Limit universe to top N tickers")
    args = parser.parse_args()

    signals = run_daily_scan(dry_run=args.dry_run, top_n=args.top)
    return 0 if signals is not None else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
