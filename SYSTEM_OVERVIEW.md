# Sterling Signals - Complete System Overview

**Purpose:** Comprehensive system documentation for marketing plan development, content strategy, and automation assessment.

**Last Updated:** January 23, 2026

---

## Executive Summary

Sterling Signals is a fully automated weekly momentum trading scanner and content publishing system targeting UK ISA investors seeking US equity exposure. The system scans 1,800+ stocks weekly, generates trade signals through a proprietary 5-gate process, and publishes content across X/Twitter and Substack with minimal manual intervention.

### Key Metrics

| Metric | Value |
|--------|-------|
| Stocks Scanned | 1,800+ weekly |
| Content Generated | 35 tweets + 1 newsletter + 2 Substack notes per week |
| Automation Level | ~95% (only Substack publish is manual) |
| Weekly Time Investment | ~15 minutes manual work |
| Cost per Week | ~$2-5 API costs |

---

## 1. Brand Identity

### Accounts & Platforms

| Platform | Handle | Purpose |
|----------|--------|---------|
| **Substack** | sterlingsignals.substack.com | Weekly newsletter, Notes |
| **X/Twitter** | @SterlingSignals | Automated daily content |
| **X/Twitter** | @AlexanderSterling | Personal brand (if applicable) |

### Target Audience

- **Primary:** UK ISA investors seeking US equity exposure
- **Secondary:** Momentum traders, swing traders, theme investors
- **Tertiary:** Trading educators, fintech enthusiasts

### Brand Voice

- Confident but not arrogant
- Data-driven with specific numbers
- Professional trader voice (not hype)
- Occasional humor acceptable
- No financial advice disclaimers in content (reserved for bio/footer)

---

## 2. Marketing Language Rules

### NEVER Reveal (Proprietary Details)

These specific strategy elements must NEVER appear in public content:

| ❌ DO NOT SAY | ✅ SAY INSTEAD |
|---------------|----------------|
| "20% trailing stop" | "Disciplined risk management" |
| "HMA pivots" | "Proprietary technical signals" |
| "Banker indicator" | "Smart money accumulation signals" |
| "Beta >= 1.5" | "High-momentum screening criteria" |
| "Weekly BoS (Break of Structure)" | "Technical trend confirmation" |
| "Tier 1/2/3 classification" | "Signal strength indicators" |

### Approved Marketing Phrases

Use these phrases consistently across all content:

**System Description:**
- "Proprietary multi-step screening process"
- "5-gate quality system"
- "Filters 1,800 stocks down to 3-5 winners"
- "Systematic approach to momentum trading"

**Signal Detection:**
- "Smart money accumulation signals"
- "Institutional flow tracking"
- "Theme momentum confirmation"
- "Technical entry/exit signals"
- "Proprietary breakout detection"

**Risk Management:**
- "Disciplined risk management"
- "Predetermined exit strategy"
- "Capital preservation focus"
- "Systematic position sizing"

**Theme Investing:**
- "Following institutional money flows"
- "Bottleneck play identification"
- "Hot vs cold theme analysis"
- "Contrarian opportunity detection"

### Content Themes to Emphasize

1. **Following Smart Money** - Institutional flows, accumulation patterns
2. **Bottleneck Plays** - Infrastructure, supply chain, capacity constraints
3. **Theme Momentum** - Hot sectors, rotating capital, catalyst-driven
4. **Contrarian Opportunities** - Cold themes, oversold setups, patience plays
5. **Discipline Over FOMO** - Patience, systematic approach, no chasing
6. **Outperformance** - Market-beating results through systematic screening

### Honesty Rules (Critical)

Even with marketing language, NEVER hide losses:

1. **Always show full P&L** - Include losers alongside winners
2. **Frame losses positively** without hiding them:
   - "Stop hit = system working exactly as designed"
   - "Risk management protected us from bigger loss"
   - "Discipline > ego. On to the next."
3. **When underwater:**
   - "Down 5% YTD but system working - cutting losers fast"
   - "3 stops hit this month = capital preserved for better setups"
4. **Compare to benchmark** when favorable:
   - "SPY down 10%, we're down 5% = outperforming in tough conditions"

---

## 3. Pipeline Architecture

