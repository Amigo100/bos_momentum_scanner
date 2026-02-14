#!/usr/bin/env python3
"""
LIVE TWEET GENERATOR - Context-Aware Tweet Generation via Claude Sonnet
=======================================================================

Takes Grok's live market context + portfolio data, decides what type of
tweet to post based on current conditions, generates 3 account variants
via Claude Sonnet, validates through a 10-step pipeline, and writes to
the live content queue.

Usage:
    python -m content.live_tweet_generator                          # Full run
    python -m content.live_tweet_generator --dry-run                # Don't write queue
    python -m content.live_tweet_generator --force-type RECEIPT     # Force tweet type
    python -m content.live_tweet_generator --context PATH           # Custom context file

Environment Variables:
    ANTHROPIC_API_KEY  - Claude API key (required)
"""

import os
import sys
import csv
import json
import re
import random
import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from zoneinfo import ZoneInfo

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

from content.models import (
    Tweet, ValidationResult, VALID_CATEGORIES,
    CHART_REQUIRED_CATEGORIES, INTERNAL_TERM_PATTERNS,
)
from config.banned_terms import (
    ALL_BANNED, CRITICAL_BANNED, check_banned_phrases, check_loser_focus,
)
from content.live_context_gatherer import is_market_open, is_extended_hours


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from config import (
        TRADES_DIR, LIVE_QUEUE_FILE,
        MAX_TWEETS_PER_DAY, MAX_SAME_TICKER_PER_DAY,
        MIN_HOURS_BETWEEN_SAME_TICKER, CONTEXT_STALENESS_HOURS,
        MODEL_LIVE_TWEET, WEEKEND_MAX_TWEETS, WEEKEND_CATEGORIES as _WEEKEND_CATS,
    )
    MODEL = MODEL_LIVE_TWEET
    WEEKEND_CATEGORIES = set(_WEEKEND_CATS)  # Config stores List, local needs Set
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent
    TRADES_DIR = BASE_DIR / "trades"
    LIVE_QUEUE_FILE = TRADES_DIR / "live_content_queue.json"
    MODEL = "claude-sonnet-4-5-20250929"
    MAX_TWEETS_PER_DAY = 12
    WEEKEND_MAX_TWEETS = 4
    MAX_SAME_TICKER_PER_DAY = 3
    MIN_HOURS_BETWEEN_SAME_TICKER = 3
    CONTEXT_STALENESS_HOURS = 4
    WEEKEND_CATEGORIES = {"EDUCATIONAL", "ENGAGEMENT", "NEWSLETTER_CTA", "RECEIPT"}

# Local-only constants (not in config)
PORTFOLIO_FILE = TRADES_DIR / "portfolio.csv"
SIGNALS_FILE = TRADES_DIR / "signals.json"
LIVE_CONTEXT_FILE = TRADES_DIR / "live_context.json"
FAILED_TWEETS_FILE = TRADES_DIR / "failed_tweets.json"
STYLE_GUIDE_PATH = Path(__file__).resolve().parent.parent / "FINTWIT_STYLE_GUIDE.md"

MAX_TOKENS = 1500
MAX_TWEET_CHARS = 280
MAX_REPAIR_ATTEMPTS = 2

# Live system valid categories (subset of VALID_CATEGORIES)
LIVE_VALID_CATEGORIES = {
    "MARKET_REACTION", "RECEIPT", "SIGNAL_ALERT", "DIP_OPPORTUNITY",
    "THEME_MOMENTUM", "ENGAGEMENT", "EDUCATIONAL", "NEWSLETTER_CTA",
}

# Account variant mapping
ACCOUNT_VARIANTS = ["variant_1", "variant_2", "variant_3"]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}


