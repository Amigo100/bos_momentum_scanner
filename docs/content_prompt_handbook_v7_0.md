# Sterling Signals: Content Prompt Handbook v8.0

> **Multi-prompt sequential system for Opus 4.6.**
> Each post uses 2–4 prompts in sequence within a single Claude.ai chat.
> Prompts specify which mode to use: Research, Extended Thinking, or Standard.
>
> **This handbook produces article drafts and visual briefs.** Final HTML
> articles and JSX visual assets are produced by the companion documents:
> - `ARTICLE_SYSTEM_v2.md` — long-form HTML article production
> - `STERLING_VISUAL_SYSTEM_v2.md` — carousel slides and Substack Notes
> - `voice_rules.md` — voice, tone, banned terms (canonical source)
>
> Saturday's "The Weekly Screening" comes from Prompt 11 in the analysis
> session. It is NOT in this handbook.

---

## How to Use This Handbook

### Workflow

1. Cowork's Sunday Mode A produces a **context package** for each post.
   This contains all data from the analysis session: decisions.json
   entries, signal history, financial metrics, rejection narratives,
   force context.
2. Open a **new** Claude.ai chat for each post.
3. Attach `voice_rules.md`.
4. Paste the context package first.
5. Paste each prompt in sequence. **Wait for the full response before
   pasting the next prompt.**
6. The final prompt produces an article draft in structured markdown
   plus a visual brief. Feed these into the companion production
   documents for final HTML/JSX output.

### Choosing Your Mode

| Mode | Toggle | Best For |
|------|--------|----------|
| **Research** | Research button ON | Data gathering: financials, 13F filings, ETF flows, news, insider transactions. Searches 20+ sources systematically with citations. |
| **Extended Thinking** | Default with Opus 4.6 | Analysis, valuation, synthesis, long-form writing. Deep reasoning with internal chain-of-thought. |

**The pattern:** Research gathers and verifies data. Extended Thinking
analyses it, builds the narrative, and writes the article.

### Content Types

| Post | Day | Trigger | Prompts | Modes |
|------|-----|---------|---------|-------|
| **Tuesday: New Signal Deep Dive** | Tuesday | Scanner produced a buy signal | 4 | Research × 2, Extended × 2 |
| **Tuesday: Sector / Force / Watchlist** | Tuesday | No new signal or material development | 3 | Research, Extended × 2 |
| **Thursday: Education** | Thursday | Best available topic from context package | 3 | Research, Extended × 2 |
| **Portfolio Review** | Ad-hoc | No analysis session, or portfolio warrants review | 3 | Research × 2, Extended |
| **Position Exit** | Any day | Stop triggered or thesis broken | 1–2 | Research (optional), Extended |
| **Visual Carousel + Note** | Any day | Context package flags a carousel topic | 2 | Research, Extended |

### Title Patterns

| Type | Pattern | Example |
|------|---------|---------|
| New signal deep dive | "$TICKER: [Thesis Hook with Number]" | "$VYGR: Gene Therapy Platforms, Pharma Deal Flow at $800M, and a 500% Institutional Bet" |
| Sector / force | "[Force Name]: [Specific Hook]" | "The Nuclear Fuel Supply Chain: $188 SWU Prices, a Russian Ban, and Where $ASPI Fits" |
| Watchlist | "On Our Radar: [N] Stocks the System is Watching" | "On Our Radar: Three Stocks That Almost Cleared the Gate" |
| Education | "[Surprising Claim or Number]" | "Past Earnings Growth Does Not Predict Future Multibagger Returns" |
| Portfolio review | "Portfolio Review: [Hook with Number]" | "Portfolio Review: 7 Positions, +18% Alpha, and the Force That Carried Us" |
| Position exit (profitable) | "$TICKER: +[Y]% in [Z] Weeks" | "$AMPX: +56% in 10 Days" |
| Position exit (not profitable) | "$TICKER: Systematic Exit, Thesis Changed" | "$SKBL: Systematic Exit, Thesis Changed" |

---

## 1. Tuesday: New Signal Deep Dive (4 Prompts)

The scanner produced a new buy signal. Saturday's briefing announced
the entry. This article delivers the complete thesis.

### Prompt 1 of 4: Research — Financials and Fundamentals

**MODE: Research mode ON**

```
You are researching $[TICKER] for a deep dive article on Sterling
Signals. This stock was entered at $[PRICE] after clearing our
five-stage screening process.

CONTEXT PACKAGE (from Cowork — pasted above this prompt):
[The context package contains the full decisions.json entry, signal
history trail, gate data, and bear case from our analysis session.
Use this as your foundation, then SUPPLEMENT with fresh research.]

This is the FIRST of two research prompts. This one focuses on
financials and fundamentals only.

RESEARCH TASK 1: FINANCIAL BASELINE

Search SEC EDGAR for the most recent 10-Q or 10-K for $[TICKER]:
A) Revenue by segment for the last 8 quarters.
B) Gross margin, operating margin, net margin per quarter (8 quarters).
C) Free cash flow: operating cash flow minus capex, trailing 4 quarters.
D) Balance sheet: cash and equivalents, total debt, current ratio.
E) Shares outstanding now vs 12 months ago. Calculate dilution %.
F) Any convertible notes, warrants, or upcoming maturities with dates
   and dollar amounts.

RESEARCH TASK 2: RECENT DEVELOPMENTS

Search for the most recent earnings call or press release:
A) Revenue beat/miss vs consensus (dollar amount and percentage).
B) Guidance: raised, lowered, maintained. Specific numbers.
C) Key management quote about forward outlook (exact quote with source).
D) Segment-specific guidance or new product announcements.

RESEARCH TASK 3: COMPETITIVE LANDSCAPE

A) Name the 3–5 closest competitors or peer companies.
B) For each peer: market cap, revenue, EV/Revenue or EV/EBITDA, growth
   rate.
C) What is $[TICKER]'s specific competitive advantage? Search for moat
   evidence: patents, switching costs, network effects, regulatory
   barriers, cost advantages.
D) What is the biggest competitive threat and from whom?

OUTPUT FORMAT:
Present each task as a headed section with data in markdown tables.
Include source URLs for every data point.

For any data you cannot verify from public sources, mark it:
**[UNVERIFIED]** and note the data gap. Do not fill gaps with estimates.

Flag any findings that CONTRADICT the context package thesis in a
separate "CONTRADICTIONS" section at the end.
```

