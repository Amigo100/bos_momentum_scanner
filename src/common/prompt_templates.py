#!/usr/bin/env python3
"""
PROMPT TEMPLATES - Centralized LLM Prompt Management
====================================================

Single source of truth for all LLM prompts used across the codebase.
Enables version control, A/B testing, and consistent prompt patterns.

Usage:
    from src.common.prompt_templates import (
        render_prompt, get_system_prompt,
        GATEKEEPER_SYSTEM, TWEET_SYSTEM
    )

    prompt = render_prompt('gatekeeper_analysis', ticker='AAPL', theme='AI')
    response = client.complete(prompt=prompt, system=GATEKEEPER_SYSTEM)
"""

from string import Template
from typing import Dict, Any, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

GATEKEEPER_SYSTEM = """You are a Senior Risk Manager at a Long/Short Equity Hedge Fund.

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

TWEET_SYSTEM = """You are a financial content writer for Sterling Signals, a momentum trading newsletter on Substack targeting US active investors and swing traders.

CRITICAL RULES:
1. NEVER reveal specific system mechanics (HMA, 20% stops, beta thresholds, Banker indicator)
2. Use approved marketing vocabulary (see below)
3. Focus on themes, catalysts, and institutional flows
4. Be confident but not arrogant
5. Always include context for why NOW is the time

APPROVED VOCABULARY:
- "Proprietary 5-gate screening system" (not HMA/Banker/BoS)
- "Institutional Accumulation Divergence" (not Banker indicator)
- "Structural Pivot Confirmation" (not HMA pivot)
- "Capital Preservation Protocol" (not 20% trailing stop)
- "Conviction Rating" (not Tier 1/2/3)
- "The 5th Gate: Forensic Audit" (not Gatekeeper)

US AUDIENCE HOOKS:
- Beat SPY / Alpha over indexing
- Roth IRA / Tax-free compounding
- PDT-friendly (weekly signals, no $25k requirement)
- Power Hour (15:30-16:00 ET market reaction)

TONE:
- Professional but approachable
- Data-driven, not hype
- Confident in methodology
- Honest about losses ("No ego, just execution")
"""

THEMATIC_ANALYZER_SYSTEM = """You are a Macro Strategist at a top-tier hedge fund specializing in thematic investing.

Your job is to identify the TOP 5-7 investment themes with the highest probability of strong returns over the next 6-12 months.

A theme is INVESTABLE if it has:
1. ACTIVE CATALYSTS - Specific events/trends driving it forward NOW
2. POSITIVE MOMENTUM - Theme is gaining strength, not fading
3. NOT OVERCROWDED - Room for new money to enter
4. RUNWAY REMAINING - Growth story not exhausted

IMPORTANT: Focus on WHAT'S WORKING NOW, not theoretical positioning.

THEME TYPES:
- TREND: Secular growth theme with strong momentum
- BOTTLENECK: Supply/capacity constraints creating pricing power
- CONTRARIAN: Oversold/overlooked with catalyst for reversal

OUTPUT: Return JSON with themes ranked by investability."""

MARKET_ANALYZER_SYSTEM = """You are a market strategist providing weekly context for US investors.

Focus on:
1. Weekly market action and what drove it
2. Sector rotation patterns
3. Key levels and what they mean
4. Catalysts for the week ahead
5. Risk factors to monitor

AUDIENCE: US active investors and swing traders
TONE: Professional, actionable, concise

Do NOT:
- Give specific price targets
- Make definitive predictions
- Reference technical indicators by name (RSI, MACD, etc.)
"""

DD_QUICK_SYSTEM = """You are a senior investment analyst conducting rapid due diligence on a stock that has already passed technical and thematic screening.

Your job is NOT to find reasons to reject - the stock has already passed multiple quality gates.
Your job is to quickly validate the bull case and identify any fatal flaws.

Be direct and actionable. If it looks good, say so. If there's a specific concern, name it."""