def load_json_list(path: Path) -> list:
    """Load JSON file as list, return empty list if missing or invalid."""
    if not path.exists():
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def load_portfolio(path: Optional[Path] = None) -> List[Dict]:
    """Load open positions from portfolio.csv."""
    p = path or PORTFOLIO_FILE
    if not p.exists():
        return []
    positions = []
    with open(p, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'OPEN':
                row['entry_price'] = float(row.get('entry_price') or 0)
                positions.append(row)
    return positions


def load_recent_tweets() -> List[Dict]:
    """Load recent tweets from live content queue."""
    return load_json_list(LIVE_QUEUE_FILE)


def load_style_guide() -> str:
    """Load style guide from file or use embedded fallback."""
    if STYLE_GUIDE_PATH.exists():
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    return (
        "Write tweets in confident, casual FinTwit voice. <=280 chars. "
        "Always include specific tickers and prices. NFA. "
        "Sound like a real trader, not a corporate account."
    )


def build_allowed_tickers(portfolio: List[Dict], signals: dict) -> Set[str]:
    """Build set of all valid tickers from portfolio + signals."""
    tickers = set()
    for row in portfolio:
        t = row.get('ticker', '').upper()
        if t:
            tickers.add(t)
    for sig in signals.get('buy_signals', []):
        t = sig.get('symbol', '').upper()
        if t:
            tickers.add(t)
    for sig in signals.get('consider_signals', []):
        t = sig.get('symbol', '').upper()
        if t:
            tickers.add(t)
    return tickers


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION LOGIC (PRD Section 14)
# ═══════════════════════════════════════════════════════════════════════════════

def recently_tweeted(ticker: str, recent_tweets: List[Dict], hours: int = 3) -> bool:
    """Check if ticker was tweeted about in last N hours."""
    # Strip $ prefix if present
    ticker = ticker.lstrip('$')
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        pt = (t.get("primary_ticker") or "").lstrip('$')
        if pt == ticker:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def recently_tweeted_theme(theme: str, recent_tweets: List[Dict], hours: int = 6) -> bool:
    """Check if theme was tweeted about in last N hours."""
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    theme_lower = theme.lower()
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        text_lower = t.get("text", "").lower()
        if theme_lower in text_lower:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def recently_tweeted_type(tweet_type: str, recent_tweets: List[Dict], hours: int = 4) -> bool:
    """Check if this tweet type was used in last N hours."""
    cutoff = datetime.now(ZoneInfo("America/New_York")) - timedelta(hours=hours)
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        if t.get("category") == tweet_type:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.tzinfo is None:
                    gen = gen.replace(tzinfo=ZoneInfo("UTC"))
                if gen > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def count_tweets_today(recent_tweets: List[Dict]) -> int:
    """Count tweets generated today."""
    today = datetime.now(ZoneInfo("America/New_York")).date()
    count = 0
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        try:
            gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
            if gen.date() == today:
                count += 1
        except (ValueError, TypeError):
            pass
    return count


def count_ticker_today(ticker: str, recent_tweets: List[Dict]) -> int:
    """Count how many times a ticker was tweeted today."""
    ticker = ticker.lstrip('$')
    today = datetime.now(ZoneInfo("America/New_York")).date()
    count = 0
    for t in recent_tweets:
        if t.get("status") not in ("pending", "posted"):
            continue
        pt = (t.get("primary_ticker") or "").lstrip('$')
        if pt == ticker:
            try:
                gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
                if gen.date() == today:
                    count += 1
            except (ValueError, TypeError):
                pass
    return count


def should_post_newsletter_cta(recent_tweets: List[Dict], target_per_week: int = 2) -> bool:
    """Check if newsletter CTA is due (2x/week)."""
    week_start = datetime.now(ZoneInfo("America/New_York")) - timedelta(days=7)
    ctas = 0
    for t in recent_tweets:
        if t.get("category") != "NEWSLETTER_CTA":
            continue
        try:
            gen = datetime.fromisoformat(t.get("generated_at", "2000-01-01"))
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=ZoneInfo("UTC"))
            if gen > week_start:
                ctas += 1
        except (ValueError, TypeError):
            pass
    return ctas < target_per_week


def get_best_performing_tickers(portfolio: List[Dict], n: int = 1) -> List[str]:
    """Get the top N performing tickers from portfolio by P&L%."""
    scored = []
    for row in portfolio:
        entry = float(row.get('entry_price') or 0)
        highest = float(row.get('highest_close') or 0)
        if entry > 0 and highest > 0:
            pnl = ((highest - entry) / entry) * 100
            scored.append((row['ticker'], pnl))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:n]]


