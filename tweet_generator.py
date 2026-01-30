#!/usr/bin/env python3
"""
TWEET GENERATOR - Hybrid Template + Claude-Powered Tweet Generation
====================================================================

Generates 21+ ready-to-post tweets for the week based on scanner outputs.
Uses authentic templates with Claude API fallback for variation.

NEW v2 FEATURES:
- Authentic template library with personal voice
- GREEN (buy) / RED (sell) signal terminology  
- Friday weekly close price references throughout
- 25%+ threshold enforcement for position updates
- Multi-account template variations
- Template usage tracking for variety
- Comparison mode: Claude vs Templates vs Hybrid

Usage:
    python tweet_generator.py                              # Uses latest briefing
    python tweet_generator.py --briefing PATH              # Specific briefing file
    python tweet_generator.py --mock                       # Use mock data (no API)
    python tweet_generator.py --compare                    # Generate comparison output

Output:
    trades/tweets/tweets_{date}.json       # All tweets with metadata
    trades/tweets/content_queue.json       # Ready for twitter_poster.py
    trades/tweets/comparison_output.json   # When --compare used
"""

import os
import sys
import json
import argparse
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
import re
import copy

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

# Import signal tracker for safeguards and big wins
try:
    from signal_tracker import (
        should_post_beat_spy,
        has_enough_wins,
        filter_public_positions,
        get_uncelebrated_wins,
        mark_as_celebrated,
        load_historical_signals,
        calculate_portfolio_vs_spy,
        filter_expired_consider_signals,
        check_cold_streak,
    )
    SIGNAL_TRACKER_AVAILABLE = True
except ImportError:
    SIGNAL_TRACKER_AVAILABLE = False
    print("  Warning: signal_tracker not available - safeguards disabled")

# Import config for thresholds
try:
    from config import (
        MARKETING_THRESHOLDS,
        get_fallback_category,
        is_safeguarded_category,
        get_highlight_threshold,
        format_holding_period,
        TIMEFRAME_DISCLAIMERS,
        WIN_CATEGORIES,
        SIGNAL_COLORS,
        CONVICTION_LANGUAGE,
        get_signal_emoji,
        get_conviction_text,
        can_show_entry_price,
        BRANDING,
        TWITTER_ACCOUNTS,
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    TWITTER_ACCOUNTS = {}
    MARKETING_THRESHOLDS = {
        'min_pnl_for_highlight': 25.0,
        'min_pnl_for_entry_price': 25.0,
        'early_mover_threshold': 5.0,
    }
    def format_holding_period(days):
        if days < 7:
            return f"{days} days" if days != 1 else "1 day"
        weeks = days // 7
        return f"{weeks} weeks" if weeks != 1 else "1 week"
    def can_show_entry_price(pnl_pct, status='OPEN'):
        return pnl_pct >= 25.0 or status == 'CLOSED'
    def get_conviction_text(conviction):
        mapping = {5: "Extremely Bullish", 4: "Bullish", 3: "Watching", 2: "Cautious", 1: "Neutral"}
        return mapping.get(conviction, "Bullish")

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
    def validate_content(text):
        return True, []
    def validate_all_tweets(tweets):
        return len(tweets), 0

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS AND CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Directory setup
SCRIPT_DIR = Path(__file__).resolve().parent
TRADES_DIR = SCRIPT_DIR / "trades"
TWEETS_DIR = TRADES_DIR / "tweets"
TWEETS_DIR.mkdir(parents=True, exist_ok=True)

# Sterling Signals branding
SUBSTACK_URL = "https://sterlingsignals.substack.com"
ACCOUNT_HANDLE = "@SterlingSignals"

# Claude model for tweet generation
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000

# Days and slots (5 per day to use X API limits)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = {
    1: "pre_market",     # 08:00 ET - Pre-market / Top performers
    2: "morning",        # 10:00 ET - 30min after market open
    3: "midday",         # 12:30 ET - Lunch break engagement
    4: "power_hour",     # 15:30 ET - Power Hour reaction
    5: "after_hours"     # 18:00 ET - After-hours / engagement
}

# Thresholds for template selection
TEMPLATE_THRESHOLDS = {
    'min_pnl_for_position_update': 25.0,
    'min_pnl_for_closed_win': 25.0,
    'min_pnl_for_entry_price': 25.0,
    'early_mover_threshold': 5.0,
}

# Signal terminology (GREEN = buy, RED = sell)
SIGNAL_EMOJI = {
    'green': '🟢',
    'red': '🔴',
    'consider': '🟡',
}

# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY CLOSE PHRASING - Natural variation for Friday references
# ═══════════════════════════════════════════════════════════════════════════════

WEEKLY_CLOSE_PHRASES = [
    "Friday's close",
    "as of Friday",
    "ended the week at",
    "last week's close",
    "the latest weekly close",
]

WEEKLY_CLOSE_PAST_PHRASES = [
    "as of the latest weekly close",
    "based on Friday's close",
    "from Friday's scan",
    "after Friday's close",
]

def get_weekly_close_phrase(style='standard'):
    """Get a natural weekly close phrase for variety."""
    if style == 'past':
        return random.choice(WEEKLY_CLOSE_PAST_PHRASES)
    return random.choice(WEEKLY_CLOSE_PHRASES)

def maybe_vary_phrase(template_text, probability=0.3):
    """Randomly vary weekly close phrasing in template.
    
    Only swaps phrases when grammatically appropriate (phrase followed by colon or period).
    """
    if random.random() >= probability:
        return template_text
    
    # Only swap "Friday's close" type phrases when they appear as standalone references
    # Don't swap mid-sentence phrases that would break grammar
    safe_swaps = {
        "Friday's close:": ["as of Friday:", "last week's close:"],
        "as of Friday.": ["as of the latest weekly close.", "based on Friday's close."],
        "ended the week at": ["closed Friday at"],
        "closed Friday at": ["ended the week at"],
    }
    
    for original, replacements in safe_swaps.items():
        if original in template_text:
            replacement = random.choice(replacements)
            return template_text.replace(original, replacement, 1)
    
    return template_text

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTIC TEMPLATE LIBRARY - Personal voice, Friday references
# ═══════════════════════════════════════════════════════════════════════════════

