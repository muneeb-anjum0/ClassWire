from datetime import datetime, timedelta, timezone

from core.source_freshness import next_refresh_by_day, stale_source_days


NOW = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def test_each_weekday_has_an_independent_next_week_calendar_boundary():
    source = {
        "items": [],
        "refreshed_at_by_day": {
            "Monday": (NOW - timedelta(days=6)).isoformat(),
            "Tuesday": (NOW - timedelta(days=7)).isoformat(),
            "Wednesday": (NOW - timedelta(days=8)).isoformat(),
        },
    }

    assert stale_source_days(source, ["Monday", "Tuesday", "Wednesday"], now=NOW) == [
        "Tuesday", "Wednesday",
    ]


def test_missing_weekday_marker_refreshes_only_the_requested_day():
    source = {
        "items": [{"schedule_day": "Monday"}],
        "refreshed_at_by_day": {"Monday": NOW.isoformat()},
    }

    assert stale_source_days(source, ["Monday"], now=NOW) == []
    assert stale_source_days(source, ["Tuesday"], now=NOW) == ["Tuesday"]


def test_next_refresh_metadata_is_the_next_local_weekday_midnight():
    source = {"refreshed_at_by_day": {"Thursday": "2026-10-15T05:00:00Z"}}

    assert next_refresh_by_day(source) == {"Thursday": "2026-10-21T19:00:00Z"}


def test_later_the_same_local_day_never_refreshes_but_next_week_midnight_does():
    source = {"refreshed_at_by_day": {"Wednesday": "2026-10-14T05:00:00Z"}}

    assert stale_source_days(
        source,
        ["Wednesday"],
        now=datetime(2026, 10, 14, 18, 59, 59, tzinfo=timezone.utc),
    ) == []
    assert stale_source_days(
        source,
        ["Wednesday"],
        now=datetime(2026, 10, 20, 18, 59, 59, tzinfo=timezone.utc),
    ) == []
    assert stale_source_days(
        source,
        ["Wednesday"],
        now=datetime(2026, 10, 20, 19, 0, 0, tzinfo=timezone.utc),
    ) == ["Wednesday"]
