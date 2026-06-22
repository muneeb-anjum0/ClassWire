"""Normalization and field extraction for timetable rows."""

import re
from typing import List, Optional, Sequence, Tuple

from .parser_constants import *  # noqa: F403
from .parser_rows import TIME_RE, collapse_whitespace as _collapse_whitespace

def _normalize_semester_key(value: str) -> str:
    if not value:
        return ""
    normalized_display = _normalize_semester_display(value)
    if not normalized_display:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", normalized_display.upper())

def _normalize_semester_display(value: str) -> str:
    cleaned = _collapse_whitespace(value)
    if not cleaned:
        return ""

    upper = cleaned.upper()
    if "BS" in upper and "PSY" in upper:
        match = re.search(r"BS\s*(?:\(|\s)?(?:PSY|PSYCHOLOGY)(?:\))?\s*(OPEN|\d+[A-Z]?)", upper)
        if match:
            suffix = match.group(1).strip()
            suffix = "Open" if suffix == "OPEN" else suffix
            return f"BS Psychology {suffix}"

    slash_parts = [part.strip() for part in cleaned.split("/") if part.strip()]
    if len(slash_parts) >= 2:
        primary = slash_parts[0]

        looks_like_section_label = re.compile(r"^[A-Za-z&().\s-]*\d+(?:\s+[A-Z])?$")
        if looks_like_section_label.fullmatch(primary):
            return _collapse_whitespace(primary)

    return cleaned

def _semester_matches_filters(item_values: Sequence[str], allowed_semesters: Optional[List[str]]) -> bool:
    if not allowed_semesters:
        return True

    item_keys = {_normalize_semester_key(value) for value in item_values if value}
    item_keys.discard("")
    if not item_keys:
        return False

    for allowed in allowed_semesters:
        allowed_key = _normalize_semester_key(allowed)
        if not allowed_key:
            continue

        for item_key in item_keys:
            if item_key == allowed_key:
                return True
            if item_key.endswith(allowed_key) or allowed_key.endswith(item_key):
                return True

    return False

def _is_name_token(token: str) -> bool:
    cleaned = token.strip().strip(",;:")
    if not cleaned:
        return False

    if cleaned.lower() in NAME_CONNECTORS:
        return True

    upper = cleaned.upper()
    if upper in NON_PERSON_TOKENS:
        return False

    if upper in NAME_PREFIXES:
        return True

    if NAME_TOKEN_RE.fullmatch(cleaned):
        return True

    return False

def _is_section_token(token: str) -> bool:
    cleaned = token.strip().strip(",;:")
    if not cleaned:
        return False

    upper = cleaned.upper()
    if upper == "OPEN":
        return True
    if cleaned in {"-", "/", "&"}:
        return True

    # Exclude common English words that might look like section codes
    common_english = {"HANDS", "WORKSHOP", "COURSE", "DEVELOPMENT", "MANAGEMENT",
                      "COMMUNICATION", "TECHNIQUES", "ANALYSIS", "PRACTICE", "RESEARCH",
                      "ELECTIVES", "EXTERNAL", "INSTRUCTORS", "UNDERSTANDING"}
    if upper in common_english:
        return False

    if re.fullmatch(r"\([A-Z0-9&/]+\)", cleaned):
        return True
    if re.fullmatch(r"[A-Z]{1,8}(?:/[A-Z]{1,8})+", upper):
        return True
    if re.fullmatch(r"[A-Z]{1,8}&[A-Z]{1,8}", upper):
        return True
    if re.fullmatch(r"[A-Z]{1,8}\d{0,4}[A-Z]?", upper):
        return True
    if re.fullmatch(r"\d{1,4}[A-Z]?", upper):
        return True

    return False

def _normalize_person_name(text: str) -> str:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return ""

    tokens = [token for token in cleaned.split() if token not in {"-", "–", "—", "/", "&", "."}]
    return _collapse_whitespace(" ".join(tokens))

