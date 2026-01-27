# Sterling Signals P&L Calculation Audit

**Document:** 04-pnl-calculation.md
**Last Updated:** 2026-01-27
**Status:** Complete

---

## Executive Summary

This audit documents the profit/loss (P&L) calculation methodology and performance tracking systems in Sterling Signals. The system uses straightforward percentage-based calculations with trailing stop mechanics, but has several design choices that users should understand.

### Key Findings

| Finding | Severity | Description |
|---------|----------|-------------|
| PNL-1 | INFO | P&L USD assumes 100 shares per position (not actual holdings) |
| PNL-2 | INFO | Unrealized P&L is simple sum, not weighted by position size |
| PNL-3 | INFO | No FX/currency handling - USD only |
| PNL-4 | MEDIUM | Two SPY comparison methods exist with different results |
| PNL-5 | LOW | Period returns only include closed trades, not open positions |
| PNL-6 | INFO | No Sharpe ratio, max drawdown, or advanced risk metrics |

---

## 1. Core P&L Calculation Methodology

### 1.1 Unrealized P&L (Open Positions)

**Location:** `portfolio_manager.py` lines 177-182

**Formula:**
```python
# Use current price for open positions
price_for_calc = self.current_price

# Percentage P&L
pnl_pct = ((price_for_calc / entry_price) - 1) * 100

# USD P&L (assumes 100 shares)
pnl_usd = (price_for_calc - entry_price) * 100
```

**Implementation:**
```python
# portfolio_manager.py:177-182
price_for_calc = self.exit_price if self.status != "OPEN" else self.current_price

if self.entry_price > 0 and price_for_calc > 0:
    self.pnl_pct = ((price_for_calc / self.entry_price) - 1) * 100
    self.pnl_usd = (price_for_calc - self.entry_price) * 100  # Assumes 100 shares
```

### 1.2 Realized P&L (Closed/Stopped Positions)

**Formula:**
```python
# Use exit price for closed/stopped positions
price_for_calc = exit_price

# Same formula as unrealized
pnl_pct = ((exit_price / entry_price) - 1) * 100
pnl_usd = (exit_price - entry_price) * 100
```

**Note:** Closed and Stopped positions use `exit_price` which is set at time of closure.

### 1.3 "Total Return Since Entry" Calculation

This is the primary metric shown in marketing content.

**Formula:**
```
Total Return % = ((Current Price / Entry Price) - 1) × 100
```

**Worked Example:**
```
Position: VNET
Entry Date: 2026-01-09
Entry Price: $10.40
Current Price: $11.23

Total Return = ((11.23 / 10.40) - 1) × 100
             = (1.0798 - 1) × 100
             = 7.98%
```

---

## 2. P&L USD Calculation Caveat

### 2.1 Fixed 100-Share Assumption

**Issue (PNL-1):** The system assumes 100 shares for all P&L USD calculations.

**Location:** `portfolio_manager.py` line 182

```python
self.pnl_usd = (price_for_calc - self.entry_price) * 100  # Assumes 100 shares
```

**Impact:**
- Dollar amounts shown are notional, not actual
- A $10 stock and a $500 stock both show P&L based on 100 shares
- This is acceptable for percentage-focused marketing but misleading for absolute returns

**Recommendation:** Add explicit note in outputs or calculate based on fixed dollar amount per position.

---

## 3. Aggregate Portfolio Metrics

### 3.1 Unrealized P&L Aggregation

**Location:** `portfolio_manager.py` lines 572-573

```python
unrealized_pnl = sum(t.pnl_pct for t in open_trades if t.pnl_pct != 0)
```

**Issue (PNL-2):** This is a **simple sum**, not an average or weighted value.

**Example:**
```
Position 1: +50%
Position 2: +10%
Position 3: -5%

Simple Sum = 50 + 10 + (-5) = 55%  ← This is what's shown

Correct Average = (50 + 10 - 5) / 3 = 18.33%
```

