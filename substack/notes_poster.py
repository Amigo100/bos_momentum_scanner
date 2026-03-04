#!/usr/bin/env python3
"""
SUBSTACK NOTES POSTER
=====================

Post generated Substack Notes via session cookie API.

Reads pre-generated HTML notes from substack/output/current/notes/,
converts to ProseMirror JSON, posts to Substack via session cookie.

The daily_content_pipeline (07:00 ET) generates all notes for the day.
This poster runs 3x daily (08:30, 12:30, 17:00 ET) to publish each slot.

If no pre-generated note exists, falls back to on-demand generation
via the existing daily_notes_generator.

Usage:
    python -m substack.notes_poster --slot 1              # Post slot 1
    python -m substack.notes_poster --slot 1 --dry-run    # Preview without posting
    python -m substack.notes_poster --check-cookie         # Test cookie validity
    python -m substack.notes_poster --slot 1 --day tuesday # Override day
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

NOTES_API_URL = "https://substack.com/api/v1/comment/feed"
COOKIE_CHECK_URL = "https://substack.com/api/v1/user/self"
STATE_FILE = BASE_DIR / "state" / "notes.json"
NOTES_OUTPUT_DIR = BASE_DIR / "substack" / "output" / "current" / "notes"

ET = ZoneInfo("US/Eastern")


# ═══════════════════════════════════════════════════════════════════════════════
# HTML → PROSEMIRROR CONVERSION
# ═══════════════════════════════════════════════════════════════════════════════

class NoteHTMLParser(HTMLParser):
    """Convert note HTML to ProseMirror paragraph nodes.

    Handles <p>, <strong>/<b>, <em>/<i>, <a href="...">, and plain text.
    Strips <div>, <html>, <head>, <body>, <meta>, <title>, <style> tags.
    Each <p> becomes a ProseMirror paragraph node with text + marks.
    """

    SKIP_TAGS = {"html", "head", "body", "meta", "title", "style", "div", "br"}
    MARK_TAGS = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic"}

    def __init__(self):
        super().__init__()
        self.paragraphs: List[Dict] = []
        self.current_content: List[Dict] = []
        self.mark_stack: List[Dict] = []
        self.in_paragraph = False
        self.in_skip_tag = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list):
        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            if tag in ("style", "title", "head"):
                self.in_skip_tag = True
                self._skip_depth += 1
            return

        if tag == "p":
            self.in_paragraph = True
            self.current_content = []
            return

        if tag in self.MARK_TAGS:
            self.mark_stack.append({"type": self.MARK_TAGS[tag]})
            return

        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.mark_stack.append({"type": "link", "attrs": {"href": href}})
            return

    def handle_endtag(self, tag: str):
        tag = tag.lower()

        if tag in ("style", "title", "head"):
            if self.in_skip_tag:
                self._skip_depth -= 1
                if self._skip_depth <= 0:
                    self.in_skip_tag = False
                    self._skip_depth = 0
            return

        if tag in self.SKIP_TAGS:
            return

        if tag == "p":
            if self.current_content:
                self.paragraphs.append({
                    "type": "paragraph",
                    "content": self.current_content,
                })
            self.in_paragraph = False
            self.current_content = []
            return

        if tag in self.MARK_TAGS or tag == "a":
            mark_type = self.MARK_TAGS.get(tag, "link")
            # Pop the matching mark from the stack
            for idx in range(len(self.mark_stack) - 1, -1, -1):
                if self.mark_stack[idx]["type"] == mark_type:
                    self.mark_stack.pop(idx)
                    break

    def handle_data(self, data: str):
        if self.in_skip_tag:
            return

        text = data
        if not text:
            return

        # If not inside a <p> but we have text, treat it as a standalone paragraph
        if not self.in_paragraph and text.strip():
            node = {"type": "text", "text": text}
            if self.mark_stack:
                node["marks"] = [dict(m) for m in self.mark_stack]
            self.paragraphs.append({
                "type": "paragraph",
                "content": [node],
            })
            return

        if self.in_paragraph:
            node = {"type": "text", "text": text}
            if self.mark_stack:
                node["marks"] = [dict(m) for m in self.mark_stack]
            self.current_content.append(node)

    def handle_entityref(self, name: str):
        """Handle HTML entities like &amp; &lt; etc."""
        import html
        char = html.unescape(f"&{name};")
        self.handle_data(char)

    def handle_charref(self, name: str):
        """Handle numeric character references like &#8212;"""
        import html
        char = html.unescape(f"&#{name};")
        self.handle_data(char)


