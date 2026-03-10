#!/usr/bin/env python3
"""
Archive previous day's Cowork content before generating new content.
==================================================================

Run at the START of each Cowork run to:
1. Read daily_manifest.json to find the previous run's date
2. Move that day's content into substack/output/archive/YYYY-WXX/{day}/
3. Clear current/posts/, current/notes/, current/diagrams/, current/carousels/
4. Preserve non-daily files (portfolio_visual.html, newsletter.html, etc.)

Usage:
    python3 -m scripts.archive_daily_content
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from config.output_paths import (
    get_substack_archive_dir,
    get_substack_current_dir,
    get_week_identifier,
)


CURRENT = get_substack_current_dir()
DAILY_DIRS = ["posts", "notes", "diagrams", "carousels"]

# Files to keep in current/ across runs (not date-specific content)
PRESERVE_FILES = {
    "portfolio_visual.html",
    "portfolio_dashboard.html",
    "portfolio_summary.png",
    "portfolio_snapshot.json",
    "newsletter.html",
    "content_schedule.json",
    "daily_notes_context.json",
    "content_production_guide.md",
    "daily_context.md",
    "daily_email.html",
    ".DS_Store",
}


def archive_previous_day():
    """Archive the previous day's content and clear daily directories."""
    manifest_path = CURRENT / "daily_manifest.json"
    if not manifest_path.exists():
        print("  No previous manifest — nothing to archive")
        return

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Error reading manifest: {e}")
        return

    prev_date = manifest.get("date")
    prev_day = manifest.get("day", "unknown")

    if not prev_date:
        print("  Manifest has no date field — nothing to archive")
        return

    # Don't re-archive today's content (idempotency guard)
    today = datetime.now().strftime("%Y-%m-%d")
    if prev_date == today:
        print(f"  Manifest date is today ({today}) — clearing for fresh generation")
        _clear_daily_dirs()
        return

    # Determine archive destination: substack/output/archive/YYYY-WXX/{day}/
    dt = datetime.strptime(prev_date, "%Y-%m-%d")
    week_id = get_week_identifier(dt)
    archive_base = get_substack_archive_dir(dt)  # substack/output/archive/YYYY-WXX/
    archive_dir = archive_base / prev_day
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_count = 0

    # Archive the manifest itself
    shutil.copy2(manifest_path, archive_dir / "daily_manifest.json")
    archived_count += 1

    # Archive content from each daily directory
    for subdir_name in DAILY_DIRS:
        src_dir = CURRENT / subdir_name
        if not src_dir.exists():
            continue

        # Find files from the previous date (YYYYMMDD in filename)
        date_stamp = prev_date.replace("-", "")
        dated_files = [
            f for f in src_dir.iterdir()
            if f.is_file() and date_stamp in f.name
        ]

        if dated_files:
            dest = archive_dir / subdir_name
            dest.mkdir(parents=True, exist_ok=True)
            for f in dated_files:
                shutil.copy2(f, dest / f.name)
                archived_count += 1

    # Archive notes manifest separately (it doesn't have a date in its name)
    notes_manifest = CURRENT / "notes" / "notes_manifest.json"
    if notes_manifest.exists():
        (archive_dir / "notes").mkdir(parents=True, exist_ok=True)
        shutil.copy2(notes_manifest, archive_dir / "notes" / "notes_manifest.json")
        archived_count += 1

    # Clear daily directories (remove ALL files, not just dated ones)
    _clear_daily_dirs()

    # Remove the old manifest so Cowork writes a fresh one
    manifest_path.unlink(missing_ok=True)

    relative_archive = f"archive/{week_id}/{prev_day}"
    print(f"  Archived {archived_count} files from {prev_day} ({prev_date}) → {relative_archive}")


def _clear_daily_dirs():
    """Remove all files from daily content directories."""
    for subdir_name in DAILY_DIRS:
        src_dir = CURRENT / subdir_name
        if not src_dir.exists():
            continue
        for f in src_dir.iterdir():
            if f.is_file() and f.name != ".gitkeep":
                f.unlink()


def main():
    print("Archiving previous day's content...")
    archive_previous_day()
    print("  Done — current/ directories cleared for today")


if __name__ == "__main__":
    main()
