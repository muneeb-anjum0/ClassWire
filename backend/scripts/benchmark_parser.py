"""Run the labeled parser benchmark and emit machine-readable quality metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper.timetable_parser import TIMETABLE_PARSER_VERSION, parse_html_with_diagnostics

IDENTITY_FIELDS = ("course_code", "course_title", "semester_display", "faculty", "room", "time")


def row_key(row):
    return tuple(str(row.get(field) or "").strip().casefold() for field in IDENTITY_FIELDS)


def main() -> int:
    path = ROOT / "tests" / "fixtures" / "parser_benchmark.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    true_positive = false_positive = false_negative = correct_fields = expected_fields = 0
    diagnostics = []
    for case in cases:
        actual, case_diagnostics = parse_html_with_diagnostics(case["html"])
        expected = case["expected"]
        actual_keys = {row_key(row) for row in actual}
        expected_keys = {row_key(row) for row in expected}
        true_positive += len(actual_keys & expected_keys)
        false_positive += len(actual_keys - expected_keys)
        false_negative += len(expected_keys - actual_keys)
        for expected_row in expected:
            candidates = [row for row in actual if row.get("course_code") == expected_row.get("course_code")]
            for field in IDENTITY_FIELDS:
                expected_fields += 1
                if candidates and candidates[0].get(field) == expected_row.get(field):
                    correct_fields += 1
        diagnostics.append({"name": case["name"], **case_diagnostics})
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    report = {
        "parser_version": TIMETABLE_PARSER_VERSION,
        "cases": len(cases),
        "row_precision": round(precision, 4),
        "row_recall": round(recall, 4),
        "field_accuracy": round(correct_fields / max(1, expected_fields), 4),
        "diagnostics": diagnostics,
    }
    print(json.dumps(report, indent=2))
    return 0 if precision == 1 and recall == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
