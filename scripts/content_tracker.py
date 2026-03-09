#!/usr/bin/env python3
"""
Track Substack publishing status — posts and notes per week.

Auto-initializes from content_schedule.json when a new week starts.
Maintains streak counters for consecutive publishing days.

Usage:
    python3 -m scripts.content_tracker --status
    python3 -m scripts.content_tracker --published post
    python3 -m scripts.content_tracker --published notes
    python3 -m scripts.content_tracker --published post --date 2026-03-02
    python3 -m scripts.content_tracker --streak
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from config.output_paths import SUBSTACK_OUTPUT, BASE_DIR
from scripts.build_daily_email import normalise_category


# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

TRACKER_PATH = BASE_DIR / "state" / "content_tracker.json"
SCHEDULE_PATH = SUBSTACK_OUTPUT / "current" / "content_schedule.json"

DAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

EMPTY_TRACKER = {
    "current_week": None,
    "posts": [],
    "notes": [],
    "streak": {
        "posts_on_schedule": 0,
        "notes_streak": 0,
        "last_post_date": None,
        "last_note_date": None,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def iso_week_string(d: date) -> str:
    """Return ISO week string like '2026-W10' for a given date.

    The content schedule runs Sun-Sat, but ISO weeks run Mon-Sun.
    Sunday belongs to the NEXT ISO week for content tracking purposes,
    so we shift Sundays forward by 1 day before calculating.
    """
    # If Sunday (weekday 6), use Monday's ISO week so Sun groups with Mon-Sat
    effective = d + timedelta(days=1) if d.weekday() == 6 else d
    iso_year, iso_week, _ = effective.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def get_week_dates(iso_week_str: str) -> dict:
    """Map each schedule day (Sun-Sat) to its date for the given ISO week.

    The content schedule runs Sunday to Saturday. ISO week N starts on Monday,
    so Sunday = Monday of ISO week minus 1 day.

    Returns: {"Sunday": date(2026,3,1), "Monday": date(2026,3,2), ...}
    """
    # Parse "2026-W10" -> year=2026, week=10
    parts = iso_week_str.split("-W")
    year = int(parts[0])
    week = int(parts[1])

    # ISO week Monday: use strptime with %G-%V-%u (ISO year, week, weekday)
    monday = datetime.strptime(f"{year}-{week:02d}-1", "%G-%V-%u").date()
    sunday = monday - timedelta(days=1)

    return {
        "Sunday": sunday,
        "Monday": monday,
        "Tuesday": monday + timedelta(days=1),
        "Wednesday": monday + timedelta(days=2),
        "Thursday": monday + timedelta(days=3),
        "Friday": monday + timedelta(days=4),
        "Saturday": monday + timedelta(days=5),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD / SAVE
# ═══════════════════════════════════════════════════════════════════════════════

def load_tracker() -> dict:
    """Load content tracker from JSON. Creates scaffold if file missing."""
    if not TRACKER_PATH.exists():
        save_tracker(EMPTY_TRACKER)
        return dict(EMPTY_TRACKER)
    try:
        data = json.loads(TRACKER_PATH.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return dict(EMPTY_TRACKER)


def save_tracker(data: dict) -> None:
    """Write content tracker to JSON with 2-space indent."""
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text(json.dumps(data, indent=2) + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# INIT WEEK
# ═══════════════════════════════════════════════════════════════════════════════

def init_week(target_date: date = None) -> dict:
    """Initialize tracker for the ISO week containing target_date.

    Reads content_schedule.json and maps each day to a post record.
    Preserves streak data from the previous week.
    """
    if target_date is None:
        target_date = date.today()

    week_str = iso_week_string(target_date)
    week_dates = get_week_dates(week_str)

    # Preserve streak from current tracker
    old_tracker = load_tracker()
    old_streak = old_tracker.get("streak", EMPTY_TRACKER["streak"])

    # Load schedule
    posts = []
    try:
        schedule_data = json.loads(SCHEDULE_PATH.read_text())
        schedule = schedule_data.get("schedule", [])

        for entry in schedule:
            day_name = entry.get("day", "")
            day_date = week_dates.get(day_name)
            if not day_date:
                continue

            raw_cat = entry.get("category", "")
            is_notes_only = raw_cat == "NOTES_ONLY"

            posts.append({
                "date": day_date.isoformat(),
                "day": day_name,
                "category": None if is_notes_only else normalise_category(raw_cat),
                "topic": entry.get("topic", ""),
                "status": "pending",
                "note_types": entry.get("note_types", []),
            })

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # Fallback: minimal entry for today only
        day_name = DAY_ORDER[target_date.weekday()]
        # Python weekday: Mon=0..Sun=6 → need to map to our Sun-Sat order
        day_name = target_date.strftime("%A")
        posts.append({
            "date": target_date.isoformat(),
            "day": day_name,
            "category": None,
            "topic": "",
            "status": "pending",
            "note_types": [],
        })

    tracker = {
        "current_week": week_str,
        "posts": posts,
        "notes": old_tracker.get("notes", []),
        "streak": old_streak,
    }

    save_tracker(tracker)
    return tracker


# ═══════════════════════════════════════════════════════════════════════════════
# ENSURE CURRENT WEEK (lightweight, for wiring into other scripts)
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_current_week(target_date: date = None) -> str:
    """Check tracker matches the ISO week; initialize if not.

    Returns the ISO week string. Prints one status line.
    """
    if target_date is None:
        target_date = date.today()

    week_str = iso_week_string(target_date)
    tracker = load_tracker()

    if tracker.get("current_week") == week_str:
        print(f"  \u2713 Content tracker: {week_str}")
    else:
        init_week(target_date)
        print(f"  \u2713 Content tracker: initialized {week_str}")

    return week_str


# ═══════════════════════════════════════════════════════════════════════════════
# MARK PUBLISHED
# ═══════════════════════════════════════════════════════════════════════════════

def mark_published(content_type: str, target_date: date = None) -> None:
    """Mark a post or notes as published for the given date.

    Args:
        content_type: "post" or "notes"
        target_date: Date to mark (defaults to today)
    """
    if target_date is None:
        target_date = date.today()

    tracker = load_tracker()

    # Auto-init if needed
    week_str = iso_week_string(target_date)
    if tracker.get("current_week") != week_str:
        tracker = init_week(target_date)

    date_str = target_date.isoformat()
    now_str = datetime.now().isoformat(timespec="seconds")

    if content_type == "post":
        found = False
        for post in tracker["posts"]:
            if post["date"] == date_str:
                post["status"] = "published"
                post["published_at"] = now_str
                found = True
                break
        if not found:
            print(f"  \u2717 No post entry for {date_str} in tracker")
            return
        print(f"  \u2713 Marked post published: {date_str}")

    elif content_type == "notes":
        # Append notes entry (or update existing)
        existing = next(
            (n for n in tracker["notes"] if n["date"] == date_str), None
        )
        if existing:
            existing["published_at"] = now_str
            print(f"  \u2713 Updated notes published: {date_str}")
        else:
            tracker["notes"].append({
                "date": date_str,
                "slots": 3,
                "published_at": now_str,
            })
            print(f"  \u2713 Marked notes published: {date_str}")
    else:
        print(f"  \u2717 Unknown content type: {content_type}")
        return

    # Recalculate streaks
    _recalculate_streaks(tracker)
    save_tracker(tracker)


def _recalculate_streaks(tracker: dict) -> None:
    """Recalculate streak counters from posts and notes data."""
    streak = tracker.get("streak", {})

    # Posts on schedule: count consecutive post days (skip notes-only)
    # where status = "published", working backwards from today
    today_str = date.today().isoformat()
    post_days = [
        p for p in tracker.get("posts", [])
        if p.get("category") is not None and p["date"] <= today_str
    ]
    # Sort by date descending
    post_days.sort(key=lambda p: p["date"], reverse=True)

    posts_on_schedule = 0
    for p in post_days:
        if p.get("status") == "published":
            posts_on_schedule += 1
        else:
            break

    # Notes streak: count consecutive days where a notes entry exists,
    # working backwards from latest
    note_dates = sorted(
        [n["date"] for n in tracker.get("notes", [])],
        reverse=True,
    )

    notes_streak = 0
    if note_dates:
        # Start from the most recent note date and count backwards
        current = date.fromisoformat(note_dates[0])
        note_date_set = set(note_dates)
        while current.isoformat() in note_date_set:
            notes_streak += 1
            current -= timedelta(days=1)

    # Find last dates
    published_posts = [
        p["date"] for p in tracker.get("posts", [])
        if p.get("status") == "published" and p.get("category") is not None
    ]
    last_post_date = max(published_posts) if published_posts else streak.get("last_post_date")
    last_note_date = note_dates[0] if note_dates else streak.get("last_note_date")

    tracker["streak"] = {
        "posts_on_schedule": posts_on_schedule,
        "notes_streak": notes_streak,
        "last_post_date": last_post_date,
        "last_note_date": last_note_date,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def show_status() -> None:
    """Print formatted week status grid."""
    tracker = load_tracker()

    if not tracker.get("current_week"):
        # Auto-init
        tracker = init_week()

    week = tracker["current_week"]
    today_str = date.today().isoformat()

    print(f"\nWeek {week}:")

    for post in tracker.get("posts", []):
        d = post.get("date", "")
        day = post.get("day", "")[:3]
        category = post.get("category") or "Notes Only"
        status = post.get("status", "pending")

        # Format date as MM/DD
        try:
            d_obj = date.fromisoformat(d)
            date_display = d_obj.strftime("%m/%d")
        except (ValueError, TypeError):
            date_display = "??/??"

        # Status icon
        if status == "published":
            icon = "\u2705 Published"
        elif d == today_str and status == "pending":
            icon = "\u23f3 Pending"
        else:
            icon = "\u2b1c Not yet"

        print(f"  {day} {date_display}  {category:<24s} {icon}")

    # Streak summary
    streak = tracker.get("streak", {})
    posts_count = streak.get("posts_on_schedule", 0)
    notes_count = streak.get("notes_streak", 0)
    print(f"\nStreak: {posts_count} posts on schedule | {notes_count} notes days")


def show_streak() -> None:
    """Print just the streak numbers."""
    tracker = load_tracker()
    streak = tracker.get("streak", {})
    posts_count = streak.get("posts_on_schedule", 0)
    notes_count = streak.get("notes_streak", 0)
    last_post = streak.get("last_post_date", "never")
    last_note = streak.get("last_note_date", "never")

    print(f"Posts on schedule: {posts_count}")
    print(f"Notes streak:      {notes_count}")
    print(f"Last post:         {last_post or 'never'}")
    print(f"Last note:         {last_note or 'never'}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Content tracker CLI."""
    parser = argparse.ArgumentParser(
        description="Track Substack publishing status"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current week status grid",
    )
    parser.add_argument(
        "--published",
        choices=["post", "notes"],
        help="Mark content as published (post or notes)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date (YYYY-MM-DD format, defaults to today)",
    )
    parser.add_argument(
        "--streak",
        action="store_true",
        help="Show streak counters",
    )
    args = parser.parse_args()

    # Parse date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"  \u2717 Invalid date format: {args.date} (use YYYY-MM-DD)")
            return 2

    # Default to --status if no action specified
    if not args.status and not args.published and not args.streak:
        args.status = True

    # Ensure tracker is initialized for the right week
    effective_date = target_date or date.today()
    tracker = load_tracker()
    week_str = iso_week_string(effective_date)
    if tracker.get("current_week") != week_str:
        init_week(effective_date)

    # Execute action
    if args.published:
        mark_published(args.published, target_date)

    if args.status:
        show_status()

    if args.streak:
        show_streak()

    return 0


if __name__ == "__main__":
    sys.exit(main())