def find_tickers_for_theme(theme: str, portfolio: List[Dict], signals: dict) -> List[str]:
    """Find tickers matching a theme from portfolio and signals."""
    theme_lower = theme.lower()
    tickers = []
    for row in portfolio:
        if theme_lower in (row.get('theme') or '').lower():
            tickers.append(row['ticker'])
    for sig in signals.get('buy_signals', []):
        if theme_lower in (sig.get('theme') or '').lower():
            tickers.append(sig.get('symbol', ''))
    return [t for t in tickers if t][:3]


def decide_tweet_type(
    context: Dict, portfolio: List[Dict], signals: Dict, recent_tweets: List[Dict]
) -> Dict:
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

    # Priority 1: Portfolio movers (>=2% move)
    for mover in movers:
        try:
            move_str = str(mover.get("move", "0")).replace("%", "").replace("+", "")
            pct = float(move_str)
        except (ValueError, TypeError):
            continue
        if abs(pct) < 2.0:
            continue
        ticker = mover.get("ticker", "").lstrip('$')
        if not ticker or recently_tweeted(ticker, recent_tweets, hours=MIN_HOURS_BETWEEN_SAME_TICKER):
            continue
        if pct > 0:
            tweet_type = "RECEIPT"
        elif pct < -3:
            tweet_type = "DIP_OPPORTUNITY"
        else:
            tweet_type = "MARKET_REACTION"
        return {
            "action": "tweet",
            "type": tweet_type,
            "reason": f"${ticker} moving {mover.get('move', '?')}: {mover.get('context', '')}",
            "tickers": [ticker],
            "urgency": "high",
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
                "urgency": "high",
            }

    # Priority 3: Grok-identified opportunities
    urgency_rank = {"high": 0, "medium": 1, "low": 2}
    for opp in sorted(opportunities, key=lambda x: urgency_rank.get(x.get("urgency", "low"), 3)):
        if opp.get("urgency") in ("high", "medium"):
            return {
                "action": "tweet",
                "type": opp.get("type", "MARKET_REACTION"),
                "reason": opp.get("reason", "Grok-identified opportunity"),
                "tickers": opp.get("tickers", []),
                "urgency": opp.get("urgency", "medium"),
            }

    # Priority 4: Market commentary (volatile/bearish mood)
    mood = market.get("market_mood", "quiet")
    if mood in ("volatile", "bearish") and not recently_tweeted_type("MARKET_REACTION", recent_tweets, hours=4):
        return {
            "action": "tweet",
            "type": "MARKET_REACTION",
            "reason": f"Market mood: {mood} — {market.get('headline', '')}",
            "tickers": [m.get("ticker", "").lstrip('$') for m in movers[:2] if m.get("ticker")],
            "urgency": "medium",
        }

    # Priority 5: Newsletter CTA (2x/week)
    if should_post_newsletter_cta(recent_tweets):
        return {
            "action": "tweet",
            "type": "NEWSLETTER_CTA",
            "reason": "Scheduled newsletter CTA",
            "tickers": get_best_performing_tickers(portfolio, n=1),
            "urgency": "low",
        }

    # Priority 6: Filler (quiet days)
    if tweets_today < 4 and not is_weekend:
        return {
            "action": "tweet",
            "type": random.choice(["EDUCATIONAL", "ENGAGEMENT"]),
            "reason": "Quiet market — filler content with live context",
            "tickers": get_best_performing_tickers(portfolio, n=1),
            "urgency": "low",
        }

    return {"action": "skip", "reason": "No tweetable events and daily minimum met"}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS (PRD Section 6.3-6.4)
# ═══════════════════════════════════════════════════════════════════════════════

