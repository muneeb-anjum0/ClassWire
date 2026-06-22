"""Build normalized timetable items from extracted row fields."""

import re
from typing import Dict, List, Optional

from .parser_fields import (
    _normalize_semester_key,
    _normalize_semester_display,
    _semester_matches_filters,
    _is_name_token,
    _is_section_token,
    _normalize_person_name,
    _clean_course_title,
    _extract_course_code,
    _extract_section_suffix,
    _split_section_and_course,
    _extract_faculty_and_course,
    _extract_time_and_campus,
    _extract_venue,
    _looks_like_room_fragment,
    _normalize_campus,
    _skip_known_columns,
    _clean_faculty_name,
    _clean_room_name,
    _merge_room_prefix_into_faculty,
)
from .parser_rows import collapse_whitespace as _collapse_whitespace

def _build_heuristic_item(serial_no: int, raw_text: str) -> Dict[str, object]:
    # Step 1: Skip the Department and Program columns (first 3 columns including Sr.No)
    # The Sr.No is already removed by _iter_row_blocks, so we just need to skip Department and Program
    text_after_skip = _skip_known_columns(raw_text)

    # Step 2: Extract from the RIGHT (Time, Campus)
    before_time, time_text, campus_text = _extract_time_and_campus(text_after_skip)

    # Step 3: Extract venue and work left
    venue_text, before_venue = _extract_venue(before_time)

    # Step 4: FIRST extract section from the remaining text, then extract faculty from what's left
    # This ensures we get the section right, which is critical for filtering
    semester_source, course_and_faculty, course_code = _split_section_and_course(before_venue)

    # Step 5: Extract faculty from the course_and_faculty text
    faculty_text, course_text = _extract_faculty_and_course(course_and_faculty)
    faculty_text = _clean_faculty_name(faculty_text)

    # If faculty extraction didn't work (returns empty course), fall back to full text as course
    if not faculty_text and not course_text:
        course_text = course_and_faculty

    # Heuristic: if faculty is empty but course_text ends with a likely faculty name
    # (two name tokens), move them to faculty. Also remove stray 'TBD' suffixes.
    if not faculty_text and course_text:
        ct_tokens = course_text.split()
        # Remove trailing TBD or similar placeholders
        if ct_tokens and ct_tokens[-1].upper() in {"TBD", "TBA"}:
            ct_tokens = ct_tokens[:-1]

        if len(ct_tokens) >= 2:
            last, second_last = ct_tokens[-1], ct_tokens[-2]
            if _is_name_token(last) and _is_name_token(second_last):
                faculty_text = _collapse_whitespace(" ".join([second_last, last]))
                course_text = _collapse_whitespace(" ".join(ct_tokens[:-2]))

    semester_display = _normalize_semester_display(semester_source)
    semester_key = _normalize_semester_key(semester_source)
    campus = _normalize_campus(campus_text)
    course_title = _clean_course_title(course_text, course_code)
    if course_code and course_text.upper().startswith(course_code.upper()):
        course_text = _collapse_whitespace(course_text)
    faculty_text, venue_text = _merge_room_prefix_into_faculty(faculty_text, venue_text)
    room_text = _clean_room_name(venue_text, faculty_text)

    raw_cells = [
        semester_display,
        course_text,
        faculty_text,
        room_text,
        time_text,
        campus,
    ]
    comma_separated = ", ".join(cell for cell in raw_cells if cell)

    return {
        "row_number": serial_no,
        "semester": semester_key,
        "semester_key": semester_key,
        "semester_display": semester_display,
        "semester_original": semester_source,
        "class_section": semester_display,
        "course": course_text,
        "course_title": course_title,
        "course_code": course_code,
        "faculty": faculty_text,
        "faculty_name": faculty_text,
        "room": room_text,
        "time": time_text,
        "campus": campus,
        "raw_line": raw_text,
        "raw_cells": raw_cells,
        "full_text": comma_separated,
    }

