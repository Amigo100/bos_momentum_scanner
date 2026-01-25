#!/usr/bin/env python3
"""
TWEET GENERATOR - Claude-Powered Final Tweet Generation
========================================================

Generates 21 ready-to-post tweets for the week based on scanner outputs.
Uses Claude API to create engaging financial content directly.

NEW CONTENT TYPES:
- Closed trades with P&L commentary
- Hot themes and why they're hot
- Cold themes and why to avoid
- System methodology highlights
- Buy signals with DD verdicts
- All linked back to Substack

Usage:
    python tweet_generator.py                              # Uses latest briefing
    python tweet_generator.py --briefing PATH              # Specific briefing file
    python tweet_generator.py --mock                       # Use mock data (no API)

Output:
    trades/tweets/tweets_{date}.json       # All 21 tweets with metadata
    trades/tweets/content_queue.json       # Ready for twitter_poster.py
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import re

# Load .env file if present (use explicit path relative to this script)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass  # dotenv not required if env vars set directly

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

# Import output path helpers
try:
    from output_paths import (
        get_current_dir,
        get_week_dir,
        ensure_output_structure,
        get_relative_path
    )
    OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    OUTPUT_PATHS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
TWEETS_DIR = TRADES_DIR / "tweets"
CHARTS_DIR = TRADES_DIR / "charts"

TWEETS_DIR.mkdir(parents=True, exist_ok=True)

# Sterling Signals branding
SUBSTACK_URL = "https://sterlingsignals.substack.com"
ACCOUNT_HANDLE = "@SterlingSignals"

# Claude model for tweet generation
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000

# Days and slots (increased from 3 to 5 per day to better use X API limits)
# X free tier allows ~50 tweets/day (1,500/month)
# Schedule aligned to US Eastern Time (ET)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = {
    1: "pre_market",     # 08:00 ET - Pre-market / Beat SPY / Roth IRA hooks
    2: "morning",        # 10:00 ET - 30min after market open
    3: "midday",         # 12:30 ET - Lunch break engagement
    4: "power_hour",     # 15:30 ET - CRITICAL: Power Hour reaction
    5: "after_hours"     # 18:00 ET - After-hours / engagement
}

# Import marketing vocabulary for validation
try:
    from marketing_vocabulary import (
        validate_content, BANNED_TERMS, APPROVED_VOCABULARY,
        POWER_PHRASES, US_AUDIENCE_HOOKS, validate_all_tweets
    )
    MARKETING_VOCABULARY_AVAILABLE = True
except ImportError:
    MARKETING_VOCABULARY_AVAILABLE = False
    BANNED_TERMS = []


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Tweet:
    """A single tweet ready for posting."""
    id: str
    day: str
    slot: int
    category: str
    text: str
    ticker: Optional[str] = None
    theme: Optional[str] = None
    image_path: Optional[str] = None
    scheduled_date: Optional[str] = None
    status: str = "pending"
    posted_at: Optional[str] = None
    tweet_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeeklyContent:
    """All content for the week."""
    pass_signals: List[Dict] = field(default_factory=list)
    caution_signals: List[Dict] = field(default_factory=list)
    sell_signals: List[Dict] = field(default_factory=list)
    open_positions: List[Dict] = field(default_factory=list)
    closed_trades: List[Dict] = field(default_factory=list)  # NEW
    prime_themes: List[Dict] = field(default_factory=list)
    investable_themes: List[Dict] = field(default_factory=list)
    selective_themes: List[Dict] = field(default_factory=list)
    avoid_themes: List[Dict] = field(default_factory=list)
    scan_date: str = ""
    chart_manifest: Dict[str, str] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE TWEET GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

TWEET_SYSTEM_PROMPT = """You are a financial content writer for Sterling Signals, a momentum trading newsletter on Substack targeting US active investors and swing traders.

Your task is to write engaging tweets for X/Twitter that:
1. Highlight trading signals, themes, and market insights
2. Drive engagement and newsletter subscriptions
3. Include relevant $TICKER cashtags
4. Stay under 280 characters
5. Use emojis sparingly but effectively
6. ALWAYS include link to newsletter or call-to-action

STYLE GUIDELINES:
- Confident but not arrogant
- Data-driven, specific numbers when available
- Professional trader voice, not hype
- Occasional humor is OK
- No financial advice disclaimers in tweets (save for bio)
- All times in Eastern Time (ET)

CRITICAL MARKETING LANGUAGE RULES - BANNED TERMS:
NEVER use these terms in any tweet:
- "HMA", "Hull Moving Average", "HMA Pivot"
- "Banker indicator", "Banker >= 55"
- "20% trailing stop", "20% stop", "trailing stop"
- "Beta >= 1.5", "beta threshold"
- "Break of Structure", "BoS", "BOS", "Weekly BoS"
- "Tier 1", "Tier 2", "Tier 3", "TIER1", "TIER2", "TIER3"
- "Gatekeeper"
- "UK ISA", "ISA account", "GMT", "BST", "UK Time"
- "RSI", "MACD", "KDJ"

APPROVED VOCABULARY - USE THESE INSTEAD:
- "Structural Pivot Confirmation" (not HMA Pivot)
- "Institutional Accumulation Divergence" (not Banker indicator)
- "Volatility Expansion Criteria" (not Beta >= 1.5)
- "Capital Preservation Protocol" (not 20% trailing stop)
- "Structural Trend Confirmation" (not Weekly BoS)
- "The 5th Gate: Forensic Audit" (not Gatekeeper)
- "Conviction Rating" (not Tier 1/2/3)
- "Sector Flow Analysis" (not Theme scoring)

US AUDIENCE CONTENT HOOKS:
1. BEAT SPY - Alpha over indexing, "Stop indexing. Start selecting."
2. ROTH IRA - Tax-free compounding, retirement account momentum
3. PDT-FRIENDLY - No $25k requirement, weekly timeframe, 15 min/week
4. POWER HOUR - 15:30-16:00 ET market reaction, relative strength
5. SECTOR ROTATION - Following institutional flows between themes

APPROVED POWER PHRASES:
- "Proprietary 5-gate screening system"
- "Filters 1,800 stocks to 3-5 actionable signals"
- "Institutional Accumulation Divergence detected"
- "Structural Pivot Confirmation triggered"
- "Forensic Audit cleared"
- "Capital Preservation Protocol activated"
- "The system protects capital so we live to fight another day"
- "No ego, just execution"

CRITICAL HONESTY + POSITIVITY RULES:
1. NEVER hide losses or only show winners - always include full P&L picture
2. NEVER exclude stopped-out trades from portfolio updates
3. When portfolio is down, frame constructively:
   - "Down 5% YTD but system working - cutting losers fast"
   - "SPY down 8%, we're down 5% = outperforming in tough conditions"
4. Frame losses as LEARNING/DISCIPLINE, not failures:
   - "Stop hit = Capital Preservation Protocol working as designed"
   - "No ego, just execution. On to the next."
5. When mentioning portfolio, ALWAYS include SPY comparison when outperforming

CRITICAL: Every tweet MUST either:
- Link to Substack (sterlingsignals.substack.com)
- Ask an engaging question
- Highlight our 5-gate proprietary screening system

STRUCTURE:
- Hook in first line
- Key insight or data point
- CTA or question to drive engagement

Return tweets as a JSON array with this structure:
[
  {
    "category": "buy_signal|theme_hot|theme_cold|closed_trade|position_update|sell_signal|system_promo|market_insight|educational|engagement|beat_spy|roth_ira|pdt_friendly|power_hour|sector_rotation|funnel_graphic|post_mortem",
    "ticker": "AAPL" or null,
    "theme": "AI Infrastructure" or null,
    "text": "The actual tweet text under 280 chars"
  }
]
"""


def generate_tweets_for_category(
    client: anthropic.Anthropic,
    category: str,
    content: WeeklyContent,
    count: int = 3
) -> List[Dict]:
    """Generate tweets for a specific category using Claude."""

    # Build context based on category
    if category == "buy_signal":
        context = f"""
Generate {count} tweets about new BUY signals that passed ALL our gates.

PASS Signals this week (passed technical + thematic + gatekeeper + DD):
{json.dumps(content.pass_signals, indent=2)}

