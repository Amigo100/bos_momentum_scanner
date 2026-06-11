# Sterling Signals - Verification Issues Fix TODO

## Overview

This document addresses issues identified during verification of the marketing system overhaul. These fixes should be applied AFTER the main implementation from `TODO.md` is complete.

**Priority Levels:**
- 🔴 CRITICAL - Must fix before deployment
- 🟡 MODERATE - Fix before go-live
- 🟢 MINOR - Fix when convenient

---

## 🔴 CRITICAL FIXES

### CRIT-1: Signal Classification Terminology Alignment

**Problem:** Inconsistent terminology between portfolio.csv (`TRADE`, `CONSIDER`) and config.py (`PASS`, `CONSIDER`, `WATCHLIST`).

**Files to Update:**
- `config.py`
- `scanner.py`
- `portfolio.csv` schema
- `tweet_generator.py`
- `newsletter_compiler.py`

**Action:**
```python
# Standardize on these terms EVERYWHERE:

SIGNAL_TYPES = {
    'PASS': 'Cleared all 5 gates - full TEAL signal (public: "TEAL Signal")',
    'CONSIDER': 'Cleared gates 1-4, watching gate 5 (public: "On Our Radar")',
    'WATCHLIST': 'Strong technicals, theme pending (internal only)',
    'CAUTION': 'Open position weakening (internal only)',
    'EXIT': 'Stop triggered or thesis broken (internal only)',
}

# In portfolio.csv, column should be 'signal_type' with values:
# PASS, CONSIDER, WATCHLIST (not TRADE)

# BANNED terms in code:
# - 'TRADE' as signal type (use 'PASS')
# - 'final_decision: TRADE' in signals.json (use 'final_decision: PASS')
```

**Verification:**
- [ ] `grep -r "TRADE" *.py` returns 0 matches for signal classification
- [ ] All portfolio.csv entries use PASS/CONSIDER/WATCHLIST
- [ ] signals.json uses `final_decision: "PASS"` not `"TRADE"`

---

### CRIT-2: Separate CONSIDER from CAUTION Signals

**Problem:** signals.json conflates two different concepts:
- `consider_signals`: Stocks that passed gates 1-4, BULLISH watchlist
- `caution_signals`: Reasons to avoid/wait, BEARISH or neutral

**Files to Update:**
- `scanner.py`
- `signals.json` schema
- `tweet_generator.py`

**Action:**
```python
# Update signals.json structure to have BOTH:

{
    "buy_signals": [...],           # PASS - cleared all 5 gates
    
    "consider_signals": [           # NEW - passed gates 1-4, watching gate 5
        {
            "symbol": "APLD",
            "price": 12.50,
            "gates_passed": [1, 2, 3, 4],
            "gate_5_blocker": "Extended price, wait for pullback to HMA",
            "theme": "AI Infrastructure",
            "theme_score": 7.8,
            "conviction_if_clears": 4,
            "watch_for": "Price pullback to $10.50 area"
        }
    ],
    
    "caution_signals": [            # RENAMED/CLARIFIED - open positions with issues
        {
            "symbol": "SMCI",
            "status": "OPEN_POSITION",
            "issue": "Below entry, thesis weakening",
            "action": "Monitor stop level"
        }
    ],
    
    "avoid_themes": [               # NEW - themes to stay away from
        {
            "theme": "Regional Banks",
            "score": 3.1,
            "reason": "CRE exposure, rate uncertainty"
        }
    ]
}
```

**Verification:**
- [ ] `consider_signals` contains BULLISH watchlist items only
- [ ] `caution_signals` contains BEARISH/warning items only
- [ ] No overlap between the two arrays
- [ ] `consider_spotlight` tweets pull from `consider_signals` only

---

### CRIT-3: Stopped Position Public Handling

**Problem:** Document says to "mention discipline" for stopped positions, but this draws attention to losses.

**Files to Update:**
- `config.py`
- `tweet_generator.py`
- `newsletter_compiler.py`

**Action:**
```python
# Add explicit rule to config.py:

STOPPED_POSITION_RULES = {
    'show_in_public_content': False,      # NEVER show stopped positions
    'show_in_newsletter': False,          # NEVER show in newsletter
    'show_in_weekly_wins': False,         # NEVER include
    'show_in_any_tweet': False,           # NEVER tweet about
    'internal_tracking': True,            # Continue tracking for metrics
    'mention_discipline_publicly': False, # DO NOT mention "system working" with losses
}

# The system's effectiveness is demonstrated by WIN RATE, not by showcasing stops.
# Stopped positions simply don't exist in public view.
```

