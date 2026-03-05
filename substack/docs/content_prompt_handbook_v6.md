# Sterling Signals — Content Prompt Handbook v6.1

> **Multi-prompt sequential system for Opus 4.6 + Extended Thinking**
> Each post category uses 2-3 prompts in sequence within a single context window.
> Earlier prompts research; later prompts build on that research to write.
> This maximises web search budget and model reasoning at each step.
> Last updated: March 2026

---

## How to Use This Handbook

### Daily Workflow

1. Open Claude.ai (Opus 4.6 + extended thinking)
2. Attach the daily context document (`daily_context.md`)
3. Check **TODAY'S POST** in the context doc for today's category
4. Paste that category's prompts **in sequence** (Prompt 1 → wait → Prompt 2 → wait → Prompt 3)
5. After the final post prompt, paste the **Notes Prompt** in the same conversation

Everything happens in ONE context window. Each prompt builds on what came before.
The model accumulates research across prompts, so the final article is grounded in
deep data rather than surface-level web searches crammed into a single pass.

### Prompt Count Per Category

| Category | Prompts | What Each Does |
|----------|---------|----------------|
| Ticker Deep Dive | 3 | Research → Analysis → Article |
| Educational | 3 | Discover topic → Research → Article |
| Theme Rotation | 2 | Research + validate → Article |
| Performance Review | 2 | Gather fresh data → Newsletter |
| Trade Alert (Entry) | 1 | Research + write (shorter post) |
| Trade Alert (Exit) | 1 | Research + write (shorter post) |
| Notes | 1 | Complements the post already in context |

### 4-Category Adaptive System

| Category | HTML Theme | When Assigned |
|----------|-----------|---------------|
| **Ticker Deep Dive** | Editorial (white) | New GREEN signal or portfolio winner 15%+ |
| **Theme Rotation** | Editorial (white, teal accents) | Active PRIME/INVESTABLE themes |
| **Educational** | Editorial (white) | Fills remaining days |
| **Performance Review** | Editorial (white, data cards) | Always Saturday |

**Example week:**

| Day | Category | Topic |
|-----|----------|-------|
| Saturday | Performance Review | Week 12 Newsletter |
| Tuesday | Ticker Deep Dive | $RCAT — New GREEN signal |
| Wednesday | Theme Rotation | Defence Technology — PRIME (8.4/10) |
| Thursday | Ticker Deep Dive | $LUNR — Portfolio winner +140% |

Sunday, Monday, Friday = notes only.

### When to Override

- **Trade Alert — Entry/Exit**: Replaces that day's scheduled post. Single prompt (shorter posts).

---

## Category 1 — Ticker Deep Dive (3 Prompts)

### Prompt 1 of 3 — Research

```
Read the attached context document for portfolio data, theme analysis, scanner results, and all marketing/terminology rules.

TICKER SELECTION: Check today's assignment in the context document. If a ticker is assigned, use it. If not, select the portfolio position with the highest P&L% (must be 15%+ to showcase). State which ticker you're analysing and why.

FRESHNESS CHECK: Web search the current stock price. Compare to the entry price in the context document and recalculate P&L. State the updated figures.

Now conduct deep financial research on this ticker. Use web search extensively — this is the research phase, not the writing phase. Your job is to build a comprehensive data foundation.

STAGE 1 — FINANCIAL BASELINE
Search for the most recent 10-Q/10-K, earnings releases, and investor presentations. Compile:
- Trailing 8-quarter revenue by segment (table format)
- Gross/operating/net margins per quarter (table format)
- Free cash flow for trailing 4 quarters
- Shares outstanding + 12-month dilution trend
- Debt, cash, and near-term maturities
- Short interest as % of float
- Institutional ownership changes (most recent 13F)

STAGE 2 — FORWARD REVENUE BUILD (12 months)
Per segment, search for: announced contracts, partnerships, product launches, pricing trends, TAM/SAM, customer metrics, known headwinds. Produce low/mid/high revenue estimates. Every assumption must cite a source.

Present all data as structured tables. Flag anything you couldn't find. Do NOT write the article yet — just present the research clearly. I'll ask you to analyse and write in the next prompts.
```

