# 06 - Distribution and Posting

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Overview

The distribution layer handles all outbound content: posting tweets to three X/Twitter accounts, tracking signal performance for milestone celebrations, managing self-quote threading for original signal references, and sending email notifications on pipeline failures. Two GitHub Actions workflows orchestrate everything: `friday_scan.yml` runs the full scanner pipeline and generates content queues each Friday, and `daily_post.yml` posts five tweets per day from those queues.

**Source files (4):**

| File | Path | Lines | Purpose |
|------|------|-------|---------|
| `twitter_poster.py` | `distribution/twitter_poster.py` | 818 | Post tweets/threads to X with media, validate content |
| `signal_tracker.py` | `distribution/signal_tracker.py` | 1,065 | Track wins, calculate SPY alpha, celebration management |
| `self_quote_tracker.py` | `distribution/self_quote_tracker.py` | 305 | Track original tweet IDs for milestone quote-tweets |
| `email_notifier.py` | `distribution/email_notifier.py` | 284 | SMTP email alerts on scan failures |

**Workflow files (2):**

| File | Path | Triggers |
|------|------|----------|
| `daily_post.yml` | `.github/workflows/daily_post.yml` | 5 cron schedules + manual |
| `friday_scan.yml` | `.github/workflows/friday_scan.yml` | Friday 21:30 UTC + manual |

**Data files read/written:**

| File | Read by | Written by |
|------|---------|------------|
| `twitter/output/content_queue.json` | twitter_poster | reaction_generator, twitter_poster |
| `twitter/output/content_queue_account2.json` | twitter_poster | reaction_generator, twitter_poster |
| `twitter/output/content_queue_account3.json` | twitter_poster | reaction_generator, twitter_poster |
| `portfolio/output/portfolio.csv` | signal_tracker | scanner, portfolio_manager |
| `twitter/output/celebrations.json` | signal_tracker | signal_tracker |
| `twitter/output/tweet_tracking.json` | self_quote_tracker, twitter_poster | self_quote_tracker, twitter_poster |
| `twitter/output/charts/chart_manifest.json` | twitter_poster | chart_capture |
| `twitter/output/charts/*.png` | twitter_poster | chart_capture |
| `email_config.json` | email_notifier | email_notifier (setup wizard) |

---

## 2. Twitter Poster (`distribution/twitter_poster.py`)

**818 lines.** The final stage of the tweet pipeline. Reads pre-generated content queues, validates every tweet immediately before posting, uploads chart images via Twitter API v1.1, and posts via API v2. Supports single tweets, threaded multi-tweet sequences, and quote tweets for milestone celebrations.

### 2.1 Account Configuration

Three X/Twitter accounts are configured in `config/settings.py` lines 149-168 under `TWITTER_ACCOUNTS`:

```python
TWITTER_ACCOUNTS: Dict[str, Dict] = {
    'main': {
        'env_prefix': 'X',                          # X_API_KEY, X_API_SECRET, etc.
        'queue_file': 'content_queue.json',
        'offset_minutes': 0,                         # Posts first
        'variation_style': 'original',
    },
    'account2': {
        'env_prefix': 'X2',                          # X2_API_KEY, X2_API_SECRET, etc.
        'queue_file': 'content_queue_account2.json',
        'offset_minutes': 10,                        # 10 min after main
        'variation_style': 'conversational',
    },
    'account3': {
        'env_prefix': 'X3',                          # X3_API_KEY, X3_API_SECRET, etc.
        'queue_file': 'content_queue_account3.json',
        'offset_minutes': 20,                        # 20 min after main
        'variation_style': 'data_driven',
    },
}
```

The `get_clients()` function (lines 184-232) creates two Tweepy objects per account:

```python
def get_clients(account_key: str = 'main') -> tuple:
```

- **`client_v2`** (`tweepy.Client`) -- Used for `create_tweet()` (posting text, media IDs, quote tweets, reply chains).
- **`api_v1`** (`tweepy.API`) -- Used for `media_upload()` (uploading chart PNGs). Twitter API v2 does not support media upload, so v1.1 is required.

The function reads four environment variables per account using the `env_prefix` from `TWITTER_ACCOUNTS`:

| Account | API Key Var | API Secret Var | Access Token Var | Access Secret Var |
|---------|-------------|----------------|------------------|-------------------|
| main | `X_API_KEY` | `X_API_SECRET` | `X_ACCESS_TOKEN` | `X_ACCESS_SECRET` |
| account2 | `X2_API_KEY` | `X2_API_SECRET` | `X2_ACCESS_TOKEN` | `X2_ACCESS_SECRET` |
| account3 | `X3_API_KEY` | `X3_API_SECRET` | `X3_ACCESS_TOKEN` | `X3_ACCESS_SECRET` |

If any credential is missing for an account, the function returns `(None, None)` and the account is silently skipped (line 215).

### 2.2 Content Queue System

Each account has its own JSON queue file in `twitter/output/`. The queue path is resolved by `get_queue_path()` (lines 235-249):

```python
def get_queue_path(account_key: str = 'main') -> Path:
```

This reads `TWITTER_ACCOUNTS[account_key]['queue_file']` and prepends `TRADES_DIR`. Fallback is `QUEUE_FILE = TRADES_DIR / "content_queue.json"` (line 59).

