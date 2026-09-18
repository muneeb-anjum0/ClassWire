from scraper.smart_search import search_timetable


ITEMS = [
    {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_code": "SEC 3603", "course_title": "Software Project Management", "faculty": "Zainab Iftikhar", "time": "08:00 AM - 09:30 AM"},
    {"schedule_day": "Monday", "semester_display": "BSSE 6A", "course_code": "SEC 3608", "course_title": "Software Quality Engineering and Testing", "faculty": "Zainab Iftikhar", "time": "02:00 PM - 03:30 PM"},
    {"schedule_day": "Friday", "semester_display": "BSSE 7A", "course_code": "SEC 3603", "course_title": "Software Project Management", "faculty": "Muhammad Qasim", "time": "02:00 PM - 03:30 PM"},
]


def test_section_and_day_query():
    result = search_timetable("Timetable for BSSE7A on Friday", ITEMS)
    assert len(result["items"]) == 1
    assert result["items"][0]["faculty"] == "Muhammad Qasim"


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


def test_unique_honorific_surname_alias_is_merged_into_full_name():
    items = [
        {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_title": "Projects", "faculty": "Mr. Qasim", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "semester_display": "BSSE 8B", "course_title": "Data Science", "faculty": "Muhammad Qasim", "time": "02:00 PM - 03:30 PM"},
    ]
    result = search_timetable("When is Qasim free on Monday?", items)
    assert result["entities"]["faculty"] == ["Muhammad Qasim"]
    assert {item["faculty"] for item in result["items"]} == {"Muhammad Qasim"}
    assert result["faculty_availability"] == [
        {"faculty": "Muhammad Qasim", "slots": {"Monday": ["9:30 AM – 2:00 PM", "3:30 PM – 9:30 PM"]}},
    ]


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
