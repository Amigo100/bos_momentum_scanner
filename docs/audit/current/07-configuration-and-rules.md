# 07 - Configuration and Rules

> Sterling Signals / BoS Momentum Scanner
> Audit date: 2026-02-06
> Branch: `refactor/cleanup-reorg`

---

## 1. Overview

The configuration layer is split across four files inside the `config/` package:

| File | Lines | Purpose |
|------|-------|---------|
| `config/settings.py` | 1158 | All constants, thresholds, LLM config, branding, schedules, marketing rules, helper functions |
| `config/marketing_vocabulary.py` | 511 | Banned terms, approved vocabulary, validation functions, decorator |
| `config/output_paths.py` | 310 | Centralized folder structure management, archive helpers |
| `config/__init__.py` | 8 | Re-exports everything from `settings.py` via `from config.settings import *` |

Backwards compatibility is preserved by `config/__init__.py`; any module in the codebase can write `from config import BETA_THRESHOLD` without knowing that the value physically lives in `config/settings.py`.

There is intentional overlap between `settings.py` and `marketing_vocabulary.py`. Both files define a `BANNED_TERMS` list and both define `CONTENT_TYPES`. The `settings.py` versions are the canonical source for the scanner pipeline; the `marketing_vocabulary.py` versions are the canonical source for content validation. The two lists differ slightly in membership (documented in Section 3.1).

---

## 2. Central Settings (`config/settings.py`)

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/config/settings.py`
**Lines:** 1-1158
**Imports:** `re`, `pathlib.Path`, `typing.Dict`, `typing.List`

### 2.1 Directory Layout

Defined at lines 18-24:

```python
BASE_DIR = Path(__file__).resolve().parent.parent   # Line 22 - project root
TRADES_DIR = BASE_DIR / "trades"                     # Line 23
TICKERS_FILE = BASE_DIR / "complete_tickers.txt"     # Line 24
```

`BASE_DIR` resolves to the project root by going one level up from `config/`. Every other path in the system derives from `TRADES_DIR`.

Note: `output_paths.py` independently redefines `BASE_DIR` and `TRADES_DIR` with the same logic (lines 36-37 of that file). This is a minor duplication, not a conflict, because both resolve identically at runtime.

### 2.2 Scanner Thresholds

Defined at lines 68-96:

| Constant | Value | Line | Purpose |
|----------|-------|------|---------|
| `TRAILING_STOP_PCT` | `20.0` | 71 | 20% trailing stop from highest close |
| `STOP_WARNING_PCT` | `5.0` | 72 | Warn when within 5% of stop |
| `TIGHTEN_STOP_PCT` | `15.0` | 73 | Tighten to 15% on BoS down |
| `BETA_THRESHOLD` | `1.5` | 75 | Minimum beta for entry |
| `BANKER_TIER1` | `70` | 76 | Tier 1 banker threshold |
| `BANKER_TIER2` | `60` | 77 | Tier 2 banker threshold |
| `BANKER_TIER3` | `55` | 78 | Tier 3 banker threshold (entry minimum) |
| `BANKER_CENTER` | `50` | 81 | Neutral point (at VWAP) |
| `BANKER_SCALE_FACTOR` | `5` | 82 | Sensitivity multiplier in banker formula |
| `VWAP_PERIOD` | `20` | 83 | Days for VWAP calculation |
| `HMA_PERIOD` | `21` | 86 | HMA lookback period for BoS calculation |
| `DEFAULT_POSITION_SHARES` | `100` | 89 | Assumed shares per position for notional P&L |
| `MAX_PORTFOLIO_BACKUPS` | `30` | 90 | Keep last N portfolio backups |
| `TWEET_STALENESS_DAYS` | `3` | 93 | Skip tweets more than N days past scheduled date |
| `DEFAULT_UNIVERSE_SIZE` | `1817` | 96 | Approximate total ticker count |

The banker formula is: `banker = BANKER_CENTER + (deviation_pct * BANKER_SCALE_FACTOR)` where `deviation_pct = ((close / VWAP) - 1) * 100`.

### 2.3 Stop Loss Parameters

Three constants govern stop loss behavior (lines 71-73):

```
Entry stop:    TRAILING_STOP_PCT  = 20.0%   from highest close
Tightened stop: TIGHTEN_STOP_PCT  = 15.0%   triggered by Weekly BoS Down
Warning zone:  STOP_WARNING_PCT   = 5.0%    alert when within 5% of stop level
```

Logic flow:
1. Position opens with 20% trailing stop from highest close.
2. If Weekly BoS turns bearish, stop tightens to 15%.
3. If current price is within 5% of either stop level, `stop_alert = True`.
4. If price drops below stop level, position status becomes `STOPPED`.

### 2.4 LLM Configuration

**Model definitions** (lines 100-113):

| Constant | Value | Line |
|----------|-------|------|
| `MODEL_SONNET` | `"claude-sonnet-4-20250514"` | 103 |
| `MODEL_OPUS` | `"claude-opus-4-5-20251101"` | 104 |

**Per-component model assignments** (lines 107-113):

| Constant | Resolves To | Line |
|----------|-------------|------|
| `MODEL_THEMATIC` | `MODEL_SONNET` | 107 |
| `MODEL_GATEKEEPER` | `MODEL_SONNET` | 108 |
| `MODEL_TWEET` | `MODEL_SONNET` | 109 |
| `MODEL_NEWSLETTER` | `MODEL_SONNET` | 110 |
| `MODEL_MARKET` | `MODEL_SONNET` | 111 |
| `MODEL_DD_QUICK` | `MODEL_SONNET` | 112 |
| `MODEL_DD_FULL` | `MODEL_OPUS` | 113 |

**API settings** (lines 116-142):

| Constant | Value | Line | Purpose |
|----------|-------|------|---------|
| `MAX_RETRIES` | `5` | 120 | Max retry attempts on failure |
| `RATE_LIMIT_COOLDOWN` | `60.0` | 121 | Seconds to wait on rate limit |
| `INTER_STEP_DELAY` | `30.0` | 122 | Delay between major pipeline steps |
| `INTER_STOCK_DELAY` | `8.0` | 123 | Delay between per-stock LLM calls |
| `BACKOFF_FACTOR` | `2.0` | 124 | Exponential backoff multiplier |
| `BACKOFF_MAX_WAIT` | `300.0` | 125 | Maximum wait time for backoff (5 min) |

**Token limits** (lines 128-131):

```python
MAX_TOKENS = {
    MODEL_SONNET: 8192,
    MODEL_OPUS: 8192,
}
```

**Cost tracking** (lines 134-142):

```python
COST_INPUT_PER_M = {
    MODEL_SONNET: 3.00,     # $3.00 per 1M input tokens
    MODEL_OPUS: 15.00,      # $15.00 per 1M input tokens
}
COST_OUTPUT_PER_M = {
    MODEL_SONNET: 15.00,    # $15.00 per 1M output tokens
    MODEL_OPUS: 75.00,      # $75.00 per 1M output tokens
}
COST_WEB_SEARCH = 0.01      # $0.01 per search
```

### 2.5 Thematic Analyzer Weights

Defined at lines 357-371:

**Classification thresholds:**

| Constant | Value | Line | Classification |
|----------|-------|------|----------------|
| `THEME_SCORE_PRIME` | `7.5` | 361 | >= for PRIME |
| `THEME_SCORE_INVESTABLE` | `6.0` | 362 | >= for INVESTABLE |
| `THEME_SCORE_SELECTIVE` | `4.5` | 363 | >= for SELECTIVE |
| (below 4.5) | - | 364 | AVOID |

**Composite score weights** (lines 366-371):

```python
THEME_WEIGHTS = {
    "catalyst": 0.40,    # Upcoming catalysts (40% weight)
    "momentum": 0.25,    # Price/flow momentum (25% weight)
    "crowding": 0.20,    # Positioning/crowding (20% weight)
    "runway":   0.15,    # Future potential (15% weight)
}
```

Formula: `composite = catalyst*0.40 + momentum*0.25 + crowding*0.20 + runway*0.15`

### 2.6 Marketing Parameters

**Marketing thresholds** (lines 399-422):

```python
MARKETING_THRESHOLDS = {
    'min_win_to_highlight': 15.0,           # Minimum % gain for top_performers
    'big_win_threshold': 25.0,              # Trigger standalone self_quote tweet
    'home_run_threshold': 50.0,             # Celebration post, pin candidate
    'hall_of_fame_threshold': 100.0,        # Thread-worthy, reference repeatedly
    'spy_outperformance_min': 5.0,          # Must beat SPY by this % for beat_spy content
    'min_winners_for_top_performers': 2,    # Need at least 2 winners to post
    'max_loss_to_mention': -5.0,            # Never mention positions worse than this
    'cold_streak_threshold': 3,             # Consecutive losses to trigger circuit breaker
    'cold_streak_lookback_days': 14,        # Days to look back for recent losses
    'max_ticker_mentions_per_week': 4,      # Max times same ticker in weekly content
}
```

**Target audience** (lines 31-41):

```python
TARGET_AUDIENCE = {
    'region': 'Global',
    'account_type': 'Any',
    'restrictions': [
        'No Roth IRA content',
        'No PDT rule content',
        'No 401k content',
        'No UK ISA content',
        'No country-specific tax advice',
    ],
}
```

**Ticker frequency limits** (lines 48-52):

```python
TICKER_LIMITS = {
    'max_mentions_per_week': 4,
    'max_consecutive_days': 2,
    'cooldown_after_milestone': 2,
}
```

**Killed categories** (lines 59-64) -- categories permanently disabled:

```python
KILLED_CATEGORIES = [
    'roth_ira',          # Wrong audience
    'pdt_friendly',      # Wrong audience
    'position_update',   # Merged to top_performers
    'weekly_wins',       # Renamed to top_performers
]
```

---

## 3. Marketing Vocabulary (`config/marketing_vocabulary.py`)

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/config/marketing_vocabulary.py`
**Lines:** 1-511
**Imports:** `functools`, `re`, `typing.Callable`, `typing.Dict`, `typing.List`, `typing.Tuple`

