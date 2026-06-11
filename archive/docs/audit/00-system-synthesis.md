# Audit 00: System Synthesis

**Scope:** Cross-cutting synthesis of audits 01-07, consolidating architecture, issues, configuration, testing gaps, and documentation gaps across the entire Sterling Signals system.

**Source Audits:**
- `01-scanner-logic.md` — Scanner pipeline and technical gates
- `02-signal-detection.md` — Buy/sell signal generation
- `03-portfolio-tracking.md` — Portfolio CSV management
- `04-pnl-calculation.md` — P&L formulas and performance reporting
- `05-twitter-automation.md` — Tweet generation and posting
- `06-newsletter-generation.md` — Newsletter compilation and Substack
- `07-marketing-compliance.md` — Marketing rules, banned terms, compliance

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Critical Path Analysis](#2-critical-path-analysis)
3. [Consolidated Issues List](#3-consolidated-issues-list)
4. [Configuration Inventory](#4-configuration-inventory)
5. [Testing Gaps](#5-testing-gaps)
6. [Documentation Gaps](#6-documentation-gaps)

---

## 1. System Architecture Overview

### 1.1 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRIDAY SCAN PIPELINE                            │
│                   (.github/workflows/friday_scan.yml)                   │
│                                                                         │
│  ┌──────────┐   ┌─────────────┐   ┌────────────┐   ┌──────────────┐   │
│  │ scanner  │──▶│  thematic   │──▶│ gatekeeper │──▶│ dd_automator │   │
│  │   .py    │   │ analyzer.py │   │    .py     │   │     .py      │   │
│  │          │   │             │   │            │   │  (optional)  │   │
│  │ Steps    │   │ Claude API  │   │ Claude API │   │ Claude API   │   │
│  │ 1-4:     │   │ + optional  │   │ + web      │   │ Opus for     │   │
│  │ yfinance │   │ web search  │   │ search     │   │ full DD      │   │
│  │ download,│   │             │   │            │   │              │   │
│  │ beta,    │   │ Theme       │   │ Per-stock  │   │ 5-phase      │   │
│  │ banker,  │   │ discovery   │   │ PASS/      │   │ deal memo    │   │
│  │ HMA BoS  │   │ & mapping   │   │ CAUTION/   │   │              │   │
│  └────┬─────┘   └─────────────┘   │ FAIL       │   └──────────────┘   │
│       │                            └──────┬─────┘                       │
│       ▼                                   ▼                             │
│  ┌─────────────────────────────────────────────────┐                   │
│  │              portfolio_manager.py                │                   │
│  │  • Add PASS signals    • Flag exits              │                   │
│  │  • Update highest_close • Export Google Sheets   │                   │
│  │  • Backup CSV          • Calculate P&L           │                   │
│  └───────────────────────┬─────────────────────────┘                   │
│                          ▼                                              │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                     OUTPUT GENERATION                          │    │
│  │                                                                │    │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐  │    │
│  │  │ tweet_       │  │ newsletter_      │  │ substack_notes │  │    │
│  │  │ generator.py │  │ compiler.py      │  │ _generator.py  │  │    │
│  │  │              │  │                  │  │                │  │    │
│  │  │ 35 tweets/wk │  │ Full HTML        │  │ Tue/Thu notes  │  │    │
│  │  │ + variations │  │ newsletter       │  │                │  │    │
│  │  │ (3 accounts) │  │                  │  │                │  │    │
│  │  └──────┬───────┘  └────────┬─────────┘  └───────┬────────┘  │    │
│  │         │                   │                     │           │    │
│  │         ▼                   ▼                     ▼           │    │
│  │  content_queue.json   newsletter.html    substack_notes/     │    │
│  │  content_queue_       latest_newsletter  tuesday_note.md     │    │
│  │   account2.json        _briefing.md      thursday_note.md    │    │
│  │  content_queue_                                               │    │
│  │   account3.json                                               │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Also: market_analyzer.py, chart_capture.py (local only),              │
│        substack_content_generator.py, signal_tracker.py                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      DAILY POSTING PIPELINE                            │
│                 (.github/workflows/daily_post.yml)                      │
│                                                                         │
│  5 cron triggers/day (08:00, 10:00, 12:30, 15:30, 18:00 ET)           │
│                                                                         │
│  ┌──────────────────┐                                                  │
│  │ twitter_poster.py │─────▶ X/Twitter API (v2 post, v1.1 media)      │
│  │                    │                                                 │
│  │ For each account:  │     Account 1: +0 min                          │
│  │  1. Load queue     │     Account 2: +10 min                         │
│  │  2. Validate (5)   │     Account 3: +20 min                         │
│  │  3. Post tweet     │                                                 │
│  │  4. Update queue   │                                                 │
│  │  5. Commit to git  │                                                 │
│  └──────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       MANUAL STEPS                                     │
│                                                                         │
│  Saturday:  Copy newsletter.html to Substack (~10 min)                 │
│  Saturday:  Run chart_capture.py locally (TradingView login)           │
│  Tuesday:   Copy tuesday_note.md to Substack Notes (~2 min)           │
│  Thursday:  Copy thursday_note.md to Substack Notes (~2 min)          │
│  Ad-hoc:    portfolio_manager.py --update / --add / --exit             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 External Services & APIs

| Service | Usage | Auth | Rate Limits |
|---------|-------|------|-------------|
| **yfinance** | Stock data (OHLCV, 1yr daily) | None (free) | ~2000 req/hr |
| **Anthropic Claude** | Thematic analysis, gatekeeper, DD, tweets, newsletter | `ANTHROPIC_API_KEY` | Tier-based |
| **X/Twitter API v2** | Tweet posting | OAuth 1.0a (3 account sets) | 1500 tweets/15min |
| **X/Twitter API v1.1** | Media upload (charts) | OAuth 1.0a | Per-endpoint |
| **GitHub Actions** | CI/CD (Friday scan + daily posting) | Built-in | 2000 min/month (free) |
| **SMTP** | Email notifications on failure | Username/password | Provider-dependent |
| **TradingView** | Chart screenshots (local only) | Browser cookies | N/A (Playwright) |

### 1.3 Data Flow Summary

```
yfinance ──▶ scanner.py ──▶ signals.json
                │               │
                ▼               ▼
         portfolio.csv    tweet_generator.py ──▶ content_queue.json(s)
                │                                       │
                ▼                                       ▼
         signal_tracker.py                    twitter_poster.py ──▶ X API
                │
                ▼
         newsletter_compiler.py ──▶ newsletter.html ──▶ Substack (manual)
```

### 1.4 Key Dependencies Between Systems

| Upstream | Downstream | Coupling |
|----------|------------|----------|
| `scanner.py` | Everything | All outputs depend on scan results |
| `portfolio.csv` | signal_tracker, tweet_generator, newsletter | Source of truth for positions |
| `signals.json` | tweet_generator, newsletter_compiler | Weekly scan data |
| `content_queue.json` | twitter_poster | Queue consumed by daily cron |
| `config.py` | All modules | Marketing thresholds, banned terms, models |
| `marketing_vocabulary.py` | tweet_generator, newsletter_compiler | Vocabulary validation |
| `signal_tracker.py` | tweet_generator | Position filtering, safeguard checks |
| Claude API | scanner (steps 5-6), tweet_generator, newsletter_compiler | All LLM-dependent content |

---

## 2. Critical Path Analysis

### 2.1 Component Failure Impact

| Component Fails | Impact | Blast Radius | Recovery |
|-----------------|--------|--------------|----------|
| **yfinance down** | No scan possible | Full pipeline stops | Wait and retry; no manual workaround |
| **Claude API down** | Steps 5-7 skip (themes, gatekeeper, DD) | Technical scan works; no content generation | `--no-llm` for tech-only scan; manual tweet writing |
| **X/Twitter API down** | Tweets not posted | Daily posts fail silently (`\|\| true`) | Manual posting; tweets remain in queue for retry |
| **GitHub Actions down** | No automated scan or posting | Everything manual | Run `./run_friday.sh` locally; post manually |
| **portfolio.csv corrupt** | P&L wrong, exits missed, signals stale | All downstream content affected | Restore from `portfolio_backups/` directory |
| **scanner.py crash** | No weekly outputs | No tweets, no newsletter, no portfolio updates | Check logs, fix, re-run manually |
| **tweet_generator.py crash** | No content queues | Daily posting has nothing to post | Re-run `python tweet_generator.py`; previous week's queue may still work |
| **twitter_poster.py crash** | Slot missed permanently | One slot × 3 accounts | No retry mechanism; tweet lost |
| **newsletter_compiler.py crash** | No newsletter HTML | Substack not published Saturday | Re-run; or compile manually from briefing.md |
| **chart_capture.py fail** | No chart images | Tweets and newsletter missing visuals | Posts work without images; add charts manually |

### 2.2 Single Points of Failure

| SPOF | Risk Level | Mitigation |
|------|------------|------------|
| **`portfolio.csv`** | HIGH | Auto-backups exist but no file locking; concurrent GitHub Actions + manual CLI can corrupt |
| **`ANTHROPIC_API_KEY`** | HIGH | Single key for all LLM operations; key rotation = full outage |
| **Friday scan timing** | MEDIUM | If Friday scan fails, entire next week has no content; no automatic retry |
| **TradingView login cookies** | LOW | Chart capture requires valid session; expires periodically |
| **GitHub Actions runner** | MEDIUM | All automation depends on ubuntu-latest availability |
| **`content_queue.json`** | HIGH | If artifact upload fails Friday, daily posting has nothing; `continue-on-error: true` masks failures |

### 2.3 Recovery Procedures

| Scenario | Recovery Steps |
|----------|---------------|
| **Friday scan failed** | 1. Check GitHub Actions logs. 2. Fix issue. 3. Trigger `friday_scan.yml` via `workflow_dispatch`. |
| **Portfolio CSV corrupt** | 1. `cp portfolio/output/portfolio_backups/portfolio_LATEST.csv portfolio/output/portfolio.csv`. 2. Verify with `python portfolio_manager.py --report`. |
| **Daily tweet missed** | No retry mechanism. Slot is lost. Consider adding retry logic or queue rollover. |
| **Newsletter not generated** | 1. Re-run `python newsletter_compiler.py --from-html`. 2. Manual publish to Substack. |
| **Content queue empty** | 1. Re-run `python tweet_generator.py`. 2. Upload artifact manually or commit to repo. |
| **API key compromised** | 1. Rotate key in Anthropic console. 2. Update GitHub secret `ANTHROPIC_API_KEY`. 3. Update local env. |
| **All GitHub Actions fail** | Run locally: `python scanner.py --web-search && python tweet_generator.py && python newsletter_compiler.py --from-html` |

---

## 3. Consolidated Issues List

### 3.1 CRITICAL / HIGH Severity

| # | Source | ID | Description | Suggested Fix |
|---|--------|----|-------------|---------------|
| 1 | Audit 02 | D1 | **BoS Bearish auto-exits positions despite documentation saying "don't exit, tighten stop."** Code calls `pm.flag_exit()` on BoS Down. Backtesting shows trailing stops (+539%) outperform signal exits (+294%). | Remove `flag_exit()` on BoS Down. Implement `tighten_stop(ticker, 15.0)` method in portfolio_manager. |
| 2 | Audit 04 | D2/D3 | **SPY comparison uses non-matched holding periods.** `get_performance_summary()` averages closed-trade P&L vs fixed-window SPY. Beat SPY tweet uses 30-day window. Inflates alpha for long-held winners. | Use `calculate_fair_spy_comparison()` everywhere. Remove/replace the 30-day method. |
| 3 | Audit 06/07 | C-1/C-3 | **Newsletter loss suppression relies entirely on LLM prompt compliance.** Scanner briefing contains ALL positions including losers. No programmatic filter on HTML output. | Add post-compilation regex scan: reject HTML containing negative P&L values or STOPPED positions. |
| 4 | Audit 07 | C-1 | **Three divergent banned term lists.** `config.py` (40), `marketing_vocabulary.py` (45), `twitter_poster.py` (13 hardcoded). Last-line-of-defense has fewest terms. | Single source of truth: `twitter_poster.py` should import from `marketing_vocabulary.py`. Remove `config.py` duplicate list or make it import from vocabulary. |
| 5 | Audit 05/07 | C-7/C-2 | **No P&L re-verification at posting time.** Tweets generated Friday with snapshot data. A +30% position on Friday could be -5% by Wednesday. Tweet still shows +30%. | Add `verify_pnl_still_valid()` check in `twitter_poster.py` before posting. Fetch current price via yfinance; skip tweet if P&L has materially changed. |
| 6 | Audit 01 | C1 | **Threshold duplication between `scanner.py` and `config.py`.** Scanner uses OWN constants (BETA_MIN=1.5, BANKER_TIER1=70). Changing `config.py` has no effect on scanner. | Refactor scanner to import from `config.py`. Remove all inline threshold constants. |

### 3.2 MEDIUM Severity

| # | Source | ID | Description | Suggested Fix |
|---|--------|----|-------------|---------------|
| 7 | Audit 01 | C3 | No pre-filtering by market cap, volume, or price. Penny stocks pass all gates. | Add minimum price ($5) and average volume (100K) filters. |
| 8 | Audit 02 | D2 | No "tighten to 15%" implementation exists. Documentation recommends it, code always uses 20%. | Implement `tighten_stop_pct` field on Trade; update stop calculation logic. |
| 9 | Audit 03 | C2 | No file locking on CSV. Concurrent GitHub Actions + manual CLI can corrupt. | Use `fcntl.flock()` or atomic write (write to temp, rename). |
| 10 | Audit 03 | C3 | Delisted tickers not auto-detected. `check_delisted=False` by default. OPEN positions persist forever. | Enable `check_delisted=True` by default, or periodic cleanup job. |
| 11 | Audit 04 | D1 | No FX cost modeling. UK ISA operator loses 1.5-2% on round-trip FX invisibly. | Add configurable FX cost parameter (default 0% for US users). |
| 12 | Audit 04 | D4 | Exit price is scan-time price, not broker execution. Slippage not modeled. | Document limitation; optionally add slippage estimate config. |
| 13 | Audit 04 | D6 | Dollar P&L assumes 100 shares hardcoded. No actual position sizing. | Add `shares` or `position_size_usd` field to Trade. |
| 14 | Audit 05 | C-1 | No automatic retry on tweet API failure. Failed tweets lost permanently. | Add retry with exponential backoff (3 attempts). Mark failed tweets for next slot. |
| 15 | Audit 05 | C-3 | Thread partial failure not recoverable. Orphaned partial threads visible publicly. | Track `in_reply_to_id` state; resume from last successful tweet in thread. |
| 16 | Audit 06 | C-3 | Chart capture requires local execution (TradingView login). Not CI-compatible. | Document as known limitation. Consider mplfinance fallback for CI. |
| 17 | Audit 07 | C-4 | `"trailing stop"` is simultaneously banned and approved. Contradictory rules. | Remove "trailing stop" from banned list OR clarify: ban "20% trailing stop" only (already banned), allow "trailing stop" generically. |
| 18 | Audit 07 | C-5 | `config.py:contains_banned_term()` uses substring matching without word boundaries. | Align with `marketing_vocabulary.py` approach: word boundary regex for short terms. |
| 19 | Audit 07 | C-6 | Multi-account tweet variations not validated through same pipeline. | Run `validate_content()` on all variation queue files after generation. |

### 3.3 LOW Severity

| # | Source | ID | Description | Suggested Fix |
|---|--------|----|-------------|---------------|
| 20 | Audit 01 | L3 | Gatekeeper CAUTION maps to "CONSIDER" not "CAUTION". Dead code: "TRADE" in `passes_final_gate()`. | Clean up naming. Remove dead code branch. |
| 21 | Audit 01 | L5 | BoS BUY fires when lower step line changes — could fire on a LOWER pivot low. | Document this as intended behavior or add direction check. |
| 22 | Audit 01 | R1 | Dual config systems: `config.py` (root) and `src/common/config.py`. | Consolidate to single config.py. Remove or redirect src/common/config.py. |
| 23 | Audit 01 | R4 | ScanStats fields `beta_gte_1_8` and `beta_gte_2_0` are leftover names from old thresholds. | Rename to match current threshold (1.5). |
| 24 | Audit 02 | D5 | Both `bos_bullish` and `bos_bearish` can be True simultaneously. | Add mutual exclusion or document when both can be true. |
| 25 | Audit 02 | D6 | `elif` masks trailing stop when BoS bearish also fires. Only BoS reason recorded. | Log both reasons; prioritize the more urgent action. |
| 26 | Audit 02 | D8 | Legacy sell path still active as silent fallback if portfolio_manager import fails. | Remove legacy path; fail explicitly. |
| 27 | Audit 03 | C1 | No backup cleanup. Backups accumulate indefinitely. | Add retention policy (keep last 30 or last 90 days). |
| 28 | Audit 03 | C5 | Legacy fallback path if portfolio_manager import fails. | Remove; fail explicitly with clear error. |
| 29 | Audit 03 | C8 | CONSIDER vs CAUTION naming confusion across modules. | Standardize to single term system-wide. |
| 30 | Audit 04 | D5 | Unrealized P&L is sum of percentages, not average. 6 × +10% = +60% reported. | Use average P&L for summary; label clearly. |
| 31 | Audit 04 | D7 | No risk-adjusted metrics (Sharpe, Sortino, max drawdown). | Add to portfolio_manager --report output. |
| 32 | Audit 05 | C-4 | Negative P&L regex misses written forms ("down 18 percent"). | Extend regex or add text pattern matching. |
| 33 | Audit 05 | C-8 | Media upload uses v1.1 API which may be deprecated. | Monitor Twitter API deprecation timeline; prepare v2 migration. |
| 34 | Audit 06 | C-7 | HTML converter hand-rolled, no code block or HR support. | Replace with markdown library if needed. |
| 35 | Audit 07 | C-7 | Self-test has 2 inverted expected values (Roth IRA, 5th Gate). | Fix test expectations to `False`. |
| 36 | Audit 07 | C-8 | `twitter_poster.py` killed categories missing `self_quote`. | Add `self_quote` to the list. |

---

## 4. Configuration Inventory

### 4.1 Trading Parameters

| Parameter | Location | Current Value | Notes |
|-----------|----------|---------------|-------|
| `BETA_THRESHOLD` | `config.py:75` | 1.5 | Also hardcoded in `scanner.py` (issue #6) |
| `BANKER_TIER1` | `config.py:76` | 70 | |
| `BANKER_TIER2` | `config.py:77` | 60 | |
| `BANKER_TIER3` | `config.py:78` | 55 | |
| `TRAILING_STOP_PCT` | `config.py:71` | 20.0 | "Tighten to 15%" not implemented (issue #8) |
| `STOP_WARNING_PCT` | `config.py:72` | 5.0 | |
| `TIGHTEN_STOP_PCT` | `config.py:73` | 15.0 | Defined but never used in code |
| HMA period | `scanner.py` (hardcoded) | 21 | Should be in config.py |
| Pivot lookback (k) | `scanner.py` (hardcoded) | 1 | Should be in config.py |
| VWAP period | `scanner.py` (hardcoded) | 20 | Should be in config.py |
| Banker scaling factor | `scanner.py` (hardcoded) | 5 | Should be in config.py |

### 4.2 Marketing Thresholds

| Parameter | Location | Current Value |
|-----------|----------|---------------|
| `min_win_to_highlight` | `config.py:268` | 15.0% |
| `big_win_threshold` | `config.py:269` | 25.0% |
| `home_run_threshold` | `config.py:270` | 50.0% |
| `hall_of_fame_threshold` | `config.py:271` | 100.0% |
| `spy_outperformance_min` | `config.py:274` | 5.0% |
| `min_winners_for_top_performers` | `config.py:277` | 2 |
| `max_loss_to_mention` | `config.py:280` | -5.0% |
| `cold_streak_threshold` | `config.py:283` | 3 |
| `cold_streak_lookback_days` | `config.py:284` | 14 |
| `max_ticker_mentions_per_week` | `config.py:287` | 4 |
| `max_consecutive_days` | `config.py:49` | 2 |
| `cooldown_after_milestone` | `config.py:50` | 2 |

### 4.3 LLM Configuration

| Parameter | Location | Current Value |
|-----------|----------|---------------|
| `MODEL_SONNET` | `config.py:85` | claude-sonnet-4-20250514 |
| `MODEL_OPUS` | `config.py:86` | claude-opus-4-5-20251101 |
| `MAX_RETRIES` | `config.py:102` | 5 |
| `RATE_LIMIT_COOLDOWN` | `config.py:103` | 60s |
| `INTER_STEP_DELAY` | `config.py:104` | 30s |
| `INTER_STOCK_DELAY` | `config.py:105` | 8s |
| `BACKOFF_FACTOR` | `config.py:106` | 2.0 |
| `BACKOFF_MAX_WAIT` | `config.py:107` | 300s |
| Newsletter max_tokens | `newsletter_compiler.py` | 6000 |

### 4.4 Content Schedule

| Parameter | Location | Current Value |
|-----------|----------|---------------|
| Tweets per day | `config.py` | 5 |
| Tweets per week | `config.py` | 25 (was 35, check actual) |
| Daily slots (ET) | `daily_post.yml` | 08:00, 10:00, 12:30, 15:30, 18:00 |
| Friday scan time | `friday_scan.yml` | 21:30 UTC (16:30 ET) |
| Multi-account stagger | `daily_post.yml` | 600s (10 min) |
| Artifact retention | Workflows | 14 days (queues), 30 days (scans) |

### 4.5 Parameters That Should Be Externalized

These are currently hardcoded and should move to `config.py` or environment variables:

| Parameter | Current Location | Recommendation |
|-----------|-----------------|----------------|
| HMA period (21) | `scanner.py` inline | Move to `config.py` |
| Pivot lookback k (1) | `scanner.py` inline | Move to `config.py` |
| VWAP period (20) | `scanner.py` inline | Move to `config.py` |
| Banker scaling (5) | `scanner.py` inline | Move to `config.py` |
| Dollar P&L shares (100) | `portfolio_manager.py` inline | Move to `config.py` or per-trade |
| Newsletter max_tokens (6000) | `newsletter_compiler.py` inline | Move to `config.py` |
| CRITICAL_BANNED (13 terms) | `twitter_poster.py` inline | Import from `marketing_vocabulary.py` |
| KILLED_CATEGORIES (4 items) | `twitter_poster.py` inline | Import from `config.py` |
| CONSIDER expiry (21 days) | `portfolio_manager.py` inline | Move to `config.py` |

---

## 5. Testing Gaps

### 5.1 Current Test Coverage

| Component | Has Tests | Coverage |
|-----------|-----------|----------|
| `scanner.py` | `tests/` directory exists | Unknown — not audited in detail |
| `marketing_vocabulary.py` | Inline self-test (`__main__`) | 8 test cases; 2 have wrong expected values |
| All other modules | No formal tests | 0% |

### 5.2 Components Needing Tests (Priority Order)

| Priority | Component | Why |
|----------|-----------|-----|
| **P0** | `signal_tracker.py:filter_public_positions()` | Gatekeeps ALL public content. A bug here leaks losses. |
| **P0** | `marketing_vocabulary.py:validate_content()` | Core compliance check. Must never miss a banned term. |
| **P0** | `twitter_poster.py:validate_before_posting()` | Last line of defense. Must block invalid content. |
| **P1** | `config.py:can_show_entry_price()` | Controls what entry prices are shown publicly. |
| **P1** | `config.py:contains_banned_term()` | Used in generation-time validation. |
| **P1** | `portfolio_manager.py` P&L calculation | Core financial accuracy. |
| **P1** | `scanner.py` HMA pivot / BoS detection | Core signal generation logic. |
| **P2** | `signal_tracker.py:check_cold_streak()` | Circuit breaker correctness. |
| **P2** | `signal_tracker.py:get_winners_for_showcase()` | Public showcase filtering. |
| **P2** | `config.py:enforce_teal_branding()` | Branding consistency. |
| **P3** | `tweet_generator.py` category scheduling | Correct daily slot assignment. |
| **P3** | `newsletter_compiler.py` HTML generation | Output format correctness. |

### 5.3 Suggested Test Cases

#### `filter_public_positions()` (P0)

```
1. Input with STOPPED positions → output has none
2. Input with negative P&L → output has none
3. Input with mix of winners/losers → only winners returned
4. Empty input → empty output
5. All losers → empty output
6. Positions without pnl_pct → fetches prices (mock yfinance)
7. Output sorted by P&L descending
```

#### `validate_content()` (P0)

```
1. Clean text → (True, [])
2. Text with "HMA" → (False, ["HMA"])
3. Text with "RSI" as word boundary ("RSI divergence") → caught
4. Text with "RSI" embedded ("crisis") → NOT caught (word boundary)
5. Text with "BoS" as word boundary → caught
6. Text with "emboss" → NOT caught
7. Text with "Roth IRA" → caught
8. Text with "trailing stop" → caught (currently banned)
9. Text with "TEAL signal" → (True, []) (approved)
10. Text with multiple violations → all listed
11. Case variations ("hma", "HMA", "Hma") → all caught
12. Unicode variants ("Banker ≥ 55") → caught
```

#### `validate_before_posting()` (P0)

```
1. Clean tweet → (True, "Validation passed")
2. Tweet with "-5.2%" → blocked (negative P&L)
3. Tweet with "HMA" → blocked (banned term)
4. Tweet with killed category → blocked
5. Tweet over 280 chars → blocked
6. Tweet with "Roth IRA" → blocked (US-specific regex)
7. Tweet with "RSI" → NOT blocked (missing from hardcoded list — documents the gap)
8. Tweet with "PASS signal" → NOT blocked (documents the gap)
```

#### `can_show_entry_price()` (P1)

```
1. CLOSED winner → True
2. CLOSED loser → False
3. OPEN at +30% → True (above 25% threshold)
4. OPEN at +20% → False (below threshold)
5. OPEN at +25.0% exactly → True (boundary)
6. STOPPED → False
7. Missing status → False
```

---

## 6. Documentation Gaps

### 6.1 Well Documented

| Area | Quality | Source |
|------|---------|--------|
| Marketing rules / banned terms | Excellent | `CLAUDE.md`, `config.py` comments, `marketing_vocabulary.py` |
| Pipeline flow / architecture | Good | `CLAUDE.md` Tier 2 |
| Weekly schedule | Good | `CLAUDE.md` Tier 1 |
| Data structures / schemas | Good | `CLAUDE.md` Tier 2, `data_models.py` |
| Command cheat sheet | Good | `CLAUDE.md` Tier 1 |
| Environment variables | Good | `CLAUDE.md` Tier 3 |
| Trading strategy (internal) | Good | `CLAUDE.md` Tier 1 |

### 6.2 Needs Better Documentation

| Area | Current State | Recommendation |
|------|---------------|----------------|
| **Recovery procedures** | Not documented | Add runbook for each failure scenario (see Section 2.3 above) |
| **Multi-account system** | Only in plan file | Document account architecture, env var naming, variation generation in CLAUDE.md |
| **BoS signal semantics** | Misleading — "BUY" fires on structure change, not necessarily bullish | Clarify that pivot low change ≠ necessarily higher low |
| **"Tighten stop" behavior** | Documented but not implemented | Either implement or remove from documentation |
| **Validation pipeline** | Spread across 4 files | Add central validation architecture doc |
| **Content queue format** | No schema doc | Document JSON structure with all fields |
| **Celebration tracking** | Minimal | Document celebrations.json format, deduplication logic |
| **Variation generation** | Not documented | Document LLM prompt, output format, quality expectations |

### 6.3 Outdated Documentation

| Area | Issue | Fix |
|------|-------|-----|
| `CLAUDE.md` "TWEETS_PER_WEEK" | Says 35 in some places; actual schedule produces 25 (5/day × 5 weekdays) or 35 (5/day × 7 days). Inconsistent. | Clarify exact number and whether weekends are included. |
| `CLAUDE.md` Tier 3 "Future Integrations" | Lists X/Twitter, Substack, TradingView charts as "future" — all are now implemented. | Update to reflect current state. |
| `CLAUDE.md` environment vars | Lists `TWITTER_API_KEY` (old name). Actual secrets use `X_API_KEY`, `X2_API_KEY`, `X3_API_KEY` prefixes. | Update to match actual GitHub Secrets names. |
| `CLAUDE.md` "Grok prompts" sections | Extensive documentation of Grok prompt system that has been superseded by `tweet_generator.py`. | Reduce to historical note or remove. |
| `CLAUDE.md` post schedule | Shows 3 slots/day in Grok section, 5 slots/day in tweet section. | Remove Grok 3-slot references. |
| `MARKETING_GUIDE.md` | Deleted from repo (git status shows `D MARKETING_GUIDE.md`). `marketing_vocabulary.py` still references it in docstring. | Update reference to point to `config.py` or `CLAUDE.md`. |
| `MASTER_TODO.md` | Deleted. Referenced by multiple config comments. | Remove references or point to successor doc. |
| `src/common/config.py` | Parallel config that may be stale vs root `config.py`. | Consolidate or remove. |

---

*Generated: 2026-01-29 | Auditor: Claude Code*
