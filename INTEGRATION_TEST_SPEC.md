# Sterling Signals — Comprehensive Integration Test Spec

## Purpose

All 5 sprints are implemented. Before going live, we need to verify every workflow, API call, email notification, content generation pipeline, and external posting mechanism actually works end-to-end — not just in dry-run/unit test mode. This document is the single source of truth for that validation.

---

## REQUIRED ENVIRONMENT VARIABLES

Before ANY testing, verify every secret is set. Missing even one will cause silent failures that are hard to diagnose later.

### GitHub Secrets (Repository Settings → Secrets and Variables → Actions)

| Secret | Used By | How to Get It | Expires? |
|--------|---------|---------------|----------|
| `ANTHROPIC_API_KEY` | Tweet generator, Notes generator, Analysis package | Anthropic Console → API Keys | No (unless revoked) |
| `SENDGRID_API_KEY` | Daily email, Cookie expiry alerts | SendGrid → Settings → API Keys | No (unless revoked) |
| `STERLING_EMAIL_TO` | All email notifications | Your email address | No |
| `SUBSTACK_SESSION_COOKIE` | Notes poster | Browser DevTools → Application → Cookies → substack.com → `substack.sid` value | **Yes — 30-90 days** |
| `TWITTER_BEARER_TOKEN` | Engagement fetch script | Twitter Developer Portal → Project → Bearer Token | No (unless regenerated) |

### Twitter OAuth (Per-Account — check how poster.py loads these)

Run this to find what env vars the tweet poster expects:

```bash
grep -n "os.environ\|os.getenv\|TWITTER\|CONSUMER\|ACCESS\|BEARER\|API_KEY\|API_SECRET\|OAUTH" twitter/poster.py | head -30
```

Common pattern is per-account OAuth 1.0a credentials:

| Secret Pattern | Account | How to Get It |
|---------------|---------|---------------|
| `TWITTER_API_KEY_{N}` | Account 1/2/3 | Twitter Developer Portal → App → Keys |
| `TWITTER_API_SECRET_{N}` | Account 1/2/3 | Twitter Developer Portal → App → Keys |
| `TWITTER_ACCESS_TOKEN_{N}` | Account 1/2/3 | Twitter Developer Portal → App → Keys |
| `TWITTER_ACCESS_SECRET_{N}` | Account 1/2/3 | Twitter Developer Portal → App → Keys |

**Action Item:** Run the grep above, document the exact variable names, and verify ALL are set in GitHub Secrets.

### Grok / Primary Context Source

```bash
grep -n "GROK\|XAI\|grok\|live_context" twitter/live_tweet_generator.py | head -20
```

**Action Item:** Identify if there's a Grok API key or other context source credential needed. Document it.

---

## TEST PHASE 1: Component Health Checks (Local / Claude Code)

Run these first. They verify imports, configs, and basic functionality without making any external API calls.

### Test 1.1 — All Imports Pass

```
Run each of these import checks. Every single one must succeed with no errors:

python3 -c "import twitter.live_tweet_generator; print('✓ Tweet generator')"
python3 -c "from twitter.live_tweet_generator import load_category_examples, load_voice_guides, fetch_yfinance_context, load_engagement_data; print('✓ Sprint 4 functions')"
python3 -c "from substack.daily_notes_generator import main; print('✓ Notes generator')"
python3 -c "from substack.notes_poster import post_note, check_cookie_validity, NoteHTMLParser; print('✓ Notes poster')"
python3 -c "from scripts.content_tracker import main; print('✓ Content tracker')"
python3 -c "from scripts.fetch_engagement import main; print('✓ Engagement fetch')"
python3 -c "from scripts.build_analysis_package import main; print('✓ Analysis package')"
python3 -c "from scripts.build_daily_email import main; print('✓ Daily email builder')"

If ANY fail, report the exact error. These are blockers.
```

### Test 1.2 — Config Files Present and Valid

