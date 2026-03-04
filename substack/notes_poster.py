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
    python -m substack.notes_poster --email-fallback --slot 1  # Email note (CI fallback)
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
COOKIE_CHECK_URL = "https://substack.com/api/v1/reader/feed"
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

    Makes a lightweight request to /api/v1/reader/feed.
    Returns (is_valid, detail_message).
    """
    try:
        resp = _build_session(cookie).get(COOKIE_CHECK_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            return True, f"Authenticated (feed returned {len(items)} items)"
        elif resp.status_code in (401, 403):
            return False, f"HTTP {resp.status_code}: Cookie expired or invalid"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, f"Connection error: {e}"


def send_cookie_expiry_alert(error_detail: str):
    """Send email alert when session cookie expires.

    Uses SMTP via utils.email_notifier.load_config() — same infrastructure
    as all other workflow notifications. Fails silently if not configured.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        from utils.email_notifier import load_config
    except ImportError:
        logger.warning("utils.email_notifier not available — cannot send cookie alert")
        return

    config = load_config()
    if not config:
        logger.warning("Email not configured — cannot send cookie alert")
        return

    subject = "\u26a0\ufe0f Sterling Signals \u2014 Substack session cookie expired"
    html_content = (
        "<h3>Substack Notes Publishing Paused</h3>"
        f"<p><strong>Error:</strong> {error_detail}</p>"
        "<p>Notes are still being generated and saved locally, "
        "but cannot be posted until the cookie is refreshed.</p>"
        "<h4>How to fix:</h4>"
        "<ol>"
        "<li>Log into <a href='https://substack.com'>Substack</a> in your browser</li>"
        "<li>Open DevTools (F12) &rarr; Application &rarr; Cookies &rarr; substack.com</li>"
        "<li>Copy the value of <code>substack.sid</code></li>"
        "<li>Update <code>SUBSTACK_SESSION_COOKIE</code> in GitHub Secrets</li>"
        "</ol>"
        "<p>Cookie typically lasts months &mdash; don't sign out of Substack.</p>"
    )

    try:
        recipients = config.get("recipients", [config.get("from_email")])
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from_email"]
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(config["from_email"], recipients, msg.as_string())

        logger.info("Cookie expiry alert sent to %s via SMTP", ", ".join(recipients))
    except Exception as e:
        logger.warning("Failed to send cookie alert: %s", e)


