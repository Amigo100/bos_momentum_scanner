# Sterling Signals — Content Prompt Handbook v7.0

> **Multi-prompt sequential system for Opus 4.6**
> Each post uses 2-3 prompts in sequence within a single claude.ai chat.
> Every post produces a companion Substack Note for the Notes feed.
> Prompts specify which mode to use: Research, Extended Thinking, or Standard.
> Last updated: March 2026

---

## How to Use This Handbook

### What This Handbook Covers

This handbook produces **Tuesday–Saturday posts and ad-hoc trade alerts.**

**Saturday's newsletter** ("The Weekly Screening") is produced by **Prompt 11** in the Sterling Prompt Library during the analysis session — NOT from this handbook. If no analysis session ran, use the **Performance Review Fallback** at the end.

### Sunday Workflow

The Sunday Cowork planner decides what to write for each day and builds prompt kits with pre-filled data. You receive the kits by email.

1. Open the prompt kit email
2. For each post day (Tue–Sat), open a **new** claude.ai chat
3. Attach the files listed in the kit (this handbook + banned_terms.py minimum)
4. Paste the portfolio context block first
5. Paste each prompt in sequence — **wait for the full response before pasting the next**
6. The final prompt produces both the article HTML AND a companion note
7. Save outputs to the repo paths listed in the kit, git push

### Choosing Your Mode

Each prompt specifies which mode produces the best results. Toggle these in claude.ai before pasting the prompt.

| Mode | Toggle | Best For | Why |
|------|--------|----------|-----|
| **Research** | Research button ON | Data gathering — financial filings, ETF flows, institutional data, tool reviews | Systematically searches 20+ sources, produces cited findings with links. Produces richer research than standard web search. |
| **Extended Thinking** | Default with Opus 4.6 | Analysis, valuation, synthesis, topic discovery | Deep reasoning with internal chain-of-thought. Best for multi-step calculations, probability weighting, connecting disparate data. |
| **Standard** | Default | Writing articles, companion notes, single-pass trade alerts | Focused output generation. No overhead from search or extended reasoning. |

**The pattern:** Research mode gathers data → Extended Thinking analyses it → Standard mode writes from it. This three-stage pipeline consistently produces the richest output.

### Content Types & Series Names

| Series | Day | Prompts | Modes | Visual |
|--------|-----|---------|-------|--------|
| **🟢 GREEN Signal** | Ad-hoc (new entry) | 1 | Standard | — |
| **Position Update** | Ad-hoc (exit) | 1 | Standard | — |
| **Deep Dive** | Tuesday | 3 | Research → Extended → Standard | Animated diagram |
| **Sector Watch** | Wednesday | 2 | Research → Standard | Carousel |
| **The Edge** | Thursday | 3 | Extended → Research → Standard | Animated diagram |
| **Investor Lessons** | Friday | 3 | Extended → Research → Standard | Carousel |
| **Tools & Tech** | Saturday | 2 | Research → Standard | Carousel |
| **The Weekly Screening** | Saturday | Prompt 11 (analysis session) | — | — |

### Title Format

| Type | Title Pattern | Example |
|------|--------------|---------|
| Newsletter | "The Weekly Screening — Week [N]: [Hook]" | "The Weekly Screening — Week 12: Defence Dominates" |
| Trade Alert Entry | "🟢 GREEN Signal: $TICKER at $[PRICE] — [Theme]" | "🟢 GREEN Signal: $ASTS at $22.80 — Space & Defence" |
| Trade Alert Exit | "Position Update: $TICKER — [Outcome]" | "Position Update: $VNET — Systematic Exit" |
| Deep Dive | "Deep Dive: $TICKER — [One-line hook]" | "Deep Dive: $ASTS — The Satellite-to-Smartphone Play" |
| Sector Watch | "Sector Watch: [Theme] ([Score]/10)" | "Sector Watch: Defence Technology (8.4/10)" |
| Educational | "The Edge: [Topic]" | "The Edge: Why 90% of Stocks Fail Our Screen" |
| Investor Lessons | "Investor Lessons: [Specific Topic]" | "Investor Lessons: The Stop Loss That Saved Our $VNET Trade" |
| Tools & Tech | "Tools & Tech: [Tool] — [Hook]" | "Tools & Tech: Finviz — The Free Screener That Finds Our Signals" |

### Weekly Calendar

**Weeks WITH new signals:**

| Day | Content | Visual |
|-----|---------|--------|
| Saturday | **The Weekly Screening** (analysis session Prompt 11) | — |
| Sunday | Notes only (2) | — |
| Monday | Notes only (3) | — |
| Tuesday | **Deep Dive: $SIGNAL1** | Animated diagram |
| Wednesday | **Sector Watch: [Top Theme]** | Carousel |
| Thursday | **Deep Dive: $SIGNAL2** or **The Edge** | Animated diagram |
| Friday | **Investor Lessons: [Principle/Case Study]** | Carousel |
| Saturday | **Tools & Tech: [Tool]** + Newsletter (if analysis session) | Carousel |

**Weeks WITHOUT new signals:**

| Day | Content |
|-----|---------|
| Tuesday | **Deep Dive: [Position Update — existing holding]** |
| Wednesday | **Sector Watch: [Top Theme]** |
| Thursday | **The Edge: [Educational]** |
| Friday | **Investor Lessons: [Principle/Case Study]** |
| Saturday | **Tools & Tech: [Tool]** |

Trade alerts (🟢 GREEN Signal / Position Update) REPLACE whatever was scheduled that day.

---

## 🟢 GREEN Signal — Trade Alert Entry (1 Prompt)

**This is your highest-engagement post type.** Publish same-day as entry. Don't wait.

### Prompt

**MODE: Standard**

