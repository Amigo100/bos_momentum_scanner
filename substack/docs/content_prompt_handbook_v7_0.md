# Sterling Signals: Content Prompt Handbook v8.0

> **Filename retained as `content_prompt_handbook_v7_0.md` for backward
> compatibility with Cowork path references. Content version: v8.0.**

> **Multi-prompt sequential system for Opus 4.6.**
> Each post uses 2-3 prompts in sequence within a single Claude.ai chat.
> Prompts specify which mode to use: Research, Extended Thinking, or Standard.
> Saturday's newsletter is produced by Prompt 11 in the Sterling Prompt
> Library during the Friday analysis session. It is NOT in this handbook.

---

## How to Use This Handbook

### What This Handbook Covers

Two post types produced in dedicated Claude.ai sessions:
- **Tuesday deep dive:** scanner-driven, produced Monday
- **Thursday education:** 4-week rotation, produced Wednesday

Saturday's "The Weekly Screening" comes from Prompt 11 in the analysis
session. The carousels and Tools & Tech content from v7 are discontinued.

### Workflow

1. Cowork's Sunday Mode A produces a **context package** for each post.
   This contains all data from the analysis session that the Claude.ai
   chat needs: decisions.json entries, signal history, financial metrics,
   rejection narratives, force context.
2. Open a **new** Claude.ai chat for each post.
3. Attach `config/voice_rules.md`.
4. Paste the context package first.
5. Paste each prompt in sequence. **Wait for the full response before
   pasting the next prompt.**
6. The final prompt produces complete HTML ready for Substack.

### Choosing Your Mode

Toggle these in Claude.ai before pasting each prompt.

| Mode | Toggle | Best For | Why |
|------|--------|----------|-----|
| **Research** | Research button ON | Data gathering: financials, 13F filings, ETF flows, news, insider transactions | Searches 20+ sources systematically. Produces cited findings with links. Far richer than standard web search. |
| **Extended Thinking** | Default with Opus 4.6 | Analysis, valuation, synthesis, long-form writing | Deep reasoning with internal chain-of-thought. Best for multi-step calculations, connecting data, and writing complete articles with narrative coherence. |

**The pattern:** Research mode gathers and verifies data. Extended
Thinking analyses it, builds the narrative, and writes the article.

### Content Types

| Post | Day | Produced | Prompts | Modes |
|------|-----|----------|---------|-------|
| **Tuesday deep dive** | Tuesday ~1pm AEDT | Written Monday | 2-3 (Research, Analysis, Write) | Research, Extended, Extended |
| **Thursday education** | Thursday ~1pm AEDT | Written Wednesday | 2-3 (Research/Discover, Write) | Research or Extended, Extended |
| **Ad-hoc trade alert** | Any day | Same day | 1 | Extended |
| **Ad-hoc position exit** | Any day | Same day | 1 | Extended |
| **Performance fallback** | Saturday (no session) | Friday or Saturday | 2 (Research, Write) | Research, Extended |

### Title Format

| Type | Pattern | Example |
|------|---------|---------|
| Deep dive (new signal) | "$TICKER: [Thesis Hook with Number]" | "$VYGR: Gene Therapy Platforms, Pharma Deal Flow at $800M, and a 500% Institutional Bet" |
| Deep dive (position update) | "$TICKER: [What Changed]" | "$AMPX: +56% in 10 Days, Director Selling $5.9M, and What We Do Next" |
| Deep dive (sector/force) | "[Force Name]: [Specific Hook]" | "The Nuclear Fuel Supply Chain: $188 SWU Prices, a Russian Ban, and Where $ASPI Fits" |
| Deep dive (watchlist) | "On Our Radar: [N] Stocks the System is Watching" | "On Our Radar: Three Stocks That Almost Cleared the Gate" |
| Education (methodology) | "[Number]-Based Hook About the System" | "1,817 Stocks In, 1 Out: How the Five-Stage Filter Chain Works" |
| Education (research) | "[Counterintuitive Finding]" | "Past Earnings Growth Does Not Predict Future Multibagger Returns" |
| Education (free tool) | "[Resource Name]: [Value Prop]" | "The Structural Forces Status Board: Updated Weekly, Always Free" |
| Education (investor lesson) | "[Specific Lesson from Real Example]" | "45% Dilution in Two Years: Why We Walked Away from a Defence Stock with 23% Short Interest" |

---

## Tuesday Deep Dive

### Priority 1: New Signal (3 Prompts)

The scanner produced a new buy signal. Saturday's briefing announced the
entry. This article delivers the complete thesis: what the company does,
why now, the numbers, the bear case, and exactly how we manage the
position. This is the flagship analytical content and should match the
depth and quality of the SKBL article.

#### Prompt 1 of 3: Research

**MODE: Research mode ON**

