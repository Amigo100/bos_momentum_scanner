# Portfolio Tracking System Audit

**Document:** `docs/audit/03-portfolio-tracking.md`
**Created:** 2026-01-27
**Author:** Claude Code Audit
**System:** Sterling Signals Marketing System

---

## Executive Summary

The Sterling Signals portfolio tracking system uses a **CSV-based architecture** with automatic backup and Google Sheets integration for live tracking. The system tracks position lifecycle from entry through exit with comprehensive metrics calculation and milestone celebration tracking.

### Key Statistics (Current State)
| Metric | Value |
|--------|-------|
| Open Positions | 11 |
| Backup Files | 31 |
| Data Storage | CSV (portfolio.csv) |
| Price Source | yfinance API |
| Backup Frequency | On every save |

---

## 1. Data Model

### 1.1 Primary Storage

**Location:** `trades/portfolio.csv`

The portfolio uses a flat-file CSV structure as the single source of truth for all trade data.

```
trades/
├── portfolio.csv                    # PRIMARY: All trades (open + closed)
├── portfolio_google_sheets.csv      # Export with calculated fields
├── portfolio_backups/               # Timestamped backups
│   └── portfolio_YYYYMMDD_HHMMSS.csv
├── celebrations.json                # Milestone tracking (25%, 50%, 100%)
└── signals.json                     # Scanner output (source of new signals)
```

### 1.2 Schema Definition

#### Trade Dataclass (`portfolio_manager.py:136-159`)

```python
@dataclass
class Trade:
    # ═══════════════════════════════════════════════════════════════
    # STORED FIELDS (12 columns, persisted to CSV)
    # ═══════════════════════════════════════════════════════════════
    ticker: str              # Stock symbol (e.g., "AAPL")
    status: str = "OPEN"     # OPEN | CLOSED | STOPPED
    entry_date: str = ""     # YYYY-MM-DD format
    entry_price: float = 0.0 # Entry execution price
    exit_date: str = ""      # Exit date (empty if OPEN)
    exit_price: float = 0.0  # Exit execution price (empty if OPEN)
    highest_close: float = 0.0  # Peak price since entry (for trailing stop)
    theme: str = ""          # Investment theme from scanner
    tier: str = ""           # TIER1 | TIER2 | TIER3
    signal_type: str = "PASS"  # PASS | CONSIDER
    conviction: int = 0      # 1-5 scale
    notes: str = ""          # Trade notes/comments

    # ═══════════════════════════════════════════════════════════════
    # CALCULATED FIELDS (8 fields, computed on load, NOT stored)
    # ═══════════════════════════════════════════════════════════════
    current_price: float = 0.0       # Live market price
    pnl_pct: float = 0.0             # Profit/loss percentage
    pnl_usd: float = 0.0             # P&L in dollars (assumes 100 shares)
    stop_level: float = 0.0          # 20% below highest_close
    days_held: int = 0               # Duration of position
    distance_to_stop_pct: float = 0.0  # % away from stop
    stop_alert: bool = False         # True if within 5% of stop
```

#### CSV Header Row
```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes
```

### 1.3 Trade Status Enum (`portfolio_manager.py:126-129`)

```python
class TradeStatus(Enum):
    OPEN = "OPEN"       # Active position being tracked
    CLOSED = "CLOSED"   # Exited manually (profit taking, strategic)
    STOPPED = "STOPPED" # Hit 20% trailing stop
```

### 1.4 Metadata Captured at Entry

When a new position is added, the following metadata is captured:

| Field | Source | Description |
|-------|--------|-------------|
| `ticker` | Stock.symbol | Uppercase ticker symbol |
| `entry_date` | System clock | Today's date (YYYY-MM-DD) |
| `entry_price` | Stock.price | Current market price at entry |
| `highest_close` | entry_price | Initialized to entry price |
| `theme` | Stock.theme | From thematic analyzer |
| `tier` | Stock.tier | TIER1/2/3 from technical gate |
| `signal_type` | Stock.final_decision | PASS or CONSIDER |
| `conviction` | Stock.conviction | 1-5 from gatekeeper |
| `notes` | Empty | Can be added manually |

