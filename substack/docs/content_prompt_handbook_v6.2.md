# Sterling Signals — Content Prompt Handbook v6.2

> **Multi-prompt sequential system for Opus 4.6 + Extended Thinking**
> Each post uses 2-3 prompts in sequence within a single context window.
> Every post produces a companion Substack Note for the Notes feed.
> Last updated: March 2026

---

## How to Use This Handbook

### What This Handbook Covers

This handbook produces **Tuesday–Thursday posts and ad-hoc trade alerts.**

**Saturday's newsletter** ("The Weekly Screening") is produced by **Prompt 11** in the Sterling Prompt Library during the analysis session — NOT from this handbook. That newsletter has the full session context and teases midweek content.

If you didn't run an analysis session (holidays, travel), use the **Performance Review Fallback** at the end of this handbook.

### Daily Workflow

1. Open Claude.ai (Opus 4.6 + extended thinking)
2. Attach the daily context document (`daily_context.md`)
3. Check **TODAY'S POST** in the context doc for today's category
4. Paste that category's prompts in sequence (Prompt 1 → wait → Prompt 2 → wait → etc.)
5. The final prompt produces both the article HTML AND a companion note

Everything in ONE context window. Each prompt builds on previous output.

### Content Types & Series Names

| Series | When | Prompts | Purpose |
|--------|------|---------|---------|
| **🟢 GREEN Signal** | Ad-hoc (new entry) | 1 | Actionable trade announcement — HIGHEST engagement |
| **Position Update** | Ad-hoc (exit) | 1 | Exit with reasoning |
| **Deep Dive** | Tue/Thu | 3 | Full analysis, valuation, price targets |
| **Sector Watch** | Wed | 2 | Theme deep dive with ETF flows, catalysts |
| **The Edge** | Thu (flex) | 3 | Educational — counterintuitive insight + portfolio connection |
| **The Weekly Screening** | Saturday | Prompt 11 (analysis session) | Newsletter overview — TEASES midweek content |

### Title Format

| Type | Title Pattern | Example |
|------|--------------|---------|
| Newsletter | "The Weekly Screening — Week [N]: [Hook]" | "The Weekly Screening — Week 12: Defence Dominates" |
| Trade Alert Entry | "🟢 GREEN Signal: $TICKER — [Theme]" | "🟢 GREEN Signal: $ASTS at $22.80 — Space & Defence" |
| Trade Alert Exit | "Position Update: $TICKER — [Outcome]" | "Position Update: $VNET — Systematic Exit" |
| Deep Dive | "Deep Dive: $TICKER — [One-line hook]" | "Deep Dive: $ASTS — The Satellite-to-Smartphone Play" |
| Theme Post | "Sector Watch: [Theme] ([Score]/10)" | "Sector Watch: Defence Technology (8.4/10)" |
| Educational | "The Edge: [Topic]" | "The Edge: Why 90% of Stocks Fail Our Screen" |

### Weekly Calendar

**Weeks WITH new signals:**

| Day | Content | Source |
|-----|---------|--------|
| Saturday | **The Weekly Screening** (newsletter) | Analysis session Prompt 11 |
| Sunday | Notes only (2) | Automated pipeline |
| Monday | Notes only (3) | Automated pipeline |
| Tuesday | **Deep Dive: $SIGNAL1** | This handbook |
| Wednesday | **Sector Watch: [Top Theme]** | This handbook |
| Thursday | **Deep Dive: $SIGNAL2** or **The Edge** | This handbook |
| Friday | Notes only (3) | Automated pipeline |

**Weeks WITHOUT new signals:**

| Day | Content | Source |
|-----|---------|--------|
| Saturday | **The Weekly Screening** (includes "Why We Passed") | Analysis session Prompt 11 |
| Tuesday | **Deep Dive: [Existing Position Update]** | This handbook (position refresh variant) |
| Wednesday | **Sector Watch: [Top Theme]** | This handbook (themes exist even without signals) |
| Thursday | **The Edge: [Educational]** | This handbook |

