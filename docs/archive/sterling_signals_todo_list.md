# Sterling Signals Comprehensive TODO List
## System Improvement Implementation Checklist

**Created:** January 27, 2026  
**Reference Document:** `sterling_signals_improvement_reference.md`  
**Estimated Total Effort:** 40-50 hours across 4 weeks

---

# How to Use This Document

- [ ] Checkboxes indicate incomplete tasks
- [x] Checked boxes indicate completed tasks
- **Priority:** HIGH / MEDIUM / LOW
- **Effort:** Estimated hours
- **Dependencies:** Tasks that must complete first

---

# Phase 1: Foundation (Week 1)
## Target: Color system live, Substack templates generating

---

## 1.1 Configuration Updates

### Task 1.1.1: Add Signal Color System to config.py
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** None

**File:** `src/config.py`

- [ ] Add `SIGNAL_COLORS` dictionary:
```python
# Signal Color System
SIGNAL_COLORS = {
    'TEAL': {
        'emoji': '🟢',
        'meaning': 'BUY',
        'internal_status': 'PASS',
        'hex': '#008080',
    },
    'VIOLET': {
        'emoji': '🟣',
        'meaning': 'EXIT',
        'internal_status': 'STOPPED',
        'hex': '#8B00FF',
    },
    'AMBER': {
        'emoji': '🟠',
        'meaning': 'WATCH',
        'internal_status': 'CONSIDER',
        'hex': '#FFBF00',
    },
}
```

- [ ] Add `CONVICTION_LANGUAGE` dictionary:
```python
# Conviction Language Mapping
CONVICTION_LANGUAGE = {
    5: 'Extremely Bullish',
    4: 'Bullish',
    3: 'Watching',
    2: 'Cautious',
    1: None,  # Do not post publicly
}

def get_conviction_language(score: int) -> str:
    """Convert internal conviction score to public language."""
    return CONVICTION_LANGUAGE.get(score, 'Watching')
```

- [ ] Add entry price display rules:
```python
# Entry Price Display Rules
ENTRY_PRICE_RULES = {
    'show_for_closed_winners': True,
    'show_for_open_above_threshold': True,
    'threshold_pct': 25.0,
}

WINNER_SHOWCASE_THRESHOLD = 25.0  # Minimum P&L to show entry price
```

- [ ] Add Substack content configuration:
```python
# Substack Content Configuration
SUBSTACK_CONTENT = {
    'monday': {
        'type': 'market_analysis',
        'title_format': 'Market Outlook: Week of {date}',
        'filename': 'monday_market_analysis.html',
    },
    'thursday': {
        'type': 'theme_spotlight',
        'title_format': 'Theme Watch: {theme_name}',
        'filename': 'thursday_theme_spotlight.html',
    },
    'saturday': {
        'type': 'weekly_signals',
        'title_format': 'TEAL Signals: {date} + Watchlist',
        'filename': 'saturday_weekly_signals.html',
    },
    'sunday': {
        'type': 'deep_dive',
        'title_format': 'Deep Dive: ${ticker}',
        'filename': 'sunday_deep_dive.html',
    },
}
```

---

### Task 1.1.2: Update marketing_vocabulary.py
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** None

**File:** `src/marketing_vocabulary.py`

- [ ] Add new approved terms to `APPROVED_TERMS`:
```python
NEW_APPROVED_TERMS = [
    'TEAL signal',
    'TEAL signals',
    '🟢 TEAL',
    'VIOLET alert',
    'VIOLET alerts',
    '🟣 VIOLET',
    'AMBER watch',
    'AMBER watchlist',
    '🟠 AMBER',
    'Extremely Bullish',
    'Bullish',
    'Watching',
    '5 gates cleared',
    '5-gate system',
    'Meanwhile... S&P 500',
    'from $',  # Entry price format
    '→',  # Arrow for price progression
]
```