**Verification:**
- [ ] Search all generated tweets for stopped ticker symbols - should find 0
- [ ] Newsletter never mentions stopped positions
- [ ] No "discipline" or "stop working" language with specific tickers

---

### CRIT-4: SPY Comparison Methodology

**Problem:** Comparing RCAT +67% (held 6 weeks) to "this week's SPY +1.2%" is misleading.

**Files to Update:**
- `config.py`
- `tweet_generator.py`
- `social_graphics.py`

**Action:**
```python
# Add to config.py:

SPY_COMPARISON_METHOD = 'matched_period'  # Options: 'matched_period', 'weekly_only', 'ytd'

# matched_period: Compare each position's return to SPY return over SAME holding period
# weekly_only: Compare only this week's price movement for all positions
# ytd: Compare YTD returns (only valid after Jan)

def calculate_fair_spy_comparison(positions: list) -> dict:
    """
    Calculate SPY comparison using matched holding periods.
    
    For each position:
    1. Get position entry_date and current P&L
    2. Get SPY return from entry_date to today
    3. Calculate alpha = position_return - spy_return
    
    Aggregate:
    - weighted_alpha = sum(position_alpha * position_weight) / total_weight
    - Only report if weighted_alpha > SPY_OUTPERFORMANCE_MIN
    """
    import yfinance as yf
    
    spy = yf.Ticker("SPY")
    results = []
    
    for pos in positions:
        entry_date = pos['entry_date']
        pos_return = pos['pnl_pct']
        
        # Get SPY return over same period
        spy_hist = spy.history(start=entry_date)
        spy_return = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1) * 100
        
        alpha = pos_return - spy_return
        results.append({
            'ticker': pos['ticker'],
            'pos_return': pos_return,
            'spy_return': spy_return,
            'alpha': alpha,
            'days_held': (datetime.now() - datetime.strptime(entry_date, '%Y-%m-%d')).days
        })
    
    # Aggregate (equal weight for simplicity)
    avg_pos_return = sum(r['pos_return'] for r in results) / len(results)
    avg_spy_return = sum(r['spy_return'] for r in results) / len(results)
    avg_alpha = avg_pos_return - avg_spy_return
    
    return {
        'portfolio_return': avg_pos_return,
        'spy_return': avg_spy_return,
        'alpha': avg_alpha,
        'comparison_note': f"Returns compared over matched holding periods (avg {sum(r['days_held'] for r in results) // len(results)} days)"
    }
```

**Verification:**
- [ ] beat_spy tweets show matched-period comparison
- [ ] Comparison note explains methodology
- [ ] No misleading "this week" vs "all time" comparisons

---

## 🟡 MODERATE FIXES

### MOD-1: Fix Tweet Count (35 → 25)

**Problem:** Verification doc says "35-Tweet Schedule" but actual schedule has ~25.

**Files to Update:**
- `VERIFICATION_OUTPUTS.md`
- `tweet_generator.py` comments

**Action:**
- Update all references from 35 to 25 tweets
- Verify WEEKLY_SCHEDULE produces exactly 25 tweets

**Verification:**
```python
total_tweets = sum(len(slots) for slots in WEEKLY_SCHEDULE.values())
assert total_tweets == 25, f"Expected 25, got {total_tweets}"
```

---

### MOD-2: Remove or Document ROTH_IRA Category

**Problem:** TODO.md says kill `roth_ira` but it still appears in schedule.

**Files to Update:**
- `tweet_generator.py`
- `config.py`

**Action - Option A (Remove):**
```python
# Remove roth_ira from WEEKLY_SCHEDULE
# Tuesday Slot 1 becomes theme_hot or beat_spy
```

**Action - Option B (Keep as Occasional):**
```python
# Document in config.py:
OCCASIONAL_CATEGORIES = {
    'roth_ira': {
        'frequency': 'weekly',  # Max once per week
        'days': ['Tuesday'],    # Only on Tuesdays
        'fallback': 'theme_hot'
    },
    'pdt_friendly': {
        'frequency': 'weekly',
        'days': ['Wednesday'],
        'fallback': 'engagement'
    }
}
```

