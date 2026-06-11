#!/usr/bin/env python3
"""
Shared email utilities for Sterling Signals.

Uses Gmail SMTP with app password authentication.

Environment variables (same as utils/email_notifier.py):
    SMTP_SERVER      — SMTP hostname (e.g. smtp.gmail.com)
    SMTP_PORT        — Port number (default: 587)
    EMAIL_SENDER     — From address
    EMAIL_PASSWORD   — Gmail App Password
    SMTP_USERNAME    — Login username (defaults to EMAIL_SENDER)
    NOTIFICATION_EMAIL — Override recipient (takes precedence)
    EMAIL_RECIPIENTS   — Comma-separated fallback recipients

Usage:
    # As a module
    from scripts.email_utils import send_email, get_recipient_email

    # CLI test
    python3 -m scripts.email_utils --test
"""

import argparse
import mimetypes
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Union


# Max attachment size (2MB) — matches build_daily_email.py
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024

# MIME type overrides for common extensions
_MIME_OVERRIDES = {
    ".html": ("text", "html"),
    ".htm": ("text", "html"),
    ".png": ("image", "png"),
    ".jpg": ("image", "jpeg"),
    ".jpeg": ("image", "jpeg"),
    ".gif": ("image", "gif"),
    ".json": ("application", "json"),
    ".md": ("text", "plain"),
    ".txt": ("text", "plain"),
    ".csv": ("text", "csv"),
    ".pdf": ("application", "pdf"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════


def _load_config() -> Optional[Dict]:
    """Load SMTP config via utils.email_notifier.load_config().

    Reuses the existing config loading chain:
        env vars → .env → email_config.json → defaults
    """
    try:
        from utils.email_notifier import load_config
        return load_config()
    except ImportError:
        # Fallback: try to load config ourselves if email_notifier unavailable
        import os
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).resolve().parent.parent / ".env"
            load_dotenv(env_path, override=False)
        except ImportError:
            pass

        smtp_server = os.environ.get("SMTP_SERVER")
        email_sender = os.environ.get("EMAIL_SENDER")
        email_password = os.environ.get("EMAIL_PASSWORD")

        if not (smtp_server and email_sender and email_password):
            return None

        notification_email = os.environ.get("NOTIFICATION_EMAIL")
        if notification_email:
            recipients = [e.strip() for e in notification_email.split(",")]
        else:
            recipients_str = os.environ.get("EMAIL_RECIPIENTS", email_sender)
            recipients = [e.strip() for e in recipients_str.split(",")]

        return {
            "smtp_server": smtp_server,
            "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
            "from_email": email_sender,
            "username": os.environ.get("SMTP_USERNAME", email_sender),
            "password": email_password,
            "recipients": recipients,
        }


def get_recipient_email() -> str:
    """Return the primary recipient email address from config.

    Resolution order: NOTIFICATION_EMAIL → EMAIL_RECIPIENTS → EMAIL_SENDER.

    Returns:
        Recipient email address string.

    Raises:
        RuntimeError: If email is not configured.
    """
    config = _load_config()
    if not config:
        raise RuntimeError(
            "Email not configured. Required env vars: "
            "SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD"
        )
    recipients = config.get("recipients", [config.get("from_email", "")])
    if not recipients or not recipients[0]:
        raise RuntimeError("No recipient configured")
    return recipients[0]


# ═══════════════════════════════════════════════════════════════════════════════
# MIME HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _detect_mime_type(filepath: Path) -> tuple:
    """Detect MIME type from file extension.

    Returns:
        Tuple of (maintype, subtype) e.g. ("text", "html").
    """
    ext = filepath.suffix.lower()
    if ext in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[ext]

    mime_type, _ = mimetypes.guess_type(str(filepath))
    if mime_type:
        main, sub = mime_type.split("/", 1)
        return (main, sub)

    return ("application", "octet-stream")


def _resolve_attachment(item: Union[Path, Dict, str]) -> Optional[tuple]:
    """Resolve an attachment item to (filepath, display_name).

    Accepts:
        - Path object
        - str (treated as file path)
        - dict with "filepath" key and optional "filename" key

    Returns:
        (Path, str) tuple or None if invalid.
    """
    if isinstance(item, dict):
        fp = item.get("filepath")
        if not fp:
            return None
        fp = Path(fp)
        display = item.get("filename", fp.name)
        return (fp, display)
    else:
        fp = Path(item)
        return (fp, fp.name)


# ═══════════════════════════════════════════════════════════════════════════════
# SEND EMAIL
# ═══════════════════════════════════════════════════════════════════════════════


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    attachments: Optional[List[Union[Path, Dict, str]]] = None,
    body_text: Optional[str] = None,
) -> bool:
    """Send an email via Gmail SMTP with optional attachments.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body_html: Email body as HTML string.
        attachments: Optional list of file attachments. Each item can be:
            - A Path object (filename derived from path)
            - A str file path (converted to Path)
            - A dict with "filepath" (Path) and optional "filename" (str)
            Files > 2MB are skipped with a warning.
        body_text: Optional plain text alternative body. If provided,
            the email includes both text and HTML parts.

    Returns:
        True if sent successfully, False if failed.
        Never raises — errors are printed to stderr.
    """
    config = _load_config()
    if not config:
        print(
            "  ✗ Email not configured. Required env vars: "
            "SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD",
            file=sys.stderr,
        )
        return False

    try:
        # Build message
        if attachments:
            msg = MIMEMultipart("mixed")
            if body_text:
                alt = MIMEMultipart("alternative")
                alt.attach(MIMEText(body_text, "plain", "utf-8"))
                alt.attach(MIMEText(body_html, "html", "utf-8"))
                msg.attach(alt)
            else:
                msg.attach(MIMEText(body_html, "html", "utf-8"))
        elif body_text:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            msg = MIMEMultipart("mixed")
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        msg["From"] = config["from_email"]
        msg["To"] = to_email
        msg["Subject"] = subject

        # Attach files
        for item in (attachments or []):
            resolved = _resolve_attachment(item)
            if not resolved:
                print(f"  ⚠ Skipping invalid attachment: {item}", file=sys.stderr)
                continue

            filepath, display_name = resolved

            if not filepath.exists():
                print(f"  ⚠ Attachment not found: {filepath}", file=sys.stderr)
                continue

            file_size = filepath.stat().st_size
            if file_size > MAX_ATTACHMENT_BYTES:
                print(
                    f"  ⚠ Skipping {display_name} ({file_size // 1024}KB > "
                    f"{MAX_ATTACHMENT_BYTES // 1024}KB limit)",
                    file=sys.stderr,
                )
                continue

            maintype, subtype = _detect_mime_type(filepath)
            content = filepath.read_bytes()

            part = MIMEBase(maintype, subtype)
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{display_name}"',
            )
            msg.attach(part)

        # Send
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(config["from_email"], [to_email], msg.as_string())

        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"  ✗ Email authentication failed: {e}", file=sys.stderr)
        return False
    except smtplib.SMTPException as e:
        print(f"  ✗ SMTP error: {e}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"  ✗ Network error: {e}", file=sys.stderr)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def _test_email() -> bool:
    """Send a test email to verify SMTP configuration."""
    try:
        recipient = get_recipient_email()
    except RuntimeError as e:
        print(f"\n  ✗ {e}")
        print("\n  Required environment variables:")
        print("    SMTP_SERVER      — e.g. smtp.gmail.com")
        print("    SMTP_PORT        — e.g. 587 (default)")
        print("    EMAIL_SENDER     — your Gmail address")
        print("    EMAIL_PASSWORD   — Gmail App Password")
        print("    NOTIFICATION_EMAIL or EMAIL_RECIPIENTS — recipient")
        return False

    print(f"\n  Sending test email to: {recipient}")

    body_html = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 20px; background: #111318; font-family: -apple-system, sans-serif;">
<div style="max-width: 500px; margin: 0 auto;">
    <div style="background: #0F1B2D; padding: 24px; border-radius: 12px;">
        <h2 style="color: #C9A84C; margin: 0 0 12px 0;">Email Test Passed</h2>
        <p style="color: #CBD5E1; margin: 0;">
            Gmail SMTP is configured correctly. Sterling Signals email
            pipeline is ready.
        </p>
    </div>
    <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 16px;">
        scripts.email_utils — Sterling Signals
    </p>
</div>
</body>
</html>"""

    ok = send_email(
        to_email=recipient,
        subject="Sterling Signals — Email Test",
        body_html=body_html,
    )

    if ok:
        print("  ✓ Test email sent successfully!")
    else:
        print("  ✗ Test email failed — check errors above")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Sterling Signals email utilities")
    parser.add_argument("--test", action="store_true", help="Send a test email")
    args = parser.parse_args()

    if args.test:
        ok = _test_email()
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
