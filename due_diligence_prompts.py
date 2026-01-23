#!/usr/bin/env python3
"""
Due Diligence Prompts v2.0
==========================

Enhanced prompts for deep research on stocks that pass the Gatekeeper.
Focused on finding 50-100%+ return potential through "Variant Perception" -
what do we see that the market hasn't fully priced in yet?

These prompts are designed for high-reasoning models (Claude Opus, GPT-4, Gemini Pro)
with web search capability.
"""

# =============================================================================
# DEAL MEMO PROMPT - THE "50%+ ALPHA" DEEP DIVE
# =============================================================================
# This is the main prompt for comprehensive due diligence after passing all gates.
# Uses Chain-of-Thought reasoning to simulate a Hedge Fund "Thesis Defense."

DEAL_MEMO_PROMPT = '''
# DEAL MEMO: {TICKER} - Deep Dive Due Diligence

## YOUR ROLE
You are the Lead Portfolio Manager at a high-conviction Global Macro Hedge Fund. 
You specialize in aggressive growth equities and "special situations."
Your reputation depends on finding asymmetric bets with 50%+ upside potential.

## SCREENING STATUS (Already Passed)
| Gate | Status | Details |
|------|--------|---------|
| Technical | ✓ PASSED | Weekly BoS breakout, Banker accumulation score: {BANKER} |
| Thematic | ✓ PASSED | Theme: {THEME} ({THEME_CLASSIFICATION}) |
| Gatekeeper | ✓ PASSED | Catalysts confirmed, red flags: {RED_FLAG_LEVEL} |

## INVESTOR CONTEXT
- Capital at risk: $10,000
- Target hold: 3-12 months (flexible if thesis holds)
- Exit rule: Disciplined risk management with predetermined exits
- Minimum return target: 50%+ (we're not here for 10% trades)
- Weekly swing trading approach - systematic entries and exits

## YOUR MISSION
Validate whether this stock has REALISTIC potential for **50-100%+ returns** in 3-12 months.
We need a **re-rating event** - either earnings surprise, multiple expansion, or both.

**IMPORTANT:** Execute all searches silently. Report only findings, not your search process.

---

## PHASE 1: THE "EXPLOSIVE GROWTH" INVESTIGATION

### 1.1 The "Hyper-Growth" Check
Search: "{TICKER} revenue growth quarterly YoY"
- Is revenue growth ACCELERATING? (e.g., 20% → 25% → 40%)
- We need "accelerating acceleration" - growth rate itself speeding up
- Compare last 4 quarters - what's the trajectory?

### 1.2 The "ROIC Inflection" Check
Search: "{TICKER} return on invested capital ROIC margin"
- Is the company suddenly making more money on every dollar spent?
- Look for R&D-heavy companies transitioning to "sales mode"
- Signs: R&D as % of revenue declining while revenue grows

### 1.3 The "Operating Leverage" Kicker
Search: "{TICKER} operating margin gross margin trend"
- Compare OpEx growth vs Revenue growth
- KEY QUESTION: Will a 10% revenue increase drive 50% earnings increase?
- This happens in high-fixed-cost businesses that just broke even

### 1.4 The "Shadow Backlog" Hunt
Search: "{TICKER} backlog book-to-bill contracts pipeline"
- Is Book-to-Bill ratio > 1.2? (Revenue explosion incoming)
- Any unannounced contracts hinted in filings or earnings calls?
- RPO (Remaining Performance Obligations) trend?

### 1.5 The "Customer Obsession" Metric
Search: "{TICKER} net revenue retention NRR dollar retention churn"
- NRR > 120% = customers spending MORE each year (very bullish)
- NRR < 100% = leaky bucket (bearish)
- Any churn concerns mentioned in recent calls?

### 1.6 The "Blue Sky" Math
Search: "{TICKER} total addressable market TAM market share"
- Current market share vs TAM?
- If they capture just 1-2% more of TAM, does the stock DOUBLE?
- Is TAM expanding (rising tide) or fixed pie (market share fight)?

---

## PHASE 2: THE "HIDDEN CATALYST" SEARCH
(Find what's NOT in the headlines - this is where alpha lives)

### 2.1 Non-Obvious Catalysts
Search: "{TICKER} patent approval CEO compensation incentives"
- Any patent approvals pending?
- CEO/management equity grants that vest at specific price targets?
- Supply chain constraints clearing up?

### 2.2 Industry Intelligence
Search: "{TICKER} industry blog expert channel check"
- What are industry insiders saying (not Wall Street)?
- Trade publication mentions, supplier commentary?
- Hiring trends (glassdoor, linkedin)?

### 2.3 Upcoming Events Timeline
Search: "{TICKER} investor day conference earnings date 2025"
- Build a 90-day catalyst calendar
- What events could force institutional re-rating?

---

## PHASE 3: THE "BEAR KILLER" PROTOCOL
(This is critical - find and DESTROY the bear case, or flag it as fatal)

### 3.1 Identify the Bear Thesis
Search: "{TICKER} short seller report bearish case risk concerns"
- What is the #1 argument shorts are making?
- What would a smart bear say at a dinner party?

### 3.2 Dismantle or Validate
For the bear argument, find counter-evidence:
- Is the bear case based on OUTDATED information?
- Has management already addressed this concern?
- Is the risk already PRICED IN?

**CRITICAL:** If you CANNOT dismantle the bear argument with data, flag it as a FATAL FLAW and recommend NO GO.

---

## PHASE 4: VALUATION REALITY CHECK
(Ignore analyst price targets - they are lagging indicators)

### 4.1 Historical Self-Comparison
Search: "{TICKER} historical P/E P/S valuation 5 year average"
- Current P/E vs OWN 3-year average P/E (not peers)
- If they hit upper-end guidance, is the stock CHEAP vs its own history?

### 4.2 The "Re-Rating" Math
Calculate the path to 50%:
- Current multiple = X
- If growth accelerates, deserved multiple = Y  
- Earnings growth Z% + Multiple expansion W% = Total return

### 4.3 Downside Floor
Search: "{TICKER} book value tangible value support"
- Where would value investors step in?
- What's the worst-case valuation support?

---

## PHASE 5: FINAL SYNTHESIS - THE DEAL MEMO

### THE ELEVATOR PITCH
[2-3 sentences: Why this stock, why NOW, what's the variant perception the market is missing?]

### THE ROCKET FUEL (3 Specific Catalysts)
| # | Catalyst | Expected Date | Price Impact |
|---|----------|---------------|--------------|
| 1 | [SPECIFIC event, not "sector is growing"] | [Date] | [X% move] |
| 2 | [SPECIFIC event] | [Date] | [X% move] |
| 3 | [SPECIFIC event] | [Date] | [X% move] |

**Quality Check:** Each catalyst must be COMPANY-SPECIFIC, not macro ("rates might fall").
If catalyst is vague like "the sector is growing," that's NOT a catalyst - dig deeper.

### THE BEAR TRAP
- **Bear Argument:** [The smartest short-seller argument]
- **Rebuttal:** [Why they're wrong - with SPECIFIC data/quotes]
- **Residual Risk:** [What concern remains, and why it's acceptable]

### THE MATH TO 50%
```
Current Price: ${PRICE}
Current Market Cap: $[X]
Current Multiple: [X]x [Sales/Earnings]

Scenario: [What needs to happen]
- Revenue/Earnings grow from $X to $Y ([Z]% growth)
- Multiple re-rates from [X]x to [Y]x (justified because [reason])
- New Market Cap: $Y × [new multiple] = $[Z]
- Implied Price: $[TARGET] (+[X]% upside)

Sanity Check: Is this above or below own 3-year average multiple? [Answer]
```

### FINAL VERDICT

**[ ] STRONG BUY** - High conviction. Fundamental inflection aligns with technical breakout. Catalysts are specific and imminent.

**[ ] SPECULATIVE BUY** - Thesis intact but execution-dependent. Smaller position size warranted.

**[ ] NO GO** - Bear case not dismantled OR catalysts are vague/distant OR math doesn't work.

**Conviction:** X/10
**Position Size:** FULL / REDUCED (50%) / PASS

---

### IF STRONG BUY:
- **Entry:** Monday at market open
- **Stop Loss:** 20% trailing from highest weekly close
- **Price Target:** $[X] (+[Y]%)
- **Key Assumption:** [The ONE thing that must be true for this to work]
- **Kill Switch:** [What would make you exit early, besides stop loss]

### IF NO GO:
- **Fatal Flaw:** [One sentence - be specific]
- **Reconsider If:** [What specific change would flip your view]

---

## QUALITY CONTROL CHECKLIST
Before submitting, verify:

☐ **Catalysts are SPECIFIC** - Not "sector tailwinds" but "Q2 earnings on May 15 expected to show 40% beat"
☐ **Avoided Consensus Trap** - If analysts expect 10% growth, that's priced in. Did you find evidence of 20%+?
☐ **Company-Specific Edge** - Catalysts work even if market is flat (not dependent on "rates falling")
☐ **Bear Case Addressed** - Either dismantled with data or flagged as fatal flaw
☐ **Math is Concrete** - Actual numbers in the "Math to 50%" section, not vague "could go up"

---

## EXAMPLE OF GOOD OUTPUT (What Success Looks Like)

**DEAL MEMO: IONQ Inc. (IONQ)**

**Elevator Pitch:** IONQ has technically broken out, but fundamentally it just passed a critical "Science to Engineering" inflection. The Seattle manufacturing facility announcement implies demand is 10x current revenue.

**Rocket Fuel:**
1. **$65M DoD Contract (Q3):** Budget filings show quantum allocation matching IONQ specs perfectly.
2. **Margin Inflection (Q2):** First gross margin positive quarter triggers institutional algo buying.
3. **Short Squeeze (18% SI):** Single positive "Forte" system PR could force cover.

**Bear Trap:**
- *Bear:* "They're burning cash and will dilute."
- *Rebuttal:* $300M cash = 3 years runway. CFO stated "No dilution needed in 2026" on Q1 call. Bear thesis is stale.

**Math to 50%:**
- Current: $12, 20x Sales on $60M revenue
- If $65M contract announced: Revenue → $100M
- Sector trades at 25x Sales: $100M × 25 = $2.5B market cap
- **Implied Price: $18+ (+50% upside)**

**VERDICT: STRONG BUY** - Fundamental inflection (margins) aligns perfectly with technical breakout.

---

**Remember:** We passed 3 quality gates to get here. We're not looking for reasons to reject.
We're looking for the VARIANT PERCEPTION that makes this a 50%+ winner or the FATAL FLAW that kills it.
'''