### 3.1 BANNED_TERMS (Full List)

Defined at lines 27-73 of `marketing_vocabulary.py`. This is the content-validation canonical list used by `validate_content()`.

**Strategy internals (lines 29-36):**
- `"HMA"`, `"Hull Moving Average"`, `"HMA Pivot"`, `"HMA pivot"`
- `"Banker indicator"`, `"Banker >= 55"`, `"Banker >= 55"` (unicode >=), `"Banker >="`, `"banker indicator"`
- `"20% trailing stop"`, `"20% stop"`
- `"Beta >= 1.5"`, `"Beta >= 1.5"` (unicode >=), `"beta threshold"`, `"Beta >="`
- `"Break of Structure"`, `"BoS"`, `"BOS"`, `"Weekly BoS"`, `"weekly bos"`
- `"Tier 1"`, `"Tier 2"`, `"Tier 3"`, `"TIER1"`, `"TIER2"`, `"TIER3"`
- `"Gatekeeper"`
- `"Weekly pivot"`

**Technical indicators (lines 38-39):**
- `"RSI"`, `"MACD"`, `"KDJ"`

**Old color system (lines 41-46):**
- `"TEAL signal"`, `"TEAL"`, `"teal signal"`, `"teal"`
- `"purple signal"`, `"purple"`, `"PURPLE"`
- `"VIOLET signal"`, `"VIOLET"`, `"violet"`
- `"🟣"` (purple circle emoji)
- `"AMBER signal"`, `"AMBER"`, `"amber"`

**UK audience references (lines 48-53):**
- `"UK ISA"`, `"ISA wrapper"`, `"Barclays ISA"`, `"ISA account"`
- `"UK investor"`, `"UK investors"`, `"UK trader"`, `"UK traders"`
- `"GMT"`, `"BST"`, `"UK Time"`, `"UK time"`, `"London time"`
- `"GBP/USD"`

**Internal terms that leaked (lines 56-59):**
- `"Capital Preservation Protocol"`
- `"Forensic Audit"`
- `"Volatility Expansion Criteria"`
- `"5th Gate"`, `"Gate 5"`

**Non-branded signal terms (lines 61-63):**
- `"proprietary entry"`, `"proprietary signal"`
- `"PASS signal"`

**US-specific retirement (lines 65-68):**
- `"Roth IRA"`, `"Roth"`
- `"PDT"`, `"PDT rule"`, `"pattern day trader"`
- `"401k"`, `"401(k)"`

**Conviction language violations (lines 70-72):**
- `"conviction 5"`, `"conviction 4"`, `"conviction 3"`
- `"conviction score"`, `"conviction rating"`

Note: `"sterling"` is explicitly NOT banned (line 53 comment) to avoid false-positives on the brand name "Sterling Signals".

**Parallel list in `settings.py`:** Lines 507-550 of `settings.py` also define a `BANNED_TERMS` list. The two lists overlap heavily but are not identical. The `settings.py` version adds `"Banker score"`, `"PASS signal"`, `"weekly winners"`, `"this week we nailed"` and omits some UK geographic terms (`"ISA wrapper"`, `"Barclays ISA"`, `"UK investor"`, etc.) and conviction terms (`"conviction 5"` etc.) present in `marketing_vocabulary.py`. The `settings.py` version is used by `contains_banned_term()` (settings helper). The `marketing_vocabulary.py` version is used by `validate_content()` (content validation path).

