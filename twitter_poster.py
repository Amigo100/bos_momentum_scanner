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
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass  # dotenv not required if env vars set directly

try:
    import tweepy
except ImportError:
    print("ERROR: tweepy not installed. Run: pip install tweepy")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"
QUEUE_FILE = TRADES_DIR / "content_queue.json"

# Slot times (Eastern Time)
SLOT_TIMES = {
    1: "08:00",  # Pre-market
    2: "10:00",  # Morning (30min after open)
    3: "12:30",  # Midday
    4: "15:30",  # Power Hour (CRITICAL)
    5: "18:00",  # After-hours
}


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
    # MASTER_TODO_v2 compliant
    CRITICAL_BANNED = [
        # Strategy internals
        'HMA', '20% stop', 'Banker >=', 'Beta >=', 'BoS',
        # Wrong audience (UK ISA, not US Roth)
        'Roth IRA', 'Roth', 'PDT', '401k',
        # Internal terms that leaked (MASTER_TODO_v2)
        'Capital Preservation Protocol', 'Forensic Audit',
        'Volatility Expansion Criteria', '5th Gate', 'Gate 5',
        # Non-branded signal terms (use TEAL signal)
        'proprietary entry', 'proprietary signal',
    ]

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

    # 5. Check tweet length
    char_count = sum(2 if ord(c) > 0xFFFF else 1 for c in text)
    if char_count > 280:
        return (False, f"BLOCKED: Tweet too long ({char_count} chars)")

    return (True, "Validation passed")


# ═══════════════════════════════════════════════════════════════════════════════
# X/TWITTER CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients() -> tuple:
    """Initialize Tweepy clients (v1.1 for media, v2 for tweets)."""
    
    # Get credentials from environment
    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_SECRET")
    
    missing = []
    if not api_key: missing.append("X_API_KEY")
    if not api_secret: missing.append("X_API_SECRET")
    if not access_token: missing.append("X_ACCESS_TOKEN")
    if not access_secret: missing.append("X_ACCESS_SECRET")
    
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    
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
    """
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute

    # Slot windows (in minutes from midnight, Eastern Time)
    # Slot 1: 07:00 - 09:00 (pre-market)
    # Slot 2: 09:00 - 12:00 (morning)
    # Slot 3: 12:00 - 15:00 (midday)
    # Slot 4: 15:00 - 17:00 (power hour)
    # Slot 5: 17:00 - 20:00 (after-hours)

    if current_time < 9 * 60:
        return 1
    elif current_time < 12 * 60:
        return 2
    elif current_time < 15 * 60:
        return 3
    elif current_time < 17 * 60:
        return 4
    elif current_time < 20 * 60:
        return 5
    else:
        return 0  # Outside posting hours
    

def find_next_content(queue: list[Dict], force: bool = False, target_slot: Optional[int] = None) -> Optional[Dict]:
    """Find the next content item (tweet or thread) to post based on schedule and slot.

    Args:
        queue: List of content dictionaries (tweets or threads)
        force: If True, post first pending regardless of schedule
        target_slot: If specified, only consider items for this slot (1-5)

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
            # If it's today, check slot
            if scheduled_date == today:
                if slot <= current_slot:
                    return tweet
            else:
                # Past due - post it
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


def post_tweet(client_v2, api_v1, tweet: Dict, dry_run: bool = False) -> bool:
    """Post a single tweet with optional media."""

    text = tweet.get("text", "")
    image_path = tweet.get("image_path")
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
        print(f"\n  🔸 DRY RUN - would post this tweet")
        if image_path:
            print(f"  🔸 Would attach: {image_path}")
        return True
    
    try:
        # Upload media if present
        media_ids = None
        if image_path:
            media_id = upload_media(api_v1, image_path)
            if media_id:
                media_ids = [media_id]
        
        # Post tweet
        response = client_v2.create_tweet(
            text=text,
            media_ids=media_ids
        )
        
        posted_tweet_id = response.data['id']
        print(f"\n  ✅ Posted! Tweet ID: {posted_tweet_id}")
        print(f"  🔗 https://x.com/i/status/{posted_tweet_id}")

        # Update tweet record
        tweet['status'] = 'posted'
        tweet['posted_at'] = datetime.now().isoformat()
        tweet['tweet_id'] = posted_tweet_id

        # Register signal tweets for future quoting (milestone celebrations)
        category = tweet.get('category', '')
        if category in ['teal_signal', 'buy_signal', 'thread_buy_signal'] and tweet.get('ticker'):
            try:
                from self_quote_tracker import register_signal_tweet
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
    quote the original TEAL signal announcement.

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

def main() -> int:
    parser = argparse.ArgumentParser(description="Post scheduled tweets/threads to X")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted")
    parser.add_argument("--force", action="store_true", help="Post next pending regardless of schedule")
    parser.add_argument("--queue", type=str, help="Path to content queue JSON")
    parser.add_argument("--slot", type=str, default="all",
                        help="Which slot to post (1-5 or 'all')")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  TWITTER POSTER - Automated X Posting")
    print("═" * 60)

    # Load queue
    queue_file = Path(args.queue) if args.queue else QUEUE_FILE
    print(f"\n  📂 Queue: {queue_file}")

    queue = load_queue(queue_file)

    pending = [t for t in queue if t.get("status") == "pending"]
    posted = [t for t in queue if t.get("status") == "posted"]
    threads = [t for t in queue if t.get("is_thread", False)]

    print(f"  📊 Status: {len(posted)} posted, {len(pending)} pending")
    if threads:
        thread_pending = [t for t in threads if t.get("status") == "pending"]
        print(f"  🧵 Threads: {len(thread_pending)} pending of {len(threads)} total")

    # Find next content item (tweet or thread) - filter by slot if specified
    target_slot = None if args.slot == "all" else int(args.slot) if args.slot.isdigit() else None
    content_item = find_next_content(queue, force=args.force, target_slot=target_slot)

    if not content_item:
        print(f"\n  ℹ️  No content due right now")
        print(f"     Current slot: {get_current_slot()} ({SLOT_TIMES.get(get_current_slot(), 'outside hours')})")
        print(f"     Today: {datetime.now().strftime('%Y-%m-%d')}")
        return 0

    # Initialize clients (skip for dry run if no credentials)
    if args.dry_run:
        client_v2, api_v1 = None, None
    else:
        client_v2, api_v1 = get_clients()

    # Check for duplicate content before posting
    tweet_text = content_item.get('text', '')
    if is_duplicate_content(tweet_text, queue):
        print(f"\n  ⚠️  DUPLICATE DETECTED - This exact tweet was already posted")
        print(f"     Skipping to prevent duplicate content on X")
        # Mark as skipped so it doesn't get picked up again
        content_item['status'] = 'skipped'
        content_item['skip_reason'] = 'duplicate_content'
        if not args.dry_run:
            save_queue(queue, queue_file)
        return 0

    # Dispatch based on content type (thread vs single tweet)
    if content_item.get('is_thread', False):
        print(f"\n  🧵 Detected: THREAD")
        success = post_thread(client_v2, api_v1, content_item, dry_run=args.dry_run)
    else:
        print(f"\n  📝 Detected: SINGLE TWEET")
        success = post_tweet(client_v2, api_v1, content_item, dry_run=args.dry_run)

    # Save updated queue
    if not args.dry_run:
        save_queue(queue, queue_file)
        print(f"\n  💾 Queue updated: {queue_file}")

    print("\n" + "═" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