### Complete Weekly Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FRIDAY PIPELINE (Automated @ 21:30 UTC)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: SCANNER (scanner.py)                                               │
│  └─> 1,800 tickers → Technical Gate → 40-50 candidates                      │
│      • Beta >= 1.5 filter                                                   │
│      • Weekly BoS (Break of Structure) detection                            │
│      • Banker indicator (smart money accumulation) >= 55                    │
│                                                                              │
│  STEP 2: THEMATIC ANALYZER (thematic_analyzer.py)                           │
│  └─> Identify 5-7 themes, classify and map stocks                          │
│      • PRIME themes (highest conviction)                                    │
│      • INVESTABLE themes (tradeable)                                        │
│      • SELECTIVE themes (mixed signals)                                     │
│      • AVOID themes (stay away)                                             │
│                                                                              │
│  STEP 3: GATEKEEPER (gatekeeper.py)                                         │
│  └─> Final quality gate with decisions                                      │
│      • PASS (5-10 stocks) → Ready for entry                                │
│      • CAUTION (5-15 stocks) → Watchlist                                   │
│      • FAIL → Skip                                                          │
│                                                                              │
│  STEP 4: DUE DILIGENCE (dd_automator.py)                                   │
│  └─> Deal Memo for each PASS signal                                        │
│      • 5-phase DD methodology                                               │
│      • 50%+ upside path validation                                          │
│      • STRONG BUY / SPEC BUY / SKIP verdicts                               │
│                                                                              │
│  STEP 5: MARKET ANALYSIS (market_analyzer.py)                               │
│  └─> Weekly macro context via Claude + web search                          │
│                                                                              │
│  STEP 6: PORTFOLIO UPDATE (portfolio_manager.py)                            │
│  └─> Track positions, P&L, stops, alerts                                   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                         CONTENT GENERATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  NEWSLETTER (newsletter_compiler.py)                                        │
│  └─> Full HTML newsletter (~2,500-3,500 words)                             │
│      • Market context                                                        │
│      • Hot themes with thesis                                               │
│      • PASS signals with DD summaries                                       │
│      • Portfolio status with P&L                                            │
│      • Caution signals analysis                                             │
│                                                                              │
│  TWEETS (tweet_generator.py)                                                │
│  └─> 35 tweets (5/day for 7 days)                                          │
│      • Follows marketing language rules                                     │
│      • Categories: buy_signal, theme_hot, position_update, etc.            │
│      • Chart attachments for position updates                               │
│                                                                              │
│  SUBSTACK NOTES (substack_notes_generator.py)                               │
│  └─> 2 mid-week notes                                                       │
│      • Tuesday: "Portfolio Pulse" - YTD status                             │
│      • Thursday: "Trade Spotlight" - Signal highlights                     │
│                                                                              │
│  CHARTS (chart_capture.py)                                                  │
│  └─> TradingView screenshots via Playwright                                │
│      • 1200x800 for X/Twitter                                               │
│      • Custom indicators visible (BoS lines, volume bars)                  │
│      • Indicator NAMES hidden for proprietary protection                   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                    AUTOMATED PUBLISHING                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  X/TWITTER (daily_post.yml + twitter_poster.py)                            │
│  └─> 5 posts/day at scheduled times (UK)                                   │
│      • Slot 1: 07:00 - Early morning                                       │
│      • Slot 2: 09:00 - Morning                                             │
│      • Slot 3: 12:30 - Midday                                              │
│      • Slot 4: 15:30 - Afternoon                                           │
│      • Slot 5: 19:00 - Evening                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Automation Status Matrix

| Component | Automation | Manual Step Required |
|-----------|------------|---------------------|
| Stock scanning | 100% | - |
| Theme analysis | 100% | - |
| Quality gating | 100% | - |
| Due diligence | 100% | - |
| Market analysis | 100% | - |
| Newsletter generation | 100% | - |
| Tweet generation | 100% | - |
| Tweet posting | 100% | - |
| Chart capture | 90% | Run locally with TradingView login |
| Substack Notes generation | 100% | - |
| **Newsletter publish** | **0%** | Copy HTML to Substack (~10 min) |
| **Substack Notes publish** | **0%** | Copy to Notes interface (~2 min each) |

---

## 4. Content Calendar

### Weekly Schedule (UK Time)