- [ ] Add new banned terms to `BANNED_TERMS`:
```python
NEW_BANNED_TERMS = [
    'buy signal',  # Use 'TEAL signal'
    'sell signal',  # Use 'VIOLET alert'
    'watchlist signal',  # Use 'AMBER watch'
    'conviction 5',  # Use 'Extremely Bullish'
    'conviction 4',  # Use 'Bullish'
    'conviction score',  # Don't expose internal scoring
]
```

- [ ] Update `translate_vocabulary()` function to handle new mappings

---

## 1.2 New Directory Structure

### Task 1.2.1: Create Substack Posts Directory
**Priority:** HIGH | **Effort:** 0.25 hrs | **Dependencies:** None

- [ ] Create directory: `trades/substack_posts/`
- [ ] Add `.gitkeep` file to preserve empty directory
- [ ] Update `.gitignore` if needed (keep HTML files tracked or ignored based on preference)

---

## 1.3 Substack Content Generator

### Task 1.3.1: Create substack_content_generator.py (Core Structure)
**Priority:** HIGH | **Effort:** 2 hrs | **Dependencies:** 1.1.1

**File:** `src/substack_content_generator.py`

- [ ] Create file with imports and base structure:
```python
#!/usr/bin/env python3
"""
Sterling Signals Substack Content Generator

Generates HTML files for weekly Substack posts:
- Monday: Market Analysis
- Thursday: Theme Spotlight
- Saturday: Weekly Signals + Watchlist
- Sunday: Deep Dive (optional)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    SIGNAL_COLORS,
    CONVICTION_LANGUAGE,
    SUBSTACK_CONTENT,
    WINNER_SHOWCASE_THRESHOLD,
)

# Paths
TRADES_DIR = Path(__file__).parent.parent / 'trades'
SIGNALS_FILE = TRADES_DIR / 'signals.json'
PORTFOLIO_FILE = TRADES_DIR / 'portfolio.csv'
OUTPUT_DIR = TRADES_DIR / 'substack_posts'

def load_signals() -> Dict:
    """Load current signals from JSON."""
    pass

def load_portfolio() -> List[Dict]:
    """Load portfolio positions from CSV."""
    pass

def get_winners_above_threshold(threshold: float = 25.0) -> List[Dict]:
    """Get positions with gains above threshold for showcase."""
    pass

def generate_monday_market_analysis() -> str:
    """Generate Monday market analysis HTML."""
    pass

def generate_thursday_theme_spotlight() -> str:
    """Generate Thursday theme spotlight HTML."""
    pass

def generate_saturday_weekly_signals() -> str:
    """Generate Saturday weekly signals HTML."""
    pass

def generate_sunday_deep_dive(ticker: str = None) -> str:
    """Generate Sunday deep dive HTML for top signal."""
    pass

def main():
    """Main entry point with CLI argument handling."""
    pass

if __name__ == '__main__':
    main()
```

---

### Task 1.3.2: Implement Monday Market Analysis Generator
**Priority:** HIGH | **Effort:** 2 hrs | **Dependencies:** 1.3.1

**File:** `src/substack_content_generator.py`

- [ ] Implement `generate_monday_market_analysis()`:
  - [ ] Load market analysis data from `market_analyzer.py` output
  - [ ] Load hot/cold themes from `signals.json`
  - [ ] Load top performers (25%+ gains) for "Winners Update" section
  - [ ] Calculate SPY comparison for matched periods
  - [ ] Generate HTML using template

- [ ] Create HTML template for market analysis:
```python
MONDAY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>

<h2>The Big Picture</h2>
{market_context}

<h2>Where Money Is Flowing</h2>
<h3>🔥 Hot Themes:</h3>
<ul>
{hot_themes_list}
</ul>

<h3>❄️ Cooling Off:</h3>
<ul>
{cold_themes_list}
</ul>

<h2>Key Levels to Watch</h2>
{key_levels}

<h2>Our Stance: {stance}</h2>
{stance_explanation}

<hr>

<h2>🟢 Top Performers Update</h2>
<p>Our TEAL signals continue to outperform:</p>
<table>
<tr><th>Ticker</th><th>Entry</th><th>Current</th><th>Return</th><th>Days Held</th></tr>
{winners_table_rows}
</table>
<p><strong>Meanwhile... S&P 500: {spy_return}%</strong></p>

<hr>
<p><em>Want the full signal list? <a href="#">Become a paid subscriber</a></em></p>
</body>
</html>
"""
```