**Queue loading** via `load_queue()` (lines 256-275):
- Exits with `sys.exit(1)` if file missing or JSON parse error.
- No recovery or fallback -- this is intentional. Missing queue means `friday_scan.yml` did not generate content.

**Queue saving** via `save_queue()` (lines 278-300):
- Uses atomic write: writes to a temp file (`.queue_tmp_` prefix) then renames via `shutil.move()`.
- On POSIX systems this is atomic, preventing corruption if the process dies mid-write.
- On failure, cleans up the temp file.

**Content item selection** via `find_next_content()` (lines 335-389):

```python
def find_next_content(queue: list[Dict], force: bool = False, target_slot: Optional[int] = None) -> Optional[Dict]:
```

Selection logic:
1. Skip items where `status != "pending"`.
2. If `target_slot` is set, skip items whose `slot` does not match.
3. If `force=True`, return the first matching pending item.
4. Compare `scheduled_date` to today (Eastern Time via `ZoneInfo("America/New_York")`):
   - If `scheduled_date > today`: skip (not yet due).
   - If `scheduled_date == today`: check `slot <= current_slot` (slot must be due).
   - If `scheduled_date < today` and overdue by more than `TWEET_STALENESS_DAYS` (default 3, from `config/settings.py` line 93): mark as `expired` and skip.
   - If overdue by 1-3 days: return it (posts past-due content).

**Staleness handling** (lines 368-379): Tweets more than 3 days past their `scheduled_date` are automatically marked `status='expired'` with a `skip_reason` field. This prevents stale content from being posted after long outages.

**Deduplication** via `is_duplicate_content()` (lines 75-94):

```python
def is_duplicate_content(tweet_text: str, queue: List[Dict]) -> bool:
```

Compares normalized (stripped) text against all `status='posted'` items. If duplicate found, marks it `status='skipped'` with `skip_reason='duplicate_content'` (lines 738-743).

### 2.3 Pre-Post Validation

The `validate_before_posting()` function (lines 101-177) is the last line of defense before any tweet reaches the Twitter API. It runs six checks in order:

```python
def validate_before_posting(tweet: Dict) -> tuple:
```

**Check 1: Negative P&L** (lines 129-132)
- Regex scan for `-\d+\.?\d*%` patterns.
- Any match blocks the tweet: `"BLOCKED: Negative P&L in tweet: [-12.5%]"`.
- Rationale: Never expose losing positions publicly.

**Check 2: Critical Banned Terms** (lines 134-138)
- Imports `CRITICAL_BANNED` from `config/marketing_vocabulary.py` (lines 77-90).
- 20-term fast-path subset: `'HMA'`, `'20% stop'`, `'Banker >='`, `'Beta >='`, `'BoS'`, `'Roth IRA'`, `'Roth'`, `'PDT'`, `'401k'`, `'Capital Preservation Protocol'`, `'Forensic Audit'`, `'Volatility Expansion Criteria'`, `'5th Gate'`, `'Gate 5'`, `'proprietary entry'`, `'proprietary signal'`, `'TEAL signal'`, `'TEAL'`, `'purple signal'`, `'VIOLET'`.
- Case-insensitive substring match.

**Check 2b: Old Color System** (lines 141-146)
- Regex word-boundary check for `\b(teal|purple|violet|amber)\b` (case-insensitive).
- Also checks for the literal `🟣` (old purple emoji).
- Blocks with: `"BLOCKED: Old color 'teal' - use GREEN/RED instead"`.

**Check 3: Killed Categories** (lines 148-150)
- `KILLED_CATEGORIES = ['roth_ira', 'pdt_friendly', 'position_update', 'weekly_wins']` (hardcoded at line 127).
- Mirrors `config/settings.py` lines 59-64.

**Check 4: US-Specific Content** (lines 153-161)
- Regex patterns: `\broth\s*ira\b`, `\b401\s*\(?k\)?\b`, `\bpdt\s*(rule)?\b`, `pattern\s+day\s+trad`.
- This is a secondary check for content that might have slipped through the category filter.

**Check 5: Full Marketing Vocabulary** (lines 164-170)
- Calls `config.marketing_vocabulary.validate_content(text)` for comprehensive 73-term banned list scan (lines 27-73 of `config/marketing_vocabulary.py`).
- This includes word-boundary matching for short terms like `RSI`, `MACD`, `KDJ`, `BoS`, `GMT`, `BST`, `HMA`, `PDT`, `TEAL` to avoid false positives.

**Check 6: Tweet Length** (lines 173-175)
- Counts characters with surrogate pair awareness: `sum(2 if ord(c) > 0xFFFF else 1 for c in text)`.
- Maximum 280 characters (Twitter limit).

If any check fails, the tweet is marked `status='blocked'` with `block_reason` (line 442-443) and is never sent to the API.

### 2.4 Chart Upload Flow

The `upload_media()` function (lines 396-419) handles image upload for tweets with chart attachments:

```python
def upload_media(api_v1, image_path: str) -> Optional[str]:
```

Path resolution order:
1. If `image_path` is absolute, use directly.
2. If relative, prepend `BASE_DIR`.
3. If still not found, try `TRADES_DIR / image_path`.

On success, calls `api_v1.media_upload(str(full_path))` and returns `media.media_id_string`. On failure, returns `None` (tweet posts without image).

### 2.5 Posting Flow

**Single tweet** via `post_tweet()` (lines 429-528):

