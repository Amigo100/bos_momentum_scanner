# Sterling Signals - P&L Calculation & Performance Tracking Audit

**Document:** `docs/audit/04-pnl-calculation.md`
**Audit Date:** January 29, 2026
**Source Files Audited:** `portfolio_manager.py`, `scanner.py`, `signal_tracker.py`, `newsletter_compiler.py`, `tweet_generator.py`

---

## Table of Contents

1. [P&L Calculation Methodology](#1-pl-calculation-methodology)
2. [Total Return Since Entry](#2-total-return-since-entry)
3. [SPY Benchmark Comparison](#3-spy-benchmark-comparison)
4. [Aggregate Portfolio Metrics](#4-aggregate-portfolio-metrics)
5. [Trailing Stop P&L Impact](#5-trailing-stop-pl-impact)
6. [Worked Examples](#6-worked-examples)
7. [Discrepancies & Concerns](#7-discrepancies--concerns)

---

## 1. P&L Calculation Methodology

### 1.1 Core P&L Formula

All P&L calculations use the same formula throughout the codebase:

```
pnl_pct = ((price_for_calc / entry_price) - 1) × 100
```

**Code:** `portfolio_manager.py:181`
```python
self.pnl_pct = ((price_for_calc / self.entry_price) - 1) * 100
```

Where `price_for_calc` is:
- **Open positions:** `self.current_price` (latest market price)
- **Closed positions:** `self.exit_price` (price at exit)

Determined at `portfolio_manager.py:179`:
```python
price_for_calc = self.exit_price if self.status != "OPEN" else self.current_price
```

### 1.2 Unrealized Gains (Open Positions)

```
Unrealized P&L % = ((current_price / entry_price) - 1) × 100
Unrealized P&L $ = (current_price - entry_price) × 100
```

- `current_price` sourced from yfinance or scanner data
- Dollar P&L **assumes 100 shares per position** (hard-coded at `portfolio_manager.py:182`)

**Aggregate unrealized P&L** (`portfolio_manager.py:573`):
```python
unrealized_pnl = sum(t.pnl_pct for t in open_trades if t.pnl_pct != 0)
```

This is a **sum of percentages**, not a weighted average. A position up +50% and one up +10% yields unrealized_pnl = 60%, not 30%.

### 1.3 Realized Gains (Closed Positions)

```
Realized P&L % = ((exit_price / entry_price) - 1) × 100
Realized P&L $ = (exit_price - entry_price) × 100
```

Exit price is set by `flag_exit()` at the time the position is closed.

### 1.4 FX / Currency Handling

**There is no FX handling anywhere in the codebase.**

All prices are assumed USD. The system:
- Downloads USD-denominated prices from yfinance
- Stores USD prices in portfolio.csv
- Reports P&L in USD terms only
- Has no GBP/USD conversion, FX cost modeling, or multi-currency support

Despite the CLAUDE.md mentioning "UK ISA" in banned terms (suggesting a UK-based operator), the system treats all positions as pure USD. The 0.75-1% FX cost per side mentioned in the audit prompt is **not modeled** anywhere.

> **DISCREPANCY D1:** If the operator trades US stocks from a UK ISA account, the actual realized returns will be lower by ~1.5-2% round-trip FX costs. These costs are invisible to the system.

### 1.5 Position Sizing

**Hard-coded 100 shares per trade** (`portfolio_manager.py:182`):
```python
self.pnl_usd = (price_for_calc - self.entry_price) * 100  # Assumes 100 shares
```

Google Sheets formula mirrors this (`portfolio_manager.py:712`):
```
=IF(B2="OPEN", (G2-D2)*100, IF(F2<>"", (F2-D2)*100, ""))
```

There is no variable position sizing, no position-size field in the Trade dataclass, and no way to record actual share counts.

---

## 2. Total Return Since Entry

### 2.1 Code Path for Computing Current Return %

```
Trade.calculate_metrics(current_price)     [portfolio_manager.py:168]
  │
  ├─ If current_price provided:
  │   └─ self.current_price = current_price   [line 170]
  │
  ├─ Determine price_for_calc:                [line 179]
  │   ├─ OPEN: self.current_price
  │   └─ CLOSED/STOPPED: self.exit_price
  │
  ├─ Calculate P&L:                           [lines 181-182]
  │   ├─ pnl_pct = ((price_for_calc / entry_price) - 1) * 100
  │   └─ pnl_usd = (price_for_calc - entry_price) * 100
  │
  ├─ Calculate stop metrics:                  [lines 185-191]
  │   ├─ stop_level = highest_close * 0.80
  │   ├─ distance_to_stop_pct = (current - stop) / current * 100
  │   └─ stop_alert = distance_to_stop_pct <= 5.0
  │
  └─ Calculate days held:                     [lines 194-201]
      ├─ OPEN: (today - entry_date).days
      └─ CLOSED: (exit_date - entry_date).days
```

### 2.2 How This Drives "Top Performers" Ranking

**In `signal_tracker.py:751-812`**, `get_winners_for_showcase()`:
1. Calls `filter_public_positions()` to remove losers and STOPPED trades
2. Filters to positions above threshold (default 25% P&L)
3. Sorts by `pnl_pct` descending
4. Returns top 5

**In `tweet_generator.py:1430-1481`**, top performers tweets:
- Filters to `pnl_pct >= 15.0` (MARKETING_THRESHOLDS['min_win_to_highlight'])
- Only shows positive P&L positions
- Entry prices only shown for positions above 25% gain
- Holding period required with every P&L figure

**Public content filtering** (`signal_tracker.py:690-741`):
```python
# CRIT-3: Never show stopped positions publicly
if status == 'STOPPED':
    continue
# Only include positions with positive P&L
if pnl_pct >= 0:
    public_positions.append(pos_copy)
```

### 2.3 Age-Based Threshold Logic

**Early movers** (`signal_tracker.py:875-936`):
- Positions held < 14 days
- Must show >= 5% gain
- Used for "early movers" tweet content

**Entry price display rule** (`signal_tracker.py:751`):
- Entry prices only displayed publicly for positions above 25% gain
- Below 25%, entry price hidden to avoid revealing strategy details

**Big win thresholds** (`signal_tracker.py:274-310`):

| Threshold | Celebration Type | Marketing Label |
|-----------|-----------------|-----------------|
| >= 25% | "big_win" | Standard milestone |
| >= 50% | "home_run" | Home run |
| >= 100% | "hall_of_fame" | Hall of fame |

**Watchlist expiry** (`signal_tracker.py:939-981`):
- CONSIDER signals removed after 21 days

---

## 3. SPY Benchmark Comparison

### 3.1 SPY Data Source

**`portfolio_manager.py:490-499`**:
```python
def _load_spy_data(self) -> None:
    self.spy_data = yf.download("SPY", period="2y", progress=False)
```

- Source: yfinance
- Period: 2 years of daily data
- Loaded lazily on first access
- Cached in `self.spy_data` for session duration

### 3.2 SPY Return Calculation

**Fixed-period SPY return** (`portfolio_manager.py:501-513`):
```python
def get_spy_return(self, days: int) -> float:
    end_price = self.spy_data['Close'].iloc[-1]
    start_idx = min(days, len(self.spy_data) - 1)
    start_price = self.spy_data['Close'].iloc[-start_idx - 1]
    return ((end_price / start_price) - 1) * 100
```

**YTD SPY return** (`portfolio_manager.py:515-528`):
```python
def get_spy_ytd_return(self) -> float:
    ytd_data = self.spy_data[self.spy_data.index >= pd.Timestamp(year_start)]
    return ((ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1) * 100
```

### 3.3 Comparison Methodology

**Portfolio vs SPY** is calculated in two different places with different approaches:

**Approach 1: `portfolio_manager.py` (period-based)**

At `get_performance_summary()` (line 611-616):
```python
'alpha': ret_7d - spy_7d    # Simple subtraction
```

- Portfolio return = arithmetic mean of P&L% for trades closed in the period
- SPY return = SPY price change over that calendar period
- Alpha = portfolio - SPY

> **DISCREPANCY D2:** This is NOT a matched holding period comparison. The portfolio return averages closed trade P&L%, while SPY return measures a calendar window. A trade closed on day 3 of a 30-day window is compared to 30 days of SPY, not 3 days.

**Approach 2: `signal_tracker.py` (30-day default)**

At `calculate_portfolio_vs_spy()` (lines 406-487):
```python
portfolio_return = total_pnl / position_count    # Average of ALL open P&L%
spy_return = fetch_spy_return(30)                # SPY over last 30 days
outperformance = portfolio_return - spy_return
```

- Portfolio return = arithmetic mean of ALL open position P&L%
- SPY return = fixed 30-day SPY change
- Used for "Beat SPY" tweet content

> **DISCREPANCY D3:** Open positions may have been held for varying durations (some 5 days, some 60 days), but all are compared to a fixed 30-day SPY return. This inflates alpha for longer-held winners.

### 3.4 What's Missing: Matched Holding Period

The documented strategy (CLAUDE.md) implies comparing each trade's return to what SPY did over the same dates. The code does not implement this. There is no per-trade SPY benchmark calculation like:

```python
# NOT IMPLEMENTED:
spy_entry_price = spy_data.loc[trade.entry_date]['Close']
spy_exit_price = spy_data.loc[trade.exit_date]['Close']
trade_spy_return = ((spy_exit_price / spy_entry_price) - 1) * 100
trade_alpha = trade.pnl_pct - trade_spy_return
```

---

## 4. Aggregate Portfolio Metrics

### 4.1 Total Portfolio Value

**Not calculated.** The system does not track total portfolio value because:
- Position sizes are not recorded (hard-coded 100 shares)
- No cash balance tracking
- No total AUM figure

The closest metric is `unrealized_pnl_pct` which sums individual P&L percentages.

### 4.2 Win Rate

**`portfolio_manager.py:576-578`**:
```python
winners = [t for t in closed_trades if t.pnl_pct > 0]
losers = [t for t in closed_trades if t.pnl_pct < 0]
win_rate = len(winners) / len(closed_trades) * 100 if closed_trades else 0
```

- Based on closed trades only (CLOSED + STOPPED)
- Break-even trades (pnl_pct == 0) are excluded from both winners and losers
- Expressed as percentage

### 4.3 Average Return Calculations

**Average winner** (`portfolio_manager.py:581`):
```python
avg_winner = sum(t.pnl_pct for t in winners) / len(winners) if winners else 0
```

**Average loser** (`portfolio_manager.py:582`):
```python
avg_loser = sum(t.pnl_pct for t in losers) / len(losers) if losers else 0
```

**Period return** (`portfolio_manager.py:530-565`):
```python
returns = [t.pnl_pct for t in relevant if t.pnl_pct != 0]
return sum(returns) / len(returns), len(returns)
```

All use arithmetic mean. No geometric mean, no compounding, no time-weighting.

### 4.4 Risk-Adjusted Metrics

**None implemented.** The system does not calculate:
- Sharpe ratio
- Sortino ratio
- Maximum drawdown (portfolio-level)
- Calmar ratio
- Information ratio
- Standard deviation of returns

The only risk metric is per-position `distance_to_stop_pct`.

### 4.5 Cold Streak Detection

**`signal_tracker.py:1016-1061`** implements a basic cold streak detector:
```python
losses = sum(1 for t in recent_closed[:threshold] if t.pnl_pct < 0)
in_cold_streak = losses >= threshold    # 3+ losses in last 5 trades
```

Used to optionally reduce tweet posting frequency during poor performance.

---

## 5. Trailing Stop P&L Impact

### 5.1 How 20% Trailing Stop Affects Reported Returns

The trailing stop ensures the **maximum loss from peak** is 20%, but the reported P&L is measured from **entry price**, not from peak.

**Example:**
- Entry: $10.00
- Peak (highest_close): $20.00 (+100% from entry)
- Stop triggers at: $16.00 (20% below peak)
- Reported P&L: +60% (from entry)

The stop limits drawdown from peak but does NOT cap the P&L at any particular level from entry.

### 5.2 Hard vs Soft Stops

**The stops are SOFT (alerts only) in terms of broker execution.** The system:

1. **Detects** when `drawdown_pct >= 20%` during the weekly scan (`scanner.py:969`)
2. **Records** the exit in portfolio.csv via `pm.flag_exit()` (`scanner.py:982`)
3. **Does NOT execute** a broker order — there is no broker API integration for order execution

The system records the stop as triggered at the price seen during the scan. The actual exit depends on the operator manually selling at their broker.

> **DISCREPANCY D4:** The recorded `exit_price` is the price at scan time (typically Friday close), not the actual broker execution price. Slippage is not modeled.

### 5.3 BoS Bearish Exit Impact

As documented in audit 02, BoS bearish triggers `flag_exit()` with status CLOSED. The P&L is:
```
pnl_pct = ((price_at_scan / entry_price) - 1) * 100
```

The documented recommendation to "tighten stop to 15%, don't exit" is not implemented — the code auto-exits.

---

## 6. Worked Examples

### Example 1: Open Position (Unrealized Gain)

```
Trade: RCAT
  entry_date:    2026-01-09
  entry_price:   $8.50
  current_price: $13.25
  highest_close: $13.25
  status:        OPEN

Calculations (portfolio_manager.py:181-191):
  price_for_calc = current_price = $13.25  (OPEN, so use current)
  pnl_pct = (($13.25 / $8.50) - 1) × 100 = +55.9%
  pnl_usd = ($13.25 - $8.50) × 100 shares = +$475.00
  stop_level = $13.25 × 0.80 = $10.60
  distance_to_stop = ($13.25 - $10.60) / $13.25 × 100 = 20.0%
  stop_alert = False  (20.0% > 5.0%)
  days_held = (2026-01-29) - (2026-01-09) = 20 days
```

### Example 2: Closed Position (Realized Gain, Manual Exit)

```
Trade: OKLO
  entry_date:    2025-12-01
  entry_price:   $22.00
  exit_date:     2026-01-08
  exit_price:    $28.50
  highest_close: $28.50
  status:        CLOSED

Calculations:
  price_for_calc = exit_price = $28.50  (CLOSED, so use exit)
  pnl_pct = (($28.50 / $22.00) - 1) × 100 = +29.5%
  pnl_usd = ($28.50 - $22.00) × 100 shares = +$650.00
  days_held = (2026-01-08) - (2025-12-01) = 38 days
```

### Example 3: Stopped Position (Trailing Stop Hit)

```
Trade: SMCI
  entry_date:    2025-10-01
  entry_price:   $45.00
  highest_close: $52.00  (peak reached during holding)
  exit_price:    $41.60  (= $52.00 × 0.80, stop triggered)
  status:        STOPPED

Calculations:
  price_for_calc = exit_price = $41.60  (STOPPED, so use exit)
  pnl_pct = (($41.60 / $45.00) - 1) × 100 = -7.6%
  pnl_usd = ($41.60 - $45.00) × 100 shares = -$340.00
  days_held = (exit_date - 2025-10-01)

Note: Despite a 20% drop from peak ($52→$41.60), the loss from entry
is only -7.6% because the stock had risen before reversing.
```

### Example 4: Stopped Position (Underwater from Entry)

```
Trade: VNET
  entry_date:    2026-01-09
  entry_price:   $12.00
  highest_close: $12.00  (never rose above entry)
  exit_price:    $9.60   (= $12.00 × 0.80, stop triggered)
  status:        STOPPED

Calculations:
  pnl_pct = (($9.60 / $12.00) - 1) × 100 = -20.0%
  pnl_usd = ($9.60 - $12.00) × 100 shares = -$240.00

Note: This is the worst-case scenario — stock never rose above entry,
so the full 20% stop loss applies from entry price.
```

### Example 5: Win Rate Calculation

```
Closed trades:
  OKLO:  +29.5%  (winner)
  SMCI:  -7.6%   (loser)
  ABC:   +42.0%  (winner)
  DEF:   -18.0%  (loser)

win_rate = 2 / 4 × 100 = 50.0%
avg_winner = (29.5 + 42.0) / 2 = +35.8%
avg_loser = (-7.6 + -18.0) / 2 = -12.8%
```

### Example 6: SPY Comparison (Showing Methodology Flaw)

```
Period: Last 30 days
  SPY: went from $580 → $600  →  SPY return = +3.4%

Closed trades in last 30 days:
  Trade A: Entered 60 days ago, closed 5 days ago, P&L = +45%
  Trade B: Entered 10 days ago, closed 2 days ago, P&L = +8%

Portfolio return = (45 + 8) / 2 = +26.5%
Alpha = 26.5 - 3.4 = +23.1%

PROBLEM: Trade A was held for 55 days but compared to 30-day SPY.
         A fair comparison would use 55-day SPY return for Trade A
         and 8-day SPY return for Trade B.
```

### Example 7: FX Impact (NOT Modeled)

```
UK ISA investor buying US stocks:

Actual trade (RCAT):
  Entry: $8.50 × (1/GBP:USD 1.27) = £6.69  (+ 0.75% FX fee = £6.74)
  Exit:  $13.25 × (1/GBP:USD 1.27) = £10.43 (- 0.75% FX fee = £10.35)

System-reported P&L: +55.9%
Actual GBP P&L:      (£10.35 / £6.74 - 1) × 100 = +53.6%
FX cost impact:       -2.3% (1.5% round-trip fees + FX rate movement)

Note: If GBP/USD moved during the holding period, the actual
return could be higher or lower than the USD return.
```

---

## 7. Discrepancies & Concerns

### D1: No FX Cost Modeling (MEDIUM)

The system reports pure USD returns. If the operator trades from a non-USD account (e.g., UK ISA), actual returns are lower by ~1.5-2% round-trip FX costs, plus currency fluctuation risk. This is invisible to the system.

**Recommendation:** Add an optional `fx_cost_pct` config parameter and subtract it from realized P&L on exit.

### D2: SPY Comparison Uses Non-Matched Periods (HIGH)

`get_performance_summary()` compares average closed-trade P&L to a fixed calendar window of SPY. Trades held for different durations are all compared to the same SPY window.

**Recommendation:** Calculate per-trade SPY return using the trade's actual entry and exit dates.

### D3: "Beat SPY" Tweet Uses 30-Day Fixed Window (HIGH)

`calculate_portfolio_vs_spy()` averages ALL open position P&L% (regardless of holding period) and compares to 30-day SPY. A position held 90 days with +50% is compared to 30-day SPY of +3%, making the outperformance appear much larger.

**Recommendation:** Use per-position matched-period SPY returns.

### D4: Exit Price Is Scan-Time Price, Not Broker Execution (MEDIUM)

When a trailing stop triggers, the `exit_price` is set to the price observed during the Friday scan. The operator must manually sell at their broker, potentially at a different price (slippage, Monday open gap, etc.).

**Recommendation:** Allow manual override of exit_price via `portfolio_manager.py --exit TICKER --exit-price <actual_fill>`.

### D5: Unrealized P&L Is Sum, Not Average (LOW)

`unrealized_pnl_pct` at line 573 sums all open position P&L percentages. With 6 positions up +10% each, this reports +60%, not +10% average. This is inconsistent with how closed-trade returns are averaged.

**Recommendation:** Report both sum and average, or change to average for consistency.

### D6: Dollar P&L Assumes 100 Shares (MEDIUM)

The `pnl_usd` field hard-codes 100 shares (`portfolio_manager.py:182`). Actual positions may be different sizes. The dollar figures are unreliable unless all positions are exactly 100 shares.

**Recommendation:** Add a `shares` or `position_size` field to the Trade dataclass.

### D7: No Risk-Adjusted Metrics (LOW)

No Sharpe ratio, Sortino ratio, max drawdown, or other risk-adjusted metrics. Alpha is reported as simple portfolio return minus SPY return (not risk-adjusted).

**Recommendation:** Add at minimum a portfolio-level max drawdown and Sharpe ratio.

### D8: Break-Even Trades Excluded from Win Rate (INFO)

Trades with exactly 0% P&L are excluded from both winners and losers counts. This is unlikely in practice but worth noting.

### D9: Arithmetic Mean, Not Geometric (INFO)

All average return calculations use arithmetic mean. For compound returns over time, geometric mean would be more accurate. Example:
- Two trades: +50%, -50%
- Arithmetic mean: 0% (break even)
- Geometric mean: -13.4% (actual compound loss)

### D10: Newsletter Compiler Has Independent P&L Calculation (LOW)

`newsletter_compiler.py:415-449` calculates YTD return independently by fetching prices via `yf.Ticker().info` instead of using portfolio_manager. This could produce different results than `portfolio_manager.py`'s calculation due to timing differences or different price fields.

---

## Appendix: Key Line References

| Item | File | Line(s) |
|------|------|---------|
| Core P&L formula | portfolio_manager.py | 181 |
| Dollar P&L (100 shares) | portfolio_manager.py | 182 |
| calculate_metrics() | portfolio_manager.py | 168-203 |
| get_performance_summary() | portfolio_manager.py | 567-618 |
| calculate_portfolio_return() | portfolio_manager.py | 530-565 |
| get_spy_return() | portfolio_manager.py | 501-513 |
| get_spy_ytd_return() | portfolio_manager.py | 515-528 |
| _load_spy_data() | portfolio_manager.py | 490-499 |
| export_for_google_sheets() | portfolio_manager.py | 624-672 |
| Google Sheets formulas | portfolio_manager.py | 674-766 |
| print_summary() | portfolio_manager.py | 831-873 |
| Newsletter P&L section | scanner.py | 2084-2170 |
| Sell signal P&L display | scanner.py | 1588-1589 |
| calculate_portfolio_vs_spy() | signal_tracker.py | 406-487 |
| find_big_wins() | signal_tracker.py | 274-310 |
| filter_public_positions() | signal_tracker.py | 690-741 |
| get_winners_for_showcase() | signal_tracker.py | 751-812 |
| get_early_movers() | signal_tracker.py | 875-936 |
| detect_cold_streak() | signal_tracker.py | 1016-1061 |
| Win highlights | newsletter_compiler.py | 340-389 |
| Independent YTD calc | newsletter_compiler.py | 415-449 |
| Top performers tweets | tweet_generator.py | 1430-1481 |
| Beat SPY tweets | tweet_generator.py | 1230-1284 |
| TRAILING_STOP_PCT | portfolio_manager.py | 74 |
| STOP_WARNING_PCT | portfolio_manager.py | 75 |

---

*End of P&L Calculation Audit*
