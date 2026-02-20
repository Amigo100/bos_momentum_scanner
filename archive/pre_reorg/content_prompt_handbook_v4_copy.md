# Sterling Signals — Content Prompt Handbook

> **Permanent reference for Substack content generation.**
> Use with Claude.ai (Opus 4.6 + extended thinking) and the weekly context document.
> Last updated: February 2026

---

## How to Use This Handbook

### Daily Workflow

1. **Friday pipeline runs** → generates `trades/current/content_production_guide.md` (your weekly context document) with scanner data, portfolio, themes, market analysis, and a **weekly schedule** telling you which category to post each day
2. **Each day**, open Claude.ai (Opus 4.6 + extended thinking enabled)
3. **Attach** the context document (`content_production_guide.md`)
4. **Copy** the relevant prompt from this handbook for today's scheduled category
5. **Fill in** any `{PLACEHOLDERS}` — the schedule tells you which ticker or theme
6. **Send** → Claude researches via web search, reasons through the content, and produces the HTML article
7. **Then copy** the Daily Notes prompt, send it, and get 3 fresh Substack Notes
8. **Paste** the HTML into Substack and publish

### The 4 Post Categories

| # | Category | HTML Theme | When | Web Search | Word Count |
|---|----------|------------|------|------------|------------|
| 1 | **Ticker Deep Dive & Price Targets** | Editorial (light) | 1-2× per week when we have signals or winners | Required | 1000–1500 |
| 2 | **Educational** | Editorial (light) | 1-2× per week | Required | 800–1200 |
| 3 | **Market Rotations & Growth Themes** | Dashboard (dark) | 1-2× per week when themes are active | Required | 800–1200 |
| 4 | **Performance Review** | Dashboard (dark) | Every Sunday (newsletter) | Required | 1200–1500 |

### Weekly Schedule Logic

The Friday pipeline assigns categories to days based on what data is available:

- **Sunday** — always Performance Review (the newsletter)
- **Monday–Friday** — a mix of the other 3 categories, avoiding repeats on consecutive days
- New GREEN signals → schedule a **Ticker Deep Dive** (pipeline names the ticker)
- Active themes → schedule a **Market Rotations** piece (pipeline names the theme)
- Remaining days → **Educational** (the prompt itself finds the topic via web search)

---

## Category 1: Ticker Deep Dive & 12-Month Price Targets

**Theme:** Editorial (light background, serif headings)
**When to use:** When the weekly schedule assigns a ticker — either a new GREEN signal or a portfolio winner
**Prompt chain:** 3 steps (send each sequentially — each builds on the previous output)

### Prompt 1 of 3 — Research

```
I have attached our Sterling Signals weekly context document. Please read it carefully for system context, marketing rules, and portfolio data.

I need you to research {TICKER} (currently trading at approximately {PRICE}) for a deep-dive article.

Please use web search to find:
1. Current analyst consensus price targets (find at least 3-5 analyst firms with specific targets)
2. Most recent quarterly earnings — revenue, EPS, beats/misses, guidance, key management commentary
3. Revenue and earnings growth trajectory over the past 4 quarters — is growth accelerating or decelerating?
4. Competitive positioning — who are the main competitors and what is the company's advantage?
5. Institutional ownership changes — any notable fund additions or reductions in the most recent 13F cycle?
6. Short interest as a percentage of float — and how has it trended over the past 3 months?
7. Upcoming catalysts within the next 90 days — earnings dates, product launches, regulatory decisions, conferences
8. Recent news — anything material in the past 2-4 weeks (partnerships, contracts, insider activity, analyst upgrades/downgrades)
9. The key sector/theme this company operates in — is that theme gaining or losing momentum?

Output a structured research brief with specific numbers, dates, and sources. Do not summarise vaguely — I need concrete data points I can use in an article.
```

### Prompt 2 of 3 — Analysis & Price Targets

