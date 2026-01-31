#!/usr/bin/env python3
"""
REACTION-BASED TWEET GENERATOR
==============================

Generates authentic, human-sounding tweets by having personas REACT to data,
not fill in templates.

Core principle: "You're a trader who just saw X. Write what you'd actually tweet."

Usage:
    from reaction_generator import generate_weekly_content
    
    tweets = generate_weekly_content(scanner_data, portfolio_data)
    
    # Or CLI:
    python reaction_generator.py --scanner-file data.json --output tweets/

Architecture:
    1. Load deep persona definitions (YAML character bibles)
    2. Summarize scanner/portfolio data into "what happened"
    3. For each account, for each day: single Claude call generates all 5 tweets
    4. Validate output (voice consistency, data accuracy, no cross-contamination)
    5. Save to content queues
"""

import json
import yaml
import anthropic
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import re
import random
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass  # dotenv not required if env vars set directly

from morning_briefing import generate_morning_briefing
from editorial_board import create_editorial_plan, validate_editorial_plan

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

PERSONAS_DIR = Path(__file__).parent / "personas"
EXAMPLES_FILE = Path(__file__).parent / "examples" / "tweet_examples.json"

NEWSLETTER_URL = "https://sterlingsignals.substack.com"

# Account mapping
ACCOUNTS = {
    'main': {
        'persona_file': 'alex.yaml',
        'queue_file': 'content_queue.json',
        'examples_key': 'alex',
    },
    'account2': {
        'persona_file': 'rozalia.yaml',
        'queue_file': 'content_queue_account2.json',
        'examples_key': 'rozalia',
    },
    'account3': {
        'persona_file': 'james.yaml',
        'queue_file': 'content_queue_account3.json',
        'examples_key': 'james',
    },
}

