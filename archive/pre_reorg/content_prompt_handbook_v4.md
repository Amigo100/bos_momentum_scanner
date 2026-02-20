# Sterling Signals — Content Prompt Handbook v4

> **Zero-input content system for Opus 4.6 + Extended Thinking**
> Every prompt is copy-paste-send. No placeholders. No manual editing.
> Attach context document → copy today's prompts → send.
> Last updated: February 2026

---

## How to Use This Handbook

### Daily Workflow (3 steps)

1. Open Claude.ai (Opus 4.6 + extended thinking)
2. Attach the weekly context document (`content_production_guide.md`)
3. Look up today's day → copy the **Post Prompt** and send → then copy the **Notes Prompt** and send

That's it. Every prompt reads the context document to find the right ticker, theme, or data. Every prompt uses web search to refresh stale information. You never need to type a ticker, price, date, or topic.

### Fixed Weekly Schedule

This schedule repeats every week. The context document tells Claude which specific ticker or theme to use for each slot.

| Day | Post | Notes Focus |
|-----|------|-------------|
| **Sunday** | Performance Review (Newsletter) | Community + Journey + Week Ahead |
| **Monday** | Ticker Deep Dive | Market Open + Winner Highlight + Ticker News |
| **Tuesday** | Market Rotations & Themes | Geopolitics/Macro + Theme Spotlight + Engagement |
| **Wednesday** | Key Investor Lessons | Teaching + Portfolio Insight + Community |
| **Thursday** | Portfolio Showcase | Market Midweek + System Update + Ticker News |
| **Friday** | Educational | Week Reflection + Winner Recap + Engagement |
| **Saturday** | No post | Journey + Teaching + Community |

### When to Break the Schedule

Two categories override the fixed schedule when triggered:

- **Trade Alert — Entry**: Use immediately when entering a new position. Replaces that day's scheduled post.
- **Trade Alert — Exit**: Use immediately when closing a position. Replaces that day's scheduled post.

These are the only two prompts that require you to add one word: the ticker symbol. Everything else is automatic.

---

## Sunday — Performance Review

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
2. What Our Scanner Found — The screening funnel from the context document. How many scanned → passed → theme-confirmed → GREEN signals. Include [SCAN_FUNNEL] placeholder. Frame rejection rate as proof of selectivity.
3. Themes Driving Momentum — Top 2-3 themes from the context document. What's hot, cooling, where is capital flowing? Include [THEME_SCORES] placeholder.
4. New GREEN Signals — If new signals exist in the context document: the pitch, theme alignment, why it cleared. Include [CHART: TICKER] for each. If no signals: "Why We Passed" section on disciplined selectivity.
5. Portfolio Performance — Showcase winners from the context document. Performance vs SPY and QQQ using FRESH benchmark data. Alpha generated. Include [WINNERS_TABLE] placeholder.
6. Benchmark Battle — Portfolio return vs SPY YTD vs QQQ YTD. Use fresh data, not the Friday snapshot.
7. Looking Ahead — Use web search to find 3-5 specific catalysts, earnings, or events for next week.
8. Footer — "Subscribe to Sterling Signals for the full weekly analysis: https://sterlingsignals.substack.com"

Output the complete HTML with all styles in a <style> block.

