# Sterling Signals — Weekly Prompt Kits: 2026-W12

> Planned: Sunday March 15, 2026
> Posts: 4 (Sun Portfolio Spotlight, Tue Sector Watch, Wed Investor Lessons, Thu Tools & Tech carousel)
> Visual assets: 3 (Sun diagram, Tue carousel, Thu carousel)
> Notes: 20 across the week

---

## PORTFOLIO CONTEXT (paste at the start of EVERY claude.ai chat)

```
PORTFOLIO SNAPSHOT (live prices as of March 14, 2026):

$SOFI: entry $7.90, current $17.76 (+124.8%), theme: Financial Technology
$EVTL: entry $4.50, current $3.82 (-15.1%), theme: Drone Tech
$NVDA: entry $150.00, current $180.25 (+20.2%), theme: AI Chip Manufacturer
$AMD: entry $120.00, current $193.39 (+61.2%), theme: Semiconductors
$TMDX: entry $65.00, current $123.48 (+90.0%), theme: Organ Transplantation
$ASPI: entry $6.00, current $5.68 (-5.3%), theme: Nuclear Fuel
$HIVE: entry $2.10, current $2.05 (-2.4%), theme: Crypto Miner and Datacentres
$BAND: entry $16.55, current $15.23 (-8.0%), theme: AI Voice CPaaS Infrastructure

Portfolio return: +32.6% | SPY YTD: +0.6% | QQQ YTD: -1.1% | Alpha vs SPY: +32.0%
Open positions: 8 | Winners: 4 (SOFI, NVDA, AMD, TMDX) | Underwater: 4 (EVTL, ASPI, HIVE, BAND)
Best: SOFI +124.8% | VIX: 27.19

MARKET CONTEXT (week of March 16-21, 2026):
- FOMC rate decision + dot plot + press conference — Wed March 18 (hold expected at 3.50-3.75%, 92%+ probability)
- Iran conflict ongoing — VIX elevated at 27.19, oil above $90 WTI
- S&P 500 on 4-day losing streak, near 200-day SMA
- Micron, Nike, FedEx earnings this week
- EVTL earnings March 24
- Powell term expires May 23 — Warsh leading replacement candidate

SCANNER: 1,279 tickers scanned → 11 technical signals → 1 buy signal (BAND, already entered)
Top themes: AI Voice CPaaS (7.6 PRIME), BizAv Connectivity (7.65 PRIME), PFAS/Methane (7.2 INVESTABLE)
No sell signals. No exit signals.
```

---

## NOTES SCHEDULE (full week)

| Day | 08:30 (Morning) | 12:30 (Midday) | 17:00 (Evening) |
|-----|-----------------|-----------------|-------------------|
| **Sunday 3/15** | SIGNAL_TRACKING (tease SOFI thesis) | COMPANION_NOTE (Portfolio Spotlight) | PORTFOLIO_UPDATE |
| **Monday 3/16** | MARKET_SNAPSHOT (FOMC preview, VIX) | SIGNAL_TRACKING (BAND update) | PORTFOLIO_UPDATE |
| **Tuesday 3/17** | SECTOR_FLOW (BizAv ETF flows) | COMPANION_NOTE (Sector Watch) | CATALYST_WATCH (FOMC tomorrow) |
| **Wednesday 3/18** | CATALYST_WATCH (FOMC day) | COMPANION_NOTE (Investor Lessons) | DATA_INSIGHT (equity curve) |
| **Thursday 3/19** | SIGNAL_TRACKING (post-FOMC reaction) | COMPANION_NOTE (Tools & Tech carousel) | READER_QUESTION |
| **Friday 3/20** | PORTFOLIO_UPDATE (week-end snapshot) | ALPHA_SCOREBOARD (vs SPY/QQQ) | WINNER_RECEIPT (SOFI +125%) |
| **Saturday 3/21** | ALPHA_SCOREBOARD (newsletter tease) | COMPANION_NOTE (newsletter) | — |

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUNDAY March 15 — Portfolio Spotlight: $SOFI — +125% in 3 Weeks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH IN CLAUDE.AI:
- content_prompt_handbook_v7_0.md
- banned_terms.py
- portfolio.csv
- signals.json

