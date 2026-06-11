#!/usr/bin/env python3
"""Fetch engagement metrics from Twitter API for the 3-account system.

Reads tweet metrics via Tweepy v2 API, matches against queue entries
for category classification, writes to state/engagement.json.

Usage:
    python -m scripts.fetch_engagement              # Fetch all accounts
    python -m scripts.fetch_engagement --dry-run    # Preview without writing
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Account config (replicated from poster.py to avoid sys.exit import trap)
ACCOUNT_CONFIG = {
    "main": {"env_prefix": "X1", "variant": "variant_1"},
    "account2": {"env_prefix": "X2", "variant": "variant_2"},
    "account3": {"env_prefix": "X3", "variant": "variant_3"},
}

QUEUE_FILES = [
    "twitter/output/live_content_queue.json",
    "twitter/output/content_queue.json",
    "twitter/output/content_queue_account2.json",
    "twitter/output/content_queue_account3.json",
    "twitter/output/daily_content_queue.json",
    "twitter/output/daily_content_queue_account2.json",
    "twitter/output/daily_content_queue_account3.json",
]

ENGAGEMENT_FILE = BASE_DIR / "state" / "engagement.json"
LOOKBACK_DAYS = 7


def get_v2_client(account_key: str):
    """Create Tweepy v2 client for an account. Returns None if credentials missing."""
    try:
        import tweepy
    except ImportError:
        logger.error("tweepy not installed — run: pip install tweepy")
        return None

    cfg = ACCOUNT_CONFIG.get(account_key)
    if not cfg:
        return None
    prefix = cfg["env_prefix"]

    api_key = os.environ.get(f"{prefix}_API_KEY")
    api_secret = os.environ.get(f"{prefix}_API_SECRET")
    access_token = os.environ.get(f"{prefix}_ACCESS_TOKEN")
    access_secret = os.environ.get(f"{prefix}_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        logger.warning("Missing credentials for %s (%s_*)", account_key, prefix)
        return None

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


def build_tweet_category_lookup() -> Dict[str, str]:
    """Build {tweet_id: category} lookup from all queue files.

    Only includes entries with status="posted" and a valid tweet_id,
    which is set by poster.py after successful posting.
    """
    lookup = {}
    found_files = 0
    for qf in QUEUE_FILES:
        path = BASE_DIR / qf
        if not path.exists():
            continue
        found_files += 1
        try:
            data = json.loads(path.read_text())
            for item in data:
                tid = item.get("tweet_id")
                cat = item.get("category")
                if tid and cat and item.get("status") == "posted":
                    lookup[str(tid)] = cat
        except Exception as e:
            logger.debug("Queue parse error %s: %s", qf, e)
    logger.info(
        "Built category lookup: %d posted tweets from %d queue files",
        len(lookup), found_files,
    )
    return lookup


def fetch_account_metrics(
    client, account_key: str, category_lookup: Dict[str, str]
) -> Optional[Dict]:
    """Fetch 7-day tweet metrics for one account.

    Uses Tweepy v2 API:
    - get_me() for user ID and handle
    - get_users_tweets() for recent tweets with public_metrics

    Matches tweets against category_lookup (built from queue files)
    to compute per-category engagement averages.
    """
    import tweepy  # guaranteed available if client was created

    # Get user ID
    try:
        me = client.get_me()
        if not me or not me.data:
            logger.warning("%s: get_me() returned empty response", account_key)
            return None
        user_id = me.data.id
        handle = me.data.username
        logger.info("%s: authenticated as @%s (id: %s)", account_key, handle, user_id)
    except tweepy.TweepyException as e:
        logger.error("%s: auth failed: %s", account_key, e)
        return None

    # Fetch recent tweets (last 7 days)
    cutoff = datetime.now(ZoneInfo("UTC")) - timedelta(days=LOOKBACK_DAYS)
    try:
        tweets = client.get_users_tweets(
            id=user_id,
            max_results=100,
            start_time=cutoff.isoformat(),
            tweet_fields=["public_metrics", "created_at"],
        )
    except tweepy.TweepyException as e:
        logger.error("%s: get_users_tweets failed: %s", account_key, e)
        return None

    if not tweets or not tweets.data:
        logger.info("%s: no tweets in last %d days", account_key, LOOKBACK_DAYS)
        return {
            "handle": f"@{handle}",
            "last_7d_avg_likes": 0,
            "last_7d_avg_retweets": 0,
            "last_7d_avg_replies": 0,
            "by_category": {},
        }

    # Process metrics
    all_likes: List[int] = []
    all_rts: List[int] = []
    all_replies: List[int] = []
    by_cat: Dict[str, List[Dict]] = {}

    for tw in tweets.data:
        m = tw.public_metrics or {}
        likes = m.get("like_count", 0)
        rts = m.get("retweet_count", 0)
        replies = m.get("reply_count", 0)
        all_likes.append(likes)
        all_rts.append(rts)
        all_replies.append(replies)

        # Match to category via queue lookup
        tid = str(tw.id)
        cat = category_lookup.get(tid)
        if cat:
            by_cat.setdefault(cat, []).append({
                "likes": likes, "retweets": rts, "replies": replies,
            })

    n = len(tweets.data)
    matched = sum(len(v) for v in by_cat.values())
    logger.info(
        "%s: %d tweets fetched, %d matched to categories (%d unmatched)",
        account_key, n, matched, n - matched,
    )

    # Aggregate per-category averages
    cat_summary = {}
    for cat, metrics_list in by_cat.items():
        c = len(metrics_list)
        cat_summary[cat] = {
            "count": c,
            "avg_likes": round(sum(m["likes"] for m in metrics_list) / c, 1),
            "avg_retweets": round(sum(m["retweets"] for m in metrics_list) / c, 1),
            "avg_replies": round(sum(m["replies"] for m in metrics_list) / c, 1),
        }

    return {
        "handle": f"@{handle}",
        "last_7d_avg_likes": round(sum(all_likes) / n, 1) if n else 0,
        "last_7d_avg_retweets": round(sum(all_rts) / n, 1) if n else 0,
        "last_7d_avg_replies": round(sum(all_replies) / n, 1) if n else 0,
        "by_category": cat_summary,
    }


def _empty_account() -> Dict:
    """Return empty account metrics (used when credentials missing or fetch fails)."""
    return {
        "handle": "",
        "last_7d_avg_likes": 0,
        "last_7d_avg_retweets": 0,
        "last_7d_avg_replies": 0,
        "by_category": {},
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Twitter engagement metrics")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    category_lookup = build_tweet_category_lookup()

    result = {
        "last_updated": datetime.now(ZoneInfo("UTC")).isoformat(),
        "fetch_source": "twitter_api",
        "accounts": {},
    }

    for account_key, cfg in ACCOUNT_CONFIG.items():
        variant = cfg["variant"]
        client = get_v2_client(account_key)
        if client is None:
            result["accounts"][variant] = _empty_account()
            continue

        metrics = fetch_account_metrics(client, account_key, category_lookup)
        result["accounts"][variant] = metrics if metrics else _empty_account()

    if args.dry_run:
        print(json.dumps(result, indent=2))
        logger.info("DRY RUN — not writing to %s", ENGAGEMENT_FILE)
    else:
        ENGAGEMENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENGAGEMENT_FILE.write_text(json.dumps(result, indent=2) + "\n")
        logger.info("Written to %s", ENGAGEMENT_FILE)

    return 0


if __name__ == "__main__":
    sys.exit(main())
