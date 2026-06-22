"""Shared defaults for persisted user settings."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

DEFAULT_USER_SETTINGS: Dict[str, Any] = {
    "allowed_semesters": [],
    "gmail_query_base": 'subject:("Class Schedule" OR schedule) in:inbox',
    "newer_than_days": 2,
    "timezone": "Asia/Karachi",
    "personal_email": "",
    "daily_email_enabled": False,
}


def build_default_user_settings(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a fresh default settings payload with optional overrides."""
    settings = deepcopy(DEFAULT_USER_SETTINGS)
    if overrides:
        settings.update(overrides)
    return settings