For each signal, highlight (use GENERIC language):
- The ticker with $TICKER format
- DD verdict (STRONG BUY / SPEC BUY)
- Key catalyst driving the trade
- Our multi-step proprietary screening process (1800 stocks → ~3 winners)
- Link to full analysis: sterlingsignals.substack.com

CRITICAL: Do NOT reveal specific indicator names or formulas.
Use: "proprietary signals", "smart money accumulation", "theme momentum confirmed"

Example format:
"🎯 $IESC passes our proprietary 5-gate system

✅ Technical entry signal confirmed
✅ Smart money accumulation detected
✅ Hot theme momentum
✅ Deep due diligence: STRONG BUY

Full analysis in this week's newsletter 👇
sterlingsignals.substack.com"
"""

    elif category == "theme_hot":
        context = f"""
Generate {count} tweets about HOT themes (PRIME and INVESTABLE).

PRIME Themes (highest conviction):
{json.dumps(content.prime_themes, indent=2)}

INVESTABLE Themes:
{json.dumps(content.investable_themes, indent=2)}

For each tweet (use language about following money/institutions):
- Explain WHY the theme is hot NOW (specific catalyst)
- Mention institutional/smart money flows
- Frame as bottleneck plays or contrarian opportunities
- Connect to our scanner identifying these opportunities
- Link to newsletter for stock picks: sterlingsignals.substack.com

CRITICAL: Focus on "following the money", "institutional flows", "bottleneck themes"

Example format:
"🔥 AI Cooling is THIS week's hottest theme

Why? Hyperscalers spending $100B+ on data centers
Institutional money piling into bottleneck plays

Our proprietary system flagged this theme early 👇
sterlingsignals.substack.com"

"💰 Following institutional flows into Power Grid

Smart money knows: AI needs power
Grid infrastructure = bottleneck play of the decade

Where we're positioned 👇
sterlingsignals.substack.com"
"""

    elif category == "theme_cold":
        context = f"""
Generate {count} tweets about themes to AVOID or be SELECTIVE with.

SELECTIVE Themes (mixed signals):
{json.dumps(content.selective_themes, indent=2)}

AVOID Themes (stay away):
{json.dumps(content.avoid_themes, indent=2)}

Frame these as (contrarian/patience angle):
- Risk warnings for crowded trades (institutions exiting)
- Themes losing momentum (smart money rotating out)
- Our system helping avoid these traps
- Patience > FOMO - wait for better setups

CRITICAL: Focus on "crowded trades", "smart money exiting", "patience over FOMO"

Example format:
"❄️ Quantum Computing is cooling off

Why we're avoiding:
- Crowded trade - everyone's in
- Smart money rotating out
- No near-term catalysts

Patience > FOMO. Our system keeps us out of traps.

What themes are you avoiding? 👇"

"🚫 When everyone's bullish, be cautious

Crowded themes = smart money exits first
Retail holds the bag

Our contrarian signals help us avoid these traps

Current themes to avoid 👇
sterlingsignals.substack.com"
"""

    elif category == "closed_trade":
        context = f"""
Generate {count} tweets about CLOSED trades (wins and losses).

Recently Closed Trades:
{json.dumps(content.closed_trades, indent=2)}

CRITICAL: Generate tweets for BOTH wins AND losses. Do not skip losses.

For each (use GENERIC language - no specific percentages for stops):
- Be TRANSPARENT about P&L (wins AND losses)
- Explain WHY we exited (risk management triggered, took profits, thesis changed)
- Show disciplined risk management in action
- Link to track record: sterlingsignals.substack.com

FRAMING LOSSES POSITIVELY (without hiding them):
- Stop hit = "System worked. Cut the loss before it got worse."
- Multiple losses = "2 losses this month, both contained. That's disciplined risk management."
- Big loss = "Painful but manageable. This is why position sizing matters."
- Loss after gain = "Gave back some profits but protected the core. On to the next."

CRITICAL: Do NOT mention specific stop percentages or indicator names.

Example formats:

WIN: "✅ $RCAT closed for +42%

Entry: $8.50 → Exit: $12.08

What worked:
• Drone theme stayed hot
• Earnings beat expectations
• Disciplined exit preserved gains

Full trade breakdown 👇
sterlingsignals.substack.com"

LOSS: "🔴 $SMCI stopped out at -18%

No system wins 100%. Here's what happened:
• Thesis changed (accounting concerns)
• Risk management triggered
• Loss capped. Capital preserved.

This is exactly why we have rules.

Full breakdown 👇
sterlingsignals.substack.com"

YTD SUMMARY: "📊 2026 track record update:

Closed trades: 12
Winners: 8 (67% win rate)
Losers: 4

Avg win: +28%
Avg loss: -17%

Expectancy: Positive.

Every trade documented 👇
sterlingsignals.substack.com"
"""

    elif category == "position_update":
        context = f"""
Generate {count} tweets about current open positions.

Open Positions:
{json.dumps(content.open_positions, indent=2)}

Portfolio Summary:
- Total positions: {len(content.open_positions)}
- Recent stops hit: {len([t for t in content.closed_trades if t.get('exit_reason') == 'STOPPED'])} (if any)
- Unrealized P&L: (calculate from positions)

CRITICAL RULES FOR POSITION UPDATES (use GENERIC language):
1. ALWAYS show the FULL portfolio picture, not just winners
2. If any positions are red, INCLUDE them - don't hide losses
3. If overall portfolio is down, frame constructively:
   - "Down but managing risk - exits in place"
   - "Drawdown expected in momentum trading - system handles it"
4. If recently stopped out, MENTION it as discipline:
   - "2 exits triggered last week, but that's disciplined risk management"
5. Include total unrealized P&L, not cherry-picked winners

CRITICAL: Do NOT mention specific stop percentages or indicator names.
Use: "risk management", "disciplined exits", "following smart money", "theme momentum"

Example formats:

MIXED PORTFOLIO:
"📊 Portfolio check: 8 positions

🟢 Winners: VNET +12%, WCC +8%, INOD +5%
🔴 Laggards: APLD -3% (monitoring closely)

Net unrealized: +4.2%

1 exit triggered last week ($SMCI -18%)
System working. Discipline > ego.

Full breakdown 👇
sterlingsignals.substack.com"

UNDERWATER PORTFOLIO:
"📉 Tough week: Portfolio -3.2% unrealized

