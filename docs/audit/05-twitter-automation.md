# Sterling Signals X/Twitter Automation Audit

**Document:** 05-twitter-automation.md
**Last Updated:** 2026-01-27
**Status:** Complete

---

## Executive Summary

This audit documents the automated X/Twitter posting system for Sterling Signals. The system generates 25 tweets per week (5/day) with comprehensive safeguards to prevent exposure of losing positions or banned terminology.

### Key Findings

| Finding | Severity | Description |
|---------|----------|-------------|
| TWA-1 | INFO | Comprehensive safeguard system with 2 validation layers |
| TWA-2 | INFO | Negative P&L regex check blocks losses at queue and post time |
| TWA-3 | LOW | EDT/EST timezone shift may offset posts by 1 hour during DST |
| TWA-4 | LOW | Thread partial failure stops entire thread (no resume) |
| TWA-5 | INFO | No exponential backoff retry logic - relies on Tweepy defaults |

---

## 1. Post Types and Triggers

### 1.1 Complete Content Type Inventory

**Location:** `config.py` lines 125-153

| Category | Trigger | Safeguarded | Fallback |
|----------|---------|-------------|----------|
| `buy_signal` | PASS signals in queue | No | N/A |
| `thread_buy_signal` | Top TEAL signal with deep-dive | No | N/A |
| `consider_spotlight` | CONSIDER signals available | No | N/A |
| `theme_hot` | PRIME/INVESTABLE themes exist | No | N/A |
| `theme_cold` | SELECTIVE/AVOID themes exist | No | N/A |
| `sector_rotation` | Theme flow data available | No | N/A |
| `top_performers` | 2+ winners at 15%+ | **Yes** | `theme_hot` |
| `early_movers` | New signals (<14 days) at 5%+ | No | N/A |
| `milestone_alerts` | Position crosses 25%/50%/100% | **Yes** | `consider_spotlight` |
| `recent_wins` | Closed trades with profit (14 days) | No | N/A |
| `beat_spy` | Portfolio +5% vs SPY | **Yes** | `engagement` |
| `educational` | Always (static content) | No | N/A |
| `engagement` | Always (community building) | No | N/A |
| `power_hour` | Market hours (15:30 ET) | No | N/A |
| `funnel_graphic` | Scan stats available | No | N/A |
| `closed_trade` | Winning closed trades exist | **Yes** | `educational` |
| `sell_signal` | Stop hit or BoS down | No | N/A |

### 1.2 Killed Categories (NEVER USE)

**Location:** `config.py` lines 58-64

| Category | Reason Killed |
|----------|---------------|
| `roth_ira` | Wrong audience (audience-neutral now) |
| `pdt_friendly` | Wrong audience (US PDT rule irrelevant) |
| `position_update` | Merged into `top_performers` |
| `weekly_wins` | Renamed to `top_performers` (misleading) |
| `self_quote` | Renamed to `milestone_alerts` |

### 1.3 Weekly Posting Schedule

**Location:** `config.py` lines 499-549

**Slot Times (Eastern Time):**

| Slot | Time ET | Description |
|------|---------|-------------|
| 1 | 08:00 | Pre-market engagement |
| 2 | 10:00 | 30 min post-open |
| 3 | 12:30 | Lunch engagement |
| 4 | 15:30 | **CRITICAL: Power Hour** |
| 5 | 18:00 | After-hours wrap |

**Weekly Grid (25 tweets):**

| Day | Slot 1 | Slot 2 | Slot 3 | Slot 4 | Slot 5 |
|-----|--------|--------|--------|--------|--------|
| **Saturday** | top_performers* | thread_buy_signal | theme_hot | funnel_graphic | engagement |
| **Sunday** | buy_signal | consider_spotlight | beat_spy* | theme_hot | engagement |
| **Monday** | theme_hot | milestone_alerts* | educational | power_hour | engagement |
| **Tuesday** | early_movers | theme_hot | educational | power_hour | engagement |
| **Wednesday** | consider_spotlight | milestone_alerts* | sector_rotation | power_hour | engagement |
| **Thursday** | theme_hot | buy_signal | educational | power_hour | engagement |
| **Friday** | recent_wins | theme_hot | sector_rotation | power_hour | engagement |

