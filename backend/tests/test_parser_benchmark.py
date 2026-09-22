import json
from pathlib import Path

from scraper.timetable_parser import parse_html_with_diagnostics


def test_labeled_parser_dataset_has_perfect_row_recall():
    cases = json.loads((Path(__file__).parent / "fixtures" / "parser_benchmark.json").read_text())
    for case in cases:
        actual, diagnostics = parse_html_with_diagnostics(case["html"])
        assert len(actual) == len(case["expected"]), case["name"]
        assert diagnostics["accepted_rows"] == len(case["expected"])
        for expected in case["expected"]:
            match = next(item for item in actual if item.get("course_code") == expected["course_code"])
            for field, value in expected.items():
                assert match.get(field) == value
