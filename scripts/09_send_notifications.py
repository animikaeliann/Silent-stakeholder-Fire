"""
Demo-safe sending of the drafts in output/team_notifications/*.json.

DEFAULT BEHAVIOR (zero configuration): dry run. Prints what would be sent,
to whom, with what subject -- sends nothing, writes nothing. This is what
runs if you just call `python scripts/09_send_notifications.py`.

Real sending only happens if ALL of the following are true:
  - DEMO_SEND_EMAIL is set (your own sending address -- read from the
    environment, never hardcoded in this file)
  - DEMO_RECIPIENT_OVERRIDE is set (every email goes here, no exceptions,
    regardless of which team a gap was routed to)
  - SMTP_HOST is set (this script will not guess a mail server; without
    it, sending is refused even if the two DEMO_* vars above are set, and
    the script falls back to a dry run instead of erroring out)

Optional when actually sending: SMTP_PORT (default 587), SMTP_USERNAME,
SMTP_PASSWORD.

Every real send rewrites the subject to
  "[DEMO -- would route to: {ORIGINAL_TEAM}] {original subject}"
so the simulated routing decision stays visible even though the email
physically only ever goes to DEMO_RECIPIENT_OVERRIDE. This script will
NEVER send to a gap's routed team address (e.g. mobile-client@...) --
those addresses don't exist and were never meant to receive real mail;
see output/team_notifications/README.md for why.

Usage: python scripts/09_send_notifications.py
"""
import json
import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTIF_DIR = ROOT / "output" / "team_notifications"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_drafts():
    return sorted(NOTIF_DIR.glob("gap_*.json"))


def send_config():
    sender = os.environ.get("DEMO_SEND_EMAIL")
    override = os.environ.get("DEMO_RECIPIENT_OVERRIDE")
    smtp_host = os.environ.get("SMTP_HOST")
    return sender, override, smtp_host


def dry_run(draft_paths, reason=None):
    print("=== DRY RUN -- no email will be sent ===")
    if reason:
        print(f"Reason: {reason}")
    print(
        "To actually send in demo mode, set DEMO_SEND_EMAIL (your own address), "
        "DEMO_RECIPIENT_OVERRIDE (where every email really goes), and SMTP_HOST -- all three."
    )
    print()
    for p in draft_paths:
        data = json.loads(p.read_text())
        print(f"Would send -> To: {data['to_address']}"
              + (f", Cc: {', '.join(data['cc_addresses'])}" if data.get("cc_addresses") else ""))
        print(f"             Subject: {data['subject']}")
    print(f"\n{len(draft_paths)} draft(s) would be sent.")


def real_send(draft_paths, sender, override, smtp_host):
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    sent = 0
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        for p in draft_paths:
            data = json.loads(p.read_text())
            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = override  # NEVER data["to_address"] -- override always wins
            msg["Subject"] = f"[DEMO -- would route to: {data['team']}] {data['subject']}"
            msg.set_content(data["body_text"])
            server.send_message(msg)
            sent += 1
            print(f"Sent: {msg['Subject']!r} -> {override}")
    print(f"\n{sent} email(s) sent, all to override address {override} "
          f"(never to any team address such as {json.loads(draft_paths[0].read_text())['to_address']}).")


def main():
    draft_paths = load_drafts()
    if not draft_paths:
        print("No drafts found in output/team_notifications/. Run scripts/08_draft_notifications.py first.")
        return

    sender, override, smtp_host = send_config()

    if not (sender and override):
        dry_run(draft_paths)
        return

    if not EMAIL_RE.match(sender) or not EMAIL_RE.match(override):
        dry_run(draft_paths, reason="DEMO_SEND_EMAIL or DEMO_RECIPIENT_OVERRIDE doesn't look like a "
                                     "valid email address; refusing to attempt a send.")
        return

    if not smtp_host:
        dry_run(draft_paths, reason="DEMO_SEND_EMAIL and DEMO_RECIPIENT_OVERRIDE are set, but "
                                     "SMTP_HOST is not -- this script will not guess a mail server.")
        return

    real_send(draft_paths, sender, override, smtp_host)


if __name__ == "__main__":
    main()
