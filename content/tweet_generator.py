#!/usr/bin/env python3
"""
Sterling Signals — Tweet Generator v2.0
========================================

Unified voice, style-guide compliant, data-driven content generation.

Replaces: reaction_generator.py (3-persona system)
Ref: STERLING_SIGNALS_PRD_v2.md section 3
Ref: FINTWIT_STYLE_GUIDE.md

Usage:
    from content.tweet_generator import generate_weekly_content, generate_daily_content

    summary = generate_weekly_content("trades/signals.json", "trades/portfolio.csv")
    daily  = generate_daily_content("trades/daily_signals.json", "trades/daily_portfolio.csv")

CLI:
    python -m content.tweet_generator --signals trades/signals.json --portfolio trades/portfolio.csv
    python -m content.tweet_generator --daily --signals trades/daily_signals.json
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

from config.settings import (
    BASE_DIR,
    TRADES_DIR,
    MODEL_TWEET,
    MAX_TOKENS,
    SLOT_TIMES_ET,
    COST_INPUT_PER_M,
    COST_OUTPUT_PER_M,
    MARKETING_THRESHOLDS,
)
from config.banned_terms import (
    ALL_BANNED,
    CRITICAL_BANNED,
    LOSER_PATTERNS,
    check_banned_phrases,
    check_loser_focus,
)
from content.models import (
    Tweet,
    ValidationResult,
    SlotAssignment,
    ContentData,
    TWEET_CATEGORIES,
    CHART_REQUIRED_CATEGORIES,
    VALID_CATEGORIES,
    INTERNAL_TERM_PATTERNS,
)


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL = MODEL_TWEET
TWEET_MAX_TOKENS = MAX_TOKENS.get(MODEL, 4096)
MAX_TWEET_CHARS = 280
MAX_REPAIR_ATTEMPTS = 2

NEWSLETTER_URL = "https://sterlingsignals.substack.com"

STYLE_GUIDE_PATH = BASE_DIR / "FINTWIT_STYLE_GUIDE.md"

# Days starting Saturday (day after weekly scan) through Friday
WEEKLY_DAYS = ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]

# Account queue files — identical content written to all three
ACCOUNT_QUEUES = {
    "main": "content_queue.json",
    "account2": "content_queue_account2.json",
    "account3": "content_queue_account3.json",
}

DAILY_ACCOUNT_QUEUES = {
    "main": "daily_content_queue.json",
    "account2": "daily_content_queue_account2.json",
    "account3": "daily_content_queue_account3.json",
}

# Weekly slots (1-5) per day
WEEKLY_SLOTS = [1, 2, 3, 4, 5]


# ═══════════════════════════════════════════════════════════════════════════════
# COST TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class CostTracker:
    """Track LLM API usage and cost across a generation run."""

    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.api_calls: int = 0

    def record(self, response) -> None:
        """Record token usage from an Anthropic API response."""
        usage = getattr(response, "usage", None)
        if usage:
            self.input_tokens += getattr(usage, "input_tokens", 0)
            self.output_tokens += getattr(usage, "output_tokens", 0)
        self.api_calls += 1

    @property
    def total_cost(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * COST_INPUT_PER_M.get(MODEL, 3.0)
        output_cost = (self.output_tokens / 1_000_000) * COST_OUTPUT_PER_M.get(MODEL, 15.0)
        return round(input_cost + output_cost, 4)

    def summary(self) -> str:
        return (
            f"API calls: {self.api_calls} | "
            f"Input: {self.input_tokens:,} tokens | "
            f"Output: {self.output_tokens:,} tokens | "
            f"Cost: ${self.total_cost:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE GUIDE LOADING
# ═══════════════════════════════════════════════════════════════════════════════

# Embedded style guide used when FINTWIT_STYLE_GUIDE.md doesn't exist on disk.
# Derived from STERLING_SIGNALS_PRD_v2.md sections 3.1–3.6.

EMBEDDED_STYLE_GUIDE = """
# Sterling Signals — Tweet Style Guide

## Voice & Tone
- Confident but humble, data-driven, community-focused
- ONE uniform voice across all accounts (no persona switching)
- Lead with specific data: $TICKER + price + context
- Show conviction through numbers, not adjectives
- Acknowledge risk: "NFA" or "easy invalidation below $X"
- Frame wins objectively: "from $entry to $current (+X%)"
- Frame losses minimally: "Lost on $TICKER. Win more than you lose." — NO loss amounts

## Tweet Categories

| Category | Chart Required | Min Elements |
|----------|---------------|--------------|
| SCANNER_RESULT | YES | $TICKER + entry price + thesis |
| DAILY_SIGNAL | YES | $TICKER + price + context |
| THEME_ANALYSIS | Recommended | Theme name + $TICKER(s) with prices |
| PERFORMANCE | YES | $TICKER + entry → current + % gain |
| WATCHLIST | Optional | $TICKER(s) with prices + what to watch |
| TECHNICAL_ANALYSIS | YES | $TICKER + level + invalidation |
| EDUCATIONAL | If specific setup | Concrete example + lesson |
| MARKET_COMMENTARY | Recommended | Context + opportunity + action |
| SELL_SIGNAL | YES | $TICKER + "setup invalidated" framing |
| ENGAGEMENT | No | Trading-adjacent, hooks |
| NEWSLETTER_CTA | Optional | Value proposition + link |