```
Verify all Sprint 1 config files exist and parse correctly:

echo "=== YAML Category Configs ==="
ls -la config/tweet_prompts/*.yaml 2>/dev/null | wc -l
# Expected: 11+ files (one per tweet category)
python3 -c "
import yaml, glob
files = glob.glob('config/tweet_prompts/*.yaml')
print(f'Found {len(files)} YAML configs')
for f in files:
    data = yaml.safe_load(open(f))
    cat = data.get('category', '???')
    examples = len(data.get('examples', []))
    banned = len(data.get('banned_terms', []))
    print(f'  {cat}: {examples} examples, {banned} banned terms')
"

echo "=== Voice Guides ==="
python3 -c "
import yaml
data = yaml.safe_load(open('config/persona_voice_guides.yaml'))
personas = data.get('personas', {})
for k, v in personas.items():
    print(f'  {k}: {v.get(\"name\", \"?\")} — {len(v.get(\"voice_guide\", \"\"))} chars')
"

echo "=== State Files ==="
for f in state/notes.json state/engagement.json state/content_tracker.json; do
    python3 -c "import json; json.load(open('$f')); print('✓ $f valid')" 2>/dev/null || echo "✗ $f missing or invalid"
done

echo "=== Workflow Files ==="
for f in .github/workflows/daily_content.yml .github/workflows/substack-notes.yml .github/workflows/engagement-fetch.yml; do
    python3 -c "import yaml; yaml.safe_load(open('$f')); print('✓ $f valid YAML')" 2>/dev/null || echo "✗ $f missing or invalid"
done

Report any missing or invalid files.
```

### Test 1.3 — Sprint 4 Tweet Generator Health

```
Test that all Sprint 4 additions work without crashing:

echo "=== YAML Category Loading ==="
python3 -c "
from twitter.live_tweet_generator import load_category_examples
configs = load_category_examples()
print(f'YAML loaded: {len(configs) if configs else 0} categories')
"

echo "=== Voice Guides ==="
python3 -c "
from twitter.live_tweet_generator import load_voice_guides
guides = load_voice_guides()
print(f'Voice guides: {len(guides) if guides else 0} personas')
"

echo "=== yfinance ==="
python3 -c "
from twitter.live_tweet_generator import fetch_yfinance_context
result = fetch_yfinance_context('AAPL')
if result:
    print(f'yfinance: working — got {len(result)} chars for AAPL')
else:
    print('yfinance: FAILED — returned None for AAPL')
"

echo "=== Engagement Data ==="
python3 -c "
from twitter.live_tweet_generator import load_engagement_data
data = load_engagement_data()
print(f'Engagement: {\"real data\" if data and data.get(\"last_updated\") else \"scaffold only (expected before first fetch)\"}')
"

echo "=== Dry-Run ==="
python3 -m twitter.live_tweet_generator --dry-run 2>&1 | tail -30
# Check: no crashes, categories selected, validation steps run
# Look for: "Loaded N categories from YAML", voice guide messages, step 8.6 dedup
```

### Test 1.4 — Notes Generator Pre-Flight

```
Test notes generation infrastructure (not the API call):

echo "=== Notes Context ==="
python3 -c "
import json
ctx = json.load(open('substack/output/current/daily_notes_context.json'))
print(f'Context keys: {list(ctx.keys())}')
ns = ctx.get('note_schedule', [])
print(f'Note schedule: {ns}')
print(f'Day: {ctx.get(\"day\", \"?\")}')
print(f'Date: {ctx.get(\"date\", \"?\")}')
"

echo "=== Pre-Generated Notes ==="
ls -la substack/output/current/daily_notes/note_slot*.html 2>/dev/null || echo "No pre-generated notes found"

echo "=== Notes Generator Dry Run ==="
# This tests the poster's ability to find and convert notes WITHOUT posting
python3 -m substack.notes_poster --slot 1 --dry-run 2>&1
# Expected: finds pre-generated note, converts HTML to ProseMirror, shows what it would post
```

### Test 1.5 — HTML→ProseMirror Conversion