### 3.2 CRITICAL_BANNED (Fast-Path List)

Defined at lines 77-90 of `marketing_vocabulary.py`. A compact subset for the pre-post check in `distribution/twitter_poster.py`.

```python
CRITICAL_BANNED = [
    'HMA', '20% stop', 'Banker >=', 'Beta >=', 'BoS',
    'Roth IRA', 'Roth', 'PDT', '401k',
    'Capital Preservation Protocol', 'Forensic Audit',
    'Volatility Expansion Criteria', '5th Gate', 'Gate 5',
    'proprietary entry', 'proprietary signal',
    'TEAL signal', 'TEAL',
    'purple signal', 'VIOLET',
]
```

Total: 19 entries. This list is checked as a simple substring scan (no regex) for speed at post time.

### 3.3 APPROVED_VOCABULARY (Translation Table)

Defined at lines 96-125 of `marketing_vocabulary.py`:

| Internal Term | Approved Replacement |
|---------------|---------------------|
| `"HMA Pivot"` | `"momentum confirmed"` |
| `"Banker indicator"` | `"strong accumulation"` |
| `"Beta >= 1.5"` | `"volatility characteristics"` |
| `"20% trailing stop"` | `"trailing stop"` |
| `"Weekly BoS"` | `"momentum confirmed"` |
| `"Gatekeeper"` | `"cleared all gates"` |
| `"Tier 1/2/3"` | `"high conviction"` |
| `"Theme scoring"` | `"theme alignment"` |
| `"TEAL signal"` | `"GREEN signal"` |
| `"VIOLET signal"` | `"RED signal"` |
| `"purple signal"` | `"RED signal"` |
| `"AMBER signal"` | `"CONSIDER signal"` |
| `"buy signal"` | `"GREEN signal"` |
| `"PASS signal"` | `"GREEN signal"` |
| `"Extremely Bullish"` | conviction 5 public language |
| `"Bullish"` | conviction 4 public language |
| `"Watching"` | conviction 3 public language |
| `"Cautious"` | conviction 2 public language |

Also includes emoji mappings:
- `"🟢 GREEN"` -- buy signal emoji
- `"🔴 RED"` -- exit/sell signal emoji
- `"🟡 CONSIDER"` -- watchlist signal emoji

### 3.4 POWER_PHRASES

Defined at lines 131-163. These are pre-approved marketing phrases safe for public use.

**System description:**
- `"Proprietary 5-gate screening system"`
- `"Filters 1,800 stocks to 3-5 actionable signals"`
- `"Institutional-grade momentum analysis"`
- `"Systematic approach that removes emotional bias"`

**Signal detection (v2.0 GREEN/RED):**
- `"GREEN signal triggered"`
- `"RED signal - time to rotate"`
- `"Cleared all 5 gates"`
- `"Strong accumulation detected"`
- `"Theme alignment confirmed"`
- `"Momentum confirmed"`

**Risk management:**
- `"Systematic exit discipline"`
- `"Trailing stop in place"`
- `"Risk-defined position sizing"`
- `"The system protects capital so we live to fight another day"`
- `"No ego, just execution"`

**Performance framing:**
- `"Beat SPY with systematic momentum"`
- `"Alpha over indexing"`
- `"Stop indexing. Start selecting."`
- `"Weekly timeframe suits swing traders"`

**Friday/weekly references:**
- `"As of Friday's close"`
- `"Based on the latest weekly close"`
- `"Friday's scan results"`

### 3.5 AUDIENCE_HOOKS

Defined at lines 169-200 as `AUDIENCE_HOOKS` (with backwards-compatible alias `US_AUDIENCE_HOOKS = AUDIENCE_HOOKS` at line 203):

| Hook Key | Sample Phrases |
|----------|---------------|
| `"beat_spy"` | "Stop indexing. Start selecting.", "SPY gives you average returns. We hunt outliers." |
| `"time_friendly"` | "Weekly timeframe suits busy schedules.", "15 minutes/week vs all-day stress." |
| `"power_hour"` | "Power Hour Check:", "Watching relative strength into the close." |
| `"sector_rotation"` | "Money is rotating.", "Follow the institutional flows." |
| `"friday_close"` | "Scanner ran after Friday's close.", "Friday's results are in." |

Each key maps to a `List[str]` of 4 phrases.

### 3.6 Validation Functions

**`validate_content(text: str) -> Tuple[bool, List[str]]`** (lines 209-247)

Core validation function. Scans text against `BANNED_TERMS` with case-insensitive matching. Short terms (`RSI`, `MACD`, `KDJ`, `BoS`, `BOS`, `GMT`, `BST`, `HMA`, `PDT`, `TEAL`, `teal`) use word-boundary regex via `re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE)` to prevent false positives. Returns `(is_valid, unique_violations)`.

**`validate_green_red_consistency(text: str) -> Tuple[bool, List[str]]`** (lines 250-277)

Checks for old color terms and suggests replacements: `TEAL->GREEN`, `purple->RED`, `VIOLET->RED`, `AMBER->CONSIDER`, `🟣->🔴`.

**`log_violations(content_type: str, violations: List[str]) -> None`** (lines 280-289)

Prints a warning with the content type and list of violations found.

**`get_replacement(internal_term: str) -> str`** (lines 292-302)

Looks up an internal term in `APPROVED_VOCABULARY` and returns the marketing replacement. Returns the original term if no mapping exists.

**`validate_all_tweets(tweets: list) -> Tuple[int, int]`** (lines 305-339)

Iterates a list of tweet dicts/objects, runs both `validate_content()` and `validate_green_red_consistency()` on each. Returns `(total_checked, violation_count)`.

**`@validate_output(strict=False, content_type="output")` decorator** (lines 347-389)

Decorator for any function returning `str`, `list`, or `dict`. Inspects the return value for banned terms. If `strict=True`, raises `ValueError`; otherwise logs a warning. Handles nested structures: `list[str]`, `list[dict]` with `'text'` key, `dict` with `'text'` or `'content'` key.

**`validated_content(text: str, content_type: str) -> str`** (lines 403-423)

Inline validation: checks text, logs warnings, returns the original text unchanged.

**`_check_content(text: str, source: str, strict: bool, content_type: str) -> None`** (lines 392-400)

Internal helper called by the decorator. Runs `validate_content()` and either raises or logs.

---

## 4. Signal Branding System

### 4.1 Color System (GREEN / RED / CONSIDER)

Defined in `settings.py` at lines 733-752:

```python
SIGNAL_COLORS = {
    'GREEN': {
        'emoji': '🟢',
        'meaning': 'BUY',
        'internal_status': 'PASS',
        'public_name': 'GREEN Signal',
    },
    'RED': {
        'emoji': '🔴',
        'meaning': 'EXIT',
        'internal_status': 'STOPPED',
        'public_name': 'Exit Alert',
    },
    'CONSIDER': {
        'emoji': '🟡',
        'meaning': 'WATCH',
        'internal_status': 'CONSIDER',
        'public_name': 'On Our Radar',
    },
}
```

