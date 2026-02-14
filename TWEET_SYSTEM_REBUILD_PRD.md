# Sterling Signals Tweet System Rebuild — PRD & Implementation Guide

> **Document purpose:** Paint-by-numbers reference for Claude Code to implement the full live-context tweet system, replace the batch architecture, archive the old system safely, and ensure zero breakage to upstream pipelines.
>
> **Created:** 2026-02-10
> **Companion doc:** `TWEET_SYSTEM_ANALYSIS.md` (feasibility analysis)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Pre-Implementation Checklist](#2-pre-implementation-checklist)
3. [Phase 0: Archive & Protect Old System](#3-phase-0-archive--protect-old-system)
4. [Phase 1: Bug Fixes to Existing System](#4-phase-1-bug-fixes-to-existing-system)
5. [Phase 2: Grok Context Gatherer](#5-phase-2-grok-context-gatherer)
6. [Phase 3: Live Tweet Generator (Sonnet)](#6-phase-3-live-tweet-generator-sonnet)
7. [Phase 4: Chart Integration (chart-img)](#7-phase-4-chart-integration-chart-img)
8. [Phase 5: Multi-Account Posting](#8-phase-5-multi-account-posting)
9. [Phase 6: GitHub Actions Workflows](#9-phase-6-github-actions-workflows)
10. [Phase 7: Monitoring & Error Handling](#10-phase-7-monitoring--error-handling)
11. [Phase 8: Testing & Cutover](#11-phase-8-testing--cutover)
12. [File Inventory — What Changes, What Doesn't](#12-file-inventory)
13. [Configuration & Environment Variables](#13-configuration--environment-variables)
14. [Tweet Decision Logic Specification](#14-tweet-decision-logic-specification)
15. [Validation Pipeline Specification](#15-validation-pipeline-specification)
16. [Style Guide Integration](#16-style-guide-integration)
17. [Rollback Procedure](#17-rollback-procedure)

---

## 1. Architecture Overview

### Current system (REPLACING)

```
FRIDAY 4:30PM ET
  Scanner → signals.json + portfolio.csv
  → tweet_generator.py generates 28 tweets/week × 3 accounts
  → Writes to content_queue.json (+ account2, account3)

DAILY (5 slots)
  → twitter_poster.py reads queue, posts next pending tweet
  → Slots 1,6,7 = daily queue; Slots 2,3,4,5 = weekly queue
```

**Problem:** Tweets written Friday with Friday's data. Posted Monday–Friday with zero awareness of live market conditions. Results in stale, repetitive, robotic content.

### New system (BUILDING)

```
EVERY 2-3 HOURS (market hours, 7 slots/day via GitHub Actions)
  1. live_context_gatherer.py → Grok 4.1 Fast API
     - X Search: what's trending in markets now?
     - Web Search: news, earnings, macro events
     - Output: live_context.json (structured market snapshot)

  2. live_tweet_generator.py → Claude Sonnet 4.5 API
     - Input: live_context.json + portfolio.csv + signals.json + style guide
     - Decides: what TYPE of tweet fits this moment?
     - Generates: 3 account variants in one call
     - Validates: port existing 7-step validation pipeline
     - Output: writes to live_content_queue.json

  3. twitter_poster.py (MODIFIED, not replaced)
     - Reads from live_content_queue.json
     - Posts with chart attachment if flagged
     - Same multi-account stagger logic

  4. chart_generator.py (NEW)
     - chart-img.com API with TradingView private layout
     - Generates chart PNG for flagged tweets
     - Falls back to text-only on failure
```

### Key architectural change

The tweet **category** is an OUTPUT of the decision logic (based on what's happening in markets right now), not an INPUT to a schedule planner. The system observes market conditions and decides what to post, just like a real trader.

### Cost comparison

| Component | Current System | New System |
|---|---|---|
| Tweet generation API | ~$15-25/mo (Sonnet, 84 weekly calls) | ~$5/mo (Sonnet, 10 calls/day) |
| Context gathering | $0 (no live data) | ~$5/mo (Grok 4.1 Fast + search tools) |
| Daily generation API | ~$10-15/mo (Sonnet, 15/day) | Included above |
| Charts | $0 (Playwright screenshots, fragile) | ~$5-10/mo (chart-img.com) |
| **Total** | **~$30-45/mo** | **~$15-25/mo** |

---

## 2. Pre-Implementation Checklist

These must be done BEFORE writing any new code. Each has a verification step.

### 2.1 Get xAI API access

- [ ] Sign up at https://console.x.ai
- [ ] Get API key
- [ ] Note promotional credits ($25 signup, optional $150/mo data sharing)
- [ ] **Verify:** Run this curl and confirm valid response:
```bash
curl https://api.x.ai/v1/chat/completions \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"grok-3-fast","messages":[{"role":"user","content":"What stocks are trending on X right now?"}],"search_parameters":{"mode":"auto"}}'
```

### 2.2 Verify X API tier

- [ ] Check current X Developer tier at https://developer.x.com/en/portal/dashboard
- [ ] Confirm free tier allows 1,500 tweets/month (50/day — we need ~10/day × 3 accounts = 30/day = 900/mo)
- [ ] If free tier insufficient, upgrade to Basic ($100/mo, 3,000 posts/mo) or check current tier limits
- [ ] **Verify:** Check twitter_poster.py dry-run still works: `python -m distribution.twitter_poster --dry-run`

### 2.3 Set up chart-img.com

- [ ] Sign up at https://chart-img.com
- [ ] Get API key
- [ ] Save a TradingView layout with Sterling Signals indicators (Blue Diamonds, HMA, Banker, Gold Zones)
- [ ] Note the layout ID from TradingView URL
- [ ] Get TradingView session cookies (CFSESSION or similar)
- [ ] **Verify:** Test API call generates a chart:
```bash
curl -X POST "https://api.chart-img.com/v2/tradingview/advanced-chart/storage" \
  -H "Authorization: Bearer $CHARTIMG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"NASDAQ:AAPL","interval":"1W","layout_id":"YOUR_LAYOUT_ID","session":"YOUR_TV_SESSION"}'
```

### 2.4 Fix Account 2 credentials

- [ ] Check GitHub Secrets for `X2_API_KEY`, `X2_API_SECRET`, `X2_ACCESS_TOKEN`, `X2_ACCESS_SECRET`
- [ ] Regenerate credentials at https://developer.x.com if expired
- [ ] Update GitHub Secrets
- [ ] **Verify:** `python -m distribution.twitter_poster --account account2 --dry-run` succeeds

### 2.5 Decide account strategy

- [ ] **Option A:** All 3 accounts post same content, slightly reworded (current approach, simpler)
- [ ] **Option B:** Each account has a different angle (e.g., main = all-purpose, account2 = charts-heavy, account3 = engagement-heavy)
- [ ] Decision affects Phase 5 implementation. Default to Option A if unsure.

---

## 3. Phase 0: Archive & Protect Old System

**Goal:** Move all files being replaced into a versioned fallback folder so nothing is lost and reverting is one command away.

### 3.0.1 Create archive directory

```bash
mkdir -p archive/batch_tweet_system_v1/content
mkdir -p archive/batch_tweet_system_v1/distribution
mkdir -p archive/batch_tweet_system_v1/config_snapshots
mkdir -p archive/batch_tweet_system_v1/workflows
mkdir -p archive/batch_tweet_system_v1/queue_snapshots
```

### 3.0.2 Copy files being replaced (NOT move — keep originals until cutover)

```bash
# Content generation files
cp content/tweet_generator.py archive/batch_tweet_system_v1/content/
cp content/reaction_generator.py archive/batch_tweet_system_v1/content/
cp content/models.py archive/batch_tweet_system_v1/content/

# Distribution files (poster will be modified, not replaced)
cp distribution/twitter_poster.py archive/batch_tweet_system_v1/distribution/

# Config snapshots
cp config/settings.py archive/batch_tweet_system_v1/config_snapshots/
cp config/banned_terms.py archive/batch_tweet_system_v1/config_snapshots/

# Workflow snapshots
cp .github/workflows/daily_post.yml archive/batch_tweet_system_v1/workflows/
cp .github/workflows/friday_scan.yml archive/batch_tweet_system_v1/workflows/

# Current queue state
cp trades/content_queue*.json archive/batch_tweet_system_v1/queue_snapshots/ 2>/dev/null || true
cp trades/daily_content_queue*.json archive/batch_tweet_system_v1/queue_snapshots/ 2>/dev/null || true
```

### 3.0.3 Create archive README

Create `archive/batch_tweet_system_v1/README.md`:

```markdown
# Batch Tweet System v1 — Archive

Archived: YYYY-MM-DD
Reason: Replaced by live-context tweet system (Grok + Sonnet hybrid)

## What this was
- Friday batch generation of 28 tweets/week using Claude API
- 3-account system with content_queue.json per account
- twitter_poster.py reading from queues on schedule (5 slots/day)

## How to restore
1. Copy all files back to their original locations
2. Restore workflow files to .github/workflows/
3. Re-run: python -m content.tweet_generator --signals trades/signals.json --portfolio trades/portfolio.csv
4. Verify: python -m distribution.twitter_poster --dry-run

## Files
- content/ — tweet_generator.py, reaction_generator.py, models.py
- distribution/ — twitter_poster.py (pre-modification snapshot)
- config_snapshots/ — settings.py, banned_terms.py at time of archive
- workflows/ — daily_post.yml, friday_scan.yml at time of archive
- queue_snapshots/ — content queue JSON files at time of archive
```

### 3.0.4 Git commit the archive

```bash
git add archive/batch_tweet_system_v1/
git commit -m "Archive batch tweet system v1 before live-context rebuild"
```

---

## 4. Phase 1: Bug Fixes to Existing System

These fixes apply to the current system and carry forward into the new system. Do them first.

### 4.1 Fix BST/Substack substring matching in twitter_poster.py

**File:** `distribution/twitter_poster.py`
**Lines:** 140-144
**Bug:** `term.lower() in text_lower` does substring match, so "BST" matches inside "su**BST**ack". Every Substack URL gets blocked.
**Note:** `tweet_generator.py` already has this fix at lines 1391-1394. The poster doesn't.

**Current code (BROKEN):**
```python
# 2. Check for critical banned terms
text_lower = text.lower()
for term in CRITICAL_BANNED:
    if term.lower() in text_lower:
        return (False, f"BLOCKED: Banned term '{term}' in tweet")
```

**Fixed code:**
```python
# 2. Check for critical banned terms (word-boundary for short terms)
text_lower = text.lower()
for term in CRITICAL_BANNED:
    term_lower = term.lower()
    if len(term) <= 4 and term.isascii():
        # Short terms need word-boundary matching to avoid false positives
        # e.g. "BST" matching inside "substack", "HMA" inside "PHARMA"
        if re.search(r'\b' + re.escape(term_lower) + r'\b', text_lower):
            return (False, f"BLOCKED: Banned term '{term}' in tweet")
    else:
        if term_lower in text_lower:
            return (False, f"BLOCKED: Banned term '{term}' in tweet")
```

**Verification:**
```python
# Should pass (contains "substack" but not standalone "BST"):
validate_before_post({"text": "Read the full breakdown on substack.com/sterling", "category": "NEWSLETTER_CTA"})
# Should block (contains standalone "BST"):
validate_before_post({"text": "Analysis using BST time zone", "category": "EDUCATIONAL"})
```

**Also add `import re` at the top of twitter_poster.py if not already imported.** (Check — it IS imported at line ~25.)

### 4.2 Fix Account 2 credentials (manual, not code)

- This is a GitHub Secrets / X Developer Portal task, not a code change
- Verify after fixing: check `content_queue_account2.json` for `"status": "failed"` entries
- Clear failed entries from queue after fixing credentials

---

## 5. Phase 2: Grok Context Gatherer

**New file:** `content/live_context_gatherer.py`
**Purpose:** Query Grok 4.1 Fast with X Search + Web Search to get a structured snapshot of what's happening in markets RIGHT NOW, filtered through Sterling Signals' themes and portfolio.
**Estimated lines:** ~250-350

### 5.1 Input data

The gatherer needs access to:

1. **Portfolio holdings** — `trades/portfolio.csv` (read current open positions, tickers, entry prices, current P&L)
2. **Scanner signals** — `trades/signals.json` (latest PASS/CONSIDER signals, themes)
3. **Theme list** — hardcoded or from config (copper, infrastructure, defense, AI/data centers, rare earth, quantum, space, crypto mining, nuclear)
4. **Recent tweet history** — `trades/live_content_queue.json` (avoid repeating what was just posted)

### 5.2 Grok API call specification

```python
import openai  # xAI uses OpenAI-compatible API

client = openai.OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

response = client.chat.completions.create(
    model="grok-3-fast",
    messages=[
        {
            "role": "system",
            "content": CONTEXT_GATHERER_SYSTEM_PROMPT  # See 5.3
        },
        {
            "role": "user",
            "content": build_context_query(portfolio, signals, themes, recent_tweets)  # See 5.4
        }
    ],
    search_parameters={"mode": "auto"},  # Enables X Search + Web Search
    temperature=0.3,
)
```

**Important:** xAI uses the OpenAI SDK format. Install `openai` package. The `search_parameters` field enables Grok's built-in live search — no separate tool calls needed.

### 5.3 System prompt for context gatherer

```
You are a market research assistant for a momentum trading newsletter called Sterling Signals. Your job is to scan current market conditions and return a structured JSON report.

You have access to X Search and Web Search. Use them to find:
1. What's happening in US stock markets right now (indices, futures, major moves)
2. News affecting these specific themes: {themes_list}
3. Price action on these specific tickers: {portfolio_tickers}
4. What FinTwit is discussing (trending stock topics on X)
5. Any macro events (Fed, earnings, tariffs, geopolitics)

Return ONLY valid JSON in this exact format — no markdown, no commentary:
{
  "timestamp": "ISO-8601",
  "market_snapshot": {
    "spy_move": "+0.3%",
    "qqq_move": "-0.1%",
    "vix": "18.5",
    "market_mood": "mixed|bullish|bearish|volatile|quiet",
    "headline": "one-sentence summary of today's market"
  },
  "portfolio_movers": [
    {"ticker": "$WCC", "move": "+2.1%", "price": "$322.40", "context": "infrastructure spending bill news"}
  ],
  "theme_activity": [
    {"theme": "copper", "status": "active|quiet|breaking", "detail": "copper futures up 1.2% on China stimulus"}
  ],
  "fintwit_trending": ["topic1", "topic2", "topic3"],
  "news_events": [
    {"event": "Fed minutes released", "impact": "hawkish tone, rates higher for longer", "relevance": "high|medium|low"}
  ],
  "tweet_opportunities": [
    {
      "type": "MARKET_REACTION|RECEIPT|SIGNAL_ALERT|DIP_OPPORTUNITY|THEME_MOMENTUM|ENGAGEMENT",
      "reason": "why this is tweetable right now",
      "tickers": ["$WCC"],
      "urgency": "high|medium|low"
    }
  ]
}
```

### 5.4 User prompt builder

```python
def build_context_query(portfolio_df, signals, themes, recent_tweets):
    """Build the user message for Grok with current portfolio/signals context."""

    # Extract open positions
    open_positions = []
    for _, row in portfolio_df.iterrows():
        if row.get('status') == 'OPEN':
            open_positions.append(f"${row['ticker']}: entry ${row['entry_price']}, current ${row.get('current_price', 'N/A')}")

    # Extract recent signals
    pass_signals = [s for s in signals if s.get('final_signal') == 'PASS']
    consider_signals = [s for s in signals if s.get('final_signal') == 'CONSIDER']

    # Last 5 posted tweets (to avoid repetition)
    recent_topics = [t.get('primary_ticker', '') for t in recent_tweets[-5:]]

    return f"""
Current portfolio positions:
{chr(10).join(open_positions)}

Recent scanner signals (PASS): {', '.join(f"${s['ticker']}" for s in pass_signals)}
Recent scanner signals (CONSIDER): {', '.join(f"${s['ticker']}" for s in consider_signals)}

Themes we track: {', '.join(themes)}

Topics we've tweeted about in last 3 hours (AVOID repeating): {', '.join(recent_topics)}

What's happening in markets right now that's relevant to our portfolio and themes?
Focus on actionable observations, not generic commentary.
"""
```

### 5.5 Output specification

Write output to `trades/live_context.json`. Overwritten each run. Include a staleness indicator:

```python
import json
from datetime import datetime

def save_context(context_data, output_path="trades/live_context.json"):
    context_data["gathered_at"] = datetime.utcnow().isoformat()
    context_data["is_market_hours"] = is_market_open()  # Helper function
    with open(output_path, "w") as f:
        json.dump(context_data, f, indent=2)
```

### 5.6 Market hours helper

```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

def is_market_open():
    """Check if US markets are currently open (9:30 AM - 4:00 PM ET, weekdays)."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:  # Saturday/Sunday
        return False
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now_et.time() <= market_close

def is_extended_hours():
    """Check if in pre-market (7:00-9:30) or after-hours (4:00-6:30)."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False
    return (time(7, 0) <= now_et.time() < time(9, 30)) or \
           (time(16, 0) < now_et.time() <= time(18, 30))
```

### 5.7 Fallback behavior

If Grok API fails (timeout, rate limit, server error):
1. Log the error
2. Check if `trades/live_context.json` exists and is < 4 hours old → use stale context with `"context_stale": true` flag
3. If no usable context → generate a "portfolio-only" tweet using just portfolio.csv data (no live market color). Flag as `"fallback_mode": true`
4. Never silently skip — always either post or log why not

### 5.8 CLI interface

```bash
# Standalone test
python -m content.live_context_gatherer

# With custom output
python -m content.live_context_gatherer --output trades/live_context.json

# Dry run (print context, don't save)
python -m content.live_context_gatherer --dry-run
```

### 5.9 Error budget

- Grok API call timeout: 30 seconds
- Max retries: 2 (with exponential backoff)
- Cost per call: ~$0.01-0.02 (including search tools)
- Daily budget cap: $1.00 (kills process if exceeded)

---

## 6. Phase 3: Live Tweet Generator (Sonnet)

**New file:** `content/live_tweet_generator.py`
**Purpose:** Take Grok's market context + portfolio data → decide what to tweet → generate 3 account variants → validate → write to queue.
**Estimated lines:** ~500-700

### 6.1 Core flow

```python
def generate_live_tweet(context_path, portfolio_path, signals_path, style_guide_path):
    """Main entry point. Called by GitHub Actions every 2-3 hours."""

    # 1. Load inputs
    context = load_json(context_path)        # From Phase 2
    portfolio = load_portfolio(portfolio_path)
    signals = load_json(signals_path)
    style_guide = load_text(style_guide_path)
    recent_tweets = load_recent_tweets()      # From live queue

    # 2. Decide what to tweet (see Section 14)
    tweet_decision = decide_tweet_type(context, portfolio, signals, recent_tweets)

    # 3. If nothing worth tweeting, skip
    if tweet_decision["action"] == "skip":
        log(f"Skipping: {tweet_decision['reason']}")
        return {"status": "skipped", "reason": tweet_decision["reason"]}

    # 4. Generate tweet via Claude Sonnet
    raw_tweets = call_sonnet(tweet_decision, context, portfolio, style_guide)

    # 5. Validate all 3 variants
    validated = []
    for variant in raw_tweets:
        result = validate_tweet(variant, portfolio, signals)
        if result.passed:
            validated.append(variant)
        else:
            # Attempt repair (max 2 tries)
            repaired = repair_tweet(variant, result.failures, tweet_decision, context, style_guide)
            if repaired:
                validated.append(repaired)

    # 6. Write to queue
    if validated:
        write_to_live_queue(validated, tweet_decision)
        return {"status": "generated", "count": len(validated)}
    else:
        log("All variants failed validation")
        return {"status": "failed", "reason": "validation_failure"}
```

### 6.2 Claude Sonnet API call

```python
import anthropic

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

def call_sonnet(decision, context, portfolio, style_guide):
    """Generate 3 tweet variants in a single Sonnet call."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        system=build_tweet_system_prompt(style_guide),
        messages=[{
            "role": "user",
            "content": build_tweet_user_prompt(decision, context, portfolio)
        }]
    )

    return parse_tweet_variants(response.content[0].text)
```

### 6.3 System prompt for Sonnet tweet generation

This is the CRITICAL prompt. It must produce tweets indistinguishable from the reference accounts.

```
You are the voice of Sterling Signals, a momentum trading newsletter on FinTwit.

STYLE RULES (non-negotiable):
{style_guide_content}

YOUR TASK:
Generate exactly 3 tweet variants for the same moment. Each variant must:
- Sound like a different human wrote it (not just rearranged words)
- Be ≤280 characters
- Contain at least one specific element (ticker, price, %, or named theme)
- Match the tone of these reference accounts: confident but not arrogant, specific not vague, casual not corporate

FORMATTING RULES:
- Return ONLY valid JSON — no markdown, no commentary
- Format: {"tweets": [{"text": "...", "category": "...", "primary_ticker": "...", "chart_recommended": true/false, "account": "variant_1|variant_2|variant_3"}, ...]}
- Categories: MARKET_REACTION, RECEIPT, SIGNAL_ALERT, DIP_OPPORTUNITY, THEME_MOMENTUM, ENGAGEMENT, EDUCATIONAL, NEWSLETTER_CTA
- chart_recommended: true if tweet references a specific ticker with price action

ABSOLUTE BANS:
- Never fabricate tickers, prices, or percentages not in the provided data
- Never use: "our scanner", "filtered X stocks", "save this post", "bookmark this"
- Never use hashtags
- Never exceed 280 characters
- Never mention losses or negative P&L
- Never use UK references (BST, GMT, GBP, ISA)
- Never reference being an AI, bot, or automated system
- Keep "NFA" to ≤30% of tweets
```

### 6.4 User prompt builder

```python
def build_tweet_user_prompt(decision, context, portfolio):
    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    trending = context.get("fintwit_trending", [])

    return f"""
CURRENT MARKET STATE:
- SPY: {market.get('spy_move', 'N/A')} | QQQ: {market.get('qqq_move', 'N/A')} | VIX: {market.get('vix', 'N/A')}
- Mood: {market.get('market_mood', 'unknown')}
- Headline: {market.get('headline', '')}

YOUR PORTFOLIO MOVERS TODAY:
{json.dumps(movers, indent=2) if movers else 'No significant moves'}

THEME ACTIVITY:
{json.dumps(themes, indent=2) if themes else 'All themes quiet'}

FINTWIT IS DISCUSSING:
{', '.join(trending) if trending else 'Nothing specific'}

TWEET TYPE REQUESTED: {decision['type']}
REASON: {decision['reason']}
FOCUS TICKER(S): {', '.join(decision.get('tickers', []))}

PORTFOLIO CONTEXT (for accuracy — use ONLY these real numbers):
{format_portfolio_for_prompt(portfolio)}

Generate 3 variants now.
"""
```

### 6.5 Port validation pipeline from tweet_generator.py

The existing validation pipeline (lines 1281-1460 of `tweet_generator.py`) should be ported with these modifications:

**Keep as-is:**
- Step 1: Category validation
- Step 2: Ticker/price fabrication check (compare against portfolio + signals)
- Step 3: Banned phrase check (WITH the word-boundary fix)
- Step 4: Winners-only check (no negative percentages)
- Step 4b: Portfolio stats fabrication check
- Step 5: Internal terminology check
- Step 6: Character count check (≤280)
- Step 7: Chart flag consistency

**Add new steps:**
- Step 8: Cross-account deduplication (no two variants should share >60% of words)
- Step 9: Staleness check (if context is >4 hours old, block MARKET_REACTION tweets)
- Step 10: Daily repetition check (don't tweet about same ticker more than 3× per day)

### 6.6 Repair loop

Port from tweet_generator.py (lines 1467-1519). Same pattern: re-call Sonnet with failure reasons appended to prompt. Max 2 attempts per variant.

### 6.7 Queue format

**New file:** `trades/live_content_queue.json`

```json
[
  {
    "id": "live_20260210_143000_v1",
    "text": "Infrastructure spending isn't slowing down. $WCC quietly grinding to $315 while nobody's watching. NFA",
    "category": "RECEIPT",
    "primary_ticker": "WCC",
    "account": "main",
    "chart_recommended": true,
    "chart_path": null,
    "scheduled_time": "2026-02-10T14:30:00-05:00",
    "status": "pending",
    "context_snapshot": {
      "spy_at_generation": "+0.3%",
      "market_mood": "mixed",
      "context_stale": false
    },
    "generated_at": "2026-02-10T14:25:00Z",
    "cost_usd": 0.015
  }
]
```

### 6.8 CLI interface

```bash
# Full generation run
python -m content.live_tweet_generator

# Dry run (generate but don't write to queue)
python -m content.live_tweet_generator --dry-run

# Force specific tweet type
python -m content.live_tweet_generator --force-type RECEIPT

# Use specific context file
python -m content.live_tweet_generator --context trades/live_context.json
```

---

## 7. Phase 4: Chart Integration (chart-img)

**New file:** `content/chart_generator.py`
**Purpose:** Generate TradingView chart images via chart-img.com API for tweets flagged with `chart_recommended: true`.
**Estimated lines:** ~150-200

### 7.1 API integration

```python
import requests

CHARTIMG_BASE = "https://api.chart-img.com/v2/tradingview/advanced-chart"

def generate_chart(ticker, interval="1W", layout_id=None):
    """Generate a chart image for a ticker using chart-img.com."""

    api_key = os.getenv("CHARTIMG_API_KEY")
    tv_session = os.getenv("TRADINGVIEW_SESSION")

    if not api_key:
        logger.warning("CHARTIMG_API_KEY not set, skipping chart generation")
        return None

    payload = {
        "symbol": f"NASDAQ:{ticker}",  # May need exchange prefix mapping
        "interval": interval,
        "width": 800,
        "height": 450,
    }

    # Use private layout if available (includes custom indicators)
    if layout_id and tv_session:
        payload["layout_id"] = layout_id
        payload["session"] = tv_session
        endpoint = f"{CHARTIMG_BASE}/storage"
    else:
        endpoint = CHARTIMG_BASE

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        # Save image
        chart_path = Path(f"trades/charts/live_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.png")
        chart_path.parent.mkdir(parents=True, exist_ok=True)

        with open(chart_path, "wb") as f:
            f.write(resp.content)

        return str(chart_path)

    except Exception as e:
        logger.error(f"Chart generation failed for {ticker}: {e}")
        return None  # Tweet posts without chart — never block on chart failure
```

### 7.2 Exchange prefix mapping

```python
# Common exchanges for Sterling Signals tickers
EXCHANGE_MAP = {
    "WCC": "NYSE", "STRL": "NASDAQ", "MOD": "NYSE",
    "MATV": "NASDAQ", "LUMN": "NYSE",
    # Add more as portfolio grows
}

def get_symbol(ticker):
    exchange = EXCHANGE_MAP.get(ticker, "NASDAQ")  # Default NASDAQ
    return f"{exchange}:{ticker}"
```

### 7.3 Integration with tweet generator

After tweet generation, before writing to queue:

```python
for tweet in validated_tweets:
    if tweet.get("chart_recommended"):
        ticker = tweet.get("primary_ticker")
        if ticker:
            chart_path = generate_chart(ticker)
            tweet["chart_path"] = chart_path  # None if failed — tweet posts without chart
```

### 7.4 TradingView session refresh

The TV session cookies expire periodically. Add a health check:

```python
def check_tv_session():
    """Test if TradingView session is still valid."""
    test_chart = generate_chart("AAPL")
    if test_chart is None:
        logger.warning("TradingView session may be expired — charts will use default layout")
        return False
    os.remove(test_chart)  # Cleanup test file
    return True
```

Run this weekly (add to Sunday health check, Phase 7).

---

## 8. Phase 5: Multi-Account Posting

### 8.1 Modify twitter_poster.py

The existing `twitter_poster.py` needs minimal changes. It already handles multi-account posting and staggered delays. Changes needed:

**Change 1: Add live queue support**

Add a new queue source alongside weekly and daily:

```python
LIVE_QUEUE_FILE = TRADES_DIR / "live_content_queue.json"

# New slot mapping for live system
# Live tweets can go in ANY slot — no weekly/daily distinction
LIVE_SLOTS = {1, 2, 3, 4, 5, 6, 7}
```

**Change 2: Queue selection logic**

Modify `get_queue_for_slot()` to prefer live queue when available:

```python
def get_queue_for_slot(slot: int, account_key: str = 'main') -> Path:
    """Select queue file. Prefer live queue if it has pending content for this account."""

    live_queue = TRADES_DIR / "live_content_queue.json"
    if live_queue.exists():
        queue_data = json.loads(live_queue.read_text())
        pending_for_account = [
            t for t in queue_data
            if t.get("status") == "pending" and t.get("account") == account_key
        ]
        if pending_for_account:
            return live_queue

    # Fallback to old system (weekly/daily queues) if live queue empty
    if slot in DAILY_SLOTS:
        return get_daily_queue_path(account_key)
    return get_queue_path(account_key)
```

**Change 3: Account variant matching**

When reading from live queue, filter by account:

```python
def find_next_live_content(queue, account_key):
    """Find next pending tweet for this specific account."""
    account_map = {"main": "variant_1", "account2": "variant_2", "account3": "variant_3"}
    target = account_map.get(account_key, "variant_1")

    for item in queue:
        if item.get("status") == "pending" and item.get("account") == target:
            return item
    return None
```

### 8.2 Backward compatibility

The poster must work with BOTH old queues and new live queue. If the live system fails for a day, it falls back to the batch-generated weekly/daily queues (if they exist). This provides a safety net during the transition period.

---

## 9. Phase 6: GitHub Actions Workflows

### 9.1 New workflow: `live_tweet.yml`

**File:** `.github/workflows/live_tweet.yml`

```yaml
name: Live Tweet Generation

on:
  schedule:
    # US market hours (ET) — runs every 2 hours
    # 9:30 AM ET = 14:30 UTC (winter) / 13:30 UTC (summer)
    - cron: '30 12 * * 1-5'   # Slot 1: 07:30 ET (pre-market) — weekdays only
    - cron: '0 15 * * 1-5'    # Slot 2: 10:00 ET (morning)
    - cron: '30 17 * * 1-5'   # Slot 3: 12:30 ET (midday)
    - cron: '30 20 * * 1-5'   # Slot 4: 15:30 ET (power hour)
    - cron: '0 23 * * 1-5'    # Slot 5: 18:00 ET (after-hours)
    # Weekend reduced schedule
    - cron: '0 15 * * 0,6'    # Slot W1: 10:00 ET Saturday/Sunday
    - cron: '0 21 * * 0,6'    # Slot W2: 16:00 ET Saturday/Sunday
  workflow_dispatch:
    inputs:
      force_type:
        description: 'Force tweet type (RECEIPT, MARKET_REACTION, etc.)'
        required: false
        type: string
      dry_run:
        description: 'Dry run (generate but do not post)'
        required: false
        type: boolean
        default: false

jobs:
  generate-and-post:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install anthropic openai tweepy requests python-dotenv

      - name: Gather live market context
        env:
          XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
        run: |
          python -m content.live_context_gatherer
        continue-on-error: true  # Tweet can still generate from portfolio-only

      - name: Generate live tweet
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
        run: |
          ARGS=""
          if [ "${{ github.event.inputs.force_type }}" != "" ]; then
            ARGS="$ARGS --force-type ${{ github.event.inputs.force_type }}"
          fi
          if [ "${{ github.event.inputs.dry_run }}" == "true" ]; then
            ARGS="$ARGS --dry-run"
          fi
          python -m content.live_tweet_generator $ARGS

      - name: Generate charts for flagged tweets
        env:
          CHARTIMG_API_KEY: ${{ secrets.CHARTIMG_API_KEY }}
          TRADINGVIEW_SESSION: ${{ secrets.TRADINGVIEW_SESSION }}
          TRADINGVIEW_LAYOUT_ID: ${{ secrets.TRADINGVIEW_LAYOUT_ID }}
        run: |
          python -m content.chart_generator
        continue-on-error: true  # Never block posting on chart failure

      - name: Post tweets (all accounts)
        if: github.event.inputs.dry_run != 'true'
        env:
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
          X2_API_KEY: ${{ secrets.X2_API_KEY }}
          X2_API_SECRET: ${{ secrets.X2_API_SECRET }}
          X2_ACCESS_TOKEN: ${{ secrets.X2_ACCESS_TOKEN }}
          X2_ACCESS_SECRET: ${{ secrets.X2_ACCESS_SECRET }}
          X3_API_KEY: ${{ secrets.X3_API_KEY }}
          X3_API_SECRET: ${{ secrets.X3_API_SECRET }}
          X3_ACCESS_TOKEN: ${{ secrets.X3_ACCESS_TOKEN }}
          X3_ACCESS_SECRET: ${{ secrets.X3_ACCESS_SECRET }}
        run: |
          python -m distribution.twitter_poster --account all --live-queue

      - name: Commit queue updates
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add trades/live_content_queue.json trades/live_context.json trades/charts/ || true
          git diff --cached --quiet || git commit -m "Live tweet: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push || echo "Push failed — will retry next run"
        continue-on-error: true

      - name: Notify on failure
        if: failure()
        run: |
          echo "Live tweet generation failed at $(date -u)"
          # TODO: Add Telegram/Slack notification (Phase 7)
```

### 9.2 Modify existing workflows — DO NOT BREAK

**`friday_scan.yml` — NO CHANGES REQUIRED**

The Friday scan pipeline generates `signals.json`, `portfolio.csv`, charts, newsletter, and Substack content. None of this changes. The live system READS from these outputs but doesn't modify the Friday pipeline.

The only step to verify is Step 5 (tweet generation). Currently it calls either:
```
python -m content.reaction_generator --scanner-file trades/signals.json --output trades/
```
or:
```
python -m content.tweet_generator --signals trades/signals.json --portfolio trades/portfolio.csv
```

**Decision:** KEEP this step running during transition. It populates the weekly `content_queue.json` which serves as a fallback if the live system fails. After 2-4 weeks of stable live operation, this step can be disabled (not deleted — commented out).

**`daily_post.yml` — MODIFY CAREFULLY**

The daily poster currently runs 5 cron jobs calling `twitter_poster.py`. During transition:

1. **Week 1-2:** Run BOTH `daily_post.yml` AND `live_tweet.yml`. The poster's queue selection logic (Phase 5) prefers live queue when available. If live queue is empty (system failed), it falls back to batch queue.

2. **Week 3+:** Once live system is stable, disable `daily_post.yml` cron schedules (comment them out, don't delete). Keep `workflow_dispatch` trigger for manual recovery.

**Modification to `daily_post.yml`:**

Add a flag to skip posting if live system already posted for this slot:

```yaml
      - name: Check if live system already posted
        id: check_live
        run: |
          python -c "
          import json
          from datetime import datetime, timedelta
          from zoneinfo import ZoneInfo
          queue = json.load(open('trades/live_content_queue.json'))
          now = datetime.now(ZoneInfo('America/New_York'))
          recent = [t for t in queue if t.get('status') == 'posted'
                    and datetime.fromisoformat(t['scheduled_time']) > now - timedelta(hours=3)]
          print(f'::set-output name=live_posted::{'true' if recent else 'false'}')
          " 2>/dev/null || echo "::set-output name=live_posted::false"

      - name: Post tweet
        if: steps.check_live.outputs.live_posted != 'true'
        run: |
          python -m distribution.twitter_poster --account all
```

### 9.3 New GitHub Secrets required

| Secret | Purpose | Source |
|---|---|---|
| `XAI_API_KEY` | Grok API authentication | https://console.x.ai |
| `CHARTIMG_API_KEY` | chart-img.com API | https://chart-img.com |
| `TRADINGVIEW_SESSION` | TV session cookies for private layouts | Browser dev tools |
| `TRADINGVIEW_LAYOUT_ID` | Saved TV layout with custom indicators | TradingView URL |

Existing secrets (X API keys, ANTHROPIC_API_KEY) remain unchanged.

---

## 10. Phase 7: Monitoring & Error Handling

### 10.1 Daily cost tracking

Add to `config/settings.py`:

```python
# Live system cost tracking
DAILY_COST_LIMIT_USD = 1.00       # Kill switch — stop generating if exceeded
MONTHLY_COST_LIMIT_USD = 30.00    # Alert threshold
COST_LOG_FILE = TRADES_DIR / "live_cost_log.json"
```

Track costs per API call:

```python
def log_cost(service, model, input_tokens, output_tokens, tool_calls=0):
    """Log API cost to running daily total."""
    PRICING = {
        "grok-3-fast": {"input": 0.20, "output": 0.50},   # per million tokens
        "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    }
    rates = PRICING.get(model, {"input": 3.00, "output": 15.00})
    cost = (input_tokens * rates["input"] / 1_000_000) + \
           (output_tokens * rates["output"] / 1_000_000) + \
           (tool_calls * 0.005)  # X Search / Web Search tool calls

    # Load or create daily log
    log_path = COST_LOG_FILE
    if log_path.exists():
        log = json.loads(log_path.read_text())
    else:
        log = {"date": str(datetime.now().date()), "total_usd": 0, "calls": []}

    # Reset if new day
    if log["date"] != str(datetime.now().date()):
        log = {"date": str(datetime.now().date()), "total_usd": 0, "calls": []}

    log["total_usd"] += cost
    log["calls"].append({"service": service, "model": model, "cost": round(cost, 6), "time": datetime.now().isoformat()})

    log_path.write_text(json.dumps(log, indent=2))

    # Kill switch
    if log["total_usd"] > DAILY_COST_LIMIT_USD:
        raise RuntimeError(f"Daily cost limit exceeded: ${log['total_usd']:.2f} > ${DAILY_COST_LIMIT_USD}")

    return cost
```

### 10.2 Health check system

**New file:** `utils/health_check.py`

Run weekly (Sunday) via GitHub Actions:

```python
def run_health_checks():
    checks = {
        "xai_api": check_xai_api(),
        "anthropic_api": check_anthropic_api(),
        "x_api_main": check_x_api("main"),
        "x_api_account2": check_x_api("account2"),
        "x_api_account3": check_x_api("account3"),
        "chartimg_api": check_chartimg_api(),
        "tv_session": check_tv_session(),
        "portfolio_freshness": check_portfolio_freshness(),
        "cost_this_week": get_weekly_cost(),
    }
    return checks
```

### 10.3 Notification system

For the initial build, use the simplest approach that works: write failures to a JSON file that can be checked manually, and print errors in GitHub Actions logs.

**Future enhancement:** Add Telegram bot or Slack webhook for real-time alerts. Not required for MVP.

### 10.4 Duplicate tweet prevention

Add to `twitter_poster.py`:

```python
def check_duplicate(text, queue):
    """Prevent posting near-identical tweets within 24 hours."""
    from difflib import SequenceMatcher
    now = datetime.now(ZoneInfo("America/New_York"))

    for item in queue:
        if item.get("status") != "posted":
            continue
        posted_time = datetime.fromisoformat(item.get("posted_at", "2000-01-01"))
        if (now - posted_time).total_seconds() > 86400:
            continue
        similarity = SequenceMatcher(None, text.lower(), item["text"].lower()).ratio()
        if similarity > 0.7:
            return True, f"Too similar to tweet posted at {posted_time}: {similarity:.0%} match"
    return False, ""
```

---

## 11. Phase 8: Testing & Cutover

### 11.1 Parallel running (Week 1-2)

1. Deploy `live_tweet.yml` workflow
2. Keep `daily_post.yml` running
3. The poster's queue logic prefers live content but falls back to batch
4. Monitor: compare live vs batch tweet quality in GitHub Actions logs
5. Check: are all 3 accounts posting? Are charts attaching?

### 11.2 Quality validation checklist

Run after first 3 days of live operation:

- [ ] No fabricated tickers (every $TICKER in tweets exists in portfolio/signals)
- [ ] No fabricated prices (every price matches portfolio data within 2%)
- [ ] No banned phrases passing through
- [ ] No tweets exceeding 280 characters
- [ ] Charts attached to ≥30% of tweets
- [ ] All 3 accounts posting without 401 errors
- [ ] No duplicate content across accounts (>60% similarity)
- [ ] No tweet repeating same ticker within 4 hours
- [ ] Cost per day < $1.00
- [ ] Tweets reference actual market conditions (spot-check against market data)

### 11.3 Cutover checklist

When ready to disable batch system:

- [ ] Live system has run successfully for ≥2 weeks
- [ ] No critical failures in last 7 days
- [ ] Cost is within budget
- [ ] Tweet quality is equal or better than batch (manual review)

Then:

1. Comment out Step 5 (tweet generation) in `friday_scan.yml`
2. Comment out cron schedules in `daily_post.yml`
3. Keep both files — don't delete them
4. Git commit: `"Disable batch tweet system — live system is primary"`

### 11.4 Rollback trigger

Re-enable batch system if ANY of:
- Live system fails for 24+ consecutive hours
- Cost exceeds $3/day for 3+ days
- Quality drops noticeably (manual review)
- X API rate limits consistently hit

---

## 12. File Inventory

### New files to create

| File | Phase | Purpose | Estimated Lines |
|---|---|---|---|
| `content/live_context_gatherer.py` | 2 | Grok API market context | 250-350 |
| `content/live_tweet_generator.py` | 3 | Sonnet tweet generation | 500-700 |
| `content/chart_generator.py` | 4 | chart-img.com integration | 150-200 |
| `utils/health_check.py` | 7 | System health monitoring | 100-150 |
| `.github/workflows/live_tweet.yml` | 6 | GitHub Actions workflow | 100-130 |
| `trades/live_content_queue.json` | 3 | Live tweet queue (runtime) | N/A |
| `trades/live_context.json` | 2 | Market context (runtime) | N/A |
| `trades/live_cost_log.json` | 7 | Cost tracking (runtime) | N/A |
| `archive/batch_tweet_system_v1/` | 0 | Full archive of old system | N/A |

### Files to MODIFY (not replace)

| File | Changes | Risk Level |
|---|---|---|
| `distribution/twitter_poster.py` | Add live queue support, fix BST bug, add duplicate check | Medium |
| `config/settings.py` | Add live system constants, cost limits, Grok config | Low |
| `.github/workflows/daily_post.yml` | Add live-system-posted check | Low |

### Files that DO NOT CHANGE

| File | Reason |
|---|---|
| `.github/workflows/friday_scan.yml` | Friday pipeline untouched — generates data that live system reads |
| `core/scanner.py` | Scanner is upstream, not affected |
| `core/portfolio_manager.py` | Portfolio management unchanged |
| `core/thematic_analyzer.py` | Theme analysis unchanged |
| `core/gatekeeper.py` | Gatekeeper unchanged |
| `content/newsletter_compiler.py` | Newsletter unaffected |
| `content/substack_notes_generator.py` | Substack notes unaffected |
| `content/chart_capture.py` | Old chart system retained as backup |
| `content/funnel_graphic.py` | Funnel graphic unchanged |
| `content/market_analyzer.py` | Market analysis unchanged |
| `config/banned_terms.py` | Read by new system, not modified |
| `config/output_paths.py` | No changes needed |
| `config/marketing_vocabulary.py` | Read by validation, not modified |
| `distribution/self_quote_tracker.py` | Self-quote unchanged |
| `distribution/signal_tracker.py` | Signal tracking unchanged |
| `distribution/email_notifier.py` | Email notifications unchanged |

---

## 13. Configuration & Environment Variables

### New environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `XAI_API_KEY` | Yes | — | Grok API authentication |
| `CHARTIMG_API_KEY` | No | — | chart-img.com API (tweets post without charts if missing) |
| `TRADINGVIEW_SESSION` | No | — | TV session for private layouts |
| `TRADINGVIEW_LAYOUT_ID` | No | — | Saved TV layout ID |
| `LIVE_TWEET_MODE` | No | `"auto"` | `"auto"`, `"manual"` (require approval), or `"disabled"` |
| `DAILY_COST_LIMIT` | No | `1.00` | Max USD spend per day |
| `TWEET_APPROVAL_WEBHOOK` | No | — | Slack/Telegram webhook for approval mode |

### New config constants (add to settings.py)

```python
# ═══════════════════════════════════════════════════════════════
# LIVE TWEET SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Models
MODEL_CONTEXT = "grok-3-fast"           # xAI Grok for live context
MODEL_LIVE_TWEET = "claude-sonnet-4-5-20250929"  # Claude Sonnet for tweet generation
XAI_BASE_URL = "https://api.x.ai/v1"

# Cost controls
DAILY_COST_LIMIT_USD = 1.00
MONTHLY_COST_LIMIT_USD = 30.00

# Content controls
MAX_TWEETS_PER_DAY = 12                 # Hard cap — never exceed this
MAX_SAME_TICKER_PER_DAY = 3             # Don't tweet about same ticker 4+ times
CONTEXT_STALENESS_HOURS = 4             # Stale context blocks MARKET_REACTION tweets
MIN_HOURS_BETWEEN_SAME_TICKER = 3       # Minimum gap between tweets about same ticker

# Chart-img
CHARTIMG_API_URL = "https://api.chart-img.com/v2/tradingview/advanced-chart"
CHART_WIDTH = 800
CHART_HEIGHT = 450
CHART_INTERVAL = "1W"                   # Default weekly charts

# Themes (can be moved to a config file later)
TRACKED_THEMES = [
    "copper", "infrastructure", "defense", "AI", "data centers",
    "rare earth", "quantum computing", "space", "crypto mining",
    "nuclear", "semiconductors", "reshoring",
]

# Weekend behavior
WEEKEND_MAX_TWEETS = 4                  # Reduced posting on weekends
WEEKEND_CATEGORIES = ["EDUCATIONAL", "ENGAGEMENT", "NEWSLETTER_CTA", "RECEIPT"]
```

---

## 14. Tweet Decision Logic Specification

This is the CORE innovation — deciding what to tweet based on current conditions.

### 14.1 Decision function

```python
def decide_tweet_type(context, portfolio, signals, recent_tweets):
    """
    Decide what type of tweet to post based on current market conditions.
    Returns: {"action": "tweet"|"skip", "type": str, "reason": str, "tickers": list, "urgency": str}
    """

    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    opportunities = context.get("tweet_opportunities", [])
    is_weekend = datetime.now(ZoneInfo("America/New_York")).weekday() >= 5

    # Check daily tweet count
    tweets_today = count_tweets_today(recent_tweets)
    max_today = WEEKEND_MAX_TWEETS if is_weekend else MAX_TWEETS_PER_DAY
    if tweets_today >= max_today:
        return {"action": "skip", "reason": f"Daily cap reached ({tweets_today}/{max_today})"}

    # Priority 1: Portfolio movers (something in our holdings is moving significantly)
    big_movers = [m for m in movers if abs(float(m.get("move", "0").replace("%", ""))) >= 2.0]
    for mover in big_movers:
        if not recently_tweeted(mover["ticker"], recent_tweets, hours=MIN_HOURS_BETWEEN_SAME_TICKER):
            pct = float(mover["move"].replace("%", ""))
            tweet_type = "RECEIPT" if pct > 0 else "DIP_OPPORTUNITY" if pct < -3 else "MARKET_REACTION"
            return {
                "action": "tweet",
                "type": tweet_type,
                "reason": f"{mover['ticker']} moving {mover['move']}: {mover.get('context', '')}",
                "tickers": [mover["ticker"]],
                "urgency": "high"
            }

    # Priority 2: Theme breakout
    active_themes = [t for t in themes if t.get("status") == "breaking"]
    for theme in active_themes:
        if not recently_tweeted_theme(theme["theme"], recent_tweets, hours=6):
            return {
                "action": "tweet",
                "type": "THEME_MOMENTUM",
                "reason": f"{theme['theme']} breaking: {theme.get('detail', '')}",
                "tickers": find_tickers_for_theme(theme["theme"], portfolio, signals),
                "urgency": "high"
            }

    # Priority 3: Grok-identified opportunities
    for opp in sorted(opportunities, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("urgency", "low"), 3)):
        if opp.get("urgency") in ("high", "medium"):
            return {
                "action": "tweet",
                "type": opp["type"],
                "reason": opp["reason"],
                "tickers": opp.get("tickers", []),
                "urgency": opp["urgency"]
            }

    # Priority 4: Market commentary (if market is doing something notable)
    mood = market.get("market_mood", "quiet")
    if mood in ("volatile", "bearish") and not recently_tweeted_type("MARKET_REACTION", recent_tweets, hours=4):
        return {
            "action": "tweet",
            "type": "MARKET_REACTION",
            "reason": f"Market mood: {mood} — {market.get('headline', '')}",
            "tickers": [m["ticker"] for m in movers[:2]] if movers else [],
            "urgency": "medium"
        }

    # Priority 5: Scheduled content (newsletter CTA 2x/week)
    if should_post_newsletter_cta(recent_tweets):
        return {
            "action": "tweet",
            "type": "NEWSLETTER_CTA",
            "reason": "Scheduled newsletter CTA",
            "tickers": get_best_performing_tickers(portfolio, n=1),
            "urgency": "low"
        }

    # Priority 6: Educational/Engagement filler (if nothing else happening)
    if tweets_today < 4 and not is_weekend:  # Don't skip entirely on quiet days
        return {
            "action": "tweet",
            "type": random.choice(["EDUCATIONAL", "ENGAGEMENT"]),
            "reason": "Quiet market — filler content with live context",
            "tickers": get_best_performing_tickers(portfolio, n=1),
            "urgency": "low"
        }

    # Nothing worth tweeting
    return {"action": "skip", "reason": "No tweetable events and daily minimum met"}
```

### 14.2 Helper functions needed

```python
def recently_tweeted(ticker, recent_tweets, hours=3):
    """Check if ticker was tweeted about in last N hours."""
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    return any(
        t.get("primary_ticker") == ticker and
        datetime.fromisoformat(t.get("generated_at", "2000-01-01")) > cutoff
        for t in recent_tweets if t.get("status") in ("pending", "posted")
    )

def count_tweets_today(recent_tweets):
    """Count tweets generated today."""
    today = datetime.now(ZoneInfo("America/New_York")).date()
    return sum(
        1 for t in recent_tweets
        if datetime.fromisoformat(t.get("generated_at", "2000-01-01")).date() == today
        and t.get("status") in ("pending", "posted")
    )

def should_post_newsletter_cta(recent_tweets, target_per_week=2):
    """Check if newsletter CTA is due (2x/week, prefer Tuesday + Friday)."""
    week_start = datetime.now(ZoneInfo("America/New_York")) - timedelta(days=7)
    ctas_this_week = sum(
        1 for t in recent_tweets
        if t.get("category") == "NEWSLETTER_CTA"
        and datetime.fromisoformat(t.get("generated_at", "2000-01-01")) > week_start
    )
    return ctas_this_week < target_per_week
```

---

## 15. Validation Pipeline Specification

Port from `tweet_generator.py` lines 1281-1460 with these exact steps:

| Step | Check | Action on Fail |
|---|---|---|
| 1 | Category is valid (from VALID_CATEGORIES list) | Repair |
| 2 | Every $TICKER exists in portfolio.csv or signals.json | Repair |
| 2b | Every price is within 5% of actual data | Repair |
| 3 | No banned phrases (word-boundary for ≤4 char terms) | Repair |
| 4 | No negative percentages (winners only) | Repair |
| 4b | No fabricated portfolio stats | Repair |
| 5 | No internal terminology (HMA pivot, BoS, UC↑, banker score) | Repair |
| 6 | ≤280 characters | Repair (truncate or regenerate) |
| 7 | chart_recommended consistent with category | Auto-fix |
| 8 | Cross-account dedup (<60% similarity between variants) | Regenerate variant |
| 9 | Context staleness (block MARKET_REACTION if context >4h old) | Downgrade to RECEIPT |
| 10 | Daily ticker repetition (≤3 per ticker per day) | Skip |

**Import banned terms from existing config:**
```python
from config.banned_terms import ALL_BANNED, CRITICAL_BANNED, check_banned_phrases, check_loser_focus
```

---

## 16. Style Guide Integration

The existing `FINTWIT_STYLE_GUIDE.md` is loaded as part of the Sonnet system prompt. No changes to the style guide are needed — the live context makes the same style rules produce better output because the tweets are grounded in real events.

**How to load:**
```python
STYLE_GUIDE_PATH = BASE_DIR / "FINTWIT_STYLE_GUIDE.md"

def load_style_guide():
    if STYLE_GUIDE_PATH.exists():
        return STYLE_GUIDE_PATH.read_text()
    logger.warning("Style guide not found — using minimal rules")
    return "Write tweets in confident, casual FinTwit voice. ≤280 chars. Always include specific tickers and prices. NFA."
```

---

## 17. Rollback Procedure

If the live system needs to be disabled:

### 17.1 Quick rollback (5 minutes)

```bash
# 1. Disable live workflow
# Go to GitHub → Actions → Live Tweet Generation → disable workflow

# 2. Re-enable batch workflow
# Uncomment cron schedules in .github/workflows/daily_post.yml
# Uncomment Step 5 in .github/workflows/friday_scan.yml (if it was commented out)

# 3. Push changes
git add .github/workflows/
git commit -m "Rollback: disable live tweets, re-enable batch system"
git push
```

### 17.2 Full rollback (restore old code)

```bash
# 1. Copy archived files back
cp archive/batch_tweet_system_v1/distribution/twitter_poster.py distribution/
cp archive/batch_tweet_system_v1/workflows/daily_post.yml .github/workflows/
cp archive/batch_tweet_system_v1/workflows/friday_scan.yml .github/workflows/

# 2. Regenerate weekly queue (if queue is empty/stale)
python -m content.tweet_generator --signals trades/signals.json --portfolio trades/portfolio.csv

# 3. Verify
python -m distribution.twitter_poster --dry-run

# 4. Commit
git add -A
git commit -m "Full rollback: restored batch tweet system v1"
git push
```

### 17.3 New system files are NOT deleted on rollback

The `content/live_*.py` and `content/chart_generator.py` files stay in the repo. They're just not called by any workflow. This means you can re-enable them later without rebuilding.

---

## Implementation Order Summary

| Phase | What | Time Estimate | Dependencies |
|---|---|---|---|
| 0 | Archive old system | 15 min | None |
| 1 | Bug fixes (BST, credentials) | 30 min | None |
| 2 | Grok context gatherer | 1.5 hours | xAI API key |
| 3 | Live tweet generator (Sonnet) | 2-3 hours | Phase 2, Anthropic API |
| 4 | Chart integration | 1 hour | chart-img.com API key |
| 5 | Multi-account posting | 1 hour | Phase 3 |
| 6 | GitHub Actions workflow | 1 hour | Phases 2-5 |
| 7 | Monitoring & error handling | 1 hour | Phase 6 |
| 8 | Testing & cutover | 2-3 weeks | All phases |
| **Total build time** | | **~8-10 hours** | |

---

## Appendix A: Claude Code Session Prompts

### Session 1 prompt (Phases 0-1)

```
Read the file TWEET_SYSTEM_REBUILD_PRD.md in the repo root.

Execute Phase 0 (archive old system) and Phase 1 (bug fixes).

Specifically:
1. Create archive/batch_tweet_system_v1/ with all files listed in Phase 0
2. Fix the BST/Substack substring bug in distribution/twitter_poster.py (see Phase 1, section 4.1)
3. Verify the fix with the test cases provided
4. Commit everything with appropriate messages
```

### Session 2 prompt (Phase 2)

```
Read TWEET_SYSTEM_REBUILD_PRD.md, focusing on Phase 2 (sections 5.1-5.9).

Build content/live_context_gatherer.py following the spec exactly:
- xAI Grok 4.1 Fast API via OpenAI-compatible SDK
- X Search + Web Search enabled via search_parameters
- Reads portfolio.csv + signals.json for context
- Outputs trades/live_context.json
- Includes market hours helper, staleness detection, fallback behavior
- CLI: python -m content.live_context_gatherer [--dry-run] [--output PATH]

Test with: python -m content.live_context_gatherer --dry-run
```

### Session 3 prompt (Phase 3)

```
Read TWEET_SYSTEM_REBUILD_PRD.md, focusing on Phase 3 (sections 6.1-6.8) and sections 14-15 (decision logic and validation).

Build content/live_tweet_generator.py following the spec:
- Decision logic from section 14 (decide_tweet_type)
- Sonnet API call from section 6.2-6.4
- Port validation pipeline from existing tweet_generator.py (section 15)
- Repair loop (max 2 attempts)
- Queue format from section 6.7
- CLI: python -m content.live_tweet_generator [--dry-run] [--force-type TYPE]

Port the validation functions — import from config.banned_terms, don't duplicate.
```

### Session 4 prompt (Phases 4-7)

```
Read TWEET_SYSTEM_REBUILD_PRD.md, focusing on Phases 4-7.

1. Build content/chart_generator.py (section 7)
2. Modify distribution/twitter_poster.py for live queue support (section 8)
3. Create .github/workflows/live_tweet.yml (section 9.1)
4. Add live-system-posted check to daily_post.yml (section 9.2)
5. Add cost tracking to config/settings.py (section 10.1)
6. Build utils/health_check.py (section 10.2)
7. Add new config constants to config/settings.py (section 13)

Critical: DO NOT break friday_scan.yml or the core scanner pipeline.
Verify twitter_poster.py still works with old queues: python -m distribution.twitter_poster --dry-run
```