---

### Task 1.3.3: Implement Thursday Theme Spotlight Generator
**Priority:** HIGH | **Effort:** 1.5 hrs | **Dependencies:** 1.3.1

**File:** `src/substack_content_generator.py`

- [ ] Implement `generate_thursday_theme_spotlight()`:
  - [ ] Identify hottest theme from signals.json (highest theme score)
  - [ ] Extract TEAL signals in that theme
  - [ ] Extract AMBER/CONSIDER signals in that theme
  - [ ] Generate theme thesis using existing LLM analysis
  - [ ] Generate HTML using template

- [ ] Create HTML template for theme spotlight:
```python
THURSDAY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>

<h2>Why This Theme Matters Now</h2>
{theme_thesis}

<h2>The Catalysts</h2>
<ol>
{catalysts_list}
</ol>

<h2>Theme Score: {theme_score}/10 — {theme_rating}</h2>

<h2>Stocks in This Theme</h2>

<h3>🟢 TEAL Signals (Cleared All 5 Gates)</h3>
<ul>
{teal_signals_list}
</ul>

<h3>🟠 AMBER Watch (Monitoring)</h3>
<ul>
{amber_signals_list}
</ul>

<h2>What Could Go Wrong</h2>
{risk_factors}

<hr>
<p><em>Full analysis and entry timing available to paid subscribers.</em></p>
</body>
</html>
"""
```

---

### Task 1.3.4: Implement Saturday Weekly Signals Generator
**Priority:** HIGH | **Effort:** 2 hrs | **Dependencies:** 1.3.1

**File:** `src/substack_content_generator.py`

- [ ] Implement `generate_saturday_weekly_signals()`:
  - [ ] Load all TEAL (PASS) signals from current scan
  - [ ] Load all VIOLET (exit) signals from portfolio
  - [ ] Load all AMBER (CONSIDER) signals for watchlist
  - [ ] Load winners above 25% threshold
  - [ ] Include chart image paths (from Playwright captures)
  - [ ] Generate HTML using template

- [ ] Create HTML template for weekly signals:
```python
SATURDAY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>

<h2>This Week's Scan Results</h2>
<p>📊 <strong>{total_scanned}</strong> stocks scanned</p>
<p>⚡ <strong>{momentum_pass}</strong> showed momentum characteristics</p>
<p>📈 <strong>{accumulation_pass}</strong> confirmed institutional accumulation</p>
<p>🔥 <strong>{theme_pass}</strong> aligned with hot themes</p>
<p>✅ <strong>{teal_count} TEAL signals</strong> — Cleared all 5 gates</p>

<hr>

<h2>🟢 NEW TEAL SIGNALS</h2>
{teal_signals_section}

<hr>

<h2>🟣 VIOLET ALERTS (Exit Signals)</h2>
{violet_alerts_section}

<hr>

<h2>🟠 AMBER WATCHLIST</h2>
<p>Stocks that cleared 4/5 gates — watching for final confirmation:</p>
<table>
<tr><th>Ticker</th><th>Price</th><th>Theme</th><th>Missing Gate</th></tr>
{amber_watchlist_rows}
</table>

<hr>

<h2>📈 PORTFOLIO UPDATE: Winners Over 25%</h2>
<table>
<tr><th>Ticker</th><th>Entry</th><th>Current</th><th>Return</th><th>Held</th></tr>
{winners_table_rows}
</table>
<p><strong>Meanwhile... S&P 500: {spy_return}%</strong></p>

<hr>
<p><em>This is our free weekly summary. Paid subscribers get real-time alerts, full thesis documents, and position sizing guidance.</em></p>
</body>
</html>
"""
```

