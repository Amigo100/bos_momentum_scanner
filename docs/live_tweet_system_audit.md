# Live Tweet System — Comprehensive Audit

**Date:** March 6, 2026
**Purpose:** Full audit of the live tweet generation system for analysis and content quality improvement

---

## 1. WHY TWEETS AREN'T POSTING

### Diagnosis (from `twitter/output/live_content_queue.json`)

| Account | Variant | Status | Error | Fix |
|---------|---------|--------|-------|-----|
| @AlexSterlingGBR | variant_1 | **13/13 FAILED** | `503 Service Unavailable` | Auth tokens expired/revoked. Regenerate at developer.twitter.com → update GitHub Secrets `X_ACCESS_TOKEN` + `X_ACCESS_SECRET` |
| @Rdobrogowska | variant_2 | **11/11 FAILED** | `402 Payment Required` | X API billing exhausted. Top up credits or switch plan |
| Account 3 (James) | variant_3 | **16/16 POSTED** | None | Working perfectly |

**Key insight:** Tweet *generation* works fine (79 tweets generated March 2-5). The failure is entirely at the *posting* layer.

---

## 2. COMPLETE CONTENT PIPELINE ARCHITECTURE

### Pipeline Flow (per GitHub Actions run)

```
.github/workflows/live_tweet.yml (14 cron triggers/day)
EST/EDT dual crons with season detection

Step 1: CONTEXT GATHERING — twitter/live_context_gatherer.py
  → Grok (grok-4-fast-non-reasoning) via xAI API
  → X Search + Web Search for market conditions
  → Output: twitter/output/live_context.json
  → Fields: market_snapshot, portfolio_movers, theme_activity,
            theme_tickers, fintwit_trending, fintwit_theme_overlaps

Step 2: TWEET GENERATION — twitter/live_tweet_generator.py
  → Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
  → 7-priority decision cascade → system prompt → user prompt
  → Generates 3 variants (1 per account)
  → 14-step validation → repair loop (max 2 retries)
  → Output: appended to twitter/output/live_content_queue.json

Step 3: CHART GENERATION — twitter/chart_generator.py
  → chart-img.com REST API (only for chart_recommended=True)
  → Output: twitter/output/charts/*.png

Step 4: POSTING — twitter/poster.py (per account)
  → X API v2 (tweet creation) + v1.1 (media upload)
  → Final validate_before_posting() banned term check
  → Retry: 3 attempts, exponential backoff

Step 5: CLEANUP + COMMIT
  → Remove items >72h old from queue
  → git commit + push queue changes
```

---

## 3. ALL CONTENT-CONTROLLING ELEMENTS

### A. System Prompt (`build_system_prompt()` — lines 1451-1580)

**Location:** `twitter/live_tweet_generator.py:1451-1580`

Assembled dynamically from:

1. **FinTwit Style Guide** — loaded from `FINTWIT_STYLE_GUIDE.md` (**MISSING** — falls back to 1-line embedded default: "Write tweets in confident, casual FinTwit voice. <=280 chars...")
2. **Persona Block** — from `config/settings.py:PERSONAS` dict + `get_persona()`
3. **Extended Voice Guides** — from `config/persona_voice_guides.yaml` (64 lines, rhythm examples per persona)
4. **Opening Sentence Cooldown** — injected from `RecentTweetTracker.recent_openings` (last 10)
5. **Phrase Cooldown** — from `RecentTweetTracker.recently_used_phrases` (up to 20, 48h window)
6. **Banned Terms Sample** — first 40 from `config/banned_terms.py:CRITICAL_BANNED`
7. **Thread Format Instructions** — conditional, only when `is_thread=True`
8. **Hard Rules** — no fabrication, no hashtags, <=280 chars, no losses, no UK refs, no AI mentions, max 1 NFA per 3 variants

### B. User Prompt (`build_user_prompt()` — lines 1671-1819)

**Location:** `twitter/live_tweet_generator.py:1671-1819`

Assembled from:

