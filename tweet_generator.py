#!/usr/bin/env python3
"""
TWEET GENERATOR - Claude-Powered Final Tweet Generation
========================================================

Generates 21 ready-to-post tweets for the week based on scanner outputs.
Uses Claude API to create engaging financial content directly.

Replaces grok_prompts_generator.py - no more manual Grok step!

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

# Days and slots
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = {
    1: "morning",   # 08:00 UK
    2: "midday",    # 12:30 UK
    3: "evening"    # 18:00 UK
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
6. Include a CTA when appropriate (link to newsletter, ask a question)

STYLE GUIDELINES:
- Confident but not arrogant
- Data-driven, specific numbers when available
- Professional trader voice, not hype
- Occasional humor is OK
- No financial advice disclaimers in tweets (save for bio)

STRUCTURE:
- Hook in first line
- Key insight or data point
- CTA or question to drive engagement

Return tweets as a JSON array with this structure:
[
  {
    "category": "buy_signal|theme_hot|theme_cold|position_update|sell_signal|market_insight|educational|engagement",
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
Generate {count} tweets about new BUY signals.

PASS Signals this week:
{json.dumps(content.pass_signals, indent=2)}

For each signal, highlight:
- The ticker and why it's bullish
- The theme it belongs to
- Key catalyst or technical setup
- Link to full analysis in newsletter
"""
    
    elif category == "theme_hot":
        context = f"""
Generate {count} tweets about HOT themes (PRIME and INVESTABLE).

PRIME Themes:
{json.dumps(content.prime_themes, indent=2)}

INVESTABLE Themes:
{json.dumps(content.investable_themes, indent=2)}

For each tweet:
- Explain why the theme is hot
- Mention key stocks benefiting
- Connect to broader market narrative
"""
    
    elif category == "theme_cold":
        context = f"""
Generate {count} tweets about themes to AVOID or be SELECTIVE with.

SELECTIVE Themes:
{json.dumps(content.selective_themes, indent=2)}

AVOID Themes:
{json.dumps(content.avoid_themes, indent=2)}

Frame these as:
- Risk warnings for crowded trades
- Themes losing momentum
- Educational about why momentum matters
"""
    
    elif category == "position_update":
        context = f"""
Generate {count} tweets about current open positions.

Open Positions:
{json.dumps(content.open_positions, indent=2)}

For each:
- Current P&L (be transparent)
- Why still holding (or watching closely)
- Stop level awareness
"""
    
    elif category == "sell_signal":
        context = f"""
Generate {count} tweets about SELL signals (if any).

Sell Signals:
{json.dumps(content.sell_signals, indent=2)}

Frame as:
- Risk management in action
- Protecting gains / cutting losses
- Educational about stop discipline
"""
    
    elif category == "market_insight":
        context = f"""
Generate {count} tweets about market outlook for the week.

Current themes: {[t.get('name') for t in content.prime_themes + content.investable_themes]}
Current positions: {[p.get('ticker') for p in content.open_positions]}

Topics:
- Week ahead preview
- Sector rotation observations
- Macro factors to watch
"""
    
    elif category == "educational":
        context = f"""
Generate {count} educational tweets about momentum trading.

Topics to cover:
- How we identify breakouts (BoS signals)
- Theme investing approach
- Risk management (20% trailing stops)
- Why we use weekly timeframes
"""
    
    elif category == "engagement":
        context = f"""
Generate {count} engagement tweets (questions, polls, discussions).

Examples:
- "What sectors are you watching this week?"
- "How do you handle positions at all-time highs?"
- "Biggest lesson from your last losing trade?"
"""
    
    else:
        context = f"Generate {count} general financial content tweets."
    
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
    # 21 total = 3 per day × 7 days
    categories_schedule = [
        # Monday: Market week ahead, hot theme, buy signal
        ("Monday", 1, "market_insight"),
        ("Monday", 2, "theme_hot"),
        ("Monday", 3, "buy_signal"),
        
        # Tuesday: Position update, educational, engagement
        ("Tuesday", 1, "position_update"),
        ("Tuesday", 2, "educational"),
        ("Tuesday", 3, "engagement"),
        
        # Wednesday: Hot theme, buy signal, cold theme warning
        ("Wednesday", 1, "theme_hot"),
        ("Wednesday", 2, "buy_signal"),
        ("Wednesday", 3, "theme_cold"),
        
        # Thursday: Market insight, position update, educational
        ("Thursday", 1, "market_insight"),
        ("Thursday", 2, "position_update"),
        ("Thursday", 3, "educational"),
        
        # Friday: Hot theme, sell signal (if any), engagement
        ("Friday", 1, "theme_hot"),
        ("Friday", 2, "sell_signal" if content.sell_signals else "position_update"),
        ("Friday", 3, "engagement"),
        
        # Saturday: Newsletter drop promo, week recap, educational
        ("Saturday", 1, "buy_signal"),  # Newsletter highlight
        ("Saturday", 2, "market_insight"),  # Week recap
        ("Saturday", 3, "educational"),
        
        # Sunday: Week ahead, engagement, theme preview
        ("Sunday", 1, "market_insight"),
        ("Sunday", 2, "engagement"),
        ("Sunday", 3, "theme_hot"),
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
    
    # Full tweets file
    tweets_file = output_dir / f"tweets_{date_str}.json"
    with open(tweets_file, 'w') as f:
        json.dump([t.to_dict() for t in tweets], f, indent=2)
    
    # Content queue for twitter_poster.py
    queue_file = output_dir / "content_queue.json"
    with open(queue_file, 'w') as f:
        json.dump([t.to_dict() for t in tweets], f, indent=2)
    
    # Also save to trades root for easy access
    root_queue = TRADES_DIR / "content_queue.json"
    with open(root_queue, 'w') as f:
        json.dump([t.to_dict() for t in tweets], f, indent=2)
    
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
    
    # Load data
    briefing_path = Path(args.briefing) if args.briefing else TRADES_DIR / "latest_newsletter_briefing.md"
    print(f"\n  📄 Loading: {briefing_path}")
    
    content = load_briefing_data(briefing_path)
    
    print(f"  📊 Data loaded:")
    print(f"     • PASS signals: {len(content.pass_signals)}")
    print(f"     • Open positions: {len(content.open_positions)}")
    print(f"     • Sell signals: {len(content.sell_signals)}")
    print(f"     • Hot themes: {len(content.prime_themes) + len(content.investable_themes)}")
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