- [ ] Create signal detail sub-template:
```python
SIGNAL_DETAIL_TEMPLATE = """
<h3>${ticker} — {theme}</h3>
<p><strong>Conviction: {conviction_language}</strong></p>
<table>
<tr><td>Entry Price</td><td>${entry_price}</td></tr>
<tr><td>Theme</td><td>{theme}</td></tr>
<tr><td>Theme Score</td><td>{theme_score}/10</td></tr>
</table>
<p><strong>Why We're {conviction_language}:</strong></p>
<ul>
{bull_points}
</ul>
<p><strong>Risk Factors:</strong></p>
<ul>
{risk_points}
</ul>
<img src="{chart_path}" alt="{ticker} chart">
<hr>
"""
```

---

### Task 1.3.5: Implement Sunday Deep Dive Generator
**Priority:** MEDIUM | **Effort:** 1.5 hrs | **Dependencies:** 1.3.1

**File:** `src/substack_content_generator.py`

- [ ] Implement `generate_sunday_deep_dive(ticker=None)`:
  - [ ] If no ticker specified, select top TEAL signal (highest conviction)
  - [ ] Generate detailed 5-gate breakdown
  - [ ] Include bull case, bear case, risk management
  - [ ] Generate HTML using template

- [ ] Create HTML template for deep dive (see reference document for full template)

---

### Task 1.3.6: Implement CLI Interface
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 1.3.2, 1.3.3, 1.3.4, 1.3.5

**File:** `src/substack_content_generator.py`

- [ ] Implement `main()` with argument parsing:
  - `--monday` flag for market analysis
  - `--thursday` flag for theme spotlight
  - `--saturday` flag for weekly signals
  - `--sunday` flag for deep dive
  - `--ticker` option for specific deep dive ticker
  - `--all` flag to generate all content

---

## 1.4 Tweet Generator Updates

### Task 1.4.1: Update Tweet Categories
**Priority:** HIGH | **Effort:** 1.5 hrs | **Dependencies:** 1.1.1, 1.1.2

**File:** `src/tweet_generator.py`

- [ ] Rename existing categories:
  - [ ] `buy_signal` → `teal_signal`
  - [ ] `consider_spotlight` → `amber_watch`
  - [ ] `top_performers` → `winner_showcase`
  - [ ] `beat_spy` → `benchmark_alpha`
  - [ ] `milestone_alerts` → `hall_of_fame`

- [ ] Add new categories:
  - [ ] `violet_alert` (exit signals)
  - [ ] `weekly_recap` (high-engagement format)

- [ ] Update category fallback mappings

---

### Task 1.4.2: Add Color Emoji Prefixes
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 1.4.1

**File:** `src/tweet_generator.py`

- [ ] Create helper function `format_signal_with_color(signal_type, ticker, detail)`
- [ ] Update all signal tweet templates to use color prefixes

---

### Task 1.4.3: Implement Conviction Language in Tweets
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 1.1.1

**File:** `src/tweet_generator.py`

- [ ] Update signal tweet templates to use conviction language mapping
- [ ] Map internal scores (5, 4, 3) to "Extremely Bullish", "Bullish", "Watching"

---

### Task 1.4.4: Update Tweet Grid
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 1.4.1

**File:** `src/tweet_generator.py`

- [ ] Update `TWEET_GRID` with new schedule (see reference document)

---

## 1.5 GitHub Actions Updates

### Task 1.5.1: Update friday_scan.yml
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 1.3.6

**File:** `.github/workflows/friday_scan.yml`

- [ ] Add Substack content generation step:
```yaml
      - name: Generate Substack Content
        run: |
          python src/substack_content_generator.py --all
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Commit Substack Content
        run: |
          git add trades/substack_posts/
          git commit -m "Add weekly Substack content" || true
```

---

