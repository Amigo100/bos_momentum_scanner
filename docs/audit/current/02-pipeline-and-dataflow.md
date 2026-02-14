# 02 - Pipeline and Dataflow

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. High-Level Pipeline Overview

The system runs a weekly cycle with two automated workflows:

1. **Friday Scan** (`friday_scan.yml` / `run_friday.sh`) - Full analysis pipeline
2. **Daily Post** (`daily_post.yml`) - Tweet distribution, 5 times per day

```
FRIDAY (4:30 PM ET)
  ┌──────────────────────────────────────────────────────────────┐
  │ Scanner Pipeline (core/scanner.py)                           │
  │   Step 1: Load tickers (complete_tickers.txt)                │
  │   Step 2: Download SPY benchmark (yfinance)                  │
  │   Step 3: Download stock data + calculate indicators         │
  │   Step 4: Technical gate (Beta + BoS + Banker)               │
  │   Step 5: Thematic analyzer (Claude Sonnet 4)                │
  │   Step 6: Gatekeeper final quality gate (Claude Sonnet 4)    │
  │   Step 7: Check sell signals on open positions               │
  │   Step 8: Update portfolio                                   │
  │   Step 9: Generate outputs (signals.json, report, briefing)  │
  ├──────────────────────────────────────────────────────────────┤
  │ Step 7.5: Automated Due Diligence (Claude Sonnet/Opus)       │
  │   Only PASS signals → DD → STRONG BUY/SPEC BUY added        │
  ├──────────────────────────────────────────────────────────────┤
  │ Content Pipeline                                              │
  │   Funnel Graphic → Chart Capture → Market Analysis →         │
  │   Newsletter Compilation → Tweet Generation (105 tweets) →   │
  │   Substack Notes → Git commit + push                         │
  └──────────────────────────────────────────────────────────────┘

SATURDAY-FRIDAY (daily, 5x/day)
  ┌──────────────────────────────────────────────────────────────┐
  │ Daily Poster (distribution/twitter_poster.py)                │
  │   Slot 1: 08:00 ET (pre-market)                             │
  │   Slot 2: 10:00 ET (morning)                                │
  │   Slot 3: 12:30 ET (midday)                                 │
  │   Slot 4: 15:30 ET (power hour) ← CRITICAL                  │
  │   Slot 5: 18:00 ET (after-hours)                            │
  │   → Posts to 3 accounts with 10-min stagger                  │
  └──────────────────────────────────────────────────────────────┘

SATURDAY (manual)
  └── Copy trades/current/newsletter.html to Substack

TUESDAY / THURSDAY (manual)
  └── Copy substack_notes/tuesday_note.md or thursday_note.md
```

---

## 2. Scanner Pipeline Trace (core/scanner.py)

### Step 1: Load Tickers (line 1076)

```
Input:  complete_tickers.txt (937 lines, ~1,800 tickers)
        + open positions from portfolio.csv
Output: List[str] of ticker symbols
Cost:   $0
```

- Function: `load_tickers()` (line 234)
- Reads `complete_tickers.txt`, splits on commas/newlines
- Also loads open position tickers from `PortfolioManager.get_open_positions()`
- Deduplicates and returns combined list

### Step 2: Download SPY Benchmark (line 1098)

```
Input:  None
Output: pd.Series of SPY daily returns (1 year)
Cost:   $0 (yfinance free)
```

- Uses `yf.download("SPY", period="1y", progress=False)`
- Calculates daily returns: `spy_data['Close'].pct_change().dropna()`

### Step 3: Download Data + Calculate Indicators (line 1121)

```
Input:  List[str] tickers, SPY returns
Output: Dict[str, Stock] with all indicator fields populated
Cost:   $0 (yfinance free)
```

- Bulk download via `yf.download(chunk, period="1y", threads=True, group_by='ticker')`
- Chunks of tickers processed in parallel
- Per-stock calculations:
  - `calculate_beta(stock_returns, spy_returns)` → Stock.beta
  - `calculate_banker(df)` → Stock.banker
  - `calculate_bos(df)` → Stock.bos_bullish, Stock.bos_bearish, Stock.bos_debug
  - 20-day return → Stock.return_20d
  - 4-week momentum → Stock.momentum_4w
  - Tier assignment via `Stock.get_tier()`

### Step 4: Technical Gate (line 1254)

```
Input:  Dict[str, Stock] all stocks
Output: List[Stock] passing technical criteria
Cost:   $0
```

- Filter: `stock.meets_technical_criteria()` (line 191)
  - `beta >= BETA_THRESHOLD` (1.5)
  - `bos_bullish == True`
  - `banker >= BANKER_TIER3` (55)