DD_FULL_SYSTEM = """You are the Lead Portfolio Manager at a high-conviction Global Macro Hedge Fund specializing in aggressive growth equities.

This stock has ALREADY passed:
1. Technical screening (Weekly BoS breakout, high beta, institutional accumulation)
2. Thematic analysis (assigned to a hot theme with good fit)
3. Gatekeeper quality check (catalysts confirmed, red flags assessed)

Your job is to validate whether this stock has REALISTIC potential for 50-100%+ returns in 3-12 months.
We need a re-rating event - either earnings surprise, multiple expansion, or both.

Be thorough but decisive. We're not looking for reasons to reject every stock.
We're looking for the VARIANT PERCEPTION that makes this a 50%+ winner or the FATAL FLAW that kills it."""

NEWSLETTER_SYSTEM = """You are a professional financial newsletter writer for Sterling Signals on Substack.

AUDIENCE: US active investors and swing traders seeking momentum opportunities.

STYLE:
- Professional but accessible
- Data-driven with specific numbers
- Confident analysis, not hedging language
- Focus on themes, catalysts, and systematic approach

STRUCTURE:
- Opening hook that references performance or key insight
- Market context section
- Theme analysis with rankings
- Stock-by-stock breakdown for PASS signals
- Portfolio update with P&L
- Week ahead preview

RULES:
- Never reveal specific system mechanics
- Use approved marketing vocabulary
- Always include performance vs SPY when outperforming
- Include [CHART: TICKER] placeholders for visual content
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, str] = {
    # ─────────────────────────────────────────────────────────────────────────
    # Gatekeeper Templates
    # ─────────────────────────────────────────────────────────────────────────
    "gatekeeper_analysis": """
Analyze ${ticker} for final quality gate.

TECHNICAL DATA:
- Price: $$${price}
- Theme: ${theme} (${theme_fit})
- Tier: ${tier}

THEMES CONTEXT:
${themes_context}

REQUIRED SEARCHES:
1. "${ticker} earnings date 2026" - Find next catalyst
2. "${ticker} insider transactions" - Check for red flags
3. "${ticker} analyst ratings" - Sentiment check

Based on your analysis, return a JSON decision (PASS/CAUTION/FAIL).
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Thematic Analyzer Templates
    # ─────────────────────────────────────────────────────────────────────────
    "thematic_discovery": """
## IDENTIFY TOP 5-7 INVESTABLE THEMES (6-12 Month Horizon)

REQUIRED SEARCHES:
1. "best performing sector ETFs 2026"
2. "investment themes working 2026"
3. "where is smart money flowing 2026"
4. "sectors with positive earnings revisions 2026"

For each theme identified, provide:
- Name and type (TREND/BOTTLENECK/CONTRARIAN)
- Composite score (0-10)
- Classification (PRIME/INVESTABLE/SELECTIVE/AVOID)
- Key catalysts
- Thesis summary

Return as JSON with structure:
{
    "themes": [
        {
            "rank": 1,
            "name": "Theme Name",
            "classification": "PRIME",
            "theme_type": "TREND",
            "composite_score": 8.5,
            "thesis_summary": "Brief explanation",
            "key_catalysts": ["Catalyst 1", "Catalyst 2"]
        }
    ]
}
""",

    "thematic_mapping": """
## MAP TICKERS TO THEMES

THEMES CONTEXT:
${themes_context}

TICKERS TO MAP:
${tickers}

For each ticker, determine:
1. Best theme fit
2. Pure play score (0-100%)
3. Theme verdict (STRONG FIT / GOOD FIT / MODERATE FIT / POOR FIT)

Return as JSON:
{
    "mappings": [
        {
            "ticker": "SYMBOL",
            "theme": "Theme Name",
            "pure_play_score": 85,
            "theme_verdict": "STRONG FIT",
            "theme_justification": "Brief explanation"
        }
    ]
}
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Due Diligence Templates
    # ─────────────────────────────────────────────────────────────────────────
    "dd_quick": """# QUICK DUE DILIGENCE: ${ticker}