## 1.6 Phase 1 Testing

### Task 1.6.1: Test Configuration Changes
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 1.1.1, 1.1.2

- [ ] Verify `config.py` imports without errors
- [ ] Verify all new dictionaries accessible
- [ ] Verify `marketing_vocabulary.py` imports without errors

---

### Task 1.6.2: Test Substack Content Generator
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 1.3.6

- [ ] Run each generator individually and verify HTML output
- [ ] Run `--all` flag and verify all files created
- [ ] Verify HTML renders correctly in browser

---

### Task 1.6.3: Test Tweet Generator Updates
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 1.4.4

- [ ] Verify new categories generate correctly
- [ ] Verify color emojis appear in tweet text
- [ ] Verify conviction language appears correctly
- [ ] Verify tweet character counts remain under 280

---

## Phase 1 Completion Checklist

- [ ] **1.1** Configuration updates complete
- [ ] **1.2** Directory structure created
- [ ] **1.3** Substack content generator working
- [ ] **1.4** Tweet generator updated
- [ ] **1.5** GitHub Actions updated
- [ ] **1.6** All tests passing

**Phase 1 Sign-off Date:** _______________

---

# Phase 2: Winner Showcasing (Week 2)
## Target: Entry prices visible, weekly recap format active

---

## 2.1 Winner Showcase Generator

### Task 2.1.1: Create winner_showcase_generator.py
**Priority:** HIGH | **Effort:** 2 hrs | **Dependencies:** Phase 1 complete

**File:** `src/winner_showcase_generator.py`

- [ ] Create file with core functionality:
  - [ ] `load_portfolio()` function
  - [ ] `can_show_entry_price(position)` function
  - [ ] `get_winners_for_showcase(threshold)` function
  - [ ] `format_winner_line(winner)` function
  - [ ] `generate_winner_showcase_tweet()` function
  - [ ] CLI interface with `--tweet`, `--json`, `--threshold` options

---

### Task 2.1.2: Update signal_tracker.py
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 2.1.1

**File:** `src/signal_tracker.py`

- [ ] Add `get_winners_for_showcase()` function if not already present
- [ ] Ensure `can_show_entry_price()` logic is consistent
- [ ] Add function to calculate matched-period SPY comparison

---

## 2.2 Weekly Recap Tweet Format

### Task 2.2.1: Implement weekly_recap Tweet Category
**Priority:** HIGH | **Effort:** 1.5 hrs | **Dependencies:** 2.1.1

**File:** `src/tweet_generator.py`

- [ ] Add `generate_weekly_recap()` function
- [ ] Include top 3-5 winners with entry prices (if qualified)
- [ ] Include "Meanwhile... S&P 500" comparison
- [ ] Implement safeguard: fallback to theme_spotlight if no winners

---

### Task 2.2.2: Implement benchmark_alpha Tweet Category
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 2.2.1

**File:** `src/tweet_generator.py`

- [ ] Add `generate_benchmark_alpha()` function with SPY comparison
- [ ] Add safeguard: only post when outperforming SPY by 5%+
- [ ] Fallback to `engagement` if not outperforming

---

## 2.3 VIOLET Exit Alert Tweets

### Task 2.3.1: Implement violet_alert Tweet Category
**Priority:** MEDIUM | **Effort:** 1 hr | **Dependencies:** 1.4.1

**File:** `src/tweet_generator.py`

- [ ] Add `generate_violet_alert()` function
- [ ] Only generate for **profitable** exits (never show losses)
- [ ] Include entry price, exit price, return, holding period
- [ ] Fallback to `educational` if no profitable exits

---

### Task 2.3.2: Add Exit Tracking to Portfolio Manager
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** 2.3.1

**File:** `src/portfolio_manager.py`

- [ ] Add `get_recent_exits(days: int)` function to retrieve recently closed positions

---

## 2.4 AMBER Watchlist Tweets

### Task 2.4.1: Implement amber_watch Tweet Category
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** 1.4.1