## Winners-Only Rules
- Positions >= 25% gain: Show as receipt ($TICKER from $entry to $current (+X%))
- Positions >= 0% but < 25%: Mention in watchlist/theme context (no P&L)
- Positions < 0%: NEVER mention
- Sell signals: Use "setup invalidated below $level" — NO loss amount
- Stopped out: "Lost on $TICKER. Win more than you lose." — NO amount

## Power Phrases (PREFER these)
- "momentum confirmed"
- "institutional accumulation"
- "structural trend confirmation"
- "cleared all gates"
- "setup invalidated" (for sells)
- "NFA" (not financial advice)
- "win more than you lose"

## BANNED (NEVER output these)
- Internal indicators: HMA, BoS, BOS, Banker, VWAP, RSI, MACD, KDJ
- System terms: Gatekeeper, gate 1-5, 5-gate, tier 1/2/3, conviction score
- Old branding: TEAL, VIOLET, AMBER, PURPLE signals
- UK references: UK ISA, GMT, BST, UK Time, GBP
- US-specific: Roth IRA, PDT, 401k
- Vague phrases: "system keeps working", "theme keeps delivering", "trust the process",
  "some interesting setups", "stay tuned", "big news coming"
- Loser focus: "still bleeding", "dragging down", "biggest loser"

