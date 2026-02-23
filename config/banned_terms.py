#!/usr/bin/env python3
"""
Sterling Signals — Banned Terms Registry (Single Source of Truth)

All modules that need to check for banned content should import from here.
Do NOT maintain separate banned term lists anywhere else in the codebase.

Ref: STERLING_SIGNALS_PRD_v2.md section 7.1
Ref: FINTWIT_STYLE_GUIDE.md section "Banned Phrases"

Exports:
    CRITICAL_BANNED          — Terms that must NEVER appear in public content
    BANNED_PHRASES           — Low-quality / vague phrases to reject
    LOSER_PATTERNS           — Regex patterns detecting loser-focused language
    ALL_BANNED               — CRITICAL_BANNED + BANNED_PHRASES combined
    INTERNAL_TERMINOLOGY_MAP — Internal term → public-facing language
    INTERNAL_TERM_PATTERNS   — Regex patterns for internal terms (validation step 5)
    validate_content         — Check text for banned terms, returns (bool, violations)
"""

import re
from typing import List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL_BANNED — Terms that must NEVER appear in any public content
# ═══════════════════════════════════════════════════════════════════════════════
#
# If ANY of these appear in a tweet, newsletter, or Substack note the content
# is blocked. This is the last line of defence before publishing.

CRITICAL_BANNED: List[str] = [
    # ── Internal indicator names ──────────────────────────────────────────────
    "HMA", "Hull Moving Average", "HMA Pivot", "HMA pivot",
    "Banker indicator", "Banker >= 55", "Banker ≥ 55", "Banker >=",
    "Banker rising", "banker rising", "UC rising",
    "banker indicator", "banker score", "VWAP",
    "20% trailing stop", "20% stop",
    "Beta >= 1.5", "Beta ≥ 1.5", "beta threshold", "Beta >=",
    "Break of Structure", "BoS", "BOS", "Weekly BoS", "weekly bos",
    "Weekly pivot",

    # ── Internal system terms ─────────────────────────────────────────────────
    "Gatekeeper", "gatekeeper",
    "thematic gate", "Thematic gate",
    "gate 1", "gate 2", "gate 3", "gate 4", "gate 5",
    "Gate 1", "Gate 2", "Gate 3", "Gate 4", "Gate 5",
    "5-gate", "5th Gate",
    "Tier 1", "Tier 2", "Tier 3", "TIER1", "TIER2", "TIER3",
    "conviction score", "conviction rating",
    "conviction 5", "conviction 4", "conviction 3",
    "Theme scoring",

    # ── Specific technical indicators (never name these publicly) ─────────────
    "RSI", "MACD", "KDJ",

    # ── Old colour system (v2.0 — use GREEN / RED) ───────────────────────────
    "TEAL signal", "TEAL", "teal signal", "teal",
    "purple signal", "purple", "PURPLE",
    "VIOLET signal", "VIOLET", "violet",
    "\U0001f7e3",  # 🟣 old purple emoji
    "AMBER signal", "AMBER", "amber",

    # ── Outdated audience references (UK) ─────────────────────────────────────
    "UK ISA", "ISA wrapper", "Barclays ISA", "ISA account",
    "UK investor", "UK investors", "UK trader", "UK traders",
    "GMT", "BST", "UK Time", "UK time", "London time",
    "GBP/USD",

    # ── Internal terms that leaked (BANNED) ───────────────────────────────────
    "Capital Preservation Protocol",
    "Forensic Audit",
    "Volatility Expansion Criteria",
    # Note: "5th Gate" and "Gate 5" already listed in gate references above

    # ── Non-branded signal terms (use "GREEN signal" instead) ─────────────────
    "proprietary entry", "proprietary signal",
    "PASS signal",

    # ── Sterling Grid internal terms (NEVER reveal publicly) ────────────────
    "Undercurrent", "undercurrent",
    "UC indicator", "UC rising", "UC falling",
    "UC > 0", "UC above zero",
    "RSI(10)", "RSI(14)", "RSI 10", "RSI 14",
    "MACD cross", "MACD crossover", "MACD cross-up",
    "MACD(12,26,9)", "MACD 12 26 9",
    "profit lock", "Profit lock", "tiered stop", "Tiered stop",
    "tiered profit", "Tiered profit",
    "ExD", "ExD exit", "ExD signal",
    "compound exit", "Compound exit",
    "gear shift", "Gear shift", "sizing gear",
    "price cap", "Price cap", "$25 cap",
    "Investment Gate", "investment gate",
    "Deep DD", "deep DD", "Deep dd",
    "STRONG BUY", "SPEC BUY", "NO GO",
    "valuation regime", "Valuation regime",
    "kill switch", "Kill switch",

    # ── Conviction scores 1-10 (internal scale — NEVER use numbers publicly) ─
    "conviction 10", "conviction 9", "conviction 8",
    "conviction 7", "conviction 6",

    # ── US-specific retirement accounts (wrong audience context) ──────────────
    "Roth IRA", "Roth",
    "PDT", "PDT rule", "pattern day trader",
    "401k", "401(k)",
]


