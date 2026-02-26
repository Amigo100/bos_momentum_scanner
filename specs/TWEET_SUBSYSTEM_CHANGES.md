# Tweet Subsystem — Required Changes Specification
## Sterling Signals Architecture Optimisation

**Date:** 2026-02-25
**Scope:** live_tweet_generator.py, live_context_gatherer.py, poster.py, models.py, chart_generator.py, tweet_generator.py, chart_capture.py, verify_tweets.py, and related config
**Status:** Pre-implementation specification — depends on scanner + Substack subsystem changes being completed first
**Depends on:** SCANNER_SUBSYSTEM_CHANGES.md, SUBSTACK_SUBSYSTEM_CHANGES.md

---

## TABLE OF CONTENTS

1. [Problem Diagnosis](#1-problem-diagnosis)
2. [Architecture Overview — Target State](#2-architecture-overview)
3. [Content Model Redesign](#3-content-model-redesign)
4. [Priority System Redesign](#4-priority-system-redesign)
5. [Context Gatherer Overhaul](#5-context-gatherer-overhaul)
6. [Tweet Generator Overhaul](#6-tweet-generator-overhaul)
7. [Thread Support](#7-thread-support)
8. [Persona System Redesign](#8-persona-system-redesign)
9. [Substack Integration](#9-substack-integration)
10. [Dynamic Theme Sync](#10-dynamic-theme-sync)
11. [models.py Changes](#11-modelspy-changes)
12. [Validation Pipeline Changes](#12-validation-pipeline-changes)
13. [poster.py Changes](#13-posterpy-changes)
14. [Chart System Changes](#14-chart-system-changes)
15. [Schedule & Volume Changes](#15-schedule--volume-changes)
16. [Configuration Changes](#16-configuration-changes)
17. [Module Inventory — Delete / Keep / Modify](#17-module-inventory)
18. [Data Flow — Target State](#18-data-flow)
19. [GitHub Actions Workflow Changes](#19-github-actions-workflow)
20. [Cross-System Dependencies](#20-cross-system-dependencies)
21. [Implementation Order](#21-implementation-order)
22. [Testing Checklist](#22-testing-checklist)
23. [Cost Analysis](#23-cost-analysis)
24. [Summary Statistics](#24-summary-statistics)

---

## 1. PROBLEM DIAGNOSIS

### 1.1 Core Issues (from Feb 20 Analysis + Ongoing Observation)

The tweet system's engineering is sound — validation pipeline, repair loop, cost tracking, banned terms, staggered posting are all well-built. The problems are **structural**, not bugs.

**Issue 1: Tiny data pool vs high output volume.**
15 tweet-slots/day (5 slots × 3 accounts). Only 3 showcase-ready winners (>25%). MAX_SAME_TICKER_PER_DAY=3 means 9 ticker-focused slots exhaust the pool. Remaining 6 slots become repetitive filler about mid-range positions.

**Issue 2: Priority cascade buries market-relevant content.**
RECEIPT at P2 with 12/week budget means positive movers fill slots before market commentary, theme analysis, or educational content is considered. The feed reads as an endless highlight reel rather than a market-aware trading account.

**Issue 3: Grok context gathered but underused.**
`fintwit_trending` isn't used by any decision path. `theme_activity` only triggers at P4. `news_events` only feeds MARKET_REACTION which requires a negative trigger. The richest context data is barely consumed.

**Issue 4: No theme-first multi-ticker content.**
The style guide's highest-engagement examples (10-ticker theme lists, sector watchlists, market commentary) are structurally impossible because the system only knows tickers in portfolio.csv and signals.json. The Grok context gatherer could provide external tickers but doesn't.

**Issue 5: Single-tweet constraint blocks best content formats.**
Multi-ticker receipts (~400 chars), theme lists (~500+ chars), detailed technical updates — none fit in 280 chars. poster.py already supports threads (post_thread), but live_tweet_generator.py never produces them.

**Issue 6: Persona differentiation is stylistic, not substantive.**
All three personas tweet about the same tickers with the same data. Differentiation is in phrasing ("data-driven angle" vs "explains-why angle"), not in content type affinity.

**Issue 7: Hardcoded theme list doesn't sync with scanner.**
Grok searches a static list: "copper, infrastructure, defense, AI..." but the scanner identifies different themes each week (Healthcare Contrarian Recovery, Financial Services AI Adoption, etc.). The two systems diverge.

**Issue 8: Substack content not leveraged.**
5-6 posts/week produced. Zero feed-back into the tweet system as content teasers. Each deep dive, theme rotation, or educational post could generate 2-3 promotional tweets.

**Issue 9: Batch system (tweet_generator.py) is redundant.**
2,225-line batch system generates weekly content queues on Fridays. The live system (live_tweet_generator.py) now handles all real-time posting. Both consume the same upstream data. The batch system is unused and unmaintained — a confusion source.

### 1.2 What Works Well (Keep As-Is)

- **14-step validation pipeline** — thorough, catches fabrication and banned terms
- **Repair loop** — max 2 attempts then drop+log, prevents infinite retries
- **Cost tracking + kill switch** — $1/day limit with atomic JSON writes
- **Banned terms system** — 111 terms, 31 regex patterns, comprehensive
- **Anti-fabrication rules** — all tickers/prices must come from source data
- **Staggered posting** — 0/10/20 min offsets across accounts
- **Chart-IMG API integration** — CI-compatible, never blocks tweets on failure
- **Queue pruning** — 7-day auto-cleanup prevents git bloat
- **Atomic JSON writes** — tempfile → rename pattern throughout

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 Target State — High-Level Flow

```
DAILY 07:00 ET — daily_content.yml (from Substack spec)
├── Generates daily_context.md + daily_notes_context.json
├── Writes fresh market_analysis.md
└── Commits to repo → triggers tweet system awareness of today's post topic

5x WEEKDAY + 2x WEEKEND — live_tweet.yml (MODIFIED)
├── Phase 1: CONTEXT GATHERING (Grok xAI)
│   ├── Input: portfolio.csv + signals.json + themes from scanner
│   │         + today's Substack topic + live_content_queue.json
│   ├── NEW: Returns external tickers for active themes
│   ├── NEW: Returns fintwit_trending overlap with tracked themes
│   └── Output: live_context.json (enriched)
│
├── Phase 2: TWEET GENERATION (Claude Sonnet)
│   ├── NEW: 7-priority system (replaces 10-priority cascade)
│   ├── NEW: Content-type affinity per persona (not just style)
│   ├── NEW: Thread-capable for multi-ticker and theme-list formats
│   ├── NEW: Substack teaser generation on post days
│   └── Output: live_content_queue.json (with thread support)
│
├── Phase 3: CHART GENERATION (chart-img.com)
│   └── Unchanged — generate charts for flagged items
│
└── Phase 4: POSTING (tweepy)
    ├── Single tweets: post_tweet() — unchanged
    ├── Threads: post_thread() — already supported
    └── Staggered: 0/10/20 min — unchanged
```

### 2.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Batch system | **Delete** | Redundant with live system, unmaintained, confusion source |
| chart_capture.py | **Delete** | Playwright-based, requires GUI login, replaced by chart_generator.py |
| verify_tweets.py | **Delete** | Tests batch system only, live system has inline validation |
| Priority levels | **7 (from 10)** | Flatten + rebalance; merge redundant levels |
| Thread support | **Add to generator** | poster.py already supports; generator needs to produce thread items |
| Grok context | **Enrich with external tickers** | Enables theme-first content that doesn't require portfolio data |
| Theme list | **Dynamic from scanner** | Read from signals.json themes[] instead of hardcoded list |
| Persona model | **Content-type affinity** | Each persona weighted toward different categories, not just style |
| Substack teaser | **New category** | SUBSTACK_TEASER replaces NEWSLETTER_CTA for richer promotion |
| Market commentary | **Split from MARKET_REACTION** | Positive market context gets its own path (not gated on negative triggers) |

---

## 3. CONTENT MODEL REDESIGN

### 3.1 New Category Taxonomy

**Remove categories:**
- `NEWSLETTER_CTA` → replaced by `SUBSTACK_TEASER` (richer, content-aware)
- `DIP_OPPORTUNITY` → merged into `MARKET_COMMENTARY` (was too narrow)
- `WATCHLIST` → merged into `SIGNAL_ALERT` with a "watching" sub-type

**Add categories:**
- `MARKET_COMMENTARY` — any notable market context (positive, negative, or neutral). Replaces MARKET_REACTION's negative-only trigger + absorbs DIP_OPPORTUNITY
- `THEME_LIST` — multi-ticker theme post (thread-capable). The high-engagement format the system couldn't produce before
- `TRENDING_TAKE` — when fintwit_trending overlaps with tracked themes, post a take connecting the buzz to our thesis
- `SUBSTACK_TEASER` — pulls a compelling stat/insight from today's Substack post and teases it with context

**Keep categories (renamed for clarity):**
- `SELL_SIGNAL` → unchanged
- `SIGNAL_ALERT` → absorbs WATCHLIST (sub-type: "watching" vs "confirmed")
- `RECEIPT` → unchanged, but with reduced budget
- `THEME_MOMENTUM` → renamed `THEME_CATALYST` (breaking theme + portfolio overlap)
- `TECHNICAL_ANALYSIS` → unchanged
- `EDUCATIONAL` → unchanged
- `ENGAGEMENT` → unchanged

### 3.2 Final Category Set (10 categories, from 11)

| Category | Source | Chart | Thread-Capable | Persona Affinity |
|----------|--------|-------|----------------|-----------------|
| `SELL_SIGNAL` | Exit signals in signals.json | Yes | No | Alex |
| `SIGNAL_ALERT` | Scanner signals (PASS + CONSIDER) | Yes | No | Alex |
| `RECEIPT` | Portfolio winners with intraday moves | Yes | Yes (multi) | Alex, James |
| `MARKET_COMMENTARY` | Market conditions — any mood | No | No | James |
| `THEME_CATALYST` | Breaking theme + portfolio overlap | No | No | Rozalia |
| `THEME_LIST` | Theme tickers (external + portfolio) | No | Yes (always) | Rozalia |
| `TRENDING_TAKE` | FinTwit buzz ∩ tracked themes | No | No | James |
| `TECHNICAL_ANALYSIS` | Position commentary with levels | Chart recommended | No | Alex |
| `EDUCATIONAL` | Methodology, trading psychology | No | No | Rozalia |
| `SUBSTACK_TEASER` | Today's post topic + key insight | No | No | Rozalia |
| `ENGAGEMENT` | Community building, questions | No | No | James |

### 3.3 Content That No Longer Requires Portfolio Tickers

This is the highest-impact change. These categories can reference tickers **outside** portfolio.csv:

| Category | External Ticker Source |
|----------|----------------------|
| `THEME_LIST` | Grok context `theme_tickers` field (5-8 per active theme) |
| `TRENDING_TAKE` | FinTwit trending tickers from Grok context |
| `MARKET_COMMENTARY` | Market indices, sector ETFs from Grok context |
| `EDUCATIONAL` | No tickers required at all |
| `ENGAGEMENT` | No tickers required at all |

**Anti-fabrication rule update:** External tickers from Grok context are **allowed** in tweets for THEME_LIST, TRENDING_TAKE, and MARKET_COMMENTARY. They must come from `live_context.json` (Grok-verified), never hallucinated by Sonnet. Validation step 2 (ticker fabrication) must check the expanded allowed set: `portfolio ∪ signals ∪ context_tickers`.

---

## 4. PRIORITY SYSTEM REDESIGN

### 4.1 Old System (10 Levels) — Problems

The 10-level cascade has structural issues:
- P2 (RECEIPT, 12/week) dominates because positive movers exist most days
- P3 (MARKET_REACTION) only fires on negative triggers — positive market context has no home
- P4-P6 are rarely reached because P2 fills slots
- P7 (Grok opportunities) duplicates upstream logic
- P8-P10 are fallback chains that produce low-engagement filler

### 4.2 New System (7 Levels) — Balanced

| Priority | Category | Trigger | Cooldown | Weekly Budget |
|----------|----------|---------|----------|---------------|
| **P0** | `SELL_SIGNAL` | Exit signals in signals.json | 12h/ticker | 3 |
| **P1** | `SIGNAL_ALERT` | Fresh scanner signals (<72h) or CONSIDER signals | 6h/ticker (PASS), 12h/ticker (CONSIDER) | 7 |
| **P2** | `RECEIPT` **OR** `MARKET_COMMENTARY` | Positive movers (+2%+) **OR** notable market conditions (any mood) | 3h/ticker (receipt), 4h/type (commentary) | 7 receipts, 7 commentary |
| **P3** | `THEME_CATALYST` **OR** `TRENDING_TAKE` | Breaking theme in context **OR** fintwit ∩ tracked themes | 6h/theme | 5 catalyst, 5 trending |
| **P4** | `THEME_LIST` **OR** `SUBSTACK_TEASER` | Active themes with Grok external tickers **OR** today is a post day | 24h/type | 3 lists, 4 teasers |
| **P5** | `TECHNICAL_ANALYSIS` **OR** `EDUCATIONAL` | Position commentary **OR** methodology content | 4h/type | 5 TA, 3 educational |
| **P6** | `ENGAGEMENT` | Community content, questions | 6h/type | 5 |

### 4.3 Key Changes from Old System

**P2 is now shared between RECEIPT and MARKET_COMMENTARY** — they compete at the same priority level. The decision function alternates: if the last P2 tweet was a RECEIPT, the next P2 prefers MARKET_COMMENTARY (and vice versa). This ensures the feed isn't receipt-dominated.

**MARKET_COMMENTARY fires on any notable market condition**, not just negative triggers. Conditions that trigger:
- SPY/QQQ move > ±1% (positive or negative)
- VIX spike > 20 or drop below 15
- Market mood is "volatile", "bearish", OR "bullish" (not "quiet")
- Portfolio tickers showing relative strength or weakness vs indices
- High-impact news_events from Grok context

**P3 TRENDING_TAKE is new.** Fires when:
1. Grok `fintwit_trending` contains a topic that overlaps with `themes` from scanner
2. The topic hasn't been tweeted about in 6 hours
3. Example: FinTwit buzzing about "copper breakout" + scanner tracks copper theme → post a take connecting buzz to our thesis

**P4 THEME_LIST is new.** Fires when:
1. Grok `theme_tickers` returns 5+ tickers for an active theme
2. The theme hasn't had a list tweet in 24 hours
3. Always produces a 2-3 tweet thread (see Section 7)
4. Naturally includes any portfolio positions that fit the theme

**P4 SUBSTACK_TEASER replaces P8 NEWSLETTER_CTA.** Fires when:
1. Today is a Substack post day (from daily_context.md or content schedule)
2. No teaser has been posted in 24 hours
3. The teaser pulls a specific stat/insight from the post topic, not generic "link in bio"

**P7 (Grok opportunities) eliminated.** The Grok context is now consumed at every priority level — `theme_activity` at P3, `fintwit_trending` at P3, `news_events` at P2 — so a separate "Grok opportunities" catch-all is redundant.

**P9 (Multi-receipt) merged into P2 RECEIPT** with thread support. When 3+ winners have >5% gains and no receipt in 24h, generate a multi-ticker receipt thread instead of a single compressed tweet.

**P10 (Filler) eliminated.** The expanded category set (TRENDING_TAKE, THEME_LIST, SUBSTACK_TEASER) provides enough content variety that the system shouldn't need filler. If all budgets are exhausted, skip (better than filler).

### 4.4 Decision Function — Pseudocode

```python
def decide_tweet_type(context, portfolio, signals, tracker):
    # P0: Sell signals (unchanged)
    if sell_signal_available and not over_budget("SELL_SIGNAL"):
        return SELL_SIGNAL

    # P1: Signal alerts (now includes CONSIDER with "watching" framing)
    if fresh_pass_signal and not over_budget("SIGNAL_ALERT"):
        return SIGNAL_ALERT(sub_type="confirmed")
    if consider_signal and not over_budget("SIGNAL_ALERT"):
        return SIGNAL_ALERT(sub_type="watching")

    # P2: RECEIPT vs MARKET_COMMENTARY (alternating preference)
    last_p2 = tracker.last_p2_category  # "RECEIPT" or "MARKET_COMMENTARY"
    
    if last_p2 != "MARKET_COMMENTARY":
        # Try market commentary first
        if notable_market_condition(context) and not over_budget("MARKET_COMMENTARY"):
            return MARKET_COMMENTARY
    if last_p2 != "RECEIPT":
        # Try receipt
        if positive_mover_available(movers) and not over_budget("RECEIPT"):
            return RECEIPT
    # If alternation didn't match, try the other
    if notable_market_condition(context) and not over_budget("MARKET_COMMENTARY"):
        return MARKET_COMMENTARY
    if positive_mover_available(movers) and not over_budget("RECEIPT"):
        return RECEIPT

    # P3: Theme catalyst or trending take
    if breaking_theme(context) and not over_budget("THEME_CATALYST"):
        return THEME_CATALYST
    if fintwit_overlaps_themes(context, scanner_themes) and not over_budget("TRENDING_TAKE"):
        return TRENDING_TAKE

    # P4: Theme list or Substack teaser
    if theme_has_external_tickers(context, min=5) and not over_budget("THEME_LIST"):
        return THEME_LIST  # → thread
    if is_post_day() and not over_budget("SUBSTACK_TEASER"):
        return SUBSTACK_TEASER

    # P5: Technical analysis or educational
    if not over_budget("TECHNICAL_ANALYSIS"):
        return TECHNICAL_ANALYSIS
    if not over_budget("EDUCATIONAL"):
        return EDUCATIONAL

    # P6: Engagement
    if not over_budget("ENGAGEMENT"):
        return ENGAGEMENT

    return SKIP  # All budgets exhausted — better than filler
```

---

## 5. CONTEXT GATHERER OVERHAUL

### 5.1 Changes to live_context_gatherer.py

**File:** `twitter/live_context_gatherer.py` (533 lines → ~600 lines)

#### Change 1: Dynamic theme list from scanner

**Current (hardcoded):**
```python
TRACKED_THEMES = [
    "copper", "infrastructure", "defense", "AI", "data centers",
    "rare earth", "quantum computing", "space", "crypto mining",
    "nuclear", "semiconductors", "reshoring",
]
```

**New (dynamic from scanner + base themes):**
```python
def load_tracked_themes() -> List[str]:
    """Load themes from scanner output + base themes."""
    # Base themes that are always tracked (market-level, not scanner-specific)
    base_themes = ["copper", "infrastructure", "defense", "AI", "semiconductors", "nuclear"]
    
    # Dynamic themes from scanner's thematic analysis
    signals = load_json(SIGNALS_FILE)
    scanner_themes = []
    for theme in signals.get("themes", []):
        name = theme.get("name", "")
        if name:
            # Normalize: "AI Power Infrastructure" → "AI power infrastructure"
            scanner_themes.append(name.lower())
    
    # Merge and deduplicate (scanner themes take priority)
    all_themes = list(dict.fromkeys(scanner_themes + base_themes))
    return all_themes[:15]  # Cap at 15 to keep Grok prompt focused
```

#### Change 2: Request external tickers for active themes

**New field in Grok system prompt:**
```
6. For each ACTIVE or BREAKING theme, find 5-8 publicly traded companies 
   that are relevant to this theme. Include their current approximate price. 
   These do NOT need to be in our portfolio — they are market context.
```

**New field in output schema:**
```json
{
  "theme_tickers": [
    {
      "theme": "copper",
      "tickers": [
        {"symbol": "$FCX", "price": "$60.41", "context": "Largest US copper miner"},
        {"symbol": "$SCCO", "price": "$184.30", "context": "Southern Copper"},
        {"symbol": "$COPX", "price": "$42.15", "context": "Copper miners ETF"}
      ]
    }
  ]
}
```

**Why this matters:** This single addition transforms the system from "only talks about its own portfolio" to "talks about the market, and happens to have positions in some of these names." The theme_tickers field enables THEME_LIST tweets that reference 8+ tickers — the exact content format that drives engagement on FinTwit.

#### Change 3: Today's Substack topic in user prompt

**New block in user prompt (when daily_context.md exists):**
```
Today's Substack post topic: "Ticker Deep Dive — $RCAT: Drone Technology Thesis"
Key insight from the post: Drone defense spending grew 340% YoY in latest DOD budget.
Look for market context that connects to this topic for potential teaser tweets.
```

**Source:** Read from `substack/output/current/daily_context.md` (produced by daily_content.yml from Substack spec). Parse the topic line and any embedded stats.

#### Change 4: FinTwit trending theme overlap detection

**New field in output schema:**
```json
{
  "fintwit_theme_overlaps": [
    {
      "trending_topic": "copper breakout",
      "matching_theme": "copper",
      "our_positions": ["$WCC"],
      "context": "FinTwit buzzing about copper futures hitting 52-week high"
    }
  ]
}
```

This is explicitly requested in the Grok prompt:
```
7. Check if any FinTwit trending topics overlap with our tracked themes. 
   If so, note which theme matches and whether we have positions in it.
```

#### Change 5: Remove tweet_opportunities from Grok output

**Current:** Grok returns `tweet_opportunities` — a pre-analyzed list of tweetable moments with type/urgency. This duplicates the decision logic in live_tweet_generator.py and creates a coupling where Grok's judgment competes with the priority system.

**New:** Remove `tweet_opportunities` from the Grok prompt and output schema. The decision logic in live_tweet_generator.py is the single source of truth for what to tweet. Grok provides **raw market data** (movers, themes, trending, news, external tickers), and the decision function consumes it.

### 5.2 Full Output Schema — Target State

```json
{
  "timestamp": "ISO-8601",
  "market_snapshot": {
    "spy_move": "+0.3%",
    "qqq_move": "-0.1%",
    "iwm_move": "+0.8%",
    "vix": "18.5",
    "market_mood": "mixed|bullish|bearish|volatile|quiet",
    "headline": "one-sentence summary"
  },
  "portfolio_movers": [
    {"ticker": "$WCC", "move": "+2.1%", "price": "$322.40", "context": "..."}
  ],
  "theme_activity": [
    {"theme": "copper", "status": "active|quiet|breaking", "detail": "..."}
  ],
  "theme_tickers": [
    {
      "theme": "copper",
      "tickers": [
        {"symbol": "$FCX", "price": "$60.41", "context": "Largest US copper miner"},
        {"symbol": "$SCCO", "price": "$184.30", "context": "Southern Copper"}
      ]
    }
  ],
  "fintwit_trending": ["topic1", "topic2", "topic3"],
  "fintwit_theme_overlaps": [
    {
      "trending_topic": "copper breakout",
      "matching_theme": "copper",
      "our_positions": ["$WCC"],
      "context": "..."
    }
  ],
  "news_events": [
    {"event": "Fed minutes released", "impact": "...", "relevance": "high|medium|low"}
  ]
}
```

**Removed:** `tweet_opportunities` (decision logic is in generator, not context gatherer)
**Added:** `theme_tickers`, `fintwit_theme_overlaps`, `iwm_move` (small-cap index relevant to portfolio)

---

## 6. TWEET GENERATOR OVERHAUL

### 6.1 Structural Changes to live_tweet_generator.py

**File:** `twitter/live_tweet_generator.py` (2,028 lines → ~1,800 lines)

The generator keeps its overall structure (decide → assign → generate → validate → repair → queue) but with significant internal changes.

#### Change 1: Replace decide_tweet_type() (lines 762-1057 → ~200 lines)

The new 7-priority system (Section 4) replaces the 10-priority cascade. Key structural changes:
- P2 alternates between RECEIPT and MARKET_COMMENTARY using `tracker.last_p2_category`
- P3 adds TRENDING_TAKE with fintwit overlap detection
- P4 adds THEME_LIST and SUBSTACK_TEASER
- Remove P7 (Grok opportunities catch-all)
- Remove P9 (multi-receipt — now handled by thread support in P2)
- Remove P10 (filler — expanded categories provide enough variety)

**New tracker field:**
```python
class RecentTweetTracker:
    # ... existing fields ...
    last_p2_category: Optional[str] = None  # "RECEIPT" or "MARKET_COMMENTARY"
```

Populated during queue scan by checking the most recent P2-level tweet.

#### Change 2: Expand build_allowed_tickers() to include context tickers

**Current:** Only portfolio + signals tickers are "allowed."
**New:** Portfolio + signals + context theme_tickers are allowed (for categories that permit external tickers).

```python
def build_allowed_tickers(
    portfolio: List[Dict], signals: dict, context: Optional[Dict] = None,
) -> Set[str]:
    """Build set of all valid tickers from portfolio + signals + context."""
    tickers = set()
    # ... existing portfolio + signals logic ...
    
    # Add external tickers from Grok context (for THEME_LIST, TRENDING_TAKE, MARKET_COMMENTARY)
    if context:
        for theme_data in context.get("theme_tickers", []):
            for t in theme_data.get("tickers", []):
                sym = t.get("symbol", "").lstrip("$").upper()
                if sym:
                    tickers.add(sym)
    return tickers
```

**Validation step 2 update:** Pass the category to ticker validation. For THEME_LIST, TRENDING_TAKE, and MARKET_COMMENTARY, use the expanded ticker set. For all other categories, use portfolio + signals only (stricter).

#### Change 3: Thread-aware slot assignment in _prepare_slot_data()

When the decision is THEME_LIST or multi-RECEIPT, the slot assignment sets `thread: True` on the relevant variant. The prompt builder then requests thread-formatted output (see Section 7).

#### Change 4: Substack topic injection in build_user_prompt()

On post days, the user prompt includes today's post topic and a key stat (from daily_context.md):

```python
def _inject_substack_context(user_prompt_parts: list, decision: Dict):
    """Add Substack teaser context to the prompt."""
    context_path = Path("substack/output/current/daily_context.md")
    if not context_path.exists():
        return
    content = context_path.read_text()
    # Extract topic line and key stats
    topic_match = re.search(r"## Today's Post: (.+)", content)
    if topic_match:
        user_prompt_parts.append(f"\nTODAY'S SUBSTACK POST: {topic_match.group(1)}")
        user_prompt_parts.append(
            "Generate a teaser tweet that pulls a specific insight from this topic. "
            "Not 'new post is up' — tease the content with a compelling stat or finding."
        )
```

#### Change 5: MARKET_COMMENTARY prompt — positive market framing

**New category examples:**
```python
LIVE_CATEGORY_EXAMPLES["MARKET_COMMENTARY"] = (
    '1) "SPY down 1.5% but our names holding relative strength. '
    '$STRL green, $RCAT flat. Conviction showing."\\n'
    '2) "Russell 2000 outperforming S&P for the 3rd straight week. '
    'Small caps leading is exactly what we want to see for our names."\\n'
    '3) "VIX below 15. Low volatility, steady grind higher. '
    '$WCC quietly holding above entry. Boring is beautiful in this tape."\\n'
    '4) "Defense spending bill advancing. $LMT $RTX catching bids. '
    'Our defense thesis getting catalysts. NFA."'
)
```

Note: examples 2 and 4 show **positive** market commentary — the content type that was impossible under the old system's negative-only MARKET_REACTION trigger.

#### Change 6: Remove standalone recently_tweeted* helper functions

**Lines 416-530** contain standalone `recently_tweeted()`, `recently_tweeted_theme()`, `recently_tweeted_type()`, `count_tweets_today()`, `count_ticker_today()`, `_count_category_this_week()`, `should_post_newsletter_cta()` — all of which duplicate logic already in `RecentTweetTracker`.

**Action:** Delete these functions. Update `decide_tweet_type()` to use `tracker` exclusively. The tracker already has `ticker_at_daily_limit()`, `category_over_weekly_budget()`, `category_at_daily_limit()`, and `ticker_recent_for_account()`.

Add to RecentTweetTracker:
```python
def type_recently_used(self, tweet_type: str, hours: int = 4) -> bool:
    """Check if tweet type was used within N hours (replaces recently_tweeted_type)."""
    cutoff = self._now_et - timedelta(hours=hours)
    for t in self._recent_tweets:
        if t.get("category") == tweet_type:
            gen_et = self._parse_time(t)
            if gen_et and gen_et > cutoff:
                return True
    return False

def theme_recently_used(self, theme: str, hours: int = 6) -> bool:
    """Check if theme was tweeted about within N hours."""
    cutoff = self._now_et - timedelta(hours=hours)
    theme_lower = theme.lower()
    for t in self._recent_tweets:
        if theme_lower in t.get("text", "").lower():
            gen_et = self._parse_time(t)
            if gen_et and gen_et > cutoff:
                return True
    return False
```

---

## 7. THREAD SUPPORT

### 7.1 When Threads Are Used

| Category | Thread Format | When |
|----------|--------------|------|
| `THEME_LIST` | Always 2-3 tweets | Opening hook → ticker list → portfolio positions + CTA |
| `RECEIPT` (multi) | 2-3 tweets | When 3+ winners with >5% gains, no receipt in 24h |

All other categories remain single tweets.

### 7.2 Thread Generation — Prompt Format

When the decision includes `thread: True`, the Sonnet prompt requests thread-formatted output:

```
THREAD FORMAT (for this tweet only):
Generate a 2-3 tweet thread. Each tweet must be <=280 characters independently.
Format:
{
  "tweets": [
    {
      "thread_tweets": [
        {"text": "Opening hook tweet (1/3)", "number": 1},
        {"text": "Detail tweet with tickers (2/3)", "number": 2},
        {"text": "Portfolio connection + CTA (3/3)", "number": 3}
      ],
      "category": "THEME_LIST",
      "primary_ticker": "FCX",
      "chart_recommended": false,
      "account": "variant_2",
      "is_thread": true
    }
  ]
}
```

### 7.3 Thread Validation

Each tweet within a thread passes the same 14-step validation individually. Additional thread-level checks:
- Each tweet ≤280 chars
- Thread has 2-3 tweets (not more)
- Tweet 1 must be a hook (no tickers required)
- Tweet 2-3 must contain specific data (tickers, prices, or stats)
- No banned terms in any tweet
- Thread tickers must all come from allowed set

### 7.4 Thread Queue Schema

```json
{
  "id": "live_20260220_153000_v2_thread",
  "category": "THEME_LIST",
  "primary_ticker": "FCX",
  "account": "variant_2",
  "is_thread": true,
  "thread_tweets": [
    {"text": "Copper is having a moment...", "number": 1},
    {"text": "$FCX $60.41\n$SCCO $184.30\n$COPX $42.15\n$TMQ $6.21\n$CPER $29.80", "number": 2},
    {"text": "We hold $WCC (+14.7%) in this theme. Infrastructure + copper = structural demand. NFA", "number": 3}
  ],
  "chart_recommended": false,
  "status": "pending",
  "generated_at": "2026-02-20T20:30:00+00:00"
}
```

poster.py's existing `post_thread()` function handles this schema — it chains tweets via `in_reply_to_tweet_id`.

---

## 8. PERSONA SYSTEM REDESIGN

### 8.1 Content-Type Affinity Model

Instead of all 3 personas tweeting about the same category with different style, each persona is **weighted toward different content types**.

| Persona | Primary Categories | Secondary Categories | Avoids |
|---------|-------------------|---------------------|--------|
| Alex (The System) | SIGNAL_ALERT, RECEIPT, SELL_SIGNAL, TECHNICAL_ANALYSIS | THEME_CATALYST | ENGAGEMENT, EDUCATIONAL |
| Rozalia (The Mentor) | EDUCATIONAL, THEME_LIST, SUBSTACK_TEASER, THEME_CATALYST | MARKET_COMMENTARY | SELL_SIGNAL |
| James (The Trader) | MARKET_COMMENTARY, TRENDING_TAKE, RECEIPT, ENGAGEMENT | TECHNICAL_ANALYSIS | EDUCATIONAL |

### 8.2 How Affinity Works in _prepare_slot_data()

```python
PERSONA_AFFINITY = {
    "variant_1": {  # Alex
        "primary": {"SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"},
        "secondary": {"THEME_CATALYST", "MARKET_COMMENTARY"},
        "avoids": {"ENGAGEMENT", "EDUCATIONAL"},
    },
    "variant_2": {  # Rozalia
        "primary": {"EDUCATIONAL", "THEME_LIST", "SUBSTACK_TEASER", "THEME_CATALYST"},
        "secondary": {"MARKET_COMMENTARY", "RECEIPT"},
        "avoids": {"SELL_SIGNAL"},
    },
    "variant_3": {  # James
        "primary": {"MARKET_COMMENTARY", "TRENDING_TAKE", "RECEIPT", "ENGAGEMENT"},
        "secondary": {"TECHNICAL_ANALYSIS", "THEME_CATALYST"},
        "avoids": {"EDUCATIONAL"},
    },
}
```

When assigning slots, the decision category is assigned to the persona with the strongest affinity. The other two personas get **different categories** from their own primary/secondary pools based on what's available:

```python
def _prepare_slot_data(decision, portfolio, signals, tracker, context):
    decision_cat = decision["type"]
    
    # Step 1: Assign decision category to best-fit persona
    best_persona = _find_best_persona(decision_cat, PERSONA_AFFINITY)
    
    # Step 2: Assign remaining personas different categories from their pools
    for variant in ACCOUNT_VARIANTS:
        if variant == best_persona:
            continue
        affinity = PERSONA_AFFINITY[variant]
        alt_cat = _pick_available_category(
            primary=affinity["primary"],
            secondary=affinity["secondary"],
            avoids=affinity["avoids"],
            tracker=tracker,
            exclude={decision_cat},  # Don't duplicate the decision category
        )
        # ... assign with ticker selection
```

**Result:** A RECEIPT decision might produce:
- variant_1 (Alex): $RCAT RECEIPT (data-driven angle)
- variant_2 (Rozalia): EDUCATIONAL (methodology lesson)
- variant_3 (James): MARKET_COMMENTARY (market context + portfolio overlay)

Instead of the old system's:
- variant_1: $RCAT RECEIPT (data-driven)
- variant_2: $STRL RECEIPT (explains-why)
- variant_3: $WCC RECEIPT (punchy)

### 8.3 Persona Voice — Unchanged

The style differentiation (tone, traits, signature phrases) stays the same. What changes is **what** each persona talks about, not **how** they talk about it.

---

## 9. SUBSTACK INTEGRATION

### 9.1 How Substack Content Feeds Into Tweets

The Substack subsystem (from SUBSTACK_SUBSYSTEM_CHANGES.md) produces:
- `substack/output/current/daily_context.md` — today's post topic + embedded prompt
- `substack/output/current/daily_notes_context.json` — live data for notes
- `substack/output/current/market_analysis.md` — fresh market analysis

The tweet system reads `daily_context.md` to determine:
1. **Is today a post day?** (If topic is present → yes)
2. **What's the topic?** (Ticker Deep Dive, Theme Rotation, Educational, etc.)
3. **Key stats/insights** (embedded in the context doc)

### 9.2 SUBSTACK_TEASER Category — How It Works

**Trigger:** Today is a post day AND no teaser in last 24h AND budget not exhausted.

**Prompt injection:**
```
SUBSTACK TEASER:
Today's post: "Ticker Deep Dive — $RCAT: Drone Technology Thesis"
Key insight: Drone defense spending grew 340% YoY in latest DOD budget.

Generate a teaser tweet that:
1. Leads with the compelling stat or finding (not "new post is up")
2. Connects it to our portfolio/theme naturally
3. Ends with a soft CTA (link in bio, full breakdown in newsletter)

GOOD: "Drone defense spending up 340% YoY. We've held $RCAT since $8.50. 
Full breakdown of why this thesis is just getting started — link in bio."

BAD: "New post is up! Check out our latest analysis on $RCAT."
```

**Budget:** 4/week (one per post day: Tue, Wed, Thu, Sat). Not posted on rest/gather days.

### 9.3 Post-Day Detection

```python
def _is_post_day() -> bool:
    """Check if today is a Substack post day."""
    day = datetime.now(ZoneInfo("America/New_York")).strftime("%A")
    return day in ("Tuesday", "Wednesday", "Thursday", "Saturday")

def _get_today_post_topic() -> Optional[str]:
    """Read today's post topic from daily_context.md."""
    context_path = Path("substack/output/current/daily_context.md")
    if not context_path.exists():
        return None
    content = context_path.read_text()
    match = re.search(r"## Today's Post: (.+)", content)
    return match.group(1) if match else None
```

---

## 10. DYNAMIC THEME SYNC

### 10.1 Scanner → Grok Theme Flow

```
Friday scan → signals.json contains themes[] array
  └── themes[]: [{name: "AI Power Infrastructure", tickers: [...], strength: ...}, ...]

Daily 07:00 → daily_content.yml writes market_analysis.md
  └── References active themes from signals.json

5x daily → live_tweet.yml (context gatherer)
  └── load_tracked_themes() reads signals.json themes[]
  └── Grok searches for these themes + base themes
  └── Returns theme_activity + theme_tickers for matched themes
```

### 10.2 Theme Freshness

Scanner themes are updated weekly (Friday scan). Between scans, the theme list is stable. This is fine — themes don't change daily.

**Base themes** (copper, infrastructure, defense, AI, semiconductors, nuclear) are always included regardless of scanner output. These represent structural macro themes that are always relevant.

**Scanner themes** (Healthcare Contrarian Recovery, Financial Services AI Adoption, etc.) are added dynamically and may rotate each week.

### 10.3 Theme Ticker Pool for THEME_LIST Tweets

When Grok returns `theme_tickers` for an active theme, the tweet generator has access to external tickers. Combined with portfolio positions in the same theme:

```python
def _build_theme_list_tickers(theme: str, context: Dict, portfolio: List[Dict]) -> List[Dict]:
    """Merge Grok external tickers with portfolio positions for a theme."""
    # External tickers from Grok
    external = []
    for td in context.get("theme_tickers", []):
        if td.get("theme", "").lower() == theme.lower():
            external = td.get("tickers", [])
            break
    
    # Portfolio positions in this theme
    portfolio_in_theme = [
        {"symbol": f"${r['ticker']}", "price": f"${r.get('current_price', r.get('highest_close', '?'))}",
         "context": f"Our position — entry ${r['entry_price']}", "is_portfolio": True}
        for r in portfolio
        if theme.lower() in (r.get('theme', '') or '').lower()
    ]
    
    # Merge: external first, then portfolio (portfolio flagged for special treatment in tweet)
    all_tickers = external + portfolio_in_theme
    return all_tickers[:8]  # Cap at 8 for tweet readability
```

---

## 11. models.py CHANGES

### 11.1 Updated TWEET_CATEGORIES

```python
TWEET_CATEGORIES: Dict[str, Dict] = {
    # ── Core signal categories ──
    "SELL_SIGNAL": {
        "source": "Exit/sell signals in signals.json",
        "chart_required": True,
        "min_elements": ["$TICKER", "invalidation framing"],
        "thread_capable": False,
    },
    "SIGNAL_ALERT": {
        "source": "Scanner signals — PASS (confirmed) or CONSIDER (watching)",
        "chart_required": True,
        "min_elements": ["$TICKER", "entry price"],
        "sub_types": ["confirmed", "watching"],
        "thread_capable": False,
    },
    
    # ── Market-aware categories ──
    "RECEIPT": {
        "source": "Portfolio winners with intraday moves",
        "chart_required": True,
        "min_elements": ["$TICKER", "entry price", "current price", "% gain"],
        "thread_capable": True,  # Multi-ticker receipt threads
    },
    "MARKET_COMMENTARY": {
        "source": "Notable market conditions — any mood (positive, negative, neutral)",
        "chart_required": False,
        "min_elements": ["market context", "portfolio overlay"],
        "thread_capable": False,
    },
    
    # ── Theme categories ──
    "THEME_CATALYST": {
        "source": "Breaking theme with portfolio overlap",
        "chart_required": False,
        "min_elements": ["theme name", "$TICKER"],
        "thread_capable": False,
    },
    "THEME_LIST": {
        "source": "Active theme with external + portfolio tickers",
        "chart_required": False,
        "min_elements": ["theme name", "5+ $TICKERs with prices"],
        "thread_capable": True,  # Always a thread
        "allows_external_tickers": True,
    },
    "TRENDING_TAKE": {
        "source": "FinTwit trending topic ∩ tracked themes",
        "chart_required": False,
        "min_elements": ["trending topic", "our take", "theme connection"],
        "allows_external_tickers": True,
        "thread_capable": False,
    },
    
    # ── Content categories ──
    "TECHNICAL_ANALYSIS": {
        "source": "Position commentary with levels",
        "chart_required": False,  # Recommended, not required
        "min_elements": ["$TICKER", "level"],
        "thread_capable": False,
    },
    "EDUCATIONAL": {
        "source": "Methodology, trading psychology, indicator explainers",
        "chart_required": False,
        "min_elements": ["concrete example"],
        "thread_capable": False,
    },
    "SUBSTACK_TEASER": {
        "source": "Today's Substack post — compelling stat + CTA",
        "chart_required": False,
        "min_elements": ["specific insight", "soft CTA"],
        "thread_capable": False,
    },
    "ENGAGEMENT": {
        "source": "Community building, questions, milestones",
        "chart_required": False,
        "min_elements": [],
        "thread_capable": False,
    },
}
```

### 11.2 Removed Categories

- `NEWSLETTER_CTA` → replaced by `SUBSTACK_TEASER`
- `DIP_OPPORTUNITY` → merged into `MARKET_COMMENTARY`
- `WATCHLIST` → merged into `SIGNAL_ALERT` (sub_type="watching")
- `MARKET_REACTION` → replaced by `MARKET_COMMENTARY` (broader trigger)
- `PERFORMANCE` → redundant with `RECEIPT` (batch system artifact)
- `SCANNER_RESULT` → redundant with `SIGNAL_ALERT` (batch system artifact)
- `DAILY_SIGNAL` → redundant with `SIGNAL_ALERT` (batch system artifact)

### 11.3 Updated Computed Sets

```python
CHART_REQUIRED_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info["chart_required"]
}
# Result: {"SELL_SIGNAL", "SIGNAL_ALERT", "RECEIPT"}

THREAD_CAPABLE_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info.get("thread_capable", False)
}
# Result: {"RECEIPT", "THEME_LIST"}

EXTERNAL_TICKER_CATEGORIES = {
    cat for cat, info in TWEET_CATEGORIES.items() if info.get("allows_external_tickers", False)
}
# Result: {"THEME_LIST", "TRENDING_TAKE"}

VALID_CATEGORIES = set(TWEET_CATEGORIES.keys())
# Result: 11 categories
```

### 11.4 Remove Batch-Only Data Classes

**Delete from models.py:**
- `SlotAssignment` — only used by batch tweet_generator.py weekly scheduling
- `ContentData` — only used by batch tweet_generator.py data aggregation

**Keep:**
- `Tweet` — used by live system
- `ValidationResult` — used by live system

### 11.5 Clean Up Import

**Current last line of models.py:**
```python
from config.banned_terms import INTERNAL_TERM_PATTERNS  # noqa: F401
```

This re-export is used by live_tweet_generator.py. Keep it. But also re-export the new sets (THREAD_CAPABLE_CATEGORIES, EXTERNAL_TICKER_CATEGORIES) for consumer convenience.

---

## 12. VALIDATION PIPELINE CHANGES

### 12.1 Steps That Change

| Step | Current | New |
|------|---------|-----|
| **2** (ticker fabrication) | Check portfolio + signals only | Check portfolio + signals + context_tickers (for EXTERNAL_TICKER_CATEGORIES) |
| **7** (chart flag correction) | Auto-correct based on static category set | Updated for new category set |
| **8** (cross-account dedup) | <70% similarity between 3 variants | **Relaxed for persona affinity** — variants may now be different categories, so high similarity is less likely. Keep 70% threshold. |
| **8.5** (slot collision) | Same ticker check across accounts | **Allow same ticker if different categories.** Alex can post RECEIPT about $RCAT while Rozalia posts EDUCATIONAL about position sizing using $RCAT as example. |
| **9** (context staleness) | Block MARKET_REACTION if stale | Block MARKET_COMMENTARY + TRENDING_TAKE if stale |

### 12.2 New Validation Step: Thread Integrity

Insert after step 6 (character count):

**Step 6c: Thread validation** (only for items with `is_thread: True`)
- Each thread_tweet.text ≤280 chars
- Thread has 2-3 tweets (reject if <2 or >3)
- Tweet 1 must not start with a ticker (hooks should be thematic)
- At least one tweet must contain a $TICKER reference
- No banned terms in any individual tweet

### 12.3 Validation Step 2 — Updated Ticker Check

```python
def _validate_ticker_fabrication(text, category, allowed_tickers, context_tickers):
    """Check that all tickers in text exist in source data."""
    tickers_in_text = re.findall(r'\$([A-Z]{1,5})', text)
    
    # Expanded allowed set for external-ticker categories
    if category in EXTERNAL_TICKER_CATEGORIES:
        full_allowed = allowed_tickers | context_tickers
    else:
        full_allowed = allowed_tickers
    
    fabricated = [t for t in tickers_in_text if t not in full_allowed]
    if fabricated:
        return False, f"Fabricated tickers: {fabricated}"
    return True, ""
```

---

## 13. poster.py CHANGES

### 13.1 Minimal Changes Required

poster.py is well-built and already supports the features needed:
- `post_tweet()` — single tweets with multi-image support ✓
- `post_thread()` — threaded tweets with reply chaining ✓
- `upload_media()` — image upload via v1.1 API ✓
- Pre-post similarity check ✓
- Staggered posting (10-min delays) ✓

### 13.2 Changes

**Change 1: find_next_live_content() — handle thread items**

The function that matches account key → next pending item needs to handle thread items:

```python
def find_next_live_content(queue: List[Dict], account_key: str) -> Optional[Dict]:
    variant_map = {"main": "variant_1", "account2": "variant_2", "account3": "variant_3"}
    target_variant = variant_map.get(account_key)
    
    for item in queue:
        if item.get("status") != "pending":
            continue
        if item.get("account") != target_variant:
            continue
        return item  # Works for both single tweets and thread items
    return None
```

Currently, this function already returns the item regardless of type. The posting path should detect `is_thread` and route to `post_thread()`:

```python
# In post_for_account():
item = find_next_live_content(queue, account_key)
if item.get("is_thread"):
    success = post_thread(client_v2, api_v1, item, dry_run=args.dry_run)
else:
    success = post_tweet(client_v2, api_v1, item, dry_run=args.dry_run)
```

**Change 2: Remove batch queue handling**

poster.py currently handles both batch queues (content_queue.json) and live queue (live_content_queue.json). With the batch system deleted, remove:
- `CONTENT_QUEUE_FILE` references
- `get_queue_path()` batch logic
- `get_daily_queue_path()` 
- `get_queue_for_slot()`
- `find_next_content()` (batch version)
- `get_current_slot()` (batch 7-slot system)

Keep only live queue functions: `find_next_live_content()`, `post_tweet()`, `post_thread()`, `post_for_account()`.

**Estimated impact:** poster.py 1,100 lines → ~700 lines.

---

## 14. CHART SYSTEM CHANGES

### 14.1 chart_generator.py — Keep As-Is

The chart-img.com REST API integration works well:
- CI-compatible (no browser required)
- Never blocks tweet posting on failure
- Atomic queue updates
- Ticker deduplication
- Chart path written back to queue JSON

No changes needed.

### 14.2 chart_capture.py — Delete

**File:** `twitter/chart_capture.py` (749 lines)

Playwright-based TradingView screenshot system. Requires GUI login, browser session, and can't run in CI. Fully superseded by chart_generator.py.

**Delete.** No downstream consumers — batch system is also being deleted.

### 14.3 Chart Attachment for Threads

Threads can optionally have a chart on one tweet (typically tweet 2 or 3). The chart_generator.py already writes `chart_path` per queue item. For threads, the chart_path applies to the entire thread item, and `post_thread()` attaches it to the specified tweet number:

```json
{
  "is_thread": true,
  "chart_path": "/path/to/chart.png",
  "chart_on_tweet": 2,
  "thread_tweets": [...]
}
```

This requires a minor update to `post_thread()` to check `chart_on_tweet` instead of attaching to every tweet that has `image_path`.

---

## 15. SCHEDULE & VOLUME CHANGES

### 15.1 Posting Schedule — Unchanged

| Slot | Weekday (ET) | Weekend (ET) |
|------|-------------|-------------|
| 1 | 07:30 | — |
| 2 | 10:00 | 10:00 |
| 3 | 12:30 | — |
| 4 | 15:30 | — |
| 5 | 18:00 | 16:00 |

No changes to cron schedule. The 5 weekday + 2 weekend slots remain.

### 15.2 Volume Changes

| Metric | Current | Target | Rationale |
|--------|---------|--------|-----------|
| Max tweets/weekday | 12 | 12 | Keep cap, but expect higher quality per tweet |
| Max tweets/weekend | 4 | 4 | Unchanged |
| Tweets per cron run | 3 (one per account) | 3 | Unchanged |
| Weekly total (target) | ~50 | ~45 | Slightly fewer, much more varied |
| Threads/week | 0 | 3-5 | THEME_LIST (2-3) + multi-RECEIPT (1-2) |
| Receipt ratio | ~25% (12/50) | ~16% (7/45) | Reduced to make room for market-relevant content |
| Market-relevant content | ~15% | ~27% | MARKET_COMMENTARY (7) + TRENDING_TAKE (5) |

### 15.3 Weekly Category Budget — Target State

| Category | Budget | % of ~45 | Notes |
|----------|--------|----------|-------|
| RECEIPT | 7 | 16% | Down from 12 — quality over quantity |
| MARKET_COMMENTARY | 7 | 16% | Up from 7 (was MARKET_REACTION, now any-mood) |
| SIGNAL_ALERT | 7 | 16% | Unchanged (now includes CONSIDER sub-type) |
| TRENDING_TAKE | 5 | 11% | New — FinTwit overlap content |
| THEME_CATALYST | 5 | 11% | Renamed from THEME_MOMENTUM |
| ENGAGEMENT | 5 | 11% | Unchanged |
| TECHNICAL_ANALYSIS | 5 | 11% | Unchanged |
| SUBSTACK_TEASER | 4 | 9% | New — replaces NEWSLETTER_CTA (was 2) |
| THEME_LIST | 3 | 7% | New — thread-only format |
| EDUCATIONAL | 3 | 7% | Unchanged |
| SELL_SIGNAL | 3 | 7% | Unchanged |

### 15.4 Weekend Categories — Updated

```python
WEEKEND_CATEGORIES = {
    "EDUCATIONAL", "ENGAGEMENT", "RECEIPT", "SIGNAL_ALERT",
    "SUBSTACK_TEASER",  # Saturday post day
    "THEME_LIST",       # Weekend deep-dive threads are high engagement
}
```

Removed from weekends: MARKET_COMMENTARY, TRENDING_TAKE (require live market data), TECHNICAL_ANALYSIS (intraday levels less relevant).

---

## 16. CONFIGURATION CHANGES

### 16.1 config/settings.py Updates

**Update CATEGORY_WEEKLY_TARGETS:**
```python
CATEGORY_WEEKLY_TARGETS = {
    "RECEIPT": 7,              # Down from 12
    "MARKET_COMMENTARY": 7,    # New (replaces MARKET_REACTION: 7)
    "SIGNAL_ALERT": 7,         # Unchanged
    "TRENDING_TAKE": 5,        # New
    "THEME_CATALYST": 5,       # Renamed from THEME_MOMENTUM: 5
    "ENGAGEMENT": 5,           # Unchanged
    "TECHNICAL_ANALYSIS": 5,   # Unchanged
    "SUBSTACK_TEASER": 4,      # New (replaces NEWSLETTER_CTA: 2)
    "THEME_LIST": 3,           # New
    "EDUCATIONAL": 3,          # Unchanged
    "SELL_SIGNAL": 3,          # Unchanged
}
```

**Remove old category references:**
- `MARKET_REACTION` → now `MARKET_COMMENTARY`
- `THEME_MOMENTUM` → now `THEME_CATALYST`
- `NEWSLETTER_CTA` → now `SUBSTACK_TEASER`
- `DIP_OPPORTUNITY` → absorbed into `MARKET_COMMENTARY`
- `WATCHLIST` → absorbed into `SIGNAL_ALERT`

**Update WEEKEND_CATEGORIES:**
```python
WEEKEND_CATEGORIES = [
    "EDUCATIONAL", "ENGAGEMENT", "RECEIPT", "SIGNAL_ALERT",
    "SUBSTACK_TEASER", "THEME_LIST",
]
```

**Add PERSONA_AFFINITY config:**
```python
PERSONA_AFFINITY = {
    "variant_1": {
        "primary": ["SIGNAL_ALERT", "RECEIPT", "SELL_SIGNAL", "TECHNICAL_ANALYSIS"],
        "secondary": ["THEME_CATALYST", "MARKET_COMMENTARY"],
        "avoids": ["ENGAGEMENT", "EDUCATIONAL"],
    },
    "variant_2": {
        "primary": ["EDUCATIONAL", "THEME_LIST", "SUBSTACK_TEASER", "THEME_CATALYST"],
        "secondary": ["MARKET_COMMENTARY", "RECEIPT"],
        "avoids": ["SELL_SIGNAL"],
    },
    "variant_3": {
        "primary": ["MARKET_COMMENTARY", "TRENDING_TAKE", "RECEIPT", "ENGAGEMENT"],
        "secondary": ["TECHNICAL_ANALYSIS", "THEME_CATALYST"],
        "avoids": ["EDUCATIONAL"],
    },
}
```

**Remove TRACKED_THEMES from config** — now dynamically loaded from signals.json in context gatherer (Section 10).

---

## 17. MODULE INVENTORY

### 17.1 Modules to Delete (3 files, ~3,723 lines)

| File | Lines | Reason |
|------|-------|--------|
| `twitter/tweet_generator.py` | 2,225 | Batch system — redundant with live system |
| `twitter/chart_capture.py` | 749 | Playwright — replaced by chart_generator.py |
| `twitter/verify_tweets.py` | 177 | Tests batch system only |
| **Subtotal** | **3,151** | |

Also delete from `content/` directory (already slated in Substack spec):
- `content/content_generator.py` (1,624 lines) — batch content generation
- Note: this was already counted in the Substack spec deletion total

### 17.2 Modules to Modify (5 files)

| File | Current Lines | Target Lines | Change |
|------|--------------|-------------|--------|
| `twitter/live_tweet_generator.py` | 2,028 | ~1,800 | New priority system, thread support, persona affinity, Substack integration, cleanup duplicate functions |
| `twitter/live_context_gatherer.py` | 533 | ~600 | Dynamic themes, external tickers, Substack topic, remove tweet_opportunities |
| `twitter/poster.py` | 1,100 | ~700 | Remove batch queue handling, add thread routing for live items |
| `twitter/models.py` | 219 | ~180 | New category taxonomy, remove batch data classes |
| `config/settings.py` | (tweet section) | (similar) | Updated budgets, persona affinity, remove old categories |

### 17.3 Modules to Keep As-Is (4 files)

| File | Lines | Reason |
|------|-------|--------|
| `twitter/chart_generator.py` | 359 | Works well, CI-compatible |
| `twitter/cost_tracker.py` | 196 | Kill switch is solid |
| `twitter/health_check.py` | 332 | Diagnostics unchanged |
| `config/banned_terms.py` | 378 | Comprehensive, no changes needed |

### 17.4 Net Line Change

| Category | Lines |
|----------|-------|
| Deleted | -3,151 |
| Reduced (poster.py) | -400 |
| Reduced (models.py) | -39 |
| Reduced (live_tweet_generator.py) | -228 |
| Added (context gatherer) | +67 |
| **Net change** | **-3,751** |
| **Total tweet system** | ~7,886 → ~4,135 lines |

---

## 18. DATA FLOW — TARGET STATE

```
INPUT FILES                              PROCESSING                              OUTPUT FILES
─────────────                            ──────────                              ────────────

portfolio/output/
  portfolio.csv ─────────────────────┐
                                     │
scanner/output/                      │  ┌───────────────────────┐
  signals.json ──────────────────────┼──┤                       │
    (themes[], buy_signals[],        │  │  CONTEXT GATHERER     │
     consider_signals[])             │  │  (Grok xAI)           │
                                     │  │                       │
substack/output/current/             │  │  Dynamic themes from  ├──→ twitter/output/
  daily_context.md ──────────────────┼──┤  scanner output       │      live_context.json
    (today's post topic)             │  │                       │      (enriched with
                                     │  │  External tickers     │       theme_tickers,
twitter/output/                      │  │  for active themes    │       fintwit_overlaps)
  live_content_queue.json ───────────┘  │                       │
    (last 5 posted for avoidance)       │  FinTwit trend ∩      │
                                        │  theme overlap        │
                                        └───────────┬───────────┘
                                                    │
                                                    ▼
                                        ┌───────────────────────┐
portfolio/output/                       │                       │
  portfolio.csv ────────────────────────┤  TWEET GENERATOR      │
                                        │  (Claude Sonnet 4.5)  │
scanner/output/                         │                       │
  signals.json ─────────────────────────┤  7-priority decision  │
                                        │  Persona affinity     │
twitter/output/                         │  Thread support       │
  live_content_queue.json ──────────────┤  Substack teasers     │
  (existing queue for tracker state)    │                       │
                                        │  → 3 variants         │
FINTWIT_STYLE_GUIDE.md ────────────────┤  → per persona        │
                                        │  → some as threads    │
config/banned_terms.py ─────────────────┤                       │
                                        │  14-step validation   │
config/settings.py ─────────────────────┤  + thread validation  │
  (PERSONA_AFFINITY, budgets)           │  + repair loop        │
                                        └───────────┬───────────┘
                                                    │
                                                    ▼
                                        ┌───────────────────────┐
                                        │  CHART GENERATOR      ├──→ twitter/output/charts/
                                        │  (chart-img.com)      │      live_*.png
                                        │  Unchanged            │
                                        └───────────┬───────────┘
                                                    │
                                       ┌────────────┼────────────┐
                                       ▼            ▼            ▼
                                 ┌──────────┐ ┌──────────┐ ┌──────────┐
                                 │ Alex     │ │ Rozalia  │ │ James    │
                                 │ Signals  │ │ Themes   │ │ Market   │
                                 │ Receipts │ │ Education│ │ Trends   │
                                 │ TA       │ │ Substack │ │ Engage   │
                                 │ POST NOW │ │ +10min   │ │ +20min   │
                                 └──────────┘ └──────────┘ └──────────┘
```

---

## 19. GITHUB ACTIONS WORKFLOW CHANGES

### 19.1 live_tweet.yml — Minimal Changes

The workflow structure stays the same (15 steps). Changes:

**Step 5 (gather context):** No code change — `python -m twitter.live_context_gatherer` remains the same command. The module itself is updated internally.

**Step 6 (generate tweet):** No code change — `python -m twitter.live_tweet_generator` remains the same command.

**Step 7 (generate charts):** Unchanged.

**Steps 9-11 (posting):** poster.py internally routes between `post_tweet()` and `post_thread()`. No workflow change needed.

**Remove:** Any references to batch system commands (`python -m twitter.tweet_generator`, `python -m twitter.chart_capture`).

### 19.2 Batch Workflow — Delete

If there's a separate workflow for the batch tweet system (e.g., tweet_content.yml), delete it. All tweet generation is now through live_tweet.yml.

---

## 20. CROSS-SYSTEM DEPENDENCIES

### 20.1 Scanner → Tweet System

| Scanner Output | Tweet Consumer | Used For |
|---------------|---------------|----------|
| `signals.json` → `buy_signals[]` | SIGNAL_ALERT (P1) | Fresh scanner signals |
| `signals.json` → `sell_signals[]` | SELL_SIGNAL (P0) | Exit alerts |
| `signals.json` → `consider_signals[]` | SIGNAL_ALERT sub_type="watching" (P1) | Watchlist content |
| `signals.json` → `themes[]` | Context gatherer → `load_tracked_themes()` | Dynamic theme list |
| `signals.json` → `themes[].tickers` | `find_tickers_for_theme()` | Portfolio tickers by theme |

**Scanner spec changes that affect tweets:**
- `theme` field renamed/restructured → update theme parsing in context gatherer
- `uc` field renamed to `banker` → no tweet impact (banned term anyway)
- `signals_technical.json` → not consumed by tweets (only by merge_decisions)

### 20.2 Substack → Tweet System

| Substack Output | Tweet Consumer | Used For |
|----------------|---------------|----------|
| `daily_context.md` | `_get_today_post_topic()` | SUBSTACK_TEASER trigger + content |
| `market_analysis.md` | Context gatherer (optional) | Enriched market context |

**Substack spec changes that affect tweets:**
- `daily_context.md` is new (doesn't exist yet) → tweet system must handle missing file gracefully
- `content_schedule.json` is being deleted → tweet system never read it (no impact)

### 20.3 Portfolio → Tweet System

| Portfolio Output | Tweet Consumer | Used For |
|-----------------|---------------|----------|
| `portfolio.csv` | Decision logic, prompt building, validation | Position data, P&L, entry prices |

Unchanged. Portfolio system is not being modified in this spec.

### 20.4 Tweet System → Substack / Scanner

The tweet system is **read-only** with respect to upstream systems. It never writes to scanner, Substack, or portfolio outputs.

### 20.5 Implementation Order Constraint

The tweet spec depends on:
1. **Scanner spec** being implemented first (for themes[] in signals.json)
2. **Substack spec** being implemented first (for daily_context.md)

Without these, the tweet system still works but falls back to:
- Static theme list (current behavior) if signals.json has no themes
- No SUBSTACK_TEASER if daily_context.md doesn't exist

Both fallbacks are handled gracefully — no crashes, just reduced content variety.

---

## 21. IMPLEMENTATION ORDER

### Phase 1: Delete Batch System (1 hour)

1. Delete `twitter/tweet_generator.py` (2,225 lines)
2. Delete `twitter/chart_capture.py` (749 lines)
3. Delete `twitter/verify_tweets.py` (177 lines)
4. Remove any batch workflow YAML files
5. Clean config imports referencing batch system
6. Clean poster.py batch queue paths/functions (~400 lines removed)
7. Run existing tests to verify nothing breaks

**Gate:** Live tweet system still works end-to-end after batch deletion.

### Phase 2: Update models.py + config (1 hour)

1. Replace TWEET_CATEGORIES with new taxonomy (Section 11)
2. Add computed sets: THREAD_CAPABLE_CATEGORIES, EXTERNAL_TICKER_CATEGORIES
3. Remove batch data classes (SlotAssignment, ContentData)
4. Update config/settings.py: CATEGORY_WEEKLY_TARGETS, WEEKEND_CATEGORIES, PERSONA_AFFINITY
5. Remove TRACKED_THEMES from config (now dynamic)

**Gate:** Imports work, no circular dependencies, all sets compute correctly.

### Phase 3: Context Gatherer Overhaul (2-3 hours)

1. Implement `load_tracked_themes()` with dynamic scanner themes
2. Update Grok system prompt: add theme_tickers request, remove tweet_opportunities
3. Update output schema parsing for new fields
4. Add Substack topic injection in user prompt
5. Add fintwit_theme_overlaps parsing
6. Test with `--dry-run`: verify enriched context output

**Gate:** Context gatherer returns valid JSON with theme_tickers and fintwit_theme_overlaps.

### Phase 4: Tweet Generator — Priority System (3-4 hours)

1. Replace `decide_tweet_type()` with 7-priority system
2. Add P2 alternation logic (RECEIPT vs MARKET_COMMENTARY)
3. Add P3 TRENDING_TAKE detection
4. Add P4 THEME_LIST trigger (external tickers required)
5. Add P4 SUBSTACK_TEASER trigger
6. Delete standalone recently_tweeted* functions, consolidate to tracker
7. Add `last_p2_category`, `type_recently_used()`, `theme_recently_used()` to tracker
8. Update prompt builder for new categories (examples, framing)
9. Test each priority level with mock context data

**Gate:** Decision tree selects correct categories for test scenarios.

### Phase 5: Tweet Generator — Thread Support + Persona Affinity (2-3 hours)

1. Update `_prepare_slot_data()` with persona affinity routing
2. Add thread-aware prompt building for THEME_LIST and multi-RECEIPT
3. Add thread parsing from Sonnet output
4. Add thread validation step (6c)
5. Update `write_to_live_queue()` to handle thread items
6. Test thread generation end-to-end

**Gate:** Generator produces valid thread items with 2-3 tweets each.

### Phase 6: Validation Pipeline Updates (1 hour)

1. Update step 2 (ticker fabrication) for external ticker categories
2. Update step 9 (context staleness) for new category names
3. Add step 6c (thread integrity)
4. Update step 7 (chart flag) for new category set
5. Relax step 8.5 (slot collision) for same-ticker different-category

**Gate:** Validation passes for test tweets across all categories.

### Phase 7: Integration Testing (2-3 hours)

1. Full pipeline: context gather → decide → generate → validate → queue write
2. Thread posting via poster.py (dry-run)
3. Persona affinity verification: 3 accounts produce different content types
4. Market commentary triggers on positive market conditions
5. Theme list thread with external tickers
6. Substack teaser on post day
7. Trending take when fintwit overlaps themes
8. Weekend category restrictions
9. Budget exhaustion → skip (no filler)
10. Cost tracking: verify daily budget under $1.00

**Total estimated time: 12-16 hours**

---

## 22. TESTING CHECKLIST

### 22.1 Context Gatherer Tests

- [ ] `load_tracked_themes()` returns scanner themes + base themes
- [ ] `load_tracked_themes()` falls back to base themes when signals.json has no themes
- [ ] Grok output contains `theme_tickers` with 5+ tickers per active theme
- [ ] Grok output contains `fintwit_theme_overlaps` when overlap exists
- [ ] `tweet_opportunities` field no longer appears in output
- [ ] Substack topic injected when `daily_context.md` exists
- [ ] Substack topic omitted when `daily_context.md` missing (no crash)
- [ ] `iwm_move` appears in market_snapshot
- [ ] Stale context fallback still works (no regression)

### 22.2 Decision Logic Tests

- [ ] P0: SELL_SIGNAL fires for exit signals
- [ ] P1: SIGNAL_ALERT fires for PASS signals with sub_type="confirmed"
- [ ] P1: SIGNAL_ALERT fires for CONSIDER signals with sub_type="watching"
- [ ] P2 alternation: after RECEIPT, next P2 prefers MARKET_COMMENTARY
- [ ] P2 alternation: after MARKET_COMMENTARY, next P2 prefers RECEIPT
- [ ] P2: MARKET_COMMENTARY fires on bullish market mood (not just bearish/volatile)
- [ ] P2: MARKET_COMMENTARY fires on SPY > +1%
- [ ] P3: TRENDING_TAKE fires when fintwit_trending ∩ tracked themes
- [ ] P3: THEME_CATALYST fires on breaking theme
- [ ] P4: THEME_LIST fires when theme_tickers has 5+ tickers
- [ ] P4: SUBSTACK_TEASER fires on post day (Tue/Wed/Thu/Sat)
- [ ] P5: TECHNICAL_ANALYSIS with diverse ticker rotation
- [ ] P6: ENGAGEMENT as lowest priority
- [ ] All budgets exhausted → SKIP (no filler generation)
- [ ] Weekend: only allowed categories are offered
- [ ] Weekend: MARKET_COMMENTARY not offered (requires live market)

### 22.3 Persona Affinity Tests

- [ ] SIGNAL_ALERT → assigned to Alex (variant_1)
- [ ] THEME_LIST → assigned to Rozalia (variant_2)
- [ ] TRENDING_TAKE → assigned to James (variant_3)
- [ ] Remaining personas get different categories from their pools
- [ ] No persona gets a category in its "avoids" list (unless no alternatives)
- [ ] Three variants have different categories (not just different angles on same category)

### 22.4 Thread Tests

- [ ] THEME_LIST produces 2-3 tweet thread (not single tweet)
- [ ] Multi-RECEIPT (3+ winners) produces 2-3 tweet thread
- [ ] Each tweet in thread ≤280 chars
- [ ] Thread tweet 1 is a hook (no ticker required)
- [ ] Thread tweets 2-3 contain specific tickers
- [ ] Thread item has `is_thread: True` in queue JSON
- [ ] Thread item has `thread_tweets` array with text + number
- [ ] poster.py routes to `post_thread()` for thread items
- [ ] Thread reply chaining works (in_reply_to_tweet_id set correctly)

### 22.5 Validation Tests

- [ ] Step 2: External tickers allowed for THEME_LIST and TRENDING_TAKE
- [ ] Step 2: External tickers rejected for RECEIPT and SIGNAL_ALERT
- [ ] Step 6c: Thread with 4+ tweets rejected
- [ ] Step 6c: Thread with 0-1 tweets rejected
- [ ] Step 9: MARKET_COMMENTARY blocked when context stale
- [ ] Step 9: TRENDING_TAKE blocked when context stale
- [ ] Step 8.5: Same ticker on Alex (RECEIPT) and Rozalia (EDUCATIONAL) → allowed

### 22.6 Substack Integration Tests

- [ ] SUBSTACK_TEASER produced on Tuesday (Ticker Deep Dive day)
- [ ] SUBSTACK_TEASER includes specific stat from daily_context.md
- [ ] SUBSTACK_TEASER NOT produced on Monday (gather day — no post)
- [ ] No crash when daily_context.md missing
- [ ] Teaser content is specific, not generic "link in bio"

### 22.7 End-to-End Integration

- [ ] Full weekday pipeline: context → decide → generate → validate → chart → post (dry-run)
- [ ] Full weekend pipeline: same (reduced categories)
- [ ] 3 accounts produce substantively different tweets (different categories, not just style)
- [ ] Thread posts create connected thread on X (dry-run)
- [ ] No MARKET_REACTION, DIP_OPPORTUNITY, WATCHLIST, or NEWSLETTER_CTA appear (old categories)
- [ ] Cost per run < $0.25
- [ ] Daily cost for 5 runs < $1.00

---

## 23. COST ANALYSIS

### 23.1 Per-Run Cost — Target State

| Component | Model | Est. Input Tokens | Est. Output Tokens | Tool Calls | Est. Cost |
|-----------|-------|-------------------|-------------------|------------|-----------|
| Context gather | grok-4-fast | ~2,000 | ~1,500 | 3-5 search | $0.02-0.05 |
| Tweet generation | claude-sonnet-4.5 | ~4,000 | ~800 | 0 | $0.02-0.03 |
| Repair (if needed) | claude-sonnet-4.5 | ~2,000 | ~400 | 0 | $0.01-0.02 |
| Charts | chart-img.com | — | — | — | $0.01 |
| **Total per run** | | | | | **$0.06-0.11** |

### 23.2 Daily Cost — Target State

| Day Type | Runs | Cost Range |
|----------|------|-----------|
| Weekday (5 slots) | 5 | $0.30-0.55 |
| Weekend (2 slots) | 2 | $0.12-0.22 |

**Weekly total: ~$1.70-3.10**

This is slightly higher than the current ~$0.35-1.00/day because:
1. Grok context is now richer (more tool calls for theme_tickers)
2. Thread generation occasionally requires longer output tokens

Still well within the $1/day kill switch (per-run, not daily total). The kill switch resets daily so the $1 limit applies to accumulated costs on that day. With 5 runs at $0.06-0.11 each, we're at $0.30-0.55 — safely under.

### 23.3 Monthly Budget

Current: ~$15-25/month
Target: ~$7-13/month

The $30/month alert threshold is comfortable.

---

## 24. SUMMARY STATISTICS

| Metric | Current | Target | Change |
|--------|---------|--------|--------|
| Total tweet system lines | ~7,886 | ~4,135 | -47% |
| Categories | 16 (many redundant) | 11 (each distinct) | -31% |
| Priority levels | 10 | 7 | -30% |
| Receipt share of tweets | ~25% | ~16% | -36% (freed for market content) |
| Market-relevant content | ~15% | ~27% | +80% |
| Content requiring portfolio tickers | 100% | ~70% | -30% (external tickers enabled) |
| Thread-capable categories | 0 | 2 | New capability |
| Personas posting same category | Always | Rarely | Substantive differentiation |
| Theme sync with scanner | None (hardcoded) | Dynamic | Auto-updates weekly |
| Substack → tweet pipeline | None | Active | 4 teasers/week |
| Batch system | 2,225 lines (unused) | Deleted | Clean codebase |
| Playwright chart system | 749 lines (unused) | Deleted | CI-only charts |

### Key Wins

1. **Feed feels like a market-aware trader**, not a portfolio highlight reel. MARKET_COMMENTARY fires on positive conditions. TRENDING_TAKE connects to what FinTwit is discussing. THEME_LIST produces the multi-ticker posts that get bookmarked and shared.

2. **Each account has a distinct identity**, not just a different writing style. Alex posts signals and receipts. Rozalia educates and curates themes. James reacts to markets and engages the community.

3. **The highest-engagement content formats are now producible.** Multi-ticker theme lists (threads), rich market commentary, trend-driven takes — all previously impossible due to 280-char constraint and portfolio-only ticker pool.

4. **Scanner and Substack outputs flow into tweets automatically.** New themes appear in Grok searches the same week they're detected. Substack deep dives generate teasers on post days.

5. **47% less code** with more capability. Batch system deletion and poster.py cleanup remove thousands of lines that were causing confusion without adding value.

---

## END OF SPECIFICATION

**Next steps after implementation:**
1. Style guide audit — update FINTWIT_STYLE_GUIDE.md with new category examples (MARKET_COMMENTARY positive, THEME_LIST thread format, TRENDING_TAKE, SUBSTACK_TEASER)
2. Prompt 7 schema alignment — ensure Saturday prompt library references align with new category names
3. A/B testing — compare engagement metrics (likes, retweets, follows) for 2 weeks pre/post changes
4. Cost monitoring — watch daily costs for first week, adjust Grok tool call budget if needed
