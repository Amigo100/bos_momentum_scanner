#!/usr/bin/env python3
"""
MARKETING VOCABULARY - Centralized Marketing Language Enforcement
=================================================================

⚠️  DEPRECATION NOTICE (2026-02-06)
────────────────────────────────────
BANNED_TERMS and CRITICAL_BANNED have moved to config/banned_terms.py.
That module is now the SINGLE SOURCE OF TRUTH for all banned content.

Import banned terms from config.banned_terms, NOT from this file:

    from config.banned_terms import CRITICAL_BANNED, BANNED_PHRASES, ALL_BANNED

This module still provides:
    - validate_content()        — content validation function
    - APPROVED_VOCABULARY       — approved marketing phrases
    - POWER_PHRASES             — high-impact phrases
    - US_AUDIENCE_HOOKS         — US audience content hooks
    - validate_all_tweets()     — batch tweet validation

The BANNED_TERMS and CRITICAL_BANNED lists here are RETAINED for
backwards compatibility but will be removed in a future release.

Version: 2.0 (GREEN/RED signal system - replaces TEAL/purple)
"""

import functools
import re
from typing import Callable, Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# BANNED TERMS - Never use these in public content
# ═══════════════════════════════════════════════════════════════════════════════

BANNED_TERMS: List[str] = [
    # Technical indicators (internal system names)
    "HMA", "Hull Moving Average", "HMA Pivot", "HMA pivot",
    "Banker indicator", "Banker >= 55", "Banker ≥ 55", "Banker >=", "banker indicator",
    "20% trailing stop", "20% stop",
    "Beta >= 1.5", "Beta ≥ 1.5", "beta threshold", "Beta >=",
    "Break of Structure", "BoS", "BOS", "Weekly BoS", "weekly bos",
    "Tier 1", "Tier 2", "Tier 3", "TIER1", "TIER2", "TIER3",
    "Gatekeeper",
    "Weekly pivot",

    # Specific technical indicators
    "RSI", "MACD", "KDJ",

    # OLD COLOR SYSTEM (v2.0 - now banned, use GREEN/RED)
    "TEAL signal", "TEAL", "teal signal", "teal",
    "purple signal", "purple", "PURPLE",
    "VIOLET signal", "VIOLET", "violet",
    "🟣",  # Old purple emoji
    "AMBER signal", "AMBER", "amber",

    # Outdated audience references (UK)
    "UK ISA", "ISA wrapper", "Barclays ISA", "ISA account",
    "UK investor", "UK investors", "UK trader", "UK traders",
    "GMT", "BST", "UK Time", "UK time", "London time",
    "GBP/USD",
    # NOTE: "sterling" not banned - false positive for "Sterling Signals" brand name

    # Internal terms that leaked (BANNED)
    "Capital Preservation Protocol",
    "Forensic Audit",
    "Volatility Expansion Criteria",
    "5th Gate", "Gate 5",

    # Non-branded signal terms (use "GREEN signal" instead)
    "proprietary entry", "proprietary signal",
    "PASS signal",

    # US-specific retirement accounts (wrong audience context)
    "Roth IRA", "Roth",
    "PDT", "PDT rule", "pattern day trader",
    "401k", "401(k)",

    # Signal branding violations - MUST use conviction language
    "conviction 5", "conviction 4", "conviction 3",
    "conviction score", "conviction rating",
]

# Fast-path subset for pre-post validation (used by twitter_poster.py).
# Must remain a subset of BANNED_TERMS above.
CRITICAL_BANNED: List[str] = [
    # Strategy internals
    'HMA', '20% stop', 'Banker >=', 'Beta >=', 'BoS',
    # Wrong audience
    'Roth IRA', 'Roth', 'PDT', '401k',
    # Internal terms that leaked
    'Capital Preservation Protocol', 'Forensic Audit',
    'Volatility Expansion Criteria', '5th Gate', 'Gate 5',
    # Non-branded signal terms
    'proprietary entry', 'proprietary signal',
    # OLD COLOR SYSTEM (v2.0 - now banned)
    'TEAL signal', 'TEAL',
    'purple signal', 'VIOLET',
]

