# Sterling Signals - System Overview

**Purpose:** Comprehensive system assessment for X/Substack marketing plan development and improvement identification.

**Last Updated:** January 22, 2026

---

## Executive Summary

Sterling Signals is a fully automated weekly momentum trading scanner and content publishing system targeting UK ISA investors seeking US equity exposure.

### Key Metrics

| Metric | Value |
|--------|-------|
| Stocks Scanned | 1,800+ weekly |
| Content Generated | 35 tweets + 1 newsletter + 2 notes per week |
| Automation Level | ~95% (only Substack publish manual) |
| Weekly Time Investment | ~15 minutes manual work |
| Cost per Week | ~$2-5 API costs |

---

## 1. System Architecture

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRIDAY PIPELINE (Automated)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Scanner (scanner.py)                                               │
│  └─> 1,800 tickers → Technical Gate → 40-50 candidates              │
│                                                                      │
│  Thematic Analyzer (thematic_analyzer.py)                           │
│  └─> Identify 5-7 hot themes, map stocks to themes                  │
│                                                                      │
│  Gatekeeper (gatekeeper.py)                                         │
│  └─> PASS (5-10) / CAUTION (5-15) / FAIL decisions                 │
│                                                                      │
│  Due Diligence (dd_automator.py)                                    │
│  └─> Deal Memo for each PASS signal                                 │
│                                                                      │
│  Market Analysis (market_analyzer.py)                               │
│  └─> Weekly market context with macro view                          │
│                                                                      │
│  Portfolio Update (portfolio_manager.py)                            │
│  └─> Track positions, calculate P&L, update stops                   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    CONTENT GENERATION                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Newsletter (newsletter_compiler.py)                                │
│  └─> Full HTML newsletter ready for Substack                        │
│                                                                      │
│  Tweets (tweet_generator.py)                                        │
│  └─> 35 tweets (5/day for 7 days) in content_queue.json            │
│                                                                      │
│  Substack Notes (substack_notes_generator.py)                       │
│  └─> Tuesday "Portfolio Pulse" + Thursday "Trade Spotlight"         │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    PUBLISHING (Automated)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  X/Twitter Posting (.github/workflows/post_content.yml)             │
│  └─> 5 tweets/day at 08:00, 10:00, 12:00, 15:00, 18:00 UK          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Automation Status

| Component | Automation | Manual Step |
|-----------|------------|-------------|
| Stock scanning | 100% | - |
| Theme analysis | 100% | - |
| Due diligence | 100% | - |
| Market analysis | 100% | - |
| Newsletter generation | 100% | - |
| Tweet generation | 100% | - |
| Tweet posting | 100% | - |
| Substack Notes generation | 100% | - |
| **Newsletter publish** | **0%** | Copy HTML to Substack (~10 min) |
| **Substack Notes publish** | **0%** | Copy to Notes interface (~2 min each) |
| Chart capture | Local only | Run locally with TradingView login |

---

## 2. Content Strategy

### Weekly Content Calendar

| Day | X/Twitter (Automated) | Substack (Manual) |
|-----|----------------------|-------------------|
| **Saturday** | 5 posts: Newsletter drop, signal spotlight, education | Newsletter publish |
| **Sunday** | 5 posts: Engagement, week ahead, lessons | - |
| **Monday** | 5 posts: Week preview, theme deep-dive, positions | - |
| **Tuesday** | 5 posts: Buy signal, cold theme, watchlist | "Portfolio Pulse" Note |
| **Wednesday** | 5 posts: Market pulse, theme compare, positions | - |
| **Thursday** | 5 posts: Signal spotlight, hot theme, watchlist | "Trade Spotlight" Note |
| **Friday** | 5 posts: Scanner tease, theme update, preview | - |

### Content Types Generated

#### Newsletter (~2,500-3,500 words)
- Market context with macro view
- Hot themes ranked with thesis
- PASS signals with full DD summaries
- Open positions with P&L and stop distances
- Caution signals with analysis
- Portfolio performance metrics

#### Tweets (35/week)
- Scanner results teasers
- Theme deep-dives
- Buy signal spotlights
- Position updates with live P&L
- Sell signal alerts
- Watchlist analysis
- Educational content
- Engagement posts

#### Substack Notes (2/week)
- **Tuesday "Portfolio Pulse"**: Portfolio YTD status, unrealized P&L, position summaries
- **Thursday "Trade Spotlight"**: New signals, trade reasoning, market context

---

## 3. Technical Infrastructure

### GitHub Actions Workflows

| Workflow | Trigger | Duration | Cost |
|----------|---------|----------|------|
| Friday Weekly Scan | Fridays 21:30 UTC | ~10-15 min | ~$2-5 |
| Daily Tweet Posting | 5x daily | ~30 sec each | Free |

### File Structure

