#!/usr/bin/env python3
"""
COMPREHENSIVE DUE DILIGENCE TOOL
================================

Final manual step before investing. Uses Claude Opus 4.5 with extended thinking
to deeply analyze a stock that has passed all automated gates.

This is NOT meant to find reasons to reject every stock - it's meant to give you
the confidence (or appropriate caution) to invest your hard-earned money.

Usage:
    python due_diligence.py NVDA
    python due_diligence.py MARA --budget 5000
    python due_diligence.py LUNR --save
    
Context:
    - US active investor or swing trader
    - Weekly timeframe, 4-8 week typical hold (can extend to 1 year)
    - Looking for significant returns (15-50%+ opportunities)
    - Stock has already passed: Technical gates, Thematic analyzer, Momentum assessor
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-opus-4-20250514"  # Opus 4.5 for deep analysis
MAX_THINKING_TOKENS = 10000      # Allow extensive reasoning
MAX_OUTPUT_TOKENS = 8000         # Comprehensive report


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a seasoned investment analyst conducting final due diligence for a US-based swing trader. Your role is to provide a thorough, balanced assessment that helps the investor make an informed decision.

IMPORTANT CONTEXT:
- The stock has ALREADY passed automated screening (technical breakout, hot theme, momentum check)
- Your job is NOT to find reasons to reject - it's to provide comprehensive analysis
- The investor is a US active trader seeking momentum opportunities
- Typical hold: 4-8 weeks, but willing to hold up to 1 year for the right opportunity
- Target: Significant returns (15-50%+ opportunities aligned with systematic approach)
- Exit strategy: Disciplined risk management with predetermined exits

YOUR ANALYTICAL FRAMEWORK:

1. THEME VALIDATION (Is this theme truly in a sustainable uptrend?)
   - What's driving this theme? (Policy, technology shift, supply/demand imbalance)
   - How long could this theme run? (Months? Years?)
   - What would cause the theme to reverse?
   - Compare to past similar themes - where are we in the cycle?

2. COMPANY POSITIONING (Is this the RIGHT stock for this theme?)
   - Pure play vs. diversified exposure
   - Market position (leader, challenger, laggard?)
   - Competitive moat or advantages
   - Management quality and alignment with shareholders
   - Balance sheet strength (can they survive volatility?)

3. VALUATION REALITY CHECK (Not demanding "cheap" - but is it reasonable?)
   - Current valuation vs. historical range
   - Valuation vs. growth rate (PEG-style thinking)
   - What's priced in already? What could surprise to the upside?
   - Downside floor - where would value investors step in?

4. CATALYST TIMELINE (What drives the next 4-8 weeks?)
   - Upcoming earnings, guidance, product launches
   - Sector-wide catalysts (policy announcements, industry events)
   - Technical setup (is the breakout confirmed or extended?)

5. RISK ASSESSMENT (Be specific, not generic)
   - Company-specific risks (NOT generic "market could fall")
   - What's the realistic worst case in your timeframe?
   - Position sizing implications
   - What would make you exit early?

6. THE BEAR CASE (Steelman the opposition)
   - Why might smart money be selling here?
   - What are you potentially missing?
   - Historical analogs that didn't work out

7. THE BULL CASE (Why this could work exceptionally well)
   - What's the upside scenario?
   - What catalysts could accelerate the move?
   - Why might this be better than it looks?

OUTPUT REQUIREMENTS:

Your analysis should conclude with:

VERDICT: One of:
- "PROCEED WITH CONVICTION" - Strong setup, size appropriately
- "PROCEED WITH CAUTION" - Valid opportunity but manage size/expectations  
- "WAIT FOR BETTER ENTRY" - Like the stock but timing concerns
- "PASS ON THIS ONE" - Specific issues override the setup

CONVICTION: 1-10 scale with reasoning

SUGGESTED POSITION SIZE: As % of typical position (50%, 100%, 150%)

KEY MONITORING POINTS: What to watch that would change the thesis

TONE GUIDANCE:
- Be direct and actionable, not wishy-washy
- If it looks good, say so confidently
- If there are concerns, be specific about what and why
- Remember: the goal is to help make money, not to cover yourself by being perpetually cautious
- A good analyst knows when to be bullish"""


# ═══════════════════════════════════════════════════════════════════════════════
# USER PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

