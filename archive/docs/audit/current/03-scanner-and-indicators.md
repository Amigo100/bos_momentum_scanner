# 03 - Scanner and Indicators

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Scanner Architecture (core/scanner.py - 3,283 lines)

### 1.1 Dataclasses

#### Stock (lines 138-230)

```python
@dataclass
class Stock:
    symbol: str
    price: float = 0.0
    beta: float = 0.0
    banker: float = 0.0
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: dict = field(default_factory=dict)
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""                    # TIER1, TIER2, TIER3

    # Thematic analyzer fields
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0          # 0-100%
    theme_verdict: str = ""           # STRONG FIT, GOOD FIT, MODERATE FIT, POOR FIT

    # Gatekeeper fields
    final_decision: str = ""          # PASS, CONSIDER, FAIL
    conviction: int = 0               # 1-5
    catalyst_summary: str = ""
    red_flag_level: str = ""          # CLEAN, MINOR, SEVERE
    action: str = ""
    bullish_factors: List[str]
    risk_factors: List[str]
    reasoning: str = ""
    sector_status: str = ""
    upside_potential: str = ""

    # DD fields (populated by dd_automator)
    dd_verdict: str = ""              # STRONG BUY, SPEC BUY, NO GO
    dd_conviction: int = 0            # 1-10
    dd_position_size: str = ""
    dd_analysis: str = ""
    dd_key_catalyst: str = ""
    dd_fatal_flaw: str = ""
```

**Key methods:**
- `meets_technical_criteria()` (line 191): `beta >= BETA_SIGNAL and bos_bullish and banker >= BANKER_TIER3`
- `get_tier()` (line 193): Returns TIER1/TIER2/TIER3 based on banker level
- `passes_theme_gate()` (line 207): `theme_verdict in ["STRONG FIT", "GOOD FIT"]`
- `is_confirmed()` (line 209): Returns True if `final_decision in ["PASS", "CONSIDER"]`

#### ScanStats (lines 215-229)

```python
@dataclass
class ScanStats:
    tickers_loaded: int = 0
    data_downloaded: int = 0
    beta_gte_1_5: int = 0
    bos_bullish: int = 0
    bos_bearish: int = 0
    banker_tier1: int = 0             # banker > 70
    banker_tier2: int = 0             # banker > 60
    banker_tier3: int = 0             # banker > 55
    meets_technical_gate: int = 0
    tier1: int = 0
    tier2: int = 0
    tier3: int = 0
    theme_confirmed: int = 0
    final_trade: int = 0              # PASS decisions
    final_consider: int = 0           # CONSIDER decisions
    final_skip: int = 0              # FAIL decisions
```

#### SellSignal (lines 231-240)

```python
@dataclass
class SellSignal:
    symbol: str
    price: float
    reason: str                       # "Trailing stop hit ..." or "Weekly BoS Down ..."
    entry_price: float
    highest_close: float
    drawdown_pct: float
```

---

## 2. Technical Indicator Formulas

### 2.1 Beta Calculation (lines 270-284)

```python
def calculate_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 60:
        return 0.0
    aligned.columns = ['stock', 'bench']
    cov = aligned['stock'].cov(aligned['bench'])
    var = aligned['bench'].var()
    if var == 0 or pd.isna(var):
        return 0.0
    beta = cov / var
    return round(float(beta), 2) if not pd.isna(beta) else 0.0
```

| Property | Value |
|----------|-------|
| Formula | `Beta = Cov(stock, SPY) / Var(SPY)` |
| Input | Daily returns for stock and SPY |
| Minimum data | 60 trading days |
| Output | Float rounded to 2 decimals |
| Threshold | >= 1.5 for entry |
| Config constant | `BETA_THRESHOLD` in settings.py |

### 2.2 Banker (Institutional Accumulation Score) (lines 287-317)

```python
def calculate_banker(df: pd.DataFrame) -> float:
    if len(df) < VWAP_PERIOD:
        return 0.0
    recent = df.tail(VWAP_PERIOD)
    typical = (recent['High'] + recent['Low'] + recent['Close']) / 3
    vwap = (typical * recent['Volume']).sum() / recent['Volume'].sum()
    current = float(recent['Close'].iloc[-1])
    if vwap == 0:
        return 0.0
    deviation_pct = ((current / vwap) - 1) * 100
    banker = BANKER_CENTER + (deviation_pct * BANKER_SCALE_FACTOR)
    return round(max(0, min(100, banker)), 1)
```

