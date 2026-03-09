# Sterling Signals — Strategic Intent Document

> **Purpose:** Companion to the System Technical Audit. Explains *what each subsystem is trying to achieve* and *why it exists* in the context of the overarching goal.
> For use in Claude Opus 4.6 extended thinking sessions alongside the technical audit.
> Generated: 2026-03-03

---

## 1. The Overarching Goal

Sterling Signals exists to solve three problems simultaneously:

**Problem 1: Finding multibagger stocks before the crowd.**
Most retail investors discover momentum stocks *after* the move. By the time a stock is on CNBC or trending on FinTwit, the easy 50-100% is gone. We need a systematic way to detect structural momentum shifts *early* — when institutional money is just beginning to accumulate, before the narrative catches up to the price action.

**Problem 2: Filtering signal from noise.**
Technical breakouts alone are not enough. A stock can have perfect momentum and still be uninvestable — bad management, no catalyst, wrong sector, overvalued. We need a multi-layered screening process that starts with 1,817 stocks and ends with 0-3 positions that each have a plausible path to 50-200%+ returns over 3-12 months.

**Problem 3: Building a monetisable audience around that edge.**
A good system with no audience generates returns for one person. A good system with transparent, verifiable results and consistent content generates a subscriber base willing to pay for access. The content system (Substack + X/Twitter) exists to convert our trading edge into a scalable media business.

### The Strategic Loop

```
Better signals → Better results → Better content → Larger audience
     ↑                                                      │
     └──────────── Subscriber revenue funds system ──────────┘
```

Every component in the system serves one or more legs of this loop.

---

## 2. The Scanner — Catching Momentum at the Point of Ignition

### What It's Trying to Achieve

The scanner answers one question: **"Which stocks just experienced a structural shift from bearish/neutral to bullish?"**

It's not looking for cheap stocks. It's not looking for fundamentally strong stocks. It's looking for *momentum ignition* — the precise moment when price structure breaks upward and institutional money starts flowing in. This is the earliest detectable signal that a multi-week or multi-month move may be beginning.

### Why This Matters for Multibaggers

Multibagger stocks (50-200%+ returns) share a common pattern: they spend weeks or months in a base, then experience a structural break where the Hull Moving Average pivots upward and institutional flow indicators confirm. This is not a guarantee — most breakouts fail — but it is a *necessary condition*. You cannot catch a 100% move without first being present at the structural break.

The scanner's job is to ensure we never miss a legitimate structural break in our 1,817-stock universe.

### What the Scanner Proves

When a stock passes the technical gate (HMA pivot low + UC rising or MACD cross-up + price under $25), it proves:

- **Price structure has shifted bullish.** The HMA(21) on the weekly timeframe has formed a new pivot low. This is a structural event, not noise — it means the stock's medium-term trend has reversed from falling to rising.
- **Institutional flow is confirming.** Either the Undercurrent (UC) indicator is rising — meaning buying pressure relative to VWAP is increasing — or the MACD has crossed up, confirming momentum acceleration. One of these must be true; both being true earns higher conviction.
- **The stock is in the sub-$25 universe.** This is a deliberate constraint. We're targeting small and micro-cap stocks where institutional positioning is light and retail attention is low. This is where multibaggers live. Large-caps rarely deliver 100%+ returns in months.

### What the Scanner Does NOT Prove

- Whether the stock is in a good theme (could be in a dying sector)
- Whether the company is investable (could have red flags, no catalyst, bad management)
- Whether the upside justifies the risk (could be fairly valued already)
- Whether the timing is right (market regime might be "risk-off")

These unanswered questions are precisely why the Claude.ai analysis phase exists.

### The Funnel Numbers

Typical Friday scan: 1,817 stocks → ~48 with HMA pivot low → ~16 with both UC/MACD confirmation and price gate → **16 technical buy signals** forwarded to Claude.ai analysis.

The scanner is intentionally loose. It's better to pass 16 signals and reject 13 in analysis than to miss a multibagger because the technical gate was too tight.

---

## 3. The Claude.ai Analysis — The Intellectual Core

### What It's Trying to Achieve

The analysis phase answers the question: **"Of these 16 technically valid signals, which 0-3 stocks represent genuine multibagger opportunities in themes with exceptional 12-month tailwinds?"**