def _clean_course_title(text: str, course_code: str = "") -> str:
    cleaned = _collapse_whitespace(text).strip(" -/.,")
    if not cleaned:
        return ""

    if course_code and cleaned.upper().startswith(course_code.upper()):
        cleaned = _collapse_whitespace(cleaned[len(course_code):].strip(" -/.,"))

    cleaned = re.sub(r"^(?:Lab|LAB)\s*:\s*", "", cleaned)
    cleaned = re.sub(r"^(?:Lab|LAB)\s+", "", cleaned)

    # Some rows append an extra section marker after credits, e.g. "(3,0) B".
    cleaned = COURSE_CREDITS_SUFFIX_RE.sub("", cleaned)
    cleaned = COURSE_CREDITS_RE.sub("", cleaned)
    cleaned = cleaned.strip(" -/.,")
    return cleaned

def _extract_course_code(tokens: Sequence[str]) -> Tuple[int, int, str]:
    for index in range(len(tokens) - 1):
        first = tokens[index].strip().strip(",;:")
        second = tokens[index + 1].strip().strip(",;:")

        if COURSE_CODE_TOKEN_RE.fullmatch(first) and COURSE_CODE_VALUE_RE.fullmatch(second):
            return index, index + 2, f"{first} {second}"

    for index, token in enumerate(tokens):
        cleaned = token.strip().strip(",;:")
        if COURSE_CODE_SINGLE_RE.fullmatch(cleaned):
            return index, index + 1, cleaned

    return -1, -1, ""

def _extract_section_suffix(text: str) -> str:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return ""

    tokens = cleaned.split()
    best_match = ""

    for start_index in range(len(tokens)):
        candidate = _collapse_whitespace(" ".join(tokens[start_index:]))
        if not candidate:
            continue

        for pattern in SECTION_SUFFIX_PATTERNS:
            if pattern.fullmatch(candidate):
                if len(candidate) > len(best_match):
                    best_match = candidate
                break

    if not best_match:
        return ""

    # Trim leading pure program acronyms when the remaining text still
    # matches a valid section pattern (e.g., "PhDMS PhD-1" -> "PhD-1").
    match_tokens = best_match.split()
    while len(match_tokens) > 1:
        first = match_tokens[0].strip("-/,")
        if not re.fullmatch(r"[A-Za-z]{2,10}", first):
            break
        candidate_tail = _collapse_whitespace(" ".join(match_tokens[1:]))
        if any(pattern.fullmatch(candidate_tail) for pattern in SECTION_SUFFIX_PATTERNS):
            match_tokens = match_tokens[1:]
            continue
        break

    return _collapse_whitespace(" ".join(match_tokens))

def _split_section_and_course(text: str) -> Tuple[str, str, str]:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return "", "", ""

    def _should_preserve_slash_section(value: str) -> bool:
        parts = [part.strip() for part in value.split("/") if part.strip()]
        if len(parts) < 2:
          return False

        def looks_like_section(part: str) -> bool:
            upper = part.upper()
            return bool(re.search(r"\d", part) or "OPEN" in upper or re.fullmatch(r"[A-Z]{2,6}(?:\s*&\s*[A-Z]{2,6})?", part.strip()))

        return any(looks_like_section(part) for part in parts)

    tokens = cleaned.split()
    code_start, code_end, code_value = _extract_course_code(tokens)
    if code_start >= 0:
        section_source = _collapse_whitespace(" ".join(tokens[:code_start]).strip(" -/"))
        if _should_preserve_slash_section(section_source):
            section_text = section_source
        else:
            section_text = _extract_section_suffix(section_source) or section_source
        course_text = _collapse_whitespace(" ".join(tokens[code_start:]))
        return section_text, course_text, code_value

    section_end = 0
    seen_section_signal = False

    for index, token in enumerate(tokens):
        if _is_section_token(token):
            section_end = index + 1
            if re.search(r"\d", token) or token.upper() == "OPEN":
                seen_section_signal = True
            continue

        if seen_section_signal:
            break

        if token[:1].isupper() and token[1:].islower():
            break

        section_end = index + 1

    section_source = _collapse_whitespace(" ".join(tokens[:section_end]).strip(" -/"))
    if _should_preserve_slash_section(section_source):
        section_text = section_source
    else:
        section_text = _extract_section_suffix(section_source) or section_source
    course_text = _collapse_whitespace(" ".join(tokens[section_end:]))
    return section_text, course_text, ""

