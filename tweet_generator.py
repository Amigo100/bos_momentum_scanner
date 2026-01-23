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
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = {
    1: "early_morning",  # 07:00 UK
    2: "morning",        # 09:00 UK
    3: "midday",         # 12:30 UK
    4: "afternoon",      # 15:30 UK
    5: "evening"         # 19:00 UK
}


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

TWEET_SYSTEM_PROMPT = """You are a financial content writer for Sterling Signals, a momentum trading newsletter on Substack.

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

CRITICAL MARKETING LANGUAGE RULES:
1. NEVER reveal specific strategy details:
   - NO: "20% trailing stop", "HMA pivots", "Banker indicator formula", "Beta >= 1.5"
   - YES: "proprietary risk management", "technical indicators", "smart money signals"

2. USE these approved phrases instead:
   - "proprietary multi-step screening process"
   - "smart money accumulation signals"
   - "institutional flow tracking"
   - "theme momentum confirmation"
   - "technical entry/exit signals"
   - "rigorous due diligence"
   - "disciplined risk management"
   - "systematic approach"

3. FOCUS messaging on these themes:
   - Following institutional money / smart money flows
   - Identifying hot themes and bottleneck plays
   - Contrarian opportunities when themes are cold
   - Patience and discipline over FOMO
   - Outperforming the market through systematic approach
   - Multi-step filtering (1800 stocks → 3-5 winners)

4. CREATE intrigue without revealing the secret sauce:
   - "Our proprietary signals flagged this before the move"
   - "Smart money was accumulating here for weeks"
   - "Our multi-step system identified this bottleneck theme"

CRITICAL HONESTY + POSITIVITY RULES:
1. NEVER hide losses or only show winners - always include full P&L picture
2. NEVER exclude stopped-out trades from portfolio updates
3. When portfolio is down, frame constructively:
   - "Down 5% YTD but system working - cutting losers fast"
   - "3 stops hit this month = capital preserved for better setups"
   - "Drawdowns are part of momentum trading - here's how we manage them"
4. Frame losses as LEARNING/DISCIPLINE, not failures:
   - "Stop hit = system working exactly as designed"
   - "Risk management protected us from a bigger loss"
   - "Discipline > ego. We'll catch the next one."
5. When mentioning portfolio, ALWAYS include:
   - Total unrealized P&L (not just winners)
   - Any recent stops hit
   - Win rate if discussing closed trades
6. Find the positive angle WITHOUT lying:
   - Market down 10%, we're down 5% = "Outperforming in tough conditions"
   - Had 2 losers, 1 big winner = "One winner covered both losses + profit"
   - New to trading, no track record = "Building track record transparently"

CRITICAL: Every tweet MUST either:
- Link to Substack (sterlingsignals.substack.com)
- Ask an engaging question
- Highlight our multi-step proprietary system

STRUCTURE:
- Hook in first line
- Key insight or data point
- CTA or question to drive engagement

Return tweets as a JSON array with this structure:
[
  {
    "category": "buy_signal|theme_hot|theme_cold|closed_trade|position_update|sell_signal|system_promo|market_insight|educational|engagement",
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

    else:
        context = f"Generate {count} general financial content tweets. Always link to sterlingsignals.substack.com"

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

    # Category distribution across the week
    # 35 total = 5 per day × 7 days (X API allows ~50/day)
    # Prioritize: system_promo, buy_signal, theme_hot, closed_trade
    categories_schedule = [
        # Monday: Week kickoff - system, themes, signals
        ("Monday", 1, "system_promo"),      # Early: System overview
        ("Monday", 2, "theme_hot"),          # Morning: Hot theme spotlight
        ("Monday", 3, "buy_signal"),         # Midday: Buy signal
        ("Monday", 4, "position_update"),    # Afternoon: Portfolio update
        ("Monday", 5, "engagement"),         # Evening: Engagement

        # Tuesday: Education & positions
        ("Tuesday", 1, "educational"),       # Early: Trading lesson
        ("Tuesday", 2, "position_update"),   # Morning: Position P&L
        ("Tuesday", 3, "theme_hot"),         # Midday: Another hot theme
        ("Tuesday", 4, "system_promo"),      # Afternoon: System feature
        ("Tuesday", 5, "closed_trade" if content.closed_trades else "engagement"),

        # Wednesday: Mid-week momentum
        ("Wednesday", 1, "theme_hot"),       # Early: Theme momentum
        ("Wednesday", 2, "buy_signal" if len(content.pass_signals) > 1 else "system_promo"),
        ("Wednesday", 3, "educational"),     # Midday: Trading tip
        ("Wednesday", 4, "theme_cold"),      # Afternoon: What to avoid
        ("Wednesday", 5, "engagement"),      # Evening: Q&A

        # Thursday: Deep dive day
        ("Thursday", 1, "market_insight"),   # Early: Market outlook
        ("Thursday", 2, "position_update"),  # Morning: Portfolio check
        ("Thursday", 3, "buy_signal" if len(content.pass_signals) > 2 else "theme_hot"),
        ("Thursday", 4, "system_promo"),     # Afternoon: Methodology
        ("Thursday", 5, "educational"),      # Evening: Risk management

        # Friday: Pre-weekend recap
        ("Friday", 1, "theme_hot"),          # Early: Theme update
        ("Friday", 2, "sell_signal" if content.sell_signals else "position_update"),
        ("Friday", 3, "system_promo"),       # Midday: Newsletter teaser
        ("Friday", 4, "engagement"),         # Afternoon: Weekend poll
        ("Friday", 5, "market_insight"),     # Evening: Week recap

        # Saturday: Newsletter day - heavy promotion
        ("Saturday", 1, "buy_signal"),       # Early: Newsletter highlight
        ("Saturday", 2, "system_promo"),     # Morning: System promo
        ("Saturday", 3, "theme_hot"),        # Midday: Featured theme
        ("Saturday", 4, "closed_trade" if content.closed_trades else "educational"),
        ("Saturday", 5, "engagement"),       # Evening: Discussion

        # Sunday: Week ahead planning
        ("Sunday", 1, "market_insight"),     # Early: Week ahead
        ("Sunday", 2, "theme_hot"),          # Morning: Theme preview
        ("Sunday", 3, "educational"),        # Midday: Learning
        ("Sunday", 4, "system_promo"),       # Afternoon: Newsletter CTA
        ("Sunday", 5, "engagement"),         # Evening: Week kickoff poll
    ]

    # Group by category to batch API calls
    categories_needed = {}
    for day, slot, category in categories_schedule:
        if category not in categories_needed:
            categories_needed[category] = []
        categories_needed[category].append((day, slot))

    # Generate tweets by category
    print("\n  🤖 Generating tweets via Claude API...")

    generated_by_category = {}
    for category, slots in categories_needed.items():
        print(f"    • {category}: {len(slots)} tweets...")
        tweets = generate_tweets_for_category(client, category, content, count=len(slots))
        generated_by_category[category] = tweets

    # Assign tweets to schedule
    category_index = {cat: 0 for cat in categories_needed}

    # Calculate dates (start from next Monday)
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # Next Monday if today is Monday
    start_date = today + timedelta(days=days_until_monday)

    for day, slot, category in categories_schedule:
        day_offset = DAYS.index(day)
        scheduled_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        # Get next tweet for this category
        idx = category_index[category]
        tweets_for_cat = generated_by_category.get(category, [])

        if idx < len(tweets_for_cat):
            tweet_data = tweets_for_cat[idx]
            category_index[category] += 1
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

    return all_tweets


def generate_mock_tweets() -> List[Tweet]:
    """Generate mock tweets for testing without API calls."""
    tweets = []

    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    start_date = today + timedelta(days=days_until_monday)

    for i, day in enumerate(DAYS):
        scheduled_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for slot in [1, 2, 3]:
            tweets.append(Tweet(
                id=f"{day.lower()}_{slot}_mock",
                day=day,
                slot=slot,
                category="mock",
                text=f"[MOCK] {day} {SLOTS[slot]} tweet placeholder",
                scheduled_date=scheduled_date
            ))

    return tweets


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

    # Load closed trades from portfolio.csv
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if portfolio_file.exists():
        import csv
        with open(portfolio_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status') in ['CLOSED', 'STOPPED']:
                    # Calculate P&L
                    try:
                        entry = float(row.get('entry_price', 0))
                        exit_price = float(row.get('exit_price', 0))
                        pnl = ((exit_price / entry) - 1) * 100 if entry > 0 else 0
                    except:
                        pnl = 0

                    content.closed_trades.append({
                        'ticker': row['ticker'],
                        'entry_price': row.get('entry_price'),
                        'exit_price': row.get('exit_price'),
                        'exit_date': row.get('exit_date'),
                        'status': row.get('status'),
                        'pnl_pct': pnl,
                        'theme': row.get('theme')
                    })

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

def save_tweets(tweets: List[Tweet], output_dir: Path) -> Path:
    """Save tweets to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    tweets_json = json.dumps([t.to_dict() for t in tweets], indent=2)

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


def print_summary(tweets: List[Tweet]):
    """Print summary of generated tweets."""
    print("\n  📊 Tweet Summary:")
    print("  " + "─" * 50)

    for day in DAYS:
        day_tweets = [t for t in tweets if t.day == day]
        if day_tweets:
            print(f"\n  📅 {day}:")
            for t in sorted(day_tweets, key=lambda x: x.slot):
                slot_name = SLOTS[t.slot]
                ticker_str = f" ${t.ticker}" if t.ticker else ""
                chart_str = " 📸" if t.image_path else ""
                text_preview = t.text[:50] + "..." if len(t.text) > 50 else t.text
                print(f"     {slot_name:8} [{t.category:15}]{ticker_str}{chart_str}")
                print(f"              {text_preview}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate tweets via Claude API")
    parser.add_argument("--briefing", type=str, help="Path to newsletter briefing")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no API)")
    args = parser.parse_args()

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