This is where machine signals meet human judgment. The scanner finds *price structure*; the analysis finds *investment merit*. A stock must pass both to enter the portfolio.

### The 8-Prompt Sequence (What Each Achieves)

**Prompt R — Retrospective: "How are our open positions doing?"**

Before looking at new opportunities, we review what we already own. For each open position:
- Is the original thesis still intact?
- Has anything changed in the theme, the company, or the market that weakens the case?
- Should we be looking to exit, or does the position deserve continued patience?

This prevents the common retail mistake of always looking for the next shiny thing while ignoring deteriorating positions.

**Prompt 0 — Market Context: "Is this a market where we should deploy capital?"**

Before evaluating individual stocks, we assess the environment:
- **Market regime**: Risk-on (deploy aggressively), selective (deploy carefully), or risk-off (preserve capital)?
- **Fed/macro trajectory**: Are rates, growth, and liquidity supportive of small-cap momentum?
- **Sector rotation**: Which sectors are accelerating and decelerating? Are institutional flows shifting?
- **Small-cap environment**: Is IWM outperforming or underperforming SPY? Headwind or tailwind?

The market regime directly impacts deployment. In a risk-off regime, even perfect signals may result in zero positions. The system doesn't chase — it waits for alignment.

**Prompt 1 — Thematic Analysis: "What are the best 12-month investment themes?"**

This is where we move from individual stocks to the landscape of opportunity. The analysis identifies the top 5-8 investable themes and classifies each:

- **PRIME**: Highest conviction. Strong catalysts, accelerating flows, wide runway. These themes deserve our largest positions. (Example: AI Infrastructure in early 2025.)
- **INVESTABLE**: Good opportunity but not as clear-cut. Some headwinds mixed with tailwinds. Standard position sizes. (Example: Power Grid Infrastructure.)
- **SELECTIVE**: Uneven. May have one or two good stocks but the theme as a whole is mixed. Small positions only if the individual stock case is exceptional.
- **AVOID**: Structural headwinds, declining flows, or crowded/exhausted. No positions regardless of individual stock quality.

Each theme gets sub-scores for catalyst strength (40% weight), momentum (25%), crowding (20%), and runway (15%), producing a composite score on a 0-10 scale.

**Why themes matter for multibaggers:** A great stock in a bad theme fights gravity. A good stock in a great theme has the wind at its back. Multibaggers almost always emerge from PRIME or early INVESTABLE themes where institutional capital is just beginning to flow. By the time a theme is mature, the easy multiples are gone.

**Prompt 2 — Batch Phase 1 Thematic Screen: "Do these signals belong in the top themes?"**

Now we overlay the 16 technical signals onto the theme map. This answers:
- How many of the 16 signals are in PRIME or INVESTABLE themes?
- How many are orphaned in SELECTIVE or AVOID themes?
- Is there theme clustering (multiple signals in the same sector)?
- Does wave alignment exist (signals aligning with established institutional flows)?

**The critical filter:** A technically perfect signal in an AVOID theme is rejected. The theme must have merit independent of the individual stock. This is what separates our approach from pure momentum trading — we require thematic alignment because themes are what drive the sustained multi-month moves that produce multibagger returns.

Typical result: 16 signals → 4-8 survive the thematic screen.

**Prompt 3 — Batch Phase 2 DD Screening: "Is each surviving stock actually investable?"**

For each stock that passed the thematic screen, we evaluate investability:

- **Catalyst assessment**: Is there a specific event within 90 days that could drive price action? (Earnings, FDA decision, contract announcement, industry catalyst.) A stock without a near-term catalyst can sit in a base for months even with perfect technicals.
- **Red flag detection**: Auditor changes, CFO/CEO departures, SEC investigations, heavy insider selling, accounting restatements, dilution risk. Any of these is an immediate FAIL — these are the stocks that destroy accounts.
- **Variant perception**: What does the market believe, and where is it wrong? The most profitable trades exist where consensus is wrong. If everyone already knows the bull case, the upside is priced in.
- **Conviction scoring (1-10)**: Based on all factors combined. HIGH (8-10) gets full position sizing; STANDARD (7) gets moderate sizing; SPEC (4-6) gets small sizing; NO GO (1-3) is rejected.