### Prompt 2 of 4: Research — Institutional Activity and Catalysts

**MODE: Research mode ON**

```
Continue researching $[TICKER]. This is the SECOND research prompt,
focusing on ownership, market positioning, and the catalyst calendar.

RESEARCH TASK 4: INSTITUTIONAL AND INSIDER ACTIVITY

A) Latest 13F filings mentioning $[TICKER]:
   - Net institutional buying or selling (dollar amount, last quarter)
   - 2–3 notable funds that entered or exited (fund name, position size,
     % change)
B) Short interest: current % of float vs 3 months ago.
C) Insider transactions (Form 4): names, titles, shares, dollar amounts,
   dates. Flag any patterns (cluster buying/selling, 10b5-1 context).

RESEARCH TASK 5: CATALYST CALENDAR

Build a timeline of specific upcoming events:
A) Next earnings date and consensus expectations.
B) Regulatory decisions (FDA, DOE, DOD, FCC) with specific dates.
C) Contract awards, partnership milestones, product launches.
D) Industry events, conferences, or policy decisions.
E) Any known lock-up expirations or secondary offering windows.

RESEARCH TASK 6: RECENT PRICE ACTION CONTEXT

A) 52-week high/low and current position within that range.
B) Average daily volume vs recent volume (any unusual spikes).
C) Any recent analyst coverage initiations or target changes
   (firm name, old/new target, date).

OUTPUT FORMAT:
Markdown tables with source URLs. **[UNVERIFIED]** for any gaps.
Add any new contradictions to the CONTRADICTIONS section.
```

### Prompt 3 of 4: Analysis

**MODE: Extended Thinking ON, Research mode OFF**

```
Using all research from this conversation and the context package data,
build a complete financial analysis. Use extended thinking to show your
working at every step.

ANALYSIS TASK 1: MARGIN AND EARNINGS PROJECTION

Build bear/base/bull scenarios for the next 12 months:

| Metric | Bear | Base | Bull |
|--------|------|------|------|
| Total revenue ($M) | | | |
| Revenue growth YoY % | | | |
| Gross margin % | | | |
| Operating margin % | | | |
| EPS ($) | | | |
| FCF/share ($) | | | |

For each scenario, state the ONE driving assumption:
- Bear: "[specific failure mode with trigger]"
- Base: "[continuation of current trajectory]"
- Bull: "[specific catalyst + date]"

Use segment-level build-up, not top-down guesses. Show the maths for
each segment.

ANALYSIS TASK 2: VALUATION (select methods by company type)

Apply the methods that are APPROPRIATE for this company. Do not force
methods that produce garbage on this company type.

ALWAYS USE:
- Method A: Peer-Relative Valuation — apply median peer multiples
  (P/E, EV/Revenue, EV/EBITDA) to projected financials. Table required.
- Method B: Catalyst-Adjusted — identify 3–5 binary events from the
  catalyst calendar. For each: probability % and dollar impact on stock
  price. Present as a probability-weighted expected value.

USE IF PROFITABLE OR NEAR-PROFITABLE:
- Method C: Historical Multiple Range — the stock's own P/E and
  EV/EBITDA over the last 3 years. Apply to bear/base/bull earnings.
- Method D: Discounted Cash Flow — FCF projections, 5-year explicit
  period + terminal. Discount rate: 10Y Treasury + 5% equity risk
  premium. Sensitivity table on discount rate and terminal growth.

SKIP IF PRE-REVENUE OR PRE-PROFIT:
- Skip DCF and Historical Multiples entirely. State: "Not applicable:
  [reason]." Weight Peer-Relative and Catalyst-Adjusted more heavily.
  Consider adding a TAM-based scenario analysis instead.

ANALYSIS TASK 3: SYNTHESIS

Weight the methods you used. State which weighting and why.

Produce bear/base/bull 12-month price targets with probability weights.
Do NOT default to 25/50/25. Assign probabilities based on the specific
assumptions.

Calculate: expected value, risk/reward ratio from entry price, and the
three assumptions most likely to be wrong (and in which direction).

Cross-check your targets against the context package targets. If they
diverge by more than 15%, explain why.

OUTPUT: Tables with full working. Do NOT write the article yet.
```

### Prompt 4 of 4: Write the Article Draft

**MODE: Extended Thinking ON**

