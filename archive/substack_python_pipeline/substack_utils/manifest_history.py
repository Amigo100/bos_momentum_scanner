"""
Read recent daily manifests from the archive to prevent duplicate content.

Used by:
    - COWORK_INSTRUCTIONS.md Section 4 (Duplicate Content Prevention)
    - Can also be called from scripts/build_daily_email.py if needed

Archive structure:
    substack/output/archive/YYYY-WXX/{day}/daily_manifest.json  (new format)
    substack/output/archive/YYYY-WXX/daily_manifest.json        (flat format)
    substack/output/current/daily_manifest.json                  (today)
"""

import glob
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config.output_paths import SUBSTACK_OUTPUT, TWITTER_OUTPUT

# --- Paths ---
ARCHIVE_ROOT = SUBSTACK_OUTPUT / "archive"
CURRENT_MANIFEST = SUBSTACK_OUTPUT / "current" / "daily_manifest.json"
LIVE_QUEUE_FILE = TWITTER_OUTPUT / "live_content_queue.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Optional[Dict]:
    """Load a JSON file, returning None on any error."""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a YYYY-MM-DD date string, returning None on failure."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_recent_manifests(days: int = 7) -> List[Dict]:
    """Return list of manifest dicts from the last *days* days.

    Searches both the archive directories and the current manifest.
    Results are sorted by date descending (newest first).

    Args:
        days: Lookback window in days (default 7).

    Returns:
        List of parsed manifest dicts, each guaranteed to have a ``"date"``
        field that falls within the lookback window.
    """
    cutoff = datetime.now() - timedelta(days=days)
    seen_dates: set = set()
    manifests: List[Dict] = []

    # 1. Scan archive directories (handles both flat and day-level structures)
    pattern = str(ARCHIVE_ROOT / "**" / "daily_manifest.json")
    for manifest_path in glob.glob(pattern, recursive=True):
        data = _load_json(Path(manifest_path))
        if data is None:
            continue
        manifest_date = data.get("date", "")
        dt = _parse_date(manifest_date)
        if dt is None or dt < cutoff:
            continue
        if manifest_date not in seen_dates:
            seen_dates.add(manifest_date)
            manifests.append(data)

    # 2. Include the current manifest (today's content)
    if CURRENT_MANIFEST.exists():
        data = _load_json(CURRENT_MANIFEST)
        if data is not None:
            manifest_date = data.get("date", "")
            dt = _parse_date(manifest_date)
            if dt is not None and dt >= cutoff and manifest_date not in seen_dates:
                seen_dates.add(manifest_date)
                manifests.append(data)

    # Sort newest first
    manifests.sort(key=lambda m: m.get("date", ""), reverse=True)
    return manifests


def was_ticker_covered(
    ticker: str,
    content_type: str,
    days: int = 21,
) -> Optional[Dict]:
    """Check if a ticker had a specific content type in the last *days* days.

    Args:
        ticker: Stock symbol, e.g. ``"ASTS"`` (case-insensitive, ``$`` prefix
            is stripped automatically).
        content_type: One of ``"deep_dive"``, ``"education"``,
            or ``"weekly_briefing"``.
        days: Lookback window (default 21 — 3 weeks for Deep Dives,
            use 7 for signal/exit posts).

    Returns:
        ``{"covered": True, "last_date": "2026-03-05", "last_title": "..."}``
        if the ticker was covered, or ``None`` if not found.
    """
    ticker_clean = ticker.upper().lstrip("$")
    manifests = get_recent_manifests(days)

    for m in manifests:
        post = m.get("post") or {}
        category = (post.get("category") or "").lower()

        if category != content_type.lower():
            continue

        # Check ticker in title or filename
        title = (post.get("title") or "").upper()
        file_name = (post.get("file") or "").upper()

        # Match ticker as standalone token (avoid "FAST" matching "AST")
        ticker_variants = [ticker_clean, f"${ticker_clean}"]
        found = False
        for variant in ticker_variants:
            # Check in title (word boundary via space/punctuation)
            if variant in title:
                # Verify it's a standalone match, not a substring
                for token in title.replace("$", " ").split():
                    if token == ticker_clean:
                        found = True
                        break
            # Check in filename (ticker often appears as _TICKER_ or /TICKER_)
            if ticker_clean in file_name:
                found = True

        if found:
            return {
                "covered": True,
                "last_date": m.get("date", ""),
                "last_title": post.get("title") or "",
            }

    return None


def was_theme_covered(theme_name: str, days: int = 14) -> Optional[Dict]:
    """Check if a theme had a deep dive post in the last *days* days.

    Args:
        theme_name: Theme name, e.g. ``"AI Infrastructure"``
            (case-insensitive substring match).
        days: Lookback window (default 14 — 2 weeks).

    Returns:
        ``{"covered": True, "last_date": "2026-03-05", "last_title": "..."}``
        if the theme was covered, or ``None`` if not found.
    """
    theme_lower = theme_name.lower()
    manifests = get_recent_manifests(days)

    for m in manifests:
        post = m.get("post") or {}
        category = (post.get("category") or "").lower()

        if category != "deep_dive":
            continue

        title = (post.get("title") or "").lower()
        if theme_lower in title:
            return {
                "covered": True,
                "last_date": m.get("date", ""),
                "last_title": post.get("title") or "",
            }

    return None


def get_weekly_tweet_counts() -> Dict[str, int]:
    """Count tweets generated this week by category from the live queue.

    Reads ``twitter/output/live_content_queue.json``, filters items whose
    ``generated_at`` timestamp falls within the current ISO week, and
    returns counts per category.

    Returns:
        Dict like ``{"RECEIPT": 3, "SIGNAL_ALERT": 2}``.
        Returns an empty dict if the queue file is missing or unreadable.
    """
    data = _load_json(LIVE_QUEUE_FILE)
    if not isinstance(data, list):
        return {}

    now = datetime.now()
    current_iso = now.isocalendar()  # (year, week, weekday)

    counts: Dict[str, int] = {}
    for item in data:
        generated_at = item.get("generated_at", "")
        if not generated_at:
            continue

        try:
            dt = datetime.fromisoformat(generated_at)
            # Strip timezone for comparison (generated_at may be UTC-aware)
            dt_naive = dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        item_iso = dt_naive.isocalendar()
        if item_iso.year == current_iso.year and item_iso.week == current_iso.week:
            category = item.get("category", "UNKNOWN")
            counts[category] = counts.get(category, 0) + 1

    return counts