```
You are researching $[TICKER] for a deep dive article on Sterling
Signals. This stock was entered at $[PRICE] after clearing our
five-stage screening process. Saturday's briefing announced the entry.
This article delivers the complete thesis.

CONTEXT PACKAGE (from Cowork — pasted above this prompt):
[The context package contains the full decisions.json entry, signal
history trail, gate data, and bear case from our analysis session.
Use this as your foundation, then SUPPLEMENT with fresh research below.]

RESEARCH TASK 1: FINANCIAL BASELINE

Search SEC EDGAR for the most recent 10-Q or 10-K for $[TICKER]:
A) Revenue by segment for the last 8 quarters. Present as a TABLE with
   quarter-over-quarter and year-over-year growth rates.
B) Gross margin, operating margin, net margin per quarter (8 quarters).
   TABLE format.
C) Free cash flow: operating cash flow minus capex, trailing 4 quarters.
D) Balance sheet: cash and equivalents, total debt, current ratio.
E) Shares outstanding now vs 12 months ago. Calculate dilution percentage.
F) Any convertible notes, warrants, or upcoming maturities. Dates and
   dollar amounts.

RESEARCH TASK 2: RECENT DEVELOPMENTS

Search for the most recent earnings call or press release:
A) Revenue beat/miss vs consensus (dollar amount and percentage).
B) Guidance: raised, lowered, maintained. Specific numbers.
C) Key CEO/CFO quote about forward outlook (exact quote with source).
D) Segment-specific guidance or new product announcements.

RESEARCH TASK 3: INSTITUTIONAL AND INSIDER ACTIVITY

A) Latest 13F filings mentioning $[TICKER]:
   - Net institutional buying or selling (dollar amount, last quarter)
   - 2-3 notable funds that entered or exited (fund name, position size,
     percentage change)
B) Short interest: current percentage of float vs 3 months ago.
C) Insider transactions (Form 4): names, titles, shares, dollar amounts,
   dates. Flag any patterns (cluster buying/selling, 10b5-1 plan context).

RESEARCH TASK 4: COMPETITIVE LANDSCAPE

A) Name the 3-5 closest competitors or peer companies.
B) For each peer: market cap, revenue, EV/Revenue or EV/EBITDA, growth
   rate. Present as a comparison TABLE.
C) What is $[TICKER]'s specific competitive advantage? Search for moat
   evidence: patents, switching costs, network effects, regulatory
   barriers, cost advantages.
D) What is the biggest competitive threat and from whom?

RESEARCH TASK 5: CATALYST CALENDAR

Build a timeline of specific upcoming events:
A) Next earnings date and consensus expectations.
B) Regulatory decisions (FDA, DOE, DOD, FCC) with specific dates.
C) Contract awards, partnership milestones, product launches.
D) Industry events, conferences, or policy decisions.
E) Any known lock-up expirations or secondary offering windows.

OUTPUT: Structured tables with citations. Flag any data gaps. Flag any
findings that contradict the context package thesis. Do NOT write the
article yet.
```

#### Prompt 2 of 3: Analysis

**MODE: Extended Thinking ON, Research mode OFF**

```
Using your research and the context package data, build a complete
financial analysis. Use extended thinking to show your working at every
step. The analysis must be rigorous enough that a professional investor
would find it credible.

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

ANALYSIS TASK 2: VALUATION TRIANGULATION (4 methods, full working)

METHOD A: Historical Multiple Range
$[TICKER]'s P/E and EV/EBITDA over the last 3 years. Apply to your
bear/base/bull earnings. Show the calculation.

METHOD B: Discounted Cash Flow
Your FCF projections, 5-year explicit period + terminal. Discount rate:
10Y Treasury + 5% equity risk premium. Show every step. Sensitivity
table on discount rate and terminal growth.

METHOD C: Peer-Relative Valuation
Use the peer comparison table from your research. Apply median peer
multiples (P/E, EV/Revenue, EV/EBITDA) to $[TICKER]'s projected
financials. TABLE required.

METHOD D: Catalyst-Adjusted
Identify 3-5 binary events from the catalyst calendar. For each:
probability percentage and dollar impact on the stock price. Present
as a probability-weighted expected value.

ANALYSIS TASK 3: SYNTHESIS

Weight the four methods by company type (state which weighting and why;
e.g., pre-revenue companies weight DCF and catalyst-adjusted more heavily).

Produce bear/base/bull 12-month price targets with probability weights.
Do NOT default to 25/50/25. Assign probabilities based on the specific
assumptions.

Calculate: expected value, risk/reward ratio from current entry price,
and the three assumptions most likely to be wrong (and in which direction).

Cross-check your targets against the context package targets (from the
analysis session). If they diverge by more than 15%, explain why.

OUTPUT: Tables with full working. Do NOT write the article yet.
```

#### Prompt 3 of 3: Write the Article

**MODE: Extended Thinking ON**