Trade alerts (🟢 GREEN Signal / Position Update) REPLACE whatever was scheduled that day.

---

## 🟢 GREEN Signal — Trade Alert Entry (1 Prompt)

**This is your highest-engagement post type.** Publish same-day as entry. Don't wait.

### Prompt

```
Read the attached context document for portfolio data, theme analysis, and marketing rules.

NEW POSITION: {TICKER}

Web search for:
- Current stock price
- Recent news and catalysts (past 2 weeks)
- Most recent quarterly earnings summary
- Sector/theme performance

Cross-reference with the context document's theme analysis — does this align with a top-rated theme?

TITLE: "🟢 GREEN Signal: ${TICKER} at $[PRICE] — [Theme Name]"

Write the trade alert AND a companion note as complete HTML.

═══ TRADE ALERT (400-800 words) ═══

Use the white-background Editorial theme (specs in Quick Reference).

1. Signal Header — 🟢 GREEN SIGNAL: ${TICKER} at $[PRICE]. Company name. Theme. Entry date.
2. Why This Company — What it does. What structural trend it's riding. 2-3 sentences.
3. What Triggered the Signal — Approved terms only: structural pivot confirmation, momentum confirmed, institutional accumulation patterns. What made this pass when 99%+ didn't?
4. The Setup — 3-5 specific data points from web search: revenue, margins, catalysts, institutional activity.
5. What We're Watching — The specific metric, date, or event that confirms or invalidates.
6. Risk — One sentence risk. One sentence why we took it anyway.
7. Footer — "Every GREEN signal documented with entry price and reasoning: https://sterlingsignals.substack.com"

Include [CHART: {TICKER}] placeholder.

═══ COMPANION NOTE (150-280 words) ═══

This note surfaces the trade alert in the Substack Notes feed.

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

**If this ticker was announced in Saturday's newsletter:** The newsletter already gave readers the 2-3 sentence pitch. This post delivers the FULL analysis they were promised. Acknowledge the newsletter: "We flagged $ASTS as a GREEN signal on Saturday. Here's the complete analysis."

**If this is a position update (no-signal week):** Use the same research framework but applied to an existing holding. "We entered $LUNR at $4.80. It's now $11.52. Here's what's changed and whether the thesis still holds."

### Prompt 1 of 3 — Research

```
Read the attached context document for portfolio data, theme analysis, scanner results, and marketing rules.

TICKER SELECTION: Check today's assignment. If a ticker is assigned, use it. If not, select the portfolio position with the highest P&L% (15%+ to showcase). State which ticker and why.

NEWSLETTER CONTEXT: Check if this ticker appeared in Saturday's newsletter (the context document may reference it). If so, note what was already said — we won't repeat that pitch. We'll go deeper.

POSITION UPDATE MODE: If this is an existing portfolio position (not a new signal), frame the research as a thesis refresh: "Is the original thesis still intact? What's changed?"

FRESHNESS CHECK: Web search current price. Recalculate P&L from context document entry price.

STAGE 1 — FINANCIAL BASELINE
Search for the most recent 10-Q/10-K, earnings releases, investor presentations. Compile:
- Trailing 8-quarter revenue by segment (table)
- Gross/operating/net margins per quarter (table)
- Free cash flow for trailing 4 quarters
- Shares outstanding + 12-month dilution trend
- Debt, cash, near-term maturities
- Short interest as % of float
- Institutional ownership changes (most recent 13F)

STAGE 2 — FORWARD REVENUE BUILD (12 months)
Per segment: contracts, partnerships, launches, pricing, TAM/SAM, headwinds.
Low/mid/high estimates. Every assumption cited.

Present as structured tables. Flag gaps. Don't write the article yet.
```

### Prompt 2 of 3 — Analysis

```
Good research. Now analyse using extended thinking.

STAGE 3 — MARGIN & EARNINGS PROJECTION
Bear/base/bull: gross margins, operating margins, EPS, FCF/share. Show working.

