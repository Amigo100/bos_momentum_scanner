# Sterling Signals -- Substack Content Strategy

> Internal playbook for content generation, scheduling, and publishing.
> All content must comply with marketing rules in `config/banned_terms.py`.
> Last updated: February 2026

---

## 1. Positioning

**What we are:** A systematic, small-cap momentum scanner that filters 1,800 US stocks down to 3-5 actionable signals per week using a proprietary 5-gate screening system.

**What we publish about:** Small-cap momentum, multibagger candidates, growth stocks, and the themes driving institutional capital flows.

**Target audience:** US active investors, swing traders, and Roth IRA builders who want a data-driven alternative to gut-feel stock picking.

**Core message:** "No ego, just execution." The system screens, the system signals, the system exits. Emotions stay at the door.

**Voice:** Medical-investor -- clinical precision meets conviction. We diagnose trends the way a specialist reads imaging: pattern recognition across multiple data points, no single data point drives a decision, and every treatment (position) has a defined exit protocol. Calm, authoritative, occasionally sharp.

**Key differentiators for public messaging:**

- Proprietary 5-gate screening system (never name the gates publicly)
- Filters 1,800 stocks to 3-5 actionable signals weekly
- Institutional-grade momentum analysis
- Systematic approach that removes emotional bias
- Capital preservation protocol protects downside
- Full P&L transparency including losses

---

## 2. Content Types (4-Category Adaptive System)

Sterling Signals uses a **4-category adaptive system** (handbook v5) instead of fixed day-of-week assignments. The Friday pipeline generates an adaptive weekly schedule based on scanner output. Each day is assigned the most relevant category:

| Category | HTML Theme | When Assigned |
|----------|-----------|---------------|
| **Ticker Deep Dive** | Editorial (light) | New GREEN signal or portfolio winner to showcase |
| **Theme Rotation** | Dashboard (dark) | Active PRIME/INVESTABLE themes from scanner |
| **Educational** | Editorial (light) | Evergreen investing wisdom — fills remaining days |
| **Performance Review** | Dashboard (dark) | Always Sunday — weekly newsletter recap |

**How it works:** `content_production_guide.py` assigns categories adaptively. The operator opens the context document, sees today's category and topic, copies the matching prompt from handbook v5, and sends to Claude.ai (Opus 4.6 + extended thinking).

The system also supports **Trade Alert** prompts (Entry + Exit) that override the schedule when triggered.

Below are the detailed specifications for each content type.

---

### A. Weekly Flagship Newsletter (Saturday)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 1,500-2,500 |
| **Theme** | Dashboard (dark, teal accents) |
| **Data sources** | `signals.json`, `portfolio.csv`, `market_analysis.md`, `newsletter_briefing.md` |
| **Cadence** | Weekly, every Saturday |
| **Visual elements** | Theme cards with progress bars, funnel graphic, winners table, benchmark stat grid (NAV, return, alpha vs SPY, alpha vs NASDAQ, max drawdown), equity curve |
| **Module** | `python -m substack.newsletter_compiler --from-html` |

**Structure:**

1. Market Context -- macro backdrop, key moves, what the data says
2. Themes This Week -- PRIME/INVESTABLE/SELECTIVE/AVOID with composite scores
3. Signals -- new GREEN signals with thesis, catalysts, and risk factors
4. Portfolio -- open positions, P&L, stop distances, recent exits
5. Week Ahead -- catalysts on the calendar, themes to watch

**Notes:** This is the anchor content. It goes to inboxes. Every issue follows the same structure so subscribers know what to expect. Charts are inserted at `[CHART: TICKER]` placeholders after generation.

---