```
Write the complete deep dive article using ALL research and analysis
from this conversation. This should be 2,500-3,500 words of the highest
quality analytical writing. Use extended thinking to plan the narrative
arc before writing.

Read the attached voice_rules.md. These rules are non-negotiable:
- No em dashes anywhere (use colons, periods, semicolons)
- No AI/LLM references
- No technical indicator names
- Structural forces, not micro themes
- Specific numbers for every claim
- Vary sentence length deliberately

TITLE: "$[TICKER]: [Thesis hook with at least one specific number]"

OUTPUT: Complete, self-contained HTML document.

Use the Sterling Signals design system:
- DM Serif Display for headings, DM Sans for body, JetBrains Mono for
  data tables
- Max-width 780px, padding 40px 24px
- Colour palette: navy #0a1628, blue #1a3a5c / #2563eb, slate #334155 /
  #64748b, green #16a34a, red #dc2626
- Tables: #0f2440 header with white text, alternating #fff/#f8fafc rows,
  monospace for numbers
- Stat grid at the top (entry price, structural force, conviction tier,
  next catalyst)
- Price target cards: Bear (red-tinted #fdf6f4), Base (blue #f4f7fa),
  Bull (green #f4faf5)

ARTICLE STRUCTURE:

PREVIEW LINE: 1-2 sentences for the email/feed preview. Must contain a
number that creates curiosity. This is the first thing subscribers see.

TABLE OF CONTENTS: linked section list.

1. THE THESIS IN ONE SENTENCE
   A single sentence capturing the entire investment thesis. It should be
   quotable, specific, and memorable.

2. WHAT THIS COMPANY DOES (200-300 words)
   Plain-language explanation of the business model. Assume the reader has
   never heard of this company. Explain what it does, how it makes money,
   and why that matters. No jargon without immediate explanation.

3. WHY NOW (300-400 words)
   What changed to create this opportunity. The structural force driving
   capital flows. The specific trigger or catalyst that made the screening
   system flag this stock at this moment. How the macro environment creates
   tailwinds. This section must make the reader feel the urgency of the
   timing without resorting to hype.

4. THE NUMBERS (400-500 words)
   Revenue trajectory with an HTML TABLE of quarterly data (minimum 4
   quarters). Margin analysis showing the trend. Balance sheet assessment.
   Peer comparison TABLE (3-5 peers with market cap, revenue, growth,
   multiples). The narrative here is data-driven: let the tables tell the
   story, with prose connecting the dots between data points.

5. WHAT WE THINK IT'S WORTH (300-400 words)
   Three colour-coded price target cards (Bear/Base/Bull) with:
   - Target price
   - Probability weight (not 25/50/25 unless justified)
   - Driving assumption (one sentence)
   - Valuation method used

   Below the cards: expected value calculation and risk/reward ratio from
   entry price.

6. THE BEAR CASE (200-300 words)
   This is NOT a throwaway section. It is the section that builds trust
   with sophisticated readers. Present the bear case as if you were SHORT
   this stock. Name the specific risks. What data point kills the thesis?
   What does the competition look like? What is the worst realistic
   12-month outcome?

7. HOW WE ARE PLAYING IT (150-200 words)
   Entry price. Position tier and what that means for sizing relative to
   the portfolio. The structural force this maps to. Specific exit criteria:
   price level, fundamental trigger, time-based review. What confirms the
   thesis. What disconfirms it.

8. WHAT HAPPENS NEXT (100-150 words)
   The next catalyst with a specific date. What we are watching. What the
   reader should watch. This section pulls the reader forward to the next
   Saturday briefing update.

FOOTER:
"Every screening result. Every entry. Every exit.
sterlingsignals.substack.com"

"Not financial advice. Informational and educational content only.
Past performance does not guarantee future results."

QUALITY CHECK (verify before outputting):
- Does the preview line contain a specific number?
- Does section 4 have at least TWO HTML tables (quarterly + peer comp)?
- Does section 5 have three distinct price targets with non-default
  probability weights?
- Does section 6 feel like it was written by a sceptic, not a bull?
- Is the article 2,500-3,500 words?
- Are there ZERO em dashes in the entire output?
- Are there ZERO technical indicator names?
- Does section 8 name a specific date for the next catalyst?
- Does the stat grid at the top show entry price, force, tier, and
  next catalyst?
```

---

### Priority 2: Position Update (2 Prompts)

A held position had a material development: earnings, FDA decision,
analyst action, or a move exceeding 10%. Saturday's briefing flagged it.
This article provides the full analysis of what changed and what we do.

#### Prompt 1 of 2: Research the Development

**MODE: Research mode ON**

```
You are researching a material development on $[TICKER] for a position
update deep dive on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains original entry data, P&L, structural force mapping, and the
material development summary from Cowork.]

RESEARCH TASK 1: THE DEVELOPMENT

Search for comprehensive coverage of [the specific event]:
A) Primary source: the earnings release, FDA letter, press release,
   or SEC filing. Exact numbers.
B) Analyst reactions: upgrades/downgrades with old/new price targets.
   Name the firms.
C) Market reaction: price move on the day, volume vs average.
D) Management commentary: direct quotes from earnings calls, press
   conferences, or interviews.

RESEARCH TASK 2: UPDATED FINANCIALS

A) If earnings: full quarterly breakdown. Revenue by segment, margins,
   EPS, guidance. Compare to consensus and prior quarter. TABLE.
B) Updated balance sheet: cash, debt, any changes.
C) Updated institutional activity since the development.

RESEARCH TASK 3: THESIS COMPARISON

Compare the current state to what the context package shows as the
original entry thesis:
A) Which specific elements of the thesis have been validated?
B) Which elements have been challenged or invalidated?
C) Has the competitive landscape changed?
D) Are there new risks that did not exist at entry?

OUTPUT: Structured tables. Explicit thesis comparison. Do NOT write yet.
```

#### Prompt 2 of 2: Write the Update

**MODE: Extended Thinking ON**

```
Write the position update article using all research from this
conversation and the context package data. 2,000-2,500 words.

Read voice_rules.md. No em dashes. No AI references. No indicator names.

TITLE: "$[TICKER]: [What Changed, with a Number]"

Complete HTML, Sterling Signals design system.

STRUCTURE:

PREVIEW LINE.
TABLE OF CONTENTS.

1. THE ORIGINAL THESIS (200-300 words)
   What we said when we entered. Entry price, structural force, conviction.
   The key catalysts we identified. The bear case we acknowledged. Include
   a stat grid showing entry data.

2. WHAT HAPPENED (300-400 words)
   The material development presented factually. Numbers from your research.
   What the market did in response.

3. THESIS CHECK (300-400 words)
   Structured comparison: what we predicted vs what occurred. TABLE format
   with columns: "At Entry" | "Now" | "Status" (Validated/Challenged/
   Unchanged). Be specific about which elements held and which did not.

4. UPDATED NUMBERS (200-300 words)
   Revised financials if the development changes the projection. Updated
   valuation. How the risk/reward has shifted since entry. Updated peer
   comparison if relevant.

5. WHAT WE ARE DOING (150-200 words)
   Holding, adding, trimming, or exiting. The specific reasoning. Updated
   exit criteria if applicable. What we watch next.

FOOTER and QUALITY CHECK per Priority 1 standards.
```