---

## 2. Position Lifecycle

### 2.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POSITION LIFECYCLE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐            │
│  │   SCANNER    │────►│  GATEKEEPER   │────►│  PASS DECISION   │            │
│  │  (1800 tickers)    │  (LLM Gate)   │     │  (3-6 signals)   │            │
│  └──────────────┘     └───────────────┘     └────────┬─────────┘            │
│                                                       │                      │
│                                                       ▼                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     ADD_TRADE_TO_PORTFOLIO()                           │ │
│  │  scanner.py:1084 → portfolio_manager.py:885 → add_trade_from_stock()  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                       │                      │
│                                                       ▼                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        portfolio.csv                                    │ │
│  │  Status: OPEN | Entry: $XX.XX | Date: YYYY-MM-DD | Theme | Tier       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│           │                     │                      │                     │
│           ▼                     ▼                      ▼                     │
│  ┌─────────────────┐  ┌─────────────────┐    ┌──────────────────┐          │
│  │  PRICE UPDATE   │  │  STOP CHECK     │    │  MANUAL EXIT     │          │
│  │  update_prices()│  │  check_stops()  │    │  flag_exit()     │          │
│  └─────────────────┘  └─────────────────┘    └──────────────────┘          │
│           │                     │                      │                     │
│           │         ┌──────────┴──────────┐           │                     │
│           │         ▼                     ▼           │                     │
│           │  ┌────────────┐      ┌────────────┐       │                     │
│           │  │ STOP HIT   │      │ NO STOP    │       │                     │
│           │  └─────┬──────┘      └──────┬─────┘       │                     │
│           │        │                    │             │                     │
│           │        ▼                    │             ▼                     │
│           │  ┌────────────────┐         │     ┌────────────────┐           │
│           │  │ Status: STOPPED│         │     │ Status: CLOSED │           │
│           │  │ exit_date: now │         │     │ exit_date: now │           │
│           │  │ exit_price: $X │         │     │ exit_price: $X │           │
│           │  └────────────────┘         │     └────────────────┘           │
│           │        │                    │             │                     │
│           │        │                    │             │                     │
│           ▼        ▼                    ▼             ▼                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        BACKUP CREATED                                   │ │
│  │  trades/portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Adding New Positions

**Entry Point:** `scanner.py:1084`

```python
# After gatekeeper decides PASS
if final_decision == "PASS":
    add_trade_to_portfolio(stock)
```

**Implementation:** `portfolio_manager.py:292-319`

```python
def add_trade(self, ticker: str, entry_price: float, theme: str = "",
              tier: str = "", signal_type: str = "PASS", conviction: int = 0,
              notes: str = "") -> Trade:
    """Add a new trade to the portfolio."""

    # DUPLICATE PREVENTION: Check if already exists as open position
    existing = self.get_open_position(ticker)
    if existing:
        print(f"  ⚠ {ticker} already has an open position")
        return existing

    trade = Trade(
        ticker=ticker.upper(),
        status="OPEN",
        entry_date=datetime.now().strftime("%Y-%m-%d"),
        entry_price=entry_price,
        highest_close=entry_price,  # Initialize to entry
        theme=theme,
        tier=tier,
        signal_type=signal_type,
        conviction=conviction,
        notes=notes
    )

    self.trades.append(trade)
    self._save()  # Immediately persist + backup

    return trade
```

### 2.3 Updating Position Data

**Price Refresh:** `portfolio_manager.py:378-446`

Two mechanisms for price updates:

1. **From Scanner Data** (preferred during scan)
   ```python
   def update_prices(self, stocks_dict: Optional[Dict] = None):
       if stocks_dict:
           for trade in open_trades:
               if trade.ticker in stocks_dict:
                   stock = stocks_dict[trade.ticker]
                   trade.calculate_metrics(stock.price)
   ```

