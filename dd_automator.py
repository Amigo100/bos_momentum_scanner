#!/usr/bin/env python3
"""
AUTOMATED DUE DILIGENCE MODULE
==============================

Runs automated deep due diligence on stocks that pass the Gatekeeper.
Integrates with the scanner pipeline as Step 7.5 between Gatekeeper and Sell Signal Check.

This module uses the Deal Memo methodology from due_diligence_prompts.py to validate
whether PASS stocks have realistic 50%+ return potential.

Usage:
    # From scanner.py (integrated)
    from dd_automator import run_automated_dd, DDResult
    results = run_automated_dd(pass_stocks, client, use_web_search=True)

    # Standalone testing
    python dd_automator.py RCAT VNET --quick
"""

import os
import sys
import re
import time
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Model configuration
MODEL_QUICK = "claude-sonnet-4-20250514"   # Quick DD - faster, cheaper
MODEL_FULL = "claude-opus-4-20250514"       # Full DD - deeper analysis
MAX_TOKENS_QUICK = 4000
MAX_TOKENS_FULL = 8000
THINKING_BUDGET_FULL = 10000

# Rate limiting
INTER_DD_DELAY = 10.0  # Seconds between DD calls
RATE_LIMIT_COOLDOWN = 60.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DDResult:
    """Result from automated due diligence analysis."""
    ticker: str
    dd_verdict: str = ""          # STRONG BUY / SPEC BUY / NO GO
    dd_conviction: int = 0        # 1-10 scale
    dd_position_size: str = ""    # FULL / REDUCED / PASS
    dd_analysis: str = ""         # Full analysis text
    dd_key_catalyst: str = ""     # Extracted key catalyst
    dd_fatal_flaw: str = ""       # Extracted fatal flaw (if NO GO)
    dd_math_to_50: str = ""       # Path to 50% return
    dd_bear_case: str = ""        # Bear case summary
    dd_bull_case: str = ""        # Bull case summary
    dd_thinking: str = ""         # Extended thinking (if available)
    dd_cost: float = 0.0          # Cost of this DD call
    dd_mode: str = ""             # QUICK or FULL
    error: str = ""               # Error message if failed

    def passed(self) -> bool:
        """Check if DD resulted in a buy verdict."""
        return self.dd_verdict in ["STRONG BUY", "SPEC BUY", "SPECULATIVE BUY"]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

QUICK_DD_SYSTEM = """You are a senior investment analyst conducting rapid due diligence on a stock that has already passed technical and thematic screening.

Your job is NOT to find reasons to reject - the stock has already passed multiple quality gates.
Your job is to quickly validate the bull case and identify any fatal flaws.

Be direct and actionable. If it looks good, say so. If there's a specific concern, name it."""

QUICK_DD_PROMPT = '''# QUICK DUE DILIGENCE: {ticker}

## Already Passed (No Need to Re-verify)
- Technical: Weekly breakout confirmed (BoS Up), Beta {beta:.2f}, Banker {banker:.0f}
- Theme: {theme} ({theme_verdict})
- Gatekeeper: PASS with conviction {conviction}/5
- Catalyst: {catalyst_summary}
- Red Flags: {red_flag_level}

## Your 5-Minute Mission

Search for recent information on {ticker} and answer:

1. **Last Earnings** (search: "{ticker} earnings results"): Beat or miss? Guidance raised/lowered?

2. **Next Catalyst** (search: "{ticker} upcoming catalyst 2026"): What's the next potential price mover and when?

3. **Bear Case** (search: "{ticker} short thesis risk"): What's the #1 argument against this stock?

4. **Counter-Argument**: Why is the bear case wrong (or why is it acceptable risk)?

5. **Math to 50%**: Roughly, what scenario gets this stock to +50%?

## Output Format

**ELEVATOR PITCH:** [One sentence - why this stock, why now]

**KEY CATALYST:** [Specific event and approximate date]

**BEAR CASE:** [The smart short-seller argument]

**COUNTER:** [Why the bear is wrong or risk is acceptable]

**MATH TO 50%:** [Brief scenario - e.g., "If revenue grows 30% and multiple re-rates from 15x to 20x"]

**FATAL FLAW:** [None found / Describe specific issue that kills the thesis]

**VERDICT:** [STRONG BUY / SPEC BUY / NO GO]

**CONVICTION:** [X/10]

**POSITION SIZE:** [FULL / REDUCED (50%) / PASS]
'''