---

### Priority 3-5: Sector, Force, or Watchlist Analysis (2 Prompts)

No new signal and no material development. The topic is determined by
Cowork's priority logic: subscriber request (P3), force deep dive (P4),
or watchlist analysis (P5).

#### Prompt 1 of 2: Research

**MODE: Research mode ON**

```
You are researching [TOPIC] for a deep dive on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains portfolio positions in this force/sector, watchlisted stocks,
force context from Prompt 2, and signal history for relevant tickers.]

RESEARCH TASK 1: STRUCTURAL FORCE ASSESSMENT

Search for the current state of the [FORCE NAME] structural force:
A) Capital flows: relevant ETF inflows/outflows (name 3-5 ETFs, dollar
   amounts, last 3 months). TABLE.
B) Government policy: bills, budgets, executive orders, regulatory
   decisions with dollar amounts and timelines. Specific legislation
   or rule names.
C) Industry data: market size, growth rate, projections from named
   sources (IEA, Gartner, McKinsey, government agencies).
D) Recent institutional positioning: 13F trends across the sector.

RESEARCH TASK 2: COMPANY-LEVEL DATA

For EACH company discussed (portfolio positions + watchlisted stocks):
A) Current price, market cap, EV.
B) Most recent quarterly revenue, growth rate, margin.
C) Key competitive differentiator in one sentence.
D) Next catalyst with date.
E) If watchlisted: what price level or event would trigger our entry.

RESEARCH TASK 3: RISKS AND COUNTER-THESIS

A) What would reverse the capital flows into this force?
B) Specific policy or regulatory risk.
C) Valuation concern: is the sector expensive relative to history?
D) Crowding: is the trade becoming consensus?

OUTPUT: Structured tables. Citations. Do NOT write yet.
```

#### Prompt 2 of 2: Write the Analysis

**MODE: Extended Thinking ON**

```
Write the analysis using all research and the context package.
2,000-3,000 words. Complete HTML.

Read voice_rules.md. Same constraints as all other posts.

TITLE: "[Force or Sector]: [Specific Hook with a Number]"

STRUCTURE:

PREVIEW LINE.
TABLE OF CONTENTS.

1. THE STRUCTURAL FORCE (200-300 words)
   The macro thesis. Why this force exists and why capital is flowing.
   Key data points. Current status. What changed recently. This section
   should make a reader who has never heard of this force understand why
   it matters.

2. THE LANDSCAPE (500-600 words)
   Key companies mapped across the force. How they relate to each other.
   Competitive dynamics. Where our holdings fit. For watchlisted stocks:
   what each offers and what prevents entry today.
   Include a TABLE: ticker, market cap, revenue, growth, multiple, our
   status (held/watchlisted/rejected).

3. THE DATA (300-400 words)
   Industry data, ETF flows, earnings trends, regulatory timeline.
   Tables where they clarify. This section is evidence: specific numbers
   from your research that either support or challenge the thesis.

4. HOW WE ARE POSITIONED (200-300 words)
   What we hold in this force and why. Current P&L on each position.
   What we do not hold and why. What would change our positioning.
   Forward catalysts to watch with dates.

FOOTER and QUALITY CHECK per Priority 1 standards.
```

---

### Quality Gate (All Tuesday Variants)

Before publishing, verify every item:

- [ ] Preview line contains a specific number and compels the open
- [ ] Table of contents present and linked
- [ ] At least one HTML data table with real numbers
- [ ] No technical indicator names (HMA, MACD, RSI, Banker, UC, MCDX)
- [ ] No em dashes anywhere in the entire document
- [ ] No AI/LLM references (Claude, AI-powered, machine learning)
- [ ] Positions mapped to structural forces, not micro themes
- [ ] Bear case is specific, fair, and reads like a sceptic wrote it
- [ ] Exit criteria are explicit (for signal and update deep dives)
- [ ] Key insight placed toward the end of the article
- [ ] Ends with a specific forward catalyst and date
- [ ] Numbers from the context package match numbers in the article
- [ ] Stat grid at top with entry price, force, tier, next catalyst
- [ ] Word count: 2,000-3,500 depending on variant

---

## Thursday Education

### Always Free, 4-Week Rotation

The growth engine. These posts attract new subscribers through Substack's
algorithm. They must have standalone value: a reader who does not follow
the portfolio should still find the post worth their time.

### Week A: Methodology (2 Prompts)

How the screening system works. The five-stage filter chain. Why the
rejection rate matters. Position sizing philosophy. The structural forces
framework. NEVER reveal specific indicator names.

#### Prompt 1 of 2: Structure and Data

**MODE: Extended Thinking ON**