```
This is a critical piece — if this fails, Substack posting will 422.

python3 -c "
from substack.notes_poster import NoteHTMLParser

# Test 1: Plain text
html = '<div class=\"note-content\"><p>Hello world.</p></div>'
parser = NoteHTMLParser()
parser.feed(html)
result = parser.get_prosemirror()
print(f'Plain text: {\"PASS\" if result else \"FAIL\"}')
print(f'  Result: {result}')

# Test 2: Bold + italic
html = '<div class=\"note-content\"><p><strong>Bold</strong> and <em>italic</em></p></div>'
parser = NoteHTMLParser()
parser.feed(html)
result = parser.get_prosemirror()
print(f'Formatting: {\"PASS\" if result else \"FAIL\"}')

# Test 3: Links
html = '<div class=\"note-content\"><p>Check <a href=\"https://example.com\">this link</a></p></div>'
parser = NoteHTMLParser()
parser.feed(html)
result = parser.get_prosemirror()
print(f'Links: {\"PASS\" if result else \"FAIL\"}')

# Test 4: Multi-paragraph
html = '<div class=\"note-content\"><p>Para 1</p><p>Para 2</p><p>Para 3</p></div>'
parser = NoteHTMLParser()
parser.feed(html)
result = parser.get_prosemirror()
print(f'Multi-paragraph: {\"PASS\" if result else \"FAIL\"}')
print(f'  Paragraphs: {len(result.get(\"content\", []))} (expected 3)')

# Test 5: Emoji passthrough
html = '<div class=\"note-content\"><p>🚀 Market is up 📈</p></div>'
parser = NoteHTMLParser()
parser.feed(html)
result = parser.get_prosemirror()
print(f'Emoji: {\"PASS\" if result else \"FAIL\"}')
"
# ALL 5 must pass. Failures here mean Substack posting will break.
```

---

## TEST PHASE 2: Live API Calls (One-Shot Tests)

These tests make REAL API calls. They cost money (small amounts) and post to real services. Run them carefully and in order.

### Test 2.1 — Anthropic API (Claude Sonnet)

```
Test that note generation via the Anthropic API works.
Requires: ANTHROPIC_API_KEY in environment.

# First, verify the API key works at all
python3 -c "
import anthropic
client = anthropic.Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-5-20250929',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Say hello in exactly 5 words.'}]
)
print(f'API response: {resp.content[0].text}')
print(f'Model: {resp.model}')
print(f'Input tokens: {resp.usage.input_tokens}')
print(f'Output tokens: {resp.usage.output_tokens}')
print('✓ Anthropic API working')
"

# If this fails:
# - "AuthenticationError" → ANTHROPIC_API_KEY is wrong or missing
# - "NotFoundError" → Model name may need updating. Try: claude-sonnet-4-5-20250929
# - "RateLimitError" → Wait and retry
# - "Connection" error → Network issue
```

### Test 2.2 — Full Note Generation (Single Slot)

```
Generate one real note via the full pipeline.
Requires: ANTHROPIC_API_KEY

# Generate slot 1 note
python3 -m substack.notes_generator --slot 1 2>&1

# OR if the existing daily_notes_generator.py handles generation:
# Check which script actually generates notes:
ls -la substack/daily_notes_generator.py substack/notes_generator.py 2>/dev/null

# Verify output
echo "=== Generated Note ==="
cat substack/output/current/daily_notes/note_slot1.html

# Validate the note
echo "=== Validation ==="
python3 -c "
html = open('substack/output/current/daily_notes/note_slot1.html').read()
print(f'Length: {len(html)} chars')
print(f'Has div wrapper: {\"<div\" in html.lower()}')
print(f'Has disclaimer: {\"not financial advice\" in html.lower() or \"informational\" in html.lower()}')
# Count words (strip HTML)
import re
text = re.sub('<[^>]+>', '', html)
words = len(text.split())
print(f'Word count: {words} (target: 100-300)')
"
```

### Test 2.3 — SendGrid Email Delivery

```
Test that the SendGrid email pipeline actually delivers.
Requires: SENDGRID_API_KEY, STERLING_EMAIL_TO

# Method 1: Test via the daily email sender directly
python3 -c "
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
message = Mail(
    from_email='sterling@yourdomain.com',  # UPDATE to your verified sender
    to_emails=os.environ.get('STERLING_EMAIL_TO'),
    subject='Sterling Signals — Integration Test',
    html_content='<p>If you receive this, SendGrid is working. ✓</p>'
)
response = sg.send(message)
print(f'Status: {response.status_code}')
print(f'✓ Email sent' if response.status_code in [200, 201, 202] else f'✗ Failed: {response.status_code}')
"

# If this fails:
# - 401 → SENDGRID_API_KEY is wrong
# - 403 → Sender email not verified in SendGrid
# - Check STERLING_EMAIL_TO is a valid email address

# IMPORTANT: Check your inbox/spam for the test email!
```