**The investability bar is intentionally high.** We'd rather miss a winner than own a stock with hidden red flags. The system's long-term edge comes from avoiding catastrophic losses, not from catching every winner.

Typical result: 4-8 thematically aligned → 1-4 investable.

**Prompt 4 — Newsletter Generation: "Package the analysis for subscribers."**

The weekly newsletter is both a product (what subscribers pay for) and proof of process (transparency builds trust). It includes:
- Market regime assessment
- Theme rankings with thesis summaries
- New signal analysis (buy decisions with full reasoning)
- Open position updates (including losers — transparency is non-negotiable)
- Exit signals and reasoning
- Portfolio performance vs SPY/QQQ benchmarks

**Prompts 5-6 — Deep Dives: "Does this stock have a plausible path to 50-200%?"**

For stocks that survived screening, deep dives answer the ultimate question: what does the math look like?

The 5-phase DD methodology:
1. **Explosive Growth**: Is revenue accelerating? Are margins expanding? Is ROIC exceptional?
2. **Hidden Catalysts**: What does the market not yet appreciate? What's not priced in?
3. **Bear Killer**: What is the strongest bear argument, and why is it wrong?
4. **Valuation Reality**: Using 4 methods (historical multiple, DCF, peer-relative, catalyst-adjusted), what is the stock worth in 12 months?
5. **Synthesis**: Is there a realistic path to 50%+ upside? What probability? What are the key risks?

A stock that survives all 5 phases with a plausible math case for 50%+ upside gets a BUY verdict. A stock where the math doesn't work — even if the technicals and theme are perfect — gets WATCHLIST or NO GO.

**Prompt 7 — Export: "Package all decisions into decisions.json."**

The final prompt structures all analysis into a machine-readable format that the Saturday workflow can merge with technical data. This is where human judgment becomes systematised — conviction scores, position sizes, entry prices, DD fields all flow downstream to power content generation and portfolio tracking.

### Why 16 Signals Routinely Become 0-3 Positions

This is by design, not a bug. The system operates as a multi-stage filter:

```
1,817 stocks → 16 technical signals (scanner)
   16 signals → 4-8 thematically aligned (Prompt 2)
   4-8 aligned → 1-4 investable (Prompt 3)
   1-4 investable → 0-3 with multibagger math (Prompts 5-6)
   0-3 candidates → 0-2 after review gate (Prompt 7)
```

Some weeks, zero stocks survive. This is correct behaviour. The system's job is not to always deploy capital — it's to deploy capital only when the technical setup, thematic alignment, investability, and valuation math all converge. Multibaggers are rare by definition. Forcing positions in weak weeks is how accounts blow up.

**The review gate (Prompt 7)** adds a final sanity check: Did we inflate conviction? Is the bear case adequately addressed? Are we swimming against the market current? Does portfolio construction still make sense with these additions?

---

## 4. The Saturday Merge — Where Machine Meets Human

### What It's Trying to Achieve

The Saturday workflow answers: **"Now that human judgment has validated (or rejected) the machine's signals, update everything downstream."**

### Why the Merge Matters

The scanner produces `signals_technical.json` (pure machine output). The Claude.ai analysis produces `decisions.json` (pure human judgment). Neither is complete alone:

- **Technical signals without analysis** = undifferentiated momentum plays with no investability filter
- **Analysis without technical signals** = opinions without structural confirmation

The merge creates `signals.json` — the authoritative file that all downstream systems read. It combines:
- Machine data: exact prices, indicator values, tier classifications
- Human data: theme assignments, conviction scores, DD fields, catalyst summaries, red flag levels

### Portfolio Construction Philosophy

**Max 6 positions.** Concentration breeds conviction. With 6 positions, each one matters enough to warrant deep analysis. A 20-stock portfolio is a closet index fund with extra fees.

**Tiered sizing based on conviction:**
- T1 (conviction 8-10): 20% of equity. These are the "I've done the work and the math is compelling" positions.
- T2 (conviction 7): 10% of equity. Good setup, good theme, but missing something that prevents full conviction.
- T3 (conviction 4-6): 5% of equity. Speculative — the thesis is interesting but unproven or the position is a catalyst bet.

**10% cash reserve.** Always. This prevents the portfolio from being 100% deployed into a market correction. It also provides capital for mid-week opportunities if an exceptional setup appears.

