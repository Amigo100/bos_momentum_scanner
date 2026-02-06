#!/usr/bin/env python3
"""
TWITTER POSTER - Automated X Posting with Media
================================================

Posts scheduled tweets to X with chart images attached.
Reads from content_queue.json, posts next pending tweet, updates status.

Usage:
    python twitter_poster.py              # Post next pending tweet
    python twitter_poster.py --dry-run    # Show what would be posted
    python twitter_poster.py --force      # Post regardless of schedule

Environment Variables Required:
    X_API_KEY
    X_API_SECRET  
    X_ACCESS_TOKEN
    X_ACCESS_SECRET
"""

import os
import sys
import json
import argparse
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo

# Load .env file if present (use explicit path relative to this script)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass  # dotenv not required if env vars set directly

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy not installed. Run: pip install tweepy")
    sys.exit(1)


# Import staleness config
try:
    from config import TWEET_STALENESS_DAYS
except ImportError:
    TWEET_STALENESS_DAYS = 3

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
TRADES_DIR = BASE_DIR / "trades"
QUEUE_FILE = TRADES_DIR / "content_queue.json"
DAILY_QUEUE_FILE = TRADES_DIR / "daily_content_queue.json"

# 7-slot system (Eastern Time)
# Slots 1, 6, 7 pull from the DAILY queue (fresh intraday content)
# Slots 2-5 pull from the WEEKLY queue (generated on Friday)
SLOT_TIMES = {
    1: "07:30",  # Pre-market (daily)
    2: "10:00",  # Morning (weekly — 30min after open)
    3: "12:30",  # Midday (weekly)
    4: "15:30",  # Power Hour (weekly — CRITICAL)
    5: "18:00",  # After-hours (weekly)
    6: "17:00",  # Late afternoon (daily)
    7: "18:30",  # Evening (daily)
}

# Map slot → queue source
DAILY_SLOTS = {1, 6, 7}     # Pull from daily_content_queue.json
WEEKLY_SLOTS = {2, 3, 4, 5}  # Pull from content_queue.json


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_duplicate_content(tweet_text: str, queue: List[Dict]) -> bool:
    """
    Check if this exact tweet text was already posted.

    Prevents posting duplicate tweets if the generator runs multiple times.

    Args:
        tweet_text: The text of the tweet to check
        queue: The content queue list

    Returns:
        True if a tweet with this exact text was already posted
    """
    normalized_text = tweet_text.strip()
    for item in queue:
        if item.get('status') == 'posted':
            posted_text = item.get('text', '').strip()
            if posted_text == normalized_text:
                return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER_TODO_v2: PRE-POST VALIDATION - LAST LINE OF DEFENSE
# ═══════════════════════════════════════════════════════════════════════════════