### B. Stock Deep Dives (1-2/week, Tuesday or Thursday)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 1,500-3,000 |
| **Theme** | Editorial (serif, light background) |
| **Data sources** | `signals.json`, `portfolio.csv`, Deep DD results, market data |
| **Cadence** | 1-2 per week when signals or portfolio winners justify it |
| **Visual elements** | Masthead, stat row (price, market cap, beta, sector), target banner (bear/base/bull), financial tables, catalyst timeline, callout boxes (neutral/warning/key), risk block, sources list, disclaimer |
| **Module** | `python -m substack.content_generator --dd` (or use Ticker Deep Dive prompt from handbook v5) |

**Structure:**

1. Business model and competitive position
2. Thesis -- what the system detected and why it matters
3. Catalysts -- upcoming events with dates and expected impact
4. Bear / Base / Bull scenarios with price context
5. Risk factors (honest, specific)
6. Our position (entry price shown only if gain exceeds 25%)

**Eligibility rules:**

- Stocks currently in portfolio showing positive performance
- Newly assessed signals that cleared the screening system
- Never write a deep dive for a position that is underwater

---

### C. Theme Deep Dives (1/week, Wednesday)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 1,000-2,000 |
| **Theme** | Dashboard (dark, teal accents) |
| **Data sources** | `signals.json` theme data, `market_analysis.md`, sector ETF data |
| **Cadence** | Weekly, Wednesday (PRIME theme gets priority) |
| **Visual elements** | Theme card with progress bars (catalyst, momentum, crowding, runway sub-scores), sector rotation bars, stat grid, related positions table |
| **Module** | `python -m substack.content_generator --theme` (or use Theme Rotation prompt from handbook v5) |

**Structure:**

1. Theme thesis -- what is happening and why
2. Scoring breakdown -- composite score with sub-score context (never reveal numeric methodology)
3. Catalysts -- what could accelerate or derail this theme
4. Sector rotation context -- where capital is flowing
5. Related positions -- which portfolio holdings are tied to this theme

---

### D. Quick-Take Market Commentary (1-2/week, event-driven)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 500-800 |
| **Theme** | Dashboard (dark, teal accents) |
| **Data sources** | Live market data, `portfolio.csv`, `market_analysis.md` |
| **Cadence** | As events warrant (Fed decisions, earnings surprises, macro shocks) |
| **Visual elements** | Stat grid (2-4 key numbers), pullquote, left-border card with key takeaway |
| **Module** | `python -m substack.content_generator --market` (or use Educational prompt from handbook v5) |

**Structure:**

1. What happened -- one paragraph, facts only
2. Why it matters -- interpretation through our systematic lens
3. How we are positioned -- relevant portfolio exposure and any triggered signals

**Notes:** Speed matters. Publish within hours of the event. Keep it short, opinionated, and end with an engagement question.

---

### E. Portfolio Showcases (1/week, Monday or Friday, when positive)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 800-1,500 |
| **Theme** | Dashboard (dark, teal accents) |
| **Data sources** | `portfolio.csv`, `portfolio_google_sheets.csv`, equity snapshots, SPY/QQQ benchmark data |
| **Cadence** | Weekly when portfolio is net positive |
| **Visual elements** | Stat grid (NAV, total return, alpha vs SPY, alpha vs NASDAQ, open positions, max drawdown), winners table with P&L, two-column thesis cards for top performers, equity curve with SPY/QQQ benchmarks |
| **Module** | `python -m substack.content_generator --portfolio` (or use Performance Review prompt from handbook v5) |

**Structure:**

1. Performance vs benchmarks -- hard numbers, no spin
2. Winners table -- positions above 15% gain with thesis recap
3. Theme distribution -- which themes are driving returns
4. Equity curve -- visual portfolio trajectory vs SPY and QQQ
5. Losses -- acknowledged directly, framed as "system working as designed"

**Entry price display rules:**

- Closed winners: Always show entry prices
- Open positions above 25% gain: Show entry prices
- Open positions below 25% gain: Do NOT show entry prices

---

