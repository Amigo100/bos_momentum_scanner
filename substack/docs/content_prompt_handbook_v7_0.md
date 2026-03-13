# Sterling Signals — Content Prompt Handbook v7.1

> **Multi-prompt sequential system for Opus 4.6**
> Each post uses 2-3 prompts in sequence within a single claude.ai chat.
> Every post produces a companion Substack Note for the Notes feed.
> Prompts specify which mode to use: Research, Extended Thinking, or Standard.
> Last updated: March 2026

---

## How to Use This Handbook

### What This Handbook Covers

This handbook produces **Sunday–Wednesday posts, a Thursday carousel, and ad-hoc trade alerts.**

**Saturday's newsletter** ("The Weekly Screening") is produced by **Prompt 11** in the Sterling Prompt Library during the Friday analysis session — NOT from this handbook. The newsletter previews the week ahead, hints at signals (without naming tickers), and updates the portfolio.

If no analysis session ran, use the **Performance Review Fallback** at the end.

### Sunday Workflow

The Sunday Cowork planner reads Friday's decisions.json, the portfolio, and scanner data. It plans the week and prints prompt kits. You then produce all heavy content in one claude.ai batch session.

1. Open the Cowork planner output (printed inline or emailed)
2. For each post (Sun trade alert, Tue Sector Watch, Wed Investor Lessons):
   open a **new** claude.ai chat
3. Attach the files listed in the kit (this handbook + banned_terms.py minimum)
4. Paste the portfolio context block first
5. Paste each prompt in sequence — **wait for the full response before pasting the next**
6. The final prompt produces both the article HTML AND a companion note
7. For Thursday's Tools & Tech carousel: open a separate chat with carousel-guide.docx + carousel-series-templates.md attached
8. Save all outputs to the repo paths listed in the kit, git push

### Choosing Your Mode

Each prompt specifies which mode produces the best results. Toggle these in claude.ai before pasting the prompt.

| Mode | Toggle | Best For | Why |
|------|--------|----------|-----|
| **Research** | Research button ON | Data gathering — financial filings, ETF flows, institutional data, tool reviews | Systematically searches 20+ sources, produces cited findings with links. Produces richer research than standard web search. |
| **Extended Thinking** | Default with Opus 4.6 | Analysis, valuation, synthesis, topic discovery | Deep reasoning with internal chain-of-thought. Best for multi-step calculations, probability weighting, connecting disparate data. |
| **Standard** | Default | Writing articles, companion notes, single-pass trade alerts | Focused output generation. No overhead from search or extended reasoning. |

**The pattern:** Research mode gathers data → Extended Thinking analyses it → Standard mode writes from it. This three-stage pipeline consistently produces the richest output.

### Content Types & Series Names

| Series | Day | Prompts | Modes | Format |
|--------|-----|---------|-------|--------|
| **The Weekly Screening** | Saturday | Prompt 11 (analysis session) | — | Long-form newsletter |
| **🟢 Trade Alert** | Sunday | 3 or 4 (Research → Analysis → Write) | Research → Extended → Standard | Long-form post |
| **Portfolio Spotlight** | Sunday (no-signal weeks) | 3 (Research → Analysis → Write) | Research → Extended → Standard | Long-form post |
| **Position Update** | Within Sunday post | — | — | Section within Trade Alert |
| **Sector Watch** | Tuesday | 2 (Research → Write) | Research → Standard | Long-form post |
| **Investor Lessons** | Wednesday | 3 (Discover → Research → Write) | Extended → Research → Standard | Long-form post |
| **Tools & Tech** | Thursday | 1 (Research → Write) | Research | Carousel (Note, not article) |

**Ad-hoc (any day, replaces scheduled content):**

| Series | Trigger | Prompts |
|--------|---------|---------|
| **🟢 GREEN Signal** (mid-week) | New entry outside analysis session | 1 (Standard) |
| **Position Update** (standalone) | Exit outside Sunday cycle | 1 (Standard) |

### Title Format

