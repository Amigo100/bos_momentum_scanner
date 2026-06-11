#!/usr/bin/env python3
"""
STERLING GRID MOMENTUM SCANNER — V10 (WEEKLY)
=============================================

ENTRY  : bare HMA(21) pivot low on a COMPLETED weekly bar. Fire wide; the
         LLM pipeline (Claude skills) does all selection. No gates, no tiers,
         no watchlist, no sizing — every published BUY is one full
         equal-weight model position (handled downstream, not here).
EXIT   : tiered_initial_35 ONLY, checked on every open position:
           gain < +50%  → hard floor at entry × (1 − 0.35)
           gain ≥ +50%  → trailing lock from peak close (+50%→25%,
                          +100%→20%, +200%→15%)
         Decided on the weekly close; act at next candle open.
         There is NO HMA-down exit. Peak close is DERIVED from price history
         since entry (never carried as mutable state).

IO CONTRACT (the scanner is a pure detector):
  reads  : scanner/complete_tickers.txt          (universe)
           sterling-run/portfolio.csv            (open positions, READ-ONLY;
             flexible headers: ticker/symbol, entry_date/date, entry_price/entry)
  writes : signals_technical.json  (+ dated archive copy with --archive)
           analysis_log.csv        (append-only run log)
  never  : writes the portfolio. Position changes belong to the weekly-close
           script / operator after the Claude.ai review.

DETERMINISM:
  --asof YYYY-MM-DD truncates all price data to that date and anchors the
  download window (start = asof − 2y, end = asof + 1d), so any historical
  week can be replayed bit-for-bit. The final weekly bar is dropped if
  partial (see sterling_indicators.resample_to_weekly), so a Thursday run
  reports the LAST COMPLETED week and says so, instead of silently emitting
  signals that can flip by Friday.

REMOVED in V10: portfolio.manager integration, quality tiers T1–T6 and all
TIER_ALLOC sizing, watchlist signals, legacy re-anchor / pre-2026 machinery,
ExD and HMA-down exits, RSI death-cross conditioning, beta + SPY benchmark
step, buy_signal_v6 diagnostics.

Usage:
    python -m scanner.scanner                       # weekly run (asof = today)
    python -m scanner.scanner --asof 2026-06-05     # replay a historical week
    python -m scanner.scanner --tickers CRSP,TEM    # ad-hoc check, any names
    python -m scanner.scanner --no-enrich --no-email
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import contextlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

# ── Sterling Grid V10 indicators (single source of all thresholds) ──────────
try:
    from scanner.sterling_indicators import (
        MIN_WEEKLY_BARS,
        resample_to_weekly,
        generate_entry_signal,
        check_tiered_initial_35,
        compute_peak_close,
    )
except ImportError:  # running as loose files
    from sterling_indicators import (
        MIN_WEEKLY_BARS,
        resample_to_weekly,
        generate_entry_signal,
        check_tiered_initial_35,
        compute_peak_close,
    )

# ── Enrichment (optional; per-ticker yfinance fundamentals on signals only) ─
try:
    from scanner.enrichment import enrich_stock
except ImportError:
    try:
        from enrichment import enrich_stock
    except ImportError:
        enrich_stock = None

# ── Output paths (repo config if present, local fallback otherwise) ─────────
try:
    from config.output_paths import (
        ensure_output_structure,
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
    PORTFOLIO_FILE = Path(__file__).resolve().parent.parent / "sterling-run" / "portfolio.csv"

    def ensure_output_structure():
        _FALLBACK_OUTPUT.mkdir(parents=True, exist_ok=True)
        return _FALLBACK_OUTPUT, _FALLBACK_OUTPUT

BASE_DIR = Path(__file__).resolve().parent.parent
TICKERS_FILE = BASE_DIR / "scanner" / "complete_tickers.txt"

DOCTRINE_VERSION = "V10"
ENTRY_CRITERIA = "V10: bare HMA(21) pivot low on a completed weekly bar; LLM selects"
EXIT_CRITERIA = (
    "V10: tiered_initial_35 only — -35% floor below +50% gain; trailing lock "
    "from peak (+50%→25%, +100%→20%, +200%→15%). No HMA-down. "
    "Decided on weekly close; act next open."
)


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Stock:
    symbol: str
    price: float = 0.0                 # last completed weekly close
    week_date: str = ""                # label of that completed week (Friday)
    # entry signal + informational context for the LLM layer
    buy_signal: bool = False
    hma_value: float = 0.0
    hma_pivot_low: bool = False
    hma_pivot_high: bool = False       # informational only — NOT an exit
    hma_slope_rising: bool = False
    rsi14: float = 0.0
    macd_cross_up: bool = False
    macd_histogram: float = 0.0
    uc: float = 0.0
    uc_rising: bool = False
    atr_rank: float = 0.0
    atr_squeeze: bool = False
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    enrichment: dict = field(default_factory=dict)


@dataclass
class Position:
    ticker: str
    entry_date: str
    entry_price: float


@dataclass
class ExitFlag:
    symbol: str
    price: float                       # last completed weekly close
    reason: str
    entry_price: float
    peak_close: float
    gain_pct: float
    lock_level: float


@dataclass
class DataQuality:
    failed_downloads: List[str] = field(default_factory=list)
    partial_week_dropped: List[str] = field(default_factory=list)   # "SYM@YYYY-MM-DD"
    short_history: List[str] = field(default_factory=list)
    indicator_errors: List[str] = field(default_factory=list)
    held_not_found: List[str] = field(default_factory=list)
    held_no_completed_bar: List[str] = field(default_factory=list)
    enrich_errors: List[str] = field(default_factory=list)


@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    pivot_signals: int = 0
    open_positions: int = 0
    exit_flags: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# UNIVERSE + POSITIONS (read-only)
# ═══════════════════════════════════════════════════════════════════════════

def load_tickers(path: Path = TICKERS_FILE) -> List[str]:
    """Universe from complete_tickers.txt — one or more symbols per line."""
    if not path.exists():
        print(f"  ✗ Universe file not found: {path}")
        return []
    tickers = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for part in line.replace(",", " ").replace("\t", " ").split():
                t = part.strip().strip("\"'").upper()
                if t in {"TICKER", "SYMBOL", "NAME", "COMPANY", ""}:
                    continue
                if 1 <= len(t) <= 6 and any(c.isalpha() for c in t) \
                        and all(c.isalnum() or c in "-." for c in t):
                    tickers.add(t)
    return sorted(tickers)


_POS_TICKER_KEYS = ("ticker", "symbol", "sym")
_POS_DATE_KEYS = ("entry_date", "date", "entered", "entry date")
_POS_PRICE_KEYS = ("entry_price", "entry", "price", "entry price", "cost")


def load_positions(path: Path = PORTFOLIO_FILE) -> List[Position]:
    """Open positions from portfolio.csv (READ-ONLY). Tolerant headers.
    Rows with an exit/closed marker column set are skipped if present."""
    if not Path(path).exists():
        return []
    positions: List[Position] = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        # skip leading comment lines (sterling-run/portfolio.csv documents itself with '#' lines)
        reader = csv.DictReader(ln for ln in f if not ln.lstrip().startswith("#"))
        if not reader.fieldnames:
            return []
        cols = {c.lower().strip(): c for c in reader.fieldnames}

        def pick(keys):
            for k in keys:
                if k in cols:
                    return cols[k]
            return None

        tcol, dcol, pcol = pick(_POS_TICKER_KEYS), pick(_POS_DATE_KEYS), pick(_POS_PRICE_KEYS)
        if not (tcol and pcol):
            print(f"  ⚠ portfolio.csv: couldn't find ticker/entry_price columns in {reader.fieldnames}")
            return []
        closed_col = next((cols[k] for k in ("exit_date", "closed", "status") if k in cols), None)

        for row in reader:
            if closed_col and str(row.get(closed_col, "")).strip() not in ("", "open", "OPEN", "None"):
                continue
            try:
                t = row[tcol].strip().upper()
                praw = str(row.get(pcol, "") or "").replace("$", "").replace(",", "").strip()
                p = float(praw) if praw else 0.0
                d = str(row.get(dcol, "") or "").strip() if dcol else ""
                if t and (p > 0 or d):
                    positions.append(Position(ticker=t, entry_date=d, entry_price=p))
            except Exception:
                continue
    return positions


# ═══════════════════════════════════════════════════════════════════════════
# DOWNLOAD + INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

def _yf_window(asof: pd.Timestamp) -> Tuple[str, str]:
    start = (asof - timedelta(days=730)).strftime("%Y-%m-%d")
    end = (asof + timedelta(days=1)).strftime("%Y-%m-%d")
    return start, end


def _process_daily(symbol: str, df: pd.DataFrame, asof: pd.Timestamp,
                   weekly_store: Dict[str, pd.DataFrame], dq: DataQuality) -> Optional[Stock]:
    """Daily OHLCV → completed-weekly indicators → Stock. None if unusable."""
    if df is None or df.empty or "Close" not in df.columns:
        return None
    df = df.dropna(subset=["Close"])
    if len(df) < 60:
        dq.short_history.append(symbol)
        return None

    weekly, dropped = resample_to_weekly(df, asof=asof)
    if dropped:
        dq.partial_week_dropped.append(f"{symbol}@{dropped}")
    if len(weekly) < MIN_WEEKLY_BARS:
        dq.short_history.append(symbol)
        return None
    weekly_store[symbol] = weekly

    try:
        sig = generate_entry_signal(weekly)
        cur = sig.iloc[-1]
    except Exception as ex:
        dq.indicator_errors.append(f"{symbol}: {type(ex).__name__}")
        return None

    s = Stock(symbol=symbol)
    s.price = round(float(weekly["close"].iloc[-1]), 4)
    s.week_date = str(weekly.index[-1].date())
    s.buy_signal = bool(cur["buy_signal"])
    s.hma_value = round(float(cur["hma"]), 4) if pd.notna(cur["hma"]) else 0.0
    s.hma_pivot_low = bool(cur["hma_pivot_low"])
    s.hma_pivot_high = bool(cur["hma_pivot_high"])
    s.hma_slope_rising = bool(cur["hma_slope_rising"])
    s.rsi14 = round(float(cur["rsi14"]), 1) if pd.notna(cur["rsi14"]) else 0.0
    s.macd_cross_up = bool(cur["macd_cross_up"])
    s.macd_histogram = round(float(cur["macd_histogram"]), 4) if pd.notna(cur["macd_histogram"]) else 0.0
    s.uc = round(float(cur["uc"]), 2) if pd.notna(cur["uc"]) else 0.0
    s.uc_rising = bool(cur["uc_rising"])
    s.atr_rank = round(float(cur["atr_rank"]), 1) if pd.notna(cur["atr_rank"]) else 0.0
    s.atr_squeeze = bool(cur["atr_squeeze"])
    if len(weekly) >= 5:
        s.momentum_4w = round((float(weekly["close"].iloc[-1]) / float(weekly["close"].iloc[-5]) - 1) * 100, 1)
    if len(df) >= 20:
        s.return_20d = round((float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-20]) - 1) * 100, 1)
    return s


def download_and_process(tickers: List[str], asof: pd.Timestamp,
                         dq: DataQuality) -> Tuple[Dict[str, Stock], Dict[str, pd.DataFrame]]:
    """Bulk price download (auto_adjust pinned) → per-symbol Stock + weekly store."""
    stocks: Dict[str, Stock] = {}
    weekly_store: Dict[str, pd.DataFrame] = {}
    start, end = _yf_window(asof)
    chunks = [tickers[i:i + 50] for i in range(0, len(tickers), 50)]

    for i, chunk in enumerate(chunks):
        print(f"\r  Downloading: {(i + 1) / len(chunks) * 100:3.0f}% ({i + 1}/{len(chunks)} chunks)",
              end="", flush=True)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                # auto_adjust=True PINNED: adjusted closes are split-safe — a 2:1 split
                # on raw closes looks like -50% and would false-trigger the floor.
                # Consequence: portfolio.csv entry prices must be on the same adjusted
                # basis (refresh entry_price after any split in a held name).
                data = yf.download(chunk, start=start, end=end, progress=False,
                                   threads=True, group_by="ticker", auto_adjust=True)
            if data is None or data.empty:
                dq.failed_downloads.extend(chunk)
                continue
            for symbol in chunk:
                try:
                    if len(chunk) == 1:
                        df = data.copy()
                    else:
                        if symbol not in data.columns.get_level_values(0):
                            dq.failed_downloads.append(symbol)
                            continue
                        df = data[symbol].copy()
                    st = _process_daily(symbol, df, asof, weekly_store, dq)
                    if st is not None:
                        stocks[symbol] = st
                except Exception as ex:
                    dq.indicator_errors.append(f"{symbol}: {type(ex).__name__}")
        except Exception:
            dq.failed_downloads.extend(chunk)
        time.sleep(0.3)

    print(f"\r  ✓ Data for {len(stocks)} stocks" + " " * 30)
    return stocks, weekly_store


def _fetch_single(symbol: str, asof: pd.Timestamp, dq: DataQuality,
                  weekly_store: Dict[str, pd.DataFrame]) -> Optional[Stock]:
    """Individual fetch for a held symbol that wasn't in the universe."""
    try:
        start, end = _yf_window(asof)
        with contextlib.redirect_stderr(io.StringIO()):
            df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        return _process_daily(symbol, df, asof, weekly_store, dq)
    except Exception:
        dq.failed_downloads.append(symbol)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# EXIT CHECK — tiered_initial_35 on every open position (peak DERIVED)