But here's the thing:
• All risk management intact
• SPY down 4.5% (we're outperforming)
• 2 positions showing strength

Drawdowns happen. Disciplined exits keep us in the game.

How we're positioned 👇
sterlingsignals.substack.com"
"""

    elif category == "sell_signal":
        context = f"""
Generate {count} tweets about SELL signals or caution flags.

Sell Signals:
{json.dumps(content.sell_signals, indent=2)}

Caution Signals:
{json.dumps(content.caution_signals, indent=2)}

Frame as (use GENERIC language):
- Risk management in action
- Technical signals showing weakness
- Protecting gains / cutting losses
- Our system identifying risks early

CRITICAL: Do NOT mention specific indicators like "BoS" or specific stop percentages.
Use phrases like "technical warning signals", "momentum fading", "risk management triggered"

Example format:
"⚠️ $VNET flashing CAUTION

Our proprietary signals showing weakness:
• Technical momentum fading
• Tightening risk management

Our system catches these early

What's your exit strategy? 👇"
"""

    elif category == "system_promo":
        context = f"""
Generate {count} tweets promoting our proprietary scanning system.

KEY SELLING POINTS (use generic language):
1. Multi-step proprietary screening (1800 stocks → 3-5 winners)
2. Smart money / institutional flow tracking
3. Theme momentum identification (hot vs cold themes)
4. Technical entry and exit signals
5. Rigorous due diligence on every signal
6. Disciplined risk management

CRITICAL: DO NOT reveal specific formulas, indicator names, or parameters.
Create mystery and intrigue. Use phrases like:
- "proprietary indicators"
- "smart money accumulation signals"
- "institutional flow tracking"
- "systematic approach"

ALWAYS link to newsletter: sterlingsignals.substack.com

Example formats:
"🔬 How we filter 1,800 stocks to 3 STRONG BUYs:

Step 1: Technical breakout confirmed ✅
Step 2: Smart money accumulation ✅
Step 3: Theme momentum aligned ✅
Step 4: Quality gate passed ✅
Step 5: Deep due diligence ✅

99% of stocks fail our screening.

See what passed this week 👇
sterlingsignals.substack.com"

"📊 Following the smart money

Our proprietary indicators track institutional accumulation.

When big money flows in, we pay attention.

This week: 3 stocks showing heavy accumulation

Free analysis 👇
sterlingsignals.substack.com"
"""

    elif category == "market_insight":
        context = f"""
Generate {count} tweets about market outlook for the week.

Current hot themes: {[t.get('name') for t in content.prime_themes + content.investable_themes]}
Current positions: {[p.get('ticker') for p in content.open_positions]}

Topics:
- Week ahead preview
- Sector rotation observations
- Macro factors affecting momentum stocks
- Link to full analysis: sterlingsignals.substack.com

Example format:
"📅 Week ahead: What momentum traders need to watch

🔹 NVDA earnings Wednesday
🔹 Fed minutes Thursday
🔹 PCE data Friday

Our scanner is positioned in Power Grid & AI Cooling

Full week preview 👇
sterlingsignals.substack.com"
"""

    elif category == "educational":
        context = f"""
Generate {count} educational tweets about momentum trading.

Topics to cover (use GENERIC language, no specific formulas):
- Identifying breakouts using technical signals
- Theme investing approach (follow institutional flows)
- Disciplined risk management (protect capital)
- Why patience beats FOMO
- Position sizing principles
- Following smart money into hot themes
- Avoiding crowded/cold themes

CRITICAL: Do NOT reveal specific indicators, percentages, or formulas.
Use phrases like "proprietary signals", "disciplined exits", "systematic approach"

ALWAYS tie back to our system and newsletter.

Example formats:
"📚 Why we use WEEKLY charts

Daily = too much noise
Monthly = too slow

Weekly timeframes:
→ Catch major trend changes
→ Filter out fake breakouts
→ Perfect for swing trades

Our proprietary system uses this 👇
sterlingsignals.substack.com"

"💡 Disciplined risk management

The difference between pros and amateurs:

✅ Predetermined exit strategy
✅ Never move stops down
✅ Cut losers fast, let winners run

Simple rules. Saves accounts.

How we manage risk 👇
sterlingsignals.substack.com"

"🎯 Theme investing = following the money

Smart money rotates into hot themes
Retail chases after the move

Our system identifies theme momentum BEFORE the crowd

Current hot theme analysis 👇
sterlingsignals.substack.com"
"""

    elif category == "engagement":
        context = f"""
Generate {count} engagement tweets (questions, polls, discussions).

Examples:
- "What sectors are you watching this week?"
- "How do you handle positions at all-time highs?"
- "Biggest lesson from your last losing trade?"
- "Do you have a systematic exit strategy?"
- "What themes are you following right now?"
- "Patience or FOMO - which wins more often?"

CRITICAL: Do NOT mention specific percentages, indicator names, or formula details.
Keep it generic and engaging.

STILL mention Sterling Signals or link where natural.

Example format:
"🤔 Quick poll for traders:

Your position is up 30%. Do you:

A) Take profits
B) Trail your stop
C) Add to winner
D) Let it ride

Reply with your strategy 👇

How we handle this at sterlingsignals.substack.com"

"💭 What's your edge in this market?

Theme momentum?
Technical signals?
Fundamental analysis?
All of the above?

Our edge: systematic multi-step screening

What's yours? 👇"
"""

    elif category == "beat_spy":
        context = f"""
Generate {count} tweets comparing our performance to SPY/QQQ for US active investors.

Open positions: {json.dumps(content.open_positions[:3], indent=2) if content.open_positions else "None"}
Hot themes: {[t.get('name') for t in content.prime_themes]}

TEMPLATES:
"SPY is chopping sideways.
Meanwhile, the system found 3 sectors breaking out with institutional backing.
Stop indexing. Start selecting.
sterlingsignals.substack.com"

"QQQ down 2% this week. Our portfolio: +4.2%
The difference? We follow smart money into specific themes, not broad exposure.
This week's breakdown:
sterlingsignals.substack.com"

"Most portfolios mirror the S&P 500.
Ours hunts the 3-5 stocks each week that institutions are quietly accumulating BEFORE the breakout.
That's alpha. That's the system.
sterlingsignals.substack.com"

RULES:
- Reference SPY/QQQ comparison when outperforming
- Be factual, not arrogant
- Focus on stock selection vs passive indexing
- ALWAYS link to newsletter
"""

    elif category == "roth_ira":
        context = f"""
Generate {count} tweets for Roth IRA / tax-advantaged account investors.

Hot themes: {[t.get('name') for t in content.prime_themes]}

TEMPLATES:
"The Roth IRA hack nobody talks about:
Instead of holding SPY forever, rotate into momentum winners.
Tax-free compounding on 30-50% swing trades > 10% annual index returns.
The system identifies these setups weekly.
sterlingsignals.substack.com"

"Your Roth doesn't have to be boring index funds.
Systematic momentum + tax-free compounding = retirement account on steroids.
This week's themes: {content.prime_themes[0].get('name') if content.prime_themes else 'Power Grid'}
sterlingsignals.substack.com"

"Perfect Roth setup:
Institutional Accumulation Divergence detected.
Sector Flow Analysis aligned.
Structural Pivot confirmed.
Tax-free gains if this runs.
sterlingsignals.substack.com"

RULES:
- Focus on tax-free compounding angle
- Mention systematic approach
- Use APPROVED vocabulary only
- Never financial advice
"""

    elif category == "pdt_friendly":
        context = f"""
Generate {count} tweets about PDT-friendly swing trading (no $25k requirement).

TEMPLATES:
"No PDT worries here.
We trade weekly signals. Buy Monday, set stops, check Friday.
Pure swing trading. No 9:30 AM stress.
sterlingsignals.substack.com"

"Day trading requires:
- $25k minimum (PDT rule)
- All-day screen time
- Split-second decisions

This system requires:
- Any account size
- 15 minutes/week
- Patience

Which sounds sustainable?
sterlingsignals.substack.com"

"The weekly timeframe advantage:
✓ No PDT restrictions
✓ No all-day monitoring
✓ Clear entry/exit signals
✓ Works with any schedule

How we trade without the $25k requirement:
sterlingsignals.substack.com"

RULES:
- Emphasize weekly timeframe = no PDT issues
- Focus on minimal time commitment
- Appeal to busy professionals
"""

    elif category == "power_hour":
        context = f"""
Generate {count} Power Hour reaction tweets (15:30-16:00 ET market hours).

Open positions: {json.dumps(content.open_positions[:3], indent=2) if content.open_positions else "None"}
Hot themes: {[t.get('name') for t in content.prime_themes]}

TEMPLATE:
"Power Hour Check:
[THEME_NAME] seeing [HIGH/MODERATE/LOW] volume into the close.
Our pick $[TICKER] currently [UP/DOWN] [PERCENT]%.
[Brief observation about relative strength vs market]
Watching for structural confirmation on the weekly close.
sterlingsignals.substack.com"

RULES:
- Post during 15:30-16:00 ET window (Power Hour)
- Reference relative strength vs market
- Keep observational, not promotional
- Mention "structural confirmation" language
"""

    elif category == "sector_rotation":
        context = f"""
Generate {count} tweets about sector rotation and institutional flow shifts.

Hot themes: {[t.get('name') for t in content.prime_themes]}
Cold themes: {[t.get('name') for t in content.avoid_themes]}

TEMPLATES:
"Money is rotating.
Out of: [COLD_THEME]
Into: [HOT_THEME]
The system detected this shift 2 weeks ago. Our [THEME] picks are up.
Don't fight the flow.
sterlingsignals.substack.com"

"Sector rotation in real-time:
[THEME_1]: 🔥 Institutional accumulation surging
[THEME_2]: 📈 Structural breakouts confirmed
[THEME_3]: ❄️ Smart money exiting
The system follows the flow. This week's picks:
sterlingsignals.substack.com"

RULES:
- Reference specific theme rotation
- Use "institutional flows" language
- Mention Sector Flow Analysis
"""

    elif category == "funnel_graphic":
        context = f"""