```
Using the research you just compiled, please build a 12-month price target framework for {TICKER}:

**Bear Case** (probability: ~25%)
- What goes wrong? Identify the 2-3 specific risks that would drive the stock lower
- 12-month bear case price target: $X (representing -Y% from current price)
- What would trigger this scenario?

**Base Case** (probability: ~50%)
- The most likely path — assuming current trends continue
- 12-month base case price target: $X (representing +Y% from current price)
- Key assumptions underpinning this target

**Bull Case** (probability: ~25%)
- What goes right? The upside scenario where multiple catalysts hit
- 12-month bull case price target: $X (representing +Y% from current price)
- What specific catalysts would drive this?

**Risk/Reward Assessment:**
- Expected value calculation: (25% × bear) + (50% × base) + (25% × bull) = weighted target
- Is the risk/reward asymmetric in our favour?

**3 Key Catalysts with Timeframes:**
1. [Catalyst] — expected [date/timeframe] — potential impact [%]
2. [Catalyst] — expected [date/timeframe] — potential impact [%]
3. [Catalyst] — expected [date/timeframe] — potential impact [%]

Be specific with numbers. No vague ranges. Every target should have a clear rationale tied to the research.
```

### Prompt 3 of 3 — Article + HTML

```
Now write the final Substack article for {TICKER} and produce it as a complete, self-contained HTML document using the **Editorial theme**.

**CRITICAL — Read the marketing rules in the attached context document.** Key reminders:
- Use "GREEN signal" for buy signals (NEVER use TEAL, PASS, VIOLET, AMBER)
- NEVER use these terms: HMA, RSI, MACD, Banker, UC, BoS, Gatekeeper, Investment Gate, conviction scores, 5-gate, profit lock, tiered stop, Beta >= 1.5
- System references: use "proprietary screening system" or "our screening system"
- Only show entry prices for positions with 25%+ gains
- NEVER mention losses, negative P&L, or stopped positions
- Conviction language: "Extremely Bullish" / "Bullish" / "Watching" — never numbers

**Article Structure (1000-1500 words):**

1. **The Pitch** — 2-3 sentence elevator pitch. Why should the reader care about this stock right now?
2. **The Thesis** — What structural trend or catalyst is driving this? Connect to the broader theme.
3. **Why Now** — What changed recently? Why did our system flag this and not 6 months ago? What's the inflection?
4. **The Numbers** — Revenue trends, margin profile, valuation context. Make the data accessible. Use specific quarterly numbers from your research.
5. **12-Month Price Targets** — Present the bear/base/bull framework from the previous step. Include the probability-weighted expected value.
6. **Bear Case** — Honest assessment. What could go wrong? Then explain why you believe the risk is manageable.
7. **Key Risk to Monitor** — One specific thing to watch. An upcoming date, a metric, a competitive development.
8. **Our View** — Confident summary. What is our outlook and what are we doing?
9. **Footer** — "Subscribe to Sterling Signals for weekly analysis and GREEN signals: https://sterlingsignals.substack.com"

**HTML THEME — Editorial:**
- Background: #fafaf8, container: #fff, max-width: 680px
- Headings: Georgia, 'Times New Roman', serif
- Body text: system sans-serif stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial)
- Text colour: #1a1a1a, muted: #6b6b6b
- Price target section: use coloured banners — Bear (#fdf6f4, text #8b3a1a), Base (#f4f7fa, text #1b3a5c), Bull (#f4faf5, text #2e5e3e)
- Tables: dark header (#2c2520, text #f0ebe4), alternating row bg #faf9f7
- Callout boxes: border-left 3px solid, light background
- Include `[CHART: {TICKER}]` placeholder where the chart image should go

**Output the complete HTML document** with all styles in a `<style>` block. The HTML must be self-contained and render correctly when pasted into Substack.

**Tone:** Authoritative but accessible. Like a research initiation from a sharp analyst who explains things clearly. Data-driven, confident, educational. The reader should learn something about this company they didn't know.
```

