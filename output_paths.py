#!/usr/bin/env python3
"""
OUTPUT PATHS - Centralized folder structure management
======================================================

Provides consistent output directory structure across all modules:
- trades/current/     - Always latest week's outputs
- trades/weeks/YYYY-WXX/ - Historical archives by ISO week

Usage:
    from output_paths import (
        get_current_dir,
        get_week_dir,
        ensure_output_structure,
        get_output_paths
    )

    # Get paths
    paths = get_output_paths()
    signals_file = paths['current'] / 'signals.json'

    # Ensure directories exist
    ensure_output_structure()
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
TRADES_DIR = BASE_DIR / "trades"


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_week_identifier(dt: datetime = None) -> str:
    """
    Get ISO week identifier string (YYYY-WXX format).

    Args:
        dt: datetime object (defaults to now)

    Returns:
        String like '2026-W04' for week 4 of 2026
    """
    if dt is None:
        dt = datetime.now()
    iso_cal = dt.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"


def get_current_dir() -> Path:
    """
    Get the 'current' output directory for latest outputs.

    This directory always contains the most recent week's outputs,
    making it easy to find files without knowing the exact date.

    Returns:
        Path to trades/current/
    """
    return TRADES_DIR / "current"


def get_week_dir(dt: datetime = None) -> Path:
    """
    Get the weekly archive directory for a specific date.

    Args:
        dt: datetime object (defaults to now)

    Returns:
        Path to trades/weeks/YYYY-WXX/
    """
    week_id = get_week_identifier(dt)
    return TRADES_DIR / "weeks" / week_id


def ensure_output_structure() -> Tuple[Path, Path]:
    """
    Ensure all output directories exist.

    Creates:
    - trades/current/
    - trades/current/substack_notes/
    - trades/current/charts/
    - trades/current/tweets/
    - trades/weeks/YYYY-WXX/
    - trades/weeks/YYYY-WXX/substack_notes/
    - trades/weeks/YYYY-WXX/charts/
    - trades/weeks/YYYY-WXX/tweets/
    - trades/portfolio_backups/

    Returns:
        Tuple of (current_dir, week_dir)
    """
    current_dir = get_current_dir()
    week_dir = get_week_dir()

    # Create directory structures
    subdirs = ['substack_notes', 'charts', 'tweets']

    for subdir in subdirs:
        (current_dir / subdir).mkdir(parents=True, exist_ok=True)
        (week_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Also ensure root current and week dirs exist
    current_dir.mkdir(parents=True, exist_ok=True)
    week_dir.mkdir(parents=True, exist_ok=True)

    # Ensure portfolio backups dir exists
    (TRADES_DIR / "portfolio_backups").mkdir(exist_ok=True)

    return current_dir, week_dir


def get_output_paths() -> Dict[str, Path]:
    """
    Get all standard output paths as a dictionary.

    Returns:
        Dict with keys: 'trades', 'current', 'week', 'backups'
    """
    return {
        'trades': TRADES_DIR,
        'current': get_current_dir(),
        'week': get_week_dir(),
        'backups': TRADES_DIR / "portfolio_backups"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_to_current_and_archive(content: str, filename: str) -> Tuple[Path, Path]:
    """
    Save a file to both current/ and weekly archive directories.

    Args:
        content: File content to write
        filename: Name of the file (e.g., 'signals.json')

    Returns:
        Tuple of (current_path, archive_path)
    """
    current_dir, week_dir = ensure_output_structure()

    current_path = current_dir / filename
    archive_path = week_dir / filename

    with open(current_path, 'w') as f:
        f.write(content)

    with open(archive_path, 'w') as f:
        f.write(content)

    return current_path, archive_path


def copy_to_current_and_archive(source: Path, filename: str = None) -> Tuple[Path, Path]:
    """
    Copy a file to both current/ and weekly archive directories.

    Args:
        source: Source file path
        filename: Optional override for destination filename

    Returns:
        Tuple of (current_path, archive_path)
    """
    current_dir, week_dir = ensure_output_structure()

    if filename is None:
        filename = source.name

    current_path = current_dir / filename
    archive_path = week_dir / filename

    shutil.copy(source, current_path)
    shutil.copy(source, archive_path)

    return current_path, archive_path


def create_legacy_symlinks():
    """
    Create symlinks from old file locations to new structure.

    This maintains backwards compatibility with scripts that
    reference old paths like trades/latest_report.txt

    Note: Only works on Unix-like systems (macOS, Linux)
    """
    current_dir = get_current_dir()

    # Mapping of old paths to new locations
    legacy_mappings = {
        'latest_report.txt': 'report.txt',
        'latest_newsletter_briefing.md': 'newsletter_briefing.md',
        'latest_newsletter.html': 'newsletter.html',
        'signals.json': 'signals.json',
    }

    for old_name, new_name in legacy_mappings.items():
        old_path = TRADES_DIR / old_name
        new_path = current_dir / new_name

        # Remove existing file/symlink
        if old_path.exists() or old_path.is_symlink():
            old_path.unlink()

        # Create symlink only if new file exists
        if new_path.exists():
            try:
                old_path.symlink_to(new_path)
            except OSError:
                # Symlinks may fail on Windows, copy instead
                shutil.copy(new_path, old_path)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def get_relative_path(path: Path) -> str:
    """
    Get path relative to current working directory for display.

    Args:
        path: Absolute path

    Returns:
        Relative path string if within cwd, else absolute path
    """
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def list_weekly_archives() -> list:
    """
    List all available weekly archive directories.

    Returns:
        List of week identifiers (e.g., ['2026-W03', '2026-W04'])
    """
    weeks_dir = TRADES_DIR / "weeks"
    if not weeks_dir.exists():
        return []

    return sorted([d.name for d in weeks_dir.iterdir() if d.is_dir()])


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Print current output paths and structure."""
    import argparse

    parser = argparse.ArgumentParser(description="Output path management")
    parser.add_argument("--init", action="store_true", help="Initialize directory structure")
    parser.add_argument("--symlinks", action="store_true", help="Create legacy symlinks")

    args = parser.parse_args()

    if args.init:
        print("Initializing output directory structure...")
        current_dir, week_dir = ensure_output_structure()
        print(f"  Created: {get_relative_path(current_dir)}")
        print(f"  Created: {get_relative_path(week_dir)}")
        return 0

    if args.symlinks:
        print("Creating legacy symlinks...")
        create_legacy_symlinks()
        print("  Done")
        return 0

    # Default: print paths
    print("\nOutput Paths:")
    print(f"  TRADES_DIR:  {TRADES_DIR}")
    print(f"  Current:     {get_current_dir()}")
    print(f"  This Week:   {get_week_dir()}")
    print(f"  Week ID:     {get_week_identifier()}")

    archives = list_weekly_archives()
    if archives:
        print(f"\nArchives ({len(archives)}):")
        for archive in archives[-5:]:  # Last 5
            print(f"    {archive}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
