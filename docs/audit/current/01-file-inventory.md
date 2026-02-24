# 01 - File Inventory

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Repository Statistics

| Metric | Count |
|--------|-------|
| Active Python files | 37 |
| Archive/legacy Python files | 7 |
| GitHub Actions workflows | 2 |
| Shell scripts | 2 |
| YAML persona files | 3 |
| JSON config/example files | 1 |
| Test files | 2 |
| Total active Python LOC | 27,494 |
| Total archive Python LOC | 3,946 |
| Total repository LOC (all source) | ~34,000 |

---

## 2. Complete File Tree

```
bos_momentum_scanner/
├── .github/
│   └── workflows/
│       ├── daily_post.yml              234 lines
│       └── friday_scan.yml             391 lines
│
├── archive/
│   └── legacy_code/
│       ├── README.md                    51 lines
│       ├── data_loader.py              857 lines
│       ├── data_models.py              610 lines
│       ├── due_diligence_prompts.py    445 lines
│       ├── llm_client.py              574 lines
│       ├── logger.py                   433 lines
│       ├── newsletter_prompts.py       340 lines
│       └── prompt_templates.py         687 lines
│
├── config/
│   ├── __init__.py                       7 lines
│   ├── marketing_vocabulary.py         510 lines
│   ├── output_paths.py                 309 lines
│   └── settings.py                   1,157 lines
│
├── content/
│   ├── __init__.py                       1 line
│   ├── chart_capture.py                648 lines
│   ├── content_planner.py            1,440 lines
│   ├── editorial_board.py              266 lines
│   ├── funnel_graphic.py               671 lines
│   ├── grok_prompts_generator.py     1,612 lines
│   ├── market_analyzer.py              265 lines
│   ├── morning_briefing.py             203 lines
│   ├── newsletter_compiler.py          970 lines
│   ├── reaction_generator.py         2,451 lines
│   ├── substack_content_generator.py   528 lines
│   ├── substack_notes_generator.py     502 lines
│   ├── tweet_generator.py            2,205 lines
│   └── winner_showcase_generator.py    271 lines
│
├── core/
│   ├── __init__.py                       1 line
│   ├── dd_automator.py                 806 lines
│   ├── due_diligence.py                494 lines
│   ├── gatekeeper.py                   627 lines
│   ├── portfolio_manager.py          1,282 lines
│   ├── scanner.py                    3,283 lines
│   └── thematic_analyzer.py          2,516 lines
│
├── distribution/
│   ├── __init__.py                       1 line
│   ├── email_notifier.py               283 lines
│   ├── self_quote_tracker.py           305 lines
│   ├── signal_tracker.py             1,065 lines
│   └── twitter_poster.py               817 lines
│
├── docs/
│   ├── audit/current/                  (this audit)
│   ├── archive/                        (historical docs)
│   ├── planning/                       (specs, guides)
│   ├── CODEBASE_AUDIT_REPORT.md
│   ├── MASTER_TODO_v2.md
│   ├── README.md
│   ├── SETUP.md
│   ├── STERLING_SIGNALS_MASTER_PROMPTS.md
│   └── STYLE_GUIDE.md
│
├── examples/
│   └── tweet_examples.json             143 lines
│
├── personas/
│   ├── alex.yaml                       150 lines
│   ├── james.yaml                      165 lines
│   └── rozalia.yaml                    152 lines
│
├── tests/
│   ├── __init__.py                      13 lines
│   ├── test_edge_cases.py              277 lines
│   └── test_safeguards.py              259 lines
│
├── utils/
│   ├── __init__.py                       1 line
│   ├── backup_cleanup.py               245 lines
│   ├── run_full_pipeline.py            263 lines
│   ├── setup_scheduler.py              418 lines
│   ├── tradingview_login.py             90 lines
│   ├── verify_reaction_tweets.py       266 lines
│   └── verify_tweets.py                166 lines
│
├── CLAUDE.md                         (project instructions)
├── README.md
├── SYSTEM_OVERVIEW.md
├── TODO.md
├── TWEET_TEMPLATE_INTEGRATION_TODO.md
├── complete_tickers.txt                937 lines
├── requirements.txt                     10 lines
├── run_friday.sh                       394 lines
└── run_local_friday.sh                  65 lines
```