### Prompt 2 of 3 — Analysis

```
Good research. Now analyse what you found. Use extended thinking to work through this carefully.

STAGE 3 — MARGIN & EARNINGS PROJECTION
Using the revenue estimates from your research, project gross margins, operating margins, EPS, and FCF/share for bear/base/bull scenarios. Show your working.

STAGE 4 — VALUATION TRIANGULATION
Apply four methods:
A — Historical Multiple Range (P/E, EV/EBITDA over the company's trading history)
B — DCF (your FCF projections, current 10-year Treasury + equity risk premium)
C — Peer-Relative (4-6 competitors — compare growth rates, margins, and multiples)
D — Catalyst-Adjusted (probability-weighted impact of known 12-month catalysts)

For each method, produce bear/base/bull price targets.

STAGE 5 — SYNTHESIS
- Weight the four methods by appropriateness for this company type (e.g., DCF matters less for pre-revenue biotech)
- Derive probability weightings from your analysis — not default 25/50/25
- Calculate the probability-weighted expected value
- Identify the 3 assumptions most likely to be wrong
- State your overall conviction: is the risk/reward asymmetric or not?

Present the analysis clearly with tables. Do NOT write the article yet.
```

### Prompt 3 of 3 — Article

```
Now write the article using all the research and analysis from this conversation. You have deep data — use it. Every claim should reference something specific you found.

Write as complete, self-contained HTML using the white-background Editorial theme (specs in Quick Reference at end of handbook).

Article structure (1000-1500 words):
1. The Pitch — 2-3 sentence elevator pitch. Ticker, price, what it does, why now.
2. The Thesis — Structural trend or catalyst. Connect to the theme from the context doc.
3. Why Now — Specific inflection point. What changed recently?
4. The Numbers — Revenue trends, margins, valuation from your research. Quarterly data. Show the trajectory.
5. 12-Month Price Targets — Bear/base/bull with your probability weightings and expected value. Use coloured target cards (Bear red, Base blue, Bull green).
6. Bear Case — What could go wrong? Be honest. Use the "assumptions most likely wrong" from your analysis.
7. Key Risk to Monitor — One specific metric or date.
8. Our Position — Entry price from context doc, current P&L, what we're watching for an exit signal. If this is a new signal we haven't entered yet, state the entry zone we're targeting.
9. Footer — "Every GREEN signal, every entry, every exit — documented weekly: https://sterlingsignals.substack.com"

Include [CHART: TICKER] placeholder.

VOICE: Direct and data-heavy. You've done the research — now deliver the conclusions with confidence. Lead every section with the number, then explain it. Use contractions. Vary sentence length. Be opinionated — state your view, don't hedge into mush. No medical metaphors. No "Let's dive in." No filler paragraphs restating data. Data → insight → move on.
```

---

## Category 2 — Educational (3 Prompts)

### Prompt 1 of 3 — Discover Topic

```
Read the attached context document for portfolio data, themes, scanner results, and marketing rules.

Your job: find the most compelling educational topic for today's post. Do NOT pick a generic investing topic. Follow this priority order:

PRIORITY 1 — PORTFOLIO EVENT
Check the context document. Has any position:
- Hit a milestone (+25%, +50%, +100%)?
- Crossed near its stop level?
- Been held for an unusually long or short time?
- An upcoming catalyst (earnings, FDA, contract) in the next 2 weeks?
If yes, the lesson is whatever that trade teaches about investing.

PRIORITY 2 — SCANNER ANOMALY
Did the scanner produce an unusual result this week?
- Zero GREEN signals (teaches: patience, selectivity as edge)
- Record rejection rate (teaches: most stocks fail the filter)
- A theme flipping from PRIME to SELECTIVE (teaches: themes rotate)
If yes, the lesson is what that result teaches.

PRIORITY 3 — MARKET CONNECTION
Is there a market event this week that connects to how we invest?
- Web search for: sector rotation, volatility events, correlation breakdowns, unusual breadth readings
- Does it connect to our portfolio or themes?

PRIORITY 4 — COUNTERINTUITIVE RESEARCH
Only if priorities 1-3 don't yield a strong topic:
- Web search for counterintuitive investing studies or data from 2024-2026
- Must be a specific finding with numbers, not a generic principle

For each candidate topic, ask: Can I illustrate this with something specific from the context document — a winning position, the scanner's rejection rate, a theme?

Present your top 2-3 candidates with a one-sentence case for each. State which one you recommend and why.
```