STAGE 4 — VALUATION TRIANGULATION
Four methods:
A — Historical Multiple Range (P/E, EV/EBITDA)
B — DCF (your projections, 10Y Treasury + equity risk premium)
C — Peer-Relative (4-6 competitors)
D — Catalyst-Adjusted (probability-weighted 12-month events)

Bear/base/bull targets per method.

STAGE 5 — SYNTHESIS
Weight methods by company type. Derive probability weightings (not default 25/50/25). Expected value. Three assumptions most likely wrong. Is the risk/reward asymmetric?

Present with tables. Don't write yet.
```

### Prompt 3 of 3 — Article + Companion Note

```
Write the article and companion note using all research from this conversation.

TITLE: "Deep Dive: $TICKER — [One-line hook from your strongest finding]"

═══ ARTICLE (1,000-1,500 words) ═══

White-background Editorial theme (specs in Quick Reference).

If this ticker was in Saturday's newsletter, open with: "We flagged $TICKER as a GREEN signal on Saturday. Here's the complete analysis behind that call." Then go straight to the data.

If this is a position update, open with: "$TICKER at $[CURRENT], up [X]% from our $[ENTRY] entry [N] days ago. Here's what's changed and whether the thesis still holds."

Structure:
1. The Pitch — 2-3 sentences. Ticker, price, what it does, why now.
2. The Thesis — Structural trend or catalyst. Connect to theme.
3. Why Now — Specific inflection. What changed recently.
4. The Numbers — Revenue, margins, valuation. Quarterly data. Show trajectory.
5. 12-Month Price Targets — Bear/base/bull cards with probability weightings and expected value.
6. Bear Case — Honest. Use "assumptions most likely wrong" from analysis.
7. Key Risk — One specific metric or date.
8. Our Position — Entry price, current P&L, exit trigger. If new signal: entry zone we're targeting.
9. Footer — "Every GREEN signal, every entry, every exit — documented weekly: https://sterlingsignals.substack.com"

[CHART: TICKER] placeholder.

═══ COMPANION NOTE (150-280 words) ═══

DO NOT summarise the article. Hook with the most surprising finding.

Lead with ONE number that makes a reader stop scrolling. Examples:
- "$ASTS has $265M cash, zero debt, and a patent wall 47 deep."
- "Our independent valuation puts $RCAT at $24 base case. It's trading at $13."
- "$LUNR: +140% in 67 days. Here's whether we're still holding."

Then 2-3 sentences of context. What does this number mean? Why should the reader care?

End with: "Full analysis with price targets just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Direct, data-heavy, opinionated. Lead with numbers. Contractions. Varied sentence length. No filler paragraphs. No "Let's dive in."
```

---

## Sector Watch (2 Prompts) — Wednesday

**The newsletter named this theme and scored it.** This post delivers the depth behind the score.

### Prompt 1 of 2 — Research & Validate

```
Read the attached context document for theme data, portfolio positions, and marketing rules.

THEME SELECTION: Check today's assignment. Use the assigned theme. If none, select the highest-rated PRIME or INVESTABLE theme. State theme and score.

NEWSLETTER CONTEXT: Saturday's newsletter already named this theme and gave a 1-2 sentence summary. This post goes DEEP — ETF flows, 13F data, policy catalysts, timeline. Don't repeat the newsletter's surface-level coverage.

FRESHNESS CHECK: Web search to validate and expand since context document was generated.

STAGE 1 — VALIDATE
Fresh data: has anything changed? Confirming or disconfirming evidence? Be honest.

STAGE 2 — DEEP RESEARCH
- ETF flows (specific tickers and dollar amounts)
- Institutional positioning (13F trends, fund moves)
- Policy/regulatory catalysts with specific dates
- Earnings evidence: are companies beating estimates?
- Risks: crowding, timeline, what would derail it?

STAGE 3 — OUR POSITIONS
Every portfolio position in this theme: ticker, entry, current, P&L%. If none, state clearly.

