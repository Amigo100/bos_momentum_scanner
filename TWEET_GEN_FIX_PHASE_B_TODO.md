# Sterling Signals — Tweet Generator Fix TODO: Phase 4B

> **Follows:** Phase 4A (structural fixes — fabrication, validation, new categories)
> **Date:** 2026-02-08
> **Convention:** Tasks numbered `[4B.AREA.SEQ]`
> **Context:** Phase 4A fixed 7 of 10 critical failures. Phase 4B addresses 3 remaining issues plus content quality gaps found in the post-fix output (17 tweets generated Feb 8).
> **Prompt mapping:** `TWEET_GEN_FIX_PHASE_B_PROMPTS.md`

---

## What Phase 4A Fixed (confirmed working)

- ✅ Zero fabricated tickers — only real scanner/portfolio tickers appear
- ✅ Zero LLM error messages — meta-language detection catches refusals
- ✅ $MATV exposure reduced from 86% → 29%
- ✅ All openings unique — no repeated phrases
- ✅ Only legitimate sell signals ($LUMN)
- ✅ Chart safety net — chart_required tweets without files are dropped
- ✅ No temporal hallucinations
- ✅ No slot 1 in weekly queue
- ✅ WATCHLIST and NEWSLETTER_CTA categories now appear

## What Phase 4B Must Fix

---

## Phase 4B.1 — PERFORMANCE Category Not Generating

_P0 — The portfolio has WCC +12%, STRL +11%, MOD +17% but zero PERFORMANCE tweets were produced. This is the most visible gap vs reference accounts._

- [ ] **[4B.1.1]** P0 — Debug PERFORMANCE pipeline with logging
  - File: `content/tweet_generator.py`
  - Add `logger.info` at each stage to trace why PERFORMANCE isn't appearing:
    1. `_build_content_data()`: log `len(winners)` and `len(notable_holdings)` after population
    2. `_pick_category()`: log when PERFORMANCE is considered and whether it's assigned or skipped (and why)
    3. `_prepare_slot_data()`: log what's returned for PERFORMANCE
    4. Generation loop: log if PERFORMANCE slot_data comes back None
  - Run generation with real data, capture logs, identify the blockage

- [ ] **[4B.1.2]** P0 — Fix the identified blockage
  - Most likely causes (check in order):
    a. `_build_content_data()` isn't parsing portfolio positions into `notable_holdings` — the position data format may not match what the code expects (field names: `entry_price` vs `avg_cost`, `current_price` vs `last_price`, etc.)
    b. `_pick_category()` never reaches the PERFORMANCE branch — the slot/day rules may not include a PERFORMANCE-eligible slot, or an earlier branch always matches first
    c. `_prepare_slot_data()` returns None because it checks `data.winners` but not `data.notable_holdings`
    d. PERFORMANCE tweets are generated but dropped by chart_required check
  - Fix whichever cause is found. PERFORMANCE should NOT require charts (chart_required=false for receipt tweets).

- [ ] **[4B.1.3]** P0 — Ensure ≥1 PERFORMANCE tweet per day when gains exist
  - In `_pick_category()` or `_plan_weekly_schedule()`: if `data.has_winners or data.has_notable_holdings`, reserve at least one slot per day for PERFORMANCE
  - Suggested slot: slot 2 on weekdays (high-visibility morning slot)
  - PERFORMANCE prompt must produce multi-ticker receipt format:
    ```
    $MOD from $184 to $215 (+17%)
    $WCC from $281 to $315 (+12%)
    $STRL from $362 to $401 (+11%)
    ```

---

## Phase 4B.2 — EDUCATIONAL Tweets Fabricating Portfolio Status

_P0 — Two EDUCATIONAL tweets claim "zero positions showing gains" and "portfolio at breakeven" when 3 positions are up 11-17%. This is a new type of fabrication — inventing negative data instead of fake tickers._

- [ ] **[4B.2.1]** P0 — Pass accurate portfolio stats to EDUCATIONAL prompts
  - File: `content/tweet_generator.py` → `_prepare_slot_data()` for EDUCATIONAL
  - Calculate and include:
    ```python
    profitable = [p for p in positions if p["current_price"] > p["entry_price"]]
    portfolio_stats = {
        "open_positions": len(positions),
        "profitable_count": len(profitable),
        "avg_gain_pct": round(mean([gain(p) for p in profitable]), 1),
        "losing_count": len(positions) - len(profitable),
    }
    ```
  - Pass to slot_data: `{"portfolio_stats": portfolio_stats, "themes": [...], ...}`

- [ ] **[4B.2.2]** P0 — Add anti-fabrication constraint to EDUCATIONAL prompt
  - File: `content/tweet_generator.py` → `_build_user_prompt()` for EDUCATIONAL
  - Append to prompt:
    ```
    PORTFOLIO CONTEXT (use these facts, do NOT invent different numbers):
    - {profitable_count} of {open_positions} positions currently profitable
    - Average gain on winners: {avg_gain_pct}%
    - Do NOT claim the portfolio has zero gains, is at breakeven, or is losing money
    ```

- [ ] **[4B.2.3]** P1 — Add portfolio-status validation to `_validate_tweet()`
  - For EDUCATIONAL tweets: if portfolio has profitable positions, flag tweets containing phrases like "zero gains", "no winners", "breakeven", "0 showing profit"
  - `failures.append("step_portfolio_fabrication: Claims no gains but portfolio has profitable positions")`

---

## Phase 4B.3 — WATCHLIST Using Wrong Data Source