Generate {count} tweets about our weekly filtering funnel.

Scan stats (use these numbers):
- Total scanned: 1,817
- Passed Volatility Expansion: ~485
- Showed Institutional Accumulation: ~48
- Theme aligned: ~17
- Forensic Audit PASS: {len(content.pass_signals) if content.pass_signals else 6}

TEMPLATE:
"This week's scan:
📊 1,817 stocks analyzed
📉 485 passed Volatility Expansion Criteria
🔍 48 showed Institutional Accumulation
🎯 17 aligned with hot themes
✅ {len(content.pass_signals) if content.pass_signals else 6} cleared the Forensic Audit

{len(content.pass_signals) if content.pass_signals else 6} actionable signals. Full breakdown in the newsletter.
sterlingsignals.substack.com"

RULES:
- Use APPROVED vocabulary (not HMA, Banker, BoS, etc.)
- Show the funnel progression with specific numbers
- End with newsletter CTA
- High viral potential - show the work done
"""

    elif category == "post_mortem":
        stopped_trades = [t for t in content.closed_trades if t.get('status') == 'STOPPED'] if content.closed_trades else []
        context = f"""
Generate Post-Mortem Card tweets for stopped-out positions.

Stopped trades: {json.dumps(stopped_trades, indent=2) if stopped_trades else "None this week"}

TEMPLATE (Post-Mortem Card format):
"❌ $[TICKER] — Stopped Out

Entry: $[ENTRY_PRICE]
Exit: $[EXIT_PRICE]
Loss: -[LOSS_PERCENT]%

The system protects capital so we live to fight another day.
No ego, just execution.

[Optional 1-sentence lesson]
sterlingsignals.substack.com"