# ═══════════════════════════════════════════════════════════════════════════════
# APPROVED VOCABULARY - Use these instead
# ═══════════════════════════════════════════════════════════════════════════════

APPROVED_VOCABULARY: Dict[str, str] = {
    # Internal term → Marketing term
    "HMA Pivot": "momentum confirmed",
    "Banker indicator": "strong accumulation",
    "Beta >= 1.5": "volatility characteristics",
    "20% trailing stop": "trailing stop",
    "Weekly BoS": "momentum confirmed",
    "Gatekeeper": "cleared all gates",
    "Tier 1/2/3": "high conviction",
    "Theme scoring": "theme alignment",

    # NEW Color signal system (v2.0 - GREEN/RED)
    "🟢 GREEN": "buy signal emoji",
    "🔴 RED": "exit/sell signal emoji", 
    "🟡 CONSIDER": "watchlist signal emoji",

    # Migration mappings (old → new)
    "TEAL signal": "GREEN signal",
    "VIOLET signal": "RED signal",
    "purple signal": "RED signal",
    "AMBER signal": "CONSIDER signal",
    "buy signal": "GREEN signal",
    "PASS signal": "GREEN signal",

    # Conviction language (public-facing)
    "Extremely Bullish": "conviction 5 public language",
    "Bullish": "conviction 4 public language",
    "Watching": "conviction 3 public language",
    "Cautious": "conviction 2 public language",
}

# ═══════════════════════════════════════════════════════════════════════════════
# POWER PHRASES - Approved marketing language
# ═══════════════════════════════════════════════════════════════════════════════

POWER_PHRASES: List[str] = [
    # System description
    "Proprietary 5-gate screening system",
    "Filters 1,800 stocks to 3-5 actionable signals",
    "Institutional-grade momentum analysis",
    "Systematic approach that removes emotional bias",

    # Signal detection (v2.0 - GREEN/RED)
    "GREEN signal triggered",
    "RED signal - time to rotate",
    "Cleared all 5 gates",
    "Strong accumulation detected",
    "Theme alignment confirmed",
    "Momentum confirmed",

    # Risk management
    "Systematic exit discipline",
    "Trailing stop in place",
    "Risk-defined position sizing",
    "The system protects capital so we live to fight another day",
    "No ego, just execution",

    # Performance framing
    "Beat SPY with systematic momentum",
    "Alpha over indexing",
    "Stop indexing. Start selecting.",
    "Weekly timeframe suits swing traders",
    
    # Friday/weekly references
    "As of Friday's close",
    "Based on the latest weekly close",
    "Friday's scan results",
]

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIENCE HOOKS - Audience-neutral content angles
# ═══════════════════════════════════════════════════════════════════════════════

AUDIENCE_HOOKS: Dict[str, List[str]] = {
    "beat_spy": [
        "Stop indexing. Start selecting.",
        "SPY gives you average returns. We hunt outliers.",
        "The difference between 10% and 40%? Stock selection.",
        "Most portfolios mirror SPY. Ours hunts alpha.",
    ],
    "time_friendly": [
        "Weekly timeframe suits busy schedules.",
        "Systematic momentum for patient capital.",
        "15 minutes/week vs all-day stress.",
        "Swing trading that works with your schedule.",
    ],
    "power_hour": [
        "Power Hour Check:",
        "Watching relative strength into the close.",
        "Volume confirmation in the final hour.",
        "Structural confirmation on the weekly close.",
    ],
    "sector_rotation": [
        "Money is rotating.",
        "Follow the institutional flows.",
        "Smart money moving from X to Y.",
        "Theme rotation in action.",
    ],
    "friday_close": [
        "Scanner ran after Friday's close.",
        "As of the latest weekly close.",
        "Friday's results are in.",
        "Week-ending momentum check.",
    ],
}

