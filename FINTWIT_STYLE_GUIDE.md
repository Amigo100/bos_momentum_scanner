# Sterling Signals — FinTwit Style Guide

> **Purpose:** This document defines the tweet style, content patterns, and quality standards for Sterling Signals based on analysis of high-performing FinTwit accounts. Use this as the authoritative reference when generating, validating, or reviewing tweet content.

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Tweet Categories](#tweet-categories)
3. [Style Rules](#style-rules)
4. [Banned Phrases](#banned-phrases)
5. [Power Phrases](#power-phrases)
6. [Content Structure Patterns](#content-structure-patterns)
7. [Tone Guidelines](#tone-guidelines)
8. [Image & Chart Requirements](#image--chart-requirements)
9. [Validation Checklist](#validation-checklist)
10. [Implementation Notes](#implementation-notes)

---

## Core Philosophy

### Every Tweet Must Deliver Value

The accounts we're emulating never post vague content — every single tweet contains at least one of:
- A specific ticker with a price
- A percentage gain (receipt)
- A technical level with clear meaning
- A theme with multiple named stocks

### Winners Only

These accounts never dwell on losses. They celebrate wins, show receipts, and move on. Losers are mentioned only when explaining why a setup was invalidated (educational), never to complain.

### Specificity Breeds Credibility

"$AMPX at $12.44 cleared all gates" beats "scanner found 2 signals" every time.

### Receipts Culture

FinTwit rewards accountability. Reference past calls, show entry prices, display percentage gains. "Trust me bro" doesn't work — "I called $ONDS at $0.83, now at $11.61" does.

---

## Category Name Alignment

This style guide uses descriptive category names. The codebase uses a different taxonomy. When generating tweets programmatically, use the code category names. When reading examples in this guide, map them via this table:

| This Guide's Name | Code Category | Notes |
|---|---|---|
| SCANNER_RESULT | `SIGNAL_ALERT` | Use SIGNAL_ALERT in all code and prompts |
| THEME_ANALYSIS | `THEME_LIST` / `THEME_CATALYST` | THEME_LIST for ticker lists with prices, THEME_CATALYST for breaking news |
| PERFORMANCE (Receipts) | `RECEIPT` | Use RECEIPT in all code and prompts |
| WATCHLIST | `SIGNAL_ALERT` (sub_type: watching) | Merged into SIGNAL_ALERT with "watching" sub-type |
| TECHNICAL_ANALYSIS | `TECHNICAL_ANALYSIS` | Same name — no change |
| EDUCATIONAL | `EDUCATIONAL` | Same name — no change |
| MARKET_COMMENTARY | `MARKET_COMMENTARY` | Same name — no change |
| ENGAGEMENT | `ENGAGEMENT` | Same name — no change |
| NEWSLETTER_CTA | `SUBSTACK_TEASER` | Use SUBSTACK_TEASER in all code and prompts |

---

## Persona Tweet Structures

Three accounts post tweets with structurally different voices. A reader following all three should never suspect they share an author. These are not suggestions — they are hard structural constraints.

### variant_1 — Alex / The System

**Pattern:** `$TICKER at $PRICE. [One data point]. [Thesis in ≤5 words].`

**Rules:**
- ALWAYS lead with ticker and price
- Maximum 3 sentences. Most tweets should be 2.
- Never start with a question or observation
- Never use "here's why" or "this matters because"
- No exclamation marks. No emoji.
- End with thesis in 5 words or fewer: "Thesis intact." "Watching resistance." "NFA."

**Tone:** Bloomberg terminal. Cold, precise, data-forward. Numbers are the argument.

**Good:**
- `$NGNE at $24.25. +18.3% from $20.50 entry. Rett catalyst June.`
- `1,817 scanned. 5 cleared. $RCAT and $INOD survived all gates.`
- `$ETON holding $18.45. HC Wainwright PT $37. Rare disease thesis validating.`

**Bad:**
- `Really excited about $NGNE's performance! Up 18%!` (excited, exclamation marks)
- `Here's why gene therapy is the future...` (starts with "here's why")
- `The system is working perfectly.` (no ticker, no price, no data)

### variant_2 — Rozalia / The Mentor

**Pattern:** `[Question or insight]. [Explanation]. [$TICKER evidence].`

**Rules:**
- ALWAYS open with a question, observation, or "Did you know" hook
- NEVER lead with a ticker — tickers appear mid-tweet as evidence
- 3-4 sentences. Teaching rhythm: hook → explain → evidence → takeaway.
- Uses "here's why", "this matters because", "the lesson here"
- Ends with a principle, not a ticker

**Tone:** Smart friend at dinner explaining something. Warm, approachable. Uses contractions.

**Good:**
- `Why do 99.7% of stocks fail our screen? Because we're not looking for good stocks. We're looking for institutional money + structural momentum confirming. $NGNE was one of 5 that cleared.`
- `Most traders panic when VIX hits 25. Here's what actually happens to conviction plays in volatility — they hold relative strength. $ETON +2.9% while SPY bleeds.`
- `Position sizing lesson from this week: $RELY pulled back 5%. Uncomfortable? Yes. Account-threatening? Not even close. That's the difference.`

**Bad:**
- `$NGNE at $24.25. Thesis intact.` (leads with ticker — that's Alex's pattern)
- `Gene therapy names running.` (no question, no explanation, no teaching)

### variant_3 — James / The Trader

**Pattern:** `[Fragment]\n[Fragment]\n[Fragment]\n[CTA]`

**Rules:**
- Short fragments, NOT full sentences
- ALWAYS uses line breaks between thoughts
- Maximum 4 lines, each under 60 characters
- Uses "watching", "eyes on", "NFA", "DYOR"
- Sounds like a trader posting from their phone between trades
- CAN use exclamation marks sparingly. CAN use ONE emoji per tweet.
- NEVER explains WHY — just states WHAT and WHAT NEXT

**Tone:** Trading Discord energy. Casual, street-level, high-energy.

**Good:**
- `$NGNE breaking out.\nEntry $20.50. Now $24.25.\nRett data mid-2026.\nNFA 🎯`
- `SPY red. Our names green.\n$ETON holding. $NGNE climbing.\nRelative strength > everything.`
- `Copper at record highs.\n$FCX $60.41\n$SCCO $184.30\nSave this list.`

**Bad:**
- `$NGNE is performing well because the gene therapy thesis is validating with FDA's new framework for rare disease approvals.` (full paragraph — that's Rozalia's territory)
- `Thesis intact. Structural pivot confirmed.` (analyst language — that's Alex)

---

## Tweet Categories

### 1. SCANNER_RESULT → Code: `SIGNAL_ALERT`

**Purpose:** Announce new buy signals from the scanner with specific tickers and prices.

**Required Elements:**
- ✅ At least one $TICKER
- ✅ Entry price for each ticker
- ✅ Brief thesis or theme context
- ✅ Funnel stats optional but powerful (X scanned → Y survived)
- ✅ Chart attachment reference

**Real Examples:**

```
$AREC breaking weekly resistance and it's game on... strong institutional accumulation confirmed.
```

```
One proper swing can change your life.

Just these past few days, we nailed:

$SATL +50.43%
$IBRX +40.07%
$NUAI +61.93%
$RDW +13.30%
$SIDU +18.41%
$TE +12.11%

Imagine compounding every single week.

This upcoming week will be turbulent.

I'll be closely watching:

$ZETA at $21.75
$HIMS at $29.62
$ONDS at $12.17
$LPTH at $12.44
$LAES at $4.92
$RR at $4.13
$SATL at $5.25

And a few more.

There'll always be great buying opportunities.

I'll share them as they come...
```

```
$ZETA just triggered a GREEN signal.

It can be invalidated still, so the safe play is to wait until we close today.

Broke clean through the support zone.

Bottom may be in...
```

```
New daily momentum confirmation on $HIMS.

Same boat as $ZETA, the signal can be invalidated. Safe play is to wait for today's candle to close.

For those with even less risk tolerance, wait for the weekly structural pivot to appear.

Will update you guys when it does!
```

**Anti-patterns (NEVER do this):**
- ❌ "Scanner found 2 survivors this week. Quality over quantity."
- ❌ "Two signals made it through the gates."
- ❌ "The system found some interesting setups."

---

### 2. THEME_ANALYSIS → Code: `THEME_LIST` / `THEME_CATALYST`

**Purpose:** Highlight a hot sector/theme with multiple tickers and prices.

**Required Elements:**
- ✅ Theme name clearly stated
- ✅ 3+ tickers with current prices
- ✅ Brief context on why the theme is moving
- ✅ Often includes "save this post" hook

**Real Examples:**

```
If you missed Gold and Silver...

The Copper bull run might be next:

$TMQ at $6.21
$TGB at $7.63
$IE at $19.86
$HBM at $24.97
$ERO at $32.84
$CPER at $36.52
$FCX at $60.41
$BHP at $67.52
$RIO at $90.43
$SCCO at $184.30

Probably want to save this post!
```

```
Rare Earth stocks ranked by market cap:

$AREC at $4.37 ~ 443.09M
$IDR at $46.68 ~ 727.85M
$NB at $7.70 ~ 919.08M
$TMQ at $6.21 ~ 1.06B
$UAMY at $10.85 ~ 1.52B
$CRML at $20.62 ~ 2.43B
$USAR at $24.77 ~ 3.66B
$TMC at $9.44 ~ 3.90B
$PPTA at $34.50 ~ 4.20B
$UUUU at $25.50 ~ 6.05B
$MP at $69.58 ~ 12.33B

Guess which one's my favorite...
```

```
I've made multi-millions investing in themes.

AI, Space, Defense, the list goes on.

One theme that's been catching momentum lately is copper. Keep an eye on:

$ERO +110% from signals.
$FCX +42% from signals.
$SCCO +79% from signals.
$TMQ +18% from signals.

Will share potential entries soon...
```

```
Copper is the next Silver.

I might be wrong on some of these tickers so I just bought $COPX...

Revisit this post soonish. NFA!
```

```
This year, these 3 themes will rally hard:

Space: $ASTS $PL $RDW $RKLB $SATL
Defense: $OSS $LPTH $ONDS $LUNR
AI & Robotics: $IREN $CIFR $RR $ZETA $TE

Save these tickers and thank me later.
```

**Anti-patterns (NEVER do this):**
- ❌ "AI infrastructure theme keeps delivering."
- ❌ "Copper looking interesting. Will share more soon."
- ❌ "The rare earth space is heating up."

---

### 3. PERFORMANCE → Code: `RECEIPT`

**Purpose:** Show gains on past calls with specific entry → current prices and percentages.

**Required Elements:**
- ✅ $TICKER with entry price
- ✅ Current price or exit price
- ✅ Percentage gain (always positive framing)
- ✅ Optional: days held, reference to original call

**Real Examples:**

```
We beat the market again this week.

In the past 4 days alone, we nailed...

$IBRX +40.07%
$NUAI +61.93%
$RDW +13.30%
$SATL +50.43%
$SIDU +18.41%
$SLS +14.52%
$TE +12.11%
$USAR +45.96%

Meanwhile... S&P 500 -0.63%
```

```
You don't get rich by missing half the run.

You get rich by riding momentum.

$SATL daily momentum confirmation came in at $2. It's now sitting at $5.25 - a solid 2x for those who followed.

Just like when I caught $ONDS at $0.83.

Don't miss the next 5-10x trade I share.
```

```
A few of my largest trades in 2025:

$ONDS from $0.83 to $11.61
$NUAI from $1.85 to $6.88
$OPEN from $0.58 to $9.79
$CIFR from $3.01 to $24.69
$IREN from $6.30 to $72.23

A ton of my followers made millions.
```

```
$USAR up 86% from our initial GREEN signals.

The U.S planning to invest $1.6B (for 10% equity) is extremely bullish.

When both technical and fundamental analysis looks good, it's a pretty safe bet.
```

```
Happy ~100% to those who celebrate!

$SATL what a crazy week!

Just added this to the "hall of fame" trades...
```

```
$BITF from $2.05 to $6.40.

Lost on $CAN.

Win more than you lose, that's the name of the game. Can't win every trade.
```

**Anti-patterns (NEVER do this):**
- ❌ "Portfolio check: 3 green, 1 red. The red? $INTC. Still bleeding..."
- ❌ "System keeps working. Trust the process."
- ❌ "We're beating the market" (without specific receipts)

---

### 4. WATCHLIST → Code: `SIGNAL_ALERT` (sub_type: watching)

**Purpose:** Share stocks being monitored that aren't yet signals, with prices and what's needed to trigger.

**Required Elements:**
- ✅ $TICKER with current price
- ✅ What's missing for a full signal OR what level to watch
- ✅ Clear "watching" or "on radar" framing

**Real Examples:**

```
Here's what I'm watching next week:

$IREN at $56.68
$LPTH at $12.44
$MNTS at $8.04
$ONDS at $12.17
$PALL at $184.74
$RZLT at $3.52
$SATL at $5.25
$UAMY at $10.85

And tomorrow, I share 1 more ticker.
```

```
I'll be closely watching:

$ZETA at $21.75
$HIMS at $29.62
$ONDS at $12.17
$LPTH at $12.44
$LAES at $4.92
$RR at $4.13
$SATL at $5.25

There'll always be great buying opportunities.

I'll share them as they come...
```

```
$BITF not seeing GREEN signals yet, but it refuses to break below the support zone.

Interestingly, momentum indicators turned bullish... which often precedes GREEN signals.

Will update if I see anything!
```

```
$RZLV no GREEN signals yet.

Will update the moment I see any!
```

```
No new GREEN signals on $HIMS yet, but seems like the bottom is near.

Safest entry is to wait for a new signal - will update you guys when I start a new position.
```

**Anti-patterns (NEVER do this):**
- ❌ "$PUMP on watchlist" (no price, no context)
- ❌ "A few stocks looking interesting" (no names)
- ❌ "Watching some setups" (completely useless)

---

### 5. TECHNICAL_ANALYSIS

**Purpose:** Share specific technical levels, support/resistance, and what happens if broken.

**Required Elements:**
- ✅ $TICKER
- ✅ Specific price level
- ✅ What happens if level holds or breaks
- ✅ Chart image attached

**Real Examples:**

```
$SATL approaching psychological resistance levels around $5-5.50.

Once we resistance breakout, which we're very well on track to do, we're shooting towards $8-10.
```

```
$TMQ I wouldn't get shaken out at 4H support zone, green, and weekly resistance support.

Looks just like $SATL yesterday...

Easy invalidation on a close below $5.95.
```

```
$TMQ same as 2 days ago, at $5.95.

Break below and setup is invalidated.

Hold it and good to go.
```

```
$UAMY I noticed that it breached silver resistance on Friday, which is why I'm extremely bullish this week.

The structural pivot confirmation called this rally since the $4 region...

Always know your levels!
```

```
$ONDS continues to hold at the daily support zone I highlighted last week.

Exit signals usually mean a trip down to support, which we already got.

Bears are wrong unless this breaks.

Important inflection point... watching!
```

```
$LAC probably ready to take out silver resistance this week and proceed higher from here IMO...
```

```
$CLSK this is why our support zone is so powerful... basically every ticker respects it... on every timeframe.

Perfect rejection on the first attempt.
Successful break on the second.
And now turned it into support.

Will keep updating...
```

```
$LPTH it's easy to get nervous on red days, but so far it's just a support retest.

Just like the previous 2 times...

Important week loading.
```

```
Still looking for that Weekly close above $5.50 on $SATL.

Psychological resistance is real. Once past, it should soar.
```

```
A lot of tickers, including $OSS 4H, are sitting at their support zone levels.

I think FOMC turbulence next week will provide us with a clear direction.
```

```
$COPX sometimes I like to experience anxiety by looking at the 5 min chart.

About to breach support zone...
```

```
$COPX nice bounce off hourly support!

Every ticker has its own support zone level, and thus setup invalidation.
```

**Key Phrases for Technical Posts:**
- "Break above $X = game on"
- "Break below $X = setup invalidated"
- "Easy invalidation on a close below"
- "Bears are wrong unless this breaks"
- "Don't get shaken out at support"
- "Strong institutional accumulation"
- "Important inflection point"
- "Psychological resistance"
- "Just a support retest"

---

### 6. EDUCATIONAL

**Purpose:** Explain methodology, indicators, or why a trade worked — always with specific examples.

**Required Elements:**
- ✅ Concrete example (ticker, price, outcome)
- ✅ Clear lesson or principle
- ✅ Actionable insight

**Real Examples:**

```
GREEN signals are buy signals.
Exit signals are sell signals.

You can set alerts for GREEN or exit signals on TradingView, for any ticker or an entire watchlist, on any timeframe.

The more confirmations across the board, the stronger the signal.
```

```
Buy GREEN. Sell on exit signal. Repeat forever.
```

```
Like they say in Pokémon, there's a time and place for everything...

Being able to identify themes at their inflection points is one of my strengths.

All the previous breakout attempts looked convincing, but ultimately failed.
```

```
$CRML has strong weekly institutional accumulation, with a "fresh" break of the silver.

At $18.46 I noticed that it breached weekly resistance... I never ignore tickers that clear the next resistance right away.

Pay attention to Rare Earths IMO...
```

```
For those worried about $ONDS, zoom out.

Short term turbulence does not negate long-term conviction & value.

Weekly looks less over-extended than before. Daily chart (not shown) held support.

Could be a solid opportunity to catch some of these dips.
```

```
Trade the theme that you have.

Not the theme that you want...

I think 2026 will be a stock picker's market... very important to choose wisely IMO.
```

```
$SATL only green space ticker today.

My biggest lesson is that only a few themes "work" at any given time...

Thousands of themes to choose from.

Just because "alligator safari" is a theme, doesn't mean it has to be bullish.
```

```
GREEN signals don't expire until the next exit signal, especially if there's minimal resistance above.
```

```
RSI can stay overbought for longer than people think, but of course can be a rollercoaster.
```

**Anti-patterns (NEVER do this):**
- ❌ "Systematic beats emotional every time." (no example)
- ❌ "Trust the process." (meaningless)
- ❌ "The system keeps working." (prove it)

---

### 7. MARKET_COMMENTARY

**Purpose:** React to market conditions, connect to opportunities.

**Required Elements:**
- ✅ Market context
- ✅ How it affects our positions/themes
- ✅ Opportunity or action item

**Real Examples:**

```
For those waiting on healthy pullbacks for an entry, today could be a good opportunity.

Discounted prices all around.

When in doubt, zoom out. Pick tickers that look good on a Weekly or Monthly timeframe.

Thank me later.
```

```
$SATL showing strength on a red day... you know what this means.

Even then, probably best you go spend time outside today & touch some grass.
```

```
Copper is still green but unfortunately looks like apocalypse everywhere else.

Ready to buy the dip on our favorite themes though... will keep watching!
```

```
$SATL stock picker's market.

Green while indices are red...

Just make sure to set alerts for exit signals etc. on 4H/1D/1W IMO!
```

```
We're going to have an opportunistic week.

Perfect buying zones for new entries, or for those wanting to add to their positions.

Play this week right and you'll be set.

Will do my best to share what I do.
```

```
COPPER ALL TIME HIGHS!

New trade today. Stay tuned.
```

```
Silver $SLV weekly update.

GREEN signals don't expire until the next exit signal... will update if I see one.

I haven't made a single bearish post on metals since December.

Just respecting momentum...
```

```
$SLV Silver new all time highs.

Will update when I do see a weekly exit signal... but wouldn't try to short this.
```

```
The global #Copper shortage could easily take it to $10 and beyond.

I've been calling it the "next" Silver.

Might want to save this post...
```

---

### 8. ENGAGEMENT

**Purpose:** Build community, respond to milestones, create conversation hooks.

**Required Elements:**
- ✅ Can be ticker-light but should still reference trading/system
- ✅ Often includes call-to-action or hook for future content
- ✅ Celebrates community wins

**Real Examples:**

```
Thank you for 75K!

We strive to build the world's most accurate, beautiful, and easy trading indicators.

I'll chart EVERY ticker in the comments this weekend, with 10+ hearts.
```

```
Congratulations! It pays to pay attention.
```

```
Let's keep printing!
```

```
One proper swing can change your life.

Imagine compounding every single week.
```

```
A few proper swings can change your life.

Don't be afraid to add to winners...
```

```
This weekend, I chart EVERYTHING.

Stocks that are "just" flipping bullish.
Stocks that are "just" flipping bearish.

Important to bear in mind that FOMC is next week, so let's look at the charts.
```

```
The trial begins... $SATL.

Are you watching?
```

```
Will $COPX be one of the best performing ETFs in 2026?
```

```
Copper bull run loading IMO...

Strong weekly institutional accumulation and basically thin air (no resistance) above.

Bulls maxed out in the fourth pane.

Guess what happens next?
```

```
Throwback to when $ONDS was $1.48.
```

---

### 9. NEWSLETTER_CTA → Code: `SUBSTACK_TEASER`

**Purpose:** Drive traffic to newsletter/Discord with value-first framing.

**Required Elements:**
- ✅ Lead with value (what they'll get)
- ✅ Reference specific content or analysis
- ✅ Include link

**Real Examples:**

```
Don't miss the next 5-10x trade I share.
```

```
Remember, the Discord gets more trade alerts & additional bullish setups!
```

```
Will always share here! Discord gets more trade alerts & new bullish setups.
```

---

## Live Tweet Categories

These categories are used by the **live tweet system** (`live_tweet_generator.py`) to produce real-time, context-aware tweets during market hours. Each category has specific required elements and a distinct purpose.

### MARKET_REACTION
**Purpose:** React to real-time market moves, news, or sentiment shifts affecting portfolio or watched tickers.
**Required Elements:** $TICKER, price movement, context (why it's moving)
**Chart:** Not required (speed > charts for reactions)

**Good Examples:**
```
$LUMN ripping +8% on infrastructure spending headlines.

This is what happens when smart money front-runs the bill. Entry was $6.72.
```
```
SPY selling off but $STRL holding green.

Relative strength in infrastructure names telling you everything you need to know right now.
```

**Anti-Patterns:**
- ❌ "Markets are moving today" (no specifics)
- ❌ Reacting to moves older than 4 hours (stale context)
- ❌ Including internal terms like "BoS" or "HMA pivot"

---

### RECEIPT
**Purpose:** Show receipts on winning trades — entry price vs current/high price with % gain.
**Required Elements:** $TICKER, entry price, current price, % gain
**Chart:** Required (attach chart showing the move)

**Good Examples:**
```
$RCAT from $8.50 entry → $13.25 high.

+55.9% on the drone play. System found it, discipline held it. NFA
```
```
$IBKR entry $65.00, now $72.93.

+12.2% and the structure is still bullish. No reason to cut winners short.
```

**Anti-Patterns:**
- ❌ Showing positions under 25% gain with entry prices (entry price display rules)
- ❌ "We called it" (sounds like a tout)
- ❌ Fabricating prices not in portfolio data

---

### SIGNAL_ALERT
**Purpose:** Announce new or recent scanner signals — fresh entries from the system.
**Required Elements:** $TICKER, entry price
**Chart:** Required (attach weekly chart)

**Good Examples:**
```
🟢 New signal: $MOD at $72.15

Infrastructure play cleared all 5 gates. Institutional Accumulation Divergence confirmed. Adding to portfolio.
```
```
🟢 $AMSC flagged at $32.40

Structural Pivot Confirmation + Sector Flow alignment in the grid modernization theme. Watching for follow-through.
```

**Anti-Patterns:**
- ❌ "Our scanner found this" (never reference the scanner publicly)
- ❌ Using "gatekeeper", "tier 1", or "conviction 5"
- ❌ Signalling tickers not in the actual signals data

---

### DIP_OPPORTUNITY
**Purpose:** Frame market dips as buying opportunities for portfolio names or watched tickers.
**Required Elements:** Context (why it's a dip), $TICKER, opportunity framing
**Chart:** Not required

**Good Examples:**
```
Market pulling back -1.2% but $APLD and $BITF barely flinching.

Crypto mining names showing relative strength in the dip. These are the ones institutions are accumulating.
```
```
$SOFI -3% on sector rotation, not fundamentals.

When quality names dip on macro noise, that's when the system earns its keep. Watching for Structural Pivot Confirmation.
```

**Anti-Patterns:**
- ❌ "Buy the dip!" without specific tickers or context
- ❌ Calling bottoms with certainty
- ❌ Mentioning any position that is currently at a loss

---

### THEME_MOMENTUM
**Purpose:** Highlight theme breakouts with multiple tickers showing simultaneous strength.
**Required Elements:** Theme name, 3+ $TICKERs with prices
**Chart:** Not required (multi-ticker text format works well)

**Good Examples:**
```
Copper theme on fire today:

$WCC $185.20 (+3.1%)
$FCX $52.40 (+2.8%)
$SCCO $98.15 (+2.4%)

Sector Flow Analysis says this rotation has legs. Infrastructure spending is the tailwind.
```
```
AI infrastructure names all moving together:

$NVDA, $AMD, $APLD, $AMSC

When 4+ names in the same theme break out simultaneously, that's not coincidence — that's institutional rotation.
```

**Anti-Patterns:**
- ❌ Listing fewer than 3 tickers (not enough for a "theme" tweet)
- ❌ "Theme scoring" or "PRIME classification" (internal terms)
- ❌ Mixing tickers from unrelated themes

---

## Style Rules

### ALWAYS DO:

| Rule | Good Example | Bad Example |
|------|--------------|-------------|
| Lead with $TICKER and price | "$AMPX at $12.44" | "One of our signals" |
| List multiple tickers when discussing themes | "$ERO, $FCX, $SCCO, $TMQ" | "Copper stocks" |
| Show receipts with entry → current | "$ONDS from $0.83 to $11.61" | "$ONDS is up big" |
| Give specific levels | "Break above $13 = game on" | "Watching for a breakout" |
| Use charts/images frequently | (attach chart) | (text only) |
| Quote your own past calls | (quote tweet original) | "As I mentioned before" |
| Include hooks for engagement | "Probably want to save this post" | (no CTA) |
| Show funnel/scan stats | "1,817 scanned → 2 survived" | "Several stocks passed" |

### NEVER DO:

| Rule | Bad Example | Why It Fails |
|------|-------------|--------------|
| Vague theme talk without tickers | "AI infrastructure theme keeps delivering" | No actionable value |
| Reference signal counts without naming them | "2 signals this week" | Frustrating, looks fake |
| Focus on losers or red positions | "The red? $INTC. Still bleeding..." | Depressing, no value |
| Generic motivation without proof | "Trust the process" | Empty, no receipts |
| Cliffhangers without value | "Big news coming soon..." | Annoying, no substance |
| Dwelling on missed opportunities | "Should have bought more" | Negative energy |

---

## Banned Phrases

These phrases are explicitly forbidden — they indicate vague, low-value content:

```python
BANNED_PHRASES = [
    # Vague system references
    "theme keeps delivering",
    "system keeps working", 
    "trust the process",
    "systematic beats emotional",
    "quality over quantity",
    
    # Unnamed references
    "2 signals",
    "2 survivors", 
    "the scanner found",
    "some interesting setups",
    "a few tickers",
    
    # Generic filler
    "picks and shovels",  # unless followed by specific tickers
    "big if true",
    
    # Loser focus
    "still bleeding",
    "dragging down",
    "the red one",
    "stubborn loser",
    "debate the exit",
    "unfortunate loss",
    
    # Empty promises
    "big news coming",
    "stay tuned for something special",
    "you won't believe",
]
```

---

## Power Phrases

These phrases appear frequently in high-performing FinTwit posts:

### Hooks & CTAs
| Phrase | Context |
|--------|---------|
| "Probably want to save this post" | After theme/ticker lists |
| "Save these tickers and thank me later" | After theme lists |
| "Revisit this post soonish" | After predictions |
| "Will update when I see..." | After watchlist or analysis |
| "Will share potential entries soon" | After theme setup |
| "Don't miss the next 10x" | After performance recap |
| "Stay tuned" | After market context |
| "I'll share them as they come" | After watchlist |

### Technical Calls
| Phrase | Context |
|--------|---------|
| "Break above $X = game on" | Resistance level |
| "Break below $X = setup invalidated" | Support level |
| "Easy invalidation on a close below" | Clear risk management |
| "Bears are wrong unless this breaks" | Bullish bias with exit |
| "Don't get shaken out at support" | Encouraging hold |
| "Strong institutional accumulation" | Strong signal |
| "Important inflection point" | Key level approaching |
| "Psychological resistance" | Round number levels |
| "Just a support retest" | Normal pullback |

### Receipts & Proof
| Phrase | Context |
|--------|---------|
| "Happy [X]% to those who celebrate" | Milestone reached |
| "It pays to pay attention" | After winner |
| "Let's keep printing" | Community engagement |
| "A ton of followers made millions" | Social proof |
| "For those who followed" | Inclusive receipt |
| "What a crazy week" | Big move |

### Confidence Builders
| Phrase | Context |
|--------|---------|
| "One proper swing can change your life" | Motivational hook |
| "Imagine compounding every single week" | Vision casting |
| "Generational buying opportunities" | Dip framing |
| "Just make sure to set alerts" | Actionable advice |
| "Don't be afraid to add to winners" | Position sizing |

### Framing Devices
| Phrase | Context |
|--------|---------|
| "If you missed [X]... [Y] might be next" | Theme transition |
| "Trade the theme that you have, not the theme that you want" | Discipline |
| "When both technical and fundamental looks good, it's a pretty safe bet" | Confluence |
| "Win more than you lose, that's the name of the game" | Risk management |
| "Maybe I'm right. Maybe I'm wrong. NFA!" | Humble confidence |

---

## Content Structure Patterns

### Pattern 1: Theme → Ticker List
```
[Theme statement]

[Ticker list with prices, 5-10 items]

[Hook/CTA]
```

### Pattern 2: Signal Announcement
```
$TICKER at $PRICE [— context]

[Brief thesis, 1-2 lines]

[Chart attached / Will update]
```

### Pattern 3: Performance Receipt
```
[Time frame or milestone]

[Ticker list with % gains]

[Comparison to benchmark]

[What's next / CTA]
```

### Pattern 4: Technical Update
```
$TICKER [technical observation]

[Specific level and what it means]

[Invalidation criteria]

[Chart attached]
```

### Pattern 5: Watchlist
```
[Context for why watching]

[Ticker list with prices]

[What you're waiting for]

[Promise to update]
```

### Pattern 6: Quote Tweet Receipt
```
[Quote own past call]

[Current status with numbers]

[Lesson or next step]
```

### Pattern 7: Dip Commentary
```
[Market observation]

[Why it's opportunity not fear]

[Action to take / themes to watch]
```

---

## Tone Guidelines

### Voice Characteristics

| Trait | Do This | Not This |
|-------|---------|----------|
| **Confident but humble** | "I think copper goes crazy. NFA!" | "I'm definitely right" |
| **Data-driven** | Always back claims with numbers | Vague assertions |
| **Action-oriented** | What to watch, what to do | Just observations |
| **Community-focused** | "For those who followed" | "I made money" |
| **Transparent** | "Maybe I'm right. Maybe I'm wrong." | False certainty |

### Sentence Style
- Short, punchy sentences
- Line breaks between thoughts
- Numbers and tickers stand alone on lines
- Minimal adjectives — let the data speak
- Active voice preferred

### Emoji Usage
- Sparingly, if at all
- 👇 to point to charts is acceptable
- 🔥 for hot themes (occasionally)
- Never overuse
- No emoji in technical analysis

### Disclaimers
- Use sparingly: IMO, NFA, DYOR
- Place at end, not beginning
- Don't overdo it

---

## Image & Chart Requirements

### When Charts are REQUIRED:
| Category | Chart Required? |
|----------|-----------------|
| scanner_result | **YES** |
| theme_analysis | Recommended (at least one) |
| performance | **YES** (shows entry) |
| watchlist | Optional |
| technical_analysis | **YES** (essential) |
| educational | If referencing specific setup |
| market_commentary | Recommended |
| engagement | No |
| newsletter_cta | Optional |

### Chart Content Should Show:
- Ticker symbol clearly visible
- Relevant timeframe (Weekly, Daily, 4H)
- Key support/resistance levels marked
- Entry point if discussing a call
- Current price
- Signal indicators visible

### Quote Tweets
**When to quote your own tweets:**
- Updating a previous call with results
- Showing receipts on past signal
- Adding new analysis to previous thesis
- Celebrating a win

---

## Validation Checklist

### Universal Checks (All Categories)
- [ ] Contains at least one $TICKER
- [ ] No banned phrases present
- [ ] No loser-focused language
- [ ] Appropriate length
- [ ] Clear, actionable information

### Category-Specific Checks

| Category | Required Elements |
|----------|-------------------|
| scanner_result | $TICKER + entry price + thesis + chart |
| theme_analysis | Theme name + 3+ tickers with prices + CTA |
| performance | $TICKER + entry + current + % gain |
| watchlist | 3+ tickers with prices + what to watch for |
| technical_analysis | $TICKER + specific level + invalidation + chart |
| educational | Concrete example + clear lesson |
| market_commentary | Market context + opportunity + action |
| engagement | Trading-adjacent content |
| newsletter_cta | Value proposition + link |

---

## Implementation Notes

### For Claude Code / Tweet Generator

When generating tweets:

1. **Load this document** at the start of any tweet generation task
2. **Inject structured data** (tickers, prices, percentages) directly — don't rely on generation to remember them
3. **Match category** to content type being generated
4. **Validate against banned phrases** before accepting output
5. **Check category-specific requirements** are met
6. **Regenerate with specific feedback** if validation fails (max 2x)

### Data Priority in Tweets

When there's limited space, prioritize in this order:
1. Ticker symbols ($TICKER)
2. Prices
3. Percentage gains
4. Theme context
5. Timeframe
6. Additional commentary

### Content Phase Awareness

**EARLY phase** (limited signals):
- Focus on watchlist and theme analysis
- Educational content about methodology
- Market commentary connecting themes

**BUILDING phase** (some performance data):
- Mix signals with early receipts
- Begin showing entry → current performance
- Quote own past tweets for continuity

**ESTABLISHED phase** (full data):
- Lead with receipts and performance
- Full funnel stats
- Comprehensive theme coverage

---

## Quick Reference Card

### Every Tweet Needs:
✅ At least one $TICKER with price
✅ Specific, actionable information
✅ Clear category alignment
✅ Appropriate hook/CTA

### Every Tweet Avoids:
❌ Banned phrases
❌ Vague theme references without tickers
❌ Loser/loss focus
❌ Empty promises or cliffhangers
❌ Generic motivation without proof

### Best Practices:
📊 Attach charts for signals and technical posts
🔄 Quote your own past tweets as receipts
📝 Use short, punchy sentences
🎯 Lead with the most valuable information
💬 End with engagement hook when appropriate

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-06 | Initial creation from FinTwit analysis |

---

*This document is the authoritative style reference for Sterling Signals tweet generation. All generated content should be validated against these patterns and rules.*
