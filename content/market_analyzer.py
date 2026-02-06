#!/usr/bin/env python3
"""
MARKET ANALYZER - Automated Market Context Generation
=====================================================

Generates the market context section for the weekly newsletter using Claude + web search.
This automates the manual step of copying the market prompt to Claude.

Usage:
    python market_analyzer.py                    # Generate market analysis
    python market_analyzer.py --save             # Save to file
    python market_analyzer.py --output PATH      # Custom output path

Output:
    trades/market_analysis.md    # Latest market analysis
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
TRADES_DIR = BASE_DIR / "trades"

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 3000


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketAnalysisResult:
    """Result from market analysis generation."""
    analysis: str = ""
    cost: float = 0.0
    error: str = ""

    def success(self) -> bool:
        return bool(self.analysis) and not self.error


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

MARKET_ANALYSIS_SYSTEM = """You are a senior market analyst writing the weekly market context section for Sterling Signals, a momentum trading newsletter on Substack focused on US growth stocks.

Your audience: US active investors and swing traders seeking systematic momentum opportunities.

Style guidelines:
- Professional but accessible tone
- Specific numbers always (e.g., "S&P 500 rose 1.2% to 5,240")
- Connect macro events to momentum stock implications
- No hedging language like "it remains to be seen"
- Confident analysis with real data
- Reference pre-market futures and after-hours movers when relevant
- Mention DXY (dollar index) only if significant macro impact

Write in markdown format."""

MARKET_ANALYSIS_PROMPT = '''Generate the market context section for this week's newsletter.

**Today's Date:** {date}
**Week Ending:** {week_ending}

## Your Task

Use web search to find and synthesize the following into a cohesive 3-4 paragraph market summary:

### Required Data Points (search for each):

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
   - General market sentiment (risk-on/risk-off)

5. **Looking Ahead:**
   - Key events next week (Fed meetings, major earnings, economic data)
   - Any looming risks or catalysts

## Output Format

Write in this exact structure (markdown):

## 📊 Market Context

[Opening paragraph: Overall market performance this week - what happened and why, with specific numbers]

[Second paragraph: Sector dynamics - what's leading, what's lagging, any rotation patterns]

[Third paragraph: Key events that moved markets - Fed, data, earnings, with specific numbers]

[Fourth paragraph: Looking ahead - what to watch next week, setup for momentum stocks]

DO NOT include:
- Generic statements without data
- Overly bullish or bearish bias
- Investment recommendations
- Disclaimers

Generate the market context section now, using web search for current data.'''


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_market_analysis(client: Optional[anthropic.Anthropic] = None) -> MarketAnalysisResult:
    """
    Generate market analysis using Claude with web search.

    Args:
        client: Anthropic client (created if not provided)

    Returns:
        MarketAnalysisResult with analysis text and cost
    """
    result = MarketAnalysisResult()

    # Create client if not provided
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            result.error = "ANTHROPIC_API_KEY not set"
            return result
        client = anthropic.Anthropic(api_key=api_key)

    # Calculate dates
    today = datetime.now()

    # Find the Friday of this week (or last Friday if today is Sat/Sun)
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0 and today.weekday() != 4:
        days_since_friday = 7
    friday = today - timedelta(days=days_since_friday)

    # Build prompt
    user_prompt = MARKET_ANALYSIS_PROMPT.format(
        date=today.strftime("%B %d, %Y"),
        week_ending=friday.strftime("%B %d, %Y")
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=MARKET_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}]
        )

        # Extract text from response
        analysis_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                analysis_text += block.text

        result.analysis = analysis_text.strip()

        # Estimate cost
        input_tokens = response.usage.input_tokens if hasattr(response.usage, 'input_tokens') else 0
        output_tokens = response.usage.output_tokens if hasattr(response.usage, 'output_tokens') else 0
        result.cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000

    except anthropic.RateLimitError:
        result.error = "Rate limited - try again later"
    except anthropic.APIError as e:
        result.error = f"API error: {str(e)}"
    except Exception as e:
        result.error = f"Error: {str(e)}"

    return result


def save_market_analysis(analysis: str, output_path: Optional[Path] = None) -> Path:
    """Save market analysis to file."""
    if output_path is None:
        output_path = TRADES_DIR / "market_analysis.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(f"# Market Analysis\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(analysis)

    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate market analysis via Claude + web search")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--save", "-s", action="store_true", help="Save to file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "═" * 60)
        print("  MARKET ANALYZER - Claude-Powered Market Context")
        print("═" * 60)
        print(f"\n  📅 Date: {datetime.now().strftime('%B %d, %Y')}")
        print("  🔍 Searching for market data...")

    result = run_market_analysis()

    if result.error:
        print(f"\n  ❌ Error: {result.error}")
        return 1

    if not args.quiet:
        print(f"  ✅ Analysis generated (cost: ${result.cost:.3f})")
        print("\n" + "─" * 60)
        print(result.analysis)
        print("─" * 60)

    if args.save or args.output:
        output_path = Path(args.output) if args.output else None
        saved_path = save_market_analysis(result.analysis, output_path)
        if not args.quiet:
            print(f"\n  💾 Saved to: {saved_path}")

    if not args.quiet:
        print("\n" + "═" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
