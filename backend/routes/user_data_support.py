"""Helpers for user data routes and async mail status updates."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from core.authentication import is_valid_automation_secret


def timestamp_now() -> str:
    return datetime.now().isoformat()


def automation_token_from_headers(headers) -> str:
    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "", 1).strip()
    return headers.get("X-Automation-Token", "")


def is_authorized_automation(headers) -> bool:
    return is_valid_automation_secret(automation_token_from_headers(headers))


def merge_daily_email_status(store, user_id: str, job_id: str, update: Dict[str, Any]) -> None:
    latest_settings = store.get_user_settings(user_id)
    latest_settings["daily_email_last_result"] = {
        **(latest_settings.get("daily_email_last_result") or {}),
        **update,
        "job_id": job_id,
        "updated_at": timestamp_now(),
    }
    store.save_user_settings(user_id, latest_settings)


def build_manual_email_message(result: Dict[str, Any]) -> str:
    if not result.get("success"):
        return result.get("error", "Mail send failed")

    provider = result.get("send_result", {}).get("provider", "email provider")
    personal_email = result.get("personal_email")
    if result.get("items") == 0:
        return f"No classes found email accepted by {provider} for {personal_email}"
    return f"Mail accepted by {provider} for {personal_email}"