```
You are planning a methodology post for Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains scanner stats, funnel numbers, rejection examples from
signal_history_rows.csv.]

TOPIC: [Specific topic from Cowork, e.g., "how the five-stage filter
chain works" or "why we size positions by tier" or "the structural
forces framework"]

Using extended thinking, plan the article:

1. What is the single most surprising or counterintuitive claim you
   can make about this topic? This becomes the opening line.

2. What specific data from the context package makes this concrete?
   Pull exact numbers: tickers scanned, rejection rates, tier breakdown,
   specific stocks rejected and why.

3. What is the narrative arc? The reader should go from "I didn't know
   this" to "now I understand the logic" to "I can see why this works"
   to "I want to apply this thinking."

4. What is the key insight that should go near the end to reward
   readers who finish the full article?

5. Is there a natural connection to a current portfolio position? If
   yes, note it. If forcing it, skip it.

OUTPUT: Structured outline with data points, opening hook, and narrative
arc. Do NOT write the article yet.
```

#### Prompt 2 of 2: Write

**MODE: Extended Thinking ON**

```
Write the methodology article using your outline and the context package.
1,500-2,000 words. HTML or clean Markdown.

Read voice_rules.md. All constraints apply.

CRITICAL: You are explaining HOW the system thinks without revealing
WHAT specific tools it uses. Describe outcomes: "the system identifies
momentum inflections," "institutional accumulation signals," "trend
acceleration confirmed." Never: "HMA pivot low," "MACD cross-up,"
"Banker indicator."

TITLE: "[Number-Based Hook About the System]"

STRUCTURE:

PREVIEW LINE: a concrete claim or number that hooks.

TABLE OF CONTENTS.

OPENING: Start with the most surprising data point. Not "today we
explain our system." Instead: "Last Friday, 1,817 stocks entered our
screening process. 1,816 were rejected. Here is how."

BODY: Build from the general to the specific. Start with the overall
philosophy (why systematic screening outperforms discretionary picking),
then walk through the specific process, using real data from the context
package at every stage. Each section should leave the reader smarter.

Include at least one TABLE showing the funnel (stages, counts, rejection
rates). If relevant, include a comparison table (e.g., our system vs
typical retail approach).

PORTFOLIO CONNECTION: If natural, show how a specific position
illustrates the methodology. If forced, skip entirely.

CLOSING: The key insight. Then: what this means for subscribers (why
following a system matters, what they should watch for in our upcoming
posts).

QUALITY CHECK:
- [ ] Opens with a surprising number, not preamble
- [ ] Explains the system without revealing any indicator names
- [ ] Uses real data from the context package (specific counts, tickers)
- [ ] At least one table
- [ ] A reader who does not follow the portfolio finds this valuable
- [ ] No em dashes, AI references, or indicator names
- [ ] 1,500-2,000 words
```

---

### Week B: Investment Education (2 Prompts)

Research on multibagger characteristics. Momentum studies. Academic
findings applied to the system's framework. The goal is to teach a
genuine investing concept through specific data.

#### Prompt 1 of 2: Research

**MODE: Research mode ON**

```
You are researching [TOPIC] for an education post on Sterling Signals.

CONTEXT PACKAGE (pasted above):
[Contains the specific concept or finding to cover, relevant data
points from the system.]

TOPIC: [e.g., "academic research on multibagger stock characteristics"
or "why momentum strategies work and when they fail" or "how structural
forces differ from sector rotation"]

RESEARCH TASKS:

A) Find the primary academic or practitioner source:
   - Author, institution, publication date, methodology
   - Key finding stated as a specific number or statistic
   - Sample size and time period studied

B) Find 2-3 supporting or contradicting sources:
   - Do other studies confirm or challenge this finding?
   - What is the base rate of success?
   - What are the known limitations?

C) Find the counterintuitive angle:
   - What does this finding say that contradicts conventional wisdom?
   - What would most retail investors get wrong about this topic?

D) Find specific examples:
   - 2-3 real companies or historical events that illustrate the finding
   - Specific returns, dates, and outcomes

OUTPUT: Structured research with citations. The counterintuitive finding
is the most important element. Do NOT write yet.
```

#### Prompt 2 of 2: Write

**MODE: Extended Thinking ON**

```
Write the education article. 1,500-2,000 words. HTML or Markdown.

Read voice_rules.md.

TITLE: "[The Counterintuitive Finding as a Claim]"
Example: "Past Earnings Growth Does Not Predict Future Multibagger Returns"

STRUCTURE:

PREVIEW LINE: the counterintuitive finding in 1-2 sentences.

TABLE OF CONTENTS.

1. THE CLAIM (100-150 words)
   State the finding directly. Do not hedge. "A study of 464 stocks that
   returned 1,000%+ found that..." This should feel like a claim worth
   arguing about.

2. THE EVIDENCE (400-500 words)
   The research methodology, sample, and findings. Specific numbers
   throughout. Include at least one TABLE showing key data. Present
   the evidence as if making a case to a sceptical investor.

3. WHY THIS MATTERS FOR STOCK SELECTION (300-400 words)
   What does this finding imply for how investors should screen for
   stocks? What popular approaches does it invalidate? What does it
   validate? This is where the finding connects to practical investing.

4. THE EXCEPTION (200-250 words)
   When does this finding NOT apply? Name a specific counter-example
   or limitation. This section builds credibility: it shows the analysis
   is honest, not a sales pitch for one idea.

5. CONNECTION TO OUR SYSTEM (100-200 words, ONLY if natural)
   If the finding directly relates to how our screening system works,
   explain the connection. "This is why our system screens for X rather
   than Y." If no natural connection exists, SKIP THIS SECTION ENTIRELY.

6. THE TAKEAWAY (100-150 words)
   One concrete insight the reader can apply. What should they look for
   or stop doing? End with a forward look connecting to upcoming content.

QUALITY CHECK:
- [ ] The title makes a specific, surprising claim
- [ ] Section 2 cites at least one named source with methodology
- [ ] Section 4 presents a genuine exception, not a strawman
- [ ] If section 5 exists, the connection is organic
- [ ] Standalone value for non-portfolio readers
- [ ] No em dashes, AI references, or indicator names
- [ ] 1,500-2,000 words
```