### F. DD Posts per Signal (when signals exist)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 1,000-2,000 |
| **Theme** | Dashboard (dark, teal accents -- dedicated dark template) |
| **Data sources** | `signals.json` Deep DD results per PASS signal |
| **Cadence** | Generated per buy signal when the scanner produces PASS results |
| **Visual elements** | Header section with ticker and theme, stat boxes (price, market cap, sector, conviction language), highlight cards for The Pitch / Why Now / The Math, bear case card, risk factors list, theme context section with progress bars for sub-scores, action card |
| **Module** | `python -m substack.dd_post_generator` |

**Structure:**

1. The Pitch -- elevator pitch for the opportunity
2. Why Now -- timing catalysts and urgency
3. The Math -- valuation context, upside scenario
4. Bear Case -- what could go wrong (honest)
5. Risk to Monitor -- the single biggest risk
6. Theme Context -- how this stock fits the broader theme
7. Action -- what the system recommends

**Marketing safety:** All DD posts run through `INTERNAL_TERMINOLOGY_MAP` from `config/banned_terms.py` to replace any internal terms that may appear in LLM-generated analysis.

---

### G. Educational / Framework Posts (1-2/month, Sunday)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 800-1,200 |
| **Theme** | Editorial (serif, light background) |
| **Data sources** | `content/learning_content_library.py` (20 topics across 5 categories) |
| **Cadence** | 1-2 per month, typically Sunday |
| **Visual elements** | Masthead, callout boxes, stat rows, section headers |
| **Module** | `python -m substack.content_generator --educational` (or use Educational prompt from handbook v5) |

**Topic categories (4 topics each, 20 total):**

| Category | Topics |
|----------|--------|
| Risk Management | Position sizing, trailing stops, drawdown math, cash reserves |
| Momentum | Structural momentum, institutional accumulation, sector rotation, breadth signals |
| Fundamentals | Catalyst investing, revenue acceleration, theme alignment, small-cap edge |
| Psychology | Patience over FOMO, systematic discipline, loss acceptance, compounding math |
| Strategy | Screening advantage, theme surfing, when to sell, portfolio concentration |

**Voice:** Medical-investor analogies are strongest in educational content. Dosing, triage, diagnosis, treatment protocols -- these map naturally to investing concepts and differentiate the writing from generic finance content.

---

### H. Engagement / Contrarian Posts (1-2/month)

| Attribute | Detail |
|-----------|--------|
| **Word count** | 600-1,000 |
| **Theme** | Editorial (serif, light background) |
| **Data sources** | Market observations, contrarian thesis from themes data |
| **Cadence** | 1-2 per month, typically midweek |
| **Visual elements** | Minimal -- text-forward with one stat or chart if supporting the argument |
| **Module** | Manual or `python -m substack.content_generator` with custom prompt |

**Purpose:** Strong thesis that generates comments. Substack's algorithm weights comments more heavily than likes. A well-argued contrarian take with 30 comments will outperform a consensus piece with 100 likes in terms of subscriber acquisition.

**Examples of contrarian angles:**

- Why indexing is the new crowded trade
- The case for holding cash when everyone else is fully invested
- Why the most popular stock in your feed is probably the worst entry right now
- Sector X is over -- here is where capital is actually flowing

---

## 3. Notes Strategy (21/week = 3/day)

### Why Notes Matter

Notes are Substack's primary organic growth channel. The platform reported 32 million new subscribers came from in-platform activity in a single quarter. For a finance newsletter, this means:

- 60-70% of new subscriber growth comes from Notes and in-platform discovery
- Comments are weighted more heavily than likes as an algorithmic signal
- Restacking is a primary distribution signal (late 2025 shift)
- 2-3 notes per day is the sweet spot for sustained visibility
- The first 4 hours of a note determine its algorithmic reach

### 7 Note Types

**1. PORTFOLIO_PULSE**
Winner receipts, benchmark alpha, "the system diagnosed X early." Show hard numbers. Reference specific positions (only those above 15% gain). Always include P&L context.

