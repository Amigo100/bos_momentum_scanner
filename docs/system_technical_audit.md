# BoS Momentum Scanner — Complete System Audit

> **Purpose:** Comprehensive information flow mapping for Claude Opus 4.6 extended thinking session.
> Covers every script, workflow, dependency, schedule, and data handoff in the system.
> Generated: 2026-03-02 | Restored: 2026-03-03
>
> **Companion document:** `docs/system_strategic_intent.md` — explains the *why* behind each subsystem.

---

## Table of Contents

1. [System Overview & Weekly Lifecycle](#1-system-overview)
2. [Phase 1: Friday Scanner Pipeline](#2-friday-scanner)
3. [Phase 2: Manual Claude.ai Analysis](#3-claude-ai-analysis)
4. [Phase 3: Saturday Workflow](#4-saturday-workflow)
5. [Phase 4: Daily Content Pipeline](#5-daily-content)
6. [Phase 5: Live Tweet System](#6-live-tweets)
7. [Portfolio System](#7-portfolio)
8. [GitHub Actions Schedules](#8-schedules)
9. [Complete File Dependency Graph](#9-dependencies)
10. [Environment Variables Reference](#10-env-vars)
11. [Known Issues & Improvement Areas](#11-improvements)

---

## 1. System Overview & Weekly Lifecycle

### What This System Does

The BoS Momentum Scanner is a weekly + daily momentum trading scanner for US stocks that powers:
- **Sterling Signals** Substack newsletter (weekly + daily posts + notes)
- **3 X/Twitter accounts** with automated context-aware tweets (~10 slots/day)
- **Portfolio tracking** with tiered profit locks, equity curve, and Google Sheets export

### Weekly Lifecycle (End-to-End)

```
FRIDAY 16:30 ET ─── Scanner runs (GitHub Actions)
  │                  ├─ Technical signals: signals_technical.json (16 stocks from 1,817)
  │                  ├─ Sell signal notifications (email/WhatsApp)
  │                  └─ Git commit + push
  │
  ▼
FRIDAY EVENING ──── User reviews signals_technical.json
  │                  └─ Pastes into Claude.ai with sterling_prompt_library.md
  │
  ▼
SATURDAY MORNING ── User runs 8 prompts in Claude.ai (Opus 4.6 + extended thinking)
  │                  ├─ Thematic analysis, DD screening, newsletter generation
  │                  ├─ Saves: decisions.json + newsletter.html + signal_history_rows.csv
  │                  └─ Pushes to GitHub
  │
  ▼
SATURDAY 21:00 UTC ─ Saturday workflow runs (GitHub Actions)
  │                   ├─ Merges decisions.json + signals_technical.json → signals.json
  │                   ├─ Updates portfolio.csv (new positions, exits)
  │                   ├─ Generates daily_context.md
  │                   ├─ Archives to weekly folder
  │                   └─ Git commit + push
  │
  ▼
DAILY 07:00 ET ──── Daily content pipeline runs (GitHub Actions)
  │                  ├─ Market analysis (Claude + web search)
  │                  ├─ Daily context doc (post assignment + embedded prompt)
  │                  ├─ 2-3 Substack notes (LLM-generated)
  │                  ├─ Email with daily brief
  │                  └─ Git commit + push
  │
  ▼
DAILY (USER) ────── User opens daily_context.md
  │                  ├─ Copies embedded prompt into Claude.ai
  │                  ├─ Gets HTML post + 3 HTML notes
  │                  └─ Pastes into Substack (~5-10 min)
  │
  ▼
CONTINUOUS ──────── Live tweet system (~10 slots/day weekdays, 2 weekends)
                     ├─ Grok gathers market context
                     ├─ Claude generates 3-account tweet variants
                     ├─ Charts generated via chart-img.com API
                     ├─ Posted to X/Twitter with 10-min staggering
                     └─ Git commit + push
```

---

## 2. Phase 1: Friday Scanner Pipeline

### Entry Points
- **GitHub Actions**: `.github/workflows/friday_scan.yml` (Friday 21:30 UTC = 16:30 ET)
- **Local**: `./run_friday.sh` or `python -m scanner.scanner --archive`

### Pipeline Steps (All $0 cost — no LLM)

| Step | Script | Input | Output | Cost |
|------|--------|-------|--------|------|
| 1. Load tickers | `scanner/scanner.py` | `scanner/complete_tickers.txt` (1,817 stocks) | Ticker list | $0 |
| 2. SPY benchmark | `scanner/scanner.py` | yfinance SPY data | 251 days of returns | $0 |
| 3. Download + indicators | `scanner/scanner.py` | yfinance bulk download | Sterling Grid V6 indicators for all stocks | $0 |
| 4. Technical gate | `scanner/scanner.py` | Indicator data | ~16 stocks passing (HMA pivot + UC/MACD) | $0 |
| 5. Check exits | `scanner/scanner.py` | `portfolio/output/portfolio.csv` | Exit signals (ExD or profit lock breach) | $0 |
| 6. Save results | `scanner/scanner.py` | All above | Multiple output files | $0 |

### Sterling Grid V6 Entry Criteria
```
HMA(21) pivot low detected (structural break)
  AND (UC rising above OR MACD(12,26,9) cross-up)
  AND Price < $25
```

### Sterling Grid V6 Exit Criteria (First Exit — whichever fires first)
```
ExD: HMA pivot high + UC falling on same bar → EXIT immediately
  OR Tiered Profit Lock:
     +200% → 15% trail from peak
     +100% → 20% trail from peak
     +50%  → 25% trail from peak
```

### Position Sizing Tiers
| Tier | Conviction | Entry Condition | Equity % |
|------|-----------|-----------------|----------|
| T1 | 8-10 | UC rising + MACD cross-up | 20% |
| T2 | 7 | MACD cross-up only | 10% |
| T3 | 4-6 | UC rising only | 5% |

### Output Files (Friday)

| File | Path | Format | Purpose |
|------|------|--------|---------|
| Technical signals | `scanner/output/signals_technical.json` | JSON | Raw technical scan results |
| Report | `scanner/output/current/report.txt` | Text | Human-readable summary |
| Analysis log | `scanner/output/analysis_log.csv` | CSV | Append-only historical record |
| Archive | `scanner/output/archive/2026-WXX/` | Mixed | Weekly snapshot |
| Workflow status | `twitter/output/workflow_status.json` | JSON | Execution tracking |

### signals_technical.json Schema (Key Fields)
```json
{
  "timestamp": "2026-03-01 22:06:24",
  "timeframe": "WEEKLY",
  "stats": {
    "tickers_loaded": 1817,
    "data_downloaded": 1814,
    "hma_pivot_low": 48,
    "macd_cross_up": 32,
    "uc_rising": 156,
    "buy_signal": 16,
    "tier_t1": 4, "tier_t2": 6, "tier_t3": 6
  },
  "buy_signals": [
    {
      "symbol": "NGNE", "price": 24.50, "tier": "T3",
      "beta": 1.86, "uc": 17.48, "uc_rising": true,
      "macd_cross_up": false, "hma_pivot_low": true,
      "return_20d": 57.5
    }
  ],
  "sell_signals": [],
  "historical_winners": [], "big_wins": [], "home_runs": []
}
```

### Friday Workflow Notifications
- **Script**: Inline Python in `friday_scan.yml` step calling `utils.notifications`
- **Reads**: `scanner/output/signals_technical.json` (buy + sell signals)
- **Channels**: Email (SMTP) + WhatsApp (Twilio) — both optional

---

## 3. Phase 2: Manual Claude.ai Analysis (User Step)

### What the User Does

1. Opens `scanner/output/signals_technical.json` + `portfolio/output/portfolio.csv`
2. Attaches `substack/docs/sterling_prompt_library.md` to a Claude.ai chat (Opus 4.6 + extended thinking)
3. Runs 8 sequential prompts (R, 0-8) covering:
   - **Prompt R**: Retrospective (review open positions)
   - **Prompt 0**: Market context assessment
   - **Prompt 1**: Thematic analysis (classify themes as PRIME/INVESTABLE/SELECTIVE/AVOID)
   - **Prompt 2**: Batch Phase 1 — thematic screen (filter non-aligned tickers)
   - **Prompt 3**: Batch Phase 2 — DD screening (conviction, catalysts, red flags)
   - **Prompt 4**: Newsletter HTML generation
   - **Prompt 5-6**: Deep dives on selected positions
   - **Prompt 7**: Final export → `decisions.json`

### decisions.json Schema (Complete)
```json
{
  "scan_date": "2026-03-01",
  "scan_week_ending": "2026-03-01",
  "market_regime": "selective",
  "market_context_summary": "S&P 500 near ATH...",

  "retrospective": {
    "open_positions_total": 3,
    "thesis_intact": 2, "thesis_weakening": 1, "thesis_broken": 0,
    "recently_closed": [], "notable_filter_misses": [],
    "calibration_notes": []
  },

  "market_context": {
    "regime": "selective",
    "economic_trajectory": "stable",
    "fed_rate_path": "holding",
    "sectors_accelerating": ["Defense/aerospace"],
    "sectors_decelerating": ["Traditional pharma"],
    "deployment_implication": "Zero positions deployed..."
  },

  "batch_assessment": {
    "batch_quality": "WEAK",
    "wave_alignment": "0 tickers align with established waves",
    "sector_concentration_warning": true
  },

  "review_gate": {
    "session_quality": "WEAK",
    "stocks_approved": [],
    "stocks_adjusted": [{"symbol": "NGNE", "adjustment": "Entry zone not met"}],
    "stocks_removed": [{"symbol": "LRMR", "reason": "System drift"}],
    "conviction_inflation_detected": false
  },

  "new_positions": [
    {
      "symbol": "NGNE", "theme": "Rare disease gene therapy",
      "verdict": "SPEC BUY", "dd_conviction": 6, "conviction": 6,
      "tier": "T3", "price": 20.50, "position_size_pct": 0.05,
      "dd_elevator_pitch": "Rett syndrome gene therapy...",
      "dd_why_now": "BTD designation, specialist accumulation",
      "dd_the_math": "50-100% upside to $30-41",
      "dd_bear_case": "Clinical failure risk",
      "dd_risk_to_monitor": "Patient safety signals",
      "dd_action": "Enter at market, 5% position",
      "bullish_factors": ["BTD designation", "$265M cash"],
      "risk_factors": ["Gene therapy sector bear market"]
    }
  ],

  "no_go": [
    {"symbol": "LRMR", "verdict": "NO GO", "stage_rejected": "review_gate"}
  ],

  "exits": [
    {"symbol": "VNET", "exit_price": 10.80, "reason": "Weekly BoS Down"}
  ],

  "watchlist": [
    {"symbol": "NGNE", "trigger_to_buy": "Price consolidates to $19.50-$21.00"}
  ],

  "themes_this_week": [
    {
      "name": "Rare Disease Gene Therapy",
      "classification": "SELECTIVE",
      "composite_score": 6.8,
      "catalyst_score": 8.0, "momentum_score": 6.5,
      "crowding_score": 7.5, "runway_score": 5.0,
      "thesis_summary": "Gene therapy entering registrational stage...",
      "tickers": ["NGNE", "LRMR", "SGMO"]
    }
  ]
}
```

### User Also Saves
- **`newsletter.html`** → from Prompt 4 output → save to `scanner/output/`
- **`signal_history_rows.csv`** → historical tracking → save to `scanner/output/`
- User pushes all 3 files to GitHub

---

## 4. Phase 3: Saturday Workflow

### Entry Point
- **GitHub Actions**: `.github/workflows/saturday_workflow.yml` (Saturday 21:00 UTC)
- **Prerequisite**: `decisions.json` must exist in `scanner/output/` (user pushed it)

### Pipeline Steps

| Step | Script | What It Does |
|------|--------|-------------|
| 1. Merge | `scanner/merge_decisions.py` | Combines `decisions.json` + `signals_technical.json` → `signals.json` |
| 2. Portfolio | `portfolio/manager.py` | Adds new positions, flags exits, updates prices, exports |
| 3. Market analysis | `substack/market_analyzer.py` | LLM market context (optional, ~$0.15) |
| 4. Daily context | `substack/daily_context_builder.py` | Generates `daily_context.md` for user |
| 5. Newsletter | `saturday_workflow.py` | Copies `newsletter.html` to `substack/output/current/` |
| 6. Archive | `saturday_workflow.py` | Archives to `scanner/output/archive/2026-WXX/` |
| 7. Git commit | workflow yml | Pushes all changes |

### Merge Logic (`scanner/merge_decisions.py`)

**Function**: `merge_signals()`
- Builds ticker lookup from ALL technical signal arrays (buy_signals, pass_signals, consider_signals)
- Maps `new_positions` from decisions.json to matching technical data
- Verdict mapping: STRONG BUY/SPEC BUY → "PASS", else → "CONSIDER"
- Extracts DD fields: elevator_pitch, why_now, the_math, bear_case, risk_to_monitor
- Copies themes_this_week, market_context, assessed signals

**Output**: `scanner/output/signals.json` (MERGED — all downstream systems read this)

### signals.json Schema (Merged — Key Additions vs Technical)
```json
{
  "market_context_summary": "From decisions.json",
  "market_regime": "selective",
  "themes": [{"name": "...", "classification": "PRIME", "composite_score": 8.2}],
  "pass_signals": [
    {
      "symbol": "NGNE", "final_decision": "PASS", "conviction": 6,
      "dd_elevator_pitch": "...", "dd_why_now": "...", "dd_the_math": "...",
      "dd_bear_case": "...", "dd_risk_to_monitor": "...",
      "theme": "Rare disease gene therapy", "theme_score": 6.8
    }
  ],
  "consider_signals": [],
  "buy_signals": [],
  "sell_signals": [],
  "assessed_signals": []
}
```

### Portfolio Updates

| Action | Function | What Happens |
|--------|----------|-------------|
| Add trade | `PortfolioManager.add_trade()` | New row in portfolio.csv with entry details |
| Flag exit | `PortfolioManager.flag_exit()` | Status changed from OPEN to STOPPED/CLOSED |
| Update prices | `PortfolioManager.update_prices()` | yfinance fetch, updates highest_close |
| Export | `PortfolioManager.export_for_google_sheets()` | Generates portfolio_google_sheets.csv |
| Backup | Auto | Creates `portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv` |
| Equity curve | Auto | Appends to `equity_curve.csv` (NAV, SPY, QQQ benchmarks) |

---

## 5. Phase 4: Daily Content Pipeline

### Entry Point
- **GitHub Actions**: `.github/workflows/daily_content.yml` (07:00 ET daily)
- **Dual cron**: `0 12 * * 0-6` (EST) + `0 11 * * 0-6` (EDT) with dedup

### 4-Step Pipeline (`substack/daily_content_pipeline.py`)

Each step is try/except isolated — failure in one doesn't block others.

#### Step 0: Portfolio Price Refresh
- Fetches live prices via yfinance
- Output: `portfolio/output/portfolio_snapshot.json`

#### Step 0.5: Portfolio Dashboard
- Generates equity curve SVG chart with SPY/QQQ benchmarks
- Output: `substack/output/current/portfolio_visual.html` + PNG

#### Step 1: Market Analysis (LLM, ~$0.15-0.25)
- Claude + web search for real-time market context
- Output: `scanner/output/current/market_analysis.md`
- Fallback: Uses cached version if LLM fails

#### Step 2: Daily Context Builder (Critical)
- **Script**: `substack/daily_context_builder.py`
- **Reads**: signals.json, portfolio.csv, portfolio_snapshot.json, market_analysis.md, content_prompt_handbook_v5.md
- **Outputs**:
  - `substack/output/current/daily_context.md` (user-facing document)
  - `substack/output/current/daily_notes_context.json` (notes generator sidecar)

**Post Assignment Logic** (day-based + event overrides):

| Day | Category | Topic Selection |
|-----|----------|----------------|
| Saturday | Performance Review | Weekly newsletter |
| Tuesday | Ticker Deep Dive | Top scanner signal or portfolio winner |
| Wednesday | Theme Rotation | Top PRIME/INVESTABLE theme |
| Thursday | Flex | Second theme, milestone, educational, or second ticker |
| Sun/Mon/Fri | No post | Notes only |

**Event Overrides** (take priority over schedule):
- Position crosses +100% P&L → Performance Review (Hall of Fame)
- Position crosses +50% P&L → Performance Review (Home Run)
- Recent exit detected → Ticker Deep Dive (exit alert)

**daily_context.md Structure**:
1. Header with date
2. TODAY'S POST: Category + topic + reason
3. YOUR PROMPT: Full prompt text from handbook v5 (user copies to Claude.ai)
4. NOTES PROMPT: Universal notes prompt
5. Market context (SPY, QQQ, VIX + analysis)
6. Signal data table
7. New signals list
8. Portfolio snapshot + open positions table
9. Showcase-ready winners (15%+ gains)
10. Theme summary with scores
11. Today's notes schedule (slots + types)

#### Step 3: Daily Notes Generator
- **Script**: `substack/daily_notes_generator.py`
- **Reads**: daily_notes_context.json, content_prompt_handbook_v5.md
- **Outputs**: 2-3 HTML note files per day

**7 Note Types in Rotation Matrix**:
| Type | Content | When Used |
|------|---------|-----------|
| PORTFOLIO_PULSE | Winner receipts, alpha proof | Mon/Wed/Fri/Sun |
| SIGNAL_ALERT | New signals, selectivity | Tue/Sat |
| THEME_MOMENTUM | Single theme focus | Wed/Thu |
| MARKET_REACTION | Quick takes on indices | Mon/Fri |
| SYSTEM_PROOF | Funnel stats, discipline | Mon/Sat |
| LEARNING_NUGGET | Educational (evergreen) | Tue/Thu/Sun |
| ENGAGEMENT_HOOK | Community questions | Fri/Sun |

#### Step 4: Email Notification
- **Script**: `utils/email_notifier.py` via pipeline
- **Sends**: Daily content brief with post assignment + note previews
- **Subject**: `Sterling Signals — {Day}: {topic}`

### Content Prompt Handbook v5 (`substack/docs/content_prompt_handbook_v5.md`)

| Prompt | Category | Output | Length |
|--------|----------|--------|--------|
| Category 1 | Ticker Deep Dive | HTML article | 1000-1500 words |
| Category 2 | Educational | HTML article | 800-1200 words |
| Category 3 | Theme Rotation | HTML dashboard | 1000-1500 words |
| Category 4 | Performance Review | HTML dashboard | 800-1200 words |
| Trade Alert Entry | New position | HTML alert | 500-800 words |
| Trade Alert Exit | Exit position | HTML alert | 500-800 words |
| Daily Notes | Per note type | HTML note | 300-500 words |

---

## 6. Phase 5: Live Tweet System

### Architecture

```
live_tweet.yml trigger (cron slot)
  │
  ├─> live_context_gatherer.py (Grok API — xAI)
  │   └─ Output: live_context.json
  │
  ├─> live_tweet_generator.py (Claude Sonnet)
  │   ├─ Reads: portfolio.csv, signals.json, live_context.json, live_content_queue.json
  │   ├─ 7-priority decision cascade → pick category
  │   ├─ Route to 3-account personas
  │   ├─ Generate 3 tweet variants via LLM
  │   ├─ 14-step validation pipeline
  │   └─ Output: live_content_queue.json (appended)
  │
  ├─> chart_generator.py (chart-img.com REST API)
  │   └─ Output: twitter/output/charts/live_TICKER.png
  │
  └─> poster.py (Twitter API v1.1 + v2)
      ├─ Account 1 (@AlexSterlingGBR) — Immediate
      ├─ Account 2 (@Rdobrogowska) — +10 min
      └─ Account 3 (@JamesSterling) — +20 min
```

### 11 Tweet Categories

| Category | Trigger | Chart? | Thread? |
|----------|---------|--------|---------|
| SELL_SIGNAL | Exit signal in portfolio | Yes | No |
| SIGNAL_ALERT | New PASS/CONSIDER signal | Yes | No |
| RECEIPT | Open position up 5%+ | Yes | Yes (multi-winner) |
| MARKET_COMMENTARY | Market mood/indices | No | No |
| THEME_CATALYST | Breaking news on theme | No | No |
| THEME_LIST | Theme ticker rotation | No | Yes (always) |
| TRENDING_TAKE | FinTwit buzz overlap | No | No |
| TECHNICAL_ANALYSIS | Key levels commentary | No | No |
| EDUCATIONAL | Methodology/psychology | No | No |
| SUBSTACK_TEASER | Today's post hook | No | No |
| ENGAGEMENT | Community building | No | No |

### 7-Priority Decision Cascade

```
Priority 1: SELL_SIGNAL     ← Exit signals (HMA fracture or stop)
Priority 2: SIGNAL_ALERT    ← New buy signals from scanner
Priority 3: RECEIPT          ← Open positions up 5%+ intraday
Priority 4: THEME_CATALYST  ← Breaking news on tracked themes
Priority 5: MARKET_COMMENTARY ← Market open/close context
Priority 6: TRENDING_TAKE / THEME_LIST ← FinTwit overlaps
Priority 7: EDUCATIONAL / ENGAGEMENT ← Content filler
```

### 3-Account Persona Affinity

| Account | Persona | Primary Categories |
|---------|---------|-------------------|
| variant_1 (@AlexSterlingGBR) | The Analyst | RECEIPT, SIGNAL_ALERT, SELL_SIGNAL, TECHNICAL_ANALYSIS |
| variant_2 (@Rdobrogowska) | The Mentor | EDUCATIONAL, THEME_LIST, SUBSTACK_TEASER, THEME_CATALYST |
| variant_3 (@JamesSterling) | The Trader | MARKET_COMMENTARY, RECEIPT, ENGAGEMENT |

### 14-Step Validation Pipeline

1. Length check (280 chars)
2. Chart validation (chart_path exists if required)
3. Ticker extraction ($TICKER mentions)
4. Banned terms check (CRITICAL_BANNED + ALL_BANNED)
5. Loser focus filter (no defeatist language)
6. Portfolio fabrication check (don't claim positions not held)
7. Internal terminology check (no HMA, UC, banker, etc.)
8. Link validation (no malicious URLs)
9. Thread coherence (parent/child consistency)
10. Duplicate detection (SequenceMatcher 0.7, 24h window)
11. Ticker reuse check (MIN_HOURS_BETWEEN_SAME_TICKER = 3h)
12. Category budget check (weekly limits)
13. Daily max tweets check (12 weekday, 4 weekend)
14. LLM repair fallback (re-prompt up to 2 attempts on fail)

### Supporting Modules

| Module | Purpose | Key File |
|--------|---------|----------|
| `twitter/live_context_gatherer.py` | Grok-powered market context | `live_context.json` |
| `twitter/chart_generator.py` | chart-img.com REST API charts | `charts/live_*.png` |
| `twitter/poster.py` | X/Twitter posting + threads | Exit codes: 0/1/2 |
| `twitter/signal_tracker.py` | Win tracking, milestones | `celebrations.json` |
| `twitter/self_quote_tracker.py` | Milestone self-quoting | `tweet_tracking.json` |
| `twitter/health_check.py` | System diagnostics | CLI tool |
| `twitter/cost_tracker.py` | API cost + kill switch | `live_cost_log.json` |

---

## 7. Portfolio System

### Core File: `portfolio/manager.py`

### portfolio.csv Structure
```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,stop_pct,position_size_pct,position_dollars,sizing_gear
```

### Key Operations

| Operation | Method | What Changes |
|-----------|--------|-------------|
| Add trade | `add_trade()` | New OPEN row |
| Flag exit | `flag_exit()` | Status → STOPPED/CLOSED |
| Update prices | `update_prices()` | highest_close updated via yfinance |
| Export | `export_for_google_sheets()` | Calculated P&L, stop levels |
| Backup | Auto on save | `portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv` |

### Equity Curve: `portfolio/output/equity_curve.csv`
```csv
date,nav,return_pct,alpha_vs_spy_pct,alpha_vs_qqq_pct,open_count,closed_count,winners,losers,avg_win_pct,avg_loss_pct,max_drawdown_pct
```

---

## 8. GitHub Actions Schedules (Complete Cron Reference)

### live_tweet.yml — Market Hours (~10 weekday, 2 weekend)

| Slot | Time (ET) | Weekday Crons (EST/EDT) | Weekend Crons |
|------|-----------|------------------------|---------------|
| 1 | 07:30 | `30 12 * * 1-5` / `30 11 * * 1-5` | — |
| 2 | 10:00 | `0 15 * * 1-5` / `0 14 * * 1-5` | `0 15 * * 0,6` / `0 14 * * 0,6` |
| 3 | 12:30 | `30 17 * * 1-5` / `30 16 * * 1-5` | — |
| 4 | 15:30 (POWER HOUR) | `30 20 * * 1-5` / `30 19 * * 1-5` | — |
| 5 | 18:00 | `0 23 * * 1-5` / `0 22 * * 1-5` | `0 21 * * 0,6` / `0 20 * * 0,6` |

### Other Workflows

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `friday_scan.yml` | Friday 21:30 UTC (16:30 ET) | Full weekly technical scan |
| `saturday_workflow.yml` | Saturday 21:00 UTC | Merge decisions + portfolio + archive |
| `daily_content.yml` | Daily 12:00/11:00 UTC (07:00 ET) | Market analysis + context + notes + email |

---

## 9. Complete File Dependency Graph

```
PHASE 1 (Friday Scanner)
  └─ signals_technical.json ──────────────────────────────┐
                                                           │
PHASE 2 (Claude.ai Manual)                                │
  ├─ decisions.json ──────────┐                           │
  ├─ newsletter.html          │                           │
  └─ signal_history_rows.csv  │                           │
                               │                           │
PHASE 3 (Saturday Workflow) ◄──┘                           │
  ├─ merge_decisions.py ◄─────────────────────────────────┘
  │   └─ signals.json (MERGED) ──────────────┐
  ├─ portfolio.csv (updated) ────────────────┤
  ├─ daily_context.md ──────────────────────┤
  └─ newsletter.html → substack/output/     │
                                             │
PHASE 4 (Daily Content) ◄───────────────────┘
  ├─ Reads: signals.json + portfolio.csv
  ├─ daily_context.md (regenerated daily)
  ├─ market_analysis.md (LLM + web search)
  └─ 2-3 note_*.html files

PHASE 5 (Live Tweets) ◄─────────────────────┘
  ├─ Reads: signals.json + portfolio.csv
  ├─ live_context.json (from Grok, per-slot)
  ├─ live_content_queue.json (appended per slot)
  └─ charts/live_*.png (per chart-required tweet)
```

### File Dependency Matrix

| File | Written By | Read By | Frequency |
|------|-----------|---------|-----------|
| `signals_technical.json` | Friday scanner | Saturday merge | Weekly (Fri) |
| `decisions.json` | User (Claude.ai) | Saturday merge | Weekly (Sat AM) |
| `signals.json` | Saturday merge | Daily content, live tweets | Weekly (Sat PM) |
| `portfolio.csv` | Saturday workflow | Daily content, live tweets | Weekly + updates |
| `portfolio_snapshot.json` | Daily pipeline | Daily context builder | Daily |
| `equity_curve.csv` | Portfolio manager | Portfolio visual | Weekly |
| `market_analysis.md` | Market analyzer | Daily context builder | Daily |
| `daily_context.md` | Daily context builder | User (Claude.ai) | Daily |
| `daily_notes_context.json` | Daily context builder | Notes generator | Daily |
| `live_context.json` | Grok gatherer | Tweet generator | Per-slot (~10/day) |
| `live_content_queue.json` | Tweet generator | Poster, charts | Per-slot |
| `live_cost_log.json` | Cost tracker | Kill switch | Per-slot |
| `workflow_status.json` | All workflows | Debugging | Per-run |

---

## 10. Environment Variables Reference

### Always Required
```
ANTHROPIC_API_KEY
```

### Live Tweet System
```
XAI_API_KEY, CHARTIMG_API_KEY
X1_API_KEY, X1_API_SECRET, X1_ACCESS_TOKEN, X1_ACCESS_SECRET
X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET  (optional)
X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET  (optional)
```

### Email Notifications
```
SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS
NOTIFICATION_EMAIL  (alternative recipient var)
```

### WhatsApp (Optional)
```
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_TO
```

---

## 11. Known Issues & Improvement Areas

### Recently Fixed
1. Live tweets not posting — gitignore + no fallback context → Fixed
2. Email notifications not arriving — no env var support → Fixed
3. Friday notifications stale data — wrong signals file → Fixed
4. Stale content_schedule.json artifact → Removed

### Areas for Opus 4.6 Review
1. Automation gap: User manually copies prompts to Claude.ai daily
2. Friday→Saturday handoff: 8 manual prompts + 3 file saves
3. Signal quality: 16 signals often → 0 positions (funnel alignment?)
4. Fallback tweet quality when Grok unavailable
5. Position sizing optimality (T1=20%, T2=10%, T3=5%)
6. Tweet system cost (~$1.50-3.00/day)
7. Thursday flex logic complexity
8. Marketing vocabulary completeness
9. Dashboard/visual enhancements
10. Notification timing optimisation