FULL_DD_SYSTEM = """You are the Lead Portfolio Manager at a high-conviction Global Macro Hedge Fund specializing in aggressive growth equities.

This stock has ALREADY passed:
1. Technical screening (Weekly BoS breakout, high beta, institutional accumulation)
2. Thematic analysis (assigned to a hot theme with good fit)
3. Gatekeeper quality check (catalysts confirmed, red flags assessed)

Your job is to validate whether this stock has REALISTIC potential for 50-100%+ returns in 3-12 months.
We need a re-rating event - either earnings surprise, multiple expansion, or both.

Be thorough but decisive. We're not looking for reasons to reject every stock.
We're looking for the VARIANT PERCEPTION that makes this a 50%+ winner or the FATAL FLAW that kills it."""

FULL_DD_PROMPT = '''# DEAL MEMO: {ticker}

## Screening Status (Already Passed)
| Gate | Status | Details |
|------|--------|---------|
| Technical | PASSED | Weekly BoS breakout, Beta {beta:.2f}, Banker {banker:.0f} (Tier: {tier}) |
| Thematic | PASSED | {theme} - {theme_verdict} |
| Gatekeeper | PASSED | Conviction {conviction}/5, Red Flags: {red_flag_level} |

## Gatekeeper Summary
- **Catalyst:** {catalyst_summary}
- **Bullish Factors:** {bullish_factors}
- **Risk Factors:** {risk_factors}

## Investment Parameters
- Entry: Monday market open
- Target Hold: 3-12 months
- Exit: Weekly BoS breakdown OR 20% trailing stop
- Minimum Target: 50%+ return

---

## PHASE 1: EXPLOSIVE GROWTH INVESTIGATION

Search and analyze:
1. Revenue growth trajectory - is it ACCELERATING?
2. Operating leverage - will 10% revenue growth drive 50% earnings growth?
3. Net Revenue Retention (NRR) - are customers spending more?
4. Backlog/pipeline - any hidden revenue not yet recognized?

## PHASE 2: HIDDEN CATALYST SEARCH

Search for non-obvious catalysts:
1. Patent approvals, regulatory decisions pending
2. Management equity grants with price targets
3. Industry insider commentary (not Wall Street)
4. Upcoming investor days, conferences

## PHASE 3: BEAR KILLER PROTOCOL

Search: "{ticker} short thesis bear case risk"
1. What is the #1 bear argument?
2. Can you DISMANTLE it with data?
3. If not dismantled, is it a FATAL FLAW?

## PHASE 4: VALUATION REALITY CHECK

Search: "{ticker} valuation P/E P/S historical"
1. Current multiple vs OWN 3-year average
2. Path to 50%: What multiple expansion + earnings growth = 50%?
3. Downside floor: Where would value investors step in?

---

## OUTPUT REQUIREMENTS

### THE ELEVATOR PITCH
[2-3 sentences: Why this stock, why NOW, what's the variant perception?]

### THE ROCKET FUEL (Key Catalysts)
| # | Catalyst | Expected Date | Price Impact |
|---|----------|---------------|--------------|
| 1 | [SPECIFIC event] | [Date] | [X% move] |
| 2 | [SPECIFIC event] | [Date] | [X% move] |

### THE BEAR TRAP
- **Bear Argument:** [The smartest short-seller argument]
- **Rebuttal:** [Why they're wrong - with data]
- **Residual Risk:** [What concern remains]

### THE MATH TO 50%
```
Current Price: ${price:.2f}
Current Multiple: [X]x [Sales/Earnings]

Scenario: [What needs to happen]
- Earnings grow from $X to $Y ([Z]% growth)
- Multiple re-rates from [X]x to [Y]x
- Implied Price: $[TARGET] (+[X]% upside)
```

### FINAL VERDICT

**[ ] STRONG BUY** - High conviction. Fundamental inflection aligns with technical breakout.

**[ ] SPECULATIVE BUY** - Thesis intact but execution-dependent. Smaller position.

**[ ] NO GO** - Bear case not dismantled OR catalysts vague OR math doesn't work.

**Conviction:** X/10
**Position Size:** FULL / REDUCED (50%) / PASS

**Key Assumption:** [The ONE thing that must be true]
**Kill Switch:** [What would make you exit early]

### IF NO GO:
**Fatal Flaw:** [Specific reason]
**Reconsider If:** [What change would flip your view]
'''


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_dd_verdict(analysis: str) -> Dict[str, Any]:
    """
    Extract structured data from DD analysis text.

    Returns dict with:
        verdict, conviction, position_size, key_catalyst, fatal_flaw,
        math_to_50, bear_case, bull_case
    """
    result = {
        "verdict": "UNKNOWN",
        "conviction": 0,
        "position_size": "STANDARD",
        "key_catalyst": "",
        "fatal_flaw": "",
        "math_to_50": "",
        "bear_case": "",
        "bull_case": ""
    }

    if not analysis:
        return result

    text_upper = analysis.upper()

    # Extract verdict
    if "STRONG BUY" in text_upper:
        result["verdict"] = "STRONG BUY"
    elif "SPEC BUY" in text_upper or "SPECULATIVE BUY" in text_upper:
        result["verdict"] = "SPEC BUY"
    elif "NO GO" in text_upper or "NOGO" in text_upper:
        result["verdict"] = "NO GO"
    elif "PASS" in text_upper.split()[-50:]:  # "PASS" near the end usually means skip
        result["verdict"] = "NO GO"

    # Extract conviction (X/10 pattern)
    conviction_match = re.search(r'(?:conviction[:\s]*)?(\d+)\s*/\s*10', analysis, re.IGNORECASE)
    if conviction_match:
        result["conviction"] = int(conviction_match.group(1))

    # Extract position size
    if "REDUCED" in text_upper or "50%" in text_upper:
        result["position_size"] = "REDUCED"
    elif "FULL" in text_upper:
        result["position_size"] = "FULL"
    elif result["verdict"] == "NO GO":
        result["position_size"] = "PASS"

    # Extract key catalyst
    catalyst_patterns = [
        r'KEY CATALYST[:\s]*\[?([^\]\n]+)',
        r'ROCKET FUEL.*?\n.*?1\s*\|\s*([^\|]+)',
        r'(?:next|upcoming)\s+catalyst[:\s]*([^\n]+)',
    ]
    for pattern in catalyst_patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            result["key_catalyst"] = match.group(1).strip()[:200]
            break

    # Extract fatal flaw
    flaw_patterns = [
        r'FATAL FLAW[:\s]*\[?([^\]\n]+)',
        r'Fatal Flaw[:\s]*([^\n]+)',
    ]
    for pattern in flaw_patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            flaw = match.group(1).strip()
            if "none" not in flaw.lower():
                result["fatal_flaw"] = flaw[:200]
            break

    # Extract math to 50%
    math_patterns = [
        r'MATH TO 50%[:\s]*\[?([^\]\n]+)',
        r'Math to 50%[:\s]*([^\n]+)',
        r'Implied Price[:\s]*\$?([\d.]+)\s*\(([^)]+)\)',
    ]
    for pattern in math_patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            result["math_to_50"] = match.group(0)[:300]
            break

    # Extract bear case
    bear_patterns = [
        r'BEAR (?:CASE|ARGUMENT)[:\s]*\[?([^\]\n]+)',
        r'Bear Argument[:\s]*([^\n]+)',
    ]
    for pattern in bear_patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            result["bear_case"] = match.group(1).strip()[:200]
            break

    # Extract elevator pitch as bull case
    pitch_patterns = [
        r'ELEVATOR PITCH[:\s]*\[?([^\]\n]+)',
        r'Elevator Pitch[:\s]*([^\n]+)',
    ]
    for pattern in pitch_patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            result["bull_case"] = match.group(1).strip()[:200]
            break

    return result


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate API cost based on token usage."""
    if "opus" in model.lower():
        # Opus pricing: $15/1M input, $75/1M output
        return (input_tokens * 15 + output_tokens * 75) / 1_000_000
    else:
        # Sonnet pricing: $3/1M input, $15/1M output
        return (input_tokens * 3 + output_tokens * 15) / 1_000_000


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DD FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_single_dd(
    client: anthropic.Anthropic,
    ticker: str,
    price: float = 0.0,
    beta: float = 0.0,
    banker: float = 0.0,
    tier: str = "",
    theme: str = "",
    theme_verdict: str = "",
    conviction: int = 0,
    catalyst_summary: str = "",
    red_flag_level: str = "",
    bullish_factors: List[str] = None,
    risk_factors: List[str] = None,
    quick_mode: bool = True,
    use_web_search: bool = True,
    save_report: bool = False
) -> DDResult:
    """
    Run due diligence on a single stock.

    Args:
        client: Anthropic client
        ticker: Stock symbol
        price, beta, banker, tier: Technical data
        theme, theme_verdict: Thematic data
        conviction, catalyst_summary, red_flag_level: Gatekeeper data
        bullish_factors, risk_factors: Lists from gatekeeper
        quick_mode: Use quick DD (Sonnet) vs full DD (Opus)
        use_web_search: Enable web search
        save_report: Save full report to file

    Returns:
        DDResult with verdict, conviction, analysis
    """
    result = DDResult(ticker=ticker, dd_mode="QUICK" if quick_mode else "FULL")

    bullish_factors = bullish_factors or []
    risk_factors = risk_factors or []

    # Select model and prompt based on mode
    if quick_mode:
        model = MODEL_QUICK
        max_tokens = MAX_TOKENS_QUICK
        system_prompt = QUICK_DD_SYSTEM
        user_prompt = QUICK_DD_PROMPT.format(
            ticker=ticker,
            price=price,
            beta=beta,
            banker=banker,
            tier=tier or "N/A",
            theme=theme or "Unknown",
            theme_verdict=theme_verdict or "N/A",
            conviction=conviction,
            catalyst_summary=catalyst_summary or "Not specified",
            red_flag_level=red_flag_level or "CLEAN",
            bullish_factors=", ".join(bullish_factors[:3]) if bullish_factors else "N/A",
            risk_factors=", ".join(risk_factors[:3]) if risk_factors else "N/A"
        )
    else:
        model = MODEL_FULL
        max_tokens = MAX_TOKENS_FULL
        system_prompt = FULL_DD_SYSTEM
        user_prompt = FULL_DD_PROMPT.format(
            ticker=ticker,
            price=price,
            beta=beta,
            banker=banker,
            tier=tier or "N/A",
            theme=theme or "Unknown",
            theme_verdict=theme_verdict or "N/A",
            conviction=conviction,
            catalyst_summary=catalyst_summary or "Not specified",
            red_flag_level=red_flag_level or "CLEAN",
            bullish_factors=", ".join(bullish_factors) if bullish_factors else "N/A",
            risk_factors=", ".join(risk_factors) if risk_factors else "N/A"
        )

    try:
        # Build API call parameters
        api_params = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }

        # Add web search tool if enabled
        if use_web_search:
            api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

        # Add extended thinking for full mode
        if not quick_mode:
            api_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": THINKING_BUDGET_FULL
            }

        # Make API call
        response = client.messages.create(**api_params)

        # Extract content
        analysis_text = ""
        thinking_text = ""

        for block in response.content:
            if hasattr(block, 'text'):
                analysis_text += block.text
            elif hasattr(block, 'thinking'):
                thinking_text += block.thinking

        # Estimate cost
        input_tokens = response.usage.input_tokens if hasattr(response.usage, 'input_tokens') else 0
        output_tokens = response.usage.output_tokens if hasattr(response.usage, 'output_tokens') else 0
        result.dd_cost = estimate_cost(input_tokens, output_tokens, model)

        # Parse results
        result.dd_analysis = analysis_text
        result.dd_thinking = thinking_text

        extracted = extract_dd_verdict(analysis_text)
        result.dd_verdict = extracted["verdict"]
        result.dd_conviction = extracted["conviction"]
        result.dd_position_size = extracted["position_size"]
        result.dd_key_catalyst = extracted["key_catalyst"]
        result.dd_fatal_flaw = extracted["fatal_flaw"]
        result.dd_math_to_50 = extracted["math_to_50"]
        result.dd_bear_case = extracted["bear_case"]
        result.dd_bull_case = extracted["bull_case"]

        # Save report if requested
        if save_report:
            save_dd_report(result, theme, tier)

    except anthropic.RateLimitError:
        result.error = "Rate limited - try again later"
        result.dd_verdict = "ERROR"
    except anthropic.APIError as e:
        result.error = f"API error: {str(e)}"
        result.dd_verdict = "ERROR"
    except Exception as e:
        result.error = f"Error: {str(e)}"
        result.dd_verdict = "ERROR"

    return result


def save_dd_report(result: DDResult, theme: str, tier: str):
    """Save DD report to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"dd_{result.ticker}_{timestamp}.md"

    with open(filename, 'w') as f:
        f.write(f"# Due Diligence Report: {result.ticker}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Mode:** {result.dd_mode}\n")
        f.write(f"**Theme:** {theme}\n")
        f.write(f"**Tier:** {tier}\n\n")
        f.write("---\n\n")
        f.write(f"## Verdict: {result.dd_verdict}\n\n")
        f.write(f"**Conviction:** {result.dd_conviction}/10\n")
        f.write(f"**Position Size:** {result.dd_position_size}\n\n")
        if result.dd_key_catalyst:
            f.write(f"**Key Catalyst:** {result.dd_key_catalyst}\n\n")
        if result.dd_fatal_flaw:
            f.write(f"**Fatal Flaw:** {result.dd_fatal_flaw}\n\n")
        f.write("---\n\n")
        f.write("## Full Analysis\n\n")
        f.write(result.dd_analysis)
        if result.dd_thinking:
            f.write("\n\n---\n\n")
            f.write("## Extended Thinking\n\n")
            f.write("<details>\n<summary>Click to expand</summary>\n\n")
            f.write(f"```\n{result.dd_thinking}\n```\n")
            f.write("</details>\n")

    print(f"        Report saved: {filename}")