def _build_item(serial_no: int, raw_text: str, expand_sections: bool = False) -> Dict[str, object]:
    structured_item = _parse_structured_row(serial_no, raw_text)
    if structured_item is not None:
        if not expand_sections:
            return structured_item

        # Expand slash-separated section cells into multiple items.
        # Use the original raw section text when available so we don't lose
        # parts during earlier normalization (e.g. the parser may canonicalize
        # a combined "BSSS 1 / BS Psychology 1" to "BS Psychology 1" which
        # would prevent expansion). Prefer `semester_original` for detecting
        # slashes, falling back to the already-normalized `section` value.
        section_original = structured_item.get("semester_original") or ""
        section_val = section_original or structured_item.get("section") or structured_item.get("semester_display") or ""
        if "/" in section_original:
            parts = [p.strip() for p in section_original.split("/") if p.strip()]
            # Only expand when parts look like section labels (contain digits or 'OPEN')
            def looks_like_section(p: str) -> bool:
                up = p.upper()
                if "OPEN" in up:
                    return True
                if re.search(r"\d", p):
                    return True
                # Long descriptive parts are likely sections too
                if len(p) > 6 and not re.fullmatch(r"[A-Z]{2,6}$", p.strip()):
                    return True
                return False

            if all(not looks_like_section(p) for p in parts):
                # treat as program acronyms; don't expand
                return structured_item

            expanded = []
            for part in parts:
                # Clean the part by extracting a section-like suffix if present
                candidate = _extract_section_suffix(part) or part
                copy = dict(structured_item)
                display = _normalize_semester_display(candidate)
                key = _normalize_semester_key(candidate)
                copy.update({
                    "section": display,
                    "semester": key,
                    "semester_key": key,
                    "semester_display": display,
                    "semester_original": candidate,
                    "class_section": display,
                })
                expanded.append(copy)
            return expanded
        return structured_item

    # Heuristic path: build item and also expand slash-separated semester labels
    heuristic_item = _build_heuristic_item(serial_no, raw_text)
    if not expand_sections:
        return heuristic_item

    section_original = str(heuristic_item.get("semester_original") or "")
    if "/" in section_original:
        parts = [p.strip() for p in section_original.split("/") if p.strip()]

        def looks_like_section(p: str) -> bool:
            up = p.upper()
            if "OPEN" in up:
                return True
            if re.search(r"\d", p):
                return True
            if len(p) > 6 and not re.fullmatch(r"[A-Z]{2,6}$", p.strip()):
                return True
            return False

        if all(not looks_like_section(p) for p in parts):
            return heuristic_item

        expanded = []
        for part in parts:
            candidate = _extract_section_suffix(part) or part
            copy = dict(heuristic_item)
            display = _normalize_semester_display(candidate)
            key = _normalize_semester_key(candidate)
            copy.update({
                "section": display,
                "semester": key,
                "semester_key": key,
                "semester_display": display,
                "semester_original": candidate,
                "class_section": display,
            })
            expanded.append(copy)
        return expanded

    return heuristic_item

def _parse_structured_row(serial_no: int, raw_text: str) -> Optional[Dict[str, object]]:
    if "\t" not in raw_text:
        return None

    parts = [part.strip() for part in raw_text.split("\t")]
    parts = [part for part in parts if part]
    if len(parts) < 8:
        return None

    if len(parts) > 8:
        parts = parts[:7] + [" ".join(parts[7:])]

    if len(parts) != 8:
        return None

    department, program, section, course, faculty, room, time_text, campus_text = parts
    course_value = _collapse_whitespace(course)

    course_code = ""
    concatenated_match = re.match(r"^([A-Z]{2,6}\s*\d{2,4})([A-Z].+)$", course_value)
    if concatenated_match:
        course_code = _collapse_whitespace(concatenated_match.group(1))
        course_value = _collapse_whitespace(f"{course_code} {concatenated_match.group(2)}")
    else:
        _, _, course_code = _extract_course_code(course_value.split())

    course_title = _clean_course_title(course_value, course_code)
    semester_display = _normalize_semester_display(section)
    semester_key = _normalize_semester_key(section)
    faculty = _clean_faculty_name(faculty)
    faculty, room = _merge_room_prefix_into_faculty(faculty, room)
    room = _clean_room_name(room, faculty)
    time_text = _collapse_whitespace(time_text)
    campus = _normalize_campus(campus_text)

    raw_cells = [
        semester_display,
        course_title or course_value,
        faculty,
        room,
        time_text,
        campus,
    ]

    return {
        "row_number": serial_no,
        "department": _collapse_whitespace(department),
        "program": _collapse_whitespace(program),
        "section": semester_display,
        "semester": semester_key,
        "semester_key": semester_key,
        "semester_display": semester_display,
        "semester_original": section,
        "class_section": semester_display,
        "course": course_value,
        "course_title": course_title or course_value,
        "course_code": course_code,
        "faculty": faculty,
        "faculty_name": faculty,
        "room": room,
        "time": time_text,
        "campus": campus,
        "raw_line": raw_text,
        "raw_cells": raw_cells,
        "full_text": ", ".join(cell for cell in raw_cells if cell),
    }