# Backwards compatibility alias
US_AUDIENCE_HOOKS = AUDIENCE_HOOKS

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_content(text: str) -> Tuple[bool, List[str]]:
    """
    Check content for banned terms.

    Args:
        text: The content to validate (tweet, newsletter section, etc.)

    Returns:
        Tuple of (is_valid, list_of_violations)
        - is_valid: True if no banned terms found
        - violations: List of banned terms that were found
    """
    if not text:
        return True, []

    violations = []
    text_lower = text.lower()

    for term in BANNED_TERMS:
        # Case-insensitive check for most terms
        if term.lower() in text_lower:
            # Avoid false positives for short terms - need word boundary check
            short_terms = ["RSI", "MACD", "KDJ", "BoS", "BOS", "GMT", "BST", 
                          "HMA", "PDT", "TEAL", "teal"]
            if term in short_terms:
                if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                    violations.append(term)
            else:
                violations.append(term)

    # Remove duplicates while preserving order
    seen = set()
    unique_violations = []
    for v in violations:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique_violations.append(v)

    return len(unique_violations) == 0, unique_violations


def validate_green_red_consistency(text: str) -> Tuple[bool, List[str]]:
    """
    Ensure tweets use GREEN/RED terminology consistently.
    Flags any use of old TEAL/purple/VIOLET terms.
    
    Args:
        text: Content to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    old_terms = {
        'TEAL': 'GREEN',
        'teal': 'GREEN', 
        'purple': 'RED',
        'VIOLET': 'RED',
        'violet': 'RED',
        'AMBER': 'CONSIDER',
        'amber': 'CONSIDER',
        '🟣': '🔴',
    }
    
    issues = []
    for old, new in old_terms.items():
        if old in text:
            issues.append(f"Replace '{old}' with '{new}'")
    
    return len(issues) == 0, issues


def log_violations(content_type: str, violations: List[str]) -> None:
    """
    Log warning for any vocabulary violations.

    Args:
        content_type: Description of what was checked (e.g., "Tweet #5", "Newsletter")
        violations: List of banned terms found
    """
    if violations:
        print(f"  ⚠ WARNING: {content_type} contains banned terms: {violations}")


def get_replacement(internal_term: str) -> str:
    """
    Get the approved marketing term for an internal term.

    Args:
        internal_term: The internal/technical term

    Returns:
        The approved marketing replacement, or the original if no mapping exists
    """
    return APPROVED_VOCABULARY.get(internal_term, internal_term)


def validate_all_tweets(tweets: list) -> Tuple[int, int]:
    """
    Validate a list of tweets and log any violations.

    Args:
        tweets: List of tweet objects with 'text' attribute or 'text' key

    Returns:
        Tuple of (total_checked, violation_count)
    """
    total = 0
    violations_found = 0

    for i, tweet in enumerate(tweets):
        # Handle both dict and object
        text = tweet.get('text') if isinstance(tweet, dict) else getattr(tweet, 'text', '')
        tweet_id = tweet.get('id', f'tweet_{i}') if isinstance(tweet, dict) else getattr(tweet, 'id', f'tweet_{i}')

        # Check banned terms
        is_valid, violations = validate_content(text)
        
        # Also check GREEN/RED consistency
        color_valid, color_issues = validate_green_red_consistency(text)
        
        total += 1

        if not is_valid:
            violations_found += 1
            log_violations(f"Tweet {tweet_id}", violations)
        
        if not color_valid:
            violations_found += 1
            print(f"  ⚠ WARNING: Tweet {tweet_id} uses old color terms: {color_issues}")

    return total, violations_found


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════


def validate_output(
    strict: bool = False,
    content_type: str = "output"
) -> Callable:
    """
    Decorator to validate function output for banned marketing terms.

    Args:
        strict: If True, raise ValueError on violations. If False, log warning.
        content_type: Description of content type for logging.

    Usage:
        @validate_output()
        def generate_tweet(ticker: str) -> str:
            return f"Buy ${ticker} using HMA pivot signals!"  # Will warn

        @validate_output(strict=True)
        def generate_newsletter(data: dict) -> str:
            ...  # Will raise if violations found
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Handle different return types
            if isinstance(result, str):
                _check_content(result, func.__name__, strict, content_type)
            elif isinstance(result, list):
                for i, item in enumerate(result):
                    if isinstance(item, str):
                        _check_content(item, f"{func.__name__}[{i}]", strict, content_type)
                    elif isinstance(item, dict) and 'text' in item:
                        _check_content(item['text'], f"{func.__name__}[{i}]", strict, content_type)
            elif isinstance(result, dict):
                if 'text' in result:
                    _check_content(result['text'], func.__name__, strict, content_type)
                if 'content' in result:
                    _check_content(result['content'], func.__name__, strict, content_type)

            return result
        return wrapper
    return decorator