**Note:** The `calculate_portfolio_vs_spy()` function correctly uses average:
```python
portfolio_return = total_pnl / position_count  # signal_tracker.py:466
```

### 3.2 Win Rate Calculation

**Location:** `portfolio_manager.py` lines 575-578

```python
winners = [t for t in closed_trades if t.pnl_pct > 0]
losers = [t for t in closed_trades if t.pnl_pct < 0]
win_rate = len(winners) / len(closed_trades) * 100 if closed_trades else 0
```

**Formula:**
```
Win Rate = (Number of Winners / Total Closed Trades) × 100
```

**Note:** Positions at exactly 0% P&L are excluded from both winners and losers.

### 3.3 Average Winner/Loser

**Location:** `portfolio_manager.py` lines 580-582

```python
avg_winner = sum(t.pnl_pct for t in winners) / len(winners) if winners else 0
avg_loser = sum(t.pnl_pct for t in losers) / len(losers) if losers else 0
```

**Formula:**
```
Average Winner = Sum of Winning P&L% / Number of Winners
Average Loser = Sum of Losing P&L% / Number of Losers
```

---

## 4. SPY Benchmark Comparison

The system has **two methods** for comparing portfolio performance to SPY:

### 4.1 Method 1: Fixed 30-Day Window (Original)

**Location:** `signal_tracker.py` lines 404-487

**Function:** `calculate_portfolio_vs_spy()`

**How It Works:**
1. Calculate average P&L across all open positions
2. Fetch SPY's return over the **last 30 days** (fixed window)
3. Compare: `outperformance = portfolio_return - spy_return`

```python
# signal_tracker.py:466-469
portfolio_return = total_pnl / position_count if position_count > 0 else 0.0
spy_return = fetch_spy_return(30)  # Fixed 30-day window
outperformance = portfolio_return - spy_return
```

**Issue (PNL-4):** This compares positions held for varying periods (some 2 days, some 2 months) against a fixed 30-day SPY return. This is methodologically flawed.

### 4.2 Method 2: Matched Holding Periods (CRIT-4 Fix)

**Location:** `signal_tracker.py` lines 494-602

**Function:** `calculate_fair_spy_comparison()`

**How It Works:**
1. For each position, fetch SPY return over the **exact same holding period**
2. Calculate alpha for each position: `alpha = position_return - matched_spy_return`
3. Average all alphas (equal weight)

```python
# signal_tracker.py:542-557
# Calculate position return
pos_return = ((current_price / entry_price) - 1) * 100

# Fetch SPY return over the SAME holding period
spy = yf.Ticker("SPY")
spy_hist = spy.history(start=entry_date)
spy_return = ((spy_end / spy_start) - 1) * 100

alpha = pos_return - spy_return
```

**Example:**
```
Position: VNET
Entry Date: 2026-01-09
Entry Price: $10.40
Current Price: $11.23
Position Return: +7.98%

SPY on 2026-01-09: $588.50
SPY Today: $601.20
SPY Return (same period): +2.16%

Alpha (vs matched SPY): 7.98% - 2.16% = +5.82%
```

### 4.3 Threshold for "Beat SPY" Content

**Location:** `signal_tracker.py` line 475-476, `config.py` line 246

```python
threshold = MARKETING_THRESHOLDS.get('spy_outperformance_min', 5.0)
should_post_beat_spy = outperformance >= threshold
```

**Rule:** Only post "Beat SPY" content when outperforming by ≥5%.

---

## 5. Trailing Stop P&L Impact

### 5.1 Stop Level Calculation

**Location:** `portfolio_manager.py` lines 184-186, `config.py` line 71

```python
TRAILING_STOP_PCT = 20.0  # 20% trailing stop

stop_level = highest_close * (1 - TRAILING_STOP_PCT / 100)
           = highest_close * 0.80
```

**Example:**
```
Position: CGON
Entry Price: $53.92
Highest Close: $57.13

Stop Level = $57.13 × 0.80 = $45.70

If price falls to $45.70 or below:
- Status changes to STOPPED
- Exit price locked at current price
- P&L calculated at exit price
```

