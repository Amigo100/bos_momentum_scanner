#!/usr/bin/env python3
"""
Weekly plan read/inspect utilities for Sterling Signals.

Reads the weekly plan JSON that Cowork's Sunday planner generates inline,
provides lookup functions for other scripts (send_single_note, build_daily_email),
and offers a CLI for quick inspection.

The weekly plan lives at:
    substack/output/current/weekly_plan_{YYYY}-W{XX}.json

Usage:
    python3 -m scripts.build_weekly_plan --show          # Full weekly plan
    python3 -m scripts.build_weekly_plan --today         # Today's plan entry
    python3 -m scripts.build_weekly_plan --check-ready   # Content readiness check
    python3 -m scripts.build_weekly_plan --date 2026-03-11 --today  # Override date
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from config.output_paths import SUBSTACK_OUTPUT, SCANNER_OUTPUT, SIGNALS_FILE


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

ET = ZoneInfo("America/New_York")

CURRENT_DIR = SUBSTACK_OUTPUT / "current"
NOTES_DIR = CURRENT_DIR / "notes"
POSTS_DIR = CURRENT_DIR / "posts"
DIAGRAMS_DIR = CURRENT_DIR / "diagrams"
CAROUSELS_DIR = CURRENT_DIR / "carousels"

SLOTS = ("morning", "midday", "evening")


# ═══════════════════════════════════════════════════════════════════════════════
# DATE HELPER
# ═══════════════════════════════════════════════════════════════════════════════


def _get_today_et() -> date:
    """Return today's date in US Eastern time."""
    return datetime.now(ET).date()


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════


def get_current_week_plan() -> Optional[Dict]:
    """Load the latest weekly plan JSON from substack/output/current/.

    Globs for ``weekly_plan_*.json`` and returns the most recent by
    filename sort (ISO week identifiers sort chronologically).

    Returns:
        Parsed plan dict, or None if no plan exists or parse fails.
    """
    plans = sorted(CURRENT_DIR.glob("weekly_plan_*.json"))
    if not plans:
        return None
    try:
        return json.loads(plans[-1].read_text())
    except (json.JSONDecodeError, OSError):
        return None


def get_today_plan(
    plan: Optional[Dict] = None,
    target_date: Optional[date] = None,
) -> Optional[Dict]:
    """Look up today's entry in the weekly plan.

    Args:
        plan: Parsed weekly plan dict. If None, loads via
            :func:`get_current_week_plan`.
        target_date: Override date. Defaults to today in ET.

    Returns:
        The day dict (e.g. ``{"post": "theme_rotation", "notes": [...],
        "visual": "diagram"}``) or None if the day isn't in the plan.
    """
    if plan is None:
        plan = get_current_week_plan()
    if not plan:
        return None

    if target_date is None:
        target_date = _get_today_et()

    day_name = target_date.strftime("%A")  # e.g. "Monday"
    days = plan.get("days", {})
    return days.get(day_name)


def check_content_ready(target_date: Optional[date] = None) -> Dict:
    """Check file existence for today's expected content.

    Scans the output directories for post, note, and visual files
    matching *target_date*.

    Args:
        target_date: Override date. Defaults to today in ET.

    Returns:
        Dict with structure::

            {
                "post": bool,
                "notes": {"morning": bool, "midday": bool, "evening": bool},
                "visual": bool,
                "all_ready": bool,
            }

        ``all_ready`` is True only when at least one note exists.
    """
    if target_date is None:
        target_date = _get_today_et()

    date_str = target_date.strftime("%Y%m%d")

    # Post check
    post_ready = False
    if POSTS_DIR.exists():
        post_ready = bool(list(POSTS_DIR.glob(f"*_{date_str}.html")))

    # Notes check per slot
    notes_ready = {}
    for slot in SLOTS:
        found = False
        if NOTES_DIR.exists():
            for f in NOTES_DIR.glob(f"{slot}_*_{date_str}.html"):
                if "_graphic_" not in f.name:
                    found = True
                    break
        notes_ready[slot] = found

    # Visual check (diagrams or carousels)
    visual_ready = False
    for d in (DIAGRAMS_DIR, CAROUSELS_DIR):
        if d.exists() and list(d.glob(f"*{date_str}*")):
            visual_ready = True
            break

    any_note = any(notes_ready.values())

    return {
        "post": post_ready,
        "notes": notes_ready,
        "visual": visual_ready,
        "all_ready": any_note,
    }