---

## 3. Per-File Detail

### 3.1 `config/` Package (1,983 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 7 | Re-exports `settings.py` via `from config.settings import *` | All settings constants |
| `settings.py` | 1,157 | Central configuration: thresholds, models, schedules, personas, marketing rules | `TRAILING_STOP_PCT`, `BETA_THRESHOLD`, `BANKER_TIER1/2/3`, `HMA_PERIOD`, `MODEL_SONNET`, `WEEKLY_SCHEDULE`, `ACCOUNTS`, `SLOTS`, etc. |
| `marketing_vocabulary.py` | 510 | Banned terms, approved language, signal branding, conviction mapping | `BANNED_TERMS`, `CRITICAL_BANNED`, `APPROVED_PHRASES`, `SIGNAL_BRANDING`, `CONVICTION_LANGUAGE` |
| `output_paths.py` | 309 | Centralized folder structure, weekly archiving | `get_week_identifier()`, `get_current_dir()`, `save_to_current_and_archive()` |

### 3.2 `core/` Package (9,009 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Empty | - |
| `scanner.py` | 3,283 | Main pipeline orchestrator: data download, indicators, 5-gate filtering, output generation | `Stock`, `ScanStats`, `SellSignal`, `run_scan()`, `main()` |
| `thematic_analyzer.py` | 2,516 | LLM-driven theme identification and ticker mapping (2-step) | `ThematicAnalyzer`, `Theme`, `TickerAnalysis`, `Config`, `CostTracker` |
| `portfolio_manager.py` | 1,282 | Trade tracking, P&L calculation, CSV persistence, Google Sheets export | `PortfolioManager`, `Trade`, `TradeStatus`, `load_portfolio()` |
| `dd_automator.py` | 806 | Automated due diligence for PASS signals | `DDResult`, `run_automated_dd()`, `apply_dd_to_stocks()` |
| `gatekeeper.py` | 627 | Final quality gate: catalyst check, red flags, sentiment | `GatekeeperResult`, `GateDecision`, `run_gatekeeper_batch()` |
| `due_diligence.py` | 494 | Manual deep DD with extended thinking (Opus) | `run_due_diligence()`, `run_dd()` (alias) |

### 3.3 `content/` Package (11,832 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Empty | - |
| `reaction_generator.py` | 2,451 | Primary tweet generation: 3 accounts x 35 tweets/week | `generate_weekly_content()`, `generate_weekly_content_v2()` |
| `tweet_generator.py` | 2,205 | Legacy tweet generator (fallback) | `generate_tweets()`, `main()` |
| `grok_prompts_generator.py` | 1,612 | 21 weekly Grok/X prompts for manual posting | `generate_grok_prompts()` |
| `content_planner.py` | 1,440 | Persona-based content planning | `ContentPlanner`, `create_editorial_plan()` |
| `newsletter_compiler.py` | 970 | Compile full newsletter: market analysis + briefing + DD -> HTML | `compile_newsletter()`, `main()` |
| `funnel_graphic.py` | 671 | Funnel visualization of scan pipeline stages | `generate_funnel_graphic()` |
| `chart_capture.py` | 648 | TradingView chart screenshots via Playwright | `capture_charts()`, `main()` |
| `substack_content_generator.py` | 528 | Mon/Thu/Sat/Sun Substack posts | `generate_substack_content()` |
| `substack_notes_generator.py` | 502 | Tuesday/Thursday mid-week Substack notes | `generate_substack_notes()` |
| `winner_showcase_generator.py` | 271 | Winner showcase with entry prices | `generate_winner_showcase()` |
| `editorial_board.py` | 266 | Editorial planning and assignment | `create_editorial_plan()`, `validate_editorial_plan()` |
| `market_analyzer.py` | 265 | Market context analysis via Claude + web search | `generate_market_analysis()` |
| `morning_briefing.py` | 203 | Briefing formatter for tweet generation input | `generate_morning_briefing()` |