*Categories marked with * are safeguarded and may fall back to alternatives.

---

## 2. Template Formats and Data Insertion

### 2.1 Single Tweet Structure

**Queue JSON Format:**
```json
{
  "id": "monday_slot1_theme_hot_001",
  "day": "Monday",
  "slot": 1,
  "category": "theme_hot",
  "text": "Tweet text under 280 chars with $TICKER mentions...",
  "ticker": "NVDA",
  "theme": "AI Infrastructure",
  "image_path": "trades/charts/NVDA_20260127.png",
  "scheduled_date": "2026-01-27",
  "is_thread": false,
  "status": "pending",
  "posted_at": null,
  "tweet_id": null,
  "validation_errors": []
}
```

### 2.2 Thread Structure (5-Tweet Deep Dives)

```json
{
  "id": "thread_buy_signal_sat_001",
  "is_thread": true,
  "day": "Saturday",
  "slot": 2,
  "category": "thread_buy_signal",
  "thread_topic": "AI Infrastructure Breakout: $NVDA",
  "thread_tweets": [
    { "number": 1, "text": "🧵 TEAL Signal Deep Dive: $NVDA\n\nWhy this cleared all 5 gates..." },
    { "number": 2, "text": "Gate Analysis:\n\n✅ Structural pivot confirmed\n✅ Institutional accumulation..." },
    { "number": 3, "text": "Theme Fit: AI Infrastructure\n\nScore: 8.2/10 (PRIME)...", "image_path": "..." },
    { "number": 4, "text": "Risk/Reward Setup:\n\n• Entry: $XXX\n• Stop: Systematic trailing stop...", "image_path": "..." },
    { "number": 5, "text": "Full analysis in this week's Sterling Signals newsletter 👇\n\nhttps://sterlingsignals.substack.com" }
  ],
  "scheduled_date": "2026-01-25",
  "thread_status": "pending",
  "posted_at": null
}
```

### 2.3 Dynamic Data Insertion

**Position Formatting with Holding Period:**

**Location:** `tweet_generator.py` lines 490-533

```python
def format_position_with_age(pos: dict) -> str:
    ticker = pos.get('ticker')
    pnl = pos.get('pnl_pct', 0)
    entry_date = pos.get('entry_date')

    days = (datetime.now() - datetime.strptime(entry_date, '%Y-%m-%d')).days

    if days <= 7:
        period = f"{days} days"
    elif days <= 30:
        period = f"{days // 7} weeks"
    else:
        period = f"{days // 30} months"

    return f"${ticker} +{pnl:.1f}% ({period})"
```

**Example Outputs:**
```
$NVDA +42.1% (3 months)
$RCAT +25.3% (4 weeks)
$INOD +5.2% (3 days)
```

### 2.4 Character Count Management

**Location:** `tweet_generator.py` lines 138-176

**Twitter's Character Algorithm:**
```python
def get_tweet_char_count(text: str) -> int:
    char_count = 0
    for char in text:
        if ord(char) > 0xFFFF:  # Emoji/special chars
            char_count += 2
        else:
            char_count += 1
    return char_count
```

**Auto-Truncation:**
```python
def truncate_tweet(text: str, max_length: int = 275) -> str:
    # Preserve URL at end if present
    # Truncate with "..." if needed
    # Leave 5 char buffer for safety
```

### 2.5 Image/Chart Attachment Logic

**Location:** `twitter_poster.py` lines 336-359

