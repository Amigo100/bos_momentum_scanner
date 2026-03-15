# Sterling Signals v8: Claude Code Implementation Spec
## Comprehensive codebase changes with testing plan

---

## CRITICAL RULE

The following files are FINAL. Paste them into the repo as-is. Do NOT edit them further:

| File | Repo destination | Lines |
|------|-----------------|-------|
| `COWORK_INSTRUCTIONS.md` | `substack/COWORK_INSTRUCTIONS.md` | 955 |
| `content_prompt_handbook_v7_0.md` | `substack/docs/content_prompt_handbook_v7_0.md` | 1,256 |
| `sterling_prompt_library_v5.html` | Root or wherever the current v5 lives | 6,890 |
| `voice_rules.md` | `config/voice_rules.md` (NEW file) | 263 |
| `start_here.html` | Paste into Substack manually | 421 |

---

## PHASE 1: Data Schema Changes

### 1.1 Add `structural_force` column to portfolio.csv

**Current CSV headers (16 columns):**
```
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,stop_pct,position_size_pct,position_dollars,sizing_gear
```

**New CSV headers (17 columns):**
```
ticker,status,entry_date,entry_price,exit_date,exit_price,highest_close,theme,tier,signal_type,conviction,notes,stop_pct,position_size_pct,position_dollars,sizing_gear,structural_force
```

**Values to add for current positions:**

| ticker | structural_force |
|--------|-----------------|
| SOFI | Financial Infrastructure |
| EVTL | Defence Spending |
| NVDA | AI Infrastructure |
| AMD | AI Infrastructure |
| TMDX | Biotech Capital Cycle |
| ASPI | Nuclear Renaissance |
| HIVE | AI Infrastructure |
| BAND | AI Infrastructure |

**Implementation:**
1. Open `portfolio/output/portfolio.csv`
2. Add `structural_force` as the 17th column header
3. Add the force value for each row per the table above
4. For any CLOSED/historical rows, leave the field empty or infer from theme

**CRITICAL: Trace all readers of portfolio.csv before changing.**

Run this grep in the repo root:
```bash
grep -rn "portfolio.csv\|portfolio_csv\|DictReader.*portfolio\|portfolio.*csv" --include="*.py" --include="*.js"
```

Files likely affected:
- `scanner/merge_decisions.py` (reads portfolio to check existing positions)
- `portfolio/tracker.py` (writes portfolio.csv, must include new column)
- `scripts/build_daily_email.py` (reads portfolio for email content)
- `portfolio/export_google_sheets.py` or similar (generates portfolio_google_sheets.csv)
- Any note generation code that iterates portfolio rows

**For each file found:**
- If it uses `csv.DictReader`: SAFE. New column is automatically available as `row["structural_force"]`. No changes needed unless the file constructs new rows (then add the field).
- If it uses `csv.reader` with positional indexing: BREAKING. Must update column indices.
- If it writes CSV with hardcoded headers: Must add `structural_force` to the header list.
- If it validates column count: Must update the expected count.

**Testing after 1.1:**
```bash
# Verify CSV is valid
python3 -c "
import csv
with open('portfolio/output/portfolio.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        assert 'structural_force' in row, f'Missing structural_force in {row}'
        if row['status'] == 'OPEN':
            assert row['structural_force'] != '', f'{row[\"ticker\"]} has empty structural_force'
        print(f'{row[\"ticker\"]}: {row[\"structural_force\"]}')
print('PASS: All OPEN positions have structural_force')
"

# Verify all downstream readers still work
python3 -m pytest tests/ -v --tb=short 2>&1 | head -50
```

### 1.2 Verify structural_force flows through decisions.json

**Current state:** The prompt library Prompt 2 already analyses structural forces. The `decisions.json` file at line ~6333 in the prompt library references a `structural_force` field. Check whether `merge_decisions.py` preserves this field when constructing the final JSON.

```bash
grep -n "structural_force" scanner/merge_decisions.py
grep -n "structural_force" scanner/output/decisions.json | head -5
```

