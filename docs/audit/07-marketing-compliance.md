# Audit 07: Marketing Compliance System

**Scope:** All marketing rules, vocabulary enforcement, position filtering safeguards, and compliance validation across all public-facing content outputs.

**Files Audited:**
- `config.py` (lines 262-911) — Marketing thresholds, banned terms, approved terms, helper functions
- `marketing_vocabulary.py` (341 lines) — Vocabulary validation, power phrases, audience hooks
- `signal_tracker.py` (lines 690-1061) — Position filtering, cold streak detection, showcase selection
- `twitter_poster.py` (lines 95-162) — Pre-post validation (last line of defense)
- `tweet_generator.py` — Generation-time validation (8 checks)
- `newsletter_compiler.py` — Newsletter validation (warning-only)
- `substack_notes_generator.py` — Substack notes filtering
- `substack_content_generator.py` — Substack post filtering

---

## Table of Contents

1. [Complete Marketing Rules Inventory](#1-complete-marketing-rules-inventory)
2. [Banned Terms System](#2-banned-terms-system)
3. [Approved Vocabulary & Branding](#3-approved-vocabulary--branding)
4. [Position Filtering Safeguards](#4-position-filtering-safeguards)
5. [High Performer Selection Algorithm](#5-high-performer-selection-algorithm)
6. [Cold Streak Circuit Breaker](#6-cold-streak-circuit-breaker)
7. [Validation Architecture](#7-validation-architecture)
8. [Gaps & Inconsistencies](#8-gaps--inconsistencies)
9. [Compliance Checklist](#9-compliance-checklist)
10. [Concerns](#10-concerns)

---

## 1. Complete Marketing Rules Inventory

### 1.1 Performance Thresholds (`config.py:266-288`)

| Key | Value | Purpose |
|-----|-------|---------|
| `min_win_to_highlight` | 15.0% | Minimum gain to include in top_performers |
| `big_win_threshold` | 25.0% | Trigger standalone milestone tweet |
| `home_run_threshold` | 50.0% | Celebration post, pin candidate |
| `hall_of_fame_threshold` | 100.0% | Thread-worthy, repeated reference |
| `spy_outperformance_min` | 5.0% | Must beat SPY by this to use beat_spy content |
| `min_winners_for_top_performers` | 2 | Need >= 2 winners at 15%+ to post top_performers |
| `max_loss_to_mention` | -5.0% | Never mention positions worse than this |
| `cold_streak_threshold` | 3 | Number of losses to trigger cold streak |
| `cold_streak_lookback_days` | 14 | Days to look back for losses |
| `max_ticker_mentions_per_week` | 4 | Prevent engagement fatigue |

### 1.2 Ticker Frequency Limits (`config.py:47-51`)

| Rule | Value |
|------|-------|
| Max mentions per week | 4 |
| Max consecutive days | 2 |
| Cooldown after milestone | 2 days |

### 1.3 Stopped Position Rules (`config.py:776-783`)

All six rules set to suppress stopped positions from any public content:

| Rule | Value |
|------|-------|
| `show_in_public_content` | **False** |
| `show_in_newsletter` | **False** |
| `show_in_top_performers` | **False** |
| `show_in_any_tweet` | **False** |
| `internal_tracking` | True (internal only) |
| `mention_discipline_publicly` | **False** |

### 1.4 Entry Price Display Rules (`config.py:625-629`)

| Rule | Value |
|------|-------|
| Show for closed winners | Yes (always) |
| Show for open positions | Only if P&L >= 25.0% |
| Below threshold | Entry price hidden |

Implementation at `config.py:680-704` (`can_show_entry_price()`):
- Closed winners (`status == 'CLOSED' and pnl_pct > 0`): always show
- Open positions (`status == 'OPEN' and pnl_pct >= 25.0`): show
- All other cases: hide

### 1.5 Signal Visibility Rules (`config.py:335-366`)

| Signal Type | Public Name | Show Publicly |
|-------------|-------------|---------------|
| PASS | TEAL Signal | Yes |
| CONSIDER | On Our Radar | Yes |
| WATCHLIST | *(none)* | No |
| CAUTION | *(none)* | No |
| EXIT | *(none)* | No |

### 1.6 Conviction Language (`config.py:617-623`)

| Score | Public Text |
|-------|-------------|
| 5 | Extremely Bullish |
| 4 | Bullish |
| 3 | Watching |
| 2 | Cautious |
| 1 | *(do not post publicly)* |

### 1.7 Killed Categories (`config.py:58-64`)

Categories permanently disabled:

| Category | Reason |
|----------|--------|
| `roth_ira` | Wrong audience |
| `pdt_friendly` | Wrong audience |
| `position_update` | Shows individual P&L — merged to top_performers |
| `weekly_wins` | Renamed to top_performers (misleading terminology) |
| `self_quote` | Renamed to milestone_alerts |

### 1.8 Safeguarded Categories (`config.py:301-306`)

Categories that require passing a safeguard check before generation:

| Category | Safeguard Function | Fallback |
|----------|-------------------|----------|
| `top_performers` | `has_enough_wins` | `theme_hot` |
| `beat_spy` | `should_post_beat_spy` | `engagement` |
| `self_quote` | `has_uncelebrated_wins` | `consider_spotlight` |
| `closed_trade` | `has_winning_closed_trades` | `educational` |

### 1.9 Age-Based Highlight Thresholds (`config.py:826-848`)

| Days Held | Min P&L to Highlight |
|-----------|---------------------|
| 0-7 | 3.0% |
| 8-14 | 5.0% |
| 15-30 | 10.0% |
| 31-60 | 15.0% |
| 60+ | 20.0% |

### 1.10 Timeframe Disclaimers (`config.py:769-773`)

Three disclaimer lengths available:
- **Short:** "Returns since signal entry."
- **Medium:** "Total gain since entry, not weekly movement."
- **Long:** "Sterling Signals targets 50-100% returns over 3-8 month holds. Returns shown are total since signal entry."

---

## 2. Banned Terms System

### 2.1 Two Separate Banned Term Lists

**CRITICAL FINDING:** There are two independent banned term lists that are NOT synchronized.

#### `config.py:373-410` — 40 terms across 7 categories

```
Strategy internals:  HMA, Hull Moving Average, HMA Pivot, Banker indicator,
                     Banker >= 55, Banker score, 20% trailing stop, 20% stop,
                     Beta >= 1.5, Break of Structure, BoS, BOS,
                     Tier 1, Tier 2, Tier 3, Gatekeeper

Geographic:          UK ISA, ISA account, GMT, BST, UK Time

Branding:            PASS signal, weekly winners, this week we nailed

Technical:           RSI, MACD, KDJ

Leaked internals:    Capital Preservation Protocol, Forensic Audit,
                     Volatility Expansion Criteria, 5th Gate, Gate 5

Non-branded signals: buy signal, proprietary entry, proprietary signal

US-specific:         Roth IRA, Roth, PDT, PDT rule, pattern day trader,
                     401k, 401(k)
```

#### `marketing_vocabulary.py:25-65` — 45 terms (superset)

Additional terms not in `config.py`:
- `Banker ≥ 55` (unicode variant)
- `Beta ≥ 1.5` (unicode variant)
- `HMA pivot` (lowercase variant)
- `banker indicator` (lowercase variant)
- `Banker >=` (partial match)
- `Beta >=` (partial match)
- `Weekly BoS`, `weekly bos`, `Weekly pivot`
- `ISA wrapper`, `Barclays ISA`
- `UK investor(s)`, `UK trader(s)`, `UK time`, `London time`, `GBP/USD`
- `Buy signal`, `BUY SIGNAL` (case variants)
- `conviction 5/4/3`, `conviction score`, `conviction rating`
- `TIER1`, `TIER2`, `TIER3` (no-space variants)

### 2.2 Validation Differences

| Aspect | `config.py` `contains_banned_term()` | `marketing_vocabulary.py` `validate_content()` |
|--------|--------------------------------------|-----------------------------------------------|
| **Location** | `config.py:898-911` | `marketing_vocabulary.py:166-203` |
| **Term count** | 40 | 45 |
| **Method** | Substring match (case-insensitive) | Substring + word boundary for short terms |
| **Short term handling** | None — substring only | 7 terms use `\b` regex: RSI, MACD, KDJ, BoS, BOS, GMT, BST |
| **Return type** | `bool` | `Tuple[bool, List[str]]` (includes violation list) |
| **Deduplication** | None | Yes (preserves order) |

### 2.3 Third Hardcoded List in `twitter_poster.py:115-125`

The pre-post validation uses a **hardcoded subset of only 13 terms**:

```
HMA, 20% stop, Banker >=, Beta >=, BoS,
Roth IRA, Roth, PDT, 401k,
Capital Preservation Protocol, Forensic Audit,
Volatility Expansion Criteria, 5th Gate, Gate 5,
proprietary entry, proprietary signal
```

**Missing from this critical last-line-of-defense check:**
- All geographic terms (UK ISA, GMT, BST, etc.)
- Technical indicators (RSI, MACD, KDJ)
- Branding terms (PASS signal, weekly winners)
- Hull Moving Average, Break of Structure (long forms)
- Tier 1/2/3, Gatekeeper
- All `marketing_vocabulary.py`-only terms

---

## 3. Approved Vocabulary & Branding

### 3.1 Internal-to-Public Vocabulary Mapping (`marketing_vocabulary.py:71-94`)

| Internal Term | Approved Public Term |
|---------------|---------------------|
| HMA Pivot | momentum confirmed |
| Banker indicator | strong accumulation |
| Beta >= 1.5 | volatility characteristics |
| 20% trailing stop | trailing stop |
| Weekly BoS | momentum confirmed |
| Gatekeeper | cleared all gates |
| Tier 1/2/3 | high conviction |
| Theme scoring | theme alignment |
| buy signal | TEAL signal |
| PASS signal | TEAL signal |

### 3.2 TEAL Branding Enforcement (`config.py:444-469`)

`enforce_teal_branding()` performs 10 text replacements:

| From | To |
|------|-----|
| buy signal | TEAL signal |
| Buy signal | TEAL signal |
| BUY SIGNAL | TEAL SIGNAL |
| proprietary entry | TEAL signal |
| proprietary signal | TEAL signal |
| our signal | TEAL signal |
| new signal | TEAL signal |
| passes our criteria | triggers a TEAL signal |
| cleared our system | triggers a TEAL signal |
| PASS signal | TEAL signal |

### 3.3 Signal Color System (`config.py:596-615`)

| Color | Emoji | Meaning | Internal Status | Public Name |
|-------|-------|---------|-----------------|-------------|
| TEAL | 🟢 | BUY | PASS | TEAL Signal |
| VIOLET | 🟣 | EXIT | STOPPED | Exit Alert |
| AMBER | 🟠 | WATCH | CONSIDER | On Our Radar |

### 3.4 Power Phrases (`marketing_vocabulary.py:100-126`)

13 approved phrases across 3 categories:
- **System description** (4): "Proprietary 5-gate screening system", "Filters 1,800 stocks to 3-5 actionable signals", etc.
- **Signal detection** (5): "TEAL signal triggered", "Cleared all 5 gates", etc.
- **Risk management** (4): "Systematic exit discipline", "Trailing stop in place", etc.

### 3.5 Audience Hooks (`marketing_vocabulary.py:132-157`)

4 categories × 4 hooks = 16 approved phrases:
- `beat_spy` — Alpha over indexing messaging
- `time_friendly` — Weekly timeframe for busy schedules
- `power_hour` — Market close / volume confirmation
- `sector_rotation` — Institutional flow following

---

## 4. Position Filtering Safeguards

### 4.1 `filter_public_positions()` (`signal_tracker.py:690-741`)

The primary filter for all public content:

1. **STOPPED positions removed** — `status == 'STOPPED'` skipped entirely
2. **Negative P&L removed** — Only `pnl_pct >= 0` included
3. **Price fetching** — If `pnl_pct` not pre-calculated, fetches current prices via yfinance
4. **Sort descending** — Best performers first

### 4.2 `has_enough_wins()` (`signal_tracker.py:615-658`)

Gate for `top_performers` category:
- Loads open positions from portfolio
- Requires >= 2 positions with P&L >= 15%
- If fewer than 2 winners, falls back to `theme_hot`

### 4.3 `should_post_beat_spy()` (`signal_tracker.py:609-612`)

Gate for `beat_spy` category:
- Delegates to `calculate_portfolio_vs_spy()` or `calculate_fair_spy_comparison()`
- SPY comparison uses matched holding periods (`SPY_COMPARISON_METHOD = 'matched_period'`)
- Must outperform SPY by >= 5%

### 4.4 `get_winners_for_showcase()` (`signal_tracker.py:751-812`)

For public showcase content:
- Threshold: >= 25% P&L
- Max 5 positions returned
- Entry price rules applied via `can_show_entry_price()`
- Calculates days held for holding period display
- Sorted by P&L descending

### 4.5 Negative P&L Regex Check (`twitter_poster.py:131-133`)

Pre-post validation blocks any tweet containing negative P&L patterns:
```python
negative_pnl = re.findall(r'-\d+\.?\d*%', text)
if negative_pnl:
    return (False, f"BLOCKED: Negative P&L in tweet: {negative_pnl}")
```

---

## 5. High Performer Selection Algorithm

### 5.1 Selection Flow

```
Portfolio CSV
  ↓
filter_public_positions()
  ├── Remove STOPPED positions
  ├── Remove negative P&L
  └── Sort by P&L descending
  ↓
get_winners_for_showcase(threshold=25.0, max=5)
  ├── Filter to >= 25% P&L
  ├── Apply entry price display rules
  │   ├── Closed winners: always show entry
  │   ├── Open >= 25%: show entry
  │   └── Open < 25%: hide entry
  ├── Calculate days held
  └── Return top 5 by P&L
```

### 5.2 Celebration/Milestone Tiers (`config.py:711-730`)

| Tier | Threshold | Emoji | Headline |
|------|-----------|-------|----------|
| Standard | 25% | 📈 | MILESTONE ALERT |
| Home Run | 50% | 🚀 | HOME RUN |
| Hall of Fame | 100% | 🏆 | HALL OF FAME |

Celebrations tracked in `trades/celebrations.json` to avoid duplicate posts. Keys: `25_pct_celebrated`, `50_pct_celebrated`, `100_pct_celebrated`.

### 5.3 Win Categories (`config.py:738-766`)

| Category | Description | Threshold | Frequency |
|----------|-------------|-----------|-----------|
| `top_performers` | Best open positions by total return | 15% | Weekly |
| `early_movers` | New signals (< 14 days) showing strength | 5% | When available |
| `milestone_alerts` | Positions crossing 25%/50%/100% | Varies | When crossed |
| `recent_wins` | Closed in profit within 14 days | 15% | When available |

---

## 6. Cold Streak Circuit Breaker

### 6.1 Detection (`signal_tracker.py:988-1061`)

**Trigger:** >= 3 losses in the most recent 3 closed trades within 14 days.

**Algorithm:**
1. Load closed trades from portfolio
2. Filter to exits within lookback period (14 days)
3. Sort by exit date (most recent first)
4. Count losses in the most recent N trades (N = threshold)
5. If losses >= threshold → cold streak active

**Output:** Dict with `in_cold_streak`, `recent_losses`, `consecutive_losses`, `win_rate`, `should_reduce_posting`, `reason`.

### 6.2 Effect on Content

When `in_cold_streak == True`:
- `beat_spy` category suppressed → falls back to `engagement`
- `top_performers` category suppressed → falls back to `theme_hot`
- `milestone_alerts` suppressed → falls back to `consider_spotlight`
- Posting frequency recommendations reduced

---

## 7. Validation Architecture

### 7.1 Four-Layer Validation Pipeline

```
LAYER 1: CONFIG (config.py)
  └── Banned terms, thresholds, killed categories defined

LAYER 2: GENERATION (tweet_generator.py)
  └── 8 checks at tweet creation time:
      1. Banned terms (imports from config.py)
      2. TEAL branding enforcement
      3. Character count <= 280
      4. Killed category rejection
      5. Safeguard function checks
      6. Negative P&L filtering
      7. Ticker frequency limits
      8. Entry price display rules

LAYER 3: BATCH (marketing_vocabulary.py)
  └── validate_all_tweets() — batch check of entire queue
      Uses marketing_vocabulary.py BANNED_TERMS (45 terms)
      Word boundary matching for short terms

LAYER 4: POSTING (twitter_poster.py)
  └── validate_before_posting() — 5 checks:
      1. Negative P&L regex
      2. Hardcoded 13-term banned check ← GAP
      3. Killed category check (4 of 5 categories)
      4. US-specific regex patterns
      5. Character count
```

### 7.2 Newsletter Validation

`newsletter_compiler.py` (lines 878-886):
- Calls `validate_content()` from `marketing_vocabulary.py`
- **WARNING-only** — does not block publication
- Relies on LLM system prompt compliance for loss suppression (no programmatic enforcement)

### 7.3 Substack Notes Validation

`substack_notes_generator.py`:
- Filters to positions >= 15% P&L (safe by design)
- No explicit banned term check (relies on LLM prompt compliance)

### 7.4 Substack Content Validation

`substack_content_generator.py`:
- Entry price shown only for positions >= 25% gain
- No explicit banned term check (relies on LLM prompt compliance)

---

## 8. Gaps & Inconsistencies

### GAP-1: Divergent Banned Term Lists (HIGH)

Three independent lists with different term counts:
- `config.py`: 40 terms
- `marketing_vocabulary.py`: 45 terms
- `twitter_poster.py`: 13 terms (hardcoded)

`twitter_poster.py` is the **last line of defense** but has the fewest terms. A term like "RSI" or "PASS signal" could pass through if the generation-time check missed it.

### GAP-2: No P&L Re-verification at Posting Time (HIGH)

Tweets are generated on Friday with snapshot P&L data. They post throughout the following week. A position that was +30% on Friday could be -5% by Wednesday. The tweet still shows +30%. There is no re-verification of P&L at posting time.

### GAP-3: Newsletter Loss Suppression is LLM-Only (HIGH)

The newsletter compiler relies entirely on the LLM system prompt to suppress losses. There is no programmatic check that the rendered HTML excludes losing positions. A single LLM compliance failure could expose loss data in a published newsletter.

### GAP-4: `contains_banned_term()` in config.py Lacks Word Boundaries (MEDIUM)

`config.py:898-911` uses pure substring matching. The term "BoS" would match "Bostonian" or "emboss". `marketing_vocabulary.py` correctly uses word boundary regex for short terms, but `config.py` does not.

### GAP-5: Self-Test False Expectations (`marketing_vocabulary.py:377-391`) (LOW)

Two test cases appear to have inverted expected values:
- `"Roth IRA compounding strategy"` → expected `True` (valid), but "Roth IRA" and "Roth" are both banned
- `"The 5th Gate: Forensic Audit cleared"` → expected `True` (valid), but "5th Gate" and "Forensic Audit" are both banned

### GAP-6: `twitter_poster.py` Killed Categories Missing `self_quote` (LOW)

The hardcoded `KILLED_CATEGORIES` in `twitter_poster.py:128` lists 4 categories but config.py lists 5 (missing `self_quote`). Minor since `self_quote` was renamed to `milestone_alerts`.

### GAP-7: `trailing stop` is Banned in marketing_vocabulary.py but Approved in config.py (MEDIUM)

- `marketing_vocabulary.py:29` bans `"trailing stop"` (full string)
- `config.py` APPROVED_TERMS `'risk'` list includes `"trailing stop"` as approved
- `marketing_vocabulary.py` APPROVED_VOCABULARY maps "20% trailing stop" → "trailing stop"

This creates a contradiction: "trailing stop" is both an approved replacement AND a banned term.

### GAP-8: No Validation on Multi-Account Variations (MEDIUM)

`tweet_generator.py --generate-variations` produces variation tweets for accounts 2 and 3 via LLM rephrasing. These variations may not pass through the same validation pipeline as the original tweets. The LLM could introduce banned terms in rephrased versions.

---

## 9. Compliance Checklist

### Pre-Publication Checklist (Run Before Any Public Post)

#### A. Content Validation

- [ ] **A1.** Run `validate_content()` from `marketing_vocabulary.py` against all text — zero violations
- [ ] **A2.** Verify no negative P&L values appear anywhere in content (regex: `-\d+\.?\d*%`)
- [ ] **A3.** Verify no stopped positions appear in any public-facing section
- [ ] **A4.** Verify "TEAL signal" used instead of "buy signal", "PASS signal", "proprietary signal"
- [ ] **A5.** Verify no killed category content present (roth_ira, pdt_friendly, position_update, weekly_wins, self_quote)

#### B. Position Data Integrity

- [ ] **B1.** All P&L figures are current (not stale from generation time)
- [ ] **B2.** Entry prices shown only for closed winners OR open positions >= 25%
- [ ] **B3.** No STOPPED positions included in any showcase, top performers, or position list
- [ ] **B4.** SPY comparison uses matched holding periods (not 30-day or YTD)
- [ ] **B5.** At least 2 winners at >= 15% before posting `top_performers` content

#### C. Banned Term Scan

- [ ] **C1.** No strategy internals: HMA, Banker, Beta >= 1.5, BoS, Gatekeeper, Tier 1/2/3
- [ ] **C2.** No geographic leaks: UK ISA, GMT, BST, UK Time, London time, GBP/USD
- [ ] **C3.** No technical indicators: RSI, MACD, KDJ
- [ ] **C4.** No leaked internal marketing terms: Capital Preservation Protocol, Forensic Audit, Volatility Expansion Criteria, 5th Gate, Gate 5
- [ ] **C5.** No non-branded signal terms: buy signal, proprietary entry, proprietary signal, PASS signal
- [ ] **C6.** No US-specific terms: Roth IRA, Roth, PDT, 401k, 401(k), pattern day trader
- [ ] **C7.** No conviction score references: conviction 5/4/3, conviction score, conviction rating

#### D. Branding & Formatting

- [ ] **D1.** TEAL branding applied to all signal references
- [ ] **D2.** Signal color emoji matches signal type (🟢 TEAL, 🟣 VIOLET, 🟠 AMBER)
- [ ] **D3.** Conviction scores expressed as language (Extremely Bullish, Bullish, etc.) not numbers
- [ ] **D4.** Timeframe disclaimer present where returns are mentioned
- [ ] **D5.** Tweet character count <= 280

#### E. Cold Streak Check

- [ ] **E1.** Run `check_cold_streak()` — if active, suppress beat_spy, top_performers, milestone content
- [ ] **E2.** Verify ticker mention frequency <= 4/week per ticker

#### F. Newsletter-Specific

- [ ] **F1.** Newsletter HTML does not contain any losing positions in showcase sections
- [ ] **F2.** Newsletter disclaimer present
- [ ] **F3.** All chart placeholders have corresponding images
- [ ] **F4.** Performance summary matches portfolio.csv source data

---

## 10. Concerns

| ID | Severity | Description |
|----|----------|-------------|
| C-1 | **HIGH** | Three divergent banned term lists (config: 40, vocabulary: 45, poster: 13). `twitter_poster.py` last-line-of-defense uses hardcoded subset of only 13 terms. Should import from `marketing_vocabulary.py`. |
| C-2 | **HIGH** | No P&L re-verification at posting time. Stale data from Friday generation could show inaccurate gains for tweets posted Monday-Thursday. |
| C-3 | **HIGH** | Newsletter loss suppression relies entirely on LLM prompt compliance with no programmatic enforcement. |
| C-4 | **MEDIUM** | `"trailing stop"` is simultaneously banned (marketing_vocabulary.py:29) and approved (config.py APPROVED_TERMS). Contradictory rules. |
| C-5 | **MEDIUM** | `config.py:contains_banned_term()` uses substring matching without word boundaries, risking false positives for short terms (BoS, RSI, BST). |
| C-6 | **MEDIUM** | Multi-account tweet variations not validated through the same pipeline as original tweets. LLM rephrasing could introduce banned terms. |
| C-7 | **LOW** | Self-test in `marketing_vocabulary.py:377-391` has 2 test cases with likely inverted expected values (Roth IRA and 5th Gate tests expect valid=True but contain banned terms). |
| C-8 | **LOW** | `twitter_poster.py` killed categories list missing `self_quote` (has 4 of 5 from config.py). |

---

*Generated: 2026-01-29 | Auditor: Claude Code*
