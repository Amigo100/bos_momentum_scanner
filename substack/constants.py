#!/usr/bin/env python3
"""
Shared constants for the Substack content system.

Extracted from daily_context_builder.py so they remain available after the
Python pipeline is archived and replaced by Cowork scheduled tasks.

Used by:
    - scripts/build_daily_email.py (HANDBOOK_SECTION_MAP, extract_prompt_from_handbook)
    - substack/COWORK_INSTRUCTIONS.md (NOTE_TYPE_MATRIX reference)
"""

import re


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE TYPE ROTATION MATRIX (v3 — 12 archetypes, rebalanced)
#
# Changes from v2:
#   - SIGNAL_TRACKING capped at 3/week (was 5). On no-signal weeks, these
#     pivot to "system selectivity" framing rather than empty updates.
#   - CATALYST_WATCH increased to 2/week (was 1). High-value for engagement.
#   - DATA_INSIGHT increased to 2/week (was 1). Uses equity curve data.
#   - MARKET_SNAPSHOT moved to Monday morning (strongest position for
#     "week ahead" framing) and Wednesday midday (midweek check-in).
#   - Weekend slots diversified: Saturday gets ALPHA_SCOREBOARD (performance
#     after newsletter), Sunday gets DATA_INSIGHT (quieter, reflective).
#
# NOTE: On post days (Tue/Wed/Thu), the midday slot is ALWAYS overridden
# by COMPANION_NOTE from the day's article. The types listed for those
# midday slots are fallbacks for notes-only days (no-post weeks, holidays).
# ═══════════════════════════════════════════════════════════════════════════════

NOTE_TYPE_MATRIX = {
    "saturday": [
        {"slot": 1, "type": "ALPHA_SCOREBOARD", "time": "08:30 ET"},
        {"slot": 2, "type": "WINNER_RECEIPT", "time": "12:30 ET"},
    ],
    "sunday": [
        {"slot": 1, "type": "DATA_INSIGHT", "time": "08:30 ET"},
        {"slot": 2, "type": "READER_QUESTION", "time": "12:30 ET"},
    ],
    "monday": [
        {"slot": 1, "type": "MARKET_SNAPSHOT", "time": "08:30 ET"},
        {"slot": 2, "type": "SIGNAL_TRACKING", "time": "12:30 ET"},
        {"slot": 3, "type": "PORTFOLIO_UPDATE", "time": "17:00 ET"},
    ],
    "tuesday": [
        {"slot": 1, "type": "CATALYST_WATCH", "time": "08:30 ET"},
        {"slot": 2, "type": "THEME_ROTATION", "time": "12:30 ET"},
        {"slot": 3, "type": "DATA_INSIGHT", "time": "17:00 ET"},
    ],
    "wednesday": [
        {"slot": 1, "type": "SECTOR_FLOW", "time": "08:30 ET"},
        {"slot": 2, "type": "MARKET_SNAPSHOT", "time": "12:30 ET"},
        {"slot": 3, "type": "CATALYST_WATCH", "time": "17:00 ET"},
    ],
    "thursday": [
        {"slot": 1, "type": "SIGNAL_TRACKING", "time": "08:30 ET"},
        {"slot": 2, "type": "THEME_ROTATION", "time": "12:30 ET"},
        {"slot": 3, "type": "READER_QUESTION", "time": "17:00 ET"},
    ],
    "friday": [
        {"slot": 1, "type": "SIGNAL_TRACKING", "time": "08:30 ET"},
        {"slot": 2, "type": "PORTFOLIO_UPDATE", "time": "12:30 ET"},
        {"slot": 3, "type": "EXIT_DEBRIEF", "time": "17:00 ET"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY TYPE FREQUENCY (for reference / validation)
#
# Type               | Slots/wk | Notes
# -------------------|----------|------
# SIGNAL_TRACKING    | 3        | Mon midday, Thu morning, Fri morning
# MARKET_SNAPSHOT    | 2        | Mon morning, Wed midday*
# CATALYST_WATCH     | 2        | Tue morning, Wed evening
# THEME_ROTATION     | 2        | Tue midday*, Thu midday*
# DATA_INSIGHT       | 2        | Sun morning, Tue evening
# PORTFOLIO_UPDATE   | 2        | Mon evening, Fri midday
# READER_QUESTION    | 2        | Sun midday, Thu evening
# ALPHA_SCOREBOARD   | 1        | Sat morning
# WINNER_RECEIPT     | 1        | Sat midday
# SECTOR_FLOW        | 1        | Wed morning
# EXIT_DEBRIEF       | 1        | Fri evening
#
# * = overridden by COMPANION_NOTE on post days
# Total: 19 slots/week (2 weekend + 3×5 weekday)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# HANDBOOK PROMPT SECTION HEADERS
# ═══════════════════════════════════════════════════════════════════════════════

HANDBOOK_SECTION_MAP = {
    "ticker_deep_dive": "## Deep Dive (3 Prompts)",
    "educational": "## The Edge — Educational (3 Prompts)",
    "theme_rotation": "## Sector Watch (2 Prompts)",
    "performance_review": "## Performance Review — FALLBACK ONLY",
    "trade_alert_entry": "## 🟢 GREEN Signal — Trade Alert Entry (1 Prompt)",
    "trade_alert_exit": "## Position Update — Trade Alert Exit (1 Prompt)",
    "daily_notes": "## Companion Note Strategy",
}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════


def extract_prompt_from_handbook(handbook_text: str, section_header: str) -> str:
    """Extract all prompt text from a handbook section.

    For multi-prompt sections (e.g. Deep Dive has 3 prompts), extracts
    ALL code-fenced blocks and joins them with numbered dividers.
    Single-prompt sections return the prompt text directly.
    """
    # Find the section start
    idx = handbook_text.find(section_header)
    if idx == -1:
        return ""

    # Get text from section start to next ## header (or end)
    section_text = handbook_text[idx + len(section_header):]
    next_section = re.search(r'\n## ', section_text)
    if next_section:
        section_text = section_text[:next_section.start()]

    # Extract ALL code-fenced prompts
    prompts = re.findall(r'```\n(.*?)```', section_text, re.DOTALL)
    if not prompts:
        return ""

    if len(prompts) == 1:
        return prompts[0].strip()

    # Multi-prompt: join with numbered dividers
    parts = []
    for i, prompt in enumerate(prompts, 1):
        parts.append(f"═══ PROMPT {i} OF {len(prompts)} ═══\n\n{prompt.strip()}")
    return "\n\n".join(parts)
