"""Natural-language timetable query interpretation."""

from __future__ import annotations

import os
import re
from collections import Counter
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PARSER_VERSION = 10
DAY_START = 8 * 60
DAY_END = 21 * 60 + 30
NOISE = {
    "schedule", "timetable", "time", "table", "class", "classes", "course", "courses",
    "when", "where", "what", "does", "have", "has", "their", "there", "entire", "week",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "free", "office",
    "next", "this", "following", "today", "tomorrow", "yesterday", "all", "every", "my",
    "is", "are", "was", "were", "be", "in", "on", "at", "for", "show", "find", "give", "tell",
    "me", "the", "a", "an", "of", "and", "or", "to", "from", "with", "without", "please",
    "theory", "lab", "labs", "laboratory", "laboratories", "fyp", "final", "year", "project", "sir", "madam",
    "maam", "mam",
    "credit", "credits", "hour", "hours", "hr", "hrs", "ch",
}
HONORIFICS = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "professor", "engr", "eng",
    "sir", "madam", "maam", "mam",
}
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
}
NOISE.update(NUMBER_WORDS)


@lru_cache(maxsize=16384)
def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize(value: object) -> str:
    return _normalize_text(str(value or ""))


@lru_cache(maxsize=16384)
def _word_tuple(value: str) -> Tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.lower()))


def words(value: object) -> List[str]:
    return list(_word_tuple(str(value or "")))


def parse_days(query: str, reference_date: date | None = None) -> List[str]:
    lowered = query.lower()
    if "entire week" in lowered or "all week" in lowered or "whole week" in lowered:
        return DAYS
    selected = [day for day in DAYS if day.lower() in lowered]
    if not selected:
        relative_offset = 0 if re.search(r"\btoday\b", lowered) else (
            1 if re.search(r"\btomorrow\b", lowered) else (
                -1 if re.search(r"\byesterday\b", lowered) else None
            )
        )
        if relative_offset is not None:
            if reference_date is None:
                timezone_name = os.getenv("TZ", "Asia/Karachi")
                try:
                    reference_date = datetime.now(ZoneInfo(timezone_name)).date()
                except Exception:
                    reference_date = datetime.now(ZoneInfo("Asia/Karachi")).date()
            return [(reference_date + timedelta(days=relative_offset)).strftime("%A")]
    if not selected:
        query_tokens = words(query)
        selected = [
            day for day in DAYS
            if any(SequenceMatcher(None, token, day.lower()).ratio() >= 0.78 for token in query_tokens)
        ]
    return selected or DAYS