- Assigns tier: TIER1 (banker > 70), TIER2 (> 60), TIER3 (> 55)
- Typically: ~1,800 → ~44 stocks pass

### Step 5: Thematic Analyzer (line 1310)

```
Input:  List[Stock] technical signals
Output: List[Stock] with theme fields populated, themes_context string
Cost:   ~$0.15-0.50 (Claude Sonnet 4)
```

- Function: `run_thematic_gate()` (line 574)
- Calls `ThematicAnalyzer.run_step_1()`:
  - Identifies 5-7 investment themes via LLM
  - Classifies: PRIME / INVESTABLE / SELECTIVE / AVOID
  - Optional web search for current market data
- Calls `ThematicAnalyzer.run_step_2(ticker_list)`:
  - Maps tickers to themes
  - Scores fit: STRONG FIT / GOOD FIT / MODERATE FIT / POOR FIT
- Filter: `stock.passes_theme_gate()` (line 207)
  - `theme_verdict in ["STRONG FIT", "GOOD FIT"]`
- Typically: ~44 → ~17 stocks pass

### Step 6: Gatekeeper (line 1362)

```
Input:  List[Stock] theme-confirmed signals
Output: List[Stock] with final decisions
Cost:   ~$0.15-0.25 per stock (Claude Sonnet 4 + web search)
```

- Function: `run_gatekeeper()` (line 798)
- Calls `run_gatekeeper_batch()` from core/gatekeeper.py
- Per-stock analysis:
  - Catalyst assessment (earnings, events within 90 days)
  - Red flag detection (auditor issues, insider selling, dilution)
  - Sentiment analysis (analyst trends, short interest)
  - Web search: 2-3 searches per stock (recommended)
- Decision mapping (line 876-881):
  - GateDecision.PASS → `Stock.final_decision = "PASS"` (trade)
  - GateDecision.CAUTION → `Stock.final_decision = "CONSIDER"` (watchlist)
  - GateDecision.FAIL → `Stock.final_decision = "FAIL"` (skip)
- `is_confirmed()` (line 209): Returns True for PASS or CONSIDER
- Typically: ~17 → 6 PASS + 7 CONSIDER

### Step 7: Check Sell Signals (line 1391)

```
Input:  Dict[str, Stock] all downloaded stocks
Output: List[SellSignal]
Cost:   $0
```

- Function: `_check_sell_signals_portfolio_manager()` (line 963)
- For each open position in portfolio.csv:
  - Updates `highest_close` if current price > previous high
  - Calculates drawdown: `((highest_close - current) / highest_close) * 100`
  - **Trailing stop** (line 997): `drawdown >= TRAILING_STOP_PCT` (20%) → EXIT
  - **BoS bearish** (line 1010): `stock.bos_bearish` → Tighten stop to 15%
  - Trailing stop check is FIRST (if/elif), so stop takes precedence over BoS

### Step 7.5: Automated Due Diligence (line 3110)

```
Input:  List[Stock] PASS signals only
Output: DD verdicts applied to Stock objects
Cost:   ~$0.50-2.00 (Claude Sonnet 4 quick mode, or Opus full mode)
```

- Function: `run_automated_dd()` from core/dd_automator.py
- Only runs on PASS signals (not CONSIDER)
- Quick mode: Claude Sonnet 4, 4000 tokens
- Full mode (`--full-dd`): Claude Opus 4, 8000 tokens + 10000 thinking budget
- Verdict mapping:
  - STRONG BUY / SPEC BUY → Added to portfolio via `add_to_open_positions()`
  - NO GO → Rejected, not added to portfolio
- **Critical gate**: Only DD-approved stocks enter portfolio.csv

### Step 8: Update Portfolio (within DD step, lines 3158-3162)

```
Input:  Stock with DD approval
Output: Updated portfolio.csv
Cost:   $0
```

- `add_to_open_positions(stock)` → `PortfolioManager.add_trade()`
- Records: ticker, entry_date, entry_price, theme, tier, conviction
- Atomic write: temp file + `os.replace()` (line 349 of portfolio_manager.py)
- Backup created in `trades/portfolio_backups/`

### Step 9: Generate Outputs (line 2638)

```
Input:  All pipeline results
Output: Multiple files
Cost:   $0
```

Files generated by `save_results()`:
- `trades/current/signals.json` + `trades/weeks/YYYY-WXX/signals.json` + `trades/signals.json`
- `trades/analysis_log.csv` (appended)
- `trades/current/report.txt` + legacy `trades/latest_report.txt`
- `trades/current/newsletter_briefing.md` + legacy `trades/latest_newsletter_briefing.md`
- `trades/grok_prompts/latest_grok_prompts.md`

---

## 3. Content Pipeline Trace

