from scraper.scheduler import (
    _build_query,
    _build_week_query,
    _compact_items,
    _day_from_subject,
    _summarize,
)


def test_weekday_query_matches_subject_and_body_variants():
    query = _build_query('subject:"Class Schedule" in:inbox', "Tuesday", 7)

    assert "{subject:Tuesday \"for Tuesday\"}" in query
    assert "newer_than:7d" in query
    assert "-in:trash" in query


def test_week_query_collects_each_supported_day_in_one_gmail_search():
    query = _build_week_query('subject:"Class Schedule" in:inbox', 14)

    assert "subject:Monday" in query
    assert "subject:Saturday" in query
    assert '"for Tuesday"' in query
    assert "newer_than:14d" in query


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
