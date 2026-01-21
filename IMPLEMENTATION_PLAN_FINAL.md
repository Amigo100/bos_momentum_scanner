# Sterling Signals - Implementation Plan (Final)

## Confirmed Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chart Capture | **Playwright** | Keep your custom BoS/Banker indicators |
| Tweet Generation | **Claude API direct** | Skip Grok, generate final tweet text |
| Substack Publishing | **MCP direct** | Write/format directly via Substack MCP |

---

## Implementation Sequence

### Phase 1: Foundation (Priority: P0)

**External Setup (Do Immediately):**
1. Apply for X Developer account → developer.x.com
2. Create private GitHub repo → `sterling-signals-automation`
3. Extract Substack session cookie + user ID
4. Extract TradingView session cookies
5. Note your TradingView chart layout ID

**Code to Create:**

| File | Purpose | Dependencies |
|------|---------|--------------|
| `chart_capture.py` | Playwright + TradingView screenshots | TradingView cookies |
| `dd_automator.py` | Automated due diligence via Claude API | Anthropic API |
| `market_analyzer.py` | Market analysis via Claude API | Anthropic API |

### Phase 2: Content Generation (Priority: P0)

| File | Purpose | Dependencies |
|------|---------|--------------|
| `tweet_generator.py` | Generate final tweets via Claude API | Replaces grok_prompts |
| `content_queue_generator.py` | Build JSON queue for posting | tweet_generator output |
| `newsletter_compiler.py` | Compile HTML newsletter | DD + market analysis |

### Phase 3: Distribution (Priority: P0)

| File | Purpose | Dependencies |
|------|---------|--------------|
| `twitter_poster.py` | Post to X with media | X API credentials |
| `substack_publisher.py` | Publish via MCP | Substack MCP configured |
| `.github/workflows/daily_post.yml` | 3x daily X posting | GitHub repo |
| `.github/workflows/friday_scan.yml` | Friday pipeline | GitHub repo |

### Phase 4: Orchestration (Priority: P1)

| File | Purpose | Dependencies |
|------|---------|--------------|
| `run_friday.sh` | Orchestrate full Friday pipeline | All Phase 1-3 |
| `run_daily.sh` | Local testing of daily posts | twitter_poster.py |

---

## Claude Code Session Plan

### Session 1: Chart Capture with Playwright

```
[Act] Create chart_capture.py that:
      - Uses Playwright with persistent Chrome profile
      - Loads TradingView with your saved layout (BoS/Banker indicators)
      - Captures charts at 1200x630 (X card size) and 800x500 (Substack)
      - Saves to trades/charts/{TICKER}_{date}.png
      - Takes list of tickers as input
      - Has --headless flag for production runs
```

**Key implementation details:**
- Use `launch_persistent_context()` to reuse your logged-in TradingView session
- Wait for indicators to fully load before screenshot
- Your layout ID goes in the URL: `tradingview.com/chart/{LAYOUT_ID}/?symbol={TICKER}`

### Session 2: DD Automation

```
[Act] Create dd_automator.py that:
      - Takes PASS signals from gatekeeper output
      - Calls Claude API with web search enabled
      - Uses existing DD prompt templates from due_diligence_prompts.py
      - Generates Deal Memo for each ticker
      - Saves to trades/due_diligence/{TICKER}_DD_{date}.md
      - Returns summary dict for newsletter compilation
      - Has --skip-dd flag for cost-conscious testing
```

**Cost estimate:** ~$0.50-1.00 per ticker with web search

### Session 3: Market Analysis

```
[Act] Create market_analyzer.py that:
      - Calls Claude API with web search
      - Analyzes: VIX, sector performance, macro headlines, Fed/rates
      - Generates 300-500 word market summary
      - Saves to trades/market_analysis_{date}.md
      - Returns content for newsletter compilation
```

**Cost estimate:** ~$0.30-0.50 per run

