#!/usr/bin/env python3
"""
DEEP DUE DILIGENCE v1.0 — Opus Deep Analysis for Newsletter + Portfolio
========================================================================

REPLACES: dd_automator.py (quick mode removed, full mode upgraded)

PURPOSE:
Runs ONLY on stocks that passed the Investment Gate (typically 1-3 stocks).
Uses Opus with extended thinking for genuine deep analysis.

TWO JOBS:
  1. NEWSLETTER CONTENT — Produces structured "Why Now", "The Math", bear/bull
     cases, and action items ready for newsletter compilation
  2. FINAL PORTFOLIO GATE — Can veto an Investment Gate pass if deep analysis
     reveals issues the initial screen missed. Only DD-PASS stocks get added
     to the portfolio.

KEY DESIGN PRINCIPLE — REGIME-AWARE ANALYSIS:
Carries the valuation regime (OPTIONALITY/FUNDAMENTAL/TRANSITION) from the
thematic analyzer through to deep analysis. A pre-revenue quantum stock gets
assessed on milestones and narrative momentum; an AI infrastructure stock gets
assessed on earnings revisions and multiple expansion.

COST:
  ~$1-2 per stock (Opus + extended thinking + web search)
  But only runs on 1-3 stocks, so typical total: $2-5 per scan

Pipeline position:
  Technical → Themes → Investment Gate (filter) → **Deep DD** → Portfolio + Newsletter

Usage:
    from deep_dd import run_deep_dd_batch, DeepDDResult
    results = run_deep_dd_batch(client, pass_stocks, use_web_search=True)
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

try:
    import anthropic
except ImportError:
    print("Install with: pip install anthropic")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-opus-4-20250514"
MAX_OUTPUT_TOKENS = 8000
THINKING_BUDGET = 10000
INTER_STOCK_DELAY = 15.0  # Opus is slower, give it room


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DeepDDResult:
    """Result from Deep Due Diligence — structured for newsletter + portfolio."""
    ticker: str

    # ── Final Verdict (can override Investment Gate) ──
    dd_verdict: str = ""          # STRONG BUY / SPEC BUY / NO GO
    dd_conviction: int = 0        # 1-10 scale
    dd_position_size: str = ""    # FULL / REDUCED / PASS

    # ── Newsletter Content (structured, not prose) ──
    elevator_pitch: str = ""      # 2-3 sentences: why this stock, why now
    why_now: str = ""             # Key catalyst with date
    the_math: str = ""            # Path to 50%+ return (regime-adapted)
    bear_case: str = ""           # Steelmanned bear argument
    bear_rebuttal: str = ""       # Why the bear is wrong
    risk_to_monitor: str = ""     # Single most important risk
    action_recommendation: str = "" # "Buy Monday at open, full position" etc.

    # ── Deep Analysis Fields ──
    revenue_trajectory: str = ""  # ACCELERATING / STABLE / DECELERATING / PRE-REVENUE
    earnings_leverage: str = ""   # How revenue growth translates to EPS growth
    catalyst_timeline: List[Dict[str, str]] = field(default_factory=list)  # [{event, date, impact}]
    variant_perception: str = ""  # What we see that the market doesn't
    key_assumption: str = ""      # The ONE thing that must be true
    kill_switch: str = ""         # What triggers early exit
    downside_floor: str = ""      # Where value buyers step in / max realistic loss

    # ── Regime Context ──
    valuation_regime: str = ""    # OPTIONALITY / FUNDAMENTAL / TRANSITION
    regime_assessment: str = ""   # How regime affects the analysis

    # ── Fatal Flaw (if NO GO) ──
    fatal_flaw: str = ""          # Specific reason for rejection
    reconsider_if: str = ""       # What would flip the verdict

    # ── Meta ──
    dd_thinking: str = ""         # Extended thinking content
    dd_cost: float = 0.0
    error: str = ""
    timestamp: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def passed(self) -> bool:
        """Did this stock pass Deep DD?"""
        return self.dd_verdict in ("STRONG BUY", "SPEC BUY", "SPECULATIVE BUY")

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the Lead Portfolio Manager at a high-conviction growth fund, conducting deep due diligence on a stock that has already passed automated screening.

CONTEXT:
This stock has passed:
1. Technical screening: Weekly HMA breakout + institutional accumulation (UC rising) + >25% below 52w high
2. Thematic analysis: Confirmed in a healthy trending theme with good company fit
3. Investment Gate: Initial quality check passed — catalysts confirmed, no disqualifiers

YOUR TWO JOBS:
1. VALIDATE OR VETO: Does deep analysis confirm the Investment Gate's pass? You have veto power.
2. PRODUCE NEWSLETTER CONTENT: If it passes, generate structured content for our investor newsletter.

═══════════════════════════════════════════════════════════════════
VALUATION REGIME AWARENESS
═══════════════════════════════════════════════════════════════════

The thematic analyzer has classified this stock's theme into a valuation regime. 
Your analysis MUST adapt accordingly.

OPTIONALITY REGIME (pre-revenue, milestone-driven):
- Don't assess P/E or earnings — focus on milestone velocity, funding, narrative expansion
- "The Math" = milestone → narrative expansion → institutional re-rating
- Example: RGTI went +705% with zero revenue because quantum milestones were hitting
- Risk: These can go to zero. Your job is to assess whether the milestones are real.

FUNDAMENTAL REGIME (revenue and earnings-driven):
- Standard: Revenue growth, operating leverage, earnings revisions, multiple expansion
- "The Math" = EPS growth × multiple expansion = target price
- Red flag: Capex growing 3x faster than revenue (late-cycle capital divergence)
- Key metric: Earnings revision trajectory — ACCELERATING (buy) vs DECELERATING (avoid)

TRANSITION REGIME (shifting from optionality to fundamental pricing):
- Highest risk — market changing what it values
- Key: Is revenue materializing fast enough to justify optionality-era valuation?
- Can produce violent repricing in either direction

═══════════════════════════════════════════════════════════════════
RESEARCH PROTOCOL
═══════════════════════════════════════════════════════════════════

Phase 1 — GROWTH TRAJECTORY
Search for recent earnings, revenue trends, guidance, operating metrics.
- For FUNDAMENTAL: Revenue acceleration? Operating leverage? NRR/retention?
- For OPTIONALITY: Milestone announcements? Funding? New partnerships?
- For TRANSITION: Revenue vs expectations? Customer traction?

Phase 2 — CATALYST DEEP DIVE
Search for upcoming events that could drive re-rating.
- Earnings dates, guidance updates, product launches
- Regulatory decisions, patent approvals
- Conference presentations, investor days
- Management equity grants with price targets

Phase 3 — BEAR CASE INVESTIGATION
Search specifically for the short thesis and risks.
- What's the #1 argument a smart short seller would make?
- Can you DISMANTLE it with data? If not, is it a FATAL FLAW?
- Insider selling patterns, dilution history, competitive threats

Phase 4 — VALUATION & RETURN MATH
Search for valuation metrics, peer comparisons, historical ranges.
- Current multiple vs own 3-year average and vs peers
- Construct the specific math: growth + re-rating = target price
- Where's the downside floor? (Value buyers, strategic acquirer interest)

═══════════════════════════════════════════════════════════════════
OUTPUT — Return ONLY valid JSON
═══════════════════════════════════════════════════════════════════

{
    "ticker": "SYMBOL",
    "verdict": "STRONG BUY|SPEC BUY|NO GO",
    "conviction": 1-10,
    "position_size": "FULL|REDUCED|PASS",

    "elevator_pitch": "2-3 sentences: why this stock, why NOW, what's the variant perception",
    "why_now": "Key catalyst with specific date — e.g., 'Earnings Mar 5: consensus at $0.42 but whisper number $0.50+ based on channel checks'",
    "the_math": "Specific path to 50%+. For FUNDAMENTAL: 'Revenue grows 35% → op leverage drives 60% EPS growth → multiple re-rates from 25x to 35x → $180 target (+65%)'. For OPTIONALITY: 'If quantum error correction milestone hit in Q2, institutional coverage expands from 5 to 15 analysts → comparable to early AI re-rating of 3-5x'",
    "bear_case": "The smartest short-seller argument, steelmanned — not a strawman",
    "bear_rebuttal": "Why the bear is wrong OR why the risk is acceptable — with data",
    "risk_to_monitor": "The single most important risk to watch — specific and actionable",
    "action_recommendation": "Specific: 'Buy Monday at open at ~$X. Full position. Set trailing stop at $Y (-20%). Monitor earnings Mar 5.'",

    "revenue_trajectory": "ACCELERATING|STABLE|DECELERATING|PRE_REVENUE",
    "earnings_leverage": "How 10% revenue growth translates to earnings growth — e.g., 'High operating leverage: 10% revenue growth → 40% EPS growth at current margins'",
    "catalyst_timeline": [
        {"event": "Q4 Earnings", "date": "Mar 5", "impact": "Beat likely based on channel checks, +10-15% on beat"},
        {"event": "Investor Day", "date": "Mar 20", "impact": "New product roadmap reveal, potential guidance raise"}
    ],
    "variant_perception": "What we see that consensus misses — the edge",
    "key_assumption": "The ONE thing that must be true for this to work",
    "kill_switch": "What would make us exit early — specific trigger, not vague risk",
    "downside_floor": "Where value buyers step in — e.g., '$85 (-15%) based on 20x trough earnings, strategic acquisition interest below $80'",

    "valuation_regime_applied": "OPTIONALITY|FUNDAMENTAL|TRANSITION",
    "regime_assessment": "One sentence on how the regime affects this specific stock's assessment",

    "fatal_flaw": "Only if NO GO — the specific dealbreaker. Empty string if verdict is BUY.",
    "reconsider_if": "Only if NO GO — what change would flip the verdict. Empty string if BUY."
}

═══════════════════════════════════════════════════════════════════
VERDICT RULES
═══════════════════════════════════════════════════════════════════

STRONG BUY (7-10):
- Variant perception is clear and defensible
- Math to 50% requires only 1-2 things to go right
- Bear case can be dismantled or is acceptable risk
- Catalyst timeline is specific and near-term
→ FULL position

SPEC BUY (4-6):
- Thesis directionally correct but execution-dependent
- Math works but requires multiple things going right
- Bear case has some merit but is outweighed
- For OPTIONALITY: milestones progressing but timeline uncertain
→ REDUCED (50%) position

NO GO (1-3):
- Bear case cannot be dismantled and is a FATAL FLAW
- Math to 50% requires heroic assumptions
- No specific near-term catalyst
- For FUNDAMENTAL: revisions negative + valuation stretched
- For OPTIONALITY: milestones stalling + narrative contracting
→ PASS — do not add to portfolio

IMPORTANT: This stock already passed multiple gates. Your job is deep validation,
not reflexive rejection. If it's good, be confident about it. Only veto for
SPECIFIC, evidence-based reasons that the earlier gates couldn't catch."""


