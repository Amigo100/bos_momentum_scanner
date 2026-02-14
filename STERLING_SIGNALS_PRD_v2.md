# Sterling Signals — Product Requirements Specification v2.0

> **Date:** 2026-02-06
> **Status:** Active — serves as the canonical reference during implementation
> **Supersedes:** Original system design (implicit from codebase)
> **Companion:** `STERLING_SIGNALS_TODO.md` (task-level implementation checklist)

---

## 1. Executive Summary

Sterling Signals v2.0 introduces four major changes to the existing BoS Momentum Scanner system:

1. **Tweet Quality Overhaul** — Replace the three-persona content generation system with a single, uniform voice following the FinTwit Style Guide. Every tweet must contain specific tickers, prices, and charts. No more vague, system-referencing content.

2. **Daily Timeframe Scanner** — Add a lightweight daily-bar scanner that identifies BoS buy signals on the daily timeframe, generates up to 5 tweets per day about fresh daily signals with charts, and tracks these in a separate portfolio with the same winners-only / sell-signal logic as the weekly system.

3. **Sell Signal Notifications** — When the weekly portfolio detects a sell signal (HMA bearish pivot OR 20% trailing stop breach), send an immediate email/WhatsApp notification specifying which condition triggered, so the operator can execute the trade.

4. **Bug Fixes & Stability** — Fix all 4 critical and 5 high-priority issues identified in the audit, consolidate configuration drift, and add test coverage for the compliance-critical code paths.

---

## 2. System Architecture — Updated

### 2.1 Pipeline Overview (v2)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRIDAY WEEKLY SCAN (unchanged logic)              │
│                  (.github/workflows/friday_scan.yml)                 │
│                                                                     │
│  yfinance (weekly bars) → Beta → Banker → BoS → Thematic (LLM)    │
│  → Gatekeeper (LLM+web) → DD (LLM) → portfolio.csv                │
│                                                                     │
│  THEN: Generate weekly tweet queue + newsletter + substack notes    │
│        (all content now uses UNIFIED VOICE per FinTwit Style Guide) │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  NEW: WEEKDAY DAILY SCAN (Mon–Fri)                  │
│              (.github/workflows/daily_scan.yml)                     │
│                                                                     │
│  Trigger: Mon–Fri ~16:35 ET (after market close)                   │
│                                                                     │
│  yfinance (daily bars) → Beta → Banker → BoS (daily timeframe)    │
│  NO thematic / gatekeeper / DD steps                                │
│  → Filter: max 5 new buy signals per day                           │
│  → Log to daily_portfolio.csv                                       │
│  → Generate 1–5 daily signal tweets (with charts) → daily_queue    │
│  → Check existing daily positions for sell signals                  │
│  → Generate sell signal tweets (no loss amounts)                    │
│  → Check for daily winners ≥25% → generate receipt tweets           │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    DAILY POSTING (updated schedule)                  │
│               (.github/workflows/daily_post.yml)                    │
│                                                                     │
│  Slot 1: 08:00 ET  — Weekly content (pre-market)                   │
│  Slot 2: 10:00 ET  — Weekly content (morning)                      │
│  Slot 3: 12:30 ET  — Weekly content (midday)                       │
│  Slot 4: 15:30 ET  — Weekly content (power hour)                   │
│  Slot 5: 17:00 ET  — Daily signal tweets (post-close, priority)    │
│  Slot 6: 18:30 ET  — Daily signal overflow / weekly content         │
│  Slot 7: 07:30 ET* — Daily signal pre-market recap (next day)      │
│                                                                     │
│  * Slot 7 runs next trading day; posts daily signal recap           │
│  All 3 accounts post same content (uniform voice, 10min stagger)   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                 NEW: SELL SIGNAL NOTIFICATIONS                       │
│           (triggered within friday_scan + daily_scan)               │
│                                                                     │
│  When weekly portfolio detects:                                     │
│    • HMA bearish pivot on any position → notify "BEARISH PIVOT"    │
│    • 20% trailing stop breach → notify "TRAILING STOP"             │
│  Notification includes: ticker, trigger type, entry price,          │
│    current price, highest close, stop level                         │
│  Channels: Email (SMTP) + WhatsApp (Twilio or similar)             │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 New Data Files