### Prompt 2 of 3 — Research

```
Go with that topic. Now research it deeply.

Use web search to find:
- 2-3 academic studies or institutional research with specific numerical findings (not vague claims)
- A real market example that illustrates the concept — ideally from the last 12 months
- A counter-example: when does this principle fail? What's the exception?
- Historical market data that quantifies the effect (e.g., "stocks above their 200-day MA returned X% vs Y% for those below")
- How this concept applies specifically to our approach — connect to positions, themes, or screening results from the context document

Also identify from the context document: which specific position, trade, or scanner result best illustrates this principle in action right now?

Present the research clearly — studies with findings, the market example, the counter-example, and the portfolio connection. Don't write the article yet.
```

### Prompt 3 of 3 — Article

```
Now write the article using your topic selection and research. You have strong data and a clear portfolio connection — use both.

Write as complete, self-contained HTML using the white-background Editorial theme.

Article structure (800-1200 words):
1. Hook — The most surprising finding from your research. A specific number that contradicts common wisdom. Start here, not with a preamble.
2. The Concept — Teach the core idea. Accessible, clear. One paragraph.
3. The Evidence — Studies and data from your research. Specific numbers, time periods, sample sizes.
4. In Our Portfolio — THIS IS REQUIRED. Connect to a specific position, trade, or screening result from the context document. Show the principle in action with our actual data. Name the ticker, the entry price, the outcome.
5. The Exception — When does this fail? Your counter-example. This shows intellectual honesty.
6. The Takeaway — One specific, actionable insight. Not "be disciplined" — something concrete a reader could do this week.
7. Footer — "We apply these frameworks to every screening decision. See the results every Saturday: https://sterlingsignals.substack.com"

Include [CHART: TICKER] if a portfolio position is referenced.

VOICE: You just found something genuinely interesting and you're sharing it with someone who invests. Not lecturing. Not textbook. Write with the energy of "I didn't know this until I looked it up and it changes how I think about $RCAT." Use "we" and "I." Contractions. Short paragraphs. No three-adjective chains. No filler paragraphs.
```

---

## Category 3 — Theme Rotation (2 Prompts)

### Prompt 1 of 2 — Research & Validate

```
Read the attached context document for theme data, portfolio positions, and marketing rules.

THEME SELECTION: Check today's assignment. Use the assigned theme. If none, select the highest-rated PRIME or INVESTABLE theme. State the theme and its scanner score.

FRESHNESS CHECK: The context document was generated earlier. Use web search to validate and expand.

STAGE 1 — VALIDATE THE THESIS
Cross-reference the scanner's thesis with fresh data. Search for:
- Has anything changed since the context document was generated?
- New policy announcements, earnings reports, or sector news?
- Is the momentum building or fading?
- Any disconfirming evidence? Be honest — if the thesis is weakening, say so.

STAGE 2 — DEEP RESEARCH
Web search for specific data on this theme:
- ETF flows (specific ETF tickers and dollar amounts where available)
- Institutional positioning (13F trends, fund commentary, hedge fund moves)
- Policy/regulatory catalysts with specific dates
- Earnings evidence: are companies in this theme beating estimates?
- Key risks: is this getting crowded? What would derail it?
- Timeline: early innings or late stage?

STAGE 3 — OUR POSITIONS
List every portfolio position aligned with this theme from the context document. For each: ticker, entry price, current price, P&L%. If we have no positions, state that clearly.

Present all research structured and clear. Don't write the article yet.
```

### Prompt 2 of 2 — Article

