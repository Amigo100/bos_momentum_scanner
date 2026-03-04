# Sprint 5 Implementation Spec — Notes Auto-Publishing

## Context for Claude Code

This sprint automates the daily Substack Notes publishing. Currently the user manually runs the notes prompt in Claude.ai, copies the HTML output, and pastes it into Substack — 3 times per day, 7 days per week. That's ~5 min × 7 days = 35 min/week of repetitive work.

The content_prompt_handbook_v5.md defines a universal notes prompt with an embedded rotation matrix: 3 notes per day, different mix each day (Community, Winner Highlight, Market Macro, Ticker News, Theme Spotlight, etc.). The daily_context_builder.py already generates a daily_notes_context.json with structured data for note generation.

**What this sprint produces:**
- `substack/notes_generator.py` — Generates 3 notes per day using Claude Sonnet API
- `substack/notes_poster.py` — Posts notes to Substack via session cookie
- `.github/workflows/substack-notes.yml` — 3x daily GitHub Actions workflow
- Cookie rotation alerting and monitoring
- Integration with state/notes.json and state/content_tracker.json

**What this sprint does NOT do:**
- No changes to the existing daily content pipeline
- No changes to the tweet generator
- No auto-publishing of full Substack posts (only Notes)

**Cost estimate:** ~3 Sonnet calls per day × ~500 input tokens + ~300 output tokens each = ~$0.01-0.02/day

---

## Files to Read First

1. `substack/docs/content_prompt_handbook_v5.md` — The universal notes prompt and rotation matrix. This is the source of truth for note types, day-of-week assignments, and HTML format.
2. `substack/output/current/daily_notes_context.json` — Structured data for notes (from daily_context_builder.py). Understand what's available: portfolio data, signals, market context.
3. `substack/output/current/daily_context.md` — The context doc. Check if it contains the notes prompt or references it.
4. `substack/daily_context_builder.py` — Understand what data it makes available for notes.
5. `.github/workflows/daily_content.yml` — The existing daily workflow. The notes workflow will run separately (different schedule: 3x daily vs 1x daily).
6. `state/notes.json` — Sprint 1 scaffold for notes tracking.
7. `state/content_tracker.json` — Sprint 3 content tracking (notes_streak field).
8. Any existing Substack interaction code:
   - `substack/` directory — check for existing posters, API clients, cookie handling
9. `scripts/build_analysis_package.py` — Sprint 2's SendGrid email pattern (for cookie expiry alerts).

---

## Task 1: Investigation — Substack Notes Architecture

### Read-only investigation. Do not modify any files.

