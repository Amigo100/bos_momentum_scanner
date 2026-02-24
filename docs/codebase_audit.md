# BoS Momentum Scanner — Comprehensive Codebase Audit

**Date:** 2026-02-23
**Codebase Size:** ~44,956 lines of Python across 50+ files, 5 GitHub Actions workflows
**Branch:** master (3 modified, 12 untracked files)
**Phase 0 deliverable per `claude_code_refactoring_strategy.md`**

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

```
                    WEEKLY PIPELINE (Friday 16:30 ET)
    ┌──────────────────────────────────────────────────────────────┐
    │  Tickers (~1,800)                                            │
    │      ↓                                                       │
    │  Download OHLCV (yfinance, 1yr daily)                       │
    │      ↓                                                       │
    │  Sterling Grid V6 Indicators (sterling_indicators.py)       │
    │    HMA(21) pivot + UC rising/MACD cross + Price <$25        │
    │      ↓                                                       │
    │  Thematic Analyzer (thematic_analyzer.py, Sonnet)           │
    │    Step 1: 5 macro themes → Step 2: bottom-up ticker fit    │
    │      ↓                                                       │
    │  Investment Gate (investment_gate.py, Sonnet)                │
    │    4-phase: Disqualify → Catalyst → Return → Verdict        │
    │      ↓                                                       │
    │  Deep DD (deep_dd.py, Opus + extended thinking)             │
    │    1-3 stocks only. Newsletter content + final veto.         │
    │      ↓                                                       │
    │  Sell signal check (ExD or tiered profit lock)              │
    │      ↓                                                       │
    │  Portfolio update → signals.json → newsletter → tweets      │
    └──────────────────────────────────────────────────────────────┘

                    DAILY PIPELINE (Mon-Fri 16:35 ET)
    ┌──────────────────────────────────────────────────────────────┐
    │  Same tickers, daily bars, legacy indicators only            │
    │  No LLM. Max 5 signals/day. Separate daily_portfolio.csv.   │
    │  Email + WhatsApp notifications on exits.                    │
    └──────────────────────────────────────────────────────────────┘

                    CONTENT SYSTEM
    ┌──────────────────────────────────────────────────────────────┐
    │  tweet_generator.py → 28 weekly tweets (7 days x 4 slots)  │
    │  live_tweet_generator.py → intraday tweets (market hours)   │
    │  poster.py → 7-slot posting (3 X accounts)                  │
    │  newsletter_compiler.py → HTML newsletter for Substack      │
    │  content_generator.py → 4 adaptive Substack posts/week     │
    │  notes_batch_generator.py → 21 Substack notes/week         │
    │  dd_post_generator.py → DD HTML posts per buy signal        │
    │  portfolio_visual.py → equity curve dashboard                │
    └──────────────────────────────────────────────────────────────┘
```

---

## 2. PACKAGE-BY-PACKAGE AUDIT

### 2.1 scanner/ (11,073 lines, 8 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| scanner.py | 3,298 | Main weekly pipeline orchestrator | Large but functional |
| thematic_analyzer.py | 3,311 | Two-step theme ID + ticker-to-theme mapping | Complex, well-documented |
| sterling_indicators.py | 1,063 | V6 indicator calculations (HMA, RSI, MACD, UC) | Clean, backtest-matched |
| investment_gate.py | 1,005 | Regime-aware quality gate (Sonnet) | Good, 4-phase design |
| deep_dd.py | 934 | Opus deep analysis (1-3 stocks) | Good, extended thinking |
| daily_scanner.py | 791 | Daily BoS scanner (legacy indicators) | Clean, separate portfolio |
| due_diligence.py | 494 | Manual CLI DD tool (not in pipeline) | Standalone, works |
| legacy_indicators.py | 177 | Old Banker/HMA/BoS for daily scanner | Preserved correctly |

**Key Findings:**
- **scanner.py is 3,298 lines** — largest single file. `run_scan()` alone is ~1,400 lines with nested logic.
- **V6 Sterling Grid** is fully implemented with quality tiers (T1/T2/T3) and tiered profit lock.
- **Thematic Analyzer v3.0** (active change): Bottom-up micro-theme discovery + sector diversity requirement.
- **Investment Gate** now passes `gate_*` fields to Deep DD (active change in git diff).
- **Deep DD** thinking budget bumped 10K→32K (active change). Citation tag stripping added.

**Issues Found:**
1. scanner.py has generic `except` blocks in multiple places (swallows errors silently)
2. Daily scanner uses legacy indicators — functionally separate system from weekly
3. `due_diligence.py` is a standalone CLI tool, never called by the pipeline

---

### 2.2 twitter/ (10,441 lines, 16 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| tweet_generator.py | 2,231 | Weekly + daily tweet generation with 7-step validation | Core, complex |
| live_tweet_generator.py | 2,029 | Intraday live tweets (market hours) | Production, cost-controlled |
| signal_tracker.py | 1,143 | Win tracking, celebrations, milestones | Supporting |
| poster.py | 1,100 | 7-slot posting to X (3 accounts) | Production |
| chart_capture.py | 749 | TradingView chart screenshots (Playwright) | Fragile dependency |
| funnel_graphic.py | 670 | Scanner funnel visualization PNG | Supporting |
| chart_generator.py | 359 | chart-img API chart generation | Alternative to Playwright |
| health_check.py | 332 | System health monitoring | Manual utility |
| self_quote_tracker.py | 304 | Signal milestone quote tracking | Supporting |
| winner_showcase_generator.py | 270 | Winner receipt tweets | Supporting |
| models.py | 259 | Shared data classes (Tweet, ValidationResult, etc.) | Clean |
| cost_tracker.py | 195 | API cost tracking + daily kill switch ($1 limit) | Critical safety |
| verify_tweets.py | 177 | Post-generation QA | Manual utility |
| tradingview_login.py | 90 | Interactive TradingView login | One-time setup |

**Issues Found:**
1. `poster.py` `get_current_slot()` has hardcoded time boundaries, not config-driven
2. Live tweet system and batch system are separate codepaths — no automatic failover
3. `INTERNAL_TERM_PATTERNS` (26 regex patterns) duplicated between `models.py` and `config/banned_terms.py`

---