def html_to_plain_text(html: str) -> str:
    """Strip all HTML tags, return plain text."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def html_to_prosemirror(html: str) -> Dict:
    """Convert note HTML to Substack ProseMirror JSON payload.

    Parses HTML paragraphs with inline marks (bold, italic, links)
    into ProseMirror document structure.

    Falls back to plain text in a single paragraph if parsing
    produces no content.
    """
    parser = NoteHTMLParser()
    try:
        parser.feed(html)
    except Exception as e:
        logger.warning("HTML parse error: %s — falling back to plain text", e)
        plain = html_to_plain_text(html)
        return {
            "type": "doc",
            "attrs": {"schemaVersion": "v1"},
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": plain}]}
            ],
        }

    paragraphs = parser.paragraphs
    if not paragraphs:
        # Fallback: strip HTML and wrap in single paragraph
        plain = html_to_plain_text(html)
        if plain:
            paragraphs = [
                {"type": "paragraph", "content": [{"type": "text", "text": plain}]}
            ]
        else:
            logger.error("HTML produced no content after parsing")
            return {"type": "doc", "attrs": {"schemaVersion": "v1"}, "content": []}

    return {
        "type": "doc",
        "attrs": {"schemaVersion": "v1"},
        "content": paragraphs,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COOKIE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_cookie() -> Optional[str]:
    """Get Substack session cookie from environment.

    Checks SUBSTACK_SESSION_COOKIE first, then SUBSTACK_SESSION_TOKEN
    (for compatibility with docs/SETUP.md MCP configuration).
    """
    cookie = os.environ.get("SUBSTACK_SESSION_COOKIE")
    if not cookie:
        cookie = os.environ.get("SUBSTACK_SESSION_TOKEN")
    if not cookie:
        logger.warning("SUBSTACK_SESSION_COOKIE not set")
        return None
    return cookie.strip()


def check_cookie_validity(cookie: str) -> Tuple[bool, str]:
    """Test if session cookie is still valid.

    Makes a lightweight request to /api/v1/user/self.
    Returns (is_valid, detail_message).
    """
    try:
        import requests
    except ImportError:
        return False, "requests package not installed"

    try:
        resp = requests.get(
            COOKIE_CHECK_URL,
            headers={"Cookie": f"substack.sid={cookie}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            name = data.get("name", data.get("email", "unknown"))
            user_id = data.get("id", "?")
            return True, f"Authenticated as {name} (id: {user_id})"
        elif resp.status_code in (401, 403):
            return False, f"HTTP {resp.status_code}: Cookie expired or invalid"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Connection error: {e}"


def send_cookie_expiry_alert(error_detail: str):
    """Send email alert when session cookie expires.

    Uses SendGrid pattern from scripts/build_daily_email.py.
    Fails silently if SendGrid not configured.
    """
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("STERLING_EMAIL_TO")
    if not api_key or not to_email:
        logger.warning("SendGrid not configured — cannot send cookie alert")
        return

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email="noreply@sterlingsignals.com",
            to_emails=to_email,
            subject="⚠️ Sterling Signals — Substack session cookie expired",
            html_content=(
                "<h3>Substack Notes Publishing Paused</h3>"
                f"<p><strong>Error:</strong> {error_detail}</p>"
                "<p>Notes are still being generated and saved locally, "
                "but cannot be posted until the cookie is refreshed.</p>"
                "<h4>How to fix:</h4>"
                "<ol>"
                "<li>Log into <a href='https://substack.com'>Substack</a> in your browser</li>"
                "<li>Open DevTools (F12) → Application → Cookies → substack.com</li>"
                "<li>Copy the value of <code>substack.sid</code></li>"
                "<li>Update <code>SUBSTACK_SESSION_COOKIE</code> in GitHub Secrets</li>"
                "</ol>"
                "<p>Cookie typically lasts months — don't sign out of Substack.</p>"
            ),
        )

        sg = SendGridAPIClient(api_key)
        sg.send(message)
        logger.info("Cookie expiry alert sent to %s", to_email)
    except Exception as e:
        logger.warning("Failed to send cookie alert: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# CORE POSTING
# ═══════════════════════════════════════════════════════════════════════════════

def post_note(html_content: str, cookie: str, dry_run: bool = False) -> Dict:
    """Post a single note to Substack via session cookie API.

    Converts HTML to ProseMirror JSON and posts to the Notes API endpoint.

    Returns:
        {"success": bool, "note_id": str|None, "error": str|None}
    """
    # Convert HTML to ProseMirror
    body_json = html_to_prosemirror(html_content)
    paragraph_count = len(body_json.get("content", []))

    if paragraph_count == 0:
        return {"success": False, "note_id": None, "error": "Empty note — no paragraphs"}

    # Build payload — bodyJson is a JSON string within the outer JSON
    payload = {
        "bodyJson": json.dumps(body_json),
        "tabId": "for-you",
        "replyMinimumRole": "everyone",
    }

    if dry_run:
        logger.info("DRY RUN — would post note (%d paragraphs)", paragraph_count)
        # Show first paragraph preview
        first_p = body_json["content"][0] if body_json["content"] else {}
        first_text = ""
        for node in first_p.get("content", []):
            first_text += node.get("text", "")
        if first_text:
            logger.info("  Preview: %s...", first_text[:80])
        return {"success": True, "note_id": "dry-run", "error": None}

    try:
        import requests
    except ImportError:
        return {"success": False, "note_id": None, "error": "requests package not installed"}

    headers = {
        "Cookie": f"substack.sid={cookie}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        resp = requests.post(
            NOTES_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            note_id = str(data.get("id", data.get("comment_id", "")))
            logger.info("Note posted successfully (id: %s, %d paragraphs)", note_id, paragraph_count)
            return {"success": True, "note_id": note_id, "error": None}

        elif resp.status_code in (401, 403):
            error = f"Auth failed (HTTP {resp.status_code}) — cookie likely expired"
            logger.error(error)
            send_cookie_expiry_alert(error)
            return {"success": False, "note_id": None, "error": error}

        elif resp.status_code == 422:
            # Substack returns 422 for malformed payload
            error = f"HTTP 422 (Unprocessable Entity): {resp.text[:300]}"
            logger.error("Payload rejected: %s", error)
            # Try alternative: bodyJson as nested dict instead of string
            logger.info("Retrying with bodyJson as nested dict...")
            payload["bodyJson"] = body_json  # dict, not string
            resp2 = requests.post(NOTES_API_URL, headers=headers, json=payload, timeout=30)
            if resp2.status_code in (200, 201):
                data = resp2.json()
                note_id = str(data.get("id", data.get("comment_id", "")))
                logger.info("Retry succeeded (id: %s)", note_id)
                return {"success": True, "note_id": note_id, "error": None}
            error = f"Both payload formats rejected: {resp2.status_code}"
            logger.error(error)
            return {"success": False, "note_id": None, "error": error}

        else:
            error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            logger.error("Post failed: %s", error)
            return {"success": False, "note_id": None, "error": error}

    except Exception as e:
        error = f"Request error: {e}"
        logger.error(error)
        return {"success": False, "note_id": None, "error": error}


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE LOADING & SLOT ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def find_note_file(slot: int, day: str = None) -> Optional[Path]:
    """Find the generated note file for a given slot.

    Looks in substack/output/current/notes/ for files matching:
    note_{slot}_*_{date}.html

    Returns the file path, or None if not found.
    """
    if not NOTES_OUTPUT_DIR.is_dir():
        logger.debug("Notes output dir does not exist: %s", NOTES_OUTPUT_DIR)
        return None

    now = datetime.now(ET)
    date_str = now.strftime("%Y%m%d")

    # Look for today's note with matching slot number
    for f in sorted(NOTES_OUTPUT_DIR.glob(f"note_{slot}_*_{date_str}.html")):
        logger.debug("Found note file: %s", f.name)
        return f

    # Try without date suffix (in case filename format differs)
    for f in sorted(NOTES_OUTPUT_DIR.glob(f"note_{slot}_*.html")):
        logger.debug("Found note file (no date match): %s", f.name)
        return f

    return None


def generate_fallback_note(slot: int, day: str) -> Optional[str]:
    """Generate a note on-demand if pre-generated file is missing.

    Calls the existing daily_notes_generator for just this slot.
    Returns the HTML content, or None on failure.
    """
    logger.info("Attempting fallback note generation for slot %d (%s)...", slot, day)

    try:
        from substack.daily_notes_generator import (
            generate_daily_notes,
            NOTES_SCHEDULE,
        )

        schedule = NOTES_SCHEDULE.get(day.lower(), [])
        if slot > len(schedule):
            logger.error("Slot %d exceeds schedule length (%d) for %s", slot, len(schedule), day)
            return None

        notes = generate_daily_notes(day=day, dry_run=False, html_output=True)

        for note in notes:
            if note.get("slot") == slot:
                filepath = note.get("filepath")
                if filepath and Path(filepath).exists():
                    return Path(filepath).read_text()
                text = note.get("text")
                if text:
                    return text

        logger.error("Fallback generation produced no note for slot %d", slot)
        return None

    except Exception as e:
        logger.error("Fallback generation failed: %s", e)
        return None


def publish_slot(slot: int, day: str = None, dry_run: bool = False) -> Dict:
    """Orchestrate: load note → post to Substack → update state.

    This is the main entry point for publishing a single note slot.

    Returns: {"success": bool, "slot": int, "day": str, ...}
    """
    if day is None:
        day = datetime.now(ET).strftime("%A").lower()

    logger.info("Publishing slot %d for %s (dry_run=%s)", slot, day, dry_run)

    # 1. Get cookie
    cookie = get_cookie()
    if not cookie and not dry_run:
        error = "No SUBSTACK_SESSION_COOKIE configured"
        logger.error(error)
        return {"success": False, "slot": slot, "day": day, "error": error}

    # 2. Find pre-generated note
    note_file = find_note_file(slot, day)
    if note_file:
        html_content = note_file.read_text()
        logger.info("Loaded note from %s (%d chars)", note_file.name, len(html_content))
    else:
        logger.warning("No pre-generated note for slot %d — trying fallback generation...", slot)
        html_content = generate_fallback_note(slot, day)
        if not html_content:
            error = f"No note available for slot {slot} and fallback generation failed"
            logger.error(error)
            return {"success": False, "slot": slot, "day": day, "error": error}
        logger.info("Fallback generated note (%d chars)", len(html_content))

    # 3. Post
    result = post_note(html_content, cookie or "dry-run", dry_run=dry_run)

    # 4. Update state — always (unless dry-run)
    if not dry_run:
        if result["success"]:
            update_notes_state(slot, day, status="published", note_id=result.get("note_id"))
        else:
            # Note was generated but posting failed — keep status="generated"
            update_notes_state(slot, day, status="generated")

    result["slot"] = slot
    result["day"] = day
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

def load_notes_state() -> Dict:
    """Load state/notes.json, returning default scaffold if missing/corrupt."""
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
        if not isinstance(data, dict):
            return default
        return data
    except (json.JSONDecodeError, IOError):
        return default


def update_notes_state(
    slot: int,
    day: str,
    status: str = "published",
    note_id: Optional[str] = None,
):
    """Update state/notes.json after posting (or failed posting).

    Two-phase state tracking:
      1. Generator (notes_generator.py) writes status="generated" + cost
      2. Poster (this module) upgrades to "published" or keeps "generated"

    If a slot entry already exists (from the generator), this merges into it
    — preserving generated_at and cost_usd while adding published_at / note_id.
    If no entry exists (generator wasn't called separately), creates one.
    """
    state = load_notes_state()
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

    # Determine note type from schedule
    note_type = "UNKNOWN"
    try:
        from substack.daily_notes_generator import NOTES_SCHEDULE
        schedule = NOTES_SCHEDULE.get(day.lower(), [])
        if slot <= len(schedule):
            note_type = schedule[slot - 1][0]
    except ImportError:
        pass

    # Find existing slot entry (may have been created by notes_generator)
    existing = next(
        (s for s in state["today"]["slots"] if s.get("slot") == slot), None
    )

    if existing:
        # Merge into existing entry — preserve generated_at and cost_usd
        existing["status"] = status
        existing["note_type"] = note_type
        if status == "published":
            existing["published_at"] = now.isoformat()
            existing["note_id"] = note_id
    else:
        # Create new entry (generator wasn't called separately)
        slot_entry = {
            "slot": slot,
            "note_type": note_type,
            "status": status,
        }
        if status == "published":
            slot_entry["published_at"] = now.isoformat()
            slot_entry["note_id"] = note_id
        state["today"]["slots"].append(slot_entry)
        state["today"]["slots"] = sorted(
            state["today"]["slots"], key=lambda s: s.get("slot", 0)
        )

    state["today"]["notes_published"] = len(
        [s for s in state["today"]["slots"] if s.get("status") == "published"]
    )

    state["last_updated"] = now.isoformat()

    # Maintain recent array — only add for "published" (avoid double-entry
    # since notes_generator already appends a "generated" entry)
    if status == "published":
        recent_entry = {
            "date": today_str,
            "slot": slot,
            "note_type": note_type,
            "note_id": note_id,
        }
        state.setdefault("recent", []).append(recent_entry)
        state["recent"] = state["recent"][-21:]

    # Write
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    logger.info(
        "State updated: slot %d %s (%d/%d today)",
        slot,
        status,
        state["today"]["notes_published"],
        state["today"]["notes_target"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Substack Notes Poster — publish generated notes via session cookie",
    )
    parser.add_argument(
        "--slot", type=int, choices=[1, 2, 3],
        help="Slot number to publish (1, 2, or 3)",
    )
    parser.add_argument(
        "--day", type=str, default=None,
        help="Override day of week (e.g., wednesday)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without posting to Substack",
    )
    parser.add_argument(
        "--check-cookie", action="store_true",
        help="Test if session cookie is valid",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  STERLING SIGNALS — SUBSTACK NOTES POSTER")
    print("=" * 60)

    # Cookie check mode
    if args.check_cookie:
        cookie = get_cookie()
        if not cookie:
            print("\n  SUBSTACK_SESSION_COOKIE not set")
            print("  See docs/SETUP.md section 3 for extraction instructions.")
            return 1

        valid, info = check_cookie_validity(cookie)
        status = "✓ VALID" if valid else "✗ INVALID"
        print(f"\n  Cookie: {status}")
        print(f"  Detail: {info}")
        return 0 if valid else 1

    # Publishing mode — slot required
    if not args.slot:
        print("\n  Error: --slot required (1, 2, or 3)")
        print("  Usage: python -m substack.notes_poster --slot 1")
        return 1

    day = args.day.lower() if args.day else datetime.now(ET).strftime("%A").lower()
    mode = "DRY RUN" if args.dry_run else "LIVE"

    print(f"  Day: {day.capitalize()}")
    print(f"  Slot: {args.slot}")
    print(f"  Mode: {mode}")
    print("=" * 60 + "\n")

    result = publish_slot(args.slot, day, args.dry_run)

    print(f"\n{'=' * 60}")
    if result["success"]:
        print(f"  ✓ SUCCESS — Slot {args.slot} {'would be ' if args.dry_run else ''}published")
        if result.get("note_id") and result["note_id"] != "dry-run":
            print(f"  Note ID: {result['note_id']}")
    else:
        print(f"  ✗ FAILED — Slot {args.slot}")
        print(f"  Error: {result.get('error', 'unknown')}")
    print(f"{'=' * 60}\n")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
