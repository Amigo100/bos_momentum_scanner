# CODEBASE AUDIT REPORT
# Sterling Signals / BoS Momentum Scanner

**Generated:** 2026-01-27
**Auditor:** Claude Code (Comprehensive Analysis)
**Mode:** Extended Thinking Analysis

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Python Files** | 34 |
| **Total Python Lines** | ~26,794 |
| **Documentation Files** | 33 |
| **GitHub Workflows** | 2 |
| **Data Directories** | 7 |
| **Security Issues** | 1 CRITICAL |
| **Orphaned Files** | 9 (review for removal) |

### Critical Finding

**SECURITY ISSUE:** `.env` file containing API keys is tracked by git, despite being in `.gitignore`. This means secrets may have been pushed to the remote repository.

---

## Section 1: Complete File Inventory

### Root Directory

```
/
├── .env                          [CONFIG] SECURITY ISSUE - tracked in git!
├── .env.example                  [CONFIG] Template (safe to commit)
├── .gitignore                    [CONFIG] Git ignore rules
├── .tradingview_cookies.json     [DATA] TradingView session (gitignored)
├── CLAUDE.md                     [DOCS] AI assistant context (59KB)
├── MASTER_TODO_v2.md             [DOCS] Active task list (62KB)
├── README.md                     [DOCS] Project overview
├── SETUP.md                      [DOCS] Setup instructions
├── SYSTEM_OVERVIEW.md            [DOCS] Marketing & architecture
├── complete_tickers.txt          [DATA] Stock universe (937 tickers)
├── requirements.txt              [CONFIG] Python dependencies
├── run_friday.sh                 [SCRIPT] Local pipeline orchestrator
└── run_local_friday.sh           [SCRIPT] Local chart capture
```

### Python Files (34 total)

#### Core Pipeline (5 files - CRITICAL)

| File | Lines | Purpose | Called By |
|------|-------|---------|-----------|
| `scanner.py` | 3,363 | Main scanning engine | friday_scan.yml, run_friday.sh |
| `thematic_analyzer.py` | 2,516 | LLM theme discovery | scanner.py |
| `gatekeeper.py` | 627 | LLM final quality gate | scanner.py |
| `portfolio_manager.py` | 980 | Trade tracking, P&L | scanner.py, signal_tracker.py |
| `dd_automator.py` | 806 | Automated due diligence | scanner.py (optional) |

#### Content Generation (7 files)

| File | Lines | Purpose | Called By |
|------|-------|---------|-----------|
| `tweet_generator.py` | 2,915 | Generate 35 weekly tweets | friday_scan.yml |
| `twitter_poster.py` | 676 | Post to X/Twitter | daily_post.yml |
| `newsletter_compiler.py` | 971 | Compile HTML newsletter | friday_scan.yml |
| `substack_notes_generator.py` | 687 | Tue/Thu Substack notes | friday_scan.yml |
| `substack_content_generator.py` | 535 | Mon/Thu/Sat/Sun posts | friday_scan.yml |
| `grok_prompts_generator.py` | 1,612 | Grok AI prompts | friday_scan.yml (fallback) |
| `market_analyzer.py` | 232 | Market context via Claude | friday_scan.yml |

#### Configuration & Infrastructure (8 files)

| File | Lines | Purpose | Imported By |
|------|-------|---------|-------------|
| `config.py` | 985 | Central configuration | 11+ files |
| `data_models.py` | 610 | Dataclass definitions | 0 (ORPHANED?) |
| `prompt_templates.py` | 687 | LLM prompt templates | 0 (ORPHANED?) |
| `output_paths.py` | 310 | Directory management | 5 files |
| `marketing_vocabulary.py` | 448 | Compliance rules | 6 files |
| `llm_client.py` | 574 | Anthropic API wrapper | 0 (ORPHANED?) |
| `logger.py` | 434 | Logging utilities | 0 (ORPHANED?) |
| `data_loader.py` | 857 | Data loading utilities | 0 (ORPHANED?) |

#### Tracking & Analysis (4 files)