# ═══════════════════════════════════════════════════════════════════════════

def check_exits(positions: List[Position], weekly_store: Dict[str, pd.DataFrame],
                dq: DataQuality) -> List[ExitFlag]:
    flags: List[ExitFlag] = []
    for pos in positions:
        weekly = weekly_store.get(pos.ticker)
        if weekly is None:
            dq.held_not_found.append(pos.ticker)
            continue
        current = float(weekly["close"].iloc[-1])
        # Derived-entry fallback: if the CSV has a date but no/zero price, take the
        # entry-week close from the SAME adjusted series (keeps basis consistent).
        if pos.entry_price <= 0 and pos.entry_date:
            try:
                ts = pd.Timestamp(pos.entry_date).normalize()
                ref = weekly.loc[weekly.index >= ts, "close"]
                if not ref.empty:
                    pos.entry_price = float(ref.iloc[0])
            except Exception:
                pass
        if pos.entry_price <= 0:
            dq.held_not_found.append(f"{pos.ticker} (no usable entry price)")
            continue
        peak = compute_peak_close(weekly, pos.entry_date) if pos.entry_date else None
        if peak is None:
            # no completed weekly bar since entry (or unparseable date):
            # fall back to max(entry context) so the floor still protects
            if pos.entry_date:
                dq.held_no_completed_bar.append(pos.ticker)
            peak = max(current, pos.entry_price)
        peak = max(peak, current)

        result = check_tiered_initial_35(pos.entry_price, current, peak)
        if result.get("triggered", False):
            flags.append(ExitFlag(
                symbol=pos.ticker,
                price=round(current, 4),
                reason=result.get("active_tier", "tiered_initial_35"),
                entry_price=pos.entry_price,
                peak_close=round(peak, 4),
                gain_pct=result.get("gain_pct", 0.0),
                lock_level=result.get("lock_level", 0.0),
            ))
            print(f"    ✗ {pos.ticker}: EXIT FLAG at ${current:.2f} — {result.get('active_tier')}")
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════

