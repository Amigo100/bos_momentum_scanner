#!/usr/bin/env python3
"""
MARKETING VOCABULARY - Centralized Marketing Language Enforcement
=================================================================

This module provides vocabulary validation for all public-facing content
to ensure compliance with MARKETING_GUIDE.md rules.

Usage:
    from marketing_vocabulary import validate_content, APPROVED_VOCABULARY, BANNED_TERMS

    is_valid, violations = validate_content(tweet_text)
    if not is_valid:
        print(f"WARNING: Contains banned terms: {violations}")
"""

from typing import List, Tuple, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# BANNED TERMS - Never use these in public content
# ═══════════════════════════════════════════════════════════════════════════════

BANNED_TERMS: List[str] = [
    # Technical indicators (internal system names)
    "HMA", "Hull Moving Average", "HMA Pivot", "HMA pivot",
    "Banker indicator", "Banker >= 55", "Banker ≥ 55", "Banker >=", "banker indicator",
    "20% trailing stop", "20% stop", "trailing stop",
    "Beta >= 1.5", "Beta ≥ 1.5", "beta threshold", "Beta >=",
    "Break of Structure", "BoS", "BOS", "Weekly BoS", "weekly bos",
    "Tier 1", "Tier 2", "Tier 3", "TIER1", "TIER2", "TIER3",
    "Gatekeeper",
    "Weekly pivot",

    # Specific technical indicators
    "RSI", "MACD", "KDJ",

    # Outdated audience references (UK)
    "UK ISA", "ISA wrapper", "Barclays ISA", "ISA account",
    "UK investor", "UK investors", "UK trader", "UK traders",
    "GMT", "BST", "UK Time", "UK time", "London time",
    "GBP/USD", "sterling",
]

# ═══════════════════════════════════════════════════════════════════════════════
# APPROVED VOCABULARY - Use these instead
# ═══════════════════════════════════════════════════════════════════════════════

APPROVED_VOCABULARY: Dict[str, str] = {
    # Internal term → Marketing term
    "HMA Pivot": "Structural Pivot Confirmation",
    "Banker indicator": "Institutional Accumulation Divergence",
    "Beta >= 1.5": "Volatility Expansion Criteria",
    "20% trailing stop": "Capital Preservation Protocol",
    "Weekly BoS": "Structural Trend Confirmation",
    "Gatekeeper": "The 5th Gate: Forensic Audit",
    "Tier 1/2/3": "Conviction Rating",
    "Theme scoring": "Sector Flow Analysis",
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

    # Signal detection
    "Institutional Accumulation Divergence detected",
    "Structural Pivot Confirmation triggered",
    "Sector Flow Analysis alignment",
    "Forensic Audit cleared",
    "Volatility Expansion Criteria met",

    # Risk management
    "Capital Preservation Protocol activated",
    "Systematic exit discipline",
    "Risk-defined position sizing",
    "The system protects capital so we live to fight another day",
    "No ego, just execution",

    # US investor focus
    "Tax-free compounding in your Roth",
    "No PDT restrictions with weekly timeframes",
    "Beat SPY with systematic momentum",
    "Alpha over indexing",
]

# ═══════════════════════════════════════════════════════════════════════════════
# US AUDIENCE HOOKS - New content angles
# ═══════════════════════════════════════════════════════════════════════════════

US_AUDIENCE_HOOKS: Dict[str, List[str]] = {
    "beat_spy": [
        "Stop indexing. Start selecting.",
        "SPY gives you average returns. We hunt outliers.",
        "The difference between 10% and 40%? Stock selection.",
        "Most portfolios mirror SPY. Ours hunts alpha.",
    ],
    "roth_ira": [
        "Your Roth doesn't have to be boring index funds.",
        "Tax-free compounding on momentum winners.",
        "Systematic momentum + Roth = retirement account on steroids.",
        "30-50% swing trades, zero capital gains tax.",
    ],
    "pdt_friendly": [
        "No PDT worries here. Weekly signals.",
        "Any account size. No $25k minimum required.",
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
        "Sector Flow Analysis shows the shift.",
    ],
}

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
            # Avoid false positives for short terms
            if term in ["RSI", "MACD", "KDJ", "BoS", "BOS", "GMT", "BST"]:
                # These short terms need word boundary check
                import re
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

        is_valid, violations = validate_content(text)
        total += 1

        if not is_valid:
            violations_found += 1
            log_violations(f"Tweet {tweet_id}", violations)

    return total, violations_found


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

import functools
from typing import Callable, Union


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
    # Original types
    "buy_signal",
    "theme_hot",
    "theme_cold",
    "closed_trade",
    "position_update",
    "sell_signal",
    "system_promo",
    "market_insight",
    "educational",
    "engagement",

    # New US-focused types
    "beat_spy",
    "roth_ira",
    "pdt_friendly",
    "power_hour",
    "sector_rotation",
    "funnel_graphic",
    "post_mortem",
    "win_card",
    "alpha_card",
]


if __name__ == "__main__":
    # Test validation
    print("Testing marketing vocabulary validation...\n")

    test_cases = [
        ("Clean tweet about momentum", True),
        ("Our HMA Pivot signals are strong", False),
        ("Using 20% trailing stop for risk", False),
        ("Institutional Accumulation Divergence detected", True),
        ("UK ISA investors should consider", False),
        ("Roth IRA compounding strategy", True),
        ("The Gatekeeper passed this signal", False),
        ("The 5th Gate: Forensic Audit cleared", True),
    ]

    for text, expected_valid in test_cases:
        is_valid, violations = validate_content(text)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} '{text[:50]}...' -> Valid: {is_valid}, Violations: {violations}")

    print("\n✓ Validation tests complete")