def send_note_email(slot: int, day: str) -> bool:
    """Email the generated note when CI posting fails.

    Sends the note as plain text (for easy copy-paste into Substack Notes)
    with an HTML preview section. Uses SMTP via utils.email_notifier.load_config()
    — same infrastructure as all other workflow notifications.

    Returns True if email sent successfully, False otherwise.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        from utils.email_notifier import load_config
    except ImportError:
        logger.warning("utils.email_notifier not available — cannot email note")
        return False

    config = load_config()
    if not config:
        logger.warning("Email not configured (no SMTP env vars or email_config.json)")
        return False

    # Load note content from manifest (has plain text)
    manifest_path = NOTES_OUTPUT_DIR / "notes_manifest.json"
    if not manifest_path.exists():
        logger.error("No notes_manifest.json found")
        return False

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to read manifest: %s", e)
        return False

    note_data = next(
        (n for n in manifest.get("notes", []) if n.get("slot") == slot), None
    )
    if not note_data:
        logger.error("Slot %d not found in manifest", slot)
        return False

    note_text = note_data.get("text", "")
    note_type = note_data.get("type", "UNKNOWN")
    time_et = note_data.get("time_et", "")

    if not note_text:
        logger.error("Note text is empty for slot %d", slot)
        return False

    # Also load the HTML file for a styled preview section
    note_file = find_note_file(slot, day)
    html_preview = note_file.read_text() if note_file else ""

    subject = (
        f"\U0001f4dd Substack Note Ready \u2014 Slot {slot} "
        f"({note_type.replace('_', ' ').title()})"
    )

    # Build email: plain text at top for copy-paste, HTML preview below
    email_html = (
        '<div style="font-family: -apple-system, BlinkMacSystemFont, '
        "'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; "
        'margin: 0 auto; padding: 20px;">'
        f'<h2 style="color: #1a1a1a; margin-bottom: 4px;">'
        f"Substack Note \u2014 Slot {slot}</h2>"
        f'<p style="color: #666; margin-top: 0;">'
        f"{day.title()} &middot; {note_type.replace('_', ' ').title()} "
        f"&middot; Scheduled {time_et} ET</p>"
        # Copy-paste section
        '<div style="background: #f5f5f0; border: 1px solid #e0ddd8; '
        'border-radius: 8px; padding: 20px; margin: 16px 0;">'
        '<p style="color: #666; font-size: 13px; margin: 0 0 8px 0; '
        'text-transform: uppercase; letter-spacing: 0.5px;">'
        "Copy this text into Substack Notes &darr;</p>"
        '<div style="white-space: pre-wrap; font-size: 15px; '
        f'line-height: 1.6; color: #1a1a1a;">{note_text}</div>'
        "</div>"
    )

    # Add HTML preview if available
    if html_preview:
        email_html += (
            '<div style="margin-top: 24px;">'
            '<p style="color: #666; font-size: 14px; '
            'margin-bottom: 8px;">HTML Preview:</p>'
            '<div style="border: 1px solid #e0ddd8; '
            f'border-radius: 8px; padding: 16px;">{html_preview}</div>'
            "</div>"
        )

    # Footer
    email_html += (
        '<p style="color: #999; font-size: 12px; margin-top: 24px; '
        'border-top: 1px solid #eee; padding-top: 12px;">'
        "CI posting blocked by Cloudflare. "
        "To post from terminal: <code>python3 -m substack.notes_poster "
        f"--slot {slot}</code></p>"
        "</div>"
    )

    try:
        recipients = config.get("recipients", [config.get("from_email")])
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from_email"]
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        # Plain text first (for copy-paste), HTML second (email clients prefer last)
        msg.attach(MIMEText(note_text, "plain", "utf-8"))
        msg.attach(MIMEText(email_html, "html", "utf-8"))

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(config["from_email"], recipients, msg.as_string())

        logger.info("Note emailed to %s via SMTP", ", ".join(recipients))
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.warning("SMTP auth failed: %s", e)
        return False
    except smtplib.SMTPException as e:
        logger.warning("SMTP error: %s", e)
        return False
    except Exception as e:
        logger.warning("Failed to email note: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CORE POSTING
# ═══════════════════════════════════════════════════════════════════════════════

def _build_session(cookie: str):
    """Build an authenticated session with browser-like TLS fingerprint.

    Uses curl_cffi to impersonate Chrome's TLS handshake, which is required
    to bypass Cloudflare Bot Management on Substack's POST endpoints.
    Falls back to standard requests if curl_cffi is unavailable.

    Sets the substack.sid cookie, then warms up the session by hitting
    /notes to collect Cloudflare cookies (__cf_bm, etc.).
    """
    try:
        from curl_cffi import requests as cffi_requests
        session = cffi_requests.Session(impersonate="chrome")
        logger.info("Using curl_cffi (browser TLS fingerprint)")
    except ImportError:
        import requests
        session = requests.Session()
        logger.warning("curl_cffi not available — falling back to requests (may hit Cloudflare 403)")

    session.cookies.set("substack.sid", cookie, domain=".substack.com")

    # Warm up session — picks up Cloudflare cookies
    try:
        warm_resp = session.get("https://substack.com/notes", timeout=15)
        logger.info("Session warm-up: HTTP %d (%d cookies collected)",
                     warm_resp.status_code, len(session.cookies))
        if warm_resp.status_code == 403:
            logger.warning("Warm-up 403 — Cloudflare may be blocking this IP or cookie is expired")
    except Exception as e:
        logger.warning("Session warm-up failed: %s — continuing anyway", e)

    return session


def post_note(html_content: str, cookie: str, dry_run: bool = False) -> Dict:
    """Post a single note to Substack via session cookie API.

    Converts HTML to ProseMirror JSON and posts to the Notes API endpoint.
    Uses a full requests.Session to collect all required cookies before POST.

    Returns:
        {"success": bool, "note_id": str|None, "error": str|None}
    """
    # Convert HTML to ProseMirror
    body_json = html_to_prosemirror(html_content)
    paragraph_count = len(body_json.get("content", []))

    if paragraph_count == 0:
        return {"success": False, "note_id": None, "error": "Empty note — no paragraphs"}

    # Build payload — bodyJson as dict (Substack expects nested object)
    payload = {
        "bodyJson": body_json,
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
        session = _build_session(cookie)

        resp = session.post(
            NOTES_API_URL,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://substack.com",
                "Referer": "https://substack.com/notes",
            },
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
            # Substack returns 422 for malformed payload — try bodyJson as string
            error = f"HTTP 422 (Unprocessable Entity): {resp.text[:300]}"
            logger.error("Payload rejected: %s", error)
            logger.info("Retrying with bodyJson as JSON string...")
            payload["bodyJson"] = json.dumps(body_json)
            resp2 = session.post(
                NOTES_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://substack.com",
                    "Referer": "https://substack.com/notes",
                },
                json=payload,
                timeout=30,
            )
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
    parser.add_argument(
        "--email-fallback", action="store_true",
        help="Email the note instead of posting (CI fallback when Cloudflare blocks)",
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

    # Email fallback mode — email the note content instead of posting
    if args.email_fallback:
        if not args.slot:
            print("\n  Error: --slot required with --email-fallback")
            print("  Usage: python -m substack.notes_poster --email-fallback --slot 1")
            return 1

        day = args.day.lower() if args.day else datetime.now(ET).strftime("%A").lower()
        print(f"  Day: {day.capitalize()}")
        print(f"  Slot: {args.slot}")
        print(f"  Mode: EMAIL FALLBACK")
        print("=" * 60 + "\n")

        success = send_note_email(args.slot, day)
        print(f"\n{'=' * 60}")
        if success:
            print(f"  ✓ Note emailed — Slot {args.slot}")
        else:
            print(f"  ✗ Email failed — Slot {args.slot}")
        print(f"{'=' * 60}\n")
        return 0 if success else 1

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