def run_scan(asof: pd.Timestamp, top_n: int = 0, tickers_override: Optional[List[str]] = None,
             no_enrich: bool = False, portfolio_path: Path = PORTFOLIO_FILE,
             ) -> Tuple[List[Stock], List[ExitFlag], ScanStats, DataQuality]:
    dq = DataQuality()
    stats = ScanStats()

    # STEP 1 — universe
    print("\n" + "─" * 70 + "\n  STEP 1: Universe\n" + "─" * 70)
    tickers = tickers_override or load_tickers()
    stats.tickers_loaded = len(tickers)
    print(f"  ✓ {len(tickers)} tickers (asof {asof.date()})")
    if not tickers:
        return [], [], stats, dq

    # STEP 2 — positions (read-only)
    positions = load_positions(portfolio_path)
    stats.open_positions = len(positions)
    held = {p.ticker for p in positions}
    if positions:
        print(f"  ✓ {len(positions)} open position(s) from {portfolio_path}")

    # STEP 3 — download + indicators (completed weeks only)
    print("\n" + "─" * 70 + "\n  STEP 3: Download & Indicators (completed weekly bars)\n" + "─" * 70)
    universe = sorted(set(tickers) | held)
    stocks, weekly_store = download_and_process(universe, asof, dq)
    stats.data_downloaded = len(stocks)
    for sym in held - set(weekly_store):
        st = _fetch_single(sym, asof, dq, weekly_store)
        if st is not None:
            stocks[sym] = st

    # STEP 4 — entry signals
    signals = [s for s in stocks.values() if s.buy_signal]
    if top_n and len(signals) > top_n:
        signals = sorted(signals, key=lambda x: -x.uc)[:top_n]
    stats.pivot_signals = len(signals)
    week_label = signals[0].week_date if signals else (
        next(iter(stocks.values())).week_date if stocks else "n/a")
    print(f"\n  📊 ENTRY SIGNALS (week ending {week_label}): {len(signals)}")
    for s in sorted(signals, key=lambda x: -x.uc):
        held_flag = " [HELD]" if s.symbol in held else ""
        print(f"    {s.symbol:<6} ${s.price:>9.2f}  UC={s.uc:4.1f}  RSI={s.rsi14:3.0f}  "
              f"MACD={'✓' if s.macd_cross_up else '✗'}  ATR={s.atr_rank:3.0f}%"
              f"{'[SQ]' if s.atr_squeeze else '    '}{held_flag}")
    if dq.partial_week_dropped:
        print(f"  ⚠ Partial final week dropped on {len(dq.partial_week_dropped)} symbol(s) — "
              f"signals reflect the last COMPLETED week.")

    # STEP 5 — enrichment (signals only, optional)
    if signals and not no_enrich and enrich_stock is not None:
        print("\n" + "─" * 70 + "\n  STEP 5: Enriching signals (yfinance fundamentals)\n" + "─" * 70)
        for i, s in enumerate(signals, 1):
            print(f"\r  Enriching: {i}/{len(signals)} ({s.symbol})    ", end="", flush=True)
            try:
                s.enrichment = enrich_stock(s.symbol)
            except Exception as ex:
                s.enrichment = {"data_warnings": [f"enrich_error: {type(ex).__name__}"]}
                dq.enrich_errors.append(s.symbol)
            time.sleep(0.3)
        print(f"\r  ✓ Enriched {len(signals)} signal(s)" + " " * 24)

    # STEP 6 — exit check (tiered_initial_35, every open position)
    print("\n" + "─" * 70 + "\n  STEP 6: Exit check — tiered_initial_35 (no HMA-down)\n" + "─" * 70)
    exit_flags = check_exits(positions, weekly_store, dq)
    stats.exit_flags = len(exit_flags)
    if not exit_flags:
        print("  ✓ No exit flags")

    return signals, exit_flags, stats, dq