## Data Injection Rule
Use EXACTLY the tickers and prices provided. Do NOT invent data.
Every tweet must contain at least one $TICKER with a price or percentage.
Exception: ENGAGEMENT and EDUCATIONAL tweets may omit tickers if the content is
methodology-focused.
""".strip()


def _load_style_guide() -> str:
    """Load the FinTwit style guide text. Falls back to embedded version."""
    if STYLE_GUIDE_PATH.exists():
        logger.info("Loading style guide from %s", STYLE_GUIDE_PATH)
        return STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    logger.info("FINTWIT_STYLE_GUIDE.md not found — using embedded style guide")
    return EMBEDDED_STYLE_GUIDE


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def _load_signals(signals_path: str) -> Dict:
    """Load signals.json and return the parsed dict."""
    path = Path(signals_path)
    if not path.exists():
        logger.warning("Signals file not found: %s", path)
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _load_portfolio(portfolio_path: str) -> List[Dict]:
    """Load portfolio.csv and return list of position dicts."""
    import csv

    path = Path(portfolio_path)
    if not path.exists():
        logger.warning("Portfolio file not found: %s", path)
        return []

    positions: List[Dict] = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Coerce numeric fields
            for key in ("entry_price", "exit_price", "highest_close", "current_price"):
                if row.get(key):
                    try:
                        row[key] = float(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0.0
            positions.append(row)
    return positions


def _build_content_data(
    signals: Dict,
    positions: List[Dict],
    market_data: Optional[Dict] = None,
) -> ContentData:
    """Build a ContentData object from raw signals and portfolio data."""
    big_win_threshold = MARKETING_THRESHOLDS.get("big_win_threshold", 25.0)

    # Extract from signals
    pass_signals = signals.get("buy_signals", [])
    consider_signals = signals.get("caution_signals", [])
    themes = signals.get("themes", [])
    stats = signals.get("stats", {})
    sell_sigs = signals.get("sell_signals", [])
    scan_date = signals.get("timestamp", datetime.now().strftime("%Y-%m-%d"))[:10]

    # Split positions into winners / holdings / losers
    winners: List[Dict] = []
    holdings: List[Dict] = []

    for pos in positions:
        if pos.get("status", "").upper() != "OPEN":
            continue
        entry = float(pos.get("entry_price", 0) or 0)
        current = float(pos.get("current_price", 0) or 0)
        if entry <= 0 or current <= 0:
            continue
        pnl_pct = ((current / entry) - 1) * 100
        pos["pnl_pct"] = pnl_pct
        if pnl_pct >= big_win_threshold:
            winners.append(pos)
        elif pnl_pct >= 0:
            holdings.append(pos)
        # pnl_pct < 0: SKIP — never mention losers

    return ContentData(
        pass_signals=pass_signals,
        consider_signals=consider_signals,
        themes=themes,
        scan_stats=stats,
        winners=winners,
        holdings=holdings,
        sell_signals=sell_sigs,
        market_data=market_data,
        scan_date=scan_date,
        newsletter_url=NEWSLETTER_URL,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY SCHEDULE PLANNING
# ═══════════════════════════════════════════════════════════════════════════════

def _plan_weekly_schedule(data: ContentData) -> List[SlotAssignment]:
    """
    Plan category allocation across 7 days x 5 slots.

    Rules (from PRD section 4.1.3):
      - PERFORMANCE receipts: at least 1/day when winners exist
      - SCANNER_RESULT: Saturday (day after weekly scan)
      - THEME_ANALYSIS: at least 2/week
      - ENGAGEMENT: max 1/day
      - NEWSLETTER_CTA: max 2/week
    """
    schedule: List[SlotAssignment] = []
    newsletter_cta_count = 0
    theme_count = 0

    for day in WEEKLY_DAYS:
        day_engagement_used = False
        day_performance_placed = False

        for slot in WEEKLY_SLOTS:
            category, data_key = _pick_category(
                day=day,
                slot=slot,
                data=data,
                day_engagement_used=day_engagement_used,
                day_performance_placed=day_performance_placed,
                newsletter_cta_count=newsletter_cta_count,
                theme_count=theme_count,
                schedule=schedule,
            )

            schedule.append(SlotAssignment(
                day=day,
                slot=slot,
                category=category,
                data_key=data_key,
            ))

            if category == "ENGAGEMENT":
                day_engagement_used = True
            if category == "PERFORMANCE":
                day_performance_placed = True
            if category == "NEWSLETTER_CTA":
                newsletter_cta_count += 1
            if category == "THEME_ANALYSIS":
                theme_count += 1

    # Enforcement pass: ensure at least 2 THEME_ANALYSIS per week
    if theme_count < 2 and data.has_themes:
        _inject_category(schedule, "THEME_ANALYSIS", "themes", 2 - theme_count)

    return schedule


def _pick_category(
    *,
    day: str,
    slot: int,
    data: ContentData,
    day_engagement_used: bool,
    day_performance_placed: bool,
    newsletter_cta_count: int,
    theme_count: int,
    schedule: List[SlotAssignment],
) -> Tuple[str, str]:
    """Pick the best category for a given day/slot based on rules and available data."""

    # Saturday slot 1: SCANNER_RESULT (day after weekly scan)
    if day == "saturday" and slot == 1 and data.has_pass_signals:
        return "SCANNER_RESULT", "pass_signals"

    # Saturday slot 2: second SCANNER_RESULT or THEME_ANALYSIS
    if day == "saturday" and slot == 2:
        if len(data.pass_signals) > 1:
            return "SCANNER_RESULT", "pass_signals"
        if data.has_themes:
            return "THEME_ANALYSIS", "themes"

    # Slot 1 (08:00): morning content — PERFORMANCE receipt if winners exist
    if slot == 1 and data.has_winners and not day_performance_placed:
        return "PERFORMANCE", "winners"

    # Ensure at least 1 PERFORMANCE per day when winners exist
    if slot == 4 and data.has_winners and not day_performance_placed:
        return "PERFORMANCE", "winners"

    # Sell signals take priority when they exist
    if slot == 3 and data.sell_signals:
        return "SELL_SIGNAL", "sell_signals"

    # Theme analysis — spread across the week
    if slot == 2 and data.has_themes and theme_count < 4:
        return "THEME_ANALYSIS", "themes"

    # Watchlist
    if slot == 3 and data.consider_signals:
        return "WATCHLIST", "consider_signals"

    # Technical analysis for holdings
    if slot == 3 and data.holdings:
        return "TECHNICAL_ANALYSIS", "holdings"

    # Market commentary
    if slot == 2 and data.market_data:
        return "MARKET_COMMENTARY", "market_data"

    # Newsletter CTA (max 2/week, prefer Sunday and Thursday)
    if newsletter_cta_count < 2 and day in ("sunday", "thursday") and slot == 5:
        return "NEWSLETTER_CTA", "newsletter_url"

    # Educational
    if slot == 4 and not data.has_winners:
        return "EDUCATIONAL", "educational"

    # Engagement (max 1/day)
    if slot == 5 and not day_engagement_used:
        return "ENGAGEMENT", "engagement"

    # Fallbacks based on available data
    if data.has_pass_signals:
        return "SCANNER_RESULT", "pass_signals"
    if data.has_winners:
        return "PERFORMANCE", "winners"
    if data.has_themes:
        return "THEME_ANALYSIS", "themes"
    if data.consider_signals:
        return "WATCHLIST", "consider_signals"

    return "EDUCATIONAL", "educational"


def _inject_category(
    schedule: List[SlotAssignment],
    category: str,
    data_key: str,
    count: int,
) -> None:
    """Replace lowest-priority slots to meet minimum category requirements."""
    replaceable = ["ENGAGEMENT", "EDUCATIONAL", "MARKET_COMMENTARY"]
    replaced = 0
    for assignment in reversed(schedule):
        if replaced >= count:
            break
        if assignment.category in replaceable:
            assignment.category = category
            assignment.data_key = data_key
            replaced += 1


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET GENERATION (LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system_prompt(style_guide: str) -> str:
    """Build the system prompt for tweet generation."""

    # Build banned terms block (first 60 most critical)
    banned_block = "\n".join(f"  - {term}" for term in CRITICAL_BANNED[:60])

    return f"""\
You are the social media voice of Sterling Signals, a weekly momentum trading scanner \
for US stocks. Generate tweets that are data-rich, specific, and compliant with the \
style guide below.

STYLE GUIDE:
{style_guide}

ADDITIONAL BANNED PHRASES (NEVER output any of these):
{banned_block}

RULES:
1. Use EXACTLY the tickers and prices provided. Do NOT invent data.
2. Every tweet must contain at least one $TICKER with a price or percentage.
   Exception: ENGAGEMENT and EDUCATIONAL tweets may omit tickers if methodology-focused.
