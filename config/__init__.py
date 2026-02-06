"""
CONFIG — Re-exports all settings for backwards compatibility.

All modules can continue using `from config import X` unchanged.
The actual configuration lives in config/settings.py.
Banned terms are in config/banned_terms.py (single source of truth).
"""
from config.settings import *  # noqa: F401,F403

# Banned terms — single source of truth
from config.banned_terms import (  # noqa: F401
    CRITICAL_BANNED,
    BANNED_PHRASES,
    LOSER_PATTERNS,
    ALL_BANNED,
    INTERNAL_TERMINOLOGY_MAP,
    check_banned_phrases,
    check_loser_focus,
)