**2. SIGNAL_ALERT**
New signals from the weekly or daily scan. Alternatively, "why we passed" notes when the system filters everything out -- these are powerful for the selectivity narrative.

**3. THEME_MOMENTUM**
One theme per note. Thesis in 2-3 sentences, what is driving it, which names are aligned. Never more than one theme per note to keep focus sharp.

**4. MARKET_REACTION**
Quick takes on market moves, VIX spikes, rate decisions, earnings surprises. Tie back to how the system is positioned. Speed matters -- publish within hours.

**5. SYSTEM_PROOF**
Funnel statistics (1,800 screened, X passed technical, Y theme-confirmed, Z cleared all gates). Discipline messaging. "The system said no to 1,795 stocks this week."

**6. LEARNING_NUGGET**
Draw from `content/learning_content_library.py` (20 topics). Medical-investor analogies. Each note teaches one concept and ends with an engagement question.

**7. ENGAGEMENT_HOOK**
Community questions, polls, "what are you watching?" Designed to generate replies. These notes exist purely to drive comments, which are the strongest algorithmic signal.

### Weekly Schedule Matrix

| Day | Morning (08:30 ET) | Midday (12:30 ET) | Evening (17:30 ET) |
|-----|--------------------|--------------------|---------------------|
| Saturday | PORTFOLIO_PULSE | THEME_MOMENTUM | ENGAGEMENT_HOOK |
| Sunday | LEARNING_NUGGET | ENGAGEMENT_HOOK | MARKET_REACTION |
| Monday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |
| Tuesday | SIGNAL_ALERT | THEME_MOMENTUM | ENGAGEMENT_HOOK |
| Wednesday | MARKET_REACTION | PORTFOLIO_PULSE | LEARNING_NUGGET |
| Thursday | THEME_MOMENTUM | SIGNAL_ALERT | ENGAGEMENT_HOOK |
| Friday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |

### Note Format Rules

- **Length:** 150-300 words, flowing paragraphs only (no markdown headers, no bullet lists)
- **Closing:** Every note ends with an engagement question
- **Disclaimer:** Every note ends with "Not financial advice. Informational only."
- **Voice:** Medical-investor throughout -- clinical precision, no hype
- **Ticker format:** $TICKER with price data when referencing stocks (e.g., "$ASPI at $4.82")
- **No emojis in body text.** Clean, professional prose.

### Dedup Rules

- No ticker in more than 3 notes per week
- No theme in more than 4 notes per week
- No engagement hook repeated within a week
- Adjacent notes (same day) must cover different topics
- Do not repeat the same learning topic within a 4-week window

### Engagement Hook Library

**Portfolio / Performance:**
- "What is the best trade your system has ever generated?"
- "How do you track your portfolio performance -- spreadsheet, app, or something else?"
- "What is your win rate this year? Honest answers only."
- "Do you benchmark against SPY, QQQ, or something else entirely?"

**Strategy / Process:**
- "How do you decide when to exit a winner?"
- "What themes are on your radar this week?"
- "What is your system telling you right now?"
- "How many stocks do you hold at once -- and how did you decide that number?"
- "Do you size positions by conviction or equal-weight everything?"

**Market / Flows:**
- "Are you seeing the same institutional flows we are?"
- "Where is capital rotating right now in your view?"
- "What sector looks most overextended to you?"
- "Is the market pricing in too much optimism or too much fear?"

**Psychology / Discipline:**
- "What is the hardest part of your investing process?"
- "Have you ever overridden your own system? What happened?"
- "How do you handle a losing streak without changing your strategy?"
- "What is the one investing lesson that took you the longest to learn?"

**Engagement / Community:**
- "What would you like us to deep dive next week?"
- "Which of our themes has been most useful for your own research?"
- "If you could add one feature to our weekly report, what would it be?"

---

## 4. Weekly Content Calendar (Adaptive)

The weekly schedule is generated by `python -m substack.content_production_guide` and adapts based on scanner output. The 4 content categories are assigned intelligently:

### Category Assignment Logic

| Category | Assigned When | HTML Theme |
|----------|---------------|-----------|
| **Performance Review** | Always Sunday | Dashboard (dark) |
| **Ticker Deep Dive** | New GREEN signal or portfolio winner ≥25% | Editorial (light) |
| **Theme Rotation** | PRIME or INVESTABLE themes detected | Dashboard (dark) |
| **Educational** | Fills remaining days | Editorial (light) |

### Example: Standard Week (signals exist)

| Day | Category | Topic | Notes (3/day) |
|-----|----------|-------|---------------|
| **Saturday** | (Notes only) | — | Journey, Teaching, Community |
| **Sunday** | Performance Review | Weekly newsletter | Community, Journey, Week Preview |
| **Monday** | Ticker Deep Dive | $INOD (new GREEN signal) | Market Macro, Winner Highlight, Ticker News |
| **Tuesday** | Theme Rotation | AI Infrastructure (PRIME) | Geopolitics, Theme Spotlight, Community |
| **Wednesday** | Ticker Deep Dive | $RCAT (portfolio winner) | Teaching, Portfolio Insight, Community |
| **Thursday** | Educational | Momentum investing framework | Market Midweek, System Insight, Ticker News |
| **Friday** | Theme Rotation | Nuclear Renaissance | Week Reflection, Winner Recap, Engagement |

### Example: Zero-Signals Week

| Day | Category | Topic | Notes (3/day) |
|-----|----------|-------|---------------|
| **Saturday** | (Notes only) | — | Journey, Teaching, Community |
| **Sunday** | Performance Review | "Why We Passed" recap | Community, Journey, Week Preview |
| **Monday** | Educational | Position sizing masterclass | Market Macro, Winner Highlight, Ticker News |
| **Tuesday** | Theme Rotation | Sector rotation flows | Geopolitics, Theme Spotlight, Community |
| **Wednesday** | Educational | The power of selectivity | Teaching, Portfolio Insight, Community |
| **Thursday** | Theme Rotation | Cold theme contrarian view | Market Midweek, System Insight, Ticker News |
| **Friday** | Educational | Compounding math | Week Reflection, Winner Recap, Engagement |

**Zero-signals weeks are valuable content.** The selectivity narrative ("we screened 1,800 stocks and found nothing worth buying") reinforces the system's discipline and generates strong engagement.

### Daily Workflow

1. Open `substack/output/current/content_production_guide.md` → check today's category + topic
2. Open `substack/docs/content_prompt_handbook_v5.md` → copy the matching category prompt
3. Attach the content production guide to Claude.ai (Opus 4.6 + extended thinking)
4. Paste prompt → get HTML post + 3 HTML notes
5. Paste into Substack

---

## 5. Visual Design System

Sterling Signals uses two HTML themes for Substack posts. Both are self-contained with inline styles (Substack strips external CSS). Max container width: 680px. System fonts only.

### Theme A: Editorial (Serif, Light Background)

**Use for:** Stock deep dives, price targets, educational posts, framework posts, contrarian takes.

| Element | Value |
|---------|-------|
| Body font | Georgia, 'Times New Roman', serif |
| Label font | -apple-system, system sans-serif |
| Page background | `#fafaf8` |
| Container background | `#fff` |
| Text colour | `#1a1a1a` |
| Label colour | `#8a7f72` |
| Date colour | `#a09890` |
| Border colour | `#e0ddd8` |
| Bear accent | `#8b3a1a` (price), `#fdf6f4` (background) |
| Base accent | `#3d5a80` (price), `#f4f7fa` (background) |
| Bull accent | `#4a7c59` (price), `#f4faf5` (background) |
| Positive P&L | `#2e5e3e` |
| Negative P&L | `#a04030` |

**Components available** (from `content/html_templates.py`):

