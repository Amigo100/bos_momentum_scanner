# Sterling Signals Newsletter Generation System Audit

**Audit Date:** 2026-01-27
**Auditor:** Claude Opus 4.5
**Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Newsletter Structure](#newsletter-structure)
3. [Content Generation Flow](#content-generation-flow)
4. [TradingView Chart Integration](#tradingview-chart-integration)
5. [Weekly Workflow](#weekly-workflow)
6. [Substack Integration](#substack-integration)
7. [Consistency Verification](#consistency-verification)
8. [Weekly Timeline Diagram](#weekly-timeline-diagram)
9. [Findings and Recommendations](#findings-and-recommendations)

---

## Executive Summary

The Sterling Signals newsletter generation system is a **semi-automated pipeline** that transforms scanner outputs into publication-ready content for Substack. The system uses:

- **LLM-powered compilation** via Claude Sonnet 4
- **Marketing vocabulary validation** for compliance
- **Chart integration** via TradingView (manual) or mplfinance (automated)
- **Cross-platform consistency** between newsletter, tweets, and Substack Notes

**Key Finding:** The system is ~85% automated, requiring only 14 minutes of manual work per week for publishing.

---

## Newsletter Structure

### Standard Sections (In Order)

| # | Section | Source | Automated |
|---|---------|--------|-----------|
| 1 | **Title & Hook** | LLM-generated based on week's theme | Yes |
| 2 | **Market Context** | `market_analyzer.py` + Claude web search | Yes |
| 3 | **Hot Themes** | `signals.json` - PRIME/INVESTABLE themes | Yes |
| 4 | **Cold Themes** | `signals.json` - SELECTIVE/AVOID themes | Yes |
| 5 | **New Trades (TEAL Signals)** | `signals.json` - PASS decisions | Yes |
| 6 | **Signals That Failed DD** | `signals.json` - FAIL decisions | Yes |
| 7 | **Watchlist** | `signals.json` - CAUTION decisions | Yes |
| 8 | **Win Highlights** | `portfolio.csv` - 15%+ gains only | Yes |
| 9 | **Looking Ahead** | LLM-generated | Yes |
| 10 | **Footer/Disclaimer** | Static template | Yes |

### Section Details

#### 1. Title & Hook
- **Template:** `Week ${WEEK_NUM}: ${NEW_SIGNALS} TEAL Signals | ${HOOK_PHRASE}`
- **Example:** "Week 4: 3 TEAL Signals | Why Power Grid is 2026's Winning Theme"
- **Zero-signal variant:** "Week ${WEEK_NUM}: No New Signals | ${THEME_HOOK}"

#### 2. Market Context
- Generated via `market_analyzer.py` using Claude + web search
- Topics: Index performance, Fed/macro events, sector rotation, VIX
- Output: `trades/current/market_analysis.md`

#### 3-4. Themes (Hot/Cold)
- Extracted from `signals.json` themes array
- Classification: PRIME (>7.5), INVESTABLE (6.0-7.5), SELECTIVE (4.5-6.0), AVOID (<4.5)
- Includes: Score, thesis summary, key catalysts

#### 5. New Trades (TEAL Signals)
Each signal includes:
```markdown
#### $TICKER

| Metric | Value |
|--------|-------|
| Price | $XX.XX |
| Theme | Theme Name (FIT LEVEL) |
| Tier | TIER1/2/3 |
| Conviction | ★★★★☆ |

**Bullish Factors:** [list]
**Risk Factors:** [list]
**Analysis:** [paragraph]
**Recommended Action:** [specific action]

[CHART: TICKER]
```

#### 8. Win Highlights
- **Marketing Rule:** Only shows closed trades with 15%+ gains
- **Never shows:** Losing positions, underwater trades, individual P&L for open positions
- Source: `portfolio.csv` filtered by `load_portfolio_status()` at `newsletter_compiler.py:328`

### Zero-Signal Week Handling

When no PASS signals exist (`newsletter_compiler.py:86-91`):
- Section 5 replaced with "NO NEW SIGNALS THIS WEEK"
- Emphasizes system selectivity as a feature
- Highlights watchlist stocks that almost qualified
- Subject line focuses on themes instead of signals

---

## Content Generation Flow

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SCANNER.PY (Friday 4:30 PM ET)                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Output: signals.json, newsletter_briefing.md, portfolio.csv            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ market_       │   │ newsletter_   │   │ tweet_        │
        │ analyzer.py   │   │ compiler.py   │   │ generator.py  │
        └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
                │                   │                   │
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ market_       │   │ newsletter.   │   │ content_      │
        │ analysis.md   │   │ html          │   │ queue.json    │
        └───────┬───────┘   └───────┴───────┘   └───────┬───────┘
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ Substack      │   │ Substack      │   │ X/Twitter     │
        │ Newsletter    │   │ Notes         │   │ Posts         │
        │ (Saturday)    │   │ (Tue/Thu)     │   │ (Daily)       │
        └───────────────┘   └───────────────┘   └───────────────┘
```

### Step-by-Step Generation

#### Step 1: Load Scanner Briefing
```python
# newsletter_compiler.py:261-276
def load_scanner_briefing() -> str:
    """Load the scanner briefing file."""
    # Try current/ folder first, then legacy location
    briefing_file = current_dir / "newsletter_briefing.md"
    # Returns markdown with themes, signals, recommendations
```

#### Step 2: Load Market Analysis
```python
# newsletter_compiler.py:237-258
def load_market_analysis() -> str:
    """Load the market analysis file."""
    # Generated by market_analyzer.py using Claude + web search
    # Contains: Index performance, macro events, sector rotation
```

#### Step 3: Load DD Results
```python
# newsletter_compiler.py:279-325
def load_dd_results() -> tuple[str, int]:
    """Load DD results from signals.json."""
    # Extracts: dd_verdict, dd_conviction, dd_position_size
    # Counts PASS signals (TRADE for backwards compatibility)
```

#### Step 4: Load Portfolio Status (Winners Only)
```python
# newsletter_compiler.py:328-389
def load_portfolio_status() -> str:
    """Load WIN HIGHLIGHTS only (no portfolio display per marketing overhaul)."""
    # Filter: status in ['CLOSED', 'STOPPED']
    # Filter: pnl_pct >= 15.0 (MARKETING_THRESHOLDS['min_win_to_highlight'])
    # Returns: Top 5 winners sorted by P&L
```

#### Step 5: LLM Compilation
```python
# newsletter_compiler.py:192-230
def compile_newsletter_llm(...) -> str:
    """Use Claude to compile the full newsletter."""
    # Model: claude-sonnet-4-20250514
    # Max tokens: 6000
    # System prompt: COMPILATION_SYSTEM (62-103)
    # User prompt: COMPILATION_PROMPT (105-189)
```

#### Step 6: Marketing Validation
```python
# newsletter_compiler.py:879-886
if MARKETING_VOCABULARY_AVAILABLE:
    is_valid, violations = validate_content(md_content)
    if not is_valid:
        print(f"WARNING: Newsletter contains banned terms: {violations}")
```

#### Step 7: Markdown to HTML Conversion
```python
# newsletter_compiler.py:528-677
def markdown_to_html(md_content: str, chart_manifest: Dict) -> str:
    """Convert markdown to Substack-friendly HTML with embedded charts."""
    # Converts: headers, bold, italic, blockquotes, tables, lists
    # Handles: [CHART: TICKER] placeholders
```

---

## TradingView Chart Integration

### Overview

Charts are captured using Playwright browser automation with TradingView Pro account authentication.

**Key File:** `chart_capture.py`
**Output Directory:** `trades/charts/`
**Manifest:** `trades/charts/chart_manifest.json`

### Chart Sizes

| Size | Dimensions | Purpose |
|------|------------|---------|
| X/Twitter | 1400 x 900 | Tweet media cards |
| Substack | 1000 x 700 | Newsletter embeds |

### Capture Process

```python
# chart_capture.py:122-210
def capture_chart(page, ticker, output_dir, date_str, sizes):
    # 1. Navigate to TradingView with saved layout
    url = f"https://www.tradingview.com/chart/{TRADINGVIEW_LAYOUT_ID}/?symbol={ticker}"

    # 2. Wait for page and indicators to load
    page.wait_for_timeout(PAGE_LOAD_WAIT_MS)     # 8000ms
    page.wait_for_timeout(INDICATOR_LOAD_WAIT_MS) # 10000ms

    # 3. Hide UI elements (keep indicators visible)
    page.evaluate(HIDE_UI_ELEMENTS_JS)

    # 4. Capture screenshots at each size
    for width, height in sizes:
        page.set_viewport_size({"width": width, "height": height})
        chart_element.screenshot(path=str(filepath))
```

### Authentication Flow

1. **First Run (Interactive):**
   ```bash
   python chart_capture.py --ticker GLXY
   # Opens browser window for manual TradingView login
   # Saves session to .playwright_profile/
   ```

2. **Subsequent Runs (Headless):**
   ```bash
   python chart_capture.py --tickers AAPL,NVDA --headless --skip-wait
   # Uses saved session from .playwright_profile/
   ```

3. **Session Persistence:**
   - Profile saved in `.playwright_profile/`
   - Cookies can be exported to `.tradingview_cookies.json`
   - Session typically lasts 30-90 days

### Chart Embedding in Newsletter

```python
# newsletter_compiler.py:614-644
def convert_chart(match):
    ticker = match.group(1)
    chart_base64 = get_chart_as_base64(ticker, chart_manifest)

    if chart_base64:
        # Embed as base64 image
        return f'<img src="data:image/png;base64,{chart_base64}" ...>'
    else:
        # Show placeholder box
        return '<div class="chart-placeholder">Chart image will be added here</div>'
```

### CI Limitations

**TradingView charts CANNOT be captured in CI** due to:
- Interactive login requirement
- No GUI available in GitHub Actions
- Custom indicators require authenticated session

**Workaround:** Run `chart_capture.py` locally after Friday scan completes.

---

## Weekly Workflow

### Automation vs Manual Steps

| Step | Automated | Manual | Time |
|------|-----------|--------|------|
| Friday scan | Yes (GitHub Actions) | - | 90 min |
| Market analysis | Yes | - | 5 min |
| Newsletter compilation | Yes | - | 10 min |
| Tweet generation | Yes | - | 10 min |
| Substack Notes | Yes | - | 5 min |
| Chart capture | - | Yes | 10 min |
| Newsletter publish | - | Yes | 10 min |
| Tuesday Note publish | - | Yes | 2 min |
| Thursday Note publish | - | Yes | 2 min |

**Total Automated Time:** ~2.5 hours
**Total Manual Time:** ~24 minutes/week

### GitHub Actions Workflows

#### friday_scan.yml (`.github/workflows/friday_scan.yml`)

**Trigger:** Friday 4:30 PM ET (21:30 UTC)

**Steps:**
1. Run Scanner (technical → thematic → gatekeeper → DD)
2. Generate Market Analysis (Claude + web search)
3. Compile Newsletter (LLM full assembly)
4. Generate Tweets (35 for the week)
5. Generate Substack Notes (Tuesday + Thursday)
6. Upload Artifacts
7. Commit & Push Results
8. Generate Summary
9. Failure Notification (email)

**Key Configuration:**
```yaml
schedule:
  - cron: '30 21 * * 5'  # Friday 4:30 PM ET

env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### daily_post.yml

**Trigger:** 5 times daily (Eastern Time)

| Slot | Time (ET) | UTC Cron | Content Type |
|------|-----------|----------|--------------|
| 1 | 08:00 | `0 13 * * *` | Pre-market |
| 2 | 10:00 | `0 15 * * *` | Morning |
| 3 | 12:30 | `30 17 * * *` | Midday |
| 4 | 15:30 | `30 20 * * *` | **Power Hour** |
| 5 | 18:00 | `0 23 * * *` | After-hours |

---

## Substack Integration

### Current State: Manual Copy-Paste

**Substack does not offer a public API for publishing.** The current workflow is:

1. **Newsletter (Saturday):**
   - Open `trades/current/newsletter.html` in browser
   - Copy content to Substack editor
   - Add any missing charts manually
   - Preview and publish

2. **Substack Notes (Tuesday/Thursday):**
   - Open `trades/current/substack_notes/tuesday_note.md`
   - Copy to Substack Notes interface
   - Publish

### Draft Creation Process

There is **no unofficial API usage** in the current implementation. All Substack interactions are manual.

### Potential Future Options

| Option | Feasibility | Notes |
|--------|-------------|-------|
| Email-to-Publish | High | Substack supports `publication@mg.substack.com` |
| Browser Automation | Medium | Playwright/Selenium, fragile |
| Substack API | Low | No public API available |

### Formatting Conversion

The `markdown_to_html()` function (`newsletter_compiler.py:528-677`) handles:

- Headers (H1-H4)
- Bold/Italic
- Blockquotes
- Tables (markdown → HTML table)
- Unordered lists
- Chart placeholders

**Note:** Substack uses its own styles, so preview may differ from final appearance.

### Subscriber Segmentation

The current system does **not** implement free vs paid content segmentation. All newsletter content is published to all subscribers.

**Potential Implementation:**
- Add `subscriber_tier` field to content sections
- Wrap premium content in Substack's paywall markers
- Modify compilation prompt to designate sections

---

## Consistency Verification

### Content Validation Pipeline

All public-facing content passes through `marketing_vocabulary.py`:

```python
# marketing_vocabulary.py:25-61
BANNED_TERMS = [
    # Technical indicators (never expose)
    "HMA", "Banker indicator", "BoS", "Beta >= 1.5",
    "20% trailing stop", "Gatekeeper", "Tier 1/2/3",

    # Non-branded terms
    "buy signal", "PASS signal",  # Use "TEAL signal" instead

    # Region-specific (audience-neutral)
    "Roth IRA", "PDT", "UK ISA", "GMT", "BST"
]
```

### Newsletter ↔ Twitter Consistency

| Check | Implementation | Location |
|-------|----------------|----------|
| Same TEAL signals | Both read from `signals.json` | `tweet_generator.py:252` |
| Same themes | Both read from `signals.json` | `newsletter_compiler.py:300` |
| Same win highlights | Both filter `portfolio.csv` 15%+ | `tweet_generator.py:98` |
| Banned terms | `validate_content()` called | Both files |

### Newsletter ↔ Internal Tracking

| Data Point | Newsletter Source | Internal Source | Consistency |
|------------|-------------------|-----------------|-------------|
| PASS signals | `signals.json` → `buy_signals[]` | `signals.json` | Same file |
| Themes | `signals.json` → `themes[]` | `signals.json` | Same file |
| Portfolio P&L | `portfolio.csv` | `portfolio.csv` | Same file |
| Win rate | Calculated from `portfolio.csv` | Same calculation | Verified |

### Stated vs Actual Performance

**Safeguards in place:**

1. **Winners-only display** (`load_portfolio_status()`):
   - Only shows closed trades with 15%+ gains
   - Never shows losing positions publicly

2. **Benchmark comparison** (`generate_benchmark_comparison()`):
   - Calculates actual portfolio return vs SPY
   - If underperforming, focuses on methodology
   - Code at `newsletter_compiler.py:459-485`

3. **Live price verification** (Substack Notes):
   - Fetches current prices via yfinance
   - Calculates accurate P&L at generation time
   - Code at `substack_notes_generator.py:116-135`

### Audit Trail

All outputs include timestamps for verification:
- `signals.json`: `"timestamp": "2026-01-24 22:06:24"`
- `chart_manifest.json`: `"captured_at": "2026-01-24T23:15:30"`
- Newsletter: Generated date in footer

---

## Weekly Timeline Diagram

```
FRIDAY (Automated)
══════════════════════════════════════════════════════════════════════════

     4:00 PM ET   4:30 PM ET                    ~7:00 PM ET    After close
         │            │                              │              │
         ▼            ▼                              ▼              ▼
    Market Close  ┌─────────────────────────────────────┐      Local Run
                  │     GITHUB ACTIONS: friday_scan     │      ┌─────────┐
                  │                                     │      │ Chart   │
                  │  1. Scanner (90 min)                │      │ Capture │
                  │  2. Market Analysis (5 min)         │      │ (local) │
                  │  3. Newsletter Compile (10 min)     │      └─────────┘
                  │  4. Tweet Generation (10 min)       │
                  │  5. Substack Notes (5 min)          │
                  │  6. Git Commit & Push               │
                  └─────────────────────────────────────┘


SATURDAY (Manual)
══════════════════════════════════════════════════════════════════════════

         Morning                    Publish
             │                         │
             ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Review newsletter   │   │ Copy to Substack    │
    │ - Check HTML output │   │ - Add any charts    │
    │ - Verify charts     │   │ - Preview           │
    │ - Read for errors   │   │ - Click Publish     │
    └─────────────────────┘   └─────────────────────┘
          ~10 min                    ~5 min


SUNDAY - FRIDAY (Automated)
══════════════════════════════════════════════════════════════════════════

     Daily Tweet Posting via daily_post.yml
     ═══════════════════════════════════════

         08:00 ET    10:00 ET    12:30 ET    15:30 ET    18:00 ET
             │           │           │           │           │
             ▼           ▼           ▼           ▼           ▼
          ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐
          │ #1  │    │ #2  │    │ #3  │    │ #4  │    │ #5  │
          │Pre- │    │Theme│    │Chart│    │Power│    │Wrap │
          │mkt  │    │ DD  │    │Post │    │Hour │    │Up   │
          └─────┘    └─────┘    └─────┘    └─────┘    └─────┘
                                         (CRITICAL)


TUESDAY (Manual)
══════════════════════════════════════════════════════════════════════════

         Any time
             │
             ▼
    ┌────────────────────────────┐
    │ Post Substack Note         │
    │ - Open tuesday_note.md     │
    │ - Copy to Substack Notes   │
    │ - Publish                  │
    └────────────────────────────┘
              ~2 min


THURSDAY (Manual)
══════════════════════════════════════════════════════════════════════════

         Any time
             │
             ▼
    ┌────────────────────────────────┐
    │ Post Substack Note             │
    │ - Open thursday_note.md        │
    │ - Copy to Substack Notes       │
    │ - Publish                      │
    └────────────────────────────────┘
                ~2 min


COMPLETE WEEKLY FLOW
══════════════════════════════════════════════════════════════════════════

Fri     Sat     Sun     Mon     Tue     Wed     Thu     Fri
 │       │       │       │       │       │       │       │
 ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐
│GHA│   │PUB│   │ 5 │   │ 5 │   │ 5 │   │ 5 │   │ 5 │   │GHA│
│   │   │NL │   │TWT│   │TWT│   │TWT│   │TWT│   │TWT│   │   │
│CHT│   │   │   │   │   │   │   │+NT│   │   │   │+NT│   │   │
└───┘   └───┘   └───┘   └───┘   └───┘   └───┘   └───┘   └───┘

Legend:
  GHA = GitHub Actions (friday_scan)
  CHT = Chart capture (local)
  PUB = Publish newsletter (manual)
  NL  = Newsletter
  TWT = 5 tweets posted automatically
  NT  = Substack Note (manual)
```

---

## Findings and Recommendations

### Strengths

1. **High automation level** (~85% automated)
2. **Strong marketing compliance** via vocabulary validation
3. **Consistent data sourcing** from single `signals.json`
4. **Winners-only display** prevents embarrassing public losses
5. **LLM-powered compilation** produces professional output
6. **Clear audit trail** with timestamps

### Gaps Identified

| Gap | Severity | Current State | Recommendation |
|-----|----------|---------------|----------------|
| No Substack API | Medium | Manual copy-paste | Evaluate email-to-publish option |
| Chart capture manual | Low | Requires local run | Document workflow clearly |
| No paid tier support | Low | All content free | Add segmentation if monetizing |
| DST handling | Low | Posts 1hr early in EDT | Document in workflow |
| No performance dashboard | Medium | Manual P&L tracking | Build automated tracking |

### Security Considerations

1. **Entry prices hidden** - Never exposed in public content (`CRIT-12.4`)
2. **API keys in secrets** - Not hardcoded
3. **Marketing terms blocked** - `validate_content()` prevents leaks
4. **Cookie file permissions** - Should be 0o600 restricted

### Recommended Improvements

1. **Priority 1:** Add email-to-publish for Substack automation
2. **Priority 2:** Create performance dashboard for tracking actual vs stated
3. **Priority 3:** Add DST-aware cron scheduling
4. **Priority 4:** Implement subscriber segmentation for paid tiers

---

## File Reference

| File | Purpose | Key Functions |
|------|---------|---------------|
| `newsletter_compiler.py` | Main compiler | `compile_newsletter_llm()`, `markdown_to_html()` |
| `substack_notes_generator.py` | Mid-week notes | `generate_tuesday_note()`, `generate_thursday_note()` |
| `chart_capture.py` | TradingView screenshots | `capture_chart()`, `capture_charts()` |
| `tweet_generator.py` | Weekly tweets | `generate_tweets()`, `validate_tweet_before_queue()` |
| `marketing_vocabulary.py` | Content validation | `validate_content()`, `BANNED_TERMS` |
| `market_analyzer.py` | Market context | `run_market_analysis()` |
| `.github/workflows/friday_scan.yml` | Friday automation | Scanner → Newsletter → Tweets |
| `.github/workflows/daily_post.yml` | Daily tweeting | 5 posts/day at scheduled times |

---

*End of Newsletter Generation System Audit*