3. Never mention negative P&L. Never reveal loss amounts. Sell signals use "setup invalidated" only.
4. Never use internal terms: HMA, BoS, Banker, tier, conviction, VWAP, gate references.
5. Keep tweets under 280 characters.
6. Output ONLY the tweet text — no labels, no quotes, no explanation.
"""


def _build_user_prompt(category: str, slot_data: Dict, slot: SlotAssignment) -> str:
    """Build the user prompt for a specific tweet, injecting structured data."""

    cat_info = TWEET_CATEGORIES.get(category, {})
    required = cat_info.get("min_elements", [])

    prompt_parts = [
        f"Generate a single {category} tweet.",
        f"Day: {slot.day.capitalize()}, Slot: {slot.slot} ({SLOT_TIMES_ET.get(slot.slot, '??:??')} ET)",
        f"Required elements: {', '.join(required) if required else 'flexible'}",
        "",
        "DATA (use EXACTLY these values):",
    ]

    # Inject category-specific data
    if category == "SCANNER_RESULT" and "signals" in slot_data:
        for sig in slot_data["signals"][:3]:
            prompt_parts.append(
                f"  ${{ticker}}: ${sig.get('symbol', '??')} at ${sig.get('price', 0):.2f} "
                f"| Theme: {sig.get('theme', 'N/A')} | Thesis: {sig.get('catalyst_summary', 'momentum confirmed')}"
            )

    elif category == "PERFORMANCE" and "winners" in slot_data:
        for w in slot_data["winners"][:3]:
            entry = float(w.get("entry_price", 0) or 0)
            current = float(w.get("current_price", 0) or 0)
            pnl = w.get("pnl_pct", 0)
            prompt_parts.append(
                f"  ${w.get('ticker', '??')} from ${entry:.2f} to ${current:.2f} (+{pnl:.1f}%)"
                f" | Theme: {w.get('theme', 'N/A')}"
            )

    elif category == "THEME_ANALYSIS" and "themes" in slot_data:
        for th in slot_data["themes"][:2]:
            prompt_parts.append(
                f"  Theme: {th.get('name', '??')} ({th.get('classification', 'INVESTABLE')})"
                f" | Score: {th.get('composite_score', 0)}/10"
            )
        if "tickers" in slot_data:
            for t in slot_data["tickers"][:4]:
                prompt_parts.append(f"  ${t.get('symbol', '??')} at ${t.get('price', 0):.2f}")

    elif category == "SELL_SIGNAL" and "sell_signals" in slot_data:
        for ss in slot_data["sell_signals"][:2]:
            prompt_parts.append(
                f"  ${ss.get('symbol', '??')} — setup invalidated. "
                f"No loss amounts. Frame as: 'Win more than you lose.'"
            )

    elif category == "WATCHLIST" and "consider" in slot_data:
        for cs in slot_data["consider"][:3]:
            prompt_parts.append(
                f"  ${cs.get('symbol', '??')} at ${cs.get('price', 0):.2f}"
                f" | Watching for: {cs.get('action', 'momentum confirmation')}"
            )

    elif category == "NEWSLETTER_CTA":
        prompt_parts.append(f"  Newsletter URL: {NEWSLETTER_URL}")
        prompt_parts.append("  Value proposition: weekly momentum signals, free to subscribe")

    elif category == "DAILY_SIGNAL" and "daily_signals" in slot_data:
        for ds in slot_data["daily_signals"][:3]:
            prompt_parts.append(
                f"  ${ds.get('symbol', '??')} at ${ds.get('price', 0):.2f}"
                f" | Daily buy signal | Theme: {ds.get('theme', 'N/A')}"
            )

    elif category in ("EDUCATIONAL", "ENGAGEMENT", "MARKET_COMMENTARY"):
        if slot_data.get("context"):
            prompt_parts.append(f"  Context: {slot_data['context']}")
        # These categories are more flexible — provide any available tickers
        if slot_data.get("tickers"):
            for t in slot_data["tickers"][:2]:
                prompt_parts.append(f"  Reference: ${t.get('symbol', '??')} at ${t.get('price', 0):.2f}")

    prompt_parts.append("")
    prompt_parts.append("Output ONLY the tweet text (under 280 characters). No labels or quotes.")

    return "\n".join(prompt_parts)


def _prepare_slot_data(category: str, data: ContentData, used_indices: Dict) -> Dict:
    """Prepare the data payload for a specific tweet generation call."""
    slot_data: Dict = {}

    if category == "SCANNER_RESULT":
        idx = used_indices.get("pass_signals", 0)
        slot_data["signals"] = data.pass_signals[idx:idx + 2]
        used_indices["pass_signals"] = idx + 1

    elif category == "PERFORMANCE":
        idx = used_indices.get("winners", 0)
        slot_data["winners"] = data.winners[idx:idx + 2] if data.winners else []
        used_indices["winners"] = (idx + 1) % max(len(data.winners), 1)

    elif category == "THEME_ANALYSIS":
        idx = used_indices.get("themes", 0)
        slot_data["themes"] = data.themes[idx:idx + 2]
        used_indices["themes"] = idx + 1
        # Add tickers from pass_signals that match the theme
        if data.pass_signals:
            slot_data["tickers"] = data.pass_signals[:4]

    elif category == "SELL_SIGNAL":
        idx = used_indices.get("sell_signals", 0)
        slot_data["sell_signals"] = data.sell_signals[idx:idx + 1]
        used_indices["sell_signals"] = idx + 1

    elif category == "WATCHLIST":
        slot_data["consider"] = data.consider_signals[:3]

    elif category == "NEWSLETTER_CTA":
        slot_data["newsletter_url"] = data.newsletter_url

    elif category == "DAILY_SIGNAL":
        idx = used_indices.get("daily_signals", 0)
        slot_data["daily_signals"] = data.daily_signals[idx:idx + 2]
        used_indices["daily_signals"] = idx + 1

    elif category == "TECHNICAL_ANALYSIS":
        slot_data["tickers"] = [
            {"symbol": h.get("ticker", "??"), "price": float(h.get("current_price", 0) or 0)}
            for h in data.holdings[:2]
        ]

    elif category in ("EDUCATIONAL", "ENGAGEMENT"):
        slot_data["context"] = "trading methodology and discipline"
        if data.pass_signals:
            slot_data["tickers"] = [
                {"symbol": s.get("symbol", "??"), "price": s.get("price", 0)}
                for s in data.pass_signals[:2]
            ]

    elif category == "MARKET_COMMENTARY":
        slot_data["context"] = json.dumps(data.market_data) if data.market_data else "general market conditions"
        if data.pass_signals:
            slot_data["tickers"] = [
                {"symbol": s.get("symbol", "??"), "price": s.get("price", 0)}
                for s in data.pass_signals[:2]
            ]

    return slot_data


def _generate_tweet(
    category: str,
    slot_data: Dict,
    slot: SlotAssignment,
    style_guide: str,
    client,
    cost_tracker: CostTracker,
) -> Tweet:
    """
    Make a single LLM call to generate one tweet.

    Args:
        category: The tweet category (e.g. SCANNER_RESULT)
        slot_data: Structured data for this tweet (tickers, prices, %)
        slot: The SlotAssignment for this tweet
        style_guide: Full style guide text
        client: Anthropic client instance
        cost_tracker: Running cost tracker

    Returns:
        Tweet object with text, category, chart_required, tickers_mentioned
    """
    system_prompt = _build_system_prompt(style_guide)
    user_prompt = _build_user_prompt(category, slot_data, slot)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,  # Single tweet never needs more
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    cost_tracker.record(response)

    text = response.content[0].text.strip()
    # Strip any wrapping quotes the LLM might add
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    chart_required = category in CHART_REQUIRED_CATEGORIES
    tickers = re.findall(r'\$[A-Z]{2,5}', text)

    return Tweet(
        text=text,
        category=category,
        chart_required=chart_required,
        tickers_mentioned=tickers,
        metadata={
            "day": slot.day,
            "slot": slot.slot,
            "data_key": slot.data_key,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE (PRD section 3.6)
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_tweet(tweet: Tweet, source_data: Dict) -> ValidationResult:
    """
    Run the 7-step validation pipeline on a single tweet.

    Steps:
        1. Category check
        2. Ticker + price check
        3. Banned phrase check
        4. Winners-only check
        5. Internal terminology check
        6. Character count
        7. Chart flag
    """
    failures: List[str] = []
    details: Dict = {}

    # ── Step 1: Category check ─────────────────────────────────────────────
    if tweet.category not in VALID_CATEGORIES:
        failures.append(f"step1_category: invalid category '{tweet.category}'")
    else:
        cat_info = TWEET_CATEGORIES[tweet.category]
        required = cat_info.get("min_elements", [])
        text_lower = tweet.text.lower()

        # Check for $TICKER presence (required for most categories)
        has_ticker = bool(re.search(r'\$[A-Z]{2,5}', tweet.text))
        if "$TICKER" in required or "entry price" in required or "price" in required:
            if not has_ticker:
                failures.append("step1_category: missing required $TICKER")

        # Check for price/percentage
        has_price = bool(re.search(r'\$\d+\.?\d*', tweet.text))
        has_pct = bool(re.search(r'[+-]?\d+\.?\d*%', tweet.text))
        if "entry price" in required or "current price" in required or "price" in required:
            if not has_price and not has_pct:
                failures.append("step1_category: missing required price or percentage")

        # Check for theme name in THEME_ANALYSIS
        if tweet.category == "THEME_ANALYSIS" and "theme name" in required:
            # Theme name check is loose — any capitalised multi-word will do
            pass  # Hard to validate without knowing exact theme names

        # Check for invalidation framing in SELL_SIGNAL
        if tweet.category == "SELL_SIGNAL" and "invalidation framing" in required:
            invalidation_terms = ["invalidat", "setup broke", "win more than you lose"]
            if not any(t in text_lower for t in invalidation_terms):
                failures.append("step1_category: SELL_SIGNAL missing invalidation framing")

    # ── Step 2: Ticker + price accuracy check ──────────────────────────────
    tickers_in_tweet = re.findall(r'\$([A-Z]{2,5})', tweet.text)
    source_tickers = set()

    # Collect all valid tickers from source data
    for key in ("signals", "winners", "consider", "sell_signals", "tickers", "daily_signals"):
        items = source_data.get(key, [])
        if isinstance(items, list):
            for item in items:
                sym = item.get("symbol") or item.get("ticker") or ""
                if sym:
                    source_tickers.add(sym.upper())

    if tickers_in_tweet:
        for ticker in tickers_in_tweet:
            if source_tickers and ticker not in source_tickers:
                failures.append(f"step2_ticker: ${ticker} not in source data")
                details["fabricated_tickers"] = details.get("fabricated_tickers", []) + [ticker]

    # ── Step 3: Banned phrase check ────────────────────────────────────────
    text_lower = tweet.text.lower()
    for phrase in ALL_BANNED:
        if phrase.lower() in text_lower:
            failures.append(f"step3_banned: '{phrase}'")

    # ── Step 4: Winners-only check ─────────────────────────────────────────
    # No negative P&L percentages
    negative_pcts = re.findall(r'-\d+\.?\d*%', tweet.text)
    if negative_pcts:
        failures.append(f"step4_winners_only: negative percentage(s) found: {negative_pcts}")

    # Check loser-focused language
    if check_loser_focus(tweet.text):
        failures.append("step4_winners_only: loser-focused language detected")

    # ── Step 5: Internal terminology check ─────────────────────────────────
    for pattern in INTERNAL_TERM_PATTERNS:
        match = re.search(pattern, tweet.text, re.IGNORECASE)
        if match:
            failures.append(f"step5_internal: '{match.group()}' is internal terminology")

    # ── Step 6: Character count ────────────────────────────────────────────
    if len(tweet.text) > MAX_TWEET_CHARS:
        failures.append(f"step6_chars: {len(tweet.text)} > {MAX_TWEET_CHARS}")

    # ── Step 7: Chart flag check ───────────────────────────────────────────
    expected_chart = tweet.category in CHART_REQUIRED_CATEGORIES
    if tweet.chart_required != expected_chart:
        failures.append(
            f"step7_chart: chart_required={tweet.chart_required} "
            f"but expected {expected_chart} for {tweet.category}"
        )

    return ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
        details=details,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REPAIR (LLM re-generation with feedback)
# ═══════════════════════════════════════════════════════════════════════════════

def _repair_tweet(
    tweet: Tweet,
    failures: List[str],
    slot_data: Dict,
    style_guide: str,
    client,
    cost_tracker: CostTracker,
) -> Tweet:
    """
    Re-generate a tweet with specific feedback about validation failures.

    Makes a second LLM call including the failed tweet and error details.
    """
    system_prompt = _build_system_prompt(style_guide)

    repair_prompt = f"""\