def validate_before_posting(tweet: Dict) -> tuple:
    """
    MASTER_TODO_v2: Final validation before posting to Twitter.

    This is the LAST LINE OF DEFENSE against posting invalid content.
    It runs right before the tweet is sent to the API.

    Args:
        tweet: Tweet dict with 'text' key

    Returns:
        Tuple of (can_post: bool, reason: str)
    """
    import re

    text = tweet.get('text', '')
    category = tweet.get('category', '')

    # BANNED_TERMS to check (critical subset for speed)
    # Single source of truth: config/banned_terms.py
    from config.banned_terms import CRITICAL_BANNED

    # KILLED categories
    KILLED_CATEGORIES = ['roth_ira', 'pdt_friendly', 'position_update', 'weekly_wins']

    # 1. Check for negative P&L (losers)
    negative_pnl = re.findall(r'-\d+\.?\d*%', text)
    if negative_pnl:
        return (False, f"BLOCKED: Negative P&L in tweet: {negative_pnl}")

    # 2. Check for critical banned terms
    text_lower = text.lower()
    for term in CRITICAL_BANNED:
        if term.lower() in text_lower:
            return (False, f"BLOCKED: Banned term '{term}' in tweet")

    # 2b. Check for old color system (word-boundary)
    old_colors = ['teal', 'purple', 'violet', 'amber']
    for color in old_colors:
        if re.search(rf'\b{color}\b', text_lower):
            return (False, f"BLOCKED: Old color '{color}' - use GREEN/RED instead")
    if '🟣' in text:
        return (False, "BLOCKED: Old purple emoji - use RED emoji")

    # 3. Check for killed categories
    if category in KILLED_CATEGORIES:
        return (False, f"BLOCKED: Killed category '{category}'")

    # 4. Check for US-specific content (wrong audience)
    us_patterns = [
        r'\broth\s*ira\b',
        r'\b401\s*\(?k\)?\b',
        r'\bpdt\s*(rule)?\b',
        r'pattern\s+day\s+trad',
    ]
    for pattern in us_patterns:
        if re.search(pattern, text_lower):
            return (False, f"BLOCKED: US-specific content ({pattern})")

    # 5. Full marketing vocabulary check (secondary defense)
    try:
        from config.marketing_vocabulary import validate_content
        mv_valid, mv_violations = validate_content(text)
        if not mv_valid:
            return (False, f"BLOCKED: Marketing vocabulary violation: {mv_violations[0]}")
    except ImportError:
        pass  # marketing_vocabulary not available

    # 6. Check tweet length
    char_count = sum(2 if ord(c) > 0xFFFF else 1 for c in text)
    if char_count > 280:
        return (False, f"BLOCKED: Tweet too long ({char_count} chars)")

    return (True, "Validation passed")


# ═══════════════════════════════════════════════════════════════════════════════
# X/TWITTER CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients(account_key: str = 'main') -> tuple:
    """Initialize Tweepy clients (v1.1 for media, v2 for tweets).

    Args:
        account_key: Account identifier ('main', 'account2', 'account3').
                     Determines which env var prefix to use.

    Returns:
        Tuple of (client_v2, api_v1) or (None, None) if credentials missing.
    """
    try:
        from config import TWITTER_ACCOUNTS
        account = TWITTER_ACCOUNTS.get(account_key, TWITTER_ACCOUNTS['main'])
        prefix = account['env_prefix']
    except (ImportError, KeyError):
        prefix = 'X'

    # Get credentials from environment using account-specific prefix
    api_key = os.environ.get(f"{prefix}_API_KEY")
    api_secret = os.environ.get(f"{prefix}_API_SECRET")
    access_token = os.environ.get(f"{prefix}_ACCESS_TOKEN")
    access_secret = os.environ.get(f"{prefix}_ACCESS_SECRET")

    missing = []
    if not api_key: missing.append(f"{prefix}_API_KEY")
    if not api_secret: missing.append(f"{prefix}_API_SECRET")
    if not access_token: missing.append(f"{prefix}_ACCESS_TOKEN")
    if not access_secret: missing.append(f"{prefix}_ACCESS_SECRET")

    if missing:
        print(f"  ⚠ Missing credentials for {account_key}: {', '.join(missing)}")
        return None, None

    # v2 Client for posting tweets
    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    # v1.1 API for media upload (v2 doesn't support media upload well yet)
    auth = tweepy.OAuth1UserHandler(
        api_key, api_secret,
        access_token, access_secret
    )
    api_v1 = tweepy.API(auth)

    return client_v2, api_v1


def get_queue_path(account_key: str = 'main') -> Path:
    """Get the content queue file path for a given account.

    Args:
        account_key: Account identifier ('main', 'account2', 'account3').

    Returns:
        Path to the account's content_queue JSON file.
    """
    try:
        from config import TWITTER_ACCOUNTS
        account = TWITTER_ACCOUNTS.get(account_key, TWITTER_ACCOUNTS['main'])
        return TRADES_DIR / account['queue_file']
    except (ImportError, KeyError):
        return QUEUE_FILE


def get_daily_queue_path(account_key: str = 'main') -> Path:
    """Get the DAILY content queue file path for a given account.

    Daily queues hold intraday content generated by the daily scanner.

    Args:
        account_key: Account identifier ('main', 'account2', 'account3').

    Returns:
        Path to the account's daily_content_queue JSON file.
    """
    daily_names = {
        'main': 'daily_content_queue.json',
        'account2': 'daily_content_queue_account2.json',
        'account3': 'daily_content_queue_account3.json',
    }
    return TRADES_DIR / daily_names.get(account_key, 'daily_content_queue.json')


