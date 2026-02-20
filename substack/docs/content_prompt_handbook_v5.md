# Sterling Signals — Content Prompt Handbook v5

> **Adaptive content system for Opus 4.6 + Extended Thinking**
> Prompts organized by content category, not day-of-week.
> The weekly context document tells you which prompt to use each day.
> Attach context document → check today's category → copy the prompt → send.
> Last updated: February 2026

---

## How to Use This Handbook

### Daily Workflow (3 steps)

1. Open Claude.ai (Opus 4.6 + extended thinking)
2. Attach the weekly context document (`content_production_guide.md`)
3. Check the **Weekly Content Schedule** in the context document for today's category → copy that category's **Post Prompt** and send → then copy the **Notes Prompt** and send

That's it. The context document assigns a category and topic to each day based on what the scanner found. You never decide what to write about — the system decides for you.

### 4-Category Adaptive System

Posts are organized by category. The Friday pipeline assigns categories to days based on scanner output:

| Category | HTML Theme | When Assigned |
|----------|-----------|---------------|
| **Ticker Deep Dive** | Editorial (light) | New GREEN signal or portfolio winner to showcase |
| **Theme Rotation** | Dashboard (dark) | Active PRIME/INVESTABLE themes from scanner |
| **Educational** | Editorial (light) | Evergreen investing wisdom — fills remaining days |
| **Performance Review** | Dashboard (dark) | Always Sunday — weekly newsletter |

**Example week with 2 new signals and 3 active themes:**
| Day | Category | Topic |
|-----|----------|-------|
| Sunday | Performance Review | Week 8 Newsletter |
| Monday | Ticker Deep Dive | $INOD — New GREEN signal |
| Tuesday | Theme Rotation | AI Infrastructure — PRIME (8.2/10) |
| Wednesday | Educational | Topic via web search |
| Thursday | Ticker Deep Dive | $RCAT — Portfolio winner +55% |
| Friday | Theme Rotation | Power Grid — INVESTABLE (7.1/10) |
| Saturday | *No post* | Notes only |

**Example week with 0 new signals:**
| Day | Category | Topic |
|-----|----------|-------|
| Sunday | Performance Review | Week 8 Newsletter |
| Monday | Ticker Deep Dive | $FIX — Top portfolio winner |
| Tuesday | Theme Rotation | Defense — PRIME (7.8/10) |
| Wednesday | Educational | Topic via web search |
| Thursday | Theme Rotation | Nuclear — INVESTABLE (6.5/10) |
| Friday | Educational | Topic via web search |
| Saturday | *No post* | Notes only |

### When to Override the Schedule

Two alert types replace the day's scheduled post when triggered:

- **Trade Alert — Entry**: Use immediately when entering a new position. Replaces that day's post.
- **Trade Alert — Exit**: Use immediately when closing a position. Replaces that day's post.

These are the only two prompts requiring you to type a ticker symbol. Everything else is automatic.

---

## Category 1 — Ticker Deep Dive

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for system context, portfolio data, and all marketing/terminology rules.

TICKER SELECTION: Read the weekly content schedule in the context document. Identify the ticker assigned for today's Ticker Deep Dive slot. If no specific ticker is assigned, select the portfolio position with the highest P&L percentage from the "Showcase-Ready Winners" section. If there are no showcase winners, select the highest-gaining position that qualifies (15%+ gain).

State which ticker you are analysing and why you selected it before proceeding.

FRESHNESS CHECK: Use web search to get the current stock price for this ticker. Compare to the entry price in the context document and recalculate P&L if it has changed. Use the CURRENT price throughout the article.

You are a senior equity research analyst building an independent 12-month price target. You must NOT reference or anchor to any Wall Street analyst price targets. Your target must be built entirely from verifiable, sourced data. Use web search extensively.

Work through these stages sequentially using extended thinking:

STAGE 1 — FINANCIAL BASELINE
Search for and compile from the most recent 10-Q/10-K, earnings releases, and investor presentations:
- Trailing 8-quarter revenue, broken out by business segment
- Gross margin, operating margin, and net margin for each of those 8 quarters
- Free cash flow for the trailing 4 quarters
- Current shares outstanding and net change over 12 months
- Total debt, cash position, and any debt maturing within 18 months
- Current stock price (from your web search above)
- Short interest as a percentage of float
- Institutional ownership changes from the most recent 13F cycle