def _extract_faculty_and_course(text: str) -> Tuple[str, str]:
    """Extract faculty from course text using keyword hints and backward matching.

    Uses both explicit keywords (like "INSTRUCTOR", "EXTERNAL") and name pattern
    matching to identify faculty. Prioritizes rightmost faculty keywords to avoid
    including course content as part of the faculty name.
    """
    cleaned = _collapse_whitespace(text).strip(" -/")
    # Clean trailing dashes and hyphens from faculty names
    cleaned = re.sub(r'\s+[-–—]+\s*$', '', cleaned)
    if not cleaned:
        return "", ""

    tokens = cleaned.split()

    if len(tokens) < 2:
        return "", cleaned

    # Prefer a clean trailing human-name block over generic title words.
    faculty_suffix_start = len(tokens)
    saw_name_token = False
    while faculty_suffix_start > 0:
        token = tokens[faculty_suffix_start - 1].strip().strip(',;:')
        upper = token.upper()

        if not token or token in {'-', '–', '—', '/', '&', '.'}:
            faculty_suffix_start -= 1
            continue

        if upper in FACULTY_SUFFIX_STOPWORDS:
            break

        if upper in NAME_PREFIXES or token.lower() in NAME_CONNECTORS or NAME_TOKEN_RE.fullmatch(token):
            saw_name_token = True
            faculty_suffix_start -= 1
            continue

        break

    if saw_name_token:
        suffix_tokens = [token for token in tokens[faculty_suffix_start:] if token not in {'-', '–', '—', '/', '&', '.'}]
        prefix_offset = next((index for index, token in enumerate(suffix_tokens) if token.upper() in NAME_PREFIXES), -1)
        if prefix_offset >= 0:
            suffix_tokens = suffix_tokens[prefix_offset:]
            faculty_suffix_start += prefix_offset

        if len(suffix_tokens) >= 2 and not any(token.upper() in COURSE_KEYWORDS for token in suffix_tokens):
            preceding_token = tokens[faculty_suffix_start - 1] if faculty_suffix_start > 0 else ''
            if faculty_suffix_start == 0 or preceding_token.upper() in FACULTY_SUFFIX_STOPWORDS or not _is_name_token(preceding_token):
                faculty = _collapse_whitespace(' '.join(suffix_tokens))
                course = _collapse_whitespace(' '.join(tokens[:faculty_suffix_start]))
                if course and faculty:
                    return faculty, course

    # First, check for explicit prefixes like DR., PROF., etc.
    prefix_index = -1
    for index, token in enumerate(tokens):
        if token.upper() in NAME_PREFIXES:
            prefix_index = index

    if prefix_index >= 0:
        end_index = prefix_index + 1

        while end_index < len(tokens) and _is_name_token(tokens[end_index]):
            end_index += 1

        while prefix_index > 0 and tokens[prefix_index - 1].upper() in NAME_PREFIXES:
            prefix_index -= 1

        faculty_tokens = tokens[prefix_index:end_index]
        if len(faculty_tokens) >= 2:
            faculty = _collapse_whitespace(" ".join(faculty_tokens))
            course = _collapse_whitespace(" ".join(tokens[:prefix_index]))
            return faculty, course

    # Look for the RIGHTMOST faculty keyword within reasonable distance from the end
    rightmost_keyword_idx = -1
    for i in range(len(tokens) - 1, max(0, len(tokens) - 4), -1):
        if tokens[i].upper() in FACULTY_KEYWORDS:
            rightmost_keyword_idx = i
            break

    if rightmost_keyword_idx >= 0:
        # Found a faculty keyword, include from here to end
        # Backtrack to include preceding name tokens, but only 1-2 at most
        start_idx = rightmost_keyword_idx

        # Check if immediately preceding token is a name
        if rightmost_keyword_idx > 0 and _is_name_token(tokens[rightmost_keyword_idx - 1]):
            start_idx = rightmost_keyword_idx - 1

            # Check if there's another name token before that
            if rightmost_keyword_idx > 1 and _is_name_token(tokens[rightmost_keyword_idx - 2]):
                # Only include if the token before the second-last is not a name
                # (to avoid including entire course titles)
                if rightmost_keyword_idx < 3 or not _is_name_token(tokens[rightmost_keyword_idx - 3]):
                    start_idx = rightmost_keyword_idx - 2

        faculty = _collapse_whitespace(" ".join(tokens[start_idx:]))
        course = _collapse_whitespace(" ".join(tokens[:start_idx]))
        if course and faculty:
            return faculty, course

    # If no faculty keywords found, try the name token approach
    # Try to extract 2 name tokens from the end (typical faculty name)
    if len(tokens) >= 2:
        last_two_are_names = (_is_name_token(tokens[-1]) and _is_name_token(tokens[-2]))

        if last_two_are_names:
            # Check what comes before them
            if len(tokens) >= 3:
                token_before = tokens[-3]
                # Accept trailing two-name faculty when preceded by either
                # a non-name token or a known course keyword phrase token.
                if (((not _is_name_token(token_before) and token_before.upper() not in COURSE_KEYWORDS)
                    or token_before.upper() in COURSE_KEYWORDS) and
                    tokens[-1].upper() not in COURSE_KEYWORDS and
                    tokens[-2].upper() not in COURSE_KEYWORDS):
                    faculty = _collapse_whitespace(" ".join(tokens[-2:]))
                    course = _collapse_whitespace(" ".join(tokens[:-2]))
                    return faculty, course
            elif len(tokens) == 2:
                # Only 2 tokens, both are names - this is the whole thing
                if (tokens[-1].upper() not in COURSE_KEYWORDS and
                    tokens[-2].upper() not in COURSE_KEYWORDS):
                    faculty = _collapse_whitespace(" ".join(tokens[-2:]))
                    return faculty, ""

    # Try 3 name tokens if 2 didn't work
    if len(tokens) >= 3:
        last_three_are_names = (
            _is_name_token(tokens[-1]) and
            _is_name_token(tokens[-2]) and
            _is_name_token(tokens[-3])
        )

        if last_three_are_names:
            if len(tokens) >= 4:
                token_before = tokens[-4]
                # Only accept if preceded by non-name token and not a course keyword
                # Also check that the tokens aren't course keywords
                if (not _is_name_token(token_before) and
                    token_before.upper() not in COURSE_KEYWORDS and
                    tokens[-1].upper() not in COURSE_KEYWORDS and
                    tokens[-2].upper() not in COURSE_KEYWORDS and
                    tokens[-3].upper() not in COURSE_KEYWORDS):
                    faculty = _collapse_whitespace(" ".join(tokens[-3:]))
                    course = _collapse_whitespace(" ".join(tokens[:-3]))
                    return faculty, course

    suffix_start = len(tokens)
    while suffix_start > 0:
        token = tokens[suffix_start - 1]
        if token in {"-", "–", "—", "/", "&", "."} or _is_name_token(token):
            suffix_start -= 1
            continue
        break

    suffix_tokens = [token for token in tokens[suffix_start:] if token not in {"-", "–", "—", "/", "&", "."}]
    if suffix_tokens and len(suffix_tokens) <= 5:
        if len(suffix_tokens) > 1 or suffix_tokens[0].upper() not in COURSE_KEYWORDS:
            faculty = _collapse_whitespace(" ".join(suffix_tokens))
            course = _collapse_whitespace(" ".join(tokens[:suffix_start]))
            if course and faculty:
                return faculty, course
            if faculty and not course:
                return faculty, ""

    # No faculty pattern found
    return "", cleaned