```
Now write the article using your research. You've validated the thesis and have fresh data — deliver it with conviction.

Write as complete HTML using the white-background Editorial theme with teal accents:
- Same Editorial base (white bg, Georgia headings, system sans-serif body)
- Theme score: prominent card with teal (#0d9488) left border, #f0fdfa background
- Data callouts: rounded cards, #f8fafc bg, #e2e8f0 border
- Positive: #16a34a | Negative: #dc2626 | Accent: #0d9488

Article structure (800-1200 words):
1. Why This Theme, Why Now — Strongest data point first. No preamble. Lead with the most compelling number from your research.
2. The Investment Thesis — Structural dynamics. Multi-year story. Why this isn't just noise.
3. The Evidence — ETF flows, institutional moves, earnings beats, catalysts. All from your research. Numbers.
4. Our Positions — Every portfolio position in this theme with entry prices and current P&L. If none: "We're watching but haven't found a setup that clears all gates yet."
5. Risks — What would make this thesis wrong? Balanced but direct.
6. What We're Watching — Specific upcoming events with dates from your research.
7. Stocks Positioned — 3-5 stocks benefiting, including any from our portfolio.
8. Footer — "We score themes weekly across 1,800 stocks. Full breakdown every Saturday: https://sterlingsignals.substack.com"

VOICE: Opinionated. "Capital is flowing into defence. The data is clear." Not "There appear to be developments in the defence sector." Have a view. Back it with numbers. Acknowledge risks without hedging your thesis into nothing. Contractions. Varied sentences. No filler paragraphs. No medical metaphors.
```

---

## Category 4 — Performance Review / Saturday Newsletter (2 Prompts)

### Prompt 1 of 2 — Gather Fresh Data

```
Read the attached context document thoroughly — it has the complete scanner results, portfolio data, theme analysis, and market context for this week.

Before writing the newsletter, I need you to gather fresh data. The context document was generated earlier and some numbers may have moved.

Use web search to get current data for:

MARKET:
- SPY: current price, weekly change, YTD return
- QQQ: current price, weekly change, YTD return
- IWM (Russell 2000): current price, weekly change, YTD return
- VIX: current level
- Any major market events since the context document was generated

PORTFOLIO (check each position in the context document):
- Current price for our top 3-5 positions
- Recalculate P&L from entry prices if prices have moved >2%
- Any significant news for portfolio tickers in the last 48 hours

NEXT WEEK:
- Key earnings reports next week (especially in our themes: defence, nuclear, AI infrastructure, or whatever themes are active in the context doc)
- Fed/economic data releases
- Any sector-specific catalysts

Present everything in a clean data table. Flag any significant changes from the context document.
```

### Prompt 2 of 2 — Newsletter

```
Now write the Saturday newsletter using the context document plus the fresh data you just gathered.

This is the flagship piece. It's the primary subscriber conversion post. Every section should demonstrate why someone would pay to read this every week.

Before writing, decide: What is the most compelling story from this week? A big winner? A theme shift? Disciplined selectivity? A new signal? Lead with that story.

Write as complete HTML using the white-background Editorial theme with data-rich visual elements:
- White background (#ffffff), max-width 680px
- Stat cards: inline-block, bg #f8f7f5, border-radius 8px, padding 16px 20px
  - Large number: 28px bold #1a1a1a | Label: 12px uppercase #6b6b6b
- Screening funnel: stepped visual (nested divs, decreasing widths, green→amber→red left borders)
- Winners table: clean with entry price, current price, P&L% columns. Green (#2e5e3e) for gains.
- Theme score cards: teal accent, score/10 display
- Benchmark comparison: side-by-side stat cards (Portfolio vs SPY vs QQQ)

Newsletter structure (1200-1500 words):
1. Market Context — What happened this week. 2-3 sentences using your fresh data.
2. The Screening Funnel — Scanned → passed → theme-confirmed → GREEN. Rejection rate. Include [SCAN_FUNNEL] placeholder.
3. Themes This Week — Top 2-3 themes with scores. What's gaining, what's cooling. Include [THEME_SCORES] placeholder.
4. New GREEN Signals — If signals exist: the pitch, theme, why it cleared all gates. [CHART: TICKER]. If none: "Why We Passed" — selectivity as discipline.
5. Portfolio — EVERY open position with entry price and current P&L (use your fresh data). Best first, then the rest. Acknowledge any under pressure honestly. Include [WINNERS_TABLE] placeholder.
6. Benchmark Comparison — Portfolio return vs SPY vs QQQ using your fresh data. If outperforming, state the alpha. If underperforming, state it plainly and explain why.
7. Looking Ahead — 3-5 specific catalysts next week from your research.
8. Footer — "Every signal, every entry, every exit — before Monday's open: https://sterlingsignals.substack.com"

VOICE: Confident weekly briefing. Lead with the strongest story. Be honest about what's working and what isn't. Numbers first, narrative second. No filler paragraphs restating data. End on what's ahead, not a summary of what you just said. Contractions. Short sentences mixed with longer ones. No medical metaphors.
```

