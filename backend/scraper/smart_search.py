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
PARSER_VERSION = 16
DAY_ALIASES = {
    "Monday": ("mon", "mond"),
    "Tuesday": ("tue", "tues", "tuesd"),
    "Wednesday": ("wed", "weds", "wednes"),
    "Thursday": ("thu", "thur", "thurs"),
    "Friday": ("fri",),
    "Saturday": ("sat",),
}
DAY_START = 8 * 60
DAY_END = 21 * 60 + 30
NOISE = {
    "schedule", "timetable", "time", "table", "class", "classes", "course", "courses",
    "when", "where", "what", "does", "have", "has", "their", "there", "entire", "week",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "free", "available",
    "availability", "open", "slot", "slots", "meet", "meeting", "office",
    "next", "this", "following", "today", "tomorrow", "yesterday", "all", "every", "my",
    "is", "are", "was", "were", "be", "in", "on", "at", "for", "show", "find", "give", "tell",
    "me", "the", "a", "an", "of", "and", "or", "to", "from", "with", "without", "please",
    "take", "takes", "taking", "took", "want", "wants", "wanted", "add", "adds", "adding",
    "include", "includes", "including", "enroll", "enrolled", "enrolling", "belong", "belongs",
    "keep", "use", "using", "skip", "remove", "attend", "attends", "attending", "register",
    "registered", "registering", "choose", "chooses", "choosing", "select", "selects", "selecting",
    "faculty", "teacher", "professor", "instructor", "lecturer", "teach", "teaches", "teaching", "taught",
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
    query_tokens = words(query)
    selected = [
        day for day in DAYS
        if day.lower() in query_tokens
        or any(alias in query_tokens for alias in DAY_ALIASES[day])
    ]
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


def _wants_faculty_availability(query: str) -> bool:
    """Recognize common ways students ask for a faculty member's free time."""
    return bool(re.search(
        r"\b(?:free|available|availability|free\s+(?:slot|slots|period|periods|time)|"
        r"open\s+(?:slot|slots|period|periods|time)|gaps?|office\s+hours?|"
        r"no\s+class|not\s+(?:have|having|teaching)\s+(?:a\s+)?class|"
        r"(?:when|what\s+time|could|can)\s+(?:i|we)\s+meet|time\s+to\s+meet)\b",
        query.lower(),
    ))


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
    # Resolve compact section typos per token. This runs independently of
    # exact course/faculty matches, so one correct entity can no longer hide a
    # misspelled section elsewhere in the same sentence. Ambiguous shorthand
    # is deliberately left unresolved instead of guessing.
    unmatched_section_tokens = [
        token for token in words(query)
        if any(character.isalpha() for character in token)
        and any(character.isdigit() for character in token)
        and not any(normalize(token) == normalize(value) for value in matched_sections)
    ]
    for token in unmatched_section_tokens:
        normalized_token = normalize(token)
        if len(normalized_token) == 2:
            suffix_matches = [
                value for value in sections
                if normalize(value).endswith(normalized_token)
            ]
            if len(suffix_matches) == 1 and suffix_matches[0] not in matched_sections:
                matched_sections.append(suffix_matches[0])
            continue
        scored_sections = sorted(
            (
                _similar(normalized_token, normalize(value)),
                value,
            )
            for value in sections
            if value not in matched_sections and len(normalize(value)) >= 4
        )
        if not scored_sections:
            continue
        best_score = scored_sections[-1][0]
        best_matches = [value for score, value in scored_sections if score == best_score]
        if best_score >= 0.86 and len(best_matches) == 1:
            matched_sections.append(best_matches[0])
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

    def explicitly_names_faculty(value: str) -> bool:
        name_tokens = [token for token in _name_words(value) if token]
        raw_tokens = words(value)
        if len(name_tokens) == 1 and len(raw_tokens) == 1:
            return normalize(name_tokens[0]) in {normalize(token) for token in query_words}
        return bool(normalize(value) and normalize(value) in compact_query)

    explicitly_named_faculty = [value for value in faculty if explicitly_names_faculty(value)]
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
    grounded_non_faculty_tokens = {
        normalize(token)
        for value in matched_sections + matched_codes + explicitly_named_courses
        for token in (*words(value), normalize(value))
        if token
    }
    faculty_query_sequence = [
        word for word in meaningful_query_sequence
        if normalize(word) not in grounded_non_faculty_tokens
    ]

    def partial_name_position(value: str) -> int | None:
        name_sequence = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
        if len(name_sequence) < 3:
            return None
        for fragment_length in range(len(name_sequence) - 1, 1, -1):
            for name_index in range(len(name_sequence) - fragment_length + 1):
                fragment = name_sequence[name_index:name_index + fragment_length]
                for query_index in range(len(faculty_query_sequence) - fragment_length + 1):
                    if faculty_query_sequence[query_index:query_index + fragment_length] == fragment:
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
    query_word_positions = {word: index for index, word in enumerate(faculty_query_sequence)}
    named_faculty.sort(key=lambda value: min(
        (query_word_positions[word] for word in _name_words(value) if word in query_word_positions),
        default=len(faculty_query_sequence),
    ))

    meaningful_query_words = set(meaningful_query_sequence)
    meaningful_query_compact = "".join(meaningful_query_sequence)
    faculty_query_words = set(faculty_query_sequence)
    faculty_query_compact = "".join(faculty_query_sequence)
    matched_faculty = list(named_faculty)
    if not matched_faculty and faculty_query_words:
        faculty_scores = []
        for value in faculty:
            name_words = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
            overlap = sum(1 for word in name_words if word in faculty_query_words)
            if not name_words:
                continue
            similarities = [
                max((_similar(name_word, query_word) for query_word in faculty_query_words), default=0)
                for name_word in name_words
            ]
            covered = [similarity for similarity in similarities if similarity >= 0.72]
            if len(faculty_query_words) == 1:
                score = max(covered, default=0)
            else:
                score = (10 * len(covered) / len(name_words)) + (sum(covered) / len(name_words)) if covered else 0
            compact_name = "".join(name_words)
            compact_name_evidence = False
            if faculty_query_compact and len(faculty_query_compact) >= max(6, int(len(compact_name) * 0.7)):
                compact_similarity = _similar(compact_name, faculty_query_compact)
                if compact_similarity >= 0.78:
                    score = max(score, compact_similarity * 20)
                    compact_name_evidence = True
            strong_name_evidence = bool(
                overlap
                or len(covered) >= 2
                or compact_name_evidence
                or (
                    len(faculty_query_words) == 1
                    and max(covered, default=0) >= 0.78
                )
            )
            if not strong_name_evidence:
                score = 0
            if score > 0:
                faculty_scores.append((score, overlap, value))
        best_faculty_score = max((score for score, _, _ in faculty_scores), default=0)
        matched_faculty = [value for score, _, value in faculty_scores if score == best_faculty_score]

    matched_courses = list(explicitly_named_courses)
    resolved_context_tokens = {
        normalize(token)
        for value in matched_sections + matched_faculty + matched_codes
        for token in (*words(value), normalize(value))
        if token
    }
    residual_course_words = [
        word for word in meaningful_query_sequence
        if normalize(word) not in resolved_context_tokens
    ]
    should_fuzzy_course = any(
        len(word) >= 4 and any(character.isalpha() for character in word)
        for word in residual_course_words
    )
    if not matched_courses and should_fuzzy_course:
        course_scores = []
        for value in courses:
            title_words = [word for word in words(value) if len(word) >= 3 and word not in NOISE]
            compact_title = normalize(value)
            overlap = sum(1 for word in title_words if word in meaningful_query_words)
            fuzzy_threshold = 0.90 if len(meaningful_query_words) == 1 else 0.82
            fuzzy_overlap = sum(
                1 for title_word in title_words
                if title_word not in meaningful_query_words
                and any(_similar(query_word, title_word) >= fuzzy_threshold for query_word in meaningful_query_words)
            )
            if overlap or fuzzy_overlap:
                score = (overlap + fuzzy_overlap) / max(len(title_words), 1)
            else:
                score = 0
            if meaningful_query_compact and len(meaningful_query_compact) >= max(8, int(len(compact_title) * 0.7)):
                compact_similarity = _similar(compact_title, meaningful_query_compact)
                if compact_similarity >= 0.78:
                    score = max(score, compact_similarity * 20)
            if score:
                course_scores.append((score, value))
        best_course_score = max((score for score, _ in course_scores), default=0)
        matched_courses = [value for score, value in course_scores if score == best_course_score]

    resolved_values = [
        (kind, value)
        for kind, values in (
            ("section", matched_sections),
            ("faculty", matched_faculty),
            ("course", matched_courses),
            ("code", matched_codes),
        )
        for value in values
    ]
    dominated = {
        (kind, value)
        for kind, value in resolved_values
        if any(
            kind != other_kind
            and normalize(value) != normalize(other)
            and normalize(value) in normalize(other)
            for other_kind, other in resolved_values
        )
    }

    return {
        "sections": [value for value in matched_sections if ("section", value) not in dominated],
        "faculty": [value for value in matched_faculty if ("faculty", value) not in dominated],
        "courses": [value for value in matched_courses if ("course", value) not in dominated],
        "codes": [value for value in matched_codes if ("code", value) not in dominated],
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
        r"\b(?:add|adding|include|including|take|taking)\b",
        r"\bbut\b.{0,80}\b(?:want|take|add|include)\b",
        r"\b(?:want|would\s+like)\s+to\s+(?:take|add|include)\b",
        r"\bi(?:\s+am|'m|m)\s+(?:from|in)\b",
    )
    return any(re.search(pattern, lowered) for pattern in additive_language)


def _excluded_entity_scope(query: str, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Return explicitly negated course titles and codes.

    Negation is attached to the entity immediately following language such as
    "except", "without", or "I don't take". Keeping this separate from the
    positive entity plan prevents an excluded base-section course from being
    mistaken for an additional course selection.
    """
    compact_query = normalize(query)
    has_negative_language = bool(re.search(
        r"\b(?:except(?:\s+for)?|excluding|exclude|without|but\s+not|other\s+than|"
        r"apart\s+from|don['’]?t\s+take|do\s+not\s+take|not\s+taking|"
        r"not\s+enrolled\s+in|leave\s+out|skip|drop|remove)\b",
        query.lower(),
    ))
    negative_prefix = re.compile(
        r"(?:except(?:for)?|excluding|exclude|without|butnot|otherthan|apartfrom|"
        r"donttake|donottake|nottaking|notenrolledin|leaveout|leavingout|skip|"
        r"skipping|drop|dropping|remove|removing|no)"
        r"(?:the)?(?:course|class|subject)?$"
    )

    def is_negated(value: str) -> bool:
        occurrences = _entity_occurrences(query, value)
        for start, _ in occurrences:
            prefix = compact_query[max(0, start - 64):start]
            if negative_prefix.search(prefix):
                return True
        # A fuzzy-resolved typo has no exact occurrence to inspect. If the
        # sentence contains exclusion language and this entity was resolved
        # only fuzzily, preserve the intended negative role.
        return not occurrences and has_negative_language

    return {
        "courses": [value for value in entities["courses"] if is_negated(value)],
        "codes": [value for value in entities["codes"] if is_negated(value)],
    }


def _without_excluded_entities(
    entities: Dict[str, List[str]],
    exclusions: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """Copy the entity plan without references reserved for exclusions."""
    excluded_courses = {normalize(value) for value in exclusions["courses"]}
    excluded_codes = {normalize(value) for value in exclusions["codes"]}
    return {
        **entities,
        "courses": [value for value in entities["courses"] if normalize(value) not in excluded_courses],
        "codes": [value for value in entities["codes"] if normalize(value) not in excluded_codes],
    }


def _matches_exclusion(item: Dict, exclusions: Dict[str, List[str]]) -> bool:
    course = normalize(item.get("course_title") or item.get("course"))
    code = normalize(item.get("course_code"))
    return any(normalize(value) == course for value in exclusions["courses"]) or any(
        normalize(value) == code for value in exclusions["codes"]
    )


def _entity_occurrences(query: str, value: str) -> List[Tuple[int, int]]:
    """Locate punctuation-insensitive entity mentions in normalized query space."""
    compact_query = normalize(query)
    needle = normalize(value)
    if not needle:
        return []
    occurrences = []
    cursor = 0
    while True:
        start = compact_query.find(needle, cursor)
        if start < 0:
            return occurrences
        occurrences.append((start, start + len(needle)))
        cursor = start + 1


def _additive_selection_scope(
    query: str,
    entities: Dict[str, List[str]],
    items: List[Dict],
) -> Dict[str, object]:
    """Bind explicitly requested courses to their requested sections.

    Natural-language custom schedules contain two different kinds of section:
    the student's base section and a section that qualifies one additional
    course. Flattening those into one list turns every named section into a
    complete timetable and leaks unrelated rows. This plan retains those
    relationships before filtering.
    """
    compact_query = normalize(query)
    section_mentions = [
        {"value": value, "start": start, "end": end}
        for value in entities["sections"]
        for start, end in _entity_occurrences(query, value)
    ]
    references = [
        {"kind": kind, "value": value, "start": start, "end": end}
        for kind, values in (("course", entities["courses"]), ("code", entities["codes"]))
        for value in values
        for start, end in _entity_occurrences(query, value)
    ]
    section_mentions.sort(key=lambda mention: (mention["start"], mention["end"]))
    references.sort(key=lambda mention: (mention["start"], mention["end"]))

    home_prefixes = (
        "iamfrom", "imfrom", "iamin", "imin", "mysectionis", "mysemesteris",
        "myclassis", "mycoresectionis", "mybaseis", "ienrolledin", "ibelongto",
        "classof", "classesof", "scheduleof", "timetableof",
        "iamtakingeveryclasswith", "itakeeveryclasswith", "iamtakingallclasseswith",
        "itakeallclasseswith", "takingeveryclasswith", "takingallclasseswith",
    )
    home_suffixes = ("student", "timetable", "schedule", "classes", "classload", "courseload", "base")
    base_sections: List[str] = []
    base_mentions = set()
    for mention in section_mentions:
        before = compact_query[max(0, int(mention["start"]) - 32):int(mention["start"])]
        after = compact_query[int(mention["end"]):int(mention["end"]) + 16]
        if any(before.endswith(marker) for marker in home_prefixes) or any(
            after.startswith(marker) for marker in home_suffixes
        ):
            value = str(mention["value"])
            if value not in base_sections:
                base_sections.append(value)
            base_mentions.add((mention["start"], mention["end"], mention["value"]))

    connector_words = {
        "", "with", "from", "in", "at", "for", "of", "under", "section",
        "fromsection", "insection", "withsection", "offeredby",
    }
    qualifier_words = {
        "theory": "theory",
        "lab": "lab",
        "labs": "lab",
        "laboratory": "lab",
        "laboratories": "lab",
        "fyp": "fyp",
        "finalyearproject": "fyp",
    }

    def binding_gap(value: str) -> Tuple[bool, List[str]]:
        remaining = value
        selected_types = []
        for qualifier, class_type in sorted(qualifier_words.items(), key=lambda entry: -len(entry[0])):
            if qualifier in remaining:
                remaining = remaining.replace(qualifier, "")
                if class_type not in selected_types:
                    selected_types.append(class_type)
        remaining = remaining.replace("classes", "").replace("class", "")
        return remaining in connector_words, selected_types

    candidates = []
    for section_index, section in enumerate(section_mentions):
        if (section["start"], section["end"], section["value"]) in base_mentions:
            continue
        for reference_index, reference in enumerate(references):
            if int(reference["end"]) <= int(section["start"]):
                gap = compact_query[int(reference["end"]):int(section["start"])]
                distance = int(section["start"]) - int(reference["end"])
                direction_penalty = 0
            elif int(section["end"]) <= int(reference["start"]):
                gap = compact_query[int(section["end"]):int(reference["start"])]
                distance = int(reference["start"]) - int(section["end"])
                # Course-qualified selections are normally written as
                # "COURSE from SECTION". Without a directional preference,
                # the next course in a comma-separated list can sit directly
                # after the previous section and steal that section because
                # its raw character distance is zero. Keep section-first
                # wording supported, but prefer the explicit reference-first
                # binding when both interpretations are possible.
                direction_penalty = 24
            else:
                continue
            valid_gap, local_class_types = binding_gap(gap)
            reference_prefix = compact_query[max(0, int(reference["start"]) - 24):int(reference["start"])]
            for qualifier, class_type in qualifier_words.items():
                if reference_prefix.endswith(qualifier) and class_type not in local_class_types:
                    local_class_types.append(class_type)
            if valid_gap and distance <= 40:
                candidates.append((
                    distance + direction_penalty,
                    section_index,
                    reference_index,
                    local_class_types,
                ))

    used_sections = set()
    used_references = set()
    pairs = []
    for _, section_index, reference_index, local_class_types in sorted(candidates):
        if section_index in used_sections or reference_index in used_references:
            continue
        section = section_mentions[section_index]
        reference = references[reference_index]
        pair = {
            "section": str(section["value"]),
            "kind": str(reference["kind"]),
            "value": str(reference["value"]),
            "class_types": local_class_types,
            "_query_position": int(reference["start"]),
        }
        if not any(
            existing["section"] == pair["section"]
            and existing["kind"] == pair["kind"]
            and existing["value"] == pair["value"]
            and existing["class_types"] == pair["class_types"]
            for existing in pairs
        ):
            pairs.append(pair)
        used_sections.add(section_index)
        used_references.add(reference_index)

    pairs.sort(key=lambda pair: pair["_query_position"])
    for pair in pairs:
        pair.pop("_query_position", None)

    paired_sections = {pair["section"] for pair in pairs}
    if not base_sections:
        # Unpaired named sections retain the legacy meaning of complete
        # section timetables. A query made entirely of qualified selections
        # ("Course X with 5B") intentionally has no base timetable.
        for mention in section_mentions:
            value = str(mention["value"])
            if value not in paired_sections and value not in base_sections:
                base_sections.append(value)

    paired_references = {(pair["kind"], pair["value"]) for pair in pairs}
    # A user may name both the code and title of the same selected course.
    # Treat both as consumed by the pair; leaving either one as a global
    # addition would reintroduce that course from every other section.
    for pair in pairs:
        for item in items:
            if normalize(pair["section"]) != normalize(_item_section(item)):
                continue
            pair_matches_item = (
                pair["kind"] == "course"
                and normalize(pair["value"]) == normalize(item.get("course_title") or item.get("course"))
            ) or (
                pair["kind"] == "code"
                and normalize(pair["value"]) == normalize(item.get("course_code"))
            )
            if not pair_matches_item:
                continue
            paired_references.update(
                ("course", value)
                for value in entities["courses"]
                if normalize(value) == normalize(item.get("course_title") or item.get("course"))
            )
            paired_references.update(
                ("code", value)
                for value in entities["codes"]
                if normalize(value) == normalize(item.get("course_code"))
            )
    paired_class_types = {
        class_type
        for pair in pairs
        for class_type in pair["class_types"]
    }
    return {
        "base_sections": base_sections,
        "_base_sections_explicit": bool(base_mentions),
        "course_section_pairs": pairs,
        "unpaired_courses": [
            value for value in entities["courses"] if ("course", value) not in paired_references
        ],
        "unpaired_codes": [
            value for value in entities["codes"] if ("code", value) not in paired_references
        ],
        "global_class_types": [
            class_type for class_type in entities["class_types"] if class_type not in paired_class_types
        ],
    }


def _matches_additive_course_scope(
    item: Dict,
    entities: Dict[str, List[str]],
    selection_scope: Dict[str, object],
) -> bool:
    """Match a base section or an explicitly scoped additional course."""
    section_match = any(
        normalize(value) == normalize(_item_section(item))
        for value in selection_scope["base_sections"]
    )
    course_match = any(
        normalize(value) == normalize(item.get("course_title") or item.get("course"))
        for value in selection_scope["unpaired_courses"]
    )
    code_match = any(
        normalize(value) == normalize(item.get("course_code"))
        for value in selection_scope["unpaired_codes"]
    )
    matched_pairs = [
        pair
        for pair in selection_scope["course_section_pairs"]
        if (
        normalize(pair["section"]) == normalize(_item_section(item))
        and (
            pair["kind"] == "course"
            and normalize(pair["value"]) == normalize(item.get("course_title") or item.get("course"))
            or pair["kind"] == "code"
            and normalize(pair["value"]) == normalize(item.get("course_code"))
        )
        )
    ]
    pair_match = bool(matched_pairs)
    if not (section_match or course_match or code_match or pair_match):
        return False

    if entities["faculty"] and not any(
        normalize(value) == normalize(item.get("faculty"))
        for value in entities["faculty"]
    ):
        return False
    if not section_match:
        local_pair_types = {
            class_type
            for pair in matched_pairs
            for class_type in pair["class_types"]
        }
        applicable_types = local_pair_types or set(selection_scope["global_class_types"])
        if applicable_types and _class_type(item) not in applicable_types:
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
    discovered_entities = find_entities(query, items)
    exclusions = _excluded_entity_scope(query, discovered_entities)
    entities = _without_excluded_entities(discovered_entities, exclusions)
    candidate_scope = (
        _additive_selection_scope(query, entities, items)
        if entities["sections"] and (entities["courses"] or entities["codes"])
        else None
    )
    structural_addition = bool(candidate_scope and (
        (
            candidate_scope["_base_sections_explicit"]
            and candidate_scope["course_section_pairs"]
        )
        or len(candidate_scope["course_section_pairs"]) > 1
    ))
    additive_course_scope = _uses_additive_course_scope(query, entities) or structural_addition
    selection_scope = candidate_scope if additive_course_scope else None
    if selection_scope:
        selection_scope.pop("_base_sections_explicit", None)
    matches_scope = (
        (lambda item: _matches_additive_course_scope(item, entities, selection_scope))
        if additive_course_scope
        else (lambda item: _matches(item, entities))
    )
    wants_free = _wants_faculty_availability(query)
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
    if exclusions["courses"] or exclusions["codes"]:
        matched = [item for item in matched if not _matches_exclusion(item, exclusions)]
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
            breakdown = f": {', '.join(type_parts)}" if len(type_parts) > 1 else ""
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
            base = ", ".join(selection_scope["base_sections"])
            additions = [
                f"{pair['value']} ({pair['section']})"
                for pair in selection_scope["course_section_pairs"]
            ] + selection_scope["unpaired_courses"] + selection_scope["unpaired_codes"]
            requested_scope = f"{base} plus {', '.join(additions)}" if base else ", ".join(additions)
            exclusion_labels = exclusions["courses"] + exclusions["codes"]
            exclusion_suffix = (
                f", excluding {', '.join(exclusion_labels)}"
                if exclusion_labels else ""
            )
            answer = (
                f"Found {len(matched)} {'class' if len(matched) == 1 else 'classes'} "
                f"for {requested_scope}{exclusion_suffix}{day_suffix}."
            )
        elif matched:
            exclusion_labels = exclusions["courses"] + exclusions["codes"]
            exclusion_suffix = (
                f", excluding {', '.join(exclusion_labels)}"
                if exclusion_labels else ""
            )
            answer = (
                f"Found {len(matched)} {kind if len(matched) == 1 else kind + 'es'} "
                f"for {subject}{exclusion_suffix}{day_suffix}."
            )
        elif not any(entities.values()) and not _is_broad_schedule_request(query):
            answer = (
                "I couldn't identify a section, faculty member, course, class type, "
                "credit-hour value, or schedule scope in that question."
            )
        else:
            answer = f"No {kind + 'es'} found for {subject}{day_suffix}."
    recognized = bool(any(entities.values()) or _is_broad_schedule_request(query))
    # Coincident rows are meaningful clashes only when the user is composing
    # a custom timetable from a base section and explicit additions. Ordinary
    # faculty, course, credit-hour, and broad schedule searches intentionally
    # return parallel offerings and must not present those as personal clashes.
    conflicts = _schedule_conflicts(matched) if additive_course_scope else []
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
            "exclusions": exclusions,
            "selection_scope": selection_scope,
        },
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "recognized": recognized,
    }
