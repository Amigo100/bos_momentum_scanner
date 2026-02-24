#!/usr/bin/env python3
"""
INVESTMENT GATE v1.0 — Combined Quality Gate + Due Diligence
=============================================================

REPLACES: gatekeeper.py + dd_automator.py (combined into one API call)

PURPOSE:
The stock has already passed:
  ✓ Technical Signal (HMA Buy + UC Rising + >25% below 52w high)
  ✓ Thematic Analysis (PRIME/INVESTABLE theme, STRONG/GOOD fit)

This gate answers ONE question: "Should I buy this stock on Monday?"

It does this in a single API call with structured web searches, covering:
  Phase 1: DISQUALIFIER SCREEN (are there landmines?)
  Phase 2: CATALYST VALIDATION (what drives the move?)
  Phase 3: RETURN VALIDATION (can this realistically make 50%+?)
  Phase 4: VERDICT (buy or don't buy)

KEY DESIGN PRINCIPLE — VALUATION REGIME AWARENESS:
Not all stocks are priced the same way. A quantum computing company with zero
revenue can be a STRONG BUY if milestones are hitting and the narrative is
expanding. An AI infrastructure company with declining earnings revisions can
be a NO GO even if revenue is growing. The assessment adapts to how the market
is actually pricing the stock.

DECISION FRAMEWORK:
  STRONG BUY  = High conviction. Clear catalyst + clean setup + math works
  SPEC BUY    = Thesis intact but execution-dependent. Smaller position.
  NO GO       = Fatal flaw OR no catalyst OR math doesn't work → Move on

Usage:
    from investment_gate import run_investment_gate, InvestmentGateResult
    results = run_investment_gate_batch(client, stocks, use_web_search=True)

Cost: ~$0.15-0.25 per stock (single Sonnet call with web search)
      Previously: ~$0.30-0.55 per stock (gatekeeper + DD = 2 calls)
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import anthropic
except ImportError:
    print("Install with: pip install anthropic")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8000
INTER_STOCK_DELAY = 8.0
RATE_LIMIT_COOLDOWN = 60.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class GateVerdict(Enum):
    STRONG_BUY = "STRONG BUY"
    SPEC_BUY = "SPEC BUY"
    NO_GO = "NO GO"
    ERROR = "ERROR"


@dataclass
class InvestmentGateResult:
    """Single result from the Investment Gate assessment."""
    ticker: str

    # ── Verdict ──
    verdict: GateVerdict = GateVerdict.ERROR
    conviction: int = 0           # 1-10 scale
    position_size: str = ""       # FULL / REDUCED / PASS

    # ── Context (passed through from pipeline) ──
    theme: str = ""
    theme_fit: str = ""           # STRONG FIT / GOOD FIT
    theme_classification: str = ""  # PRIME / INVESTABLE
    valuation_regime: str = ""    # OPTIONALITY / FUNDAMENTAL / TRANSITION (from theme analyzer)

    # ── Phase 1: Disqualifier Screen ──
    red_flag_level: str = ""      # CLEAN / MINOR / SEVERE
    red_flags: List[str] = field(default_factory=list)
    disqualified: bool = False
    disqualifier_reason: str = ""

    # ── Phase 2: Catalyst Validation ──
    catalyst_present: bool = False
    catalyst_summary: str = ""    # "Earnings Mar 5, Investor Day Mar 20"
    days_to_catalyst: int = -1
    analyst_trend: str = ""       # BULLISH / NEUTRAL / BEARISH
    short_interest_pct: float = 0.0
    revision_trajectory: str = "" # ACCELERATING / STABLE / DECELERATING / NEGATIVE / N/A

    # ── Phase 3: Return Validation ──
    math_to_50: str = ""          # Path to 50%+ return
    bear_case: str = ""           # Steelmanned bear argument
    bear_rebuttal: str = ""       # Why the bear is wrong (or acceptable)
    bull_case: str = ""           # Elevator pitch
    downside_floor: str = ""      # Where value buyers step in

    # ── Phase 4: Synthesis ──
    key_bullish: List[str] = field(default_factory=list)   # Top 3 reasons to buy
    key_risks: List[str] = field(default_factory=list)     # Top 3 risks
    kill_switch: str = ""         # What would force early exit
    reasoning: str = ""           # 2-3 sentence synthesis
    action: str = ""              # Specific recommendation

    # ── Meta ──
    timestamp: str = ""
    error: bool = False
    error_msg: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def passed(self) -> bool:
        """Did this stock pass the gate?"""
        return self.verdict in (GateVerdict.STRONG_BUY, GateVerdict.SPEC_BUY)

    def get_cost(self) -> float:
        """Estimate cost (Sonnet pricing)."""
        return (self.input_tokens / 1_000_000 * 3.0 +
                self.output_tokens / 1_000_000 * 15.0)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['verdict'] = self.verdict.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a Senior Investment Analyst at a High-Conviction Growth Fund, conducting the FINAL assessment before committing capital.

CONTEXT:
This stock has already passed:
- Technical buy signal: Weekly V6 momentum pivot (HMA pivot low V-bottom + at least one confirmation gate: UC rising indicating institutional accumulation OR MACD cross-up for timing + Price under $25). Quality tier assigned at signal: T1 (both gates, 20% sizing), T2 (MACD only, 10%), T3 (UC only, 5%).
- Thematic analysis: Confirmed to be in a healthy investment theme with good company fit

YOUR MISSION:
Answer ONE question: "Should we buy this stock on Monday?"

You're looking for ASYMMETRIC setups — stocks with realistic potential for 50-100%+ returns over 3-12 months. This is NOT about finding "safe" stocks. It's about finding multi-bagger candidates with manageable downside.

═══════════════════════════════════════════════════════════════════
CRITICAL: VALUATION REGIME AWARENESS
═══════════════════════════════════════════════════════════════════

Not all stocks are priced the same way. You MUST adapt your assessment to the stock's valuation regime. The thematic analyzer has already classified the theme's regime — use it.

REGIME A — OPTIONALITY (pre-revenue or milestone-driven)
Examples: Quantum computing (IONQ, RGTI), early space (LUNR, ASTS), pre-revenue biotech
- Do NOT look for P/E ratios or earnings beats — they don't exist or are irrelevant
- DO assess: Are technical milestones being hit? Is funding growing? Is narrative expanding?
- "Math to 50%" = Milestone achievement → narrative expansion → institutional re-rating
- Bear case = Milestone delays, funding drying up, competitor leapfrog, hype cycle peak
- These stocks can go +300-700% on narrative momentum alone (RGTI did +705%, IONQ +293%)
- They can also go to zero. Position sizing should reflect this.

REGIME B — FUNDAMENTAL (revenue and earnings-driven)
Examples: AI infrastructure (SMCI, VRT), cybersecurity (CRWD), fintech (COIN, AFRM)
- Standard assessment: Revenue growth trajectory, operating leverage, earnings revisions
- "Math to 50%" = Earnings growth × multiple expansion
- Bear case = Capex/revenue divergence, decelerating revisions, competition, valuation stretched
- Red flag: If theme's capex is growing 3x faster than revenue, be very cautious

REGIME C — TRANSITION (shifting from milestone-based to revenue-based pricing)
Examples: Drones moving to commercial delivery, space companies booking first revenue
- HIGHEST RISK regime. Market is shifting what it values.
- Key question: Is revenue materializing fast enough to justify current valuation?
- Bear case = Valuation reset as market demands fundamentals
- Bull case = Revenue surprise that validates the optionality pricing

═══════════════════════════════════════════════════════════════════
PHASE 1: DISQUALIFIER SCREEN (Search 1-2)
═══════════════════════════════════════════════════════════════════

IMMEDIATE DISQUALIFIERS (→ NO GO, stop analysis):
- Auditor resignation or delayed 10-K filing
- CFO/CEO resigned in last 60 days (without clear succession)
- Shelf offering (S-3) filed in last 30 days with no stated use
- Active SEC or DOJ investigation
- For OPTIONALITY or TRANSITION regime: Earnings in < 5 trading days (binary risk too high on stocks not yet priced on earnings)
- For FUNDAMENTAL regime: earnings revisions turned negative across the board

EARNINGS TIMING — REGIME-DEPENDENT RULE:
- FUNDAMENTAL regime + earnings in < 5 days + revisions ACCELERATING:
  This is a CATALYST, not a risk. Note as CAUTION FLAG but CONTINUE analysis.
  The technical signal likely fired BECAUSE smart money is positioning for the beat.
- FUNDAMENTAL regime + earnings in < 5 days + revisions STABLE/DECELERATING/NEGATIVE:
  DISQUALIFIER. Binary risk without positive setup.
- OPTIONALITY/TRANSITION regime + earnings in < 5 days:
  DISQUALIFIER. Pre-revenue earnings are genuinely unpredictable.

CAUTION FLAGS (note but continue):
- Earnings in 5-15 trading days → flag timing risk
- Short interest > 25% → flag volatility risk
- Single analyst downgrade → one opinion, not a trend
- Insider selling under 10b5-1 plan → scheduled, not panic
- Average daily trading volume < $1M or float < 5M shares → LIQUIDITY CONCERN, factor into position sizing (recommend REDUCED)

═══════════════════════════════════════════════════════════════════
PHASE 2: CATALYST VALIDATION (Search 3-4)
═══════════════════════════════════════════════════════════════════

For FUNDAMENTAL regime:
- Upcoming earnings date and estimate trend (rising/falling?)
- Revenue growth: is it ACCELERATING?
- Earnings revision trajectory: ↑↑ (accelerating) vs ↑ (stable) vs ↑ slowing (decelerating)
- Analyst upgrades/downgrades in last 30 days
- Product launches, contracts, partnerships in next 90 days

For OPTIONALITY regime:
- Technical milestone announcements (demos, breakthroughs, certifications)
- Government/institutional funding awards or pipeline
- Partnership or contract announcements
- Conference presentations, investor days
- Narrative expansion: new use cases being discussed, new institutional coverage

For TRANSITION regime:
- First revenue numbers vs market expectations
- Customer announcements, order book
- Regulatory approvals (FAA, FDA, etc.)
- Market's tolerance for current valuation — any repricing underway?

═══════════════════════════════════════════════════════════════════
PHASE 3: RETURN VALIDATION (Search 5)
═══════════════════════════════════════════════════════════════════

THE MATH TO 50%+ (adapt to regime):

For FUNDAMENTAL:
  "Revenue grows X% → operating leverage delivers Y% EPS growth → multiple re-rates from Ax to Bx → price target $Z (+N%)"
  Include: current multiple vs 3-year average, vs peers

For OPTIONALITY:
  "If [milestone X] is achieved in [timeframe], institutional coverage expands from N to M analysts → re-rating as theme goes mainstream"
  Include: comparable milestones in similar themes (e.g., "early AI stocks re-rated 3-5x once GPT-3 launched")

For TRANSITION:
  "Revenue of $X validates the story → multiple stabilizes at Yx vs current Zx → floor at $P, upside to $Q"

THE BEAR CASE — STEELMAN THE OPPOSITION:
- What's the #1 argument a smart short-seller would make?
- Can you dismantle it with data?
- If not, is it a FATAL FLAW or an ACCEPTABLE RISK?

DOWNSIDE FLOOR:
- Where would value investors or strategic acquirers step in?
- What's the maximum realistic loss in 3 months?

═══════════════════════════════════════════════════════════════════
OUTPUT FORMAT — Return ONLY valid JSON
═══════════════════════════════════════════════════════════════════

{
    "ticker": "SYMBOL",
    "verdict": "STRONG BUY|SPEC BUY|NO GO",
    "conviction": 1-10,
    "position_size": "FULL|REDUCED|PASS",

    "valuation_regime_applied": "OPTIONALITY|FUNDAMENTAL|TRANSITION",

    "disqualified": false,
    "disqualifier_reason": "",
    "red_flag_level": "CLEAN|MINOR|SEVERE",
    "red_flags": ["Specific issue 1"],

    "catalyst_present": true,
    "catalyst_summary": "Earnings Mar 5 (est beat likely based on accelerating revisions), Investor Day Mar 20",
    "days_to_catalyst": 30,
    "analyst_trend": "BULLISH|NEUTRAL|BEARISH",
    "short_interest_pct": 8.5,
    "revision_trajectory": "ACCELERATING|STABLE|DECELERATING|NEGATIVE|NOT_APPLICABLE",

    "math_to_50": "Revenue grows 35% → operating leverage drives 60% EPS growth → multiple re-rates from 25x to 35x → $180 target (+65%)",
    "bear_case": "The smart short-seller argument",
    "bear_rebuttal": "Why the bear is wrong or risk is acceptable",
    "bull_case": "2-sentence elevator pitch — why this stock, why now",
    "downside_floor": "Value floor at ~$X (-Y% from current) based on Z",

    "key_bullish": ["Reason 1", "Reason 2", "Reason 3"],
    "key_risks": ["Risk 1", "Risk 2", "Risk 3"],
    "kill_switch": "What would force early exit — e.g., 'Revenue growth decelerates below 20%'",

    "reasoning": "2-3 sentence synthesis of why STRONG BUY / SPEC BUY / NO GO",
    "action": "Specific recommendation — e.g., 'Buy Monday at open, full position' or 'Wait until after Mar 5 earnings'"
}

═══════════════════════════════════════════════════════════════════
VERDICT RULES
═══════════════════════════════════════════════════════════════════

STRONG BUY (conviction 7-10):
- Catalyst within 90 days + no disqualifiers + math to 50% is clear
- For OPTIONALITY: milestones hitting + narrative expanding + early institutional interest
- For FUNDAMENTAL: revisions accelerating + reasonable valuation + upcoming beat likely
- Position size: FULL

SPEC BUY (conviction 4-6):
- Thesis intact but one or more concerns:
  - Timing uncertainty (earnings soon, regulatory pending)
  - Math works but requires multiple things to go right
  - For OPTIONALITY: milestone timeline uncertain but direction correct
- Position size: REDUCED (50%)

NO GO (conviction 1-3):
- Any disqualifier present
- No visible catalyst within 90 days (dead money risk)
- Bear case is strong and you cannot dismantle it
- For FUNDAMENTAL: revisions negative + valuation stretched
- For OPTIONALITY: milestones missed + narrative contracting
- Position size: PASS

IMPORTANT: Your job is NOT to reject every stock. The stock passed multiple quality gates.
If it looks good, say so confidently. Only reject for SPECIFIC, evidenced reasons."""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().rstrip('%').replace(',', '')
        if cleaned.lower() in ('n/a', 'na', 'none', 'unknown', ''):
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def create_client() -> anthropic.Anthropic:
    """Create Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


# ═══════════════════════════════════════════════════════════════════════════════
# CORE: SINGLE STOCK ASSESSMENT
# ═══════════════════════════════════════════════════════════════════════════════

def run_investment_gate(
    client: anthropic.Anthropic,
    ticker: str,
    price: float = 0.0,
    beta: float = 0.0,
    banker: float = 0.0,
    tier: str = "",
    theme: str = "",
    theme_fit: str = "",
    theme_classification: str = "",
    valuation_regime: str = "",
    conviction_prior: int = 0,
    catalyst_hint: str = "",
    themes_context: str = "",
    use_web_search: bool = True,
    max_retries: int = 3
) -> InvestmentGateResult:
    """
    Run the complete Investment Gate assessment on a single stock.

    Args:
        client: Anthropic client
        ticker: Stock symbol
        price: Current price
        beta, banker, tier: Technical data from scanner
        theme, theme_fit: From thematic analyzer
        theme_classification: PRIME / INVESTABLE from thematic analyzer
        valuation_regime: OPTIONALITY / FUNDAMENTAL / TRANSITION from theme analyzer
        conviction_prior: Theme fit conviction (passed through)
        catalyst_hint: Any catalyst info already known from theme analysis
        themes_context: Full themes context string
        use_web_search: Enable web search (strongly recommended for production)
        max_retries: API retry attempts

    Returns:
        InvestmentGateResult
    """
    from datetime import datetime
    current_year = datetime.now().year

    # Build the user prompt with all context
    regime_context = ""
    if valuation_regime:
        regime_context = f"""