### 2.3 substack/ (9,895 lines, 11 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| content_generator.py | 1,656 | 4 adaptive Substack posts (Mon/Thu/Sat/Sun) | Complex, 7 prompt builders |
| notes_batch_generator.py | 1,344 | 21 notes/week (3/day), 7 note types | High duplication |
| html_templates.py | 1,182 | Reusable HTML template functions | Good shared resource |
| learning_content_library.py | 1,182 | 40+ educational topics | Static, never dynamically used |
| newsletter_compiler.py | 1,159 | Full HTML newsletter from scanner output | Production |
| notes_generator.py | 1,016 | Legacy Tuesday/Thursday notes | Superseded by batch |
| portfolio_visual.py | 819 | Equity curve SVG + dashboard HTML | Manual SVG coords |
| content_production_guide.py | 709 | Weekly content schedule for Claude.ai | Adaptive |
| dd_post_generator.py | 545 | DD HTML posts per buy signal (dark theme) | Good |
| market_analyzer.py | 282 | Market context via Claude | Simple, no retry |

**Issues Found:**
1. `notes_generator.py` is legacy/superseded — dead code (but still imported by batch generator)
2. `learning_content_library.py` is a static library never used in any pipeline
3. Newsletter compiler handles multiple DD field name formats — backward compat complexity
4. `market_analyzer.py` has no retry logic or cost tracking

---

### 2.4 portfolio/ (2,010 lines, 3 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| manager.py | 1,713 | Trade tracking, live pricing, equity model, Google Sheets export | Monolithic |
| backup_cleanup.py | 296 | Dedup backups (newest per calendar week) | Clean |

**Issues Found:**
1. `calculate_nav()` replays all trades chronologically each call — O(n) with no caching
2. Monolithic class mixes 4 concerns (trade management, pricing, equity tracking, export)
3. No locking/concurrency protection on portfolio.csv

---

### 2.5 config/ (2,547 lines, 5 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| settings.py | 1,363 | All constants, thresholds, models, helpers | Good but bloated |
| marketing_vocabulary.py | 520 | Legacy vocab validation (DEPRECATED) | Should be removed |
| output_paths.py | 333 | Multi-section output path registry | Clean |
| banned_terms.py | 311 | Single source of truth for banned content | Good |
| __init__.py | 20 | Re-exports via wildcard | Works |

**Issues Found:**
1. Banned terms triple-defined (3 files) — single-source violation
2. `marketing_vocabulary.py` deprecated but not removed
3. UTC slot times hardcoded for EST, not EDT-aware
4. `config/__init__.py` uses `from config.settings import *` — wildcard masks dependencies

---

### 2.6 utils/ (1,155 lines, 3 files)

| File | Lines | Purpose | Health |
|------|-------|---------|--------|
| notifications.py | 870 | Email + WhatsApp sell signal alerts | Good, independent channels |
| email_notifier.py | 284 | SMTP setup wizard + sender | Legacy, security concern |

**Issues Found:**
- `email_notifier.py` stores passwords in plaintext `email_config.json`
- No retry logic on notification failures

---

### 2.7 tests/ (7,404 lines, ~461 tests across 11 files)

| File | Tests | Coverage Area |
|------|-------|--------------|
| test_sterling_indicators.py | 63 | V6 indicators |
| test_live_tweet_system.py | ~40 | Live tweets, cost tracking |
| test_substack_content_v2.py | ~35 | Posts, notes, HTML generation |
| test_integration.py | 34 | Cross-module pipelines |
| test_tweet_gen_audit_fixes.py | ~25 | Banned terms compliance |
| test_tweet_generator_v2.py | 24 | Tweet gen, validation |
| test_tweet_gen_integration.py | ~15 | Batch + live pipeline |
| test_safeguards.py | ~12 | Winner display, SPY outperformance |
| test_daily_scanner.py | 11 | Daily scanner logic |
| test_edge_cases.py | ~10 | Zero prices, missing data, NaN |

---

### 2.8 GitHub Actions Workflows (5 files)

| Workflow | Trigger | Purpose | Status |
|----------|---------|---------|--------|
| friday_scan.yml | Fri 21:30 UTC | Full weekly pipeline | Active |
| daily_scan.yml | Mon-Fri 21:35 + 20:35 UTC | Daily scanner + tweets | Active |
| daily_post.yml | Manual only | 7-slot batch posting | DISABLED (crons commented) |
| live_tweet.yml | Market hours | Live intraday tweets | Active |
| test_notifications.yml | Manual only | Test email/WhatsApp | Active |

---

## 3. ACTIVE GIT CHANGES (Uncommitted)

### Modified Files:
1. **scanner/deep_dd.py** — THINKING_BUDGET 10K→32K, citation tag stripping, gate context passthrough fix
2. **scanner/investment_gate.py** — Citation tag stripping, `gate_*` field passthrough to Stock objects
3. **scanner/thematic_analyzer.py** — v3.0 upgrade: bottom-up micro-theme discovery, sector diversity requirement

### Untracked Files:
- `LIVE_TWEET_SYSTEM_AUDIT.md`
- `substack/output/current/content_production_guide.md`
- `substack/output/current/substack_notes/` — 10 note files + manifest
- `substack/output/current/substack_posts/`
- `scanner/output/archive/2026-W08/`

---

## 4. CROSS-CUTTING ISSUES

### HIGH SEVERITY

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | Banned terms defined in 3 places | settings.py, banned_terms.py, marketing_vocabulary.py | Terms drift out of sync |
| 2 | Email password stored in plaintext | utils/email_notifier.py → email_config.json | Security vulnerability |
| 3 | UTC slot times hardcoded for EST | config/settings.py SLOT_TIMES_UTC | Wrong times during EDT |
| 4 | No pinned dependency versions | requirements.txt | Builds not reproducible |
| 5 | Playwright chart capture fragile | chart_capture.py, dd_post_generator.py, portfolio_visual.py | Cookie expiry → silent failure |

### MEDIUM SEVERITY

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 6 | scanner.py is 3,298 lines | scanner/scanner.py | Hard to navigate, review, test |
| 7 | Double validation (tweet gen + poster) | tweet_generator.py, poster.py | Duplicated logic |
| 8 | INTERNAL_TERM_PATTERNS duplicated | models.py vs banned_terms.py | DRY violation |
| 9 | No end-to-end integration test | tests/ | Can't verify full pipeline |
| 10 | PortfolioManager monolithic (1,713 LOC) | portfolio/manager.py | Mixes 4 concerns |
| 11 | 14 nearly-identical prompt builders | content_generator.py + notes_batch_generator.py | High maintenance |
| 12 | NAV calculation O(n) with no cache | portfolio/manager.py | Degrades over time |
| 13 | No retry logic on notifications | utils/notifications.py | Silent failure |
| 14 | marketing_vocabulary.py deprecated but present | config/marketing_vocabulary.py | Confusion, 3rd banned terms copy |