---

## Trade Alert — Entry (1 Prompt)

**Use when entering a new position. Replaces that day's scheduled post. Shorter format — single prompt is sufficient.**

### Post Prompt

```
Read the attached context document for portfolio data, theme analysis, and marketing rules.

NEW POSITION: {TICKER}

Web search for:
- Current stock price
- Recent news and catalysts (past 2 weeks)
- Most recent quarterly earnings summary
- Sector/theme performance

Cross-reference with the context document's theme analysis — does this align with a top-rated theme?

Write a Trade Alert as complete HTML using the white-background Editorial theme.

Article structure (400-800 words):
1. Trade Header — "🟢 NEW GREEN SIGNAL: {TICKER}" with company name, entry price, theme
2. Why This Company — What it does. What structural trend it's riding. 2-3 sentences.
3. What Triggered the Signal — Use approved terms only: structural pivot confirmation, momentum confirmed, institutional accumulation patterns.
4. The Setup — 3-5 specific financial data points from web search.
5. What We're Watching — The specific metric, date, or event that confirms or invalidates
6. Risk — One sentence risk. One sentence why we took the trade anyway.
7. Footer — "Every GREEN signal documented with entry price and reasoning: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder.

VOICE: Decisive. Short sentences. "We're entering $TICKER at $X. Here's why."
```

---

## Trade Alert — Exit (1 Prompt)

**Use when closing a position. Replaces that day's scheduled post.**

### Post Prompt

```
Read the attached context document for portfolio data and marketing rules.

CLOSING POSITION: {TICKER}

Look up entry price and P&L in the context document. Web search for current price and recalculate.

Also search for:
- Recent news affecting this position
- Current state of the theme/sector

CRITICAL FRAMING:
- If profitable (any gain): Lead with the return. "$TICKER closed at $X. +Y% in Z weeks from our $ENTRY entry."
- If profitable 15%+: The system worked. Show it.
- If at a loss or small gain: DO NOT state the P&L number. Frame as: "Our systematic exit discipline triggered on $TICKER." Focus on what changed. NEVER use "loss", "stopped out", "down", "negative", "underperformed."

Write as complete HTML using the white-background Editorial theme.

Article structure (400-800 words):
1. Trade Header — If profitable: "TRADE CLOSED: {TICKER} — +Y% in Z weeks"
   If not profitable: "POSITION UPDATE: {TICKER} — Systematic Exit"
2. The Exit — What changed? What did the system see?
3. What Changed — Specifics from web search
4. The Lesson — One thing this trade teaches
5. What's Next — Redeploying or patient?
6. Footer — "Every entry and exit documented with full reasoning: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder.

VOICE: Measured. An exit is a decision, not an apology.
```

---

## Notes Prompt (Sequential — After Post Prompts)

**Paste this AFTER all post prompts in the same conversation.**
**The model already has the context document + research + the post it just wrote.**

### Notes Prompt

