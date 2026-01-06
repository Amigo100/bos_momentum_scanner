#!/usr/bin/env python3
"""
Momentum Stock Assessor v2
==========================
Optimized for WEEKLY timeframe trading with longer hold periods.

CONTEXT:
- User trades US stocks from UK (Barclays ISA)
- Weekly timeframe to minimize FX costs
- Average hold period: ~4-8 weeks (can extend to months)
- Entry signal: BoS Up on weekly chart
- Exit signal: BoS Down on weekly chart (or 20% trailing stop)

This assessor determines: Should I take this trade NOW?

Usage:
    python momentum_assessor_v2.py NVDA TSLA IONQ RGTI
    python momentum_assessor_v2.py --file tickers.txt
    python momentum_assessor_v2.py --interactive

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY='your-key'
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import anthropic
except ImportError:
    print("Install with: pip install anthropic")
    sys.exit(1)


class Decision(Enum):
    TRADE = "TRADE"
    CONSIDER = "CONSIDER"
    SKIP = "SKIP"


@dataclass 
class Assessment:
    ticker: str
    decision: Decision
    conviction: int  # 1-5
    theme: str
    sector_status: str
    upside_potential: str
    hold_outlook: str
    bullish: List[str]
    risks: List[str]
    reasoning: str
    timestamp: str
    error: bool = False


SYSTEM_PROMPT = """You assess stocks for WEEKLY momentum trading. A buy signal has fired. Decide: TRADE, CONSIDER, or SKIP.

CONTEXT: UK trader, 4-8 week holds, needs moves >10% to justify costs.

SEARCH FOR:
1. Recent news (past 2 weeks) - catalysts, contracts, earnings
2. Sector/theme status - are peers also strong, or is this stock lagging?
3. Insider activity - note buying or selling WITH CONTEXT (10b5-1 scheduled? tax sale? or unusual?)
4. Red flags - short reports, lawsuits, dilution, lockups
5. Upcoming risks (1-3 months)

RED FLAGS (note with context):
- Insider selling: Scheduled 10b5-1 or tax sale = minor. Multiple execs dumping = severe.
- Short seller report: Old and recovered = minor. Recent and unresolved = severe.
- Litigation: Ambulance-chaser lawsuit = minor. SEC investigation = severe.
- Relative weakness: Stock flat while sector +20% = concern.
- Dilution: Shelf filed vs actively raising = different severity.

DECISION GUIDE:
- Strong bullish + no red flags → TRADE
- Bullish but 1 minor red flag → CONSIDER
- Multiple red flags OR 1 severe red flag → SKIP
- When uncertain, lean CONSIDER