### Test 2.4 — Analysis Package Email (Sprint 2)

```
Test the full analysis package build + email.
Requires: ANTHROPIC_API_KEY, SENDGRID_API_KEY, STERLING_EMAIL_TO

python3 -m scripts.build_analysis_package 2>&1 | tail -20

# Check: Did it build the package? Did it send the email?
# Verify by checking your inbox for the analysis email.
# If it fails, check:
# 1. Does the context data exist? ls -la substack/output/current/
# 2. Does the email sender import correctly?
# 3. What's the exact error message?
```

### Test 2.5 — Substack Cookie Validity

```
Test that the Substack session cookie is valid and hasn't expired.
Requires: SUBSTACK_SESSION_COOKIE

python3 -c "
from substack.notes_poster import check_cookie_validity
valid = check_cookie_validity()
print(f'Cookie valid: {valid}')
"

# Expected outcomes:
# True → Cookie works, proceed to posting test
# False → Cookie expired, need to refresh:
#   1. Log into Substack in browser
#   2. DevTools → Application → Cookies → substack.com
#   3. Copy substack.sid value
#   4. Update SUBSTACK_SESSION_COOKIE in GitHub Secrets
#   5. Re-test
```

### Test 2.6 — Substack Notes Posting (LIVE — Posts to Your Substack)

```
⚠️ THIS WILL POST A REAL NOTE TO YOUR SUBSTACK

Only run this after Test 2.5 passes.
Requires: SUBSTACK_SESSION_COOKIE, a pre-generated note from Test 2.2

# Step 1: Dry-run first (no actual posting)
python3 -m substack.notes_poster --slot 1 --dry-run 2>&1
# Verify: it finds the note, converts to ProseMirror, logs what it would post

# Step 2: LIVE POST (this creates a real Substack Note)
python3 -m substack.notes_poster --slot 1 2>&1

# Expected output:
# - "Posted note: <note_id>" or similar success message
# - State updated in state/notes.json
# - Go to your Substack Notes feed and verify the note appeared

# If it fails with 422:
# - ProseMirror conversion may be wrong
# - Try both JSON string and dict for bodyJson (the poster should handle this)
# - Check the exact error response body

# If it fails with 401/403:
# - Cookie expired — refresh per Test 2.5 instructions

# AFTER POSTING: Go to Substack and delete the test note if you don't want it public
```

### Test 2.7 — Cookie Expiry Alert

```
Test that the cookie expiry email alert fires when the cookie is bad.
Requires: SENDGRID_API_KEY, STERLING_EMAIL_TO

# Set a fake invalid cookie and try to post
SUBSTACK_SESSION_COOKIE="expired_fake_cookie" python3 -m substack.notes_poster --slot 1 2>&1

# Expected:
# - Auth failure detected
# - SendGrid alert email sent to STERLING_EMAIL_TO
# - Check your inbox for the alert email
# - The script should NOT crash
```

### Test 2.8 — Twitter Engagement Fetch

```
Test that engagement metrics can be fetched.
Requires: TWITTER_BEARER_TOKEN (and per-account OAuth if needed)

python3 -m scripts.fetch_engagement 2>&1

# Expected outcomes:
# A) Success: Fetches tweets, calculates engagement, updates state/engagement.json
# B) Graceful failure: Logs "credentials not found" and exits cleanly
# C) Rate limit: Logs the limit and exits cleanly

# Verify state wasn't corrupted:
python3 -c "import json; data = json.load(open('state/engagement.json')); print(json.dumps(data, indent=2)[:500])"
```

---

## TEST PHASE 3: Tweet Generation + Posting (LIVE — Posts to Twitter)

This is the highest-risk test. It posts REAL tweets to your REAL Twitter accounts.

### Test 3.1 — Tweet Generator Dry-Run (Full Pipeline)