**Verification:**
- [ ] Either roth_ira removed from schedule OR documented as occasional

---

### MOD-3: Add Full Schedules for Scenarios B and C

**Problem:** Can't verify fallback behavior without complete schedules.

**Files to Update:**
- `VERIFICATION_OUTPUTS.md`

**Action:**
Add complete Saturday-Sunday-Monday schedules for:
- Scenario B (bad week): Show which slots get fallback content
- Scenario C (terrible week): Show full week of non-position content

**Template for Scenario B:**
```markdown
### Saturday (Bad Week)
| Slot | Category | Safeguard | Result | Content |
|------|----------|-----------|--------|---------|
| 1 | weekly_wins | has_enough_wins() | ❌ FAIL (1 winner) | FALLBACK: theme_hot |
| 2 | thread_buy_signal | has_pass_signals() | ✅ PASS | Normal thread |
| 3 | theme_hot | — | ✅ PASS | Normal content |
| ... | ... | ... | ... | ... |

### Sunday (Bad Week)
| Slot | Category | Safeguard | Result | Content |
|------|----------|-----------|--------|---------|
| 3 | beat_spy | should_post_beat_spy() | ❌ FAIL (-2.5% alpha) | FALLBACK: engagement |
| ... | ... | ... | ... | ... |
```

---

### MOD-4: Add Celebration Tracking Example

**Problem:** No example showing celebrations.json state changes.

**Files to Update:**
- `VERIFICATION_OUTPUTS.md`
- Create `celebrations.json` schema

**Action:**
```json
// celebrations.json BEFORE this week's scan:
{
  "RCAT": {
    "25_pct": "2026-01-10",
    "50_pct": "2026-01-18",
    "100_pct": null
  },
  "OKLO": {
    "25_pct": "2025-12-01",
    "50_pct": null,
    "100_pct": null
  },
  "INOD": {
    "25_pct": null,
    "50_pct": null,
    "100_pct": null
  }
}

// This week: OKLO closed at +52%, INOD hit +22%

// celebrations.json AFTER this week's scan:
{
  "RCAT": {
    "25_pct": "2026-01-10",
    "50_pct": "2026-01-18",
    "100_pct": null
  },
  "OKLO": {
    "25_pct": "2025-12-01",
    "50_pct": "2026-01-25",  // NEW - triggers self_quote
    "100_pct": null
  },
  "INOD": {
    "25_pct": "2026-01-25",  // NEW - triggers self_quote (if 25%+ not 22%)
    "50_pct": null,
    "100_pct": null
  }
}

// INOD at +22% does NOT trigger celebration (below 25% threshold)
// OKLO at +52% triggers 50% celebration (25% was already celebrated)
```

**Verification:**
- [ ] celebrations.json updates correctly
- [ ] Only NEW threshold crossings generate tweets
- [ ] Closed positions still get tracked

---

### MOD-5: Add Missing Test Cases

**Problem:** Several edge cases not tested in verification doc.

**Files to Create:**
- `tests/test_edge_cases.py`

**Test Cases to Add:**

