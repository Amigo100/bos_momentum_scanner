# Sterling Signals Content System — Audit & Design Recommendations

> **Purpose:** Comprehensive audit of the Substack content system with specific improvement recommendations.
> Use this document as the reference for Claude.ai sessions where content rewriting happens.
> Date: 2026-03-05

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Current Voice & Tone (What Exists)](#2-current-voice--tone)
3. [Current Post Categories & Prompts](#3-current-post-categories--prompts)
4. [Current Note System](#4-current-note-system)
5. [HTML Themes & Formatting](#5-html-themes--formatting)
6. [Marketing Rules & Banned Terms](#6-marketing-rules--banned-terms)
7. [Data Sources Available](#7-data-sources-available)
8. [Identified Problems](#8-identified-problems)
9. [Design Recommendations](#9-design-recommendations)
10. [File Reference for Implementation](#10-file-reference-for-implementation)

---

## 1. System Architecture Overview

### Content Production Pipeline

```
FRIDAY PM: scanner.py → signals.json + newsletter_briefing.md
    ↓
SATURDAY PM: saturday_workflow.py → merge decisions + portfolio + archive
    ↓
DAILY 07:00 ET: daily_content_pipeline.py
    ├── Step 0:   yfinance portfolio refresh
    ├── Step 0.5: portfolio_visual.py → dashboard HTML + PNG
    ├── Step 1:   market_analyzer.py → market_analysis.md (LLM + web search)
    ├── Step 2:   daily_context_builder.py → daily_context.md + daily_notes_context.json
    ├── Step 3:   daily_notes_generator.py → 2-3 HTML notes (LLM via Sonnet)
    └── Step 4:   build_daily_email.py → SMTP email with self-contained prompts
    ↓
USER WORKFLOW (manual, from email):
    ├── Copy POST PROMPT → Claude.ai → get HTML post → paste to Substack
    └── Notes: auto-posted via substack-notes.yml (3x daily) or emailed as fallback
```

### Content-Producing Scripts

| Script | Triggered By | Output | Content Role |
|--------|-------------|--------|--------------|
| `substack/daily_context_builder.py` | Pipeline Step 2 | `daily_context.md` + `daily_notes_context.json` | Assigns post category + topic, builds context for Claude.ai |
| `substack/daily_notes_generator.py` | Pipeline Step 3 | 2-3 HTML notes in `current/notes/` | Generates note content via Claude Sonnet |
| `substack/market_analyzer.py` | Pipeline Step 1 | `market_analysis.md` | Market context via Claude + web search |
| `scripts/build_daily_email.py` | `daily_content.yml` after pipeline | HTML email to user | Assembles prompts + context for mobile Claude.ai workflow |
| `substack/newsletter_compiler.py` | Manual (`--from-html`) | `newsletter.html` | Converts Claude.ai HTML output for Substack |
| `substack/dd_post_generator.py` | `friday_scan.yml` / manual | `dd_TICKER.html` per signal | DD post HTML from signals data |
| `substack/portfolio_visual.py` | Pipeline Step 0.5 | `portfolio_visual.html` + PNG | Portfolio dashboard with equity curve |
| `substack/notes_poster.py` | `substack-notes.yml` (3x daily) | Posts to Substack API / email fallback | Posts individual notes at scheduled times |

### CI Workflows

| Workflow | Schedule | What It Does |
|----------|----------|-------------|
| `daily_content.yml` | Daily 07:00 ET | Full pipeline: market → context → notes → email |
| `substack-notes.yml` | 08:30 / 12:35 / 17:00 ET | Posts individual notes (API or email fallback) |
| `friday_scan.yml` | Friday 21:30 UTC | Technical scan → signals.json |
| `saturday_workflow.yml` | Saturday 21:30 UTC | Merge decisions → portfolio → archive |

---

## 2. Current Voice & Tone

### System Prompt (used in notes generation)

**Location:** `substack/daily_notes_generator.py` lines 103-137 AND `substack/note_utils.py` lines 63-93 (duplicated)

**Current identity:**
> "Three physicians who traded stethoscopes for stock screeners. We built a systematic momentum scanner that screens 1,800+ US stocks through a proprietary screening system — because we believe the same evidence-based rigor that saves lives in medicine can generate alpha in markets."

**Current voice rules:**
- "Clinical precision meets market conviction"
- "Triage setups, diagnose trends, prescribe entries and exits"
- "Think in probabilities, not certainties"
- "Contrarian by training — medicine taught us to question consensus"
- "Process over prediction. Our screening system is our clinical protocol."
- "Direct and specific. Every claim comes with a number."

**Current format rules (notes):**
- 150-300 words, short social posts NOT articles
- NO markdown headers, NO bullet lists
- Start with scroll-stopping hook
- End with engagement question
- $TICKER format with price or percentage
- Always end with "Not financial advice. Informational only."

### Post Prompts Voice (handbook v5)

The 6 post prompts in `content_prompt_handbook_v5.md` don't embed a system prompt — they rely on the context document to carry the voice. Each prompt has a "Tone:" line at the end:

| Category | Current Tone Instruction |
|----------|------------------------|
| Ticker Deep Dive | "Authoritative but accessible. Data-driven, confident, educational." |
| Educational | "Teacher, not preacher. Evidence-based, slightly contrarian. Light and engaging." |
| Theme Rotation | "Sharp, opinionated, data-backed. Institutional quality but accessible." |
| Performance Review | "Confident and direct. Like a weekly briefing from a trusted analyst." |
| Entry Alert | "Decisive, calm authority. Measured conviction backed by data." |
| Exit Alert | "Measured, professional. An exit should feel as deliberate as an entry." |

---

## 3. Current Post Categories & Prompts

### 4 Regular Categories + 2 Override Alerts

All prompts live in `substack/docs/content_prompt_handbook_v5.md` (597 lines).

### Category 1: Ticker Deep Dive (handbook lines 69-139)

**When assigned:** New GREEN signal or portfolio winner 15%+
**HTML theme:** Editorial (light/serif)
**Word count:** 1000-1500
**Research method:** 5-stage deep research with web search:
1. Financial Baseline (8-quarter revenue, margins, FCF, short interest, institutional ownership)
2. Forward Revenue Build (contracts, launches, pricing, TAM)
3. Margin & Earnings Projection (bear/base/bull scenarios)
4. Valuation Triangulation (4 methods: Historical, DCF, Peer-Relative, Catalyst-Adjusted)
5. Synthesis & Article

**Article structure (9 sections):**
1. The Pitch (2-3 sentence elevator pitch)
2. The Thesis (structural trend or catalyst)
3. Why Now (recent inflection)
4. The Numbers (revenue, margins, valuation)
5. 12-Month Price Targets (bear/base/bull with probability weightings)
6. Bear Case (what could go wrong)
7. Key Risk to Monitor (one specific thing with date)
8. Our View (confident summary)
9. Footer (subscribe CTA)

**Includes:** `[CHART: TICKER]` placeholder

### Category 2: Educational (handbook lines 147-198)

**When assigned:** Fills remaining days when no signals/themes to cover
**HTML theme:** Editorial (light/serif)
**Word count:** 800-1200
**Topic selection:** Web search discovers topic from 7 areas:
- Execution, Analysis, Psychology, System, Risk Management, Momentum, Strategy

**Each candidate evaluated on:** Timeliness, Data richness, Audience fit, Novelty, Portfolio connection

**Article structure (7 sections):**
1. Hook (surprising stat or counterintuitive finding)
2. The Concept (teach core idea)
3. The Evidence (studies, data, specific numbers)
4. How We Apply It (connect to screening system + portfolio winners)
5. The Takeaway (one actionable insight)
6. Engagement Close (genuine question)
7. Footer (subscribe CTA)

### Category 3: Theme Rotation (handbook lines 206-250)

**When assigned:** Active PRIME/INVESTABLE themes from scanner
**HTML theme:** Dashboard (dark/teal)
**Word count:** 800-1200
**Research method:** 3-stage:
1. Theme Validation (cross-reference with fresh data since Friday)
2. Deep Research (ETF flows, institutional positioning, policy, earnings, risks, timeline)
3. Article

**Article structure (8 sections):**
1. Why This Theme, Why Now (strongest data point first)
2. The Investment Thesis (structural dynamics)
3. The Evidence (ETF flows, institutional moves, catalysts)
4. What Our System Sees (scanner theme analysis + portfolio positions)
5. Risks to the Thesis
6. What We're Watching (specific events with dates)
7. Stocks Positioned (3-5 stocks)
8. Footer (subscribe CTA)

### Category 4: Performance Review / Sunday Newsletter (handbook lines 258-291)

**When assigned:** Always Sunday
**HTML theme:** Dashboard (dark/teal)
**Word count:** 1200-1500
**Freshness check:** SPY, QQQ, IWM, VIX current data via web search

**Article structure (8 sections):**
1. Market Context (what happened this week)
2. What Our Scanner Found (screening funnel + `[SCAN_FUNNEL]` placeholder)
3. Themes Driving Momentum (top 2-3 themes + `[THEME_SCORES]` placeholder)
4. New GREEN Signals (or "Why We Passed" if no signals)
5. Portfolio Performance (showcase winners + `[WINNERS_TABLE]` placeholder)
6. Benchmark Battle (Portfolio vs SPY YTD vs QQQ YTD)
7. Looking Ahead (3-5 specific next-week catalysts)
8. Footer (subscribe CTA)

### Trade Alert — Entry (handbook lines 301-328)

**Trigger:** Manual — user entering a new position
**HTML theme:** Editorial
**Word count:** 400-800
**Structure:** Trade Header, Why This Name, Signal Trigger, The Setup, What We're Watching, Risk Framing, Footer

### Trade Alert — Exit (handbook lines 338-369)

**Trigger:** Manual — user closing a position
**HTML theme:** Editorial
**Word count:** 400-800
**Critical framing:** If profitable → lead with return %. If at a loss → NEVER mention P&L number, frame as "systematic exit discipline triggered"
**Structure:** Trade Header, Exit Decision, What Changed, The Lesson, What's Next, Footer

### Daily Notes Prompt (handbook lines 379-462)

**Universal prompt** used once per day in Claude.ai. Generates 3 HTML notes.

**Rotation matrix (from handbook):**

| Day | Note 1 | Note 2 | Note 3 |
|-----|--------|--------|--------|
| Sunday | Community & Connection | Journey & Milestones | Week Preview |
| Monday | Market Macro | Winner Highlight | Ticker News |
| Tuesday | Geopolitics/Macro | Theme Spotlight | Community |
| Wednesday | Teaching & Wisdom | Portfolio Insight | Community |
| Thursday | Market Midweek | System Insight | Ticker News |
| Friday | Week Reflection | Winner Recap | Engagement |
| Saturday | Journey | Teaching | Community |

**Note guidelines per type:** 12 type descriptions (Community & Connection, Journey & Milestones, Market Macro, Winner Highlight, Ticker News, Theme Spotlight, System Insight, Teaching & Wisdom, Portfolio Insight, Week Preview/Review, Weekend Engagement)

**Format:** Self-contained HTML snippets, 100-200 words, inline styles, $TICKER format

---

## 4. Current Note System (Automated — daily_notes_generator.py)

### Separate from Handbook Notes

The handbook's "Daily Notes Prompt" is used when the user manually generates notes via Claude.ai. But the automated system in `daily_notes_generator.py` uses a **completely different** set of 7 types and schedule.

### Automated Note Types (what actually runs in CI)

**Location:** `substack/daily_notes_generator.py` lines 78-96

| Type Code | Purpose | Data Source |
|-----------|---------|-------------|
| `PORTFOLIO_PULSE` | Winner receipts, alpha proof | Portfolio positions with P&L |
| `SIGNAL_ALERT` | New signals or selectivity narrative | signals.json PASS/CAUTION |
| `THEME_MOMENTUM` | Single theme focus, thesis, catalysts | Theme data with scores |
| `MARKET_REACTION` | SPY/QQQ/VIX quick takes | Live yfinance data |
| `SYSTEM_PROOF` | Funnel stats, screening narrative | scan_stats |
| `LEARNING_NUGGET` | Evergreen investing wisdom | learning_content_library.py |
| `ENGAGEMENT_HOOK` | Community questions | ENGAGEMENT_HOOKS dict (60+ hooks) |

### Automated Schedule (what actually runs)

**Location:** `substack/daily_notes_generator.py` `NOTES_SCHEDULE` dict (lines 78-86)

| Day | Slot 1 (08:30 ET) | Slot 2 (12:30 ET) | Slot 3 (17:00 ET) |
|-----|--------------------|--------------------|---------------------|
| Saturday | PORTFOLIO_PULSE | THEME_MOMENTUM | — |
| Sunday | LEARNING_NUGGET | ENGAGEMENT_HOOK | — |
| Monday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |
| Tuesday | SIGNAL_ALERT | THEME_MOMENTUM | ENGAGEMENT_HOOK |
| Wednesday | MARKET_REACTION | PORTFOLIO_PULSE | LEARNING_NUGGET |
| Thursday | THEME_MOMENTUM | SIGNAL_ALERT | ENGAGEMENT_HOOK |
| Friday | MARKET_REACTION | SYSTEM_PROOF | PORTFOLIO_PULSE |

### Note Generation Process

1. Load `daily_notes_context.json` (built by `daily_context_builder.py`)
2. For each scheduled note type → build type-specific LLM prompt with embedded data
3. Call Claude Sonnet 4 (`MODEL_NOTES`), max 1000 tokens
4. 3-layer validation: banned terms → loser focus → format check
5. If fails: 1 LLM repair attempt, then drop + log
6. Save as HTML: `note_{slot}_{type}_{date}.html`

### Note HTML Template

**Location:** `daily_notes_generator.py` lines 144-159

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
     max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a;
     line-height: 1.6; font-size: 16px;">
  [body_html]
  <p style="color: #6b6b6b; font-size: 13px; margin-top: 16px;
     padding-top: 12px; border-top: 1px solid #e0ddd8;">
    Not financial advice. Informational only.
  </p>
</div>
```

### Engagement Hooks (60+ hooks)

**Location:** `daily_notes_generator.py` lines 166-250+

8 hooks per note type. Examples:
- PORTFOLIO_PULSE: "What themes are driving your portfolio right now?"
- SIGNAL_ALERT: "Would you take this trade? Why or why not?"
- THEME_MOMENTUM: "Is anyone else noticing this theme gaining momentum?"
- MARKET_REACTION: "How are you reading today's market action?"

---

## 5. HTML Themes & Formatting

### Two Themes in `substack/html_templates.py` (1183 lines)

#### Editorial Theme (Light, Serif)
- **Used for:** Ticker Deep Dives, Educational, Trade Alerts
- Background: `#fafaf8` | Container: `#fff` | Text: `#1a1a1a`
- Headings: Georgia/Times serif | Body: system sans-serif
- Positive: `#2e5e3e` | Negative: `#a04030`
- Price targets: Bear `#fdf6f4`/`#8b3a1a`, Base `#f4f7fa`/`#1b3a5c`, Bull `#f4faf5`/`#2e5e3e`
- Components: masthead, target banner, stat row, callouts (3 variants), tables, catalyst lists

#### Dashboard Theme (Dark, Teal)
- **Used for:** Theme Rotation, Performance Review, Portfolio Showcase
- Background: `#111827` | Cards: `#1F2937` | Accent: `#2DD4BF`
- Green: `#22C55E` | Amber: `#FBBF24` | Red: `#EF4444`
- Text: `#F9FAFB` | Muted: `#9CA3AF`
- Components: hero, stat grid, theme cards with progress bars, funnel, pullquote, winners table

#### Notes Theme (Minimal)
- Background: transparent | Max-width: 680px
- Font: system sans-serif 16px, line-height 1.6
- Disclaimer: `#6b6b6b` 13px with `#e0ddd8` top border

### Visual Placeholders in Posts
- `[CHART: TICKER]` — TradingView chart screenshot (added manually)
- `[SCAN_FUNNEL]` — Screening funnel visualization
- `[THEME_SCORES]` — Theme score cards with progress bars
- `[WINNERS_TABLE]` — Portfolio winners table

---

## 6. Marketing Rules & Banned Terms

### Banned Terms Registry — `config/banned_terms.py` (378 lines)

**105 CRITICAL_BANNED terms** including:

**Indicators (NEVER use):** HMA, Hull Moving Average, RSI, RSI(10), RSI(14), MACD, KDJ, VWAP, Banker, Banker indicator, Banker rising, Banker >= 55, UC, UC rising, UC falling, Undercurrent, BoS, Break of Structure, ExD, Beta >= 1.5

**System internals (NEVER use):** Gatekeeper, Investment Gate, Deep DD, 5-gate, 5th Gate, Tier 1/2/3, conviction score, conviction 1-10, profit lock, tiered stop, gear shift, sizing gear, price cap, $25 cap, STRONG BUY, SPEC BUY, NO GO

**Old branding (NEVER use):** TEAL signal, VIOLET signal, AMBER signal, Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria

**Geography (NEVER use):** UK ISA, ISA account, GMT, BST, UK Time, Roth IRA, PDT, 401k

**Vague phrases (NEVER use):** "theme keeps delivering", "system keeps working", "trust the process", "some interesting setups", "stay tuned", "picks and shovels"

### Approved Alternatives — `config/marketing_vocabulary.py`

| Internal | Public |
|----------|--------|
| HMA/Banker/UC/indicators | "proprietary screening system" or "our screening system" |
| Entry signal / HMA pivot | "momentum confirmed", "structural pivot confirmation" |
| Banker/UC rising | "institutional accumulation divergence" |
| Stop hit / exit | "systematic exit discipline" |
| Conviction 8-10 | "Extremely Bullish" |
| Conviction 7 | "Bullish" |
| Conviction 4-6 | "Watching" |
| TEAL/PASS signal | "GREEN signal" |

### Signal Colors
- GREEN (buy) — `emoji: 🟢`
- RED (exit) — `emoji: 🔴`
- CONSIDER (watchlist) — `emoji: 🟡`

### Winners-Only Display Rules
- 15%+ gain: Can showcase + mention P&L %
- 25%+ gain: Can show entry price
- Under 15%: Do not highlight or showcase
- Losses: NEVER mention specific P&L numbers

### Loss Framing Rules
- If profitable: Lead with return
- If at a loss: NEVER say "loss", "stopped out", "down", "negative"
- Frame as: "systematic exit discipline triggered", "the system working as designed"

---

## 7. Data Sources Available for Content

The system has rich data that content should leverage maximally:

### From `signals.json` (weekly scan)
- `scan_stats`: tickers_loaded, data_downloaded, beta_gte_1_5, weekly_bos_up, technical_signals, theme_confirmed, final_trade, final_consider
- `themes[]`: name, classification (PRIME/INVESTABLE/SELECTIVE/AVOID), composite_score, thesis_summary, key_catalysts, primary_etfs
- `buy_signals[]`: symbol, price, beta, momentum_4w, return_20d, theme, theme_score, pure_play_score, theme_verdict, conviction, catalyst_summary, red_flag_level, bullish_factors, risk_factors, reasoning, action
- `sell_signals[]` and `exit_signals[]`: symbol, reason, action

### From `portfolio.csv` (live positions)
- ticker, status, entry_date, entry_price, current_price, highest_close
- Calculated: pnl_pct, pnl_usd, stop_level, days_held, distance_to_stop_pct, stop_alert

### From `equity_curve.csv` (historical NAV)
- Weekly NAV snapshots with SPY and QQQ benchmarks
- Alpha calculations vs both benchmarks

### From `market_analysis.md` (daily, LLM-generated)
- SPY/QQQ/VIX levels and changes
- Sector rotation observations
- Key macro events
- Upcoming catalysts

### From `daily_notes_context.json` (aggregated for notes)
- day, date, post_category, post_topic
- portfolio: open_positions, showcase_winners, recent_exits
- themes: prime, investable lists
- signals: pass, caution lists
- market_data: spy_price, spy_change_pct, qqq_price, qqq_change_pct, vix

---

## 8. Identified Problems

### Problem 1: Voice Identity Mismatch
- The "three physicians" medical metaphor feels forced and inauthentic
- Medical jargon (triage, diagnose, prescribe) doesn't resonate with US swing traders
- Voice is not informative enough — too much personality framing, not enough data delivery

### Problem 2: Notes Feel Generic & Repetitive
- 7 broad types cycle predictably — Monday MARKET_REACTION looks like Wednesday MARKET_REACTION
- Types are too vague: "PORTFOLIO_PULSE" could be anything about the portfolio
- Not enough specific data embedded — notes read as generic market commentary
- Engagement hooks are formulaic ("What themes are driving your portfolio?")
- No subscriber conversion hooks — notes inform but don't convert

### Problem 3: Handbook vs Code Note Systems Are Out of Sync
- Handbook v5 has 11 note type descriptions (Community & Connection, Journey & Milestones, etc.)
- Code has 7 different types (PORTFOLIO_PULSE, SIGNAL_ALERT, etc.)
- Two completely different rotation matrices
- When user manually generates notes (Claude.ai) vs automated (CI), they get different content strategies

### Problem 4: Posts Don't Fully Leverage System Data
- Ticker Deep Dive does extensive web research but could better integrate scanner-specific data (theme score, pure play score, conviction reasoning)
- Theme Rotation doesn't always connect back to specific portfolio positions clearly
- Performance Review could be more compelling as the primary subscriber conversion piece
- Educational topics are web-search discovered — could be more connected to current portfolio/market events

### Problem 5: Content Doesn't Convert
- CTAs are generic footer links ("Subscribe to Sterling Signals for...")
- Notes end with engagement questions instead of subscribe hooks
- No "show don't tell" approach — not demonstrating what subscribers get
- No FOMO triggers or social proof in notes
- Substack Notes are the #1 growth driver (70% of subscriber growth in 2026) but our notes aren't optimized for subscription conversion

### Problem 6: Post-Note Alignment
- No explicit deduplication between daily post and daily notes
- Notes might cover the same ticker/theme as the post that day
- No complementary content strategy (if post is a deep dive, notes could provide different angles)

---

## 9. Design Recommendations

### 9.1 New Voice: "The Signal Hunter" (Information-First)

**Replace the medical metaphor with a data-forward, informative voice.**

**Core principle:** Clarity over cleverness. Real data over sensational hooks. Every word earns its place by informing the reader.

**New identity:**
> A systematic trader who screens 1,800 stocks weekly and shares exactly what the system finds. Direct, factual, useful. Confidence comes from showing real numbers — not from bold language. Tells you what the scanner found, what the portfolio looks like, and what the data says. Readers finish every piece knowing something specific they didn't before.

**Voice markers:**
- Lead with the data point: "SPY dropped 1.2% today. Our portfolio gained 0.3%. Here's why."
- Name the thing: "$RCAT entered at $8.50, now $13.25. +55.9% in 23 days."
- Show the filter: "1,817 stocks scanned. 48 passed the technical gate. 6 cleared all gates."
- Be direct: "Drone technology is rotating out. Grid infrastructure is rotating in."
- Explain decisions: "We exited $VNET because the structural trend broke. That's the system working."

**What it IS:** Informative, data-dense, transparent, selective, actionable
**What it's NOT:** Sensational, vague, preachy, hedging, hype

**Files to update:**
- `substack/daily_notes_generator.py` — `NOTES_SYSTEM_PROMPT` (lines 103-137)
- `substack/note_utils.py` — `NOTES_SYSTEM_PROMPT` (lines 63-93)
- `substack/docs/content_prompt_handbook_v5.md` → v6 — all tone instructions
- `scripts/build_daily_email.py` — any voice references in email copy

### 9.2 Note System Redesign

**Goal:** Every note should contain at least one specific data point and a natural reason to subscribe.

**Proposed: 12 specific note archetypes** (replacing 7 broad types):

| # | Archetype | Content | Data Source | Fires When |
|---|-----------|---------|-------------|------------|
| 1 | **Market Snapshot** | SPY/QQQ/VIX + one portfolio impact | Live yfinance | Mon-Fri mornings |
| 2 | **Signal Drop** | New GREEN signal: ticker, theme, trigger | signals.json PASS | When signals exist |
| 3 | **Winner Receipt** | Position: entry, current, P&L%, days held | Portfolio 15%+ | When winners exist |
| 4 | **Theme Rotation** | One theme: score, ETF flow, 1-2 tickers | Theme data | 2-3x/week |
| 5 | **The Filter** | Funnel: 1,817 → X → Y → Z. What got rejected. | scan_stats | 1-2x/week |
| 6 | **Catalyst Calendar** | Upcoming earnings/events for positions | Web search + portfolio | 1-2x/week |
| 7 | **Sector Flow** | Money in/out: one sector gaining, one losing | Market data + themes | Mon/Wed/Fri |
| 8 | **Exit Debrief** | Position closed: why, what system saw, lesson | Portfolio exits | When exits happen |
| 9 | **Contrarian Read** | One thing consensus is wrong about, data-backed | Themes + market | 1x/week |
| 10 | **Alpha Scoreboard** | Portfolio vs SPY/QQQ: return %, time period | equity_curve.csv | 1x/week |
| 11 | **Data Insight** | One investing pattern/stat, connected to portfolio | Educational + context | 1-2x/week |
| 12 | **Reader Question** | Specific question about sector/theme readers watch | Themes + market | 1-2x/week |

**Key design changes:**
- **Conditional firing**: Some types only appear when data exists (no fabrication)
- **Each archetype does ONE thing** — sharper than current broad types
- **Data-first**: Every note tied to a specific data source
- **Subscribe hooks**: Every note ends with a natural "see more" hook showing what subscribers get

**Subscribe hook examples:**
- Winner Receipt: "Subscribers got this signal at $8.50. The next screening drops Friday."
- The Filter: "6 stocks cleared all gates this week. Full analysis in Sunday's newsletter."
- Theme Rotation: "We track 5 themes across 1,800 stocks weekly. See which ones made the cut → [link]"

**Files to update:**
- `substack/daily_notes_generator.py` — `NOTES_SCHEDULE`, `NOTE_TYPES`, per-type prompts, `ENGAGEMENT_HOOKS`
- `substack/note_utils.py` — System prompt, validation rules
- `substack/daily_context_builder.py` — Note schedule references in context doc

### 9.3 Post Prompt Optimization

**Keep the 4 categories but improve data utilization and voice:**

**Ticker Deep Dive improvements:**
- Better integration of scanner-specific data (theme score, pure play score, conviction reasoning from Investment Gate)
- Price target methodology already strong — ensure new voice is applied
- Connect more explicitly to current portfolio composition and theme alignment

**Educational improvements:**
- Topic discovery should check current portfolio events first (position hitting milestone, theme shifting, upcoming catalyst) before web searching for generic topics
- Should always anchor to something specific from the scanner/portfolio — "here's what we're seeing in practice"

**Theme Rotation improvements:**
- More opinionated — instead of "here's a theme", frame as "here's what the data says about where money is flowing and why"
- Better use of scanner theme scores (PRIME/INVESTABLE/SELECTIVE/AVOID with sub-scores)
- Connect to specific portfolio positions in that theme

**Performance Review improvements:**
- This is the primary subscriber conversion piece — needs to be the most compelling content of the week
- Lead with the strongest proof point (alpha vs benchmark, biggest winner, rejection rate)
- More specific forward-looking section with dates and catalysts
- Stronger subscribe CTA — this is where free readers decide to stay

**Files to update:**
- `substack/docs/content_prompt_handbook_v5.md` → v6 with all revised prompts

### 9.4 Handbook/Code Note Alignment

**The handbook v5 notes rotation and the code's `NOTES_SCHEDULE` must be unified.**

Options:
- A) Code adopts handbook types → rewrite code note types to match handbook names
- B) Handbook adopts code types → update handbook rotation to use code's 7 (or new 12) types
- C) Separate systems with clear roles → handbook for manual override, code for daily automation

**Recommendation:** Option B — update handbook to reference the same note archetypes that the code uses. When the user manually generates notes via Claude.ai, they should use the same taxonomy as the automated system. This ensures consistency across all channels.

**Files to update:**
- `substack/docs/content_prompt_handbook_v5.md` → v6 notes prompt with aligned types
- `substack/daily_notes_generator.py` — if new archetypes adopted

### 9.5 Post-Note Complementary Scheduling

**Add explicit deduplication and complementary logic:**

- If today's post is Ticker Deep Dive on $RCAT → notes should NOT mention RCAT
- If today's post is Theme Rotation on "AI Infrastructure" → notes should cover different themes
- If today's post is Educational → notes should be more data-heavy (market snapshot, winner receipt, alpha scoreboard) to balance
- If today's post is Performance Review → notes should be forward-looking (catalyst calendar, theme rotation, sector flow)

**Files to update:**
- `substack/daily_context_builder.py` — dedup logic in note assignment
- `substack/daily_notes_generator.py` — post-aware note selection

### 9.6 CTA Strategy

**Current:** Generic footer links ("Subscribe to Sterling Signals for weekly analysis and GREEN signals")

**Proposed:** Natural "show don't tell" hooks embedded in content:

**For posts:**
- End each section with a value demonstration, not just a link
- Performance Review: "Last week's GREEN signal is up X% — subscribers got it before the market opened Monday."
- Ticker Deep Dive: "Our screening system identified $TICKER before the breakout. Get the next signal → [subscribe]"

**For notes:**
- Replace generic engagement questions with subscribe-relevant hooks
- Always demonstrate what subscribers uniquely get (early signals, full analysis, exit alerts)
- Vary CTA style to avoid repetition (some weeks proof-based, some FOMO-based, some value-based)

**Files to update:**
- `substack/docs/content_prompt_handbook_v5.md` → v6 post footer CTAs
- `substack/daily_notes_generator.py` — note ending templates
- `substack/daily_notes_generator.py` — `ENGAGEMENT_HOOKS` dict replaced with `SUBSCRIBE_HOOKS`

---

## 10. File Reference for Implementation

### Files That Need Content Changes

| File | Lines | What Changes |
|------|-------|-------------|
| `substack/docs/content_prompt_handbook_v5.md` | 597 | → v6: New voice in all prompts, updated note rotation, revised CTAs, aligned note types |
| `substack/daily_notes_generator.py` | ~500 | New `NOTES_SYSTEM_PROMPT`, new `NOTES_SCHEDULE` (12 types), new per-type prompts, new hooks |
| `substack/note_utils.py` | ~400 | Updated `NOTES_SYSTEM_PROMPT` (must sync with generator), validation rules for new types |
| `scripts/build_daily_email.py` | ~500 | Voice references in email copy, handbook references |
| `substack/daily_context_builder.py` | ~600 | Note schedule references, post-note dedup logic, context doc formatting |

### Files That May Need Minor Updates

| File | Why |
|------|-----|
| `substack/html_templates.py` | Only if HTML theme tweaks needed |
| `config/banned_terms.py` | If new banned terms or approved alternatives added |
| `config/marketing_vocabulary.py` | If new terminology mappings needed |
| `substack/market_analyzer.py` | If market analysis prompt needs voice update |
| `substack/learning_content_library.py` | If educational content library needs refresh |

### Files That Stay Unchanged

| File | Why |
|------|-----|
| `substack/newsletter_compiler.py` | Just converts HTML, no content generation |
| `substack/dd_post_generator.py` | Generates from signals data, voice comes from handbook |
| `substack/portfolio_visual.py` | Data visualization, no voice/content |
| `substack/notes_poster.py` | Just posts notes, no content decisions |
| All CI workflows | Pipeline stays the same, just content quality improves |

---

## Substack Growth Context (2026)

Key findings from Substack platform research:

- **Notes drive 70% of subscriber growth** — note quality is the single highest-leverage improvement
- **32 million new subscribers** came from within the Substack app in one recent quarter — internal discovery matters more than external traffic
- **Algorithm optimizes for subscriptions** — content that makes people subscribe gets more distribution
- **Consistency beats volume** — showing up daily with 1-2 quality notes outperforms sporadic posting
- **Engagement creates threads** — replying to comments signals the algorithm
- **80/20 rule** — 80% pure value, 20% soft CTAs

Sources:
- [Substack Notes Strategy 2026](https://thrivewithcarrie.substack.com/p/substack-notes-strategy-2026)
- [Substack 2026 Playbook](https://wanderwealth.substack.com/p/the-2026-substack-playbook-5-shifts)
- [What Quiet Winners Are Doing](https://pubstacksuccess.substack.com/p/what-the-quiet-winners-are-doing)