---

### Week C: Free Tool or Resource (2 Prompts)

A permanent lead magnet. Something subscribers bookmark and return to.
The Screener equivalent for Sterling Signals: a scanner funnel summary,
a structural forces status board, a "how to read our updates" guide, or
a watchlist framework.

#### Prompt 1 of 2: Build the Resource

**MODE: Extended Thinking ON**

```
You are building a free resource for Sterling Signals subscribers.

CONTEXT PACKAGE (pasted above):
[Contains the data needed to build the resource: scanner stats, force
data, portfolio data, etc.]

RESOURCE: [Specific resource from Cowork, e.g., "structural forces
status board" or "how to read our portfolio updates" or "the weekly
scanner funnel explained"]

Using the context package data, build the complete resource:
1. What data does this resource present?
2. What format makes it most useful? (Table, guide, reference card)
3. What makes this worth bookmarking? What would make someone return?
4. How does this resource improve over time? (Updated weekly, expanded)

BUILD: The complete resource content with all data filled in. Use real
numbers from the context package. If this is a status board, populate
it. If this is a guide, write the full guide.

OUTPUT: Complete resource content, ready to be wrapped in an article.
```

#### Prompt 2 of 2: Write the Article Around It

**MODE: Extended Thinking ON**

```
Write the article that frames and presents the resource. 1,200-1,800
words. HTML.

Read voice_rules.md.

TITLE: "[Resource Name]: [Value Proposition]"

STRUCTURE:

PREVIEW LINE.

1. WHAT THIS IS AND WHY IT EXISTS (150-200 words)
   Brief context. What problem this solves. Why we are giving it away.

2. THE RESOURCE (main body, 600-1,000 words)
   The complete resource from Prompt 1, formatted as HTML with styled
   tables, callout boxes, and clear structure. This is the content people
   bookmark.

3. HOW TO USE IT (150-200 words)
   Practical guidance. What to check weekly. What changes mean.

4. WHAT IS COMING (100 words)
   How this resource connects to the rest of Sterling Signals. What
   subscribers get beyond this free resource.

FOOTER.

This should be permanently useful. A subscriber who finds this post
six months from now should still get value from it.
```

---

### Week D: Investor Lessons (3 Prompts)

Real examples from our screening process. A stock we rejected and why.
A capital structure trap. A turnaround that failed. The lesson is taught
through a specific, real story with specific numbers.

#### Prompt 1 of 3: Select the Story

**MODE: Extended Thinking ON**

```
Today is an Investor Lessons post. I want to teach through a real
example from our screening process.

CONTEXT PACKAGE (pasted above):
[Contains signal_history_rows.csv entries for rejected stocks, their
rejection reasons, and portfolio parallels.]

From the context package, identify 2-3 candidate stories. For each:

1. The stock and what happened (rejected, failed at which stage, why)
2. The lesson it teaches (stated as a specific, surprising claim)
3. The hook: one number that would make someone stop scrolling
4. Is this timely? (Connected to a recent market event or a common
   investor mistake?)
5. Does it connect naturally to a portfolio position that AVOIDED this
   trap? (If so, note it. If not, the story stands on its own.)

Recommend your top choice and explain why it teaches the most valuable
lesson.
```

#### Prompt 2 of 3: Research the Example

**MODE: Research mode ON**

```
Research [SELECTED STOCK] to build the full story.

Search for:
A) The company's recent financials: revenue trend, margins, cash flow.
   Enough to understand the business.
B) The specific issue our system identified (from the context package
   rejection reason). Verify with public data:
   - If dilution: shares outstanding history, warrant details, placement
     prices and dates
   - If competitive deterioration: competitor moves, market share data
   - If capital structure: debt schedule, covenant details, maturity dates
   - If turnaround failure: management history, prior promises vs results
C) What happened AFTER we rejected it (if data available):
   - Did the stock decline? By how much?
   - Did the risk materialise?
   - Or did it rally (and if so, does our rejection still look correct
     given the risk we identified)?
D) The broader pattern: is this a common trap? How often do stocks with
   this profile fail?

OUTPUT: Structured findings. The goal is to tell a specific story with
specific numbers that teaches a general principle.
```

#### Prompt 3 of 3: Write the Lesson

**MODE: Extended Thinking ON**