RULES:
- Post IMMEDIATELY when stop hits
- Never delete losing trade posts
- Frame positively (Capital Preservation Protocol working)
- Optional brief lesson learned
- NEVER mention "20%" stop level
- Use "Capital Preservation Protocol" not "trailing stop"
"""

    else:
        context = f"Generate {count} general financial content tweets. Always link to sterlingsignals.substack.com. Use APPROVED vocabulary - never mention HMA, Banker, BoS, 20% stop, Tier 1/2/3, or UK ISA."

    # Call Claude
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=TWEET_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": context}
            ]
        )

        # Extract JSON from response
        response_text = response.content[0].text

        # Try to parse JSON (handle markdown code blocks)
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            tweets = json.loads(json_match.group())
            return tweets
        else:
            print(f"  ⚠ Could not parse JSON for {category}")
            return []

    except Exception as e:
        print(f"  ✗ Error generating {category} tweets: {e}")
        return []


def generate_all_tweets(content: WeeklyContent, mock: bool = False) -> List[Tweet]:
    """Generate all 21 tweets for the week."""

    if mock:
        return generate_mock_tweets()

    # Initialize Claude client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    all_tweets = []

    # Category distribution across the week - US AUDIENCE FOCUS
    # 35 total = 5 per day × 7 days (X API allows ~50/day)
    # Schedule aligned to Eastern Time (ET)
    # Slot 1 = 08:00 ET (Pre-market), Slot 4 = 15:30 ET (Power Hour) are CRITICAL
    stopped_trades = [t for t in content.closed_trades if t.get('status') == 'STOPPED'] if content.closed_trades else []

    categories_schedule = [
        # Monday: Week kickoff - US focus with alpha hooks
        ("Monday", 1, "beat_spy"),             # 08:00 ET - Alpha hook (pre-market)
        ("Monday", 2, "theme_hot"),            # 10:00 ET - Theme momentum
        ("Monday", 3, "position_update"),      # 12:30 ET - Portfolio check
        ("Monday", 4, "power_hour"),           # 15:30 ET - Power Hour reaction (CRITICAL)
        ("Monday", 5, "market_insight"),       # 18:00 ET - Week ahead

        # Tuesday: Position updates + tax angle
        ("Tuesday", 1, "roth_ira"),            # 08:00 ET - Tax-advantaged angle
        ("Tuesday", 2, "position_update"),     # 10:00 ET - Portfolio Pulse day
        ("Tuesday", 3, "buy_signal" if content.pass_signals else "theme_hot"),
        ("Tuesday", 4, "power_hour"),          # 15:30 ET - Power Hour
        ("Tuesday", 5, "educational"),         # 18:00 ET - Trading lesson

        # Wednesday: Educational + PDT-friendly
        ("Wednesday", 1, "pdt_friendly"),      # 08:00 ET - PDT-free swing trading
        ("Wednesday", 2, "thread_educational"),# 10:00 ET - 🧵 Educational thread (5 tweets)
        ("Wednesday", 3, "theme_hot"),         # 12:30 ET - Theme spotlight
        ("Wednesday", 4, "power_hour"),        # 15:30 ET - Power Hour
        ("Wednesday", 5, "engagement"),        # 18:00 ET - Community Q&A

        # Thursday: Trade spotlight + sector rotation
        ("Thursday", 1, "beat_spy"),           # 08:00 ET - Alpha comparison
        ("Thursday", 2, "buy_signal" if content.pass_signals else "position_update"),
        ("Thursday", 3, "sector_rotation"),    # 12:30 ET - Sector flows
        ("Thursday", 4, "power_hour"),         # 15:30 ET - Power Hour
        ("Thursday", 5, "educational"),        # 18:00 ET - Risk management

        # Friday: Scanner tease + Funnel graphic
        ("Friday", 1, "roth_ira"),             # 08:00 ET - Tax angle
        ("Friday", 2, "funnel_graphic"),       # 10:00 ET - Weekly funnel visual
        ("Friday", 3, "system_promo"),         # 12:30 ET - Newsletter teaser
        ("Friday", 4, "power_hour"),           # 15:30 ET - Power Hour
        ("Friday", 5, "market_insight"),       # 18:00 ET - Week recap

        # Saturday: Newsletter day - ONE buy signal max (prevents portfolio bloat)
        ("Saturday", 1, "buy_signal" if content.pass_signals else "funnel_graphic"),  # 08:00 ET - THE weekly pick
        ("Saturday", 2, "thread_buy_signal"),  # 10:00 ET - 🧵 Deep dive on signal (5 tweets)
        ("Saturday", 3, "funnel_graphic"),     # 12:30 ET - Funnel stats
        ("Saturday", 4, "position_update" if content.open_positions else "educational"),  # 15:30 ET - Portfolio status
        ("Saturday", 5, "engagement"),         # 18:00 ET - Discussion

        # Sunday: Reinforce THE signal before Monday entry
        ("Sunday", 1, "buy_signal" if content.pass_signals else "market_insight"),  # 08:00 ET - Reinforce the pick
        ("Sunday", 2, "sector_rotation"),      # 10:00 ET - Sector flow preview
        ("Sunday", 3, "thread_week_ahead"),    # 12:30 ET - 🧵 Week ahead preview (5 tweets)
        ("Sunday", 4, "theme_hot"),            # 15:30 ET - Hot theme for week
        ("Sunday", 5, "engagement"),           # 18:00 ET - Week kickoff poll
    ]

    # Group by category to batch API calls (separate threads from regular tweets)
    categories_needed = {}
    thread_categories = []
    for day, slot, category in categories_schedule:
        if category.startswith('thread_'):
            thread_categories.append((day, slot, category))
        else:
            if category not in categories_needed:
                categories_needed[category] = []
            categories_needed[category].append((day, slot))

    # Generate regular tweets by category
    print("\n  🤖 Generating tweets via Claude API...")

    generated_by_category = {}
    for category, slots in categories_needed.items():
        print(f"    • {category}: {len(slots)} tweets...")
        tweets = generate_tweets_for_category(client, category, content, count=len(slots))
        generated_by_category[category] = tweets

    # Generate threads
    if thread_categories:
        print(f"\n  🧵 Generating {len(thread_categories)} thread(s)...")
        for day, slot, category in thread_categories:
            print(f"    • {category} for {day} slot {slot}...")
            # Threads are generated individually during assignment (below)

    # Assign tweets to schedule
    category_index = {cat: 0 for cat in categories_needed}

    # Calculate dates for the week
    # When run on Friday (after scan), schedule tweets starting Saturday
    # When run on other days, schedule starting from next Saturday
    today = datetime.now()
    current_weekday = today.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    if current_weekday == 4:  # Friday - start from tomorrow (Saturday)
        days_until_saturday = 1
    elif current_weekday == 5:  # Saturday - start from today
        days_until_saturday = 0
    elif current_weekday == 6:  # Sunday - start from yesterday (use current week)
        days_until_saturday = -1
    else:  # Mon-Thu - start from this coming Saturday
        days_until_saturday = 5 - current_weekday

    # start_date is Saturday - calculate offsets from Saturday
    # Saturday=0, Sunday=1, Monday=2, Tuesday=3, Wednesday=4, Thursday=5, Friday=6
    start_date = today + timedelta(days=days_until_saturday)

    # Map day names to offsets from Saturday
    day_offset_from_saturday = {
        "Saturday": 0,
        "Sunday": 1,
        "Monday": 2,
        "Tuesday": 3,
        "Wednesday": 4,
        "Thursday": 5,
        "Friday": 6
    }

    # Track threads separately (they're dict format, not Tweet objects)
    all_content = []  # Will contain both Tweet objects and thread dicts

    for day, slot, category in categories_schedule:
        day_offset = day_offset_from_saturday[day]
        scheduled_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        # Handle threads separately from regular tweets
        if category.startswith('thread_'):
            # Generate thread for this slot
            thread_data = generate_thread_for_schedule(client, category, content, mock=mock)
            thread_data.update({
                'id': f"{day.lower()}_{slot}_{category}",
                'day': day,
                'slot': slot,
                'category': category,
                'scheduled_date': scheduled_date,
                'status': 'pending',
                'posted_at': None,
                'tweet_id': None,
            })
            all_content.append(thread_data)
            continue

        # Regular tweet handling
        idx = category_index.get(category, 0)
        tweets_for_cat = generated_by_category.get(category, [])

        if idx < len(tweets_for_cat):
            tweet_data = tweets_for_cat[idx]
            category_index[category] = idx + 1
        else:
            # Fallback if not enough tweets generated
            tweet_data = {
                "category": category,
                "text": f"[Placeholder: {category} tweet for {day} {SLOTS[slot]}]",
                "ticker": None,
                "theme": None
            }

        # Find chart path if ticker present
        image_path = None
        ticker = tweet_data.get("ticker")
        if ticker and ticker in content.chart_manifest:
            image_path = content.chart_manifest[ticker]

        tweet = Tweet(
            id=f"{day.lower()}_{slot}_{category}",
            day=day,
            slot=slot,
            category=tweet_data.get("category", category),
            text=tweet_data.get("text", ""),
            ticker=ticker,
            theme=tweet_data.get("theme"),
            image_path=image_path,
            scheduled_date=scheduled_date
        )

        all_tweets.append(tweet)
        all_content.append(tweet)

    # Validate tweets for banned terms
    if MARKETING_VOCABULARY_AVAILABLE:
        print("\n  🔍 Validating content for banned terms...")
        total, violations = validate_all_tweets(all_tweets)
        if violations > 0:
            print(f"  ⚠ {violations}/{total} tweets contain banned terms (review recommended)")
        else:
            print(f"  ✓ All {total} tweets passed vocabulary validation")

        # Also validate thread content
        thread_count = len([c for c in all_content if isinstance(c, dict) and c.get('is_thread')])
        if thread_count > 0:
            print(f"  🧵 {thread_count} thread(s) generated (validate manually if needed)")

    # Return all_content which includes both Tweet objects and thread dicts
    # The save function needs to handle both types
    return all_content


def generate_mock_tweets() -> List[Tweet]:
    """Generate mock tweets for testing without API calls."""
    tweets = []

    # Same logic as generate_all_tweets - start from Saturday
    today = datetime.now()
    current_weekday = today.weekday()

    if current_weekday == 4:  # Friday
        days_until_saturday = 1
    elif current_weekday == 5:  # Saturday
        days_until_saturday = 0
    elif current_weekday == 6:  # Sunday
        days_until_saturday = -1
    else:  # Mon-Thu
        days_until_saturday = 5 - current_weekday

    start_date = today + timedelta(days=days_until_saturday)

    # Day offsets from Saturday
    day_offset_from_saturday = {
        "Saturday": 0, "Sunday": 1, "Monday": 2, "Tuesday": 3,
        "Wednesday": 4, "Thursday": 5, "Friday": 6
    }

    # Thread slots (matching the real schedule)
    thread_slots = {
        ('Saturday', 2): 'thread_buy_signal',
        ('Wednesday', 2): 'thread_educational',
        ('Sunday', 3): 'thread_week_ahead',
    }

    all_content = []

    for day in DAYS:
        day_offset = day_offset_from_saturday[day]
        scheduled_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for slot in [1, 2, 3]:
            # Check if this slot should be a thread
            if (day, slot) in thread_slots:
                category = thread_slots[(day, slot)]
                thread_data = {
                    'id': f"{day.lower()}_{slot}_{category}",
                    'day': day,
                    'slot': slot,
                    'category': category,
                    'is_thread': True,
                    'thread_topic': f"Mock {category.replace('thread_', '').replace('_', ' ').title()}",
                    'thread_tweets': [
                        {'number': 1, 'text': f"🧵 1/5: [MOCK] {category} hook tweet", 'tweet_id': None},
                        {'number': 2, 'text': f"2/5: [MOCK] Problem statement", 'tweet_id': None},
                        {'number': 3, 'text': f"3/5: [MOCK] Our solution", 'tweet_id': None},
                        {'number': 4, 'text': f"4/5: [MOCK] Proof/example", 'tweet_id': None},
                        {'number': 5, 'text': f"5/5: [MOCK] CTA to sterlingsignals.substack.com", 'tweet_id': None},
                    ],
                    'thread_status': 'pending',
                    'scheduled_date': scheduled_date,
                    'status': 'pending',
                    'posted_at': None,
                    'tweet_id': None,
                    'ticker': None,
                    'theme': None,
                }
                all_content.append(thread_data)
            else:
                # Regular mock tweet
                tweet = Tweet(
                    id=f"{day.lower()}_{slot}_mock",
                    day=day,
                    slot=slot,
                    category="mock",
                    text=f"[MOCK] {day} {SLOTS[slot]} tweet placeholder",
                    scheduled_date=scheduled_date
                )
                tweets.append(tweet)
                all_content.append(tweet)

    return all_content


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_briefing_data(briefing_path: Path) -> WeeklyContent:
    """Load data from newsletter briefing markdown."""
    content = WeeklyContent()

    if not briefing_path.exists():
        print(f"  ⚠ Briefing not found: {briefing_path}")
        return content

    # Import the parsing function from grok_prompts_generator if available
    try:
        from grok_prompts_generator import parse_briefing_markdown
        data = parse_briefing_markdown(briefing_path)

        content.pass_signals = data.pass_signals
        content.caution_signals = data.caution_signals
        content.sell_signals = data.sell_signals
        content.open_positions = data.open_positions
        content.prime_themes = data.prime_themes
        content.investable_themes = data.investable_themes
        content.selective_themes = data.selective_themes
        content.avoid_themes = data.avoid_themes
        content.scan_date = data.scan_date

    except ImportError:
        print("  ⚠ Could not import grok_prompts_generator, using basic parsing")
        # Basic fallback parsing could go here

    # Load positions with LIVE P&L from PortfolioManager (authoritative source)
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if portfolio_file.exists():
        import csv
        open_positions_from_csv = []

        # Try to use PortfolioManager for live prices
        try:
            from portfolio_manager import PortfolioManager
            pm = PortfolioManager()
            pm.update_prices()  # Fetch live prices via yfinance

            for trade in pm.get_open_positions():
                open_positions_from_csv.append({
                    'ticker': trade.ticker,
                    'entry_date': trade.entry_date,
                    'entry_price': trade.entry_price,
                    'current_price': trade.current_price,
                    'pnl_pct': trade.pnl_pct,
                    'highest_close': trade.highest_close,
                    'stop_level': trade.stop_level,
                    'distance_to_stop': trade.distance_to_stop_pct,
                    'days_held': trade.days_held,
                    'theme': trade.theme,
                    'tier': trade.tier,
                    'conviction': trade.conviction,
                    'stop_alert': trade.stop_alert,
                })

            for trade in pm.get_closed_trades():
                content.closed_trades.append({
                    'ticker': trade.ticker,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'exit_date': trade.exit_date,
                    'status': trade.status,
                    'pnl_pct': trade.pnl_pct,
                    'theme': trade.theme
                })

            print(f"  📊 Loaded {len(open_positions_from_csv)} positions with LIVE prices")

        except (ImportError, Exception) as e:
            print(f"  ⚠ PortfolioManager unavailable ({e}), using basic CSV loading")
            # Fallback to basic CSV loading without live prices
            with open(portfolio_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get('status', 'OPEN').upper()
                    if status == 'OPEN':
                        try:
                            entry_price = float(row.get('entry_price', 0) or 0)
                        except (ValueError, TypeError):
                            entry_price = 0
                        open_positions_from_csv.append({
                            'ticker': row.get('ticker', ''),
                            'entry_date': row.get('entry_date', ''),
                            'entry_price': entry_price,
                            'theme': row.get('theme', ''),
                            'tier': row.get('tier', ''),
                            'conviction': row.get('conviction', ''),
                            'highest_close': row.get('highest_close', ''),
                        })
                    elif status in ['CLOSED', 'STOPPED']:
                        try:
                            entry = float(row.get('entry_price', 0))
                            exit_price = float(row.get('exit_price', 0))
                            pnl = ((exit_price / entry) - 1) * 100 if entry > 0 else 0
                        except (ValueError, ZeroDivisionError):
                            pnl = 0

                        content.closed_trades.append({
                            'ticker': row['ticker'],
                            'entry_price': row.get('entry_price'),
                            'exit_price': row.get('exit_price'),
                            'exit_date': row.get('exit_date'),
                            'status': status,
                            'pnl_pct': pnl,
                            'theme': row.get('theme')
                        })

        # Use CSV positions if markdown parsing found none (more reliable)
        if not content.open_positions and open_positions_from_csv:
            print(f"  📊 Loaded {len(open_positions_from_csv)} open positions from portfolio.csv")
            content.open_positions = open_positions_from_csv

        # CRITICAL: Filter out PASS signals that were in portfolio BEFORE this scan
        # Signals added on the same day as the scan are NEW and should be tweeted
        # Only filter signals where entry_date < scan_date (previous weeks' positions)
        scan_date = content.scan_date or datetime.now().strftime("%Y-%m-%d")

        # Build set of tickers that were in portfolio BEFORE this scan
        pre_existing_tickers = set()
        for pos in open_positions_from_csv:
            ticker = pos.get('ticker', '').upper()
            entry_date = pos.get('entry_date', '')

            # Normalize entry_date to YYYY-MM-DD format for comparison
            if entry_date:
                # Handle various date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        parsed_date = datetime.strptime(entry_date, fmt)
                        entry_date_normalized = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                else:
                    entry_date_normalized = entry_date  # Use as-is if parsing fails

                # If entry_date is BEFORE scan_date, it's a pre-existing position
                if entry_date_normalized < scan_date:
                    pre_existing_tickers.add(ticker)
                else:
                    # This is a NEW signal from this week's scan - don't filter it
                    print(f"  ✨ {ticker} is a NEW signal (entry: {entry_date_normalized}, scan: {scan_date})")

        original_pass_count = len(content.pass_signals)
        content.pass_signals = [
            sig for sig in content.pass_signals
            if sig.get('ticker', '').upper() not in pre_existing_tickers
        ]
        if original_pass_count != len(content.pass_signals):
            removed = original_pass_count - len(content.pass_signals)
            filtered_tickers = [sig.get('ticker') for sig in content.pass_signals if sig.get('ticker', '').upper() in pre_existing_tickers]
            print(f"  🔄 Filtered {removed} PASS signal(s) already in portfolio from previous weeks")

        # LIMIT: Only keep the highest conviction signal (max 1 per week)
        # This prevents portfolio bloat - we add max 1 new position per week
        if len(content.pass_signals) > 1:
            # Sort by conviction (descending), then by theme score if available
            content.pass_signals.sort(
                key=lambda x: (
                    int(x.get('conviction', 0)) if isinstance(x.get('conviction'), (int, str)) and str(x.get('conviction', '')).isdigit() else 0,
                    float(x.get('theme_score', 0)) if x.get('theme_score') else 0
                ),
                reverse=True
            )
            top_signal = content.pass_signals[0]
            print(f"  🎯 LIMITED to 1 buy signal: {top_signal.get('ticker')} (conviction: {top_signal.get('conviction', 'N/A')})")
            print(f"     Skipped: {', '.join(s.get('ticker', '?') for s in content.pass_signals[1:])}")
            content.pass_signals = [top_signal]

    # Load chart manifest
    manifest_path = CHARTS_DIR / "chart_manifest.json"
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            content.chart_manifest = manifest.get("charts", {})

    return content


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_tweets(content: List, output_dir: Path) -> Path:
    """Save tweets and threads to JSON files.

    Args:
        content: List of Tweet objects and/or thread dicts
        output_dir: Directory to save files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    # Convert to JSON-serializable format
    # Handle both Tweet objects (need .to_dict()) and thread dicts (already dict)
    serialized = []
    for item in content:
        if isinstance(item, Tweet):
            serialized.append(item.to_dict())
        elif isinstance(item, dict):
            # Thread dict - already serializable
            serialized.append(item)
        else:
            # Fallback
            serialized.append(item)

    # Sort by scheduled_date and slot to ensure proper posting order
    def sort_key(item):
        date = item.get('scheduled_date', '9999-99-99')
        slot = item.get('slot', 99)
        return (date, slot)

    serialized = sorted(serialized, key=sort_key)

    tweets_json = json.dumps(serialized, indent=2)

    # Save to current/ and weekly archive if available
    if OUTPUT_PATHS_AVAILABLE:
        current_dir, week_dir = ensure_output_structure()

        # Save to current/tweets/
        current_tweets = current_dir / "tweets"
        current_tweets.mkdir(exist_ok=True)
        with open(current_tweets / "content_queue.json", 'w') as f:
            f.write(tweets_json)
        with open(current_tweets / f"tweets_{date_str}.json", 'w') as f:
            f.write(tweets_json)

        # Save to weekly archive
        archive_tweets = week_dir / "tweets"
        archive_tweets.mkdir(exist_ok=True)
        with open(archive_tweets / "content_queue.json", 'w') as f:
            f.write(tweets_json)
        with open(archive_tweets / f"tweets_{date_str}.json", 'w') as f:
            f.write(tweets_json)

    # Full tweets file (legacy location)
    tweets_file = output_dir / f"tweets_{date_str}.json"
    with open(tweets_file, 'w') as f:
        f.write(tweets_json)

    # Content queue for twitter_poster.py (legacy location)
    queue_file = output_dir / "content_queue.json"
    with open(queue_file, 'w') as f:
        f.write(tweets_json)

    # Also save to trades root for easy access
    root_queue = TRADES_DIR / "content_queue.json"
    with open(root_queue, 'w') as f:
        f.write(tweets_json)

    return queue_file