def get_queue_for_slot(slot: int, account_key: str = 'main') -> Path:
    """Select the correct queue file (weekly vs daily) based on slot number.

    Slots 1, 6, 7 → daily queue (fresh intraday content)
    Slots 2-5     → weekly queue (Friday-generated content)

    Args:
        slot: Slot number (1-7)
        account_key: Account identifier

    Returns:
        Path to the appropriate queue file
    """
    if slot in DAILY_SLOTS:
        return get_daily_queue_path(account_key)
    return get_queue_path(account_key)


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def load_queue(queue_file: Path) -> list[Dict]:
    """Load content queue from JSON file.

    Exits with error if file is missing or corrupted (JSON parse error).
    """
    if not queue_file.exists():
        print(f"ERROR: Queue file not found: {queue_file}")
        sys.exit(1)

    try:
        with open(queue_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse queue file: {e}")
        print(f"       The content_queue.json may be corrupted.")
        print(f"       File: {queue_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load queue file: {e}")
        sys.exit(1)


def save_queue(queue: list[Dict], queue_file: Path) -> None:
    """Save updated queue back to JSON file (atomic write).

    Uses write-to-temp-then-rename pattern to prevent corruption
    if the process is interrupted mid-write.
    """
    # Write to temp file in same directory, then rename (atomic on POSIX)
    temp_fd, temp_path = tempfile.mkstemp(
        suffix='.json',
        dir=queue_file.parent,
        prefix='.queue_tmp_'
    )
    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(queue, f, indent=2)
        # Atomic rename (on POSIX systems)
        shutil.move(temp_path, queue_file)
    except Exception as e:
        # Clean up temp file if something went wrong
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"ERROR: Failed to save queue: {e}")
        raise


def get_current_slot() -> int:
    """Determine current time slot based on Eastern Time (ET).

    Uses timezone-aware datetime to correctly handle both local and CI environments.

    7-slot system:
        Slot 1: 07:00 - 09:30   (daily — pre-market)
        Slot 2: 09:30 - 12:00   (weekly — morning)
        Slot 3: 12:00 - 14:30   (weekly — midday)
        Slot 4: 14:30 - 16:30   (weekly — power hour)
        Slot 5: 16:30 - 17:15   (weekly — after-hours)
        Slot 6: 17:15 - 18:15   (daily — late afternoon)
        Slot 7: 18:15 - 20:00   (daily — evening)
    """
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    current_time = now.hour * 60 + now.minute

    if current_time < 9 * 60 + 30:      # < 09:30
        return 1
    elif current_time < 12 * 60:         # < 12:00
        return 2
    elif current_time < 14 * 60 + 30:    # < 14:30
        return 3
    elif current_time < 16 * 60 + 30:    # < 16:30
        return 4
    elif current_time < 17 * 60 + 15:    # < 17:15
        return 5
    elif current_time < 18 * 60 + 15:    # < 18:15
        return 6
    elif current_time < 20 * 60:         # < 20:00
        return 7
    else:
        return 0  # Outside posting hours
    