Present structured. Don't write yet.
```

### Prompt 2 of 2 — Article + Companion Note

```
Write the article and companion note.

TITLE: "Sector Watch: [Theme Name] ([Score]/10)"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme with teal accents:
- Theme score card: teal (#0d9488) left border, #f0fdfa bg
- Data callouts: rounded cards, #f8fafc bg, #e2e8f0 border

Open with: "[Theme] scored [X]/10 in this week's screening." Or reference the newsletter: "We named [Theme] as our top-rated sector on Saturday. Here's the data behind that score."

Structure:
1. Why This Theme, Why Now — Strongest data point first.
2. The Investment Thesis — Structural dynamics. Multi-year story.
3. The Evidence — ETF flows, institutional moves, earnings, catalysts. Numbers from your research.
4. Our Positions — Every position in this theme with entry prices and P&L. If none: "We're watching but haven't found a setup that clears all gates."
5. Risks — What would make this wrong?
6. What We're Watching — Upcoming events with dates.
7. Stocks Positioned — 3-5 stocks, including ours.
8. Footer — "We score themes weekly across 1,800 stocks: https://sterlingsignals.substack.com"

═══ COMPANION NOTE (150-280 words) ═══

Lead with the most compelling data point from your research:
- "$800M flowed into defence ETFs this month. Here's why."
- "3 of our 5 positions sit in one theme. It just scored 8.4/10."

Don't summarise the article. Give ONE data point that makes a reader want the full picture.

End with: "Full sector analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Opinionated. "Capital is flowing into defence. The data is clear." Contractions. No filler. No hedging into nothing.
```

---

## The Edge — Educational (3 Prompts) — Thursday (Flex)

### Prompt 1 of 3 — Discover Topic

```
Read the attached context document for portfolio data, themes, scanner results, marketing rules.

Find the most compelling educational topic. Priority order:

1. PORTFOLIO EVENT — Position milestone, stop proximity, upcoming catalyst
2. SCANNER ANOMALY — Zero signals, record rejection, theme flip
3. MARKET CONNECTION — Sector rotation, volatility event, breadth reading
4. COUNTERINTUITIVE RESEARCH — Studies from 2024-2026 (last resort)

For each candidate: can I illustrate it with something specific from the context document?

Present top 2-3 candidates. Recommend one.
```

### Prompt 2 of 3 — Research

```
Research that topic deeply. Web search for:
- 2-3 studies with specific numerical findings
- Real market example from the last 12 months
- Counter-example: when does this fail?
- Historical data quantifying the effect
- Which portfolio position or scanner result illustrates this?

Present research clearly. Don't write yet.
```

### Prompt 3 of 3 — Article + Companion Note

```
Write the article and companion note.

TITLE: "The Edge: [Topic — make it specific and surprising]"
Examples: "The Edge: Why the Best Portfolios Are 90% Empty"
          "The Edge: $LUNR Proves Why We Ignore Analyst Targets"

═══ ARTICLE (800-1,200 words) ═══

White-background Editorial theme.

Structure:
1. Hook — Most surprising finding. A number that contradicts common wisdom.
2. The Concept — Core idea, accessible, one paragraph.
3. The Evidence — Studies, data, specific numbers and periods.
4. In Our Portfolio — REQUIRED. Connect to a position or screening result. Name the ticker, entry, outcome.
5. The Exception — When does this fail? Intellectual honesty.
6. The Takeaway — One concrete, actionable insight.
7. Footer — "We apply these frameworks every week: https://sterlingsignals.substack.com"

[CHART: TICKER] if a position is referenced.

═══ COMPANION NOTE (150-280 words) ═══

Lead with the most counterintuitive stat:
- "The best-performing brokerage accounts belong to people who forgot their passwords."
- "Our scanner rejected 99.8% of stocks this week. That's not a bug."

2-3 sentences connecting it to our portfolio or approach.

End with: "Full analysis just published."
Then: "Not financial advice. Informational only."

Label: [ARTICLE HTML] and [COMPANION NOTE].

VOICE: Energy of "I just found something that changes how I think about $RCAT." Not lecturing.
```

---

## Performance Review — FALLBACK ONLY

**Use ONLY when no analysis session was run that week** (holiday, travel, skip week).
Saturday's newsletter normally comes from Prompt 11 in the analysis session.

### Prompt 1 of 2 — Gather Fresh Data

```
Read the attached context document. No analysis session was run this week,
so we're producing the newsletter from the context document alone.

Web search for current data:

MARKET: SPY, QQQ, IWM current + YTD. VIX. Major events this week.
PORTFOLIO: Current prices for all positions. Recalculate P&L.
NEXT WEEK: Earnings in our themes. Fed/data releases. Sector catalysts.

Present in a data table. Flag changes from context document.
```

### Prompt 2 of 2 — Newsletter + Companion Note

```
Write "The Weekly Screening" newsletter and companion note.

TITLE: "The Weekly Screening — Week [N]: [Hook]"

Follow the same structure as the analysis session newsletter (sections 1-9 from Prompt 11), but use only the context document data + your fresh web search data.

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
| The Weekly Screening | Portfolio's strongest number vs benchmark | "Full breakdown in this week's newsletter." |

### What Makes a Good Hook

BAD: "We just published our weekly deep dive on $ASTS."
GOOD: "$ASTS has $265M cash, zero debt, and a patent portfolio 47 deep. Our base case puts it at $38. It's trading at $22.80."

BAD: "New sector analysis on Defence."
GOOD: "$800M flowed into defence ETFs in February alone. Our three defence positions are up a combined 72%."

BAD: "This week's newsletter is out."
GOOD: "1,817 stocks screened. 3 survived. Portfolio at +34% vs SPY +12%. Full breakdown in today's newsletter."

The hook gives ONE number that creates curiosity. The post delivers the full story.

---

## Prompt Count Summary

| Day | Prompts | Time |
|-----|---------|------|
| Saturday (analysis session) | Prompt 11 + companion note | Built into session |
| Tuesday (Deep Dive) | 3 + companion note = 4 | ~15-20 min |
| Wednesday (Sector Watch) | 2 + companion note = 3 | ~10-15 min |
| Thursday (Deep Dive or Edge) | 3 + companion note = 4 | ~15-20 min |
| Ad-hoc Trade Alert | 1 (includes companion note) | ~5-10 min |

---

## v6.2 Change Log

| Change | Rationale |
|---|---|
| **Tiered content architecture** | Newsletter teases midweek content instead of delivering full analysis. Prevents repetition across the week. |
| **Saturday = Prompt 11, not handbook** | The analysis session newsletter has the richest context. Handbook Performance Review demoted to fallback for no-session weeks. |
| **Series names** | "The Weekly Screening", "Deep Dive", "Sector Watch", "🟢 GREEN Signal", "The Edge", "Position Update" — consistent branding readers recognise. |
| **Title format standardised** | Every post type has a specific title pattern. Ticker/theme/score in the title, not generic. |
| **Cross-references** | Deep Dive acknowledges Saturday's newsletter announcement. Sector Watch references the theme score. Prevents re-explaining what readers already saw. |
| **Companion notes on every post** | Every article produces a hook note for the Substack Notes feed. Note is NOT a summary — it's one surprising number that drives traffic. |
| **No-signal week calendar** | Tuesday shifts to position update, Thursday shifts to educational. Explicit handling instead of awkward gap. |
| **Trade alerts elevated** | Highest-engagement format treated as flagship, not exception. Published same-day with clear 🟢 branding. |
| **Position update framing** | Deep Dive has a "position update mode" for refreshing existing holdings. "Is the thesis still intact?" |
| **All v6.1 changes preserved** | Sequential prompts, anti-AI rules, anti-fabrication, white backgrounds, honest transparency, enriched data pipeline. |