---

## Category 2: Educational

**Theme:** Editorial (light background, serif headings)
**When to use:** When the weekly schedule assigns an educational day — or any day you want to teach a concept
**Prompt chain:** 2 steps

### Prompt 1 of 2 — Research

```
I have attached our Sterling Signals weekly context document. Please read it carefully for system context, marketing rules, and portfolio data.

I need to write an educational Substack article about a financial concept or strategy relevant to small-cap growth stock investing.

**Topic:** [Either paste the specific topic from the weekly schedule, OR write "Please use web search to identify a compelling topic — look for recent financial studies, strategy research, or data-driven insights related to small-cap investing, momentum strategies, sector rotation, portfolio construction, or risk management. Choose something with real data that our audience of active US investors and swing traders would find valuable and actionable."]

Please use web search to find:
1. Academic studies or institutional research papers related to the topic (find at least 2-3 with specific findings, sample sizes, and date ranges)
2. Historical market data that illustrates the concept (specific periods, returns, drawdowns)
3. Real-world examples — ideally from the small-cap or growth stock universe
4. Counter-arguments or limitations — what does the research say about when this approach fails?
5. Practical application — how would an individual investor actually implement this?
6. Any recent (2024-2026) data or events that make this topic especially timely

Output a structured research brief with specific citations, numbers, and examples. I need concrete evidence, not generalities.
```

### Prompt 2 of 2 — Article + HTML

```
Using the research you compiled, write an educational Substack article and produce it as a complete, self-contained HTML document using the **Editorial theme**.

**CRITICAL — Read the marketing rules in the attached context document.** Key reminders:
- NEVER use: HMA, RSI, MACD, Banker, UC, BoS, Gatekeeper, conviction scores, 5-gate, Beta >= 1.5
- System: "proprietary screening system" or "our screening system"
- Only showcase positions with 15%+ gains; only show entry prices at 25%+ gains
- NEVER mention losses or negative P&L
- If referencing our portfolio winners from the context document, weave them in naturally as examples

**Article Structure (800-1200 words):**

1. **Hook** — Open with a surprising stat, a provocative question, or a counterintuitive finding from the research. Make the reader stop scrolling.
2. **The Concept** — Teach the core idea in accessible language. Use an analogy if it helps. Our voice uses medical-investor metaphors naturally: "Like a good clinician, we diagnose before we prescribe."
3. **The Evidence** — This is the substance. Cite the studies and data you found. Specific numbers, time periods, sample sizes. "A 2023 study of 3,400 small-cap stocks found that..." — this is what makes the article credible.
4. **How We Apply It** — Connect to our screening system using marketing-safe language. Show how this concept is embedded in our process. Reference portfolio winners from the context document as proof where relevant.
5. **The Takeaway** — One actionable insight the reader can implement. Be specific, not vague.
6. **Engagement Close** — End with a genuine question that invites discussion.
7. **Footer** — "Learn more in our weekly newsletter: https://sterlingsignals.substack.com"

**HTML THEME — Editorial:**
- Background: #fafaf8, container: #fff, max-width: 680px
- Headings: Georgia, 'Times New Roman', serif
- Body: system sans-serif, colour #1a1a1a
- Callout boxes for key stats: border-left 3px solid #3d5a80, background #f4f7fa
- Blockquotes for study citations: italic, border-left #c8bfb4
- Financial tables for any data comparisons: dark header (#2c2520), alternating rows

**Output the complete HTML document** with all styles in a `<style>` block.

**Tone:** Teacher, not preacher. The reader should feel smarter after reading this. Ground every claim in data. Medical-investor voice where natural — precise, evidence-based, slightly contrarian. Keep it light and engaging, never dry or academic.
```

---

## Category 3: Market Rotations & Growth Themes

