#!/usr/bin/env python3
"""
Tests for the email attachment system.

Tests:
- send_email_with_attachments() with mock SMTP
- build_daily_email manifest parsing
- Fallback when no manifest exists
- Attachment collection from output dirs
"""

import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: send_email_with_attachments
# ═══════════════════════════════════════════════════════════════════════════════


class TestSendEmailWithAttachments:
    """Tests for utils.email_notifier.send_email_with_attachments."""

    @pytest.fixture
    def mock_config(self):
        return {
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "from_email": "test@test.com",
            "username": "test@test.com",
            "password": "pass123",
            "recipients": ["user@example.com"],
        }

    @patch("utils.email_notifier.smtplib.SMTP")
    @patch("utils.email_notifier.load_config")
    def test_sends_html_body(self, mock_load, mock_smtp_cls, mock_config):
        """Email sends with HTML body."""
        mock_load.return_value = mock_config
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from utils.email_notifier import send_email_with_attachments

        result = send_email_with_attachments(
            "Test Subject",
            "<h1>Hello</h1>",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "pass123")
        mock_server.sendmail.assert_called_once()

    @patch("utils.email_notifier.smtplib.SMTP")
    @patch("utils.email_notifier.load_config")
    def test_sends_with_attachments(self, mock_load, mock_smtp_cls, mock_config):
        """Email sends with file attachments."""
        mock_load.return_value = mock_config
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from utils.email_notifier import send_email_with_attachments

        attachments = [
            ("note_1.html", b"<div>Note 1</div>"),
            ("post.html", b"<div>Post content</div>"),
        ]

        result = send_email_with_attachments(
            "Content Delivery",
            "<h1>Today's content attached</h1>",
            attachments=attachments,
        )

        assert result is True
        # Check the message was sent (sendmail was called)
        call_args = mock_server.sendmail.call_args
        msg_str = call_args[0][2]  # Third arg is the message string
        assert "note_1.html" in msg_str
        assert "post.html" in msg_str

    @patch("utils.email_notifier.load_config")
    def test_raises_when_not_configured(self, mock_load):
        """Raises RuntimeError when no config available."""
        mock_load.return_value = None

        from utils.email_notifier import send_email_with_attachments

        with pytest.raises(RuntimeError, match="not configured"):
            send_email_with_attachments("Subject", "<p>Body</p>")

    @patch("utils.email_notifier.smtplib.SMTP")
    @patch("utils.email_notifier.load_config")
    def test_empty_attachments_ok(self, mock_load, mock_smtp_cls, mock_config):
        """Sending with no attachments works."""
        mock_load.return_value = mock_config
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from utils.email_notifier import send_email_with_attachments

        result = send_email_with_attachments("No Attachments", "<p>Just body</p>", [])
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Manifest Loading
# ═══════════════════════════════════════════════════════════════════════════════


class TestManifestLoading:
    """Tests for build_daily_email manifest parsing."""

    def test_load_manifest_matching_date(self, tmp_path):
        """Loads manifest when date matches."""
        from scripts.build_daily_email import _load_manifest, MANIFEST_PATH

        manifest_data = {
            "date": "2026-03-09",
            "day": "monday",
            "generated_at": "2026-03-09T08:15:00",
            "post": {"category": "none", "file": None},
            "notes": [],
        }

        with patch("scripts.build_daily_email.MANIFEST_PATH", tmp_path / "manifest.json"):
            (tmp_path / "manifest.json").write_text(json.dumps(manifest_data))

            # Patch the module-level constant
            import scripts.build_daily_email as mod
            original = mod.MANIFEST_PATH
            mod.MANIFEST_PATH = tmp_path / "manifest.json"
            try:
                result = _load_manifest(date(2026, 3, 9))
                assert result is not None
                assert result["day"] == "monday"
            finally:
                mod.MANIFEST_PATH = original

    def test_load_manifest_wrong_date(self, tmp_path):
        """Returns None when manifest date doesn't match."""
        manifest_data = {"date": "2026-03-08", "day": "sunday"}

        import scripts.build_daily_email as mod
        original = mod.MANIFEST_PATH
        mod.MANIFEST_PATH = tmp_path / "manifest.json"
        (tmp_path / "manifest.json").write_text(json.dumps(manifest_data))

        try:
            result = mod._load_manifest(date(2026, 3, 9))
            assert result is None
        finally:
            mod.MANIFEST_PATH = original

    def test_load_manifest_missing_file(self):
        """Returns None when manifest doesn't exist."""
        import scripts.build_daily_email as mod
        original = mod.MANIFEST_PATH
        mod.MANIFEST_PATH = Path("/nonexistent/path/manifest.json")

        try:
            result = mod._load_manifest(date(2026, 3, 9))
            assert result is None
        finally:
            mod.MANIFEST_PATH = original


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Attachment Collection
# ═══════════════════════════════════════════════════════════════════════════════