### 3.4 `distribution/` Package (2,471 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Empty | - |
| `signal_tracker.py` | 1,065 | Win tracking, portfolio stats, safeguard functions | `get_open_positions()`, `should_post_beat_spy()`, `has_enough_wins()`, `filter_expired_watchlist_signals()` |
| `twitter_poster.py` | 817 | X/Twitter posting: 3-account, chart upload, banned term checking | `post_tweet()`, `post_for_slot()`, `main()` |
| `self_quote_tracker.py` | 305 | Track tweet IDs for milestone quote tweets (25%/50%/100%) | `register_signal_tweet()`, `get_unquoted_milestones()` |
| `email_notifier.py` | 283 | SMTP email notifications, multi-recipient | `send_email()`, `setup()` |

### 3.5 `utils/` Package (1,449 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Empty | - |
| `setup_scheduler.py` | 418 | macOS launchd scheduler for automated scans | `setup_scheduler()` |
| `verify_reaction_tweets.py` | 266 | Validate reaction_generator output quality | `verify_tweets()` |
| `run_full_pipeline.py` | 263 | Full pipeline runner (alternative to shell script) | `main()` |
| `backup_cleanup.py` | 245 | Portfolio backup rotation and cleanup | `cleanup_backups()` |
| `verify_tweets.py` | 166 | Validate tweet_generator output quality | `verify_tweets()` |
| `tradingview_login.py` | 90 | TradingView browser login helper | `login()` |

### 3.6 `tests/` Package (549 lines)

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 13 | Test package init with path setup | - |
| `test_edge_cases.py` | 277 | Edge case tests for portfolio, signals, content | Test functions |
| `test_safeguards.py` | 259 | Safeguard validation tests for tweet content | Test functions |

### 3.7 GitHub Actions Workflows (625 lines)

| File | Lines | Trigger | Purpose |
|------|-------|---------|---------|
| `friday_scan.yml` | 391 | `cron: '30 21 * * 5'` + manual | Full weekly scan pipeline |
| `daily_post.yml` | 234 | 5 cron triggers/day + manual | Post tweets for 3 accounts |

### 3.8 Shell Scripts (459 lines)

| File | Lines | Purpose |
|------|-------|---------|
| `run_friday.sh` | 394 | Local Friday pipeline orchestrator (6 steps + git) |
| `run_local_friday.sh` | 65 | Local chart capture only (TradingView) |

### 3.9 Data/Config Files (1,557 lines)

| File | Lines | Purpose |
|------|-------|---------|
| `complete_tickers.txt` | 937 | Ticker universe (~1,800 US stocks, some multi-line) |
| `requirements.txt` | 10 | Python dependencies |
| `personas/alex.yaml` | 150 | Alex persona: "The System Builder" (@SterlingSignals) |
| `personas/rozalia.yaml` | 152 | Rozalia persona: "The Mentor" (Account 2) |
| `personas/james.yaml` | 165 | James persona: "The Trader" (Account 3) |
| `examples/tweet_examples.json` | 143 | Curated example tweets for few-shot learning |

### 3.10 Archive/Legacy (3,997 lines)