```
You've just written today's post in this conversation. Now generate 3 Substack Notes that COMPLEMENT it — different tickers, different angles.

Check the context document for today's note schedule. The system uses these 12 types:

MARKET_SNAPSHOT — SPY/QQQ/VIX + what it means for our specific positions
SIGNAL_DROP — New GREEN signal: ticker, price, funnel stats
WINNER_RECEIPT — One position: entry, current, P&L%, days, theme
PORTFOLIO_UPDATE — Honest snapshot of all positions
THEME_ROTATION — One theme: score, catalysts, our positions in it
THE_FILTER — Screening funnel numbers
CATALYST_WATCH — Upcoming events for our positions
SECTOR_FLOW — Where money is moving, connected to our themes
EXIT_DEBRIEF — Position closed: why, what the system saw
ALPHA_SCOREBOARD — Portfolio return vs SPY/QQQ
DATA_INSIGHT — Counterintuitive investing stat, connected to current context
READER_QUESTION — Data-seeded question for engagement

RULES:
- Notes must cover DIFFERENT tickers and themes than today's post
- Each note: 150-280 words, no headers, no bullet lists, short paragraphs
- Lead every note with a specific number or data point — never a question
- After the data, one forward-looking thought, then subscribe hook, then disclaimer
- Never restate in abstract terms what you just showed with numbers
- Use contractions. Vary sentence length. Be blunt when appropriate.
- Never use: "Let's dive in", "Here's the thing", "It's worth noting", "This is what X looks like"
- $TICKER format with prices always

FRESHNESS: Web search for SPY, QQQ current move, VIX, and any breaking news for portfolio tickers.

SUBSCRIBE HOOKS (vary across the 3 notes):
- "Every position, every entry price, every week — in the Saturday newsletter."
- "Subscribers got this signal before Monday's open. The next screening drops Friday."
- "Full analysis — entry reasoning, theme alignment, exit plan — every Saturday."
- "We score themes weekly across 1,800 stocks. Full breakdown every Saturday."
For READER_QUESTION type: no hook, end with the question.

Each note as self-contained HTML:
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
[content — <p> tags, <strong> for emphasis]
<p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
</div>

Output as [NOTE 1], [NOTE 2], [NOTE 3].
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

**Vague/generic:** "theme keeps delivering", "system keeps working", "trust the process", "some interesting setups", "a few tickers", "interesting developments", "stay tuned", "more to come", "keep an eye on", "picks and shovels", "still bleeding", "loser", "dragging down"

**AI-sounding:** "Let's dive in", "Here's the thing", "It's worth noting", "Interestingly enough", "In today's market", "Let me break this down", "The bottom line is", "This is what X looks like", "That's the power of Y", "This is why we Z"

### Approved Alternatives

| Instead of... | Use... |
|---------------|--------|
| HMA/Banker/UC/indicators | "our screening system" |
| Entry signal / HMA pivot | "momentum confirmed", "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation patterns" |
| Stop hit / exit | "systematic exit discipline", "the system triggered an exit" |
| Break of Structure | "structural trend confirmation" |
| Gatekeeper / Investment Gate | "cleared all gates" |
| Deep DD | "deep analysis" |
| Conviction 8-10 | "Extremely Bullish" |
| Conviction 7 | "Bullish" |
| Conviction 4-6 | "Watching" |
| TEAL/PASS signal | "GREEN signal" |
| Tier 1/2/3 | "high conviction" |

### Portfolio Display Rules
- **15%+ gain**: Showcase with entry price and P&L percentage
- **Under 15% (positive)**: Can mention in portfolio updates, no spotlight
- **Negative P&L**: Acknowledge honestly in portfolio updates and market snapshots. State the facts: "$ANET at $85.50, down from our $89.00 entry." NEVER use the word "loss."
- **Performance Reviews**: Show ALL positions with entry prices. Transparency builds trust.
- **Notes**: Only spotlight 15%+ winners. Red positions only in PORTFOLIO_UPDATE and MARKET_SNAPSHOT types.

### HTML Theme Specs (White Background for All)

**Editorial Theme** (all post types)
- Background: `#ffffff` | Container max-width: `680px` | Padding: `40px 24px`
- Headings: `Georgia, 'Times New Roman', serif` | Color: `#1a1a1a` | h1: 28px, h2: 22px, h3: 18px
- Body: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif` | 16px | line-height 1.7 | Color: `#2d2d2d`
- Section dividers: `1px solid #e8e4df` | Spacing: `32px 0`
- Muted: `#6b6b6b` | Labels: `#8a7f72`
- Price target cards: border-radius 8px, padding 16px 20px
  - Bear: bg `#fdf6f4`, border-left `4px solid #dc2626`, text `#8b3a1a`
  - Base: bg `#f4f7fa`, border-left `4px solid #2563eb`, text `#1b3a5c`
  - Bull: bg `#f4faf5`, border-left `4px solid #16a34a`, text `#2e5e3e`
