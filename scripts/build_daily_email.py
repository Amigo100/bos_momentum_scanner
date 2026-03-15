#!/usr/bin/env python3
"""
Build and send the daily Sterling Signals content email.

Reads the daily manifest and collects generated HTML files (posts, notes,
diagrams) as email attachments. Sends a summary email with all content
attached for mobile posting to Substack.

Works with Cowork (which generates the content) or standalone.

Usage:
    python3 -m scripts.build_daily_email                     # Today
    python3 -m scripts.build_daily_email --date 2026-03-01   # Override date
    python3 -m scripts.build_daily_email --skip-email        # Local only
    python3 -m scripts.build_daily_email --dry-run           # Print + save, no email
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

from config.output_paths import SUBSTACK_OUTPUT, BASE_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

MANIFEST_PATH = SUBSTACK_OUTPUT / "current" / "daily_manifest.json"
NOTES_MANIFEST_PATH = SUBSTACK_OUTPUT / "current" / "notes" / "notes_manifest.json"
POSTS_DIR = SUBSTACK_OUTPUT / "current" / "posts"
NOTES_DIR = SUBSTACK_OUTPUT / "current" / "notes"
DIAGRAMS_DIR = SUBSTACK_OUTPUT / "current" / "diagrams"
DAILY_EMAIL_OUTPUT = SUBSTACK_OUTPUT / "current" / "daily_email.html"

# File size limit for attachments (2MB per file)
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024

# Extensions we can email as attachments
EMAILABLE_EXTENSIONS = {".html", ".htm", ".png"}


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST LOADING
# ═══════════════════════════════════════════════════════════════════════════════


def _load_manifest(target_date: date) -> Optional[Dict]:
    """Load daily manifest if it matches target_date."""
    if not MANIFEST_PATH.exists():
        return None

    try:
        data = json.loads(MANIFEST_PATH.read_text())
        manifest_date = data.get("date", "")
        if manifest_date == target_date.isoformat():
            return data
        print(f"  ℹ Manifest date ({manifest_date}) != target ({target_date.isoformat()})")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠ Failed to parse manifest: {e}")
        return None


def _load_notes_manifest(target_date: date) -> Optional[Dict]:
    """Load notes manifest if it matches target_date."""
    if not NOTES_MANIFEST_PATH.exists():
        return None

    try:
        data = json.loads(NOTES_MANIFEST_PATH.read_text())
        manifest_date = data.get("target_date", "")
        if manifest_date == target_date.isoformat():
            return data
        return None
    except (json.JSONDecodeError, KeyError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# FILE COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════


def _collect_attachments_from_manifest(
    manifest: Dict,
) -> List[Path]:
    """Collect file paths referenced in manifest for email attachment."""
    attachments = []
    base = SUBSTACK_OUTPUT / "current"

    # Post file
    post_info = manifest.get("post") or {}
    post_file = post_info.get("file")
    if post_file:
        post_path = base / post_file if not Path(post_file).is_absolute() else Path(post_file)
        if post_path.exists() and post_path.suffix in EMAILABLE_EXTENSIONS:
            size_kb = post_path.stat().st_size // 1024
            if post_path.stat().st_size <= MAX_ATTACHMENT_BYTES:
                attachments.append(post_path)
                print(f"    ✓ Post: {post_path.name} ({size_kb}KB)")

    # Note files
    for note in manifest.get("notes", []):
        note_file = note.get("file")
        if not note_file:
            continue
        note_path = base / note_file if not Path(note_file).is_absolute() else Path(note_file)
        if note_path.exists() and note_path.suffix in EMAILABLE_EXTENSIONS:
            size_kb = note_path.stat().st_size // 1024
            if note_path.stat().st_size <= MAX_ATTACHMENT_BYTES:
                attachments.append(note_path)
                slot = note.get("slot", "?")
                ntype = note.get("type", "?")
                print(f"    ✓ Note {slot} ({ntype}): {note_path.name} ({size_kb}KB)")

    # Diagram HTML (not MP4)
    visual = manifest.get("visual") or {}
    visual_file = visual.get("file")
    if visual_file:
        visual_path = base / visual_file if not Path(visual_file).is_absolute() else Path(visual_file)
        if visual_path.exists() and visual_path.suffix in EMAILABLE_EXTENSIONS:
            size_kb = visual_path.stat().st_size // 1024
            if visual_path.stat().st_size <= MAX_ATTACHMENT_BYTES:
                attachments.append(visual_path)
                print(f"    ✓ Visual: {visual_path.name} ({size_kb}KB)")

    return attachments


def _collect_attachments_fallback(
    target_date: date,
) -> List[Path]:
    """Fallback: scan output dirs for today's HTML files when no manifest."""
    attachments = []
    date_str = target_date.strftime("%Y%m%d")

    for directory, label in [
        (POSTS_DIR, "Post"),
        (NOTES_DIR, "Note"),
        (DIAGRAMS_DIR, "Diagram"),
    ]:
        if not directory.exists():
            continue
        for ext in (".html", ".png"):
            for f in sorted(directory.glob(f"*{date_str}*{ext}")):
                if f.stat().st_size <= MAX_ATTACHMENT_BYTES:
                    attachments.append(f)
                    size_kb = f.stat().st_size // 1024
                    print(f"    ✓ {label}: {f.name} ({size_kb}KB)")

    return attachments


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL HTML BODY
# ═══════════════════════════════════════════════════════════════════════════════


