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
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    MARKETING_THRESHOLDS = {
        'min_win_to_highlight': 15.0,
        'big_win_threshold': 25.0,
        'spy_outperformance_min': 5.0,
        'min_winners_for_top_performers': 2,  # Phase 9: Renamed from min_winners_for_weekly_wins
    }
    # Fallback implementations
    def get_highlight_threshold(days_held: int) -> float:
        if days_held <= 7: return 3.0
        elif days_held <= 14: return 5.0
        elif days_held <= 30: return 10.0
        elif days_held <= 60: return 15.0
        else: return 20.0

    def format_holding_period(days_held: int) -> str:
        if days_held <= 0: return "held"
        elif days_held <= 7: return f"{days_held} days"
        elif days_held <= 30: return f"{days_held // 7} week{'s' if days_held // 7 > 1 else ''}"
        else: return f"{days_held // 30} month{'s' if days_held // 30 > 1 else ''}"

    TIMEFRAME_DISCLAIMERS = {
        'short': 'Returns since signal entry.',
        'medium': 'Total gain since entry, not weekly movement.',
        'long': 'Sterling Signals targets 50-100% returns over 3-8 month holds. Returns shown are total since signal entry.',
    }
    WIN_CATEGORIES = {}


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
TWEETS_DIR = TRADES_DIR / "tweets"
CHARTS_DIR = TRADES_DIR / "charts"

TWEETS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET VALIDATION (MIN-1)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_tweet_length(tweet_text: str) -> bool:
    """
    Validate tweet is under 280 characters.

    Note: Emojis and special characters count as 2 characters on Twitter.

    Args:
        tweet_text: The tweet text to validate

    Returns:
        True if tweet is valid length, False otherwise
    """
    if not tweet_text:
        return True

    # Count characters with Twitter's algorithm (emojis = 2 chars)
    char_count = 0
    for char in tweet_text:
        if ord(char) > 0xFFFF:  # Emoji or special char
            char_count += 2
        else:
            char_count += 1

    return char_count <= 280


def get_tweet_char_count(tweet_text: str) -> int:
    """Get the character count using Twitter's algorithm."""
    if not tweet_text:
        return 0

    char_count = 0
    for char in tweet_text:
        if ord(char) > 0xFFFF:
            char_count += 2
        else:
            char_count += 1

    return char_count


def truncate_tweet(tweet_text: str, max_length: int = 275) -> str:
    """
    Truncate tweet to fit within max_length, preserving URL at end if present.

    Args:
        tweet_text: The tweet text to truncate
        max_length: Maximum character length (default 275 to leave room for ...)

    Returns:
        Truncated tweet text
    """
    if not tweet_text or get_tweet_char_count(tweet_text) <= max_length:
        return tweet_text

    # Check if there's a URL at the end
    url_pattern = r'https?://\S+$'
    match = re.search(url_pattern, tweet_text)

    if match:
        url = match.group()
        text_without_url = tweet_text[:match.start()].rstrip()
        url_length = get_tweet_char_count(url)
        available = max_length - url_length - 4  # 4 for "... "

        # Truncate text portion
        truncated_text = ""
        char_count = 0
        for char in text_without_url:
            char_len = 2 if ord(char) > 0xFFFF else 1
            if char_count + char_len > available:
                break
            truncated_text += char
            char_count += char_len

        return f"{truncated_text.rstrip()}... {url}"
    else:
        # No URL, just truncate
        truncated_text = ""
        char_count = 0
        for char in tweet_text:
            char_len = 2 if ord(char) > 0xFFFF else 1
            if char_count + char_len > (max_length - 3):  # 3 for "..."
                break
            truncated_text += char
            char_count += char_len

        return f"{truncated_text.rstrip()}..."


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER_TODO_v2: PRE-GENERATION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_tweet_before_queue(tweet: dict, existing_tweets: list = None) -> tuple:
    """
    MASTER_TODO_v2: Run all validations before adding tweet to queue.

    This is a CRITICAL safeguard function that ensures no invalid content
    is queued for posting.

    Args:
        tweet: Tweet dict with 'text' and 'category' keys
        existing_tweets: List of already-queued tweets for ticker frequency check

    Returns:
        Tuple of (is_valid: bool, errors: list)
    """
    errors = []
    text = tweet.get('text', '')
    category = tweet.get('category', '')

    if existing_tweets is None:
        existing_tweets = []

    # Import config items needed for validation
    try:
        from config import (
            BANNED_TERMS,
            KILLED_CATEGORIES,
            TICKER_LIMITS,
            enforce_teal_branding,
        )
    except ImportError:
        # Fallback comprehensive banned terms list
        BANNED_TERMS = [
            # Internal technical terms
            'HMA', 'Hull Moving Average', 'HMA Pivot',
            'Banker', 'Banker indicator', 'Banker >=',
            'BoS', 'BOS', 'Break of Structure', 'Weekly BoS',
            '20% stop', '20% trailing',
            'Beta >=', 'beta threshold',
            'Tier 1', 'Tier 2', 'Tier 3', 'TIER1', 'TIER2', 'TIER3',
            'Gatekeeper',
            # Internal gate names
            'Forensic Audit', '5th Gate', 'Gate 5',
            'Volatility Expansion Criteria', 'Volatility Expansion',
            'Institutional Accumulation Divergence',
            'Structural Pivot Confirmation',
            'Capital Preservation Protocol',
            # Non-branded signal terms
            'proprietary entry', 'proprietary signal',
            'buy signal', 'PASS signal',
            # Region-specific (audience-neutral - avoid all)
            'Roth IRA', 'Roth', '401k', '401(k)',
            'PDT', 'PDT rule', 'pattern day trader',
            'UK ISA', 'ISA account', 'GMT', 'BST', 'UK Time',
            # Technical indicators
            'RSI', 'MACD', 'KDJ',
        ]
        KILLED_CATEGORIES = ['roth_ira', 'pdt_friendly', 'position_update', 'weekly_wins']
        TICKER_LIMITS = {'max_mentions_per_week': 4}

    # 1. Check killed categories
    if category in KILLED_CATEGORIES:
        errors.append(f"KILLED CATEGORY: '{category}' is not allowed")

    # 2. Check tweet length
    if not validate_tweet_length(text):
        char_count = get_tweet_char_count(text)
        errors.append(f"TOO LONG: {char_count} chars (max 280)")

    # 3. Check banned terms (with word boundary for short terms)
    text_lower = text.lower()
    # Short terms that need word boundary matching to avoid false positives
    # e.g., "BST" should not match inside "substack"
    short_terms = ['bst', 'gmt', 'rsi', 'bos', 'hma', 'pdt', 'roth']
    for term in BANNED_TERMS:
        term_lower = term.lower()
        if term_lower in short_terms or len(term_lower) <= 4:
            # Use word boundary regex for short terms
            pattern = r'\b' + re.escape(term_lower) + r'\b'
            if re.search(pattern, text_lower):
                errors.append(f"BANNED TERM: '{term}' found in tweet")
        elif term_lower in text_lower:
            errors.append(f"BANNED TERM: '{term}' found in tweet")

    # 4. Check for negative P&L (losers shown)
    negative_pnl = re.findall(r'-\d+\.?\d*%', text)
    if negative_pnl:
        errors.append(f"LOSER SHOWN: Negative P&L found: {negative_pnl}")

    # 5. Check TEAL branding for signal tweets
    signal_categories = ['buy_signal', 'thread_buy_signal', 'milestone_alerts', 'early_movers']
    if category in signal_categories:
        if 'TEAL' not in text.upper():
            errors.append("MISSING BRANDING: Signal tweet must contain 'TEAL'")

    # 6. Check holding period for P&L tweets
    has_pnl = '%' in text and ('+' in text or '-' in text)
    if has_pnl:
        holding_indicators = ['week', 'weeks', 'day', 'days', 'month', 'months', 'held', 'holding', 'entry', 'since']
        if not any(ind in text.lower() for ind in holding_indicators):
            errors.append("MISSING HOLDING PERIOD: P&L shown without timeframe context")

    # 7. Check US-specific content (wrong audience)
    us_terms = ['roth', '401k', 'pdt rule', 'pattern day', 'ira ']  # Note: 'ira ' with space to avoid matching in 'sterlingsignals'
    for term in us_terms:
        if term in text.lower():
            errors.append(f"US-SPECIFIC: '{term}' not appropriate for UK audience")

    # 8. Check ticker frequency limits
    tickers = re.findall(r'\$([A-Z]+)', text)
    for ticker in tickers:
        mentions = sum(1 for t in existing_tweets if ticker.upper() in t.get('text', '').upper())
        if mentions >= TICKER_LIMITS.get('max_mentions_per_week', 4):
            errors.append(f"TICKER OVEREXPOSED: ${ticker} already mentioned {mentions} times")

    return (len(errors) == 0, errors)