| Property | Value |
|----------|-------|
| Formula | `banker = 50 + ((price/VWAP - 1) × 100 × 5)` |
| VWAP period | 20 days (`VWAP_PERIOD` in settings.py) |
| Center | 50 (`BANKER_CENTER` in settings.py) |
| Scale factor | 5 (`BANKER_SCALE_FACTOR` in settings.py) |
| Output range | 0-100, clamped |
| Interpretation | 50 = at VWAP (neutral), 55+ = accumulation, 70+ = strong |
| Tier thresholds | TIER1: >70, TIER2: >60, TIER3: >55 |
| Config constants | `BANKER_TIER1`, `BANKER_TIER2`, `BANKER_TIER3` in settings.py |

### 2.3 Hull Moving Average (lines 320-340)

```python
def calculate_hma(series: pd.Series, length: int) -> pd.Series:
    import math
    half_length = max(1, length // 2)
    sqrt_length = max(1, int(math.sqrt(length)))

    def wma(s, n):
        weights = np.arange(1, n + 1)
        return s.rolling(n).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    wma_half = wma(series, half_length)
    wma_full = wma(series, length)
    raw_hma = 2 * wma_half - wma_full
    hma = wma(raw_hma, sqrt_length)
    return hma
```

| Property | Value |
|----------|-------|
| Formula | `HMA = WMA(2 × WMA(n/2) - WMA(n), sqrt(n))` |
| WMA weights | Linear: `[1, 2, 3, ..., n]` |
| Default period | 21 (`HMA_PERIOD` in settings.py) |
| Applied to | HL2 = `(High + Low) / 2` on weekly bars |

### 2.4 Pivot Detection (lines 343-369)

```python
def find_pivots(series: pd.Series, k: int = 1) -> Tuple[pd.Series, pd.Series]:
    pivot_highs = pd.Series(index=series.index, dtype=float)
    pivot_lows = pd.Series(index=series.index, dtype=float)

    for i in range(k, len(series) - k):
        window = series.iloc[i-k:i+k+1]
        center_val = series.iloc[i]

        if center_val == window.max() and (window == center_val).sum() == 1:
            pivot_highs.iloc[i + k] = center_val

        if center_val == window.min() and (window == center_val).sum() == 1:
            pivot_lows.iloc[i + k] = center_val

    return pivot_highs, pivot_lows
```

| Property | Value |
|----------|-------|
| Pivot High | Center value strictly highest in `[i-k ... i+k]` window |
| Pivot Low | Center value strictly lowest in `[i-k ... i+k]` window |
| Default k | 1 (immediate confirmation) |
| Confirmation lag | Pivot recorded k bars AFTER occurrence (line 362, 367) |
| Uniqueness | `(window == center_val).sum() == 1` ensures no ties |

### 2.5 Break of Structure (BoS) Detection (lines 372-477)

```python
def calculate_bos(df: pd.DataFrame) -> Tuple[bool, bool, dict]:
    # 1. Resample daily to weekly (Friday close)
    weekly = df.resample('W-FRI').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min',
        'Close': 'last', 'Volume': 'sum'
    }).dropna()

    # 2. Calculate HL2 and HMA on weekly bars
    hl2 = (weekly['High'] + weekly['Low']) / 2
    hma = calculate_hma(hl2, HMA_PERIOD)

    # 3. Find pivots on HMA
    pivot_highs, pivot_lows = find_pivots(hma, k=1)

    # 4. Build step lines (forward-fill last pivot value)
    upper = pd.Series(index=weekly.index, dtype=float)
    lower = pd.Series(index=weekly.index, dtype=float)
    last_ph, last_pl = np.nan, np.nan
    for i in range(len(weekly)):
        if not pd.isna(pivot_highs.iloc[i]):
            last_ph = pivot_highs.iloc[i]
        if not pd.isna(pivot_lows.iloc[i]):
            last_pl = pivot_lows.iloc[i]
        upper.iloc[i] = last_ph
        lower.iloc[i] = last_pl

    # 5. Detect break of structure
    bos_up = (current_lower != prev_lower)    # New bullish pivot
    bos_down = (current_upper != prev_upper)  # New bearish pivot

    return bos_up, bos_down, debug_info
```

| Property | Value |
|----------|-------|
| Timeframe | Weekly (W-FRI resampling) |
| HMA input | HL2 on weekly bars |
| HMA period | 21 (default) |
| Step lines | Forward-filled last pivot high/low values |
| BUY signal (bos_up) | Lower step line value changed (new pivot low on HMA) |
| SELL signal (bos_down) | Upper step line value changed (new pivot high on HMA) |
| Both can be True | Yes, if both step lines changed on same bar |