2. **Via yfinance** (standalone update)
   ```python
   def update_prices(self, stocks_dict: Optional[Dict] = None):
       else:
           symbols = [t.ticker for t in open_trades]
           data = yf.download(symbols, period="5d", progress=False)
           # Extract latest Close price
           for trade in open_trades:
               price = data['Close'][trade.ticker].iloc[-1]
               trade.calculate_metrics(float(price))
   ```

**Highest Close Update:** `portfolio_manager.py:173-175`

```python
# In calculate_metrics()
if self.status == "OPEN" and current_price > self.highest_close:
    self.highest_close = current_price  # Ratchet up only
```

### 2.4 Closing Positions

#### Automatic Stop (20% trailing)

**Location:** `portfolio_manager.py:448-484`

```python
def check_stop_signals(self, stocks_dict: Dict) -> List[Trade]:
    """Check for positions that hit their trailing stop."""
    triggered = []

    for trade in self.get_open_positions():
        current_price = stocks_dict[trade.ticker].price

        # Update highest close (only goes up)
        if current_price > trade.highest_close:
            trade.highest_close = current_price

        # Calculate stop level: 20% below peak
        stop_level = trade.highest_close * (1 - TRAILING_STOP_PCT / 100)

        # Check if stopped out
        if current_price <= stop_level:
            trade.status = "STOPPED"
            trade.exit_date = datetime.now().strftime("%Y-%m-%d")
            trade.exit_price = current_price
            trade.notes = f"{trade.notes}; Trailing stop hit at ${current_price:.2f}"
            triggered.append(trade)

    if triggered:
        self._save()  # Persist changes + backup

    return triggered
```

#### Manual Exit

**Location:** `portfolio_manager.py:333-352`

```python
def flag_exit(self, ticker: str, exit_price: float, reason: str = "Manual exit"):
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
```

### 2.5 Historical Position Archive

**Approach:** All positions (open and closed) remain in the same `portfolio.csv` file.

Filtering by status provides access to:
- Open positions: `status == "OPEN"`
- Closed positions: `status in ["CLOSED", "STOPPED"]`

**Accessor Functions:**

```python
# portfolio_manager.py
def get_open_positions(self) -> List[Trade]:
    return [t for t in self.trades if t.status == "OPEN"]

def get_closed_trades(self) -> List[Trade]:
    return [t for t in self.trades if t.status != "OPEN"]

# signal_tracker.py
def get_closed_positions() -> List[Dict]:
    trades = load_portfolio()
    return [t for t in trades if t.get('status', '').upper() in ['CLOSED', 'STOPPED']]
```

---

## 3. Flagged Tickers / Watchlist System

### 3.1 Signal Classification

Sterling Signals uses a **two-tier signal system** for flagged tickers:

| Signal Type | Scanner Decision | Public Name | Action |
|-------------|------------------|-------------|--------|
| **PASS** | Cleared all 5 gates | TEAL signal | Full position, enter Monday |
| **CONSIDER** | Cleared gates 1-4, watching gate 5 | On Our Radar | Smaller position or wait |

### 3.2 Consider Signals (Watchlist)

**Location:** `scanner.py:843, 2792-2818`

Consider signals are stored in `signals.json` alongside PASS signals:

```json
{
  "pass_signals": [...],        // TEAL signals - ready to trade
  "consider_signals": [         // Watchlist items
    {
      "symbol": "IONQ",
      "tier": "TIER2",
      "price": 42.15,
      "theme": "Quantum Computing",
      "theme_verdict": "GOOD FIT",
      "final_decision": "CONSIDER",
      "conviction": 3,
      "reasoning": "Extended move, wait for pullback"
    }
  ],
  "sell_signals": [...]
}
```

### 3.3 State Transitions

