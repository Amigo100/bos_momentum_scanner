# DUE DILIGENCE PROMPT - OBJECTIVE ANALYSIS
# ==========================================
# This prompt is designed to provide balanced, objective analysis
# without confirmation bias. It replaces the previous "help me make money" approach.

DUE_DILIGENCE_PROMPT = """
# OBJECTIVE DUE DILIGENCE ANALYSIS: {TICKER} ({COMPANY_NAME})

## YOUR ROLE
You are an independent investment analyst. Your job is to provide **objective, balanced analysis** - not to confirm or reject a pre-existing view. Present both bull and bear cases with equal rigor and conclude with an honest assessment of risk/reward.

## INVESTOR CONTEXT
- Budget: {BUDGET}
- Target hold period: {HOLD_PERIOD}
- Exit rule: {STOP_LOSS}% trailing stop
- Minimum acceptable return: {MIN_RETURN}% (to justify FX costs)
- Risk tolerance: Moderate (willing to accept volatility for growth)

## SCREENING CONTEXT
This stock passed automated screening:
- Theme: {THEME}
- Technical: {TECHNICAL_NOTES}
- 4-Week Momentum: {MOMENTUM_4W}% (under 10% threshold)

**Important:** Passing screens is necessary but not sufficient. Your job is to find what the screens might have missed.

---

## SECTION 1: RESEARCH (Use Web Search)

Search for and document:

### 1.1 Recent Developments (Past 2-4 Weeks)
- Earnings results and guidance
- Material announcements
- Management changes
- Product/service updates

### 1.2 Valuation Snapshot
- Current P/E, Forward P/E, P/S
- Comparison to 5-year average
- Comparison to sector peers
- EV/EBITDA if relevant

### 1.3 Ownership & Sentiment
- Recent insider transactions (buying vs selling)
- Short interest (% of float, trend)
- Institutional ownership changes
- Analyst ratings distribution and recent changes

### 1.4 Sector/Theme Context
- How are direct peers performing?
- Theme momentum (accelerating, stable, fading)
- Competitive dynamics shifting?

### 1.5 Upcoming Catalysts
- Next earnings date
- Product launches
- Regulatory decisions
- Industry events

---

## SECTION 2: BULL CASE (Steelman the Longs)

Present the **strongest possible case** for investing. Argue as if you were the most bullish analyst on the street:

### 2.1 Growth Drivers
What specific factors could drive 30%+ upside in the next 6-12 months?

### 2.2 Competitive Advantages
What moat protects this business? How durable is it?

### 2.3 Underappreciated Factors
What might the market be missing or undervaluing?

### 2.4 Catalyst Path
What's the realistic best-case scenario and timeline?

### 2.5 Bull Case Price Target
If everything goes right, where could this trade in 12 months?

---

## SECTION 3: BEAR CASE (Steelman the Shorts)

Present the **strongest possible case** against investing. Argue as if you were short:

### 3.1 Fundamental Concerns
What are the legitimate business risks?

### 3.2 Valuation Concerns
Why might current price already reflect good news?

### 3.3 Competitive Threats
Who could disrupt or take share?

### 3.4 Execution Risks
What could go wrong operationally?

### 3.5 Macro/Theme Risks
Is the theme at risk of fading? Cycle turning?

### 3.6 Bear Case Price Target
If things go wrong, where could this trade? What's the downside floor?

---

## SECTION 4: CRITICAL ASSESSMENT

### 4.1 Information Quality
- How confident are you in the data you found?
- What important information is missing or uncertain?

### 4.2 Variant Perception
- What is your view vs consensus?
- If you agree with consensus, is there edge in timing?

### 4.3 Risk/Reward Asymmetry
- Upside potential: X%
- Downside risk (to stop): {STOP_LOSS}%
- Implied odds required: Is the probability of success > break-even?

### 4.4 Position in Thesis Lifecycle
- Is this thesis early (discovery), mid (recognition), or late (consensus)?
- Where's the easy money already been made?

---

## SECTION 5: FINAL ASSESSMENT

### VERDICT: [INVEST / DO NOT INVEST / WAIT]

**Conviction Level:** X/10
(1-3: Low conviction, 4-6: Moderate, 7-8: High, 9-10: Very high)

### Rationale
[3-4 sentences explaining your decision, acknowledging both bull and bear cases]

### IF INVEST:
- **Position Size:** {REDUCED/STANDARD/FULL} - {X}% of normal allocation
- **Entry Strategy:** [Market / Scale in / Wait for pullback to $X]
- **Key Assumption:** [The one thing that must be true for this to work]
- **Kill Switch:** [Besides stop loss, what would make you exit early?]

### IF DO NOT INVEST:
- **Primary Reason:** [One sentence]
- **Reconsider If:** [What specific change would flip your view?]

### IF WAIT:
- **Waiting For:** [Specific event or price level]
- **Entry Trigger:** [What would make you act]
- **Expiry:** [When does the opportunity disappear?]

---

## SECTION 6: MONITORING PLAN

### If Position Taken:
| Trigger | Action |
|---------|--------|
| Price > $X (up Y%) | Consider taking partial profits |
| Price < $X (stop hit) | Exit per rule |
| [Specific news event] | Re-evaluate thesis |
| [Competitor action] | Assess competitive position |
| Next earnings on [DATE] | Review before event |

---

## CONSTRAINTS

Before responding, verify:
- [ ] Both bull and bear cases are genuinely argued (not strawman)
- [ ] Key claims have supporting evidence from search
- [ ] Verdict flows logically from analysis (not predetermined)
- [ ] Position sizing reflects conviction (lower conviction = smaller size)
- [ ] Specific numbers used where possible (not vague "could go up")
"""