Tone: Confident and direct. Like a weekly briefing from a trusted analyst.
```

### Sunday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

Use web search to check:
- How SPY, QQQ, and IWM performed this past week
- Any notable market news from today or the weekend
- VIX level and sentiment indicators

FRESHNESS CHECK: Verify current prices for any tickers you mention. Do not rely solely on Friday's context document for prices or P&L — update with web search.

Generate 3 Substack Notes for today (Sunday). Apply all marketing and terminology rules from the context document.

NOTE 1 — COMMUNITY & CONNECTION
Write a note inviting connection with other Substack writers and investors. Pull from the context document to identify 3-5 specific topics/themes we cover (e.g. our top-rated themes, small-cap momentum, systematic screening). Frame as: "I write about [specific topics from our portfolio/themes]. Looking to connect with others interested in these areas." Use a numbered list for the topics. End with an invitation to connect or share their work. Keep under 200 words.

NOTE 2 — JOURNEY & MILESTONE
Write a note sharing a genuine milestone or update from the context document. Pull the most impressive number available — portfolio alpha vs SPY, number of weeks publishing, win count, average return, screening rejection rate, or number of positions. Frame as a reflection on the journey of building Sterling Signals. Include 2-3 short observations about what we've learned. End with encouragement or a question for others on a similar path. Keep under 250 words.

NOTE 3 — WEEK AHEAD PREVIEW
Write a note previewing what's coming this week. Use web search to find 2-3 key market events for the coming week (Fed speakers, earnings, economic data). Connect them to our portfolio themes from the context document. Tease upcoming content without giving it all away. End with "What are you watching this week?" Keep under 250 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers (no #, ##, ###)
- NO bullet points (no •, -, *)
- Use short paragraphs, single-line statements, and numbered lists (1. 2. 3.) ONLY when listing items
- $TICKER format with current price or percentage where relevant
- One or two emoji max per note, placed naturally
- End EVERY note with: "Not financial advice. Informational only."

Tone: Genuine, warm, personal. These should feel like a real person sharing their investing journey, not a brand posting content.

Output 3 notes clearly labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Monday — Ticker Deep Dive

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for system context, portfolio data, and all marketing/terminology rules.

TICKER SELECTION: Read the weekly content schedule in the context document. Identify the ticker assigned for Monday (or the first Ticker Deep Dive slot). If no specific ticker is assigned, select the portfolio position with the highest P&L percentage from the "Showcase-Ready Winners" section. If there are no showcase winners, select the highest-gaining position that qualifies (15%+ gain).

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

Write the article as complete HTML using the Editorial theme (specs in Quick Reference).

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

### Monday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- How SPY and QQQ are trading today (Monday morning)
- Any pre-market movers or overnight news
- Breaking news for ANY tickers in our portfolio (check the full portfolio list in the context document)
- VIX level and futures

Generate 3 Substack Notes for today (Monday). Apply all marketing and terminology rules from the context document.

NOTE 1 — MARKET OPEN REACTION
Write a note commenting on today's market open and early moves. Use web search data for specific numbers (SPY, QQQ levels, notable movers). Connect any sector moves to our portfolio themes from the context document. If any of our held tickers are moving significantly today, mention them (following the 15%+ showcase rule). Frame as real-time observation. Keep under 250 words.

NOTE 2 — WINNER HIGHLIGHT
From the context document's "Showcase-Ready Winners" section, select the top performer. Use web search to get its CURRENT price and any recent news about the company. Write a note highlighting this position — why we're in it, what theme it rides, and what's driving the move. Use updated price data, not the Friday snapshot. End with a question: "Anyone else positioned in [theme]?" Keep under 250 words.

NOTE 3 — TICKER NEWS
Use web search to find the most significant recent news (last 48 hours) for any ticker in our portfolio. This could be: earnings announcement, analyst action, partnership, contract win, regulatory development, or sector catalyst. Write a note connecting this news to our thesis for holding the position and to the broader theme. If no significant news exists for any held ticker, search for news related to our top-rated theme from the context document and connect it to our portfolio positioning. Keep under 250 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs and single-line statements only
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: Sharp, informed, real-time. Like an investor reacting to the market with data, not hype.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Tuesday — Market Rotations & Growth Themes

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for system context, portfolio data, theme analysis, and all marketing/terminology rules.

THEME SELECTION: Read the weekly content schedule in the context document. Identify the theme assigned for Tuesday (or the first Market Rotations slot). If no specific theme is assigned, select the highest-rated theme from the "Top Themes" section of the context document.

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

### Tuesday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- Major geopolitical news from today (trade policy, tariffs, sanctions, conflicts, diplomatic developments)
- Any government policy announcements affecting markets (energy policy, defense spending, tech regulation, AI policy)
- Sector ETF performance today
- News related to our top-rated themes from the context document

Generate 3 Substack Notes for today (Tuesday). Apply all marketing and terminology rules from the context document.

NOTE 1 — GEOPOLITICS & MACRO
Write a note connecting today's biggest geopolitical or macroeconomic development to our portfolio positioning. Use web search to find the specific news, then connect it to themes and tickers from the context document. Examples: "Trade tensions with China are escalating — here's how our data center and defense themes are positioned." "New energy policy announcement — this directly impacts our grid infrastructure holdings." Be specific about the news AND the connection to our portfolio. Keep under 250 words.

NOTE 2 — THEME SPOTLIGHT
Select the second-highest-rated theme from the context document (not the one used in today's post). Use web search to find one fresh data point about this theme (ETF flow, earnings beat, policy catalyst, contract announcement). Write a note explaining why this theme matters and how we're positioned. Keep under 250 words.

NOTE 3 — COMMUNITY ENGAGEMENT
Write a note that invites genuine discussion. Pull from the context document to ask a specific, informed question. Examples: "Our scanner screened [X] stocks this week and passed [Y]. What does your process for filtering look like?" or "We're seeing capital rotate into [theme from context doc] — what themes are on your radar?" or "Small-cap momentum has been [description based on IWM data] — are you finding opportunities or staying patient?" The question should demonstrate knowledge while genuinely inviting responses. Keep under 200 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs, single-line statements, numbered lists only when listing items
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: Informed and conversational. Like an investor who reads widely and connects dots.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Wednesday — Key Investor Lessons

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it carefully for portfolio data, themes, and all marketing/terminology rules.

TOPIC SELECTION: No topic is pre-assigned. You will discover one. Use web search and the context document to identify the most timely lesson.

Think through 3-5 candidates from these categories, evaluating each against what's happening in the portfolio and market RIGHT NOW:

EXECUTION: Knowing when to sell vs buy, position sizing, letting winners run, the first loss is the best loss, averaging down trap
ANALYSIS: Technical + fundamental synergy, reading institutional flow, revenue > earnings for small-caps, catalyst vs story, spotting crowded trades
PSYCHOLOGY: FOMO cost, discipline paradox, confirmation bias, best trade you didn't make, compounding effect of avoiding big losses
SYSTEM: Systematic > discretionary, emotion removal, theme alignment value, selectivity as edge

For each candidate, ask: (1) Can I illustrate this with something specific from the context document — a winning position, the scanner's rejection rate, a theme that's working? (2) Is there research data backing this up? (3) Is there a market event this week making this timely?

Select the lesson with the best combination of timeliness, data support, and portfolio illustration.

FRESHNESS CHECK: Use web search to get current prices for any portfolio positions you'll reference. Verify any market data.

RESEARCH: Use web search to find:
- 1-2 academic studies or data points that quantify this lesson
- A specific recent market example
- A counter-example (when does this NOT apply?)

ARTICLE: Write as complete HTML using the Editorial theme (specs in Quick Reference).

Article structure (600-1000 words):
1. The Moment — Open with a vivid scenario every investor recognises
2. The Lesson — State the principle in one sentence
3. The Evidence — Research, data, market history. Specific numbers.
4. How We Apply It — Connect to our system and portfolio using specific examples from the context document
5. The Nuance — When does this break down?
6. The Takeaway — One practical step
7. Engagement Close — Ask a genuine question inviting discussion
8. Footer — "More lessons from the portfolio every week: https://sterlingsignals.substack.com"

Output complete HTML.

Tone: Wise but not preachy. Earned wisdom shared over a drink, not a textbook chapter.
```