- `editorial_wrap()` -- full page wrapper with styles
- `editorial_masthead()` -- ticker, date, subtitle header
- `editorial_target_banner()` -- bear/base/bull price target row
- `editorial_stat_row()` -- horizontal key-value pairs
- `editorial_callout()` -- three variants: neutral, warning, key
- `editorial_financial_table()` -- styled data table
- `editorial_catalyst_list()` -- timeline-style catalyst items
- `editorial_risk_block()` -- red-accented risk section
- `editorial_sources()` -- source attribution list

### Theme B: Dashboard (Dark, Teal Accents)

**Use for:** Weekly newsletters, market analysis, theme deep dives, portfolio showcases, DD posts, quick takes.

| Element | Value |
|---------|-------|
| Body font | -apple-system, BlinkMacSystemFont, system sans-serif |
| Page background | `#111827` |
| Card background | `#1F2937` |
| Border colour | `#374151` |
| Primary accent | `#2DD4BF` (teal) |
| Gains | `#22C55E` (green) |
| Caution / gold | `#F59E0B` |
| Losses | `#EF4444` (red) |
| Text | `#F9FAFB` |
| Muted text | `#9CA3AF` |
| Header background | `#0F172A` |

**Components available** (from `content/html_templates.py`):

- `dashboard_wrap()` -- full page wrapper with dark styles
- `dashboard_hero()` -- large header section with title and subtitle
- `dashboard_stat_grid()` -- 2-6 stat boxes in a responsive grid
- `dashboard_theme_card()` -- theme name, classification, progress bars for sub-scores
- `dashboard_rotation_bars()` -- horizontal bars showing sector flow direction
- `dashboard_funnel()` -- screening funnel visualisation
- `dashboard_pullquote()` -- highlighted quote block with teal border
- `dashboard_winners_table()` -- portfolio winners with P&L columns
- `dashboard_left_border_card()` -- card with coloured left border
- `dashboard_two_column()` -- side-by-side content layout

### Shared Components

- `footer_cta()` -- subscribe call-to-action
- `disclaimer()` -- "Not financial advice" legal text

### Screenshot Workflow for Substack

Substack does not render custom HTML reliably. For posts with visual elements:

1. Generate the HTML file using the relevant module
2. Open the HTML file in a browser at 680px viewport width
3. Screenshot individual visual sections (stat grids, theme cards, tables)
4. Paste screenshots into the Substack editor as images
5. Write surrounding narrative text directly in Substack's native editor
6. This produces the best visual result on both web and email delivery

---

## 6. Marketing Compliance

### Banned Terms (never appear in any public content)

All banned terms are defined in `config/banned_terms.py`. This is the single source of truth. Key categories:

**Internal indicators (never name these publicly):**
HMA, Hull Moving Average, RSI, MACD, KDJ, VWAP, Banker, Banker indicator, Banker rising, UC, Undercurrent, UC rising, UC falling, BoS, Break of Structure, ExD, Weekly BoS, Weekly pivot

**System internals:**
Gatekeeper, Investment Gate, Deep DD, Tier 1/2/3, TIER1/TIER2/TIER3, conviction score, conviction rating, conviction 3/4/5 (any numeric value), theme scoring, 5-gate, 5th Gate, gate 1-5

**Strategy specifics:**
20% trailing stop, 20% stop, Beta >= 1.5, beta threshold, profit lock, tiered stop, gear shift, sizing gear, price cap, $25 cap

**Old branding (retired):**
TEAL signal, VIOLET signal, AMBER signal, purple signal (use GREEN signal / RED signal instead)

**UK references:**
ISA, UK ISA, GMT, BST, UK Time, UK investor, GBP/USD

**Previously leaked internal terms:**
Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria

### Approved Marketing Language