```python
def post_tweet(client_v2, api_v1, tweet: Dict, dry_run: bool = False) -> bool:
```

Flow:
1. Call `validate_before_posting(tweet)` -- block if failed.
2. Print tweet preview (text, category, ticker, scheduled date).
3. If `dry_run=True`, return `True` without posting.
4. If `image_path` present, call `upload_media()` to get `media_id`.
5. Post via `client_v2.create_tweet(text=text, media_ids=[media_id])` with retry logic.
6. Retry logic (lines 474-489): up to 3 attempts with exponential backoff (`2^(attempt+1)` seconds) for transient errors (rate limits, timeouts, 429/502/503).
7. On success: update tweet record with `status='posted'`, `posted_at`, `tweet_id`.
8. If category is `'buy_signal'` or `'thread_buy_signal'` and tweet has a `ticker`, register with self-quote tracker (lines 508-520).
9. On failure: mark `status='failed'` with `error` string.

**Thread posting** via `post_thread()` (lines 589-684):

```python
def post_thread(client_v2, api_v1, thread_item: Dict, dry_run: bool = False) -> bool:
```

Flow:
1. Read `thread_tweets` array from the queue item.
2. Post first tweet with `in_reply_to_tweet_id=None`.
3. For subsequent tweets (2-5), pass `in_reply_to_tweet_id` of the previous tweet's ID.
4. 1-second sleep between tweets for rate limit protection (line 667).
5. If any tweet fails, mark `thread_status='partial'` and return `False`.
6. On full success, set `thread_status='complete'` and `status='posted'`.

**Quote tweet** via `post_quote_tweet()` (lines 531-586):

```python
def post_quote_tweet(client_v2, api_v1, text: str, quote_tweet_id: str, dry_run: bool = False) -> Optional[str]:
```

Used for milestone celebrations. Posts with `client_v2.create_tweet(text=text, quote_tweet_id=quote_tweet_id)`. Validates content before posting using the same `validate_before_posting()` pipeline.

**Account orchestration** via `post_for_account()` (lines 691-757) and `main()` (lines 760-817):

When `--account all` is specified, `main()` iterates through all accounts in `TWITTER_ACCOUNTS` with staggered delays. The delay between accounts is computed from `offset_minutes` (lines 796-801):

```python
delay_min = accts[next_account]['offset_minutes'] - accts[account_key]['offset_minutes']
delay_sec = max(delay_min * 60, 0)
```

Default fallback: 600 seconds (10 minutes) between accounts.

### 2.6 Slot Determination

The `get_current_slot()` function (lines 303-332) uses timezone-aware datetime (`ZoneInfo("America/New_York")`) to determine the current posting slot:

| Slot | ET Window | Minutes from Midnight |
|------|-----------|-----------------------|
| 1 | 00:00 - 08:59 | 0 - 539 |
| 2 | 09:00 - 11:59 | 540 - 719 |
| 3 | 12:00 - 14:59 | 720 - 899 |
| 4 | 15:00 - 16:59 | 900 - 1019 |
| 5 | 17:00 - 19:59 | 1020 - 1199 |
| 0 (outside) | 20:00 - 23:59 | 1200+ |

Note: This differs slightly from the target times in `SLOT_TIMES_ET` (`config/settings.py` lines 299-305: 08:00, 10:00, 12:30, 15:30, 18:00). The windows are wider to accommodate GitHub Actions scheduler delays.

### 2.7 CLI Interface