| Color | Emoji | Meaning | Internal Status | Public Name |
|-------|-------|---------|-----------------|-------------|
| GREEN | `🟢` | BUY | PASS | GREEN Signal |
| RED | `🔴` | EXIT | STOPPED | Exit Alert |
| CONSIDER | `🟡` | WATCH | CONSIDER | On Our Radar |

**Important branding note:** The original TEAL/VIOLET/AMBER system is fully deprecated. All references to `TEAL`, `VIOLET`, `AMBER`, `purple`, and the `🟣` emoji are in `BANNED_TERMS`. The canonical signal branding constant is `SIGNAL_BRAND = "GREEN signal"` (line 462).

Additional branding at lines 718-726:

```python
BRANDING = {
    'signal_name': 'GREEN signal',
    'signal_tagline': 'GREEN means go.',
    'system_name': '5-Gate System',
    'buy_color': 'GREEN',
    'sell_color': 'RED',
    'substack_url': 'https://sterlingsignals.substack.com',
    'twitter_handle': '@SterlingSignals',
}
```

**Signal types** (lines 469-500):

```python
SIGNAL_TYPES = {
    'PASS':      {'public_name': 'GREEN Signal', 'gates_required': [1,2,3,4,5], 'show_publicly': True},
    'CONSIDER':  {'public_name': 'On Our Radar', 'gates_required': [1,2,3,4],   'show_publicly': True},
    'WATCHLIST': {'public_name': None,           'gates_required': [1,2,3],     'show_publicly': False},
    'CAUTION':   {'public_name': None,           'gates_required': None,        'show_publicly': False},
    'EXIT':      {'public_name': None,           'gates_required': None,        'show_publicly': False},
}
```

Only `PASS` and `CONSIDER` signals are shown publicly.

### 4.2 Conviction Language

Defined at lines 754-760 of `settings.py`:

```python
CONVICTION_LANGUAGE = {
    5: 'Extremely Bullish',
    4: 'Bullish',
    3: 'Watching',
    2: 'Cautious',
    1: None,   # Do not post publicly
}
```

| Score | Public Language | Postable? |
|-------|----------------|-----------|
| 5 | Extremely Bullish | Yes |
| 4 | Bullish | Yes |
| 3 | Watching | Yes |
| 2 | Cautious | Yes |
| 1 | (None) | No -- do not post publicly |

Helper function: `get_conviction_text(score: int) -> str` (lines 804-814). Returns `'Watching'` as default for invalid/missing scores.

The raw numeric terms (`"conviction 5"`, `"conviction 4"`, `"conviction 3"`, `"conviction score"`, `"conviction rating"`) are all in `BANNED_TERMS` -- only the prose equivalents may appear in public content.

### 4.3 Entry Price Display Rules

Defined at lines 762-766 of `settings.py`:

```python
ENTRY_PRICE_RULES = {
    'show_for_closed_winners': True,
    'show_for_open_above_threshold': True,
    'threshold_pct': 25.0,
}
```

Helper function: `can_show_entry_price(position: dict) -> bool` (lines 817-841).

Logic:
1. If `status == 'CLOSED'` and `pnl_pct > 0`: return `True` (closed winners always show entry).
2. If `status == 'OPEN'` and `pnl_pct >= 25.0`: return `True` (validated by performance).
3. Otherwise: return `False`.

This prevents revealing entry prices on positions that have not yet proven profitable enough to validate.

### 4.4 Age-Based Highlight Thresholds

Defined by helper function `get_highlight_threshold(days_held: int) -> float` at lines 963-984 of `settings.py`:

| Days Held | Min P&L to Highlight | Rationale |
|-----------|---------------------|-----------|
| 0-7 | 3.0% | New positions: just need to be green |
| 8-14 | 5.0% | Early momentum: showing promise |
| 15-30 | 10.0% | Building position: solid start |
| 31-60 | 15.0% | Standard threshold |
| 61+ | 20.0% | Mature positions: need stronger returns |

Younger positions have lower bars to be featured in content because even modest early gains are noteworthy. Mature positions that are only up a few percent are not worth highlighting.

Related helper: `get_position_age_category(entry_date: str) -> str` (lines 1008-1032).

| Days Held | Category |
|-----------|----------|
| 0-14 | `'early'` |
| 15-60 | `'developing'` |
| 61+ | `'mature'` |

---

## 5. Content Safeguards

### 5.1 Safeguarded Categories

Defined at lines 435-440 of `settings.py`:

```python
SAFEGUARDED_CATEGORIES = {
    'top_performers': 'has_enough_wins',
    'beat_spy':       'should_post_beat_spy',
    'self_quote':     'has_uncelebrated_wins',
    'closed_trade':   'has_winning_closed_trades',
}
```

Each key is a content category; the value names the safeguard check that must pass before that category can produce a tweet. If the safeguard fails, the system falls back to `CATEGORY_FALLBACKS` (lines 444-449):

```python
CATEGORY_FALLBACKS = {
    'top_performers': 'theme_hot',
    'beat_spy':       'engagement',
    'self_quote':     'consider_spotlight',
    'closed_trade':   'educational',
}
```

Helper functions:

- `is_safeguarded_category(category: str) -> bool` (line 940-942): Returns `True` if the category key exists in `SAFEGUARDED_CATEGORIES`.
- `get_fallback_category(category: str) -> str` (lines 935-937): Returns the fallback, defaulting to `'engagement'` if no mapping exists.

### 5.2 Win Categories

Defined at lines 875-903 of `settings.py`:

```python
WIN_CATEGORIES = {
    'top_performers': {
        'description': 'Best open positions by TOTAL return since signal entry',
        'threshold': 15.0,
        'min_positions': 2,
        'public_name': 'Top Performers',
        'tweet_frequency': 'weekly',
    },
    'early_movers': {
        'description': 'NEW signals (< 2 weeks old) showing early strength',
        'max_age_days': 14,
        'threshold': 5.0,
        'public_name': 'Early Momentum',
        'tweet_frequency': 'when_available',
    },
    'milestone_alerts': {
        'description': 'Positions crossing key thresholds (25%, 50%, 100%)',
        'thresholds': [25, 50, 100],
        'public_name': 'Milestone Alert',
        'tweet_frequency': 'when_crossed',
    },
    'recent_wins': {
        'description': 'Positions CLOSED in profit within last 14 days',
        'threshold': 15.0,
        'lookback_days': 14,
        'public_name': 'Recent Wins',
        'tweet_frequency': 'when_available',
    },
}
```

