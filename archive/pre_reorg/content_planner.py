#!/usr/bin/env python3
"""
CONTENT_PLANNER.PY - Persona-Based Content Generation System
=============================================================

This module replaces the template-first approach with a data-first,
persona-aware content generation system.

Core Concepts:
1. ContentPlanner - Analyzes scanner data, determines what's available
2. ContentBrief - Instructions for generating one account's content
3. PersonaGenerator - Claude-based generation with persona context
4. CrossAccountValidator - Ensures differentiation across accounts

Usage:
    from content_planner import ContentPlanner
    
    planner = ContentPlanner(scanner_data, portfolio_data)
    briefs = planner.create_all_briefs()
    
    for account_id, brief in briefs.items():
        tweets = PersonaGenerator(brief).generate()
        save_to_queue(account_id, tweets)

Integration:
    This module integrates with existing tweet_generator.py and can be
    adopted incrementally. See MIGRATION_PATH at end of file.
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from pathlib import Path
from enum import Enum
import anthropic

# Import from existing config
from config import (
    MODEL_SONNET, MODEL_TWEET,
    TWITTER_ACCOUNTS, SLOTS, SLOT_TIMES_ET,
    MARKETING_THRESHOLDS, SAFEGUARDED_CATEGORIES,
    SIGNAL_COLORS, BRANDING,
    CELEBRATION_THRESHOLDS, CELEBRATION_KEYS,
    TWEETS_PER_DAY, TWEETS_PER_WEEK,
    can_show_entry_price, contains_banned_term,
    get_highlight_threshold, format_holding_period,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PersonaVoice:
    """Voice characteristics for a persona."""
    tone: str                    # 'authoritative', 'conversational', 'direct'
    formality: str               # 'professional', 'approachable', 'casual'
    traits: List[str]            # ['data-driven', 'precise', 'confident']
    avoid: List[str]             # Things this persona wouldn't say


@dataclass
class Persona:
    """Complete persona definition for an account."""
    name: str                    # 'The System', 'The Mentor', 'The Trader'
    account_id: str              # 'main', 'account2', 'account3'
    archetype: str               # 'Analyst', 'Teacher', 'Practitioner'
    voice: PersonaVoice
    focus_areas: Dict[str, List[str]]  # primary, secondary, tertiary
    content_mix: Dict[str, float]      # category -> percentage
    signature_phrases: List[str]
    post_timing: str             # 'market_aligned', 'educational_hours', etc.


# Pre-defined personas
PERSONAS: Dict[str, Persona] = {
    'main': Persona(
        name='The System',
        account_id='main',
        archetype='Analyst',
        voice=PersonaVoice(
            tone='authoritative',
            formality='professional',
            traits=['data-driven', 'precise', 'confident', 'systematic'],
            avoid=['slang', 'excessive emojis', 'hype language', 'FOMO appeals'],
        ),
        focus_areas={
            'primary': ['signal_announcements', 'scanner_results', 'system_performance'],
            'secondary': ['funnel_stats', 'process_explanation', 'theme_analysis'],
            'tertiary': ['educational', 'engagement'],
        },
        content_mix={
            'signals': 0.45,
            'educational': 0.25,
            'engagement': 0.15,
            'themes': 0.15,
        },
        signature_phrases=[
            "The scanner doesn't lie.",
            "Data drives decisions.",
            "That's the 5-Gate System in action.",
            "Quality over quantity. Always.",
            "The gates filtered this week's noise.",
        ],
        post_timing='market_aligned',
    ),
    
    'account2': Persona(
        name='The Mentor',
        account_id='account2',
        archetype='Teacher',
        voice=PersonaVoice(
            tone='conversational',
            formality='approachable',
            traits=['helpful', 'patient', 'encouraging', 'explanatory'],
            avoid=['jargon without explanation', 'condescension', 'rushed language'],
        ),
        focus_areas={
            'primary': ['educational', 'process_explanation', 'trading_psychology'],
            'secondary': ['watchlist_context', 'theme_breakdown', 'risk_education'],
            'tertiary': ['signals', 'engagement'],
        },
        content_mix={
            'educational': 0.40,
            'signals': 0.25,
            'engagement': 0.20,
            'themes': 0.15,
        },
        signature_phrases=[
            "Here's why this matters...",
            "Let me break this down.",
            "The lesson here:",
            "Most traders miss this.",
            "Think about it this way:",
        ],
        post_timing='educational_hours',
    ),
    
    'account3': Persona(
        name='The Trader',
        account_id='account3',
        archetype='Practitioner',
        voice=PersonaVoice(
            tone='direct',
            formality='casual',
            traits=['action-oriented', 'confident', 'punchy', 'real-time'],
            avoid=['excessive hedging', 'overly formal language', 'lengthy explanations'],
        ),
        focus_areas={
            'primary': ['real_time_market_color', 'power_hour', 'theme_momentum'],
            'secondary': ['signals', 'watchlist', 'early_movers'],
            'tertiary': ['educational'],
        },
        content_mix={
            'signals': 0.35,
            'market_color': 0.25,
            'engagement': 0.25,
            'educational': 0.15,
        },
        signature_phrases=[
            "Eyes on this one.",
            "The close matters.",
            "Momentum is real.",
            "Let's see how this plays out.",
            "Watch the tape.",
        ],
        post_timing='market_hours_heavy',
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DAY-AWARE CONTENT RULES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DayRules:
    """Content rules for a specific day of the week."""
    day: str
    context: str                 # What's happening this day
    allowed_phrases: List[str]   # OK to use
    blocked_phrases: List[str]   # Never use on this day
    time_reference: str          # How to reference market data
    primary_focus: List[str]     # Best content types for this day
    avoid_categories: List[str]  # Categories that don't fit this day


DAY_CONTENT_RULES: Dict[str, DayRules] = {
    'Saturday': DayRules(
        day='Saturday',
        context='Newsletter just dropped, weekend recap mode',
        allowed_phrases=['Friday close', 'This week', 'Weekend', 'Saturday morning', 'Fresh scan'],
        blocked_phrases=['Today', 'Right now', 'Power hour', 'Into the close', 'This morning'],
        time_reference="Friday's close",
        primary_focus=['signal_recap', 'newsletter_promo', 'top_performers', 'funnel_stats'],
        avoid_categories=['power_hour', 'real_time'],
    ),
    'Sunday': DayRules(
        day='Sunday',
        context='Prep for week ahead, relaxed engagement',
        allowed_phrases=['This week', 'Looking ahead', 'Weekend', 'Next week', 'Sunday thoughts'],
        blocked_phrases=['Today', 'Power hour', 'Into the close', 'This morning'],
        time_reference="Friday's close",
        primary_focus=['watchlist', 'theme_outlook', 'engagement', 'educational'],
        avoid_categories=['power_hour', 'real_time', 'market_color'],
    ),
    'Monday': DayRules(
        day='Monday',
        context='Week kickoff, market opening',
        allowed_phrases=['This week', 'Based on Friday', 'New week', 'Opening bell', 'Monday momentum'],
        blocked_phrases=['Weekend homework', 'Saturday', 'Sunday'],
        time_reference="Friday's close",
        primary_focus=['theme_momentum', 'educational', 'market_color', 'signals'],
        avoid_categories=[],
    ),
    'Tuesday': DayRules(
        day='Tuesday',
        context='Mid-early week, positions developing',
        allowed_phrases=['This week', 'Early movers', 'Building', 'Developing'],
        blocked_phrases=['Weekend', 'Friday close', 'Saturday', 'Sunday'],
        time_reference="the weekly scan",
        primary_focus=['educational', 'early_movers', 'engagement', 'theme_analysis'],
        avoid_categories=['newsletter_promo'],
    ),
    'Wednesday': DayRules(
        day='Wednesday',
        context='Mid-week check-in',
        allowed_phrases=['Mid-week', 'This week', 'Halfway', 'Wednesday check'],
        blocked_phrases=['Weekend', 'Friday close', 'Saturday', 'Sunday', 'Weekend homework'],
        time_reference="the weekly scan",
        primary_focus=['watchlist', 'educational', 'engagement', 'process'],
        avoid_categories=['newsletter_promo', 'top_performers'],
    ),
    'Thursday': DayRules(
        day='Thursday',
        context='Building anticipation for Friday scan',
        allowed_phrases=['Tomorrow', 'Friday scan', 'Almost Friday', 'Looking ahead', 'Tomorrow\'s scan'],
        blocked_phrases=['Weekend homework', 'Last Friday', 'Saturday', 'Sunday'],
        time_reference="tomorrow's scan",
        primary_focus=['anticipation', 'educational', 'engagement', 'theme_preview'],
        avoid_categories=['top_performers', 'newsletter_promo'],
    ),
    'Friday': DayRules(
        day='Friday',
        context='Scan day - power hour is critical',
        allowed_phrases=['Today', "Today's close", 'Power hour', 'Scanner running', 'Fresh scan', 'Into the close'],
        blocked_phrases=['Last week', 'Weekend homework', 'Next Friday', 'Saturday'],
        time_reference="today's close",
        primary_focus=['power_hour', 'scan_anticipation', 'real_time', 'market_color'],
        avoid_categories=['newsletter_promo'],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT AVAILABILITY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class ContentCategory(Enum):
    """All possible content categories."""
    # Signal-based (requires data)
    WINNER_SHOWCASE = 'winner_showcase'
    SELF_QUOTE = 'self_quote'
    BEAT_SPY = 'beat_spy'
    SIGNAL_SPOTLIGHT = 'signal_spotlight'
    WATCHLIST_UPDATE = 'watchlist_update'
    THEME_MOMENTUM = 'theme_momentum'
    EARLY_MOVERS = 'early_movers'
    CLOSED_TRADE = 'closed_trade'
    MILESTONE_ALERT = 'milestone_alert'
    
    # Always available
    FUNNEL_STATS = 'funnel_stats'
    EDUCATIONAL = 'educational'
    ENGAGEMENT = 'engagement'
    PROCESS_EXPLAINER = 'process_explainer'
    NEWSLETTER_PROMO = 'newsletter_promo'
    
    # Building phase specific
    PATIENCE_CONTENT = 'patience_content'
    WHY_PROCESS_MATTERS = 'why_process_matters'
    
    # Time-specific
    POWER_HOUR = 'power_hour'
    MARKET_COLOR = 'market_color'


@dataclass
class ContentRequirement:
    """Defines what data is needed for a content category."""
    category: ContentCategory
    check_function: Callable[[dict], bool]
    priority: int                # 1=highest, 5=lowest
    valid_personas: List[str]    # Which personas can use this
    min_data_points: int = 1     # Minimum items needed
    description: str = ""


def _has_big_winners(data: dict) -> bool:
    """Check if there are positions up 25%+."""
    positions = data.get('open_positions', [])
    return any(p.get('pnl_pct', 0) >= 25.0 for p in positions)


def _has_uncelebrated_milestones(data: dict) -> bool:
    """Check for milestones not yet celebrated."""
    return len(data.get('uncelebrated_milestones', [])) >= 1


def _has_spy_outperformance(data: dict) -> bool:
    """Check if portfolio beats SPY by 5%+."""
    return data.get('portfolio_vs_spy', 0) >= 5.0


def _has_green_signals(data: dict) -> bool:
    """Check for GREEN (PASS) signals."""
    return len(data.get('pass_signals', [])) >= 1


def _has_consider_signals(data: dict) -> bool:
    """Check for CONSIDER signals."""
    return len(data.get('consider_signals', [])) >= 1


def _has_hot_themes(data: dict) -> bool:
    """Check for PRIME or INVESTABLE themes."""
    return len(data.get('prime_themes', []) + data.get('investable_themes', [])) >= 1


def _has_early_movers(data: dict) -> bool:
    """Check for young positions showing green."""
    positions = data.get('open_positions', [])
    return any(
        p.get('days_held', 999) <= 14 and p.get('pnl_pct', 0) > 0
        for p in positions
    )


def _has_winning_closed_trades(data: dict) -> bool:
    """Check for recent winning closed trades."""
    closed = data.get('closed_trades', [])
    return any(t.get('pnl_pct', 0) > 0 for t in closed)


def _no_big_winners(data: dict) -> bool:
    """Inverse of has_big_winners - for building phase content."""
    return not _has_big_winners(data)


def _always_available(data: dict) -> bool:
    """Content that's always available."""
    return True