VALUATION REGIME (from thematic analyzer): {valuation_regime}
Adapt your assessment accordingly — see system prompt for regime-specific guidance."""
    else:
        regime_context = """
VALUATION REGIME: Not specified by thematic analyzer. Determine it yourself:
- If the company has <$50M annual revenue or is pre-commercial → OPTIONALITY
- If the company has established revenue and is priced on P/E or P/S → FUNDAMENTAL
- If the company is transitioning from pre-revenue to revenue-generating → TRANSITION"""

    # Search instructions
    if use_web_search:
        search_instructions = f"""REQUIRED SEARCHES (do these efficiently):

1. "{ticker} SEC filing insider trading news {current_year}" → Red flags, governance, insider activity
2. "{ticker} earnings date analyst consensus short interest" → Catalyst timing, street sentiment
3. "{ticker} revenue growth catalyst upcoming {current_year}" → Growth trajectory, upcoming catalysts
4. "{ticker} bear case risk valuation" → Bear argument, valuation context
5. (Only if needed) "{ticker} technical milestones funding" → For OPTIONALITY regime stocks

After searches, synthesize into the JSON response. Be specific with dates and numbers."""
    else:
        search_instructions = """WEB SEARCH DISABLED (testing mode).
Use your knowledge to assess. Flag any areas where current data is critical."""

    user_prompt = f"""Conduct Investment Gate assessment for: {ticker}

