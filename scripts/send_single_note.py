#!/usr/bin/env python3
"""
Per-slot email delivery for Sterling Signals Cowork tasks.

Finds today's note/graphic/post files by date and slot label, then sends
them via Gmail SMTP using scripts.email_utils.

Modes:
    --slot morning|midday|evening   Send a single note + graphic for that slot
    --slot morning-bundle           Full morning email: schedule + post/visual
                                    status + signal alerts + morning note
    --file PATH                     Send any file directly (--subject optional)

Usage:
    python3 -m scripts.send_single_note --slot morning
    python3 -m scripts.send_single_note --slot morning-bundle
    python3 -m scripts.send_single_note --slot midday --dry-run
    python3 -m scripts.send_single_note --file path/to/file.html --subject "Custom"
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from config.output_paths import SUBSTACK_OUTPUT
from scripts.build_weekly_plan import get_current_week_plan, check_new_signals


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

ET = ZoneInfo("America/New_York")

NOTES_DIR = SUBSTACK_OUTPUT / "current" / "notes"
POSTS_DIR = SUBSTACK_OUTPUT / "current" / "posts"
DIAGRAMS_DIR = SUBSTACK_OUTPUT / "current" / "diagrams"
CAROUSELS_DIR = SUBSTACK_OUTPUT / "current" / "carousels"
CURRENT_DIR = SUBSTACK_OUTPUT / "current"

SLOT_CONFIG = {
    "morning": {"time": "08:30", "emoji": "\u2600\ufe0f"},   # ☀️
    "midday": {"time": "12:30", "emoji": "\U0001f4dd"},      # 📝
    "evening": {"time": "17:00", "emoji": "\U0001f319"},      # 🌙
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATE HELPER
# ═══════════════════════════════════════════════════════════════════════════════


def _get_today_et() -> date:
    """Return today's date in US Eastern time."""
    return datetime.now(ET).date()


# ═══════════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════


def _find_note_for_slot(slot: str, date_str: str) -> Optional[Path]:
    """Find the note HTML for a slot, excluding graphic files.

    Pattern: {slot}_{type}_{YYYYMMDD}.html (no '_graphic_' in name)
    """
    if not NOTES_DIR.exists():
        return None
    for f in sorted(NOTES_DIR.glob(f"{slot}_*_{date_str}.html")):
        if "_graphic_" not in f.name:
            return f
    return None


def _find_graphic_for_slot(slot: str, date_str: str) -> Optional[Path]:
    """Find graphic HTML or PNG for a slot.

    Pattern: {slot}_{type}_graphic_{YYYYMMDD}.{html,png}
    Prefers PNG over HTML for attachment.
    """
    if not NOTES_DIR.exists():
        return None
    # Prefer PNG (smaller, more universal)
    for ext in (".png", ".html"):
        for f in sorted(NOTES_DIR.glob(f"{slot}_*_graphic_*{date_str}*{ext}")):
            return f
    return None


def _find_prompt_kit(date_str: str) -> Optional[Path]:
    """Find prompt kit markdown for today.

    Checks: prompt_kit_{YYYYMMDD}.md then weekly_prompt_kits_*.md
    """
    specific = CURRENT_DIR / f"prompt_kit_{date_str}.md"
    if specific.exists():
        return specific
    # Fallback: latest weekly prompt kit
    weekly = sorted(CURRENT_DIR.glob("weekly_prompt_kits_*.md"))
    if weekly:
        return weekly[-1]
    return None


def _find_post_for_date(date_str: str) -> Optional[Path]:
    """Find the post HTML for today."""
    if not POSTS_DIR.exists():
        return None
    posts = sorted(POSTS_DIR.glob(f"*_{date_str}.html"))
    return posts[0] if posts else None


def _find_visual_for_date(date_str: str) -> Optional[Path]:
    """Find diagram or carousel for today."""
    for d in (DIAGRAMS_DIR, CAROUSELS_DIR):
        if not d.exists():
            continue
        for f in sorted(d.glob(f"*{date_str}*")):
            return f
    return None


