#!/usr/bin/env python3
"""
LIVE CONTEXT GATHERER - Real-Time Market Snapshot via Grok
==========================================================

Queries xAI Grok via the Responses API with X Search + Web Search to get a
structured snapshot of current market conditions, filtered through Sterling
Signals' portfolio holdings and tracked themes.

Output is consumed by live_tweet_generator.py to produce timely tweets.

Usage:
    python -m content.live_context_gatherer              # Gather and save
    python -m content.live_context_gatherer --dry-run    # Print only, don't save
    python -m content.live_context_gatherer --output PATH # Custom output path

Environment Variables:
    XAI_API_KEY    - xAI API key (required)
"""

import os
import sys
import csv
import json
import re
import argparse
import logging
import time
from datetime import datetime, timedelta, time as dtime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from config import (
        TRADES_DIR, TRACKED_THEMES, CONTEXT_STALENESS_HOURS,
        MODEL_CONTEXT, XAI_BASE_URL,
    )
    MODEL = MODEL_CONTEXT
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TRADES_DIR = BASE_DIR / "trades"
    MODEL = "grok-4-fast-non-reasoning"
    XAI_BASE_URL = "https://api.x.ai/v1"
    CONTEXT_STALENESS_HOURS = 4
    TRACKED_THEMES = [
        "copper", "infrastructure", "defense", "AI", "data centers",
        "rare earth", "quantum computing", "space", "crypto mining",
        "nuclear", "semiconductors", "reshoring",
    ]

# Local-only constants (not in config)
PORTFOLIO_FILE = TRADES_DIR / "portfolio.csv"
SIGNALS_FILE = TRADES_DIR / "signals.json"
LIVE_QUEUE_FILE = TRADES_DIR / "live_content_queue.json"
LIVE_CONTEXT_FILE = TRADES_DIR / "live_context.json"
MAX_RETRIES = 2
API_TIMEOUT = 30


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContextResult:
    """Result from live context gathering."""
    context_data: Dict = field(default_factory=dict)
    cost: float = 0.0
    error: str = ""
    stale: bool = False

    def success(self) -> bool:
        return bool(self.context_data) and not self.error


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET HOURS HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def is_market_open() -> bool:
    """Check if US markets are currently open (9:30 AM - 4:00 PM ET, weekdays)."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False
    return dtime(9, 30) <= now_et.time() <= dtime(16, 0)


def is_extended_hours() -> bool:
    """Check if in pre-market (7:00-9:30) or after-hours (4:00-6:30)."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False
    return (dtime(7, 0) <= now_et.time() < dtime(9, 30)) or \
           (dtime(16, 0) < now_et.time() <= dtime(18, 30))


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_open_positions() -> List[Dict]:
    """Load open positions from portfolio.csv."""
    if not PORTFOLIO_FILE.exists():
        return []
    positions = []
    with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'OPEN':
                positions.append(row)
    return positions


def load_signals() -> Dict:
    """Load latest scanner signals from signals.json."""
    if not SIGNALS_FILE.exists():
        return {}
    with open(SIGNALS_FILE, 'r') as f:
        return json.load(f)


