#!/usr/bin/env python3
"""
BACKUP CLEANUP UTILITY
======================

Manages 30-day retention for portfolio backups in trades/portfolio_backups/.

This utility removes old backup files to prevent disk space accumulation
while maintaining a reasonable backup history for recovery purposes.

Usage:
    python backup_cleanup.py                  # Preview what would be deleted
    python backup_cleanup.py --execute        # Actually delete old backups
    python backup_cleanup.py --days 14        # Use 14-day retention instead
    python backup_cleanup.py --list           # List all backups with ages
"""

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Import config for paths
try:
    from config import TRADES_DIR
except ImportError:
    TRADES_DIR = Path(__file__).resolve().parent / "trades"

BACKUP_DIR = TRADES_DIR / "portfolio_backups"
DEFAULT_RETENTION_DAYS = 30


def get_backup_files() -> List[Path]:
    """Get all backup files in the backup directory.

    Returns:
        List of Path objects for backup files, sorted by modification time (oldest first)
    """
    if not BACKUP_DIR.exists():
        return []

    # Match portfolio backup pattern: portfolio_YYYYMMDD_HHMMSS.csv
    backup_files = list(BACKUP_DIR.glob("portfolio_*.csv"))

    # Sort by modification time (oldest first)
    backup_files.sort(key=lambda f: f.stat().st_mtime)

    return backup_files


def get_file_age_days(file_path: Path) -> float:
    """Get the age of a file in days.

    Args:
        file_path: Path to the file

    Returns:
        Age in days (float)
    """
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    age = datetime.now() - mtime
    return age.total_seconds() / (24 * 3600)


def get_old_backups(retention_days: int = DEFAULT_RETENTION_DAYS) -> List[Tuple[Path, float]]:
    """Get backup files older than retention period.

    Args:
        retention_days: Number of days to retain backups

    Returns:
        List of (Path, age_days) tuples for files to delete
    """
    old_files = []

    for backup_file in get_backup_files():
        age_days = get_file_age_days(backup_file)
        if age_days > retention_days:
            old_files.append((backup_file, age_days))

    return old_files


def list_all_backups() -> None:
    """List all backup files with their ages."""
    backup_files = get_backup_files()

    if not backup_files:
        print("No backup files found.")
        return

    print(f"\nBackup Files ({len(backup_files)} total):\n")
    print(f"{'File':<45} {'Age':<12} {'Size':<10}")
    print("-" * 67)

    total_size = 0
    for backup_file in backup_files:
        age_days = get_file_age_days(backup_file)
        size_kb = backup_file.stat().st_size / 1024
        total_size += size_kb

        age_str = f"{age_days:.1f} days"
        size_str = f"{size_kb:.1f} KB"

        print(f"{backup_file.name:<45} {age_str:<12} {size_str:<10}")

    print("-" * 67)
    print(f"Total: {total_size:.1f} KB ({total_size/1024:.2f} MB)")


def cleanup_backups(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = True
) -> int:
    """Remove backup files older than retention period.

    Args:
        retention_days: Number of days to retain backups
        dry_run: If True, only preview what would be deleted

    Returns:
        Number of files deleted (or would be deleted in dry run)
    """
    old_backups = get_old_backups(retention_days)

    if not old_backups:
        print(f"No backups older than {retention_days} days found.")
        return 0

    mode = "DRY RUN" if dry_run else "EXECUTING"
    print(f"\n[{mode}] Cleanup with {retention_days}-day retention:\n")

    total_size = 0
    for backup_file, age_days in old_backups:
        size_kb = backup_file.stat().st_size / 1024
        total_size += size_kb

        action = "Would delete" if dry_run else "Deleting"
        print(f"  {action}: {backup_file.name} ({age_days:.1f} days old, {size_kb:.1f} KB)")

        if not dry_run:
            try:
                backup_file.unlink()
            except Exception as e:
                print(f"    ERROR: Failed to delete: {e}")

    print(f"\n{'Would free' if dry_run else 'Freed'}: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
    print(f"Files {'to delete' if dry_run else 'deleted'}: {len(old_backups)}")

    if dry_run:
        print("\nTo execute deletion, run: python backup_cleanup.py --execute")

    return len(old_backups)


def get_backup_stats() -> dict:
    """Get statistics about backup files.

    Returns:
        Dict with backup statistics
    """
    backup_files = get_backup_files()

    if not backup_files:
        return {
            'count': 0,
            'total_size_kb': 0,
            'oldest_days': 0,
            'newest_days': 0,
        }

    ages = [get_file_age_days(f) for f in backup_files]
    sizes = [f.stat().st_size / 1024 for f in backup_files]

    return {
        'count': len(backup_files),
        'total_size_kb': sum(sizes),
        'oldest_days': max(ages),
        'newest_days': min(ages),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Manage 30-day retention for portfolio backups"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete old backups (default is dry run)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Retention period in days (default: {DEFAULT_RETENTION_DAYS})"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all backups with ages"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show backup statistics"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  BACKUP CLEANUP UTILITY")
    print("=" * 60)
    print(f"\nBackup directory: {BACKUP_DIR}")

    if not BACKUP_DIR.exists():
        print(f"\nBackup directory does not exist yet.")
        print("No cleanup needed.")
        return

    if args.list:
        list_all_backups()
        return

    if args.stats:
        stats = get_backup_stats()
        print(f"\nBackup Statistics:")
        print(f"  Total backups: {stats['count']}")
        print(f"  Total size: {stats['total_size_kb']:.1f} KB ({stats['total_size_kb']/1024:.2f} MB)")
        print(f"  Oldest backup: {stats['oldest_days']:.1f} days")
        print(f"  Newest backup: {stats['newest_days']:.1f} days")
        return

    # Default: cleanup with dry run or execute
    cleanup_backups(
        retention_days=args.days,
        dry_run=not args.execute
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
