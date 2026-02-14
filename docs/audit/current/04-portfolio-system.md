# 04 - Portfolio System

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Overview

The portfolio system is managed by `core/portfolio_manager.py` (1,282 lines). It tracks all trades from entry to exit, calculates P&L, and exports data for Google Sheets.

**Source of truth:** `trades/portfolio.csv`

---

## 2. Data Model

### 2.1 TradeStatus Enum

```python
class TradeStatus(Enum):
    OPEN = "OPEN"         # Active position being tracked
    CLOSED = "CLOSED"     # Exited manually (profit/strategic)
    STOPPED = "STOPPED"   # Hit trailing stop
```

### 2.2 Trade Dataclass

**Stored fields** (persisted in CSV):

| Field | Type | Default | CSV Column |
|-------|------|---------|-----------|
| `ticker` | str | required | ticker |
| `status` | str | "OPEN" | status |
| `entry_date` | str | "" | entry_date |
| `entry_price` | float | 0.0 | entry_price |
| `exit_date` | str | "" | exit_date |
| `exit_price` | float | 0.0 | exit_price |
| `highest_close` | float | 0.0 | highest_close |
| `theme` | str | "" | theme |
| `tier` | str | "" | tier |
| `signal_type` | str | "" | signal_type |
| `conviction` | int | 0 | conviction |
| `notes` | str | "" | notes |
| `stop_pct` | float | 20.0 | stop_pct |

**Calculated fields** (in-memory only):

| Field | Type | Formula |
|-------|------|---------|
| `current_price` | float | From yfinance |
| `pnl_pct` | float | `((current - entry) / entry) × 100` |
| `pnl_usd` | float | `(current - entry) × 100` (assumes 100 shares) |
| `stop_level` | float | `highest_close × (1 - stop_pct/100)` |
| `days_held` | int | `(today - entry_date).days` |
| `distance_to_stop_pct` | float | `((current - stop) / current) × 100` |
| `stop_alert` | bool | True if within 5% of stop |

### 2.3 CSV Format

```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,stop_pct
RCAT,OPEN,2025-12-29,8.50,,,12.19,Drone Technology,TIER1,TRADE,4,Scanner signal,20.0
IBKR,OPEN,2025-12-29,65.00,,,72.93,Financials,TIER1,TRADE,5,Scanner signal,20.0
OKLO,CLOSED,2024-11-15,22.00,2025-01-08,28.50,28.50,Nuclear,TIER1,TRADE,4,Manual exit,20.0
SMCI,STOPPED,2024-10-01,45.00,2025-01-10,36.00,52.00,AI Infrastructure,TIER2,TRADE,3,Hit 20% trailing stop,20.0
```

---

## 3. PortfolioManager Class

### 3.1 Constructor

```python
class PortfolioManager:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path or TRADES_DIR / "portfolio.csv"
        self.trades: List[Trade] = []
        self._load()
```

### 3.2 Key Methods

| Method | Line | Purpose |
|--------|------|---------|
| `_load()` | ~280 | Load trades from CSV, run validate() on each |
| `_save()` | ~310 | Atomic write: tempfile + os.replace(), create backup |
| `add_trade(ticker, entry_price, theme, tier, ...)` | ~350 | Add new OPEN trade |
| `flag_exit(ticker, exit_price, reason)` | ~380 | Mark trade as CLOSED or STOPPED |
| `tighten_stop(ticker)` | ~400 | Set per-trade stop_pct to TIGHTEN_STOP_PCT (15%) |
| `update_prices()` | ~420 | Fetch current prices via yfinance, recalculate P&L |
| `check_stop_signals()` | ~460 | Check all open trades against their stop levels |
| `get_open_positions()` | ~490 | Return List[Trade] where status == OPEN |
| `get_performance_summary()` | ~520 | Calculate win rate, avg winner, avg loser |
| `export_for_google_sheets()` | ~580 | Write portfolio_google_sheets.csv with calculated fields |
| `_matched_spy_alpha(trade)` | ~650 | Calculate SPY return over same holding period |
| `get_spy_return_for_period(start, end)` | ~680 | Get SPY return for specific date range |

### 3.3 Atomic Write Implementation (line ~310)

