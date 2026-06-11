#!/usr/bin/env python3
"""
APPEND SIGNAL HISTORY — Post-session signal history updater
============================================================

Appends new rows to signal_history_rows.csv after a Claude.ai analysis session.

Usage:
    # Single row as CLI argument:
    python3 -m scripts.append_signal_history "2026-03-08,TICK1,12.50,T1,theme_name,7.80,STRONG,yes,BUY"

    # Pipe mode: echo or cat rows via stdin
    echo "2026-03-08,TEST,10.00,T2,test_theme,6.50,MODERATE,no,NO GO" | \\
        python3 -m scripts.append_signal_history --stdin

    # Interactive mode: paste rows from Claude.ai, empty line to finish
    python3 -m scripts.append_signal_history --interactive
"""

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.output_paths import SIGNAL_HISTORY_FILE

EXPECTED_HEADER = "date,ticker,price,tier,theme,composite_score,system_fit,advanced,session_verdict"
EXPECTED_COLS = EXPECTED_HEADER.split(",")
NUM_COLS = len(EXPECTED_COLS)


def validate_row(line: str, line_num: int) -> bool:
    """Validate a single CSV row has the expected number of fields."""
    line = line.strip()
    if not line:
        return False  # Skip blank lines
    fields = line.split(",")
    if len(fields) != NUM_COLS:
        print(f"  WARN line {line_num}: expected {NUM_COLS} fields, got {len(fields)}: {line[:80]}")
        return False
    return True


def ensure_file_with_header() -> None:
    """Create signal_history_rows.csv with header if it doesn't exist."""
    if not SIGNAL_HISTORY_FILE.exists():
        SIGNAL_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SIGNAL_HISTORY_FILE.write_text(EXPECTED_HEADER + "\n")
        print(f"  Created new file: {SIGNAL_HISTORY_FILE}")


def count_existing_rows() -> int:
    """Count existing data rows (excluding header)."""
    if not SIGNAL_HISTORY_FILE.exists():
        return 0
    lines = SIGNAL_HISTORY_FILE.read_text().strip().split("\n")
    return max(0, len(lines) - 1)  # Subtract header


def append_rows(raw_input: str) -> int:
    """Append validated rows to signal history file. Returns count appended."""
    ensure_file_with_header()

    lines = raw_input.strip().split("\n")
    valid_rows = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        # Skip if it looks like the header
        if line.lower().startswith("date,ticker,price"):
            print(f"  Skipping header row: {line[:60]}...")
            continue
        if validate_row(line, i):
            valid_rows.append(line)

    if not valid_rows:
        print("  No valid rows to append.")
        return 0

    # Append to file
    with open(SIGNAL_HISTORY_FILE, "a") as f:
        for row in valid_rows:
            f.write(row + "\n")

    return len(valid_rows)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Append rows to signal_history_rows.csv")
    parser.add_argument("row", nargs="?", default=None, help="Single CSV row to append")
    parser.add_argument("--stdin", action="store_true", help="Read rows from stdin (pipe mode)")
    parser.add_argument("--interactive", action="store_true", help="Paste rows interactively (empty line to finish)")
    args = parser.parse_args()

    # Validate: at least one mode must be specified
    if not args.row and not args.stdin and not args.interactive:
        parser.error("Provide a row argument, --stdin, or --interactive")

    print(f"\n  Signal history file: {SIGNAL_HISTORY_FILE}")
    before = count_existing_rows()
    print(f"  Existing rows: {before}")

    if args.row:
        raw = args.row
    elif args.interactive:
        print(f"\n  Expected format ({NUM_COLS} columns):")
        print(f"    {EXPECTED_HEADER}")
        print(f"\n  Paste signal history rows from Prompt 8 (empty line to finish):\n")
        lines = []
        for line in sys.stdin:
            if line.strip() == "":
                break
            lines.append(line.rstrip("\n"))
        raw = "\n".join(lines)
    else:
        raw = sys.stdin.read()

    count = append_rows(raw)

    after = count_existing_rows()
    print(f"\n  Appended: {count} rows")
    print(f"  Total rows: {before} -> {after}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
