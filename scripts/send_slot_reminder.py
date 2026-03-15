#!/usr/bin/env python3
"""
Send a timed reminder email for a specific Substack posting slot.

Reads the daily manifest, finds the file for the given slot, and emails it
with the HTML attached so you can paste it into Substack from your phone.

Designed to be called by launchd plists set up via scripts/setup_reminders.py.

Usage:
    python3 -m scripts.send_slot_reminder --slot morning
    python3 -m scripts.send_slot_reminder --slot midday
    python3 -m scripts.send_slot_reminder --slot evening
    python3 -m scripts.send_slot_reminder --slot morning --dry-run
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

from config.output_paths import SUBSTACK_OUTPUT

CURRENT = SUBSTACK_OUTPUT / "current"

SLOT_TIMES = {
    "morning": "08:00 AEDT",
    "midday": "12:00 AEDT",
    "evening": "20:00 AEDT",
}

SLOT_NUMBERS = {
    "morning": 1,
    "midday": 2,
    "evening": 3,
}


def _find_content_for_slot(manifest: Dict, slot: str) -> Optional[Dict]:
    """Find the content entry for a given slot from the manifest."""
    # First check the reminders array (new format)
    reminders = manifest.get("reminders", [])
    match = next((r for r in reminders if r.get("slot") == slot), None)
    if match:
        return match

    # Fallback: check notes array by slot number
    slot_num = SLOT_NUMBERS.get(slot)
    notes = manifest.get("notes", [])
    match = next((n for n in notes if n.get("slot") == slot_num), None)
    if match:
        return match

    # Fallback: check notes array by time_label
    match = next((n for n in notes if n.get("time_label") == slot), None)
    return match


def send_reminder(slot: str, dry_run: bool = False) -> bool:
    """Send a reminder email for a specific posting slot.

    Returns True if email was sent (or would be sent in dry-run mode).
    """
    today = date.today()
    today_str = today.isoformat()

    # Load manifest
    manifest_path = CURRENT / "daily_manifest.json"
    if not manifest_path.exists():
        print(f"  No manifest found at {manifest_path}")
        return False

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Error reading manifest: {e}")
        return False

    # Verify manifest is for today
    manifest_date = manifest.get("date", "")
    if manifest_date != today_str:
        print(f"  Manifest is for {manifest_date}, not today ({today_str})")
        return False

    # Find content for this slot
    match = _find_content_for_slot(manifest, slot)
    if not match:
        print(f"  No content scheduled for {slot} slot today")
        return False

    # Resolve file path
    file_rel = match.get("file", "")
    if not file_rel:
        print(f"  No file specified for {slot} slot")
        return False

    filepath = CURRENT / file_rel
    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return False

    content_type = match.get("type", "note").replace("_", " ").title()
    time_str = SLOT_TIMES.get(slot, slot)

    print(f"  Found: {filepath.name} ({content_type})")
    print(f"  Post at: {time_str}")

    if dry_run:
        print(f"  [DRY RUN] Would send reminder for {slot}: {filepath.name}")
        return True

    # Send email
    try:
        from utils.email_notifier import send_email_with_attachments
    except ImportError:
        print("  Error: email_notifier not available")
        return False

    subject = f"📋 Post Now — {slot.title()} {content_type} ({time_str})"

    body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 20px; background: #111318; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
<div style="max-width: 500px; margin: 0 auto;">
    <div style="background: #0F1B2D; padding: 20px; border-radius: 12px; margin-bottom: 16px;">
        <h1 style="color: #C9A84C; margin: 0 0 4px 0; font-size: 20px;">Time to Post</h1>
        <p style="color: #94A3B8; margin: 0; font-size: 14px;">{time_str} — {slot.title()} Slot</p>
    </div>
    <div style="background: #1E293B; padding: 16px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #22C55E;">
        <p style="color: #E5E7EB; margin: 0 0 8px 0; font-size: 16px;"><b>{content_type}</b></p>
        <p style="color: #94A3B8; margin: 0; font-size: 14px;">File: <code style="background: #334155; padding: 2px 6px; border-radius: 4px;">{filepath.name}</code></p>
    </div>
    <div style="background: #1E293B; padding: 16px; border-radius: 8px;">
        <p style="color: #CBD5E1; margin: 0; font-size: 14px;">
            1. Open the attached HTML file<br>
            2. Select all → Copy<br>
            3. Paste into Substack Notes<br>
            4. Publish!
        </p>
    </div>
    <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 16px;">Sterling Signals Reminder System</p>
</div>
</body>
</html>"""

    # Read the file for attachment
    try:
        file_bytes = filepath.read_bytes()
        attachments = [(filepath.name, file_bytes)]
    except OSError as e:
        print(f"  Error reading file: {e}")
        return False

    if send_email_with_attachments(subject, body, attachments):
        print(f"  ✓ Reminder sent for {slot}: {filepath.name}")
        return True
    else:
        print(f"  ✗ Failed to send reminder")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Send a timed Substack posting reminder"
    )
    parser.add_argument(
        "--slot",
        required=True,
        choices=["morning", "midday", "evening"],
        help="Which posting slot to send a reminder for",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without sending",
    )
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  SLOT REMINDER — {args.slot.upper()}")
    print(f"{'='*50}\n")

    success = send_reminder(args.slot, dry_run=args.dry_run)

    if not success:
        print("\n  No reminder sent.")
        sys.exit(1)

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    main()
