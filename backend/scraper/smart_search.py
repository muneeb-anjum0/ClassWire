"""Natural-language timetable query interpretation."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_START = 8 * 60
DAY_END = 21 * 60 + 30
NOISE = {
    "schedule", "timetable", "time", "table", "class", "classes", "course", "courses",
    "when", "where", "what", "does", "have", "has", "their", "there", "entire", "week",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "free", "office",
    "next", "this", "following",
    "is", "are", "was", "were", "be", "in", "on", "at", "for", "show", "find", "give", "tell",
    "me", "the", "a", "an", "of", "please", "theory", "lab", "laboratory", "fyp", "final", "year", "project",
}
HONORIFICS = {"mr", "mrs", "ms", "miss", "dr", "prof", "professor", "engr", "eng"}


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def words(value: object) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def parse_days(query: str) -> List[str]:
    lowered = query.lower()
    selected = [day for day in DAYS if day.lower() in lowered]
    if "entire week" in lowered or "all week" in lowered or "whole week" in lowered:
        return DAYS
    if not selected:
        query_tokens = words(query)
        selected = [
            day for day in DAYS
            if any(SequenceMatcher(None, token, day.lower()).ratio() >= 0.78 for token in query_tokens)
        ]
    return selected or DAYS


def _similar(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _item_section(item: Dict) -> str:
    return str(item.get("semester_display") or item.get("semester") or item.get("section") or "")


def _class_type(item: Dict) -> str | None:
    text = " ".join(str(item.get(field) or "") for field in ("course", "course_title", "full_text"))
    match = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if not match:
        return None
    credits = (int(match.group(1)), int(match.group(2)))
    if credits in {(3, 0), (2, 0)}:
        return "theory"
    if credits == (0, 1):
        return "lab"
    if credits == (0, 3):
        return "fyp"
    return None


def _requested_class_types(query: str) -> List[str]:
    lowered = query.lower()
    requested = []
    if "theory" in lowered or re.search(r"\(\s*[23]\s*,\s*0\s*\)", lowered):
        requested.append("theory")
    if re.search(r"\b(?:lab|laboratory)\b", lowered) or re.search(r"\(\s*0\s*,\s*1\s*\)", lowered):
        requested.append("lab")
    if "fyp" in lowered or "final year project" in lowered or re.search(r"\(\s*0\s*,\s*3\s*\)", lowered):
        requested.append("fyp")
    return requested


def _name_words(value: object) -> List[str]:
    return [word for word in words(value) if word not in HONORIFICS]


def _canonical_faculty_names(items: List[Dict]) -> Dict[str, str]:
    """Resolve harmless aliases such as 'Mr. Qasim' to a unique full name."""
    names = sorted({str(item.get("faculty")).strip() for item in items if item.get("faculty")})
    aliases = {name: name for name in names}
    for name in names:
        base = _name_words(name)
        if not base:
            continue
        exact = [candidate for candidate in names if _name_words(candidate) == base]
        if len(exact) > 1:
            aliases[name] = max(exact, key=lambda candidate: (len(_name_words(candidate)), len(candidate)))
            continue
        if len(base) == 1:
            fuller = [
                candidate for candidate in names
                if len(_name_words(candidate)) > 1 and _name_words(candidate)[-1] == base[0]
            ]
            if len(fuller) == 1:
                aliases[name] = fuller[0]
    return aliases


def _canonicalize_faculty(items: List[Dict]) -> List[Dict]:
    aliases = _canonical_faculty_names(items)
    canonical = []
    seen = set()
    for source in items:
        item = dict(source)
        faculty = str(item.get("faculty") or "").strip()
        if faculty:
            item["faculty"] = aliases.get(faculty, faculty)
            item["faculty_name"] = item["faculty"]
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

    matched_sections = [value for value in sections if normalize(value) and normalize(value) in compact_query]
    faculty_scores = []
    meaningful_query_words = {word for word in query_words if len(word) >= 3 and word not in NOISE}
    for value in faculty:
        name_words = [word for word in _name_words(value) if len(word) >= 3 and word not in NOISE]
        overlap = sum(1 for word in name_words if word in meaningful_query_words)
        if not name_words:
            continue
        if normalize(value) in compact_query:
            score = 100 + len(name_words)
        else:
            score = overlap
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

    matched_codes = [value for value in codes if normalize(value) and normalize(value) in compact_query]
    course_scores = []
    for value in courses:
        title_words = [word for word in words(value) if len(word) >= 4 and word not in NOISE]
        compact_title = normalize(value)
        overlap = sum(1 for word in title_words if word in meaningful_query_words)
        fuzzy_overlap = sum(
            1 for title_word in title_words
            if title_word not in meaningful_query_words and any(_similar(query_word, title_word) >= 0.82 for query_word in meaningful_query_words)
        )
        if len(compact_title) >= 3 and compact_title in compact_query:
            score = 100 + len(title_words)
        elif overlap or fuzzy_overlap:
            score = (overlap + fuzzy_overlap) / max(len(title_words), 1)
        else:
            score = 0
        if score:
            course_scores.append((score, value))
    if len(meaningful_query_words) <= 1:
        matched_courses = [value for _, value in course_scores]
    else:
        best_course_score = max((score for score, _ in course_scores), default=0)
        matched_courses = [value for score, value in course_scores if score == best_course_score]

    return {"sections": matched_sections, "faculty": matched_faculty, "courses": matched_courses, "codes": matched_codes, "class_types": _requested_class_types(query)}


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
    return all(checks) if checks else False


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


def search_timetable(query: str, items: List[Dict]) -> Dict:
    items = _canonicalize_faculty(items)
    days = parse_days(query)
    entities = find_entities(query, items)
    day_items = [item for item in items if item.get("schedule_day") in days]
    matched = [item for item in day_items if _matches(item, entities)]
    day_rank = {day: index for index, day in enumerate(DAYS)}
    matched.sort(key=lambda item: (
        day_rank.get(str(item.get("schedule_day")), len(DAYS)),
        (_time_minutes(str(item.get("time") or "")) or (DAY_END, DAY_END))[0],
        normalize(_item_section(item)),
        normalize(item.get("course_title") or item.get("course")),
    ))
    wants_free = any(phrase in query.lower() for phrase in ("free", "available", "office hour", "no class"))
    faculty_availability = []
    if wants_free and entities["faculty"]:
        for faculty in entities["faculty"]:
            faculty_items = [item for item in matched if normalize(item.get("faculty")) == normalize(faculty)]
            faculty_availability.append({
                "faculty": faculty,
                "slots": faculty_free_slots(faculty_items, days),
            })
    free_slots = faculty_availability[0]["slots"] if len(faculty_availability) == 1 else {}
    labels = entities["sections"] + entities["faculty"] + entities["courses"] + entities["codes"]
    subject = ", ".join(dict.fromkeys(labels)) if labels else "your query"
    if wants_free and entities["faculty"]:
        answer = "Faculty availability"
    else:
        class_type = entities["class_types"][0] if len(entities["class_types"]) == 1 else ""
        kind = f"{class_type} class" if class_type else "class"
        if matched:
            answer = f"Found {len(matched)} {kind if len(matched) == 1 else kind + 'es'} for {subject}."
        else:
            answer = f"No {kind + 'es'} found for {subject}."
    return {"items": matched, "days": days, "entities": entities, "free_slots": free_slots, "faculty_availability": faculty_availability, "answer": answer, "intent": "free_time" if wants_free else "schedule"}
