"""Provider-specific email sending helpers."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Dict

from .email_content import build_plain_text, build_subject, build_timetable_email_html


def smtp_settings() -> Dict[str, object]:
    return {
        "host": os.environ.get("SMTP_HOST", "smtp-mail.outlook.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": os.environ.get("SMTP_USERNAME", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_name": os.environ.get("SMTP_FROM_NAME", "ClassWire"),
    }


def build_email_message(
    subject: str,
    from_email: str,
    from_name: str,
    to_email: str,
    university_email: str,
    timetable: Dict,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="classwire.local")
    msg.set_content(build_plain_text(timetable))
    msg.add_alternative(build_timetable_email_html(timetable, university_email), subtype="html")
    return msg


def send_with_smtp(to_email: str, university_email: str, timetable: Dict) -> Dict:
    smtp = smtp_settings()
    username = str(smtp["username"])
    password = str(smtp["password"])
    if not username or not password:
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD must be configured")

    subject = build_subject(timetable)
    msg = build_email_message(
        subject,
        username,
        str(smtp["from_name"]),
        to_email,
        university_email,
        timetable,
    )

    with smtplib.SMTP(str(smtp["host"]), int(smtp["port"]), timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.send_message(msg)

    return {"provider": "smtp", "subject": subject}
