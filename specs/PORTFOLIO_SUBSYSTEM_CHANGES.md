# Portfolio Subsystem — Required Changes Specification
## Sterling Signals Architecture Optimisation

**Date:** 2026-02-25
**Scope:** portfolio/manager.py, portfolio/backup_cleanup.py, daily_scanner.py integration, portfolio snapshot system, daily price refresh, portfolio dashboard
**Status:** Pre-implementation specification
**Depends on:** SCANNER_SUBSYSTEM_CHANGES.md (for sterling_indicators integration), SUBSTACK_SUBSYSTEM_CHANGES.md (daily pipeline consumes portfolio snapshot)
**Consumed by:** TWEET_SUBSYSTEM_CHANGES.md (live prices, portfolio movers), SUBSTACK_SUBSYSTEM_CHANGES.md (daily context builder, notes generator)

---

## TABLE OF CONTENTS

1. [System Assessment](#1-system-assessment)
2. [Architecture Overview — Target State](#2-architecture-overview)
3. [Daily Price Refresh Pipeline](#3-daily-price-refresh)
4. [Portfolio JSON Snapshot](#4-portfolio-json-snapshot)
5. [Daily Equity Curve](#5-daily-equity-curve)
6. [Portfolio Dashboard Generation](#6-portfolio-dashboard)
7. [Sharing Portfolio via Substack](#7-sharing-via-substack)
8. [Sharing Portfolio via Tweets](#8-sharing-via-tweets)
9. [Daily Portfolio System — Simplification](#9-daily-portfolio-simplification)
10. [manager.py Changes](#10-managerpy-changes)
11. [backup_cleanup.py — No Changes](#11-backup-cleanup)
12. [Google Sheets Export — Improvements](#12-google-sheets-improvements)
13. [Portfolio Viewer Artifact](#13-portfolio-viewer)
14. [Configuration Changes](#14-configuration-changes)
15. [Cross-System Data Contracts](#15-data-contracts)
16. [GitHub Actions Integration](#16-github-actions)
17. [Module Inventory](#17-module-inventory)
18. [Implementation Order](#18-implementation-order)
19. [Testing Checklist](#19-testing-checklist)
20. [Summary Statistics](#20-summary-statistics)

---

## 1. SYSTEM ASSESSMENT

### 1.1 What's Working Well (Keep As-Is)

The portfolio system is the best-architected subsystem in Sterling Signals. Unlike the scanner (needs refactoring), Substack (needs restructuring), and tweets (needs rebalancing), the portfolio system's core logic is sound.

**Keep unchanged:**
- **Trade dataclass** — 16 stored fields + 7 calculated, clean separation
- **Atomic CSV writes** — tempfile + os.replace() pattern throughout
- **Compounding NAV algorithm** — £5,000/position with cash pool recycling, replay-based
- **Tiered profit lock** — current-return-based tiers with first-exit logic
- **Backup system** — automatic per-save + weekly dedup via backup_cleanup.py
- **Canonical API functions** — load_portfolio(), fetch_current_prices(), get_spy_ytd_return() are the right abstraction
- **Read-only consumer pattern** — 10+ modules read, only scanner pipeline and CLI write
- **EquityTracker** — NAV calculation with SPY/QQQ benchmarks is solid

### 1.2 What Needs Improvement

**Problem 1: Prices only update on Friday scan or manual CLI.**
Between Friday scans, portfolio.csv prices go stale. The live tweet system calls fetch_current_prices() independently for each run (5x/day weekdays), but these prices don't persist back to portfolio.csv. The daily Substack content builder (from Substack spec) needs fresh prices but has no reliable source. Every consumer that needs current prices does its own yfinance call — wasteful and inconsistent.

**Problem 2: No structured portfolio snapshot for downstream consumers.**
10+ modules read portfolio.csv via ad-hoc CSV parsing. Each extracts what it needs differently. There's no single "here's the portfolio state right now" JSON that all consumers can reference. The Substack daily_context_builder, tweet live_tweet_generator, and portfolio_visual all do redundant work loading and processing the same data.

**Problem 3: Equity curve only updates on Friday scans.**
equity_curve.csv gets a new row only when `update_equity_curve()` is called during the scanner pipeline. This means the equity curve has weekly resolution at best. For a compounding portfolio, missing 4 days of NAV tracking per week loses significant information — especially during volatile weeks.

**Problem 4: No way to view portfolio outside Google Sheets or terminal.**
portfolio_visual.py generates an HTML dashboard, but only during the Friday scan → Saturday newsletter pipeline. There's no persistent, always-current portfolio view. Subscribers can see the portfolio in the Saturday newsletter, but it's a week old by Wednesday. You can't quickly check "how's the portfolio doing?" without running a CLI command or opening Google Sheets.

**Problem 5: Daily portfolio system is orphaned.**
daily_portfolio.csv and daily_scanner.py use legacy indicators (BoS daily, flat 20% stop) instead of Sterling Grid. The DailyTrade dataclass duplicates Trade with fewer fields. The daily scan deduplicates against weekly but doesn't share any other state. It's a parallel system that doesn't integrate cleanly.

**Problem 6: Consumer modules use inconsistent price data.**
The live tweet system fetches current prices independently. The Substack content generator reads stale prices from portfolio.csv. The portfolio visual uses whatever prices were current at Friday scan time. At any given moment, different parts of the system may report different P&L for the same position.

### 1.3 Root Cause

All six problems stem from one architectural gap: **there's no daily portfolio refresh step in the automated pipeline.** The scanner pipeline runs Friday only. Between Fridays, the portfolio data is either stale (CSV) or independently fetched (each consumer does its own yfinance call).

The fix is straightforward: add a **daily portfolio refresh** to the daily_content.yml pipeline (from Substack spec) that updates prices, refreshes the equity curve, and writes a structured JSON snapshot that all consumers can reference.

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 Target State — Daily Portfolio Flow

```
FRIDAY 21:30 UTC — friday_scan.yml (scanner pipeline)
├── scanner.py runs full scan
│   ├── add_trade_from_stock() → new OPEN trades
│   ├── check_sell_signals() → exits (ExD + profit lock)
│   └── update_prices() → refresh prices + highest_close
├── portfolio.csv updated with entries/exits/prices
├── equity_curve.csv updated
├── portfolio_google_sheets.csv exported
└── Commit + push

DAILY 07:00 ET — daily_content.yml (Substack pipeline, MODIFIED)
├── Step 1: Fetch live prices for all open positions
├── Step 2: Update portfolio.csv prices + highest_close  ← NEW
├── Step 3: Update equity_curve.csv with today's NAV     ← NEW
├── Step 4: Generate portfolio_snapshot.json              ← NEW
├── Step 5: Run market_analyzer.py → market_analysis.md
├── Step 6: Run daily_context_builder.py (reads snapshot)
├── Step 7: Run daily_notes_generator.py (reads snapshot)
├── Step 8: Send email notification
└── Commit + push

5x WEEKDAY — live_tweet.yml (tweet pipeline)
├── Context gatherer reads portfolio_snapshot.json        ← NEW (instead of CSV)
├── Tweet generator reads portfolio_snapshot.json         ← NEW
└── All price data is consistent (from morning refresh)
```

### 2.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Daily price refresh location | **daily_content.yml, step 2** | Already runs daily at 07:00, before all consumers need data |
| Price persistence | **Write back to portfolio.csv** | Source of truth stays in one place; consumers don't diverge |
| Structured snapshot | **portfolio_snapshot.json** | JSON with pre-computed stats; consumers read one file instead of parsing CSV + computing |
| Equity curve frequency | **Daily** (weekdays) | Captures intraday NAV changes, especially important during volatile weeks |
| Daily portfolio system | **Simplify, don't delete** | Keep daily_portfolio.csv for its own signals but don't try to merge with weekly |
| Portfolio dashboard | **Generate daily as part of pipeline** | Always-current HTML artifact; embed in Saturday newsletter + available standalone |
| Google Sheets export | **Keep + improve** | Add auto-import via Apps Script webhook (optional enhancement) |

---

## 3. DAILY PRICE REFRESH PIPELINE

### 3.1 New Function: refresh_daily_prices()

**File:** `portfolio/manager.py` (new function, ~60 lines)

This is the core new function. Called by daily_content.yml before any Substack or tweet content generation.

```python
def refresh_daily_prices() -> Dict:
    """Daily price refresh for all open positions.
    
    Called by daily_content.yml at 07:00 ET. Updates:
    1. portfolio.csv — current_price, highest_close for all OPEN positions
    2. equity_curve.csv — new NAV snapshot for today
    3. portfolio_snapshot.json — structured snapshot for downstream consumers
    4. portfolio_google_sheets.csv — refreshed export
    
    Returns:
        Dict with refresh summary (positions updated, NAV, movers, etc.)
    """
    pm = PortfolioManager()
    
    # Step 1: Fetch live prices
    open_tickers = list(pm.get_open_symbols())
    if not open_tickers:
        return {"status": "no_open_positions"}
    
    prices = fetch_current_prices(open_tickers)
    
    # Step 2: Update portfolio.csv (prices + highest_close)
    pm.update_prices()  # Uses yfinance internally
    
    # Step 3: Update equity curve
    snapshot = pm.update_equity_curve()
    
    # Step 4: Generate portfolio snapshot JSON
    snapshot_data = generate_portfolio_snapshot(pm, snapshot, prices)
    
    # Step 5: Export Google Sheets
    pm.export_for_google_sheets()
    
    return snapshot_data
```

### 3.2 Integration with daily_content.yml

The daily content pipeline (from Substack spec) gains a new step at the beginning:

```yaml
# daily_content.yml — MODIFIED
steps:
  # Step 1: Portfolio refresh (NEW — before any content generation)
  - name: Refresh portfolio prices
    run: python -c "from portfolio.manager import refresh_daily_prices; refresh_daily_prices()"
    continue-on-error: true  # Content generation should proceed even if price fetch fails
  
  # Step 2: Market analysis (existing from Substack spec)
  - name: Run market analyzer
    run: python -m content.market_analyzer
  
  # Steps 3-7: Context builder, notes generator, email...
```

**Why continue-on-error:** If yfinance is down or rate-limited, the pipeline should still generate content using the last known prices (from portfolio.csv). Stale-but-present data is better than no data.

### 3.3 Price Staleness Awareness

Add a `prices_updated_at` timestamp to portfolio_snapshot.json so consumers can judge freshness:

```python
def _get_price_age_hours(portfolio_file: Path) -> float:
    """How many hours since portfolio.csv was last modified."""
    if not portfolio_file.exists():
        return 999.0
    mtime = datetime.fromtimestamp(portfolio_file.stat().st_mtime)
    return (datetime.now() - mtime).total_seconds() / 3600
```

Consumers can check this and warn or fallback:
- Tweet system: if prices >6h old, skip RECEIPT tweets (stale price → inaccurate P&L)
- Substack notes: always use whatever's available (stale is better than missing)
- Portfolio dashboard: show "Prices as of [timestamp]" badge

---

## 4. PORTFOLIO JSON SNAPSHOT

### 4.1 Why a JSON Snapshot

Currently, every consumer module parses portfolio.csv independently and computes its own derived fields. This creates:
- **Redundant work:** 10 modules each calling `load_portfolio()` + computing P&L
- **Inconsistent numbers:** Different modules may compute pnl_pct slightly differently (rounding, price source)
- **Missing context:** CSV has no pre-computed stats (win rate, NAV, alpha) — each consumer that needs them builds its own

A daily JSON snapshot provides a single, pre-computed source of truth.

### 4.2 portfolio_snapshot.json Schema

```json
{
  "generated_at": "2026-02-25T12:00:00Z",
  "prices_updated_at": "2026-02-25T12:00:00Z",
  
  "summary": {
    "open_positions": 6,
    "closed_trades": 14,
    "total_trades": 20,
    "win_rate": 71.4,
    "avg_winner_pct": 38.2,
    "avg_loser_pct": -12.5,
    "unrealized_pnl_pct": 22.4
  },
  
  "equity": {
    "nav": 37500.00,
    "cash": 7500.00,
    "invested": 30000.00,
    "total_deployed": 35000.00,
    "total_return_pct": 7.14,
    "spy_return_pct": 4.2,
    "alpha_pct": 2.94,
    "qqq_return_pct": 3.1,
    "alpha_vs_qqq_pct": 4.04,
    "max_drawdown_pct": -5.2,
    "inception_date": "2024-10-01",
    "currency": "£"
  },
  
  "open_positions": [
    {
      "ticker": "RCAT",
      "entry_date": "2025-12-29",
      "entry_price": 8.50,
      "current_price": 13.25,
      "highest_close": 13.25,
      "pnl_pct": 55.9,
      "pnl_usd": 475.00,
      "days_held": 58,
      "theme": "Drone Technology",
      "conviction": 4,
      "stop_level": 0.0,
      "stop_active": false,
      "distance_to_stop_pct": 0.0,
      "stop_alert": false,
      "profit_lock_tier": null
    },
    {
      "ticker": "WCC",
      "entry_price": 281.00,
      "current_price": 322.40,
      "pnl_pct": 14.7,
      "stop_level": 0.0,
      "stop_active": false,
      "profit_lock_tier": null
    }
  ],
  
  "closed_trades": [
    {
      "ticker": "OKLO",
      "entry_date": "2024-11-15",
      "entry_price": 22.00,
      "exit_date": "2025-01-08",
      "exit_price": 28.50,
      "pnl_pct": 29.5,
      "days_held": 54,
      "theme": "Nuclear",
      "exit_reason": "Manual exit",
      "status": "CLOSED"
    }
  ],
  
  "winners": [
    {"ticker": "RCAT", "pnl_pct": 55.9, "theme": "Drone Technology"},
    {"ticker": "STRL", "pnl_pct": 44.8, "theme": "Infrastructure"},
    {"ticker": "MOD", "pnl_pct": 32.7, "theme": "Power Grid"}
  ],
  
  "big_wins": [
    {"ticker": "RCAT", "pnl_pct": 55.9, "entry_price": 8.50, "current_price": 13.25}
  ],
  
  "home_runs": [],
  
  "recent_exits": [
    {"ticker": "VNET", "pnl_pct": 32.7, "exit_date": "2026-02-14", "reason": "Profit lock (50% tier)"}
  ],
  
  "movers_today": [
    {"ticker": "RCAT", "move_pct": 3.2, "current_price": 13.25, "context": "Drone sector strength"}
  ],
  
  "themes": {
    "Drone Technology": {"positions": 1, "avg_pnl": 55.9, "tickers": ["RCAT"]},
    "Infrastructure": {"positions": 2, "avg_pnl": 29.8, "tickers": ["STRL", "WCC"]},
    "Power Grid": {"positions": 1, "avg_pnl": 32.7, "tickers": ["MOD"]}
  },
  
  "benchmarks": {
    "7d": {"portfolio": 2.1, "spy": 0.8, "alpha": 1.3},
    "30d": {"portfolio": 8.5, "spy": 3.2, "alpha": 5.3},
    "ytd": {"portfolio": 12.4, "spy": 6.1, "alpha": 6.3}
  }
}
```

### 4.3 generate_portfolio_snapshot() Function

**File:** `portfolio/manager.py` (new function, ~120 lines)

```python
def generate_portfolio_snapshot(
    pm: PortfolioManager,
    equity_snapshot: EquitySnapshot,
    live_prices: Dict[str, float],
) -> Dict:
    """Generate structured JSON snapshot of current portfolio state.
    
    This is the canonical portfolio state output. All downstream consumers
    (Substack, tweets, dashboard) should read this instead of parsing CSV.
    
    Args:
        pm: PortfolioManager with updated prices
        equity_snapshot: Latest equity snapshot
        live_prices: Dict of ticker → current price (from fetch_current_prices)
    
    Returns:
        Dict with full portfolio snapshot (also saved to portfolio_snapshot.json)
    """
    open_positions = pm.get_open_positions()
    closed_trades = pm.get_closed_trades()
    perf = pm.get_performance_summary()
    
    # Compute movers (positions with biggest intraday changes)
    movers = _compute_daily_movers(open_positions, live_prices)
    
    # Theme grouping
    themes = _group_by_theme(open_positions)
    
    # Winners / big wins / home runs
    winners = sorted(
        [t for t in open_positions if t.pnl_pct > 0],
        key=lambda t: t.pnl_pct, reverse=True
    )
    big_wins = [t for t in winners if t.pnl_pct >= 25.0]
    home_runs = [t for t in winners if t.pnl_pct >= 50.0]
    
    # Build snapshot dict
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prices_updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": { ... },
        "equity": { ... },
        "open_positions": [_trade_to_dict(t) for t in open_positions],
        "closed_trades": [_trade_to_dict(t) for t in closed_trades[-20:]],  # Last 20
        "winners": [{"ticker": t.ticker, "pnl_pct": t.pnl_pct, "theme": t.theme} for t in winners],
        "big_wins": [_trade_to_dict(t) for t in big_wins],
        "home_runs": [_trade_to_dict(t) for t in home_runs],
        "recent_exits": _get_recent_exits(closed_trades, days=14),
        "movers_today": movers,
        "themes": themes,
        "benchmarks": perf["periods"],
    }
    
    # Save to JSON (atomic write)
    _save_json_atomic(snapshot, PORTFOLIO_SNAPSHOT_FILE)
    
    return snapshot
```

### 4.4 Output Location

```python
PORTFOLIO_SNAPSHOT_FILE = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"
```

This file is committed to the repo alongside portfolio.csv by the daily_content.yml workflow.

### 4.5 Consumer Migration Path

Modules currently doing ad-hoc CSV parsing should migrate to reading portfolio_snapshot.json:

| Consumer | Current Approach | Target Approach |
|----------|-----------------|-----------------|
| Substack daily_context_builder | `load_portfolio()` + compute P&L | Read `portfolio_snapshot.json` |
| Substack daily_notes_generator | `load_portfolio()` + compute P&L | Read `portfolio_snapshot.json` |
| Tweet live_tweet_generator | `load_portfolio()` + fetch_current_prices() | Read `portfolio_snapshot.json` for base data, fetch_current_prices() only for intraday updates |
| Tweet live_context_gatherer | Parse portfolio.csv directly | Read `portfolio_snapshot.json` |
| portfolio_visual.py | PortfolioManager() + compute everything | Read `portfolio_snapshot.json` for data, focus on rendering |

**Migration is not required for Phase 1.** The snapshot is additive — existing consumers continue to work. Migration happens organically as each subsystem spec is implemented.

---

## 5. DAILY EQUITY CURVE

### 5.1 Current State: Weekly Resolution

equity_curve.csv gets a new row only during the Friday scan pipeline when `update_equity_curve()` is called. Between Fridays, the curve has no data points.

### 5.2 Target State: Daily Resolution (Weekdays)

The daily price refresh (Section 3) calls `pm.update_equity_curve()` every weekday morning. This produces 5 equity curve entries per week instead of 1.

**Benefits:**
- Accurate max drawdown calculation (currently misses intra-week drawdowns)
- Richer equity curve for newsletter dashboard SVG
- Daily alpha tracking (did we beat SPY today?)
- Better trend detection for content generation ("3rd straight day of alpha generation")

### 5.3 Implementation

No new code needed — `update_equity_curve()` already deduplicates by date (replaces same-date entries). Calling it daily just produces more data points. The only change is adding the call to `refresh_daily_prices()` (Section 3).

### 5.4 Weekend Handling

On weekends (Saturday 07:00 run), prices won't change from Friday close. The equity curve will get a Saturday entry with identical values to Friday — which is correct (NAV doesn't change when markets are closed). The dedup-by-date logic handles re-runs cleanly.

---

## 6. PORTFOLIO DASHBOARD GENERATION

### 6.1 Current State

`portfolio_visual.py` generates an HTML dashboard + equity curve SVG, but only during the Friday scan → Saturday newsletter pipeline. The dashboard shows data from Friday's scan — by Wednesday, it's 5 days stale.

### 6.2 Target State: Daily Dashboard

Generate a lightweight portfolio dashboard every morning as part of the daily pipeline. Two outputs:

**Output 1: portfolio_dashboard.html** — Full interactive dashboard (for Substack embedding and standalone viewing)
- Open positions table with live P&L, stop levels, theme grouping
- Equity curve chart (from daily equity_curve.csv)
- Performance vs SPY/QQQ
- Win rate, average winner/loser
- Theme allocation breakdown
- "Prices as of [timestamp]" badge

**Output 2: portfolio_summary.png** — Static image for tweet attachments
- Simplified portfolio card: total return, alpha, open positions count, top 3 winners
- Clean design suitable for X card preview
- Generated via matplotlib or HTML-to-image

### 6.3 Dashboard Generation — Where It Runs

**Option A (recommended): As part of daily_content.yml, after price refresh**

```yaml
# daily_content.yml — MODIFIED
steps:
  - name: Refresh portfolio prices
    run: python -c "from portfolio.manager import refresh_daily_prices; refresh_daily_prices()"
  
  - name: Generate portfolio dashboard  # NEW
    run: python -m substack.portfolio_visual --daily
    continue-on-error: true
```

The `--daily` flag tells portfolio_visual.py to generate a lightweight version (no full newsletter layout, just the dashboard). The existing Friday pipeline continues to generate the full newsletter-embedded version.

**Why portfolio_visual.py, not a new module:** The rendering logic already exists (HTML tables, SVG equity curve, theme grouping). Adding a `--daily` mode is simpler than duplicating the code.

### 6.4 Changes to portfolio_visual.py

Add a `--daily` CLI flag that:
1. Reads from portfolio_snapshot.json (instead of calling PortfolioManager directly)
2. Generates a standalone HTML dashboard (not newsletter-embedded)
3. Generates a summary PNG for tweet attachments
4. Saves to `substack/output/current/portfolio_dashboard.html` and `portfolio_summary.png`

```python
# portfolio_visual.py — new daily mode
def generate_daily_dashboard(snapshot_path: Path) -> Tuple[Path, Path]:
    """Generate daily portfolio dashboard from JSON snapshot.
    
    Returns: (html_path, png_path)
    """
    snapshot = json.loads(snapshot_path.read_text())
    
    html = _render_dashboard_html(snapshot)
    png = _render_summary_card(snapshot)
    
    html_path = SUBSTACK_CURRENT / "portfolio_dashboard.html"
    png_path = SUBSTACK_CURRENT / "portfolio_summary.png"
    
    html_path.write_text(html)
    # PNG generation via matplotlib
    _save_summary_card(png, png_path)
    
    return html_path, png_path
```

---

## 7. SHARING PORTFOLIO VIA SUBSTACK

### 7.1 Current Integration

The Saturday newsletter includes a portfolio dashboard section (generated by portfolio_visual.py). This is the primary way subscribers see the portfolio.

### 7.2 Enhanced Integration — Daily Context

The Substack daily_context_builder (from Substack spec) reads the portfolio snapshot to include:

**In daily notes (2-3/day):**
- PORTFOLIO_PULSE notes use live positions with current P&L
- Notes can reference "portfolio up X% this week" with accurate daily numbers

**In daily context doc (for chat sessions):**
- Full position list with current prices
- Theme allocation breakdown
- Recent winners/exits for content topics
- Equity curve stats for benchmark comparisons

**In long-form posts (3-4/week):**
- Tuesday Ticker Deep Dive can reference accurate P&L for the featured position
- Wednesday Theme Rotation can show all positions in the theme with current stats
- Thursday flex posts have accurate portfolio data for any format

### 7.3 Portfolio Milestones as Content Triggers

The Substack spec's event override system (Section 3.3 of SUBSTACK_SUBSYSTEM_CHANGES.md) checks for portfolio milestones:

```python
def check_event_overrides(portfolio_snapshot: dict) -> Optional[PostAssignment]:
    # +50% milestone
    for pos in portfolio_snapshot["open_positions"]:
        if pos["pnl_pct"] >= 50.0 and not _milestone_recently_covered(pos["ticker"], 50):
            return PostAssignment(category="MILESTONE", ticker=pos["ticker"], ...)
    
    # +100% milestone  
    for pos in portfolio_snapshot["open_positions"]:
        if pos["pnl_pct"] >= 100.0 and not _milestone_recently_covered(pos["ticker"], 100):
            return PostAssignment(category="MILESTONE", ticker=pos["ticker"], ...)
    
    # Recent exit with significant P&L
    for exit in portfolio_snapshot["recent_exits"]:
        if abs(exit["pnl_pct"]) >= 25 and not _exit_recently_covered(exit["ticker"]):
            return PostAssignment(category="EXIT_REVIEW", ticker=exit["ticker"], ...)
```

With daily price updates, these milestone detections are accurate to the morning — not a week delayed.

---

## 8. SHARING PORTFOLIO VIA TWEETS

### 8.1 Current Integration

The live tweet system reads portfolio.csv (stale prices) and calls fetch_current_prices() separately for live prices. RECEIPT tweets use these prices but the system has no awareness of portfolio-level stats (NAV, alpha, win rate).

### 8.2 Enhanced Integration — Portfolio-Aware Tweets

With the portfolio snapshot available, the tweet system gains:

**RECEIPT tweets with richer context:**
```
"$RCAT from $8.50 to $13.25. +55.9%.
Portfolio alpha: +2.9% vs S&P this week. The system works."
```

vs current:
```
"$RCAT from $8.50 to $13.25. +55.9%. Drone tech thesis playing out."
```

**Multi-RECEIPT thread tweets with portfolio stats:**
```
Tweet 1: "Portfolio update 📊
6 open positions. +22.4% unrealized.
Alpha vs S&P: +2.9% this week."

Tweet 2: "$RCAT +55.9%
$STRL +44.8%
$MOD +32.7%
$WCC +14.7%"

Tweet 3: "71% win rate across 20 trades.
1,800 stocks scanned → 8 survived. NFA."
```

**Portfolio summary card attachment:**
The daily-generated portfolio_summary.png can be attached to multi-RECEIPT or ENGAGEMENT tweets as a visual.

### 8.3 Tweet System Reads portfolio_snapshot.json

The tweet system's context gatherer (from tweet spec) adds portfolio stats to the Grok prompt context:

```python
# live_context_gatherer.py — enhanced portfolio context
def _build_portfolio_context() -> str:
    snapshot_path = PORTFOLIO_SNAPSHOT_FILE
    if not snapshot_path.exists():
        # Fallback: parse portfolio.csv directly
        return _build_portfolio_context_from_csv()
    
    snapshot = json.loads(snapshot_path.read_text())
    
    lines = ["Current portfolio positions:"]
    for pos in snapshot["open_positions"]:
        lines.append(
            f"${pos['ticker']}: entry ${pos['entry_price']:.2f}, "
            f"current ${pos['current_price']:.2f} (+{pos['pnl_pct']:.1f}%)"
        )
    
    # Add portfolio-level stats
    eq = snapshot["equity"]
    lines.append(f"\nPortfolio alpha vs S&P: {eq['alpha_pct']:+.1f}%")
    lines.append(f"NAV: {eq['currency']}{eq['nav']:,.0f}")
    lines.append(f"Win rate: {snapshot['summary']['win_rate']:.0f}%")
    
    return "\n".join(lines)
```

### 8.4 portfolio_summary.png for Tweet Charts

When the decision function selects a multi-RECEIPT or portfolio-level ENGAGEMENT tweet, the chart_recommended flag is set to True and the `chart_path` points to the daily portfolio_summary.png:

```python
# In decide_tweet_type(), P2 multi-receipt branch:
if len(winners) >= 3 and not over_budget("RECEIPT"):
    return {
        "type": "RECEIPT",
        "multi_receipt": True,
        "chart_path": str(PORTFOLIO_SUMMARY_PNG),  # Daily-generated card
        ...
    }
```

---

## 9. DAILY PORTFOLIO SYSTEM — SIMPLIFICATION

### 9.1 Current State

daily_scanner.py maintains a separate daily_portfolio.csv with its own DailyTrade dataclass, legacy indicators (BoS daily, flat 20% stop), and independent backup system. It reads portfolio.csv only for deduplication.

### 9.2 Assessment

The daily portfolio serves a different purpose than the weekly portfolio — it tracks short-term momentum signals that don't qualify for the weekly scanner's stringent 5-gate process. However, the legacy indicators and separate dataclass create maintenance overhead.

### 9.3 Recommendation: Keep Separate, Minor Cleanup

**Don't merge daily and weekly portfolios.** They serve different purposes:
- Weekly: high-conviction, multi-gate screening, tiered profit lock
- Daily: momentum-based, simpler signals, flat 20% trailing stop

**Cleanup:**
1. Include daily_portfolio positions in the portfolio_snapshot.json under a separate `daily_positions` key
2. Update daily_scanner.py to call `refresh_daily_prices()` for its positions as part of the daily pipeline (before the weekly refresh)
3. Consider: should the daily portfolio feed into tweets? Currently it doesn't. If daily positions are interesting enough to share, add them to the tweet system's data pool.

**Deferred to future:** Migrating daily_scanner from legacy indicators to Sterling Grid. This is a significant change that should be its own spec when the weekly scanner + Sterling indicators are validated and stable.

### 9.4 daily_positions in portfolio_snapshot.json

```json
{
  "daily_positions": [
    {
      "ticker": "AAPL",
      "entry_date": "2026-02-24",
      "entry_price": 185.50,
      "current_price": 187.25,
      "pnl_pct": 0.9,
      "stop_level": 149.80,
      "theme": "Technology",
      "timeframe": "daily"
    }
  ]
}
```

This allows the Substack and tweet systems to optionally reference daily positions without parsing a separate CSV.

---

## 10. manager.py CHANGES

### 10.1 New Functions (3)

**Function 1: refresh_daily_prices()** (~60 lines)
- Called by daily_content.yml
- Fetches prices, updates portfolio.csv, equity curve, snapshot, Sheets export
- See Section 3.1 for full design

**Function 2: generate_portfolio_snapshot()** (~120 lines)
- Builds comprehensive JSON snapshot from PortfolioManager state
- Pre-computes all derived stats (winners, movers, themes, benchmarks)
- Atomic JSON write to portfolio_snapshot.json
- See Section 4.3 for full design

**Function 3: _compute_daily_movers()** (~40 lines)
- Compares current prices to yesterday's close (from equity_curve.csv last entry)
- Returns list of positions with biggest moves today
- Used in portfolio_snapshot.json `movers_today` field

### 10.2 Modified Functions (2)

**update_prices():** Add `prices_updated_at` tracking
```python
def update_prices(self, stocks_dict=None, check_delisted=True):
    # ... existing logic ...
    self._prices_updated_at = datetime.now(timezone.utc).isoformat()
    self._save()
```

**_save():** No logic change, but ensure backup_cleanup integration is clean. Currently, _save() creates a backup every call. With daily price refresh calling _save() every weekday morning, that's 5 additional backups per week. backup_cleanup.py handles this (keeps 1 per ISO week), so no change needed.

### 10.3 New Import

```python
from datetime import datetime, timedelta, timezone  # Add timezone
```

### 10.4 New Config Constant

```python
PORTFOLIO_SNAPSHOT_FILE = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"
```

### 10.5 Lines Impact

Current: 1,713 lines → Target: ~1,930 lines (+~220 lines for 3 new functions + helpers)

---

## 11. BACKUP_CLEANUP.PY — NO CHANGES

backup_cleanup.py (296 lines) is well-designed and complete. The ISO-week dedup algorithm handles increased backup frequency from daily refreshes without any changes.

The only consideration is that with daily saves, each ISO week will have 5-6 backups to clean (instead of 1-2 from Friday scans). The dedup keeps the newest per week, so the behavior is correct.

---

## 12. GOOGLE SHEETS EXPORT — IMPROVEMENTS

### 12.1 Current State

export_for_google_sheets() creates portfolio_google_sheets.csv with 19 columns. Users manually import this CSV into Google Sheets and add GOOGLEFINANCE formulas. The import is manual and ad-hoc.

### 12.2 Improvement: Daily Auto-Export

With the daily refresh pipeline, portfolio_google_sheets.csv is updated every morning automatically. The file is committed to the repo, so Google Sheets can be configured to auto-import via URL.

**Google Sheets auto-import formula (manual one-time setup):**
```
=IMPORTDATA("https://raw.githubusercontent.com/[your-repo]/main/portfolio/output/portfolio_google_sheets.csv")
```

This makes Google Sheets self-updating from the daily pipeline — no manual CSV import needed after initial setup.

### 12.3 Enhancement: Add Portfolio Stats Row

Add a summary row at the bottom of the Google Sheets export:

```csv
# After all trade rows:
SUMMARY,,,,,,,,,,,,,,,,,,
,Total Return,{total_return_pct}%,,SPY Return,{spy_return_pct}%,,Alpha,{alpha_pct}%,,Win Rate,{win_rate}%,,NAV,{currency}{nav}
```

This gives Google Sheets users a quick summary without scrolling or adding formulas.

---

## 13. PORTFOLIO VIEWER ARTIFACT

### 13.1 Concept

For quick portfolio checks outside of Google Sheets or terminal, build a self-contained HTML portfolio viewer that can be:
1. Generated daily as part of the pipeline
2. Opened in any browser
3. Optionally deployed as a simple static page

### 13.2 Implementation — Lightweight HTML Artifact

`portfolio_visual.py --daily` generates a self-contained HTML file with:

```html
<!-- portfolio_dashboard.html — self-contained, no external dependencies -->
<html>
<head>
  <style>
    /* Inline CSS — dark theme, clean tables, responsive */
  </style>
</head>
<body>
  <h1>Sterling Signals Portfolio</h1>
  <p class="timestamp">Prices as of Feb 25, 2026 12:00 UTC</p>
  
  <!-- Summary cards -->
  <div class="cards">
    <div class="card">NAV: £37,500</div>
    <div class="card">Alpha vs S&P: +2.9%</div>
    <div class="card">Win Rate: 71%</div>
    <div class="card">Open: 6 positions</div>
  </div>
  
  <!-- Equity curve (inline SVG) -->
  <svg class="equity-curve">...</svg>
  
  <!-- Open positions table -->
  <table>
    <tr><th>Ticker</th><th>Entry</th><th>Current</th><th>P&L</th><th>Days</th><th>Theme</th><th>Stop</th></tr>
    <tr class="winner"><td>$RCAT</td><td>$8.50</td><td>$13.25</td><td class="green">+55.9%</td><td>58</td><td>Drone Tech</td><td>—</td></tr>
    ...
  </table>
  
  <!-- Theme allocation (inline chart or simple bars) -->
  <div class="themes">...</div>
  
  <!-- Performance vs benchmarks -->
  <table class="benchmarks">
    <tr><th>Period</th><th>Portfolio</th><th>S&P 500</th><th>Alpha</th></tr>
    <tr><td>7D</td><td>+2.1%</td><td>+0.8%</td><td class="green">+1.3%</td></tr>
    ...
  </table>
  
  <!-- Recent exits -->
  <table class="exits">...</table>
</body>
</html>
```

**All data is inlined** — no JavaScript API calls, no external stylesheets. The file works offline and renders correctly when embedded in Substack notes or opened standalone.

### 13.3 Portfolio Summary Card (PNG)

For tweet attachments, generate a clean 800×450 summary card:

```
┌────────────────────────────────────────────┐
│  STERLING SIGNALS PORTFOLIO                │
│  ──────────────────────────                │
│  NAV: £37,500    Alpha: +2.9%             │
│  Win Rate: 71%   Positions: 6             │
│                                            │
│  TOP PERFORMERS                            │
│  $RCAT  +55.9%  ████████████████░░  Drone │
│  $STRL  +44.8%  ██████████████░░░░  Infra │
│  $MOD   +32.7%  ██████████░░░░░░░░  Power │
│                                            │
│  sterlingssignals.substack.com             │
└────────────────────────────────────────────┘
```

Generated via matplotlib with Sterling Signals branding. Saved as `portfolio_summary.png`.

---

## 14. CONFIGURATION CHANGES

### 14.1 New Config Constants

```python
# config/output_paths.py
PORTFOLIO_SNAPSHOT_FILE = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"
PORTFOLIO_DASHBOARD_FILE = SUBSTACK_CURRENT / "portfolio_dashboard.html"
PORTFOLIO_SUMMARY_PNG = SUBSTACK_CURRENT / "portfolio_summary.png"
```

### 14.2 Marketing Thresholds — Keep As-Is

```python
big_win_threshold = 25.0      # Big win display threshold
home_run_threshold = 50.0     # Home run milestone
hall_of_fame_threshold = 100.0 # 100%+ milestone
CELEBRATION_THRESHOLDS = [25.0, 50.0, 100.0]
```

These feed into portfolio_snapshot.json `big_wins`, `home_runs` lists and into the Substack milestone override detection.

### 14.3 Daily Refresh Settings

```python
# config/settings.py — new
PORTFOLIO_PRICE_STALENESS_HOURS = 8  # Warn if prices older than this
PORTFOLIO_SNAPSHOT_CLOSED_TRADES_LIMIT = 20  # Include last N closed trades in snapshot
```

---

## 15. CROSS-SYSTEM DATA CONTRACTS

### 15.1 Portfolio → Scanner

| Output | Consumer | Contract |
|--------|----------|----------|
| portfolio.csv | scanner.py `get_open_position_symbols()` | Returns set of OPEN ticker symbols for dedup |
| portfolio.csv | scanner.py `check_sell_signals()` | Reads entry_price, highest_close for profit lock calc |
| portfolio.csv | scanner.py `add_trade_from_stock()` | Writes new OPEN trade row |
| portfolio.csv | scanner.py `flag_exit()` | Updates status to CLOSED/STOPPED |

**No changes.** Scanner writes are the primary mutation path and remain unchanged.

### 15.2 Portfolio → Substack

| Output | Consumer | Contract |
|--------|----------|----------|
| **portfolio_snapshot.json** (NEW) | daily_context_builder.py | Full portfolio state for context doc |
| **portfolio_snapshot.json** (NEW) | daily_notes_generator.py | Winners, movers, stats for notes |
| **portfolio_dashboard.html** (NEW) | Saturday newsletter embedding | Latest dashboard HTML |
| portfolio.csv | portfolio_visual.py | Direct read for full dashboard generation |
| equity_curve.csv | portfolio_visual.py | NAV history for equity curve SVG |

**Migration:** Substack modules should prefer portfolio_snapshot.json over direct CSV reads. Existing CSV reads remain as fallback.

### 15.3 Portfolio → Tweets

| Output | Consumer | Contract |
|--------|----------|----------|
| **portfolio_snapshot.json** (NEW) | live_context_gatherer.py | Portfolio context for Grok prompt |
| **portfolio_snapshot.json** (NEW) | live_tweet_generator.py | Position data for receipts, validation |
| **portfolio_summary.png** (NEW) | poster.py | Chart attachment for portfolio tweets |
| portfolio.csv | live_tweet_generator.py `load_portfolio()` | Fallback if snapshot missing |

### 15.4 Portfolio → Daily Scanner

| Output | Consumer | Contract |
|--------|----------|----------|
| portfolio.csv | daily_scanner.py `load_weekly_open_symbols()` | Dedup against weekly positions |

**No changes.** Daily scanner reads weekly portfolio for dedup only.

### 15.5 External → Portfolio

| Input | Source | Consumer |
|-------|--------|----------|
| yfinance price data | Yahoo Finance API | fetch_current_prices() |
| SPY/QQQ data | yfinance | get_spy_ytd_return(), EquityTracker.calculate_nav() |

---

## 16. GITHUB ACTIONS INTEGRATION

### 16.1 daily_content.yml — Modified Steps

The daily content pipeline gains portfolio refresh as its first step:

```yaml
name: Daily Content Pipeline
on:
  schedule:
    - cron: '0 12 * * *'   # 07:00 ET (EST)
    - cron: '0 11 * * *'   # 07:00 ET (EDT)
  workflow_dispatch:

jobs:
  daily-content:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # ... setup steps ...
      
      # Portfolio refresh (NEW — before any content generation)
      - name: Refresh portfolio prices
        run: |
          python -c "
          from portfolio.manager import refresh_daily_prices
          result = refresh_daily_prices()
          print(f'Portfolio refresh: {result.get(\"summary\", {}).get(\"open_positions\", 0)} positions updated')
          "
        continue-on-error: true
        env:
          # No additional secrets needed — yfinance is public
      
      # Portfolio dashboard (NEW)
      - name: Generate portfolio dashboard
        run: python -m substack.portfolio_visual --daily
        continue-on-error: true
      
      # ... remaining Substack content steps (market analyzer, context builder, notes) ...
      
      # Commit all outputs
      - name: Commit results
        run: |
          git add --force portfolio/output/ substack/output/
          git diff --staged --quiet || git commit -m "Daily content update $(date +%Y-%m-%d)"
          git push
```

### 16.2 friday_scan.yml — No Changes

The Friday scan pipeline continues to handle entries, exits, and the full scanner pass. It calls `update_prices()` and `update_equity_curve()` as part of the scan. The daily refresh on Saturday morning (if daily_content.yml runs on weekends) will simply overwrite with identical data — no conflict.

### 16.3 Commit Scope

The daily pipeline now commits:
- `portfolio/output/portfolio.csv` (updated prices)
- `portfolio/output/equity_curve.csv` (new daily row)
- `portfolio/output/portfolio_snapshot.json` (new)
- `portfolio/output/portfolio_google_sheets.csv` (refreshed)
- `substack/output/current/portfolio_dashboard.html` (new)
- `substack/output/current/portfolio_summary.png` (new)
- Plus all existing Substack outputs (daily_context.md, notes, market_analysis.md)

---

## 17. MODULE INVENTORY

### 17.1 Modules Modified (2)

| File | Current Lines | Target Lines | Changes |
|------|--------------|-------------|---------|
| `portfolio/manager.py` | 1,713 | ~1,930 | +3 new functions (refresh_daily_prices, generate_portfolio_snapshot, _compute_daily_movers), timezone import, PORTFOLIO_SNAPSHOT_FILE constant |
| `substack/portfolio_visual.py` | 819 | ~900 | +`--daily` mode for lightweight dashboard + summary PNG generation |

### 17.2 Modules Unchanged (1)

| File | Lines | Reason |
|------|-------|--------|
| `portfolio/backup_cleanup.py` | 296 | Works well, handles increased backup frequency |

### 17.3 No Modules Deleted

The portfolio system has no dead code to remove. Every function is either called by the scanner pipeline, CLI, or downstream consumers.

### 17.4 Net Line Change

| Category | Lines |
|----------|-------|
| Added (manager.py) | +217 |
| Added (portfolio_visual.py --daily) | +81 |
| **Net change** | **+298** |
| **Total portfolio system** | 2,828 → ~3,126 lines |

---

## 18. IMPLEMENTATION ORDER

### Phase 1: Core — refresh_daily_prices() + snapshot (3-4 hours)

1. Add `PORTFOLIO_SNAPSHOT_FILE` to config/output_paths.py
2. Implement `generate_portfolio_snapshot()` in manager.py
3. Implement `_compute_daily_movers()` helper
4. Implement `refresh_daily_prices()` orchestrator
5. Test: run refresh, verify portfolio.csv updated, snapshot.json created, equity curve has new row
6. Test: verify snapshot JSON schema matches Section 4.2

**Gate:** `python -c "from portfolio.manager import refresh_daily_prices; print(refresh_daily_prices())"` works and produces valid snapshot.

### Phase 2: Daily Dashboard (2-3 hours)

1. Add `--daily` mode to portfolio_visual.py
2. Implement `generate_daily_dashboard()` — reads from snapshot JSON
3. Implement summary card PNG generation (matplotlib)
4. Test: verify HTML dashboard renders correctly in browser
5. Test: verify PNG is clean 800×450 with branding

**Gate:** Both portfolio_dashboard.html and portfolio_summary.png generate without errors and look professional.

### Phase 3: Pipeline Integration (1-2 hours)

1. Add portfolio refresh step to daily_content.yml (before content generation)
2. Add dashboard generation step to daily_content.yml
3. Update git commit scope to include portfolio outputs
4. Test: run daily_content.yml end-to-end (dry-run or local)
5. Verify no conflicts with friday_scan.yml commit patterns

**Gate:** Full pipeline runs: prices refresh → dashboard generates → Substack content generates → commit succeeds.

### Phase 4: Consumer Migration (1-2 hours, can be deferred)

1. Update live_context_gatherer.py to read portfolio_snapshot.json
2. Update daily_context_builder.py to read portfolio_snapshot.json
3. Update daily_notes_generator.py to read portfolio_snapshot.json
4. Each update includes fallback to CSV parsing if snapshot missing

**Gate:** All consumers produce identical output whether reading from snapshot or CSV.

### Phase 5: Google Sheets Improvements (30 min)

1. Add summary row to export_for_google_sheets()
2. Document IMPORTDATA URL in generate_google_sheets_template()
3. Test: verify summary row doesn't break existing Sheets import

**Total estimated time: 8-12 hours**

---

## 19. TESTING CHECKLIST

### 19.1 Price Refresh Tests

- [ ] `refresh_daily_prices()` fetches prices for all open positions
- [ ] portfolio.csv highest_close updates when current_price exceeds it
- [ ] portfolio.csv highest_close does NOT decrease
- [ ] equity_curve.csv gets a new row for today's date
- [ ] equity_curve.csv deduplicates same-date entries (re-run safe)
- [ ] portfolio_snapshot.json written with valid schema
- [ ] portfolio_google_sheets.csv refreshed
- [ ] Works when yfinance is down (continue-on-error, uses stale data)
- [ ] Works with 0 open positions (returns empty snapshot)
- [ ] Works on weekend (uses Friday close prices)

### 19.2 Snapshot Tests

- [ ] `open_positions` list matches portfolio.csv OPEN rows
- [ ] `closed_trades` limited to last 20 (not entire history)
- [ ] `winners` sorted by pnl_pct descending
- [ ] `big_wins` only includes pnl_pct >= 25%
- [ ] `home_runs` only includes pnl_pct >= 50%
- [ ] `movers_today` shows intraday changes (vs yesterday's equity curve close)
- [ ] `themes` grouping is correct (all positions in theme)
- [ ] `equity` section matches EquityTracker.calculate_nav() output
- [ ] `benchmarks` periods match get_performance_summary() output
- [ ] `generated_at` and `prices_updated_at` are valid ISO timestamps
- [ ] Atomic write: partial failure doesn't corrupt existing snapshot

### 19.3 Dashboard Tests

- [ ] `--daily` flag produces standalone HTML (not newsletter-embedded)
- [ ] HTML renders correctly in Chrome/Safari
- [ ] Equity curve SVG is inline (no external dependencies)
- [ ] "Prices as of" badge shows correct timestamp
- [ ] Summary card PNG is 800×450 with readable text
- [ ] PNG includes branding and top 3 winners
- [ ] Both files save to substack/output/current/

### 19.4 Pipeline Integration Tests

- [ ] daily_content.yml: portfolio refresh runs before content generation
- [ ] daily_content.yml: dashboard generates after refresh
- [ ] daily_content.yml: git commit includes portfolio outputs
- [ ] friday_scan.yml: still works independently (no regression)
- [ ] No git merge conflicts between daily and Friday commits
- [ ] Portfolio refresh failure doesn't block content generation (continue-on-error)

### 19.5 Consumer Compatibility Tests

- [ ] live_context_gatherer.py reads portfolio_snapshot.json when available
- [ ] live_context_gatherer.py falls back to CSV when snapshot missing
- [ ] daily_context_builder.py produces correct context doc with snapshot data
- [ ] daily_notes_generator.py produces notes with accurate portfolio stats
- [ ] portfolio_visual.py --daily matches portfolio_visual.py full output (subset of data)

### 19.6 Cross-System Tests

- [ ] Friday scan → Saturday refresh → data is consistent
- [ ] New trade added Friday → snapshot reflects it Saturday morning
- [ ] Position exited Friday → snapshot shows it in recent_exits Saturday
- [ ] Milestone detection: +50% position triggers Substack override
- [ ] Tweet system: RECEIPT with portfolio alpha stat (from snapshot)
- [ ] Tweet system: multi-RECEIPT with portfolio_summary.png attached

---

## 20. SUMMARY STATISTICS

| Metric | Current | Target | Change |
|--------|---------|--------|--------|
| Price refresh frequency | Weekly (Friday) | Daily (weekday mornings) | 5x more frequent |
| Equity curve resolution | Weekly (1 point/week) | Daily (5 points/week) | 5x more data |
| Consumer data source | Ad-hoc CSV parsing (10+ modules) | Single JSON snapshot | Consistent |
| Portfolio visibility | Terminal / Google Sheets | Dashboard HTML + summary PNG | Always accessible |
| Stale data window | Up to 7 days | Up to 18 hours (next morning refresh) | -89% staleness |
| Lines added | — | ~298 | Modest |
| Lines deleted | 0 | 0 | No dead code |
| New output files | 0 | 3 | snapshot.json, dashboard.html, summary.png |
| Pipeline integration | Friday-only | Daily (07:00 ET) | 5x/week |
| Module changes | 0 | 2 (manager.py, portfolio_visual.py) | Minimal surface area |

### Key Wins

1. **Single source of truth with daily freshness.** portfolio_snapshot.json gives every consumer consistent, pre-computed data. No more 10 modules each doing their own CSV parsing and P&L calculation.

2. **Daily equity curve unlocks accurate drawdown tracking.** Current weekly resolution misses intra-week drawdowns entirely. A 10% drawdown that recovers by Friday is invisible. Daily snapshots capture it.

3. **Portfolio dashboard always available.** No more "open Google Sheets and import the CSV manually." A clean HTML dashboard generates every morning, viewable in any browser, embeddable in Substack.

4. **Tweet system gets portfolio-level stats.** Alpha vs S&P, win rate, NAV — these powerful marketing metrics were locked in get_performance_summary() and never surfaced in tweets. Now they're in every snapshot.

5. **Milestone detection becomes daily, not weekly.** A position hitting +50% on Tuesday gets caught Tuesday morning (for Substack content override), not the following Friday. Content stays timely.

6. **Minimal code changes for maximum impact.** 298 new lines across 2 files. No deletions, no restructuring, no breaking changes. The portfolio system was well-built — we're adding a daily refresh layer on top, not redesigning it.

---

## END OF SPECIFICATION

**Implementation dependency chain:**
1. Scanner spec (signals.json themes for tweet system)
2. **Portfolio spec** (can be implemented independently — no scanner/Substack dependencies for core refresh)
3. Substack spec (consumes portfolio_snapshot.json)
4. Tweet spec (consumes portfolio_snapshot.json + portfolio_summary.png)

The portfolio spec is the **most independent** of the four — refresh_daily_prices() and generate_portfolio_snapshot() can be built and tested in isolation before any other subsystem changes.
