"""Integration smoke tests — marketing-language compliance.

The banned-terms registry (config/banned_terms.py) is the machine-readable
guard behind CLAUDE.md's MARKETING LANGUAGE RULES; these tests keep it honest.

(QQQ/equity-tracker tests removed 2026-06-11 with portfolio/manager.py;
tweet-system tests archived 2026-06-11 with the twitter system.)
"""

import pytest

from config.banned_terms import ALL_BANNED, INTERNAL_TERM_PATTERNS

class TestCrossCuttingSmoke:
    """Quick smoke tests for cross-module consistency."""

    def test_banned_terms_registry_has_minimum_coverage(self):
        """ALL_BANNED contains at least the critical terms from CLAUDE.md marketing rules."""
        # Use exact forms as they appear in ALL_BANNED (compound forms for indicator names)
        critical_must_have = [
            "HMA", "BoS", "BOS", "Banker indicator", "VWAP", "RSI", "MACD", "KDJ",
            "Gatekeeper", "gatekeeper", "TIER1", "TIER2", "TIER3",
            "UK ISA", "GMT", "BST",
            # Sterling Grid terms
            "Undercurrent", "UC indicator", "ExD", "profit lock",
            "tiered stop", "gear shift", "price cap",
        ]
        all_banned_lower = {t.lower() for t in ALL_BANNED}
        missing = [t for t in critical_must_have if t.lower() not in all_banned_lower]
        assert len(missing) == 0, f"ALL_BANNED is missing critical terms: {missing}"

    def test_internal_term_patterns_catch_critical_banned(self):
        """INTERNAL_TERM_PATTERNS regex list covers key terms from CRITICAL_BANNED."""
        import re

        must_catch = ["HMA", "BoS", "BOS", "Banker", "TIER1", "TIER2", "TIER3",
                       "RSI", "MACD", "KDJ", "gatekeeper", "VWAP",
                       "Undercurrent", "ExD", "profit lock"]
        missed = []

        for term in must_catch:
            test_text = f"The {term} indicator shows strength"
            caught = False
            for pattern in INTERNAL_TERM_PATTERNS:
                if re.search(pattern, test_text, re.IGNORECASE):
                    caught = True
                    break
            if not caught:
                missed.append(term)

        assert len(missed) == 0, f"INTERNAL_TERM_PATTERNS missed: {missed}"