Present as structured tables. Flag any data you cannot find.

STAGE 2 — FORWARD REVENUE BUILD (next 12 months)
For each revenue segment, search for and document:
- Announced contracts, partnerships, or deals
- Product launches or expansion initiatives
- Pricing actions or ASP/ARPU trends
- TAM/SAM sizing for new markets
- Customer count or volume trends
- Known headwinds

Produce low/mid/high revenue estimates. Every assumption must cite a source.

STAGE 3 — MARGIN AND EARNINGS PROJECTION
Project gross margins, operating margins, EPS, and FCF per share for bear/base/bull scenarios.

STAGE 4 — VALUATION TRIANGULATION
Apply four methods:
A — Historical Multiple Range (P/E, EV/EBITDA over 5 years)
B — DCF (using your FCF projections, current 10-year Treasury + equity risk premium)
C — Peer-Relative (4-6 competitors, compare growth/margins/multiples)
D — Catalyst-Adjusted (probability-weighted impact of known 12-month catalysts)

STAGE 5 — SYNTHESIS AND ARTICLE
- Produce bear/base/bull targets from each method
- Weight the methods by appropriateness for this company type
- Derive probability weightings from analysis (not 25/50/25 default)
- Calculate probability-weighted expected value
- Identify 3 assumptions most likely wrong

Write the article as complete HTML using the Editorial theme (specs in Quick Reference at end of handbook).

Article structure (1000-1500 words):
1. The Pitch — 2-3 sentence elevator pitch
2. The Thesis — Structural trend or catalyst driving this. Connect to theme from context document.
3. Why Now — What changed recently? What's the inflection?
4. The Numbers — Revenue trends, margins, valuation. Specific quarterly data.
5. 12-Month Price Targets — Bear/base/bull with probability weightings and expected value
6. Bear Case — What could go wrong? Why risk is manageable.
7. Key Risk to Monitor — One specific thing with a date or metric
8. Our View — Confident summary
9. Footer — "Subscribe to Sterling Signals for weekly analysis and GREEN signals: https://sterlingsignals.substack.com"

Include [CHART: TICKER] placeholder. Output complete HTML.

Tone: Authoritative but accessible. Data-driven, confident, educational.
```

---

## Category 2 — Educational

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for system context, portfolio data, themes, and all marketing/terminology rules.

TOPIC SELECTION: No topic is pre-assigned. You will discover one.

Use web search to identify 3-5 candidate topics. For each, evaluate:
- Timeliness: Is there a recent study, market event, or data release making this relevant right now?
- Data richness: Are there specific, citable studies or datasets?
- Audience fit: Would an active small-cap swing trader find this actionable?
- Novelty: Fresh angle, not generic advice?
- Portfolio connection: Does it relate to what our scanner or portfolio is currently showing in the context document?

Think through candidates from these areas:
EXECUTION: Knowing when to sell vs buy, position sizing, letting winners run, first loss = best loss, averaging down trap
ANALYSIS: Technical + fundamental synergy, reading institutional flow, revenue > earnings for small-caps, catalyst vs story, spotting crowded trades
PSYCHOLOGY: FOMO cost, discipline paradox, confirmation bias, best trade you didn't make, compounding effect of avoiding big losses
SYSTEM: Systematic > discretionary, emotion removal, theme alignment value, selectivity as edge
RISK MANAGEMENT: Position sizing, trailing stops, max drawdown math, cash as ammunition
MOMENTUM: Structural momentum, institutional accumulation, sector rotation, market breadth
STRATEGY: Screening advantage, theme surfing, when to sell, concentration vs diversification

For each candidate, ask: (1) Can I illustrate this with something specific from the context document — a winning position, the scanner's rejection rate, a theme that's working? (2) Is there research data backing this up? (3) Is there a market event this week making this timely?

Select the strongest and explain your choice.

FRESHNESS CHECK: Use web search to verify any portfolio data you reference is current.

RESEARCH: Use web search to find:
- 2-3 academic studies or institutional research with specific findings
- Historical market data illustrating the concept
- Real-world examples from small-cap or growth stocks
- Counter-arguments — when does this fail?
- Practical application for individual investors
- 2024-2026 data making this timely

ARTICLE: Think through: What is the most surprising finding? Lead with that.

Write as complete HTML using the Editorial theme (specs in Quick Reference).

Article structure (800-1200 words):
1. Hook — Surprising stat, provocative question, or counterintuitive finding
2. The Concept — Teach the core idea accessibly
3. The Evidence — Studies, data, specific numbers and time periods
4. How We Apply It — Connect to our screening system. Reference portfolio winners from context document.
5. The Takeaway — One specific, actionable insight
6. Engagement Close — Genuine question inviting discussion
7. Footer — "Learn more in our weekly newsletter: https://sterlingsignals.substack.com"

Output complete HTML.

Tone: Teacher, not preacher. Evidence-based, slightly contrarian. Light and engaging.
```