### 2.6 Four-Week Momentum (lines 538-549)

```python
weekly = df.resample('W-FRI').agg({'Close': 'last'}).dropna()
if len(weekly) >= 5:
    close_now = float(weekly['Close'].iloc[-1])
    close_4w_ago = float(weekly['Close'].iloc[-5])
    stock.momentum_4w = round((close_now / close_4w_ago - 1) * 100, 1)
```

| Property | Value |
|----------|-------|
| Formula | `(close_now / close_4w_ago - 1) × 100` |
| Lookback | 5 weekly bars = 4 weeks |
| Status | Tracked but NOT used as a filter (removed after backtest) |
| Note | Backtest showed momentum filter reduced returns from +9.2% to +6.1% |

### 2.7 Twenty-Day Return (line 528)

```python
stock.return_20d = round((df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100, 1)
```

| Property | Value |
|----------|-------|
| Formula | `(current_close / close_20d_ago - 1) × 100` |
| Used for | Display, analysis log, newsletter briefing |
| Not a gate | Does not filter signals |

---

## 3. The Five-Gate Pipeline

### Gate 1: Technical Gate (line 1254)

```
Condition: beta >= 1.5 AND bos_bullish == True AND banker >= 55
Typical:   ~1,800 → ~44 stocks pass
```

Tier assignment:
- TIER1: banker > 70 (strong accumulation)
- TIER2: banker > 60 (moderate accumulation)
- TIER3: banker > 55 (slight accumulation)

### Gate 2: Thematic Analyzer (line 1310)

```
Model:     Claude Sonnet 4 (claude-sonnet-4-20250514)
Max tokens: 12,000
Web search: Optional (adds ~$0.50)
Condition: theme_verdict in ["STRONG FIT", "GOOD FIT"]
Typical:   ~44 → ~17 stocks pass
```

**Step 1 - Theme Identification:**
- System prompt (lines 532-838): Identify 5-7 investable themes
- Scoring: 4 components weighted → composite score
  - Catalyst strength: 40%
  - Momentum direction: 25%
  - Crowding level: 20%
  - Runway remaining: 15%
- Classification: PRIME (>=7.5), INVESTABLE (>=6.0), SELECTIVE (>=4.5), AVOID (<4.5)
- Theme types: TREND, BOTTLENECK, CONTRARIAN

**Step 2 - Ticker Mapping:**
- Prompt template (lines 840-949): Map tickers to themes
- Per-ticker: theme fit score (0-100%) + company position (Leader/Challenger/Niche/Laggard)
- Verdicts: STRONG FIT, GOOD FIT, MODERATE FIT, WEAK FIT

### Gate 3: Gatekeeper (line 1362)

```
Model:     Claude Sonnet 4
Max tokens: 3,000
Web search: 2-3 per stock (recommended)
Decisions: PASS / CAUTION / FAIL
Typical:   ~17 → 6 PASS + 7 CONSIDER
```

Per-stock analysis:
- Catalyst assessment (earnings, events within 90 days)
- Red flag detection (auditor resignation, CFO departure, SEC investigation, dilution)
- Sentiment analysis (analyst trends, short interest)
- Conviction score: 1-5

**Immediate Disqualifiers** (automatic FAIL):
- Recent auditor resignation/change
- CFO or CEO departure within 90 days
- SEC investigation or accounting restatement
- Severe short report with unaddressed allegations
- Upcoming dilution event (shelf registration, ATM active)
- Insider selling > 10% in last 30 days

**Decision Mapping** (scanner.py lines 876-881):
- `GateDecision.PASS` → `Stock.final_decision = "PASS"` (green signal)
- `GateDecision.CAUTION` → `Stock.final_decision = "CONSIDER"` (watchlist)
- `GateDecision.FAIL` → `Stock.final_decision = "FAIL"` (skip)

### Gate 4: Automated Due Diligence (line 3110)

```
Model:     Claude Sonnet 4 (quick) or Opus 4 (full)
Max tokens: 4,000 (quick) or 8,000 + 10,000 thinking (full)
Only runs:  On PASS signals
Decisions:  STRONG BUY / SPEC BUY / NO GO
```

5-phase methodology:
1. Explosive Growth - Revenue, margins, ROIC
2. Hidden Catalysts - Non-consensus events
3. Bear Killer - Short thesis rebuttal
4. Valuation Reality - Multiple analysis
5. Synthesis - Final recommendation

Only STRONG BUY and SPEC BUY are added to portfolio.

### Gate 5: Portfolio Entry (line 3158)