| File | Lines | Status |
|------|-------|--------|
| `archive/legacy_code/data_loader.py` | 857 | Dead code - replaced by yfinance in scanner.py |
| `archive/legacy_code/data_models.py` | 610 | Dead code - replaced by dataclasses in scanner.py |
| `archive/legacy_code/due_diligence_prompts.py` | 445 | Dead code - replaced by core/due_diligence.py |
| `archive/legacy_code/llm_client.py` | 574 | Dead code - replaced by direct anthropic calls |
| `archive/legacy_code/logger.py` | 433 | Dead code - replaced by inline logging |
| `archive/legacy_code/newsletter_prompts.py` | 340 | Dead code - replaced by newsletter_compiler.py |
| `archive/legacy_code/prompt_templates.py` | 687 | Dead code - prompts now inline in each module |
| `archive/legacy_code/README.md` | 51 | Documents archive purpose |

**Note:** The archive also previously contained `bos_scanner_v1.py` through `bos_scanner_v6_gatekeeper.py` and `tweet_generator_v1.py` (referenced in the audit prompt) but these files no longer exist on the current branch. They were likely removed during the Phase 2 cleanup.

---

## 4. Dependency Graph (Import Relationships)

### 4.1 Core Package Dependencies

```
config/settings.py          ← imported by nearly every module
config/marketing_vocabulary.py ← content/*, distribution/twitter_poster.py
config/output_paths.py      ← core/scanner.py, core/portfolio_manager.py

core/scanner.py
  ├── imports core/thematic_analyzer.py (ThematicAnalyzer)
  ├── imports core/gatekeeper.py (run_gatekeeper_batch)
  ├── imports core/portfolio_manager.py (PortfolioManager, load_portfolio, etc.)
  ├── imports core/dd_automator.py (run_automated_dd, apply_dd_to_stocks)
  ├── imports distribution/signal_tracker.py (load_historical_signals, find_big_wins)
  ├── imports distribution/email_notifier.py (send_email)
  ├── imports config/settings.py (all thresholds)
  └── imports config/output_paths.py (archive paths)

core/thematic_analyzer.py
  ├── imports anthropic
  ├── imports yfinance
  └── self-contained (no internal imports except config)

core/gatekeeper.py
  ├── imports anthropic
  └── imports config/settings.py

core/portfolio_manager.py
  ├── imports yfinance
  └── imports config/settings.py, config/output_paths.py

core/dd_automator.py
  ├── imports anthropic
  ├── imports core/due_diligence.py
  └── imports config/settings.py

core/due_diligence.py
  ├── imports anthropic
  └── imports config/settings.py
```

### 4.2 Content Package Dependencies

```
content/reaction_generator.py
  ├── imports core/portfolio_manager.py (fetch_current_prices)
  ├── imports content/editorial_board.py (create_editorial_plan, validate_editorial_plan)
  ├── imports content/morning_briefing.py (generate_morning_briefing)
  ├── imports config/settings.py (ACCOUNTS, SLOTS, WEEKLY_SCHEDULE, etc.)
  └── imports config/marketing_vocabulary.py (banned terms)

content/tweet_generator.py
  ├── imports distribution/signal_tracker.py (filter_expired_watchlist_signals, etc.)
  ├── imports config/settings.py
  └── imports config/marketing_vocabulary.py

content/newsletter_compiler.py
  ├── imports anthropic
  ├── imports core/portfolio_manager.py
  └── imports config/settings.py

content/chart_capture.py
  ├── imports playwright
  └── imports config/settings.py (TRADES_DIR)

content/grok_prompts_generator.py
  ├── imports core/portfolio_manager.py
  └── imports config/settings.py

content/funnel_graphic.py
  ├── imports matplotlib/mplfinance
  └── imports config/settings.py
```

### 4.3 Distribution Package Dependencies

```
distribution/twitter_poster.py
  ├── imports tweepy
  ├── imports anthropic (for tweet repair)
  ├── imports config/settings.py (ACCOUNTS, SLOTS)
  ├── imports config/marketing_vocabulary.py (CRITICAL_BANNED, BANNED_TERMS)
  └── imports distribution/self_quote_tracker.py

distribution/signal_tracker.py
  ├── imports core/portfolio_manager.py (load_portfolio, fetch_current_prices)
  ├── imports config/settings.py
  └── self-contained for most functions

distribution/self_quote_tracker.py
  ├── imports config/settings.py (TRADES_DIR, CELEBRATION_THRESHOLDS)
  └── imports distribution/signal_tracker.py (get_open_positions)

distribution/email_notifier.py
  └── self-contained (uses email_config.json)
```