_P1 — Both WATCHLIST tweets show $MATV which is a PASS signal. WATCHLIST should use CONSIDER signals — tickers that partially cleared the funnel but need confirmation._

- [ ] **[4B.3.1]** P1 — Fix WATCHLIST data routing in `_prepare_slot_data()`
  - WATCHLIST must pull from `data.consider_signals`, NOT `data.pass_signals`
  - If `data.consider_signals` is empty, return None (don't fall back to pass_signals)
  - Log: "WATCHLIST skipped — no CONSIDER signals available"

- [ ] **[4B.3.2]** P1 — Handle edge case: no CONSIDER signals available
  - In `_pick_category()`: only assign WATCHLIST if `data.has_consider_signals`
  - If WATCHLIST can't be assigned, fall back to THEME_ANALYSIS or EDUCATIONAL
  - Current output had 2 WATCHLIST tweets using wrong data — these slots should have been THEME_ANALYSIS or EDUCATIONAL instead

---

## Phase 4B.4 — TECHNICAL_ANALYSIS Not Generating

_P1 — Zero TA tweets despite having open positions with clear price levels. Likely being dropped by chart_required safety net since no holding-specific charts exist._

- [ ] **[4B.4.1]** P1 — Investigate why TECHNICAL_ANALYSIS produces no output
  - Check: is _pick_category() assigning TA slots?
  - Check: is _prepare_slot_data() returning data?
  - Check: are TA tweets being generated then dropped by chart_required filter?
  - Most likely cause: chart_required=true + no charts = all dropped

- [ ] **[4B.4.2]** P1 — Make chart_required conditional for TECHNICAL_ANALYSIS
  - If specific holding chart exists → chart_required=true, attach it
  - If no chart exists → chart_required=false, generate text-only TA tweet
  - Text-only TA format: "$WCC holding above $281 entry. Watching $320 resistance for breakout continuation. Setup invalidated below $256. NFA"
  - This allows TA tweets to appear even when chart capture hasn't run for that ticker

---

## Phase 4B.5 — Content Quality & Category Balance

_P1/P2 — EDUCATIONAL-heavy (5 of 17 tweets), no multi-ticker tweets, missing power phrases from style guide._

- [ ] **[4B.5.1]** P1 — Tighten EDUCATIONAL repetition limit
  - Current: max 5/week. Change to: max 3/week
  - Freed slots should go to PERFORMANCE (if gains exist) or TECHNICAL_ANALYSIS

- [ ] **[4B.5.2]** P1 — THEME_ANALYSIS should use portfolio tickers with gains, not just $MATV
  - Current: all THEME_ANALYSIS tweets reference $MATV (the scanner signal)
  - Fix: THEME_ANALYSIS data should primarily use portfolio holdings grouped by theme:
    ```
    Infrastructure theme running:
    $STRL at $401 (+11% from entry)
    $WCC at $315 (+12% from entry)
    ```
  - In `_prepare_slot_data()` for THEME_ANALYSIS: group portfolio holdings by theme, include entry/current/gain

- [ ] **[4B.5.3]** P2 — Add power phrase hooks to prompt instructions
  - In `_build_user_prompt()`, add to closing instructions for data-heavy categories:
    "End with one of: 'Probably want to save this post', 'Revisit this post soonish', 'Save this list', or similar bookmark CTA when the tweet contains 3+ tickers."

---

## Phase 4B.6 — Regenerate & Validate

- [ ] **[4B.6.1]** — Re-run `generate_weekly_content()` with current signals + portfolio data
- [ ] **[4B.6.2]** — Print generation summary: category distribution, ticker frequency, skipped slots, dropped tweets
- [ ] **[4B.6.3]** — Validate output against checklist:
  - [ ] ≥1 PERFORMANCE tweet with entry→current→% format
  - [ ] Zero EDUCATIONAL tweets claiming no gains / breakeven
  - [ ] WATCHLIST uses CONSIDER signals only (or absent if none exist)
  - [ ] ≥1 TECHNICAL_ANALYSIS tweet (text-only acceptable)
  - [ ] ≤3 EDUCATIONAL tweets
  - [ ] ≥1 THEME_ANALYSIS with portfolio holdings (not just scanner signal)
  - [ ] ≥6 categories represented

---

## Summary

| Area | P0 | P1 | P2 | Total |
|------|----|----|-----|-------|
| 4B.1 PERFORMANCE pipeline | 3 | 0 | 0 | 3 |
| 4B.2 EDUCATIONAL fabrication | 2 | 1 | 0 | 3 |
| 4B.3 WATCHLIST data source | 0 | 2 | 0 | 2 |
| 4B.4 TECHNICAL_ANALYSIS | 0 | 2 | 0 | 2 |
| 4B.5 Quality & balance | 0 | 2 | 1 | 3 |
| 4B.6 Regenerate | 0 | 0 | 0 | 3 |
| **Total** | **5** | **7** | **1** | **16** |

---

## Dependencies

```
[4B.1.1] ──→ [4B.1.2] ──→ [4B.1.3]   (debug → fix → schedule)
[4B.2.1] ──→ [4B.2.2] ──→ [4B.2.3]   (data → prompt → validation)
[4B.3.1] ──→ [4B.3.2]                  (fix routing → handle empty)
[4B.4.1] ──→ [4B.4.2]                  (debug → fix)
[4B.5.1] depends on [4B.1.3]           (freed EDUCATIONAL slots → PERFORMANCE)
[4B.5.2] independent
ALL ──→ [4B.6]                          (regenerate after all fixes)
```