```
python -m distribution.twitter_poster [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | flag | False | Preview without posting |
| `--force` | flag | False | Post next pending regardless of schedule |
| `--queue` | str | None | Override queue file path |
| `--slot` | str | `"all"` | Target slot (1-5 or "all") |
| `--account` | str | `"main"` | Account (main, account2, account3, or all) |

Exit code: 0 on success, 1 on failure.

---

## 3. Signal Tracker (`distribution/signal_tracker.py`)

**1,065 lines.** The analytics and safeguard engine for all performance-related content. Provides portfolio filtering, SPY comparison with matched holding periods, celebration management, cold streak detection, and win-highlighting thresholds. Every safeguarded tweet category calls into this module before content generation.

### 3.1 Portfolio Filtering for Public Display

The `filter_public_positions()` function (lines 616-667) enforces the critical rule: **never expose losing positions publicly**.

```python
def filter_public_positions(positions: List[Dict]) -> List[Dict]:
```

Filtering logic:
1. Skip any position with `status == 'STOPPED'` (CRIT-3 rule, line 643).
2. If `pnl_pct` is not pre-calculated on the position dict, fetch current prices via `fetch_current_prices()` (imported from `core/portfolio_manager.py`, line 34) and calculate: `pnl_pct = ((current_price / entry_price) - 1) * 100`.
3. Only include positions where `pnl_pct >= 0` (line 660).
4. Sort by P&L descending.
5. Return copies of position dicts (not references) with `pnl_pct` added.

Additional filtering functions:

- **`get_public_winners(min_pnl=0.0)`** (lines 670-674): Calls `filter_public_positions()` then filters by minimum P&L.
- **`get_winners_for_showcase(threshold=25.0, include_entry_price=True, max_positions=5)`** (lines 677-738): Applies entry price display rules from `config.can_show_entry_price()`. Entry prices are shown only for positions above 25% gain (`ENTRY_PRICE_RULES['threshold_pct']` from `config/settings.py` line 766).
- **`get_recent_closes(days=14, winners_only=True)`** (lines 741-798): Gets positions closed within the lookback period, optionally filtering to winners only.
- **`get_early_movers(max_age_days=14, min_gain=5.0)`** (lines 801-862): Gets new signals (under 14 days old) showing early strength above 5% gain.

### 3.2 Age-Based Highlight Thresholds

The `get_highlight_threshold()` function lives in `config/settings.py` (lines 963-984) and is imported by the signal tracker and tweet generators:

```python
def get_highlight_threshold(days_held: int) -> float:
```

| Days Held | Minimum P&L to Highlight |
|-----------|--------------------------|
| 0-7 | 3.0% |
| 8-14 | 5.0% |
| 15-30 | 10.0% |
| 31-60 | 15.0% |
| 61+ | 20.0% |

Rationale: Young positions just need to be green. Mature positions need stronger returns to be worth mentioning publicly.

### 3.3 Win Celebration System

Celebrations track when positions cross key P&L thresholds, ensuring each milestone is announced exactly once.

**Thresholds** (from `config/settings.py` line 452):

```python
CELEBRATION_THRESHOLDS: List[float] = [25.0, 50.0, 100.0]
```

**Celebration keys** (`config/settings.py` lines 455-459):

```python
CELEBRATION_KEYS: Dict[float, str] = {
    25.0: '25_pct_celebrated',
    50.0: '50_pct_celebrated',
    100.0: '100_pct_celebrated',
}
```

**Celebration types** (defined in `find_big_wins()`, lines 195-231):

| Threshold | Celebration Type | Marketing Threshold Key |
|-----------|-----------------|------------------------|
| 25% | `big_win` | `big_win_threshold` |
| 50% | `home_run` | `home_run_threshold` |
| 100% | `hall_of_fame` | `hall_of_fame_threshold` |

**Data structures:**

```python
@dataclass
class BigWin:                       # Lines 58-71
    ticker: str
    entry_date: str
    entry_price: float
    current_price: float
    pnl_pct: float
    theme: str
    threshold_crossed: float        # 25.0, 50.0, or 100.0
    celebration_type: str           # "big_win", "home_run", "hall_of_fame"
```

**Tracking file:** `twitter/output/celebrations.json`

Format:
```json
{
  "RCAT": {
    "25_pct_celebrated": "2026-01-15",
    "50_pct_celebrated": "2026-01-28"
  },
  "IBKR": {
    "25_pct_celebrated": "2026-02-01"
  }
}
```

**Key functions:**

- **`load_celebrations()`** (lines 238-248): Reads `CELEBRATIONS_FILE`. Returns empty dict on missing/corrupt file.
- **`save_celebrations(celebrations)`** (lines 251-258): Writes JSON with indent=2. Creates parent directory if needed.
- **`mark_as_celebrated(ticker, threshold)`** (lines 261-272): Marks a specific threshold as celebrated with today's date.
- **`is_celebrated(ticker, threshold)`** (lines 275-280): Boolean check for a specific threshold.
- **`get_uncelebrated_wins()`** (lines 283-318): Cross-references `find_big_wins()` with celebrations data. Uses `get_highest_uncelebrated_threshold()` from `config/settings.py` (lines 953-960) to find the highest threshold that has not yet been celebrated for each position.

### 3.4 SPY Comparison Safeguard

Two comparison methods are implemented:

**Method 1: Fixed 30-day window** (fallback)
- `fetch_spy_return(days=30)` (lines 113-124): Fetches SPY history via `yf.Ticker("SPY").history(period="30d")` and calculates simple return.

**Method 2: Matched holding periods** (primary, CRIT-4 fix)
- `calculate_fair_spy_comparison(positions)` (lines 420-528): For each open position, fetches SPY return over the exact same holding period (from entry date to now). Calculates alpha per position and averages across all positions.

The main entry point is `calculate_portfolio_vs_spy()` (lines 325-413):

```python
def calculate_portfolio_vs_spy(positions: List[Dict] = None) -> Dict:
```

Flow:
1. Load open positions and fetch current prices.
2. If price fetch fails completely, return `should_post_beat_spy: False` with `error: 'price_fetch_failed'` (conservative safeguard, lines 353-362).
3. Calculate portfolio return (equal-weighted average of all position P&Ls).
4. Call `calculate_fair_spy_comparison()` for matched-period alpha.
5. If matched-period comparison available, use it; otherwise fall back to 30-day window.
6. Check against threshold: `MARKETING_THRESHOLDS['spy_outperformance_min']` = 5.0% (from `config/settings.py` line 408).
7. Return dict with `should_post_beat_spy` boolean.

**Safeguard function** `should_post_beat_spy()` (lines 535-538):
```python
def should_post_beat_spy() -> bool:
    result = calculate_portfolio_vs_spy()
    return result['should_post_beat_spy']
```

### 3.5 Watchlist Signal Expiry

`filter_expired_watchlist_signals()` (lines 865-911):

```python
def filter_expired_watchlist_signals(signals: List[Dict], max_age_days: int = 21) -> List[Dict]:
```

- Removes CONSIDER/CAUTION signals older than 21 days.
- Tries multiple date field names: `signal_date`, `entry_date`, `date`.
- Signals with unparseable or missing dates are kept (safer to include).
- Backward-compat alias at line 911: `filter_expired_consider_signals = filter_expired_watchlist_signals`.

### 3.6 Historical Signal Recording

**Data structure:**

```python
@dataclass
class HistoricalSignal:             # Lines 42-55
    ticker: str
    entry_date: str
    entry_price: float
    current_price: float
    pnl_pct: float
    theme: str
    conviction: int
    days_held: int
    status: str                     # OPEN, CLOSED, STOPPED