def validate_and_fix_tweet(tweet: dict, existing_tweets: list = None) -> dict:
    """
    Validate tweet and attempt to fix minor issues.

    Args:
        tweet: Tweet dict to validate/fix
        existing_tweets: List of already-queued tweets

    Returns:
        Fixed tweet dict with 'validation_errors' key if unfixable issues remain
    """
    # Import enforce_teal_branding for auto-fix
    try:
        from config import enforce_teal_branding
    except ImportError:
        def enforce_teal_branding(t):
            return t.replace('buy signal', 'TEAL signal').replace('Buy signal', 'TEAL signal')

    text = tweet.get('text', '')
    category = tweet.get('category', '')

    # Auto-fix: Apply TEAL branding
    signal_categories = ['buy_signal', 'thread_buy_signal', 'milestone_alerts', 'early_movers']
    if category in signal_categories:
        text = enforce_teal_branding(text)

    # Auto-fix: Truncate if too long
    if not validate_tweet_length(text):
        text = truncate_tweet(text, max_length=275)

    tweet['text'] = text

    # Validate the fixed tweet
    is_valid, errors = validate_tweet_before_queue(tweet, existing_tweets)

    if not is_valid:
        tweet['validation_errors'] = errors
        print(f"  ⚠️ Validation errors for {tweet.get('id', 'unknown')}: {errors}")

    return tweet


def validate_and_fix_thread_tweets(tweets: list) -> list:
    """
    MASTER_TODO_v2: Validate and fix thread tweets for compliance.
    
    Checks:
    1. TEAL branding in final tweet (CTA)
    2. No banned terms
    3. No hashtags at end
    4. Holding periods on any P&L percentages
    
    Args:
        tweets: List of tweet dicts with 'number' and 'text' keys
        
    Returns:
        Fixed list of tweets
    """
    # Import enforce_teal_branding for auto-fix
    try:
        from config import enforce_teal_branding
    except ImportError:
        def enforce_teal_branding(t):
            replacements = {
                'buy signal': 'TEAL signal',
                'Buy signal': 'TEAL signal',
                'our signal': 'TEAL signal',
                'proprietary signal': 'TEAL signal',
                'proprietary entry': 'TEAL signal',
            }
            for old, new in replacements.items():
                t = t.replace(old, new)
            return t
    
    for tweet in tweets:
        text = tweet.get('text', '')
        number = tweet.get('number', 0)
        
        # 1. Apply TEAL branding to all tweets
        text = enforce_teal_branding(text)
        
        # 2. Final tweet (5/5) MUST have TEAL branding
        if number == 5:
            if 'TEAL' not in text.upper():
                # Try to insert TEAL branding
                if 'signal' in text.lower():
                    text = text.replace('signals', 'TEAL signals')
                    text = text.replace('signal process', 'TEAL signal process')
                elif 'sterlingsignals' in text.lower():
                    # Add before the link
                    text = text.replace('sterlingsignals', 'Get TEAL signals: sterlingsignals')
                else:
                    # Append mention
                    if 'substack.com' in text:
                        text = text.replace('substack.com', 'substack.com\n\nTEAL signals weekly.')
                
                print(f"  🔧 Added TEAL branding to thread tweet 5")
        
        # 3. Remove hashtags at end (they're low-value on X now)
        import re
        hashtag_pattern = r'\s*#\w+\s*$'
        while re.search(hashtag_pattern, text):
            text = re.sub(hashtag_pattern, '', text)
            print(f"  🔧 Removed hashtag from thread tweet {number}")
        
        # 4. Check for banned terms and warn
        banned_check = ['Forensic Audit', 'Volatility Expansion', 'Gate 5', '5th Gate', 
                       'Capital Preservation', 'Roth IRA', '401k', 'PDT']
        for term in banned_check:
            if term.lower() in text.lower():
                print(f"  ⚠️ Thread tweet {number} contains banned term: {term}")
        
        tweet['text'] = text
    
    return tweets


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: POSITION DISPLAY WITH HOLDING PERIOD
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_days_held(entry_date: str) -> int:
    """Calculate days held from entry date string.

    Args:
        entry_date: Date string in YYYY-MM-DD format

    Returns:
        Number of days held, or 0 if parsing fails
    """
    if not entry_date:
        return 0

    try:
        entry = datetime.strptime(entry_date, '%Y-%m-%d')
        days = (datetime.now() - entry).days
        return max(0, days)  # Never negative
    except (ValueError, TypeError):
        return 0


def format_position_with_age(pos: dict) -> str:
    """Format position with holding period for honest timeframe display.

    Phase 9: Ensures P&L figures always show holding period context to
    avoid misleading audiences about whether returns are weekly or cumulative.

    Args:
        pos: Position dict with ticker, pnl_pct, entry_date fields

    Returns:
        Formatted string like "$AAPL +25.3% (4 weeks)"
    """
    ticker = pos.get('ticker', 'UNK')
    pnl = pos.get('pnl_pct', 0)
    entry_date = pos.get('entry_date', '')

    # Calculate holding period
    days_held = calculate_days_held(entry_date)
    period = format_holding_period(days_held)

    # Format P&L
    pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"

    return f"${ticker} {pnl_str} ({period})"