| Day | X/Twitter (Automated) | Substack (Manual) |
|-----|----------------------|-------------------|
| **Friday** | 5 posts: Scanner tease, theme update, week ahead | Pipeline runs @ 21:30 UTC |
| **Saturday** | 5 posts: Newsletter drop, signal spotlight, education | **Publish newsletter** (~10 min) |
| **Sunday** | 5 posts: Engagement, lessons, week preview | - |
| **Monday** | 5 posts: Week ahead, theme deep-dive, positions | - |
| **Tuesday** | 5 posts: Buy signal, cold theme, watchlist | **Post "Portfolio Pulse" note** (~2 min) |
| **Wednesday** | 5 posts: Market pulse, theme compare, positions | - |
| **Thursday** | 5 posts: Signal spotlight, hot theme, watchlist | **Post "Trade Spotlight" note** (~2 min) |

### Tweet Categories (35/week)

| Category | Count | Purpose |
|----------|-------|---------|
| `system_promo` | 5 | Explain 5-gate system, funnel stats |
| `buy_signal` | 5 | Spotlight PASS signals, DD verdicts |
| `theme_hot` | 5 | PRIME/INVESTABLE theme analysis |
| `theme_cold` | 3 | SELECTIVE/AVOID warnings, contrarian takes |
| `position_update` | 5 | Portfolio status, live P&L, chart attachments |
| `sell_signal` | 2 | Caution alerts, stop triggers |
| `educational` | 5 | Trading methodology, risk management |
| `engagement` | 5 | Polls, questions, community building |

### Tweet Schedule (5 slots/day)

| Slot | UK Time | Content Type |
|------|---------|--------------|
| 1 | 07:00 | System promo / Educational |
| 2 | 09:00 | Theme analysis / Buy signal |
| 3 | 12:30 | Position update / Market pulse |
| 4 | 15:30 | Theme / Watchlist |
| 5 | 19:00 | Engagement / Lessons |

---

## 5. Content Examples

### Tweet: System Promo
```
🔬 How we filter 1,800 stocks to 3 STRONG BUYs:

Step 1: Technical breakout confirmed ✅
Step 2: Smart money accumulation ✅
Step 3: Theme momentum aligned ✅
Step 4: Quality gate passed ✅
Step 5: Deep due diligence ✅

99% of stocks fail our screening.

See what passed this week 👇
sterlingsignals.substack.com
```

### Tweet: Buy Signal
```
🎯 $IESC passes our proprietary 5-gate system

✅ Technical entry signal confirmed
✅ Smart money accumulation detected
✅ Hot theme momentum
✅ Deep due diligence: STRONG BUY

Full analysis in this week's newsletter 👇
sterlingsignals.substack.com
```

### Tweet: Theme Hot
```
🔥 AI Cooling is THIS week's hottest theme

Why? Hyperscalers spending $100B+ on data centers
Institutional money piling into bottleneck plays

Our proprietary system flagged this theme early 👇
sterlingsignals.substack.com
```

### Tweet: Position Update (with chart)
```
📈 Position update: $STRL

Entry: $362.53
Current: $364.25
P&L: +0.5%

AI Cooling & Data Center Infrastructure - smart money accumulation confirmed by our proprietary indicators.

Following the institutional flows into bottleneck themes.

Full analysis → sterlingsignals.substack.com
```

### Tweet: Loss (Honest Framing)
```
🔴 $SMCI stopped out at -18%

No system wins 100%. Here's what happened:
• Thesis changed (accounting concerns)
• Risk management triggered
• Loss capped. Capital preserved.

This is exactly why we have rules.

Full breakdown 👇
sterlingsignals.substack.com
```

### Substack Note: Tuesday "Portfolio Pulse"
```
📊 Portfolio Pulse - Week 4

YTD Performance: +12.3%
Open Positions: 6
Win Rate: 75%

Top Performer: $RCAT (+55%)
Recent Exit: $OKLO (+29%)

Watchlist: 3 stocks nearing entry signals

Full analysis in Saturday's newsletter →
sterlingsignals.substack.com
```

