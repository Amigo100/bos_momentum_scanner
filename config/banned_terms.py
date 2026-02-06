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
"""

import re
from typing import List

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

    # Conviction language (internal score → public)
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