def run_automated_dd(
    stocks: List[Any],
    client: anthropic.Anthropic = None,
    quick_mode: bool = True,
    use_web_search: bool = True,
    save_reports: bool = False,
    max_stocks: int = None
) -> List[DDResult]:
    """
    Run automated due diligence on a list of stocks.

    Args:
        stocks: List of Stock objects (from scanner.py)
        client: Anthropic client (created if not provided)
        quick_mode: Use quick DD vs full DD
        use_web_search: Enable web search
        save_reports: Save individual reports
        max_stocks: Limit number of stocks to analyze

    Returns:
        List of DDResult objects
    """
    if not stocks:
        return []

    # Create client if not provided
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  ERROR: ANTHROPIC_API_KEY not set")
            return []
        client = anthropic.Anthropic(api_key=api_key)

    # Limit stocks if specified
    if max_stocks:
        stocks = stocks[:max_stocks]

    results = []
    total_cost = 0.0

    print(f"\n  Running {'Quick' if quick_mode else 'Full'} DD on {len(stocks)} stock(s)...")
    print(f"  Web search: {'Enabled' if use_web_search else 'Disabled'}")
    print()

    for i, stock in enumerate(stocks, 1):
        # Extract stock attributes (handle both Stock objects and dicts)
        if hasattr(stock, 'symbol'):
            ticker = stock.symbol
            price = getattr(stock, 'price', 0.0)
            beta = getattr(stock, 'beta', 0.0)
            banker = getattr(stock, 'banker', 0.0)
            tier = getattr(stock, 'tier', '')
            theme = getattr(stock, 'theme', '')
            theme_verdict = getattr(stock, 'theme_verdict', '')
            conviction = getattr(stock, 'conviction', 0)
            catalyst_summary = getattr(stock, 'catalyst_summary', '')
            red_flag_level = getattr(stock, 'red_flag_level', '')
            bullish_factors = getattr(stock, 'bullish_factors', [])
            risk_factors = getattr(stock, 'risk_factors', [])
        else:
            ticker = stock.get('symbol', stock.get('ticker', 'UNKNOWN'))
            price = stock.get('price', 0.0)
            beta = stock.get('beta', 0.0)
            banker = stock.get('banker', 0.0)
            tier = stock.get('tier', '')
            theme = stock.get('theme', '')
            theme_verdict = stock.get('theme_verdict', '')
            conviction = stock.get('conviction', 0)
            catalyst_summary = stock.get('catalyst_summary', '')
            red_flag_level = stock.get('red_flag_level', '')
            bullish_factors = stock.get('bullish_factors', [])
            risk_factors = stock.get('risk_factors', [])

        print(f"  [{i}/{len(stocks)}] {ticker} - {theme or 'Unknown Theme'}")
        print(f"        Analyzing...", end="", flush=True)

        result = run_single_dd(
            client=client,
            ticker=ticker,
            price=price,
            beta=beta,
            banker=banker,
            tier=tier,
            theme=theme,
            theme_verdict=theme_verdict,
            conviction=conviction,
            catalyst_summary=catalyst_summary,
            red_flag_level=red_flag_level,
            bullish_factors=bullish_factors,
            risk_factors=risk_factors,
            quick_mode=quick_mode,
            use_web_search=use_web_search,
            save_report=save_reports
        )

        results.append(result)
        total_cost += result.dd_cost

        # Print result summary
        if result.error:
            print(f" ERROR: {result.error}")
        else:
            verdict_icon = {
                "STRONG BUY": "++",
                "SPEC BUY": "+ ",
                "NO GO": "X ",
                "UNKNOWN": "? "
            }.get(result.dd_verdict, "? ")

            print(f" Done!")
            print(f"        [{verdict_icon}] {result.dd_verdict} ({result.dd_conviction}/10)")
            if result.dd_key_catalyst:
                print(f"        Catalyst: {result.dd_key_catalyst[:60]}...")
            if result.dd_fatal_flaw:
                print(f"        FLAW: {result.dd_fatal_flaw[:60]}...")
            print(f"        Position: {result.dd_position_size} | Cost: ${result.dd_cost:.3f}")

        print()

        # Rate limiting delay between stocks
        if i < len(stocks):
            time.sleep(INTER_DD_DELAY)

    # Print summary
    print("  " + "─" * 66)
    print("  DD SUMMARY")
    print("  " + "─" * 66)

    strong_buys = [r for r in results if r.dd_verdict == "STRONG BUY"]
    spec_buys = [r for r in results if r.dd_verdict in ["SPEC BUY", "SPECULATIVE BUY"]]
    no_gos = [r for r in results if r.dd_verdict == "NO GO"]
    errors = [r for r in results if r.dd_verdict == "ERROR" or r.error]

    print(f"  STRONG BUY: {len(strong_buys)} | SPEC BUY: {len(spec_buys)} | NO GO: {len(no_gos)} | Errors: {len(errors)}")
    print(f"  Total DD Cost: ${total_cost:.2f}")
    print()

    return results