### Session 4: Tweet Generator (Replace Grok Prompts)

```
[Act] Create tweet_generator.py that:
      - Takes scanner output (PASS signals, themes, sell signals, positions)
      - Generates 21 final tweets for the week (3 per day)
      - Uses Claude API to write engaging financial content
      - Includes $TICKER mentions, emojis, CTAs
      - Maps each tweet to a chart file path
      - Outputs structured data for content_queue_generator.py
      
      Tweet categories:
      - Morning: Market outlook, theme highlight, position update
      - Midday: New signal spotlight, theme deep-dive, educational
      - Evening: Watchlist, sell signal alerts, week ahead preview
```

### Session 5: Content Queue Generator

```
[Act] Create content_queue_generator.py that:
      - Takes tweet_generator output
      - Schedules tweets across Mon-Sun, 3 slots per day
      - Creates content_queue.json with structure:
        {
          "id": "signal_AAPL_1",
          "status": "pending",
          "scheduled_date": "2026-01-27",
          "slot": 1,  // 1=morning, 2=midday, 3=evening
          "text": "Full tweet text here...",
          "image_path": "charts/AAPL_20260124.png",
          "ticker": "AAPL",
          "category": "buy_signal"
        }
```

### Session 6: Twitter Poster

```
[Act] Create twitter_poster.py that:
      - Reads content_queue.json
      - Finds next pending tweet for current slot
      - Uploads chart image via Tweepy v1.1 media endpoint
      - Posts tweet via Tweepy v2 client
      - Marks as posted with timestamp and tweet_id
      - Commits updated queue back to repo
      - Has --dry-run flag for testing
```

### Session 7: Newsletter Compiler

```
[Act] Create newsletter_compiler.py that:
      - Combines: market analysis, theme summaries, PASS signals with DD, 
        open positions, sell signals
      - Generates HTML formatted for Substack
      - Includes [CHART: TICKER] placeholders or embedded base64 images
      - Outputs to trades/newsletter_{date}.html
```

### Session 8: Substack Publisher

```
[Act] Create substack_publisher.py that:
      - Reads compiled newsletter HTML
      - Uses Substack MCP server to create draft
      - Or: Uses unofficial Substack API directly
      - Handles image uploads
      - Creates as draft (manual review before publish)
```

### Session 9: GitHub Actions Workflows

```
[Act] Create .github/workflows/friday_scan.yml:
      - Triggers: Friday 21:30 UTC (4:30 PM EST)
      - Runs: Full scanner pipeline
      - Commits: All outputs to repo

[Act] Create .github/workflows/daily_post.yml:
      - Triggers: 08:00, 12:30, 18:00 UK time (Mon-Sun)
      - Runs: twitter_poster.py
      - Commits: Updated content_queue.json
```

### Session 10: Friday Orchestrator

```
[Act] Create run_friday.sh that runs in sequence:
      1. python scanner.py --web-search --archive
      2. python chart_capture.py --tickers-from trades/latest_signals.json
      3. python dd_automator.py --signals trades/latest_signals.json
      4. python market_analyzer.py
      5. python newsletter_compiler.py
      6. python tweet_generator.py
      7. python content_queue_generator.py
      8. python substack_publisher.py --draft
      9. git add . && git commit -m "Weekly scan $(date)" && git push
```

---

## File Structure (Target)