def _extract_time_and_campus(text: str) -> Tuple[str, str, str]:
    cleaned = _collapse_whitespace(text)
    match = TIME_RE.search(cleaned)
    if not match:
        return cleaned, "", ""

    before_time = _collapse_whitespace(cleaned[: match.start()])
    time_text = _collapse_whitespace(match.group(0))
    campus_text = _collapse_whitespace(cleaned[match.end():])
    return before_time, time_text, campus_text

def _extract_venue(text: str) -> Tuple[str, str]:
    cleaned = _collapse_whitespace(text).strip(" -/")
    if not cleaned:
        return "", ""

    venue_patterns = [
        re.compile(r"(?:Cancelled|Canceled)\s+\d{2}-\d{2}-\d{4}", re.IGNORECASE),
        re.compile(r"(?:VF\s+)?ONLINE", re.IGNORECASE),
        re.compile(r"\b(?:NB|OB|HB|CB|AIC)-\d{2,4}\b", re.IGNORECASE),
        re.compile(r"\bTV\s+Studio\b", re.IGNORECASE),
        re.compile(r"\bMeeting\s+Room(?:\s+\d+)?\s+Admin\s+Block\b", re.IGNORECASE),
        re.compile(r"\bConference\s+Room\b", re.IGNORECASE),
        re.compile(r"\b(?:[A-Za-z]+\s+)?Lab(?:\s+\d+[A-Z]?)?\b", re.IGNORECASE),
        re.compile(r"\b(?:Media|Digital)\s+Lab\b", re.IGNORECASE),
        re.compile(r"\bFM-?Radio\b", re.IGNORECASE),
        re.compile(r"\bORIC\s+Hall\b", re.IGNORECASE),
        re.compile(r"\bAuditorium\b", re.IGNORECASE),
        re.compile(r"\bLibrary\b", re.IGNORECASE),
        re.compile(r"\b(?:Lab|Room)\s+\d+[A-Z]?\b", re.IGNORECASE),
        re.compile(r"\bHall\s+\d+\s*[A-Z]?\b", re.IGNORECASE),
        re.compile(r"\b\d{3}\b"),
    ]

    candidates = []
    for priority, pattern in enumerate(venue_patterns):
        for match in pattern.finditer(cleaned):
            candidates.append((match.start(), match.end(), priority, match.group(0)))

    if not candidates:
        return "", cleaned

    start, _, _, venue = sorted(candidates, key=lambda item: (item[1], -item[2], item[0]))[-1]
    before = _collapse_whitespace(cleaned[:start].rstrip(" -/"))
    return _collapse_whitespace(venue), before