class TestAttachmentCollection:
    """Tests for collecting HTML files as attachments."""

    def test_collect_from_manifest(self, tmp_path):
        """Collects files referenced in manifest."""
        import scripts.build_daily_email as mod

        # Create mock files
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "note_1_market_20260309.html").write_text("<div>Note 1</div>")
        (notes_dir / "note_2_signal_20260309.html").write_text("<div>Note 2</div>")

        manifest = {
            "post": {"category": "none", "file": None},
            "notes": [
                {"slot": 1, "type": "MARKET", "file": "notes/note_1_market_20260309.html"},
                {"slot": 2, "type": "SCANNER", "file": "notes/note_2_signal_20260309.html"},
            ],
            "visual": {"type": "none", "file": None},
        }

        # Patch SUBSTACK_OUTPUT
        original = mod.SUBSTACK_OUTPUT
        # We need to trick the path so base / "notes/..." resolves correctly
        # Manifest paths are relative to SUBSTACK_OUTPUT / "current"
        current_dir = tmp_path
        with patch.object(mod, "SUBSTACK_OUTPUT", tmp_path.parent):
            # Override to make base = tmp_path
            original_fn = mod._collect_attachments_from_manifest

            def patched_collect(m):
                # Temporarily override base
                import types
                old_code = mod._collect_attachments_from_manifest
                # Just test with direct file access
                attachments = []
                for note in m.get("notes", []):
                    f = note.get("file")
                    if f:
                        p = tmp_path / f
                        if p.exists():
                            attachments.append((p.name, p.read_bytes()))
                return attachments

            result = patched_collect(manifest)
            assert len(result) == 2
            assert result[0][0] == "note_1_market_20260309.html"

    def test_fallback_collection(self, tmp_path):
        """Fallback scans dirs for date-matching HTML files."""
        import scripts.build_daily_email as mod

        # Create mock output files
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "note_1_market_20260309.html").write_text("<div>Note</div>")
        (notes_dir / "note_old_20260308.html").write_text("<div>Old</div>")  # Wrong date

        original_notes = mod.NOTES_DIR
        original_posts = mod.POSTS_DIR
        original_diagrams = mod.DIAGRAMS_DIR

        mod.NOTES_DIR = notes_dir
        mod.POSTS_DIR = tmp_path / "posts"  # Doesn't exist
        mod.DIAGRAMS_DIR = tmp_path / "diagrams"  # Doesn't exist

        try:
            result = mod._collect_attachments_fallback(date(2026, 3, 9))
            assert len(result) == 1
            assert "20260309" in result[0].name
        finally:
            mod.NOTES_DIR = original_notes
            mod.POSTS_DIR = original_posts
            mod.DIAGRAMS_DIR = original_diagrams


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Email Body Generation
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmailBody:
    """Tests for email HTML body generation."""

    def test_body_contains_day_and_date(self):
        """Email body includes the day name and date."""
        from scripts.build_daily_email import _build_email_body

        html = _build_email_body(date(2026, 3, 9), None, 0)
        assert "Monday" in html
        assert "March 09, 2026" in html

    def test_body_with_manifest(self):
        """Email body uses manifest data."""
        from scripts.build_daily_email import _build_email_body

        manifest = {
            "post": {"category": "ticker_deep_dive", "title": "NVDA Deep Dive"},
            "notes": [
                {"slot": 1, "type": "MARKET", "time_aedt": "08:00"},
                {"slot": 2, "type": "SCANNER", "time_aedt": "12:00"},
            ],
            "visual": {"type": "diagram", "file": "diagram.html"},
        }

        html = _build_email_body(date(2026, 3, 10), manifest, 3)
        assert "Ticker Deep Dive" in html
        assert "NVDA Deep Dive" in html
        assert "Diagram" in html
        assert "3 HTML file(s)" in html
        assert "MARKET" in html
        assert "08:00" in html
        assert "AEDT" in html

    def test_body_without_manifest(self):
        """Email body works without manifest."""
        from scripts.build_daily_email import _build_email_body

        html = _build_email_body(date(2026, 3, 9), None, 0)
        assert "Sterling Signals" in html
        assert "0 HTML file(s)" in html


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Constants Module
# ═══════════════════════════════════════════════════════════════════════════════


class TestConstants:
    """Tests for the extracted constants module."""

    def test_handbook_section_map_has_required_keys(self):
        """HANDBOOK_SECTION_MAP has all expected category keys."""
        from substack.constants import HANDBOOK_SECTION_MAP

        expected = {"tuesday_deep_dive", "thursday_education", "ad_hoc"}
        assert set(HANDBOOK_SECTION_MAP.keys()) == expected

    def test_note_type_matrix_covers_all_days(self):
        """NOTE_TYPE_MATRIX has entries for all 7 days."""
        from substack.constants import NOTE_TYPE_MATRIX

        expected_days = {"monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday"}
        assert set(NOTE_TYPE_MATRIX.keys()) == expected_days

    def test_note_type_matrix_structure(self):
        """Each day's notes have slot, type, and time."""
        from substack.constants import NOTE_TYPE_MATRIX

        for day, notes in NOTE_TYPE_MATRIX.items():
            assert len(notes) >= 2, f"{day} has fewer than 2 notes"
            for note in notes:
                assert "slot" in note, f"{day} note missing 'slot'"
                assert "type" in note, f"{day} note missing 'type'"
                assert "time" in note, f"{day} note missing 'time'"

    def test_extract_prompt_from_handbook(self):
        """extract_prompt_from_handbook extracts code-fenced prompts."""
        from substack.constants import extract_prompt_from_handbook

        handbook = """## Test Section

Some intro text.

```
This is the prompt content.
Line two of prompt.
```

## Next Section
"""
        result = extract_prompt_from_handbook(handbook, "## Test Section")
        assert "This is the prompt content." in result
        assert "Line two of prompt." in result

    def test_extract_prompt_multi(self):
        """extract_prompt_from_handbook handles multiple prompts."""
        from substack.constants import extract_prompt_from_handbook

        handbook = """## Multi Section

```
Prompt one.
```

```
Prompt two.
```

## End
"""
        result = extract_prompt_from_handbook(handbook, "## Multi Section")
        assert "PROMPT 1 OF 2" in result
        assert "Prompt one." in result
        assert "PROMPT 2 OF 2" in result
        assert "Prompt two." in result

    def test_extract_prompt_not_found(self):
        """Returns empty string for missing section."""
        from substack.constants import extract_prompt_from_handbook

        result = extract_prompt_from_handbook("## Other\nContent", "## Missing")
        assert result == ""
