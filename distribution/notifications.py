#!/usr/bin/env python3
"""
SCAN NOTIFICATIONS — Email + WhatsApp
======================================

Sends combined scan summary notifications with all buy and sell signals
in a single message per channel.

Channels:
  - Email (SMTP) — reuses existing email_notifier.py configuration
  - WhatsApp (Twilio) — concise mobile-friendly alert

Both channels fire independently; if WhatsApp fails, email still sends.
Notifications fire immediately upon detection — not queued.

Environment Variables:
    # Email (reuses existing email_config.json OR env vars)
    SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD
    NOTIFICATION_EMAIL          — recipient for scan alerts

    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM        — e.g. "whatsapp:+14155238886"
    WHATSAPP_TO                 — comma-separated, e.g. "whatsapp:+11111,whatsapp:+12222"

Usage:
    from distribution.notifications import send_scan_summary

    result = send_scan_summary(
        buy_signals=[{"symbol": "AAPL", "price": 185.0, "theme": "AI", ...}],
        sell_signals=[{"symbol": "RCAT", "price": 10.2, "entry_price": 8.5, ...}],
        timeframe="weekly",
    )
    # result == {"email": "sent", "whatsapp": "sent"}
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Reuse email_notifier's config file when env vars aren't set
_EMAIL_CONFIG_FILE = Path(__file__).resolve().parent.parent / "email_config.json"


def _load_email_config() -> Optional[Dict]:
    """Load SMTP credentials, preferring env vars over config file.

    Priority:
        1. Environment variables (SMTP_SERVER, EMAIL_SENDER, etc.)
        2. email_config.json (written by email_notifier.py setup wizard)

    Returns:
        Dict with smtp_server, smtp_port, from_email, username, password, recipients
        or None if nothing is configured.
    """
    # ── Try env vars first ────────────────────────────────────────────────────
    smtp_server = os.environ.get("SMTP_SERVER")
    email_sender = os.environ.get("EMAIL_SENDER")
    email_password = os.environ.get("EMAIL_PASSWORD")

    if smtp_server and email_sender and email_password:
        # Recipient: NOTIFICATION_EMAIL → EMAIL_RECIPIENTS → sender
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

    # ── Fallback: email_config.json ───────────────────────────────────────────
    if _EMAIL_CONFIG_FILE.exists():
        import json

        try:
            with open(_EMAIL_CONFIG_FILE, "r") as f:
                config = json.load(f)

            # Overlay NOTIFICATION_EMAIL if set
            notification_email = os.environ.get("NOTIFICATION_EMAIL")
            if notification_email:
                config["recipients"] = [e.strip() for e in notification_email.split(",")]
            elif "recipients" not in config:
                config["recipients"] = [config.get("to_email", config["from_email"])]

            return config
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load %s: %s", _EMAIL_CONFIG_FILE, exc)

    return None


def _load_whatsapp_config() -> Optional[Dict]:
    """Load Twilio WhatsApp credentials from environment variables.

    WHATSAPP_TO supports comma-separated numbers for multiple recipients:
        WHATSAPP_TO=whatsapp:+11111111111,whatsapp:+12222222222,whatsapp:+13333333333

    Returns:
        Dict with account_sid, auth_token, from_number, to_numbers (list)
        or None if not configured.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM")
    whatsapp_to = os.environ.get("WHATSAPP_TO")

    # Diagnostic: show which vars are set/missing (print so it's visible in GH Actions)
    _wa_vars = {
        "TWILIO_ACCOUNT_SID": bool(account_sid),
        "TWILIO_AUTH_TOKEN": bool(auth_token),
        "TWILIO_WHATSAPP_FROM": bool(whatsapp_from),
        "WHATSAPP_TO": bool(whatsapp_to),
    }
    missing = [k for k, v in _wa_vars.items() if not v]
    if missing:
        print(f"  [WhatsApp] Missing env vars: {', '.join(missing)}")
        logger.info("WhatsApp missing env vars: %s", ", ".join(missing))
        return None

    to_numbers = [n.strip() for n in whatsapp_to.split(",") if n.strip()]

    # Validate format: WHATSAPP_TO must use whatsapp: prefix
    invalid_numbers = [n for n in to_numbers if not n.startswith("whatsapp:")]
    if invalid_numbers:
        print(f"  [WhatsApp] WARNING: WHATSAPP_TO numbers missing 'whatsapp:' prefix: {invalid_numbers}")
        print(f"  [WhatsApp] Expected format: whatsapp:+14155238886")
        logger.warning("WHATSAPP_TO numbers missing 'whatsapp:' prefix: %s", invalid_numbers)

    # Validate format: TWILIO_WHATSAPP_FROM must use whatsapp: prefix
    if not whatsapp_from.startswith("whatsapp:"):
        print(f"  [WhatsApp] WARNING: TWILIO_WHATSAPP_FROM missing 'whatsapp:' prefix: {whatsapp_from}")
        print(f"  [WhatsApp] Expected format: whatsapp:+14155238886")
        logger.warning("TWILIO_WHATSAPP_FROM missing 'whatsapp:' prefix: %s", whatsapp_from)

    print(f"  [WhatsApp] Config loaded: from={whatsapp_from}, to={len(to_numbers)} recipient(s)")

    return {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_number": whatsapp_from,
        "to_numbers": to_numbers,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def _format_signal_label(signal_type: str) -> str:
    """Map signal_type to human-readable label per PRD 5.2."""
    labels = {
        "BEARISH PIVOT": "HMA Bearish Pivot",
        "TRAILING STOP": "20% Trailing Stop",
        "EXIT": "First Exit Triggered",
    }
    return labels.get(signal_type.upper(), signal_type)


def _build_plain_text(
    ticker: str,
    signal_type: str,
    entry_price: float,
    current_price: float,
    highest_close: float,
    stop_level: float,
    pnl_pct: float,
    theme: str,
    timeframe: str,
    entry_date: str,
) -> str:
    """Build plain-text email body per PRD section 5.2."""
    pnl_sign = "+" if pnl_pct >= 0 else ""
    stop_pct = (1 - stop_level / highest_close) * 100 if highest_close > 0 else 0
    entry_str = f" (entered {entry_date})" if entry_date else ""

    return f"""\
SELL SIGNAL — ${ticker} [{signal_type.upper()}]
{'=' * 50}

Ticker:         ${ticker}
Signal:         {_format_signal_label(signal_type)}
Entry Price:    ${entry_price:.2f}{entry_str}
Current Price:  ${current_price:.2f}
Highest Close:  ${highest_close:.2f}
Stop Level:     ${stop_level:.2f} ({stop_pct:.0f}% trailing)
P&L:            {pnl_sign}{pnl_pct:.1f}% (private — not published)
Theme:          {theme}
Timeframe:      {timeframe.capitalize()}

ACTION REQUIRED: Review and execute sell if appropriate.

{'—' * 50}
Sterling Signals — Automated Sell Alert
"""


def _build_html(
    ticker: str,
    signal_type: str,
    entry_price: float,
    current_price: float,
    highest_close: float,
    stop_level: float,
    pnl_pct: float,
    theme: str,
    timeframe: str,
    entry_date: str,
) -> str:
    """Build HTML email body with styled table."""
    pnl_sign = "+" if pnl_pct >= 0 else ""
    pnl_color = "#22c55e" if pnl_pct >= 0 else "#ef4444"
    stop_pct = (1 - stop_level / highest_close) * 100 if highest_close > 0 else 0
    entry_str = f" <span style='color:#6b7280;'>(entered {entry_date})</span>" if entry_date else ""

    # Signal badge colour
    if signal_type.upper() == "BEARISH PIVOT":
        badge_bg = "#f59e0b"  # amber
        badge_text = "BEARISH PIVOT"
    else:
        badge_bg = "#ef4444"  # red
        badge_text = signal_type.upper()

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:20px;background:#f9fafb;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;">

    <!-- Header -->
    <div style="background:#1e293b;padding:16px 20px;">
      <h2 style="margin:0;color:#fff;font-size:18px;">
        \U0001F514 SELL SIGNAL — ${ticker}
        <span style="background:{badge_bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;margin-left:8px;">{badge_text}</span>
      </h2>
    </div>

    <!-- Body -->
    <div style="padding:20px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr><td style="padding:6px 0;color:#6b7280;width:140px;">Ticker</td>
            <td style="padding:6px 0;font-weight:600;">${ticker}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Signal</td>
            <td style="padding:6px 0;">{_format_signal_label(signal_type)}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Entry Price</td>
            <td style="padding:6px 0;">${entry_price:.2f}{entry_str}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Current Price</td>
            <td style="padding:6px 0;font-weight:600;">${current_price:.2f}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Highest Close</td>
            <td style="padding:6px 0;">${highest_close:.2f}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Stop Level</td>
            <td style="padding:6px 0;">${stop_level:.2f} ({stop_pct:.0f}% trailing)</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">P&amp;L</td>
            <td style="padding:6px 0;font-weight:600;color:{pnl_color};">{pnl_sign}{pnl_pct:.1f}%
                <span style="color:#9ca3af;font-weight:400;font-size:12px;">(private — not published)</span></td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Theme</td>
            <td style="padding:6px 0;">{theme}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Timeframe</td>
            <td style="padding:6px 0;">{timeframe.capitalize()}</td></tr>
      </table>

      <!-- CTA -->
      <div style="margin-top:16px;padding:12px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:4px;">
        <strong>\u26a0\ufe0f ACTION REQUIRED:</strong> Review and execute sell if appropriate.
      </div>
    </div>

    <!-- Footer -->
    <div style="padding:12px 20px;background:#f1f5f9;font-size:12px;color:#64748b;text-align:center;">
      Sterling Signals — Automated Sell Alert &bull; {datetime.now().strftime("%Y-%m-%d %H:%M ET")}
    </div>
  </div>
</body>
</html>"""


def _build_whatsapp_message(
    ticker: str,
    signal_type: str,
    entry_price: float,
    current_price: float,
    highest_close: float,
    stop_level: float,
    pnl_pct: float,
    theme: str,
    timeframe: str,
    entry_date: str,
) -> str:
    """Build concise WhatsApp message (~500 chars max)."""
    pnl_sign = "+" if pnl_pct >= 0 else ""
    stop_pct = (1 - stop_level / highest_close) * 100 if highest_close > 0 else 0
    entry_str = f" ({entry_date})" if entry_date else ""

    return (
        f"\U0001F514 SELL SIGNAL — ${ticker}\n"
        f"Signal: {_format_signal_label(signal_type)}\n"
        f"Entry: ${entry_price:.2f}{entry_str}\n"
        f"Current: ${current_price:.2f}\n"
        f"High: ${highest_close:.2f}\n"
        f"Stop: ${stop_level:.2f} ({stop_pct:.0f}%)\n"
        f"P&L: {pnl_sign}{pnl_pct:.1f}%\n"
        f"Theme: {theme}\n"
        f"Timeframe: {timeframe.capitalize()}\n"
        f"\n\u26a0\ufe0f Review and execute sell if appropriate."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL SENDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _send_email(subject: str, body_text: str, body_html: str) -> str:
    """Send a sell-signal email via SMTP.

    Reuses the same SMTP pattern as distribution/email_notifier.py.

    Returns:
        "sent", "skipped" (not configured), or "failed"
    """
    config = _load_email_config()
    if not config:
        print("  [Email] Not configured — skipping email notification")
        logger.info("Email not configured — skipping email notification")
        return "skipped"

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from_email"]
        msg["To"] = ", ".join(config["recipients"])
        msg["Subject"] = subject

        # Plain text first, HTML second (email clients prefer the last part)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.sendmail(config["from_email"], config["recipients"], msg.as_string())

        logger.info(
            "Email sent to %d recipient(s): %s",
            len(config["recipients"]),
            ", ".join(config["recipients"]),
        )
        return "sent"

    except smtplib.SMTPAuthenticationError as exc:
        logger.error("Email auth failed: %s", exc)
        return "failed"
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        return "failed"
    except OSError as exc:
        logger.error("Network error sending email: %s", exc)
        return "failed"


def _send_whatsapp(message: str) -> str:
    """Send a sell-signal WhatsApp message via Twilio to all recipients.

    Sends independently to each number in WHATSAPP_TO (comma-separated).
    Returns "sent" if ALL succeeded, "partial" if some failed, "failed" if all failed.

    Returns:
        "sent", "partial", "skipped" (not configured), or "failed"
    """
    config = _load_whatsapp_config()
    if not config:
        print("  [WhatsApp] Not configured — skipping WhatsApp notification")
        logger.info("WhatsApp not configured — skipping WhatsApp notification")
        return "skipped"

    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError:
        print("  [WhatsApp] ERROR: twilio package not installed — run: pip install twilio>=8.0.0")
        logger.warning("twilio package not installed — run: pip install twilio>=8.0.0")
        return "failed"

    print(f"  [WhatsApp] Sending to {len(config['to_numbers'])} recipient(s)...")
    client = Client(config["account_sid"], config["auth_token"])
    sent_count = 0
    fail_count = 0

    for to_number in config["to_numbers"]:
        try:
            sent_message = client.messages.create(
                body=message,
                from_=config["from_number"],
                to=to_number,
            )
            print(f"  [WhatsApp] ✅ Sent to {to_number} — SID: {sent_message.sid}")
            logger.info("WhatsApp sent to %s — SID: %s", to_number, sent_message.sid)
            sent_count += 1
        except Exception as exc:
            print(f"  [WhatsApp] ❌ Failed to send to {to_number}: {exc}")
            logger.error("WhatsApp send to %s failed: %s", to_number, exc)
            fail_count += 1

    if fail_count == 0:
        return "sent"
    elif sent_count == 0:
        return "failed"
    else:
        return "partial"


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def send_sell_notification(
    ticker: str,
    signal_type: str,
    entry_price: float,
    current_price: float,
    highest_close: float,
    stop_level: float,
    pnl_pct: float,
    theme: str,
    timeframe: str,
    entry_date: str = "",
) -> Dict[str, str]:
    """Send sell signal notification via all configured channels.

    Channels fire independently — if WhatsApp fails, email still sends.
    Notifications are sent immediately (not queued).

    Args:
        ticker:        Stock symbol (e.g. "RCAT")
        signal_type:   "BEARISH PIVOT" or "TRAILING STOP" or "TIGHTENED STOP"
        entry_price:   Original entry price
        current_price: Price at time of signal
        highest_close: Highest weekly close since entry
        stop_level:    Calculated stop price
        pnl_pct:       Percentage P&L (private — included here but NOT in tweets)
        theme:         Thematic category (e.g. "Drone Technology")
        timeframe:     "weekly" or "daily"
        entry_date:    Entry date string (YYYY-MM-DD), optional

    Returns:
        Dict with status per channel, e.g.:
            {"email": "sent", "whatsapp": "sent"}
            {"email": "sent", "whatsapp": "failed"}
            {"email": "skipped", "whatsapp": "skipped"}
    """
    print(f"\n  Sell signal notification: ${ticker} [{signal_type}] — P&L: {pnl_pct:+.1f}%")
    logger.info(
        "Sell signal: $%s [%s] — P&L: %+.1f%% — sending notifications",
        ticker, signal_type, pnl_pct,
    )

    # ── Build messages ────────────────────────────────────────────────────────
    kwargs = dict(
        ticker=ticker,
        signal_type=signal_type,
        entry_price=entry_price,
        current_price=current_price,
        highest_close=highest_close,
        stop_level=stop_level,
        pnl_pct=pnl_pct,
        theme=theme,
        timeframe=timeframe,
        entry_date=entry_date,
    )

    subject = f"\U0001F514 SELL SIGNAL — ${ticker} [{signal_type.upper()}]"
    body_text = _build_plain_text(**kwargs)
    body_html = _build_html(**kwargs)
    whatsapp_msg = _build_whatsapp_message(**kwargs)

    # ── Fire channels independently ───────────────────────────────────────────
    result: Dict[str, str] = {}

    result["email"] = _send_email(subject, body_text, body_html)
    result["whatsapp"] = _send_whatsapp(whatsapp_msg)

    # ── Summary log ───────────────────────────────────────────────────────────
    print(f"  Notification result for ${ticker}: email={result['email']}, whatsapp={result['whatsapp']}")
    logger.info(
        "Notification result for $%s: email=%s, whatsapp=%s",
        ticker, result["email"], result["whatsapp"],
    )

    return result


def _build_summary_whatsapp(
    buy_signals: list,
    sell_signals: list,
    timeframe: str,
) -> str:
    """Build a single WhatsApp message summarising all buy + sell signals."""
    lines = []
    date_str = datetime.now().strftime("%Y-%m-%d")
    tf = timeframe.capitalize()

    lines.append(f"📊 STERLING SIGNALS — {tf} Scan")
    lines.append(f"📅 {date_str}")
    lines.append("")

    # ── Buy signals ──────────────────────────────────────────────────────────
    if buy_signals:
        lines.append(f"🟢 BUY SIGNALS ({len(buy_signals)})")
        lines.append("─" * 28)
        for sig in buy_signals:
            symbol = sig.get("symbol", "???")
            price = float(sig.get("price", 0))
            theme = sig.get("theme", "")
            conviction = sig.get("conviction", "")
            decision = sig.get("final_decision", "PASS")
            conv_str = f" ★{conviction}" if conviction else ""
            dec_label = "PASS" if decision in ("PASS", "TRADE") else decision
            lines.append(f"${symbol} — ${price:.2f}")
            lines.append(f"  {theme}{conv_str} [{dec_label}]")
        lines.append("")

    # ── Sell signals ─────────────────────────────────────────────────────────
    if sell_signals:
        lines.append(f"🔴 EXIT SIGNALS ({len(sell_signals)})")
        lines.append("─" * 28)
        for sig in sell_signals:
            symbol = sig.get("symbol", "???")
            price = float(sig.get("price", 0))
            entry_price = float(sig.get("entry_price", 0))
            reason = sig.get("reason", "Exit")
            pnl = ((price / entry_price) - 1) * 100 if entry_price > 0 else 0
            pnl_sign = "+" if pnl >= 0 else ""
            lines.append(f"${symbol} — ${price:.2f} ({pnl_sign}{pnl:.1f}%)")
            lines.append(f"  {reason[:40]}")
        lines.append("")

    if not buy_signals and not sell_signals:
        lines.append("No new signals this scan.")
        lines.append("")

    lines.append("sterlingsignals.substack.com")

    return "\n".join(lines)


def _build_summary_email_text(
    buy_signals: list,
    sell_signals: list,
    timeframe: str,
) -> str:
    """Build plain-text email for combined scan summary."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    tf = timeframe.capitalize()

    text = f"STERLING SIGNALS — {tf} Scan Summary\n"
    text += f"Date: {date_str}\n"
    text += "=" * 50 + "\n\n"

    if buy_signals:
        text += f"BUY SIGNALS ({len(buy_signals)})\n"
        text += "-" * 30 + "\n"
        for sig in buy_signals:
            symbol = sig.get("symbol", "???")
            price = float(sig.get("price", 0))
            theme = sig.get("theme", "")
            conviction = sig.get("conviction", "")
            decision = sig.get("final_decision", "PASS")
            dec_label = "PASS" if decision in ("PASS", "TRADE") else decision
            text += f"  {symbol:8s} ${price:<10.2f} {theme} [{dec_label}]"
            if conviction:
                text += f" ★{conviction}"
            text += "\n"
        text += "\n"

    if sell_signals:
        text += f"EXIT SIGNALS ({len(sell_signals)})\n"
        text += "-" * 30 + "\n"
        for sig in sell_signals:
            symbol = sig.get("symbol", "???")
            price = float(sig.get("price", 0))
            entry_price = float(sig.get("entry_price", 0))
            reason = sig.get("reason", "Exit")
            pnl = ((price / entry_price) - 1) * 100 if entry_price > 0 else 0
            pnl_sign = "+" if pnl >= 0 else ""
            text += f"  {symbol:8s} ${price:<10.2f} {pnl_sign}{pnl:.1f}%  {reason}\n"
        text += "\n"

    if not buy_signals and not sell_signals:
        text += "No new signals this scan.\n\n"

    text += "—" * 50 + "\n"
    text += "Sterling Signals — Automated Scan Alert\n"

    return text


def _build_summary_email_html(
    buy_signals: list,
    sell_signals: list,
    timeframe: str,
) -> str:
    """Build HTML email for combined scan summary."""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    tf = timeframe.capitalize()

    buy_count = len(buy_signals)
    sell_count = len(sell_signals)

    # Buy rows
    buy_rows = ""
    for sig in buy_signals:
        symbol = sig.get("symbol", "???")
        price = float(sig.get("price", 0))
        theme = sig.get("theme", "")
        conviction = int(sig.get("conviction", 0))
        decision = sig.get("final_decision", "PASS")
        dec_label = "PASS" if decision in ("PASS", "TRADE") else decision
        stars = "★" * conviction + "☆" * (5 - conviction) if conviction else ""
        buy_rows += f"""
        <tr>
          <td style="padding:6px 10px;font-weight:600;">${symbol}</td>
          <td style="padding:6px 10px;">${price:.2f}</td>
          <td style="padding:6px 10px;">{theme}</td>
          <td style="padding:6px 10px;">{stars}</td>
          <td style="padding:6px 10px;"><span style="background:#16a34a;color:#fff;padding:1px 6px;border-radius:3px;font-size:12px;">{dec_label}</span></td>
        </tr>"""

    # Sell rows
    sell_rows = ""
    for sig in sell_signals:
        symbol = sig.get("symbol", "???")
        price = float(sig.get("price", 0))
        entry_price = float(sig.get("entry_price", 0))
        reason = sig.get("reason", "Exit")
        pnl = ((price / entry_price) - 1) * 100 if entry_price > 0 else 0
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_color = "#16a34a" if pnl >= 0 else "#ef4444"
        sell_rows += f"""
        <tr>
          <td style="padding:6px 10px;font-weight:600;">${symbol}</td>
          <td style="padding:6px 10px;">${price:.2f}</td>
          <td style="padding:6px 10px;color:{pnl_color};font-weight:600;">{pnl_sign}{pnl:.1f}%</td>
          <td style="padding:6px 10px;">{reason[:50]}</td>
        </tr>"""

    buy_section = ""
    if buy_signals:
        buy_section = f"""
    <div style="padding:15px 20px;">
      <h3 style="margin:0 0 10px 0;color:#16a34a;">🟢 Buy Signals ({buy_count})</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="background:#f0fdf4;">
          <th style="padding:6px 10px;text-align:left;">Ticker</th>
          <th style="padding:6px 10px;text-align:left;">Price</th>
          <th style="padding:6px 10px;text-align:left;">Theme</th>
          <th style="padding:6px 10px;text-align:left;">Conviction</th>
          <th style="padding:6px 10px;text-align:left;">Decision</th>
        </tr>
        {buy_rows}
      </table>
    </div>"""

    sell_section = ""
    if sell_signals:
        sell_section = f"""
    <div style="padding:15px 20px;">
      <h3 style="margin:0 0 10px 0;color:#ef4444;">🔴 Exit Signals ({sell_count})</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="background:#fef2f2;">
          <th style="padding:6px 10px;text-align:left;">Ticker</th>
          <th style="padding:6px 10px;text-align:left;">Price</th>
          <th style="padding:6px 10px;text-align:left;">P&amp;L</th>
          <th style="padding:6px 10px;text-align:left;">Reason</th>
        </tr>
        {sell_rows}
      </table>
    </div>"""

    no_signals = ""
    if not buy_signals and not sell_signals:
        no_signals = """
    <div style="padding:20px;text-align:center;color:#6b7280;">
      <p>No new signals this scan. Patience is edge.</p>
    </div>"""

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:20px;background:#f9fafb;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;">
    <div style="background:#1e293b;padding:16px 20px;">
      <h2 style="margin:0;color:#fff;font-size:18px;">📊 Sterling Signals — {tf} Scan Summary</h2>
    </div>
    {buy_section}
    {sell_section}
    {no_signals}
    <div style="padding:12px 20px;background:#f1f5f9;font-size:12px;color:#64748b;text-align:center;">
      Sterling Signals — Automated Scan Alert &bull; {date_str}
    </div>
  </div>
</body>
</html>"""


def send_scan_summary(
    buy_signals: list,
    sell_signals: list,
    timeframe: str = "weekly",
) -> Dict[str, str]:
    """Send a single combined notification with all buy and sell signals.

    Replaces per-signal send_sell_notification() calls. Both buy and sell
    signals are merged into one email and one WhatsApp message.

    Args:
        buy_signals:  List of dicts with keys: symbol, price, theme, conviction,
                      final_decision (from signals.json buy_signals)
        sell_signals: List of dicts with keys: symbol, price, entry_price, reason,
                      pnl_pct (from signals.json sell_signals)
        timeframe:    "weekly" or "daily"

    Returns:
        Dict with status per channel: {"email": "sent", "whatsapp": "sent"}
    """
    total = len(buy_signals) + len(sell_signals)
    print(f"\n  Scan summary notification: {len(buy_signals)} buys, {len(sell_signals)} sells")
    logger.info(
        "Scan summary: %d buys, %d sells — sending combined notification",
        len(buy_signals), len(sell_signals),
    )

    if total == 0:
        print("  No signals — skipping notification")
        return {"email": "skipped", "whatsapp": "skipped"}

    # ── Build messages ────────────────────────────────────────────────────────
    subject = f"📊 Sterling Signals — {timeframe.capitalize()} Scan: {len(buy_signals)} buys, {len(sell_signals)} exits"
    body_text = _build_summary_email_text(buy_signals, sell_signals, timeframe)
    body_html = _build_summary_email_html(buy_signals, sell_signals, timeframe)
    whatsapp_msg = _build_summary_whatsapp(buy_signals, sell_signals, timeframe)

    # ── Fire channels independently ───────────────────────────────────────────
    result: Dict[str, str] = {}
    result["email"] = _send_email(subject, body_text, body_html)
    result["whatsapp"] = _send_whatsapp(whatsapp_msg)

    print(f"  Notification result: email={result['email']}, whatsapp={result['whatsapp']}")
    logger.info("Scan summary result: email=%s, whatsapp=%s", result["email"], result["whatsapp"])

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Sell Signal Notifications — Test & Debug")
    parser.add_argument("--dry-run", action="store_true", help="Print messages without sending")
    parser.add_argument("--send-test", action="store_true", help="Send a test notification")
    parser.add_argument("--check-config", action="store_true", help="Check channel configuration")
    args = parser.parse_args()

    # Test data
    test_kwargs = dict(
        ticker="TEST",
        signal_type="BEARISH PIVOT",
        entry_price=25.00,
        current_price=22.50,
        highest_close=30.00,
        stop_level=25.50,
        pnl_pct=-10.0,
        theme="Test Theme",
        timeframe="weekly",
        entry_date="2026-01-15",
    )

    if args.check_config:
        print("\n  Channel Configuration")
        print("  " + "─" * 40)
        email_cfg = _load_email_config()
        wa_cfg = _load_whatsapp_config()
        print(f"  Email:    {'✅ Configured' if email_cfg else '❌ Not configured'}")
        if email_cfg:
            print(f"            Server: {email_cfg['smtp_server']}:{email_cfg['smtp_port']}")
            print(f"            From:   {email_cfg['from_email']}")
            print(f"            To:     {', '.join(email_cfg['recipients'])}")
        print(f"  WhatsApp: {'✅ Configured' if wa_cfg else '❌ Not configured'}")
        if wa_cfg:
            print(f"            From: {wa_cfg['from_number']}")
            print(f"            To:   {', '.join(wa_cfg['to_numbers'])} ({len(wa_cfg['to_numbers'])} recipient(s))")
        print()

    elif args.dry_run:
        print("\n  ── Plain Text Email ──")
        print(_build_plain_text(**test_kwargs))
        print("\n  ── WhatsApp Message ──")
        print(_build_whatsapp_message(**test_kwargs))
        print("\n  ── HTML Email ──")
        print("  (Use --send-test to actually send, or pipe HTML to a file)")
        print()

    elif args.send_test:
        print("\n  Sending test combined scan summary...")
        test_buy_signals = [
            {
                "symbol": "TEST1",
                "price": 25.50,
                "theme": "Grid Infrastructure",
                "conviction": 4,
                "final_decision": "PASS",
            },
            {
                "symbol": "TEST2",
                "price": 42.75,
                "theme": "Defense Manufacturing",
                "conviction": 3,
                "final_decision": "PASS",
            },
        ]
        test_sell_signals = [
            {
                "symbol": "TEST3",
                "price": 18.00,
                "entry_price": 20.00,
                "reason": "First Exit — HMA Bearish Pivot",
                "pnl_pct": -10.0,
            },
        ]
        result = send_scan_summary(
            buy_signals=test_buy_signals,
            sell_signals=test_sell_signals,
            timeframe="weekly",
        )
        print(f"\n  Result: {result}")
        print()

    else:
        parser.print_help()
