# Sterling Grid Prompt Library
## Interactive Stock Screening in Claude.ai (Opus 4.6 + Extended Thinking)

> **Purpose:** Replace the 3-stage API pipeline with an interactive session where Opus 4.6
> does ALL analysis — thematic mapping, investment gate, and deep DD — in a single
> conversation with sequential prompts that build on each other.
>
> **Key design:** Each stage gets Claude's FULL extended thinking budget and web search
> allocation. You gate between stages — challenging, overriding, and filtering — so
> only the best candidates advance to the most intensive analysis.
>
> **Workflow:**
> 1. Run `python -m core.scanner --no-llm` → produces technical signals
> 2. Open a new Claude.ai chat (Opus 4.6, extended thinking ON, web search ON)
> 3. Paste **Prompt 1** with your signals → thematic analysis for all tickers
> 4. Review, challenge, decide which advance → **Prompt 2** for each (investment gate)
> 5. Review, challenge, decide which advance → **Prompt 3** for each (deep DD)
> 6. Use **Challenge Prompts** at any stage to push back
> 7. **Prompt 4** → newsletter HTML | **Prompt 7** → decisions.json export

---

# PROMPT 1: THEMATIC ANALYSIS

> **When to use:** Start of every weekly screening session. Paste this with ALL your
> scanner output. This is the broadest analysis — mapping every signal to its micro-theme
> and scoring themes. Claude uses full thinking time for JUST this stage.
>
> **After this prompt:** Review the results, challenge any calls, then tell Claude
> which tickers to advance to the Investment Gate (Prompt 2).

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
- Average hold: 4-8 weeks, targeting 50-100%+ returns
- Exit: ExD (HMA pivot high + UC falling) or tiered trailing stops

We want ASYMMETRIC setups — stocks where the upside is 50-100%+ and downside is bounded.
This is NOT about finding safe stocks. It's about finding multi-bagger candidates with
manageable risk.

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
- 8-10: Multiple SPECIFIC catalysts in next 6-12 months (FDA dates, contracts, launches)
- 5-7: General tailwinds but no specific near-term events
- 1-4: No catalysts, or catalysts already priced in

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

| Composite | Classification | Action |
|-----------|----------------|--------|
| 7.5+      | PRIME          | High conviction — prioritize |
| 6.0-7.4   | INVESTABLE     | Good opportunity — standard sizing |
| 4.5-5.9   | SELECTIVE      | Only the best stock in this theme |
| < 4.5     | AVOID          | Do not invest |

## Opportunity type classification (determines trading approach):
- SECULAR_GROWTH: Multi-year tailwind, revenue accelerating → full size, longer hold
- BINARY_CATALYST: Pass/fail event (FDA, trial, ruling) → reduced size, defined timeline
- CYCLICAL_RECOVERY: Sector turning, early-cycle improving → full size if early
- SPECIAL_SITUATION: Restructuring, spin-off, activist → case-by-case
- MOMENTUM_CATCHUP: Strong sector, this stock lagging peers → standard size, tight stops

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════

For each ticker, present:
- Company description (1 sentence)
- Micro-theme name
- Sub-scores (catalyst, demand, recognition, timing, capital cycle) with brief justification
- Composite score and classification
- Opportunity type and valuation regime
- 2-sentence thesis specific to this company

After ALL tickers, present:

COMPARATIVE RANKING TABLE:
| Ticker | Theme | Composite | Classification | Regime | Recommendation |
"If I could only buy ONE, which has the best risk-adjusted setup and why?"

GATING RECOMMENDATION:
- ADVANCE TO GATE: [list tickers] — PRIME/INVESTABLE themes with strong fit
- FILTERED OUT: [list tickers] — each with 1-sentence reason
- BORDERLINE: [list tickers] — worth discussing before deciding

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
> **After this prompt:** Review each verdict, challenge as needed, then decide which
> to advance to Deep DD (Prompt 3).