### 4.4 Circular Import Protections

All cross-package imports use `try/except ImportError` with fallback defaults:
- `core/scanner.py` lines 82-101: Wraps imports of portfolio_manager, output_paths, email_notifier
- `distribution/twitter_poster.py` lines 119-123: Wraps import of CRITICAL_BANNED
- `distribution/self_quote_tracker.py` lines 34-38: Wraps import of TRADES_DIR, CELEBRATION_THRESHOLDS
- `content/reaction_generator.py` lines 38-53: Wraps imports of dotenv, portfolio_manager, editorial_board

---

## 5. External Dependencies

### 5.1 requirements.txt

| Package | Version | Used By |
|---------|---------|---------|
| `yfinance>=0.2.28` | Stock data | scanner.py, portfolio_manager.py, thematic_analyzer.py |
| `pandas>=2.0.0` | Data manipulation | scanner.py, portfolio_manager.py, signal_tracker.py |
| `numpy>=1.24.0` | Numerical computation | scanner.py (beta, HMA, banker) |
| `anthropic>=0.39.0` | Claude API | thematic_analyzer, gatekeeper, dd_automator, due_diligence, newsletter_compiler, reaction_generator, twitter_poster |
| `tweepy>=4.14.0` | Twitter/X API | twitter_poster.py |
| `mplfinance>=0.12.10b0` | Chart generation | funnel_graphic.py |
| `playwright>=1.40.0` | Browser automation | chart_capture.py, tradingview_login.py |
| `python-dotenv>=1.0.0` | .env file loading | reaction_generator.py |
| `PyYAML>=6.0` | Persona files | reaction_generator.py |
| `Pillow>=10.0.0` | Image processing | funnel_graphic.py |

### 5.2 Standard Library Usage (Notable)

| Module | Used For |
|--------|----------|
| `smtplib` | Email sending (email_notifier.py, scanner.py) |
| `csv` | Portfolio CSV read/write |
| `json` | Signals, content queues, tracking files |
| `argparse` | CLI in scanner, portfolio_manager, twitter_poster, etc. |
| `logging` | thematic_analyzer.py (comprehensive logging) |
| `dataclasses` | Stock, Trade, Theme, ScanStats, etc. |
| `pathlib` | All file path operations |
| `tempfile` | Atomic writes in portfolio_manager |
| `re` | Tweet validation, banned term checking |

---

## 6. Runtime Data Files

### 6.1 Files Read at Runtime

| File | Read By | Purpose |
|------|---------|---------|
| `complete_tickers.txt` | scanner.py | Ticker universe |
| `portfolio/output/portfolio.csv` | portfolio_manager.py | Trade history |
| `scanner/output/signals.json` | reaction_generator, tweet_generator, chart_capture | Scan results |
| `twitter/output/content_queue.json` | twitter_poster.py, daily_post.yml | Tweet queue (main) |
| `twitter/output/content_queue_account2.json` | twitter_poster.py | Tweet queue (account 2) |
| `twitter/output/content_queue_account3.json` | twitter_poster.py | Tweet queue (account 3) |
| `twitter/output/tweet_tracking.json` | self_quote_tracker.py | Milestone tracking |
| `twitter/output/charts/chart_manifest.json` | reaction_generator.py | Chart paths |
| `scanner/output/current/market_analysis.md` | newsletter_compiler.py | Market context |
| `scanner/output/current/newsletter_briefing.md` | newsletter_compiler.py, grok_prompts_generator.py | Briefing data |
| `personas/*.yaml` | reaction_generator.py | Persona definitions |
| `examples/tweet_examples.json` | reaction_generator.py | Few-shot examples |
| `email_config.json` | email_notifier.py | SMTP credentials |
| `.env` | reaction_generator.py (via dotenv) | Environment vars |

