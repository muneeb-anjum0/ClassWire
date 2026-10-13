"""Weekday-aware freshness policy for persisted parsed timetables."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


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


def stale_source_days(
    source: dict[str, Any] | None,
    requested_days: Iterable[str],
    *,
    now: datetime | None = None,
) -> list[str]:
    """Return requested weekdays that have never refreshed or are seven days old."""
    days = normalize_requested_days(requested_days)
    if not days:
        return []
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    refreshed = (source or {}).get("refreshed_at_by_day")
    if not isinstance(refreshed, dict):
        return days
    return [
        day for day in days
        if (timestamp := _as_utc_datetime(refreshed.get(day))) is None
        or current - timestamp >= SOURCE_FRESHNESS
    ]


def next_refresh_by_day(source: dict[str, Any] | None) -> dict[str, str]:
    refreshed = (source or {}).get("refreshed_at_by_day")
    if not isinstance(refreshed, dict):
        return {}
    result = {}
    for day in SUPPORTED_DAYS:
        timestamp = _as_utc_datetime(refreshed.get(day))
        if timestamp is not None:
            result[day] = (timestamp + SOURCE_FRESHNESS).isoformat().replace("+00:00", "Z")
    return result


def has_cached_source(source: Any) -> bool:
    return isinstance(source, dict) and isinstance(source.get("items"), list)
