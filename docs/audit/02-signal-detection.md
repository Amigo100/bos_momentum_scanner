# Sterling Signals - Signal Detection System Audit

**Document:** `docs/audit/02-signal-detection.md`
**Audit Date:** January 29, 2026
**System Version:** BoS Momentum Scanner v2.x
**Source Files Audited:** `scanner.py`, `portfolio_manager.py`, `config.py`

---

## Table of Contents

1. [Buy Signal Conditions](#1-buy-signal-conditions)
2. [Sell Signal Conditions](#2-sell-signal-conditions)
3. [Code Path Traces](#3-code-path-traces)
4. [HMA Pivot BoS: Alternating Signal Logic](#4-hma-pivot-bos-alternating-signal-logic)
5. [Indicator Formulas](#5-indicator-formulas)
6. [Truth Tables](#6-truth-tables)
7. [Backtesting Findings vs Live Code](#7-backtesting-findings-vs-live-code)
8. [Discrepancies & Concerns](#8-discrepancies--concerns)

---

## 1. Buy Signal Conditions

A stock must pass **all five gates** sequentially to generate a BUY signal.

### Gate 1: Beta Filter (Technical)

| Condition | Threshold | Code Location |
|-----------|-----------|---------------|
| `stock.beta >= 1.5` | BETA_SIGNAL = 1.5 | `scanner.py:187`, `scanner.py:118-119` |

- Calculated as `Cov(stock, SPY) / Var(SPY)` over 1 year of daily returns
- Minimum 60 data points required (`scanner.py:287`)
- If Beta < 1.5, Banker and BoS are **never calculated** (`scanner.py:573-576`)

### Gate 2: Weekly BoS Bullish (Technical)

| Condition | Trigger | Code Location |
|-----------|---------|---------------|
| `stock.bos_bullish == True` | Lower step line changed on weekly HMA | `scanner.py:464-465` |

- HMA period: 21, pivot lookback k=1, applied to weekly HL2
- Daily data resampled to weekly with Friday anchor (`scanner.py:415-421`)
- Signal fires when `current_lower != prev_lower` (new pivot low on HMA)

### Gate 3: Banker >= 55 (Technical / Tier Assignment)

| Condition | Tier | Code Location |
|-----------|------|---------------|
| `banker > 70` | TIER1 | `scanner.py:208` |
| `banker > 60` | TIER2 | `scanner.py:210` |
| `banker > 55` | TIER3 | `scanner.py:212` |
| `banker <= 55` | Rejected (no tier) | `scanner.py:213` returns `""` |

- `get_tier()` returns empty string if `meets_technical_criteria()` is False
- A stock with no tier is excluded from `technical_signals` list (`scanner.py:1356`)

### Gate 4: Theme Confirmation (LLM)

| Condition | Requirement | Code Location |
|-----------|-------------|---------------|
| Theme classification | PRIME or INVESTABLE | `thematic_analyzer.py` |
| Theme fit verdict | STRONG FIT or GOOD FIT | `scanner.py:1405` |

### Gate 5: Gatekeeper Decision (LLM)

| Condition | Requirement | Code Location |
|-----------|-------------|---------------|
| `final_decision` | "PASS" or "TRADE" | `scanner.py:1464-1465` |
| Conviction | 1-5 scale (informational) | `gatekeeper.py` |

**"CONSIDER"** signals are tracked as watchlist items, not buy signals.

### Combined Buy Signal Formula

```
BUY = (Beta >= 1.5)
    AND (bos_bullish == True)        -- weekly HMA lower step changed
    AND (Banker > 55)                -- price above 20-day VWAP
    AND (Theme in [PRIME, INVESTABLE] AND Fit in [STRONG, GOOD])
    AND (Gatekeeper == PASS)
```

---

## 2. Sell Signal Conditions

### Exit Condition 1: Weekly BoS Down (CAUTION)

| Condition | Trigger | Code Location |
|-----------|---------|---------------|
| `stock.bos_bearish == True` | Upper step line changed on weekly HMA | `scanner.py:468-469`, `scanner.py:965` |

**Important:** This is documented as a CAUTION signal, **not an automatic exit**. The recommendation is to tighten the trailing stop from 20% to 15%. However, the code in `_check_sell_signals_portfolio_manager()` at line 965 **does** call `pm.flag_exit()` at line 982, which sets the trade status to CLOSED/STOPPED.

> **DISCREPANCY D1:** See [Section 8](#8-discrepancies--concerns).

### Exit Condition 2: 20% Trailing Stop (AUTOMATIC)

| Condition | Trigger | Code Location |
|-----------|---------|---------------|
| `drawdown_pct >= 20.0` | Price fell 20%+ from highest close since entry | `scanner.py:969`, `portfolio_manager.py:471` |

- `TRAILING_STOP_PCT = 20.0` (`scanner.py:133`)
- Stop level = `highest_close * 0.80` (`portfolio_manager.py:184-186`)
- `highest_close` updated continuously while position is OPEN

### Exit Condition 3: Manual Exit

| Method | Status Set | Code Location |
|--------|-----------|---------------|
| `portfolio_manager.flag_exit()` | "CLOSED" (unless reason contains "stop") | `portfolio_manager.py:333-352` |
| `portfolio_manager.py --exit TICKER` | "CLOSED" or "STOPPED" | CLI interface |

### Stop Alert (Warning, Not Exit)

| Condition | Threshold | Code Location |
|-----------|-----------|---------------|
| `distance_to_stop_pct <= 5.0` | STOP_WARNING_PCT = 5.0 | `portfolio_manager.py:191` |

Displays warning emoji in Google Sheets export; does not trigger exit.

### Combined Sell Signal Formula

```
SELL = (bos_bearish == True)         -- CAUTION: flags exit in code
    OR (drawdown >= 20%)             -- AUTOMATIC: trailing stop
    OR (manual exit by trader)
```

---

## 3. Code Path Traces

### 3.1 Buy Signal: Entry to Output

```
main() [scanner.py:1150]
  │
  ├─ Step 3: download_and_process() [scanner.py:524]
  │   ├─ returns = df['Close'].pct_change()
  │   ├─ stock.beta = calculate_beta(returns, spy_returns) [line 570]
  │   ├─ if beta >= 1.5:                                   [line 573]
  │   │   ├─ stock.banker = calculate_banker(df)            [line 574]
  │   │   ├─ stock.bos_bullish, stock.bos_bearish, ... = calculate_bos(df) [line 575]
  │   │   └─ stock.tier = stock.get_tier()                  [line 576]
  │   └─ stock.momentum_4w = ... (tracked, not filtered)    [line 578-589]
  │
  ├─ Step 4: Pre-filter by Beta                             [line 1231]
  │   └─ high_beta_stocks = [s for s in stocks if s.beta >= BETA_MIN]
  │
  ├─ Step 5: Technical Gate                                 [line 1349]
  │   └─ for stock in high_beta_stocks:
  │       └─ if stock.meets_technical_criteria():            [line 1353]
  │           └─ return beta >= 1.5 AND bos_bullish          [line 187]
  │           └─ if stock.tier:                              [line 1356]
  │               └─ technical_signals.append(stock)
  │
  ├─ Step 6: Thematic Gate                                  [line 1405]
  │   └─ theme_confirmed = run_thematic_gate(technical_signals)
  │       └─ Filter: theme in [PRIME, INVESTABLE], fit in [STRONG, GOOD]
  │
  ├─ Step 7: Gatekeeper Gate                                [line 1457]
  │   └─ confirmed = run_gatekeeper(theme_confirmed)
  │       └─ Filter: final_decision in [PASS, TRADE]
  │
  └─ Output: confirmed list → signals.json, portfolio.csv
```

### 3.2 Sell Signal: Detection to Output

```
main() [scanner.py:1150]
  │
  ├─ Step 8: check_sell_signals(stocks)                     [line 1575]
  │   └─ check_sell_signals() [line 913]
  │       └─ _check_sell_signals_portfolio_manager()        [line 931]
  │           ├─ pm.get_open_positions()                    [line 938]
  │           ├─ for each open trade:
  │           │   ├─ Update highest_close                   [line 952-953]
  │           │   ├─ Calculate drawdown_pct                 [line 956-959]
  │           │   ├─ Check bos_bearish → CAUTION            [line 965]
  │           │   ├─ Check drawdown >= 20% → STOP           [line 969]
  │           │   └─ If triggered: pm.flag_exit()           [line 982]
  │           └─ return sell_signals
  │
  └─ Output: sell_signals printed as caution alerts
```

### 3.3 BoS Calculation: Daily Data to Signal

```
calculate_bos(df, hma_length=21, pivot_k=1)                [line 385]
  │
  ├─ Resample daily → weekly (Friday anchor)                [line 415-421]
  │   OHLCV: Open=first, High=max, Low=min, Close=last, Volume=sum
  │
  ├─ Calculate HL2 = (High + Low) / 2                       [line 427]
  │
  ├─ Calculate HMA(HL2, 21)                                  [line 430]
  │   └─ calculate_hma(hl2, 21)                              [line 333]
  │       ├─ half_length = 10                                [line 339]
  │       ├─ sqrt_length = 4                                 [line 340]
  │       ├─ wma_half = WMA(hl2, 10)                         [line 347]
  │       ├─ wma_full = WMA(hl2, 21)                         [line 348]
  │       ├─ raw_hma = 2 * wma_half - wma_full               [line 350]
  │       └─ hma = WMA(raw_hma, 4)                           [line 351]
  │
  ├─ Find pivots on HMA (k=1)                               [line 433]
  │   └─ find_pivots(hma, 1)                                 [line 356]
  │       ├─ Pivot HIGH: hma[i] > hma[i-1] AND hma[i] > hma[i+1]
  │       │   AND unique maximum (no ties)                   [line 369-371]
  │       ├─ Pivot LOW: hma[i] < hma[i-1] AND hma[i] < hma[i+1]
  │       │   AND unique minimum (no ties)                   [line 374-376]
  │       └─ Pivots confirmed k=1 bars AFTER occurrence      [line 371, 376]
  │
  ├─ Build step lines                                        [line 435-448]
  │   ├─ upper: carry forward last pivot HIGH value
  │   └─ lower: carry forward last pivot LOW value
  │
  └─ Fire signals                                            [line 463-469]
      ├─ bos_up = (current_lower != prev_lower)  → BUY
      └─ bos_down = (current_upper != prev_upper) → SELL
```

---

## 4. HMA Pivot BoS: Alternating Signal Logic

### How Alternation Works

The HMA Pivot method produces naturally alternating signals because:

1. **HMA smooths price action** into a single curve
2. **Pivots on HMA alternate**: low → high → low → high (by definition of local extrema on a smooth curve)
3. **Step lines change in sequence**: lower step changes (BUY) → upper step changes (SELL) → lower step changes (BUY)

### Signal State Machine

```
                 ┌──────────────────────┐
                 │                      │
                 ▼                      │
     ┌───────────────────┐    ┌───────────────────┐
     │   BULLISH (BUY)   │    │  BEARISH (SELL)    │
     │                   │    │                    │
     │ lower step changed│    │ upper step changed │
     └─────────┬─────────┘    └─────────┬──────────┘
               │                        │
               │   Next pivot is HIGH   │
               └────────────────────────┘
```

### Can Both Fire Simultaneously?

**Theoretically possible but extremely unlikely.** Both `bos_up` and `bos_down` could be True on the same bar if:
- A pivot HIGH and a pivot LOW are both confirmed on the same weekly bar
- This would require k=1, meaning the HMA had both a local max and local min within 3 consecutive bars

The code does **not** enforce mutual exclusivity. Both flags are independently calculated (`scanner.py:464-469`).

### No Explicit State Tracking

There is **no `last_signal_type` variable** in the code. The alternation relies entirely on the mathematical properties of HMA pivots. The code does not track or enforce signal ordering.

### Pivot Confirmation Delay

Pivots are confirmed `k=1` bars after occurrence (`scanner.py:371, 376`):
```python
pivot_highs.iloc[i + k] = center_val   # Confirmed 1 bar later
```

This means:
- A pivot detected at week N is assigned to week N+1
- The signal fires on the weekly bar **after** the pivot forms
- This introduces a 1-week delay from pivot formation to signal

---

## 5. Indicator Formulas

### 5.1 Beta

```
Beta = Cov(R_stock, R_spy) / Var(R_spy)

Where:
  R_stock = daily close-to-close returns over ~1 year
  R_spy   = daily SPY returns over same period
  Minimum 60 aligned data points required
```

**Code:** `scanner.py:283-297`

### 5.2 Banker (Institutional Accumulation)

```
Typical_Price = (High + Low + Close) / 3
VWAP_20 = Sum(TP * Volume, 20 days) / Sum(Volume, 20 days)
Deviation% = (Close / VWAP_20 - 1) * 100
Banker = CLAMP(50 + Deviation% * 5, 0, 100)

Interpretation:
  Banker = 50  → Price at VWAP (neutral)
  Banker = 55  → Price 1% above VWAP (TIER3 threshold)
  Banker = 60  → Price 2% above VWAP (TIER2 threshold)
  Banker = 70  → Price 4% above VWAP (TIER1 threshold)
```

**Code:** `scanner.py:300-330`

### 5.3 Hull Moving Average (HMA)

```
HMA(series, n) = WMA(2 * WMA(series, n/2) - WMA(series, n), sqrt(n))

Where:
  WMA(x, n) = (x_1*1 + x_2*2 + ... + x_n*n) / (1 + 2 + ... + n)
  n = 21 (weekly bars)
  Input series = HL2 = (weekly_High + weekly_Low) / 2

  For n=21:
    half_length = 10
    sqrt_length = 4
```

**Code:** `scanner.py:333-353`

### 5.4 Pivot Detection

```
Pivot HIGH at bar i:
  HMA[i] > HMA[i-1] AND HMA[i] > HMA[i+1]
  AND HMA[i] is unique max in window (no ties)
  Confirmed at bar i+1

Pivot LOW at bar i:
  HMA[i] < HMA[i-1] AND HMA[i] < HMA[i+1]
  AND HMA[i] is unique min in window (no ties)
  Confirmed at bar i+1
```

**Code:** `scanner.py:356-382`

### 5.5 Trailing Stop

```
highest_close = max(entry_price, all subsequent closes while OPEN)
stop_level    = highest_close * (1 - 20/100) = highest_close * 0.80
drawdown_pct  = (highest_close - current_price) / highest_close * 100

EXIT when: drawdown_pct >= 20.0
```

**Code:** `portfolio_manager.py:184-186`, `scanner.py:969`

---

## 6. Truth Tables

### 6.1 Technical Gate

| Beta >= 1.5 | bos_bullish | Banker > 55 | Result |
|:-----------:|:-----------:|:-----------:|:------:|
| F | F | F | REJECT |
| F | F | T | REJECT |
| F | T | F | REJECT |
| F | T | T | REJECT |
| T | F | F | REJECT |
| T | F | T | REJECT |
| T | T | F | REJECT (no tier) |
| **T** | **T** | **T** | **PASS** |

All three conditions must be True. Only the last row passes.

### 6.2 Tier Assignment (Given Technical Gate PASS)

| Banker Range | Tier |
|:------------:|:----:|
| > 70 | TIER1 |
| > 60, <= 70 | TIER2 |
| > 55, <= 60 | TIER3 |
| <= 55 | (rejected, no tier) |

### 6.3 Theme Gate

| Classification | Fit Verdict | Result |
|:--------------:|:-----------:|:------:|
| PRIME | STRONG FIT | **PASS** |
| PRIME | GOOD FIT | **PASS** |
| PRIME | MODERATE FIT | REJECT |
| PRIME | POOR FIT | REJECT |
| INVESTABLE | STRONG FIT | **PASS** |
| INVESTABLE | GOOD FIT | **PASS** |
| INVESTABLE | MODERATE/POOR | REJECT |
| SELECTIVE | Any | REJECT |
| AVOID | Any | REJECT |

### 6.4 Gatekeeper Gate

| Decision | Result |
|:--------:|:------:|
| PASS / TRADE | **BUY SIGNAL** |
| CONSIDER | Watchlist (no buy) |
| CAUTION | Watchlist (no buy) |
| FAIL / SKIP | Rejected |

### 6.5 Sell Signal Priority

| bos_bearish | drawdown >= 20% | Result |
|:-----------:|:---------------:|:------:|
| F | F | No signal |
| F | T | **TRAILING STOP** (automatic) |
| T | F | **BoS DOWN** (caution) |
| T | T | **BoS DOWN** (checked first due to `elif`) |

Note: The `elif` at line 969 means if `bos_bearish` is True, the trailing stop check is skipped. Both conditions flagging a sell is handled by the BoS check taking priority.

### 6.6 Full Pipeline Funnel (Typical Numbers)

| Stage | Input | Output | Pass Rate |
|:-----:|:-----:|:------:|:---------:|
| Universe | ~1,800 | ~1,800 | 100% |
| Beta >= 1.5 | ~1,800 | ~485 | ~27% |
| BoS Bullish | ~485 | ~48 | ~10% |
| Banker >= 55 (Tier) | ~48 | ~44 | ~92% |
| Theme Confirmed | ~44 | ~17 | ~39% |
| Gatekeeper PASS | ~17 | ~6 | ~35% |

---

## 7. Backtesting Findings vs Live Code

### Finding 1: Momentum Filter Hurts Returns

**Documented claim** (`scanner.py:127-130`):
> Momentum filter (<10%) REDUCED returns from +9.2% to +6.1% on average across 4000+ stocks

**Live code status:**
- `passes_momentum_filter()` at line 189-195 **always returns True** (filter disabled)
- `momentum_4w` is still calculated (`scanner.py:578-589`) but used only for informational display
- `meets_all_technical_criteria()` at line 197-202 calls `meets_technical_criteria()` only

**Verdict: CONSISTENT.** Filter removed as backtesting recommended.

### Finding 2: Trailing Stop > Signal-Based Exit

**Documented claim** (`scanner.py:1760-1763`):
> Signal-based exits: +294% average return
> Trailing stop exits: +539% average return

**Live code status:**
- Primary exit method in code is `TRAILING_STOP_PCT = 20.0` (`scanner.py:133`)
- BoS Down is documented as "tighten stop to 15%, do NOT auto-exit" (`scanner.py:1595`)

**Verdict: INCONSISTENT.** See Discrepancy D1 below.

### Finding 3: HMA Pivot Entries (10% of Baseline)

**Documented claim** (from CLAUDE.md):
> HMA Pivot entries were roughly 10% of baseline (total opportunities very limited)

**Live code status:**
- Typical pipeline: ~48 BoS bullish out of ~485 high-beta stocks = ~10%
- This matches the documented finding

**Verdict: CONSISTENT.**

### Finding 4: Fresh Trends < 4 Weeks

**Documented claim**: Fresh trends (entered within 4 weeks of signal) performed better.

**Live code status:**
- No explicit "fresh trend" filter exists in the code
- `momentum_4w` is tracked but not used as a gate
- The weekly BoS signal inherently fires on the most recent bar only (`scanner.py:464-465` checks last vs second-to-last weekly bar)

**Verdict: PARTIALLY CONSISTENT.** The BoS signal only fires on the current week's bar, which naturally captures "fresh" signals. However, there is no explicit recency check.

---

## 8. Discrepancies & Concerns

### D1: BoS Bearish Is BOTH a Caution AND an Auto-Exit (CRITICAL)

**Documentation says** (`scanner.py:1595`):
```
⚠️  This is NOT an automatic exit - use trailing stop
```

And (`scanner.py:1595-1596`):
```
CAUTION: HMA Pivot SELL = tighten stop to 15%, don't exit
DO NOT automatically exit on SELL signal
```

**But the code does** (`scanner.py:965, 982`):
```python
if stock.bos_bearish:
    sell_reason = f"Weekly BoS Down (price breaking structure low)"
    ...
    pm.flag_exit(symbol, current_price, reason=sell_reason)
```

`flag_exit()` sets `trade.status = "CLOSED"` and records an exit date/price. This **is** an automatic exit.

**Impact:** The backtesting found trailing stops (+539%) outperform signal exits (+294%). The code contradicts its own documented recommendation by auto-exiting on BoS bearish.

**Recommendation:** Either:
1. Remove `pm.flag_exit()` from the BoS bearish branch and only generate a warning, OR
2. Implement the documented "tighten to 15%" behavior programmatically

### D2: No "Tighten to 15%" Implementation

The documentation repeatedly recommends tightening the trailing stop from 20% to 15% when BoS bearish fires. There is **no code that implements this**. The trailing stop is always 20% (`TRAILING_STOP_PCT = 20.0` is a constant).

**Recommendation:** Add a per-trade `stop_pct` field that defaults to 20% and narrows to 15% on BoS bearish.

### D3: Duplicate Threshold Constants

Constants are defined in **both** `config.py` and `scanner.py`:

| Constant | scanner.py | config.py |
|----------|-----------|-----------|
| BETA_MIN | Line 118 (1.5) | Defined |
| BANKER_TIER1 | Line 123 (70.0) | Defined |
| TRAILING_STOP_PCT | Line 133 (20.0) | Defined |

If values diverge, behavior depends on which module is imported. `scanner.py` uses its own local constants.

### D4: `meets_technical_criteria()` vs Pipeline Usage

`meets_technical_criteria()` checks only `beta >= 1.5 AND bos_bullish` (line 187). But the pipeline **also** requires `Banker > 55` (via `get_tier()` returning non-empty). The method name is misleading since it doesn't capture all technical criteria.

### D5: Both bos_bullish and bos_bearish Can Be True Simultaneously

The code calculates both independently (`scanner.py:464-469`). There is no mutual exclusion enforced. If both fire on the same bar, a stock could simultaneously:
- Pass the technical gate (bos_bullish = True)
- Trigger a sell signal on existing positions (bos_bearish = True)

This is an edge case but could cause contradictory signals.

### D6: Sell Signal `elif` Masks Trailing Stop When BoS Bearish

At `scanner.py:969`, the trailing stop check uses `elif`:
```python
if stock.bos_bearish:
    sell_reason = "Weekly BoS Down..."
elif drawdown_pct >= TRAILING_STOP_PCT:
    sell_reason = "Trailing stop hit..."
```

If a stock has **both** BoS bearish AND has hit 20% drawdown, only the BoS reason is recorded. The more severe condition (actual stop hit) is masked. The trade is still flagged for exit either way, but the recorded reason may be misleading.

### D7: `highest_close` Updated in Multiple Places

`highest_close` is updated in:
1. `scanner.py:952-953` (in `_check_sell_signals_portfolio_manager`)
2. `portfolio_manager.py:174-175` (in `calculate_metrics`)
3. `portfolio_manager.py:464-465` (in `check_stop_signals`)

The scanner update (1) happens during the weekly scan, but (2) and (3) happen when prices are refreshed. If `portfolio_manager.py --update` runs independently, `highest_close` updates outside the scanner's awareness. This is correct behavior but worth noting for traceability.

### D8: Legacy Sell Path Still Exists

`_check_sell_signals_legacy()` (`scanner.py:996-1072`) reads from `open_positions.csv`, a deprecated file. If `PORTFOLIO_MANAGER_AVAILABLE` is False (import failure), the system falls back to this legacy path silently. The legacy path has identical logic but bypasses `portfolio_manager.py`'s `flag_exit()` method.

---

## Appendix A: Key Line References

| Item | File | Line(s) |
|------|------|---------|
| Stock dataclass | scanner.py | 148-219 |
| SellSignal dataclass | scanner.py | 903-911 |
| meets_technical_criteria() | scanner.py | 185-187 |
| passes_momentum_filter() (disabled) | scanner.py | 189-195 |
| get_tier() | scanner.py | 204-214 |
| calculate_beta() | scanner.py | 283-297 |
| calculate_banker() | scanner.py | 300-330 |
| calculate_hma() | scanner.py | 333-353 |
| find_pivots() | scanner.py | 356-382 |
| calculate_bos() | scanner.py | 385-490 |
| BUY signal condition | scanner.py | 464-465 |
| SELL signal condition | scanner.py | 468-469 |
| download_and_process() | scanner.py | 524-599 |
| bos_bullish/bearish assigned | scanner.py | 575 |
| check_sell_signals() | scanner.py | 913-928 |
| BoS bearish exit check | scanner.py | 965 |
| Trailing stop exit check | scanner.py | 969 |
| flag_exit() call | scanner.py | 982 |
| Technical gate loop | scanner.py | 1349-1363 |
| Theme gate | scanner.py | 1405 |
| Gatekeeper gate | scanner.py | 1457-1470 |
| Caution output text | scanner.py | 1590-1597 |
| Trade dataclass | portfolio_manager.py | 131-166 |
| calculate_metrics() | portfolio_manager.py | 168-204 |
| flag_exit() | portfolio_manager.py | 333-352 |
| check_stop_signals() | portfolio_manager.py | 448-484 |
| TRAILING_STOP_PCT | scanner.py | 133 |
| STOP_WARNING_PCT | portfolio_manager.py | 75 |

---

*End of Signal Detection Audit*
