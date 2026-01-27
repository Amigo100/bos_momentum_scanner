# Claude Code Review & Gap Check Prompt

## Context

The Sterling Signals marketing system has been updated with:
- New safeguards for win thresholds and SPY comparisons
- Removal of 1-signal-per-week limit
- New CONSIDER classification for watchlist stocks
- Historical signal scanning for big wins
- New tweet categories (weekly_wins, self_quote, consider_spotlight)
- Newsletter restructuring to remove public portfolio display
- Substack notes alignment

## Your Task

Please review the implementation and check for ANY gaps, edge cases, or issues we may have missed.

### 1. Safeguard Completeness Check

Review all content generation paths and verify:
- [ ] Can a losing position EVER appear in a public tweet?
- [ ] Can beat_spy content EVER generate when not outperforming?
- [ ] Can weekly_wins EVER generate with insufficient winners?
- [ ] Are there any code paths that bypass the safeguards?
- [ ] What happens if ALL positions are losers? (Should generate no position-related content)
- [ ] What happens if we have 0 PASS signals? (Should still work with themes/engagement)

### 2. Edge Case Analysis

Consider and handle:
- [ ] What if yfinance API fails to fetch prices? (Need fallback/skip logic)
- [ ] What if portfolio.csv is empty? (First week scenario)
- [ ] What if signals.json doesn't exist? (Scanner hasn't run)
- [ ] What if a ticker is delisted? (Remove from tracking)
- [ ] What if SPY data fetch fails? (Skip SPY comparison)
- [ ] What if we have exactly 1 winner at 14.9%? (Just below threshold)

### 3. Data Flow Verification

Trace data through the system:
- [ ] Scanner output → Tweet generator: All fields present?
- [ ] Portfolio.csv → Signal tracker: Correct date parsing?
- [ ] Historical signals → Self-quote: Celebration tracking working?
- [ ] Newsletter briefing → Tweet content: All mappings correct?

### 4. Branding Consistency Check

Verify across all files:
- [ ] "TEAL signal" used consistently (not "PASS signal" in public content)
- [ ] "TEAL means go" tagline present where appropriate
- [ ] No banned terms from marketing vocabulary appearing
- [ ] Color scheme references match (teal/violet, not blue/pink like competitors)

### 5. Private vs Public Data Separation

Verify:
- [ ] portfolio.csv continues to track ALL positions (including losers)
- [ ] Entry prices for open positions NEVER in public content
- [ ] Stop loss levels NEVER in public content
- [ ] Internal P&L tracking continues working
- [ ] Sell signals still generated when stops hit (but not tweeted unless win)

### 6. Missing Features Check

Did we miss anything?
- [ ] Should there be a "cold streak" circuit breaker? (If 3+ losses in a row, reduce posting?)
- [ ] Should consider signals have an expiry? (After X weeks, remove from watchlist)
- [ ] Should big win celebrations have a cooldown? (Don't spam same ticker)
- [ ] Should there be a maximum tweets about same ticker per week?
- [ ] Do we need to handle stock splits? (Entry price adjustment)
- [ ] Do we need to handle ticker changes? (META was FB, etc.)

### 7. Content Quality Check

Review generated content for:
- [ ] Are tweet templates under 280 characters?
- [ ] Do all tweets have CTAs (Substack link or question)?
- [ ] Are threads properly structured (1/5, 2/5, etc.)?
- [ ] Do graphics have correct dimensions for X/Twitter?
- [ ] Are fallback contents engaging (not just filler)?

### 8. Automation Reliability

Check workflow robustness:
- [ ] What happens if GitHub Actions fails mid-run?
- [ ] Is there idempotency? (Can re-run without duplicate posts?)
- [ ] Are there retries for API failures?
- [ ] Is there logging for debugging production issues?

### 9. Legal/Compliance Considerations

Verify:
- [ ] No explicit "buy this stock" language without disclaimer?
- [ ] "Not financial advice" present in appropriate places?
- [ ] Past performance disclaimers where showing returns?
- [ ] No promises of future returns?

### 10. Competitor Feature Parity

Compare to analyzed competitors:
- [ ] Weekly win showcase ✓
- [ ] Self-quoting past calls ✓
- [ ] Price-anchored watchlists ✓
- [ ] Theme spotlights with tickers ✓
- [ ] Engagement polls ✓
- [ ] Follower testimonial amplification (did we implement this?)
- [ ] "Chart every ticker in comments" engagement tactic (do we want this?)

## Output Required

Please provide:
1. List of any gaps found
2. Suggested fixes for each gap
3. Any additional features worth considering
4. Risk assessment (what could go wrong in production?)
5. Recommended testing scenarios before deployment

## Files to Review

- `config.py`
- `scanner.py`
- `signal_tracker.py`
- `tweet_generator.py`
- `social_graphics.py`
- `newsletter_compiler.py`
- `substack_notes_generator.py`
- `TODO.md` (verify all items completed)