**1A. The Notes Prompt and Rotation Matrix:**
```bash
# Find the universal notes prompt in the handbook
grep -n "notes\|Notes\|NOTES\|universal\|rotation" substack/docs/content_prompt_handbook_v5.md | head -20
```
- Extract the rotation matrix: which note types are assigned to which days
- Extract the prompt text (inside ``` blocks under the notes section)
- What format does the prompt expect output in? (HTML divs with inline styles?)
- What deduplication rules exist? (Monday's winner ≠ Thursday's, etc.)

**1B. daily_notes_context.json structure:**
```bash
cat substack/output/current/daily_notes_context.json | python3 -m json.tool | head -60
```
- What fields are available? (day, date, note_schedule, portfolio, signals, market?)
- Does note_schedule already contain today's note types from the rotation matrix?
- What portfolio data is included? (tickers, prices, P&L, themes?)
- What market data is included?

**1C. Existing Substack interaction code:**
```bash
find substack/ -name "*.py" | head -20
grep -rn "substack\|cookie\|session\|publish\|post.*note\|api.*substack" substack/ --include="*.py" | head -30
```
- Is there already a notes poster or Substack API client?
- How is authentication handled? (session cookie, API key, OAuth?)
- Is there a cookie storage mechanism?
- Any existing note publishing code we should reuse?

**1D. Existing notes generation in the daily pipeline:**
```bash
grep -n "notes\|generate.*note\|note.*gen" substack/daily_context_builder.py | head -20
# Also check the daily workflow for notes steps
grep -n "notes" .github/workflows/daily_content.yml | head -10
```
- Does the daily pipeline already generate notes? (Task 1 findings from Sprint 3 mentioned a "notes generator" step)
- If so, what does it produce and where?
- We may need to ENHANCE existing code rather than build from scratch

**1E. Substack Notes API:**
```bash
# Check if there's documentation or code about how to post Notes
grep -rn "note\|substacknote\|substack.*api\|api.*substack" . --include="*.py" --include="*.md" | head -20
```
- Substack Notes API is unofficial — it uses the session cookie from the browser
- The endpoint is typically POST to substack.com/api/v1/notes or similar
- Check if any existing code reveals the API endpoint and payload format

**1F. Cookie handling:**
```bash
# Check for existing cookie storage/management
grep -rn "cookie\|SUBSTACK.*SESSION\|session.*cookie" . --include="*.py" --include="*.yml" --include="*.env" | head -20
find . -name "*cookie*" -o -name "*.cookie" | head -10
```
- Where are Substack cookies stored? (env var, file, GitHub secret?)
- Is there a refresh/rotation mechanism?
- How often do they expire?

Report ALL findings. The notes generation approach (new script vs enhancing existing) depends on 1D. The posting approach depends on 1C/1E/1F.

---

## Task 2: Build the Notes Generator

### File: `substack/notes_generator.py`

This script generates 3 notes per day using the Claude Sonnet API. It does NOT post them — that's Task 3.

**Architecture:**

```
notes_generator.py
├── load_notes_context()      — Read daily_notes_context.json
├── get_note_schedule()       — Get today's 3 note types from rotation matrix
├── build_note_prompt()       — Build a focused Sonnet prompt for one note
├── generate_note()           — Call Claude Sonnet API
├── validate_note()           — Check output format and banned terms
├── generate_daily_notes()    — Orchestrate all 3 notes
└── save_notes()              — Write to output file for poster
```

**Key Design Decisions:**

1. **Sonnet, not Opus**: Notes are 100-200 words each, template-driven. Sonnet is sufficient and ~1/10th the cost. Use `claude-sonnet-4-5-20250929` (or the latest Sonnet model available).

2. **One note per call**: Generate each note individually (not all 3 in one call). This allows:
   - Slot-specific timing (note 1 at 08:30, note 2 at 12:30, note 3 at 17:00)
   - Better quality (focused prompt per note type)
   - Easier retry on failure

3. **The prompt should be MUCH shorter than the handbook's universal prompt**: The handbook prompt is designed for Opus in Claude.ai with the full context document attached. For automated Sonnet generation, strip it to essentials:
   - Note type for this slot
   - Today's post topic (for deduplication — don't repeat)
   - Relevant portfolio data (top winners, recent signals)
   - Market snapshot (SPY/QQQ moves, VIX)
   - Banned terms list
   - HTML output template

4. **HTML output**: Each note is a self-contained HTML div with inline styles, matching the handbook's Notes theme spec:
   ```html
   <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
   [Note content]
   <p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
   </div>
   ```

**Implementation:**

```python
def build_note_prompt(note_type, slot_number, context):
    """
    Build a focused prompt for Sonnet to generate one note.
    
    Args:
        note_type: e.g., "Market Macro", "Winner Highlight", "Ticker News"
        slot_number: 1, 2, or 3 (for time-of-day context)
        context: dict from daily_notes_context.json
    
    The prompt should be ~400-600 tokens (much shorter than the handbook's 
    full notes prompt). Include:
    - Note type and what it should cover
    - Today's post topic (to avoid repeating)
    - Relevant data (portfolio for Winner Highlight, market for Market Macro, etc.)
    - Banned terms (the full list from the handbook)
    - Output format (HTML div with inline styles)
    - Length target (100-200 words)
    - Tone guide (brief — Sonnet doesn't need as much guidance as in the 
      handbook's prompt which targets Opus)
    """

def generate_note(prompt, note_type):
    """
    Call Claude Sonnet API to generate one note.
    
    Uses the Anthropic API directly (not Claude.ai).
    Requires ANTHROPIC_API_KEY in environment.
    
    Model: claude-sonnet-4-5-20250929
    Max tokens: 500 (notes are short)
    Temperature: 0.7 (some creativity, not too wild)
    
    Returns: HTML string or None on failure
    """
    import anthropic
    
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY from env
    
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Extract text from response
    html = response.content[0].text
    
    # Basic validation
    if "<div" not in html.lower():
        logger.warning(f"Note output missing HTML div wrapper for {note_type}")
        return None
    
    return html

def validate_note(html, note_type, context):
    """
    Validate generated note before publishing.
    
    Checks:
    - Contains HTML div wrapper
    - Contains disclaimer ("Not financial advice")
    - No banned terms (from handbook's master list)
    - Length within range (50-300 words of actual text)
    - No negative P&L mentions (winners-only policy)
    - Doesn't repeat today's post topic ticker
    
    Returns: (is_valid, issues_list)
    """

def generate_daily_notes(slot_number=None):
    """
    Generate notes for today (or a specific slot).
    
    If slot_number is None: generate all 3 notes
    If slot_number is 1/2/3: generate just that slot's note
    
    Workflow:
    1. Load daily_notes_context.json
    2. Get today's note schedule (3 note types from rotation matrix)
    3. For each note (or just the specified slot):
       a. Build prompt
       b. Generate via Sonnet
       c. Validate
       d. Retry once on validation failure (with feedback about what failed)
    4. Save results
    
    Returns list of generated notes (HTML strings)
    """

def save_notes(notes, slot_number=None):
    """
    Save generated notes for the poster to pick up.
    
    Output: substack/output/current/notes/
    Files: note_1_{type}_{date}.html, note_2_{type}_{date}.html, note_3_{type}_{date}.html
    
    Also update state/notes.json with generation status.
    """
```

**Rotation Matrix Handling:**

The handbook defines which note types go in which slots on which days. Two approaches:

Option A: Read the rotation matrix from the handbook and implement it in code.
Option B: Read it from daily_notes_context.json if the daily_context_builder already assigns note types.

Check Task 1B findings — if daily_notes_context.json already has `note_schedule` with today's note types, use that (Option B). If not, implement the rotation matrix from the handbook (Option A).

**Edge Cases:**
- ANTHROPIC_API_KEY missing: Log error, skip generation, don't crash
- daily_notes_context.json missing: Use minimal defaults (date, day of week)
- Sonnet returns malformed HTML: Retry once with "Output must be a valid HTML div"
- Rate limit: Wait and retry (Sonnet limits are generous)
- Zero portfolio data: Skip Winner Highlight type, use a fallback note type

---

## Task 3: Build the Notes Poster

### File: `substack/notes_poster.py`

This script posts generated notes to Substack using a session cookie.

**Important**: Substack does NOT have an official Notes API. Notes are posted via the same session that the browser uses. This requires a session cookie extracted from the browser.

**Implementation:**

```python
"""
Post notes to Substack using session cookie authentication.

The session cookie must be set as SUBSTACK_SESSION_COOKIE in the environment
(typically from GitHub Secrets).

To extract the cookie:
1. Log into Substack in your browser
2. Open DevTools → Application → Cookies → substack.com
3. Copy the value of the 'substack.sid' cookie
4. Set as SUBSTACK_SESSION_COOKIE in GitHub Secrets

Cookie typically expires after 30-90 days. The script alerts when 
authentication fails (likely expired cookie).
"""

def post_note(html_content, cookie=None):
    """
    Post a single note to Substack.
    
    Args:
        html_content: The note HTML to publish
        cookie: Session cookie (from env if not provided)
    
    Returns:
        dict: {"success": bool, "note_id": str or None, "error": str or None}
    
    The Substack Notes API endpoint is:
    POST https://substack.com/api/v1/notes
    
    Headers:
        Cookie: substack.sid={cookie_value}
        Content-Type: application/json
    
    Payload (verify against actual API — this is the known structure):
        {
            "body_json": {
                "type": "note",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "..."}]}
                ]
            }
        }
    
    NOTE: The exact payload format may differ. Substack uses ProseMirror JSON 
    internally, not raw HTML. If posting HTML directly doesn't work, we may 
    need to convert HTML to ProseMirror format or use a different endpoint.
    
    ALTERNATIVE APPROACH: If the Notes API is too fragile, consider:
    - Using Substack's email-to-note feature (if it exists)
    - Using the Substack mobile app's share API
    - Posting via Puppeteer/Playwright browser automation
    
    The investigation in Task 1C/1E should reveal the best approach.
    """

def check_cookie_validity(cookie=None):
    """
    Test if the session cookie is still valid.
    
    Makes a lightweight authenticated request to Substack.
    Returns: (is_valid, expiry_info_if_available)
    
    If invalid: send alert email via SendGrid.
    """

def send_cookie_alert():
    """
    Alert the user that the Substack session cookie has expired.
    
    Uses SendGrid (from Sprint 2 pattern).
    Subject: "⚠️ Sterling Signals — Substack cookie expired"
    Body: Instructions to refresh the cookie.
    """
```

**Cookie Management:**

The session cookie is stored in GitHub Secrets as `SUBSTACK_SESSION_COOKIE`. When it expires:
1. The poster detects auth failure
2. Sends an alert email
3. Skips publishing (notes are saved locally but not posted)
4. The user refreshes the cookie manually

Future enhancement: A browser extension or local script that auto-refreshes the cookie. But for now, manual refresh with alerting is sufficient.

**HTML to Substack Format:**

Substack Notes may not accept raw HTML. The poster may need to convert HTML notes to Substack's internal format (ProseMirror JSON) or strip to plain text with basic formatting. Task 1E findings should clarify this.

If Substack Notes requires plain text (no HTML):
- Strip HTML tags
- Preserve line breaks
- Keep $TICKER formatting
- Keep the disclaimer text

---

## Task 4: Create the GitHub Actions Workflow

### File: `.github/workflows/substack-notes.yml`

The workflow runs 3 times daily to generate and post notes at different times.

```yaml
name: Publish Substack Notes

on:
  schedule:
    # Slot 1: 08:30 ET
    - cron: '30 13 * * *'   # UTC during EST
    - cron: '30 12 * * *'   # UTC during EDT
    
    # Slot 2: 12:30 ET  
    - cron: '30 17 * * *'   # UTC during EST
    - cron: '30 16 * * *'   # UTC during EDT
    
    # Slot 3: 17:00 ET
    - cron: '0 22 * * *'    # UTC during EST
    - cron: '0 21 * * *'    # UTC during EDT
    
  workflow_dispatch:
    inputs:
      slot:
        description: 'Slot number (1, 2, or 3)'
        required: false
        default: ''
      dry_run:
        description: 'Generate but do not post'
        required: false
        default: 'false'

jobs:
  publish-note:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install anthropic requests  # Add other deps as needed
      
      - name: Determine slot number
        id: slot
        run: |
          # If manual dispatch with slot specified, use that
          # Otherwise, determine from current UTC hour
          if [ -n "${{ github.event.inputs.slot }}" ]; then
            echo "slot=${{ github.event.inputs.slot }}" >> $GITHUB_OUTPUT
          else
            HOUR=$(date -u +%H)
            if [ "$HOUR" -le "14" ]; then
              echo "slot=1" >> $GITHUB_OUTPUT
            elif [ "$HOUR" -le "18" ]; then
              echo "slot=2" >> $GITHUB_OUTPUT
            else
              echo "slot=3" >> $GITHUB_OUTPUT
            fi
          fi
      
      - name: Generate note
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python3 -m substack.notes_generator --slot ${{ steps.slot.outputs.slot }}
      
      - name: Post to Substack
        if: ${{ github.event.inputs.dry_run != 'true' }}
        env:
          SUBSTACK_SESSION_COOKIE: ${{ secrets.SUBSTACK_SESSION_COOKIE }}
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          STERLING_EMAIL_TO: ${{ secrets.STERLING_EMAIL_TO }}
        run: |
          python3 -m substack.notes_poster --slot ${{ steps.slot.outputs.slot }} || {
            echo "Posting failed — note saved locally but not published"
            echo "Check if session cookie needs refresh"
          }
      
      - name: Update tracking
        run: |
          python3 -m scripts.content_tracker --published notes
      
      - name: Commit state updates
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add state/notes.json state/content_tracker.json substack/output/current/notes/
          git diff --cached --quiet || git commit -m "Auto-publish note slot ${{ steps.slot.outputs.slot }}"
          git push || echo "Push failed - will retry"
```

**Scheduling notes:**
- 6 cron entries (3 slots × 2 for EST/EDT) — match the existing dual-cron pattern
- The slot determination logic uses UTC hour as a heuristic
- Manual dispatch allows testing individual slots
- dry_run mode generates without posting (for testing)

**Secrets needed:**
- `ANTHROPIC_API_KEY` — for Sonnet note generation
- `SUBSTACK_SESSION_COOKIE` — for posting
- `SENDGRID_API_KEY` + `STERLING_EMAIL_TO` — for cookie expiry alerts

---

## Task 5: Integration with State Tracking

Update `state/notes.json` after each note is generated and posted:

```python
def update_notes_state(slot_number, note_type, status, note_id=None):
    """
    Update state/notes.json after note generation/posting.
    
    Adds to today's slots:
    {
        "slot": 1,
        "note_type": "Market Macro",
        "status": "published",  # or "generated", "failed", "skipped"
        "generated_at": "2026-03-04T13:30:00Z",
        "published_at": "2026-03-04T13:30:15Z",
        "note_id": "abc123",  # Substack note ID if available
        "cost_usd": 0.003     # Estimated Sonnet cost
    }
    
    Also update:
    - today.notes_published count
    - recent[] array (last 7 days of notes)
    """
```

Also update `state/content_tracker.json` via the Sprint 3 content_tracker:
```bash
python3 -m scripts.content_tracker --published notes
```

---

## Task 6: Test End-to-End

### Verification Steps

1. **Test note generation (no posting):**
```bash
# Generate slot 1 note
python3 -m substack.notes_generator --slot 1
# Check output
ls substack/output/current/notes/note_1_*.html
# Verify: HTML format, disclaimer present, no banned terms, reasonable length
```

2. **Test all 3 slots:**
```bash
python3 -m substack.notes_generator --slot 1
python3 -m substack.notes_generator --slot 2
python3 -m substack.notes_generator --slot 3
ls -la substack/output/current/notes/note_*.html
# All 3 files should exist
```

3. **Test note validation:**
```bash
# Check each note for banned terms
python3 -c "
import glob
for i in [1,2,3]:
    files = glob.glob(f'substack/output/current/notes/note_{i}_*.html')
    if not files:
        print(f'Slot {i}: MISSING — no note file found')
        continue
    html = open(files[0]).read()
    has_disclaimer = 'Not financial advice' in html
    print(f'Slot {i}: {\"PASS\" if has_disclaimer else \"FAIL — missing disclaimer\"} — {files[0]}')
"
```

4. **Test cookie check (may fail without cookie — that's OK):**
```bash
python3 -c "
from substack.notes_poster import check_cookie_validity
valid, info = check_cookie_validity()
print(f'Cookie: {\"valid\" if valid else \"invalid/missing\"} — {info}')
"
```

5. **Test posting in dry-run mode:**
```bash
# This should generate but not post
python3 -m substack.notes_poster --slot 1 --dry-run
```

6. **Test state tracking:**
```bash
cat state/notes.json | python3 -m json.tool
python3 -m scripts.content_tracker --status
```

7. **Verify workflow YAML:**
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/substack-notes.yml')); print('Valid')"
```

8. **Test cookie expiry alerting:**
```bash
# Set an invalid cookie and try to post
SUBSTACK_SESSION_COOKIE="invalid" python3 -m substack.notes_poster --slot 1 2>&1
# Should detect auth failure and attempt to send alert
```

9. **Verify costs:**
```bash
# Check that generation cost is reasonable
# 3 notes × ~800 tokens each × Sonnet pricing = should be < $0.05/day
python3 -c "
# Rough cost estimate
input_tokens = 500 * 3   # 500 per note, 3 notes
output_tokens = 300 * 3  # 300 per note, 3 notes
cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
print(f'Estimated daily cost: \${cost:.4f}')
"
```

---

## Sprint 5 Completion Checklist

```bash
echo "=== Notes Generator ==="
python3 -c "from substack.notes_generator import generate_daily_notes; print('Import OK')"

echo "=== Notes Poster ==="
python3 -c "from substack.notes_poster import post_note, check_cookie_validity; print('Import OK')"

echo "=== Generated Notes ==="
ls -la substack/output/current/notes/note_*.html 2>/dev/null || echo "No notes generated yet"

echo "=== State ==="
cat state/notes.json | python3 -m json.tool | head -15

echo "=== Workflow ==="
ls -la .github/workflows/substack-notes.yml

echo "=== Secrets Needed ==="
echo "  ANTHROPIC_API_KEY (for Sonnet)"
echo "  SUBSTACK_SESSION_COOKIE (for posting)"
echo "  SENDGRID_API_KEY (for cookie alerts)"
echo "  STERLING_EMAIL_TO (for cookie alerts)"
```

### Commit Message

```
Sprint 5: Substack Notes auto-publishing — saves ~35 min/week

- substack/notes_generator.py: Generates 3 notes/day via Claude Sonnet API,
  using rotation matrix from handbook + daily context data. ~$0.02/day cost.
- substack/notes_poster.py: Posts notes to Substack via session cookie.
  Cookie expiry detection + SendGrid alert.
- .github/workflows/substack-notes.yml: 3x daily workflow (08:30, 12:30, 17:00 ET)
  with manual dispatch and dry-run mode.
- State tracking: notes.json + content_tracker.json updated per slot.
- Graceful degradation: if Sonnet fails, poster fails, or cookie expires,
  notes are saved locally and alerts are sent. No crashes.
```

---

## Notes for Claude Code

- **Task 1 is critical** — the Substack Notes posting mechanism is the biggest unknown. The API is unofficial and the payload format may require ProseMirror JSON instead of raw HTML. Investigate thoroughly before building the poster.
- **If Substack posting is too fragile**, build the generator fully but stub the poster with a clear TODO. The generator alone has value — it saves the user from running the notes prompt manually. They can still copy-paste from the generated files.
- **Anthropic API key**: The user may have this in GitHub Secrets already (for other Claude integrations). Check.
- **The rotation matrix might already be in daily_notes_context.json** — if so, use it rather than reimplementing from the handbook.
- **Banned terms enforcement**: Import or replicate the banned terms check from Sprint 4's YAML configs. Notes must follow the same rules as tweets.
- **Cost tracking**: Log the approximate Sonnet cost per generation to state/notes.json. This feeds the dashboard System Health panel later.
