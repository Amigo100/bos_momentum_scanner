#!/usr/bin/env python3
"""
Verification script for reaction_generator.py output.
Checks structure, scheduling, persona differentiation, content rules,
URL presence, duplicate detection, ticker validity, and cross-persona contamination.
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

QUEUE_FILES = {
    'main': 'trades/tweets/content_queue.json',
    'account2': 'trades/tweets/content_queue_account2.json',
    'account3': 'trades/tweets/content_queue_account3.json',
}

EXPECTED_DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
EXPECTED_SLOTS = [1, 2, 3, 4, 5]
EXPECTED_TIMES = ['08:00', '10:00', '12:30', '15:30', '18:00']
PERSONAS = {'main': 'Alex', 'account2': 'Rozalia', 'account3': 'James'}

BANNED_TERMS = [
    '20% trailing stop', 'HMA pivot', 'Banker indicator', 'Banker >= 55',
    'Beta >= 1.5', 'Weekly BoS', 'Tier 1', 'Tier 2', 'Tier 3',
    'Gatekeeper', 'Theme scoring', 'conviction 5', 'conviction 4',
    'conviction score', 'UK ISA', 'ISA account', 'GMT', 'BST',
    'UK Time', 'RSI', 'MACD', 'KDJ',
]

WEEKEND_BANNED = ['power hour', 'into the close', 'market open', 'pre-market']

# Cross-persona signature phrases that should NOT appear in other accounts
PERSONA_SIGNATURES = {
    'main': ["the scanner doesn't lie", "data drives decisions"],
    'account2': ["here's the thing", "when i was starting out", "i wish someone told me"],
    'account3': ["here we go", "that's the move", "eyes on"],
}

# Mock data tickers that are valid
VALID_TICKERS = {'AMPX', 'LUMN', 'NVDA', 'PLTR', 'OKLO', 'RCAT', 'SPY', 'QQQ'}

passed = 0
failed = 0
warnings = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} -- {detail}")
        failed += 1


def warn(name, detail=""):
    global warnings
    print(f"  WARN: {name} -- {detail}")
    warnings += 1


# 1. File existence
print("\n=== 1. FILE EXISTENCE ===")
queues = {}
for account, path in QUEUE_FILES.items():
    exists = Path(path).exists()
    check(f"{account} queue exists", exists, f"Missing {path}")
    if exists:
        with open(path) as f:
            queues[account] = json.load(f)

if not queues:
    print("No queue files found. Exiting.")
    sys.exit(1)

# 2. Tweet counts
print("\n=== 2. TWEET COUNTS ===")
for account, tweets in queues.items():
    check(f"{account} has 35 tweets", len(tweets) == 35, f"Got {len(tweets)}")

# 3. Schedule structure
print("\n=== 3. SCHEDULE STRUCTURE ===")
for account, tweets in queues.items():
    days_seen = {}
    for t in tweets:
        days_seen.setdefault(t.get('day'), []).append(t.get('slot'))

    for day in EXPECTED_DAYS:
        slots = sorted(days_seen.get(day, []))
        check(f"{account} {day} has slots 1-5", slots == EXPECTED_SLOTS,
              f"Got slots {slots}")

# 4. Persona assignment
print("\n=== 4. PERSONA ASSIGNMENT ===")
for account, tweets in queues.items():
    expected_persona = PERSONAS[account]
    all_match = all(t.get('persona') == expected_persona for t in tweets)
    check(f"{account} all tweets persona={expected_persona}", all_match)
    all_account = all(t.get('account') == account for t in tweets)
    check(f"{account} all tweets account={account}", all_account)

# 5. Banned terms
print("\n=== 5. BANNED TERMS ===")
for account, tweets in queues.items():
    violations = []
    for t in tweets:
        text = t.get('text', '').lower()
        for term in BANNED_TERMS:
            if re.search(r'\b' + re.escape(term.lower()) + r'\b', text):
                violations.append(f"{t['day']} slot {t['slot']}: '{term}'")
    check(f"{account} no banned terms", len(violations) == 0,
          f"{len(violations)} violations: {violations[:3]}")

# 6. Weekend content rules
print("\n=== 6. WEEKEND CONTENT RULES ===")
for account, tweets in queues.items():
    violations = []
    for t in tweets:
        if t.get('day') in ('Saturday', 'Sunday'):
            text = t.get('text', '').lower()
            for phrase in WEEKEND_BANNED:
                if phrase in text:
                    violations.append(f"{t['day']} slot {t['slot']}: '{phrase}'")
    check(f"{account} no weekend market-hours language", len(violations) == 0,
          f"{violations[:3]}")

# 7. Character limits
print("\n=== 7. CHARACTER LIMITS ===")
for account, tweets in queues.items():
    over_limit = [t for t in tweets if len(t.get('text', '')) > 280]
    check(f"{account} all tweets <= 280 chars", len(over_limit) == 0,
          f"{len(over_limit)} over: " + ", ".join(
              f"{t['day']} slot {t['slot']} ({len(t['text'])} chars)" for t in over_limit[:3]))

# 8. No empty tweets
print("\n=== 8. NO EMPTY TWEETS ===")
for account, tweets in queues.items():
    empty = [t for t in tweets if not t.get('text', '').strip()]
    check(f"{account} no empty tweets", len(empty) == 0, f"{len(empty)} empty")

# 9. Newsletter URL presence (2-3 per day)
print("\n=== 9. NEWSLETTER URL PER DAY ===")
URL_PATTERN = 'sterlingsignals.substack.com'
for account, tweets in queues.items():
    day_url_counts = {}
    for t in tweets:
        day = t.get('day')
        has_url = URL_PATTERN in t.get('text', '')
        day_url_counts.setdefault(day, 0)
        if has_url:
            day_url_counts[day] += 1

    low_days = [d for d in EXPECTED_DAYS if day_url_counts.get(d, 0) < 1]
    high_days = [d for d in EXPECTED_DAYS if day_url_counts.get(d, 0) > 3]
    total_urls = sum(day_url_counts.values())

    check(f"{account} has URLs in tweets (total: {total_urls})", total_urls >= 7,
          f"Only {total_urls} tweets have newsletter URL across all days")
    if low_days:
        warn(f"{account} days with 0 URLs: {low_days}")
    if high_days:
        warn(f"{account} days with >3 URLs: {high_days}")

# 10. Cross-persona phrase contamination
print("\n=== 10. CROSS-PERSONA CONTAMINATION ===")
for account, tweets in queues.items():
    violations = []
    for other_account, phrases in PERSONA_SIGNATURES.items():
        if other_account == account:
            continue
        for t in tweets:
            text = t.get('text', '').lower()
            for phrase in phrases:
                if phrase in text:
                    violations.append(
                        f"{t['day']} slot {t['slot']}: has {other_account}'s phrase '{phrase}'")
    check(f"{account} no cross-persona contamination", len(violations) == 0,
          f"{len(violations)} violations: {violations[:3]}")

# 11. Duplicate / very similar tweets (within same account)
print("\n=== 11. DUPLICATE DETECTION ===")
for account, tweets in queues.items():
    texts = [t.get('text', '') for t in tweets]
    similar_pairs = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            ratio = SequenceMatcher(None, texts[i], texts[j]).ratio()
            if ratio > 0.85:
                similar_pairs.append(
                    f"slot {tweets[i]['day']}/{tweets[i]['slot']} vs "
                    f"{tweets[j]['day']}/{tweets[j]['slot']} ({ratio:.0%})")
    check(f"{account} no duplicate/very similar tweets", len(similar_pairs) == 0,
          f"{len(similar_pairs)} similar pairs: {similar_pairs[:3]}")

# 12. Valid tickers
print("\n=== 12. VALID TICKERS ===")
for account, tweets in queues.items():
    unknown_tickers = set()
    for t in tweets:
        text = t.get('text', '')
        mentioned = re.findall(r'\$([A-Z]{2,5})', text)
        for ticker in mentioned:
            if ticker not in VALID_TICKERS:
                unknown_tickers.add(ticker)
    if unknown_tickers:
        warn(f"{account} mentions tickers not in mock data: {unknown_tickers}",
             "May be acceptable if Claude added market color")
    else:
        check(f"{account} all tickers from mock data", True)

# 13. Cross-account differentiation
print("\n=== 13. CROSS-ACCOUNT DIFFERENTIATION ===")
if len(queues) == 3:
    identical_count = 0
    for i in range(35):
        texts = set()
        for account in queues:
            if i < len(queues[account]):
                texts.add(queues[account][i].get('text'))
        if len(texts) == 1:
            identical_count += 1

    if identical_count == 35:
        warn("All tweets identical across accounts (expected with fallback/no API key)")
    else:
        pct_unique = ((35 - identical_count) / 35) * 100
        check(f"Cross-account differentiation ({pct_unique:.0f}% unique)",
              identical_count < 5, f"{identical_count}/35 identical")

# 14. Required fields
print("\n=== 14. REQUIRED FIELDS ===")
REQUIRED_FIELDS = ['id', 'day', 'slot', 'time', 'text', 'category', 'account', 'persona',
                   'scheduled_date', 'status', 'generation_method', 'char_count']
for account, tweets in queues.items():
    missing = []
    for t in tweets:
        for field in REQUIRED_FIELDS:
            if field not in t:
                missing.append(f"{t.get('day', '?')} slot {t.get('slot', '?')}: missing '{field}'")
    check(f"{account} all required fields present", len(missing) == 0,
          f"{len(missing)} missing: {missing[:3]}")

# 15. Generation method check
print("\n=== 15. GENERATION METHOD ===")
for account, tweets in queues.items():
    methods = {}
    for t in tweets:
        m = t.get('generation_method', 'unknown')
        methods[m] = methods.get(m, 0) + 1
    reaction_count = methods.get('reaction', 0)
    fallback_count = methods.get('fallback', 0)
    check(f"{account} mostly reaction-generated ({reaction_count}/35 reaction, {fallback_count} fallback)",
          reaction_count >= 30, f"Only {reaction_count} reaction tweets")

# Summary
print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed, {warnings} warnings")
if failed == 0:
    print("All checks passed!")
else:
    print("Some checks failed - review output above.")
    sys.exit(1)