### Substack Note: Thursday "Trade Spotlight"
```
🎯 Trade Spotlight

This week's focus: $INOD
Theme: Power Grid Infrastructure
Verdict: STRONG BUY

Why we're watching:
• Infrastructure bill tailwind
• Earnings catalyst in 3 weeks
• Smart money accumulating

Details in Saturday's newsletter →
sterlingsignals.substack.com
```

---

## 6. Charts & Graphics

### TradingView Chart Capture

Charts are captured via Playwright browser automation from TradingView.

**Configuration:**
- Layout ID: `rxC5j0SK` (saved with custom indicators)
- X/Twitter size: 1200x800 pixels
- Substack size: 800x600 pixels
- Indicators: BoS lines, volume bars (names hidden)

**Process:**
1. Script opens TradingView with saved layout
2. Switches to target ticker symbol
3. Waits for indicators to render
4. Hides indicator names via JavaScript injection
5. Captures screenshot
6. Saves to `trades/charts/{TICKER}_{date}.png`

**Chart Manifest:**
```json
{
  "captured_at": "2026-01-23T01:23:21.351833",
  "charts": {
    "STRL": "/path/to/trades/charts/STRL_20260123.png"
  }
}
```

**Usage in Tweets:**
- Position update tweets include `image_path` field
- twitter_poster.py uploads image via Twitter API v1.1
- Attaches media_id to tweet via Twitter API v2

---

## 7. File Structure

```
bos_momentum_scanner/
├── Core Pipeline
│   ├── scanner.py              # Main orchestrator (~3000 lines)
│   ├── thematic_analyzer.py    # Theme discovery (~1400 lines)
│   ├── gatekeeper.py           # Quality gate (~600 lines)
│   ├── dd_automator.py         # Due diligence automation
│   └── portfolio_manager.py    # Trade tracking (~900 lines)
│
├── Content Generation
│   ├── tweet_generator.py           # 35 weekly tweets with marketing rules
│   ├── newsletter_compiler.py       # Full HTML newsletter
│   ├── substack_notes_generator.py  # Tuesday/Thursday notes
│   ├── market_analyzer.py           # Market context (Claude + web)
│   └── chart_capture.py             # TradingView screenshots
│
├── Publishing
│   ├── twitter_poster.py            # X/Twitter API posting
│   └── .github/workflows/
│       ├── friday_scan.yml          # Weekly pipeline (Fridays 21:30 UTC)
│       └── daily_post.yml           # 5 tweets/day posting
│
├── Configuration
│   ├── output_paths.py              # Folder structure management
│   ├── complete_tickers.txt         # 1,800+ ticker universe
│   └── .env                         # API keys (not in repo)
│
├── Documentation
│   ├── SYSTEM_OVERVIEW.md           # This file
│   ├── CLAUDE.md                    # Full technical docs
│   ├── README.md                    # Quick start
│   └── SETUP.md                     # Installation guide
│
└── Output (trades/)
    ├── current/                     # Latest week's outputs
    │   ├── newsletter.html
    │   ├── newsletter_briefing.md
    │   ├── signals.json
    │   ├── substack_notes/
    │   │   ├── tuesday_note.md
    │   │   └── thursday_note.md
    │   ├── charts/
    │   └── tweets/
    │       └── content_queue.json
    ├── weeks/                       # Weekly archives (YYYY-WXX/)
    ├── portfolio.csv                # Source of truth
    ├── content_queue.json           # Tweet posting queue
    └── charts/                      # Chart images
```

---

## 8. API & Costs

### APIs Used

| API | Purpose | Cost |
|-----|---------|------|
| **Anthropic Claude** | LLM analysis (themes, gating, DD, newsletter, tweets) | ~$2-5/week |
| **Twitter/X API** | Tweet posting with media | Free (Basic tier) |
| **yfinance** | Stock data download | Free |
| **GitHub Actions** | Scheduled automation | Free (private repo limits) |

### Weekly Cost Breakdown

| Item | Estimated Cost |
|------|----------------|
| Scanner (themes + gating) | ~$1.00-1.50 |
| Due Diligence (per signal) | ~$0.30-0.50 |
| Market Analysis | ~$0.20-0.30 |
| Newsletter Compilation | ~$0.20-0.50 |
| Tweet Generation | ~$0.30-0.50 |
| **Total Weekly** | **~$2-5** |

### Annual Projection
- Conservative: ~$100-150/year
- High usage: ~$200-300/year

