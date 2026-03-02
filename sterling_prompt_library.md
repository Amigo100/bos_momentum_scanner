# Sterling Grid Prompt Library
## Interactive Stock Screening in Claude.ai (Opus 4.6 + Extended Thinking)

> **Purpose:** Replace the 3-stage API pipeline with an interactive session where Opus 4.6
> does ALL analysis — thematic mapping, investment gate, and deep DD — in a single
> conversation with sequential prompts that build on each other.
>
> **Core principle:** The system's edge comes from rare 200-700% monster winners that
> account for 81% of total P&L. Those winners come from catching powerful secular themes
> early — not from scattered binary bets. Every prompt is designed to find exceptional
> emerging themes and filter everything else. Passing on a weak batch protects capital
> for when the real opportunity shows up.
>
> **Investment horizon:** Mean hold ~8 months. Losers are cut early (weeks to a few
> months) via ExD scanner signals and trailing stops. Winners run 12-18+ months as
> the secular thesis compounds through multiple catalyst cycles. The scanner uses
> short-term technical signals (HMA pivots, momentum confirmations) to catch
> INFLECTION POINTS — the moment a secular theme starts showing up in price action.
> But the THESIS is medium-to-long-term: structural demand shifts, capital cycle
> turns, secular growth waves that play out over quarters, not weeks. A near-term
> catalyst is the ENTRY TRIGGER that initiates re-rating — but the investment case
> must have a multi-quarter runway of catalysts and compounding demand. Theme
> assessment, bear case analysis, and competitive positioning should be evaluated
> on a 6-18 month outlook. Market regime affects deployment sizing, not stock
> selection — the regime will change multiple times during a typical hold.
>
> **Key design:** Each stage gets Claude's FULL extended thinking budget and web search
> allocation. You gate between stages — challenging, overriding, and filtering — so
> only the best candidates advance to the most intensive analysis. Conviction should
> decrease or stay flat through the pipeline as more risks are uncovered — not inflate.
>
> **Workflow:**
> 1. Run `python -m core.scanner --no-llm` → produces technical signals
> 2. Open a new Claude.ai chat (Opus 4.6, extended thinking ON, web search ON)
> 3. Paste **Prompt R** → retrospective on recent picks + attach signal_history.csv
> 4. Paste **Prompt 0** → market regime, capital flows, emerging themes
> 5. Paste **Prompt 1** with your signals → thematic analysis + cross-session clustering
> 6. Optionally run **Theme Power Check** challenge prompt if batch looks scattered
> 7. Review, challenge, decide which advance → **Prompt 2** for each (investment gate)
> 8. Review, challenge, decide which advance → **Prompt 3** for each (deep DD)
> 9. Run **Prompt 4** → Portfolio Review Gate (holistic session audit)
> 9b. If Prompt 4 flags DRIFT on a stock you believe in → **Prompt 3B** Parts A→B→C
>     (3 sequential messages: data foundation → forward model → scenarios + exception score)
> 10. Use **Challenge Prompts** at any stage to push back
> 11. **Prompt 5** → newsletter HTML | **Prompt 8** → decisions.json + signal_history rows
>
> **Mode recommendations by prompt:**
>
> | Prompt | Recommended Mode | Why |
> |--------|-----------------|-----|
> | R (Retrospective) | Extended Thinking | Light reasoning, price lookups via web search |
> | 0 (Market Context) | Extended Thinking | Heavy web search for flows/themes, moderate reasoning |
> | 1 (Thematic Analysis) | Extended Thinking | Per-ticker web search + scoring. Batch ≤4 tickers |
> | 2 (Investment Gate) | Extended Thinking | Adversarial reasoning, dilution/bear case research |
> | 3 (Deep DD) | Extended Thinking | Deepest single-stock reasoning. One ticker at a time |
> | **3B Part A** (Data Foundation) | **Research mode** | Broad data gathering (financial baseline + 15-20+ sources). Research mode's multi-step search is ideal. If unavailable, use Extended Thinking with aggressive search |
> | **3B Part B** (Forward Model) | **Extended Thinking** | Revenue projections, margin model, 4-method valuation triangulation. Needs full reasoning budget |
> | **3B Part C** (Scenarios & Verdict) | **Extended Thinking** | Probability-weighted scenarios, sensitivity testing, exception score. Adversarial judgment |
> | 4 (CRO Review) | Extended Thinking | Works from session memory. Minimal web search |
> | 5 (Newsletter) | Standard | Template-driven. Light price freshness search |
> | 6 (Sell Signal) | Extended Thinking | Bear case reasoning + current data search |
> | 7 (Mid-Week Catalyst) | Standard + web search | Quick catalyst/news checks |
> | 8 (JSON Export) | Standard | Structured output from session decisions |
>
> **When to switch modes mid-session:** The main pipeline (R→0→1→2→3→4) should run
> entirely in one Extended Thinking conversation to preserve context. If Prompt 3B is
> triggered after Prompt 4, you have two options: (a) run Part A in a separate Research
> mode chat, copy its output back into the main session, then run Parts B and C in
> Extended Thinking — this gives the best data quality for the financial baseline and
> valuation anchors; or (b) run all three parts in the main Extended Thinking session
> with thorough web search — simpler but Part A won't be as comprehensive.

---

# PROMPT R: WEEKLY RETROSPECTIVE (3 minutes)

> **When to use:** Very first prompt of every session, before Prompt 0. Takes ~3 minutes.
> Skip in your first-ever session (no prior data), but never skip after that.
>
> **Why this exists:** The pipeline generates better analysis over time if it learns
> from outcomes. Without this, each session starts from zero — the same scoring biases
> repeat. A stock you filtered 2 months ago that subsequently 3x'd is the most valuable
> data point your system can produce, and without a retrospective you'll never capture it.
>
> **Hold period context:** Our average hold is 3-18 months. A position entered 2 weeks
> ago being down 5% tells us NOTHING — that's noise within our timeframe. What matters:
> is the original THESIS still intact? Are the catalysts we predicted materialising? Is
> the structural demand driver accelerating or decelerating? We care about thesis
> tracking, not week-to-week price action.
>
> **After this prompt:** Run Prompt 0 (market context). The retrospective findings
> stay in conversation memory and inform all downstream analysis.

```
Before we start this week's analysis, let's do a quick retrospective on recent
decisions. This takes 3 minutes and makes everything downstream better.

═══════════════════════════════════════════════════════════════════
CURRENT PORTFOLIO & RECENT DECISIONS
═══════════════════════════════════════════════════════════════════

ALL OPEN POSITIONS (entered anytime — some may be months old):
[PASTE: ticker, entry date, entry price, current price, P&L %, original thesis]
(If no open positions, paste "No open positions")

RECENTLY CLOSED POSITIONS (last 4 weeks — hit target, stopped out, or exited):
[PASTE: ticker, entry date, exit date, P&L %, reason for exit]
(If none, paste "No recent closes")

NOTABLE FILTERED STOCKS (from last 2-4 sessions — stocks we seriously considered
but didn't buy):
[PASTE: 3-5 notable filtered tickers with brief reason for filtering,
or attach recent decisions.json files]
(If first session, paste "First session — no prior data")

SIGNAL HISTORY (for cross-session theme tracking):
[PASTE or ATTACH: signal_history.csv — the running log of all scanner signals
and their theme classifications from recent sessions. This file is updated at
the end of each session via Prompt 8.]
(If no history exists yet, paste "No signal history — first session")

═══════════════════════════════════════════════════════════════════
RETROSPECTIVE (quick calibration, not deep analysis)
═══════════════════════════════════════════════════════════════════

1. THESIS TRACKING (open positions): For each open position, search
   "[ticker] recent developments news catalysts":
   - Is the THESIS still intact? Are the structural drivers we identified
     still playing out? (This matters far more than week-to-week price moves)
   - Have any catalysts we predicted MATERIALISED since entry? What happened?
   - Any new RISKS that weren't in our original analysis?
   - Classify each: THESIS INTACT / THESIS WEAKENING / THESIS BROKEN
   NOTE: Short-term price drops in a 3-18 month hold are expected noise.
   Only flag price action if it signals thesis deterioration (e.g., catalyst failed,
   sector structural break), not normal volatility.

2. CLOSED POSITION LEARNINGS: For recently closed positions:
   - Did winners win FOR THE REASON we predicted? (If it ran on an unrelated catalyst,
     we got lucky — don't take credit)
   - Did losers lose FOR THE REASON the bear case predicted? (If yes, our bear case
     analysis needs to have more weight in future sessions)
   - Any pattern? (e.g., "our last 3 losers were all BINARY_CATALYST biotech plays")

3. FILTER AUDIT: For notable filtered stocks, search "[ticker] stock price performance
   last 3 months":
   - Did any filtered stock move +30% or more since we passed? If yes:
     Was our filter correct (it moved on something unrelated to our identified thesis)
     or was it a miss (it moved on exactly the thesis we identified but filtered)?
   - Did any filtered stock drop significantly, validating our filter?
   - With a 3-18 month horizon, filtered stocks that haven't moved yet may still
     be too early to judge — only flag clear winners (+30%) or clear validations (-20%).

4. CALIBRATION NOTES: Based on all of the above, produce 2-3 brief notes for this
   session. These should be SPECIFIC and actionable, not generic. Examples:
   - "We filtered TICKER_X 6 weeks ago for weak theme clustering, and it's since
     rallied 65% as the theme developed. Calibration: we may be over-filtering early
     movers in emerging themes — the clustering comes AFTER the first stock runs."
   - "TICKER_Y's thesis is weakening — the demand driver we identified is decelerating
     per latest channel checks. Consider tightening stop. Calibration: demand visibility
     scores above 7 need more rigorous channel check evidence."
   - "Our last 2 BINARY_CATALYST biotech plays both failed. Calibration: raise the bar
     on isolated biotech binaries — treat them as MODERATE FIT regardless of score."
   - "All open positions tracking thesis. Recent filter audit clean. No adjustment."

Present:

RETROSPECTIVE SUMMARY:
- Open positions: [X total, Y thesis intact, Z weakening, W broken]
- Closed positions: [any learnings from recent exits]
- Filter audit: [any notable misses (+30%) or validations (-20%)]
- Calibration notes: [2-3 specific adjustments for this session]

Then STOP. I'll confirm or adjust the calibration notes before we proceed to
Prompt 0 (market context).
```

---

# PROMPT 0: MARKET & CAPITAL FLOW CONTEXT

> **When to use:** After Prompt R (retrospective), BEFORE pasting scanner signals.
> Run this while your scanner is processing or before you open the signals output.
> Takes ~5 minutes of Claude's time. The output stays in conversation context and
> gives Prompt 1 a reference frame for judging theme power.
>
> **Why this exists:** The evaluation revealed that purely bottom-up analysis misses
> the "is this part of a wave?" question. When AI was the trade, you didn't need a
> macro prompt — the clustering was obvious. But in weeks where the scanner produces
> scattered signals, this context helps distinguish "isolated binary bet" from "early
> signal in an emerging wave." It's the difference between seeing one biotech signal
> (a coin flip) and seeing one biotech signal while knowing $4B in capital just
> rotated into XBI in the last 2 weeks (a wave starting).
>
> **Key structural distinction:** The output separates ESTABLISHED WAVES (what
> consensus already knows — useful for confirming clustering) from EMERGING SHIFTS
> (pre-consensus structural changes — where our actual edge is). The emerging shifts
> section is the higher-value output. It feeds directly into the Exceptional Setup
> Override in Prompt 1's Step D2.
>
> **Critical guardrail:** This prompt produces CONTEXT, not DIRECTION. It should
> NEVER be used to pre-select which stocks to favor. Score Steps A-C of Prompt 1
> blind to this context. Use it ONLY in Step D (system fit assessment).
>
> **After this prompt:** Paste Prompt 1 with your scanner signals. Claude will have
> the macro context in conversation memory when scoring micro-themes.

```
Before I give you this week's scanner signals, I need you to map the current market
environment. This context will inform our thematic analysis in the next message —
but it must NOT bias individual stock scoring. Use your full search budget here.

Our hold period is 3-18 months. Assess the market with that lens — we care about what
the environment looks like over the next 6-18 months, not what happened this week.
Short-term volatility is noise; structural regime shifts are signal.

You already have the retrospective calibration notes from Prompt R in this conversation.
Keep those in mind as you assess the market — particularly if recent outcomes suggest
adjusting how aggressively we deploy capital or filter themes.

═══════════════════════════════════════════════════════════════════
PART 1: MARKET REGIME — 6-18 MONTH OUTLOOK (2 minutes)
═══════════════════════════════════════════════════════════════════

Search: "stock market outlook 2026 2027 economy growth"
Search: "Fed interest rate path expectations 2026"
Search: "S&P 500 earnings growth forecast next 12 months"

We're NOT asking "is the market up or down this week?" We're asking: "Is the
environment over the next 6-18 months supportive of small-cap growth stocks breaking
out and sustaining multi-month runs?"

Classify the regime:
- RISK-ON: Economic expansion, accommodative policy, earnings growth accelerating,
  credit conditions supportive → our momentum system works best here. Small caps
  can sustain multi-month trends. Deploy capital at normal levels.
- RISK-OFF: Recession risk, tightening policy, earnings contracting, credit stress →
  momentum signals are less reliable, breakouts fail more often. Even good setups
  get dragged down by macro. Tighten all filters, reduce total deployment.
- SELECTIVE: Mixed — some sectors expanding, others contracting. Leadership narrow.
  Theme selection matters more than usual — need to be in the RIGHT themes, not
  just any theme with a technical signal.

Key data points (focus on TREND and DIRECTION, not single-week snapshots):
- Economic trajectory: GDP growth trend, employment, consumer spending
- Monetary policy: Fed rate path for next 12 months, real rates, liquidity conditions
- Earnings cycle: Are corporate earnings accelerating or decelerating?
- Credit conditions: High-yield spreads, bank lending, VC/IPO activity
- Small-cap specific: IWM relative performance over 3M/6M (structural trend, not
  weekly noise). Is capital structurally flowing into or out of small caps?
- Any major regime-changing events on the horizon (elections, trade policy, regulatory
  shifts) that could alter the 6-18 month outlook?

═══════════════════════════════════════════════════════════════════
PART 2: ESTABLISHED WAVES — What's Already Working (2 minutes)
═══════════════════════════════════════════════════════════════════

These are themes the MARKET ALREADY KNOWS ABOUT. They're useful for confirming
theme clustering in Prompt 1, but they are NOT where our edge comes from.
The consensus is already positioned here. Our edge is catching waves BEFORE consensus.

Search: "sector ETF flows capital rotation 2026 trends"
Search: "which sectors leading market performance 2026"
Search: "institutional capital allocation trends sectors"

a) SECTOR MOMENTUM (which sectors are in structural uptrends vs downtrends):
   Search: "sector performance ranking 3 month 6 month 2026"
   Focus on 3-month and 6-month trends, not weekly noise. Identify: top 2-3
   sectors in sustained acceleration AND bottom 2-3 in structural decline.

b) ESTABLISHED THEMATIC WAVES (themes where multiple stocks have sustained
   multi-month breakouts on the same structural driver):
   Search: "market themes driving stock performance 2026"
   Look for: themes where multiple stocks are co-moving on the SAME structural
   driver — not sector labels but specific catalysts (e.g., "AI inference demand
   causing GPU shortage" not "tech is up"). These waves can persist for 12-24
   months, so being in an established wave is fine for our 3-18 month hold —
   the question is whether we're early enough to capture meaningful upside.

c) SMALL-CAP ENVIRONMENT (structural, not weekly):
   Search: "small cap vs large cap relative performance trend 2026"
   Search: "small cap growth capital flows institutional"
   Is capital structurally flowing into or out of small caps over the medium term?
   Our system lives here — if small caps are in a sustained multi-month drawdown,
   even good signals underperform over our hold period.

═══════════════════════════════════════════════════════════════════
PART 3: EMERGING SHIFTS — Where the Edge Actually Is (3 minutes)
═══════════════════════════════════════════════════════════════════

THIS IS THE HIGHEST-VALUE SECTION. Spend the most search budget here.

These are themes that are JUST STARTING — not yet consensus, not yet crowded,
not yet reflected in sector ETF flows. The first stock in a wave always looks
like a standalone bet. Finding these themes BEFORE clustering is visible is
how our system catches 200-700% winners.

Search: "emerging investment themes 2026 institutional capital early"
Search: "new sector trends early innings growth 2026"
Search: "structural shifts capital spending technology healthcare energy"
Search: "venture capital investment trends new areas 2026"

Identify 2-4 themes that meet ALL of these criteria:
- EARLY INNINGS: Not widely covered, not consensus, not priced in
- STRUCTURAL DEMAND: Driven by a real shift (regulation, technology, demographics,
  supply chain) — not just sentiment or momentum
- MEASURABLE EVIDENCE: At least one concrete signal (VC funding round, corporate
  capex announcement, regulatory change, M&A deal) — not just a thesis
- SMALL-CAP RELEVANT: Would produce signals in our under-$25 stock universe

For each emerging theme:
- Theme name (specific, not a sector label)
- The structural driver (what changed and why it can't easily reverse)
- Early evidence (specific data: dollar amounts, deal names, regulatory filings)
- Scanner prediction: what kind of stocks would fire signals if this wave builds?
- Timing estimate: how early are we? (pre-revenue / first movers / early adoption)
- Duration estimate: is this a 6-month trade or a multi-year secular shift?

═══════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════

Present a compact briefing:

MARKET REGIME (6-18 month outlook): [RISK-ON / RISK-OFF / SELECTIVE]
- 2-3 sentences on why, with data on economic trajectory and policy direction

SMALL-CAP ENVIRONMENT: [FAVORABLE / NEUTRAL / HEADWIND]
- 1-2 sentences on structural capital flow trend (3M/6M direction, not weekly)

ESTABLISHED WAVES (consensus themes — useful for cluster confirmation):
- Sectors in sustained uptrend: [list with 3M/6M performance trend]
- Sectors in structural decline: [list with 3M/6M trend]
- Active established waves: [Theme 1: 1 sentence + participating stocks]
- If none detected: "No powerful multi-stock waves active."

EMERGING SHIFTS (pre-consensus — where our edge lives):
- [Theme 1]: [structural driver + early evidence + timing + duration estimate]
- [Theme 2]: [structural driver + early evidence + timing + duration estimate]
- If none detected: "No clear emerging shifts identified."

IMPLICATION FOR THIS SCAN:
- 2-3 sentences on what this means for how aggressively we should deploy
  capital and which themes deserve extra attention if they appear in signals.
- Frame this on our hold period: "Given a 3-18 month hold, the current regime
  [supports / does not support] aggressive deployment because [reason]."
- If regime is RISK-OFF: "Raise the bar. Advance only PRIME themes or exceptional
  asymmetric setups. Reduce total deployment — protecting capital for better
  conditions is the right move over a 6-18 month outlook."

═══════════════════════════════════════════════════════════════════
⚠️ HOW TO USE THIS CONTEXT (READ CAREFULLY)
═══════════════════════════════════════════════════════════════════

This context has TWO different uses in Prompt 1. Do not confuse them:

1. ESTABLISHED WAVES → use ONLY to confirm or deny theme clustering in Step D1.
   "Our scanner found 3 biotech signals, and biotech is an established wave" = good,
   clustering confirmed. But DON'T give a stock bonus points in Steps A-C just
   because its sector is hot. The stock still earns its score on its own merits.

2. EMERGING SHIFTS → use to RECOGNIZE potential early winners in Step D2.
   If a scanner signal aligns with an emerging shift identified here, that's a
   positive signal for system fit — it might be the first stock in a new wave.
   This should make you more willing to advance a standalone signal, not less.
   BUT: the stock still needs to pass on fundamentals. Alignment with an emerging
   theme is a reason to advance at standard threshold, not a reason to skip scoring.

The anchoring risk: if you identified "AI infrastructure" here, you'll unconsciously
score AI stocks higher in Prompt 1. Guard against this. Score Steps A-C blind to
this context. Use this context ONLY in Step D (system fit assessment).

Then STOP and wait for me to paste the scanner signals.
```