```python
def upload_media(api_v1, image_path: str) -> Optional[str]:
    # Try path as-is first
    path = Path(image_path)

    # Fall back to trades/[path]
    if not path.exists():
        path = TRADES_DIR / image_path

    if not path.exists():
        print(f"  ⚠ Image not found: {image_path}")
        return None  # Tweet posts without image

    media = api_v1.media_upload(str(path))
    return media.media_id_string
```

**Image Sources:**
- `trades/charts/{ticker}_{date}.png` - TradingView captures
- `trades/graphics/funnel_{date}.png` - Scan funnel visualization
- `trades/graphics/beat_spy_{date}.png` - SPY comparison graphic
- `trades/graphics/top_performers_{date}.png` - Winner showcase

---

## 3. CRITICAL Marketing Safeguards

### 3.1 Two-Layer Validation Architecture

**Layer 1: Queue-Time Validation**
- Function: `validate_tweet_before_queue()`
- Location: `tweet_generator.py` lines 232-346
- Runs when tweet is added to content_queue.json
- Checks 8 validation rules

**Layer 2: Post-Time Validation**
- Function: `validate_before_posting()`
- Location: `twitter_poster.py` lines 95-161
- Runs immediately before API call
- **LAST LINE OF DEFENSE**
- Checks 5 critical rules

### 3.2 "Never Display Losing Positions" Enforcement

#### Primary Filter: `filter_public_positions()`

**Location:** `signal_tracker.py` lines 690-741

```python
def filter_public_positions(positions: List[Dict]) -> List[Dict]:
    public_positions = []

    for pos in positions:
        # CRIT-3: Never show STOPPED positions
        if pos.get('status') == 'STOPPED':
            continue

        # Calculate P&L if not provided
        pnl_pct = pos.get('pnl_pct')
        if pnl_pct is None:
            pnl_pct = ((current_price / entry_price) - 1) * 100

        # ONLY include positive P&L (winners)
        if pnl_pct >= 0:  # Breakeven OK, losses NEVER
            public_positions.append(pos)

    return public_positions
```

**Key Protection Points:**
- Line 716-717: Skip all `STOPPED` status positions
- Line 734: Only include `pnl_pct >= 0`
- Automatic price fetch if P&L not pre-calculated

#### Secondary Check: Negative P&L Regex

**Queue-Time Check (tweet_generator.py:316-318):**
```python
negative_pnl = re.findall(r'-\d+\.?\d*%', text)
if negative_pnl:
    errors.append(f"LOSER SHOWN: Negative P&L found: {negative_pnl}")
```

**Post-Time Check (twitter_poster.py:131-133):**
```python
negative_pnl = re.findall(r'-\d+\.?\d*%', text)
if negative_pnl:
    return (False, f"BLOCKED: Negative P&L in tweet: {negative_pnl}")
```

### 3.3 Losing Position Definition

A position is considered "losing" if ANY of:

| Condition | Check Location | Action |
|-----------|----------------|--------|
| `pnl_pct < 0` | filter_public_positions:734 | Excluded from public list |
| `status == 'STOPPED'` | filter_public_positions:716 | Excluded regardless of P&L |
| `-X.X%` in text | validate_before_posting:131 | Tweet blocked |

### 3.4 Potential Edge Cases

| Edge Case | Protection | Gap Risk |
|-----------|------------|----------|
| P&L rounds to -0.0% | `pnl_pct >= 0` catches this | LOW |
| Manual text entry with loss | Regex catches `-X%` pattern | LOW |
| Price fetch failure | Uses entry_price as fallback (shows 0%) | MEDIUM |
| STOPPED with positive final P&L | Filtered by status check | NONE |
| Breakeven position (0%) | Included in public (not a loss) | NONE |

---

## 4. Selective Showcase System

### 4.1 Top Performers Selection

**Function:** `has_enough_wins()`
**Location:** `signal_tracker.py` lines 615-658

**Thresholds (config.py:242, 251):**
```python
'min_win_to_highlight': 15.0,         # Minimum P&L %
'min_winners_for_top_performers': 2,  # Need at least 2 winners
```