# ═══════════════════════════════════════════════════════════════════════════════
# CORE: SINGLE STOCK DEEP DD
# ═══════════════════════════════════════════════════════════════════════════════

def run_single_deep_dd(
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
    gate_conviction: int = 0,
    gate_catalyst: str = "",
    gate_bull_case: str = "",
    gate_bear_case: str = "",
    gate_math: str = "",
    gate_reasoning: str = "",
    use_web_search: bool = True,
    save_report: bool = False,
    max_retries: int = 3
) -> DeepDDResult:
    """
    Run Opus deep due diligence on a single stock.

    This runs ONLY on stocks that passed the Investment Gate.
    Produces newsletter content and has veto power over the gate.
    """
    from datetime import datetime
    current_year = datetime.now().year

    # Build context from Investment Gate results
    gate_context = ""
    if gate_catalyst or gate_bull_case or gate_bear_case:
        gate_context = f"""
INVESTMENT GATE FINDINGS (from initial screening):
- Gate Conviction: {gate_conviction}/10
- Catalyst: {gate_catalyst or 'Not specified'}
- Bull Case: {gate_bull_case or 'Not specified'}
- Bear Case: {gate_bear_case or 'Not specified'}
- Math to 50%: {gate_math or 'Not assessed'}
- Reasoning: {gate_reasoning or 'Not specified'}

Your job is to DEEPEN this analysis, not repeat it. Confirm or challenge these findings."""

    regime_hint = ""
    if valuation_regime:
        regime_hint = f"\nVALUATION REGIME (from thematic analyzer): {valuation_regime}"
    else:
        regime_hint = "\nVALUATION REGIME: Not specified. Determine from your research."

    user_prompt = f"""# DEEP DUE DILIGENCE: {ticker}

## Stock Profile
| Field | Value |
|-------|-------|
| Ticker | {ticker} |
| Price | ${price:.2f} |
| Beta | {beta:.2f} |
| Banker (UC) | {banker:.0f} |
| Tier | {tier} |
| Theme | {theme} |
| Theme Fit | {theme_fit} |
| Theme Classification | {theme_classification} |
{regime_hint}

{gate_context}

## Your Mission
Conduct thorough deep due diligence following the 4-phase research protocol in your instructions.

SEARCH SUGGESTIONS:
1. "{ticker} earnings results revenue growth {current_year}"
2. "{ticker} upcoming catalyst conference investor day {current_year}"
3. "{ticker} short thesis bear case risk concerns"
4. "{ticker} valuation P/E P/S historical multiple peers"

Take your time with extended thinking. This analysis controls whether we invest real capital.

Return ONLY the JSON object specified in your instructions, no other text."""

    result = DeepDDResult(ticker=ticker, valuation_regime=valuation_regime)

    for attempt in range(max_retries):
        try:
            api_params = {
                "model": MODEL,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": THINKING_BUDGET
                },
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }

            if use_web_search:
                api_params["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

            response = client.messages.create(**api_params)

            # Track tokens
            input_tokens = getattr(response.usage, 'input_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', 0)

            # Extract text and thinking
            analysis_text = ""
            thinking_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    analysis_text += block.text
                elif hasattr(block, 'thinking'):
                    thinking_text += block.thinking

            # Parse JSON from response
            match = re.search(r'\{[\s\S]*\}', analysis_text)
            if match:
                data = json.loads(match.group())
                result = _parse_dd_result(data, ticker, valuation_regime,
                                          input_tokens, output_tokens, thinking_text)

                if save_report:
                    _save_dd_report(result, theme, tier, thinking_text)

                return result

            raise ValueError("No valid JSON in response")

        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"    ⚠️  Rate limit, waiting {wait}s...")
            time.sleep(wait)

        except anthropic.BadRequestError as e:
            if "credit" in str(e).lower() or "billing" in str(e).lower():
                raise RuntimeError("BILLING_ERROR: Add credits at console.anthropic.com")
            result.error = str(e)
            result.dd_verdict = "ERROR"
            return result

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"    ⚠️  JSON parse error, retrying... ({e})")
                time.sleep(5)
            else:
                result.error = f"JSON parse failed: {e}"
                result.dd_verdict = "ERROR"
                return result

        except Exception as e:
            result.error = str(e)
            result.dd_verdict = "ERROR"
            return result

    result.error = f"Failed after {max_retries} attempts"
    result.dd_verdict = "ERROR"
    return result