1. **Market State** — SPY/QQQ/VIX moves, mood, headline from Grok context
2. **Portfolio Movers** — today's significant moves from Grok context
3. **Theme Activity** — breaking/active themes from Grok context
4. **FinTwit Trending** — what's buzzing on X from Grok context
5. **Tweet Type + Reason** — from `decide_tweet_type()` decision
6. **Per-Account Assignments** — from `_prepare_slot_data()` — each account gets different ticker/category/angle
7. **Category Examples** — YAML-first from `config/tweet_prompts/*.yaml` (11 files), hardcoded fallback from `LIVE_CATEGORY_EXAMPLES`
8. **Persona-Specific Examples** — from YAML `persona_examples` (**currently all empty `[]`**)
9. **Funnel Stats** — for SIGNAL_ALERT/SUBSTACK_TEASER: "1,817 stocks scanned → X survived"
10. **Chart Reference** — for SIGNAL_ALERT/RECEIPT/SELL_SIGNAL/TECHNICAL_ANALYSIS
11. **Time Context** — pre-market/market-open/power-hour/after-hours
12. **Catalyst/Bullish Factors** — for TECHNICAL_ANALYSIS from signals.json
13. **Thread Instructions** — for THEME_LIST and multi-RECEIPT threads
14. **Portfolio Context** — full position list with entry prices, current prices, P&L %

### C. 11-Category Taxonomy (`twitter/models.py`)

| Category | Source | Chart | Thread | External Tickers |
|----------|--------|-------|--------|-----------------|
| SELL_SIGNAL | Exit signals | Yes | No | No |
| SIGNAL_ALERT | Scanner signals (PASS + CONSIDER) | Yes | No | No |
| RECEIPT | Portfolio winners with moves | Yes | Yes (multi-winner) | No |
| MARKET_COMMENTARY | Market conditions (any mood) | No | No | Yes |
| THEME_CATALYST | Breaking theme + portfolio overlap | No | No | No |
| THEME_LIST | Theme tickers (external + portfolio) | No | Yes (always) | Yes |
| TRENDING_TAKE | FinTwit buzz + tracked themes | No | No | Yes |
| TECHNICAL_ANALYSIS | Position commentary with levels | No | No | No |
| EDUCATIONAL | Methodology, trading psychology | No | No | No |
| SUBSTACK_TEASER | Today's post topic + key insight | No | No | No |
| ENGAGEMENT | Community building, questions | No | No | No |

### D. 7-Priority Decision Cascade (`decide_tweet_type()` — lines 1113-1444)

Budget-gated at every level — if over weekly target, falls through:

| Priority | Category | Triggers When | Cooldown | Weekly Target |
|----------|----------|---------------|----------|---------------|
| P0 | SELL_SIGNAL | Exit signal exists | 12h/ticker | 3 |
| P1a | SIGNAL_ALERT (confirmed) | Fresh buy signals (<72h) | 6h/ticker | 7 |
| P1b | SIGNAL_ALERT (watching) | Consider signals exist | 12h/ticker | (shared) |
| P2 | RECEIPT / MARKET_COMMENTARY | Alternating (engagement-weighted 70/30) | 3h ticker / 4h type | 7 each |
| P3a | THEME_CATALYST | Breaking theme detected | 6h/theme | 5 |
| P3b | TRENDING_TAKE | FinTwit overlaps themes | 6h/theme | 5 |
| P4a | THEME_LIST | Theme with 5+ external tickers | 6h/theme | 3 |
| P4b | SUBSTACK_TEASER | Post day detected | — | 4 |
| P5a | TECHNICAL_ANALYSIS | Weekday + position exists | 4h cooldown | 5 |
| P5b | EDUCATIONAL | No cooldown block | 6h cooldown | 3 |
| P6 | ENGAGEMENT | Fallback | 6h cooldown | 5 |
| — | SKIP | All budgets exhausted | — | — |

### E. 3-Account Persona System

**Config:** `config/settings.py:222-297`

