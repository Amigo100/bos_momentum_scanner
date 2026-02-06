#!/usr/bin/env python3
"""
GATEKEEPER v1.0 - Final Quality Gate for Swing Trades
======================================================

PURPOSE:
This is the FINAL gate before entry. The stock has already passed:
  ✓ Technical Signal (BoS Up, Beta ≥1.5, Banker ≥55)
  ✓ Thematic Gate (PRIME/INVESTABLE theme, GOOD/STRONG fit)

This gate answers: "Is this stock capable of 50-100%+ returns in 3-8 months?"

PHILOSOPHY:
We are NOT looking for "safe" stocks. We are looking for:
  - Asymmetric setups with strong catalysts
  - Clean governance (no hidden landmines)
  - Stocks where the thesis can play out over months

DECISION FRAMEWORK:
  PASS   = Strong catalyst + clean governance → Enter position
  CAUTION = Good setup but timing risk (e.g., earnings in 3 days) → Wait or size down
  FAIL   = Red flag detected → Do not trade, move on

Usage:
    from gatekeeper import run_gatekeeper, GatekeeperResult
    results = run_gatekeeper(client, stocks, themes_context, use_web_search=True)
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import anthropic
except ImportError:
    print("Install with: pip install anthropic")
    sys.exit(1)


class GateDecision(Enum):
    PASS = "PASS"
    CAUTION = "CAUTION"
    FAIL = "FAIL"


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, handling strings like 'N/A', '19.1%', etc."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove common suffixes and try to parse
        cleaned = value.strip().rstrip('%').replace(',', '')
        if cleaned.lower() in ('n/a', 'na', 'none', 'unknown', ''):
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


@dataclass
class GatekeeperResult:
    """Result from the Gatekeeper analysis"""
    ticker: str
    decision: GateDecision
    conviction: int  # 1-5 stars
    
    # Theme (passed through from prior analysis)
    theme: str
    theme_fit: str  # STRONG/GOOD/MODERATE
    
    # Catalyst Assessment
    catalyst_present: bool
    catalyst_summary: str  # "Earnings Feb 15, Investor Day Feb 20"
    days_to_catalyst: int  # -1 if none found
    
    # Red Flag Assessment  
    red_flag_level: str  # CLEAN / MINOR / SEVERE
    red_flags: List[str]  # Specific issues found
    
    # Analyst/Street Sentiment
    analyst_trend: str  # BULLISH / NEUTRAL / BEARISH
    short_interest_pct: float
    
    # Key Data Points
    key_bullish: List[str]  # Top 3 reasons to buy
    key_risks: List[str]    # Top 3 risks to monitor
    
    # Final Synthesis
    reasoning: str  # 2-3 sentence synthesis
    action: str     # Specific recommendation
    
    # Meta
    timestamp: str = ""
    error: bool = False
    error_msg: str = ""
    
    # Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def get_cost(self, model: str = "sonnet") -> float:
        """Estimate cost for this analysis"""
        if "opus" in model.lower():
            input_rate, output_rate = 15.0, 75.0
        elif "sonnet" in model.lower():
            input_rate, output_rate = 3.0, 15.0
        else:  # haiku
            input_rate, output_rate = 0.25, 1.25
        
        return (self.input_tokens / 1_000_000 * input_rate + 
                self.output_tokens / 1_000_000 * output_rate)


# =============================================================================
# GATEKEEPER SYSTEM PROMPT
# =============================================================================

GATEKEEPER_SYSTEM_PROMPT = """You are a Senior Risk Manager at a Long/Short Equity Hedge Fund.

CONTEXT:
You are conducting the FINAL quality gate before position entry. The stock has already passed:
- Technical buy signal (weekly momentum breakout)
- Thematic analysis (confirmed to be in a "hot" investment theme)

YOUR MISSION:
Determine if this stock has REALISTIC potential for 50-100%+ returns over 3-8 months.
This is NOT about finding "safe" stocks. It's about finding ASYMMETRIC setups.

WHAT MAKES A 50-100% MOVER:
1. CATALYST - A specific upcoming event that forces institutional re-rating
   (Earnings beat + raise, product launch, FDA approval, major contract, M&A)
2. CLEAN SETUP - No hidden landmines that will destroy the thesis
   (No imminent dilution, no CFO fleeing, no SEC investigation)
