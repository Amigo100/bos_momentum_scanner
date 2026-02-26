#!/usr/bin/env python3
"""
OUTPUT PATHS - Centralized folder structure management
======================================================

Multi-section output path registry. Each section owns its outputs:
- scanner/output/     - Scan results, signals, reports
- portfolio/output/   - Portfolio CSVs, equity curve, backups
- substack/output/    - Newsletter, posts, notes
- twitter/output/     - Tweet queues, charts, tracking

Usage:
    from config.output_paths import (
        SCANNER_OUTPUT, PORTFOLIO_OUTPUT, SUBSTACK_OUTPUT, TWITTER_OUTPUT,
        get_scanner_current_dir, get_substack_current_dir,
        ensure_output_structure,
    )
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent  # Project root (one level up from config/)

# Section output roots
SCANNER_OUTPUT = BASE_DIR / "scanner" / "output"
PORTFOLIO_OUTPUT = BASE_DIR / "portfolio" / "output"
SUBSTACK_OUTPUT = BASE_DIR / "substack" / "output"
TWITTER_OUTPUT = BASE_DIR / "twitter" / "output"

# Legacy alias — DEPRECATED, kept for gradual migration
TRADES_DIR = BASE_DIR / "trades"


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNER OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

SIGNALS_FILE = SCANNER_OUTPUT / "signals.json"
SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"
ANALYSIS_LOG = SCANNER_OUTPUT / "analysis_log.csv"
SCAN_REPORT = SCANNER_OUTPUT / "scan_report.txt"


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

PORTFOLIO_FILE = PORTFOLIO_OUTPUT / "portfolio.csv"
SHEETS_EXPORT_FILE = PORTFOLIO_OUTPUT / "portfolio_google_sheets.csv"
EQUITY_CURVE_FILE = PORTFOLIO_OUTPUT / "equity_curve.csv"
PORTFOLIO_BACKUP_DIR = PORTFOLIO_OUTPUT / "portfolio_backups"
PORTFOLIO_SNAPSHOT_FILE = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"
PORTFOLIO_DASHBOARD_FILE = SUBSTACK_OUTPUT / "current" / "portfolio_dashboard.html"
PORTFOLIO_SUMMARY_PNG = SUBSTACK_OUTPUT / "current" / "portfolio_summary.png"


# ═══════════════════════════════════════════════════════════════════════════════
# TWITTER OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_QUEUE_FILE = TWITTER_OUTPUT / "content_queue.json"
CONTENT_QUEUE_ACCOUNT2_FILE = TWITTER_OUTPUT / "content_queue_account2.json"
CONTENT_QUEUE_ACCOUNT3_FILE = TWITTER_OUTPUT / "content_queue_account3.json"
DAILY_QUEUE_FILE = TWITTER_OUTPUT / "daily_content_queue.json"
DAILY_QUEUE_ACCOUNT2_FILE = TWITTER_OUTPUT / "daily_content_queue_account2.json"
DAILY_QUEUE_ACCOUNT3_FILE = TWITTER_OUTPUT / "daily_content_queue_account3.json"
LIVE_QUEUE_FILE = TWITTER_OUTPUT / "live_content_queue.json"
LIVE_CONTEXT_FILE = TWITTER_OUTPUT / "live_context.json"
LIVE_COST_LOG_FILE = TWITTER_OUTPUT / "live_cost_log.json"
TWEET_TRACKING_FILE = TWITTER_OUTPUT / "tweet_tracking.json"
CELEBRATIONS_FILE = TWITTER_OUTPUT / "celebrations.json"
FAILED_TWEETS_FILE = TWITTER_OUTPUT / "failed_tweets.json"
WORKFLOW_STATUS_FILE = TWITTER_OUTPUT / "workflow_status.json"
CHARTS_DIR = TWITTER_OUTPUT / "charts"

# Claude.ai-produced content storage
CLAUDE_CONTENT_DIR = SUBSTACK_OUTPUT / "claude_content"


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_week_identifier(dt: Optional[datetime] = None) -> str:
    """Get ISO week identifier string (YYYY-WXX format)."""
    if dt is None:
        dt = datetime.now()
    iso_cal = dt.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"


# ── Scanner directories ──────────────────────────────────────────────────────

def get_scanner_current_dir() -> Path:
    """Get scanner/output/current/ for latest scanner outputs."""
    return SCANNER_OUTPUT / "current"


def get_scanner_archive_dir(dt: Optional[datetime] = None) -> Path:
    """Get scanner/output/archive/YYYY-WXX/ for weekly archives."""
    week_id = get_week_identifier(dt)
    return SCANNER_OUTPUT / "archive" / week_id


# ── Substack directories ─────────────────────────────────────────────────────

def get_substack_current_dir() -> Path:
    """Get substack/output/current/ for latest substack outputs."""
    return SUBSTACK_OUTPUT / "current"


def get_substack_archive_dir(dt: Optional[datetime] = None) -> Path:
    """Get substack/output/archive/YYYY-WXX/ for weekly archives."""
    week_id = get_week_identifier(dt)
    return SUBSTACK_OUTPUT / "archive" / week_id


def get_claude_content_dir() -> Path:
    """Get substack/output/claude_content/ for Claude.ai-produced HTML files."""
    CLAUDE_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    return CLAUDE_CONTENT_DIR


# ── Legacy compatibility ──────────────────────────────────────────────────────

def get_current_dir() -> Path:
    """DEPRECATED: Use get_scanner_current_dir() or get_substack_current_dir()."""
    return get_scanner_current_dir()


def get_week_dir(dt: Optional[datetime] = None) -> Path:
    """DEPRECATED: Use get_scanner_archive_dir() or get_substack_archive_dir()."""
    return get_scanner_archive_dir(dt)


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_output_structure() -> Tuple[Path, Path]:
    """
    Ensure all section output directories exist.

    Creates all necessary directories across all sections.

    Returns:
        Tuple of (scanner_current_dir, scanner_archive_dir) for backward compat
    """
    scanner_current = get_scanner_current_dir()
    scanner_archive = get_scanner_archive_dir()
    substack_current = get_substack_current_dir()
    substack_archive = get_substack_archive_dir()

    # Scanner output dirs
    scanner_current.mkdir(parents=True, exist_ok=True)
    scanner_archive.mkdir(parents=True, exist_ok=True)

    # Substack output dirs with subdirs
    for d in [substack_current, substack_archive]:
        (d / "substack_notes").mkdir(parents=True, exist_ok=True)
        (d / "substack_posts").mkdir(parents=True, exist_ok=True)

    # Claude.ai content storage
    CLAUDE_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    # Portfolio output dirs
    PORTFOLIO_OUTPUT.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Twitter output dirs
    TWITTER_OUTPUT.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    return scanner_current, scanner_archive


def get_output_paths() -> Dict[str, Path]:
    """
    Get all standard output paths as a dictionary.

    Returns dict with section output roots and commonly used paths.
    """
    return {
        'scanner': SCANNER_OUTPUT,
        'portfolio': PORTFOLIO_OUTPUT,
        'substack': SUBSTACK_OUTPUT,
        'twitter': TWITTER_OUTPUT,
        'scanner_current': get_scanner_current_dir(),
        'scanner_archive': get_scanner_archive_dir(),
        'substack_current': get_substack_current_dir(),
        'substack_archive': get_substack_archive_dir(),
        'backups': PORTFOLIO_BACKUP_DIR,
        # Legacy aliases
        'trades': SCANNER_OUTPUT,
        'current': get_scanner_current_dir(),
        'week': get_scanner_archive_dir(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_to_scanner_current_and_archive(content: str, filename: str) -> Tuple[Path, Path]:
    """Save a file to both scanner current/ and archive/ directories."""
    ensure_output_structure()
    current_path = get_scanner_current_dir() / filename
    archive_path = get_scanner_archive_dir() / filename

    with open(current_path, 'w') as f:
        f.write(content)
    with open(archive_path, 'w') as f:
        f.write(content)

    return current_path, archive_path


def save_to_substack_current_and_archive(content: str, filename: str,
                                          subdir: Optional[str] = None) -> Tuple[Path, Path]:
    """Save a file to both substack current/ and archive/ directories."""
    ensure_output_structure()
    current_dir = get_substack_current_dir()
    archive_dir = get_substack_archive_dir()

    if subdir:
        current_dir = current_dir / subdir
        archive_dir = archive_dir / subdir
        current_dir.mkdir(parents=True, exist_ok=True)
        archive_dir.mkdir(parents=True, exist_ok=True)

    current_path = current_dir / filename
    archive_path = archive_dir / filename

    with open(current_path, 'w') as f:
        f.write(content)
    with open(archive_path, 'w') as f:
        f.write(content)

    return current_path, archive_path


# Legacy alias
def save_to_current_and_archive(content: str, filename: str) -> Tuple[Path, Path]:
    """DEPRECATED: Use save_to_scanner_current_and_archive() or save_to_substack_current_and_archive()."""
    return save_to_scanner_current_and_archive(content, filename)


def copy_to_current_and_archive(source: Path, filename: Optional[str] = None) -> Tuple[Path, Path]:
    """DEPRECATED: Copy to scanner current + archive."""
    ensure_output_structure()
    if filename is None:
        filename = source.name

    current_path = get_scanner_current_dir() / filename
    archive_path = get_scanner_archive_dir() / filename

    shutil.copy(source, current_path)
    shutil.copy(source, archive_path)

    return current_path, archive_path


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def get_relative_path(path: Path) -> str:
    """Get path relative to current working directory for display."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def list_weekly_archives(section: str = "scanner") -> List[str]:
    """
    List all available weekly archive directories for a section.

    Args:
        section: "scanner" or "substack"
    """
    if section == "scanner":
        archive_dir = SCANNER_OUTPUT / "archive"
    elif section == "substack":
        archive_dir = SUBSTACK_OUTPUT / "archive"
    else:
        archive_dir = SCANNER_OUTPUT / "archive"

    if not archive_dir.exists():
        return []

    return sorted([d.name for d in archive_dir.iterdir() if d.is_dir()])


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Print current output paths and structure."""
    import argparse

    parser = argparse.ArgumentParser(description="Output path management")
    parser.add_argument("--init", action="store_true", help="Initialize directory structure")
    args = parser.parse_args()

    if args.init:
        print("Initializing output directory structure...")
        ensure_output_structure()
        print("  All section output directories created.")
        return 0

    # Default: print paths
    print("\nOutput Paths:")
    print(f"  Scanner:     {SCANNER_OUTPUT}")
    print(f"    Current:   {get_scanner_current_dir()}")
    print(f"    Archive:   {get_scanner_archive_dir()}")
    print(f"  Portfolio:   {PORTFOLIO_OUTPUT}")
    print(f"  Substack:    {SUBSTACK_OUTPUT}")
    print(f"    Current:   {get_substack_current_dir()}")
    print(f"    Archive:   {get_substack_archive_dir()}")
    print(f"  Twitter:     {TWITTER_OUTPUT}")
    print(f"  Week ID:     {get_week_identifier()}")

    for section in ["scanner", "substack"]:
        archives = list_weekly_archives(section)
        if archives:
            print(f"\n  {section.title()} Archives ({len(archives)}):")
            for archive in archives[-5:]:
                print(f"    {archive}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