### LOW SEVERITY

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 15 | daily_post.yml crons commented, not removed | .github/workflows/ | Accidental re-enable risk |
| 16 | learning_content_library.py never used | substack/ | 1,182 lines dead code |
| 17 | notes_generator.py superseded | substack/ | Legacy, replaced by batch |
| 18 | openai in requirements.txt unused | requirements.txt | Dead dependency |
| 19 | Generic except blocks in scanner.py | scanner/scanner.py | Swallows errors silently |
| 20 | Unused path constants | config/output_paths.py | PORTFOLIO_BACKUP_DIR never referenced |
| 21 | Standalone utilities not in pipeline | verify_tweets.py, health_check.py | Could confuse developers |
| 22 | No concurrency protection on CSV | portfolio/manager.py | Corrupt if dual write |

---

## 5. DATA FLOW VALIDATION

### Weekly Pipeline Data Flow (Verified)
```
complete_tickers.txt (1,800 tickers)
    → yfinance download (1yr daily OHLCV)
    → sterling_indicators.py (V6: HMA pivot + UC + MACD + price cap)
    → thematic_analyzer.py (Sonnet: 5 themes + bottom-up ticker fit)
    → investment_gate.py (Sonnet: 4-phase, STRONG_BUY/SPEC_BUY/NO_GO)
    → deep_dd.py (Opus: newsletter content + final veto, 1-3 stocks)
    → portfolio/manager.py (add trades, check exits, update prices)
    → signals.json + report.txt + newsletter_briefing.md
    → tweet_generator.py → content_queue.json (3 accounts)
    → newsletter_compiler.py → newsletter.html
    → poster.py → X/Twitter (7 slots/day)
```

### Key Integration Points (Verified)
- Investment Gate now passes `gate_*` fields to Stock objects (new in active changes)
- Deep DD reads `gate_conviction`, `gate_catalyst`, `gate_bear_case`, `gate_math` (new fix)
- Citation tags from web search responses are now stripped before JSON parsing (new fix)
- Portfolio updates happen AFTER Deep DD (only DD-PASS stocks get added)
- signals.json maps `"banker": uc_value` for backward compat with content systems

---

## 6. COST STRUCTURE (Verified)

| Component | Model | Cost per Call | Typical Weekly |
|-----------|-------|---------------|----------------|
| Thematic Analyzer | Sonnet 4 | $0.15-0.50 | $0.25 |
| Investment Gate | Sonnet 4 | $0.15-0.25/stock | $1.50-2.50 |
| Deep DD | Opus 4 + thinking | $1-2/stock | $2-5 |
| Tweet Generation | Sonnet 4 | $0.10-0.30 | $0.30 |
| Newsletter Compilation | Sonnet 4 | $0.10-0.20 | $0.15 |
| Live Tweets | Sonnet 4 | $0.05-0.10/tweet | $1/day |
| **Weekly Total** | | | **$4-9** |

---

## 7. SCHEDULE VERIFICATION

| Time (ET) | Day | What Runs | How |
|-----------|-----|-----------|-----|
| 16:30 Fri | Friday | Full weekly scan + content gen | GH Actions friday_scan.yml |
| 16:35 Mon-Fri | Weekdays | Daily scanner + notifications | GH Actions daily_scan.yml |
| Market hours | Weekdays | Live tweets | GH Actions live_tweet.yml |
| 07:30-18:30 ET | Daily | 7-slot tweet posting | poster.py via live system |
| Saturday AM | Manual | Newsletter publish to Substack | Human copies HTML |
| Daily | Manual | 1 Substack post + 3 notes | Human via Claude.ai |

---

## 8. RECOMMENDATIONS (Prioritized)

### Quick Wins (< 1 hour each)
1. Delete marketing_vocabulary.py — deprecated, creates confusion
2. Remove openai from requirements.txt — unused dependency
3. Pin dependency versions — `yfinance==0.2.28` not `>=0.2.28`
4. Delete or archive notes_generator.py — superseded by batch
5. Commit active changes — deep_dd, investment_gate, thematic_analyzer fixes are good

### Medium Effort (1-4 hours each)
6. Consolidate banned terms — single source in banned_terms.py, remove from settings.py
7. Extract INTERNAL_TERM_PATTERNS — single definition in banned_terms.py, import in models.py
8. Add EDT-aware scheduling — replace hardcoded SLOT_TIMES_UTC with timezone-aware calculation
9. Add config helper tests — normalize_ticker, contains_banned_term, get_celebration_key
10. Move email passwords to env vars only — remove plaintext JSON storage

### Larger Refactors (4+ hours)
11. Split scanner.py — extract reporting, portfolio integration, technical gate into sub-modules
12. Split PortfolioManager — separate pricing, equity tracking, export, CSV I/O
13. Consolidate prompt builders — template-driven approach for content_generator + notes_batch
14. Add end-to-end integration test — full scan → notify → tweet pipeline
15. Remove daily_post.yml or fully delete — commented crons are a risk

---

## 9. OVERALL ASSESSMENT

The codebase is a **production-grade, well-architected trading system** with:
- Solid multi-gate filtering pipeline (Technical → Thematic → Investment Gate → Deep DD)
- Comprehensive content system (tweets, newsletter, notes, DD posts)
- Good test coverage (~461 tests, 7,404 test lines)
- Well-documented CLAUDE.md (1,200+ lines)

**Primary concerns** are maintenance-related:
- Banned terms triple-definition creates drift risk
- Large files (scanner.py at 3.3K lines) need splitting
- Duplicated validation logic between tweet_generator and poster
- Playwright dependency is fragile for CI/CD

**Active changes in git** are all improvements:
- Thematic analyzer v3.0 (bottom-up discovery) is a significant upgrade
- Gate context passthrough (investment_gate → deep_dd) fixes lost context
- Citation tag stripping fixes web search JSON parsing
- Thinking budget increase (10K→32K) gives Deep DD more room

---

## 10. DEPENDENCY GRAPH

### 10.1 Layered Architecture Diagram