```
Write the complete deep dive article using ALL research and analysis
from this conversation. Use extended thinking to plan the narrative arc
before writing.

Read voice_rules.md. These rules are non-negotiable:
- No em dashes anywhere (use colons, periods, semicolons)
- No AI/LLM references
- No technical indicator names
- Structural forces, not micro themes
- Specific numbers for every claim
- Vary sentence length deliberately

TITLE: "$[TICKER]: [Thesis hook with at least one specific number]"

Propose three alternative titles. Explain which is strongest and why.
Use the strongest as the article title.

TARGET: 2,500–3,500 words.

ARTICLE STRUCTURE:

PREVIEW LINE: 1–2 sentences for the email/feed preview. Must contain a
number that creates curiosity.

TABLE OF CONTENTS: linked section list.

1. THE THESIS IN ONE SENTENCE
   A single sentence capturing the entire investment thesis. Quotable,
   specific, memorable.

2. WHAT THIS COMPANY DOES (200–300 words)
   Plain-language business model explanation. Assume the reader has never
   heard of this company. No jargon without immediate explanation.

3. WHY NOW (300–400 words)
   What changed to create this opportunity. The structural force. The
   specific trigger. How the macro environment creates tailwinds. Make
   the reader feel the timing without resorting to hype.

4. THE NUMBERS (400–500 words)
   Revenue trajectory with quarterly data (minimum 4 quarters). Margin
   analysis showing the trend. Balance sheet assessment. Peer comparison
   (3–5 peers with market cap, revenue, growth, multiples). Let data
   tell the story; prose connects the dots.

5. WHAT WE THINK IT IS WORTH (300–400 words)
   Three price target scenarios (Bear/Base/Bull) with:
   - Target price
   - Probability weight (not 25/50/25 unless justified)
   - Driving assumption (one sentence)
   - Valuation method used
   Expected value calculation and risk/reward ratio from entry price.

6. THE BEAR CASE (200–300 words)
   Write this as if you were SHORT the stock. Name specific risks. What
   data point kills the thesis? What does the competition look like?
   What is the worst realistic 12-month outcome? This section builds
   trust with sophisticated readers.

7. HOW WE ARE PLAYING IT (150–200 words)
   Entry price. Position tier and sizing rationale. Structural force
   mapping. Specific exit criteria: price level, fundamental trigger,
   time-based review. What confirms vs disconfirms the thesis.

8. WHAT HAPPENS NEXT (100–150 words)
   Next catalyst with a specific date. What we are watching. What the
   reader should watch. Pull the reader forward to the next update.

FOOTER:
"Every screening result. Every entry. Every exit.
sterlingsignals.substack.com"

"Not financial advice. Informational and educational content only.
Past performance does not guarantee future results."

---

VISUAL BRIEF (include at the end, after the article text):

List every visual element this article needs for the HTML production
step. For each, specify:
- Component type (from ARTICLE_SYSTEM_v2: stat-grid, pull-stat,
  thesis-box, pipeline-diagram, catalyst-map, data-table, peer-bars,
  price-target-cards, ev-summary, risk-reward-bar, callout-box)
- Position (after which section or paragraph)
- Data to display (exact numbers extracted from your research/analysis)
- Any notes on adaptation (e.g., "pre-revenue: use cash burn bridge
  instead of standard waterfall")

Also state whether this article warrants a visual carousel
(STERLING_VISUAL_SYSTEM_v2) and if so, note any slide adaptations
by company type.

---

BEFORE YOU OUTPUT, verify every item:
□ Preview line contains a specific number
□ Table of contents present
□ Section 4 specifies at least TWO data tables (quarterly + peer comp)
□ Section 5 has three distinct price targets with non-default weights
□ Section 6 reads like it was written by a sceptic, not a bull
□ Word count is 2,500–3,500
□ ZERO em dashes in the entire output
□ ZERO technical indicator names (HMA, MACD, RSI, Banker, UC, MCDX)
□ ZERO AI/LLM references
□ Section 8 names a specific date for the next catalyst
□ Numbers from context package match numbers in the article
□ Visual brief is complete with component types and data
□ Three alternative titles are proposed with a recommendation
```

---

## 2. Tuesday: Sector / Force / Watchlist (3 Prompts)

No new signal and no material development. Topic determined by Cowork's
priority logic: subscriber request, force deep dive, or watchlist
analysis.

### Prompt 1 of 3: Research

**MODE: Research mode ON**

```
You are researching [TOPIC] for a deep dive on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains portfolio positions in this force/sector, watchlisted stocks,
force context from Prompt 2, signal history for relevant tickers.]

RESEARCH TASK 1: STRUCTURAL FORCE ASSESSMENT

Search for the current state of [FORCE NAME]:
A) Capital flows: relevant ETF inflows/outflows (name 3–5 ETFs, dollar
   amounts, last 3 months).
B) Government policy: bills, budgets, executive orders, regulatory
   decisions with dollar amounts and timelines.
C) Industry data: market size, growth rate, projections from named
   sources (IEA, Gartner, McKinsey, government agencies).
D) Recent institutional positioning: 13F trends across the sector.

RESEARCH TASK 2: COMPANY-LEVEL DATA

For EACH company discussed (portfolio positions + watchlisted stocks):
A) Current price, market cap, EV.
B) Most recent quarterly revenue, growth rate, margin.
C) Key competitive differentiator in one sentence.
D) Next catalyst with date.
E) If watchlisted: what price level or event would trigger entry.

RESEARCH TASK 3: RISKS AND COUNTER-THESIS

A) What would reverse the capital flows into this force?
B) Specific policy or regulatory risk.
C) Valuation concern: is the sector expensive relative to history?
D) Crowding: is the trade becoming consensus?

OUTPUT: Markdown tables with source URLs. **[UNVERIFIED]** for gaps.
```