PROMPT 1 OF 3 — RESEARCH:

**MODE: Research mode ON**

```
No new signals this week. We're refreshing the thesis on our best performer.

TICKER: $SOFI
Entry: $7.90 | Current: $17.76 | P&L: +124.8% in 21 days
Theme: Financial Technology

Research question: "Is the thesis that drove our entry still intact? What's
changed since we entered, and does the risk/reward still favour holding?"

RESEARCH TASK 1 — FINANCIAL BASELINE

Search specifically for:

A) SEC EDGAR — most recent 10-Q or 10-K filing for $SOFI:
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
   - SoFiUSD stablecoin partnership with Mastercard — details, launch timeline
   - CEO Anthony Noto's $1M open-market share purchase — date, price, shares

C) Institutional ownership:
   - Latest 13F filings mentioning $SOFI
   - Net institutional buying or selling ($ amount, last quarter)
   - 2-3 notable funds that entered or exited (name + position size)
   - Short interest % of float — current vs 3 months ago

D) Recent catalysts (last 30 days):
   - FDA decisions, regulatory rulings, contracts
   - Analyst upgrades/downgrades — firm, old PT, new PT
   - Insider buying/selling — name, title, shares, $ (Form 4)
   - Partnerships, acquisitions, product launches

RESEARCH TASK 2 — FORWARD REVENUE BUILD (next 12 months)

For EACH revenue segment (Lending, Technology Platform, Financial Services):
- Known contracts/backlog with $ values and delivery dates
- Pipeline items with probability weights
- Pricing trends: ASP, ARPU, contract values — direction + evidence
- TAM and SAM with penetration rate
- Headwinds: competition, regulation, funding dependency

Build LOW / MID / HIGH per segment. Cite every assumption.

Additional focus for thesis refresh:
- What's changed since entry? (new contracts, earnings, regulatory)
- Has institutional ownership increased or decreased since our entry?
- Any new risks that didn't exist at entry?
- Forward revenue build: has the trajectory improved or weakened?

OUTPUT: Structured tables with citations. Flag gaps. Do NOT write yet.
```

PROMPT 2 OF 3 — ANALYSIS:

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

ANALYSIS TASK 4 — THESIS REVIEW

Compare current state to entry thesis:
- What we expected at entry vs what actually happened
- Has conviction increased, decreased, or held?
- Updated exit trigger (has it changed?)
- Should we add to this position, hold, or begin trimming?

Be honest. If the thesis is weakening, say so.

OUTPUT: Tables with working. Do NOT write yet.
```

PROMPT 3 OF 3 — ARTICLE + COMPANION NOTE:

**MODE: Standard**

```
Write the Portfolio Spotlight article and companion note.

TITLE: "Portfolio Spotlight: $SOFI — +125% in 3 Weeks. Are We Still Holding?"

Read the attached banned_terms.py. Do NOT use any banned terms.

═══ ARTICLE (1,000-1,500 words) ═══

White-background Editorial theme (680px, inline CSS).
- Background: #ffffff | Max-width: 680px | Padding: 40px 24px
- Headings: Georgia, serif | #1a1a1a | h1: 28px, h2: 22px, h3: 18px
- Body: system sans-serif | 16px | line-height 1.7 | #2d2d2d
- Tables: #f8f7f5 header, #fafaf8 alt rows, #e8e4df borders
- Positive: #2e5e3e | Negative: #a04030
- Stat cards: inline-block #f8f7f5, 28px bold number, 12px label

STRUCTURE:
1. THE HOOK — "$SOFI at $17.76, up +125% from our $7.90 entry
   21 days ago." Why is this worth a deep look right now?

2. THE ORIGINAL THESIS — What we saw at entry. Why we entered.

3. WHAT'S CHANGED — New data since entry. Earnings, contracts, institutional
   moves. Be specific — table of what we expected vs what happened.

4. THE NUMBERS — Updated financials. HTML table with quarterly data.