def _parse_dd_result(
    data: dict,
    ticker: str,
    valuation_regime: str,
    input_tokens: int,
    output_tokens: int,
    thinking_text: str
) -> DeepDDResult:
    """Parse JSON response into DeepDDResult."""

    # Normalize verdict
    raw_verdict = data.get("verdict", "").upper()
    if "STRONG" in raw_verdict:
        verdict = "STRONG BUY"
    elif "SPEC" in raw_verdict:
        verdict = "SPEC BUY"
    elif "NO" in raw_verdict:
        verdict = "NO GO"
    else:
        verdict = "NO GO"

    # Parse catalyst timeline
    raw_catalysts = data.get("catalyst_timeline", [])
    catalysts = []
    for cat in raw_catalysts:
        if isinstance(cat, dict):
            catalysts.append({
                "event": cat.get("event", ""),
                "date": cat.get("date", ""),
                "impact": cat.get("impact", "")
            })

    # Cost estimate (Opus pricing)
    cost = (input_tokens * 15 + output_tokens * 75) / 1_000_000

    return DeepDDResult(
        ticker=ticker,
        dd_verdict=verdict,
        dd_conviction=data.get("conviction", 0),
        dd_position_size=data.get("position_size", "PASS"),

        elevator_pitch=data.get("elevator_pitch", ""),
        why_now=data.get("why_now", ""),
        the_math=data.get("the_math", ""),
        bear_case=data.get("bear_case", ""),
        bear_rebuttal=data.get("bear_rebuttal", ""),
        risk_to_monitor=data.get("risk_to_monitor", ""),
        action_recommendation=data.get("action_recommendation", ""),

        revenue_trajectory=data.get("revenue_trajectory", ""),
        earnings_leverage=data.get("earnings_leverage", ""),
        catalyst_timeline=catalysts,
        variant_perception=data.get("variant_perception", ""),
        key_assumption=data.get("key_assumption", ""),
        kill_switch=data.get("kill_switch", ""),
        downside_floor=data.get("downside_floor", ""),

        valuation_regime=data.get("valuation_regime_applied", valuation_regime),
        regime_assessment=data.get("regime_assessment", ""),

        fatal_flaw=data.get("fatal_flaw", ""),
        reconsider_if=data.get("reconsider_if", ""),

        dd_thinking=thinking_text,
        dd_cost=cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def run_deep_dd_batch(
    stocks: List[Any],
    client: Optional[anthropic.Anthropic] = None,
    use_web_search: bool = True,
    save_reports: bool = False,
    max_stocks: Optional[int] = None
) -> List[DeepDDResult]:
    """
    Run Deep DD on stocks that passed the Investment Gate.

    Args:
        stocks: List of Stock objects that passed Investment Gate
        client: Anthropic client (created if not provided)
        use_web_search: Enable web search (strongly recommended)
        save_reports: Save individual reports
        max_stocks: Limit number of stocks

    Returns:
        List of DeepDDResult
    """
    if not stocks:
        return []

    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  ERROR: ANTHROPIC_API_KEY not set")
            return []
        client = anthropic.Anthropic(api_key=api_key)

    if max_stocks:
        stocks = stocks[:max_stocks]

    results = []
    total_cost = 0.0

    print(f"\n  Running DEEP DD (Opus) on {len(stocks)} Investment Gate pass(es)")
    print(f"  {'═' * 60}")
    print(f"  🧠 Model: Opus + Extended Thinking ({THINKING_BUDGET:,} token budget)")
    print(f"  🌐 Web search: {'Enabled' if use_web_search else 'Disabled'}")
    print(f"  💰 Estimated cost: ~${len(stocks) * 1.5:.2f}")
    print(f"  ⏱️  ~1-2 minutes per stock")
    print(f"  {'─' * 60}")

    for i, stock in enumerate(stocks):
        # Extract attributes
        if hasattr(stock, 'symbol'):
            ticker = stock.symbol
            attrs = {
                'price': getattr(stock, 'price', 0.0),
                'beta': getattr(stock, 'beta', 0.0),
                'banker': getattr(stock, 'banker', 0.0),
                'tier': getattr(stock, 'tier', ''),
                'theme': getattr(stock, 'theme', ''),
                'theme_fit': getattr(stock, 'theme_verdict', ''),
                'theme_classification': getattr(stock, 'theme_classification', ''),
                'valuation_regime': getattr(stock, 'valuation_regime', ''),
                # Investment Gate results to pass through as context
                'gate_conviction': getattr(stock, 'conviction', 0),
                'gate_catalyst': getattr(stock, 'catalyst_summary', ''),
                'gate_bull_case': getattr(stock, 'dd_analysis', '') or getattr(stock, 'reasoning', ''),
                'gate_bear_case': '',
                'gate_math': '',
                'gate_reasoning': getattr(stock, 'reasoning', ''),
            }
        else:
            ticker = stock.get('symbol', stock.get('ticker', 'UNKNOWN'))
            attrs = {
                'price': stock.get('price', 0.0),
                'beta': stock.get('beta', 0.0),
                'banker': stock.get('banker', 0.0),
                'tier': stock.get('tier', ''),
                'theme': stock.get('theme', ''),
                'theme_fit': stock.get('theme_fit', stock.get('theme_verdict', '')),
                'theme_classification': stock.get('theme_classification', ''),
                'valuation_regime': stock.get('valuation_regime', ''),
                'gate_conviction': stock.get('conviction', 0),
                'gate_catalyst': stock.get('catalyst_summary', ''),
                'gate_bull_case': stock.get('reasoning', ''),
                'gate_bear_case': stock.get('bear_case', ''),
                'gate_math': stock.get('math_to_50', ''),
                'gate_reasoning': stock.get('reasoning', ''),
            }

        print(f"\n  [{i+1}/{len(stocks)}] {ticker} — {attrs['theme'] or 'Unknown Theme'}")
        print(f"  {'─' * 50}")
        print(f"  🧠 Deep analysis in progress... (1-2 minutes)")

        result = run_single_deep_dd(
            client=client,
            ticker=ticker,
            use_web_search=use_web_search,
            save_report=save_reports,
            **attrs
        )

        results.append(result)
        total_cost += result.dd_cost

        # Print result
        if result.error:
            print(f"  ❌ ERROR: {result.error}")
        else:
            _print_dd_result(result)

        print()

        # Delay between stocks
        if i < len(stocks) - 1:
            time.sleep(INTER_STOCK_DELAY)

    # Summary
    _print_dd_summary(results, total_cost)
    return results


def apply_dd_to_stocks(stocks: List[Any], dd_results: List[DeepDDResult]) -> tuple:
    """
    Apply Deep DD results back to Stock objects.

    Returns:
        (dd_pass_stocks, dd_fail_stocks)
    """
    lookup = {r.ticker: r for r in dd_results}
    dd_pass = []
    dd_fail = []

    for stock in stocks:
        ticker = getattr(stock, 'symbol', stock.get('symbol', stock.get('ticker', '')))
        if ticker not in lookup:
            continue

        r = lookup[ticker]

        # Apply DD fields to Stock object (backward compat with scanner.py)
        if hasattr(stock, 'dd_verdict'):
            stock.dd_verdict = r.dd_verdict
        if hasattr(stock, 'dd_conviction'):
            stock.dd_conviction = r.dd_conviction
        if hasattr(stock, 'dd_position_size'):
            stock.dd_position_size = r.dd_position_size
        if hasattr(stock, 'dd_analysis'):
            stock.dd_analysis = r.elevator_pitch
        if hasattr(stock, 'dd_key_catalyst'):
            stock.dd_key_catalyst = r.why_now
        if hasattr(stock, 'dd_fatal_flaw'):
            stock.dd_fatal_flaw = r.fatal_flaw

        # Categorize
        if r.passed():
            dd_pass.append(stock)
        elif r.dd_verdict == "NO GO":
            dd_fail.append(stock)

    return dd_pass, dd_fail


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def _print_dd_result(result: DeepDDResult) -> None:
    """Print Deep DD result in terminal."""

    verdict_icons = {
        "STRONG BUY": "🟢 STRONG BUY",
        "SPEC BUY": "🟡 SPEC BUY",
        "NO GO": "🔴 NO GO",
        "ERROR": "⚠️  ERROR"
    }
    verdict_str = verdict_icons.get(result.dd_verdict, "?")
    stars = "★" * result.dd_conviction + "☆" * (10 - result.dd_conviction)

    print(f"""
  ┌{'─' * 68}┐
  │ {result.ticker:<8} │ {verdict_str:<18} │ {stars} │ {result.dd_position_size:<8} │
  ├{'─' * 68}┤""")

    # Elevator pitch
    if result.elevator_pitch:
        for line in _wrap(result.elevator_pitch, 64):
            print(f"  │ 📋 {line:<64} │")

    # Why now
    if result.why_now:
        for line in _wrap(f"WHY NOW: {result.why_now}", 64):
            print(f"  │ ⏰ {line:<64} │")

    # The math
    if result.the_math:
        for line in _wrap(f"MATH: {result.the_math}", 64):
            print(f"  │ 🧮 {line:<64} │")

    # Bear case
    if result.bear_case:
        bear_short = result.bear_case[:64]
        print(f"  │ 🐻 {bear_short:<64} │")

    # Risk
    if result.risk_to_monitor:
        risk_short = result.risk_to_monitor[:64]
        print(f"  │ ⚠️  {risk_short:<64} │")

    # Action
    print(f"  ├{'─' * 68}┤")
    if result.action_recommendation:
        for line in _wrap(result.action_recommendation, 62)[:2]:
            print(f"  │ → {line:<65} │")

    if result.kill_switch:
        kill_short = result.kill_switch[:62]
        print(f"  │ ✂ {kill_short:<65} │")

    # Fatal flaw (if NO GO)
    if result.fatal_flaw:
        print(f"  ├{'─' * 68}┤")
        for line in _wrap(f"FATAL FLAW: {result.fatal_flaw}", 64):
            print(f"  │ ❌ {line:<64} │")
        if result.reconsider_if:
            for line in _wrap(f"Reconsider if: {result.reconsider_if}", 64):
                print(f"  │    {line:<64} │")

    print(f"  │ 💰 Cost: ${result.dd_cost:.3f}{' ' * 50} │")
    print(f"  └{'─' * 68}┘")


def _wrap(text: str, width: int) -> List[str]:
    """Word-wrap text."""
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


def _print_dd_summary(results: List[DeepDDResult], total_cost: float) -> None:
    """Print summary."""
    strong = [r for r in results if r.dd_verdict == "STRONG BUY"]
    spec = [r for r in results if r.dd_verdict in ("SPEC BUY", "SPECULATIVE BUY")]
    nogo = [r for r in results if r.dd_verdict == "NO GO"]
    errors = [r for r in results if r.dd_verdict == "ERROR" or r.error]

    print(f"""
  ╔{'═' * 60}╗
  ║{'DEEP DD SUMMARY'.center(60)}║
  ╠{'═' * 60}╣
  ║  🟢 STRONG BUY: {len(strong):<3} — Add to portfolio, full position{' ' * 8}║
  ║  🟡 SPEC BUY:   {len(spec):<3} — Add to portfolio, reduced position{' ' * 4}║
  ║  🔴 NO GO:      {len(nogo):<3} — Vetoed, do NOT add to portfolio{' ' * 7}║""")

    if errors:
        print(f"  ║  ⚠️  ERRORS:    {len(errors):<3} — Manual review required{' ' * 18}║")

    print(f"  ╠{'═' * 60}╣")

    for r in strong + spec:
        why = (r.why_now or r.elevator_pitch or "")[:45]
        print(f"  ║  {r.ticker:<6} [{r.dd_verdict:<10}] {why:<39}║")

    for r in nogo:
        flaw = (r.fatal_flaw or "Rejected")[:45]
        print(f"  ║  {r.ticker:<6} [NO GO     ] {flaw:<39}║")

    print(f"  ╠{'═' * 60}╣")
    print(f"  ║  💰 Total Deep DD Cost: ${total_cost:.2f}{' ' * 34}║")
    print(f"  ╚{'═' * 60}╝")


def _save_dd_report(result: DeepDDResult, theme: str, tier: str, thinking: str) -> None:
    """Save full DD report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"deep_dd_{result.ticker}_{timestamp}.md"

    with open(filename, 'w') as f:
        f.write(f"# Deep Due Diligence: {result.ticker}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Verdict:** {result.dd_verdict} ({result.dd_conviction}/10)\n")
        f.write(f"**Position:** {result.dd_position_size}\n")
        f.write(f"**Theme:** {theme} | **Regime:** {result.valuation_regime}\n\n")

        f.write("---\n\n")
        f.write(f"## Elevator Pitch\n{result.elevator_pitch}\n\n")
        f.write(f"## Why Now\n{result.why_now}\n\n")
        f.write(f"## The Math to 50%+\n{result.the_math}\n\n")
        f.write(f"## Bear Case\n{result.bear_case}\n\n")
        f.write(f"## Bear Rebuttal\n{result.bear_rebuttal}\n\n")
        f.write(f"## Risk to Monitor\n{result.risk_to_monitor}\n\n")
        f.write(f"## Action\n{result.action_recommendation}\n\n")

        if result.catalyst_timeline:
            f.write("## Catalyst Timeline\n")
            f.write("| Event | Date | Impact |\n|---|---|---|\n")
            for cat in result.catalyst_timeline:
                f.write(f"| {cat.get('event','')} | {cat.get('date','')} | {cat.get('impact','')} |\n")
            f.write("\n")

        f.write(f"## Variant Perception\n{result.variant_perception}\n\n")
        f.write(f"## Key Assumption\n{result.key_assumption}\n\n")
        f.write(f"## Kill Switch\n{result.kill_switch}\n\n")
        f.write(f"## Downside Floor\n{result.downside_floor}\n\n")

        if result.fatal_flaw:
            f.write(f"## Fatal Flaw\n{result.fatal_flaw}\n\n")
            f.write(f"## Reconsider If\n{result.reconsider_if}\n\n")

        if thinking:
            f.write("---\n\n## Extended Thinking\n\n")
            f.write("<details>\n<summary>Click to expand</summary>\n\n")
            f.write(f"```\n{thinking}\n```\n\n</details>\n")

    print(f"  📄 Report: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Deep Due Diligence — Opus Analysis")
    parser.add_argument("tickers", nargs="+", help="Ticker(s) to analyze")
    parser.add_argument("--theme", default="", help="Theme context")
    parser.add_argument("--regime", default="", choices=["OPTIONALITY", "FUNDAMENTAL", "TRANSITION", ""],
                        help="Valuation regime")
    parser.add_argument("--price", type=float, default=0.0, help="Current price")
    parser.add_argument("--no-web", action="store_true", help="Disable web search")
    parser.add_argument("--save", action="store_true", help="Save reports")

    args = parser.parse_args()

    stocks = [{
        "ticker": t.upper(),
        "symbol": t.upper(),
        "price": args.price,
        "beta": 2.0,
        "banker": 65.0,
        "tier": "TIER1",
        "theme": args.theme or "Test Theme",
        "theme_fit": "GOOD FIT",
        "theme_classification": "INVESTABLE",
        "valuation_regime": args.regime,
    } for t in args.tickers]

    print("\n" + "═" * 70)
    print("  DEEP DUE DILIGENCE — Opus + Extended Thinking")
    print("═" * 70)

    results = run_deep_dd_batch(
        stocks=stocks,
        use_web_search=not args.no_web,
        save_reports=args.save
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