```
Run the Investment Gate on: [TICKER(S)]

You have the full thematic analysis from our earlier discussion. DO NOT repeat it.
Focus this entire analysis on RED FLAGS, RETURN MATH, and BEAR CASE.

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
PHASE C: BEAR CASE (steelmanned)
═══════════════════════════════════════════════════════════════════

Search: "[ticker] bear case risk short thesis"

- What's the #1 argument a smart short-seller would make?
- Can you dismantle it with DATA? (Not "I think," but "Revenue grew X% which proves…")
- If not dismantled: FATAL FLAW (→ NO GO) or ACCEPTABLE RISK (→ continue)?

DOWNSIDE FLOOR:
- Where would value investors or strategic acquirers step in?
- Maximum realistic loss in 3 months?

═══════════════════════════════════════════════════════════════════
VERDICT
═══════════════════════════════════════════════════════════════════

STRONG BUY (conviction 7-10):
- Catalyst within 90 days + no disqualifiers + math to 50% is clear
→ Advance to Deep DD at FULL position size

SPEC BUY (conviction 4-6):
- Thesis intact but concerns: timing, execution dependency, multiple conditions
→ Advance to Deep DD at REDUCED (50%) position size

NO GO (conviction 1-3):
- Any disqualifier hit, no math to 50%, or fatal bear case
→ Stop. State the specific reason AND what would flip the verdict.

IMPORTANT: Your job is NOT to reject every stock. These already passed technical
screening AND your thematic analysis. If it looks good, be confident. Only reject
for SPECIFIC, evidenced reasons.

Present for each ticker:
- Disqualifier result (CLEAN / CAUTION / DQ)
- Return math summary (1-2 sentences)
- Bear case + rebuttal (1-2 sentences)
- Downside floor estimate
- VERDICT + conviction score
- If STRONG/SPEC BUY: recommended position sizing

Then STOP and wait for my feedback before we proceed to Deep DD.
```

---

# PROMPT 3: DEEP DUE DILIGENCE

> **When to use:** After Prompt 2, for each ticker that passed the Investment Gate.
> Run this ONCE PER TICKER to give Claude maximum thinking time and search depth.
>
> **Context:** Same conversation. Claude has both thematic analysis and gate output.
> This is the forensic deep dive — Claude should go DEEPER than the gate, not repeat it.

```
Run Deep Due Diligence on: [TICKER]

You have the full thematic analysis and investment gate from our earlier discussion.
DO NOT repeat what you already found. This phase is about going DEEPER — finding what
the earlier analysis couldn't catch. Use your full extended thinking and search budget
on this one stock.

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

3. BEAR CASE INVESTIGATION (go deeper than the gate)
Search: "[ticker] short thesis detailed bear case risks 2025/2026"
Search: "[ticker] insider buying selling SEC Form 4 2025/2026"
- What's the #1 thing that could go wrong that we HAVEN'T considered yet?
- Insider selling beyond scheduled 10b5-1 plans?
- Any class action lawsuits, patent challenges, regulatory headwinds?
- Customer concentration risk?

4. SMART MONEY POSITIONING
Search: "[ticker] institutional ownership 13F changes hedge fund 2025/2026"
- Are top-tier funds accumulating or distributing?
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

VARIANT PERCEPTION: What we see that the consensus misses — our edge.

KEY ASSUMPTION: The ONE thing that must be true for this to work.

KILL SWITCH: What triggers early exit — specific and measurable, not vague.

DOWNSIDE FLOOR: Where value buyers or acquirers step in. Max realistic loss.

RISK TO MONITOR: The single most important risk with a specific metric or date.

ACTION: Be specific — "Buy Monday at open at ~$X. [Full/Reduced] position at T[1/2/3]
allocation. Set trailing stop at $Y. Monitor [specific event] on [date]."

FINAL VERDICT: STRONG BUY / SPEC BUY / NO GO with conviction 1-10.
If verdict changed from the gate, explain what you found that shifted it.
If NO GO: State the fatal flaw AND what would flip the verdict.

Then STOP. I may challenge your bear case, stress-test the math, or ask for
comparisons before we finalize.
```

---

# CHALLENGE PROMPTS

> **When to use:** After receiving analysis at ANY stage. Pick the one relevant to
> your situation. These work after Prompt 1 (thematic), Prompt 2 (gate), or Prompt 3 (DD).

## Challenge the Bear Case