## Already Passed (No Need to Re-verify)
- Technical: Weekly breakout confirmed, Beta ${beta}, Banker ${banker}
- Theme: ${theme} (${theme_verdict})
- Gatekeeper: PASS with conviction ${conviction}/5
- Catalyst: ${catalyst_summary}
- Red Flags: ${red_flag_level}

## Your 5-Minute Mission

Search for recent information on ${ticker} and answer:

1. **Last Earnings** (search: "${ticker} earnings results"): Beat or miss? Guidance?

2. **Next Catalyst** (search: "${ticker} upcoming catalyst 2026"): Next price mover?

3. **Bear Case** (search: "${ticker} short thesis risk"): #1 argument against?

4. **Counter-Argument**: Why is the bear case wrong?

5. **Math to 50%**: What scenario gets +50%?

## Output Format

**ELEVATOR PITCH:** [One sentence - why this stock, why now]

**KEY CATALYST:** [Specific event and date]

**BEAR CASE:** [The smart short-seller argument]

**COUNTER:** [Why the bear is wrong]

**MATH TO 50%:** [Brief scenario]

**FATAL FLAW:** [None found / Describe specific issue]

**VERDICT:** [STRONG BUY / SPEC BUY / NO GO]

**CONVICTION:** [X/10]

**POSITION SIZE:** [FULL / REDUCED / PASS]
""",

    "dd_full": """# DEAL MEMO: ${ticker}

## Screening Status (Already Passed)
| Gate | Status | Details |
|------|--------|---------|
| Technical | PASSED | Weekly BoS breakout, Beta ${beta}, Banker ${banker} (Tier: ${tier}) |
| Thematic | PASSED | ${theme} - ${theme_verdict} |
| Gatekeeper | PASSED | Conviction ${conviction}/5, Red Flags: ${red_flag_level} |

## Gatekeeper Summary
- **Catalyst:** ${catalyst_summary}
- **Bullish Factors:** ${bullish_factors}
- **Risk Factors:** ${risk_factors}

## Investment Parameters
- Entry: Monday market open
- Target Hold: 3-12 months
- Exit: Weekly BoS breakdown OR trailing stop protocol
- Minimum Target: 50%+ return

---

## PHASE 1: EXPLOSIVE GROWTH INVESTIGATION

Search and analyze:
1. Revenue growth trajectory - is it ACCELERATING?
2. Operating leverage - will 10% revenue drive 50% earnings?
3. Net Revenue Retention (NRR) - customers spending more?
4. Backlog/pipeline - hidden revenue not yet recognized?

## PHASE 2: HIDDEN CATALYST SEARCH

Search for events that could drive re-rating:
1. M&A potential (acquirer or target?)
2. New product launches
3. Regulatory/approval events
4. Management changes signaling strategy shift

## PHASE 3: BEAR CASE DEMOLITION

What's the SHORT thesis? Why is it wrong?

## PHASE 4: VALUATION REALITY CHECK

Is current multiple justified? What multiple at 50%+ target?

## PHASE 5: FINAL SYNTHESIS