| Concept | Public Language |
|---------|----------------|
| Banker / UC indicator | "Institutional accumulation" or "Institutional Accumulation Divergence" |
| HMA / BoS | "Structural momentum" or "Structural Pivot Confirmation" |
| Full pipeline | "Proprietary 5-gate screening system" |
| Theme scoring | "Sector flow analysis" or "Sector Flow Analysis" |
| Trailing stops | "Capital preservation protocol" (note: also banned as of recent update -- use "systematic exit discipline" instead) |
| Buy signal | "GREEN signal" |
| Sell signal | "RED signal" or "exit alert" |
| Conviction 8-10 | "Extremely Bullish" |
| Conviction 7 | "Bullish" |
| Conviction 4-6 | "Watching" |
| Conviction 1-3 | Do not publish |

### Approved System Descriptions

- "Proprietary 5-gate screening system"
- "Filters 1,800 stocks to 3-5 actionable signals"
- "Institutional-grade momentum analysis"
- "Systematic approach that removes emotional bias"
- "No ego, just execution"
- "The system protects capital so we live to fight another day"

### Winners-Only Policy

- Minimum 15% gain to showcase a position publicly
- Minimum 25% gain before showing an entry price for an open position
- Closed winners: always show entry prices for profitable exits
- Never dwell on losses, but never hide them either
- When a stop is hit: "Stop hit = system working as designed"
- When portfolio is underwater: "Down but managing risk -- disciplined exits in place"
- Always show full P&L including losers in portfolio performance summaries

### Honesty Rules

Marketing language does not mean dishonesty. These rules are absolute:

- Always show full P&L including losers
- Frame losses constructively but never omit them
- If the system produced zero signals, say so proudly
- If a stop was hit, report the loss amount
- Never cherry-pick a timeframe to hide poor performance

---

## 7. Production Guide

### Full Friday Pipeline (automated via `run_friday.sh`)

The Friday pipeline generates all weekly content in sequence:

```
Step 1:   Scanner (Technical > Thematic > Investment Gate > Deep DD)
Step 1.5: Funnel graphic
Step 2:   TradingView chart capture
Step 3:   Market analysis (Claude + web search)
Step 4:   Newsletter compilation (Claude)
Step 4.5: DD HTML posts per buy signal
Step 5:   Tweet generation (3 accounts x 35 tweets)
Step 5.5: Content production guide (adaptive schedule + context doc)
Step 5.6: Substack notes batch (21 notes for the week)
Step 6:   Git commit and push
```

```bash
./run_friday.sh              # Full production run
./run_friday.sh --test       # Test mode (minimal API calls)
./run_friday.sh --no-push    # Skip git push
./run_friday.sh --skip-charts       # Skip TradingView capture
./run_friday.sh --skip-newsletter   # Skip newsletter compilation
```

### Individual Content Generation Commands

**Content production guide (adaptive schedule):**
```bash
python -m substack.content_production_guide              # Generate weekly schedule + context doc
python -m substack.content_production_guide --dry-run    # Preview without saving
```

**Substack posts (automated fallback — prefer handbook v5 + Claude.ai):**
```bash
python -m substack.content_generator --all               # Auto-detect and generate all
python -m substack.content_generator --market            # Saturday weekly recap
python -m substack.content_generator --theme             # Theme deep dive
python -m substack.content_generator --dd                # DD deep dive(s)
python -m substack.content_generator --portfolio         # Portfolio spotlight
python -m substack.content_generator --dry-run           # Preview without LLM
```

**Substack notes:**
```bash
python -m substack.notes_batch_generator                 # Full week (21 notes)
python -m substack.notes_batch_generator --html          # Full week as HTML files
python -m substack.notes_batch_generator --day monday    # Single day
python -m substack.notes_batch_generator --no-llm        # Template fallback (no LLM)
python -m substack.notes_batch_generator --dry-run       # Preview without saving
python -m substack.notes_generator                       # Legacy 2-note generator (Tuesday + Thursday)
```

**DD posts:**
```bash
python -m substack.dd_post_generator                     # All PASS signals
python -m substack.dd_post_generator --ticker ASPI       # Specific ticker
python -m substack.dd_post_generator --dry-run           # Preview to stdout
```