### 5.2 Distance to Stop Calculation

**Location:** `portfolio_manager.py` lines 188-191

```python
distance_to_stop_pct = ((current_price - stop_level) / current_price) * 100
stop_alert = distance_to_stop_pct <= STOP_WARNING_PCT  # 5%
```

**Example:**
```
Current Price: $54.50
Stop Level: $45.70

Distance to Stop = (($54.50 - $45.70) / $54.50) × 100
                 = ($8.80 / $54.50) × 100
                 = 16.15%

Stop Alert: 16.15% > 5%, so no alert
```

### 5.3 Stop Trigger Logic

**Location:** `portfolio_manager.py` lines 448-484

```python
def check_stop_signals(self, stocks_dict: Dict) -> List[Trade]:
    for trade in self.get_open_positions():
        current_price = stock.price

        # Update highest close (trailing mechanism)
        if current_price > trade.highest_close:
            trade.highest_close = current_price

        # Calculate current stop level
        stop_level = trade.highest_close * (1 - TRAILING_STOP_PCT / 100)

        # Check if stopped out
        if current_price <= stop_level:
            trade.status = "STOPPED"
            trade.exit_date = datetime.now().strftime("%Y-%m-%d")
            trade.exit_price = current_price
```

### 5.4 Stopped Position P&L Example

```
Position: SMCI (hypothetical)
Entry Date: 2025-10-01
Entry Price: $45.00
Highest Close: $52.00 (reached on 2025-11-15)

Stop Level = $52.00 × 0.80 = $41.60

On 2025-12-01, price falls to $36.00 (below stop):
- Status: STOPPED
- Exit Price: $36.00
- Exit Date: 2025-12-01

Final P&L = (($36.00 / $45.00) - 1) × 100 = -20.0%
```

**Note:** The P&L reflects the actual loss at the stop price, not the theoretical -20% stop level. In this example, slippage caused an additional loss (price dropped to $36 before the stop was triggered at $41.60).

---

## 6. Period-Based Return Calculations

### 6.1 calculate_portfolio_return()

**Location:** `portfolio_manager.py` lines 530-565

**Issue (PNL-5):** This function only includes **closed trades**, not open positions.

```python
def calculate_portfolio_return(self, days: Optional[int] = None, ytd: bool = False):
    closed = self.get_closed_trades()  # Only closed!

    if ytd:
        relevant = [t for t in closed if exit_date >= year_start]
    elif days:
        cutoff = datetime.now() - timedelta(days=days)
        relevant = [t for t in closed if exit_date >= cutoff]

    returns = [t.pnl_pct for t in relevant if t.pnl_pct != 0]
    return sum(returns) / len(returns), len(returns)
```

**Impact:**
- "30-day portfolio return" only includes trades closed in the last 30 days
- Open positions (which may be up significantly) are excluded
- This can understate performance when positions are held long-term

### 6.2 Performance Summary Periods

**Location:** `portfolio_manager.py` lines 584-598

```python
periods = {
    '7d':  {'portfolio': ret_7d,  'spy': spy_7d,  'alpha': ret_7d - spy_7d},
    '30d': {'portfolio': ret_30d, 'spy': spy_30d, 'alpha': ret_30d - spy_30d},
    '90d': {'portfolio': ret_90d, 'spy': spy_90d, 'alpha': ret_90d - spy_90d},
    '180d': {'portfolio': ret_180d, 'spy': spy_180d, 'alpha': ret_180d - spy_180d},
    'ytd': {'portfolio': ret_ytd, 'spy': spy_ytd, 'alpha': ret_ytd - spy_ytd},
    '1y':  {'portfolio': ret_365d, 'spy': spy_365d, 'alpha': ret_365d - spy_365d},
}
```

---

## 7. FX/Currency Handling

### 7.1 Current State (PNL-3)

**No FX handling exists.** The system is USD-only.

