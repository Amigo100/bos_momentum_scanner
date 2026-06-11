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
        PORTFOLIO_FILE, SIGNALS_FILE, LIVE_QUEUE_FILE, LIVE_CONTEXT_FILE,
        CONTEXT_STALENESS_HOURS, WEEKEND_CONTEXT_STALENESS_HOURS,
        MODEL_CONTEXT, XAI_BASE_URL,
    )
    MODEL = MODEL_CONTEXT
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    _TWITTER_OUTPUT = BASE_DIR / "twitter" / "output"
    _SCANNER_OUTPUT = BASE_DIR / "scanner" / "output"
    _PORTFOLIO_OUTPUT = BASE_DIR / "portfolio" / "output"
    PORTFOLIO_FILE = _PORTFOLIO_OUTPUT / "portfolio.csv"
    SIGNALS_FILE = _SCANNER_OUTPUT / "signals.json"
    LIVE_QUEUE_FILE = _TWITTER_OUTPUT / "live_content_queue.json"
    LIVE_CONTEXT_FILE = _TWITTER_OUTPUT / "live_context.json"
    MODEL = "grok-4-fast-non-reasoning"
    XAI_BASE_URL = "https://api.x.ai/v1"
    CONTEXT_STALENESS_HOURS = 4
    WEEKEND_CONTEXT_STALENESS_HOURS = 24

# Base themes that are always tracked (structural macro themes, not scanner-specific)
BASE_THEMES = ["copper", "infrastructure", "defense", "AI", "semiconductors", "nuclear"]


def load_tracked_themes() -> List[str]:
    """Load themes from scanner output + base themes.

    Scanner themes are refreshed weekly (Friday scan). Between scans,
    the theme list is stable. Base themes are always included.
    """
    scanner_themes = []
    if SIGNALS_FILE.exists():
        try:
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
            for theme in signals.get("themes", []):
                name = theme.get("name", "")
                if name:
                    scanner_themes.append(name.lower())
        except (json.JSONDecodeError, KeyError):
            pass

    # Merge: scanner themes first (priority), then base themes
    all_themes = list(dict.fromkeys(scanner_themes + BASE_THEMES))
    return all_themes[:15]  # Cap to keep Grok prompt focused
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


def _build_portfolio_context() -> tuple:
    """Load portfolio positions, preferring snapshot over CSV.

    Returns (positions_list, formatted_context_string).
    positions_list is list of dicts with at least 'ticker' and 'entry_price' keys.
    """
    # Try snapshot first (richer data: current_price, pnl_pct, stop_distance)
    snapshot_path = Path(__file__).resolve().parent.parent / "portfolio" / "output" / "portfolio_snapshot.json"
    if snapshot_path.exists():
        try:
            snapshot = json.loads(snapshot_path.read_text())
            positions = snapshot.get("open_positions", [])

            lines = []
            for pos in positions:
                ticker = pos.get("ticker", "")
                entry = pos.get("entry_price", 0)
                current = pos.get("current_price", 0)
                pnl = pos.get("pnl_pct", 0)
                lines.append(
                    f"${ticker}: entry ${entry:.2f}, current ${current:.2f} ({pnl:+.1f}%)"
                )

            # Add summary stats if available
            eq = snapshot.get("equity", {})
            if eq:
                lines.append(f"\nPortfolio alpha vs S&P: {eq.get('alpha_pct', 0):+.1f}%")
                win_rate = snapshot.get("summary", {}).get("win_rate", 0)
                if win_rate:
                    lines.append(f"Win rate: {win_rate:.0f}%")

            # Convert to list-of-dicts format for compatibility with existing code
            compat_positions = [
                {"ticker": p.get("ticker", ""), "entry_price": str(p.get("entry_price", ""))}
                for p in positions
            ]
            context_str = "\n".join(lines) if lines else "No open positions"
            return compat_positions, context_str
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    # Fallback: CSV loading (existing behavior)
    positions = load_open_positions()
    lines = [f"${r.get('ticker', '')}: entry ${r.get('entry_price', 'N/A')}" for r in positions]
    return positions, ("\n".join(lines) if lines else "No open positions")


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
6. For each ACTIVE or BREAKING theme, find 5-8 publicly traded companies relevant to this theme. Include their ticker symbol and approximate current price. These do NOT need to be in our portfolio — they are market context tickers for theme analysis.
7. Check if any FinTwit trending topics overlap with our tracked themes. If so, note which theme matches and whether we have positions in it.