```
sterling-signals-automation/
├── # EXISTING (copy from current project)
├── scanner.py
├── thematic_analyzer.py
├── gatekeeper.py
├── portfolio_manager.py
├── email_notifier.py
├── due_diligence_prompts.py      # Keep for prompt templates
├── complete_tickers.txt
│
├── # NEW MODULES
├── chart_capture.py              # Playwright + TradingView
├── dd_automator.py               # Automated DD via Claude
├── market_analyzer.py            # Market analysis via Claude
├── tweet_generator.py            # Final tweet generation
├── content_queue_generator.py    # Build posting queue
├── twitter_poster.py             # X posting with media
├── newsletter_compiler.py        # HTML newsletter
├── substack_publisher.py         # MCP publishing
│
├── # ORCHESTRATION
├── run_friday.sh                 # Friday pipeline
├── run_daily.sh                  # Local daily test
│
├── # GITHUB ACTIONS
├── .github/
│   └── workflows/
│       ├── friday_scan.yml
│       └── daily_post.yml
│
├── # OUTPUTS
├── trades/
│   ├── charts/                   # {TICKER}_{date}.png
│   ├── due_diligence/            # {TICKER}_DD_{date}.md
│   ├── newsletters/              # newsletter_{date}.html
│   ├── content_queue.json        # Posting queue
│   ├── latest_newsletter_briefing.md
│   └── latest_signals.json       # For chart_capture input
│
├── # CONFIG
├── config/
│   ├── claude_desktop_config.json.example
│   └── .env.example
│
├── # DOCS
├── requirements.txt
├── README.md
└── SETUP.md
```

---

## Claude Desktop MCP Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "substack-api": {
      "command": "npx",
      "args": ["-y", "substack-mcp@latest"],
      "env": {
        "SUBSTACK_PUBLICATION_URL": "https://sterlingsignals.substack.com",
        "SUBSTACK_SESSION_TOKEN": "YOUR_SESSION_TOKEN",
        "SUBSTACK_USER_ID": "YOUR_USER_ID"
      }
    }
  }
}
```

**To get your Substack credentials:**
1. Open Substack dashboard in Chrome
2. DevTools → Network tab → filter XHR
3. Find any API call, look at Cookie header
4. Extract `substack.sid=...` or `connect.sid=...` value
5. For user ID: find `publication_user` call → Preview → `user.id`

---

## GitHub Secrets Required

| Secret | Source |
|--------|--------|
| `ANTHROPIC_API_KEY` | Your existing key |
| `X_API_KEY` | X Developer Portal |
| `X_API_SECRET` | X Developer Portal |
| `X_ACCESS_TOKEN` | X Developer Portal |
| `X_ACCESS_SECRET` | X Developer Portal |
| `TRADINGVIEW_SESSION_ID` | Browser cookies |
| `TRADINGVIEW_SESSION_SIGN` | Browser cookies |
| `TRADINGVIEW_LAYOUT_ID` | Your chart URL |

---

## Testing Strategy

### Unit Testing (No API Costs)

```bash
# Test chart capture with one ticker
python chart_capture.py --ticker AAPL --headless

# Test tweet generator with mock data
python tweet_generator.py --mock

# Test twitter poster dry run
python twitter_poster.py --dry-run

# Test content queue structure
python content_queue_generator.py --validate-only
```

### Integration Testing (Low Cost)

```bash
# Run scanner without web search
python scanner.py --no-llm --top 10

# Run DD on single ticker
python dd_automator.py --ticker AAPL --no-web-search

# Test full Friday pipeline with --dry-run flags
./run_friday.sh --test
```

### Production Run

```bash
# Full Friday pipeline
./run_friday.sh

# Or via GitHub Actions
# Push to main → Actions → Run workflow manually
```

---

## Estimated Costs (Weekly)

| Component | Cost |
|-----------|------|
| Scanner + Theme + Gatekeeper | $2-3 |
| DD Automation (6 tickers avg) | $4-5 |
| Market Analysis | $0.40 |
| Tweet Generation (21 tweets) | $1.50 |
| Newsletter Compilation | $0.30 |
| **Total** | **~$8-10/week** |

**Time Saved:** 4-5 hours/week

---

## Next Steps

1. **Immediate:** Apply for X Developer account (do today)
2. **Immediate:** Create GitHub repo and configure secrets
3. **This Week:** Extract all cookies/credentials (see SETUP.md)
4. **Claude Code:** Start with Session 1 (chart_capture.py)

Ready to start with Session 1?