def _looks_like_room_fragment(text: str) -> bool:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return False

    return bool(ROOM_HINT_RE.search(cleaned))

def _normalize_campus(text: str) -> str:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return ""

    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    cleaned = re.sub(r"(?<=\w)(Campus)$", r" \1", cleaned)

    upper = cleaned.upper()
    if "ONLINE" in upper or "VIRTUAL" in upper:
        return "Virtual Campus"
    if "HMB" in upper or "I-8 MARKAZ" in upper:
        return "SZABIST HMB I-8 Markaz Campus"
    if "H-8/4" in upper or "ISB" in upper or "UNIVERSITY" in upper:
        return "SZABIST University H-8/4 ISB Campus"

    return cleaned

def _skip_known_columns(text: str) -> str:
    """Skip the Department and Program columns at the start of the row.

    After Sr.No is removed, the text typically starts with:
    Department (e.g., "Management Sciences", "Social Sciences", "Media Studies")
    Program (e.g., "MBA", "MSDS", "MHRM", "BBA")

    This function identifies and skips these columns, returning everything
    from Section onwards (Section, Course, Faculty, Room, Time, Campus).
    """
    cleaned = _collapse_whitespace(text).strip()
    if not cleaned:
        return ""

    tokens = cleaned.split()
    if len(tokens) < 2:
        return cleaned

    # Known department names (common patterns)
    dept_patterns = [
        "Computer Sciences",
        "Robotics & AI",
        "Management Sciences",
        "Social Sciences",
        "Media Sciences",
        "Media Studies",
        "Law",
        "Engineering",
    ]

    # Check if the text starts with a known department name
    dept_skipped = 0
    text_upper = cleaned.upper()

    for dept in dept_patterns:
        if text_upper.startswith(dept.upper()):
            dept_skipped = len(dept)
            break

    if dept_skipped > 0:
        remaining = _collapse_whitespace(cleaned[dept_skipped:]).strip()
    else:
        # If no exact match, assume first 1-2 words are department
        remaining = _collapse_whitespace(" ".join(tokens[1:])).strip() if len(tokens) > 1 else ""

    if not remaining:
        return ""

    tokens = remaining.split()
    if len(tokens) < 1:
        return ""

    # Skip a compact program acronym only when the following token(s)
    # clearly indicate section content.
    first_token = tokens[0]
    second_token = tokens[1] if len(tokens) > 1 else ""
    third_token = tokens[2] if len(tokens) > 2 else ""
    second_or_third_has_section_signal = (
        "/" in second_token
        or bool(re.search(r"\d", second_token))
        or bool(re.search(r"\d", third_token))
    )
    if (
        re.fullmatch(r"^[A-Z]{2,6}$", first_token)
        and first_token not in {"AND", "FOR", "WITH", "OR", "OF"}
        and second_or_third_has_section_signal
    ):
        remaining = _collapse_whitespace(" ".join(tokens[1:])).strip() if len(tokens) > 1 else ""

    return remaining