Return ONLY valid JSON in this exact format — no markdown, no commentary:
{{
  "timestamp": "ISO-8601",
  "market_snapshot": {{
    "spy_move": "+0.3%",
    "qqq_move": "-0.1%",
    "iwm_move": "+0.8%",
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
  "theme_tickers": [
    {{"theme": "copper", "tickers": [
      {{"symbol": "$FCX", "price": "$60.41", "context": "Largest US copper miner"}},
      {{"symbol": "$SCCO", "price": "$184.30", "context": "Southern Copper"}}
    ]}}
  ],
  "fintwit_trending": ["topic1", "topic2", "topic3"],
  "fintwit_theme_overlaps": [
    {{"trending_topic": "copper breakout", "matching_theme": "copper", "our_positions": ["$WCC"], "context": "FinTwit buzzing about copper futures hitting 52-week high"}}
  ],
  "news_events": [
    {{"event": "Fed minutes released", "impact": "hawkish tone, rates higher for longer", "relevance": "high|medium|low"}}
  ]
}}"""


def _get_substack_topic() -> str:
    """Get today's Substack post topic from daily_context.md if available."""
    context_path = Path(__file__).resolve().parent.parent / "substack" / "output" / "current" / "daily_context.md"
    if not context_path.exists():
        return ""
    try:
        content = context_path.read_text()
        topic_match = re.search(r"\*\*Topic:\*\*\s*(.+)", content)
        category_match = re.search(r"\*\*Category:\*\*\s*(.+)", content)
        if topic_match:
            topic = topic_match.group(1).strip()
            category = category_match.group(1).strip() if category_match else ""
            label = f"{category} — {topic}" if category else topic
            return (
                f"\nToday's Substack post: \"{label}\"\n"
                "Look for market context that connects to this topic for potential teaser tweets."
            )
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def build_context_query(
    positions: List[Dict],
    signals: Dict,
    recent_tweets: List[Dict],
    portfolio_context: str = "",
) -> str:
    """Build the user message for Grok with current portfolio/signals context.

    Args:
        positions: List of position dicts (used if portfolio_context not provided).
        signals: Scanner signals dict.
        recent_tweets: Recent tweets for dedup.
        portfolio_context: Pre-formatted portfolio string from _build_portfolio_context().
    """
    # Portfolio section — use pre-formatted context if available, else build from positions
    if not portfolio_context:
        open_lines = []
        for row in positions:
            ticker = row.get('ticker', '')
            entry = row.get('entry_price', 'N/A')
            open_lines.append(f"${ticker}: entry ${entry}")
        portfolio_context = chr(10).join(open_lines) if open_lines else 'No open positions'

    # Extract signals (use actual field names from signals.json)
    buy_signals = signals.get('buy_signals', [])
    consider_signals = signals.get('consider_signals', [])

    pass_tickers = ', '.join(f"${s.get('symbol', '')}" for s in buy_signals)
    consider_tickers = ', '.join(f"${s.get('symbol', '')}" for s in consider_signals)

    # Recent tweet topics (last 5 posted)
    posted = [t for t in recent_tweets if t.get('status') in ('pending', 'posted')]
    recent_topics = [t.get('primary_ticker', '') for t in posted[-5:] if t.get('primary_ticker')]

    substack_topic = _get_substack_topic()

    return f"""Current portfolio positions:
{portfolio_context}

Recent scanner signals (PASS): {pass_tickers or 'None'}
Recent scanner signals (CONSIDER): {consider_tickers or 'None'}

Themes we track: {', '.join(load_tracked_themes())}

Topics we've tweeted about in last 3 hours (AVOID repeating): {', '.join(recent_topics) or 'None'}
{substack_topic}
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
    """Check if existing context file is usable (relaxed threshold on weekends)."""
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
        now_et = datetime.now(ZoneInfo("America/New_York"))
        staleness_limit = WEEKEND_CONTEXT_STALENESS_HOURS if now_et.weekday() >= 5 else CONTEXT_STALENESS_HOURS
        if age_hours < staleness_limit:
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
            "iwm_move": "N/A",
            "vix": "N/A",
            "market_mood": "unknown",
            "headline": "Market data unavailable — using portfolio context only"
        },
        "portfolio_movers": portfolio_movers,
        "theme_activity": [],
        "theme_tickers": [],
        "fintwit_trending": [],
        "fintwit_theme_overlaps": [],
        "news_events": [],
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
    positions, portfolio_context = _build_portfolio_context()
    signals = load_signals()
    recent_tweets = load_recent_tweets()

    # Build prompts
    portfolio_tickers = ', '.join(f"${r.get('ticker', '')}" for r in positions)
    themes = load_tracked_themes()
    system_prompt = CONTEXT_SYSTEM_PROMPT.format(
        themes_list=', '.join(themes),
        portfolio_tickers=portfolio_tickers or 'None'
    )
    user_prompt = build_context_query(positions, signals, recent_tweets, portfolio_context)

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

            # Normalize new fields with safe defaults
            context_data.setdefault("theme_tickers", [])
            context_data.setdefault("fintwit_theme_overlaps", [])
            context_data.get("market_snapshot", {}).setdefault("iwm_move", "N/A")

            # Remove legacy field if Grok still returns it
            context_data.pop("tweet_opportunities", None)

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
              f"IWM: {snapshot.get('iwm_move', 'N/A')} | "
              f"VIX: {snapshot.get('vix', 'N/A')}")
        print(f"  Mood: {snapshot.get('market_mood', 'unknown')}")
        print(f"  Headline: {snapshot.get('headline', 'N/A')}")

        movers = result.context_data.get('portfolio_movers', [])
        if movers:
            print(f"\n  Portfolio movers: {len(movers)}")
            for m in movers[:5]:
                print(f"    {m.get('ticker', '?')}: {m.get('move', '?')} — {m.get('context', '')}")

        theme_tickers = result.context_data.get('theme_tickers', [])
        if theme_tickers:
            total = sum(len(td.get('tickers', [])) for td in theme_tickers)
            print(f"\n  Theme tickers: {total} across {len(theme_tickers)} themes")

        overlaps = result.context_data.get('fintwit_theme_overlaps', [])
        if overlaps:
            print(f"\n  FinTwit theme overlaps: {len(overlaps)}")
            for o in overlaps[:3]:
                print(f"    {o.get('trending_topic', '?')} → {o.get('matching_theme', '?')}")

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