# Days of the week in order (starting Saturday for newsletter drop)
DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# Slot times (Eastern)
SLOTS = {
    1: {'time': '08:00', 'context': 'Morning, starting the day'},
    2: {'time': '10:00', 'context': 'Mid-morning, market open 30 mins'},
    3: {'time': '12:30', 'context': 'Midday, lunch break'},
    4: {'time': '15:30', 'context': 'Power hour (3:30pm)'},
    5: {'time': '18:00', 'context': 'After hours, reflecting'},
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Persona:
    """Loaded persona from YAML."""
    name: str
    identity: dict
    background: str
    personality: dict
    voice: dict
    content_approach: dict
    example_tweets: dict
    day_tendencies: dict


@dataclass 
class MarketContext:
    """What happened this week - for personas to react to."""
    scan_date: str
    
    # Signals
    green_signals: List[dict]  # PASS signals with ticker, price, theme
    consider_signals: List[dict]  # CONSIDER signals
    signal_count: int
    
    # Portfolio state
    open_positions: List[dict]  # ticker, pnl_pct, days_held, entry_price
    winners: List[dict]  # 25%+ positions
    losers: List[dict]  # Negative positions (for honesty)
    
    # Recent closes
    closed_trades: List[dict]  # Recent closed with P&L
    
    # Themes
    hot_themes: List[str]
    
    # Metrics
    total_positions: int
    green_count: int
    portfolio_vs_spy: float
    
    # Flags
    is_quiet_week: bool  # Few or no signals
    has_big_winner: bool  # 25%+ position
    has_new_signals: bool  # Fresh signals this week

    # Charts
    chart_manifest: Dict[str, str] = field(default_factory=dict)  # ticker -> image_path


@dataclass
class DayContext:
    """Context for a specific day."""
    day_name: str
    day_number: int  # 0=Saturday
    is_weekend: bool
    is_friday: bool
    is_scan_day: bool  # Friday

    # What to reference
    time_reference: str  # "Friday's close", "today", etc.
    mood: str
    energy: str

    # Temporal guidance
    temporal: dict = field(default_factory=dict)  # from get_temporal_reference()


@dataclass
class GeneratedTweet:
    """A single generated tweet."""
    id: str
    day: str
    slot: int
    time: str
    text: str
    category: str  # Inferred from content
    account: str
    persona_name: str
    generation_method: str = 'reaction'
    
    # For validation
    mentioned_tickers: List[str] = field(default_factory=list)
    has_url: bool = False
    char_count: int = 0
    image_path: Optional[str] = None


@dataclass
class ContentTracker:
    """
    Tracks ALL content across the week: tickers, phrases, and facts.
    Used both for pre-generation avoidance guidance and post-generation flagging.
    """
    # Per-account ticker mentions
    ticker_mentions: Dict[str, Dict[str, int]] = field(default_factory=lambda: {})
    # Per-account phrase usage
    phrase_usage: Dict[str, Dict[str, int]] = field(default_factory=lambda: {})
    # Global fact mentions (cross-account)
    facts_mentioned: Dict[str, int] = field(default_factory=lambda: {})
    # Days generated so far
    days_generated: int = 0

    # Limits
    TICKER_LIMIT_PER_ACCOUNT = 2
    FACT_LIMITS = {
        'scan_count': 2,        # "1,800 stocks" max 2x total
        'portfolio_status': 3,  # "3 green, 1 red" max 3x total
        'spy_comparison': 3,    # "+12.5% vs SPY" max 3x total
        'winner_pnl': 2,       # Specific winner P&L max 2x total
    }

    def _ensure_account(self, account_id: str):
        if account_id not in self.ticker_mentions:
            self.ticker_mentions[account_id] = {}
        if account_id not in self.phrase_usage:
            self.phrase_usage[account_id] = {}

    def record_tweet(self, text: str, account_id: str, persona_name: str):
        """Record all trackable items from a tweet."""
        self._ensure_account(account_id)
        text_lower = text.lower()
        text_upper = text.upper()

        # Track tickers
        for match in re.findall(r'\$([A-Z]{2,5})', text):
            self.ticker_mentions[account_id][match] = \
                self.ticker_mentions[account_id].get(match, 0) + 1

        # Track phrases
        limits_key = {'main': 'alex', 'account2': 'rozalia', 'account3': 'james'}.get(account_id, 'alex')
        for phrase in PHRASE_LIMITS.get(limits_key, {}):
            if phrase in text_lower:
                self.phrase_usage[account_id][phrase] = \
                    self.phrase_usage[account_id].get(phrase, 0) + 1

        # Track facts
        if re.search(r'1[,.]?8\d{2}\s*(stocks?|names?|scanned|tickers?)', text_lower):
            self.facts_mentioned['scan_count'] = self.facts_mentioned.get('scan_count', 0) + 1
        if re.search(r'\d+\s*green.*\d+\s*red|\d+\s*red.*\d+\s*green', text_lower):
            self.facts_mentioned['portfolio_status'] = self.facts_mentioned.get('portfolio_status', 0) + 1
        if re.search(r'[\d.]+%\s*(vs\.?|versus|over|ahead of|beating)\s*s\W?p\W?y', text_lower):
            self.facts_mentioned['spy_comparison'] = self.facts_mentioned.get('spy_comparison', 0) + 1
        if re.search(r'[\d.]+%\s*(winner|gain|up\b|profit)', text_lower):
            self.facts_mentioned['winner_pnl'] = self.facts_mentioned.get('winner_pnl', 0) + 1

    def check_tweet(self, text: str, account_id: str, persona_name: str) -> List[str]:
        """Check if a tweet violates any limits. Returns list of violations."""
        self._ensure_account(account_id)
        violations = []
        text_lower = text.lower()

        # Check tickers
        for match in re.findall(r'\$([A-Z]{2,5})', text):
            current = self.ticker_mentions[account_id].get(match, 0)
            if current > self.TICKER_LIMIT_PER_ACCOUNT:
                violations.append(f'{match} mentioned {current}x (max {self.TICKER_LIMIT_PER_ACCOUNT})')

        # Check phrases
        limits_key = {'main': 'alex', 'account2': 'rozalia', 'account3': 'james'}.get(account_id, 'alex')
        for phrase, max_count in PHRASE_LIMITS.get(limits_key, {}).items():
            if phrase in text_lower:
                current = self.phrase_usage[account_id].get(phrase, 0)
                if current > max_count:
                    violations.append(f'Phrase "{phrase}" used {current}x (max {max_count})')

        # Check facts
        if re.search(r'1[,.]?8\d{2}\s*(stocks?|names?|scanned|tickers?)', text_lower):
            current = self.facts_mentioned.get('scan_count', 0)
            if current > self.FACT_LIMITS['scan_count']:
                violations.append(f'Scan count mentioned {current}x (max {self.FACT_LIMITS["scan_count"]})')
        if re.search(r'\d+\s*green.*\d+\s*red|\d+\s*red.*\d+\s*green', text_lower):
            current = self.facts_mentioned.get('portfolio_status', 0)
            if current > self.FACT_LIMITS['portfolio_status']:
                violations.append(f'Portfolio status mentioned {current}x (max {self.FACT_LIMITS["portfolio_status"]})')
        if re.search(r'[\d.]+%\s*(vs\.?|versus|over|ahead of|beating)\s*s\W?p\W?y', text_lower):
            current = self.facts_mentioned.get('spy_comparison', 0)
            if current > self.FACT_LIMITS['spy_comparison']:
                violations.append(f'SPY comparison mentioned {current}x (max {self.FACT_LIMITS["spy_comparison"]})')

        return violations

    def get_avoidance_guidance(self, account_id: str, persona_name: str) -> str:
        """Generate avoidance rules for the next generation call."""
        self._ensure_account(account_id)
        guidance = []

        # Tickers at or over limit
        at_limit = [t for t, c in self.ticker_mentions[account_id].items()
                     if c >= self.TICKER_LIMIT_PER_ACCOUNT]
        if at_limit:
            guidance.append(f"DO NOT mention these tickers: {', '.join(f'${t}' for t in at_limit)}")

        # Phrases at limit
        limits_key = {'main': 'alex', 'account2': 'rozalia', 'account3': 'james'}.get(account_id, 'alex')
        at_limit_phrases = [p for p, limit in PHRASE_LIMITS.get(limits_key, {}).items()
                            if self.phrase_usage[account_id].get(p, 0) >= limit]
        if at_limit_phrases:
            guidance.append(f"DO NOT use these phrases: {', '.join(f'\"{p}\"' for p in at_limit_phrases)}")

        # Facts at limit
        fact_warnings = []
        if self.facts_mentioned.get('scan_count', 0) >= self.FACT_LIMITS['scan_count']:
            fact_warnings.append('the scan count (1,800 stocks)')
        if self.facts_mentioned.get('portfolio_status', 0) >= self.FACT_LIMITS['portfolio_status']:
            fact_warnings.append('portfolio status (X green, Y red)')
        if self.facts_mentioned.get('spy_comparison', 0) >= self.FACT_LIMITS['spy_comparison']:
            fact_warnings.append('SPY comparison percentage')
        if self.facts_mentioned.get('winner_pnl', 0) >= self.FACT_LIMITS['winner_pnl']:
            fact_warnings.append('specific winner P&L percentages')
        if fact_warnings:
            guidance.append(f"DO NOT repeat these facts: {', '.join(fact_warnings)}")

        # Content shift guidance
        day = self.days_generated
        if day <= 1:
            guidance.append("FOCUS: Scanner results, fresh reactions to the data.")
        elif day <= 3:
            guidance.append("FOCUS: Watchlist stocks, themes, educational angles. Avoid repeating winner stats.")
        elif day <= 5:
            guidance.append("FOCUS: Engagement, process/discipline, forward-looking.")
        else:
            guidance.append("FOCUS: Brief recap, anticipate next scan. Keep it fresh.")

        return '\n'.join(guidance)


# Per-persona phrase weekly limits
PHRASE_LIMITS = {
    'alex': {
        'the system': 3,
        'the scanner': 3,
        'look,': 3,
    },
    'rozalia': {
        "here's the thing": 2,
        "i wish someone told me": 2,
        "honest question": 2,
        "the lesson": 3,
    },
    'james': {
        'eyes on': 2,
        'let the winners run': 1,
        "that's how you": 2,
        'here we go': 2,
    },
}


def get_temporal_reference(day_name: str) -> dict:
    """Return appropriate temporal language for each day."""
    return {
        'Saturday': {
            'for_friday_data': "Friday's close",
            'for_current': "this weekend",
            'avoid': ["yesterday", "today's close"],
        },
        'Sunday': {
            'for_friday_data': "Friday's scan",
            'for_current': "the weekend",
            'avoid': ["yesterday", "today"],
        },
        'Monday': {
            'for_friday_data': "last Friday",
            'for_current': "today",
            'avoid': ["yesterday"],  # Yesterday is Sunday, market closed
        },
        'Tuesday': {
            'for_friday_data': "Friday's close",
            'for_current': "today",
            'avoid': ["yesterday"],  # Don't say yesterday for Friday data
        },
        'Wednesday': {
            'for_friday_data': "this week's scan",
            'for_current': "today",
            'avoid': ["yesterday"],
        },
        'Thursday': {
            'for_friday_data': "this week",
            'for_current': "today",
            'avoid': ["yesterday"],
        },
        'Friday': {
            'for_friday_data': "today's close",
            'for_current': "today",
            'avoid': [],  # All references valid on Friday
        },
    }.get(day_name, {'for_friday_data': 'the scan', 'for_current': 'today', 'avoid': []})


# ═══════════════════════════════════════════════════════════════════════════════
# LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_persona(persona_file: str) -> Persona:
    """Load a persona from YAML file."""
    path = PERSONAS_DIR / persona_file
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    return Persona(
        name=data.get('identity', {}).get('name', 'Unknown'),
        identity=data.get('identity', {}),
        background=data.get('background', ''),
        personality=data.get('personality', {}),
        voice=data.get('voice', {}),
        content_approach=data.get('content_approach', {}),
        example_tweets=data.get('example_tweets', {}),
        day_tendencies=data.get('day_of_week_tendencies', {}),
    )


def load_examples() -> dict:
    """Load curated example tweets."""
    if not EXAMPLES_FILE.exists():
        return {}
    
    with open(EXAMPLES_FILE, 'r') as f:
        return json.load(f)


def create_market_context(scanner_data: dict, portfolio_data: dict) -> MarketContext:
    """Transform raw data into readable market context."""
    
    positions = portfolio_data.get('positions', [])
    closed = portfolio_data.get('closed_trades', [])
    
    green_signals = scanner_data.get('pass_signals', [])
    consider_signals = scanner_data.get('consider_signals', [])
    
    winners = [p for p in positions if p.get('pnl_pct', 0) >= 25]
    losers = [p for p in positions if p.get('pnl_pct', 0) < 0]
    green_positions = [p for p in positions if p.get('pnl_pct', 0) > 0]
    
    hot_themes = []
    for theme in scanner_data.get('prime_themes', []):
        hot_themes.append(theme.get('name', theme) if isinstance(theme, dict) else theme)
    for theme in scanner_data.get('investable_themes', []):
        hot_themes.append(theme.get('name', theme) if isinstance(theme, dict) else theme)
    
    # Load chart manifest if available
    chart_manifest = {}
    charts_dir = Path(__file__).parent / "trades" / "charts"
    if charts_dir.exists():
        for chart_file in charts_dir.glob("*.png"):
            ticker = chart_file.stem.split('_')[0].upper()
            chart_manifest[ticker] = str(chart_file)

    # Also check scanner_data for chart paths
    for signal in green_signals + consider_signals:
        if signal.get('chart_path'):
            chart_manifest[signal['ticker']] = signal['chart_path']

    return MarketContext(
        scan_date=scanner_data.get('scan_date', datetime.now().strftime('%Y-%m-%d')),
        green_signals=green_signals,
        consider_signals=consider_signals,
        signal_count=len(green_signals),
        open_positions=positions,
        winners=winners,
        losers=losers,
        closed_trades=closed[:5],  # Recent 5
        hot_themes=hot_themes[:3],  # Top 3
        total_positions=len(positions),
        green_count=len(green_positions),
        portfolio_vs_spy=portfolio_data.get('vs_spy', 0),
        is_quiet_week=len(green_signals) == 0,
        has_big_winner=len(winners) > 0,
        has_new_signals=len(green_signals) > 0,
        chart_manifest=chart_manifest,
    )


def create_day_context(day_name: str, scan_date: str) -> DayContext:
    """Create context for a specific day."""
    
    day_idx = DAYS.index(day_name)
    is_weekend = day_name in ['Saturday', 'Sunday']
    is_friday = day_name == 'Friday'
    
    time_refs = {
        'Saturday': "Friday's close",
        'Sunday': "the weekend",
        'Monday': "Friday's scan",
        'Tuesday': "this week's scan",
        'Wednesday': "mid-week",
        'Thursday': "tomorrow's scan",
        'Friday': "today's close",
    }
    
    moods = {
        'Saturday': 'reflective',
        'Sunday': 'relaxed prep',
        'Monday': 'fresh start',
        'Tuesday': 'steady',
        'Wednesday': 'midweek check',
        'Thursday': 'building anticipation',
        'Friday': 'game day',
    }
    
    energies = {
        'Saturday': 'low-key',
        'Sunday': 'calm',
        'Monday': 'focused',
        'Tuesday': 'steady',
        'Wednesday': 'steady',
        'Thursday': 'building',
        'Friday': 'peak',
    }
    
    return DayContext(
        day_name=day_name,
        day_number=day_idx,
        is_weekend=is_weekend,
        is_friday=is_friday,
        is_scan_day=is_friday,
        time_reference=time_refs.get(day_name, "the scan"),
        mood=moods.get(day_name, 'neutral'),
        energy=energies.get(day_name, 'steady'),
        temporal=get_temporal_reference(day_name),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDING
# ═══════════════════════════════════════════════════════════════════════════════

def build_persona_section(persona: Persona) -> str:
    """Build the persona section of the prompt."""
    
    voice = persona.voice
    personality = persona.personality
    
    # Core traits
    traits = personality.get('core_traits', [])
    traits_str = ', '.join(traits[:5]) if traits else 'authentic, genuine'
    
    # Voice patterns
    uses = voice.get('vocabulary', {}).get('uses', [])
    never = voice.get('vocabulary', {}).get('never_uses', [])
    
    uses_str = ', '.join(f'"{u}"' for u in uses[:6]) if uses else ''
    never_str = ', '.join(f'"{n}"' for n in never[:6]) if never else ''
    
    # Emoji guidance
    emoji = voice.get('emoji_style', {})
    emoji_freq = emoji.get('frequency', 'sparse')
    emoji_allowed = ', '.join(emoji.get('allowed', []))
    emoji_never = ', '.join(emoji.get('never', []))
    
    return f"""
## WHO YOU ARE: {persona.name}

{persona.background.strip()}

YOUR PERSONALITY: {traits_str}

HOW YOU TALK:
- Phrases you use naturally: {uses_str}
- Phrases you NEVER use (they belong to other accounts): {never_str}
- Emoji usage: {emoji_freq} - allowed: {emoji_allowed} - never: {emoji_never}

YOUR APPROACH:
- You share: {', '.join(persona.content_approach.get('what_he_shares', [])[:4])}
- You avoid: {', '.join(persona.content_approach.get('what_he_doesnt_share', [])[:4])}
"""


def build_market_section(ctx: MarketContext) -> str:
    """Build the market data section."""
    
    # Signals summary
    if ctx.green_signals:
        signals_text = "NEW SIGNALS THIS WEEK:\n"
        for sig in ctx.green_signals[:3]:
            ticker = sig.get('ticker', 'UNKNOWN')
            price = sig.get('close_price') or sig.get('price', 'N/A')
            theme = sig.get('theme', '')
            signals_text += f"  🟢 ${ticker} at ${price}"
            if theme:
                signals_text += f" ({theme})"
            signals_text += "\n"
    else:
        signals_text = "NEW SIGNALS: None this week. Scanner came up empty.\n"
    
    # Consider signals
    if ctx.consider_signals:
        signals_text += "\nWATCHLIST (passed most gates, waiting for confirmation):\n"
        for sig in ctx.consider_signals[:3]:
            ticker = sig.get('ticker', 'UNKNOWN')
            price = sig.get('close_price') or sig.get('price', 'N/A')
            signals_text += f"  🟡 ${ticker} at ${price}\n"
    
    # Winners
    winners_text = ""
    if ctx.winners:
        winners_text = "\nBIG WINNERS (25%+ gains):\n"
        for w in ctx.winners[:3]:
            ticker = w.get('ticker')
            pnl = w.get('pnl_pct', 0)
            entry = w.get('entry_price')
            days = w.get('days_held', 0)
            winners_text += f"  ${ticker}: +{pnl:.1f}%"
            if entry:
                winners_text += f" (entry ${entry})"
            winners_text += f" - held {days} days\n"
    
    # Portfolio summary
    portfolio_text = f"""
PORTFOLIO SNAPSHOT:
- {ctx.total_positions} open positions
- {ctx.green_count} in the green, {len(ctx.losers)} in the red
- vs SPY: {'+' if ctx.portfolio_vs_spy > 0 else ''}{ctx.portfolio_vs_spy:.1f}%
"""
    
    # Themes
    if ctx.hot_themes:
        portfolio_text += f"- Hot themes: {', '.join(ctx.hot_themes)}\n"
    
    return f"""
## WHAT HAPPENED (as of {ctx.scan_date})

{signals_text}
{winners_text}
{portfolio_text}

WEEK SUMMARY:
- {'Quiet week - no new signals' if ctx.is_quiet_week else f'{ctx.signal_count} new signals'}
- {'You have a big winner to talk about!' if ctx.has_big_winner else 'No 25%+ winners yet - focus on process'}
"""


def build_day_section(day_ctx: DayContext, persona: Persona) -> str:
    """Build the day-specific guidance."""

    # Get persona's day tendencies
    tendencies = persona.day_tendencies.get(day_ctx.day_name.lower(), {})
    mood = tendencies.get('mood', day_ctx.mood)
    content_focus = tendencies.get('typical_content', '')
    energy = tendencies.get('energy', day_ctx.energy)

    temporal = day_ctx.temporal

    # Temporal rules
    temporal_rules = f"""
TEMPORAL RULES FOR {day_ctx.day_name}:
- When referencing Friday's scan data, say: "{temporal.get('for_friday_data', 'the scan')}"
- For current day references, say: "{temporal.get('for_current', 'today')}"
"""
    avoid = temporal.get('avoid', [])
    if avoid:
        temporal_rules += f"- NEVER say: {', '.join(f'\"{{a}}\"' for a in avoid)}\n"
        temporal_rules += f"- \"yesterday\" is ONLY valid on Saturday (referring to Friday)\n"

    # Weekend restrictions
    restrictions = ""
    if day_ctx.is_weekend:
        restrictions = """
⚠️ WEEKEND RULES:
- No "power hour" or "into the close" - markets are closed
- More reflective, less urgent
"""

    if day_ctx.is_friday:
        restrictions = """
⚠️ FRIDAY RULES:
- Power hour (slot 4) is PEAK energy - market is live
- Use "today" and "into the close" freely
- This is scan day - newsletter drops after close
"""

    return f"""
## TODAY: {day_ctx.day_name}

Time reference: "{day_ctx.time_reference}"
Your mood: {mood}
Energy level: {energy}
Typical content for you on {day_ctx.day_name}: {content_focus}
{temporal_rules}
{restrictions}
"""


def build_examples_section(persona_key: str, examples: dict, ctx: MarketContext) -> str:
    """Build few-shot examples based on current context."""
    
    persona_examples = examples.get(persona_key, {})
    if not persona_examples:
        return ""
    
    selected = []
    
    # Pick relevant examples based on context
    if ctx.is_quiet_week and 'no_signal_weeks' in persona_examples:
        selected.extend(random.sample(persona_examples['no_signal_weeks'], min(2, len(persona_examples['no_signal_weeks']))))
    
    if ctx.has_big_winner and 'winner_reactions' in persona_examples:
        selected.extend(random.sample(persona_examples['winner_reactions'], min(2, len(persona_examples['winner_reactions']))))
    
    if ctx.has_new_signals and 'scanner_results' in persona_examples:
        selected.extend(random.sample(persona_examples['scanner_results'], min(2, len(persona_examples['scanner_results']))))
    
    # Always include some variety
    if 'vulnerability_honesty' in persona_examples:
        selected.extend(random.sample(persona_examples['vulnerability_honesty'], min(1, len(persona_examples['vulnerability_honesty']))))
    
    if not selected:
        # Fallback to random examples
        all_examples = []
        for category_examples in persona_examples.values():
            if isinstance(category_examples, list):
                all_examples.extend(category_examples)
        selected = random.sample(all_examples, min(4, len(all_examples)))
    
    examples_text = "\n\n".join(f'"{ex}"' for ex in selected[:5])
    
    return f"""
## YOUR VOICE - Examples of how you write:

{examples_text}

Write in THIS voice. Not robotic. Not template-y. Like a real person reacting to real information.
"""


def build_slot_guidance() -> str:
    """Build the slot-by-slot guidance."""
    
    return """
## YOUR 5 TWEETS TODAY

Generate exactly 5 tweets, one for each time slot:

SLOT 1 (8:00am): Morning tweet. You're starting your day.
SLOT 2 (10:00am): Mid-morning. Market's been open a bit (on weekdays).
SLOT 3 (12:30pm): Midday. Quick check-in energy.
SLOT 4 (3:30pm): Power hour on trading days. Peak energy. Or afternoon reflection on weekends.
SLOT 5 (6:00pm): End of day. Reflecting, wrapping up.

RULES:
1. Each tweet MUST be under 280 characters
2. Mix it up - not every tweet needs a link or CTA
3. Reference REAL data - don't invent tickers or percentages
4. 2-3 tweets should include the newsletter URL
5. Some tweets can be short observations or questions
6. Show personality, not just information
7. It's okay to have a tweet that's just a quick thought

VARIETY REQUIREMENTS:
- At least one tweet about scanner/signals (if you have them)
- At least one engagement element (question, observation)
- At least one that shows your personality/voice
- NOT all tweets should be promotional
- Mix: some with links, some without
- Do NOT mention portfolio stats (positions count, vs SPY %) more than once today
- Avoid cliffhanger tweets that promise "more details" without giving substance
"""


def build_generation_prompt(
    persona: Persona,
    persona_key: str,
    market_ctx: MarketContext,
    day_ctx: DayContext,
    examples: dict,
    tracker: Optional[ContentTracker] = None,
    account_id: str = 'main',
) -> str:
    """Build the complete generation prompt."""

    # Anti-repetition section
    anti_repetition = ""
    if tracker:
        avoidance = tracker.get_avoidance_guidance(account_id, persona.name)

        anti_repetition = f"""
## AVOIDANCE RULES (CRITICAL — WILL BE ENFORCED)

{avoidance}

- Mention each winning position MAX 2 times across the whole week, not daily
- Portfolio stats (number of positions, vs SPY percentage) MAX 3 times this week
- Scan count ("1,800 stocks") MAX 2 times this week
- Each day needs DIFFERENT content angles, not the same stats repackaged
- Do NOT write cliffhanger tweets that promise content without delivering it
"""

    return f"""You are {persona.name}, writing your tweets for {day_ctx.day_name}.

{build_persona_section(persona)}

{build_market_section(market_ctx)}

{build_day_section(day_ctx, persona)}

{anti_repetition}

{build_examples_section(persona_key, examples, market_ctx)}

{build_slot_guidance()}

## OUTPUT FORMAT

Return ONLY a JSON array with exactly 5 tweets:

```json
[
  {{"slot": 1, "text": "Your morning tweet here...", "has_url": false}},
  {{"slot": 2, "text": "Your 10am tweet here...", "has_url": true}},
  {{"slot": 3, "text": "Your midday tweet here...", "has_url": false}},
  {{"slot": 4, "text": "Your power hour/afternoon tweet...", "has_url": false}},
  {{"slot": 5, "text": "Your evening tweet here...", "has_url": true}}
]
```

Remember: You're a real person, not a brand. Write like you actually would.

Newsletter URL (when including): {NEWSLETTER_URL}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_day_tweets(
    client: anthropic.Anthropic,
    persona: Persona,
    persona_key: str,
    market_ctx: MarketContext,
    day_ctx: DayContext,
    examples: dict,
    account_id: str,
    tracker: Optional[ContentTracker] = None
) -> List[GeneratedTweet]:
    """Generate all tweets for one account for one day."""

    prompt = build_generation_prompt(persona, persona_key, market_ctx, day_ctx, examples, tracker, account_id)
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        
        response_text = response.content[0].text.strip()
        
        # Parse JSON from response
        tweets_raw = parse_json_response(response_text)
        
        # Convert to GeneratedTweet objects
        tweets = []
        scan_date = datetime.strptime(market_ctx.scan_date, '%Y-%m-%d')
        day_offset = DAYS.index(day_ctx.day_name)
        tweet_date = scan_date + timedelta(days=day_offset)
        
        for raw in tweets_raw:
            slot = raw.get('slot', 1)
            text = raw.get('text', '')
            
            tweets.append(GeneratedTweet(
                id=f"{day_ctx.day_name.lower()}_{slot}_{account_id}",
                day=day_ctx.day_name,
                slot=slot,
                time=SLOTS.get(slot, {}).get('time', '12:00'),
                text=text,
                category=infer_category(text),
                account=account_id,
                persona_name=persona.name,
                mentioned_tickers=extract_tickers(text),
                has_url=NEWSLETTER_URL in text or 'substack' in text.lower(),
                char_count=len(text),
            ))
        
        return tweets
        
    except Exception as e:
        print(f"  ❌ Generation failed for {account_id} {day_ctx.day_name}: {e}")
        return generate_fallback_tweets(persona, day_ctx, account_id)


def parse_json_response(text: str) -> List[dict]:
    """Parse JSON from Claude's response."""
    
    # Try to extract JSON from markdown code blocks
    if '```json' in text:
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            text = match.group(1)
    elif '```' in text:
        match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if match:
            text = match.group(1)
    
    # Try to find array
    if '[' in text:
        start = text.index('[')
        end = text.rindex(']') + 1
        text = text[start:end]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error: {e}")
        return []


def extract_tickers(text: str) -> List[str]:
    """Extract $TICKER mentions from text."""
    return re.findall(r'\$([A-Z]{1,5})', text)


def infer_category(text: str) -> str:
    """Infer content category from tweet text."""
    
    text_lower = text.lower()
    
    if any(w in text_lower for w in ['power hour', '3:30', '3:45', 'final hour', 'into the close']):
        return 'power_hour'
    
    if any(w in text_lower for w in ['scanner', 'scan', 'gates', 'cleared', 'passed']):
        return 'scanner_result'
    
    if any(w in text_lower for w in ['up', '+', 'gain', 'winner', 'closed for']):
        if re.search(r'\+?\d+%', text):
            return 'performance'
    
    if any(w in text_lower for w in ['watching', 'eyes on', 'radar', 'consider']):
        return 'watchlist'
    
    if any(w in text_lower for w in ['lesson', 'learn', 'mistake', 'wish', 'tip']):
        return 'educational'
    
    if '?' in text:
        return 'engagement'
    
    if any(w in text_lower for w in ['newsletter', 'breakdown', 'substack']):
        return 'newsletter_promo'
    
    return 'observation'


def generate_fallback_tweets(persona: Persona, day_ctx: DayContext, account_id: str) -> List[GeneratedTweet]:
    """Generate simple fallback tweets if Claude fails."""
    
    fallbacks = [
        f"Another {day_ctx.day_name}. Let's see what the market brings.",
        f"Watching the tape. Some days are quiet. That's fine.",
        f"The system keeps running. Patience is part of the process.",
        f"Markets are markets. We adapt and move forward.",
        f"Scan complete. More details in the newsletter: {NEWSLETTER_URL}",
    ]
    
    tweets = []
    for i, text in enumerate(fallbacks, 1):
        tweets.append(GeneratedTweet(
            id=f"{day_ctx.day_name.lower()}_{i}_{account_id}",
            day=day_ctx.day_name,
            slot=i,
            time=SLOTS.get(i, {}).get('time', '12:00'),
            text=text,
            category='fallback',
            account=account_id,
            persona_name=persona.name,
            generation_method='fallback',
            char_count=len(text),
        ))
    
    return tweets


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_tweet(tweet: GeneratedTweet, persona: Persona, all_tickers: Set[str]) -> List[str]:
    """Validate a single tweet. Returns list of issues."""
    
    issues = []
    
    # Length check
    if tweet.char_count > 280:
        issues.append(f"Too long: {tweet.char_count} chars")
    
    # Check for wrong persona phrases
    voice = persona.voice
    never_use = voice.get('vocabulary', {}).get('never_uses', [])
    
    text_lower = tweet.text.lower()
    for phrase in never_use:
        if phrase.lower() in text_lower:
            issues.append(f"Uses forbidden phrase: '{phrase}'")
    
    # Check for hallucinated tickers
    for ticker in tweet.mentioned_tickers:
        if ticker not in all_tickers and ticker not in ['SPY', 'QQQ', 'VIX']:
            issues.append(f"Unknown ticker: ${ticker}")
    
    # Check for robotic patterns
    robotic = ['systematic analysis', 'algorithmic', 'data drives decisions', 'execute', 'protocol']
    for pattern in robotic:
        if pattern in text_lower:
            issues.append(f"Robotic language: '{pattern}'")
    
    return issues


def validate_day_tweets(tweets: List[GeneratedTweet], persona: Persona, market_ctx: MarketContext) -> Dict[str, List[str]]:
    """Validate all tweets for a day."""
    
    # Build set of valid tickers
    valid_tickers = set()
    for sig in market_ctx.green_signals + market_ctx.consider_signals:
        valid_tickers.add(sig.get('ticker', ''))
    for pos in market_ctx.open_positions:
        valid_tickers.add(pos.get('ticker', ''))
    
    issues_by_slot = {}
    
    for tweet in tweets:
        slot_issues = validate_tweet(tweet, persona, valid_tickers)
        if slot_issues:
            issues_by_slot[f"slot_{tweet.slot}"] = slot_issues
    
    # Check for duplicate content
    texts = [t.text.lower()[:50] for t in tweets]
    if len(texts) != len(set(texts)):
        issues_by_slot['duplicates'] = ['Duplicate or very similar tweets detected']
    
    # Check URL distribution
    url_count = sum(1 for t in tweets if t.has_url)
    if url_count < 2:
        issues_by_slot['urls'] = [f'Only {url_count} tweets have URL (should be 2-3)']
    elif url_count > 4:
        issues_by_slot['urls'] = [f'{url_count} tweets have URL (too many, feels spammy)']
    
    return issues_by_slot


def deduplicate_weekly_content(all_content: Dict[str, List[dict]], market_ctx: MarketContext) -> Dict[str, List[dict]]:
    """Check and flag repetitive content across the week."""

    # Collect all valid tickers from market context
    all_tickers = set()
    for sig in market_ctx.green_signals + market_ctx.consider_signals:
        all_tickers.add(sig.get('ticker', '').upper())
    for pos in market_ctx.open_positions:
        all_tickers.add(pos.get('ticker', '').upper())

    for account_id, tweets in all_content.items():
        ticker_mentions = {}
        portfolio_stat_days = set()

        for tweet in tweets:
            text = tweet['text']
            day = tweet['day']

            # Track ticker mentions
            for ticker in all_tickers:
                if f'${ticker}' in text.upper() or f' {ticker} ' in text.upper():
                    ticker_mentions[ticker] = ticker_mentions.get(ticker, 0) + 1

                    if ticker_mentions[ticker] > 3:
                        tweet['_flagged'] = f'{ticker} mentioned {ticker_mentions[ticker]}x'

            # Track portfolio stats repetition
            text_lower = text.lower()
            if any(p in text_lower for p in ['positions', 'vs spy', 'beating spy',
                                              'green,', 'in the green', 'in the red']):
                if day in portfolio_stat_days:
                    tweet['_flagged'] = 'Portfolio stats repeated same day'
                portfolio_stat_days.add(day)

        # Check phrase limits
        persona_key = {'main': 'alex', 'account2': 'rozalia', 'account3': 'james'}.get(account_id, 'alex')
        # Map to PHRASE_LIMITS keys
        limits_key = {'main': 'alex', 'account2': 'rozalia', 'account3': 'james'}.get(account_id, 'alex')
        limits = PHRASE_LIMITS.get(limits_key, {})

        phrase_counts = {}
        for tweet in tweets:
            text_lower = tweet['text'].lower()
            for phrase, max_count in limits.items():
                if phrase in text_lower:
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
                    if phrase_counts[phrase] > max_count:
                        tweet['_flagged'] = f'Phrase "{phrase}" used {phrase_counts[phrase]}x (max {max_count})'

        # Report
        flagged = [t for t in tweets if '_flagged' in t]
        if flagged:
            print(f"  📋 {account_id}: {len(flagged)} tweets flagged for repetition")
            for t in flagged[:3]:
                print(f"      {t['day']} slot {t['slot']}: {t['_flagged']}")

    return all_content


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION FLOW
# ═══════════════════════════════════════════════════════════════════════════════

def generate_weekly_content(
    scanner_data: dict,
    portfolio_data: dict,
    output_dir: Optional[Path] = None,
    accounts_to_generate: Optional[List[str]] = None
) -> Dict[str, List[dict]]:
    """
    Generate a full week of content for all accounts.
    
    Args:
        scanner_data: Output from scanner
        portfolio_data: Output from portfolio manager
        output_dir: Where to save content queues
        accounts_to_generate: Specific accounts to generate (default: all)
    
    Returns:
        Dict mapping account_id to list of tweet dicts
    """
    
    print("\n🎯 Reaction-Based Tweet Generator")
    print("=" * 50)
    
    # Initialize
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    examples = load_examples()
    market_ctx = create_market_context(scanner_data, portfolio_data)
    
    # Status
    print(f"📅 Scan date: {market_ctx.scan_date}")
    print(f"📊 Signals: {market_ctx.signal_count} GREEN, {len(market_ctx.consider_signals)} CONSIDER")
    print(f"💼 Positions: {market_ctx.total_positions} open ({market_ctx.green_count} green)")
    if market_ctx.has_big_winner:
        print(f"🏆 Big winners: {len(market_ctx.winners)}")
    if market_ctx.is_quiet_week:
        print("📭 Quiet week - no new signals")
    
    accounts = accounts_to_generate or list(ACCOUNTS.keys())
    all_content = {}
    
    for account_id in accounts:
        account_config = ACCOUNTS.get(account_id)
        if not account_config:
            print(f"  ⚠️ Unknown account: {account_id}")
            continue
        
        # Load persona
        persona = load_persona(account_config['persona_file'])
        persona_key = account_config['examples_key']
        
        print(f"\n👤 Generating for {persona.name} ({account_id})...")

        account_tweets = []
        tracker = ContentTracker()

        for day_name in DAYS:
            day_ctx = create_day_context(day_name, market_ctx.scan_date)

            print(f"  📝 {day_name}...", end=' ')

            tweets = generate_day_tweets(
                client=client,
                persona=persona,
                persona_key=persona_key,
                market_ctx=market_ctx,
                day_ctx=day_ctx,
                examples=examples,
                account_id=account_id,
                tracker=tracker
            )

            # Record what was generated for next day's anti-repetition
            for tweet in tweets:
                tracker.record_tweet(tweet.text, account_id, persona.name)

            # Validate
            issues = validate_day_tweets(tweets, persona, market_ctx)
            if issues:
                print(f"⚠️ {len(issues)} issues")
                for slot, slot_issues in issues.items():
                    for issue in slot_issues[:2]:
                        print(f"      {slot}: {issue}")
            else:
                print("✅")

            account_tweets.extend(tweets)
        
        # Convert to dict format for saving
        all_content[account_id] = [
            {
                'id': t.id,
                'day': t.day,
                'slot': t.slot,
                'time': t.time,
                'text': t.text,
                'category': t.category,
                'account': t.account,
                'persona': t.persona_name,
                'scheduled_date': calculate_scheduled_date(market_ctx.scan_date, t.day),
                'status': 'pending',
                'generation_method': t.generation_method,
                'char_count': t.char_count,
            }
            for t in account_tweets
        ]
        
        print(f"  ✅ Generated {len(account_tweets)} tweets")
    
    # Post-generation deduplication check
    all_content = deduplicate_weekly_content(all_content, market_ctx)

    # Post-generation temporal fix: replace "yesterday" on wrong days
    for account_id, tweets in all_content.items():
        for tweet in tweets:
            day = tweet['day']
            temporal = get_temporal_reference(day)
            avoid = temporal.get('avoid', [])
            text = tweet['text']
            for bad_word in avoid:
                if bad_word.lower() in text.lower():
                    replacement = temporal.get('for_friday_data', 'the scan')
                    # Case-insensitive replace
                    text = re.sub(re.escape(bad_word), replacement, text, flags=re.IGNORECASE)
                    tweet['text'] = text
                    tweet['char_count'] = len(text)

    # Save if output dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for account_id, tweets in all_content.items():
            queue_file = ACCOUNTS[account_id]['queue_file']
            output_path = output_dir / queue_file
            
            with open(output_path, 'w') as f:
                json.dump(tweets, f, indent=2)
            
            print(f"💾 Saved {len(tweets)} tweets to {output_path}")
    
    print(f"\n✅ Generation complete: {sum(len(t) for t in all_content.values())} total tweets")
    
    return all_content


def calculate_scheduled_date(scan_date: str, day_name: str) -> str:
    """Calculate the scheduled date for a tweet."""
    base = datetime.strptime(scan_date, '%Y-%m-%d')
    offset = DAYS.index(day_name)
    return (base + timedelta(days=offset)).strftime('%Y-%m-%d')


# ═══════════════════════════════════════════════════════════════════════════════
# EDITORIAL BOARD FLOW (V2)
# ═══════════════════════════════════════════════════════════════════════════════

PERSONA_NAME_MAP = {'main': 'Alex', 'account2': 'Rozalia', 'account3': 'James'}


def build_assigned_prompt(
    persona: Persona,
    persona_key: str,
    day_ctx: DayContext,
    market_ctx: MarketContext,
    assignments: dict,
    examples: dict,
    avoidance_guidance: str = "",
) -> str:
    """Build a writer prompt constrained by editorial assignments."""

    # Format per-slot instructions
    slot_instructions = ""
    for slot_num in range(1, 6):
        slot_key = f'slot_{slot_num}'
        assignment = assignments.get(slot_key, {})
        category = assignment.get('category', 'observation')
        topic = assignment.get('topic', 'Write naturally')
        tickers = assignment.get('tickers', [])
        include_url = assignment.get('include_url', False)

        ticker_note = f" Mention: {', '.join(f'${t}' for t in tickers)}." if tickers else " No specific ticker required."
        url_note = f" Include newsletter URL: {NEWSLETTER_URL}" if include_url else " No URL needed."

        slot_instructions += f"""
SLOT {slot_num} ({SLOTS[slot_num]['time']}):
  Category: {category}
  Assignment: {topic}
 {ticker_note}{url_note}
"""

    temporal = day_ctx.temporal
    temporal_note = ""
    avoid = temporal.get('avoid', [])
    if avoid:
        temporal_note = f"\nTEMPORAL: When referencing Friday data, say \"{temporal.get('for_friday_data', 'the scan')}\". NEVER say: {', '.join(f'\"{a}\"' for a in avoid)}."

    return f"""You are {persona.name}, writing your 5 tweets for {day_ctx.day_name}.

{build_persona_section(persona)}

{build_examples_section(persona_key, examples, market_ctx)}

## YOUR ASSIGNMENTS FROM THE EDITORIAL BOARD

The Managing Editor has planned today's content. Follow these assignments:

{slot_instructions}

## MARKET DATA (reference as needed)

{build_market_section(market_ctx)}
{temporal_note}

{f'''## AVOIDANCE RULES (CRITICAL — WILL BE ENFORCED)
{avoidance_guidance}
''' if avoidance_guidance else ''}
## RULES
1. Each tweet MUST be under 280 characters
2. Follow the assigned category and topic for each slot
3. Only mention tickers listed in the assignment (or none if not listed)
4. Show YOUR personality — you're a real person, not a brand
5. Do NOT write cliffhanger tweets that promise content without delivering
6. Do NOT mention portfolio stats (positions count, vs SPY %) unless your assignment is specifically about performance
7. Scan count ("1,800 stocks") MAX 2 times total this week — skip if already used
8. Specific winner P&L percentages MAX 2 times total this week

## OUTPUT FORMAT

Return ONLY a JSON array with exactly 5 tweets:

```json
[
  {{"slot": 1, "text": "...", "has_url": false}},
  {{"slot": 2, "text": "...", "has_url": true}},
  {{"slot": 3, "text": "...", "has_url": false}},
  {{"slot": 4, "text": "...", "has_url": false}},
  {{"slot": 5, "text": "...", "has_url": true}}
]
```

Newsletter URL (when assigned): {NEWSLETTER_URL}
"""


def generate_day_tweets_with_board(
    client,
    persona: Persona,
    persona_key: str,
    market_ctx: MarketContext,
    day_ctx: DayContext,
    examples: dict,
    account_id: str,
    editorial_assignments: dict,
    tracker: Optional[ContentTracker] = None,
) -> List[GeneratedTweet]:
    """Generate tweets for one account for one day, guided by editorial assignments."""

    persona_name = PERSONA_NAME_MAP.get(account_id, 'Alex')
    assignments = editorial_assignments.get(persona_name, {})

    avoidance = ""
    if tracker:
        avoidance = tracker.get_avoidance_guidance(account_id, persona_name)

    prompt = build_assigned_prompt(
        persona=persona,
        persona_key=persona_key,
        day_ctx=day_ctx,
        market_ctx=market_ctx,
        assignments=assignments,
        examples=examples,
        avoidance_guidance=avoidance,
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()
        tweets_raw = parse_json_response(response_text)

        tweets = []
        scan_date = datetime.strptime(market_ctx.scan_date, '%Y-%m-%d')
        day_offset = DAYS.index(day_ctx.day_name)
        tweet_date = scan_date + timedelta(days=day_offset)

        for raw in tweets_raw:
            slot = raw.get('slot', 1)
            text = raw.get('text', '')

            # Use category from editorial assignment if available
            slot_key = f'slot_{slot}'
            assigned_category = assignments.get(slot_key, {}).get('category', infer_category(text))

            tweets.append(GeneratedTweet(
                id=f"{day_ctx.day_name.lower()}_{slot}_{account_id}",
                day=day_ctx.day_name,
                slot=slot,
                time=SLOTS.get(slot, {}).get('time', '12:00'),
                text=text,
                category=assigned_category,
                account=account_id,
                persona_name=persona.name,
                mentioned_tickers=extract_tickers(text),
                has_url=NEWSLETTER_URL in text or 'substack' in text.lower(),
                char_count=len(text),
            ))

        return tweets

    except Exception as e:
        print(f"  ❌ Writer failed for {persona.name}: {e}")
        return generate_fallback_tweets(persona, day_ctx, account_id)


def regenerate_single_tweet(client, tweet: dict, avoid_items: dict, persona: Persona) -> str:
    """Generate a replacement tweet that avoids problematic content."""
    avoid_tickers = ', '.join(f'${t}' for t in avoid_items.get('tickers', []))
    avoid_phrases = ', '.join(f'"{p}"' for p in avoid_items.get('phrases', []))
    avoid_facts = ', '.join(avoid_items.get('facts', []))

    prompt = f"""You are {persona.name}. Write a REPLACEMENT tweet for this slot.

ORIGINAL TWEET (DO NOT REUSE — it had repetition issues):
{tweet['text']}

DAY: {tweet['day']}
TIME SLOT: {tweet['slot']} ({tweet['time']})
CATEGORY: {tweet['category']}

CRITICAL CONSTRAINTS:
{f'- DO NOT mention these tickers: {avoid_tickers}' if avoid_tickers else ''}
{f'- DO NOT use these phrases: {avoid_phrases}' if avoid_phrases else ''}
{f'- DO NOT repeat these facts: {avoid_facts}' if avoid_facts else ''}
- Find a COMPLETELY DIFFERENT angle for the same category
- Stay in character as {persona.name}
- Keep under 260 characters
- Do NOT write cliffhanger tweets

ALTERNATIVE ANGLES: Process/discipline, general market observation (no tickers), engagement question, educational concept, theme analysis without naming stocks.

Write ONLY the tweet text, nothing else."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().strip('"')


def extract_avoid_from_flag(flag_reason: str) -> dict:
    """Parse flag reason to determine what to avoid."""
    avoid = {'tickers': [], 'phrases': [], 'facts': []}

    ticker_match = re.search(r'(\w+) mentioned \d+x', flag_reason)
    if ticker_match:
        avoid['tickers'].append(ticker_match.group(1))

    phrase_match = re.search(r'Phrase "([^"]+)" used \d+x', flag_reason)
    if phrase_match:
        avoid['phrases'].append(phrase_match.group(1))

    if 'Scan count' in flag_reason:
        avoid['facts'].append('scan count (1,800 stocks)')
    if 'Portfolio status' in flag_reason:
        avoid['facts'].append('portfolio status (X green, Y red)')
    if 'SPY comparison' in flag_reason:
        avoid['facts'].append('SPY comparison percentage')

    return avoid


def regenerate_flagged_tweets(
    client,
    all_content: Dict[str, List[dict]],
    tracker: ContentTracker,
    personas: Dict[str, Persona],
) -> Dict[str, List[dict]]:
    """Find all flagged tweets and regenerate them."""
    MAX_REGEN_ATTEMPTS = 3
    regen_count = 0
    fail_count = 0

    for account_id, tweets in all_content.items():
        persona = personas.get(account_id)
        if not persona:
            continue

        for i, tweet in enumerate(tweets):
            if '_flagged' not in tweet:
                continue

            flag_reason = tweet['_flagged']
            avoid_items = extract_avoid_from_flag(flag_reason)

            for attempt in range(MAX_REGEN_ATTEMPTS):
                new_text = regenerate_single_tweet(client, tweet, avoid_items, persona)

                # Check the new tweet against tracker
                violations = tracker.check_tweet(new_text, account_id, persona.name)

                if not violations and len(new_text) <= 280:
                    tweet['text'] = new_text
                    tweet['char_count'] = len(new_text)
                    tweet['generation_method'] = 'reaction_regenerated'
                    del tweet['_flagged']
                    regen_count += 1
                    break
                else:
                    # Widen avoidance on retry
                    for v in violations:
                        tm = re.search(r'(\w+) mentioned', v)
                        if tm:
                            avoid_items['tickers'].append(tm.group(1))
                        pm = re.search(r'Phrase "([^"]+)"', v)
                        if pm:
                            avoid_items['phrases'].append(pm.group(1))
            else:
                fail_count += 1

    print(f"  Regenerated: {regen_count} | Could not fix: {fail_count}")
    return all_content


def generate_weekly_content_v2(
    scanner_data: dict,
    portfolio_data: dict,
    output_dir: Optional[Path] = None,
    accounts_to_generate: Optional[List[str]] = None,
) -> Dict[str, List[dict]]:
    """
    Two-stage generation with content tracking and regeneration.

    Stage 1: Morning Briefing (data summary)
    Stage 2: Editorial Board (plans all 15 slots per day)
    Stage 3: Writer Room (each persona writes their 5 tweets)
    Stage 4: Flag violations via ContentTracker
    Stage 5: Regenerate flagged tweets
    Stage 6: Temporal fix + save
    """

    print("\n🎯 Editorial Board Tweet Generator (v2)")
    print("=" * 50)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    examples = load_examples()
    market_ctx = create_market_context(scanner_data, portfolio_data)

    print(f"📅 Scan date: {market_ctx.scan_date}")
    print(f"📊 Signals: {market_ctx.signal_count} GREEN, {len(market_ctx.consider_signals)} CONSIDER")
    print(f"💼 Positions: {market_ctx.total_positions} open ({market_ctx.green_count} green)")
    if market_ctx.has_big_winner:
        print(f"🏆 Big winners: {len(market_ctx.winners)}")

    accounts = accounts_to_generate or list(ACCOUNTS.keys())
    all_content = {acct: [] for acct in accounts}

    # Global content tracker — enforces limits across ALL days and accounts
    tracker = ContentTracker()
    # Week-level tracker for editorial board briefings
    week_tracker = {'tickers_featured': {}}
    # Cache personas for regeneration
    personas_cache = {}

    for day_name in DAYS:
        print(f"\n📅 {day_name}")
        tracker.days_generated += 1

        # STAGE 1: Morning Briefing
        briefing = generate_morning_briefing(
            scanner_data, portfolio_data, day_name, week_tracker
        )

        # STAGE 2: Editorial Board
        print("  📋 Editorial Board planning...", end=' ')
        editorial_plan = create_editorial_plan(
            client, briefing, day_name, market_ctx, week_tracker
        )

        # Validate the plan
        plan_issues = validate_editorial_plan(editorial_plan)
        if plan_issues:
            print(f"⚠️ {len(plan_issues)} issues")
            for issue in plan_issues[:3]:
                print(f"      {issue}")
        else:
            print("✅")

        # STAGE 3: Writer Room — each persona writes their tweets
        day_ctx = create_day_context(day_name, market_ctx.scan_date)

        for account_id in accounts:
            account_config = ACCOUNTS.get(account_id)
            if not account_config:
                continue

            persona = load_persona(account_config['persona_file'])
            personas_cache[account_id] = persona
            persona_key = account_config['examples_key']

            print(f"  ✍️  {persona.name}...", end=' ')

            tweets = generate_day_tweets_with_board(
                client=client,
                persona=persona,
                persona_key=persona_key,
                market_ctx=market_ctx,
                day_ctx=day_ctx,
                examples=examples,
                account_id=account_id,
                editorial_assignments=editorial_plan,
                tracker=tracker,
            )

            # Validate
            issues = validate_day_tweets(tweets, persona, market_ctx)
            if issues:
                print(f"⚠️ {len(issues)} issues")
                for slot, slot_issues in issues.items():
                    for issue in slot_issues[:2]:
                        print(f"        {slot}: {issue}")
            else:
                print("✅")

            # Convert to dict, record in tracker, and append
            for t in tweets:
                # Find chart for first ticker mentioned
                image_path = None
                for ticker in t.mentioned_tickers:
                    if ticker in market_ctx.chart_manifest:
                        image_path = market_ctx.chart_manifest[ticker]
                        break

                tweet_dict = {
                    'id': t.id,
                    'day': t.day,
                    'slot': t.slot,
                    'time': t.time,
                    'text': t.text,
                    'category': t.category,
                    'account': t.account,
                    'persona': t.persona_name,
                    'scheduled_date': calculate_scheduled_date(market_ctx.scan_date, t.day),
                    'status': 'pending',
                    'generation_method': t.generation_method,
                    'char_count': t.char_count,
                }

                # Add image_path if available and category is appropriate
                if image_path and t.category in ['scanner_result', 'performance', 'theme_analysis']:
                    tweet_dict['image_path'] = image_path

                # Record in tracker IMMEDIATELY
                tracker.record_tweet(t.text, account_id, persona.name)

                # Check for violations
                violations = tracker.check_tweet(t.text, account_id, persona.name)
                if violations:
                    tweet_dict['_flagged'] = violations[0]

                all_content[account_id].append(tweet_dict)

        # Update week tracker for editorial board briefings
        for account_id in accounts:
            day_tweets = [t for t in all_content[account_id] if t['day'] == day_name]
            for tweet in day_tweets:
                for ticker in extract_tickers(tweet['text']):
                    week_tracker['tickers_featured'][ticker] = \
                        week_tracker['tickers_featured'].get(ticker, 0) + 1

    # STAGE 4: Report flagged tweets
    total_flagged = sum(1 for tweets in all_content.values() for t in tweets if '_flagged' in t)
    if total_flagged:
        print(f"\n🔄 Regeneration Pass: {total_flagged} tweets flagged")
        all_content = regenerate_flagged_tweets(client, all_content, tracker, personas_cache)
    else:
        print("\n✅ No flagged tweets — all within limits")

    # STAGE 5: Temporal fix
    for account_id, tweets in all_content.items():
        for tweet in tweets:
            day = tweet['day']
            temporal = get_temporal_reference(day)
            avoid = temporal.get('avoid', [])
            text = tweet['text']
            for bad_word in avoid:
                if bad_word.lower() in text.lower():
                    replacement = temporal.get('for_friday_data', 'the scan')
                    text = re.sub(re.escape(bad_word), replacement, text, flags=re.IGNORECASE)
                    tweet['text'] = text
                    tweet['char_count'] = len(text)

    # STAGE 6: Strip _flagged from any remaining (unfixable) tweets before saving
    for account_id, tweets in all_content.items():
        for tweet in tweets:
            tweet.pop('_flagged', None)

    # Save
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for account_id, tweets in all_content.items():
            queue_file = ACCOUNTS[account_id]['queue_file']
            output_path = output_dir / queue_file

            with open(output_path, 'w') as f:
                json.dump(tweets, f, indent=2)

            print(f"💾 Saved {len(tweets)} tweets to {output_path}")

    total = sum(len(t) for t in all_content.values())
    print(f"\n✅ Generation complete: {total} total tweets")

    return all_content


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Reaction-based tweet generator')
    parser.add_argument('--scanner-file', type=str, help='Path to scanner JSON')
    parser.add_argument('--portfolio-file', type=str, help='Path to portfolio JSON')
    parser.add_argument('--output', type=str, default='trades', help='Output directory')
    parser.add_argument('--account', type=str, help='Generate for specific account only')
    parser.add_argument('--mock', action='store_true', help='Use mock data')
    
    args = parser.parse_args()
    
    # Load or mock data
    if args.mock:
        scanner_data = {
            'scan_date': datetime.now().strftime('%Y-%m-%d'),
            'pass_signals': [
                {'ticker': 'AMPX', 'close_price': 12.44, 'theme': 'AI Infrastructure'},
                {'ticker': 'LUMN', 'close_price': 8.92, 'theme': 'Data Centers'},
            ],
            'consider_signals': [
                {'ticker': 'PUMP', 'close_price': 11.49, 'theme': 'Energy'},
            ],
            'prime_themes': [{'name': 'AI Power Infrastructure'}],
            'investable_themes': [{'name': 'Data Centers'}],
        }
        portfolio_data = {
            'positions': [
                {'ticker': 'NVDA', 'pnl_pct': 32.5, 'days_held': 45, 'entry_price': 450},
                {'ticker': 'AMD', 'pnl_pct': 15.2, 'days_held': 30},
                {'ticker': 'AMPX', 'pnl_pct': 8.5, 'days_held': 7, 'entry_price': 11.47},
                {'ticker': 'INTC', 'pnl_pct': -5.2, 'days_held': 14},
            ],
            'closed_trades': [
                {'ticker': 'TSLA', 'pnl_pct': 23.5, 'days_held': 28},
            ],
            'vs_spy': 12.5,
        }
    else:
        if args.scanner_file:
            with open(args.scanner_file) as f:
                scanner_data = json.load(f)
        else:
            print("Error: --scanner-file required (or use --mock)")
            return
        
        if args.portfolio_file:
            with open(args.portfolio_file) as f:
                portfolio_data = json.load(f)
        else:
            portfolio_data = {'positions': [], 'closed_trades': [], 'vs_spy': 0}
    
    accounts = [args.account] if args.account else None
    
    generate_weekly_content_v2(
        scanner_data=scanner_data,
        portfolio_data=portfolio_data,
        output_dir=Path(args.output),
        accounts_to_generate=accounts
    )


if __name__ == '__main__':
    main()
