#!/usr/bin/env python3
"""
Shared constants for the Substack content system.

Extracted from daily_context_builder.py so they remain available after the
Python pipeline is archived and replaced by Cowork scheduled tasks.

Used by:
    - scripts/build_daily_email.py (HANDBOOK_SECTION_MAP, extract_prompt_from_handbook)
    - scripts/fallback_content_generator.py (NOTE_TYPE_MATRIX)
    - substack/COWORK_INSTRUCTIONS.md (NOTE_TYPE_MATRIX reference)
"""

import re


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE TYPE ROTATION MATRIX (v8 — 5-type system, AEDT timezone)
#
# Changes from v4:
#   - 11 types collapsed to 5: SCANNER, POSITION, MARKET, EDUCATION, PROMO
#   - Timezone changed from ET to AEDT (Australia/Sydney)
#   - Time slots: 08:00 / 12:00 / 20:00 AEDT
#   - Saturday and Sunday: 2 slots (no evening). Weekdays: 3 slots.
#   - 19 notes/week (was 20).
# ═══════════════════════════════════════════════════════════════════════════════

NOTE_TYPE_MATRIX = {
    "saturday": [
        {"slot": 1, "type": "PROMO", "time": "08:00 AEDT"},       # briefing
        {"slot": 2, "type": "SCANNER", "time": "12:00 AEDT"},     # visual card
    ],
    "sunday": [
        {"slot": 1, "type": "EDUCATION", "time": "08:00 AEDT"},
        {"slot": 2, "type": "MARKET", "time": "12:00 AEDT"},
    ],
    "monday": [
        {"slot": 1, "type": "POSITION", "time": "08:00 AEDT"},
        {"slot": 2, "type": "MARKET", "time": "12:00 AEDT"},
        {"slot": 3, "type": "EDUCATION", "time": "20:00 AEDT"},
    ],
    "tuesday": [
        {"slot": 1, "type": "SCANNER", "time": "08:00 AEDT"},
        {"slot": 2, "type": "POSITION", "time": "12:00 AEDT"},
        {"slot": 3, "type": "PROMO", "time": "20:00 AEDT"},       # deep dive
    ],
    "wednesday": [
        {"slot": 1, "type": "MARKET", "time": "08:00 AEDT"},
        {"slot": 2, "type": "EDUCATION", "time": "12:00 AEDT"},
        {"slot": 3, "type": "SCANNER", "time": "20:00 AEDT"},
    ],
    "thursday": [
        {"slot": 1, "type": "POSITION", "time": "08:00 AEDT"},
        {"slot": 2, "type": "MARKET", "time": "12:00 AEDT"},
        {"slot": 3, "type": "PROMO", "time": "20:00 AEDT"},       # education
    ],
    "friday": [
        {"slot": 1, "type": "EDUCATION", "time": "08:00 AEDT"},
        {"slot": 2, "type": "POSITION", "time": "12:00 AEDT"},
        {"slot": 3, "type": "SCANNER", "time": "20:00 AEDT"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY TYPE FREQUENCY (for reference / validation)
#
# Type       | Slots/wk | Sub-variants
# -----------|----------|-------------------------------------------
# SCANNER    | 4        | weekly_funnel, rejection_story, signal_count
# POSITION   | 4        | portfolio_alpha, single_winner, honest_loser
# MARKET     | 4        | event_impact, force_connection, catalyst_flag
# EDUCATION  | 4        | research_finding, methodology_insight, investing_concept
# PROMO      | 3        | briefing_announce, deep_dive_hook, education_preview
#
# Total: 19 slots/week (2 weekend + 3×5 weekday)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# HANDBOOK PROMPT SECTION HEADERS (v7)
# ═══════════════════════════════════════════════════════════════════════════════

HANDBOOK_SECTION_MAP = {
    "tuesday_deep_dive": "## Tuesday Deep Dive",
    "thursday_education": "## Thursday Education",
    "ad_hoc": "## Ad-Hoc Prompts",
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
