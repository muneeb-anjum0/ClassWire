from datetime import datetime, timedelta, timezone

from core.source_freshness import next_refresh_by_day, stale_source_days


NOW = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def test_each_weekday_has_an_independent_exact_seven_day_freshness_window():
    source = {
        "items": [],
        "refreshed_at_by_day": {
            "Monday": (NOW - timedelta(days=6, hours=23)).isoformat(),
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


def test_next_refresh_metadata_is_exposed_per_weekday():
    source = {"refreshed_at_by_day": {"Thursday": "2026-10-15T05:00:00Z"}}

    assert next_refresh_by_day(source) == {"Thursday": "2026-10-22T05:00:00Z"}