```
Run the full tweet generation pipeline in dry-run mode.
Requires: ANTHROPIC_API_KEY (or Grok credentials for context)

python3 -m twitter.live_tweet_generator --dry-run 2>&1

# Examine the full output. Check for:

# Sprint 4 features:
# ✓ "Loaded N categories from YAML" (YAML config loading)
# ✓ Voice guide references (persona injection)
# ✓ "Step 8.6" or "dedup" (cross-account ticker dedup)
# ✓ yfinance fallback messages (if Grok context was unavailable)
# ✓ Engagement data status

# Core pipeline:
# ✓ Categories selected for each account (P0-P6 cascade)
# ✓ Tweets generated (content visible in output)
# ✓ 14-step validation passed (or repair loop triggered)
# ✓ No crashes or unhandled exceptions

# Per-account:
# ✓ Account 1 (Alex): Distinct voice
# ✓ Account 2 (Rozalia): Distinct voice
# ✓ Account 3 (James): Distinct voice
# ✓ No duplicate tickers across accounts in same slot

# Save the output for review:
python3 -m twitter.live_tweet_generator --dry-run 2>&1 | tee /tmp/tweet_dryrun.log
echo "Output saved to /tmp/tweet_dryrun.log"
wc -l /tmp/tweet_dryrun.log
```

### Test 3.2 — Tweet Quality Review

```
From the dry-run output, extract the generated tweets and review quality.

# Find generated tweet content in the logs
grep -A5 "generated\|tweet.*content\|final.*text\|output.*text" /tmp/tweet_dryrun.log | head -60

# For each tweet, manually check:
# 1. Does it sound like the right persona? (Alex vs Rozalia vs James)
# 2. Is the category appropriate? (matches the data/context)
# 3. Are banned terms absent?
# 4. Is the length correct? (280 chars max for tweets)
# 5. Does it include a chart/image reference if the category needs one?
# 6. No "AI slop" language (e.g., "buckle up", "let's dive in")
```

### Test 3.3 — Chart/Image Generation

```
If tweets include charts (e.g., for RECEIPT, SIGNAL_ALERT categories),
verify charts are generated correctly.

# Check if chart generation is part of the pipeline:
grep -rn "chart\|image\|matplotlib\|plotly\|png\|jpg" twitter/live_tweet_generator.py | head -20

# Find where charts are saved:
find twitter/ -name "*.png" -o -name "*.jpg" | head -10
find substack/output/ -name "*.png" -o -name "*.jpg" | head -10

# If charts exist, verify they render:
# 1. Open the image files
# 2. Check they contain actual data (not blank/error images)
# 3. Verify the data matches the tweet content
```

### Test 3.4 — Live Tweet Post (ONE ACCOUNT ONLY)

```
⚠️ THIS POSTS A REAL TWEET

Do this for ONE account first. Pick the lowest-risk account.

# Check what flags control posting:
grep -n "post\|publish\|send\|--live\|--real" twitter/live_tweet_generator.py twitter/poster.py | head -20

# Option A: If there's a single-account flag
python3 -m twitter.live_tweet_generator --account 1 --live 2>&1
# (adjust flags based on what the code actually supports)

# Option B: If there's no per-account control, use the poster directly
# First generate a tweet via dry-run, then post it manually:
# 1. Copy the generated tweet text from the dry-run output
# 2. Post it via the poster:
python3 -c "
from twitter.poster import post_tweet
result = post_tweet(
    account='account_1_name',  # UPDATE with actual account identifier
    text='TEST: Integration test tweet. Will delete shortly.',
    # image_path=None  # Add if chart was generated
)
print(f'Posted: {result}')
"

# AFTER POSTING:
# 1. Check Twitter — did the tweet appear?
# 2. Does it look correct?
# 3. DELETE the test tweet if it was just a test message
```

---

## TEST PHASE 4: GitHub Actions Workflows

These tests verify the workflows trigger correctly and have all required secrets.

### Test 4.1 — Workflow Secret Audit