def find_next_content(queue: list[Dict], force: bool = False, target_slot: Optional[int] = None) -> Optional[Dict]:
    """Find the next content item (tweet or thread) to post based on schedule and slot.

    Args:
        queue: List of content dictionaries (tweets or threads)
        force: If True, post first pending regardless of schedule
        target_slot: If specified, only consider items for this slot (1-7)

    Returns:
        Next pending content item (single tweet or thread), or None if nothing due
    """
    # Use Eastern Time for date comparison to match schedule
    et = ZoneInfo("America/New_York")
    today = datetime.now(et).strftime("%Y-%m-%d")
    current_slot = get_current_slot()

    for tweet in queue:
        if tweet.get("status") != "pending":
            continue

        scheduled_date = tweet.get("scheduled_date", "")
        slot = tweet.get("slot", 0)

        # Filter by target slot if specified
        if target_slot is not None and slot != target_slot:
            continue

        # If forcing, post first pending tweet (that matches slot filter)
        if force:
            return tweet

        # Check if this tweet is due
        if scheduled_date <= today:
            # Skip stale tweets (> 3 days past scheduled date)
            if scheduled_date < today:
                try:
                    sched_dt = datetime.strptime(scheduled_date, "%Y-%m-%d")
                    today_dt = datetime.strptime(today, "%Y-%m-%d")
                    days_overdue = (today_dt - sched_dt).days
                    if days_overdue > TWEET_STALENESS_DAYS:
                        tweet['status'] = 'expired'
                        tweet['skip_reason'] = f'Stale: {days_overdue} days past scheduled date'
                        continue
                except ValueError:
                    pass  # Unparseable date — let it through

            # If it's today, check slot
            if scheduled_date == today:
                if slot <= current_slot:
                    return tweet
            else:
                # Past due (within 3-day window) - post it
                return tweet

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# POSTING
# ═══════════════════════════════════════════════════════════════════════════════

def upload_media(api_v1, image_path: str) -> Optional[str]:
    """Upload image to X and return media_id."""
    
    # Handle relative paths
    full_path = Path(image_path)
    if not full_path.is_absolute():
        full_path = BASE_DIR / image_path
    
    if not full_path.exists():
        # Try under trades/
        alt_path = TRADES_DIR / image_path
        if alt_path.exists():
            full_path = alt_path
        else:
            print(f"  ⚠ Image not found: {image_path}")
            return None
    
    try:
        print(f"  📤 Uploading: {full_path.name}")
        media = api_v1.media_upload(str(full_path))
        return media.media_id_string
    except Exception as e:
        print(f"  ✗ Media upload failed: {e}")
        return None


def _is_transient_error(e: Exception) -> bool:
    """Check if a tweepy error is transient (worth retrying)."""
    err_str = str(e).lower()
    transient_indicators = ['rate limit', '429', 'timeout', 'connection', '503', '502', 'server error']
    return any(indicator in err_str for indicator in transient_indicators)


def post_tweet(client_v2, api_v1, tweet: Dict, dry_run: bool = False) -> bool:
    """Post a single tweet with optional media."""

    text = tweet.get("text", "")
    # Support both legacy 'image_path' and new 'chart_path' fields
    image_path = tweet.get("chart_path") or tweet.get("image_path")
    tweet_id = tweet.get("id", "unknown")

    # MASTER_TODO_v2: Pre-post validation - LAST LINE OF DEFENSE
    can_post, reason = validate_before_posting(tweet)
    if not can_post:
        print(f"\n  🚨 {reason}")
        print(f"  ⛔ Tweet {tweet_id} BLOCKED from posting")
        tweet['status'] = 'blocked'
        tweet['block_reason'] = reason
        return False

    print(f"\n  📝 Tweet: {tweet_id}")
    print(f"  📅 Scheduled: {tweet.get('scheduled_date')} slot {tweet.get('slot')}")
    print(f"  📊 Category: {tweet.get('category')}")
    if tweet.get("ticker"):
        print(f"  💹 Ticker: ${tweet.get('ticker')}")
    print(f"\n  Text ({len(text)} chars):")
    print(f"  ┌{'─' * 50}")
    for line in text.split('\n'):
        print(f"  │ {line}")
    print(f"  └{'─' * 50}")

    if dry_run:
        print(f"\n  DRY RUN - would post this tweet")
        if image_path:
            print(f"  Would attach: {image_path}")
        if tweet.get('template_id'):
            print(f"  Template: {tweet.get('template_id')}")
        print(f"  Method: {tweet.get('generation_method', 'unknown')}")
        return True
    
    try:
        # Upload media if present
        media_ids = None
        if image_path:
            media_id = upload_media(api_v1, image_path)
            if media_id:
                media_ids = [media_id]

        # Post tweet with retry logic for transient failures
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = client_v2.create_tweet(
                    text=text,
                    media_ids=media_ids
                )
                break
            except tweepy.TweepyException as e:
                if attempt < max_retries - 1 and _is_transient_error(e):
                    wait = 2 ** (attempt + 1)
                    print(f"  Retry {attempt+1}/{max_retries} in {wait}s... ({e})")
                    time.sleep(wait)
                else:
                    raise

        posted_tweet_id = response.data['id']
        print(f"\n  ✅ Posted! Tweet ID: {posted_tweet_id}")
        print(f"  🔗 https://x.com/i/status/{posted_tweet_id}")

        # Update tweet record
        tweet['status'] = 'posted'
        tweet['posted_at'] = datetime.now().isoformat()
        tweet['tweet_id'] = posted_tweet_id

        # Log generation method for analytics
        gen_method = tweet.get('generation_method', 'unknown')
        template_id = tweet.get('template_id', None)
        if template_id:
            print(f"  Template: {template_id} (method: {gen_method})")
        else:
            print(f"  Generated via: {gen_method}")

        # Register signal tweets for future quoting (milestone celebrations)
        category = tweet.get('category', '')
        if category in ['buy_signal', 'thread_buy_signal'] and tweet.get('ticker'):
            try:
                from distribution.self_quote_tracker import register_signal_tweet
                register_signal_tweet(
                    ticker=tweet['ticker'],
                    tweet_id=posted_tweet_id,
                    entry_price=float(tweet.get('entry_price', 0) or 0),
                    signal_date=datetime.now().strftime('%Y-%m-%d')
                )
            except Exception as e:
                print(f"  ⚠️ Could not register for quote tracking: {e}")

        return True

    except tweepy.TweepyException as e:
        print(f"\n  ✗ Failed to post: {e}")
        tweet['status'] = 'failed'
        tweet['error'] = str(e)
        return False