### 3.1 Funnel Graphic (content/funnel_graphic.py)

```
Input:  trades/signals.json (stats section)
Output: trades/graphics/funnel_YYYYMMDD.png
```

- Reads scan stats: tickers_loaded, beta_gte_1_5, bos_bullish, etc.
- Generates matplotlib bar chart showing pipeline funnel
- Non-critical: failures don't stop pipeline

### 3.2 Chart Capture (content/chart_capture.py)

```
Input:  trades/signals.json (tickers), portfolio.csv (open positions)
Output: trades/charts/*.png, trades/charts/chart_manifest.json
```

- Uses Playwright to open TradingView with saved layout (ID: rxC5j0SK)
- Captures 1200x800 screenshots for each ticker
- Requires TradingView login session (headless mode uses saved cookies)
- Non-critical: tweets post without charts if capture fails

### 3.3 Market Analysis (content/market_analyzer.py)

```
Input:  None (uses web search)
Output: trades/market_analysis.md
```

- Calls Claude Sonnet 4 with web search tool
- Generates market context: indices, sectors, themes, sentiment
- Saved as markdown for newsletter compiler

### 3.4 Newsletter Compilation (content/newsletter_compiler.py)

```
Input:  trades/latest_newsletter_briefing.md, trades/market_analysis.md
Output: trades/latest_newsletter.html, trades/current/newsletter.html
```

- `--full` mode: Uses Claude to compile market analysis + briefing + DD into publication-ready HTML
- Basic mode: Simple markdown-to-HTML conversion
- Includes P&L leakage check on LLM output (lines 864-873)

### 3.5 Tweet Generation (content/reaction_generator.py)

```
Input:  trades/signals.json, trades/portfolio.csv, personas/*.yaml, examples/tweet_examples.json
Output: trades/content_queue.json (×3 accounts)
```

- Generates 105 tweets: 3 accounts × 7 days × 5 slots
- Per-account loop:
  1. Load persona from YAML
  2. Initialize ContentTracker (per-account limits)
  3. For each day: single Claude call generates 5 tweets
  4. Validate: FinTwit style, banned phrases, ticker density, character count
  5. Regenerate failures (up to 2 attempts + fallback)
- Cross-account deduplication
- Temporal reference validation

### 3.6 Substack Notes (content/substack_notes_generator.py)

```
Input:  trades/signals.json, portfolio data
Output: trades/current/substack_notes/tuesday_note.md, thursday_note.md
```

- Tuesday: "Portfolio Pulse" mid-week update
- Thursday: "Trade Spotlight" individual signal deep-dive
- Generated via Claude Sonnet 4

### 3.7 Substack Content (content/substack_content_generator.py)

```
Input:  trades/signals.json, portfolio data
Output: trades/substack_posts/{day}_post.md
```

- Generates Mon/Thu/Sat/Sun Substack posts
- Called with `--all` flag in friday_scan.yml

---

## 4. Distribution Pipeline Trace

### 4.1 Daily Tweet Posting (distribution/twitter_poster.py)

```
Input:  trades/content_queue.json (×3 accounts)
Output: Updated queues with status="posted", tweet_tracking.json
```

**Trigger:** 5 cron jobs in daily_post.yml (13:00, 15:00, 17:30, 20:30, 23:00 UTC)

**Slot Determination** (daily_post.yml lines 71-101):
- Manual dispatch: User specifies slot
- Scheduled: UTC hour mapped to slot via ranges (handles GitHub Actions delays)

**Posting Flow** (twitter_poster.py):
1. Load content queue JSON for the account
2. Find tweet matching current slot + today's date
3. Pre-post validation:
   - Banned term check against `CRITICAL_BANNED` (from config/marketing_vocabulary.py)
   - Full `BANNED_TERMS` check
   - Character count check (max 280)
   - If fails: attempt LLM repair via Claude (tweet_repair)
4. Post via Tweepy (Twitter API v2):
   - Text-only tweet, OR
   - Media upload (chart image) via Twitter API v1.1 → attach media_id
5. Register signal tweets for milestone tracking
6. Mark tweet as "posted" in queue JSON
7. Save updated queue

**Stagger:** Main account → 10 min → Account 2 → 10 min → Account 3

### 4.2 Milestone Quote Tracking (distribution/self_quote_tracker.py)

```
Input:  trades/tweet_tracking.json + portfolio P&L
Output: List of quotable milestones
```

- Thresholds: 25%, 50%, 100% gain
- Checked after each daily post run
- Returns unquoted milestones for potential quote tweets

---

## 5. Data Flow Map (File Dependencies)