**The discipline of zero positions.** If the scanner produces 16 signals and the analysis rejects all 16, we deploy nothing. The portfolio sits in existing positions (or cash if flat). This happens more often than you'd think — and it's the single most important edge. The stocks we *don't* buy matter as much as the ones we do.

---

## 5. The Substack System — Content as a Business

### What It's Trying to Achieve

The Substack system answers: **"How do we convert our trading edge into consistent, high-quality content that builds subscriber trust and eventually revenue?"**

### The Content Strategy

**The core insight:** Subscribers don't pay for stock tips. They pay for *a system they trust*. Trust comes from:
1. **Transparency** — Showing every trade, every loss, every stop hit. No cherry-picking.
2. **Consistency** — Publishing daily, not just when things go well.
3. **Education** — Teaching readers why the system works, not just what it bought.
4. **Proof** — Verifiable entry prices, timestamped signals, public receipts.

### Why the Daily Content Schedule Exists

The daily pipeline generates a context document (`daily_context.md`) that contains:
- Today's assigned post category
- The exact prompt to paste into Claude.ai
- All the data that prompt needs (portfolio, signals, themes, market context)

**The genius of this design:** The user spends 5-10 minutes per day. They open the context doc, copy the prompt, paste it into Claude.ai, get back HTML, paste into Substack. That's it. The system did the hard work — deciding what to write about, gathering the data, embedding the prompt.

### The 4 Adaptive Content Categories

The system doesn't follow a rigid "Monday = X, Tuesday = Y" schedule. Instead, it adapts to what's happening:

**Ticker Deep Dive (Tuesday default):** When we have a new buy signal or a portfolio position with a compelling story, we write a deep analysis. This is the highest-value content — it showcases the DD process and gives subscribers actionable information.

**Theme Rotation (Wednesday default):** When themes are shifting, we write about sector flows, emerging trends, and where institutional money is moving. This positions Sterling Signals as a macro-aware system, not just a stock picker.

**Educational (Thursday flex):** When the market is quiet or we have no new signals, we teach. Topics include risk management, momentum principles, portfolio construction, trading psychology. This builds long-term trust and positions the author as a thoughtful practitioner, not a tout.

**Performance Review (Saturday):** The weekly newsletter. Full transparency — every position, every P&L number, every exit. This is the proof layer. Subscribers can verify everything.

**Event overrides:** If a position hits +100% (Hall of Fame) or +50% (Home Run), the scheduled post gets overridden. Milestones are too valuable to waste — they're the strongest proof of the system's effectiveness.

### The Notes Rotation (2-3 Per Day)

Substack Notes are short-form content (like tweets for Substack). They serve a different purpose from posts:
- **PORTFOLIO_PULSE**: Quick winner receipts. "RCAT now +62% from our $8.50 entry." This is social proof that drives subscriptions.
- **SIGNAL_ALERT**: New signals or scan results. Shows the system is actively working.
- **THEME_MOMENTUM**: Quick theme takes. Shows macro awareness.
- **MARKET_REACTION**: Quick market takes on SPY/QQQ moves. Shows we're watching.
- **SYSTEM_PROOF**: Funnel stats — "Scanned 1,817 stocks, found 16 signals, deployed in 1." Shows systematic discipline.
- **LEARNING_NUGGET**: Bite-sized educational content. Builds authority.
- **ENGAGEMENT_HOOK**: Questions to the community. Builds interaction and retention.

The rotation matrix ensures each note type appears 2-3 times per week, preventing repetition while maintaining consistent engagement.

### The Flywheel

```
Good signals → Transparent results → Quality content → Subscriber trust
     ↑                                                          │
     │              Revenue funds system improvements            │
     └──────────────────────────────────────────────────────────┘
```

Each week the system works, it generates more proof. More proof generates better content. Better content generates more subscribers. More subscribers generate revenue. Revenue funds system improvements. The flywheel accelerates.

---

## 6. The Tweet System — The Growth Engine

### What It's Trying to Achieve

The tweet system answers: **"How do we get our content in front of people who don't know we exist yet?"**

Substack is where subscribers live. X/Twitter is where they're *found*. The tweet system is a top-of-funnel growth engine that converts X/Twitter attention into Substack subscribers.

### Why 3 Accounts With Distinct Personas

Each persona reaches a different audience segment:

**@AlexSterlingGBR (The Analyst)** — Primary account. Posts buy/sell signals, receipts, technical analysis. This account builds credibility through verifiable calls. Followers come here for *what to buy* and *proof it works*.

**@Rdobrogowska (The Mentor)** — Educational focus. Posts theme analysis, learning content, Substack teasers. This account builds authority through teaching. Followers come here to *learn how to think* about markets.

**@JamesSterling (The Trader)** — Market commentary, receipts, engagement. This account builds community through personality. Followers come here for *market vibes* and *relatable trading content*.

Three accounts tripling the surface area. A single account posting 10+ tweets/day looks spammy. Three accounts posting 3-4 each looks natural. And each persona attracts a different type of follower, broadening the subscriber funnel.

### Why the 11 Categories Exist

Each category serves a specific function in the attention-to-subscriber pipeline:

**Signal categories (highest value):**
- **SELL_SIGNAL**: Exit alerts. Proves the system has discipline. "We cut VNET at -10% because the structure broke." Followers see that we don't baghold.
- **SIGNAL_ALERT**: New buy signals. Creates FOMO and curiosity. "GREEN Signal: $RCAT at $8.50." Followers want to know *why*.
- **RECEIPT**: Winner showcases. The most powerful category. "Called $RCAT at $8.50, now $13.25 = +55.9%." This is the proof that converts followers into subscribers. People don't subscribe for predictions — they subscribe for *verified results*.

**Market categories (credibility builders):**
- **MARKET_COMMENTARY**: Shows we're paying attention to the broader market, not just our positions. Builds trust as thoughtful market participants.
- **THEME_CATALYST**: Breaking news that affects our themes. Shows real-time awareness and thematic conviction.
- **TRENDING_TAKE**: When FinTwit is buzzing about something that overlaps our holdings. This hijacks existing attention and redirects it toward our content.
- **THEME_LIST**: Thread format listing theme tickers. Provides value and gets shared/bookmarked.

**Position categories (engagement):**
- **TECHNICAL_ANALYSIS**: Key levels and commentary on positions. Shows we actively manage positions, not just buy-and-forget.

**Content categories (funnel):**
- **EDUCATIONAL**: Methodology explainers. Builds authority and gets bookmarked/shared.
- **SUBSTACK_TEASER**: Hooks for today's post. Direct subscriber conversion.
- **ENGAGEMENT**: Community questions, milestones. Builds algorithmic engagement that amplifies future tweets.

### Why Receipts Are the Most Valuable Content

In financial X/Twitter, talk is cheap. Everyone has an opinion. What's rare is *verifiable performance*. A receipt tweet — showing entry price, current price, and P&L — is proof that the system works. It's the single strongest driver of new subscribers because it answers the fundamental question: "Does this person actually make money?"

This is why RECEIPT is Priority 3 in the decision cascade (right after time-sensitive sell/buy signals). Any day we have a position up 5%+, we're showcasing it. Winners are the fuel that powers audience growth.

### The 7-Priority Decision Cascade — Why This Order

The cascade is designed to post the most time-sensitive and highest-value content first:

1. **SELL_SIGNAL first** — Because exits affect subscribers' real money. If someone followed our buy signal, they need to know when to exit. This is a fiduciary responsibility.
2. **SIGNAL_ALERT second** — New buy signals are perishable. The price moves every hour. Getting these out quickly matters.
3. **RECEIPT third** — Winners should be showcased while momentum is hot. A receipt during a big green day gets 10x the engagement of one posted the next morning.
4. **THEME_CATALYST fourth** — Breaking news is perishable but not as critical as trade alerts.
5. **MARKET_COMMENTARY fifth** — Good for maintaining presence but not time-critical.
6. **TRENDING_TAKE/THEME_LIST sixth** — Opportunistic content that rides existing trends.
7. **EDUCATIONAL/ENGAGEMENT seventh** — Evergreen filler for when nothing more urgent exists.

### The Attention Pipeline

```
X/Twitter impression (tweet appears in feed)
  → Tweet read (value demonstrated in 280 chars)
    → Profile visit (bio mentions Sterling Signals)
      → Substack click (link in bio)
        → Free subscriber (reads newsletter)
          → Paid subscriber (trusts the system)
```

