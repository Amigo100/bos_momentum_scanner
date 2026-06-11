# Sterling Signals System Improvement Reference
## Comprehensive Marketing & Technical Overhaul

**Document Version:** 1.0  
**Created:** January 27, 2026  
**Purpose:** Define all improvements needed to align Sterling Signals with competitive best practices

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [New Brand Signal Language](#2-new-brand-signal-language)
3. [Substack Content Restructure](#3-substack-content-restructure)
4. [Twitter/X Marketing Improvements](#4-twitterx-marketing-improvements)
5. [Technical System Updates](#5-technical-system-updates)
6. [Codebase Cleanup Inventory](#6-codebase-cleanup-inventory)
7. [Marketing Compliance Updates](#7-marketing-compliance-updates)
8. [Implementation Priorities](#8-implementation-priorities)

---

# 1. Executive Summary

## 1.1 Current State vs Target State

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| **Substack frequency** | 1x/week (Saturday) | 3-4x/week |
| **Signal language** | "TEAL signal" (text only) | 🟢 TEAL / 🟣 VIOLET color system |
| **Entry price visibility** | Hidden completely | Shown for winners >25% |
| **Weekly win tracking** | Not systematically generated | Automated high-engagement format |
| **SPY benchmark comparison** | Exists but buried | Prominent "Meanwhile SPY..." format |
| **Watchlist format** | CONSIDER signals (internal) | "$TICKER at $XX.XX" public drops |
| **Self-quote amplification** | None | Systematic thread building |
| **Conviction language** | Internal 1-5 scale | Public: "Extremely Bullish" / "Bullish" / "Watching" |

## 1.2 Key Strategic Shifts

### From → To

```
Internal terminology     →  Consumer-facing color system
Weekly newsletter dump   →  Distributed daily content
Hidden performance data  →  Showcased winner tracking
Passive content          →  Engagement-optimized formats
Complex methodology      →  Simple "5 Gates" messaging
```

## 1.3 Success Metrics

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| Substack posts/week | 1 | 3-4 |
| X followers | ? | +50% |
| Substack subscribers | ? | +100% |
| Engagement per tweet | ? | 2x average |
| Self-quote thread length | 0 | 10+ validated calls |

---

# 2. New Brand Signal Language

## 2.1 Color Signal System

### Primary Signals

| Signal | Color | Emoji | Meaning | Internal Mapping |
|--------|-------|-------|---------|------------------|
| **TEAL** | Teal/Cyan | 🟢 | BUY - All 5 gates cleared | `final_decision = "PASS"` |
| **VIOLET** | Purple/Violet | 🟣 | EXIT - Sell signal triggered | `status = "STOPPED"` or BoS DOWN |
| **AMBER** | Orange/Amber | 🟠 | WATCH - On radar, not yet qualified | `final_decision = "CONSIDER"` |

### Visual Identity

```
🟢 TEAL SIGNAL  = Entry opportunity (5 gates cleared)
🟣 VIOLET ALERT = Exit triggered (trailing stop or BoS down)
🟠 AMBER WATCH  = Monitoring closely (4/5 gates, watchlist)
```

### Tagline Options (Choose One)

| Option | Tagline |
|--------|---------|
| A | **"5 Gates. TEAL Signals. Beat the Market."** |
| B | **"🟢 TEAL = Buy. 🟣 VIOLET = Sell. Systematic edge."** |
| C | **"From 1,800 stocks to 5 signals. Every week."** |

**Recommendation:** Option A for bio/header, Option B for signal posts, Option C for funnel graphics.

## 2.2 Conviction Language Mapping

| Internal Score | Public Language | Usage |
|----------------|-----------------|-------|
| 5 | **"Extremely Bullish"** | "We're extremely bullish on $TICKER" |
| 4 | **"Bullish"** | "Bullish setup forming on $TICKER" |
| 3 | **"Watching"** | "Watching $TICKER closely" |
| 2 | **"Cautious"** | "Cautious on $TICKER - risk factors present" |
| 1 | **"Avoiding"** | Do not post publicly |

## 2.3 Benchmark Comparison Language

### Standard Format
```
Meanwhile... S&P 500: +X.X%

Our TEAL signals:
$TICKER1: +XX.X%
$TICKER2: +XX.X%
$TICKER3: +XX.X%

Alpha generated: +XX.X%
```

### When Underperforming SPY
Do not post benchmark comparisons. Use theme/educational content instead.

---

# 3. Substack Content Restructure

## 3.1 New Weekly Calendar

| Day | Content Type | Title Format | Source |
|-----|--------------|--------------|--------|
| **Monday** | Market Analysis | "Market Outlook: [Week of Date]" | `market_analyzer.py` |
| **Wednesday** | Theme Spotlight | "Theme Watch: [Hot Theme Name]" | `signals.json` themes |
| **Saturday** | Signals & Watchlist | "TEAL Signals: [Date] + Watchlist" | `signals.json` |
| **Sunday** (optional) | Deep Dive | "Deep Dive: $TICKER" | Top TEAL signal |

### Alternative 3-Post Schedule

| Day | Content Type | Notes |
|-----|--------------|-------|
| **Monday** | Market Analysis | Market context + theme preview |
| **Thursday** | Theme Deep Dive | Hot theme + related tickers |
| **Saturday** | Signals + Watchlist | New TEAL signals, VIOLET exits, AMBER watchlist |

## 3.2 Substack Post Templates

### Template 1: Market Analysis (Monday)

```markdown
# Market Outlook: Week of [DATE]

## The Big Picture

[2-3 paragraphs on market conditions]

## Where Money Is Flowing

🔥 **Hot Themes:**
- [Theme 1]: [Brief reason]
- [Theme 2]: [Brief reason]

❄️ **Cooling Off:**
- [Theme 1]: [Brief reason]

## Key Levels to Watch

- **S&P 500:** [Level] support, [Level] resistance
- **VIX:** [Level] - [interpretation]

## Our Stance: [BULLISH / CAUTIOUS / DEFENSIVE]

[1 paragraph explaining positioning]

---

## 🟢 Top Performers Update

Our TEAL signals continue to outperform:

| Ticker | Entry | Current | Return | Days Held |
|--------|-------|---------|--------|-----------|
| $XXX | $XX.XX | $XX.XX | +XX.X% | XX |
| $XXX | $XX.XX | $XX.XX | +XX.X% | XX |

Meanwhile... S&P 500: +X.X% over same period.

---

*Want the full signal list? [Become a paid subscriber](#)*
```

### Template 2: Theme Spotlight (Wednesday/Thursday)

```markdown
# Theme Watch: [THEME NAME]

## Why This Theme Matters Now

[2-3 paragraphs on theme thesis]

## The Catalysts

1. **[Catalyst 1]:** [Explanation]
2. **[Catalyst 2]:** [Explanation]
3. **[Catalyst 3]:** [Explanation]

## Theme Score: [X.X/10] — [PRIME/INVESTABLE/SELECTIVE]

## Stocks in This Theme

### 🟢 TEAL Signals (Cleared All 5 Gates)
- **$TICKER1** — [One-line thesis]
- **$TICKER2** — [One-line thesis]

### 🟠 AMBER Watch (Monitoring)
- **$TICKER3** at $XX.XX — Watching for [catalyst]
- **$TICKER4** at $XX.XX — Needs [condition]

## What Could Go Wrong

[1-2 paragraphs on risks]

---

*Full analysis and entry timing available to paid subscribers.*
```

### Template 3: Weekly Signals (Saturday)

```markdown
# TEAL Signals: Week of [DATE]

## This Week's Scan Results

📊 **1,817 stocks scanned**
⚡ **485** showed momentum characteristics
📈 **48** confirmed institutional accumulation
🔥 **17** aligned with hot themes
✅ **[X] TEAL signals** — Cleared all 5 gates

---

## 🟢 NEW TEAL SIGNALS

### $TICKER1 — [Theme]

**Conviction: [Extremely Bullish/Bullish]**

| Metric | Value |
|--------|-------|
| Entry Price | $XX.XX |
| Theme | [Theme Name] |
| Theme Score | X.X/10 |

**Why We're Bullish:**
- [Bullet 1]
- [Bullet 2]
- [Bullet 3]

**Risk Factors:**
- [Bullet 1]
- [Bullet 2]

[CHART]

---

### $TICKER2 — [Theme]

[Same format...]

---

## 🟣 VIOLET ALERTS (Exit Signals)

[If any sell signals triggered this week]

| Ticker | Entry | Exit | Return | Reason |
|--------|-------|------|--------|--------|
| $XXX | $XX.XX | $XX.XX | +XX.X% | Trailing stop hit |

---

## 🟠 AMBER WATCHLIST

Stocks that cleared 4/5 gates — watching for final confirmation:

| Ticker | Price | Theme | Missing Gate |
|--------|-------|-------|--------------|
| $XXX | $XX.XX | [Theme] | [What's needed] |
| $XXX | $XX.XX | [Theme] | [What's needed] |

---

## 📈 PORTFOLIO UPDATE: Winners Over 25%

| Ticker | Entry | Current | Return | Held |
|--------|-------|---------|--------|------|
| $XXX | $XX.XX | $XX.XX | +XX.X% | X weeks |
| $XXX | $XX.XX | $XX.XX | +XX.X% | X weeks |

**Meanwhile... S&P 500: +X.X%**

---

*This is our free weekly summary. Paid subscribers get real-time alerts, full thesis documents, and position sizing guidance.*
```

### Template 4: Deep Dive (Sunday, Optional)

```markdown
# Deep Dive: $TICKER

## The Setup

[CHART - Weekly timeframe showing signal]

**TEAL Signal Date:** [Date]
**Entry Price:** $XX.XX
**Current Price:** $XX.XX
**Conviction:** [Extremely Bullish/Bullish]

---

## Why $TICKER Cleared All 5 Gates

### Gate 1: Volatility Screening ✅
Beta: X.XX — Stock amplifies market moves, ideal for momentum.

### Gate 2: Structural Pivot Confirmation ✅
Weekly HMA pivot formed — buyers stepping in at higher lows.

### Gate 3: Institutional Accumulation ✅
Banker Score: XX — Trading X% above 20-day VWAP indicates accumulation.

### Gate 4: Theme Momentum ✅
Theme: [Theme Name] — Score X.X/10 (PRIME)
[Theme thesis paragraph]

### Gate 5: Catalyst Verification ✅
- [Catalyst 1]
- [Catalyst 2]
- No red flags identified

---

## The Bull Case

[2-3 paragraphs]

## The Bear Case

[1-2 paragraphs]

## Risk Management

- **Trailing Stop:** 20% from highest close
- **Current Stop Level:** $XX.XX
- **Risk/Reward:** X:1

---

## Our Take

[Concluding paragraph with conviction statement]

---

*Want signals like this every week? [Subscribe to Sterling Signals](#)*
```

## 3.3 File Generation Requirements

Each Substack post should be generated as an HTML file in a new directory:

```
trades/
└── substack_posts/
    ├── monday_market_analysis.html
    ├── thursday_theme_spotlight.html
    ├── saturday_weekly_signals.html
    └── sunday_deep_dive.html  (optional)
```

### New Script Required: `substack_content_generator.py`

**Functions needed:**
- `generate_monday_market_analysis()` → HTML file
- `generate_theme_spotlight()` → HTML file
- `generate_weekly_signals()` → HTML file
- `generate_deep_dive(ticker)` → HTML file

**Data sources:**
- Market analysis: `market_analyzer.py` output + Claude
- Theme spotlight: `signals.json` → themes array
- Weekly signals: `signals.json` → buy_signals, consider_signals
- Deep dive: `signals.json` → top PASS signal with highest conviction

---

# 4. Twitter/X Marketing Improvements

## 4.1 New Content Categories

### Category Overhaul

| OLD Category | NEW Category | Purpose | Frequency |
|--------------|--------------|---------|-----------|
| `buy_signal` | `teal_signal` | Announce new TEAL signals | Post-scan |
| `consider_spotlight` | `amber_watch` | Watchlist teasers | 2-3x/week |
| `top_performers` | `winner_showcase` | 25%+ gains with entry prices | 1-2x/week |
| `beat_spy` | `benchmark_alpha` | SPY comparison | 1x/week (when winning) |
| `milestone_alerts` | `hall_of_fame` | 50%+ / 100%+ wins | As achieved |
| NEW | `violet_alert` | Exit signals | As triggered |
| NEW | `self_quote` | Quote past correct calls | When validated |
| NEW | `weekly_recap` | Week's performance summary | Saturday |

## 4.2 High-Engagement Tweet Formats

### Format 1: Weekly Recap (Highest Engagement)

```
🟢 TEAL signals this week:

$TICKER1 — Extremely Bullish
$TICKER2 — Bullish
$TICKER3 — Bullish

Meanwhile... S&P 500: +X.X%

Our 5-Gate System continues to find asymmetric setups.

Full analysis 👇
sterlingsignals.substack.com
```

### Format 2: Winner Showcase (25%+ Returns)

```
One proper swing can change your portfolio.

Recent TEAL signal performance:

$TICKER1: $XX.XX → $XX.XX (+XX.X%)
$TICKER2: $XX.XX → $XX.XX (+XX.X%)
$TICKER3: $XX.XX → $XX.XX (+XX.X%)

Meanwhile... S&P 500: +X.X%

This is what 5 gates of screening delivers.

sterlingsignals.substack.com
```

### Format 3: Self-Quote Thread Building

**Step 1: Original Signal Post**
```
🟢 TEAL Signal: $TICKER

Entry: $XX.XX
Theme: [Theme Name]
Conviction: Extremely Bullish

5 gates cleared. Full analysis 👇
sterlingsignals.substack.com
```

**Step 2: Quote-Tweet When Validated (25%+ gain)**
```
🟢 $TICKER update: +XX.X% from TEAL signal

From $XX.XX → $XX.XX

This is why we built a 5-gate system.

[Quote tweet of original signal]
```

### Format 4: VIOLET Exit Alert

```
🟣 VIOLET Alert: $TICKER

Trailing stop triggered.

Entry: $XX.XX
Exit: $XX.XX
Return: +XX.X%
Held: X weeks

Systematic exits protect gains.

sterlingsignals.substack.com
```

### Format 5: AMBER Watchlist Drop

```
🟠 AMBER Watchlist

Stocks cleared 4/5 gates — watching for TEAL:

$TICKER1 at $XX.XX — [Theme]
$TICKER2 at $XX.XX — [Theme]
$TICKER3 at $XX.XX — [Theme]

Save this. We'll update when they clear Gate 5.

sterlingsignals.substack.com
```

### Format 6: Theme Spotlight

```
🔥 [THEME NAME] is heating up

Our scanner flagged this theme early:

Theme Score: X.X/10 (PRIME)

Top plays:
$TICKER1 — Extremely Bullish
$TICKER2 — Bullish
$TICKER3 — Watching

Full theme analysis 👇
sterlingsignals.substack.com
```

### Format 7: Funnel Graphic (Keep, Enhance)

```
This week's scan:

📊 1,817 stocks analyzed
⚡ 485 showed momentum
📈 48 confirmed accumulation
🔥 17 aligned with themes
🟢 X TEAL signals

97% rejection rate = only the strongest survive.

sterlingsignals.substack.com

[FUNNEL CHART IMAGE]
```

## 4.3 New Tweet Grid (25/week)

| Day | Slot 1 (08:00) | Slot 2 (10:00) | Slot 3 (12:30) | Slot 4 (15:30) | Slot 5 (18:00) |
|-----|----------------|----------------|----------------|----------------|----------------|
| **Sat** | weekly_recap | thread_teal_signal | theme_spotlight | funnel_graphic | engagement |
| **Sun** | winner_showcase | amber_watch | teal_signal | engagement | engagement |
| **Mon** | theme_spotlight | amber_watch | educational | power_hour | engagement |
| **Tue** | winner_showcase | theme_spotlight | educational | power_hour | engagement |
| **Wed** | amber_watch | theme_spotlight | educational | power_hour | engagement |
| **Thu** | theme_spotlight | amber_watch | educational | power_hour | engagement |
| **Fri** | theme_spotlight | funnel_graphic | violet_alert* | power_hour | engagement |

*violet_alert only if exits triggered; fallback to educational

## 4.4 Self-Quote Thread Strategy

### Process

1. **On Signal:** Post TEAL signal tweet with entry price
2. **Track:** Store tweet_id in `signals.json` or separate tracking file
3. **On Milestone (25%/50%/100%):** Quote-tweet original with update
4. **On Exit:** Quote-tweet original with final result

### New Data Field Needed

```json
// In signals.json or new file
{
  "ticker": "AMSC",
  "signal_tweet_id": "1234567890",
  "entry_price": 33.28,
  "entry_date": "2026-01-24",
  "milestones_quoted": {
    "25_pct": null,
    "50_pct": null,
    "100_pct": null,
    "exit": null
  }
}
```

---

# 5. Technical System Updates

## 5.1 New Scripts Required

| Script | Purpose | Priority |
|--------|---------|----------|
| `substack_content_generator.py` | Generate 3-4 HTML posts per week | HIGH |
| `self_quote_tracker.py` | Track signal tweets for quote-threading | MEDIUM |
| `winner_showcase_generator.py` | Generate winner showcase content with entry prices | HIGH |

## 5.2 Existing Script Modifications

### `config.py`

**Add:**
```python
# Signal Color System
SIGNAL_COLORS = {
    'TEAL': {'emoji': '🟢', 'meaning': 'BUY', 'internal': 'PASS'},
    'VIOLET': {'emoji': '🟣', 'meaning': 'EXIT', 'internal': 'STOPPED'},
    'AMBER': {'emoji': '🟠', 'meaning': 'WATCH', 'internal': 'CONSIDER'},
}

# Conviction Language
CONVICTION_LANGUAGE = {
    5: 'Extremely Bullish',
    4: 'Bullish',
    3: 'Watching',
    2: 'Cautious',
    1: None,  # Do not post
}

# Winner Showcase Threshold
WINNER_SHOWCASE_THRESHOLD = 25.0  # Show entry price for 25%+ gains

# Entry Price Display Rules
ENTRY_PRICE_RULES = {
    'show_for_closed_winners': True,
    'show_for_open_above_threshold': True,
    'threshold_pct': 25.0,
}
```

### `tweet_generator.py`

**Modifications needed:**
1. Update category names (buy_signal → teal_signal, etc.)
2. Add color emoji prefixes to signal tweets
3. Implement conviction language mapping
4. Add entry price display for qualifying positions
5. Implement self-quote reference tracking

### `signal_tracker.py`

**Add:**
```python
def get_winners_for_showcase(threshold: float = 25.0) -> List[Dict]:
    """Get positions over threshold with entry prices for public display."""
    winners = []
    for pos in positions:
        if pos['pnl_pct'] >= threshold and pos['status'] != 'STOPPED':
            winners.append({
                'ticker': pos['ticker'],
                'entry_price': pos['entry_price'],  # NOW INCLUDED
                'current_price': pos['current_price'],
                'pnl_pct': pos['pnl_pct'],
                'days_held': pos['days_held'],
                'theme': pos['theme'],
            })
    return sorted(winners, key=lambda x: x['pnl_pct'], reverse=True)
```

### `marketing_vocabulary.py`

**Add approved terms:**
```python
APPROVED_TERMS.extend([
    'TEAL signal',
    'VIOLET alert',
    'AMBER watch',
    'Extremely Bullish',
    '5 gates cleared',
    'Meanwhile... S&P 500',
])
```

**Remove/update banned terms:**
```python
# Remove if previously banned
# 'entry price' - NOW ALLOWED for 25%+ winners
```

## 5.3 New Directory Structure

```
trades/
├── substack_posts/           # NEW: HTML files for Substack
│   ├── monday_market.html
│   ├── thursday_theme.html
│   ├── saturday_signals.html
│   └── sunday_deepdive.html
├── self_quote_tracker.json   # NEW: Tweet IDs for quote threads
├── portfolio.csv
├── signals.json
├── content_queue.json
└── ...
```

## 5.4 GitHub Actions Updates

### `friday_scan.yml` — Add New Steps

```yaml
# After existing steps...

- name: Generate Substack Content
  run: |
    python substack_content_generator.py --monday
    python substack_content_generator.py --thursday
    python substack_content_generator.py --saturday
    python substack_content_generator.py --sunday  # Optional deep dive

- name: Generate Winner Showcase Data
  run: |
    python winner_showcase_generator.py
```

---

# 6. Codebase Cleanup Inventory

## 6.1 Files to Review for Removal

Based on the audit documents, these categories of files should be reviewed:

### Potentially Deprecated Code

| File/Pattern | Reason to Review | Action |
|--------------|------------------|--------|
| `passes_momentum_filter()` | Always returns True (disabled) | Remove or document |
| 4-week momentum code | Backtest showed -3.1% reduction | Remove dead code |
| `roth_ira` category | In KILLED_CATEGORIES | Verify no references |
| `pdt_friendly` category | In KILLED_CATEGORIES | Verify no references |
| `position_update` category | Merged into top_performers | Verify removed |
| `weekly_wins` category | Renamed | Verify removed |

### Documentation to Update/Remove

| Document | Issue | Action |
|----------|-------|--------|
| CLAUDE.md | Claims 1800 stocks (actual: 937) | Update |
| CLAUDE.md | "Exit on BoS Bearish" (actually advisory) | Clarify |
| CLAUDE.md | "10% baseline entry" (not implemented) | Remove or implement |
| Old audit files | If outdated | Archive or remove |
| TODO lists | If completed | Remove |

### Backup Cleanup

| Location | Issue | Action |
|----------|-------|--------|
| `portfolio/output/portfolio_backups/` | 31+ files, no retention | Add 30-day retention script |

## 6.2 Code Quality Improvements

### Remove Dead Code

```python
# scanner.py - Lines 127-131, 189-195, 578-589
# The momentum filter code that always returns True
# Either remove completely or add clear deprecation notice
```

### Consolidate Duplicate Logic

The audit identified two SPY comparison methods:
- `calculate_portfolio_vs_spy()` — Fixed 30-day (flawed)
- `calculate_fair_spy_comparison()` — Matched periods (correct)

**Action:** Remove or deprecate the fixed 30-day method.

### Configuration Consolidation

Move all hardcoded values to `config.py`:

| Hardcoded Value | Location | Move To |
|-----------------|----------|---------|
| HMA period (21) | scanner.py:430 | config.py |
| Pivot window (k=1) | scanner.py:401 | config.py |
| Banker VWAP period (20) | scanner.py:320 | config.py |
| Banker multiplier (5) | scanner.py:328 | config.py |
| yfinance batch size (50) | scanner.py:558 | config.py |
| Data period ("1y") | scanner.py:553 | config.py |

## 6.3 Recommended File Structure After Cleanup

```
sterling-signals/
├── .github/
│   └── workflows/
│       ├── friday_scan.yml
│       └── daily_post.yml
├── src/                          # Main source code
│   ├── scanner.py
│   ├── portfolio_manager.py
│   ├── signal_tracker.py
│   ├── tweet_generator.py
│   ├── twitter_poster.py
│   ├── newsletter_compiler.py
│   ├── substack_content_generator.py    # NEW
│   ├── substack_notes_generator.py
│   ├── winner_showcase_generator.py     # NEW
│   ├── self_quote_tracker.py            # NEW
│   ├── market_analyzer.py
│   ├── chart_capture.py
│   ├── config.py
│   └── marketing_vocabulary.py
├── trades/                       # Output data
│   ├── portfolio.csv
│   ├── signals.json
│   ├── content_queue.json
│   ├── celebrations.json
│   ├── self_quote_tracker.json          # NEW
│   ├── substack_posts/                  # NEW
│   ├── current/
│   └── charts/
├── docs/                         # Documentation
│   ├── SYSTEM_ARCHITECTURE.md           # Consolidated from audits
│   ├── MARKETING_GUIDE.md               # NEW
│   └── CHANGELOG.md
├── archive/                      # OLD: Deprecated files
│   └── (old audits, completed TODOs)
├── complete_tickers.txt
├── requirements.txt
└── README.md
```

---

# 7. Marketing Compliance Updates

## 7.1 Entry Price Display Rules

### New Rule: Show Entry Prices for Winners

**Condition:** Position P&L ≥ 25%

**Implementation:**
```python
def can_show_entry_price(position: dict) -> bool:
    """Determine if entry price can be shown publicly."""
    pnl = position.get('pnl_pct', 0)
    status = position.get('status', 'OPEN')
    
    # Closed winners: Always show
    if status in ['CLOSED'] and pnl > 0:
        return True
    
    # Open positions: Only show if 25%+ gain
    if status == 'OPEN' and pnl >= 25.0:
        return True
    
    # STOPPED positions: Show if profitable
    if status == 'STOPPED' and pnl > 0:
        return True
    
    return False
```

### Display Format

```
$TICKER: $XX.XX → $XX.XX (+XX.X%)
         ↑ entry   ↑ current
```

## 7.2 Updated Safeguard Rules

### Modified: `filter_public_positions()`

```python
def filter_public_positions_v2(positions: List[Dict], include_entry_price: bool = True) -> List[Dict]:
    """
    Filter positions for public display.
    
    NEW: Optionally includes entry prices for qualifying positions.
    """
    public_positions = []
    
    for pos in positions:
        # Still never show STOPPED positions in general lists
        if pos.get('status') == 'STOPPED':
            continue
        
        pnl = pos.get('pnl_pct', 0)
        
        # Only positive P&L
        if pnl < 0:
            continue
        
        # Build public record
        public_pos = {
            'ticker': pos['ticker'],
            'current_price': pos['current_price'],
            'pnl_pct': pnl,
            'days_held': pos.get('days_held', 0),
            'theme': pos.get('theme', ''),
        }
        
        # NEW: Include entry price if qualifies
        if include_entry_price and pnl >= 25.0:
            public_pos['entry_price'] = pos['entry_price']
            public_pos['show_entry'] = True
        else:
            public_pos['show_entry'] = False
        
        public_positions.append(public_pos)
    
    return public_positions
```

## 7.3 Updated Vocabulary

### New Approved Terms

| Term | Context |
|------|---------|
| `🟢 TEAL` | Signal type |
| `🟣 VIOLET` | Exit alert |
| `🟠 AMBER` | Watchlist |
| `Extremely Bullish` | Conviction 5 |
| `Bullish` | Conviction 4 |
| `Watching` | Conviction 3 |
| `from $XX.XX → $XX.XX` | Entry price format |
| `Meanwhile... S&P 500` | Benchmark comparison |
| `5 gates cleared` | Signal validation |

### New Banned Terms

| Term | Reason |
|------|--------|
| `buy signal` | Use "TEAL signal" |
| `sell signal` | Use "VIOLET alert" |
| `watchlist signal` | Use "AMBER watch" |

---

# 8. Implementation Priorities

## 8.1 Phase 1: Foundation (Week 1)

### HIGH Priority

| Task | Description | Effort |
|------|-------------|--------|
| Update `config.py` | Add signal colors, conviction language, entry price rules | 2 hrs |
| Create `substack_content_generator.py` | Generate 4 HTML templates | 8 hrs |
| Update `tweet_generator.py` | New categories, color system | 4 hrs |
| Update `marketing_vocabulary.py` | New approved/banned terms | 1 hr |
| Update Friday workflow | Add Substack content generation | 1 hr |

### Deliverables
- [ ] Color signal system implemented
- [ ] 4 Substack HTML templates generating
- [ ] Conviction language mapping active
- [ ] New tweet grid deployed

## 8.2 Phase 2: Winner Showcasing (Week 2)

### HIGH Priority

| Task | Description | Effort |
|------|-------------|--------|
| Create `winner_showcase_generator.py` | Entry price display for 25%+ | 4 hrs |
| Update `signal_tracker.py` | Add `get_winners_for_showcase()` | 2 hrs |
| Update tweet templates | Add entry price format | 2 hrs |
| Create `weekly_recap` tweet format | High-engagement format | 2 hrs |

### Deliverables
- [ ] Entry prices shown for qualifying positions
- [ ] Weekly recap tweet format active
- [ ] Winner showcase tweets generating

## 8.3 Phase 3: Self-Quote System (Week 3)

### MEDIUM Priority

| Task | Description | Effort |
|------|-------------|--------|
| Create `self_quote_tracker.py` | Track tweet IDs | 4 hrs |
| Update signal storage | Store tweet_id with signals | 2 hrs |
| Create quote-tweet workflow | Generate quote tweets on milestones | 4 hrs |
| Test end-to-end | Validate quote thread building | 2 hrs |

### Deliverables
- [ ] Signal tweet IDs tracked
- [ ] Quote tweets generated on milestones
- [ ] Thread building active

## 8.4 Phase 4: Codebase Cleanup (Week 4)

### LOW Priority (But Important)

| Task | Description | Effort |
|------|-------------|--------|
| Remove dead momentum code | scanner.py cleanup | 1 hr |
| Consolidate SPY comparison | Remove flawed method | 1 hr |
| Move hardcoded values | To config.py | 2 hrs |
| Update documentation | CLAUDE.md, README | 2 hrs |
| Archive old files | Audits, TODOs | 1 hr |
| Add backup retention | 30-day cleanup script | 1 hr |

### Deliverables
- [ ] Dead code removed
- [ ] Configuration consolidated
- [ ] Documentation accurate
- [ ] File structure clean

## 8.5 Success Checkpoints

| Week | Checkpoint |
|------|------------|
| Week 1 | 3-4 Substack posts generating, color system live |
| Week 2 | Entry prices showing, weekly recap format active |
| Week 3 | Self-quote tracking working, first quote thread built |
| Week 4 | Codebase clean, documentation updated |

---

# Appendix A: Quick Reference Card

## Signal System

| Signal | Emoji | Meaning | Trigger |
|--------|-------|---------|---------|
| TEAL | 🟢 | BUY | 5 gates cleared |
| VIOLET | 🟣 | EXIT | Stop hit or BoS down |
| AMBER | 🟠 | WATCH | 4/5 gates, monitoring |

## Conviction Language

| Score | Public | Tweet Format |
|-------|--------|--------------|
| 5 | Extremely Bullish | "We're extremely bullish on $TICKER" |
| 4 | Bullish | "Bullish setup on $TICKER" |
| 3 | Watching | "Watching $TICKER closely" |

## Entry Price Rules

| Condition | Show Entry? |
|-----------|-------------|
| Closed winner | ✅ Yes |
| Open 25%+ | ✅ Yes |
| Open <25% | ❌ No |
| Any loser | ❌ Never |
| STOPPED (profitable) | ✅ Yes (in exit posts) |

## Weekly Content Calendar

| Day | Substack | Tweets |
|-----|----------|--------|
| Mon | Market Analysis | 5 tweets |
| Tue | — | 5 tweets |
| Wed | — | 5 tweets |
| Thu | Theme Spotlight | 5 tweets |
| Fri | — | 5 tweets |
| Sat | Weekly Signals | 5 tweets |
| Sun | Deep Dive (optional) | 5 tweets |

---

# Appendix B: Competitor Benchmark

## What They Do (Copy These Patterns)

| Pattern | Implementation |
|---------|----------------|
| "One proper swing can change your life" | Use in winner showcase tweets |
| "$TICKER from $X → $Y (+XX%)" | Entry price format for 25%+ |
| "Meanwhile... S&P 500" | Benchmark shaming format |
| Watchlist with prices | AMBER watch format |
| Self-quote threads | Quote original signal on wins |
| Simple signal language | TEAL/VIOLET/AMBER system |

## What They Don't Do (Maintain These Standards)

| Pattern | Our Approach |
|---------|--------------|
| Show losing trades | Never show losses |
| Discuss methodology in detail | Keep 5-gate mystery |
| Use complex terminology | Simple color system |
| Post without visuals | Always include charts |

---

*End of Sterling Signals Improvement Reference Document*
