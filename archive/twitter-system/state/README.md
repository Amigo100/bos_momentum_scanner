# State Directory

Persistent state files for Sterling Signals automation. These files are read and written by various pipeline scripts.

## Files

| File | Written By | Read By | Frequency |
|------|-----------|---------|-----------|
| `engagement.json` | engagement-fetch.yml | live_tweet_generator.py, daily_context_builder.py | Daily 9 PM ET |
| `content_tracker.json` | daily_content_pipeline.py | Dashboard Content Calendar | Daily |
| `cost_summary.json` | live_tweet_generator.py | Dashboard System Health | Per tweet slot |
| `system_log.json` | health-check.yml | Dashboard System Health | Daily 10 PM ET |
| `notes.json` | notes_poster.py | Dashboard Activity Feed | 3x daily |

## Important

- All JSON files use UTF-8 encoding
- Scripts should handle missing files gracefully (create with defaults on first run)
- Git-committed (not gitignored) so dashboard can read via GitHub API
