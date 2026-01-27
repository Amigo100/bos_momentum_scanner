# Sterling Signals - Signal Detection System Audit

**Document:** `docs/audit/02-signal-detection.md`
**Audit Date:** January 28, 2026
**System Version:** BoS Momentum Scanner v2.x

---

## Executive Summary

The Sterling Signals scanner uses a **5-Gate entry system** with **dual exit triggers**. This document traces every condition that generates BUY or SELL signals, the code paths involved, and validates backtesting findings against live implementation.

**Key Finding:** The system is well-implemented with proper alternating signal logic. However, the documented "10% baseline entry" feature was NOT found in code, and the backtested exit strategy (trailing stop) contradicts the marketed "BoS exit" approach.

---

## Table of Contents

1. [BUY Signal Conditions](#1-buy-signal-conditions)
2. [SELL Signal Conditions](#2-sell-signal-conditions)
3. [Code Path Tracing](#3-code-path-tracing)
4. [Anti-Whipsaw Mechanisms](#4-anti-whipsaw-mechanisms)
5. [Backtesting Validation](#5-backtesting-validation)
6. [Truth Tables](#6-truth-tables)
7. [Discrepancies & Concerns](#7-discrepancies--concerns)

---

## 1. BUY Signal Conditions

### 1.1 Overview: 5-Gate Entry System

A stock must pass ALL 5 gates to generate a "TEAL signal" (BUY):

```
GATE 1: Beta >= 1.5           [Technical - Mandatory]
GATE 2: Weekly BoS UP         [Technical - Mandatory]
GATE 3: Banker >= 55          [Technical - Mandatory]
GATE 4: Theme Fit             [LLM - Optional via --no-llm]
GATE 5: Gatekeeper PASS       [LLM - Optional via --no-llm]
```

---

### 1.2 Gate 1: Beta Requirement

**Threshold:** `Beta >= 1.5`

**Location:** `config.py` line 75, `scanner.py` lines 283-297

**Calculation Formula:**
```python
def calculate_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Beta = Covariance(stock, SPY) / Variance(SPY)

    Period: 1 year daily data
    Minimum data points: 60 trading days
    Benchmark: SPY (S&P 500 ETF)
    """
    aligned = pd.DataFrame({'stock': returns, 'bench': benchmark_returns}).dropna()
    if len(aligned) < 60:
        return 0.0

    cov = aligned['stock'].cov(aligned['bench'])
    var = aligned['bench'].var()
    beta = cov / var
    return round(float(beta), 2)
```

**Rationale:** High-beta stocks (>1.5) amplify market moves, providing better momentum opportunities.

**Typical Filter Rate:** ~52% pass (937 tickers → ~485 with Beta >= 1.5)

---

### 1.3 Gate 2: Weekly HMA Pivot BoS (Break of Structure)

**Condition:** `bos_bullish == True` (Weekly BoS UP)

**Location:** `scanner.py` lines 385-490

#### 1.3.1 HMA Calculation

**Formula:** `HMA(n) = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))`

**Parameters:**
- Period: `n = 21` (weekly bars)
- Input: `HL2 = (High + Low) / 2`
- Timeframe: Weekly (resampled from daily at Friday close)

```python
def calculate_hma(data: pd.Series, length: int = 21) -> pd.Series:
    """Hull Moving Average - smoother than SMA/EMA, less lag."""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))

    wma_half = data.rolling(half_length).apply(wma_weights, raw=True)
    wma_full = data.rolling(length).apply(wma_weights, raw=True)

    raw_hma = 2 * wma_half - wma_full
    hma = raw_hma.rolling(sqrt_length).apply(wma_weights, raw=True)
    return hma
```

#### 1.3.2 Pivot Detection

**Function:** `find_pivots()` (scanner.py lines 361-382)

**Parameters:**
- Lookback window: `k = 1` (1 bar on each side)
- Confirmation delay: 1 bar (signal confirmed after pivot forms)

**Logic:**
```python
def find_pivots(series: pd.Series, k: int = 1) -> Tuple[pd.Series, pd.Series]:
    """
    Pivot HIGH: HMA[i] > HMA[i-1] AND HMA[i] > HMA[i+1]
    Pivot LOW:  HMA[i] < HMA[i-1] AND HMA[i] < HMA[i+1]
    """
    pivot_highs = pd.Series(np.nan, index=series.index)
    pivot_lows = pd.Series(np.nan, index=series.index)

    for i in range(k, len(series) - k):
        # Check for pivot high
        is_high = all(series.iloc[i] > series.iloc[i-j] for j in range(1, k+1))
        is_high &= all(series.iloc[i] > series.iloc[i+j] for j in range(1, k+1))
        if is_high:
            pivot_highs.iloc[i] = series.iloc[i]

        # Check for pivot low
        is_low = all(series.iloc[i] < series.iloc[i-j] for j in range(1, k+1))
        is_low &= all(series.iloc[i] < series.iloc[i+j] for j in range(1, k+1))
        if is_low:
            pivot_lows.iloc[i] = series.iloc[i]

    return pivot_highs, pivot_lows
```

#### 1.3.3 BoS Signal Generation

**Function:** `calculate_bos()` (scanner.py lines 385-490)

**Step Lines:**
- Upper step line = Most recent pivot HIGH value (carried forward)
- Lower step line = Most recent pivot LOW value (carried forward)

**Signal Definition:**
```python
# BUY Signal (bos_bullish = True)
# Lower step line CHANGED = New pivot low formed on HMA
bos_up = (
    not pd.isna(current_lower) and
    not pd.isna(prev_lower) and
    current_lower != prev_lower
)

# SELL Signal (bos_bearish = True)
# Upper step line CHANGED = New pivot high formed on HMA
bos_down = (
    not pd.isna(current_upper) and
    not pd.isna(prev_upper) and
    current_upper != prev_upper
)
```

**Data Requirements:**
- Minimum daily bars: 60 (line 411)
- Minimum weekly bars: `hma_length + pivot_k + 5 = 27` weeks

**Typical Filter Rate:** ~10% of high-beta stocks pass (485 → ~48 with BoS UP)

---

### 1.4 Gate 3: Banker Indicator (Institutional Accumulation)

**Threshold:** `Banker >= 55`

**Location:** `scanner.py` lines 300-330, `config.py` lines 76-78

**Formula:**
```python
def calculate_banker(df: pd.DataFrame, period: int = 20) -> float:
    """
    Banker measures deviation from 20-day VWAP, scaled to 50-centered score.

    Formula: banker = 50 + ((close / vwap_20d - 1) * 100 * 5)

    Where:
    - vwap_20d = sum(typical_price * volume) / sum(volume) over 20 days
    - typical_price = (High + Low + Close) / 3
    """
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()

    deviation_pct = (df['Close'].iloc[-1] / vwap.iloc[-1] - 1) * 100
    banker = 50 + (deviation_pct * 5)

    return round(banker, 1)
```

**Tier Assignment:**

| Banker Score | VWAP Deviation | Tier | Meaning |
|--------------|----------------|------|---------|
| > 70 | +4% above | TIER1 | Strong institutional accumulation |
| 60-70 | +2-4% above | TIER2 | Moderate accumulation |
| 55-60 | +1-2% above | TIER3 | Slight accumulation (entry minimum) |
| < 55 | < +1% | - | Insufficient accumulation |

**Typical Filter Rate:** ~92% of BoS UP stocks pass (48 → ~44 with Banker >= 55)

---

### 1.5 Gate 4: Thematic Analyzer (LLM)

**Condition:** `theme_verdict in ["STRONG FIT", "GOOD FIT"]`

**Location:** `scanner.py` lines 614-756, `thematic_analyzer.py`

**Process:**
1. LLM identifies top 5 investment themes
2. Each stock mapped to best-fit theme
3. Theme fit scored: STRONG FIT, GOOD FIT, MODERATE FIT, POOR FIT

**Theme Classification Thresholds:**

| Theme Score | Classification | Actionable? |
|-------------|---------------|-------------|
| >= 7.5 | PRIME | Yes |
| 6.0 - 7.5 | INVESTABLE | Yes |
| 4.5 - 6.0 | SELECTIVE | Watchlist |
| < 4.5 | AVOID | No |

**Fields Added:**
- `stock.theme` - Theme name
- `stock.theme_score` - 0-10 composite score
- `stock.pure_play_score` - 0-100% theme purity
- `stock.theme_verdict` - STRONG/GOOD/MODERATE/POOR FIT

**Typical Filter Rate:** ~39% pass (44 technical → ~17 theme-confirmed)

---

### 1.6 Gate 5: Gatekeeper (LLM Final Quality Gate)

**Condition:** `final_decision == "PASS"`

**Location:** `scanner.py` lines 763-896, `gatekeeper.py`

**Analysis Per Stock:**
1. **Catalyst Check:** Earnings, events within 90 days
2. **Red Flag Scan:** Auditor issues, insider selling, SEC investigations
3. **Sentiment Analysis:** Analyst trends, short interest
4. **Conviction Score:** 1-5 assessment

**Decision Matrix:**

| Decision | Mapped To | Meaning | Action |
|----------|-----------|---------|--------|
| PASS | `final_decision = "PASS"` | All clear | Enter position |
| CAUTION | `final_decision = "CONSIDER"` | Some concerns | Watchlist only |
| FAIL | Filtered out | Red flags | Skip entirely |

**Immediate Disqualifiers (→ FAIL):**
- Auditor resignation or delayed 10-K
- CFO/CEO departure within 60 days
- Shelf offering (S-3) filed in last 30 days
- Active SEC/DOJ investigation
- Earnings in < 5 trading days

**Typical Filter Rate:** ~35-40% get PASS (17 → 6-7 TEAL signals)

---

### 1.7 Complete BUY Signal Requirements Summary

```
TEAL SIGNAL (BUY) = ALL of:
├─ Beta >= 1.5
├─ Weekly HMA Pivot BoS UP (lower step line changed)
├─ Banker >= 55 (1%+ above 20-day VWAP)
├─ Theme: STRONG FIT or GOOD FIT (with --llm)
└─ Gatekeeper: PASS decision (with --llm)
```

---

## 2. SELL Signal Conditions

### 2.1 Overview: Dual Exit System

The system has **two independent exit triggers**:

```
EXIT 1 (PRIMARY):   20% Trailing Stop from highest close
EXIT 2 (ADVISORY):  Weekly BoS DOWN → Tighten stop to 15%
```

**Important:** Backtesting showed trailing stop (+539% returns) >> signal exits (+294% returns).

---

### 2.2 Primary Exit: 20% Trailing Stop

**Threshold:** `TRAILING_STOP_PCT = 20.0`

**Location:** `config.py` line 71, `scanner.py` lines 969, 1035

**Implementation:**

```python
def check_trailing_stop(trade: Trade, current_price: float) -> Tuple[bool, str]:
    """
    Check if position hit 20% trailing stop.

    Stop level = highest_close * (1 - 0.20)
    Triggered when: current_price <= stop_level
    """
    if trade.highest_close <= 0:
        return False, ""

    drawdown_pct = ((trade.highest_close - current_price) / trade.highest_close) * 100

    if drawdown_pct >= TRAILING_STOP_PCT:  # 20.0
        return True, f"Trailing stop hit ({drawdown_pct:.1f}% from high of ${trade.highest_close:.2f})"

    return False, ""
```

**Highest Close Tracking:**
- Updated in `portfolio_manager.py` lines 464-465
- `highest_close = max(highest_close, current_price)` on each update

**Example:**
```
Entry: $100
Peak (highest_close): $150
Stop level: $150 * 0.80 = $120
Current: $118 → STOPPED (21.3% drawdown)
```

---

### 2.3 Advisory Exit: Weekly BoS DOWN

**Condition:** `bos_bearish == True`

**Location:** `scanner.py` lines 965, 1593-1597

**Logic:**
```python
if stock.bos_bearish:
    sell_reason = "Weekly BoS Down (price breaking structure low)"
    # ADVISORY: Tighten stop to 15%, do NOT auto-exit
```

**CRITICAL NOTE:** This is NOT an automatic exit trigger!
```python
# From scanner.py lines 1593-1597:
print(f"  EXIT STRATEGY (Backtested +539% avg vs +294% with signal exits):")
print(f"    • USE: 20% trailing stop from highest weekly close")
print(f"    • CAUTION: HMA Pivot SELL = tighten stop to 15%, don't exit")
print(f"    • DO NOT automatically exit on SELL signal")
```

**Action on BoS DOWN:**
1. Issue caution alert
2. Tighten stop from 20% → 15% (advisory)
3. Continue holding until trailing stop hits

---

### 2.4 Stop Tightening Logic

**Thresholds:**
- Normal stop: `TRAILING_STOP_PCT = 20.0%`
- Tightened stop: `TIGHTEN_STOP_PCT = 15.0%`
- Warning zone: `STOP_WARNING_PCT = 5.0%` (alert when within 5% of stop)

**Location:** `config.py` lines 71-73

---

### 2.5 Manual Exit Capabilities

**Function:** `portfolio_manager.py` → `flag_exit()`

```python
def flag_exit(self, ticker: str, exit_price: float, reason: str = "Manual exit"):
    """
    Manually exit a position.

    Sets:
    - status = "CLOSED" (manual) or "STOPPED" (trailing stop)
    - exit_date = today
    - exit_price = provided price
    - notes += reason
    """
```

**CLI Usage:**
```bash
python portfolio_manager.py --exit TICKER --exit-price 15.00 --reason "Taking profits"
```

---

### 2.6 Time-Based Exit Rules

**Finding:** NO time-based exit rules exist in the codebase.

- No maximum holding period
- No forced exit after X weeks/months
- Positions can be held indefinitely until stop hit

---

### 2.7 Complete SELL Signal Requirements Summary

```
EXIT TRIGGER = ANY of:
├─ 20% Trailing Stop: current_price <= highest_close * 0.80
└─ Manual Exit: User-initiated via CLI or direct CSV edit

ADVISORY (Non-Exit):
└─ Weekly BoS DOWN: Tighten stop to 15%, issue alert
```

---

## 3. Code Path Tracing

### 3.1 BUY Signal Path: Raw Data → Signal → Portfolio

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Data Download                                           │
│ Function: download_and_process() [scanner.py:524-607]           │
│ Input: List of ticker symbols                                   │
│ Output: Dict[str, Stock] with indicators calculated             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Calculate Beta                                          │
│ Function: calculate_beta() [scanner.py:283-297]                 │
│ For each stock: stock.beta = cov(returns, SPY) / var(SPY)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Calculate Banker                                        │
│ Function: calculate_banker() [scanner.py:300-330]               │
│ For each stock: stock.banker = 50 + (deviation_from_vwap * 5)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Calculate Weekly BoS                                    │
│ Function: calculate_bos() [scanner.py:385-490]                  │
│ For each stock:                                                 │
│   - Resample daily → weekly                                     │
│   - Calculate HMA(21) on HL2                                    │
│   - Find pivots (k=1)                                           │
│   - Build step lines                                            │
│   - stock.bos_bullish = (lower_step_line changed)               │
│   - stock.bos_bearish = (upper_step_line changed)               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Technical Gate Filter                                   │
│ Location: [scanner.py:1341-1373]                                │
│ Filter: beta >= 1.5 AND bos_bullish AND banker >= 55            │
│ Output: technical_signals list                                  │
│ Side effect: Assign tier (TIER1/2/3) based on banker            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Thematic Analyzer (Optional)                            │
│ Function: run_thematic_gate() [scanner.py:614-756]              │
│ For each technical signal:                                      │
│   - Map to best-fit theme                                       │
│   - Score theme alignment                                       │
│   - Filter: STRONG FIT or GOOD FIT only                         │
│ Output: theme_confirmed list                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Gatekeeper (Optional)                                   │
│ Function: run_gatekeeper() [scanner.py:763-896]                 │
│ For each theme-confirmed signal:                                │
│   - Analyze catalysts, red flags, sentiment                     │
│   - Assign: PASS / CONSIDER / FAIL                              │
│ Output: confirmed list (PASS + CONSIDER only)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: Record to Portfolio                                     │
│ Function: add_trade_from_stock() [portfolio_manager.py:321-331] │
│ For each PASS signal:                                           │
│   - Create Trade object from Stock                              │
│   - Set status = "OPEN"                                         │
│   - Set entry_date = today                                      │
│   - Set entry_price = current price                             │
│   - Append to portfolio.csv                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: Record to signals.json                                  │
│ Function: save_results() [scanner.py:2700+]                     │
│ Write: buy_signals[], sell_signals[], themes[], stats{}         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 SELL Signal Path: Position Check → Exit → Update

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Open Positions                                     │
│ Function: get_open_positions() [portfolio_manager.py]           │
│ Read: portfolio.csv where status == "OPEN"                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Check Each Position                                     │
│ Function: check_sell_signals() [scanner.py:913-1072]            │
│ For each open position:                                         │
│   a) Get current price (yfinance)                               │
│   b) Check if stock has bos_bearish (BoS DOWN)                  │
│   c) Calculate drawdown from highest_close                      │
│   d) If drawdown >= 20%: Create SellSignal                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Flag Exit in Portfolio                                  │
│ Function: flag_exit() [portfolio_manager.py:333-352]            │
│ Update:                                                         │
│   - status = "STOPPED"                                          │
│   - exit_date = today                                           │
│   - exit_price = current price                                  │
│   - notes += exit reason                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Save Updated Portfolio                                  │
│ Function: _save() [portfolio_manager.py:273-286]                │
│ Write: Updated portfolio.csv                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Record to signals.json                                  │
│ Append to sell_signals[] array                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Anti-Whipsaw Mechanisms

### 4.1 HMA Pivot Alternating Signal Logic

**The primary anti-whipsaw mechanism is INHERENT in the HMA pivot detection.**

**How it works:**

```
Time →    T1      T2      T3      T4      T5
HMA:      /\      __      \/      __      /\
         HIGH    ---     LOW     ---    HIGH

Signals:   -      SELL     -      BUY      -
                  (H)            (L)

The system ALTERNATES between:
- Pivot HIGH (potential SELL)
- Pivot LOW (potential BUY)

You CANNOT get consecutive BUYs or SELLs because:
- After a LOW pivot (BUY), HMA must make a HIGH before another LOW
- After a HIGH pivot (SELL), HMA must make a LOW before another HIGH
```

**Code Location:** `scanner.py` lines 464-469

```python
# These are MUTUALLY EXCLUSIVE due to pivot detection
bos_up = (lower_step_line changed)   # BUY - requires new pivot LOW
bos_down = (upper_step_line changed) # SELL - requires new pivot HIGH
```

### 4.2 Pivot Confirmation Delay

**The `k=1` lookback creates a 1-bar confirmation delay:**

- Pivot is only confirmed when the NEXT bar shows direction change
- This prevents premature signals on temporary reversals
- For weekly timeframe: 1-week delay after pivot forms

### 4.3 CONSIDER Signal Expiry

**Location:** `signal_tracker.py` lines 875-917

```python
def filter_expired_consider_signals(signals: List[Dict], max_age_days: int = 21) -> List[Dict]:
    """
    Remove CONSIDER signals older than 21 days.
    Prevents stale watchlist stocks from being repeatedly mentioned.
    """
```

### 4.4 Rate Limiting (API Protection)

**Location:** `config.py` lines 104-107

```python
INTER_STEP_DELAY = 30.0      # 30 sec between analyzer and gatekeeper
INTER_STOCK_DELAY = 8.0      # 8 sec between gatekeeper calls
RATE_LIMIT_COOLDOWN = 60.0   # 60 sec cooldown on rate limit error
BACKOFF_FACTOR = 2.0         # Exponential backoff multiplier
```

### 4.5 Ticker Mention Limits (Content Generation)

**Location:** `config.py` lines 47-51

```python
TICKER_LIMITS = {
    'max_mentions_per_week': 4,        # Can't mention same ticker > 4x/week
    'max_consecutive_days': 2,         # Can't mention same ticker 3+ days in row
    'cooldown_after_milestone': 2,     # 2-day cooldown after milestone celebration
}
```

---

## 5. Backtesting Validation

### 5.1 HMA Pivot Entries vs Breakout Entries

**Documented Preference:** HMA Pivot entries preferred over breakout entries

**Code Validation:** ✅ CONFIRMED

**Location:** `scanner.py` lines 388-396 (comments)

```python
# NOTE: We use HMA PIVOT method which produces alternating B-S-B-S signals
# Alternative "price crossing step line" method does NOT alternate properly
# and produces unreliable entry/exit signals
```

**Implementation:** The system ONLY uses HMA pivot-based signals, not price crossovers.

---

### 5.2 Entry Within 10% of HMA Baseline

**Documented Preference:** Entry within 10% of HMA baseline

**Code Validation:** ❌ NOT FOUND

**Search Results:** No code implements a "10% of HMA baseline" filter.

**Possible Explanations:**
1. Feature was removed in a prior version
2. Documentation refers to a different system
3. Banker indicator (VWAP-based) serves similar purpose

**Closest Equivalent:** Banker indicator measures deviation from 20-day VWAP, providing similar "not too extended" filtering.

---

### 5.3 Fresh Trends Under 4 Weeks

**Documented Preference:** Prioritize trends under 4 weeks old

**Code Validation:** ⚠️ REMOVED

**Location:** `scanner.py` lines 127-131, 189-195

```python
# BACKTEST RESULT: 4-week momentum filter REDUCED returns
# from +9.2% to +6.1% across 4000+ stocks

def passes_momentum_filter(stock: Stock) -> bool:
    """DEPRECATED: Always returns True - filter disabled"""
    return True  # Filter removed based on backtest results
```

**Current State:** 4-week momentum is TRACKED but NOT FILTERED. The `passes_momentum_filter()` function always returns True.

---

### 5.4 BoS Bearish Exit Preference

**Documented Preference:** Exit on BoS Bearish signal

**Code Validation:** ⚠️ CONTRADICTED BY BACKTEST

**Location:** `scanner.py` lines 1593-1597

```python
print(f"  EXIT STRATEGY (Backtested +539% avg vs +294% with signal exits):")
print(f"    • USE: 20% trailing stop from highest weekly close")
print(f"    • CAUTION: HMA Pivot SELL = tighten stop to 15%, don't exit")
print(f"    • DO NOT automatically exit on SELL signal")
```

**Actual Implementation:**
- BoS Bearish triggers an ADVISORY (tighten stop to 15%)
- BoS Bearish does NOT trigger automatic exit
- 20% trailing stop is the PRIMARY exit mechanism

**Backtest Evidence:**
- Trailing stop strategy: +539% average returns
- Signal-based exits: +294% average returns
- **Trailing stop outperforms by 83%**

---

### 5.5 Backtesting Summary Table

| Feature | Documented | Implemented | Status |
|---------|------------|-------------|--------|
| HMA Pivot entries | Yes | Yes | ✅ CONFIRMED |
| 10% baseline entry | Yes | No | ❌ NOT FOUND |
| Fresh trends <4 weeks | Yes | Disabled | ⚠️ REMOVED |
| BoS Bearish exit | Yes | Advisory only | ⚠️ MODIFIED |
| 20% trailing stop | Yes | Yes (PRIMARY) | ✅ CONFIRMED |

---

## 6. Truth Tables

### 6.1 BUY Signal Truth Table

| Beta >= 1.5 | BoS UP | Banker >= 55 | Theme Fit | Gatekeeper | Result |
|:-----------:|:------:|:------------:|:---------:|:----------:|:------:|
| ❌ | - | - | - | - | FILTERED |
| ✅ | ❌ | - | - | - | FILTERED |
| ✅ | ✅ | ❌ | - | - | FILTERED |
| ✅ | ✅ | ✅ | ❌ | - | FILTERED (with LLM) |
| ✅ | ✅ | ✅ | ✅ | FAIL | FILTERED |
| ✅ | ✅ | ✅ | ✅ | CAUTION | **CONSIDER** (watchlist) |
| ✅ | ✅ | ✅ | ✅ | PASS | **TEAL SIGNAL** (buy) |
| ✅ | ✅ | ✅ | - | - | **TEAL SIGNAL** (--no-llm mode) |

### 6.2 SELL Signal Truth Table

| Drawdown >= 20% | BoS DOWN | Status | Action |
|:---------------:|:--------:|:------:|:------:|
| ❌ | ❌ | OPEN | Hold position |
| ❌ | ✅ | OPEN | **ADVISORY**: Tighten stop to 15% |
| ✅ | ❌ | STOPPED | **EXIT**: Trailing stop hit |
| ✅ | ✅ | STOPPED | **EXIT**: Trailing stop hit |

### 6.3 Tier Assignment Truth Table

| Banker Score | Tier | Public Description |
|:------------:|:----:|:-------------------|
| < 55 | - | Does not qualify |
| 55 - 60 | TIER3 | Slight accumulation |
| 60 - 70 | TIER2 | Moderate accumulation |
| > 70 | TIER1 | Strong accumulation |

### 6.4 Theme Classification Truth Table

| Theme Score | Classification | Actionable? | Pass Gate 4? |
|:-----------:|:--------------:|:-----------:|:------------:|
| < 4.5 | AVOID | No | ❌ |
| 4.5 - 6.0 | SELECTIVE | Watchlist | ❌ |
| 6.0 - 7.5 | INVESTABLE | Yes | ✅ |
| >= 7.5 | PRIME | Yes | ✅ |

### 6.5 Combined Signal Flow (Typical Week)

```
UNIVERSE: 937 tickers
    ↓ (Beta >= 1.5)
BETA PASS: ~485 (52%)
    ↓ (BoS UP)
BOS PASS: ~48 (10%)
    ↓ (Banker >= 55)
TECHNICAL: ~44 (92%)
    ↓ (Theme fit)
THEME CONFIRMED: ~17 (39%)
    ↓ (Gatekeeper)
TEAL SIGNALS: 6-7 PASS (35-40%)
WATCHLIST: 5-10 CONSIDER
```

---

## 7. Discrepancies & Concerns

### 7.1 CRITICAL: 10% Baseline Entry Logic Missing

**Documented:** "Entry within 10% of HMA baseline"
**Found:** ❌ NO IMPLEMENTATION

**Impact:** Medium - Documented feature not implemented. Users may expect this filtering.

**Recommendation:** Either implement or remove from documentation.

---

### 7.2 CRITICAL: Exit Strategy Mismatch

**Documented:** "Exit on BoS Bearish signal"
**Actual:** BoS Bearish is ADVISORY only; 20% trailing stop is primary exit

**Impact:** HIGH - Marketing may mislead users about exit methodology.

**Evidence:**
```
Backtest Results:
- Trailing stop: +539% average
- Signal exits: +294% average
```

**Recommendation:** Update marketing to reflect trailing stop as primary exit.

---

### 7.3 MODERATE: Momentum Filter Silently Disabled

**Documented:** "Fresh trends under 4 weeks prioritized"
**Actual:** Filter disabled based on backtest (-3.1% return reduction)

**Impact:** Low - Correct decision based on evidence, but creates documentation drift.

**Recommendation:** Remove from documentation or clearly mark as deprecated.

---

### 7.4 LOW: Pivot Confirmation Lag Not Documented

**Issue:** HMA pivots are confirmed 1 week AFTER they form (k=1 lookback)

**Impact:** Users may not understand signal timing.

**Example:**
- Pivot forms on Week 10
- Signal confirmed on Week 11
- Entry happens Week 12 (Friday scan)
- Stock may have moved 5-15% before entry

**Recommendation:** Document the 1-week confirmation lag in user-facing materials.

---

### 7.5 LOW: Manual Stop Tightening Not Automated

**Issue:** BoS DOWN advises "tighten stop to 15%" but doesn't automatically adjust.

**Current Behavior:**
1. BoS DOWN detected
2. Alert issued: "Tighten stop to 15%"
3. User must MANUALLY adjust (no automatic enforcement)

**Recommendation:** Consider automating stop adjustment or clearly document manual requirement.

---

### 7.6 INFO: No Time-Based Exits

**Observation:** System has no maximum holding period.

**Implications:**
- Positions can be held indefinitely
- No forced exit after poor performance duration
- Relies entirely on 20% trailing stop

**Status:** Design choice, not a bug.

---

## Appendix A: Key Function Reference

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `calculate_beta()` | scanner.py | 283-297 | Beta calculation vs SPY |
| `calculate_banker()` | scanner.py | 300-330 | Institutional accumulation score |
| `calculate_hma()` | scanner.py | 333-353 | Hull Moving Average |
| `find_pivots()` | scanner.py | 361-382 | Pivot high/low detection |
| `calculate_bos()` | scanner.py | 385-490 | Break of Structure signals |
| `check_sell_signals()` | scanner.py | 913-1072 | Exit condition checking |
| `run_thematic_gate()` | scanner.py | 614-756 | Theme analysis integration |
| `run_gatekeeper()` | scanner.py | 763-896 | Final quality gate |
| `add_trade_from_stock()` | portfolio_manager.py | 321-331 | Record new position |
| `flag_exit()` | portfolio_manager.py | 333-352 | Record position exit |

---

## Appendix B: Threshold Quick Reference

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `BETA_THRESHOLD` | 1.5 | Minimum beta for entry |
| `BANKER_TIER1` | 70 | Strong accumulation |
| `BANKER_TIER2` | 60 | Moderate accumulation |
| `BANKER_TIER3` | 55 | Entry minimum |
| `TRAILING_STOP_PCT` | 20.0 | Primary exit trigger |
| `TIGHTEN_STOP_PCT` | 15.0 | Advisory tightening on BoS DOWN |
| `STOP_WARNING_PCT` | 5.0 | Alert threshold |
| `HMA_LENGTH` | 21 | HMA period (weekly bars) |
| `PIVOT_K` | 1 | Pivot lookback window |
| `THEME_PRIME` | 7.5 | Top theme score |
| `THEME_INVESTABLE` | 6.0 | Good theme score |
| `MIN_TRADING_DAYS` | 60 | Minimum for valid beta |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-28 | Claude Code Audit | Initial comprehensive audit |

---

*End of Document*