def _load_manifest(target_date: date) -> Optional[Dict]:
    """Load daily manifest if it matches target date."""
    manifest_path = CURRENT_DIR / "daily_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text())
        if data.get("date") == target_date.isoformat():
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


## _load_weekly_plan, _load_signals, _check_new_signals moved to
## scripts.build_weekly_plan (Task 4). Imported at module top.


# ═══════════════════════════════════════════════════════════════════════════════
# HTML BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════


def _html_wrapper(title: str, subtitle: str, body_sections: str) -> str:
    """Wrap content in the standard Sterling Signals dark-theme email."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 20px; background: #111318; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
<div style="max-width: 600px; margin: 0 auto;">
    <div style="background: #0F1B2D; padding: 24px; border-radius: 12px; margin-bottom: 16px;">
        <h1 style="color: #C9A84C; margin: 0 0 4px 0; font-family: Georgia, serif; font-size: 22px;">{title}</h1>
        <p style="color: #94A3B8; margin: 0; font-size: 14px;">{subtitle}</p>
    </div>
{body_sections}
    <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 20px;">Sterling Signals Content Pipeline</p>
</div>
</body>
</html>"""


def _section_card(heading: str, content: str, border_color: str = "#C9A84C") -> str:
    """Build a styled section card."""
    return f"""    <div style="background: #1E293B; padding: 16px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid {border_color};">
        <h3 style="color: #E5E7EB; margin: 0 0 8px 0; font-size: 16px;">{heading}</h3>
        {content}
    </div>
"""


def _status_badge(ready: bool) -> str:
    """Green READY or red MISSING badge."""
    if ready:
        return '<span style="background: #166534; color: #4ADE80; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">READY</span>'
    return '<span style="background: #7F1D1D; color: #FCA5A5; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">MISSING</span>'


# ═══════════════════════════════════════════════════════════════════════════════
# SLOT SEND (morning / midday / evening)
# ═══════════════════════════════════════════════════════════════════════════════


def send_slot(slot: str, target_date: date, dry_run: bool = False) -> bool:
    """Send a single note email for a given slot."""
    date_str = target_date.strftime("%Y%m%d")
    cfg = SLOT_CONFIG[slot]

    note_path = _find_note_for_slot(slot, date_str)
    graphic_path = _find_graphic_for_slot(slot, date_str)

    if not note_path:
        print(f"  No {slot} note found for {target_date.isoformat()}")
        print(f"  Expected pattern: {NOTES_DIR}/{slot}_*_{date_str}.html")
        return False

    print(f"  Found note: {note_path.name}")
    if graphic_path:
        print(f"  Found graphic: {graphic_path.name}")

    # Build email
    subject = f"{cfg['emoji']} Sterling Signals — {slot.title()} note ready ({cfg['time']} ET)"

    note_html = note_path.read_text(errors="replace")
    instructions = '<p style="color: #CBD5E1; font-size: 14px; margin: 0;">Open the attached HTML → Select All → Copy → Paste into Substack Notes → Publish</p>'
    body_sections = _section_card(f"{slot.title()} Note — {cfg['time']} ET", instructions, "#22C55E")

    body_html = _html_wrapper(
        f"{cfg['emoji']} {slot.title()} Note Ready",
        f"{target_date.strftime('%A, %B %d')} — {cfg['time']} ET",
        body_sections,
    )

    attachments: List[Path] = [note_path]
    if graphic_path:
        attachments.append(graphic_path)

    if dry_run:
        print(f"  [DRY RUN] Would send: {subject}")
        print(f"  Attachments: {[p.name for p in attachments]}")
        return True

    return _do_send(subject, body_html, attachments)


# ═══════════════════════════════════════════════════════════════════════════════
# MORNING BUNDLE
# ═══════════════════════════════════════════════════════════════════════════════


