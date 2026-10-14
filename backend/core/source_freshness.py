"""Weekday-aware freshness policy for persisted parsed timetables."""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo


SOURCE_FRESHNESS = timedelta(days=7)
SUPPORTED_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def _as_utc_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_requested_days(days: Iterable[str]) -> list[str]:
    selected = {str(day).strip().title() for day in days}
    return [day for day in SUPPORTED_DAYS if day in selected]


def _schedule_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("TZ", "Asia/Karachi"))
    except Exception:
        return ZoneInfo("Asia/Karachi")


def _next_weekday_boundary(timestamp: datetime) -> datetime:
    local = timestamp.astimezone(_schedule_timezone())
    next_date = local.date() + SOURCE_FRESHNESS
    return datetime.combine(next_date, time.min, tzinfo=local.tzinfo)


def stale_source_days(
    source: dict[str, Any] | None,
    requested_days: Iterable[str],
    *,
    now: datetime | None = None,
) -> list[str]:
    """Return requested weekdays missing or at their next Karachi week boundary."""
    days = normalize_requested_days(requested_days)
    if not days:
        return []
    current = (now or datetime.now(timezone.utc)).astimezone(_schedule_timezone())
    refreshed = (source or {}).get("refreshed_at_by_day")
    if not isinstance(refreshed, dict):
        return days
    return [
        day for day in days
        if (timestamp := _as_utc_datetime(refreshed.get(day))) is None
        or current >= _next_weekday_boundary(timestamp)
    ]


def next_refresh_by_day(source: dict[str, Any] | None) -> dict[str, str]:
    refreshed = (source or {}).get("refreshed_at_by_day")
    if not isinstance(refreshed, dict):
        return {}
    result = {}
    for day in SUPPORTED_DAYS:
        timestamp = _as_utc_datetime(refreshed.get(day))
        if timestamp is not None:
            boundary = _next_weekday_boundary(timestamp).astimezone(timezone.utc)
            result[day] = boundary.isoformat().replace("+00:00", "Z")
    return result


def has_cached_source(source: Any) -> bool:
    return isinstance(source, dict) and isinstance(source.get("items"), list)
