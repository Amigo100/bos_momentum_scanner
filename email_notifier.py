#!/usr/bin/env python3
"""
EMAIL NOTIFIER - Multiple Recipients Support
=============================================

Send email notifications to multiple recipients for scanner alerts.

Usage:
    python email_notifier.py setup              # Initial configuration
    python email_notifier.py test               # Send test email
    python email_notifier.py list               # List all recipients
    python email_notifier.py add EMAIL          # Add a recipient
    python email_notifier.py remove EMAIL       # Remove a recipient
"""

import getpass
import json
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG_FILE = Path(__file__).parent / "email_config.json"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


def load_config() -> Optional[Dict]:
    """Load email configuration from config file."""
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_config(config: Dict) -> None:
    """Save email configuration to config file (with restricted permissions)."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    CONFIG_FILE.chmod(0o600)


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP & RECIPIENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


def setup() -> None:
    """Interactive email setup wizard."""
    print("\n" + "=" * 50)
    print("EMAIL SETUP")
    print("=" * 50)
    
    print("\nSMTP Providers:")
    print("  1. Gmail (requires App Password)")
    print("  2. Outlook/Hotmail")
    print("  3. Yahoo (requires App Password)")
    print("  4. Custom SMTP")
    
    choice = input("\nSelect provider (1-4): ").strip()
    
    servers = {
        "1": ("smtp.gmail.com", 587),
        "2": ("smtp-mail.outlook.com", 587),
        "3": ("smtp.mail.yahoo.com", 587),
    }
    
    if choice in servers:
        smtp_server, smtp_port = servers[choice]
    else:
        smtp_server = input("SMTP server: ").strip()
        smtp_port = int(input("SMTP port: ").strip())
    
    from_email = input("Your email address: ").strip()
    
    print(f"\nRecipients (who should receive alerts):")
    print(f"  You can add multiple emails, separated by commas")
    print(f"  Press Enter to just use your own email")
    
    recipients_input = input(f"Recipients [{from_email}]: ").strip()
    
    if recipients_input:
        # Parse multiple emails
        recipients = [e.strip() for e in recipients_input.replace(";", ",").split(",")]
        recipients = [e for e in recipients if "@" in e]  # Basic validation
    else:
        recipients = [from_email]
    
    username = input(f"SMTP username [{from_email}]: ").strip() or from_email
    password = getpass.getpass("SMTP password/app password: ")
    
    config = {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "from_email": from_email,
        "recipients": recipients,
        "username": username,
        "password": password
    }
    
    save_config(config)
    
    print(f"\n✓ Configuration saved to {CONFIG_FILE}")
    print(f"✓ Recipients: {', '.join(recipients)}")
    print("\nRun 'python email_notifier.py test' to verify")


def add_recipient(email: str) -> None:
    """Add a new recipient to the notification list."""
    config = load_config()
    if not config:
        print("✗ Email not configured. Run: python email_notifier.py setup")
        return
    
    if "recipients" not in config:
        config["recipients"] = [config.get("to_email", config["from_email"])]
    
    if email in config["recipients"]:
        print(f"✗ {email} is already a recipient")
        return
    
    config["recipients"].append(email)
    save_config(config)
    print(f"✓ Added {email}")
    print(f"  All recipients: {', '.join(config['recipients'])}")


def remove_recipient(email: str) -> None:
    """Remove a recipient from the notification list."""
    config = load_config()
    if not config:
        print("✗ Email not configured. Run: python email_notifier.py setup")
        return
    
    if email not in config.get("recipients", []):
        print(f"✗ {email} is not a recipient")
        return
    
    config["recipients"].remove(email)
    save_config(config)
    print(f"✓ Removed {email}")
    print(f"  Remaining recipients: {', '.join(config['recipients'])}")


def list_recipients() -> None:
    """List all configured recipients."""
    config = load_config()
    if not config:
        print("✗ Email not configured. Run: python email_notifier.py setup")
        return
    
    recipients = config.get("recipients", [config.get("to_email", "")])
    print(f"\nEmail Recipients ({len(recipients)}):")
    for i, r in enumerate(recipients, 1):
        print(f"  {i}. {r}")
    print(f"\nFrom: {config.get('from_email', 'Not set')}")


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL SENDING
# ═══════════════════════════════════════════════════════════════════════════════


def send_email(subject: str, body: str) -> bool:
    """
    Send an email to all configured recipients.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        True if sent successfully, False otherwise

    Raises:
        RuntimeError: If email is not configured
    """
    config = load_config()
    if not config:
        raise RuntimeError("Email not configured. Run: python email_notifier.py setup")

    # Support both old and new config format
    recipients = config.get("recipients", [config.get("to_email", config["from_email"])])

    try:
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['username'], config['password'])
            server.sendmail(config['from_email'], recipients, msg.as_string())

        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"  ✗ Email authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"  ✗ SMTP error: {e}")
        return False
    except OSError as e:
        print(f"  ✗ Network error: {e}")
        return False


def test() -> None:
    """Send a test email to all configured recipients."""
    config = load_config()
    if not config:
        print("✗ Email not configured. Run: python email_notifier.py setup")
        return
    
    recipients = config.get("recipients", [config.get("to_email", config["from_email"])])
    print(f"\nSending test email to {len(recipients)} recipient(s)...")
    print(f"  Recipients: {', '.join(recipients)}")
    
    body = """This is a test email from the BoS Momentum Scanner.

If you received this, email notifications are working correctly.

Recipients configured:
""" + "\n".join(f"  - {r}" for r in recipients)
    
    if send_email("BoS Scanner Test", body):
        print("✓ Test email sent successfully!")
    else:
        print("✗ Test email failed")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def print_usage() -> None:
    """Print usage instructions."""
    print("""
Email Notifier - Usage:

  python email_notifier.py setup              Initial configuration
  python email_notifier.py test               Send test email
  python email_notifier.py list               List all recipients
  python email_notifier.py add EMAIL          Add a recipient
  python email_notifier.py remove EMAIL       Remove a recipient

Examples:
  python email_notifier.py add john@example.com
  python email_notifier.py add jane@example.com
  python email_notifier.py remove old@example.com
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
    elif sys.argv[1] == "setup":
        setup()
    elif sys.argv[1] == "test":
        test()
    elif sys.argv[1] == "list":
        list_recipients()
    elif sys.argv[1] == "add" and len(sys.argv) >= 3:
        add_recipient(sys.argv[2])
    elif sys.argv[1] == "remove" and len(sys.argv) >= 3:
        remove_recipient(sys.argv[2])
    elif sys.argv[1] == "add-recipient" and len(sys.argv) >= 3:
        add_recipient(sys.argv[2])
    else:
        print_usage()