### Prompt 2 of 3: Hook and Narrative Development

**MODE: Extended Thinking ON**

```
Before writing the full article, develop the hook and narrative angle.

Using your research and the context package, answer:

1. What is the single most surprising or counterintuitive finding from
   the research? This becomes the opening line.

2. What is the central tension? Every good piece has a tension:
   opportunity vs risk, consensus vs reality, promise vs execution.
   State it in one sentence.

3. Propose FIVE title options. For each, state:
   - The title
   - What makes it click-worthy
   - What reader it targets (existing subscriber vs new discovery)

4. What is the narrative arc? The reader should go from "I didn't know
   this" to "now I see the opportunity" to "here are the specific plays"
   to "here is what could go wrong."

5. What is the key insight that should go near the end to reward
   readers who finish?

OUTPUT: Structured outline with the recommended title, opening hook,
narrative arc, and section-by-section plan with word count targets.
Do NOT write the article yet.
```

### Prompt 3 of 3: Write the Analysis

**MODE: Extended Thinking ON**

```
Write the analysis using all research, the context package, and the
narrative plan from the previous prompt.

Read voice_rules.md. All constraints apply.

Use your recommended title. Include the other four alternatives for
reference.

TARGET: 2,000–3,000 words.

STRUCTURE:

PREVIEW LINE.
TABLE OF CONTENTS.

1. THE STRUCTURAL FORCE (200–300 words)
   The macro thesis. Why this force exists and why capital is flowing.
   Key data points. What changed recently. Make a reader who has never
   heard of this force understand why it matters.

2. THE LANDSCAPE (500–600 words)
   Key companies mapped across the force. Competitive dynamics. Where
   our holdings fit. For watchlisted stocks: what each offers and what
   prevents entry today. Include a markdown table: ticker, market cap,
   revenue, growth, multiple, our status (held/watchlisted/rejected).

3. THE DATA (300–400 words)
   Industry data, ETF flows, earnings trends, regulatory timeline.
   Tables where they clarify. Specific numbers from research that either
   support or challenge the thesis.

4. HOW WE ARE POSITIONED (200–300 words)
   What we hold and why. Current P&L on each position. What we do not
   hold and why. Forward catalysts with dates.

FOOTER.

VISUAL BRIEF: List components for HTML production. Include at minimum:
stat-grid (force-level metrics), landscape comparison table, ETF flow
data table, callout-box for key risk.

Also note whether a visual carousel would add value for this topic and
suggest slide adaptations if so.

BEFORE YOU OUTPUT, verify:
□ Five title alternatives proposed with recommendation
□ Opens with the hook from the narrative plan, not preamble
□ At least one data table with real numbers
□ Bear case / counter-thesis is specific and fair
□ ZERO em dashes, indicator names, or AI references
□ 2,000–3,000 words
□ Visual brief is complete
```

---

## 3. Thursday: Education (3 Prompts)

The growth engine. These posts attract new subscribers through
Substack's algorithm. They must have standalone value: a reader who
does not follow the portfolio should still find the post worth their
time.

There is no fixed rotation. Each week, choose the strongest topic from
the context package. Topics typically fall into one of these angles,
but any combination or hybrid is fine:

- **Methodology:** How the screening system works, position sizing,
  the structural forces framework. NEVER reveal specific indicator names.
- **Research finding:** Academic or practitioner research on multibagger
  characteristics, momentum, factor investing. Counterintuitive findings.
- **Investor lesson:** A real example from our screening process. A
  stock we rejected and why. A capital structure trap. A turnaround
  that failed. The lesson taught through a specific story.

### Prompt 1 of 3: Research

**MODE: Research mode ON** (or Extended Thinking if the topic draws
primarily from the context package rather than external sources)

```
You are researching a topic for an education post on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains the topic, relevant data from the system, and any specific
stocks or examples to reference.]

TOPIC: [topic from context package]

Determine which angle this topic falls into and research accordingly:

IF METHODOLOGY OR SYSTEM TOPIC:
- Pull exact data from the context package: tickers scanned, rejection
  rates, tier breakdown, specific stocks rejected and why.
- Search for any external data that supports the system's approach:
  academic research on systematic vs discretionary investing, momentum
  factor performance, screening effectiveness.
- Identify the most counterintuitive claim the data supports.

IF RESEARCH FINDING:
A) Find the primary academic or practitioner source:
   - Author, institution, publication date, methodology
   - Key finding stated as a specific number or statistic
   - Sample size and time period studied
B) Find 2–3 supporting or contradicting sources.
C) Find the counterintuitive angle: what does this finding say that
   contradicts conventional wisdom?
D) Find 2–3 real company examples that illustrate the finding with
   specific returns, dates, and outcomes.

IF INVESTOR LESSON:
A) From the context package, identify the specific stock and rejection
   reason. Search for:
   - Recent financials: revenue trend, margins, cash flow.
   - The specific issue (dilution, competitive deterioration, capital
     structure, turnaround failure). Verify with public data.
B) What happened AFTER rejection? Did the risk materialise?
C) The broader pattern: is this a common trap? How often do stocks
   with this profile fail?

OUTPUT: Structured research with source URLs. **[UNVERIFIED]** for
gaps. Highlight the single most counterintuitive finding.
```