```
Verify every workflow references only secrets that exist.

echo "=== daily_content.yml secrets ==="
grep -o '\${{ secrets\.[A-Z_]* }}' .github/workflows/daily_content.yml | sort -u

echo "=== substack-notes.yml secrets ==="
grep -o '\${{ secrets\.[A-Z_]* }}' .github/workflows/substack-notes.yml | sort -u

echo "=== engagement-fetch.yml secrets ==="
grep -o '\${{ secrets\.[A-Z_]* }}' .github/workflows/engagement-fetch.yml | sort -u

# Also check any tweet-related workflows:
for f in .github/workflows/*tweet* .github/workflows/*twitter*; do
    [ -f "$f" ] && echo "=== $(basename $f) ===" && grep -o '\${{ secrets\.[A-Z_]* }}' "$f" | sort -u
done

# CROSS-REFERENCE: Every secret listed above must be set in GitHub.
# Go to: Repository Settings → Secrets and Variables → Actions
# Verify each one exists (you can see names but not values).
```

### Test 4.2 — Manual Workflow Dispatch (Dry-Run)

```
Test each workflow via manual dispatch with dry-run enabled.

# In GitHub UI (Actions tab):

# 1. substack-notes.yml → Run workflow → slot=1, dry_run=true
#    Watch the log. Check:
#    ✓ Python setup succeeds
#    ✓ Dependencies install
#    ✓ Slot determined correctly
#    ✓ Note generation runs (or finds pre-generated note)
#    ✓ Poster runs in dry-run mode (no actual post)
#    ✓ State files updated
#    ✓ Git commit step runs

# 2. engagement-fetch.yml → Run workflow
#    Watch the log. Check:
#    ✓ Fetch script runs
#    ✓ Graceful handling of any API issues
#    ✓ state/engagement.json not corrupted

# 3. daily_content.yml → Run workflow (if it has manual dispatch)
#    Watch the log. Check:
#    ✓ Context builder runs
#    ✓ Notes generator runs
#    ✓ All steps complete
```

### Test 4.3 — Cron Schedule Audit

```
Verify all cron schedules are correct and don't conflict.

python3 -c "
import yaml, glob

for f in sorted(glob.glob('.github/workflows/*.yml')):
    data = yaml.safe_load(open(f))
    if not data:
        continue
    schedule = data.get('on', {})
    if isinstance(schedule, dict):
        crons = schedule.get('schedule', [])
    else:
        crons = []
    
    if crons:
        name = data.get('name', f)
        print(f'\n{name} ({f}):')
        for c in crons:
            cron_expr = c.get('cron', c) if isinstance(c, dict) else c
            print(f'  {cron_expr}')
"

# Cross-reference against expected schedule:
# daily_content.yml:      07:00 ET (12:00/11:00 UTC)
# substack-notes.yml:     08:30, 12:30, 17:00 ET (×2 for EST/EDT)
# engagement-fetch.yml:   21:00 ET (02:00/01:00 UTC)
# tweet workflows:        Check existing schedule
#
# Verify: No overlapping times that could cause git push conflicts
```

### Test 4.4 — Timezone Dedup Logic

```
The notes workflow has 6 cron entries (3 slots × 2 for EST/EDT).
Verify the timezone dedup logic correctly maps UTC hour → slot.

python3 -c "
# Simulate the slot determination logic from the workflow
import datetime

# EST mapping (UTC = ET + 5)
est_map = {13: 1, 17: 2, 22: 3}  # 08:30, 12:30, 17:00 ET
# EDT mapping (UTC = ET + 4)
edt_map = {12: 1, 16: 2, 21: 3}  # 08:30, 12:30, 17:00 ET

for hour in [12, 13, 16, 17, 21, 22]:
    slot_est = est_map.get(hour, None)
    slot_edt = edt_map.get(hour, None)
    print(f'UTC {hour:02d}:30 → EST slot={slot_est}, EDT slot={slot_edt}')
    # Only ONE should be non-None at any time (depends on current DST)
    # The workflow should skip if it gets the wrong timezone's trigger
"
```

---

## TEST PHASE 5: End-to-End Pipeline Simulation

Simulate a full day of operations in order.

### Test 5.1 — Morning Pipeline (07:00 ET)

