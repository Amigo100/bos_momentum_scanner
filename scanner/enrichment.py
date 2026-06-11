#!/usr/bin/env python3
"""
scanner/enrichment.py — yfinance fundamentals + profile enrichment.

Run ONLY on flagged technical signals (the ~30–60 that fire), never the full
universe: fundamentals require per-ticker yf.Ticker calls (slow + flaky), unlike
the bulk price download. Called from scanner.run_scan() after STEP 5.

Adds, per signal, what the technical scan doesn't have:
  - profile: company, sector, industry, business_summary, market_cap
  - fundamentals: revenue + YoY growth, R&D YoY growth, gross margin, cash, OCF,
    runway_months, dilution_yoy
  - liquidity hard-cut + runway/dilution risk flags

YFINANCE PROFILE CAVEAT (handled explicitly):
yfinance sector/industry are often generic, stale, or missing. So we (a) pull the
business_summary and pass it downstream — the chat workflow should classify the
theme from the *description + fundamentals*, NOT the sector bucket — (b) tag
profile_confidence + profile_warnings so nothing trusts a stale label silently,
and (c) prefer dated financial-statement figures over the often-stale .info.

Public API:
    enrich_stock(symbol, price_history=None) -> dict
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import pandas as pd

CONFIG = {
    "min_addv_usd": 750_000,        # below this avg daily $ volume => liquidity_fail (hard cut)
    "low_runway_months": 12,
    "high_dilution_yoy": 0.25,
    "price_period": "2y",
    "marketcap_mismatch_tol": 0.20,
    "summary_max_chars": 800,       # keep signals_technical.json from bloating
    "generic_sectors": {"Technology", "Industrials", "Financial Services",
                        "Consumer Cyclical", "Communication Services", "Healthcare",
                        "Consumer Defensive", "Basic Materials"},
}

# ── pure compute (unit-tested) ───────────────────────────────────────────────

def pct_change(new, old):
    if new is None or old in (None, 0):
        return None
    return new / old - 1.0

def compute_runway_months(cash_st, ocf_quarter):
    if cash_st is None or ocf_quarter is None or ocf_quarter >= 0:
        return None
    monthly_burn = abs(ocf_quarter) / 3.0
    return round(cash_st / monthly_burn, 1) if monthly_burn else None

def _round(x, n=4):
    return round(x, n) if isinstance(x, (int, float)) else x

def compute_price_features(closes, vols):
    if not closes:
        return {}
    last = closes[-1]
    window = closes[-252:] if len(closes) >= 252 else closes
    high_52w = max(window)
    n = min(21, len(closes))
    addv = sum(c * v for c, v in zip(closes[-n:], vols[-n:])) / n if n else None
    return {
        "price": round(last, 4),
        "pct_from_52w_high": round(pct_change(last, high_52w), 4) if high_52w else None,
        "addv_usd": round(addv, 0) if addv is not None else None,
    }

def derive_flags(addv, runway_months, dilution_yoy, cfg=CONFIG):
    hard, soft = [], []
    if addv is not None and addv < cfg["min_addv_usd"]:
        hard.append("liquidity_fail")
    if runway_months is not None and runway_months < cfg["low_runway_months"]:
        soft.append(f"low_runway_{runway_months}m")
    if dilution_yoy is not None and dilution_yoy > cfg["high_dilution_yoy"]:
        soft.append(f"high_dilution_{round(dilution_yoy*100)}pct")
    return hard, soft

# ── dataframe helpers (yfinance: line-items as rows, periods as columns) ──────

def _newest_first(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    try:
        return df.reindex(sorted(df.columns, reverse=True), axis=1)
    except Exception:
        return df

def _row(df, col_idx, *labels):
    """Value at period column for the first matching line-item label. Multiple
    candidate labels guard against yfinance renaming fields across versions."""
    if df is None or df.shape[1] <= col_idx:
        return None
    for lab in labels:
        if lab in df.index:
            try:
                v = df.loc[lab].iloc[col_idx]
                return float(v) if pd.notna(v) else None
            except Exception:
                continue
    return None

# ── assembly + fetch ──────────────────────────────────────────────────────────

@dataclass
class Enrichment:
    company: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    business_summary: Optional[str] = None
    profile_confidence: str = "ok"          # "low" when sector/summary missing or generic
    market_cap: Optional[float] = None
    revenue_q: Optional[float] = None
    revenue_yoy_growth: Optional[float] = None
    rd_yoy_growth: Optional[float] = None
    gross_margin: Optional[float] = None
    cash_st: Optional[float] = None
    ocf_quarter: Optional[float] = None
    runway_months: Optional[float] = None
    dilution_yoy: Optional[float] = None
    addv_usd: Optional[float] = None
    pct_from_52w_high: Optional[float] = None
    hard_disqualifiers: list = field(default_factory=list)
    risk_flags: list = field(default_factory=list)
    profile_warnings: list = field(default_factory=list)
    data_warnings: list = field(default_factory=list)


def _assemble(info, inc, bs, cf, closes, vols, cfg=CONFIG) -> Enrichment:
    e = Enrichment()
    info = info or {}
    inc, bs, cf = _newest_first(inc), _newest_first(bs), _newest_first(cf)

    # profile (yfinance's weak spot — handle explicitly)
    e.company = info.get("longName") or info.get("shortName")
    e.sector, e.industry = info.get("sector"), info.get("industry")
    summary = info.get("longBusinessSummary")
    if summary:
        e.business_summary = summary[:cfg["summary_max_chars"]].rstrip()
    else:
        e.profile_warnings.append("no_business_summary")
    if not e.sector:
        e.profile_warnings.append("sector_missing")
    elif e.sector in cfg["generic_sectors"]:
        e.profile_warnings.append("sector_generic")
    if not e.industry:
        e.profile_warnings.append("industry_missing")
    e.profile_confidence = "low" if (not e.business_summary or not e.sector) else "ok"

    # fundamentals (prefer dated statements over stale .info)
    e.revenue_q = _row(inc, 0, "Total Revenue", "Revenue", "Operating Revenue")
    rev_yr = _row(inc, 4, "Total Revenue", "Revenue", "Operating Revenue")
    e.revenue_yoy_growth = _round(pct_change(e.revenue_q, rev_yr))
    rd_now = _row(inc, 0, "Research And Development", "Research & Development")
    rd_yr = _row(inc, 4, "Research And Development", "Research & Development")
    e.rd_yoy_growth = _round(pct_change(rd_now, rd_yr))
    gp = _row(inc, 0, "Gross Profit")
    if gp is not None and e.revenue_q:
        e.gross_margin = _round(gp / e.revenue_q)

    e.cash_st = _row(bs, 0, "Cash Cash Equivalents And Short Term Investments",
                     "Cash And Cash Equivalents", "Cash Financial")
    e.ocf_quarter = _row(cf, 0, "Operating Cash Flow",
                         "Cash Flow From Continuing Operating Activities")
    e.runway_months = compute_runway_months(e.cash_st, e.ocf_quarter)

    shares_now = (_row(bs, 0, "Ordinary Shares Number", "Share Issued")
                  or info.get("sharesOutstanding"))
    shares_yr = _row(bs, 4, "Ordinary Shares Number", "Share Issued")
    e.dilution_yoy = _round(pct_change(shares_now, shares_yr))

    # price-derived liquidity / extension (reuses history if provided)
    feats = compute_price_features(closes, vols)
    e.addv_usd = feats.get("addv_usd")
    e.pct_from_52w_high = feats.get("pct_from_52w_high")

    # market cap: prefer .info, cross-check vs price x shares
    price = feats.get("price")
    mc_info = info.get("marketCap")
    mc_calc = (price * shares_now) if (price and shares_now) else None
    e.market_cap = mc_info or mc_calc
    if mc_info and mc_calc and abs(pct_change(mc_info, mc_calc) or 0) > cfg["marketcap_mismatch_tol"]:
        e.profile_warnings.append("marketcap_mismatch")

    e.hard_disqualifiers, e.risk_flags = derive_flags(e.addv_usd, e.runway_months, e.dilution_yoy, cfg)
    return e


def enrich_stock(symbol: str, price_history: Optional[pd.DataFrame] = None, cfg=CONFIG) -> dict:
    """Fetch yfinance fundamentals + profile for one flagged signal -> dict.

    price_history (optional): a yfinance .history()/.download() df for this symbol;
    pass it to avoid re-downloading price. If omitted, history is fetched here.
    """
    import yfinance as yf
    try:
        t = yf.Ticker(symbol)
        try:
            info = t.info or {}
        except Exception:
            info = {}            # .info is the flaky part — proceed; profile_warnings will fire
        inc = getattr(t, "quarterly_income_stmt", None)
        if inc is None or (isinstance(inc, pd.DataFrame) and inc.empty):
            inc = getattr(t, "quarterly_financials", None)
        bs = getattr(t, "quarterly_balance_sheet", None)
        cf = getattr(t, "quarterly_cashflow", None)

        if price_history is None or getattr(price_history, "empty", True):
            price_history = t.history(period=cfg["price_period"], interval="1d")

        closes, vols = [], []
        if price_history is not None and not price_history.empty:
            cc = "Close" if "Close" in price_history.columns else (
                 "Adj Close" if "Adj Close" in price_history.columns else None)
            if cc:
                sub = price_history.dropna(subset=[cc])
                closes = [float(x) for x in sub[cc].tolist()]
                vols = [float(x) for x in sub["Volume"].tolist()] if "Volume" in sub.columns else [0.0]*len(closes)

        return asdict(_assemble(info, inc, bs, cf, closes, vols, cfg))
    except Exception as ex:
        e = Enrichment()
        e.data_warnings.append(f"enrich_error: {type(ex).__name__}: {ex}")
        return asdict(e)


# backward-compatible alias
enrich = enrich_stock


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", required=True)
    a = ap.parse_args()
    print(json.dumps([enrich_stock(t.strip()) for t in a.tickers.split(",") if t.strip()],
                     indent=2, default=str))
