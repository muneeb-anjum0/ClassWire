from scraper.scheduler import _filter_faculty_items, _filter_subject_items


ITEMS = [
    {"course_code": "SEC 3603", "course_title": "Software Re-Engineering", "semester": "BS(SE)-7A"},
    {"course_code": "SEC-3603", "course_title": "Software Re Engineering", "semester": "BS(SE)-7B"},
    {"course_code": "CSC 1201", "course_title": "Programming Fundamentals", "semester": "BS(CS)-1A"},
]


def test_subject_code_matching_ignores_spacing_and_punctuation():
    matched = _filter_subject_items(ITEMS, ["sec3603"])
    assert len(matched) == 2


def test_subject_title_matching_ignores_spacing_and_case():
    matched = _filter_subject_items(ITEMS, ["SOFTWARE REENGINEERING"])
    assert len(matched) == 2


def test_subject_filter_keeps_all_sections():
    matched = _filter_subject_items(ITEMS, ["Software Re-Engineering"])
    assert {item["semester"] for item in matched} == {"BS(SE)-7A", "BS(SE)-7B"}


def test_partial_subject_name_returns_every_matching_course_with_original_data():
    items = ITEMS + [
        {"course_code": "SEC 3608", "course_title": "Software Quality Engineering and Testing", "semester": "BS(SE)-6A"},
    ]
    matched = _filter_subject_items(items, ["Software"])
    assert len(matched) == 3
    assert {item["course_code"] for item in matched} == {"SEC 3603", "SEC-3603", "SEC 3608"}
    assert matched[-1]["course_title"] == "Software Quality Engineering and Testing"


def test_faculty_fragment_matching_ignores_case_spacing_and_punctuation():
    items = [
        {"course_title": "Course A", "faculty": "Muhammad Qasim"},
        {"course_title": "Course B", "faculty": "Dr. Muhammad-Qasim"},
        {"course_title": "Course C", "faculty": "Reema Tariq"},
    ]
    assert len(_filter_faculty_items(items, ["qasim"])) == 2
    assert len(_filter_faculty_items(items, ["MUHAMMAD QASIM"])) == 2