```
                    ┌────────────────┐
                    │   UNIVERSE     │
                    │ (1,800 tickers)│
                    └───────┬────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────┐                      ┌───────────────┐
│ PASS (TEAL)   │                      │ CONSIDER      │
│ (3-6/week)    │                      │ (5-10/week)   │
└───────┬───────┘                      └───────┬───────┘
        │                                      │
        ▼                                      │
┌───────────────┐                              │
│ portfolio.csv │                              │
│ Status: OPEN  │                              │
└───────┬───────┘                              │
        │                                      │
        │         ┌────────────────────────────┘
        │         │ (Next week if conditions
        │         │  improve → becomes PASS)
        │         ▼
        │  ┌───────────────┐
        │  │ PASS (TEAL)   │
        │  │ (promoted)    │
        │  └───────┬───────┘
        │          │
        │          ▼
        │  ┌───────────────┐
        │  │ portfolio.csv │
        │  │ Status: OPEN  │
        │  └───────────────┘
        │
        ├─────────────────┬────────────────────┐
        ▼                 ▼                    ▼
┌───────────────┐ ┌───────────────┐  ┌───────────────┐
│ Status: CLOSED│ │ Status: STOPPED│  │ Status: OPEN  │
│ (manual exit) │ │ (20% stop hit)│  │ (still active)│
└───────────────┘ └───────────────┘  └───────────────┘
```

### 3.4 Retention Policy

| Data Type | Retention | Location |
|-----------|-----------|----------|
| Open Positions | Indefinite | portfolio.csv |
| Closed/Stopped Positions | Indefinite | portfolio.csv |
| CONSIDER Signals | 21 days | signals.json (auto-expired) |
| Portfolio Backups | Manual cleanup | portfolio_backups/ |

**Consider Signal Expiration:** `signal_tracker.py:875-917`

```python
def filter_expired_consider_signals(signals: List[Dict], max_age_days: int = 21):
    """Remove CONSIDER signals older than max_age_days."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    valid = []
    expired = []

    for signal in signals:
        signal_date = signal.get('scan_date', '')
        if datetime.strptime(signal_date, '%Y-%m-%d') < cutoff:
            expired.append(signal)
        else:
            valid.append(signal)

    if expired:
        print(f"  ⚠️ Expired {len(expired)} consider signals (>{max_age_days} days old)")

    return valid
```

---

## 4. Price Update Data Sources

### 4.1 Primary: yfinance API

**Library:** `yfinance` (Yahoo Finance wrapper)

**Usage Locations:**

| File | Function | Purpose |
|------|----------|---------|
| `portfolio_manager.py:378-446` | `update_prices()` | Update open position prices |
| `portfolio_manager.py:490-499` | `_load_spy_data()` | Load SPY benchmark |
| `signal_tracker.py:119-189` | `fetch_current_prices()` | Batch price fetch |
| `signal_tracker.py:192-203` | `fetch_spy_return()` | SPY return for period |
| `scanner.py:550-600` | `download_and_process()` | Full universe download |

### 4.2 API Call Patterns

**Batch Download (Efficient):**
```python
# signal_tracker.py:139-145
data = yf.download(
    tickers,           # List of symbols
    period="1d",       # 1 day of data
    interval="1d",     # Daily bars
    progress=False,    # No progress bar
    auto_adjust=True   # Adjusted closes
)
```

**Single Ticker:**
```python
# portfolio_manager.py:94-105
info = yf.Ticker(ticker).info
# Returns: marketCap, regularMarketPrice, exchange
```

**Historical Data:**
```python
# portfolio_manager.py:494
spy_data = yf.download("SPY", period="2y", progress=False)
```

### 4.3 Refresh Frequency

| Context | Frequency | Trigger |
|---------|-----------|---------|
| Scanner Run | Weekly (Friday) | `scanner.py --web-search` |
| Portfolio Update | On-demand | `portfolio_manager.py --update` |
| Google Sheets | ~15-20 min | GOOGLEFINANCE() auto-refresh |
| GitHub Actions | Daily (5x) | `daily_post.yml` cron triggers |

### 4.4 Error Handling

**Location:** `signal_tracker.py:119-189`