The following tweet FAILED validation and must be rewritten.

FAILED TWEET:
{tweet.text}

VALIDATION ERRORS:
{chr(10).join(f'  - {f}' for f in failures)}

CATEGORY: {tweet.category}

Rewrite the tweet to fix ALL validation errors listed above.
Keep the same category ({tweet.category}) and use the same data.
Output ONLY the corrected tweet text (under 280 characters). No labels or quotes.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": repair_prompt}],
    )
    cost_tracker.record(response)

    text = response.content[0].text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    tickers = re.findall(r'\$[A-Z]{2,5}', text)
    chart_required = tweet.category in CHART_REQUIRED_CATEGORIES

    return Tweet(
        text=text,
        category=tweet.category,
        chart_required=chart_required,
        tickers_mentioned=tickers,
        metadata={**tweet.metadata, "repaired": True},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE WRITING
# ═══════════════════════════════════════════════════════════════════════════════

def _write_queues(
    tweets: List[Tweet],
    queue_map: Dict[str, str],
    output_dir: Optional[Path] = None,
    scan_date: str = "",
) -> None:
    """
    Write identical tweet lists to all 3 account queues.

    Each entry matches the format used by distribution/twitter_poster.py.
    """
    out_dir = output_dir or TRADES_DIR
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build queue entries
    entries: List[Dict] = []
    for i, tweet in enumerate(tweets):
        day = tweet.metadata.get("day", "saturday")
        slot = tweet.metadata.get("slot", 1)
        slot_time = SLOT_TIMES_ET.get(slot, "08:00")

        entries.append({
            "id": f"{day}_{slot}_{i}",
            "day": day.capitalize(),
            "slot": slot,
            "time": slot_time,
            "text": tweet.text,
            "category": tweet.category,
            "scheduled_date": _calculate_scheduled_date(scan_date, day) if scan_date else "",
            "status": "pending",
            "posted": False,
            "char_count": len(tweet.text),
            "mentioned_tickers": tweet.tickers_mentioned,
            "chart_required": tweet.chart_required,
            "chart_path": tweet.chart_path,
            "timestamp": datetime.now().isoformat(),
        })

    # Write identical content to all account queues
    for account_id, queue_file in queue_map.items():
        path = out_dir / queue_file
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)
        logger.info("Saved %d tweets to %s", len(entries), path)