---

# PROMPT 1: THEMATIC ANALYSIS

> **When to use:** After running Prompt R (retrospective) and Prompt 0 (market context).
> Paste this with ALL your scanner output. This is the broadest analysis — mapping
> every signal to its micro-theme, scoring themes, and assessing the BATCH as a whole
> for theme clustering and quality. Claude uses full thinking time for JUST this stage.
> Both the retrospective calibration notes and the market context (established waves +
> emerging shifts) are already in conversation memory and will inform the analysis.
>
> **Key addition (v2):** After individual ticker analysis, Claude now assesses theme
> clustering across the batch, system fit per stock, and whether "pass on the batch"
> is the right call. This prevents advancing scattered binary bets when the system's
> edge requires catching powerful multi-stock themes.
>
> **After this prompt:** Review the batch assessment first. If clustering is weak,
> consider running the Theme Power Check challenge prompt. Then decide which tickers
> to advance to the Investment Gate (Prompt 2).

```
You are the Lead Portfolio Manager at a high-conviction growth fund. I'm going to give
you technical entry signals from our automated scanner. In THIS message, your job is
ONLY Phase 1: Thematic Analysis. We'll do the Investment Gate and Due Diligence in
subsequent messages — don't jump ahead.

Take your time with extended thinking. This is the foundation for capital allocation
decisions, so accuracy here prevents wasted analysis downstream.

═══════════════════════════════════════════════════════════════════
ABOUT OUR SYSTEM
═══════════════════════════════════════════════════════════════════

Our scanner finds stocks using a weekly momentum system (Sterling Grid V6):
- Entry: HMA(21) pivot low (V-bottom) + at least one confirmation gate
  - UC rising (institutional accumulation signal) AND/OR
  - MACD(12,26,9) cross-up (timing confirmation)
- Quality tiers: T1 (both gates, 20% equity), T2 (MACD only, 10%), T3 (UC only, 5%)
- Hold profile: Mean ~8 months. Losers cut early via ExD signals / trailing stops.
  Winners run 12-18+ months as the secular thesis compounds through multiple catalysts.
  The scanner catches inflection points; the THESIS plays out over quarters.
- Target: 50-100%+ returns, with occasional 200-700% monster winners
- Exit: ExD (HMA pivot high + UC falling) or tiered trailing stops

We want ASYMMETRIC setups — stocks where the upside is 100%+ over 6-18 months and
downside is bounded by clear floors. This is NOT about finding safe stocks or quick
trades. It's about finding multi-bagger candidates at inflection points where the
secular thesis has a multi-quarter runway to compound.

CATALYST FRAMEWORK (important — applies to all scoring below):
Our scanner catches SHORT-TERM technical inflection points, but our HOLD PERIOD is
3-18 months. This means we evaluate TWO types of catalysts:
- ENTRY CATALYSTS: Near-term triggers (next 1-3 months) that confirm the inflection
  point and initiate the re-rating. These validate our entry timing. Examples: earnings
  report, FDA milestone, product launch, conference presentation.
- THESIS CATALYSTS: Medium-to-long-term structural drivers (6-18 months) that sustain
  the move and produce multi-bagger returns. These are the REAL thesis. Examples:
  secular demand shift, market share expansion, capital cycle turn, regulatory tailwind.
A great setup has BOTH — near-term entry catalyst to confirm timing + structural thesis
catalyst to sustain the move over our hold period. A stock with only near-term binary
catalysts and no structural runway is a short-term trade, not a system fit.

═══════════════════════════════════════════════════════════════════
CONTEXT FROM EARLIER PROMPTS (DO NOT repeat — it's already in this conversation)
═══════════════════════════════════════════════════════════════════

You already have:
- RETROSPECTIVE (Prompt R): Calibration notes from recent outcomes. Apply these
  adjustments to your scoring and filtering throughout this analysis.
- MARKET CONTEXT (Prompt 0): Market regime (6-18 month outlook), established waves,
  emerging shifts. USE the established waves to confirm/deny clustering in Step D1.
  USE the emerging shifts to evaluate override eligibility in Step D2. Do NOT let
  either bias your individual stock scores in Steps A-C.

═══════════════════════════════════════════════════════════════════
CURRENT PORTFOLIO (for context — do not re-analyze these)
═══════════════════════════════════════════════════════════════════

[PASTE CURRENT OPEN POSITIONS WITH P&L — optional but helps Claude see theme exposure]

═══════════════════════════════════════════════════════════════════
TODAY'S TECHNICAL SIGNALS
═══════════════════════════════════════════════════════════════════

[PASTE YOUR SCANNER OUTPUT TABLE HERE]

═══════════════════════════════════════════════════════════════════
THEMATIC ANALYSIS — BOTTOM-UP MICRO-THEME DISCOVERY
═══════════════════════════════════════════════════════════════════

For EACH ticker, work through this 3-step bottom-up process. Do NOT force-fit tickers
into macro themes. Each stock gets its OWN micro-theme based on what actually drives
its business.

## Step A: Discover what the company actually does
Search: "[company] business model revenue segments 2025/2026"
- Primary business (1 sentence)
- Revenue composition (top 2-3 segments with approximate %)
- Specific growth driver — the ONE structural tailwind that could make this +50%

If pre-revenue, search "[company] technology pipeline milestones" instead.

## Step B: Identify the company's specific micro-theme
A micro-theme is NOT a sector label. It's the specific structural shift or catalyst
that creates outsized returns for THIS company.

Good micro-themes: "Cross-border digital remittance volume acceleration",
"505(b)(2) specialty pharma with near-term PDUFA dates",
"Outpatient surgery shift from hospital to ambulatory"

Bad micro-themes: "Fintech growth", "Healthcare innovation", "Technology sector"

The test: Can you write a 2-sentence investment thesis SPECIFIC to this company's
growth driver? If you can only write a generic sector overview, go more specific.

## Step C: Score the micro-theme on 5 factors

### 1. CATALYST STRENGTH (30% weight)
Search: "[micro-theme] catalysts 2025/2026" or "[company] upcoming catalysts"
Score on BOTH entry catalysts AND thesis catalysts (see framework above):
- 8-10: Near-term entry catalyst (1-3 months) PLUS structural thesis catalyst
  sustaining 6-18 month move. The ideal: specific dated event confirms timing,
  secular demand shift sustains the run.
- 5-7: Has structural thesis catalyst but no specific near-term entry trigger,
  OR has near-term trigger but limited structural runway beyond the event
- 1-4: No catalysts, or catalysts already priced in, or purely speculative timing

### 2. DEMAND VISIBILITY (20% weight)
Search: "[company] revenue growth trends" or "[micro-theme] growth acceleration"
- 8-10: Revenue/volume accelerating, backlog growing, contracted revenue
- 5-7: Steady growth, positive but not accelerating
- 1-4: Decelerating, speculative, single-customer dependent

### 3. MARKET RECOGNITION (15% weight)
Search: "[ticker] analyst coverage institutional ownership"
- 8-10: Under-followed (≤4 analysts), low institutional ownership — discovery upside
- 5-7: Moderate coverage, known but not crowded
- 1-4: Widely covered, fully priced, consensus already bullish

### 4. TIMING (10% weight)
Search: "[micro-theme] recent developments 2025/2026"
- 8-10: Early innings — inflection point just starting
- 5-7: Mid-cycle — established but room to run
- 1-4: Late cycle — most gains captured, mean reversion risk

### 5. CAPITAL CYCLE HEALTH (25% weight — HAS VETO)
Search: "[micro-theme] competition new entrants" or "[company] competitive moat"

First determine valuation regime:
- FUNDAMENTAL: Profitable, revenue-driven → score on earnings revisions + capex discipline
- OPTIONALITY: Pre-revenue, milestone-driven → score on TAM validity + funding runway
- TRANSITION: First revenue, proving model → blend both

Scores:
- 8-10: Demand exceeds supply, limited competition, pricing power
- 5-7: Competition entering but incumbents advantaged
- 1-4: Overcrowded, margin compression, capex exceeding demand

**VETO: If Capital Cycle Health ≤ 3, cap classification at SELECTIVE regardless of composite.**

COMPOSITE = (Catalyst × 0.30) + (Demand × 0.20) + (Recognition × 0.15) +
            (Timing × 0.10) + (Capital × 0.25)

OUTPUT FORMAT — MANDATORY:
Always present the composite as a WEIGHTED score out of 10.00 (two decimal places).
Show the calculation explicitly, e.g.:
COMPOSITE: (8×0.30) + (7×0.20) + (9×0.15) + (8×0.10) + (7×0.25) = 7.70

Do NOT present raw sums out of 50. Do NOT use "/50" scoring. Do NOT simply add
the five sub-scores together. The weighted composite must be directly comparable
across all batches in the session. If you find yourself writing "42/50", stop —
recalculate using the weighted formula above.

| Composite | Classification | Action |
|-----------|----------------|--------|
| 7.5+      | PRIME          | High conviction — prioritize |
| 6.0-7.4   | INVESTABLE     | Good opportunity — standard sizing |
| 4.5-5.9   | SELECTIVE      | Only the best stock in this theme |
| < 4.5     | AVOID          | Do not invest |

## Opportunity type classification (determines position approach):
- SECULAR_GROWTH: Multi-year structural tailwind, revenue accelerating, multiple
  catalysts stacked over 6-18 months → full size, longest hold (12-18+ months).
  THIS IS THE SYSTEM'S SWEET SPOT — these produce the 200-700% monster winners.
- BINARY_CATALYST: Pass/fail event (FDA, trial, ruling) → reduced size. BUT: our
  8-month mean hold means we're NOT playing just the event. The stock needs a
  POST-EVENT secular thesis (commercial launch, revenue ramp, market expansion)
  that sustains appreciation for 6-12 months after the catalyst resolves. A pure
  "bet on approval then sell" is NOT a system fit — that's a swing trade, not our game.
  If there's no post-event runway, classify as POOR FIT in D2.

  POST-EVENT RUNWAY TEST — the runway must be INDEPENDENTLY ASSESSABLE:
  Every drug has a theoretical commercial runway after approval. Every merger has
  a theoretical integration runway. The test is NOT "does a runway exist if the
  binary event succeeds?" — of course it does. The test is:
  1. Does the company have commercial infrastructure or a partner to capture demand?
     (A pre-revenue biotech with no sales force ≠ credible post-event runway)
  2. Is the post-event market established (existing patients, payer coverage precedent,
     known reimbursement pathway)?
  3. Can the post-event appreciation be modeled WITHOUT assuming best-case scenario?
  4. Does the company have EXISTING revenue or partnerships that provide value
     independent of the binary event?

  If the post-event thesis REQUIRES the binary event to resolve positively before
  any runway exists, classify as PURE BINARY in D2. Pure binaries get:
  - Position sizing capped at T3 (25% standard size)
  - Must score PRIME (7.5+) to advance regardless of system fit
  - Explicit acknowledgment: "This is a binary bet, not a secular theme trade"

  If the company has existing revenue, partnerships, or platform value independent
  of the binary event, classify as BINARY_WITH_FLOOR — standard BINARY_CATALYST
  rules apply (50% size via the binary sizing modifier).
- CYCLICAL_RECOVERY: Sector turning, early-cycle improving → full size if early in
  the cycle. Our 8-month hold captures the early-to-mid cycle recovery, which is
  where the biggest gains come from.
- SPECIAL_SITUATION: Restructuring, spin-off, activist → case-by-case. Thesis should
  have a 6-12 month runway of value creation, not just the event itself.
- MOMENTUM_CATCHUP: Strong sector, this stock lagging peers → standard size. Thesis:
  valuation gap closes as the market recognises this laggard belongs in the same
  re-rating wave as its peers. Needs structural reason for the gap to close, not
  just "it hasn't moved yet." Stops based on thesis break, not tight price levels.

═══════════════════════════════════════════════════════════════════
STEP D: SYSTEM FIT ASSESSMENT (after scoring all tickers)
═══════════════════════════════════════════════════════════════════

After scoring all tickers individually, step back and assess the BATCH as a whole.
This system's edge comes from rare 200-700% monster winners that account for 81% of
total P&L. Those winners came from catching powerful secular themes early — AI in 2022,
bitcoin miners at inflection points — NOT from scattered binary bets.

## D1: Theme Clustering Check

CROSS-SESSION THEME HISTORY:
Before evaluating this batch in isolation, check the SIGNAL HISTORY. If you have a
signal_history.csv (pasted or attached), load it now. This file tracks every ticker
that triggered a scanner signal in recent sessions, along with its theme classification.

Signal history format (maintained between sessions — see Prompt 8 output):
```
date,ticker,price,tier,theme,composite_score,system_fit,advanced,session_verdict
2026-02-28,NGNE,24.50,T2,rare_disease_biotech,7.60,MODERATE,yes,SPEC BUY
2026-02-28,LRMR,3.20,T1,rare_disease_biotech,7.70,MODERATE,yes,BUY
2026-02-21,QBTS,8.40,T2,quantum_computing,7.20,STRONG,yes,BUY
2026-02-14,IONQ,12.80,T1,quantum_computing,8.10,STRONG,yes,STRONG BUY
```

If no signal_history.csv is available, skip cross-session checks and evaluate this
batch using within-session clustering only (original behaviour).

WITHIN-SESSION CLUSTERING (this batch):
Look across ALL tickers in this batch:
- Are 2+ tickers in the SAME or closely related micro-theme? If yes, that theme
  clustering IS the signal — capital is flowing into this space so aggressively that
  multiple stocks are breaking out simultaneously. PRIORITIZE these.
- If every ticker is in its own isolated micro-theme with zero overlap, flag this
  explicitly: "No theme clustering detected — this batch contains N isolated bets."

CROSS-SESSION CLUSTERING (from signal_history.csv, last 4 weeks):
- Does any ticker in THIS batch share a theme with 1+ tickers from the last 4 weeks
  of signal history? If yes, this is LAGGED CLUSTERING — the wave is developing across
  sessions, not just within one session.
- Count how many tickers from the last 4 weeks share the same theme as any ticker
  in this batch. 2+ matches across 2+ sessions = LAGGED CLUSTERING detected.
- LAGGED CLUSTERING is a STRONG signal: it means the scanner is repeatedly catching
  the same structural shift across multiple weeks — exactly the pattern that preceded
  our best historical winners (e.g., AI stocks firing across consecutive weeks in
  2022, bitcoin miners firing across Nov-Dec 2023). The fact that they didn't all
  fire in ONE session doesn't weaken the wave — it confirms it's building.

MACRO ALIGNMENT:
- Reference the ESTABLISHED WAVES from Prompt 0: do any tickers in this batch align
  with those consensus waves? If yes, clustering is partially confirmed by external
  capital flows — note this.
- Reference the EMERGING SHIFTS from Prompt 0: do any tickers align with pre-consensus
  structural changes? If yes, this is more valuable than established wave alignment —
  it may be the first signal in a new wave. Flag for Exceptional Setup Override in D2.

THEME ALIGNMENT IMPACT ON GATING THRESHOLDS:
For each ticker, assess its alignment with Prompt 0 themes AND signal history,
then adjust the advancement threshold accordingly:

| Alignment Level | Evidence | Threshold Adjustment |
|----------------|----------|---------------------|
| STRONG (same-session clustering + wave alignment) | 2+ tickers THIS batch in same theme + Prompt 0 wave | Lower threshold: INVESTABLE 5.5+ advances |
| LAGGED (cross-session clustering) | This ticker's theme matches 2+ tickers from last 4 weeks of signal_history.csv | Standard threshold: per D2 system fit rules (treat as if clustering detected) |
| MODERATE (wave alignment, no clustering) | Aligns with Prompt 0 established wave, no clustering in batch or history | Standard threshold: per D2 system fit rules |
| EMERGING (potential first-mover) | Aligns with Prompt 0 emerging shift, no clustering yet | Standard threshold + flag for Exceptional Setup Override |
| NONE (zero alignment) | No match to Prompt 0 themes, no clustering in batch or history | Raise threshold: +1.0 to all advancement thresholds |

When a ticker has NONE alignment:
- STRONG FIT threshold rises from 6.0 to 7.0
- MODERATE FIT threshold rises from 7.5 to 8.5
- Exceptional Setup Override criterion #4 (Emerging Theme Alignment) CANNOT be met

When a ticker has LAGGED alignment (from signal history):
- Treat as STANDARD threshold — the cross-session clustering provides the confirmation
  that same-session clustering normally provides
- Note: "LAGGED CLUSTERING detected — [theme] has triggered [N] signals across [M]
  sessions in the last 4 weeks: [list tickers and dates from history]"
- This is valuable intelligence: flag the emerging wave for Prompt 0 calibration in
  the next session

This means off-theme tickers need to score exceptionally high on pure
company-specific merit to advance. This is intentional — the system's edge
comes from theme alignment, and capital deployed into off-theme trades has
lower expected returns historically. State the alignment level and adjusted
threshold explicitly for each ticker.

## D2: System Fit Filter
For each ticker, assess fit with the system's return profile:

STRONG FIT (advance at standard INVESTABLE 6.0+ threshold):
- Secular growth theme with multi-stock participation
- Clear catalyst within 6 months that could initiate re-rating, with structural
  runway supporting 6-18 month appreciation
- Under-followed name in a proven, powerful theme
- T1/T2 signal quality

MODERATE FIT (raise threshold — need PRIME 7.5+ to advance):
- Standalone binary bet in isolated micro-theme (no clustering)
- No catalyst within 6 months (thesis relies on gradual re-rating only)
- T3 signal quality (weakest technical confirmation)

⚡ EXCEPTIONAL SETUP OVERRIDE (advance at standard threshold DESPITE moderate fit):
The first stock in a wave always looks like a standalone bet. RGTI was a standalone
quantum computing signal before the wave became visible. The override exists to
prevent over-filtering potential monster winners. A stock qualifies for override if
it meets ALL FOUR of these criteria — not three, all four:

1. CATALYST STACK: 2+ specific catalysts within 6 months (not vague "H2 2026"),
   with structural drivers supporting appreciation over our full 6-18 month hold
2. SHORT SQUEEZE POTENTIAL: Short interest >20% of float, OR institutional
   accumulation by sector specialists in most recent 13F
3. EXTREME ASYMMETRY: Math shows 100%+ upside over 6-18 months with downside floor
   within 30% (minimum 3:1 reward/risk), OR trading below cash value
4. EMERGING THEME ALIGNMENT: Micro-theme aligns with an EMERGING SHIFT identified
   in Prompt 0, OR is in a space with recent structural catalyst (new regulation,
   breakthrough technology, supply shock) that could produce multi-stock breakouts
   over the coming months

If all four criteria are met: advance at INVESTABLE threshold with notation
"EXCEPTIONAL OVERRIDE — potential first-mover in emerging wave. Monitor for
clustering signals in subsequent sessions."

If only 2-3 criteria are met: remains MODERATE FIT, needs PRIME 7.5+ to advance.
The override is NARROW by design — it should fire on ~1 stock per month, not
every session.

POOR FIT (filter regardless of score):
- Large-cap (>$2B) with <30% analyst upside to consensus
- Turnaround/value play with no binary catalyst
- Pre-revenue with no catalyst within 6-12 months
- Stock already up >40% in 20 trading days (chasing, not catching)

## D3: Sector Concentration Warning
If the advancing tickers are >80% concentrated in one sector (e.g., all biotech),
flag this explicitly: "WARNING: Portfolio would be [X]% [sector]. A sector-wide
selloff creates correlated risk across all positions."

## D4: Session-Level Theme Alignment Gate

After completing Phase 1 for ALL batches in this session, assess theme alignment
across the full signal set. This is the most important quality check of the session.

THEME ALIGNMENT SCORE — count across ALL batches combined:
- How many advancing tickers align with established waves or emerging shifts
  from Prompt 0?
- How many advancing tickers cluster into shared micro-themes (2+ tickers
  in the same structural shift) — within THIS session OR across recent sessions
  via signal_history.csv (LAGGED CLUSTERING)?

| Alignment | Session Quality | Action |
|-----------|----------------|--------|
| 2+ tickers in same theme + wave alignment | STRONG SESSION | Deploy normally |
| LAGGED CLUSTERING detected (this session + history = 2+ in same theme) | STRONG SESSION | Deploy normally — the wave is building across sessions |
| 1+ ticker with wave alignment, no clustering (neither session nor history) | MODERATE SESSION | Deploy at reduced conviction (all scores -1) |
| 0 tickers with wave alignment BUT lagged clustering detected | MODERATE SESSION | Deploy at standard conviction for clustered tickers only |
| 0 tickers with wave alignment, no clustering of any kind | WEAK SESSION | ⚠️ PAUSE — do not proceed to gating automatically |

If WEAK SESSION:
Flag explicitly: "Zero advancing tickers align with identified themes. This
session's candidates are OFF-SYSTEM trades — they may be individually strong
but don't match the trade type that produced our system's 200-700% winners."

Present the user with a conscious choice:
"The scanner found [N] technically strong signals but none align with our
identified macro themes. Options:
(a) Proceed with the strongest individual setup at reduced size (T3/25%)
    as an off-system speculative position
(b) Pass entirely and preserve capital for a theme-aligned session
Which approach?"

Do NOT automatically proceed to gating in a WEAK SESSION. The user must
consciously choose to deploy capital into off-theme trades. This gate exists
because the system's historical edge comes from theme-driven momentum, not
isolated binary bets. A session with zero theme alignment is not necessarily
wrong — the scanner caught what it caught — but deploying should be deliberate.

NOTE: This check runs AFTER all batches are analysed, not after each individual
batch. A single batch might have zero alignment, but a later batch might produce
the theme-aligned signal. Wait until all batches are complete before triggering
the session-level gate.

## D5: "Pass on the Batch" Is a Valid Outcome
If no theme clustering exists AND no individual stock reaches PRIME (7.5+) AND
no stock qualifies for the Exceptional Setup Override AND the system fit assessment
shows mostly MODERATE/POOR fits, the correct recommendation may be:
"No exceptional setups this session. Recommend holding cash and waiting for a
stronger signal set." Passing on a weak batch protects the win rate. Every mediocre theme
that passes is capital unavailable when the real opportunity shows up.

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

For each ticker, present:
- Company description (1 sentence)
- Micro-theme name
- Sub-scores (catalyst, demand, recognition, timing, capital cycle) with brief justification
- Composite score and classification
- Opportunity type and valuation regime
- System fit: STRONG / MODERATE / POOR with 1-sentence reason
- 2-sentence thesis specific to this company

After ALL tickers, present:

BATCH ASSESSMENT:
- Theme clustering: [Detected: X tickers in Y theme] or [None — N isolated micro-themes]
- Sector concentration: [X% in sector Y — flag if >80%]
- Batch quality: [STRONG / MIXED / WEAK] — honest assessment of whether this batch
  contains the kind of setups that produce monster winners, or scattered modest opportunities

COMPARATIVE RANKING TABLE:
| Ticker | Theme | Composite | Classification | Regime | System Fit | Recommendation |
"If I could only buy ONE, which has the best risk-adjusted setup and why?"

GATING RECOMMENDATION:
- ADVANCE TO GATE: [list tickers] — PRIME themes, or INVESTABLE with STRONG system fit
- FILTERED OUT: [list tickers] — each with 1-sentence reason
- BORDERLINE: [list tickers] — worth discussing before deciding
- If batch is weak: "PASS ON BATCH — [reason]. Recommend waiting for stronger signals."

For stocks with MODERATE system fit (standalone binary bets, T3 signals, no entry
catalyst within 3 months), explicitly flag: "Advancing at reduced conviction — needs
exceptional Gate 2 performance to justify position."

Then STOP and wait for my feedback. I'll tell you which tickers to advance to the
Investment Gate. I may challenge your theme calls, override your gating, or ask you
to look deeper at a borderline case before we proceed.
```