| File | Purpose | Written by | Read by |
|------|---------|------------|---------|
| `trades/daily_portfolio.csv` | Daily timeframe positions | `daily_scanner.py` | `daily_scanner.py`, tweet generator |
| `trades/daily_signals.json` | Daily scan results | `daily_scanner.py` | Tweet generator |
| `trades/daily_content_queue.json` | Daily signal tweets (account 1) | Tweet generator | `twitter_poster.py` |
| `trades/daily_content_queue_account2.json` | Daily signal tweets (account 2) | Tweet generator | `twitter_poster.py` |
| `trades/daily_content_queue_account3.json` | Daily signal tweets (account 3) | Tweet generator | `twitter_poster.py` |

### 2.3 Updated External Services

| Service | Change |
|---------|--------|
| **Twilio / WhatsApp Business API** | NEW — for sell signal WhatsApp notifications |
| **SMTP** | EXPANDED — now also used for sell signal email notifications |
| **TradingView / Playwright** | EXPANDED — now captures daily timeframe charts in CI (headless) |

---

## 3. Tweet Generation — Complete Overhaul

### 3.1 Voice & Style

**The FinTwit Style Guide (`FINTWIT_STYLE_GUIDE.md`) is the authoritative reference for all tweet content.** The style guide must be loaded into the LLM context at the start of every tweet generation run.

**Key changes from v1:**

| Aspect | v1 (old) | v2 (new) |
|--------|----------|----------|
| Voice | 3 personas (Alex, Rozalia, James) | 1 uniform voice across all 3 accounts |
| Tone | Persona-specific (data-driven / warm / high-energy) | Confident but humble, data-driven, community-focused |
| Content | Could be vague ("system keeps working") | Must always contain $TICKER + price minimum |
| Charts | Optional on most categories | Required on scanner_result, performance, technical_analysis |
| Losers | Filtered but sometimes shown | Never shown. Winners only. Sell signals OK without loss amounts. |
| Banned terms | 60+ terms across two drifting lists | Single consolidated list from style guide + existing compliance terms |

### 3.2 Tweet Categories (from Style Guide)

All generated tweets must map to exactly one of these categories:

| Category | Source Data | Chart Required | Min Elements |
|----------|------------|----------------|--------------|
| `SCANNER_RESULT` | Weekly scan PASS signals | YES | $TICKER + entry price + thesis |
| `DAILY_SIGNAL` | Daily scan BoS buy signals | YES | $TICKER + price + "Daily BD" context |
| `THEME_ANALYSIS` | Thematic groupings from scan | Recommended | Theme name + 3+ tickers with prices |
| `PERFORMANCE` | Portfolio winners ≥25% | YES | $TICKER + entry → current + % gain |
| `WATCHLIST` | CONSIDER signals, near-triggers | Optional | 3+ tickers with prices + what to watch |
| `TECHNICAL_ANALYSIS` | Existing positions, key levels | YES | $TICKER + level + invalidation |
| `EDUCATIONAL` | Methodology, indicator explainers | If specific setup | Concrete example + lesson |
| `MARKET_COMMENTARY` | Market context, dip reactions | Recommended | Context + opportunity + action |
| `SELL_SIGNAL` | Daily/weekly BoS bearish pivots | YES | $TICKER + "setup invalidated" framing |
| `ENGAGEMENT` | Community building, milestones | No | Trading-adjacent, hooks |
| `NEWSLETTER_CTA` | Drive Substack traffic | Optional | Value proposition + link |

### 3.3 Content Generation Flow (v2)

```
1. Load FINTWIT_STYLE_GUIDE.md into LLM context
2. Load structured data:
   - Weekly: signals.json, portfolio.csv (winners only, ≥25% for receipts)
   - Daily: daily_signals.json, daily_portfolio.csv (winners only)
   - Market: SPY performance, sector moves
3. Editorial planning (LLM):
   - Allocate categories across 7 daily slots × 7 days
   - Daily signal tweets always assigned to Slot 5 (17:00 ET post-close)
   - Daily recap tweets assigned to Slot 7 (07:30 ET next morning)
   - Prioritise PERFORMANCE receipts when available
4. Generate tweets per slot:
   - Inject specific data (tickers, prices, %) directly — never rely on LLM memory
   - Validate against style guide banned phrases + existing CRITICAL_BANNED
   - Check category-specific required elements
   - Flag chart_required = true/false per tweet
   - Regenerate with specific feedback if validation fails (max 2 retries)
5. Duplicate each tweet identically to all 3 account queues (uniform voice)
6. Write to content_queue.json / daily_content_queue.json
```