def load_recent_tweets() -> List[Dict]:
    """Load recent tweets from live content queue (if exists)."""
    if not LIVE_QUEUE_FILE.exists():
        return []
    try:
        with open(LIVE_QUEUE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

CONTEXT_SYSTEM_PROMPT = """You are a market research assistant for a momentum trading newsletter called Sterling Signals. Your job is to scan current market conditions and return a structured JSON report.

You have access to X Search and Web Search. Use them to find:
1. What's happening in US stock markets right now (indices, futures, major moves)
2. News affecting these specific themes: {themes_list}
3. Price action on these specific tickers: {portfolio_tickers}
4. What FinTwit is discussing (trending stock topics on X)
5. Any macro events (Fed, earnings, tariffs, geopolitics)

Return ONLY valid JSON in this exact format — no markdown, no commentary:
{{
  "timestamp": "ISO-8601",
  "market_snapshot": {{
    "spy_move": "+0.3%",
    "qqq_move": "-0.1%",
    "vix": "18.5",
    "market_mood": "mixed|bullish|bearish|volatile|quiet",
    "headline": "one-sentence summary of today's market"
  }},
  "portfolio_movers": [
    {{"ticker": "$WCC", "move": "+2.1%", "price": "$322.40", "context": "infrastructure spending bill news"}}
  ],
  "theme_activity": [
    {{"theme": "copper", "status": "active|quiet|breaking", "detail": "copper futures up 1.2% on China stimulus"}}
  ],
  "fintwit_trending": ["topic1", "topic2", "topic3"],
  "news_events": [
    {{"event": "Fed minutes released", "impact": "hawkish tone, rates higher for longer", "relevance": "high|medium|low"}}
  ],
  "tweet_opportunities": [
    {{
      "type": "MARKET_REACTION|RECEIPT|SIGNAL_ALERT|DIP_OPPORTUNITY|THEME_MOMENTUM|ENGAGEMENT",
      "reason": "why this is tweetable right now",
      "tickers": ["$WCC"],
      "urgency": "high|medium|low"
    }}
  ]
}}"""


def build_context_query(positions: List[Dict], signals: Dict, recent_tweets: List[Dict]) -> str:
    """Build the user message for Grok with current portfolio/signals context."""

    # Format open positions
    open_lines = []
    for row in positions:
        ticker = row.get('ticker', '')
        entry = row.get('entry_price', 'N/A')
        open_lines.append(f"${ticker}: entry ${entry}")

    # Extract signals (use actual field names from signals.json)
    buy_signals = signals.get('buy_signals', [])
    consider_signals = signals.get('consider_signals', [])

    pass_tickers = ', '.join(f"${s.get('symbol', '')}" for s in buy_signals)
    consider_tickers = ', '.join(f"${s.get('symbol', '')}" for s in consider_signals)

    # Recent tweet topics (last 5 posted)
    posted = [t for t in recent_tweets if t.get('status') in ('pending', 'posted')]
    recent_topics = [t.get('primary_ticker', '') for t in posted[-5:] if t.get('primary_ticker')]

    return f"""Current portfolio positions:
{chr(10).join(open_lines) if open_lines else 'No open positions'}

Recent scanner signals (PASS): {pass_tickers or 'None'}
Recent scanner signals (CONSIDER): {consider_tickers or 'None'}

Themes we track: {', '.join(TRACKED_THEMES)}

Topics we've tweeted about in last 3 hours (AVOID repeating): {', '.join(recent_topics) or 'None'}

What's happening in markets right now that's relevant to our portfolio and themes?
Focus on actionable observations, not generic commentary."""


# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def parse_json_response(text: str) -> Dict:
    """Parse JSON from Grok response, stripping markdown fences if present."""
    cleaned = text.strip()
    # Strip markdown code fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    return json.loads(cleaned)


def check_stale_context() -> Optional[Dict]:
    """Check if existing context file is usable (< CONTEXT_STALENESS_HOURS old)."""
    if not LIVE_CONTEXT_FILE.exists():
        return None
    try:
        with open(LIVE_CONTEXT_FILE, 'r') as f:
            data = json.load(f)
        gathered_at = data.get('gathered_at', '')
        if not gathered_at:
            return None
        gathered_time = datetime.fromisoformat(gathered_at)
        if gathered_time.tzinfo is None:
            gathered_time = gathered_time.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - gathered_time).total_seconds() / 3600
        if age_hours < CONTEXT_STALENESS_HOURS:
            data['context_stale'] = True
            return data
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def build_fallback_context(positions: List[Dict]) -> Dict:
    """Build a minimal portfolio-only context when API is unavailable."""
    portfolio_movers = []
    for row in positions:
        portfolio_movers.append({
            "ticker": f"${row.get('ticker', '')}",
            "move": "N/A",
            "price": "N/A",
            "context": f"Portfolio position, entry ${row.get('entry_price', 'N/A')}"
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_snapshot": {
            "spy_move": "N/A",
            "qqq_move": "N/A",
            "vix": "N/A",
            "market_mood": "unknown",
            "headline": "Market data unavailable — using portfolio context only"
        },
        "portfolio_movers": portfolio_movers,
        "theme_activity": [],
        "fintwit_trending": [],
        "news_events": [],
        "tweet_opportunities": [],
        "fallback_mode": True,
    }