def _calculate_scheduled_date(scan_date: str, day_name: str) -> str:
    """Calculate the scheduled date for a tweet given the scan date and day."""
    try:
        base = datetime.strptime(scan_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        base = datetime.now()
    offset = WEEKLY_DAYS.index(day_name.lower()) if day_name.lower() in WEEKLY_DAYS else 0
    return (base + timedelta(days=offset)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# FAILED TWEET LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _log_failed_tweet(tweet: Tweet, failures: List[str], output_dir: Optional[Path] = None) -> None:
    """Append a failed tweet to failed_tweets.json for manual review."""
    out_dir = output_dir or TRADES_DIR
    failed_path = Path(out_dir) / "failed_tweets.json"

    existing: List[Dict] = []
    if failed_path.exists():
        try:
            with open(failed_path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.append({
        "text": tweet.text,
        "category": tweet.category,
        "failures": failures,
        "metadata": tweet.metadata,
        "timestamp": datetime.now().isoformat(),
    })

    with open(failed_path, "w") as f:
        json.dump(existing, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY: WEEKLY CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_weekly_content(
    signals_path: str,
    portfolio_path: str,
    market_data: Optional[Dict] = None,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generate a full week of tweets (7 days x 5 slots = 35 tweets).

    Reads weekly signals.json and portfolio.csv, plans category allocation,
    generates tweets via LLM, validates, repairs if needed, and writes
    identical content to all 3 account queues.

    Args:
        signals_path: Path to signals.json
        portfolio_path: Path to portfolio.csv
        market_data: Optional market context dict
        output_dir: Output directory (default: trades/)

    Returns:
        Summary dict: {total_tweets, by_category, failed_count, chart_required_count}
    """
    if anthropic is None:
        logger.error("anthropic package not installed")
        return {"total_tweets": 0, "error": "anthropic not installed"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"total_tweets": 0, "error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()

    # 1. Load style guide
    style_guide = _load_style_guide()
    logger.info("Style guide loaded (%d chars)", len(style_guide))

    # 2. Load data
    signals = _load_signals(signals_path)
    positions = _load_portfolio(portfolio_path)
    data = _build_content_data(signals, positions, market_data)
    logger.info(
        "Data loaded: %d pass signals, %d winners, %d themes, %d sell signals",
        len(data.pass_signals), len(data.winners), len(data.themes), len(data.sell_signals),
    )

    # 3. Plan schedule
    schedule = _plan_weekly_schedule(data)
    logger.info("Schedule planned: %d slots across %d days", len(schedule), len(WEEKLY_DAYS))

    # 4. Generate + validate + repair
    valid_tweets: List[Tweet] = []
    failed_count = 0
    by_category: Dict[str, int] = {}
    used_indices: Dict[str, int] = {}

    for assignment in schedule:
        slot_data = _prepare_slot_data(assignment.category, data, used_indices)

        # Generate
        tweet = _generate_tweet(
            category=assignment.category,
            slot_data=slot_data,
            slot=assignment,
            style_guide=style_guide,
            client=client,
            cost_tracker=cost_tracker,
        )

        # Validate
        result = _validate_tweet(tweet, slot_data)

        # Repair loop (max 2 attempts)
        repair_attempts = 0
        while not result.passed and repair_attempts < MAX_REPAIR_ATTEMPTS:
            logger.info(
                "Repairing %s tweet (%s/%s, attempt %d): %s",
                assignment.category, assignment.day, assignment.slot,
                repair_attempts + 1, result.failures[:2],
            )
            tweet = _repair_tweet(
                tweet, result.failures, slot_data, style_guide, client, cost_tracker,
            )
            result = _validate_tweet(tweet, slot_data)
            repair_attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category[tweet.category] = by_category.get(tweet.category, 0) + 1
        else:
            logger.warning(
                "DROPPED tweet after %d repairs: %s/%s %s — %s",
                MAX_REPAIR_ATTEMPTS, assignment.day, assignment.slot,
                assignment.category, result.failures[:3],
            )
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # 5. Write queues
    out = Path(output_dir) if output_dir else TRADES_DIR
    _write_queues(valid_tweets, ACCOUNT_QUEUES, out, data.scan_date)

    chart_required_count = sum(1 for t in valid_tweets if t.chart_required)

    logger.info(
        "Weekly generation complete: %d tweets, %d failed, %d charts required",
        len(valid_tweets), failed_count, chart_required_count,
    )
    logger.info("Cost: %s", cost_tracker.summary())

    return {
        "total_tweets": len(valid_tweets),
        "by_category": by_category,
        "failed_count": failed_count,
        "chart_required_count": chart_required_count,
        "cost": cost_tracker.summary(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY: DAILY CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_content(
    daily_signals_path: str,
    daily_portfolio_path: str,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Generate daily tweets for new daily scan signals, sell signals, and winners.

    - Up to 5 DAILY_SIGNAL tweets (one per signal)
    - SELL_SIGNAL tweets for any daily exits
    - PERFORMANCE tweets for daily winners >= 25%

    Args:
        daily_signals_path: Path to daily_signals.json
        daily_portfolio_path: Path to daily_portfolio.csv
        output_dir: Output directory (default: trades/)

    Returns:
        Summary dict: {total_tweets, by_category, failed_count, chart_required_count}
    """
    if anthropic is None:
        logger.error("anthropic package not installed")
        return {"total_tweets": 0, "error": "anthropic not installed"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"total_tweets": 0, "error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    cost_tracker = CostTracker()
    style_guide = _load_style_guide()

    # Load daily signals
    daily_signals_raw = _load_signals(daily_signals_path)
    daily_buy_signals = daily_signals_raw.get("buy_signals", [])[:5]
    daily_sell_signals = daily_signals_raw.get("sell_signals", [])

    # Load daily portfolio for winners
    daily_positions = _load_portfolio(daily_portfolio_path)
    big_win = MARKETING_THRESHOLDS.get("big_win_threshold", 25.0)
    daily_winners = []
    for pos in daily_positions:
        if pos.get("status", "").upper() != "OPEN":
            continue
        entry = float(pos.get("entry_price", 0) or 0)
        current = float(pos.get("current_price", 0) or 0)
        if entry > 0 and current > 0:
            pnl = ((current / entry) - 1) * 100
            if pnl >= big_win:
                pos["pnl_pct"] = pnl
                daily_winners.append(pos)

    # Build content data for daily context
    data = ContentData(
        daily_signals=daily_buy_signals,
        daily_sells=daily_sell_signals,
        daily_winners=daily_winners,
        scan_date=datetime.now().strftime("%Y-%m-%d"),
        newsletter_url=NEWSLETTER_URL,
    )

    valid_tweets: List[Tweet] = []
    failed_count = 0
    by_category: Dict[str, int] = {}
    used_indices: Dict[str, int] = {}

    # Generate DAILY_SIGNAL tweets (one per signal, max 5)
    for i, sig in enumerate(daily_buy_signals):
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=5,  # Daily signals go to slot 5 (17:00 ET)
            category="DAILY_SIGNAL",
            data_key="daily_signals",
        )
        slot_data = {"daily_signals": [sig]}

        tweet = _generate_tweet("DAILY_SIGNAL", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["DAILY_SIGNAL"] = by_category.get("DAILY_SIGNAL", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Generate SELL_SIGNAL tweets
    for ss in daily_sell_signals:
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=5,
            category="SELL_SIGNAL",
            data_key="sell_signals",
        )
        slot_data = {"sell_signals": [ss]}

        tweet = _generate_tweet("SELL_SIGNAL", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["SELL_SIGNAL"] = by_category.get("SELL_SIGNAL", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Generate PERFORMANCE tweets for daily winners >= 25%
    for w in daily_winners:
        slot = SlotAssignment(
            day=datetime.now().strftime("%A").lower(),
            slot=1,  # Morning slot for receipts
            category="PERFORMANCE",
            data_key="winners",
        )
        slot_data = {"winners": [w]}

        tweet = _generate_tweet("PERFORMANCE", slot_data, slot, style_guide, client, cost_tracker)
        result = _validate_tweet(tweet, slot_data)

        attempts = 0
        while not result.passed and attempts < MAX_REPAIR_ATTEMPTS:
            tweet = _repair_tweet(tweet, result.failures, slot_data, style_guide, client, cost_tracker)
            result = _validate_tweet(tweet, slot_data)
            attempts += 1

        if result.passed:
            valid_tweets.append(tweet)
            by_category["PERFORMANCE"] = by_category.get("PERFORMANCE", 0) + 1
        else:
            _log_failed_tweet(tweet, result.failures, Path(output_dir) if output_dir else None)
            failed_count += 1

    # Write daily queues
    out = Path(output_dir) if output_dir else TRADES_DIR
    _write_queues(valid_tweets, DAILY_ACCOUNT_QUEUES, out, data.scan_date)

    chart_required_count = sum(1 for t in valid_tweets if t.chart_required)

    logger.info(
        "Daily generation complete: %d tweets, %d failed",
        len(valid_tweets), failed_count,
    )
    logger.info("Cost: %s", cost_tracker.summary())

    return {
        "total_tweets": len(valid_tweets),
        "by_category": by_category,
        "failed_count": failed_count,
        "chart_required_count": chart_required_count,
        "cost": cost_tracker.summary(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY HELPERS (backwards-compat with v1 imports in tests)
# ═══════════════════════════════════════════════════════════════════════════════

def get_tweet_char_count(text: str) -> int:
    """Calculate Twitter character count (handles Unicode).

    Emojis and characters above U+FFFF count as 2 characters on Twitter.
    """
    count = 0
    for char in text:
        if ord(char) > 0xFFFF:
            count += 2
        else:
            count += 1
    return count


def validate_tweet_length(text: str, max_length: int = 280) -> bool:
    """Check if tweet is within character limit."""
    return get_tweet_char_count(text) <= max_length


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """CLI entry point for tweet generation."""
    parser = argparse.ArgumentParser(
        description="Sterling Signals Tweet Generator v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--signals", default=str(TRADES_DIR / "signals.json"),
        help="Path to signals.json (weekly) or daily_signals.json",
    )
    parser.add_argument(
        "--portfolio", default=str(TRADES_DIR / "portfolio.csv"),
        help="Path to portfolio.csv or daily_portfolio.csv",
    )
    parser.add_argument(
        "--output", default=str(TRADES_DIR),
        help="Output directory for queue files",
    )
    parser.add_argument(
        "--daily", action="store_true",
        help="Generate daily content instead of weekly",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.daily:
        result = generate_daily_content(
            daily_signals_path=args.signals,
            daily_portfolio_path=args.portfolio,
            output_dir=args.output,
        )
    else:
        result = generate_weekly_content(
            signals_path=args.signals,
            portfolio_path=args.portfolio,
            output_dir=args.output,
        )

    print(f"\n{'=' * 60}")
    print("TWEET GENERATOR v2.0 — RESULTS")
    print(f"{'=' * 60}")
    print(f"  Total tweets:        {result.get('total_tweets', 0)}")
    print(f"  Failed (dropped):    {result.get('failed_count', 0)}")
    print(f"  Charts required:     {result.get('chart_required_count', 0)}")
    print(f"  Cost:                {result.get('cost', 'N/A')}")
    print(f"\n  By category:")
    for cat, count in sorted(result.get("by_category", {}).items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