def build_system_prompt(style_guide: str) -> str:
    """Build the Sonnet system prompt for tweet generation."""
    banned_sample = ", ".join(f'"{t}"' for t in CRITICAL_BANNED[:40])

    return f"""You are the voice of Sterling Signals, a momentum trading newsletter on FinTwit.

STYLE RULES (non-negotiable):
{style_guide}

YOUR TASK:
Generate exactly 3 tweet variants for the same moment. Each variant must:
- Sound like a different human wrote it (not just rearranged words)
- Be <=280 characters
- Contain at least one specific element (ticker, price, %, or named theme)
- Match the tone of these reference accounts: confident but not arrogant, specific not vague, casual not corporate

FORMATTING RULES:
- Return ONLY valid JSON — no markdown, no commentary
- Format: {{"tweets": [{{"text": "...", "category": "...", "primary_ticker": "...", "chart_recommended": true/false, "account": "variant_1|variant_2|variant_3"}}, ...]}}
- Categories: MARKET_REACTION, RECEIPT, SIGNAL_ALERT, DIP_OPPORTUNITY, THEME_MOMENTUM, ENGAGEMENT, EDUCATIONAL, NEWSLETTER_CTA
- chart_recommended: true if tweet references a specific ticker with price action

ABSOLUTE BANS (NEVER use these terms):
{banned_sample}

ADDITIONAL RULES:
- Never fabricate tickers, prices, or percentages not in the provided data
- Never use: "our scanner", "filtered X stocks", "save this post", "bookmark this"
- Never use hashtags
- Never exceed 280 characters
- Never mention losses or negative P&L
- Never use UK references (BST, GMT, GBP, ISA)
- Never reference being an AI, bot, or automated system
- Keep "NFA" to <=1 of the 3 variants
- Output ONLY the JSON — no explanations"""


def format_portfolio_for_prompt(portfolio: List[Dict]) -> str:
    """Format portfolio data for the user prompt."""
    lines = []
    for row in portfolio:
        ticker = row.get('ticker', '')
        entry = float(row.get('entry_price') or 0)
        highest = float(row.get('highest_close') or 0)
        theme = row.get('theme', '')
        if entry > 0 and highest > 0:
            pnl = ((highest - entry) / entry) * 100
            lines.append(f"${ticker}: entry ${entry:.2f}, high ${highest:.2f} ({pnl:+.1f}%) — {theme}")
        else:
            lines.append(f"${ticker}: entry ${entry:.2f} — {theme}")
    return "\n".join(lines) if lines else "No open positions"


def build_user_prompt(decision: Dict, context: Dict, portfolio: List[Dict]) -> str:
    """Build the user prompt with live market context."""
    market = context.get("market_snapshot", {})
    movers = context.get("portfolio_movers", [])
    themes = context.get("theme_activity", [])
    trending = context.get("fintwit_trending", [])

    movers_text = json.dumps(movers, indent=2) if movers else "No significant moves"
    themes_text = json.dumps(themes, indent=2) if themes else "All themes quiet"
    trending_text = ", ".join(trending) if trending else "Nothing specific"

    return f"""CURRENT MARKET STATE:
- SPY: {market.get('spy_move', 'N/A')} | QQQ: {market.get('qqq_move', 'N/A')} | VIX: {market.get('vix', 'N/A')}
- Mood: {market.get('market_mood', 'unknown')}
- Headline: {market.get('headline', '')}

YOUR PORTFOLIO MOVERS TODAY:
{movers_text}

THEME ACTIVITY:
{themes_text}

FINTWIT IS DISCUSSING:
{trending_text}

TWEET TYPE REQUESTED: {decision.get('type', 'ENGAGEMENT')}
REASON: {decision.get('reason', '')}
FOCUS TICKER(S): {', '.join(f'${t}' for t in decision.get('tickers', []))}

PORTFOLIO CONTEXT (for accuracy — use ONLY these real numbers):
{format_portfolio_for_prompt(portfolio)}

Generate 3 variants now."""


# ═══════════════════════════════════════════════════════════════════════════════
# SONNET API CALL
# ═══════════════════════════════════════════════════════════════════════════════

