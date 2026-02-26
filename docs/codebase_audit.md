# BoS Momentum Scanner — Comprehensive Codebase Audit

**Date:** 2026-02-24
**Codebase Size:** 38,464 lines of Python across 59 files + 1,227 lines GitHub Actions + 378 lines shell
**Branch:** master
**Scanner Version:** Sterling Grid V6 (backtest-validated: +3294% return, -5.1% DD, 645x ret/DD)

---

## TABLE OF CONTENTS

| # | Section | Lines | Purpose |
|---|---------|-------|---------|
| 0 | [System Map](#0-system-map) | — | Top-level architecture atlas |
| 1 | [File Inventory](#1-file-inventory) | — | Every file with line counts and purpose |
| 2 | [Weekly Scanner Pipeline](#2-weekly-scanner-pipeline) | — | scanner.py function-by-function |
| 3 | [Sterling Grid V6 Indicators](#3-sterling-grid-v6-indicators) | — | Every indicator with exact formulas |
| 4 | [Claude.ai Interactive Workflow](#4-claudeai-interactive-workflow) | — | 7 prompts, decisions.json, human gates |
| 5 | [Merge Decisions — The Bridge](#5-merge-decisions--the-bridge) | — | merge_decisions.py field mapping |
| 6 | [Saturday Workflow Orchestrator](#6-saturday-workflow-orchestrator) | — | 7-step pipeline |
| 7 | [Portfolio Management](#7-portfolio-management) | — | Trade tracking, P&L, sizing |
| 8 | [Content Production System](#8-content-production-system) | — | Guide, generator, newsletter, notes, DD |
| 9 | [Tweet Generation System](#9-tweet-generation-system) | — | Batch + live tweet pipelines |
| 10 | [Posting Pipeline](#10-posting-pipeline) | — | 7-slot system, queue routing |
| 11 | [GitHub Actions Automation](#11-github-actions-automation) | — | 4 workflows step-by-step |
| 12 | [Daily Scanner](#12-daily-scanner) | — | Daily differences from weekly |
| 13 | [Dependency Graph](#13-dependency-graph) | — | Import matrices, hub ranking |
| 14 | [Data Flow Paths & Field Compatibility](#14-data-flow-paths--field-compatibility) | — | 6 data flow paths, field matrices |
| 15 | [Known Issues & Recommendations](#15-known-issues--recommendations) | — | Severity-ranked issues |

---

# 0. SYSTEM MAP

## 0.1 Architecture Atlas

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                     BoS MOMENTUM SCANNER — SYSTEM ATLAS                          ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║   ┌─────────────────────┐     ┌────────────────────────┐     ┌──────────────────┐║
║   │  SCANNER PIPELINE   │     │  CLAUDE.AI CHAT SESSION │     │  SATURDAY        ║
║   │  (Automated, $0)    │     │  (Interactive, Opus 4.6) │     │  WORKFLOW         ║
║   │                     │     │                          │     │  (Bridge)         ║
║   │  scanner.py         │────▶│  sterling_prompt_library │────▶│  saturday_       ║
║   │  sterling_indicators│     │  .md (7 prompts)         │     │  workflow.py      ║
║   │  daily_scanner.py   │     │                          │     │  merge_decisions  ║
║   │                     │     │  Human reviews each step │     │  .py              ║
║   │  OUTPUT:            │     │  OUTPUT:                 │     │                   ║
║   │  signals_technical  │     │  decisions.json          │     │  OUTPUT:          ║
║   │  .json              │     │  newsletter.html         │     │  signals.json     ║
║   └─────────────────────┘     └────────────────────────┘     └──────┬───────────┘║
║                                                                      │             ║
║                         ┌────────────────────────────────────────────┘             ║
║                         │                                                          ║
║                         ▼                                                          ║
║   ┌───────────────────────────────────────────────────────────────────────────────┐║
║   │                     DOWNSTREAM CONSUMERS (All Automated)                      │║
║   │                                                                               │║
║   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │║
║   │  │  PORTFOLIO    │  │  CONTENT     │  │  TWITTER     │  │  SUBSTACK        │ │║
║   │  │              │  │  PRODUCTION  │  │              │  │                  │ │║
║   │  │  manager.py  │  │  guide.py    │  │  tweet_gen   │  │  newsletter_     │ │║
║   │  │  portfolio   │  │  content_    │  │  .py         │  │  compiler.py     │ │║
║   │  │  .csv        │  │  generator   │  │  poster.py   │  │  content_gen.py  │ │║
║   │  │  equity_     │  │  .py         │  │  live_tweet  │  │  notes_batch_    │ │║
║   │  │  curve.csv   │  │              │  │  _gen.py     │  │  generator.py    │ │║
║   │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │║
║   └───────────────────────────────────────────────────────────────────────────────┘║
║                                                                                   ║
║   ┌───────────────────────────────────────────────────────────────────────────────┐║
║   │                         GITHUB ACTIONS (4 Workflows)                          │║
║   │                                                                               │║
║   │  friday_scan.yml    daily_scan.yml    daily_post.yml    live_tweet.yml        │║
║   │  (Fri 16:15 ET)     (M-F 16:35 ET)   (14 cron triggers) (Market hours)       │║
║   └───────────────────────────────────────────────────────────────────────────────┘║
║                                                                                   ║
║   ┌───────────────────────────────────────────────────────────────────────────────┐║
║   │                       CONFIG & UTILITIES                                      │║
║   │                                                                               │║
║   │  config/settings.py      config/output_paths.py    config/banned_terms.py    │║
║   │  utils/notifications.py  utils/email_notifier.py   utils/setup_scheduler.py  │║
║   └───────────────────────────────────────────────────────────────────────────────┘║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

## 0.2 Weekly Temporal Flow

```
FRIDAY 16:15 ET ─────────────────────────────────────────────────────────────────

  GitHub Actions: friday_scan.yml
  ├─ scanner.py --no-email --archive → signals_technical.json
  ├─ tweet_generator.py (weekly)     → content_queue.json (3 accounts)
  ├─ chart_capture.py                → twitter/output/charts/*.png
  ├─ dd_post_generator.py            → substack/output/current/substack_posts/
  ├─ notes_batch_generator.py --html → substack/output/current/substack_notes/
  ├─ content_production_guide.py     → substack/output/current/content_production_guide.md
  └─ newsletter_compiler.py          → substack/output/current/newsletter.html

SATURDAY MORNING (Human) ────────────────────────────────────────────────────────

  1. Open Claude.ai (Opus 4.6 + extended thinking)
  2. Attach signals_technical.json + portfolio.csv
  3. Run 7 prompts from sterling_prompt_library.md
     ├─ Prompt 1: Thematic Analysis → themes classified
     ├─ Prompt 2: Investment Gate   → per-stock verdicts
     ├─ Prompt 3: Deep DD          → detailed analysis (1-3 stocks)
     ├─ Prompt 4: Newsletter HTML   → newsletter.html
     ├─ Prompt 5: Sell Signal Review → exit decisions
     ├─ Prompt 6: Catalyst Check    → timing decisions
     └─ Prompt 7: Structured Export → decisions.json
  4. Save decisions.json to scanner/output/
  5. Save newsletter.html to substack/output/current/

SATURDAY AFTERNOON (Automated) ──────────────────────────────────────────────────

  python -m scanner.saturday_workflow
  ├─ Step 1: merge_decisions.py   → signals.json (merged)
  ├─ Step 2: Portfolio updates    → portfolio.csv updated
  ├─ Step 3: Market analysis      → market_analysis.md (if missing)
  ├─ Step 4: Content guide        → content_production_guide.md
  ├─ Step 5: Newsletter dist      → copy newsletter.html
  ├─ Step 6: Archive              → scanner/output/archive/YYYY-WXX/
  └─ Step 7: Summary              → next steps printed

MON-FRI 16:35 ET ────────────────────────────────────────────────────────────────

  GitHub Actions: daily_scan.yml
  ├─ daily_scanner.py             → daily_signals.json + daily_portfolio.csv
  ├─ tweet_generator.py (daily)   → daily_content_queue.json (3 accounts)
  └─ notifications.py             → email + WhatsApp for sell signals

DAILY (7 SLOTS) ─────────────────────────────────────────────────────────────────

  GitHub Actions: daily_post.yml (14 cron triggers)
  ├─ Slot 1 (07:30 ET): Daily queue → Pre-market recap
  ├─ Slot 2 (10:00 ET): Weekly queue → Theme analysis
  ├─ Slot 3 (12:30 ET): Weekly queue → Position update + chart
  ├─ Slot 4 (15:30 ET): Weekly queue → Power Hour (CRITICAL)
  ├─ Slot 5 (18:00 ET): Weekly queue → Engagement / Lessons
  ├─ Slot 6 (17:00 ET): Daily queue → Post-close recap
  └─ Slot 7 (18:30 ET): Daily queue → Daily overflow

DAILY CONTENT (Human) ──────────────────────────────────────────────────────────

  1. Open content_production_guide.md → today's category + topic
  2. Open content_prompt_handbook_v5.md → copy matching prompt
  3. Attach guide to Claude.ai (Opus 4.6)
  4. Paste prompt → get HTML post + 3 HTML notes
  5. Paste into Substack
```

## 0.3 Data Flow Summary

```
AUTOMATED INPUTS                    HUMAN DECISIONS                  MERGED OUTPUT
─────────────────                   ───────────────                  ─────────────
complete_tickers.txt ──┐
(~1,800 tickers)       │
                       ├──▶ scanner.py ──▶ signals_technical.json
SPY benchmark          │                          │
(yfinance)             │                          │
                       │                          ▼
portfolio.csv ─────────┘           decisions.json ─┐
                                   (from Claude.ai)│
                                                   ├──▶ merge_decisions.py ──▶ signals.json
                                                   │                              │
                                                   │                              ├──▶ tweet_generator.py
                                                   │                              ├──▶ content_generator.py
                                                   │                              ├──▶ content_production_guide.py
                                                   │                              ├──▶ newsletter_compiler.py
                                                   │                              ├──▶ notes_batch_generator.py
                                                   │                              └──▶ dashboard/data.ts
                                                   │
                                   newsletter.html ┘──▶ substack/output/current/
```

---

# 1. FILE INVENTORY

## 1.1 Summary Statistics

| Metric | Count |
|--------|-------|
| Python files | 59 |
| Python lines | 38,464 |
| GitHub Actions workflows | 4 |
| Workflow lines | 1,227 |
| Shell scripts | 1 |
| Shell lines | 378 |
| Test files | 10 |
| Test lines | 8,051 |
| **Grand Total LOC** | **~40,069** (excl. docs, data, dashboard TS) |

## 1.2 Files by Section

### `scanner/` — Scanner Pipeline (7 files, 6,055 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `scanner.py` | 2,518 | Sterling Grid V6 weekly pipeline orchestrator | Active — ~400 lines archived/dead code |
| `sterling_indicators.py` | 1,063 | V6 indicator functions (HMA, RSI, MACD, UC, ExD, profit lock, sizing) | Active — clean |
| `daily_scanner.py` | 791 | Daily timeframe scanner (Mon-Fri, legacy indicators) | Active |
| `merge_decisions.py` | 615 | Bridge: decisions.json + signals_technical.json → signals.json | Active — critical |
| `due_diligence.py` | 494 | DD prompt generation templates | Partially active |
| `saturday_workflow.py` | 397 | 7-step orchestrator: chat → automation bridge | Active |
| `legacy_indicators.py` | 177 | Old Banker/HMA/BoS indicators for daily scanner | Active (daily only) |

### `portfolio/` — Portfolio Management (3 files, 2,010 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `manager.py` | 1,713 | Trade tracking, P&L, profit lock, conviction sizing, equity curve | Active — core |
| `backup_cleanup.py` | 296 | Portfolio backup dedup (newest per calendar week) | Active |
| `__init__.py` | 1 | Package marker | — |

### `substack/` — Substack Content System (8 files, 8,068 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `content_generator.py` | 1,624 | Mon/Thu/Sat/Sun Substack posts (8 post types, HTML) | Active |
| `notes_batch_generator.py` | 1,347 | Batch note generation (21/week, 3/day, HTML support) | Active |
| `html_templates.py` | 1,182 | HTML template strings for all post/note types | Active |
| `newsletter_compiler.py` | 947 | Newsletter compilation with DD + themes + QQQ benchmark | Active |
| `content_production_guide.py` | 858 | Adaptive 4-category weekly schedule + context doc | Active — key |
| `portfolio_visual.py` | 819 | Portfolio dashboard HTML + equity curve SVG | Active |
| `dd_post_generator.py` | 545 | Standalone DD HTML posts per buy signal | Active |
| `note_utils.py` | 463 | Note formatting utilities | Active |
| `market_analyzer.py` | 282 | Market context analysis via LLM | Active |
| `__init__.py` | 1 | Package marker | — |

### `twitter/` — Twitter/X Content System (15 files, 12,370 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `tweet_generator.py` | 2,225 | Unified voice tweet gen (weekly+daily, 7-step validation) | Active — core |
| `live_tweet_generator.py` | 2,027 | Live tweet gen (market hours, 14-step validation) | Active |
| `signal_tracker.py` | 1,130 | Win tracking for celebrations and milestones | Active |
| `poster.py` | 1,100 | X/Twitter posting (7-slot system, dual queues, 3 accounts) | Active — core |
| `chart_capture.py` | 749 | TradingView chart screenshots (Playwright) | Active |
| `funnel_graphic.py` | 670 | Funnel visualization generation | Active |
| `live_context_gatherer.py` | 532 | Market context gathering for live tweets (xAI Grok) | Active |
| `chart_generator.py` | 359 | Chart generation via chart-img.com API | Active |
| `health_check.py` | 332 | Live tweet system health monitoring | Active |
| `self_quote_tracker.py` | 304 | Track tweets for milestone self-quoting | Active |
| `winner_showcase_generator.py` | 265 | Winner showcase with entry prices | Active |
| `models.py` | 218 | Shared dataclasses: Tweet, ContentData, SlotAssignment | Active — shared |
| `cost_tracker.py` | 195 | API cost tracking with daily kill switch | Active |
| `verify_tweets.py` | 177 | Tweet generator output verification | Active |
| `tradingview_login.py` | 90 | TradingView browser login helper | Active |
| `__init__.py` | 1 | Package marker | — |

### `config/` — Shared Configuration (4 files, 2,066 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `settings.py` | 1,324 | All constants, thresholds, API config, personas, schedules | Active — large |
| `banned_terms.py` | 377 | Banned terms, internal terminology map, regex patterns | Active |
| `output_paths.py` | 346 | Multi-section output path registry (21 path constants) | Active — clean |
| `__init__.py` | 19 | Re-exports from settings + banned_terms | Active |

### `utils/` — Shared Utilities (4 files, 1,576 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `notifications.py` | 869 | Sell signal notifications (email + WhatsApp via Twilio) | Active |
| `setup_scheduler.py` | 424 | macOS launchd scheduler setup | Active |
| `email_notifier.py` | 283 | SMTP email notifications (general purpose) | Active |
| `__init__.py` | 1 | Package marker | — |

### `dashboard/` — Next.js Dashboard (1 Python file, 321 lines)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| `scripts/backfill_equity_curve.py` | 321 | Backfill equity curve CSV from portfolio history | Active |

### `tests/` — Test Suite (10 files, 8,051 lines)

| File | Lines | Tests | Purpose |
|------|-------|-------|---------|
| `test_integration.py` | 1,348 | 34 | Cross-module integration tests (QQQ, DD, pipeline) |
| `test_substack_content_v2.py` | 1,017 | — | Substack content generator tests |
| `test_live_tweet_system.py` | 1,001 | — | Live tweet system tests |
| `test_tweet_gen_audit_fixes.py` | 900 | — | Tweet generator audit fix tests |
| `test_sterling_indicators.py` | 896 | 63 | Sterling Grid indicator unit tests |
| `test_tweet_generator_v2.py` | 748 | 24 | Tweet generator v2 unit tests |
| `test_tweet_gen_integration.py` | 475 | — | Tweet generator integration tests |
| `test_saturday_workflow.py` | 474 | — | Saturday workflow tests |
| `test_daily_scanner.py` | 459 | 11 | Daily scanner unit tests |
| `test_safeguards.py` | 277 | — | Safety guard tests |
| `test_edge_cases.py` | 276 | — | Edge case tests |
| `test_scheduling.py` | 108 | — | Scheduling tests |
| `__init__.py` | 13 | — | Package marker |

### Root & Workflow Files

| File | Lines | Purpose |
|------|-------|---------|
| `.github/workflows/friday_scan.yml` | 482 | Friday automated scan + tweets + content |
| `.github/workflows/daily_scan.yml` | 347 | Mon-Fri daily scanner + notifications |
| `.github/workflows/live_tweet.yml` | 352 | Live tweet system (market hours) |
| `.github/workflows/daily_post.yml` | 46 | 7-slot daily tweet posting (14 cron triggers) |
| `run_friday.sh` | 378 | Full Friday pipeline shell orchestrator |
| `sterling_prompt_library.md` | 971 | 7 interactive prompts for Claude.ai chat |
| `scanner/complete_tickers.txt` | 937 | Ticker universe (~1,800 US stocks) |

---

# 2. WEEKLY SCANNER PIPELINE

## 2.1 Overview

**File:** `scanner/scanner.py` (2,518 lines)
**Purpose:** Sterling Grid V6 momentum scanner — pure technical signal detector on weekly timeframe
**Cost:** $0 per run (no LLM API calls — all LLM analysis moved to Claude.ai chat)
**Output:** `signals_technical.json` (consumed by merge_decisions.py after human review)

## 2.2 Stock Dataclass (Lines 176-268)

The `Stock` dataclass is the central data structure flowing through the entire system. It has 60+ fields organized in 7 groups:

### Core Fields
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `symbol` | `str` | required | Ticker symbol |
| `price` | `float` | 0.0 | Latest closing price |
| `beta` | `float` | 0.0 | Beta vs SPY (informational, no longer an entry gate) |

### Sterling Grid V6 Indicator Fields
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `hma_value` | `float` | 0.0 | HMA(21) value on weekly HL2 |
| `hma_pivot_low` | `bool` | False | V-bottom: HMA[i-2] > HMA[i-1] < HMA[i] |
| `hma_pivot_high` | `bool` | False | V-top: HMA[i-2] < HMA[i-1] > HMA[i] |
| `hma_slope_rising` | `bool` | False | Informational (watchlist only) |
| `hma_slope_falling` | `bool` | False | Informational |
| `rsi14` | `float` | 0.0 | RSI(14) — display only, NOT a gate in V6 |
| `rsi_above_50` | `bool` | False | Informational only |
| `macd_cross_up` | `bool` | False | Single-bar MACD crossover event |
| `macd_line` | `float` | 0.0 | MACD line value |
| `macd_signal_line` | `float` | 0.0 | Signal line value |
| `macd_histogram` | `float` | 0.0 | Histogram value |
| `uc` | `float` | 0.0 | Undercurrent value (RSI-10 derivative, 0-20 range) |
| `uc_prev` | `float` | 0.0 | Previous bar UC value |
| `uc_rising` | `bool` | False | V6: UC > UC.shift(1) (no >0 requirement) |
| `uc_rising_above` | `bool` | False | V4 legacy: UC > prev AND UC > 0 |
| `uc_falling` | `bool` | False | UC < UC.shift(1) |
| `price_under_cap` | `bool` | False | Price < $25 |
| `buy_signal` | `bool` | False | V6 composite: HMA pivot + (UC OR MACD) + price |
| `exd_signal` | `bool` | False | V6 exit: HMA pivot high + UC falling |
| `quality_tier` | `int` | 0 | 0=none, 1=T1(both), 2=T2(MACD), 3=T3(UC) |
| `week_date` | `str` | "" | Week date for the signal bar |

### Legacy Backward-Compat Fields
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `banker` | `float` | 0.0 | Mapped from UC value for downstream compat |
| `banker_prev` | `float` | 0.0 | Previous bar banker |
| `banker_rising` | `bool` | False | Mapped from uc_rising |
| `bos_bullish` | `bool` | False | Mapped from buy_signal |
| `bos_bearish` | `bool` | False | Mapped from exd_signal |
| `bos_debug` | `dict` | {} | Debug info |
| `return_20d` | `float` | 0.0 | 20-day return |
| `momentum_4w` | `float` | 0.0 | 4-week momentum |
| `tier` | `str` | "" | Legacy tier string |

### Thematic Analyzer Fields (Populated by Claude.ai, then merge_decisions.py)
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `theme` | `str` | "" | Assigned theme name |
| `theme_score` | `float` | 0.0 | Theme composite score (0-10) |
| `pure_play_score` | `int` | 0 | Theme purity (0-100%) |
| `theme_verdict` | `str` | "" | STRONG/GOOD/MODERATE/POOR FIT |
| `theme_classification` | `str` | "" | PRIME/INVESTABLE/SELECTIVE/AVOID |
| `valuation_regime` | `str` | "" | OPTIONALITY/FUNDAMENTAL/TRANSITION |

### Investment Gate Fields (Populated by Claude.ai, then merge_decisions.py)
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `final_decision` | `str` | "" | PASS / CONSIDER / SKIP |
| `conviction` | `int` | 0 | 1-10 scale |
| `gate_verdict` | `str` | "" | STRONG_BUY / SPEC_BUY / NO_GO |
| `gate_conviction` | `int` | 0 | 1-10 from Investment Gate |
| `gate_catalyst` | `str` | "" | Key catalyst |
| `gate_bear_case` | `str` | "" | Bear case |
| `gate_math` | `str` | "" | Return math |
| `sector_status` | `str` | "" | Sector status |
| `upside_potential` | `str` | "" | Upside estimate |
| `bullish_factors` | `List[str]` | [] | Top bullish factors |
| `risk_factors` | `List[str]` | [] | Top risk factors |
| `reasoning` | `str` | "" | Analysis reasoning |
| `catalyst_summary` | `str` | "" | Catalyst summary |
| `red_flag_level` | `str` | "" | CLEAN / MINOR / SEVERE |
| `action` | `str` | "" | Recommended action |

### Position Sizing Fields
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `position_size_pct` | `float` | 0.0 | % of equity allocated |
| `position_dollars` | `float` | 0.0 | Dollar amount |
| `position_tier` | `str` | "" | T1/T2/T3 label |
| `sizing_gear` | `str` | "" | conservative/recommended/aggressive |

### Deep DD Fields (Populated by Claude.ai Opus)
| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `dd_verdict` | `str` | "" | STRONG BUY / SPEC BUY / NO GO |
| `dd_conviction` | `int` | 0 | 1-10 scale |
| `dd_position_size` | `str` | "" | FULL / REDUCED / PASS |
| `dd_analysis` | `str` | "" | Full analysis text |
| `dd_key_catalyst` | `str` | "" | Key catalyst |
| `dd_fatal_flaw` | `str` | "" | Fatal flaw if any |
| `dd_elevator_pitch` | `str` | "" | One-liner pitch |
| `dd_why_now` | `str` | "" | Why now thesis |
| `dd_the_math` | `str` | "" | Return math |
| `dd_bear_case` | `str` | "" | Bear case |
| `dd_risk_to_monitor` | `str` | "" | Key risk |
| `dd_action` | `str` | "" | Action recommendation |

### Methods on Stock
| Method | Line | Returns | Logic |
|--------|------|---------|-------|
| `meets_technical_criteria()` | 269 | `bool` | Returns `self.buy_signal` |
| `get_tier()` | 276 | `str` | Maps quality_tier int to T1/T2/T3 label |
| `passes_theme_gate()` | 303 | `bool` | True if theme_verdict not POOR/SKIP |
| `is_confirmed()` | 307 | `bool` | True if final_decision == "PASS" |

## 2.3 ScanStats Dataclass

| Field | Type | Purpose |
|-------|------|---------|
| `tickers_loaded` | `int` | Tickers read from complete_tickers.txt |
| `data_downloaded` | `int` | Successfully downloaded from yfinance |
| `hma_pivot_low` | `int` | Stocks with HMA V-bottom |
| `macd_cross_up` | `int` | Stocks with MACD crossover |
| `uc_rising` | `int` | Stocks with UC rising |
| `price_under_cap` | `int` | Stocks under $25 |
| `buy_signal` | `int` | Stocks with composite buy signal |
| `exd_exit` | `int` | Open positions with ExD exit signal |
| `technical_signals` | `int` | Final buy signal count |

## 2.4 SellSignal Dataclass

| Field | Type | Purpose |
|-------|------|---------|
| `symbol` | `str` | Ticker |
| `price` | `float` | Current price |
| `reason` | `str` | Exit reason(s) — may combine if both fire |
| `entry_price` | `float` | Original entry price |
| `highest_close` | `float` | Peak close since entry |
| `pnl_pct` | `float` | Return at exit |

## 2.5 Pipeline Functions (Execution Order)

### Function: `load_tickers()` (Line 389)
```
Input:  scanner/complete_tickers.txt
Output: List[str] — deduplicated, sorted ticker symbols
Logic:  Read file, split on whitespace, strip, dedup, sort
        Also loads open positions from portfolio.csv via PortfolioManager
```

### Function: `calculate_beta()` (Line 419)
```
Input:  stock_returns: pd.Series, benchmark_returns: pd.Series
Output: float — beta value
Formula: beta = cov(stock, SPY) / var(SPY)
         Minimum 60 data points required
         Returns 0.0 on error
```

### Function: `download_and_process()` (Line 445)
```
Input:  tickers: List[str], benchmark_returns: pd.Series
Output: Dict[str, Stock] — all stocks with indicators calculated

Processing (per ticker):
  1. Download 1 year daily data via yfinance (50-ticker chunks)
  2. Calculate beta vs SPY
  3. Resample daily → weekly (Friday close)
  4. Calculate all Sterling Grid V6 indicators:
     - HMA(21) pivots via calculate_hma_pivots()
     - Entry signal via generate_entry_signal()
     - Exit signal via generate_exit_signal()
  5. Populate Stock dataclass fields
  6. Map V6 fields to legacy fields for backward compat:
     banker = uc, banker_rising = uc_rising,
     bos_bullish = buy_signal, bos_bearish = exd_signal

Error handling: Catches per-ticker exceptions, continues processing
               Fails hard if < 30% of tickers download successfully
```

### Function: `check_sell_signals()` (Line 585)
```
Input:  stocks: Dict[str, Stock] — all downloaded stocks
Output: List[SellSignal]

Logic (per open position from portfolio.csv):
  1. Look up stock in downloaded data
  2. Check ExD exit: hma_pivot_high AND uc_falling
  3. Check tiered profit lock via check_profit_lock()
  4. First exit wins — if both fire, combine reasons
  5. Create SellSignal with entry_price, highest_close, pnl_pct
```

### Function: `run_scan()` (Line 685) — MAIN PIPELINE
```
Input:  top_n: int (optional limit), verbose: bool
Output: Tuple[confirmed, all_assessed, sell_signals, stats, [], []]

8 Steps:
  Step 1 (L699): Load tickers from complete_tickers.txt
  Step 2 (L721): Download SPY benchmark (1 year daily)
  Step 3 (L747): Download all stock data + calculate V6 indicators
  Step 4 (L769): Calculate statistics (count indicator hits)
  Step 5 (L903): Apply Sterling Grid technical gates
                 → Filter: buy_signal == True
                 → Assign quality tiers (T1/T2/T3)
  Step 6 (L945): Mark all as TECHNICAL_ONLY (no LLM in scanner)
  Step 7 (skipped): Placeholder for future gate
  Step 8 (L967): Check sell signals on open positions

Returns: confirmed (technical signals), [], sell_signals, stats, [], []
  Note: themes_data and momentum_rejected always empty in V6
```

### Function: `save_results()` (Line 1942)
```
Input:  confirmed, all_assessed, sell_signals, stats, momentum_rejected, themes_data
Output: Saves 3 files to disk

Files written:
  1. scanner/output/signals_technical.json (primary output)
     + scanner/output/current/signals_technical.json (copy)
     + scanner/output/archive/YYYY-WXX/signals_technical.json (if --archive)
  2. scanner/output/analysis_log.csv (append-only)
  3. scanner/output/current/report.txt
     + scanner/output/archive/YYYY-WXX/report.txt (if --archive)
```

### Function: `main()` (Line 2360) — ENTRY POINT
```
CLI Arguments:
  --top N        Only scan top N stocks by UC
  --verbose/-v   Show 10 items per diagnostic category (default: 3)
  --archive      Save dated archive copies
  --no-email     Skip email notification

Legacy (hidden/no-op):
  --no-llm, --no-momentum, --web-search, --no-dd, --save-dd,
  --no-prompts, --full-dd, --dd-top, --dd, --assess-top

Flow:
  1. Parse args
  2. Call run_scan()
  3. Call save_results()
  4. Update portfolio prices via PortfolioManager
  5. Export Google Sheets CSV
  6. Print summary report
  7. Send email notification (unless --no-email)
```

## 2.6 Files Read & Written

### Files Read
| File | Function | Purpose |
|------|----------|---------|
| `scanner/complete_tickers.txt` | `load_tickers()` | Ticker universe |
| `portfolio/output/portfolio.csv` | `load_open_positions()` | Open positions for stop checks |
| SPY data (yfinance API) | `run_scan()` Step 2 | Benchmark for beta calculation |
| Stock data (yfinance API) | `download_and_process()` | OHLCV for all tickers |

### Files Written
| File | Function | Format |
|------|----------|--------|
| `scanner/output/signals_technical.json` | `save_results()` | JSON |
| `scanner/output/current/signals_technical.json` | `save_results()` | JSON (copy) |
| `scanner/output/archive/YYYY-WXX/signals_technical.json` | `save_results()` | JSON (if --archive) |
| `scanner/output/analysis_log.csv` | `save_results()` | CSV (append) |
| `scanner/output/current/report.txt` | `save_results()` | Plain text |
| `scanner/output/archive/YYYY-WXX/report.txt` | `save_results()` | Plain text (if --archive) |

## 2.7 Archived/Dead Code

Lines ~1419-1916 contain archived functions that were part of the old automated LLM pipeline:
- `generate_newsletter_briefing()` — stub, replaced by Claude.ai chat
- `_generate_newsletter_briefing_ARCHIVED()` — V1 implementation
- `save_newsletter_briefing()` — stub
- `print_newsletter_prompts()` — stub

These ~500 lines could be removed in a future cleanup pass.

---

# 3. STERLING GRID V6 INDICATORS

## 3.1 Overview

**File:** `scanner/sterling_indicators.py` (1,063 lines)
**Purpose:** All Sterling Grid V6 technical indicator calculations
**Backtest Provenance:** V1-V4 → V6 evolution, validated on 11 stocks (2019-2026)
**Functions:** 16 total (7 indicator, 3 signal, 4 scanner, 2 sizing)

## 3.2 Configuration Constants (Lines 62-107)

### Indicator Parameters
| Constant | Value | Purpose |
|----------|-------|---------|
| `HMA_PERIOD` | 21 | Hull Moving Average period (weekly HL2) |
| `RSI_PERIOD` | 14 | RSI period (computed but NOT a V6 gate) |
| `MACD_FAST` | 12 | MACD fast EMA |
| `MACD_SLOW` | 26 | MACD slow EMA |
| `MACD_SIGNAL` | 9 | MACD signal EMA |
| `PRICE_CAP` | 25.0 | Maximum entry price |
| `UC_TARGET_DAYS` | 50 | Target days for internal RSI |
| `UC_SENSITIVITY` | 1.5 | Scaling factor for (RSI - 50) |
| `UC_TIMEFRAME` | "weekly" | Divisor = 5.0, RSI length = round(50/5) = 10 |

### Profit Lock Tiers
| Return Threshold | Trail % | Meaning |
|-----------------|---------|---------|
| >= +200% | 15% | Tight trail for big winners |
| >= +100% | 20% | Medium trail for strong positions |
| >= +50% | 25% | Loose trail for developing positions |
| < +50% | None | Only ExD can trigger exit |

### Position Sizing
| Tier | Conservative | Recommended | Aggressive |
|------|-------------|-------------|------------|
| T1 (both gates) | 12% | 20% | 25% |
| T2 (MACD only) | 8% | 10% | 15% |
| T3 (UC only) | 3% | 5% | 8% |

Max concurrent positions: 8. Minimum trade size: $500.

## 3.3 Indicator Functions — Exact Formulas

### `resample_to_weekly()` (Line 114)
```
Input:  Daily OHLCV DataFrame
Output: Weekly OHLCV DataFrame (Friday close)

Logic:
  Resample daily bars to 'W-FRI' frequency:
    Open  = first
    High  = max
    Low   = min
    Close = last
    Volume = sum
  Drop rows with NaN close
```

### `_wma()` (Line 131) — Internal Helper
```
Input:  series: pd.Series, length: int
Output: pd.Series

Formula: WMA(n) = Σ(weight_i × value_i) / Σ(weight_i)
         where weight_i = i + 1 (linear weights, newest has highest weight)
```

### `calculate_hma()` (Line 145)
```
Input:  series: pd.Series (typically HL2), length: int = 21
Output: pd.Series

Formula: HMA(n) = WMA(2 × WMA(n/2) − WMA(n), √n)

Steps:
  1. half = int(21/2) = 10
  2. sqrt_len = int(√21) = 4
  3. wma_half = WMA(series, 10)
  4. wma_full = WMA(series, 21)
  5. diff = 2 × wma_half − wma_full
  6. hma = WMA(diff, 4)

Applied to: HL2 = (High + Low) / 2 on weekly data
```

### `calculate_hma_pivots()` (Line 159)
```
Input:  weekly_df: pd.DataFrame, period: int = 21
Output: DataFrame with columns: hma, hma_pivot_low, hma_pivot_high,
        hma_slope_rising, hma_slope_falling

Pivot Detection (3-bar pattern):
  PIVOT LOW (buy trigger):
    hma_pivot_low[i] = (HMA[i-2] > HMA[i-1]) AND (HMA[i] > HMA[i-1])
    → V-bottom: HMA dipped then recovered

  PIVOT HIGH (exit trigger):
    hma_pivot_high[i] = (HMA[i-2] < HMA[i-1]) AND (HMA[i] < HMA[i-1])
    → V-top: HMA peaked then declined

Slope (informational):
  hma_slope_rising  = HMA > HMA.shift(1)
  hma_slope_falling = HMA < HMA.shift(1)

Edge cases: First 2 bars always False, NaN → False
```

### `calculate_rsi()` (Line 207)
```
Input:  series: pd.Series, period: int = 14
Output: pd.Series

Formula (Wilder's Smoothing):
  delta = series.diff()
  gain = max(delta, 0)
  loss = max(-delta, 0)
  avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
  avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
  rs = avg_gain / avg_loss
  rsi = 100 − 100/(1 + rs)

Note: RSI(14) is computed but NOT an entry gate in V6.
      Used for display/watchlist purposes only.
```

### `calculate_macd()` (Line 226)
```
Input:  series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
Output: DataFrame with: macd_line, signal_line, histogram, macd_cross_up

Formula:
  ema_fast = series.ewm(span=12, adjust=False).mean()
  ema_slow = series.ewm(span=26, adjust=False).mean()
  macd_line = ema_fast − ema_slow
  signal_line = macd_line.ewm(span=9, adjust=False).mean()
  histogram = macd_line − signal_line

Cross-Up Detection (V6 entry gate):
  macd_cross_up[i] = (macd_line[i] > signal_line[i])
                     AND (macd_line[i-1] <= signal_line[i-1])
  → SINGLE-BAR event only — no multi-bar lookback
```

### `calculate_undercurrent()` (Line 264)
```
Input:  weekly_df: pd.DataFrame, target_days: int = 50,
        sensitivity: float = 1.5, timeframe: str = "weekly"
Output: DataFrame with: uc, uc_prev, uc_rising, uc_rising_above, uc_falling

Internal RSI Calculation:
  tf_divisor = 5.0 (for weekly)
  length = round(target_days / tf_divisor) = round(50/5) = 10
  rsi_uc = RSI(close, 10) with Wilder's smoothing

Normalization Formula:
  UC = clip(sensitivity × (RSI(10) − 50), 0.0, 20.0)
     = clip(1.5 × (RSI(10) − 50), 0.0, 20.0)

UC Behavior:
  RSI(10) <= 50   → UC = 0.0  (bearish, clipped at floor)
  RSI(10) = 55    → UC = 7.5  (mild bullish)
  RSI(10) = 60    → UC = 15.0 (strong bullish)
  RSI(10) >= 63.3 → UC = 20.0 (capped at ceiling)

Direction Signals:
  uc_rising       = UC > UC.shift(1)       (V6: no >0 requirement)
  uc_rising_above = UC > UC.shift(1) AND UC > 0  (V4 legacy)
  uc_falling      = UC < UC.shift(1)
```

## 3.4 Signal Functions

### `generate_entry_signal()` (Line 335)
```
Input:  weekly_df: pd.DataFrame
Output: DataFrame with all indicator columns + buy_signal + quality_tier

V6 Entry Composite:
  buy_signal = hma_pivot_low
               AND (uc_rising OR macd_cross_up)
               AND (close < PRICE_CAP)

Quality Tier Classification:
  T1 = uc_rising AND macd_cross_up  (both gates)  → quality_tier = 1
  T2 = macd_cross_up only           (timing)       → quality_tier = 2
  T3 = uc_rising only               (regime)       → quality_tier = 3

Watchlist Signal (non-trade):
  watchlist = hma_slope_rising
              AND (uc_rising OR macd_histogram > 0)
              AND (close < PRICE_CAP)
              AND NOT buy_signal
```

### `generate_exit_signal()` (Line 437)
```
Input:  weekly_df: pd.DataFrame
Output: DataFrame with exd_signal column

V6 ExD Compound Exit:
  exd_signal = hma_pivot_high AND uc_falling

Both conditions must fire on the SAME weekly bar.
V4→V6 change: Replaced "HMA slope falling" with "HMA pivot high"
  (less sensitive — requires confirmed peak, not just downward tick)
```

### `check_profit_lock()` (Line 472)
```
Input:  entry_price: float, current_close: float, peak_close: float
Output: dict with: triggered, tier_name, trail_pct, lock_level,
        peak_close, gain_pct, peak_gain_pct, active_tier

CRITICAL: Tier determined by CURRENT return, NOT peak return.
          Tiers can DEGRADE as position retraces.

Algorithm:
  current_return = (current_close − entry_price) / entry_price

  if current_return >= 2.00:
    lock_level = peak_close × (1 − 0.15)   # 15% trail
    triggered  = current_close <= lock_level
  elif current_return >= 1.00:
    lock_level = peak_close × (1 − 0.20)   # 20% trail
    triggered  = current_close <= lock_level
  elif current_return >= 0.50:
    lock_level = peak_close × (1 − 0.25)   # 25% trail
    triggered  = current_close <= lock_level
  else:
    lock inactive (only ExD can trigger exit below +50%)
```

## 3.5 Scanner Utility Functions

### `scan_ticker()` (Line 542)
```
Input:  ticker: str, verbose: bool = True
Output: dict with all indicator values + buy/exit signals

Standalone function for scanning a single ticker.
Downloads data, calculates all V6 indicators, returns result dict.
Used by CLI and check_position().
```

### `check_position()` (Line 661)
```
Input:  ticker: str, entry_price: float, peak_price: float = None
Output: dict with: ticker, entry_price, current_close, peak_close,
        gain_pct, exd_exit, lock_triggered, lock_detail, action

Checks an open position for both exit types:
  1. ExD compound exit (HMA pivot high + UC falling)
  2. Tiered profit lock
Returns action string: "EXIT: ..." or "HOLD: ..."
```

### `dump_history()` (Line 713)
```
Input:  ticker: str
Output: CSV file with full weekly indicator history

Exports all weekly bars with all calculated indicators for debugging.
```

## 3.6 Position Sizing Functions

### `calculate_position_size()` (Line 762)
```
Input:  equity: float, quality_tier: int, gear: str = 'recommended'
Output: dict with: size_dollars, size_pct, tier_label, gear, shares_at_price

Looks up allocation % from SIZING_GEARS[gear][quality_tier].
Applies MAX_CONCURRENT_POSITIONS cap.
Enforces MIN_TRADE_SIZE ($500) floor.
```

### `show_portfolio_status()` (Line 818)
```
Input:  equity: float, positions: list, gear: str = 'recommended'
Output: Printed portfolio summary

Displays:
  - Current deployment by tier
  - Available capacity
  - Position sizes at current gear
```

## 3.7 V4 → V6 Evolution Summary

| Aspect | V4 | V6 |
|--------|----|----|
| **Entry trigger** | HMA slope rising | HMA PIVOT LOW (3-bar V-shape) |
| **RSI gate** | RSI(14) > 50 (required) | RSI(14) computed (NOT a gate) |
| **UC condition** | uc_rising_above (>prev AND >0) | uc_rising (>prev only) |
| **Gate logic** | All 5 conditions AND'd | pivot AND (UC OR MACD) AND price |
| **Exit trigger** | HMA slope falling | HMA PIVOT HIGH (3-bar V-top) |
| **Quality tiers** | Conviction 1-10 scalar | T1/T2/T3 discrete gates |
| **Tier sizing** | 8%, 15%, 20% dynamic | 5%, 10%, 20% fixed per tier |
| **Profit lock** | Same tiers | Same tiers (unchanged) |
| **Backtest result** | V4: +633% at 10x10, 79% WR | V6: +3294%, -5.1% DD, 645x |

---

<!-- Sections 0-3 above, Sections 4-6 below -->

# 4. CLAUDE.AI INTERACTIVE WORKFLOW

## 4.1 Overview

**File:** `sterling_prompt_library.md` (971 lines)
**Purpose:** 7-prompt sequential pipeline for human-in-the-loop stock analysis
**Model Required:** Claude Opus 4.6 with extended thinking + web search ON
**Session Duration:** 45-75 minutes (avg 11 messages)
**Output:** `decisions.json` + `newsletter.html`

This is the **most critical architectural insight** about the system: the scanner is NOT fully automated. It is a **human-in-the-loop hybrid** where:

1. **Automated** ($0): `scanner.py --no-llm` produces `signals_technical.json` (pure technical signals)
2. **Interactive** (Opus 4.6): Human runs 7 prompts in Claude.ai, reviewing/gating at each step
3. **Bridge** (automated): `saturday_workflow.py` merges human decisions into `signals.json`
4. **Downstream** (automated): All content/tweet/newsletter systems consume `signals.json`

## 4.2 The 7 Prompts

### Prompt 1: THEMATIC ANALYSIS

**Input:** Scanner output table (Ticker, Price, Tier, UC, RSI, MACD, 4W Momentum)
**Purpose:** Bottom-up micro-theme discovery for all technical signals

**Process:**
- Per ticker: 1-sentence company description + micro-theme name
- 5-factor scoring model:
  - Catalyst (30%): Upcoming catalysts and timing
  - Demand (20%): Supply/demand dynamics
  - Recognition (15%): Analyst coverage and institutional interest
  - Timing (10%): Entry timing quality
  - Capital Cycle (25%): With veto power if score <= 3
- Composite score (0-10) and classification:
  - PRIME (>= 7.5), INVESTABLE (6.0-7.4), SELECTIVE (4.5-5.9), AVOID (< 4.5)
- Gating recommendation: ADVANCE TO GATE / FILTERED OUT / BORDERLINE

**Human Gate:** User reviews theme calls, challenges classifications, decides which tickers advance.

### Prompt 2: INVESTMENT GATE

**Input:** Tickers advanced from Prompt 1 (context already in conversation)
**Purpose:** Red flag screening, return math validation, bear case steelman

**3-Phase Analysis:**
- **Phase A — Disqualifier Screen:**
  - IMMEDIATE DISQUALIFIERS (auto NO GO): Auditor resignation, CFO/CEO departure < 60 days, S-3 filed < 30 days, active SEC/DOJ investigation, earnings-timing conflicts
  - CAUTION FLAGS: Earnings 5-15 days, short interest > 25%, single analyst downgrade, low volume/float
- **Phase B — Return Math to 50%+:** Regime-adapted path (FUNDAMENTAL: earnings + multiple; OPTIONALITY: milestone → coverage; TRANSITION: revenue validates)
- **Phase C — Bear Case:** Steelmanned bear argument + data-backed rebuttal + downside floor

**Verdict Scale:**
| Verdict | Conviction | Action |
|---------|-----------|--------|
| STRONG BUY | 7-10 | Advance at FULL position size |
| SPEC BUY | 4-6 | Advance at REDUCED (50%) size |
| NO GO | 1-3 | Reject with specific reason + flip condition |

**Human Gate:** User challenges math, pushes back on bear case, decides which tickers advance to DD.

### Prompt 3: DEEP DUE DILIGENCE

**Input:** Single ticker (max 2), gate context in conversation
**Purpose:** Forensic 5-phase research

**5 Research Phases:**
1. **Growth Trajectory** — Revenue acceleration, operating leverage, customer retention
2. **Catalyst Deep Dive** — Specific dates, beat patterns, management equity grants
3. **Bear Case Investigation** — Deeper than gate; new risks, insider selling, lawsuits
4. **Smart Money Positioning** — 13F changes, hedge fund activity, activist interest
5. **Competitive Moat** — Switching costs, network effects, IP defensibility

**Deliverables:**
- ELEVATOR PITCH (2-3 sentences)
- WHY NOW (key catalyst with specific date)
- THE MATH (path to 50%+ with numbers)
- BEAR CASE (steelmanned + data-backed rebuttal)
- VARIANT PERCEPTION (what we see that consensus misses)
- KEY ASSUMPTION (one thing that must be true)
- KILL SWITCH (measurable trigger for early exit)
- ACTION (specific: "Buy Monday at ~$X, T1/T2 at allocation")
- FINAL VERDICT (STRONG BUY / SPEC BUY / NO GO, conviction 1-10)

**Human Gate:** User challenges bear case, stress-tests math, finalizes decisions.

### Prompt 4: NEWSLETTER (HTML)

**Input:** All decisions finalized from Prompts 1-3
**Purpose:** Self-contained subscriber-facing HTML newsletter

**Structure (1,200-1,500 words):**
1. Market Context — SPY/QQQ/IWM/VIX performance
2. What Our Scanner Found — Funnel stats, selectivity proof
3. Themes Driving Momentum — Top 2-3 themes
4. New GREEN Signals — Per-BUY pitch + `[CHART: TICKER]` placeholders
5. Portfolio Performance — Winners 15%+ threshold, SPY/QQQ alpha
6. Looking Ahead — 3-5 catalysts for next week
7. Footer — Subscribe link

**Dark dashboard theme:** bg #111827, cards #1F2937, accents teal #2DD4BF
**Marketing rules enforced:** GREEN signal (never TEAL/PASS), all banned terms filtered

### Prompt 5: SELL SIGNAL REVIEW

**Input:** Current holdings with entry prices, P&L, ExD signals
**Purpose:** Thesis validation and exit decisions

**Per Position:**
1. Thesis Check — Web search: Is original thesis intact?
2. Technical Signal — ExD, trailing stop, or none?
3. Regime Check — Valuation regime shifted?
4. Recommendation — HOLD / TRIM / EXIT with specific action

### Prompt 6: MID-WEEK CATALYST CHECK

**Input:** Holdings list with tickers
**Purpose:** Quick scan for material events in next 10 trading days

**Flags:** Earnings, FDA decisions, trial readouts, lock-up expirations, conference presentations, offering pricing windows

### Prompt 7: STRUCTURED EXPORT (decisions.json)

**Input:** All analysis from Prompts 1-6
**Purpose:** JSON export for repo integration

**Output Schema — Top-Level Fields:**
```
{
  "scan_date": "YYYY-MM-DD",
  "scan_week_ending": "YYYY-MM-DD",
  "market_regime": "risk_on|risk_off|selective",
  "market_context_summary": "string",
  "new_positions": [...],
  "no_go": [...],
  "exits": [...],
  "watchlist": [...],
  "themes_this_week": [...]
}
```

**new_positions[] fields (40+ per position):**
| Category | Key Fields |
|----------|-----------|
| Core | symbol, action, verdict, conviction (1-10), tier, price, stop_price |
| Sizing | position_size (FULL/REDUCED), position_size_pct (decimal) |
| Theme | theme, theme_score, theme_classification, theme_verdict, opportunity_type, valuation_regime |
| Gate | gate_verdict, gate_conviction, catalyst_summary, red_flag_level, gate_bear_case, gate_math |
| DD | dd_verdict, dd_conviction, dd_elevator_pitch, dd_why_now, dd_the_math, dd_bear_case, dd_risk_to_monitor, dd_action, dd_key_catalyst, dd_fatal_flaw |
| Extra | variant_perception, key_assumption, kill_switch, downside_floor |

**no_go[] fields:** symbol, verdict, stage_rejected, rejection_reason, reconsider_if
**exits[] fields:** symbol, action, reason, exit_price, entry_price, pnl_pct, lesson
**watchlist[] fields:** symbol, theme, status, trigger_to_buy, price_at_scan
**themes_this_week[] fields:** name, classification, lifecycle_stage, valuation_regime, composite_score, sub-scores, thesis_summary, key_catalysts, primary_risks, tickers

## 4.3 Challenge Prompts (6 Additional)

| Prompt | Purpose |
|--------|---------|
| Challenge the Bear Case | When bear case feels too easy to dismiss |
| Challenge the Math | When return assumptions feel optimistic |
| Head-to-Head Comparison | Choosing between multiple tickers |
| Validate Timing | Early/late entry risk assessment |
| Liquidity & Execution Check | Position sizing vs volume feasibility |
| Check for Fresh News | Latest developments verification |

## 4.4 Session Flow

```
FRIDAY EVENING (2-3 min automated):
  scanner.py --no-llm → signals_technical.json (table of ~10-40 technical signals)

FRIDAY/SATURDAY (45-75 min interactive in Claude.ai):

  Message 1: Paste Prompt 1 + scanner output table
  Message 2: Review themes, challenge classifications
  Message 3: Gate decision — advance 5-8 tickers to Investment Gate

  Message 4: Paste Prompt 2 for advanced tickers
  Message 5: Challenge math, push back on bear cases
  Message 6: Gate decision — advance 1-3 tickers to Deep DD

  Message 7: Paste Prompt 3 for first ticker
  Message 8: Challenge bear case, stress-test math
  Message 9: (Repeat for additional tickers if any)

  Message 10: Paste Prompt 4 (newsletter) + Prompt 7 (JSON export)
  Message 11: Save decisions.json + newsletter.html

SATURDAY (automated — saturday_workflow.py):
  merge_decisions.py → portfolio updates → content guide → archive
```

## 4.5 Critical Design Principle

Each stage **gates aggressively** (filters candidates), freeing later stages to use full thinking budget on higher-quality tickers:

```
~1,800 tickers → scanner.py → ~10-40 technical signals
   ~10-40 → Prompt 1 (Thematic) → ~5-8 advance
      ~5-8 → Prompt 2 (Gate) → ~1-3 advance
         ~1-3 → Prompt 3 (DD) → 0-3 final positions

Rejection rate: ~99.8% (1,800 → 0-3)
```

---

# 5. MERGE DECISIONS — THE BRIDGE

## 5.1 Overview

**File:** `scanner/merge_decisions.py` (615 lines)
**Purpose:** Bridge between Claude.ai chat analysis (`decisions.json`) and downstream automation (`signals.json`)
**Functions:** 8 total (3 helpers, 4 core, 1 CLI entry)
**Critical Role:** Without this module, human decisions would not flow to any automated content system

## 5.2 Architecture

```
signals_technical.json ─┐
(from scanner.py)        │
                         ├──▶ merge_signals() ──▶ signals.json (canonical)
decisions.json ──────────┘                            │
(from Claude.ai)              ┌───────────────────────┘
                              │
                              ├──▶ tweet_generator.py (reads buy_signals[])
                              ├──▶ content_generator.py (reads themes[], buy_signals[])
                              ├──▶ newsletter_compiler.py (reads pass_signals[], themes[])
                              ├──▶ live_tweet_generator.py (reads buy_signals[])
                              ├──▶ signal_tracker.py (reads buy_signals[])
                              ├──▶ content_production_guide.py (reads themes[], pass_signals[])
                              └──▶ dashboard/data.ts (reads everything)
```

## 5.3 Functions

### Helper Functions

| Function | Line | Purpose |
|----------|------|---------|
| `load_json(path, required)` | 64 | Load JSON with error handling; returns {} on failure |
| `save_json(data, path)` | 79 | Save JSON with parent dir creation; returns bool |
| `get_weekly_archive_dir()` | 91 | Get/create scanner/output/archive/YYYY-WNN/ |

### Core Functions

### `merge_signals(tech, decisions)` — Line 102 (219 lines)

The core function. Maps Claude.ai decisions + scanner technical data into unified `signals.json`.

**Processing Steps:**
1. **Build tech lookup** — Index technical signals by symbol for O(1) access
2. **Map themes** — `decisions.themes_this_week[]` → `merged.themes[]` (direct passthrough + compat fields)
3. **Map new positions** — `decisions.new_positions[]` → `merged.pass_signals[]` or `merged.consider_signals[]`
   - Verdict mapping: STRONG BUY → PASS, SPEC BUY → CONSIDER, all others → CONSIDER
   - Merge technical data from tech_lookup with decision fields
   - Build bullish_factors[] and risk_factors[] from DD fields
4. **Map exits** — `decisions.exits[]` + `tech.sell_signals[]` → `merged.sell_signals[]` (deduped)
5. **Map rejections** — `decisions.no_go[]` → `merged.assessed_signals[]` (REJECTED)
6. **Map watchlist** — `decisions.watchlist[]` → `merged.assessed_signals[]` (WATCHLIST)
7. **Create legacy aliases** — `buy_signals = union(pass + consider)`, `exit_signals = sell_signals`

**Verdict Mapping Table:**

| Input (decisions.json) | Output (signals.json) | Array |
|------------------------|----------------------|-------|
| `STRONG BUY` / `STRONG_BUY` | `final_decision: "PASS"` | pass_signals[] |
| `SPEC BUY` / `SPEC_BUY` / `SPECULATIVE BUY` | `final_decision: "CONSIDER"` | consider_signals[] |
| Any other value | `final_decision: "CONSIDER"` | consider_signals[] |
| (all of the above) | — | buy_signals[] (legacy union) |

**Field Mapping — Technical Data (from tech_lookup):**

| signals.json Field | Source | Note |
|--------------------|--------|------|
| `beta` | tech_data.beta | Informational |
| `uc` | tech_data.uc | UC indicator value |
| `uc_rising` | tech_data.uc_rising | Boolean |
| `rsi14` | tech_data.rsi14 | Display only |
| `macd_cross_up` | tech_data.macd_cross_up | Boolean |
| `hma_pivot_low` | tech_data.hma_pivot_low | Boolean |
| `hma_pivot_high` | tech_data.hma_pivot_high | Boolean |
| `buy_signal` | tech_data.buy_signal | Boolean |
| `exd_signal` | tech_data.exd_signal | Boolean |
| `banker` | tech_data.uc (fallback: banker) | **Legacy compat** |
| `uc_rising_above` | tech_data.uc_rising_above | **Legacy compat** |

**Field Mapping — Decision Data (from decisions.json position):**

| signals.json Field | Source | Default |
|--------------------|--------|---------|
| `theme` | pos.theme | "" |
| `theme_score` | pos.theme_score | 0 |
| `theme_verdict` | pos.theme_verdict | "STRONG FIT" |
| `conviction` | pos.dd_conviction → pos.conviction | 0 |
| `gate_verdict` | pos.gate_verdict → verdict (normalized) | "" |
| `reasoning` | pos.dd_elevator_pitch | "" |
| `upside_potential` | pos.dd_the_math | "" |
| `dd_verdict` | pos.dd_verdict → verdict | "" |
| `dd_conviction` | pos.dd_conviction → conviction | 0 |
| `dd_elevator_pitch` | pos.dd_elevator_pitch | "" |
| `dd_why_now` | pos.dd_why_now | "" |
| `dd_the_math` | pos.dd_the_math | "" |
| `dd_bear_case` | pos.dd_bear_case | "" |
| `dd_risk_to_monitor` | pos.dd_risk_to_monitor | "" |
| `dd_action` | pos.dd_action | "" |
| `action` | pos.dd_action | "Enter Monday at market open" |

### `build_content_schedule(decisions)` — Line 328

Builds minimal content metadata for downstream reference.

| Output Field | Source |
|-------------|--------|
| `generated` | datetime.now().isoformat() |
| `scan_date` | decisions.scan_date |
| `week_start` | scan_date + 1 day |
| `week_end` | scan_date + 7 days |
| `market_context` | decisions.market_context_summary |
| `new_positions` | [{symbol, theme}] |
| `has_newsletter` | newsletter.html exists check |

### `update_portfolio(decisions, dry_run)` — Line 362

Updates portfolio manager with new positions and exits.

**Add Logic:**
```
pm.add_trade(
    ticker=symbol, entry_price=price, theme=theme,
    tier=tier (default T2), signal_type="PASS",
    conviction=dd_conviction→conviction→0,
    notes=dd_elevator_pitch, position_size_pct=..., sizing_gear=...
)
```

**Exit Logic:**
```
pm.flag_exit(ticker=symbol, exit_price=price, reason=reason)
```

**Error Handling:** Gracefully degrades if portfolio manager not available.

### `validate_decisions(decisions)` — Line 444

Non-fatal structural validation. Returns list of warnings.

**Checks:**
| Check | Severity |
|-------|----------|
| decisions is not empty | Blocking |
| Required top-level fields present (scan_date, market_regime, new_positions, themes_this_week) | Warning |
| Each position has symbol | Warning |
| Each position has verdict | Warning |
| Each position has dd_elevator_pitch | Warning (newsletter needs it) |
| Each position has conviction > 0 | Warning |

## 5.4 Legacy Backward-Compatibility Layer

| Compat Feature | Purpose |
|----------------|---------|
| `banker` = UC value | Old consumers reading `banker` field |
| `uc_rising_above` preserved | V4 consumers |
| `pure_play_score` = theme_score | Old field name alias |
| `buy_signals[]` = union of pass + consider | Old consumers not aware of split |
| `exit_signals` = sell_signals | Old field name alias |
| Dual output paths (canonical + current/) | Old consumers reading from current/ |
| Conviction fallback chain (dd_conviction → conviction → 0) | Different field names across versions |
| Catalyst summary aliases (catalyst_summary ↔ dd_key_catalyst) | Different field names |

## 5.5 CLI Interface

```bash
python -m scanner.merge_decisions                    # Full production merge
python -m scanner.merge_decisions --dry-run          # Preview without saving
python -m scanner.merge_decisions --no-portfolio     # Skip portfolio updates
python -m scanner.merge_decisions --decisions FILE   # Custom decisions path
python -m scanner.merge_decisions --technical FILE   # Custom technical path
```

## 5.6 Output Files

| File | Location | Purpose |
|------|----------|---------|
| signals.json | scanner/output/signals.json | Canonical merged output |
| signals.json | scanner/output/current/signals.json | Backward compat copy |
| content_schedule.json | scanner/output/current/content_schedule.json | Content metadata |
| signals.json | scanner/output/archive/YYYY-WNN/ | Weekly archive |
| decisions.json | scanner/output/archive/YYYY-WNN/ | Weekly archive |
| content_schedule.json | scanner/output/archive/YYYY-WNN/ | Weekly archive |

---

# 6. SATURDAY WORKFLOW ORCHESTRATOR

## 6.1 Overview

**File:** `scanner/saturday_workflow.py` (397 lines)
**Purpose:** Single command to bridge Claude.ai chat session to downstream automation
**Input:** decisions.json (from Claude.ai) + signals_technical.json (from scanner)
**Output:** Updated signals.json, portfolio, content guide, newsletter, archives

## 6.2 7-Step Pipeline

```
╔══════════════════════════════════════════════════════════╗
║  SATURDAY WORKFLOW — 7 Steps                             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Step 1: merge_decisions.py                              ║
║          signals_technical.json + decisions.json          ║
║          → signals.json (canonical)                      ║
║          → content_schedule.json                         ║
║                                                          ║
║  Step 2: Portfolio Manager                               ║
║          → Add new positions (pm.add_trade)              ║
║          → Flag exits (pm.flag_exit)                     ║
║          → Update prices (pm.update_prices)              ║
║                                                          ║
║  Step 3: Market Analysis (optional, LLM call)            ║
║          → market_analysis.md (if missing)               ║
║          Skippable with --skip-market                    ║
║                                                          ║
║  Step 4: Content Production Guide                        ║
║          → content_production_guide.md                   ║
║          Skippable with --skip-guide                     ║
║                                                          ║
║  Step 5: Newsletter Distribution                         ║
║          → Copy newsletter.html to output dirs           ║
║          (Only if newsletter.html exists)                ║
║                                                          ║
║  Step 6: Archive                                         ║
║          → Copy to scanner/output/archive/YYYY-WNN/     ║
║          → Copy to substack/output/archive/YYYY-WNN/    ║
║                                                          ║
║  Step 7: Summary                                         ║
║          → Print market regime, positions, exits, themes ║
║          → Print NEXT STEPS checklist                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

## 6.3 Step Functions

### `step_merge(decisions_path, dry_run)` — Line 95

**Purpose:** Merge decisions with technical data → signals.json

**Logic:**
1. Load existing signals.json (or signals_technical.json) as base
2. Load decisions.json (required — fails if missing)
3. Call `merge_signals(tech, decisions)` from merge_decisions.py
4. Call `build_content_schedule(decisions)`
5. Save merged signals to SIGNALS_FILE and CURRENT_DIR/signals.json
6. Save content schedule to CURRENT_DIR/content_schedule.json

**Returns:** decisions dict (or None on failure)

### `step_portfolio(decisions, dry_run)` — Line 149

**Purpose:** Update portfolio with new positions and exits

**Logic:** Delegates to `merge_decisions.update_portfolio(decisions, dry_run)`

### `step_market_analysis(dry_run, skip)` — Line 160

**Purpose:** Generate market analysis if not already present

**Logic:**
1. Check if CURRENT_DIR/market_analysis.md exists
2. If exists: skip (already generated)
3. If missing: import `substack.market_analyzer.run_market_analysis()` and generate
4. Catches ImportError (market_analyzer not available) and general exceptions

### `step_content_guide(dry_run, skip)` — Line 196

**Purpose:** Generate content production guide

**Logic:** Imports `substack.content_production_guide.main()` and runs it

### `step_newsletter(decisions_path, dry_run)` — Line 223

**Purpose:** Copy newsletter.html to output directories

**Logic:**
1. Check if `substack/output/current/newsletter.html` exists
2. If exists: copy to target locations
3. If missing: skip (newsletter compiled separately)

### `step_archive(decisions_path, dry_run)` — Line 253

**Purpose:** Archive all outputs to weekly folder

**Files Archived:**
| File | Destination Name |
|------|-----------------|
| decisions.json | decisions.json |
| signals.json (merged) | signals.json |
| content_schedule.json | content_schedule.json |
| newsletter.html (if exists) | newsletter.html |

**Archive Locations:**
- `scanner/output/archive/YYYY-WNN/`
- `substack/output/archive/YYYY-WNN/` (newsletter only)

### `step_summary(decisions, dry_run)` — Line 301

**Purpose:** Print completion summary with next steps

**Output:**
```
  Market regime: [regime]
  New positions: [count]
  Exits:         [count]
  Themes:        [count]

  New buys:
    [emoji] TICKER — theme (price, verdict)

  NEXT STEPS:
  1. Open substack/output/current/content_production_guide.md
  2. Publish newsletter to Substack (copy HTML)
  3. Add TradingView charts at [CHART: TICKER] placeholders
  4. Post Saturday tweets (slots 2-5 from content_queue)
  5. Post 3 Substack notes for today
```

## 6.4 CLI Interface

```bash
python -m scanner.saturday_workflow                   # Full workflow
python -m scanner.saturday_workflow --dry-run         # Preview without writing
python -m scanner.saturday_workflow --skip-market     # Skip market analyzer LLM call
python -m scanner.saturday_workflow --skip-guide      # Skip content production guide
python -m scanner.saturday_workflow --decisions FILE  # Custom decisions path
```

## 6.5 Error Handling

Each step is independently error-handled:
- Step 1 (merge): Returns None on failure, halts workflow
- Steps 2-6: Catch exceptions, print warnings, continue to next step
- Step 3 (market): Catches ImportError for missing market_analyzer
- Step 4 (guide): Catches ImportError for missing content_production_guide

## 6.6 Temporal Context

The Saturday workflow is designed to run **after** the Claude.ai chat session:

```
TIMELINE:
  Friday PM: scanner.py runs (automated) → signals_technical.json
  Saturday AM: Human runs Claude.ai chat → decisions.json + newsletter.html
  Saturday PM: python -m scanner.saturday_workflow → everything merged + archived

The workflow expects:
  - decisions.json to already exist at scanner/output/decisions.json
  - Optionally: newsletter.html at substack/output/current/newsletter.html
  - Optionally: signals_technical.json at scanner/output/signals_technical.json
```

---

<!-- Sections 4-6 above, Sections 7-8 below -->

## 7. Portfolio Management (`portfolio/manager.py` — 1,714 lines)

The portfolio module is the financial source of truth for the entire system. Every
downstream module — tweets, newsletter, dashboard, content guide — reads either
`portfolio.csv` directly or calls `PortfolioManager` methods.

### 7.1 Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │     portfolio/manager.py     │
                    │         1,714 lines          │
                    ├─────────────────────────────┤
                    │                             │
                    │  TradeStatus (Enum)         │
                    │  Trade (dataclass)          │
                    │  EquitySnapshot (dataclass) │
                    │  EquityTracker (class)      │
                    │  PortfolioManager (class)   │
                    │  + 7 standalone functions   │
                    │                             │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     portfolio.csv    equity_curve.csv   portfolio_google_sheets.csv
     (source of        (NAV history,     (calculated fields,
      truth, 16        13 columns,       GOOGLEFINANCE formulas)
      columns)         deduped by date)
              │
              ▼
     portfolio_backups/
     (timestamped, max 30, atomic writes)
```

### 7.2 Data Structures

#### TradeStatus Enum (line 151)

```
OPEN     — Active position being tracked
CLOSED   — Manual exit (profit taking, strategic)
STOPPED  — Hit tiered profit lock or ExD exit
```

#### Trade Dataclass (lines 183–339)

16 CSV-persisted fields + 7 calculated in-memory fields:

| # | Field | Type | Stored | Purpose |
|---|-------|------|--------|---------|
| 1 | `ticker` | str | CSV | Stock symbol (uppercased) |
| 2 | `status` | str | CSV | OPEN / CLOSED / STOPPED |
| 3 | `entry_date` | str | CSV | YYYY-MM-DD (auto-set if empty) |
| 4 | `entry_price` | float | CSV | Price at entry |
| 5 | `exit_date` | str | CSV | YYYY-MM-DD (set on exit) |
| 6 | `exit_price` | float | CSV | Price at exit |
| 7 | `highest_close` | float | CSV | Tracks peak for profit lock (init to entry_price) |
| 8 | `theme` | str | CSV | Investment theme |
| 9 | `tier` | str | CSV | T1/T2/T3 from Sterling Grid |
| 10 | `signal_type` | str | CSV | PASS or CONSIDER |
| 11 | `conviction` | int | CSV | 1-10 scale |
| 12 | `notes` | str | CSV | Free text (appended on exit) |
| 13 | `stop_pct` | float | CSV | Per-trade stop override (0 = use global) |
| 14 | `position_size_pct` | float | CSV | % of equity allocated |
| 15 | `position_dollars` | float | CSV | Dollar amount allocated |
| 16 | `sizing_gear` | str | CSV | conservative / recommended / aggressive |
| — | `current_price` | float | Mem | Live price from yfinance |
| — | `pnl_pct` | float | Mem | Unrealized/realized P&L % |
| — | `pnl_usd` | float | Mem | P&L in dollars (× DEFAULT_POSITION_SHARES) |
| — | `stop_level` | float | Mem | Current profit lock level (0 if inactive) |
| — | `days_held` | int | Mem | Calendar days entry→now or entry→exit |
| — | `distance_to_stop_pct` | float | Mem | % distance to stop (0 if no lock) |
| — | `stop_alert` | bool | Mem | True if within STOP_WARNING_PCT of stop |

**Key methods on Trade:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `__post_init__()` | 213–218 | Sets entry_date to today, highest_close to entry_price |
| `calculate_metrics(current_price)` | 220–263 | Computes all 7 in-memory fields; calls `check_profit_lock()` for stop_level |
| `validate()` | 265–296 | Business rule validation (negative prices, date ordering, stopped-without-exit) |
| `to_csv_row()` | 298–317 | Serializes 16 fields to dict for CSV writer |
| `from_csv_row(row)` | 319–339 | Class method: deserializes from CSV dict with type coercion |

**Profit lock integration in `calculate_metrics()`:**
- Below +50% return from entry: `stop_level = 0` (only ExD can exit)
- At/above +50%: calls `check_profit_lock()` from `sterling_indicators.py`
- Returns tiered trailing stop: +200% gain → 15% trail, +100% → 20%, +50% → 25%

#### EquitySnapshot Dataclass (lines 346–403)

13-field point-in-time NAV snapshot for equity curve tracking:

| Field | Purpose |
|-------|---------|
| `date` | YYYY-MM-DD |
| `nav` | Net Asset Value (cash + open positions) |
| `cash` | Uninvested cash from closed profits |
| `invested` | Current value of open positions |
| `total_deployed` | Total capital ever allocated (£5k × N allocations) |
| `open_count` | Number of open positions |
| `total_return_pct` | NAV / total_deployed - 1 |
| `spy_value` | What total_deployed in SPY would be worth |
| `spy_return_pct` | SPY return since inception |
| `alpha_pct` | total_return_pct - spy_return_pct |
| `qqq_value` | What total_deployed in QQQ would be worth |
| `qqq_return_pct` | QQQ return since inception |
| `alpha_vs_qqq_pct` | total_return_pct - qqq_return_pct |

### 7.3 EquityTracker Class (lines 406–622)

Tracks compounding portfolio equity over time using a replay model.

**Model:** £5,000 per position. Closed trade profits flow into a cash pool.
New trades draw from the pool when sufficient, otherwise new capital is deployed.
NAV = cash_pool + Σ(open position current values).

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__(starting_per_position, equity_file)` | 415–419 | Loads equity_curve.csv on init |
| `_load_curve()` | 421–431 | Deserializes CSV → List[EquitySnapshot] |
| `_save_curve()` | 433–442 | Serializes snapshots → CSV |
| `_get_inception_date(trades)` | 444–453 | Finds earliest entry_date across all trades |
| `calculate_nav(trades, spy_data, qqq_data)` | 455–586 | **Core method:** Chronological replay of all trades |
| `record_snapshot(snapshot)` | 588–595 | Appends snapshot (deduplicates by date, sorts) |
| `get_latest()` | 597–599 | Returns most recent snapshot |
| `get_max_drawdown()` | 601–622 | Peak-to-trough drawdown from equity history |

**`calculate_nav()` replay algorithm (lines 455–586):**

```
1. Sort all trades by entry_date
2. For each trade:
   a. If cash_pool >= £5,000 → draw from pool
   b. Else → deploy new capital (pool partially covers if any)
   c. If CLOSED/STOPPED → return allocation × (1 + trade_return) to cash
   d. If OPEN → track allocation for current value calculation
3. invested_value = Σ(allocation × current_price / entry_price) for open trades
4. NAV = cash_pool + invested_value
5. Compare against SPY and QQQ over same inception→today window
```

### 7.4 PortfolioManager Class (lines 629–1714)

Central class with 16 CSV fields and 26+ methods organized into 6 groups:

**CSV Schema (`CSV_FIELDNAMES`, line 632):**
```
ticker, status, entry_date, entry_price, exit_date, exit_price,
highest_close, theme, tier, signal_type, conviction, notes, stop_pct,
position_size_pct, position_dollars, sizing_gear
```

#### Group 1: I/O (lines 638–699)

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__(portfolio_file)` | 638–644 | Loads CSV, inits EquityTracker |
| `_load()` | 646–662 | CSV → List[Trade] with validation warnings |
| `_save()` | 664–699 | Atomic write: backup → temp file → os.replace(); max 30 backups |

**Atomic write pattern:**
```
1. Copy current file → portfolio_backups/portfolio_YYYYMMDD_HHMMSS.csv
2. Prune backups to MAX_PORTFOLIO_BACKUPS (30)
3. Write to NamedTemporaryFile in same directory
4. os.replace(temp, target) — atomic on same filesystem
5. On failure: clean up temp file
```

#### Group 2: Trade Management (lines 701–792)

| Method | Lines | Purpose |
|--------|-------|---------|
| `add_trade(ticker, entry_price, ...)` | 705–736 | Add new trade; skips if already open |
| `add_trade_from_stock(stock)` | 738–751 | Scanner integration: Stock → Trade via getattr |
| `flag_exit(ticker, exit_price, reason)` | 753–772 | Exit trade; sets STOPPED or CLOSED based on reason |
| `get_open_position(ticker)` | 774–780 | Lookup single open position |
| `get_open_positions()` | 782–784 | List all OPEN trades |
| `get_closed_trades()` | 786–788 | List all non-OPEN trades |
| `get_open_symbols()` | 790–792 | Set of open ticker symbols |

#### Group 3: Price Updates (lines 794–910)

| Method | Lines | Purpose |
|--------|-------|---------|
| `update_prices(stocks_dict, check_delisted)` | 798–866 | Update all open positions; from scanner dict or yfinance |
| `check_stop_signals(stocks_dict)` | 868–910 | Check tiered profit lock via `check_profit_lock()` |

**`update_prices()` flow:**
1. Optionally check for delisted tickers via yfinance `.info`
2. If `stocks_dict` provided → use prices from scanner
3. Else → `yf.download(symbols, period="5d")` for latest close
4. Call `calculate_metrics(price)` on each trade
5. Collect `stop_alert` trades (within STOP_WARNING_PCT of stop)
6. Save to CSV

**`check_stop_signals()` flow:**
1. For each open position in `stocks_dict`
2. Update highest_close if current > highest
3. Call `check_profit_lock(entry, current, highest)` from sterling_indicators
4. If `triggered` → set STOPPED, record exit_price, add notes
5. Save if any triggered

#### Group 4: Performance Metrics (lines 912–1057)

| Method | Lines | Purpose |
|--------|-------|---------|
| `_load_spy_data()` | 916–925 | Lazy-load 2y SPY data via yfinance |
| `_load_qqq_data()` | 927–936 | Lazy-load 2y QQQ data via yfinance |
| `get_spy_return(days)` | 938–950 | Calendar-window SPY return |
| `get_spy_return_for_period(start, end)` | 952–985 | Date-range SPY return (for matched alpha) |
| `get_spy_ytd_return()` | 987–1000 | SPY year-to-date return |
| `calculate_portfolio_return(days, ytd)` | 1002–1037 | Average P&L of closed trades in window |
| `_matched_spy_alpha(trades)` | 1039–1057 | Per-trade alpha: each trade vs SPY over same holding period |
| `get_performance_summary()` | 1059–1124 | Comprehensive dict: win rate, avg winner/loser, period returns, matched alpha |

#### Group 5: Compounding Equity (lines 1126–1172)

| Method | Lines | Purpose |
|--------|-------|---------|
| `update_equity_curve()` | 1130–1142 | Calculate NAV → record snapshot to equity_curve.csv |
| `get_compounding_summary()` | 1144–1172 | Full summary dict for newsletter/dashboard |

#### Group 6: Export & Reporting (lines 1174–1450)

| Method | Lines | Purpose |
|--------|-------|---------|
| `export_for_google_sheets(output_file)` | 1178–1226 | CSV with calculated fields (19 columns) |
| `generate_google_sheets_template()` | 1228–1320 | Markdown with GOOGLEFINANCE formulas |
| `migrate_from_old_format()` | 1326–1379 | Legacy open_positions.csv → unified portfolio.csv |
| `print_summary()` | 1385–1450 | Terminal report: positions, SPY comparison, compounding equity |

### 7.5 Standalone Functions (lines 1453–1618)

These provide a simplified API for scanner and downstream modules:

| Function | Lines | Purpose |
|----------|-------|---------|
| `load_portfolio(status_filter, compute_pnl)` | 1457–1493 | Canonical CSV reader → List[Dict] |
| `get_portfolio_manager()` | 1496–1498 | Singleton factory |
| `add_trade_to_portfolio(stock)` | 1501–1504 | Scanner → portfolio bridge |
| `check_portfolio_stops(stocks_dict)` | 1507–1510 | Scanner → stop check bridge |
| `get_open_position_symbols()` | 1513–1516 | Scanner dedup check |
| `update_portfolio_prices(stocks_dict)` | 1519–1523 | Update + auto-export sheets |
| `fetch_current_prices(tickers, warn_threshold)` | 1530–1591 | **Canonical** yfinance price fetcher |
| `get_spy_ytd_return()` | 1594–1618 | **Canonical** SPY YTD benchmark |

### 7.6 Utility Functions (lines 107–177)

| Function | Lines | Purpose |
|----------|-------|---------|
| `is_ticker_valid(ticker)` | 107–130 | Check if ticker is still trading via yfinance .info |
| `check_portfolio_for_invalid_tickers(tickers)` | 133–148 | Batch delisting check |
| `_normalize_date(date_str)` | 157–176 | YYYY-MM-DD or DD/MM/YYYY → YYYY-MM-DD |

### 7.7 Backup System

```
portfolio/output/portfolio_backups/
    portfolio_20260224_143000.csv    ← timestamped on every _save()
    portfolio_20260223_160000.csv
    ...
    (max 30 files, oldest pruned)
```

**Behavior:**
- Every `_save()` call creates a backup before writing
- Backups named `portfolio_YYYYMMDD_HHMMSS.csv`
- Pruned to `MAX_PORTFOLIO_BACKUPS` (30) keeping newest
- Atomic write via temp file + `os.replace()` prevents corruption
- Separate `DAILY_PORTFOLIO_BACKUP_DIR` for daily scanner trades

### 7.8 CLI Interface (lines 1625–1714)

```bash
python -m portfolio.manager --report        # Full terminal summary
python -m portfolio.manager --update        # Refresh prices via yfinance
python -m portfolio.manager --export        # Google Sheets CSV
python -m portfolio.manager --equity        # Compounding equity summary
python -m portfolio.manager --add TICKER --price 10.50 --theme "AI"
python -m portfolio.manager --exit TICKER --exit-price 15.00
python -m portfolio.manager --migrate       # Legacy format migration
python -m portfolio.manager --setup         # Google Sheets formula guide
```

### 7.9 `portfolio/backup_cleanup.py` (296 lines)

Deduplicates portfolio backups — keeps only the newest backup per calendar week.

| Function | Purpose |
|----------|---------|
| `group_backups_by_week()` | Groups portfolio_*.csv files by ISO week |
| `find_duplicates()` | Identifies all but newest in each week |
| `execute_cleanup()` | Deletes duplicates (with `--execute` flag) |
| `list_backups()` | Pretty-print backups grouped by week |
| `show_stats()` | Backup count, disk usage, oldest/newest |

---

## 8. Content Production System (7 modules, 8,068 lines)

The content production system generates all Substack content: newsletter, posts,
notes, DD pages, and the production guide that bridges the scanner to Claude.ai
for on-demand content generation.

### 8.1 Architecture Diagram

```
signals.json ──┐
               ▼
┌──────────────────────────────────┐    ┌────────────────────────────────┐
│ content_production_guide.py      │    │ content_prompt_handbook_v5.md  │
│ (858 lines, $0)                  │    │ (prompts live here)           │
│                                  │    └────────────────────────────────┘
│ Generates:                       │            │
│ • content_production_guide.md    │◄───────────┘ (references)
│ • content_schedule.json          │
│                                  │
│ Contains:                        │
│ • System context + marketing     │
│ • This week's data (scanner,     │
│   themes, portfolio, equity)     │
│ • 7-day schedule (4 categories)  │
│ • Note types per day             │
└──────────┬───────────────────────┘
           │ User attaches to Claude.ai
           ▼
    ┌─────────────────┐
    │  Claude.ai       │    Opus 4.6 + extended thinking
    │  (interactive)   │    User pastes prompt from handbook
    │                  │───► HTML post + 3 HTML notes
    └─────────────────┘

signals.json ──┐
               ▼
┌──────────────────────────────────┐     ┌────────────────────────────┐
│ newsletter_compiler.py (947 ln)  │◄────│ dd_post_generator.py       │
│ Compiles: newsletter.html        │     │ (545 lines)                │
│ • DD results integration         │     │ Generates: dd_TICKER.html  │
│ • Theme sub-scores               │     │ per buy signal             │
│ • QQQ benchmark                  │     └────────────────────────────┘
└──────────────────────────────────┘

signals.json ──┐
               ▼
┌──────────────────────────────────┐     ┌────────────────────────────┐
│ content_generator.py (1,624 ln)  │     │ notes_batch_generator.py   │
│ 8 post types (LLM, ~$0.50/post) │     │ (1,347 lines)              │
│ Mon/Thu/Sat/Sun Substack posts   │     │ 21 notes/week (3/day)      │
│                                  │     │ 7 note types               │
└──────────────────────────────────┘     │ --html flag support        │
                                         └────────────────────────────┘
┌──────────────────────────────────┐     ┌────────────────────────────┐
│ market_analyzer.py (282 lines)   │     │ portfolio_visual.py        │
│ Claude + web search → analysis   │     │ (819 lines)                │
│ market_analysis.md               │     │ SVG equity curve + HTML    │
└──────────────────────────────────┘     │ dashboard                  │
                                         └────────────────────────────┘
```

### 8.2 `content_production_guide.py` (858 lines)

The production guide is the **bridge between scanner outputs and human-driven
content creation**. It generates a single markdown document designed to be
attached to a Claude.ai chat session for on-demand content generation.

**Cost: $0** (no LLM calls — pure data assembly)

#### The 4 Adaptive Categories

| Category | Constant | Theme | When Scheduled |
|----------|----------|-------|----------------|
| Ticker Deep Dive | `CATEGORY_TICKER_DIVE` | Editorial (light) | When new GREEN signals or portfolio winners exist |
| Educational | `CATEGORY_EDUCATIONAL` | Editorial (light) | Fills remaining days; at least 1/week guaranteed |
| Theme Rotation | `CATEGORY_THEME_ROTATION` | Dashboard (dark) | When PRIME/INVESTABLE themes available |
| Performance Review | `CATEGORY_PERFORMANCE_REVIEW` | Dashboard (dark) | Always Sunday (newsletter companion) |

#### NOTE_TYPE_MATRIX (lines 108–116)

Each day has 3 note types for variety:

| Day | Note 1 | Note 2 | Note 3 |
|-----|--------|--------|--------|
| Sunday | Community & Connection | Journey & Milestones | Week Preview |
| Monday | Market Macro | Winner Highlight | Ticker News |
| Tuesday | Geopolitics/Macro | Theme Spotlight | Community |
| Wednesday | Teaching & Wisdom | Portfolio Insight | Community |
| Thursday | Market Midweek | System Insight | Ticker News |
| Friday | Week Reflection | Winner Recap | Engagement |
| Saturday | Journey | Teaching | Community |

#### Key Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `load_full_portfolio()` | 131–165 | Load all open positions with live metrics via PortfolioManager |
| `build_weekly_schedule(ctx, portfolio)` | 172–318 | **Core:** Builds 7-day schedule from scanner data |
| `generate_system_context()` | 325–434 | Static context: who we are, marketing rules, HTML specs |
| `generate_weekly_data(ctx, portfolio)` | 441–end | Dynamic data: scanner results, themes, portfolio, equity |
| `generate_schedule_section(schedule)` | (in file) | Formats schedule as markdown table |
| `main()` | (end) | CLI entry point with --dry-run |

**`build_weekly_schedule()` algorithm:**
```
1. Sunday → always PERFORMANCE_REVIEW
2. Build topic pools:
   - GREEN signals → ticker dive candidates
   - Top performers (≥15% P&L) → ticker dive candidates
   - PRIME/INVESTABLE themes → rotation candidates
3. For Mon-Fri:
   a. Prioritize: ticker dive > theme rotation > educational
   b. No consecutive same-category days
4. If no educational assigned all week → swap Wednesday
5. Saturday → NOTES_ONLY
6. Annotate each day with note_types and handbook_prompt reference
```

**Outputs:**
- `substack/output/current/content_production_guide.md` — attach to Claude.ai
- `substack/output/current/content_schedule.json` — dashboard sidecar
- Archived copies in `substack/output/archive/YYYY-WXX/`

### 8.3 `content_generator.py` (1,624 lines)

Generates Substack posts using Claude API calls. This is the **automated** path
(as opposed to the Claude.ai interactive path via the production guide).

#### 8 Post Types

| Type | Day | Template | Description |
|------|-----|----------|-------------|
| `monday_theme_analysis` | Monday | Editorial | Theme deep dive with catalyst timeline |
| `tuesday_portfolio_pulse` | Tuesday | Dashboard | Portfolio update with equity stats |
| `wednesday_theme_deep_dive` | Wednesday | Editorial | Detailed theme rotation analysis |
| `thursday_stock_deep_dive` | Thursday | Editorial | Individual stock deep dive |
| `friday_portfolio_showcase` | Friday | Dashboard | Weekly portfolio showcase |
| `saturday_weekend_watchlist` | Saturday | Dashboard | Weekend watchlist and prep |
| `sunday_week_ahead` | Sunday | Dashboard | Week ahead preview |
| `performance_review` | Sunday | Dashboard | Full performance review (newsletter companion) |

#### Key Components

| Component | Purpose |
|-----------|---------|
| `ContentContext` | Dataclass holding all scanner/portfolio/theme data |
| `PostSpec` | Dataclass: type, title, prompt, template, output_path |
| `TEMPLATE_MAP` | Maps post types → HTML template strings |
| `build_content_context()` | Loads signals.json + portfolio → ContentContext |
| `load_portfolio_winners()` | Filters portfolio for display-worthy positions |
| `load_historical_themes()` | Loads past themes for rotation tracking |
| `generate_post(spec, ctx)` | Claude API call → HTML post |
| `_format_*()` helper functions | 8 formatting functions for prompt data injection |

### 8.4 `newsletter_compiler.py` (947 lines)

Compiles the complete Saturday newsletter from multiple data sources.

#### Key Functions

| Function | Lines (approx) | Purpose |
|----------|----------------|---------|
| `load_dd_results()` | ~80 | Extracts Deep DD fields: elevator_pitch, why_now, the_math, bear_case, risk_to_monitor, action |
| `load_theme_details()` | ~60 | Theme sub-score table: catalyst, momentum, crowding, runway scores |
| `generate_benchmark_comparison()` | ~50 | QQQ + SPY benchmark with max drawdown |
| `compile_newsletter(signals, portfolio)` | ~200 | Main compilation: assembles all sections into prompt |
| `COMPILATION_PROMPT` | ~100 | System prompt with `{theme_details}`, `{dd_results}`, `{benchmark}` sections |

**Data sources consumed:**
- `signals.json` — buy signals, themes, exit signals
- `portfolio.csv` — open positions, closed trades
- `equity_curve.csv` — NAV history for benchmark comparison
- Deep DD results embedded in signals.json buy_signals
- Market analysis from `market_analysis.md` (if available)

**Output:** `substack/output/current/newsletter.html`

### 8.5 `notes_batch_generator.py` (1,347 lines)

Generates 21 Substack notes per week (3 per day) using Claude API.

#### 7 Note Types

| Type | Description | Rotation |
|------|-------------|----------|
| `Market Macro` | Macro trends, sector flows | Mon, Thu |
| `Winner Highlight` | Top performer spotlight | Mon, Fri |
| `Theme Spotlight` | Deep dive into active theme | Tue |
| `Teaching & Wisdom` | Strategy education | Wed, Sat |
| `Community & Connection` | Engagement, questions | Sun, Tue, Wed |
| `Portfolio Insight` | System mechanics, process | Wed, Thu |
| `Journey & Milestones` | Personal narrative | Sun, Sat |

#### Key Components

| Component | Purpose |
|-----------|---------|
| `NoteSpec` | Dataclass: day, slot, type, topic, output filename |
| `generate_notes_for_day(day)` | Generates 3 notes for a specific day |
| `generate_all_notes()` | Full batch: 7 days × 3 notes = 21 |
| `wrap_note_html(markdown_content)` | Markdown → HTML converter (for `--html` flag) |
| `HTML_NOTE_TEMPLATE` | HTML template for note output |

**CLI:**
```bash
python -m substack.notes_batch_generator              # All 21 notes (markdown)
python -m substack.notes_batch_generator --html        # All 21 notes (HTML)
python -m substack.notes_batch_generator --day monday  # Single day (3 notes)
```

**Outputs:**
```
substack/output/current/substack_notes/
    monday_1_market_macro.md          (or .html with --html)
    monday_2_winner_highlight.md
    monday_3_ticker_news.md
    tuesday_1_geopolitics_macro.md
    ...
    notes_manifest.json               (batch tracking metadata)
```

### 8.6 `dd_post_generator.py` (545 lines)

Generates standalone dark-theme HTML pages per buy signal for Substack publication.

#### 10-Section HTML Layout

1. Hero header with ticker, theme, price
2. The Pitch (elevator pitch)
3. Why Now (catalyst timeline)
4. The Math (valuation case)
5. Bear Case (counter-argument)
6. Risk to Monitor (key risk)
7. Theme Context (progress bars for sub-scores: catalyst, momentum, crowding, runway)
8. Investment Gate Summary (conviction, signal type)
9. Action card (entry guidance)
10. Footer with disclaimer

**Marketing safety:** Sanitizes internal terminology via `INTERNAL_TERMINOLOGY_MAP`
from `config/banned_terms.py` before rendering.

**CLI:**
```bash
python -m substack.dd_post_generator                 # All buy signals
python -m substack.dd_post_generator --ticker NVDA   # Specific ticker
python -m substack.dd_post_generator --dry-run       # Preview without saving
```

**Output:** `substack/output/current/substack_posts/dd_TICKER.html`

### 8.7 `market_analyzer.py` (282 lines)

Generates market context analysis using Claude + web search.

| Function | Purpose |
|----------|---------|
| `run_market_analysis()` | Claude API call with web search for current market conditions |
| `save_analysis(content)` | Saves to `scanner/output/current/market_analysis.md` |

**Used by:** `saturday_workflow.py` Step 3 (optional, costs ~$0.50)

### 8.8 `portfolio_visual.py` (819 lines)

Generates a portfolio dashboard HTML page with SVG equity curve chart.

#### Components

| Component | Purpose |
|-----------|---------|
| SVG equity curve | Polyline chart: Portfolio NAV vs SPY vs QQQ since inception |
| 6-stat grid | NAV, Total Return, Win Rate, Alpha vs SPY, Alpha vs NASDAQ, Max Drawdown |
| Positions table | All open positions with Current Price, P&L, Stop Distance columns |
| Theme breakdown | Positions grouped by investment theme |

**Output:**
- `substack/output/current/portfolio_visual.html` — full HTML dashboard
- Optional: PNG screenshot via Playwright (for embedding in newsletter)

**CLI:**
```bash
python -m substack.portfolio_visual                  # HTML + PNG
python -m substack.portfolio_visual --dry-run        # HTML only (no Playwright)
```

### 8.9 Content Flow Summary

The daily workflow for content creation:

```
Step 1: Open substack/output/current/content_production_guide.md
        → Check today's category and topic

Step 2: Open substack/docs/content_prompt_handbook_v5.md
        → Copy the matching category prompt

Step 3: Attach the content_production_guide.md to Claude.ai
        (Opus 4.6 + extended thinking)

Step 4: Paste prompt → get 1 HTML post + 3 HTML notes

Step 5: Paste into Substack editor
```

This replaces the older fully-automated approach (content_generator.py) with a
human-in-the-loop workflow that produces significantly higher quality output
using Opus 4.6 with extended thinking.

---

<!-- Sections 7-8 above, Sections 9-12 below -->

---

## 9. Tweet Generation System

Two independent tweet generators produce content for the 7-slot posting pipeline:
**batch** (weekly + daily) and **live** (market hours). Both share the same 7-step
validation pipeline and data model layer.

### 9.1 Data Models — `twitter/models.py` (218 lines)

Shared dataclasses consumed by both generators and the poster.

#### Tweet Categories (16 total)

```
11 WEEKLY/DAILY CATEGORIES          5 LIVE-ONLY CATEGORIES
───────────────────────────────     ──────────────────────────
SCANNER_RESULT   chart: ✓          MARKET_REACTION  chart: ✗
DAILY_SIGNAL     chart: ✓          RECEIPT          chart: ✓
THEME_ANALYSIS   chart: ✗          SIGNAL_ALERT     chart: ✓
PERFORMANCE      chart: ✓          DIP_OPPORTUNITY  chart: ✗
WATCHLIST        chart: ✗          THEME_MOMENTUM   chart: ✗
TECHNICAL_ANALYSIS chart: ✗
EDUCATIONAL      chart: ✗
MARKET_COMMENTARY chart: ✗
SELL_SIGNAL      chart: ✓
ENGAGEMENT       chart: ✗
NEWSLETTER_CTA   chart: ✗
```

Chart-required set: `{SCANNER_RESULT, DAILY_SIGNAL, PERFORMANCE, SELL_SIGNAL, RECEIPT, SIGNAL_ALERT}`

#### Dataclasses

| Class | Fields | Purpose |
|-------|--------|---------|
| `Tweet` | `text, category, chart_required, tickers_mentioned, chart_path, chart_paths, metadata` | Single generated tweet; `char_count` property; `get_all_chart_paths()` for multi-image |
| `ValidationResult` | `passed, failures, details` | Output of 7-step validation pipeline |
| `SlotAssignment` | `day, slot, category, data_key` | Planned slot in weekly/daily schedule |
| `ContentData` | 15 fields across 4 groups | Aggregated source data for generation |

**ContentData field groups:**

```
Weekly:    pass_signals, consider_signals, themes, scan_stats
Portfolio: winners (≥25%), notable_holdings (≥10%), holdings (≥0%), sell_signals
Daily:     daily_signals, daily_sells, daily_winners
Context:   market_data, scan_date, newsletter_url
```

Eight `@property` booleans: `has_winners`, `has_notable_holdings`, `has_holdings`,
`has_consider_signals`, `has_pass_signals`, `has_themes`, `has_daily_signals`.

### 9.2 Batch Tweet Generator — `twitter/tweet_generator.py` (2,267 lines)

Generates weekly tweets (28 slots × 7 days × 4 slots/day) and daily tweets
(slots 1/6/7 per day). Uses Claude Sonnet 4 for generation with a 7-step
validation pipeline and LLM repair loop.

#### Architecture Overview

```
signals.json ─────┐
portfolio.csv ────┤    ┌──────────────┐    ┌──────────┐    ┌──────────┐
market_data ──────┼───►│ ContentData  │───►│ Schedule │───►│ Generate │
daily_signals ────┤    │ (15 fields)  │    │ (28 slots)│   │ (LLM)    │
style_guide ──────┘    └──────────────┘    └──────────┘    └────┬─────┘
                                                                │
                    ┌──────────┐    ┌──────────┐    ┌──────────┐│
                    │ Write    │◄───│ Attach   │◄───│ Validate ││
                    │ Queues   │    │ Charts   │    │ (7-step) │◄┘
                    └──────────┘    └──────────┘    └──────────┘
                         │                               │ fail
                    ┌────┴────┐                    ┌─────┴──────┐
                    │ 3 accts │                    │ Repair     │
                    │ × queues│                    │ (max 2)    │
                    └─────────┘                    └────────────┘
```

#### Internal CostTracker (lines 147–172)

Lightweight per-run cost tracking (separate from `twitter/cost_tracker.py`):

| Method | Purpose |
|--------|---------|
| `__init__()` | Initialize with model pricing dict |
| `record(input_tokens, output_tokens)` | Accumulate token counts |
| `total_cost` | Property: USD cost from token counts |
| `summary()` | Human-readable string: "$0.25 (in: 3,200, out: 800)" |

#### Data Loading (lines 351–467)

| Function | Lines | Returns |
|----------|-------|---------|
| `_load_style_guide()` | 351–357 | Embedded FinTwit style guide string (40+ KB) |
| `_load_signals(path)` | 364–371 | Dict from signals.json |
| `_load_portfolio(path)` | 374–395 | List of position dicts with P&L calculated |
| `_build_content_data(signals, portfolio, market_data, daily_signals)` | 398–467 | `ContentData` with winner/notable/holding classification |

Winner classification thresholds:
- `winners`: P&L ≥ 25%
- `notable_holdings`: 10% ≤ P&L < 25%
- `holdings`: 0% ≤ P&L < 10%

#### Schedule Planning (lines 474–825)

**`_plan_weekly_schedule(data, seed)`** — 28-slot deterministic scheduler.

Schedule shape: 7 days × 4 slots (slots 2-5 only; slots 1/6/7 are daily).

```
           Slot 2     Slot 3     Slot 4     Slot 5
Saturday   SCANNER    THEME      PERF       ENGAGE
Sunday     NEWSLETTER WATCH      SCANNER    ENGAGE
Monday     THEME      PERF       SCANNER    ENGAGE
Tuesday    SCANNER    WATCH      THEME      ENGAGE
Wednesday  PERF       SCANNER    MARKET     ENGAGE
Thursday   THEME      SCANNER    PERF       ENGAGE
Friday     SCANNER    THEME      WATCH      NEWSLETTER
```

Helper functions:

| Function | Lines | Purpose |
|----------|-------|---------|
| `_data_available(category, data)` | 576–598 | Check if ContentData has data for category |
| `_within_limits(category, schedule, day)` | 601–612 | Check daily/weekly repetition limits |
| `_try_assign(category, schedule, data, day, slot)` | 615–628 | Attempt assignment with availability + limit checks |
| `_pick_category(day, slot, data, ...)` | 631–806 | Deterministic selection with fallback chains |
| `_inject_category(schedule, category, data_key, count)` | 809–825 | Replace low-priority slots to meet category minimums |

Category constraints:

| Constraint | Value |
|------------|-------|
| MAX_SAME_CATEGORY_PER_DAY | 2 |
| MAX_PORTFOLIO_POOL_PER_DAY | 2 |
| Min SCANNER_RESULT per week | 2 (injected if schedule falls short) |
| Min PERFORMANCE per week | 2 (injected if portfolio has winners) |
| NEWSLETTER_CTA per week | 2 (Saturday + Friday) |

#### LLM Prompt Building (lines 831–1220)

**`_build_system_prompt(style_guide)`** (lines 831–863):
- Sterling Signals identity paragraph
- Embedded style guide (40+ KB of rules)
- First 60 terms from `CRITICAL_BANNED` list
- 7 core generation rules (use exact data, ticker mandatory, no loss amounts, etc.)

**`_build_user_prompt(category, slot_data, slot, recent_openings, recent_closings)`** (lines 866–1220):

Category-specific prompt injection:

| Category | Prompt Content |
|----------|---------------|
| `SCANNER_RESULT` | List signals with theme + thesis + entry price |
| `PERFORMANCE` | Multi-ticker receipt: $X from $entry to $current, +Z% |
| `THEME_ANALYSIS` | Theme observation + portfolio holdings + scanner tickers |
| `SELL_SIGNAL` | Setup invalidated framing (no loss amounts) |
| `WATCHLIST` | Tickers being watched for trigger |
| `NEWSLETTER_CTA` | Newsletter URL + recent wins |
| `DAILY_SIGNAL` | Daily BoS signals with price + beta |
| `TECHNICAL_ANALYSIS` | Key levels + invalidation points |
| `ENGAGEMENT` | Portfolio stats context |
| `MARKET_COMMENTARY` | Market data context |

**`_prepare_slot_data(category, data, used_indices)`** (lines 1077–1220):
Extract slot-specific data from ContentData, tracking which indices have been
used to prevent repetition across slots.

#### Tweet Generation (lines 1223–1278)

**`_generate_tweet(category, slot_data, slot, style_guide, client, cost_tracker, ...)`**

Single LLM call per tweet:
1. Build system + user prompts
2. Call Claude Sonnet 4 (max_tokens=300)
3. Record cost via CostTracker
4. Strip quotes + extract `$TICKER` mentions via regex
5. Return `Tweet` object

#### 7-Step Validation Pipeline (lines 1285–1460)

**`_validate_tweet(tweet, source_data, allowed_tickers)`** → `ValidationResult`

| Step | Name | Checks |
|------|------|--------|
| 1 | Category Check | Valid category? Required elements present? SELL_SIGNAL has "invalidated" framing? NEWSLETTER_CTA has reference? |
| 2a | Meta-language Detection | No LLM artifacts ("cannot generate", "please provide", "$TICKER" placeholder) |
| 2b | Ticker + Price Accuracy | All `$TICKER`s from source data? Strict for DATA_DEPENDENT_CATEGORIES: SCANNER_RESULT, SELL_SIGNAL, DAILY_SIGNAL, PERFORMANCE, TECHNICAL_ANALYSIS, WATCHLIST |
| 3 | Banned Phrase Check | All terms in `ALL_BANNED` absent? Word-boundary matching for short terms (HMA, RSI, etc.) |
| 4 | Winners-Only Check | No negative P&L percentages (-X%)? No portfolio fabrication? |
| 5 | Internal Terminology | `INTERNAL_TERM_PATTERNS` regex matching |
| 6 | Character Count + Temporal | ≤280 chars? No "year-end" in Q1? No future quarter references? |
| 7 | Chart Flag Check | `chart_required` matches expected per category? |

#### LLM Repair Loop (lines 1467–1519)

**`_repair_tweet(tweet, failures, slot_data, style_guide, client, cost_tracker)`**

Second LLM call with:
- Failed tweet text
- Specific validation failures as bullet points
- Original category + source data
- Instruction to fix ALL errors

Max 2 repair attempts. If still failing after 2 repairs → drop tweet + log to
`failed_tweets.json`.

#### Chart Path Attachment (lines 1527–1629)

**`_attach_chart_paths(tweets, charts_dir)`**

Reads `chart_manifest.json` and matches paths to tweets:
- PERFORMANCE: multi-chart (up to 4 winner charts)
- SCANNER_RESULT / THEME_ANALYSIS: single chart + funnel graphic fallback
- TECHNICAL_ANALYSIS / SELL_SIGNAL: single chart (no fallback)

#### Queue Writing (lines 1636–1713)

**`_write_queues(tweets, queue_map, output_dir, scan_date)`**

Each queue entry:
```json
{
  "id": "saturday_2_0",
  "day": "Saturday",
  "slot": 2,
  "time": "10:00",
  "text": "...",
  "category": "SCANNER_RESULT",
  "scheduled_date": "2026-02-22",
  "status": "pending",
  "posted": false,
  "char_count": 247,
  "mentioned_tickers": ["$RCAT"],
  "chart_required": true,
  "chart_path": "charts/RCAT_weekly_20260221.png",
  "chart_paths": [],
  "timestamp": "2026-02-21T22:30:00"
}
```

**`_log_failed_tweet(tweet, failures, output_dir)`** (lines 1720–1742):
Append to `failed_tweets.json` for manual review.

#### Main Entry Points

**`generate_weekly_content(signals_path, portfolio_path, market_data, output_dir, account_id)`** (lines 1749–1937):

Full workflow:
1. Load style guide
2. Load + build ContentData
3. Plan 28-slot schedule (seeded by `account_id` for cross-account variation)
4. For each slot: generate → validate → repair (if needed) → queue or drop
5. Attach chart paths
6. Write queues (3 accounts)
7. Return summary dict: `{total_tweets, by_category, failed_count, chart_required_count, cost, duration_secs}`

**`generate_daily_content(daily_signals_path, daily_portfolio_path, output_dir, account_id)`** (lines 1937–2068):

Similar workflow for daily signals (slots 1, 6, 7 only). Generates up to 5
`DAILY_SIGNAL` tweets + `SELL_SIGNAL` tweets for daily exits.

### 9.3 Live Tweet Generator — `twitter/live_tweet_generator.py` (2,027 lines)

Real-time tweet generation during market hours based on portfolio performance,
market conditions, and Grok context. Runs via GitHub Actions at 5 weekday slots
+ 2 weekend slots.

#### 14-Step Pipeline

```
 1. Load Configuration        signals, portfolio, style guide, recent tweets
 2. Build Allowed Tickers     Union of portfolio + signal tickers
 3. Check Market Hours        Only generate during open (skip otherwise)
 4. Get Recent Tweets         Prevent recency duplicates
 5. Decide Tweet Type         Market condition → category
 6. Gather Live Context       Call Grok for market intelligence
 7. Prepare Slot Data         Extract category-relevant data
 8. Build LLM Prompts         System + user with live context
 9. Call Sonnet               Generate tweet (max_tokens=300)
10. Validate Output           7-step pipeline (same as weekly)
11. Repair if Failed          Retry with feedback (max 2)
12. Attach Charts             Match to chart_manifest.json
13. Check Cost Limits         Kill switch enforcement ($1/day)
14. Write to Queue            Append to live_content_queue.json
```

#### RecentTweetTracker Class (lines 211–340)

Prevents duplicate/repetitive posting:

| Method | Purpose |
|--------|---------|
| `add_tweet(tweet_dict)` | Track posted tweet by ticker/category |
| `recently_tweeted_ticker(ticker, hours)` | Was ticker posted about within N hours? |
| `recently_tweeted_type(tweet_type, hours)` | Was category posted within N hours? |
| `count_per_category(category)` | Count this week's posts for category |
| `get_recent_openings()` | Last 10 tweet opening lines |
| `get_recent_closings()` | Last 5 tweet closing lines |
| `reset_weekly()` | Reset counts on Monday |

#### Category Decision Tree (lines 762–1061)

**`decide_tweet_type(market_condition, portfolio, signals, recent_tweets, time_context, tracker)`**

Maps market condition to tweet category with recency + budget constraints:

| Market Condition | Default Category | Recency Limit |
|-----------------|-----------------|---------------|
| `market_open` | MARKET_REACTION | — |
| `power_hour` + winning position | RECEIPT | Max 1/day |
| `dip_opportunity` (market -1%+) | DIP_OPPORTUNITY | — |
| `theme_breakout` (leader +2%+) | THEME_MOMENTUM | Max 2/day |
| `winner_milestone` (position +50%+) | RECEIPT | Max 1/day |
| `signal_trigger` (new 2hr signal) | SIGNAL_ALERT | — |
| `cold_market` | ENGAGEMENT | — |
| `default` | MARKET_REACTION | — |

#### Ticker Selection Functions (lines 550–629)

| Function | Purpose |
|----------|---------|
| `get_best_performing_tickers(portfolio, n)` | Top N by P&L % |
| `get_diverse_tickers(portfolio, signals, count, diversity_rule)` | Select by rule: "balanced", "winners_only", "growth", "deep_value" |
| `find_tickers_for_theme(theme, portfolio, signals)` | Tickers matching theme name |

#### LLM Integration

**`call_sonnet(system, user_prompt, cost_tracker)`** (lines 1336–1380):
- Claude Sonnet 4, max_tokens=300
- 2-second retry on rate limits
- Cost tracking via CostTracker

**`validate_tweet()`** (lines 1447–1679): Identical 7-step pipeline as weekly.

#### Queue Management

**`write_to_live_queue(tweet_dict, queue_file, account_key)`** (lines 1717–1765):

```json
{
  "id": "live_1708534200",
  "text": "...",
  "category": "MARKET_REACTION",
  "account": "variant_1",
  "status": "pending",
  "generated_at": "2026-02-21T14:30:00",
  "chart_path": null,
  "timestamp": "2026-02-21T14:30:00.123456"
}
```

**`_prune_queue(queue, max_age_days)`** (lines 1681–1715): Remove tweets older
than N days from queue.

### 9.4 Supporting Modules

#### Chart Capture — `twitter/chart_capture.py` (749 lines)

TradingView chart screenshots via Playwright browser automation.

| Function | Lines | Purpose |
|----------|-------|---------|
| `capture_chart(page, ticker, output_dir, date_str, timeframe, sizes)` | 143–239 | Single ticker: build TV URL with layout ID + interval → navigate → hide UI → screenshot at two sizes (X-card + Substack) |
| `capture_charts(tickers, headless, ...)` | 242–402 | Bulk capture with session management |
| `capture_charts_batch(tickers, headless, dry_run, output_dir)` | 407–605 | Wrapper with error handling + manifest |
| `extract_chrome_cookies(domain)` | 407–478 | Extract cookies from local Chrome profile |
| `save_cookies(context, filepath)` | 481–487 | Persist cookies to JSON |
| `load_cookies(context, filepath)` | 489–501 | Load saved cookies into Playwright |
| `check_indicators_loaded(page)` | 504–564 | Verify custom indicators rendering |
| `save_chart_manifest(results, output_dir)` | 623–649 | Write `chart_manifest.json` |

Chart manifest schema:
```json
{
  "charts": {
    "RCAT": "charts/RCAT_weekly_20260221.png",
    "funnel_graphic": {"path": "charts/funnel_20260221.png"}
  },
  "timestamp": "2026-02-21T22:00:00",
  "count": 2
}
```

#### Cost Tracker — `twitter/cost_tracker.py` (195 lines)

Centralized API cost logging with daily kill switch.

| Constant | Value |
|----------|-------|
| `DAILY_COST_LIMIT_USD` | $1.00 |
| Claude Sonnet 4 pricing | Input: $3.00/1M, Output: $15.00/1M |
| `TOOL_CALL_COST` | $0.005 per call |

| Function | Lines | Purpose |
|----------|-------|---------|
| `_load_log()` | 51–68 | Load cost log from disk; auto-reset on new day |
| `_save_log(log)` | 71–87 | Atomic write (temp → rename) |
| `log_cost(service, model, input_tokens, output_tokens, tool_calls)` | 94–140 | Log API call; **raises RuntimeError if daily limit exceeded** |
| `get_daily_total()` | 143–146 | Today's cumulative USD |
| `get_weekly_total()` | 149–159 | Weekly aggregate (returns daily for now) |

#### Health Check — `twitter/health_check.py` (332 lines)

9-point diagnostic system:

| # | Check | Type | Threshold |
|---|-------|------|-----------|
| 1 | `check_anthropic_api()` | Critical | API connectivity |
| 2 | `check_x_api("main")` | Critical | X/Twitter account 1 creds |
| 3 | `check_x_api("account2")` | Warning | X/Twitter account 2 creds |
| 4 | `check_x_api("account3")` | Warning | X/Twitter account 3 creds |
| 5 | `check_xai_api()` | Critical | Grok API connectivity |
| 6 | `check_chartimg_api()` | Warning | chart-img.com API |
| 7 | `check_tv_session()` | Warning | TradingView session validity |
| 8 | `check_portfolio_freshness()` | Warning | portfolio.csv age (alert if >10 days) |
| 9 | `get_weekly_cost()` | Info | Cost tracking status |

Exit code 0 if all critical checks pass; exit code 1 if any critical check fails.

### 9.5 Validation Pipeline Summary

Both weekly and live generators share the **identical** 7-step validation:

```
Tweet Text
    │
    ▼
┌─────────────────────────────────────────────────┐
│ Step 1: Category Check                           │
│   Valid category? Required elements present?     │
├─────────────────────────────────────────────────┤
│ Step 2a: Meta-language Detection                 │
│   No "cannot generate", "$TICKER" placeholders   │
├─────────────────────────────────────────────────┤
│ Step 2b: Ticker + Price Accuracy                 │
│   All $TICKERs from source data? (strict for    │
│   DATA_DEPENDENT: SCANNER_RESULT, SELL_SIGNAL,   │
│   DAILY_SIGNAL, PERFORMANCE, TECHNICAL_ANALYSIS, │
│   WATCHLIST)                                     │
├─────────────────────────────────────────────────┤
│ Step 3: Banned Phrase Check                      │
│   ALL_BANNED absent? Word-boundary matching      │
├─────────────────────────────────────────────────┤
│ Step 4: Winners-Only Check                       │
│   No negative P&L? No fabrication?               │
├─────────────────────────────────────────────────┤
│ Step 5: Internal Terminology                     │
│   INTERNAL_TERM_PATTERNS regex scan              │
├─────────────────────────────────────────────────┤
│ Step 6: Character Count + Temporal               │
│   ≤280 chars? No year-end in Q1?                 │
├─────────────────────────────────────────────────┤
│ Step 7: Chart Flag Check                         │
│   chart_required matches category expectation?   │
└─────────────────────────────────────────────────┘
    │                          │
    ▼ PASS                     ▼ FAIL
  Queue tweet              Repair (LLM)
                              │
                              ▼ max 2 attempts
                           PASS → Queue
                           FAIL → Drop + log to failed_tweets.json
```

---

## 10. Posting Pipeline

### 10.1 Poster — `twitter/poster.py` (1,100 lines)

Posts scheduled tweets from weekly/daily/live queues to X/Twitter via the
7-slot system. Routes content based on current time slot.

#### 7-Slot System Configuration (lines 80–95)

```
Slot  Time(ET)  Source Queue           Days        Purpose
────  ────────  ────────────────────   ─────────   ──────────────────
  1   07:30     daily_content_queue    Mon-Fri     Pre-market recap
  2   10:00     content_queue          Daily       Morning theme/signal
  3   12:30     content_queue          Daily       Position update + chart
  4   15:30     content_queue          Daily       POWER HOUR (CRITICAL)
  5   18:00     content_queue          Daily       After-hours engagement
  6   17:00     daily_content_queue    Mon-Fri     Post-close daily recap
  7   18:30     daily_content_queue    Mon-Fri     Evening overflow
```

```python
DAILY_SLOTS  = {1, 6, 7}     # → daily_content_queue.json
WEEKLY_SLOTS = {2, 3, 4, 5}  # → content_queue.json
```

#### Queue Routing

**`get_current_slot()`** (lines 466–500) — Determine slot from Eastern Time:

```
Time Range (ET)     → Slot
< 09:30             → 1
09:30 – 12:00       → 2
12:00 – 14:30       → 3
14:30 – 16:30       → 4
16:30 – 17:15       → 5
17:15 – 18:15       → 6
18:15 – 20:00       → 7
else                → 0 (off-hours)
```

**`get_queue_for_slot(slot, account_key)`** (lines 397–412):

| Slot Type | Queue File (account 1) | Queue File (account 2) | Queue File (account 3) |
|-----------|----------------------|----------------------|----------------------|
| Daily (1,6,7) | `daily_content_queue.json` | `daily_content_queue_account2.json` | `daily_content_queue_account3.json` |
| Weekly (2-5) | `content_queue.json` | `content_queue_account2.json` | `content_queue_account3.json` |
| Live | `live_content_queue.json` | `live_content_queue.json` | `live_content_queue.json` |

#### Pre-Post Validation (lines 202–282)

**`validate_before_posting(tweet)`** — Final safety gate before API submission:

| # | Check | Action on Fail |
|---|-------|---------------|
| 1 | No negative P&L (losers) | Block post |
| 2 | No critical banned terms (word-boundary) | Block post |
| 3 | No old color system (TEAL/PURPLE/AMBER) | Block post |
| 4 | No killed categories | Block post |
| 5 | No US-specific content (reserved) | Block post |
| 6 | Tweet length ≤280 chars | Block post |

Returns `(can_post: bool, reason: str)`.

#### Deduplication (lines 102–195)

| Function | Lines | Method |
|----------|-------|--------|
| `is_duplicate_content(tweet_text, queue)` | 102–121 | Exact text match against already-posted tweets |
| `check_similarity_duplicate(text, queue, hours)` | 156–195 | `SequenceMatcher` ratio > 0.7 within N hours |

#### X/Twitter API Integration (lines 289–871)

**`get_clients(account_key)`** (lines 289–337):
- Gets credentials from env vars with account-specific prefix (`X1_`, `X2_`, `X3_`)
- Returns `(client_v2, api_v1)` for tweet posting + media upload
- Returns `(None, None)` if credentials missing

**`verify_credentials(account_key)`** (lines 340–358):
- Calls GET `/2/users/me` (free, read-only) to verify auth

**`upload_media(api_v1, image_path)`** (lines 563–586):
- Uploads image to X via v1.1 API
- Returns `media_id` for attachment

**`post_tweet(client_v2, api_v1, tweet, dry_run)`** (lines 596–708):

Workflow:
1. Call `validate_before_posting()` — block if fails
2. If `dry_run`, print preview and return
3. Upload media (up to 4 images via `get_all_chart_paths()`)
4. Post via v2 API with retry (3 attempts, exponential backoff)
5. Update tweet status to `"posted"`
6. Register signal tweet for milestone tracking
7. Log generation method

**`post_quote_tweet(client_v2, original_tweet_id, quote_text, ...)`** (lines 710–765):
- Quote tweet for milestone celebration

**`post_thread(client_v2, api_v1, thread_item, dry_run)`** (lines 768–871):
- Multi-tweet thread with media support

#### Queue File Operations

| Function | Lines | Safety |
|----------|-------|--------|
| `load_queue(queue_file)` | 419–438 | Exit with error if file missing |
| `save_queue(queue, queue_file)` | 441–463 | **Atomic write**: temp file → `os.replace()` |
| `find_next_content(queue, force, target_slot)` | 502–556 | Filters: `scheduled_date <= today`, `current_slot >= slot`, not expired (>3 days stale) |

#### Main Entry Point

**`post_for_account(account_key, args, target_slot)`** (lines 873–1011):

1. Get current slot → select queue (daily or weekly)
2. Load queue JSON
3. Find next pending content
4. Post tweet/thread
5. Save queue atomically

**`main()`** (lines 1014–1100): CLI with `--dry-run`, `--force`, `--account`, `--target-slot`.

### 10.2 Queue System Summary

```
FRIDAY PIPELINE (GitHub Actions)
    tweet_generator.py
        ├── content_queue.json          (28 tweets, account 1)
        ├── content_queue_account2.json (28 tweets, account 2)
        └── content_queue_account3.json (28 tweets, account 3)

DAILY PIPELINE (Mon-Fri GitHub Actions)
    tweet_generator.py --daily
        ├── daily_content_queue.json          (up to 5 tweets, account 1)
        ├── daily_content_queue_account2.json (up to 5 tweets, account 2)
        └── daily_content_queue_account3.json (up to 5 tweets, account 3)

LIVE PIPELINE (Market hours GitHub Actions)
    live_tweet_generator.py
        └── live_content_queue.json     (shared across accounts)

POSTING (7 slots/day)
    poster.py
        Slot 1 (07:30) → daily queue
        Slot 2 (10:00) → weekly queue
        Slot 3 (12:30) → weekly queue
        Slot 4 (15:30) → weekly queue   ← POWER HOUR
        Slot 5 (18:00) → weekly queue
        Slot 6 (17:00) → daily queue
        Slot 7 (18:30) → daily queue
```

---

## 11. GitHub Actions Automation

Four workflow files orchestrate the entire system. All run on `ubuntu-latest`
with `permissions: contents: write` for git push.

### 11.1 Overview

| Workflow | File | Lines | Trigger | Jobs | Cost/Run |
|----------|------|-------|---------|------|----------|
| Friday Weekly Scan | `friday_scan.yml` | 482 | Manual + Fri 21:30 UTC | `weekly-scan` | $3–6 |
| Daily BoS Scan | `daily_scan.yml` | 347 | Manual + Mon-Fri 20:35/21:35 UTC | `daily-scan` | $0.30–0.60 |
| Live Tweet Generation | `live_tweet.yml` | 352 | Manual + 14 crons | `generate-and-post` | $0.10–0.30/slot |
| *(daily_post.yml)* | *(referenced in CLAUDE.md)* | — | 14 crons (7 slots × 2) | — | $0 |

### 11.2 Friday Weekly Scan — `friday_scan.yml` (482 lines)

**Trigger:**
- `workflow_dispatch` with inputs: `top_n`, `skip_charts`, `skip_tweets`, `skip_content`
- `schedule: cron: '30 21 * * 5'` (Friday 4:30 PM ET = 21:30 UTC)

**Timeout:** 25 minutes

#### 18-Step Pipeline

| # | Step | Cost | Notes |
|---|------|------|-------|
| 1 | Checkout repository | $0 | `actions/checkout@v4` |
| 2 | Set up Python 3.11 | $0 | `actions/setup-python@v5` with pip cache |
| 3 | Install dependencies | $0 | `pip install -r requirements.txt` |
| 4 | **Run Scanner** | **$0** | `python -m scanner.scanner --archive` (pure technical, no LLM) |
| 5 | Check notification config | $0 | Validate email/Twilio secrets |
| 6 | Send scan summary notification | Variable | Email + WhatsApp for buy + sell signals |
| 7 | Generate Funnel Graphic | $0 | `continue-on-error: true` |
| 8 | Capture TradingView Charts | $0 | Headless Playwright; `if: skip_charts != 'true'` |
| 9 | Generate Portfolio Dashboard | $0 | HTML + PNG with equity curve |
| 10 | **Generate Tweets** (3 accounts × 28) | **$1–3** | `tweet_generator --account all` |
| 11 | Generate Content Production Guide | $0 | Adaptive schedule + context |
| 12 | **Generate Substack Notes** (21/week) | **$2–4** | `notes_batch_generator --html` |
| 13 | Upload artifacts | $0 | Scan results, notes, posts, charts, queues |
| 14 | Record workflow status | $0 | JSON in `twitter/output/workflow_status.json` |
| 15 | Commit and push results | $0 | `git pull --rebase` then push; fallback to merge |
| 16 | Deploy dashboard to Vercel | $0 | `continue-on-error: true` |
| 17 | Generate Summary | $0 | GitHub Step Summary table |
| 18 | Notify on Failure | Variable | Email alert if workflow fails |

**Key design decisions:**

- **Pure technical first (Step 4, $0):** Scanner runs `--archive` flag without LLM.
  Outputs `signals.json`, `portfolio.csv`, `analysis_log.csv` at zero cost.
- **LLM content second (Steps 10 + 12, $3–7):** Tweet generation + notes use
  Claude Sonnet 4 and can be skipped independently via input flags.
- **Conditional skips:** Steps 7, 8, 9, 11, 12, 16, 18 marked `continue-on-error: true`.
- **Git safety (lines 368–375):** `git pull --rebase` before push with fallback
  to merge if rebase fails. Prevents race conditions with concurrent `daily_scan.yml`.

**Secrets used:**

| Secret | Steps | Purpose |
|--------|-------|---------|
| `ANTHROPIC_API_KEY` | 10, 12 | LLM calls for tweets + notes |
| `NOTIFICATION_EMAIL`, `SMTP_*` | 5-6, 18 | Email notifications |
| `TWILIO_*` | 5-6 | WhatsApp notifications |
| `TRADINGVIEW_COOKIES` | 8 | TradingView headless login |
| `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | 16 | Dashboard deployment |

### 11.3 Daily BoS Scan — `daily_scan.yml` (347 lines)

**Trigger:**
- `workflow_dispatch` with inputs: `dry_run`, `top_n`, `skip_charts`, `skip_tweets`
- Two crons for EST/EDT: `'35 21 * * 1-5'` + `'35 20 * * 1-5'`

**Timeout:** 45 minutes | **Concurrency:** `group: daily-scan, cancel-in-progress: false`

#### 15-Step Pipeline

| # | Step | Cost |
|---|------|------|
| 1 | Checkout repository | $0 |
| 2 | Set up Python 3.11 | $0 |
| 3 | Install dependencies | $0 |
| 4 | **Run Daily Scanner** | **$0** |
| 5 | Check notification config | $0 |
| 6 | Send scan summary notification | Variable |
| 7 | Install Playwright | $0 |
| 8 | Capture daily charts | $0 |
| 9 | **Generate daily signal tweets** | **$0.30–0.60** |
| 10 | Upload daily artifacts | $0 |
| 11 | Record workflow status | $0 |
| 12 | Commit and push results | $0 |
| 13 | Deploy dashboard | $0 |
| 14 | Generate Summary | $0 |
| 15 | Notify on Failure | Variable |

**EST/EDT Dual Cron Strategy:**

Both crons fire year-round. The scanner itself handles deduplication gracefully
if run twice on the same day (idempotent signals, atomic portfolio writes).

**Concurrency control** prevents overlapping runs — queues second trigger rather
than cancelling.

### 11.4 Live Tweet Generation — `live_tweet.yml` (352 lines)

**Trigger:**
- `workflow_dispatch` with inputs: `force_type`, `dry_run`
- **14 cron triggers** (5 weekday × 2 EST/EDT + 2 weekend × 2 EST/EDT)

**Cron Schedule:**

| Slot | Time (ET) | Weekday EST | Weekday EDT | Weekend EST | Weekend EDT |
|------|-----------|-------------|-------------|-------------|-------------|
| 1 | 07:30 | `30 12 * * 1-5` | `30 11 * * 1-5` | — | — |
| 2 | 10:00 | `0 15 * * 1-5` | `0 14 * * 1-5` | `0 15 * * 0,6` | `0 14 * * 0,6` |
| 3 | 12:30 | `30 17 * * 1-5` | `30 16 * * 1-5` | — | — |
| 4 | 15:30 | `30 20 * * 1-5` | `30 19 * * 1-5` | — | — |
| 5 | 18:00 | `0 23 * * 1-5` | `0 22 * * 1-5` | — | — |
| — | 16:00 | — | — | `0 21 * * 0,6` | `0 20 * * 0,6` |

**Timezone Deduplication Logic (lines 94–123):**

Both EST and EDT crons fire year-round. Workflow detects current ET offset
via Python's `zoneinfo` and skips wrong-season crons:

```
ET_OFFSET = -05 (EST season):
  → Skip EDT cron hours (11,14,16,19,20,22)
  → Run EST cron hours  (12,15,17,20,21,23)

ET_OFFSET = -04 (EDT season):
  → Skip EST cron hours (12,15,17,21,23)
  → Run EDT cron hours  (11,14,16,19,20,22)
```

**Account Staggering:** 10-minute delays between accounts (1 → 2 → 3) to avoid
rate limits.

**Environment Variables:** 16 X/Twitter secrets (4 per account × 3 accounts +
`ANTHROPIC_API_KEY`, `XAI_API_KEY`, `CHARTIMG_API_KEY`, `TRADINGVIEW_COOKIES`).

### 11.5 Weekly Cost Summary

```
┌──────────────────────────────────────────────────────┐
│                 WEEKLY CI/CD COSTS                     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Friday Weekly Scan (1×/week)                         │
│    Scanner (pure technical):        $0.00             │
│    Tweets (28 × 3 accounts):       $1.50–3.00        │
│    Notes (21 batch):               $1.50–3.00        │
│    Subtotal:                       $3.00–6.00        │
│                                                       │
│  Daily Scan (5×/week, Mon-Fri)                        │
│    Scanner (pure technical):        $0.00             │
│    Daily tweets (up to 5):         $0.30–0.60/run    │
│    Subtotal:                       $1.50–3.00        │
│                                                       │
│  Live Tweets (5 weekday + 2 weekend slots)            │
│    Generation (Sonnet):            $0.10–0.30/slot   │
│    Weekly subtotal (37 slots):     $3.70–11.10       │
│                                                       │
│  ════════════════════════════════════════════════     │
│  TOTAL WEEKLY:                     $8.20–20.10       │
│  ════════════════════════════════════════════════     │
│                                                       │
│  Kill switch: $1.00/day on live tweets                │
│  All posting (API calls to X): $0                     │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

## 12. Daily Scanner

### 12.1 Module — `scanner/daily_scanner.py` (791 lines)

Lightweight weekday (Mon-Fri) technical scanner that identifies Break of
Structure buy signals on **daily bars** without thematic analysis, gatekeeper,
or due diligence. Pure technical, $0 cost.

### 12.2 Key Differences from Weekly Scanner

| Aspect | Weekly (`scanner.py`) | Daily (`daily_scanner.py`) |
|--------|----------------------|---------------------------|
| Timeframe | Weekly bars (HMA on resampled weekly) | Daily bars (no resample) |
| Indicators | Sterling Grid (HMA slope, RSI, MACD, UC, ExD) | Legacy (Banker + HMA BoS) |
| Thematic Analysis | Yes (Claude Sonnet) | **NO** |
| Investment Gate | Yes (Sonnet) | **NO** |
| Deep DD | Yes (Opus) | **NO** |
| Max Signals/Period | Varies | **5 per day** (hard cap) |
| Portfolio File | `portfolio.csv` | `daily_portfolio.csv` |
| Signals File | `signals.json` | `daily_signals.json` |
| Sell Notifications | Optional | **Required** (email + WhatsApp) |
| Cost per Run | $1–3 (with web search) | **$0** (pure technical) |

### 12.3 Data Structures (lines 88–152)

**DailySignal** (lines 91–100):
```
Fields: ticker, price, beta, banker_score, sector, industry
```
Lightweight 6-field signal representation (vs Stock's 60+ fields in weekly).

**DailyTrade** (lines 102–151):
```
Fields: ticker, entry_date, entry_price, highest_close, stop_pct,
        theme, timeframe, status, exit_date, exit_price, exit_reason
CSV_FIELDS: 11 columns
Methods: to_csv_row() → dict, from_csv_row(row) → DailyTrade
```

### 12.4 Function Reference

#### Indicator Calculation

**`calculate_bos_daily(df, hma_length=21, pivot_k=1)`** (lines 158–236):

Computes Break of Structure on daily bars:
1. Check minimum bars (50 required)
2. Compute HL2 = (High + Low) / 2
3. Calculate HMA via `scanner.legacy_indicators.calculate_hma()`
4. Find pivots via `scanner.legacy_indicators.find_pivots()`
5. Build step lines carrying forward last pivot value
6. Compare current vs previous step lines → `bos_up` / `bos_down`

Returns `(bos_up: bool, bos_down: bool, debug_info: dict)`.

Uses **legacy indicators** (not Sterling Grid) because the daily scanner
predates the Sterling Grid upgrade and was intentionally left on the old
indicator set.

#### Portfolio I/O

| Function | Lines | Purpose |
|----------|-------|---------|
| `load_daily_portfolio(path)` | 243–253 | Load `daily_portfolio.csv` → `List[DailyTrade]` |
| `save_daily_portfolio(trades, path)` | 256–288 | Atomic write: backup → temp → `os.replace()` |
| `load_weekly_open_symbols(path)` | 291–304 | Get OPEN tickers from weekly `portfolio.csv` |

Backup strategy: Before each write, copy current file to
`daily_portfolio_YYYYMMDD_HHMMSS.csv`. Prune to keep latest 30 only.

#### Deduplication

**`_recently_signalled(ticker, daily_trades, lookback_days=7)`** (lines 311–336):

Check if ticker was signalled within last N days **and still OPEN**:
- OPEN trade within window → duplicate (skip)
- STOPPED/CLOSED trade within window → eligible again (dedup reset)

**`deduplicate(tickers, daily_trades, weekly_open, lookback_days=7)`** (lines 339–353):

Two-stage filter:
1. Remove tickers in weekly OPEN positions
2. Remove tickers recently signalled and still OPEN in daily portfolio

**Example:**
```
Weekly OPEN:  {RCAT}
Daily trades: OKLO (OPEN, 2 days ago), IBKR (STOPPED, 8 days ago)
Candidates:   [RCAT, OKLO, IONQ, IBKR]

After dedup:  [IONQ, IBKR]
  RCAT  → removed (in weekly OPEN)
  OKLO  → removed (OPEN within 7-day lookback)
  IONQ  → kept (not in either portfolio)
  IBKR  → kept (STOPPED = dedup reset)
```

#### Data Download

**`download_daily_data(tickers, period="6mo")`** (lines 360–412):
- Chunks tickers into groups of 50
- Uses `yf.download()` with `threads=True`
- 0.3s sleep between chunks for rate limiting
- Progress display: `Downloading daily bars: 75% (3/4 chunks)`
- Minimum bars check: `DAILY_MIN_BARS = 50`

**`download_spy_returns(period="6mo")`** (lines 415–429):
- Downloads SPY, computes `pct_change()`, returns `pd.Series`

#### Sell Signal Detection

**`check_daily_sell_signals(trades, frames)`** (lines 450–504):

First-exit strategy — whichever fires first:
1. Update `highest_close` if today's close > current highest
2. Check BoS on daily bars → if bearish → EXIT
3. Check trailing stop → if close < `highest_close * 0.80` → EXIT
4. If both fire on same bar → combined reason string

**`_send_daily_sell_notifications(sell_signals)`** (lines 507–541):

Fire email + WhatsApp via `utils.notifications.send_sell_notification()`:
- Detect signal type from exit reason: "bos down" → BEARISH PIVOT,
  "trailing stop" → TRAILING STOP, else → EXIT
- Calculate P&L percentage
- Fire both channels independently

#### Signal Output

**`save_daily_signals(signals, path, sell_signals)`** (lines 548–592):

Write `daily_signals.json` compatible with `tweet_generator`:
```json
{
  "scan_date": "2026-02-24",
  "timeframe": "daily",
  "buy_signals": [
    {"ticker": "RCAT", "symbol": "RCAT", "price": 13.25,
     "beta": 2.48, "banker_score": 75.1,
     "sector": "Technology", "industry": "Aerospace",
     "theme": "Technology"}
  ],
  "sell_signals": [
    {"symbol": "VNET", "ticker": "VNET", "price": 10.80,
     "reason": "Daily BoS Down at $10.80",
     "entry_price": 12.00, "highest_close": 13.50,
     "pnl_pct": -10.0, "theme": "Cloud", "entry_date": "2026-02-20"}
  ]
}
```

### 12.5 Core Pipeline — `run_daily_scan()` (lines 599–768)

```
Step  1: Load tickers (~1,800)                           [lines 633-642]
Step  2: Download daily data (6 months, chunks of 50)    [lines 644-656]
Step  3: Compute indicators per ticker                   [lines 659-684]
           price, beta, skip if < 1.5
           banker + banker_rising, skip if not rising
           BoS on daily bars, skip if not up
           → candidates list
Step  4: Deduplicate                                     [lines 700-708]
           remove weekly OPEN tickers
           remove recently signalled OPEN daily tickers
Step  5: Rank by banker score (descending) + cap at 5    [lines 710-712]
Step  6: Build DailySignal objects                       [lines 714-726]
Step  7: Print results                                   [lines 727-729]
Step  8: Dry-run check (return if --dry-run)             [lines 731-733]
Step  9: Add new signals to daily portfolio              [lines 735-747]
Step 10: Check existing positions for sell signals       [lines 749-751]
Step 11: Save daily_signals.json                         [lines 753-755]
Step 12: Save daily_portfolio.csv (atomic)               [lines 757-763]
           + send notifications for sell signals
Step 13: Print summary                                   [lines 765-766]
```

### 12.6 Configuration Constants

| Constant | Value | Source |
|----------|-------|--------|
| `BETA_THRESHOLD` | 1.5 | `config/settings.py` |
| `TRAILING_STOP_PCT` | 20.0 | `config/settings.py` |
| `HMA_PERIOD` | 21 | `config/settings.py` |
| `DAILY_SIGNAL_MAX` | 5 | `config/settings.py` |
| `DAILY_DEDUP_LOOKBACK_DAYS` | 7 | `config/settings.py` |
| `DAILY_DOWNLOAD_PERIOD` | "6mo" | `config/settings.py` |
| `DAILY_MIN_BARS` | 50 | `config/settings.py` |
| `MAX_DAILY_BACKUPS` | 30 | `daily_scanner.py` line 84 |

### 12.7 Legacy Indicator Imports

The daily scanner intentionally uses legacy indicators from
`scanner/legacy_indicators.py`:

```python
from scanner.legacy_indicators import (
    calculate_banker,    # (df) → (banker, banker_prev)
    calculate_hma,       # (series, period) → Series
    find_pivots,        # (series, k) → (pivot_highs, pivot_lows)
)
```

The weekly scanner uses the newer Sterling Grid indicators from
`scanner/sterling_indicators.py`. The daily scanner was not migrated because:
1. Daily BoS has different signal characteristics than weekly
2. Tiered profit lock doesn't apply to daily timeframe
3. The daily scanner is pure technical ($0 cost) and works well as-is

---

<!-- Sections 9-12 above, Sections 13-15 below -->

---

## 13. Dependency Graph

### 13.1 File Inventory by Package (59 Python files, 38,464 total lines)

```
scanner/         (6 files,  6,564 lines)  ← Core pipeline
  scanner.py             2,518
  daily_scanner.py         791
  merge_decisions.py       615
  sterling_indicators.py 1,063
  saturday_workflow.py     397
  legacy_indicators.py     177
  due_diligence.py         494
  __init__.py                1

portfolio/       (3 files,  2,010 lines)  ← Trade tracking
  manager.py             1,713
  backup_cleanup.py        296
  __init__.py                1

substack/        (11 files, 9,316 lines)  ← Newsletter + content
  content_generator.py   1,624
  notes_batch_generator.py 1,347
  html_templates.py      1,182
  newsletter_compiler.py   947
  content_production_guide.py 858
  portfolio_visual.py      819
  dd_post_generator.py     545
  note_utils.py            463
  market_analyzer.py       282
  learning_content_library.py (in substack/)
  __init__.py                1

twitter/         (14 files, 9,242 lines)  ← Tweet pipeline + posting
  tweet_generator.py     2,225
  live_tweet_generator.py 2,027
  signal_tracker.py      1,130
  poster.py              1,100
  chart_capture.py         749
  funnel_graphic.py        670
  live_context_gatherer.py 532
  chart_generator.py       359
  health_check.py          332
  self_quote_tracker.py    304
  winner_showcase_gen.py   265
  models.py                218
  cost_tracker.py          195
  verify_tweets.py         177
  tradingview_login.py      90
  __init__.py                1

config/          (4 files,  2,066 lines)  ← Shared configuration
  settings.py            1,324
  output_paths.py          346
  banned_terms.py          377
  __init__.py               19

utils/           (3 files,  1,153 lines)  ← Utilities
  notifications.py         869
  email_notifier.py        283
  __init__.py                1

tests/           (12 files, 8,113 lines)  ← Test suite
  test_integration.py    1,348
  test_substack_content_v2.py 1,017
  test_live_tweet_system.py 1,001
  test_tweet_gen_audit_fixes.py 900
  test_sterling_indicators.py 896
  test_tweet_generator_v2.py  748
  test_tweet_gen_integration.py 475
  test_saturday_workflow.py   474
  test_daily_scanner.py      459
  test_safeguards.py         277
  test_edge_cases.py         276
  test_scheduling.py         108
  __init__.py                 13
```

### 13.2 Layered Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │           config/ (hub)              │
                    │  settings.py │ output_paths.py       │
                    │  banned_terms.py │ __init__.py        │
                    └────────┬──────────┬──────────┬───────┘
                             │          │          │
          ┌──────────────────┼──────────┼──────────┼──────────────────┐
          │                  │          │          │                  │
          ▼                  ▼          ▼          ▼                  ▼
    ┌───────────┐    ┌───────────┐  ┌────────┐  ┌──────────┐   ┌────────┐
    │ scanner/  │    │ portfolio/│  │substack/│  │ twitter/ │   │ utils/ │
    │ (6 files) │───►│ (3 files) │  │(11 fil.)│  │(14 fil.) │   │(3 fil.)│
    └─────┬─────┘    └─────┬─────┘  └────┬───┘  └────┬─────┘   └────┬───┘
          │                │             │           │              │
          │                │             │           │              │
          ▼                ▼             ▼           ▼              ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                     DATA FILES (disk I/O)                           │
    │  signals.json │ portfolio.csv │ content_queue.json │ newsletter.html │
    └─────────────────────────────────────────────────────────────────────┘
```

### 13.3 Import Matrix — Internal Dependencies

Each row shows what the file imports from other internal packages.

#### scanner/ imports

| File | Imports From |
|------|-------------|
| `scanner.py` | `scanner.sterling_indicators` (6 functions), `portfolio.manager` (6 functions), `config` (12 constants), `config.output_paths` (8 symbols) |
| `daily_scanner.py` | `scanner.scanner` (2 functions: `calculate_beta`, `load_tickers`), `scanner.legacy_indicators` (3 functions), `config` (12 constants) |
| `merge_decisions.py` | `config.output_paths` (8 symbols), `portfolio.manager` (3 functions) |
| `saturday_workflow.py` | `config.output_paths` (6 symbols), `scanner.merge_decisions` (3 functions), `substack.market_analyzer`, `substack.content_production_guide` |
| `sterling_indicators.py` | *(none — leaf module, pure math)* |
| `legacy_indicators.py` | `config` (4 constants) |

#### portfolio/ imports

| File | Imports From |
|------|-------------|
| `manager.py` | *(none from other packages — leaf module, imports only stdlib + yfinance)* |
| `backup_cleanup.py` | *(none from other packages)* |

#### substack/ imports

| File | Imports From |
|------|-------------|
| `content_production_guide.py` | `config` (5 symbols), `config.banned_terms` (3 symbols), `substack.content_generator` (1 constant) |
| `content_generator.py` | `config` (12 symbols), `config.banned_terms` (4 functions) |
| `newsletter_compiler.py` | `config.output_paths` (6 symbols), `config.banned_terms` (1 alias) |
| `notes_batch_generator.py` | `config` (8 symbols), `config.banned_terms` (3 functions), `substack.note_utils` (utilities) |
| `dd_post_generator.py` | `config` (3 symbols), `config.banned_terms` (3 symbols) |
| `portfolio_visual.py` | `config.output_paths` (4 symbols), `config.settings` (6 symbols), `config.banned_terms` (1 function), `portfolio.manager` (2 classes) |
| `note_utils.py` | `config` (3 symbols), `config.output_paths` (3 symbols), `config.banned_terms` (2 functions) |
| `market_analyzer.py` | `config.output_paths` (3 symbols) |

#### twitter/ imports

| File | Imports From |
|------|-------------|
| `tweet_generator.py` | `config.settings` (15+ symbols), `config` (5 symbols), `config.banned_terms` (4 functions), `twitter.models` (5 classes) |
| `live_tweet_generator.py` | `twitter.models` (5 classes), `config.banned_terms` (3 functions), `twitter.live_context_gatherer` (2 functions) |
| `poster.py` | `config` (1 constant: `TWEET_STALENESS_DAYS`), `config.output_paths` (6 queue paths) |
| `signal_tracker.py` | `config` (3 symbols), `portfolio.manager` (2 functions) |
| `models.py` | `config.banned_terms` (1 symbol: `INTERNAL_TERM_PATTERNS`) |
| `funnel_graphic.py` | `config` (2 symbols) |
| `winner_showcase_generator.py` | `config` (3 symbols) |

### 13.4 Hub Ranking (most-imported modules)

Modules ranked by number of dependents (files that import them):

| Rank | Module | Dependents | Role |
|------|--------|-----------|------|
| 1 | `config/settings.py` | 22 | Central constant registry |
| 2 | `config/banned_terms.py` | 16 | Marketing safety |
| 3 | `config/output_paths.py` | 14 | Path registry |
| 4 | `portfolio/manager.py` | 5 | Portfolio state |
| 5 | `twitter/models.py` | 4 | Tweet data model |
| 6 | `scanner/sterling_indicators.py` | 1 | Indicator math |
| 7 | `scanner/legacy_indicators.py` | 1 | Daily indicator math |

**Key insight:** `config/` is the hub of the entire system. Every package
depends on it but it depends on nothing external. This is correct architecture.

`portfolio/manager.py` is the second hub — consumed by scanner (for stop
checks), substack (for portfolio dashboard), and twitter (for signal tracking).

### 13.5 External Library Dependencies

| Library | Used By | Purpose |
|---------|---------|---------|
| `pandas` | scanner, portfolio, daily_scanner | DataFrames, CSV I/O |
| `numpy` | scanner, sterling_indicators, legacy_indicators | Numerical computation |
| `yfinance` | scanner, daily_scanner, portfolio/manager | Market data download |
| `anthropic` | scanner (thematic, gate, DD), tweet_generator, content_generator, notes, newsletter | Claude API |
| `tweepy` | poster | X/Twitter API v1.1 + v2 |
| `playwright` | chart_capture | TradingView screenshots |
| `matplotlib` | portfolio_visual, funnel_graphic | Chart generation |

---

## 14. Data Flow Paths & Field Compatibility

### 14.1 Six Primary Data Flow Paths

```
PATH A: WEEKLY SCAN → SIGNALS
  complete_tickers.txt → scanner.py → signals_technical.json
                                    → portfolio.csv (stop checks)
                                    → analysis_log.csv (append)
                                    → current/report.txt
                                    → current/newsletter_briefing.md

PATH B: CHAT SESSION → AUTOMATION BRIDGE
  signals_technical.json ──┐
  decisions.json ──────────┼── merge_decisions.py → signals.json
  (from Claude.ai)         │                      → content_schedule.json
                           │                      → portfolio updates
                           └── saturday_workflow.py (orchestrator)

PATH C: SIGNALS → CONTENT
  signals.json ────────────┐
  portfolio.csv ───────────┼── tweet_generator.py → content_queue.json (×3)
                           ├── content_production_guide.py → guide.md
                           ├── newsletter_compiler.py → newsletter.html
                           ├── content_generator.py → substack_posts/
                           ├── notes_batch_generator.py → substack_notes/
                           ├── dd_post_generator.py → dd_*.html
                           └── portfolio_visual.py → portfolio_visual.html

PATH D: CONTENT → POSTING
  content_queue.json ────── poster.py → X/Twitter API (slots 2-5)
  daily_content_queue.json ─ poster.py → X/Twitter API (slots 1,6,7)
  live_content_queue.json ── poster.py → X/Twitter API (live)

PATH E: DAILY SCAN → DAILY SIGNALS
  complete_tickers.txt → daily_scanner.py → daily_signals.json
                                          → daily_portfolio.csv
                                          → notifications (email/WhatsApp)
  daily_signals.json → tweet_generator --daily → daily_content_queue.json (×3)

PATH F: LIVE MARKET → LIVE TWEETS
  portfolio.csv ───────┐
  signals.json ────────┼── live_tweet_generator.py → live_content_queue.json
  live_context.json ───┘
  (from Grok API)
```

### 14.2 signals.json Consumer Matrix

`signals.json` is the **most consumed data file** in the system. Every downstream
module reads it, but each consumes different fields.

| Consumer | Fields Used | Notes |
|----------|------------|-------|
| `tweet_generator.py` | `buy_signals[].symbol`, `.price`, `.theme`, `.theme_score`, `.conviction`, `.bullish_factors`, `.catalyst_summary`, `.final_decision`; `themes[]`; `sell_signals[]`; `stats` | Core data for tweet content |
| `content_production_guide.py` | `buy_signals[]` count, `themes[]` names + classification, `stats.final_trade`, `sell_signals[]` | Schedule decisions |
| `newsletter_compiler.py` | Full `buy_signals[]` with DD fields, `themes[]` with sub-scores, `sell_signals[]`, `stats` | Newsletter compilation |
| `content_generator.py` | `buy_signals[]`, `themes[]`, `sell_signals[]`, `stats` | Substack post content |
| `notes_batch_generator.py` | `buy_signals[]`, `themes[]`, portfolio context | Note generation |
| `dd_post_generator.py` | `buy_signals[]` with DD fields (elevator_pitch, why_now, the_math, bear_case, risk_to_monitor) | DD post HTML |
| `signal_tracker.py` | `buy_signals[].symbol`, `.price`, `.conviction` | Win tracking |
| `live_tweet_generator.py` | `buy_signals[]`, `themes[]` | Live context |
| `funnel_graphic.py` | `stats` (scan funnel counts) | Visualization |

### 14.3 portfolio.csv Consumer Matrix

| Consumer | Fields Used | Notes |
|----------|------------|-------|
| `scanner.py` | `ticker`, `status` (OPEN only), `entry_price`, `highest_close` | Stop checks |
| `tweet_generator.py` | `ticker`, `entry_price`, `current_price`, `pnl_pct`, `theme`, `conviction` | Tweet content |
| `live_tweet_generator.py` | Same as tweet_generator | Live tweets |
| `content_production_guide.py` | Position count, win rate, top winners | Schedule context |
| `portfolio_visual.py` | Full trade history + equity snapshots | Dashboard |
| `daily_scanner.py` | `ticker`, `status` (OPEN only) | Dedup filter |
| `signal_tracker.py` | `ticker`, `entry_price`, current prices | Milestone tracking |

### 14.4 Field Mapping: decisions.json → signals.json

The merge bridge (`merge_decisions.py`) maps interactive decisions to the
downstream-compatible signals format:

| decisions.json field | signals.json field | Notes |
|---------------------|-------------------|-------|
| `new_positions[].symbol` | `buy_signals[].symbol` | Direct copy |
| `new_positions[].price` | `buy_signals[].price` | Direct copy |
| `new_positions[].theme` | `buy_signals[].theme` | Direct copy |
| `new_positions[].verdict` | `buy_signals[].final_decision` | STRONG_BUY → TRADE, SPEC_BUY → CONSIDER |
| `new_positions[].conviction` | `buy_signals[].conviction` | 1-10 scale |
| `new_positions[].reasoning` | `buy_signals[].catalyst_summary` | Mapped |
| `exits[].symbol` | `sell_signals[].symbol` / `exit_signals[].symbol` | Dual output |
| `themes_this_week[]` | `themes[]` | Theme objects with scores |
| `market_regime` | `stats.market_regime` | Market context |
| *(computed)* | `buy_signals[].banker` | Set to UC value for backward compat |
| *(computed)* | `buy_signals[].beta` | From signals_technical.json if available |

### 14.5 Queue Entry Schema Compatibility

All three queue types share a common schema consumed by `poster.py`:

| Field | Weekly Queue | Daily Queue | Live Queue |
|-------|-------------|-------------|------------|
| `id` | `"{day}_{slot}_{i}"` | `"daily_{day}_{slot}_{i}"` | `"live_{timestamp}"` |
| `text` | ✓ | ✓ | ✓ |
| `category` | ✓ | ✓ | ✓ |
| `status` | `"pending"` | `"pending"` | `"pending"` |
| `posted` | `false` | `false` | *(not present)* |
| `scheduled_date` | ✓ | ✓ | *(not present)* |
| `slot` | 2-5 | 1,6,7 | *(not present)* |
| `chart_required` | ✓ | ✓ | *(may be absent)* |
| `chart_path` | ✓ | ✓ | ✓ |
| `mentioned_tickers` | ✓ | ✓ | *(may be absent)* |
| `account` | *(implicit from file)* | *(implicit from file)* | ✓ (explicit) |

**Compatibility note:** The poster handles missing fields gracefully with
`.get()` defaults, so the schema differences don't cause runtime errors.

---

## 15. Known Issues & Recommendations

### 15.1 Issues by Severity

#### CRITICAL

*No critical issues identified.* The system is production-stable with all tests
passing (217 tests across 12 test files).

#### HIGH

| # | Issue | Location | Description | Recommendation |
|---|-------|----------|-------------|----------------|
| H1 | **signals.json dual-write path** | `scanner.py` lines 2195–2209 | Scanner writes `signals_technical.json` (primary) but also writes a transitional `signals.json` for backward compat. `merge_decisions.py` overwrites this `signals.json` with the merged version. If Saturday workflow doesn't run, downstream gets stale/technical-only data. | Add a health check that warns if `signals.json` timestamp < `signals_technical.json` timestamp |
| H2 | **Live tweet cost tracking separate from batch** | `twitter/cost_tracker.py` vs `tweet_generator.py` CostTracker | Two independent cost tracking systems: live uses `cost_tracker.py` with $1/day kill switch; batch uses internal `CostTracker` class. Neither sees the other's spend. | Unify into single cost tracker; aggregate daily spend across both systems |
| H3 | **EST/EDT dual crons fire redundantly** | `.github/workflows/daily_scan.yml`, `live_tweet.yml` | Both EST and EDT cron triggers fire year-round. `live_tweet.yml` has dedup logic; `daily_scan.yml` relies on scanner idempotency. | Add explicit timezone dedup to `daily_scan.yml` matching `live_tweet.yml` approach |

#### MEDIUM

| # | Issue | Location | Description | Recommendation |
|---|-------|----------|-------------|----------------|
| M1 | **Legacy `TRADES_DIR` alias** | `config/output_paths.py` line 39 | Deprecated alias kept for gradual migration. All production code uses section-specific paths now. | Remove after confirming zero references remain |
| M2 | **`content_generator.py` partially superseded** | `substack/content_generator.py` | Content production guide + handbook v5 workflow via Claude.ai has largely replaced automated post generation, but the module is still invoked by Friday Actions. | Document which post types are still auto-generated vs Claude.ai-produced; consider making it opt-in |
| M3 | **Portfolio manager has no config imports** | `portfolio/manager.py` | Defines its own constants (CSV fields, date formats, etc.) rather than importing from `config/settings.py`. | Extract shared constants to config for consistency |
| M4 | **`signal_tracker.py` is large (1,130 lines)** | `twitter/signal_tracker.py` | Combines win tracking, milestone detection, self-quoting, and celebration logic in one file. | Consider splitting into `win_tracker.py` + `milestone_tracker.py` |
| M5 | **Daily scanner uses legacy indicators** | `scanner/daily_scanner.py` | Uses `legacy_indicators.py` (Banker + HMA BoS) while weekly uses Sterling Grid V6. Intentional, but undocumented. | Add inline comment explaining the rationale (or migrate to Sterling Grid) |
| M6 | **`html_templates.py` is pure data (1,182 lines)** | `substack/html_templates.py` | Large file containing only HTML template strings. | Consider moving to `substack/templates/` directory as separate `.html` files |

#### LOW

| # | Issue | Location | Description | Recommendation |
|---|-------|----------|-------------|----------------|
| L1 | **Deprecated functions in `output_paths.py`** | `config/output_paths.py` lines 134-141 | `get_current_dir()`, `get_week_dir()`, `save_to_current_and_archive()`, `copy_to_current_and_archive()` are marked DEPRECATED. | Add deprecation warnings; remove after confirming zero callers |
| L2 | **Import fallback blocks** | `scanner.py` lines 107-136, `poster.py` lines 60-78 | Many files have `try/except ImportError` blocks with fallback path definitions. These were needed during migration but may be unnecessary now. | Audit which fallbacks still trigger; remove if all imports succeed in CI |
| L3 | **`verify_tweets.py` may be unused** | `twitter/verify_tweets.py` (177 lines) | Standalone verification script that duplicates validation logic from `tweet_generator.py`. | Verify if still used in any workflow; if not, archive |
| L4 | **No type hints on some older functions** | Various files | Some functions lack type annotations, particularly in `scanner.py` and `poster.py`. | Add type hints incrementally |

### 15.2 Quick Wins (< 1 hour each)

1. **Add `signals.json` freshness check** to `saturday_workflow.py` — warn if
   merge hasn't run but downstream expects merged data.

2. **Add explicit timezone dedup** to `daily_scan.yml` — copy the approach from
   `live_tweet.yml` lines 94-123.

3. **Remove `TRADES_DIR` alias** from `config/output_paths.py` — grep confirms
   zero production references remain.

4. **Add deprecation warnings** to `get_current_dir()`, `get_week_dir()` in
   `output_paths.py`.

5. **Document daily scanner indicator choice** — add a comment in
   `daily_scanner.py` explaining why it uses legacy indicators.

### 15.3 Refactoring Roadmap (Longer-term)

| Phase | Effort | Impact | Description |
|-------|--------|--------|-------------|
| 1 | Small | Medium | Unify cost tracking: merge `cost_tracker.py` + internal `CostTracker` into single system |
| 2 | Small | Low | Extract HTML templates from `html_templates.py` into `substack/templates/` directory |
| 3 | Medium | Medium | Split `signal_tracker.py` (1,130 lines) into focused modules |
| 4 | Medium | High | Migrate daily scanner to Sterling Grid V6 indicators (requires backtesting on daily bars) |
| 5 | Large | Medium | Remove all `try/except ImportError` fallback blocks after confirming CI stability |
| 6 | Large | High | Add comprehensive type hints across all modules |

### 15.4 Test Coverage Summary

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_sterling_indicators.py` | 63 | Sterling Grid indicator math |
| `test_integration.py` | 34 | Cross-module: Friday pipeline, daily pipeline, posting, content, QQQ benchmark, DD posts |
| `test_tweet_generator_v2.py` | 24 | Tweet generation + validation |
| `test_tweet_gen_audit_fixes.py` | ~30 | Audit fix regressions |
| `test_tweet_gen_integration.py` | ~15 | Tweet gen end-to-end |
| `test_daily_scanner.py` | 11 | Daily scanner pipeline |
| `test_substack_content_v2.py` | ~20 | Substack content generation |
| `test_live_tweet_system.py` | ~15 | Live tweet pipeline |
| `test_safeguards.py` | ~10 | Safety guard tests |
| `test_edge_cases.py` | ~10 | Edge case handling |
| `test_saturday_workflow.py` | ~10 | Saturday workflow steps |
| `test_scheduling.py` | ~5 | Schedule planning |
| **TOTAL** | **~247** | |

**Gaps:** No dedicated tests for `portfolio/manager.py` (tested indirectly via
integration tests), `utils/notifications.py`, `twitter/poster.py`,
`config/output_paths.py`.

---

*End of Codebase Audit — Generated 2026-02-24*