```
Simulate the daily_content.yml workflow locally.

# Step 1: Build daily context
python3 -m substack.daily_context_builder 2>&1 | tail -20

# Verify output:
ls -la substack/output/current/daily_context.md
ls -la substack/output/current/daily_notes_context.json
python3 -c "
import json
ctx = json.load(open('substack/output/current/daily_notes_context.json'))
print(f'Date: {ctx.get(\"date\")}')
print(f'Day: {ctx.get(\"day\")}')
print(f'Note schedule: {ctx.get(\"note_schedule\", [])}')
"

# Step 2: Generate all 3 notes (existing generator)
python3 -m substack.daily_notes_generator 2>&1 | tail -20

# Verify:
for i in 1 2 3; do
    FILE="substack/output/current/daily_notes/note_slot${i}.html"
    if [ -f "$FILE" ]; then
        WORDS=$(python3 -c "import re; print(len(re.sub('<[^>]+>', '', open('$FILE').read()).split()))")
        echo "Slot $i: $WORDS words ✓"
    else
        echo "Slot $i: MISSING ✗"
    fi
done

# Step 3: Generate tweets (dry-run)
python3 -m twitter.live_tweet_generator --dry-run 2>&1 | tail -30
```

### Test 5.2 — Notes Posting Pipeline (08:30, 12:30, 17:00 ET)

```
Simulate the 3 daily note posts.

# Slot 1 (08:30 ET)
python3 -m substack.notes_poster --slot 1 --dry-run 2>&1
echo "---"

# Slot 2 (12:30 ET)
python3 -m substack.notes_poster --slot 2 --dry-run 2>&1
echo "---"

# Slot 3 (17:00 ET)
python3 -m substack.notes_poster --slot 3 --dry-run 2>&1

# Check state accumulation:
python3 -c "
import json
state = json.load(open('state/notes.json'))
print(json.dumps(state, indent=2)[:500])
"
# Verify: 3 slots tracked, sorted by slot number, no duplicates
```

### Test 5.3 — Content Tracker Integration

```
Verify the content tracker correctly records all publications.

python3 -m scripts.content_tracker --status 2>&1

# Check:
# ✓ Tweet streak tracked
# ✓ Notes streak tracked
# ✓ Today's publications recorded
# ✓ No data corruption
```

### Test 5.4 — Evening Pipeline (21:00 ET)

```
Simulate the engagement fetch.

python3 -m scripts.fetch_engagement 2>&1

# Then verify the data feeds back into the tweet generator:
python3 -c "
from twitter.live_tweet_generator import load_engagement_data
data = load_engagement_data()
if data and data.get('last_updated'):
    print(f'Engagement data loaded: last_updated={data[\"last_updated\"]}')
    accounts = data.get('accounts', {})
    for acct, info in accounts.items():
        categories = info.get('by_category', {})
        print(f'  {acct}: {len(categories)} categories tracked')
else:
    print('No engagement data yet (expected on first run)')
"
```

---

## TEST PHASE 6: Failure Mode Tests

Verify graceful degradation when things break.

### Test 6.1 — Missing API Key

```
# Notes generator without API key
unset ANTHROPIC_API_KEY
python3 -m substack.notes_generator --slot 1 2>&1 | head -10
# Expected: Clear error message, no crash
export ANTHROPIC_API_KEY="your_key_here"  # Restore
```

### Test 6.2 — Missing Cookie

```
# Notes poster without cookie
unset SUBSTACK_SESSION_COOKIE
python3 -m substack.notes_poster --slot 1 2>&1 | head -10
# Expected: Warning logged, note saved locally, alert attempt, no crash
export SUBSTACK_SESSION_COOKIE="your_cookie_here"  # Restore
```

### Test 6.3 — Missing YAML Configs (Sprint 4 Fallbacks)

```
mv config/tweet_prompts config/tweet_prompts.bak
mv config/persona_voice_guides.yaml config/persona_voice_guides.yaml.bak

python3 -m twitter.live_tweet_generator --dry-run 2>&1 | head -30
# Expected: Fallback warnings, hardcoded examples used, no crash

mv config/tweet_prompts.bak config/tweet_prompts
mv config/persona_voice_guides.yaml.bak config/persona_voice_guides.yaml
```

### Test 6.4 — Missing Note Files