### Wednesday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- SPY and QQQ midweek performance
- Any breaking news for tickers in our portfolio
- Notable earnings reports or economic data released today

Generate 3 Substack Notes for today (Wednesday). Apply all marketing and terminology rules from the context document.

NOTE 1 — TEACHING MOMENT
Use web search to find a counterintuitive investing stat or historical pattern that's relevant to current market conditions. Connect it to what's happening this week. Frame as "One stat that changed how I think about [topic]:" followed by the insight and why it matters. Keep under 250 words.

NOTE 2 — PORTFOLIO INSIGHT
From the context document, identify an interesting pattern in our portfolio — theme clustering, sector exposure, how many positions are in the same theme, or how our newest vs oldest positions are performing. Use web search to check current prices for the tickers you'll mention. Write a note sharing this observation and what it tells us about where momentum is flowing. Keep under 250 words.

NOTE 3 — CONNECTION REQUEST
Write a note specifically inviting connection with other Substack writers in adjacent niches. Pull from the context document to list 3-5 specific topics we write about (using our actual themes and focus areas). Model after high-engagement Substack connection posts: direct, warm, with a numbered list of interests and an explicit invitation to connect. Offer to support others who are just starting. Keep under 200 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs, single-line statements, numbered lists only when listing items
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: Thoughtful midweek energy. Reflective but data-grounded.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Thursday — Portfolio Showcase