AUTHENTIC_TEMPLATES = {
    # -------------------------------------------------------------------------
    # CATEGORY 1: BUY SIGNAL (GREEN signals)
    # -------------------------------------------------------------------------
    'buy_signal': [
        {
            'id': 'buy_1',
            'text': "🟢 ${{TICKER}} showed up in Friday's scan.\n\nClosed the week at ${{PRICE}}. {{CONVICTION_TEXT}}.\n\nFull breakdown in the newsletter 👇\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'price', 'conviction'],
            'account_variations': {
                'account_2': "🟢 GREEN signal: ${{TICKER}}\n\nFriday's close: ${{PRICE}}\nConviction: {{CONVICTION_TEXT}}\n\nDetails in this week's issue:\n{{SUBSTACK_URL}}",
                'account_3': "${{TICKER}} cleared all 5 gates as of Friday.\n\n🟢 Weekly close: ${{PRICE}}\n\nAnalysis:\n{{SUBSTACK_URL}}"
            }
        },
        {
            'id': 'buy_2', 
            'text': "Ran the scanner after Friday's close.\n\nHere's what passed all 5 gates:\n\n{{SIGNAL_LIST}}\n\nFull analysis + entry levels 👇\n{{SUBSTACK_URL}}",
            'requires': ['signal_list'],
            'account_variations': {
                'account_2': "Friday scan complete.\n\n🟢 GREEN signals this week:\n{{SIGNAL_LIST}}\n\nDetailed breakdown:\n{{SUBSTACK_URL}}",
                'account_3': "5-Gate Scanner Results (Friday close):\n\n{{SIGNAL_LIST}}\n\nFull writeup:\n{{SUBSTACK_URL}}"
            }
        },
        {
            'id': 'buy_3',
            'text': "🟢 New GREEN signal: ${{TICKER}}\n\nEnded the week at ${{PRICE}} — {{CONVICTION_TEXT}}\n\n{{THEME}} theme showing strength.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'price', 'conviction', 'theme'],
        },
        {
            'id': 'buy_4',
            'text': "{{NUM_SIGNALS}} stocks cleared all gates this week.\n\n🟢 Top conviction:\n${{TICKER}} — {{CONVICTION_TEXT}}\nFriday's close: ${{PRICE}}\n\n{{SUBSTACK_URL}}",
            'requires': ['num_signals', 'ticker', 'price', 'conviction'],
        },
        {
            'id': 'buy_5',
            'text': "The scanner doesn't lie.\n\n🟢 ${{TICKER}} passed all 5 gates as of Friday's close at ${{PRICE}}.\n\nThis week's full signal list:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'price'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 2: TOP PERFORMERS (25%+ ONLY)
    # -------------------------------------------------------------------------
    'top_performers': [
        {
            'id': 'top_1',
            'text': "Current positions as of Friday's close:\n\n{{WINNERS_LIST}}\n\nEntry prices + full thesis in the newsletter:\n{{SUBSTACK_URL}}",
            'requires': ['winners_list'],
            'min_pnl': 25.0,
            'account_variations': {
                'account_2': "Portfolio update (Friday close):\n\n{{WINNERS_LIST}}\n\nAll positions tracked here:\n{{SUBSTACK_URL}}",
                'account_3': "Where we stand after last week:\n\n{{WINNERS_LIST}}\n\n{{SUBSTACK_URL}}"
            }
        },
        {
            'id': 'top_2',
            'text': "${{TICKER}} update:\n\nEntry: ${{ENTRY}}\nFriday's close: ${{CURRENT}}\nReturn: +{{PNL}}% ({{WEEKS_HELD}})\n\nStill holding. Trailing stop in place.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'current', 'pnl', 'weeks_held'],
            'min_pnl': 25.0,
        },
        {
            'id': 'top_3',
            'text': "The 5-Gate System at work:\n\n${{TICKER}}: +{{PNL}}%\nEntry: ${{ENTRY}} → Friday: ${{CURRENT}}\nHeld: {{WEEKS_HELD}}\n\nMore setups like this weekly:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'current', 'pnl', 'weeks_held'],
            'min_pnl': 25.0,
        },
        {
            'id': 'top_4',
            'text': "{{THEME}} has been good to us.\n\n${{TICKER}}: +{{PNL}}% since entry\nFriday's close: ${{CURRENT}}\n\nFull portfolio breakdown:\n{{SUBSTACK_URL}}",
            'requires': ['theme', 'ticker', 'pnl', 'current'],
            'min_pnl': 25.0,
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 3: CLOSED TRADE (25%+ winners only)
    # -------------------------------------------------------------------------
    'closed_trade': [
        {
            'id': 'closed_1',
            'text': "Closed ${{TICKER}} last week.\n\nEntry: ${{ENTRY}}\nExit: ${{EXIT}}\nReturn: +{{PNL}}%\nHeld: {{WEEKS_HELD}}\n\nOnto the next setup.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'exit', 'pnl', 'weeks_held'],
            'min_pnl': 25.0,
        },
        {
            'id': 'closed_2',
            'text': "${{TICKER}} trade complete.\n\n+{{PNL}}% in {{WEEKS_HELD}}\n\nEntry at ${{ENTRY}}, exited at ${{EXIT}} as of Friday.\n\nThis is what the system is built for.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'exit', 'pnl', 'weeks_held'],
            'min_pnl': 25.0,
        },
        {
            'id': 'closed_3',
            'text': "Trade recap: ${{TICKER}}\n\n🟢 Entry: ${{ENTRY}}\n🔴 Exit: ${{EXIT}}\n📈 Result: +{{PNL}}%\n⏱️ Duration: {{WEEKS_HELD}}\n\nNext week's signals drop Saturday:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'exit', 'pnl', 'weeks_held'],
            'min_pnl': 25.0,
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 4: SELL SIGNAL (RED - neutral framing, NO P&L)
    # -------------------------------------------------------------------------
    'sell_signal': [
        {
            'id': 'sell_1',
            'text': "🔴 Exited ${{TICKER}} at last week's close.\n\nTime to move on. The system says rotate.\n\nCurrent open positions:\n{{SUBSTACK_URL}}",
            'requires': ['ticker'],
        },
        {
            'id': 'sell_2',
            'text': "Rotating out of ${{TICKER}} as of Friday.\n\n{{THEME}} momentum slowing. Following the signals.\n\nUpdated portfolio:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'theme'],
        },
        {
            'id': 'sell_3',
            'text': "🔴 RED signal on ${{TICKER}}.\n\nClosed the position last week. Capital freed up for new setups.\n\nThis week's scan:\n{{SUBSTACK_URL}}",
            'requires': ['ticker'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 5: THEME HOT
    # -------------------------------------------------------------------------
    'theme_hot': [
        {
            'id': 'hot_1',
            'text': "{{THEME}} ended the week on fire.\n\n${{TICKER1}}, ${{TICKER2}}, ${{TICKER3}} all closed strong Friday.\n\nTheme rotation is real. Are you positioned?\n\n{{SUBSTACK_URL}}",
            'requires': ['theme', 'ticker1', 'ticker2', 'ticker3'],
        },
        {
            'id': 'hot_2',
            'text': "{{THEME}} showing up in the scanner again.\n\nThis sector has been printing GREEN signals for weeks.\n\nLatest picks:\n{{SUBSTACK_URL}}",
            'requires': ['theme'],
        },
        {
            'id': 'hot_3',
            'text': "Sector spotlight: {{THEME}}\n\nMultiple stocks from this theme passed Friday's scan.\n\nMomentum is real. Full breakdown:\n{{SUBSTACK_URL}}",
            'requires': ['theme'],
            'account_variations': {
                'account_2': "{{THEME}} continues to dominate the scanner.\n\nFriday's results speak for themselves.\n\nAnalysis:\n{{SUBSTACK_URL}}",
                'account_3': "Theme watch: {{THEME}}\n\nStrong closes across the sector Friday.\n\n{{SUBSTACK_URL}}"
            }
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 6: THEME COLD
    # -------------------------------------------------------------------------
    'theme_cold': [
        {
            'id': 'cold_1',
            'text': "Rotation showing up as of last week.\n\nMoney leaving {{COLD_THEME}}, flowing into {{HOT_THEME}}.\n\nThe scanner sees it first.\n\n{{SUBSTACK_URL}}",
            'requires': ['cold_theme', 'hot_theme'],
        },
        {
            'id': 'cold_2',
            'text': "{{COLD_THEME}} went quiet in Friday's scan.\n\nNo new signals. Existing positions on watch.\n\nWhere the momentum is now:\n{{SUBSTACK_URL}}",
            'requires': ['cold_theme'],
        },
        {
            'id': 'cold_3',
            'text': "Not everything works forever.\n\n{{COLD_THEME}} cooling off based on Friday's data.\n\nRotating capital to stronger themes:\n{{SUBSTACK_URL}}",
            'requires': ['cold_theme'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 7: FUNNEL GRAPHIC
    # -------------------------------------------------------------------------
    'funnel_graphic': [
        {
            'id': 'funnel_1',
            'text': "Scanner finished after Friday's close.\n\n{{TOTAL}} stocks analyzed\n{{GATE1}} passed Gate 1\n{{GATE2}} passed Gate 2\n{{GATE3}} passed Gate 3\n{{GATE4}} passed Gate 4\n{{FINAL}} made the cut ✅\n\n{{SUBSTACK_URL}}",
            'requires': ['total', 'final'],
        },
        {
            'id': 'funnel_2',
            'text': "The funnel in action:\n\n{{TOTAL}} stocks → {{FINAL}} GREEN signals\n\nThat's the 5-Gate filter doing its job.\n\nThis week's survivors:\n{{SUBSTACK_URL}}",
            'requires': ['total', 'final'],
        },
        {
            'id': 'funnel_3',
            'text': "Friday scan stats:\n\n📊 {{TOTAL}} stocks scanned\n✅ {{FINAL}} passed all 5 gates\n\nQuality > quantity. Always.\n\n{{SUBSTACK_URL}}",
            'requires': ['total', 'final'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 8: EDUCATIONAL (evergreen content)
    # -------------------------------------------------------------------------
    'educational': [
        {
            'id': 'edu_1',
            'text': "Why I trade weekly signals:\n\n• Less noise than daily\n• Clearer trend confirmation\n• Better risk management\n• No pattern day trader restrictions\n\nHow I find them:\n{{SUBSTACK_URL}}",
            'requires': [],
        },
        {
            'id': 'edu_2',
            'text': "The 5-Gate System in 30 seconds:\n\nGate 1: Trend alignment\nGate 2: Momentum confirmation\nGate 3: Volume validation\nGate 4: Institutional footprint\nGate 5: Risk/reward setup\n\nFull methodology:\n{{SUBSTACK_URL}}",
            'requires': [],
        },
        {
            'id': 'edu_3',
            'text': "Most traders overcomplicate entries.\n\nI look for 5 things. That's it.\n\nIf all 5 align, I take the trade.\nIf not, I wait.\n\nSimplicity scales.\n\n{{SUBSTACK_URL}}",
            'requires': [],
        },
        {
            'id': 'edu_4',
            'text': "Position sizing matters more than entry price.\n\nI never risk more than I'm willing to lose on any single trade.\n\nThe math behind my approach:\n{{SUBSTACK_URL}}",
            'requires': [],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 9: BEAT SPY
    # -------------------------------------------------------------------------
    'beat_spy': [
        {
            'id': 'spy_1',
            'text': "Last week:\n\nSPY: {{SPY_PCT}}%\nOur positions: +{{OUR_PCT}}% average\n\nAlpha exists if you know where to look.\n\n{{SUBSTACK_URL}}",
            'requires': ['spy_pct', 'our_pct'],
        },
        {
            'id': 'spy_2',
            'text': "Portfolio vs benchmark (as of Friday's close):\n\n📈 Our average: +{{OUR_PCT}}%\n📊 SPY: {{SPY_PCT}}%\n\nThe 5-Gate edge in action.\n\n{{SUBSTACK_URL}}",
            'requires': ['spy_pct', 'our_pct'],
        },
        {
            'id': 'spy_3',
            'text': "Why stock pick when you can just buy SPY?\n\nBecause last week:\nSPY: {{SPY_PCT}}%\nUs: +{{OUR_PCT}}%\n\nThat's why.\n\n{{SUBSTACK_URL}}",
            'requires': ['spy_pct', 'our_pct'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 10: ENGAGEMENT
    # -------------------------------------------------------------------------
    'engagement': [
        {
            'id': 'engage_1',
            'text': "Drop a ticker below.\n\nI'll chart the top 3 this weekend and share what the 5-Gate System says.\n\n👇",
            'requires': [],
        },
        {
            'id': 'engage_2',
            'text': "What sector are you most bullish on heading into next week?\n\n🔋 Energy\n💻 Tech\n🏥 Healthcare\n🏦 Financials\n\nReply with your pick 👇",
            'requires': [],
        },
        {
            'id': 'engage_3',
            'text': "Quick question:\n\nDo you prefer to see:\nA) More signal breakdowns\nB) More trade recaps\nC) More educational content\n\nHelps me know what to post.\n\n👇",
            'requires': [],
        },
        {
            'id': 'engage_4',
            'text': "Weekend homework:\n\nPick your top 3 stocks for next week.\n\nComment below — let's compare notes after Friday's scan.\n\n👇",
            'requires': [],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 11: POWER HOUR (theme-focused)
    # -------------------------------------------------------------------------
    'power_hour': [
        {
            'id': 'power_1',
            'text': "⚡ Power Hour:\n\n{{THEME}} showing relative strength into Friday's close.\n\nWatching for follow-through next week.\n\n{{SUBSTACK_URL}}",
            'requires': ['theme'],
        },
        {
            'id': 'power_2',
            'text': "⚡ Power Hour watch:\n\nVolume picking up in {{THEME}} names.\n\nThe close matters. Eyes on the scanner.\n\n{{SUBSTACK_URL}}",
            'requires': ['theme'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 12: CONSIDER SPOTLIGHT (watchlist - not full GREEN)
    # -------------------------------------------------------------------------
    'consider_spotlight': [
        {
            'id': 'consider_1',
            'text': "🟡 On my radar: ${{TICKER}}\n\nCleared 4 of 5 gates. Waiting for final confirmation.\n\nEnded the week at ${{PRICE}}.\n\nFull watchlist:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'price'],
        },
        {
            'id': 'consider_2',
            'text': "Watchlist update:\n\n${{TICKER}} — almost there.\n\nFriday's close: ${{PRICE}}\n\nOne more gate to clear. Patience.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'price'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 13: SELF QUOTE (milestone celebrations)
    # -------------------------------------------------------------------------
    'self_quote': [
        {
            'id': 'quote_1',
            'text': "Remember when I posted about ${{TICKER}} at ${{OLD_PRICE}}?\n\nFriday's close: ${{CURRENT}}\n\n+{{PNL}}% since the call.\n\nThat's what following the system looks like.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'old_price', 'current', 'pnl'],
            'min_pnl': 25.0,
        },
        {
            'id': 'quote_2',
            'text': "${{TICKER}} hit a milestone.\n\n+{{PNL}}% since entry.\n\nThese are the setups the 5-Gate System is built to find.\n\nHow it works:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'pnl'],
            'min_pnl': 25.0,
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 14: NEWSLETTER CTA
    # -------------------------------------------------------------------------
    'newsletter': [
        {
            'id': 'news_1',
            'text': "New newsletter just dropped.\n\nThis week (based on Friday's scan):\n• {{NUM_SIGNALS}} new GREEN signals\n• Updated portfolio status\n• Theme rotation analysis\n\nRead it here 👇\n{{SUBSTACK_URL}}",
            'requires': ['num_signals'],
        },
        {
            'id': 'news_2',
            'text': "Saturday morning reading:\n\nFresh signals from Friday's close.\nFull breakdown. No fluff.\n\n{{SUBSTACK_URL}}",
            'requires': [],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 15: WEEKLY RECAP
    # -------------------------------------------------------------------------
    'weekly_recap': [
        {
            'id': 'recap_1',
            'text': "🟢 GREEN signals this week:\n\n{{SIGNAL_LIST}}\n\nMeanwhile... SPY: {{SPY_PCT}}%\n\nThe 5-Gate System continues to find asymmetric setups.\n\n{{SUBSTACK_URL}}",
            'requires': ['signal_list', 'spy_pct'],
        },
        {
            'id': 'recap_2',
            'text': "Week in review:\n\n✅ {{NUM_SIGNALS}} new signals\n📈 Top performer: ${{TOP_TICKER}} (+{{TOP_PNL}}%)\n🎯 Win rate holding steady\n\nFull recap:\n{{SUBSTACK_URL}}",
            'requires': ['num_signals', 'top_ticker', 'top_pnl'],
        },
    ],

    # -------------------------------------------------------------------------
    # CATEGORY 16: EARLY MOVERS
    # -------------------------------------------------------------------------
    'early_movers': [
        {
            'id': 'early_1',
            'text': "Early mover alert:\n\n${{TICKER}} already up +{{PNL}}% since Friday's GREEN signal.\n\nEntry: ${{ENTRY}}\nCurrent: ${{CURRENT}}\n\nMore setups like this:\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'entry', 'current', 'pnl'],
        },
        {
            'id': 'early_2',
            'text': "New signal, quick start:\n\n${{TICKER}}: +{{PNL}}% already\n\nThis is why I scan on Fridays and post Saturdays.\n\n{{SUBSTACK_URL}}",
            'requires': ['ticker', 'pnl'],
        },
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE TRACKING - Ensure variety across the week
# ═══════════════════════════════════════════════════════════════════════════════

class TemplateTracker:
    """Track used templates to ensure variety."""
    
    def __init__(self):
        self.used_templates = {}  # category -> set of template_ids
        self.used_tickers = {}    # ticker -> count
        
    def mark_used(self, category: str, template_id: str, ticker: str = None):
        """Mark a template as used."""
        if category not in self.used_templates:
            self.used_templates[category] = set()
        self.used_templates[category].add(template_id)
        
        if ticker:
            self.used_tickers[ticker] = self.used_tickers.get(ticker, 0) + 1
    
    def get_unused_templates(self, category: str) -> List[dict]:
        """Get templates not yet used for a category."""
        if category not in AUTHENTIC_TEMPLATES:
            return []
        
        used = self.used_templates.get(category, set())
        return [t for t in AUTHENTIC_TEMPLATES[category] if t['id'] not in used]
    
    def is_ticker_overused(self, ticker: str, max_count: int = 4) -> bool:
        """Check if ticker has been mentioned too many times."""
        return self.used_tickers.get(ticker, 0) >= max_count
    
    def reset(self):
        """Reset for new week."""
        self.used_templates = {}
        self.used_tickers = {}


# Global tracker instance
template_tracker = TemplateTracker()

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
    template_id: Optional[str] = None
    generation_method: str = "template"  # template, claude, hybrid

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeeklyContent:
    """All content for the week."""
    pass_signals: List[Dict] = field(default_factory=list)
    consider_signals: List[Dict] = field(default_factory=list)
    caution_signals: List[Dict] = field(default_factory=list)
    sell_signals: List[Dict] = field(default_factory=list)
    open_positions: List[Dict] = field(default_factory=list)
    closed_trades: List[Dict] = field(default_factory=list)
    prime_themes: List[Dict] = field(default_factory=list)
    investable_themes: List[Dict] = field(default_factory=list)
    selective_themes: List[Dict] = field(default_factory=list)
    avoid_themes: List[Dict] = field(default_factory=list)
    scan_date: str = ""
    chart_manifest: Dict[str, str] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_tweet_char_count(text: str) -> int:
    """Calculate Twitter character count (handles Unicode)."""
    count = 0
    for char in text:
        if ord(char) > 0xFFFF:
            count += 2
        else:
            count += 1
    return count


def validate_tweet_length(text: str, max_length: int = 280) -> bool:
    """Check if tweet is within character limit."""
    return get_tweet_char_count(text) <= max_length


def truncate_tweet(tweet_text: str, max_length: int = 280) -> str:
    """Truncate tweet to fit within limit, preserving URL if present."""
    if validate_tweet_length(tweet_text, max_length):
        return tweet_text
    
    url_pattern = r'https?://\S+$'
    match = re.search(url_pattern, tweet_text)
    
    if match:
        url = match.group()
        text_without_url = tweet_text[:match.start()].rstrip()
        url_length = get_tweet_char_count(url)
        available = max_length - url_length - 4
        
        truncated = ""
        count = 0
        for char in text_without_url:
            char_len = 2 if ord(char) > 0xFFFF else 1
            if count + char_len > available:
                break
            truncated += char
            count += char_len
        
        return f"{truncated.rstrip()}... {url}"
    else:
        truncated = ""
        count = 0
        for char in tweet_text:
            char_len = 2 if ord(char) > 0xFFFF else 1
            if count + char_len > (max_length - 3):
                break
            truncated += char
            count += char_len
        return f"{truncated.rstrip()}..."


def calculate_days_held(entry_date: str) -> int:
    """Calculate days held from entry date to today."""
    if not entry_date:
        return 0
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        days = (datetime.now() - entry_dt).days
        return max(1, days)  # Minimum 1 day
    except ValueError:
        return 0


def format_weeks_held(days: int) -> str:
    """Format days held as weeks for display."""
    if days < 7:
        return f"{days} days" if days != 1 else "1 day"
    weeks = days // 7
    return f"{weeks} weeks" if weeks != 1 else "1 week"


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE POPULATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def populate_template(template: str, data: dict) -> str:
    """
    Replace {{PLACEHOLDER}} markers with actual data values.
    
    Args:
        template: Template string with {{PLACEHOLDER}} markers
        data: Dictionary of values to substitute
        
    Returns:
        Populated template string
    """
    result = template
    
    # Standard replacements
    for key, value in data.items():
        placeholder = "{{" + key.upper() + "}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    
    # Always replace SUBSTACK_URL
    result = result.replace("{{SUBSTACK_URL}}", SUBSTACK_URL)
    
    # Apply random variation to weekly close phrasing (30% chance)
    result = maybe_vary_phrase(result, probability=0.3)
    
    return result


def build_template_data(category: str, content: WeeklyContent, 
                        template: dict = None) -> Optional[dict]:
    """
    Build data dictionary for populating a template.
    
    Returns None if required data is unavailable.
    Enforces 25% threshold for position updates and closed trades.
    """
    data = {}
    
    # -------------------------------------------------------------------------
    # BUY SIGNAL
    # -------------------------------------------------------------------------
    if category == 'buy_signal':
        if not content.pass_signals:
            return None
        
        # Single signal format
        if template and 'ticker' in template.get('requires', []):
            signal = content.pass_signals[0]
            data['ticker'] = signal.get('ticker', '')
            data['price'] = f"{signal.get('current_price', signal.get('price', 0)):.2f}"
            data['conviction'] = signal.get('conviction', 4)
            data['conviction_text'] = get_conviction_text(signal.get('conviction', 4))
            data['theme'] = signal.get('theme', 'Momentum')
        
        # Multi-signal list format
        if template and 'signal_list' in template.get('requires', []):
            signals = content.pass_signals[:5]
            lines = []
            for s in signals:
                conv_text = get_conviction_text(s.get('conviction', 4))
                lines.append(f"🟢 ${s.get('ticker', '')} — {conv_text}")
            data['signal_list'] = "\n".join(lines)
        
        data['num_signals'] = len(content.pass_signals)
        
    # -------------------------------------------------------------------------
    # TOP PERFORMERS (25%+ only)
    # -------------------------------------------------------------------------
    elif category == 'top_performers':
        # Filter to 25%+ winners only
        min_pnl = TEMPLATE_THRESHOLDS['min_pnl_for_position_update']
        winners = [p for p in content.open_positions 
                   if p.get('pnl_pct', 0) >= min_pnl]
        
        if not winners:
            return None  # No qualifying winners
        
        winners = sorted(winners, key=lambda x: x.get('pnl_pct', 0), reverse=True)
        
        # Build winners list
        lines = []
        for w in winners[:5]:
            ticker = w.get('ticker', '')
            pnl = w.get('pnl_pct', 0)
            days = calculate_days_held(w.get('entry_date', ''))
            period = format_weeks_held(days)
            lines.append(f"${ticker}: +{pnl:.1f}% ({period})")
        data['winners_list'] = "\n".join(lines)
        
        # Single winner data for specific templates
        top = winners[0]
        data['ticker'] = top.get('ticker', '')
        data['entry'] = f"{top.get('entry_price', 0):.2f}"
        data['current'] = f"{top.get('current_price', 0):.2f}"
        data['pnl'] = f"{top.get('pnl_pct', 0):.1f}"
        data['weeks_held'] = format_weeks_held(calculate_days_held(top.get('entry_date', '')))
        data['theme'] = top.get('theme', 'Momentum')
        
    # -------------------------------------------------------------------------
    # CLOSED TRADE (25%+ only)
    # -------------------------------------------------------------------------
    elif category == 'closed_trade':
        # Filter to 25%+ closed winners only
        min_pnl = TEMPLATE_THRESHOLDS['min_pnl_for_closed_win']
        closed_winners = []
        
        for t in content.closed_trades:
            entry = t.get('entry_price', 0)
            exit_p = t.get('exit_price', t.get('current_price', 0))
            if entry > 0:
                pnl = ((exit_p - entry) / entry) * 100
                if pnl >= min_pnl:
                    t['calculated_pnl'] = pnl
                    closed_winners.append(t)
        
        if not closed_winners:
            return None
        
        trade = closed_winners[0]
        data['ticker'] = trade.get('ticker', '')
        data['entry'] = f"{trade.get('entry_price', 0):.2f}"
        data['exit'] = f"{trade.get('exit_price', trade.get('current_price', 0)):.2f}"
        data['pnl'] = f"{trade.get('calculated_pnl', 0):.1f}"
        
        days = calculate_days_held(trade.get('entry_date', ''))
        data['weeks_held'] = format_weeks_held(days)
        
    # -------------------------------------------------------------------------
    # SELL SIGNAL (neutral - no P&L)
    # -------------------------------------------------------------------------
    elif category == 'sell_signal':
        if not content.sell_signals:
            return None
        
        signal = content.sell_signals[0]
        data['ticker'] = signal.get('ticker', '')
        data['theme'] = signal.get('theme', 'Sector')
        
    # -------------------------------------------------------------------------
    # THEME HOT
    # -------------------------------------------------------------------------
    elif category == 'theme_hot':
        hot_themes = content.prime_themes + content.investable_themes
        if not hot_themes:
            return None
        
        theme = hot_themes[0]
        data['theme'] = theme.get('name', theme.get('theme', 'Momentum'))
        
        # Get tickers from this theme OR from pass_signals if no theme match
        theme_name = data['theme'].lower()
        theme_tickers = [p.get('ticker', '') for p in content.open_positions 
                        if theme_name in p.get('theme', '').lower()]
        
        # If not enough tickers from positions, use pass_signals
        if len(theme_tickers) < 3 and content.pass_signals:
            signal_tickers = [s.get('ticker', '') for s in content.pass_signals 
                             if theme_name in s.get('theme', '').lower()]
            theme_tickers = list(set(theme_tickers + signal_tickers))
        
        # If still not enough, grab top signals regardless of theme
        if len(theme_tickers) < 3 and content.pass_signals:
            for s in content.pass_signals:
                if s.get('ticker') not in theme_tickers:
                    theme_tickers.append(s.get('ticker', ''))
                if len(theme_tickers) >= 3:
                    break
        
        # Ensure we have unique tickers
        unique_tickers = list(dict.fromkeys(theme_tickers))[:3]
        
        if len(unique_tickers) >= 3:
            data['ticker1'] = unique_tickers[0]
            data['ticker2'] = unique_tickers[1]
            data['ticker3'] = unique_tickers[2]
        elif len(unique_tickers) == 2:
            data['ticker1'] = unique_tickers[0]
            data['ticker2'] = unique_tickers[1]
            data['ticker3'] = unique_tickers[0]  # Repeat first if only 2
        elif len(unique_tickers) == 1:
            # Only one ticker - skip templates requiring 3 tickers
            pass
            
    # -------------------------------------------------------------------------
    # THEME COLD
    # -------------------------------------------------------------------------
    elif category == 'theme_cold':
        cold_themes = content.selective_themes + content.avoid_themes
        if not cold_themes:
            return None
        
        data['cold_theme'] = cold_themes[0].get('name', cold_themes[0].get('theme', 'Sector'))
        
        hot_themes = content.prime_themes + content.investable_themes
        if hot_themes:
            data['hot_theme'] = hot_themes[0].get('name', hot_themes[0].get('theme', 'Momentum'))
        else:
            data['hot_theme'] = 'other sectors'
            
    # -------------------------------------------------------------------------
    # FUNNEL GRAPHIC
    # -------------------------------------------------------------------------
    elif category == 'funnel_graphic':
        # Use scan stats if available
        data['total'] = '200+'
        data['gate1'] = '~150'
        data['gate2'] = '~80'
        data['gate3'] = '~40'
        data['gate4'] = '~15'
        data['final'] = str(len(content.pass_signals)) if content.pass_signals else '5'
        
    # -------------------------------------------------------------------------
    # BEAT SPY
    # -------------------------------------------------------------------------
    elif category == 'beat_spy':
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                spy_data = calculate_portfolio_vs_spy(content.open_positions)
                if spy_data:
                    data['spy_pct'] = f"{spy_data.get('spy_return', 0):+.1f}"
                    data['our_pct'] = f"{spy_data.get('portfolio_return', 0):.1f}"
                else:
                    return None
            except:
                return None
        else:
            return None
            
    # -------------------------------------------------------------------------
    # CONSIDER SPOTLIGHT
    # -------------------------------------------------------------------------
    elif category == 'consider_spotlight':
        if not content.consider_signals:
            return None
        
        signal = content.consider_signals[0]
        data['ticker'] = signal.get('ticker', '')
        data['price'] = f"{signal.get('current_price', signal.get('price', 0)):.2f}"
        
    # -------------------------------------------------------------------------
    # SELF QUOTE (milestone - 25%+ only)
    # -------------------------------------------------------------------------
    elif category == 'self_quote':
        # Get uncelebrated wins from tracker
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                wins = get_uncelebrated_wins()
                if wins:
                    win = wins[0]
                    data['ticker'] = win.get('ticker', '')
                    data['old_price'] = f"{win.get('entry_price', 0):.2f}"
                    data['current'] = f"{win.get('current_price', 0):.2f}"
                    data['pnl'] = f"{win.get('pnl_pct', 0):.1f}"
                else:
                    return None
            except:
                return None
        else:
            return None
            
    # -------------------------------------------------------------------------
    # NEWSLETTER
    # -------------------------------------------------------------------------
    elif category == 'newsletter':
        data['num_signals'] = len(content.pass_signals)
        
    # -------------------------------------------------------------------------
    # WEEKLY RECAP
    # -------------------------------------------------------------------------
    elif category == 'weekly_recap':
        if content.pass_signals:
            lines = []
            for s in content.pass_signals[:5]:
                conv_text = get_conviction_text(s.get('conviction', 4))
                lines.append(f"${s.get('ticker', '')} — {conv_text}")
            data['signal_list'] = "\n".join(lines)
        
        data['num_signals'] = len(content.pass_signals)
        
        # SPY comparison
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                spy_data = calculate_portfolio_vs_spy(content.open_positions)
                if spy_data:
                    data['spy_pct'] = f"{spy_data.get('spy_return', 0):+.1f}"
            except:
                data['spy_pct'] = "flat"
        else:
            data['spy_pct'] = "N/A"
        
        # Top performer
        winners = sorted(content.open_positions, 
                        key=lambda x: x.get('pnl_pct', 0), reverse=True)
        if winners:
            data['top_ticker'] = winners[0].get('ticker', '')
            data['top_pnl'] = f"{winners[0].get('pnl_pct', 0):.1f}"
            
    # -------------------------------------------------------------------------
    # EARLY MOVERS
    # -------------------------------------------------------------------------
    elif category == 'early_movers':
        threshold = TEMPLATE_THRESHOLDS['early_mover_threshold']
        early = [p for p in content.open_positions 
                 if p.get('pnl_pct', 0) >= threshold 
                 and calculate_days_held(p.get('entry_date', '')) <= 14]
        
        if not early:
            return None
        
        mover = early[0]
        data['ticker'] = mover.get('ticker', '')
        data['entry'] = f"{mover.get('entry_price', 0):.2f}"
        data['current'] = f"{mover.get('current_price', 0):.2f}"
        data['pnl'] = f"{mover.get('pnl_pct', 0):.1f}"
        
    # -------------------------------------------------------------------------
    # POWER HOUR
    # -------------------------------------------------------------------------
    elif category == 'power_hour':
        hot_themes = content.prime_themes + content.investable_themes
        if hot_themes:
            data['theme'] = hot_themes[0].get('name', hot_themes[0].get('theme', 'Momentum'))
        else:
            data['theme'] = 'momentum names'
            
    # -------------------------------------------------------------------------
    # EDUCATIONAL / ENGAGEMENT (no data required)
    # -------------------------------------------------------------------------
    elif category in ['educational', 'engagement']:
        pass  # These templates don't need data
        
    return data


def select_and_populate_template(category: str, content: WeeklyContent,
                                  account: str = 'account_1') -> Optional[dict]:
    """
    Select an unused template and populate it with data.
    
    Args:
        category: Tweet category
        content: WeeklyContent with scanner data
        account: Which account (for variations)
        
    Returns:
        Dict with populated tweet or None if no valid template/data
    """
    # Get unused templates for this category
    available = template_tracker.get_unused_templates(category)
    
    if not available:
        # All templates used - reset and try again
        if category in AUTHENTIC_TEMPLATES:
            available = AUTHENTIC_TEMPLATES[category]
        else:
            return None
    
    # Shuffle for variety
    random.shuffle(available)
    
    for template in available:
        # Check min_pnl requirement
        min_pnl = template.get('min_pnl', 0)
        
        # Build data for this template
        data = build_template_data(category, content, template)
        
        if data is None:
            continue  # Data requirements not met
        
        # Get template text (with account variation if available)
        if account != 'account_1' and 'account_variations' in template:
            text = template['account_variations'].get(account, template['text'])
        else:
            text = template['text']
        
        # Populate template
        populated = populate_template(text, data)
        
        # Validate length
        if not validate_tweet_length(populated):
            populated = truncate_tweet(populated)
        
        # Validate content
        is_valid, violations = validate_content(populated)
        if not is_valid:
            print(f"  ⚠️ Template {template['id']} has violations: {violations}")
            continue
        
        # Mark as used
        template_tracker.mark_used(category, template['id'], data.get('ticker'))
        
        return {
            'category': category,
            'text': populated,
            'ticker': data.get('ticker'),
            'theme': data.get('theme'),
            'template_id': template['id'],
            'template_data': data,
            'generation_method': 'template'
        }
    
    return None  # No valid template found


def get_fallback_category(original_category: str, content: WeeklyContent) -> str:
    """
    Get fallback category when original can't be populated.
    
    When no 25%+ winners exist, substitute hot theme or engagement.
    """
    fallback_map = {
        'top_performers': 'theme_hot',
        'closed_trade': 'theme_hot',
        'self_quote': 'consider_spotlight',
        'beat_spy': 'engagement',
        'early_movers': 'theme_hot',
        'consider_spotlight': 'theme_hot',
    }
    
    fallback = fallback_map.get(original_category, 'engagement')
    
    # Check if fallback has data
    if fallback == 'theme_hot':
        if not (content.prime_themes or content.investable_themes):
            return 'engagement'
    elif fallback == 'consider_spotlight':
        if not content.consider_signals:
            return 'engagement'
    
    return fallback


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE API GENERATION (Fallback)
# ═══════════════════════════════════════════════════════════════════════════════

TWEET_SYSTEM_PROMPT = """You are a financial content writer for Sterling Signals, a momentum trading newsletter on Substack targeting US active investors.

Your task is to write engaging tweets for X/Twitter that:
1. Highlight trading signals, themes, and market insights
2. Drive engagement and newsletter subscriptions
3. Include relevant $TICKER cashtags
4. Stay under 280 characters
5. Use emojis sparingly but effectively

CRITICAL TERMINOLOGY:
- Use 🟢 GREEN signal for BUY signals (not TEAL)
- Use 🔴 RED signal for SELL signals (not purple)
- Always reference "Friday's close" or "as of the latest weekly close" for prices
- Never mention internal terms: HMA, Banker, BoS, RSI, MACD, Tier 1/2/3

STYLE:
- Confident but not arrogant
- Data-driven with specific numbers
- Authentic voice, not corporate marketing
- Always include link to sterlingsignals.substack.com

25% RULE: Only mention entry prices or specific P&L for positions that are up 25% or more. For losers or small winners, use neutral language without numbers."""


def generate_claude_tweet(client, category: str, content: WeeklyContent) -> Optional[dict]:
    """
    Generate a tweet using Claude API as fallback.
    
    Used when templates can't be populated with available data.
    """
    # Build context based on category
    context_parts = [f"Generate 1 tweet for category: {category}"]
    
    if category == 'buy_signal' and content.pass_signals:
        signals = content.pass_signals[:3]
        context_parts.append(f"\nGREEN signals this week:\n{json.dumps(signals, indent=2)}")
        
    elif category == 'top_performers':
        winners = [p for p in content.open_positions if p.get('pnl_pct', 0) >= 25]
        if winners:
            context_parts.append(f"\nTop performers (25%+):\n{json.dumps(winners[:3], indent=2)}")
        else:
            context_parts.append("\nNo 25%+ winners. Generate a theme_hot tweet instead.")
            
    elif category == 'theme_hot':
        themes = content.prime_themes + content.investable_themes
        if themes:
            context_parts.append(f"\nHot themes:\n{json.dumps(themes[:2], indent=2)}")
            
    elif category == 'sell_signal' and content.sell_signals:
        context_parts.append(f"\nSell signal (use neutral language, NO P&L):\n{json.dumps(content.sell_signals[0], indent=2)}")
    
    context_parts.append(f"\nAlways end with: sterlingsignals.substack.com")
    context_parts.append("\nReturn ONLY the tweet text, no JSON or explanations.")
    
    context = "\n".join(context_parts)
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=TWEET_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}]
        )
        
        text = response.content[0].text.strip()
        
        # Clean up any markdown or quotes
        text = text.strip('"\'`')
        
        if validate_tweet_length(text):
            return {
                'category': category,
                'text': text,
                'ticker': None,
                'theme': None,
                'template_id': None,
                'generation_method': 'claude'
            }
        else:
            return {
                'category': category,
                'text': truncate_tweet(text),
                'ticker': None,
                'theme': None,
                'template_id': None,
                'generation_method': 'claude'
            }
            
    except Exception as e:
        print(f"  ✗ Claude API error for {category}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# HYBRID GENERATION - Templates with Claude fallback
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tweet_hybrid(client, category: str, content: WeeklyContent,
                          account: str = 'account_1') -> dict:
    """
    Generate a tweet using hybrid approach:
    1. Try template first
    2. If no valid template, try fallback category template
    3. If still no template, use Claude API
    
    Returns tweet dict with generation_method field.
    """
    # Step 1: Try template for original category
    tweet = select_and_populate_template(category, content, account)
    
    if tweet:
        return tweet
    
    # Step 2: Try fallback category template
    fallback = get_fallback_category(category, content)
    if fallback != category:
        tweet = select_and_populate_template(fallback, content, account)
        if tweet:
            tweet['original_category'] = category
            tweet['category'] = fallback  # Update to actual category used
            return tweet
    
    # Step 3: Claude API fallback
    if client:
        tweet = generate_claude_tweet(client, category, content)
        if tweet:
            return tweet
    
    # Final fallback: placeholder
    return {
        'category': category,
        'text': f"[Placeholder: {category} - insufficient data for template]",
        'ticker': None,
        'theme': None,
        'template_id': None,
        'generation_method': 'placeholder'
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON MODE - Generate Claude, Template, and Hybrid versions
# ═══════════════════════════════════════════════════════════════════════════════

def generate_comparison_output(content: WeeklyContent, client) -> dict:
    """
    Generate comparison output showing Claude vs Templates vs Hybrid.
    
    Returns dict with all three versions for each scheduled slot.
    """
    comparison = {
        'generated_at': datetime.now().isoformat(),
        'scan_date': content.scan_date,
        'comparisons': []
    }
    
    # Sample of key categories to compare
    test_categories = [
        'buy_signal',
        'top_performers',
        'theme_hot',
        'sell_signal',
        'educational',
        'engagement',
        'beat_spy',
        'funnel_graphic',
    ]
    
    for category in test_categories:
        entry = {
            'category': category,
            'template_version': None,
            'claude_version': None,
            'hybrid_version': None,
        }
        
        # Template version
        template_tweet = select_and_populate_template(category, content)
        if template_tweet:
            entry['template_version'] = {
                'text': template_tweet['text'],
                'template_id': template_tweet.get('template_id'),
                'char_count': get_tweet_char_count(template_tweet['text'])
            }
        
        # Claude version
        claude_tweet = generate_claude_tweet(client, category, content)
        if claude_tweet:
            entry['claude_version'] = {
                'text': claude_tweet['text'],
                'char_count': get_tweet_char_count(claude_tweet['text'])
            }
        
        # Hybrid version (reset tracker to get fresh selection)
        template_tracker.reset()
        hybrid_tweet = generate_tweet_hybrid(client, category, content)
        entry['hybrid_version'] = {
            'text': hybrid_tweet['text'],
            'method': hybrid_tweet.get('generation_method'),
            'template_id': hybrid_tweet.get('template_id'),
            'char_count': get_tweet_char_count(hybrid_tweet['text'])
        }
        
        comparison['comparisons'].append(entry)
    
    return comparison


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all_tweets(content: WeeklyContent, mock: bool = False,
                        cold_streak_active: bool = False) -> List:
    """
    Generate all tweets for the week using hybrid approach.
    
    Args:
        content: WeeklyContent with all scanner data
        mock: If True, generate mock tweets without API
        cold_streak_active: If True, reduce position-focused content
    """
    if mock:
        return generate_mock_tweets()
    
    # Initialize Claude client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = None
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        print("  ⚠️ No ANTHROPIC_API_KEY - template-only mode")
    
    # Reset template tracker for fresh week
    template_tracker.reset()
    
    all_content = []
    
    # Check safeguards
    can_post_beat_spy = False
    can_post_top_performers = False
    uncelebrated_wins = []
    
    if SIGNAL_TRACKER_AVAILABLE and not cold_streak_active:
        try:
            can_post_beat_spy = should_post_beat_spy(content.open_positions)
            can_post_top_performers = has_enough_wins(content.open_positions)
            uncelebrated_wins = get_uncelebrated_wins()
        except Exception as e:
            print(f"  ⚠️ Safeguard check failed: {e}")
    
    if cold_streak_active:
        print("  🥶 COLD STREAK ACTIVE - Reducing position-focused content")
        can_post_beat_spy = False
        can_post_top_performers = False
        uncelebrated_wins = []
    
    # Dynamic category selection
    beat_spy_or_fallback = "beat_spy" if can_post_beat_spy else "engagement"
    top_performers_or_fallback = "top_performers" if can_post_top_performers else "theme_hot"
    self_quote_or_fallback = "self_quote" if uncelebrated_wins else (
        "consider_spotlight" if content.consider_signals else "theme_hot"
    )
    
    # Weekly schedule
    categories_schedule = [
        # Saturday: Newsletter day
        ("Saturday", 1, top_performers_or_fallback),
        ("Saturday", 2, "buy_signal" if content.pass_signals else "funnel_graphic"),
        ("Saturday", 3, "theme_hot"),
        ("Saturday", 4, "funnel_graphic"),
        ("Saturday", 5, "engagement"),
        
        # Sunday: All signals + watchlist
        ("Sunday", 1, "buy_signal" if content.pass_signals else "funnel_graphic"),
        ("Sunday", 2, "consider_spotlight" if content.consider_signals else "theme_hot"),
        ("Sunday", 3, beat_spy_or_fallback),
        ("Sunday", 4, "engagement"),
        ("Sunday", 5, "educational"),

        # Monday: Week kickoff
        ("Monday", 1, "theme_hot"),
        ("Monday", 2, self_quote_or_fallback),
        ("Monday", 3, "power_hour"),
        ("Monday", 4, "engagement"),
        ("Monday", 5, "educational"),

        # Tuesday: Education
        ("Tuesday", 1, "early_movers" if content.open_positions else "theme_hot"),
        ("Tuesday", 2, "theme_hot"),
        ("Tuesday", 3, "power_hour"),
        ("Tuesday", 4, "educational"),
        ("Tuesday", 5, "engagement"),

        # Wednesday: Watchlist + education
        ("Wednesday", 1, "consider_spotlight" if content.consider_signals else "theme_hot"),
        ("Wednesday", 2, "theme_hot"),
        ("Wednesday", 3, "power_hour"),
        ("Wednesday", 4, "engagement"),
        ("Wednesday", 5, "educational"),

        # Thursday: Alpha + wins
        ("Thursday", 1, beat_spy_or_fallback),
        ("Thursday", 2, self_quote_or_fallback),
        ("Thursday", 3, "power_hour"),
        ("Thursday", 4, "educational"),
        ("Thursday", 5, "engagement"),

        # Friday: Scanner tease
        ("Friday", 1, "buy_signal" if content.pass_signals else "theme_hot"),
        ("Friday", 2, "funnel_graphic"),
        ("Friday", 3, "power_hour"),
        ("Friday", 4, "newsletter"),
        ("Friday", 5, "engagement"),
    ]
    
    # Calculate dates
    today = datetime.now()
    current_weekday = today.weekday()
    
    if current_weekday == 4:  # Friday
        days_until_saturday = 1
    elif current_weekday == 5:  # Saturday
        days_until_saturday = 0
    elif current_weekday == 6:  # Sunday
        days_until_saturday = -1
    else:
        days_until_saturday = 5 - current_weekday
    
    start_date = today + timedelta(days=days_until_saturday)
    
    day_offset_from_saturday = {
        "Saturday": 0, "Sunday": 1, "Monday": 2, "Tuesday": 3,
        "Wednesday": 4, "Thursday": 5, "Friday": 6
    }
    
    print("\n  🤖 Generating tweets (hybrid: templates + Claude fallback)...")
    
    for day, slot, category in categories_schedule:
        day_offset = day_offset_from_saturday[day]
        scheduled_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        # Generate tweet using hybrid approach
        tweet_data = generate_tweet_hybrid(client, category, content)
        
        # Find chart if ticker present
        image_path = None
        ticker = tweet_data.get('ticker')
        if ticker and ticker in content.chart_manifest:
            image_path = content.chart_manifest[ticker]
        
        tweet = Tweet(
            id=f"{day.lower()}_{slot}_{category}",
            day=day,
            slot=slot,
            category=tweet_data.get('category', category),
            text=tweet_data.get('text', ''),
            ticker=ticker,
            theme=tweet_data.get('theme'),
            image_path=image_path,
            scheduled_date=scheduled_date,
            template_id=tweet_data.get('template_id'),
            generation_method=tweet_data.get('generation_method', 'unknown')
        )
        
        all_content.append(tweet)
        
        method_emoji = {
            'template': '📝',
            'claude': '🤖',
            'hybrid': '🔄',
            'placeholder': '⚠️'
        }.get(tweet.generation_method, '❓')
        
        print(f"    {method_emoji} {day} slot {slot}: {category}")
    
    # Validation
    if MARKETING_VOCABULARY_AVAILABLE:
        print("\n  🔍 Validating content...")
        total, violations = validate_all_tweets(all_content)
        if violations > 0:
            print(f"  ⚠️ {violations}/{total} tweets have violations")
        else:
            print(f"  ✅ All {total} tweets passed validation")
    
    return all_content


def generate_mock_tweets() -> List:
    """Generate mock tweets for testing."""
    tweets = []
    today = datetime.now()
    
    for day in DAYS:
        for slot in [1, 2, 3, 4]:
            tweet = Tweet(
                id=f"{day.lower()}_{slot}_mock",
                day=day,
                slot=slot,
                category="mock",
                text=f"[MOCK] {day} slot {slot} placeholder tweet",
                scheduled_date=today.strftime("%Y-%m-%d"),
                generation_method="mock"
            )
            tweets.append(tweet)
    
    return tweets


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_briefing_data(briefing_path: Path) -> WeeklyContent:
    """Load data from newsletter briefing markdown."""
    content = WeeklyContent()
    
    if not briefing_path.exists():
        print(f"  ⚠️ Briefing not found: {briefing_path}")
        return content
    
    try:
        from grok_prompts_generator import parse_briefing_markdown
        data = parse_briefing_markdown(briefing_path)
        
        content.pass_signals = data.pass_signals
        content.consider_signals = data.caution_signals  # Legacy naming
        content.sell_signals = data.sell_signals
        content.open_positions = data.open_positions
        content.prime_themes = data.prime_themes
        content.investable_themes = data.investable_themes
        content.selective_themes = data.selective_themes
        content.avoid_themes = data.avoid_themes
        content.scan_date = data.scan_date
        
    except ImportError:
        print("  ⚠️ Could not import grok_prompts_generator")
    
    # Load live portfolio data
    portfolio_file = TRADES_DIR / "portfolio.csv"
    if portfolio_file.exists():
        try:
            from portfolio_manager import PortfolioManager
            pm = PortfolioManager()
            pm.update_prices()
            
            content.open_positions = []
            for trade in pm.get_open_positions():
                content.open_positions.append({
                    'ticker': trade.ticker,
                    'entry_date': trade.entry_date,
                    'entry_price': trade.entry_price,
                    'current_price': trade.current_price,
                    'pnl_pct': trade.pnl_pct,
                    'theme': trade.theme,
                    'conviction': trade.conviction,
                })
            
            for trade in pm.get_closed_trades():
                content.closed_trades.append({
                    'ticker': trade.ticker,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'exit_date': trade.exit_date,
                    'status': trade.status,
                })
                
        except ImportError:
            pass
    
    return content


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_tweets(tweets: List, output_dir: Path) -> Path:
    """Save tweets to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to dicts
    queue = []
    for item in tweets:
        if hasattr(item, 'to_dict'):
            queue.append(item.to_dict())
        else:
            queue.append(item)
    
    # Save main queue
    queue_file = output_dir / "content_queue.json"
    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)
    
    # Save dated backup
    date_str = datetime.now().strftime("%Y%m%d")
    backup_file = output_dir / f"tweets_{date_str}.json"
    with open(backup_file, 'w') as f:
        json.dump(queue, f, indent=2)
    
    return queue_file


def print_summary(tweets: List):
    """Print generation summary."""
    print("\n  📊 Generation Summary:")
    print("  " + "─" * 50)
    
    # Count by method
    methods = {}
    for t in tweets:
        method = t.generation_method if hasattr(t, 'generation_method') else t.get('generation_method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    for method, count in sorted(methods.items()):
        emoji = {'template': '📝', 'claude': '🤖', 'placeholder': '⚠️'}.get(method, '❓')
        print(f"    {emoji} {method}: {count}")
    
    # Count by category
    print("\n  By category:")
    categories = {}
    for t in tweets:
        cat = t.category if hasattr(t, 'category') else t.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    • {cat}: {count}")


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-ACCOUNT VARIATION GENERATION (Claude-powered)
# ═══════════════════════════════════════════════════════════════════════════════

VARIATION_SYSTEM_PROMPT = """You rephrase tweets for the Sterling Signals trading newsletter.

You will receive the ORIGINAL tweet (account 1) and must produce a rephrased version for a
different account. The rephrased tweet must:

1. SAME VOICE — Conversational, personal, casual, first-person. Same personality as the original.
   Use "I", opinions, short punchy sentences, emojis where natural.
2. SAME FACTS — Identical tickers ($TICKER), prices, percentages, dates, URLs. Never change data.
3. DIFFERENT WORDING — Restructure sentences, swap synonyms, reorder points, change the opening
   hook, vary emoji placement. It should read like a different person making the same point in
   their own words — not a copy-paste.
4. COMPLEMENTARY — If the original leads with a question, lead with a statement (or vice versa).
   If the original lists top-down, try bottom-up. The tweets should feel like they complement
   each other when seen side by side, not repeat each other.
5. UNDER 280 CHARACTERS — This is mandatory. Count carefully.

BANNED TERMS (never use): HMA, Banker indicator, Beta >= 1.5, Weekly BoS, Tier 1/2/3,
conviction score, 20% trailing stop, Gatekeeper, RSI, MACD, KDJ, UK ISA, GMT, BST.

Return ONLY the rephrased tweet text. No quotes, no explanation, no JSON."""


def _rephrase_tweet_batch(client, tweets_batch: List[dict], account_label: str) -> List[str]:
    """
    Send a batch of tweets to Claude for rephrasing in a single API call.

    Batches up to 10 tweets per call to balance cost and quality.
    Returns list of rephrased texts in the same order.
    """
    # Build the user prompt with all tweets numbered
    parts = [f"Rephrase each tweet below for {account_label}. "
             f"Return exactly {len(tweets_batch)} rephrased tweets, "
             f"each on its own block separated by\n---\n"
             f"Preserve all $TICKER cashtags, prices, percentages, and URLs exactly.\n"]

    for i, tweet in enumerate(tweets_batch, 1):
        parts.append(f"TWEET {i}:\n{tweet.get('text', '')}\n")

    user_prompt = "\n".join(parts)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=VARIATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw = response.content[0].text.strip()

        # Split on --- separator
        rephrased = [block.strip() for block in raw.split("---") if block.strip()]

        # If Claude returned wrong count, pad or truncate
        if len(rephrased) < len(tweets_batch):
            # Fill missing with originals
            for i in range(len(rephrased), len(tweets_batch)):
                rephrased.append(tweets_batch[i].get('text', ''))
        elif len(rephrased) > len(tweets_batch):
            rephrased = rephrased[:len(tweets_batch)]

        # Strip any leading "TWEET N:" artifacts Claude might have included
        import re as _re
        cleaned = []
        for text in rephrased:
            text = _re.sub(r'^TWEET\s*\d+\s*:\s*', '', text, flags=_re.IGNORECASE).strip()
            text = text.strip('"\'`')
            cleaned.append(text)

        return cleaned

    except Exception as e:
        print(f"    Claude API error during rephrasing: {e}")
        # Fallback: return originals unchanged
        return [t.get('text', '') for t in tweets_batch]


def generate_account_variations(base_queue_path: Path) -> None:
    """
    Generate variation queues for account2 and account3 using Claude to rephrase
    each tweet in the same casual/personal voice with different wording.

    Processes tweets in batches of 10 to minimise API calls (~4 calls per account).
    """
    import time as _time

    with open(base_queue_path, 'r') as f:
        base_queue = json.load(f)

    # Initialise Claude client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ERROR: ANTHROPIC_API_KEY required for variation generation.")
        print("  Falling back to copying main queue for account2/account3.")
        _fallback_copy(base_queue, base_queue_path)
        return

    client = anthropic.Anthropic(api_key=api_key)
    batch_size = 10

    for account_key in ['account2', 'account3']:
        account_config = TWITTER_ACCOUNTS.get(account_key)
        if not account_config:
            print(f"  No config for {account_key}, skipping")
            continue

        account_label = f"Account {account_key[-1]}"
        print(f"\n  Generating variations for {account_label}...")

        variation_queue = []
        rephrased_count = 0

        # Process in batches
        for batch_start in range(0, len(base_queue), batch_size):
            batch = base_queue[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(base_queue) + batch_size - 1) // batch_size
            print(f"    Batch {batch_num}/{total_batches} ({len(batch)} tweets)...")

            rephrased_texts = _rephrase_tweet_batch(client, batch, account_label)

            for tweet, new_text in zip(batch, rephrased_texts):
                varied = dict(tweet)
                varied['account'] = account_key
                if new_text != tweet.get('text', ''):
                    varied['text'] = new_text
                    varied['generation_method'] = 'claude_variation'
                    rephrased_count += 1
                variation_queue.append(varied)

            # Rate limit pause between batches
            if batch_start + batch_size < len(base_queue):
                _time.sleep(2)

        # Rotate slot assignments so accounts post different categories at each time
        variation_queue = _rotate_slots(variation_queue, account_key)

        output_path = base_queue_path.parent / account_config['queue_file']
        with open(output_path, 'w') as f:
            json.dump(variation_queue, f, indent=2)
        print(f"  {account_key}: {len(variation_queue)} tweets "
              f"({rephrased_count} rephrased by Claude, slots rotated) -> {output_path}")


def _rotate_slots(queue: list, account_key: str) -> list:
    """
    Rotate slot assignments within each day so that accounts post different
    categories at the same time.

    Account 1 (main): original order   [1, 2, 3, 4, 5]
    Account 2:        rotate by +2     [3, 4, 5, 1, 2]  (slot 1 gets what was slot 3, etc.)
    Account 3:        rotate by +4     [5, 1, 2, 3, 4]  (slot 1 gets what was slot 5, etc.)

    This means at any given time slot, all 3 accounts post different categories.
    The tweet text/content stays the same — only the slot number and posting time change.
    """
    rotation = {'account2': 2, 'account3': 4}.get(account_key, 0)
    if rotation == 0:
        return queue

    from collections import defaultdict

    # Group tweets by their scheduled day
    by_day = defaultdict(list)
    for tweet in queue:
        day_key = tweet.get('scheduled_date', '') or tweet.get('day', '')
        by_day[day_key].append(tweet)

    rotated = []
    for day_key in sorted(by_day.keys()):
        day_tweets = sorted(by_day[day_key], key=lambda t: t.get('slot', 0))
        n = len(day_tweets)
        if n == 0:
            continue

        # Collect the original slot numbers and IDs in order
        original_slots = [t.get('slot', i + 1) for i, t in enumerate(day_tweets)]
        original_ids = [t.get('id', '') for t in day_tweets]

        # Rotate: tweet at position i gets the slot from position (i + rotation) % n
        for i, tweet in enumerate(day_tweets):
            source_idx = (i + rotation) % n
            tweet['slot'] = original_slots[source_idx]
            # Update the ID to reflect the new slot
            if original_ids[i]:
                parts = original_ids[i].rsplit('_', 2)
                if len(parts) >= 2:
                    # Reconstruct ID with new slot: day_slot_category
                    day_part = tweet.get('day', parts[0]).lower()
                    cat_part = tweet.get('category', parts[-1] if len(parts) > 2 else '')
                    tweet['id'] = f"{day_part}_{tweet['slot']}_{cat_part}"

        rotated.extend(day_tweets)

    return rotated


def _fallback_copy(base_queue: list, base_queue_path: Path) -> None:
    """Copy main queue with rotated slots when Claude API is unavailable."""
    for account_key in ['account2', 'account3']:
        account_config = TWITTER_ACCOUNTS.get(account_key, {})
        queue_file = account_config.get('queue_file')
        if queue_file:
            output_path = base_queue_path.parent / queue_file
            copied = [dict(t, account=account_key) for t in base_queue]
            copied = _rotate_slots(copied, account_key)
            with open(output_path, 'w') as f:
                json.dump(copied, f, indent=2)
            print(f"  {account_key}: {len(copied)} tweets (UNMODIFIED text, slots rotated) -> {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate tweets via hybrid templates + Claude")
    parser.add_argument("--briefing", type=str, help="Path to newsletter briefing")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no API)")
    parser.add_argument("--force", action="store_true", help="Force regeneration")
    parser.add_argument("--compare", action="store_true", help="Generate comparison output")
    parser.add_argument("--generate-variations", action="store_true",
                        help="Generate account2/account3 variation queues from main queue")
    args = parser.parse_args()

    # Handle --generate-variations early (no data loading needed)
    if args.generate_variations:
        print("\n" + "═" * 60)
        print("  GENERATING MULTI-ACCOUNT VARIATIONS")
        print("═" * 60)
        base_path = TRADES_DIR / "content_queue.json"
        if base_path.exists():
            generate_account_variations(base_path)
            print("\n  Done!")
        else:
            print(f"\n  ERROR: Base queue not found: {base_path}")
        print("═" * 60)
        return

    print("\n" + "═" * 60)
    print("  TWEET GENERATOR v2 - Hybrid Templates + Claude")
    print("═" * 60)
    
    # Load data
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
    print(f"     • GREEN signals: {len(content.pass_signals)}")
    print(f"     • Open positions: {len(content.open_positions)}")
    print(f"     • Closed trades: {len(content.closed_trades)}")
    print(f"     • Hot themes: {len(content.prime_themes) + len(content.investable_themes)}")
    
    # Comparison mode
    if args.compare:
        print("\n  🔬 COMPARISON MODE - Generating Claude vs Templates vs Hybrid")
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  ✗ ERROR: ANTHROPIC_API_KEY required for comparison mode")
            return
        
        client = anthropic.Anthropic(api_key=api_key)
        comparison = generate_comparison_output(content, client)
        
        output_dir = Path(args.output) if args.output else TWEETS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        comparison_file = output_dir / "comparison_output.json"
        with open(comparison_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"\n  📁 Comparison saved: {comparison_file}")
        
        # Print preview
        print("\n  Preview:")
        print("  " + "─" * 50)
        for entry in comparison['comparisons']:
            print(f"\n  Category: {entry['category']}")
            
            if entry['template_version']:
                print(f"  📝 TEMPLATE ({entry['template_version']['char_count']} chars):")
                print(f"     {entry['template_version']['text'][:100]}...")
            
            if entry['claude_version']:
                print(f"  🤖 CLAUDE ({entry['claude_version']['char_count']} chars):")
                print(f"     {entry['claude_version']['text'][:100]}...")
            
            print(f"  🔄 HYBRID (method: {entry['hybrid_version']['method']}):")
            print(f"     {entry['hybrid_version']['text'][:100]}...")
        
        print("\n" + "═" * 60)
        return
    
    # Check cold streak
    cold_streak_active = False
    if SIGNAL_TRACKER_AVAILABLE:
        cold_streak = check_cold_streak()
        if cold_streak.get('in_cold_streak'):
            print(f"\n  ⚠️ COLD STREAK: {cold_streak.get('reason')}")
            cold_streak_active = True
    
    # Generate tweets
    tweets = generate_all_tweets(content, mock=args.mock, cold_streak_active=cold_streak_active)
    
    # Save output
    output_dir = Path(args.output) if args.output else TRADES_DIR
    queue_file = save_tweets(tweets, output_dir)
    
    # Print summary
    print_summary(tweets)
    
    print(f"\n  ✅ Generated {len(tweets)} tweets")
    print(f"  📁 Content queue: {queue_file}")
    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