| Account | Persona | Archetype | Tone | Primary Categories | Avoids |
|---------|---------|-----------|------|-------------------|--------|
| variant_1 (Alex) | The System | Analyst | Authoritative | SIGNAL_ALERT, RECEIPT, SELL_SIGNAL, TECHNICAL_ANALYSIS | ENGAGEMENT, EDUCATIONAL |
| variant_2 (Rozalia) | The Mentor | Teacher | Conversational | EDUCATIONAL, THEME_LIST, SUBSTACK_TEASER, THEME_CATALYST | SELL_SIGNAL |
| variant_3 (James) | The Trader | Practitioner | Direct/Casual | MARKET_COMMENTARY, TRENDING_TAKE, RECEIPT, ENGAGEMENT | EDUCATIONAL |

**Extended voice guides:** `config/persona_voice_guides.yaml` — detailed rhythm examples and never-do lists per persona:

- **Alex:** Quant-like. Short declarative sentences. Leads with data. Dry confidence. No exclamation marks. Rhythm: short-short-medium.
- **Rozalia:** Connects stocks to bigger themes. Flowing sentences. Uses "we" naturally. Warm authority. Balances data with narrative.
- **James:** Most conversational. Casual transitions. Addresses reader directly. Shorter tweets. Comfortable with uncertainty.

### F. 14-Step Validation Pipeline

1. Category validation (matches taxonomy)
2. Fabrication check (tickers/prices must exist in provided data)
3. Banned phrases check (`config/banned_terms.py:ALL_BANNED`)
4. Winners-only display (no negative P&L)
5. Internal term patterns check (`INTERNAL_TERM_PATTERNS` from models.py)
6. Character count (<=280)
7. Opening sentence diversity (vs `RecentTweetTracker.recent_openings`)
8. Thread integrity (each sub-tweet <=280, correct numbering)
9. Chart flag validation
10. Cross-account dedup (3 variants must be sufficiently different)
11. Slot collision check
12. Context staleness (reject if >4h old)
13. Queue dedup (>80% similarity → reject)
14. Meta-language / portfolio fabrication / defeatist language filters

**Repair loop:** Failed tweets get max 2 retries via Claude Sonnet.

### G. Diversity Controls

- **RecentTweetTracker:** 48h state from `live_content_queue.json`
- **Category weekly targets:** `CATEGORY_WEEKLY_TARGETS` (total ~54/week)
- **Same ticker:** MAX_SAME_TICKER_PER_DAY=3, MIN_HOURS_BETWEEN=3h
- **Same category:** MAX_SAME_CATEGORY_PER_DAY=3
- **Queue dedup:** 80% similarity (SequenceMatcher)
- **Opening dedup:** 70% similarity
- **Daily cap:** 12 weekday, 4 weekend

---

## 4. DATA SOURCES

| Data | Source File | Updated By | Staleness |
|------|-----------|------------|-----------|
| Live market context | `twitter/output/live_context.json` | `live_context_gatherer.py` via Grok | 4h max |
| Portfolio positions | `portfolio/output/portfolio.csv` | Friday scan + manual | Weekly |
| Scanner signals | `scanner/output/signals.json` | Friday scan | Weekly |
| Current prices | yfinance API (real-time) | `fetch_current_prices()` | Per-run |
| Tweet history | `twitter/output/live_content_queue.json` | Each gen run | Per-run |
| Engagement data | `twitter/output/engagement_data.json` | External (optional) | Optional |
| Failed tweets | `twitter/output/failed_tweets.json` | Validation failures | Per-run |
| Category examples | `config/tweet_prompts/*.yaml` (11 files) | Manual | Static |
| Voice guides | `config/persona_voice_guides.yaml` | Manual | Static |
| Banned terms | `config/banned_terms.py` | Manual | Static |
| Persona config | `config/settings.py:222-297` | Manual | Static |

---

## 5. ALL SCRIPTS INVOLVED

### Core Pipeline

| Script | Purpose | Model Used |
|--------|---------|------------|
| `twitter/live_tweet_generator.py` (~2,500 lines) | Decision → prompt → API → validate → queue | Claude Sonnet 4.5 |
| `twitter/live_context_gatherer.py` (~400 lines) | Grok market context (X + Web Search) | Grok-4-fast |
| `twitter/poster.py` (~500 lines) | Queue reading, X API posting, media upload | None |
| `twitter/chart_generator.py` (~300 lines) | chart-img.com REST API charts | None |
| `twitter/models.py` (~180 lines) | Category taxonomy, data classes | None |