| Type | Title Pattern | Example |
|------|--------------|---------|
| Newsletter | "The Weekly Screening — Week [N]: [Forward-looking hook]" | "The Weekly Screening — Week 12: CPI Tuesday, Eyes on Defence" |
| Trade Alert (1 signal) | "🟢 Trade Alert: $TICKER at $PRICE — [Theme]" | "🟢 Trade Alert: $ASTS at $22.80 — Space & Defence" |
| Trade Alert (2 signals) | "🟢 Trade Alert: $TICK1 & $TICK2 — This Week's Entries" | "🟢 Trade Alert: $ASTS & $BAND — Two Signals, One Theme" |
| Portfolio Spotlight | "Portfolio Spotlight: $TICKER — [Hook from strongest finding]" | "Portfolio Spotlight: $TMDX — +99% in 8 Weeks" |
| Position Update (standalone) | "Position Update: $TICKER — [Outcome]" | "Position Update: $VNET — Systematic Exit" |
| Sector Watch | "Sector Watch: [Theme] ([Score]/10)" | "Sector Watch: Defence Technology (8.4/10)" |
| Investor Lessons | "Investor Lessons: [Specific, Surprising Topic]" | "Investor Lessons: Druckenmiller's Biggest Bet Was 100% of His Fund" |
| Tools & Tech | "Tools & Tech: [Tool] — [Hook]" | "Tools & Tech: Finviz — The Free Screener That Finds Our Signals" |

### Weekly Calendar

