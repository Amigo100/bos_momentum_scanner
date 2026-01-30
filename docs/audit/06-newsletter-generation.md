# Sterling Signals Newsletter Generation System Audit

**Document:** 06-newsletter-generation.md
**Last Updated:** 2026-01-29
**Status:** Complete
**Auditor:** Claude Opus 4.5

---

## Table of Contents

1. [Newsletter Structure](#1-newsletter-structure)
2. [Content Generation by Section](#2-content-generation-by-section)
3. [TradingView Chart Integration](#3-tradingview-chart-integration)
4. [Weekly Workflow Timeline](#4-weekly-workflow-timeline)
5. [Substack Integration](#5-substack-integration)
6. [Consistency Verification](#6-consistency-verification)
7. [Substack Notes (Mid-Week)](#7-substack-notes-mid-week)
8. [Substack Posts (Extended Content)](#8-substack-posts-extended-content)
9. [Concerns and Gaps](#9-concerns-and-gaps)

---

## 1. Newsletter Structure

### 1.1 Standard Sections (in order)

The newsletter is assembled from multiple data sources into a single publication-ready HTML document. The section order is determined by the LLM compilation prompt (`newsletter_compiler.py:105-189`):

| # | Section | Automated | Manual | Source |
|---|---------|-----------|--------|--------|
| 1 | Subject Line | Yes (LLM) | — | Claude generates from signal count + hook phrase |
| 2 | Market Context | Yes (LLM + web search) | — | `market_analyzer.py` via Claude + web search |
| 3 | Hot Themes | Yes | — | Scanner thematic analyzer (PRIME + INVESTABLE) |
| 4 | Signal Candidates (TEAL) | Yes | Chart screenshots | Scanner gatekeeper PASS signals |
| 5 | Signal Candidates (AMBER) | Yes | — | Scanner gatekeeper CAUTION signals |
| 6 | Due Diligence Summaries | Yes (LLM) | — | `dd_automator.py` per PASS signal |
| 7 | Portfolio Update | Yes | — | `portfolio_manager.py` open positions |
| 8 | Recently Closed Trades | Yes | — | Portfolio exits within last 7 days |
| 9 | Win Highlights | Yes | — | Closed trades above 15% gain |
| 10 | Benchmark Comparison | Yes | — | Portfolio YTD vs SPY YTD |
| 11 | Caution Signals | Yes | — | BoS Down / stop distance alerts |
| 12 | Disclaimer | Yes (static) | — | Legal footer template |

### 1.2 Two-Stage Generation

**Stage 1: Scanner Briefing** (scanner.py:1797-2230)
- Raw data compilation from scan results
- Generated automatically by `generate_newsletter_briefing()`
- Output: `trades/current/newsletter_briefing.md`
- Contains all data tables, charts placeholders, P&L figures

**Stage 2: LLM Compilation** (newsletter_compiler.py:192-230)
- Claude Sonnet 4 receives briefing + market analysis + DD results + portfolio status + benchmark
- Produces publication-ready markdown with marketing language applied
- Model: `claude-sonnet-4-20250514`, max_tokens: 6000
- Output: `trades/current/newsletter.html` (via markdown-to-HTML conversion)

### 1.3 Subject Line Formula (newsletter_compiler.py:92-94)

```
Week ${WEEK_NUM}: ${NEW_SIGNALS} TEAL Signals | ${HOOK_PHRASE}
Example: "Week 4: 3 TEAL Signals | Why Power Grid is 2026's Winning Theme"
```

---

## 2. Content Generation by Section

### 2.1 Market Context (market_analyzer.py:140-204)

**Generator:** `market_analyzer.py` with `run_market_analysis()`
- Model: Claude Sonnet 4 with web search enabled
- Max tokens: 3000
- Tool: `web_search_20250305` for real-time data

**Content sourced via web search:**
- S&P 500, NASDAQ, Russell 2000 weekly changes
- Federal Reserve announcements, economic data
- Sector rotation patterns
- VIX levels and sentiment
- Looking-ahead catalysts

**Output format:** 4-paragraph markdown with `## Market Context` header
**Saved to:** `trades/market_analysis.md` or `trades/current/market_analysis.md`

**Loading in compiler** (newsletter_compiler.py:237-258):
```
Primary: trades/current/market_analysis.md
Fallback: trades/market_analysis.md
```

### 2.2 Hot Themes (scanner.py:1851-1892)

**Source:** Thematic analyzer output (`themes_data` list)
**Filtering:** PRIME classification first (highest conviction), then INVESTABLE
**Fields per theme:** name, classification, theme_type, composite_score, thesis_summary (truncated to 300 chars), key_catalysts

**Format in briefing:**
```markdown
### PRIME Themes (Highest Conviction)
**AI Infrastructure** (TREND)
- Score: 8.2/10
- Thesis: Data center buildout accelerating...
- Catalysts: NVDA earnings, hyperscaler CapEx guidance
```

### 2.3 Signal Candidates — TEAL/PASS (scanner.py:1907-1951)

**Source:** Confirmed stocks with `final_decision == "TRADE"` or `"PASS"`
**Per-signal data:**

| Field | Source | Example |
|-------|--------|---------|
| Price | yfinance | $61.54 |
| Theme + fit | Thematic analyzer | "Power Grid (STRONG FIT)" |
| Tier | Technical gate | TIER1 |
| Beta | Calculation | 2.48 |
| Banker | Calculation | 78.3 |
| Conviction | Gatekeeper | 4/5 |
| Catalyst summary | Gatekeeper | "Earnings in 3 weeks" |
| Red flag level | Gatekeeper | CLEAN |
| Bullish factors | Gatekeeper | Top 3 |
| Risk factors | Gatekeeper | Top 3 |
| Analysis | Gatekeeper reasoning | Full text |
| Recommended action | Gatekeeper | "Enter Monday at market open" |
| Chart placeholder | Template | `📸 **[CHART: TICKER]**` |

### 2.4 Due Diligence Integration (newsletter_compiler.py:279-326)

**Source:** `signals.json` buy_signals array with DD fields
**DD fields per signal:**

| Field | Source | Example |
|-------|--------|---------|
| `dd_verdict` | dd_automator.py | STRONG BUY / SPEC BUY / NO GO |
| `dd_conviction` | dd_automator.py | 8/10 |
| `dd_position_size` | dd_automator.py | FULL / REDUCED / PASS |
| `dd_key_catalyst` | dd_automator.py | "Earnings report Feb 12" |
| `dd_fatal_flaw` | dd_automator.py | null or flaw description |

**DD modes** (dd_automator.py):
- Quick DD: Sonnet, 4000 tokens — 5-minute analysis
- Full DD: Opus, 8000 tokens + extended thinking — 4-phase deep analysis

**Fallback:** If no DD run, returns `"[DD not yet run]"` (newsletter_compiler.py:325)

### 2.5 Portfolio Update (scanner.py:2101-2172)

**Source:** `portfolio_manager.py` → `get_open_positions()` with live yfinance prices

**Table format:**
```markdown
| Ticker | Theme | P&L | Days Held | Stop Distance |
|--------|-------|-----|-----------|---------------|
| RCAT | Drone Technology | +55.9% | 23d | 🟢 26.4% |
| VNET | Cloud | -10.0% | 45d | 🔴 8.2% |
```

**Stop distance color coding:**
- 🟢 >15% — safe
- 🟡 10-15% — watch
- 🔴 <10% — alert

**Marketing note:** Entry prices for open positions are marked PRIVATE in the briefing (scanner.py:2152-2153). The newsletter's internal briefing shows full P&L, but the LLM compilation system prompt instructs Claude to never show full portfolio with individual P&L publicly (newsletter_compiler.py:76-79).

### 2.6 Win Highlights (newsletter_compiler.py:328-389)

**Source:** `portfolio.csv` — closed trades
**Filter:** `status in ['CLOSED', 'STOPPED'] AND pnl_pct >= 15.0`
**Threshold:** From `config.MARKETING_THRESHOLDS['min_win_to_highlight']` (default 15%)
**Limit:** Top 5 by P&L descending
**Marketing rule:** Only shows winning trades above threshold. Losing trades never appear in this section.

### 2.7 Benchmark Comparison (newsletter_compiler.py:392-485)

**Calculation:**
- Portfolio YTD: Sum of open position P&L via yfinance (lines 415-456)
- SPY YTD: `((current_spy / jan1_spy) - 1) * 100` (lines 392-412)
- Alpha: `portfolio_return - spy_return`

**Conditional messaging** (lines 476-481):
- Outperforming: Bullish alpha narrative
- Underperforming: Focus on methodology and discipline instead
- This conditional is enforced in the LLM system prompt (line 85-87)

### 2.8 Performance Summary (scanner.py:2084-2107)

**Fields:**
```markdown
- Open Positions: {count}
- Unrealized P&L: {sum_pnl_pct}% (${sum_pnl_usd})
- Win Rate: {win_rate}% (closed trades)
- Avg Winner: {avg_winner}%
- Avg Loser: {avg_loser}%
- Total Closed: {count}
```

**Source:** `portfolio_manager.py` → `get_performance_summary()` (scanner.py:2066)

### 2.9 Recently Closed Trades (scanner.py:2112-2126)

**Filter:** Trades with exit_date within last 7 days
**Shows:** Ticker, exit date, entry price, exit price, P&L%, status (CLOSED/STOPPED)
**Note:** This section shows ALL recent exits including losses — honesty rule applies here.

---

## 3. TradingView Chart Integration

### 3.1 Chart Capture Mechanism (chart_capture.py)

**Tool:** Playwright browser automation (not Selenium, not mplfinance)
**Source:** TradingView Pro account with custom indicators

**Chart capture process:**
1. Launch persistent Chromium context (`chart_capture.py:248-257`)
2. Navigate to TradingView chart with saved layout ID
3. Apply ticker symbol via URL parameter
4. Wait for indicators to load (7-point error detection, lines 417-472)
5. Hide indicator names via JavaScript injection
6. Screenshot chart element (4-selector fallback chain, lines 166-187)
7. Save PNG to `trades/charts/`

### 3.2 Chart Sizes

| Target | Dimensions | Filename Suffix | Purpose |
|--------|-----------|----------------|---------|
| X/Twitter | 1400 x 900 | (none) | Twitter card embed |
| Substack | 1000 x 700 | `_substack` | Newsletter embed |

**File naming:** `{TICKER}_{YYYYMMDD}.png` / `{TICKER}_{YYYYMMDD}_substack.png`

### 3.3 Which Tickers Get Charts

Determined by CLI arguments in `run_local_friday.sh`:
```bash
python chart_capture.py --tickers-from trades/signals.json --include-portfolio
```

This captures:
- All PASS/TRADE signals from the weekly scan
- All open portfolio positions
- Optionally: specific tickers via `--ticker` or `--tickers`

### 3.4 Authentication (Three Methods)

| Method | How | Persistence |
|--------|-----|-------------|
| Interactive login | Browser opens, user logs in manually (2-min wait) | Saved to `.playwright_profile/` |
| Persistent profile | Reuses `.playwright_profile/` directory | 30-90 days |
| Cookie file | Loads `.tradingview_cookies.json` | Until cookies expire |

**First run:** Interactive mode (browser visible).
**Subsequent runs:** `--headless --skip-wait` (no browser window).

### 3.5 Chart Manifest (trades/charts/chart_manifest.json)

```json
{
  "captured_at": "2026-01-24T18:05:24.356074",
  "charts": {
    "EOSE": "trades/charts/EOSE_20260124.png",
    "RMBS": "trades/charts/RMBS_20260124.png",
    "funnel_graphic": {
      "path": "trades/charts/funnel_20260127.png",
      "generated": "2026-01-27T11:37:38.092385",
      "data": {"universe": 885, "final": 3}
    }
  }
}
```

### 3.6 Chart Embedding in Newsletter (newsletter_compiler.py:512-648)

**Placeholder in briefing markdown:**
```markdown
📸 **[CHART: TICKER]** - *Add TradingView screenshot*
```

**HTML conversion pipeline:**
1. Regex finds `[CHART: TICKER]` patterns (lines 646-648)
2. Looks up ticker in chart_manifest.json
3. If found: reads PNG, encodes to base64, embeds as `<img src="data:image/png;base64,..."/>`
4. If not in manifest: searches `trades/charts/{TICKER}_*.png` directly
5. If no file found: renders placeholder box with "Chart image will be added here"

**Missing chart reporting** (lines 925-934):
```
⚠️ Charts missing: BTDR, RMBS
   Run: python chart_capture.py --ticker BTDR RMBS
```

### 3.7 Chart Embedding in Tweets (tweet_generator.py:1889-1913)

Tweet objects include `image_path` field populated from chart_manifest.
During posting, `twitter_poster.py:367-390` uploads via v1.1 API and attaches to tweet.

### 3.8 Limitations

- **Not CI-compatible:** TradingView requires authenticated Pro account login
- **Local only:** Charts captured via `run_local_friday.sh` after GitHub Actions workflow completes
- **Indicators hidden:** JavaScript injection removes indicator names for marketing compliance
- **Fallback:** If chart capture fails, newsletter shows placeholder boxes; tweets post without images (non-fatal)

---

## 4. Weekly Workflow Timeline

### 4.1 Complete Timeline Diagram

```
FRIDAY
═══════════════════════════════════════════════════════════════════

16:00 ET   US Market Close
              │
16:30 ET   GitHub Actions: friday_scan.yml triggers
              │
              ├─ Step 1: scanner.py --archive --web-search
              │    ├─ Load 1,817 tickers
              │    ├─ Download stock data (yfinance)
              │    ├─ Technical gate (Beta ≥1.5, BoS Up, Banker ≥55)
              │    ├─ Thematic analyzer (Claude + optional web search)
              │    ├─ Gatekeeper (Claude + web search per stock)
              │    ├─ Check sell signals on open positions
              │    ├─ Update portfolio.csv
              │    └─ Generate: signals.json, newsletter_briefing.md, report.txt
              │
              ├─ Step 3: market_analyzer.py --save
              │    └─ Generate: market_analysis.md (Claude + web search)
              │
              ├─ Step 4: newsletter_compiler.py --full
              │    ├─ Load: market_analysis + briefing + DD + portfolio
              │    ├─ LLM compile via Claude Sonnet 4
              │    ├─ Convert markdown → HTML with chart embedding
              │    └─ Generate: newsletter.html
              │
              ├─ Step 4.5: substack_content_generator.py --all
              │    └─ Generate: Mon/Thu/Sat/Sun Substack posts
              │
              ├─ Step 5: tweet_generator.py
              │    ├─ Generate 28-35 tweets for the week
              │    └─ Generate: content_queue.json
              │
              ├─ Step 5.5: substack_notes_generator.py
              │    └─ Generate: tuesday_note.md, thursday_note.md
              │
              ├─ Step 5b: tweet_generator.py --generate-variations
              │    └─ Generate: account2 + account3 queue files
              │
              ├─ Step 6: Upload artifacts to GitHub
              │
              └─ Step 7: git commit + push results
              │
~18:00 ET  GitHub Actions complete
              │
              ▼
         [LOCAL STEP - Manual]
         run_local_friday.sh
              │
              ├─ chart_capture.py --tickers-from signals.json --include-portfolio
              │    ├─ Launch Playwright browser (headless if session exists)
              │    ├─ Navigate to TradingView per ticker
              │    ├─ Screenshot charts (1400x900 + 1000x700)
              │    └─ Save chart_manifest.json
              │
              └─ git add trades/charts/ && git commit && git push


SATURDAY
═══════════════════════════════════════════════════════════════════

Morning    [MANUAL - ~10 minutes]
              │
              ├─ Open trades/current/newsletter.html in browser
              ├─ Copy rendered content to Substack editor
              ├─ Add TradingView chart screenshots at [CHART:] placeholders
              ├─ Preview formatting
              └─ Publish newsletter on Substack
              │
08:00 ET   daily_post.yml Slot 1 → top_performers tweet
10:00 ET   daily_post.yml Slot 2 → thread_buy_signal (5-tweet)
12:30 ET   daily_post.yml Slot 3 → theme_hot tweet
15:30 ET   daily_post.yml Slot 4 → funnel_graphic tweet
18:00 ET   daily_post.yml Slot 5 → engagement tweet


SUNDAY
═══════════════════════════════════════════════════════════════════

              Daily tweet posting continues (5 slots)


MONDAY
═══════════════════════════════════════════════════════════════════

              Daily tweet posting continues (5 slots)


TUESDAY
═══════════════════════════════════════════════════════════════════

              Daily tweet posting continues (5 slots)
              │
              └─ [MANUAL - ~2 minutes]
                   ├─ Open trades/current/substack_notes/tuesday_note.md
                   ├─ Copy to Substack Notes editor
                   └─ Publish "Portfolio Pulse" note


WEDNESDAY
═══════════════════════════════════════════════════════════════════

              Daily tweet posting continues (5 slots)


THURSDAY
═══════════════════════════════════════════════════════════════════

              Daily tweet posting continues (5 slots)
              │
              └─ [MANUAL - ~2 minutes]
                   ├─ Open trades/current/substack_notes/thursday_note.md
                   ├─ Copy to Substack Notes editor
                   └─ Publish "Trade Spotlight" note


FRIDAY (NEXT)
═══════════════════════════════════════════════════════════════════

              Cycle repeats
```

### 4.2 Manual vs Automated Breakdown

| Task | Time | Automated | Manual Effort |
|------|------|-----------|---------------|
| Full scan pipeline | Friday 16:30 ET | Yes (GitHub Actions) | 0 min |
| Chart capture | Friday ~18:00 ET | Semi (local script) | ~5 min |
| Newsletter publish | Saturday AM | No | ~10 min |
| Daily tweets (5/day) | Mon-Sun, 5 slots | Yes (GitHub Actions) | 0 min |
| Tuesday Substack Note | Tuesday | No | ~2 min |
| Thursday Substack Note | Thursday | No | ~2 min |
| **Total manual effort** | | | **~19 min/week** |

### 4.3 Manual Approval Gates

**There are no manual approval gates in the pipeline.** All content is generated and posted automatically. The only manual steps are:

1. **Newsletter publication** — user copies HTML to Substack editor
2. **Substack Notes** — user copies markdown to Substack Notes
3. **Chart capture** — user runs local script (requires TradingView login)

There is no review/approval step between content generation and tweet posting. Safeguards are enforced programmatically via the 4-layer validation system documented in [05-twitter-automation.md](05-twitter-automation.md).

---

## 5. Substack Integration

### 5.1 Current State: No API Integration

There is **no automated Substack publishing**. The system generates publication-ready content but requires manual copy-paste to Substack.

**Why:** Substack has no public API. The codebase documents three potential approaches (CLAUDE.md):

| Approach | Feasibility | Status |
|----------|-------------|--------|
| Email-to-publish | High | Not implemented |
| Browser automation | Medium | Not implemented |
| Substack API | Low | No public API exists |

### 5.2 Draft Creation Process

**Newsletter (Saturday):**
1. `newsletter_compiler.py --full` generates `trades/current/newsletter.html`
2. HTML includes inline CSS, tables, chart embeds (base64)
3. User opens HTML in browser, copies rendered content
4. Pastes into Substack rich text editor
5. Adds any missing TradingView chart screenshots manually
6. Publishes

**Substack Notes (Tuesday/Thursday):**
1. Pre-generated markdown files in `trades/current/substack_notes/`
2. User copies markdown content
3. Pastes into Substack Notes editor
4. Publishes

### 5.3 Formatting Conversion (newsletter_compiler.py:528-677)

Custom markdown-to-HTML converter handles:

| Element | Markdown | HTML |
|---------|----------|------|
| Headers | `# text` | `<h1>` through `<h4>` |
| Bold | `**text**` | `<strong>` |
| Italic | `*text*` | `<em>` |
| Tables | Pipe tables | `<table>` with `<thead>`/`<tbody>` |
| Lists | `- item` | `<ul><li>` |
| Blockquotes | `> text` | `<blockquote>` (multi-line safe) |
| Charts | `[CHART: TICKER]` | `<img>` with base64 or placeholder |
| Links | `[text](url)` | `<a href>` |

**HTML template** (lines 684-773) includes:
- Responsive CSS (max-width 680px body)
- Color classes: `.pass` (green), `.caution` (orange), `.fail` (red)
- Table styling with borders and padding
- Substack-friendly image max-width: 100%
- Footer with disclaimer and subscribe link

### 5.4 Subscriber Segmentation

**Current state: No segmentation.** All content is free-tier Substack. There is no paywall implementation.

**Selective visibility rules apply to ALL public content:**

| Element | Threshold | Shown Publicly |
|---------|-----------|----------------|
| Winning trades | >= 15% gain | Yes |
| Losing trades | Any | No |
| Stopped positions | Any | No |
| Entry prices (open) | >= 25% gain | Yes |
| Entry prices (open, < 25%) | — | No |
| Beat SPY comparison | >= 5% outperformance | Yes |
| Beat SPY (underperforming) | — | Methodology focus instead |

---

## 6. Consistency Verification

### 6.1 Newsletter Content vs Twitter Posts

**Data source:** Both newsletter and tweets derive from the same `newsletter_briefing.md` and `signals.json` generated Friday.

| Aspect | Newsletter | Twitter | Consistent? |
|--------|-----------|---------|-------------|
| Signal list (TEAL) | All PASS signals shown | All PASS signals shown | Yes |
| Signal details | Full tables + DD | Brief summaries | N/A (different depth) |
| Portfolio P&L | Shown in briefing (internal) | Winners only (public) | Intentionally different |
| Win highlights | >= 15% threshold | >= 15% threshold | Yes |
| Themes | All classified themes | PRIME + INVESTABLE featured | Subset |
| Market context | Full 4-paragraph analysis | Not in tweets | N/A |
| Vocabulary | TEAL/AMBER/VIOLET branding | Same branding | Yes |
| Banned terms | Validated (marketing_vocabulary.py) | Validated (4-layer) | Yes |

**Inconsistency risk (C-1):** Newsletter briefing includes full portfolio table with losing positions (for internal use). The LLM compilation system prompt instructs Claude to suppress losses, but this relies on LLM compliance rather than programmatic enforcement.

### 6.2 Newsletter Signals vs Internal Tracking

| Aspect | Newsletter/Briefing | Internal (portfolio.csv) | Consistent? |
|--------|-------------------|--------------------------|-------------|
| PASS signals | Listed with full metadata | Added to portfolio.csv as OPEN | Yes |
| Entry prices | Shown in briefing tables | Stored in entry_price field | Yes |
| Exit signals | BoS Down / stop alerts listed | Status updated to STOPPED/CLOSED | Yes |
| Win rate | Calculated from closed trades | Same formula | Yes |
| P&L formula | `((price/entry) - 1) * 100` | Same formula | Yes |

### 6.3 Stated Performance vs Actual Performance

| Metric | Newsletter Source | Actual Source | Notes |
|--------|-----------------|---------------|-------|
| Unrealized P&L | yfinance live prices | yfinance live prices | Same source — consistent |
| Realized P&L | portfolio.csv exit_price | portfolio.csv exit_price | Same source — consistent |
| Win rate | Closed trades in portfolio.csv | Same | Consistent |
| SPY comparison | yfinance SPY YTD | yfinance SPY YTD | **Flawed methodology** (see audit 04) |
| Dollar P&L | Assumes 100 shares/position | Hard-coded 100 shares | Not real position sizing |

**Key discrepancy:** The SPY benchmark comparison uses different methodologies depending on context:
- Newsletter: YTD portfolio return vs YTD SPY return (non-matched periods)
- Signal tracker: Average open P&L vs 30-day SPY (also non-matched)
- Neither uses holding-period-matched returns

This was documented as HIGH severity in [04-pnl-calculation.md](04-pnl-calculation.md) (D-1, D-2).

### 6.4 Marketing Safeguards in Newsletter

**LLM system prompt rules** (newsletter_compiler.py:75-90):
1. NEVER mention losing positions or underwater trades
2. NEVER show full portfolio with individual P&L
3. Only showcase wins above 15% threshold
4. If benchmark negative → focus on methodology
5. Use "TEAL signal" branding
6. Zero signals week → "sometimes the best trade is no trade"

**Post-compilation validation** (lines 878-886):
```python
if MARKETING_VOCABULARY_AVAILABLE:
    is_valid, violations = validate_content(md_content)
    if not is_valid:
        print(f"⚠️ WARNING: Newsletter contains banned terms: {violations}")
```

This is a warning-level check. It does not block publication.

---

## 7. Substack Notes (Mid-Week)

### 7.1 Tuesday Note — "Portfolio Pulse" (substack_notes_generator.py:221-279)

**Content:**
- Hot themes (PRIME only, top 3)
- TEAL signal count
- Win highlights (15%+ gains only)
- Scanner statistics funnel
- Disclaimer footer

**Data sources:** `signals.json`, `portfolio.csv`, live yfinance prices

### 7.2 Thursday Note — "Trade Spotlight" (substack_notes_generator.py:282-378)

**Content:**
- All TEAL signals (full list)
- Featured signal deep dive (highest conviction)
- Watchlist signals as fallback
- Scanner statistics
- Top winner showcase (15%+ threshold)
- Disclaimer footer

**Data sources:** Same as Tuesday

### 7.3 Output Paths

```
trades/current/substack_notes/tuesday_note.md
trades/current/substack_notes/thursday_note.md
trades/weeks/YYYY-WXX/substack_notes/tuesday_note.md
trades/weeks/YYYY-WXX/substack_notes/thursday_note.md
```

### 7.4 Marketing Safeguards in Notes

- No portfolio P&L display (substack_notes_generator.py:226)
- Winners above 15% only (lines 259, 366)
- No losing positions mentioned (line 361)
- Validates against banned marketing terms (lines 388-392)

---

## 8. Substack Posts (Extended Content)

### 8.1 Content Types (substack_content_generator.py)

| Day | Post Type | Content |
|-----|-----------|---------|
| Monday | Market Analysis | Top themes, portfolio highlights (winners), sector flows |
| Thursday | Theme Spotlight | Deep dive on top PRIME/INVESTABLE theme, TEAL signals in theme |
| Saturday | Weekly Signals Recap | All TEAL/AMBER/VIOLET signals, scan statistics |
| Sunday | Deep Dive | Single stock analysis (highest conviction TEAL signal) |

### 8.2 Color Signal Branding

Used consistently across all Substack content:

| Color | Internal Term | Public Term | Meaning |
|-------|--------------|-------------|---------|
| 🟢 TEAL | PASS / TRADE | TEAL Signal | Cleared all 5 gates — ready for entry |
| 🟡 AMBER | CONSIDER / CAUTION | AMBER Watch | Cleared 4/5 gates — watchlist |
| 🟣 VIOLET | Sell Signal | VIOLET Alert | Systematic exit triggered |
| 🔴 RED | STOPPED | (not shown) | Hit trailing stop — excluded from public |

### 8.3 Output Path

```
trades/substack_posts/
├── monday_market_analysis_YYYYMMDD.md
├── thursday_theme_spotlight_YYYYMMDD.md
├── saturday_weekly_signals_YYYYMMDD.md
└── sunday_deep_dive_YYYYMMDD.md
```

---

## 9. Concerns and Gaps

### C-1: Newsletter Loss Suppression Relies on LLM Compliance (HIGH)

**Location:** newsletter_compiler.py:75-90

The newsletter briefing (Stage 1) contains full portfolio data including losing positions. The LLM system prompt instructs Claude to suppress losses, but this is a **soft enforcement**. There is no programmatic filter between the briefing data and the compiled output. If the LLM fails to follow instructions, losses could appear in the published newsletter.

**Contrast with tweets:** Tweet validation has 4 layers of programmatic enforcement including regex-based negative P&L blocking.

**Recommendation:** Add post-compilation regex check for negative P&L patterns, similar to tweet validation.

### C-2: No Automated Substack Publishing (MEDIUM)

**Impact:** Every publication requires manual copy-paste (~10 min Saturday + ~2 min Tuesday + ~2 min Thursday = ~14 min/week manual effort).

**Status:** Email-to-publish approach documented in CLAUDE.md but not implemented.

### C-3: Chart Capture Requires Local Execution (MEDIUM)

**Location:** chart_capture.py (entire file)

Charts cannot be captured in GitHub Actions CI because TradingView requires authenticated Pro account login. The user must run `run_local_friday.sh` locally after the GitHub Actions workflow completes.

**Impact:** If user forgets or is unavailable, newsletter publishes with placeholder boxes instead of charts.

### C-4: Newsletter Validation is Warning-Only (MEDIUM)

**Location:** newsletter_compiler.py:878-886

The marketing vocabulary validation after newsletter compilation only prints warnings. It does not block or fix violations. Unlike tweet validation which has auto-fix and rejection, newsletter violations require manual review.

### C-5: Stale Data in Mid-Week Notes (LOW)

**Location:** substack_notes_generator.py

Tuesday and Thursday notes are generated Friday evening but published Tuesday/Thursday. Signal data could be 4-6 days old. No freshness check or price update mechanism exists for the notes.

### C-6: No Version Control for Published Content (LOW)

Published newsletter content (what actually appears on Substack) is not tracked. Only the generated HTML is archived in `trades/weeks/`. If the user modifies content during manual Substack publishing, the modification is not captured.

### C-7: HTML Conversion is Custom (Not Standard Library) (LOW)

**Location:** newsletter_compiler.py:528-677

The markdown-to-HTML converter is hand-rolled rather than using a standard library like `markdown` or `mistune`. Edge cases in markdown formatting could produce incorrect HTML. Notable: no support for inline code, code blocks, or horizontal rules in the custom converter.

### C-8: DD Integration Depends on signals.json Field Names (LOW)

**Location:** newsletter_compiler.py:303-325

DD fields are accessed by specific key names (`dd_verdict`, `dd_conviction`, etc.) from `signals.json`. If `dd_automator.py` changes field names, the newsletter silently shows no DD content (falls back to `"[DD not yet run]"`).

---

## Appendix: File Output Map

```
trades/
├── current/
│   ├── newsletter_briefing.md      ← scanner.py (Stage 1)
│   ├── newsletter.html             ← newsletter_compiler.py (Stage 2)
│   ├── signals.json                ← scanner.py
│   ├── market_analysis.md          ← market_analyzer.py
│   ├── substack_notes/
│   │   ├── tuesday_note.md         ← substack_notes_generator.py
│   │   └── thursday_note.md        ← substack_notes_generator.py
│   └── charts/
│       └── chart_manifest.json     ← chart_capture.py
│
├── weeks/
│   └── 2026-WXX/                   ← Archived copies of all above
│
├── substack_posts/
│   ├── monday_market_analysis_YYYYMMDD.md    ← substack_content_generator.py
│   ├── thursday_theme_spotlight_YYYYMMDD.md
│   ├── saturday_weekly_signals_YYYYMMDD.md
│   └── sunday_deep_dive_YYYYMMDD.md
│
├── charts/
│   ├── {TICKER}_{YYYYMMDD}.png              ← chart_capture.py (X size)
│   ├── {TICKER}_{YYYYMMDD}_substack.png     ← chart_capture.py (Substack size)
│   └── chart_manifest.json
│
├── market_analysis.md              ← Legacy location
├── latest_newsletter_briefing.md   ← Legacy symlink
├── latest_newsletter.html          ← Legacy copy
└── portfolio.csv                   ← Source of truth
```

---

*End of audit document.*
