# Sterling Signals - Master TODO Checklist

**Last Updated:** January 21, 2026
**Purpose:** Complete all items before testing Friday Scan and Daily Tweet workflows

---

## Progress Summary

| Phase | Status | Items |
|-------|--------|-------|
| Phase 1: External Setup | ✅ Complete | 6/6 complete |
| Phase 2: MCP Configuration | ✅ Complete | 3/3 complete |
| Phase 3: Core Modules | ✅ MVP Complete | 3/3 MVP complete |
| Phase 4: Integration | ✅ Complete | 5/5 complete |
| Phase 5: Testing | 🟡 In Progress | 4/6 complete |

---

## SEQUENTIAL ACTION ORDER

Complete these in exact order:

```
1. ✅ GitHub repo created + secrets configured
2. ✅ Twitter/Anthropic API keys added to GitHub Secrets
3. ✅ TradingView layout ID obtained
4. ✅ Extract Substack credentials (browser)
5. ✅ Configure Substack MCP in Claude Desktop
6. ✅ Complete all core modules
7. ⬜ Run integration tests
8. ⬜ Test Friday workflow (dry-run)
9. ⬜ Test Daily tweet workflow (dry-run)
10. ⬜ Go live
```

---

## Phase 1: External Setup

### ✅ ALL COMPLETED

- [x] **1.1** Create private GitHub repository
- [x] **1.2** Add `ANTHROPIC_API_KEY` to GitHub Secrets
- [x] **1.3** Add X/Twitter credentials to GitHub Secrets:
  - [x] `X_API_KEY`
  - [x] `X_API_SECRET`
  - [x] `X_ACCESS_TOKEN`
  - [x] `X_ACCESS_SECRET`
- [x] **1.4** Obtain TradingView chart layout ID: `rxC5j0SK`
- [x] **1.5** Push existing scanner code to repo
- [x] **1.6** Extract Substack credentials from browser
  - Session token: `s%3Afg0l29tn5tSq93M0kZzVsU_1fWPauoCq...`
  - User ID: `5950124`

---

## Phase 2: MCP Configuration

### ✅ ALL COMPLETED

- [x] **2.1** Open Claude Desktop config file
  - Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

- [x] **2.2** Add Substack MCP server configuration
  - Server: `substack-api` using `substack-mcp@latest`
  - Publication: `https://sterlingsignals.substack.com`

- [x] **2.3** Restart Claude Desktop to load MCP
  - **Action Required:** Quit and reopen Claude Desktop to activate

---

## Phase 3: Core Modules

### ✅ MVP COMPLETE

All MVP modules exist and are functional:

- [x] **3.1** `chart_capture.py` - TradingView screenshots via Playwright
  - [x] `TRADINGVIEW_LAYOUT_ID` set to `rxC5j0SK`
  - [x] `PLAYWRIGHT_USER_DATA_DIR` configured for local profile
  - [ ] Test: `python chart_capture.py --ticker AAPL --headless --skip-wait`

- [x] **3.2** `tweet_generator.py` - Claude API → final tweets
  - [x] Integrates with `parse_briefing_markdown()` from grok_prompts_generator.py
  - [ ] Test: `python tweet_generator.py --mock`

- [x] **3.3** `twitter_poster.py` - Post to X with media
  - [x] Uses correct env vars: `X_API_KEY`, `X_API_SECRET`, etc.
  - [ ] Test: `python twitter_poster.py --dry-run`

### Optional Modules (Not Required for MVP)

- [x] **3.4** `dd_automator.py` - Exists (optional)
- [ ] **3.5** `market_analyzer.py` - Not created (optional)
- [ ] **3.6** `newsletter_compiler.py` - Not created (optional)
- [ ] **3.7** `substack_publisher.py` - Not created (will use MCP instead)

---

## Phase 4: Integration

### ✅ ALL COMPLETE

- [x] **4.1** Directory structure verified:
  ```
  bos_momentum_scanner/
  ├── scanner.py
  ├── thematic_analyzer.py
  ├── gatekeeper.py
  ├── grok_prompts_generator.py
  ├── chart_capture.py           ✅
  ├── tweet_generator.py         ✅
  ├── twitter_poster.py          ✅
  ├── run_friday.sh              ✅
  ├── requirements.txt
  ├── complete_tickers.txt
  ├── trades/
  │   ├── charts/
  │   └── tweets/
  └── .github/
      └── workflows/
          ├── friday_scan.yml    ✅ Created
          └── daily_post.yml     ✅ Fixed env vars
  ```

- [x] **4.2** `friday_scan.yml` exists in `.github/workflows/`
- [x] **4.3** `daily_post.yml` exists in `.github/workflows/`
  - Fixed: Changed `TWITTER_*` to `X_*` to match GitHub Secrets

- [x] **4.4** `run_friday.sh` is executable

- [x] **4.5** Python dependencies documented in requirements.txt
  - Run locally: `pip install -r requirements.txt && playwright install chromium`

---

## Phase 5: Testing

### Local Tests (No API Costs)