### Post Prompt

```
I have attached our Sterling Signals weekly context document. Read it thoroughly for portfolio data, theme analysis, and all marketing/terminology rules.

FRESHNESS CHECK: Use web search to get current data for:
- SPY current price and YTD return
- QQQ current price and YTD return
- IWM (Russell 2000) current price and YTD return
- Current prices for ALL showcase-ready winners in the context document — recalculate P&L from entry prices
- Current prices for any other portfolio positions approaching the 15% showcase threshold

Update all performance figures using current prices. If our alpha vs benchmarks has changed, use the updated numbers.

Write a Portfolio Showcase article — a focused, confident piece that demonstrates our systematic, theme-driven approach is generating results.

CRITICAL FRAMING RULES:
- ALWAYS frame performance positively
- During strong periods: showcase absolute returns and alpha
- During flat periods: "capital preservation while being selective" or "the discipline to wait"
- NEVER mention losses, stopped-out positions, or negative P&L
- Compare to S&P 500 (SPY) prominently. Compare to QQQ when it makes us look good.
- Frame winners through thematic lens: "our AI infrastructure theme is up X%"
- Reference screening selectivity as a feature

Think through: What is our strongest metric right now? Lead with that.

Write as complete HTML using the Dashboard theme (specs in Quick Reference).

Article structure (600-1000 words):
1. The Scoreboard — Lead with the single most impressive number
2. What's Working — Group winners by theme. Show thematic approach working.
3. The System in Action — How winners were identified. Screening funnel, theme alignment. Approved terminology only.
4. [WINNERS_TABLE] — placeholder for winners table
5. vs The Benchmarks — Direct comparison with FRESH data. Portfolio vs SPY YTD vs QQQ YTD. State alpha clearly.
6. What We're Watching Next — 1-2 sentences on upcoming catalysts or developing themes from the context document.
7. Footer — "See how our system identifies winners before they move: https://sterlingsignals.substack.com"

Include [CHART: TOP_WINNER_TICKER] placeholder. Output complete HTML.

Tone: Confident, data-forward. Let the numbers speak.
```

### Thursday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- Midweek market action — any notable reversals, sector moves, or sentiment shifts
- Breaking news for any tickers in our portfolio
- News related to our top-rated themes from the context document
- Any notable institutional moves (fund commentary, 13F filings, ETF launches)

Generate 3 Substack Notes for today (Thursday). Apply all marketing and terminology rules from the context document.

NOTE 1 — MIDWEEK MARKET CHECK
Write a note on how the week is shaping up. Use web search for specific data (SPY/QQQ week-to-date, sector leaders/laggards, VIX direction). Connect market action to our portfolio themes from the context document. If any of our themes are outperforming or underperforming, note it. Keep under 250 words.

