# 08 - Issues and Observations

> **Sterling Signals / BoS Momentum Scanner**
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`
> Auditor: Automated codebase audit (Claude)

---

## 1. Overview

This document consolidates every bug, dead code path, inconsistency, security concern,
and architectural observation found across the entire codebase during the exhaustive audit.

**Summary statistics:**

| Severity | Count |
|----------|-------|
| Critical (would cause runtime failures) | 4 |
| High (correctness / data accuracy) | 5 |
| Medium (maintenance debt) | 12 |
| Low (style / documentation) | 5 |
| Security observations | 3 |
| Architectural observations | 7 |
| **Total issues** | **36** |
| Positive observations | 7 |

**Files with the most issues:**

| File | Issue count |
|------|-------------|
| `utils/run_full_pipeline.py` | 5 |
| `core/scanner.py` | 3 |
| `utils/verify_tweets.py` | 2 |
| `utils/verify_reaction_tweets.py` | 2 |
| `utils/setup_scheduler.py` | 3 |
| `distribution/twitter_poster.py` | 2 |
| `utils/backup_cleanup.py` | 2 |
| `tests/test_edge_cases.py` | 2 |

---

## 2. Critical Issues (Would Cause Failures)

These issues will cause runtime errors or incorrect behavior when the affected code path
is executed.

### CRIT-1: Stale scanner path in `run_full_pipeline.py`

- **File:** `/utils/run_full_pipeline.py` line 41
- **Severity:** Critical -- will fail on execution
- **Description:** References `BASE_DIR / "scanner.py"` (root-level) instead of
  `BASE_DIR / "core" / "scanner.py"` after the package reorganisation.

```python
# Line 41 -- BROKEN
cmd = [sys.executable, str(BASE_DIR / "scanner.py")]

# Should be:
cmd = [sys.executable, str(BASE_DIR / "core" / "scanner.py")]
```

The subprocess call will raise `FileNotFoundError` because `scanner.py` no longer exists
at the project root.

---

### CRIT-2: Stale DD path in `run_full_pipeline.py`

- **File:** `/utils/run_full_pipeline.py` line 86
- **Severity:** Critical -- will fail on subprocess fallback
- **Description:** The subprocess fallback path references `BASE_DIR / "due_diligence.py"`
  instead of `BASE_DIR / "core" / "due_diligence.py"`.

```python
# Line 86 -- BROKEN
cmd = [sys.executable, str(BASE_DIR / "due_diligence.py"), ticker]

# Should be:
cmd = [sys.executable, str(BASE_DIR / "core" / "due_diligence.py"), ticker]
```

This is the fallback path when the direct import on line 72 fails. Both the import path
and the subprocess path need updating.

---

### CRIT-3: Wrong data directory in `run_full_pipeline.py`

- **File:** `/utils/run_full_pipeline.py` line 60
- **Severity:** Critical -- reads from nonexistent path
- **Description:** Reads from `data/signals.json` but the scanner outputs to
  `trades/signals.json`. The `data/` directory does not exist in the current project
  structure.

```python
# Line 60 -- BROKEN
signals_file = BASE_DIR / "data" / "signals.json"

# Should be:
signals_file = BASE_DIR / "trades" / "signals.json"
```

The function silently returns `{}` when the file is not found, so downstream DD steps
receive no candidates and do nothing.

---

### CRIT-4: Stale import of archived module in `scanner.py`

- **File:** `/core/scanner.py` line 3194
- **Severity:** Critical (degraded) -- silent failure due to try/except
- **Description:** Imports from `due_diligence_prompts` which was moved to
  `archive/legacy_code/due_diligence_prompts.py`. The import is wrapped in try/except
  so it silently fails rather than crashing.

```python
# Line 3194
from due_diligence_prompts import print_dd_prompts_for_stocks
```

The functionality was merged into `core/dd_automator.py`. The DD prompt feature silently
does not run. Either update the import to the new location or remove it if the feature
is superseded by `dd_automator`.

---

## 3. High-Priority Issues (Correctness Concerns)

These issues affect data accuracy, consistency between components, or could produce
incorrect output.

### HIGH-1: Content queue path inconsistency across verification scripts

- **Files:**
  - `/utils/verify_tweets.py` lines 10-12 -- reads from `trades/content_queue*.json`
  - `/utils/verify_reaction_tweets.py` lines 15-17 -- reads from `trades/tweets/content_queue*.json`
  - `/distribution/twitter_poster.py` line 59 -- reads from `trades/content_queue.json`
  - `/content/reaction_generator.py` -- writes to both `trades/` and `trades/current/tweets/`
- **Severity:** High -- verification scripts may check stale or wrong files
- **Description:** The three systems use different paths for the same content queue:

```python
# verify_tweets.py (lines 10-12)
QUEUES = [
    ("main", "content_queue.json"),        # reads trades/content_queue.json
    ("account2", "content_queue_account2.json"),
    ("account3", "content_queue_account3.json"),
]