| Category | Threshold | Trigger | Frequency |
|----------|-----------|---------|-----------|
| `top_performers` | 15.0% gain, min 2 positions | Automatic | Weekly |
| `early_movers` | 5.0% gain, max 14 days old | When available | As needed |
| `milestone_alerts` | 25%, 50%, 100% crossings | When crossed | Per event |
| `recent_wins` | 15.0% gain, closed within 14 days | When available | As needed |

### 5.3 Celebration Thresholds

**Thresholds** (line 452):

```python
CELEBRATION_THRESHOLDS = [25.0, 50.0, 100.0]
```

**Tracking keys** (lines 455-459):

```python
CELEBRATION_KEYS = {
    25.0: '25_pct_celebrated',
    50.0: '50_pct_celebrated',
    100.0: '100_pct_celebrated',
}
```

**Celebration tiers** (lines 848-867):

```python
CELEBRATION_TIERS = {
    'standard':      {'threshold': 25.0,  'emoji': '📈', 'headline': 'MILESTONE ALERT'},
    'home_run':      {'threshold': 50.0,  'emoji': '🚀', 'headline': 'HOME RUN'},
    'hall_of_fame':  {'threshold': 100.0, 'emoji': '🏆', 'headline': 'HALL OF FAME'},
}
```

Helper functions:

- `get_celebration_key(pnl_pct: float) -> str` (lines 945-950): Returns the tracking key for the highest threshold met, e.g., `'100_pct_celebrated'` for a 120% gain. Returns `None` if below 25%.
- `get_highest_uncelebrated_threshold(pnl_pct: float, celebrated: dict) -> float` (lines 953-960): Walks thresholds in descending order and returns the first one that has not been celebrated yet.

### 5.4 Loss Suppression Rules

**Stopped position rules** (lines 913-920):

```python
STOPPED_POSITION_RULES = {
    'show_in_public_content': False,
    'show_in_newsletter': False,
    'show_in_top_performers': False,
    'show_in_any_tweet': False,
    'internal_tracking': True,
    'mention_discipline_publicly': False,
}
```

Every field except `internal_tracking` is `False`. Stopped (losing) positions are never shown in any public content, never included in performance tweets, and the system does not even publicly mention that "the stop worked" (which would imply a loss).

**Marketing threshold for loss mention** (from `MARKETING_THRESHOLDS`):

```python
'max_loss_to_mention': -5.0   # Never mention positions worse than -5%
```

**Cold streak circuit breaker** (from `MARKETING_THRESHOLDS`):

```python
'cold_streak_threshold': 3       # Number of consecutive losses
'cold_streak_lookback_days': 14  # Days to look back
```

**SPY comparison method** (line 923):

```python
SPY_COMPARISON_METHOD = 'matched_period'
```

This ensures SPY comparisons use the same holding period as the position, preventing misleading timeframe mismatches.

**Timeframe disclaimers** (lines 906-910):

```python
TIMEFRAME_DISCLAIMERS = {
    'short':  'Returns since signal entry.',
    'medium': 'Total gain since entry, not weekly movement.',
    'long':   'Sterling Signals targets 50-100% returns over 3-8 month holds. '
              'Returns shown are total since signal entry.',
}
```

**Honesty rules summary:**
- Newsletter: always shows full P&L including losers.
- Tweets: never show losses. `STOPPED_POSITION_RULES['show_in_any_tweet'] = False`.
- Framework: losses framed as "system working as designed" internally, but not mentioned publicly per `mention_discipline_publicly: False`.

---

## 6. Output Paths (`config/output_paths.py`)

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/config/output_paths.py`
**Lines:** 1-310
**Imports:** `shutil`, `datetime.datetime`, `pathlib.Path`, `typing.Dict`, `typing.List`, `typing.Optional`, `typing.Tuple`

### 6.1 Directory Structure

Created by `ensure_output_structure()` (lines 87-122):

```
scanner/output/
  current/                      # Latest week outputs
  archive/
    YYYY-WXX/                   # ISO week archive

portfolio/output/
  portfolio_backups/

substack/output/
  current/
    substack_notes/
    substack_posts/

twitter/output/
  charts/
  content_queue*.json