### 3.4 Chart Generation

Charts are now required on most tweet categories. The system must generate charts in CI (headless).

**Approach:** Playwright-based TradingView chart capture, running in GitHub Actions with a headless Chromium instance.

| Trigger | Charts needed | Timeframe |
|---------|---------------|-----------|
| Friday weekly scan | 1 per PASS signal + 1 per winner showcase | Weekly |
| Daily scan (Mon–Fri) | 1 per daily buy signal (max 5) | Daily |
| Sell signal tweets | 1 per sell signal | Weekly or Daily (match source) |
| Performance receipts | 1 per showcased winner | Weekly (showing entry → current) |

**Chart requirements (from style guide):**
- Ticker symbol clearly visible
- Relevant timeframe (Weekly for weekly signals, Daily for daily signals)
- Key support/resistance levels marked
- Entry point if discussing a call
- Current price visible
- Diamond indicators visible (BoS markers)

**Fallback:** If chart capture fails (TradingView auth issues, rate limits), the tweet posts without an image and is flagged for manual chart attachment. The tweet text must still be valid without the chart.

### 3.5 Winners-Only Display Rules

| Scenario | Display? | What to show |
|----------|----------|--------------|
| Weekly position ≥25% gain | YES | $TICKER from $entry to $current (+X%) |
| Weekly position ≥0% but <25% | YES (as holding, not receipt) | $TICKER at $price in watchlist/theme context |
| Weekly position <0% | NO | Do not mention |
| Daily position ≥25% gain | YES | $TICKER from $entry to $current (+X%) |
| Daily position ≥0% but <25% | YES (as active signal) | $TICKER at $price |
| Daily position <0% | NO | Do not mention |
| Sell signal (BoS bearish) | YES | "$TICKER setup invalidated below $level" — no loss amount |
| Stopped out position | BRIEF ONLY | "Lost on $TICKER. Win more than you lose." — no amount |

### 3.6 Validation Pipeline (v2)

Every tweet passes through this pipeline before entering any queue:

```
Step 1: CATEGORY CHECK
  - Tweet maps to exactly one category
  - Category-specific required elements present (per style guide table)

Step 2: TICKER + PRICE CHECK
  - Contains at least one $TICKER
  - Each $TICKER has an associated price or % gain
  - Prices are accurate (cross-referenced against source data)

Step 3: BANNED PHRASE CHECK (consolidated)
  - Single canonical list combining:
    • FINTWIT_STYLE_GUIDE.md BANNED_PHRASES
    • config/marketing_vocabulary.py BANNED_TERMS
    • config/marketing_vocabulary.py CRITICAL_BANNED
  - No duplicates, no drift — one source of truth

Step 4: WINNERS-ONLY CHECK
  - No negative P&L percentages anywhere in text
  - No negative framing of any position
  - Sell signals use invalidation language only, no loss amounts

Step 5: INTERNAL TERMINOLOGY CHECK
  - No: BoS, HMA, Banker, tier numbers, conviction scores, VWAP
  - No: gate references, scanner internals, "5-gate pipeline"
  - Map to public language: "Blue Diamond" = buy signal, "Pink Diamond" = sell signal

Step 6: CHARACTER COUNT
  - ≤ 280 characters (or 4000 for long-form if X Premium)

Step 7: CHART FLAG
  - chart_required field set based on category
  - If chart_required but no chart available, flag for manual attachment

FAIL HANDLING:
  - On validation failure → LLM repair attempt with specific feedback (max 2x)
  - After 2 failures → drop tweet, log to failed_tweets.json for manual review
```

---

## 4. Daily Timeframe Scanner

### 4.1 Overview