# verify_reaction_tweets.py (lines 15-17)
QUEUE_FILES = {
    'main': 'trades/tweets/content_queue.json',          # reads trades/tweets/
    'account2': 'trades/tweets/content_queue_account2.json',
    'account3': 'trades/tweets/content_queue_account3.json',
}

# twitter_poster.py (line 59)
QUEUE_FILE = TRADES_DIR / "content_queue.json"           # reads trades/
```

If `reaction_generator.py` writes to `trades/tweets/` but `twitter_poster.py` reads from
`trades/`, posts could use stale data or fail to find the queue.

---

### HIGH-2: CRITICAL_BANNED list duplication with drift risk

- **Primary location:** `/config/marketing_vocabulary.py` -- canonical CRITICAL_BANNED list
- **Fallback location:** `/distribution/twitter_poster.py` lines 121-124 -- falls back to
  empty list `[]` if import fails
- **Severity:** High -- if the import fails, no banned terms are checked at the posting layer

```python
# twitter_poster.py lines 121-124
try:
    from config.marketing_vocabulary import CRITICAL_BANNED
except ImportError:
    CRITICAL_BANNED = []
```

The fallback is an empty list, meaning ALL banned terms pass through if the import fails.
This is the last line of defence before a tweet reaches the Twitter API. The previous
version had a hardcoded 17-term fallback list; the current version degrades to zero
protection on import failure.

---

### HIGH-3: GATEKEEPER verdict mapping confusion (CAUTION vs CONSIDER)

- **Files:**
  - `/core/gatekeeper.py` -- outputs `GateDecision.CAUTION`
  - `/core/scanner.py` line 878 -- maps CAUTION to `final_decision = "CONSIDER"`
  - Various display code -- shows "CAUTION" in some places, "CONSIDER" in others
- **Severity:** High -- confusing but documented as intentional
- **Description:** The gatekeeper produces three decisions: PASS, CAUTION, FAIL. The
  scanner remaps CAUTION to "CONSIDER" for portfolio tracking, but display code is
  inconsistent:

```python
# core/scanner.py line 877-879
elif r.decision == GateDecision.CAUTION:
    # Gatekeeper CAUTION -> scanner CONSIDER (gate verdict vs portfolio action)
    stock.final_decision = "CONSIDER"
```

The comment on line 878 documents this is intentional, but downstream code sometimes
displays "CAUTION" and sometimes "CONSIDER" for the same stocks. This should be
standardised to one term in all user-facing output.

---

### HIGH-4: Budget default uses GBP instead of USD

- **File:** `/utils/run_full_pipeline.py` line 68
- **Severity:** High -- wrong currency for US-audience product

```python
# Line 68 (and line 17 in docstring)
def run_due_diligence(ticker: str, budget: str = "£5,000", ...):
```

The default budget is British pounds ("GBP5,000"), which conflicts with the US-audience
focus of Sterling Signals. The DD prompts will reference pounds instead of dollars. Should
be `"$5,000"`.

---

### HIGH-5: `test_none_values` reveals unhandled None case

- **File:** `/tests/test_edge_cases.py` lines 161-174
- **Severity:** High -- production code may crash on None pnl_pct
- **Description:** The test catches `TypeError` from `filter_public_positions` when given
  `None` for `pnl_pct` and calls `pytest.skip()` rather than asserting correct behaviour.

```python
# Lines 161-174
def test_none_values(self):
    """None values should be handled gracefully."""
    positions = [
        {'ticker': 'NONE_PNL', 'pnl_pct': None, 'status': 'OPEN'},
        ...
    ]
    try:
        filtered = filter_public_positions(positions)
        assert any(p['ticker'] == 'WIN' for p in filtered)
    except TypeError:
        # If it crashes on None comparison, that's acceptable but noted
        pytest.skip("Implementation doesn't handle None pnl_pct")