```python
def _save(self):
    # Validate all trades before saving
    for trade in self.trades:
        warnings = trade.validate()
        if warnings:
            for w in warnings:
                print(f"    ⚠ {trade.ticker}: {w}")

    # Create backup
    if self.csv_path.exists():
        backup_dir = TRADES_DIR / "portfolio_backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"portfolio_{timestamp}.csv"
        shutil.copy2(self.csv_path, backup_path)

        # Rotate backups (keep 30)
        backups = sorted(backup_dir.glob("portfolio_*.csv"))
        while len(backups) > 30:
            backups[0].unlink()
            backups.pop(0)

    # Atomic write via temp file
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', dir=self.csv_path.parent,
        suffix='.csv', delete=False
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for trade in self.trades:
            writer.writerow(trade.to_dict())
        tmp_path = tmp.name

    os.replace(tmp_path, self.csv_path)
```

### 3.4 Trade.validate() Method (line ~217)

```python
def validate(self) -> List[str]:
    warnings = []
    if self.entry_price < 0:
        warnings.append("Negative entry price")
    if self.exit_price < 0:
        warnings.append("Negative exit price")
    if self.highest_close < 0:
        warnings.append("Negative highest_close")
    if self.exit_date and self.entry_date:
        if self.exit_date < self.entry_date:
            warnings.append("Exit date before entry date")
    if self.status == "OPEN" and self.highest_close > 0:
        if self.highest_close < self.entry_price:
            warnings.append("highest_close < entry_price for OPEN position")
    if self.status == "STOPPED" and self.exit_price == 0:
        warnings.append("STOPPED status with no exit_price")
    return warnings
```

Warnings only - no exceptions raised, no data rejection.

---

## 4. Position Lifecycle

### 4.1 Entry

```
Scanner Step 7.5 (DD) → STRONG BUY or SPEC BUY
  → scanner.py: add_to_open_positions(stock) [line 3158]
    → portfolio_manager.add_trade(
        ticker=stock.symbol,
        entry_price=stock.price,
        theme=stock.theme,
        tier=stock.tier,
        signal_type="TRADE",
        conviction=stock.conviction,
        notes="Scanner signal"
      )
```

Entry date = current date. Status = OPEN.

### 4.2 Monitoring (Weekly)

Each Friday scan:
1. Download current prices for open positions
2. Update `highest_close` if current > previous high
3. Check trailing stop: `drawdown >= trade.stop_pct`
4. Check BoS bearish: tighten stop to 15%

### 4.3 Exit - Trailing Stop

```
scanner.py: _check_sell_signals_portfolio_manager() [line 963]
  → drawdown_pct >= trade.stop_pct (default 20%, or 15% if tightened)
    → portfolio_manager.flag_exit(ticker, current_price, reason)
      → trade.status = "STOPPED"
      → trade.exit_price = current_price
      → trade.exit_date = today
```

### 4.4 Exit - Manual

```
CLI: python -m core.portfolio_manager --exit TICKER --exit-price 15.00
  → portfolio_manager.flag_exit(ticker, exit_price)
    → trade.status = "CLOSED"
    → trade.exit_price = exit_price
    → trade.exit_date = today
```

### 4.5 Stop Tightening

```
scanner.py: stock.bos_bearish detected [line 1010]
  → portfolio_manager.tighten_stop(ticker)
    → trade.stop_pct = TIGHTEN_STOP_PCT (15%)
```

Per-trade `stop_pct` persisted in CSV. Default 20%, tightened to 15% on BoS bearish.

---

## 5. P&L Calculation

### 5.1 Per-Trade P&L

```python
# For OPEN positions:
pnl_pct = ((current_price - entry_price) / entry_price) * 100
pnl_usd = (current_price - entry_price) * 100  # assumes 100 shares

# For CLOSED/STOPPED positions:
pnl_pct = ((exit_price - entry_price) / entry_price) * 100
pnl_usd = (exit_price - entry_price) * 100
```

### 5.2 Portfolio Summary