A new lightweight scanner that runs Monday–Friday after market close, computing technical indicators on daily bars and identifying BoS buy signals. This runs independently of the weekly scan and has its own portfolio tracker.

### 4.2 Technical Gate (Daily)

The daily scanner uses the **same three technical indicators** as the weekly scanner, but computed on daily bars instead of weekly:

| Indicator | Weekly Config | Daily Config | Notes |
|-----------|--------------|--------------|-------|
| Beta | ≥1.5 (vs SPY, daily returns) | ≥1.5 (vs SPY, daily returns) | Same calculation, same threshold |
| Banker | ≥55 (20-day VWAP) | ≥55 (20-day VWAP) | Same calculation — already uses daily data |
| HMA Period | 21 (on weekly HL2) | 21 (on daily HL2) | Same period, different bar size |
| BoS | Pivot on weekly HMA step lines | Pivot on daily HMA step lines | Same logic, daily resolution |

**No LLM gates for daily signals.** The daily scanner skips thematic analysis, gatekeeper, and DD steps. It is purely technical: Beta ≥ 1.5, Banker ≥ 55, BoS bullish on daily bars.

### 4.3 Signal Limiting

The daily timeframe will produce many more signals than the weekly (tighter bars = more pivots). To keep content manageable:

- **Max 5 new buy signals per day** — if more than 5 pass the technical gate, rank by Banker score (highest institutional accumulation first) and take top 5.
- **Deduplication vs weekly portfolio** — if a ticker already has an OPEN weekly position, do not re-signal on daily. The weekly position takes precedence.
- **Deduplication vs prior daily signals** — if a ticker was signalled daily within the last 5 trading days, do not re-signal unless it had an intervening sell signal.

### 4.4 Daily Portfolio Tracking

`trades/daily_portfolio.csv` — same schema as `portfolio.csv`:

```
ticker,entry_date,entry_price,highest_close,stop_pct,theme,timeframe,status,exit_date,exit_price,exit_reason
```

**New field: `timeframe`** — value is `"daily"` for daily positions, `"weekly"` for weekly (added to weekly portfolio.csv too for clarity).

**Exit logic (daily positions):**
- **HMA bearish pivot on daily bars** — tightens trailing stop from 20% to 15% (same as weekly)
- **Trailing stop breach** — exit at 20% (or 15% if tightened)
- Daily sell signals are checked at each daily scan run

**Winners display:** Daily positions with ≥25% gain are eligible for PERFORMANCE receipt tweets. Daily positions with <0% gain are never mentioned.

### 4.5 Daily Scan Workflow

```yaml
# .github/workflows/daily_scan.yml
name: Daily BoS Scan
on:
  schedule:
    # Mon–Fri at 16:35 ET (21:35 UTC, adjusts for DST)
    - cron: '35 21 * * 1-5'   # EST
    - cron: '35 20 * * 1-5'   # EDT (summer)
  workflow_dispatch: {}

jobs:
  daily_scan:
    runs-on: ubuntu-latest
    steps:
      - checkout repo
      - setup python
      - install dependencies
      - run: python core/daily_scanner.py
        # Steps:
        # 1. Download daily bars for complete_tickers.txt via yfinance
        # 2. Compute Beta, Banker, HMA, BoS on daily timeframe
        # 3. Filter: Beta ≥ 1.5 AND Banker ≥ 55 AND BoS bullish
        # 4. Deduplicate vs weekly portfolio + recent daily signals
        # 5. Rank by Banker, take top 5
        # 6. Log to daily_portfolio.csv
        # 7. Check existing daily positions for sell signals
        # 8. Capture charts for new signals + sell signals
        # 9. Generate tweets via LLM (load style guide, inject data)
        # 10. Write to daily_content_queue*.json
        # 11. Send sell signal notifications (email + WhatsApp) for weekly portfolio
      - commit and push changes
```

### 4.6 Daily Content Tweets

For each new daily buy signal (up to 5):

```
Pattern: Signal Announcement (Style Guide Pattern 2)

$TICKER at $PRICE

New Daily buy signal. [Brief context from sector/industry].

Chart shows clean break above [level].

Easy invalidation on a close below $STOP_LEVEL. NFA!

[Chart attached]
```

For daily sell signals:

```
$TICKER setup invalidated below $LEVEL on the daily.

Win more than you lose, that's the name of the game.

[Chart attached]
```

For daily winners ≥25%:

```
$TICKER from $ENTRY to $CURRENT (+X%).

Daily signal nailed it. For those who followed...

[Chart attached]
```

---

## 5. Sell Signal Notifications

### 5.1 Trigger Conditions (Weekly Portfolio)

The weekly portfolio's exit logic remains the same, but now sends real-time notifications:

| Condition | Trigger | Stop Behaviour |
|-----------|---------|----------------|
| **HMA Bearish Pivot** | Weekly BoS flips from bullish → bearish | Tighten trailing stop from 20% → 15%. Notify operator. |
| **Trailing Stop Breach** | Weekly close < highest_close × (1 - stop_pct) | Exit position. Notify operator. |

Both conditions can fire in the same week for the same ticker (bearish pivot tightens stop, then the tighter stop triggers). The notification must specify **which condition printed**.

### 5.2 Notification Content

```
SUBJECT: 🔔 SELL SIGNAL — $TICKER [BEARISH PIVOT | TRAILING STOP]

Ticker:         $TICKER
Signal:         [HMA Bearish Pivot | 20% Trailing Stop | 15% Tightened Stop]
Entry Price:    $XX.XX (entered YYYY-MM-DD)
Current Price:  $XX.XX
Highest Close:  $XX.XX
Stop Level:     $XX.XX (XX% trailing)
P&L:            +X.X% or -X.X% (private — not published)
Theme:          [theme name]
Timeframe:      Weekly

ACTION REQUIRED: Review and execute sell if appropriate.
```

### 5.3 Notification Channels

**Email (SMTP):**
- Uses existing SMTP configuration (already in the system for failure alerts)
- Send to operator email address (env var: `NOTIFICATION_EMAIL`)
- Plain text + HTML formatted

**WhatsApp (Twilio API):**
- New integration via Twilio WhatsApp Business API
- Env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `WHATSAPP_TO`
- Concise message format (no HTML)
- Fallback: if Twilio fails, email notification is still sent

### 5.4 Notification Timing

- **Friday scan:** After portfolio sell-signal check completes, before content generation
- **Daily scan:** Daily portfolio sell signals also trigger notifications (same format, `Timeframe: Daily`)
- Notifications fire immediately upon detection — not queued

---

## 6. Weekly Pipeline Changes

### 6.1 Sell Signal Logic (Updated)

The weekly portfolio sell signal logic now:

1. **Checks BoS on weekly bars** — if any OPEN position's BoS flips bearish:
   - Tighten that position's `stop_pct` from 0.20 → 0.15
   - Send notification: "HMA Bearish Pivot"
   - Generate sell signal tweet (invalidation language, no loss amount)

2. **Checks trailing stop** — if any OPEN position's latest close < `highest_close × (1 - stop_pct)`:
   - Mark position as STOPPED in portfolio.csv
   - Send notification: "Trailing Stop"
   - Generate brief tweet if appropriate ("Lost on $TICKER. Win more than you lose.")

3. Both conditions are checked for every position every Friday scan.

### 6.2 Content Generation (Updated)

The Friday scan content generation is updated to:

- **Load `FINTWIT_STYLE_GUIDE.md`** at the start of every generation run
- **Use uniform voice** — no persona selection, all accounts get identical content
- **Allocate tweets across 9 categories** defined in section 3.2
- **Generate charts** for all chart-required categories
- **Apply full validation pipeline** (section 3.6) to every tweet
- **Remove the editorial board / persona reaction system** — replace with direct data-driven generation

### 6.3 Substack (Unchanged)

- Newsletter, Substack notes, and Substack posts continue as before
- Daily signals are **not** published to Substack (future consideration)
- Newsletter content must also follow the style guide's tone (confident, specific, data-driven)

---

## 7. Configuration Consolidation

### 7.1 Single Source of Truth for Banned Terms

Create a single, merged banned terms list in `config/banned_terms.py`:

```python
# config/banned_terms.py — SINGLE SOURCE OF TRUTH

# Terms that must NEVER appear in any public content
CRITICAL_BANNED = [
    # Internal indicator names
    "HMA", "Hull Moving Average", "BoS", "Break of Structure",
    "Banker", "VWAP", "banker score",
    # Internal system terms
    "gatekeeper", "thematic gate", "gate 1", "gate 2", "gate 3",
    "gate 4", "gate 5", "5-gate", "conviction score", "tier 1",
    "tier 2", "tier 3",
    # ... (full list from existing CRITICAL_BANNED)
]

# Phrases that indicate low-quality, vague content (from style guide)
BANNED_PHRASES = [
    "theme keeps delivering", "system keeps working",
    "trust the process", "systematic beats emotional",
    "quality over quantity", "the scanner found",
    "some interesting setups", "a few tickers",
    "still bleeding", "dragging down", "the red one",
    "big news coming", "stay tuned for something special",
    "you won't believe",
    # ... (full list from FINTWIT_STYLE_GUIDE.md)
]

# All banned terms combined for validation
ALL_BANNED = CRITICAL_BANNED + BANNED_PHRASES
```

All modules import from this single file. No fallback to empty list anywhere.

### 7.2 Configuration Updates

| Parameter | Current | New | File |
|-----------|---------|-----|------|
| `PERSONAS` | 3 (Alex, Rozalia, James) | REMOVED — uniform voice | `config/settings.py` |
| `TWEETS_PER_DAY` | 5 | 7 (5 weekly + 2 daily signal slots) | `config/settings.py` |
| `DAILY_SIGNAL_MAX` | N/A | 5 | `config/settings.py` |
| `DAILY_SCAN_TICKERS` | N/A | same as `complete_tickers.txt` | `config/settings.py` |
| `NOTIFICATION_EMAIL` | N/A | env var | `.github/workflows/` |
| `WHATSAPP_TO` | N/A | env var | `.github/workflows/` |
| `TWILIO_*` | N/A | env vars | `.github/workflows/` |
| `CHART_CAPTURE_HEADLESS` | N/A | `true` (CI) / `false` (local) | `config/settings.py` |
| `STYLE_GUIDE_PATH` | N/A | `FINTWIT_STYLE_GUIDE.md` | `config/settings.py` |
| Budget default | `"£5,000"` | `"$5,000"` | `utils/run_full_pipeline.py` |

---

## 8. Bug Fixes Required

### 8.1 Critical (Must Fix Before Any New Features)