**VERDICT:** [STRONG BUY / SPEC BUY / NO GO]
**CONVICTION:** [X/10]
**POSITION SIZE:** [FULL / REDUCED / PASS]
**KEY CATALYST:** [Most important driver]
**FATAL FLAW:** [None / Describe issue]
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Tweet Templates
    # ─────────────────────────────────────────────────────────────────────────
    "tweet_buy_signal": """Generate ${count} tweets about a new BUY signal.

SIGNAL DATA:
- Ticker: ${ticker}
- Theme: ${theme}
- Conviction Rating: ${conviction}/5
- Key Catalyst: ${catalyst}
- Theme Score: ${theme_score}

RULES:
- Maximum 280 characters per tweet
- Use $ before ticker symbol
- No specific stop levels or entry prices
- Focus on the opportunity, not the mechanics
- Include one of: thread teaser, newsletter link, or engagement hook

Return as JSON array:
[{"number": 1, "text": "Tweet text here"}, ...]
""",

    "tweet_theme_hot": """Generate ${count} tweets about a hot investment theme.

THEME DATA:
- Name: ${theme_name}
- Classification: ${classification}
- Score: ${score}/10
- Key Catalysts: ${catalysts}
- Thesis: ${thesis}

RULES:
- Maximum 280 characters per tweet
- Focus on institutional flows and momentum
- Mention 1-2 representative tickers if appropriate
- Hook readers to learn more in newsletter

Return as JSON array.
""",

    "tweet_position_update": """Generate ${count} position update tweets.

POSITION DATA:
- Ticker: ${ticker}
- Entry: $$${entry_price} on ${entry_date}
- Current: $$${current_price}
- P&L: ${pnl_pct}%
- Days Held: ${days_held}
- Theme: ${theme}

RULES:
- Be factual about performance
- Frame losses positively ("system working")
- No specific stop levels
- Mention theme strength if relevant

Return as JSON array.
""",

    "tweet_power_hour": """Generate ${count} Power Hour reaction tweets (15:30-16:00 ET).

CONTEXT:
- Hot themes: ${hot_themes}
- Open positions: ${positions}
- Market sentiment: ${sentiment}

TEMPLATE STYLE:
"Power Hour Check:
{Theme} seeing {volume pattern} into the close.
Our pick $${ticker} currently {direction} {percent}%.
{Brief observation about relative strength}
Watching for structural confirmation on the weekly close."

Return as JSON array.
""",

    "tweet_beat_spy": """Generate ${count} Beat SPY / Alpha comparison tweets.

PERFORMANCE DATA:
- Portfolio YTD: ${portfolio_return}%
- SPY YTD: ${spy_return}%
- Alpha: ${alpha}%
- Best performer: ${best_performer}

HOOKS TO USE:
- "Stop indexing. Start selecting."
- "SPY gives you average returns. We hunt outliers."
- "The difference between 10% and 40%? Stock selection."

Return as JSON array.
""",

    "tweet_roth_ira": """Generate ${count} tweets for Roth IRA / tax-advantaged investors.

CONTEXT:
- Recent winners: ${recent_winners}
- YTD performance: ${ytd_return}%

TEMPLATES TO RIFF ON:
"The Roth IRA hack nobody talks about:
Instead of holding SPY forever, rotate into momentum winners.
Tax-free compounding on 30-50% swing trades > 10% annual index returns.
The system identifies these setups weekly."

"Your Roth doesn't have to be boring index funds.
Systematic momentum + tax-free compounding = retirement account on steroids."

RULES:
- Focus on tax-free compounding angle
- Mention systematic approach
- Never financial advice

Return as JSON array.
""",

    "tweet_post_mortem": """Generate ${count} Post-Mortem tweets for stopped-out positions.

STOPPED TRADE DATA:
- Ticker: ${ticker}
- Entry: $$${entry_price}
- Exit: $$${exit_price}
- Loss: ${loss_pct}%
- Days Held: ${days_held}
- Theme: ${theme}
- Lesson: ${lesson}

TEMPLATE:
"❌ $${ticker} — Stopped Out

Entry: $$${entry_price}
Exit: $$${exit_price}
Loss: ${loss_pct}%

The system protects capital so we live to fight another day.
No ego, just execution.

{Optional 1-sentence lesson}"

RULES:
- Never delete losing posts
- Frame as system working
- NEVER mention specific stop level percentage

Return as JSON array.
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Market Analysis Templates
    # ─────────────────────────────────────────────────────────────────────────
    "market_context": """Generate the market context section for this week's newsletter.

CURRENT DATA:
- Date: ${date}
- Week Ending: ${week_ending}

Use web search to gather:
1. S&P 500 weekly performance
2. NASDAQ weekly performance
3. Key events that moved markets
4. Sector rotation observations
5. What to watch next week

Write 3-4 paragraphs covering:
1. What drove this week's market action (with specific numbers)
2. Sector rotation observations
3. Key events that moved markets
4. What to watch for next week

