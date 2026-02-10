# Batch Tweet System v1 — Archive

Archived: 2026-02-10
Reason: Replaced by live-context tweet system (Grok + Sonnet hybrid)

## What this was
- Friday batch generation of 28 tweets/week using Claude API
- 3-account system with content_queue.json per account
- twitter_poster.py reading from queues on schedule (5 slots/day)

## How to restore
1. Copy all files back to their original locations
2. Restore workflow files to .github/workflows/
3. Re-run: python -m content.tweet_generator --signals trades/signals.json --portfolio trades/portfolio.csv
4. Verify: python -m distribution.twitter_poster --dry-run

## Files
- content/ — tweet_generator.py, reaction_generator.py, models.py
- distribution/ — twitter_poster.py (pre-modification snapshot)
- config_snapshots/ — settings.py, banned_terms.py at time of archive
- workflows/ — daily_post.yml, friday_scan.yml at time of archive
- queue_snapshots/ — content queue JSON files at time of archive