```

**`load_historical_signals()`** (lines 131-186): Loads all trades from portfolio.csv via `load_portfolio()`, fetches current prices for open positions, calculates P&L and days held.

**`get_historical_winners(min_pnl=0.0)`** (lines 189-192): Filters to signals above a P&L threshold.

**Cold streak detection** via `check_cold_streak()` (lines 918-991):

```python
def check_cold_streak(lookback_days: int = 14, threshold: int = 3) -> Dict:
```

Returns dict with:
- `in_cold_streak`: True if >= threshold consecutive losses in lookback period.
- `should_reduce_posting`: Mirrors `in_cold_streak`.
- `consecutive_losses`, `win_rate`, `reason`.

Uses `PortfolioManager.get_closed_trades()` for closed trade data.

**Safeguard summary** -- all functions used by content generators:

| Function | Returns | Used by Category |
|----------|---------|-----------------|
| `should_post_beat_spy()` | bool | `beat_spy` |
| `has_enough_wins()` | bool | `top_performers` |
| `has_uncelebrated_wins()` | bool | `self_quote` |
| `has_winning_closed_trades()` | bool | `closed_trade` |
| `filter_public_positions()` | list | All performance tweets |
| `check_cold_streak()` | dict | Content frequency reduction |

These map to `SAFEGUARDED_CATEGORIES` in `config/settings.py` lines 435-440:

```python
SAFEGUARDED_CATEGORIES: Dict[str, str] = {
    'top_performers': 'has_enough_wins',
    'beat_spy': 'should_post_beat_spy',
    'self_quote': 'has_uncelebrated_wins',
    'closed_trade': 'has_winning_closed_trades',
}
```

With fallback categories in `CATEGORY_FALLBACKS` (lines 444-449):

```python
CATEGORY_FALLBACKS: Dict[str, str] = {
    'top_performers': 'theme_hot',
    'beat_spy': 'engagement',
    'self_quote': 'consider_spotlight',
    'closed_trade': 'educational',
}
```

---

## 4. Self-Quote Tracker (`distribution/self_quote_tracker.py`)

**305 lines.** Enables the "milestone quote tweet" system: when a GREEN signal tweet is posted, its tweet ID is stored. When the position later crosses 25%, 50%, or 100% gain, the system can post a quote tweet referencing the original signal announcement.

### 4.1 Purpose and Flow

1. **Registration** -- When `twitter_poster.py` posts a tweet with category `buy_signal` or `thread_buy_signal`, it calls `register_signal_tweet()` (lines 67-100) to store the ticker, tweet ID, entry price, and signal date.

2. **Milestone checking** -- `daily_post.yml` runs `get_unquoted_milestones()` after each posting cycle (workflow lines 155-180) to find positions that crossed celebration thresholds but have not been quote-tweeted.

3. **Quote posting** -- The quote tweet is posted via `post_quote_tweet()` in twitter_poster.py, and the milestone is marked as quoted via `mark_milestone_quoted()`.

### 4.2 Milestone Detection

**`get_unquoted_milestones()`** (lines 176-226):

```python
def get_unquoted_milestones() -> List[Dict]:
```

Flow:
1. Import `get_open_positions` and `filter_public_positions` from `distribution.signal_tracker`.
2. Load tracking data from `TWEET_TRACKING_FILE`.
3. Get filtered public positions (winners only).
4. For each position with a tracked signal:
   - Check each threshold in `CELEBRATION_THRESHOLDS` = `[25.0, 50.0, 100.0]` (descending order).
   - If P&L >= threshold and `milestones_quoted[milestone_key]` is `None`, add to unquoted list.
   - Only reports the highest unquoted milestone per ticker (line 224: `break` after first match).

Returns list of dicts with: `ticker`, `pnl_pct`, `threshold`, `milestone_key`, `original_tweet_id`, `entry_price`, `signal_date`.

### 4.3 Data Format

**Tracking file:** `twitter/output/tweet_tracking.json`

```json
{
  "signals": {
    "RCAT": {
      "tweet_id": "1234567890123456789",
      "entry_price": 8.50,
      "signal_date": "2025-12-29",
      "registered_at": "2025-12-29T16:45:00.000000",
      "milestones_quoted": {
        "25_pct": {
          "quoted_at": "2026-01-15T10:00:00.000000",
          "quote_tweet_id": "9876543210987654321"
        },
        "50_pct": null,
        "100_pct": null
      }
    }
  }
}
```

**Key functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_tracking_data()` | `() -> Dict` | Read JSON, return `{"signals": {}}` on missing/corrupt |
| `save_tracking_data(data)` | `(Dict) -> None` | Write JSON with indent=2 |
| `register_signal_tweet(ticker, tweet_id, entry_price, signal_date)` | `(str, str, float, str) -> None` | Store original signal for future quoting |
| `get_original_tweet_id(ticker)` | `(str) -> Optional[str]` | Retrieve tweet ID by ticker |
| `get_signal_data(ticker)` | `(str) -> Optional[Dict]` | Full signal tracking data |
| `mark_milestone_quoted(ticker, milestone, quote_tweet_id)` | `(str, str, str) -> None` | Record quote tweet for milestone |
| `is_milestone_quoted(ticker, milestone)` | `(str, str) -> bool` | Check if milestone already quoted |
| `get_unquoted_milestones()` | `() -> List[Dict]` | Cross-reference P&L with tracking |
| `get_all_tracked_signals()` | `() -> Dict[str, Dict]` | Return all tracked signals |
| `remove_signal(ticker)` | `(str) -> bool` | Remove ticker from tracking |