**Evidence:**
- No currency fields in Trade dataclass
- No conversion functions in portfolio_manager.py
- No currency columns in portfolio.csv

**Impact:**
- All prices assumed to be USD
- International users must manually convert
- ADRs and foreign tickers work fine (prices are in USD via US exchanges)

---

## 8. Missing Advanced Metrics (PNL-6)

The following metrics are **not implemented**:

| Metric | Status | Notes |
|--------|--------|-------|
| Sharpe Ratio | Not Implemented | Would require risk-free rate and volatility |
| Sortino Ratio | Not Implemented | Downside deviation not tracked |
| Max Drawdown | Not Implemented | Peak-to-trough tracking not implemented |
| Calmar Ratio | Not Implemented | Requires max drawdown |
| Beta (Portfolio) | Not Implemented | Individual stock betas exist, not portfolio beta |
| Information Ratio | Not Implemented | Would require tracking error calculation |

**Recommendation:** For a weekly momentum system with 3-8 month holds, these metrics may add unnecessary complexity. Win rate and average winner/loser are appropriate for the strategy.

---

## 9. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         P&L CALCULATION DATA FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

              ┌─────────────┐
              │ portfolio.  │
              │    csv      │
              └──────┬──────┘
                     │
                     ▼
          ┌──────────────────────┐
          │   PortfolioManager   │
          │       _load()        │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐        ┌──────────────────┐
          │   Trade.from_csv_    │        │    yfinance      │
          │       row()          │        │ (current prices) │
          └──────────┬───────────┘        └────────┬─────────┘
                     │                             │
                     ▼                             ▼
          ┌──────────────────────────────────────────────────┐
          │            Trade.calculate_metrics()              │
          │                                                   │
          │  Inputs:                                          │
          │  - entry_price (from CSV)                         │
          │  - current_price (from yfinance)                  │
          │  - exit_price (if closed, from CSV)               │
          │  - highest_close (from CSV, updated live)         │
          │                                                   │
          │  Outputs:                                         │
          │  - pnl_pct = ((price / entry) - 1) × 100         │
          │  - pnl_usd = (price - entry) × 100               │
          │  - stop_level = highest × 0.80                   │
          │  - distance_to_stop_pct                          │
          │  - days_held                                      │
          └──────────────────────────────────────────────────┘
                     │
                     ├─────────────────────────────────────────────┐
                     ▼                                             ▼
          ┌──────────────────────┐                      ┌─────────────────────┐
          │ get_performance_     │                      │ calculate_portfolio │
          │    summary()         │                      │    _vs_spy()        │
          │                      │                      │                     │
          │ - unrealized_pnl_pct │                      │ - portfolio_return  │
          │ - win_rate           │                      │ - spy_return        │
          │ - avg_winner         │                      │ - outperformance    │
          │ - avg_loser          │                      │ - should_post_      │
          │ - period returns     │                      │     beat_spy        │
          └──────────────────────┘                      └─────────────────────┘
```

---

## 10. Worked Examples

### 10.1 Current Portfolio P&L Calculations

Using actual positions from `portfolio.csv` (as of 2026-01-27):

#### Position 1: VNET

```
Entry Date:     2026-01-09
Entry Price:    $10.40
Highest Close:  $11.23
Status:         OPEN

Assuming Current Price = $10.85:

P&L % = ((10.85 / 10.40) - 1) × 100
      = (1.0433 - 1) × 100
      = +4.33%

P&L USD = (10.85 - 10.40) × 100
        = $0.45 × 100
        = $45.00 (assuming 100 shares)

Stop Level = $11.23 × 0.80 = $8.98

Distance to Stop = ((10.85 - 8.98) / 10.85) × 100
                 = 17.24%
```

#### Position 2: CGON

```
Entry Date:     2026-01-09
Entry Price:    $53.92
Highest Close:  $57.13
Status:         OPEN

Assuming Current Price = $55.50:

P&L % = ((55.50 / 53.92) - 1) × 100
      = (1.0293 - 1) × 100
      = +2.93%

