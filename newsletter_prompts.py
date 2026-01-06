#!/usr/bin/env python3
"""
Newsletter Generation Prompts
=============================

Two prompts for weekly Substack newsletter generation:

1. MARKET_CONTEXT_PROMPT - Generate market analysis section
2. NEWSLETTER_COMPILATION_PROMPT - Compile final newsletter from all inputs

Usage:
    python newsletter_prompts.py market     # Print market context prompt
    python newsletter_prompts.py compile    # Print compilation prompt
    python newsletter_prompts.py all        # Print both prompts
"""

from datetime import datetime, timedelta

# =============================================================================
# MARKET CONTEXT GENERATION PROMPT
# =============================================================================

MARKET_CONTEXT_PROMPT = '''
# MARKET CONTEXT GENERATION

You are writing the market analysis section for a weekly investment newsletter focused on US momentum/growth stocks. The newsletter is aimed at UK investors using ISA accounts for US equity exposure.

**Today's Date:** {date}
**Week Ending:** {week_ending}

## YOUR TASK

Search for and synthesize the following into a cohesive 3-4 paragraph market summary:

### Required Data Points (Search for each):
1. **Index Performance This Week:**
   - S&P 500 weekly change (% and points)
   - NASDAQ Composite weekly change
   - Russell 2000 weekly change (small caps sentiment)

2. **Key Events This Week:**
   - Federal Reserve announcements or commentary
   - Major economic data releases (jobs, CPI, retail sales, etc.)
   - Significant earnings reports from bellwether companies

3. **Sector Rotation:**
   - Which sectors led this week?
   - Which sectors lagged?
   - Any notable rotation patterns?

4. **Volatility & Sentiment:**
   - VIX level and weekly change
   - Put/call ratio if notable
   - General market sentiment (risk-on/risk-off)

5. **Looking Ahead:**
   - Key events next week (Fed meetings, major earnings, economic data)
   - Any looming risks or catalysts

## OUTPUT FORMAT

Write in this structure (markdown):

```
## 📊 Market Context

[Opening paragraph: Overall market performance this week - what happened and why]

[Second paragraph: Sector dynamics - what's leading, what's lagging, any rotation]

[Third paragraph: Key events that moved markets - Fed, data, earnings]

[Fourth paragraph: Looking ahead - what to watch next week, setup for momentum stocks]
```

## STYLE GUIDELINES
- Professional but accessible tone
- Specific numbers (e.g., "S&P 500 rose 1.2% to 4,850")
- Connect macro to momentum stock implications
- No hedging language like "it remains to be seen"
- Confident analysis, acknowledge uncertainty where real
- UK investor perspective (mention GBP/USD if significant move)

## DO NOT INCLUDE
- Generic statements without data
- Overly bullish or bearish bias
- Investment recommendations
- Disclaimers (those come later in the newsletter)

Generate the market context section now.
'''


# =============================================================================
# NEWSLETTER COMPILATION PROMPT
# =============================================================================

NEWSLETTER_COMPILATION_PROMPT = '''
# WEEKLY NEWSLETTER COMPILATION

You are the editor compiling the final weekly edition of "BoS Momentum Scanner" - a Substack newsletter for momentum stock investors. You have all the raw materials below and need to produce a polished, publication-ready newsletter.

## NEWSLETTER IDENTITY
- **Name:** BoS Momentum Scanner Weekly
- **Audience:** UK investors trading US momentum stocks via ISA accounts
- **Frequency:** Weekly (published Saturday/Sunday)
- **Tone:** Professional, data-driven, actionable
- **Platform:** Substack

---

## RAW INPUTS

### 1. MARKET CONTEXT
{market_context}

### 2. SCANNER BRIEFING (Themes & Signals)
{scanner_briefing}

### 3. DUE DILIGENCE OUTPUTS
{due_diligence}

---

## YOUR TASK

Compile these inputs into a polished Substack newsletter with the following structure:

### REQUIRED SECTIONS

**1. TITLE & HOOK**
- Compelling title that captures this week's key theme/signal
- One-line subtitle/hook
- Example: "Power Play: AI Infrastructure Signals Fire" / "Two high-conviction entries as data center demand accelerates"

**2. MARKET CONTEXT**
- Use the market context provided
- Light editing for flow only
- Keep all specific data points

**3. THIS WEEK'S THEMES**
- Extract PRIME and INVESTABLE themes from scanner briefing
- Brief explanation of why each theme is hot NOW
- Focus on themes with actual signals this week

**4. NEW SIGNALS**
For each stock that passed all gates (🟢 PASS):
- **Ticker & Company** (header)
- **The Setup** (2-3 sentences from scanner data)
- **Why Now** (key catalyst from DD)
- **The Math** (path to 50%+ from DD)
- **Risk to Monitor** (main concern from DD)
- **Action:** Entry price, position sizing guidance
- **[CHART: TICKER]** placeholder for screenshot

**5. WATCHLIST** (if any 🟡 CAUTION signals)
- Brief mention of stocks worth watching
- Why waiting (earnings, extended, etc.)
- What would trigger entry

**6. PORTFOLIO UPDATE**
- Open positions with current P&L
- Any caution/sell signals and what action to take
- Brief commentary on existing positions

**7. LOOKING AHEAD**
- What to watch next week
- Upcoming catalysts for open positions or watchlist
- Any macro events that matter

**8. FOOTER**
- Standard disclaimer
- Next scan date
- How to use the newsletter

---

## FORMATTING RULES

1. **Use markdown** - Headers, bold, tables, bullet points
2. **Chart placeholders** - Use `[CHART: TICKER]` where screenshots go
3. **Tables for data** - Open positions, signal metrics
4. **Keep it scannable** - Busy readers should get the gist from headers
5. **No walls of text** - Break up long sections
6. **Specific numbers** - Always include price, %, dates

## TONE RULES

1. **Confident but not arrogant** - "This looks strong" not "This will definitely work"
2. **Educational** - Explain WHY, not just WHAT
3. **Actionable** - Clear entry/exit guidance
4. **Honest about risk** - Every trade can fail
5. **No hype** - Let the data speak

## LENGTH TARGET
- 1,500-2,500 words total
- Readers should finish in 8-12 minutes

---

## OUTPUT

Generate the complete newsletter in markdown format, ready to paste into Substack.

Begin with the title and work through each section.
'''