```
Action:    add_to_open_positions(stock)
Records:   ticker, entry_date, entry_price, theme, tier, conviction
File:      portfolio/output/portfolio.csv (atomic write)
```

---

## 4. Sell Signal Detection (lines 963-1033)

Two independent checks on each open position:

### 4.1 Trailing Stop (PRIMARY - line 997)

```python
drawdown_pct = ((trade.highest_close - current_price) / trade.highest_close) * 100
if drawdown_pct >= TRAILING_STOP_PCT:  # default 20%
    # EXIT: Flag as STOPPED
```

- Default: 20% from highest weekly close (`TRAILING_STOP_PCT`)
- Can be tightened to 15% per-trade (`TIGHTEN_STOP_PCT`)
- Updates `trade.highest_close` if current price exceeds it

### 4.2 BoS Bearish (SECONDARY - line 1010)

```python
elif stock.bos_bearish:
    # CAUTION: Tighten stop to 15%, don't exit
    pm.tighten_stop(symbol)
```

- Does NOT trigger immediate exit
- Tightens per-trade stop to `TIGHTEN_STOP_PCT` (15%)
- Uses elif: only reached if trailing stop NOT hit

### 4.3 Precedence

Trailing stop is checked FIRST. If `drawdown >= stop_pct`, the position is STOPPED regardless of BoS status. BoS bearish only applies when the position is still within stop distance.

---

## 5. Scanner CLI Arguments (line 3016)

| Argument | Type | Default | Purpose |
|----------|------|---------|---------|
| `--no-llm` | flag | False | Skip ALL LLM gates (technical signals only) |
| `--no-momentum` | flag | False | Skip gatekeeper (keep theme analysis) |
| `--assess-top` | int | None | Only run gatekeeper on top N by banker |
| `--no-email` | flag | False | Skip email notification |
| `--no-prompts` | flag | False | Skip DD/newsletter prompts |
| `--no-grok-prompts` | flag | False | Skip Grok/X prompt generation |
| `--top` | int | None | Only scan top N stocks by beta |
| `--web-search` | flag | False | Enable web search for analyzer + gatekeeper |
| `--verbose` / `-v` | flag | False | Show detailed diagnostic output |
| `--archive` | flag | False | Save dated archive files |
| `--no-dd` | flag | False | Skip automated DD (NOT recommended) |
| `--full-dd` | flag | False | Run full DD using Opus |
| `--dd-top` | int | None | Only run DD on top N by conviction |
| `--save-dd` | flag | False | Save DD reports to reports/ directory |

---

## 6. Scanner Functions Reference

| Line | Function | Purpose |
|------|----------|---------|
| 234 | `load_tickers(filepath)` | Load ticker list from file |
| 270 | `calculate_beta(returns, benchmark)` | Stock beta vs SPY |
| 287 | `calculate_banker(df)` | Institutional accumulation score |
| 320 | `calculate_hma(series, length)` | Hull Moving Average |
| 343 | `find_pivots(series, k)` | Pivot high/low detection |
| 372 | `calculate_bos(df)` | Break of Structure (weekly) |
| 480 | `download_and_process(ticker, spy_data, ...)` | Download + all indicators |
| 574 | `run_thematic_gate(signals, use_web_search)` | Step 5: Theme analysis |
| 798 | `run_gatekeeper(signals, top_n, themes_context, use_web_search)` | Step 6: Final gate |
| 949 | `check_sell_signals(stocks)` | Step 7: Sell signal check |
| 963 | `_check_sell_signals_portfolio_manager(stocks)` | Implementation: trailing stop + BoS |
| 1037 | `add_to_open_positions(stock)` | Add trade to portfolio |
| 1042 | `load_open_positions()` | Get open position symbols |
| 1056 | `run_scan(skip_llm, skip_momentum, ...)` | Complete 8-step pipeline |
| 1413 | `print_final_report(confirmed, sell_signals, stats)` | Terminal summary |
| 1519 | `generate_report(confirmed, all_assessed, sell_signals, stats)` | Text report |
| 1702 | `generate_newsletter_briefing(confirmed, sell_signals, themes_data, stats)` | Markdown briefing |
| 2138 | `save_newsletter_briefing(confirmed, sell_signals, ...)` | Save briefing files |
| 2189 | `generate_grok_prompts(briefing_file, confirmed, ...)` | 21 Grok prompts |
| 2638 | `save_results(confirmed, all_assessed, sell_signals, stats, ...)` | Save all outputs |
| 2953 | `send_notification(confirmed, sell_signals, stats, report)` | Email alert |
| 3015 | `main()` | CLI entry point |

---