STOCK CONTEXT:
- Ticker: {ticker}
- Current Price: ${price:.2f}
- Beta: {beta:.2f}
- Banker (UC): {banker:.0f}
- Tier: {tier}
- Theme: {theme}
- Theme Fit: {theme_fit}
- Theme Classification: {theme_classification}
{regime_context}

{f'PRIOR CATALYST HINT: {catalyst_hint}' if catalyst_hint else ''}

{themes_context}

{search_instructions}

Remember:
- Adapt your analysis to the VALUATION REGIME
- We want 50-100%+ return potential over 3-12 months
- A clean stock with no catalyst is NO GO (dead money)
- A stock with strong catalyst but minor risk is still a buy if the risk is manageable
- Be decisive. If it looks good, say so. If there's a specific problem, name it.

Return ONLY the JSON object, no other text."""

    # API call with retries
    last_error = None
    for attempt in range(max_retries):
        try:
            api_params = {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }

            if use_web_search:
                api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

            response = client.messages.create(**api_params)

            # Track tokens
            input_tokens = getattr(response.usage, 'input_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', 0)

            # Extract text
            text = "".join([b.text for b in response.content if hasattr(b, 'text')])

            # Strip citation tags from web search responses
            text = re.sub(r'</?antml:cite[^>]*>', '', text)

            # Parse JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group())
                return _parse_result(
                    data, ticker, theme, theme_fit, theme_classification,
                    valuation_regime, input_tokens, output_tokens
                )

            raise ValueError("No valid JSON in response")

        except anthropic.RateLimitError:
            last_error = "Rate limited"
            wait = RATE_LIMIT_COOLDOWN * (attempt + 1)
            print(f"    ⚠️  Rate limit, waiting {wait:.0f}s...")
            time.sleep(wait)

        except anthropic.BadRequestError as e:
            if "credit" in str(e).lower() or "billing" in str(e).lower():
                raise RuntimeError("BILLING_ERROR: Add credits at console.anthropic.com")
            last_error = str(e)
            break

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                break

    # Return error result
    return InvestmentGateResult(
        ticker=ticker,
        verdict=GateVerdict.ERROR,
        theme=theme,
        theme_fit=theme_fit,
        error=True,
        error_msg=f"Failed after {max_retries} attempts: {last_error}",
        reasoning=f"Analysis failed: {last_error}",
        action="Manual review required"
    )


def _parse_result(
    data: dict,
    ticker: str,
    theme: str,
    theme_fit: str,
    theme_classification: str,
    valuation_regime: str,
    input_tokens: int,
    output_tokens: int
) -> InvestmentGateResult:
    """Parse JSON response into InvestmentGateResult."""

    verdict_map = {
        "STRONG BUY": GateVerdict.STRONG_BUY,
        "SPEC BUY": GateVerdict.SPEC_BUY,
        "SPECULATIVE BUY": GateVerdict.SPEC_BUY,
        "NO GO": GateVerdict.NO_GO,
        "NOGO": GateVerdict.NO_GO,
    }

    return InvestmentGateResult(
        ticker=ticker,
        verdict=verdict_map.get(data.get("verdict", "").upper(), GateVerdict.NO_GO),
        conviction=data.get("conviction", 0),
        position_size=data.get("position_size", "PASS"),

        theme=data.get("theme", theme),
        theme_fit=theme_fit,
        theme_classification=theme_classification,
        valuation_regime=data.get("valuation_regime_applied", valuation_regime),

        red_flag_level=data.get("red_flag_level", "UNKNOWN"),
        red_flags=data.get("red_flags", []),
        disqualified=data.get("disqualified", False),
        disqualifier_reason=data.get("disqualifier_reason", ""),

        catalyst_present=data.get("catalyst_present", False),
        catalyst_summary=data.get("catalyst_summary", ""),
        days_to_catalyst=data.get("days_to_catalyst", -1),
        analyst_trend=data.get("analyst_trend", "UNKNOWN"),
        short_interest_pct=_safe_float(data.get("short_interest_pct"), 0.0),
        revision_trajectory=data.get("revision_trajectory", ""),

        math_to_50=data.get("math_to_50", ""),
        bear_case=data.get("bear_case", ""),
        bear_rebuttal=data.get("bear_rebuttal", ""),
        bull_case=data.get("bull_case", ""),
        downside_floor=data.get("downside_floor", ""),

        key_bullish=data.get("key_bullish", []),
        key_risks=data.get("key_risks", []),
        kill_switch=data.get("kill_switch", ""),
        reasoning=data.get("reasoning", ""),
        action=data.get("action", ""),

        input_tokens=input_tokens,
        output_tokens=output_tokens
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def run_investment_gate_batch(
    client: anthropic.Anthropic,
    stocks: List[Any],
    themes_context: str = "",
    use_web_search: bool = True,
    delay_between: float = INTER_STOCK_DELAY,
    max_stocks: Optional[int] = None,
    save_reports: bool = False
) -> List[InvestmentGateResult]:
    """
    Run Investment Gate on multiple stocks.

    Args:
        client: Anthropic client
        stocks: List of Stock objects or dicts
        themes_context: Full themes context from thematic analyzer
        use_web_search: Enable web search
        delay_between: Seconds between API calls
        max_stocks: Limit number of stocks
        save_reports: Save individual reports to files

    Returns:
        List of InvestmentGateResult
    """
    if not stocks:
        return []

    if max_stocks:
        stocks = stocks[:max_stocks]

    results = []
    total_cost = 0.0

    print(f"\n  Running INVESTMENT GATE on {len(stocks)} stock(s)")
    print(f"  {'═' * 60}")
    print(f"  🎯 Target: 50-100%+ return potential over 3-12 months")
    print(f"  🔍 Checking: Red flags → Catalysts → Return math → Verdict")
    if use_web_search:
        print(f"  🌐 Web search ENABLED — ~5 searches per stock")
        print(f"  💰 Estimated cost: ~${len(stocks) * 0.20:.2f}")
    else:
        print(f"  💰 Web search DISABLED — testing mode")
    print(f"  {'─' * 60}")

    for i, stock in enumerate(stocks):
        # Extract attributes (handle Stock objects and dicts)
        if hasattr(stock, 'symbol'):
            ticker = stock.symbol
            price = getattr(stock, 'price', 0.0)
            beta = getattr(stock, 'beta', 0.0)
            banker = getattr(stock, 'banker', 0.0)
            tier = getattr(stock, 'tier', '')
            theme = getattr(stock, 'theme', '')
            theme_fit = getattr(stock, 'theme_verdict', '')
            theme_classification = getattr(stock, 'theme_classification', '')
            valuation_regime = getattr(stock, 'valuation_regime', '')
        else:
            ticker = stock.get('symbol', stock.get('ticker', 'UNKNOWN'))
            price = stock.get('price', 0.0)
            beta = stock.get('beta', 0.0)
            banker = stock.get('banker', 0.0)
            tier = stock.get('tier', '')
            theme = stock.get('theme', '')
            theme_fit = stock.get('theme_fit', stock.get('theme_verdict', ''))
            theme_classification = stock.get('theme_classification', '')
            valuation_regime = stock.get('valuation_regime', '')

        print(f"\n  [{i+1}/{len(stocks)}] {ticker} — {theme or 'Unknown Theme'}")
        print(f"  {'─' * 50}")

        result = run_investment_gate(
            client=client,
            ticker=ticker,
            price=price,
            beta=beta,
            banker=banker,
            tier=tier,
            theme=theme,
            theme_fit=theme_fit,
            theme_classification=theme_classification,
            valuation_regime=valuation_regime,
            themes_context=themes_context,
            use_web_search=use_web_search
        )

        results.append(result)
        cost = result.get_cost()
        total_cost += cost

        # Print result immediately
        try:
            _print_result(result)
        except Exception as e:
            print(f"  ⚠ Display error: {e}")
            print(f"  │ Verdict: {result.verdict.value} │ Conviction: {result.conviction}")

        if save_reports and not result.error:
            _save_report(result)

        # Rate limit delay
        if i < len(stocks) - 1:
            time.sleep(delay_between)

    # Summary
    _print_summary(results, total_cost)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# APPLY RESULTS TO STOCK OBJECTS (for scanner.py integration)
# ═══════════════════════════════════════════════════════════════════════════════

def apply_results_to_stocks(stocks: List[Any], results: List[InvestmentGateResult]) -> tuple:
    """
    Apply Investment Gate results back to Stock objects.

    Returns:
        (pass_stocks, fail_stocks) — lists of Stock objects
    """
    lookup = {r.ticker: r for r in results}
    pass_stocks = []
    fail_stocks = []

    for stock in stocks:
        ticker = getattr(stock, 'symbol', getattr(stock, 'ticker', ''))
        if ticker not in lookup:
            continue

        r = lookup[ticker]

        # Map to existing Stock fields (backward compatible with scanner.py)
        if hasattr(stock, 'final_decision'):
            if r.verdict == GateVerdict.STRONG_BUY:
                stock.final_decision = "PASS"
            elif r.verdict == GateVerdict.SPEC_BUY:
                stock.final_decision = "PASS"
            elif r.verdict == GateVerdict.NO_GO:
                stock.final_decision = "FAIL"
            else:
                stock.final_decision = "ERROR"

        # Gatekeeper-era fields (backward compat)
        if hasattr(stock, 'conviction'):
            stock.conviction = r.conviction
        if hasattr(stock, 'catalyst_summary'):
            stock.catalyst_summary = r.catalyst_summary
        if hasattr(stock, 'red_flag_level'):
            stock.red_flag_level = r.red_flag_level
        if hasattr(stock, 'action'):
            stock.action = r.action
        if hasattr(stock, 'reasoning'):
            stock.reasoning = r.reasoning
        if hasattr(stock, 'bullish_factors'):
            stock.bullish_factors = r.key_bullish
        if hasattr(stock, 'risk_factors'):
            stock.risk_factors = r.key_risks
        if hasattr(stock, 'sector_status'):
            stock.sector_status = r.analyst_trend
        if hasattr(stock, 'upside_potential'):
            stock.upside_potential = "High (50%+)" if r.catalyst_present else "Uncertain"

        # Gate-specific fields (for Deep DD consumption)
        if hasattr(stock, 'gate_verdict'):
            stock.gate_verdict = r.verdict.value
        if hasattr(stock, 'gate_conviction'):
            stock.gate_conviction = r.conviction
        if hasattr(stock, 'gate_catalyst'):
            stock.gate_catalyst = r.catalyst_summary
        if hasattr(stock, 'gate_bear_case'):
            stock.gate_bear_case = r.bear_case
        if hasattr(stock, 'gate_math'):
            stock.gate_math = r.math_to_50

        # DD-era fields (backward compat)
        if hasattr(stock, 'dd_verdict'):
            stock.dd_verdict = r.verdict.value
        if hasattr(stock, 'dd_conviction'):
            stock.dd_conviction = r.conviction
        if hasattr(stock, 'dd_position_size'):
            stock.dd_position_size = r.position_size
        if hasattr(stock, 'dd_analysis'):
            stock.dd_analysis = r.reasoning
        if hasattr(stock, 'dd_key_catalyst'):
            stock.dd_key_catalyst = r.catalyst_summary
        if hasattr(stock, 'dd_fatal_flaw'):
            stock.dd_fatal_flaw = r.disqualifier_reason if r.disqualified else ""

        # Categorize
        if r.passed():
            pass_stocks.append(stock)
        elif r.verdict == GateVerdict.NO_GO:
            fail_stocks.append(stock)

    return pass_stocks, fail_stocks


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def _print_result(result: InvestmentGateResult) -> None:
    """Print a single result in a clean terminal format."""

    verdict_display = {
        GateVerdict.STRONG_BUY: "🟢 STRONG BUY",
        GateVerdict.SPEC_BUY:   "🟡 SPEC BUY",
        GateVerdict.NO_GO:      "🔴 NO GO",
        GateVerdict.ERROR:      "⚠️  ERROR",
    }

    verdict_str = verdict_display.get(result.verdict, "?")
    stars = "★" * result.conviction + "☆" * (10 - result.conviction)
    regime = result.valuation_regime or "Unknown"

    print(f"""
  ┌{'─' * 68}┐
  │ {result.ticker:<8} │ {verdict_str:<18} │ {stars} │ {result.position_size:<8} │
  │ Theme: {(result.theme or 'Unknown')[:30]:<30} │ Regime: {regime:<12} │ {result.theme_classification:<10} │
  ├{'─' * 68}┤""")

    # Red flags
    flag_icon = {"CLEAN": "✓", "MINOR": "⚠", "SEVERE": "✗"}.get(result.red_flag_level, "?")
    print(f"  │ Red Flags: {flag_icon} {result.red_flag_level:<54} │")
    for flag in (result.red_flags or [])[:2]:
        print(f"  │   └─ {str(flag)[:59]:<59} │")

    # Catalyst
    cat_icon = "✓" if result.catalyst_present else "✗"
    cat_text = (result.catalyst_summary or "None identified")[:52]
    print(f"  │ Catalyst:  {cat_icon} {cat_text:<54} │")
    if result.days_to_catalyst > 0:
        print(f"  │            └─ {result.days_to_catalyst} days until next catalyst{' ' * 35} │")

    # Analyst / Short interest
    print(f"  │ Analysts: {(result.analyst_trend or 'N/A'):<10} │ Short: {_safe_float(result.short_interest_pct):>5.1f}% │ Revisions: {(result.revision_trajectory or 'N/A'):<12} │")

    # Bull / Bear
    print(f"  ├{'─' * 68}┤")
    if result.bull_case:
        bull_lines = _wrap(result.bull_case, 64)
        print(f"  │ 📈 {bull_lines[0]:<64} │")
        for line in bull_lines[1:2]:
            print(f"  │    {line:<64} │")
    if result.bear_case:
        bear_short = result.bear_case[:64]
        print(f"  │ 📉 {bear_short:<64} │")
    if result.math_to_50:
        math_short = result.math_to_50[:64]
        print(f"  │ 🧮 {math_short:<64} │")

    # Action
    print(f"  ├{'─' * 68}┤")
    action = (result.action or "Review manually")[:60]
    print(f"  │ ACTION: {action:<59} │")
    if result.kill_switch:
        kill = result.kill_switch[:58]
        print(f"  │ KILL:   {kill:<59} │")
    print(f"  └{'─' * 68}┘")


def _wrap(text: str, width: int) -> List[str]:
    """Word-wrap text to given width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current += (" " + word if current else word)
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _print_summary(results: List[InvestmentGateResult], total_cost: float) -> None:
    """Print summary of all results."""

    strong = [r for r in results if r.verdict == GateVerdict.STRONG_BUY]
    spec = [r for r in results if r.verdict == GateVerdict.SPEC_BUY]
    nogo = [r for r in results if r.verdict == GateVerdict.NO_GO]
    errors = [r for r in results if r.verdict == GateVerdict.ERROR]

    total_in = sum(r.input_tokens for r in results)
    total_out = sum(r.output_tokens for r in results)

    print(f"""
  ╔{'═' * 68}╗
  ║{'INVESTMENT GATE SUMMARY'.center(68)}║
  ╠{'═' * 68}╣
  ║  🟢 STRONG BUY: {len(strong):<3} — Full position, high conviction{' ' * 18}║
  ║  🟡 SPEC BUY:   {len(spec):<3} — Reduced position, thesis-dependent{' ' * 14}║
  ║  🔴 NO GO:      {len(nogo):<3} — Do not trade{' ' * 36}║""")

    if errors:
        print(f"  ║  ⚠️  ERRORS:    {len(errors):<3} — Manual review required{' ' * 26}║")

    print(f"  ╠{'═' * 68}╣")

    if strong:
        print(f"  ║ READY TO TRADE:{' ' * 52}║")
        for r in strong:
            stars = "★" * r.conviction + "☆" * (10 - r.conviction)
            cat = (r.catalyst_summary or "Catalyst confirmed")[:30]
            print(f"  ║   {r.ticker:<6} {stars} │ {cat:<30} ║")

    if spec:
        print(f"  ║ TRADE WITH CAUTION:{' ' * 48}║")
        for r in spec:
            stars = "★" * r.conviction + "☆" * (10 - r.conviction)
            reason = (r.reasoning[:30] if r.reasoning else "Spec setup")
            print(f"  ║   {r.ticker:<6} {stars} │ {reason:<30} ║")

    if nogo:
        print(f"  ║ REJECTED:{' ' * 58}║")
        for r in nogo:
            reason = r.disqualifier_reason or (r.red_flags[0] if r.red_flags else r.reasoning[:45] if r.reasoning else "Failed gate")
            print(f"  ║   {r.ticker:<6} │ {str(reason)[:55]:<55} ║")

    print(f"  ╠{'═' * 68}╣")
    print(f"  ║ 💰 {total_in:,} in + {total_out:,} out tokens = ${total_cost:.4f}{' ' * 20} ║")
    print(f"  ╚{'═' * 68}╝")