```
Read the attached context document for portfolio data, theme analysis, and marketing rules.

NEW POSITION: {TICKER}

Web search for:
- Current stock price (verify against your entry)
- Recent news and catalysts (past 2 weeks)
- Most recent quarterly earnings: revenue beat/miss, guidance direction
- Sector/theme performance this month

Cross-reference with the context document's theme analysis — does this align with a top-rated theme?

TITLE: "🟢 GREEN Signal: ${TICKER} at $[PRICE] — [Theme Name]"

Write the trade alert AND a companion note as complete HTML.

═══ TRADE ALERT (400-800 words) ═══

Use the white-background Editorial theme (specs in Quick Reference).

1. Signal Header — 🟢 GREEN SIGNAL: ${TICKER} at $[PRICE]. Company name. Theme. Entry date.
2. Why This Company — What it does. What structural trend it's riding. 2-3 sentences.
3. What Triggered the Signal — Approved terms only: structural pivot confirmation, momentum confirmed, institutional accumulation patterns. What made this pass when 99%+ didn't?
4. The Setup — 3-5 specific data points from web search: revenue trajectory, margin direction, institutional activity, catalyst dates.
5. What We're Watching — The specific metric, date, or event that confirms or invalidates.
6. Risk — One sentence risk. One sentence why we took it anyway.
7. Footer — "Every GREEN signal documented with entry price and reasoning: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder.

═══ COMPANION NOTE (150-280 words) ═══

Lead with: "$TICKER at $[PRICE]. GREEN signal confirmed."
Show the funnel: "1,817 screened. This was one of [N] that passed."
One sentence on the theme.
End with: "Full signal analysis — entry reasoning, theme, and risk — just published."
Then: "Not financial advice. Informational only."

Format as self-contained HTML note (see Quick Reference for note template).

Label outputs: [TRADE ALERT HTML] and [COMPANION NOTE].

VOICE: Decisive. Short sentences. "We're entering $TICKER at $X. Here's why." Not "After careful analysis, we believe this presents an opportunity."
```

---

## Position Update — Trade Alert Exit (1 Prompt)

### Prompt

**MODE: Standard**

```
Read the attached context document for portfolio data and marketing rules.

CLOSING POSITION: {TICKER}

Look up entry price and P&L in the context document. Web search for current price and recalculate.

Also search for: recent news, current state of the theme/sector.

CRITICAL FRAMING:
- Profitable (any gain): Lead with the return. "$TICKER closed at $X. +Y% in Z weeks from our $ENTRY entry."
- Profitable 15%+: The system worked. Show it.
- At a loss or small gain: DO NOT state the P&L number. Frame: "Our systematic exit discipline triggered on $TICKER." Focus on thesis change. NEVER use "loss", "stopped out", "down", "negative."

TITLE:
- If profitable: "Position Update: $TICKER — +Y% in Z Weeks"
- If not profitable: "Position Update: $TICKER — Systematic Exit"

Write the exit alert AND companion note as complete HTML.

═══ EXIT ALERT (400-800 words) ═══

White-background Editorial theme.

1. Trade Header — Title from above with entry/exit prices (if profitable) or just the exit framing
2. The Exit — What changed? What did the system see?
3. What Changed — Specifics from web search
4. The Lesson — One thing this trade teaches about our process
5. What's Next — Redeploying capital or being patient?
6. Footer — "Every entry and exit documented: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}].

═══ COMPANION NOTE (150-280 words) ═══

If profitable: Lead with the P&L. "$TICKER closed. +Y% in Z weeks from our $ENTRY entry."
If exit discipline: Lead with the discipline angle. "Systematic exit on $TICKER. The thesis changed — here's what happened."
End with: "Full exit analysis just published."
Then: "Not financial advice. Informational only."

Label: [EXIT ALERT HTML] and [COMPANION NOTE].

VOICE: Measured. An exit is a decision, not an apology.
```

---

## Deep Dive (3 Prompts) — Tuesday/Thursday

**If this ticker was announced in Saturday's newsletter:** The newsletter already gave readers the 2-3 sentence pitch. This post delivers the FULL analysis they were promised.

**If this is a position update (no-signal week):** Use the same research framework but applied to an existing holding. "We entered $LUNR at $4.80. It's now $11.52. Here's what's changed and whether the thesis still holds."

### Prompt 1 of 3 — Research

**MODE: Research mode ON** (toggle before pasting)

```
You are researching $TICKER for a Deep Dive article. Produce structured financial data — NOT prose, NOT an article. Tables and numbers only.

CONTEXT:
- Entry price: $[ENTRY] | Current: $[CURRENT] | P&L: [+/-X%]
- Theme: [THEME NAME] ([SCORE]/10)
- [If applicable: "This ticker was flagged as a GREEN signal in Saturday's newsletter. We won't repeat that pitch — we're going deeper."]
- [If position update: "This is an existing holding. Frame as thesis refresh: is the original thesis still intact?"]

RESEARCH TASK 1 — FINANCIAL BASELINE

Search specifically for:

A) SEC EDGAR — most recent 10-Q or 10-K filing for $TICKER:
   - Revenue by segment for the last 8 quarters. Present as a TABLE with QoQ and YoY growth rates calculated for each segment.
   - Gross margin, operating margin, net margin per quarter (8 quarters) — TABLE
   - Free cash flow: operating cash flow minus capex, trailing 4 quarters
   - Balance sheet snapshot: cash + equivalents, total debt, current ratio
   - Shares outstanding now vs 12 months ago. Calculate dilution %.

B) Most recent earnings call or press release:
   - Revenue beat/miss vs consensus ($ amount AND %)
   - Was guidance raised, lowered, or maintained?
   - Key quote from CEO/CFO about forward outlook (exact quote with source)
   - Any segment-specific guidance or new product announcements

C) Institutional ownership:
   - Search for latest 13F filings mentioning $TICKER
   - Net institutional buying or selling in the most recent quarter ($ amount)
   - Name 2-3 notable funds that entered or exited (fund name + position size)
   - Short interest as % of float — current vs 3 months ago

D) Recent catalysts (last 30 days):
   - FDA decisions, regulatory rulings, government contracts
   - Analyst upgrades/downgrades — name the firm, old PT, new PT
   - Insider buying/selling — name, title, shares, $ amount (Form 4)
   - Any material partnerships, acquisitions, or product launches

RESEARCH TASK 2 — FORWARD REVENUE BUILD (next 12 months)

For EACH revenue segment identified above:
- Known contracts or backlog (with dollar values and delivery dates)
- Pipeline items with probability weights (% likelihood of closing)
- Pricing trends: ASP, ARPU, or contract values — direction and evidence
- TAM and SAM with current penetration rate
- Specific headwinds: competition, regulation, funding dependency

Build LOW / MID / HIGH revenue estimates per segment. Every assumption must cite a source (filing, earnings call, analyst report, press release).

OUTPUT FORMAT:
- Structured tables only — no prose paragraphs
- Every number must have a source citation [source: ...]
- Flag any data gaps with [GAP: could not find X — searched Y and Z]
- Do NOT write the article yet
```