def format_positions_for_display(positions: list, max_positions: int = 5) -> str:
    """Format multiple positions with holding periods for tweet display.

    Args:
        positions: List of position dicts
        max_positions: Maximum positions to include

    Returns:
        Multi-line string with formatted positions
    """
    if not positions:
        return "No positions to display"

    lines = []
    for pos in positions[:max_positions]:
        lines.append(format_position_with_age(pos))

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def check_already_generated(output_dir: Path, scan_date: str = None) -> tuple[bool, int, str]:
    """Check if tweets have already been generated for this scan date.

    Prevents duplicate content generation when re-running the generator.

    Args:
        output_dir: Directory containing content_queue.json
        scan_date: The scan date to check (YYYY-MM-DD). If None, uses today.

    Returns:
        tuple: (already_generated: bool, pending_count: int, queue_date: str)
    """
    queue_file = output_dir / "content_queue.json"
    if not queue_file.exists():
        return False, 0, ""

    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False, 0, ""

    if not queue:
        return False, 0, ""

    # Check for pending tweets
    pending = [t for t in queue if t.get('status') == 'pending']
    if not pending:
        return False, 0, ""

    # Get the earliest scheduled date from pending tweets
    scheduled_dates = [t.get('scheduled_date', '') for t in pending if t.get('scheduled_date')]
    if not scheduled_dates:
        return False, len(pending), ""

    earliest_date = min(scheduled_dates)

    # If scan_date provided, check if it matches the week of existing content
    if scan_date:
        try:
            scan_dt = datetime.strptime(scan_date, '%Y-%m-%d')
            earliest_dt = datetime.strptime(earliest_date, '%Y-%m-%d')

            # Check if they're in the same week (within 7 days)
            days_diff = abs((earliest_dt - scan_dt).days)
            if days_diff <= 7:
                return True, len(pending), earliest_date
        except ValueError:
            pass

    # Fallback: check if today matches the content week
    today = datetime.now()
    try:
        earliest_dt = datetime.strptime(earliest_date, '%Y-%m-%d')
        days_diff = abs((earliest_dt - today).days)
        # If pending content is for this week or next (within 10 days), consider it current
        if days_diff <= 10:
            return True, len(pending), earliest_date
    except ValueError:
        pass

    return False, len(pending), earliest_date


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
    1: "pre_market",     # 08:00 ET - Pre-market / Top performers / Alpha
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
    # Signals (CRIT-2: Separate CONSIDER from CAUTION)
    pass_signals: List[Dict] = field(default_factory=list)        # PASS - cleared all 5 gates
    consider_signals: List[Dict] = field(default_factory=list)    # CONSIDER - passed gates 1-4 (bullish watchlist)
    caution_signals: List[Dict] = field(default_factory=list)     # Open positions with issues (warnings)
    sell_signals: List[Dict] = field(default_factory=list)        # EXIT - stop triggered
    open_positions: List[Dict] = field(default_factory=list)
    closed_trades: List[Dict] = field(default_factory=list)
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
- Keep legal disclaimers in bio/newsletter, but NEVER give explicit "buy/sell this stock" advice in tweets
- Frame all content as educational/observational, not as financial advice
- All times in Eastern Time (ET)

CRITICAL MARKETING LANGUAGE RULES - BANNED TERMS:
NEVER use these terms in any tweet:
- "HMA", "Hull Moving Average", "HMA Pivot"
- "Banker indicator", "Banker >= 55"
- "20% trailing stop", "20% stop"
- "Beta >= 1.5", "beta threshold"
- "Break of Structure", "BoS", "BOS", "Weekly BoS"
- "Tier 1", "Tier 2", "Tier 3", "TIER1", "TIER2", "TIER3"
- "Gatekeeper"
- "UK ISA", "ISA account", "GMT", "BST", "UK Time"
- "RSI", "MACD", "KDJ"
- "Forensic Audit", "5th Gate", "Gate 5" (use "final gate" or "cleared all gates")
- "Volatility Expansion Criteria", "Volatility Expansion"
- "Institutional Accumulation Divergence" (use "institutional accumulation" only)
- "Structural Pivot Confirmation" (use "technical setup" or "momentum confirmed")
- "Capital Preservation Protocol" (use "systematic stop" or "trailing stop")
- "proprietary entry", "proprietary signal" (use "TEAL signal")
- "buy signal", "Buy signal" (use "TEAL signal")
- "PASS signal" (use "TEAL signal")
- "Roth IRA", "Roth", "401k", "401(k)" (audience-neutral - no region-specific)
- "PDT", "PDT rule", "pattern day trader" (audience-neutral - no region-specific)

