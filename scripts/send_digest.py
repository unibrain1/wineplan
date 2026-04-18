#!/usr/bin/env python3
"""Send the morning digest via email (Gmail SMTP).

Reads site/digest.json and site/digest.html, sends via SMTP with STARTTLS.
Idempotent: tracks last-sent date to prevent double-sends.

Usage: send_digest.py [--dry-run] [--force]
  --dry-run  Print the email subject and recipient list without sending
  --force    Send even if digest has no content or already sent today
"""

import json
import os
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

STATE_FILE = Path("data/digest_last_sent.txt")
DIGEST_JSON = Path("site/digest.json")
DIGEST_HTML = Path("site/digest.html")


def already_sent_today() -> bool:
    """Check if digest was already sent today."""
    if not STATE_FILE.exists():
        return False
    last_sent = STATE_FILE.read_text().strip()
    return last_sent == date.today().isoformat()


def mark_sent() -> None:
    """Record that digest was sent today."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(date.today().isoformat())


def build_email(
    digest: dict, html_body: str, sender: str, recipients: list[str]
) -> MIMEMultipart:
    """Build the email message with HTML body."""
    wine = digest.get("wine")
    if wine:
        subject = f"Tonight: {wine['vintage']} {wine['name']}"
    else:
        subject = "The Sommelier — Daily Digest"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    return msg


def send_email(msg: MIMEMultipart, username: str, password: str) -> None:
    """Send via Gmail SMTP with STARTTLS."""
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    if not DIGEST_JSON.exists():
        print(
            "ERROR: site/digest.json not found — run generate_digest.py first",
            file=sys.stderr,
        )
        sys.exit(1)

    digest = json.loads(DIGEST_JSON.read_text(encoding="utf-8"))
    html_body = DIGEST_HTML.read_text(encoding="utf-8") if DIGEST_HTML.exists() else ""

    # Check if there's content worth sending
    if not digest.get("has_content") and not force:
        print("Nothing to send (no menu today). Use --force to override.")
        return

    # Idempotency check
    if already_sent_today() and not force:
        print(
            f"Digest already sent today ({date.today().isoformat()}). "
            "Use --force to resend."
        )
        return

    # Resolve SMTP credentials
    smtp_username = os.environ.get("SMTP_USERNAME", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    recipients_str = os.environ.get("DIGEST_RECIPIENTS", "")

    if not dry_run and (not smtp_username or not smtp_password or not recipients_str):
        print(
            "ERROR: SMTP_USERNAME, SMTP_PASSWORD, and DIGEST_RECIPIENTS must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    msg = build_email(digest, html_body, smtp_username, recipients)

    if dry_run:
        print("=== DRY RUN ===")
        print(f"From: {smtp_username or '(not set)'}")
        print(f"To: {', '.join(recipients) if recipients else '(no recipients)'}")
        print(f"Subject: {msg['Subject']}")
        print(f"Body: {len(html_body)} bytes HTML")
        print("=== END DRY RUN ===")
        return

    try:
        send_email(msg, smtp_username, smtp_password)
    except Exception as e:
        print(f"ERROR: Failed to send digest email: {e}", file=sys.stderr)
        sys.exit(1)

    mark_sent()
    print(f"Digest sent to {', '.join(recipients)}")


if __name__ == "__main__":
    main()