```
Your bear case for [TICKER] feels too easy to dismiss. Steelman it harder:

1. Search specifically for "[ticker] short seller thesis 2025/2026" — what are
   the bears actually saying?
2. What's the WORST realistic scenario in the next 3 months?
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

## Validate Timing

```
For [TICKER]: Is the timing right, or are we early/late?

1. Search: "[ticker] price action momentum recent weeks"
2. Did we miss the initial move? What % has it already rallied from the pivot?
3. Is there a better entry point coming (earnings pullback, offering overhang)?
4. What's the cost of waiting 1-2 weeks vs entering Monday?

I'd rather miss a trade than chase one.
```

## Liquidity & Execution Check

```
For [TICKER]: Can we actually trade this cleanly?

1. What's the average daily dollar volume?
2. What's the float and short interest as % of float?
3. If we allocate [T1=20%/T2=10%/T3=5%] of a $[X] portfolio, how many shares is that
   vs average daily volume?
4. Is there offering/dilution risk in the next 90 days?
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

---

# PROMPT 4: NEWSLETTER (HTML)

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
AMBER, STRONG BUY, SPEC BUY, NO GO.

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

# PROMPT 5: SELL SIGNAL REVIEW

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

# PROMPT 6: MID-WEEK CATALYST CHECK

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

# PROMPT 7: STRUCTURED EXPORT (decisions.json)

> **When to use:** At the END of every analysis session, after all decisions are final.
> This produces the structured JSON that your Saturday workflow reads to update the
> portfolio, generate signals.json, and build the weekly Substack schedule.
>
> **Note:** The Substack content schedule is generated AUTOMATICALLY by
> `content_production_guide.py` from your repo data (portfolio, themes, signals).
> You do NOT generate it in chat — the repo has full history context that chat lacks.
> Similarly, the newsletter HTML was already produced by Prompt 4.

