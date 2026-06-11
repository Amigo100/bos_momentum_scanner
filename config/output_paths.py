#!/usr/bin/env python3
"""
OUTPUT PATHS - the lean Sterling system's path registry
=======================================================

Two data homes:
- scanner/output/   - the V10 scanner's outputs (signals_technical.json, analysis_log.csv,
                      archive/ dated copies)
- sterling-run/     - the state layer (signals, runs, research, weeks, decisions.json,
                      portfolio.csv) - paths owned by scripts/sterling_*.py

Usage:
    from config.output_paths import (
        SCANNER_OUTPUT, STERLING_RUN, PORTFOLIO_FILE,
        SIGNALS_TECH_FILE, ANALYSIS_LOG, ensure_output_structure,
    )
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent  # Project root (one level up from config/)

# ── Scanner outputs ───────────────────────────────────────────────────────────
SCANNER_OUTPUT = BASE_DIR / "scanner" / "output"
SIGNALS_TECH_FILE = SCANNER_OUTPUT / "signals_technical.json"
ANALYSIS_LOG = SCANNER_OUTPUT / "analysis_log.csv"

# ── The sterling-run state layer ──────────────────────────────────────────────
STERLING_RUN = BASE_DIR / "sterling-run"
STERLING_SIGNALS_FILE = STERLING_RUN / "signals" / "this-week.csv"

# THE single portfolio book (consolidated 2026-06-11): held positions + Entry Date,
# read by the V10 scanner's exit checks, the skills, and sterling_price_refresh.
PORTFOLIO_FILE = STERLING_RUN / "portfolio.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_week_identifier(dt: Optional[datetime] = None) -> str:
    """ISO week identifier string (YYYY-WXX)."""
    if dt is None:
        dt = datetime.now()
    iso_cal = dt.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"


def ensure_output_structure() -> Tuple[Path, Path]:
    """Ensure the scanner + sterling-run output directories exist."""
    archive_dir = SCANNER_OUTPUT / "archive"
    SCANNER_OUTPUT.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    (STERLING_RUN / "signals" / "archive").mkdir(parents=True, exist_ok=True)
    return SCANNER_OUTPUT, archive_dir


def get_output_paths() -> Dict[str, Path]:
    return {
        "scanner": SCANNER_OUTPUT,
        "sterling_run": STERLING_RUN,
        "portfolio": PORTFOLIO_FILE,
        "signals": SIGNALS_TECH_FILE,
    }


def get_relative_path(path: Path) -> str:
    """Path relative to the current working directory, for display."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Output path management")
    parser.add_argument("--init", action="store_true", help="Initialize directory structure")
    args = parser.parse_args()
    if args.init:
        ensure_output_structure()
        print("Output directories created.")
        return 0
    print("\nOutput Paths:")
    for name, p in get_output_paths().items():
        print(f"  {name:12} {p}")
    print(f"  {'week_id':12} {get_week_identifier()}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