```

This indicates `filter_public_positions` in `distribution/signal_tracker.py` does not
handle `None` values for `pnl_pct`. If portfolio data is incomplete (e.g., yfinance
returns no price), None could propagate and crash the tweet generation pipeline.

---

## 4. Medium-Priority Issues (Maintenance Debt)

### MED-1: Unused `REPORTS_DIR` in `run_full_pipeline.py`

- **File:** `/utils/run_full_pipeline.py` lines 34-35
- **Description:** `REPORTS_DIR` is created at import time but never referenced.

```python
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)   # Creates directory as side effect on import
```

Creates a `reports/` directory every time the module is imported, even if unused.

---

### MED-2: Unused import `getpass` in `setup_scheduler.py`

- **File:** `/utils/setup_scheduler.py` line 36

```python
import getpass   # imported but never used
```

---

### MED-3: Unused import `os` in `backup_cleanup.py`

- **File:** `/utils/backup_cleanup.py` line 19

```python
import os   # imported but never used (pathlib.Path used throughout)
```

---

### MED-4: Unused import `timedelta` in `backup_cleanup.py`

- **File:** `/utils/backup_cleanup.py` line 20

```python
from datetime import datetime, timedelta   # timedelta never used
```

---

### MED-5: Unused imports in `test_edge_cases.py`

- **File:** `/tests/test_edge_cases.py` lines 20-21

```python
from datetime import datetime, timedelta    # both imported, never used
from unittest.mock import patch, MagicMock  # both imported, never used
```

These were likely added for planned mock tests that were never written.

---

### MED-6: Unused imports in `test_safeguards.py`

- **File:** `/tests/test_safeguards.py` line 18

```python
from datetime import datetime, timedelta   # both imported, never used
```

---

### MED-7: `verify_tweets.py` runs on import (no `__main__` guard)

- **File:** `/utils/verify_tweets.py` lines 103-167
- **Description:** All verification logic executes at module level. Lines 103-167 contain
  the main execution block with no `if __name__ == "__main__":` guard. If any other module
  imports this file (e.g., for the `check_duplicate_tickers` function), all verification
  checks run immediately with side effects (file reads, print output).

---

### MED-8: `verify_reaction_tweets.py` runs on import (no `__main__` guard)

- **File:** `/utils/verify_reaction_tweets.py`
- **Description:** Same issue as MED-7. All 15 check blocks execute at module level. The
  global variables `passed`, `failed`, `warnings` (lines 45-47) accumulate counts as a
  side effect of import.

---

### MED-9: Bare `except:` clauses in `setup_scheduler.py`

- **File:** `/utils/setup_scheduler.py` lines 384 and 402

```python
# Line 384
except:
    ...

# Line 402
except:
    ...