```
We've finalized our analysis. Now produce the structured decisions.json export.

Generate ONLY valid JSON (no markdown fences, no commentary). I'll paste this directly
into my repo as scanner/output/decisions.json.

{
  "scan_date": "YYYY-MM-DD",
  "scan_week_ending": "YYYY-MM-DD",
  "market_regime": "risk_on|risk_off|selective",
  "market_context_summary": "2-3 sentences on what's driving markets this week",

  "new_positions": [
    {
      "symbol": "TICKER",
      "action": "BUY",
      "verdict": "STRONG BUY|SPEC BUY",
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
      "opportunity_type": "SECULAR_GROWTH|BINARY_CATALYST|CYCLICAL_RECOVERY|SPECIAL_SITUATION|MOMENTUM_CATCHUP",
      "valuation_regime": "FUNDAMENTAL|OPTIONALITY|TRANSITION",

      "gate_verdict": "STRONG_BUY|SPEC_BUY",
      "gate_conviction": 8,
      "catalyst_summary": "Specific catalyst with date",
      "red_flag_level": "CLEAN|MINOR",
      "gate_bear_case": "1-sentence bear case",
      "gate_math": "Path to 50%+",

      "dd_verdict": "STRONG BUY|SPEC BUY",
      "dd_conviction": 8,
      "dd_elevator_pitch": "2-3 sentences from our DD",
      "dd_why_now": "Key catalyst with date",
      "dd_the_math": "Regime-adapted path to 50%+",
      "dd_bear_case": "Steelmanned bear argument",
      "dd_risk_to_monitor": "Single most important risk",
      "dd_action": "Specific: Buy Monday at ~$X, T1 full position, stop at $Y",
      "dd_key_catalyst": "Primary catalyst driving the trade",
      "dd_fatal_flaw": "",

      "variant_perception": "What we see that consensus misses",
      "key_assumption": "The ONE thing that must be true",
      "kill_switch": "What triggers early exit",
      "downside_floor": "Where value buyers step in"
    }
  ],

  "no_go": [
    {
      "symbol": "TICKER",
      "verdict": "NO GO",
      "stage_rejected": "thematic|gate|dd",
      "rejection_reason": "Specific reason",
      "reconsider_if": "What would flip the verdict"
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
- Every field must be populated — use empty string "" not null for missing text fields
- conviction and dd_conviction are integers 1-10
- position_size_pct is a decimal (0.20 = 20%)
- Theme sub-scores (catalyst, momentum, crowding, runway) are 0-10 floats estimated from
  your analysis. These feed the content production guide and newsletter theme tables.
  Composite = rough average of the four, but weight catalyst/momentum higher for PRIME themes.
- Include ALL stocks we analyzed, not just passes — no_go captures rejections with
  stage_rejected showing WHERE they were filtered (thematic, gate, or dd)
- themes_this_week includes every theme we identified, even for rejected stocks
- Do NOT include content_angles or newsletter — those are handled by repo automation
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
10. **Always end with Prompt 4 then Prompt 7** — HTML newsletter + decisions.json

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
Message 1: [Prompt 1 + 12 scanner signals]
  Claude: Thematic analysis for all 12. Recommends advancing 5, filtering 7.
  You: "Agree on the 7 filters. But look again at TICKER_X — the theme feels
       stronger than you scored it. Also drop TICKER_Y, I don't like the sector."

Message 2: Claude re-assesses TICKER_X, updates recommendation.
  You: "OK, advance TICKER_X, TICKER_A, TICKER_B, TICKER_C to the gate."

Message 3: [Prompt 2 for TICKER_X]
  Claude: Investment gate analysis. Verdict: STRONG BUY, conviction 8.
  You: [Challenge the math] "Revenue assumption feels aggressive."

Message 4: Claude stress-tests the math.
  You: "OK, I buy it. Next."

Message 5: [Prompt 2 for TICKER_A]
  Claude: NO GO — shelf offering filed last week.
  You: "Agree. Skip it."

Message 6: [Prompt 2 for TICKER_B and TICKER_C]
  Claude: TICKER_B SPEC BUY (5), TICKER_C NO GO (fatal flaw).
  You: "Advance TICKER_X and TICKER_B to DD."

Message 7: [Prompt 3 for TICKER_X]
  Claude: Full DD. STRONG BUY, conviction 8.
  You: [Challenge bear case]

Message 8: Claude steelmans the bear harder.
  You: "Acceptable risk. Finalize."

Message 9: [Prompt 3 for TICKER_B]
  Claude: Full DD. SPEC BUY, conviction 5.
  You: "Agreed. Let's do the newsletter."

Message 10: [Prompt 4]
  Claude: Complete HTML newsletter.

Message 11: [Prompt 7]
  Claude: decisions.json with all results (passes, no-gos, watchlist, themes).
```

Total: ~11 messages, ~45-60 minutes. Each stage got full thinking time.
Compare to monolithic: 1 massive message trying to do it all at once.

---

# WEEKLY WORKFLOW (COMPLETE)

```
FRIDAY EVENING (automated: 2-3 min)
├── python -m core.scanner --no-llm
├── Outputs: technical signals table, sell signal alerts
└── Copy signals table for Claude session

FRIDAY/SATURDAY (interactive: 45-75 min)
├── New Claude.ai chat → Prompt 1 with all signals (thematic analysis)
├── Review, challenge theme calls, decide which advance
├── Prompt 2 for each advancing ticker (investment gate)
│   └── Challenge, compare, filter at each step
├── Prompt 3 for each gate-passing ticker (deep DD, one at a time)
│   └── Challenge bear cases, stress-test math
├── Prompt 5 for any ExD sell signals from scanner
├── Prompt 4 → newsletter.html (save to substack/output/current/)
├── Prompt 7 → decisions.json (save to scanner/output/)
└── Two files saved to repo

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
└── Prompt 6 (catalyst check) if needed for held positions

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
| Prompt 1: Thematic analysis | scanner.py: Technical signals |
| Prompt 2: Investment gate | merge_decisions.py: Merge → signals.json |
| Prompt 3: Deep due diligence | portfolio manager: Prices, P&L, equity |
| Prompt 4: Newsletter HTML | newsletter placement + archiving |
| Prompt 7: decisions.json export | content_production_guide.py: Weekly schedule |
| Prompt 5-6: Position mgmt | content_prompt_handbook_v5.md: Daily prompts |
| Challenge prompts: Refinement | tweet system: Automated posting |