| ID | Issue | Fix |
|----|-------|-----|
| CRIT-1 | `run_full_pipeline.py` line 41: stale `scanner.py` path | Change to `BASE_DIR / "core" / "scanner.py"` |
| CRIT-2 | `run_full_pipeline.py` line 86: stale `due_diligence.py` path | Change to `BASE_DIR / "core" / "due_diligence.py"` |
| CRIT-3 | `run_full_pipeline.py` line 60: reads `data/signals.json` (doesn't exist) | Change to `trades/signals.json` |
| CRIT-4 | `scanner.py` line 3194: imports from archived module | Update import to `core.dd_automator` or remove |

### 8.2 High Priority (Fix During Implementation)

| ID | Issue | Fix |
|----|-------|-----|
| HIGH-1 | Content queue path inconsistency (3 different paths) | Standardise all to `trades/content_queue*.json` |
| HIGH-2 | `CRITICAL_BANNED` fallback to empty `[]` | Import from `config/banned_terms.py`, hard fail if missing |
| HIGH-3 | CAUTION vs CONSIDER naming confusion | Standardise to "CONSIDER" everywhere |
| HIGH-4 | Budget default `£5,000` → `$5,000` | Fix in `run_full_pipeline.py` |
| HIGH-5 | `None` pnl_pct crashes `filter_public_positions` | Add explicit None handling: treat as 0% or skip |

### 8.3 Medium Priority (Clean Up During Implementation)

Fix all 12 medium-priority issues from audit 08 as encountered during implementation. Key items:
- Remove unused imports (`getpass`, `os`, `timedelta`)
- Add `__main__` guards to all scripts
- Replace bare `except:` with specific exception types
- Consolidate dual output paths (`trades/` vs `trades/current/tweets/`)

---

## 9. Testing Requirements

### 9.1 P0 Tests (Must Pass Before Deploy)

| Test | Module | What It Validates |
|------|--------|-------------------|
| `test_filter_public_positions_winners_only` | `signal_tracker.py` | Only ≥0% positions returned; None handled |
| `test_validate_content_banned_terms` | `banned_terms.py` | Every CRITICAL_BANNED + BANNED_PHRASES term caught |
| `test_validate_before_posting_full` | `twitter_poster.py` | Negative P&L blocked, banned terms blocked, char count |
| `test_daily_scanner_signal_limit` | `daily_scanner.py` | Max 5 signals returned, ranked by Banker |
| `test_daily_scanner_dedup_weekly` | `daily_scanner.py` | Weekly portfolio tickers excluded |
| `test_sell_notification_triggers` | `notifications.py` | Bearish pivot + trailing stop both trigger correctly |
| `test_tweet_category_validation` | `tweet_generator.py` | Each category enforces required elements |
| `test_style_guide_compliance` | `tweet_generator.py` | Generated tweets pass full validation pipeline |

### 9.2 P1 Tests (Before Production)

| Test | Module |
|------|--------|
| `test_can_show_entry_price` | `config.py` |
| `test_portfolio_pnl_calculation` | `portfolio_manager.py` |
| `test_hma_bos_daily_vs_weekly` | `scanner.py` / `daily_scanner.py` |
| `test_chart_capture_headless` | `chart_capture.py` |
| `test_content_queue_path_consistency` | Integration test |
| `test_notification_email_format` | `notifications.py` |

### 9.3 Integration Tests

| Test | Scope |
|------|-------|
| `test_friday_scan_end_to_end` | Full pipeline: scan → portfolio → content → queues |
| `test_daily_scan_end_to_end` | Daily scan → daily portfolio → daily tweets |
| `test_daily_post_workflow` | Queue consumption → validation → posting |
| `test_sell_signal_notification_flow` | Sell detection → email + WhatsApp sent |

---

## 10. GitHub Actions Workflows (Updated)

### 10.1 `friday_scan.yml` (Updated)

```
Schedule: Friday 16:30 ET (unchanged)
Steps:
  1. Checkout + setup
  2. Run weekly scanner (unchanged logic)
  3. Update weekly portfolio (add PASS, check sells, update highest_close)
  4. NEW: Send sell signal notifications (email + WhatsApp)
  5. Capture charts (headless Playwright) for all signal/sell/winner tweets
  6. Generate weekly content (UPDATED: uniform voice, style guide, full validation)
  7. Generate newsletter + Substack notes (updated tone)
  8. Commit + push
```

### 10.2 `daily_scan.yml` (NEW)

```
Schedule: Mon–Fri 16:35 ET
Steps:
  1. Checkout + setup
  2. Run daily scanner (technical gates only, max 5 signals)
  3. Update daily portfolio (add buys, check sells, update highest_close)
  4. Send sell signal notifications for daily portfolio
  5. Capture daily charts (headless Playwright)
  6. Generate daily signal tweets (style guide compliant)
  7. Write to daily_content_queue*.json
  8. Commit + push
```

### 10.3 `daily_post.yml` (Updated)

```
Schedule: 7 slots/day (up from 5)
  - 07:30 ET: Daily signal pre-market recap (from previous day's daily scan)
  - 08:00 ET: Weekly content
  - 10:00 ET: Weekly content
  - 12:30 ET: Weekly content
  - 15:30 ET: Weekly content (power hour)
  - 17:00 ET: Daily signal tweets (post-close, priority — from today's daily scan)
  - 18:30 ET: Daily signal overflow or weekly content

Changes:
  - Posts identical content to all 3 accounts (10min stagger preserved)
  - Daily signal slots (07:30, 17:00) pull from daily_content_queue*.json
  - Weekly content slots pull from content_queue*.json (as before)
  - 18:30 slot: if daily queue has remaining tweets, post those; else weekly
```

---

## 11. New File Structure

```
core/
  scanner.py              # Weekly scanner (existing, bug fixes applied)
  daily_scanner.py        # NEW: Daily timeframe scanner
  portfolio_manager.py    # Updated: adds timeframe field, notification hooks
  dd_automator.py         # Existing (unchanged)
  gatekeeper.py           # Existing (unchanged)
  thematic_analyzer.py    # Existing (unchanged)

config/
  settings.py             # Updated: new constants, removed personas
  banned_terms.py         # NEW: single source of truth for all banned terms
  marketing_vocabulary.py # DEPRECATED: merged into banned_terms.py

content/
  tweet_generator.py      # REWRITTEN: uniform voice, style guide, categories
  reaction_generator.py   # DEPRECATED: replaced by tweet_generator.py v2
  newsletter_compiler.py  # Updated: style guide tone
  chart_capture.py        # Updated: headless CI support, daily timeframe

distribution/
  twitter_poster.py       # Updated: dual queue support (weekly + daily)
  signal_tracker.py       # Updated: None handling, daily portfolio support
  notifications.py        # NEW: email + WhatsApp sell signal notifications

.github/workflows/
  friday_scan.yml         # Updated: notification step, chart capture
  daily_scan.yml          # NEW: Mon–Fri daily scanner
  daily_post.yml          # Updated: 7 slots, dual queue consumption
```

---

## 12. Environment Variables (New)

| Variable | Purpose | Required |
|----------|---------|----------|
| `NOTIFICATION_EMAIL` | Operator email for sell signal alerts | Yes |
| `SMTP_HOST` | SMTP server (existing) | Yes |
| `SMTP_USER` | SMTP username (existing) | Yes |
| `SMTP_PASS` | SMTP password (existing) | Yes |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For WhatsApp |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For WhatsApp |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp sender number | For WhatsApp |
| `WHATSAPP_TO` | Operator WhatsApp number | For WhatsApp |
| `TRADINGVIEW_SESSION` | TradingView session cookie for headless chart capture | For charts in CI |

---

## 13. Migration Notes

### 13.1 Deprecations

| Component | Status | Replacement |
|-----------|--------|-------------|
| 3-persona system (Alex/Rozalia/James) | Deprecated | Uniform voice per style guide |
| `content/reaction_generator.py` | Deprecated | `content/tweet_generator.py` (rewritten) |
| `config/marketing_vocabulary.py` | Deprecated | `config/banned_terms.py` |
| Grok prompt generation | Deprecated | All content now LLM-generated |
| Editorial board system | Deprecated | Direct category allocation |

### 13.2 Backwards Compatibility

- Weekly portfolio.csv gains a `timeframe` column — existing rows default to `"weekly"`
- Content queue JSON format unchanged — daily queues use same structure
- Twitter posting logic unchanged — just reads from additional queue files
- Newsletter and Substack workflows unaffected

### 13.3 Rollback Plan

- Daily scanner is a standalone addition — can be disabled by removing `daily_scan.yml` cron
- Tweet generator rewrite is the highest-risk change — keep `reaction_generator.py` available as fallback
- Notification system is additive — failure doesn't affect core pipeline

---

## Appendix A: Weekly Schedule (v2)

| Day | Time (ET) | Event |
|-----|-----------|-------|
| Mon | 07:30 | Post: Daily signal recap (from Friday's daily scan) |
| Mon | 08:00, 10:00, 12:30, 15:30 | Post: Weekly content (4 slots) |
| Mon | 16:35 | Run: Daily scan → daily portfolio → daily tweets |
| Mon | 17:00 | Post: Today's daily signals |
| Mon | 18:30 | Post: Daily overflow or weekly content |
| Tue | Same as Mon | + Manual: Substack Tuesday note |
| Wed | Same as Mon | |
| Thu | Same as Mon | + Manual: Substack Thursday note |
| Fri | Same as Mon (07:30–15:30) | |
| Fri | 16:30 | Run: Weekly scan → portfolio → notifications → content |
| Fri | 16:35 | Run: Daily scan (runs after weekly) |
| Fri | 17:00, 18:30 | Post: Daily signals + weekly new signals |
| Sat | 08:00–18:30 | Post: Weekly content (7 slots, no daily scan) |
| Sat | Manual | Publish newsletter to Substack |
| Sun | 08:00–18:30 | Post: Weekly content (7 slots, no daily scan) |

---

*This document is the authoritative product specification for Sterling Signals v2.0. All implementation work should reference this PRD and the companion TODO list.*