---

# PROMPT 2: INVESTMENT GATE

> **When to use:** After Prompt 1, for each ticker you decide to advance. Run this
> once per ticker (or small batch of 2-3 if you want to compare them).
>
> **Context:** You're in the same conversation. Claude already has the thematic analysis.
> No need to re-paste anything — just name the tickers.
>
> **Key principle (v2):** The gate's job is to FILTER, not CONFIRM. It now includes a
> structural dilution check (not just S-3 filings), stronger bear case requirements
> (with classification: dismantled/partially/can't), entry timing assessment (Phase D —
> prevents chasing), and a WATCHLIST verdict for good-thesis-bad-timing stocks.
> The gate's value is measured by what it rejects.
>
> **After this prompt:** Review each verdict, challenge as needed, then decide which
> to advance to Deep DD (Prompt 3).

```
Run the Investment Gate on: [TICKER(S)]

You have the full thematic analysis from our earlier discussion. DO NOT repeat it.
Focus this entire analysis on RED FLAGS, RETURN MATH, and BEAR CASE.

HOLD PERIOD REMINDER: Our average hold is 3-18 months. Assess risks and catalysts
on that timeframe. A stock with no catalyst for 6 weeks is fine if the structural
thesis sustains a 12-month move. A stock with ONLY a near-term binary catalyst and
no structural runway beyond the event is a short-term trade, not a system fit.

Use your full extended thinking budget on just this assessment.

═══════════════════════════════════════════════════════════════════
PHASE A: DISQUALIFIER SCREEN
═══════════════════════════════════════════════════════════════════

Search: "[ticker] SEC filing insider trading news 2025/2026"
Search: "[ticker] earnings date short interest analyst revisions"

IMMEDIATE DISQUALIFIERS (→ NO GO, stop analysis):
- Auditor resignation or delayed 10-K filing
- CFO/CEO resigned in last 60 days (without clear succession)
- Shelf offering (S-3) filed in last 30 days with no stated use
- Active SEC or DOJ investigation
- OPTIONALITY/TRANSITION regime + earnings in < 5 trading days
- FUNDAMENTAL regime + earnings in < 5 days + revisions STABLE/DECELERATING/NEGATIVE

STRUCTURAL DILUTION CHECK (new — goes beyond single S-3 filing):
Search: "[ticker] shares outstanding history dilution warrant exercise"
- Shares outstanding increase >50% in trailing 12 months → CAUTION: structural dilution
- Shares outstanding increase >100% in trailing 12 months → DISQUALIFIER unless cash
  position now exceeds market cap (i.e., dilution funded a war chest, not plugged losses)
- Warrants/options exercisable within 12 months that would add >15% to float →
  CAUTION: upside ceiling. Note the strike price — it acts as a technical resistance level.

EXCEPTION (continue, flag CAUTION):
- FUNDAMENTAL regime + earnings in < 5 days + revisions ACCELERATING
  → This is a catalyst, not a risk. Smart money is positioning for the beat.

CAUTION FLAGS (note but continue):
- Earnings in 5-15 trading days → timing risk
- Short interest > 25% → volatility risk
- Single analyst downgrade → one opinion, not a trend
- Insider selling under 10b5-1 plan → scheduled, not panic
- Volume < $1M/day or float < 5M shares → LIQUIDITY CONCERN, recommend REDUCED size

═══════════════════════════════════════════════════════════════════
PHASE B: RETURN MATH TO 50%+
═══════════════════════════════════════════════════════════════════

Search: "[ticker] valuation multiples peers bear case risk 2025/2026"

Adapt to the valuation regime you identified in thematic analysis:

For FUNDAMENTAL:
"Revenue grows X% → operating leverage delivers Y% EPS growth → multiple re-rates
from Ax to Bx → price target $Z (+N%)"
Include: current multiple vs 3-year average and vs peers

For OPTIONALITY:
"If [milestone X] in [timeframe], institutional coverage expands from N to M analysts
→ re-rating as theme goes mainstream"
Include: comparable milestone re-ratings in similar themes

For TRANSITION:
"Revenue of $X validates the story → multiple stabilizes at Yx vs current Zx
→ floor at $P, upside to $Q"

═══════════════════════════════════════════════════════════════════
PHASE C: BEAR CASE (steelmanned — genuinely try to kill this trade)
═══════════════════════════════════════════════════════════════════

Search: "[ticker] bear case risk short thesis"
Search: "[ticker] short interest short seller report"

Your job here is to find the ONE thing that should prevent us from buying this stock.
Approach this as a short seller building a position, not as a bull looking for reasons
to dismiss concerns.

- What's the #1 argument a smart short-seller would make?
- Can you dismantle it with DATA? (Not "I think," but "Revenue grew X% which proves…")
- If not dismantled: FATAL FLAW (→ NO GO) or ACCEPTABLE RISK (→ continue)?

CRITICAL: "The FDA granted [designation X], so the risk is mitigated" is NOT a
universal rebuttal. FDA designations don't eliminate commercial risk, competitive risk,
capital structure risk, or execution risk. Each bear argument must be rebutted on its
OWN terms with specific data, not deflected with a regulatory citation.

BEAR CASE CLASSIFICATION:
- CAN'T DISMANTLE: The bear argument stands and you cannot refute it with data →
  Does it threaten >50% of the thesis? If yes → FATAL FLAW → NO GO.
  If no → ACCEPTABLE RISK, but note it honestly and reduce conviction.
- DISMANTLED: Specific data contradicts the bear thesis → ACCEPTABLE RISK → continue.
- PARTIALLY DISMANTLED: Data weakens but doesn't eliminate the bear case →
  ACCEPTABLE RISK at reduced conviction. Do NOT spin this as fully resolved.

DOWNSIDE FLOOR:
- Where would value investors or strategic acquirers step in?
- Maximum realistic loss over the hold period if thesis fails?

═══════════════════════════════════════════════════════════════════
PHASE D: ENTRY TIMING ASSESSMENT
═══════════════════════════════════════════════════════════════════

Good thesis + bad entry = underperformance even on a 6-18 month hold. A stock that
drops 30% in month 1 needs to rally 43% just to get back to breakeven — that's
wasted time and capital. This check ensures we're entering near an inflection, not
chasing a move that already happened.

Search: "[ticker] stock price performance last 3 months"
Search: "[ticker] stock price chart recent months"

1. RECENT MOVE: How much has the stock already moved from its pivot low?
   - Up <20% from pivot: CLEAN ENTRY — standard approach
   - Up 20-40% from pivot: ELEVATED ENTRY — still acceptable if thesis has 100%+
     upside over 6-18 months, but acknowledge we're paying up. Reduce conviction
     by 1 point.
   - Up >40% from pivot: CHASING — do NOT enter unless a hard catalyst is imminent.
     Even on a 12-month thesis, entering after a 40%+ run creates significant
     drawdown risk if the move consolidates. Recommend WATCHLIST with pullback
     entry target.

2. GAP-UP RISK: Did the stock gap up >15% in a single session recently?
   - If yes: gaps often consolidate before the next leg. Recommend waiting 1-2 weeks
     for a new base to form unless a hard catalyst prevents waiting.

3. CATALYST PIPELINE: What's the catalyst roadmap over the next 6-18 months?
   - First catalyst within 3 months: STRONG — near-term event can initiate re-rating,
     with longer-term catalysts sustaining momentum
   - First catalyst in 3-6 months: ACCEPTABLE — may see sideways action initially,
     but if structural thesis is strong, accumulation phase can be productive.
     Are there interim developments (conferences, data updates, partnerships)
     to sustain investor interest?
   - No specific catalyst within 6 months: CAUTION — thesis relies entirely on
     gradual re-rating. Needs exceptionally strong structural thesis to justify
     tying up capital. Reduce conviction by 1 point.
   - Multiple catalysts stacked over 6-18 months: IDEAL — this is the setup that
     produces monster winners. Each catalyst re-rates the stock higher, and the
     thesis compounds over our full hold period.

4. WAITING COST: What's the realistic cost of waiting 2-4 weeks for a better entry?
   - Is there a defined event that makes waiting risky (lockup expiry, offering)?
   - Or is the stock likely to consolidate, giving a better entry point?
   - For a 12-month thesis, a 2-week wait is insignificant if it improves entry by 10%.

ENTRY TIMING VERDICT:
- CLEAN ENTRY: Proceed at full conviction
- ELEVATED ENTRY: Proceed but reduce conviction by 1 point, note the entry risk
- CHASING: Recommend WATCHLIST with specific pullback target price
- POOR TIMING: Recommend WATCHLIST with re-entry trigger closer to catalyst

If timing verdict is CHASING or POOR TIMING, this DOES affect the overall verdict —
a STRONG BUY with bad timing becomes BUY or WATCHLIST. A BUY with bad timing
becomes SPEC BUY or WATCHLIST.

═══════════════════════════════════════════════════════════════════
VERDICT
═══════════════════════════════════════════════════════════════════

STRONG BUY (conviction 8-10):
- No disqualifiers + math to 50%+ clear + entry timing CLEAN or ELEVATED
- Catalyst pipeline over 6-18 months with structural drivers
→ Advance to Deep DD at FULL position size

BUY (conviction 6-7):
- Thesis intact, math works, but meaningful concerns remain
  (moderate dilution, partial bear cases, single catalyst dependency)
→ Advance to Deep DD at STANDARD position size (T2)

SPEC BUY (conviction 4-5):
- Thesis has merit but multiple unresolved concerns
  (heavy dilution, competitive threats, execution dependency)
→ Advance to Deep DD at REDUCED (50%) position size

WATCHLIST (timing-driven):
- Strong thesis (conviction would be 5+) but CHASING or POOR TIMING entry
→ Do NOT advance now. Set specific re-entry trigger and price target.
  Re-evaluate if the stock pulls back or catalyst window approaches.

NO GO (conviction 1-3):
- Any disqualifier hit, no math to 50%, or fatal bear case
→ Stop. State the specific reason AND what would flip the verdict.

BINARY RISK SIZING MODIFIER:
If opportunity type is BINARY_CATALYST, cap position size at 50% (T2 max)
REGARDLESS of conviction score. This is a SIZING adjustment, not a conviction
adjustment. A conviction-8 binary catalyst is still 8/10 conviction — it gets
50% size because the outcome distribution is bimodal, not because the thesis
is weak. Report both: "BUY 7/10, T2 (binary cap)" or "STRONG BUY 8/10,
50% size (binary modifier)."

This separation matters: conviction measures THESIS STRENGTH. Position size
reflects thesis strength PLUS outcome distribution. A secular growth stock
at 7/10 gets full T2 sizing. A binary catalyst at 7/10 gets the same
conviction score but capped sizing. Don't conflate the two by artificially
lowering conviction to justify smaller size — score conviction honestly,
then apply the sizing modifier separately.

IMPORTANT: Your job is to FILTER, not to CONFIRM. These stocks passed technical screening
and thematic analysis — that means they deserve serious consideration. But the gate exists
to catch what earlier stages missed. If the bear case is strong, the dilution is severe,
or the math doesn't work — kill it. Don't rationalize a pass because the thematic score
was high. Each stage must independently justify advancement.

The gate's value is measured by what it REJECTS, not what it advances. If everything
passes, the gate isn't working.

Present for each ticker:
- Disqualifier result (CLEAN / CAUTION / DQ)
- Dilution check result (if applicable)
- Return math summary (1-2 sentences)
- Bear case + rebuttal + classification (DISMANTLED / PARTIALLY DISMANTLED / CAN'T DISMANTLE)
- Downside floor estimate
- Entry timing verdict (CLEAN / ELEVATED / CHASING / POOR TIMING)
- VERDICT + conviction score (use the defined scale: STRONG BUY / BUY / SPEC BUY /
  WATCHLIST / NO GO). If BINARY_CATALYST, note the sizing modifier separately.
- If STRONG BUY/BUY/SPEC BUY: recommended position sizing
- If WATCHLIST: specific re-entry trigger and target price

Then STOP and wait for my feedback before we proceed to Deep DD.
```