NOTE 2 — SYSTEM & SCANNER UPDATE
From the context document, pull the scanner's numbers: how many screened, how many passed, rejection rate, how many GREEN signals. Write a note about what our system is seeing this week. Frame selectivity as the edge. If we had zero signals, explain why that's discipline, not failure. If we had signals, build anticipation. Reference the specific themes the system is scoring highest. Keep under 250 words.

NOTE 3 — TICKER NEWS DEEP CUT
Use web search to find news about a specific ticker in our portfolio — ideally NOT the top winner (which was highlighted Monday) but a mid-portfolio position where something interesting is developing. Look for: upcoming earnings, new contracts, analyst coverage initiation, insider buying, sector catalyst. Write a note connecting this development to why we hold the position and our broader theme thesis. Keep under 250 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs, single-line statements, numbered lists only when listing items
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: Sharp and data-focused. Midweek intensity.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Friday — Educational

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

Think through candidates carefully. Select the strongest and explain your choice.

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

### Friday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- SPY and QQQ week-to-date and Friday session performance
- Weekly sector performance leaders and laggards
- End-of-week news wrap for any tickers in our portfolio
- VIX level heading into the weekend

Generate 3 Substack Notes for today (Friday). Apply all marketing and terminology rules from the context document.

NOTE 1 — WEEK IN REVIEW
Write a note summarising the week's market action in 3-4 sentences using web search data. Then connect to how our portfolio and themes performed this week. Use updated prices for any tickers mentioned. Frame as "wrapping up the week" energy. If it was a good week for us, show it. If flat, show discipline. Keep under 250 words.

NOTE 2 — WINNER OF THE WEEK
From the context document, identify the showcase-ready winner that had the best week (use web search to check which of our winners moved most this week specifically, not just total P&L). Write a note celebrating this position — the entry thesis, the theme, and what drove this week's move. Use current price data. End with "What was your best move this week?" Keep under 250 words.

NOTE 3 — WEEKEND ENGAGEMENT
Write a note designed purely for engagement and connection. Choose ONE of these formats based on what feels most natural given the week's context:
a) "Three things I learned this week about [investing/markets/building a newsletter]:" — pull genuine observations from the week's market action and portfolio developments
b) "What I'm reading/researching this weekend:" — tease next week's content themes based on the context document's theme analysis
c) "Question for the community:" — ask something specific and informed, drawn from a real observation in the data (not generic)

Keep under 200 words. Maximise reply potential.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs, single-line statements, numbered lists only when listing items
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: End-of-week reflective energy. Genuine, warm, inviting weekend conversation.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Saturday — Notes Only (No Post)

### Saturday Notes Prompt

```
I have attached our Sterling Signals weekly context document. Read it for portfolio data, themes, system context, and marketing rules.

FRESHNESS CHECK: Use web search to get:
- Any weekend financial news, geopolitical developments, or policy announcements
- Overnight moves in global markets (futures, Asian/European markets if relevant)
- Any weekend news about specific tickers in our portfolio

Generate 3 Substack Notes for today (Saturday). These are weekend notes — lighter tone, more personal, designed for engagement when people are browsing casually. Apply all marketing and terminology rules from the context document.

NOTE 1 — JOURNEY UPDATE
Write a personal note reflecting on where Sterling Signals is in its journey. Pull real numbers from the context document: how many positions we hold, our alpha vs benchmarks, how many weeks we've been publishing, our scanner's selectivity rate. Frame as genuine reflection — what's working, what we're learning, what excites us about next week. Use the "I gained X in Y weeks" milestone format that performs well on Substack. Keep under 250 words.

NOTE 2 — TEACHING MOMENT
Use web search to find an interesting investing insight, historical market fact, or research finding that connects to weekend reading energy. Something someone can learn in 30 seconds. Connect it loosely to our approach or a current market theme from the context document. Keep under 200 words.

NOTE 3 — COMMUNITY BUILDING
Write a note that explicitly invites new connections. List 3-5 specific areas we cover, drawn from the context document's themes and portfolio focus. Use the format: "I'm building [description of Sterling Signals]. I'd love to connect with others who are into: 1. [topic] 2. [topic] 3. [topic]..." End with "Drop your newsletter below" or "I'd love to support anyone else just starting out." This is the highest-engagement note format on Substack. Keep under 200 words.

FORMAT RULES (ALL NOTES):
- NO markdown headers, NO bullet points
- Short paragraphs, single-line statements, numbered lists only when listing items
- $TICKER format with current price or percentage
- One or two emoji max per note
- End EVERY note with: "Not financial advice. Informational only."

Tone: Weekend casual. Personal, warm, community-focused. The most human-sounding notes of the week.

Output 3 notes labelled [NOTE 1], [NOTE 2], [NOTE 3].
```