**Theme:** Dashboard (dark background, teal accents)
**When to use:** When the weekly schedule assigns a theme — either a top-ranked scanner theme or a broader rotation story
**Prompt chain:** 2 steps

### Prompt 1 of 2 — Research

```
I have attached our Sterling Signals weekly context document. Please read it carefully for system context, marketing rules, portfolio data, and this week's theme analysis.

I need to write a Substack article about a market rotation or growth theme that investors should be targeting.

**Theme:** [Either paste the theme details from the weekly schedule — e.g. "The theme is AI Power Infrastructure & Grid Modernization. Our scanner scored it 8.6/10 with classification PRIME. The thesis from our system: [copy thesis from Section 2 of context doc]. Key catalysts: [copy catalysts]." — OR write "Please use web search to identify the most compelling sector rotation or growth theme happening right now in US markets. Look for evidence of institutional capital flows into a specific sector or theme."]

Please use web search to find:
1. ETF flows for relevant sector ETFs over the past 1-3 months — which ETFs are seeing inflows vs outflows? (be specific with ETF tickers and dollar amounts if available)
2. Institutional positioning — any notable fund moves, 13F trends, or hedge fund commentary on this theme?
3. Policy and regulatory catalysts — government spending, legislation, regulatory changes driving the theme
4. Earnings evidence — have companies in this theme been beating estimates? What is the revenue growth trend across the sector?
5. Key companies positioned to benefit — which stocks are pure-play exposures to this theme?
6. Risks to the thesis — what could derail this rotation? Is the theme getting crowded?
7. Historical parallels — has a similar rotation happened before? What were the returns?
8. Timeline — is this an early-stage theme with years of runway, or a late-stage trade getting crowded?

Output a structured research brief with specific data points, ETF tickers, stock names, and flow numbers.
```

### Prompt 2 of 2 — Article + HTML

```
Using the research you compiled, write a market rotation / growth themes article and produce it as a complete, self-contained HTML document using the **Dashboard theme**.

**CRITICAL — Read the marketing rules in the attached context document.** Key reminders:
- Use "GREEN signal" for buy signals (NEVER use TEAL, PASS, VIOLET, AMBER)
- NEVER use: HMA, RSI, MACD, Banker, UC, BoS, Gatekeeper, Investment Gate, conviction scores, 5-gate, profit lock, tiered stop
- System: "proprietary screening system", "sector flow analysis", "institutional accumulation divergence"
- Only showcase positions with 15%+ gains; only show entry prices at 25%+ gains
- NEVER mention losses or negative P&L
- Reference portfolio positions that align with this theme as validation (from the context document)

**Article Structure (800-1200 words):**

1. **Why This Theme, Why Now** — Open with the strongest data point. A specific ETF flow number, a policy catalyst, an earnings surprise. Make the case that capital is moving here.
2. **The Investment Thesis** — Explain the structural dynamics driving this theme. Why is institutional capital flowing here? What's the multi-year story?
3. **The Evidence** — ETF flows, institutional moves, earnings trends, policy catalysts. This is the proof section. Specific numbers and dates.
4. **What Our System Sees** — Connect to our scanner's theme analysis. How does our system score this theme? Which stocks in our portfolio or watchlist are positioned here? Use marketing-safe language.
5. **Risks to the Thesis** — Balanced assessment. What could go wrong? Is the trade getting crowded?
6. **What We're Watching** — Specific upcoming events, data releases, or earnings dates that will test the thesis
7. **Stocks Positioned** — Name 3-5 specific stocks that are well-positioned within this theme (from scanner data or your research)
8. **Footer** — "Get weekly theme analysis and GREEN signals: https://sterlingsignals.substack.com"

**HTML THEME — Dashboard:**
- Dark background: #111827, card background: #1F2937, max-width: 680px
- Teal accent: #2DD4BF, green: #22C55E, amber: #FBBF24
- Text: #F9FAFB (primary), #9CA3AF (muted)
- Font: system sans-serif throughout
- Use card-based layout with subtle borders (#374151)
- Stat grid for key numbers (ETF flows, sector returns, etc.) — 2 or 3 column grid with teal labels
- Theme score card if scanner data available — progress bar with teal fill
- Use teal for positive highlights, amber for caution, green for growth metrics

**Output the complete HTML document** with all styles in a `<style>` block.

**Tone:** Sharp, opinionated, data-backed. Like a hedge fund's weekly sector note — institutional quality but accessible to individual investors. Confident about where capital is flowing, honest about risks.
```