**CLI** (lines 253-305):

```
python -m distribution.self_quote_tracker --list       # List all tracked signals
python -m distribution.self_quote_tracker --unquoted   # Show unquoted milestones
python -m distribution.self_quote_tracker --register TICKER TWEET_ID PRICE DATE
```

---

## 5. Email Notifier (`distribution/email_notifier.py`)

**284 lines.** Provides SMTP email notifications, primarily used for failure alerts on the Friday scan. Uses a local `email_config.json` file for configuration rather than environment variables (though the Friday workflow passes env vars for CI use).

### 5.1 Configuration

**Config file:** `email_config.json` in the project root (line 30):

```python
CONFIG_FILE = Path(__file__).resolve().parent.parent / "email_config.json"
```

Config format:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "from_email": "user@gmail.com",
  "recipients": ["user@gmail.com", "other@example.com"],
  "username": "user@gmail.com",
  "password": "xxxx xxxx xxxx xxxx"
}
```

The `save_config()` function (lines 46-50) sets file permissions to `0o600` (owner read/write only) after writing.

**Supported SMTP providers** (setup wizard, lines 72-76):

| Choice | Server | Port |
|--------|--------|------|
| 1 (Gmail) | `smtp.gmail.com` | 587 |
| 2 (Outlook) | `smtp-mail.outlook.com` | 587 |
| 3 (Yahoo) | `smtp.mail.yahoo.com` | 587 |
| 4 (Custom) | User-specified | User-specified |

### 5.2 Alert Types

**`send_email(subject, body)`** (lines 174-217):

```python
def send_email(subject: str, body: str) -> bool:
```

- Reads config from `email_config.json`.
- Supports both old format (`to_email` single recipient) and new format (`recipients` list).
- Uses STARTTLS for encryption.
- Returns `True` on success, `False` on SMTP auth, SMTP, or network errors.
- Raises `RuntimeError` if email not configured.

**Alert types used in workflows:**

| Alert | Trigger | Source |
|-------|---------|--------|
| Scan failure | `friday_scan.yml` step fails | Workflow step "Notify on Failure" (line 365-391) |
| Test email | Manual via CLI | `python -m distribution.email_notifier test` |

**CLI** (lines 267-283):

```
python -m distribution.email_notifier setup    # Interactive configuration wizard
python -m distribution.email_notifier test     # Send test email to all recipients
python -m distribution.email_notifier list     # List all configured recipients
python -m distribution.email_notifier add EMAIL
python -m distribution.email_notifier remove EMAIL
```

Note: The Friday scan workflow (lines 365-391) passes `EMAIL_PASSWORD`, `EMAIL_SENDER`, `EMAIL_RECIPIENTS`, and `SMTP_SERVER` as environment variables from GitHub Secrets. However, the `email_notifier.py` `send_email()` function reads from `email_config.json`, not environment variables. The workflow actually invokes the notifier with `--subject` and `--body` flags, but the current CLI `print_usage()` does not list these flags -- the workflow call pattern (`python -m distribution.email_notifier --subject "..." --body "..."`) does not match the module's actual CLI parsing (`sys.argv[1] == "setup"` etc.). This is an integration gap: the workflow command will fall through to `print_usage()` and not send the email.

---

## 6. GitHub Actions Workflows

### 6.1 `friday_scan.yml` -- Full Pipeline

**File:** `.github/workflows/friday_scan.yml` (392 lines)

**Triggers:**
- Cron: `30 21 * * 5` (Friday 21:30 UTC = 4:30 PM ET)
- `workflow_dispatch` with inputs: `skip_llm`, `web_search`, `top_n`, `skip_charts`, `skip_tweets`, `skip_newsletter`

**Configuration:**
- Runner: `ubuntu-latest`
- Python: 3.11 with pip cache
- Timeout: 90 minutes
- Permissions: `contents: write` (for git push)
- Env: `ANTHROPIC_API_KEY`

**Pipeline steps (9):**

| Step | Name | Command | Critical |
|------|------|---------|----------|
| 1 | Run Scanner | `python -m core.scanner --archive [--web-search] [--no-llm] [--top N]` | Yes |
| 2a | Generate Funnel Graphic | `python -m content.funnel_graphic` | No (continue-on-error) |
| 2b | Capture TradingView Charts | `python -m content.chart_capture --tickers-from scanner/output/signals.json --include-portfolio --headless --use-cookies` | No (continue-on-error) |
| 3 | Generate Market Analysis | `python -m content.market_analyzer --save` | No (continue-on-error) |
| 4 | Compile Newsletter | `python -m content.newsletter_compiler --from-html` | No (continue-on-error) |
| 4.5 | Generate Substack Content | `python -m content.substack_content_generator --all` | No (continue-on-error) |
| 5 | Generate Tweets | `python -m content.reaction_generator --scanner-file scanner/output/signals.json --output twitter/output/` | Yes |
| 5.5 | Generate Substack Notes | `python -m content.substack_notes_generator` | No (continue-on-error) |
| 6 | Upload artifacts | `actions/upload-artifact@v4` | Yes |
| 7 | Commit and push | `git add scanner/output/ portfolio/output/ substack/output/ twitter/output/ && git commit && git push` | Yes |
| 8 | Generate summary | Write to `$GITHUB_STEP_SUMMARY` | Always |
| 9 | Notify on failure | `python -m distribution.email_notifier` | On failure only |

**Artifact uploads:**

| Artifact Name | Contents | Retention |
|--------------|----------|-----------|
| `scan-results-{run_id}` | `scanner/output/current/`, signals, portfolio, report | 30 days |
| `substack-notes-{run_id}` | `substack/output/current/substack_notes/` | 7 days |
| `substack-posts-{run_id}` | `substack/output/current/substack_posts/` | 30 days |
| `content-queue` | 3 content_queue JSON files | 14 days |
| `charts-{run_id}` | `twitter/output/charts/` | 30 days |

The `content-queue` artifact (without run_id suffix) is the critical handoff to `daily_post.yml`. It uses a fixed name so the daily workflow can download the latest version.

### 6.2 `daily_post.yml` -- Tweet Posting

**File:** `.github/workflows/daily_post.yml` (235 lines)

**Triggers:**
- 5 cron schedules (UTC, targeting EST times):
  - `0 13 * * *` -- Slot 1 (08:00 ET)
  - `0 15 * * *` -- Slot 2 (10:00 ET)
  - `30 17 * * *` -- Slot 3 (12:30 ET)
  - `30 20 * * *` -- Slot 4 (15:30 ET)
  - `0 23 * * *` -- Slot 5 (18:00 ET)
- `workflow_dispatch` with inputs: `slot` (default "all"), `dry_run` (default "false")

**Note on EDT:** The cron times use EST (UTC-5). During EDT (March-November), posts will be 1 hour earlier than intended (e.g., Slot 1 at 09:00 EDT instead of 08:00 EDT). This is documented in the workflow comment at line 18.

**Environment variables (12 secrets):**

```yaml
ANTHROPIC_API_KEY, X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET,
X2_API_KEY, X2_API_SECRET, X2_ACCESS_TOKEN, X2_ACCESS_SECRET,
X3_API_KEY, X3_API_SECRET, X3_ACCESS_TOKEN, X3_ACCESS_SECRET
```

**Steps:**

| # | Step | Detail |
|---|------|--------|
| 1 | Checkout + Python setup | Python 3.11 with pip cache |
| 2 | Determine slot | UTC hour-based ranges (lines 77-101) |
| 3 | Download content-queue artifact | `actions/download-artifact@v4`, continue-on-error |
| 4 | Check queue exists | Verify `twitter/output/content_queue.json` exists |
| 5 | Fail if no queue | Exit 1 with diagnostic message (GAP 29 fix) |
| 6 | Post to all accounts | Staggered: main, 10min wait, account2, 10min wait, account3 |
| 7 | Check milestone quotes | Python inline script calling `get_unquoted_milestones()` and `get_uncelebrated_wins()` |
| 8 | Commit updated queues | `git add` queue files + tracking, `git pull --rebase`, `git push` |
| 9 | Upload updated queues | Re-upload `content-queue` artifact |
| 10 | Report status | Write summary to `$GITHUB_STEP_SUMMARY` |

**Slot determination logic** (lines 77-101):

The workflow determines slot from UTC hour at runtime:

| UTC Hour Range | Slot | ET Time |
|---------------|------|---------|
| 13-14 | 1 | 08:00-09:59 ET |
| 15-16 | 2 | 10:00-11:59 ET |
| 17-19 | 3 | 12:00-14:59 ET |
| 20-22 | 4 | 15:00-17:59 ET |
| 23-00 | 5 | 18:00-19:59 ET |
| Other | all | Fallback |

This uses 2-hour windows per slot to handle GitHub Actions scheduler delays (which can be up to 60 minutes).

### 6.3 Artifact Flow Between Workflows

```
friday_scan.yml                          daily_post.yml
     |                                        |
     | Upload artifact:                       | Download artifact:
     | "content-queue"                        | "content-queue"
     |   content_queue.json                   |   content_queue.json
     |   content_queue_account2.json          |   content_queue_account2.json
     |   content_queue_account3.json          |   content_queue_account3.json
     |                                        |
     | retention: 14 days                     | Downloads latest available
     |                                        |
     +-------- Git commit + push ------------>| Also downloads from repo
     |                                        |
     |                                        | After posting:
     |                                        | Upload updated "content-queue"
     |                                        | Git commit + push updated queues