```python
def fetch_current_prices(tickers: List[str], warn_threshold: float = 0.5):
    """Fetch current prices with validation."""
    prices = {}
    failed_tickers = []

    try:
        data = yf.download(tickers, period="1d", progress=False)

        for ticker in tickers:
            try:
                price = data['Close'][ticker].iloc[-1]
                if not (price != price):  # NaN check
                    prices[ticker] = float(price)
                else:
                    failed_tickers.append(ticker)
            except (KeyError, IndexError):
                failed_tickers.append(ticker)

    except Exception as e:
        print(f"  ❌ Error fetching prices: {e}")
        failed_tickers = list(tickers)

    # GAP 32 fix: Validate completeness
    if tickers:
        success_rate = len(prices) / len(tickers)
        if success_rate < warn_threshold:
            print(f"  ⚠️ WARNING: Price fetch incomplete - only {len(prices)}/{len(tickers)}")
            print(f"     P&L calculations may use stale entry prices as fallback")

    return prices
```

**Fallback Behavior:**
- If yfinance fails, `current_price` remains at `entry_price`
- P&L shows 0% (neither gain nor loss)
- Stop calculations use stale `highest_close`

---

## 5. Data Integrity Mechanisms

### 5.1 Duplicate Prevention

**Location:** `portfolio_manager.py:297-301`

```python
def add_trade(self, ticker: str, entry_price: float, ...):
    # Check if already exists as open position
    existing = self.get_open_position(ticker)
    if existing:
        print(f"  ⚠ {ticker} already has an open position")
        return existing  # Return existing, don't create duplicate
```

**Protection Level:** Prevents duplicate OPEN positions for same ticker.

**Limitation:** Can have multiple closed trades for same ticker (intentional - allows re-entry after exit).

### 5.2 Orphaned Record Handling

**Delisted Ticker Detection:** `portfolio_manager.py:82-123`

```python
def is_ticker_valid(ticker: str) -> bool:
    """Check if ticker is still valid/actively trading."""
    try:
        info = yf.Ticker(ticker).info
        has_market_cap = info.get('marketCap', 0) > 0
        has_price = info.get('regularMarketPrice') is not None
        has_exchange = info.get('exchange') is not None
        return has_market_cap or has_price or has_exchange
    except Exception:
        return False

def check_portfolio_for_invalid_tickers(tickers: List[str]) -> List[str]:
    """Check for delisted/invalid tickers."""
    invalid = []
    for ticker in tickers:
        if not is_ticker_valid(ticker):
            invalid.append(ticker)
            print(f"    ⚠ Ticker {ticker} appears delisted or invalid")
    return invalid
```

**Usage:** Called with `check_delisted=True` flag (optional, adds API latency).

### 5.3 Backup/Recovery Procedures

**Automatic Backup:** `portfolio_manager.py:273-279`

```python
def _save(self) -> None:
    """Save trades to CSV with automatic backup."""
    # Create backup BEFORE overwriting
    if self.portfolio_file.exists():
        backup_file = BACKUP_DIR / f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        import shutil
        shutil.copy(self.portfolio_file, backup_file)

    # Write updated portfolio
    with open(self.portfolio_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDNAMES)
        writer.writeheader()
        for trade in self.trades:
            writer.writerow(trade.to_csv_row())
```

**Backup Directory Structure:**
```
trades/portfolio_backups/
├── portfolio_20260113_174228.csv
├── portfolio_20260118_214327.csv
├── portfolio_20260122_132924.csv
├── portfolio_20260124_234514.csv
├── portfolio_20260127_113626.csv   # Latest
└── ... (31 total backups)
```

**Recovery Procedure:**
```bash
# 1. Identify correct backup by timestamp
ls -la trades/portfolio_backups/

# 2. Copy backup to restore
cp trades/portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv trades/portfolio.csv

# 3. Verify restored data
python portfolio_manager.py --report
```

### 5.4 Data Validation

**CSV Parsing:** `portfolio_manager.py:259-271`

