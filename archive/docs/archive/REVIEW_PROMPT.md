# Sterling Signals - Implementation Review Prompt

**Version:** 2.0
**Purpose:** Audit implementation for gaps, edge cases, and potential issues before deployment

---

# INSTRUCTIONS FOR CLAUDE CODE

After implementing changes from `MASTER_TODO.md` and generating verification outputs, run this review to catch anything missed.

Systematically check each area below and report any issues found.

---

# 1. SAFEGUARD COMPLETENESS AUDIT

## 1.1 Loser Exposure Check

Trace ALL code paths that could expose position data:

```python
# Check every function that outputs position information
functions_to_audit = [
    'generate_top_performers()',
    'generate_early_movers()',
    'generate_milestone_alerts()',
    'generate_beat_spy()',
    'generate_recent_wins()',
    'compile_newsletter()',
    'generate_substack_notes()',
]

# For each function, verify:
# 1. Calls filter_public_positions() BEFORE any output
# 2. Never accesses positions directly without filtering
# 3. Cannot bypass filter through alternate code path
```

**Questions to Answer:**
- [ ] Can a losing position EVER appear in a tweet?
- [ ] Can a losing position EVER appear in the newsletter?
- [ ] Can a stopped position EVER be mentioned?
- [ ] Are there any code paths that bypass `filter_public_positions()`?
- [ ] What happens if `filter_public_positions()` itself has a bug?

## 1.2 SPY Comparison Integrity

Verify matched-period calculation:

```python
# Check calculate_spy_comparison() logic:
# 1. For each position, fetches SPY from entry_date to today
# 2. Calculates alpha per position
# 3. Averages correctly (equal weight or weighted?)
# 4. Returns valid=False if any fetch fails
```

**Questions to Answer:**
- [ ] Is the comparison truly apples-to-apples?
- [ ] What if SPY data fetch fails for one position?
- [ ] What if entry_date is a weekend/holiday?
- [ ] Is the average weighted by position size or equal?

## 1.3 Threshold Edge Cases

```python
# Test boundary conditions:
test_cases = [
    ('exactly_15_pct', 15.0, True),    # Should include
    ('just_below_15', 14.99, False),   # Should exclude
    ('exactly_0_pct', 0.0, False),     # Should exclude (not positive)
    ('tiny_positive', 0.01, True),     # Should include (for public)
    ('exactly_25_pct', 25.0, True),    # Should trigger milestone
    ('just_below_25', 24.99, False),   # Should not trigger milestone
]
```

**Questions to Answer:**
- [ ] Are comparisons using `>=` or `>`?
- [ ] Is 0% considered a "loser" or neutral?
- [ ] Document exact boundary behavior

---

# 2. EDGE CASE ANALYSIS

## 2.1 Data Availability

| Scenario | Expected Behavior | Verify |
|----------|-------------------|--------|
| yfinance API timeout | Skip affected positions, continue with others | [ ] |
| yfinance returns None | Skip that position | [ ] |
| portfolio.csv empty | Generate theme/engagement content only | [ ] |
| portfolio.csv missing | Error gracefully, don't crash | [ ] |
| signals.json empty | Show "no signals this week" | [ ] |
| signals.json missing | Error gracefully | [ ] |
| celebrations.json missing | Create new empty file | [ ] |

## 2.2 Position Edge Cases

| Scenario | Expected Behavior | Verify |
|----------|-------------------|--------|
| Ticker delisted | Remove from tracking, skip in output | [ ] |
| Stock split occurred | Entry price should be adjusted | [ ] |
| Ticker changed (e.g., FB→META) | Handle mapping | [ ] |
| Position exactly at entry price (0%) | Exclude from public | [ ] |
| Position just opened today | Include if positive, use "1 day" not "0 weeks" | [ ] |
| Very old position (>1 year) | Show "52+ weeks" or actual count | [ ] |

## 2.3 Multiple Event Edge Cases

| Scenario | Expected Behavior | Verify |
|----------|-------------------|--------|
| Multiple big wins same week | Generate multiple milestone tweets | [ ] |
| Same ticker crosses 25% and 50% same week | Generate both celebrations | [ ] |
| 10 PASS signals in one week | Show all 10, not limited | [ ] |
| 0 PASS but 10 CONSIDER | Show CONSIDER content | [ ] |
| All themes are AVOID | Show "rotating to cash" message | [ ] |

## 2.4 Content Edge Cases