### Prompt 2 of 3: Hook and Title Testing

**MODE: Extended Thinking ON**

```
Using the research, develop the hook and narrative angle.

1. Propose FIVE title options. For each:
   - The title
   - Why it stops a scroller
   - Who it targets: existing subscriber vs new reader discovering
     Sterling Signals through Substack's algorithm

2. Write THREE different opening paragraphs (2–3 sentences each).
   Each should use a different hook strategy:
   A) The surprising statistic: lead with the most counterintuitive
      number from the data.
   B) The common mistake: open with what most investors get wrong about
      this topic.
   C) The specific story: open with a specific stock or example that
      illustrates the concept.

3. What is the narrative arc? The reader should go from "I didn't know
   this" to "now I understand" to "I can apply this" to "I want to
   keep reading Sterling Signals."

4. What is the key insight that should go near the end to reward
   readers who finish?

5. Recommend the strongest title + opening combination for Substack
   discovery (algorithmic reach to non-subscribers). Explain why.

OUTPUT: Titles, openings, arc, recommendation. Do NOT write the full
article yet.
```

### Prompt 3 of 3: Write the Article

**MODE: Extended Thinking ON**

```
Write the education article using your research, the recommended
title/opening, and the context package. 1,500–2,000 words.

Read voice_rules.md. All constraints apply.

Use the recommended title. List the other four alternatives for
reference.

CRITICAL: If this is a methodology topic, you are explaining HOW the
system thinks without revealing WHAT specific tools it uses. Describe
outcomes: "the system identifies momentum inflections," "institutional
accumulation signals," "trend acceleration confirmed." Never: "HMA
pivot low," "MACD cross-up," "Banker indicator."

STRUCTURE:

PREVIEW LINE: a concrete claim or number that hooks.

TABLE OF CONTENTS.

OPENING: Your recommended opening paragraph from the previous prompt.

BODY: The structure should match the topic. Use your narrative arc
from the previous prompt. General guidelines:

- Lead with the strongest claim or most surprising finding.
- Build from general to specific.
- Use real data from the context package and research at every stage.
- Include at least one markdown table.
- If an investor lesson: make the reader believe the stock looked good
  before revealing what you found. The lesson has no power otherwise.
- If methodology: include a funnel or comparison table.
- If research finding: cite the named source and present a genuine
  exception or limitation to build credibility.

PORTFOLIO CONNECTION: If a current holding naturally illustrates the
point, include it. If forcing it, skip entirely.

CLOSING: The key insight from your outline. One concrete takeaway the
reader can apply. Forward look to upcoming content.

FOOTER.

VISUAL BRIEF: List components for HTML production. Adapt to topic:
- Methodology: stat-grid (scanner stats), funnel flow diagram
- Research: stat-grid (key statistics), data table, case-study cards
- Investor lesson: case-study card, forensic data table, callout-box
  for the broader pattern

BEFORE YOU OUTPUT, verify:
□ Five title alternatives proposed with recommendation
□ Opens with the recommended hook, not preamble
□ Every claim backed by a specific number or named source
□ At least one data table with real numbers
□ Connection to Sterling Signals system is organic, not forced
□ Standalone value for non-portfolio readers
□ ZERO em dashes, indicator names, or AI references
□ 1,500–2,000 words
□ Visual brief is complete
```

---

## 4. Portfolio Review (3 Prompts)

**When:** No analysis session was run that week, or the portfolio
warrants a dedicated long-form review (significant moves, multiple
catalysts firing, milestone performance). This is a proper analytical
article, not a fallback summary.

### Prompt 1 of 3: Research — Market and Portfolio Data

**MODE: Research mode ON**

```
We are producing a portfolio review article for Sterling Signals.

Read portfolio.csv and equity_curve.csv for current positions.

RESEARCH TASK 1: MARKET CONTEXT

Search for:
A) Current prices and weekly/YTD returns for SPY, QQQ, IWM.
B) VIX current level and trend.
C) Major market events this week (Fed, earnings season, macro data).
D) Sector rotation data: which sectors led/lagged this week.

RESEARCH TASK 2: PORTFOLIO POSITIONS

For EACH open position in portfolio.csv:
A) Current price. Calculate P&L from entry price.
B) Key development this week: earnings, news, analyst action, or
   price movement > 5%.
C) Next upcoming catalyst with date.
D) Current short interest and any notable changes.

Present as a table:
Ticker | Entry | Current | P&L % | Force | Days Held | Key Development

RESEARCH TASK 3: STRUCTURAL FORCE STATUS

For each structural force represented in the portfolio:
A) Any policy developments this week.
B) Earnings from related companies (not just our holdings).
C) ETF flow data for relevant sector ETFs.
D) Regulatory decisions or upcoming dates.

RESEARCH TASK 4: FORWARD CALENDAR

A) Earnings dates for all portfolio tickers (next 2 weeks).
B) Fed meetings, economic data releases.
C) Sector-specific events, conferences, regulatory deadlines.

OUTPUT: Structured tables with source URLs. Flag any positions that
moved > 5% this week. Flag any upcoming catalysts within 7 days.
```