- Tables: header `#f8f7f5`, alt rows `#fafaf8`, border `1px solid #e8e4df`
- Callout: border-left `3px solid #3d5a80`, bg `#f4f7fa`, padding 16px
- Positive: `#2e5e3e` | Negative: `#a04030`

**Theme Rotation accent:** theme score card border-left `4px solid #0d9488`, bg `#f0fdfa`. Data cards: bg `#f8fafc`, border `#e2e8f0`.

**Performance Review accent:** stat cards inline-block bg `#f8f7f5`, large number 28px bold, label 12px uppercase. Funnel: nested divs decreasing width. Benchmarks: side-by-side cards.

**Notes Theme**
- Transparent bg | Max-width `680px` | Padding `20px`
- System sans-serif 16px, line-height 1.6 | Text `#1a1a1a`
- Disclaimer: `#6b6b6b` 13px, border-top `1px solid #e0ddd8`

### Visual Placeholders
- `[CHART: TICKER]` — TradingView chart screenshot
- `[SCAN_FUNNEL]` — Screening funnel
- `[THEME_SCORES]` — Theme score cards
- `[WINNERS_TABLE]` — Portfolio table

---

## Prompt Count Summary

**Typical Tuesday (Ticker Deep Dive + Notes):**
- Prompt 1: Research (web search heavy — financial data)
- Prompt 2: Analysis (extended thinking — valuation work)
- Prompt 3: Article (writing — uses all accumulated context)
- Prompt 4: Notes (3 complementary notes using the full conversation)
Total: 4 prompts, ~15-20 minutes

**Typical Wednesday (Theme Rotation + Notes):**
- Prompt 1: Research & validate (web search — ETF flows, policy, earnings)
- Prompt 2: Article (writing — uses research)
- Prompt 3: Notes (3 complementary notes)
Total: 3 prompts, ~10-15 minutes

**Saturday (Performance Review + Notes):**
- Prompt 1: Gather fresh data (web search — prices, benchmarks, catalysts)
- Prompt 2: Newsletter (writing — flagship piece)
- Prompt 3: Notes (2 complementary notes — Saturday has 2 slots)
Total: 3 prompts, ~15-20 minutes

**Ad-hoc Trade Alert + Notes:**
- Prompt 1: Trade alert (research + write)
- Prompt 2: Notes (3 complementary notes)
Total: 2 prompts, ~10 minutes

---

## v6.1 Change Log

| Change | Rationale |
|--------|-----------|
| **Multi-prompt sequential workflows** | Single mega-prompts forced research + analysis + writing simultaneously, reducing quality at each step. Sequential prompts let the model go deep on research, then deep on analysis, then write with full context. |
| **Ticker Deep Dive: 3 prompts** | Research → Analysis → Article. The valuation triangulation alone benefits from its own prompt — four methods with bear/base/bull for each is substantial analytical work. |
| **Educational: 3 prompts** | Discover → Research → Article. Topic discovery is now its own step, preventing the model from picking a generic topic and rushing to write about it. |
| **Theme Rotation: 2 prompts** | Research → Article. Theme validation needs fresh web search; writing needs the accumulated research. |
| **Performance Review: 2 prompts** | Fresh data → Newsletter. Fresh prices and benchmark data should be gathered before the writing prompt fires. |
| **Trade Alerts: 1 prompt** | Shorter posts (400-800 words) with less complex research. Single prompt sufficient. |
| **Prompt count summary added** | Shows time investment per day so operator can plan. |
| **All v6 changes preserved** | Voice overhaul, anti-AI rules, anti-fabrication, white backgrounds, honest transparency, aligned notes, subscribe hooks — all carried forward. |