| Scenario | Expected Behavior | Verify |
|----------|-------------------|--------|
| Tweet would exceed 280 chars | Truncate or split | [ ] |
| No image generated | Post text-only | [ ] |
| Thread tweet 3 exceeds limit | Truncate that tweet | [ ] |
| Same content for 2 slots | Vary the content | [ ] |

---

# 3. DATA FLOW VERIFICATION

## 3.1 Scanner → Tweet Generator

```
signals.json structure must match expected format:

Required fields in pass_signals[]:
- symbol (string)
- price (float)
- signal_type (string: "PASS")
- theme (string)
- conviction (int: 1-5)
- gates_passed (array: [1,2,3,4,5])
- catalyst (string)
- thesis (string)

Required fields in consider_signals[]:
- symbol (string)
- signal_type (string: "CONSIDER")
- gates_passed (array: [1,2,3,4])
- gate_5_blocker (string)
- watch_for (string)
```

**Verify:**
- [ ] All required fields present
- [ ] No `TRADE` signal_type (only `PASS`, `CONSIDER`)
- [ ] gates_passed is array, not comma-separated string

## 3.2 Portfolio.csv → Signal Tracker

```
Required columns:
- ticker
- status (OPEN, CLOSED, STOPPED)
- entry_date (YYYY-MM-DD)
- entry_price (float)
- exit_date (YYYY-MM-DD or empty)
- exit_price (float or empty)
- theme
- signal_type (PASS, CONSIDER)
- conviction (1-5)
```

**Verify:**
- [ ] Date parsing handles all formats
- [ ] Empty exit_date/exit_price handled for OPEN positions
- [ ] status values are exactly OPEN/CLOSED/STOPPED

## 3.3 Signal Tracker → Celebrations.json

```
Structure:
{
  "TICKER": {
    "25_pct": "YYYY-MM-DD" or null,
    "50_pct": "YYYY-MM-DD" or null,
    "100_pct": "YYYY-MM-DD" or null
  }
}
```

**Verify:**
- [ ] New tickers added automatically
- [ ] Dates stored correctly
- [ ] File saved after updates
- [ ] Handles concurrent access (if applicable)

---

# 4. BRANDING CONSISTENCY CHECK

## 4.1 Terminology Audit

Search ALL output files for banned terms:

```bash
# Run these checks:
grep -r "weekly_wins" *.py *.json *.html *.md
grep -r "PASS signal" *.py *.json *.html *.md
grep -r "\"TRADE\"" *.py *.json
grep -r "this week we nailed" *.py
grep -r "weekly winners" *.py
grep -r "HMA Pivot" *.py  # Internal term
grep -r "Banker indicator" *.py  # Internal term
grep -r "UK ISA" *.py  # Wrong audience
```

**Expected:** All return 0 matches

## 4.2 Approved Terminology Usage

Verify these terms ARE used:

```bash
grep -r "TEAL signal" *.py  # Should find matches
grep -r "5-Gate System" *.py  # Should find matches
grep -r "Structural Pivot" *.py  # Approved public term
grep -r "Institutional Accumulation" *.py  # Approved public term
```

## 4.3 Color Reference Check

```bash
# Should use TEAL/VIOLET, not blue/pink (competitor terminology)
grep -r "blue" *.py | grep -v "# blue" | grep -v ".blue"
grep -r "pink" *.py
```

---

# 5. PRIVATE VS PUBLIC DATA SEPARATION

## 5.1 What Must Stay Private

| Data | Private | Public | Verify |
|------|---------|--------|--------|
| portfolio.csv (full) | ✅ | ❌ | [ ] |
| Entry prices for OPEN positions | ✅ | ❌ | [ ] |
| Stop loss levels | ✅ | ❌ | [ ] |
| Losing position tickers | ✅ | ❌ | [ ] |
| Stopped position details | ✅ | ❌ | [ ] |
| Internal win rate metrics | ✅ | ❌ | [ ] |
| Exact position sizes | ✅ | ❌ | [ ] |

## 5.2 What Can Be Public

| Data | Private | Public | Verify |
|------|---------|--------|--------|
| Winning position tickers | ✅ | ✅ | [ ] |
| Winning position % return | ❌ | ✅ | [ ] |
| Holding period for winners | ❌ | ✅ | [ ] |
| Closed winner entry/exit | ❌ | ✅ | [ ] |
| Theme rankings | ❌ | ✅ | [ ] |
| Scanner statistics | ❌ | ✅ | [ ] |