def send_morning_bundle(target_date: date, dry_run: bool = False) -> bool:
    """Send the full morning bundle email."""
    date_str = target_date.strftime("%Y%m%d")
    day_name = target_date.strftime("%A")

    # Discover files
    note_path = _find_note_for_slot("morning", date_str)
    graphic_path = _find_graphic_for_slot("morning", date_str)
    prompt_kit = _find_prompt_kit(date_str)
    post_path = _find_post_for_date(date_str)
    visual_path = _find_visual_for_date(date_str)
    manifest = _load_manifest(target_date)
    weekly_plan = get_current_week_plan()

    # Determine post title
    post_title = None
    if manifest:
        post_info = manifest.get("post", {})
        post_title = post_info.get("title")
    if not post_title and post_path:
        post_title = post_path.stem.replace("_", " ").title()

    headline = post_title if post_title else "Notes only"

    print(f"  Day: {day_name}")
    print(f"  Note: {note_path.name if note_path else 'MISSING'}")
    print(f"  Graphic: {graphic_path.name if graphic_path else 'none'}")
    print(f"  Post: {post_path.name if post_path else 'none'}")
    print(f"  Visual: {visual_path.name if visual_path else 'none'}")
    print(f"  Prompt kit: {prompt_kit.name if prompt_kit else 'none'}")

    # ─── Section 1: Today's Schedule ─────────────────────────────────
    schedule_rows = ""
    for s, c in SLOT_CONFIG.items():
        n = _find_note_for_slot(s, date_str)
        status = f'<span style="color: #4ADE80;">{n.name}</span>' if n else '<span style="color: #94A3B8;">—</span>'
        schedule_rows += f'<tr><td style="color: #C9A84C; padding: 4px 12px 4px 0; font-size: 14px;">{c["emoji"]} {c["time"]} ET</td><td style="color: #CBD5E1; font-size: 14px;">{s.title()}</td><td style="font-size: 13px;">{status}</td></tr>'

    schedule_html = f'<table style="width: 100%;">{schedule_rows}</table>'
    sections = _section_card("Today's Schedule", schedule_html)

    # ─── Section 2: Today's Article ──────────────────────────────────
    if post_title or post_path:
        title_display = post_title or post_path.stem.replace("_", " ").title()
        badge = _status_badge(post_path is not None)
        article_html = f'<p style="color: #CBD5E1; font-size: 14px; margin: 0 0 4px 0;">{title_display}</p><p style="margin: 0;">{badge}</p>'
        sections += _section_card("Today's Article", article_html, "#3B82F6")

    # ─── Section 3: Today's Visual ───────────────────────────────────
    if manifest and manifest.get("visual", {}).get("type"):
        vtype = manifest["visual"]["type"].title()
        badge = _status_badge(visual_path is not None)
        visual_html = f'<p style="color: #CBD5E1; font-size: 14px; margin: 0 0 4px 0;">{vtype}</p><p style="margin: 0;">{badge}</p>'
        sections += _section_card("Today's Visual", visual_html, "#8B5CF6")

    # ─── Section 4: New Signal Alert ─────────────────────────────────
    new_tickers = check_new_signals(weekly_plan)
    if new_tickers:
        ticker_list = ", ".join(f"<b>${t}</b>" for t in new_tickers)
        alert_html = f'<p style="color: #FCD34D; font-size: 14px; margin: 0;">New signals not in weekly plan: {ticker_list}</p>'
        sections += _section_card("\u26a0\ufe0f New Signal Alert", alert_html, "#F59E0B")

    # ─── Section 5: Morning Note ─────────────────────────────────────
    if note_path:
        instructions = '<p style="color: #CBD5E1; font-size: 14px; margin: 0;">Open the attached HTML → Select All → Copy → Paste into Substack Notes</p>'
        sections += _section_card("Morning Note", instructions, "#22C55E")

    subject = f"\u2600\ufe0f Sterling Signals — {day_name}: {headline}"
    body_html = _html_wrapper(
        f"\u2600\ufe0f {day_name} Morning Brief",
        target_date.strftime("%B %d, %Y"),
        sections,
    )

    attachments: List[Path] = []
    if note_path:
        attachments.append(note_path)
    if graphic_path:
        attachments.append(graphic_path)
    if prompt_kit:
        attachments.append(prompt_kit)

    if dry_run:
        print(f"  [DRY RUN] Would send: {subject}")
        print(f"  Attachments: {[p.name for p in attachments]}")
        if new_tickers:
            print(f"  ⚠️ New signals: {', '.join(new_tickers)}")
        return True

    return _do_send(subject, body_html, attachments)


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECT FILE SEND
# ═══════════════════════════════════════════════════════════════════════════════