```
Write the investor lesson. 1,500-2,000 words. HTML.

Read voice_rules.md.

TITLE: "[Specific Detail]: [The Lesson in Plain Language]"
Example: "45% Dilution in Two Years: Why We Walked Away from a Defence
Stock with 23% Short Interest"

STRUCTURE:

PREVIEW LINE: the most surprising number from the story.

TABLE OF CONTENTS.

1. THE SETUP (200-300 words)
   What made this stock look attractive. The surface-level case: sector
   tailwind, short interest, momentum signals. Make the reader understand
   why someone WOULD buy this. The lesson has no power if the reader
   does not first believe the stock looked good.

2. WHAT WE FOUND (400-500 words)
   The forensic discovery. Walk through it step by step: what data we
   pulled, what it showed, why it changed the picture. This is the
   educational core. Specific numbers at every step. Tables if they
   clarify.

3. THE DECISION (150-200 words)
   We walked away. State it plainly. No self-congratulation. Just the
   facts: the system identified this risk, the risk exceeded our
   threshold, the position was not entered.

4. THE BROADER PATTERN (300-400 words)
   Is this a common trap? How often do stocks with this profile fail?
   What should investors look for to avoid it? Generalise the specific
   example into a principle.

5. IN OUR PORTFOLIO (100-200 words, ONLY if natural)
   If a current holding avoided this exact trap, show the comparison.
   "Our [TICKER] has [specific metric that is the opposite of the trap]."
   If nothing connects naturally, SKIP.

6. THE TAKEAWAY (100-150 words)
   One concrete thing the reader can check on any stock they own or are
   considering. End with a forward look.

QUALITY CHECK:
- [ ] Section 1 makes the reader believe the stock looked good
- [ ] Section 2 uses specific numbers from the research
- [ ] Section 4 generalises into a reusable principle
- [ ] If section 5 exists, the connection is genuine
- [ ] The title names the specific detail, not a vague concept
- [ ] No em dashes, AI references, indicator names
- [ ] 1,500-2,000 words
```

---

### Quality Gate (All Thursday Variants)

- [ ] Opens with a hook, not preamble
- [ ] Teaches something genuinely useful and specific
- [ ] Every claim backed by a specific number or named source
- [ ] Connection to Sterling Signals system is organic, not forced
- [ ] No indicator names, em dashes, or AI references
- [ ] Standalone value: non-portfolio readers find it worth their time
- [ ] Ends with an actionable takeaway, not "thanks for reading"
- [ ] All data from the context package, not invented
- [ ] 1,200-2,000 words depending on variant

---

## Ad-Hoc Prompts

These cover situations outside the normal Tuesday/Thursday rhythm.
They can publish any day and replace whatever was scheduled.

### Mid-Week Trade Alert (1 Prompt)

**When:** A position is entered outside the normal Friday analysis
session (e.g., an intra-week exceptional setup, a stop-loss re-entry
at a better level). For signals from the Friday analysis, use the
Tuesday deep dive Priority 1 sequence above.

**MODE: Extended Thinking ON**

```
Read the attached voice_rules.md.

NEW POSITION: $[TICKER] at $[PRICE]

CONTEXT:
- Entry date: [date]
- Structural force: [force name]
- Reason for entry: [brief thesis from the user]

Web search for:
- Current stock price (verify against entry)
- Recent news and catalysts (past 2 weeks)
- Most recent quarterly earnings: revenue beat/miss, guidance
- 13F institutional activity (recent quarter)
- Short interest as percentage of float

Write a trade alert as complete HTML (1,200-1,800 words).
Sterling Signals design system (780px, navy/blue/slate palette).

STRUCTURE:

PREVIEW LINE: 1-2 sentences with a specific number.

1. THE SIGNAL: "$[TICKER] at $[PRICE]. GREEN signal confirmed." What
   the company does in one sentence. Structural force connection.

2. WHY THIS COMPANY: What makes it unique. Structural advantage. 2-3
   paragraphs with specific data from your search.

3. WHAT TRIGGERED THE SIGNAL: Use approved terms only: structural
   pivot confirmation, momentum confirmed, institutional accumulation
   patterns. What made this pass when 99%+ are rejected? Include funnel
   context.

4. THE SETUP: 4-6 specific data points from your search. Revenue
   trajectory, margin direction, institutional activity, upcoming
   catalysts. At least one HTML TABLE.

5. BEAR CASE: The specific risk. What data point kills the thesis.
   What the worst realistic 12-month outcome looks like.

6. HOW WE ARE PLAYING IT: Entry price, position sizing rationale,
   structural force, specific exit criteria.

7. WHAT WE ARE WATCHING: Next catalyst with date. What confirms or
   invalidates.

FOOTER.

VOICE: Decisive. "We are entering $[TICKER] at $[PRICE]. Here is why."
Not "After careful analysis, we believe this presents an opportunity."
```

### Standalone Position Exit (1 Prompt)

**When:** A position is exited outside the normal Saturday briefing
cycle (e.g., stop triggered mid-week, thesis broken by news event).

**MODE: Extended Thinking ON**

```
Read the attached voice_rules.md.

CLOSING POSITION: $[TICKER]

CONTEXT:
- Entry price: $[ENTRY] on [date]
- Current/exit price: $[EXIT]
- P&L: [calculate]
- Structural force: [force]
- Exit reason: [brief from user]

Web search for: recent news on $[TICKER], current sector conditions.

Write a position exit article (800-1,200 words, HTML).

CRITICAL FRAMING:
- Profitable (any gain): Lead with the return. Show the numbers.
- At a loss or small gain: Lead with the discipline angle. "Our
  systematic exit discipline triggered on $[TICKER]." Focus on the
  thesis change. NEVER use "loss," "stopped out," "down."

TITLE:
- If profitable: "$[TICKER]: +[Y]% in [Z] Weeks"
- If not profitable: "$[TICKER]: Systematic Exit, Thesis Changed"

STRUCTURE:

PREVIEW LINE.

1. THE EXIT: Entry price, exit price, P&L (if positive), days held.
   What changed. One paragraph.

2. THE ORIGINAL THESIS: What we saw at entry. The structural force.
   The catalysts we identified.

3. WHAT CHANGED: Specifics from your search. What new information
   invalidated or shifted the thesis.

4. THE LESSON: One thing this trade teaches about our process. Be
   specific: "This is why we set exit triggers at entry, not after
   the fact."

5. WHAT IS NEXT: Redeploying capital or waiting? Which structural
   forces look strongest?

FOOTER.

VOICE: Measured. An exit is a decision, not an apology. Show the
process working regardless of outcome.
```

