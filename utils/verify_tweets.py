#!/usr/bin/env python3
"""Verify tweet generator output for known bugs."""

import json
from pathlib import Path
from collections import Counter

TRADES_DIR = Path("trades")
QUEUES = [
    ("main", "content_queue.json"),
    ("account2", "content_queue_account2.json"),
    ("account3", "content_queue_account3.json"),
]

def load_queue(filename):
    path = TRADES_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def check_duplicate_tickers(tweets, account):
    """Bug 1: Check for duplicate tickers in same tweet."""
    issues = []
    for t in tweets:
        text = t.get('text', '')
        tickers = [w for w in text.split() if w.startswith('$') and len(w) > 1]
        if len(tickers) != len(set(tickers)):
            issues.append(f"{t.get('day')} slot {t.get('slot')}: {tickers}")
    return issues

def check_template_reuse(tweets, account):
    """Bug 2: Check for same template used multiple times."""
    issues = []
    template_ids = [t.get('template_id') for t in tweets if t.get('template_id')]
    counts = Counter(template_ids)
    for tid, count in counts.items():
        if count > 1:
            issues.append(f"{tid}: used {count}x")
    return issues

def check_day_inappropriate(tweets, account):
    """Bug 3: Check for day-inappropriate phrases."""
    issues = []
    rules = {
        'Saturday': {'blocked': ['power hour', 'into the close', 'this morning']},
        'Sunday': {'blocked': ['power hour', 'into the close', 'this morning']},
        'Monday': {'blocked': ['weekend homework', 'saturday']},
        'Tuesday': {'blocked': ['weekend homework', 'friday close', 'saturday']},
        'Wednesday': {'blocked': ['weekend homework', 'friday close', 'saturday']},
        'Thursday': {'blocked': ['weekend homework', 'last friday', 'saturday']},
        'Friday': {'blocked': ['weekend homework', 'next friday', 'last week']},
    }
    for t in tweets:
        day = t.get('day', '')
        text = t.get('text', '').lower()
        blocked = rules.get(day, {}).get('blocked', [])
        for phrase in blocked:
            if phrase in text:
                issues.append(f"{day} slot {t.get('slot')}: contains '{phrase}'")
    return issues

def check_fallback_clustering(tweets, account):
    """Bug 4: Check for too many engagement fallbacks in a row."""
    issues = []
    for day in ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        day_tweets = [t for t in tweets if t.get('day') == day]
        categories = [t.get('category', '') for t in day_tweets]
        engagement_count = sum(1 for c in categories if c == 'engagement')
        if engagement_count >= 3:
            issues.append(f"{day}: {engagement_count} engagement tweets (clustering)")
    return issues

def check_persona_differentiation(all_tweets):
    """Check that accounts have different content."""
    issues = []
    if len(all_tweets) < 2:
        return issues

    main = all_tweets.get('main', [])
    acc2 = all_tweets.get('account2', [])
    acc3 = all_tweets.get('account3', [])

    identical = 0
    for m in main:
        for a in acc2 + acc3:
            if m.get('day') == a.get('day') and m.get('slot') == a.get('slot'):
                if m.get('text') == a.get('text'):
                    identical += 1

    if identical > 0:
        issues.append(f"{identical} tweets identical across accounts")

    return issues

def print_sample_tweets(tweets, account, n=3):
    """Print sample tweets to verify tone."""
    print(f"\n  Sample tweets from {account}:")
    for t in tweets[:n]:
        text = t.get('text', '')[:75]
        print(f"    {t.get('day')} #{t.get('slot')}: {text}...")

if __name__ == "__main__":
    # Run all checks
    print("=" * 60)
    print("TWEET GENERATOR VERIFICATION")
    print("=" * 60)

    all_tweets = {}
    for account, filename in QUEUES:
        tweets = load_queue(filename)
        if tweets is None:
            print(f"\n⚠️  {account}: Queue file not found ({filename})")
            continue
        all_tweets[account] = tweets

        print(f"\n📋 {account.upper()} ({len(tweets)} tweets)")
        print("-" * 40)

        # Bug 1
        issues = check_duplicate_tickers(tweets, account)
        status = "✅ PASS" if not issues else f"❌ FAIL ({len(issues)})"
        print(f"  Duplicate tickers: {status}")
        for i in issues[:3]:
            print(f"    - {i}")

        # Bug 2
        issues = check_template_reuse(tweets, account)
        status = "✅ PASS" if not issues else f"❌ FAIL ({len(issues)})"
        print(f"  Template reuse: {status}")
        for i in issues[:3]:
            print(f"    - {i}")

        # Bug 3
        issues = check_day_inappropriate(tweets, account)
        status = "✅ PASS" if not issues else f"❌ FAIL ({len(issues)})"
        print(f"  Day-appropriate content: {status}")
        for i in issues[:3]:
            print(f"    - {i}")

        # Bug 4
        issues = check_fallback_clustering(tweets, account)
        status = "✅ PASS" if not issues else f"⚠️  WARN ({len(issues)})"
        print(f"  Fallback variety: {status}")
        for i in issues[:3]:
            print(f"    - {i}")

    # Cross-account check
    print(f"\n📋 CROSS-ACCOUNT DIFFERENTIATION")
    print("-" * 40)
    issues = check_persona_differentiation(all_tweets)
    status = "✅ PASS" if not issues else f"❌ FAIL ({len(issues)})"
    print(f"  Unique content per account: {status}")
    for i in issues:
        print(f"    - {i}")

    # Show samples for tone verification
    if 'main' in all_tweets:
        print_sample_tweets(all_tweets['main'], "main (The System)")
    if 'account2' in all_tweets:
        print_sample_tweets(all_tweets['account2'], "account2 (The Mentor)")
    if 'account3' in all_tweets:
        print_sample_tweets(all_tweets['account3'], "account3 (The Trader)")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