### Prompt 2 of 3: Analysis

**MODE: Extended Thinking ON**

```
Using the research data, perform a portfolio-level analysis. Use
extended thinking.

ANALYSIS TASK 1: PERFORMANCE ATTRIBUTION

A) Calculate portfolio return vs SPY, QQQ for the period.
B) Which positions contributed most to performance (positive and
   negative)? Rank by dollar contribution.
C) Which structural forces drove returns? Are we concentrated in one
   force or diversified?
D) Are any positions approaching exit criteria (stops, time limits,
   thesis degradation)?

ANALYSIS TASK 2: FORCE ASSESSMENT

For each structural force in the portfolio:
A) Is the force strengthening, stable, or weakening? State the
   specific evidence.
B) How does our exposure to this force compare to 4 weeks ago?
C) Are there any positions we should be watching more closely?

ANALYSIS TASK 3: RISK CHECK

A) Position concentration: is any single position > 15% of portfolio?
B) Force concentration: is any single force > 40% of portfolio?
C) Correlation risk: are multiple positions likely to move together
   on the same catalyst?
D) Upcoming binary events: any positions facing high-impact events
   in the next 2 weeks?

ANALYSIS TASK 4: FORWARD POSITIONING

A) Where do the best risk/reward setups sit in the current portfolio?
B) Are there positions where the original thesis is weakening?
C) What would we want to see from the next analysis session?

OUTPUT: Tables with analysis. Clear assessment for each position:
STRONG (thesis intact + performing), HOLD (thesis intact, needs time),
WATCH (thesis under pressure), and flag any that warrant EXIT review.

Do NOT write the article yet.
```

### Prompt 3 of 3: Write the Review

**MODE: Extended Thinking ON**

```
Write the portfolio review article using all research and analysis
from this conversation. 2,500–3,500 words.

Read voice_rules.md. All constraints apply.

TITLE: "Portfolio Review: [Hook with Number]"
Propose three alternatives. Use the strongest.

This is a long-form analytical article, not a summary or status update.
The reader should come away understanding our current positioning, why
we hold what we hold, what is working, what is not, and what we are
watching for.

STRUCTURE:

PREVIEW LINE: a specific number (alpha, best performer, or key event).

TABLE OF CONTENTS.

1. THE HEADLINE (200–300 words)
   Performance snapshot: portfolio return vs benchmarks. The one-sentence
   story of this period. The most significant event or development.

2. THE FORCES AT WORK (400–500 words)
   Each structural force represented in the portfolio. Current status
   (strengthening/stable/weakening). Evidence from research. This
   section explains WHY positions are moving, not just that they moved.

3. THE PORTFOLIO (500–700 words)
   Full P&L table (all positions). Then deeper analysis on:
   - Top performers: what drove the move, is it sustainable?
   - Underperformers: what is happening, does the thesis still hold?
   - Any position approaching exit criteria: state the specific trigger.

   Every position gets at least one sentence. No hiding.

4. RISK AND CONCENTRATION (200–300 words)
   Position concentration, force concentration, correlation risk. Any
   upcoming binary events. What keeps us up at night.

5. THE WEEK AHEAD (200–300 words)
   Specific calendar items from research. Earnings dates, Fed meetings,
   regulatory deadlines. What we are watching and what it means for
   each position.

6. THE BOTTOM LINE (150–200 words)
   Synthesis. Where are we in the broader market cycle? What is working
   and what is not? What should subscribers watch for in Tuesday and
   Thursday posts?

FOOTER.

VISUAL BRIEF: stat-grid (portfolio return, alpha, positions, best
performer), full portfolio data table, force status summary table,
callout-box for key risk, forward calendar.

BEFORE YOU OUTPUT, verify:
□ Three title alternatives proposed with recommendation
□ Portfolio table includes ALL positions with P&L
□ Every position addressed (no hiding underperformers)
□ Forward calendar includes specific dates
□ Risk section is honest about concentration
□ ZERO em dashes, indicator names, or AI references
□ 2,500–3,500 words
□ Visual brief is complete
```

---

## 5. Position Exit (1–2 Prompts)

**When:** A position is exited outside the normal Saturday briefing
cycle (stop triggered, thesis broken by news event).

### Optional Prompt 1: Quick Research

**MODE: Research mode ON**

Use this if you need fresh context on what drove the exit.

```
Quick research on $[TICKER] for a position exit article.

Search for:
A) Recent news on $[TICKER] (past 2 weeks).
B) Current sector conditions for [force name].
C) Any analyst commentary or downgrades.
D) Price action context: what happened and when.

OUTPUT: Brief structured findings with source URLs.
```

### Prompt 2: Write the Exit Article

**MODE: Extended Thinking ON**

