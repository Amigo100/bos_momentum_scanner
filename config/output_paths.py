#!/usr/bin/env python3
"""
OUTPUT PATHS - Centralized folder structure management
======================================================

Path registry for the lean Sterling system. Each section owns its outputs:
- scanner/output/     - Scan results, signals, reports (the Friday technical scan)
- portfolio/output/   - Portfolio CSVs, equity curve, backups (the manager's book)
- substack/output/    - Cowork content working area (posts, notes, diagrams, carousels)
- sterling-run/       - The sterling-grid state layer (signals, runs, research, weeks,
                        decisions.json, portfolio.csv) — paths owned by scripts/sterling_*.py

Usage:
    from config.output_paths import (
        SCANNER_OUTPUT, PORTFOLIO_OUTPUT, SUBSTACK_OUTPUT, STERLING_RUN,
        get_scanner_current_dir, ensure_output_structure,
    )
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent  # Project root (one level up from config/)

# Section output roots
SCANNER_OUTPUT = BASE_DIR / "scanner" / "output"
PORTFOLIO_OUTPUT = BASE_DIR / "portfolio" / "output"
SUBSTACK_OUTPUT = BASE_DIR / "substack" / "output"

# The sterling-grid state layer (signals/this-week.csv, runs/, research/, weeks/, ledger)
STERLING_RUN = BASE_DIR / "sterling-run"
STERLING_SIGNALS_FILE = STERLING_RUN / "signals" / "this-week.csv"


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNER OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

SIGNALS_FILE = SCANNER_OUTPUT / "signals.json"
SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"
ANALYSIS_LOG = SCANNER_OUTPUT / "analysis_log.csv"
SIGNAL_HISTORY_FILE = SCANNER_OUTPUT / "signal_history_rows.csv"


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

PORTFOLIO_FILE = PORTFOLIO_OUTPUT / "portfolio.csv"
SHEETS_EXPORT_FILE = PORTFOLIO_OUTPUT / "portfolio_google_sheets.csv"
EQUITY_CURVE_FILE = PORTFOLIO_OUTPUT / "equity_curve.csv"
PORTFOLIO_BACKUP_DIR = PORTFOLIO_OUTPUT / "portfolio_backups"
PORTFOLIO_SNAPSHOT_FILE = PORTFOLIO_OUTPUT / "portfolio_snapshot.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_week_identifier(dt: Optional[datetime] = None) -> str:
    """Get ISO week identifier string (YYYY-WXX format)."""
    if dt is None:
        dt = datetime.now()
    iso_cal = dt.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"


def get_scanner_current_dir() -> Path:
    """Get scanner/output/current/ for latest scanner outputs."""
    return SCANNER_OUTPUT / "current"


def get_scanner_archive_dir(dt: Optional[datetime] = None) -> Path:
    """Get scanner/output/archive/YYYY-WXX/ for weekly archives."""
    week_id = get_week_identifier(dt)
    return SCANNER_OUTPUT / "archive" / week_id


def get_substack_current_dir() -> Path:
    """Get substack/output/current/ — the Cowork content working area."""
    return SUBSTACK_OUTPUT / "current"


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_output_structure() -> Tuple[Path, Path]:
    """
    Ensure the section output directories exist.

    Returns:
        Tuple of (scanner_current_dir, scanner_archive_dir) for backward compat.
    """
    scanner_current = get_scanner_current_dir()
    scanner_archive = get_scanner_archive_dir()

    scanner_current.mkdir(parents=True, exist_ok=True)
    scanner_archive.mkdir(parents=True, exist_ok=True)

    for subdir in ["posts", "notes", "diagrams", "carousels"]:
        (get_substack_current_dir() / subdir).mkdir(parents=True, exist_ok=True)

    PORTFOLIO_OUTPUT.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (STERLING_RUN / "signals").mkdir(parents=True, exist_ok=True)

    return scanner_current, scanner_archive


def get_output_paths() -> Dict[str, Path]:
    """Get all standard output paths as a dictionary."""
    return {
        'scanner': SCANNER_OUTPUT,
        'portfolio': PORTFOLIO_OUTPUT,
        'substack': SUBSTACK_OUTPUT,
        'sterling_run': STERLING_RUN,
        'scanner_current': get_scanner_current_dir(),
        'scanner_archive': get_scanner_archive_dir(),
        'substack_current': get_substack_current_dir(),
        'backups': PORTFOLIO_BACKUP_DIR,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def get_relative_path(path: Path) -> str:
    """Get path relative to current working directory for display."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


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

    print("\nOutput Paths:")
    print(f"  Scanner:      {SCANNER_OUTPUT}")
    print(f"    Current:    {get_scanner_current_dir()}")
    print(f"    Archive:    {get_scanner_archive_dir()}")
    print(f"  Portfolio:    {PORTFOLIO_OUTPUT}")
    print(f"  Substack:     {SUBSTACK_OUTPUT}")
    print(f"  Sterling run: {STERLING_RUN}")
    print(f"  Week ID:      {get_week_identifier()}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