---

# PROMPT 3: DEEP DUE DILIGENCE

> **When to use:** After Prompt 2, for each ticker that passed the Investment Gate.
> Run this ONCE PER TICKER to give Claude maximum thinking time and search depth.
>
> **Context:** Same conversation. Claude has both thematic analysis and gate output.
> This is the forensic deep dive — Claude should go DEEPER than the gate, not repeat it.
>
> **Key principle (v2):** Deep DD now starts with a "Conviction Direction Rule" —
> the default is same or lower conviction, not higher. The bear case investigation is
> explicitly elevated as the MOST IMPORTANT phase (more search budget than the other
> 4 phases combined). Claude must classify each bear argument and state conviction
> change direction explicitly. If conviction increased, Prompt 4's Review 2 will
> audit the upgrade — but flag it in your delivery so the review gate catches it.

```
Run Deep Due Diligence on: [TICKER]

You have the full thematic analysis and investment gate from our earlier discussion.
DO NOT repeat what you already found. This phase is about going DEEPER — finding what
the earlier analysis couldn't catch. Use your full extended thinking and search budget
on this one stock.

HOLD PERIOD: 3-18 months. Assess competitive moat, demand runway, and institutional
positioning on that timeframe. A strong thesis here means the structural drivers
sustain appreciation for 6-18 months, not just through the next binary event.

═══════════════════════════════════════════════════════════════════
CONVICTION DIRECTION RULE
═══════════════════════════════════════════════════════════════════

Your gate verdict was [X/10]. The DEFAULT outcome of deep DD is SAME or LOWER
conviction — not higher. The deeper you dig, the more risks you find. That's normal.

To UPGRADE conviction from the gate, you must identify a MATERIAL new finding that
wasn't available at gate stage — not just more detail on the same bull case.
Examples of valid upgrades: previously unknown institutional accumulation by top-tier
sector specialists, a competitor elimination event, a regulatory milestone that
structurally de-risks the thesis.

Examples that do NOT justify an upgrade: earnings beat in line with expectations,
confirming a known catalyst date, restating the same thesis with more prose, spinning
a negative (institutional outflows) as a positive (contrarian entry).

═══════════════════════════════════════════════════════════════════
5-PHASE RESEARCH PROTOCOL
═══════════════════════════════════════════════════════════════════

1. GROWTH TRAJECTORY
Search: "[ticker] latest earnings revenue guidance operating metrics 2025/2026"
- FUNDAMENTAL: Revenue acceleration? Operating leverage kicking in? Customer retention?
- OPTIONALITY: Milestone announcements? Funding secured? Partnership validation?
- TRANSITION: Revenue vs expectations? Proving the model?
Key question: Is the growth story STRENGTHENING or weakening since our gate analysis?

2. CATALYST DEEP DIVE
Search: "[ticker] upcoming catalysts events dates 2025/2026"
- Exact catalyst dates (not vague "Q2 2026" — find the specific date or week)
- Historical patterns: Does this company beat estimates? By how much?
- Management equity grants with price targets — skin in the game?
- Conference presentations, investor days, analyst meetings coming up?

3. BEAR CASE INVESTIGATION (go deeper than the gate — THIS IS THE MOST IMPORTANT PHASE)
Search: "[ticker] short thesis detailed bear case risks 2025/2026"
Search: "[ticker] insider buying selling SEC Form 4 2025/2026"
Search: "[ticker] dilution shares outstanding warrant exercise history"

Your PRIMARY job in deep DD is to find the one thing that kills this trade.
Spend at LEAST as much search budget and thinking on bear case investigation as
you spend on phases 1, 2, 4, and 5 combined.

- What's the #1 thing that could go wrong that we HAVEN'T considered yet?
- Insider selling beyond scheduled 10b5-1 plans?
- Any class action lawsuits, patent challenges, regulatory headwinds?
- Customer concentration risk?
- Dilution trajectory: shares outstanding over 6/12/24 months. Warrants exercisable
  within 12-18 months. History of raises at or near catalyst dates.
- What would a forensic short seller find that a bullish analyst would overlook?

4. SMART MONEY POSITIONING
Search: "[ticker] institutional ownership 13F changes hedge fund 2025/2026"
- Are top-tier SECTOR SPECIALIST funds accumulating or distributing?
  (Index funds and quant shops entering ≠ conviction. Sector specialists entering = conviction.)
- Any notable new positions or exits?
- Activist interest?
- Short interest trend (increasing or decreasing?)

5. COMPETITIVE MOAT
Search: "[ticker] competitors market share defensibility moat"
- What stops a competitor from taking share?
- For OPTIONALITY: Is the IP defensible? Patent portfolio?
- Switching costs, network effects, or regulatory barriers?
- Who is the biggest competitive threat and what would they need to do?

═══════════════════════════════════════════════════════════════════
DELIVER
═══════════════════════════════════════════════════════════════════

ELEVATOR PITCH: 2-3 sentences — why this stock, why NOW, what's the edge.

WHY NOW: Key catalyst with SPECIFIC date.

THE MATH: Regime-adapted path to 50%+. Be specific — show the numbers.

BEAR CASE: Steelmanned — not a strawman. Then your rebuttal with DATA.
Classify each bear argument: DISMANTLED / PARTIALLY DISMANTLED / CAN'T DISMANTLE.
If any argument is CAN'T DISMANTLE, state this honestly and assess impact on thesis.

VARIANT PERCEPTION: What we see that the consensus misses — our edge.

KEY ASSUMPTION: The ONE thing that must be true for this to work.

KILL SWITCH: What triggers early exit — specific and measurable, not vague.

DOWNSIDE FLOOR: Where value buyers or acquirers step in. Max realistic loss.

RISK TO MONITOR: The single most important risk with a specific metric or date.

ACTION: Be specific — "Enter at ~$X. [Full/Reduced] position at T[1/2/3] allocation.
Set trailing stop at $Y. Monitor [specific event] on [date]."

HOLD THESIS: Expected hold period (3-6 months / 6-12 months / 12-18 months).
Key milestones over the hold period that should re-rate the stock. What would
trigger early exit (thesis broken) vs what's just noise (short-term drawdown).

CONVICTION CHANGE: State explicitly whether conviction INCREASED, DECREASED, or
stayed SAME from the gate verdict. If increased, name the specific new finding.
If decreased, name what the DD uncovered that the gate missed.

PRICE ANCHORING — MANDATORY:
If the stock price has moved >10% between gate analysis and DD analysis, you MUST
account for this in your conviction assessment. State the prices explicitly:
"Gate price: $X.XX | DD price: $Y.YY | Change: +/-Z%"

- Stock rose >10%: Risk/reward has deteriorated at the new price. Default action
  is DECREASE conviction by 1 point UNLESS the DD surfaced a material NEW positive
  finding that offsets the worse entry (e.g., previously unknown institutional
  accumulation, competitive moat widened, new catalyst emerged). If maintaining
  conviction despite >10% price increase, you must name the specific offsetting
  finding — "thesis unchanged" is not sufficient.
- Stock fell >10%: Risk/reward has improved. Conviction may INCREASE by 1 point
  IF the decline was not thesis-damaging (e.g., broad market selloff, not company-
  specific news). If the decline IS thesis-related, conviction should DECREASE
  despite the better price.
- Stock moved <10%: No price-driven adjustment required. Assess conviction on
  thesis and findings only.

FINAL VERDICT: STRONG BUY / BUY / SPEC BUY / NO GO with conviction 1-10.
If BINARY_CATALYST, state sizing modifier separately from conviction.
If verdict changed from the gate, explain what you found that shifted it.
If NO GO: State the fatal flaw AND what would flip the verdict.

Then STOP. I may challenge your bear case, stress-test the math, or ask for
comparisons before we finalize.
```

---

# CHALLENGE PROMPTS

> **When to use:** After receiving analysis at ANY stage. Pick the one relevant to
> your situation. These work after Prompt 1 (thematic), Prompt 2 (gate), or Prompt 3 (DD).
>
> **Active prompts:** Challenge the Bear Case, Challenge the Math, Head-to-Head
> Comparison, Liquidity & Execution Check, Check for Fresh News, Theme Power Check.
>
> **Absorbed into core pipeline:** Three former challenge prompts are now built into
> the core flow and run automatically:
> - ~~Validate Timing~~ → now Phase D of Prompt 2 (investment gate)
> - ~~Portfolio Concentration Check~~ → now Review 4 of Prompt 4 (portfolio review gate)
> - ~~Conviction Audit~~ → now Review 2 of Prompt 4 (portfolio review gate)

## Challenge the Bear Case

```
Your bear case for [TICKER] feels too easy to dismiss. Steelman it harder:

1. Search specifically for "[ticker] short seller thesis 2025/2026" — what are
   the bears actually saying?
2. What's the WORST realistic scenario over the next 6-12 months?
3. If you were SHORT this stock, what's your specific thesis and timeline?
4. How much could it drop if the bear case plays out?

Don't give me a balanced take. I want you to argue the bear side as hard as you can.
Then we'll decide if it's a fatal flaw or acceptable risk.
```

## Challenge the Math

```
The return math for [TICKER] feels optimistic. Stress-test it:

1. What if revenue grows at HALF the rate you assumed? Does math to 50% still work?
2. What if the multiple CONTRACTS instead of expands? (This sector may be de-rating)
3. For OPTIONALITY: What if the milestone slips 6 months? Does the thesis survive?
4. What's the math with FLAT multiples and only organic growth?

Give me the realistic case, not the bull case.
```

## Head-to-Head Comparison

```
I need to choose between [TICKER A] and [TICKER B]. Compare them directly:

1. Which has the better risk/reward from current price?
2. Which has the nearer-term catalyst?
3. Which bear case is more dangerous?
4. Which has more institutional discovery upside?
5. If you could only buy ONE, which and why?

Use specific numbers. "TICKER A has 80% upside vs 60% for B" not
"TICKER A has more upside."
```

## ~~Validate Timing~~ → Now built into Prompt 2, Phase D
> Entry timing assessment is now a core part of the investment gate. It runs
> automatically for every stock, not just when you remember to challenge it.
> If you need deeper timing analysis after Prompt 2, use the fresh news check below.

## Liquidity & Execution Check

```
For [TICKER]: Can we actually trade this cleanly?

1. What's the average daily dollar volume?
2. What's the float and short interest as % of float?
3. If we allocate [T1=20%/T2=10%/T3=5%] of a $[X] portfolio, how many shares is that
   vs average daily volume?
4. Is there offering/dilution risk in the next 12 months?
5. Any lockup expirations coming?
```

## Check for Fresh News

```
Before I pull the trigger on [TICKER], search for the very latest:

1. "[ticker] news today this week"
2. Any material developments since your earlier analysis?
3. Any insider transactions in the last 5 days?
4. Pre-market or after-hours moves that might signal something?

Quick check only — just tell me if anything has changed.
```

## Theme Power Check (use after Prompt 1)

```
Step back from individual stocks. I want to assess THEME POWER across this batch.

1. Are any of the micro-themes you identified part of a BROADER capital flow wave?
   Search: "sector ETF flows [relevant sectors] 2026" and
   "[theme] investment capital spending 2026"
2. When AI was the trade in 2022-2023, our scanner would have seen NVDA, SMCI, AMD,
   AVGO all firing signals in the same theme within weeks. When bitcoin miners were
   the trade, MARA, RIOT, CLSK all fired together. Is ANYTHING like that happening
   in this batch?
3. If this batch has zero theme clustering, be honest: are these isolated binary bets
   or genuine emerging themes? Would you rather deploy capital here or wait for a
   batch with stronger thematic conviction?
4. What themes are you seeing in the broader market right now (via search) that our
   scanner HASN'T caught yet? Should we be looking in a different direction?

Be blunt. "This batch is five unrelated binary bets" is a valid and useful answer.
```

## ~~Portfolio Concentration Check~~ → Now built into Prompt 4, Review 4
> Portfolio construction assessment (sector concentration, opportunity type mix,
> correlated risk, capital deployment) is now a core part of the Portfolio Review
> Gate. It runs automatically as Review 4 of Prompt 4 for every session.

## ~~Conviction Audit~~ → Now built into Prompt 4, Review 2
> Conviction trajectory auditing is now a core part of the Portfolio Review Gate.
> It runs automatically as Review 2 of Prompt 4, tracing each stock's conviction
> through the pipeline and flagging unjustified upgrades.
>
> **Ad-hoc use:** If you want to challenge conviction on a SPECIFIC stock mid-session
> (before Prompt 4), you can still ask directly:
> "Conviction on [TICKER] went from [X] to [Y]. Name the specific new finding or
> revert to the gate conviction."

---

# PROMPT 4: PORTFOLIO REVIEW GATE

> **When to use:** After ALL due diligence is complete, BEFORE running the newsletter
> or decisions.json export. This is the final quality gate — a holistic review of
> the entire session's output against the system's stated aims.
>
> **Why this exists:** The evaluation of our Feb 28 batch caught systemic issues that
> no individual prompt could detect: all 5 passing stocks were unrelated biotech
> binaries (system drift), 3 of 5 had conviction inflate through the pipeline
> (confirmation bias), and bear cases were too easily dismissed with FDA citations.
> These are portfolio-level and process-level problems that only show up when you
> step back from individual analysis and audit the session as a whole.
>
> **What it does:** Audits theme quality, conviction trajectories, bear case rigor,
> portfolio construction, and system fit. Can REMOVE stocks from the final list,
> REDUCE sizing, or APPROVE as-is. Think of it as the Chief Risk Officer reviewing
> the portfolio manager's picks before capital is deployed.
>
> **After this prompt:** Proceed to Prompt 5 (newsletter) and Prompt 8 (decisions.json)
> with the approved set of positions. Any removals or adjustments from this review
> should be reflected in the final export.