---

## Category 3 — Theme Rotation

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for system context, portfolio data, theme analysis, and all marketing/terminology rules.

THEME SELECTION: Read the weekly content schedule in the context document. Identify the theme assigned for today's Theme Rotation slot. If no specific theme is assigned, select the highest-rated theme from the "Top Themes" section of the context document.

State which theme you are analysing and why before proceeding.

FRESHNESS CHECK: The context document was generated on Friday. Use web search to:
- Validate the theme thesis with any developments since Friday
- Check for new ETF flow data, policy announcements, or earnings that affect this theme
- Get current prices for any portfolio positions aligned with this theme

STAGE 1 — THEME VALIDATION
Use web search to cross-reference the scanner's thesis with fresh data. Has anything changed since Friday? Is the thesis strengthening or weakening? Look for confirming or disconfirming evidence.

STAGE 2 — DEEP RESEARCH
Use web search to find specific data for:
- ETF flows for relevant sector ETFs (tickers and dollar amounts)
- Institutional positioning — fund moves, 13F trends, commentary
- Policy and regulatory catalysts
- Earnings evidence — are companies in this theme beating estimates?
- Key companies positioned to benefit
- Risks — what could derail this? Crowded?
- Historical parallels
- Timeline — early-stage or late-stage?

STAGE 3 — ARTICLE
Think through: What is the single strongest data point? Lead with that.

Write as complete HTML using the Dashboard theme (specs in Quick Reference).

Article structure (800-1200 words):
1. Why This Theme, Why Now — Strongest data point first
2. The Investment Thesis — Structural dynamics, multi-year story
3. The Evidence — ETF flows, institutional moves, earnings, catalysts
4. What Our System Sees — Connect to scanner theme analysis from context document. Reference aligned portfolio positions.
5. Risks to the Thesis — Balanced assessment
6. What We're Watching — Specific upcoming events with dates
7. Stocks Positioned — 3-5 stocks, including any from our portfolio
8. Footer — "Get weekly theme analysis and GREEN signals: https://sterlingsignals.substack.com"

Output complete HTML.

Tone: Sharp, opinionated, data-backed. Institutional quality but accessible.
```

---

## Category 4 — Performance Review (Sunday Newsletter)

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it thoroughly — it contains our complete scanner results, portfolio data, theme analysis, and market analysis.

FRESHNESS CHECK: The context document was generated on Friday. Use web search to update:
- SPY current price and YTD return
- QQQ current price and YTD return
- IWM (Russell 2000) current price and YTD return
- VIX current level
- Any major market events since Friday's close
- Current prices for our top 3 showcase winners listed in the context document — recalculate their P&L from entry prices if prices have moved significantly

IMPORTANT: If any portfolio P&L figures in the context document are now materially different (>2% change) based on updated prices, use the updated figures in the article. Flag this in your reasoning but present the updated numbers seamlessly in the output.

Now write the Sunday newsletter and produce it as a complete, self-contained HTML document using the Dashboard theme (specs in Quick Reference at end of handbook).

Apply all marketing and terminology rules from the attached context document.

Before writing, think through: What is the most important story from this week? Is it a big winner, a theme shift, market context, or disciplined selectivity? Lead with that story.

Newsletter structure (1200-1500 words):

1. Market Context — What happened in markets this week? 2-3 sentences using fresh search data.
2. What Our Scanner Found — The screening funnel from the context document. How many scanned -> passed -> theme-confirmed -> GREEN signals. Include [SCAN_FUNNEL] placeholder. Frame rejection rate as proof of selectivity.
3. Themes Driving Momentum — Top 2-3 themes from the context document. What's hot, cooling, where is capital flowing? Include [THEME_SCORES] placeholder.
4. New GREEN Signals — If new signals exist in the context document: the pitch, theme alignment, why it cleared. Include [CHART: TICKER] for each. If no signals: "Why We Passed" section on disciplined selectivity.
5. Portfolio Performance — Showcase winners from the context document. Performance vs SPY and QQQ using FRESH benchmark data. Alpha generated. Include [WINNERS_TABLE] placeholder.
6. Benchmark Battle — Portfolio return vs SPY YTD vs QQQ YTD. Use fresh data, not the Friday snapshot.
7. Looking Ahead — Use web search to find 3-5 specific catalysts, earnings, or events for next week.
8. Footer — "Subscribe to Sterling Signals for the full weekly analysis: https://sterlingsignals.substack.com"

Output the complete HTML with all styles in a <style> block.

Tone: Confident and direct. Like a weekly briefing from a trusted analyst.
```