```
Read voice_rules.md.

CLOSING POSITION: $[TICKER]

CONTEXT:
- Entry price: $[ENTRY] on [date]
- Exit price: $[EXIT]
- P&L: [calculate]
- Structural force: [force]
- Exit reason: [brief from user]

Write a position exit article (800–1,200 words).

CRITICAL FRAMING:
- Profitable (any gain): Lead with the return. Show the numbers.
- At a loss or small gain: Lead with discipline. "Our systematic exit
  discipline triggered on $[TICKER]." Focus on the thesis change.
  NEVER use "loss," "stopped out," "down."

TITLE:
- If profitable: "$[TICKER]: +[Y]% in [Z] Weeks"
- If not profitable: "$[TICKER]: Systematic Exit, Thesis Changed"

STRUCTURE:

PREVIEW LINE.

1. THE EXIT: Entry price, exit price, P&L (if positive), days held.
   What changed. One paragraph.

2. THE ORIGINAL THESIS: What we saw at entry. Structural force.
   Catalysts identified.

3. WHAT CHANGED: Specifics from research or context. What new
   information invalidated or shifted the thesis.

4. THE LESSON: One thing this trade teaches about our process.
   Be specific.

5. WHAT IS NEXT: Redeploying capital or waiting? Which structural
   forces look strongest?

FOOTER.

VOICE: Measured. An exit is a decision, not an apology.

VISUAL BRIEF: Stat-grid (entry/exit data), callout-box (lesson).

BEFORE YOU OUTPUT, verify:
□ Framing matches P&L direction
□ ZERO em dashes, indicator names, or AI references
□ 800–1,200 words
□ Visual brief is complete
```

---

## 6. Visual Carousel + Note (2 Prompts)

**When:** The context package identifies a topic suited to a visual
carousel for Substack Notes. These are lighter-weight than long-form
articles and focus on communicating one clear idea through 6 slides
and a companion note.

Common topics: company business model breakdowns, sector overviews,
screening funnel snapshots, portfolio snapshots, technical setup
explainers, tool walkthroughs, structural force primers.

### Prompt 1 of 2: Focused Research

**MODE: Research mode ON**

```
You are researching [TOPIC] for a visual carousel on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains the carousel topic, relevant data, and any specific stocks
or concepts to cover.]

This is for a 6-slide visual carousel with a companion Substack Note,
not a long-form article. Focus on the specific data needed to populate
the slides.

WHAT TO RESEARCH depends on the carousel type:

IF COMPANY BUSINESS MODEL:
A) Revenue by segment (most recent year and growth rates).
B) Cost structure: COGS, gross margin, major OpEx lines, operating
   margin.
C) TAM by addressable market segment (with source).
D) 3–5 key competitive advantages or moat elements.
E) Bear/base/bull price targets with probability weights and key
   drivers (4 bullets each).
F) 3–5 upcoming catalysts with dates.
G) Current price, market cap, shares outstanding.

IF SECTOR / FORCE OVERVIEW:
A) Force definition: what it is, capital flows, policy drivers.
B) 4–6 key companies with: ticker, market cap, revenue, growth, our
   status.
C) Key data points: ETF flows, industry projections, policy amounts.
D) 3–5 upcoming sector-level catalysts with dates.
E) The counter-thesis: what could reverse this force.

IF PORTFOLIO SNAPSHOT:
A) Current prices for all positions. P&L from entry.
B) Portfolio-level return vs benchmarks.
C) Force allocation breakdown.
D) Top 3 upcoming catalysts across the portfolio.

IF SCREENING / METHODOLOGY:
A) Scanner stats from the context package: stocks scanned, pass rates,
   rejection reasons.
B) Funnel data: how many at each stage.
C) 2–3 specific examples (one that passed, one that failed).

OUTPUT: Structured data tables optimised for slide population. Every
number the carousel will display should be in this output. Source URLs
for externally sourced data. **[UNVERIFIED]** for gaps.
```

### Prompt 2 of 2: Carousel Brief and Companion Note

**MODE: Extended Thinking ON**

```
Using all research from this conversation and the context package,
produce two deliverables.

Read voice_rules.md. All constraints apply.

DELIVERABLE 1: CAROUSEL DATA BRIEF

A structured brief that will be fed into STERLING_VISUAL_SYSTEM_v2.md
to produce the 6-slide JSX carousel. For EACH slide, extract the exact
data from your research:

SLIDE 1 — COVER:
- Company name / topic title
- Ticker + exchange (if applicable)
- Thesis subtitle (1–2 lines)
- Value chain pipeline (5 boxes) or topic framework
- 4 key metrics with deltas

SLIDE 2 — REVENUE ENGINE (or equivalent):
- Revenue segments with values and percentages
- Total revenue + growth
- Cost of revenue + gross profit + margins
- Key structural insight (one sentence)
Adapt by type: Revenue Engine for companies, Force Overview for
sectors, Funnel Breakdown for methodology topics.

SLIDE 3 — MARKET OPPORTUNITY:
- Top-level segments with TAM values
- Sub-markets per segment with status indicators
Adapt: Treemap for companies, Landscape Map for sectors, Comparison
Grid for methodology topics.

SLIDE 4 — FLYWHEEL / MOAT (or alternative):
- 4–6 node descriptions with metrics
- 3 sidebar moat insights
If no flywheel: use Catalyst Timeline (upcoming events) or Competitive
Landscape (comparison cards). State which alternative and why.

SLIDE 5 — WATERFALL:
- Revenue lines with values
- COGS, gross profit
- OpEx lines with values
- Operating income
- Margin badges and trend
Adapt: Cash Burn Bridge for pre-revenue, Force Allocation for
portfolio snapshots.

SLIDE 6 — SCENARIO TREE:
- Current price
- Bear/base/bull: probability, target, return, EV basis, 4 drivers
- Weighted target and risk/reward ratio

For each slide, note any adaptations needed from the standard spec
(e.g., "Slide 4: use Catalyst Timeline, no clear flywheel").

DELIVERABLE 2: COMPANION SUBSTACK NOTE

A ready-to-post Substack Note (150–250 words) to accompany the
carousel. Follow this structure:

1. HOOK (1 sentence): Surprising number, contrarian framing, or
   provocative question. Never open with the company name or ticker.

2. CONTEXT (2–3 sentences): What the company/topic is, why it matters
   now, the key tension or catalyst.

3. CAROUSEL CALLOUT (1 sentence): Reference the visual content.
   "Swipe through for the full breakdown" or "The waterfall tells the
   story." Give readers a reason to engage with the images.

4. CLOSE (1 sentence): Question or forward-looking statement to drive
   comments and engagement.

5. HASHTAGS: 2–3, relevant to sector and investment theme.

TONE: First-person, data-forward, direct. Confident analyst sharing
with peers, not a marketer selling a product.

---

BEFORE YOU OUTPUT, verify:
□ Carousel brief has exact data for all 6 slides
□ All numbers match the research (no estimates or rounding errors)
□ Slide adaptations are noted where the standard spec does not fit
□ Companion note opens with a hook, not the company name
□ Note is 150–250 words
□ Note references the carousel
□ 2–3 hashtags included
□ ZERO em dashes, indicator names, or AI references
□ ZERO banned terms in the note
```