def _clean_faculty_name(faculty: str) -> str:
    """Clean faculty names by removing trailing dashes, hyphens, and extra whitespace."""
    if not faculty:
        return ""
    cleaned = _normalize_person_name(faculty)
    cleaned = re.sub(r"\s*[-–—,.;]+\s*$", "", cleaned).strip()
    return cleaned

def _clean_room_name(room: str, faculty: str = "") -> str:
    cleaned = _collapse_whitespace(room).strip(" -/")
    faculty_cleaned = _collapse_whitespace(faculty).strip(" -/")
    if not cleaned:
        return ""

    if faculty_cleaned:
        room_casefold = cleaned.casefold()
        faculty_casefold = faculty_cleaned.casefold()
        if room_casefold == faculty_casefold:
            return ""

        prefix = faculty_cleaned + " "
        if room_casefold.startswith(prefix.casefold()):
            candidate = _collapse_whitespace(cleaned[len(faculty_cleaned):])
            if _looks_like_room_fragment(candidate):
                return candidate

    tokens = cleaned.split()
    prefix_count = 0
    for token in tokens:
        if token.upper() in NAME_PREFIXES or _is_name_token(token):
            prefix_count += 1
            continue
        break

    if prefix_count >= 2:
        candidate = _collapse_whitespace(" ".join(tokens[prefix_count:]))
        if _looks_like_room_fragment(candidate):
            return candidate

    if prefix_count == 1 and tokens and tokens[0].upper() in NAME_PREFIXES:
        candidate = _collapse_whitespace(" ".join(tokens[1:]))
        if _looks_like_room_fragment(candidate):
            return candidate

    return cleaned

def _merge_room_prefix_into_faculty(faculty: str, room: str) -> Tuple[str, str]:
    cleaned_faculty = _clean_faculty_name(faculty)
    cleaned_room = _collapse_whitespace(room).strip(" -/")
    if not cleaned_room:
        return cleaned_faculty, cleaned_room

    if cleaned_faculty:
        faculty_casefold = cleaned_faculty.casefold()
        room_casefold = cleaned_room.casefold()
        if room_casefold.startswith(faculty_casefold + " "):
            candidate_room = _collapse_whitespace(cleaned_room[len(cleaned_faculty):])
            if _looks_like_room_fragment(candidate_room):
                return cleaned_faculty, candidate_room

    room_tokens = cleaned_room.split()
    if len(room_tokens) < 2:
        return cleaned_faculty, cleaned_room

    prefix_tokens: List[str] = []
    index = 0
    while index < len(room_tokens):
        token = room_tokens[index]
        if token.upper() in ROOM_PREFIX_STOPWORDS:
            break
        if token.upper() in NAME_PREFIXES or _is_name_token(token):
            prefix_tokens.append(token)
            index += 1
            continue
        break

    if not prefix_tokens:
        return cleaned_faculty, cleaned_room

    candidate_room = _collapse_whitespace(" ".join(room_tokens[index:]))
    if not _looks_like_room_fragment(candidate_room):
        return cleaned_faculty, cleaned_room

    if cleaned_faculty:
        merged_faculty = _collapse_whitespace(f"{cleaned_faculty} {' '.join(prefix_tokens)}")
    else:
        merged_faculty = _collapse_whitespace(" ".join(prefix_tokens))

    return merged_faculty, candidate_room