### Prompt 2 of 3 — Analysis

**MODE: Extended Thinking ON, Research mode OFF**

```
Using the research data from your previous response, build a complete financial analysis. Use extended thinking to reason through the valuation carefully — show your working, not just conclusions.

ANALYSIS TASK 1 — MARGIN & EARNINGS PROJECTION

Build bear/base/bull scenarios for the next 12 months. Present as a table:

| Metric | Bear | Base | Bull |
|--------|------|------|------|
| Total revenue ($M) | | | |
| Revenue growth (YoY %) | | | |
| Gross margin (%) | | | |
| Operating margin (%) | | | |
| EPS ($) | | | |
| FCF/share ($) | | | |

For each scenario, state the ONE driving assumption:
- Bear: "[specific thing that goes wrong — name it]"
- Base: "[continuation of current trajectory with specific metric]"
- Bull: "[specific catalyst that accelerates — name the event and date]"

ANALYSIS TASK 2 — VALUATION TRIANGULATION

Apply four methods. Show full working for each — not just the answer.

METHOD A — HISTORICAL MULTIPLE RANGE:
- What P/E and EV/EBITDA has $TICKER traded at over the last 3 years? (high, low, median)
- Apply those multiples to your bear/base/bull earnings from Task 1
- Result: 3 price targets (bear, base, bull) from historical multiples

METHOD B — DCF (Discounted Cash Flow):
- Use your FCF projections from Task 1
- Discount rate: search for the current 10-Year Treasury yield, add 5% equity risk premium
- Terminal growth rate: 3% default. Adjust to 2% if mature, 4-5% if hyper-growth. State which and why.
- Show the calculation: present value of 10-year FCFs + terminal value ÷ shares outstanding
- Result: 1 intrinsic value per share

METHOD C — PEER-RELATIVE:
- Identify 4-6 peers by market cap, sector, and growth rate. Name them.
- Compare current P/E, EV/Revenue, and EV/EBITDA across all peers (table)
- Where does $TICKER sit? Premium or discount? Is the premium/discount justified?
- Result: fair value range (low–high)

METHOD D — CATALYST-ADJUSTED:
- List 3-5 specific binary events in the next 12 months (name, date, description)
- Assign each a probability (%) and price impact ($ or %)
- Calculate: current price + sum of (probability × impact) for each
- Result: catalyst-adjusted expected price

ANALYSIS TASK 3 — SYNTHESIS

Combine the four methods. DO NOT equally weight them — weight by relevance:
- Pre-revenue or early-revenue: DCF (40%) + Catalyst-Adjusted (30%) + Peer (20%) + Historical (10%)
- Mature and profitable: Historical (35%) + Peer (30%) + DCF (25%) + Catalyst (10%)
- High-growth but profitable: EV/Revenue Peer (30%) + DCF (25%) + Catalyst (25%) + Historical (20%)

State which weighting you're using and why.

Derive:
- Bear price target with probability weight (NOT default 25% — justify your number)
- Base price target with probability weight
- Bull price target with probability weight
- Expected value: sum of (target × probability)
- Risk/reward ratio: (bull upside ÷ bear downside)

Finally: what are the THREE assumptions most likely to be wrong? For each, state which direction the error would push the price and by roughly how much.

OUTPUT: Tables with full working. Do NOT write the article yet.
```

### Prompt 3 of 3 — Article + Companion Note

**MODE: Standard**

```
Write the article and companion note using ALL research and analysis from this conversation. Do not invent any numbers — use only what you researched and calculated above.

TITLE: "Deep Dive: $TICKER — [One-line hook from your strongest finding]"
Pick the single most surprising or compelling data point for the title hook.

═══ ARTICLE (1,000-1,500 words) ═══

White-background Editorial theme: 680px max-width, inline CSS only, Georgia headings, system sans-serif body (specs in Quick Reference).

[If this ticker was in Saturday's newsletter]: Open with "We flagged $TICKER as a GREEN signal on Saturday. Here's the complete analysis behind that call." Then go straight to the data.

[If this is a position update]: Open with "$TICKER at $[CURRENT], up [X]% from our $[ENTRY] entry [N] days ago. Here's what's changed and whether the thesis still holds."

STRUCTURE — every section MUST appear:

1. THE PITCH — 2-3 sentences. Ticker, price, what it does, why now. The reader should understand the company and the opportunity in 30 seconds.

2. THE THESIS — The structural trend or catalyst this company rides. Connect to the theme. Why is this a multi-year story, not a one-quarter trade?

3. WHY NOW — The specific recent inflection. What changed in the last 30 days? An earnings beat, a contract win, an FDA decision, a policy catalyst. Name the event and the date.

4. THE NUMBERS — Revenue trajectory, margin expansion or contraction, balance sheet strength. This section MUST contain an actual HTML table with quarterly data — not just prose saying "revenue is growing." Show the reader the trend with real numbers from your research.

5. 12-MONTH PRICE TARGETS — Three colour-coded stat cards:
   - Bear: red-tinted box (#fdf6f4, #dc2626 border) with price, probability %, and driving assumption
   - Base: blue-tinted box (#f4f7fa, #2563eb border) with price, probability %, and driving assumption
   - Bull: green-tinted box (#f4faf5, #16a34a border) with price, probability %, and driving assumption
   - Below the cards: "Expected value: $[X] (weighted average)" and "Risk/reward: [X]:1"

6. BEAR CASE — Use the three assumptions most likely wrong from your analysis. Be specific and honest. "If [event] happens, the base case breaks because [mechanism]."

7. KEY RISK — One specific metric, date, or event that could invalidate the thesis. Not vague ("competition") but specific ("If Q2 revenue misses by >10%, the growth narrative collapses").

8. OUR POSITION — Entry price, current P&L%, what triggers an exit. If new signal: the entry zone we're targeting and position size rationale.

9. FOOTER — "Every GREEN signal, every entry, every exit — documented weekly: https://sterlingsignals.substack.com"

Include [CHART: TICKER] placeholder after section 3 or 4.

═══ QUALITY CHECK (verify before outputting) ═══

- Does section 4 contain an actual HTML table with quarterly numbers? If it's just prose, add the table.
- Do sections 5 and 6 contain specific numbers from your analysis? Not generic statements.
- Is the article between 1,000 and 1,500 words? Count it.
- Are all prices from your research, not from memory or the prompt context?

═══ COMPANION NOTE (150-280 words) ═══

DO NOT summarise the article. Hook with the most surprising finding.

Lead with ONE number that makes a reader stop scrolling:
- "$ASTS has $265M cash, zero debt, and a patent portfolio 47 deep."
- "Our independent valuation puts $RCAT at $24 base case. It's trading at $13."
- "$LUNR: +140% in 67 days. Here's whether we're still holding."

Then 2-3 sentences of context. What does this number mean? Why should the reader care?

⛔ ANTI-SPOILER: Reveal at most ONE price target (base case only — never bear AND bull together). If readers get the conclusion from the note, they won't click through.

End with: "Full analysis with price targets just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Direct, data-heavy, opinionated. Lead with numbers. Contractions. Varied sentence length. No filler paragraphs. No "Let's dive in." No "In today's market."
```