---

## Category 4: Performance Review (Sunday Newsletter)

**Theme:** Dashboard (dark background, teal accents)
**When to use:** Every Sunday — this is the weekly newsletter
**Prompt chain:** Single comprehensive prompt

### Prompt

```
I have attached our Sterling Signals weekly context document. Please read it thoroughly — it contains our complete scanner results, portfolio data, theme analysis, equity curve, and market analysis for this week.

Please also use web search to get:
1. SPY YTD return and this week's performance
2. QQQ (NASDAQ-100) YTD return and this week's performance
3. Russell 2000 (IWM) YTD return and this week's performance
4. VIX current level and weekly change
5. Any notable market events from this week that moved markets

Now write the Sunday newsletter for Sterling Signals — Week {WEEK_NUMBER} — and produce it as a complete, self-contained HTML document using the **Dashboard theme**.

**CRITICAL — Read the marketing rules in the attached context document.** Key reminders:
- "GREEN signal" only (NEVER TEAL/PASS/VIOLET/AMBER)
- NEVER use: HMA, RSI, MACD, Banker, UC, BoS, Gatekeeper, Investment Gate, conviction scores, 5-gate, profit lock, tiered stop
- System: "proprietary screening system", "institutional accumulation divergence", "structural pivot confirmation"
- Only showcase positions with 15%+ gains; only show entry prices at 25%+ gains
- NEVER mention losses, negative P&L, or stopped positions
- If no new signals this week, frame selectivity as a feature: "The scanner found zero stocks meeting all criteria this week. That's not a bug — it's discipline."

**Newsletter Structure (1200-1500 words):**

1. **Market Context** — What happened in markets this week? 2-3 sentences using the fresh data you just searched. SPY, QQQ, notable moves.
2. **What Our Scanner Found** — The screening funnel. How many stocks scanned → how many passed technical gates → how many theme-confirmed → how many GREEN signals. Include `[SCAN_FUNNEL]` placeholder. Frame the rejection rate as proof of selectivity.
3. **Themes Driving Momentum** — Analyse the top 2-3 themes from the context document. What's hot, what's cooling, where is institutional capital flowing? Include `[THEME_SCORES]` placeholder.
4. **New GREEN Signals** — If we have new signals, present each with: the pitch, the theme alignment, why it cleared all gates. Use marketing-safe language. Include `[CHART: TICKER]` for each. **OR** if no signals: "Why We Passed" section about disciplined selectivity.
5. **Portfolio Performance** — Showcase winners. How the portfolio is performing vs SPY and QQQ. Alpha generated. Include `[WINNERS_TABLE]` placeholder.
6. **Benchmark Battle** — Specific comparison: Portfolio return vs SPY YTD vs QQQ YTD. Use the fresh benchmark data you searched.
7. **Looking Ahead** — What catalysts, earnings, or events are on deck for next week? 3-5 specific items with dates.
8. **Footer** — "Subscribe to Sterling Signals for the full weekly analysis: https://sterlingsignals.substack.com"

**HTML THEME — Dashboard:**
- Dark background: #111827, card bg: #1F2937, max-width: 680px
- Teal: #2DD4BF, green: #22C55E, amber: #FBBF24, text: #F9FAFB, muted: #9CA3AF
- System sans-serif font throughout
- Card-based layout with #374151 borders
- Stat grid (2-3 columns) for key metrics: portfolio return, SPY alpha, positions count, win rate
- Winners table: dark rows, green P&L numbers
- Funnel visualisation: stepped blocks showing scan narrowing
- Theme cards with progress bar fills

**Output the complete HTML document** with all styles in a `<style>` block.

**Tone:** Confident and direct. The newsletter should feel like a weekly briefing from a trusted analyst. Lead with the most important number. Be specific with every data point. If it was a great week, show it. If it was quiet, show the discipline.
```