def print_summary(content: List):
    """Print summary of generated content (tweets and threads)."""
    print("\n  📊 Content Summary:")
    print("  " + "─" * 50)

    # Count threads and tweets
    threads = [c for c in content if isinstance(c, dict) and c.get('is_thread')]
    tweets = [c for c in content if isinstance(c, Tweet)]

    print(f"\n  📝 Single tweets: {len(tweets)}")
    print(f"  🧵 Threads: {len(threads)} ({len(threads) * 5} thread tweets)")
    print(f"  📊 Total content pieces: {len(tweets) + len(threads)}")

    for day in DAYS:
        # Get items for this day (handle both Tweet objects and thread dicts)
        day_items = []
        for c in content:
            if isinstance(c, Tweet) and c.day == day:
                day_items.append(('tweet', c))
            elif isinstance(c, dict) and c.get('day') == day:
                day_items.append(('thread', c))

        if day_items:
            print(f"\n  📅 {day}:")
            for item_type, item in sorted(day_items, key=lambda x: x[1].slot if isinstance(x[1], Tweet) else x[1].get('slot', 0)):
                if item_type == 'tweet':
                    t = item
                    slot_name = SLOTS[t.slot]
                    ticker_str = f" ${t.ticker}" if t.ticker else ""
                    chart_str = " 📸" if t.image_path else ""
                    text_preview = t.text[:50] + "..." if len(t.text) > 50 else t.text
                    print(f"     {slot_name:8} [{t.category:15}]{ticker_str}{chart_str}")
                    print(f"              {text_preview}")
                else:
                    # Thread
                    t = item
                    slot_name = SLOTS[t.get('slot', 1)]
                    ticker_str = f" ${t.get('ticker')}" if t.get('ticker') else ""
                    topic = t.get('thread_topic', 'Thread')
                    print(f"     {slot_name:8} 🧵 [{t.get('category', 'thread'):15}]{ticker_str}")
                    print(f"              {topic} (5 tweets)")


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