---

## Sector Watch (2 Prompts) — Wednesday

**The newsletter named this theme and scored it.** This post delivers the depth behind the score.

### Prompt 1 of 2 — Research & Validate

**MODE: Research mode ON**

```
You are researching the [THEME NAME] sector ([SCORE]/10) for a Sector Watch article. Produce structured research data — NOT an article.

CONTEXT:
- Theme score: [SCORE]/10 (from this week's screening)
- Our positions in this theme: [list tickers with entry prices and P&L]
- [If newsletter mentioned this theme]: "Saturday's newsletter named this theme and gave a surface summary. This post goes DEEP — ETF flows, 13F data, policy catalysts."

RESEARCH TASK 1 — ETF FLOWS
Search for:
- The 3-5 largest ETFs in this sector by AUM (name them)
- Monthly net inflows/outflows for each in dollars (last 3 months)
- Any record flow months in the last 6 months
- Compare to broad market flows (SPY, QQQ inflows in same period)

RESEARCH TASK 2 — INSTITUTIONAL POSITIONING
Search for:
- Recent 13F filings from major funds mentioning stocks in this theme
- Name 2-3 specific funds and their positions (fund, ticker, shares, change)
- Is hedge fund concentration in this sector rising or falling vs 12 months ago?
- Any activist positions or notable new entrants

RESEARCH TASK 3 — POLICY & REGULATORY CATALYSTS
Search for:
- Government bills, executive orders, or budget allocations with $ amounts and timeline
- Regulatory decisions pending (FDA, DOE, DOD, FCC) with specific dates
- International policy (EU, China) that affects US companies in this theme
- Any upcoming congressional hearings or committee votes

RESEARCH TASK 4 — EARNINGS EVIDENCE
- Which companies in this theme reported recently? Beat or miss?
- Average revenue beat rate for theme stocks vs S&P 500 average
- Guidance trends: are theme companies raising or lowering?
- Any notable guidance quotes

RESEARCH TASK 5 — OUR POSITIONS
For every portfolio position in this theme:
- Ticker, entry price, current price (from web search), P&L %
- Days held, original thesis, what's changed since entry

RESEARCH TASK 6 — RISKS
- Crowding signals: is the theme's main ETF overbought? (RSI context)
- Policy reversal risk: what would undo the bullish catalyst?
- Valuation: are theme stocks expensive relative to history?
- What specific event would make you SELL the theme?

OUTPUT: Structured research with citations. No article yet.
```

### Prompt 2 of 2 — Article + Companion Note

**MODE: Standard**

```
Write the article and companion note using your research.

TITLE: "Sector Watch: [Theme Name] ([Score]/10)"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme with teal accents:
- Theme score card: teal (#0d9488) left border, #f0fdfa background
- Data callouts: rounded cards, #f8fafc background, #e2e8f0 border

Open with: "[Theme] scored [X]/10 in this week's screening." Or reference the newsletter: "We named [Theme] as our top-rated sector on Saturday. Here's the data behind that score."

STRUCTURE:
1. Why This Theme, Why Now — Lead with the strongest data point from your research. Not a summary — one number that commands attention.
2. The Investment Thesis — Structural dynamics. Multi-year story. Why does this theme have staying power?
3. The Evidence — ETF flows, institutional moves, earnings, catalysts. NUMBERS from your research — not vague statements. Include at least one stat card or callout box.
4. Our Positions — Every position in this theme with entry prices and P&L. HTML table format. If no positions: "We're watching but haven't found a setup that clears all gates."
5. Risks — What would make this wrong? Be specific. Name the event, the date, the mechanism.
6. What We're Watching — Upcoming events with specific dates and what they mean.
7. Stocks Positioned — 3-5 stocks in this theme (including ours), with current price and one-line thesis each.
8. Footer — "We score themes weekly across 1,800 stocks: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 3 cite specific dollar amounts for ETF flows? Not just "money is flowing in."
- Does section 4 have an HTML table with entry prices and P&L?
- Does section 6 list dates, not just "upcoming catalysts"?

═══ COMPANION NOTE (150-280 words) ═══

Lead with the most compelling data point:
- "$800M flowed into defence ETFs this month. Here's why."
- "3 of our 5 positions sit in one theme. It just scored 8.4/10."

Don't summarise the article. Give ONE data point that makes a reader want the full picture.

End with: "Full sector analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Opinionated. "Capital is flowing into defence. The data is clear." Contractions. No filler. No hedging into nothing.
```

---

## The Edge — Educational (3 Prompts) — Thursday

### Prompt 1 of 3 — Discover Topic

**MODE: Extended Thinking**