| File | Lines | Purpose | Imported By |
|------|-------|---------|-------------|
| `signal_tracker.py` | 1,135 | Win tracking, safeguards | scanner.py, tweet_generator.py |
| `self_quote_tracker.py` | 256 | Quote tweet tracking | daily_post.yml (inline) |
| `winner_showcase_generator.py` | 233 | Winner content | 0 (ORPHANED) |
| `due_diligence.py` | 628 | Manual DD tool | 0 (CLI only) |

#### Charts & Graphics (2 files)

| File | Lines | Purpose | Called By |
|------|-------|---------|-----------|
| `chart_capture.py` | 643 | TradingView screenshots | run_local_friday.sh |
| `funnel_graphic.py` | 666 | Filter funnel charts | 0 (ORPHANED) |

#### Utilities (8 files)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `email_notifier.py` | 324 | SMTP notifications | friday_scan.yml (on failure) |
| `setup_scheduler.py` | 414 | macOS launchd setup | CLI only |
| `tradingview_login.py` | 89 | TradingView auth | CLI only |
| `backup_cleanup.py` | 262 | Portfolio backup retention | CLI only |
| `run_full_pipeline.py` | 263 | Pipeline orchestration | CLI only |
| `generate_example_graphics.py` | 543 | Demo graphics | ORPHANED |
| `newsletter_prompts.py` | 228 | Newsletter prompts | ORPHANED |
| `due_diligence_prompts.py` | 421 | DD prompts | ORPHANED |