# =============================================================================
# QUICK DD PROMPT - For rapid screening when time-constrained
# =============================================================================

QUICK_DD_PROMPT = '''
# QUICK DUE DILIGENCE: {TICKER}

## Screening Context
- Theme: {THEME} ({THEME_CLASSIFICATION})
- Technical: Banker {BANKER}, Beta {BETA}
- Gatekeeper: {GATEKEEPER_RESULT}

## 5-Minute Research (Search Required)

1. **Last Earnings:** Beat/miss? Guidance raised/lowered?
2. **Next Catalyst:** Date? What is it?
3. **Bear Case:** What's the #1 short argument?
4. **Counter:** Why is the bear case wrong (or right)?
5. **Math to 50%:** Roughly, how does price get there?

## Quick Verdict

**ELEVATOR PITCH:** [One sentence - why this stock, why now]

**FATAL FLAW:** [None found / Describe it]

**VERDICT:** [STRONG BUY / SPEC BUY / NO GO]

**If buying:** Entry now at market / Wait for $X
'''


# =============================================================================
# HELPER FUNCTION TO GENERATE PROMPTS
# =============================================================================

def generate_deal_memo_prompt(
    ticker: str,
    theme: str,
    theme_classification: str = "PRIME",
    price: float = 0.0,
    banker: float = 0.0,
    beta: float = 0.0,
    red_flag_level: str = "CLEAN",
    catalyst_summary: str = "",
    gatekeeper_result: str = "PASS"
) -> str:
    """Generate a Deal Memo prompt for a specific ticker."""
    
    prompt = DEAL_MEMO_PROMPT.replace("{TICKER}", ticker)
    prompt = prompt.replace("{THEME}", theme)
    prompt = prompt.replace("{THEME_CLASSIFICATION}", theme_classification)
    prompt = prompt.replace("{PRICE}", f"{price:.2f}" if price > 0 else "[LOOKUP]")
    prompt = prompt.replace("{BANKER}", f"{banker:.0f}" if banker > 0 else "High")
    prompt = prompt.replace("{BETA}", f"{beta:.2f}" if beta > 0 else "≥1.5")
    prompt = prompt.replace("{RED_FLAG_LEVEL}", red_flag_level)
    prompt = prompt.replace("{CATALYST_SUMMARY}", catalyst_summary or "See gatekeeper analysis")
    prompt = prompt.replace("{GATEKEEPER_RESULT}", gatekeeper_result)
    
    return prompt


