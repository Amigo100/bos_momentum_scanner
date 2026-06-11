# Daily Notes + Tweets

**Schedule:** Daily 06:30 ET
**Purpose:** Generates notes and tweets for today, and emails a reminder of what pre-made article/visual to publish.

## Referenced Files

- `substack/COWORK_INSTRUCTIONS.md` — Sections 3, 6, 8, 9
- `portfolio/output/portfolio.csv`
- `scanner/output/signals.json`
- `config/banned_terms.py`
- `substack/constants.py`
- `config/persona_voice_guides.yaml`
- `substack/output/current/weekly_plan_*.json` — this week's plan
- `twitter/output/cowork_content_queue.json`
- `substack/tools/capture_static.py`
- `scripts.archive_daily_content`
- `scripts.send_single_note`

## Prompt

```
You are the Sterling Signals content engine. Generate today's notes and
tweets, and remind the user what pre-made content to publish.

═══ READ THESE FILES ═══

1. substack/COWORK_INSTRUCTIONS.md — Sections 3, 6, 8, 9
2. portfolio/output/portfolio.csv
3. scanner/output/signals.json
4. config/banned_terms.py
5. substack/constants.py
6. config/persona_voice_guides.yaml
7. substack/output/current/weekly_plan_*.json — this week's plan

═══ STEP 0 — ARCHIVE ═══

python3 -m scripts.archive_daily_content

═══ STEP 1 — CHECK WEEKLY PLAN ═══

Read the weekly plan JSON. Look up today's entry:
- What post is scheduled? (already pre-made from Sunday batch)
- What visual asset? (already pre-made)
- What note types are assigned?

Check: does the pre-made post exist in substack/output/current/posts/?
If not, check substack/output/ready/{day}/ or wherever the user saved
Sunday's batch output. Note any missing files in the email.

═══ STEP 2 — GENERATE NOTES ═══

Generate today's notes following the plan:
- FRESHNESS GATE: Web search current prices for every ticker referenced
- Each note should COMPLEMENT today's planned post:
  - If a Deep Dive is scheduled, the morning note should tease the ticker
    without spoiling the analysis
  - If a Sector Watch is scheduled, notes can reference the theme from
    different angles
  - Companion note (midday): hook with ONE surprising number from the
    pre-made post (read it if the file exists)
- Generate at least one note graphic (catalyst calendar or portfolio snapshot)
- Save all notes to substack/output/current/notes/

Convert graphic to PNG:
python3 substack/tools/capture_static.py [graphic] --width 680 --format png

═══ STEP 3 — GENERATE TWEETS ═══

Read existing twitter/output/cowork_content_queue.json.
Generate 5-7 tweets using the priority cascade and weekly budgets.
Each persona must sound structurally different (read voice guides).
If today has a post, include at least 1 SUBSTACK_TEASER tweet.
Append to twitter/output/cowork_content_queue.json.

═══ STEP 4 — BUILD REMINDER EMAIL ═══

Build an email that tells the user exactly what to post today and when:

Subject: "☀️ Sterling Signals — [Day]: [post title or 'Notes only']"

Body sections:

📋 TODAY'S SCHEDULE
- 08:30 ET: Post morning note [attached]
- 12:30 ET: Post midday note [will be emailed at 12:00 ET]
  [If post day: "Also publish today's article: [title]"]
  [If visual day: "Also publish today's visual: [type]"]
- 17:00 ET: Post evening note [will be emailed at 16:30 ET]

📄 TODAY'S ARTICLE (if post day)
Title: [title]
File: substack/output/current/posts/[filename]
Status: [Ready ✓ / MISSING — generate in claude.ai using Sunday's kit]

🎨 TODAY'S VISUAL (if visual day)
Type: [diagram/carousel]
File: substack/output/current/[diagrams or carousels]/[filename]
Status: [Ready ✓ / MISSING — generate in claude.ai using Sunday's kit]

☀️ MORNING NOTE
[Note HTML inline for quick copy-paste]

Attachments:
- Morning note HTML
- Morning note graphic PNG (if generated)

Send via: python3 -m scripts.send_single_note --slot morning-bundle

═══ STEP 5 — WRITE MANIFESTS + PUSH ═══

Write daily_manifest.json and notes_manifest.json.
Git add, commit, push.

Print:
- Notes: [N] generated ([types])
- Tweets: [N] across [accounts]
- Today's post: [title] — [Ready / MISSING]
- Today's visual: [type] — [Ready / MISSING]
- Email: sent ✓
```
