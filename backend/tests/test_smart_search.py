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


def test_short_honorific_name_is_not_renamed_or_merged_with_full_name():
    items = [
        {"schedule_day": "Monday", "semester_display": "BSSE 7A", "course_title": "Projects", "faculty": "Mr. Qasim", "time": "08:00 AM - 09:30 AM"},
        {"schedule_day": "Monday", "semester_display": "BSSE 8B", "course_title": "Data Science", "faculty": "Muhammad Qasim", "time": "02:00 PM - 03:30 PM"},
    ]
    exact = search_timetable("When is Muhammad Qasim free on Monday?", items)
    assert exact["parser_version"] == 2
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