def generate_quick_dd_prompt(
    ticker: str,
    theme: str,
    theme_classification: str = "INVESTABLE",
    banker: float = 0.0,
    beta: float = 0.0,
    gatekeeper_result: str = "PASS"
) -> str:
    """Generate a Quick DD prompt for rapid screening."""
    
    prompt = QUICK_DD_PROMPT.replace("{TICKER}", ticker)
    prompt = prompt.replace("{THEME}", theme)
    prompt = prompt.replace("{THEME_CLASSIFICATION}", theme_classification)
    prompt = prompt.replace("{BANKER}", f"{banker:.0f}" if banker > 0 else "High")
    prompt = prompt.replace("{BETA}", f"{beta:.2f}" if beta > 0 else "≥1.5")
    prompt = prompt.replace("{GATEKEEPER_RESULT}", gatekeeper_result)
    
    return prompt


def print_dd_prompts_for_stocks(stocks: list, output_file: str = None):
    """
    Print Deal Memo prompts for a list of stocks that passed the Gatekeeper.
    
    Args:
        stocks: List of Stock objects or dicts with ticker info
        output_file: Optional file path to save prompts
    """
    
    if not stocks:
        print("\n  No stocks passed the Gatekeeper - no DD prompts to generate.")
        return
    
    output_lines = []
    
    output_lines.append("")
    output_lines.append("═" * 80)
    output_lines.append("  DUE DILIGENCE PROMPTS - Ready for Deep Research")
    output_lines.append("═" * 80)
    output_lines.append("")
    output_lines.append("  These stocks passed ALL gates (Technical → Theme → Gatekeeper).")
    output_lines.append("  Copy each prompt into a web-enabled AI for comprehensive due diligence.")
    output_lines.append("")
    output_lines.append("  Recommended: Claude with web search, GPT-4, or Gemini Pro")
    output_lines.append("")
    
    for i, stock in enumerate(stocks, 1):
        # Handle both Stock objects and dicts
        if hasattr(stock, 'symbol'):
            ticker = stock.symbol
            theme = getattr(stock, 'theme', 'Unknown')
            theme_verdict = getattr(stock, 'theme_verdict', 'GOOD FIT')
            price = getattr(stock, 'price', 0.0)
            banker = getattr(stock, 'banker', 0.0)
            beta = getattr(stock, 'beta', 0.0)
            red_flag_level = getattr(stock, 'red_flag_level', 'CLEAN')
            catalyst_summary = getattr(stock, 'catalyst_summary', '')
        else:
            ticker = stock.get('ticker', stock.get('symbol', 'UNKNOWN'))
            theme = stock.get('theme', 'Unknown')
            theme_verdict = stock.get('theme_verdict', 'GOOD FIT')
            price = stock.get('price', 0.0)
            banker = stock.get('banker', 0.0)
            beta = stock.get('beta', 0.0)
            red_flag_level = stock.get('red_flag_level', 'CLEAN')
            catalyst_summary = stock.get('catalyst_summary', '')
        
        # Determine theme classification from verdict
        if 'STRONG' in str(theme_verdict).upper():
            theme_class = "PRIME"
        elif 'GOOD' in str(theme_verdict).upper():
            theme_class = "INVESTABLE"
        else:
            theme_class = "SELECTIVE"
        
        output_lines.append("─" * 80)
        output_lines.append(f"  [{i}] {ticker} @ ${price:.2f} - {theme}")
        output_lines.append(f"      Banker: {banker:.0f} | Red Flags: {red_flag_level}")
        if catalyst_summary:
            output_lines.append(f"      Catalyst: {catalyst_summary[:60]}")
        output_lines.append("─" * 80)
        output_lines.append("")
        output_lines.append("  >>> COPY PROMPT BELOW <<<")
        output_lines.append("")
        
        prompt = generate_deal_memo_prompt(
            ticker=ticker,
            theme=theme,
            theme_classification=theme_class,
            price=price,
            banker=banker,
            beta=beta,
            red_flag_level=red_flag_level,
            catalyst_summary=catalyst_summary
        )
        
        output_lines.append(prompt)
        output_lines.append("")
        output_lines.append("  >>> END PROMPT <<<")
        output_lines.append("")
    
    # Print to console
    for line in output_lines:
        print(line)
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))
        print(f"\n  📄 Prompts also saved to: {output_file}")


# =============================================================================
# MAIN - Standalone usage
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python due_diligence_prompts.py TICKER [THEME]")
        print("Example: python due_diligence_prompts.py ALGM 'AI Power Infrastructure'")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    theme = sys.argv[2] if len(sys.argv) > 2 else "Unknown Theme"
    
    prompt = generate_deal_memo_prompt(ticker, theme)
    print(prompt)
