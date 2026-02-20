#!/usr/bin/env python3
"""
BACKUP CLEANUP UTILITY
======================

Deduplicates portfolio backups: keeps only the newest file per ISO calendar week.
Applies to both trades/portfolio_backups/ and trades/daily_portfolio_backups/.

This prevents duplicate backups from re-runs while preserving one snapshot per week
for historical reference.

Usage:
    python -m utils.backup_cleanup                  # Preview what would be removed
    python -m utils.backup_cleanup --execute        # Actually remove duplicates
    python -m utils.backup_cleanup --list           # List all backups grouped by week
    python -m utils.backup_cleanup --stats          # Show backup statistics
"""

import argparse
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Import config for paths
try:
    from config import PORTFOLIO_BACKUP_DIR, DAILY_PORTFOLIO_BACKUP_DIR
except ImportError:
    _BASE_DIR = Path(__file__).resolve().parent.parent
    PORTFOLIO_BACKUP_DIR = _BASE_DIR / "portfolio" / "output" / "portfolio_backups"
    DAILY_PORTFOLIO_BACKUP_DIR = _BASE_DIR / "portfolio" / "output" / "daily_portfolio_backups"

BACKUP_DIRS = {
    'weekly': PORTFOLIO_BACKUP_DIR,
    'daily': DAILY_PORTFOLIO_BACKUP_DIR,
}

# Pattern: portfolio_YYYYMMDD_HHMMSS.csv or daily_portfolio_YYYYMMDD_HHMMSS.csv
DATE_PATTERN = re.compile(r'(\d{8})_(\d{6})')


def _parse_backup_datetime(filename: str) -> datetime:
    """Extract datetime from backup filename.

    Args:
        filename: e.g. 'portfolio_20260124_235455.csv'

    Returns:
        datetime object, or datetime.min if unparseable
    """
    match = DATE_PATTERN.search(filename)
    if not match:
        return datetime.min
    date_str, time_str = match.groups()
    try:
        return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    except ValueError:
        return datetime.min


def _iso_week_key(dt: datetime) -> str:
    """Get ISO week key from datetime.

    Returns:
        String like '2026-W04'
    """
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def get_backup_files(backup_dir: Path) -> List[Path]:
    """Get all CSV backup files in a directory, sorted oldest first."""
    if not backup_dir.exists():
        return []
    files = list(backup_dir.glob("*.csv"))
    files.sort(key=lambda f: _parse_backup_datetime(f.name))
    return files


def group_by_week(files: List[Path]) -> Dict[str, List[Path]]:
    """Group backup files by ISO calendar week.

    Args:
        files: List of backup file paths

    Returns:
        Dict mapping week key to list of files in that week
    """
    groups = defaultdict(list)
    for f in files:
        dt = _parse_backup_datetime(f.name)
        if dt == datetime.min:
            groups['unknown'].append(f)
        else:
            groups[_iso_week_key(dt)].append(f)

    # Sort files within each group by datetime (newest last)
    for week_key in groups:
        groups[week_key].sort(key=lambda f: _parse_backup_datetime(f.name))

    return dict(groups)