# ═══════════════════════════════════════════════════════════════════════════
# SAVE + REPORT + EMAIL
# ═══════════════════════════════════════════════════════════════════════════

def save_results(signals: List[Stock], exit_flags: List[ExitFlag], stats: ScanStats,
                 dq: DataQuality, asof: pd.Timestamp, archive: bool = False) -> Path:
    ensure_output_structure()

    def _sig(s: Stock) -> dict:
        d = asdict(s)
        d["banker"] = s.uc           # legacy compat key for content systems
        return d

    payload = {
        "scan_meta": {
            "doctrine_version": DOCTRINE_VERSION,
            "asof": str(asof.date()),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_criteria": ENTRY_CRITERIA,
            "exit_criteria": EXIT_CRITERIA,
        },
        "stats": asdict(stats),
        "data_quality": asdict(dq),
        "buy_signals": [_sig(s) for s in signals],
        "exit_flags": [asdict(e) for e in exit_flags],
        # retained keys for output-schema stability (the tweet-system consumers were retired 2026-06)
        "historical_winners": [], "big_wins": [], "home_runs": [],
    }

    SIGNALS_TECH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS_TECH_FILE, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n  ✓ Saved: {SIGNALS_TECH_FILE}")

    if archive:
        arch = SCANNER_OUTPUT / "archive"
        arch.mkdir(parents=True, exist_ok=True)
        arch_file = arch / f"signals_technical_{asof.date()}.json"
        arch_file.write_text(json.dumps(payload, indent=2, default=str))
        print(f"  ✓ Archived: {arch_file}")

    ANALYSIS_LOG.parent.mkdir(parents=True, exist_ok=True)
    new_log = not ANALYSIS_LOG.exists()
    with open(ANALYSIS_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["asof", "generated_at", "doctrine", "tickers", "downloaded",
                        "signals", "exit_flags", "failed", "partial_dropped"])
        w.writerow([asof.date(), payload["scan_meta"]["generated_at"], DOCTRINE_VERSION,
                    stats.tickers_loaded, stats.data_downloaded, stats.pivot_signals,
                    stats.exit_flags, len(dq.failed_downloads), len(dq.partial_week_dropped)])
    return SIGNALS_TECH_FILE