# =============================================================================
# QUICK DD SUMMARY PROMPT (Optional - for extracting key points from DD)
# =============================================================================

DD_SUMMARY_PROMPT = '''
# DD SUMMARY EXTRACTION

I have a detailed due diligence report below. Please extract ONLY the key points needed for the newsletter:

## DD REPORT:
{dd_report}

## EXTRACT:

**Elevator Pitch:** [One sentence - why this stock, why now]

**Key Catalyst:** [Most important upcoming event with date]

**The Math to 50%:**
- Current: $X at Yx multiple
- Target: $Y at Zx multiple  
- Path: [Brief explanation]

**Bear Case & Rebuttal:** [One sentence each]

**Main Risk:** [The #1 thing that could go wrong]

**Verdict:** [STRONG BUY / SPEC BUY / NO GO]

Keep each item to 1-2 sentences maximum.
'''


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_market_context_prompt() -> str:
    """Get the market context prompt with current date filled in."""
    today = datetime.now()
    
    # Find the Friday of this week (or last Friday if today is Sat/Sun)
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0 and today.weekday() != 4:
        days_since_friday = 7
    friday = today - timedelta(days=days_since_friday)
    
    return MARKET_CONTEXT_PROMPT.format(
        date=today.strftime("%B %d, %Y"),
        week_ending=friday.strftime("%B %d, %Y")
    )


def get_compilation_prompt(
    market_context: str = "[PASTE MARKET CONTEXT HERE]",
    scanner_briefing: str = "[PASTE SCANNER BRIEFING HERE]",
    due_diligence: str = "[PASTE DUE DILIGENCE OUTPUTS HERE]"
) -> str:
    """Get the compilation prompt with placeholders or actual content."""
    return NEWSLETTER_COMPILATION_PROMPT.format(
        market_context=market_context,
        scanner_briefing=scanner_briefing,
        due_diligence=due_diligence
    )


def get_dd_summary_prompt(dd_report: str = "[PASTE DD REPORT HERE]") -> str:
    """Get the DD summary extraction prompt."""
    return DD_SUMMARY_PROMPT.format(dd_report=dd_report)


def print_prompt(prompt: str, title: str):
    """Print a prompt with clear boundaries."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print("\n>>> COPY FROM HERE >>>")
    print()
    print(prompt)
    print()
    print("<<< COPY TO HERE <<<")
    print("=" * 80 + "\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
Newsletter Prompts Generator
============================

Usage:
    python newsletter_prompts.py market     # Market context generation prompt
    python newsletter_prompts.py compile    # Final newsletter compilation prompt
    python newsletter_prompts.py summary    # DD summary extraction prompt
    python newsletter_prompts.py all        # All prompts
    
Workflow:
    1. Run scanner.py --web-search (generates briefing)
    2. Use 'market' prompt in Claude to generate market context
    3. Run DD prompts for each PASS signal (from due_diligence_prompts.py)
    4. Use 'compile' prompt with all inputs to generate final newsletter
    5. Add charts and publish to Substack
""")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "market":
        print_prompt(get_market_context_prompt(), "MARKET CONTEXT GENERATION PROMPT")
        
    elif command == "compile":
        print_prompt(get_compilation_prompt(), "NEWSLETTER COMPILATION PROMPT")
        
    elif command == "summary":
        print_prompt(get_dd_summary_prompt(), "DD SUMMARY EXTRACTION PROMPT")
        
    elif command == "all":
        print_prompt(get_market_context_prompt(), "MARKET CONTEXT GENERATION PROMPT")
        print_prompt(get_compilation_prompt(), "NEWSLETTER COMPILATION PROMPT")
        print_prompt(get_dd_summary_prompt(), "DD SUMMARY EXTRACTION PROMPT")
        
    else:
        print(f"Unknown command: {command}")
        print("Use: market, compile, summary, or all")
        sys.exit(1)
