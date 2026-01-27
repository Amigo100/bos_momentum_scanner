# Claude Code Implementation Prompt

## Context

I'm updating the Sterling Signals marketing system - a momentum trading newsletter with automated tweet generation, newsletter compilation, and social media posting.

## Reference Files

Please read these files to understand the current system:
- `TODO.md` - Comprehensive task list for this update
- `scanner.py` - Stock scanning logic (needs limit removal)
- `tweet_generator.py` - Tweet generation (needs new categories + safeguards)
- `social_graphics.py` - Chart/graphic generation
- `newsletter_compiler.py` - Newsletter HTML generation
- `substack_notes_generator.py` - Substack notes generation
- `twitter_poster.py` - Tweet posting (reference only, minimal changes)
- `chart_capture.py` - TradingView captures (reference only)

## Your Task

Implement ALL changes from `TODO.md` following this order:

### Step 1: Create Config Module
Create `config.py` with:
- All threshold constants (win thresholds, SPY outperformance minimum, etc.)
- Signal classification definitions
- Centralized settings that other modules import

### Step 2: Update Scanner Logic
In `scanner.py`:
- Remove the 1-signal-per-week limit - return ALL signals that pass 5 gates
- Add CONSIDER classification for stocks passing gates 1-4 but not gate 5
- Add WATCHLIST classification for strong technicals pending theme alignment
- Update `signals.json` output structure to include all new classifications
- Add `scan_historical_signals()` function to check past signals for big wins
- Add `find_big_wins()` function with threshold filtering

### Step 3: Create Signal Tracker
Create `signal_tracker.py` with:
- Function to load historical signals from portfolio.csv
- Function to fetch current prices and calculate P&L
- Function to identify threshold crossings (25%, 50%, 100%)
- Celebration tracking to avoid repeat posts
- Integration with tweet generator

### Step 4: Update Tweet Generator
In `tweet_generator.py`:
- Add safeguard functions:
  - `should_post_beat_spy()` - check if outperforming SPY by threshold
  - `filter_public_positions()` - remove losers from public content
  - `has_enough_wins()` - check minimum winners for weekly_wins
  - `get_comparable_returns()` - fair SPY comparison calculation
- Add new categories:
  - `weekly_wins` - with all safeguards
  - `self_quote` - for big win celebrations
  - `consider_spotlight` - for watchlist stocks
- Remove/merge old categories as specified in TODO.md
- Update `WEEKLY_SCHEDULE` to new 25-tweet format
- Add fallback content logic when safeguards block content
- Update all templates to use "TEAL signal" branding

### Step 5: Update Social Graphics
In `social_graphics.py`:
- Add `generate_weekly_wins_graphic()` 
- Add `generate_big_win_graphic()`
- Add `generate_consider_graphic()`
- Update `generate_beat_spy()` with safeguard check
- Remove or repurpose `generate_portfolio_dashboard()` (no longer public)

### Step 6: Update Newsletter Compiler
In `newsletter_compiler.py`:
- Remove "Current Portfolio" section completely
- Remove individual position P&L displays
- Remove entry prices for open positions
- Add new sections:
  - "THIS WEEK'S TEAL SIGNALS" (all PASS signals)
  - "ON OUR RADAR" (CONSIDER signals)
  - "WIN HIGHLIGHTS" (only if winners exist above threshold)
- Add conditional section hiding (don't show empty sections)
- Keep private portfolio tracking for internal stop monitoring

### Step 7: Update Substack Notes Generator
In `substack_notes_generator.py`:
- Remove portfolio references
- Align note categories with new tweet categories
- Update templates to match new branding

### Step 8: Update Workflow
If `.github/workflows/friday_scan.yml` exists, update to:
- Run historical signal scanning
- Calculate SPY comparison
- Apply safeguards before content generation

## Important Constraints

1. **NEVER** generate content mentioning losing positions publicly
2. **NEVER** post beat_spy unless outperforming by 5%+ 
3. **NEVER** post weekly_wins unless 2+ winners above 15%
4. **ALWAYS** use "TEAL signal" branding (not "PASS signal")
5. **ALWAYS** include fallback content when safeguards block primary content
6. **ALWAYS** maintain private portfolio.csv tracking for stop monitoring

## Code Style

- Use existing code patterns and naming conventions
- Add docstrings to all new functions
- Include type hints
- Add comments explaining safeguard logic
- Keep functions focused and testable

## Verification

After implementation, the system should:
1. Generate tweets for all PASS signals (not limited to 1)
2. Show CONSIDER signals as watchlist items
3. Automatically generate celebration posts for big wins
4. Skip beat_spy when not outperforming
5. Skip weekly_wins when insufficient winners
6. Never mention losing positions in public content
7. Continue tracking all positions privately

Please implement these changes systematically, updating each file and confirming completion before moving to the next.