def _save_report(result: InvestmentGateResult) -> None:
    """Save assessment report to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"gate_{result.ticker}_{timestamp}.md"

    with open(filename, 'w') as f:
        f.write(f"# Investment Gate Report: {result.ticker}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Verdict:** {result.verdict.value}\n")
        f.write(f"**Conviction:** {result.conviction}/10\n")
        f.write(f"**Position Size:** {result.position_size}\n")
        f.write(f"**Regime:** {result.valuation_regime}\n\n")
        f.write("---\n\n")
        f.write(f"**Bull Case:** {result.bull_case}\n\n")
        f.write(f"**Bear Case:** {result.bear_case}\n\n")
        f.write(f"**Bear Rebuttal:** {result.bear_rebuttal}\n\n")
        f.write(f"**Math to 50%:** {result.math_to_50}\n\n")
        f.write(f"**Kill Switch:** {result.kill_switch}\n\n")
        f.write("---\n\n")
        f.write(f"**Reasoning:** {result.reasoning}\n\n")
        f.write(f"**Action:** {result.action}\n")

    print(f"  📄 Report: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Command-line interface for standalone Investment Gate runs."""
    import argparse

    parser = argparse.ArgumentParser(description="Investment Gate — Final Assessment Before Entry")
    parser.add_argument("tickers", nargs="+", help="Ticker symbols to analyze")
    parser.add_argument("--theme", default="", help="Investment theme")
    parser.add_argument("--regime", default="", choices=["OPTIONALITY", "FUNDAMENTAL", "TRANSITION", ""],
                        help="Valuation regime hint")
    parser.add_argument("--price", type=float, default=0.0, help="Current price")
    parser.add_argument("--no-web", action="store_true", help="Disable web search (testing)")
    parser.add_argument("--save", action="store_true", help="Save reports")

    args = parser.parse_args()

    client = create_client()

    print("\n" + "═" * 70)
    print("  INVESTMENT GATE — Final Assessment Before Entry")
    print("═" * 70)

    stocks = [{
        "ticker": t.upper(),
        "symbol": t.upper(),
        "price": args.price,
        "beta": 2.0,
        "banker": 65.0,
        "tier": "T1",
        "theme": args.theme or "Test Theme",
        "theme_fit": "GOOD FIT",
        "theme_classification": "INVESTABLE",
        "valuation_regime": args.regime
    } for t in args.tickers]

    results = run_investment_gate_batch(
        client=client,
        stocks=stocks,
        use_web_search=not args.no_web,
        save_reports=args.save
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