def _build_email_body(
    target_date: date,
    manifest: Optional[Dict],
    attachment_count: int,
) -> str:
    """Build a summary HTML email body."""
    day_name = target_date.strftime("%A")
    date_str = target_date.strftime("%B %d, %Y")

    # Extract info from manifest
    post_category = "None"
    post_title = None
    note_count = 0
    visual_type = "None"
    notes_info = []

    if manifest:
        post_info = manifest.get("post") or {}
        post_category = post_info.get("category", "none").replace("_", " ").title()
        post_title = post_info.get("title")
        if post_category.lower() == "None":
            post_category = "None"

        notes_data = manifest.get("notes", [])
        note_count = len(notes_data)
        for n in notes_data:
            time_label = n.get("time_label", "")
            time_et = n.get("time_et", "?")
            ntype = n.get("type", "?")
            nfile = n.get("file", "")
            filename = Path(nfile).name if nfile else "—"
            notes_info.append({
                "display": f"📌 {time_et} ET — {ntype}",
                "filename": filename,
                "time_label": time_label,
            })

        visual = manifest.get("visual") or {}
        visual_type = visual.get("type", "none").title()

    # Build HTML
    sections = []

    # Header
    sections.append(f"""
    <div style="background: #0F1B2D; padding: 24px; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="color: #C9A84C; margin: 0 0 8px 0; font-family: Georgia, serif; font-size: 24px;">
            Sterling Signals — {day_name}
        </h1>
        <p style="color: #94A3B8; margin: 0; font-size: 14px;">{date_str}</p>
    </div>
    """)

    # Summary card
    sections.append(f"""
    <div style="background: #1E293B; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #C9A84C;">
        <h2 style="color: #E5E7EB; margin: 0 0 12px 0; font-size: 18px;">Today's Content</h2>
        <table style="width: 100%; color: #CBD5E1; font-size: 14px;">
            <tr><td style="padding: 4px 0; color: #94A3B8;">Post:</td><td style="padding: 4px 0;">{post_category}{f' — {post_title}' if post_title else ''}</td></tr>
            <tr><td style="padding: 4px 0; color: #94A3B8;">Notes:</td><td style="padding: 4px 0;">{note_count}</td></tr>
            <tr><td style="padding: 4px 0; color: #94A3B8;">Visual:</td><td style="padding: 4px 0;">{visual_type}</td></tr>
            <tr><td style="padding: 4px 0; color: #94A3B8;">Attachments:</td><td style="padding: 4px 0;">{attachment_count} HTML file(s)</td></tr>
        </table>
    </div>
    """)

    # Posting schedule with filenames
    if notes_info:
        schedule_rows = ""
        for n in notes_info:
            schedule_rows += f"""
                <tr>
                    <td style="padding: 6px 0; color: #22C55E; font-size: 14px; white-space: nowrap; vertical-align: top;">{n['display']}</td>
                </tr>
                <tr>
                    <td style="padding: 0 0 8px 24px; color: #94A3B8; font-size: 13px; font-family: monospace;">{n['filename']}</td>
                </tr>"""

        sections.append(f"""
        <div style="background: #1E293B; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="color: #22C55E; margin: 0 0 12px 0; font-size: 16px;">Today's Posting Schedule</h3>
            <table style="width: 100%;">{schedule_rows}</table>
            <p style="color: #64748B; font-size: 13px; margin: 12px 0 0 0; border-top: 1px solid #334155; padding-top: 8px;">
                You'll receive a reminder email 15 min before each slot.
            </p>
        </div>
        """)

    # Quick-start instructions
    sections.append("""
    <div style="background: #0F1B2D; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155;">
        <h3 style="color: #C9A84C; margin: 0 0 8px 0; font-size: 16px;">Quick Start</h3>
        <ol style="color: #CBD5E1; padding-left: 20px; margin: 0; font-size: 14px;">
            <li style="padding: 4px 0;">Open each attached HTML file</li>
            <li style="padding: 4px 0;">Copy the content</li>
            <li style="padding: 4px 0;">Paste into Substack (post editor or Notes)</li>
            <li style="padding: 4px 0;">Publish!</li>
        </ol>
    </div>
    """)

    body_content = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 20px; background: #111318; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