def gather_live_context() -> ContextResult:
    """
    Query Grok via the Responses API for live market context.

    Returns:
        ContextResult with market data, cost, and error info.
    """
    result = ContextResult()

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        result.error = "XAI_API_KEY not set"
        logger.error(result.error)
        # Try stale context or fallback
        stale = check_stale_context()
        if stale:
            result.context_data = stale
            result.stale = True
            result.error = ""
            return result
        positions = load_open_positions()
        result.context_data = build_fallback_context(positions)
        return result

    # Load data for prompt
    positions = load_open_positions()
    signals = load_signals()
    recent_tweets = load_recent_tweets()

    # Build prompts
    portfolio_tickers = ', '.join(f"${r.get('ticker', '')}" for r in positions)
    system_prompt = CONTEXT_SYSTEM_PROMPT.format(
        themes_list=', '.join(TRACKED_THEMES),
        portfolio_tickers=portfolio_tickers or 'None'
    )
    user_prompt = build_context_query(positions, signals, recent_tweets)

    # Construct Responses API request
    api_url = f"{XAI_BASE_URL}/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            wait = 5 * (3 ** (attempt - 1))  # 5s, 15s
            logger.info(f"Retry {attempt}/{MAX_RETRIES} after {wait}s...")
            time.sleep(wait)

        try:
            payload = {
                "model": MODEL,
                "tools": [{"type": "web_search"}, {"type": "x_search"}],
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            }

            resp = requests.post(
                api_url, headers=headers, json=payload, timeout=API_TIMEOUT,
            )

            if resp.status_code == 429:
                last_error = "Rate limited: HTTP 429"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
                continue

            if resp.status_code != 200:
                last_error = f"API error: HTTP {resp.status_code} — {resp.text[:200]}"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
                continue

            data = resp.json()

            # Extract text from Responses API output
            # Text can be in output[].type=="message" -> content[].type=="output_text"
            # OR output[].type=="text" (varies by model/version)
            raw_text = ""
            for block in data.get("output", []):
                if block.get("type") == "message":
                    for cb in block.get("content", []):
                        if cb.get("type") == "output_text":
                            raw_text += cb.get("text", "")
                elif block.get("type") == "text":
                    raw_text += block.get("text", "")

            if not raw_text:
                last_error = "Empty response from API"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
                continue

            # Parse JSON
            context_data = parse_json_response(raw_text)

            # Estimate cost
            usage = data.get("usage", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0
                result.cost = (input_tokens * 0.20 + output_tokens * 0.50) / 1_000_000

            result.context_data = context_data
            return result

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            logger.warning(f"Attempt {attempt + 1}: {last_error}")
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout: {e}"
            logger.warning(f"Attempt {attempt + 1}: {last_error}")
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {e}"
            logger.warning(f"Attempt {attempt + 1}: {last_error}")
        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {e}"
            logger.warning(f"Attempt {attempt + 1}: {last_error}")
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            logger.error(f"Attempt {attempt + 1}: {last_error}")
            break  # Don't retry unknown errors

    # All retries exhausted — try fallback
    result.error = last_error or "Unknown error"
    logger.error(f"All attempts failed: {result.error}")

    stale = check_stale_context()
    if stale:
        logger.info("Using stale context as fallback")
        result.context_data = stale
        result.stale = True
        result.error = ""
        return result

    logger.info("No stale context available — using portfolio-only fallback")
    result.context_data = build_fallback_context(positions)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════════════

def save_context(context_data: Dict, output_path: Optional[Path] = None) -> Path:
    """Save context data to JSON file with metadata."""
    context_data["gathered_at"] = datetime.now(timezone.utc).isoformat()
    context_data["is_market_hours"] = is_market_open()
    context_data["is_extended_hours"] = is_extended_hours()

    path = output_path or LIVE_CONTEXT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(context_data, f, indent=2)

    return path


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gather live market context via Grok (xAI)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print context to stdout, don't save")
    parser.add_argument("--output", "-o", type=str,
                        help="Custom output file path")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress banner output")
    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "=" * 60)
        print("  LIVE CONTEXT GATHERER - Grok Market Snapshot")
        print("=" * 60)
        now_et = datetime.now(ZoneInfo("America/New_York"))
        print(f"\n  Time: {now_et.strftime('%Y-%m-%d %H:%M ET')}")
        print(f"  Market open: {is_market_open()}")
        print(f"  Extended hours: {is_extended_hours()}")
        print(f"  Querying {MODEL} with live search...")

    result = gather_live_context()

    if result.error:
        print(f"\n  ERROR: {result.error}")
        if not result.context_data:
            return 1

    if not args.quiet:
        stale_tag = " (STALE)" if result.stale else ""
        fallback_tag = " (FALLBACK)" if result.context_data.get('fallback_mode') else ""
        print(f"  Context gathered{stale_tag}{fallback_tag} (cost: ${result.cost:.4f})")

        # Print summary
        snapshot = result.context_data.get('market_snapshot', {})
        print(f"\n  SPY: {snapshot.get('spy_move', 'N/A')} | "
              f"QQQ: {snapshot.get('qqq_move', 'N/A')} | "
              f"VIX: {snapshot.get('vix', 'N/A')}")
        print(f"  Mood: {snapshot.get('market_mood', 'unknown')}")
        print(f"  Headline: {snapshot.get('headline', 'N/A')}")

        movers = result.context_data.get('portfolio_movers', [])
        if movers:
            print(f"\n  Portfolio movers: {len(movers)}")
            for m in movers[:5]:
                print(f"    {m.get('ticker', '?')}: {m.get('move', '?')} — {m.get('context', '')}")

        opps = result.context_data.get('tweet_opportunities', [])
        if opps:
            print(f"\n  Tweet opportunities: {len(opps)}")
            for o in opps[:3]:
                print(f"    [{o.get('urgency', '?')}] {o.get('type', '?')}: {o.get('reason', '')}")

    if args.dry_run:
        if not args.quiet:
            print("\n" + "-" * 60)
            print(json.dumps(result.context_data, indent=2))
            print("-" * 60)
            print("\n  (dry run — not saved)")
    else:
        output_path = Path(args.output) if args.output else None
        saved_path = save_context(result.context_data, output_path)
        if not args.quiet:
            print(f"\n  Saved to: {saved_path}")

    if not args.quiet:
        print("\n" + "=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
