# Sterling Signals — Final Content Architecture

## How It Works

**Sunday:** Cowork plans the whole week — what posts, what tickers, what
visuals, what days. Prints everything inline. You go into claude.ai and
produce all heavy content (posts + diagrams + carousels) in one session,
maybe two. Save to repo, push.

**Daily:** Cowork generates notes (2-3/day) and tweets (5-7/day) that
are designed to complement that day's planned post. Emails you the notes
at posting time plus a reminder of which article/visual to publish.

**Weekdays 11:30 ET:** Cowork scans portfolio holdings for 24h developments.
If something material happened, generates a note + tweet.

**You do:** Paste notes into Substack when emailed. Paste the pre-made
article/visual from your Sunday batch when reminded. That's it.

---

## Scheduled Tasks (4 total)

| # | Task | Schedule | Automated? |
|---|------|----------|------------|
| 1 | Weekly Planner | Sunday 06:30 ET | Prints plan — you produce heavy content in chat |
| 2 | Daily Notes + Tweets | Daily 06:30 ET | Fully automated |
| 3 | Portfolio Scanner | Weekdays 11:30 ET | Fully automated |
| 4 | Watchdog | Daily 08:00 ET (GitHub Actions) | Fully automated |

---

## TASK 1 — Weekly Planner (Sunday 06:30 ET)

**What it does:** Reads all data, plans the entire week, prints the plan
and all prompt kits inline so you can copy them into claude.ai.

**What you do after:** Open claude.ai. Produce all posts, diagrams, and
carousels in one or two focused sessions. Save everything to the repo.
You now have a week's worth of heavy content ready to publish on schedule.

### Prompt:

```
You are the Sterling Signals content engine. Plan the entire upcoming
week's content and prepare prompt kits for all heavy content.

═══ READ THESE FILES ═══

1. substack/COWORK_INSTRUCTIONS.md — Sections 3, 4, 5
2. substack/docs/content_prompt_handbook_v6.2.md — FULL document
3. portfolio/output/portfolio.csv
4. scanner/output/signals.json
5. portfolio/output/equity_curve.csv
6. config/banned_terms.py
7. substack/constants.py — NOTE_TYPE_MATRIX v3

═══ STEP 1 — GATHER CONTEXT ═══

Web search current prices for ALL open portfolio positions. Recalculate
P&L from entry prices. Note any positions that moved significantly
(>5%) since the CSV was last updated.

Web search for: SPY, QQQ, IWM current + YTD. VIX. Major upcoming events
this week (earnings for portfolio tickers, Fed, economic data, sector
catalysts).

Read recent manifests from substack/output/archive/ for duplicate prevention.

═══ STEP 2 — PLAN THE WEEK ═══

Determine what content to produce each day. Follow the Content Decision
Engine (Section 4) but plan all days at once:

TUESDAY: Deep Dive — [Ticker] — [Reasoning]
WEDNESDAY: Sector Watch — [Theme] — [Reasoning]
THURSDAY: The Edge OR Deep Dive #2 — [Topic/Ticker] — [Reasoning]
FRIDAY: Investor Lessons — [Subcategory: case_study / legendary_investor /
  investing_principle / market_mechanics / behavioural_finance] — [Topic]
SATURDAY: Tools & Tech — [Tool or tool category] — [Topic]

For Investor Lessons (Friday), rotate subcategories:
- Check the last 4 Fridays' subcategories from archived manifests
- Pick the least-recently-used subcategory
- Priority: portfolio-connected topics first, then market events,
  then classic studies. Every post MUST connect to our portfolio.

For Tools & Tech (Saturday), rotate subcategories:
- Check the last 4 Saturdays from archived manifests
- Pick a different tool category each time
- The tool MUST be demonstrated on a real portfolio ticker
- Free tools preferred over paid (audience resonance)

For each post, also plan the visual asset:
TUESDAY: Animated diagram for [ticker]
WEDNESDAY: Carousel on [theme]
THURSDAY: Animated diagram for [ticker/topic]
FRIDAY: Carousel on [lesson principle/case study]
SATURDAY: Carousel on [tool walkthrough/comparison]

Apply all duplicate prevention rules:
- No ticker covered by Deep Dive in the last 21 days
- No theme covered by Sector Watch in the last 14 days
- If a signal was announced Saturday but already had a GREEN Signal post, skip
- Thursday checks if any signal still needs a Deep Dive

═══ STEP 3 — NOTE PLANNING ═══

Plan the full week's notes. For each day, assign note types from the
NOTE_TYPE_MATRIX v3 that COMPLEMENT that day's post:

- Tuesday notes should tease or set up the Deep Dive without spoiling it
- Wednesday morning note can preview the Sector Watch theme
- Thursday evening note can reflect on The Edge's educational insight
- Notes-only days (Mon/Fri/Sun) should maintain audience engagement
  with portfolio updates, data insights, and reader questions

Print the full week's note schedule:

| Day | Slot 1 (08:30) | Slot 2 (12:30) | Slot 3 (17:00) |
|-----|----------------|----------------|-----------------|
| Monday | [type] | [type] | [type] |
| Tuesday | [type — complements post] | COMPANION NOTE | [type] |
| ... | ... | ... | ... |

═══ STEP 4 — PROMPT KITS (print inline) ═══

For EACH post and visual asset, print the complete prompt kit. Do NOT
abbreviate the prompts — extract them in full from the handbook.

For each kit, print:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TUESDAY — Deep Dive: $TICKER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH IN CLAUDE.AI:
- content_prompt_handbook_v6.2.md
- config/banned_terms.py

PORTFOLIO CONTEXT (paste this at the start of your chat):
$TICKER1: entry $X, current $Y (+Z%), theme: [name]
$TICKER2: entry $X, current $Y (+Z%), theme: [name]
[... all open positions with LIVE prices from your web search ...]

PROMPT 1 OF 3 — RESEARCH:
[Full prompt text from handbook, pre-filled with today's ticker,
entry price, current price, theme, newsletter context]

PROMPT 2 OF 3 — ANALYSIS:
[Full prompt text from handbook]

PROMPT 3 OF 3 — WRITE:
[Full prompt text from handbook]

DIAGRAM PROMPT (separate claude.ai chat):
Attach: animated-diagram-spec.md + substack/docs/aspi-v7.html
"Read the attached spec and reference diagram. Web search for $TICKER
business model: revenue segments, key metrics, strategic pipeline,
flywheel dynamics. Generate an animated business model diagram."

SAVE TO:
- Post: substack/output/current/posts/deep_dive_{YYYYMMDD}.html
- Companion note: substack/output/current/notes/midday_companion_note_{YYYYMMDD}.html
- Diagram: substack/output/current/diagrams/diagram_{ticker}_{YYYYMMDD}.html

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEDNESDAY — Sector Watch: [Theme]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Same format — full prompts from handbook Section 5d, files to attach,
save to posts/sector_watch_{YYYYMMDD}.html, carousel prompt included]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THURSDAY — The Edge / Deep Dive: [Topic/Ticker]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Same format — handbook Section 5e for Edge or 5c for DD #2, diagram prompt]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRIDAY — Investor Lessons: [Topic]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH: content_prompt_handbook_v6.2.md + banned_terms.py

PORTFOLIO CONTEXT: [all positions with LIVE prices]

PROMPT 1 OF 3 — DISCOVER TOPIC:
[Full prompt from handbook Section 5g — subcategory rotation,
portfolio connection candidates, 2-3 topic options with recommendation]

PROMPT 2 OF 3 — RESEARCH:
[Full prompt — original sources, specific numbers, counter-arguments,
portfolio ticker illustration, surprising stat]

PROMPT 3 OF 3 — WRITE:
[Full prompt — article 800-1,200 words: Hook → Story → Evidence →
In Our Portfolio (REQUIRED — name ticker, entry, outcome) → Exception →
Takeaway → Footer. Title: "Investor Lessons: [Topic]"]

COMPANION NOTE: Lead with most surprising stat from the lesson.
"Druckenmiller once put 100% of his fund in one trade. We cap at 5 positions.
Here's why both approaches work." Max ONE insight. Do not summarise.

CAROUSEL PROMPT (separate chat — attach carousel-guide.docx):
"Produce a 5-slide INVESTOR TOOLKIT carousel on [TOPIC]:
Slide 1: Principle + hook stat (dark)
Slide 2: The story explained simply (light)
Slide 3: Key numbers (stat cards, light)
Slide 4: Right vs wrong approach (two-column, light)
Slide 5: The takeaway (dark)"

SAVE TO:
- Post: substack/output/current/posts/investor_lessons_{YYYYMMDD}.html
- Companion: substack/output/current/notes/midday_companion_note_{YYYYMMDD}.html
- Carousel: substack/output/current/carousels/carousel_lesson_{YYYYMMDD}.pptx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SATURDAY — Tools & Tech: [Tool Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES TO ATTACH: content_prompt_handbook_v6.2.md + banned_terms.py

PORTFOLIO CONTEXT: [all positions with LIVE prices]

PROMPT 1 OF 2 — RESEARCH & TEST:
[Full prompt from handbook Section 5h — tool name, pricing, free tier,
specific workflow demonstrated on 1-2 portfolio tickers, limitations]

PROMPT 2 OF 2 — WRITE:
[Full prompt — article 600-1,000 words: Problem → Tool → How We Use It
(demo on $TICKER from portfolio) → What It Found → Limitations →
Setup Guide (3-5 steps) → Footer. Title: "Tools & Tech: [Tool] — [Hook]"]

COMPANION NOTE: Lead with what the tool found on our ticker.
"I ran $LUNR through Finviz. It flagged 3 things our scanner missed.
Here's what free tools can do." Max ONE finding. Do not summarise.

CAROUSEL PROMPT (separate chat — attach carousel-guide.docx):
"Produce a 5-slide INVESTOR TOOLKIT carousel on [TOOL]:
Slide 1: Tool name + the problem it solves (dark)
Slide 2: What it does in plain English (light)
Slide 3: Live demo on our ticker — what it found (stat cards, light)
Slide 4: Free vs paid / limitations (two-column, light)
Slide 5: 3-step setup + Sterling Signals verdict (dark)"

SAVE TO:
- Post: substack/output/current/posts/tools_and_tech_{YYYYMMDD}.html
- Companion: substack/output/current/notes/midday_companion_note_{YYYYMMDD}.html
- Carousel: substack/output/current/carousels/carousel_tools_{YYYYMMDD}.pptx

═══ STEP 5 — SAVE WEEKLY PLAN ═══

Save the complete plan to: substack/output/current/weekly_plan_{YYYY_WXX}.json

Schema:
{
    "week": "2026-W12",
    "planned_at": "2026-03-15T06:30:00-04:00",
    "portfolio_snapshot": {
        "positions": [...],
        "total_return": "...",
        "spy_ytd": "...",
        "qqq_ytd": "..."
    },
    "days": {
        "monday": {"post": null, "visual": null, "notes": ["MARKET_SNAPSHOT", "SIGNAL_TRACKING", "PORTFOLIO_UPDATE"]},
        "tuesday": {"post": {"type": "deep_dive", "ticker": "ASTS", "title": "..."}, "visual": {"type": "diagram", "ticker": "ASTS"}, "notes": ["CATALYST_WATCH", "COMPANION_NOTE", "DATA_INSIGHT"]},
        "wednesday": {"post": {"type": "sector_watch", "theme": "Defence Technology", "score": 8.4}, "visual": {"type": "carousel", "topic": "..."}, "notes": ["SECTOR_FLOW", "COMPANION_NOTE", "CATALYST_WATCH"]},
        "thursday": {"post": {"type": "the_edge", "topic": "..."}, "visual": {"type": "diagram", "ticker": "..."}, "notes": ["SIGNAL_TRACKING", "COMPANION_NOTE", "READER_QUESTION"]},
        "friday": {"post": null, "visual": null, "notes": ["SIGNAL_TRACKING", "PORTFOLIO_UPDATE", "EXIT_DEBRIEF"]},
        "saturday": {"post": null, "visual": null, "notes": ["ALPHA_SCOREBOARD", "WINNER_RECEIPT"]},
        "sunday": {"post": null, "visual": null, "notes": ["DATA_INSIGHT", "READER_QUESTION"]}
    }
}

Also save the full prompt kits to: substack/output/current/weekly_prompt_kits_{YYYY_WXX}.md

Git add, commit, push.

═══ SUMMARY ═══

Print:
- Week [N] plan complete
- Posts planned: [N] — [list of types and tickers]
- Visual assets: [N] — [list]
- Notes planned: [total across week]
- Prompt kits: saved to weekly_prompt_kits file
- Weekly plan JSON: saved
```