def build_report(signals: List[Stock], exit_flags: List[ExitFlag],
                 stats: ScanStats, dq: DataQuality, asof: pd.Timestamp) -> str:
    L = [f"STERLING GRID {DOCTRINE_VERSION} — WEEKLY SCAN (asof {asof.date()})", "=" * 60,
         f"Universe {stats.tickers_loaded} | data {stats.data_downloaded} | "
         f"signals {stats.pivot_signals} | exit flags {stats.exit_flags}", ""]
    if signals:
        L.append("ENTRY SIGNALS (bare HMA pivot — selection happens in the pipeline):")
        for s in sorted(signals, key=lambda x: -x.uc):
            e = s.enrichment or {}
            cap = e.get("market_cap")
            cap_s = f"  cap ${cap/1e6:,.0f}M" if isinstance(cap, (int, float)) and cap else ""
            L.append(f"  {s.symbol:<6} ${s.price:>9.2f}  UC={s.uc:4.1f} RSI={s.rsi14:3.0f} "
                     f"MACD={'Y' if s.macd_cross_up else 'n'} ATRr={s.atr_rank:3.0f}{cap_s}")
    else:
        L.append("No entry signals this week.")
    if exit_flags:
        L += ["", "EXIT FLAGS (tiered_initial_35 — act next open):"]
        for x in exit_flags:
            L.append(f"  {x.symbol:<6} ${x.price:>9.2f}  {x.gain_pct:+.1f}% vs entry "
                     f"${x.entry_price:.2f} — {x.reason}")
    issues = sum(len(v) for v in asdict(dq).values())
    if issues:
        L += ["", f"DATA QUALITY: {len(dq.failed_downloads)} failed, "
              f"{len(dq.partial_week_dropped)} partial-week dropped, "
              f"{len(dq.indicator_errors)} indicator errors, "
              f"{len(dq.held_not_found)} held-not-found"]
    return "\n".join(L)


