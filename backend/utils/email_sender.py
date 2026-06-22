"""Small public interface for sending timetable emails."""

from __future__ import annotations

from typing import Dict

from .email_content import build_plain_text, build_subject, build_timetable_email_html
from .email_providers import send_with_smtp

_build_plain_text = build_plain_text
_build_subject = build_subject


def send_timetable_email(to_email: str, university_email: str, timetable: Dict) -> Dict:
    return send_with_smtp(to_email, university_email, timetable)


__all__ = [
    "_build_plain_text",
    "_build_subject",
    "build_plain_text",
    "build_subject",
    "build_timetable_email_html",
    "send_timetable_email",
]