**Logic:**
```python
def has_enough_wins(positions, min_winners=2, min_pnl=15.0):
    winner_count = 0

    for pos in positions:
        pnl_pct = pos.get('pnl_pct')
        if pnl_pct is None:
            pnl_pct = ((current_price / entry_price) - 1) * 100

        if pnl_pct >= min_pnl:
            winner_count += 1

    return winner_count >= min_winners
```

**Selection Order:**
1. Filter to only public positions (winners, no STOPPED)
2. Filter to only positions above 15%
3. Sort by P&L descending
4. Take top N for display

### 4.2 Beat SPY Safeguard

**Function:** `should_post_beat_spy()`
**Location:** `signal_tracker.py` lines 609-612

**Threshold:** Must outperform SPY by ≥5% (config.py:248)

```python
def should_post_beat_spy() -> bool:
    result = calculate_portfolio_vs_spy()
    return result['should_post_beat_spy']
```

### 4.3 Milestone Alerts Selection

**Thresholds (config.py:292, 570-589):**

| Threshold | Category | Emoji | Headline |
|-----------|----------|-------|----------|
| 25% | standard | 📈 | MILESTONE ALERT |
| 50% | home_run | 🚀 | HOME RUN |
| 100% | hall_of_fame | 🏆 | HALL OF FAME |

**Tracking File:** `trades/celebrations.json`
```json
{
  "NVDA": {
    "25_pct_celebrated": "2026-01-15",
    "50_pct_celebrated": null,
    "100_pct_celebrated": null
  }
}
```

### 4.4 Ticker Frequency Limits (Anti-Repetition)

**Location:** `config.py` lines 47-51, 261

```python
TICKER_LIMITS = {
    'max_mentions_per_week': 4,        # Max times per week
    'max_consecutive_days': 2,         # Max consecutive days
    'cooldown_after_milestone': 2,     # Days after celebration
}
```

**Enforcement:** `validate_tweet_before_queue()` line 340-344
```python
tickers = re.findall(r'\$([A-Z]+)', text)
for ticker in tickers:
    mentions = sum(1 for t in existing_tweets if ticker in t.get('text', ''))
    if mentions >= 4:
        errors.append(f"TICKER OVEREXPOSED: ${ticker}")
```

---

## 5. Posting Pipeline

### 5.1 Content Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TWITTER POSTING PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

FRIDAY (Generation)
═══════════════════

    ┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
    │ scanner.py  │ -> │ tweet_generator │ -> │ validate_tweet_  │
    │ signals.json│    │      .py        │    │  before_queue()  │
    └─────────────┘    └─────────────────┘    └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │ content_queue.   │
                                              │     json         │
                                              │ (25 tweets)      │
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │ GitHub Artifact  │
                                              │ (friday_scan.yml)│
                                              └──────────────────┘

DAILY (Posting - 5x per day)
════════════════════════════

    ┌─────────────────┐
    │ GitHub Actions  │  <- Cron triggers at 5 slot times
    │ daily_post.yml  │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Detect Slot     │  <- Handles scheduler delays (2hr windows)
    │ (1-5 based on   │
    │  UTC hour)      │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Download        │
    │ Artifact        │
    └────────┬────────┘
             │
    ┌────────▼─────────────┐
    │ twitter_poster.py    │
    │                      │
    │ 1. load_queue()      │
    │ 2. find_next_content │
    │ 3. validate_before_  │  <- LAST LINE OF DEFENSE
    │    posting()         │
    │ 4. upload_media()    │
    │ 5. post_tweet()      │
    │ 6. save_queue()      │
    └────────┬─────────────┘
             │
    ┌────────▼────────┐
    │ Git Commit      │
    │ & Push          │
    └─────────────────┘