<div style="max-width: 600px; margin: 0 auto;">
{body_content}
    <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 24px;">
        Sterling Signals Daily Content Pipeline
    </p>
</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Build and optionally send the daily content email."""
    parser = argparse.ArgumentParser(description="Build daily content email")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD)")
    parser.add_argument("--skip-email", action="store_true", help="Save locally, don't send")
    parser.add_argument("--dry-run", action="store_true", help="Print summary, save HTML, don't send")
    args = parser.parse_args()

    # Determine target date
    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = date.today()

    day_name = target_date.strftime("%A")
    print(f"\n{'='*60}")
    print(f"  DAILY CONTENT EMAIL — {day_name} {target_date.isoformat()}")
    print(f"{'='*60}\n")

    # Step 1: Load manifest
    print("  Step 1: Loading manifest...")
    manifest = _load_manifest(target_date)
    if manifest:
        print(f"  ✓ Manifest loaded (generated: {manifest.get('generated_at', '?')})")
    else:
        print(f"  ℹ No manifest found — will scan output dirs for today's files")
        # Try notes manifest as partial fallback
        notes_manifest = _load_notes_manifest(target_date)
        if notes_manifest:
            print(f"  ℹ Found notes manifest with {len(notes_manifest.get('notes', []))} notes")

    # Step 2: Collect attachments
    print("\n  Step 2: Collecting attachments...")
    if manifest:
        attachments = _collect_attachments_from_manifest(manifest)
    else:
        attachments = _collect_attachments_fallback(target_date)

    if not attachments:
        print("  ⚠ No HTML files found for today")
        print("  ℹ Content may not have been generated yet (run Cowork first)")

    print(f"\n  → {len(attachments)} attachment(s) collected")

    # Step 3: Build email HTML body
    print("\n  Step 3: Building email body...")
    email_html = _build_email_body(target_date, manifest, len(attachments))

    # Save locally
    DAILY_EMAIL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DAILY_EMAIL_OUTPUT.write_text(email_html)
    print(f"  ✓ Saved: {DAILY_EMAIL_OUTPUT}")

    # Step 4: Send email
    if args.dry_run:
        print("\n  [DRY RUN] Email not sent")
        print(f"  Preview: {DAILY_EMAIL_OUTPUT}")
        return

    if args.skip_email:
        print("\n  ⏭ Email skipped (--skip-email)")
        return

    print("\n  Step 4: Sending email...")
    try:
        from scripts.email_utils import send_email, get_recipient_email

        recipient = get_recipient_email()
        subject = f"Sterling Signals — {day_name} Content ({target_date.isoformat()})"

        if send_email(recipient, subject, email_html, attachments=attachments):
            print(f"  ✓ Email sent with {len(attachments)} attachment(s)")
        else:
            print("  ✗ Email send failed")
            sys.exit(1)
    except RuntimeError as e:
        print(f"  ✗ {e}")
        sys.exit(1)
    except ImportError:
        print("  ✗ scripts.email_utils not available")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