# Define all content requirements
CONTENT_REQUIREMENTS: Dict[ContentCategory, ContentRequirement] = {
    ContentCategory.WINNER_SHOWCASE: ContentRequirement(
        category=ContentCategory.WINNER_SHOWCASE,
        check_function=_has_big_winners,
        priority=1,
        valid_personas=['main', 'account3'],
        description="Showcase positions up 25%+",
    ),
    ContentCategory.SELF_QUOTE: ContentRequirement(
        category=ContentCategory.SELF_QUOTE,
        check_function=_has_uncelebrated_milestones,
        priority=1,
        valid_personas=['main'],
        description="Celebrate uncelebrated milestones",
    ),
    ContentCategory.BEAT_SPY: ContentRequirement(
        category=ContentCategory.BEAT_SPY,
        check_function=_has_spy_outperformance,
        priority=2,
        valid_personas=['main'],
        description="Portfolio vs SPY comparison",
    ),
    ContentCategory.SIGNAL_SPOTLIGHT: ContentRequirement(
        category=ContentCategory.SIGNAL_SPOTLIGHT,
        check_function=_has_green_signals,
        priority=1,
        valid_personas=['main', 'account2', 'account3'],
        description="Highlight new GREEN signals",
    ),
    ContentCategory.WATCHLIST_UPDATE: ContentRequirement(
        category=ContentCategory.WATCHLIST_UPDATE,
        check_function=_has_consider_signals,
        priority=2,
        valid_personas=['main', 'account2', 'account3'],
        description="CONSIDER signals on radar",
    ),
    ContentCategory.THEME_MOMENTUM: ContentRequirement(
        category=ContentCategory.THEME_MOMENTUM,
        check_function=_has_hot_themes,
        priority=2,
        valid_personas=['main', 'account2', 'account3'],
        description="Hot theme discussion",
    ),
    ContentCategory.EARLY_MOVERS: ContentRequirement(
        category=ContentCategory.EARLY_MOVERS,
        check_function=_has_early_movers,
        priority=3,
        valid_personas=['account3', 'main'],
        description="Young positions showing strength",
    ),
    ContentCategory.CLOSED_TRADE: ContentRequirement(
        category=ContentCategory.CLOSED_TRADE,
        check_function=_has_winning_closed_trades,
        priority=2,
        valid_personas=['main'],
        description="Recent winning closed trades",
    ),
    ContentCategory.FUNNEL_STATS: ContentRequirement(
        category=ContentCategory.FUNNEL_STATS,
        check_function=_always_available,
        priority=3,
        valid_personas=['main', 'account2'],
        description="5-Gate funnel statistics",
    ),
    ContentCategory.EDUCATIONAL: ContentRequirement(
        category=ContentCategory.EDUCATIONAL,
        check_function=_always_available,
        priority=4,
        valid_personas=['account2', 'main', 'account3'],
        description="Educational content",
    ),
    ContentCategory.ENGAGEMENT: ContentRequirement(
        category=ContentCategory.ENGAGEMENT,
        check_function=_always_available,
        priority=5,
        valid_personas=['main', 'account2', 'account3'],
        description="Audience engagement",
    ),
    ContentCategory.PROCESS_EXPLAINER: ContentRequirement(
        category=ContentCategory.PROCESS_EXPLAINER,
        check_function=_always_available,
        priority=4,
        valid_personas=['main', 'account2'],
        description="How the system works",
    ),
    ContentCategory.PATIENCE_CONTENT: ContentRequirement(
        category=ContentCategory.PATIENCE_CONTENT,
        check_function=_no_big_winners,
        priority=3,
        valid_personas=['account2', 'main'],
        description="Building phase - patience messaging",
    ),
    ContentCategory.WHY_PROCESS_MATTERS: ContentRequirement(
        category=ContentCategory.WHY_PROCESS_MATTERS,
        check_function=_no_big_winners,
        priority=3,
        valid_personas=['account2'],
        description="Building phase - process focus",
    ),
    ContentCategory.POWER_HOUR: ContentRequirement(
        category=ContentCategory.POWER_HOUR,
        check_function=_always_available,
        priority=2,
        valid_personas=['account3', 'main'],
        description="Power hour market color",
    ),
    ContentCategory.MARKET_COLOR: ContentRequirement(
        category=ContentCategory.MARKET_COLOR,
        check_function=_always_available,
        priority=3,
        valid_personas=['account3'],
        description="Real-time market observations",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContentSlot:
    """A single content slot in the weekly schedule."""
    day: str                           # 'Saturday', 'Sunday', etc.
    slot_number: int                   # 1-5
    slot_time: str                     # '08:00'
    
    # What to generate
    primary_category: ContentCategory
    fallback_chain: List[ContentCategory]
    
    # Constraints
    max_chars: int = 280
    must_include_url: bool = True
    
    # Generation result (filled after generation)
    generated_text: Optional[str] = None
    actual_category: Optional[ContentCategory] = None
    generation_method: str = 'pending'


@dataclass
class ScannerSummary:
    """Summarized scanner data for content generation."""
    scan_date: str
    
    # Signals
    green_signals: List[dict]          # PASS signals (public-safe)
    consider_signals: List[dict]       # CONSIDER signals
    
    # Performance (filtered for public)
    top_performers: List[dict]         # Only 25%+ positions
    early_movers: List[dict]           # Young positions showing green
    closed_winners: List[dict]         # Recent winning closes
    
    # Themes
    themes_hot: List[dict]             # PRIME + INVESTABLE
    themes_cold: List[dict]            # AVOID themes
    
    # Metrics
    total_positions: int
    green_positions: int
    win_rate: float
    portfolio_vs_spy: float
    uncelebrated_milestones: List[dict]
    
    # Phase
    is_building_phase: bool            # No 25%+ winners yet


@dataclass
class ContentBrief:
    """Complete instructions for generating one account's weekly content."""
    
    # Identity
    account_id: str
    persona: Persona
    
    # Data
    scanner_summary: ScannerSummary
    
    # Available content
    available_categories: List[ContentCategory]
    unavailable_categories: List[ContentCategory]
    
    # Weekly plan
    slots: List[ContentSlot]
    
    # Constraints
    excluded_tickers: Set[str]         # Already mentioned enough
    content_hashes_used: Set[str]      # Avoid duplicates
    
    # Metadata
    created_at: str
    week_start: str


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT PLANNER
# ═══════════════════════════════════════════════════════════════════════════════

class ContentPlanner:
    """
    Analyzes scanner data and creates differentiated content briefs.
    
    This is the main orchestrator that:
    1. Assesses what content is possible given current data
    2. Creates tailored briefs for each persona
    3. Ensures differentiation across accounts
    """
    
    def __init__(self, scanner_data: dict, portfolio_data: dict):
        """
        Initialize planner with scanner and portfolio data.
        
        Args:
            scanner_data: Output from scanner.py (signals, themes, etc.)
            portfolio_data: Output from portfolio_manager.py (positions, P&L)
        """
        self.scanner_data = scanner_data
        self.portfolio_data = portfolio_data
        self.scan_date = scanner_data.get('scan_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Merge data for availability checking
        self.merged_data = self._merge_data()
        
        # Assess what's available
        self.availability = self._assess_availability()
        
        # Track cross-account usage
        self.used_topics_by_day: Dict[str, Set[str]] = {}
        self.used_tickers_by_account: Dict[str, Set[str]] = {}
    
    def _merge_data(self) -> dict:
        """Merge scanner and portfolio data into unified structure."""
        positions = self.portfolio_data.get('positions', [])
        
        # Calculate derived fields
        winners_25_plus = [p for p in positions if p.get('pnl_pct', 0) >= 25.0]
        green_positions = [p for p in positions if p.get('pnl_pct', 0) > 0]
        
        return {
            'pass_signals': self.scanner_data.get('pass_signals', []),
            'consider_signals': self.scanner_data.get('consider_signals', []),
            'open_positions': positions,
            'closed_trades': self.portfolio_data.get('closed_trades', []),
            'prime_themes': self.scanner_data.get('prime_themes', []),
            'investable_themes': self.scanner_data.get('investable_themes', []),
            'winners_25_plus': winners_25_plus,
            'uncelebrated_milestones': self._find_uncelebrated_milestones(positions),
            'portfolio_vs_spy': self.portfolio_data.get('vs_spy', 0),
        }
    
    def _find_uncelebrated_milestones(self, positions: List[dict]) -> List[dict]:
        """Find positions that hit milestones not yet celebrated."""
        uncelebrated = []
        for pos in positions:
            pnl = pos.get('pnl_pct', 0)
            celebrated = pos.get('celebrated', {})
            
            for threshold in CELEBRATION_THRESHOLDS:
                if pnl >= threshold:
                    key = CELEBRATION_KEYS[threshold]
                    if not celebrated.get(key):
                        uncelebrated.append({
                            'ticker': pos.get('ticker'),
                            'pnl_pct': pnl,
                            'threshold': threshold,
                        })
                        break  # Only count highest uncelebrated
        
        return uncelebrated
    
    def _assess_availability(self) -> Dict[ContentCategory, bool]:
        """Check which content categories are available."""
        availability = {}
        
        for category, requirement in CONTENT_REQUIREMENTS.items():
            try:
                available = requirement.check_function(self.merged_data)
                availability[category] = available
            except Exception as e:
                print(f"  ⚠️ Error checking {category.value}: {e}")
                availability[category] = False
        
        return availability
    
    def _create_scanner_summary(self) -> ScannerSummary:
        """Create public-safe summary of scanner data."""
        positions = self.merged_data.get('open_positions', [])
        
        # Filter for public safety
        public_positions = [
            p for p in positions
            if p.get('pnl_pct', 0) >= 0  # Only green positions
        ]
        
        top_performers = [
            {
                'ticker': p.get('ticker'),
                'pnl_pct': p.get('pnl_pct'),
                'days_held': p.get('days_held'),
                'entry_price': p.get('entry_price') if can_show_entry_price(p) else None,
                'theme': p.get('theme'),
            }
            for p in positions
            if p.get('pnl_pct', 0) >= 25.0
        ]
        
        early_movers = [
            {
                'ticker': p.get('ticker'),
                'pnl_pct': p.get('pnl_pct'),
                'days_held': p.get('days_held'),
            }
            for p in positions
            if p.get('days_held', 999) <= 14 and p.get('pnl_pct', 0) > 0
        ]
        
        green_count = len([p for p in positions if p.get('pnl_pct', 0) > 0])
        total_count = len(positions)
        
        return ScannerSummary(
            scan_date=self.scan_date,
            green_signals=self.merged_data.get('pass_signals', []),
            consider_signals=self.merged_data.get('consider_signals', []),
            top_performers=top_performers,
            early_movers=early_movers,
            closed_winners=[
                t for t in self.merged_data.get('closed_trades', [])
                if t.get('pnl_pct', 0) > 0
            ],
            themes_hot=self.merged_data.get('prime_themes', []) + self.merged_data.get('investable_themes', []),
            themes_cold=self.scanner_data.get('avoid_themes', []),
            total_positions=total_count,
            green_positions=green_count,
            win_rate=(green_count / total_count * 100) if total_count > 0 else 0,
            portfolio_vs_spy=self.merged_data.get('portfolio_vs_spy', 0),
            uncelebrated_milestones=self.merged_data.get('uncelebrated_milestones', []),
            is_building_phase=not self.availability.get(ContentCategory.WINNER_SHOWCASE, False),
        )
    
    def _get_available_categories_for_persona(self, persona: Persona) -> Tuple[List[ContentCategory], List[ContentCategory]]:
        """Get available and unavailable categories for a persona."""
        available = []
        unavailable = []
        
        for category, is_available in self.availability.items():
            requirement = CONTENT_REQUIREMENTS.get(category)
            if not requirement:
                continue
            
            # Check if persona can use this category
            if persona.account_id not in requirement.valid_personas:
                continue
            
            if is_available:
                available.append(category)
            else:
                unavailable.append(category)
        
        # Sort by priority
        available.sort(key=lambda c: CONTENT_REQUIREMENTS[c].priority)
        
        return available, unavailable
    
    def _create_weekly_slots(self, persona: Persona, available_categories: List[ContentCategory]) -> List[ContentSlot]:
        """Create weekly content slots for a persona."""
        slots = []
        
        # Get persona's content mix weights
        mix = persona.content_mix
        
        for day_name, day_rules in DAY_CONTENT_RULES.items():
            for slot_num in range(1, 6):
                slot_time = SLOT_TIMES_ET.get(slot_num, '12:00')
                
                # Determine primary category based on:
                # 1. Day rules (what's appropriate for this day)
                # 2. Persona focus (what this account emphasizes)
                # 3. Data availability (what we can actually generate)
                # 4. Slot timing (power hour = slot 4)
                
                primary = self._select_primary_category(
                    day_name, slot_num, persona, available_categories, day_rules
                )
                
                # Build fallback chain
                fallbacks = self._build_fallback_chain(primary, available_categories)
                
                slots.append(ContentSlot(
                    day=day_name,
                    slot_number=slot_num,
                    slot_time=slot_time,
                    primary_category=primary,
                    fallback_chain=fallbacks,
                    must_include_url=(slot_num in [1, 2, 5]),  # URL on key slots
                ))
        
        return slots
    
    def _select_primary_category(
        self, 
        day: str, 
        slot: int, 
        persona: Persona,
        available: List[ContentCategory],
        day_rules: DayRules
    ) -> ContentCategory:
        """Select the best category for a specific slot."""
        
        # Special cases by slot
        if slot == 4 and day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            # Power hour slot
            if ContentCategory.POWER_HOUR in available:
                return ContentCategory.POWER_HOUR
            if ContentCategory.MARKET_COLOR in available:
                return ContentCategory.MARKET_COLOR
        
        # Saturday slot 1 = top performers or signal recap
        if day == 'Saturday' and slot == 1:
            if ContentCategory.WINNER_SHOWCASE in available:
                return ContentCategory.WINNER_SHOWCASE
            if ContentCategory.SIGNAL_SPOTLIGHT in available:
                return ContentCategory.SIGNAL_SPOTLIGHT
        
        # Filter by day rules
        valid_for_day = [
            c for c in available
            if c.value not in [cat for cat in day_rules.avoid_categories]
        ]
        
        # Prefer persona's focus areas
        primary_focus = persona.focus_areas.get('primary', [])
        for focus in primary_focus:
            for cat in valid_for_day:
                if focus in cat.value:
                    return cat
        
        # Fall back to highest priority available
        if valid_for_day:
            return valid_for_day[0]
        
        # Ultimate fallback
        return ContentCategory.ENGAGEMENT
    
    def _build_fallback_chain(
        self, 
        primary: ContentCategory, 
        available: List[ContentCategory]
    ) -> List[ContentCategory]:
        """Build fallback chain for a category."""
        
        # Define fallback preferences
        FALLBACK_MAP = {
            ContentCategory.WINNER_SHOWCASE: [ContentCategory.THEME_MOMENTUM, ContentCategory.FUNNEL_STATS, ContentCategory.EDUCATIONAL],
            ContentCategory.SELF_QUOTE: [ContentCategory.WATCHLIST_UPDATE, ContentCategory.THEME_MOMENTUM, ContentCategory.EDUCATIONAL],
            ContentCategory.BEAT_SPY: [ContentCategory.FUNNEL_STATS, ContentCategory.THEME_MOMENTUM, ContentCategory.EDUCATIONAL],
            ContentCategory.SIGNAL_SPOTLIGHT: [ContentCategory.THEME_MOMENTUM, ContentCategory.FUNNEL_STATS, ContentCategory.EDUCATIONAL],
            ContentCategory.POWER_HOUR: [ContentCategory.MARKET_COLOR, ContentCategory.THEME_MOMENTUM, ContentCategory.ENGAGEMENT],
        }
        
        chain = FALLBACK_MAP.get(primary, [ContentCategory.EDUCATIONAL, ContentCategory.ENGAGEMENT])
        
        # Filter to only available categories
        chain = [c for c in chain if c in available or c == ContentCategory.ENGAGEMENT]
        
        # Always end with engagement as ultimate fallback
        if ContentCategory.ENGAGEMENT not in chain:
            chain.append(ContentCategory.ENGAGEMENT)
        
        return chain
    
    def _ensure_differentiation(self, briefs: Dict[str, ContentBrief]) -> None:
        """Ensure accounts don't post the same content on the same day."""
        
        for day in DAY_CONTENT_RULES.keys():
            # Get all slots for this day across accounts
            day_slots_by_account = {}
            
            for account_id, brief in briefs.items():
                day_slots_by_account[account_id] = [
                    s for s in brief.slots if s.day == day
                ]
            
            # For each slot number, ensure different primary categories
            for slot_num in range(1, 6):
                used_categories = set()
                
                for account_id in ['main', 'account2', 'account3']:
                    brief = briefs.get(account_id)
                    if not brief:
                        continue
                    
                    slot = next((s for s in brief.slots if s.day == day and s.slot_number == slot_num), None)
                    if not slot:
                        continue
                    
                    # If this category already used by another account in this slot
                    if slot.primary_category in used_categories:
                        # Try fallbacks
                        for fallback in slot.fallback_chain:
                            if fallback not in used_categories:
                                slot.primary_category = fallback
                                break
                    
                    used_categories.add(slot.primary_category)
    
    def create_brief(self, account_id: str) -> ContentBrief:
        """Create a content brief for a single account."""
        persona = PERSONAS.get(account_id)
        if not persona:
            raise ValueError(f"Unknown account: {account_id}")
        
        available, unavailable = self._get_available_categories_for_persona(persona)
        scanner_summary = self._create_scanner_summary()
        slots = self._create_weekly_slots(persona, available)
        
        return ContentBrief(
            account_id=account_id,
            persona=persona,
            scanner_summary=scanner_summary,
            available_categories=available,
            unavailable_categories=unavailable,
            slots=slots,
            excluded_tickers=set(),
            content_hashes_used=set(),
            created_at=datetime.now().isoformat(),
            week_start=self.scan_date,
        )
    
    def create_all_briefs(self) -> Dict[str, ContentBrief]:
        """Create content briefs for all accounts."""
        briefs = {}
        
        for account_id in PERSONAS.keys():
            briefs[account_id] = self.create_brief(account_id)
        
        # Ensure differentiation
        self._ensure_differentiation(briefs)
        
        return briefs


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class PersonaGenerator:
    """
    Generates content for a single account using Claude API.
    
    Features:
    - Single batch call for cohesive voice
    - Persona-aware prompting
    - Day-aware phrasing
    - Building phase handling
    """
    
    def __init__(self, brief: ContentBrief):
        self.brief = brief
        self.client = anthropic.Anthropic()
    
    def generate(self) -> List[dict]:
        """Generate all tweets for this account's brief."""
        
        # Group slots by day for batch generation
        tweets_by_day = {}
        
        for day in DAY_CONTENT_RULES.keys():
            day_slots = [s for s in self.brief.slots if s.day == day]
            if day_slots:
                tweets_by_day[day] = self._generate_day_batch(day, day_slots)
        
        # Flatten to list
        all_tweets = []
        for day, tweets in tweets_by_day.items():
            all_tweets.extend(tweets)
        
        return all_tweets
    
    def _generate_day_batch(self, day: str, slots: List[ContentSlot]) -> List[dict]:
        """Generate all tweets for a single day in one Claude call."""
        
        day_rules = DAY_CONTENT_RULES[day]
        
        prompt = self._build_generation_prompt(day, slots, day_rules)
        
        try:
            response = self.client.messages.create(
                model=MODEL_TWEET,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_response(response.content[0].text, day, slots)
            
        except Exception as e:
            print(f"  ❌ Generation failed for {self.brief.account_id} {day}: {e}")
            return self._generate_fallback_tweets(day, slots)
    
    def _build_generation_prompt(self, day: str, slots: List[ContentSlot], day_rules: DayRules) -> str:
        """Build the Claude prompt for generating a day's tweets."""
        
        persona = self.brief.persona
        summary = self.brief.scanner_summary
        
        # Serialize persona for prompt
        persona_json = json.dumps({
            'name': persona.name,
            'archetype': persona.archetype,
            'tone': persona.voice.tone,
            'traits': persona.voice.traits,
            'signature_phrases': persona.signature_phrases,
            'avoid': persona.voice.avoid,
        }, indent=2)
        
        # Serialize data for prompt
        data_json = json.dumps({
            'scan_date': summary.scan_date,
            'green_signals': summary.green_signals[:5],  # Limit for token efficiency
            'consider_signals': summary.consider_signals[:5],
            'top_performers': summary.top_performers[:5],
            'themes_hot': [t.get('name') for t in summary.themes_hot[:3]],
            'win_rate': f"{summary.win_rate:.1f}%",
            'is_building_phase': summary.is_building_phase,
        }, indent=2)
        
        # Build slot requirements
        slot_reqs = []
        for slot in slots:
            slot_reqs.append(f"Slot {slot.slot_number} ({slot.slot_time}): {slot.primary_category.value}")
        
        building_guidance = ""
        if summary.is_building_phase:
            building_guidance = """
## BUILDING PHASE ACTIVE
You don't have 25%+ winners yet. This is normal for a new system.

DO:
- Focus on process, not results
- Highlight new signals and what makes them interesting
- Educate about the 5-Gate System
- Build anticipation

DON'T:
- Pretend you have big winners
- Use language like "crushing it" or "winning streak"
- Show entry prices (reserved for 25%+ positions)
"""
        
        return f'''
Generate {len(slots)} tweets for {day}.

## YOUR PERSONA
{persona_json}

## TODAY'S CONTEXT: {day}
{day_rules.context}
Time reference to use: "{day_rules.time_reference}"
Phrases to AVOID today: {', '.join(day_rules.blocked_phrases)}
Phrases OK to use: {', '.join(day_rules.allowed_phrases)}

## SCANNER DATA
{data_json}

## SLOTS TO FILL
{chr(10).join(slot_reqs)}
{building_guidance}

## RULES
1. Stay in character - use the persona's tone and signature phrases
2. Reference real data only - never invent tickers or percentages
3. Use GREEN for buy signals, CONSIDER (🟡) for watchlist
4. Entry prices: ONLY show for positions up 25%+ (top_performers)
5. Include newsletter URL on slots 1, 2, and 5: https://sterlingsignals.substack.com
6. Stay under 280 characters per tweet
7. Each tweet must be unique - different angle, different tickers
8. Respect the day context - no "Weekend homework" on {day}

## OUTPUT FORMAT
Return ONLY a JSON array, no other text:
[
  {{"slot": 1, "category": "signal_spotlight", "text": "Tweet text here..."}},
  {{"slot": 2, "category": "educational", "text": "Tweet text here..."}},
  ...
]
'''
    
    def _parse_response(self, response_text: str, day: str, slots: List[ContentSlot]) -> List[dict]:
        """Parse Claude's response into tweet dicts."""
        
        # Clean response
        text = response_text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()
        
        try:
            tweets_raw = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse response: {e}")
            return self._generate_fallback_tweets(day, slots)
        
        # Convert to standard format
        tweets = []
        for raw in tweets_raw:
            slot_num = raw.get('slot')
            slot = next((s for s in slots if s.slot_number == slot_num), None)
            
            tweets.append({
                'id': f"{self.brief.account_id}_{day}_{slot_num}",
                'day': day,
                'slot': slot_num,
                'time': slot.slot_time if slot else '12:00',
                'category': raw.get('category'),
                'text': raw.get('text'),
                'account': self.brief.account_id,
                'persona': self.brief.persona.name,
                'generation_method': 'claude_persona',
                'scan_date': self.brief.scanner_summary.scan_date,
            })
        
        return tweets
    
    def _generate_fallback_tweets(self, day: str, slots: List[ContentSlot]) -> List[dict]:
        """Generate simple fallback tweets if Claude fails."""
        
        tweets = []
        for slot in slots:
            # Very simple fallback
            text = f"The 5-Gate System keeps scanning. Quality over quantity.\n\n{BRANDING['substack_url']}"
            
            tweets.append({
                'id': f"{self.brief.account_id}_{day}_{slot.slot_number}",
                'day': day,
                'slot': slot.slot_number,
                'time': slot.slot_time,
                'category': 'engagement',
                'text': text,
                'account': self.brief.account_id,
                'persona': self.brief.persona.name,
                'generation_method': 'fallback',
            })
        
        return tweets


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-ACCOUNT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CrossAccountValidator:
    """
    Validates content across all accounts to ensure differentiation.
    """
    
    def __init__(self, all_tweets: Dict[str, List[dict]]):
        self.all_tweets = all_tweets
    
    def validate(self) -> Dict[str, List[str]]:
        """
        Run all validation checks.
        
        Returns:
            Dict mapping account_id to list of issues
        """
        issues = {account: [] for account in self.all_tweets.keys()}
        
        # Check for duplicate content across accounts
        self._check_cross_account_duplicates(issues)
        
        # Check for same topic on same day across accounts
        self._check_topic_overlap(issues)
        
        # Check for day-inappropriate content
        self._check_day_appropriateness(issues)
        
        return issues
    
    def _check_cross_account_duplicates(self, issues: Dict[str, List[str]]) -> None:
        """Check for substantially similar tweets across accounts."""
        
        all_texts = []
        for account_id, tweets in self.all_tweets.items():
            for tweet in tweets:
                all_texts.append((account_id, tweet.get('day'), tweet.get('slot'), tweet.get('text', '')))
        
        for i, (acc1, day1, slot1, text1) in enumerate(all_texts):
            for acc2, day2, slot2, text2 in all_texts[i+1:]:
                if acc1 == acc2:
                    continue
                
                # Check similarity
                similarity = self._text_similarity(text1, text2)
                if similarity > 0.7:  # 70% similar
                    issues[acc1].append(
                        f"Similar to {acc2} on {day2} slot {slot2}: {similarity:.0%} match"
                    )
    
    def _check_topic_overlap(self, issues: Dict[str, List[str]]) -> None:
        """Check for same category on same day/slot across accounts."""
        
        for day in DAY_CONTENT_RULES.keys():
            for slot in range(1, 6):
                categories_used = {}
                
                for account_id, tweets in self.all_tweets.items():
                    tweet = next(
                        (t for t in tweets if t.get('day') == day and t.get('slot') == slot),
                        None
                    )
                    if tweet:
                        cat = tweet.get('category')
                        if cat in categories_used:
                            issues[account_id].append(
                                f"{day} slot {slot}: Same category '{cat}' as {categories_used[cat]}"
                            )
                        else:
                            categories_used[cat] = account_id
    
    def _check_day_appropriateness(self, issues: Dict[str, List[str]]) -> None:
        """Check for day-inappropriate phrases."""
        
        for account_id, tweets in self.all_tweets.items():
            for tweet in tweets:
                day = tweet.get('day')
                text = tweet.get('text', '').lower()
                
                day_rules = DAY_CONTENT_RULES.get(day)
                if not day_rules:
                    continue
                
                for blocked in day_rules.blocked_phrases:
                    if blocked.lower() in text:
                        issues[account_id].append(
                            f"{day} slot {tweet.get('slot')}: Contains blocked phrase '{blocked}'"
                        )
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_all_content(scanner_data: dict, portfolio_data: dict) -> Dict[str, List[dict]]:
    """
    Main entry point for generating content for all accounts.
    
    Args:
        scanner_data: Output from scanner.py
        portfolio_data: Output from portfolio_manager.py
    
    Returns:
        Dict mapping account_id to list of tweets
    """
    print("\n📊 Content Planner: Starting generation")
    
    # Phase 1: Create content briefs
    print("  Creating content briefs...")
    planner = ContentPlanner(scanner_data, portfolio_data)
    briefs = planner.create_all_briefs()
    
    # Log phase status
    if briefs['main'].scanner_summary.is_building_phase:
        print("  📈 BUILDING PHASE: No 25%+ winners yet - focusing on process content")
    else:
        print(f"  🏆 PERFORMANCE PHASE: {len(briefs['main'].scanner_summary.top_performers)} top performers")
    
    # Phase 2: Generate content for each account
    all_tweets = {}
    for account_id, brief in briefs.items():
        print(f"  Generating {brief.persona.name} ({account_id})...")
        generator = PersonaGenerator(brief)
        all_tweets[account_id] = generator.generate()
    
    # Phase 3: Validate cross-account
    print("  Validating cross-account differentiation...")
    validator = CrossAccountValidator(all_tweets)
    issues = validator.validate()
    
    for account_id, account_issues in issues.items():
        if account_issues:
            print(f"    ⚠️ {account_id}: {len(account_issues)} issues")
            for issue in account_issues[:3]:  # Show first 3
                print(f"       - {issue}")
    
    print(f"  ✅ Generated {sum(len(t) for t in all_tweets.values())} tweets total")
    
    return all_tweets


def save_content_queues(all_tweets: Dict[str, List[dict]], output_dir: Path) -> None:
    """Save generated tweets to content queue files."""
    
    for account_id, tweets in all_tweets.items():
        account_config = TWITTER_ACCOUNTS.get(account_id, {})
        queue_file = account_config.get('queue_file', f'content_queue_{account_id}.json')
        
        output_path = output_dir / queue_file
        
        with open(output_path, 'w') as f:
            json.dump(tweets, f, indent=2)
        
        print(f"  Saved {len(tweets)} tweets to {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION PATH
# ═══════════════════════════════════════════════════════════════════════════════

"""
MIGRATION FROM EXISTING TWEET_GENERATOR.PY
==========================================

Phase 1 (Quick Wins):
- Keep existing tweet_generator.py as primary
- Apply bug fixes from CLAUDE_CODE_PROMPT
- Add persona context to variation prompts
- Add day-aware filtering to templates

Phase 2 (Parallel Operation):
- Import ContentPlanner alongside existing code
- Use ContentPlanner to create briefs
- Use existing templates where available
- Fall back to PersonaGenerator for gaps
- Compare output quality

Phase 3 (Full Migration):
- Replace template generation with PersonaGenerator
- Use ContentBrief as primary data structure
- Keep templates as "hint" library, not literal output
- Archive old template-based code

Integration Code for Phase 2:
-----------------------------

from content_planner import ContentPlanner, PersonaGenerator

def generate_weekly_tweets_v2(content: WeeklyContent) -> Dict[str, List[dict]]:
    '''Hybrid generation using ContentPlanner + existing templates.'''
    
    # Convert WeeklyContent to scanner_data format
    scanner_data = {
        'pass_signals': content.pass_signals,
        'consider_signals': content.consider_signals,
        'prime_themes': content.prime_themes,
        'investable_themes': content.investable_themes,
        'scan_date': content.scan_date,
    }
    
    portfolio_data = {
        'positions': content.open_positions,
        'closed_trades': content.closed_trades,
        'vs_spy': calculate_spy_comparison(content),  # Your existing function
    }
    
    # Create briefs
    planner = ContentPlanner(scanner_data, portfolio_data)
    briefs = planner.create_all_briefs()
    
    all_tweets = {}
    
    for account_id, brief in briefs.items():
        tweets = []
        
        for slot in brief.slots:
            # Try template first for main account
            if account_id == 'main':
                template_tweet = select_and_populate_template(
                    slot.primary_category.value,
                    content,
                    day=slot.day
                )
                if template_tweet:
                    tweets.append(template_tweet)
                    continue
            
            # Fall back to persona generation
            generator = PersonaGenerator(ContentBrief(
                account_id=account_id,
                persona=brief.persona,
                scanner_summary=brief.scanner_summary,
                available_categories=brief.available_categories,
                unavailable_categories=brief.unavailable_categories,
                slots=[slot],  # Just this slot
                excluded_tickers=set(),
                content_hashes_used=set(),
                created_at=datetime.now().isoformat(),
                week_start=brief.scanner_summary.scan_date,
            ))
            generated = generator.generate()
            tweets.extend(generated)
        
        all_tweets[account_id] = tweets
    
    return all_tweets
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Content Planner CLI')
    parser.add_argument('--scanner-file', type=str, help='Path to scanner output JSON')
    parser.add_argument('--portfolio-file', type=str, help='Path to portfolio data JSON')
    parser.add_argument('--output-dir', type=str, default='trades/tweets', help='Output directory')
    parser.add_argument('--dry-run', action='store_true', help='Print briefs without generating')
    
    args = parser.parse_args()
    
    # Load data
    if args.scanner_file:
        with open(args.scanner_file) as f:
            scanner_data = json.load(f)
    else:
        # Mock data for testing
        scanner_data = {
            'pass_signals': [{'ticker': 'AMPX', 'theme': 'AI Infrastructure'}],
            'consider_signals': [{'ticker': 'LUMN', 'theme': 'Data Centers'}],
            'prime_themes': [{'name': 'AI Infrastructure', 'score': 8.5}],
            'investable_themes': [{'name': 'Data Centers', 'score': 7.0}],
            'scan_date': datetime.now().strftime('%Y-%m-%d'),
        }
    
    if args.portfolio_file:
        with open(args.portfolio_file) as f:
            portfolio_data = json.load(f)
    else:
        # Mock data for testing
        portfolio_data = {
            'positions': [
                {'ticker': 'NVDA', 'pnl_pct': 32.5, 'days_held': 45, 'entry_price': 450},
                {'ticker': 'AMD', 'pnl_pct': 15.2, 'days_held': 30},
                {'ticker': 'AMPX', 'pnl_pct': 5.5, 'days_held': 7},
            ],
            'closed_trades': [],
            'vs_spy': 12.5,
        }
    
    if args.dry_run:
        # Just print briefs
        planner = ContentPlanner(scanner_data, portfolio_data)
        briefs = planner.create_all_briefs()
        
        for account_id, brief in briefs.items():
            print(f"\n{'='*60}")
            print(f"BRIEF: {brief.persona.name} ({account_id})")
            print(f"{'='*60}")
            print(f"Building Phase: {brief.scanner_summary.is_building_phase}")
            print(f"Available Categories: {[c.value for c in brief.available_categories]}")
            print(f"\nSlots:")
            for slot in brief.slots[:10]:  # First 10
                print(f"  {slot.day} #{slot.slot_number}: {slot.primary_category.value}")
    else:
        # Full generation
        all_tweets = generate_all_content(scanner_data, portfolio_data)
        
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        save_content_queues(all_tweets, output_dir)
        
        print("\n✅ Content generation complete!")
