# CLAUDE.md - BoS Momentum Scanner

> **Comprehensive System Documentation**
> For AI analysis (Gemini Pro, Claude), development planning, and daily operations.
> Last updated: January 2026

---

# TIER 1: OPERATIONAL QUICK REFERENCE

## System Identity

| Attribute | Value |
|-----------|-------|
| **Project** | BoS Momentum Scanner |
| **Purpose** | Weekly momentum trading scanner for US stocks |
| **Newsletter** | [Sterling Signals](https://sterlingsignals.substack.com) |
| **X/Twitter** | [@SterlingSignals](https://twitter.com/SterlingSignals), [@AlexanderSterling](https://twitter.com/AlexanderSterling) |
| **Target Audience** | UK ISA investors seeking US equity exposure |

### Trading Strategy (Internal Reference Only)

```
ENTRY:  Weekly HMA Pivot BUY + Beta ≥1.5 + Banker ≥55 + Theme Confirmed + Gatekeeper PASS
EXIT:   20% trailing stop from highest weekly close OR Weekly BoS Down (tighten stop)
```

> **IMPORTANT:** These specific strategy details are for internal documentation only.
> Public content must use approved marketing language (see below).

---

## MARKETING LANGUAGE RULES (CRITICAL)

All public-facing content (tweets, newsletter, notes) must follow these rules.

### NEVER Reveal These Details

| Internal Term | Public Alternative |
|---------------|-------------------|
| "20% trailing stop" | "Disciplined risk management" |
| "HMA pivots" | "Proprietary technical signals" |
| "Banker indicator" / "Banker >= 55" | "Smart money accumulation signals" |
| "Beta >= 1.5" | "High-momentum screening criteria" |
| "Weekly BoS (Break of Structure)" | "Technical trend confirmation" |
| "Tier 1/2/3 classification" | "Signal strength indicators" |

### Approved Marketing Phrases

**System Description:**
- "Proprietary multi-step screening process"
- "5-gate quality system"
- "Filters 1,800 stocks down to 3-5 winners"
- "Systematic approach to momentum trading"

**Signal Detection:**
- "Smart money accumulation signals"
- "Institutional flow tracking"
- "Theme momentum confirmation"
- "Technical entry/exit signals"
- "Proprietary breakout detection"

**Risk Management:**
- "Disciplined risk management"
- "Predetermined exit strategy"
- "Capital preservation focus"
- "Systematic position sizing"

### Content Themes to Emphasize

1. **Following Smart Money** - Institutional flows, accumulation patterns
2. **Bottleneck Plays** - Infrastructure, supply chain, capacity constraints
3. **Theme Momentum** - Hot sectors, rotating capital, catalyst-driven
4. **Contrarian Opportunities** - Cold themes, oversold setups, patience plays
5. **Discipline Over FOMO** - Patience, systematic approach, no chasing

### Honesty Rules

Even with marketing language, NEVER hide losses:
- Always show full P&L including losers
- Frame losses positively: "Stop hit = system working as designed"
- When underwater: "Down but managing risk - disciplined exits in place"

> **Full marketing guidelines:** See `SYSTEM_OVERVIEW.md` Section 2

---

### Weekly Schedule

| Day | Automated | Manual |
|-----|-----------|--------|
| **Friday PM** | Full scan, DD, tweets, newsletter via GitHub Actions | - |
| **Saturday AM** | Tweet posting (5/day) | Copy newsletter to Substack, add charts |
| **Sunday-Monday** | Tweet posting (5/day) | - |
| **Tuesday** | Tweet posting, Substack Note ready | Post Tuesday "Portfolio Pulse" note |
| **Wednesday** | Tweet posting (5/day) | - |
| **Thursday** | Tweet posting, Substack Note ready | Post Thursday "Trade Spotlight" note |

**Only manual steps:** Substack newsletter publish (~10 min) + Tuesday/Thursday notes (~2 min each)

---

## Command Cheat Sheet

### Production Scan (Costs ~$1-3)
```bash
python scanner.py --web-search              # Full pipeline with web search
python scanner.py --web-search --top 50     # Limit to top 50 by beta
```

### Free Testing (No API Costs)
```bash
python scanner.py --no-llm                  # Technical scan only
python scanner.py --no-llm --top 20         # Quick test with 20 tickers
python scanner.py --no-momentum             # Themes only, skip gatekeeper
```

### Portfolio Management
```bash
python portfolio_manager.py --report        # View portfolio summary
python portfolio_manager.py --update        # Refresh prices via yfinance
python portfolio_manager.py --export        # Export for Google Sheets
python portfolio_manager.py --add TICKER --price 10.50 --theme "AI"   # Manual add
python portfolio_manager.py --exit TICKER --exit-price 15.00          # Manual exit
python portfolio_manager.py --migrate       # One-time: migrate legacy files
```

### Content Generation
```bash
python tweet_generator.py                   # Generate 35 weekly tweets
python newsletter_compiler.py --full        # Compile full newsletter with DD
python substack_notes_generator.py          # Generate Tuesday/Thursday notes
python market_analyzer.py                   # Generate market context analysis
python dd_automator.py                      # Run automated due diligence
```

### Full Pipeline (Automated via GitHub Actions)
```bash
./run_friday.sh                             # Complete Friday pipeline
```

### Debugging
```bash
python verify_bos.py NVDA TSLA PLTR         # Check specific tickers
python diagnose_bos.py 100                  # Universe state analysis
python -m py_compile scanner.py             # Syntax check
```

---

## File Locations Quick Reference

### Output Directory Structure (trades/)

```
trades/
├── current/                        # Latest outputs (always current week)
│   ├── newsletter_briefing.md      # Scanner briefing for newsletter
│   ├── newsletter.html             # Compiled newsletter ready for Substack
│   ├── tweets.json                 # Generated tweets for the week
│   └── substack_notes/
│       ├── tuesday_note.md         # "Portfolio Pulse" mid-week update
│       └── thursday_note.md        # "Trade Spotlight" mid-week update
│
├── weeks/                          # Weekly archives (ISO week format)
│   ├── 2026-W03/                   # Archived week data
│   ├── 2026-W04/
│   └── ...
│
├── charts/                         # TradingView chart screenshots
│   └── chart_manifest.json
│
├── grok_prompts/                   # Daily tweet prompt files
│   ├── latest_grok_prompts.md
│   ├── monday_prompts.md
│   └── ...
│
├── portfolio.csv                   # **Source of truth** - all trades
├── portfolio_google_sheets.csv     # Export with calculated P&L
├── portfolio_backups/              # Auto-timestamped backups
├── signals.json                    # Latest scan results
├── analysis_log.csv                # Historical scan data
├── content_queue.json              # Tweet posting queue
├── latest_report.txt               # Human-readable scan summary (legacy)
└── latest_newsletter_briefing.md   # Newsletter briefing (legacy symlink)
```

**Note:** `latest_*` files maintained for backwards compatibility, but primary outputs are in `current/`

### Source Files

#### Core Pipeline
| File | Purpose |
|------|---------|
| `scanner.py` | Main pipeline orchestrator |
| `thematic_analyzer.py` | LLM theme discovery and scoring |
| `gatekeeper.py` | LLM final quality gate |
| `portfolio_manager.py` | Trade tracking, P&L, Google Sheets export |
| `dd_automator.py` | Automated due diligence for PASS signals |

#### Content Generation
| File | Purpose |
|------|---------|
| `tweet_generator.py` | Generate 35 weekly tweets (5/day) |
| `newsletter_compiler.py` | Compile full newsletter with DD integration |
| `substack_notes_generator.py` | Tuesday/Thursday mid-week Substack notes |
| `market_analyzer.py` | Market context analysis via LLM |
| `chart_capture.py` | TradingView chart screenshots |

#### Automation & Infrastructure
| File | Purpose |
|------|---------|
| `run_friday.sh` | Full Friday pipeline orchestration |
| `output_paths.py` | Centralized folder structure management |
| `.github/workflows/friday_scan.yml` | Friday automated scan |
| `.github/workflows/post_content.yml` | Daily tweet posting |
| `email_notifier.py` | SMTP email notifications |

#### Utilities
| File | Purpose |
|------|---------|
| `verify_bos.py` | Debug signal calculation for specific tickers |
| `diagnose_bos.py` | Universe state analysis |
| `complete_tickers.txt` | Ticker universe (~1800 stocks) |

---

## Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Email notifications
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"
```

---

# TIER 2: SYSTEM ARCHITECTURE

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCANNER.PY PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: LOAD TICKERS                                              Cost: $0 │
│  ├─ Input: complete_tickers.txt (~1800 US stocks)                           │
│  ├─ Also loads: open positions from portfolio.csv                           │
│  └─ Output: List[str] ticker symbols                                        │
│                                                                              │
│  STEP 2: DOWNLOAD SPY BENCHMARK                                    Cost: $0 │
│  ├─ Source: yfinance                                                        │
│  ├─ Period: 1 year daily data                                               │
│  └─ Output: pd.Series of SPY daily returns (for beta calculation)           │
│                                                                              │
│  STEP 3: DOWNLOAD DATA + CALCULATE INDICATORS                      Cost: $0 │
│  ├─ Source: yfinance bulk download                                          │
│  ├─ Calculates:                                                             │
│  │   • Beta = cov(stock, SPY) / var(SPY)                                    │
│  │   • Banker = 50 + ((price/20d-VWAP - 1) * 100 * 5)                       │
│  │   • HMA Pivot BoS (Break of Structure) on weekly timeframe               │
│  │   • 4-week momentum (tracked, not filtered)                              │
│  │   • 20-day return                                                        │
│  └─ Output: Dict[str, Stock] with all fields populated                      │
│                                                                              │
│  STEP 4: TECHNICAL GATE                                            Cost: $0 │
│  ├─ Criteria: Beta ≥ 1.5 AND Weekly BoS UP AND Banker ≥ 55                  │
│  ├─ Tier assignment: TIER1 (>70) / TIER2 (>60) / TIER3 (>55)                │
│  └─ Output: List[Stock] passing technical gate                              │
│                                                                              │
│  STEP 5: THEMATIC ANALYZER (LLM)                          Cost: ~$0.15-0.25 │
│  ├─ Model: Claude Sonnet 4 (claude-sonnet-4-20250514)                       │
│  ├─ Step 1: Identify top 5 themes (PRIME/INVESTABLE/SELECTIVE/AVOID)        │
│  ├─ Step 2: Map tickers to themes, score fit (STRONG/GOOD/MODERATE/POOR)    │
│  ├─ Web search: Optional (adds ~$0.50-1.00 for current news)                │
│  └─ Output: Themes classified, tickers mapped with scores                   │
│                                                                              │
│  STEP 6: GATEKEEPER (LLM)                         Cost: ~$0.15-0.25/stock   │
│  ├─ Model: Claude Sonnet 4                                                  │
│  ├─ Per-stock analysis:                                                     │
│  │   • Catalyst assessment (earnings, events within 90 days)                │
│  │   • Red flag detection (auditor issues, insider selling, etc.)           │
│  │   • Sentiment analysis (analyst trends, short interest)                  │
│  ├─ Web search: 2-3 searches per stock (recommended for production)         │
│  ├─ Decisions: PASS (trade) / CAUTION (watchlist) / FAIL (skip)             │
│  └─ Output: Final decisions with conviction scores 1-5                      │
│                                                                              │
│  STEP 7: CHECK SELL SIGNALS                                        Cost: $0 │
│  ├─ Checks open positions from portfolio.csv                                │
│  ├─ Criteria:                                                               │
│  │   • Weekly BoS DOWN → Caution signal (tighten stop to 15%)               │
│  │   • Price < 80% of highest_close → STOPPED (20% trailing stop)           │
│  └─ Output: List[SellSignal] for positions at risk                          │
│                                                                              │
│  STEP 8: UPDATE PORTFOLIO                                          Cost: $0 │
│  ├─ Add PASS signals to portfolio.csv with entry details                    │
│  ├─ Flag exits for positions hitting stops                                  │
│  ├─ Update highest_close for open positions                                 │
│  ├─ Export to portfolio_google_sheets.csv with calculated fields            │
│  └─ Create backup in portfolio_backups/                                     │
│                                                                              │
│  STEP 9: GENERATE OUTPUTS                                          Cost: $0 │
│  ├─ signals.json - Full scan results in JSON format                         │
│  ├─ analysis_log.csv - Append to historical data                            │
│  ├─ latest_report.txt - Human-readable summary                              │
│  ├─ latest_newsletter_briefing.md - Newsletter data with P&L                │
│  └─ grok_prompts/*.md - 21 weekly X/Twitter prompts                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

TOTAL COST: ~$1-3 per full run with web search enabled
```

---

## Technical Indicator Formulas

### HMA Pivot BoS (Break of Structure)

The Hull Moving Average Pivot system identifies structural breaks in price action.

```python
# Hull Moving Average formula
def HMA(series, n):
    """
    HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))
    Uses HL2 (high+low)/2 as input
    """
    half_period = int(n / 2)
    sqrt_period = int(np.sqrt(n))

    wma_half = WMA(series, half_period)
    wma_full = WMA(series, n)

    raw_hma = 2 * wma_half - wma_full
    hma = WMA(raw_hma, sqrt_period)
    return hma

# Parameters
n = 21  # periods (weekly timeframe)
k = 1   # pivot lookback

# Pivot detection
pivot_high = HMA[i] > max(HMA[i-k], HMA[i+k])  # Local maximum
pivot_low = HMA[i] < min(HMA[i-k], HMA[i+k])   # Local minimum

# Signal generation (step lines)
upper_step_line = most recent pivot high value
lower_step_line = most recent pivot low value

BUY_SIGNAL:  lower_step_line changed (new pivot low established)
SELL_SIGNAL: upper_step_line changed (new pivot high established)

# Weekly resampling
Daily OHLCV data resampled to weekly (Friday close)
```

### Beta Calculation

```python
def calculate_beta(stock_returns, spy_returns):
    """
    Beta = Covariance(stock, SPY) / Variance(SPY)

    Period: 1 year of daily returns
    Minimum data points: 60 trading days
    Threshold for entry: Beta >= 1.5
    """
    covariance = np.cov(stock_returns, spy_returns)[0, 1]
    variance = np.var(spy_returns)
    beta = covariance / variance
    return beta
```

### Banker (Institutional Accumulation Score)

```python
def calculate_banker(df, period=20):
    """
    Banker measures deviation from 20-day VWAP, scaled to 50-centered score.

    Formula: banker = 50 + ((price/vwap - 1) * 100 * 5)

    Interpretation:
      50 = At VWAP (neutral)
      55 = 1% above VWAP (entry threshold)
      60 = 2% above VWAP (TIER2)
      70 = 4% above VWAP (TIER1 - strong accumulation)

    Tier assignment:
      TIER1: banker > 70 (4%+ above VWAP)
      TIER2: banker > 60 (2%+ above VWAP)
      TIER3: banker > 55 (1%+ above VWAP)
    """
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).rolling(period).sum() / df['Volume'].rolling(period).sum()

    deviation_pct = (df['Close'] / vwap - 1) * 100
    banker = 50 + (deviation_pct * 5)

    return banker.iloc[-1]
```

### Theme Scoring (Thematic Analyzer)

```python
# Composite score calculation (0-10 scale)
composite_score = (
    catalyst_score * 0.40 +    # Upcoming catalysts (40% weight)
    momentum_score * 0.25 +    # Price/flow momentum (25% weight)
    crowding_score * 0.20 +    # Positioning/crowding (20% weight)
    runway_score * 0.15        # Future potential (15% weight)
)

# Classification thresholds
PRIME:      composite_score >= 7.5  # Highest conviction
INVESTABLE: 6.0 <= composite_score < 7.5  # Good opportunities
SELECTIVE:  4.5 <= composite_score < 6.0  # Mixed signals
AVOID:      composite_score < 4.5  # Stay away
```

---

## Data Structures (Python Definitions)

### Stock Dataclass (scanner.py)

```python
@dataclass
class Stock:
    # Core fields (always populated)
    symbol: str
    price: float = 0.0
    beta: float = 0.0
    banker: float = 0.0
    bos_bullish: bool = False
    bos_bearish: bool = False
    bos_debug: dict = field(default_factory=dict)
    return_20d: float = 0.0
    momentum_4w: float = 0.0
    tier: str = ""  # TIER1, TIER2, TIER3

    # Thematic analyzer fields (populated in Step 5)
    theme: str = ""
    theme_score: float = 0.0
    pure_play_score: int = 0  # 0-100%
    theme_verdict: str = ""   # STRONG FIT, GOOD FIT, MODERATE FIT, POOR FIT

    # Gatekeeper fields (populated in Step 6)
    final_decision: str = ""  # TRADE, CONSIDER, SKIP
    conviction: int = 0       # 1-5
    catalyst_summary: str = ""
    red_flag_level: str = ""  # CLEAN, MINOR, SEVERE
    action: str = ""          # Recommended action
    bullish_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    reasoning: str = ""
```

### Trade Dataclass (portfolio_manager.py)

```python
class TradeStatus(Enum):
    OPEN = "OPEN"       # Active position being tracked
    CLOSED = "CLOSED"   # Exited manually (profit/strategic)
    STOPPED = "STOPPED" # Hit 20% trailing stop

@dataclass
class Trade:
    # Stored in CSV
    ticker: str
    status: str = "OPEN"
    entry_date: str = ""
    entry_price: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    highest_close: float = 0.0
    theme: str = ""
    tier: str = ""          # TIER1, TIER2, TIER3
    signal_type: str = ""   # TRADE, CONSIDER
    conviction: int = 0
    notes: str = ""

    # Calculated in-memory (not stored)
    current_price: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    stop_level: float = 0.0
    days_held: int = 0
    distance_to_stop_pct: float = 0.0
    stop_alert: bool = False  # True if within 5% of stop
```

### Theme Dataclass (thematic_analyzer.py)

```python
@dataclass
class Theme:
    rank: int
    name: str
    classification: str = "INVESTABLE"  # PRIME, INVESTABLE, SELECTIVE, AVOID
    theme_type: str = "TREND"           # TREND, BOTTLENECK, CONTRARIAN
    composite_score: float = 0.0        # 0-10
    catalyst_score: float = 0.0
    momentum_score: float = 0.0
    crowding_score: float = 0.0
    runway_score: float = 0.0
    thesis_summary: str = ""
    key_catalysts: List[str] = field(default_factory=list)
    primary_etfs: List[str] = field(default_factory=list)
    crowding_indicator: str = "Moderate"  # Low, Moderate, High
```

### GatekeeperResult Dataclass (gatekeeper.py)

```python
class GateDecision(Enum):
    PASS = "PASS"       # Trade at next open
    CAUTION = "CAUTION" # Watchlist only
    FAIL = "FAIL"       # Skip

@dataclass
class GatekeeperResult:
    ticker: str
    decision: GateDecision
    conviction: int             # 1-5
    theme: str
    theme_fit: str              # STRONG, GOOD, MODERATE
    catalyst_present: bool
    catalyst_summary: str
    days_to_catalyst: int
    red_flag_level: str         # CLEAN, MINOR, SEVERE
    red_flags: List[str]
    analyst_trend: str          # BULLISH, NEUTRAL, BEARISH
    short_interest_pct: float
    key_bullish: List[str]      # Top 3 bullish factors
    key_risks: List[str]        # Top 3 risk factors
    reasoning: str
    action: str                 # Recommended action
```

### SellSignal Dataclass (scanner.py)

```python
@dataclass
class SellSignal:
    symbol: str
    price: float
    reason: str           # "Weekly BoS Down" or "20% Trailing Stop"
    entry_price: float
    highest_close: float
    pnl_pct: float
```

---

## Output File Schemas

### portfolio.csv

```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes
RCAT,OPEN,2025-12-29,8.50,,,12.19,Drone Technology,TIER1,TRADE,4,Scanner signal
IBKR,OPEN,2025-12-29,65.00,,,72.93,Financials,TIER1,TRADE,5,Scanner signal
OKLO,CLOSED,2024-11-15,22.00,2025-01-08,28.50,28.50,Nuclear,TIER1,TRADE,4,Manual exit - took profits
SMCI,STOPPED,2024-10-01,45.00,2025-01-10,36.00,52.00,AI Infrastructure,TIER2,TRADE,3,Hit 20% trailing stop
```

### portfolio_google_sheets.csv (with calculated fields)

```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,current_price,pnl_pct,pnl_usd,stop_level,days_held,distance_to_stop,stop_alert
RCAT,OPEN,2025-12-29,8.50,,,12.19,Drone Technology,TIER1,TRADE,4,Scanner signal,13.25,55.9%,475,9.75,23,26.4%,
```

**Google Sheets Setup:**
Replace `current_price` column with formula: `=IF(B2="OPEN", GOOGLEFINANCE(A2, "price"), G2)`

### signals.json

```json
{
  "timestamp": "2026-01-18 22:06:24",
  "timeframe": "WEEKLY",
  "entry_criteria": "Weekly BoS Up + Hot Theme + TRADE/CONSIDER decision",
  "exit_criteria": "Weekly BoS Down OR 20.0% trailing stop",
  "stats": {
    "tickers_loaded": 1817,
    "data_downloaded": 1814,
    "beta_gte_1_5": 485,
    "weekly_bos_up": 48,
    "technical_signals": 44,
    "theme_confirmed": 17,
    "final_trade": 6,
    "final_consider": 7
  },
  "themes": [
    {
      "name": "AI Infrastructure",
      "classification": "PRIME",
      "composite_score": 8.2,
      "thesis_summary": "..."
    }
  ],
  "buy_signals": [
    {
      "symbol": "INOD",
      "tier": "TIER1",
      "price": 61.54,
      "beta": 2.48,
      "banker": 78.3,
      "momentum_4w": 12.5,
      "return_20d": 8.2,
      "theme": "Power Grid Infrastructure",
      "theme_score": 7.8,
      "pure_play_score": 85,
      "theme_verdict": "STRONG FIT",
      "final_decision": "TRADE",
      "conviction": 4,
      "catalyst_summary": "Earnings in 3 weeks, infrastructure bill tailwind",
      "red_flag_level": "CLEAN",
      "bullish_factors": ["Strong institutional buying", "Theme leader", "Catalyst upcoming"],
      "risk_factors": ["High valuation", "Concentrated customer base"],
      "reasoning": "Strong theme fit with near-term catalyst...",
      "action": "Enter Monday at market open, 2% position size"
    }
  ],
  "sell_signals": [],
  "caution_signals": [
    {
      "symbol": "VNET",
      "reason": "Weekly BoS Down",
      "action": "Tighten stop to 15% from high"
    }
  ]
}
```

### latest_newsletter_briefing.md Structure

```markdown
# Weekly Scanner Briefing - Week Ending January 17, 2026

## Performance Summary
- Unrealized P&L: +32.5% ($4,250)
- Open Positions: 6
- Win Rate (closed): 75%
- Avg Winner: +42.3% | Avg Loser: -18.2%

## Recently Closed (Last 7 Days)
| Ticker | Exit Date | Entry | Exit | P&L | Reason |
|--------|-----------|-------|------|-----|--------|
| OKLO | 2025-01-08 | $22.00 | $28.50 | +29.5% | Took profits |

## Hot Themes This Week

### PRIME Themes (Highest Conviction)
**AI Infrastructure** (TREND)
- Score: 8.2/10
- Thesis: Data center buildout accelerating...
- Catalysts: NVDA earnings, hyperscaler CapEx guidance

### INVESTABLE Themes
**Power Grid Infrastructure** (BOTTLENECK)
- Score: 7.1/10
- Thesis: Grid modernization spending...

### SELECTIVE Themes
**Quantum Computing** (CONTRARIAN)
- Score: 5.2/10

### AVOID Themes
**Legacy Retail** (TREND)
- Score: 3.1/10

## PASS - Ready for Entry

### INOD
| Metric | Value |
|--------|-------|
| Price | $61.54 |
| Theme | Power Grid Infrastructure (STRONG FIT) |
| Tier | TIER1 |
| Beta | 2.48 |
| Banker | 78.3 |
| Conviction | 4/5 |

**Bullish Factors:**
- Strong institutional accumulation
- Infrastructure bill beneficiary
- Earnings catalyst in 3 weeks

**Risk Factors:**
- Concentrated customer base
- High valuation vs peers

**Analysis:** [Gatekeeper reasoning]

**Recommended Action:** Enter Monday at market open, 2% position

[CHART: INOD]

## CAUTION - Watchlist

### IONQ
| Metric | Value |
|--------|-------|
| Price | $42.15 |
| Theme | Quantum Computing (GOOD FIT) |
| Tier | TIER2 |
| Conviction | 3/5 |

**Concern:** Extended move, wait for pullback

## Open Positions

| Ticker | Entry | Current | P&L | Days | Theme | Stop Distance |
|--------|-------|---------|-----|------|-------|---------------|
| RCAT | $8.50 | $13.25 | +55.9% | 23 | Drone Tech | 26.4% |
| IBKR | $65.00 | $72.93 | +12.2% | 23 | Financials | 18.5% |
| VNET | $12.00 | $10.80 | -10.0% | 45 | Cloud | 8.2% |

**Stop Distance Indicators:** >15% safe | 10-15% watch | <10% alert

## Caution Signals

### VNET
- **Reason:** Weekly BoS Down
- **Current P&L:** -10.0%
- **Action:** Tighten stop to 15% from high ($11.50 -> stop at $9.78)

## Scan Statistics
- Tickers scanned: 1,817
- Weekly BoS Up: 48
- Technical signals: 44
- Theme confirmed: 17
- PASS signals: 6
- CAUTION signals: 7
```

---

## LLM Integration Details

### Model Configuration

| Component | Model | Max Tokens | Web Search |
|-----------|-------|------------|------------|
| Thematic Analyzer | `claude-sonnet-4-20250514` | 12,000 | Optional |
| Gatekeeper | `claude-sonnet-4-20250514` | 3,000 | Recommended |

### API Costs

```
Claude Sonnet 4 Pricing:
  Input:  $3.00 / 1M tokens
  Output: $15.00 / 1M tokens
  Web Search: $0.01 / search

Typical Run Costs:
  Step 5 (Thematic Analyzer):
    - Without web search: ~$0.15
    - With web search: ~$0.25-0.50

  Step 6 (Gatekeeper per stock):
    - Without web search: ~$0.05
    - With web search: ~$0.15-0.25

  Full run (10 stocks, web search):
    - Total: ~$1.50-3.00
```

### Rate Limiting & Error Handling

```python
# Rate limit configuration
INTER_STEP_DELAY = 30.0      # Seconds between analyzer and gatekeeper
INTER_STOCK_DELAY = 8.0      # Seconds between gatekeeper calls
RATE_LIMIT_COOLDOWN = 90.0   # Cooldown on rate limit error
MAX_RETRIES = 8              # Retry attempts on failure

# Exponential backoff on rate limits
wait_time = min(base_wait * (2 ** attempt), max_wait)
```

### Gatekeeper Immediate Disqualifiers

These trigger automatic FAIL:
- Recent auditor resignation/change
- CFO or CEO departure within 90 days
- SEC investigation or accounting restatement
- Severe short report with unaddressed allegations
- Upcoming dilution event (shelf registration, ATM active)
- Insider selling > 10% in last 30 days

---

## Grok Prompts System

### Overview

Generates 21 contextual X/Twitter prompts per week (3 per day) based on scanner outputs. Prompts are designed for real-time posting via Grok (X's AI).

### Weekly Schedule

| Day | Slot 1 (08:00) | Slot 2 (12:00) | Slot 3 (18:00) |
|-----|----------------|----------------|----------------|
| **Mon** | Week Ahead Preview | Hot Theme Deep Dive | Position Update |
| **Tue** | Buy Signal / Scanner Stats | Cold Theme / Lesson | Watchlist Stock |
| **Wed** | Market Pulse | Theme Comparison | Sell Signal / Position |
| **Thu** | Second Buy Signal | Hot Theme 2 / Lesson | Watchlist 2 |
| **Fri** | Scanner Stats Teaser | Cold Theme 2 | Position Update 3 |
| **Sat** | Newsletter Drop | Buy Signal Deep Dive | Sell Signal / Why Passed |
| **Sun** | Engagement (no sell) | Trading Lesson | Week Ahead Preview |

### Prompt Categories

| Category | Purpose | Data Source |
|----------|---------|-------------|
| `scanner_results` | Funnel stats (1800->48->6) | scan_stats |
| `theme_hot` | PRIME/INVESTABLE theme analysis | themes_data |
| `theme_cold` | SELECTIVE/AVOID themes | themes_data |
| `buy_signal` | New PASS signal spotlight | pass_signals |
| `position_update` | Open position P&L | open_positions |
| `sell_signal` | Exit/stop alerts | sell_signals |
| `watchlist` | CAUTION signal analysis | caution_signals |
| `market_pulse` | Daily market performance | Live search |
| `educational` | Trading methodology | Static templates |
| `engagement` | Community building | Static templates |

### Live Price Feature

Position update prompts instruct Grok to look up current prices:

```
POSITION CONTEXT (may be outdated - look up current price):
Ticker: $RCAT
Entry: $8.50 on 2025-12-29
Theme: Drone Technology | Tier: TIER1
Days Held: ~23
Snapshot P&L: +55.9% (verify with current price)

---

IMPORTANT: The P&L above may be stale. Before drafting:
1. Look up the CURRENT price of $RCAT
2. Calculate the LIVE P&L: ((current_price / 8.50) - 1) * 100
```

### Output Files

| File | Purpose |
|------|---------|
| `latest_grok_prompts.md` | Full prompts in markdown |
| `grok_prompts_summary.txt` | Plain text for terminal |
| `{day}_prompts.md` | Day-by-day convenience files |
| `grok_prompts_YYYYMMDD.md` | Dated archives |

---

## Newsletter Generation

### Workflow

1. **Friday PM:** Run scanner -> generates `latest_newsletter_briefing.md`
2. **Saturday AM:**
   - Run `python newsletter_prompts.py market` -> get market context prompt
   - Paste to Claude, get market analysis
3. **Optional DD:**
   - Run `python due_diligence_prompts.py TICKER "Theme"` for each PASS signal
   - Get Deal Memo with 50%+ path analysis
4. **Compile:**
   - Run `python newsletter_prompts.py compile`
   - Paste with market context + briefing + DD summaries
   - Get publication-ready markdown
5. **Publish:**
   - Copy to Substack
   - Add TradingView charts at [CHART: TICKER] placeholders
   - Publish

### Due Diligence Deal Memo

5-phase methodology for 50%+ return validation:

| Phase | Focus | Key Questions |
|-------|-------|---------------|
| 1. Explosive Growth | Revenue, margins, ROIC | Is growth accelerating? |
| 2. Hidden Catalysts | Non-consensus events | What hasn't market priced? |
| 3. Bear Killer | Short thesis rebuttal | Why is bear case wrong? |
| 4. Valuation Reality | Multiple analysis | What multiple is justified? |
| 5. Synthesis | Final recommendation | Path to 50%+ upside? |

---

## Email Notification System

### Configuration

```bash
# Gmail setup (requires App Password)
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="your.email@gmail.com"
export EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"  # App Password, not regular password
export EMAIL_RECIPIENTS="recipient1@email.com,recipient2@email.com"
```

### Supported Providers

| Provider | SMTP Server | Port | Notes |
|----------|-------------|------|-------|
| Gmail | smtp.gmail.com | 587 | Requires App Password |
| Outlook | smtp.office365.com | 587 | |
| Yahoo | smtp.mail.yahoo.com | 587 | Requires App Password |
| Custom | Your server | 587/465 | |

---

## macOS Scheduler Setup

### Automated Weekly Scans

```bash
# Setup scheduler (runs Sunday 21:30 by default)
python setup_scheduler.py

# Custom time
python setup_scheduler.py --time "18:00" --day "Friday"

# Remove scheduler
python setup_scheduler.py --remove
```

### launchd Configuration

Creates plist at `~/Library/LaunchAgents/com.bos.scanner.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bos.scanner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/run_scanner.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>21</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
</dict>
</plist>
```

---

# TIER 3: INTEGRATION & EXTENSION

## Current External APIs

| API | Purpose | Authentication | Rate Limits |
|-----|---------|----------------|-------------|
| **yfinance** | Stock data download | None (free) | ~2000 req/hour |
| **Anthropic Claude** | LLM analysis | `ANTHROPIC_API_KEY` | Tier-based |
| **Twitter/X API** | Tweet posting | OAuth 1.0a (GitHub Secrets) | 1500 tweets/15 min |
| **SMTP** | Email notifications | Username/password | Provider-dependent |

---

## Implemented Integrations

### X/Twitter Auto-Posting (IMPLEMENTED)

**Status:** Fully operational via GitHub Actions

**Components:**
- `tweet_generator.py` - Generates 35 tweets per week (5/day)
- `content_queue.json` - Tweet queue with posting status
- `.github/workflows/post_content.yml` - Posts 5 tweets daily

**Configuration (GitHub Secrets):**
```
TWITTER_API_KEY
TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_SECRET
```

**Schedule (UK Time):**
| Slot | Time | Content Type |
|------|------|--------------|
| 1 | 07:00 | System promo / Educational |
| 2 | 09:00 | Theme analysis / Buy signal |
| 3 | 12:30 | Position update with chart |
| 4 | 15:30 | Theme / Watchlist |
| 5 | 19:00 | Engagement / Lessons |

---

### Substack Notes (IMPLEMENTED)

**Status:** Fully operational, generated every Friday

**Components:**
- `substack_notes_generator.py` - Generates Tuesday/Thursday notes
- `trades/current/substack_notes/tuesday_note.md` - "Portfolio Pulse" update
- `trades/current/substack_notes/thursday_note.md` - "Trade Spotlight" update

**Manual step:** Copy notes to Substack Notes interface (~2 min each)

---

## Future Integration Opportunities

### Substack Newsletter Auto-Publish (MEDIUM PRIORITY)

**Current State:**
- `newsletter_compiler.py --full` generates complete HTML newsletter
- User manually copies to Substack editor
- Charts added manually via TradingView screenshots

**Target State:**
- Automated publication via API or browser automation
- Charts auto-embedded

**Options:**

| Option | Feasibility | Notes |
|--------|-------------|-------|
| **Email-to-Publish** | High | Substack supports email posting |
| **Browser Automation** | Medium | Playwright/Selenium, fragile |
| **Substack API** | Low | No public API currently |

**Interim Solution (Email-to-Publish):**

```python
# Potential: substack_publisher.py

def publish_via_email(newsletter_content, subject):
    """
    Send newsletter to Substack's email-to-publish address.
    Format: your-publication@mg.substack.com
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = SUBSTACK_PUBLISH_EMAIL

    # HTML content with embedded charts
    html_content = convert_markdown_to_html(newsletter_content)
    msg.attach(MIMEText(html_content, 'html'))

    # Send
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
```

---

### TradingView Chart Integration (IMPLEMENTED)

**Status:** Operational via `chart_capture.py`

**Components:**
- `chart_capture.py` - Playwright-based TradingView screenshot capture
- `trades/charts/` - Output directory for chart images
- `trades/charts/chart_manifest.json` - Tracks captured charts with paths

**Configuration:**
- Layout ID: `rxC5j0SK` (saved with custom indicators)
- X/Twitter size: 1200x800 pixels
- Indicator names hidden via JavaScript injection

**Usage:**
```bash
# Capture specific tickers
python chart_capture.py --tickers AAPL,NVDA

# Capture from signals file
python chart_capture.py --tickers-from trades/signals.json

# Headless mode (for CI)
python chart_capture.py --tickers AAPL --headless
```

**Integration:**
- Position update tweets include `image_path` field
- `twitter_poster.py` uploads chart via Twitter API v1.1
- Attaches media_id to tweet via Twitter API v2

**Note:** Requires local run with TradingView login (not fully CI-compatible)

**Implementation Options:**

| Option | Feasibility | Quality | Notes |
|--------|-------------|---------|-------|
| **Selenium/Playwright** | High | High | Browser automation, uses user's indicators |
| **TradingView Snapshot API** | Low | High | Requires partnership |
| **Pine Script Webhooks** | Medium | Medium | Alert-based, limited |
| **mplfinance (Python)** | High | Medium | No custom indicators |

**Recommended Implementation (Playwright):**

```python
# New file: chart_capture.py

from playwright.sync_api import sync_playwright

def capture_tradingview_chart(ticker: str, output_path: str):
    """
    Capture TradingView chart with user's indicators.

    Prerequisites:
    - TradingView account logged in (saved browser profile)
    - Custom indicators saved to chart template
    """
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="~/.tradingview_profile",
            headless=True
        )
        page = browser.new_page()

        # Navigate to chart
        page.goto(f"https://www.tradingview.com/chart/?symbol={ticker}")
        page.wait_for_load_state("networkidle")

        # Wait for indicators to load
        page.wait_for_timeout(5000)

        # Capture screenshot
        chart_element = page.locator(".chart-container")
        chart_element.screenshot(path=output_path)

        browser.close()

def generate_all_charts(tickers: List[str]):
    """Generate charts for all positions and signals."""
    output_dir = TRADES_DIR / "charts"
    output_dir.mkdir(exist_ok=True)

    for ticker in tickers:
        output_path = output_dir / f"{ticker}_{datetime.now():%Y%m%d}.png"
        capture_tradingview_chart(ticker, output_path)
        print(f"  Chart saved: {output_path}")
```

**Integration with Scanner:**

```python
# In scanner.py, after generating outputs

if not args.no_charts:
    from chart_capture import generate_all_charts

    # Get tickers needing charts
    chart_tickers = []
    chart_tickers.extend([s.symbol for s in confirmed if s.final_decision == "TRADE"])
    chart_tickers.extend([t.ticker for t in pm.get_open_positions()])

    generate_all_charts(chart_tickers)
```

**Chart Embedding:**

```python
# In grok_prompts_generator.py
def create_position_update_prompt(position, data):
    chart_path = TRADES_DIR / "charts" / f"{position['ticker']}_latest.png"

    prompt = GrokPrompt(
        # ... existing fields ...
        visual_suggestion=f"Attach: {chart_path}" if chart_path.exists() else "Screenshot from TradingView"
    )
```

---

### Google Sheets Live Sync (LOW PRIORITY)

**Current State:**
- `portfolio_google_sheets.csv` exported by scanner
- User manually imports to Google Sheets
- GOOGLEFINANCE formulas added manually

**Target State:**
- Auto-sync on each scan
- Preserve formulas and formatting

**Implementation:**

```python
# New file: sheets_sync.py

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def sync_portfolio_to_sheets(portfolio_data: List[Dict]):
    """
    Sync portfolio data to Google Sheets.

    Prerequisites:
    - Service account created in Google Cloud Console
    - Spreadsheet shared with service account email
    - GOOGLE_SHEETS_CREDENTIALS_PATH env var set
    - GOOGLE_SHEETS_SPREADSHEET_ID env var set
    """
    creds = Credentials.from_service_account_file(
        os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH'),
        scopes=SCOPES
    )

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    # Clear existing data (preserve header and formulas)
    sheet.values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range='Portfolio!A2:L100'
    ).execute()

    # Write new data
    values = [trade_to_row(t) for t in portfolio_data]
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range='Portfolio!A2',
        valueInputOption='USER_ENTERED',
        body={'values': values}
    ).execute()
```

---

### Real-Time Alerts (FUTURE)

**Concept:**
- Intraday price monitoring for stop alerts
- Push notifications when positions approach stops

**Implementation Ideas:**
- Use yfinance streaming or alternative (Alpha Vantage, Polygon.io)
- Check prices every 15 minutes during market hours
- Send alerts via email/SMS/push when within 5% of stop

---

## Extension Patterns

### Adding New Technical Indicators

```python
# Location: scanner.py, after calculate_banker()

def calculate_new_indicator(df: pd.DataFrame) -> float:
    """
    Calculate [indicator name].

    Formula: [explicit formula]

    Args:
        df: Daily OHLCV DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
        Indicator value (float)
    """
    try:
        # Your calculation here
        value = ...
        return value
    except Exception:
        return 0.0

# Add to Stock dataclass
@dataclass
class Stock:
    # ... existing fields ...
    new_indicator: float = 0.0

# Add calculation in download_and_process()
def download_and_process(ticker, spy_data, ...):
    # ... existing code ...
    stock.new_indicator = calculate_new_indicator(df)
```

### Adding New LLM Gates

```python
# Pattern: Create new module like gatekeeper.py

# 1. Define result dataclass
@dataclass
class NewGateResult:
    ticker: str
    decision: str  # PASS, CAUTION, FAIL
    reasoning: str
    # ... additional fields ...

# 2. Define system prompt
NEW_GATE_SYSTEM_PROMPT = """
You are a [role] at a [context].
Your task is to [objective].
...
"""

# 3. Implement run function
def run_new_gate(
    client: anthropic.Anthropic,
    stocks: List[Stock],
    use_web_search: bool = False
) -> List[NewGateResult]:
    results = []
    for stock in stocks:
        # Build user prompt
        user_prompt = f"Analyze {stock.symbol}..."

        # API call
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=NEW_GATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Parse response
        result = parse_response(response.content[0].text)
        results.append(result)

    return results

# 4. Integrate in scanner.py
def run_new_gate_in_scanner(signals: List[Stock], client, **kwargs) -> List[Stock]:
    from new_gate import run_new_gate

    results = run_new_gate(client, signals, **kwargs)

    # Map results back to Stock objects
    for stock in signals:
        result = next((r for r in results if r.ticker == stock.symbol), None)
        if result:
            stock.new_gate_decision = result.decision
            # ... additional mapping ...

    # Filter based on decisions
    passed = [s for s in signals if s.new_gate_decision == "PASS"]
    return passed
```

### Adding New Output Formats

```python
# Location: scanner.py, save_results()

def save_new_format(
    confirmed: List[Stock],
    sell_signals: List[SellSignal],
    stats: ScanStats
) -> Path:
    """Generate [format name] output."""

    output_file = TRADES_DIR / "output.ext"

    # Generate content
    content = {
        "timestamp": datetime.now().isoformat(),
        "signals": [stock_to_dict(s) for s in confirmed],
        # ... additional content ...
    }

    # Write file
    with open(output_file, 'w') as f:
        json.dump(content, f, indent=2)

    print(f"  New format: {output_file}")
    return output_file

# Call from save_results()
def save_results(confirmed, all_assessed, sell_signals, stats, ...):
    # ... existing saves ...
    save_new_format(confirmed, sell_signals, stats)
```

---

## Complete Environment Variables Reference

```bash
# ============================================================
# REQUIRED
# ============================================================

# Anthropic API (for LLM analysis)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# ============================================================
# OPTIONAL: Email Notifications
# ============================================================

export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="your.email@gmail.com"
export EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"  # App Password
export EMAIL_RECIPIENTS="recipient@email.com"

# ============================================================
# FUTURE: X/Twitter Integration
# ============================================================

export TWITTER_API_KEY=""
export TWITTER_API_SECRET=""
export TWITTER_BEARER_TOKEN=""
export TWITTER_ACCESS_TOKEN=""
export TWITTER_ACCESS_SECRET=""

# ============================================================
# FUTURE: Google Sheets Sync
# ============================================================

export GOOGLE_SHEETS_CREDENTIALS_PATH="/path/to/service-account.json"
export GOOGLE_SHEETS_SPREADSHEET_ID="1abc..."

# ============================================================
# FUTURE: Substack Publishing
# ============================================================

export SUBSTACK_PUBLISH_EMAIL="your-publication@mg.substack.com"
```

---

# APPENDICES

## A. Complete Terminal Output Example

```
==============================================================================
              BoS MOMENTUM SCANNER - WEEKLY TIMEFRAME
                      2026-01-17 22:30:00
==============================================================================

  Pipeline: Technical -> Thematic -> Gatekeeper (thorough)
  Cost: ~$1-3/run (web search enabled)
  Schedule: Run WEEKLY (signals only change on Friday close)

  Web search ENABLED:
     - Thematic: Current theme momentum
     - Gatekeeper: 2-3 searches per stock

  Portfolio: 6 open position(s) tracked
     - trades/portfolio.csv
     - Google Sheets export on completion

------------------------------------------------------------------------------
  STEP 1: Loading Tickers
------------------------------------------------------------------------------
  Loaded 1,817 tickers from complete_tickers.txt
  Tracking 6 open position(s): CGON, FIX, IBKR, RCAT, TLN, VNET

------------------------------------------------------------------------------
  STEP 2: Downloading SPY Benchmark
------------------------------------------------------------------------------
  Downloaded 251 days of SPY data

------------------------------------------------------------------------------
  STEP 3: Downloading Stock Data
------------------------------------------------------------------------------
  Downloaded data for 1,814 stocks (3 failed)
  Calculated Beta, Banker, HMA Pivot BoS for all stocks

------------------------------------------------------------------------------
  STEP 4: Technical Gate
------------------------------------------------------------------------------
  Universe Statistics:
    High Beta (>=1.5):  485 stocks
    Weekly BoS Up:      48 stocks
    Banker >=55:        312 stocks

  44 stocks passed technical gate (Beta >=1.5 AND BoS Up AND Banker >=55)

  Top 10 by Banker:
    TIER1  INOD    $61.54  Beta: 2.48  Banker: 78.3
    TIER1  RCAT    $13.25  Beta: 3.12  Banker: 75.1
    ...

------------------------------------------------------------------------------
  STEP 5: Thematic Analyzer
------------------------------------------------------------------------------
  Identifying top investment themes...

  PRIME Themes (Highest Conviction):
     - AI Infrastructure (TREND) - Score: 8.2/10
     - Power Grid Infrastructure (BOTTLENECK) - Score: 7.8/10

  INVESTABLE Themes:
     - Drone Technology (TREND) - Score: 7.1/10
     - Nuclear Renaissance (CONTRARIAN) - Score: 6.8/10

  SELECTIVE Themes:
     - Quantum Computing (CONTRARIAN) - Score: 5.2/10

  AVOID Themes:
     - Legacy Retail (TREND) - Score: 3.1/10

  Mapping 44 tickers to themes...
  17 stocks theme-confirmed

  Step 5 cost: $0.23 (input: 12,450 tokens, output: 2,100 tokens)

------------------------------------------------------------------------------
  STEP 6: Gatekeeper
------------------------------------------------------------------------------
  Running final quality gate on 17 stocks...

  [1/17] INOD... PASS (Conviction: 4/5)
  [2/17] RCAT... PASS (Conviction: 4/5)
  [3/17] IONQ... CAUTION - Extended, wait for pullback
  ...

  Results:
    PASS:    6 stocks (ready to trade)
    CAUTION: 7 stocks (watchlist)
    FAIL:    4 stocks (skip)

  Step 6 cost: $2.15 (17 stocks x ~$0.13/stock)

------------------------------------------------------------------------------
  STEP 7: Checking Sell Signals
------------------------------------------------------------------------------
  Checking 6 open positions...

  VNET: Weekly BoS Down - Tighten stop to 15%
  RCAT: Bullish, +55.9% from entry
  IBKR: Bullish, +12.2% from entry
  ...

------------------------------------------------------------------------------
  PORTFOLIO UPDATE
------------------------------------------------------------------------------
  Portfolio: 6 open, 2 closed
  CSV: trades/portfolio.csv
  Google Sheets export: trades/portfolio_google_sheets.csv

  Performance (closed trades):
     Win Rate: 75% | Avg Win: +42.3% | Avg Loss: -18.2%

------------------------------------------------------------------------------
  GROK PROMPTS GENERATED
------------------------------------------------------------------------------
  Generated 21 Grok prompts for the week

  Grok prompts: trades/grok_prompts/latest_grok_prompts.md

  Weekly Schedule:
     Monday     | Week Ahead           | Hot Theme            | Position Update
     Tuesday    | Buy Signal           | Cold Theme           | Watchlist
     Wednesday  | Market Pulse         | Theme Compare        | Sell Signal
     Thursday   | Buy Signal 2         | Hot Theme 2          | Watchlist 2
     Friday     | Scanner Stats        | Cold Theme 2         | Position Update
     Saturday   | Newsletter Drop      | Signal Deep Dive     | Why Passed
     Sunday     | Engagement           | Trading Lesson       | Week Ahead

  Copy prompts to Grok (X's AI) to generate ready-to-post tweets

==============================================================================
  FULL GROK PROMPTS (21 FOR THE WEEK)
==============================================================================

  [Full prompts displayed organized by day...]

==============================================================================

  Summary saved: trades/grok_prompts/grok_prompts_summary.txt

------------------------------------------------------------------------------
  RESULTS SAVED
------------------------------------------------------------------------------
  Files:
     - trades/signals_20260117.json
     - trades/analysis_log.csv (appended)
     - trades/report_20260117.txt
     - trades/latest_report.txt
     - trades/latest_newsletter_briefing.md
     - trades/portfolio.csv
     - trades/portfolio_google_sheets.csv
     - trades/grok_prompts/latest_grok_prompts.md

------------------------------------------------------------------------------
  COST SUMMARY
------------------------------------------------------------------------------
  Step 5 (Thematic Analyzer): $0.23
  Step 6 (Gatekeeper):        $2.15
  Web searches:               $0.34
  -----------------------------
  Total:                      $2.72

  Completed in 147.3 seconds
==============================================================================
```

---

## B. Weekly Workflow Checklist

### Friday Evening (After Market Close)

```
[ ] Run full scan
    python scanner.py --web-search

[ ] Review terminal output
    - Note PASS signals
    - Check for sell signals on open positions
    - Review cost summary

[ ] Quick portfolio check
    python portfolio_manager.py --report
```

### Saturday Morning

```
[ ] Review newsletter briefing
    cat trades/latest_newsletter_briefing.md

[ ] Generate market context (optional)
    python newsletter_prompts.py market
    -> Paste to Claude, save output

[ ] Run deep DD on PASS signals (optional)
    python due_diligence_prompts.py TICKER "Theme"
    -> Paste to Claude, save Deal Memos

[ ] Compile newsletter
    python newsletter_prompts.py compile
    -> Paste with market context + briefing + DD
    -> Get publication-ready markdown

[ ] Add TradingView charts
    - Screenshot charts for PASS signals
    - Screenshot charts for open positions
    - Insert at [CHART: TICKER] placeholders

[ ] Publish to Substack
    - Copy markdown to Substack editor
    - Preview and adjust formatting
    - Schedule or publish immediately
```

### Daily (Monday-Sunday)

```
[ ] Morning post (08:00 UK)
    - Open trades/grok_prompts/{day}_prompts.md
    - Copy Slot 1 prompt to Grok
    - Review generated tweet
    - Post to X

[ ] Midday post (12:30 UK)
    - Copy Slot 2 prompt to Grok
    - Post to X

[ ] Evening post (18:00 UK)
    - Copy Slot 3 prompt to Grok
    - Post to X
```

### Mid-Week (Optional)

```
[ ] Check portfolio prices
    python portfolio_manager.py --update

[ ] Check Google Sheets for live P&L
    - Open your synced Google Sheet
    - Review stop distances

[ ] React to market events
    - Adjust prompts if major news
```

---

## C. Troubleshooting

### API Billing Errors

```
Error: "Billing not enabled" or "Insufficient credits"

Solution:
1. Log into console.anthropic.com
2. Go to Billing -> Add payment method
3. Add credits ($10 minimum)
4. Retry scan
```

### yfinance Rate Limits

```
Error: "Too many requests" or "Connection timeout"

Solution:
1. Wait 5-10 minutes
2. Reduce ticker count: --top 50
3. Run during off-peak hours
```

### Missing Environment Variables

```
Error: "ANTHROPIC_API_KEY not set"

Solution:
1. Add to ~/.bashrc or ~/.zshrc:
   export ANTHROPIC_API_KEY="sk-ant-api03-..."
2. Source the file: source ~/.zshrc
3. Verify: echo $ANTHROPIC_API_KEY
```

### Scheduler Not Running (macOS)

```
Problem: Scheduled scan not executing

Solutions:
1. Check laptop wasn't sleeping
   - Energy Saver -> Prevent sleep when display is off

2. Verify launchd status:
   launchctl list | grep bos

3. Check logs:
   cat ~/Library/Logs/bos_scanner.log

4. Reload agent:
   launchctl unload ~/Library/LaunchAgents/com.bos.scanner.plist
   launchctl load ~/Library/LaunchAgents/com.bos.scanner.plist
```

### Portfolio CSV Corruption

```
Problem: Malformed portfolio.csv

Solution:
1. Restore from backup:
   cp trades/portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv trades/portfolio.csv

2. Or recreate from signals.json + manual entry
```

---

## D. Changelog

### 2026-01-21

- **Enhanced CLAUDE.md** - Complete rewrite with three-tier architecture
- **Full Grok prompts in terminal** - All 21 prompts displayed during scan
- **Grok prompts summary file** - `grok_prompts_summary.txt` for easy reference
- **Future integrations documented** - X API, Substack, TradingView, Google Sheets

### 2026-01-13

- **Enhanced newsletter briefing** - Added P&L data, stop distances, performance summary
- **Dynamic Grok prompts** - Prompts instruct Grok to look up current prices
- **Live price fetching** - yfinance integration for accurate P&L at generation time
- **Folder structure cleanup** - Moved files to trades/, created docs/

### 2026-01-06

- **Model upgrade** - Changed to Claude Sonnet 4 for cost efficiency
- **Portfolio manager integration** - Unified trade tracking
- **Google Sheets export** - CSV with calculated fields and formula setup

### 2025-12-29

- **Initial release** - Core scanner pipeline with thematic analyzer and gatekeeper

---

## E. Dependencies

### requirements.txt

```
# Core
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.28  # Use <1.0 for Python 3.9

# LLM
anthropic>=0.18.0

# Optional: Charts
matplotlib>=3.7.0
mplfinance>=0.12.0

# Optional: Browser automation (for TradingView charts)
playwright>=1.40.0

# Optional: Google Sheets
google-auth>=2.0.0
google-api-python-client>=2.0.0
```

### Python Version

- **Recommended:** Python 3.10+
- **Minimum:** Python 3.9 (requires `yfinance<1.0`)

### System Requirements

- macOS, Linux, or Windows
- Internet connection (for yfinance and Anthropic API)
- ~500MB disk space for data and outputs

---

*End of CLAUDE.md*