```

### 6.2 Helper Functions

| Function | Signature | Line | Purpose |
|----------|-----------|------|---------|
| `get_week_identifier` | `(dt: Optional[datetime] = None) -> str` | 44 | Returns `"YYYY-WXX"` ISO week string |
| `get_current_dir` | `() -> Path` | 60 | Returns `scanner/output/current/` |
| `get_week_dir` | `(dt: Optional[datetime] = None) -> Path` | 73 | Returns `scanner/output/archive/YYYY-WXX/` |
| `ensure_output_structure` | `() -> Tuple[Path, Path]` | 87 | Creates all dirs, returns `(current_dir, week_dir)` |
| `get_output_paths` | `() -> Dict[str, Path]` | 125 | Returns dict with keys: `trades`, `current`, `week`, `backups` |
| `save_to_current_and_archive` | `(content: str, filename: str) -> Tuple[Path, Path]` | 144 | Writes to both `current/` and `weeks/` |
| `copy_to_current_and_archive` | `(source: Path, filename: Optional[str]) -> Tuple[Path, Path]` | 169 | Copies file to both locations |
| `create_legacy_symlinks` | `() -> None` | 194 | Creates symlinks from old paths to new structure |
| `get_relative_path` | `(path: Path) -> str` | 234 | Returns path relative to CWD for display |
| `list_weekly_archives` | `() -> List[str]` | 250 | Returns sorted list of week identifiers |

### 6.3 Weekly Archive Pattern

Each Friday scan saves outputs to both `scanner/output/current/` and `scanner/output/archive/YYYY-WXX/`. The `save_to_current_and_archive()` function (line 144) handles this dual-write pattern. `current/` always contains the latest outputs for scripts that do not need to specify a date. `weeks/` provides historical access.

Legacy symlinks (line 194) maintain backwards compatibility:

| Old Path (legacy trades/) | New Path (section output/) |
|--------------------|---------------------------|
| `latest_report.txt` | `report.txt` |
| `latest_newsletter_briefing.md` | `newsletter_briefing.md` |
| `latest_newsletter.html` | `newsletter.html` |
| `signals.json` | `signals.json` |

On Windows where symlinks may fail, `create_legacy_symlinks()` falls back to `shutil.copy()`.

---

## 7. Package Re-Exports (`config/__init__.py`)

**File:** `/Users/mattydeighton/Downloads/bos_momentum_scanner/config/__init__.py`
**Lines:** 1-8

```python
"""
CONFIG -- Re-exports all settings for backwards compatibility.

All modules can continue using `from config import X` unchanged.
The actual configuration lives in config/settings.py.
"""
from config.settings import *  # noqa: F401,F403
```

This wildcard re-export means every public name in `settings.py` is available via `from config import NAME`. This includes all constants, dicts, and helper functions defined at module level in `settings.py`.

Notably, `marketing_vocabulary.py` is NOT re-exported through `__init__.py`. Modules that need validation functions must import directly:

```python
from config.marketing_vocabulary import validate_content, BANNED_TERMS
```

Or use the `settings.py` version of `contains_banned_term()` via:

```python
from config import contains_banned_term
```

---

## 8. Twitter Account Configuration

### Multi-Account Setup

Defined at lines 149-168 of `settings.py`:

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

| Account | Env Prefix | Queue File | Offset | Style |
|---------|-----------|------------|--------|-------|
| `main` | `X` | `content_queue.json` | 0 min | `original` |
| `account2` | `X2` | `content_queue_account2.json` | +10 min | `conversational` |
| `account3` | `X3` | `content_queue_account3.json` | +20 min | `data_driven` |

The `env_prefix` determines which environment variables supply credentials: `X_API_KEY`, `X2_API_KEY`, `X3_API_KEY`, etc.

### Account Personas

Defined at lines 175-224 of `settings.py`:

**`main` -- "The System" (Analyst)**
- Tone: authoritative, professional
- Traits: data-driven, precise, confident
- Focus: scanner_results, signal_announcements, system_performance
- Signature phrases: "The scanner doesn't lie.", "Data drives decisions.", "That's the 5-Gate System in action.", "Quality over quantity. Always."

**`account2` -- "The Mentor" (Teacher)**
- Tone: conversational, approachable
- Traits: helpful, patient, encouraging
- Focus: educational, process_explanation, trading_psychology
- Signature phrases: "Here's why this matters...", "Let me break this down.", "The lesson here:", "Most traders miss this."

**`account3` -- "The Trader" (Practitioner)**
- Tone: direct, casual
- Traits: action-oriented, confident, punchy
- Focus: real_time_market_color, power_hour, theme_momentum
- Signature phrases: "Eyes on this one.", "The close matters.", "Momentum is real.", "Let's see how this plays out."

Helper: `get_persona(account_id: str) -> Dict` (lines 282-284). Falls back to `PERSONAS['main']` for unknown accounts.

---

## 9. Slot and Schedule Configuration

### Slot Definitions

Three parallel dictionaries define the 5 daily tweet slots (lines 291-314):

**Slot names** (`SLOTS`, lines 291-297):

| Slot | Name |
|------|------|
| 1 | `"pre_market"` |
| 2 | `"morning"` |
| 3 | `"midday"` |
| 4 | `"power_hour"` |
| 5 | `"after_hours"` |

**Slot times ET** (`SLOT_TIMES_ET`, lines 299-305):

| Slot | ET Time |
|------|---------|
| 1 | `"08:00"` |
| 2 | `"10:00"` |
| 3 | `"12:30"` |
| 4 | `"15:30"` |
| 5 | `"18:00"` |

**Slot times UTC** (`SLOT_TIMES_UTC`, lines 308-314, assumes EST not EDT):

| Slot | UTC Time |
|------|----------|
| 1 | `"13:00"` |
| 2 | `"15:00"` |
| 3 | `"17:30"` |
| 4 | `"20:30"` |
| 5 | `"23:00"` |

### Weekly Content Schedule

Defined at lines 662-712 of `settings.py` as `WEEKLY_SCHEDULE`. Each day maps to a list of `(slot_number, content_type)` tuples:

**Saturday:**
1. `top_performers` (safeguarded)
2. `thread_buy_signal`
3. `theme_hot`
4. `funnel_graphic`
5. `engagement`

**Sunday:**
1. `buy_signal`
2. `consider_spotlight`
3. `beat_spy` (safeguarded)
4. `theme_hot`
5. `engagement`

**Monday:**
1. `theme_hot`
2. `milestone_alerts` (safeguarded)
3. `educational`
4. `power_hour`
5. `engagement`

**Tuesday:**
1. `early_movers`
2. `theme_hot`
3. `educational`
4. `power_hour`
5. `engagement`

**Wednesday:**
1. `consider_spotlight`
2. `milestone_alerts` (safeguarded)
3. `sector_rotation`
4. `power_hour`
5. `engagement`

**Thursday:**
1. `theme_hot`
2. `buy_signal`
3. `educational`
4. `power_hour`
5. `engagement`

**Friday:**
1. `recent_wins`
2. `theme_hot`
3. `sector_rotation`
4. `power_hour`
5. `engagement`

Safeguarded slots (marked above) require data validation before generation. If the safeguard fails, the system substitutes the fallback category from `CATEGORY_FALLBACKS`.

### Day-Aware Content Rules

Defined at lines 231-274 of `settings.py` as `DAY_CONTENT_RULES`. Each day specifies context, allowed phrases, blocked phrases, and time reference:

| Day | Context | Time Reference | Key Blocked Phrases |
|-----|---------|----------------|---------------------|
| Saturday | Newsletter dropped, weekend recap | "Friday's close" | "Today", "Right now", "Power hour", "Into the close" |
| Sunday | Prep for week ahead | "Friday's close" | "Today", "Power hour", "Into the close" |
| Monday | Week kickoff | "Friday's close" | "Weekend homework", "Saturday" |
| Tuesday | Mid-early week | "the weekly scan" | "Weekend", "Friday close", "Saturday" |
| Wednesday | Mid-week check-in | "the weekly scan" | "Weekend", "Friday close", "Saturday" |
| Thursday | Building to Friday scan | "tomorrow's scan" | "Weekend homework", "Last Friday", "Saturday" |
| Friday | Scan day | "today's close" | "Last week", "Weekend homework", "Next Friday" |

Helper: `get_day_context(day: str) -> Dict` (lines 277-279). Returns Saturday rules as default for unknown days.

---

## 10. Environment Variables Registry

Complete listing of all environment variables referenced across the codebase:

### Required

| Variable | Used By | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | `core/scanner.py`, `core/gatekeeper.py`, `core/thematic_analyzer.py`, `content/reaction_generator.py`, `content/market_analyzer.py`, `core/dd_automator.py` | Anthropic API authentication |

### Twitter/X Credentials (per account)

| Variable Pattern | Account | Used By |
|-----------------|---------|---------|
| `X_API_KEY` | main | `distribution/twitter_poster.py` |
| `X_API_SECRET` | main | `distribution/twitter_poster.py` |
| `X_ACCESS_TOKEN` | main | `distribution/twitter_poster.py` |
| `X_ACCESS_SECRET` | main | `distribution/twitter_poster.py` |
| `X2_API_KEY` | account2 | `distribution/twitter_poster.py` |
| `X2_API_SECRET` | account2 | `distribution/twitter_poster.py` |
| `X2_ACCESS_TOKEN` | account2 | `distribution/twitter_poster.py` |
| `X2_ACCESS_SECRET` | account2 | `distribution/twitter_poster.py` |
| `X3_API_KEY` | account3 | `distribution/twitter_poster.py` |
| `X3_API_SECRET` | account3 | `distribution/twitter_poster.py` |
| `X3_ACCESS_TOKEN` | account3 | `distribution/twitter_poster.py` |
| `X3_ACCESS_SECRET` | account3 | `distribution/twitter_poster.py` |

The env prefix for each account is defined in `TWITTER_ACCOUNTS[account_id]['env_prefix']`. The poster appends `_API_KEY`, `_API_SECRET`, `_ACCESS_TOKEN`, `_ACCESS_SECRET` to the prefix.

### Email / SMTP (Optional)

| Variable | Used By | Purpose |
|----------|---------|---------|
| `SMTP_SERVER` | `distribution/email_notifier.py` | SMTP server hostname |
| `SMTP_PORT` | `distribution/email_notifier.py` | SMTP port (typically 587) |
| `EMAIL_SENDER` | `distribution/email_notifier.py` | Sender email address |
| `EMAIL_PASSWORD` | `distribution/email_notifier.py` | SMTP password / app password |
| `EMAIL_RECIPIENTS` | `distribution/email_notifier.py` | Comma-separated recipient list |

### GitHub Actions Secrets

| Secret | Workflow | Purpose |
|--------|----------|---------|
| `ANTHROPIC_API_KEY` | `friday_scan.yml` | Scanner LLM calls |
| `TWITTER_API_KEY` | `daily_post.yml` | Legacy name, maps to `X_API_KEY` |
| `TWITTER_API_SECRET` | `daily_post.yml` | Legacy name, maps to `X_API_SECRET` |
| `TWITTER_ACCESS_TOKEN` | `daily_post.yml` | Legacy name, maps to `X_ACCESS_TOKEN` |
| `TWITTER_ACCESS_SECRET` | `daily_post.yml` | Legacy name, maps to `X_ACCESS_SECRET` |

### Future / Documented but Not Yet Active

| Variable | Purpose |
|----------|---------|
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Service account JSON for Google Sheets sync |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Target spreadsheet ID |
| `SUBSTACK_PUBLISH_EMAIL` | Email-to-publish address for Substack |

---

## 11. Additional Configuration Structures

### 11.1 Content Types

Defined at lines 326-354 of `settings.py` (`CONTENT_TYPES` list):

**Signal categories:** `buy_signal`, `thread_buy_signal`, `consider_spotlight`

**Theme categories:** `theme_hot`, `theme_cold`, `sector_rotation`

**Performance categories (safeguarded):** `top_performers`, `early_movers`, `milestone_alerts`, `recent_wins`, `beat_spy`

**Content categories:** `educational`, `engagement`, `power_hour`, `funnel_graphic`

**Rarely used:** `closed_trade`, `sell_signal`, `system_promo`, `market_insight`, `post_mortem`, `win_card`, `alpha_card`

A parallel `CONTENT_TYPES` list exists in `marketing_vocabulary.py` (lines 430-460) with slightly different membership: it includes `self_quote`, `newsletter`, `weekly_recap`, `thread_educational` but omits `sector_rotation`, `milestone_alerts`, `recent_wins`, `system_promo`, `market_insight`, `post_mortem`, `win_card`, `alpha_card`.

Deprecated types are tracked in `marketing_vocabulary.py` at lines 463-468:

```python
DEPRECATED_CONTENT_TYPES = [
    "roth_ira",
    "pdt_friendly",
    "position_update",
    "weekly_wins",
]
```

### 11.2 Image Filename Patterns

Defined at lines 644-655 of `settings.py`:

| Pattern Key | Template |
|-------------|----------|
| `top_performers` | `top_performers_{date}.png` |
| `beat_spy` | `beat_spy_{date}.png` |
| `funnel` | `funnel_{date}.png` |
| `theme_card` | `theme_{theme}_{date}.png` |
| `milestone` | `milestone_{ticker}_{date}.png` |
| `consider` | `consider_{date}.png` |
| `chart` | `{ticker}_{date}.png` |
| `early_movers` | `early_movers_{date}.png` |
| `sector_rotation` | `sector_rotation_{date}.png` |
| `portfolio_dashboard` | `portfolio_dashboard_{date}.png` (internal only) |

Helper: `get_image_filename(pattern_key: str, **kwargs) -> str` (lines 1060-1073).

### 11.3 Visualization Constants

Defined at lines 383-393 of `settings.py`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `CARD_WIDTH` | `1200` | Twitter card width (px) |
| `CARD_HEIGHT` | `675` | Twitter card height (px) |
| `CARD_BG_COLOR` | `"#1a1a2e"` | Dark theme background |
| `CARD_TEXT_COLOR` | `"#ffffff"` | White text |
| `CARD_ACCENT_GREEN` | `"#00ff88"` | Win/bullish accent |
| `CARD_ACCENT_RED` | `"#ff4444"` | Loss/bearish accent |

### 11.4 Data Download Settings

Defined at lines 374-380 of `settings.py`:

| Constant | Value | Line | Purpose |
|----------|-------|------|---------|
| `YFINANCE_PERIOD` | `"1y"` | 378 | Data period for beta calculation |
| `YFINANCE_INTERVAL` | `"1d"` | 379 | Data interval |
| `MIN_TRADING_DAYS` | `60` | 380 | Minimum data points for valid beta |

### 11.5 Substack Content Schedule

Defined at lines 768-789 of `settings.py`:

| Day | Type | Title Format | Filename |
|-----|------|-------------|----------|
| Monday | `market_analysis` | `"Market Outlook: Week of {date}"` | `monday_market_analysis.html` |
| Thursday | `theme_spotlight` | `"Theme Watch: {theme_name}"` | `thursday_theme_spotlight.html` |
| Saturday | `weekly_signals` | `"GREEN Signals: {date}"` | `saturday_weekly_signals.html` |
| Sunday | `deep_dive` | `"Deep Dive: ${ticker}"` | `sunday_deep_dive.html` |

### 11.6 Ticker Aliases

Defined at lines 1081-1092 of `settings.py`:

```python
TICKER_ALIASES = {
    'FB': 'META',
    'TWTR': 'X',
    'GOOGL': 'GOOG',
    'BRK.A': 'BRK-A',
    'BRK.B': 'BRK-B',
}
```

Helper functions:
- `normalize_ticker(ticker: str) -> str` (lines 1095-1107): Returns canonical name.
- `get_ticker_history(ticker: str) -> List[str]` (lines 1110-1132): Returns all known names (current + historical).

### 11.7 Signal Classifications

Defined at lines 425-431 of `settings.py`:

```python
SIGNAL_CLASSIFICATIONS = {
    'PASS':      'Cleared all 5 gates - full GREEN recommendation',
    'CONSIDER':  'Cleared gates 1-4, watching for gate 5',
    'WATCHLIST': 'Strong technical setup, theme alignment pending',
    'CAUTION':   'Open position showing weakness',
    'EXIT':      'Stop triggered or thesis broken',
}
```

---

## 12. Complete Helper Functions Index

All helper functions defined in `config/settings.py`:

| Function | Signature | Line | Returns |
|----------|-----------|------|---------|
| `get_day_context` | `(day: str) -> Dict` | 277 | Content rules for a day; defaults to Saturday |
| `get_persona` | `(account_id: str) -> Dict` | 282 | Persona dict; defaults to `main` |
| `enforce_green_branding` | `(text: str) -> str` | 584 | Text with old terms replaced by GREEN branding |
| `check_ticker_frequency` | `(ticker: str, existing_tweets: list) -> bool` | 609 | True if ticker can be mentioned again |
| `validate_not_killed_category` | `(category: str) -> bool` | 623 | True if allowed; raises ValueError if killed |
| `get_signal_emoji` | `(signal_type: str) -> str` | 792 | Emoji string; empty if not found |
| `get_conviction_text` | `(score: int) -> str` | 804 | Public language; defaults to `'Watching'` |
| `can_show_entry_price` | `(position: dict) -> bool` | 817 | True if entry price can be shown publicly |
| `get_marketing_threshold` | `(key: str, default: float) -> float` | 930 | Threshold value from `MARKETING_THRESHOLDS` |
| `get_fallback_category` | `(category: str) -> str` | 935 | Fallback category; defaults to `'engagement'` |
| `is_safeguarded_category` | `(category: str) -> bool` | 940 | True if category needs safeguard check |
| `get_celebration_key` | `(pnl_pct: float) -> str` | 945 | Tracking key for highest threshold met |
| `get_highest_uncelebrated_threshold` | `(pnl_pct: float, celebrated: dict) -> float` | 953 | Highest uncelebrated threshold |
| `get_highlight_threshold` | `(days_held: int) -> float` | 963 | Minimum P&L for highlighting by age |
| `format_holding_period` | `(days_held: int) -> str` | 987 | Human-readable period string |
| `get_position_age_category` | `(entry_date: str) -> str` | 1008 | `'early'`, `'developing'`, or `'mature'` |
| `contains_banned_term` | `(text: str) -> bool` | 1035 | True if any banned term found |
| `get_image_filename` | `(pattern_key: str, **kwargs) -> str` | 1060 | Formatted image filename |
| `normalize_ticker` | `(ticker: str) -> str` | 1095 | Canonical ticker name |
| `get_ticker_history` | `(ticker: str) -> List[str]` | 1110 | All known names for a ticker |

All helper functions defined in `config/marketing_vocabulary.py`:

| Function | Signature | Line | Returns |
|----------|-----------|------|---------|
| `validate_content` | `(text: str) -> Tuple[bool, List[str]]` | 209 | `(is_valid, violations)` |
| `validate_green_red_consistency` | `(text: str) -> Tuple[bool, List[str]]` | 250 | `(is_valid, issues)` |
| `log_violations` | `(content_type: str, violations: List[str]) -> None` | 280 | Prints warning |
| `get_replacement` | `(internal_term: str) -> str` | 292 | Marketing replacement term |
| `validate_all_tweets` | `(tweets: list) -> Tuple[int, int]` | 305 | `(total_checked, violation_count)` |
| `@validate_output` | `(strict: bool, content_type: str) -> Callable` | 347 | Decorator |
| `_check_content` | `(text: str, source: str, strict: bool, content_type: str) -> None` | 392 | Internal helper |
| `validated_content` | `(text: str, content_type: str) -> str` | 403 | Original text (with logging) |

All helper functions defined in `config/output_paths.py`:

| Function | Signature | Line | Returns |
|----------|-----------|------|---------|
| `get_week_identifier` | `(dt: Optional[datetime]) -> str` | 44 | `"YYYY-WXX"` string |
| `get_current_dir` | `() -> Path` | 60 | `scanner/output/current/` |
| `get_week_dir` | `(dt: Optional[datetime]) -> Path` | 73 | `scanner/output/archive/YYYY-WXX/` |
| `ensure_output_structure` | `() -> Tuple[Path, Path]` | 87 | `(current_dir, week_dir)` |
| `get_output_paths` | `() -> Dict[str, Path]` | 125 | Dict with `trades`, `current`, `week`, `backups` |
| `save_to_current_and_archive` | `(content: str, filename: str) -> Tuple[Path, Path]` | 144 | `(current_path, archive_path)` |
| `copy_to_current_and_archive` | `(source: Path, filename: Optional[str]) -> Tuple[Path, Path]` | 169 | `(current_path, archive_path)` |
| `create_legacy_symlinks` | `() -> None` | 194 | Creates symlinks |
| `get_relative_path` | `(path: Path) -> str` | 234 | Relative path string |
| `list_weekly_archives` | `() -> List[str]` | 250 | Sorted list of week IDs |

---

## 13. Cross-Reference: Dual BANNED_TERMS Lists

Both `config/settings.py` (lines 507-550) and `config/marketing_vocabulary.py` (lines 27-73) define `BANNED_TERMS`. Because `config/__init__.py` re-exports from `settings.py`, `from config import BANNED_TERMS` returns the `settings.py` version. Modules importing from `marketing_vocabulary` directly get the other version.

**Terms only in `settings.py`:**
- `"Banker score"`
- `"weekly winners"`
- `"this week we nailed"`

**Terms only in `marketing_vocabulary.py`:**
- `"Banker >= 55"` (unicode version)
- `"Beta >= 1.5"` (unicode version)
- `"beta threshold"`
- `"HMA pivot"` (lowercase variant)
- `"banker indicator"` (lowercase variant)
- `"weekly bos"` (lowercase variant)
- `"ISA wrapper"`, `"Barclays ISA"`
- `"UK investor"`, `"UK investors"`, `"UK trader"`, `"UK traders"`
- `"UK time"` (lowercase variant), `"London time"`
- `"GBP/USD"`
- `"Weekly pivot"`
- `"conviction 5"`, `"conviction 4"`, `"conviction 3"`, `"conviction score"`, `"conviction rating"`

Both `contains_banned_term()` in `settings.py` and `validate_content()` in `marketing_vocabulary.py` use word-boundary regex for the same set of short terms (`RSI`, `MACD`, `KDJ`, `BoS`, `BOS`, `GMT`, `BST`, `HMA`, `PDT`, `TEAL`, `teal`). The implementations are nearly identical.

This dual-list pattern is a known debt from the reorganization. The recommended resolution is to consolidate into a single canonical list in one location and have the other import it.

---

*End of Configuration and Rules audit.*
