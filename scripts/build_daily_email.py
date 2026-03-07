#!/usr/bin/env python3
"""
Build and send the daily Sterling Signals content email.

Reads the daily context document and content prompt handbook, identifies
today's content category and topic, assembles the correct prompts, and
sends a mobile-friendly HTML email via SMTP. Zero LLM cost.

The email embeds context data directly into the post prompt so the user
can copy-paste a single self-contained block into Claude.ai — no file
attachment or git pull required. Designed for phone use.

Usage:
    python3 -m scripts.build_daily_email                     # Today
    python3 -m scripts.build_daily_email --date 2026-03-01   # Override date
    python3 -m scripts.build_daily_email --skip-email         # Local only
    python3 -m scripts.build_daily_email --dry-run            # Print + save, no email
"""

import argparse
import html as html_module
import json
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, Tuple

from config.output_paths import SUBSTACK_OUTPUT, BASE_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

CONTEXT_DOC_PATH = SUBSTACK_OUTPUT / "current" / "daily_context.md"
CONTENT_SCHEDULE_PATH = SUBSTACK_OUTPUT / "current" / "content_schedule.json"
DAILY_EMAIL_OUTPUT = SUBSTACK_OUTPUT / "current" / "daily_email.html"
HANDBOOK_DIR = BASE_DIR / "substack" / "docs"


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════════

# Maps category names (title case and UPPER_SNAKE_CASE) to handbook prompt keys.
# Mirrors HANDBOOK_SECTION_MAP from daily_context_builder.py:148 — redefined
# locally to avoid importing the heavy daily_context_builder module.
CATEGORY_TO_PROMPT_KEY = {
    "Deep Dive": "ticker_deep_dive",
    "Ticker Deep Dive": "ticker_deep_dive",       # backwards compat (v6)
    "TICKER_DEEP_DIVE": "ticker_deep_dive",
    "The Edge": "educational",
    "Educational": "educational",                   # backwards compat (v6)
    "EDUCATIONAL": "educational",
    "Sector Watch": "theme_rotation",
    "Theme Rotation": "theme_rotation",             # backwards compat (v6)
    "THEME_ROTATION": "theme_rotation",
    "Performance Review": "performance_review",
    "PERFORMANCE_REVIEW": "performance_review",
    "NOTES_ONLY": None,
}

HANDBOOK_SECTION_MAP = {
    "ticker_deep_dive": "## Deep Dive (3 Prompts)",
    "educational": "## The Edge — Educational (3 Prompts)",
    "theme_rotation": "## Sector Watch (2 Prompts)",
    "performance_review": "## Performance Review — FALLBACK ONLY",
    "trade_alert_entry": "## 🟢 GREEN Signal — Trade Alert Entry (1 Prompt)",
    "trade_alert_exit": "## Position Update — Trade Alert Exit (1 Prompt)",
    "daily_notes": "## Companion Note Strategy",
}

# Normalise UPPER_SNAKE_CASE to title case for display
CATEGORY_DISPLAY = {
    "TICKER_DEEP_DIVE": "Deep Dive",
    "EDUCATIONAL": "The Edge",
    "THEME_ROTATION": "Sector Watch",
    "PERFORMANCE_REVIEW": "Performance Review",
    "NOTES_ONLY": "Notes Only",
}


def normalise_category(cat: str) -> str:
    """Return display-friendly category name."""
    if not cat:
        return ""
    return CATEGORY_DISPLAY.get(cat, cat)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: PARSE TODAY'S ASSIGNMENT FROM daily_context.md
# ═══════════════════════════════════════════════════════════════════════════════