---

## Trade Alert — Entry (Ad-Hoc Override)

**Use when entering a new position. Replaces that day's scheduled post. Requires you to type the ticker symbol.**

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for portfolio data, theme analysis, and all marketing/terminology rules.

NEW POSITION: {TICKER}

Use web search to get:
- Current stock price
- Recent news and catalysts (past 2 weeks)
- Most recent quarterly earnings summary
- Sector/theme and how it's performing

Cross-reference with the context document's theme analysis — does this ticker align with any of our top-rated themes?

Write a Trade Alert article as complete HTML using the Editorial theme (specs in Quick Reference).

Article structure (400-800 words):
1. Trade Header — "NEW GREEN SIGNAL: {TICKER} — [Company Name]" with entry price, date, and theme alignment
2. Why This Name — What does the company do? What structural trend is it riding?
3. What Triggered the Signal — Describe using approved terminology ONLY (structural pivot confirmation, institutional accumulation divergence, momentum confirmed)
4. The Setup — Key financial metrics. 3-5 specific data points from web search.
5. What We're Watching — The specific metric or date that confirms the thesis
6. Risk Framing — One sentence risk, one sentence why risk-reward is favourable
7. Footer — "Get real-time GREEN signals: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder. Output complete HTML.

Tone: Decisive, calm authority. Measured conviction backed by data.
```

---

## Trade Alert — Exit (Ad-Hoc Override)

**Use when closing a position. Replaces that day's scheduled post. Requires you to type the ticker symbol.**

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for portfolio data, theme analysis, and all marketing/terminology rules.

CLOSING POSITION: {TICKER}

Look up this ticker in the context document's portfolio table to find entry price and P&L. Use web search to get the current price and recalculate final P&L.

Also search for:
- Recent news and developments
- Current state of the theme/sector this position was in

CRITICAL FRAMING RULES:
- If profitable (any gain): Lead with the return. "We're closing $TICKER at $X, locking in a Y% gain over Z weeks."
- If profitable (15%+): Celebrate — this validates the system.
- If at a loss or small gain: DO NOT mention the P&L number. Frame as "Our systematic exit discipline has triggered on $TICKER" and focus entirely on what changed in the thesis. NEVER use "loss," "stopped out," "down," "negative," or "underperformed."

Write a Trade Alert article as complete HTML using the Editorial theme.

Article structure (400-800 words):
1. Trade Header —
   If profitable: "TRADE CLOSED: {TICKER} — +Y% in Z weeks"
   If not profitable: "POSITION UPDATE: {TICKER} — Systematic Exit"
2. The Exit Decision — What changed? (System signal / thesis evolution / headwinds / target achieved)
3. What Changed — Specific details from web search
4. The Lesson — What does this trade teach about our process?
5. What's Next — Capital redeployment or patience?
6. Footer — "See every entry and exit: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder. Output complete HTML.

Tone: Measured, professional. An exit should feel as deliberate as an entry.
```

---

## Daily Notes Prompt (Universal — Used Every Day)

**Copy this prompt once per day, after the post prompt. It generates 3 HTML notes tailored to today's day and category.**

### Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

TODAY'S CONTEXT: Check the weekly content schedule in the context document to identify:
1. What day of the week it is today
2. What post category was assigned (Ticker Deep Dive, Theme Rotation, Educational, or Performance Review)
3. What specific topic/ticker/theme was covered in today's post

Your 3 notes must COMPLEMENT today's post — cover different angles, tickers, and themes. Never repeat the same ticker or theme featured in the post.

FRESHNESS CHECK: Use web search to get:
- SPY and QQQ current price and today's performance
- VIX current level
- Any breaking news for tickers in our portfolio (check the full portfolio list in the context document)
- Any notable market or geopolitical developments today