```python
def _load(self) -> None:
    """Load trades from CSV with error handling."""
    if not self.portfolio_file.exists():
        self.trades = []
        return

    try:
        with open(self.portfolio_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.trades = [Trade.from_csv_row(row) for row in reader]
    except Exception as e:
        print(f"  ⚠ Error loading portfolio: {e}")
        self.trades = []  # Fail safe - empty list
```

**Price Validation:** `signal_tracker.py:160-161`

```python
if not (price != price):  # NaN check (x != x is True only for NaN)
    prices[ticker] = float(price)
else:
    failed_tickers.append(ticker)
```

---

## 6. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENTITY RELATIONSHIP DIAGRAM                          │
└─────────────────────────────────────────────────────────────────────────────┘

                               ┌─────────────────┐
                               │    SCANNER      │
                               │   (scanner.py)  │
                               └────────┬────────┘
                                        │
                                        │ produces
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                             signals.json                                 │
  │ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
  │ │  pass_signals   │  │ consider_signals│  │  sell_signals   │          │
  │ │  (TEAL - trade) │  │ (watchlist)     │  │ (exit alerts)   │          │
  │ └────────┬────────┘  └────────┬────────┘  └────────┬────────┘          │
  └──────────┼────────────────────┼────────────────────┼────────────────────┘
             │                    │                    │
             │ adds to            │ (future)           │ triggers
             ▼                    ▼                    ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                           portfolio.csv                                   │
  │ ┌────────────────────────────────────────────────────────────────────┐   │
  │ │ TRADES (unified storage)                                           │   │
  │ │                                                                    │   │
  │ │  [PK] ticker + entry_date                                          │   │
  │ │                                                                    │   │
  │ │  ┌──────────────────────────────────────────────────────────────┐  │   │
  │ │  │ STORED FIELDS (12 columns)                                   │  │   │
  │ │  │ ticker, status, entry_date, entry_price, exit_date,          │  │   │
  │ │  │ exit_price, highest_close, theme, tier, signal_type,         │  │   │
  │ │  │ conviction, notes                                            │  │   │
  │ │  └──────────────────────────────────────────────────────────────┘  │   │
  │ │                                                                    │   │
  │ │  ┌──────────────────────────────────────────────────────────────┐  │   │
  │ │  │ CALCULATED FIELDS (8 fields, in-memory)                      │  │   │
  │ │  │ current_price, pnl_pct, pnl_usd, stop_level, days_held,      │  │   │
  │ │  │ distance_to_stop_pct, stop_alert                             │  │   │
  │ │  └──────────────────────────────────────────────────────────────┘  │   │
  │ │                                                                    │   │
  │ │  STATUS VALUES: OPEN | CLOSED | STOPPED                           │   │
  │ └────────────────────────────────────────────────────────────────────┘   │
  └────────────────────────────────────────────────────────────────────────┘
             │                                         │
             │ exports                                 │ backs up
             ▼                                         ▼
  ┌──────────────────────────┐           ┌──────────────────────────────┐
  │ portfolio_google_sheets  │           │     portfolio_backups/       │
  │       .csv               │           │  portfolio_YYYYMMDD_HHMMSS   │
  │                          │           │        .csv                  │
  │ + calculated fields      │           │  (31 backup files)           │
  │ + formulas for Sheets    │           └──────────────────────────────┘
  └──────────────────────────┘
             │
             │ references
             ▼
  ┌──────────────────────────┐
  │   celebrations.json      │
  │                          │
  │  Tracks milestone posts: │
  │  • 25% = big_win         │
  │  • 50% = home_run        │
  │  • 100% = hall_of_fame   │
  │                          │
  │  Prevents duplicate      │
  │  celebration tweets      │
  └──────────────────────────┘


  RELATIONSHIPS:

  scanner.py ──1:N──► pass_signals      (generates weekly)
  scanner.py ──1:N──► consider_signals  (generates weekly)
  scanner.py ──1:N──► sell_signals      (generates when triggered)

  pass_signals ──1:1──► portfolio.csv   (adds trade on PASS)
  portfolio.csv ──1:N──► backups        (creates on every save)
  portfolio.csv ──1:1──► google_sheets  (exports calculated fields)
  portfolio.csv ──1:N──► celebrations   (tracks milestones)

  yfinance ──N:1──► portfolio.csv       (updates current_price)
  yfinance ──N:1──► signal_tracker      (fetches prices for P&L)