**File:** `src/tweet_generator.py`

- [ ] Add `generate_amber_watch()` function
- [ ] Format: "$TICKER at $XX.XX — Theme"
- [ ] Include 3-5 CONSIDER signals
- [ ] Add "Save this. We'll update when they clear Gate 5."

---

## 2.5 Phase 2 Testing

### Task 2.5.1: Test Winner Showcase Generator
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 2.1.1

- [ ] Run `python src/winner_showcase_generator.py --tweet`
- [ ] Verify entry prices appear for 25%+ positions
- [ ] Verify entry prices hidden for <25% positions
- [ ] Verify tweet under 280 characters

---

### Task 2.5.2: Test New Tweet Categories
**Priority:** HIGH | **Effort:** 0.5 hrs | **Dependencies:** 2.2.1, 2.3.1, 2.4.1

- [ ] Verify `weekly_recap` generates correctly
- [ ] Verify `benchmark_alpha` generates with safeguard
- [ ] Verify `violet_alert` generates only for profitable exits
- [ ] Verify `amber_watch` generates watchlist format

---

## Phase 2 Completion Checklist

- [ ] **2.1** Winner showcase generator complete
- [ ] **2.2** Weekly recap tweet format working
- [ ] **2.3** VIOLET exit alerts implemented
- [ ] **2.4** AMBER watchlist tweets working
- [ ] **2.5** All tests passing

**Phase 2 Sign-off Date:** _______________

---

# Phase 3: Self-Quote System (Week 3)
## Target: Tweet tracking, quote threads building

---

## 3.1 Self-Quote Tracker

### Task 3.1.1: Create self_quote_tracker.py
**Priority:** MEDIUM | **Effort:** 2 hrs | **Dependencies:** Phase 2 complete

**File:** `src/self_quote_tracker.py`

- [ ] Create file with core functionality:
  - [ ] `load_tracker()` / `save_tracker()` functions
  - [ ] `register_signal_tweet(ticker, tweet_id, entry_price, entry_date)` function
  - [ ] `get_unquoted_milestones(ticker, current_pnl)` function
  - [ ] `mark_milestone_quoted(ticker, milestone, quote_tweet_id)` function
  - [ ] `generate_quote_tweet(ticker, milestone, current_price, current_pnl)` function
  - [ ] `get_original_tweet_id(ticker)` function

---

### Task 3.1.2: Update Twitter Poster for Quote Tweets
**Priority:** MEDIUM | **Effort:** 1.5 hrs | **Dependencies:** 3.1.1

**File:** `src/twitter_poster.py`

- [ ] Add `post_quote_tweet(text, quote_tweet_id)` function using Tweepy v2
- [ ] Update posting workflow to check for milestone quote opportunities

---

### Task 3.1.3: Integrate Quote Tracker with Signal Posts
**Priority:** MEDIUM | **Effort:** 1 hr | **Dependencies:** 3.1.1, 3.1.2

**File:** `src/twitter_poster.py`

- [ ] After posting TEAL signal tweet, register it in tracker
- [ ] Store tweet_id for future quote-threading

---

### Task 3.1.4: Create Milestone Check Workflow
**Priority:** MEDIUM | **Effort:** 1.5 hrs | **Dependencies:** 3.1.1, 3.1.2, 3.1.3

**File:** `src/self_quote_tracker.py`

- [ ] Add `check_and_generate_quote_tweets()` function
- [ ] Check all tracked signals for 25%/50%/100% milestones
- [ ] Generate quote tweets for unquoted milestones

---

### Task 3.1.5: Add to Daily Posting Workflow
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** 3.1.4

**File:** `.github/workflows/daily_post.yml`

- [ ] Add milestone check step to daily workflow

---

## 3.2 Phase 3 Testing

### Task 3.2.1: Test Self-Quote Tracker
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** 3.1.1

- [ ] Manually register a test signal
- [ ] Verify milestone detection works
- [ ] Verify quote tweet generation works