---

## Quality Gates

### All Long-Form Articles (Sections 1–4)

- [ ] Preview line contains a specific number and compels the open
- [ ] Table of contents present
- [ ] At least one data table with real numbers
- [ ] No technical indicator names (HMA, MACD, RSI, Banker, UC, MCDX)
- [ ] No em dashes anywhere
- [ ] No AI/LLM references
- [ ] Positions mapped to structural forces, not micro themes
- [ ] Bear case or counter-thesis is specific and fair
- [ ] Key insight placed toward the end
- [ ] Ends with a specific forward catalyst and date
- [ ] Numbers from the context package match the article
- [ ] Title alternatives proposed and the strongest selected
- [ ] Visual brief is complete with component types and data
- [ ] Word count within range for the content type

### Visual Carousel + Note (Section 6)

- [ ] Carousel brief has exact data for all 6 slides
- [ ] Numbers match research (no rounding errors or estimates)
- [ ] Slide adaptations noted where standard spec does not fit
- [ ] Note opens with hook, not company/ticker name
- [ ] Note is 150–250 words and references the carousel
- [ ] 2–3 relevant hashtags
- [ ] ZERO banned terms in both deliverables

---

## Quick Reference

### Signal Branding

- **"GREEN signal"** for buy entries
- NEVER: TEAL, PASS, VIOLET, AMBER, STRONG BUY, SPEC BUY

### Banned Terms

**Indicators:** HMA, Hull Moving Average, RSI, MACD, KDJ, VWAP, Banker,
UC, Undercurrent, BoS, ExD, Beta >= 1.5, compound exit, 20% trailing stop

**System internals:** Gatekeeper, Investment Gate, Deep DD, 5-gate,
Tier 1/2/3, conviction score, conviction 1-10, profit lock, tiered stop,
gear shift, price cap, $25 cap, kill switch, STRONG BUY, SPEC BUY, NO GO

**AI-sounding:** "Let's dive in," "Here's the thing," "It's worth noting,"
"Interestingly enough," "In today's market," "Let me break this down,"
"The bottom line is"

**Geography:** UK ISA, GMT, BST, Roth IRA, PDT, 401k

### Approved Alternatives

| Instead of... | Use... |
|---|---|
| HMA/Banker/UC | "our screening system" |
| Entry signal | "momentum confirmed," "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation patterns" |
| Stop hit | "systematic exit discipline" |
| Gatekeeper | "cleared all screening stages" |
| Conviction 8–10 | "high conviction" |
| TEAL/PASS | "GREEN signal" |

### Portfolio Display Rules

- **15%+ gain:** Showcase with entry price and P&L percentage
- **Under 15%:** Include in tables, no spotlight narrative
- **Negative P&L:** Acknowledge honestly. State facts. Never "loss."
- **All positions:** Always show in portfolio tables. Never hide.

---

## Production Handoff

After completing a prompt sequence, you have two outputs:
1. **Article draft** — structured text ready for HTML production
2. **Visual brief** — component list for the production systems

### To produce the final HTML article:
Paste the article draft into a new Claude.ai chat, attach
`ARTICLE_SYSTEM_v2.md` and `voice_rules.md`, then paste the Article
System prompt from Part 1 of that document.

### To produce a visual carousel:
Paste the carousel data brief into a new Claude.ai chat, attach
`STERLING_VISUAL_SYSTEM_v2.md`, then paste the Visual System prompt
from Part 1 of that document.

### To produce both from a deep dive:
Run the Article System first (since it reuses the full research
conversation), then run the Visual System in the same chat or a new one.

---

## Prompt Count Summary

| Post | Prompts | Modes | Est. Time |
|------|---------|-------|-----------|
| Tuesday: new signal deep dive | 4 | Research × 2, Extended × 2 | ~30 min |
| Tuesday: sector/force/watchlist | 3 | Research, Extended × 2 | ~22 min |
| Thursday: education | 3 | Research, Extended × 2 | ~20 min |
| Portfolio review | 3 | Research × 2, Extended | ~25 min |
| Position exit | 1–2 | Research (opt), Extended | ~10 min |
| Visual carousel + note | 2 | Research, Extended | ~15 min |