```
LAYER 0 — No Project Dependencies (leaf nodes)
├── config/output_paths.py          (stdlib only)
├── config/banned_terms.py          (stdlib only)
├── config/marketing_vocabulary.py  (stdlib only, DEPRECATED)
├── scanner/legacy_indicators.py    (imports config)
├── scanner/sterling_indicators.py  (self-contained constants)
├── scanner/thematic_analyzer.py    (zero project imports — receives args)
├── scanner/investment_gate.py      (zero project imports — receives args)
├── scanner/deep_dd.py              (zero project imports — receives args)
├── scanner/due_diligence.py        (zero project imports — standalone CLI)
├── substack/html_templates.py      (stdlib only)
├── substack/learning_content_library.py  (stdlib only)
├── twitter/models.py               (stdlib only)
├── utils/notifications.py          (no project imports)
└── utils/email_notifier.py         (no project imports)

LAYER 1 — Config Facade
├── config/settings.py              → imports config/output_paths.py
└── config/__init__.py              → imports config/settings.py (wildcard), config/banned_terms.py

LAYER 2 — Core Business Logic
├── portfolio/manager.py            → imports config, scanner/sterling_indicators.py
├── portfolio/backup_cleanup.py     → imports config
└── substack/market_analyzer.py     → imports config/output_paths.py

LAYER 3 — Substack Content (depends on portfolio + config)
├── substack/newsletter_compiler.py → imports config, config/output_paths, config/banned_terms, portfolio/manager
├── substack/content_generator.py   → imports config, config/banned_terms, config/marketing_vocabulary, config/output_paths, substack/newsletter_compiler (optional)
├── substack/notes_generator.py     → imports config, config/output_paths, config/banned_terms, config/marketing_vocabulary
├── substack/dd_post_generator.py   → imports config, config/marketing_vocabulary, config/banned_terms, config/output_paths
├── substack/portfolio_visual.py    → imports config/output_paths, config/settings, config/marketing_vocabulary, portfolio/manager
└── substack/content_production_guide.py → imports config, config/banned_terms, config/output_paths, substack/content_generator

LAYER 3 — Substack Content (continued)
└── substack/notes_batch_generator.py → imports config, config/banned_terms, config/marketing_vocabulary, substack/notes_generator, substack/learning_content_library

LAYER 3 — Twitter Content (depends on portfolio + config)
├── twitter/tweet_generator.py      → imports config, config/banned_terms, twitter/models
├── twitter/live_tweet_generator.py → imports twitter/models, config/banned_terms, twitter/live_context_gatherer, portfolio/manager (optional)
├── twitter/live_context_gatherer.py → imports config
├── twitter/poster.py               → imports config, config/output_paths
├── twitter/signal_tracker.py       → imports config, portfolio/manager
├── twitter/winner_showcase_generator.py → imports config, portfolio/manager (inline)
├── twitter/chart_capture.py        → no project imports (self-contained)
├── twitter/chart_generator.py      → imports config
├── twitter/funnel_graphic.py       → imports config
├── twitter/self_quote_tracker.py   → imports config
├── twitter/cost_tracker.py         → imports config
├── twitter/health_check.py         → imports config
└── twitter/verify_tweets.py        → imports config, config/output_paths

LAYER 4 — Pipeline Entry Points (depend on everything)
├── scanner/scanner.py              → imports config, config/output_paths, scanner/sterling_indicators, portfolio/manager, scanner/thematic_analyzer (deferred), scanner/investment_gate (deferred), scanner/deep_dd (deferred)
└── scanner/daily_scanner.py        → imports scanner/scanner (calculate_beta, load_tickers), scanner/legacy_indicators, config
```

### 10.2 Per-File Detail: scanner/

| File | Project Imports | Imported By | Reads | Writes | APIs |
|------|----------------|-------------|-------|--------|------|
| **scanner.py** | config, config.output_paths, sterling_indicators, portfolio.manager, thematic_analyzer (deferred), investment_gate (deferred), deep_dd (deferred) | daily_scanner | complete_tickers.txt, portfolio.csv | signals.json (×3 locations), analysis_log.csv, report.txt (×2), newsletter_briefing.md (×2) | yfinance, anthropic (via gates) |
| **thematic_analyzer.py** | None | scanner.py | themes_cache.json | themes_cache.json, logs/failed_response_*.txt, analysis_*.json | anthropic (Sonnet + web search), yfinance, smtplib |
| **investment_gate.py** | None | scanner.py | None | reports/gate_{ticker}_{ts}.md | anthropic (Sonnet + web search) |
| **deep_dd.py** | None | scanner.py | None | reports/deep_dd_{ticker}_{ts}.md | anthropic (Opus + extended thinking + web search) |
| **sterling_indicators.py** | None (self-contained constants) | scanner.py, portfolio/manager.py, tests | None | {ticker}_indicator_history.csv (CLI only) | yfinance (CLI only) |
| **daily_scanner.py** | scanner.scanner, legacy_indicators, config | None (standalone entry) | complete_tickers.txt, daily_portfolio.csv, portfolio.csv | daily_portfolio.csv, daily_signals.json, daily_portfolio_backups/ | yfinance |
| **legacy_indicators.py** | config (BANKER_CENTER, VWAP_PERIOD, HMA_PERIOD) | daily_scanner.py | None | None | None |
| **due_diligence.py** | None | None (standalone CLI) | scanner/output/analysis_log.csv (legacy path!) | reports/dd_{ticker}_{ts}.md | anthropic (Opus + web search) |

### 10.3 Per-File Detail: portfolio/

| File | Project Imports | Imported By | Reads | Writes | APIs |
|------|----------------|-------------|-------|--------|------|
| **manager.py** | config, scanner.sterling_indicators (check_profit_lock) | scanner.py, portfolio_visual, newsletter_compiler, notes_generator, signal_tracker, tweet_generator, live_tweet_generator, winner_showcase | portfolio.csv, equity_curve.csv, portfolio/output/portfolio.csv (migration) | portfolio.csv, portfolio_google_sheets.csv, equity_curve.csv, portfolio_backups/ | yfinance (SPY, QQQ, batch) |
| **backup_cleanup.py** | config | None (standalone CLI) | portfolio_backups/ (dir listing) | Deletes old backup files | None |

### 10.4 Per-File Detail: substack/