def send_file(filepath: Path, subject: Optional[str], dry_run: bool = False) -> bool:
    """Send a specific file as an email."""
    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return False

    print(f"  File: {filepath.name} ({filepath.stat().st_size // 1024}KB)")

    if not subject:
        subject = f"Sterling Signals — {filepath.stem.replace('_', ' ').title()}"

    # Build body
    if filepath.suffix.lower() in (".html", ".htm"):
        file_content = filepath.read_text(errors="replace")
        body_text = f'<p style="color: #CBD5E1; font-size: 14px;">See attached HTML file: <code>{filepath.name}</code></p>'
    else:
        body_text = f'<p style="color: #CBD5E1; font-size: 14px;">See attached file: <code>{filepath.name}</code></p>'

    body_html = _html_wrapper(
        "File Delivery",
        filepath.name,
        _section_card("Attached", body_text),
    )

    if dry_run:
        print(f"  [DRY RUN] Would send: {subject}")
        print(f"  Attachment: {filepath.name}")
        return True

    return _do_send(subject, body_html, [filepath])


# ═══════════════════════════════════════════════════════════════════════════════
# SEND HELPER
# ═══════════════════════════════════════════════════════════════════════════════


def _do_send(subject: str, body_html: str, attachments: List[Path]) -> bool:
    """Send email via email_utils."""
    try:
        from scripts.email_utils import send_email, get_recipient_email

        recipient = get_recipient_email()
        ok = send_email(recipient, subject, body_html, attachments=attachments)
        if ok:
            print(f"  \u2713 Email sent with {len(attachments)} attachment(s)")
        else:
            print("  \u2717 Email send failed")
        return ok
    except RuntimeError as e:
        print(f"  \u2717 {e}")
        return False
    except ImportError:
        print("  \u2717 scripts.email_utils not available")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Per-slot email delivery for Sterling Signals"
    )
    parser.add_argument(
        "--slot",
        choices=["morning", "midday", "evening", "morning-bundle"],
        help="Slot to send (morning-bundle includes schedule + status)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Send a specific file directly",
    )
    parser.add_argument(
        "--subject",
        help="Custom subject line (used with --file)",
    )
    parser.add_argument(
        "--date",
        help="Override date (YYYY-MM-DD, default: today in ET)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without sending",
    )
    args = parser.parse_args()

    if not args.slot and not args.file:
        parser.error("Either --slot or --file is required")

    # Determine target date
    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = _get_today_et()

    mode = args.slot or f"file:{args.file.name}"
    print(f"\n{'='*55}")
    print(f"  SEND NOTE — {mode.upper()} ({target_date.isoformat()})")
    print(f"{'='*55}\n")

    if args.file:
        success = send_file(args.file, args.subject, dry_run=args.dry_run)
    elif args.slot == "morning-bundle":
        success = send_morning_bundle(target_date, dry_run=args.dry_run)
    else:
        success = send_slot(args.slot, target_date, dry_run=args.dry_run)

    if not success:
        print("\n  No email sent.")
        sys.exit(1)

    print(f"\n{'='*55}\n")


if __name__ == "__main__":
    main()