```
We've completed due diligence on all advancing stocks. Before we lock decisions and
produce the newsletter, run a FULL SESSION REVIEW against our system's aims.

Your role shifts here. You are no longer the analyst building a bull case — you are
the Chief Risk Officer reviewing the analyst's work. Be adversarial. Find the weak
links. This review exists because the analysis pipeline has a structural tendency
toward confirmation — each stage builds on the last, and conviction tends to inflate
rather than sharpen. Your job is to catch that.

═══════════════════════════════════════════════════════════════════
REVIEW 1: SYSTEM FIT — ARE THESE THE RIGHT TRADES FOR OUR SYSTEM?
═══════════════════════════════════════════════════════════════════

Our system's edge: rare 200-700% winners from catching powerful secular themes early.
The top 5 trades = 81% of total P&L. The backtest's 79% win rate comes from extreme
selectivity, not from taking many trades.

For EACH stock that passed DD, answer honestly:

a) Is this stock riding a POWERFUL SECULAR THEME — the kind that produces multiple
   simultaneous winners across a sector? Or is it an isolated binary bet?

b) Does this setup have realistic MULTI-BAGGER potential (100%+), or is the upside
   math capped at 50-80% under the best case? Our system's edge requires occasional
   monster winners, not consistent modest gains.

c) Compare this stock to our archetypes:
   - RGTI (+705%): Quantum computing theme, multiple stocks firing, massive short
     squeeze, secular wave
   - Best historical winners: secular theme + institutional discovery + catalyst stack
   Does this session's pick share those characteristics, or is it a fundamentally
   different type of trade?

d) ARCHETYPE SCORECARD — for each stock, score against the system's historical
   winner profile:

   | Criterion | This Stock | Match? |
   |-----------|------------|--------|
   | Theme clustering (2+ stocks in same wave this session) | | Y/N |
   | Established or emerging wave alignment (from Prompt 0) | | Y/N |
   | Multiple simultaneous signals in sector (scanner found 2+ in space) | | Y/N |
   | Under-followed (≤4 analysts) | | Y/N |
   | Institutional discovery phase (broad, not just specialist accumulation) | | Y/N |
   | Short squeeze potential (>15% short interest) | | Y/N |
   | Sub-$500M market cap at entry | | Y/N |

   Archetype score: X/7

   ≤2 matches: STRONG DRIFT — this trade does not resemble our winners. Deploy only
   if individually exceptional AND user consciously accepts off-system risk.
   3-4 matches: MODERATE DRIFT — some characteristics match. Reduce sizing by one tier.
   5-7 matches: ARCHETYPE FIT — this resembles our historical edge. Deploy as analysed.

Rate each stock: ARCHETYPE FIT / MODERATE DRIFT / STRONG DRIFT with the scorecard
to support the classification.

═══════════════════════════════════════════════════════════════════
REVIEW 2: CONVICTION TRAJECTORY AUDIT
═══════════════════════════════════════════════════════════════════

For each stock, trace conviction through the pipeline:

| Stock | Gate 1 Score | Gate 2 Conviction | Gate 3 Conviction | Direction |
|-------|-------------|-------------------|-------------------|-----------|
| ...   | ...         | ...               | ...               | ↑ ↓ →     |

Flag ANY stock where conviction INCREASED from Gate 2 to Gate 3.

For each flagged stock:
- What was the SPECIFIC new finding that justified the upgrade?
- Is it a genuinely material discovery, or a restatement of the existing bull case
  with more detail?
- Would the finding change a skeptic's mind, or only confirm a believer's view?

VERDICT: Was the upgrade justified? [YES — cite the finding] or
[NO — recommend reverting to gate conviction]

═══════════════════════════════════════════════════════════════════
REVIEW 3: BEAR CASE QUALITY AUDIT
═══════════════════════════════════════════════════════════════════

For each stock, review the bear case handling across Gate 2 and Gate 3:

a) Was the bear case genuinely STEELMANNED, or was it a strawman that was easy
   to knock down?
   - Test: Would a short seller read our bear case and say "yes, that's my thesis"?
   - Or would they say "you missed the real problem entirely"?

b) Was the rebuttal DATA-DRIVEN or ASSERTION-DRIVEN?
   - Good: "Revenue grew 45% QoQ which contradicts the bear thesis of decelerating demand"
   - Bad: "The FDA granted BTD so the risk is mitigated" (citation, not data)
   - Bad: "Management is confident" (assertion, not evidence)

c) Were any bear arguments classified as "CAN'T DISMANTLE" or "PARTIALLY DISMANTLED"?
   If yes: was the conviction score appropriately reduced, or was the unresolved
   risk hand-waved away?

For each stock, rate bear case handling: RIGOROUS / ADEQUATE / WEAK
If WEAK: recommend either re-running the bear case challenge prompt or reducing
conviction by 1-2 points.

═══════════════════════════════════════════════════════════════════
REVIEW 4: PORTFOLIO CONSTRUCTION
═══════════════════════════════════════════════════════════════════

Look at the COMPLETE set of positions we're about to deploy:

a) SECTOR CONCENTRATION: What % of new capital goes to one sector?
   If >70% in one sector → recommend reducing to 50% max by dropping the weakest
   stock or cutting sizes.

b) OPPORTUNITY TYPE CONCENTRATION: How many are BINARY_CATALYST vs SECULAR_GROWTH
   vs other types? A portfolio of all binary catalysts is a casino, not a strategy.

c) CORRELATED RISK: If the WORST thing happens to one stock (sector selloff, FDA
   complete response, biotech bear market), how many other positions are hit?

d) CAPITAL DEPLOYMENT: Total % of portfolio being deployed in new positions.
   If >30% in a single session and no exceptional theme clustering exists,
   recommend holding back capital.

e) TIMING COHERENCE: Do the catalyst timelines form a coherent portfolio?
   Ideally, positions should have catalysts staggered over the next 3-18 months
   so the portfolio has ongoing re-rating events. A portfolio where all catalysts
   are 12+ months away creates dead money risk. A portfolio where all catalysts
   are within 1 month is a batch of binary bets, not a diversified book.

═══════════════════════════════════════════════════════════════════
REVIEW 5: CONTEXT CHECK — RETROSPECTIVE & MARKET ALIGNMENT
═══════════════════════════════════════════════════════════════════

Reference the retrospective (Prompt R) and market context (Prompt 0):

a) RETROSPECTIVE CALIBRATION: Are we repeating any mistakes the retrospective flagged?
   - If Prompt R noted we over-filtered recently, did we over-filter again?
   - If Prompt R noted partially dismantled bear cases are playing out, did we
     let any through this session with the same weakness?

b) MARKET REGIME: Does the regime (risk-on/off/selective) support deploying this
   much capital? If RISK-OFF or SELECTIVE: are our picks the kind of stocks that
   work in this environment, or are we fighting the tape?

c) ESTABLISHED WAVE ALIGNMENT: Do any picks align with the established waves from
   Prompt 0? If yes: clustering confirmed by external capital flows — good sign.
   If none align: not necessarily bad (we don't want consensus trades), but note it.

d) EMERGING SHIFT ALIGNMENT: Do any picks align with the emerging shifts from
   Prompt 0? If yes: this is the highest-value alignment — we may be catching a
   wave before consensus. These picks deserve the most confidence.
   If none align: our scanner may be finding signal in the wrong places, or the
   emerging shifts haven't produced technical breakouts yet (both are fine).

e) Did Prompt 0 identify emerging themes that our scanner missed entirely?
   If yes: note for future weeks. Not actionable now but signals scanner limitations.

═══════════════════════════════════════════════════════════════════
FINAL SESSION VERDICT
═══════════════════════════════════════════════════════════════════

For each stock that passed DD, issue one of:

✅ APPROVED — Deploy as planned. System fit is strong, conviction trajectory is
   clean, bear case was rigorous, portfolio construction is sound.

⚠️ APPROVED WITH ADJUSTMENTS — Deploy but with specific changes:
   "Reduce from T[X] to T[Y]" or "Reduce conviction from X to Y" or
   "Flag as higher-risk binary, not core position"

❌ REMOVE — Do not deploy. Specific reason: [system drift / conviction inflation
   not justified / bear case inadequately addressed / portfolio overconcentration /
   timing misalignment]

For removed stocks: move to WATCHLIST with trigger conditions for re-entry.

OVERALL SESSION QUALITY:
Rate this session: STRONG / ADEQUATE / WEAK
- STRONG: Advancing stocks match our system's edge profile, theme clustering exists
  or individual setups are genuinely exceptional, conviction is disciplined
- ADEQUATE: Some good picks but mixed quality, some system drift present
- WEAK: Mostly drift from system aims, recommend reducing total deployment

"If these were the ONLY positions we could hold for the next 12 months, would I be
confident they represent our system's edge? Or would I rather hold cash and wait?"

Then STOP. I may override your verdicts or ask for additional analysis before we
proceed to the newsletter and export.
```


---

# PROMPT 3B: OFF-SYSTEM EXCEPTION ANALYSIS (Probability-Weighted Price Target)

> **When to use:** After Prompt 4 (CRO Review) flags a stock as DRIFT or STRONG DRIFT
> — it passed all analytical gates but doesn't match the system's secular theme archetype.
> Also triggered when the D4 Session-Level Theme Alignment Gate classified the session as
> WEAK and you chose option (a): proceed with the strongest setup at reduced size.
>
> Use this when you believe the individual setup is compelling enough to justify deploying
> capital off-system. This prompt produces a probability-weighted 12-month price target
> to make the exception decision rigorous rather than emotional.
>
> **Why this exists:** The theme alignment gates (D1, D4, CRO Review 1) correctly filter
> stocks that don't match our archetype. Those gates should NOT be weakened — they protect
> the system's edge. But occasionally a stock with genuinely exceptional asymmetry surfaces
> where refusing to act is itself a risk. This prompt creates a structured path to approve
> those exceptions. The bar is deliberately higher than standard DD: an off-system exception
> must clear a probability-weighted expected return hurdle well above the standard pipeline's
> 50%+ threshold, because we're deploying capital that could otherwise wait for a theme-
> aligned opportunity with historical edge.
>
> **Three-part sequential design:** Each part is a SEPARATE MESSAGE. Run Part A, review,
> then paste Part B, review, then paste Part C. This gives each stage full thinking
> budget and lets you course-correct between stages. The methodology is adapted from our
> content deep dive approach (5-stage sequential analysis) for internal decision-making.
>
> | Part | Purpose | Recommended Mode |
> |------|---------|-----------------|
> | **A: Data Foundation** | Broad data gathering (15-20+ sources) | **Research mode** (preferred) or Extended Thinking with aggressive search |
> | **B: Forward Model & Valuation** | Revenue projections, margin model, 4-method valuation triangulation | **Extended Thinking** — needs full reasoning budget |
> | **C: Scenario Synthesis & Verdict** | Probability-weighted scenarios, sensitivity testing, exception score | **Extended Thinking** — adversarial judgment |
>
> **Context:** The stock has already passed Prompt 1, 2, and 3. You have the full thematic
> analysis, gate assessment, and deep DD in conversation memory (or pasted in). This prompt
> BUILDS ON that work — it does not repeat it.
>
> **Output:** A concrete APPROVED / CONDITIONAL / DENIED verdict with an EXCEPTION SCORE
> (1-10), probability-weighted 12-month price target, and explicit off-system risk
> acknowledgment. If approved, position is capped at T3 (25% standard size) regardless
> of conviction — this is a structural constraint, not negotiable.

## Part A: Data Foundation (Message 1 of 3)

> **Mode:** Research mode (preferred) or Extended Thinking with thorough web search.
> This part is pure data gathering — broad, cross-referenced, primary-source focused.
> Present data without synthesising into a recommendation; that happens in Parts B and C.

```
[TICKER] passed our analytical pipeline (conviction [X]/10 at DD) but was flagged
as [DRIFT / STRONG DRIFT / WEAK SESSION] because [1-sentence reason — e.g.,
"isolated biotech binary with zero theme alignment to identified waves"].

I want to evaluate whether the individual setup justifies an off-system exception.
Before we build scenarios, I need a comprehensive data foundation. Research the
following — prioritise PRIMARY sources (SEC filings, company presentations, peer-
reviewed data, ClinicalTrials.gov) over secondary commentary.

═══════════════════════════════════════════════════════════════════
PHASE 0: FINANCIAL BASELINE (trailing data for forward model)
═══════════════════════════════════════════════════════════════════

Search for the most recent 10-Q/10-K, earnings releases, and investor presentations.
Compile:

1. TRAILING 8-QUARTER REVENUE broken out by business segment (or pipeline stage
   if pre-revenue). Present as a table showing the trend.
2. GROSS MARGIN, OPERATING MARGIN, and NET MARGIN for each of those 8 quarters.
   Flag any inflection points (margin expansion/compression).
3. FREE CASH FLOW for the trailing 4 quarters. Is FCF trending toward positive?
4. CURRENT SHARES OUTSTANDING and net change over 12 months (dilution trend).
5. TOTAL DEBT, CASH POSITION, and any debt maturing within 18 months.
6. CURRENT STOCK PRICE (web search for live quote).
7. SHORT INTEREST as percentage of float (current + 3-month trend).

If pre-revenue company: report cash burn rate per quarter, pipeline milestones
achieved in last 12 months, and any revenue (grants, licensing, collaboration
payments) even if immaterial.

Present as structured tables. Flag any data you cannot find with "[NOT FOUND]".
This baseline anchors Part B's forward projections.

═══════════════════════════════════════════════════════════════════
PHASE 1: VALUATION ANCHORS
═══════════════════════════════════════════════════════════════════

1. ANALYST LANDSCAPE
   Search: "[ticker] analyst price targets 2025 2026"
   Search: "[ticker] analyst initiations upgrades downgrades"
   - List ALL current analyst ratings, price targets, and dates of last update
   - Identify the HIGHEST and LOWEST targets — who are they and what assumptions
     drive the gap between them?
   - Any recent initiations or target changes in the last 30 days?
   - Consensus revenue/earnings estimates for the next 4 quarters (if applicable)
   - How many analysts cover this stock? (≤3 = under-followed signal)

2. COMPARABLE COMPANY ANALYSIS
   Search: "[ticker] comparable companies peers valuation"
   Search: "[closest competitor] market cap revenue valuation multiples"
   - Identify 3-5 closest public comparables by business model, stage, and market
   - For each comp: market cap, EV, revenue (or pipeline stage), key multiple
     (EV/Revenue, EV/EBITDA, Price/Book, or market cap / TAM penetration for
     pre-revenue companies)
   - Where does [TICKER] sit relative to peers? Premium, discount, or in-line?
   - If significant discount: is it justified (worse execution, higher risk) or
     a genuine mispricing?
   - If pre-revenue: what market cap did comps trade at when they were at an
     equivalent pipeline stage?

3. PRECEDENT TRANSACTIONS
   Search: "[sector] M&A acquisitions premiums 2024 2025 2026"
   Search: "[ticker] acquisition target buyout rumor"
   - Any M&A activity in this space in the last 24 months?
   - At what multiples or premiums were deals done?
   - Is [TICKER] a plausible acquisition target? Who would be the logical acquirer?
   - What would an acquirer likely pay based on precedent multiples?
   - This establishes a FLOOR for the bull scenarios and informs downside support

4. CASH-ADJUSTED VALUATION
   Search: "[ticker] 10-Q cash balance shares outstanding"
   - Cash and equivalents (most recent quarter-end)
   - Total debt and net cash position
   - Net cash per share vs current stock price
   - Enterprise value at current price
   - Cash runway (quarters at current burn rate)
   - Forthcoming dilution: warrants (with exercise prices), convertible notes
     (conversion prices), ATM facility (remaining capacity), stock options
     with estimated diluted share count

═══════════════════════════════════════════════════════════════════
PHASE 2: CATALYST MAPPING WITH BASE RATES
═══════════════════════════════════════════════════════════════════

For each catalyst over the next 12 months:
   Search: "[ticker] upcoming catalysts milestones events 2026"
   Search: "[ticker] clinical trial results FDA timeline" (if biotech)
   Search: "[ticker] earnings guidance contract pipeline" (if commercial)

For EACH identified catalyst, research:
   a) WHAT: Specific event description
   b) WHEN: Exact date or narrowest possible window (not "H2 2026")
   c) HISTORICAL BASE RATE: The general success rate for this type of event —
      NOT a guess. Find the data:
      - FDA approval rates by therapeutic area and phase (search: "FDA
        approval probability by phase [indication]")
      - Clinical trial success rates by phase and indication
      - Contract win rates in the relevant industry
      - Revenue beat/miss rates for this company and its peers
   d) COMPANY-SPECIFIC ADJUSTMENTS: What makes THIS company's probability
      higher or lower than the base rate? (Prior data, mechanism of action
      differentiation, regulatory interactions, competitive positioning)
   e) STOCK PRICE IMPACT: Based on comparable precedents, how much does a stock
      in this space typically move on this type of catalyst — both on success
      AND on failure? Find 3-5 comparable events and their stock reactions.

═══════════════════════════════════════════════════════════════════
PHASE 3: INSTITUTIONAL POSITIONING
═══════════════════════════════════════════════════════════════════

Search: "[ticker] 13F institutional ownership changes"
Search: "[ticker] insider buying selling Form 4"
Search: "[ticker] short interest shares short days to cover"

   a) TOP 10 institutional holders — position sizes and quarter-over-quarter changes
   b) Are SECTOR SPECIALISTS accumulating or distributing? (Name the funds and
      their focus — index fund inclusions and quant rebalancing don't count as
      conviction signals)
   c) Any activist positions or 13D/13G filings?
   d) Insider transactions in the last 6 months — net buyer or seller? Dollar
      magnitude relative to compensation?
   e) Short interest: current level, 3-month trend, days to cover
   f) Cost to borrow (if findable) — elevated borrow cost signals short conviction

═══════════════════════════════════════════════════════════════════
PHASE 4: ADDRESSABLE MARKET REALITY CHECK
═══════════════════════════════════════════════════════════════════

Search: "[company's target market] total addressable market size"
Search: "[company's target market] market share competition"

   a) BOTTOMS-UP TAM: Build from unit economics, not top-down "the market is
      $X billion." For biotech: prevalence × diagnosis rate × treatment-eligible %
      × expected price × realistic market share. For tech/industrial: customer
      count × contract value × win rate × retention.
   b) PEAK REVENUE ESTIMATE: What is realistic peak revenue if the thesis works?
      What penetration rate does that assume? Is that penetration achievable given
      competition?
   c) TIMELINE TO PEAK: How many years from today to peak revenue?
   d) COMPETITIVE LANDSCAPE: Who else is going after the same TAM? What market
      share is realistic for [TICKER] given the competitive set?
   e) TAM RISK: What could SHRINK the TAM? (Competing modalities, price pressure,
      regulatory changes, generics/biosimilars timeline)

═══════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════

Present all data in structured format with source attribution. Flag any data points
where sources conflict, where data is stale (>6 months old), or where you have low
confidence. Distinguish between hard data (SEC filings, trial results) and estimates
(analyst projections, market size forecasts).

Do NOT synthesise into recommendations yet — that happens in Part B. The goal of
Part A is an honest, comprehensive data foundation. If the data paints a weaker
picture than the DD suggested, that's valuable — say so.

Then STOP. I'll review the data foundation before we proceed to scenario modelling.
```