def parse_json_response(text: str) -> Dict:
    """Parse JSON from Sonnet response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    return json.loads(cleaned)


def call_sonnet(
    decision: Dict, context: Dict, portfolio: List[Dict],
    style_guide: str, client: anthropic.Anthropic,
) -> List[Dict]:
    """Generate 3 tweet variants in a single Sonnet call."""
    system_prompt = build_system_prompt(style_guide)
    user_prompt = build_user_prompt(decision, context, portfolio)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text
    raw_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            raw_text += block.text

    # Parse JSON
    data = parse_json_response(raw_text)
    tweets = data.get("tweets", [])

    # Calculate cost
    usage = response.usage
    input_tokens = getattr(usage, 'input_tokens', 0) or 0
    output_tokens = getattr(usage, 'output_tokens', 0) or 0
    cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

    # Attach cost to each variant
    for t in tweets:
        t['_cost'] = cost / max(len(tweets), 1)

    return tweets


def repair_tweet(
    tweet_dict: Dict, failures: List[str], decision: Dict,
    context: Dict, portfolio: List[Dict],
    style_guide: str, client: anthropic.Anthropic,
) -> Optional[Dict]:
    """Attempt to repair a failed tweet by re-calling Sonnet with error feedback."""
    system_prompt = build_system_prompt(style_guide)
    failures_text = "\n".join(f"- {f}" for f in failures)

    user_prompt = f"""The following tweet FAILED validation:

"{tweet_dict.get('text', '')}"

Category: {tweet_dict.get('category', '')}
Failures:
{failures_text}

Rewrite this tweet to fix ALL the above issues.
Keep the same category ({tweet_dict.get('category', '')}) and general topic.
Use only tickers and prices from the portfolio data below.
Must be under 280 characters. Output ONLY the tweet text — no labels, no quotes, no JSON.

PORTFOLIO CONTEXT:
{format_portfolio_for_prompt(portfolio)}"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                text += block.text
        text = text.strip()

        # Strip wrapping quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        tickers = re.findall(r'\$([A-Z]{2,5})', text)
        primary = tickers[0] if tickers else tweet_dict.get('primary_ticker', '')

        return {
            "text": text,
            "category": tweet_dict.get("category", ""),
            "primary_ticker": primary,
            "chart_recommended": tweet_dict.get("chart_recommended", False),
            "account": tweet_dict.get("account", "variant_1"),
            "_repaired": True,
            "_cost": tweet_dict.get("_cost", 0),
        }
    except Exception as e:
        logger.error("Repair failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE (10 steps — PRD Section 15)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_tweet(
    tweet_dict: Dict,
    allowed_tickers: Set[str],
    all_variants: Optional[List[Dict]] = None,
    context: Optional[Dict] = None,
    recent_tweets: Optional[List[Dict]] = None,
) -> ValidationResult:
    """
    Run the 10-step validation pipeline on a tweet.

    Args:
        tweet_dict: Tweet data with 'text', 'category', 'chart_recommended', etc.
        allowed_tickers: Set of valid ticker symbols from portfolio + signals
        all_variants: Other variants in this batch (for step 8 cross-dedup)
        context: Live context data (for step 9 staleness check)
        recent_tweets: Recent tweet queue (for step 10 daily repetition)

    Returns:
        ValidationResult with passed flag and failure list.
    """
    failures = []
    text = tweet_dict.get("text", "")
    category = tweet_dict.get("category", "")
    text_lower = text.lower()

    # Step 1: Category validation
    if category not in LIVE_VALID_CATEGORIES:
        failures.append(f"step1_category: '{category}' not in LIVE_VALID_CATEGORIES")

    # Step 2: Ticker fabrication check
    found_tickers = re.findall(r'\$([A-Z]{2,5})', text)
    if allowed_tickers:
        for ticker in found_tickers:
            if ticker not in allowed_tickers:
                failures.append(f"step2_fabrication: ${ticker} not in source data")

    # Step 3: Banned phrase check (word-boundary for short terms)
    for term in ALL_BANNED:
        term_lower = term.lower()
        if len(term) <= 4 and term.isascii():
            if re.search(r'\b' + re.escape(term_lower) + r'\b', text_lower):
                failures.append(f"step3_banned: '{term}'")
                break  # One banned term is enough to fail
        else:
            if term_lower in text_lower:
                failures.append(f"step3_banned: '{term}'")
                break

    # Step 4: Winners-only check
    negative_pcts = re.findall(r'-\d+\.?\d*%', text)
    if negative_pcts:
        failures.append(f"step4_winners_only: negative percentage(s) {negative_pcts}")
    if check_loser_focus(text):
        failures.append("step4_winners_only: loser-focused language detected")

    # Step 5: Internal terminology check
    for pattern in INTERNAL_TERM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            failures.append(f"step5_internal: '{match.group()}' is internal terminology")
            break

    # Step 6: Character count
    if len(text) > MAX_TWEET_CHARS:
        failures.append(f"step6_chars: {len(text)} > {MAX_TWEET_CHARS}")

    # Step 7: Chart flag — recommend chart for any tweet with a specific ticker
    # Always chart: SIGNAL_ALERT, RECEIPT
    # Chart when ticker present: MARKET_REACTION, DIP_OPPORTUNITY, THEME_MOMENTUM
    always_chart = {"SIGNAL_ALERT", "RECEIPT"}
    chart_if_ticker = {"MARKET_REACTION", "DIP_OPPORTUNITY", "THEME_MOMENTUM"}
    has_ticker = bool(tweet_dict.get("primary_ticker"))
    expected_chart = category in always_chart or (category in chart_if_ticker and has_ticker)
    if tweet_dict.get("chart_recommended") != expected_chart:
        tweet_dict["chart_recommended"] = expected_chart
        # Auto-fixed, not a failure

    # Step 8: Cross-account dedup (if other variants provided)
    if all_variants:
        for other in all_variants:
            if other.get("account") == tweet_dict.get("account"):
                continue
            similarity = SequenceMatcher(
                None, text_lower, other.get("text", "").lower()
            ).ratio()
            if similarity > 0.60:
                failures.append(
                    f"step8_dedup: {similarity:.0%} similar to {other.get('account', '?')}"
                )
                break

    # Step 9: Context staleness check
    if context and category == "MARKET_REACTION":
        gathered_at = context.get("gathered_at", "")
        if gathered_at:
            try:
                gathered_time = datetime.fromisoformat(gathered_at)
                if gathered_time.tzinfo is None:
                    gathered_time = gathered_time.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - gathered_time).total_seconds() / 3600
                if age_hours > CONTEXT_STALENESS_HOURS:
                    failures.append(
                        f"step9_staleness: context {age_hours:.1f}h old, MARKET_REACTION blocked"
                    )
            except (ValueError, TypeError):
                pass
        if context.get("fallback_mode") or context.get("context_stale"):
            failures.append("step9_staleness: context is stale/fallback, MARKET_REACTION blocked")

    # Step 10: Daily ticker repetition
    if recent_tweets and found_tickers:
        primary = found_tickers[0] if found_tickers else ""
        if primary:
            ticker_count = count_ticker_today(primary, recent_tweets)
            if ticker_count >= MAX_SAME_TICKER_PER_DAY:
                failures.append(
                    f"step10_repetition: ${primary} already tweeted {ticker_count}x today (max {MAX_SAME_TICKER_PER_DAY})"
                )

    return ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE WRITING
