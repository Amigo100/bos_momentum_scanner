# Weekly Planner

**Schedule:** Sunday 06:30 ET
**Purpose:** Reads all data, plans the entire week, prints the plan and all prompt kits inline so you can copy them into claude.ai.

## Referenced Files

- `substack/COWORK_INSTRUCTIONS.md` — Sections 3, 4, 5
- `substack/docs/content_prompt_handbook_v6.2.md` — full document
- `portfolio/output/portfolio.csv`
- `scanner/output/signals.json`
- `portfolio/output/equity_curve.csv`
- `config/banned_terms.py`
- `substack/constants.py` — NOTE_TYPE_MATRIX v4
- `substack/docs/animated-diagram-spec.md`
- `substack/docs/carousel-guide.docx`
- `substack/output/archive/` — recent manifests for duplicate prevention

## Prompt

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
7. substack/constants.py — NOTE_TYPE_MATRIX v4

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
NOTE_TYPE_MATRIX v4 that COMPLEMENT that day's post:

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