# ═══════════════════════════════════════════════════════════════════════════════
# BANNED_PHRASES — Phrases that indicate low-quality / vague content
# ═══════════════════════════════════════════════════════════════════════════════
#
# These come from the FinTwit Style Guide and the reaction-generator QA layer.
# Content containing any of these phrases should be rejected or rewritten.

BANNED_PHRASES: List[str] = [
    # ── Vague system references ───────────────────────────────────────────────
    "theme keeps delivering",
    "system keeps working",
    "the system works",
    "the scanner found",
    "systematic beats emotional",
    "process over outcome",
    "trust the process",
    "quality over quantity",

    # ── Unnamed / unspecific references ────────────────────────────────────────
    "some interesting setups",
    "a few tickers",
    "interesting developments",
    "watching some interesting",

    # ── Loser focus (never dwell on losses) ───────────────────────────────────
    "still bleeding",
    "loser",
    "dragging down",
    "dragging you",

    # ── Generic filler / empty promises ───────────────────────────────────────
    "stay tuned",
    "more to come",
    "keep an eye on",
    "big news coming",
    "stay tuned for something special",
    "you won't believe",

    # ── Overused clichés ──────────────────────────────────────────────────────
    "picks and shovels",
    "2 signals",
    "2 survivors",
]


# ═══════════════════════════════════════════════════════════════════════════════
# LOSER_PATTERNS — Regex patterns that detect loser-focused language
# ═══════════════════════════════════════════════════════════════════════════════

LOSER_PATTERNS: List[str] = [
    r'the red\b',
    r'still bleeding',
    r'keep losing',
    r'\bred position',
    r'stubborn loser',
    r'watching.*lose',
    r'debate the exit',
    r'down.*portfolio',
    r'biggest loser',
]


# ═══════════════════════════════════════════════════════════════════════════════
# ALL_BANNED — Convenience export combining both lists for full validation
# ═══════════════════════════════════════════════════════════════════════════════

ALL_BANNED: List[str] = CRITICAL_BANNED + BANNED_PHRASES


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL_TERMINOLOGY_MAP — Internal term → public-facing equivalent
# ═══════════════════════════════════════════════════════════════════════════════
#
# Use this when transforming scanner output into marketing copy.
# Ref: STERLING_SIGNALS_PRD_v2.md section 3.5, CLAUDE.md marketing rules.