```

### 5.2 Slot Detection Logic

**Location:** `.github/workflows/daily_post.yml` lines 57-90

**Cron Schedule (UTC):**
```yaml
schedule:
  - cron: '0 13 * * *'   # Slot 1: 08:00 ET
  - cron: '0 15 * * *'   # Slot 2: 10:00 ET
  - cron: '30 17 * * *'  # Slot 3: 12:30 ET
  - cron: '30 20 * * *'  # Slot 4: 15:30 ET
  - cron: '0 23 * * *'   # Slot 5: 18:00 ET
```

**Delay-Tolerant Detection (2-hour windows):**
```bash
if [ $HOUR -ge 13 ] && [ $HOUR -lt 15 ]; then
  SLOT=1
elif [ $HOUR -ge 15 ] && [ $HOUR -lt 17 ]; then
  SLOT=2
elif [ $HOUR -ge 17 ] && [ $HOUR -lt 20 ]; then
  SLOT=3
elif [ $HOUR -ge 20 ] && [ $HOUR -lt 23 ]; then
  SLOT=4
elif [ $HOUR -ge 23 ] || [ $HOUR -lt 1 ]; then
  SLOT=5
fi
```

### 5.3 Manual Approval Gates

**Current State:** No manual approval required.

All tweets are:
1. Generated by Claude with strict system prompts
2. Validated at queue time (8 checks)
3. Validated at post time (5 checks)
4. Automatically posted if validations pass

**Blocked tweets (status='blocked'):**
- Remain in queue with `block_reason`
- Not automatically retried
- Require manual review and re-queuing

### 5.4 Rate Limiting Controls

**Thread Posting (twitter_poster.py:503-505):**
```python
if number < len(thread_tweets):
    time.sleep(1)  # 1 second between tweets in thread
```

**Slot-Based Throttling:**
- Only 1 tweet per slot
- 5 slots per day = 5 tweets max
- Minimum 2 hours between posts

---

## 6. API Integration

### 6.1 Authentication

**Location:** `twitter_poster.py` lines 168-202

**Required Environment Variables:**
```bash
X_API_KEY        # Consumer Key (API Key)
X_API_SECRET     # Consumer Secret (API Key Secret)
X_ACCESS_TOKEN   # Access Token
X_ACCESS_SECRET  # Access Token Secret
```

**Client Initialization:**
```python
# v2 Client - For posting tweets
client_v2 = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_secret
)

# v1.1 API - For media upload (v2 doesn't support well)
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
api_v1 = tweepy.API(auth)
```

### 6.2 Error Handling

**Tweet Posting Errors (twitter_poster.py:420-424):**
```python
except tweepy.TweepyException as e:
    print(f"Failed to post: {e}")
    tweet['status'] = 'failed'
    tweet['error'] = str(e)
    return False
```

**Thread Partial Failure (twitter_poster.py:507-511):**
```python
except tweepy.TweepyException as e:
    print(f"Thread failed at tweet {number}: {e}")
    thread_item['thread_status'] = 'partial'
    thread_item['error'] = str(e)
    return False  # Stops thread, doesn't continue
```

**Media Upload Errors (twitter_poster.py:357-359):**
```python
if not path.exists():
    print(f"  ⚠ Image not found: {image_path}")
    return None  # Tweet posts without image (non-blocking)