---

## Daily Notes Prompt

**Use this prompt every day to generate 3 fresh Substack Notes.**

Notes are independent of the day's post — they should feel natural, varied, and sincere. Copy this prompt, fill in the day, and send to Claude.ai.

### Prompt

```
I have attached our Sterling Signals weekly context document. Please read it for portfolio data, themes, system context, and marketing rules.

Please also use web search to check:
- How SPY, QQQ, and IWM (Russell 2000) are performing today/this week
- Any notable sector moves, earnings surprises, or market news from today
- VIX level and any unusual options activity if relevant

Now generate 3 Substack Notes for {DAY} (today). These are short social posts — not articles.

**What I want:** Three varied, sincere notes that feel like they come from a real person building a newsletter about small-cap momentum investing. They should be intelligent and light in tone. Not every note needs to be about data — some can be reflective, curious, or community-building.

**The 3 notes should be different from each other.** Mix and match from these styles:
- **Winner spotlight** — Highlight a portfolio position doing well (15%+ gain only), explain the theme behind it, ask what others are seeing in that space
- **Market observation** — A quick take on today's/this week's market action. What sectors are moving? Where is capital rotating? What's interesting about small-cap activity?
- **Learning reflection** — Share something we've learned about investing, about building a newsletter, about the process of systematic screening. Be genuine about the journey.
- **Community question** — Ask something you genuinely want to know from readers. What themes they're watching, how they handle drawdowns, what their process looks like. Make it feel like a real conversation, not a marketing prompt.
- **Teaching moment** — A financial concept, a stat, a historical pattern. Something the reader can learn from in 30 seconds.
- **System insight** — What our screening system is seeing right now. How many stocks passed, how selective it's being, what the funnel looks like. Frame discipline as the edge.
- **Theme spotlight** — One specific theme from this week's analysis. Why capital is flowing there, what the catalysts are, which companies are positioned.

**Format Rules (CRITICAL):**
- 150-300 words each (100-200 for pure engagement questions)
- NO markdown headers (no #, ##, ###)
- NO bullet lists (no •, -, *)
- Flowing paragraphs and single-line statements only
- $TICKER format when mentioning stocks, include price or percentage where relevant
- Light use of emoji for visual breaks — a single 📊 or 🔍 at most, never multiple
- End EVERY note with: "Not financial advice. Informational only."

**Marketing Rules (CRITICAL — from the context document):**
- "GREEN signal" only (NEVER use TEAL, PASS, VIOLET, AMBER)
- NEVER use: HMA, RSI, MACD, Banker, UC, BoS, Gatekeeper, Investment Gate, conviction scores, 5-gate, profit lock, tiered stop
- System: "proprietary screening system" or "our screening system"
- Only mention winning positions (15%+). Only show entry prices at 25%+ gain.
- NEVER mention losses, negative P&L, or stopped positions.

**Tone:** Sincere, intelligent, light. Like a thoughtful investor sharing observations over coffee. Not salesy, not hype-y, not performatively humble. Just genuine curiosity and measured confidence. The medical-investor voice is natural when it fits — "we diagnose trends the way we once diagnosed patients" — but don't force it into every note.

Output the 3 notes clearly separated, numbered 1-3.
```

---

## Quick Reference

### Signal Branding
- ✅ **"GREEN signal"** for buy signals
- ❌ NEVER: TEAL, PASS, VIOLET, AMBER, purple, STRONG BUY, SPEC BUY