#### Tests (2 files)

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_safeguards.py` | ~300 | Safeguard unit tests |
| `tests/test_edge_cases.py` | ~300 | Edge case tests |

### Documentation Files (33 total)

#### Primary Documentation (5 files - ROOT)

| File | Size | Status | Last Modified |
|------|------|--------|---------------|
| `CLAUDE.md` | 59KB | CURRENT | 2026-01-27 |
| `MASTER_TODO_v2.md` | 62KB | CURRENT | 2026-01-27 |
| `README.md` | 269 lines | CURRENT | 2026-01-23 |
| `SYSTEM_OVERVIEW.md` | 655 lines | CURRENT | 2026-01-23 |
| `SETUP.md` | 358 lines | CURRENT | 2026-01-21 |

#### Technical Documentation (5 files - docs/)

| File | Status | Notes |
|------|--------|-------|
| `docs/STYLE_GUIDE.md` | CURRENT | Python coding standards |
| `docs/OPTIMISATION_PLAN.md` | CURRENT | Refactoring roadmap |
| `docs/MIGRATION_GUIDE.md` | CURRENT | src/common migration |
| `docs/PORTFOLIO_DASHBOARD_SPEC.md` | PLANNED | Not implemented |
| `docs/STERLING_SIGNALS_MASTER_PROMPTS.md` | OUTDATED | UK ISA references |

#### Audit Documentation (8 files - docs/audit/)

| File | Status | Notes |
|------|--------|-------|
| `docs/audit/AUDIT_REPORT.md` | CURRENT | Previous marketing audit |
| `docs/audit/01-scanner-logic.md` | CURRENT | Scanner audit |
| `docs/audit/02-signal-detection.md` | CURRENT | Signal detection audit |
| `docs/audit/03-portfolio-tracking.md` | CURRENT | Portfolio audit |
| `docs/audit/04-pnl-calculation.md` | CURRENT | P&L audit |
| `docs/audit/05-twitter-automation.md` | CURRENT | Twitter audit |
| `docs/audit/06-newsletter-generation.md` | CURRENT | Newsletter audit |
| `docs/audit/07-marketing-compliance.md` | CURRENT | Compliance audit |

#### Archived Documentation (13 files - docs/archive/)

All files are historical/completed - safe for reference only:
- `CLAUDE_CODE_IMPLEMENTATION.md` - Completed implementation
- `CLAUDE_CODE_REFERENCE.md` - Archived reference
- `CLAUDE_CODE_REVIEW.md` - Completed review
- `CLAUDE_CODE_VERIFICATION.md` - Completed verification
- `IMPLEMENTATION_PLAN_FINAL.md` - Completed plan
- `REVIEW_PROMPT.md` - Old review prompt
- `TODO.md` - Old todo list
- `TODO_VERIFICATION_FIXES.md` - Completed fixes
- `VERIFICATION_OUTPUTS.md` - Old verification
- `VERIFICATION_PROMPT.md` - Old prompt
- `sterling_signals_improvement_reference.md` - Archived reference
- `sterling_signals_todo_list.md` - Old todo
- `weekly_newsletter_workflow.md` - Superseded

### Data Directory Structure

```
trades/
├── current/                        # This week's outputs
│   ├── newsletter.html             # Ready for Substack
│   ├── newsletter_briefing.md      # Scanner briefing
│   ├── report.txt                  # Scan summary
│   ├── signals.json                # Full scan results
│   ├── substack_notes/             # Tue/Thu notes
│   └── tweets/                     # Generated tweets
│       └── content_queue.json      # Tweet queue
│
├── weeks/                          # ISO week archives
│   ├── 2026-W03/                   # Archived week
│   ├── 2026-W04/                   # Archived week
│   └── 2026-W05/                   # Current week
│
├── charts/                         # Chart images (~60 files)
│   ├── *.png                       # TradingView captures
│   ├── chart_manifest.json         # Chart metadata
│   └── examples/                   # Demo charts
│
├── grok_prompts/                   # Grok AI prompts
│   ├── latest_grok_prompts.md
│   └── {day}_prompts.md
│
├── portfolio_backups/              # Timestamped backups (~30 files)
│
├── tweets/                         # Tweet archives
│
├── substack_posts/                 # Substack content
│
├── portfolio.csv                   # SOURCE OF TRUTH
├── portfolio_google_sheets.csv     # Export with formulas
├── signals.json                    # Latest signals
├── content_queue.json              # Tweet queue
├── celebrations.json               # Milestone tracking
├── analysis_log.csv                # Historical data
├── market_analysis.md              # Market context
├── latest_newsletter.html          # Legacy symlink
├── latest_newsletter_briefing.md   # Legacy symlink
└── latest_report.txt               # Legacy symlink
```

---

## Section 2: Dependency Graph

### Workflow: friday_scan.yml

```
friday_scan.yml
│
├─► scanner.py
│   ├─► config.py
│   ├─► thematic_analyzer.py
│   ├─► gatekeeper.py
│   ├─► portfolio_manager.py
│   ├─► signal_tracker.py
│   ├─► output_paths.py
│   ├─► email_notifier.py
│   ├─► [reads] complete_tickers.txt
│   ├─► [reads] portfolio.csv
│   ├─► [writes] signals.json
│   ├─► [writes] portfolio.csv
│   └─► [writes] newsletter_briefing.md
│
├─► market_analyzer.py
│   ├─► config.py
│   └─► [writes] market_analysis.md
│
├─► newsletter_compiler.py
│   ├─► config.py
│   ├─► marketing_vocabulary.py
│   ├─► output_paths.py
│   ├─► [reads] signals.json
│   ├─► [reads] newsletter_briefing.md
│   └─► [writes] newsletter.html
│
├─► substack_content_generator.py
│   ├─► config.py
│   ├─► marketing_vocabulary.py
│   └─► [writes] trades/substack_posts/
│
├─► tweet_generator.py
│   ├─► config.py
│   ├─► marketing_vocabulary.py
│   ├─► signal_tracker.py
│   ├─► portfolio_manager.py
│   ├─► output_paths.py
│   ├─► [reads] signals.json
│   ├─► [reads] portfolio.csv
│   └─► [writes] content_queue.json
│
├─► grok_prompts_generator.py (fallback)
│   ├─► config.py
│   ├─► marketing_vocabulary.py
│   └─► [writes] grok_prompts/
│
├─► substack_notes_generator.py
│   ├─► config.py
│   └─► [writes] substack_notes/
│
└─► email_notifier.py (on failure)
    └─► SMTP