def post_quote_tweet(
    client_v2,
    api_v1,
    text: str,
    quote_tweet_id: str,
    dry_run: bool = False
) -> Optional[str]:
    """
    Post a quote tweet referencing an original signal tweet.

    Used for milestone celebrations (25%, 50%, 100% gains) to
    quote the original GREEN signal announcement.

    Args:
        client_v2: Tweepy v2 client for posting
        api_v1: Tweepy v1.1 API (for future media support)
        text: Tweet text to post
        quote_tweet_id: Twitter ID of the original tweet to quote
        dry_run: If True, print without posting

    Returns:
        New tweet ID if successful, None if failed
    """
    # Validate content before posting
    temp_tweet = {"text": text, "category": "hall_of_fame"}
    can_post, reason = validate_before_posting(temp_tweet)
    if not can_post:
        print(f"  🚨 Cannot post quote: {reason}")
        return None

    print(f"\n  📝 Quote Tweet")
    print(f"  🔗 Quoting: {quote_tweet_id}")
    print(f"\n  Text ({len(text)} chars):")
    print(f"  ┌{'─' * 50}")
    for line in text.split('\n'):
        print(f"  │ {line}")
    print(f"  └{'─' * 50}")

    if dry_run:
        print(f"  🔸 DRY RUN - Would quote tweet {quote_tweet_id}")
        print(f"  🔸 Text: {text[:100]}...")
        return "dry_run_id"

    try:
        response = client_v2.create_tweet(
            text=text,
            quote_tweet_id=quote_tweet_id
        )
        new_tweet_id = response.data['id']
        print(f"\n  ✅ Posted quote tweet: {new_tweet_id}")
        print(f"  🔗 https://x.com/i/status/{new_tweet_id}")
        return new_tweet_id

    except Exception as e:
        print(f"  ✗ Failed to post quote: {e}")
        return None


