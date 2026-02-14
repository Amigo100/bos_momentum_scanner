#!/usr/bin/env python3
"""
POST TWEET CLI — Lightweight wrapper for posting to X from Claude Code
======================================================================

Posts a single tweet to X using the existing twitter_poster.py infrastructure.
Designed to be called by the /post Claude Code slash command.

Usage:
    python scripts/post_tweet.py --text "Tweet text here"
    python scripts/post_tweet.py --text "Tweet text here" --dry-run
    python scripts/post_tweet.py --text "Tweet text here" --account account2
    python scripts/post_tweet.py --text "Tweet text here" --image trades/charts/NVDA.png
"""

import argparse
import sys
import os

# Add project root to path so we can import from distribution/, config/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from distribution.twitter_poster import get_clients, validate_before_posting, post_tweet, upload_media


def main():
    parser = argparse.ArgumentParser(description="Post a tweet to X via Sterling Signals infrastructure")
    parser.add_argument("--text", required=True, help="Tweet text to post")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't post")
    parser.add_argument("--account", default="main", help="Account key: main, account2, account3")
    parser.add_argument("--image", default=None, help="Path to image to attach")
    args = parser.parse_args()

    # Build tweet dict (matching the format twitter_poster expects)
    tweet = {
        "text": args.text,
        "category": "reactive",
        "id": "cli-reactive",
        "generation_method": "claude-code-post-command",
    }
    if args.image:
        tweet["chart_path"] = args.image

    # Step 1: Validate (last-line-of-defense)
    can_post, reason = validate_before_posting(tweet)
    if not can_post:
        print(f"\n{reason}")
        sys.exit(1)

    # Step 2: Dry run — just confirm validation passed
    if args.dry_run:
        char_count = len(args.text)
        print(f"\nValidation PASSED ({char_count} chars)")
        print(f"DRY RUN — would post:\n")
        for line in args.text.split('\n'):
            print(f"  {line}")
        sys.exit(0)

    # Step 3: Get API clients
    client_v2, api_v1 = get_clients(args.account)
    if not client_v2:
        print(f"\nMissing X API credentials for '{args.account}'")
        print(f"Ensure these env vars are set:")
        from config import TWITTER_ACCOUNTS
        account = TWITTER_ACCOUNTS.get(args.account, TWITTER_ACCOUNTS['main'])
        prefix = account['env_prefix']
        print(f"  {prefix}_API_KEY")
        print(f"  {prefix}_API_SECRET")
        print(f"  {prefix}_ACCESS_TOKEN")
        print(f"  {prefix}_ACCESS_SECRET")
        sys.exit(1)

    # Step 4: Post
    success = post_tweet(client_v2, api_v1, tweet, dry_run=False)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