```

### Workflow: daily_post.yml

```
daily_post.yml
│
├─► twitter_poster.py
│   ├─► config.py
│   ├─► output_paths.py
│   ├─► [reads] content_queue.json
│   ├─► [reads] trades/charts/*.png
│   ├─► [writes] content_queue.json (updates posted status)
│   └─► X/Twitter API
│
└─► (inline Python) self_quote_tracker checks
    └─► signal_tracker.py
```

### Local Script: run_local_friday.sh

```
run_local_friday.sh
│
└─► chart_capture.py
    ├─► config.py
    ├─► playwright (browser automation)
    ├─► [reads] signals.json
    └─► [writes] trades/charts/*.png
```

---

## Section 3: Active vs Inactive Files

### ACTIVE - Used in Production

| File | Called By | Status |
|------|-----------|--------|
| `scanner.py` | friday_scan.yml | CRITICAL |
| `thematic_analyzer.py` | scanner.py | CRITICAL |
| `gatekeeper.py` | scanner.py | CRITICAL |
| `portfolio_manager.py` | scanner.py, signal_tracker.py | CRITICAL |
| `tweet_generator.py` | friday_scan.yml | CRITICAL |
| `twitter_poster.py` | daily_post.yml | CRITICAL |
| `newsletter_compiler.py` | friday_scan.yml | ACTIVE |
| `substack_notes_generator.py` | friday_scan.yml | ACTIVE |
| `substack_content_generator.py` | friday_scan.yml | ACTIVE |
| `grok_prompts_generator.py` | friday_scan.yml (fallback) | ACTIVE |
| `market_analyzer.py` | friday_scan.yml | ACTIVE |
| `email_notifier.py` | friday_scan.yml (on failure) | ACTIVE |
| `chart_capture.py` | run_local_friday.sh | ACTIVE (local) |
| `signal_tracker.py` | scanner.py, tweet_generator.py | ACTIVE |
| `config.py` | 11+ files | CORE |
| `marketing_vocabulary.py` | 6 files | CORE |
| `output_paths.py` | 5 files | CORE |

### CLI UTILITIES - Not in Workflows but Used Manually

| File | Purpose | Recommendation |
|------|---------|----------------|
| `portfolio_manager.py` | Manual trade management | KEEP |
| `backup_cleanup.py` | Cleanup old backups | KEEP |
| `setup_scheduler.py` | macOS launchd setup | KEEP |
| `tradingview_login.py` | TradingView auth | KEEP |
| `run_full_pipeline.py` | Local development | KEEP |
| `due_diligence.py` | Manual DD analysis | KEEP |
| `self_quote_tracker.py` | Quote tweet tracking | KEEP |

### ORPHANED - Review for Removal

| File | Lines | Last Used | Recommendation |
|------|-------|-----------|----------------|
| `data_models.py` | 610 | Never imported | ARCHIVE (may be useful reference) |
| `prompt_templates.py` | 687 | Never imported | ARCHIVE |
| `llm_client.py` | 574 | Never imported | ARCHIVE |
| `logger.py` | 434 | Never imported | ARCHIVE |
| `data_loader.py` | 857 | Never imported | ARCHIVE |
| `funnel_graphic.py` | 666 | Never imported | KEEP (standalone tool) |
| `generate_example_graphics.py` | 543 | Never called | DELETE |
| `newsletter_prompts.py` | 228 | Never called | ARCHIVE |
| `due_diligence_prompts.py` | 421 | Never called | ARCHIVE |
| `winner_showcase_generator.py` | 233 | Never imported | REVIEW |

---

## Section 4: Documentation Status

| Document | Status | Issues | Action |
|----------|--------|--------|--------|
| `CLAUDE.md` | CURRENT | References deleted files | UPDATE |
| `MASTER_TODO_v2.md` | CURRENT | Large (62KB) | KEEP |
| `README.md` | CURRENT | None | KEEP |
| `SYSTEM_OVERVIEW.md` | CURRENT | None | KEEP |
| `SETUP.md` | CURRENT | None | KEEP |
| `docs/STYLE_GUIDE.md` | CURRENT | None | KEEP |
| `docs/OPTIMISATION_PLAN.md` | CURRENT | None | KEEP |
| `docs/MIGRATION_GUIDE.md` | CURRENT | None | KEEP |
| `docs/PORTFOLIO_DASHBOARD_SPEC.md` | PLANNED | Not implemented | KEEP (future) |
| `docs/STERLING_SIGNALS_MASTER_PROMPTS.md` | OUTDATED | UK ISA references | UPDATE |
| `docs/audit/*.md` | CURRENT | 8 files | KEEP |
| `docs/archive/*.md` | ARCHIVED | 13 files | KEEP (historical) |

### CLAUDE.md Issues

References to non-existent files:
- `diagnose_bos.py` - Mentioned but doesn't exist
- `verify_bos.py` - Mentioned but doesn't exist
- `sheets_sync.py` - Future integration (doesn't exist)
- `substack_publisher.py` - Future integration (doesn't exist)

---

## Section 5: Duplicate/Redundant Files

### Definite Duplicates

| File A | File B | Similarity | Action |
|--------|--------|------------|--------|
| `trades/weeks/2026-W04/newsletter_briefing_old.md` | `newsletter_briefing.md` | Old version | DELETE |
| `trades/weeks/2026-W04/report_old.txt` | `report.txt` | Old version | DELETE |

### Similar Purpose Files (Not Duplicates)

| File A | File B | Relationship |
|--------|--------|--------------|
| `tweet_generator.py` | `grok_prompts_generator.py` | tweet_generator supersedes grok_prompts |
| `newsletter_compiler.py` | `newsletter_prompts.py` | compiler uses prompts internally |
| `substack_notes_generator.py` | `substack_content_generator.py` | Different content types |

### Legacy Symlinks in trades/

| File | Points To | Status |
|------|-----------|--------|
| `latest_newsletter.html` | `current/newsletter.html` | KEEP (backwards compat) |
| `latest_newsletter_briefing.md` | `current/newsletter_briefing.md` | KEEP |
| `latest_report.txt` | `current/report.txt` | KEEP |

---

## Section 6: Security Analysis

### CRITICAL: .env Tracked in Git

```
STATUS: .env IS TRACKED BY GIT
RISK: API keys may be in git history
```

**Immediate Action Required:**
```bash
# 1. Remove .env from git tracking (but keep local file)
git rm --cached .env

# 2. Commit the removal
git commit -m "Remove .env from tracking (security fix)"

# 3. CRITICAL: Consider rotating ALL API keys since they may be in history
#    - Anthropic API key
#    - X/Twitter API keys
#    - Any email credentials
```

### Other Security Items

| Item | Status | Notes |
|------|--------|-------|
| `.tradingview_cookies.json` | GITIGNORED | Safe |
| `.env.example` | TRACKED | Safe (no real secrets) |
| API keys in code | NOT FOUND | Uses environment variables |
| Hardcoded credentials | NOT FOUND | Good practice followed |

---

## Section 7: Proposed Cleanup Actions

### Phase 1: Critical Security Fix

```bash
# Remove .env from git tracking
git rm --cached .env
git commit -m "security: remove .env from git tracking"
git push

# IMPORTANT: Rotate all API keys in .env after this!
```

### Phase 2: Delete Definite Duplicates

```bash
# Old version files in archives
rm trades/weeks/2026-W04/newsletter_briefing_old.md
rm trades/weeks/2026-W04/report_old.txt
```

### Phase 3: Archive Orphaned Utility Files

```bash
# Create archive directory for orphaned code
mkdir -p archive/legacy_code

# Move orphaned files that may be useful for reference
mv data_models.py archive/legacy_code/
mv prompt_templates.py archive/legacy_code/
mv llm_client.py archive/legacy_code/
mv logger.py archive/legacy_code/
mv data_loader.py archive/legacy_code/
mv newsletter_prompts.py archive/legacy_code/
mv due_diligence_prompts.py archive/legacy_code/
```

### Phase 4: Delete Truly Unused Files

```bash
# Delete files with no current use
rm generate_example_graphics.py
```

### Phase 5: Update Documentation

1. Update `CLAUDE.md` to remove references to non-existent files
2. Update `docs/STERLING_SIGNALS_MASTER_PROMPTS.md` for US audience

---

## Section 8: File Relationship Summary

### What Creates What

| Generator | Creates |
|-----------|---------|
| `scanner.py` | signals.json, portfolio.csv, analysis_log.csv, newsletter_briefing.md |
| `tweet_generator.py` | content_queue.json, tweets_*.json |
| `newsletter_compiler.py` | newsletter.html |
| `twitter_poster.py` | Updates content_queue.json (posted status) |
| `chart_capture.py` | trades/charts/*.png, chart_manifest.json |
| `substack_notes_generator.py` | tuesday_note.md, thursday_note.md |
| `substack_content_generator.py` | trades/substack_posts/*.md |
| `grok_prompts_generator.py` | grok_prompts/*.md |
| `market_analyzer.py` | market_analysis.md |
| `portfolio_manager.py` | portfolio_backups/*.csv |
| `funnel_graphic.py` | funnel_*.png |

### What Reads What

| Consumer | Reads |
|----------|-------|
| `scanner.py` | complete_tickers.txt, portfolio.csv |
| `tweet_generator.py` | signals.json, portfolio.csv |
| `twitter_poster.py` | content_queue.json, trades/charts/*.png |
| `newsletter_compiler.py` | signals.json, market_analysis.md |
| `substack_notes_generator.py` | signals.json, portfolio.csv |
| `signal_tracker.py` | portfolio.csv, celebrations.json |
| `chart_capture.py` | signals.json |

---

## Section 9: Statistics Summary

| Category | Count |
|----------|-------|
| **Python Files (Active)** | 17 |
| **Python Files (CLI Utilities)** | 8 |
| **Python Files (Orphaned)** | 9 |
| **Total Python Lines** | 26,794 |
| **Documentation Files** | 33 |
| **Archived Docs** | 13 |
| **GitHub Workflows** | 2 |
| **Data Directories** | 7 |
| **Stock Universe** | 937 tickers |
| **Weekly Tweets** | 35 |
| **Daily Post Slots** | 5 |

---

## Section 10: Recommendations

### Immediate (This Session)

1. **CRITICAL:** Remove `.env` from git tracking and rotate API keys
2. Delete old version files (`*_old.md`, `*_old.txt`)
3. Update CLAUDE.md to remove references to non-existent files

### Short Term (1-2 Weeks)

1. Archive orphaned utility files (data_models.py, llm_client.py, etc.)
2. Delete `generate_example_graphics.py`
3. Update `docs/STERLING_SIGNALS_MASTER_PROMPTS.md` for US audience
4. Add `docs/archive/README.md` explaining archived status

### Medium Term (1 Month)

1. Consider consolidating `tweet_generator.py` and `grok_prompts_generator.py`
2. Implement dashboard from `PORTFOLIO_DASHBOARD_SPEC.md`
3. Add test coverage (currently ~0%)
4. Clean up `__pycache__/` directories from repo

---

## Appendix A: Complete Python Import Map

```
config.py
├── Imported by: backup_cleanup.py, data_loader.py, llm_client.py,
│                newsletter_compiler.py, scanner.py, self_quote_tracker.py,
│                signal_tracker.py, substack_content_generator.py,
│                tweet_generator.py, winner_showcase_generator.py

marketing_vocabulary.py
├── Imported by: grok_prompts_generator.py, newsletter_compiler.py,
│                substack_content_generator.py, substack_notes_generator.py,
│                tweet_generator.py

output_paths.py
├── Imported by: data_loader.py, newsletter_compiler.py, scanner.py,
│                tweet_generator.py

signal_tracker.py
├── Imported by: scanner.py, self_quote_tracker.py, tweet_generator.py

portfolio_manager.py
├── Imported by: scanner.py, signal_tracker.py, tweet_generator.py

thematic_analyzer.py
├── Imported by: scanner.py

gatekeeper.py
├── Imported by: scanner.py

email_notifier.py
├── Imported by: scanner.py
```

---

## Appendix B: Verification Commands

```bash
# Verify file counts
ls *.py | wc -l                           # Should be ~34

# Verify documentation
find . -name "*.md" -not -path "./.git/*" | wc -l  # Should be ~33

# Verify workflows
ls .github/workflows/*.yml                 # Should show 2 files

# Check git status for .env
git ls-files .env                          # Should be empty after fix

# Verify no secrets in code
grep -r "sk-ant-api" --include="*.py" .    # Should be empty
```

---

**Report Complete**

This audit identified 1 critical security issue (`.env` tracked in git), 9 potentially orphaned Python files, and 2 duplicate data files. All active production files are properly connected through the workflow dependency chain.