## Part B: Forward Model & Valuation Triangulation (Message 2 of 3)

> **Mode:** Extended Thinking (Opus 4.6 with extended thinking ON). This part requires
> deep analytical reasoning to build forward projections and triangulate valuation using
> multiple methods. All Part A data should be in conversation memory.

```
Using the data foundation from Part A, build a forward financial model and
independent valuation for [TICKER]. Do NOT anchor to analyst price targets —
build your own from the data.

═══════════════════════════════════════════════════════════════════
STAGE 1: FORWARD REVENUE BUILD (next 12 months)
═══════════════════════════════════════════════════════════════════

Starting from the TRAILING 8-QUARTER REVENUE baseline in Part A Phase 0,
project forward. For each revenue segment identified in Part A:
- Announced contracts, partnerships, or deals with revenue implications
- Product launches, regulatory milestones, or expansion initiatives
- Pricing actions, ASP/ARPU trends, or reimbursement changes
- Customer/patient pipeline and conversion trends
- Known headwinds (competition, patent cliffs, regulatory risk)

Produce LOW / MID / HIGH revenue estimates for the next 4 quarters.
Every assumption must cite a source from Part A or a new search.
If pre-revenue: estimate probability-weighted revenue onset timeline
and first-year revenue range based on comparable launches.

| Quarter | Segment A | Segment B | Total LOW | Total MID | Total HIGH |
|---------|-----------|-----------|-----------|-----------|------------|
| Q[next] | | | | | |
| Q+1 | | | | | |
| Q+2 | | | | | |
| Q+3 | | | | | |

═══════════════════════════════════════════════════════════════════
STAGE 2: MARGIN & EARNINGS PROJECTION
═══════════════════════════════════════════════════════════════════

Project for BEAR / BASE / BULL scenarios, using Part A Phase 0 trailing
margins as the starting baseline:
- Gross margins (using trailing trend + known mix shift or scale effects)
- Operating margins (R&D trajectory, SG&A leverage, one-time costs)
- EPS (using diluted share count from Part A, including warrant/convert dilution)
- Free cash flow per share
- Cash runway under each scenario (quarters until cash-flow positive or
  quarters until additional funding needed)

If pre-revenue biotech or early-stage: project cash burn trajectory and
funding gap. When would the company need to raise? At what dilution?

═══════════════════════════════════════════════════════════════════
STAGE 3: VALUATION TRIANGULATION (4 methods)
═══════════════════════════════════════════════════════════════════

Apply ALL FOUR methods. Each produces BEAR / BASE / BULL targets:

METHOD A — HISTORICAL MULTIPLE RANGE:
Using the company's own 3-5 year trading history (P/E, EV/Revenue,
EV/EBITDA — whichever is most applicable), apply the historical range
to your forward earnings/revenue estimates. Where has the stock traded
during comparable growth periods?

METHOD B — DCF (Discounted Cash Flow):
Using your FCF projections from Stage 2. Discount rate = current 10-year
Treasury + equity risk premium (5-6% for established small-cap, 8-10%
for pre-revenue/speculative). Terminal growth 2-3%. Show the math.
If pre-revenue: use risk-adjusted NPV of pipeline (rNPV) instead.

METHOD C — PEER-RELATIVE VALUATION:
Using the comps from Part A. Apply peer median and best-in-class multiples
to your forward estimates. Where SHOULD this stock trade relative to its
peer set, given relative growth rate, margins, and risk profile?

METHOD D — CATALYST-ADJUSTED VALUATION:
For each catalyst from Part A Phase 2, calculate:
- Probability of success (from base rates)
- Stock price impact on success (from comparable precedents)
- Stock price impact on failure
- Probability-weighted catalyst contribution to 12-month target

Sum: Current price + Σ(probability × impact) for each catalyst.

═══════════════════════════════════════════════════════════════════
STAGE 4: SYNTHESIS
═══════════════════════════════════════════════════════════════════

| Method | Bear Target | Base Target | Bull Target | Weight |
|--------|------------|-------------|-------------|--------|
| A: Historical Multiple | $XX | $XX | $XX | XX% |
| B: DCF / rNPV | $XX | $XX | $XX | XX% |
| C: Peer-Relative | $XX | $XX | $XX | XX% |
| D: Catalyst-Adjusted | $XX | $XX | $XX | XX% |
| **WEIGHTED** | **$XX** | **$XX** | **$XX** | **100%** |

Weight each method by appropriateness for THIS company type:
- Revenue-stage company: weight Historical Multiple and Peer-Relative higher
- Pre-revenue biotech: weight Catalyst-Adjusted and DCF/rNPV higher
- Transitional (early revenue): weight all roughly equally

Flag the 3 ASSUMPTIONS MOST LIKELY TO BE WRONG. These drive the scenario
spread in Part C.

Then STOP. I'll review the valuation model before we proceed to scenario
synthesis and the exception verdict.
```

## Part C: Scenario Synthesis & Exception Verdict (Message 3 of 3)

> **Mode:** Extended Thinking (Opus 4.6 with extended thinking ON). This requires
> complex probabilistic reasoning, adversarial scenario construction, and the final
> exception judgment. Parts A and B should be in conversation memory.

```
Using the data foundation (Part A) and valuation model (Part B), build the
probability-weighted 12-month price target and exception verdict for [TICKER].

═══════════════════════════════════════════════════════════════════
STEP 1: SCENARIO CONSTRUCTION
═══════════════════════════════════════════════════════════════════

Build exactly 5 discrete scenarios. They must be MUTUALLY EXCLUSIVE and
COLLECTIVELY EXHAUSTIVE — probabilities must sum to 100%.

For each scenario, derive (do not guess):
- TRIGGER: The specific event(s) that cause this outcome
- 12-MONTH PRICE TARGET: Derive from Part B's valuation triangulation.
  State WHICH valuation method anchors this scenario's target and why.
- PROBABILITY: Anchor to historical BASE RATES from Part A Phase 2, then
  adjust for company-specific factors. Show the chain of reasoning.

THE FIVE SCENARIOS:

1. MONSTER BULL (everything right + market discovers the stock)
   All key catalysts succeed. Multiple expansion to peer-comparable levels.
   Ceiling = Part B Method C best-in-class peer multiple applied to Part B
   Stage 1 HIGH revenue estimate.

2. BULL (primary catalyst succeeds, modest re-rating)
   Main thesis plays out. Stock re-rates toward Part B weighted BASE target.

3. BASE (mixed results, stock drifts)
   Some catalysts hit, some miss or slip. No dramatic re-rating. Anchored to
   Part B Stage 1 MID revenue × current multiple (no expansion).

4. BEAR (primary catalyst fails or disappoints)
   The main risk materialises. Stock sells off to Part B Method A historical
   trough multiple × LOW revenue, or Part A cash-adjusted floor — whichever
   is higher.

5. CATASTROPHIC (thesis destroyed)
   Worst realistic outcome. Stock trades to net cash value or below.

CALIBRATION CHECK — apply before proceeding:
- Monster Bull: 5-15%. If >20%, you're overweighting best-case.
- Catastrophic: 5-15%. If <5%, you're underweighting tail risk.
- Base case: Highest single probability (25-40%).
- Bull + Bear: Most of the remaining probability.
- Total: Must equal exactly 100%.
- SANITY CHECK: Would you bet real money at these probabilities?

═══════════════════════════════════════════════════════════════════
STEP 2: EXPECTED VALUE CALCULATION
═══════════════════════════════════════════════════════════════════

CURRENT PRICE: $[X.XX] (use live price from web search)

| Scenario | 12mo Target | Return | Probability | Weighted Return |
|----------|------------|--------|-------------|-----------------|
| Monster Bull | $XX.XX | +XXX% | XX% | +XX.X% |
| Bull | $XX.XX | +XXX% | XX% | +XX.X% |
| Base | $XX.XX | +XX% | XX% | +XX.X% |
| Bear | $XX.XX | -XX% | XX% | -XX.X% |
| Catastrophic | $XX.XX | -XX% | XX% | -XX.X% |
| **TOTAL** | | | **100%** | **+XX.X%** |

PROBABILITY-WEIGHTED 12-MONTH PRICE TARGET: $XX.XX (+XX% from current)

SKEW PROFILE:
- P(>100% return): XX% — multi-bagger probability
- P(>50% return): XX% — strong win probability
- P(>0% return): XX% — probability of any positive outcome
- P(>30% loss): XX% — probability of significant drawdown
- Upside/downside ratio: (weighted upside scenarios) / |weighted downside scenarios|

═══════════════════════════════════════════════════════════════════
STEP 3: SENSITIVITY ANALYSIS
═══════════════════════════════════════════════════════════════════

Test how robust the expected return is to probability estimation error:

a) PESSIMISTIC SHIFT: Move 10 percentage points from Bull → Bear AND 5 points
   from Monster Bull → Catastrophic. Recalculate expected return.

b) OPTIMISTIC SHIFT: Move 10 points from Bear → Bull AND 5 points from
   Base → Monster Bull. Recalculate expected return.

c) PRIMARY CATALYST FAILURE: If the single most important catalyst FAILS
   (move all its success probability to Bear/Catastrophic), what is the residual
   expected return from remaining catalysts and base case alone?

d) MULTIPLE COMPRESSION: If ALL scenarios get 20% lower price targets (market
   de-rates the sector), what happens to expected return?

ROBUSTNESS VERDICT:
- If expected return goes NEGATIVE under pessimistic shift → NOT ROBUST
- If expected return stays >25% under pessimistic shift → ROBUST

═══════════════════════════════════════════════════════════════════
STEP 4: EXCEPTION SCORE & VERDICT
═══════════════════════════════════════════════════════════════════

EXCEPTION CHECKLIST — higher bar than standard pipeline because we're deploying
capital outside our demonstrated edge:

| # | Check | Result | Pass? |
|---|-------|--------|-------|
| 1 | Probability-weighted expected return >75% | +XX% | Y/N |
| 2 | Expected return stays POSITIVE under pessimistic shift | +XX% | Y/N |
| 3 | P(>50% return) exceeds 35% | XX% | Y/N |
| 4 | P(>30% loss) is below 35% | XX% | Y/N |
| 5 | Upside/downside ratio exceeds 2.5:1 | X.X:1 | Y/N |
| 6 | Residual EV positive even if primary catalyst fails | +XX% | Y/N |
| 7 | Robust under 20% multiple compression | +XX% | Y/N |

EXCEPTION SCORE (1-10):
Convert the checklist results into a single score for direct comparison with
the system's standard conviction scale:

| Checks Passed | Exception Score | Verdict |
|---------------|----------------|---------|
| 7/7 + expected return >100% | 9-10 | EXCEPTION APPROVED — exceptional asymmetry |
| 7/7 + expected return 75-100% | 8 | EXCEPTION APPROVED — strong off-system setup |
| 5-6/7, no critical failures | 6-7 | CONDITIONAL EXCEPTION — deploy with caution |
| 5-6/7, check 1 or 2 failed | 4-5 | EXCEPTION DENIED — math doesn't survive stress test |
| ≤4/7 | 1-3 | EXCEPTION DENIED — does not meet off-system hurdle |

CRITICAL CHECKS: If check 1 (expected return >75%) or check 2 (positive under
pessimistic shift) fails, the exception is DENIED regardless of other checks.
These are non-negotiable — an off-system trade that doesn't clear the higher
hurdle or isn't robust to probability error has no business receiving capital.

═══════════════════════════════════════════════════════════════════
FINAL OUTPUT
═══════════════════════════════════════════════════════════════════

EXCEPTION VERDICT: [APPROVED / CONDITIONAL / DENIED]
EXCEPTION SCORE: X/10

If APPROVED or CONDITIONAL (score 6+):
- PROBABILITY-WEIGHTED 12-MONTH TARGET: $XX.XX (+XX%)
- EXPECTED RETURN: +XX% (vs 75% off-system hurdle)
- POSITION: T3 (25% standard size) — NON-NEGOTIABLE for off-system exceptions
- ENTRY: $XX.XX (specific level)
- STOP: $XX.XX (set at Bear scenario floor, NOT Catastrophic floor)
- HOLD PERIOD: X months to [primary catalyst date]
- OFF-SYSTEM LABEL: This position is flagged as an off-system exception trade.
  It does not match our system's archetype. It is sized at T3 because our edge
  here is individual setup quality, not theme momentum. Monitor more closely than
  core positions. If a theme-aligned opportunity emerges that requires this
  capital, this position is FIRST to be trimmed or closed.
- KILL SWITCH: [Specific, measurable trigger for immediate exit]
- MONITORING CADENCE: Review weekly (vs bi-weekly for core positions)

If DENIED (score ≤5):
- WHY: Specifically which checks failed and by how much
- WATCHLIST: With specific price level or catalyst trigger that would flip verdict
  (e.g., "Re-run 3B if stock pulls back to $X or if [catalyst] data reads out")
- CAPITAL PRESERVATION: "Preserve capital for a theme-aligned session. Current
  themes to watch for scanner signals: [list 2-3 from Prompt 0 emerging shifts]"

Then STOP. I'll review the scenario model and either approve the exception,
challenge the probabilities, or accept the denial.
```

---

# PROMPT 5: NEWSLETTER (HTML)

> **When to use:** After finalizing your investment decisions, generate the
> subscriber-facing weekly newsletter as a complete HTML document. This is the
> Sunday "Performance Review" post on Substack.
>
> **Output:** A self-contained HTML file you save as `newsletter.html` in your repo.
> The Saturday workflow copies it to the correct output directories.

```
Based on our analysis session, produce the weekly Sterling Signals newsletter as a
complete, self-contained HTML document.

Use the decisions we made in this session for all content.

FRESHNESS CHECK: Use web search to get current prices for:
- SPY, QQQ, IWM — current price and weekly/YTD performance
- VIX current level
- Any portfolio positions we discussed — recalculate P&L if prices moved

═══════════════════════════════════════════════════════════════════
MARKETING RULES (FOLLOW EXACTLY)
═══════════════════════════════════════════════════════════════════

Signal branding: "GREEN signal" for buy signals. NEVER use: TEAL, PASS, VIOLET,
AMBER, STRONG BUY, BUY (as a verdict label), SPEC BUY, NO GO.

Banned terms: HMA, Banker, UC, Undercurrent, BoS, RSI, MACD, KDJ, ExD, VWAP,
Gatekeeper, Investment Gate, Deep DD, 5-gate, Tier 1/2/3, conviction scores,
price cap, kill switch, valuation regime.

Approved alternatives:
- System: "proprietary screening system", "our screening system"
- Entry: "momentum confirmed", "structural pivot confirmation"
- Accumulation: "institutional accumulation divergence"
- Exit: "systematic exit discipline"
- Signal branding: "GREEN signal" (buys), "system exit" (sells)
- Conviction: "Extremely Bullish" / "Bullish" / "Watching" — NEVER numbers

Entry price display:
- 25%+ gain: Can show entry price
- 15%+ gain: Can show P&L percentage, no entry price
- Under 15%: Do not highlight or showcase
- Losses: NEVER mention. No negative percentages. No "stopped out", "down",
  "underperformed", "loser", "bleeding", "dragging down".

═══════════════════════════════════════════════════════════════════
NEWSLETTER STRUCTURE (1,200-1,500 words)
═══════════════════════════════════════════════════════════════════

1. Market Context — What happened in markets this week. 2-3 sentences with fresh
   search data (SPY/QQQ/IWM performance, VIX, key events).

2. What Our Scanner Found — The screening funnel. How many scanned → passed →
   theme-confirmed → GREEN signals. Frame rejection rate as proof of selectivity.
   Include [SCAN_FUNNEL] placeholder.

3. Themes Driving Momentum — Top 2-3 themes from our analysis. What's hot,
   what's cooling, where is capital flowing. Include [THEME_SCORES] placeholder.

4. New GREEN Signals — For each BUY from our session:
   - The pitch, theme alignment, why it cleared our screening
   - Include [CHART: TICKER] placeholder for each
   If no signals: "Why We Passed" section on disciplined selectivity.

5. Portfolio Performance — Showcase winners (15%+ only). Performance vs SPY and
   QQQ using fresh benchmark data. Alpha generated. Include [WINNERS_TABLE]
   placeholder.

6. Looking Ahead — 3-5 specific catalysts, earnings, or events for next week
   (use web search to find these).

7. Footer — "Subscribe to Sterling Signals for the full weekly analysis:
   https://sterlingsignals.substack.com"

═══════════════════════════════════════════════════════════════════
HTML FORMAT — DASHBOARD THEME
═══════════════════════════════════════════════════════════════════

Produce a complete self-contained HTML document with ALL styles in a <style> block.
Use the Dashboard theme:

- Dark background: #111827 | Card bg: #1F2937 | Max-width: 680px
- Accent: teal #2DD4BF | Green: #22C55E | Amber: #FBBF24 | Red: #EF4444
- Text: #F9FAFB | Muted: #9CA3AF | Dim: #6B7280
- Borders: #374151 | Header bg: #0F172A
- Font: system sans-serif throughout (-apple-system, BlinkMacSystemFont, 'Segoe UI',
  Roboto, Arial, sans-serif)
- Teal highlight bg: #0D3B34

Components to use: gradient hero section, stat grids, theme cards with progress bars,
funnel steps, winners tables, cards, pullquotes.

Tone: Confident and direct. Like a weekly briefing from a trusted analyst.
No hedging, no "it remains to be seen." Every claim backed by a number.
```