THREAD_SYSTEM = """You are writing an educational X/Twitter thread for @SterlingSignals.

Your threads are:
- 5 tweets long (numbered 1/5, 2/5, etc.)
- Educational and value-driven
- Each tweet stands alone but builds a narrative
- Under 280 characters per tweet
- Uses line breaks for readability
- Ends with CTA to Substack

Topics you cover:
- Bottleneck investing (infrastructure, supply chain)
- Systematic stock selection methodology
- Theme momentum analysis
- Risk management principles
- Market psychology and discipline

STYLE:
- Confident but not arrogant
- Data-driven with specific examples
- Accessible to regular investors
- No jargon, no banned technical terms
"""

THREAD_PROMPT = """Generate a 5-tweet educational thread on this topic:

TOPIC: {topic}

CONTEXT:
{context}

REQUIREMENTS:
1. Each tweet numbered (1/5, 2/5, etc.)
2. Under 280 characters each
3. Tweet 1: Hook - provocative question or bold claim
4. Tweet 2: Problem - why most investors fail at this
5. Tweet 3: Insight - your systematic solution
6. Tweet 4: Proof - specific example or data point
7. Tweet 5: CTA - link to https://sterlingsignals.substack.com

Output as JSON array:
[
  {{"number": 1, "text": "..."}},
  {{"number": 2, "text": "..."}},
  ...
]
"""


@dataclass
class Thread:
    """Represents a multi-tweet thread."""
    id: str
    topic: str
    tweets: List[Dict]  # [{number: 1, text: "..."}, ...]
    generated_at: str = ""
    scheduled_date: str = ""


