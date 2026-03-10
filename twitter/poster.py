#!/usr/bin/env python3
"""
TWITTER POSTER - Automated X Posting with Media
================================================

Posts live tweets/threads to X with chart images attached.
Reads from live_content_queue.json, posts next pending item, updates status.

Usage:
    python -m twitter.poster --dry-run          # Show what would be posted
    python -m twitter.poster --account main     # Post for main account
    python -m twitter.poster --account all      # Post for all accounts
    python -m twitter.poster --verify           # Check credentials

Environment Variables Required:
    X1_API_KEY, X1_API_SECRET, X1_ACCESS_TOKEN, X1_ACCESS_SECRET  (main)
    X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET  (account2)
    X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET  (account3)
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


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent

# Import queue file paths from config
try:
    from config import LIVE_QUEUE_FILE, TWITTER_OUTPUT
except ImportError:
    TWITTER_OUTPUT = BASE_DIR / "twitter" / "output"
    LIVE_QUEUE_FILE = TWITTER_OUTPUT / "live_content_queue.json"


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE QUEUE SUPPORT (Phase 5 — live tweet system)
# ═══════════════════════════════════════════════════════════════════════════════

# Account key → live queue variant mapping
LIVE_ACCOUNT_MAP = {
    "main": "variant_1",
    "account2": "variant_2",
    "account3": "variant_3",
}


def find_next_live_content(queue: List[Dict], account_key: str) -> Optional[Dict]:
    """Find next pending tweet from the live queue for a specific account.

    Live queue items use 'account' field (variant_1/variant_2/variant_3)
    instead of slot/scheduled_date.

    Args:
        queue: Live content queue list
        account_key: Account identifier ('main', 'account2', 'account3')

    Returns:
        Next pending item for this account, or None
    """
    target_variant = LIVE_ACCOUNT_MAP.get(account_key, "variant_1")
    for item in queue:
        if item.get("status") == "pending" and item.get("account") == target_variant:
            return item
    return None


def check_similarity_duplicate(text: str, queue: List[Dict], hours: int = 24) -> tuple:
    """Check if a tweet is too similar to recently posted tweets.

    Uses SequenceMatcher with 0.7 threshold within a time window.

    Args:
        text: Tweet text to check
        queue: Queue list to check against
        hours: Lookback window in hours

    Returns:
        Tuple of (is_duplicate: bool, reason: str)
    """
    from difflib import SequenceMatcher

    now = datetime.now(ZoneInfo("America/New_York"))
    text_lower = text.lower().strip()

    for item in queue:
        if item.get("status") != "posted":
            continue
        posted_at = item.get("posted_at")
        if not posted_at:
            continue
        try:
            posted_time = datetime.fromisoformat(posted_at)
            if posted_time.tzinfo is None:
                posted_time = posted_time.replace(tzinfo=ZoneInfo("UTC"))
            if (now - posted_time).total_seconds() > hours * 3600:
                continue
        except (ValueError, TypeError):
            continue

        similarity = SequenceMatcher(
            None, text_lower, item.get("text", "").lower().strip()
        ).ratio()
        if similarity > 0.7:
            return (True, f"Too similar ({similarity:.0%}) to tweet posted at {posted_at}")

    return (False, "")


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

    # 2. Check for critical banned terms (word-boundary for short terms)
    text_lower = text.lower()
    for term in CRITICAL_BANNED:
        term_lower = term.lower()
        if len(term) <= 4 and term.isascii():
            # Short terms need word-boundary matching to avoid false positives
            # e.g. "BST" matching inside "substack", "HMA" inside "PHARMA"
            if re.search(r'\b' + re.escape(term_lower) + r'\b', text_lower):
                return (False, f"BLOCKED: Banned term '{term}' in tweet")
        else:
            if term_lower in text_lower:
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
        from config.banned_terms import validate_content
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
        prefix = 'X1'

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


def verify_credentials(account_key: str = 'main') -> tuple:
    """Verify Twitter credentials by calling GET /2/users/me (read-only, free).

    Returns:
        Tuple of (success: bool, message: str).
    """
    client_v2, _ = get_clients(account_key)
    if client_v2 is None:
        return False, "credentials missing"
    try:
        me = client_v2.get_me()
        if me and me.data:
            return True, f"authenticated as @{me.data.username} (id: {me.data.id})"
        return False, "get_me() returned empty response"
    except tweepy.TweepyException as e:
        err = str(e)
        if "401" in err or "Unauthorized" in err:
            return False, f"401 Unauthorized — token invalid or expired: {err}"
        return False, f"auth failed: {err}"


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


def merge_cowork_queue(live_queue_file: Path) -> int:
    """Merge pending Cowork tweets into the live queue.

    Reads from the dedicated cowork queue file, appends un-merged pending
    items to the live queue, and marks them as merged in the cowork file.

    Returns number of items merged.
    """
    from config.output_paths import COWORK_QUEUE_FILE

    if not COWORK_QUEUE_FILE.exists():
        return 0

    try:
        with open(COWORK_QUEUE_FILE, 'r') as f:
            cowork_items = json.load(f)
    except (json.JSONDecodeError, Exception):
        return 0

    if not cowork_items:
        return 0

    # Load live queue (create empty if missing)
    if live_queue_file.exists():
        try:
            with open(live_queue_file, 'r') as f:
                live_items = json.load(f)
        except (json.JSONDecodeError, Exception):
            live_items = []
    else:
        live_items = []

    live_ids = {item.get("id") for item in live_items}

    new_items = [
        item for item in cowork_items
        if item.get("id") not in live_ids
        and item.get("status") == "pending"
        and not item.get("merged")
    ]

    if not new_items:
        return 0

    live_items.extend(new_items)
    save_queue(live_items, live_queue_file)

    # Mark merged in cowork queue
    merged_ids = {item["id"] for item in new_items}
    for item in cowork_items:
        if item.get("id") in merged_ids:
            item["merged"] = True
    save_queue(cowork_items, COWORK_QUEUE_FILE)

    print(f"  \U0001f500 Merged {len(new_items)} Cowork tweet(s) into live queue")
    return len(new_items)


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
        # Try under twitter/output/
        alt_path = TWITTER_OUTPUT / image_path
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
    # Support multi-chart (chart_paths list), single chart, and legacy image_path
    chart_paths = tweet.get("chart_paths") or []
    if not chart_paths:
        single = tweet.get("chart_path") or tweet.get("image_path")
        if single:
            chart_paths = [single]
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
    if tweet.get('scheduled_date'):
        print(f"  📅 Scheduled: {tweet.get('scheduled_date')} slot {tweet.get('slot')}")
    else:
        print(f"  📡 Mode: LIVE | Generated: {tweet.get('scheduled_time', tweet.get('generated_at', 'N/A'))}")
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
        if chart_paths:
            print(f"  Would attach {len(chart_paths)} image(s): {', '.join(chart_paths)}")
        if tweet.get('template_id'):
            print(f"  Template: {tweet.get('template_id')}")
        print(f"  Method: {tweet.get('generation_method', 'unknown')}")
        return True

    try:
        # Upload media if present (up to 4 images per Twitter API)
        media_ids = None
        if chart_paths:
            media_ids = []
            for path in chart_paths[:4]:
                media_id = upload_media(api_v1, path)
                if media_id:
                    media_ids.append(media_id)
            if not media_ids:
                media_ids = None  # No successful uploads

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
                from twitter.self_quote_tracker import register_signal_tweet
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
    if thread_item.get('scheduled_date'):
        print(f"  📅 Scheduled: {thread_item.get('scheduled_date')} slot {thread_item.get('slot')}")
    else:
        print(f"  📡 Mode: LIVE")

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

def post_for_account(account_key: str, args) -> int:
    """Post content for a single account from the live queue.

    Args:
        account_key: Account identifier ('main', 'account2', 'account3').
        args: Parsed CLI arguments.

    Returns:
        0 on success, 1 on failure.
    """
    queue_file = LIVE_QUEUE_FILE

    # Merge any Cowork-generated tweets before loading
    merge_cowork_queue(queue_file)

    print(f"\n  📂 [{account_key}] Live Queue: {queue_file}")

    if not queue_file.exists():
        print(f"  ⚠ [{account_key}] Live queue not found: {queue_file}")
        return 0

    queue = load_queue(queue_file)

    pending = [t for t in queue if t.get("status") == "pending"]
    posted = [t for t in queue if t.get("status") == "posted"]
    print(f"  📊 [{account_key}] Status: {len(posted)} posted, {len(pending)} pending")

    content_item = find_next_live_content(queue, account_key)

    if not content_item:
        print(f"\n  ℹ️  [{account_key}] No pending live content")
        return 2  # Distinct from 0 (posted) and 1 (failed)

    # Similarity duplicate check (fuzzy, 24h window)
    tweet_text = content_item.get('text', '')
    is_dup, dup_reason = check_similarity_duplicate(tweet_text, queue)
    if is_dup:
        print(f"\n  ⚠️  [{account_key}] SIMILAR DUPLICATE: {dup_reason}")
        content_item['status'] = 'skipped'
        content_item['skip_reason'] = dup_reason
        if not args.dry_run:
            save_queue(queue, queue_file)
        return 0

    # Initialize clients
    if args.dry_run:
        client_v2, api_v1 = None, None
    else:
        client_v2, api_v1 = get_clients(account_key)
        if client_v2 is None:
            print(f"  ⚠ [{account_key}] No credentials, skipping")
            return 0

    # Route to thread or single tweet posting
    if content_item.get("is_thread", False):
        print(f"  🧵 [{account_key}] LIVE THREAD ({len(content_item.get('thread_tweets', []))} tweets)")
        success = post_thread(client_v2, api_v1, content_item, dry_run=args.dry_run)
    else:
        print(f"  📝 [{account_key}] LIVE TWEET")
        success = post_tweet(client_v2, api_v1, content_item, dry_run=args.dry_run)

    if not args.dry_run:
        save_queue(queue, queue_file)
        print(f"\n  💾 [{account_key}] Live queue updated: {queue_file}")

    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Post live tweets/threads to X")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted")
    parser.add_argument("--force", action="store_true", help="Post next pending regardless of schedule")
    parser.add_argument("--account", type=str, default="main",
                        help="Account to post to (main, account2, account3, or all)")
    parser.add_argument("--verify", action="store_true",
                        help="Verify Twitter credentials for all accounts (no posting)")
    parser.add_argument("--live-queue", action="store_true",
                        help="Use live content queue (default behavior, kept for workflow compat)")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  TWITTER POSTER - Automated X Posting")
    print("═" * 60)

    # ── Verify mode: check credentials and exit ──
    if args.verify:
        print("\n  🔑 Credential Verification\n")
        try:
            from config import TWITTER_ACCOUNTS
            accounts = list(TWITTER_ACCOUNTS.keys())
        except ImportError:
            accounts = ['main']

        all_ok = True
        for account_key in accounts:
            try:
                from config import TWITTER_ACCOUNTS as accts
                prefix = accts[account_key]['env_prefix']
            except (ImportError, KeyError):
                prefix = 'X1'
            ok, msg = verify_credentials(account_key)
            emoji = "✅" if ok else "❌"
            print(f"  {emoji} {account_key} ({prefix}_*): {msg}")
            if not ok:
                all_ok = False

        print()
        return 0 if all_ok else 1

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
            ret = post_for_account(account_key, args)
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
        result = post_for_account(args.account, args)
        print("\n" + "═" * 60)
        return result


if __name__ == "__main__":
    sys.exit(main())