---

### Task 3.2.2: Test End-to-End Quote Thread
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** 3.1.5

- [ ] Post a test TEAL signal tweet
- [ ] Verify it gets registered in tracker
- [ ] Simulate milestone (update portfolio P&L)
- [ ] Verify quote tweet generates

---

## Phase 3 Completion Checklist

- [ ] **3.1** Self-quote tracker implemented
- [ ] **3.2** All tests passing

**Phase 3 Sign-off Date:** _______________

---

# Phase 4: Codebase Cleanup (Week 4)
## Target: Clean code, accurate documentation

---

## 4.1 Dead Code Removal

### Task 4.1.1: Remove Momentum Filter Dead Code
**Priority:** LOW | **Effort:** 0.5 hrs | **Dependencies:** None

**File:** `src/scanner.py`

- [ ] Locate `passes_momentum_filter()` function
- [ ] Confirm it always returns `True`
- [ ] Remove function or add deprecation notice
- [ ] Remove all calls to this function
- [ ] Run tests to verify no breakage

---

### Task 4.1.2: Consolidate SPY Comparison Methods
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** None

**File:** `src/signal_tracker.py` or `src/portfolio_manager.py`

- [ ] Identify both SPY comparison methods
- [ ] Deprecate or remove fixed 30-day method (FLAWED)
- [ ] Update all callers to use matched-period method (CORRECT)
- [ ] Add docstring explaining methodology

---

### Task 4.1.3: Remove Killed Tweet Categories
**Priority:** LOW | **Effort:** 0.25 hrs | **Dependencies:** None

**File:** `src/tweet_generator.py`

- [ ] Verify `KILLED_CATEGORIES` list
- [ ] Remove any remaining code for killed categories

---

## 4.2 Configuration Consolidation

### Task 4.2.1: Move Hardcoded Values to config.py
**Priority:** MEDIUM | **Effort:** 1 hr | **Dependencies:** None

**Files:** Multiple

- [ ] Move from `scanner.py`:
  - [ ] HMA period (21) → `config.HMA_PERIOD`
  - [ ] Pivot window k=1 → `config.PIVOT_WINDOW`
  - [ ] VWAP period (20) → `config.VWAP_PERIOD`
  - [ ] Banker multiplier (5) → `config.BANKER_MULTIPLIER`
  - [ ] yfinance batch size (50) → `config.YFINANCE_BATCH_SIZE`
  - [ ] Data period ("1y") → `config.DATA_PERIOD`

- [ ] Update all hardcoded references to use config values

---

## 4.3 Documentation Updates

### Task 4.3.1: Update CLAUDE.md
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** None

**File:** `CLAUDE.md`

- [ ] Fix universe size claim (937 not 1800)
- [ ] Clarify exit strategy (trailing stop primary, BoS advisory)
- [ ] Remove "10% baseline entry" if not implemented
- [ ] Add section on new color signal system
- [ ] Update any other discrepancies from audits

---

### Task 4.3.2: Create/Update MARKETING_GUIDE.md
**Priority:** MEDIUM | **Effort:** 1 hr | **Dependencies:** None

**File:** `docs/MARKETING_GUIDE.md`

- [ ] Create if doesn't exist
- [ ] Document color signal system
- [ ] Document conviction language
- [ ] Document entry price display rules
- [ ] Document tweet categories and grid
- [ ] Document safeguard rules
- [ ] List banned/approved vocabulary

---

### Task 4.3.3: Archive Old Audit Files
**Priority:** LOW | **Effort:** 0.25 hrs | **Dependencies:** None

- [ ] Create `archive/audits/` directory
- [ ] Move completed audit files (01-07)
- [ ] Move any completed TODO lists to `archive/todos/`

---

## 4.4 File System Cleanup

### Task 4.4.1: Add Backup Retention Script
**Priority:** LOW | **Effort:** 0.5 hrs | **Dependencies:** None

**File:** `src/backup_cleanup.py` (NEW)