---

## TASK 2 — Daily Notes + Tweets (Daily 06:30 ET)

**What it does:** Generates notes and tweets for today, and emails you
a reminder of what pre-made article/visual to publish.

**What you do:** Paste notes into Substack. Paste the pre-made article
(from your Sunday batch) into Substack when reminded.

### Prompt:

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

---

## TASK 3 — Portfolio Developments Scanner (Weekdays 11:30 ET)

**Unchanged from the previous version.** Scans every holding for 24h news,
generates note + tweet if material, emails you, auto-queues tweet.

### Prompt:

```
You are the Sterling Signals content engine. Scan portfolio holdings for
material developments in the last 24 hours.

═══ READ THESE FILES ═══

1. portfolio/output/portfolio.csv — all open positions
2. config/banned_terms.py — terms to NEVER use

═══ STEP 1 — SCAN EVERY HOLDING ═══

Read all OPEN positions from portfolio.csv. For EACH ticker, web search:
"$TICKER stock news today" and "$TICKER [company name] latest"

Look for material developments from the LAST 24 HOURS ONLY:
- Earnings releases or guidance updates
- FDA decisions, regulatory rulings, approvals
- Major contract wins or partnership announcements
- Analyst upgrades/downgrades with price target changes
- Insider buying/selling (Form 4 filings)
- Significant price moves (>5% in a day)
- Industry/sector catalysts affecting the position
- M&A activity, tender offers, or strategic reviews

Classify each: MATERIAL / MINOR / NONE

═══ STEP 2 — DECIDE ═══

If NO tickers have MATERIAL developments:
  Print "PORTFOLIO SCAN: No material developments in last 24h" and stop.

If 1+ MATERIAL developments: continue.

═══ STEP 3 — GENERATE NOTE + TWEET ═══

NOTE (150-280 words HTML):
- Lead with the most impactful development
- Cover each material ticker: what happened, what it means, our position
- End with what we're watching next
- Footer: "Not financial advice. Informational only."

Save to: substack/output/current/notes/midday_portfolio_developments_{YYYYMMDD}.html

TWEET (variant_1 voice — data-driven, max 280 chars):
- "$TICKER: [what happened]. [impact]. Entry $X. NFA"
Append to twitter/output/cowork_content_queue.json with source: "cowork"

═══ STEP 4 — DELIVER ═══

Git add, commit, push.
Email the note:
python3 -m scripts.send_single_note --file [note_path] --subject "⚡ Sterling Signals — $TICKER: [headline]"
```