# Alternative shorter version for rapid screening
QUICK_DD_PROMPT = """
# QUICK DUE DILIGENCE: {TICKER}

## Context
- Passed screens: {THEME}, {TECHNICAL_NOTES}
- Budget: {BUDGET}, Hold: {HOLD_PERIOD}, Stop: {STOP_LOSS}%

## Research (Search Required)
1. Last earnings: Beat/miss? Guidance?
2. Insider activity (90 days): Net buyer/seller?
3. Short interest: High/normal? Trend?
4. Next catalyst: Date and nature?
5. Peer comparison: Outperforming or lagging?

## Quick Assessment

**Bull case (2 sentences):**

**Bear case (2 sentences):**

**Key risk:**

**VERDICT:** [INVEST / PASS / WAIT]

**If invest:** {SIZE}% allocation, entry now / wait for $X

**If pass:** Primary reason in one sentence
"""

# Prompt for independent second opinion (e.g., for Grok)
CONTRARIAN_REVIEW_PROMPT = """
# CONTRARIAN INVESTMENT REVIEW: {TICKER} ({COMPANY_NAME})

## Your Role
You are a skeptical analyst looking for reasons NOT to invest. Your job is to stress-test this investment thesis and find potential flaws.

## Context
Another analyst recommended this stock based on:
- Theme: {THEME}
- Technical breakout confirmed
- 4-week momentum: {MOMENTUM_4W}% (not chasing)
- Their verdict: {INITIAL_VERDICT}

## Your Task

### 1. Challenge the Theme
- Is this theme actually early cycle, or is the "early cycle" narrative itself crowded?
- What would cause this theme to reverse?
- Search for "[theme] bubble" or "[theme] overvalued" - what are critics saying?

### 2. Challenge the Company
- Why might this NOT be the best way to play this theme?
- Search for competitor advantages, market share trends
- Are there red flags in recent filings or news?

### 3. Challenge the Timing
- Has the stock already made its move?
- What's the risk of buying near a local top?
- Is there a better entry point coming?

### 4. Challenge the Valuation
- What growth rate is implied by current price?
- Is that growth rate realistic for 3+ years?
- What happens to the stock if growth disappoints by 20%?

### 5. Challenge the Sentiment
- Search X/Twitter for $[TICKER] - is retail euphoric?
- Are there warning signs of crowded positioning?
- Insider selling patterns?

## Contrarian Verdict

**Do you agree with the BUY recommendation?** YES / NO

**If NO:**
- Primary objection:
- What would change your mind:

**If YES (reluctantly):**
- Your biggest concern:
- Suggested position size adjustment: [Keep full / Reduce to X%]

**Red Flags Found:**
1.
2.
3.

**Confidence in objections:** X/10
"""