def parse_today_assignment(
    context_path: Path, target_date: Optional[date] = None
) -> Dict:
    """Parse the ## TODAY'S POST section from daily_context.md.

    Returns dict with keys:
        day         - Day name (e.g. "Monday")
        date_str    - Date string from header (e.g. "March 02, 2026")
        category    - Category name (e.g. "Ticker Deep Dive") or None
        topic       - Topic string or None
        html_theme  - "Editorial (light)" or "Dashboard (dark)" or None
        reason      - Why this topic or None
        is_post_day - True if a post is assigned
        is_notes_only - True if notes-only day
    """
    if not context_path.exists():
        return {
            "day": None,
            "date_str": None,
            "category": None,
            "topic": None,
            "html_theme": None,
            "reason": None,
            "is_post_day": False,
            "is_notes_only": False,
        }

    text = context_path.read_text()

    # Extract day and date from document header
    # Format: # Sterling Signals — Monday March 02, 2026
    header_match = re.search(
        r"^# Sterling Signals\s*[—–-]\s*(\w+)\s+(.+?)$", text, re.MULTILINE
    )
    day_name = header_match.group(1) if header_match else None
    date_str = header_match.group(2).strip() if header_match else None

    # If --date was provided and doesn't match context doc, return empty
    if target_date and date_str:
        try:
            doc_date = datetime.strptime(date_str, "%B %d, %Y").date()
            if doc_date != target_date:
                # Context doc is for a different date — use content_schedule.json
                # instead (handled by caller)
                return {
                    "day": day_name,
                    "date_str": date_str,
                    "category": None,
                    "topic": None,
                    "html_theme": None,
                    "reason": None,
                    "is_post_day": False,
                    "is_notes_only": False,
                    "_date_mismatch": True,
                }
        except ValueError:
            pass

    # Find ## TODAY'S POST section
    post_section_match = re.search(
        r"## TODAY'S POST\n(.*?)(?=\n---|\n## )", text, re.DOTALL
    )
    if not post_section_match:
        return {
            "day": day_name,
            "date_str": date_str,
            "category": None,
            "topic": None,
            "html_theme": None,
            "reason": None,
            "is_post_day": False,
            "is_notes_only": False,
        }

    section = post_section_match.group(1)

    # Check notes-only pattern
    if "No long-form post today" in section:
        return {
            "day": day_name,
            "date_str": date_str,
            "category": None,
            "topic": None,
            "html_theme": None,
            "reason": None,
            "is_post_day": False,
            "is_notes_only": True,
        }

    # Parse post-day fields
    # Format:
    #   **Category:** Ticker Deep Dive
    #   **Topic:** Deep Dive — $RCAT
    #   **Theme:** Editorial (light)
    #   **Why this topic:** Highest conviction new signal
    category_match = re.search(r"\*\*Category:\*\*\s*(.+)", section)
    topic_match = re.search(r"\*\*Topic:\*\*\s*(.+)", section)
    theme_match = re.search(r"\*\*Theme:\*\*\s*(.+)", section)
    reason_match = re.search(r"\*\*Why this topic:\*\*\s*(.+)", section)

    category = category_match.group(1).strip() if category_match else None
    topic = topic_match.group(1).strip() if topic_match else None
    html_theme = theme_match.group(1).strip() if theme_match else None
    reason = reason_match.group(1).strip() if reason_match else None

    return {
        "day": day_name,
        "date_str": date_str,
        "category": category,
        "topic": topic,
        "html_theme": html_theme,
        "reason": reason,
        "is_post_day": category is not None,
        "is_notes_only": False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: LOAD HANDBOOK PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

def _handbook_version_key(path: Path) -> tuple:
    """Extract version number for sorting. v6.2 -> (6, 2), v6 -> (6, 0)."""
    match = re.search(r'_v(\d+(?:\.\d+)*)', path.stem)
    if match:
        return tuple(int(p) for p in match.group(1).split('.'))
    return (0,)


def find_handbook_path() -> Optional[Path]:
    """Find the newest content prompt handbook in the repo."""
    if not HANDBOOK_DIR.exists():
        return None

    # Find all handbook versions sorted by version number (highest first)
    handbooks = sorted(
        HANDBOOK_DIR.glob("content_prompt_handbook*.md"),
        key=_handbook_version_key,
        reverse=True,
    )
    for p in handbooks:
        if p.exists():
            return p
    return None


def extract_prompt_from_handbook(handbook_text: str, section_header: str) -> str:
    """Extract all prompt text from a handbook section.

    For multi-prompt sections (e.g. Deep Dive has 3 prompts), extracts
    ALL code-fenced blocks and joins them with numbered dividers.
    Single-prompt sections return the prompt text directly.
    """
    idx = handbook_text.find(section_header)
    if idx == -1:
        return ""

    section_text = handbook_text[idx + len(section_header):]
    next_section = re.search(r"\n## ", section_text)
    if next_section:
        section_text = section_text[: next_section.start()]

    # Extract ALL code-fenced prompts
    prompts = re.findall(r"```\n(.*?)```", section_text, re.DOTALL)
    if not prompts:
        return ""

    if len(prompts) == 1:
        return prompts[0].strip()

    # Multi-prompt: join with numbered dividers
    parts = []
    for i, prompt in enumerate(prompts, 1):
        parts.append(f"═══ PROMPT {i} OF {len(prompts)} ═══\n\n{prompt.strip()}")
    return "\n\n".join(parts)


def load_handbook_prompts() -> Dict[str, str]:
    """Load all prompts from the content prompt handbook.

    Returns dict mapping prompt_key -> prompt text.
    Keys: ticker_deep_dive, educational, theme_rotation, performance_review,
          trade_alert_entry, trade_alert_exit, daily_notes
    """
    handbook_path = find_handbook_path()
    if not handbook_path:
        return {}

    handbook_text = handbook_path.read_text()
    prompts = {}

    for key, section_header in HANDBOOK_SECTION_MAP.items():
        text = extract_prompt_from_handbook(handbook_text, section_header)
        if text:
            prompts[key] = text

    return prompts


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: LOAD TOMORROW PREVIEW (for Saturday emails)
# ═══════════════════════════════════════════════════════════════════════════════

def load_tomorrow_preview(
    schedule_path: Path, today_day: str
) -> Optional[Dict]:
    """Load tomorrow's assignment from content_schedule.json.

    Used for Saturday emails to show what's coming on Sunday.
    Returns dict with {day, category, topic} or None.
    """
    if not schedule_path.exists():
        return None

    try:
        data = json.loads(schedule_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    schedule = data.get("schedule", [])
    if not schedule:
        return None

    # Day ordering for "tomorrow" lookup
    day_order = [
        "Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday",
    ]

    today_lower = (today_day or "").lower()
    today_idx = None
    for i, d in enumerate(day_order):
        if d.lower() == today_lower:
            today_idx = i
            break

    if today_idx is None:
        return None

    tomorrow_day = day_order[(today_idx + 1) % 7]

    for entry in schedule:
        if entry.get("day", "").lower() == tomorrow_day.lower():
            return {
                "day": entry.get("day", tomorrow_day),
                "category": entry.get("category", ""),
                "topic": entry.get("topic", ""),
            }

    return None


def load_schedule_for_date(
    schedule_path: Path, target_date: date
) -> Optional[Dict]:
    """Load assignment for a specific date from content_schedule.json.

    Used when --date flag targets a different date than the context doc.
    Returns dict with {day, category, topic} or None.
    """
    if not schedule_path.exists():
        return None

    try:
        data = json.loads(schedule_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    schedule = data.get("schedule", [])
    target_day = target_date.strftime("%A")  # e.g. "Monday"

    for entry in schedule:
        if entry.get("day", "").lower() == target_day.lower():
            category = entry.get("category", "")
            topic = entry.get("topic", "")
            is_notes_only = category == "NOTES_ONLY"
            return {
                "day": target_day,
                "date_str": target_date.strftime("%B %d, %Y"),
                "category": None if is_notes_only else category,
                "topic": None if is_notes_only else topic,
                "html_theme": None,
                "reason": None,
                "is_post_day": not is_notes_only and category != "",
                "is_notes_only": is_notes_only,
            }

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: RENDER EMAIL HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _escape(text: str) -> str:
    """HTML-escape text for safe embedding."""
    return html_module.escape(text)


def _prompt_block(block_id: str, prompt_text: str) -> str:
    """Render a mobile-friendly prompt text block.

    No JavaScript — email clients strip it. Uses a styled <pre> block
    that can be long-pressed on mobile to select-all and copy.
    """
    return f"""<p style="
        font-size: 13px;
        color: #6B7280;
        margin: 0 0 6px 0;
    ">Long-press the text below to select all, then copy:</p>
    <pre id="{block_id}" style="
        background: #F3F4F6;
        border: 2px solid #2563EB;
        border-radius: 8px;
        padding: 16px;
        font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-wrap: break-word;
        color: #1F2937;
        -webkit-user-select: all;
        user-select: all;
    ">{_escape(prompt_text)}</pre>"""


def _trade_alert_section(prompts: Dict[str, str]) -> str:
    """Render Trade Alert prompts section (no <details> — Gmail strips it)."""
    entry_prompt = prompts.get("trade_alert_entry", "")
    exit_prompt = prompts.get("trade_alert_exit", "")

    if not entry_prompt and not exit_prompt:
        return ""

    sections = []
    if entry_prompt:
        sections.append(f"""<p style="font-weight: 600; margin-top: 12px;">Trade Alert — Entry</p>
        <p style="color: #6B7280; font-size: 13px;">Replace {{TICKER}} with the ticker symbol.</p>
        {_prompt_block("trade_entry_prompt", entry_prompt)}""")

    if exit_prompt:
        sections.append(f"""<p style="font-weight: 600; margin-top: 12px;">Trade Alert — Exit</p>
        <p style="color: #6B7280; font-size: 13px;">Replace {{TICKER}} with the ticker symbol.</p>
        {_prompt_block("trade_exit_prompt", exit_prompt)}""")

    return f"""
    <div style="margin-top: 24px; border-top: 1px solid #E5E7EB; padding-top: 16px;">
        <h3 style="font-size: 14px; color: #4B5563; margin: 0 0 8px 0;">
            Trade Alert Prompts (Entry / Exit)
        </h3>
        {''.join(sections)}
    </div>"""


def _load_context_doc(context_path: Path) -> str:
    """Load the full daily_context.md content for embedding into prompts.

    Returns the raw markdown text, or an empty string if file not found.
    """
    if not context_path.exists():
        return ""
    try:
        return context_path.read_text()
    except OSError:
        return ""


def _extract_notes_context(context_text: str) -> str:
    """Extract a shorter context excerpt for the notes prompt.

    Includes: PORTFOLIO SNAPSHOT + TODAY'S NOTES sections only (~3KB).
    """
    if not context_text:
        return ""

    sections = []

    # Extract PORTFOLIO SNAPSHOT
    portfolio_match = re.search(
        r"(## PORTFOLIO SNAPSHOT.*?)(?=\n## )", context_text, re.DOTALL
    )
    if portfolio_match:
        sections.append(portfolio_match.group(1).strip())

    # Extract TODAY'S NOTES
    notes_match = re.search(
        r"(## TODAY'S NOTES.*?)(?=\n## |\Z)", context_text, re.DOTALL
    )
    if notes_match:
        sections.append(notes_match.group(1).strip())

    # Extract MARKET CONTEXT (first 500 chars only)
    market_match = re.search(
        r"(## MARKET CONTEXT.*?)(?=\n## )", context_text, re.DOTALL
    )
    if market_match:
        market_text = market_match.group(1).strip()
        if len(market_text) > 500:
            market_text = market_text[:500] + "\n[... truncated for notes ...]"
        sections.append(market_text)

    return "\n\n".join(sections)


def _build_self_contained_prompt(prompt_text: str, context_text: str) -> str:
    """Combine context data + prompt into one self-contained block.

    The user copies this single block into Claude.ai — no file attachment needed.
    """
    if not context_text:
        return prompt_text

    return (
        "I have the following context data for Sterling Signals. "
        "Use this data for portfolio, themes, signals, and marketing rules.\n\n"
        "--- BEGIN CONTEXT DATA ---\n"
        f"{context_text}\n"
        "--- END CONTEXT DATA ---\n\n"
        f"{prompt_text}"
    )


def _quick_start_card(category: str, topic: str, is_post_day: bool) -> str:
    """Render the green Quick Start card at the top of the email."""
    if is_post_day:
        return f"""
    <div style="
        background: #16A34A;
        color: white;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    ">
        <p style="font-weight: 700; margin: 0 0 8px 0; font-size: 16px;">
            Today: {_escape(category)} — {_escape(topic or 'See prompt')}
        </p>
        <ol style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8;">
            <li>Copy the <strong>POST PROMPT</strong> below (includes all context data)</li>
            <li>Open Claude.ai &rarr; paste &rarr; send</li>
            <li>Copy the <strong>NOTES PROMPT</strong> &rarr; paste &rarr; send</li>
            <li>Take HTML outputs &rarr; paste into Substack</li>
        </ol>
    </div>"""
    else:
        return f"""
    <div style="
        background: #2563EB;
        color: white;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    ">
        <p style="font-weight: 700; margin: 0 0 8px 0; font-size: 16px;">
            Notes Only Today
        </p>
        <ol style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8;">
            <li>Copy the <strong>NOTES PROMPT</strong> below</li>
            <li>Open Claude.ai &rarr; paste &rarr; send</li>
            <li>Take 3 HTML notes &rarr; paste into Substack Notes</li>
        </ol>
    </div>"""


def _html_to_plain_text(subject: str, html: str) -> str:
    """Convert HTML email to plain-text fallback for MIME alternative part."""
    # Strip HTML tags
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return f"Subject: {subject}\n\n{text.strip()}"


def _email_wrapper(subject: str, body_html: str) -> str:
    """Wrap body HTML in the full email template."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape(subject)}</title>
</head>
<body style="
    margin: 0;
    padding: 0;
    background: #F9FAFB;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    color: #1F2937;
    line-height: 1.6;
">
    <div style="
        max-width: 640px;
        margin: 0 auto;
        padding: 24px 16px;
    ">
        {body_html}
        <p style="
            text-align: center;
            color: #9CA3AF;
            font-size: 12px;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #E5E7EB;
        ">Sterling Signals Daily Content Email &mdash; generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
</body>
</html>"""


def render_post_day_email(
    assignment: Dict,
    post_prompt: str,
    notes_prompt: str,
    prompts: Dict[str, str],
    context_doc_path: Path,
) -> Tuple[str, str]:
    """Render email for a post day. Returns (subject, html).

    The post prompt includes the full daily_context.md embedded inline,
    so the user can copy one self-contained block into Claude.ai without
    needing to attach a file.
    """
    day = assignment.get("day", "Today")
    date_str = assignment.get("date_str", "")
    category = normalise_category(assignment.get("category", "Unknown"))
    topic = assignment.get("topic", "")
    html_theme = assignment.get("html_theme", "")

    subject = f"POST DAY: {category} — {topic}" if topic else f"POST DAY: {category}"

    # Load context data and build self-contained prompts
    context_text = _load_context_doc(context_doc_path)
    full_post_prompt = _build_self_contained_prompt(post_prompt, context_text)
    notes_context = _extract_notes_context(context_text)
    full_notes_prompt = _build_self_contained_prompt(notes_prompt, notes_context)

    body = f"""
    {_quick_start_card(category, topic, is_post_day=True)}

    <div style="
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        border: 1px solid #E5E7EB;
    ">
        <h1 style="margin: 0 0 4px 0; font-size: 22px; color: #111827;">
            {_escape(day)}, {_escape(date_str)}
        </h1>
        <p style="margin: 0 0 4px 0; font-size: 16px;">
            <strong>Category:</strong> {_escape(category)}
        </p>
        <p style="margin: 0 0 4px 0; font-size: 16px;">
            <strong>Topic:</strong> {_escape(topic or 'See prompt')}
        </p>
        {f'<p style="margin: 0 0 4px 0; font-size: 14px; color: #6B7280;"><strong>Theme:</strong> {_escape(html_theme)}</p>' if html_theme else ''}
    </div>

    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; color: #111827; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.05em;">
            Post Prompt (includes context data)
        </h2>
        <p style="font-size: 13px; color: #6B7280; margin: 0 0 4px 0;">
            This prompt is self-contained — no file attachment needed.
        </p>
        {_prompt_block("post_prompt", full_post_prompt)}
    </div>

    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; color: #111827; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.05em;">
            Notes Prompt
        </h2>
        {_prompt_block("notes_prompt", full_notes_prompt)}
    </div>

    {_trade_alert_section(prompts)}
    """

    return subject, _email_wrapper(subject, body)


def render_notes_only_email(
    assignment: Dict,
    notes_prompt: str,
    prompts: Dict[str, str],
    tomorrow: Optional[Dict],
    context_doc_path: Path,
) -> Tuple[str, str]:
    """Render email for a notes-only day. Returns (subject, html).

    Notes prompt includes a shorter context excerpt (portfolio + notes schedule).
    """
    day = assignment.get("day", "Today")
    date_str = assignment.get("date_str", "")

    subject = f"NOTES ONLY — {day}"

    # Load context and build self-contained notes prompt
    context_text = _load_context_doc(context_doc_path)
    notes_context = _extract_notes_context(context_text)
    full_notes_prompt = _build_self_contained_prompt(notes_prompt, notes_context)

    tomorrow_html = ""
    if tomorrow:
        t_cat = tomorrow.get("category", "")
        t_topic = tomorrow.get("topic", "")
        t_cat_display = normalise_category(t_cat)
        tomorrow_html = f"""
    <div style="
        background: #F0FDF4;
        border-radius: 8px;
        padding: 16px;
        margin-top: 24px;
        border-left: 4px solid #22C55E;
    ">
        <p style="font-weight: 600; margin: 0 0 4px 0;">Tomorrow: {_escape(tomorrow.get('day', ''))}</p>
        <p style="margin: 0; font-size: 14px; color: #374151;">
            {_escape(t_cat_display)}{(' — ' + _escape(t_topic)) if t_topic else ''}
        </p>
    </div>"""

    body = f"""
    {_quick_start_card("", "", is_post_day=False)}

    <div style="
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        border: 1px solid #E5E7EB;
    ">
        <h1 style="margin: 0 0 4px 0; font-size: 22px; color: #111827;">
            {_escape(day)}, {_escape(date_str)}
        </h1>
        <p style="margin: 0; font-size: 16px; color: #6B7280;">
            Notes only &mdash; no long-form post today.
        </p>
    </div>

    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; color: #111827; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.05em;">
            Notes Prompt (includes context data)
        </h2>
        {_prompt_block("notes_prompt", full_notes_prompt)}
    </div>

    {tomorrow_html}

    {_trade_alert_section(prompts)}
    """

    return subject, _email_wrapper(subject, body)


def render_no_assignment_email(
    notes_prompt: str,
) -> Tuple[str, str]:
    """Render email when no assignment can be determined. Returns (subject, html)."""
    subject = "Sterling Signals — No content schedule found"

    body = f"""
    <div style="
        background: #FFFBEB;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        border: 1px solid #FDE68A;
    ">
        <h1 style="margin: 0 0 8px 0; font-size: 20px; color: #92400E;">
            No Content Assignment Found
        </h1>
        <p style="margin: 0 0 12px 0; font-size: 14px; color: #78350F;">
            Could not find today's assignment in the content schedule.
            The daily context document may need to be regenerated.
        </p>
        <p style="margin: 0; font-size: 13px;">
            <strong>Run:</strong>
            <code style="background: #FEF3C7; padding: 2px 6px; border-radius: 3px;">python3 -m substack.daily_content_pipeline</code>
        </p>
    </div>

    <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; color: #111827; margin: 0 0 4px 0;">
            Manual Fallback &mdash; Notes Prompt
        </h2>
        <p style="font-size: 14px; color: #6B7280; margin: 0 0 8px 0;">
            You can still generate today's notes using this universal prompt:
        </p>
        {_prompt_block("notes_prompt", notes_prompt) if notes_prompt else '<p style="color: #EF4444;">Notes prompt not found in handbook.</p>'}
    </div>
    """

    return subject, _email_wrapper(subject, body)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: SAVE AND SEND
# ═══════════════════════════════════════════════════════════════════════════════

def save_email(html: str, output_path: Path = DAILY_EMAIL_OUTPUT) -> Path:
    """Save email HTML locally."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


def send_email(html: str, subject: str, skip: bool = False) -> bool:
    """Send via SMTP (Gmail/Outlook/etc). Reuses notifications.py config.

    Uses the same env vars already configured in CI:
        SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD, NOTIFICATION_EMAIL
    Falls back to email_config.json for local development.
    """
    if skip:
        print("  ⚠ Email sending skipped (--skip-email)")
        return False

    try:
        from utils.notifications import _load_email_config
    except ImportError:
        print("  ⚠ utils.notifications not available — email not sent")
        return False

    config = _load_email_config()
    if not config:
        print("  ⚠ SMTP not configured — email not sent")
        print("    Set SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD, NOTIFICATION_EMAIL")
        return False

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    plain_text = _html_to_plain_text(subject, html)

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from_email"]
        msg["To"] = ", ".join(config["recipients"])
        msg["Subject"] = subject

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(
                config["from_email"], config["recipients"], msg.as_string()
            )

        print(f"  ✓ Email sent to {len(config['recipients'])} recipient(s)")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"  ✗ SMTP auth failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Email send failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Build and send the daily content email."""
    parser = argparse.ArgumentParser(
        description="Build daily Sterling Signals content email"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override date (YYYY-MM-DD format, e.g. 2026-03-01)",
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Save locally but do not send email",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print subject line and save locally, no email",
    )
    args = parser.parse_args()

    skip_email = args.skip_email or args.dry_run
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"  ✗ Invalid date format: {args.date} (use YYYY-MM-DD)")
            return 2

    print("=" * 60)
    print("  DAILY CONTENT EMAIL BUILDER")
    print("=" * 60)

    # ── Auto-initialize content tracker for current week ─────────────────────
    from scripts.content_tracker import ensure_current_week
    ensure_current_week(target_date)

    # ── Step 1: Load handbook prompts ────────────────────────────────────────
    print("\n  Step 1: Loading handbook prompts...")
    prompts = load_handbook_prompts()
    if not prompts:
        print("  ✗ FATAL: Could not find content_prompt_handbook in repo")
        return 2
    print(f"  ✓ Loaded {len(prompts)} prompts from handbook")

    notes_prompt = prompts.get("daily_notes", "")

    # ── Step 2: Parse today's assignment ─────────────────────────────────────
    print("\n  Step 2: Parsing today's assignment...")

    context_path = CONTEXT_DOC_PATH
    assignment = parse_today_assignment(context_path, target_date)

    # If --date was used and doesn't match context doc, try content_schedule.json
    if assignment.get("_date_mismatch") and target_date:
        print(f"  ⚠ Context doc is for {assignment.get('date_str')} — "
              f"using content_schedule.json for {target_date}")
        sched_assignment = load_schedule_for_date(
            CONTENT_SCHEDULE_PATH, target_date
        )
        if sched_assignment:
            assignment = sched_assignment
        else:
            print(f"  ⚠ No schedule entry for {target_date.strftime('%A')}")
    elif target_date and assignment.get("day") is None:
        # Context doc doesn't exist — try schedule
        sched_assignment = load_schedule_for_date(
            CONTENT_SCHEDULE_PATH, target_date
        )
        if sched_assignment:
            assignment = sched_assignment

    day = assignment.get("day")
    category = assignment.get("category")
    topic = assignment.get("topic")
    is_post_day = assignment.get("is_post_day", False)
    is_notes_only = assignment.get("is_notes_only", False)

    if day:
        print(f"  ✓ Day: {day}")
        if is_post_day:
            print(f"  ✓ Category: {normalise_category(category)}")
            print(f"  ✓ Topic: {topic}")
        elif is_notes_only:
            print(f"  ✓ Notes-only day")
        else:
            print(f"  ⚠ No assignment found for {day}")
    else:
        print(f"  ⚠ Could not determine today's assignment")

    # ── Step 3: Build email ──────────────────────────────────────────────────
    print("\n  Step 3: Building email...")

    if is_post_day and category:
        # Look up post prompt
        prompt_key = CATEGORY_TO_PROMPT_KEY.get(category)
        if not prompt_key:
            print(f"  ⚠ Unknown category '{category}' — falling back to notes-only")
            is_post_day = False
            is_notes_only = True

    if is_post_day and category:
        prompt_key = CATEGORY_TO_PROMPT_KEY.get(category)
        post_prompt = prompts.get(prompt_key, "")
        if not post_prompt:
            print(f"  ⚠ No prompt found for key '{prompt_key}' — check handbook")

        subject, html = render_post_day_email(
            assignment, post_prompt, notes_prompt, prompts, context_path
        )
        print(f"  ✓ Post day email: {normalise_category(category)}")

    elif is_notes_only:
        tomorrow = load_tomorrow_preview(
            CONTENT_SCHEDULE_PATH, day or ""
        )
        subject, html = render_notes_only_email(
            assignment, notes_prompt, prompts, tomorrow, context_path
        )
        print(f"  ✓ Notes-only email")
        if tomorrow:
            print(f"  ✓ Tomorrow preview: {normalise_category(tomorrow.get('category', ''))}")

    else:
        subject, html = render_no_assignment_email(notes_prompt)
        print(f"  ✓ No-assignment fallback email")

    # ── Step 4: Save locally ─────────────────────────────────────────────────
    print("\n  Step 4: Saving email...")
    output_path = save_email(html)
    print(f"  ✓ Saved: {output_path}")

    # ── Step 5: Send ─────────────────────────────────────────────────────────
    print(f"\n  Subject: {subject}")

    if not skip_email:
        print("\n  Step 5: Sending email...")
        send_email(html, subject)
    else:
        print("\n  Step 5: Skipped (--skip-email or --dry-run)")

    print("\n" + "=" * 60)
    print("  Done.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