### Supporting

| Script | Purpose |
|--------|---------|
| `twitter/signal_tracker.py` | Win tracking, milestone detection, `filter_public_positions()` |
| `twitter/self_quote_tracker.py` | Quote tweets at 25%/50%/100% milestones |
| `twitter/health_check.py` | API health checks (Grok, Claude, X, chart-img) |
| `twitter/cost_tracker.py` | Daily kill switch ($1.00/day) |
| `twitter/funnel_graphic.py` | Funnel visualization PNG |
| `twitter/winner_showcase_generator.py` | Winner showcase with entry prices |

### Configuration

| File | Purpose |
|------|---------|
| `config/settings.py` (lines 219-1250) | PERSONAS, PERSONA_AFFINITY, CATEGORY_WEEKLY_TARGETS, MODEL_LIVE_TWEET, limits |
| `config/banned_terms.py` | CRITICAL_BANNED, ALL_BANNED, check_banned_phrases() |
| `config/persona_voice_guides.yaml` | Extended voice guides with rhythm examples |
| `config/tweet_prompts/*.yaml` (11 files) | Per-category examples, persona examples (mostly empty), banned terms |
| `FINTWIT_STYLE_GUIDE.md` | **MISSING** — falls back to 1-line embedded default |

### Workflow

| File | Purpose |
|------|---------|
| `.github/workflows/live_tweet.yml` | 14 crons/day, 10-step pipeline, dual EST/EDT |

---

## 6. IDENTIFIED ISSUES FOR QUALITY IMPROVEMENT

### Critical
1. **Account 1 auth tokens expired** — 503 on all attempts
2. **Account 2 out of API credits** — 402 on all attempts
3. **`FINTWIT_STYLE_GUIDE.md` missing** — falls back to 1-line default, losing significant voice guidance

### Content Quality
4. **Persona-specific examples empty** — all `persona_examples` in YAML files are `[]`
5. **No bad examples** — all `bad_examples` in YAML files are `[]`
6. **Opening repetition** — 10-opening window may be too small for 12 tweets/day
7. **Category examples stale** — reference old tickers/prices
8. **Style guide content minimal** — even the fallback is 1 sentence

### Structural
9. **Engagement data optional** — drives P2 weighting but may not exist
10. **Context staleness 4h** — may be too old in fast-moving markets
11. **No A/B testing** — no mechanism to compare prompt versions
12. **Thread underutilized** — only THEME_LIST + multi-RECEIPT produce threads

---

## 7. FILES TO UPLOAD TO CLAUDE.AI FOR ANALYSIS

### Must-have (core content pipeline)
1. `twitter/live_tweet_generator.py` — entire generation system (~2,500 lines)
2. `twitter/models.py` — category taxonomy and data classes
3. `config/settings.py` — personas, affinity, weekly targets, all tweet config
4. `config/persona_voice_guides.yaml` — extended voice guides
5. `config/banned_terms.py` — banned terms registry

### Should-have (data context)
6. `twitter/output/live_content_queue.json` — recent output for quality review
7. `config/tweet_prompts/receipt.yaml` — sample YAML prompt config (pick 2-3)
8. `twitter/live_context_gatherer.py` — how market context is gathered

### Nice-to-have
9. `twitter/poster.py` — posting logic and final validation
10. `.github/workflows/live_tweet.yml` — scheduling
11. `twitter/signal_tracker.py` — win tracking
12. This audit document

---

## 8. RECOMMENDED IMPROVEMENT AREAS

For the Claude.ai analysis session, focus on:

1. **System prompt rewrite** — apply data-forward voice treatment (like notes v2)
2. **Style guide creation** — create `FINTWIT_STYLE_GUIDE.md` with detailed voice/rhythm/anti-pattern guidance
3. **Persona example population** — fill empty `persona_examples` in all 11 YAML files
4. **Bad example population** — add `bad_examples` showing what NOT to do
5. **Category example refresh** — update with current portfolio tickers/prices
6. **Thread strategy expansion** — threads for more categories
7. **Opening diversity** — expand tracker window or add structural templates per persona

