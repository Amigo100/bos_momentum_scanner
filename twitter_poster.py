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
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

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
    """Load content queue from JSON file."""
    if not queue_file.exists():
        print(f"ERROR: Queue file not found: {queue_file}")
        sys.exit(1)
    
    with open(queue_file, 'r') as f:
        return json.load(f)


def save_queue(queue: list[Dict], queue_file: Path) -> None:
    """Save updated queue back to JSON file."""
    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)


def get_current_slot() -> int:
    """Determine current time slot based on Eastern Time (ET)."""
    # Note: In production via GitHub Actions, UTC time is converted in workflow
    # Locally, this assumes system is in ET or adjust accordingly
    now = datetime.now()
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
    

def find_next_tweet(queue: list[Dict], force: bool = False, target_slot: Optional[int] = None) -> Optional[Dict]:
    """Find the next tweet to post based on schedule and slot.

    Args:
        queue: List of tweet dictionaries
        force: If True, post first pending regardless of schedule
        target_slot: If specified, only consider tweets for this slot (1, 2, or 3)
    """

    today = datetime.now().strftime("%Y-%m-%d")
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
        
        return True
        
    except tweepy.TweepyException as e:
        print(f"\n  ✗ Failed to post: {e}")
        tweet['status'] = 'failed'
        tweet['error'] = str(e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Post scheduled tweets to X")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted")
    parser.add_argument("--force", action="store_true", help="Post next pending regardless of schedule")
    parser.add_argument("--queue", type=str, help="Path to content queue JSON")
    parser.add_argument("--slot", type=str, default="all",
                        help="Which slot to post (1, 2, 3, or 'all')")
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
    
    print(f"  📊 Status: {len(posted)} posted, {len(pending)} pending")
    
    # Find next tweet (filter by slot if specified)
    target_slot = None if args.slot == "all" else int(args.slot) if args.slot.isdigit() else None
    tweet = find_next_tweet(queue, force=args.force, target_slot=target_slot)
    
    if not tweet:
        print(f"\n  ℹ️  No tweets due right now")
        print(f"     Current slot: {get_current_slot()} ({SLOT_TIMES.get(get_current_slot(), 'outside hours')})")
        print(f"     Today: {datetime.now().strftime('%Y-%m-%d')}")
        return 0
    
    # Initialize clients (skip for dry run if no credentials)
    if args.dry_run:
        client_v2, api_v1 = None, None
    else:
        client_v2, api_v1 = get_clients()
    
    # Post tweet
    success = post_tweet(client_v2, api_v1, tweet, dry_run=args.dry_run)
    
    # Save updated queue
    if not args.dry_run:
        save_queue(queue, queue_file)
        print(f"\n  💾 Queue updated: {queue_file}")
    
    print("\n" + "═" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