```python
def get_performance_summary(self):
    closed = [t for t in self.trades if t.status in ("CLOSED", "STOPPED")]
    winners = [t for t in closed if t.pnl_pct > 0]
    losers = [t for t in closed if t.pnl_pct <= 0]

    return {
        "total_trades": len(closed),
        "win_rate": len(winners) / len(closed) * 100 if closed else 0,
        "avg_winner": mean([t.pnl_pct for t in winners]) if winners else 0,
        "avg_loser": mean([t.pnl_pct for t in losers]) if losers else 0,
        "open_positions": len([t for t in self.trades if t.status == "OPEN"]),
        "unrealized_pnl": sum(t.pnl_pct for t in self.trades if t.status == "OPEN"),
    }
```

### 5.3 SPY Alpha Calculation

```python
def _matched_spy_alpha(self, trade):
    """Calculate SPY return over the same holding period as the trade."""
    spy_return = get_spy_return_for_period(trade.entry_date, trade.exit_date or today)
    alpha = trade.pnl_pct - spy_return
    return alpha
```

Uses matched-period comparison (not just YTD SPY).

---

## 6. Google Sheets Export

### 6.1 Export Format

```csv
ticker,status,entry_date,entry_price,...,current_price,pnl_pct,pnl_usd,stop_level,days_held,distance_to_stop,stop_alert
RCAT,OPEN,2025-12-29,8.50,...,13.25,55.9%,475,9.75,23,26.4%,
```

Additional calculated columns appended to base CSV:
- `current_price`: From yfinance (replace with `=GOOGLEFINANCE(A2,"price")` in Sheets)
- `pnl_pct`: Percentage gain/loss
- `pnl_usd`: Dollar gain/loss (assumes 100 shares)
- `stop_level`: Current stop price
- `days_held`: Days since entry
- `distance_to_stop`: Percentage above stop
- `stop_alert`: "ALERT" if within 5% of stop

### 6.2 Google Sheets Formula Setup

Replace `current_price` column with:
```
=IF(B2="OPEN", GOOGLEFINANCE(A2, "price"), G2)
```

---

## 7. CLI Interface

```bash
python -m core.portfolio_manager --report        # View portfolio summary
python -m core.portfolio_manager --update        # Refresh prices via yfinance
python -m core.portfolio_manager --export        # Export for Google Sheets
python -m core.portfolio_manager --add TICKER --price 10.50 --theme "AI"
python -m core.portfolio_manager --exit TICKER --exit-price 15.00
python -m core.portfolio_manager --migrate       # One-time: migrate legacy files
```

| Argument | Purpose |
|----------|---------|
| `--report` | Print portfolio summary with P&L |
| `--update` | Fetch current prices, recalculate P&L |
| `--export` | Write portfolio_google_sheets.csv |
| `--add TICKER` | Add manual trade |
| `--price PRICE` | Entry price for --add |
| `--theme THEME` | Theme for --add |
| `--exit TICKER` | Exit a position |
| `--exit-price PRICE` | Exit price for --exit |
| `--migrate` | Migrate from legacy CSV formats |
| `--setup` | Initialize portfolio.csv if missing |

---

## 8. Files Read/Written

### Read
- `trades/portfolio.csv` - Trade history
- yfinance API - Current prices, SPY data

### Written
- `trades/portfolio.csv` - Updated trades (atomic write)
- `trades/portfolio_google_sheets.csv` - Export with calculated fields
- `trades/portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv` - Timestamped backups (max 30)

---

## 9. Integration Points

### Called By
- `core/scanner.py` - Add trades, check stops, update prices, export
- `content/reaction_generator.py` - `fetch_current_prices()` for tweet data
- `content/grok_prompts_generator.py` - Portfolio data for prompts
- `content/newsletter_compiler.py` - P&L data for newsletter
- `distribution/signal_tracker.py` - `load_portfolio()` for win tracking

### Standalone Functions (importable)
- `load_portfolio(csv_path) -> PortfolioManager` - Factory function
- `fetch_current_prices(tickers) -> Dict[str, float]` - Canonical price fetcher
- `get_spy_ytd_return() -> float` - SPY year-to-date return
- `get_spy_return_for_period(start, end) -> float` - Matched-period SPY return
- `get_open_position_symbols() -> Set[str]` - Quick symbol lookup

---

*End of Document 4*