P&L USD = (55.50 - 53.92) × 100
        = $1.58 × 100
        = $158.00 (assuming 100 shares)

Stop Level = $57.13 × 0.80 = $45.70

Distance to Stop = ((55.50 - 45.70) / 55.50) × 100
                 = 17.66%
```

#### Position 3: INOD (New Entry)

```
Entry Date:     2026-01-18
Entry Price:    $61.54
Highest Close:  $61.54 (same as entry - no move yet)
Status:         OPEN

Assuming Current Price = $63.00:

P&L % = ((63.00 / 61.54) - 1) × 100
      = (1.0237 - 1) × 100
      = +2.37%

P&L USD = (63.00 - 61.54) × 100
        = $1.46 × 100
        = $146.00 (assuming 100 shares)

Note: Since current price > highest_close, highest_close would update to $63.00
New Stop Level = $63.00 × 0.80 = $50.40
```

### 10.2 Portfolio Aggregate Example

Using 3 positions above:

```
Position Breakdown:
  VNET:  +4.33%
  CGON:  +2.93%
  INOD:  +2.37%

Simple Sum (used in unrealized_pnl_pct):
  4.33 + 2.93 + 2.37 = 9.63%

Average (used in portfolio_vs_spy):
  9.63 / 3 = 3.21%
```

### 10.3 SPY Comparison Example (Matched Periods)

```
Position: VNET
Entry Date: 2026-01-09
Position Return: +4.33%

SPY Data:
  2026-01-09 Close: $590.00
  2026-01-27 Close: $602.00
  SPY Return (same period): ((602 / 590) - 1) × 100 = +2.03%

Alpha = 4.33% - 2.03% = +2.30%

---

Position: CGON
Entry Date: 2026-01-09
Position Return: +2.93%

SPY Return (same period): +2.03%

Alpha = 2.93% - 2.03% = +0.90%

---

Portfolio Alpha (average):
  (2.30 + 0.90) / 2 = +1.60%

Since 1.60% < 5.0% (threshold), beat_spy content is BLOCKED.
```

### 10.4 Stopped Position Example

```
Hypothetical Position: XYZ
Entry Date:     2026-01-01
Entry Price:    $100.00
Highest Close:  $115.00 (reached 2026-01-10)

Stop Level = $115.00 × 0.80 = $92.00

Price Movement:
  2026-01-01: $100.00 (entry)
  2026-01-10: $115.00 (peak, highest_close updates)
  2026-01-15: $105.00 (still above stop)
  2026-01-20: $92.00  (hits stop level)

At Stop Trigger:
  Status: OPEN → STOPPED
  Exit Date: 2026-01-20
  Exit Price: $92.00

Final P&L % = ((92.00 / 100.00) - 1) × 100
            = -8.0%

Note: Loss is -8%, not -20%, because the position peaked at $115
before falling back. The 20% stop is from the HIGH ($115), not entry.
```

---

## 11. Celebration/Milestone Tracking

### 11.1 Thresholds

**Location:** `config.py` lines 292-298

```python
CELEBRATION_THRESHOLDS: List[float] = [25.0, 50.0, 100.0]

CELEBRATION_KEYS: Dict[float, str] = {
    25.0: '25_pct_celebrated',   # Big Win
    50.0: '50_pct_celebrated',   # Home Run
    100.0: '100_pct_celebrated', # Hall of Fame
}
```

### 11.2 Milestone Detection

**Location:** `config.py` lines 673-682

```python
def get_next_milestone(pnl_pct: float, celebrated: Dict) -> Optional[float]:
    """Get next uncelebrated milestone for a position."""
    for threshold in sorted(CELEBRATION_THRESHOLDS, reverse=True):
        if pnl_pct >= threshold:
            key = CELEBRATION_KEYS[threshold]
            if not celebrated.get(key):
                return threshold
    return None
```

**Example:**
```
Position: RCAT
P&L: +55%
Previously celebrated: 25%

