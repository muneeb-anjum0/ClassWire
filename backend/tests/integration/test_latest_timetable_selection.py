from scraper.scheduler import (
    _build_query,
    _build_week_query,
    _compact_items,
    _day_from_subject,
    _latest_messages_by_weekday,
    _summarize,
    run_once,
)
from scraper.timetable_parser import TIMETABLE_PARSER_VERSION


def test_weekday_query_matches_subject_and_body_variants_without_an_age_limit():
    query = _build_query('subject:"Class Schedule" in:inbox', "Tuesday")

    assert "{subject:Tuesday \"for Tuesday\"}" in query
    assert "newer_than:" not in query
    assert "-in:trash" in query


def test_latest_weekday_messages_use_one_unbounded_query_per_day(monkeypatch):
    calls = []

    def fake_batch(_service, _user_email, queries):
        calls.append(queries)
        return {
            "Monday": {"id": "new-monday"},
            "Tuesday": {"id": "older-latest-tuesday"},
        }

    monkeypatch.setattr("scraper.scheduler.list_latest_messages_batch", fake_batch)

    result = _latest_messages_by_weekday(
        object(),
        "me",
        'subject:"Class Schedule" in:inbox',
        ["Monday", "Tuesday"],
    )

    assert result == {
        "Monday": {"id": "new-monday"},
        "Tuesday": {"id": "older-latest-tuesday"},
    }
    assert len(calls) == 1
    assert set(calls[0]) == {"Monday", "Tuesday"}
    assert all("newer_than:" not in query for query in calls[0].values())


def test_week_query_collects_each_supported_day_in_one_gmail_search():
    query = _build_week_query('subject:"Class Schedule" in:inbox')

    assert "subject:Monday" in query
    assert "subject:Saturday" in query
    assert '"for Tuesday"' in query
    assert "newer_than:" not in query


def test_day_detection_uses_whole_words_only():
    assert _day_from_subject("Class Schedule – Tuesday, September 15") == "Tuesday"
    assert _day_from_subject("Friday timetable") == "Friday"
    assert _day_from_subject("Fridayish draft") is None


def test_compact_items_remove_parser_diagnostics_but_keep_search_fields():
    item = {
        "row_number": 3,
        "semester": "BSSE7A",
        "semester_display": "BS(SE)-7A",
        "course": "SEC 3603 Software Project Management (3,0)",
        "course_title": "Software Project Management",
        "course_code": "SEC 3603",
        "faculty": "Muhammad Qasim",
        "room": "204",
        "time": "02:00 PM - 03:30 PM",
        "campus": "SZABIST University Campus",
        "schedule_day": "Monday",
        "raw_line": "very large parser source row",
        "raw_cells": ["duplicate", "parser", "data"],
        "full_text": "another duplicate parser representation",
        "faculty_name": "Muhammad Qasim",
    }

    compact = _compact_items([item])[0]

    assert compact["course"] == item["course"]
    assert compact["faculty"] == "Muhammad Qasim"
    assert compact["schedule_day"] == "Monday"
    assert "raw_line" not in compact
    assert "raw_cells" not in compact
    assert "full_text" not in compact
    assert "faculty_name" not in compact


def test_summary_uses_display_semesters_and_stable_course_identity():
    summary = _summarize([
        {"semester_display": "BS(SE)-7A", "course_code": "SEC 3603", "faculty": "One"},
        {"semester_display": "BS(SE)-7A", "course_code": "SEC 3603", "faculty": "Two"},
    ])

    assert summary == {
        "total_items": 2,
        "semester_breakdown": {"BS(SE)-7A": 2},
        "unique_courses": 1,
        "unique_faculty": 2,
    }


def test_week_refresh_fetches_and_parses_only_changed_weekdays(monkeypatch):
    from unittest.mock import MagicMock

    previous = {
        "parser_version": TIMETABLE_PARSER_VERSION,
        "message_ids_by_day": {"Monday": "old-mon", "Tuesday": "same-tue"},
        "source_received_at_by_day": {"Tuesday": "2026-09-15T10:00:00Z"},
        "items": [{
            "schedule_day": "Tuesday",
            "semester_display": "BS(SE)-7A",
            "course_title": "Reused Course",
            "course_code": "SEC 1000",
            "time": "08:00 AM - 09:30 AM",
        }],
    }
    fake_store = MagicMock()
    fake_store.get_user_tokens.return_value = {"token": "token"}
    monkeypatch.setattr("database.firestore_store.data_store", fake_store)
    monkeypatch.setattr("scraper.scheduler.build_service", lambda _credentials: object())
    monkeypatch.setattr("scraper.scheduler._latest_messages_by_weekday", lambda *_args: {
        "Monday": {"id": "new-mon"}, "Tuesday": {"id": "same-tue"},
    })
    fetched_ids = []

    def fake_fetch(_service, _email, ids):
        fetched_ids.extend(ids)
        return {"new-mon": {"id": "new-mon", "internalDate": "1789999200000", "payload": {}}}

    monkeypatch.setattr("scraper.scheduler.get_messages_batch", fake_fetch)
    monkeypatch.setattr("scraper.scheduler.get_message_html_from_message", lambda _message: "new html")
    monkeypatch.setattr("scraper.scheduler.parse_html_with_diagnostics", lambda *_args: ([{
        "semester_display": "BS(SE)-7A", "course_title": "New Course",
        "course_code": "SEC 2000", "time": "09:30 AM - 11:00 AM",
    }], {"parser_version": TIMETABLE_PARSER_VERSION, "accepted_rows": 1}))

    result = run_once(
        user_email="me",
        user_id="user-1",
        user_settings={"timetable_day": "Entire Week", "_save_cache": False, "_previous_source": previous},
    )

    assert result["success"] is True
    assert fetched_ids == ["new-mon"]
    assert result["data"]["refresh"] == {
        "changed_days": ["Monday"], "reused_days": ["Tuesday"], "fetched_messages": 1,
    }
    assert {item["course_title"] for item in result["data"]["items"]} == {"New Course", "Reused Course"}