## 5.3 Newsletter Audit

```
Check newsletter HTML for leakage:

- [ ] No <table> or section labeled "Portfolio"
- [ ] No entry prices for open positions
- [ ] No individual P&L rows for open positions
- [ ] No stop loss levels mentioned
- [ ] No ticker appears that is currently losing
```

---

# 6. MISSING FEATURES CHECK

## 6.1 Should We Add These?

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Cold streak circuit breaker | Medium | Reduce position content if 3+ consecutive stops |
| CONSIDER signal expiry | Low | Remove from watchlist after X weeks |
| Big win cooldown | Medium | Don't spam same ticker multiple days |
| Max tweets per ticker per week | Medium | Prevent overexposure to single name |
| Stock split detection | Low | Auto-adjust entry prices |
| Ticker change handling | Low | Map old→new symbols |

## 6.2 Recommended Additions

**Cold Streak Circuit Breaker:**
```python
def check_cold_streak(portfolio: pd.DataFrame) -> bool:
    """Return True if we should reduce position content."""
    recent_closes = portfolio[
        (portfolio['status'].isin(['CLOSED', 'STOPPED'])) &
        (pd.to_datetime(portfolio['exit_date']) >= datetime.now() - timedelta(days=30))
    ].sort_values('exit_date', ascending=False)
    
    # Check last 3 closes
    if len(recent_closes) >= 3:
        last_3 = recent_closes.head(3)
        losses = (last_3['exit_price'] < last_3['entry_price']).sum()
        if losses >= 3:
            return True  # Cold streak active
    
    return False
```

**Ticker Frequency Limiter:**
```python
def get_ticker_mentions_this_week(ticker: str, queue: list) -> int:
    """Count how many times ticker mentioned in current queue."""
    count = 0
    for tweet in queue:
        if ticker in tweet.get('text', ''):
            count += 1
    return count

MAX_TICKER_MENTIONS_PER_WEEK = 5
```

---

# 7. CONTENT QUALITY CHECK

## 7.1 Tweet Quality

For each generated tweet, verify:

- [ ] Under 280 characters (including emoji as 2)
- [ ] Has clear CTA (link or question)
- [ ] No orphaned numbers (e.g., "+67" without context)
- [ ] Holding period included for any P&L
- [ ] No duplicate content in same week
- [ ] Threads numbered correctly (1/5, 2/5, etc.)

## 7.2 Graphics Quality

For each generated graphic:

- [ ] Correct dimensions for X/Twitter (1200x675 or 1080x1080)
- [ ] Text is readable (not too small)
- [ ] Colors match TEAL/VIOLET branding
- [ ] Disclaimer present on P&L graphics
- [ ] Holding periods shown

## 7.3 Newsletter Quality

- [ ] Mobile responsive
- [ ] Links work
- [ ] Images load
- [ ] Disclaimer in footer
- [ ] Sections flow logically
- [ ] Empty sections hidden (not shown with "None")

---

# 8. AUTOMATION RELIABILITY

## 8.1 Workflow Robustness

| Scenario | Expected Behavior | Verify |
|----------|-------------------|--------|
| GitHub Actions times out mid-run | Partial content saved, can retry | [ ] |
| Re-run same day | Idempotent - doesn't duplicate posts | [ ] |
| Twitter API rate limit | Retry with backoff | [ ] |
| Twitter API auth failure | Alert, don't crash | [ ] |
| Image upload fails | Post text-only, log warning | [ ] |

## 8.2 Idempotency Check

```python
# Running tweet_generator.py twice should:
# 1. Not duplicate tweets in queue
# 2. Not re-celebrate already-celebrated milestones
# 3. Overwrite content_queue.json cleanly

# Running twitter_poster.py twice in same slot should:
# 1. Check if tweet already posted
# 2. Skip if already posted
# 3. Update status correctly
```

## 8.3 Logging Requirements

Verify logging exists for:

- [ ] Scanner start/end with ticker count
- [ ] Each safeguard check result
- [ ] Each fallback triggered
- [ ] Tweet generation success/failure
- [ ] Image generation success/failure
- [ ] Twitter API responses
- [ ] Errors with stack traces

---

# 9. LEGAL/COMPLIANCE CHECK

## 9.1 Required Disclaimers