---

## APPENDIX: KEY CODE SECTIONS REFERENCE

### System Prompt Template (from `build_system_prompt()`)
```
"You are the voice of Sterling Signals, a momentum trading newsletter on FinTwit.

STYLE RULES (non-negotiable):
{style_guide}
{persona_block}
{voice_guide_block}
{opening_cooldown_block}
{phrase_cooldown_block}

YOUR TASK:
Generate exactly 3 tweet variants for the same moment. Each variant must:
- Sound like a different human wrote it
- Be <=280 characters
- Contain at least one specific element (ticker, price, %, or named theme)

FORMATTING RULES:
- Return ONLY valid JSON
- Format: {"tweets": [{"text": "...", "category": "...", "primary_ticker": "...", "chart_recommended": true/false, "account": "variant_1|variant_2|variant_3"}, ...]}

ABSOLUTE BANS: {banned_sample}

ADDITIONAL RULES:
- Never fabricate tickers, prices, or percentages
- Never use hashtags
- Never exceed 280 characters
- Never mention losses or negative P&L
- Never use UK references
- Never reference being an AI
- Keep NFA to <=1 of 3 variants"
```

### User Prompt Template (from `build_user_prompt()`)
```
"CURRENT MARKET STATE:
- SPY: {spy_move} | QQQ: {qqq_move} | VIX: {vix}
- Mood: {market_mood}
- Headline: {headline}

YOUR PORTFOLIO MOVERS TODAY:
{movers_json}

THEME ACTIVITY:
{themes_json}

FINTWIT IS DISCUSSING:
{trending_text}

TWEET TYPE REQUESTED: {decision_type}
REASON: {reason}
FOCUS TICKER(S): {tickers}

PER-ACCOUNT ASSIGNMENTS:
{per_account_instructions}

REFERENCE EXAMPLES:
{category_examples}

PORTFOLIO CONTEXT:
{formatted_positions}

Generate 3 variants now."
```

### Persona Config (from `config/settings.py`)
```python
PERSONAS = {
    'main': {
        'name': 'The System', 'archetype': 'Analyst',
        'voice': {'tone': 'authoritative', 'traits': ['data-driven', 'precise', 'confident']},
        'signature_phrases': ["The scanner doesn't lie.", "Data drives decisions."]
    },
    'account2': {
        'name': 'The Mentor', 'archetype': 'Teacher',
        'voice': {'tone': 'conversational', 'traits': ['helpful', 'patient', 'encouraging']},
        'signature_phrases': ["Here's why this matters...", "The lesson here:"]
    },
    'account3': {
        'name': 'The Trader', 'archetype': 'Practitioner',
        'voice': {'tone': 'direct', 'traits': ['action-oriented', 'confident', 'punchy']},
        'signature_phrases': ["Eyes on this one.", "Momentum is real."]
    },
}

PERSONA_AFFINITY = {
    "variant_1": {"primary": {"SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"}, "avoids": {"ENGAGEMENT", "EDUCATIONAL"}},
    "variant_2": {"primary": {"EDUCATIONAL", "THEME_LIST", "SUBSTACK_TEASER", "THEME_CATALYST"}, "avoids": {"SELL_SIGNAL"}},
    "variant_3": {"primary": {"MARKET_COMMENTARY", "TRENDING_TAKE", "RECEIPT", "ENGAGEMENT"}, "avoids": {"EDUCATIONAL"}},
}

CATEGORY_WEEKLY_TARGETS = {
    "RECEIPT": 7, "MARKET_COMMENTARY": 7, "SIGNAL_ALERT": 7,
    "TRENDING_TAKE": 5, "THEME_CATALYST": 5, "ENGAGEMENT": 5,
    "TECHNICAL_ANALYSIS": 5, "SUBSTACK_TEASER": 4, "THEME_LIST": 3,
    "EDUCATIONAL": 3, "SELL_SIGNAL": 3,
}
```