def send_notification(report: str, stats: ScanStats):
    try:
        from utils.email_notifier import send_email, load_config
        if not load_config():
            print("  ⚠ Email not configured")
            return
        parts = []
        if stats.pivot_signals:
            parts.append(f"{stats.pivot_signals} Entry")
        if stats.exit_flags:
            parts.append(f"{stats.exit_flags} Exit")
        subject = f"BoS Scanner: {', '.join(parts)}" if parts else "BoS Scanner: No Signals This Week"
        print("  ✓ Email sent" if send_email(subject, report) else "  ✗ Email send failed")
    except ImportError:
        print("  ⚠ email_notifier not found — skipping email")
    except Exception as e:
        print(f"  ⚠ Email error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description=f"Sterling Grid {DOCTRINE_VERSION} — weekly technical scanner")
    ap.add_argument("--asof", type=str, default=None,
                    help="Scan as of this date (YYYY-MM-DD). Default: today. Historical dates replay that week.")
    ap.add_argument("--top", type=int, default=0, help="Keep only top N signals by UC")
    ap.add_argument("--tickers", type=str, default=None, help="Comma-separated ad-hoc universe override")
    ap.add_argument("--portfolio", type=str, default=None, help="Path to portfolio.csv (read-only)")
    ap.add_argument("--no-enrich", action="store_true", help="Skip yfinance fundamentals enrichment")
    ap.add_argument("--no-email", action="store_true", help="Skip email notification")
    ap.add_argument("--archive", action="store_true", help="Also write dated archive copy of the JSON")
    args = ap.parse_args()

    asof = pd.Timestamp(args.asof).normalize() if args.asof else pd.Timestamp.now().normalize()
    tick_override = [t.strip().upper() for t in args.tickers.split(",")] if args.tickers else None
    pf_path = Path(args.portfolio) if args.portfolio else PORTFOLIO_FILE

    print("\n╔" + "═" * 68 + "╗")
    print("║" + f"STERLING GRID {DOCTRINE_VERSION} — WEEKLY TECHNICAL SCANNER".center(68) + "║")
    print("║" + f"asof {asof.date()}".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print(f"\n  ENTRY : {ENTRY_CRITERIA}\n  EXIT  : {EXIT_CRITERIA}")
    print("  Signals only change on the weekly (Friday) close; mid-week runs report the last completed week.")

    t0 = time.time()
    signals, exit_flags, stats, dq = run_scan(
        asof=asof, top_n=args.top, tickers_override=tick_override,
        no_enrich=args.no_enrich, portfolio_path=pf_path)
    save_results(signals, exit_flags, stats, dq, asof, archive=args.archive)
    report = build_report(signals, exit_flags, stats, dq, asof)
    print("\n" + report)
    if not args.no_email:
        send_notification(report, stats)
    print(f"\n  Done in {(time.time() - t0)/60:.1f}m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