### Performance Review Fallback (2 Prompts)

**When:** No analysis session was run that week (travel, holiday, etc.)
and the Saturday briefing was not produced via Prompt 11. Use this to
produce a performance-focused newsletter as a substitute.

#### Prompt 1 of 2: Gather Fresh Data

**MODE: Research mode ON**

```
No analysis session was run this week. We need a performance-focused
newsletter using portfolio data and web search only.

Read portfolio.csv and equity_curve.csv for current positions.

RESEARCH:

MARKET: Web search for current prices and weekly/YTD returns for SPY,
QQQ, IWM. VIX current level. Major market events this week.

PORTFOLIO: Web search for current prices of ALL open positions in
portfolio.csv. Recalculate P&L from entry prices. Present as a TABLE:
Ticker | Entry | Current | P&L% | Structural Force | Days Held.

THEMES: For each structural force represented in the portfolio, search
for any developments this week: policy changes, earnings from related
companies, regulatory decisions.

NEXT WEEK: Earnings dates for tickers in the portfolio. Fed meetings,
economic data releases, sector-specific events.

OUTPUT: Structured tables with all data. Flag any positions that moved
more than 5% this week.
```

#### Prompt 2 of 2: Write the Newsletter

**MODE: Extended Thinking ON**

```
Write "The Weekly Screening" newsletter using the data above.
2,000-2,500 words. Complete HTML. Sterling Signals design system.

Read voice_rules.md.

TITLE: "The Weekly Screening: Week [N]: [Forward-looking hook]"

Follow the standard briefing structure from Prompt 11:
1. The Headline (performance snapshot, key event)
2. The Forces at Work (structural forces with available data)
3. The Portfolio (full P&L table, winners, losers, alpha)
4. The Screening (no new scan this week: use "selectivity" framing.
   "No analysis session this week. Our existing positions continue to
   compound. Here is where we stand.")
5. The Week Ahead (calendar from your research)
6. The Bottom Line (synthesis, Tuesday/Thursday preview)

FOOTER.

The newsletter should feel complete even without a fresh scan. The
portfolio update and week ahead sections carry the issue.
```

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
| Conviction 8-10 | "high conviction" |
| TEAL/PASS | "GREEN signal" |

### Portfolio Display Rules

- **15%+ gain:** Showcase with entry price and P&L percentage
- **Under 15%:** Include in tables, no spotlight narrative
- **Negative P&L:** Acknowledge honestly. State facts. Never "loss."
- **All positions:** Always show in portfolio tables. Never hide.

### HTML Design System

**Fonts:**
- DM Serif Display (headings: h1 42px, h2 28px)
- DM Sans (body: 17px, weight 400/500/600/700)
- JetBrains Mono (data tables, ticker symbols)

**Layout:** max-width 780px, margin 0 auto, padding 40px 24px

**Colours:**
Navy: #0a1628, #0f2440, #1a3a5c
Blue: #2563eb (links), #3b82f6, #60a5fa, #dbeafe (light bg)
Slate: #0f172a (headings), #334155 (body), #64748b (muted)
Green: #16a34a (positive P&L, READY badges)
Red: #dc2626 (negative P&L)
Amber: #d97706 (warnings, APPROACHING)

**Tables:**
Header: bg #0f2440, color #fff, font-size 13px, uppercase
Rows: alternating #fff / #f8fafc, border-bottom 1px #e2e8f0
Ticker column: JetBrains Mono, weight 600

**Stat grid (top of post):**
Flex row, gap 16px. Box: bg #f1f5f9, border-radius 8px, padding 16px.
Number: 24px weight 700 #0f2440. Label: 12px uppercase #64748b.

**Price target cards:**
Bear: bg #fdf6f4, border-left 4px #dc2626
Base: bg #f4f7fa, border-left 4px #2563eb
Bull: bg #f4faf5, border-left 4px #16a34a

### Visual Placeholders

- `[CHART: TICKER]` for TradingView chart screenshots
- `[SCAN_FUNNEL]` for screening funnel graphic
- `[WINNERS_TABLE]` for portfolio table graphic

---

## Prompt Count Summary

| Post | Prompts | Modes | Est. Time |
|------|---------|-------|-----------|
| Tuesday: new signal deep dive | 3 | Research, Extended, Extended | ~25 min |
| Tuesday: position update | 2 | Research, Extended | ~18 min |
| Tuesday: sector/force/watchlist | 2 | Research, Extended | ~20 min |
| Thursday: methodology | 2 | Extended, Extended | ~15 min |
| Thursday: education | 2 | Research, Extended | ~18 min |
| Thursday: free tool | 2 | Extended, Extended | ~15 min |
| Thursday: investor lessons | 3 | Extended, Research, Extended | ~20 min |
| Ad-hoc: mid-week trade alert | 1 | Extended | ~10 min |
| Ad-hoc: standalone exit | 1 | Extended | ~8 min |
| Fallback: performance review | 2 | Research, Extended | ~15 min |