## 7. Thematic Analyzer (core/thematic_analyzer.py - 2,516 lines)

### 7.1 Key Classes

| Class | Lines | Fields | Purpose |
|-------|-------|--------|---------|
| `Config` | 50-93 | 23 fields | API keys, model, rate limits, email settings |
| `CostTracker` | 100-188 | 8 fields | Token/search cost tracking |
| `Theme` | 266-349 | 26 fields | Investment theme with scoring |
| `TickerAnalysis` | 352-430 | 28 fields | Per-ticker analysis result |
| `AnalysisResult` | 433-443 | 4 fields | Complete analysis output |
| `RateLimiter` | 450-525 | 7 fields | API rate limiting |
| `ThematicAnalyzer` | 956-2328 | 7 fields | Main analyzer orchestrator |

### 7.2 Theme Scoring

```
COMPOSITE = (Catalyst × 0.40) + (Momentum × 0.25) + (Crowding × 0.20) + (Runway × 0.15)
```

| Component | Weight | Scale | High Score Means |
|-----------|--------|-------|-----------------|
| Catalyst | 40% | 1-10 | Multiple specific catalysts in 6-12 months |
| Momentum | 25% | 1-10 | Accelerating (3-month > 1-month annualized) |
| Crowding | 20% | 1-10 | Under-owned, skepticism, elevated shorts |
| Runway | 15% | 1-10 | <40% penetration or multi-year capex cycle |

| Composite Score | Classification | Position Sizing |
|-----------------|----------------|-----------------|
| >= 7.5 | PRIME | FULL |
| 6.0 - 7.4 | INVESTABLE | FULL |
| 4.5 - 5.9 | SELECTIVE | REDUCED |
| < 4.5 | AVOID | NONE |

### 7.3 API Configuration

| Parameter | Value |
|-----------|-------|
| Model | `claude-sonnet-4-20250514` |
| Max tokens | 12,000 |
| Temperature | Not set (API default) |
| Web search tool | `web_search_20250305` (when enabled) |
| Max retries | 8 |
| Base delay | 5.0 seconds |
| Max delay | 180.0 seconds |

---

## 8. Gatekeeper (core/gatekeeper.py - 627 lines)

### 8.1 Key Classes

| Class | Lines | Purpose |
|-------|-------|---------|
| `GateDecision` (Enum) | - | PASS, CAUTION, FAIL |
| `GatekeeperResult` | - | 18-field result dataclass |

### 8.2 GatekeeperResult Fields

```python
@dataclass
class GatekeeperResult:
    ticker: str
    decision: GateDecision
    conviction: int               # 1-5
    theme: str
    theme_fit: str                # STRONG, GOOD, MODERATE
    catalyst_present: bool
    catalyst_summary: str
    days_to_catalyst: int
    red_flag_level: str           # CLEAN, MINOR, SEVERE
    red_flags: List[str]
    analyst_trend: str            # BULLISH, NEUTRAL, BEARISH
    short_interest_pct: float
    key_bullish: List[str]        # Top 3 bullish factors
    key_risks: List[str]          # Top 3 risk factors
    reasoning: str
    action: str                   # Recommended action
```

### 8.3 API Configuration

| Parameter | Value |
|-----------|-------|
| Model | `claude-sonnet-4-20250514` |
| Max tokens | 3,000 |
| Web search | Optional, 2-3 per stock recommended |
| Role | Senior Risk Manager at a $500M hedge fund |

---

## 9. Due Diligence System

### 9.1 DD Automator (core/dd_automator.py - 806 lines)

| Mode | Model | Max Tokens | Thinking Budget |
|------|-------|------------|-----------------|
| Quick | Claude Sonnet 4 | 4,000 | None |
| Full | Claude Opus 4 | 8,000 | 10,000 |

Key function: `run_automated_dd(stocks, quick_mode, use_web_search, save_reports, max_stocks)`

DDResult fields: `dd_verdict`, `dd_conviction` (1-10), `dd_position_size`, `dd_analysis`, `dd_key_catalyst`, `dd_fatal_flaw`

### 9.2 Due Diligence (core/due_diligence.py - 494 lines)

Manual deep DD tool with streaming output.

| Parameter | Value |
|-----------|-------|
| Model | Claude Opus 4 (`claude-opus-4-5-20251101`) |
| Max tokens | 8,000 |
| Thinking budget | 10,000 |
| Streaming | Yes (real-time progress) |

**Note:** The `USER_PROMPT_TEMPLATE` (line ~180) still references "£5,000" and "UK->US FX costs" - legacy UK audience language that should be updated to USD.

---

*End of Document 3*