3. STREET UNDERWEIGHT - Analysts behind the curve, room for upgrades
4. THEME MOMENTUM - The sector/theme itself is in a bull phase

IMMEDIATE DISQUALIFIERS (→ FAIL):
- Auditor resignation or delayed 10-K filing
- CFO/CEO resigned in last 60 days (without clear succession)
- Shelf offering (S-3) filed in last 30 days with no stated use
- Active SEC or DOJ investigation
- Earnings in < 5 trading days (binary risk too high)

CAUTION FLAGS (→ CAUTION, not FAIL):
- Earnings in 5-15 trading days (consider waiting)
- Short interest > 25% (high volatility, but not disqualifying)
- Single analyst downgrade (one opinion, not trend)
- Insider selling under 10b5-1 plan (scheduled, not panic)

DECISION FRAMEWORK:
- PASS: Clear catalyst within 90 days + no disqualifiers + thesis intact
- CAUTION: Good setup but timing issue OR one minor flag worth monitoring  
- FAIL: Any immediate disqualifier OR multiple red flags OR no catalyst visible

OUTPUT FORMAT - Return ONLY valid JSON:
{
    "ticker": "SYMBOL",
    "decision": "PASS|CAUTION|FAIL",
    "conviction": 1-5,
    "theme": "The assigned theme from context",
    "theme_fit": "STRONG|GOOD|MODERATE",
    
    "catalyst_present": true/false,
    "catalyst_summary": "Earnings Feb 15 (est beat likely), Investor Day Feb 20",
    "days_to_catalyst": 45,
    
    "red_flag_level": "CLEAN|MINOR|SEVERE",
    "red_flags": ["Specific issue with context"],
    
    "analyst_trend": "BULLISH|NEUTRAL|BEARISH",
    "short_interest_pct": 8.5,
    
    "key_bullish": ["Reason 1", "Reason 2", "Reason 3"],
    "key_risks": ["Risk 1 to monitor", "Risk 2"],
    
    "reasoning": "2-3 sentences synthesizing why PASS/CAUTION/FAIL",
    "action": "Specific recommendation (e.g., 'Enter Monday at open' or 'Wait until after Feb 15 earnings')"
}
"""


# =============================================================================
# GATEKEEPER IMPLEMENTATION
# =============================================================================

def create_client() -> anthropic.Anthropic:
    """Create Anthropic client"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def run_gatekeeper_single(
    client: anthropic.Anthropic,
    ticker: str,
    theme: str,
    theme_fit: str,
    price: float,
    themes_context: str = "",
    use_web_search: bool = False,
    max_retries: int = 5
) -> GatekeeperResult:
    """
    Run thorough gatekeeper analysis on a single stock.
    
    Args:
        ticker: Stock symbol
        theme: Assigned theme from thematic analysis
        theme_fit: STRONG/GOOD/MODERATE
        price: Current price
        themes_context: Full themes context from Step 6
        use_web_search: If True, use web search for current data. If False, use model knowledge.
    """
    
    # Adjust prompt based on web search availability
    if use_web_search:
        search_instructions = """REQUIRED SEARCHES (consolidated for efficiency):

1. Search: "{ticker} earnings date analyst consensus short interest 2025"
   → Find: next earnings date, estimate trend (rising/falling), short interest %

2. Search: "{ticker} SEC filing insider buying selling CFO recent news"
   → Find: any 8-K material events, auditor changes, insider sentiment, governance red flags

3. (Only if concerns found) Search: "{ticker} dilution shelf offering S-3"
   → Check for pending dilution only if prior searches suggest risk

After completing searches, synthesize findings into the JSON response.
Focus on what matters: Is there a catalyst? Are there dealbreaker red flags?"""
    else:
        search_instructions = """Based on your knowledge (web search disabled for testing):
1. What you know about upcoming earnings and catalysts
2. Any known governance issues or red flags
3. Analyst sentiment and short interest levels
4. Any known dilution history

NOTE: Without web search, your information may be outdated. 
Flag any areas where current data would be needed for a real decision."""
    
    user_prompt = f"""Conduct a Gatekeeper analysis for: {ticker}

STOCK CONTEXT:
- Ticker: {ticker}
- Current Price: ${price:.2f}
- Assigned Theme: {theme}
- Theme Fit: {theme_fit}

{themes_context}

{search_instructions}

Remember: We want 50-100%+ return potential. A clean stock with no catalyst is CAUTION (dead money).
A stock with strong catalyst but minor red flag is still PASS if the risk is manageable.

Return ONLY the JSON object, no other text."""

    last_error = None
    input_tokens = 0
    output_tokens = 0
    
    for attempt in range(max_retries):
        try:
            # Build API parameters - use Sonnet 4.5 for cost efficiency
            api_params = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 3000,  # Reduced - Sonnet is more concise
                "system": GATEKEEPER_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }
            
            # Only add web search tool if enabled
            if use_web_search:
                api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
            
            response = client.messages.create(**api_params)
            
            # Track token usage
            if hasattr(response, 'usage'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
            
            # Extract text content
            text = "".join([b.text for b in response.content if hasattr(b, 'text')])
            
            # Parse JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group())
                
                decision_map = {
                    "PASS": GateDecision.PASS,
                    "CAUTION": GateDecision.CAUTION,
                    "FAIL": GateDecision.FAIL
                }
                
                return GatekeeperResult(
                    ticker=ticker,
                    decision=decision_map.get(data.get("decision", "CAUTION"), GateDecision.CAUTION),
                    conviction=data.get("conviction", 3),
                    theme=data.get("theme", theme),
                    theme_fit=data.get("theme_fit", theme_fit),
                    catalyst_present=data.get("catalyst_present", False),
                    catalyst_summary=data.get("catalyst_summary", "None identified"),
                    days_to_catalyst=data.get("days_to_catalyst", -1),
                    red_flag_level=data.get("red_flag_level", "UNKNOWN"),
                    red_flags=data.get("red_flags", []),
                    analyst_trend=data.get("analyst_trend", "UNKNOWN"),
                    short_interest_pct=_safe_float(data.get("short_interest_pct"), 0.0),
                    key_bullish=data.get("key_bullish", []),
                    key_risks=data.get("key_risks", []),
                    reasoning=data.get("reasoning", ""),
                    action=data.get("action", ""),
                    error=False,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            
            raise ValueError("No valid JSON in response")
            
        except anthropic.RateLimitError as e:
            last_error = e
            wait_time = 60 * (attempt + 1)
            print(f"    ⚠️  Rate limit hit, waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except anthropic.BadRequestError as e:
            error_str = str(e).lower()
            if "credit" in error_str or "billing" in error_str:
                raise RuntimeError("BILLING_ERROR: Add credits at console.anthropic.com")
            last_error = e
            break
            
        except Exception as e:
            last_error = e
            break
    
    # Return error result
    return GatekeeperResult(
        ticker=ticker,
        decision=GateDecision.CAUTION,
        conviction=0,
        theme=theme,
        theme_fit=theme_fit,
        catalyst_present=False,
        catalyst_summary="Analysis failed",
        days_to_catalyst=-1,
        red_flag_level="UNKNOWN",
        red_flags=[f"Analysis error: {last_error}"],
        analyst_trend="UNKNOWN",
        short_interest_pct=0.0,
        key_bullish=[],
        key_risks=["Could not complete analysis"],
        reasoning=f"Analysis failed after {max_retries} attempts",
        action="Manual review required",
        error=True,
        error_msg=str(last_error)
    )


def run_gatekeeper_batch(
    client: anthropic.Anthropic,
    stocks: List[Dict],
    themes_context: str = "",
    delay_between: float = 5.0,
    use_web_search: bool = False
) -> List[GatekeeperResult]:
    """
    Run gatekeeper on multiple stocks sequentially.
    
    Args:
        stocks: List of dicts with {ticker, theme, theme_fit, price}
        themes_context: Full themes context string
        delay_between: Seconds between API calls
        use_web_search: If True, use web search for current data
    
    Returns:
        List of GatekeeperResult objects
    """
    results = []
    
    for i, stock in enumerate(stocks):
        ticker = stock.get("ticker", stock.get("symbol", "UNKNOWN"))
        print(f"\n  [{i+1}/{len(stocks)}] Gatekeeper: {ticker}")
        print(f"  " + "─" * 50)
        
        try:
            result = run_gatekeeper_single(
                client=client,
                ticker=ticker,
                theme=stock.get("theme", "Unknown"),
                theme_fit=stock.get("theme_fit", stock.get("theme_verdict", "GOOD")),
                price=stock.get("price", 0.0),
                themes_context=themes_context,
                use_web_search=use_web_search
            )
            
            results.append(result)
            
            # Print result immediately (with error handling for formatting issues)
            try:
                print_gatekeeper_result(result)
            except Exception as print_err:
                print(f"  ⚠ Display error for {ticker}: {print_err}")
                print(f"  │ Decision: {result.decision.value} │ Conviction: {result.conviction}")
            
        except Exception as e:
            print(f"  ⚠ Analysis error for {ticker}: {e}")
            # Create error result so we don't lose the stock
            error_result = GatekeeperResult(
                ticker=ticker,
                decision=GateDecision.CAUTION,
                conviction=0,
                theme=stock.get("theme", "Unknown"),
                theme_fit=stock.get("theme_fit", "GOOD"),
                catalyst_present=False,
                catalyst_summary="Analysis failed",
                days_to_catalyst=-1,
                red_flag_level="UNKNOWN",
                red_flags=[f"Analysis error: {e}"],
                analyst_trend="UNKNOWN",
                short_interest_pct=0.0,
                key_bullish=[],
                key_risks=["Could not complete analysis"],
                reasoning=f"Analysis failed: {e}",
                action="Manual review required",
                error=True,
                error_msg=str(e)
            )
            results.append(error_result)
        
        # Delay between calls to avoid rate limits
        if i < len(stocks) - 1:
            time.sleep(delay_between)
    
    return results


def print_gatekeeper_result(result: GatekeeperResult) -> None:
    """Print a single gatekeeper result in a clean format"""
    
    # Decision emoji and color
    if result.decision == GateDecision.PASS:
        decision_str = "🟢 PASS"
    elif result.decision == GateDecision.CAUTION:
        decision_str = "🟡 CONSIDER"
    else:
        decision_str = "🔴 FAIL"
    
    # Handle None conviction
    conviction = result.conviction if result.conviction is not None else 0
    stars = "★" * conviction + "☆" * (5 - conviction)
    
    # Handle None theme
    theme_display = (result.theme or "Unknown")[:25]
    
    print(f"""
  ┌{'─' * 60}┐
  │ {result.ticker:<8} │ {decision_str:<12} │ {stars} │ {theme_display:<25} │
  ├{'─' * 60}┤""")
    
    # Catalyst - handle None values
    catalyst_icon = "✓" if result.catalyst_present else "✗"
    catalyst_summary = (result.catalyst_summary or "None identified")[:45]
    print(f"  │ Catalyst: {catalyst_icon} {catalyst_summary:<45} │")
    
    days_to_catalyst = result.days_to_catalyst if result.days_to_catalyst is not None else -1
    if days_to_catalyst > 0:
        print(f"  │          └─ {days_to_catalyst} days until next catalyst{' ' * 25} │")
    
    # Red Flags - handle None values
    red_flag_level = result.red_flag_level or "UNKNOWN"
    flag_icon = {"CLEAN": "✓", "MINOR": "⚠", "SEVERE": "✗"}.get(red_flag_level, "?")
    print(f"  │ Red Flags: {flag_icon} {red_flag_level:<47} │")
    
    red_flags = result.red_flags or []
    for flag in red_flags[:2]:
        print(f"  │            └─ {str(flag)[:42]:<42} │")
    
    # Street Sentiment - handle None values and string values
    analyst_trend = result.analyst_trend or "UNKNOWN"
    short_interest = _safe_float(result.short_interest_pct, 0.0)
    print(f"  │ Analysts: {analyst_trend:<10} │ Short Interest: {short_interest:>5.1f}%{' ' * 15} │")
    
    # Key Points - handle None/empty lists
    print(f"  ├{'─' * 60}┤")
    print(f"  │ BULLISH:{' ' * 51} │")
    key_bullish = result.key_bullish or []
    for point in key_bullish[:3]:
        print(f"  │   • {str(point)[:53]:<53} │")
    if not key_bullish:
        print(f"  │   • {'(none identified)':<53} │")
    
    print(f"  │ RISKS:{' ' * 53} │")
    key_risks = result.key_risks or []
    for risk in key_risks[:3]:
        print(f"  │   • {str(risk)[:53]:<53} │")
    if not key_risks:
        print(f"  │   • {'(none identified)':<53} │")
    
    # Reasoning and Action - handle None
    print(f"  ├{'─' * 60}┤")
    
    # Word wrap reasoning
    reasoning = result.reasoning or "No detailed reasoning provided."
    reasoning_words = reasoning.split()
    lines = []
    current_line = ""
    for word in reasoning_words:
        if len(current_line) + len(word) + 1 <= 56:
            current_line += (" " + word if current_line else word)
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    for line in lines[:3]:
        print(f"  │ {line:<58} │")
    
    print(f"  ├{'─' * 60}┤")
    action = (result.action or "Review manually")[:50]
    print(f"  │ ACTION: {action:<50} │")
    print(f"  └{'─' * 60}┘")


def print_gatekeeper_summary(results: List[GatekeeperResult]) -> None:
    """Print summary of all gatekeeper results including cost tracking"""
    
    passes = [r for r in results if r.decision == GateDecision.PASS]
    cautions = [r for r in results if r.decision == GateDecision.CAUTION]
    fails = [r for r in results if r.decision == GateDecision.FAIL]
    
    # Calculate total costs
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    # Sonnet pricing: $3/1M input, $15/1M output
    total_cost = (total_input / 1_000_000 * 3.0) + (total_output / 1_000_000 * 15.0)
    
    print(f"""
  ╔{'═' * 60}╗
  ║{'GATEKEEPER SUMMARY'.center(60)}║
  ╠{'═' * 60}╣
  ║  🟢 PASS:    {len(passes):<3} {'─ Ready for entry':<42} ║
  ║  🟡 CONSIDER: {len(cautions):<3} {'─ Wait or size down':<42} ║
  ║  🔴 FAIL:    {len(fails):<3} {'─ Do not trade':<42} ║
  ╠{'═' * 60}╣""")
    
    if passes:
        print(f"  ║ READY TO TRADE:{' ' * 43} ║")
        for r in passes:
            conviction = r.conviction if r.conviction is not None else 0
            stars = "★" * conviction + "☆" * (5 - conviction)
            catalyst = (r.catalyst_summary or "Catalyst pending")[:35]
            print(f"  ║   {r.ticker:<6} {stars} │ {catalyst:<35} ║")
    
    if cautions:
        print(f"  ║ WAIT / MONITOR:{' ' * 43} ║")
        for r in cautions:
            reason = (r.reasoning[:40] if r.reasoning else "Review needed")
            print(f"  ║   {r.ticker:<6} │ {reason:<48} ║")
    
    if fails:
        print(f"  ║ REJECTED:{' ' * 49} ║")
        for r in fails:
            flag = (r.red_flags[0][:45] if r.red_flags else "Failed gate")
            print(f"  ║   {r.ticker:<6} │ {flag:<48} ║")
    
    # Cost summary
    print(f"  ╠{'═' * 60}╣")
    print(f"  ║ 💰 COST: {total_input:,} in + {total_output:,} out tokens = ${total_cost:.4f}  ║")
    print(f"  ╚{'═' * 60}╝")


# =============================================================================
# MAIN / CLI
# =============================================================================

def main() -> None:
    """Command-line interface for standalone gatekeeper runs"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gatekeeper - Final Quality Gate")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols to analyze")
    parser.add_argument("--theme", default="Unknown", help="Investment theme")
    parser.add_argument("--price", type=float, default=0.0, help="Current price")
    args = parser.parse_args()
    
    if not args.tickers:
        print("Usage: python gatekeeper.py AAPL NVDA PLTR --theme 'AI Infrastructure'")
        return
    
    client = create_client()
    
    print("\n" + "═" * 70)
    print("  GATEKEEPER - Final Quality Gate for Swing Trades")
    print("═" * 70)
    print("  Looking for: 50-100%+ return potential over 3-8 months")
    print("  Checking: Catalysts, Red Flags, Analyst Sentiment")
    print("─" * 70)
    
    stocks = [{"ticker": t, "theme": args.theme, "theme_fit": "GOOD", "price": args.price} 
              for t in args.tickers]
    
    results = run_gatekeeper_batch(client, stocks)
    
    print("\n")
    print_gatekeeper_summary(results)


if __name__ == "__main__":
    main()