```

The `content-queue` artifact serves as the primary handoff mechanism. It uses a fixed name (no run_id suffix) so each workflow run overwrites the previous artifact. The `download-artifact` step in `daily_post.yml` has `continue-on-error: true` (line 108) because the artifact may not exist yet if `friday_scan.yml` has never run.

If the artifact download fails, the workflow checks if `twitter/output/content_queue.json` exists in the repo itself (committed by a previous Friday scan). If neither source provides a queue, the workflow fails with a diagnostic message (lines 122-134).

### 6.4 Git Commit Strategy

**Friday scan** (lines 297-311):
- Commits all files in section output directories.
- Commit message: `"Weekly scan results YYYY-MM-DD"`.
- Straightforward `git push` (no rebase needed since this runs once per week).

**Daily posting** (lines 182-202):
- Commits only queue files and tracking file:
  ```
  twitter/output/content_queue.json
  twitter/output/content_queue_account2.json
  twitter/output/content_queue_account3.json
  twitter/output/tweet_tracking.json
  ```
- Commit message: `"Update content queue after posting"`.
- Uses `git pull --rebase` before push to handle race conditions (GAP 33 fix, line 195).
- If rebase fails, falls back to merge: `git rebase --abort && git pull origin $branch` (lines 196-199).
- Entire commit step has `continue-on-error: true` (line 202) to prevent workflow failure on push conflicts.

---

## 7. Weekly Automation Timeline

| Day | Time (ET) | Trigger | Action | Files Affected |
|-----|-----------|---------|--------|---------------|
| **Friday** | 16:30 | `friday_scan.yml` cron | Full scanner pipeline | All section output files |
| **Friday** | 16:30+ | (same run) | Generate tweets | `content_queue*.json` |
| **Friday** | 16:30+ | (same run) | Generate newsletter | `substack/output/current/newsletter.html` |
| **Friday** | 16:30+ | (same run) | Generate Substack notes | `substack/output/current/substack_notes/` |
| **Friday** | 16:30+ | (same run) | Upload artifacts | GitHub artifact storage |
| **Saturday** | 08:00 | `daily_post.yml` Slot 1 | Post pre-market tweet (all 3 accounts) | Queue files updated |
| **Saturday** | 10:00 | `daily_post.yml` Slot 2 | Post morning tweet | Queue files updated |
| **Saturday** | 12:30 | `daily_post.yml` Slot 3 | Post midday tweet | Queue files updated |
| **Saturday** | 15:30 | `daily_post.yml` Slot 4 | Post Power Hour tweet | Queue files updated |
| **Saturday** | 18:00 | `daily_post.yml` Slot 5 | Post evening tweet | Queue files updated |
| **Saturday** | Manual | Human | Copy newsletter to Substack, add charts | N/A |
| **Sun-Fri** | 5x daily | `daily_post.yml` | Post 5 tweets per day | Queue files updated |
| **Tuesday** | Manual | Human | Post "Portfolio Pulse" Substack note | N/A |
| **Thursday** | Manual | Human | Post "Trade Spotlight" Substack note | N/A |

Each `daily_post.yml` run posts 1 tweet per account per slot (3 tweets total per slot, staggered 10 minutes apart), then commits the updated queue files back to the repo and uploads the updated artifact.

---

## 8. Files Read/Written Summary

### Files Read

| File | Read By | Purpose |
|------|---------|---------|
| `twitter/output/content_queue.json` | `twitter_poster.py` | Main account tweet queue |
| `twitter/output/content_queue_account2.json` | `twitter_poster.py` | Account 2 tweet queue |
| `twitter/output/content_queue_account3.json` | `twitter_poster.py` | Account 3 tweet queue |
| `portfolio/output/portfolio.csv` | `signal_tracker.py` (via portfolio_manager) | Position data for P&L |
| `twitter/output/celebrations.json` | `signal_tracker.py` | Celebration tracking state |
| `twitter/output/tweet_tracking.json` | `self_quote_tracker.py`, `twitter_poster.py` | Signal tweet ID tracking |
| `twitter/output/charts/chart_manifest.json` | `twitter_poster.py` (via upload_media) | Chart file lookup |
| `twitter/output/charts/*.png` | `twitter_poster.py` | Chart images for media upload |
| `email_config.json` | `email_notifier.py` | SMTP credentials and recipients |
| `config/settings.py` | All modules (via `from config import ...`) | Thresholds, accounts, schedules |
| `config/marketing_vocabulary.py` | `twitter_poster.py` | Banned terms validation |

### Files Written

| File | Written By | Trigger |
|------|------------|---------|
| `twitter/output/content_queue.json` | `twitter_poster.py` | After each post (status update) |
| `twitter/output/content_queue_account2.json` | `twitter_poster.py` | After each post (status update) |
| `twitter/output/content_queue_account3.json` | `twitter_poster.py` | After each post (status update) |
| `twitter/output/celebrations.json` | `signal_tracker.py` | On celebration milestone |
| `twitter/output/tweet_tracking.json` | `self_quote_tracker.py` | On signal registration or milestone quote |
| `email_config.json` | `email_notifier.py` | On setup wizard completion |

### External API Calls

| API | Module | Method | Purpose |
|-----|--------|--------|---------|
| Twitter API v2 | `twitter_poster.py` | `tweepy.Client.create_tweet()` | Post tweets, quote tweets, thread replies |
| Twitter API v1.1 | `twitter_poster.py` | `tweepy.API.media_upload()` | Upload chart PNG images |
| yfinance | `signal_tracker.py` | `yf.Ticker("SPY").history()` | SPY benchmark data for alpha calculation |
| yfinance | `signal_tracker.py` (via portfolio_manager) | `fetch_current_prices()` | Current position prices for P&L |
| SMTP | `email_notifier.py` | `smtplib.SMTP.sendmail()` | Failure alert emails |
