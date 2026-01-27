# Sterling Signals Marketing System Overhaul - TODO

## Overview
This document outlines all changes needed to implement the new engagement-optimized marketing system while maintaining integrity safeguards.

---

## PHASE 1: SAFEGUARDS & THRESHOLDS

### 1.1 Win Threshold Configuration
**File:** `config.py` (new) or add to existing config

- [ ] Create `THRESHOLDS` dict:
  ```python
  THRESHOLDS = {
      'min_win_to_highlight': 15.0,      # Minimum % gain to include in weekly_wins
      'big_win_threshold': 25.0,          # Trigger standalone self_quote tweet
      'home_run_threshold': 50.0,         # Celebration post, pin candidate
      'hall_of_fame_threshold': 100.0,    # Thread-worthy, reference repeatedly
      'spy_outperformance_min': 5.0,      # Must beat SPY by this % to use beat_spy content
      'min_winners_for_weekly_wins': 2,   # Need at least 2 winners to post weekly_wins
      'max_loss_to_mention': -5.0,        # Never mention positions worse than this
  }
  ```

### 1.2 SPY Comparison Safeguards
**File:** `tweet_generator.py`

- [ ] Add `should_post_beat_spy()` function:
  - Fetch SPY return for comparison period
  - Calculate portfolio/signals average return
  - Return True ONLY if outperforming by `spy_outperformance_min`
  - If not outperforming, skip beat_spy category for the week

- [ ] Add `get_comparable_returns()` function:
  - Calculate SPY return over same holding period as signals
  - Weight by position age (fair comparison)
  - Return dict with `spy_return`, `signals_return`, `outperformance`

### 1.3 Negative Content Filtering
**File:** `tweet_generator.py`

- [ ] Add `filter_public_positions()` function:
  - Remove any position with P&L < 0 from public content
  - Remove any position with P&L < `min_win_to_highlight`
  - Keep full data internally for stop monitoring
  - Return filtered list for tweet generation