- [x] **5.1** Test chart capture: ✅ PASSED (2026-01-21)
  ```bash
  python chart_capture.py --ticker AAPL --skip-wait
  ```
  Result: `trades/charts/AAPL_20260121.png` (1200x630) and `AAPL_20260121_substack.png` (800x500) created

- [x] **5.2** Test tweet generator (mock): ✅ PASSED (2026-01-21)
  ```bash
  python tweet_generator.py --mock
  ```
  Result: `trades/content_queue.json` created with 21 mock tweets

- [x] **5.3** Test twitter poster (dry-run): ✅ PASSED (2026-01-21)
  ```bash
  python twitter_poster.py --dry-run --force
  ```
  Result: Correctly displays pending tweet without posting

### Friday Workflow Test

- [x] **5.4** Test Friday pipeline locally: ✅ PASSED (2026-01-21)
  ```bash
  ./run_friday.sh --test --no-push --skip-charts
  ```
  Result:
  - Scanner ran successfully (no LLM, top 20 tickers)
  - 21 mock tweets generated
  - Newsletter briefing created
  - No git push (as expected)

- [ ] **5.5** Test Friday workflow via GitHub Actions:
  ```
  Go to: GitHub repo → Actions → Friday Weekly Scan → Run workflow
  Set: skip_llm=true, web_search=false
  ```
  Expected: Workflow completes, files committed to repo

### Daily Tweet Workflow Test

- [ ] **5.6** Test daily posting via GitHub Actions:
  ```
  Go to: GitHub repo → Actions → Daily Tweet Posting → Run workflow
  Set: dry_run=true, slot=1
  ```
  Expected:
  - Shows what would be posted
  - No actual tweet posted

---

## Phase 6: Go Live

- [ ] **6.1** Run Friday pipeline with full LLM:
  ```bash
  ./run_friday.sh
  ```

- [ ] **6.2** Verify content_queue.json has 21 tweets

- [ ] **6.3** Post first real tweet:
  ```bash
  python twitter_poster.py --force
  ```

- [ ] **6.4** Enable scheduled workflows (push to main)

- [ ] **6.5** Monitor first Friday run (4:30 PM EST / 21:30 UTC)

- [ ] **6.6** Monitor first daily tweets (Monday 08:00 UK)

---

## Quick Reference: Environment Variables

### Local Development (.env or export)

```bash
# Required
export ANTHROPIC_API_KEY=sk-ant-...

# For Twitter posting
export X_API_KEY=...
export X_API_SECRET=...
export X_ACCESS_TOKEN=...
export X_ACCESS_SECRET=...

# Optional - chart capture uses browser profile instead
export TRADINGVIEW_LAYOUT_ID=rxC5j0SK
```

### GitHub Secrets (Already Configured ✅)

- `ANTHROPIC_API_KEY` ✅
- `X_API_KEY` ✅
- `X_API_SECRET` ✅
- `X_ACCESS_TOKEN` ✅
- `X_ACCESS_SECRET` ✅

---

## Quick Reference: Test Commands

```bash
# Chart capture (first run - allows login)
python chart_capture.py --ticker AAPL

# Chart capture (subsequent runs - skip wait)
python chart_capture.py --ticker AAPL --skip-wait

# Tweet generator (no API)
python tweet_generator.py --mock

# Tweet generator (with API)
python tweet_generator.py

# Twitter poster (no posting)
python twitter_poster.py --dry-run

# Twitter poster (force post)
python twitter_poster.py --force

# Friday pipeline (test mode)
./run_friday.sh --test --no-push

# Friday pipeline (production)
./run_friday.sh
```

---

## Troubleshooting

### Chart capture fails
- First run requires TradingView login in the browser window
- After first login, use `--skip-wait` flag
- Verify `TRADINGVIEW_LAYOUT_ID` is correct (rxC5j0SK)
- Try without `--headless` to see what's happening

### Tweet generator fails
- Check `ANTHROPIC_API_KEY` is set
- Try `--mock` flag first to test without API

### Twitter poster fails
- Verify all 4 X credentials are set (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
- Check X app has "Read and Write" permissions
- Try `--dry-run` first

### GitHub Actions fails
- Check workflow syntax (YAML is whitespace-sensitive)
- Verify all secrets are configured in repo Settings → Secrets
- Check Actions logs for specific error

---

## Notes

- MVP requires: chart_capture.py, tweet_generator.py, twitter_poster.py ✅
- Optional for MVP: dd_automator.py, market_analyzer.py, newsletter_compiler.py, substack_publisher.py
- Substack publishing will use MCP via Claude Desktop (manual for now)
- Charts may not capture in GitHub Actions (no TradingView login) - capture locally

---

## Changelog

### 2026-01-21
- ✅ Added Substack MCP to Claude Desktop config
- ✅ Created `friday_scan.yml` workflow
- ✅ Fixed `daily_post.yml` env vars (TWITTER_* → X_*)
- ✅ Updated all phases to reflect current state
- ✅ Verified all MVP modules exist and are functional