### 6.2 Files Written at Runtime

| File | Written By | Purpose |
|------|-----------|---------|
| `portfolio/output/portfolio.csv` | portfolio_manager.py | Trade updates (atomic write) |
| `portfolio/output/portfolio_google_sheets.csv` | portfolio_manager.py | Export with calculated fields |
| `portfolio/output/portfolio_backups/*.csv` | portfolio_manager.py | Timestamped backups |
| `scanner/output/signals.json` | scanner.py | Scan results |
| `scanner/output/analysis_log.csv` | scanner.py | Historical scan log (appended) |
| `scanner/output/current/report.txt` | scanner.py | Human-readable summary |
| `scanner/output/current/newsletter_briefing.md` | scanner.py | Newsletter data |
| `scanner/output/current/market_analysis.md` | market_analyzer.py | Market context |
| `substack/output/current/newsletter.html` | newsletter_compiler.py | Compiled newsletter |
| `twitter/output/content_queue.json` | reaction_generator.py | Generated tweets (main) |
| `twitter/output/content_queue_account2.json` | reaction_generator.py | Generated tweets (account 2) |
| `twitter/output/content_queue_account3.json` | reaction_generator.py | Generated tweets (account 3) |
| `twitter/output/generation_report.json` | reaction_generator.py | Generation statistics |
| `twitter/output/tweet_tracking.json` | twitter_poster.py, self_quote_tracker.py | Tweet IDs for quoting |
| `twitter/output/charts/*.png` | chart_capture.py | TradingView screenshots |
| `twitter/output/charts/chart_manifest.json` | chart_capture.py | Chart path index |
| `twitter/output/charts/*.png` | funnel_graphic.py | Pipeline funnel image |
| `scanner/output/current/` | scanner.py, various | Current week outputs |
| `scanner/output/archive/YYYY-WXX/*` | scanner.py, various | Weekly archives |
| `twitter/output/grok_prompts/*.md` | scanner.py | Grok/X prompt files |
| `logs/*.log` | thematic_analyzer.py | Debug logs |

---

## 7. Environment Variables

| Variable | Required | Used By | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Yes (for LLM) | scanner, thematic_analyzer, gatekeeper, dd_automator, due_diligence, newsletter_compiler, reaction_generator, twitter_poster | Claude API auth |
| `X_API_KEY` | Yes (for tweets) | daily_post.yml -> twitter_poster | Twitter main account |
| `X_API_SECRET` | Yes (for tweets) | daily_post.yml -> twitter_poster | Twitter main account |
| `X_ACCESS_TOKEN` | Yes (for tweets) | daily_post.yml -> twitter_poster | Twitter main account |
| `X_ACCESS_SECRET` | Yes (for tweets) | daily_post.yml -> twitter_poster | Twitter main account |
| `X2_API_KEY` / `X2_*` | For account 2 | daily_post.yml -> twitter_poster | Twitter account 2 |
| `X3_API_KEY` / `X3_*` | For account 3 | daily_post.yml -> twitter_poster | Twitter account 3 |
| `SMTP_SERVER` | Optional | thematic_analyzer, email_notifier | Email server |
| `SMTP_PORT` | Optional | thematic_analyzer, email_notifier | Email port |
| `EMAIL_SENDER` | Optional | email_notifier, friday_scan.yml | Sender address |
| `EMAIL_PASSWORD` | Optional | email_notifier, friday_scan.yml | SMTP password |
| `EMAIL_RECIPIENTS` | Optional | friday_scan.yml | Failure notifications |
| `TRADINGVIEW_COOKIES` | Optional | friday_scan.yml | Chart capture auth |

---

*End of Document 1*