```
I need to find the most compelling educational topic for this week's "The Edge" post. Use extended thinking to reason carefully about what would genuinely surprise and educate active US investors.

PORTFOLIO AND SCANNER CONTEXT:
[Pre-filled by Sunday planner with all positions, P&L, recent signals, scanner stats]

Generate 3 topic candidates. For each, provide:
- The topic stated as a specific, surprising claim (not generic)
- The hook stat — the ONE number that would make someone stop scrolling
- Which portfolio position or scanner result illustrates this in our live portfolio
- Why this is timely (what happened this week that makes this relevant NOW?)
- Can you find SPECIFIC NUMBERS from web search to prove this? If it requires hand-waving, skip it.

CANDIDATE PRIORITY:
1. PORTFOLIO EVENT — a position milestone, stop proximity, catalyst hit, or sector rotation visible in our holdings (highest relevance — our audience cares about our trades)
2. SCANNER ANOMALY — "99.8% rejected", zero signals for 3 weeks, record theme score, a sector flipping from DECLINING to PRIME (showcases our system)
3. MARKET CONNECTION — sector rotation, VIX regime change, breadth divergence — something in the market that our portfolio uniquely demonstrates
4. COUNTERINTUITIVE RESEARCH — an academic study or legendary investor insight (last resort — excellent content but harder to connect to our live portfolio)

Recommend your top choice and explain why it beats the alternatives.
```

### Prompt 2 of 3 — Research

**MODE: Research mode ON**

```
Research [SELECTED TOPIC] thoroughly. I need specific, cited evidence — not general knowledge.

SEARCH FOR:

A) Academic or professional sources:
   - Studies with specific numerical findings (author, year, sample size, result)
   - Books or papers that established this concept (name the source)
   - Any contradicting studies (name them too — we need the counter-argument)

B) Real market example from the last 12 months:
   - A specific stock, sector, or event that demonstrates this principle
   - Dates, prices, percentage moves — the reader should be able to verify this

C) Counter-example — when does this principle FAIL?
   - Name a specific instance where following this advice would have lost money
   - Why did it fail in that case? What was different?

D) Historical data quantifying the effect:
   - Long-term statistics that prove or disprove the principle
   - Comparisons: investors who do X vs investors who don't — what's the performance gap?

E) Portfolio connection:
   - Current price for [illustrative ticker] from web search
   - Recalculate P&L from entry
   - How does our position, trade, or system design demonstrate or contradict this principle?
   - The specific numbers: our entry, our return, our timeline, what happened

F) One stat that contradicts common wisdom:
   - The most surprising or counterintuitive finding from your research
   - This becomes the article's hook

OUTPUT: Structured research with source citations. No article yet.
```

### Prompt 3 of 3 — Article + Companion Note

**MODE: Standard**

```
Write the article and companion note.

TITLE: "The Edge: [Topic — make it specific and surprising]"
Not generic ("Position Sizing 101") but specific and intriguing:
- "The Edge: Why the Best Portfolios Are 90% Empty"
- "The Edge: $LUNR Proves Why We Ignore Analyst Targets"
- "The Edge: The 3-Week Signal Drought That Made Us Better"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme.

STRUCTURE:
1. HOOK — The most surprising finding from your research. One sentence or number that contradicts what the reader assumes. Make them think "wait, really?"
2. THE CONCEPT — The core idea explained accessibly. One paragraph. No jargon. If a 25-year-old with a brokerage account can't understand this, simplify it.
3. THE EVIDENCE — Studies, data, specific numbers and time periods. This section should contain at least one data point with a citation. "Dalbar's 2024 study found the average equity investor earned 5.5% annualised vs the S&P 500's 10.2%."
4. IN OUR PORTFOLIO — REQUIRED. This section MUST name a specific ticker, state the entry price, show the current P&L, and explain how this principle played out in our actual trading. Not hypothetical. Real. "Our $RCAT position is up 55% from $8.50. Peter Lynch would call this a 'fast grower.' Here's his checklist applied to $RCAT."
5. THE EXCEPTION — When does this fail? Name a specific counter-example with dates and numbers. This is what separates us from clickbait.
6. THE TAKEAWAY — One concrete, actionable thing the reader can do THIS WEEK. Not "think about risk management" but "open your brokerage, check your largest position, and ask: if this drops 20% tomorrow, does it threaten my account?"
7. FOOTER — "We apply these frameworks every week: https://sterlingsignals.substack.com"

[CHART: TICKER] if a position is referenced in section 4.

═══ QUALITY CHECK ═══
- Does section 3 cite at least one study or data source with a specific number?
- Does section 4 name a real ticker with real entry price and P&L?
- Does section 5 contain a specific counter-example (not "sometimes it doesn't work")?

═══ COMPANION NOTE (150-280 words) ═══

Lead with the most counterintuitive stat:
- "The best-performing brokerage accounts belong to people who forgot their passwords."
- "Our scanner rejected 99.8% of stocks this week. That's not a bug."

2-3 sentences connecting it to our portfolio or approach.

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Energy of "I just found something that changes how I think about $RCAT." Not lecturing. Not professorial. Enthusiastic curiosity backed by data.
```

---

## Investor Lessons (3 Prompts) — Friday

**Series identity:** Case studies, legendary investors, investing principles, market mechanics, and behavioural finance — always connected to our live portfolio.

