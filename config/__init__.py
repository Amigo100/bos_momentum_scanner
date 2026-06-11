"""
CONFIG — the lean Sterling system's configuration package.

- config/output_paths.py — the path registry (scanner output, sterling-run, helpers).
- config/banned_terms.py — the marketing-language guard (single source of truth;
  re-exported here so `from config import ALL_BANNED` keeps working).

(config/settings.py — the V8-era tweet/content/threshold settings — was archived
2026-06-11 to archive/cowork-content-system/; the V10 scanner carries its own
thresholds in scanner/sterling_indicators.py.)
"""
from config.banned_terms import (  # noqa: F401
    CRITICAL_BANNED,
    BANNED_PHRASES,
    ALL_BANNED,
    INTERNAL_TERMINOLOGY_MAP,
    INTERNAL_TERM_PATTERNS,
    validate_content,
    check_banned_phrases,
)
