from datetime import date

from scraper.smart_search import parse_days, search_timetable


ITEMS = [
    {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_code": "SEC 3603", "course_title": "Software Project Management", "faculty": "Zainab Iftikhar", "time": "08:00 AM - 09:30 AM"},
    {"schedule_day": "Monday", "semester_display": "BSSE 6A", "course_code": "SEC 3608", "course_title": "Software Quality Engineering and Testing", "faculty": "Zainab Iftikhar", "time": "02:00 PM - 03:30 PM"},
    {"schedule_day": "Friday", "semester_display": "BSSE 7A", "course_code": "SEC 3603", "course_title": "Software Project Management", "faculty": "Muhammad Qasim", "time": "02:00 PM - 03:30 PM"},
]


def test_section_and_day_query():
    result = search_timetable("Timetable for BSSE7A on Friday", ITEMS)
    assert len(result["items"]) == 1
    assert result["items"][0]["faculty"] == "Muhammad Qasim"
    assert result["answer"] == "Found 1 class for BSSE 7A on Friday."


def test_relative_day_queries_resolve_from_the_local_calendar_date():
    sunday = date(2026, 9, 20)

    assert parse_days("BSSE7A classes today", sunday) == ["Sunday"]
    assert parse_days("classes tomorrow", sunday) == ["Monday"]
    assert parse_days("classes yesterday", sunday) == ["Saturday"]


def test_today_query_on_sunday_does_not_return_the_entire_week():
    result = search_timetable("BSSE7A classes today", ITEMS, date(2026, 9, 20))

    assert result["days"] == ["Sunday"]
    assert result["items"] == []
    assert result["answer"] == "No classes found for BSSE 7A on Sunday."


def test_first_name_faculty_query_matches_full_name():
    result = search_timetable("When does Zainab have classes?", ITEMS)
    assert len(result["items"]) == 2
    assert result["entities"]["faculty"] == ["Zainab Iftikhar"]


def test_full_faculty_name_beats_partial_first_or_last_name_collisions():
    items = [
        {"schedule_day": "Monday", "semester_display": "BSCS 3C", "course_title": "Assembly", "faculty": "Atif Iftikhar", "time": "12:00 PM - 01:00 PM"},
        {"schedule_day": "Monday", "semester_display": "BBA 2A", "course_title": "Marketing", "faculty": "Zainab Zia Dar", "time": "04:00 PM - 05:00 PM"},
        {"schedule_day": "Monday", "semester_display": "BSSE 5A", "course_title": "Testing", "faculty": "Zainab Iftikhar Chaudhary", "time": "06:00 PM - 07:00 PM"},
    ]
    result = search_timetable("When is Zainab Iftikhar free on Monday?", items)
    assert result["entities"]["faculty"] == ["Zainab Iftikhar Chaudhary"]
    assert len(result["items"]) == 1


def test_course_fragment_query():
    result = search_timetable("Show Software classes on Friday", ITEMS)
    assert len(result["items"]) == 1
    assert result["items"][0]["course_code"] == "SEC 3603"


def test_free_time_is_calculated_inside_university_hours():
    result = search_timetable("When is Zainab free on Monday?", ITEMS)
    assert result["intent"] == "free_time"
    assert result["free_slots"]["Monday"] == ["9:30 AM – 2:00 PM", "3:30 PM – 9:30 PM"]


def test_first_name_availability_is_separated_by_faculty_member():
    items = [
        {"schedule_day": "Monday", "course_title": "Programming", "faculty": "Zainab Iftikhar", "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Monday", "course_title": "Databases", "faculty": "Zainab Iftikhar", "time": "12:30 PM - 02:00 PM"},
        {"schedule_day": "Monday", "course_title": "Art", "faculty": "Zainab Zia Dar", "time": "11:10 AM - 02:00 PM"},
    ]
    result = search_timetable("When is Zainab free on Monday?", items)
    assert result["faculty_availability"] == [
        {"faculty": "Zainab Iftikhar", "slots": {"Monday": ["8:00 AM – 9:30 AM", "11:00 AM – 12:30 PM", "2:00 PM – 9:30 PM"]}},
        {"faculty": "Zainab Zia Dar", "slots": {"Monday": ["8:00 AM – 11:10 AM", "2:00 PM – 9:30 PM"]}},
    ]


def test_short_honorific_name_is_not_renamed_or_merged_with_full_name():
    items = [
        {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_title": "Projects", "faculty": "Mr. Qasim", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "semester_display": "BSSE 8B", "course_title": "Data Science", "faculty": "Muhammad Qasim", "time": "02:00 PM - 03:30 PM"},
    ]
    exact = search_timetable("When is Muhammad Qasim free on Monday?", items)
    assert exact["parser_version"] == 8
    assert exact["entities"]["faculty"] == ["Muhammad Qasim"]
    assert {item["faculty"] for item in exact["items"]} == {"Muhammad Qasim"}

    broad = search_timetable("When is Qasim free on Monday?", items)
    assert broad["entities"]["faculty"] == ["Mr. Qasim", "Muhammad Qasim"]
    assert {item["faculty"] for item in broad["items"]} == {"Mr. Qasim", "Muhammad Qasim"}
    assert {entry["faculty"] for entry in broad["faculty_availability"]} == {"Mr. Qasim", "Muhammad Qasim"}


def test_formatting_only_faculty_variants_are_one_consistent_identity():
    items = [
        {"schedule_day": "Monday", "course_title": "A", "faculty": "Dr Ghulam Mustafa", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Tuesday", "course_title": "B", "faculty": "Dr. Ghulam Mustafa", "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Wednesday", "course_title": "C", "faculty": "Dr. Ghulam Mustafa", "time": "11:00 AM - 12:30 PM"},
    ]

    result = search_timetable("When is Dr Ghulam Mustafa free?", items)

    assert result["entities"]["faculty"] == ["Dr. Ghulam Mustafa"]
    assert {item["faculty"] for item in result["items"]} == {"Dr. Ghulam Mustafa"}
    assert result["faculty_availability"][0]["faculty"] == "Dr. Ghulam Mustafa"


def test_duplicate_rows_do_not_inflate_search_results():
    item = {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_code": "SEC 1", "course_title": "Projects", "faculty": "Muhammad Qasim", "room": "204", "time": "02:00 PM - 03:30 PM"}
    result = search_timetable("When does Qasim have classes on Monday?", [item, dict(item)])
    assert len(result["items"]) == 1


def test_faculty_with_no_classes_on_selected_day_is_free_all_day():
    items = [
        {"schedule_day": "Tuesday", "course_title": "Projects", "faculty": "Zainab Zia Dar", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_title": "Data Science", "faculty": "Zainab Iftikhar", "time": "02:00 PM - 03:30 PM"},
    ]
    result = search_timetable("When is Zainab free on Monday?", items)
    availability = {entry["faculty"]: entry["slots"] for entry in result["faculty_availability"]}
    assert availability["Zainab Zia Dar"]["Monday"] == ["8:00 AM – 9:30 PM"]


def test_free_time_query_returns_faculty_timetable_for_requested_days_only():
    items = [
        {"schedule_day": "Monday", "course_title": "Projects", "faculty": "Safi Ullah", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Wednesday", "course_title": "Data Science", "faculty": "Safi Ullah", "time": "02:00 PM - 03:30 PM"},
        {"schedule_day": "Thursday", "course_title": "Research Methods and Practice", "faculty": "Safi Ullah", "time": "11:00 AM - 12:30 PM"},
        {"schedule_day": "Monday", "course_title": "Research Methods and Practice", "faculty": "Someone Else", "time": "11:00 AM - 12:30 PM"},
    ]
    result = search_timetable("When is sir Safi Ullah free on Monday and Thursday?", items)

    assert [item["schedule_day"] for item in result["items"]] == ["Monday", "Thursday"]


def test_overlapping_parallel_classes_are_merged_before_calculating_gaps():
    items = [
        {"schedule_day": "Monday", "course_title": "A", "faculty": "Sheikh Abdul Wahab", "time": "10:30 AM - 12:00 PM"},
        {"schedule_day": "Monday", "course_title": "B", "faculty": "Sheikh Abdul Wahab", "time": "03:30 PM - 05:00 PM"},
        {"schedule_day": "Monday", "course_title": "C", "faculty": "Sheikh Abdul Wahab", "time": "05:00 PM - 06:30 PM"},
        {"schedule_day": "Monday", "course_title": "D", "faculty": "Sheikh Abdul Wahab", "time": "05:00 PM - 06:30 PM"},
        {"schedule_day": "Monday", "course_title": "E", "faculty": "Sheikh Abdul Wahab", "time": "08:00 PM - 09:30 PM"},
    ]
    result = search_timetable("When is Wahab free on Monday?", items)
    assert result["free_slots"]["Monday"] == [
        "8:00 AM – 10:30 AM", "12:00 PM – 3:30 PM", "6:30 PM – 8:00 PM",
    ]


def test_invalid_or_out_of_hours_times_cannot_corrupt_availability():
    items = [
        {"schedule_day": "Monday", "course_title": "Invalid", "faculty": "Zainab Dar", "time": "TBA"},
        {"schedule_day": "Monday", "course_title": "Early", "faculty": "Zainab Dar", "time": "07:00 AM - 09:00 AM"},
        {"schedule_day": "Monday", "course_title": "Late", "faculty": "Zainab Dar", "time": "09:00 PM - 10:30 PM"},
    ]
    result = search_timetable("When is Zainab Dar free on Monday?", items)
    assert result["free_slots"]["Monday"] == ["9:00 AM – 9:00 PM"]


def test_common_name_and_day_typos_are_understood():
    result = search_timetable("When is Zainub free on Monay?", ITEMS)
    assert result["days"] == ["Monday"]
    assert result["entities"]["faculty"] == ["Zainab Iftikhar"]
    assert len(result["items"]) == 2


def test_course_typo_uses_fragment_fuzzy_matching():
    result = search_timetable("Show softwre classes on Friday", ITEMS)
    assert len(result["items"]) == 1
    assert result["items"][0]["course_code"] == "SEC 3603"


def test_specific_course_theory_query_excludes_its_lab_and_unrelated_development_courses():
    items = [
        {"schedule_day": "Monday", "semester_display": "BSSE 5A", "course_code": "SEC 3604", "course_title": "Software Construction and Development", "course": "SEC 3604 Software Construction and Development (2,0)", "faculty": "Teacher One", "time": "02:00 PM - 03:00 PM"},
        {"schedule_day": "Wednesday", "semester_display": "BSSE 5A", "course_code": "SEC 3604", "course_title": "Software Construction and Development Lab", "course": "SEC 3604 Lab: Software Construction and Development (0,1)", "faculty": "Teacher Two", "time": "02:00 PM - 04:00 PM"},
        {"schedule_day": "Thursday", "semester_display": "BSCS 4A", "course_code": "CSC 9999", "course_title": "Mobile Application Development", "course": "CSC 9999 Mobile Application Development (3,0)", "faculty": "Teacher Three", "time": "11:00 AM - 12:30 PM"},
        {"schedule_day": "Friday", "semester_display": "BSSE 7A", "course_code": "SEC 1111", "course_title": "Unrelated Course", "course": "SEC 1111 Unrelated Course (3,0)", "faculty": "Next Week", "time": "11:00 AM - 12:30 PM"},
    ]
    result = search_timetable(
        "when are Software Construction and Development theory classes in the entire week",
        items,
    )
    assert result["entities"]["faculty"] == []
    assert result["entities"]["courses"] == ["Software Construction and Development"]
    assert result["entities"]["class_types"] == ["theory"]
    assert len(result["items"]) == 1
    assert result["items"][0]["faculty"] == "Teacher One"


def test_course_type_credit_rules_cover_theory_lab_and_fyp():
    items = [
        {"schedule_day": "Monday", "course_title": "Capstone", "course": "Capstone (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Tuesday", "course_title": "Capstone", "course": "Capstone (2,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Wednesday", "course_title": "Capstone Lab", "course": "Capstone Lab (0,1)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Thursday", "course_title": "Capstone FYP", "course": "Capstone FYP (0,3)", "time": "08:00 AM - 09:30 AM"},
    ]
    assert len(search_timetable("Capstone theory entire week", items)["items"]) == 2
    assert len(search_timetable("Capstone lab entire week", items)["items"]) == 1
    assert len(search_timetable("Capstone FYP entire week", items)["items"]) == 1


def test_credit_hour_query_matches_total_course_credits_and_explains_result():
    items = [
        {"schedule_day": "Monday", "course_code": "SEC 1", "course_title": "Theory A", "course": "SEC 1 Theory A (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Tuesday", "course_code": "SEC 1", "course_title": "Theory A", "course": "SEC 1 Theory A (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Wednesday", "course_code": "SEC 2", "course_title": "FYP", "course": "SEC 2 FYP (0,3)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Thursday", "course_code": "SEC 3", "course_title": "Theory B", "course": "SEC 3 Theory B (2,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Friday", "course_code": "SEC 4", "course_title": "Lab", "course": "SEC 4 Lab (0,1)", "time": "08:00 AM - 09:30 AM"},
    ]

    result = search_timetable("show all 3 credit hour courses", items)

    assert result["entities"]["credit_hours"] == ["3"]
    assert [item["course_code"] for item in result["items"]] == ["SEC 1", "SEC 1", "SEC 2"]
    assert result["answer"] == "Found 3 scheduled classes across 2 3-credit-hour courses — 2 theory classes, 1 FYP class."


def test_credit_hour_phrasings_and_explicit_credit_field_are_supported():
    items = [
        {"schedule_day": "Monday", "course_code": "SEC 1001", "course_title": "Alpha", "course": "SEC 1001 Alpha (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_code": "SEC 1002", "course_title": "Beta", "credit_hours": 3, "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Monday", "course_code": "SEC 1003", "course_title": "Gamma", "course": "SEC 1003 Gamma (2,0)", "time": "11:00 AM - 12:30 PM"},
    ]

    for query in ("three credit-hour courses", "courses with 3 credit hours", "show 3 CH courses", "credit hours: 3", "show 3cr/hr courses"):
        result = search_timetable(query, items)
        assert [item["course_code"] for item in result["items"]] == ["SEC 1001", "SEC 1002"], query


def test_credit_hours_can_be_combined_with_class_type_and_day():
    items = [
        {"schedule_day": "Monday", "course_code": "A", "course_title": "A", "course": "A (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_code": "B", "course_title": "B", "course": "B (0,3)", "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Tuesday", "course_code": "C", "course_title": "C", "course": "C (3,0)", "time": "11:00 AM - 12:30 PM"},
    ]

    result = search_timetable("show all 3 credit hour theory courses on Monday", items)

    assert [item["course_code"] for item in result["items"]] == ["A"]


def test_credit_query_does_not_mistake_a_numeric_section_for_the_credit_value():
    items = [
        {"schedule_day": "Monday", "semester_display": "2", "course_code": "NOPE", "course_title": "Three Credits", "course": "NOPE Three Credits (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "semester_display": "BS(CS)-1A", "course_code": "CSC 1108", "course_title": "Computer Science", "course": "CSC 1108 Computer Science (2,0)", "time": "09:30 AM - 11:00 AM"},
    ]

    result = search_timetable("show all 2 cr/hr courses for Monday", items)

    assert result["entities"]["sections"] == []
    assert result["entities"]["credit_hours"] == ["2"]
    assert [item["course_code"] for item in result["items"]] == ["CSC 1108"]


def test_one_credit_query_keeps_theory_and_labs_distinct():
    items = [
        {"schedule_day": "Monday", "course_code": "MD 1120", "course_title": "Holy Quran", "course": "MD 1120 Holy Quran (1,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_code": "CSCL 1103", "course_title": "Programming Lab", "course": "CSCL 1103 Programming Lab (0,1)", "time": "09:30 AM - 11:00 AM"},
    ]

    result = search_timetable("show all 1 cr/hr courses", items)

    assert len(result["items"]) == 2
    assert result["answer"].endswith("1 theory class, 1 lab class.")


def test_multiple_credit_values_are_supported_in_one_query():
    items = [
        {"schedule_day": "Monday", "course_code": "SEC 2001", "course_title": "Alpha", "course": "SEC 2001 Alpha (2,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_code": "SEC 3001", "course_title": "Beta", "course": "SEC 3001 Beta (3,0)", "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Monday", "course_code": "SECL 1001", "course_title": "Gamma", "course": "SECL 1001 Gamma (0,1)", "time": "11:00 AM - 12:30 PM"},
    ]

    result = search_timetable("show 2 and 3 cr/hr courses", items)

    assert result["entities"]["credit_hours"] == ["3", "2"]
    assert [item["course_code"] for item in result["items"]] == ["SEC 2001", "SEC 3001"]


def test_broad_schedule_requests_return_the_selected_schedule_instead_of_nothing():
    result = search_timetable("show all classes on Monday", ITEMS)
    assert len(result["items"]) == 2
    assert {item["schedule_day"] for item in result["items"]} == {"Monday"}

    entire_week = search_timetable("show my entire timetable", ITEMS)
    assert len(entire_week["items"]) == len(ITEMS)


def test_day_only_timetable_request_is_a_valid_schedule_scope():
    result = search_timetable("timetable for Friday", ITEMS)

    assert result["recognized"] is True
    assert result["days"] == ["Friday"]
    assert len(result["items"]) == 1


def test_plural_labs_does_not_false_match_a_short_bs_section():
    items = [
        {
            "schedule_day": "Monday",
            "semester_display": "BS(CS)-1A",
            "course_title": "Programming Lab",
            "course": "CSCL 1103 Programming Lab (0,1)",
            "time": "12:00 PM - 02:00 PM",
        },
        {
            "schedule_day": "Monday",
            "semester_display": "BS",
            "course_title": "Media Studies",
            "course": "MD 1120 Media Studies (1,0)",
            "time": "08:00 AM - 09:30 AM",
        },
    ]

    result = search_timetable("show all 1 credit hour labs for Monday", items)

    assert result["recognized"] is True
    assert result["entities"]["sections"] == []
    assert result["entities"]["class_types"] == ["lab"]
    assert [item["course_title"] for item in result["items"]] == ["Programming Lab"]


def test_unrecognized_question_gives_an_interpretation_message():
    result = search_timetable("please solve something mysterious", ITEMS)
    assert result["items"] == []
    assert "couldn't identify" in result["answer"]
    assert result["recognized"] is False


def test_honorific_and_surname_resolve_faculty_availability():
    items = [
        {
            "schedule_day": "Monday",
            "course_title": "Software Re-Engineering",
            "faculty": "Sheikh Abdul Wahab",
            "time": "10:30 AM - 12:00 PM",
        },
        {
            "schedule_day": "Monday",
            "course_title": "Software Project Management",
            "faculty": "Muhammad Qasim",
            "time": "02:00 PM - 03:30 PM",
        },
    ]

    result = search_timetable("When is sir wahab free on Monday?", items)

    assert result["recognized"] is True
    assert result["entities"]["faculty"] == ["Sheikh Abdul Wahab"]
    assert [item["faculty"] for item in result["items"]] == ["Sheikh Abdul Wahab"]
    assert result["free_slots"]["Monday"] == ["8:00 AM – 10:30 AM", "12:00 PM – 9:30 PM"]


def test_maam_honorific_does_not_interfere_with_surname_matching():
    items = [{
        "schedule_day": "Tuesday",
        "course_title": "Design and Analysis of Algorithms",
        "faculty": "Zainab Iftikhar Chaudhary",
        "time": "03:30 PM - 05:00 PM",
    }]

    result = search_timetable("When is ma'am Zainab free on Tuesday?", items)

    assert result["recognized"] is True
    assert result["entities"]["faculty"] == ["Zainab Iftikhar Chaudhary"]


def test_partial_faculty_name_before_classes_is_treated_as_faculty_intent():
    items = [
        {"schedule_day": "Monday", "course_title": "Algorithms", "faculty": "Zainab Iftikhar Chaudhary", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_title": "Databases", "faculty": "Someone Else", "time": "09:30 AM - 11:00 AM"},
    ]

    result = search_timetable("Zainab Iftikhar classes Monday", items)

    assert result["entities"]["faculty"] == ["Zainab Iftikhar Chaudhary"]
    assert [item["faculty"] for item in result["items"]] == ["Zainab Iftikhar Chaudhary"]


def test_spelled_credit_number_is_not_mistaken_for_a_faculty_name():
    items = [
        {"schedule_day": "Monday", "course_title": "Programming Lab", "course": "CSCL 1103 Programming Lab (0,1)", "faculty": "Ada Lovelace", "time": "08:00 AM - 10:00 AM"},
        {"schedule_day": "Monday", "course_title": "Finance", "course": "FIN 2001 Finance (3,0)", "faculty": "Money Markets TBA", "time": "10:00 AM - 11:30 AM"},
    ]

    result = search_timetable("one credit hour courses", items)

    assert result["entities"]["faculty"] == []
    assert [item["course_title"] for item in result["items"]] == ["Programming Lab"]


def test_explicit_faculty_ignores_names_embedded_in_noisy_course_text():
    items = [
        {"schedule_day": "Monday", "course_title": "Databases", "faculty": "Sidra Aleem", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_title": "Narratology Aleem Raza Will Start From", "faculty": "Someone Else", "time": "09:30 AM - 11:00 AM"},
    ]
    result = search_timetable("When does Sidra Aleem have classes?", items)
    assert [item["faculty"] for item in result["items"]] == ["Sidra Aleem"]


def test_multiple_explicit_faculty_names_are_all_retained():
    items = [
        {"schedule_day": "Monday", "course_title": "Operating Systems", "faculty": "Safi Ullah", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_title": "Databases", "faculty": "Zainab Iftikhar Chaudhary", "time": "09:30 AM - 11:00 AM"},
    ]
    result = search_timetable("Show classes for Safi Ullah and Zainab Iftikhar Chaudhary", items)
    assert {item["faculty"] for item in result["items"]} == {"Safi Ullah", "Zainab Iftikhar Chaudhary"}


def test_exact_and_shortened_faculty_names_are_both_retained_for_availability():
    items = [
        {"schedule_day": "Monday", "course_title": "Algorithms", "faculty": "Zainab Iftikhar Chaudhary", "time": "09:30 AM - 11:00 AM"},
        {"schedule_day": "Monday", "course_title": "Programming", "faculty": "Hamza Imran", "time": "12:00 PM - 01:30 PM"},
    ]

    result = search_timetable("When is Zainab Iftikhar and Hamza Imran free on Monday?", items)

    assert result["entities"]["faculty"] == ["Zainab Iftikhar Chaudhary", "Hamza Imran"]
    assert [entry["faculty"] for entry in result["faculty_availability"]] == [
        "Zainab Iftikhar Chaudhary",
        "Hamza Imran",
    ]
    assert {item["faculty"] for item in result["items"]} == {
        "Zainab Iftikhar Chaudhary",
        "Hamza Imran",
    }


def test_nested_course_title_prefers_the_specific_explicit_title():
    items = [
        {"schedule_day": "Monday", "course_title": "Software Engineering", "course": "Software Engineering (3,0)", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "course_title": "Software Engineering Lab", "course": "Software Engineering Lab (0,1)", "time": "09:30 AM - 11:00 AM"},
    ]
    result = search_timetable("Show Software Engineering Lab classes", items)
    assert [item["course_title"] for item in result["items"]] == ["Software Engineering Lab"]


def test_lab_word_inside_exact_course_title_is_not_a_type_filter():
    items = [{
        "schedule_day": "Tuesday",
        "semester_display": "BBA-1A",
        "course_title": "IT in Business Lab (ORIENTATION)",
        "course": "BA 1108 IT in Business Lab (ORIENTATION)",
        "faculty": "Abbas Amir",
        "time": "08:00 AM - 11:00 AM",
    }]

    result = search_timetable(
        "When are IT in Business Lab (ORIENTATION) classes in the entire week?",
        items,
    )

    assert result["entities"]["courses"] == ["IT in Business Lab (ORIENTATION)"]
    assert result["entities"]["class_types"] == []
    assert result["items"] == items


def test_theory_word_inside_exact_course_title_is_not_a_type_filter():
    items = [{
        "schedule_day": "Monday",
        "semester_display": "BS(CS)-4A",
        "course_title": "Theory of Computation",
        "course": "CSC 3001 Theory of Computation",
        "faculty": "Teacher One",
        "time": "08:00 AM - 09:30 AM",
    }]

    result = search_timetable("Show Theory of Computation", items)

    assert result["entities"]["class_types"] == []
    assert len(result["items"]) == 1


def test_88_compacted_single_deletion_typos_resolve_to_the_unique_entity():
    faculty = [
        "Muhammad Qasim", "Ali Raza", "Syed Aziz Rasool", "Faisal Malik",
        "Zainab Iftikhar Chaudhary",
    ]
    courses = [
        "Software Construction and Development", "Data Structures and Algorithms",
        "Software Quality Engineering and Testing", "Introduction to Data Science",
        "Advanced Database Management Systems",
    ]
    items = [
        {
            "schedule_day": "Monday", "faculty": name, "course_title": course,
            "course": f"{course} (3,0)", "time": "08:00 AM - 09:30 AM",
            "semester_display": f"BS(SE)-{index + 1}A",
        }
        for index, (name, course) in enumerate(zip(faculty, courses))
    ]

    cases = []
    for field, values in (("faculty", faculty), ("course_title", courses)):
        for expected in values:
            compact = expected.replace(" ", "")
            variants = []
            for index, character in enumerate(compact):
                if not character.isalpha():
                    continue
                variant = compact[:index] + compact[index + 1:]
                if variant not in variants:
                    variants.append(variant)
            for variant in variants[:9]:
                cases.append((field, expected, variant))

    assert len(cases) == 88
    for field, expected, typo in cases:
        query = f"When is {typo} free?" if field == "faculty" else f"Show {typo} classes"
        result = search_timetable(query, items)
        assert len(result["items"]) == 1, (field, expected, typo, result["entities"])
        assert result["items"][0][field] == expected