def apply_dd_to_stocks(stocks: List[Any], dd_results: List[DDResult]) -> List[Any]:
    """
    Apply DD results back to Stock objects.

    Args:
        stocks: Original list of Stock objects
        dd_results: List of DDResult from run_automated_dd

    Returns:
        Updated stocks list with DD fields populated
    """
    # Create lookup by ticker
    dd_lookup = {r.ticker: r for r in dd_results}

    for stock in stocks:
        ticker = getattr(stock, 'symbol', stock.get('symbol', stock.get('ticker', '')))
        if ticker in dd_lookup:
            result = dd_lookup[ticker]

            # Apply DD fields to stock
            if hasattr(stock, 'dd_verdict'):
                stock.dd_verdict = result.dd_verdict
                stock.dd_conviction = result.dd_conviction
                stock.dd_position_size = result.dd_position_size
                stock.dd_analysis = result.dd_analysis
                stock.dd_key_catalyst = result.dd_key_catalyst
                stock.dd_fatal_flaw = result.dd_fatal_flaw

    return stocks


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TESTING
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Standalone testing of DD automator."""
    import argparse

    parser = argparse.ArgumentParser(description="Automated Due Diligence")
    parser.add_argument("tickers", nargs="+", help="Ticker(s) to analyze")
    parser.add_argument("--quick", action="store_true", help="Use quick DD mode (default)")
    parser.add_argument("--full", action="store_true", help="Use full DD mode (Opus)")
    parser.add_argument("--no-web", action="store_true", help="Disable web search")
    parser.add_argument("--save", action="store_true", help="Save reports to files")
    parser.add_argument("--theme", default="", help="Theme context")

    args = parser.parse_args()

    quick_mode = not args.full
    use_web_search = not args.no_web

    # Create mock stocks for testing
    stocks = []
    for ticker in args.tickers:
        stocks.append({
            "ticker": ticker.upper(),
            "symbol": ticker.upper(),
            "price": 0.0,
            "beta": 2.0,
            "banker": 65.0,
            "tier": "TIER1",
            "theme": args.theme or "Test Theme",
            "theme_verdict": "GOOD FIT",
            "conviction": 4,
            "catalyst_summary": "Testing",
            "red_flag_level": "CLEAN",
            "bullish_factors": ["Test factor 1"],
            "risk_factors": ["Test risk 1"]
        })

    print("\n" + "=" * 70)
    print("  AUTOMATED DUE DILIGENCE - STANDALONE TEST")
    print("=" * 70)

    results = run_automated_dd(
        stocks=stocks,
        quick_mode=quick_mode,
        use_web_search=use_web_search,
        save_reports=args.save
    )

    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70 + "\n")

    for result in results:
        print(f"  {result.ticker}:")
        print(f"    Verdict: {result.dd_verdict}")
        print(f"    Conviction: {result.dd_conviction}/10")
        print(f"    Position: {result.dd_position_size}")
        if result.dd_key_catalyst:
            print(f"    Catalyst: {result.dd_key_catalyst}")
        if result.dd_fatal_flaw:
            print(f"    Fatal Flaw: {result.dd_fatal_flaw}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