- [ ] Create script for 30-day backup retention
- [ ] Add to weekly workflow or cron

---

### Task 4.4.2: Verify Directory Structure
**Priority:** LOW | **Effort:** 0.25 hrs | **Dependencies:** 4.3.3

- [ ] Verify structure matches target (see reference document)
- [ ] Create any missing directories
- [ ] Remove any obsolete directories

---

## 4.5 Phase 4 Testing

### Task 4.5.1: Full System Test
**Priority:** HIGH | **Effort:** 1 hr | **Dependencies:** All Phase 4 tasks

- [ ] Run full scanner: `python src/scanner.py --no-llm --top 50`
- [ ] Run tweet generator: `python src/tweet_generator.py`
- [ ] Run Substack generator: `python src/substack_content_generator.py --all`
- [ ] Verify no import errors
- [ ] Verify no runtime errors
- [ ] Spot-check output quality

---

### Task 4.5.2: Documentation Review
**Priority:** MEDIUM | **Effort:** 0.5 hrs | **Dependencies:** 4.3.1, 4.3.2

- [ ] Read through updated CLAUDE.md
- [ ] Verify accuracy of all claims
- [ ] Verify no contradictions with actual code

---

## Phase 4 Completion Checklist

- [ ] **4.1** Dead code removed
- [ ] **4.2** Configuration consolidated
- [ ] **4.3** Documentation updated
- [ ] **4.4** File system cleaned
- [ ] **4.5** All tests passing

**Phase 4 Sign-off Date:** _______________

---

# Post-Implementation Checklist

## Verification

- [ ] Color signal system visible in all tweets
- [ ] Conviction language appearing correctly
- [ ] Entry prices showing for 25%+ winners
- [ ] 3-4 Substack posts generating weekly
- [ ] Weekly recap tweets generating
- [ ] Benchmark comparison ("Meanwhile SPY...") working
- [ ] AMBER watchlist drops posting
- [ ] Self-quote thread building (after first milestone hit)
- [ ] No dead code remaining
- [ ] Documentation accurate

## Monitoring (First 2 Weeks Post-Launch)

- [ ] Monitor tweet engagement vs baseline
- [ ] Monitor Substack open rates
- [ ] Monitor follower growth
- [ ] Check for any safeguard failures
- [ ] Verify no negative positions exposed
- [ ] Collect any user feedback

## Future Enhancements (Backlog)

- [ ] Follower testimonial collection system
- [ ] A/B testing for tweet formats
- [ ] Automated chart quality improvement
- [ ] Email notification for milestone achievements
- [ ] Dashboard for tracking system metrics

---

# Quick Reference: Key File Locations

| Purpose | File Path |
|---------|-----------|
| Color system config | `src/config.py` |
| Vocabulary rules | `src/marketing_vocabulary.py` |
| Substack generator | `src/substack_content_generator.py` |
| Winner showcase | `src/winner_showcase_generator.py` |
| Self-quote tracker | `src/self_quote_tracker.py` |
| Tweet generator | `src/tweet_generator.py` |
| Twitter poster | `src/twitter_poster.py` |
| Friday workflow | `.github/workflows/friday_scan.yml` |
| Daily workflow | `.github/workflows/daily_post.yml` |
| Substack output | `trades/substack_posts/` |
| Quote tracker data | `trades/self_quote_tracker.json` |

---

# Estimated Total Effort Summary

| Phase | Effort | Timeline |
|-------|--------|----------|
| Phase 1: Foundation | ~15 hrs | Week 1 |
| Phase 2: Winner Showcasing | ~8 hrs | Week 2 |
| Phase 3: Self-Quote System | ~8 hrs | Week 3 |
| Phase 4: Codebase Cleanup | ~7 hrs | Week 4 |
| Testing & Buffer | ~5 hrs | Throughout |
| **Total** | **~43 hrs** | **4 weeks** |

---

*End of Sterling Signals Comprehensive TODO List*