---

## Trade Alert — Entry (Ad-Hoc)

**Use when entering a new position. Replaces that day's scheduled post. This is the ONLY prompt that requires you to type a ticker.**

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
1. Trade Header — "🟢 NEW GREEN SIGNAL: {TICKER} — [Company Name]" with entry price, date, and theme alignment
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

## Trade Alert — Exit (Ad-Hoc)

**Use when closing a position. Replaces that day's scheduled post. This is the ONLY other prompt requiring a ticker.**

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
   If profitable: "✅ TRADE CLOSED: {TICKER} — +Y% in Z weeks"
   If not profitable: "📋 POSITION UPDATE: {TICKER} — Systematic Exit"
2. The Exit Decision — What changed? (System signal / thesis evolution / headwinds / target achieved)
3. What Changed — Specific details from web search
4. The Lesson — What does this trade teach about our process?
5. What's Next — Capital redeployment or patience?
6. Footer — "See every entry and exit: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder. Output complete HTML.

Tone: Measured, professional. An exit should feel as deliberate as an entry.
```

---

## Quick Reference

### Signal Branding
- ✅ **"GREEN signal"** for buy signals
- ❌ NEVER: TEAL, PASS, VIOLET, AMBER, purple, STRONG BUY, SPEC BUY

### Banned Terms (Never Use in Any Content)
**Indicators:** HMA, Hull Moving Average, RSI, MACD, KDJ, VWAP, Banker, Banker indicator, UC, Undercurrent, BoS, Break of Structure, ExD, Beta >= 1.5
**System internals:** Gatekeeper, Investment Gate, Deep DD, 5-gate, 5th Gate, Gate 1-5, Tier 1/2/3, conviction score, conviction 1-10, theme scoring, profit lock, tiered stop, gear shift, price cap, $25 cap, kill switch, compound exit, STRONG BUY, SPEC BUY, NO GO
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
- **Losses**: NEVER mention

### HTML Theme Specs

**Editorial Theme** (Ticker Deep Dives, Educational, Key Lessons, Trade Alerts)
- Background: `#fafaf8` | Container: `#fff` | Max-width: `680px`
- Headings: `Georgia, 'Times New Roman', serif`
- Body: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif`
- Text: `#1a1a1a` | Muted: `#6b6b6b` | Labels: `#8a7f72`
- Price targets: Bear `#fdf6f4`/`#8b3a1a`, Base `#f4f7fa`/`#1b3a5c`, Bull `#f4faf5`/`#2e5e3e`
- Table header: `#2c2520` text `#f0ebe4` | Alt rows: `#faf9f7`
- Callout: border-left 3px solid `#3d5a80`, bg `#f4f7fa`