APPROVED VOCABULARY - USE THESE INSTEAD:
- "TEAL signal" (ALWAYS use this for buy signals - this is our brand)
- "5-gate screening system" (don't mention individual gate names)
- "Cleared all gates" or "cleared all 5 gates" (not Forensic Audit, not Gate 5)
- "Systematic stop" or "trailing stop" (not Capital Preservation Protocol)
- "Momentum confirmed" or "technical setup confirmed" (not Weekly BoS)
- "High conviction" (not Tier 1/2/3)
- "Institutional accumulation" (not "Institutional Accumulation Divergence")

AUDIENCE CONTENT HOOKS (audience-neutral):
1. BEAT SPY - Alpha over indexing, "Stop indexing. Start selecting."
2. TIME-FRIENDLY - Weekly timeframe suits busy schedules
3. POWER HOUR - 15:30-16:00 ET market reaction, relative strength
4. SECTOR ROTATION - Following institutional flows between themes

APPROVED POWER PHRASES:
- "Proprietary 5-gate screening system"
- "Filters 1,800 stocks to 3-5 actionable signals"
- "TEAL signal triggered" (NOT "buy signal")
- "Cleared all 5 gates" (NOT "Forensic Audit cleared")
- "Systematic exit discipline" (NOT "Capital Preservation Protocol")
- "The system protects capital so we live to fight another day"
- "No ego, just execution"

CRITICAL HONESTY + POSITIVITY RULES:
1. For position_update tweets, ONLY show winning positions (pre-filtered for you)
2. When portfolio is down overall, focus on themes and education instead
3. Frame exits as DISCIPLINE, not failures:
   - "Stop hit = system working as designed"
   - "Systematic exit discipline in action"
   - "No ego, just execution. On to the next."
4. When mentioning portfolio returns, ALWAYS include SPY comparison when outperforming

LEGAL COMPLIANCE REQUIREMENTS:
1. NEVER say "buy this stock" or "you should invest in X" - instead say "what we're watching" or "our system identified"
2. When showing returns/gains, frame as educational/informational:
   - "Our screening identified $TICKER +25% since signal" (educational)
   - NOT "Buy $TICKER for 25% gains" (advice)
3. NEVER make promises about future returns
4. Use language that implies analysis/observation, not recommendation:
   - "Cleared all 5 gates" (observation)
   - "Showing institutional accumulation" (analysis)
   - "On our radar" (watching, not recommending)
5. Full "not financial advice" disclaimer is in bio and newsletter - tweets imply educational purpose

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
    if category == "buy_signal" or category == "teal_signal":
        # Show ALL TEAL signals (no limit - marketing overhaul)
        num_signals = len(content.pass_signals) if content.pass_signals else 0
        teal_emoji = get_signal_emoji('TEAL') if CONFIG_AVAILABLE else '🟢'
        context = f"""
Generate {count} tweets about new TEAL signals that passed ALL our gates.

TEAL Signals this week ({num_signals} total - show ALL of them):
{json.dumps(content.pass_signals, indent=2)}

IMPORTANT: We now show ALL signals that pass our 5-gate system, not just one.
If multiple signals, mention all tickers.

For each signal, highlight (use GENERIC language):
- The ticker with $TICKER format
- Conviction level using these EXACT terms: "Extremely Bullish" (conv 5), "Bullish" (conv 4), "Watching" (conv 3)
- Key catalyst driving the trade
- Our multi-step proprietary screening process (1800 stocks → {num_signals} TEAL signals)
- Link to full analysis: sterlingsignals.substack.com

CRITICAL: Do NOT reveal specific indicator names or formulas.
Use: "proprietary signals", "smart money accumulation", "theme momentum confirmed"
Use "TEAL signal" branding (not "PASS signal")
ALWAYS start with {teal_emoji} TEAL Signal emoji prefix

Example format (single signal):
"{teal_emoji} TEAL Signal: $IESC

Conviction: Bullish

✅ Technical entry signal confirmed
✅ Smart money accumulation detected
✅ Hot theme momentum

Full analysis in this week's newsletter 👇
sterlingsignals.substack.com"

Example format (multiple signals):
"{teal_emoji} TEAL Signals this week:

$TICKER1 - Extremely Bullish
$TICKER2 - Bullish
$TICKER3 - Bullish

All cleared our proprietary 5-gate system.
1,817 stocks → {num_signals} opportunities.

Full analysis 👇
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
        # MASTER_TODO_v2: KILLED CATEGORY - Shows individual P&L
        # Use top_performers instead (safeguarded, winners only)
        print(f"  🚨 ERROR: position_update category is KILLED. Using top_performers instead.")
        return generate_tweets_for_category(client, "top_performers", content, count)

    elif category == "sell_signal" or category == "violet_alert":
        violet_emoji = get_signal_emoji('VIOLET') if CONFIG_AVAILABLE else '🟣'
        # Filter to only show profitable exits (never show losses)
        profitable_exits = [s for s in content.sell_signals if s.get('pnl_pct', 0) > 0] if content.sell_signals else []

        context = f"""
Generate {count} tweets about EXIT signals (VIOLET alerts).

CRITICAL: Only show PROFITABLE exits. Never show losing positions.

PROFITABLE EXITS (show these):
{json.dumps(profitable_exits, indent=2) if profitable_exits else "No profitable exits this week"}

Caution Signals (watching closely):
{json.dumps(content.caution_signals, indent=2)}

For PROFITABLE exits, frame as (use GENERIC language):
- System protecting gains
- Trailing stop worked as designed
- Disciplined exits lock in profits
- Our system identifying the right exit timing

For CAUTION signals, frame as:
- Risk management in action
- Technical signals showing weakness
- Tightening stops to protect gains

CRITICAL: Do NOT mention specific indicators like "BoS" or specific stop percentages.
Use phrases like "systematic exit", "trailing stop triggered", "protecting gains"

TEMPLATE for profitable exit:
"{violet_emoji} VIOLET Alert: $TICKER

Trailing stop triggered.

Entry: $XX.XX
Exit: $XX.XX
Return: +XX.X%
Held: X weeks

Systematic exits protect gains.

sterlingsignals.substack.com"

RULES:
- ALWAYS start with {violet_emoji} VIOLET emoji for exits
- ONLY show profitable exits (NEVER show losses)
- Include entry price, exit price, and return percentage for winners
- Include holding period
- Focus on the system working as designed
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

    elif category == "beat_spy" or category == "benchmark_alpha":
        # Get SPY comparison data if available
        teal_emoji = get_signal_emoji('TEAL') if CONFIG_AVAILABLE else '🟢'
        spy_comparison = None
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                spy_comparison = calculate_portfolio_vs_spy(content.open_positions)
            except:
                pass

        # Only generate if actually outperforming (safeguard enforced in schedule)
        outperformance = spy_comparison.get('outperformance', 0) if spy_comparison else 0
        portfolio_return = spy_comparison.get('portfolio_return', 0) if spy_comparison else 0
        spy_return = spy_comparison.get('spy_return', 0) if spy_comparison else 0

        context = f"""
Generate {count} tweets comparing our performance to SPY/QQQ for active investors.

PERFORMANCE DATA (use these real numbers):
- Portfolio Return: {portfolio_return:.1f}%
- SPY Return: {spy_return:.1f}%
- Outperformance: {outperformance:.1f}%

Open positions: {json.dumps(content.open_positions[:3], indent=2) if content.open_positions else "None"}
Hot themes: {[t.get('name') for t in content.prime_themes]}

CRITICAL: Only use benchmark comparison messaging when we have real outperformance data.
If no data, focus on the methodology rather than specific numbers.

TEMPLATES:
"{teal_emoji} TEAL Signal Alpha

SPY is chopping sideways.
Meanwhile, the system found 3 sectors breaking out with institutional backing.
Stop indexing. Start selecting.
sterlingsignals.substack.com"

"S&P 500: {'+' if spy_return >= 0 else ''}{spy_return:.1f}%
TEAL Signals: {'+' if portfolio_return >= 0 else ''}{portfolio_return:.1f}%

The difference? We follow smart money into specific themes.
Not broad exposure — targeted alpha.

sterlingsignals.substack.com"

"Most portfolios mirror the S&P 500.
Ours hunts the 3-5 stocks each week that institutions are quietly accumulating BEFORE the breakout.
That's alpha. That's the system.
sterlingsignals.substack.com"

RULES:
- Only post when genuinely outperforming by 5%+
- Be factual with real numbers, not arrogant
- Focus on stock selection vs passive indexing
- ALWAYS link to newsletter
- Use {teal_emoji} TEAL emoji when showing outperformance
"""

    elif category == "roth_ira":
        # MASTER_TODO_v2: KILLED CATEGORY - Audience-neutral (avoid region-specific content)
        print(f"  🚨 ERROR: roth_ira category is KILLED. Using theme_hot instead.")
        return generate_tweets_for_category(client, "theme_hot", content, count)

    elif category == "pdt_friendly":
        # MASTER_TODO_v2: KILLED CATEGORY - Audience-neutral (avoid region-specific content)
        print(f"  🚨 ERROR: pdt_friendly category is KILLED. Using educational instead.")
        return generate_tweets_for_category(client, "educational", content, count)

    elif category == "power_hour":
        # MASTER_TODO_v2: power_hour MUST NOT show individual position P&L
        # Only theme-level market commentary allowed
        context = f"""
Generate {count} Power Hour reaction tweets (15:30-16:00 ET market hours).

Hot themes: {[t.get('name') for t in content.prime_themes]}
Cold themes: {[t.get('name') for t in content.avoid_themes]}

🚨 CRITICAL SAFEGUARD (MASTER_TODO_v2):
- NO individual ticker P&L (don't say "$TICKER up/down X%")
- NO position updates or portfolio commentary
- ONLY theme-level market observations

TEMPLATES:
"⚡ POWER HOUR

Watching {content.prime_themes[0].get('name', 'infrastructure') if content.prime_themes else 'key themes'} theme into the close.

Relative strength vs broad market.

Full analysis 👇
sterlingsignals.substack.com"

"⚡ POWER HOUR

Market rotation visible:
🔥 {content.prime_themes[0].get('name', 'Growth themes') if content.prime_themes else 'Growth'} showing strength
❄️ {content.avoid_themes[0].get('name', 'Defensive sectors') if content.avoid_themes else 'Defensive'} lagging

Following institutional flows into the close.

sterlingsignals.substack.com"

RULES:
- Post during 15:30-16:00 ET window (Power Hour)
- Reference theme/sector performance ONLY
- 🚨 NEVER mention individual stocks or P&L percentages
- Keep observational, not promotional
- Mention "structural" or "institutional" language
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
- Passed momentum gates: ~485
- Showed strong accumulation: ~48
- Theme aligned: ~17
- Cleared all 5 gates: {len(content.pass_signals) if content.pass_signals else 6}

TEMPLATE:
"This week's scan:
📊 1,817 stocks analyzed
📉 485 showed momentum characteristics
🔍 48 confirmed strong accumulation
🎯 17 aligned with hot themes
✅ {len(content.pass_signals) if content.pass_signals else 6} cleared all 5 gates = TEAL signals

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

    elif category == "top_performers" or category == "winner_showcase":
        # Phase 9: Renamed from weekly_wins to avoid misleading terminology
        # Filter to only show winning positions (safeguard already checked)
        teal_emoji = get_signal_emoji('TEAL') if CONFIG_AVAILABLE else '🟢'
        winners = []
        if SIGNAL_TRACKER_AVAILABLE:
            winners = filter_public_positions(content.open_positions)
        else:
            # Fallback: manually filter to positive P&L only
            winners = [p for p in content.open_positions if p.get('pnl_pct', 0) >= MARKETING_THRESHOLDS.get('min_win_to_highlight', 15.0)]

        # Format positions with holding periods for honest display
        formatted_positions = format_positions_for_display(winners, max_positions=5)

        # Check if we can show entry prices (above 25% threshold)
        can_show_entries = any(p.get('pnl_pct', 0) >= 25.0 for p in winners) if winners else False

        context = f"""
Generate {count} tweets showcasing our top-performing positions (ONLY positive positions).

CRITICAL: Always show holding period with each return.
Format: "$TICKER +XX% (X weeks held)" NOT just "$TICKER +XX%"

TOP PERFORMING POSITIONS (with holding periods):
{formatted_positions}

{TIMEFRAME_DISCLAIMERS.get('medium', 'Total gain since entry, not weekly movement.')}

ENTRY PRICE RULE: {"For positions above 25% gain, you MAY show entry prices (e.g., '$XX.XX → $YY.YY')" if can_show_entries else "Do NOT show entry prices (not above 25% threshold)"}

CRITICAL SAFEGUARD: This tweet type ONLY shows winners. Never mention losers.

TEMPLATE:
"{teal_emoji} TEAL Signal Winners

Best positions since signal entry:

$TICKER1: +XX% (Xw held)
$TICKER2: +XX% (Xw held)
$TICKER3: +XX% (Xw held)

Returns measured from entry. Targeting 50-100% over months.
1,817 stocks scanned → {len(content.pass_signals) if content.pass_signals else 'X'} TEAL signals

Full analysis 👇
sterlingsignals.substack.com"

RULES:
- ALWAYS start with {teal_emoji} TEAL emoji
- ALWAYS include holding period with each P&L (e.g., "4 weeks held")
- ONLY show positions with positive P&L
- Never mention any losers or underwater positions
- Only show entry prices for positions above 25% gain
- Clarify these are TOTAL returns since entry, not weekly gains
- Focus on the system identifying these winners
- Always link to newsletter
- Use "TEAL signal" not "PASS signal"
"""

    elif category == "self_quote" or category == "milestone_alerts" or category == "hall_of_fame":
        # Get uncelebrated wins from signal tracker
        teal_emoji = get_signal_emoji('TEAL') if CONFIG_AVAILABLE else '🟢'
        big_wins_data = []
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                big_wins_data = get_uncelebrated_wins()
            except:
                pass

        context = f"""
Generate {count} celebration tweets for big wins from past TEAL signals.

CRITICAL: Always include holding period with the return (e.g., "X weeks held")
CRITICAL: Always include entry price for milestone celebrations (positions above 25%)

BIG WINS TO CELEBRATE (uncelebrated threshold crossings):
{json.dumps([{{'ticker': w.ticker, 'entry_price': w.entry_price, 'current_price': w.current_price, 'pnl_pct': w.pnl_pct, 'signal_date': w.signal_date, 'theme': w.theme, 'threshold_crossed': w.threshold_crossed}} for w in big_wins_data[:3]], indent=2) if big_wins_data else "No new big wins to celebrate"}

{TIMEFRAME_DISCLAIMERS.get('medium', 'Total gain since entry, not weekly movement.')}

TEMPLATE FOR 25%+ WIN (MILESTONE):
"{teal_emoji} TEAL Signal Update: $TICKER

Entry: $ENTRY on [DATE]
Now: $CURRENT (+XX% over X weeks)

Another TEAL signal delivering.
The 5-gate system works.

More signals every week 👇
sterlingsignals.substack.com"

TEMPLATE FOR 50%+ WIN (HOME RUN):
"🏆 HOME RUN: $TICKER

{teal_emoji} TEAL Signal Entry: $ENTRY on [DATE]
Now: $CURRENT
Gain: +XX% (X weeks held)

When all 5 gates align, this is what happens.
Our proprietary system found this before the crowd.

Want signals like this? 👇
sterlingsignals.substack.com"

TEMPLATE FOR 100%+ WIN (HALL OF FAME):
"🚀 HALL OF FAME: $TICKER DOUBLED

{teal_emoji} TEAL Signal Entry: $ENTRY on [DATE]
Current: $CURRENT
Return: +XXX% (X months held)

This is what disciplined momentum trading delivers.
Proprietary screening. Systematic execution.

Join the journey 👇
sterlingsignals.substack.com"

RULES:
- ALWAYS include entry price for milestone celebrations
- Each big win gets ONE celebration post per threshold
- Use the appropriate template based on gain level
- Always include entry price, signal date, AND holding period
- Focus on the system, not luck
- Use "TEAL signal" branding with {teal_emoji} emoji
"""

    elif category == "consider_spotlight" or category == "amber_watch":
        amber_emoji = get_signal_emoji('AMBER') if CONFIG_AVAILABLE else '🟠'
        context = f"""
Generate {count} tweets about stocks on our watchlist (CONSIDER classification).

WATCHLIST STOCKS (passed gates 1-4, watching gate 5):
{json.dumps(content.consider_signals[:5], indent=2) if content.consider_signals else "No watchlist stocks this week"}

These are stocks that:
- Passed technical screening (4/5 gates)
- Show institutional accumulation
- Align with hot themes
- But haven't cleared our final gate yet

TEMPLATE:
"{amber_emoji} AMBER Watchlist

Stocks cleared 4/5 gates - watching for TEAL:

$TICKER1 at $XX.XX - Theme1
$TICKER2 at $XX.XX - Theme2

Not TEAL signals yet, but worth watching.
Save this. We'll update when they clear all 5 gates.

Full watchlist 👇
sterlingsignals.substack.com"

RULES:
- ALWAYS start with {amber_emoji} AMBER emoji
- DO NOT frame as buy recommendations
- Use "AMBER Watchlist" or "On Our Radar" language
- Explain they need all 5 gates cleared for TEAL signal
- Create curiosity without over-promising
- Use "TEAL signal" when referencing full signals
- NEVER say "Forensic Audit" - use "final gate" or "full confirmation"
- NEVER say "Gate 5" - use "final gate" or "all 5 gates"
- NEVER say "proprietary entry" - use "TEAL signal"
"""

    elif category == "weekly_recap":
        # High-engagement weekly summary with color signals
        teal_emoji = get_signal_emoji('TEAL') if CONFIG_AVAILABLE else '🟢'
        amber_emoji = get_signal_emoji('AMBER') if CONFIG_AVAILABLE else '🟠'

        # Get winners for showcase
        winners = []
        if SIGNAL_TRACKER_AVAILABLE:
            winners = filter_public_positions(content.open_positions)
        else:
            winners = [p for p in content.open_positions if p.get('pnl_pct', 0) >= 15.0]

        winners = sorted(winners, key=lambda x: x.get('pnl_pct', 0), reverse=True)[:3]

        # Get SPY comparison
        spy_comparison = None
        if SIGNAL_TRACKER_AVAILABLE:
            try:
                spy_comparison = calculate_portfolio_vs_spy(content.open_positions)
            except:
                pass

        spy_return = spy_comparison.get('spy_return', 0) if spy_comparison else 0

        context = f"""
Generate {count} high-engagement weekly recap tweets summarizing the week's signals.

THIS WEEK'S TEAL SIGNALS:
{json.dumps(content.pass_signals[:5], indent=2) if content.pass_signals else "None"}

TOP PERFORMING POSITIONS (show conviction language):
{json.dumps(winners, indent=2) if winners else "None"}

SPY RETURN THIS PERIOD: {spy_return:+.1f}%

TEMPLATE:
"{teal_emoji} TEAL signals this week:

$TICKER1 — Extremely Bullish
$TICKER2 — Bullish
$TICKER3 — Bullish

Meanwhile... S&P 500: {spy_return:+.1f}%

Our 5-Gate System continues to find asymmetric setups.

Full analysis 👇
sterlingsignals.substack.com"

CONVICTION LANGUAGE (use these EXACT terms):
- Conviction 5 = "Extremely Bullish"
- Conviction 4 = "Bullish"
- Conviction 3 = "Watching"

RULES:
- ALWAYS start with {teal_emoji} TEAL emoji
- Use conviction language (Extremely Bullish, Bullish, Watching)
- Compare to SPY when outperforming
- Encourage saves and engagement
- Link to newsletter
"""

    else:
        context = f"Generate {count} general financial content tweets. Always link to sterlingsignals.substack.com. Use APPROVED vocabulary - never mention HMA, Banker, BoS, 20% stop, Tier 1/2/3, or region-specific terms (ISA, Roth IRA, etc)."

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


def generate_all_tweets(content: WeeklyContent, mock: bool = False, cold_streak_active: bool = False) -> List[Tweet]:
    """Generate all 21 tweets for the week.

    Args:
        content: WeeklyContent with all scanner data
        mock: If True, generate mock tweets without API calls
        cold_streak_active: If True, reduce position-focused content (GAP 38 fix)
    """

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

    # Check safeguards for dynamic category selection
    # These determine whether certain content categories can be posted
    can_post_beat_spy = False
    can_post_top_performers = False  # Phase 9: Renamed from can_post_weekly_wins
    uncelebrated_wins = []

    if SIGNAL_TRACKER_AVAILABLE:
        try:
            can_post_beat_spy = should_post_beat_spy(content.open_positions)
            can_post_top_performers = has_enough_wins(content.open_positions)
            uncelebrated_wins = get_uncelebrated_wins()
            print(f"  📊 Safeguard checks: beat_spy={can_post_beat_spy}, top_performers={can_post_top_performers}, uncelebrated_wins={len(uncelebrated_wins)}")
        except Exception as e:
            print(f"  ⚠️ Safeguard check failed: {e}")

    # GAP 38 fix: Cold streak enforcement
    # When in cold streak, disable position-focused categories to avoid drawing attention to losses
    if cold_streak_active:
        print(f"  🥶 COLD STREAK ACTIVE - Reducing position-focused content")
        can_post_beat_spy = False  # Don't compare to SPY during losing streak
        can_post_top_performers = False  # Don't highlight wins when recent losses
        uncelebrated_wins = []  # Don't self-quote during cold streak
    else:
        print("  ⚠️ Signal tracker not available - using fallback categories")

    # Dynamic category selection based on safeguards
    # If safeguard fails, use fallback category
    beat_spy_or_fallback = "beat_spy" if can_post_beat_spy else "engagement"
    top_performers_or_fallback = "top_performers" if can_post_top_performers else "theme_hot"  # Phase 9: Renamed
    self_quote_or_fallback = "self_quote" if uncelebrated_wins else "consider_spotlight" if content.consider_signals else "theme_hot"

    categories_schedule = [
        # Saturday: Newsletter day - showcase ALL TEAL signals + performance
        ("Saturday", 1, top_performers_or_fallback),  # 08:00 ET - Top performers (safeguarded)
        ("Saturday", 2, "thread_buy_signal"),      # 10:00 ET - 🧵 Deep dive on top signal
        ("Saturday", 3, "theme_hot"),              # 12:30 ET - Theme momentum
        ("Saturday", 4, "funnel_graphic"),         # 15:30 ET - Scanner stats
        ("Saturday", 5, "engagement"),             # 18:00 ET - Poll/discussion

        # Sunday: All TEAL signals + consider spotlight
        ("Sunday", 1, "buy_signal" if content.pass_signals else "funnel_graphic"),  # 08:00 ET - ALL TEAL signals
        ("Sunday", 2, "consider_spotlight" if content.consider_signals else "theme_hot"),  # 10:00 ET - Watchlist stocks
        ("Sunday", 3, beat_spy_or_fallback),       # 12:30 ET - SPY comparison (safeguarded)
        ("Sunday", 4, "engagement"),               # 18:00 ET - Community

        # Monday: Week kickoff + celebrate wins
        ("Monday", 1, "theme_hot"),                # 08:00 ET - Hot theme
        ("Monday", 2, self_quote_or_fallback),     # 10:00 ET - Big win celebration (if any)
        ("Monday", 3, "power_hour"),               # 15:30 ET - Power Hour (CRITICAL)
        ("Monday", 4, "engagement"),               # 18:00 ET - Discussion

        # Tuesday: Early movers + education (MASTER_TODO_v2: removed roth_ira - wrong audience)
        ("Tuesday", 1, "early_movers" if content.open_positions else "theme_hot"),  # 08:00 ET - New signals showing strength
        ("Tuesday", 2, "theme_hot"),               # 10:00 ET - Theme momentum
        ("Tuesday", 3, "power_hour"),              # 15:30 ET - Power Hour
        ("Tuesday", 4, "educational"),             # 18:00 ET - Trading lesson

        # Wednesday: Consider spotlight + educational (MASTER_TODO_v2: removed pdt_friendly - wrong audience)
        ("Wednesday", 1, "consider_spotlight" if content.consider_signals else "theme_hot"),  # 08:00 ET - On Our Radar stocks
        ("Wednesday", 2, "theme_hot"),             # 10:00 ET - Theme spotlight
        ("Wednesday", 3, "power_hour"),            # 15:30 ET - Power Hour
        ("Wednesday", 4, "engagement"),            # 18:00 ET - Community Q&A

        # Thursday: Alpha comparison + celebrate wins
        ("Thursday", 1, beat_spy_or_fallback),     # 08:00 ET - SPY comparison (safeguarded)
        ("Thursday", 2, self_quote_or_fallback),   # 10:00 ET - Big win celebration (if any)
        ("Thursday", 3, "power_hour"),             # 15:30 ET - Power Hour
        ("Thursday", 4, "educational"),            # 18:00 ET - Risk management

        # Friday: Scanner tease + reinforce signals
        ("Friday", 1, "buy_signal" if content.pass_signals else "theme_hot"),  # 08:00 ET - Reinforce TEAL signals
        ("Friday", 2, "funnel_graphic"),           # 10:00 ET - Weekly funnel visual
        ("Friday", 3, "power_hour"),               # 15:30 ET - Power Hour
        ("Friday", 4, "theme_hot"),                # 18:00 ET - Theme for week ahead
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

        # CRITICAL FIX: Always use the SCHEDULED category, not what Claude returned
        # Claude sometimes returns "system_promo" when we scheduled "consider_spotlight"
        # The schedule is authoritative - it determines content categorization for analytics
        tweet = Tweet(
            id=f"{day.lower()}_{slot}_{category}",
            day=day,
            slot=slot,
            category=category,  # USE SCHEDULED CATEGORY - not tweet_data.get("category")
            text=tweet_data.get("text", ""),
            ticker=ticker,
            theme=tweet_data.get("theme"),
            image_path=image_path,
            scheduled_date=scheduled_date
        )

        # MASTER_TODO_v2: Validate and fix tweet before adding to queue
        tweet_dict = tweet.to_dict() if hasattr(tweet, 'to_dict') else {
            'id': tweet.id, 'text': tweet.text, 'category': tweet.category,
            'day': tweet.day, 'slot': tweet.slot, 'scheduled_date': tweet.scheduled_date,
            'ticker': tweet.ticker, 'theme': tweet.theme, 'image_path': tweet.image_path
        }
        fixed_tweet = validate_and_fix_tweet(tweet_dict, [t.to_dict() if hasattr(t, 'to_dict') else t for t in all_tweets])
        # Update tweet with fixed text
        tweet.text = fixed_tweet.get('text', tweet.text)

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
        # CRIT-2: Use consider_signals for bullish watchlist (passed gates 1-4)
        # data.caution_signals contains bullish watchlist items (misleading legacy name)
        content.consider_signals = data.caution_signals  # Bullish watchlist
        content.caution_signals = []  # Reserved for open position warnings (populated below)
        content.sell_signals = data.sell_signals
        content.open_positions = data.open_positions
        content.prime_themes = data.prime_themes
        content.investable_themes = data.investable_themes
        content.selective_themes = data.selective_themes
        content.avoid_themes = data.avoid_themes
        content.scan_date = data.scan_date

        # Filter expired CONSIDER signals (default 21 days)
        # Add scan_date to each signal so expiry can be checked
        if SIGNAL_TRACKER_AVAILABLE and content.consider_signals:
            for sig in content.consider_signals:
                if 'signal_date' not in sig and content.scan_date:
                    sig['signal_date'] = content.scan_date
            content.consider_signals = filter_expired_consider_signals(
                content.consider_signals, max_age_days=21
            )

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

            # Normalize entry_date and compare using datetime objects (not strings)
            if entry_date:
                entry_dt = None
                # Handle various date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        entry_dt = datetime.strptime(entry_date, fmt)
                        break
                    except ValueError:
                        continue

                if entry_dt is None:
                    # Could not parse entry_date - skip this position to be safe
                    print(f"  ⚠ Could not parse entry_date for {ticker}: {entry_date}")
                    continue

                # Parse scan_date for proper datetime comparison
                try:
                    scan_dt = datetime.strptime(scan_date, '%Y-%m-%d')
                except ValueError:
                    scan_dt = datetime.now()

                # If entry_date is BEFORE scan_date, it's a pre-existing position
                if entry_dt < scan_dt:
                    pre_existing_tickers.add(ticker)
                else:
                    # This is a NEW signal from this week's scan - don't filter it
                    entry_str = entry_dt.strftime('%Y-%m-%d')
                    print(f"  ✨ {ticker} is a NEW signal (entry: {entry_str}, scan: {scan_date})")

        original_pass_count = len(content.pass_signals)
        content.pass_signals = [
            sig for sig in content.pass_signals
            if sig.get('ticker', '').upper() not in pre_existing_tickers
        ]
        if original_pass_count != len(content.pass_signals):
            removed = original_pass_count - len(content.pass_signals)
            filtered_tickers = [sig.get('ticker') for sig in content.pass_signals if sig.get('ticker', '').upper() in pre_existing_tickers]
            print(f"  🔄 Filtered {removed} PASS signal(s) already in portfolio from previous weeks")

        # Show all PASS signals (no limit - removed per marketing overhaul)
        if len(content.pass_signals) > 0:
            # Sort by conviction (descending), then by theme score for display order
            content.pass_signals.sort(
                key=lambda x: (
                    int(x.get('conviction', 0)) if isinstance(x.get('conviction'), (int, str)) and str(x.get('conviction', '')).isdigit() else 0,
                    float(x.get('theme_score', 0)) if x.get('theme_score') else 0
                ),
                reverse=True
            )
            print(f"  🎯 ALL {len(content.pass_signals)} TEAL signal(s) will be shown: {', '.join(s.get('ticker', '?') for s in content.pass_signals)}")

    # Load chart manifest
    manifest_path = CHARTS_DIR / "chart_manifest.json"
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            raw_charts = manifest.get("charts", {})
            # Normalize paths to relative (for CI compatibility)
            normalized = {}
            for key, value in raw_charts.items():
                if isinstance(value, str):
                    # Convert absolute paths to relative
                    if '/bos_momentum_scanner/' in value:
                        value = value.split('/bos_momentum_scanner/')[-1]
                    normalized[key] = value
                elif isinstance(value, dict) and value.get("path"):
                    path = value["path"]
                    if '/bos_momentum_scanner/' in path:
                        value["path"] = path.split('/bos_momentum_scanner/')[-1]
                    normalized[key] = value.get("path", value)
            content.chart_manifest = normalized

    return content


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

TWITTER_MAX_LENGTH = 280


def count_ticker_mentions(tweets: List) -> Dict[str, int]:
    """Count mentions of each ticker across all tweets.

    Args:
        tweets: List of Tweet objects or dicts

    Returns:
        Dict mapping ticker -> mention count
    """
    counts = {}
    for tweet in tweets:
        # Handle both Tweet objects and dicts
        if isinstance(tweet, Tweet):
            text = tweet.text
            ticker = tweet.ticker
        elif isinstance(tweet, dict):
            text = tweet.get('text', '')
            ticker = tweet.get('ticker', '')
        else:
            continue

        # Count $TICKER patterns in text
        ticker_matches = re.findall(r'\$([A-Z]{1,5})', text)
        for t in ticker_matches:
            counts[t] = counts.get(t, 0) + 1

        # Also count explicit ticker field
        if ticker and ticker not in [t for t in ticker_matches]:
            counts[ticker] = counts.get(ticker, 0) + 1

    return counts


def validate_ticker_frequency(tweets: List, max_mentions: int = None) -> tuple[List[str], Dict[str, int]]:
    """Check for tickers that appear too many times.

    Args:
        tweets: List of Tweet objects or dicts
        max_mentions: Maximum allowed mentions (default from config)

    Returns:
        tuple: (list of over-mentioned tickers, full counts dict)
    """
    # Get threshold from config
    if max_mentions is None:
        try:
            from config import MARKETING_THRESHOLDS
            max_mentions = MARKETING_THRESHOLDS.get('max_ticker_mentions_per_week', 4)
        except ImportError:
            max_mentions = 4

    counts = count_ticker_mentions(tweets)
    over_mentioned = [t for t, c in counts.items() if c > max_mentions]

    return over_mentioned, counts


def validate_tweet_lengths(tweets: List, auto_truncate: bool = True) -> List:
    """Validate tweet lengths and auto-truncate any over 280 chars.

    Args:
        tweets: List of Tweet objects or dicts
        auto_truncate: If True, automatically truncate overlong tweets (default: True)

    Returns:
        List with overlong tweets truncated (if auto_truncate=True)
    """
    warnings = []
    truncated_count = 0

    for i, tweet in enumerate(tweets):
        # Handle both Tweet objects and dicts
        if isinstance(tweet, Tweet):
            text = tweet.text
            tweet_id = tweet.id
        elif isinstance(tweet, dict):
            text = tweet.get('text', '')
            tweet_id = tweet.get('id', f'tweet_{i}')
        else:
            continue

        length = len(text)
        if length > TWITTER_MAX_LENGTH:
            over_by = length - TWITTER_MAX_LENGTH

            if auto_truncate and isinstance(tweet, dict):
                # Truncate at word boundary with ellipsis
                truncate_at = TWITTER_MAX_LENGTH - 3  # Room for "..."
                truncated = text[:truncate_at].rsplit(' ', 1)[0] + '...'

                # Ensure we actually shortened it (in case of very long word)
                if len(truncated) > TWITTER_MAX_LENGTH:
                    truncated = text[:truncate_at] + '...'

                tweet['text'] = truncated
                tweet['_was_truncated'] = True
                tweet['_original_length'] = length
                truncated_count += 1
                warnings.append(f"    🔧 Tweet {tweet_id}: truncated from {length} to {len(truncated)} chars")
            else:
                warnings.append(f"    ⚠️ Tweet {tweet_id}: {length} chars (over by {over_by})")
                if isinstance(tweet, dict):
                    tweet['_length_warning'] = f"Over {TWITTER_MAX_LENGTH} by {over_by} chars - needs editing"

    if warnings:
        print("\n  📏 TWEET LENGTH VALIDATION:")
        for warning in warnings:
            print(warning)
        if truncated_count > 0:
            print(f"\n  🔧 Auto-truncated {truncated_count} tweet(s) to fit {TWITTER_MAX_LENGTH} character limit.\n")
    else:
        print(f"  ✅ All tweets under {TWITTER_MAX_LENGTH} characters")

    return tweets


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

    # VALIDATION: Check ticker frequency
    over_mentioned, ticker_counts = validate_ticker_frequency(serialized)
    if over_mentioned:
        print(f"\n  ⚠️  TICKER FREQUENCY WARNING:")
        for ticker in over_mentioned:
            print(f"     ${ticker} mentioned {ticker_counts[ticker]} times (max recommended: 4)")
        print(f"     Consider diversifying content to avoid engagement fatigue.\n")

    # VALIDATION: Check tweet lengths before saving
    serialized = validate_tweet_lengths(serialized)

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

CRITICAL BRANDING REQUIREMENT:
- ALWAYS use "TEAL signal" when referring to our buy signals
- NEVER use "buy signal", "proprietary entry", "PASS signal", or "proprietary signal"
- Our 5-gate system produces "TEAL signals" - this is our brand identity
- Tweet 5 (CTA) MUST mention "TEAL signals" at least once

Topics you cover:
- Bottleneck investing (infrastructure, supply chain)
- Systematic stock selection methodology
- Theme momentum analysis
- Risk management principles
- Market psychology and discipline

BANNED TERMS (never use):
- "Forensic Audit", "Gate 5", "5th Gate"
- "Volatility Expansion Criteria"
- "Institutional Accumulation Divergence"
- "Structural Pivot Confirmation"
- "Capital Preservation Protocol"
- "HMA", "Banker indicator", "BoS"
- "Roth IRA", "401k", "PDT rule"

STYLE:
- Confident but not arrogant
- Data-driven with specific examples
- Accessible to regular investors
- No jargon, no banned technical terms
- When showing historical gains, ALWAYS include holding period (e.g., "+90% in 6 months")
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
5. Tweet 3: Insight - your systematic solution (mention "5-gate system")
6. Tweet 4: Proof - specific example WITH HOLDING PERIOD (e.g., "$NVDA +90% in 6 months", never show gain without timeframe)
7. Tweet 5: CTA - MUST mention "TEAL signals" and link to https://sterlingsignals.substack.com

CRITICAL RULES:
- Tweet 5 MUST contain the phrase "TEAL signal" or "TEAL signals"
- Any percentage gains MUST include holding period (e.g., "+50% in 3 months")
- NEVER use: "buy signal", "Forensic Audit", "proprietary entry", hashtags
- DO NOT end with hashtags like #SystematicInvesting - just end with the Substack link

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

        # MASTER_TODO_v2: Comprehensive thread validation and auto-fix
        tweets = validate_and_fix_thread_tweets(tweets)

        # Validate each tweet for banned terms
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
        'context': 'Explain the concept of second-order investing: instead of buying the obvious trend (AI), buy what the trend NEEDS that is in shortage (power, cooling). Use current examples like data centers, grid infrastructure. Mention that our 5-gate system generates TEAL signals for these bottleneck plays.'
    },
    {
        'topic': 'The 5-Gate System',
        'context': 'Explain systematic stock selection process that produces TEAL signals. Focus on: starting with 1,800 stocks, filtering through momentum criteria, institutional accumulation signals, sector alignment, and final review. Emphasize how filtering down to 3-5 TEAL signals weekly reduces noise. DO NOT mention: Forensic Audit, HMA, Banker indicator, BoS, or any specific thresholds.'
    },
    {
        'topic': 'Systematic Risk Management',
        'context': 'Explain systematic stop discipline: predetermined exits, position sizing, never fighting the system. "No ego, just execution." When a stop is hit, the system worked as designed. DO NOT say "Capital Preservation Protocol" - use "systematic stop" or "trailing stop".'
    },
    {
        'topic': 'Following Smart Money',
        'context': 'Explain how tracking institutional capital flows helps identify winning themes. Focus on sector rotation, following where big money is accumulating, and avoiding crowded retail trades. Our 5-gate system detects institutional accumulation before breakouts, generating TEAL signals. DO NOT say "Institutional Accumulation Divergence".'
    },
    {
        'topic': 'Beat the Index',
        'context': 'Explain why systematic momentum selection beats passive indexing: concentration in best TEAL signal setups, active sector rotation timing, disciplined risk management vs buy-and-hope. Reference SPY underperformance in choppy markets. Our TEAL signals focus capital on highest-conviction opportunities.'
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
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tweets via Claude API")
    parser.add_argument("--briefing", type=str, help="Path to newsletter briefing")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no API)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if tweets exist")
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

    # IDEMPOTENCY CHECK: Prevent duplicate generation
    output_dir = Path(args.output) if args.output else TWEETS_DIR
    already_generated, pending_count, queue_date = check_already_generated(
        output_dir, content.scan_date
    )

    if already_generated and not args.force:
        print(f"\n  ⚠️  TWEETS ALREADY GENERATED")
        print(f"     {pending_count} pending tweets found (scheduled from {queue_date})")
        print(f"     Use --force to regenerate and replace existing content")
        print("\n" + "═" * 60)
        return

    if args.force and already_generated:
        print(f"\n  ⚠️  Forcing regeneration ({pending_count} existing tweets will be replaced)")

    # Check for cold streak (circuit breaker)
    cold_streak_active = False
    if SIGNAL_TRACKER_AVAILABLE:
        cold_streak = check_cold_streak()
        if cold_streak.get('in_cold_streak'):
            print(f"\n  ⚠️  COLD STREAK DETECTED")
            print(f"     {cold_streak.get('reason')}")
            print(f"     Reducing position-focused content (GAP 38 enforcement)")
            cold_streak_active = True  # GAP 38 fix: Actually enforce the circuit breaker
        elif cold_streak.get('recent_trades', 0) > 0:
            win_rate = cold_streak.get('win_rate', 0)
            print(f"     • Recent win rate: {win_rate:.0%} ({cold_streak.get('recent_trades')} trades)")

    # Generate tweets (pass cold_streak_active for GAP 38 enforcement)
    tweets = generate_all_tweets(content, mock=args.mock, cold_streak_active=cold_streak_active)

    # Save output (output_dir already defined during idempotency check)
    queue_file = save_tweets(tweets, output_dir)

    # Print summary
    print_summary(tweets)

    print(f"\n  ✅ Generated {len(tweets)} tweets")
    print(f"  📁 Content queue: {queue_file}")
    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