NOTE TYPE ROTATION (follow this matrix for today's day):

| Day | Note 1 | Note 2 | Note 3 |
|-----|--------|--------|--------|
| Sunday | Community & Connection | Journey & Milestones | Week Preview |
| Monday | Market Macro | Winner Highlight | Ticker News |
| Tuesday | Geopolitics/Macro | Theme Spotlight | Community |
| Wednesday | Teaching & Wisdom | Portfolio Insight | Community |
| Thursday | Market Midweek | System Insight | Ticker News |
| Friday | Week Reflection | Winner Recap | Engagement |
| Saturday | Journey | Teaching | Community |

Generate 3 notes following today's assigned types. Use these guidelines for each type:

**Community & Connection:** Invite connection with other Substack writers/investors. List 3-5 specific topics we cover from our themes. End with invitation to connect or share their work.

**Journey & Milestones:** Share a genuine milestone from the context document — portfolio alpha, win count, screening stats, weeks publishing. Frame as reflection with 2-3 observations about what we've learned.

**Week Preview / Week Reflection:** Preview upcoming catalysts (web search for earnings, Fed, data) or reflect on the week's market action and how our portfolio performed. Connect to our themes.

**Market Macro / Geopolitics/Macro / Market Midweek:** Comment on today's market action or geopolitical developments using web search data. Connect sector moves to our portfolio themes.

**Winner Highlight / Winner Recap:** Showcase a 15%+ winner from the context document with UPDATED price from web search. Frame through thematic lens. End with engagement question.

**Ticker News:** Search for the most significant recent news (last 48 hours) for any portfolio ticker. Connect to our thesis for holding it. If no news, search for news about our top-rated theme.

**Theme Spotlight:** Cover a theme from the context document that's NOT featured in today's post. One fresh data point from web search. Explain why it matters and how we're positioned.

**System Insight:** Pull scanner numbers from context (screened, passed, rejection rate, GREEN signals). Frame selectivity as the edge. Build anticipation for signals.

**Teaching & Wisdom:** Find a counterintuitive investing stat or pattern relevant to current markets. Connect to what's happening this week.

**Portfolio Insight:** Identify an interesting pattern in our portfolio from the context document — theme clustering, sector exposure, newest vs oldest positions.

**Engagement:** Ask a specific, informed question drawn from real data. Maximise reply potential.

DEDUPLICATION RULES:
- Monday's winner highlight and ticker news must feature DIFFERENT tickers than Thursday's and Friday's
- Tuesday's theme spotlight must cover a DIFFERENT theme than Thursday's system update
- Never repeat the same ticker across two notes on the same day

FORMAT — PRODUCE EACH NOTE AS SELF-CONTAINED HTML:
Each note must be a complete HTML snippet with inline styles. Use this template:

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
[Note content here — use <p> tags for paragraphs, <strong> for emphasis, <br> for line breaks]
<p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
</div>

CONTENT RULES (ALL NOTES):
- NO markdown headers (no #, ##, ###)
- NO bullet points (no -, *)
- Use short paragraphs and single-line statements
- $TICKER format with current price or percentage where relevant
- One or two emoji max per note, placed naturally
- 100-200 words per note
- End EVERY note with: "Not financial advice. Informational only."

Tone varies by day:
- Monday: Sharp, informed, real-time market energy
- Tuesday: Informed and conversational, connecting dots
- Wednesday: Thoughtful midweek, reflective but data-grounded
- Thursday: Sharp and data-focused, midweek intensity
- Friday: End-of-week reflective, warm, inviting weekend conversation
- Saturday/Sunday: Weekend casual, personal, community-focused

Output 3 notes clearly labelled [NOTE 1], [NOTE 2], [NOTE 3]. Each as self-contained HTML.
```

---

## Quick Reference

### Signal Branding
- **"GREEN signal"** for buy signals
- NEVER: TEAL, PASS, VIOLET, AMBER, purple, STRONG BUY, SPEC BUY

### Banned Terms (Never Use in Any Content)

**Indicators:** HMA, Hull Moving Average, HMA Pivot, RSI, RSI(10), RSI(14), MACD, MACD cross, MACD crossover, MACD(12,26,9), KDJ, VWAP, Banker, Banker indicator, Banker rising, Banker >= 55, UC, UC rising, UC falling, UC indicator, UC > 0, Undercurrent, BoS, Break of Structure, Weekly BoS, ExD, ExD exit, ExD signal, Beta >= 1.5, beta threshold, compound exit, 20% trailing stop, 20% stop

**System internals:** Gatekeeper, Investment Gate, Deep DD, 5-gate, 5th Gate, Gate 1-5, Tier 1/2/3, TIER1, TIER2, TIER3, conviction score, conviction rating, conviction 1-10, Theme scoring, profit lock, tiered stop, tiered profit, gear shift, sizing gear, price cap, $25 cap, kill switch, valuation regime, STRONG BUY, SPEC BUY, NO GO

**Old branding:** TEAL signal, VIOLET signal, AMBER signal, PASS signal, Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria

**Geography/Audience:** UK ISA, ISA account, ISA wrapper, GMT, BST, UK Time, London time, GBP/USD, UK investor, UK trader, Roth IRA, Roth, PDT, PDT rule, pattern day trader, 401k, 401(k)

**Vague/generic phrases:** "theme keeps delivering", "system keeps working", "trust the process", "some interesting setups", "a few tickers", "interesting developments", "stay tuned", "more to come", "keep an eye on", "picks and shovels", "still bleeding", "loser", "dragging down"

### Approved Alternatives

| Instead of... | Use... |
|---------------|--------|
| HMA/Banker/UC/indicators | "proprietary screening system" or "our screening system" |
| Entry signal / HMA pivot | "momentum confirmed", "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation divergence" |
| Stop hit / exit | "systematic exit discipline", "the system triggered an exit" |
| Break of Structure | "structural trend confirmation" |
| Gatekeeper / Investment Gate | "fundamental screening", "cleared all gates" |
| Deep DD | "deep analysis" |
| Conviction 8-10 | "Extremely Bullish" |
| Conviction 7 | "Bullish" |
| Conviction 4-6 | "Watching" |
| TEAL/PASS signal | "GREEN signal" |
| VIOLET signal | "system exit" |
| Tier 1/2/3 | "high conviction" |

### Entry Price Display Rules
- **15%+ gain**: Can showcase the position and mention P&L percentage
- **25%+ gain**: Can show entry price
- **Under 15%**: Do not highlight or showcase
- **Losses**: NEVER mention

### Winners-Only Policy
- NEVER mention losing positions, negative P&L, or underwater trades
- NEVER show a number with a minus sign followed by a percent (e.g., -5.2%)
- If portfolio is down overall: focus on methodology, patience, and selectivity
- Only spotlight positions with 15%+ gains

### HTML Theme Specs

**Editorial Theme** (Ticker Deep Dives, Educational, Trade Alerts)
- Background: `#fafaf8` | Container: `#fff` | Max-width: `680px`
- Headings: `Georgia, 'Times New Roman', serif`
- Body: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif`
- Text: `#1a1a1a` | Muted: `#6b6b6b` | Labels: `#8a7f72`
- Price targets: Bear `#fdf6f4`/`#8b3a1a`, Base `#f4f7fa`/`#1b3a5c`, Bull `#f4faf5`/`#2e5e3e`
- Table header: `#2c2520` text `#f0ebe4` | Alt rows: `#faf9f7`
- Callout: border-left 3px solid `#3d5a80`, bg `#f4f7fa`
- Positive: `#2e5e3e` | Negative: `#a04030`

**Dashboard Theme** (Theme Rotations, Performance Review, Portfolio Showcase)
- Dark background: `#111827` | Card bg: `#1F2937` | Max-width: `680px`
- Accent: teal `#2DD4BF` | Green: `#22C55E` | Amber: `#FBBF24` | Red: `#EF4444`
- Text: `#F9FAFB` | Muted: `#9CA3AF` | Dim: `#6B7280`
- Borders: `#374151`
- Font: system sans-serif throughout
- Header bg: `#0F172A`
- Teal bg (highlights): `#0D3B34`

**Notes Theme** (Compact, light)
- Background: transparent (Substack handles it)
- Max-width: `680px` | Padding: `20px`
- Font: system sans-serif, `16px`, line-height `1.6`
- Text: `#1a1a1a` | Disclaimer: `#6b6b6b`, `13px`
- Disclaimer border-top: `1px solid #e0ddd8`

### Visual Element Placeholders
- `[CHART: TICKER]` — TradingView chart screenshot
- `[SCAN_FUNNEL]` — Scanning funnel visualisation
- `[THEME_SCORES]` — Theme score cards with progress bars
- `[WINNERS_TABLE]` — Portfolio winners table

### Educational Topic Seeds
**Risk Management:** Position Sizing, Trailing Stops, Max Drawdown Math, Cash as Ammunition
**Momentum:** Structural Momentum, Institutional Accumulation, Sector Rotation, Market Breadth
**Fundamentals:** Catalyst Investing, Revenue Acceleration, Theme Alignment, Small-Cap Edge
**Psychology:** Patience Over FOMO, Systematic Discipline, Loss Acceptance, Compounding Math
**Strategy:** Screening Advantage, Theme Surfing, When to Sell, Concentration vs Diversification

### Key Investor Lesson Seeds
**Execution:** When to sell, position sizing, averaging down trap, letting winners run, first loss = best loss
**Analysis:** Technical + fundamental synergy, reading institutional flow, revenue > earnings for small-caps, catalyst vs story, spotting crowded trades
**Psychology:** FOMO cost, discipline paradox, confirmation bias, best trade you didn't make, avoiding big losses
**System:** Systematic > discretionary, emotion removal, theme alignment value, selectivity as edge

---

## Weekly Note Distribution

Ensures variety — no note type repeated on consecutive days, and readers get a different mix every day.

| Note Type | Sun | Mon | Tue | Wed | Thu | Fri | Sat | Total |
|-----------|-----|-----|-----|-----|-----|-----|-----|-------|
| **Community & Connection** | 1 | | 1 | 1 | | | 1 | 4 |
| **Journey & Milestones** | 1 | | | | | | 1 | 2 |
| **Market Macro & Geopolitics** | | 1 | 1 | | 1 | | | 3 |
| **Ticker News** | | 1 | | | 1 | | | 2 |
| **Winner Highlight** | | 1 | | | | 1 | | 2 |
| **Theme Spotlight** | | | 1 | | | | | 1 |
| **System & Scanner Insight** | | | | | 1 | | | 1 |
| **Teaching & Wisdom** | | | | 1 | | | 1 | 2 |
| **Portfolio Insight** | | | | 1 | | | | 1 |
| **Week Preview / Review** | 1 | | | | | 1 | | 2 |
| **Weekend Engagement** | | | | | | 1 | | 1 |

**21 notes per week** across 7 days. Each day covers different tickers and themes — Monday's winner highlight and ticker news must feature different tickers than Thursday's and Friday's.

---

## v5 Change Log

| Change | Rationale |
|--------|-----------|
| **4-category system replaces 7-day fixed** | Posts organized by content category (Ticker Deep Dive, Theme Rotation, Educational, Performance Review) instead of day-of-week. The Friday pipeline assigns categories to days based on scanner output. No more "Monday is always Deep Dive" — some weeks Monday might be Theme Rotation if there are no new signals. |
| **Adaptive schedule from context document** | The content production guide now assigns specific categories, topics, and tickers to each day based on that week's scanner results, themes, and portfolio. Zero daily decisions needed — just look up today in the schedule. |
| **Universal notes prompt replaces 7 day-specific prompts** | One prompt with an embedded rotation matrix handles all 7 days. Reduces handbook size by ~60% while maintaining the same note variety and deduplication rules. |
| **Notes output as HTML** | Notes are now produced as self-contained HTML snippets with inline styles, ready for direct paste into Substack. No more markdown-to-HTML conversion needed. |
| **Saturday added as notes-only day** | Weekend presence without requiring a full article. 3 community-focused notes keep engagement active 7 days/week. |
| **Educational absorbs Key Lessons + Friday Educational** | v4 had separate Wednesday "Key Investor Lessons" and Friday "Educational" categories. v5 merges them into one "Educational" category — the prompt discovers its own topic each time, and the system assigns it to whichever days don't have ticker dives or theme rotations. |
| **Portfolio Showcase absorbed into Ticker Deep Dive and Performance Review** | v4 Thursday Portfolio Showcase content is now covered by: (1) the Sunday Performance Review which always showcases winners, and (2) Ticker Deep Dive posts which cover portfolio winners when no new signals exist. |
| **All v4 prompt quality preserved** | Every prompt retains the v4 FRESHNESS CHECK, web search requirements, stage-based research methodology, article structure guidelines, and tone instructions. |