**Signal weeks (1-2 new GREEN signals from Friday's session):**

| Day | Content | Visual | Format |
|-----|---------|--------|--------|
| Saturday | **The Weekly Screening** (newsletter — hints at signal sector, doesn't name ticker) | — | Long-form post |
| Sunday | **🟢 Trade Alert:** Full deep dive on signal(s) + brief exit notes if closing positions | Animated diagram | Long-form post |
| Monday | Notes only (3) | Note graphic | — |
| Tuesday | **Sector Watch:** Theme related to a portfolio holding (NOT the signal's theme if possible) | Carousel | Long-form post |
| Wednesday | **Investor Lessons:** Case study, principle, or legendary investor (standalone) | — | Long-form post |
| Thursday | **Tools & Tech:** Tool demo carousel (posted as a Note, not an article) | Carousel | Note |
| Friday | Notes only (3) | Note graphic | — |

**No-signal weeks:**

| Day | Content |
|-----|---------|
| Saturday | **The Weekly Screening** (includes "Why We Passed" framing) |
| Sunday | **Portfolio Spotlight:** Deep dive on best-performing holding — "Is the thesis still intact?" |
| Tuesday | **Sector Watch:** Highest-rated theme |
| Wednesday | **Investor Lessons:** Standalone educational |
| Thursday | **Tools & Tech:** Carousel in Notes |

**Weekly output:** 4 long-form posts (Sat, Sun, Tue, Wed) + 1 carousel (Thu) + 19 notes + 35-49 tweets

Ad-hoc trade alerts (🟢 GREEN Signal / Position Update) can publish any day and REPLACE whatever was scheduled.

---

## 🟢 GREEN Signal — Mid-Week Trade Alert (1 Prompt)

**Use this ONLY for mid-week entries** — when a position is entered outside the normal Friday analysis → Sunday trade alert cycle (e.g., a stop-loss re-entry, an exceptional setup on Tuesday).

For signals from the Friday analysis session, use the **Sunday Trade Alert** section below — it provides a more comprehensive deep-dive format.

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

## 🟢 Sunday Trade Alert (3-4 Prompts) — Sunday

**The flagship post of the week.** Saturday's newsletter hinted at the signal's sector without naming the ticker. Sunday's trade alert delivers the full reveal: ticker, price, complete analysis, valuation, and price targets.

This is the GREEN Signal announcement AND the Deep Dive merged into one comprehensive article. Readers who saw Saturday's hint have been waiting for this.

**Three variants:**
- **1 signal:** 3-prompt sequential (Research → Analysis → Write)
- **2 signals:** 4-prompt sequential (Research A → Research B → Analysis both → Write combined)
- **0 signals (Portfolio Spotlight):** 3-prompt sequential on best-performing holding

### Variant A: Single Signal (3 Prompts)

#### Prompt 1 of 3 — Research

**MODE: Research mode ON**

```
You are researching $TICKER for a Trade Alert article. This is the signal
that Saturday's newsletter hinted at — readers are expecting the full reveal.
Produce structured financial data — NOT prose, NOT an article.

CONTEXT:
- Entry price: $[ENTRY] | Current: $[CURRENT]
- Theme: [THEME NAME] ([SCORE]/10)
- Saturday's newsletter said: "[exact hint text from newsletter]"

RESEARCH TASK 1 — FINANCIAL BASELINE

Search specifically for:

A) SEC EDGAR — most recent 10-Q or 10-K filing for $TICKER:
   - Revenue by segment for the last 8 quarters. TABLE with QoQ and YoY growth.
   - Gross margin, operating margin, net margin per quarter (8 quarters) — TABLE
   - Free cash flow: operating cash flow minus capex, trailing 4 quarters
   - Balance sheet: cash + equivalents, total debt, current ratio
   - Shares outstanding now vs 12 months ago. Dilution %.

B) Most recent earnings call or press release:
   - Revenue beat/miss vs consensus ($ and %)
   - Guidance raised, lowered, or maintained?
   - Key CEO/CFO quote about forward outlook (exact quote with source)
   - Segment-specific guidance or new product announcements

C) Institutional ownership:
   - Latest 13F filings mentioning $TICKER
   - Net institutional buying or selling ($ amount, last quarter)
   - 2-3 notable funds that entered or exited (name + position size)
   - Short interest % of float — current vs 3 months ago

D) Recent catalysts (last 30 days):
   - FDA decisions, regulatory rulings, contracts
   - Analyst upgrades/downgrades — firm, old PT, new PT
   - Insider buying/selling — name, title, shares, $ (Form 4)
   - Partnerships, acquisitions, product launches

RESEARCH TASK 2 — FORWARD REVENUE BUILD (next 12 months)

For EACH revenue segment:
- Known contracts/backlog with $ values and delivery dates
- Pipeline items with probability weights
- Pricing trends: ASP, ARPU, contract values — direction + evidence
- TAM and SAM with penetration rate
- Headwinds: competition, regulation, funding dependency

Build LOW / MID / HIGH per segment. Cite every assumption.

OUTPUT: Structured tables with citations. Flag gaps. Do NOT write yet.
```

#### Prompt 2 of 3 — Analysis

**MODE: Extended Thinking ON, Research mode OFF**

```
Using your research, build a complete financial analysis. Use extended
thinking — show working, not just conclusions.

ANALYSIS TASK 1 — MARGIN & EARNINGS PROJECTION

Bear/base/bull for next 12 months:

| Metric | Bear | Base | Bull |
|--------|------|------|------|
| Total revenue ($M) | | | |
| Revenue growth (YoY %) | | | |
| Gross margin (%) | | | |
| Operating margin (%) | | | |
| EPS ($) | | | |
| FCF/share ($) | | | |

One driving assumption per scenario:
- Bear: "[specific failure]"
- Base: "[specific continuation]"
- Bull: "[specific catalyst + date]"

ANALYSIS TASK 2 — VALUATION TRIANGULATION (4 methods, full working)

METHOD A — Historical Multiple Range: P/E and EV/EBITDA over 3 years. Apply to bear/base/bull earnings.
METHOD B — DCF: Your FCF projections. 10Y Treasury + 5% risk premium. Show calculation.
METHOD C — Peer-Relative: 4-6 named peers. Compare P/E, EV/Revenue, EV/EBITDA (table).
METHOD D — Catalyst-Adjusted: 3-5 binary events with probability % and $ impact each.

ANALYSIS TASK 3 — SYNTHESIS

Weight methods by company type (state which weighting and why).
Bear/base/bull targets with probability weights (NOT default 25/50/25).
Expected value. Risk/reward ratio.
Three assumptions most likely wrong — which direction and by how much.

OUTPUT: Tables with working. Do NOT write yet.
```

#### Prompt 3 of 3 — Article + Companion Note

**MODE: Standard**

```
Write the Trade Alert article and companion note using ALL research and
analysis from this conversation.

Saturday's newsletter hinted at this signal in the [THEME] space. This
article is the reveal — the first time readers see the ticker.

TITLE: "🟢 Trade Alert: $TICKER at $[PRICE] — [Theme Name]"

═══ ARTICLE (1,200-1,800 words) ═══

White-background Editorial theme (680px, inline CSS).

STRUCTURE:
1. THE REVEAL — "We're entering $TICKER at $[PRICE]." Decisive. What the
   company does in one sentence. Theme connection. This is the moment
   Saturday's readers have been waiting for.

2. WHY THIS COMPANY — What makes it unique. Structural advantage. 2-3
   paragraphs with specific data from your research.

3. WHAT TRIGGERED THE SIGNAL — Approved terms: structural pivot confirmation,
   momentum confirmed, institutional accumulation. What made this pass when
   99%+ didn't? Include [SCAN_FUNNEL] placeholder.

4. THE NUMBERS — Revenue trajectory, margins, balance sheet. HTML TABLE with
   quarterly data required — not just prose. Show the reader the trend.

5. 12-MONTH PRICE TARGETS — Three colour-coded cards:
   - Bear (red-tinted, #fdf6f4): price, probability %, driving assumption
   - Base (blue-tinted, #f4f7fa): price, probability %, driving assumption
   - Bull (green-tinted, #f4faf5): price, probability %, driving assumption
   - Below: Expected value + Risk/reward ratio

6. BEAR CASE — Three assumptions most likely wrong. Specific and honest.

7. KEY RISK — One metric, date, or event that invalidates.

8. OUR POSITION — Entry price, position size rationale, exit trigger.

9. WHAT WE'RE WATCHING — Next catalyst, next data point, what confirms.

[If also closing a position this week, add before footer:]
10. ALSO THIS WEEK: EXITING $TICKER2 — 3-4 sentences: what changed, P&L
    if profitable, discipline framing if not. Brief — this isn't the focus.

11. FOOTER — "Every signal, every entry, every exit — documented weekly:
    https://sterlingsignals.substack.com"

[CHART: TICKER] placeholder after section 3 or 4.

═══ QUALITY CHECK ═══
- Does section 4 have an HTML table with quarterly numbers?
- Do sections 5-6 use specific numbers from your analysis?
- Is the article 1,200-1,800 words?
- Does section 1 feel like a REVEAL, not a dry announcement?

═══ COMPANION NOTE (150-280 words) ═══

This is the moment: name the ticker for the first time in the Notes feed.

"$TICKER at $[PRICE]. GREEN signal confirmed."
Funnel stat: "1,817 screened. This was one of [N] that passed."
ONE surprising finding from your research (not the price targets).

⛔ ANTI-SPOILER: Max ONE price target (base case). Never bear/base/bull together.

End with: "Full analysis with price targets just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: The energy of "we've been waiting to tell you about this one." Decisive,
not tentative. This is the best post of the week — it should read like it.
```

### Variant B: Two Signals (4 Prompts)

#### Prompt 1a of 4 — Research Signal 1

**MODE: Research mode ON**

Same as Variant A Prompt 1, but for $TICKER1 only.

#### Prompt 1b of 4 — Research Signal 2

**MODE: Research mode ON**

Same research tasks, now for $TICKER2. State: "This is the second signal
from this week's screening. Research this independently — do not blend with
the previous ticker's analysis."

#### Prompt 2 of 4 — Analysis (Both Tickers)

**MODE: Extended Thinking ON, Research mode OFF**

```
Analyse BOTH tickers from your research. Build separate valuations for each.

For $TICKER1:
[Same Analysis Tasks 1-3 as Variant A]

For $TICKER2:
[Same Analysis Tasks 1-3 as Variant A]

COMPARISON:
- Which has better risk/reward?
- Which has nearer-term catalysts?
- Are they correlated (same theme) or diversifying?

OUTPUT: Separate tables for each. Do NOT write yet.
```

#### Prompt 3 of 4 — Combined Article + Companion Note

**MODE: Standard**

```
Write a combined Trade Alert covering both signals.

TITLE: "🟢 Trade Alert: $TICKER1 & $TICKER2 — This Week's Entries"

═══ ARTICLE (1,800-2,400 words) ═══

STRUCTURE:
1. THE REVEAL — "Two stocks cleared all gates this week. Here's the full
   analysis on both." Name both tickers and prices.

2-8. [SIGNAL 1: Full analysis using same structure as Variant A sections 2-8]

── DIVIDER ──

9-15. [SIGNAL 2: Full analysis — same structure, independent sections]

16. HEAD TO HEAD — Quick comparison table: ticker, price, risk/reward,
    nearest catalyst, theme overlap. Helps readers who can only buy one.

17. EXITS (if applicable) — Brief section on any positions closing.

18. FOOTER

═══ COMPANION NOTE (150-280 words) ═══

"Two signals this week. $TICKER1 at $[PRICE] and $TICKER2 at $[PRICE]."
ONE surprising finding from either research set.
"Full analysis with price targets on both just published."

Label: [ARTICLE HTML] and [COMPANION NOTE].
```

### Variant C: No Signals — Portfolio Spotlight (3 Prompts)

**Use when the Friday session produced no new GREEN signals.** The Sunday
post becomes a thesis refresh on the best-performing holding.

#### Prompt 1 of 3 — Research

**MODE: Research mode ON**

```
No new signals this week. We're refreshing the thesis on our best performer.

TICKER: $TICKER
Entry: $[ENTRY] | Current: $[CURRENT] | P&L: +[X]% in [N] days
Theme: [THEME NAME]

Research question: "Is the thesis that drove our entry still intact? What's
changed since we entered, and does the risk/reward still favour holding?"

[Same Research Tasks 1-2 as Variant A, but framed as thesis refresh:
- What's changed since entry? (new contracts, earnings, regulatory)
- Has institutional ownership increased or decreased since our entry?
- Any new risks that didn't exist at entry?
- Forward revenue build: has the trajectory improved or weakened?]

OUTPUT: Structured tables with citations. Flag what changed vs entry thesis.
```

#### Prompt 2 of 3 — Analysis

**MODE: Extended Thinking ON**

Same analysis structure as Variant A Prompt 2, but with additional section:

```
[Same Analysis Tasks 1-3]

ANALYSIS TASK 4 — THESIS REVIEW

Compare current state to entry thesis:
- What we expected at entry vs what actually happened
- Has conviction increased, decreased, or held?
- Updated exit trigger (has it changed?)
- Should we add to this position, hold, or begin trimming?

Be honest. If the thesis is weakening, say so.
```

#### Prompt 3 of 3 — Article + Companion Note

**MODE: Standard**

```
Write the Portfolio Spotlight article and companion note.

TITLE: "Portfolio Spotlight: $TICKER — [Hook from strongest finding]"
Example: "Portfolio Spotlight: $TMDX — +99% in 8 Weeks. Are We Still Holding?"

═══ ARTICLE (1,000-1,500 words) ═══

STRUCTURE:
1. THE HOOK — "$TICKER at $[CURRENT], up [X]% from our $[ENTRY] entry
   [N] days ago." Why is this worth a deep look right now?

2. THE ORIGINAL THESIS — What we saw at entry. Why we entered.

3. WHAT'S CHANGED — New data since entry. Earnings, contracts, institutional
   moves. Be specific — table of what we expected vs what happened.

4. THE NUMBERS — Updated financials. HTML table with quarterly data.

5. UPDATED PRICE TARGETS — Refreshed bear/base/bull with new data.

6. BEAR CASE — What could go wrong from HERE (not from entry).

7. OUR DECISION — Hold, add, or trim? Exit trigger update.

8. FOOTER

═══ COMPANION NOTE ═══

"$TICKER: +[X]% in [N] days. Is the thesis still intact?"
ONE updated finding. Don't reveal the hold/add/trim decision — make them read.

Label: [ARTICLE HTML] and [COMPANION NOTE].
```

---

## Sector Watch (2 Prompts) — Tuesday

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

## Investor Lessons (3 Prompts) — Wednesday

**Series identity:** Case studies, legendary investors, investing principles,
market mechanics, and behavioural finance. These posts stand on their own —
a portfolio connection is welcome when natural but NEVER forced.

**Subcategory rotation** (check last 4 Wednesdays' manifests, pick least-recently-used):

| Subcategory | Examples |
|---|---|
| Case Study | Enron, GameStop, Nvidia's pivot, LTCM, Tesla short squeeze |
| Legendary Investor | Buffett, Druckenmiller, Lynch, Soros, Dalio, Cathie Wood |
| Investing Principle | Stop losses, position sizing, risk/reward, momentum vs value |
| Market Mechanics | Short squeezes, 13F analysis, options flow, index rebalancing |
| Behavioural Finance | Loss aversion, anchoring, FOMO, recency bias, disposition effect |

### Prompt 1 of 3 — Discover Topic

**MODE: Extended Thinking**

```
Today is an Investor Lessons post. Subcategory: [SELECTED BY ROTATION].

Generate 3 topic candidates. For EACH:
- The topic stated as a specific, surprising claim (not generic)
- The hook stat — one number that would make someone stop scrolling
- What makes this timely? (Why this week — a market event, a position
  milestone, something in the news?)
- Shareability: would someone repost this? What's the quotable insight?

If any topic has a natural portfolio connection, note it — but do NOT
force one. "Druckenmiller concentrated into one trade" is a great topic
whether or not we can connect it to our portfolio.

Recommend your top choice. Explain why it beats the alternatives.
```

### Prompt 2 of 3 — Research

**MODE: Research mode ON**

```
Research [SELECTED TOPIC] thoroughly.

SEARCH FOR:

A) The original source:
   - The shareholder letter, interview, academic paper, SEC filing, book chapter
   - Specific dates, returns, drawdowns, position sizes, dollar amounts
   - Direct quotes from primary sources

B) Specific numbers that make the story compelling:
   - Returns, timeframes, drawdowns, AUM, position sizes
   - The more specific, the more credible

C) Counter-evidence:
   - When did this principle fail? Name a specific case.
   - Is this survivorship bias?
   - What's the base rate of success?

D) One stat that contradicts common wisdom:
   - The counterintuitive finding that hooks the article

E) OPTIONAL — Portfolio connection (only if natural):
   - If one of our positions genuinely illustrates this principle,
     note the ticker, entry, P&L, and how it connects
   - If nothing connects naturally, skip this. Do NOT force it.

OUTPUT: Structured research with citations. No article yet.
```

### Prompt 3 of 3 — Write

**MODE: Standard**

```
Write the article and companion note.

TITLE: "Investor Lessons: [Specific, Surprising Topic]"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme.

STRUCTURE:
1. THE HOOK — Most surprising number or claim. One sentence.
2. THE STORY — Narrative, not bullet points. Tell it like a story.
3. THE EVIDENCE — Studies, data, specific numbers with citations.
   Include at least one table or data comparison.
4. [OPTIONAL] IN OUR PORTFOLIO — Only if a natural connection exists
   from your research. Name the ticker, entry, P&L. If nothing connects
   naturally, SKIP this section entirely. A forced connection is worse
   than no connection.
5. THE EXCEPTION — When does this fail? Specific counter-example.
6. THE TAKEAWAY — One concrete thing the reader can do THIS WEEK.
7. FOOTER — "We study the best to build a better system: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 2 tell a STORY (narrative) not just list facts?
- Does section 3 cite at least one source with a specific number?
- If section 4 exists, is the portfolio connection genuine or forced?
  If forced, DELETE it.

═══ COMPANION NOTE (150-280 words) ═══

Lead with the hook stat. Create curiosity.

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Enthusiasm backed by evidence. Not professorial. Not clickbait.
```

---

## Tools & Tech (1 Prompt) — Thursday Carousel

**Series identity:** A carousel posted as a Substack Note (NOT a long-form
article). Shows a specific tool, demonstrated on a real ticker.

**This is lighter content by design.** Thursday is sandwiched between
Wednesday's Investor Lessons post and Friday's notes — a carousel provides
visual variety without article fatigue.

**Subcategory rotation** (check last 4 Thursdays' manifests):

| Subcategory | Example Tools |
|---|---|
| Screeners & Scanners | Finviz, TradingView screener, EDGAR full-text |
| Charting Platforms | TradingView setup, indicator configuration |
| Data & Research | Koyfin, Simply Wall St, Macrotrends, FRED, Quiver Quant |
| Portfolio Management | Position sizing calculators, correlation matrices |
| AI & Automation | Claude for 10-K analysis, Perplexity for earnings |
| Free vs Paid | "Free tools that replace $500/year subscriptions" |

### Prompt — Research + Carousel Data

**MODE: Research mode ON**

```
Research [TOOL NAME] for a Tools & Tech carousel. Demo on $TICKER.

SEARCH FOR:
- Official site, pricing, free tier limitations
- What problem it solves, who it's for
- Specific workflow on $TICKER: what screens, what data, what insights
- 2-3 alternatives and how this compares
- Limitations and gotchas

Then generate carousel data JSON for a 5-slide INVESTOR TOOLKIT carousel:

Slide 1 (DARK): Tool name + the problem it solves
  Hook stat: "Bloomberg costs $25K/year. This does 80% of the job for free."

Slide 2 (LIGHT): What it does in plain English. 2-3 short paragraphs.

Slide 3 (LIGHT): 4 stat cards showing what the tool found on $TICKER.
  Each card: number + label + source. Real data from your research.

Slide 4 (LIGHT): Two-column — "FREE TIER" vs "PAID ($X/mo)" or comparison
  with 2 alternatives.

Slide 5 (DARK): 3-4 numbered setup steps. URL included. Sterling Signals
  verdict: "We use this for [specific purpose]."

Output the JSON following the schema in carousel-data-schema.json.
Also output a brief companion note (100-150 words) for posting alongside
the carousel in Substack Notes.
```

**Files to attach:** carousel-guide.docx + carousel-series-templates.md + banned_terms.py

**After generation:** Run `node substack/tools/carousel-generator.js [json_file]`

**Save to:** `substack/output/current/carousels/carousel_tools_{YYYYMMDD}.pptx`

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
| Saturday | The Weekly Screening | Prompt 11 (analysis session) | — | Built into session |
| Sunday (signals) | 🟢 Trade Alert (1 signal) | 3 | Research → Extended → Standard | ~20 min |
| Sunday (signals) | 🟢 Trade Alert (2 signals) | 4 | Research × 2 → Extended → Standard | ~30 min |
| Sunday (no signals) | Portfolio Spotlight | 3 | Research → Extended → Standard | ~20 min |
| Tuesday | Sector Watch | 2 | Research → Standard | ~12 min |
| Wednesday | Investor Lessons | 3 | Extended → Research → Standard | ~18 min |
| Thursday | Tools & Tech (carousel) | 1 | Research | ~8 min |
| Ad-hoc | GREEN Signal (mid-week) | 1 | Standard | ~5 min |
| Ad-hoc | Position Update (standalone) | 1 | Standard | ~5 min |

**Sunday batch total:** ~60-90 min for Sunday post + Tue + Wed + Thu carousel + all companion notes + visual assets

---

## v7.1 Change Log

| Change | Rationale |
|---|---|
| **Saturday newsletter restructured** | "Week Ahead" format: leads with catalyst calendar, hints at signals without naming tickers, creates anticipation for Sunday. Prompt 11 rewritten in Sterling Prompt Library. |
| **Sunday Trade Alert (NEW)** | Merges GREEN Signal + Deep Dive into one comprehensive article. 3-4 prompt sequence. Supports 1 signal, 2 signals, or no-signal (Portfolio Spotlight) variants. |
| **Position exits folded into Sunday** | No separate Position Update posts during normal weeks. Exits get a brief section within the Sunday Trade Alert. Standalone Position Update kept for ad-hoc mid-week exits only. |
| **Investor Lessons: portfolio connection optional** | Forced connections produced strained content. Now: if natural, include it. If not, skip. Quality over formula. |
| **Tools & Tech: carousel only** | Tool reviews are visual by nature. A 5-slide carousel is a better format than an 800-word article. Reduces weekly post count, increases variety. Posted as a Note, not an article. |
| **Weekly calendar: 4 posts + 1 carousel** | Sat newsletter, Sun trade alert, Tue Sector Watch, Wed Investor Lessons, Thu carousel. Fewer posts, more depth, less repetition. |
| **Anti-concentration rules** | Max 2 posts per ticker. Sector Watch theme must differ from Sunday's signal theme. Tools demo on a different ticker. |
| **Tuesday moved to Sector Watch, Wednesday to Investor Lessons** | Sector Watch benefits from fresh Monday market data. Investor Lessons midweek provides educational variety. |
| **The Edge removed** | Absorbed into Investor Lessons. Five educational formats (Case Study, Legendary Investor, Investing Principle, Market Mechanics, Behavioural Finance) provide more variety than Edge + Lessons as separate series. |

### v7.0 Changes (preserved)

| Change | Rationale |
|---|---|
| **Mode annotations on every prompt** | Research mode for data gathering, Extended Thinking for analysis, Standard for writing. Using the right mode at each stage is the single biggest quality lever. |
| **Specific research instructions** | "Search SEC EDGAR for 10-Q revenue by segment" beats "search for financial data." Specificity produces tables; vagueness produces prose. |
| **Quality checks on every writing prompt** | "Does section 4 contain an actual HTML table?" catches thin output before it ships. |
| **5-post weekly calendar** | All v6.2 changes preserved: tiered architecture, series names, companion notes, trade alerts, position update framing, anti-AI rules. |