INTERNAL_TERMINOLOGY_MAP = {
    # Scanner signals
    "BoS bullish": "Blue Diamond",
    "BoS bearish": "setup invalidated",
    "HMA bullish pivot": "momentum confirmed",
    "HMA bearish pivot": "bearish signal",

    # Indicators → marketing language
    "Banker >= 55": "institutional accumulation",
    "Banker rising": "institutional accumulation",
    "UC rising": "institutional accumulation",
    "Banker indicator": "strong accumulation",
    "Beta >= 1.5": "volatility characteristics",
    "20% trailing stop": "trailing stop",
    "Weekly BoS": "momentum confirmed",
    "Break of Structure": "structural trend confirmation",
    "HMA Pivot": "momentum confirmed",

    # System references
    "Gatekeeper": "cleared all gates",
    "Tier 1/2/3": "high conviction",
    "Theme scoring": "theme alignment",
    "5-gate pipeline": "proprietary 5-gate screening system",

    # Signal branding (v2.0 — GREEN / RED)
    "TEAL signal": "GREEN signal",
    "VIOLET signal": "RED signal",
    "purple signal": "RED signal",
    "AMBER signal": "CONSIDER signal",
    "PASS signal": "GREEN signal",

    # Sterling Grid terms → public language
    "Undercurrent": "institutional accumulation",
    "UC indicator": "institutional accumulation",
    "UC rising": "institutional accumulation",
    "ExD exit": "structural exit signal",
    "ExD signal": "structural exit signal",
    "profit lock": "trailing stop",
    "tiered stop": "trailing stop",
    "STRONG BUY": "GREEN signal",
    "SPEC BUY": "GREEN signal (speculative)",
    "NO GO": "did not pass screening",
    "Investment Gate": "fundamental screening",
    "Deep DD": "deep analysis",
    "price cap": "price criteria",
    "gear shift": "position sizing",
    "valuation regime": "market conditions",

    # Conviction language (internal score → public)
    "conviction 10": "Extremely Bullish",
    "conviction 9": "Extremely Bullish",
    "conviction 8": "Extremely Bullish",
    "conviction 7": "Bullish",
    "conviction 6": "Watching",
    "conviction 5": "Extremely Bullish",
    "conviction 4": "Bullish",
    "conviction 3": "Watching",
    "conviction 2": "Cautious",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_banned_phrases(text: str) -> List[str]:
    """Scan text for banned phrases. Returns list of violations."""
    issues = []
    text_lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in text_lower:
            issues.append(f"FAIL: banned phrase '{phrase}'")
    return issues


def check_loser_focus(text: str) -> bool:
    """Detect emphasis on losing positions. Returns True if loser-focused."""
    for pattern in LOSER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

# Short terms that need word-boundary checks to avoid false positives
_SHORT_TERMS = frozenset(t.lower() for t in [
    "RSI", "MACD", "KDJ", "BoS", "BOS", "GMT", "BST",
    "HMA", "PDT", "TEAL", "teal", "UC", "ExD",
])


def validate_content(text: str) -> Tuple[bool, List[str]]:
    """
    Check content for banned terms.

    Uses ALL_BANNED (the canonical 121-term list) for maximum coverage.

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

    for term in ALL_BANNED:
        if term.lower() in text_lower:
            # Short terms need word-boundary check to avoid false positives
            if term.lower() in _SHORT_TERMS:
                if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                    violations.append(term)
            else:
                violations.append(term)

    # Remove duplicates while preserving order
    seen: set = set()
    unique_violations: List[str] = []
    for v in violations:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique_violations.append(v)

    return len(unique_violations) == 0, unique_violations


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL TERMINOLOGY PATTERNS (regex, for tweet validation step 5)
# ═══════════════════════════════════════════════════════════════════════════════

INTERNAL_TERM_PATTERNS: List[str] = [
    # Legacy indicator terms
    r"\bHMA\b",
    r"\bBoS\b",
    r"\bBOS\b",
    r"\bBanker\b",
    r"\btier\s*[123]\b",
    r"\bTIER[123]\b",
    r"\bconviction\s*\d+\b",
    r"\bconviction\s+score\b",
    r"\bVWAP\b",
    r"\bgate\s*[1-5]\b",
    r"\b5-gate\b",
    r"\b5th\s+gate\b",
    r"\bgatekeeper\b",
    r"\bRSI\b",
    r"\bMACD\b",
    r"\bKDJ\b",
    # Sterling Grid terms (never reveal publicly)
    r"\bUC\b",
    r"\bundercurrent\b",
    r"\bExD\b",
    r"\bprofit\s+lock\b",
    r"\btiered\s+stop\b",
    r"\bgear\s+shift\b",
    r"\bprice\s+cap\b",
    r"\binvestment\s+gate\b",
    r"\bdeep\s+dd\b",
    r"\bSTRONG\s+BUY\b",
    r"\bSPEC\s+BUY\b",
    r"\bNO\s+GO\b",
    r"\bvaluation\s+regime\b",
    r"\bkill\s+switch\b",
]


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Banned Terms Registry — Self-Test")
    print("=" * 50)
    print(f"CRITICAL_BANNED: {len(CRITICAL_BANNED)} terms")
    print(f"BANNED_PHRASES:  {len(BANNED_PHRASES)} phrases")
    print(f"LOSER_PATTERNS:  {len(LOSER_PATTERNS)} patterns")
    print(f"ALL_BANNED:      {len(ALL_BANNED)} total")
    print(f"TERMINOLOGY_MAP: {len(INTERNAL_TERMINOLOGY_MAP)} mappings")
    print()

    # Check for duplicates
    dupes = [x for x in ALL_BANNED if ALL_BANNED.count(x) > 1]
    if dupes:
        print(f"WARNING: {len(set(dupes))} duplicate terms: {set(dupes)}")
    else:
        print("No duplicates found.")

    # Quick validation spot-check
    test_cases = [
        ("Clean momentum tweet", False),
        ("The HMA Pivot triggered today", True),
        ("Banker >= 55 is strong", True),
        ("Banker rising confirms accumulation", True),
        ("The scanner found some interesting setups", True),
        ("GREEN signal on $NVDA", False),
        ("TEAL signal on $NVDA", True),
        ("stay tuned for something special", True),
    ]

    passed = 0
    for text, expect_banned in test_cases:
        text_lower = text.lower()
        found = any(term.lower() in text_lower for term in ALL_BANNED)
        ok = found == expect_banned
        status = "PASS" if ok else "FAIL"
        if not ok:
            print(f"  {status}: '{text[:50]}' — expected {'banned' if expect_banned else 'clean'}, got {'banned' if found else 'clean'}")
        passed += ok

    print(f"\nSpot-check: {passed}/{len(test_cases)} passed")
    print("Self-test passed." if passed == len(test_cases) else "Self-test FAILED.")
