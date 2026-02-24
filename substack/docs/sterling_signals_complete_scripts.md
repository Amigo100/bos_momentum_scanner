# STERLING SIGNALS — COMPLETE SCRIPTS REFERENCE
# All Source Files: Tiers 1-6 + Pipeline Diagrams
# Generated: February 2026
# Purpose: Attach alongside the audit document when pasting into Claude.ai
#
# HOW TO USE:
# 1. Attach both files to Claude.ai (Opus 4.6):
#    - This file: sterling_signals_complete_scripts.md (ALL code)
#    - The audit:  cached-pondering-moth.md (architecture analysis)
# 2. Ask Claude to analyse, restructure, or improve the system

---

# PIPELINE DIAGRAMS

## FRIDAY PIPELINE (Full Sequence)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    FRIDAY PIPELINE — 12 Steps                            │
│         GitHub Actions (friday_scan.yml) OR Local (run_friday.sh)        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: core/scanner.py --web-search --archive                          │
│          ├── Downloads 1,817 tickers via yfinance                        │
│          ├── Technical Gate: HMA slope + RSI + MACD + UC                 │
│          ├── Thematic Analyzer (Claude Sonnet) → themes classified       │
│          ├── Investment Gate (Claude Sonnet) → per-stock PASS/CONSIDER   │
│          ├── Deep DD (Claude Opus, extended thinking) → 1-3 stocks       │
│          └── OUTPUT: signals.json, portfolio.csv, newsletter_briefing.md │
│                                                                          │
│  Step 2: distribution/notifications.py                                   │
│          └── Email (SMTP) + WhatsApp (Twilio) scan summary alerts        │
│                                                                          │
│  Step 3: content/funnel_graphic.py                                       │
│          └── twitter/output/charts/funnel_graphic.png (1200×675px)        │
│                                                                          │
│  Step 4: content/chart_capture.py --tickers-from signals.json            │
│          └── twitter/output/charts/*.png (1400×900 X + 1000×700 Substack)│
│                                                                          │
│  Step 5: content/market_analyzer.py --save                               │
│          └── scanner/output/current/market_analysis.md (Claude + web search)│
│                                                                          │
│  Step 5.5: content/content_production_guide.py                           │
│            └── substack/output/current/content_production_guide.md       │
│                (DATA + SCHEDULE context doc — no prompts)                │
│                                                                          │
│  Step 6: content/newsletter_compiler.py --from-html                      │
│          └── substack/output/current/newsletter.html                     │
│                                                                          │
│  Step 7: content/dd_post_generator.py                                    │
│          └── substack/output/current/substack_posts/dd_TICKER.html (per signal)│
│                                                                          │
│  Step 8: content/substack_content_generator.py --all                    │
│          └── substack/output/current/substack_posts/*.html (4-5 posts/week)│
│                                                                          │
│  Step 9: content/portfolio_visual.py                                     │
│          └── substack/output/current/portfolio_visual.html               │
│                                                                          │
│  Step 10: content/tweet_generator.py --signals --portfolio --account all │
│           └── twitter/output/content_queue*.json (3 accounts, slots 2-5) │
│                                                                          │
│  Step 11: content/substack_notes_batch_generator.py                     │
│           └── substack/output/current/substack_notes/*.md (21 notes, 3/day)│
│                                                                          │
│  Step 12: git add scanner/ portfolio/ substack/ twitter/ && git commit && git push│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

Cost: ~$2-4 total (scanner $1-3 + content $0.50-1.00)
```

## DAILY PIPELINE (Mon-Fri, 4:35 PM ET)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   DAILY PIPELINE — 5 Steps                               │
│              GitHub Actions (daily_scan.yml), Mon-Fri                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: core/daily_scanner.py                                           │
│          ├── Daily HMA Pivot BUY + Beta ≥1.5 + Banker Rising             │
│          ├── Max 5 signals/day, dedup vs weekly portfolio                │
│          └── OUTPUT: daily_signals.json, daily_portfolio.csv             │
│                                                                          │
│  Step 2: distribution/notifications.py (sell alerts only)                │
│                                                                          │
│  Step 3: content/chart_capture.py --daily                                │
│          └── twitter/output/charts/*.png (daily timeframe)               │
│                                                                          │
│  Step 4: content/tweet_generator.py --daily --account all                │
│          └── twitter/output/daily_content_queue*.json (3 accounts, slots 1/6/7)│
│                                                                          │
│  Step 5: git add scanner/ portfolio/ twitter/ && git commit && git push  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

Cost: ~$0.10-0.30 per run
```

## LIVE TWEET PIPELINE (5-10x/day, market hours)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  LIVE TWEET PIPELINE — 3 Steps                           │
│              GitHub Actions (live_tweet.yml), 5-10x/day                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: content/live_context_gatherer.py                                │
│          ├── Queries xAI Grok via Responses API                          │
│          ├── Tools: X Search + Web Search                                │
│          └── OUTPUT: twitter/output/live_context.json                    │
│                  ├── market_snapshot (SPY/QQQ, VIX, breadth)            │
│                  ├── portfolio_movers (current prices, alerts)           │
│                  ├── theme_activity (trending sectors)                   │
│                  └── fintwit_trending (sentiment, topics)                │
│                                                                          │
│  Step 2: content/live_tweet_generator.py                                 │
│          ├── RecentTweetTracker → diversity enforcement                  │
│          ├── P0-P10 priority decision system                             │
│          ├── 3-variant generation per account                            │
│          ├── 14-step validation + repair loop                            │
│          └── OUTPUT: twitter/output/live_content_queue.json              │
│                                                                          │
│  Step 3: distribution/twitter_poster.py --live-queue                    │
│          ├── Account 1 → variant_1 of each slot                         │
│          ├── Account 2 → variant_2 (10 min stagger)                     │
│          └── Account 3 → variant_3 (20 min stagger)                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

Cost: ~$0.50-2.00/day
```

## BATCH TWEET POSTING PIPELINE (7-Slot System)

```
┌──────────────────────────────────────────────────────────────────────────┐
│              7-SLOT BATCH TWEET POSTING SCHEDULE                         │
│              GitHub Actions (daily_post.yml) — CRON DISABLED             │
├──────────────┬───────────┬────────────────────┬────────────────────────┤
│   Slot       │  Time ET  │  Queue Source       │  Content Type          │
├──────────────┼───────────┼────────────────────┼────────────────────────┤
│  Slot 1      │  07:30    │  daily_queue        │  Pre-market signals    │
│  Slot 2      │  10:00    │  weekly_queue       │  Theme/signal analysis │
│  Slot 3      │  12:30    │  weekly_queue       │  Position update       │
│  Slot 4      │  15:30    │  weekly_queue       │  POWER HOUR (critical) │
│  Slot 5      │  18:00    │  weekly_queue       │  Engagement/lessons    │
│  Slot 6      │  17:00    │  daily_queue        │  Post-close recap      │
│  Slot 7      │  18:30    │  daily_queue        │  Daily overflow        │
└──────────────┴───────────┴────────────────────┴────────────────────────┘

3 accounts posted 10 minutes apart per slot.
Slots 1/6/7 → daily_content_queue.json (fresh intraday)
Slots 2-5   → content_queue.json (Friday-generated weekly)
```

## THREE-LAYER VALIDATION ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  MARKETING SAFETY — THREE LAYERS                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LAYER 1 — DATA LAYER (before generation)                                │
│  ├── ContentData only includes winners ≥15% P&L                          │
│  ├── Entry prices shown only for positions ≥25% gain                     │
│  ├── STOPPED positions never included                                    │
│  └── sell_signals use "setup invalidated" framing only                   │
│                                                                          │
│  LAYER 2 — GENERATION LAYER (during LLM generation)                     │
│  ├── sanitize_text() — 70+ internal→marketing term replacements          │
│  ├── scrub_llm_output() — strips negative P&L regex, STOPPED mentions   │
│  └── LLM system prompts embed all marketing rules + 104 banned terms     │
│                                                                          │
│  LAYER 3 — POST-GENERATION VALIDATION (after generation)                │
│  ├── validate_tweet() — 7-step pipeline (tweets)                         │
│  │   1. Length ≤280 chars                                                │
│  │   2. 104 CRITICAL_BANNED terms scan                                   │
│  │   3. Data accuracy (tickers/prices match source)                      │
│  │   4. Loser focus (9 regex patterns)                                   │
│  │   5. Conviction language (no numeric scores)                          │
│  │   6. Chart requirement check                                           │
│  │   7. Marketing compliance                                              │
│  ├── validate_post_content() — Substack posts                            │
│  ├── validate_before_posting() — LAST LINE before X posting              │
│  └── Repair loop: LLM repair → max 2 attempts → drop + log              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

# TIER 1 — CORE CONTENT SYSTEM (PRIMARY SUBSTACK GENERATION)

Files: substack_content_generator.py, substack_notes_batch_generator.py,
       content_production_guide.py, newsletter_compiler.py,
       dd_post_generator.py, html_templates.py, learning_content_library.py

---

## FILE: content/substack_content_generator.py
## Purpose: 8-type Substack post generator (4-5 posts/week via LLM)
## LLM: Claude Sonnet 4, cost ~$0.06-0.12 per post

Key structures:
- PostSpec dataclass: post_type, title, publish_day, filename, template_theme, priority
- ContentContext dataclass: signals, themes, buy_signals, assessed_signals, portfolio_stats, winners, benchmark, theme_details, theme_history, chart_manifest
- TEMPLATE_MAP: maps 8 post types to (HTML theme, builder_function)
- 8 builder functions: build_weekly_recap_prompt(), build_theme_deep_dive_prompt(), build_dd_deep_dive_prompt(), build_portfolio_spotlight_prompt(), build_stock_deep_dive_prompt(), build_quick_take_prompt(), build_portfolio_showcase_prompt(), build_educational_prompt()
- Data formatters: _format_themes_for_prompt(), _format_signals_for_prompt(), _format_winners_for_prompt(), _format_assessed_for_prompt(), _format_equity_stats(), _format_theme_history()
- Safety functions: sanitize_text(), scrub_llm_output(), validate_post_content()
- Visual injection: inject_visual_elements() — replaces [SCAN_FUNNEL], [THEME_SCORES], [WINNERS_TABLE] placeholders

Content calendar logic (determine_content_calendar):
- When PASS > 0: Saturday=WeeklyRecap, Tuesday=DDDeepDive, Wednesday=ThemeDeepDive, Thursday=StockDeepDive
- When PASS = 0: Saturday=WeeklyRecap(selectivity), Tuesday=StockDeepDive, Wednesday=ThemeDeepDive, Thursday=PortfolioShowcase

System prompt enforces: GREEN signal branding, 104 banned terms, entry price rules (≥25% only), winners-only, approved marketing vocabulary

---

## FILE: content/substack_notes_batch_generator.py
## Purpose: 21 Substack Notes/week (3/day × 7 days) with dedup tracking
## LLM: Claude Sonnet 4, cost ~$0.01-0.02 per note

Key structures:
- 7 note types: PORTFOLIO_PULSE, SIGNAL_ALERT, THEME_MOMENTUM, MARKET_REACTION, SYSTEM_PROOF, LEARNING_NUGGET, ENGAGEMENT_HOOK
- WEEKLY_NOTES_SCHEDULE (fixed rotation, see below)
- DedupTracker: max 3 ticker uses/week, max 4 theme uses/week
- 60+ engagement hooks organized by type (rotated, no repeats)
- 7 builder functions: build_portfolio_pulse_prompt() through build_engagement_hook_prompt()
- 7 template fallbacks for --no-llm mode

WEEKLY_NOTES_SCHEDULE:
  Saturday:  PORTFOLIO_PULSE (08:30), THEME_MOMENTUM (12:30), ENGAGEMENT_HOOK (17:30)
  Sunday:    LEARNING_NUGGET (09:00), ENGAGEMENT_HOOK (13:00), MARKET_REACTION (17:00)
  Monday:    MARKET_REACTION (08:30), SYSTEM_PROOF (12:30), PORTFOLIO_PULSE (17:30)
  Tuesday:   SIGNAL_ALERT (08:30), THEME_MOMENTUM (12:30), ENGAGEMENT_HOOK (17:30)
  Wednesday: MARKET_REACTION (08:30), PORTFOLIO_PULSE (12:30), LEARNING_NUGGET (17:30)
  Thursday:  THEME_MOMENTUM (08:30), SIGNAL_ALERT (12:30), ENGAGEMENT_HOOK (17:30)
  Friday:    MARKET_REACTION (08:30), SYSTEM_PROOF (12:30), PORTFOLIO_PULSE (17:30)

System prompt: Medical-investor voice, 150-300 words, no markdown headers, no bullet lists, flowing paragraphs, sparse emoji, end with "Not financial advice. Informational only."
Output: substack/output/current/substack_notes/*.md (21 files) + notes_manifest.json

---

## FILE: content/content_production_guide.py
## Purpose: Weekly DATA + SCHEDULE context doc for Claude.ai chats (NO prompts)
## LLM: None ($0)

4 category constants:
  CATEGORY_TICKER_DIVE = "TICKER_DEEP_DIVE"
  CATEGORY_EDUCATIONAL = "EDUCATIONAL"
  CATEGORY_THEME_ROTATION = "THEME_ROTATION"
  CATEGORY_PERFORMANCE_REVIEW = "PERFORMANCE_REVIEW"

Schedule builder logic:
  - Sunday → always PERFORMANCE_REVIEW
  - Mon-Fri → assigns based on data:
    * New GREEN signals → TICKER_DEEP_DIVE (names ticker)
    * Active themes (PRIME/INVESTABLE or score ≥6.0) → THEME_ROTATION (names theme)
    * Remaining → EDUCATIONAL (prompt searches web for topic)
    * No consecutive same-category days
    * Minimum 1 EDUCATIONAL day guaranteed

4 output sections:
  1. System Context — identity, voice, marketing rules, HTML specs, banned terms
  2. This Week's Data — scanner results, themes+catalysts, signals, portfolio, winners, benchmarks, market analysis
  3. Weekly Schedule — day→category→topic→handbook reference
  4. How to Use — brief instructions

Output: substack/output/current/content_production_guide.md (~17,000 chars)
Companion: docs/content_prompt_handbook_v5.md (permanent, prompts live here)

---

## FILE: content/newsletter_compiler.py
## Purpose: Sunday newsletter compilation — data + LLM → publication-ready HTML
## LLM: Claude Sonnet 4, cost ~$0.06-0.12

Key functions:
  load_dd_results() — extracts all Deep DD fields: elevator_pitch, why_now, the_math, bear_case, risk_to_monitor, action
  load_theme_details() — builds sub-score table: Catalyst(40%), Momentum(25%), Crowding(20%), Runway(15%)
  generate_benchmark_comparison() — portfolio vs SPY vs QQQ since inception + max drawdown
  markdown_to_html() — reused by substack_content_generator.py

COMPILATION_SYSTEM prompt excerpt:
  "Use GREEN signal branding. Never mention losing positions. Only showcase wins ≥15%.
  Zero-signal weeks focus on selectivity, themes, and watchlist stocks."

Newsletter structure (8-12 min read):
  1. Title + hook
  2. Market context (from market_analysis.md)
  3. Hot themes (PRIME, INVESTABLE — with sub-score detail)
  4. Cold themes (SELECTIVE, AVOID)
  5. New trades with full DD OR selectivity narrative
  6. Signals that failed DD
  7. Watchlist (CONSIDER)
  8. Win highlights (conditional on ≥15% gains)
  9. Looking ahead (catalysts)
  10. Footer + disclaimer

Output: substack/output/current/newsletter.html + weekly archive copy

---

## FILE: content/dd_post_generator.py
## Purpose: Standalone dark-theme HTML pages per buy signal (Deep DD content)
## LLM: None ($0 — data-only rendering)

Sections rendered:
  The Pitch (elevator_pitch), Why Now, The Math, Bear Case,
  Risk to Monitor, Theme Context (progress bars for sub-scores),
  Investment Gate Summary, Action card (colour-coded GREEN/YELLOW/RED)

Safety: sanitizes via INTERNAL_TERMINOLOGY_MAP (70+ mappings)
Optional: Playwright PNG screenshots (Substack + Twitter sizes)
Output: substack/output/current/substack_posts/dd_TICKER.html

---

## FILE: content/html_templates.py
## Purpose: Centralized HTML template system — 2 design themes

EDITORIAL_COLORS (light theme — for long-form stock/educational posts):
  bg: #fafaf8, container: #fff, text: #1a1a1a, muted: #6b6b6b
  Serif headings: Georgia, Times New Roman
  Price target bands: Bear #fdf6f4/#8b3a1a, Base #f4f7fa/#1b3a5c, Bull #f4faf5/#2e5e3e
  Table header: #2c2520 / text #f0ebe4

DASHBOARD_COLORS (dark theme — for scanner/performance/rotation posts):
  bg: #111827, card: #1F2937, teal: #2DD4BF, green: #22C55E
  Sans-serif, gold: #F59E0B, red: #EF4444, violet: #A78BFA
  Borders: #374151, header: #0F172A

Key template functions:
  editorial_wrap(content, title, subtitle) → full editorial HTML page
  editorial_masthead(newsletter, edition, date) → top banner
  editorial_target_banner(bear, base, bull) → 3-column price target display
  dashboard_wrap(content, title) → full dashboard HTML page
  dashboard_hero(headline, subtext, badge) → dark hero banner
  dashboard_stat_grid(stats_list) → 3-col grid of key metrics
  footer_cta(url, label) → CTA button
  disclaimer() → regulatory disclaimer text

---

## FILE: content/learning_content_library.py
## Purpose: 20 educational topics across 5 categories for LEARNING_NUGGET notes + EDUCATIONAL posts

5 Categories × 4 topics each:
  Risk Management: Position Sizing, Trailing Stops, Max Drawdown Math, Cash as Ammunition
  Momentum: Structural Momentum, Institutional Accumulation, Sector Rotation, Market Breadth
  Fundamentals: Catalyst Investing, Revenue Acceleration, Theme Alignment, Small-Cap Edge
  Psychology: Patience Over FOMO, Systematic Discipline, Loss Acceptance, Compounding Math
  Strategy: Screening Advantage, Theme Surfing, When to Sell, Concentration vs Diversification

Each topic dict contains:
  hook, key_concept, example, engagement_question,
  note_template (150-250 words — ready to post directly),
  post_outline (section headings for full 1200-word article),
  tags

Key functions:
  LEARNING_TOPICS — full list of 20 dicts
  get_random_topic(exclude_used=[]) — dedup-aware random selection
  get_topics_by_category(category) — filter by category
  get_topic_by_name(name) — lookup by name

---

# TIER 2 — CONFIGURATION & SAFEGUARDS

Files: config/banned_terms.py, config/settings.py,
       config/marketing_vocabulary.py, config/output_paths.py

---

## FILE: config/banned_terms.py
## Purpose: Single source of truth for all marketing compliance terms

CRITICAL_BANNED (104 terms) — grouped by category:

  Internal indicators:
    HMA, Hull Moving Average, Banker, Banker Rising, UC, Undercurrent, UC indicator,
    BoS, Break of Structure, RSI, MACD, KDJ, VWAP, ExD, profit lock, tiered stop,
    gear shift, price cap, $25 cap, Beta >= 1.5, 20% trailing stop, HMA slope,
    HMA pivot, HMA fracture, bos bullish, bos bearish, weekly bos, monthly bos,
    institutional accumulation divergence (internal framing), UC rising

  System terms:
    Gatekeeper, Investment Gate, Deep DD, 5-gate, 5th Gate, Gate 1, Gate 2, Gate 3,
    Gate 4, Gate 5, Tier 1, Tier 2, Tier 3, conviction score, conviction 1-10,
    conviction 8, conviction 9, conviction 10, STRONG BUY, SPEC BUY, NO GO,
    theme scoring, kill switch, Sterling Grid, sterling grid

  Old branding:
    TEAL signal, VIOLET signal, AMBER signal, TEAL Signal, VIOLET Alert,
    🟣 emoji, old color system references

  Geography:
    UK ISA, ISA account, GMT, BST, UK Time, Roth IRA (appears in public content),
    PDT, 401(k)

BANNED_PHRASES (15):
  "theme keeps delivering", "system keeps working", "trust the process",
  "some interesting setups", "still bleeding", "loser", "dragging down",
  "underwater", "bag holding", "bagholding", "down bad", "in the red",
  "cut losses", "stop out", "got stopped"

LOSER_PATTERNS (9 regex):
  Patterns detecting emphasis on losing positions:
    r"[-−]\d+\.?\d*%", r"down \d+", r"lost \$\d+",
    r"stop.{0,10}hit", r"stoppedout", etc.

INTERNAL_TERMINOLOGY_MAP (70+ mappings):
  "BoS bullish" → "momentum confirmed"
  "Banker >= 55" → "institutional accumulation"
  "TEAL signal" → "GREEN signal"
  "Gatekeeper" → "Forensic Audit"
  "Investment Gate" → "5th Gate"
  "Deep DD" → "Forensic analysis"
  "HMA slope rising" → "Structural Pivot Confirmation"
  "UC rising" → "Institutional Accumulation Divergence"
  "ExD exit" → "Structural exit"
  "20% trailing stop" → "Capital Preservation Protocol"
  etc. (70+ total)

Helper functions:
  check_banned_phrases(text) → List[str] of found violations
  check_loser_focus(text) → bool (True if loser patterns found)

---

## FILE: config/settings.py (~1340 lines)
## Purpose: All system constants, thresholds, schedules, branding

Key content constants:
  SIGNAL_BRAND = "GREEN signal"
  MODEL_SONNET = "claude-sonnet-4-20250514"
  MODEL_OPUS = "claude-opus-4-20250514"
  MODEL_NOTES = "claude-sonnet-4-20250514"
  MODEL_LIVE_TWEET = "claude-sonnet-4-5-20250929"

  CONVICTION_LANGUAGE = {
    range(8, 11): "Extremely Bullish",
    7: "Bullish",
    range(4, 7): "Watching",
    range(1, 4): None  # Don't post
  }

  MARKETING_THRESHOLDS = {
    'min_win_to_highlight': 15.0,
    'big_win_threshold': 25.0,
    'home_run_threshold': 50.0,
    'hall_of_fame_threshold': 100.0,
    'spy_outperformance_min': 5.0,
    'min_winners_for_top_performers': 2,
  }

  ENTRY_PRICE_RULES: show at ≥25% gain OR closed winners (always)
  STOPPED_POSITION_RULES: never show in public content

  CELEBRATION_THRESHOLDS = [25.0, 50.0, 100.0]
  CELEBRATION_KEYS = {25.0: "big_win_25", 50.0: "home_run_50", 100.0: "hall_of_fame_100"}

  KILLED_CATEGORIES = ['roth_ira', 'pdt_friendly', 'position_update', 'weekly_wins']
  SAFEGUARDED_CATEGORIES = {
    'top_performers': requires 2+ winners ≥15%,
    'beat_spy': portfolio must outperform SPY by 5%+,
    'self_quote': needs uncelebrated milestone,
    'closed_trade': needs profitable closed trades,
  }

  Sterling Grid position sizing:
    CONVICTION_TIERS = {
      range(8, 11): {'pct': 20.0, 'label': 'HIGH'},
      7: {'pct': 15.0, 'label': 'STANDARD'},
      range(4, 7): {'pct': 8.0, 'label': 'SPEC'},
    }
    MAX_POSITIONS = 6
    CASH_RESERVE_PCT = 10.0

  Sterling Grid indicators:
    HMA_PERIOD = 21
    RSI_PERIOD = 14
    MACD_FAST = 12, MACD_SLOW = 26, MACD_SIGNAL = 9
    TRAILING_STOP_PCT = 20.0
    LOCK_TIERS = [(2.00, 0.15), (1.00, 0.20), (0.50, 0.25)]
      # (+200% → 15% trail), (+100% → 20% trail), (+50% → 25% trail)

  BRANDING = {
    'name': 'Sterling Signals',
    'substack_url': 'https://sterlingsignals.substack.com',
    'twitter_main': '@AlexSterlingGBR',
  }

  get_conviction_text(score) → public language string
  can_show_entry_price(position) → bool

---

## FILE: config/marketing_vocabulary.py (~520 lines)
## Purpose: Approved vocabulary validation for content

Key functions:
  validate_content(text) → ValidationResult(valid, violations, warnings)

Checks for:
  - Required positive framing terms
  - Forbidden negative language patterns
  - US audience appropriateness
  - Approved signal language

Note: Partially deprecated — banned_terms.py is the authoritative source.
Still used by substack_content_generator.py and twitter_poster.py as
an additional validation layer.

---

## FILE: config/output_paths.py (~270 lines)
## Purpose: Centralized folder structure management

Key paths:
  BASE_DIR = project root
  SCANNER_OUTPUT = scanner/output/
  PORTFOLIO_OUTPUT = portfolio/output/
  SUBSTACK_OUTPUT = substack/output/
  TWITTER_OUTPUT = twitter/output/
  SCANNER_CURRENT = scanner/output/current/
  SUBSTACK_CURRENT = substack/output/current/
  CHARTS_DIR = twitter/output/charts/
  SUBSTACK_POSTS_DIR = substack/output/current/substack_posts/
  SUBSTACK_NOTES_DIR = substack/output/current/substack_notes/
  SCANNER_ARCHIVE = scanner/output/archive/
  SUBSTACK_ARCHIVE = substack/output/archive/

Key functions:
  ensure_output_structure() → creates all dirs
  get_current_dir() → scanner/output/current/
  get_week_dir(date) → scanner/output/archive/YYYY-WXX/
  get_relative_path(abs_path) → path relative to BASE_DIR
  save_to_current_and_archive(content, filename, subdir) → dual-writes
  list_weekly_archives() → sorted list of week dirs

---

# TIER 3 — OVERLAPPING CONTENT GENERATORS

Files: content/tweet_generator.py, content/market_analyzer.py,
       content/models.py, content/substack_notes_generator.py (legacy)

---

## FILE: content/tweet_generator.py (~900 lines)
## Purpose: Batch tweet generation for 3 accounts (weekly + daily)
## LLM: Claude Sonnet 4, cost ~$0.30-0.60 per full run

TWEET_CATEGORIES (18 categories):
  SCANNER_RESULT, DAILY_SIGNAL, THEME_ANALYSIS, PERFORMANCE, WATCHLIST,
  TECHNICAL_ANALYSIS, EDUCATIONAL, MARKET_COMMENTARY, SELL_SIGNAL,
  ENGAGEMENT, NEWSLETTER_CTA, MARKET_REACTION, RECEIPT, SIGNAL_ALERT,
  DIP_OPPORTUNITY, THEME_MOMENTUM, MARKET_OPEN, MARKET_CLOSE

ACCOUNT_QUEUES (3 accounts):
  main → twitter/output/content_queue.json
  account2 → twitter/output/content_queue_account2.json
  account3 → twitter/output/content_queue_account3.json

WEEKLY_SLOTS = [2, 3, 4, 5] (slots 1/6/7 reserved for daily queue)

CATEGORY_WEEKLY_LIMITS:
  EDUCATIONAL: 3, ENGAGEMENT: 4, WATCHLIST: 2, THEME_ANALYSIS: 8,
  SCANNER_RESULT: 3, PERFORMANCE: 7, MARKET_COMMENTARY: 3, etc.

DATA_DEPENDENT_CATEGORIES: {SCANNER_RESULT, SELL_SIGNAL, DAILY_SIGNAL, PERFORMANCE, TECHNICAL_ANALYSIS, WATCHLIST}

EMBEDDED_STYLE_GUIDE (250 lines):
  FinTwit voice, category examples, winners-only rules, power phrases,
  CLOSING_CTA_OPTIONS list (14 CTAs), required data per category

Key functions:
  _plan_weekly_schedule(data) → 7-day × 4-slot assignment plan
  _pick_category(slot, day, data, counts, ...) → category + data_key
    Priority chains: slot 2 Saturday = SCANNER_RESULT, slot 4 = PERFORMANCE/POWER HOUR, etc.
    Terminal fallbacks prevent empty slots
  _build_content_data(signals_path, portfolio_path) → ContentData
    - Fetches live prices via yfinance
    - winners (≥25%), notable_holdings (10-25%), holdings (0-10%)
    - Never includes losers
  _build_system_prompt(style_guide) → embedded with all banned terms
  _build_user_prompt(category, slot_data, slot, recent_openings, recent_closings) → data-rich prompt
  _validate_tweet(tweet) → ValidationResult (7 checks)
  _repair_tweet(tweet, failures, prompt) → LLM repair attempt
  generate_tweet(slot, data, account, recent_openings) → Tweet | None

7-step validation pipeline:
  1. Length ≤280 chars
  2. 104 CRITICAL_BANNED terms
  3. Data accuracy (tickers/prices match source data)
  4. Loser focus (9 regex patterns)
  5. Conviction language (no numeric scores)
  6. Chart requirement check (CHART_REQUIRED_CATEGORIES)
  7. Marketing compliance

Safeguarded category checks:
  top_performers → needs 2+ winners ≥15% (via has_enough_wins())
  beat_spy → portfolio must outperform SPY by 5%+ (matched holding periods)
  self_quote → needs uncelebrated 25/50/100% milestone
  closed_trade → needs profitable closed trades in last 14 days

Repair loop: max 2 LLM attempts → if still failing → drop + log to failed_tweets.json

MAX_PORTFOLIO_POOL_PER_DAY = 4 (limits same-position mentions per day)

---

## FILE: content/market_analyzer.py
## Purpose: Market context section generation (Claude + web search)
## LLM: Claude Sonnet 4, cost ~$0.05-0.09

System prompt: Senior analyst voice, specific numbers, connect macro to momentum implications.

5 web searches performed:
  1. Index performance (SPY, QQQ, IWM last 5 days)
  2. Key market events (Fed decisions, economic data, earnings)
  3. Sector rotation (leaders/laggards this week)
  4. Volatility + sentiment (VIX, put/call ratios)
  5. Upcoming catalysts (next 2 weeks)

Output format: 3-4 paragraph market context section
Output: scanner/output/current/market_analysis.md

---

## FILE: content/models.py
## Purpose: Shared data classes across content modules

Key dataclasses:
  Tweet:
    id, text, category, ticker, chart_path,
    scheduled_date, slot, status, posted_at, tweet_id, block_reason
    status values: 'pending', 'posted', 'blocked', 'expired', 'skipped'

  ContentData:
    pass_signals, consider_signals, sell_signals
    themes, winners, notable_holdings, holdings
    market_data, educational, engagement, newsletter_url
    has_signals, has_themes, has_winners (booleans)

  SlotAssignment:
    day, slot, category, data_key, account

  ValidationResult:
    valid (bool), violations (List[str]), warnings (List[str])

CHART_REQUIRED_CATEGORIES = {'SCANNER_RESULT', 'PERFORMANCE', 'RECEIPT', 'TECHNICAL_ANALYSIS'}
INTERNAL_TERM_PATTERNS — regex for internal terms in tweet text

---

## FILE: content/substack_notes_generator.py (legacy, 2-note system)
## Purpose: Original Tuesday/Thursday note generator — still called as fallback

Key reused functions (imported by substack_notes_batch_generator.py):
  NoteContext dataclass: winners, themes, signals, stats, week_date, market_analysis
  build_note_context(signals_path, portfolio_path) → NoteContext
  sanitize_note(text) → marketing-safe note text
  validate_note(text) → ValidationResult
  repair_note(text, failures, client) → repaired note
  save_note(content, filename, output_dir) → Path
  ensure_output_dirs() → creates substack_notes/ dirs
  get_current_dir() → substack/output/current/

Output (legacy): substack/output/current/substack_notes/tuesday_note.md,
                  substack/output/current/substack_notes/thursday_note.md

---

# TIER 4 — DISTRIBUTION LAYER

Files: distribution/twitter_poster.py, content/live_tweet_generator.py,
       content/live_context_gatherer.py

---

## FILE: distribution/twitter_poster.py (~1089 lines)
## Purpose: Unified X/Twitter posting engine (batch + live, 3 accounts)

Queue routing:
  Slots 1, 6, 7 → daily_content_queue.json
  Slots 2-5 → content_queue.json
  --live-queue → live_content_queue.json

LIVE_ACCOUNT_MAP:
  main → variant_1, account2 → variant_2, account3 → variant_3

3-account credential pattern:
  main:     X1_API_KEY, X1_API_SECRET, X1_ACCESS_TOKEN, X1_ACCESS_SECRET
  account2: X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET
  account3: X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET

get_clients(account) → (tweepy.Client v2, tweepy.API v1.1)
  v2: posting tweets (OAuth 1.0a)
  v1.1: media upload (images)

validate_before_posting(tweet_text, category) — LAST LINE OF DEFENSE:
  1. Check negative P&L (losers) → BLOCK
  2. Check CRITICAL_BANNED terms → BLOCK
  3. Check old color system (TEAL/VIOLET) → BLOCK
  4. Check killed categories → BLOCK
  5. Full marketing vocabulary check
  6. Tweet length ≤280 chars

find_next_content(account, slot, target_date) → Tweet | None
  - Slot-aware routing (daily vs weekly queue)
  - Staleness check: >3 days = expired
  - Today/current-slot gating (don't post future slots)

is_duplicate_content(text) → bool (exact match)
check_similarity_duplicate(text, window_hours=24) → bool (≥70% similarity)

post_tweet(account, tweet, client, api) → str (tweet_id)
  - Validates → uploads up to 4 images (v1.1 API) → posts (v2 API)
  - 3 retry attempts with exponential backoff

post_thread(account, tweets, client, api) → List[str]
  - 5-tweet chain via reply chaining (in_reply_to_tweet_id)

post_quote_tweet(account, tweet_text, quote_tweet_id, client) → str
  - Quote-tweet for milestone celebrations (25/50/100% gains)

find_next_live_content(account) → Tweet | None
  - Reads live_content_queue.json
  - Maps account → variant (variant_1/2/3)
  - Posts pending variants in chronological order

Atomic queue writes: write to temp file → rename (prevents corruption)
Duplicate detection: exact text + SequenceMatcher 0.7 threshold in 24h window

---

## FILE: content/live_tweet_generator.py (~2029 lines)
## Purpose: Real-time tweet generation based on live Grok market context
## LLM: Claude Sonnet 4.5

LIVE_VALID_CATEGORIES (11):
  MARKET_REACTION, RECEIPT, SIGNAL_ALERT, DIP_OPPORTUNITY, THEME_MOMENTUM,
  ENGAGEMENT, EDUCATIONAL, NEWSLETTER_CTA, SELL_SIGNAL, TECHNICAL_ANALYSIS, WATCHLIST

LIVE_CATEGORY_EXAMPLES: 11 categories × 2 reference examples each

RecentTweetTracker class (diversity enforcement):
  - Scans existing live_content_queue.json at startup
  - Tracks: tickers_today, categories_today, categories_this_week
  - Tracks: recent_openings (dedup opening sentences)
  - Tracks: recently_used_phrases (cooldown list)
  - Enforces: daily ticker caps, weekly category budgets

get_diverse_tickers(n, exclude):
  - Time-based deterministic rotation (hour//3 % len)
  - Different tickers at different times of day
  - Falls back to EDUCATIONAL/ENGAGEMENT when <3 unique tickers

decide_tweet_type(context, tracker) → category (P0-P10 priority):
  P0: SELL_SIGNAL (if exit signals exist)
  P1: SIGNAL_ALERT (if new GREEN signals)
  P2: RECEIPT (if portfolio mover >3%)
  P3: MARKET_REACTION (if market data fresh)
  P4: THEME_MOMENTUM (if trending theme)
  P5: TECHNICAL_ANALYSIS (if chart signal)
  P6: WATCHLIST (if consider signals)
  P7: SIGNAL_ALERT again (Grok tweet opportunities)
  P8: NEWSLETTER_CTA (if not used today)
  P9: Multi-RECEIPT (multiple movers)
  P10: ENGAGEMENT or EDUCATIONAL (filler)

build_system_prompt(account, tracker) → persona + cooldown enforcement
build_user_prompt(context, slot_assignments, time_context) → full data prompt

14-step validate_tweet() pipeline:
  step1: category validity
  step2: ticker fabrication check (must match source data)
  step3: banned terms
  step4: winners-only rule
  step5: internal terminology
  step6: length ≤280 chars
  step6b: opening sentence diversity (no repeated opening words)
  step7: chart flag in tweet (CHART_REQUIRED_CATEGORIES)
  step8: cross-account dedup (check all 3 account queues)
  step8.5: slot collision detection
  step9: staleness check
  step9b: queue dedup 48h window 80% similarity threshold
  step10: daily ticker repetition cap
  step11: meta-language detection ("In this tweet...", "As an AI...")
  step12: portfolio fabrication detection
  step14: defeatist language detection

repair_tweet(tweet, failures, system_prompt, user_prompt) → repaired text

write_to_live_queue(tweets, account):
  - Atomic write
  - _prune_queue(): 7-day retention for non-pending items

generate_live_tweet(account):
  - load context → track existing queue → decide type → assign slots
  - call Claude Sonnet (3 variants per call, 1 per account)
  - validate (14 steps) → repair if needed → write to queue

---

## FILE: content/live_context_gatherer.py (~532 lines)
## Purpose: Real-time market context via xAI Grok Responses API
## LLM: xAI Grok

ContextResult dataclass: context_data, cost, error, stale (bool)

is_market_open() → bool (9:30-16:00 ET weekdays)
is_extended_hours() → bool (7:00-9:30 or 16:00-18:30 ET)

CONTEXT_SYSTEM_PROMPT → structured JSON output:
  market_snapshot: {spy_change, qqq_change, vix_level, breadth, sector_rotation}
  portfolio_movers: [{ticker, price, change_pct, catalyst}]
  theme_activity: [{theme, momentum, etf_performance, catalyst}]
  fintwit_trending: [{topic, sentiment, volume}]
  news_events: [{headline, impact, relevance}]
  tweet_opportunities: [{type, ticker_or_theme, hook}]

gather_live_context(portfolio_path, signals_path) → ContextResult
  - MAX_RETRIES = 2, exponential backoff (5s, 15s)
  - Falls back to: stale context (<CONTEXT_STALENESS_HOURS old) → portfolio-only fallback

build_fallback_context() → minimal context from portfolio.csv (no API call)
check_stale_context() → age check on live_context.json
save_context(data) → writes with gathered_at, is_market_hours, is_extended_hours

---

# TIER 5 — STANDALONE SUPPORT MODULES

Files: content/portfolio_visual.py, content/chart_capture.py,
       content/funnel_graphic.py, distribution/notifications.py,
       distribution/signal_tracker.py

---

## FILE: content/portfolio_visual.py (~820 lines)
## Purpose: Dark-themed HTML portfolio dashboard + optional PNG screenshots

COLORS:
  teal: #2DD4BF, teal_bg: #0D3B34, violet: #A78BFA
  green: #22C55E, red: #EF4444, dark_bg: #111827, card_bg: #1F2937

_generate_equity_curve_svg(snapshots) → inline SVG:
  - 3 polylines: Portfolio (teal 2.5px), SPY (muted 1.5px), QQQ (violet 1.5px)
  - Grid lines, zero line, date labels, legend
  - Requires ≥2 equity snapshots

generate_dashboard_html(portfolio_manager, signals) → HTML string:
  - 6-stat grid: NAV, Return %, Win Rate, Alpha vs SPY, Alpha vs NASDAQ, Max Drawdown
  - Equity curve SVG (Portfolio/SPY/QQQ polylines)
  - Open positions table (7 cols: Ticker, Theme, Entry, Current, Held, P&L %, Stop Dist)
  - Recent exits table

EXIT_REASON_MAP: internal→marketing-safe exit reasons
  "Weekly BoS Down" → "Structural exit"
  "20% trailing stop" → "Capital Preservation Protocol activated"

capture_dashboard_screenshot(html_path) → Playwright PNG:
  - 1400×900 (X/Twitter card)
  - 1000×700 (Substack embed)

save_dashboard(html_content) → dual-write:
  - substack/output/current/portfolio_visual.html
  - substack/output/archive/YYYY-WXX/portfolio_visual.html

_validate_dashboard(html) → runs through marketing_vocabulary validator

---

## FILE: content/chart_capture.py (~750 lines)
## Purpose: TradingView screenshots with custom Sterling Grid indicators

TRADINGVIEW_LAYOUT_ID = os.environ.get("TRADINGVIEW_LAYOUT_ID", "rxC5j0SK")
PLAYWRIGHT_USER_DATA_DIR = .playwright_profile/ (persistent session)

Chart sizes:
  CHART_SIZE_X = (1400, 900)        # X/Twitter card
  CHART_SIZE_SUBSTACK = (1000, 700) # Substack embed

HIDE_UI_ELEMENTS_JS:
  Hides: right-side panels, drawing toolbar, cookie consent
  Preserves: indicator visuals (chart panes), indicator lines (marketing feature)

capture_chart(page, ticker, output_dir, date_str, timeframe='weekly') → List[Path]:
  - URL format: tradingview.com/chart/{LAYOUT_ID}/?symbol={ticker}&interval={W|D}
  - PAGE_LOAD_WAIT_MS = 8000, INDICATOR_LOAD_WAIT_MS = 10000
  - Tries 4 selectors: .layout__area--center, .chart-markup-table, .chart-container, canvas
  - Falls back to full page screenshot if no chart element found
  - Saves both sizes per ticker

capture_charts_batch(tickers_with_timeframe, headless, ...) → Dict[ticker, path|None]:
  - Single browser session for all tickers (efficient)
  - Per-ticker fallback — batch never crashes on single ticker failure
  - Rate-limit delay: 1.5s between captures
  - Returns relative paths for CI compatibility

Cookie management:
  save_cookies(context), load_cookies(context) → JSON file
  extract_chrome_cookies(domain) → imports from Chrome SQLite (Chrome must be closed)

check_indicators_loaded(page) → (bool, str):
  - Checks for runtime errors, study limit messages, login prompts
  - Counts .study-renderer elements (0 = auth/subscription issue)

save_chart_manifest(results, output_dir):
  - Merges new captures into existing chart_manifest.json (preserves funnel graphic)

---

## FILE: content/funnel_graphic.py (~672 lines)
## Purpose: 1200×675px PNG funnel — 5-Gate Filtering System

Image: 1200×675 (Twitter/X card ratio 1.91:1)
Themes: dark (#0d1117 bg) and light (#ffffff bg)

5 stages with gradient trapezoids:
  Stage 1 (Green):  Universe — 1,817 stocks scanned
  Stage 2 (Blue):   Volatility Expansion — Beta ≥1.5
  Stage 3 (Purple): Institutional Signals — Smart money detection
  Stage 4 (Coral):  Theme Alignment — Sector flow confirmation
  Stage 5 (Gold):   Forensic Audit — Final PASS signals

Each stage shows:
  Left: icon + stage name
  Center: count (large bold)
  Right: description + pass-rate percentage

Funnel graphic layout:
  Title: "The 5-Gate Filtering System"
  Subtitle: "Weekly Scan • {date}"
  Body: 5 trapezoid stages narrowing downward
  Summary: "Final Result: 1,817 stocks → 6 actionable signals (0.33%)"
  Footer: "Sterling Signals • sterlingsignals.substack.com"

generate_funnel_graphic(data, output_path, theme) → Path
load_signals_data(signals_path) → reads from signals.json stats block
update_chart_manifest(output_path, data) → updates chart_manifest.json

Dependencies: Pillow (PIL), system fonts (SF Display, Helvetica, DejaVu fallbacks)

---

## FILE: distribution/notifications.py (~870 lines)
## Purpose: Email (SMTP) + WhatsApp (Twilio) scan summary alerts

Channels fire independently — WhatsApp failure doesn't block email.

_load_email_config() → priority: env vars → email_config.json
  Env vars: SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD, NOTIFICATION_EMAIL

_load_whatsapp_config() → validates all 4 Twilio env vars
  Env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_TO
  WHATSAPP_TO: comma-separated for multiple recipients

Signal label mapping (_format_signal_label):
  "BEARISH PIVOT" → "Structural Exit Signal"
  "TRAILING STOP" → "Capital Preservation Triggered"
  "EXD EXIT" → "Structural Exit Signal"

Message formats:
  _build_plain_text() → plain text email body
  _build_html() → styled HTML email with badge colours
  _build_whatsapp_message() → concise ~500 char mobile message
  _build_summary_email_html() → combined buy+sell table HTML
  _build_summary_whatsapp() → combined buy+sell list message

Public API:
  send_sell_notification(ticker, signal_type, entry_price, ...) → Dict[channel, status]
    status values: "sent", "skipped", "failed", "partial"

  send_scan_summary(buy_signals, sell_signals, timeframe) → Dict[channel, status]
    Combined notification — single email + single WhatsApp for full scan
    (Replaces per-signal notifications in the pipeline)

---

## FILE: distribution/signal_tracker.py (~1144 lines)
## Purpose: Portfolio performance tracking + celebration milestone management

Key dataclasses:
  HistoricalSignal: ticker, entry_date, entry_price, current_price, pnl_pct, theme, days_held, status
  BigWin: ticker, entry_date, entry_price, current_price, pnl_pct, theme, threshold_crossed, celebration_type

Celebration types:
  big_win (≥25%), home_run (≥50%), hall_of_fame (≥100%)

Portfolio loading:
  load_portfolio() → delegates to core/portfolio_manager.load_portfolio()
  get_open_positions() → OPEN status only
  get_closed_positions() → CLOSED + STOPPED

Historical signal analysis:
  load_historical_signals() → all trades + live prices
  get_historical_winners(min_pnl) → filtered by threshold
  find_big_wins(signals) → BigWin list sorted by P&L desc

Celebration tracking:
  load_celebrations() → celebrations.json
  mark_as_celebrated(ticker, threshold) → writes to celebrations.json
  is_celebrated(ticker, threshold) → bool
  get_uncelebrated_wins() → BigWin list (highest uncelebrated threshold per ticker)

Portfolio vs SPY comparison:
  calculate_portfolio_vs_spy(positions) → {portfolio_return, spy_return, outperformance, winners}
  calculate_fair_spy_comparison(positions) → MATCHED HOLDING PERIODS (accurate alpha calc)
    - Fetches SPY once from earliest entry date (not N API calls)
    - Per-position slice for matched comparison
    - Requires ≥50% of positions to have valid SPY data
    - Returns: can_compare, alpha, comparison_type='matched_period'

Safeguard functions (used by tweet_generator.py):
  should_post_beat_spy() → bool
  has_enough_wins(positions, min_winners=2, min_pnl=15%) → bool
  has_uncelebrated_wins() → bool
  has_winning_closed_trades() → bool

Content helpers:
  filter_public_positions(positions) → winners only (STOPPED excluded)
  get_public_winners(min_pnl) → filtered + sorted desc
  get_winners_for_showcase(threshold=25%, include_entry_price, max=5) → showcase-ready
  get_recent_closes(days=14, winners_only=True) → recent exits
  get_early_movers(max_age=14, min_gain=5%) → new signals showing strength
  filter_expired_watchlist_signals(signals, max_age=21) → removes stale CONSIDER signals

Cold streak detection:
  check_cold_streak(lookback_days=14, threshold=3) → {in_cold_streak, should_reduce_posting, ...}

---

# TIER 6 — ORCHESTRATION & DATA SOURCES (CONTEXT)

Files: core/portfolio_manager.py (partial), run_friday.sh, .github/workflows/friday_scan.yml

---

## FILE: core/portfolio_manager.py (key interfaces)
## Purpose: Single source of truth for all trade tracking

Trade dataclass:
  ticker, status (OPEN/CLOSED/STOPPED), entry_date, entry_price,
  exit_date, exit_price, highest_close, theme, tier, signal_type (PASS/CONSIDER),
  conviction, notes, stop_pct, position_size_pct, position_dollars, sizing_gear
  [calculated]: current_price, pnl_pct, pnl_usd, stop_level, days_held, distance_to_stop

TradeStatus enum: OPEN, CLOSED, STOPPED

Date normalization: _normalize_date() handles YYYY-MM-DD and DD/MM/YYYY formats

Portfolio file: portfolio/output/portfolio.csv (single source of truth)
Backup: portfolio/output/portfolio_backups/ (max 30, deduped to 1 per calendar week)

Key PortfolioManager methods:
  add_trade(stock) → adds PASS/CONSIDER signals from scanner
  flag_exit(symbol, exit_price, reason) → marks CLOSED/STOPPED
  update_prices() → fetches live prices via yfinance
  get_open_positions() → active trades with calculated fields
  get_closed_trades() → historical exits
  export_to_sheets() → portfolio_google_sheets.csv
  get_compounding_summary() → NAV, return %, alpha vs SPY/QQQ, max drawdown

Module-level functions:
  load_portfolio() → List[Dict] (raw CSV rows)
  fetch_current_prices(tickers) → Dict[ticker, price] (yfinance)
  get_spy_ytd_return() → float (canonical SPY return)

EquitySnapshot: stores weekly NAV + SPY + QQQ for equity_curve.csv
EQUITY_CURVE_FILE = "equity_curve.csv" (used by portfolio_visual.py for chart)

---

## FILE: run_friday.sh
## Purpose: Local pipeline orchestrator (same steps as friday_scan.yml)

```bash
#!/bin/bash
# Usage:
#   ./run_friday.sh              # Full production run
#   ./run_friday.sh --test       # Test mode (no API calls)
#   ./run_friday.sh --no-push    # Run without pushing to GitHub
#   ./run_friday.sh --skip-charts
#   ./run_friday.sh --skip-newsletter

set -e  # Exit on error

# STEP 1: Scanner
python3 -m core.scanner --archive [--web-search | --no-llm --top 20]

# STEP 1.5: Funnel Graphic
python3 -m content.funnel_graphic

# STEP 2: Chart Capture (skippable with --skip-charts)
python3 -m content.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --headless

# STEP 3: Market Analysis (skippable with --skip-newsletter)
python3 -m content.market_analyzer --save

# STEP 4: Newsletter (skippable with --skip-newsletter)
python3 -m content.newsletter_compiler --from-html

# STEP 4.5: DD HTML Posts
python3 -m content.dd_post_generator

# STEP 5: Tweets
python3 -m content.tweet_generator --signals scanner/output/signals.json --portfolio portfolio/output/portfolio.csv --output twitter/output/

# STEP 5.5: Content Production Guide
python3 -m content.content_production_guide

# STEP 5.6: Substack Notes Batch (fallback to legacy if not found)
python3 -m content.substack_notes_batch_generator
# Fallback: python3 -m content.substack_notes_generator

# STEP 6: Git commit + push (skippable with --no-push)
git add scanner/ portfolio/ substack/ twitter/
git commit -m "Weekly scan results YYYY-MM-DD"
git push

# Test mode appends [TEST] prefix to commit message and skips API calls
```

Summary output lists all generated files + content calendar:
  Saturday: Weekly Recap + 3 notes
  Sunday-Friday: Posts per day + 3 notes each
  Daily: Tweets auto-post via GitHub Actions

---

## FILE: .github/workflows/friday_scan.yml
## Purpose: GitHub Actions — full Friday automated pipeline

Trigger: cron '30 21 * * 5' (Friday 21:30 UTC = 4:30 PM ET) + workflow_dispatch

Manual inputs:
  skip_llm: false (--no-llm for scanner)
  web_search: true
  top_n: 0 (0 = all tickers)
  skip_charts: false
  skip_tweets: false
  skip_newsletter: false

9 named job steps:

  Step 1: Full Scanner Run
    python -m core.scanner --archive [--web-search]

  Step 2: Send Scan Notifications
    python -m distribution.notifications --scan-complete
    Requires: SMTP_SERVER, EMAIL_SENDER (optional WhatsApp Twilio vars)

  Step 3: Chart Capture (Funnel + TradingView)
    python -m content.funnel_graphic
    python -m content.chart_capture --tickers-from scanner/output/signals.json --headless
    Requires: TRADINGVIEW_COOKIES (optional, falls back to skip)

  Step 4: Generate Market Analysis
    python -m content.market_analyzer --save

  Step 4.5: Compile Newsletter
    python -m content.newsletter_compiler --from-html

  Step 4.6: Generate Substack Posts
    python -m content.substack_content_generator --all

  Step 4.75: Portfolio Visual
    python -m content.portfolio_visual

  Step 5: Generate Tweets
    python -m content.tweet_generator --signals scanner/output/signals.json --portfolio portfolio/output/portfolio.csv --account all

  Step 5.5: Generate Content Production Guide
    python -m content.content_production_guide

  Step 5.6: Generate Substack Notes Batch
    python -m content.substack_notes_batch_generator

  Step 5.7: Generate DD Posts
    python -m content.dd_post_generator

  Artifacts uploaded:
    scan-results (30 days): scanner/output/signals.json, portfolio/output/portfolio.csv, scanner/output/current/newsletter_briefing.md, scanner/output/current/report.txt
    substack-notes (7 days): substack/output/current/substack_notes/
    substack-posts (30 days): substack/output/current/substack_posts/
    content-queue (14 days): twitter/output/content_queue*.json
    charts (30 days): twitter/output/charts/

  Step 6 (Git commit):
    git add scanner/ portfolio/ substack/ twitter/
    git commit -m "Weekly scan results YYYY-MM-DD"
    git push

  Step 7 (Vercel deploy, optional):
    Conditional on VERCEL_TOKEN secret existing
    Deploys portfolio dashboard to Vercel

  Required secrets:
    ANTHROPIC_API_KEY (required)
    TRADINGVIEW_COOKIES (optional — chart capture)
    VERCEL_TOKEN (optional — dashboard deploy)
    SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD, NOTIFICATION_EMAIL (optional)
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_TO (optional)

  Cost: ~$2-4 per Friday run with web search enabled

---

# APPENDIX: KEY CONSTANTS QUICK REFERENCE

## Models
  Substack posts (8 types):   claude-sonnet-4-20250514
  Newsletter compilation:      claude-sonnet-4-20250514
  Substack notes (21/week):   claude-sonnet-4-20250514
  Weekly tweets (batch):       claude-sonnet-4-20250514
  Live tweets:                 claude-sonnet-4-5-20250929
  Deep DD:                     claude-opus-4-20250514 (extended thinking)

## Critical File Paths
  scanner/output/signals.json                         — weekly scanner output (source of truth)
  portfolio/output/portfolio.csv                      — all positions (OPEN/CLOSED/STOPPED)
  twitter/output/content_queue.json                   — main account weekly tweets (slots 2-5)
  twitter/output/daily_content_queue.json             — main account daily tweets (slots 1/6/7)
  twitter/output/live_content_queue.json              — live tweets (all accounts)
  twitter/output/live_context.json                    — Grok market context
  twitter/output/celebrations.json                    — milestone celebration tracking
  twitter/output/failed_tweets.json                   — validation failure log
  substack/output/current/newsletter.html             — Sunday newsletter
  scanner/output/current/market_analysis.md           — market context
  substack/output/current/content_production_guide.md — weekly context doc for Claude.ai
  substack/output/current/substack_notes/*.md         — 21 notes (3/day)
  substack/output/current/substack_posts/*.html       — 4-5 Substack posts
  twitter/output/charts/chart_manifest.json           — all captured chart paths
  docs/content_prompt_handbook_v5.md             — permanent prompt reference

## Cost Summary
  Full Friday pipeline:  $2-4 (scanner $1-3 + content $0.50-1.00)
  Daily scanner + tweets: $0.10-0.30 per run (Mon-Fri)
  Live tweets:            $0.50-2.00 per day
  Weekly total:           ~$5-15

---

*Reference file compiled: February 2026*
*Attach alongside: cached-pondering-moth.md (architecture audit)*
