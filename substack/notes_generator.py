#!/usr/bin/env python3
"""
SUBSTACK NOTES GENERATOR (single-slot wrapper)
===============================================

Generate a single Substack note for a specific slot, with state tracking
and cost logging.

Wraps daily_notes_generator — reuses its prompt builders, validation,
and template fallbacks. Adds:
  - Single-slot targeting via --slot N
  - State tracking to state/notes.json (status="generated")
  - Cost logging from Anthropic API usage

Usage:
    python -m substack.notes_generator --slot 1
    python -m substack.notes_generator --slot 2 --dry-run
    python -m substack.notes_generator --slot 1 --no-llm
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state" / "notes.json"
ET = ZoneInfo("US/Eastern")


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

def _load_notes_state() -> Dict:
    """Load state/notes.json, returning default scaffold if missing."""
    default = {
        "last_updated": None,
        "today": {
            "date": None,
            "notes_published": 0,
            "notes_target": 3,
            "slots": [],
        },
        "recent": [],
    }
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text())
        return data if isinstance(data, dict) else default
    except (json.JSONDecodeError, IOError):
        return default


def _save_notes_state(state: Dict):
    """Write state/notes.json."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def mark_generated(slot: int, day: str, note_type: str, cost_usd: float = 0.0):
    """Update state/notes.json after note generation.

    Creates or updates a slot entry with status="generated", timestamp,
    note type, and estimated API cost.
    """
    state = _load_notes_state()
    now = datetime.now(ET)
    today_str = now.strftime("%Y-%m-%d")

    # Reset today if date changed
    if state.get("today", {}).get("date") != today_str:
        state["today"] = {
            "date": today_str,
            "notes_published": 0,
            "notes_target": 3,
            "slots": [],
        }

    # Find existing slot entry or create new one
    existing = next(
        (s for s in state["today"]["slots"] if s.get("slot") == slot), None
    )

    if existing:
        existing["status"] = "generated"
        existing["generated_at"] = now.isoformat()
        existing["cost_usd"] = cost_usd
        existing["note_type"] = note_type
    else:
        state["today"]["slots"].append({
            "slot": slot,
            "note_type": note_type,
            "status": "generated",
            "generated_at": now.isoformat(),
            "cost_usd": cost_usd,
        })
        state["today"]["slots"] = sorted(
            state["today"]["slots"], key=lambda s: s.get("slot", 0)
        )

    # Update recent array (generation events, capped at 21)
    state.setdefault("recent", []).append({
        "date": today_str,
        "slot": slot,
        "note_type": note_type,
        "status": "generated",
    })
    state["recent"] = state["recent"][-21:]

    state["last_updated"] = now.isoformat()
    _save_notes_state(state)

    logger.info(
        "State: slot %d marked generated (%s, $%.4f)",
        slot, note_type, cost_usd,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_slot(
    slot: int,
    day: str = None,
    dry_run: bool = False,
    no_llm: bool = False,
) -> Dict:
    """Generate a single slot's note and update state tracking.

    Calls daily_notes_generator.generate_daily_notes() — which generates
    all notes for the day — then extracts the requested slot's data.

    Returns: {"success": bool, "slot": int, "note_type": str, ...}
    """
    from substack.daily_notes_generator import generate_daily_notes, NOTES_SCHEDULE

    if day is None:
        day = datetime.now(ET).strftime("%A").lower()

    # Check schedule
    schedule = NOTES_SCHEDULE.get(day.lower(), [])
    if slot > len(schedule):
        return {
            "success": False,
            "slot": slot,
            "error": f"Slot {slot} exceeds schedule ({len(schedule)} slots for {day})",
        }

    note_type = schedule[slot - 1][0]

    if dry_run:
        logger.info("DRY RUN — would generate slot %d (%s) for %s", slot, note_type, day)
        return {"success": True, "slot": slot, "note_type": note_type, "cost": 0.0}

    # Generate all notes for the day (idempotent — re-generates if already exist)
    notes = generate_daily_notes(
        day=day,
        dry_run=False,
        no_llm=no_llm,
        html_output=True,
    )

    # Find the requested slot
    note = next((n for n in notes if n.get("slot") == slot), None)
    if not note:
        return {
            "success": False,
            "slot": slot,
            "note_type": note_type,
            "error": f"Generation produced no note for slot {slot}",
        }

    cost = note.get("cost", 0.0)

    # Update state/notes.json with "generated" status
    mark_generated(slot, day, note_type, cost_usd=cost)

    return {
        "success": True,
        "slot": slot,
        "note_type": note_type,
        "filepath": note.get("filepath"),
        "word_count": note.get("word_count", 0),
        "cost": cost,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Substack Notes Generator — single-slot generation with state tracking",
    )
    parser.add_argument(
        "--slot", type=int, choices=[1, 2, 3], required=True,
        help="Slot number to generate (1, 2, or 3)",
    )
    parser.add_argument(
        "--day", type=str, default=None,
        help="Override day of week (e.g., wednesday)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without generating or saving",
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Use template fallback (no API cost)",
    )
    args = parser.parse_args()

    result = generate_slot(
        slot=args.slot,
        day=args.day,
        dry_run=args.dry_run,
        no_llm=args.no_llm,
    )

    print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
    if result.get("note_type"):
        print(f"Type:   {result['note_type']}")
    if result.get("filepath"):
        print(f"File:   {result['filepath']}")
    if result.get("cost", 0) > 0:
        print(f"Cost:   ${result['cost']:.4f}")
    if result.get("error"):
        print(f"Error:  {result['error']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