```python
def test_position_at_exactly_threshold():
    """Position at exactly 15.00% should be included (>=, not >)."""
    position = {'ticker': 'TEST', 'pnl_pct': 15.0}
    assert should_highlight_position(position['pnl_pct']) == True

def test_multiple_big_wins_same_week():
    """Multiple tickers crossing 50% in same week."""
    big_wins = [
        {'ticker': 'RCAT', 'pnl_pct': 67.0, 'crossed_50': '2026-01-25'},
        {'ticker': 'OKLO', 'pnl_pct': 52.0, 'crossed_50': '2026-01-25'},
    ]
    tweets = generate_self_quotes(big_wins)
    # Should generate 2 separate tweets, not combine
    assert len(tweets) == 2
    # Order by P&L descending (biggest win first)
    assert tweets[0]['ticker'] == 'RCAT'

def test_same_ticker_multiple_thresholds_same_week():
    """Ticker crosses both 50% and 100% in same week."""
    # RCAT was at 45% last week, now at 105%
    crossings = detect_threshold_crossings('RCAT', previous_pnl=45.0, current_pnl=105.0)
    # Should detect BOTH 50% and 100% crossings
    assert crossings == ['50_pct', '100_pct']
    # Should generate 2 tweets (one for each milestone)
    tweets = generate_self_quotes_for_ticker('RCAT', crossings)
    assert len(tweets) == 2

def test_duplicate_ticker_in_signals():
    """Ticker appears in both buy_signals and consider_signals."""
    signals = {
        'buy_signals': [{'symbol': 'ASPI', 'final_decision': 'PASS'}],
        'consider_signals': [{'symbol': 'ASPI', 'gate_5_blocker': 'old data'}]
    }
    # PASS takes precedence - remove from consider
    cleaned = deduplicate_signals(signals)
    assert 'ASPI' not in [s['symbol'] for s in cleaned['consider_signals']]
    assert 'ASPI' in [s['symbol'] for s in cleaned['buy_signals']]

def test_yfinance_api_failure():
    """Graceful handling when price fetch fails."""
    with mock.patch('yfinance.download', side_effect=Exception("API Error")):
        result = fetch_current_prices(['ASPI', 'CGON'])
        # Should return empty dict, not crash
        assert result == {}
        # Tweets should skip price-dependent content
        tweets = generate_weekly_wins(content_with_no_prices)
        assert tweets is None or 'price' not in tweets[0]['text'].lower()

def test_empty_portfolio():
    """First week scenario - no positions yet."""
    portfolio = []
    tweets = generate_all_tweets(portfolio, signals)
    # Should still generate theme/engagement content
    assert len(tweets) > 0
    # No position-related tweets
    position_tweets = [t for t in tweets if t['category'] in ['weekly_wins', 'self_quote', 'beat_spy']]
    assert len(position_tweets) == 0 or all(t['text'] is None for t in position_tweets)

def test_all_positions_are_losers():
    """Every open position is underwater."""
    portfolio = [
        {'ticker': 'SMCI', 'pnl_pct': -8.3},
        {'ticker': 'IONQ', 'pnl_pct': -14.0},
        {'ticker': 'RIVN', 'pnl_pct': -20.0},
    ]
    public_positions = filter_public_positions(portfolio)
    # Should return empty list
    assert len(public_positions) == 0
    # weekly_wins should be skipped
    assert should_post_weekly_wins(portfolio) == False
    # beat_spy should be skipped
    assert should_post_beat_spy(portfolio) == False
```

---

## 🟢 MINOR FIXES

### MIN-1: Tweet Character Count Validation

**Problem:** Some sample tweets may exceed 280 characters.

**Files to Update:**
- `tweet_generator.py`

**Action:**
```python
def validate_tweet_length(tweet_text: str) -> bool:
    """Validate tweet is under 280 characters."""
    # Note: Emojis count as 2 characters on Twitter
    char_count = 0
    for char in tweet_text:
        if ord(char) > 0xFFFF:  # Emoji or special char
            char_count += 2
        else:
            char_count += 1
    return char_count <= 280

def truncate_tweet(tweet_text: str, max_length: int = 275) -> str:
    """Truncate tweet to fit, preserving URL at end."""
    # Implementation
    pass

# Add validation to generate_tweet():
tweet_text = generate_tweet_content(...)
if not validate_tweet_length(tweet_text):
    logger.warning(f"Tweet exceeds 280 chars: {len(tweet_text)}")
    tweet_text = truncate_tweet(tweet_text)
```

**Verification:**
- [ ] All generated tweets pass `validate_tweet_length()`
- [ ] Add character count to tweet output for debugging

---

### MIN-2: Standardize Image Filename Format

**Problem:** Inconsistent date suffixes on image files.

**Files to Update:**
- `social_graphics.py`
- `chart_capture.py`

**Action:**
```python
# Standardize ALL image filenames to:
# {type}_{YYYYMMDD}.png

IMAGE_FILENAME_PATTERNS = {
    'weekly_wins': 'weekly_wins_{date}.png',
    'beat_spy': 'beat_spy_{date}.png',
    'funnel': 'funnel_{date}.png',
    'theme_card': 'theme_card_{THEME}_{date}.png',
    'big_win': 'big_win_{TICKER}_{date}.png',
    'consider': 'consider_spotlight_{date}.png',
    'chart': '{TICKER}_{date}.png',
    'chart_substack': '{TICKER}_{date}_substack.png',
}

def get_image_filename(image_type: str, date: datetime, **kwargs) -> str:
    """Generate standardized image filename."""
    date_str = date.strftime('%Y%m%d')
    pattern = IMAGE_FILENAME_PATTERNS[image_type]
    return pattern.format(date=date_str, **kwargs)
```