def generate_thread(
    topic: str,
    context: str = "",
    client: Optional[anthropic.Anthropic] = None
) -> Thread:
    """
    Generate a 5-tweet educational thread.

    Args:
        topic: Thread topic (e.g., "bottleneck investing", "systematic selection")
        context: Additional context for personalization
        client: Anthropic client (creates one if not provided)

    Returns:
        Thread object with 5 tweets
    """
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  ⚠️ ANTHROPIC_API_KEY not set")
            return Thread(
                id=f"thread_{datetime.now():%Y%m%d_%H%M%S}",
                topic=topic,
                tweets=[{"number": i, "text": f"[Thread {i}/5 placeholder]"} for i in range(1, 6)],
                generated_at=datetime.now().isoformat()
            )
        client = anthropic.Anthropic(api_key=api_key)

    prompt = THREAD_PROMPT.format(
        topic=topic,
        context=context or "General educational content for momentum investors."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=THREAD_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Parse JSON response
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            tweets = json.loads(json_match.group())
        else:
            tweets = [{"number": i, "text": f"[Parse error - tweet {i}]"} for i in range(1, 6)]

        # Validate each tweet
        if MARKETING_VOCABULARY_AVAILABLE:
            for tweet in tweets:
                is_valid, violations = validate_content(tweet.get('text', ''))
                if not is_valid:
                    print(f"  ⚠️ Thread tweet {tweet.get('number')} contains banned terms: {violations}")

        return Thread(
            id=f"thread_{datetime.now():%Y%m%d_%H%M%S}",
            topic=topic,
            tweets=tweets,
            generated_at=datetime.now().isoformat()
        )

    except Exception as e:
        print(f"  ⚠️ Thread generation error: {e}")
        return Thread(
            id=f"thread_{datetime.now():%Y%m%d_%H%M%S}",
            topic=topic,
            tweets=[{"number": i, "text": f"[Error: {e}]"} for i in range(1, 6)],
            generated_at=datetime.now().isoformat()
        )


def save_thread(thread: Thread, output_dir: Path = None) -> Path:
    """Save thread to JSON file."""
    if output_dir is None:
        output_dir = TWEETS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"thread_{datetime.now():%Y%m%d_%H%M%S}.json"
    output_path = output_dir / filename

    with open(output_path, 'w') as f:
        json.dump({
            'id': thread.id,
            'topic': thread.topic,
            'tweets': thread.tweets,
            'generated_at': thread.generated_at,
            'scheduled_date': thread.scheduled_date
        }, f, indent=2)

    print(f"  Thread saved: {output_path}")
    return output_path


THREAD_TOPICS = [
    {
        'topic': 'Bottleneck Investing',
        'context': 'Explain the concept of second-order investing: instead of buying the obvious trend (AI), buy what the trend NEEDS that is in shortage (power, cooling). Use current examples like data centers, grid infrastructure.'
    },
    {
        'topic': 'The 5-Gate System',
        'context': 'Explain systematic stock selection process without revealing specific gate mechanics. Focus on: starting with 1,800 stocks, filtering through volatility criteria, smart money signals, sector alignment, and final forensic review. Emphasize how filtering down to 3-5 weekly picks reduces noise and improves conviction. DO NOT mention specific indicator names or thresholds.'
    },
    {
        'topic': 'Systematic Risk Management',
        'context': 'Explain capital preservation protocols: predetermined exits, position sizing, never fighting the system. No ego, just execution. The stop hit = system working as designed.'
    },
    {
        'topic': 'Following Smart Money',
        'context': 'Explain how tracking institutional capital flows helps identify winning themes. Focus on sector rotation, following where big money is accumulating, and avoiding crowded retail trades. Use "institutional accumulation signals" and "smart money flows" language.'
    },
    {
        'topic': 'Beat the Index',
        'context': 'Explain why systematic momentum selection beats passive indexing: concentration in best setups, active sector rotation timing, disciplined risk management vs buy-and-hope. Reference SPY/QQQ underperformance in choppy markets.'
    },
]


def generate_thread_for_schedule(
    client: Optional[anthropic.Anthropic],
    category: str,
    content: 'WeeklyContent',
    mock: bool = False
) -> Dict:
    """
    Generate a thread for the weekly schedule.

    Thread categories:
    - thread_buy_signal: Deep dive on the weekly pick
    - thread_educational: Rotating through 5 educational topics
    - thread_week_ahead: Preview of hot themes for upcoming week

    Args:
        client: Anthropic client (None if mock mode)
        category: thread_buy_signal, thread_educational, or thread_week_ahead
        content: Weekly content data with signals, themes, positions
        mock: If True, generate placeholder thread without API

    Returns:
        Dict with thread data ready for content_queue.json
    """
    # Determine week number for topic rotation (1-5)
    week_number = datetime.now().isocalendar()[1] % 5 or 5

    if category == "thread_buy_signal":
        # Deep dive on the weekly pick
        if content.pass_signals:
            signal = content.pass_signals[0]
            ticker = signal.get('ticker', signal.get('symbol', 'UNKNOWN'))
            theme = signal.get('theme', 'Momentum')
            topic = "Buy Signal Analysis"
            context = f"""Deep dive thread on ${ticker} - our weekly signal.

Theme: {theme}
Key points to cover:
1. Why this fits our systematic criteria (without revealing specifics)
2. The theme momentum driving this sector
3. Risk management approach (Capital Preservation Protocol)
4. How this fits with current portfolio
5. CTA to newsletter for full analysis

DO NOT reveal specific indicator names or thresholds."""
        else:
            topic = "Signal Methodology"
            context = "Explain how our 5-gate system identifies opportunities when most traders are chasing breakouts. Focus on systematic advantage."

    elif category == "thread_educational":
        # Rotate through 5 educational topics each week
        topic_index = (week_number - 1) % len(THREAD_TOPICS)
        topic_data = THREAD_TOPICS[topic_index]
        topic = topic_data['topic']
        context = topic_data['context']

    elif category == "thread_week_ahead":
        # Preview hot themes for upcoming week
        topic = "Week Ahead Preview"
        hot_themes = []
        if content.prime_themes:
            hot_themes = [t.get('name', 'Theme') for t in content.prime_themes[:3]]

        if hot_themes:
            themes_str = ', '.join(hot_themes)
            context = f"""Week ahead preview thread for traders.

Hot themes this week: {themes_str}

Cover:
1. Hook: What's moving into the new week
2. Theme 1 momentum and why
3. Theme 2 opportunities
4. Portfolio positioning / what we're watching
5. CTA to subscribe for signals

Focus on systematic approach and alpha generation vs SPY."""
        else:
            context = "General week ahead preview focusing on market positioning, sector rotation opportunities, and systematic momentum approach."
    else:
        # Fallback for unknown thread category
        topic = "Trading Wisdom"
        context = "Share systematic trading insights and methodology."

    # Generate thread
    if mock:
        # Mock thread for testing
        thread_tweets = [
            {'number': 1, 'text': f"🧵 1/5: [{topic}] Thread placeholder - hook tweet about {category}", 'tweet_id': None},
            {'number': 2, 'text': f"2/5: Problem statement - why most traders struggle with this", 'tweet_id': None},
            {'number': 3, 'text': f"3/5: Our systematic solution and approach", 'tweet_id': None},
            {'number': 4, 'text': f"4/5: Specific example or proof point", 'tweet_id': None},
            {'number': 5, 'text': f"5/5: CTA - Follow for signals, subscribe at sterlingsignals.substack.com", 'tweet_id': None},
        ]
    else:
        # Generate via Claude API
        thread = generate_thread(topic, context, client)
        thread_tweets = thread.tweets if thread else []

    return {
        'is_thread': True,
        'thread_topic': topic,
        'thread_tweets': thread_tweets,
        'thread_status': 'pending',
        'ticker': content.pass_signals[0].get('ticker', content.pass_signals[0].get('symbol')) if content.pass_signals and category == 'thread_buy_signal' else None,
        'theme': content.pass_signals[0].get('theme') if content.pass_signals and category == 'thread_buy_signal' else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL GRAPHICS INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def attach_social_graphics(content: List) -> List:
    """
    Generate social graphics and attach them to content by category.

    Graphics are assigned to tweets that don't already have images:
    - position_update -> portfolio_dashboard
    - beat_spy -> beat_spy comparison chart
    - theme_hot -> theme_card
    - sector_rotation -> sector_rotation chart
    - funnel_graphic -> funnel visualization
    - system_promo -> funnel (reuse)

    Args:
        content: List of Tweet objects and/or thread dicts
    """
    print("\n  📸 Generating social graphics...")

    try:
        from social_graphics import SocialGraphicsGenerator
        generator = SocialGraphicsGenerator()
        graphics = generator.generate_all()
    except ImportError as e:
        print(f"    ⚠ Could not import social_graphics: {e}")
        return content
    except Exception as e:
        print(f"    ⚠ Error generating graphics: {e}")
        return content

    if not graphics:
        print("    ⚠ No graphics generated")
        return content

    # Map categories to graphics
    category_graphics = {
        'position_update': graphics.get('portfolio_dashboard'),
        'beat_spy': graphics.get('beat_spy'),
        'theme_hot': graphics.get('theme_card'),
        'sector_rotation': graphics.get('sector_rotation'),
        'funnel_graphic': graphics.get('funnel'),
        'system_promo': graphics.get('funnel'),  # Reuse funnel
        'market_insight': graphics.get('sector_rotation'),  # Reuse sector rotation
    }

    # Attach graphics to content (handle both Tweet objects and thread dicts)
    attached_count = 0
    for item in content:
        if isinstance(item, Tweet):
            # Tweet object
            if item.image_path:
                continue
            graphic_path = category_graphics.get(item.category)
            if graphic_path:
                item.image_path = str(graphic_path)
                attached_count += 1
        elif isinstance(item, dict) and not item.get('is_thread'):
            # Non-thread dict (shouldn't happen but handle it)
            if item.get('image_path'):
                continue
            graphic_path = category_graphics.get(item.get('category'))
            if graphic_path:
                item['image_path'] = str(graphic_path)
                attached_count += 1
        # Skip threads - they don't get social graphics attached this way

    print(f"    ✓ Attached {attached_count} graphics to tweets")
    print(f"    📁 Graphics in: {CHARTS_DIR}")

    return content


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tweets via Claude API")
    parser.add_argument("--briefing", type=str, help="Path to newsletter briefing")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no API)")
    parser.add_argument("--thread", type=str, help="Generate thread on specific topic")
    parser.add_argument("--thread-list", action="store_true", help="List available thread topics")
    args = parser.parse_args()

    # Thread topic list mode
    if args.thread_list:
        print("\n  Available Thread Topics:")
        print("  " + "─" * 50)
        for i, t in enumerate(THREAD_TOPICS, 1):
            print(f"\n  {i}. {t['topic']}")
            print(f"     {t['context'][:80]}...")
        print("\n  Usage: python tweet_generator.py --thread \"Bottleneck Investing\"")
        return

    # Thread generation mode
    if args.thread:
        print("\n" + "═" * 60)
        print("  THREAD GENERATOR")
        print("═" * 60)

        # Find matching topic
        topic_match = next((t for t in THREAD_TOPICS if args.thread.lower() in t['topic'].lower()), None)

        if topic_match:
            print(f"\n  📝 Generating thread: {topic_match['topic']}")
            thread = generate_thread(topic_match['topic'], topic_match['context'])
        else:
            print(f"\n  📝 Generating thread: {args.thread}")
            thread = generate_thread(args.thread)

        # Save thread
        output_dir = Path(args.output) if args.output else TWEETS_DIR
        save_thread(thread, output_dir)

        # Print preview
        print("\n  Thread Preview:")
        print("  " + "─" * 50)
        for tweet in thread.tweets:
            print(f"\n  {tweet.get('number', '?')}/5:")
            print(f"  {tweet.get('text', '[empty]')}")

        print("\n" + "═" * 60)
        return

    print("\n" + "═" * 60)
    print("  TWEET GENERATOR - Claude-Powered Content")
    print("═" * 60)

    # Load data - try current/ folder first
    if args.briefing:
        briefing_path = Path(args.briefing)
    elif OUTPUT_PATHS_AVAILABLE:
        current_dir = get_current_dir()
        briefing_path = current_dir / "newsletter_briefing.md"
        if not briefing_path.exists():
            briefing_path = TRADES_DIR / "latest_newsletter_briefing.md"
    else:
        briefing_path = TRADES_DIR / "latest_newsletter_briefing.md"

    print(f"\n  📄 Loading: {briefing_path}")

    content = load_briefing_data(briefing_path)

    print(f"  📊 Data loaded:")
    print(f"     • PASS signals: {len(content.pass_signals)}")
    print(f"     • Open positions: {len(content.open_positions)}")
    print(f"     • Closed trades: {len(content.closed_trades)}")
    print(f"     • Sell signals: {len(content.sell_signals)}")
    print(f"     • Hot themes: {len(content.prime_themes) + len(content.investable_themes)}")
    print(f"     • Cold themes: {len(content.selective_themes) + len(content.avoid_themes)}")
    print(f"     • Charts available: {len(content.chart_manifest)}")

    # Generate tweets
    tweets = generate_all_tweets(content, mock=args.mock)

    # Generate social graphics and attach to tweets
    tweets = attach_social_graphics(tweets)

    # Save output
    output_dir = Path(args.output) if args.output else TWEETS_DIR
    queue_file = save_tweets(tweets, output_dir)

    # Print summary
    print_summary(tweets)

    print(f"\n  ✅ Generated {len(tweets)} tweets")
    print(f"  📁 Content queue: {queue_file}")
    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