```
bos_momentum_scanner/
├── Core Pipeline
│   ├── scanner.py           # Main orchestrator
│   ├── thematic_analyzer.py # Theme discovery
│   ├── gatekeeper.py        # Quality gate
│   └── portfolio_manager.py # Trade tracking
│
├── Content Generation
│   ├── tweet_generator.py          # 35 weekly tweets
│   ├── newsletter_compiler.py      # Full newsletter
│   ├── substack_notes_generator.py # Mid-week notes
│   ├── market_analyzer.py          # Market context
│   └── dd_automator.py             # Due diligence
│
├── Automation
│   ├── run_friday.sh               # Pipeline script
│   ├── output_paths.py             # Folder management
│   └── .github/workflows/          # GitHub Actions
│
└── Output (trades/)
    ├── current/                    # Latest outputs
    ├── weeks/                      # Weekly archives
    ├── charts/                     # Chart images
    └── grok_prompts/               # Tweet files
```

### API Dependencies

| API | Purpose | Monthly Cost |
|-----|---------|--------------|
| Anthropic Claude | LLM analysis | ~$8-20 |
| Twitter/X | Tweet posting | Free (Basic tier) |
| yfinance | Stock data | Free |

---

## 4. Performance Tracking

### Portfolio Metrics (Tracked)
- Open positions count
- Unrealized P&L (% and $)
- Win rate (closed trades)
- Average winner/loser
- Days held per position
- Stop distance alerts

### Content Metrics (Not Yet Tracked)
- Tweet engagement (likes, retweets, replies)
- Newsletter open rates
- Subscriber growth
- Click-through rates

---

## 5. Improvement Opportunities

### High Priority

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Tweet engagement tracking | Medium | High | Add tweet_id logging, fetch metrics via API |
| Substack auto-publish | Medium | High | Email-to-publish or browser automation |
| Performance dashboard | High | High | Visual portfolio and content analytics |

### Medium Priority

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Chart capture in CI | Medium | Medium | Headless TradingView or alternative |
| Newsletter open tracking | Low | Medium | Substack provides basic analytics |
| A/B testing tweets | Medium | Medium | Test different formats/times |

### Low Priority / Future

| Improvement | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Substack API integration | Depends | Medium | Wait for public API |
| Backtesting integration | High | Medium | Historical signal performance |
| Multiple account posting | Low | Low | Cross-post to multiple X accounts |

---

## 6. Marketing Recommendations

### Current Positioning
- **Target Audience:** UK ISA investors seeking US equity exposure
- **Value Proposition:** AI-powered momentum signals with institutional-quality analysis
- **Frequency:** Weekly newsletter + daily X engagement

### Content Strategy Alignment

| Channel | Purpose | Cadence | Content Type |
|---------|---------|---------|--------------|
| **Substack Newsletter** | Deep analysis, trade recommendations | Weekly | Long-form, research-grade |
| **Substack Notes** | Mid-week updates, engagement | 2x/week | Short-form, portfolio status |
| **X/Twitter** | Awareness, real-time commentary | Daily | Sound bites, charts, teasers |

### Growth Opportunities

1. **Cross-Promotion**
   - Newsletter CTAs in tweets
   - Tweet threads summarizing newsletter highlights
   - Notes previewing upcoming newsletter

2. **Content Repurposing**
   - Newsletter sections → tweet threads
   - DD summaries → standalone posts
   - Theme analysis → educational content

3. **Engagement Optimization**
   - Track best-performing tweet types
   - Optimize posting times based on engagement
   - A/B test different formats

4. **Community Building**
   - Respond to comments/replies
   - Polls on themes/stocks
   - Q&A threads

---

## 7. Cost Analysis

### Weekly Costs

| Item | Cost |
|------|------|
| Anthropic API (scanner) | ~$1.50-2.50 |
| Anthropic API (DD) | ~$0.50-1.50 |
| Anthropic API (newsletter) | ~$0.20-0.50 |
| Twitter API | Free |
| GitHub Actions | Free (public repo limits) |
| **Total** | **~$2-5/week** |

### Annual Projection
- Low estimate: ~$100/year
- High estimate: ~$250/year

---

## 8. Risk Factors

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limits | Medium | Medium | Exponential backoff, caching |
| Twitter API changes | Medium | High | Monitor announcements, backup strategy |
| Anthropic pricing changes | Low | Medium | Budget buffer, alternative models |
| TradingView access issues | Medium | Low | Chart capture is optional |
| GitHub Actions limits | Low | Low | Generous free tier for private repos |

---

## 9. Quick Reference

### Key Commands

```bash
# Full Friday pipeline
./run_friday.sh

# Generate tweets only
python tweet_generator.py

# Generate newsletter only
python newsletter_compiler.py --full

# Generate Substack notes
python substack_notes_generator.py

# View portfolio
python portfolio_manager.py --report
```

### Key Files for Content

| File | Content |
|------|---------|
| `trades/current/newsletter.html` | Newsletter for Substack |
| `trades/current/tweets.json` | Tweet queue |
| `trades/current/substack_notes/tuesday_note.md` | Tuesday note |
| `trades/current/substack_notes/thursday_note.md` | Thursday note |
| `trades/content_queue.json` | Posting status |

---

*Document generated for marketing plan development and system improvement assessment.*