def find_duplicates(backup_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Find duplicate backups (all but newest per week).

    Args:
        backup_dir: Path to backup directory

    Returns:
        Tuple of (files_to_remove, files_to_keep)
    """
    files = get_backup_files(backup_dir)
    if not files:
        return [], []

    groups = group_by_week(files)
    to_remove = []
    to_keep = []

    for week_key, week_files in sorted(groups.items()):
        # Keep the newest (last) file, remove the rest
        to_keep.append(week_files[-1])
        to_remove.extend(week_files[:-1])

    return to_remove, to_keep


def dedup_backups(
    backup_dir: Path,
    label: str,
    dry_run: bool = True
) -> int:
    """Remove duplicate backups, keeping newest per calendar week.

    Args:
        backup_dir: Path to backup directory
        label: Human-readable label (e.g., 'Weekly Portfolio')
        dry_run: If True, only preview

    Returns:
        Number of files removed (or would be removed)
    """
    to_remove, to_keep = find_duplicates(backup_dir)

    if not to_remove:
        print(f"\n  {label}: No duplicates found ({len(to_keep)} files, 1 per week)")
        return 0

    mode = "DRY RUN" if dry_run else "EXECUTING"
    print(f"\n  [{mode}] {label}:")
    print(f"  Keeping {len(to_keep)} files (newest per week)")
    print(f"  Removing {len(to_remove)} duplicates:\n")

    total_size = 0
    for f in to_remove:
        dt = _parse_backup_datetime(f.name)
        week = _iso_week_key(dt) if dt != datetime.min else 'unknown'
        size_kb = f.stat().st_size / 1024
        total_size += size_kb

        action = "Would remove" if dry_run else "Removing"
        print(f"    {action}: {f.name} ({week}, {size_kb:.1f} KB)")

        if not dry_run:
            try:
                f.unlink()
            except Exception as e:
                print(f"      ERROR: {e}")

    freed = "Would free" if dry_run else "Freed"
    print(f"\n  {freed}: {total_size:.1f} KB ({total_size / 1024:.2f} MB)")

    return len(to_remove)


def list_backups(backup_dir: Path, label: str) -> None:
    """List all backups grouped by ISO week."""
    files = get_backup_files(backup_dir)
    if not files:
        print(f"\n  {label}: No backups found")
        return

    groups = group_by_week(files)
    total = len(files)
    total_size = sum(f.stat().st_size for f in files) / 1024

    print(f"\n  {label}: {total} files ({total_size:.1f} KB)")
    print(f"  {'Week':<12} {'Files':<8} {'Newest':<30} {'Keep'}")
    print(f"  {'─' * 62}")

    for week_key in sorted(groups.keys()):
        week_files = groups[week_key]
        newest = week_files[-1]
        keep_marker = "✅" if len(week_files) == 1 else f"✅ (+{len(week_files) - 1} dupes)"
        print(f"  {week_key:<12} {len(week_files):<8} {newest.name:<30} {keep_marker}")


def get_backup_stats() -> Dict:
    """Get aggregate statistics across all backup directories."""
    stats = {}
    for label, backup_dir in BACKUP_DIRS.items():
        files = get_backup_files(backup_dir)
        to_remove, to_keep = find_duplicates(backup_dir)
        sizes = [f.stat().st_size / 1024 for f in files] if files else [0]

        stats[label] = {
            'total_files': len(files),
            'unique_weeks': len(to_keep),
            'duplicates': len(to_remove),
            'total_size_kb': sum(sizes),
            'reclaimable_kb': sum(f.stat().st_size / 1024 for f in to_remove),
        }
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API (for pipeline integration)
# ═══════════════════════════════════════════════════════════════════════════════

def run_dedup(dry_run: bool = False) -> int:
    """Run dedup across all backup directories.

    Args:
        dry_run: If True, preview only

    Returns:
        Total number of files removed
    """
    total = 0
    for label, backup_dir in BACKUP_DIRS.items():
        display_label = label.replace('_', ' ').title() + " Backups"
        total += dedup_backups(backup_dir, display_label, dry_run=dry_run)
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate portfolio backups (keep newest per calendar week)"
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually remove duplicates (default is dry run)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all backups grouped by week"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show backup statistics"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  BACKUP DEDUP UTILITY")
    print("=" * 60)

    if args.list:
        for label, backup_dir in BACKUP_DIRS.items():
            display = label.replace('_', ' ').title() + " Backups"
            list_backups(backup_dir, display)
        return

    if args.stats:
        stats = get_backup_stats()
        print("\n  Backup Statistics:")
        for label, s in stats.items():
            display = label.replace('_', ' ').title()
            print(f"\n  {display}:")
            print(f"    Total files:     {s['total_files']}")
            print(f"    Unique weeks:    {s['unique_weeks']}")
            print(f"    Duplicates:      {s['duplicates']}")
            print(f"    Total size:      {s['total_size_kb']:.1f} KB")
            print(f"    Reclaimable:     {s['reclaimable_kb']:.1f} KB")
        return

    # Default: dedup
    total = run_dedup(dry_run=not args.execute)

    if total == 0:
        print("\n  ✅ All clean — one backup per calendar week")
    elif not args.execute:
        print(f"\n  Run with --execute to remove {total} duplicate(s)")

    print("\n  Done!")


if __name__ == "__main__":
    main()