```

### 6.3 Retry Logic

**Current Implementation:** No custom retry logic.
- Relies on Tweepy's built-in rate limit handling
- Failed tweets marked with `status='failed'`
- No automatic retry on failure
- Requires manual intervention for failed posts

**Gap (TWA-5):** Consider adding exponential backoff for transient failures.

---

## 7. Vocabulary Translation

### 7.1 Banned Terms Dictionary

**Location:** `config.py` lines 301-336

| Category | Banned Terms |
|----------|--------------|
| **Strategy Internals** | HMA, Hull Moving Average, Banker, Banker >=, 20% stop, 20% trailing, Beta >=, BoS, BOS, Break of Structure, Tier 1/2/3, TIER1/2/3, Gatekeeper |
| **Internal Gate Names** | Forensic Audit, 5th Gate, Gate 5, Volatility Expansion Criteria, Structural Pivot Confirmation, Institutional Accumulation Divergence, Capital Preservation Protocol |
| **Non-Branded Signals** | buy signal, PASS signal, proprietary entry, proprietary signal |
| **Region-Specific** | Roth IRA, Roth, 401k, 401(k), PDT, PDT rule, pattern day trader, UK ISA, ISA account, GMT, BST, UK Time |
| **Technical Indicators** | RSI, MACD, KDJ |
| **Misleading Terms** | weekly winners, this week we nailed |

### 7.2 Approved Terms

**Location:** `config.py` lines 343-367

| Category | Approved Terms |
|----------|---------------|
| **Signals** | TEAL signal, TEAL signal fires, triggers a TEAL signal, cleared all 5 gates |
| **System** | 5-Gate System, our scanner, systematic approach |
| **Gates** | Structural Pivot Confirmation, Institutional Accumulation Divergence, Sector Flow Analysis |
| **Risk** | trailing stop, systematic stop, risk management, defined risk |

### 7.3 Auto-Replacement Function

**Location:** `config.py` lines 370-395

```python
def enforce_teal_branding(text: str) -> str:
    replacements = {
        'buy signal': 'TEAL signal',
        'Buy signal': 'TEAL signal',
        'BUY SIGNAL': 'TEAL SIGNAL',
        'proprietary entry': 'TEAL signal',
        'proprietary signal': 'TEAL signal',
        'our signal': 'TEAL signal',
        'new signal': 'TEAL signal',
        'passes our criteria': 'triggers a TEAL signal',
        'cleared our system': 'triggers a TEAL signal',
        'PASS signal': 'TEAL signal',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
```

### 7.4 Where Translation Applied

| Stage | Function | Location |
|-------|----------|----------|
| Tweet Generation | System prompt instructs Claude | tweet_generator.py |
| Queue Validation | `enforce_teal_branding()` called | tweet_generator.py:372-373 |
| Auto-Fix | `validate_and_fix_tweet()` | tweet_generator.py:370-373 |
| Final Check | Banned term check | twitter_poster.py:136-139 |

---

## 8. Example Outputs by Category

### 8.1 buy_signal

```
🎯 TEAL Signal: $NVDA

Our 5-Gate System just triggered on this AI Infrastructure leader.

✅ Cleared all gates
✅ Theme: PRIME (8.2/10)
✅ Conviction: 4/5

Full analysis in this week's Sterling Signals 👇
sterlingsignals.substack.com
```

### 8.2 top_performers

```
📈 TOP PERFORMERS

Our TEAL signals in the green:

$RCAT +55.9% (4 weeks)
$IBKR +22.3% (6 weeks)
$CGON +12.1% (3 weeks)

Returns since entry, not weekly movement.

See all positions 👇
sterlingsignals.substack.com
```

### 8.3 milestone_alerts

```
🚀 HOME RUN: $RCAT

Up +50% since our TEAL signal fired.

Entry: December 2025
Theme: Drone Technology
Held: 4 weeks

This is what the 5-Gate System is designed to find.

Full analysis 👇
sterlingsignals.substack.com
```

### 8.4 beat_spy

```
📊 Sterling Signals vs SPY

Portfolio: +18.2%
SPY: +4.1%
Alpha: +14.1%

Matched holding periods comparison.

Our systematic approach continues to outperform passive indexing.

See how we do it 👇
sterlingsignals.substack.com
```

### 8.5 theme_hot

```
🔥 PRIME Theme: AI Infrastructure

Score: 8.2/10

What's driving it:
• Data center capex explosion
• Hyperscaler earnings guidance
• Power demand surge

Top plays from our scanner:
$NVDA, $AMD, $AVGO

Full theme analysis 👇
sterlingsignals.substack.com
```

### 8.6 power_hour

```
⚡ Power Hour Check (15:30 ET)

Watching our TEAL signals into the close:

$NVDA: Holding gains, relative strength
$RCAT: Momentum building, volume expanding

The final 30 minutes often reveal institutional intent.

Live positions 👇
sterlingsignals.substack.com
```

### 8.7 engagement

```
💬 Question for the community:

What's your biggest challenge with momentum trading?

A) Finding entries
B) Managing stops
C) Sizing positions
D) Taking profits