---

## 9. Improvement Opportunities

### High Priority

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Tweet engagement tracking | Medium | High | Log tweet_ids, fetch metrics via API |
| Substack email-to-publish | Medium | High | Automate newsletter publish |
| Performance dashboard | High | High | Visual portfolio + content analytics |

### Medium Priority

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Chart capture in CI | Medium | Medium | Alternative to TradingView or headless setup |
| A/B testing tweets | Medium | Medium | Test formats, times, messaging |
| Newsletter open tracking | Low | Medium | Substack provides basic analytics |

### Future Considerations

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Substack API integration | Depends | Medium | Wait for public API |
| Multiple X account posting | Low | Low | Cross-post strategy |
| Backtesting integration | High | Medium | Historical signal performance |

---

## 10. Marketing Strategy Alignment

### Current Funnel

```
AWARENESS (X/Twitter)
       │
       ▼ "Interesting scanner..."
INTEREST (Thread engagement, profile visit)
       │
       ▼ "Want to see full analysis"
CONSIDERATION (Newsletter signup)
       │
       ▼ "Weekly insights valuable"
CONVERSION (Loyal subscriber)
       │
       ▼ "Premium content?"
EXPANSION (Future premium tier?)
```

### Content Strategy by Funnel Stage

| Stage | Content Type | Platform | Goal |
|-------|--------------|----------|------|
| **Awareness** | Teasers, stats, hot takes | X/Twitter | Impressions, engagement |
| **Interest** | Thread summaries, charts | X/Twitter | Profile visits, follows |
| **Consideration** | Educational, methodology | X/Twitter + Notes | Newsletter signups |
| **Conversion** | Full analysis, DD reports | Newsletter | Retained subscribers |

### Cross-Promotion Strategy

1. **Every tweet links to newsletter** - sterlingsignals.substack.com
2. **Newsletter previews in Notes** - Tuesday/Thursday teasers
3. **Position updates with charts** - Visual engagement drivers
4. **Educational threads** - Build authority, drive signups

### Content Repurposing

| Source | Repurposed As |
|--------|---------------|
| DD Summary | Buy signal tweet + thread |
| Theme Analysis | Hot theme tweet + educational post |
| Portfolio Update | Position tweet with chart + Note |
| Loss Exit | Lesson tweet + risk management post |

---

## 11. Quick Reference

### Key Commands

```bash
# Full Friday pipeline
./run_friday.sh

# Generate tweets only (with marketing language)
python tweet_generator.py

# Generate newsletter
python newsletter_compiler.py --full

# Generate Substack notes
python substack_notes_generator.py

# Capture charts
python chart_capture.py --tickers AAPL,NVDA

# Post tweet manually
source .env && python twitter_poster.py --force

# View portfolio
python portfolio_manager.py --report
```

### Key Files for Manual Steps

| Day | File | Action |
|-----|------|--------|
| Saturday | `trades/current/newsletter.html` | Copy to Substack |
| Tuesday | `trades/current/substack_notes/tuesday_note.md` | Copy to Notes |
| Thursday | `trades/current/substack_notes/thursday_note.md` | Copy to Notes |

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Twitter/X Posting
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_SECRET=...

# Optional: Chart capture
TRADINGVIEW_LAYOUT_ID=rxC5j0SK
```

---

## 12. Metrics to Track

### Content Performance (To Implement)

| Metric | Source | Frequency |
|--------|--------|-----------|
| Tweet impressions | X Analytics / API | Weekly |
| Tweet engagements | X Analytics / API | Weekly |
| Newsletter opens | Substack Dashboard | Weekly |
| Newsletter CTR | Substack Dashboard | Weekly |
| Subscriber growth | Substack Dashboard | Weekly |
| Notes engagement | Substack Dashboard | Weekly |

### Trading Performance (Implemented)

| Metric | Source | Frequency |
|--------|--------|-----------|
| Open positions | portfolio.csv | Real-time |
| Unrealized P&L | portfolio.csv | Real-time |
| Closed trades | portfolio.csv | Per exit |
| Win rate | portfolio.csv | Monthly |
| Avg winner/loser | portfolio.csv | Monthly |

---

*Document generated for marketing plan development. Last updated: January 23, 2026*