def _check_content(text: str, source: str, strict: bool, content_type: str) -> None:
    """Check content and handle violations."""
    is_valid, violations = validate_content(text)
    if not is_valid:
        message = f"{content_type} from {source} contains banned terms: {violations}"
        if strict:
            raise ValueError(message)
        else:
            print(f"  ⚠ WARNING: {message}")


def validated_content(text: str, content_type: str = "content") -> str:
    """
    Validate content and return it, logging any warnings.

    Args:
        text: Content to validate
        content_type: Description for logging

    Returns:
        The original text (unchanged)

    Example:
        tweet = validated_content(
            generate_tweet_text(),
            content_type="Tweet"
        )
    """
    is_valid, violations = validate_content(text)
    if not is_valid:
        log_violations(content_type, violations)
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT TYPE DEFINITIONS (for tweet_generator.py)
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_TYPES = [
    # Signal announcements
    "buy_signal",
    "sell_signal",
    "consider_spotlight",
    
    # Performance (safeguarded - require 25%+)
    "top_performers",
    "closed_trade",
    "self_quote",
    "beat_spy",
    "early_movers",
    
    # Theme content
    "theme_hot",
    "theme_cold",
    
    # Engagement
    "educational",
    "engagement",
    "power_hour",
    
    # System/funnel
    "funnel_graphic",
    "newsletter",
    "weekly_recap",
    
    # Threads
    "thread_buy_signal",
    "thread_educational",
]

# Categories that were deprecated
DEPRECATED_CONTENT_TYPES = [
    "roth_ira",       # Wrong audience
    "pdt_friendly",   # Wrong audience  
    "position_update", # Renamed to top_performers
    "weekly_wins",    # Merged into top_performers
]


if __name__ == "__main__":
    # Test validation
    print("Testing marketing vocabulary validation (v2.0 - GREEN/RED)...\n")

    test_cases = [
        ("Clean tweet about momentum", True),
        ("Our HMA Pivot signals are strong", False),
        ("Using 20% trailing stop for risk", False),
        ("🟢 GREEN signal on $NVDA", True),
        ("🟢 TEAL signal on $NVDA", False),  # Old term
        ("🔴 RED signal - rotating out", True),
        ("Purple signal means sell", False),  # Old term
        ("UK ISA investors should consider", False),
        ("Roth IRA compounding strategy", False),
        ("The Gatekeeper passed this signal", False),
        ("Cleared all 5 gates - Extremely Bullish", True),
        ("As of Friday's close: $142.50", True),
    ]

    passed = 0
    failed = 0
    
    for text, expected_valid in test_cases:
        is_valid, violations = validate_content(text)
        status = "✓" if is_valid == expected_valid else "✗"
        
        if is_valid == expected_valid:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} '{text[:50]}...'")
        print(f"   Expected: {'valid' if expected_valid else 'invalid'}, Got: {'valid' if is_valid else 'invalid'}")
        if violations:
            print(f"   Violations: {violations}")
        print()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print("✓ Validation tests complete")