```

Bare `except:` catches all exceptions including `KeyboardInterrupt` and `SystemExit`.
Should use `except Exception:` at minimum.

---

### MED-10: `run_full_pipeline.py` may be fully obsolete

- **File:** `/utils/run_full_pipeline.py` (264 lines)
- **Description:** Contains 3 critical broken paths (CRIT-1, CRIT-2, CRIT-3), wrong
  currency default (HIGH-4), and unused directory creation (MED-1). The functionality is
  now handled by:
  - `.github/workflows/friday_scan.yml` -- GitHub Actions workflow
  - `run_friday.sh` -- shell script for local execution

This file may be entirely dead code. If confirmed unused, it should be moved to
`archive/legacy_code/` or deleted.

---

### MED-11: Archive files still partially referenced

- **Directory:** `/archive/legacy_code/` (7 files, 3,946 lines total)
- **Files and line counts:**

| File | Lines | Superseded by |
|------|-------|---------------|
| `data_loader.py` | 857 | `core/portfolio_manager.py` |
| `data_models.py` | 610 | Inline dataclasses in `core/scanner.py` |
| `due_diligence_prompts.py` | 445 | `core/dd_automator.py` |
| `llm_client.py` | 574 | Direct `anthropic` calls |
| `logger.py` | 433 | `print()` statements |
| `newsletter_prompts.py` | 340 | `content/newsletter_compiler.py`, `content/market_analyzer.py` |
| `prompt_templates.py` | 687 | Inline prompts in each module |

All confirmed orphaned except `due_diligence_prompts.py` which is still imported by
`core/scanner.py` line 3194 (see CRIT-4).

---

### MED-12: Dual output pattern creates redundant file I/O

- **Description:** Many modules write output to both the new `trades/current/` structure
  and legacy root-level paths:

| New path | Legacy path |
|----------|-------------|
| `trades/current/newsletter.html` | `trades/latest_newsletter.html` |
| `trades/current/newsletter_briefing.md` | `trades/latest_newsletter_briefing.md` |
| `trades/current/signals.json` | `trades/signals.json` |

This doubles file I/O and creates a risk of inconsistency if one write succeeds and the
other fails. The legacy paths should eventually be deprecated.

---

## 5. Low-Priority Issues (Style and Documentation)

### LOW-1: No structured logging

- **Description:** The entire active codebase uses `print()` statements for output. The
  archived `logger.py` (433 lines) in `archive/legacy_code/` provided structured logging
  with colours, timing, and file output but was never adopted.
- **Impact:** Parsing scanner output programmatically is difficult. No log levels, no
  timestamps in output, no file logging.

---

### LOW-2: No type checking enforcement

- **Description:** The codebase uses type hints extensively (`List[str]`, `Dict`,
  `Optional[int]`, etc.) but has no `mypy` configuration, `pyproject.toml`, or CI step
  for type checking. Type hints serve as documentation only.

---

### LOW-3: No test coverage for LLM interactions

- **Files:** `/tests/test_edge_cases.py` (48 test methods), `/tests/test_safeguards.py`
- **Description:** Both test files only test pure functions (`filter_public_positions`,
  `validate_tweet_length`, etc.). No tests mock or verify:
  - LLM API calls
  - Prompt construction
  - Response parsing (JSON extraction from LLM output)
  - Error handling on malformed LLM responses

---

### LOW-4: Missing inline docstrings

- **Description:** Many public functions across the codebase lack docstrings, relying on
  function names and inline comments instead. Notable modules with sparse docstrings:
  - `distribution/signal_tracker.py`
  - `content/content_planner.py`
  - `content/grok_prompts_generator.py`

---

### LOW-5: CLAUDE.md may drift from code

- **Description:** `CLAUDE.md` is extremely comprehensive (900+ lines) and documents the
  system in detail, but there is no automated validation that it matches the actual code.
  Command examples, file paths, and data structures could become outdated after refactors.

---

## 6. Security Observations

### SEC-1: API key written to plaintext file

- **File:** `/utils/setup_scheduler.py` line 89
- **Severity:** Medium
- **Description:** Embeds `ANTHROPIC_API_KEY` in plaintext in the generated
  `run_scanner.sh` wrapper script.

```python
# Line 89
export ANTHROPIC_API_KEY="{api_key}"
```

The key value is read from the environment (line 60) and written directly into the shell
script file on disk. Anyone with read access to the generated script can see the key.

**Recommendation:** Use `os.environ` passthrough or a `.env` file reference instead of
embedding the literal key.

---

### SEC-2: TradingView cookies stored in project directory

- **File:** `/content/chart_capture.py` line 114
- **Severity:** Low (mitigated)
- **Description:** Saves TradingView authentication cookies to
`.tradingview_cookies.json` in the project root.

```python
# Line 114
str(BASE_DIR / ".tradingview_cookies.json")
```

**Mitigation:** This file IS listed in `.gitignore` (line 33), so it will not be committed
to the repository. However, it could be inadvertently shared if the project directory is
copied or archived.

---

### SEC-3: All Twitter credentials available to every workflow step

- **File:** `/.github/workflows/daily_post.yml` lines 31-47
- **Severity:** Low (standard GitHub Actions pattern)
- **Description:** Thirteen secrets (1 Anthropic + 12 Twitter across 3 accounts) are set
  as job-level environment variables, making them available to every step in the job.

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  X_API_KEY: ${{ secrets.X_API_KEY }}
  X_API_SECRET: ${{ secrets.X_API_SECRET }}
  X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
  X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
  X2_API_KEY: ${{ secrets.X2_API_KEY }}
  X2_API_SECRET: ${{ secrets.X2_API_SECRET }}
  X2_ACCESS_TOKEN: ${{ secrets.X2_ACCESS_TOKEN }}
  X2_ACCESS_SECRET: ${{ secrets.X2_ACCESS_SECRET }}
  X3_API_KEY: ${{ secrets.X3_API_KEY }}
  X3_API_SECRET: ${{ secrets.X3_API_SECRET }}
  X3_ACCESS_TOKEN: ${{ secrets.X3_ACCESS_TOKEN }}
  X3_ACCESS_SECRET: ${{ secrets.X3_ACCESS_SECRET }}
```