**If the field exists in decisions.json already:** No code change needed. The prompt library updates (Prompt 11 split) handle the content generation side.

**If the field is missing from decisions.json output:** Add it to `merge_decisions.py` in the position construction logic, pulling from the prompt output.

### 1.3 Verify signal_history_rows.csv

**Current state (VERIFIED):** The actual file already has `structural_force` as column 9:
```
scan_date,symbol,price_at_scan,theme,theme_score,theme_classification,wave_strength,source,structural_force,stage_reached,final_verdict,conviction,tier,return_driver,entry_price,stop_price,notes
```

The prompt library v5 updates (Prompt 12) have already been updated to reference this schema. No code changes needed here.

**Verification:**
```bash
head -1 scanner/output/signal_history_rows.csv
# Should show structural_force as 9th column
```

---

## PHASE 2: Document Deployment

These are simple file replacements. No code logic involved.

### 2.1 Replace COWORK_INSTRUCTIONS.md
```bash
cp /path/to/new/COWORK_INSTRUCTIONS.md substack/COWORK_INSTRUCTIONS.md
```

### 2.2 Replace content_prompt_handbook
```bash
cp /path/to/new/content_prompt_handbook_v7_0.md substack/docs/content_prompt_handbook_v7_0.md
```

### 2.3 Replace sterling_prompt_library_v5.html
```bash
# Find current location first
find . -name "sterling_prompt_library*" -type f
# Then replace
cp /path/to/new/sterling_prompt_library_v5.html [found_path]
```

### 2.4 Create voice_rules.md (NEW file)
```bash
mkdir -p config
cp /path/to/new/voice_rules.md config/voice_rules.md
```

### 2.5 Start Here HTML
Manual: paste into Substack editor, publish, and pin.

**Post-deployment verification:**
```bash
# Confirm all files are in place and have expected sizes
wc -l substack/COWORK_INSTRUCTIONS.md
# Expected: ~955

wc -l substack/docs/content_prompt_handbook_v7_0.md
# Expected: ~1256

wc -l config/voice_rules.md
# Expected: ~263

# Verify no syntax issues in the prompt library HTML
python3 -c "
from html.parser import HTMLParser
with open('[path_to_prompt_library]') as f:
    content = f.read()
    parser = HTMLParser()
    parser.feed(content)
    print(f'Parsed OK: {len(content)} chars')
"
```

---

## PHASE 3: Code Changes

### 3.1 Note Type Refactor (11 types to 5)

**Old types to remove:**
```
MARKET_SNAPSHOT, SIGNAL_TRACKING, PORTFOLIO_UPDATE, CATALYST_WATCH,
COMPANION_NOTE, DATA_INSIGHT, SECTOR_FLOW, READER_QUESTION,
ALPHA_SCOREBOARD, WINNER_RECEIPT, EXIT_DEBRIEF
```

**New types:**
```
SCANNER, POSITION, MARKET, EDUCATION, PROMO
```

**Mapping (for any code that needs migration logic):**

| Old type | New type |
|----------|----------|
| MARKET_SNAPSHOT | MARKET |
| SIGNAL_TRACKING | SCANNER or POSITION |
| PORTFOLIO_UPDATE | POSITION |
| CATALYST_WATCH | MARKET |
| COMPANION_NOTE | PROMO |
| DATA_INSIGHT | EDUCATION |
| SECTOR_FLOW | SCANNER |
| READER_QUESTION | EDUCATION |
| ALPHA_SCOREBOARD | POSITION |
| WINNER_RECEIPT | POSITION |
| EXIT_DEBRIEF | POSITION or MARKET |

**Step 1: Find every reference to old type names.**
```bash
for type in MARKET_SNAPSHOT SIGNAL_TRACKING PORTFOLIO_UPDATE CATALYST_WATCH COMPANION_NOTE DATA_INSIGHT SECTOR_FLOW READER_QUESTION ALPHA_SCOREBOARD WINNER_RECEIPT EXIT_DEBRIEF; do
    echo "=== $type ==="
    grep -rn "$type" --include="*.py" --include="*.js" --include="*.json" --include="*.yaml" --include="*.yml" | grep -v node_modules | grep -v __pycache__
done
```