```
complete_tickers.txt ──────┐
                           ▼
                    ┌──────────────┐
                    │  scanner.py  │◄── yfinance (SPY + stocks)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────────────┐
              ▼            ▼                    ▼
       signals.json   portfolio.csv    newsletter_briefing.md
              │            │                    │
    ┌─────────┴───┐   ┌───┴────┐         ┌────┴─────┐
    │             │   │        │         │          │
    ▼             ▼   ▼        ▼         ▼          ▼
reaction_    chart_  signal_ portfolio_ newsletter  grok_
generator    capture tracker  _google    compiler   prompts
    │            │      │    _sheets      │
    ▼            ▼      │    .csv         ▼
content_     charts/    │              newsletter.html
queue.json   *.png      │
    │                   ▼
    ▼            tweet_tracking.json
twitter_poster
    │
    ▼
Twitter API (3 accounts)
```

---

## 6. Weekly Timeline

| Time (ET) | Day | Action | Trigger | Files Affected |
|-----------|-----|--------|---------|----------------|
| 16:30 | Friday | Full scanner pipeline | `friday_scan.yml` cron | signals.json, portfolio.csv, briefing, tweets, notes |
| 08:00 | Saturday | Slot 1 tweet (3 accounts) | `daily_post.yml` cron | content_queue*.json |
| 10:00 | Saturday | Slot 2 tweet | cron | content_queue*.json |
| ~AM | Saturday | Publish newsletter to Substack | **Manual** | - |
| 12:30 | Saturday | Slot 3 tweet | cron | content_queue*.json |
| 15:30 | Saturday | Slot 4 tweet (power hour) | cron | content_queue*.json |
| 18:00 | Saturday | Slot 5 tweet | cron | content_queue*.json |
| ... | Sun-Mon | 5 tweets/day × 3 accounts | cron | content_queue*.json |
| ~AM | Tuesday | Post "Portfolio Pulse" Substack note | **Manual** | - |
| ... | Tue-Wed | 5 tweets/day × 3 accounts | cron | content_queue*.json |
| ~AM | Thursday | Post "Trade Spotlight" Substack note | **Manual** | - |
| ... | Thu-Fri | 5 tweets/day × 3 accounts | cron | content_queue*.json |

**Total weekly automated actions:** 1 scan + 35 tweet postings (5 slots × 7 days) × 3 accounts = 106 automated actions

**Total weekly manual actions:** 3 (newsletter publish + 2 Substack notes)

---

## 7. Cost Breakdown Per Weekly Run

| Component | Model | Typical Cost |
|-----------|-------|--------------|
| Thematic Analyzer (Step 5) | Claude Sonnet 4 | $0.15-0.50 |
| Gatekeeper (Step 6, ~17 stocks) | Claude Sonnet 4 + web search | $1.50-3.00 |
| Automated DD (Step 7.5, ~6 stocks) | Claude Sonnet 4 (quick) | $0.30-1.00 |
| Market Analyzer | Claude Sonnet 4 + web search | $0.10-0.30 |
| Newsletter Compiler | Claude Sonnet 4 | $0.10-0.30 |
| Tweet Generation (21 Claude calls) | Claude Sonnet 4 | $0.50-1.50 |
| Substack Notes | Claude Sonnet 4 | $0.10-0.30 |
| Substack Content | Claude Sonnet 4 | $0.10-0.30 |
| Web search queries | Anthropic API | $0.30-0.50 |
| **Total** | | **$3.15-7.70** |

Full DD mode with Opus adds ~$5-15 per stock.

---

## 8. Error Handling and Resilience

### Pipeline-Level

- `run_friday.sh`: Each step wrapped in `|| { log_warning "...failed - continuing anyway"; }`
- `friday_scan.yml`: Non-critical steps have `continue-on-error: true`
- Scanner core (`set -e` in shell, but Python catches exceptions per-step)

### Module-Level

| Module | Strategy |
|--------|----------|
| scanner.py | Try/except per stock in download loop; failed stocks skipped |
| thematic_analyzer.py | 8-retry exponential backoff for API calls; billing error fails immediately |
| gatekeeper.py | Per-stock retry; failed stocks get FAIL decision |
| portfolio_manager.py | Atomic writes (temp+rename); 30-day backup rotation |
| reaction_generator.py | Per-tweet regeneration loop (2 attempts + fallback) |
| twitter_poster.py | Per-tweet try/except; queue updated even on failure |
| chart_capture.py | Non-critical; failures logged but pipeline continues |

### Rate Limiting

- `RateLimiter` class in thematic_analyzer.py (lines 450-525)
- Configuration: 3.0s min between requests, 90s cooldown after 3+ rate limits
- Exponential backoff: `delay = min(base_delay * 2^attempt, max_delay)`
- Inter-step cooldown: 30s between analyzer and gatekeeper

---

*End of Document 2*