USER_PROMPT_TEMPLATE = """Please conduct comprehensive due diligence on {ticker} for a potential swing trade.

WHAT I ALREADY KNOW (from automated screening):
- Technical: Weekly breakout confirmed (BoS Up), strong institutional accumulation
- Theme: {theme_info}
- Initial Assessment: Passed momentum check

INVESTMENT PARAMETERS:
- Entry: Would be at Monday's market open
- Target Hold: 4-8 weeks (flexible to 1 year if thesis intact)
- Exit Rules: Weekly BoS breakdown OR 20% trailing stop from highs
- Position Budget: {budget}
- Minimum Target: 10%+ return (to justify UK->US FX costs)

PLEASE RESEARCH AND ANALYZE:

1. Search for recent news, earnings, analyst coverage on {ticker}
2. Research the broader theme/sector momentum
3. Look for any red flags: insider selling, short interest, litigation, dilution
4. Find the bull and bear cases being made by analysts/investors
5. Check valuation metrics and how they compare historically
6. Identify upcoming catalysts in the next 1-3 months

After your research, provide your comprehensive analysis following the framework in your instructions.

Take your time to think through this carefully - I'm trusting you with real investment capital."""


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_due_diligence(ticker: str, theme_info: str = "Identified as hot sector",
                       budget: str = "Standard position size", save_report: bool = False) -> tuple:
    """Run comprehensive due diligence using Opus 4.5 with extended thinking."""
    
    ticker = ticker.upper().strip()
    
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "COMPREHENSIVE DUE DILIGENCE".center(68) + "║")
    print("║" + f"{ticker}".center(68) + "║")
    print("║" + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print(f"  Model: {MODEL} (Extended Thinking)")
    print(f"  Budget: {budget}")
    print(f"  Theme Context: {theme_info}")
    print()
    print("  " + "─" * 66)
    print("  🧠 Deep analysis in progress... (this may take 1-2 minutes)")
    print("  " + "─" * 66)
    print()
    
    # Create client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        ticker=ticker,
        theme_info=theme_info,
        budget=budget
    )
    
    try:
        # Use streaming to show progress and capture thinking
        thinking_content = []
        response_content = []
        
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={
                "type": "enabled",
                "budget_tokens": MAX_THINKING_TOKENS
            },
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        ) as stream:
            
            current_block_type = None
            
            for event in stream:
                # Handle different event types
                if hasattr(event, 'type'):
                    if event.type == 'content_block_start':
                        if hasattr(event, 'content_block'):
                            block = event.content_block
                            if hasattr(block, 'type'):
                                current_block_type = block.type
                                if current_block_type == 'thinking':
                                    print("  💭 Thinking deeply...", end="", flush=True)
                                elif current_block_type == 'text':
                                    print("\n\n  📝 Writing analysis...\n")
                                    print("  " + "═" * 66)
                                    print()
                    
                    elif event.type == 'content_block_delta':
                        if hasattr(event, 'delta'):
                            delta = event.delta
                            if hasattr(delta, 'type'):
                                if delta.type == 'thinking_delta' and hasattr(delta, 'thinking'):
                                    thinking_content.append(delta.thinking)
                                    # Show progress dots
                                    if len(thinking_content) % 50 == 0:
                                        print(".", end="", flush=True)
                                elif delta.type == 'text_delta' and hasattr(delta, 'text'):
                                    response_content.append(delta.text)
                                    print(delta.text, end="", flush=True)
                    
                    elif event.type == 'content_block_stop':
                        if current_block_type == 'thinking':
                            print(" Done!")
        
        # Combine response
        full_response = "".join(response_content)
        full_thinking = "".join(thinking_content)
        
        print("\n")
        print("  " + "═" * 66)
        
        # Save report if requested
        if save_report:
            save_analysis_report(ticker, theme_info, budget, full_thinking, full_response)
        
        return full_response, full_thinking
        
    except anthropic.APIError as e:
        print(f"\n  ❌ API Error: {e}")
        return None, None
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def save_analysis_report(ticker: str, theme_info: str, budget: str,
                         thinking: str, analysis: str) -> None:
    """Save the full analysis report to a file."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"dd_{ticker}_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(f"# Due Diligence Report: {ticker}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Theme Context:** {theme_info}\n\n")
        f.write(f"**Budget:** {budget}\n\n")
        f.write("---\n\n")
        f.write("## Analysis\n\n")
        f.write(analysis)
        f.write("\n\n---\n\n")
        f.write("## Extended Thinking (Internal Reasoning)\n\n")
        f.write("<details>\n<summary>Click to expand thinking process</summary>\n\n")
        f.write("```\n")
        f.write(thinking)
        f.write("\n```\n\n")
        f.write("</details>\n")
    
    print(f"\n  📄 Report saved: {filename}")


def load_stock_context(ticker: str) -> dict:
    """Try to load context from recent analysis if available."""
    
    analysis_log = BASE_DIR / "trades" / "analysis_log.csv"
    
    if not analysis_log.exists():
        return {}
    
    try:
        import csv
        with open(analysis_log, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('symbol', '').upper() == ticker.upper():
                    return {
                        'theme': row.get('theme', ''),
                        'theme_verdict': row.get('theme_verdict', ''),
                        'pure_play_score': row.get('pure_play_score', ''),
                        'tier': row.get('tier', ''),
                        'beta': row.get('beta', ''),
                        'reasoning': row.get('reasoning', '')
                    }
    except (OSError, csv.Error):
        pass
    
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_verdict(analysis: str) -> dict:
    """Extract structured verdict from analysis text."""
    
    result = {
        "verdict": "UNKNOWN",
        "conviction": "?",
        "position_size": "STANDARD",
        "key_risk": "",
        "bull_case": "",
        "bear_case": ""
    }
    
    if not analysis:
        return result
    
    text = analysis.upper()
    
    # Extract verdict
    if "PROCEED WITH CONVICTION" in text:
        result["verdict"] = "PROCEED WITH CONVICTION"
    elif "PROCEED WITH CAUTION" in text:
        result["verdict"] = "PROCEED WITH CAUTION"
    elif "WAIT FOR BETTER ENTRY" in text or "WAIT" in text.split()[:50]:
        result["verdict"] = "WAIT FOR BETTER ENTRY"
    elif "PASS ON THIS ONE" in text or "DO NOT INVEST" in text:
        result["verdict"] = "PASS ON THIS ONE"
    elif "INVEST" in text.split()[:100]:
        result["verdict"] = "INVEST"
    
    # Extract conviction (look for X/10 pattern)
    import re
    conviction_match = re.search(r'(\d+)\s*/\s*10', analysis)
    if conviction_match:
        result["conviction"] = conviction_match.group(1)
    
    # Extract position size
    if "REDUCED" in text or "SMALLER" in text or "HALF" in text:
        result["position_size"] = "REDUCED"
    elif "FULL" in text:
        result["position_size"] = "FULL"
    
    return result


def run_due_diligence_for_pipeline(
    ticker: str,
    budget: str = "$5,000",
    theme: str = "",
    hold_period: str = "4-8 weeks",
    stop_loss: int = 20,
    save_report: bool = False
) -> dict:
    """
    Run due diligence and return structured result for pipeline integration.
    
    Returns:
        dict with keys: ticker, verdict, conviction, position_size, analysis, thinking
    """
    
    theme_info = theme if theme else "Hot sector (passed thematic screening)"
    
    analysis, thinking = run_due_diligence(
        ticker=ticker,
        theme_info=theme_info,
        budget=budget,
        save_report=save_report
    )
    
    if not analysis:
        return {
            "ticker": ticker,
            "verdict": "ERROR",
            "conviction": "0",
            "position_size": "NONE",
            "analysis": None,
            "thinking": None,
            "error": "Analysis failed"
        }
    
    # Extract structured data from analysis
    extracted = extract_verdict(analysis)
    
    return {
        "ticker": ticker,
        "verdict": extracted["verdict"],
        "conviction": extracted["conviction"],
        "position_size": extracted["position_size"],
        "analysis": analysis,
        "thinking": thinking
    }


# Alias for backward compatibility
run_dd = run_due_diligence_for_pipeline


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comprehensive Due Diligence - Final check before investing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python due_diligence.py NVDA
  python due_diligence.py MARA --budget "$5,000"
  python due_diligence.py LUNR --theme "Defense/Aerospace - Space segment"
  python due_diligence.py MU --save
  python due_diligence.py CCJ --budget "$10,000" --theme "Uranium/Nuclear" --save
        """
    )
    parser.add_argument("ticker", help="Stock ticker to analyze")
    parser.add_argument("--budget", default="Standard position size", 
                        help="Investment budget for position sizing advice")
    parser.add_argument("--theme", default=None,
                        help="Theme/sector context (auto-detected if available)")
    parser.add_argument("--save", action="store_true",
                        help="Save full report to reports/ directory")
    
    args = parser.parse_args()
    
    ticker = args.ticker.upper().strip()
    
    # Try to load context from previous analysis
    context = load_stock_context(ticker)
    
    if args.theme:
        theme_info = args.theme
    elif context.get('theme'):
        theme_info = f"{context['theme']} ({context.get('theme_verdict', 'N/A')} - {context.get('pure_play_score', 'N/A')}% pure play)"
        if context.get('reasoning'):
            theme_info += f"\nPrior assessment: {context['reasoning'][:200]}"
    else:
        theme_info = "Hot sector (passed thematic screening)"
    
    # Run analysis
    analysis, thinking = run_due_diligence(
        ticker=ticker,
        theme_info=theme_info,
        budget=args.budget,
        save_report=args.save
    )
    
    if analysis:
        print("\n  ✅ Analysis complete!")
        if not args.save:
            print("  💡 Tip: Use --save to keep a record of this analysis")
    else:
        print("\n  ❌ Analysis failed - check API key and try again")
        return 1
    
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