- [ ] Add `has_enough_wins()` function:
  - Check if we have `min_winners_for_weekly_wins` positions above threshold
  - If not, skip weekly_wins tweet (don't post weak results)

---

## PHASE 2: SCANNER LOGIC CHANGES

### 2.1 Remove 1-Signal-Per-Week Limit
**File:** `scanner.py`

- [ ] Locate the code that limits to 1 PASS signal
- [ ] Change to return ALL signals that pass all 5 gates
- [ ] Add new classification tiers:
  ```python
  SIGNAL_CLASSIFICATIONS = {
      'PASS': 'Cleared all 5 gates - full recommendation',
      'CONSIDER': 'Cleared gates 1-4, watching for gate 5',
      'WATCHLIST': 'Strong technical setup, theme alignment pending',
      'CAUTION': 'Open position showing weakness',
      'EXIT': 'Stop triggered or thesis broken'
  }
  ```

### 2.2 Add CONSIDER Classification
**File:** `scanner.py`

- [ ] Add logic to flag stocks that:
  - Pass HMA Pivot (Gate 1)
  - Pass Banker threshold (Gate 2)
  - Pass Beta/volatility filter (Gate 3)
  - Align with hot theme (Gate 4)
  - BUT haven't cleared Gatekeeper/Forensic Audit (Gate 5)
- [ ] Store these as `consider_signals` in signals.json
- [ ] Include reason why Gate 5 not passed (for internal reference)

### 2.3 Historical Signal Tracking
**File:** `scanner.py` or new `signal_tracker.py`

- [ ] Create `scan_historical_signals()` function:
  - Load all past PASS signals from portfolio.csv or signals history
  - Fetch current prices for each
  - Calculate P&L from signal date
  - Return list sorted by performance

- [ ] Create `find_big_wins()` function:
  - Filter historical signals by threshold (25%, 50%, 100%)
  - Return list of tickers ready for celebration posts
  - Include: ticker, entry_price, current_price, pnl_pct, signal_date, theme

### 2.4 Update signals.json Structure
**File:** `scanner.py`

- [ ] New output structure:
  ```json
  {
    "scan_date": "2026-01-25",
    "scan_stats": { "total": 1817, "gate1": 485, ... },
    "pass_signals": [ ... ],       // ALL that passed 5 gates
    "consider_signals": [ ... ],   // Passed gates 1-4
    "watchlist_signals": [ ... ],  // Strong technicals, theme TBD
    "historical_winners": [ ... ], // Past signals now in profit
    "big_wins": [ ... ],           // Past signals above 25%
    "home_runs": [ ... ],          // Past signals above 50%
    "caution_signals": [ ... ],    // Open positions weakening
    "exit_signals": [ ... ]        // Stops triggered
  }
  ```

---

## PHASE 3: TWEET GENERATOR OVERHAUL

### 3.1 New Category System (8 Categories)
**File:** `tweet_generator.py`

- [ ] Remove old categories:
  - `theme_cold`
  - `roth_ira` (keep as occasional mention)
  - `pdt_friendly` (keep as occasional mention)
  - `post_mortem` (newsletter only)
  - `sell_signal` (internal only)
  - `thread_week_ahead`
  - `thread_educational` (monthly only)
  - `position_update` (merge into weekly_wins)
  - `closed_trade` (merge into self_quote)
  - `sector_rotation` (merge into theme_hot)
  - `market_insight` (merge into theme_hot)
  - `system_promo` (merge into funnel_graphic)

- [ ] Keep/Update categories:
  - `buy_signal` - Now shows ALL pass signals, not just 1
  - `theme_hot` - Add tickers with current prices
  - `beat_spy` - Add safeguard check before generating
  - `power_hour` - Keep as-is
  - `funnel_graphic` - Merge system_promo content
  - `engagement` - Merge educational content

- [ ] Add new categories:
  - `weekly_wins` - Showcase best performers (with safeguards)
  - `self_quote` - Celebrate big wins from past signals
  - `consider_spotlight` - Highlight CONSIDER stocks as watchlist

### 3.2 Weekly Wins Generator
**File:** `tweet_generator.py`

- [ ] Create `generate_weekly_wins()`:
  ```python
  def generate_weekly_wins(content: WeeklyContent) -> Optional[Tweet]:
      """Generate weekly wins tweet with safeguards."""
      
      # Get all positions above threshold
      winners = get_filtered_winners(content, min_pct=THRESHOLDS['min_win_to_highlight'])
      
      # Check we have enough to post
      if len(winners) < THRESHOLDS['min_winners_for_weekly_wins']:
          return None  # Skip this week - not enough wins
      
      # Check SPY comparison is favorable
      spy_comparison = get_comparable_returns(winners)
      if spy_comparison['outperformance'] < THRESHOLDS['spy_outperformance_min']:
          return None  # Skip - not meaningfully beating market
      
      # Generate tweet with top 3-5 winners
      # ...
  ```

### 3.3 Self-Quote Generator
**File:** `tweet_generator.py`

- [ ] Create `generate_self_quotes()`:
  - Scan historical signals for those crossing thresholds
  - Generate celebration tweet for each big win
  - Include original signal date and entry price
  - Format: "Called $X at $Y on [date]. Now $Z (+XX%)"

- [ ] Create threshold-based templates:
  - 25%+ : Standard self-quote
  - 50%+ : "Home run" celebration
  - 100%+ : Hall of Fame post

### 3.4 Consider Spotlight Generator
**File:** `tweet_generator.py`

- [ ] Create `generate_consider_spotlight()`:
  - Pull from `consider_signals` in scanner output
  - Format as "On our radar" or "Watching closely"
  - Include: ticker, current price, theme, what's missing for full signal
  - DO NOT frame as buy recommendation

### 3.5 Beat SPY Safeguard Integration
**File:** `tweet_generator.py`

- [ ] Update `generate_beat_spy()`:
  - Call `should_post_beat_spy()` first
  - If returns False, return None (skip this slot)
  - Replace with engagement or theme_hot content instead

### 3.6 Update Schedule
**File:** `tweet_generator.py`

- [ ] New `WEEKLY_SCHEDULE`:
  ```python
  WEEKLY_SCHEDULE = {
      "Saturday": [
          (1, "weekly_wins"),        # 08:00 - ONLY if safeguards pass
          (2, "thread_buy_signal"),  # 10:00 - Deep dive on top signal
          (3, "theme_hot"),          # 12:30 - Theme + tickers
          (4, "funnel_graphic"),     # 15:30 - Scanner stats
          (5, "engagement"),         # 18:00 - Poll
      ],
      "Sunday": [
          (1, "buy_signal"),         # 08:00 - This week's signals (all of them)
          (2, "consider_spotlight"), # 10:00 - Watchlist stocks
          (3, "beat_spy"),           # 15:30 - ONLY if outperforming
          (4, "engagement"),         # 18:00 - Community
      ],
      "Monday": [
          (1, "theme_hot"),          # 08:00
          (2, "self_quote"),         # 10:00 - If any big wins to celebrate
          (3, "power_hour"),         # 15:30
          (4, "engagement"),         # 18:00
      ],
      # ... Tuesday-Friday similar pattern
  }
  ```

### 3.7 Fallback Content Logic
**File:** `tweet_generator.py`

- [ ] Create `get_fallback_content()`:
  - If weekly_wins safeguards fail → post theme_hot instead
  - If beat_spy safeguards fail → post engagement instead
  - If no self_quote candidates → post consider_spotlight
  - Ensure no empty slots in schedule

---

## PHASE 4: NEWSLETTER CHANGES

### 4.1 Remove Public Portfolio Display
**File:** `newsletter_compiler.py`

- [ ] Remove "Current Portfolio" section from HTML output
- [ ] Remove individual position P&L tables
- [ ] Remove entry prices for open positions
- [ ] Keep internal portfolio tracking for:
  - Stop monitoring
  - Sell signal generation
  - Historical performance calculation

### 4.2 New Newsletter Structure
**File:** `newsletter_compiler.py`

- [ ] Update HTML template sections:
  ```
  1. THIS WEEK'S TEAL SIGNALS
     - All PASS signals (not just 1)
     - Full thesis for each
     - Entry level guidance
  
  2. ON OUR RADAR (CONSIDER)
     - Stocks watching closely
     - What they need to become full signals
  
  3. THEME RANKINGS
     - PRIME themes with top tickers
     - INVESTABLE themes
     - What's cooling off (brief)
  
  4. WIN HIGHLIGHTS (if applicable)
     - Closed trades above 15%
     - Big wins celebration
     - NO mention of losses
  
  5. SCANNER STATS
     - Funnel visualization
     - This week's filtering numbers
  
  6. WEEK AHEAD
     - Key catalysts
     - Earnings to watch
  ```

### 4.3 Private Portfolio Tracking
**File:** `newsletter_compiler.py` or `portfolio_tracker.py`

- [ ] Maintain `portfolio.csv` with all open positions
- [ ] Continue generating internal reports with full P&L
- [ ] Use for:
  - Stop loss monitoring
  - Sell signal generation
  - Historical win rate calculation (internal metrics)
- [ ] DO NOT expose in public newsletter

### 4.4 Conditional Sections
**File:** `newsletter_compiler.py`

- [ ] Add logic to hide sections if no content:
  - Hide "Win Highlights" if no winners above threshold
  - Hide "CONSIDER" section if no consider signals
  - Never show empty sections

---

## PHASE 5: SUBSTACK NOTES CHANGES

### 5.1 Align with New Structure
**File:** `substack_notes_generator.py`

- [ ] Remove portfolio references
- [ ] Update note templates to match tweet style:
  - TEAL signal announcements
  - Theme spotlights with tickers + prices
  - Big win celebrations
  - Scanner stats

### 5.2 Note Categories
**File:** `substack_notes_generator.py`

- [ ] Map to new tweet categories:
  ```python
  NOTE_CATEGORIES = {
      'signal_alert': 'New TEAL signal announcement',
      'theme_update': 'Hot theme with top tickers',
      'win_celebration': 'Big win highlight',
      'scanner_stats': 'Weekly funnel visualization',
      'watchlist': 'CONSIDER stocks spotlight'
  }
  ```

---

## PHASE 6: SOCIAL GRAPHICS UPDATES

### 6.1 New Graphics Types
**File:** `social_graphics.py`

- [ ] Add `generate_weekly_wins_graphic()`:
  - Visual showcase of top 3-5 winners
  - Bar chart or card layout
  - Include % gains prominently
  - SPY comparison if favorable

- [ ] Add `generate_big_win_graphic()`:
  - Single ticker celebration card
  - Entry → Current price visual
  - Percentage gain prominent
  - Theme badge

- [ ] Add `generate_consider_graphic()`:
  - Watchlist card design
  - Multiple tickers
  - "On Our Radar" branding

### 6.2 Update Existing Graphics
**File:** `social_graphics.py`

- [ ] `generate_beat_spy()`:
  - Add safeguard check - don't generate if not outperforming
  - Return None if comparison unfavorable

- [ ] `generate_portfolio_dashboard()`:
  - Remove or repurpose (no longer public)
  - Could become internal-only metric tracker

---

## PHASE 7: WORKFLOW INTEGRATION

### 7.1 Friday Scan Workflow
**File:** `.github/workflows/friday_scan.yml` or equivalent

- [ ] Update workflow to:
  1. Run scanner (now returns all PASS + CONSIDER signals)
  2. Scan historical signals for big wins
  3. Calculate SPY comparison
  4. Generate tweets with safeguards
  5. Generate newsletter (no portfolio)
  6. Generate Substack notes

### 7.2 Automated Big Wins Detection
**File:** `scanner.py` or `signal_tracker.py`

- [ ] Add step in Friday workflow:
  ```python
  # Check all historical signals for threshold crossings
  big_wins = scan_historical_signals(
      min_threshold=THRESHOLDS['big_win_threshold']
  )
  
  # Generate self_quote tweets for new threshold crossings
  for win in big_wins:
      if not already_celebrated(win):
          generate_self_quote(win)
          mark_as_celebrated(win)
  ```

### 7.3 Celebration Tracking
**File:** New `celebrations.json` or add to portfolio.csv

- [ ] Track which wins have been celebrated to avoid repeats:
  ```json
  {
    "ASPI": {
      "25_pct_celebrated": "2026-01-20",
      "50_pct_celebrated": null,
      "100_pct_celebrated": null
    }
  }
  ```

---

## PHASE 8: TESTING & VALIDATION

### 8.1 Unit Tests
**File:** `tests/test_safeguards.py` (new)

- [ ] Test `should_post_beat_spy()` with various scenarios
- [ ] Test `filter_public_positions()` removes losers
- [ ] Test `has_enough_wins()` threshold logic
- [ ] Test weekly_wins generates None when safeguards fail

### 8.2 Integration Tests
**File:** `tests/test_tweet_generation.py`

- [ ] Test full workflow with mock data
- [ ] Verify no losing positions appear in output
- [ ] Verify SPY comparison only appears when favorable
- [ ] Verify fallback content fills empty slots

### 8.3 Manual Verification Checklist
- [ ] Run with sample data where we're DOWN vs SPY
  - Verify: No beat_spy tweets generated
  - Verify: weekly_wins skipped or shows only winners
- [ ] Run with sample data where all positions are losers
  - Verify: weekly_wins tweet not generated
  - Verify: No position P&L mentioned anywhere
- [ ] Run with sample data where we have big wins
  - Verify: self_quote tweets generated
  - Verify: Correct threshold categories applied

---

## PHASE 9: DOCUMENTATION

### 9.1 Update CLAUDE.md
- [ ] Document new category system
- [ ] Document threshold configuration
- [ ] Document safeguard logic
- [ ] Update marketing vocabulary if needed

### 9.2 Update README
- [ ] Document new workflow
- [ ] Document configuration options
- [ ] Add examples of expected output

---

## FILES TO MODIFY

| File | Changes |
|------|---------|
| `scanner.py` | Remove 1-signal limit, add CONSIDER classification, add historical scanning |
| `tweet_generator.py` | New categories, safeguards, weekly_wins, self_quote |
| `social_graphics.py` | New graphics types, safeguard integration |
| `newsletter_compiler.py` | Remove portfolio, new structure |
| `substack_notes_generator.py` | Align with new categories |
| `twitter_poster.py` | No changes needed |
| `chart_capture.py` | No changes needed |
| `config.py` (new) | Centralized thresholds and settings |
| `signal_tracker.py` (new) | Historical signal scanning |
| `.github/workflows/friday_scan.yml` | Updated workflow steps |

---

## IMPLEMENTATION ORDER

1. **Config & Thresholds** - Foundation for all safeguards
2. **Scanner Changes** - Remove limits, add classifications
3. **Signal Tracker** - Historical scanning for big wins
4. **Tweet Generator** - New categories with safeguards
5. **Social Graphics** - New graphic types
6. **Newsletter** - Remove portfolio, new structure
7. **Substack Notes** - Align with changes
8. **Workflow Integration** - Connect everything
9. **Testing** - Verify safeguards work
10. **Documentation** - Update all docs

---

## SUCCESS CRITERIA

- [ ] No tweet ever mentions a losing position
- [ ] beat_spy content only appears when outperforming by 5%+
- [ ] weekly_wins only appears with 2+ winners above 15%
- [ ] All PASS signals shown (not limited to 1)
- [ ] CONSIDER signals shown as watchlist
- [ ] Big wins automatically celebrated when crossing thresholds
- [ ] Newsletter has no public portfolio display
- [ ] Portfolio tracking continues privately for stops