---

# PROMPT 6: SELL SIGNAL REVIEW

> **When to use:** When your scanner flags ExD (exit) signals on held positions,
> or you want to review current holdings.

```
Review these positions for potential exits:

CURRENT HOLDINGS:
[PASTE: ticker, entry price, current price, return %, entry date, original thesis,
any ExD signals from scanner]

For each position:

1. THESIS CHECK: Is the original investment thesis still intact?
   Search: "[ticker] latest news developments 2025/2026"
   - Has anything materially changed since entry?
   - Is the catalyst still on track?

2. TECHNICAL SIGNAL: Our scanner is flagging [ExD signal / trailing stop / no signal].
   - ExD (HMA pivot high + UC falling) = systematic exit signal
   - Trailing stop hit = mechanical exit
   - No signal = hold

3. REGIME CHECK: Has the valuation regime shifted?
   - Did OPTIONALITY become TRANSITION? (regime shift risk)
   - Did FUNDAMENTAL revisions turn negative?

4. RECOMMENDATION for each:
   - HOLD: Thesis intact, no exit signal, catalyst still ahead
   - TRIM: Partial exit — thesis intact but risk increasing or overweight
   - EXIT: Full exit — thesis broken, exit signal confirmed, or target reached
   - Specific: "EXIT [TICKER] at open Monday. Reason: [specific]"

For any EXIT recommendation, also say:
- Was this a WIN or LOSS?
- What did we learn? (Would we have entered differently in hindsight?)
- Should it go on the watchlist for re-entry later?
```

---

# PROMPT 7: MID-WEEK CATALYST CHECK

> **When to use:** Mid-week between scans to check if held positions have
> upcoming events that require attention.

```
Quick catalyst check on my current holdings. For each, search for events in the
next 10 trading days that could cause significant moves:

HOLDINGS:
[PASTE: ticker list with entry prices]

For each, search: "[ticker] earnings date catalyst upcoming events"

Flag ANY of these:
- Earnings in next 10 trading days
- FDA decisions, trial readouts
- Lock-up expirations
- Conference presentations
- Insider transaction deadlines
- Offering pricing windows

For each flagged event:
- Date
- Expected impact (positive/negative/unknown)
- Recommendation: Hold through / Trim before / Exit before

Only flag material events. Don't list routine items.
```

---

# PROMPT 8: STRUCTURED EXPORT (decisions.json)

> **When to use:** At the END of every analysis session, after all decisions are final.
> This produces the structured JSON that your Saturday workflow reads to update the
> portfolio, generate signals.json, and build the weekly Substack schedule.
>
> **CRITICAL:** This prompt must run AFTER Prompt 4 (and Prompt 3B if triggered).
> The Saturday workflow treats every stock in `new_positions` as a confirmed buy and
> adds it to the portfolio automatically — there is no second check. If Prompt 4
> removed a stock, it MUST NOT appear in `new_positions`. The reconciliation step
> at the top of this prompt enforces this, but you should also verify the output.
>
> **Note:** The Substack content schedule is generated AUTOMATICALLY by
> `content_production_guide.py` from your repo data (portfolio, themes, signals).
> You do NOT generate it in chat — the repo has full history context that chat lacks.
> Similarly, the newsletter HTML was already produced by Prompt 5.

```
We've finalized our analysis. Now produce the structured decisions.json export.

═══════════════════════════════════════════════════════════════════
MANDATORY: PROMPT 4 RECONCILIATION (do this BEFORE generating JSON)
═══════════════════════════════════════════════════════════════════

Before writing any JSON, review the Prompt 4 (Portfolio Review Gate) output from
this session. Build two explicit lists:

APPROVED FOR DEPLOYMENT (go into "new_positions"):
- Only stocks that Prompt 4 APPROVED or APPROVED WITH ADJUSTMENTS
- If Prompt 4 adjusted sizing (e.g., reduced from T2 to T3), use the ADJUSTED
  values, not the original Prompt 3 values
- If a stock went through Prompt 3B (off-system exception) and was APPROVED or
  CONDITIONAL, include it with off_system_exception: true
- If Prompt 4 was not run (should never happen), STOP and flag this

REJECTED / REMOVED (go into "no_go"):
- Stocks removed by Prompt 4 → stage_rejected: "review_gate"
- Stocks denied by Prompt 3B → stage_rejected: "exception_denied"
- Stocks filtered at thematic (Prompt 1) → stage_rejected: "thematic"
- Stocks filtered at gate (Prompt 2) → stage_rejected: "gate"
- Stocks filtered at DD (Prompt 3) → stage_rejected: "dd"

State both lists explicitly before generating JSON. Example:
"APPROVED: TICK1 (T2, conviction 8), TICK2 (T3, conviction 7, off-system exception)
 REJECTED: TICK3 (removed by Prompt 4 — system drift), TICK4 (filtered at gate —
 dilution DQ), TICK5 (3B exception denied — failed checks 1 and 2)"

If a stock appears in review_gate.stocks_removed, it MUST NOT appear in
new_positions. This is the rule that prevents the NGNE bug — a stock rejected
by the CRO must never flow through to the Saturday workflow as a confirmed buy.

═══════════════════════════════════════════════════════════════════

Generate ONLY valid JSON (no markdown fences, no commentary). I'll paste this directly
into my repo as scanner/output/decisions.json.

{
  "scan_date": "YYYY-MM-DD",
  "scan_week_ending": "YYYY-MM-DD",
  "market_regime": "risk_on|risk_off|selective",
  "market_context_summary": "2-3 sentences on the intermediate-term market environment for our 6-18 month holds",

  "retrospective": {
    "open_positions_total": 3,
    "thesis_intact": 2,
    "thesis_weakening": 1,
    "thesis_broken": 0,
    "recently_closed": [{"symbol": "TICKER_A", "pnl_pct": 45, "held_months": 4, "thesis_correct": true}],
    "notable_filter_misses": ["TICKER_Z rallied 65% over 6 weeks on identified catalyst"],
    "notable_filter_validations": ["TICKER_W dropped 30% confirming bear case"],
    "calibration_notes": [
      "Over-filtered standalone setups in emerging themes recently — apply Override more liberally",
      "Partially dismantled bear cases playing out on recent losers — treat closer to CAN'T DISMANTLE"
    ]
  },

  "market_context": {
    "regime": "risk_on|risk_off|selective",
    "regime_outlook_months": "6-18 month assessment",
    "economic_trajectory": "expanding|stable|contracting",
    "fed_rate_path": "easing|holding|tightening",
    "earnings_cycle": "accelerating|stable|decelerating",
    "small_cap_environment": "favorable|neutral|headwind",
    "small_cap_3m_trend": "IWM 3-month relative performance vs SPY",
    "sectors_accelerating": ["sector1 — structural driver", "sector2"],
    "sectors_decelerating": ["sector3", "sector4"],
    "established_waves": ["theme1 — consensus, multi-month trend", "theme2"],
    "emerging_shifts": ["theme1 — pre-consensus, structural driver + evidence", "theme2"],
    "deployment_implication": "Given 3-18 month holds, capital deployment is [aggressive/normal/cautious] because [reason]"
  },

  "batch_assessment": {
    "theme_clustering": "detected|none",
    "theme_clustering_detail": "X tickers in Y theme, or 'N isolated micro-themes'",
    "wave_alignment": "X tickers align with active waves from market context",
    "sector_concentration": "X% in sector Y",
    "sector_concentration_warning": true,
    "batch_quality": "STRONG|MIXED|WEAK",
    "batch_quality_rationale": "1-sentence honest assessment"
  },

  "review_gate": {
    "session_quality": "STRONG|ADEQUATE|WEAK",
    "session_quality_rationale": "1-sentence assessment",
    "stocks_approved": ["TICKER1", "TICKER2"],
    "stocks_adjusted": [
      {
        "symbol": "TICKER",
        "adjustment": "Reduced from T2 to T3",
        "reason": "System drift — isolated binary, not riding a wave"
      }
    ],
    "stocks_removed": [
      {
        "symbol": "TICKER",
        "reason": "Conviction inflation not justified — no material new finding at DD",
        "moved_to": "watchlist"
      }
    ],
    "conviction_inflation_detected": false,
    "bear_case_quality": "RIGOROUS|ADEQUATE|WEAK",
    "portfolio_construction_notes": "Any sector/type concentration concerns",
    "market_alignment": "swimming_with_current|swimming_against_current|neutral"
  },

  "new_positions": [
    {
      "symbol": "TICKER",
      "action": "BUY",
      "verdict": "STRONG BUY|BUY|SPEC BUY",
      "conviction": 8,
      "tier": "T1|T2|T3",
      "quality_tier": 1,
      "price": 14.50,
      "stop_price": 11.60,
      "position_size": "FULL|REDUCED",
      "position_size_pct": 0.20,

      "theme": "Specific micro-theme name",
      "theme_score": 7.8,
      "theme_classification": "PRIME|INVESTABLE",
      "theme_verdict": "STRONG FIT|GOOD FIT",
      "system_fit": "STRONG|MODERATE|POOR",
      "system_fit_reason": "1-sentence reason for fit assessment",
      "opportunity_type": "SECULAR_GROWTH|BINARY_CATALYST|CYCLICAL_RECOVERY|SPECIAL_SITUATION|MOMENTUM_CATCHUP",
      "valuation_regime": "FUNDAMENTAL|OPTIONALITY|TRANSITION",

      "gate_verdict": "STRONG_BUY|BUY|SPEC_BUY",
      "gate_conviction": 8,
      "catalyst_summary": "Specific catalyst with date",
      "red_flag_level": "CLEAN|MINOR",
      "dilution_check": "CLEAN|CAUTION|DQ",
      "dilution_detail": "Shares outstanding change and warrant status",
      "gate_bear_case": "1-sentence bear case",
      "gate_bear_classification": "DISMANTLED|PARTIALLY_DISMANTLED|CANT_DISMANTLE",
      "gate_math": "Path to 50%+",
      "entry_timing_verdict": "CLEAN|ELEVATED|CHASING|POOR_TIMING",
      "entry_timing_detail": "Up X% from pivot, catalyst in Y weeks",
      "exceptional_override": false,
      "exceptional_override_criteria": "Which 4 criteria were met, or empty if not applicable",

      "dd_verdict": "STRONG BUY|BUY|SPEC BUY",
      "dd_conviction": 8,
      "dd_conviction_change": "INCREASED|SAME|DECREASED",
      "dd_conviction_change_reason": "Specific new finding or risk that shifted conviction",
      "dd_elevator_pitch": "2-3 sentences from our DD",
      "dd_why_now": "Key catalyst with date",
      "dd_the_math": "Regime-adapted path to 50%+",
      "dd_bear_case": "Steelmanned bear argument",
      "dd_risk_to_monitor": "Single most important risk",
      "dd_action": "Specific: Enter at ~$X, T1 full position, stop at $Y",
      "dd_hold_thesis": "Expected hold 6-12mo. Key milestones: [catalyst1 in Q2, catalyst2 in Q4]",
      "dd_key_catalyst": "Primary catalyst driving the trade",
      "dd_fatal_flaw": "",

      "variant_perception": "What we see that consensus misses",
      "key_assumption": "The ONE thing that must be true",
      "kill_switch": "What triggers early exit",
      "downside_floor": "Where value buyers step in",

      "off_system_exception": false,
      "off_system_verdict": "APPROVED|CONDITIONAL|DENIED|N/A",
      "off_system_exception_score": 0,
      "off_system_reason": "Why this stock triggered 3B — drift classification from CRO",
      "off_system_expected_return": 0,
      "off_system_12mo_target": 0.00,
      "off_system_checks_passed": "7/7|6/7|etc",
      "off_system_failed_checks": "Which specific checks failed, if any",
      "off_system_monitoring_cadence": "weekly"
    }
  ],

  "no_go": [
    {
      "symbol": "TICKER",
      "verdict": "NO GO",
      "stage_rejected": "thematic|gate|dd|review_gate|exception_denied",
      "rejection_reason": "Specific reason",
      "reconsider_if": "What would flip the verdict",
      "prompt4_removal": false,
      "prompt4_removal_reason": "Only populated if stage_rejected is review_gate — the CRO's specific rationale"
    }
  ],

  "exits": [
    {
      "symbol": "TICKER",
      "action": "SELL",
      "reason": "ExD signal|thesis broken|target reached|stop hit",
      "exit_price": 16.50,
      "entry_price": 10.00,
      "pnl_pct": 65.0,
      "lesson": "What we learned"
    }
  ],

  "watchlist": [
    {
      "symbol": "TICKER",
      "theme": "Micro-theme name",
      "status": "Near miss — why it didn't make the cut",
      "trigger_to_buy": "What would flip this to a buy",
      "price_at_scan": 12.50
    }
  ],

  "themes_this_week": [
    {
      "name": "Specific theme name",
      "classification": "PRIME|INVESTABLE|SELECTIVE",
      "lifecycle_stage": "EMERGENCE|EARLY_ADOPTION|MAINSTREAM",
      "valuation_regime": "FUNDAMENTAL|OPTIONALITY|TRANSITION",
      "composite_score": 7.8,
      "catalyst_score": 8.0,
      "momentum_score": 7.5,
      "crowding_score": 7.0,
      "runway_score": 8.5,
      "one_liner": "1 sentence why this theme matters now",
      "thesis_summary": "2-3 sentence investment thesis",
      "why_now": "Specific timing catalyst",
      "key_catalysts": ["Catalyst 1", "Catalyst 2"],
      "primary_risks": ["Risk 1", "Risk 2"],
      "tickers": ["TICK1", "TICK2"]
    }
  ]
}

CRITICAL RULES:
- ⚠️ MOST IMPORTANT: The new_positions array must ONLY contain stocks from your
  APPROVED FOR DEPLOYMENT list (the reconciliation above). If a stock was removed
  by Prompt 4 or denied by Prompt 3B, it goes in no_go — NEVER in new_positions.
  The Saturday workflow reads new_positions and adds them to the portfolio automatically.
  A stock in new_positions = a confirmed buy. There is no second check downstream.
- Every field must be populated — use empty string "" not null for missing text fields
- conviction and dd_conviction are integers 1-10
- position_size_pct is a decimal (0.20 = 20%)
- If Prompt 4 ADJUSTED a stock (e.g., reduced tier, lowered conviction), use the
  ADJUSTED values in new_positions, not the pre-Prompt 4 values from DD
- retrospective captures Prompt R's calibration notes from recent portfolio outcomes.
  If first session, use empty arrays and "First session — no prior data" for notes.
- market_context captures Prompt 0's market regime and capital flow analysis.
  established_waves and emerging_shifts should be clearly separated.
- batch_assessment is required — captures the theme clustering and quality assessment
- review_gate is required — captures the Prompt 4 portfolio review gate output.
  stocks_adjusted and stocks_removed must be complete and accurate. Cross-check:
  every stock in stocks_removed must appear in no_go with stage_rejected: "review_gate".
  Every stock in stocks_approved must appear in new_positions (and nowhere else).
- no_go.stage_rejected must accurately reflect WHERE the stock was filtered:
  "thematic" (Prompt 1), "gate" (Prompt 2), "dd" (Prompt 3), "review_gate" (Prompt 4),
  or "exception_denied" (Prompt 3B). The stage matters for retrospective calibration.
- entry_timing_verdict captures Phase D of Prompt 2 (CLEAN/ELEVATED/CHASING/POOR_TIMING)
- exceptional_override is true ONLY if all 4 override criteria were met in Step D2
- system_fit must match the assessment from Prompt 1 (STRONG/MODERATE/POOR)
- dd_conviction_change must be explicitly stated (INCREASED/SAME/DECREASED)
- dd_conviction_change_reason is required if conviction changed in either direction
- gate_bear_classification must reflect the honest bear case assessment
- dilution_check captures the structural dilution screen result
- Theme sub-scores (catalyst, momentum, crowding, runway) are 0-10 floats estimated from
  your analysis. These feed the content production guide and newsletter theme tables.
  Composite = rough average of the four, but weight catalyst/momentum higher for PRIME themes.
- Include ALL stocks we analyzed, not just passes — no_go captures rejections with
  stage_rejected showing WHERE they were filtered
- themes_this_week includes every theme we identified, even for rejected stocks
- Off-system exception fields: set off_system_exception to true only for stocks that
  went through Prompt 3B. off_system_verdict captures the 3B result. For non-exception
  stocks, set off_system_exception to false and off_system_verdict to "N/A".
  off_system_expected_return and off_system_12mo_target are the probability-weighted
  values from Part C Step 2.
- Do NOT include content_angles or newsletter — those are handled by repo automation

After generating the JSON, also output SIGNAL HISTORY ROWS for this session.
These rows are APPENDED to signal_history.csv to build the cross-session theme
tracking database used in Prompt 1 D1 (Theme Clustering Check).

Output format — one row per ticker that was ANALYSED this session (not just passes):
```csv
date,ticker,price,tier,theme,composite_score,system_fit,advanced,session_verdict
```

Example rows:
```csv
2026-03-01,NGNE,24.50,T2,rare_disease_biotech,7.60,MODERATE,yes,BUY
2026-03-01,LRMR,3.20,T1,rare_disease_biotech,7.70,MODERATE,yes,SPEC BUY
2026-03-01,CCCC,8.50,T3,china_consumer,6.80,POOR,no,NO GO
2026-03-01,ABCD,5.10,T2,quantum_computing,5.20,POOR,no,NO GO
```

Include ALL tickers from Prompt 1 — passes AND rejections. The theme column is the
micro-theme you assigned during thematic analysis. This builds a complete picture of
what themes the scanner is catching across weeks, even for stocks that didn't advance.
The user appends these rows to their running signal_history.csv file between sessions.
```