---

### MIN-3: Remove/Define "GAP 38" Reference

**Problem:** Line 769 mentions "GAP 38" which is undefined.

**Files to Update:**
- `VERIFICATION_OUTPUTS.md`

**Action:**
Either:
- Define GAP 38 in the document
- Remove the reference entirely

```markdown
# If defining:
**GAP 38: Cold Streak Circuit Breaker**
When 3+ consecutive positions hit stops, reduce position-related content frequency by 50% for 2 weeks. This prevents showcasing a bad run while maintaining engagement through theme/educational content.

# If removing:
- Change line 769 to: "Cold streak enforcement works - system reduces position content during losing streaks"
```

---

### MIN-4: Thread Tweet Character Validation

**Problem:** Thread tweets (5 parts) not individually validated for length.

**Files to Update:**
- `tweet_generator.py`

**Action:**
```python
def generate_thread(topic: str, content: dict) -> list[dict]:
    """Generate 5-tweet thread."""
    tweets = []
    for i in range(1, 6):
        tweet_text = generate_thread_tweet(i, topic, content)
        
        # Validate each tweet individually
        if not validate_tweet_length(tweet_text):
            logger.warning(f"Thread tweet {i}/5 exceeds 280 chars")
            tweet_text = truncate_tweet(tweet_text)
        
        tweets.append({
            'number': i,
            'text': tweet_text,
            'char_count': len(tweet_text)  # For debugging
        })
    
    return tweets
```

---

## IMPLEMENTATION ORDER

1. **CRIT-1** - Signal terminology (affects all files)
2. **CRIT-2** - CONSIDER vs CAUTION separation
3. **CRIT-3** - Stopped position rules
4. **CRIT-4** - SPY comparison methodology
5. **MOD-1** - Tweet count fix
6. **MOD-2** - ROTH_IRA decision
7. **MOD-4** - Celebration tracking
8. **MOD-5** - Edge case tests
9. **MOD-3** - Scenario B/C schedules
10. **MIN-1 to MIN-4** - Cleanup items

---

## VERIFICATION CHECKLIST

After implementing all fixes, verify:

```bash
# 1. No TRADE signal type in codebase
grep -r "TRADE" *.py | grep -v "# TRADE" | grep signal

# 2. No stopped positions in public content
python -c "from tweet_generator import generate_all_tweets; print([t for t in generate_all_tweets() if 'RIVN' in t.get('text', '')])"

# 3. SPY comparison uses matched periods
python -c "from tweet_generator import calculate_fair_spy_comparison; print(calculate_fair_spy_comparison(test_positions))"

# 4. All tweets under 280 chars
python -c "from tweet_generator import generate_all_tweets, validate_tweet_length; tweets = generate_all_tweets(); print([t for t in tweets if not validate_tweet_length(t['text'])])"

# 5. Celebration tracking works
python -c "from signal_tracker import detect_threshold_crossings; print(detect_threshold_crossings('TEST', 45.0, 105.0))"
```

---

## FILES MODIFIED BY THIS TODO

| File | Changes |
|------|---------|
| `config.py` | Signal types, SPY comparison method, stopped position rules |
| `scanner.py` | CONSIDER vs CAUTION separation, signal terminology |
| `tweet_generator.py` | Character validation, fallback content, terminology |
| `signal_tracker.py` | Celebration tracking, threshold detection |
| `social_graphics.py` | Filename standardization |
| `newsletter_compiler.py` | Remove stopped positions |
| `VERIFICATION_OUTPUTS.md` | Fix count, add scenarios, add examples |
| `tests/test_edge_cases.py` | New test file |
| `celebrations.json` | New tracking file |

---

## SUCCESS CRITERIA

- [ ] Zero mentions of losing positions in any public output
- [ ] SPY comparisons use fair matched-period methodology
- [ ] CONSIDER signals are clearly bullish watchlist (not warnings)
- [ ] All tweets validate under 280 characters
- [ ] Celebration tracking prevents duplicate posts
- [ ] Edge cases handled gracefully (API failures, empty data)
- [ ] Full scenario schedules demonstrate fallback behavior