While GitHub Secrets are stored securely, best practice is to scope credentials to only
the steps that need them.

---

## 7. Architectural Observations

### 7.1 Large Monolithic Files

Eight files exceed 970 lines, totalling 15,542 lines:

| File | Lines | Concern |
|------|-------|---------|
| `core/scanner.py` | 3,283 | Main orchestrator: data download, indicators, filtering, LLM integration, output generation, portfolio update, DD prompts |
| `core/thematic_analyzer.py` | 2,516 | Theme analysis, web search, rate limiting, response parsing |
| `content/reaction_generator.py` | 2,451 | Persona-driven tweet generation, safeguards, queue management |
| `content/tweet_generator.py` | 2,205 | Legacy template-driven tweet generation |
| `content/grok_prompts_generator.py` | 1,612 | 14+ prompt creator functions, weekly scheduler |
| `content/content_planner.py` | 1,440 | ContentPlanner, PersonaGenerator, CrossAccountValidator |
| `distribution/signal_tracker.py` | 1,065 | Win tracking, position filtering, safeguard checks |
| `content/newsletter_compiler.py` | 970 | Compiler, HTML template, markdown parser |

`core/scanner.py` at 3,283 lines is the largest and does the most. It could be split into:
- Data download and indicator calculation
- Technical filtering
- Pipeline orchestration
- Output generation

---

### 7.2 Three Overlapping Tweet Generation Systems

The codebase has three systems that generate tweet content:

| System | File | Lines | Status |
|--------|------|-------|--------|
| Reaction Generator | `content/reaction_generator.py` | 2,451 | **Primary** -- persona-driven, used by `daily_post.yml` |
| Tweet Generator | `content/tweet_generator.py` | 2,205 | **Legacy** -- template-driven fallback |
| Content Planner | `content/content_planner.py` | 1,440 | **Unclear** -- most sophisticated architecture, but unclear if actively called |

Total: 6,096 lines for tweet generation alone.

`content_planner.py` defines `ContentPlanner`, `PersonaGenerator`, and
`CrossAccountValidator` classes that overlap significantly with
`reaction_generator.py`'s functionality. The relationship between these three systems
is not documented, and it is unclear whether `content_planner.py` is actively invoked
by any pipeline step.

---

### 7.3 Dual Output Pattern

Many modules write to both the new directory structure and legacy locations for backwards
compatibility:

```
trades/current/newsletter.html       + trades/latest_newsletter.html
trades/current/newsletter_briefing.md + trades/latest_newsletter_briefing.md
trades/current/signals.json           + trades/signals.json
trades/current/tweets/                + trades/content_queue.json
```

This pattern:
- Doubles file I/O on every pipeline run
- Creates risk of inconsistency if one write fails
- Makes it unclear which path is canonical for downstream consumers

A deprecation plan should remove legacy paths once all consumers are updated.