```
# What happens if the poster can't find a pre-generated note?
mv substack/output/current/daily_notes substack/output/current/daily_notes.bak

python3 -m substack.notes_poster --slot 1 --dry-run 2>&1 | head -15
# Expected: Fallback generation triggered OR clear error, no crash

mv substack/output/current/daily_notes.bak substack/output/current/daily_notes
```

### Test 6.5 — Stale/Corrupted State Files

```
# Corrupt notes.json and verify recovery
cp state/notes.json state/notes.json.bak
echo "CORRUPTED" > state/notes.json

python3 -m substack.notes_poster --slot 1 --dry-run 2>&1 | head -10
# Expected: Handles gracefully (reset state or clear error)

cp state/notes.json.bak state/notes.json  # Restore
```

---

## FINAL CHECKLIST

Run this after all tests pass:

```
echo "╔══════════════════════════════════════════╗"
echo "║  STERLING SIGNALS — GO-LIVE CHECKLIST    ║"
echo "╚══════════════════════════════════════════╝"

echo ""
echo "=== SECRETS ==="
echo "[ ] ANTHROPIC_API_KEY set in GitHub Secrets"
echo "[ ] SENDGRID_API_KEY set in GitHub Secrets"
echo "[ ] STERLING_EMAIL_TO set in GitHub Secrets"
echo "[ ] SUBSTACK_SESSION_COOKIE set (and verified not expired)"
echo "[ ] TWITTER_BEARER_TOKEN set in GitHub Secrets"
echo "[ ] All Twitter OAuth per-account secrets set"
echo "[ ] Grok/context source credentials set (if applicable)"

echo ""
echo "=== VERIFIED WORKING ==="
echo "[ ] All Python imports pass (Test 1.1)"
echo "[ ] All config files valid (Test 1.2)"
echo "[ ] Tweet generator dry-run passes (Test 3.1)"
echo "[ ] Note generation produces valid HTML (Test 2.2)"
echo "[ ] HTML→ProseMirror conversion passes all 5 cases (Test 1.5)"
echo "[ ] SendGrid delivers email (Test 2.3)"
echo "[ ] Substack cookie valid (Test 2.5)"
echo "[ ] Substack note posted successfully (Test 2.6)"
echo "[ ] Cookie expiry alert fires (Test 2.7)"
echo "[ ] Engagement fetch runs (Test 2.8)"
echo "[ ] At least one test tweet posted (Test 3.4)"
echo "[ ] All workflow YAMLs valid (Test 1.2)"
echo "[ ] Cron schedules correct (Test 4.3)"
echo "[ ] Fallback modes all work (Tests 6.1-6.5)"

echo ""
echo "=== POST-LAUNCH MONITORING ==="
echo "[ ] Set calendar reminder: Check Substack cookie in 30 days"
echo "[ ] Monitor first 3 days of automated runs"
echo "[ ] Check GitHub Actions for any failed runs"
echo "[ ] Verify tweets appear on all 3 accounts"
echo "[ ] Verify notes appear on Substack 3x daily"
echo "[ ] Verify daily email arrives"
echo "[ ] Check state files aren't growing unbounded"
```

---

## TROUBLESHOOTING QUICK REFERENCE

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "AuthenticationError" from Anthropic | Bad API key | Regenerate at console.anthropic.com |
| 422 from Substack | ProseMirror format wrong | Check HTML→PM conversion (Test 1.5) |
| 401/403 from Substack | Cookie expired | Refresh cookie (Test 2.5 instructions) |
| No email received | SendGrid sender not verified | Verify sender domain in SendGrid dashboard |
| "tweepy.errors.Unauthorized" | Twitter OAuth credentials wrong | Regenerate at developer.twitter.com |
| yfinance returns None | Market closed or ticker invalid | Normal outside market hours; check ticker symbol |
| "No engagement data" | First run or fetch hasn't run yet | Run engagement fetch manually (Test 2.8) |
| Git push conflicts in Actions | Two workflows ran simultaneously | Check cron schedules for overlap (Test 4.3) |
| "Module not found" | Missing pip dependency | Check requirements.txt, pip install missing package |
| Notes content is garbage | Prompt too short or wrong context | Review build_note_prompt() output, check context JSON |