| File | Project Imports | Imported By | Reads | Writes | APIs |
|------|----------------|-------------|-------|--------|------|
| **newsletter_compiler.py** | config.output_paths, config.banned_terms, config.marketing_vocabulary (opt), portfolio.manager (opt) | content_generator (opt) | signals.json, portfolio.csv, newsletter_briefing.md, market_analysis.md, chart PNGs | newsletter.html (current + archive) | anthropic (opt) |
| **content_generator.py** | config, config.banned_terms, config.marketing_vocabulary, config.output_paths (opt), substack.newsletter_compiler (opt) | content_production_guide | signals.json, portfolio.csv, equity_curve.csv, market_analysis.md | substack_posts/*.html (current + archive) | anthropic |
| **content_production_guide.py** | config, config.banned_terms, config.output_paths (opt), substack.content_generator | None (standalone entry) | signals.json, portfolio.csv, equity_curve.csv | content_production_guide.md, content_schedule.json | None ($0 cost) |
| **notes_batch_generator.py** | config, config.banned_terms, config.marketing_vocabulary, substack.notes_generator, substack.learning_content_library | None (standalone entry) | signals.json, portfolio.csv | substack_notes/*_{1,2,3}_*.md/.html, notes_manifest.json | anthropic, yfinance |
| **notes_generator.py** | config, config.output_paths, config.banned_terms, config.marketing_vocabulary | notes_batch_generator | signals.json, portfolio.csv, market_analysis.md | tuesday_note.md, thursday_note.md | anthropic, yfinance |
| **dd_post_generator.py** | config, config.marketing_vocabulary, config.banned_terms, config.output_paths (opt) | None (standalone entry) | signals.json, chart PNGs | substack_posts/dd_TICKER.html (current + archive) | playwright (opt) |
| **market_analyzer.py** | config.output_paths | None (standalone entry) | None (uses web search) | market_analysis.md (scanner current + archive) | anthropic (Sonnet + web search) |
| **portfolio_visual.py** | config.output_paths, config.settings, config.marketing_vocabulary, portfolio.manager | None (standalone entry) | portfolio.csv, equity_curve.csv (via manager) | portfolio_visual.html, portfolio_dashboard.png | playwright (opt), yfinance (via manager) |
| **html_templates.py** | None | content_generator (opt) | None | None | None |
| **learning_content_library.py** | None | notes_batch_generator | None | None | None |

### 10.5 Per-File Detail: twitter/

| File | Project Imports | Imported By | Reads | Writes | APIs |
|------|----------------|-------------|-------|--------|------|
| **tweet_generator.py** | config, config.banned_terms, twitter.models | None (standalone entry) | signals.json, portfolio.csv, daily_signals.json, chart PNGs | content_queue.json (×3 accounts), daily_content_queue.json (×3), failed_tweets.json | anthropic |
| **live_tweet_generator.py** | twitter.models, config.banned_terms, twitter.live_context_gatherer, portfolio.manager (opt) | None (standalone entry) | live_context.json, portfolio.csv, signals.json, live_content_queue.json | live_content_queue.json, failed_tweets.json | anthropic |
| **live_context_gatherer.py** | config | live_tweet_generator | portfolio.csv, signals.json | live_context.json | xAI Grok API (requests) |
| **poster.py** | config, config.output_paths (opt) | None (standalone entry) | content_queue.json (×3), daily_content_queue.json (×3), live_content_queue.json, chart PNGs | Updates status in-place in queue JSONs | tweepy (Twitter API) |
| **signal_tracker.py** | config, portfolio.manager | scanner.py (save_results) | portfolio.csv, celebrations.json | celebrations.json | yfinance (SPY) |
| **models.py** | None | tweet_generator, live_tweet_generator | None | None | None |
| **chart_capture.py** | None (self-contained) | None (standalone entry) | signals.json (via CLI), portfolio.csv (via CLI) | charts/*.png, chart_manifest.json | playwright (TradingView) |
| **chart_generator.py** | config | None (standalone entry) | live_content_queue.json | charts/*.png, updates live_content_queue.json | chart-img.com (requests) |
| **funnel_graphic.py** | config | None (standalone entry) | signals.json | funnel_graphic.png, chart_manifest.json | PIL (local) |
| **self_quote_tracker.py** | config | None | tweet_tracking.json | tweet_tracking.json | None |
| **winner_showcase_generator.py** | config, portfolio.manager (inline) | None | portfolio.csv | stdout/JSON | None |
| **cost_tracker.py** | config | None | live_cost_log.json | live_cost_log.json | None |
| **health_check.py** | config | None | live_cost_log.json, portfolio.csv | None (diagnostic) | HTTP probes (xAI, chart-img, Twitter) |
| **verify_tweets.py** | config, config.output_paths | None | content_queue.json (×3) | None (diagnostic) | None |

### 10.6 Per-File Detail: config/ and utils/

| File | Project Imports | Imported By | Notes |
|------|----------------|-------------|-------|
| **config/output_paths.py** | None | config/settings.py, scanner.py (direct) | Leaf node. Creates dirs on demand. |
| **config/banned_terms.py** | None | config/__init__.py | Leaf node. Helper functions. |
| **config/marketing_vocabulary.py** | None | ~5 substack/twitter files | DEPRECATED. Redundant banned terms. |
| **config/settings.py** | config/output_paths | config/__init__.py | 1,363 lines of constants. |
| **config/__init__.py** | config.settings (wildcard), config.banned_terms | Everything via `from config import X` | Public facade. |
| **utils/notifications.py** | None | daily_scanner (called by GH Actions) | Reads email_config.json |
| **utils/email_notifier.py** | None | None (standalone setup wizard) | Writes email_config.json (plaintext passwords) |

### 10.7 Most-Imported Modules (Hub Dependencies)

| Module | Imported By (count) |
|--------|-------------------|
| `config` (via __init__.py) | ~30+ files |
| `portfolio/manager.py` | 8 files (scanner, portfolio_visual, newsletter_compiler, notes_generator, signal_tracker, tweet_generator, live_tweet_generator, winner_showcase) |
| `config/banned_terms.py` | 7 files |
| `config/output_paths.py` | 6 files (direct imports, plus via settings.py) |
| `config/marketing_vocabulary.py` | 5 files (DEPRECATED) |
| `twitter/models.py` | 2 files (tweet_generator, live_tweet_generator) |
| `substack/content_generator.py` | 1 file (content_production_guide) |
| `substack/notes_generator.py` | 1 file (notes_batch_generator) |

---

## 11. DATA FLOW PATHS A-E

### Path A: scanner.py → signals.json

**Source:** `scanner/scanner.py` lines 2648-2790, `save_results()` function.

**Top-level keys written:**

```json
{
  "timestamp": "2026-02-21 22:06:24",
  "timeframe": "WEEKLY",
  "entry_criteria": "Sterling Grid V6: ...",
  "exit_criteria": "ExD compound exit OR tiered profit lock",
  "stats": { /* 17 fields */ },
  "themes": [ /* ThematicAnalyzer output */ ],
  "pass_signals": [ /* PASS/TRADE only */ ],
  "consider_signals": [ /* CONSIDER only */ ],
  "buy_signals": [ /* ALL confirmed — legacy compat key */ ],
  "sell_signals": [ /* exit signals */ ],
  "assessed_signals": [ /* theme-confirmed but NOT pass/consider */ ],
  "historical_winners": [],
  "big_wins": [],
  "home_runs": []
}
```

**`stats` sub-fields (17):**
```
tickers_loaded, data_downloaded, price_under_cap,
hma_pivot_low, hma_slope_rising, rsi_above_50, macd_cross_up,
uc_rising, uc_rising_above, buy_signal,
tier_t1, tier_t2, tier_t3,
technical_signals, theme_confirmed, final_trade, final_consider,
beta_gte_1_5 (legacy alias), weekly_bos_up (legacy alias → buy_signal)
```

**Per buy_signal fields (52 fields via `_signal_dict()` at line 2648):**

| Category | Fields |
|----------|--------|
| Identity | `symbol`, `tier`, `quality_tier`, `price` |
| V6 Indicators | `uc`, `uc_rising`, `rsi14`, `macd_cross_up`, `hma_pivot_low`, `hma_pivot_high`, `hma_slope_rising`, `buy_signal`, `exd_signal` |
| Legacy Compat | `beta`, `banker` (= uc value), `return_20d`, `uc_rising_above` |
| Theme | `theme`, `theme_score`, `pure_play_score`, `theme_verdict`, `theme_classification` |
| Gate | `final_decision`, `conviction`, `gate_verdict`, `gate_conviction`, `gate_catalyst`, `gate_bear_case`, `gate_math`, `valuation_regime`, `sector_status`, `upside_potential`, `bullish_factors`, `risk_factors`, `reasoning` |
| Sizing | `position_size_pct`, `position_dollars`, `position_tier` |
| Deep DD | `dd_verdict`, `dd_conviction`, `dd_position_size`, `dd_key_catalyst`, `dd_fatal_flaw`, `dd_elevator_pitch`, `dd_why_now`, `dd_the_math`, `dd_bear_case`, `dd_risk_to_monitor`, `dd_action` |
| List-level | `action` (appended outside `_signal_dict()`) |

**Per sell_signal fields (7):**
```
symbol, price, reason, entry_price, highest_close, drawdown_pct, pnl_pct
```

**Per assessed_signal fields (7):**
```
symbol, price, theme, theme_score, theme_verdict, final_decision, tier
```

**Per theme fields (12 — from ThematicAnalyzer):**
```
name, classification, composite_score, catalyst_score, momentum_score,
crowding_score, runway_score, thesis_summary, key_catalysts,
primary_etfs, crowding_indicator, theme_type
```

---

### Path B: signals.json → content_production_guide.py

**Entry point:** `content_production_guide.py` calls `content_generator.build_content_context()`.

**Fields consumed from `buy_signals[]`:**
```
symbol, price, theme, conviction, dd_conviction,
dd_elevator_pitch, catalyst_summary(!), dd_why_now, dd_the_math,
gate_math, dd_bear_case, gate_bear_case, dd_risk_to_monitor,
dd_action, bullish_factors, risk_factors, dd_fatal_flaw, reasoning
```

**Fields consumed from `themes[]`:**
```
name, classification, composite_score, thesis_summary,
key_catalysts, catalyst_score, momentum_score, theme_type
```

**Fields consumed from `stats`:**
```
tickers_loaded, technical_signals (fallback: buy_signal), theme_confirmed
```

**Fields consumed from `assessed_signals[]`:**
```
symbol, final_decision, dd_fatal_flaw, reasoning
```

**CONFLICT:** Reads `catalyst_summary` — scanner writes `gate_catalyst`. See Section 13.

---

### Path C: signals.json → newsletter_compiler.py

**`load_dd_results()`** — reads `buy_signals[]`, filters: `final_decision` in (PASS, TRADE):

```
symbol, dd_verdict, dd_conviction, conviction (fallback),
dd_position_size, dd_elevator_pitch, dd_why_now, dd_the_math,
dd_bear_case, dd_risk_to_monitor, dd_action,
gate_math (fallback for dd_the_math), gate_bear_case (fallback for dd_bear_case),
dd_key_catalyst (legacy), dd_fatal_flaw (legacy),
bullish_factors, risk_factors
```

**`load_theme_details()`** — reads `themes[]`:

```
name, classification, composite_score,
catalyst_score, momentum_score, crowding_score,
runway_score, thesis_summary, key_catalysts
```

---

### Path D: signals.json → tweet system

**`tweet_generator.py` (`_build_content_data()`):**

| Top-level key | Fallback key |
|---------------|-------------|
| `pass_signals` | `buy_signals` |
| `consider_signals` | `caution_signals` (legacy) |
| `themes` | — |
| `stats` | — |
| `sell_signals` | — |
| `timestamp` | — |

Per buy_signal: `symbol, price, theme, catalyst_summary`
Per consider_signal: `symbol, price, theme, action`
Per sell_signal: `symbol`
Stats: `tickers_loaded, technical_signals (fallback: buy_signal), theme_confirmed, final_trade, final_consider`
Themes: `name, classification, composite_score`

**`live_tweet_generator.py`:**

| Top-level key | Fields accessed |
|---------------|----------------|
| `buy_signals` | `symbol, theme, catalyst_summary, bullish_factors` |
| `consider_signals` | `symbol` |
| `sell_signals` | `symbol` |
| `exit_signals` | `symbol` — **KEY NOT WRITTEN BY SCANNER** |
| `timestamp` | Freshness check (rejects if > 72h old) |
| `stats` | `tickers_loaded, final_trade, final_consider` |

**CONFLICTS:** Both read `catalyst_summary` (scanner writes `gate_catalyst`). live_tweet_generator reads `exit_signals` (scanner doesn't write this key). See Section 13.

---

### Path E: portfolio.csv → consumers

**Canonical CSV columns** (from `PortfolioManager.CSV_FIELDNAMES`):
```
ticker, status, entry_date, entry_price, exit_date, exit_price,
highest_close, theme, tier, signal_type, conviction, notes,
stop_pct, position_size_pct, position_dollars, sizing_gear
```

**Google Sheets export adds 7 calculated columns:**
```
current_price, stop_level, pnl_pct, pnl_usd, days_held, distance_to_stop, stop_alert
```

**Consumer field access:**

| Consumer | Fields Read |
|----------|-------------|
| `content_generator.py` (load_portfolio_winners) | `status`, `entry_price`, `highest_close`, `ticker`, `theme`, `entry_date` |
| `content_production_guide.py` (load_full_portfolio) | `status`, `entry_price`, `highest_close`, `ticker`, `entry_date`, `theme` |
| `newsletter_compiler.py` (load_portfolio_status) | `status` (filter: CLOSED/STOPPED), `entry_price`, `exit_price`, `ticker`, `theme`, `exit_date` |
| `tweet_generator.py` (_load_portfolio) | `ticker`, `status`, `entry_price`, `current_price` (coerced), `exit_price` (coerced), `highest_close` (coerced), `theme`, calculates `pnl_pct` |
| `signal_tracker.py` (load_portfolio) | `ticker`, `entry_price`, `status`, `exit_price`, `entry_date`, `exit_date`, `theme`, `conviction` |
| `live_tweet_generator.py` | `ticker`, `status`, `entry_price`, `highest_close`, `theme` |

**Note:** V6 columns (`stop_pct`, `position_size_pct`, `position_dollars`, `sizing_gear`) are written by portfolio/manager.py but NOT yet read by any content consumer. They are consumed only by the portfolio dashboard and visual generator.

---

## 12. FIELD COMPATIBILITY MATRIX

### 12.1 signals.json `buy_signals[]` fields vs consumers

Legend: **R** = reads directly, **F** = reads as fallback, **—** = does not read

| Field | content_gen | newsletter | tweet_gen | live_tweet | dd_post | notes_gen |
|-------|:-----------:|:----------:|:---------:|:----------:|:-------:|:---------:|
| `symbol` | R | R | R | R | R | R |
| `price` | R | — | R | — | R | R |
| `theme` | R | — | R | R | R | R |
| `final_decision` | R | R (filter) | — | — | R (filter) | — |
| `conviction` | R | F | — | — | F | — |
| `dd_conviction` | R | R | — | — | R | — |
| `dd_elevator_pitch` | R | R | — | — | R | — |
| `dd_why_now` | R | R | — | — | R | — |
| `dd_the_math` | R | R | — | — | R | — |
| `dd_bear_case` | R | R | — | — | R | — |
| `dd_risk_to_monitor` | R | R | — | — | R | — |
| `dd_action` | R | R | — | — | R | — |
| `gate_math` | R | F | — | — | — | — |
| `gate_bear_case` | R | F | — | — | — | — |
| `gate_catalyst` | — | — | — | — | — | — |
| `catalyst_summary` | R | — | R | R | — | — |
| `bullish_factors` | R | R | — | R | — | — |
| `risk_factors` | R | R | — | — | — | — |
| `dd_fatal_flaw` | R | R (legacy) | — | — | — | — |
| `dd_key_catalyst` | — | R (legacy) | — | — | — | — |
| `dd_position_size` | — | R | — | — | — | — |
| `dd_verdict` | — | R | — | — | — | — |
| `reasoning` | R | — | — | — | — | — |
| `theme_verdict` | — | — | — | — | R | — |
| `tier` | — | — | — | — | — | — |
| `quality_tier` | — | — | — | — | — | — |
| `uc` | — | — | — | — | — | — |
| `uc_rising` | — | — | — | — | — | — |
| `rsi14` | — | — | — | — | — | — |
| `macd_cross_up` | — | — | — | — | — | — |
| `hma_*` | — | — | — | — | — | — |
| `buy_signal` | — | — | — | — | — | — |
| `exd_signal` | — | — | — | — | — | — |
| `beta` | — | — | — | — | — | — |
| `banker` | — | — | — | — | — | — |
| `return_20d` | — | — | — | — | — | — |
| `position_*` | — | — | — | — | — | — |
| `action` | — | — | — | — | — | — |

### 12.2 signals.json `themes[]` fields vs consumers

| Field | content_gen | newsletter | tweet_gen | live_tweet | dd_post | notes_gen |
|-------|:-----------:|:----------:|:---------:|:----------:|:-------:|:---------:|
| `name` | R | R | R | — | R | R |
| `classification` | R | R | R | — | — | R |
| `composite_score` | R | R | R | — | — | R |
| `thesis_summary` | R | R | — | — | — | — |
| `key_catalysts` | R | R | — | — | — | — |
| `catalyst_score` | R | R | — | — | — | — |
| `momentum_score` | R | R | — | — | — | — |
| `crowding_score` | — | R | — | — | — | — |
| `runway_score` | — | R | — | — | — | — |
| `theme_type` | R | — | — | — | — | — |
| `primary_etfs` | — | — | — | — | — | — |
| `crowding_indicator` | — | — | — | — | — | — |

### 12.3 signals.json `stats` fields vs consumers

| Field | content_gen | tweet_gen | live_tweet |
|-------|:-----------:|:---------:|:----------:|
| `tickers_loaded` | R | R | R |
| `technical_signals` | R (fallback: `buy_signal`) | R (fallback: `buy_signal`) | — |
| `theme_confirmed` | R | R | — |
| `final_trade` | — | R | R |
| `final_consider` | — | R | R |
| `data_downloaded` | — | — | — |
| `price_under_cap` | — | — | — |
| `hma_*`, `rsi_*`, `uc_*`, `macd_*` | — | — | — |
| `tier_t1/t2/t3` | — | — | — |
| `beta_gte_1_5` (legacy) | — | — | — |
| `weekly_bos_up` (legacy) | — | — | — |

### 12.4 signals.json top-level keys vs consumers

| Key | content_gen | newsletter | tweet_gen | live_tweet | dd_post |
|-----|:-----------:|:----------:|:---------:|:----------:|:-------:|
| `buy_signals` | R | R | F (from `pass_signals`) | R | R |
| `pass_signals` | — | — | R | — | — |
| `consider_signals` | — | — | R | R | — |
| `sell_signals` | — | — | R | R | — |
| `assessed_signals` | R (fallback: `all_assessed`) | — | — | — | — |
| `exit_signals` | — | — | — | R (**NOT WRITTEN**) | — |
| `themes` | R | R | R | — | R |
| `stats` | R | — | R | R | — |
| `timestamp` | — | — | R | R (freshness) | — |
| `historical_winners` | — | — | — | — | — |
| `big_wins` | — | — | — | — | — |
| `home_runs` | — | — | — | — | — |

### 12.5 portfolio.csv columns vs consumers

| Column | content_gen | content_guide | newsletter | tweet_gen | signal_tracker | live_tweet |
|--------|:-----------:|:-------------:|:----------:|:---------:|:--------------:|:----------:|
| `ticker` | R | R | R | R | R | R |
| `status` | R (filter) | R (filter) | R (filter) | R | R | R (filter) |
| `entry_price` | R | R | R | R | R | R |
| `exit_price` | — | — | R | R (coerced) | R | — |
| `entry_date` | R | R | — | — | R | — |
| `exit_date` | — | — | R | — | R | — |
| `highest_close` | R | R | — | R (coerced) | — | R |
| `theme` | R | R | R | R | R | R |
| `conviction` | — | — | — | — | R | — |
| `tier` | — | — | — | — | — | — |
| `signal_type` | — | — | — | — | — | — |
| `notes` | — | — | — | — | — | — |
| `stop_pct` | — | — | — | — | — | — |
| `position_size_pct` | — | — | — | — | — | — |
| `position_dollars` | — | — | — | — | — | — |
| `sizing_gear` | — | — | — | — | — | — |

---

## 13. CONFLICTS FOUND + RECOMMENDED RESOLUTIONS

### Conflict 1: `catalyst_summary` vs `gate_catalyst` (CRITICAL)

**Problem:** Three consumers read `signal.get("catalyst_summary")`:
- `content_generator.py` (`build_content_context()`)
- `tweet_generator.py` (`_build_user_prompt()`)
- `live_tweet_generator.py`

But `scanner.py:_signal_dict()` (line 2680) writes the field as `gate_catalyst`, NOT `catalyst_summary`. The `catalyst_summary` key does not exist in signals.json output. These consumers silently get `None`.

**Resolution:** Add a legacy alias in `_signal_dict()`:
```python
"catalyst_summary": s.gate_catalyst,  # Alias for downstream compat
```
One line change in `scanner/scanner.py` at line 2680.

---

### Conflict 2: `exit_signals` key not written (MEDIUM)

**Problem:** `live_tweet_generator.py` reads `signals.get("exit_signals", [])` but `scanner.py:save_results()` never writes an `exit_signals` key. It writes `sell_signals` instead. The `.get()` default returns `[]` so no crash, but live tweets never see exit data.

**Resolution:** Either:
- (a) Add `"exit_signals": [same as sell_signals]` to `save_results()`, OR
- (b) Change `live_tweet_generator.py` to read `sell_signals` instead

Option (b) is cleaner — one consumer change vs adding a redundant key.

---

### Conflict 3: Banned terms triple-definition (HIGH)

**Problem:** Banned terms are defined in three separate files:
1. `config/settings.py` — 80+ terms in `BANNED_TERMS_IN_TWEETS`
2. `config/banned_terms.py` — 104 terms in `CRITICAL_BANNED` + `BANNED_PHRASES`
3. `config/marketing_vocabulary.py` — 80+ terms in its own `BANNED_TERMS` + `CRITICAL_BANNED`

Lists can drift out of sync. A term added to one file may be missed in others.

**Resolution:** Consolidate to single source of truth in `config/banned_terms.py`:
1. Remove banned terms from `config/settings.py` (move any unique terms to banned_terms.py)
2. Delete `config/marketing_vocabulary.py` entirely (deprecated)
3. Update 5 files that import from marketing_vocabulary.py to import from banned_terms.py

---

### Conflict 4: `INTERNAL_TERM_PATTERNS` duplicated (MEDIUM)

**Problem:** `twitter/models.py` defines 26 regex patterns in `INTERNAL_TERM_PATTERNS`. `config/banned_terms.py` defines a similar but potentially different set. Both are used for validation but may drift.

**Resolution:** Single definition in `config/banned_terms.py`, imported by `twitter/models.py`:
```python
# twitter/models.py
from config.banned_terms import INTERNAL_TERM_PATTERNS
```

---

### Conflict 5: `notes_generator.py` legacy but still imported (LOW)

**Problem:** `substack/notes_generator.py` is documented as "superseded by batch generator" but `notes_batch_generator.py` imports 4 functions from it: `NoteContext`, `build_note_context`, `sanitize_note`, `validate_note`. This creates a dependency on dead code.

**Resolution:** Either:
- (a) Inline the 4 used functions into `notes_batch_generator.py`, then archive `notes_generator.py`
- (b) Extract shared utilities to a `substack/note_utils.py` module

Option (a) is simpler if the functions are small.

---

### Conflict 6: `marketing_vocabulary.py` deprecated but imported by 5+ files (MEDIUM)

**Problem:** File has an explicit deprecation notice but is still imported by:
- `substack/newsletter_compiler.py` (validate_content)
- `substack/content_generator.py` (validate_content)
- `substack/notes_generator.py` (validate_content)
- `substack/dd_post_generator.py` (validate_content)
- `substack/portfolio_visual.py` (validate_content)

**Resolution:** Move `validate_content()` function to `config/banned_terms.py` (it already has `check_banned_phrases()`). Update all 5 callers to import from the new location. Then delete `marketing_vocabulary.py`.

---

### Conflict Summary

| # | Severity | Conflict | Fix Effort |
|---|----------|----------|------------|
| 1 | CRITICAL | `catalyst_summary` vs `gate_catalyst` | 1 line in scanner.py |
| 2 | MEDIUM | `exit_signals` key not written | 1 line change (consumer or producer) |
| 3 | HIGH | Banned terms in 3 files | ~2 hours (consolidate + update imports) |
| 4 | MEDIUM | INTERNAL_TERM_PATTERNS duplicated | ~30 min (move + import) |
| 5 | LOW | Legacy notes_generator still imported | ~1 hour (inline or extract) |
| 6 | MEDIUM | Deprecated marketing_vocabulary still imported | ~1 hour (move validate_content + delete) |

---

*End of Phase 0 Codebase Audit*