```

---

## 7. Celebration/Milestone Tracking

### 7.1 Celebrations File

**Location:** `trades/celebrations.json`

```json
{
  "_comment": "Tracks which milestones have been celebrated to prevent duplicate posts",
  "_format": "ticker: { threshold_pct: date_celebrated_or_null }",
  "_thresholds": {
    "25_pct": "Standard milestone (25%+)",
    "50_pct": "Home run (50%+)",
    "100_pct": "Hall of fame (100%+)"
  }
}
```

### 7.2 BigWin Dataclass

**Location:** `signal_tracker.py:57-70`

```python
@dataclass
class BigWin:
    ticker: str
    entry_date: str
    entry_price: float
    current_price: float
    pnl_pct: float
    theme: str
    threshold_crossed: float  # 25, 50, or 100
    celebration_type: str     # "big_win", "home_run", "hall_of_fame"
```

### 7.3 Celebration Workflow

```python
# signal_tracker.py

def find_big_wins(signals: List[HistoricalSignal]) -> List[BigWin]:
    """Find signals that crossed celebration thresholds."""
    # 25% = big_win, 50% = home_run, 100% = hall_of_fame

def mark_as_celebrated(ticker: str, threshold: float) -> None:
    """Mark threshold as celebrated to prevent duplicate posts."""
    celebrations[ticker][key] = datetime.now().strftime('%Y-%m-%d')

def is_celebrated(ticker: str, threshold: float) -> bool:
    """Check if threshold already celebrated."""
    return ticker in celebrations and key in celebrations[ticker]

def get_uncelebrated_wins() -> List[BigWin]:
    """Get wins that haven't been celebrated yet."""
```

---

## 8. Google Sheets Integration

### 8.1 Export Format

**Location:** `portfolio_manager.py:624-672`

**Output File:** `trades/portfolio_google_sheets.csv`

**Additional Columns (19 total):**

```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,current_price,
highest_close,stop_level,pnl_pct,pnl_usd,days_held,distance_to_stop,
stop_alert,theme,tier,signal_type,conviction,notes
```

### 8.2 Live Price Formula

```
=IF(B2="OPEN", GOOGLEFINANCE(A2, "price"), G2)
```

**Behavior:**
- If OPEN: Fetches live price from Google Finance
- If CLOSED/STOPPED: Uses stored exit_price

### 8.3 Auto-Refresh

Google Sheets updates `GOOGLEFINANCE()` formulas every 15-20 minutes during market hours.

---

## 9. Questions & Concerns

### 9.1 Critical Issues

| ID | Severity | Issue | Location | Impact |
|----|----------|-------|----------|--------|
| **PTR-1** | 🔴 CRITICAL | No database transactions | CSV operations | Data corruption possible on crash |
| **PTR-2** | 🔴 CRITICAL | No file locking | `_save()` | Concurrent writes could corrupt data |
| **PTR-3** | 🟠 HIGH | Stale prices on yfinance failure | `update_prices()` | P&L shows 0% incorrectly |

### 9.2 Medium Issues

| ID | Severity | Issue | Location | Recommendation |
|----|----------|-------|----------|----------------|
| **PTR-4** | 🟡 MEDIUM | Backup cleanup absent | `portfolio_backups/` | Add retention policy (keep 30 days) |
| **PTR-5** | 🟡 MEDIUM | No CONSIDER → portfolio path | signals.json | Manual process required |
| **PTR-6** | 🟡 MEDIUM | Single ticker rate limit | yfinance | Batch calls only, no individual refresh |

### 9.3 Low Issues

| ID | Severity | Issue | Location | Note |
|----|----------|-------|----------|------|
| **PTR-7** | 🟢 LOW | P&L assumes 100 shares | `pnl_usd` calculation | Cosmetic only |
| **PTR-8** | 🟢 LOW | celebrations.json mostly empty | Current state | Will populate over time |
| **PTR-9** | 🟢 LOW | No audit trail for manual edits | portfolio.csv | Backups provide history |

### 9.4 Recommendations

1. **Add file locking** to prevent concurrent write corruption
2. **Implement backup retention** policy (30 days max)
3. **Add yfinance retry logic** with exponential backoff
4. **Consider SQLite migration** for transaction safety
5. **Add CONSIDER → OPEN promotion workflow** automation

---

## 10. CLI Commands Reference

```bash
# Portfolio Management
python portfolio_manager.py --report          # Print summary
python portfolio_manager.py --update          # Refresh prices via yfinance
python portfolio_manager.py --export          # Export for Google Sheets
python portfolio_manager.py --migrate         # Migrate from old format

