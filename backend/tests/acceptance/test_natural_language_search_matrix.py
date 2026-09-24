"""Forty high-risk natural-language scenarios that define search correctness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from scraper.smart_search import search_timetable


def row(
    item_id: str,
    day: str,
    section: str,
    code: str,
    title: str,
    credits: str,
    faculty: str,
    time: str,
) -> dict:
    return {
        "test_id": item_id,
        "schedule_day": day,
        "semester_display": section,
        "course_code": code,
        "course_title": title,
        "course": f"{code} {title} {credits}",
        "faculty": faculty,
        "room": "201",
        "campus": "SZABIST University Campus",
        "time": time,
    }


ITEMS = [
    # BS(SE)-7A base timetable.
    row("a1", "Monday", "BS(SE)-7A", "SEC 3603", "Software Project Management", "(3,0)", "Muhammad Qasim", "02:00 PM - 03:30 PM"),
    row("a2", "Monday", "BS(SE)-7A", "SEC 3612", "Mobile Application Development", "(3,0)", "Sheikh Abdul Wahab", "05:00 PM - 06:30 PM"),
    row("a3", "Wednesday", "BS(SE)-7A", "SEC 3612", "Mobile Application Development", "(3,0)", "Sheikh Abdul Wahab", "05:00 PM - 06:30 PM"),
    row("a4", "Wednesday", "BS(SE)-7A", "SEC 3606", "Software Re-Engineering", "(3,0)", "Awais Mahmood", "08:00 PM - 09:30 PM"),
    row("a5", "Thursday", "BS(SE)-7A", "SEC 3603", "Software Project Management", "(3,0)", "Muhammad Qasim", "02:00 PM - 03:30 PM"),
    row("a6", "Thursday", "BS(SE)-7A", "SEC 3606", "Software Re-Engineering", "(3,0)", "Sheikh Abdul Wahab", "03:30 PM - 05:00 PM"),
    row("a7", "Friday", "BS(SE)-7A", "SEC 4515", "Digital Image Processing", "(3,0)", "Reema Tariq", "05:00 PM - 06:30 PM"),
    row("a8", "Wednesday", "BS(SE)-7A", "SEC 4515", "Digital Image Processing", "(3,0)", "Reema Tariq", "06:30 PM - 08:00 PM"),
    row("a9", "Tuesday", "BS(SE)-7A", "SEC 4516", "Artificial Intelligence", "(2,0)", "Arfa Asaf", "06:30 PM - 08:00 PM"),
    row("a10", "Monday", "BS(SE)-7A", "SECL 7001", "Research Lab", "(0,1)", "Hamza Imran", "08:00 AM - 10:00 AM"),
    # BS(SE)-5A contains competing theory/lab rows and distractors.
    row("b1", "Monday", "BS(SE)-5A", "SEC 3604", "Software Construction and Development", "(2,0)", "Tooba Abdul Qudoos Khan", "02:00 PM - 03:00 PM"),
    row("b2", "Wednesday", "BS(SE)-5A", "SEC 3604", "Software Construction and Development", "(2,0)", "Tooba Abdul Qudoos Khan", "05:30 PM - 06:30 PM"),
    row("b3", "Wednesday", "BS(SE)-5A", "SECL 3604", "Software Construction and Development", "(0,1)", "Syed Haseeb Amjad", "02:00 PM - 04:00 PM"),
    row("b4", "Monday", "BS(SE)-5A", "CSC 3202", "Design and Analysis of Algorithms", "(3,0)", "Zainab Iftikhar Chaudhary", "03:30 PM - 05:00 PM"),
    row("b5", "Wednesday", "BS(SE)-5A", "CSC 3202", "Design and Analysis of Algorithms", "(3,0)", "Zainab Iftikhar Chaudhary", "03:30 PM - 05:00 PM"),
    row("b6", "Friday", "BS(SE)-5A", "CSC 3209", "Computer Networks", "(2,0)", "Someone Else", "05:00 PM - 06:00 PM"),
    row("b7", "Monday", "BS(SE)-5A", "MD 1120", "Understanding of Holy Quran", "(1,0)", "Hafiz Atiq ur Rehman", "08:00 AM - 09:30 AM"),
    row("b8", "Monday", "BS(SE)-5A", "SEC 5000", "Requirements Engineering", "(3,0)", "Someone Else", "06:30 PM - 08:00 PM"),
    # BS(SE)-5B repeats titles and adds labs to expose section/type leakage.
    row("c1", "Monday", "BS(SE)-5B", "SEC 3604", "Software Construction and Development", "(2,0)", "Iqra Yasmin", "05:00 PM - 06:00 PM"),
    row("c2", "Wednesday", "BS(SE)-5B", "SEC 3604", "Software Construction and Development", "(2,0)", "Iqra Yasmin", "04:00 PM - 05:00 PM"),
    row("c3", "Monday", "BS(SE)-5B", "SECL 3604", "Software Construction and Development", "(0,1)", "Jawad Naseer", "12:00 PM - 02:00 PM"),
    row("c4", "Tuesday", "BS(SE)-5B", "SECL 3604", "Software Construction and Development", "(0,1)", "Zainab Iftikhar Chaudhary", "12:00 PM - 02:00 PM"),
    row("c5", "Monday", "BS(SE)-5B", "CSC 3209", "Computer Networks", "(2,0)", "Zainab Iftikhar Chaudhary", "02:00 PM - 03:00 PM"),
    row("c6", "Wednesday", "BS(SE)-5B", "CSC 3209", "Computer Networks", "(2,0)", "Zainab Iftikhar Chaudhary", "05:00 PM - 06:00 PM"),
    row("c7", "Friday", "BS(SE)-5B", "CSC 3209", "Computer Networks", "(2,0)", "Zainab Iftikhar Chaudhary", "06:00 PM - 07:00 PM"),
    row("c8", "Tuesday", "BS(SE)-5B", "SEC 5001", "Web Engineering", "(3,0)", "Someone Else", "03:30 PM - 05:00 PM"),
    # BS(SE)-6A courses include 2-credit theory, 3-credit theory, and FYP.
    row("d1", "Monday", "BS(SE)-6A", "SEC 4516", "Artificial Intelligence", "(2,0)", "Arfa Asaf", "02:30 PM - 04:00 PM"),
    row("d2", "Wednesday", "BS(SE)-6A", "SEC 4516", "Artificial Intelligence", "(2,0)", "Arfa Asaf", "02:00 PM - 03:30 PM"),
    row("d3", "Monday", "BS(SE)-6A", "SEC 3608", "Software Quality Engineering and Testing", "(3,0)", "Arfa Asaf", "02:00 PM - 03:30 PM"),
    row("d4", "Wednesday", "BS(SE)-6A", "SEC 3608", "Software Quality Engineering and Testing", "(3,0)", "Arfa Asaf", "06:30 PM - 08:00 PM"),
    row("d5", "Tuesday", "BS(SE)-6A", "SEC 6001", "Cloud Computing", "(3,0)", "Someone Else", "08:00 AM - 09:30 AM"),
    row("d6", "Thursday", "BS(SE)-6A", "SEC 6002", "Information Security", "(3,0)", "Someone Else", "09:30 AM - 11:00 AM"),
    row("d7", "Monday", "BS(SE)-6A", "FYP 6003", "Final Year Project", "(0,3)", "Project Supervisor", "08:00 AM - 11:00 AM"),
    # BS(SE)-6B includes the same code/title plus ambiguous faculty identities.
    row("e1", "Monday", "BS(SE)-6B", "SEC 3608", "Software Quality Engineering and Testing", "(3,0)", "Iqra Yasmin", "02:00 PM - 03:30 PM"),
    row("e2", "Wednesday", "BS(SE)-6B", "SEC 3608", "Software Quality Engineering and Testing", "(3,0)", "Iqra Yasmin", "02:00 PM - 03:30 PM"),
    row("e3", "Tuesday", "BS(SE)-6B", "SEC 6101", "Secure Software Design", "(3,0)", "Someone Else", "09:30 AM - 11:00 AM"),
    row("e4", "Thursday", "BS(SE)-6B", "SEC 6102", "Software Metrics", "(3,0)", "Zainab Iftikhar Chaudhary", "11:00 AM - 12:30 PM"),
    row("e5", "Tuesday", "BS(SE)-6B", "SEC 6103", "DevOps", "(3,0)", "Muhammad Qasim", "02:00 PM - 03:30 PM"),
    row("e6", "Tuesday", "BS(SE)-6B", "SEC 6104", "Technology Management", "(3,0)", "Mr. Qasim", "03:30 PM - 05:00 PM"),
    row("e7", "Friday", "BS(SE)-6B", "SEC 3608", "Software Quality Engineering and Testing", "(3,0)", "Iqra Yasmin", "05:00 PM - 06:30 PM"),
]


@dataclass(frozen=True)
class AcceptanceCase:
    number: int
    query: str
    expected_ids: frozenset[str]
    availability_faculty: frozenset[str] = frozenset()
    conflict_expected: bool = False


def ids(*values: str) -> frozenset[str]:
    return frozenset(values)


CASES = [
    AcceptanceCase(1, "Show BSSE7A classes on Wednesday", ids("a3", "a4", "a8")),
    AcceptanceCase(2, "BSSE5A and BSSE5B classes on Monday", ids("b1", "b4", "b7", "b8", "c1", "c3", "c5")),
    AcceptanceCase(3, "Show Software Re-Engineering classes for the entire week", ids("a4", "a6")),
    AcceptanceCase(4, "Show SEC 3608 classes for BSSE6B", ids("e1", "e2", "e7")),
    AcceptanceCase(5, "When is Sheikh Abdul Wahab free on Thursday?", ids("a6"), ids("Sheikh Abdul Wahab")),
    AcceptanceCase(6, "When are Zainab Iftikhar Chaudhary and Hamza Imran free on Monday?", ids("a10", "b4", "c5"), ids("Zainab Iftikhar Chaudhary", "Hamza Imran")),
    AcceptanceCase(7, "when is sir wahab free on thursday", ids("a6"), ids("Sheikh Abdul Wahab")),
    AcceptanceCase(8, "When is Zainub Iftikhar free on Monay?", ids("b4", "c5"), ids("Zainab Iftikhar Chaudhary")),
    AcceptanceCase(9, "Show all 2 cr/hr theory courses on Wednesday", ids("b2", "c2", "c6", "d2")),
    AcceptanceCase(10, "Show all 1-credit-hour labs on Monday", ids("a10", "c3")),
    AcceptanceCase(11, "Show every FYP course in the entire week", ids("d7")),
    AcceptanceCase(12, "Show 2 and 3 credit hour courses on Friday", ids("a7", "b6", "c7", "e7")),
    AcceptanceCase(13, "What classes does BSSE7A have tomorrow?", ids("a9")),
    AcceptanceCase(14, "BSSE6A timetable for the whole week", ids("d1", "d2", "d3", "d4", "d5", "d6", "d7")),
    AcceptanceCase(15, "Show Software Construction and Development theory for BSSE5A on Monday", ids("b1")),
    AcceptanceCase(16, "Take Software Construction and Development with BSSE5B and Software Quality Engineering and Testing with BSSE6B", ids("c1", "c2", "c3", "c4", "e1", "e2", "e7")),
    AcceptanceCase(17, "I am in BSSE5A; add Artificial Intelligence from BSSE6A", ids("b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "d1", "d2")),
    AcceptanceCase(18, "My section is BSSE6B; include Computer Networks from BSSE5B and Digital Image Processing from BSSE7A", ids("e1", "e2", "e3", "e4", "e5", "e6", "e7", "c5", "c6", "c7", "a7", "a8")),
    AcceptanceCase(19, "I belong to BSSE7A plus SEC 3608 from BSSE6A", ids("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "d3", "d4")),
    AcceptanceCase(20, "Take Software Construction and Development lab with BSSE5B and Artificial Intelligence theory with BSSE6A", ids("c3", "c4", "d1", "d2")),
    AcceptanceCase(21, "I'm from BSSE7A; add SEC 3604 theory from BSSE5B, SECL 3604 lab from BSSE5A, and SEC 3608 from BSSE6B.", ids("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "c1", "c2", "b3", "e1", "e2", "e7")),
    AcceptanceCase(22, "My section is BSSE6A; include theory Software Construction and Development with BSSE5B", ids("d1", "d2", "d3", "d4", "d5", "d6", "d7", "c1", "c2")),
    AcceptanceCase(23, "BSSE7A timetable plus Software Construction and Development (BSSE5B) and Software Quality Engineering and Testing (BSSE6A)", ids("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "c1", "c2", "c3", "c4", "d3", "d4")),
    AcceptanceCase(24, "I am in BSSE6A but want Design and Analysis of Algorithms from BSSE5A on Monday and Wednesday", ids("d1", "d2", "d3", "d4", "d7", "b4", "b5")),
    AcceptanceCase(25, "I belong to BSSE7A and also want SEC 3604 Software Construction and Development with BSSE5B", ids("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "c1", "c2", "c3", "c4")),
    AcceptanceCase(26, "When are Muhammad Qasim and Sheikh Abdul Wahab available on Monday and Thursday?", ids("a1", "a2", "a5", "a6"), ids("Muhammad Qasim", "Sheikh Abdul Wahab")),
    AcceptanceCase(27, "When is Qasim free on Tuesday?", ids("e5", "e6"), ids("Muhammad Qasim", "Mr. Qasim")),
    AcceptanceCase(28, "Show Zainab Iftikhar Chaudhary classes on Monday and Thursday", ids("b4", "c5", "e4")),
    AcceptanceCase(29, "Show Software Construction and Development theory classes for the entire week", ids("b1", "b2", "c1", "c2")),
    AcceptanceCase(30, "Show SEC3608 on Monay and Wednesay", ids("d3", "d4", "e1", "e2")),
    AcceptanceCase(31, "BS (SE) - 7A timetable Friday", ids("a7")),
    AcceptanceCase(32, "show all 3 CH theory courses on Monday and Wednesday", ids("a1", "a2", "a3", "a4", "a8", "b4", "b5", "b8", "d3", "d4", "e1", "e2")),
    AcceptanceCase(33, "Show all 3-credit-hour FYP courses", ids("d7")),
    AcceptanceCase(34, "Show all 1 credit hour theory courses for the whole week", ids("b7")),
    AcceptanceCase(35, "When is ZainabIftikharChaudhary free on Tuesday?", ids("c4"), ids("Zainab Iftikhar Chaudhary")),
    AcceptanceCase(36, "show softwre re enginering classes on Thursday", ids("a6")),
    AcceptanceCase(37, "Show BSSE6A and BSSE6B classes on Tuesday and Thursday", ids("d5", "d6", "e3", "e4", "e5", "e6")),
    AcceptanceCase(38, "Show Computer Networks classes taught by Zainab Iftikhar Chaudhary", ids("c5", "c6", "c7")),
    AcceptanceCase(39, "Take Software Construction and Development theory with BSSE5B and Software Construction and Development lab with BSSE5A", ids("c1", "c2", "b3")),
    AcceptanceCase(40, "I am from BSSE7A; include Artificial Intelligence from BSSE6A and Computer Networks from BSSE5B on Monday and Wednesday", ids("a1", "a2", "a3", "a4", "a8", "a10", "d1", "d2", "c5", "c6"), conflict_expected=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"query-{case.number:02d}")
def test_natural_language_query_returns_only_the_expected_schedule(case: AcceptanceCase):
    result = search_timetable(case.query, ITEMS, reference_date=date(2026, 9, 21))
    actual_ids = {item["test_id"] for item in result["items"]}

    assert result["recognized"] is True
    assert actual_ids == case.expected_ids, {
        "query": case.query,
        "missing": sorted(case.expected_ids - actual_ids),
        "unexpected": sorted(actual_ids - case.expected_ids),
        "entities": result["entities"],
        "query_plan": result["query_plan"],
    }
    if case.availability_faculty:
        assert result["intent"] == "free_time"
        assert {entry["faculty"] for entry in result["faculty_availability"]} == case.availability_faculty
    if case.conflict_expected:
        assert result["conflict_count"] > 0


BASE_7A = ids("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10")
BASE_7A_WITHOUT_REENGINEERING = ids("a1", "a2", "a3", "a5", "a7", "a8", "a9", "a10")
CUSTOM_WITHOUT_REENGINEERING = BASE_7A_WITHOUT_REENGINEERING | ids(
    "c1", "c2", "c3", "c4", "d3", "d4",
)


@pytest.mark.parametrize(
    ("query", "expected_ids", "expected_faculty", "expected_intent"),
    [
        (
            "I am taking every class with BSSE7A except Software Re-Engineering, and I am taking Software Construction and Development with BSSE5B and Software Quality Engineering and Testing with BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "I am in BSSE7A, and I am taking Software Construction and Development with BSSE5B and Software Quality Engineering and Testing with BSSE6A. I don't take Software Re-Engineering with BSSE7A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "Every BSSE7A class except Software Re-Engineering; add Software Construction and Development from BSSE5B and Software Quality Engineering and Testing from BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "Keep my BSSE7A timetable excluding Software Re-Engineering, plus Software Construction and Development with BSSE5B and Software Quality Engineering and Testing with BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "My base is BSSE7A. Without SEC 3606, include SEC 3604 from BSSE5B and SEC 3608 from BSSE6A",
            BASE_7A_WITHOUT_REENGINEERING | ids("c1", "c2", "d3", "d4"),
            frozenset(), "schedule",
        ),
        (
            "I belong to BSSE7A, but not Software Re-Engineering. Also take Software Construction and Development with BSSE5B and Software Quality Engineering and Testing with BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "Use BSSE7A as my schedule other than Software Re-Engineering, along with Software Construction and Development from BSSE5B and Software Quality Engineering and Testing from BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "BSSE7A full timetable, leave out Software Re-Engineering, then add Software Construction and Development from BSSE5B and Software Quality Engineering and Testing from BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "All BSSE7A classes, skip Software Re-Engineering, and take Software Construction and Development with BSSE5B plus Software Quality Engineering and Testing with BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "Start with BSSE7A; remove Software Re-Engineering; include Software Construction and Development from BSSE5B and Software Quality Engineering and Testing from BSSE6A",
            CUSTOM_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "Show BSSE7A classes except Software Re-Engineering",
            BASE_7A_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        (
            "I am from BSSE7A and I do not take Software Re-Engineering",
            BASE_7A_WITHOUT_REENGINEERING, frozenset(), "schedule",
        ),
        ("I am from BSSE7A", BASE_7A, frozenset(), "schedule"),
        ("My section is BSSE7A", BASE_7A, frozenset(), "schedule"),
        ("Give me the complete BSSE7A timetable", BASE_7A, frozenset(), "schedule"),
        (
            "When is Sir Wahab free?",
            ids("a2", "a3", "a6"), ids("Sheikh Abdul Wahab"), "free_time",
        ),
        (
            "Show Sir Wahab's availability",
            ids("a2", "a3", "a6"), ids("Sheikh Abdul Wahab"), "free_time",
        ),
        (
            "What open slots does Sheikh Abdul Wahab have?",
            ids("a2", "a3", "a6"), ids("Sheikh Abdul Wahab"), "free_time",
        ),
        (
            "When is Sir Qasim free on Monday and Tuesday?",
            ids("a1", "e5", "e6"), ids("Muhammad Qasim", "Mr. Qasim"), "free_time",
        ),
        (
            "Show Qasim's availability for Monday and Tuesday",
            ids("a1", "e5", "e6"), ids("Muhammad Qasim", "Mr. Qasim"), "free_time",
        ),
    ],
    ids=[f"language-variant-{number:02d}" for number in range(1, 21)],
)
def test_schedule_language_variants(
    query: str,
    expected_ids: frozenset[str],
    expected_faculty: frozenset[str],
    expected_intent: str,
):
    result = search_timetable(query, ITEMS, reference_date=date(2026, 9, 21))

    assert {item["test_id"] for item in result["items"]} == expected_ids
    assert result["intent"] == expected_intent
    assert {entry["faculty"] for entry in result["faculty_availability"]} == expected_faculty
    if expected_intent == "free_time":
        assert result["conflict_count"] == 0


@pytest.mark.parametrize(
    "query",
    [
        "Class of BSSE7A and Software Construction and Development with BSSE5B today",
        "BSSE7A classes and Software Construction and Development with BSSE5B today",
        "Class of BSSE7A alongside Software Construction and Development from BSSE5B today",
        "BSSE7A schedule; Software Construction and Development from BSSE5B today",
        "Software Construction and Development with BSSE5B today, and class of BSSE7A",
    ],
)
def test_structural_planner_understands_base_section_and_bound_addition_without_trigger_words(query: str):
    result = search_timetable(query, ITEMS, reference_date=date(2026, 9, 24))

    assert {item["test_id"] for item in result["items"]} == ids("a5", "a6")
    assert result["query_plan"]["combination"] == "union"
    assert result["query_plan"]["selection_scope"]["base_sections"] == ["BS(SE)-7A"]
    assert result["query_plan"]["selection_scope"]["course_section_pairs"] == [{
        "section": "BS(SE)-5B",
        "kind": "course",
        "value": "Software Construction and Development",
        "class_types": [],
    }]


def test_semantic_plan_survives_generated_clause_order_and_wording_variants():
    """Exercise a query family instead of maintaining only hand-picked sentences."""
    base_phrases = [
        "I am from BSSE7A",
        "My section is BSSE7A",
        "Class of BSSE7A",
    ]
    exclusion_phrases = [
        "except Software Re-Engineering",
        "without Software Re-Engineering",
        "skip SEC 3606",
    ]
    addition = (
        "take Software Construction and Development with BSSE5B and "
        "Software Quality Engineering and Testing with BSSE6A"
    )
    templates = [
        "{base}, {exclusion}, and {addition}",
        "{base}; {addition}; {exclusion}",
        "{addition}; {base}; {exclusion}",
    ]

    checked = 0
    for base in base_phrases:
        for exclusion in exclusion_phrases:
            for template in templates:
                query = template.format(
                    base=base,
                    exclusion=exclusion,
                    addition=addition,
                )
                result = search_timetable(query, ITEMS, reference_date=date(2026, 9, 21))
                actual_ids = {item["test_id"] for item in result["items"]}

                assert actual_ids == CUSTOM_WITHOUT_REENGINEERING, query
                assert result["query_plan"]["combination"] == "union", query
                assert result["query_plan"]["selection_scope"]["base_sections"] == [
                    "BS(SE)-7A"
                ], query
                assert result["query_plan"]["exclusions"], query
                checked += 1

    assert checked == 27


def test_entity_resolution_combines_typos_shorthand_and_intent_without_losing_context():
    cases = [
        (
            "Show softwre re enginering for BSSE7A",
            ids("a4", "a6"),
            "schedule",
        ),
        (
            "I am from BSSE7A except softwre re enginering",
            BASE_7A_WITHOUT_REENGINEERING,
            "schedule",
        ),
        ("Classes of BSSE7A on Tues", ids("a9"), "schedule"),
        ("I am from BSE7A", BASE_7A, "schedule"),
        ("Could I meet sir Wahab on Tues?", ids(), "free_time"),
        (
            "When does sir Wahab not have a class?",
            ids("a2", "a3", "a6"),
            "free_time",
        ),
        ("Classes for 7A today", ids("a1", "a2", "a10"), "schedule"),
    ]

    for query, expected_ids, expected_intent in cases:
        result = search_timetable(query, ITEMS, reference_date=date(2026, 9, 21))

        assert {item["test_id"] for item in result["items"]} == expected_ids, query
        assert result["intent"] == expected_intent, query
