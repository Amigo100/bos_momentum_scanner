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
# NOTE TYPE ROTATION MATRIX (v4 — 5-post calendar with companion notes)
#
# Changes from v3:
#   - 5 post days (Tue–Sat) each get explicit COMPANION_NOTE in midday slot.
#     Previously COMPANION_NOTE was a runtime override; now it's in the matrix.
#   - THEME_ROTATION removed (0/week, was 2). Replaced by COMPANION_NOTE.
#   - SIGNAL_TRACKING reduced to 2/week (was 3). Fri morning → PORTFOLIO_UPDATE.
#   - MARKET_SNAPSHOT reduced to 1/week (was 2). Wed midday → COMPANION_NOTE.
#   - Saturday expanded to 3 slots (was 2). WINNER_RECEIPT moved to evening.
#   - COMPANION_NOTE added as explicit type: 5/week (Tue–Sat midday).
# ═══════════════════════════════════════════════════════════════════════════════

NOTE_TYPE_MATRIX = {
    "saturday": [
        {"slot": 1, "type": "ALPHA_SCOREBOARD", "time": "08:30 ET"},
        {"slot": 2, "type": "COMPANION_NOTE", "time": "12:30 ET"},    # Tools & Tech companion
        {"slot": 3, "type": "WINNER_RECEIPT", "time": "17:00 ET"},
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
        {"slot": 1, "type": "CATALYST_WATCH", "time": "08:30 ET"},    # Teases Deep Dive ticker
        {"slot": 2, "type": "COMPANION_NOTE", "time": "12:30 ET"},    # Deep Dive companion
        {"slot": 3, "type": "DATA_INSIGHT", "time": "17:00 ET"},
    ],
    "wednesday": [
        {"slot": 1, "type": "SECTOR_FLOW", "time": "08:30 ET"},       # Previews Sector Watch theme
        {"slot": 2, "type": "COMPANION_NOTE", "time": "12:30 ET"},    # Sector Watch companion
        {"slot": 3, "type": "CATALYST_WATCH", "time": "17:00 ET"},
    ],
    "thursday": [
        {"slot": 1, "type": "SIGNAL_TRACKING", "time": "08:30 ET"},
        {"slot": 2, "type": "COMPANION_NOTE", "time": "12:30 ET"},    # The Edge companion
        {"slot": 3, "type": "READER_QUESTION", "time": "17:00 ET"},
    ],
    "friday": [
        {"slot": 1, "type": "PORTFOLIO_UPDATE", "time": "08:30 ET"},  # Sets up Investor Lessons
        {"slot": 2, "type": "COMPANION_NOTE", "time": "12:30 ET"},    # Investor Lessons companion
        {"slot": 3, "type": "EXIT_DEBRIEF", "time": "17:00 ET"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY TYPE FREQUENCY (for reference / validation)
#
# Type               | Slots/wk | Notes
# -------------------|----------|------
# COMPANION_NOTE     | 5        | Tue–Sat midday (post day companion)
# SIGNAL_TRACKING    | 2        | Mon midday, Thu morning
# CATALYST_WATCH     | 2        | Tue morning, Wed evening
# DATA_INSIGHT       | 2        | Sun morning, Tue evening
# PORTFOLIO_UPDATE   | 2        | Mon evening, Fri morning
# READER_QUESTION    | 2        | Sun midday, Thu evening
# MARKET_SNAPSHOT    | 1        | Mon morning
# ALPHA_SCOREBOARD   | 1        | Sat morning
# WINNER_RECEIPT     | 1        | Sat evening
# SECTOR_FLOW        | 1        | Wed morning
# EXIT_DEBRIEF       | 1        | Fri evening
#
# Removed in v4: THEME_ROTATION (was 2/week, replaced by COMPANION_NOTE)
# Total: 20 slots/week (2 weekend + 3×5 weekday + 1 extra Sat slot)
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
