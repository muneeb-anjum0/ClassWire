import json
from pathlib import Path

from scraper.timetable_parser import parse_html_with_diagnostics


def test_representative_timetable_examples_are_parsed_without_data_loss():
    fixture_path = Path(__file__).parents[1] / "fixtures" / "timetable_parser_examples.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    for case in cases:
        actual, diagnostics = parse_html_with_diagnostics(case["html"])
        assert len(actual) == len(case["expected"]), case["name"]
        assert diagnostics["accepted_rows"] == len(case["expected"])
        for expected in case["expected"]:
            match = next(item for item in actual if item.get("course_code") == expected["course_code"])
            for field, value in expected.items():
                assert match.get(field) == value
