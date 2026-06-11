# Substack Content Subsystem — Required Changes Specification
## Sterling Signals Architecture Optimisation

**Date:** 2026-02-25
**Scope:** All files under `substack/`, daily content GitHub Action, email notifications, content schedule logic
**Status:** Pre-implementation — all changes must be validated before first live week
**Companion:** `SCANNER_SUBSYSTEM_CHANGES.md` (upstream dependency — implement first)

---

## TABLE OF CONTENTS

1. [Design Decisions](#1-design-decisions)
2. [Architecture Overview](#2-architecture-overview)
3. [Content Calendar](#3-content-calendar)
4. [New Module: daily_content_pipeline.py](#4-daily_content_pipelinepy)
5. [New Module: content_utils.py (Extract from content_generator.py)](#5-content_utilspy)
6. [Refactor: notes generation (daily, live context)](#6-notes-generation)
7. [Refactor: content_production_guide.py → daily_context_builder.py](#7-daily_context_builderpy)
8. [Simplify: newsletter_compiler.py](#8-newsletter_compilerpy)
9. [Keep As-Is Modules](#9-keep-as-is-modules)
10. [File Deletions & Deprecations](#10-file-deletions)
11. [New GitHub Action: daily_content.yml](#11-github-action)
12. [Email Notification System](#12-email-notifications)
13. [Data Flow & Field Dependencies](#13-data-flow)
14. [Deferred Items Resolution (from Scanner Spec)](#14-deferred-items-resolution)
15. [Implementation Order](#15-implementation-order)
16. [Testing Checklist](#16-testing-checklist)
17. [Content Quality Standards](#17-content-quality-standards)

---

## 1. DESIGN DECISIONS

### 1.1 Two-Track Content Model

| Track | Content | Generation | Publishing | Human Effort |
|-------|---------|------------|------------|--------------|
| **Notes** | 2-3 short posts/day, live market context | Automated (daily GitHub Action, Sonnet) | Files generated + email notification → manual paste to Substack | ~2 min/day |
| **Long-form posts** | 3-4 articles/week, deep analysis | Human-in-chat (Claude.ai Opus 4.6 + extended thinking) | Manual paste to Substack | ~5-10 min/post |

**Rationale:** Notes benefit from timeliness (live prices, fresh market data) and tolerate Sonnet-quality writing. Long-form posts are the product — they must be Opus-quality with human oversight. Mixing these into one pipeline would degrade the posts without improving the notes.

### 1.2 Daily Context Document

Instead of generating posts automatically, the system generates a **daily context document** that contains everything needed for manual chat generation:
- Today's assigned post category and topic
- The exact prompt to paste (from handbook v5)
- Fresh market data (generated that morning)
- All relevant signal/portfolio/theme data for today's topic
- Event override flags (new milestones, significant market moves)

This document is committed to the repo and emailed as a summary each morning. The human opens Claude.ai, attaches the file, pastes the prompt, gets HTML back. Total manual effort: 5-10 minutes per post.

### 1.3 Saturday Chat Session — Unchanged

The 7-prompt Saturday session (sterling_prompt_library.md) remains exactly as-is. Quality of ticker analysis and output files is the top priority. No consolidation unless proven to produce identical or better output. This is flagged as a future optimisation only.

### 1.4 Notes Publishing — Manual with Email Notification

Notes are generated as HTML files and emailed to you each morning with a summary. You paste them into Substack (~2 min). This is more reliable than the session-cookie API approach and avoids the fragility of reverse-engineered authentication. Auto-publishing via API is a future upgrade path once a stable method is available.

### 1.5 Substack Post Archiving

All generated content (notes + context docs) follows the existing dual-write pattern: save to `substack/output/current/` and `substack/output/archive/YYYY-WXX/`. Long-form posts created in chat are archived via `newsletter_compiler.py --from-html` (kept for this purpose).

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 New Pipeline Flow

```
FRIDAY 16:15 ET — Scanner runs (unchanged)
├── signals_technical.json
├── portfolio.csv (updated)
├── equity_curve.csv (updated)
└── friday_scan.yml triggers downstream content steps:
    ├── portfolio_visual.py → dashboard HTML + PNG
    ├── dd_post_generator.py → DD HTML per signal
    └── Commit all outputs

SATURDAY MORNING — Chat session (unchanged, 30-45 min)
├── 7 prompts from sterling_prompt_library.md
├── Output: decisions.json, newsletter.html, DD posts
└── Run saturday_workflow.py → merge → signals.json (canonical)

DAILY 07:00 ET — daily_content.yml (NEW)
├── Step 1: Fetch live prices + index performance
├── Step 2: market_analyzer.py → fresh market_analysis.md
├── Step 3: daily_context_builder.py
│   ├── Reads: signals.json, portfolio.csv, equity_curve.csv,
│   │         market_analysis.md, archive history
│   ├── Determines: today's post category + topic
│   ├── Detects: event overrides (new milestones, big market moves)
│   ├── Builds: daily_context.md with embedded prompt
│   └── Builds: daily_notes_context.json (live data for notes)
├── Step 4: daily_notes_generator.py
│   ├── Reads: daily_notes_context.json
│   ├── Generates: 2-3 HTML notes with live market data
│   ├── Validates: banned terms, format, quality
│   └── Saves: HTML files to current/ + archive/
├── Step 5: Email notification
│   ├── Subject: "Sterling Signals — [Day]: [Post Topic]"
│   ├── Body: Today's post topic + category, note summaries,
│   │         portfolio snapshot, market context summary
│   ├── Attachments: daily_context.md + note HTML files
│   └── Uses: existing email_notifier.py infrastructure
└── Step 6: Commit all outputs to repo

YOU (5-10 min on post days, 2 min on non-post days)
├── Check email
├── On post days: Open Claude.ai → attach daily_context.md → paste prompt → get HTML → paste to Substack
├── On all days: Paste 2-3 note HTML files into Substack Notes
└── Done
```

### 2.2 System Boundary Rules

- The daily content pipeline **reads** from scanner/portfolio outputs but **never writes** to them
- Notes and long-form posts are **independent pipelines** — a notes failure never blocks a post, and vice versa
- The tweet system and Substack system share upstream data but do not import from each other
- All LLM calls in the daily pipeline use **Sonnet** (cost-efficient for notes + market analysis). Long-form quality comes from **Opus in the chat session**

---

## 3. CONTENT CALENDAR

### 3.1 Weekly Post Schedule

| Day | Long-Form Post | Category | Theme | Trigger |
|-----|---------------|----------|-------|---------|
| **Saturday** | Weekly Newsletter (flagship) | Performance Review | Dashboard | Always — scanner data from Friday |
| **Sunday** | — (rest day) | — | — | — |
| **Monday** | — (market day, gather data) | — | — | — |
| **Tuesday** | Ticker Deep Dive or DD | Ticker Deep Dive | Editorial | Top new signal or highest-conviction position |
| **Wednesday** | Theme Rotation or Educational | Theme Rotation | Dashboard | Top PRIME/INVESTABLE theme this week |
| **Thursday** | Flex post | Educational / Portfolio Review / Topical | Varies | Depends on week's data — see decision logic below |
| **Friday** | — (scanner runs) | — | — | — |

### 3.2 Thursday Flex Logic

Thursday's post category is determined by available data:

```
IF new GREEN signals this week AND a theme has shifted status (new PRIME/INVESTABLE):
    → Theme Rotation (different theme than Wednesday)
ELIF portfolio has a position at +50% or +100% milestone:
    → Performance Review (milestone celebration)
ELIF no signals this week (quiet week):
    → Educational (evergreen investing framework)
ELSE:
    → Ticker Deep Dive (second-priority signal or portfolio position update)
```

### 3.3 Event Overrides

These override the scheduled category for that day:

| Event | Override | Priority |
|-------|----------|----------|
| New GREEN signal (midweek buy via daily monitoring) | Trade Alert post | Highest |
| Position exit (stop or manual sell) | Exit Alert post | High |
| Position hits +100% (Hall of Fame) | Milestone Celebration | High |
| Major market event (crash >3%, Fed surprise, etc.) | Market Commentary | Medium |

The daily_context_builder detects these by comparing current portfolio/signals state against the previous day's snapshot.

### 3.4 Notes Schedule (Daily, Live Context)

| Day | Note 1 (08:30 ET) | Note 2 (12:30 ET) | Note 3 (17:00 ET) |
|-----|--------------------|--------------------|---------------------|
| Saturday | PORTFOLIO_PULSE | THEME_MOMENTUM | — |
| Sunday | LEARNING_NUGGET | ENGAGEMENT_HOOK | — |
| Monday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |
| Tuesday | SIGNAL_ALERT | THEME_MOMENTUM | ENGAGEMENT_HOOK |
| Wednesday | MARKET_REACTION | PORTFOLIO_PULSE | LEARNING_NUGGET |
| Thursday | THEME_MOMENTUM | SIGNAL_ALERT | ENGAGEMENT_HOOK |
| Friday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |

**Changes from current batch system:**
- Reduced from 21/week to ~17/week (2 on weekends, 3 on weekdays)
- Generated daily with live prices, not batched on Friday
- MARKET_REACTION notes now actually react to the market (Mon/Wed/Fri morning)
- Weekend notes generated Saturday morning (after chat session data is available)

### 3.5 Note Types (Unchanged Definitions, Updated Context)

| Type | Purpose | Live Data Used |
|------|---------|---------------|
| PORTFOLIO_PULSE | Winner receipts, alpha proof | Live prices → real-time P&L |
| SIGNAL_ALERT | New signals or selectivity narrative | This week's signals + pass rate |
| THEME_MOMENTUM | Single theme focus | Theme scores + sector ETF performance |
| MARKET_REACTION | Quick take on market | SPY/QQQ/VIX from that morning |
| SYSTEM_PROOF | Funnel stats, screening narrative | Scanner stats + win rate |
| LEARNING_NUGGET | Educational content | Evergreen — no live data needed |
| ENGAGEMENT_HOOK | Community questions | Light portfolio context |

---

## 4. NEW MODULE: `daily_content_pipeline.py`

**Location:** `substack/daily_content_pipeline.py`
**Purpose:** Orchestrator for the daily content GitHub Action. Runs all steps in sequence.
**Lines:** ~150-200 (thin orchestrator)

### Responsibilities

1. Call `market_analyzer.py` to generate fresh market context
2. Call `daily_context_builder.py` to produce the daily context document
3. Call `daily_notes_generator.py` to produce today's notes
4. Call email notification to send summary + attachments
5. Handle errors gracefully — a notes failure still sends the context doc, and vice versa

### CLI

```bash
python -m substack.daily_content_pipeline                    # Full daily run
python -m substack.daily_content_pipeline --skip-notes       # Context doc only
python -m substack.daily_content_pipeline --skip-email       # No email notification
python -m substack.daily_content_pipeline --day wednesday    # Override day detection
python -m substack.daily_content_pipeline --dry-run          # Preview without LLM/email
```

### Error Handling

```python
def run_daily_pipeline(day: str, dry_run: bool = False, skip_notes: bool = False, skip_email: bool = False):
    results = {"market_analysis": None, "context_doc": None, "notes": [], "email_sent": False}

    # Step 1: Market analysis (non-blocking — use cached if fails)
    try:
        results["market_analysis"] = run_market_analysis(save=True)
    except Exception as e:
        print(f"  ⚠ Market analysis failed: {e} — using cached version")
        results["market_analysis"] = load_cached_market_analysis()

    # Step 2: Daily context doc (critical — always attempt)
    try:
        results["context_doc"] = build_daily_context(day, results["market_analysis"])
    except Exception as e:
        print(f"  ❌ Context doc failed: {e}")
        # Still attempt notes with available data

    # Step 3: Notes (non-blocking — failure doesn't stop email)
    if not skip_notes:
        try:
            results["notes"] = generate_daily_notes(day, dry_run=dry_run)
        except Exception as e:
            print(f"  ⚠ Notes generation failed: {e}")

    # Step 4: Email (sends whatever we have)
    if not skip_email and not dry_run:
        try:
            send_daily_email(day, results)
            results["email_sent"] = True
        except Exception as e:
            print(f"  ⚠ Email failed: {e}")

    return results
```

---

## 5. NEW MODULE: `content_utils.py` (Extracted from content_generator.py)

**Location:** `substack/content_utils.py`
**Purpose:** Shared data loading and formatting utilities used by multiple Substack modules
**Lines:** ~300 (extracted from content_generator.py's 1,624 lines)

### What to Extract

These functions and classes are imported by `content_production_guide.py` and other modules. They must survive the deletion of `content_generator.py`:

```python
# Data structures
ContentContext          # Dataclass aggregating all content data sources
PostSpec                # Dataclass defining a post's type, day, theme, priority

# Data loading
load_signals()          # Load signals.json with path fallback chain
load_portfolio_winners() # Load open positions, calculate P&L
load_equity_curve()     # Load NAV, alpha, benchmark stats
load_historical_themes() # Load 4 weeks of theme history from archives
build_content_context() # Aggregate all data into ContentContext

# Formatting helpers (used in prompts and context docs)
_format_themes_for_prompt()
_format_signals_for_prompt()
_format_winners_for_prompt()
_format_assessed_for_prompt()
_format_equity_stats()
_format_theme_history()

# Content safety
sanitize_text()         # Replace internal terminology via INTERNAL_TERMINOLOGY_MAP
validate_post_content() # 3-layer validation: banned phrases + marketing vocabulary

# HTML helpers
build_scan_funnel_html() # Visual funnel (Universe → Technical → Theme → GREEN)

# Template map
TEMPLATE_MAP            # Post type → (theme, filename, day) mapping
```

### What NOT to Extract

Everything related to LLM post generation stays behind and gets deleted with `content_generator.py`:
- `generate_post()` and its per-type prompt builders
- `determine_content_calendar()` (replaced by daily_context_builder logic)
- All `--market`, `--theme`, `--dd` CLI flags and their handlers

### Import Update Cascade

After extraction, update these files to import from `content_utils` instead of `content_generator`:

| File | Current Import | New Import |
|------|---------------|------------|
| `content_production_guide.py` → `daily_context_builder.py` | `from substack.content_generator import build_content_context, ...` | `from substack.content_utils import build_content_context, ...` |
| `newsletter_compiler.py` | Local functions for DD/theme loading | Move shared loaders to content_utils |

Also move from `newsletter_compiler.py` to `content_utils.py`:
- `load_dd_results()` — extracts DD fields from signals.json
- `load_theme_details()` — builds theme sub-score table
- `generate_benchmark_comparison()` — SPY/QQQ performance comparison

---

## 6. NOTES GENERATION (Daily, Live Context)

### 6.1 New Module: `daily_notes_generator.py`

**Location:** `substack/daily_notes_generator.py`
**Replaces:** `substack/notes_batch_generator.py` (1,347 lines)
**Target size:** ~600-800 lines (significantly simpler — generates 2-3 notes, not 21)

### 6.2 Key Differences from Current Batch System

| Aspect | Current (Batch) | New (Daily) |
|--------|----------------|-------------|
| When generated | Friday, all 21 at once | Each morning, 2-3 for today |
| Market data | Friday close prices only | Live prices from that morning |
| MARKET_REACTION | Written about Friday's market | Written about today's pre-market/yesterday's close |
| PORTFOLIO_PULSE | Friday P&L (stale by Wed) | Live P&L with current prices |
| Cost per run | ~$0.50-1.00 (21 notes) | ~$0.08-0.15 (2-3 notes) |
| Staleness risk | High (midweek notes are 3-5 days old) | None (generated same morning) |

### 6.3 Generation Flow

```python
def generate_daily_notes(day: str, context: dict, dry_run: bool = False) -> List[dict]:
    """Generate 2-3 notes for today using live context."""

    # 1. Determine today's note types from schedule
    schedule = get_notes_schedule(day)  # Returns 2-3 note type strings

    # 2. Build note-specific context (live prices already in context)
    note_context = build_note_context_from_daily(context)

    # 3. Generate each note
    notes = []
    for slot, note_type in enumerate(schedule, 1):
        if dry_run:
            notes.append({"type": note_type, "slot": slot, "text": f"[DRY RUN: {note_type}]"})
            continue

        # Generate with type-specific prompt
        raw = generate_single_note(note_type, note_context)

        # Validate + repair (existing pipeline from note_utils)
        validated = validate_and_repair(raw, note_type)

        # Save as HTML
        filepath = save_note_html(validated, day, slot, note_type)
        notes.append({"type": note_type, "slot": slot, "filepath": filepath, "text": validated})

    return notes
```

### 6.4 What to Preserve from notes_batch_generator.py

- **Note type definitions and rotation matrix** (Section 3.4 of this spec updates the schedule, but the type definitions stay)
- **System prompt** (BATCH_NOTES_SYSTEM_PROMPT — the physician-trader voice, marketing rules, format rules)
- **Engagement hook pools** (~60+ per-type hooks for closing questions)
- **Validation and repair pipeline** (validate_note → repair_note → drop + log)
- **HTML wrapping** (wrap_note_html with inline styles)
- **Dual-write save pattern** (current/ + archive/)

### 6.5 What to Remove

- All Friday-batch orchestration logic (generating 21 notes across 7 days)
- `--days N` and `--day X --full-week` modes (daily generator always generates for today)
- The separate `NotesBatchResult` tracking for 21-note batches
- Any references to `learning_content_library.py` (already deleted, fallback no longer needed)

### 6.6 CLI

```bash
python -m substack.daily_notes_generator                       # Today's notes
python -m substack.daily_notes_generator --day wednesday       # Override day
python -m substack.daily_notes_generator --html                # HTML output (default)
python -m substack.daily_notes_generator --dry-run             # Preview without LLM
python -m substack.daily_notes_generator --no-llm              # Template fallback only
```

---

## 7. REFACTOR: `daily_context_builder.py`

**Location:** `substack/daily_context_builder.py`
**Replaces:** `substack/content_production_guide.py` (858 lines)
**Target size:** ~500-600 lines

### 7.1 Purpose

Generates a daily context document (`daily_context.md`) containing everything needed for that day's chat-based post generation. Also produces `daily_notes_context.json` with structured data for the notes generator.

**No LLM calls. Cost: $0.**

### 7.2 Key Differences from content_production_guide.py

| Aspect | Current (Weekly Guide) | New (Daily Context) |
|--------|----------------------|---------------------|
| Scope | Entire week's schedule + all data | Today's specific topic + relevant data only |
| Prompt | References handbook — user finds the right one | Embeds the exact prompt, pre-filled with today's data |
| Market data | Friday's market_analysis.md | This morning's fresh market_analysis.md |
| Portfolio data | Friday close prices | Live prices from daily pipeline |
| Output | ~2,000 word markdown doc | ~800-1,200 word focused doc (less noise) |
| Frequency | Once per week (Friday) | Once per day (07:00 ET) |

### 7.3 Schedule Logic

```python
def determine_todays_post(day: str, signals: dict, portfolio: dict, history: dict) -> Optional[PostAssignment]:
    """Determine what post to write today, if any."""

    # Check event overrides first (highest priority)
    override = check_event_overrides(portfolio, signals)
    if override:
        return override

    # Day-based schedule
    if day == "saturday":
        return PostAssignment(
            category="Performance Review",
            theme="dashboard",
            topic="Weekly Newsletter — flagship recap",
            reason="Saturday = always weekly newsletter",
            prompt_key="performance_review",
        )
    elif day == "tuesday":
        # Ticker Deep Dive on top new signal, or top portfolio position
        ticker = get_top_signal_or_position(signals, portfolio)
        return PostAssignment(
            category="Ticker Deep Dive",
            theme="editorial",
            topic=f"Deep Dive — ${ticker['symbol']}",
            reason=f"Highest conviction {'new signal' if ticker['is_new'] else 'position'}",
            prompt_key="ticker_deep_dive",
            ticker_data=ticker,
        )
    elif day == "wednesday":
        # Theme Rotation on top PRIME/INVESTABLE theme
        theme = get_top_theme(signals)
        return PostAssignment(
            category="Theme Rotation",
            theme="dashboard",
            topic=f"Theme Rotation — {theme['name']}",
            reason=f"Top {'PRIME' if theme['status'] == 'PRIME' else 'INVESTABLE'} theme (composite {theme['score']}/100)",
            prompt_key="theme_rotation",
            theme_data=theme,
        )
    elif day == "thursday":
        return determine_thursday_flex(signals, portfolio)
    else:
        # Sunday, Monday, Friday — no long-form post
        return None
```

### 7.4 Event Override Detection

```python
def check_event_overrides(portfolio: dict, signals: dict) -> Optional[PostAssignment]:
    """Detect events that override the scheduled post category."""

    # Check for new milestones since yesterday
    for pos in portfolio.get("open_positions", []):
        pnl_pct = pos.get("pnl_pct", 0)
        prev_pnl = pos.get("prev_day_pnl_pct", 0)  # From yesterday's snapshot

        # Hall of Fame: crossed +100%
        if pnl_pct >= 100 and prev_pnl < 100:
            return PostAssignment(
                category="Performance Review",
                theme="dashboard",
                topic=f"HALL OF FAME — ${pos['symbol']} +{pnl_pct:.0f}%",
                reason="Position crossed +100% milestone",
                prompt_key="performance_review",
                override_type="milestone",
            )

        # Home Run: crossed +50%
        if pnl_pct >= 50 and prev_pnl < 50:
            return PostAssignment(
                category="Performance Review",
                theme="dashboard",
                topic=f"HOME RUN — ${pos['symbol']} +{pnl_pct:.0f}%",
                reason="Position crossed +50% milestone",
                prompt_key="performance_review",
                override_type="milestone",
            )

    # Check for exits since yesterday
    recent_exits = [e for e in portfolio.get("recent_exits", [])
                    if e.get("exit_date") == datetime.now().strftime("%Y-%m-%d")]
    if recent_exits:
        return PostAssignment(
            category="Ticker Deep Dive",
            theme="editorial",
            topic=f"Exit Alert — ${recent_exits[0]['symbol']}",
            reason=f"Position exited today: {recent_exits[0].get('exit_reason', 'stop hit')}",
            prompt_key="exit_alert",
            override_type="exit",
        )

    return None
```

### 7.5 Daily Context Document Format

The output `daily_context.md` follows this structure:

```markdown
# Sterling Signals — [Day] [Date]

## TODAY'S POST
**Category:** [Ticker Deep Dive / Theme Rotation / Educational / Performance Review]
**Topic:** [Specific topic with ticker or theme name]
**Theme:** [Editorial (light) / Dashboard (dark)]
**Why this topic:** [1-2 sentence explanation]

---

## YOUR PROMPT
[The complete prompt from handbook v5 for today's category, with data placeholders
already filled in. User copies this entire section and pastes into Claude.ai.]

---

## MARKET CONTEXT (generated [time] ET today)
[Full output from market_analyzer.py — 4 paragraphs]

## SIGNAL DATA
[Relevant signals for today's topic — new signals, assessed signals, or specific
ticker data depending on category]

## PORTFOLIO SNAPSHOT
Open: [N] positions | Win rate: [X]% | Best: $[TICKER] +[X]%
NAV: $[X] | vs SPY: [±X]% alpha | vs QQQ: [±X]% alpha
[Open positions table with live prices if available]

## THEME SUMMARY
[Active themes with scores, sorted by composite — relevant for Theme Rotation
and Educational posts]

## RECENT CONTENT (anti-repetition)
[Last 7 days of published post titles + categories to avoid overlap]

---

## TODAY'S NOTES (auto-generated, paste to Substack)
[Summary of 2-3 notes generated this morning — full HTML in separate files]

---

*Attach this file to Claude.ai (Opus 4.6 + extended thinking). Paste the prompt
from the "YOUR PROMPT" section. The response will be publishable HTML.*
```

### 7.6 Daily Notes Context (JSON sidecar)

```json
{
    "day": "tuesday",
    "date": "2026-02-25",
    "generated_at": "2026-02-25T12:00:00Z",
    "note_schedule": [
        {"slot": 1, "type": "SIGNAL_ALERT", "time": "08:30 ET"},
        {"slot": 2, "type": "THEME_MOMENTUM", "time": "12:30 ET"},
        {"slot": 3, "type": "ENGAGEMENT_HOOK", "time": "17:00 ET"}
    ],
    "live_data": {
        "spy_price": 589.24,
        "spy_change_pct": 0.42,
        "qqq_price": 512.18,
        "qqq_change_pct": 0.61,
        "vix": 14.2
    },
    "portfolio": {
        "open_count": 8,
        "win_rate": 75.0,
        "total_pnl_pct": 34.2,
        "top_performer": {"symbol": "LUNR", "pnl_pct": 112.4, "entry": 4.52, "current": 9.60},
        "positions": [
            {"symbol": "LUNR", "pnl_pct": 112.4, "theme": "Defense Technology"},
            {"symbol": "RCAT", "pnl_pct": 6.3, "theme": "Defense Technology"}
        ]
    },
    "signals": {
        "new_this_week": ["RCAT", "APLD"],
        "pass_count": 3,
        "themes": [
            {"name": "AI Power Infrastructure", "status": "PRIME", "composite": 85},
            {"name": "Defense Technology", "status": "INVESTABLE", "composite": 72}
        ]
    },
    "scanner_stats": {
        "universe_size": 1847,
        "technical_pass": 48,
        "theme_pass": 17,
        "green_signals": 3
    }
}
```

### 7.7 What to Preserve from content_production_guide.py

- `load_portfolio_data()` — but delegate to `content_utils.py` version
- `generate_system_context()` — system identity, marketing rules, banned terms reference
- `generate_content_history()` — last 4 weeks archive scan for anti-repetition
- Dual-write save pattern

### 7.8 What to Remove

- `build_weekly_schedule()` — replaced by per-day `determine_todays_post()`
- `generate_weekly_schedule()` — no longer generating a week-at-a-glance table
- `generate_prompt_reference()` — prompts are now embedded directly in the context doc
- All imports from `content_generator.py` — redirected to `content_utils.py`

### 7.9 Output Files

| File | Location | Consumer |
|------|----------|----------|
| `daily_context.md` | `substack/output/current/` + `archive/` | Human (Claude.ai chat) |
| `daily_notes_context.json` | `substack/output/current/` + `archive/` | `daily_notes_generator.py` |
| `content_schedule.json` | **REMOVED** — no longer generated | Nothing reads it (see Section 14) |

### 7.10 CLI

```bash
python -m substack.daily_context_builder                       # Today
python -m substack.daily_context_builder --day wednesday       # Override day
python -m substack.daily_context_builder --dry-run             # Preview to stdout
```

---

## 8. SIMPLIFY: `newsletter_compiler.py`

**Current:** 947 lines, two modes (LLM compilation + `--from-html` file copy)
**Target:** ~150 lines — `--from-html` mode only + general post archiver

### 8.1 What to Keep

The `--from-html` mode:
- `compile_from_html(path)` — copies a Claude.ai-generated HTML file to `substack/output/current/newsletter.html` and `archive/YYYY-WXX/newsletter.html`
- Validation pass on the copied HTML (banned terms check)
- CLI: `python -m substack.newsletter_compiler --from-html PATH`

Additionally, move these shared data loading functions to `content_utils.py`:
- `load_dd_results()` — extracts DD fields from signals.json
- `load_theme_details()` — builds theme sub-score table
- `generate_benchmark_comparison()` — SPY/QQQ performance comparison

### 8.2 What to Remove

- `compile_newsletter()` — the full LLM compilation pipeline (legacy mode)
- All LLM imports (anthropic client, system prompts, token counting)
- `load_market_analysis()` and `load_scanner_briefing()` — specific to the LLM compilation flow
- `load_portfolio_status()` — moved to content_utils if needed, or dropped

### 8.3 Simplified Module

```python
"""
NEWSLETTER COMPILER — Simplified
Copies Claude.ai-generated HTML to output directories. Also provides
general post archiving for midweek content.

Usage:
    python -m substack.newsletter_compiler --from-html PATH
    python -m substack.newsletter_compiler --archive-post PATH --filename tuesday_deep_dive.html
"""

def compile_from_html(html_path: str, dry_run: bool = False) -> Path:
    """Copy HTML file to current/ and archive/ with validation."""
    content = Path(html_path).read_text(encoding="utf-8")

    is_valid, violations = validate_content(content)
    if not is_valid:
        print(f"  ⚠ Banned terms found: {violations}")
        print(f"  Proceeding anyway — review before publishing")

    if dry_run:
        print(f"  [DRY RUN] Would save to current/ and archive/")
        return Path(html_path)

    output_path = save_to_substack_current_and_archive(
        content, "newsletter.html", make_dirs=True
    )
    print(f"  ✅ Newsletter saved to {output_path}")
    return output_path


def archive_post(html_path: str, filename: str, dry_run: bool = False) -> Path:
    """Archive any Substack post HTML to current/ and archive/."""
    content = Path(html_path).read_text(encoding="utf-8")
    is_valid, violations = validate_content(content)
    if not is_valid:
        print(f"  ⚠ Banned terms found: {violations}")

    if dry_run:
        return Path(html_path)

    return save_to_substack_current_and_archive(content, filename, make_dirs=True)
```

---

## 9. KEEP AS-IS MODULES

These modules require no changes:

| Module | Lines | Rationale |
|--------|-------|-----------|
| `dd_post_generator.py` | 545 | Works well. Generates HTML from DD data for Saturday workflow. No live context needed. |
| `portfolio_visual.py` | 819 | Dashboard generation is solid. Used by tweets and Substack. Runs Friday. |
| `html_templates.py` | 1,182 | Pure data file. Editorial + Dashboard themes work. Could move to separate `.html` files later but not blocking. |
| `note_utils.py` | 463 | Shared validation/repair/save utilities. Minor update: accept pre-built context (see 9.1). |
| `market_analyzer.py` | 282 | Excellent module. Currently Friday-only; now also called daily. No code change needed. |

### 9.1 Minor Update: `note_utils.py`

Add an optional parameter to `build_note_context()` to accept pre-fetched live data instead of always calling yfinance:

```python
def build_note_context(live_data: Optional[dict] = None) -> NoteContext:
    """Build note context. Uses live_data if provided, else fetches fresh."""
    if live_data:
        spy_5d = live_data.get("spy_change_pct", 0)
        qqq_5d = live_data.get("qqq_change_pct", 0)
    else:
        spy_5d, qqq_5d = get_index_performance()
    # ... rest unchanged
```

This avoids duplicate yfinance calls (daily pipeline already fetched prices).

---

## 10. FILE DELETIONS & DEPRECATIONS

### 10.1 Delete

| File | Lines | Reason |
|------|-------|--------|
| `substack/content_generator.py` | 1,624 | Replaced by chat workflow + content_utils.py extraction. LLM post generation via API is inferior to Opus chat. |
| `substack/content_production_guide.py` | 858 | Replaced by `daily_context_builder.py`. Weekly guide concept replaced by daily context doc. |
| `substack/notes_batch_generator.py` | 1,347 | Replaced by `daily_notes_generator.py`. Batch-on-Friday concept replaced by daily-with-live-context. |

**Total deleted:** 3,829 lines

### 10.2 Archive (Move to `substack/archive/` — Don't Delete Yet)

| File | Reason |
|------|--------|
| `substack/docs/newsletter_strategy.md` | Content strategy doc — useful reference but superseded by this spec |
| `substack/docs/sterling_signals_complete_scripts.md` | Pipeline reference — needs updating after changes |

### 10.3 Update CLAUDE.md References

After deletions, update CLAUDE.md to:
- Remove references to `content_generator.py`, `content_production_guide.py`, `notes_batch_generator.py`
- Add references to `daily_content_pipeline.py`, `daily_context_builder.py`, `daily_notes_generator.py`, `content_utils.py`
- Update the Friday pipeline description (no longer generates notes or content guide)
- Add daily pipeline description
- Update file tree

---

## 11. NEW GITHUB ACTION: `daily_content.yml`

```yaml
name: Daily Content Pipeline

on:
  schedule:
    # 07:00 ET (12:00 UTC during EST, 11:00 UTC during EDT)
    - cron: '0 12 * * 0-6'   # EST: 07:00 ET
    - cron: '0 11 * * 0-6'   # EDT: 07:00 ET
  workflow_dispatch:
    inputs:
      day_override:
        description: 'Override day (e.g., wednesday)'
        required: false
      dry_run:
        description: 'Dry run (no LLM calls, no email)'
        required: false
        default: 'false'

jobs:
  daily-content:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Timezone dedup
        id: tz_check
        run: |
          HOUR=$(date -u +%H)
          MONTH=$(date +%m)
          if [ "$MONTH" -ge 3 ] && [ "$MONTH" -le 10 ]; then
            EXPECTED=11
          else
            EXPECTED=12
          fi
          if [ "$HOUR" != "$EXPECTED" ] && [ "${{ github.event_name }}" = "schedule" ]; then
            echo "skip=true" >> $GITHUB_OUTPUT
          else
            echo "skip=false" >> $GITHUB_OUTPUT
          fi

      - name: Run daily content pipeline
        if: steps.tz_check.outputs.skip != 'true'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NOTIFICATION_EMAIL: ${{ secrets.NOTIFICATION_EMAIL }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
          EMAIL_SENDER: ${{ secrets.EMAIL_SENDER }}
        run: |
          ARGS=""
          if [ "${{ github.event.inputs.day_override }}" != "" ]; then
            ARGS="$ARGS --day ${{ github.event.inputs.day_override }}"
          fi
          if [ "${{ github.event.inputs.dry_run }}" = "true" ]; then
            ARGS="$ARGS --dry-run"
          fi
          python -m substack.daily_content_pipeline $ARGS

      - name: Commit outputs
        if: steps.tz_check.outputs.skip != 'true'
        run: |
          git config user.name "Sterling Bot"
          git config user.email "bot@sterling-signals.com"
          git add substack/output/ scanner/output/current/market_analysis.md
          git diff --staged --quiet || git commit -m "Auto: daily content $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
```

### 11.1 Friday Pipeline Update

Remove these steps from `friday_scan.yml`:
- `notes_batch_generator.py --html` (moved to daily pipeline)
- `content_production_guide.py` (replaced by daily_context_builder)

Keep these in `friday_scan.yml`:
- `portfolio_visual.py` (dashboard generation — still Friday-only)
- `dd_post_generator.py` (DD pages per signal — needs scanner data)

---

## 12. EMAIL NOTIFICATIONS

### 12.1 Daily Content Email

Uses the existing `utils/email_notifier.py` infrastructure.

**Subject:** `Sterling Signals — [Day]: [Post Topic or "Notes Only"]`

**Body structure:**
```
STERLING SIGNALS — DAILY CONTENT BRIEF
[Day], [Date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TODAY'S POST: [Category — Topic]
(or "No long-form post today — notes only")

MARKET SNAPSHOT
SPY: $589.24 (+0.42%)  |  QQQ: $512.18 (+0.61%)  |  VIX: 14.2

PORTFOLIO
Open: 8 positions  |  Win rate: 75%  |  Best: $LUNR +112%

TODAY'S NOTES (paste to Substack)
1. SIGNAL_ALERT: "New GREEN signal: $RCAT cleared all five gates..."
2. THEME_MOMENTUM: "AI Infrastructure theme composite at 85/100..."
3. ENGAGEMENT_HOOK: "What sectors are you watching this week?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ATTACHMENTS
- daily_context.md — attach to Claude.ai for today's post
- 3x note HTML files — paste directly to Substack Notes

The full daily_context.md is also in the repo:
substack/output/current/daily_context.md
```

**Attachments:**
- `daily_context.md` (for chat session)
- 2-3 note HTML files (for pasting to Substack)

### 12.2 Email Function

```python
def send_daily_email(day: str, results: dict):
    """Send daily content brief via email."""
    from utils.email_notifier import send_email

    post = results.get("context_doc", {}).get("post_assignment")
    notes = results.get("notes", [])

    subject = f"Sterling Signals — {day.title()}: "
    if post:
        subject += post.get("topic", post.get("category", "Content Ready"))
    else:
        subject += "Notes Only"

    body = format_email_body(day, post, notes, results.get("market_analysis"))

    attachments = []
    context_path = results.get("context_doc", {}).get("filepath")
    if context_path and Path(context_path).exists():
        attachments.append(str(context_path))
    for note in notes:
        if note.get("filepath") and Path(note["filepath"]).exists():
            attachments.append(note["filepath"])

    send_email(subject=subject, body=body, attachments=attachments)
```

---

## 13. DATA FLOW & FIELD DEPENDENCIES

### 13.1 What Substack Modules Read from signals.json

| Field | Read By | Keep? |
|-------|---------|-------|
| `buy_signals[]` (with DD fields) | content_utils, dd_post_generator, newsletter_compiler | Yes |
| `sell_signals[]` | content_utils (for exit alerts) | Yes |
| `themes[]` (with sub-scores) | content_utils, daily_context_builder, notes | Yes |
| `stats.universe_size` | notes (SYSTEM_PROOF), content_utils | Yes |
| `stats.technical_pass` | notes (SYSTEM_PROOF funnel) | Yes |
| `stats.market_regime` | content_utils (market context) | Yes |
| `assessed_signals[]` | content_utils (full signal list) | Yes |
| `historical_winners[]` | content_utils (top performers) | Yes |
| `big_wins[]` / `home_runs[]` | content_utils (milestone tracking) | Yes |
| `uc_rising_above` | **Nothing** | Safe to prune from merge |
| `sector_status` | **Nothing** (always empty string) | Safe to prune from merge |
| `pure_play_score` | **Nothing** (alias for theme_score) | Safe to prune from merge |

### 13.2 Cross-System Data Sharing

```
signals.json ──────────┬──→ Substack (content_utils, notes, context builder)
(canonical, weekly)     ├──→ Tweet system (tweet_generator, live_tweet_gen)
                        └──→ Portfolio visual (portfolio_visual.py)

portfolio.csv ─────────┬──→ Substack (content_utils, notes, portfolio_visual)
(updated weekly +       ├──→ Tweet system (signal_tracker, live_tweet_gen)
 on exits)              └──→ Email notifications (sell alerts)

market_analysis.md ────┬──→ Substack (daily_context_builder, notes)
(daily, fresh)          └──→ Tweet system (independent — uses Grok for X-specific context)

equity_curve.csv ──────┬──→ Substack (content_utils, portfolio_visual)
(weekly)                └──→ Tweet system (signal_tracker milestones)
```

**Boundary note:** The tweet system's `live_context_gatherer.py` generates its own market context via Grok 4 Fast (with X search + web search). It does NOT read `market_analysis.md`. These are intentionally independent — tweets need X-specific context (trending topics, sentiment), Substack needs traditional market analysis.

---

## 14. DEFERRED ITEMS RESOLUTION (from Scanner Spec)

### 14.1 `content_schedule.json` — Is It Consumed?

**Answer: No.** Only `content_production_guide.py` writes it, and nothing reads it. It was a metadata sidecar for a dashboard that was never built.

**Action:** Stop generating it. Module that produced it is being deleted.

### 14.2 Newsletter: Prompt 4 vs Automated

**Answer: Keep in chat (Prompt 4).** The Saturday newsletter is the flagship content piece. Opus 4.6 + extended thinking + human review produces meaningfully better output than any automated pipeline. The simplified `newsletter_compiler.py --from-html` handles archiving.

### 14.3 Legacy Field Pruning in Merged signals.json

**Answer:** Safe to prune from `merge_decisions.py`:
- `uc_rising_above` — nothing reads it
- `sector_status` — always empty string, nothing reads it
- `pure_play_score` — alias for theme_score, nothing reads it

**Keep:** `banker` (alias for UC) — tweet system's signal_tracker reads it for celebration tweets.

### 14.4 Prompt 7 Schema Alignment

**Deferred further.** Requires auditing merge_decisions.py field reads vs Prompt 7 output. Not blocking for Substack changes. Separate pass after both subsystem specs are implemented.

### 14.5 Analysis Log CSV

**Recommendation:** Simplify to technical-only fields (remove empty LLM columns). The daily_context_builder reads signals.json directly. Log is useful for scanner debugging but doesn't feed content generation.

---

## 15. IMPLEMENTATION ORDER

Execute in this order. Each phase is independently testable. Commit after each.

### Phase 1: Extract Utilities (1-2 hours)

1. Create `substack/content_utils.py` — extract from content_generator.py (Section 5)
2. Update `content_production_guide.py` imports to use content_utils (temporary — will be replaced)
3. Move `load_dd_results()`, `load_theme_details()`, `generate_benchmark_comparison()` from newsletter_compiler to content_utils
4. Verify: `python -c "from substack.content_utils import build_content_context, ContentContext"` works
5. Verify: `python -m substack.content_production_guide --dry-run` still works with new imports

**Commit:** `Extract shared utilities into substack/content_utils.py`

### Phase 2: Build Daily Context Builder (2-3 hours)

1. Create `substack/daily_context_builder.py` (Section 7)
2. Implement `determine_todays_post()` with schedule logic + event overrides
3. Implement `build_daily_context()` producing the markdown context doc
4. Implement `build_daily_notes_context()` producing the JSON sidecar
5. Embed prompts from handbook v5 — ensure exact prompt text, not references
6. Test: `python -m substack.daily_context_builder --day tuesday --dry-run`
7. Test: `python -m substack.daily_context_builder --day saturday --dry-run`
8. Test: Verify daily_context.md contains the correct prompt for each category

**Commit:** `Add daily_context_builder.py — per-day context doc with embedded prompts`

### Phase 3: Build Daily Notes Generator (2-3 hours)

1. Create `substack/daily_notes_generator.py` (Section 6)
2. Port note type definitions, system prompt, engagement hooks from notes_batch_generator
3. Implement `generate_daily_notes()` — 2-3 notes for today
4. Update `note_utils.py` to accept pre-fetched live data (Section 9.1)
5. Test: `python -m substack.daily_notes_generator --day monday --dry-run`
6. Test: `python -m substack.daily_notes_generator --day monday --html` (with LLM)
7. Validate: all generated notes pass banned terms check
8. Validate: MARKET_REACTION note references today's data, not stale Friday data

**Commit:** `Add daily_notes_generator.py — live-context notes replacing Friday batch`

### Phase 4: Build Pipeline Orchestrator + Email (1-2 hours)

1. Create `substack/daily_content_pipeline.py` (Section 4)
2. Wire together: market_analyzer → daily_context_builder → daily_notes_generator → email
3. Implement email notification (Section 12)
4. Test: `python -m substack.daily_content_pipeline --dry-run`
5. Test: `python -m substack.daily_content_pipeline --day tuesday` (full run with LLM + email)
6. Verify email arrives with correct subject, body, attachments

**Commit:** `Add daily_content_pipeline.py — orchestrator with email notifications`

### Phase 5: Simplify Newsletter Compiler (30 minutes)

1. Strip `newsletter_compiler.py` to `--from-html` mode only + `archive_post()` (Section 8)
2. Test: `python -m substack.newsletter_compiler --from-html path/to/test.html --dry-run`

**Commit:** `Simplify newsletter_compiler.py to file-copy + archive utility`

### Phase 6: Delete Old Modules + Create GitHub Action (1 hour)

1. Delete `content_generator.py` (verify no remaining imports first)
2. Delete `content_production_guide.py` (replaced by daily_context_builder)
3. Delete `notes_batch_generator.py` (replaced by daily_notes_generator)
4. Create `.github/workflows/daily_content.yml` (Section 11)
5. Update `friday_scan.yml` — remove notes batch and content guide steps
6. Update `run_friday.sh` — remove notes batch and content guide steps
7. Update `CLAUDE.md` — new module references, updated pipeline description

**Commit:** `Remove legacy modules, add daily_content.yml workflow`

### Phase 7: Integration Testing (1-2 hours)

1. Run full Friday pipeline (scanner → portfolio → DD posts → portfolio visual)
2. Simulate Saturday workflow (merge with test decisions.json)
3. Run daily content pipeline for each day of the week
4. Verify daily_context.md quality for each post category
5. Verify notes quality with live data
6. Verify email delivery
7. Verify all outputs are correctly archived

**Commit:** `Verify full weekly cycle — Friday → Saturday → daily content pipeline`

### Total Estimated Time: 10-14 hours across 7 phases

---

## 16. TESTING CHECKLIST

### Content Utils Tests
- [ ] `build_content_context()` returns valid ContentContext with all fields populated
- [ ] `load_signals()` fallback chain works (primary path → current/ → root)
- [ ] `load_portfolio_winners()` returns sorted positions with P&L
- [ ] `sanitize_text()` replaces all INTERNAL_TERMINOLOGY_MAP entries
- [ ] `validate_post_content()` catches all CRITICAL_BANNED terms

### Daily Context Builder Tests
- [ ] Saturday → always Performance Review
- [ ] Tuesday → Ticker Deep Dive with correct ticker data
- [ ] Wednesday → Theme Rotation with correct theme data
- [ ] Thursday flex → correct category based on data conditions
- [ ] Sunday/Monday/Friday → no post assignment (returns None)
- [ ] Event override: +100% milestone detected and overrides scheduled category
- [ ] Event override: exit detected and creates Exit Alert
- [ ] Anti-repetition: recent content history loaded from archives
- [ ] Embedded prompt matches handbook v5 verbatim for each category
- [ ] Output daily_context.md is well-formed markdown

### Daily Notes Generator Tests
- [ ] Generates correct number of notes per day (2 on weekends, 3 on weekdays)
- [ ] Correct note types assigned per schedule matrix
- [ ] MARKET_REACTION notes reference live market data (not stale)
- [ ] PORTFOLIO_PULSE notes reference live prices
- [ ] All generated notes pass `validate_note()` (banned terms + length + format)
- [ ] HTML output is self-contained with inline styles
- [ ] Dual-write: files in both current/ and archive/
- [ ] `--no-llm` mode produces template fallback content (no crash)

### Pipeline Orchestrator Tests
- [ ] Full pipeline completes without error
- [ ] Market analysis failure is non-blocking (uses cached version)
- [ ] Notes failure is non-blocking (context doc still sent)
- [ ] Email sends with correct subject, body, and attachments
- [ ] `--skip-notes` and `--skip-email` flags work
- [ ] `--dry-run` produces no LLM calls and no email

### Newsletter Compiler Tests
- [ ] `--from-html` copies file to current/ and archive/
- [ ] Banned terms validation runs on copied HTML
- [ ] `archive_post()` works for midweek post archiving
- [ ] Invalid path produces clear error message

### Integration Tests (Full Cycle)
- [ ] Friday scan → Saturday merge → Sunday daily pipeline → all outputs valid
- [ ] Run daily pipeline for each day Mon-Sat → verify all context docs are correct
- [ ] Verify no cross-contamination: daily pipeline never modifies signals.json or portfolio.csv
- [ ] Verify email delivery for 3 consecutive days
- [ ] Verify total API cost for one week's daily pipeline stays under $2.00

### GitHub Actions Tests
- [ ] `daily_content.yml` triggers on schedule
- [ ] Timezone dedup correctly skips redundant trigger
- [ ] `workflow_dispatch` with day_override works
- [ ] Commit step only fires when files changed
- [ ] No conflict with `friday_scan.yml` or `live_tweet.yml`

---

## 17. CONTENT QUALITY STANDARDS

### 17.1 Notes Quality Gates

Every generated note must pass ALL of these before saving:

| Gate | Check | Failure Action |
|------|-------|---------------|
| **Banned terms** | `validate_content()` returns `(True, [])` | LLM repair (max 2 attempts) |
| **Length** | 100-300 words | LLM repair (trim or expand) |
| **Format** | No markdown headers, no bullet lists | LLM repair |
| **Ticker format** | All tickers use `$TICKER` format | Regex fix |
| **Disclaimer** | Ends with "Not financial advice. Informational only." | Auto-append |
| **Data accuracy** | No fabricated prices or percentages | Verified against live_data in context |

### 17.2 Long-Form Post Quality (Human Responsibility)

These are enforced by the prompts in handbook v5, verified by the human:
- Correct HTML theme (editorial vs dashboard)
- No banned terms or internal terminology
- Accurate prices and percentages (cross-reference with context doc data)
- Engaging opening, clear structure, proper disclaimer
- 1,000-3,000 words depending on category

### 17.3 Anti-Fabrication Rules (Inherited from Master PRD)

- **NEVER fabricate prices, percentages, or dates** — all data must come from signals.json, portfolio.csv, or live price feeds
- **NEVER reference positions not in portfolio.csv** — only mention stocks we actually hold or have signalled
- **NEVER claim a signal was issued if it wasn't** — only reference stocks that appear in signals.json
- Notes system has additional guard: the `daily_notes_context.json` provides the ONLY data the LLM is allowed to reference. The system prompt instructs: "Use ONLY the data provided below. Do not invent any ticker, price, percentage, or date."

---

## SUMMARY

| Category | Count | Impact |
|----------|-------|--------|
| New modules | 4 | daily_content_pipeline, daily_context_builder, daily_notes_generator, content_utils |
| Simplified modules | 1 | newsletter_compiler (947 → ~150 lines) |
| Deleted modules | 3 | content_generator, content_production_guide, notes_batch_generator (3,829 lines) |
| Kept as-is modules | 5 | dd_post_generator, portfolio_visual, html_templates, note_utils, market_analyzer |
| New GitHub Action | 1 | daily_content.yml |
| Updated GitHub Action | 1 | friday_scan.yml (remove content steps) |
| Deferred items resolved | 4 of 5 | content_schedule.json, newsletter workflow, field pruning, analysis log |

**Net line change:** ~8,000 lines current → ~4,200 lines target

**Weekly cost:** ~$0.60-1.20 current → ~$0.70-1.50 target (daily market analysis adds ~$0.10/day, but notes cost spread across the week is similar)

**Manual effort:** ~20-30 min/day → ~5-10 min on post days, ~2 min on non-post days

**Content freshness:** Notes go from "stale by Wednesday" to "generated that morning with live data"

---

*End of Substack Subsystem Changes Specification — Generated 2026-02-25*