**Newsletter:**
```bash
python -m substack.newsletter_compiler --from-html       # Convert Claude.ai HTML to newsletter
```

**Market analysis:**
```bash
python -m substack.market_analyzer --save                # Generate and save market context
```

**Portfolio dashboard:**
```bash
python -m substack.portfolio_visual                      # Generate HTML + PNG dashboard
python -m substack.portfolio_visual --dry-run            # Preview HTML only
```

### Output Locations

```
substack/output/current/
    newsletter.html                         # Saturday flagship newsletter
    portfolio_visual.html                   # Portfolio dashboard with equity curve SVG
    content_production_guide.md             # Adaptive weekly schedule + context (attach to Claude.ai)
    substack_posts/
        dd_TICKER.html                      # DD post per buy signal (e.g., dd_ASPI.html)
        wednesday_theme_deep_dive.html      # Theme deep dive (automated fallback)
        thursday_stock_deep_dive.html       # Stock deep dive (automated fallback)
        friday_portfolio_showcase.html      # Portfolio showcase (automated fallback)
    substack_notes/
        *_1_*.md/html, *_2_*.md/html        # 21 notes (3/day) — .html with --html flag
        tuesday_note.md                     # Legacy compat
        thursday_note.md                    # Legacy compat
        notes_manifest.json                 # Batch tracking

scanner/output/current/
    newsletter_briefing.md                  # Scanner data for newsletter
    market_analysis.md                      # Market context analysis

twitter/output/charts/
    TICKER_YYYYMMDD.png                     # TradingView chart screenshots
    chart_manifest.json                     # Tracks all captured charts
```

Archived weekly to `scanner/output/archive/2026-WXX/` and `substack/output/archive/2026-WXX/` by ISO week number.

### Manual Steps (Daily)

| When | Task | Time |
|------|------|------|
| **Saturday** | Copy `newsletter.html` to Substack, add TradingView charts, publish; post 3 notes | ~15 min |
| **Sunday-Friday** | Open context doc → copy category prompt → Claude.ai → HTML post + 3 notes → Substack | ~10 min/day |

Everything else (tweets, daily scanner, daily tweet posting) is automated via GitHub Actions.

**Prompt reference:** `substack/docs/content_prompt_handbook_v5.md`

---

## 8. Growth Levers (Substack-Specific)

### Recommendations Engine

Set up and maintain recommendations for 10-15 complementary finance newsletters. Monthly, check which are sending the most inbound subscribers and deepen those relationships. Recommendation-driven signups typically account for 20-25% of growth for established newsletters.

### Welcome Email

The most-opened email. Include: who we are, what subscribers get, our 2-3 best posts with links, and a direct question ("What are you most interested in -- signals, themes, or education?").

### Homepage

Pin a "Start Here" post that guides new visitors to the best content. Organise the archive by category (signals, themes, education, portfolio). As the library grows, this becomes a discovery asset.

### Cross-Promotion

Guest posts and post swaps with complementary newsletters. Joint Q&A sessions. Being featured in another creator's newsletter carries a built-in endorsement and converts at a higher rate than any other channel.

### Notes Engagement (Beyond Posting)

- Leave 3-5 thoughtful comments on other finance creators' Notes daily
- Restack strategically: morning (own post), afternoon (older Note), evening (other writers)
- Engage with smaller accounts, not just large ones -- mutual growth compounds

### X/Twitter Coordination

Sterling Signals posts 7 tweets per day across multiple accounts via automated GitHub Actions. Tweets link back to Substack for deeper analysis. X is a top-of-funnel channel; Substack is where subscribers convert and retain.

---

*This document is the single source of truth for Sterling Signals content strategy on Substack. All content must comply with `config/banned_terms.py` before publishing. See `substack/docs/content_prompt_handbook_v5.md` for the category-based prompt reference.*