TONE: Professional, actionable, no specific predictions.
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Newsletter Templates
    # ─────────────────────────────────────────────────────────────────────────
    "newsletter_compile": """Compile the weekly Sterling Signals newsletter from these inputs:

MARKET CONTEXT:
${market_context}

SCANNER BRIEFING:
${briefing}

DD SUMMARIES:
${dd_summaries}

INSTRUCTIONS:
1. Create compelling intro paragraph
2. Format Hot Themes section
3. Format PASS signals with DD summaries
4. Format CAUTION (watchlist) signals
5. Include portfolio performance section
6. Add [CHART: TICKER] placeholders for charts
7. End with week ahead preview

Output in Markdown format ready for Substack.
""",

    # ─────────────────────────────────────────────────────────────────────────
    # Thread Templates
    # ─────────────────────────────────────────────────────────────────────────
    "thread_educational": """Generate a 5-tweet educational thread.

TOPIC: ${topic}
CONTEXT: ${context}

THREAD STRUCTURE:
1/ Hook - Provocative question or bold claim
2/ Problem - Why most traders fail at this
3/ Insight - The systematic solution
4/ Proof - Example with data (no specific numbers)
5/ CTA - Link to newsletter for more

RULES:
- Each tweet max 280 characters
- Number with 1/, 2/, etc.
- Do NOT reveal specific system mechanics
- Focus on concepts and frameworks

Return as JSON array.
""",
}


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPTS: Dict[str, str] = {
    'gatekeeper': GATEKEEPER_SYSTEM,
    'tweet': TWEET_SYSTEM,
    'thematic': THEMATIC_ANALYZER_SYSTEM,
    'market': MARKET_ANALYZER_SYSTEM,
    'dd_quick': DD_QUICK_SYSTEM,
    'dd_full': DD_FULL_SYSTEM,
    'newsletter': NEWSLETTER_SYSTEM,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def render_prompt(template_name: str, **kwargs) -> str:
    """
    Render a prompt template with provided variables.

    Args:
        template_name: Name of the template in TEMPLATES
        **kwargs: Variables to substitute into the template

    Returns:
        Rendered prompt string

    Raises:
        ValueError: If template name not found

    Example:
        prompt = render_prompt('gatekeeper_analysis',
            ticker='AAPL',
            price=150.00,
            theme='AI Infrastructure',
            theme_fit='STRONG'
        )
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(TEMPLATES.keys())}")

    template = Template(TEMPLATES[template_name])

    # Convert non-string values to strings
    str_kwargs = {k: str(v) if v is not None else '' for k, v in kwargs.items()}

    try:
        return template.safe_substitute(str_kwargs)
    except Exception as e:
        raise ValueError(f"Error rendering template {template_name}: {e}")


def get_system_prompt(component: str) -> str:
    """
    Get the system prompt for a component.

    Args:
        component: Component name (gatekeeper, tweet, thematic, market, dd_quick, dd_full, newsletter)

    Returns:
        System prompt string

    Raises:
        ValueError: If component not found

    Example:
        system = get_system_prompt('gatekeeper')
    """
    if component not in SYSTEM_PROMPTS:
        raise ValueError(f"Unknown component: {component}. Available: {list(SYSTEM_PROMPTS.keys())}")

    return SYSTEM_PROMPTS[component]


def list_templates() -> List[str]:
    """List all available template names."""
    return list(TEMPLATES.keys())


def list_system_prompts() -> List[str]:
    """List all available system prompt names."""
    return list(SYSTEM_PROMPTS.keys())


def get_template(template_name: str) -> str:
    """
    Get raw template string without rendering.

    Args:
        template_name: Name of the template

    Returns:
        Raw template string

    Raises:
        ValueError: If template not found
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    return TEMPLATES[template_name]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def format_list(items: List[Any], separator: str = ", ") -> str:
    """
    Format a list for prompt inclusion.

    Args:
        items: List to format
        separator: Separator between items

    Returns:
        Formatted string

    Example:
        format_list(['A', 'B', 'C'])  # Returns: "A, B, C"
    """
    if not items:
        return "None"
    return separator.join(str(item) for item in items)


def format_dict(d: Dict[str, Any], format_type: str = "bullet") -> str:
    """
    Format a dictionary for prompt inclusion.

    Args:
        d: Dictionary to format
        format_type: 'bullet', 'table', or 'inline'

    Returns:
        Formatted string

    Example:
        format_dict({'key': 'value'}, 'bullet')  # Returns: "- key: value"
    """
    if not d:
        return "None"

    if format_type == "bullet":
        return "\n".join(f"- {k}: {v}" for k, v in d.items())
    elif format_type == "table":
        return "\n".join(f"| {k} | {v} |" for k, v in d.items())
    else:
        return ", ".join(f"{k}={v}" for k, v in d.items())


def format_themes_context(themes: List[Dict[str, Any]]) -> str:
    """
    Format themes list for inclusion in prompts.

    Args:
        themes: List of theme dictionaries

    Returns:
        Formatted string for prompt context
    """
    if not themes:
        return "No themes available"

    lines = []
    for theme in themes:
        name = theme.get('name', 'Unknown')
        classification = theme.get('classification', '')
        score = theme.get('composite_score', 0)
        lines.append(f"- {name} ({classification}): Score {score}/10")

    return "\n".join(lines)


def format_tickers_list(tickers: List[str], max_per_line: int = 10) -> str:
    """
    Format tickers list for inclusion in prompts.

    Args:
        tickers: List of ticker symbols
        max_per_line: Maximum tickers per line

    Returns:
        Formatted string
    """
    if not tickers:
        return "No tickers"

    lines = []
    for i in range(0, len(tickers), max_per_line):
        chunk = tickers[i:i + max_per_line]
        lines.append(", ".join(chunk))

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Test prompt templates."""
    import argparse

    parser = argparse.ArgumentParser(description="Prompt Templates")
    parser.add_argument("--list", action="store_true", help="List available templates")
    parser.add_argument("--show", help="Show a specific template")
    parser.add_argument("--system", help="Show system prompt for component")
    parser.add_argument("--render", help="Render template with test data")

    args = parser.parse_args()

    if args.list:
        print("Available Templates:")
        for name in list_templates():
            print(f"  - {name}")
        print("\nSystem Prompts:")
        for name in list_system_prompts():
            print(f"  - {name}")

    elif args.show:
        try:
            print(f"\n=== {args.show} ===\n")
            print(get_template(args.show))
        except ValueError as e:
            print(f"  ✗ Error: {e}")

    elif args.system:
        try:
            print(f"\n=== {args.system} System Prompt ===\n")
            print(get_system_prompt(args.system))
        except ValueError as e:
            print(f"  ✗ Error: {e}")

    elif args.render:
        # Test rendering with sample data
        test_data = {
            'ticker': 'AAPL',
            'price': '150.00',
            'theme': 'AI Infrastructure',
            'theme_fit': 'STRONG',
            'tier': 'TIER1',
            'themes_context': 'Sample themes context...',
            'count': '3',
            'conviction': '4',
            'catalyst': 'Earnings Feb 15',
            'theme_score': '8.5',
            'beta': '1.8',
            'banker': '65',
            'catalyst_summary': 'Earnings Feb 15',
            'red_flag_level': 'CLEAN',
            'theme_verdict': 'STRONG FIT',
            'bullish_factors': 'Strong momentum, Theme leader',
            'risk_factors': 'High valuation'
        }
        try:
            print(f"\n=== Rendered: {args.render} ===\n")
            print(render_prompt(args.render, **test_data))
        except ValueError as e:
            print(f"  ✗ Error: {e}")

    else:
        print("Prompt Templates - Use --list, --show, --system, or --render")
        print("\n  ✓ Module loaded successfully")


if __name__ == "__main__":
    main()