Check 100%: 55% < 100%, skip
Check 50%:  55% >= 50%, 50_pct_celebrated = False
→ Return 50.0 (50% milestone ready to celebrate)
```

---

## 12. Issues Summary and Recommendations

### 12.1 Issues Identified

| ID | Severity | Description | Location |
|----|----------|-------------|----------|
| PNL-1 | INFO | USD P&L assumes 100 shares | portfolio_manager.py:182 |
| PNL-2 | INFO | Unrealized P&L is simple sum | portfolio_manager.py:573 |
| PNL-3 | INFO | No FX handling (USD only) | N/A |
| PNL-4 | MEDIUM | Two SPY methods give different results | signal_tracker.py |
| PNL-5 | LOW | Period returns exclude open positions | portfolio_manager.py:536 |
| PNL-6 | INFO | No Sharpe/drawdown metrics | N/A |

### 12.2 Recommendations

**PNL-4 (MEDIUM):** Standardize on `calculate_fair_spy_comparison()` for all SPY comparisons. The fixed 30-day window method is methodologically flawed.

**PNL-5 (LOW):** Consider adding a "total return" metric that includes mark-to-market values of open positions alongside closed trade returns.

**PNL-1/PNL-2:** Add documentation notes in output files clarifying these assumptions.

---

## 13. Code Reference Quick Index

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `Trade.calculate_metrics()` | portfolio_manager.py | 168-203 | Core P&L calculation |
| `check_stop_signals()` | portfolio_manager.py | 448-484 | Trailing stop logic |
| `calculate_portfolio_return()` | portfolio_manager.py | 530-565 | Period returns (closed only) |
| `get_performance_summary()` | portfolio_manager.py | 567-618 | Aggregate metrics |
| `calculate_portfolio_vs_spy()` | signal_tracker.py | 404-487 | Fixed 30-day SPY comparison |
| `calculate_fair_spy_comparison()` | signal_tracker.py | 494-602 | Matched period SPY comparison |
| `fetch_spy_return()` | signal_tracker.py | 192-203 | SPY data fetch |
| `should_post_beat_spy()` | signal_tracker.py | 609-612 | Beat SPY safeguard check |

---

## 14. Configuration Constants

| Constant | Value | File | Line | Purpose |
|----------|-------|------|------|---------|
| `TRAILING_STOP_PCT` | 20.0 | config.py | 71 | Trailing stop percentage |
| `STOP_WARNING_PCT` | 5.0 | config.py | 72 | Alert when within 5% of stop |
| `spy_outperformance_min` | 5.0 | config.py | 246 | Min alpha for beat_spy posts |
| `min_win_to_highlight` | 15.0 | config.py | 242 | Min P&L for top_performers |
| `big_win_threshold` | 25.0 | config.py | 243 | Milestone celebration tier 1 |

---

## Appendix A: Full P&L Calculation Flow

```
1. Load Trade from CSV
   └─ entry_price, highest_close, status, exit_price (if closed)

2. Fetch Current Price (for OPEN positions)
   └─ yfinance.download() for current market price

3. Determine price_for_calc
   └─ OPEN: current_price
   └─ CLOSED/STOPPED: exit_price

4. Calculate P&L Percentage
   └─ pnl_pct = ((price_for_calc / entry_price) - 1) × 100

5. Calculate P&L USD
   └─ pnl_usd = (price_for_calc - entry_price) × 100

6. Update highest_close (OPEN only)
   └─ If current_price > highest_close: highest_close = current_price

7. Calculate Stop Level
   └─ stop_level = highest_close × 0.80

8. Calculate Distance to Stop
   └─ distance = ((current_price - stop_level) / current_price) × 100

9. Check Stop Alert
   └─ stop_alert = (distance <= 5%)

10. Calculate Days Held
    └─ OPEN: today - entry_date
    └─ CLOSED: exit_date - entry_date
```

---

*Document generated: 2026-01-27*
*Audit scope: P&L calculation, performance tracking, SPY comparison*