Every tweet is optimised for the first step of this pipeline. The 14-step validation ensures nothing goes out that could damage the brand (banned terms, fabricated positions, defeatist language on losses).

---

## 7. How It All Connects — The Complete Strategic Loop

### The Weekly Rhythm

**Friday afternoon:** The scanner fires. 1,817 stocks are evaluated for structural momentum. ~16 pass the technical gate. This is the raw material — the universe of *possible* opportunities.

**Friday evening / Saturday morning:** The human sits with Claude Opus 4.6 and applies judgment to the machine's output. Market regime is assessed. Themes are ranked. Signals are mapped to themes. Investability is evaluated. Deep dives are conducted. The 16 signals are filtered to 0-3 genuine multibagger candidates.

This is the most important hour of the week. It's where the edge is created. The scanner catches the wave; the analysis decides whether to surf it or let it pass.

**Saturday evening:** The Saturday workflow merges human decisions with machine data. The portfolio is updated. Content is prepared. The archive is created. Everything is systematised.

**Sunday-Friday:** The content machine runs. Daily at 07:00 ET, the pipeline generates fresh context, assigns today's post category, embeds the right prompt, and generates notes. The user spends 5-10 minutes turning this into a Substack post. Simultaneously, the live tweet system fires 5-10 times per day across 3 accounts, showcasing results, sharing analysis, and building the audience.

### Why This Design Works for Multibaggers

Multibagger investing requires:
1. **Systematic screening** (scanner) — to never miss a breakout
2. **Deep fundamental analysis** (Claude.ai DD) — to distinguish real opportunities from traps
3. **Thematic conviction** (theme ranking) — to ensure the stock has a tailwind, not a headwind
4. **Disciplined position management** (portfolio system) — to size correctly and exit when wrong
5. **Patience** (the "zero positions" discipline) — to wait for genuine setups instead of forcing mediocre ones

Most retail traders fail because they skip steps 2-5. They see a breakout and buy immediately. Our system adds 4 additional layers of analysis between "technical signal" and "portfolio position." This is why we have a high win rate on deployed capital — we only deploy when everything aligns.

### Why This Design Works for Content

Good content requires:
1. **Real data** (scanner output, portfolio P&L) — not opinions, facts
2. **Consistent publishing** (daily pipeline) — not sporadic when inspired
3. **Variety** (4 categories, 7 note types, 11 tweet categories) — not repetitive
4. **Transparency** (show losses, show stops, show reasoning) — not cherry-picked wins
5. **Proof** (timestamped entries, verifiable results) — not just claims

The system generates all of this automatically. The scanner produces data. The portfolio tracks results. The content pipeline converts data into publishable content. The tweet system amplifies it. The human's only daily input is 5-10 minutes of paste-and-publish.

### The Endgame

As the track record grows and the audience scales:
- **Year 1**: Build the system, prove the edge, grow to 1,000+ subscribers
- **Year 2**: Paid tier launch, premium signals access, deeper DD content
- **Year 3**: Scale to 5,000+ subscribers, potential partnerships, course/book

The system is designed to compound on both axes simultaneously — investment returns compound through the portfolio, audience compounds through consistent content. Each reinforces the other.

---

## Summary: What Each Subsystem Achieves

| Subsystem | Strategic Question It Answers | Output |
|-----------|------------------------------|--------|
| **Scanner** | "Which stocks just broke out structurally?" | 16 technical signals from 1,817 stocks |
| **Claude.ai Analysis** | "Which 0-3 of these are genuine multibagger opportunities?" | decisions.json with conviction-rated positions |
| **Saturday Merge** | "How do we systematise human judgment?" | signals.json + portfolio updates |
| **Daily Content Pipeline** | "What should we publish today and how?" | daily_context.md + 2-3 notes |
| **Substack Posts** | "How do we build subscriber trust?" | 3-4 long-form posts/week |
| **Substack Notes** | "How do we maintain daily engagement?" | 2-3 notes/day |
| **Live Tweet System** | "How do we find new subscribers?" | 5-10 tweets/day across 3 accounts |
| **Portfolio System** | "How do we track and prove our results?" | Transparent P&L, equity curve, benchmarks |

Every component exists to serve the loop: **Find edge → Prove edge → Publish edge → Grow audience → Fund improvements → Find more edge.**