### Banned Terms (Never Use in Any Content)
**Indicators:** HMA, Hull Moving Average, RSI, MACD, KDJ, VWAP, Banker, Banker indicator, UC, Undercurrent, BoS, Break of Structure, ExD, Beta >= 1.5
**System internals:** Gatekeeper, Investment Gate, Deep DD, 5-gate, 5th Gate, Gate 1-5, Tier 1/2/3, conviction score, conviction 1-10 (any number), theme scoring, profit lock, tiered stop, gear shift, price cap, $25 cap, kill switch, compound exit, STRONG BUY, SPEC BUY, NO GO
**Old branding:** TEAL signal, VIOLET signal, AMBER signal, PASS signal, Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria
**Geography:** UK ISA, ISA account, GMT, BST, UK Time, Roth IRA, PDT, 401(k)

### Approved Alternatives
| Instead of... | Use... |
|---------------|--------|
| HMA/Banker/indicators | "proprietary screening system" or "our screening system" |
| Entry signal | "momentum confirmed", "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation divergence" |
| Stop hit / exit | "systematic exit discipline", "the system triggered an exit" |
| Conviction 8-10 | "Extremely Bullish" |
| Conviction 7 | "Bullish" |
| Conviction 4-6 | "Watching" |

### Entry Price Display Rules
- **15%+ gain**: Can showcase the position and mention P&L percentage
- **25%+ gain**: Can show entry price
- **Under 15%**: Do not highlight or showcase
- **Losses**: NEVER mention. Focus on methodology and patience instead.

### HTML Theme Specs

**Editorial Theme** (for Ticker Deep Dives, Educational)
- Background: `#fafaf8` | Container: `#fff` | Max-width: `680px`
- Headings: `Georgia, 'Times New Roman', serif`
- Body: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif`
- Text: `#1a1a1a` | Muted: `#6b6b6b` | Labels: `#8a7f72`
- Price targets: Bear `#fdf6f4`/`#8b3a1a`, Base `#f4f7fa`/`#1b3a5c`, Bull `#f4faf5`/`#2e5e3e`
- Table header: `#2c2520` text `#f0ebe4` | Alt rows: `#faf9f7`
- Callout: border-left 3px solid `#3d5a80`, bg `#f4f7fa`

**Dashboard Theme** (for Market Rotations, Performance Review)
- Dark background: `#111827` | Card bg: `#1F2937` | Max-width: `680px`
- Accent: teal `#2DD4BF` | Green: `#22C55E` | Amber: `#FBBF24`
- Text: `#F9FAFB` | Muted: `#9CA3AF` | Dim: `#6B7280`
- Borders: `#374151`
- Font: system sans-serif throughout
- Header bg: `#0F172A`
- Teal bg (for highlights): `#0D3B34`

### Visual Element Placeholders
Use these in articles — they tell you where to add charts or inject HTML components in Substack:
- `[CHART: TICKER]` — TradingView chart screenshot placeholder
- `[SCAN_FUNNEL]` — Scanning funnel visualisation (tickers → gates → signals)
- `[THEME_SCORES]` — Theme score cards with progress bars
- `[WINNERS_TABLE]` — Portfolio winners table

### Educational Topic Seeds
The learning content library has 20 pre-defined topics across 5 categories. Use these as inspiration for Educational posts, or let the prompt find its own topic via web search.

**Risk Management:** Position Sizing, Trailing Stops, Max Drawdown Math, Cash as Ammunition
**Momentum:** Structural Momentum, Institutional Accumulation, Sector Rotation, Market Breadth
**Fundamentals:** Catalyst Investing, Revenue Acceleration, Theme Alignment, Small-Cap Edge
**Psychology:** Patience Over FOMO, Systematic Discipline, Loss Acceptance, Compounding Math
**Strategy:** Screening Advantage, Theme Surfing, When to Sell, Concentration vs Diversification