---

## TASK 4 — Watchdog (GitHub Actions, 08:00 ET)

**Already built in v3.2.** No changes needed.

---

## Your Weekly Routine

### Sunday Evening (~21:30 AEDT / 06:30 ET)

1. **Weekly plan email arrives** from Task 1
2. Read the plan: what posts, what tickers, what visuals
3. Open claude.ai chat (or two — one for posts, one for visuals)
4. **Produce all heavy content** using the prompt kits:
   - Paste portfolio context + Prompt 1 → wait → Prompt 2 → wait → Prompt 3
   - Repeat for each post (typically 3: Tue Deep Dive, Wed Sector Watch, Thu Edge/DD)
   - Open a separate chat for diagrams: attach spec + reference, paste prompt
   - Open a separate chat for carousels: attach guide, paste prompt
5. Save all outputs to the repo, git push
6. **Time:** 60-90 minutes for a full week's content

### Monday–Saturday Mornings (~21:30 AEDT / 06:30 ET)

1. **Daily email arrives** from Task 2 with:
   - Morning note (ready to paste)
   - Reminder of what article/visual to publish today
   - Whether the files are ready or missing
2. **Paste morning note** into Substack Notes (1 min)
3. **If post day:** Open the pre-made article HTML, paste into Substack (2 min)
4. **If visual day:** Upload the pre-made diagram MP4 or carousel PPTX (2 min)

### Throughout Day

- **Midday:** Task 2 emails the midday note at 12:00 ET → paste when convenient
- **Evening:** Task 2 generates + emails evening note at 16:30 ET → paste
- **Portfolio alert:** Task 3 emails if something moved → paste the note
- **Tweets:** Auto-posted all day by GitHub Actions

### Time Budget

| Activity | When | Time |
|----------|------|------|
| Sunday batch: all posts + visuals | Sunday evening | 60-90 min |
| Daily note pasting (3/day × 7) | Throughout week | 21 min total |
| Article/visual publishing (3-4/week) | Morning of post day | 8 min total |
| Portfolio development notes | Ad-hoc weekdays | 5 min total |
| **Weekly total** | | **~100 min** |

---

## What Changes If Signals Break Mid-Week

If a new GREEN signal appears on Tuesday (scanner ran Friday, you made
decisions Saturday, but a new signal fires from the analysis session):

**The weekly plan becomes stale for that day.** The planned Tuesday Deep
Dive might need to switch to a GREEN Signal post.

**How to handle:** Task 2 (daily notes/tweets) reads the weekly plan but
also reads signals.json. If it detects a new signal that wasn't in the
plan, the email should flag: "⚠️ NEW SIGNAL: $TICKER — consider replacing
today's planned content with a GREEN Signal post. Prompt kit for trade
alerts is in the handbook Section 5a."

This way you're alerted but not locked into a stale plan.

---

## Files the Sunday Batch Produces

After your Sunday claude.ai session, the repo should contain:

```
substack/output/current/
├── posts/
│   ├── deep_dive_20260317.html          (Tuesday)
│   ├── sector_watch_20260318.html       (Wednesday)
│   └── the_edge_20260319.html           (Thursday)
├── notes/
│   ├── midday_companion_note_20260317.html  (Tuesday companion)
│   ├── midday_companion_note_20260318.html  (Wednesday companion)
│   └── midday_companion_note_20260319.html  (Thursday companion)
├── diagrams/
│   ├── diagram_asts_20260317.html       (Tuesday)
│   └── diagram_rcat_20260319.html       (Thursday)
├── carousels/
│   └── carousel_defence_20260318.pptx   (Wednesday)
├── weekly_plan_2026-W12.json
└── weekly_prompt_kits_2026-W12.md
```

Task 2 reads the weekly plan each morning to know what exists and what
to remind you about.