---

### 7.4 No Structured Logging

All output uses `print()`. There are no:
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Timestamps in output lines
- File-based logging for post-mortem analysis
- Machine-parseable output format

The archived `logger.py` (433 lines) provided structured logging with colours, timing,
and file output, but was never integrated into the active codebase.

---

### 7.5 Inline Prompts vs Centralised Prompt Management

The archived `prompt_templates.py` attempted to centralise all LLM prompts. The active
codebase co-locates prompts with their modules:

| Module | Prompt location |
|--------|-----------------|
| `core/gatekeeper.py` | Inline system prompt constant |
| `core/thematic_analyzer.py` | Inline system prompt constant |
| `content/newsletter_compiler.py` | `COMPILATION_SYSTEM` + `COMPILATION_PROMPT` |
| `content/reaction_generator.py` | Builds prompts dynamically per persona |
| `content/market_analyzer.py` | Inline analysis prompt |

This makes prompts harder to audit holistically (e.g., checking all prompts for banned
terms) but easier to maintain per-module.

---

### 7.6 No Retry Logic in Twitter Poster

`distribution/twitter_poster.py` has no retry mechanism for failed tweet posts. If a
network error or rate limit occurs, it logs the error and moves on. The
`daily_post.yml` workflow suppresses failures with `|| true`.