def check_new_signals(plan: Optional[Dict] = None) -> List[str]:
    """Find buy-signal tickers not present in the weekly plan.

    Loads ``scanner/output/signals.json``, extracts ``buy_signals[].symbol``,
    and compares against tickers mentioned anywhere in the plan's day entries.

    Args:
        plan: Parsed weekly plan dict. If None, loads via
            :func:`get_current_week_plan`.

    Returns:
        List of ticker strings present in signals but absent from the plan.
        Returns all buy tickers if no plan exists.
    """
    if not SIGNALS_FILE.exists():
        return []

    try:
        signals = json.loads(SIGNALS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    buy_tickers = [s.get("symbol", "") for s in signals.get("buy_signals", [])]
    if not buy_tickers:
        return []

    if plan is None:
        plan = get_current_week_plan()
    if not plan:
        return buy_tickers  # All are new if no plan exists

    # Extract planned tickers from weekly plan
    planned = set()
    for day_data in plan.get("days", {}).values():
        if isinstance(day_data, list):
            items = day_data
        elif isinstance(day_data, dict):
            items = [day_data]
        else:
            continue
        for item in items:
            if isinstance(item, dict):
                ticker = item.get("ticker", "")
                if ticker:
                    planned.add(ticker.upper())

    return [t for t in buy_tickers if t.upper() not in planned]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _print_full_plan(plan: Dict) -> None:
    """Pretty-print the full weekly plan."""
    week = plan.get("week", "?")
    generated = plan.get("generated", "?")
    print(f"\n  Weekly Plan: {week}")
    print(f"  Generated:   {generated}\n")

    days = plan.get("days", {})
    for day_name in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                     "Saturday", "Sunday"):
        entry = days.get(day_name)
        if entry is None:
            continue

        print(f"  {day_name}")

        if isinstance(entry, dict):
            post = entry.get("post", None)
            notes = entry.get("notes", [])
            visual = entry.get("visual", None)
            print(f"    Post:   {post or '—'}")
            if notes:
                print(f"    Notes:  {', '.join(str(n) for n in notes)}")
            else:
                print(f"    Notes:  —")
            print(f"    Visual: {visual or '—'}")
        else:
            print(f"    {entry}")

        print()


def _print_today_plan(entry: Dict, day_name: str) -> None:
    """Pretty-print today's plan entry."""
    print(f"\n  {day_name}'s Plan\n")

    if isinstance(entry, dict):
        post = entry.get("post", None)
        notes = entry.get("notes", [])
        visual = entry.get("visual", None)
        print(f"    Post:   {post or '—'}")
        if notes:
            for i, n in enumerate(notes, 1):
                print(f"    Note {i}: {n}")
        else:
            print(f"    Notes:  —")
        print(f"    Visual: {visual or '—'}")
    else:
        print(f"    {entry}")
    print()


def _print_readiness(ready: Dict, target_date: date) -> None:
    """Pretty-print content readiness check."""
    ok = "\u2713"   # ✓
    miss = "\u2717"  # ✗

    print(f"\n  Content Readiness — {target_date.isoformat()}\n")
    print(f"    Post:    {ok if ready['post'] else miss}")
    for slot in SLOTS:
        s = ready["notes"].get(slot, False)
        print(f"    {slot.title():8s} {ok if s else miss}")
    print(f"    Visual:  {ok if ready['visual'] else miss}")
    print(f"\n    All ready: {'YES' if ready['all_ready'] else 'NO'}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Weekly plan utilities for Sterling Signals"
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Pretty-print the full weekly plan",
    )
    parser.add_argument(
        "--today", action="store_true",
        help="Show today's plan entry",
    )
    parser.add_argument(
        "--check-ready", action="store_true",
        help="Check content readiness for today",
    )
    parser.add_argument(
        "--date",
        help="Override date (YYYY-MM-DD). Defaults to today in ET.",
    )
    args = parser.parse_args()

    # Determine target date
    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = _get_today_et()

    if not (args.show or args.today or args.check_ready):
        parser.print_help()
        return

    print(f"\n{'='*50}")
    print(f"  WEEKLY PLAN — {target_date.isoformat()}")
    print(f"{'='*50}")

    # --show: full plan
    if args.show:
        plan = get_current_week_plan()
        if not plan:
            print("\n  No weekly plan found.")
            print(f"  Expected: {CURRENT_DIR}/weekly_plan_*.json\n")
            sys.exit(1)
        _print_full_plan(plan)

    # --today: today's entry
    if args.today:
        plan = get_current_week_plan()
        if not plan:
            print("\n  No weekly plan found.\n")
            sys.exit(1)
        day_name = target_date.strftime("%A")
        entry = get_today_plan(plan, target_date)
        if not entry:
            print(f"\n  No entry for {day_name} in the plan.\n")
            sys.exit(1)
        _print_today_plan(entry, day_name)

    # --check-ready: file readiness
    if args.check_ready:
        ready = check_content_ready(target_date)
        _print_readiness(ready, target_date)

        # Also check for new signals
        plan = get_current_week_plan()
        new_sigs = check_new_signals(plan)
        if new_sigs:
            print(f"  New signals not in plan: {', '.join(new_sigs)}\n")

    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
