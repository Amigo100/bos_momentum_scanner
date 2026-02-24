# Sterling Signals X/Twitter Automation Audit

**Document:** 05-twitter-automation.md
**Last Updated:** 2026-01-29
**Status:** Complete
**Auditor:** Claude Opus 4.5

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Post Types and Triggers](#2-post-types-and-triggers)
3. [Template Formats and Dynamic Data](#3-template-formats-and-dynamic-data)
4. [Marketing Safeguards](#4-marketing-safeguards-critical)
5. [Selective Showcase System](#5-selective-showcase-system)
6. [Posting Pipeline](#6-posting-pipeline)
7. [API Integration](#7-api-integration)
8. [Vocabulary Translation](#8-vocabulary-translation)
9. [Multi-Account System](#9-multi-account-system)
10. [Concerns and Gaps](#10-concerns-and-gaps)

---

## 1. System Overview

The Twitter automation system generates and posts 28-35 tweets per week across up to 3 X/Twitter accounts. Content is generated on Friday via Claude API, stored in JSON queues, and posted daily via GitHub Actions on a 5-slot schedule.

### Architecture

```
Friday Scan (friday_scan.yml)
  └─ tweet_generator.py
       ├─ Load briefing data (newsletter_briefing.md)
       ├─ Check safeguards (signal_tracker.py)
       ├─ Generate 28-35 tweets via Claude API
       ├─ Validate all tweets (8-point check)
       ├─ Save content_queue.json (main account)
       └─ --generate-variations (optional)
            ├─ content_queue_account2.json (conversational)
            └─ content_queue_account3.json (data-driven)

Daily Posting (daily_post.yml) — 5 cron triggers/day
  └─ twitter_poster.py
       ├─ Determine slot from UTC hour
       ├─ Load account-specific queue
       ├─ Find next pending tweet for slot
       ├─ validate_before_posting() — final gate
       ├─ Upload media (v1.1 API) if image_path set
       ├─ Post tweet (v2 API)
       ├─ Update queue status → "posted"
       └─ Repeat for account2, account3 (10-min stagger)
```

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `tweet_generator.py` | Content generation via Claude | ~3117 |
| `twitter_poster.py` | Posting pipeline + API | ~758 |
| `signal_tracker.py` | Portfolio filtering + safeguards | ~1136 |
| `config.py` | Thresholds, banned terms, accounts | ~961 |
| `marketing_vocabulary.py` | Vocabulary validation + translation | ~341 |
| `grok_prompts_generator.py` | Legacy prompt generation | ~1477 |

---

## 2. Post Types and Triggers

### 2.1 Active Post Categories (21 types)

| Category | Trigger/Data Source | Tweets/Week | Safeguarded |
|----------|-------------------|-------------|-------------|
| `buy_signal` / `teal_signal` | `pass_signals` from scanner | 3-4 | No |
| `theme_hot` | PRIME + INVESTABLE themes | 4-5 | No |
| `theme_cold` | SELECTIVE + AVOID themes | 2-3 | No |
| `closed_trade` | `closed_trades` (wins AND losses) | 2-3 | No |
| `sell_signal` / `violet_alert` | `sell_signals` filtered to pnl_pct > 0 | 1-2 | Yes (profitable only) |
| `system_promo` | Static (5-gate system description) | 2-3 | No |
| `market_insight` | `prime_themes` + macro context | 2-3 | No |
| `educational` | Static templates (methodology) | 3-4 | No |
| `engagement` | Static templates (questions/polls) | 3-4 | No |
| `beat_spy` / `benchmark_alpha` | `calculate_portfolio_vs_spy()` | 1-2 | Yes (threshold) |
| `power_hour` | Themes only — NO individual P&L | 3-4 | Yes (theme-only) |
| `sector_rotation` | Hot/cold theme rotation data | 2-3 | No |
| `funnel_graphic` | Scan stats (1817→6 TEAL) | 2-3 | No |
| `post_mortem` | STOPPED positions analysis | 1-2 | No |
| `top_performers` / `winner_showcase` | `filter_public_positions()` | 1-2 | Yes (winners only) |
| `self_quote` / `milestone_alerts` | `get_uncelebrated_wins()` | 1-2 | Yes (thresholds) |
| `consider_spotlight` / `amber_watch` | `consider_signals` (4/5 gates) | 1-2 | No |
| `weekly_recap` | All signal types + performance | 1-2 | No |
| `thread_buy_signal` | Educational 5-tweet thread | 1/week | No |
| `early_movers` | New positions showing 5%+ early | 1 | Yes (positive only) |

### 2.2 Killed Categories (permanently disabled)

| Category | Reason | Fallback |
|----------|--------|----------|
| `position_update` | Shows individual P&L (avoided) | `top_performers` |
| `roth_ira` | Region-specific | `theme_hot` |
| `pdt_friendly` | Region-specific | `educational` |
| `weekly_wins` | Survivorship bias risk | `theme_hot` |

Enforcement: `tweet_generator.py:297-299`, `twitter_poster.py:141-143`, `config.py:58-64`

### 2.3 Daily Slot Schedule (Eastern Time)

| Slot | Time (ET) | UTC Cron | Content Focus |
|------|-----------|----------|---------------|
| 1 | 08:00 | 13:00 | Pre-market / Winners / Signals |
| 2 | 10:00 | 15:00 | Themes / Threads / Self-quotes |
| 3 | 12:30 | 17:30 | Beat SPY / Power Hour / Themes |
| 4 | 15:30 | 20:30 | Power Hour (CRITICAL) / Education |
| 5 | 18:00 | 23:00 | Engagement / Education |

### 2.4 Weekly Category Schedule

| Day | Slot 1 | Slot 2 | Slot 3 | Slot 4 | Slot 5 |
|-----|--------|--------|--------|--------|--------|
| Sat | `top_performers`* | `thread` | `theme_hot` | `funnel` | `engagement` |
| Sun | `buy_signal` | `consider` | `beat_spy`* | `engagement` | — |
| Mon | `theme_hot` | `self_quote`* | `power_hour` | `engagement` | — |
| Tue | `early_movers` | `theme_hot` | `power_hour` | `educational` | — |
| Wed | `consider` | `theme_hot` | `power_hour` | `engagement` | — |
| Thu | `beat_spy`* | `self_quote`* | `power_hour` | `educational` | — |
| Fri | `buy_signal` | `funnel` | `power_hour` | `theme_hot` | — |

\* Safeguarded — falls back to alternative if conditions not met.

---

## 3. Template Formats and Dynamic Data

### 3.1 Template Architecture

Each category uses a Claude prompt containing:
1. **Context section** — dynamic data injected (tickers, themes, P&L figures)
2. **Instructions** — writing guidelines specific to category
3. **Example formats** — concrete tweet examples
4. **Critical rules** — marketing compliance constraints

The Claude API generates the actual tweet text based on these structured prompts.

### 3.2 Key Category Templates

#### `buy_signal` / `teal_signal` (tweet_generator.py:805-854)

**Dynamic data:** `{num_signals}`, `{content.pass_signals}` (JSON with tickers, conviction, themes)

**Template pattern:**
```
🟢 TEAL Signals this week:
$TICKER1 - Extremely Bullish (conv 5)
$TICKER2 - Bullish (conv 4)
Cleared all 5 gates.
sterlingsignals.substack.com
```

**Rules:** Must use "TEAL signal" branding. Must show ALL signals, not just one.

#### `closed_trade` (tweet_generator.py:934-996)

**Dynamic data:** `{content.closed_trades}` (status, entry_price, exit_price, pnl_pct)

**Win template:**
```
✅ $TICKER closed for +XX%
Entry: $XX.XX → Exit: $YY.YY
What worked: [bullets]
sterlingsignals.substack.com
```

**Loss template:**
```
🔴 $TICKER stopped out at -XX%
No system wins 100%. Here's what happened:
[explanation]
This is why we have rules.
sterlingsignals.substack.com
```

**Rules:** Must show BOTH wins AND losses (honesty). No specific stop percentages.

#### `top_performers` (tweet_generator.py:1424-1481)

**Dynamic data:** Filtered to winners only (pnl_pct >= 15%). Entry prices shown only if pnl_pct >= 25%.

**Template pattern:**
```
🟢 TEAL Signal Winners
$TICKER1: +XX% (Xw held)
$TICKER2: +XX% (Xw held)
Returns measured from entry.
sterlingsignals.substack.com
```

**Rules:** ALWAYS include holding period. Never mention losers.

#### `power_hour` (tweet_generator.py:1296-1336)

**Dynamic data:** Theme names only (prime_themes, avoid_themes)

**Template pattern:**
```
⚡ POWER HOUR
Watching [THEME] theme into close.
Relative strength vs broad market.
sterlingsignals.substack.com
```

**CRITICAL rule:** NO individual ticker P&L. NO position updates. Theme-level observations ONLY.

#### `beat_spy` (tweet_generator.py:1228-1284)

**Dynamic data:** `calculate_portfolio_vs_spy()` result (portfolio avg vs SPY return)

**Template pattern:**
```
📊 Portfolio vs $SPY
Our signals: +XX.X%
S&P 500: +YY.Y%
Alpha: +ZZ.Z%
sterlingsignals.substack.com
```

**Safeguard:** Only posted if outperformance >= 5% (config MARKETING_THRESHOLDS).

### 3.3 Thread Format (5-tweet educational threads)

**Structure in content_queue.json:**
```json
{
  "is_thread": true,
  "thread_topic": "Signal Methodology",
  "thread_tweets": [
    {"number": 1, "text": "1/5 [Opening hook]", "image_path": null},
    {"number": 2, "text": "2/5 [Explanation]"},
    {"number": 3, "text": "3/5 [Data point]"},
    {"number": 4, "text": "4/5 [Example]", "image_path": "twitter/output/charts/..."},
    {"number": 5, "text": "5/5 [CTA]"}
  ]
}
```

Posted via reply-chain: each tweet replies to the previous, creating a visible thread on X.

---

## 4. Marketing Safeguards (CRITICAL)

### 4.1 Four-Layer Validation Architecture

```
Layer 1: CONFIG           config.py BANNED_TERMS + MARKETING_THRESHOLDS
    ↓
Layer 2: GENERATION       tweet_generator.py validate_tweet_before_queue() — 8 checks
    ↓
Layer 3: BATCH            marketing_vocabulary.py validate_all_tweets()
    ↓
Layer 4: POSTING          twitter_poster.py validate_before_posting() — 5 checks
```

### 4.2 Layer 1: Configuration (config.py:266-410)

**MARKETING_THRESHOLDS:**

| Threshold | Value | Purpose |
|-----------|-------|---------|
| `min_win_to_highlight` | 15.0% | Minimum gain for top_performers |
| `big_win_threshold` | 25.0% | Self-quote / milestone tweet |
| `home_run_threshold` | 50.0% | Celebration post |
| `hall_of_fame_threshold` | 100.0% | Thread-worthy reference |
| `spy_outperformance_min` | 5.0% | Beat SPY posting gate |
| `min_winners_for_top_performers` | 2 | Minimum winners needed |
| `max_loss_to_mention` | -5.0% | Never show losses publicly |
| `cold_streak_threshold` | 3 | Consecutive losses trigger |
| `max_ticker_mentions_per_week` | 4 | Ticker frequency cap |

**BANNED_TERMS (45+ terms):** Strategy internals (HMA, Banker, BoS, Beta >=), geographic markers (UK ISA, GMT, BST), audience-specific (Roth IRA, PDT, 401k), technical indicators (RSI, MACD, KDJ), leaked marketing language (Capital Preservation Protocol, Forensic Audit, 5th Gate).

**STOPPED_POSITION_RULES (config.py:776-783):**
```python
show_in_public_content: False
show_in_newsletter: False
show_in_top_performers: False
show_in_any_tweet: False
```

### 4.3 Layer 2: Generation Validation (tweet_generator.py:238-352)

`validate_tweet_before_queue()` runs **8 checks** on every generated tweet:

| # | Check | Action on Fail |
|---|-------|----------------|
| 1 | Killed categories (roth_ira, pdt_friendly, position_update, weekly_wins) | Reject |
| 2 | Length <= 280 chars (emoji-aware counting) | Reject |
| 3 | Banned terms (word-boundary regex for short terms, substring for long) | Reject |
| 4 | Negative P&L pattern (`-\d+\.?\d*%`) | Reject — "LOSER SHOWN" |
| 5 | TEAL branding present in signal tweets | Reject |
| 6 | Holding period context with any P&L display | Reject |
| 7 | US-specific content (roth, 401k, pdt, pattern day) | Reject |
| 8 | Ticker frequency <= 4 mentions/week | Reject |

### 4.4 Layer 3: Batch Vocabulary Validation (marketing_vocabulary.py:231-256)

After all tweets generated, `validate_all_tweets()` scans the full batch:
- Case-insensitive checking against BANNED_TERMS
- Word-boundary regex for short terms (RSI, BoS, GMT, BST)
- Reports violation count + specific terms found
- Warning-level (does not block, but logs)

### 4.5 Layer 4: Final Posting Gate (twitter_poster.py:95-161)

`validate_before_posting()` — last check before API call:

| # | Check | Action on Fail |
|---|-------|----------------|
| 1 | Negative P&L regex | Block — status = "blocked" |
| 2 | Critical banned terms (15 high-severity terms) | Block |
| 3 | Killed categories | Block |
| 4 | US-specific patterns (regex) | Block |
| 5 | Length > 280 chars | Block |

Blocked tweets are recorded with `block_reason` in the queue JSON but never posted.

### 4.6 Duplicate Prevention (twitter_poster.py:69-88)

`is_duplicate_content()` compares normalized tweet text against all previously posted tweets in the queue. Duplicates are marked `status: "skipped"`.

---

## 5. Selective Showcase System

### 5.1 Position Filtering for Public Content

**Primary filter:** `signal_tracker.py:filter_public_positions()` (lines 690-741)

```
Input: All open positions from portfolio.csv
  ↓
Remove: status == "STOPPED"
Remove: pnl_pct < 0 (any losing position)
  ↓
Sort: by pnl_pct descending
  ↓
Output: Only winning, active positions
```

This function is called by tweet_generator.py before generating `top_performers`, `beat_spy`, and `self_quote` categories.

### 5.2 Safeguard Functions in signal_tracker.py

| Function | Lines | Purpose | Threshold |
|----------|-------|---------|-----------|
| `filter_public_positions()` | 690-741 | Remove losers + stopped | pnl_pct > 0 |
| `has_enough_wins()` | 615-658 | Gate for top_performers | >= 2 winners at 15%+ |
| `should_post_beat_spy()` | 609-612 | Gate for beat_spy | >= 5% outperformance |
| `get_uncelebrated_wins()` | 661-664 | Gate for self_quote | 25%/50%/100% thresholds |
| `check_cold_streak()` | 988-1061 | Circuit breaker | >= 3 losses in 14 days |
| `get_winners_for_showcase()` | 751-812 | Curated winner list | >= 25%, max 5 |
| `get_early_movers()` | 875-936 | New signals with early gains | < 14 days, >= 5% |

### 5.3 Cold Streak Circuit Breaker

When `check_cold_streak()` detects >= 3 consecutive losses in the last 14 days:

```python
# tweet_generator.py:3089-3097
can_post_beat_spy = False          # Suppress portfolio comparison
can_post_top_performers = False    # Suppress winners showcase
uncelebrated_wins = []             # Suppress milestone celebrations
```

All safeguarded categories fall back to safe alternatives (educational, theme, engagement content).

### 5.4 Dynamic Category Fallbacks (tweet_generator.py:1712-1741)

```python
beat_spy_or_fallback = "beat_spy" if can_post_beat_spy else "engagement"
top_performers_or_fallback = "top_performers" if can_post_top_performers else "theme_hot"
self_quote_or_fallback = "self_quote" if uncelebrated_wins else "theme_hot"
```

### 5.5 Entry Price Display Rules

- Entry prices shown **only** for positions with pnl_pct >= 25% (tweet_generator.py:1438-1452)
- All P&L displays **must** include holding period context (e.g., "4 weeks held")
- Enforced by validation check #6

### 5.6 Sell Signal Filtering

`sell_signal` / `violet_alert` category (tweet_generator.py:1004-1007):
```python
profitable_exits = [s for s in content.sell_signals if s.get('pnl_pct', 0) > 0]
```

Only profitable exits are shown in sell signal tweets. Losing exits appear only in the `closed_trade` and `post_mortem` categories which frame them as "system working as designed."

---

## 6. Posting Pipeline

### 6.1 End-to-End Flow

```
                      daily_post.yml (GitHub Actions)
                              │
                    ┌─────────▼──────────┐
                    │  Determine Slot     │  UTC hour → slot 1-5
                    │  (workflow step)     │  Range-based windows
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Download Artifact  │  content-queue artifact
                    │  (if exists)        │  from friday_scan.yml
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Check Queue Exists │  Fail if no queue
                    │  (GAP 29 fix)       │  (no silent failures)
                    └─────────┬──────────┘
                              │
               ┌──────────────▼───────────────┐
               │  twitter_poster.py            │
               │  --slot N --account main      │
               │                               │
               │  1. load_queue()              │
               │  2. find_next_content()       │
               │  3. is_duplicate_content()    │
               │  4. validate_before_posting() │
               │  5. upload_media() (if image) │
               │  6. post_tweet() / post_thread()
               │  7. save_queue() (atomic)     │
               └──────────────┬───────────────┘
                              │
                         sleep 600s
                              │
               ┌──────────────▼───────────────┐
               │  twitter_poster.py            │
               │  --slot N --account account2  │
               │  (same pipeline, own queue)   │
               └──────────────┬───────────────┘
                              │
                         sleep 600s
                              │
               ┌──────────────▼───────────────┐
               │  twitter_poster.py            │
               │  --slot N --account account3  │
               └──────────────┬───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  git commit + push  │  Update queue status
                    │  (with rebase)      │  GAP 33 race fix
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Upload artifact    │  Persist updated queues
                    └─────────────────────┘
```

### 6.2 Slot Determination (daily_post.yml:76-101)

GitHub Actions uses UTC hour ranges to handle scheduler delays (up to 60 min):

| Slot | UTC Window | ET Window |
|------|------------|-----------|
| 1 | 13:00-14:59 | 08:00-09:59 |
| 2 | 15:00-16:59 | 10:00-11:59 |
| 3 | 17:00-19:59 | 12:00-14:59 |
| 4 | 20:00-22:59 | 15:00-17:59 |
| 5 | 23:00-00:59 | 18:00-19:59 |

### 6.3 Tweet Selection (twitter_poster.py:319-360)

`find_next_content()` algorithm:
1. Filter to `status == "pending"`
2. If `--slot` specified, filter to matching slot
3. If `--force`, return first matching pending tweet
4. Otherwise: return tweet where `scheduled_date` is today or past AND `slot <= current_slot`

### 6.4 Queue Persistence (twitter_poster.py:262-284)

Atomic write via temp file + rename pattern:
```python
temp_file = tempfile.NamedTemporaryFile(suffix='.json', dir=queue_dir, prefix='.queue_tmp_')
json.dump(queue, temp_file)
shutil.move(temp_file.name, queue_file)  # POSIX atomic rename
```

### 6.5 Tweet Status Lifecycle

```
pending → posted    (successful API call)
pending → failed    (API error — tweepy.TweepyException)
pending → blocked   (validation failure — validate_before_posting)
pending → skipped   (duplicate detected)
```

**Posted record fields:**
```json
{
  "status": "posted",
  "posted_at": "2026-01-25T23:39:01.808788",
  "tweet_id": "2015570131636687153"
}
```

---

## 7. API Integration

### 7.1 Dual-Client Architecture (twitter_poster.py:168-216)

| Client | API Version | Purpose | Auth |
|--------|-------------|---------|------|
| `client_v2` | Twitter API v2 | `create_tweet()` — post text + attach media | OAuth 1.0a User Context |
| `api_v1` | Twitter API v1.1 | `media_upload()` — upload images | OAuth 1.0a |

Both clients use the same OAuth 1.0a credentials (Consumer Key/Secret + Access Token/Secret).

### 7.2 Credential Loading (twitter_poster.py:178-195)

Per-account credential resolution via environment variable prefix:

```
Account "main"    → X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
Account "account2" → X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET
Account "account3" → X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET
```

Missing credentials → warning printed, account skipped (non-fatal).

### 7.3 Media Upload Flow (twitter_poster.py:367-390)

```
image_path field in queue JSON
    ↓
Resolve to absolute path (BASE_DIR / image_path)
    ↓
Fallback: TRADES_DIR / image_path
    ↓
api_v1.media_upload(path) → media_id_string
    ↓
client_v2.create_tweet(text=..., media_ids=[media_id])
```

**Non-fatal:** If media upload fails, tweet posts without image.

### 7.4 Thread Reply Chain (twitter_poster.py:530-625)

```python
reply_to_id = None  # First tweet is standalone
for tweet in thread_tweets:
    response = client_v2.create_tweet(
        text=tweet['text'],
        media_ids=media_ids,
        in_reply_to_tweet_id=reply_to_id  # Chain to previous
    )
    reply_to_id = response.data['id']  # Next replies to this
    time.sleep(1)  # Rate limit protection
```

### 7.5 Quote Tweets (twitter_poster.py:472-527)

For milestone celebrations quoting original TEAL signal:
```python
client_v2.create_tweet(text=quote_text, quote_tweet_id=original_tweet_id)
```

### 7.6 Error Handling

| Scenario | Handler | Recovery |
|----------|---------|----------|
| API posting error | `tweepy.TweepyException` caught | status = "failed", error stored |
| Media upload error | Generic `Exception` caught | Post without media (non-fatal) |
| Missing credentials | Check at `get_clients()` | Return (None, None), skip account |
| Queue file missing | `sys.exit(1)` | Workflow fails explicitly |
| JSON parse error | `JSONDecodeError` caught | `sys.exit(1)` |
| Thread partial failure | Set `thread_status = "partial"` | Stop remaining tweets |

**No automatic retry logic.** Failed tweets remain in "failed" status. This is intentional to prevent accidental re-posts.

### 7.7 Rate Limiting

| Context | Delay | Location |
|---------|-------|----------|
| Between thread tweets | 1 second | twitter_poster.py:607-608 |
| Between accounts | 10 minutes (600s) | daily_post.yml:148,152 |
| No other rate limiting | — | Relies on 5 slots/day being well-spaced |

---

## 8. Vocabulary Translation

### 8.1 Internal → Public Term Mapping

| Internal Term | Public Alternative | Enforcement |
|---------------|-------------------|-------------|
| Buy signal / PASS signal | **TEAL signal** | Auto-fix + validation |
| 20% trailing stop | "Trailing stop" / "Systematic stop" | Banned term check |
| HMA pivot | "Momentum confirmed" / "Structural pivot" | Banned term check |
| Banker indicator / Banker >= 55 | "Institutional accumulation" / "Strong accumulation" | Banned term check |
| Beta >= 1.5 | "Volatility characteristics" | Banned term check |
| Break of Structure / BoS | "Momentum confirmed" / "Technical setup" | Banned term check |
| Gatekeeper / Gate 5 / 5th Gate | "Cleared all gates" / "Final gate" | Banned term check |
| Tier 1/2/3 | "High conviction" | Banned term check |
| Forensic Audit | "Final gate" | Banned term check |
| Capital Preservation Protocol | "Systematic exit" | Banned term check |
| CAUTION signal | "Amber watch" | Template convention |
| STOPPED position | Not shown publicly | filter_public_positions() |

### 8.2 Approved Power Phrases (marketing_vocabulary.py:100-126)

- "Proprietary 5-gate screening system"
- "Filters 1,800 stocks to 3-5 actionable signals"
- "Institutional-grade momentum analysis"
- "TEAL signal triggered"
- "Cleared all 5 gates"
- "Systematic exit discipline"
- "Trailing stop in place"
- "No ego, just execution"
- "The system protects capital"

### 8.3 Audience Hooks (marketing_vocabulary.py:132-157)

| Hook | Example Phrases |
|------|-----------------|
| Beat SPY | "Stop indexing. Start selecting." |
| Time-friendly | "Weekly timeframe suits busy schedules" |
| Power Hour | "Power Hour Check:", "Volume confirmation in final hour" |
| Sector Rotation | "Money is rotating.", "Follow institutional flows" |

### 8.4 Auto-Fix: TEAL Branding (config.py:444-469)

`enforce_teal_branding()` automatically replaces non-branded terms:
- "buy signal" → "TEAL signal"
- "PASS signal" → "TEAL signal"
- "our signal" → "TEAL signal"

Applied during generation validation (Layer 2).

---

## 9. Multi-Account System

### 9.1 Account Configuration (config.py:131-150)

```python
TWITTER_ACCOUNTS = {
    'main': {
        'env_prefix': 'X',
        'queue_file': 'content_queue.json',
        'offset_minutes': 0,
        'variation_style': 'original',
    },
    'account2': {
        'env_prefix': 'X2',
        'queue_file': 'content_queue_account2.json',
        'offset_minutes': 10,
        'variation_style': 'conversational',
    },
    'account3': {
        'env_prefix': 'X3',
        'queue_file': 'content_queue_account3.json',
        'offset_minutes': 20,
        'variation_style': 'data_driven',
    },
}
```

### 9.2 Variation Generation (tweet_generator.py:2807-2970)

Single Claude API call rephrases all 35 base tweets into 2 style variants:
- **Variation A (account2):** Conversational tone, "we" + "our", informal
- **Variation B (account3):** Data-driven/analytical, lead with numbers

Rules: Same meaning, tickers, facts. Within 280 chars. Keep TEAL branding + URLs.

### 9.3 Staggered Posting (daily_post.yml:136-153)

```
Post to main account (offset +0 min)
  sleep 600
Post to account2 (offset +10 min)
  sleep 600
Post to account3 (offset +20 min)
```

Each account reads its own queue file. Missing credentials cause skip (non-fatal).

### 9.4 GitHub Secrets Required

| Secret | Account |
|--------|---------|
| X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET | Main |
| X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET | Account 2 |
| X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET | Account 3 |

---

## 10. Concerns and Gaps

### C-1: No Automatic Retry on API Failure (MEDIUM)

**Location:** twitter_poster.py:465-469

Failed tweets are recorded but never retried. If an API call fails due to transient network issues, the tweet is lost for that slot. There is no retry queue or exponential backoff for posting failures.

**Impact:** Missed posts during X API outages or rate limiting.

### C-2: Validation Layer Inconsistency (LOW)

**Location:** tweet_generator.py:238-352 vs twitter_poster.py:95-161

Generation validation (8 checks) and posting validation (5 checks) use different banned term lists and different checking logic. The poster's `CRITICAL_BANNED` list is a subset of the generator's list. A term could pass Layer 4 but would have been caught by Layer 2.

**Impact:** Low — Layer 2 is more strict, so anything reaching Layer 4 should already be clean. But the inconsistency could cause confusion during maintenance.

### C-3: Thread Partial Failure Not Recoverable (MEDIUM)

**Location:** twitter_poster.py:610-614

If a thread fails mid-posting (e.g., tweet 3/5 fails), `thread_status` is set to "partial" but there is no mechanism to resume from the failed tweet. The partial thread remains on X with no cleanup.

**Impact:** Orphaned partial threads visible publicly.

### C-4: Negative P&L Regex May Miss Edge Cases (LOW)

**Location:** tweet_generator.py:321-324, twitter_poster.py:130-133

The regex `-\d+\.?\d*%` would not catch:
- Written losses: "down 18 percent"
- Formatted losses: "loss of $500"
- Relative declines: "fell 10%"

The `closed_trade` category explicitly requests loss tweets, which pass validation because they use the `closed_trade` category (not safeguarded). The negative P&L check primarily prevents losses leaking into other categories.

**Impact:** Low — the architecture intentionally allows losses in `closed_trade` and `post_mortem`.

### C-5: Cold Streak Detection Uses Hardcoded Lookback (LOW)

**Location:** signal_tracker.py:988-1061, config.py:285-286

The cold streak detector uses a fixed 14-day lookback with a 3-loss threshold. These are configurable in MARKETING_THRESHOLDS but the detection window could miss patterns (e.g., 3 losses spread over 15 days).

### C-6: Queue File Race Condition in Multi-Account (LOW)

**Location:** daily_post.yml:182-201

Each account writes to its own queue file, so direct conflicts are avoided. However, the git commit step adds all three queue files in a single commit. If the workflow runs concurrently for different slots (e.g., slot delayed into next slot's window), both could try to push simultaneously. The rebase-then-push (GAP 33 fix) mitigates this.

### C-7: No Content Freshness Validation (MEDIUM)

**Location:** tweet_generator.py:3073-3087

Tweets are generated Friday and posted through the following Friday. Market conditions can change significantly (e.g., a featured stock drops 30% on Monday). There is no mechanism to pull stale content from the queue.

**Impact:** Could post outdated or misleading content about stocks that have moved significantly.

### C-8: Media Upload Uses v1.1 API (LOW)

**Location:** twitter_poster.py:367-390

Image upload still uses Twitter API v1.1 (`api_v1.media_upload`). While v1.1 media endpoints are still functional, they could be deprecated. The v2 API media upload endpoint may require migration in the future.

---

## Appendix: Complete Post Type Reference Table

| # | Category | Slot Placement | Safeguarded | Data Source | Example Output |
|---|----------|---------------|-------------|-------------|----------------|
| 1 | `teal_signal` | Sat 1, Sun 1, Fri 1 | No | pass_signals | "🟢 TEAL Signals: $BTDR - Extremely Bullish, $RMBS - Bullish. Cleared all 5 gates." |
| 2 | `theme_hot` | Mon 1, Tue 2, Wed 2, Thu -, Fri 4 | No | prime_themes | "🔥 Grid Modernization showing institutional accumulation. Smart money rotating into infrastructure plays." |
| 3 | `theme_cold` | (mixed) | No | selective_themes | "❄️ Legacy Retail continues to lag. Our system avoids crowded exits." |
| 4 | `closed_trade` | (scheduled) | No | closed_trades | "✅ $RCAT closed for +55.9% (4w held). Entry: $8.50 → Exit: $13.25" |
| 5 | `violet_alert` | (scheduled) | Yes (profitable only) | sell_signals | "🟣 VIOLET Alert: $TLN systematic exit triggered. Capital preserved." |
| 6 | `system_promo` | (mixed) | No | Static | "Our 5-gate system filters 1,800 stocks to 3-5 actionable signals weekly." |
| 7 | `market_insight` | (mixed) | No | themes + macro | "Week ahead: watching AI Infrastructure for follow-through after strong close." |
| 8 | `educational` | Tue 4, Thu 4 | No | Static templates | "Most traders overtrade. Our weekly timeframe means 15 min/week. Discipline > activity." |
| 9 | `engagement` | Sat 5, Sun 4, Mon 4, Wed 4 | No | Static templates | "What's your biggest position right now? Drop a ticker 👇" |
| 10 | `beat_spy` | Sun 3, Thu 1 | Yes (5%+ threshold) | portfolio_vs_spy | "📊 TEAL signals avg +32.5% vs $SPY +12.1%. Alpha matters." |
| 11 | `power_hour` | Mon 3, Tue 3, Wed 3, Thu 3, Fri 3 | Yes (theme-only) | themes | "⚡ POWER HOUR: AI Infrastructure showing relative strength into close." |
| 12 | `sector_rotation` | (mixed) | No | hot/cold themes | "Money rotating FROM Legacy Retail INTO Grid Modernization. Follow the flow." |
| 13 | `funnel_graphic` | Sat 4, Fri 2 | No | scan_stats | "This week: 1,817 scanned → 485 high beta → 48 momentum → 6 TEAL signals." |
| 14 | `post_mortem` | (scheduled) | No | stopped trades | "🔴 $SMCI stopped out. No system wins 100%. This is why we have rules." |
| 15 | `top_performers` | Sat 1 | Yes (2+ winners) | filter_public_positions | "🟢 TEAL Winners: $RCAT +55.9% (4w), $IBKR +12.2% (3w). Measured from entry." |
| 16 | `self_quote` | Mon 2, Thu 2 | Yes (milestones) | uncelebrated_wins | "🏆 $RCAT hits +50%! Original TEAL signal was $8.50. System works. [quote tweet]" |
| 17 | `consider_spotlight` | Sun 2, Wed 1 | No | consider_signals | "🟡 AMBER Watch: $IONQ cleared 4 of 5 gates. Watching for final confirmation." |
| 18 | `weekly_recap` | (scheduled) | No | all signals | "Weekly recap: 6 TEAL signals, 2 exits, portfolio +32.5%. Full breakdown 👇" |
| 19 | `thread_buy_signal` | Sat 2 | No | Educational | "1/5 🧵 How our 5-gate system found $BTDR this week..." |
| 20 | `early_movers` | Tue 1 | Yes (5%+ early) | new positions | "🟢 Early strength: $BTDR up 8% in first week. TEAL signal working." |

---

*End of audit document.*