**Dashboard Theme** (Market Rotations, Performance Review, Portfolio Showcase)
- Dark background: `#111827` | Card bg: `#1F2937` | Max-width: `680px`
- Accent: teal `#2DD4BF` | Green: `#22C55E` | Amber: `#FBBF24`
- Text: `#F9FAFB` | Muted: `#9CA3AF` | Dim: `#6B7280`
- Borders: `#374151`
- Font: system sans-serif throughout
- Header bg: `#0F172A`
- Teal bg (highlights): `#0D3B34`

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
| **Community & Connection** | ✓ | | ✓ | ✓ | | | ✓ | 4 |
| **Journey & Milestones** | ✓ | | | | | | ✓ | 2 |
| **Market Macro & Geopolitics** | | ✓ | ✓ | | ✓ | | | 3 |
| **Ticker News** | | ✓ | | | ✓ | | | 2 |
| **Winner Highlight** | | ✓ | | | | ✓ | | 2 |
| **Theme Spotlight** | | | ✓ | | | | | 1 |
| **System & Scanner Insight** | | | | | ✓ | | | 1 |
| **Teaching & Wisdom** | | | | ✓ | | | ✓ | 2 |
| **Portfolio Insight** | | | | ✓ | | | | 1 |
| **Week Preview / Review** | ✓ | | | | | ✓ | | 2 |
| **Weekend Engagement** | | | | | | ✓ | | 1 |

**21 notes per week** across 7 days. Each day covers different tickers and themes — Monday's winner highlight and ticker news must feature different tickers than Thursday's and Friday's.

---

## v4 Change Log

| Change | Rationale |
|--------|-----------|
| **Fixed weekly schedule for posts AND notes** | Same pattern every week — no decision fatigue. Sunday=Review, Monday=Deep Dive, Tuesday=Themes, Wednesday=Lessons, Thursday=Showcase, Friday=Educational, Saturday=Notes only. Trade Alerts override when triggered. |
| **Zero placeholders (except Trade Alerts)** | Every prompt reads the context document and auto-selects the appropriate ticker, theme, or topic. Deep Dive selects top winner or new signal. Themes selects highest-scored theme. Educational and Lessons discover their own topics. No `{TICKER}`, `{THEME}`, `{TOPIC}`, `{DAY}`, or `{WEEK}` to fill in. Trade Alerts are the only exception — they require the ticker symbol. |
| **Day-specific notes prompts (7 prompts, not 1)** | Each day has its own prompt with 3 defined note types tailored to that day's energy (Monday=sharp market open, Friday=reflective wrap, Saturday=personal/community). Ensures variety across the week without repeated types on consecutive days. |
| **Ticker News notes added** | Web-searches for breaking news on portfolio holdings and comments on developments. Shows active monitoring. Appears Monday and Thursday covering different tickers each time. |
| **Market Macro & Geopolitics notes added** | Searches for market-moving geopolitical/macro news and connects to our themes and holdings. Appears Monday (market open), Tuesday (geopolitics focus), and Thursday (midweek check). |
| **Winner Highlight notes added** | Showcases specific 15%+ winners with updated prices and thematic framing. Appears Monday (top winner) and Friday (best weekly mover). |
| **Journey & Milestone notes pull from context doc** | No manual milestone input needed. Notes extract portfolio alpha, win count, screening stats, weeks publishing, and other metrics directly from the context document. |
| **FRESHNESS CHECK in every prompt** | Every post and notes prompt starts with explicit web search instructions to update prices, recalculate P&L, and find today's news. A Friday context document used on Thursday still produces accurate content. |
| **Saturday notes-only day added** | Lighter weekend presence (no post) with 3 personal/community-focused notes. Keeps engagement going 7 days/week without requiring a full article on Saturday. |
| **Notes reduced from 4 to 3 per day** | Cleaner execution and less repetition risk. 21 notes/week across 7 days still provides strong growth engine. |
| **Portfolio Showcase moved to Thursday** | Midweek showcase with updated prices bridges the gap between Tuesday's theme piece and Friday's educational. Natural "proof point" placement. |
| **Deduplication built into notes** | Monday's ticker news and winner must feature different tickers than Thursday's and Friday's. Tuesday's theme spotlight covers a different theme than Thursday's system update. |