5. UPDATED PRICE TARGETS — Refreshed bear/base/bull with new data.
   Three colour-coded cards:
   - Bear (red-tinted, #fdf6f4): price, probability %, driving assumption
   - Base (blue-tinted, #f4f7fa): price, probability %, driving assumption
   - Bull (green-tinted, #f4faf5): price, probability %, driving assumption

6. BEAR CASE — What could go wrong from HERE (not from entry).

7. OUR DECISION — Hold, add, or trim? Exit trigger update.

8. FOOTER — "Every entry and exit documented weekly: https://sterlingsignals.substack.com"

[CHART: SOFI] placeholder after section 3 or 4.

═══ QUALITY CHECK ═══
- Does section 3 contain a specific comparison table?
- Does section 4 have an HTML table with quarterly numbers?
- Does section 5 use specific numbers from your analysis?
- Is the article 1,000-1,500 words?

═══ COMPANION NOTE (150-280 words) ═══

"$SOFI: +125% in 21 days. Is the thesis still intact?"
ONE updated finding. Don't reveal the hold/add/trim decision — make them read.

⛔ ANTI-SPOILER: Max ONE price target (base case). Never bear/base/bull together.

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: The energy of genuine curiosity about whether a big winner still has legs. Decisive, not tentative.
```

VISUAL PROMPT (separate claude.ai chat):

Files to attach: animated-diagram-spec.md, aspi-v7.html (reference), banned_terms.py

```
Create an animated business model diagram for $SOFI (SoFi Technologies).
Canvas: 1280 x 720px, dark background #111318.

SOFI revenue engine with these interconnected boxes:
1. LENDING (blue, #3b82f6): Personal loans, student loans, home loans. KPI: Lending revenue $X (from research)
2. FINANCIAL SERVICES (green, #22c55e): SoFi Money, Invest, Relay, Credit Card. KPI: FS revenue $X, member count
3. TECHNOLOGY PLATFORM (purple, #a855f7): Galileo + Technisys — banking-as-a-service for 150M+ accounts. KPI: Tech platform revenue $X
4. SOFIUSD STABLECOIN (amber, #f59e0b): Mastercard partnership, digital payments. KPI: Launch timeline
5. MEMBER FLYWHEEL (pink, #ec4899): Cross-sell from 1 product → 3+ products. KPI: Products per member, member growth rate

Connections:
- Lending → Member Flywheel (members acquired via lending)
- Financial Services ← Member Flywheel (cross-sell destination)
- Technology Platform → Financial Services (powers the backend)
- SoFiUSD → Financial Services (new product within ecosystem)
- Member Flywheel → Lending (returning members refinance)

CSS animations: boxes fade in sequentially, connections draw as animated dashes, KPI numbers count up.

Every KPI must be a specific number from SOFI's most recent financials.
Use only inline CSS. Self-contained HTML file.
```

SAVE TO:
- Post: substack/output/current/posts/portfolio_spotlight_20260315.html
- Companion note: substack/output/current/notes/midday_companion_note_20260315.html
- Diagram: substack/output/current/diagrams/diagram_sofi_20260315.html

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TUESDAY March 17 — Sector Watch: BizAv Connectivity (7.65/10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH IN CLAUDE.AI:
- content_prompt_handbook_v7_0.md
- banned_terms.py
- signals.json

PROMPT 1 OF 2 — RESEARCH & VALIDATE:

**MODE: Research mode ON**

```
You are researching the BizAv Connectivity Upgrade (5G + LEO) sector (7.65/10) for a Sector Watch article. Produce structured research data — NOT an article.

CONTEXT:
- Theme score: 7.65/10 (PRIME classification from this week's screening)
- Our positions in this theme: None currently (GOGO is on our watchlist at $5.23, T2)
- This theme scored highest PRIME in our screening — dominant market position + 5G catalyst + military expansion

RESEARCH TASK 1 — ETF FLOWS
Search for:
- The 3-5 largest ETFs covering business aviation, aerospace connectivity, or satellite communications by AUM (name them)
- Monthly net inflows/outflows for each in dollars (last 3 months)
- Any record flow months in the last 6 months
- Compare to broad market flows (SPY, QQQ inflows in same period)

RESEARCH TASK 2 — INSTITUTIONAL POSITIONING
Search for:
- Recent 13F filings from major funds mentioning GOGO, ASTS, VSAT, or other BizAv connectivity stocks
- Name 2-3 specific funds and their positions (fund, ticker, shares, change)
- Is hedge fund concentration in this sector rising or falling vs 12 months ago?
- Any activist positions or notable new entrants
- GOGO insider buying: CEO $1.4M, Chairman $907K — verify and get dates

RESEARCH TASK 3 — POLICY & REGULATORY CATALYSTS
Search for:
- FAA or FCC rulings on in-flight 5G connectivity
- DoD contracts for military aircraft connectivity (C-130, other platforms)
- Textron OEM line-fit agreements — status and timeline
- Starlink Aviation competitive moves — pricing, fleet count, service quality
- International regulatory approvals for Galileo 5G system

RESEARCH TASK 4 — EARNINGS EVIDENCE
- GOGO most recent quarterly results: revenue, EBITDA, subscriber count, ARPU
- 5G Galileo development timeline — first service revenue expected when?
- Competitor comparison: GOGO vs Starlink Aviation vs Viasat vs SmartSky

RESEARCH TASK 5 — OUR WATCHLIST POSITION
For GOGO (watchlist):
- Current price $5.23, T2 signal
- Scanner verdict: WATCHLIST (GOOD FIT for theme)
- Key concern from scan: $909M debt at SOFR+6%, flat 2026 guidance
- What would make this graduate from watchlist to entry?

RESEARCH TASK 6 — RISKS
- Debt overhang: $909M at SOFR+6% — what does this mean at current rates?
- Starlink competition: is Starlink actually threatening BizAv specifically?
- Valuation: is GOGO expensive or cheap relative to the 5G launch catalyst?
- What specific event would make you SELL the theme?

OUTPUT: Structured research with citations. No article yet.
```

PROMPT 2 OF 2 — ARTICLE + COMPANION NOTE:

**MODE: Standard**

```
Write the article and companion note using your research.

TITLE: "Sector Watch: BizAv Connectivity (7.65/10)"

Read the attached banned_terms.py. Do NOT use any banned terms.

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme with teal accents:
- Theme score card: teal (#0d9488) left border, #f0fdfa background
- Data callouts: rounded cards, #f8fafc background, #e2e8f0 border
- Background: #ffffff | Max-width: 680px | Padding: 40px 24px
- Headings: Georgia, serif | #1a1a1a
- Body: system sans-serif | 16px | line-height 1.7 | #2d2d2d

Open with: "BizAv Connectivity scored 7.65/10 in this week's screening — our highest-rated theme."

STRUCTURE:
1. Why This Theme, Why Now — The strongest data point from your research. Not a summary — one number that commands attention. 5G is coming to private jets, and one company owns the install base.
2. The Investment Thesis — GOGO's dominant market share + 5G Galileo transition + military expansion. Multi-year story.
3. The Evidence — ETF flows, institutional moves, insider buying ($1.4M CEO + $907K Chairman), earnings, catalysts. NUMBERS from your research. Include at least one stat card or callout box.
4. Our Positions — We don't hold GOGO yet — explain why (watchlist, debt concern, flat guidance). "We're watching but haven't found a setup that clears all gates."
5. Risks — Debt at SOFR+6%, Starlink competition, execution risk on Galileo timeline. Be specific.
6. What We're Watching — 5G first service revenue, Textron line-fit, military C-130 ramp. Specific dates.
7. Stocks Positioned — GOGO, ASTS, VSAT, and 2-3 others in this theme with current price and one-line thesis each.
8. Footer — "We score themes weekly across 1,800 stocks: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 3 cite specific dollar amounts for ETF flows? Not just "money is flowing in."
- Does section 4 explain honestly why we haven't entered?
- Does section 6 list dates, not just "upcoming catalysts"?

═══ COMPANION NOTE (150-280 words) ═══

Lead with the most compelling data point:
- "GOGO's CEO bought $1.4M of stock. The Chairman added another $907K. When insiders bet their own money..." or
- "One company connects 75%+ of North American business jets. In 6 months, they're upgrading every one of them to 5G."

Don't summarise the article. Give ONE data point that makes a reader want the full picture.

End with: "Full sector analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Opinionated. "Capital is flowing into connectivity. The data is clear." Contractions. No filler.
```

VISUAL PROMPT (separate claude.ai chat):

Files to attach: carousel-guide.docx, carousel-series-templates.md, banned_terms.py

```
Create a 5-slide MACRO PULSE carousel on BizAv Connectivity.

Slide 1 (DARK): "BizAv Connectivity — When Every Private Jet Gets 5G"
  Hook stat: "One company connects 75%+ of North American business jets. They're about to upgrade all of them."

Slide 2 (LIGHT): The thesis in plain English. 2-3 short paragraphs.
  GOGO dominates BizAv connectivity. Galileo 5G launches mid-2026. Military contracts expanding.

Slide 3 (LIGHT): 4 stat cards with real data:
  - GOGO BizAv market share (%)
  - CEO insider buying ($1.4M)
  - 5G launch timeline (mid-2026)
  - Debt/EBITDA ratio

Slide 4 (LIGHT): Competitive landscape comparison:
  GOGO vs Starlink Aviation vs Viasat — market focus, technology, pricing

Slide 5 (DARK): "What We're Watching" — 3-4 dated catalysts.
  Sterling Signals verdict: "On our watchlist. Waiting for the debt picture to improve."

Output the JSON following the carousel data schema.
```

SAVE TO:
- Post: substack/output/current/posts/sector_watch_20260317.html
- Companion note: substack/output/current/notes/midday_companion_note_20260317.html
- Carousel: substack/output/current/carousels/carousel_bizav_connectivity_20260317.pptx

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEDNESDAY March 18 — Investor Lessons: The Dot Plot Decoded
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH IN CLAUDE.AI:
- content_prompt_handbook_v7_0.md
- banned_terms.py

PROMPT 1 OF 3 — DISCOVER TOPIC:

**MODE: Extended Thinking**

```
Today is an Investor Lessons post. Subcategory: market_mechanics.

The FOMC meets TODAY (March 18, 2026). Rate decision at 2pm ET, press conference at 2:30pm. Hold expected (92%+ probability). But this meeting includes the dot plot and updated economic projections — the first to incorporate Iran conflict, $90+ oil, and Trump's 15% tariffs.

Generate 3 topic candidates. For EACH:
- The topic stated as a specific, surprising claim (not generic)
- The hook stat — one number that would make someone stop scrolling
- What makes this timely? (Why this week)
- Shareability: would someone repost this? What's the quotable insight?

My top recommendation: "How the Fed Dot Plot Moves Markets — And What Most Investors Miss"
- Most retail investors don't understand the dot plot or how to trade it
- FOMC day is literally today — peak relevance
- Natural connection to our portfolio: rate expectations directly affect growth stock valuations (our SOFI at +125%, our semiconductor positions)

But generate 2 alternatives in case you find something better:
- Alternative A: A market mechanics topic around VIX / volatility (VIX at 27.19, elevated)
- Alternative B: A market mechanics topic around oil price shocks and sector rotation

Recommend your top choice. Explain why it beats the alternatives.
```

PROMPT 2 OF 3 — RESEARCH:

**MODE: Research mode ON**

```
Research the Fed Dot Plot and how it moves markets.

SEARCH FOR:

A) The original source:
   - How the dot plot works: 19 FOMC members, each projects year-end rate
   - History: When was it introduced? (2012). Why?
   - The most dramatic dot plot shifts and what happened to markets after
   - Specific examples: Dec 2023 pivot (3 cuts signaled → market rallied X%), Sep 2024 shift, March 2025 revision

B) Specific numbers that make the story compelling:
   - Average S&P 500 move on FOMC days with dot plot vs without
   - How far the dot plot median has been from where rates actually end up (accuracy track record)
   - The "dot plot tantrum" of 2013 — what happened
   - Today's market expectations: CME FedWatch probabilities for June, September cuts

C) Counter-evidence:
   - When has following the dot plot led investors astray?
   - Is the dot plot actually predictive? What does academic research say?
   - Fed Chair Powell's own caveats about dot plots

D) One stat that contradicts common wisdom:
   - The counterintuitive finding that hooks the article
   - Example: "The dot plot has been wrong X% of the time" or "Markets move more on the PRESS CONFERENCE than the dots"

E) OPTIONAL — Portfolio connection:
   - How do rate expectations affect fintech (SOFI), semiconductors (AMD, NVDA), and growth stocks in our portfolio?
   - If rate cuts are delayed, what does that mean for our positions?
   - Natural connection through how interest rate expectations affect multiple expansion/compression for growth stocks

OUTPUT: Structured research with citations. No article yet.
```

PROMPT 3 OF 3 — WRITE:

**MODE: Standard**

```
Write the article and companion note.

TITLE: "Investor Lessons: The Dot Plot Decoded — How 19 Dots Move Trillions"

Read the attached banned_terms.py. Do NOT use any banned terms.

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme (680px, inline CSS).
- Background: #ffffff | Max-width: 680px | Padding: 40px 24px
- Headings: Georgia, serif | #1a1a1a
- Body: system sans-serif | 16px | line-height 1.7 | #2d2d2d

STRUCTURE:
1. THE HOOK — Most surprising number about dot plot accuracy or market impact.
   "The Fed meets today. 19 people will place 19 dots on a chart. Last time they did this, [X happened]."
2. THE STORY — What the dot plot is, told as a story. When it was created, why, the first time it moved markets dramatically. Narrative, not bullet points.
3. THE EVIDENCE — Studies, data, specific numbers with citations. How often the dot plot has been right. Average market move on dot plot days. Include a table or data comparison.
4. [OPTIONAL] IN OUR PORTFOLIO — If natural: how rate expectations affect fintech and semiconductor valuations. SOFI as a rate-sensitive fintech, AMD/NVDA as growth stocks. Only include if it flows naturally — DO NOT force this.
5. THE EXCEPTION — When does following the dot plot fail? The 2013 tantrum. The 2024 overestimation. Specific counter-example.
6. THE TAKEAWAY — One concrete thing the reader can do TODAY when the dot plot drops at 2pm ET. How to read it. What to watch for. Not "be careful" — a specific action.
7. FOOTER — "We study the best to build a better system: https://sterlingsignals.substack.com"

═══ QUALITY CHECK ═══
- Does section 2 tell a STORY (narrative) not just list facts?
- Does section 3 cite at least one source with a specific number?
- If section 4 exists, is the portfolio connection genuine or forced? If forced, DELETE it.

═══ COMPANION NOTE (150-280 words) ═══

Lead with the hook stat. Create curiosity around FOMC day.
"The Fed meets in [X] hours. 19 dots will move trillions. Most investors don't know how to read them."

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Enthusiasm backed by evidence. Not professorial. Not clickbait. The energy of "I'm going to show you something most people miss."
```

SAVE TO:
- Post: substack/output/current/posts/investor_lessons_20260318.html
- Companion note: substack/output/current/notes/midday_companion_note_20260318.html

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THURSDAY March 19 — Tools & Tech: Koyfin — Bloomberg Alternative
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH IN CLAUDE.AI:
- carousel-guide.docx
- carousel-series-templates.md
- banned_terms.py

PROMPT 1 OF 1 — RESEARCH + CAROUSEL DATA:

**MODE: Research mode ON**

```
Research Koyfin for a Tools & Tech carousel. Demo on $TMDX (TransMedics Group).

CONTEXT: TMDX is in our portfolio at entry $65.00, current $123.48 (+90.0%). Theme: Organ Transplantation. We want to show how Koyfin reveals the fundamental story behind this performer.

SEARCH FOR:
- Koyfin official site, pricing tiers (free, Plus, Pro), limitations of free tier
- What problem it solves: Bloomberg-quality financial data visualization for retail investors
- Specific workflow on $TMDX:
  - Revenue growth chart (quarterly, show acceleration)
  - Margin expansion visualization
  - Peer comparison (TMDX vs ISRG, DXCM, PODD — medical device peers)
  - Institutional ownership tracking over time
  - Financial statement waterfall view
- 2-3 alternatives: Macrotrends, Simply Wall St, Tikr Terminal — how does Koyfin compare?
- Limitations and gotchas: what's missing vs paid Bloomberg/FactSet?

Then generate carousel data JSON for a 5-slide INVESTOR TOOLKIT carousel:

Slide 1 (DARK): "Koyfin — The Bloomberg Alternative That's Actually Free"
  Hook stat: "Bloomberg costs $25,000/year. Koyfin does 80% of the job for $0."

Slide 2 (LIGHT): What Koyfin does in plain English. 2-3 short paragraphs.
  Financial data visualization, screening, charting, peer comparison — all in one platform.

Slide 3 (LIGHT): 4 stat cards showing what Koyfin found on $TMDX.
  Each card: number + label + source. Real data from your research.
  Examples: Revenue growth %, margin expansion, institutional ownership change, peer valuation comparison

Slide 4 (LIGHT): Two-column comparison:
  "KOYFIN FREE" vs "KOYFIN PLUS ($25/mo)" OR comparison with Macrotrends (free) and Simply Wall St ($10/mo)

Slide 5 (DARK): 3-4 numbered setup steps.
  1. Go to koyfin.com, create free account
  2. Search TMDX → Dashboard
  3. Click "Financials" → Quarterly Revenue → spot the acceleration
  4. Click "Comps" → add ISRG, DXCM → see relative valuation

  Sterling Signals verdict: "We use Koyfin for peer comparisons and margin tracking. Free tier covers 90% of what we need."

Output the JSON following the carousel data schema.
Also output a brief companion note (100-150 words) for posting alongside
the carousel in Substack Notes.

Companion note hook: "I ran $TMDX through Koyfin. It showed me [one specific insight from the data]. Free."
```

SAVE TO:
- Carousel JSON: substack/output/current/carousels/carousel_koyfin_20260319.json
- Carousel PPTX (after running generator): substack/output/current/carousels/carousel_koyfin_20260319.pptx
- Companion note: substack/output/current/notes/midday_companion_note_20260319.html

---

## PRODUCTION CHECKLIST

### Sunday Evening Batch Session (~75 min total)

| Order | Chat | Content | Time |
|-------|------|---------|------|
| 1 | Chat 1 | Sunday Portfolio Spotlight: SOFI (3 prompts) | ~20 min |
| 2 | Chat 2 | Tuesday Sector Watch: BizAv (2 prompts) | ~12 min |
| 3 | Chat 3 | Wednesday Investor Lessons: Dot Plot (3 prompts) | ~18 min |
| 4 | Chat 4 | Thursday Tools & Tech: Koyfin carousel (1 prompt) | ~8 min |
| 5 | Chat 5 | Sunday diagram: SOFI (1 prompt) | ~10 min |
| 6 | Chat 6 | Tuesday carousel: BizAv (1 prompt) | ~7 min |

### After Production

```bash
# Export Sunday diagram to MP4
python3 substack/tools/capture.py substack/output/current/diagrams/diagram_sofi_20260315.html --duration 10 --fps 24 --format mp4

# Generate Thursday carousel PPTX
node substack/tools/carousel-generator.js substack/output/current/carousels/carousel_koyfin_20260319.json

# Generate Tuesday carousel PPTX
node substack/tools/carousel-generator.js substack/output/current/carousels/carousel_bizav_connectivity_20260317.json

# Git push all content
git add substack/output/current/
git commit -m "W12 content: SOFI spotlight, BizAv sector watch, dot plot lessons, Koyfin carousel"
git push origin master
```

---

## WEEK SUMMARY

| Day | Post | Visual | Notes |
|-----|------|--------|-------|
| **Sun 3/15** | Portfolio Spotlight: $SOFI (+125%) | Animated diagram (SOFI) | 3 |
| **Mon 3/16** | — | — | 3 |
| **Tue 3/17** | Sector Watch: BizAv Connectivity (7.65/10) | Carousel (MACRO PULSE) | 3 |
| **Wed 3/18** | Investor Lessons: Dot Plot Decoded (FOMC day) | — | 3 |
| **Thu 3/19** | Tools & Tech: Koyfin (carousel Note) | Carousel (INVESTOR TOOLKIT) | 3 |
| **Fri 3/20** | — | — | 3 |
| **Sat 3/21** | — (newsletter from analysis session) | — | 2 |

**Totals:** 4 posts + 3 visual assets + 20 notes planned