def post_thread(client_v2, api_v1, thread_item: Dict, dry_run: bool = False) -> bool:
    """Post a 5-tweet thread with reply chaining.

    Posts tweets sequentially, with each tweet (2-5) replying to the previous one.
    This creates a connected thread on X.

    Args:
        client_v2: Tweepy v2 client for posting tweets
        api_v1: Tweepy v1.1 API for media upload
        thread_item: Queue item with thread_tweets array
        dry_run: If True, print what would be posted without posting

    Returns:
        True if all tweets posted successfully, False otherwise
    """
    thread_tweets = thread_item.get('thread_tweets', [])
    thread_id = thread_item.get('id', 'unknown')
    thread_topic = thread_item.get('thread_topic', 'Thread')

    if not thread_tweets:
        print(f"  ⚠ No thread tweets found in {thread_id}")
        return False

    print(f"\n  🧵 Thread: {thread_id}")
    print(f"  📚 Topic: {thread_topic}")
    print(f"  📊 Tweets: {len(thread_tweets)}")
    print(f"  📅 Scheduled: {thread_item.get('scheduled_date')} slot {thread_item.get('slot')}")

    reply_to_id = None  # First tweet has no parent

    for tweet in thread_tweets:
        text = tweet.get('text', '')
        number = tweet.get('number', 0)
        image_path = tweet.get('image_path')

        print(f"\n  ┌─ Tweet {number}/{len(thread_tweets)} ({len(text)} chars)")
        print(f"  │")
        for line in text.split('\n'):
            print(f"  │ {line}")
        print(f"  │")
        if image_path:
            print(f"  │ 📷 Image: {image_path}")
        if reply_to_id:
            print(f"  │ ↩️  Replying to: {reply_to_id}")
        print(f"  └─")

        if dry_run:
            print(f"  🔸 DRY RUN - would post tweet {number}/{len(thread_tweets)}")
            tweet['tweet_id'] = f"dry_run_{thread_id}_{number}"
            reply_to_id = tweet['tweet_id']
            continue

        try:
            # Upload media if present (often on tweet 4 for charts)
            media_ids = None
            if image_path:
                media_id = upload_media(api_v1, image_path)
                if media_id:
                    media_ids = [media_id]

            # Post tweet (with in_reply_to for tweets 2-5)
            response = client_v2.create_tweet(
                text=text,
                media_ids=media_ids,
                in_reply_to_tweet_id=reply_to_id  # None for first tweet
            )

            posted_tweet_id = response.data['id']
            tweet['tweet_id'] = posted_tweet_id
            tweet['posted_at'] = datetime.now().isoformat()

            print(f"  ✅ Posted! ID: {posted_tweet_id}")

            # Next tweet replies to this one (creates the chain)
            reply_to_id = posted_tweet_id

            # Rate limit protection (1 second between tweets)
            if number < len(thread_tweets):
                time.sleep(1)

        except tweepy.TweepyException as e:
            print(f"\n  ✗ Thread failed at tweet {number}: {e}")
            thread_item['thread_status'] = 'partial'
            thread_item['error'] = str(e)
            return False

    # All tweets posted successfully
    thread_item['thread_status'] = 'complete'
    thread_item['status'] = 'posted'
    thread_item['posted_at'] = datetime.now().isoformat()
    thread_item['tweet_id'] = thread_tweets[0].get('tweet_id')  # Link to thread head

    print(f"\n  🎉 Thread complete!")
    print(f"  🔗 https://x.com/i/status/{thread_item['tweet_id']}")

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def post_for_account(account_key: str, args, target_slot) -> int:
    """Post content for a single account.

    Selects the correct queue (weekly vs daily) based on slot:
      - Slots 1, 6, 7 → daily_content_queue*.json
      - Slots 2-5      → content_queue*.json

    If --queue is given explicitly, that overrides the automatic selection.

    Args:
        account_key: Account identifier ('main', 'account2', 'account3').
        args: Parsed CLI arguments.
        target_slot: Target slot number or None for 'all'.

    Returns:
        0 on success, 1 on failure.
    """
    # If a specific queue was given on CLI, use it
    if args.queue:
        queue_file = Path(args.queue)
    elif target_slot is not None:
        # Select queue based on which slot we are targeting
        queue_file = get_queue_for_slot(target_slot, account_key)
    else:
        # 'all' mode — determine from current time slot
        current = get_current_slot()
        if current == 0:
            # Outside posting hours — fall back to weekly queue
            queue_file = get_queue_path(account_key)
        else:
            queue_file = get_queue_for_slot(current, account_key)

    source_label = "daily" if queue_file.name.startswith("daily_") else "weekly"
    print(f"\n  📂 [{account_key}] Queue ({source_label}): {queue_file}")

    if not queue_file.exists():
        print(f"  ⚠ [{account_key}] Queue file not found, skipping")
        return 0

    queue = load_queue(queue_file)

    pending = [t for t in queue if t.get("status") == "pending"]
    posted = [t for t in queue if t.get("status") == "posted"]
    threads = [t for t in queue if t.get("is_thread", False)]

    print(f"  📊 [{account_key}] Status: {len(posted)} posted, {len(pending)} pending")
    if threads:
        thread_pending = [t for t in threads if t.get("status") == "pending"]
        print(f"  🧵 [{account_key}] Threads: {len(thread_pending)} pending of {len(threads)} total")

    content_item = find_next_content(queue, force=args.force, target_slot=target_slot)

    if not content_item:
        print(f"\n  ℹ️  [{account_key}] No content due right now")
        return 0

    # Initialize clients
    if args.dry_run:
        client_v2, api_v1 = None, None
    else:
        client_v2, api_v1 = get_clients(account_key)
        if client_v2 is None:
            print(f"  ⚠ [{account_key}] No credentials, skipping")
            return 0

    # Duplicate check
    tweet_text = content_item.get('text', '')
    if is_duplicate_content(tweet_text, queue):
        print(f"\n  ⚠️  [{account_key}] DUPLICATE DETECTED - skipping")
        content_item['status'] = 'skipped'
        content_item['skip_reason'] = 'duplicate_content'
        if not args.dry_run:
            save_queue(queue, queue_file)
        return 0

    # Post
    if content_item.get('is_thread', False):
        print(f"\n  🧵 [{account_key}] Detected: THREAD")
        success = post_thread(client_v2, api_v1, content_item, dry_run=args.dry_run)
    else:
        print(f"\n  📝 [{account_key}] Detected: SINGLE TWEET")
        success = post_tweet(client_v2, api_v1, content_item, dry_run=args.dry_run)

    if not args.dry_run:
        save_queue(queue, queue_file)
        print(f"\n  💾 [{account_key}] Queue updated: {queue_file}")

    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Post scheduled tweets/threads to X")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted")
    parser.add_argument("--force", action="store_true", help="Post next pending regardless of schedule")
    parser.add_argument("--queue", type=str, help="Path to content queue JSON")
    parser.add_argument("--slot", type=str, default="all",
                        help="Which slot to post (1-7 or 'all'). Slots 1/6/7=daily, 2-5=weekly")
    parser.add_argument("--account", type=str, default="main",
                        help="Account to post to (main, account2, account3, or all)")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  TWITTER POSTER - Automated X Posting")
    print("═" * 60)

    target_slot = None if args.slot == "all" else int(args.slot) if args.slot.isdigit() else None

    if args.account == "all":
        # Post to all accounts sequentially with staggered delays
        try:
            from config import TWITTER_ACCOUNTS
            accounts = list(TWITTER_ACCOUNTS.keys())
        except ImportError:
            accounts = ['main']

        result = 0
        for i, account_key in enumerate(accounts):
            print(f"\n{'─' * 60}")
            print(f"  === Account: {account_key} ===")
            ret = post_for_account(account_key, args, target_slot)
            if ret != 0:
                result = ret

            # Stagger posts between accounts (skip delay after last)
            if i < len(accounts) - 1:
                try:
                    from config import TWITTER_ACCOUNTS as accts
                    next_account = accounts[i + 1]
                    delay_min = accts[next_account]['offset_minutes'] - accts[account_key]['offset_minutes']
                    delay_sec = max(delay_min * 60, 0)
                except (ImportError, KeyError):
                    delay_sec = 600  # Default 10 min

                if delay_sec > 0 and not args.dry_run:
                    print(f"\n  ⏳ Waiting {delay_sec // 60} min before next account...")
                    time.sleep(delay_sec)

        print(f"\n{'═' * 60}")
        return result
    else:
        # Single account mode
        result = post_for_account(args.account, args, target_slot)
        print("\n" + "═" * 60)
        return result


if __name__ == "__main__":
    sys.exit(main())