# Manual Trade Operations
python portfolio_manager.py --add TICKER --price 10.50 --theme "AI"
python portfolio_manager.py --exit TICKER --exit-price 15.00

# Signal Tracking
python signal_tracker.py                      # Run analysis

# Verification
python -m py_compile portfolio_manager.py signal_tracker.py
```

---

## Appendix A: Current Portfolio Snapshot

**As of 2026-01-27:**

| Ticker | Status | Entry Date | Theme | Tier | Signal |
|--------|--------|------------|-------|------|--------|
| VNET | OPEN | 2026-01-09 | Data Center Cooling | TIER1 | PASS |
| CGON | OPEN | 2026-01-09 | Healthcare / Biotech | TIER1 | PASS |
| INOD | OPEN | 2026-01-18 | Power Grid Infrastructure | TIER1 | PASS |
| OUST | OPEN | 2026-01-18 | Defense & Aerospace | TIER1 | PASS |
| APLD | OPEN | 2026-01-18 | Power Grid Infrastructure | TIER1 | PASS |
| WCC | OPEN | 2026-01-18 | Power Grid Infrastructure | TIER1 | PASS |
| IESC | OPEN | 2026-01-22 | Industrials Manufacturing | TIER1 | PASS |
| STRL | OPEN | 2026-01-22 | AI Cooling & Data Center | TIER1 | PASS |
| AAON | OPEN | 2026-01-22 | AI Cooling & Data Center | TIER1 | PASS |
| GLXY | OPEN | 2026-01-24 | Grid Modernization | TIER1 | PASS |
| AMSC | OPEN | 2026-01-24 | Grid Modernization | TIER1 | PASS |

---

## Appendix B: File Line References

| Component | File | Lines |
|-----------|------|-------|
| Trade dataclass | portfolio_manager.py | 136-238 |
| TradeStatus enum | portfolio_manager.py | 126-129 |
| PortfolioManager class | portfolio_manager.py | 245-873 |
| add_trade() | portfolio_manager.py | 292-319 |
| flag_exit() | portfolio_manager.py | 333-352 |
| update_prices() | portfolio_manager.py | 378-446 |
| check_stop_signals() | portfolio_manager.py | 448-484 |
| _save() (with backup) | portfolio_manager.py | 273-286 |
| export_for_google_sheets() | portfolio_manager.py | 624-672 |
| migrate_from_old_format() | portfolio_manager.py | 772-825 |
| fetch_current_prices() | signal_tracker.py | 119-189 |
| load_historical_signals() | signal_tracker.py | 210-265 |
| find_big_wins() | signal_tracker.py | 274-310 |
| mark_as_celebrated() | signal_tracker.py | 340-351 |
| filter_public_positions() | signal_tracker.py | 690-741 |
| get_recent_closes() | signal_tracker.py | 751-808 |
| get_early_movers() | signal_tracker.py | 811-872 |