**Subcategory rotation** (check last 4 Fridays' manifests, pick least-recently-used):

| Subcategory | Description | Example Topics |
|---|---|---|
| Case Study | Famous trades, market events, company stories | Enron, GameStop, Nvidia's pivot, LTCM collapse, Tesla short squeeze |
| Legendary Investor | Principles from the greats, applied to our portfolio | Buffett's moats, Druckenmiller's concentration, Lynch's "invest in what you know", Soros's reflexivity |
| Investing Principle | Actionable techniques for active investors | Stop losses, position sizing, risk/reward ratios, sector rotation, mean reversion, momentum |
| Market Mechanics | How markets actually work behind the scenes | Short squeezes, 13F filing analysis, options flow, dark pools, index rebalancing |
| Behavioural Finance | Psychology of investing and common traps | Loss aversion, anchoring bias, FOMO, recency bias, survivorship bias, disposition effect |

### Prompt 1 of 3 — Discover Topic

**MODE: Extended Thinking**

```
Today is an Investor Lessons post. Subcategory: [SELECTED BY ROTATION].

PORTFOLIO AND SCANNER CONTEXT:
[Pre-filled by Sunday planner]

Generate 3 topic candidates. For EACH candidate:
- The topic stated as a specific, surprising claim
- The hook stat — one number that makes a reader stop
- The PORTFOLIO CONNECTION — which specific ticker, trade, or system feature from our live portfolio illustrates this lesson? This is MANDATORY.
- What makes this timely? (Why this week, not any other?)
- Shareability test: would someone repost this? What's the quotable insight?

PORTFOLIO CONNECTION IS NON-NEGOTIABLE. If you cannot connect the lesson to our portfolio or system with a specific ticker, entry price, and outcome, SKIP the topic and find one you can connect.

Good connections:
- "Druckenmiller concentrated into one trade. We hold 5 max. Here's why both work."
- "Stop losses saved us $X on $VNET. Here's the math."
- "$LUNR +140%. Peter Lynch calls this a 'stalwart turning fast grower.'"

Bad connections:
- "Buffett says be greedy when others are fearful. We agree." (too vague)
- "Loss aversion affects all investors, including us." (no specific ticker)

Recommend your top choice. Explain why the portfolio connection is strong.
```

### Prompt 2 of 3 — Research

**MODE: Research mode ON**

```
Research [SELECTED TOPIC] thoroughly.

SEARCH FOR:

A) The original source material:
   - If legendary investor: the actual shareholder letter, interview, or book chapter. Quote directly.
   - If case study: SEC filings, news articles from the time, outcome data. Dates and dollar amounts.
   - If investing principle: the academic study or practitioner paper. Author, year, sample, finding.
   - If market mechanics: how the mechanism actually works with a recent real example.
   - If behavioural finance: the original Kahneman/Tversky study or equivalent. The exact experimental finding.

B) Specific numbers that make the story compelling:
   - Returns, drawdowns, position sizes, timeframes, dollar amounts
   - The more specific, the more credible. "$1 billion profit on a single currency trade" beats "Soros made a lot of money."

C) Counter-evidence — the strongest argument against this lesson:
   - When did following this principle lose money? Name the case.
   - Is this survivorship bias? Would we know about this principle if it had failed?
   - What's the base rate of success for people who follow this advice?

D) Portfolio connection — fresh data:
   - Current price for [illustrative ticker] from web search
   - Recalculate P&L from entry price
   - How our position demonstrates or contradicts the lesson
   - Timeline comparison: our holding period vs the lesson's timeframe

E) One stat that contradicts common wisdom:
   - The counterintuitive finding that will be the article's hook

OUTPUT: Structured research with citations. No article yet.
```

### Prompt 3 of 3 — Article + Companion Note

**MODE: Standard**

```
Write the article and companion note.

TITLE: "Investor Lessons: [Specific, Surprising Topic]"
Not generic ("Position Sizing 101") but specific:
- "Investor Lessons: Druckenmiller's Biggest Bet Was 100% of His Fund"
- "Investor Lessons: The Stop Loss That Saved Our $VNET Trade"
- "Investor Lessons: Why 90% of 'Cheap' Stocks Stay Cheap Forever"
- "Investor Lessons: The 13F Filing That Predicted NVDA's Rally 6 Months Early"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme.

STRUCTURE:
1. THE HOOK — The most surprising number or claim. One sentence that makes the reader think "wait, really?" This is the reason someone shares this article.
2. THE STORY — The case study, investor, or principle explained like you're telling a friend over coffee. Use narrative, not bullet points. Make it human. If it's about Druckenmiller, tell the STORY of the trade — the setup, the conviction, the risk, the payoff.
3. THE EVIDENCE — Specific numbers. Dates. Returns. Drawdowns. Include at least one table or data comparison with real figures from your research.
4. IN OUR PORTFOLIO — REQUIRED. Name the ticker. State the entry price and current P&L. Show exactly how this principle plays out in our real trading. "Our $RCAT position is up 55% from $8.50 in 47 days. Peter Lynch's 'fast grower' checklist: ✅ Revenue growth >25%, ✅ Low institutional ownership, ✅ New product cycle."
5. THE EXCEPTION — When does this fail? Name a specific counter-example with a date and an outcome. This is intellectual honesty — it's what makes readers trust us.
6. THE TAKEAWAY — One concrete thing the reader can do THIS WEEK. Specific and actionable: "Open your portfolio. Find your largest position. Calculate: if it drops 20%, what % of your account is that? If the answer makes you uncomfortable, you're oversized."
7. FOOTER — "We study the best to build a better system: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 2 tell an actual STORY (narrative) not just list facts?
- Does section 4 name a real ticker with entry price and P&L from our portfolio?
- Does section 5 have a specific counter-example with dates and numbers?
- Is the takeaway in section 6 something the reader can literally do this week?

═══ COMPANION NOTE (150-280 words) ═══

Lead with the hook stat from section 1. Connect to our portfolio in one sentence.
Do not summarise the article — create curiosity.

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: "I just learned something that changed how I think about this trade." Enthusiasm backed by evidence. Not professorial. Not clickbait.
```

---

## Tools & Tech (2 Prompts) — Saturday

**Series identity:** Specific tools that help investors analyse, screen, research, and manage portfolios. Every tool is demonstrated on a real ticker from our portfolio.

**Subcategory rotation** (check last 4 Saturdays' manifests, pick least-recently-used):

| Subcategory | Example Tools |
|---|---|
| Screeners & Scanners | Finviz, TradingView screener, EDGAR full-text search |
| Charting Platforms | TradingView setup guide, key indicators, template sharing |
| Data & Research | Koyfin, Simply Wall St, Macrotrends, FRED, Quiver Quant |
| Portfolio Management | Position sizing calculators, correlation matrices, brokerage features |
| AI & Automation | Claude for 10-K analysis, Perplexity for earnings, AI screener tools |
| Free vs Paid | "The free tools that replace $500/year subscriptions" |

### Prompt 1 of 2 — Research & Test

**MODE: Research mode ON**

```
Research [TOOL NAME] for a Tools & Tech article. Demonstrate it on $TICKER from our portfolio.

CONTEXT:
- Tool: [TOOL NAME]
- Demo ticker: $TICKER (entry $[ENTRY], current $[CURRENT], +[X]%)
- Theme: [THEME NAME]

SEARCH FOR:

A) Tool basics:
   - Official website URL and pricing page
   - Free tier: what's included, what's limited
   - Paid tiers: price, what you get, worth it or not
   - Who is this for? Beginner, intermediate, professional?

B) Live demo on our ticker:
   - Go to [TOOL] and search for $TICKER
   - What data does it surface? (describe each screen/section)
   - What metrics or insights stand out?
   - Does it show anything our scanner or portfolio.csv doesn't capture?
   - Describe what the reader would SEE at each step (since we can't embed screenshots)

C) Workflow — step-by-step:
   - Step 1: [URL to visit]
   - Step 2: [What to type/click]
   - Step 3: [What to look for]
   - Step 4: [How to interpret the result]
   - Step 5: [What action to take based on findings]

D) Comparison to alternatives:
   - Top 2-3 competing tools (name them)
   - What does this tool do better?
   - What does it do worse?
   - Pricing comparison table if relevant

E) Limitations:
   - Data accuracy issues or delays
   - Missing features that matter for our strategy
   - Edge cases where the tool gives misleading results
   - When to use something else instead

OUTPUT: Structured research. No article yet.
```

### Prompt 2 of 2 — Article + Companion Note

**MODE: Standard**

```
Write the article and companion note.

TITLE: "Tools & Tech: [Tool Name] — [What It Does in One Line]"
Examples:
- "Tools & Tech: Finviz — The Free Screener That Finds Our Signals"
- "Tools & Tech: Koyfin — Institutional-Grade Charts for $0"
- "Tools & Tech: Using Claude to Read 10-Ks in 5 Minutes"
- "Tools & Tech: The TradingView Setup Every Momentum Trader Needs"

═══ ARTICLE (600-1,000 words) ═══

White-background Editorial theme.

STRUCTURE:
1. THE PROBLEM — What analysis challenge does this tool solve? Start with the reader's pain point, not the tool's features. "You want to know if institutions are buying your stock. Bloomberg costs $25,000/year. Here's a free alternative."
2. THE TOOL — What it is, free or paid, who it's for. 2-3 sentences max. Don't oversell.
3. HOW WE USE IT — Step-by-step walkthrough with $TICKER from our portfolio. "I typed ASTS into Finviz's screener. Here's what came up..." Be specific: what fields, what filters, what data appeared on screen.
4. WHAT IT FOUND — The actual output, interpreted for the reader. "Finviz showed institutional ownership jumped from 12% to 28% in Q4. Our scanner flagged the same trend via different data — confirming the thesis from two angles."
5. LIMITATIONS — What it misses, gets wrong, or costs too much for. Be honest — our readers trust reviews that acknowledge weaknesses. "Finviz data lags by one day. For same-day moves, you need..."
6. SETUP GUIDE — 3-5 numbered steps to get started. Include the URL. Make it so a reader can follow along right now. "Step 1: Go to finviz.com. Step 2: Click 'Screener.' Step 3: Set..."
7. FOOTER — "We use these tools alongside our screening system: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 3 describe a specific workflow with $TICKER? Not generic.
- Does section 4 contain specific data the tool surfaced? Not "it shows useful information."
- Does section 6 have numbered steps with a real URL?

═══ COMPANION NOTE (150-280 words) ═══

Lead with what the tool found on our ticker:
"I ran $LUNR through [tool]. It flagged 3 things our scanner missed."
"Bloomberg costs $25K/year. This free tool does 80% of the job."

2-3 sentences on what makes this tool worth the reader's time.

End with: "Full walkthrough with setup guide just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Helpful, practical, opinionated. "I've tested dozens of tools. This one actually works." Not sponsored content — genuine assessment.
```

---

## Performance Review — FALLBACK ONLY

**Use ONLY when no analysis session was run that week.** Saturday's newsletter normally comes from Prompt 11 in the analysis session.

### Prompt 1 of 2 — Gather Fresh Data

**MODE: Research mode ON**

```
Read the attached context document. No analysis session was run this week, so we're producing the newsletter from the context document alone.

Web search for current data:

MARKET: SPY, QQQ, IWM — current price, week change, YTD return. VIX current. Major events this week.
PORTFOLIO: Current prices for ALL open positions. Recalculate P&L from entry prices in context document.
THEMES: Status of our tracked themes — any catalysts this week?
NEXT WEEK: Earnings dates for tickers in our themes. Fed/data releases. Sector catalysts.

Present everything in structured tables. Flag any significant changes from context document data.
```

### Prompt 2 of 2 — Newsletter + Companion Note

**MODE: Standard**

```
Write "The Weekly Screening" newsletter and companion note.

TITLE: "The Weekly Screening — Week [N]: [Hook]"

Follow the same structure as the analysis session newsletter (sections 1-9 from Prompt 11), but use the context document data + your fresh web search data.

Since there was no new analysis session, section 4 (New Signals) should either:
- Reference any signals from LAST week's session if still relevant
- Or run "Why We Passed" framing about selectivity

Include a "Coming This Week" section previewing midweek content.

Produce companion note (ALPHA_SCOREBOARD type — lead with strongest portfolio number vs benchmark).

White-background HTML with stat cards, funnel, portfolio table (same specs as Prompt 11).

Label: [NEWSLETTER HTML] and [COMPANION NOTE].
```

---

## Quick Reference

### Signal Branding
- **"GREEN signal"** for buy signals
- NEVER: TEAL, PASS, VIOLET, AMBER, STRONG BUY, SPEC BUY

### Banned Terms

**Indicators:** HMA, Hull Moving Average, RSI, MACD, KDJ, VWAP, Banker, UC, Undercurrent, BoS, ExD, Beta >= 1.5, compound exit, 20% trailing stop

**System internals:** Gatekeeper, Investment Gate, Deep DD, 5-gate, Tier 1/2/3, conviction score, conviction 1-10, profit lock, tiered stop, gear shift, price cap, $25 cap, kill switch, STRONG BUY, SPEC BUY, NO GO

**Old branding:** TEAL/VIOLET/AMBER/PASS signal, Capital Preservation Protocol

**Geography:** UK ISA, GMT, BST, Roth IRA, PDT, 401k

**Vague:** "interesting setups", "keep an eye on", "stay tuned", "more to come", "picks and shovels"

**AI-sounding:** "Let's dive in", "Here's the thing", "It's worth noting", "Interestingly enough", "In today's market", "Let me break this down", "The bottom line is", "This is what X looks like", "That's the power of Y"

### Approved Alternatives

| Instead of... | Use... |
|---|---|
| HMA/Banker/UC | "our screening system" |
| Entry signal | "momentum confirmed", "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation patterns" |
| Stop hit | "systematic exit discipline" |
| Gatekeeper | "cleared all gates" |
| Conviction 8-10 | "Extremely Bullish" |
| TEAL/PASS | "GREEN signal" |
| Tier 1/2/3 | "high conviction" |

### Portfolio Display
- **15%+ gain:** Showcase with entry price and P&L%
- **Under 15% positive:** Include in tables, no spotlight
- **Negative:** Acknowledge honestly. State facts. Never say "loss."
- **Performance Reviews:** ALL positions with entry prices
- **Notes:** Spotlight 15%+ only. Red positions in PORTFOLIO_UPDATE/MARKET_SNAPSHOT only.

### HTML Specs (White Background)

**Editorial Theme** (all posts)
- Background: `#ffffff` | Max-width: `680px` | Padding: `40px 24px`
- Headings: `Georgia, serif` | `#1a1a1a` | h1: 28px, h2: 22px, h3: 18px
- Body: system sans-serif | 16px | line-height 1.7 | `#2d2d2d`
- Dividers: `1px solid #e8e4df`
- Price targets: Bear (`#fdf6f4`, `#dc2626` border), Base (`#f4f7fa`, `#2563eb`), Bull (`#f4faf5`, `#16a34a`)
- Tables: `#f8f7f5` header, `#fafaf8` alt rows, `#e8e4df` borders
- Callout: 3px left `#3d5a80`, bg `#f4f7fa`
- Positive: `#2e5e3e` | Negative: `#a04030`
- Stat cards: inline-block `#f8f7f5`, 28px bold number, 12px label
- Funnel: stepped bars, green→amber→red borders

**Teal accents** (Sector Watch): `#0d9488` borders, `#f0fdfa` highlights

**Note template:**
```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
[content]
<p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
</div>
```

### Visual Placeholders
- `[CHART: TICKER]` — TradingView chart screenshot
- `[SCAN_FUNNEL]` — Screening funnel (design for 680px screenshot)
- `[THEME_SCORES]` — Theme cards
- `[WINNERS_TABLE]` — Portfolio table (design for 680px screenshot)

---

## Companion Note Strategy (Summary)

Every post gets a companion note. The note is NOT a summary — it's a HOOK.

| Post Type | Hook Strategy | End With |
|---|---|---|
| 🟢 GREEN Signal | Ticker + price + funnel rejection rate | "Full signal analysis just published." |
| Position Update | P&L outcome (if winner) or discipline angle | "Full exit analysis just published." |
| Deep Dive | Most surprising research finding (one number) | "Full analysis with price targets just published." |
| Sector Watch | Strongest ETF flow or institutional data point | "Full sector analysis just published." |
| The Edge | Most counterintuitive stat | "Full analysis just published." |
| Investor Lessons | Most surprising principle + portfolio connection | "Full analysis just published." |
| Tools & Tech | What the tool found on our ticker | "Full walkthrough with setup guide just published." |
| The Weekly Screening | Portfolio's strongest number vs benchmark | "Full breakdown in this week's newsletter." |

### What Makes a Good Hook

BAD: "We just published our weekly deep dive on $ASTS."
GOOD: "$ASTS has $265M cash, zero debt, and a patent portfolio 47 deep. Our base case puts it at $38. It's trading at $22.80."

BAD: "New sector analysis on Defence."
GOOD: "$800M flowed into defence ETFs in February alone. Our three defence positions are up a combined 72%."

BAD: "This week's newsletter is out."
GOOD: "1,817 stocks screened. 3 survived. Portfolio at +34% vs SPY +12%. Full breakdown in today's newsletter."

BAD: "New article about stop losses."
GOOD: "Our stop loss on $VNET saved us $1,200 in 48 hours. Here's the math of systematic exits."

BAD: "We reviewed a free analysis tool."
GOOD: "I ran $LUNR through Finviz. It flagged institutional ownership jumped 16% in one quarter. Free."

The hook gives ONE number that creates curiosity. The post delivers the full story.

---

## Prompt Count Summary

| Day | Series | Prompts | Modes | Time |
|-----|--------|---------|-------|------|
| Saturday (analysis session) | The Weekly Screening | Prompt 11 | — | Built into session |
| Tuesday | Deep Dive | 3 | Research → Extended → Standard | ~15-20 min |
| Wednesday | Sector Watch | 2 | Research → Standard | ~10-15 min |
| Thursday | The Edge | 3 | Extended → Research → Standard | ~15-20 min |
| Friday | Investor Lessons | 3 | Extended → Research → Standard | ~15-20 min |
| Saturday | Tools & Tech | 2 | Research → Standard | ~10-15 min |
| Ad-hoc | Trade Alert (entry/exit) | 1 | Standard | ~5-10 min |

**Sunday batch total:** ~65-90 min for all 5 posts + 5 companion notes

---

## v7.0 Change Log

| Change | Rationale |
|---|---|
| **Mode annotations on every prompt** | Research mode for data gathering, Extended Thinking for analysis, Standard for writing. Using the right mode at each stage is the single biggest quality lever. |
| **Specific research instructions** | "Search SEC EDGAR for 10-Q revenue by segment" beats "search for financial data." Specificity produces tables; vagueness produces prose. |
| **Quality checks on every writing prompt** | "Does section 4 contain an actual HTML table?" catches thin output before it ships. |
| **Investor Lessons series (NEW)** | Friday post: case studies, legendary investors, investing principles. Mandatory portfolio connection. Fills the educational gap between The Edge (Thursday) and the weekend. |
| **Tools & Tech series (NEW)** | Saturday post: specific tools demonstrated on portfolio tickers. Positions Sterling Signals as a resource, not just a newsletter. Strong for SEO and evergreen traffic. |
| **5-post weekly calendar** | Tue-Sat all have posts + visuals. Monday and Sunday remain notes-only. Weekly output: 5 posts, 5 companion notes, 2 diagrams, 3 carousels, 19 notes, 35-49 tweets. |
| **Subcategory rotation** | Investor Lessons and Tools & Tech rotate through subcategories. Sunday planner checks last 4 weeks' manifests to prevent repetition. |
| **Portfolio connection requirement strengthened** | The Edge and Investor Lessons MUST name a specific ticker with entry price and P&L. No abstract lessons. |
| **All v6.2 changes preserved** | Tiered architecture, series names, companion notes, trade alerts, position update framing, anti-AI rules. |