# ═══════════════════════════════════════════════════════════════════════════════

def _prune_queue(queue: List[Dict], max_age_days: int = 7) -> List[Dict]:
    """Remove old posted/skipped/failed items. Keep all pending items.

    Prevents unbounded queue growth that causes git bloat and slow dedup.

    Args:
        queue: Full queue list
        max_age_days: Remove non-pending items older than this

    Returns:
        Pruned queue list
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    pruned = []
    removed = 0
    for item in queue:
        if item.get("status") == "pending":
            pruned.append(item)
            continue
        generated_at = item.get("generated_at", "")
        try:
            gen_time = datetime.fromisoformat(generated_at)
            if gen_time.tzinfo is None:
                gen_time = gen_time.replace(tzinfo=timezone.utc)
            if gen_time >= cutoff:
                pruned.append(item)
                continue
        except (ValueError, TypeError):
            pruned.append(item)  # Keep items with bad dates
            continue
        removed += 1
    if removed > 0:
        print(f"  🧹 Pruned {removed} items older than {max_age_days} days")
    return pruned


def write_to_live_queue(
    validated_tweets: List[Dict], decision: Dict, context: Dict, cost: float,
) -> Path:
    """Write validated tweets to the live content queue."""
    # Load existing queue and prune old items
    queue = load_json_list(LIVE_QUEUE_FILE)
    queue = _prune_queue(queue)

    now_utc = datetime.now(timezone.utc)
    now_et = datetime.now(ZoneInfo("America/New_York"))
    timestamp_str = now_et.strftime("%Y%m%d_%H%M%S")

    market = context.get("market_snapshot", {})

    for i, tweet in enumerate(validated_tweets):
        account = tweet.get("account", ACCOUNT_VARIANTS[i] if i < 3 else "variant_1")
        primary_ticker = tweet.get("primary_ticker", "")
        if not primary_ticker:
            tickers = re.findall(r'\$([A-Z]{2,5})', tweet.get("text", ""))
            primary_ticker = tickers[0] if tickers else ""

        entry = {
            "id": f"live_{timestamp_str}_v{i + 1}",
            "text": tweet["text"],
            "category": tweet.get("category", decision.get("type", "")),
            "primary_ticker": primary_ticker,
            "account": account,
            "chart_recommended": tweet.get("chart_recommended", False),
            "chart_path": None,
            "scheduled_time": now_et.isoformat(),
            "status": "pending",
            "context_snapshot": {
                "spy_at_generation": market.get("spy_move", "N/A"),
                "market_mood": market.get("market_mood", "unknown"),
                "context_stale": context.get("context_stale", False),
            },
            "generated_at": now_utc.isoformat(),
            "cost_usd": round(tweet.get("_cost", cost / max(len(validated_tweets), 1)), 6),
        }
        queue.append(entry)

    # Write atomically
    LIVE_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = LIVE_QUEUE_FILE.with_suffix(".tmp")
    with open(tmp_path, 'w') as f:
        json.dump(queue, f, indent=2)
    tmp_path.replace(LIVE_QUEUE_FILE)

    return LIVE_QUEUE_FILE


def log_failed_tweet(tweet_dict: Dict, failures: List[str]):
    """Log a failed tweet for debugging."""
    failed = load_json_list(FAILED_TWEETS_FILE)
    failed.append({
        "text": tweet_dict.get("text", ""),
        "category": tweet_dict.get("category", ""),
        "failures": failures,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last 100 entries
    failed = failed[-100:]
    with open(FAILED_TWEETS_FILE, 'w') as f:
        json.dump(failed, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_live_tweet(
    context_path: Optional[Path] = None,
    portfolio_path: Optional[Path] = None,
    signals_path: Optional[Path] = None,
    force_type: Optional[str] = None,
    dry_run: bool = False,
) -> Dict:
    """
    Main entry point. Decide, generate, validate, and queue live tweets.

    Returns:
        Status dict: {"status": "generated"|"skipped"|"failed", ...}
    """
    # 1. Load inputs
    context = load_json(context_path or LIVE_CONTEXT_FILE)
    portfolio = load_portfolio(portfolio_path)
    signals = load_json(signals_path or SIGNALS_FILE)
    style_guide = load_style_guide()
    recent_tweets = load_recent_tweets()
    allowed_tickers = build_allowed_tickers(portfolio, signals)

    if not context:
        logger.warning("No context data available")
        return {"status": "failed", "reason": "no_context"}

    # 2. Decide what to tweet
    if force_type:
        decision = {
            "action": "tweet",
            "type": force_type,
            "reason": f"Forced type: {force_type}",
            "tickers": get_best_performing_tickers(portfolio, n=2),
            "urgency": "medium",
        }
    else:
        decision = decide_tweet_type(context, portfolio, signals, recent_tweets)

    # 3. If nothing worth tweeting, skip
    if decision["action"] == "skip":
        logger.info("Skipping: %s", decision["reason"])
        return {"status": "skipped", "reason": decision["reason"]}

    # 4. Check Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "failed", "reason": "ANTHROPIC_API_KEY not set"}
    client = anthropic.Anthropic(api_key=api_key)

    # 5. Generate tweets via Sonnet
    try:
        raw_tweets = call_sonnet(decision, context, portfolio, style_guide, client)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Sonnet response: %s", e)
        return {"status": "failed", "reason": f"json_parse_error: {e}"}
    except anthropic.APIError as e:
        logger.error("Sonnet API error: %s", e)
        return {"status": "failed", "reason": f"api_error: {e}"}
    except Exception as e:
        logger.error("Unexpected error in Sonnet call: %s", e)
        return {"status": "failed", "reason": f"error: {e}"}

    if not raw_tweets:
        return {"status": "failed", "reason": "no_tweets_generated"}

    # 6. Validate all variants
    validated = []
    total_cost = sum(t.get("_cost", 0) for t in raw_tweets)

    for tweet_dict in raw_tweets:
        result = validate_tweet(
            tweet_dict,
            allowed_tickers=allowed_tickers,
            all_variants=validated,  # Already-validated for cross-dedup
            context=context,
            recent_tweets=recent_tweets,
        )

        if result.passed:
            validated.append(tweet_dict)
            continue

        # Attempt repair
        for attempt in range(MAX_REPAIR_ATTEMPTS):
            logger.info(
                "Repairing %s tweet (attempt %d): %s",
                tweet_dict.get("account", "?"), attempt + 1, result.failures,
            )
            repaired = repair_tweet(
                tweet_dict, result.failures, decision,
                context, portfolio, style_guide, client,
            )
            if repaired is None:
                break

            result = validate_tweet(
                repaired,
                allowed_tickers=allowed_tickers,
                all_variants=validated,
                context=context,
                recent_tweets=recent_tweets,
            )
            if result.passed:
                validated.append(repaired)
                break
            tweet_dict = repaired  # Try repairing the repair
        else:
            # All repair attempts exhausted
            log_failed_tweet(tweet_dict, result.failures)
            logger.warning(
                "Dropped %s tweet after %d repair attempts: %s",
                tweet_dict.get("account", "?"), MAX_REPAIR_ATTEMPTS, result.failures,
            )

    # 7. Write to queue
    if not validated:
        logger.error("All variants failed validation")
        return {"status": "failed", "reason": "all_variants_failed"}

    if dry_run:
        return {
            "status": "dry_run",
            "count": len(validated),
            "tweets": validated,
            "decision": decision,
            "cost": total_cost,
        }

    queue_path = write_to_live_queue(validated, decision, context, total_cost)
    return {
        "status": "generated",
        "count": len(validated),
        "queue_path": str(queue_path),
        "decision_type": decision.get("type"),
        "cost": total_cost,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate live tweets via Claude Sonnet"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate but don't write to queue")
    parser.add_argument("--force-type", type=str, default=None,
                        help="Force tweet type (RECEIPT, MARKET_REACTION, etc.)")
    parser.add_argument("--context", type=str, default=None,
                        help="Custom context file path")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress banner output")
    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "=" * 60)
        print("  LIVE TWEET GENERATOR - Claude Sonnet")
        print("=" * 60)
        now_et = datetime.now(ZoneInfo("America/New_York"))
        print(f"\n  Time: {now_et.strftime('%Y-%m-%d %H:%M ET')}")
        print(f"  Market open: {is_market_open()}")
        if args.force_type:
            print(f"  Forced type: {args.force_type}")
        if args.dry_run:
            print("  Mode: DRY RUN")

    context_path = Path(args.context) if args.context else None

    result = generate_live_tweet(
        context_path=context_path,
        force_type=args.force_type,
        dry_run=args.dry_run,
    )

    if not args.quiet:
        status = result.get("status", "unknown")
        print(f"\n  Status: {status}")

        if status == "skipped":
            print(f"  Reason: {result.get('reason', '')}")

        elif status == "failed":
            print(f"  Reason: {result.get('reason', '')}")

        elif status in ("generated", "dry_run"):
            print(f"  Tweets: {result.get('count', 0)} variants")
            print(f"  Type: {result.get('decision_type', result.get('decision', {}).get('type', ''))}")
            print(f"  Cost: ${result.get('cost', 0):.4f}")

            if status == "dry_run" and result.get("tweets"):
                print("\n" + "-" * 60)
                for t in result["tweets"]:
                    print(f"\n  [{t.get('account', '?')}] {t.get('category', '?')}")
                    print(f"  {t.get('text', '')}")
                    print(f"  Ticker: {t.get('primary_ticker', 'N/A')} | "
                          f"Chart: {t.get('chart_recommended', False)}")
                print("\n" + "-" * 60)
                print("  (dry run — not queued)")

        if result.get("queue_path"):
            print(f"  Queue: {result['queue_path']}")

        print("\n" + "=" * 60 + "\n")

    return 0 if result.get("status") != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