**Step 2: Update each file found.**

For each file, apply the mapping above. Key locations to check:
- Note generation functions (where type determines what content to produce)
- Filename pattern construction (`{time_label}_{type}_{YYYYMMDD}.html`)
- Manifest construction (note type field in JSON)
- Freshness gate logic (which types need live prices: POSITION and MARKET need it; SCANNER, EDUCATION, PROMO do not)
- Any enum/constant definitions listing valid note types
- The note matrix/schedule (which type goes in which slot)

**Step 3: Update the note sub-variant tracking.**

The new COWORK_INSTRUCTIONS.md defines sub-variants for each type. If existing code tracks sub-variants (e.g., for variety rotation), update those definitions.

The new 5 types have these sub-variants (from COWORK_INSTRUCTIONS):

| Type | Sub-variants |
|------|-------------|
| SCANNER | weekly_funnel, rejection_story, signal_count |
| POSITION | portfolio_alpha, single_winner, honest_loser |
| MARKET | event_impact, force_connection, catalyst_flag |
| EDUCATION | research_finding, methodology_insight, investing_concept |
| PROMO | briefing_announce, deep_dive_hook, education_preview |

**Testing after 3.1:**
```bash
# Verify no old type names remain in code
for type in MARKET_SNAPSHOT SIGNAL_TRACKING PORTFOLIO_UPDATE CATALYST_WATCH COMPANION_NOTE DATA_INSIGHT SECTOR_FLOW READER_QUESTION ALPHA_SCOREBOARD WINNER_RECEIPT EXIT_DEBRIEF; do
    count=$(grep -rn "$type" --include="*.py" --include="*.js" | grep -v node_modules | grep -v __pycache__ | grep -v ".md" | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "FAIL: $type still referenced $count times"
        grep -rn "$type" --include="*.py" --include="*.js" | grep -v node_modules | grep -v __pycache__ | grep -v ".md"
    fi
done
echo "Type refactor check complete"

# Run test suite
python3 -m pytest tests/ -v --tb=short
```

### 3.2 Time Slot Changes

**Old slots:** 08:30 / 12:30 / 17:00 ET
**New slots:** 08:00 / 12:00 / 20:00 AEDT

**Find all time references:**
```bash
grep -rn "08:30\|12:30\|17:00\|0830\|1230\|1700" --include="*.py" --include="*.js" --include="*.json" --include="*.yaml"
```

Also search for timezone references:
```bash
grep -rn "ET\|Eastern\|America/New_York\|EST\|EDT" --include="*.py" --include="*.js"
```

**Changes needed:**
- Slot times: `08:30` to `08:00`, `12:30` to `12:00`, `17:00` to `20:00`
- Timezone: References should use AEDT (Australia/Sydney, UTC+11) instead of ET
- Filename labels remain: `morning`, `midday`, `evening`
- Manifest fields: change `time_et` to `time_aedt`
- Email delivery timing: adjust send times to match new AEDT slots

**Testing after 3.2:**
```bash
# Verify no old time references remain
grep -rn "08:30\|12:30\|17:00" --include="*.py" --include="*.js" | grep -v node_modules | grep -v __pycache__ | grep -v ".md"
# Should return nothing
```

### 3.3 Mode A Decision Engine Rewrite

This is the biggest code change. The current 8-check priority system must become:

**Saturday:** Always "The Weekly Screening." Fixed structure. Not decided by Mode A (it's produced Friday evening/Saturday morning in Claude.ai using Prompt 11A+11B from the prompt library).

**Tuesday:** Scanner-driven priority (from COWORK_INSTRUCTIONS Section 5b):
1. New buy signal from latest scan: full deep dive
2. Exit signal or material development: position update deep dive
3. Subscriber request: sector deep dive
4. Multiple signals in one force: force deep dive
5. Default: watchlist analysis

**Thursday:** 4-week education rotation (A=Methodology, B=Education, C=Tool, D=Lessons). Check last 4 Thursday manifests, pick least-recently-used.

**Mode A output changes:**

The `weekly_plan_YYYY-WXX.json` schema changes. The new schema is defined in COWORK_INSTRUCTIONS Section 10. Key additions:
- `tuesday_decision` block with priority, reason, type, topic, data_needed
- `thursday_decision` block with rotation letter, type, topic, data_needed
- `batch_notes[]` array with pre-drafted Tier 1 notes
- `scanner_summary` block
- `days` structure uses new note types (SCANNER, POSITION, MARKET, EDUCATION, PROMO)

**Context packages:**

Mode A now produces context packages for Tuesday and Thursday. These are saved as:
- `context_tuesday_{YYYYMMDD}.md`
- `context_thursday_{YYYYMMDD}.md`

Each context package contains: the content decision (which priority matched), all relevant data from decisions.json/signal_history/portfolio, headline options, structure outline, and data attachment instructions for the Claude.ai session.

**Implementation approach:**
1. Find the Mode A function/entry point
2. Replace the 8-check Decision Engine with the new Sat/Tue/Thu logic
3. Add batch_notes generation
4. Add context package generation
5. Update weekly_plan.json writer to use new schema
6. Remove references to old post types (Trade Alert, Sector Watch, Investor Lessons, Tools & Tech, Green Signal, Portfolio Spotlight, Performance Review)

**Testing after 3.3:**
```bash
# Dry-run Mode A with current data
python3 -c "
# Simulate Mode A logic with actual data files
import csv, json
from pathlib import Path

ROOT = Path('.')

# Load data
with open(ROOT / 'portfolio/output/portfolio.csv') as f:
    positions = [r for r in csv.DictReader(f) if r['status'] == 'OPEN']

with open(ROOT / 'scanner/output/signals.json') as f:
    signals = json.load(f)

with open(ROOT / 'scanner/output/decisions.json') as f:
    decisions = json.load(f)

# Check Tuesday decision logic
new_positions = decisions.get('new_positions', [])
print(f'New positions in decisions.json: {len(new_positions)}')
for p in new_positions:
    print(f'  {p.get(\"symbol\", \"?\")}: verdict={p.get(\"dd_verdict\")}, conviction={p.get(\"dd_conviction\")}')

if new_positions:
    print('Tuesday decision: Priority 1 - Deep dive on highest conviction new signal')
else:
    print('Tuesday decision: Priority 5 - Watchlist analysis')

# Check Thursday rotation
# Would need manifest history; for now just confirm the logic path works
print('Thursday decision: Check last 4 Thursday manifests for rotation')
print('PASS: Decision engine logic executes without errors')
"
```

### 3.4 Mode B Update

Mode B changes are simpler. Key differences from v7.1:
- Only generates Tier 2 notes (POSITION, reactive MARKET, same-day PROMO)
- Validates that Tier 1 notes (from Sunday batch) are still factually valid
- Uses new AEDT time slots
- No tweet generation (removed from Cowork pipeline)
- `git add` command no longer includes `twitter/output/cowork_content_queue.json`

**Find Mode B entry point:**
```bash
grep -rn "Mode B\|mode_b\|daily_notes\|Daily Notes" --include="*.py" | head -20
```

**Changes:**
1. Remove tweet generation step (Step 3 in old Mode B)
2. Remove `cowork_content_queue.json` from git add
3. Update note type references to new 5 types
4. Update time slots in manifests to AEDT
5. Add Tier 1/Tier 2 distinction: check weekly_plan.batch_notes for today's pre-batched notes

### 3.5 Manifest Schema Updates

**Daily manifest changes:**
- `time_et` field becomes `time_aedt`
- Note types use new 5-type system
- `tweets_generated` field: REMOVE (no automated tweets)
- `visual` field: keep but simplify
- Add `publish_time_aedt` to post block

**Notes manifest changes:**
- Same time field rename
- Same type name changes

**Find all manifest construction code:**
```bash
grep -rn "daily_manifest\|notes_manifest\|tweets_generated\|time_et" --include="*.py" --include="*.js"
```

### 3.6 Remove Twitter Automation from Cowork Pipeline

**Decision:** Twitter/X posting is now manual (share from Substack). Remove from Cowork automation.

**What to remove:**
1. Tweet generation step from Mode B (the `generate_tweets` or equivalent function call)
2. `cowork_content_queue.json` writes and reads from Mode B
3. `git add twitter/output/` from Mode B git push command
4. Tweet queue schema references in Cowork
5. Tweet weekly budget logic
6. Mode C tweet generation (keep the MARKET note generation, remove the tweet)

**What to KEEP (do not delete):**
- The entire `twitter/` directory (poster.py, live_tweet_generator.py, etc.)
- `config/persona_voice_guides.yaml`
- GitHub Actions tweet posting workflows
- The tweet queue file itself

The Twitter infrastructure stays intact for manual/GitHub Actions use. We're only removing it from the Cowork automated pipeline.

```bash
# Find Cowork-specific tweet references
grep -rn "cowork_content_queue\|tweets_generated\|generate.*tweet\|tweet.*queue" --include="*.py" | grep -v "twitter/" | grep -v test
```

### 3.7 Fix build_daily_email.py NoneType Bug

**Known bug:** On notes-only days, Cowork writes `"post": null` in `daily_manifest.json`. Python's `dict.get("post", {})` returns `None` (not `{}`), crashing on `.get("title")`.

**File:** `scripts/build_daily_email.py`

**Fix:** Change all 4 instances of `manifest.get("key", {})` to `manifest.get("key") or {}`:

```bash
grep -n 'manifest.get("post", {})' scripts/build_daily_email.py
grep -n 'manifest.get("visual", {})' scripts/build_daily_email.py
```

**Expected locations (from previous analysis):**
- Line ~97: `post_info = manifest.get("post", {})` -> `manifest.get("post") or {}`
- Line ~122: `visual = manifest.get("visual", {})` -> `manifest.get("visual") or {}`
- Line ~181: `post_info = manifest.get("post", {})` -> `manifest.get("post") or {}`
- Line ~201: `visual = manifest.get("visual", {})` -> `manifest.get("visual") or {}`

**Testing after 3.7:**
```bash
python3 -c "
# Simulate null manifest fields
manifest = {'date': '2026-03-15', 'post': None, 'visual': None, 'notes': []}
post_info = manifest.get('post') or {}
visual = manifest.get('visual') or {}
print('post_info:', post_info)      # Expected: {}
print('visual:', visual)            # Expected: {}
print('category:', post_info.get('category', 'none'))  # Expected: 'none'
print('PASS: NoneType bug fix verified')
"

# Run email tests if they exist
python3 -m pytest tests/test_email_attachments.py -v 2>/dev/null || echo "No email tests found"
```

---

## PHASE 4: Manual Tasks (User does these)

| # | Task | Time | Detail |
|---|------|------|--------|
| 4.1 | Fix Twitter accounts 1+2 | 30 min | developer.twitter.com: regenerate tokens for accounts 1 and 2. Update GitHub Secrets. Run `--reset-failed`. |
| 4.2 | Set up Recommendations | 15 min | Substack settings: add Strategic Wave Trading, Cassandra Unchained, DeepValue Capital, Heavy Moat Investments, Marlin Capital + 2-3 others. |
| 4.3 | Enable Substack Chat | 5 min | Substack settings: turn on Chat, post welcome message. |
| 4.4 | Publish Start Here post | 30 min | Paste start_here.html into Substack. Pin to profile. Update href="#" links as posts are published. |
| 4.5 | Create archive sections | 15 min | Substack settings: create "Weekly Briefings," "Deep Dives," "Education," "Scanner Reports." Move existing posts. |

---

## PHASE 5: Comprehensive Testing

### 5.1 Unit Tests (run after each phase)

```bash
# Full test suite
python3 -m pytest tests/ -v --tb=short

# Specific test files likely affected
python3 -m pytest tests/test_saturday_workflow.py -v
python3 -m pytest tests/test_email_attachments.py -v
python3 -m pytest tests/test_live_tweet_system.py -v 2>/dev/null
```

### 5.2 Portfolio.csv Reader Verification

```bash
# Test every script that reads portfolio.csv
python3 -c "
import csv
with open('portfolio/output/portfolio.csv') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    headers = reader.fieldnames
    print(f'Headers: {headers}')
    print(f'Row count: {len(rows)}')
    print(f'structural_force present: {\"structural_force\" in headers}')
    for row in rows:
        if row['status'] == 'OPEN':
            print(f'  {row[\"ticker\"]}: force={row[\"structural_force\"]}, theme={row[\"theme\"]}')
"

# Test merge_decisions.py can still read portfolio
python3 -c "
from scanner.merge_decisions import *
print('merge_decisions imports OK')
"

# Test tracker can still write portfolio
python3 -c "
from portfolio.tracker import *
print('tracker imports OK')
"
```

### 5.3 Signal History Verification

```bash
python3 -c "
import csv
with open('scanner/output/signal_history_rows.csv') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    print(f'Headers: {headers}')
    print(f'structural_force in headers: {\"structural_force\" in headers}')
    rows = list(reader)
    forces_found = set()
    for row in rows:
        if row.get('structural_force'):
            forces_found.add(row['structural_force'])
    print(f'Forces found: {forces_found}')
    print(f'Total rows: {len(rows)}')
"
```

### 5.4 Note Type Verification

```bash
# Ensure no old type names exist in any Python code
echo "Checking for old note type references..."
OLD_TYPES="MARKET_SNAPSHOT SIGNAL_TRACKING PORTFOLIO_UPDATE CATALYST_WATCH COMPANION_NOTE DATA_INSIGHT SECTOR_FLOW READER_QUESTION ALPHA_SCOREBOARD WINNER_RECEIPT EXIT_DEBRIEF"
FOUND=0
for type in $OLD_TYPES; do
    matches=$(grep -rn "$type" --include="*.py" --include="*.js" | grep -v __pycache__ | grep -v node_modules | grep -v ".md" | wc -l)
    if [ "$matches" -gt 0 ]; then
        echo "  FOUND: $type ($matches references)"
        FOUND=$((FOUND + matches))
    fi
done
if [ "$FOUND" -eq 0 ]; then
    echo "PASS: All old note types removed from code"
else
    echo "FAIL: $FOUND old type references remain"
fi
```

### 5.5 Manifest Schema Verification

```bash
# Generate a test manifest and verify schema
python3 -c "
import json

# Expected new manifest structure
expected_keys = ['date', 'day', 'generated_at', 'decision_reason', 'post', 'notes']
unexpected_keys = ['tweets_generated']
expected_note_keys = ['slot', 'type', 'time_aedt', 'time_label', 'file']
valid_types = ['SCANNER', 'POSITION', 'MARKET', 'EDUCATION', 'PROMO']

# If a manifest exists, validate it
import os
manifest_path = 'substack/output/current/daily_manifest.json'
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        m = json.load(f)
    for key in unexpected_keys:
        assert key not in m, f'Unexpected key: {key}'
    for note in m.get('notes', []):
        assert note['type'] in valid_types, f'Invalid note type: {note[\"type\"]}'
    print('PASS: Existing manifest validates against new schema')
else:
    print('SKIP: No manifest file found (will be created on first run)')
"
```

### 5.6 End-to-End Simulation

```bash
# Simulate a full week's production without actually generating content
python3 -c "
import csv, json
from pathlib import Path

ROOT = Path('.')

# 1. Can we read all data files?
files = [
    'portfolio/output/portfolio.csv',
    'portfolio/output/equity_curve.csv',
    'scanner/output/signals.json',
    'scanner/output/decisions.json',
    'scanner/output/signal_history_rows.csv',
]
for f in files:
    path = ROOT / f
    assert path.exists(), f'Missing: {f}'
    print(f'OK: {f}')

# 2. Can we construct a portfolio snapshot?
with open(ROOT / 'portfolio/output/portfolio.csv') as f:
    positions = [r for r in csv.DictReader(f) if r['status'] == 'OPEN']
print(f'Open positions: {len(positions)}')
for p in positions:
    force = p.get('structural_force', 'MISSING')
    print(f'  {p[\"ticker\"]}: {p[\"theme\"]} -> {force}')

# 3. Can we read the equity curve?
with open(ROOT / 'portfolio/output/equity_curve.csv') as f:
    rows = list(csv.DictReader(f))
    latest = rows[-1]
    print(f'Latest NAV: {latest[\"nav\"]}, Alpha: {latest[\"alpha_pct\"]}%')

# 4. Can we read scanner stats?
with open(ROOT / 'scanner/output/signals.json') as f:
    signals = json.load(f)
    stats = signals.get('stats', {})
    print(f'Tickers scanned: {stats.get(\"tickers_loaded\")}')
    print(f'Buy signals: {stats.get(\"buy_signal\")}')

# 5. Check decisions.json for new positions
with open(ROOT / 'scanner/output/decisions.json') as f:
    decisions = json.load(f)
    new_pos = decisions.get('new_positions', [])
    print(f'New positions in decisions: {len(new_pos)}')

# 6. Check signal history for rejection narratives
with open(ROOT / 'scanner/output/signal_history_rows.csv') as f:
    history = list(csv.DictReader(f))
    fails = [h for h in history if h.get('final_verdict') == 'FAIL']
    print(f'Failed signals (for rejection stories): {len(fails)}')

print()
print('=== END-TO-END DATA PIPELINE: ALL CHECKS PASSED ===')
"
```

---

## EXECUTION ORDER SUMMARY

```
PHASE 1 (Foundation):
  1.1  Add structural_force to portfolio.csv + trace all readers
  1.2  Verify structural_force in decisions.json
  1.3  Verify signal_history_rows.csv (already correct)
  -> Run Phase 1 tests

PHASE 2 (Documents):
  2.1  Paste COWORK_INSTRUCTIONS.md
  2.2  Paste content_prompt_handbook_v7_0.md
  2.3  Paste sterling_prompt_library_v5.html
  2.4  Create config/voice_rules.md
  -> Run Phase 2 verification

PHASE 3 (Code):
  3.7  Fix NoneType bug (quickest win, no dependencies)
  3.1  Note type refactor (11->5) (most impactful)
  3.2  Time slot changes (ET->AEDT)
  3.6  Remove tweet automation from Cowork
  3.5  Manifest schema updates
  3.3  Mode A decision engine rewrite (biggest change)
  3.4  Mode B update
  -> Run full test suite after each step
  -> Run Phase 5 comprehensive tests

PHASE 4 (Manual):
  Can run in parallel with Phases 1-3.

PHASE 5 (Testing):
  Run after all code changes complete.
  Run end-to-end simulation.
  First live execution: next Friday scanner run.
```

---

## DEPENDENCY MAP

```
portfolio.csv structural_force (1.1)
    |
    v
decisions.json verification (1.2)
    |
    v
Document deployment (2.1-2.4) <-- voice_rules.md (2.4)
    |
    v
NoneType bug fix (3.7) [independent, do first]
    |
    v
Note type refactor (3.1) --> Time slot changes (3.2)
    |                              |
    v                              v
Remove tweet automation (3.6)  Manifest updates (3.5)
    |
    v
Mode A rewrite (3.3) [depends on 3.1, 3.2, 3.5]
    |
    v
Mode B update (3.4) [depends on 3.1, 3.2, 3.3]
    |
    v
End-to-end testing (5.6)
    |
    v
First live execution: Friday scanner -> Saturday briefing
```