RESPOND ONLY WITH JSON:
{
    "ticker": "SYMBOL",
    "decision": "TRADE|CONSIDER|SKIP",
    "conviction": 1-5,
    "theme": "Sector/theme",
    "sector_status": "Hot 🔥🔥🔥 | Warm 🔥🔥 | Cooling 🔥 | Cold ❄️",
    "upside_potential": "High (50%+) | Moderate (20-50%) | Limited (<20%)",
    "hold_outlook": "Strong | Uncertain | Deteriorating",
    "bullish": ["Factor 1", "Factor 2"],
    "risks": ["Risk with context", "Risk 2"],
    "reasoning": "2-3 sentences. What tips the decision? Be specific."
}"""


def create_client() -> anthropic.Anthropic:
    """Create Anthropic client"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def assess_stock(client: anthropic.Anthropic, ticker: str, max_retries: int = 5, use_web_search: bool = False) -> Assessment:
    """
    Assess a single stock for weekly timeframe trading.
    Includes exponential backoff for rate limit handling.
    
    Args:
        use_web_search: Enable web search (adds ~$0.05-0.10 per call). Default OFF.
    """
    ticker = ticker.upper().strip()
    
    # Adjust prompt based on whether web search is available
    if use_web_search:
        search_instructions = """Search for:
1. Recent news about {ticker} (past 2 weeks)
2. Sector/theme performance - are peers also moving?
3. Insider buying or selling (IMPORTANT - check recent SEC filings)
4. Red flags: short seller reports, lawsuits, investigations
5. Upcoming risks in next 1-3 months"""
    else:
        search_instructions = """Based on your knowledge (web search disabled for cost savings):
1. What is {ticker}'s primary business and sector?
2. What themes/trends does this company benefit from?
3. What are typical risks for this type of company?
4. Any known issues or red flags from your training data?"""
    
    user_prompt = f"""Assess {ticker} for momentum trading.

{search_instructions.format(ticker=ticker)}

Return JSON only."""

    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Build API parameters
            api_params = {
                "model": "claude-opus-4-5-20251101",
                "max_tokens": 1500,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }
            
            # Only add web search if enabled (costs ~$10/1000 searches)
            if use_web_search:
                api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
            
            response = client.messages.create(**api_params)
            
            # Extract text
            text = "".join([b.text for b in response.content if hasattr(b, 'text')])
            
            # Parse JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group())
                
                decision_map = {"TRADE": Decision.TRADE, "CONSIDER": Decision.CONSIDER, "SKIP": Decision.SKIP}
                
                return Assessment(
                    ticker=ticker,
                    decision=decision_map.get(data.get("decision", "SKIP"), Decision.SKIP),
                    conviction=data.get("conviction", 3),
                    theme=data.get("theme", "Unknown"),
                    sector_status=data.get("sector_status", "Unknown"),
                    upside_potential=data.get("upside_potential", "Unknown"),
                    hold_outlook=data.get("hold_outlook", "Unknown"),
                    bullish=data.get("bullish", []),
                    risks=data.get("risks", []),
                    reasoning=data.get("reasoning", ""),
                    timestamp=datetime.now().isoformat(),
                    error=False
                )
            
            raise ValueError("No valid JSON in response")
            
        except anthropic.RateLimitError as e:
            last_error = e
            # Extract wait time from error message if available
            error_str = str(e)
            wait_time = 60  # Default wait
            
            # Try to parse the retry-after or calculate backoff
            if "retry" in error_str.lower():
                import re as regex
                match = regex.search(r'(\d+)\s*second', error_str.lower())
                if match:
                    wait_time = int(match.group(1)) + 5
            else:
                # Exponential backoff: 60, 120, 240, 480, 960 seconds
                wait_time = 60 * (2 ** attempt)
            
            print(f"    ⚠️  Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        except anthropic.BadRequestError as e:
            # BadRequestError is status 400 - check for billing errors
            error_str = str(e).lower()
            if "credit balance" in error_str or "billing" in error_str:
                raise RuntimeError(f"BILLING_ERROR: {e}")
            # Other bad requests - don't retry
            last_error = e
            break
            
        except anthropic.APIError as e:
            last_error = e
            error_str = str(e).lower()
            
            # Check for billing/credit errors - these should fail immediately
            if "credit balance" in error_str or "billing" in error_str:
                raise RuntimeError(f"BILLING_ERROR: {e}")
            
            if "429" in str(e) or "rate" in error_str:
                # Rate limit error not caught as RateLimitError
                wait_time = 60 * (2 ** attempt)
                print(f"    ⚠️  API rate limit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                # Other API error - don't retry
                break
                
        except Exception as e:
            last_error = e
            break
    
    # All retries exhausted or non-retryable error
    return Assessment(
        ticker=ticker,
        decision=Decision.SKIP,
        conviction=0,
        theme="Error",
        sector_status="Unknown",
        upside_potential="Unknown",
        hold_outlook="Unknown",
        bullish=[],
        risks=[f"Assessment failed after {max_retries} attempts: {last_error}"],
        reasoning=f"Assessment failed: {last_error}",
        timestamp=datetime.now().isoformat(),
        error=True
    )


def assess_batch(client: anthropic.Anthropic, tickers: List[str], max_retries: int = 5, use_web_search: bool = False) -> List[Assessment]:
    """
    Assess multiple stocks in a single API call (batched).
    Much more cost-efficient than individual calls.
    
    Args:
        client: Anthropic client
        tickers: List of ticker symbols (max 10 recommended)
        max_retries: Number of retries on failure
        use_web_search: Enable web search (adds ~$0.10-0.30 per batch). Default OFF.
    
    Returns:
        List of Assessment objects
    """
    tickers = [t.upper().strip() for t in tickers]
    ticker_list = ", ".join(tickers)
    
    # Adjust prompt based on whether web search is available
    if use_web_search:
        search_instructions = """For EACH stock, search for:
1. Recent news (past 2 weeks)
2. Sector/theme status
3. Notable insider activity
4. Red flags (short reports, lawsuits, dilution)"""
    else:
        search_instructions = """For EACH stock, based on your knowledge (web search disabled for cost savings):
1. Primary business and sector
2. Relevant investment themes
3. Typical risks for this company type
4. Any known issues from your training data"""
    
    user_prompt = f"""Assess these stocks for momentum trading: {ticker_list}

{search_instructions}

Return a JSON array with one object per stock:
[
  {{
    "ticker": "SYMBOL",
    "decision": "TRADE|CONSIDER|SKIP",
    "conviction": 1-5,
    "theme": "Sector/theme",
    "sector_status": "Hot|Warm|Cooling|Cold",
    "upside_potential": "High|Moderate|Limited",
    "hold_outlook": "Strong|Uncertain|Deteriorating",
    "bullish": ["Factor 1"],
    "risks": ["Risk 1"],
    "reasoning": "Brief explanation"
  }},
  ...
]

Return ONLY the JSON array, no other text."""

    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Build API parameters
            api_params = {
                "model": "claude-opus-4-5-20251101",
                "max_tokens": 4000,  # More tokens for batch response
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }
            
            # Only add web search if enabled (costs ~$10/1000 searches)
            if use_web_search:
                api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
            
            response = client.messages.create(**api_params)
            
            # Extract text
            text = "".join([b.text for b in response.content if hasattr(b, 'text')])
            
            # Parse JSON array
            match = re.search(r'\[[\s\S]*\]', text)
            if match:
                data_list = json.loads(match.group())
                
                decision_map = {"TRADE": Decision.TRADE, "CONSIDER": Decision.CONSIDER, "SKIP": Decision.SKIP}
                assessments = []
                
                for data in data_list:
                    assessments.append(Assessment(
                        ticker=data.get("ticker", "UNKNOWN"),
                        decision=decision_map.get(data.get("decision", "SKIP"), Decision.SKIP),
                        conviction=data.get("conviction", 3),
                        theme=data.get("theme", "Unknown"),
                        sector_status=data.get("sector_status", "Unknown"),
                        upside_potential=data.get("upside_potential", "Unknown"),
                        hold_outlook=data.get("hold_outlook", "Unknown"),
                        bullish=data.get("bullish", []),
                        risks=data.get("risks", []),
                        reasoning=data.get("reasoning", ""),
                        timestamp=datetime.now().isoformat(),
                        error=False
                    ))
                
                # Check if all tickers were covered
                assessed_tickers = {a.ticker for a in assessments}
                for ticker in tickers:
                    if ticker not in assessed_tickers:
                        assessments.append(Assessment(
                            ticker=ticker,
                            decision=Decision.SKIP,
                            conviction=0,
                            theme="Missing",
                            sector_status="Unknown",
                            upside_potential="Unknown",
                            hold_outlook="Unknown",
                            bullish=[],
                            risks=["Not included in batch response"],
                            reasoning="Ticker was not assessed in batch response",
                            timestamp=datetime.now().isoformat(),
                            error=True
                        ))
                
                return assessments
            
            raise ValueError("No valid JSON array in response")
            
        except anthropic.RateLimitError as e:
            last_error = e
            wait_time = 60 * (2 ** attempt)
            print(f"    ⚠️  Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        except anthropic.BadRequestError as e:
            error_str = str(e).lower()
            if "credit balance" in error_str or "billing" in error_str:
                raise RuntimeError(f"BILLING_ERROR: {e}")
            last_error = e
            break
            
        except anthropic.APIError as e:
            last_error = e
            error_str = str(e).lower()
            
            if "credit balance" in error_str or "billing" in error_str:
                raise RuntimeError(f"BILLING_ERROR: {e}")
            
            if "429" in str(e) or "rate" in error_str:
                wait_time = 60 * (2 ** attempt)
                print(f"    ⚠️  API rate limit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                break
                
        except Exception as e:
            last_error = e
            break
    
    # All retries exhausted - return error assessments for all tickers
    return [
        Assessment(
            ticker=ticker,
            decision=Decision.SKIP,
            conviction=0,
            theme="Error",
            sector_status="Unknown",
            upside_potential="Unknown",
            hold_outlook="Unknown",
            bullish=[],
            risks=[f"Batch assessment failed: {last_error}"],
            reasoning=f"Assessment failed: {last_error}",
            timestamp=datetime.now().isoformat(),
            error=True
        )
        for ticker in tickers
    ]


def print_assessment(a: Assessment, verbose: bool = True):
    """Print formatted assessment"""
    
    symbols = {
        Decision.TRADE: ("🟢 TRADE", "\033[92m"),
        Decision.CONSIDER: ("🟡 CONSIDER", "\033[93m"),
        Decision.SKIP: ("🔴 SKIP", "\033[91m"),
    }
    
    display, color = symbols[a.decision]
    reset, bold = "\033[0m", "\033[1m"
    stars = "★" * a.conviction + "☆" * (5 - a.conviction)
    
    print(f"\n{'='*60}")
    print(f"{bold}{a.ticker}{reset} | {color}{display}{reset} | {stars}")
    print(f"{'='*60}")
    print(f"Theme: {a.theme} | Sector: {a.sector_status}")
    print(f"Upside: {a.upside_potential} | Outlook: {a.hold_outlook}")
    
    if verbose:
        if a.bullish:
            print(f"\n✅ BULLISH:")
            for x in a.bullish:
                print(f"   • {x}")
        
        if a.risks:
            print(f"\n⚠️  RISKS:")
            for x in a.risks:
                print(f"   • {x}")
    
    print(f"\n{bold}REASONING:{reset} {a.reasoning}")
    print(f"{'─'*60}")


def print_summary(assessments: List[Assessment]):
    """Print summary with action items"""
    
    trades = [a for a in assessments if a.decision == Decision.TRADE]
    considers = [a for a in assessments if a.decision == Decision.CONSIDER]
    skips = [a for a in assessments if a.decision == Decision.SKIP and not a.error]
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    if trades:
        print(f"\n🟢 TRADE ({len(trades)}):")
        for a in sorted(trades, key=lambda x: x.conviction, reverse=True):
            stars = "★" * a.conviction
            print(f"   {a.ticker} {stars} | {a.theme}")
    
    if considers:
        print(f"\n🟡 CONSIDER ({len(considers)}):")
        for a in considers:
            print(f"   {a.ticker} | {a.reasoning[:50]}...")
    
    if skips:
        print(f"\n🔴 SKIP ({len(skips)}):")
        for a in skips:
            print(f"   {a.ticker} | {a.reasoning[:50]}...")
    
    print(f"\n{'='*60}")
    
    if trades:
        tickers = ", ".join([a.ticker for a in sorted(trades, key=lambda x: x.conviction, reverse=True)])
        print(f"✅ TRADE: {tickers}")
    else:
        print("❌ No trades this week")
    
    print(f"{'='*60}\n")


def save_results(assessments: List[Assessment], filepath: str):
    """Save to JSON"""
    results = [{
        "ticker": a.ticker,
        "decision": a.decision.value,
        "conviction": a.conviction,
        "theme": a.theme,
        "sector_status": a.sector_status,
        "upside_potential": a.upside_potential,
        "hold_outlook": a.hold_outlook,
        "bullish": a.bullish,
        "risks": a.risks,
        "reasoning": a.reasoning,
        "timestamp": a.timestamp,
        "error": a.error
    } for a in assessments]
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {filepath}")


def load_tickers(filepath: str) -> List[str]:
    """Load tickers from file"""
    with open(filepath, 'r') as f:
        content = f.read()
    return [t.strip().upper() for t in re.split(r'[\s,\n]+', content) 
            if t.strip() and len(t.strip()) <= 5 and t.strip().isalpha()]


def interactive_mode(client: anthropic.Anthropic):
    """Interactive mode"""
    print("\n📊 Weekly Momentum Assessor - Interactive Mode")
    print("─" * 50)
    print("Enter tickers to assess (comma-separated)")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("Tickers: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            tickers = [t.strip().upper() for t in re.split(r'[\s,]+', user_input)
                      if t.strip() and len(t.strip()) <= 5 and t.strip().isalpha()]
            
            if not tickers:
                print("No valid tickers. Try again.")
                continue
            
            assessments = []
            for i, ticker in enumerate(tickers):
                print(f"\n⏳ [{i+1}/{len(tickers)}] Assessing {ticker}...")
                assessment = assess_stock(client, ticker)
                assessments.append(assessment)
                print_assessment(assessment)
                if i < len(tickers) - 1:
                    time.sleep(1.5)
            
            if len(assessments) > 1:
                print_summary(assessments)
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Weekly Momentum Stock Assessor v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s NVDA TSLA IONQ
  %(prog)s --file scanner_output.txt
  %(prog)s --interactive
  %(prog)s NVDA TSLA --output results.json
        """
    )
    
    parser.add_argument('tickers', nargs='*', help='Ticker symbols')
    parser.add_argument('--file', '-f', help='Load tickers from file')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--output', '-o', help='Save results to JSON')
    parser.add_argument('--brief', '-b', action='store_true', help='Brief output')
    
    args = parser.parse_args()
    client = create_client()
    
    if args.interactive:
        interactive_mode(client)
        return
    
    # Collect tickers
    tickers = []
    if args.file:
        tickers.extend(load_tickers(args.file))
    if args.tickers:
        tickers.extend([t.upper() for t in args.tickers if t.isalpha() and len(t) <= 5])
    
    # Remove duplicates
    tickers = list(dict.fromkeys(tickers))
    
    if not tickers:
        print("No tickers provided. Use --help for usage.")
        parser.print_help()
        sys.exit(1)
    
    print(f"\n📊 Weekly Momentum Assessor v2")
    print(f"{'─'*50}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Timeframe: WEEKLY | Exit: BoS Down or 20% trailing")
    print(f"{'─'*50}")
    
    # Assess
    assessments = []
    for i, ticker in enumerate(tickers):
        print(f"\n⏳ [{i+1}/{len(tickers)}] Assessing {ticker}...")
        assessment = assess_stock(client, ticker)
        assessments.append(assessment)
        print_assessment(assessment, verbose=not args.brief)
        if i < len(tickers) - 1:
            time.sleep(1.5)
    
    # Summary
    if len(assessments) > 1:
        print_summary(assessments)
    
    # Save
    if args.output:
        save_results(assessments, args.output)


if __name__ == "__main__":
    main()