| Location | Disclaimer Required | Present |
|----------|---------------------|---------|
| Newsletter footer | "Not financial advice..." | [ ] |
| Substack notes | "Not financial advice..." | [ ] |
| Beat SPY graphics | "Past performance..." | [ ] |
| Milestone graphics | "Not a recommendation..." | [ ] |

## 9.2 Language Compliance

Verify NO tweets contain:

- [ ] "Buy this stock" (without disclaimer)
- [ ] "Guaranteed returns"
- [ ] "Can't lose"
- [ ] "100% win rate"
- [ ] "Get rich quick"
- [ ] Specific price targets as promises

## 9.3 Approved Language

Verify tweets use:

- [ ] "Our scanner identified..."
- [ ] "TEAL signal fired..."
- [ ] "Targeting X-Y% over Z months"
- [ ] "Past performance shown..."
- [ ] "Not financial advice"

---

# 10. COMPETITOR FEATURE PARITY

## 10.1 Feature Comparison

| Feature | Competitors | Sterling Signals | Status |
|---------|-------------|------------------|--------|
| Weekly win showcase | ✅ | `top_performers` | [ ] Verify |
| Self-quoting past calls | ✅ | `milestone_alerts` | [ ] Verify |
| Price-anchored watchlists | ✅ | `consider_spotlight` | [ ] Verify |
| Theme spotlights | ✅ | `theme_hot` | [ ] Verify |
| Engagement polls | ✅ | `engagement` | [ ] Verify |
| Follower testimonials | ✅ | Not implemented | [ ] Consider |
| "Chart every ticker" | ✅ | Not implemented | [ ] Consider |

## 10.2 Differentiation

Features we have that competitors don't:

- [ ] 5-Gate systematic approach
- [ ] CONSIDER watchlist (transparency)
- [ ] Honest timeframe framing
- [ ] Matched-period SPY comparison
- [ ] Age-based thresholds

---

# 11. REVIEW OUTPUT

## 11.1 Issues Found

List all issues discovered:

```
## CRITICAL ISSUES
1. [Description] - [File] - [Fix Required]

## MODERATE ISSUES
1. [Description] - [File] - [Fix Required]

## MINOR ISSUES
1. [Description] - [File] - [Fix Required]

## RECOMMENDATIONS
1. [Feature/Improvement] - [Rationale]
```

## 11.2 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Loser exposed publicly | Low | High | Double-check filter_public_positions() |
| Tweet exceeds 280 chars | Medium | Low | Validation function catches |
| SPY comparison misleading | Low | Medium | Matched-period methodology |
| Workflow fails silently | Medium | Medium | Add alerting |

## 11.3 Testing Recommendations

Before deployment, test these scenarios:

1. **All losers week** - Verify graceful handling
2. **Zero signals week** - Verify "no signals" messaging
3. **Multiple milestones** - Verify all celebrated
4. **API failures** - Verify error handling
5. **Re-run same day** - Verify idempotency

---

# 12. FINAL SIGN-OFF CHECKLIST

## Pre-Deployment Requirements

- [ ] All CRITICAL issues resolved
- [ ] All MODERATE issues resolved or documented
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual review of sample outputs
- [ ] Dry-run tweet successful
- [ ] Newsletter renders correctly
- [ ] Workflows trigger correctly
- [ ] Monitoring/alerting in place

## Approval

```
Implementation Review: [PASS/FAIL]
Reviewed By: [Claude Code]
Date: [DATE]
Notes: [Any caveats or conditions]
```

---

# APPENDIX: QUICK VERIFICATION COMMANDS

```bash
# 1. Check for banned terms
grep -rE "weekly_wins|PASS signal|TRADE|HMA Pivot|Banker" *.py content_queue.json newsletter.html

# 2. Check for losing tickers (replace with actual losers)
grep -E "SMCI|IONQ|RIVN" content_queue.json newsletter.html

# 3. Verify all tweets under 280
python -c "
import json
with open('content_queue.json') as f:
    for t in json.load(f)['tweets']:
        if t.get('char_count', 0) > 280:
            print(f'FAIL: {t[\"id\"]}')
"

# 4. Verify holding periods present
grep -c "weeks\|days" content_queue.json
# Should be > 0 for position content

# 5. Verify newsletter structure
grep -c "Portfolio" newsletter.html
# Should be 0

# 6. Count tweets generated
cat content_queue.json | jq '.total_tweets'
# Should be 25
```

---

# END OF REVIEW PROMPT