This means transient failures (network blip, Twitter rate limit) permanently skip that
tweet. A simple exponential backoff retry (similar to the gatekeeper's retry logic)
would improve reliability.

---

### 7.7 No Validation on yfinance Data

Multiple files fetch data from yfinance without checking for:
- NaN values in OHLCV columns
- Empty DataFrames (ticker delisted or data unavailable)
- Stale data (last trading day older than expected)
- Volume of zero (market holiday / pre-market)

If yfinance returns incomplete data, indicator calculations proceed with potentially
wrong values. The beta, banker, and HMA calculations all operate on raw yfinance output
without explicit NaN handling.

---

## 8. Positive Observations

### POS-1: Atomic writes for portfolio.csv

The `_save()` method in `core/portfolio_manager.py` uses `tempfile.NamedTemporaryFile` +
`os.replace()` for atomic writes, preventing data corruption on interrupted writes.
Backup rotation keeps 30 copies with timestamps.

---

### POS-2: Comprehensive marketing safeguards (defence in depth)

The system has multiple layers of protection against leaking internal terminology:

1. `config/marketing_vocabulary.py` -- canonical banned terms list
2. `content/reaction_generator.py` -- 14 distinct safeguard checks during generation
3. `distribution/twitter_poster.py` -- `validate_before_posting()` as last line of defence
4. `utils/verify_tweets.py` -- post-generation verification
5. `utils/verify_reaction_tweets.py` -- post-generation verification for reaction tweets

---

### POS-3: Backwards-compatible config package

`config/__init__.py` re-exports everything from `config/settings.py`, so existing code
using `from config import X` continues to work after the package reorganisation. This is
a clean migration pattern.

---

### POS-4: Graceful degradation throughout

Nearly every import uses `try/except` with sensible fallback defaults. Missing optional
modules (tweepy, playwright, dotenv) do not crash the system. This allows the scanner
to run in minimal environments without all optional dependencies.

---

### POS-5: Well-structured Phase 3 fixes

The completed Phase 3 bug fixes addressed several substantive issues:
- Duplicate constants extraction to `config/settings.py`
- `ScanStats` field renaming (`banker_gt_5` to `banker_tier1`, etc.)
- `passes_final_gate()` renamed to `is_confirmed()`
- `Trade.validate()` method added for portfolio data integrity
- Atomic writes with `tempfile` + `os.replace()`
- SPY matched-period benchmark comparison

---

### POS-6: Good test coverage for critical business rules

48 test methods across 2 test files covering the most critical safeguards:
- Loss suppression (negative P&L never appears in public content)
- Tweet character limit enforcement
- Age-based thresholds for position highlighting
- SPY comparison safeguards
- Edge cases (empty portfolios, zero PASS signals, all losers)

---

### POS-7: Git commit safety in GitHub Actions

Both workflows use `git pull --rebase` before push with fallback to merge if rebase fails.
The `daily_post.yml` handles race conditions between concurrent slot posts by retrying
the push after a fresh pull.

---

## 9. Recommended Priority Order

The following is the recommended order for addressing issues, balancing impact against
effort.

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 1 | **CRIT-1, CRIT-2, CRIT-3**: Fix or remove `run_full_pipeline.py` | Low | Eliminates 3 critical failures |
| 2 | **CRIT-4**: Remove stale `due_diligence_prompts` import in `scanner.py` line 3194 | Trivial | Restores DD prompt functionality or cleans dead path |
| 3 | **HIGH-1**: Standardise content queue paths across all scripts | Medium | Prevents verification scripts checking wrong files |
| 4 | **HIGH-2**: Add hardcoded fallback to `twitter_poster.py` CRITICAL_BANNED | Low | Ensures last-line-of-defence always has terms to check |
| 5 | **HIGH-5**: Handle `None` values in `filter_public_positions` | Low | Prevents crash on incomplete yfinance data |
| 6 | **HIGH-4**: Change default budget from GBP to USD | Trivial | Correct currency for US audience |
| 7 | **HIGH-3**: Standardise CAUTION/CONSIDER terminology | Medium | Reduces confusion in display output |
| 8 | **SEC-1**: Remove plaintext API key from generated shell script | Low | Security improvement |
| 9 | **MED-7, MED-8**: Add `__main__` guards to verification scripts | Low | Prevents side effects on import |
| 10 | **MED-9**: Replace bare `except:` with `except Exception:` | Trivial | Correctness |
| 11 | **MED-2 through MED-6**: Remove unused imports | Trivial | Clean code |
| 12 | **MED-10, MED-11**: Assess `run_full_pipeline.py` for deletion; clean archive references | Medium | Reduce dead code |
| 13 | **MED-12**: Deprecation plan for dual output paths | Medium | Reduce I/O and inconsistency risk |
| 14 | Architectural improvements (7.1-7.7) | High | Long-term maintainability |
| 15 | Low-priority items (LOW-1 through LOW-5) | Varies | Code quality |

---

## 10. Phase 3 Fix Status

The following issues were identified during the audit and have already been addressed by
the Phase 3 bug fixes on the `refactor/cleanup-reorg` branch.

| Issue | Phase 3 Status | Verification |
|-------|----------------|--------------|
| `ScanStats` field names (`banker_gt_5`, `banker_gt_3`, `banker_gt_2`) misleading | **FIXED** -- renamed to `banker_tier1`, `banker_tier2`, `banker_tier3` | Verified: `core/scanner.py` lines 221-223 use new names |
| `beta_gte_2_0` duplicate of `beta_gte_1_5` | **FIXED** -- removed | Verified: no occurrences of `beta_gte_2_0` in `core/scanner.py` |
| `passes_final_gate()` misleading name | **FIXED** -- renamed to `is_confirmed()` | Verified: `core/scanner.py` line 209 defines `is_confirmed()`, line 895 calls it |
| `Trade.validate()` missing | **FIXED** -- added as warnings-only validation | Verified: method exists in `core/portfolio_manager.py` |
| Non-atomic portfolio writes | **FIXED** -- uses `tempfile` + `os.replace()` | Verified in `core/portfolio_manager.py` `_save()` method |
| Duplicate constants (magic numbers) | **FIXED** -- extracted to `config/settings.py` | Verified: `BANKER_CENTER`, `HMA_PERIOD`, `VWAP_PERIOD` etc. in settings |

### Not Yet Addressed by Phase 3

The following issues documented in this report remain **open** and were not part of the
Phase 3 fix scope:

- All CRIT-1 through CRIT-4 (stale paths and imports)
- All HIGH-1 through HIGH-5 (consistency and correctness)
- All MED-1 through MED-12 (maintenance debt)
- All SEC-1 through SEC-3 (security observations)
- All LOW-1 through LOW-5 (style and documentation)
- All architectural observations (7.1 through 7.7)

---

*End of document. This is the final consolidated issues report for the BoS Momentum
Scanner codebase audit.*