@lru_cache(maxsize=65536)
def _similar(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _item_section(item: Dict) -> str:
    return str(item.get("semester_display") or item.get("semester") or item.get("section") or "")


def _credit_components(item: Dict) -> Tuple[float, float] | None:
    text = " ".join(str(item.get(field) or "") for field in ("course", "course_title", "full_text"))
    match = re.search(r"\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)", text)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _class_type(item: Dict) -> str | None:
    credits = _credit_components(item)
    if not credits:
        return None
    theory, practical = credits
    if theory > 0 and practical == 0:
        return "theory"
    if theory == 0 and practical == 1:
        return "lab"
    if theory == 0 and practical == 3:
        return "fyp"
    return None


def _credit_hours(item: Dict) -> float | None:
    """Return the total credits represented by a parsed timetable row."""
    for field in ("credit_hours", "credits", "credit"):
        value = item.get(field)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        if value is not None:
            match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", str(value))
            if match:
                return float(match.group(1))

    components = _credit_components(item)
    return sum(components) if components else None


def _requested_credit_hours(query: str) -> List[str]:
    """Extract credit-hour constraints from natural language without reading course codes as credits."""
    lowered = query.lower()
    number = r"(?:\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine)"
    suffix = r"(?:credit(?:\s*|-)*(?:hours?|hrs?)|credits?|cr(?:edit)?\.?\s*(?:/\s*)?(?:hours?|hrs?)|crhrs?|ch)"
    prefix = r"(?:credit(?:\s*|-)*(?:hours?|hrs?)|credits?|ch)"
    values = re.findall(rf"\b({number})\s*(?:-|\s)*{suffix}\b", lowered)
    values.extend(re.findall(rf"\b{prefix}\s*(?:of|=|:)?\s*({number})\b", lowered))
    for first, second in re.findall(
        rf"\b({number})\s*(?:,|/|&|and|or|\s)\s*({number})\s*(?:-|\s)*{suffix}\b",
        lowered,
    ):
        values.extend((first, second))

    parsed: List[str] = []
    for value in values:
        numeric = float(NUMBER_WORDS[value]) if value in NUMBER_WORDS else float(value)
        if 0 <= numeric <= 12:
            label = str(int(numeric)) if numeric.is_integer() else str(numeric)
            if label not in parsed:
                parsed.append(label)
    return parsed


def _is_broad_schedule_request(query: str) -> bool:
    """Recognize requests whose intended constraint is only their selected day scope."""
    lowered = query.lower()
    if re.search(r"\b(?:all|every|my)\s+(?:scheduled\s+)?(?:classes|courses)\b", lowered):
        return True
    if re.search(r"\b(?:full|whole|entire|my)\s+(?:class\s+)?(?:schedule|timetable)\b", lowered):
        return True
    if re.search(r"\b(?:show|list|give)\s+(?:me\s+)?(?:the\s+)?(?:schedule|timetable)\b", lowered):
        return True
    query_words = words(query)
    has_day_scope = any(
        token == day.lower() or _similar(token, day.lower()) >= 0.78
        for token in query_words
        for day in DAYS
    ) or any(token in {"today", "tomorrow", "yesterday"} for token in query_words)
    if has_day_scope and re.search(r"\b(?:classes|courses|schedule|timetable)\b", lowered):
        return True
    return bool(re.search(r"\bwhat\s+classes\s+(?:do\s+i\s+have|are\s+scheduled)\b", lowered))


def _format_credit_hours(values: List[str]) -> str:
    if not values:
        return ""
    labels = [f"{value}-credit-hour" for value in values]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" or {labels[-1]}"


def _requested_class_types(query: str, named_courses: List[str] | None = None) -> List[str]:
    lowered = query.lower()
    requested = []
    if "theory" in lowered or re.search(r"\(\s*[23]\s*,\s*0\s*\)", lowered):
        requested.append("theory")
    if re.search(r"\b(?:labs?|laborator(?:y|ies))\b", lowered) or re.search(r"\(\s*0\s*,\s*1\s*\)", lowered):
        requested.append("lab")
    if "fyp" in lowered or "final year project" in lowered or re.search(r"\(\s*0\s*,\s*3\s*\)", lowered):
        requested.append("fyp")
    # Words such as "Lab" and "Theory" are often part of the actual course
    # title rather than a requested class-type filter. Once a course entity is
    # identified, its own words must not accidentally filter that course out.
    for course in named_courses or []:
        course_words = set(words(course))
        if "lab" in course_words or "laboratory" in course_words:
            if not re.search(r"\(\s*0\s*,\s*1\s*\)", lowered):
                requested = [kind for kind in requested if kind != "lab"]
        if "theory" in course_words:
            if not re.search(r"\(\s*[23]\s*,\s*0\s*\)", lowered):
                requested = [kind for kind in requested if kind != "theory"]
        if "fyp" in course_words or {"final", "year", "project"}.issubset(course_words):
            if not re.search(r"\(\s*0\s*,\s*3\s*\)", lowered):
                requested = [kind for kind in requested if kind != "fyp"]
    return requested


def _name_words(value: object) -> List[str]:
    return [word for word in words(value) if word not in HONORIFICS]


def _canonicalize_faculty(items: List[Dict]) -> List[Dict]:
    # Unify formatting-only variants ("Dr Ghulam Mustafa" vs
    # "Dr. Ghulam Mustafa") while preserving genuinely different names. A
    # short honorific name such as "Mr. Qasim" is not proof that the person is
    # the same as "Muhammad Qasim", so those identities remain separate.
    label_counts: Dict[str, Counter[str]] = {}
    for item in items:
        label = str(item.get("faculty") or "").strip()
        identity = normalize(label)
        if identity:
            label_counts.setdefault(identity, Counter())[label] += 1

    def label_quality(label: str) -> Tuple[int, int, int, str]:
        tokens = words(label)
        normal_case = int(not label.isupper() and not label.islower())
        punctuated_honorific = int(bool(re.match(r"^(?:Mr|Mrs|Ms|Dr|Prof)\.", label, re.I)))
        title_case_words = sum(token[:1].isupper() for token in re.findall(r"[A-Za-z]+", label))
        return normal_case, punctuated_honorific, title_case_words, label

    preferred_labels = {
        identity: max(counts, key=lambda label: (counts[label], *label_quality(label)))
        for identity, counts in label_counts.items()
    }

    canonical = []
    seen = set()
    for source in items:
        original_label = str(source.get("faculty") or "").strip()
        preferred_label = preferred_labels.get(normalize(original_label), original_label)
        item = source if preferred_label == original_label else {**source, "faculty": preferred_label}
        identity = (
            item.get("schedule_day"), normalize(_item_section(item)), normalize(item.get("course_code")),
            normalize(item.get("course_title") or item.get("course")), normalize(item.get("faculty")),
            normalize(item.get("room")), normalize(item.get("time")),
        )
        if identity not in seen:
            canonical.append(item)
            seen.add(identity)
    return canonical


def find_entities(query: str, items: List[Dict]) -> Dict[str, List[str]]:
    compact_query = normalize(query)
    query_words = set(words(query))
    sections = sorted({_item_section(item) for item in items if _item_section(item)})
    faculty = sorted({str(item.get("faculty")) for item in items if item.get("faculty")})
    courses = sorted({str(item.get("course_title") or item.get("course")) for item in items if item.get("course_title") or item.get("course")})
    codes = sorted({str(item.get("course_code")) for item in items if item.get("course_code")})

    matched_sections = []
    for value in sections:
        normalized_section = normalize(value)
        if len(normalized_section) < 2 or not re.search(r"[a-z]", normalized_section):
            continue
        # A short section such as "BS" must match a complete token. Raw
        # substring matching otherwise treats the end of "labs" as section
        # BS and filters every legitimate lab row out of the result.
        section_is_named = (
            normalized_section in query_words
            if len(normalized_section) <= 2
            else normalized_section in compact_query
        )
        if section_is_named:
            matched_sections.append(value)
    # Prefer the most specific section when one label contains another
    # (for example "BSSS 2" and "BSSS 2 - Section A").
    matched_sections = [
        value for value in matched_sections
        if not any(
            normalize(value) != normalize(other) and normalize(value) in normalize(other)
            for other in matched_sections
        )
    ]
    explicitly_named_faculty = [value for value in faculty if normalize(value) and normalize(value) in compact_query]
    explicitly_named_faculty = [
        value for value in explicitly_named_faculty
        if not any(
            normalize(value) != normalize(other) and normalize(value) in normalize(other)
            for other in explicitly_named_faculty
        )
    ]
    # A user may combine an exact faculty name with a recognizable shortened
    # name (for example, "Zainab Iftikhar and Hamza Imran"). Previously the
    # exact match triggered the fast path and silently discarded the partial
    # name before fuzzy resolution could run. Retain unambiguous, consecutive
    # two-word name fragments alongside exact matches.
    meaningful_query_sequence = [
        word for word in words(query)
        if len(word) >= 3
        and word not in NOISE
        and word not in HONORIFICS
        and not any(_similar(word, day.lower()) >= 0.78 for day in DAYS)
    ]

    def partial_name_position(value: str) -> int | None:
        name_sequence = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
        if len(name_sequence) < 3:
            return None
        for fragment_length in range(len(name_sequence) - 1, 1, -1):
            for name_index in range(len(name_sequence) - fragment_length + 1):
                fragment = name_sequence[name_index:name_index + fragment_length]
                for query_index in range(len(meaningful_query_sequence) - fragment_length + 1):
                    if meaningful_query_sequence[query_index:query_index + fragment_length] == fragment:
                        return query_index
        return None

    partially_named_faculty = []
    for value in faculty:
        if value in explicitly_named_faculty:
            continue
        position = partial_name_position(value)
        if position is None:
            continue
        # If the fragment already names a shorter exact identity, do not also
        # broaden it to a longer faculty label with the same prefix/suffix.
        if any(normalize(exact) in normalize(value) for exact in explicitly_named_faculty):
            continue
        partially_named_faculty.append((position, value))

    named_faculty = list(dict.fromkeys(
        explicitly_named_faculty + [value for _, value in sorted(partially_named_faculty)]
    ))
    query_word_positions = {word: index for index, word in enumerate(meaningful_query_sequence)}
    named_faculty.sort(key=lambda value: min(
        (query_word_positions[word] for word in _name_words(value) if word in query_word_positions),
        default=len(meaningful_query_sequence),
    ))
    matched_codes = [value for value in codes if normalize(value) and normalize(value) in compact_query]
    explicitly_named_courses = [
        value for value in courses
        if len(normalize(value)) >= 3 and normalize(value) in compact_query
    ]
    explicitly_named_courses = [
        value for value in explicitly_named_courses
        if not any(
            normalize(value) != normalize(other) and normalize(value) in normalize(other)
            for other in explicitly_named_courses
        )
    ]

    # Exact entities are overwhelmingly the common path and always outrank
    # fuzzy candidates. Return before running thousands of SequenceMatcher
    # comparisons across a university-wide timetable.
    explicit_values = [
        (kind, value)
        for kind, values in (
            ("section", matched_sections),
            ("faculty", named_faculty),
            ("course", explicitly_named_courses),
            ("code", matched_codes),
        )
        for value in values
    ]
    if explicit_values:
        dominated = {
            (kind, value)
            for kind, value in explicit_values
            if any(
                kind != other_kind
                and normalize(value) != normalize(other)
                and normalize(value) in normalize(other)
                for other_kind, other in explicit_values
            )
        }
        return {
            "sections": [value for value in matched_sections if ("section", value) not in dominated],
            "faculty": [value for value in named_faculty if ("faculty", value) not in dominated],
            "courses": [value for value in explicitly_named_courses if ("course", value) not in dominated],
            "codes": [value for value in matched_codes if ("code", value) not in dominated],
            "class_types": _requested_class_types(query, explicitly_named_courses),
            "credit_hours": _requested_credit_hours(query),
        }

    faculty_scores = []
    meaningful_query_words = set(meaningful_query_sequence)
    meaningful_query_compact = "".join(meaningful_query_sequence)
    faculty_intent = bool(re.search(
        r"\b(?:free|available|faculty|teacher|professor|sir|madam|maam|mam|miss|ms|mr|dr|class|classes)\b|\bwhen\s+(?:does|is)\b",
        query.lower(),
    ))
    for value in faculty:
        name_words = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
        overlap = sum(1 for word in name_words if word in meaningful_query_words)
        if not name_words:
            continue
        if normalize(value) in compact_query:
            score = 100 + len(name_words)
        else:
            similarities = [
                max((_similar(name_word, query_word) for query_word in meaningful_query_words), default=0)
                for name_word in name_words
            ]
            covered = [similarity for similarity in similarities if similarity >= 0.72]
            if len(meaningful_query_words) == 1:
                score = max(covered, default=0)
            else:
                score = (10 * len(covered) / len(name_words)) + (sum(covered) / len(name_words)) if covered else 0
            # Users commonly omit spaces while typing a full name. Compare the
            # complete meaningful phrase as well as individual tokens, but do
            # not apply this to short surname-only searches.
            compact_name = "".join(name_words)
            if meaningful_query_compact and len(meaningful_query_compact) >= max(6, int(len(compact_name) * 0.7)):
                compact_similarity = _similar(compact_name, meaningful_query_compact)
                if compact_similarity >= 0.78:
                    score = max(score, compact_similarity * 20)
        if score > 0:
            faculty_scores.append((score, overlap, value))
    if not faculty_scores:
        for value in faculty:
            name_words = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
            similarity = max(
                (_similar(query_word, name_word) for query_word in meaningful_query_words for name_word in name_words),
                default=0,
            )
            if similarity >= 0.78:
                faculty_scores.append((similarity, 0, value))
    best_faculty_score = max((score for score, _, _ in faculty_scores), default=0)
    matched_faculty = [value for score, _, value in faculty_scores if score == best_faculty_score]
    if not faculty_intent and len(meaningful_query_words) > 1:
        matched_faculty = []

    course_scores = []
    for value in courses:
        title_words = [word for word in words(value) if len(word) >= 4 and word not in NOISE]
        compact_title = normalize(value)
        overlap = sum(1 for word in title_words if word in meaningful_query_words)
        fuzzy_threshold = 0.90 if len(meaningful_query_words) == 1 else 0.82
        fuzzy_overlap = sum(
            1 for title_word in title_words
            if title_word not in meaningful_query_words
            and any(_similar(query_word, title_word) >= fuzzy_threshold for query_word in meaningful_query_words)
        )
        if len(compact_title) >= 3 and compact_title in compact_query:
            score = 100 + len(title_words)
        elif overlap or fuzzy_overlap:
            score = (overlap + fuzzy_overlap) / max(len(title_words), 1)
        else:
            score = 0
        if meaningful_query_compact and len(meaningful_query_compact) >= max(8, int(len(compact_title) * 0.7)):
            compact_similarity = _similar(compact_title, meaningful_query_compact)
            if compact_similarity >= 0.78:
                score = max(score, compact_similarity * 20)
        if score:
            course_scores.append((score, value))
    if len(meaningful_query_words) <= 1:
        matched_courses = [value for _, value in course_scores]
    else:
        best_course_score = max((score for score, _ in course_scores), default=0)
        matched_courses = [value for score, value in course_scores if score == best_course_score]

    return {
        "sections": matched_sections,
        "faculty": matched_faculty,
        "courses": matched_courses,
        "codes": matched_codes,
        "class_types": _requested_class_types(query, matched_courses),
        "credit_hours": _requested_credit_hours(query),
    }


def _matches(item: Dict, entities: Dict[str, List[str]]) -> bool:
    checks = []
    if entities["sections"]:
        checks.append(any(normalize(value) == normalize(_item_section(item)) for value in entities["sections"]))
    if entities["faculty"]:
        checks.append(any(normalize(value) == normalize(item.get("faculty")) for value in entities["faculty"]))
    if entities["courses"]:
        checks.append(any(normalize(value) == normalize(item.get("course_title") or item.get("course")) for value in entities["courses"]))
    if entities["codes"]:
        checks.append(any(normalize(value) == normalize(item.get("course_code")) for value in entities["codes"]))
    if entities["class_types"]:
        checks.append(_class_type(item) in entities["class_types"])
    if entities["credit_hours"]:
        requested = {float(value) for value in entities["credit_hours"]}
        checks.append(_credit_hours(item) in requested)
    return all(checks) if checks else False


def _uses_additive_course_scope(query: str, entities: Dict[str, List[str]]) -> bool:
    """Detect requests for a section timetable plus courses from elsewhere."""
    if not entities["sections"] or not (entities["courses"] or entities["codes"]):
        return False
    lowered = query.lower()
    additive_language = (
        r"\bas\s+well\b",
        r"\bin\s+addition\b",
        r"\balong\s+with\b",
        r"\bplus\b",
        r"\balso\b",
        r"\bbut\b.{0,80}\b(?:want|take|add|include)\b",
        r"\b(?:want|would\s+like)\s+to\s+(?:take|add|include)\b",
        r"\bi(?:\s+am|'m|m)\s+(?:from|in)\b",
    )
    return any(re.search(pattern, lowered) for pattern in additive_language)


def _matches_additive_course_scope(item: Dict, entities: Dict[str, List[str]]) -> bool:
    """Match a base section OR an explicitly requested additional course."""
    section_match = any(
        normalize(value) == normalize(_item_section(item))
        for value in entities["sections"]
    )
    course_match = any(
        normalize(value) == normalize(item.get("course_title") or item.get("course"))
        for value in entities["courses"]
    )
    code_match = any(
        normalize(value) == normalize(item.get("course_code"))
        for value in entities["codes"]
    )
    if not (section_match or course_match or code_match):
        return False

    if entities["faculty"] and not any(
        normalize(value) == normalize(item.get("faculty"))
        for value in entities["faculty"]
    ):
        return False
    if entities["class_types"] and _class_type(item) not in entities["class_types"]:
        return False
    if entities["credit_hours"]:
        requested = {float(value) for value in entities["credit_hours"]}
        if _credit_hours(item) not in requested:
            return False
    return True


def _time_minutes(value: str) -> Tuple[int, int] | None:
    matches = re.findall(r"(\d{1,2}):(\d{2})\s*(AM|PM)", value or "", re.I)
    if len(matches) < 2:
        return None
    values = []
    for hour, minute, period in matches[:2]:
        number = int(hour) % 12 + (12 * (period.upper() == "PM"))
        values.append(number * 60 + int(minute))
    start, end = values
    if end <= start:
        return None
    start = max(start, DAY_START)
    end = min(end, DAY_END)
    return (start, end) if start < end else None


def _format_minutes(value: int) -> str:
    hour, minute = divmod(value, 60)
    suffix = "PM" if hour >= 12 else "AM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _schedule_conflicts(items: List[Dict]) -> List[Dict]:
    """Return deterministic overlapping class pairs for custom schedules."""
    conflicts: List[Dict] = []
    by_day: Dict[str, List[tuple[Dict, Tuple[int, int]]]] = {}
    for item in items:
        interval = _time_minutes(str(item.get("time") or ""))
        day = str(item.get("schedule_day") or "")
        if interval and day:
            by_day.setdefault(day, []).append((item, interval))
    for day, entries in by_day.items():
        entries.sort(key=lambda pair: pair[1])
        for index, (left, left_interval) in enumerate(entries):
            for right, right_interval in entries[index + 1:]:
                if right_interval[0] >= left_interval[1]:
                    break
                overlap_start = max(left_interval[0], right_interval[0])
                overlap_end = min(left_interval[1], right_interval[1])
                if overlap_start >= overlap_end:
                    continue
                conflicts.append({
                    "day": day,
                    "overlap": f"{_format_minutes(overlap_start)} – {_format_minutes(overlap_end)}",
                    "left": {
                        "course": left.get("course_title") or left.get("course"),
                        "section": _item_section(left),
                        "time": left.get("time"),
                    },
                    "right": {
                        "course": right.get("course_title") or right.get("course"),
                        "section": _item_section(right),
                        "time": right.get("time"),
                    },
                })
    return conflicts


def faculty_free_slots(items: List[Dict], days: List[str]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for day in days:
        intervals = sorted(filter(None, (_time_minutes(str(item.get("time") or "")) for item in items if item.get("schedule_day") == day)))
        merged: List[List[int]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        if not merged:
            result[day] = [f"{_format_minutes(DAY_START)} – {_format_minutes(DAY_END)}"]
            continue
        cursor = DAY_START
        slots = []
        for start, end in merged:
            if start > cursor:
                slots.append(f"{_format_minutes(cursor)} – {_format_minutes(start)}")
            cursor = max(cursor, end)
        if cursor < DAY_END:
            slots.append(f"{_format_minutes(cursor)} – {_format_minutes(DAY_END)}")
        result[day] = slots
    return result


def search_timetable(query: str, items: List[Dict], reference_date: date | None = None) -> Dict:
    items = _canonicalize_faculty(items)
    days = parse_days(query, reference_date)
    entities = find_entities(query, items)
    additive_course_scope = _uses_additive_course_scope(query, entities)
    matches_scope = (
        (lambda item: _matches_additive_course_scope(item, entities))
        if additive_course_scope
        else (lambda item: _matches(item, entities))
    )
    wants_free = any(phrase in query.lower() for phrase in ("free", "available", "office hour", "no class"))
    if wants_free and entities["faculty"]:
        # Availability questions are faculty-first. Incidental words such as
        # "and" between requested days must never introduce a course filter
        # that removes the teacher's schedule.
        all_entity_matches = [
            item for item in items
            if any(normalize(faculty) == normalize(item.get("faculty")) for faculty in entities["faculty"])
        ]
    elif _is_broad_schedule_request(query) and not any(entities.values()):
        all_entity_matches = list(items)
    else:
        all_entity_matches = [item for item in items if matches_scope(item)]
    day_items = [item for item in items if item.get("schedule_day") in days]
    # Availability answers and their supporting timetable share the requested
    # day scope. Faculty-only matching above prevents incidental query words
    # from removing otherwise valid rows.
    if wants_free and entities["faculty"]:
        matched = [item for item in all_entity_matches if item.get("schedule_day") in days]
    elif _is_broad_schedule_request(query) and not any(entities.values()):
        matched = day_items
    else:
        matched = [item for item in day_items if matches_scope(item)]
    day_rank = {day: index for index, day in enumerate(DAYS)}
    matched.sort(key=lambda item: (
        day_rank.get(str(item.get("schedule_day")), len(DAYS)),
        (_time_minutes(str(item.get("time") or "")) or (DAY_END, DAY_END))[0],
        normalize(_item_section(item)),
        normalize(item.get("course_title") or item.get("course")),
    ))
    faculty_availability = []
    if wants_free and entities["faculty"]:
        for faculty in entities["faculty"]:
            faculty_items = [item for item in all_entity_matches if normalize(item.get("faculty")) == normalize(faculty)]
            faculty_availability.append({
                "faculty": faculty,
                "slots": faculty_free_slots(faculty_items, days),
            })
    free_slots = faculty_availability[0]["slots"] if len(faculty_availability) == 1 else {}
    labels = entities["sections"] + entities["faculty"] + entities["courses"] + entities["codes"]
    subject = ", ".join(dict.fromkeys(labels)) if labels else "your query"
    day_suffix = f" on {days[0]}" if len(days) == 1 else ""
    if wants_free and entities["faculty"]:
        answer = "Faculty availability"
    else:
        class_type = entities["class_types"][0] if len(entities["class_types"]) == 1 else ""
        credit_label = _format_credit_hours(entities["credit_hours"])
        kind = f"{class_type} class" if class_type else "class"
        if credit_label and matched:
            course_keys = {
                normalize(item.get("course_code") or item.get("course_title") or item.get("course"))
                for item in matched
                if item.get("course_code") or item.get("course_title") or item.get("course")
            }
            course_count = len(course_keys)
            qualifier = f" {class_type}" if class_type else ""
            type_counts = Counter(_class_type(item) or "other" for item in matched)
            type_parts = []
            for class_kind, type_label in (("theory", "theory"), ("lab", "lab"), ("fyp", "FYP"), ("other", "other")):
                count = type_counts.get(class_kind, 0)
                if count:
                    type_parts.append(f"{count} {type_label} {'class' if count == 1 else 'classes'}")
            breakdown = f" — {', '.join(type_parts)}" if len(type_parts) > 1 else ""
            answer = (
                f"Found {len(matched)} scheduled {'class' if len(matched) == 1 else 'classes'} "
                f"across {course_count} {credit_label}{qualifier} "
                f"{'course' if course_count == 1 else 'courses'}{breakdown}."
            )
        elif credit_label:
            qualifier = f" {class_type}" if class_type else ""
            answer = f"No scheduled classes found for {credit_label}{qualifier} courses."
        elif matched and _is_broad_schedule_request(query) and not any(entities.values()):
            scope = days[0] if len(days) == 1 else "the selected week"
            answer = f"Found {len(matched)} scheduled {'class' if len(matched) == 1 else 'classes'} for {scope}."
        elif matched and additive_course_scope:
            base = ", ".join(dict.fromkeys(entities["sections"]))
            additions = ", ".join(dict.fromkeys(entities["courses"] + entities["codes"]))
            answer = (
                f"Found {len(matched)} {'class' if len(matched) == 1 else 'classes'} "
                f"for {base} plus {additions}{day_suffix}."
            )
        elif matched:
            answer = f"Found {len(matched)} {kind if len(matched) == 1 else kind + 'es'} for {subject}{day_suffix}."
        elif not any(entities.values()) and not _is_broad_schedule_request(query):
            answer = (
                "I couldn't identify a section, faculty member, course, class type, "
                "credit-hour value, or schedule scope in that question."
            )
        else:
            answer = f"No {kind + 'es'} found for {subject}{day_suffix}."
    recognized = bool(any(entities.values()) or _is_broad_schedule_request(query))
    conflicts = _schedule_conflicts(matched)
    return {
        "parser_version": PARSER_VERSION,
        "items": matched,
        "days": days,
        "entities": entities,
        "free_slots": free_slots,
        "faculty_availability": faculty_availability,
        "answer": answer,
        "intent": "free_time" if wants_free else "schedule",
        "match_mode": "union" if additive_course_scope else "intersection",
        "query_plan": {
            "intent": "free_time" if wants_free else "schedule",
            "day_scope": days,
            "combination": "union" if additive_course_scope else "intersection",
            "filters": entities,
        },
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "recognized": recognized,
    }