---

# TIPS FOR BEST RESULTS

1. **Keep web search ON** — the analysis depends on current data
2. **Use extended thinking model (Opus 4.6)** — don't switch to Sonnet mid-session
3. **One session per scan** — keep all phases in one conversation for full context
4. **Run Prompts 1→2→3 sequentially** — each builds on the prior. Don't skip stages.
5. **Gate aggressively between stages** — the whole point is filtering. If thematic
   analysis kills 8 out of 12, that's 8 fewer stocks cluttering the investment gate.
6. **Challenge at EVERY stage, not just the end** — catch bad theme calls before
   wasting gate analysis on them
7. **Run Prompt 2 per ticker** for best quality. Batching 2-3 is fine for comparison.
   Batching 5+ defeats the purpose of staged analysis.
8. **Run Prompt 3 strictly one at a time** — DD quality is inversely proportional to
   breadth. One stock = full thinking time = better forensic analysis.
9. **If processing 15+ signals**, consider splitting Prompt 1 into two batches
   (8 tickers each) to give thematic analysis enough depth per stock
10. **Always end with Prompt 4 (review gate) then Prompt 5 + Prompt 8** — review gate
    catches session-level drift, then newsletter HTML + decisions.json

## Selectivity & Theme Discipline

11. **Look for theme clustering first.** Before evaluating individual stocks, check:
    are 2-3+ signals firing in the same theme? If yes, that's where capital should go.
    Single-stock themes should clear a higher bar to advance.
12. **Passing on the entire batch is a valid outcome.** If no theme clustering exists
    and no individual stock reaches PRIME, the best trade is no trade. Your backtest
    shows the top 5 trades = 81% of P&L. Protecting capital for those opportunities
    is the real edge.
13. **Watch for conviction inflation.** If every stock's conviction goes UP through
    the pipeline (Gate → DD), the system has a confirmation bias problem. The normal
    pattern should be: most stocks stay flat or decrease, and only 1-2 genuinely
    improve on new material findings. Prompt 4's Review 2 catches this automatically.
14. **Diversify opportunity types.** A portfolio of 5 BINARY_CATALYST biotech plays
    is not diversification — it's a sector bet. Aim for a mix of opportunity types
    and sectors. If the scanner only produces one sector, either reduce total capital
    deployed or explicitly acknowledge the concentration risk.
15. **Run the Theme Power Check after Prompt 1** whenever you suspect the batch is
    composed of isolated micro-themes rather than a genuine capital flow wave. The
    monster winners come from catching themes, not from picking individual stocks.
16. **Always run Prompt R then Prompt 0 first.** Prompt R takes ~3 minutes and
    calibrates this session's analysis based on how open positions are tracking thesis,
    recent closes, and whether filtered stocks validated or invalidated our filters.
    Prompt 0 takes ~5 minutes and gives Prompt 1 the 6-18 month market context to
    judge whether a micro-theme is part of a structural wave or an isolated bet.
    Without them, the system scores themes in a vacuum.
17. **Never skip Prompt 4 (Portfolio Review Gate).** This is where we caught every
    major issue in the Feb 28 evaluation — system drift, conviction inflation, weak
    bear cases, sector concentration. Running it takes 3-5 minutes and may save you
    from a losing position. If Prompt 4 flags WEAK session quality, take it seriously —
    consider reducing total deployment or passing on the batch entirely.
18. **The pipeline now runs: R → 0 → 1 → 2 → 3 → 4 → (3B if drift) → 5 → 8.**
    Prompt 4 is the final decision gate for on-system trades. If Prompt 4 flags
    DRIFT on a stock you believe in, Prompt 3B provides a rigorous off-system
    exception path. Prompts 5 (newsletter) and 8 (export) should only reflect
    positions that survived the review gate or were approved via 3B exception.
19. **Entry timing is now core, not optional.** Prompt 2 Phase D assesses whether
    you're catching a move or chasing one. A good thesis with bad timing still loses
    money. The NGNE case (buying after a 26% gap-up with no catalyst for 3-4 months)
    would have been caught by Phase D and moved to WATCHLIST instead of STRONG BUY.
20. **The Exceptional Setup Override exists so you don't filter the next RGTI.** If a
    stock meets all four override criteria (catalyst stack + squeeze potential + extreme
    asymmetry + emerging theme alignment), it advances even without theme clustering.
    This should fire ~1 stock per month — if it's firing every week, the criteria
    aren't being applied strictly enough.
21. **Prompt 3B is the off-system exception path, not a loophole.** If Prompt 4 flags
    a stock as DRIFT but you believe the individual setup is genuinely exceptional,
    3B provides a rigorous probability-weighted analysis to test that belief. The
    75% expected return hurdle is deliberately higher than the standard 50%+ hurdle.
    If 3B fires every session, you're using it to bypass theme discipline — that's a
    sign to recalibrate, not to run more exceptions. Target: ≤1 exception per month.
22. **Use Research mode for Prompt 3B Part A when available.** Research mode's multi-step
    search is materially better at gathering the financial baseline and 15-20+ sources
    needed for the data foundation. Run Part A in a separate Research mode chat, review
    the data, then paste the output back into your main Extended Thinking session for
    Parts B and C. Parts B (forward model + valuation triangulation) and C (scenarios +
    exception verdict) need the full thinking budget and should always run in Extended
    Thinking mode. If Research mode is unavailable, run all three parts in Extended
    Thinking with aggressive web search — it works, just with shallower data in Part A.

## Scanner Output Format (what to paste)

When you run `python -m core.scanner --no-llm`, paste the entry candidates section.
The minimum useful information per stock is:

```
Ticker | Price | Tier | UC | RSI | MACD | 4W Mom%
```

If you have it, also include: beta, week date, HMA value.
More context = better analysis.

## Example Session Flow

```
Message 1: [Prompt R — weekly retrospective]
  Claude: 3 open positions: TICKER_A (entered 8 weeks ago, +32%, thesis intact —
          demand accelerating as predicted). TICKER_B (entered 3 weeks ago, -6%,
          thesis intact — normal consolidation, first catalyst in 5 weeks).
          TICKER_Y (entered 6 weeks ago, -18%, thesis WEAKENING — bear case on
          customer concentration is materialising). Filtered TICKER_Z from 2 months
          ago rallied 65% on the exact catalyst we identified.
          Calibration: over-filtered standalone setups in emerging themes recently.
          Partially dismantled bear cases are playing out on TICKER_Y.
  You: "Good calibration. Tighten stop on TICKER_Y. Noted on the over-filtering.
       Let's see the market."

Message 2: [Prompt 0 — market context]
  Claude: SELECTIVE regime (6-18 month outlook: economy expanding but narrow
          leadership, Fed holding, earnings mixed). Established wave:
          AI infrastructure still running (multi-month trend). Emerging shift:
          GLP-1 supply chain buildout — contract manufacturers starting to break out.
          Implication: deploy selectively, favour themes aligned with structural waves.
  You: "Noted. Here are the signals."

Message 3: [Prompt 1 + 12 scanner signals]
  Claude: Thematic analysis for all 12. Batch assessment: MIXED — no clustering,
          3 isolated biotech binaries + 1 contract manufacturer (emerging shift
          alignment!) + 8 filtered. TICKER_X gets Exceptional Setup Override
          (catalyst stack + 25% short interest + 4:1 asymmetry + GLP-1 emerging
          theme alignment). Recommends advancing 2, filtering 10.
  You: "Love the override call on TICKER_X. Run the Theme Power Check on the
       biotech batch — are any of those worth keeping?"

Message 4: [Theme Power Check challenge prompt]
  Claude: Biotech signals are isolated. No wave. Recommend dropping all 3.
  You: "Agreed. Advance TICKER_X and TICKER_M (contract manufacturer) to gate."

Message 5: [Prompt 2 for TICKER_X]
  Claude: Investment gate. Dilution: CLEAN. Bear case: DISMANTLED.
          Entry timing: CLEAN ENTRY (up 8% from pivot, catalyst in 3 weeks).
          Verdict: STRONG BUY, conviction 8. Full position.
  You: "Solid. Next."

Message 6: [Prompt 2 for TICKER_M]
  Claude: Investment gate. Bear case: PARTIALLY DISMANTLED (customer
          concentration risk). Entry timing: ELEVATED (up 22% from pivot).
          Verdict: BUY, conviction 6 (reduced 1 for elevated entry). T2 size.
          Note: BINARY_CATALYST modifier applies — capped at 50% regardless.
  You: "Per our calibration — partially dismantled bears need stricter treatment.
       Drop conviction to 5 or kill it?"
  Claude: "Reconsidering — the customer concentration is real. Recommend WATCHLIST
           with pullback entry at $X."
  You: "Agreed. Only TICKER_X advances to DD."

Message 7: [Prompt 3 for TICKER_X]
  Claude: Full DD. Conviction SAME at 8 (found minor negative: insider sold
          $50K under 10b5-1 — immaterial). STRONG BUY confirmed. Full position.
  You: "Good — conviction didn't inflate. Run the review gate."

Message 8: [Prompt 4 — Portfolio Review Gate]
  Claude: System fit: ARCHETYPE FIT (emerging theme alignment, squeeze potential,
          strong catalyst stack). Conviction trajectory: clean (flat at 8).
          Bear case: RIGOROUS. Portfolio: single stock, acceptable.
          Market alignment: swimming with emerging shift from Prompt 0.
          Session quality: ADEQUATE (only 1 position, but high quality).
  You: "Approved. Newsletter."

Message 9-10: [Prompt 5 + Prompt 8]
```

Alternative flow (strong batch with clustering):
```
Message 1: [Prompt R] — All 3 picks tracking thesis. No calibration adjustment.
Message 2: [Prompt 0] — RISK-ON. Active wave: semiconductor equipment capex.
Message 3: [Prompt 1 + 10 signals]
  Claude: STRONG batch — 3 tickers in semi equipment theme, clustering confirmed.
          2 align with established wave from Prompt 0.
Messages 4-7: [Prompt 2 for each, then Prompt 3 for passes]
  Entry timing: 2 CLEAN, 1 ELEVATED. Conviction flat through pipeline.
Message 8: [Prompt 4] — STRONG session. 2 ARCHETYPE FIT stocks approved.
Message 9-10: [Prompt 5 + Prompt 8]
```

Alt: Off-system exception flow (when CRO flags DRIFT on a stock you believe in)
```
Message 8: [Prompt 4]
  Claude: CRO Review. TICKER_X: STRONG DRIFT (2/7 archetype match — isolated binary,
          no theme clustering, no wave alignment). Recommend REMOVE.
  You: "I still think the asymmetry on TICKER_X is exceptional. Run 3B."

Message 9: [Prompt 3B Part A — ideally in Research mode side chat]
  Claude: Financial baseline: trailing revenue $12M/quarter growing 15% QoQ. Cash
          runway 6 quarters. Comps at 2-4x current valuation. Phase 3 base rate 58%.
          Strong specialist fund accumulation. TAM bottoms-up: $2.8B addressable.
  You: [Reviews data, pastes back into main chat if needed] "Data looks solid. Run Part B."

Message 10: [Prompt 3B Part B — Extended Thinking]
  Claude: Forward model: LOW $52M / MID $68M / HIGH $85M revenue next 12 months.
          4-method valuation triangulation: weighted target $18.40 (base), range
          $11.20 (bear) to $34.50 (bull). Key assumption: Phase 3 readout positive.
  You: "Model looks reasonable. Run Part C."

Message 11: [Prompt 3B Part C — Extended Thinking]
  Claude: 5-scenario model. Expected return: +92%. Pessimistic shift: +31% (robust).
          7/7 checks pass. Exception Score: 8/10. EXCEPTION APPROVED.
          T3, entry $XX, stop $YY.
  You: "Approved. Include in decisions.json with off-system flag."
```

Total: ~10-12 messages, ~55-85 minutes. Each stage got full thinking time.
Add ~25-35 minutes if Prompt 3B is triggered (3 sequential messages).

---

# WEEKLY WORKFLOW (COMPLETE)

```
FRIDAY EVENING (automated: 2-3 min)
├── python -m core.scanner --no-llm
├── Outputs: technical signals table, sell signal alerts
└── Copy signals table for Claude session

FRIDAY/SATURDAY (interactive: 55-85 min, +25-35 min if 3B triggered)
├── New Claude.ai chat → Prompt R (retrospective + signal_history.csv, ~3 min)
├── Prompt 0 (market context, capital flows, established vs emerging themes, ~5 min)
├── Prompt 1 with all signals (thematic analysis + cross-session clustering + system fit)
├── If batch looks scattered → Theme Power Check challenge prompt
├── Review, challenge theme calls, decide which advance
├── Prompt 2 for each advancing ticker (investment gate + timing assessment)
│   └── Challenge, compare, filter at each step
├── Prompt 3 for each gate-passing ticker (deep DD, one at a time)
│   └── Challenge bear cases, stress-test math, watch for conviction inflation
├── Prompt 4 → Portfolio Review Gate (holistic session audit, ~5 min)
│   └── May remove stocks, reduce sizing, or approve as-is
├── IF Prompt 4 flags DRIFT on a stock you believe in:
│   ├── Prompt 3B Part A (Research mode side chat if available, ~10-15 min)
│   ├── Review data foundation
│   ├── Prompt 3B Part B (Extended Thinking, ~8-12 min) → Forward model + valuation
│   ├── Review valuation triangulation
│   └── Prompt 3B Part C (Extended Thinking, ~8-12 min) → Exception score + verdict
├── Prompt 6 for any ExD sell signals from scanner
├── Prompt 5 → newsletter.html (save to substack/output/current/)
├── Prompt 8 → decisions.json + signal_history.csv rows (save to scanner/output/)
└── Append signal_history rows to running signal_history.csv

SATURDAY (automated: python -m core.saturday_workflow)
├── 1. merge_decisions.py
│   └── signals_technical.json + decisions.json → signals.json
├── 2. Portfolio manager
│   ├── Add new positions from decisions.json
│   ├── Close exits from decisions.json
│   └── Update prices on all open positions
├── 3. market_analyzer.py → market_analysis.md (if not in decisions)
├── 4. content_production_guide.py
│   ├── Reads: signals.json, portfolio.csv, equity_curve.csv
│   ├── Builds weekly schedule (4 categories across Sun-Sat)
│   └── Outputs: content_production_guide.md + content_schedule.json
├── 5. Newsletter placement
│   └── Copies newsletter.html to substack/output/current/
└── Outputs: everything ready for the week

SUNDAY (interactive: 15-20 min)
├── Publish newsletter.html to Substack
├── Open Claude.ai → attach content_production_guide.md
├── Use Category 4 notes prompt from handbook → 3 HTML notes
└── Post notes to Substack

MONDAY-FRIDAY (interactive: 10-15 min per day)
├── Open Claude.ai → attach content_production_guide.md
├── Check schedule for today's category
├── Copy that category's prompt from content_prompt_handbook_v5.md
├── Get: 1 HTML post + 3 HTML notes
└── Post to Substack

WEDNESDAY (optional)
└── Prompt 7 (catalyst check) if needed for held positions

SATURDAY
├── Notes only (no post)
└── Attach content_production_guide.md → Daily Notes Prompt → 3 notes

NEXT FRIDAY
└── Repeat
```

## What the Saturday Workflow Does

The `saturday_workflow.py` script is the single command that bridges your chat
session to the full automation stack. It:

1. **Merges** your chat decisions with scanner technical data → `signals.json`
   (the format ALL downstream systems already consume)
2. **Updates portfolio** — adds new positions, closes exits, refreshes prices
3. **Generates market analysis** — API call for fresh market context (if needed)
4. **Builds content schedule** — `content_production_guide.py` reads your repo
   (portfolio, themes, winners, equity curve) and assigns categories + topics
   to each day of the week
5. **Places newsletter** — copies your chat-generated HTML to the right directories
6. **Archives everything** — weekly folder for historical reference

After running this, you have:
- `content_production_guide.md` — attach to Claude.ai each day for Substack posts
- `newsletter.html` — ready to publish to Substack
- Updated portfolio and equity curve
- Tweet system fed with fresh signals.json

## How Content Production Works (Repo-Driven)

The Substack content schedule is generated by `content_production_guide.py`, NOT in
the chat session. This is intentional — the script has access to:

- Full portfolio history (what you've posted about recently)
- All open positions with current P&L
- Historical winners for showcase
- Equity curve for benchmark comparisons
- Theme history across weeks

The chat session doesn't have this context. So the schedule comes from the repo,
and the daily content comes from Claude.ai with the production guide attached.

| Prompt Library (chat) | Repo Automation (scripts) |
|----------------------|--------------------------|
| Prompt R: Retrospective | scanner.py: Technical signals |
| Prompt 0: Market context | merge_decisions.py: Merge → signals.json |
| Prompt 1: Thematic analysis | portfolio manager: Prices, P&L, equity |
| Prompt 2: Investment gate | content_production_guide.py: Weekly schedule |
| Prompt 3: Deep due diligence | newsletter placement + archiving |
| Prompt 4: Portfolio review gate | content_prompt_handbook_v5.md: Daily prompts |
| Prompt 5: Newsletter HTML | tweet system: Automated posting |
| Prompt 8: decisions.json export | |
| Prompt 6-7: Position mgmt | |
| Challenge prompts: Refinement | |