Drop your answer below 👇
```

### 8.8 educational

```
📚 Trading Lesson #42

Why we use trailing stops:

A 20% gain can become a loss if you don't protect it.

Our systematic approach:
• Trailing stop from highest close
• No ego, just execution
• Let winners run, cut losers

More lessons 👇
sterlingsignals.substack.com
```

---

## 9. Complete Validation Checklist

### 9.1 Queue-Time Validation (8 Checks)

**Function:** `validate_tweet_before_queue()`
**Location:** `tweet_generator.py` lines 232-346

| Check | Regex/Logic | Error Message |
|-------|-------------|---------------|
| 1. Killed category | `category in KILLED_CATEGORIES` | KILLED CATEGORY |
| 2. Tweet length | `char_count > 280` | TOO LONG |
| 3. Banned terms | Word boundary for short terms | BANNED TERM |
| 4. Negative P&L | `-\d+\.?\d*%` | LOSER SHOWN |
| 5. TEAL branding | Signal tweets need "TEAL" | MISSING BRANDING |
| 6. Holding period | P&L needs timeframe context | MISSING HOLDING PERIOD |
| 7. US-specific | roth, 401k, pdt patterns | US-SPECIFIC |
| 8. Ticker frequency | Max 4 mentions per week | TICKER OVEREXPOSED |

### 9.2 Post-Time Validation (5 Checks)

**Function:** `validate_before_posting()`
**Location:** `twitter_poster.py` lines 95-161

| Check | Regex/Logic | Error Message |
|-------|-------------|---------------|
| 1. Negative P&L | `-\d+\.?\d*%` | BLOCKED: Negative P&L |
| 2. Banned terms | Case-insensitive contains | BLOCKED: Banned term |
| 3. Killed category | `category in KILLED_CATEGORIES` | BLOCKED: Killed category |
| 4. US-specific | Regex patterns | BLOCKED: US-specific |
| 5. Tweet length | Emoji-aware count > 280 | BLOCKED: Too long |

---

## 10. Issues Summary

| ID | Severity | Description | Recommendation |
|----|----------|-------------|----------------|
| TWA-1 | INFO | Two-layer validation provides strong protection | None needed |
| TWA-2 | INFO | Negative P&L regex is comprehensive | None needed |
| TWA-3 | LOW | EDT/EST shift during DST | Document for users |
| TWA-4 | LOW | Thread partial failure stops entire thread | Add resume capability |
| TWA-5 | INFO | No exponential backoff retry | Consider adding |

---

## Appendix A: Status Values

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `pending` | Ready to post, waiting for slot | Automatic posting |
| `posted` | Successfully posted | None (complete) |
| `failed` | API error during posting | Manual retry |
| `blocked` | Validation failed | Review and re-queue |
| `skipped` | Duplicate or manual skip | None |
| `partial` | Thread partially posted | Manual completion |

---

## Appendix B: File Reference

| File | Purpose |
|------|---------|
| `tweet_generator.py` | Generate 25 weekly tweets |
| `twitter_poster.py` | Post tweets via X API |
| `signal_tracker.py` | Safeguard functions |
| `config.py` | Constants, thresholds, schedules |
| `.github/workflows/friday_scan.yml` | Friday generation workflow |
| `.github/workflows/daily_post.yml` | Daily posting workflow |
| `trades/content_queue.json` | Tweet queue with status |
| `trades/celebrations.json` | Milestone tracking |

---

*Document generated: 2026-01-27*
*Audit scope: X/Twitter automation, safeguards, vocabulary translation*
