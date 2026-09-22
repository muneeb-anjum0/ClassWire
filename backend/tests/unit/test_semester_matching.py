"""Behavioral checks for flexible SZABIST semester and section matching."""

import pytest

from scraper.semester_matcher import (
    extract_all_semesters_from_line,
    find_all_matching_semesters,
    find_best_semester_match,
    flexible_semester_match,
    generate_semester_variations,
    normalize_semester,
    tokenize_semester,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BS (SE) - 7A", "BS(SE)-7A"),
        ("BS( SE)-  7A", "BS(SE)-7A"),
        ("BS (CS) - 1 D", "BS(CS)-1D"),
        ("  MS (DS) - 2  ", "MS(DS)-2"),
        ("", ""),
    ],
)
def test_semester_formatting_is_normalized_without_changing_identity(raw, expected):
    assert normalize_semester(raw) == expected


def test_tokenized_identity_ignores_spacing_punctuation_and_case():
    identities = {
        tokenize_semester("BS(SE)-7A"),
        tokenize_semester("bs (se) - 7a"),
        tokenize_semester("BSSE7A"),
    }

    assert identities == {"BSSE7A"}


def test_generated_variations_are_unique_and_preserve_the_same_identity():
    variations = generate_semester_variations("BS (SE) - 7A")

    assert variations
    assert len(variations) == len(set(variations))
    assert {tokenize_semester(value) for value in variations} == {"BSSE7A"}


@pytest.mark.parametrize(
    "candidate",
    ["BS(SE)-7A", "BS (SE) - 7A", "BS( SE)-  7A", "bs(se)-7a"],
)
def test_flexible_matching_accepts_equivalent_section_formats(candidate):
    assert flexible_semester_match(candidate, f"Schedule for {candidate}", ["BS(SE)-7A"])


def test_flexible_matching_rejects_missing_inputs_and_other_sections():
    assert not flexible_semester_match("", "Schedule for BS(SE)-7A", ["BS(SE)-7A"])
    assert not flexible_semester_match("BS(SE)-7A", "Schedule for BS(SE)-7A", [])
    assert not flexible_semester_match("BS(SE)-7B", "Schedule for BS(SE)-7B", ["BS(SE)-7A"])


def test_slash_separated_social_science_sections_are_extracted_individually():
    result = extract_all_semesters_from_line("BSSS-1A / BS(PSY)-1B")

    assert result == ["BSSS-1A", "BS(PSY)-1B"]


def test_matching_semesters_returns_only_allowed_sections():
    result = find_all_matching_semesters(
        "Combined class: BS(SE)-7A / BS(SE)-7B / BS(CS)-1A",
        ["BS(SE)-7A", "BS(CS)-1A"],
    )

    assert result == ["BS(SE)-7A", "BS(CS)-1A"]


def test_best_match_returns_normalized_identity_or_empty_string():
    assert find_best_semester_match("Timetable for BS (SE) - 7 A", ["BS(SE)-7A"]) == "BS(SE)-7A"
    assert find_best_semester_match("No section is present", ["BS(SE)-7A"]) == ""
    assert find_best_semester_match("BS(SE)-7A", []) == ""
