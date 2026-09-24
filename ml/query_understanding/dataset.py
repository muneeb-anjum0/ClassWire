"""Deterministic synthetic data for the ClassWire NLU model.

Every entity offset is created while composing the sentence. Labels therefore do
not come from the production parser and cannot silently copy its mistakes.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .labels import ENTITY_ROLES, INTENTS


@dataclass(frozen=True)
class Mention:
    text: str
    label: str
    group: int | None = None


Part = str | Mention
Builder = Callable[[random.Random], tuple[str, list[dict], str]]

SECTIONS = (
    "BSSE2A", "BSSE3A", "BSSE5A", "BSSE5B", "BSSE6A", "BSSE6B",
    "BSSE7A", "BSSE7B", "BSSE8A", "BSAI8B", "BSCS2A", "BSCS3B",
    "BBA4A", "BSAF3A", "BSSS2", "BSED1",
)
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
DAY_ALIASES = {
    "Monday": ("Monday", "Mon", "Monay"),
    "Tuesday": ("Tuesday", "Tue", "Tuesay"),
    "Wednesday": ("Wednesday", "Wed", "Wednesay"),
    "Thursday": ("Thursday", "Thu", "Thrusday"),
    "Friday": ("Friday", "Fri", "Firday"),
    "Saturday": ("Saturday", "Sat", "Satuday"),
}
COURSES = (
    "Software Construction and Development",
    "Software Quality Engineering and Testing",
    "Software Re-Engineering",
    "Artificial Intelligence",
    "Computer Networks",
    "Mobile Application Development",
    "Design and Analysis of Algorithms",
    "Data Structures and Algorithms",
    "Digital Image Processing",
    "Information Security",
    "Object Oriented Programming Techniques",
    "Visual Programming",
    "Organizational Behavior",
    "Mathematics and Statistics",
    "Principles of Microeconomics",
    "Introduction to International Relations",
    "Fundamentals of Sociology",
)
COURSE_ALIASES = {
    "Software Construction and Development": (
        "Software Construction and Development", "Software Construction", "SEC 3604",
    ),
    "Software Quality Engineering and Testing": (
        "Software Quality Engineering and Testing", "Software Quality", "SEC 3608",
    ),
    "Software Re-Engineering": (
        "Software Re-Engineering", "Software Re Engineering", "SEC 3606",
    ),
    "Artificial Intelligence": ("Artificial Intelligence", "AI", "SEC 3616"),
    "Computer Networks": ("Computer Networks", "Networks", "CSC 3209"),
    "Mobile Application Development": (
        "Mobile Application Development", "Mobile Development", "SEC 3612",
    ),
    "Design and Analysis of Algorithms": (
        "Design and Analysis of Algorithms", "Algorithm Analysis", "CSC 3202",
    ),
    "Data Structures and Algorithms": (
        "Data Structures and Algorithms", "Data Structures", "CSC 2102",
    ),
    "Digital Image Processing": ("Digital Image Processing", "DIP", "SEC 4515"),
    "Information Security": ("Information Security", "InfoSec", "SEC 3617"),
    "Object Oriented Programming Techniques": (
        "Object Oriented Programming Techniques", "OOP", "CSC 1208",
    ),
    "Visual Programming": ("Visual Programming", "VP", "SEC 4518"),
    "Organizational Behavior": ("Organizational Behavior", "OB", "SEC 3309"),
    "Mathematics and Statistics": ("Mathematics and Statistics", "EDS 1108"),
    "Principles of Microeconomics": ("Principles of Microeconomics", "EDS 1104"),
    "Introduction to International Relations": (
        "Introduction to International Relations", "IR 2108",
    ),
    "Fundamentals of Sociology": ("Fundamentals of Sociology", "SOC 2102"),
}
FACULTY = (
    ("Sheikh Abdul Wahab", ("Sheikh Abdul Wahab", "sir Wahab", "Wahab")),
    ("Muhammad Qasim", ("Muhammad Qasim", "sir Qasim", "Qasim")),
    ("Zainab Iftikhar Chaudhary", ("Zainab Iftikhar Chaudhary", "Zainab Iftikhar", "Zainub Iftikhar")),
    ("Hamza Imran", ("Hamza Imran", "Hamza")),
    ("Arfa Asaf", ("Arfa Asaf", "maam Arfa", "Arfa")),
)
TIME_RANGES = ("before 2 PM", "after 5 PM", "between 11 AM and 3 PM", "8 AM to noon")


def compose(parts: Iterable[Part]) -> tuple[str, list[dict]]:
    """Join text fragments and calculate exact, non-overlapping entity spans."""
    text = ""
    entities: list[dict] = []
    for part in parts:
        if isinstance(part, str):
            text += part
            continue
        if part.label not in ENTITY_ROLES:
            raise ValueError(f"Unknown entity role: {part.label}")
        start = len(text)
        text += part.text
        entity = {
            "text": part.text,
            "label": part.label,
            "start": start,
            "end": len(text),
        }
        if part.group is not None:
            entity["group"] = part.group
        entities.append(entity)
    return text, entities


def _section(rng: random.Random, role: str, *, exclude: str | None = None, group: int | None = None) -> Mention:
    choices = [value for value in SECTIONS if value != exclude]
    return Mention(rng.choice(choices), role, group)


def _day(rng: random.Random) -> Mention:
    canonical = rng.choice(DAYS)
    return Mention(rng.choice(DAY_ALIASES[canonical]), "DAY")


def _course(rng: random.Random, role: str, *, exclude: str | None = None, group: int | None = None) -> Mention:
    excluded_canonical = next(
        (
            canonical
            for canonical, aliases in COURSE_ALIASES.items()
            if exclude == canonical or exclude in aliases
        ),
        exclude,
    )
    choices = [value for value in COURSES if value != excluded_canonical]
    canonical = rng.choice(choices)
    return Mention(rng.choice(COURSE_ALIASES[canonical]), role, group)


def _faculty(rng: random.Random) -> Mention:
    _, aliases = rng.choice(FACULTY)
    return Mention(rng.choice(aliases), "FACULTY")


def _record(parts: list[Part], intent: str) -> tuple[str, list[dict], str]:
    text, entities = compose(parts)
    return text, entities, intent


def _base_plain(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Show me ", "I am from ", "Open the timetable for ")),
        _section(rng, "BASE_SECTION"),
    ], "schedule")


def _base_day(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Show ", "What classes does ", "Give me ")),
        _section(rng, "BASE_SECTION"),
        rng.choice((" have on ", " classes for ", " on ")),
        _day(rng),
    ], "schedule")


def _filter_course(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Show ", "Find ", "When is ")),
        _course(rng, "FILTER_COURSE"),
        rng.choice((" across the week", " classes", " scheduled")),
    ], "schedule")


def _filter_course_day(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Find ", "Show me ", "List ")),
        _course(rng, "FILTER_COURSE"), " on ", _day(rng),
    ], "schedule")


def _filter_course_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "During ", _day(rng), rng.choice((" locate ", " where is ", " find the slot for ")),
        _course(rng, "FILTER_COURSE"),
    ], "schedule")


def _section_pair_days(rng: random.Random) -> tuple[str, list[dict], str]:
    first = _section(rng, "FILTER_SECTION")
    second = _section(rng, "FILTER_SECTION", exclude=first.text)
    return _record([
        first, rng.choice((" and ", " plus ")), second,
        rng.choice((" classes on ", " timetable for ")), _day(rng),
    ], "schedule")


def _base_add_one(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        rng.choice(("I am in ", "My section is ", "Build my ")),
        base, rng.choice(("; add ", " but include ", " plus ")),
        _course(rng, "ADDED_COURSE", group=1),
        rng.choice((" from ", " with ")),
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
    ], "schedule")


def _base_add_one_polite(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        rng.choice(("Can I get all of ", "Please use ", "Create a plan around ")),
        base, rng.choice((" and take ", " while taking ", " together with ")),
        _course(rng, "ADDED_COURSE", group=1), " in ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
    ], "schedule")


def _base_add_two(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    first_course = _course(rng, "ADDED_COURSE", group=1)
    second_course = _course(rng, "ADDED_COURSE", exclude=first_course.text, group=2)
    first_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=1)
    second_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=2)
    return _record([
        "I am from ", base, "; take ", first_course, " with ", first_section,
        rng.choice((" and ", ", plus ", "; also ")), second_course, " with ", second_section,
    ], "schedule")


def _base_add_two_reordered(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    first_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=1)
    second_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=2)
    return _record([
        "For ", base, " include ", first_section, "'s ",
        _course(rng, "ADDED_COURSE", group=1), " and ", second_section, "'s ",
        _course(rng, "ADDED_COURSE", group=2),
    ], "schedule")


def _base_add_section_first_train(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        rng.choice(("Use ", "Keep ", "Start with ")), base,
        rng.choice((" and borrow from ", " then include from ", " together with ")),
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
        rng.choice((" the course ", " its ", " class for ")),
        _course(rng, "ADDED_COURSE", group=1),
    ], "schedule")


def _base_add_possessive_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Teach possessive course-section binding without copying held-out templates."""
    base = _section(rng, "BASE_SECTION")
    return _record([
        rng.choice(("Use ", "Keep ", "Start from ")), base,
        rng.choice((" and include ", " while adding ", " together with ")),
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1), "'s ",
        _course(rng, "ADDED_COURSE", group=1),
    ], "schedule")


def _base_add_section_pairs_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Teach repeated section-first bindings and the boundary at a joining word."""
    base = _section(rng, "BASE_SECTION")
    first_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=1)
    second_section = _section(rng, "ADDED_SECTION", exclude=base.text, group=2)
    first_course = _course(rng, "ADDED_COURSE", group=1)
    return _record([
        rng.choice(("Build around ", "Keep all classes from ", "My base is ")), base,
        rng.choice(("; add ", ", then take ", " plus ")),
        first_section, " ", first_course,
        rng.choice((" and also ", ", alongside ", "; then ")),
        second_section, " ",
        _course(rng, "ADDED_COURSE", exclude=first_course.text, group=2),
    ], "schedule")


def _base_exclude(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("I take everything in ", "Show all of ", "My timetable is ")),
        _section(rng, "BASE_SECTION"),
        rng.choice((
            " except ", " without ", " but remove ", " but leave out ",
            " and skip ", " but do not include ",
        )),
        _course(rng, "EXCLUDED_COURSE"),
    ], "schedule")


def _base_exclude_add(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        "I am in ", base, ", not taking ", _course(rng, "EXCLUDED_COURSE"),
        ", and taking ", _course(rng, "ADDED_COURSE", group=1), " with ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
    ], "schedule")


def _base_exclude_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        "Use ", base, " minus ", _course(rng, "EXCLUDED_COURSE"),
        ", then include ", _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
        " for ", _course(rng, "ADDED_COURSE", group=1),
    ], "schedule")


def _base_exclude_two_train(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    first_course = _course(rng, "ADDED_COURSE", group=1)
    second_course = _course(rng, "ADDED_COURSE", exclude=first_course.text, group=2)
    return _record([
        "I take every class with ", base, " except ", _course(rng, "EXCLUDED_COURSE"),
        ", and I take ", first_course, " with ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1), " plus ",
        second_course, " with ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=2),
    ], "schedule")


def _base_add_then_exclude_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Teach that a trailing exclusion changes the following course's role."""
    base = _section(rng, "BASE_SECTION")
    added_course = _course(rng, "ADDED_COURSE", group=1)
    return _record([
        rng.choice(("Plan from ", "Use all of ", "Begin with ")), base,
        rng.choice((" and add ", "; include ", ", taking ")),
        added_course, " from ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1),
        rng.choice((", then leave out ", ", but skip ", "; exclude ")),
        _course(rng, "EXCLUDED_COURSE", exclude=added_course.text),
    ], "schedule")


def _base_exclude_two_test(rng: random.Random) -> tuple[str, list[dict], str]:
    base = _section(rng, "BASE_SECTION")
    return _record([
        "Start from ", base, ", add ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=1), " ",
        _course(rng, "ADDED_COURSE", group=1), " and ",
        _section(rng, "ADDED_SECTION", exclude=base.text, group=2), " ",
        _course(rng, "ADDED_COURSE", group=2), ", then leave out ",
        _course(rng, "EXCLUDED_COURSE"),
    ], "schedule")


def _availability(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("When is ", "Tell me when ", "Find free time for ")),
        _faculty(rng), rng.choice((" free", " available", " not teaching")),
    ], "faculty_availability")


def _availability_day(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("When can I meet ", "When is ", "Availability of ")),
        _faculty(rng), rng.choice((" on ", " this ", " during ")), _day(rng),
    ], "faculty_availability")


def _availability_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Free periods for ", "Open time belonging to ", "Find gaps for ")),
        _faculty(rng), rng.choice((" on ", " during ", " this ")), _day(rng),
    ], "faculty_availability")


def _availability_two_days(rng: random.Random) -> tuple[str, list[dict], str]:
    first = _day(rng)
    second_choices = [day for day in DAYS if day.lower() not in first.text.lower()]
    second_day = rng.choice(second_choices)
    return _record([
        "When is ", _faculty(rng), " free on ", first, " and ",
        Mention(rng.choice(DAY_ALIASES[second_day]), "DAY"),
    ], "faculty_availability")


def _availability_two_people_train(rng: random.Random) -> tuple[str, list[dict], str]:
    first_name, first_aliases = rng.choice(FACULTY)
    second_choices = [faculty for faculty in FACULTY if faculty[0] != first_name]
    _, second_aliases = rng.choice(second_choices)
    return _record([
        "When are ", Mention(rng.choice(first_aliases), "FACULTY"), " and ",
        Mention(rng.choice(second_aliases), "FACULTY"), " free on ", _day(rng),
    ], "faculty_availability")


def _availability_two_people_test(rng: random.Random) -> tuple[str, list[dict], str]:
    first_name, first_aliases = rng.choice(FACULTY)
    second_choices = [faculty for faculty in FACULTY if faculty[0] != first_name]
    _, second_aliases = rng.choice(second_choices)
    return _record([
        "Check ", _day(rng), " availability separately for ",
        Mention(rng.choice(first_aliases), "FACULTY"), " plus ",
        Mention(rng.choice(second_aliases), "FACULTY"),
    ], "faculty_availability")


def _faculty_schedule(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Show classes taught by ", "What does ", "Teaching schedule for ")),
        _faculty(rng), rng.choice(("", " teach", " this week")),
    ], "faculty_schedule")


def _faculty_schedule_day(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Show ", "List lessons for ", "Which classes does ")),
        _faculty(rng), rng.choice((" teach on ", " have on ", " on ")), _day(rng),
    ], "faculty_schedule")


def _faculty_schedule_day_first_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Contrast day-first teaching requests with availability questions."""
    return _record([
        rng.choice(("On ", "For ", "During ")), _day(rng),
        rng.choice((", list the classes taught by ", " show the teaching timetable for ",
                    ", which lessons belong to ")),
        _faculty(rng),
    ], "faculty_schedule")


def _availability_day_first_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Provide a matched day-first availability contrast for intent learning."""
    return _record([
        rng.choice(("On ", "For ", "During ")), _day(rng),
        rng.choice((", when is ", " find the free periods for ", ", show open time for ")),
        _faculty(rng), rng.choice(("", " please", " during university hours")),
    ], "faculty_availability")


def _class_type(rng: random.Random) -> tuple[str, list[dict], str]:
    class_type = rng.choice(("theory", "lab", "FYP"))
    return _record([
        rng.choice(("Show every ", "Find all ", "List ")),
        Mention(class_type, "CLASS_TYPE"), " class on ", _day(rng),
    ], "schedule")


def _credits_train(rng: random.Random) -> tuple[str, list[dict], str]:
    credit = rng.choice((
        "1 credit hour", "2 credit hour", "3 CH", "1 CH", "2 CH",
        "3 credits", "one credit", "two credits", "three credit hours",
    ))
    class_type = rng.choice(("theory", "lab", "FYP"))
    return _record([
        rng.choice(("Find ", "Show ", "List every ", "I need ")),
        Mention(credit, "CREDIT_HOURS"), " ", Mention(class_type, "CLASS_TYPE"),
        rng.choice((" course on ", " class scheduled on ", " offering for ")), _day(rng),
    ], "schedule")


def _credits_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    credit = rng.choice((
        "one credit", "two credits", "three credit hours", "1 CH", "2 CH", "3 CH",
    ))
    class_type = rng.choice(("theory", "lab", "FYP"))
    return _record([
        rng.choice(("Across the week show ", "For the full week list ", "Find any ")),
        Mention(class_type, "CLASS_TYPE"), " worth ", Mention(credit, "CREDIT_HOURS"),
        rng.choice(("", " please", " only")),
    ], "schedule")


def _credits_test(rng: random.Random) -> tuple[str, list[dict], str]:
    credit = rng.choice(("1 CH", "2 CH", "3 credits", "one credit", "two credits"))
    class_type = rng.choice(("theory", "lab", "FYP"))
    return _record([
        "On ", _day(rng), rng.choice((", which ", " show the ", " give me ")),
        Mention(class_type, "CLASS_TYPE"), " subjects carrying ",
        Mention(credit, "CREDIT_HOURS"), rng.choice(("", " in total", " only")),
    ], "schedule")


def _credits_reordered_train(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "On ", _day(rng), rng.choice((" list ", " show every ", " find a ")),
        Mention(rng.choice(("theory", "lab", "FYP")), "CLASS_TYPE"),
        rng.choice((" course worth ", " subject carrying ", " class with ")),
        Mention(rng.choice(("1 CH", "2 CH", "3 credits", "one credit")), "CREDIT_HOURS"),
    ], "schedule")


def _time_filter_train(rng: random.Random) -> tuple[str, list[dict], str]:
    if rng.random() < 0.5:
        return _record([
            rng.choice(("For ", "In ", "From ")), _section(rng, "FILTER_SECTION"),
            rng.choice((" find anything ", " show classes ", " list lectures ")),
            Mention(rng.choice(TIME_RANGES), "TIME_RANGE"),
        ], "schedule")
    return _record([
        rng.choice(("List ", "Find ", "Which ")),
        _section(rng, "FILTER_SECTION"),
        rng.choice((" classes running ", " lessons scheduled ", " courses held ")),
        Mention(rng.choice(TIME_RANGES), "TIME_RANGE"), " on ", _day(rng),
    ], "schedule")


def _time_filter_test(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "Show ", _section(rng, "FILTER_SECTION"), " classes ",
        Mention(rng.choice(TIME_RANGES), "TIME_RANGE"), " on ", _day(rng),
    ], "schedule")


def _time_filter_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "On ", _day(rng), " limit ", _section(rng, "FILTER_SECTION"),
        " to classes ", Mention(rng.choice(TIME_RANGES), "TIME_RANGE"),
    ], "schedule")


def _faculty_schedule_test(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "On ", _day(rng), rng.choice((", what is ", " show what ", " list what ")),
        _faculty(rng), rng.choice((" teaching", " scheduled to teach", " taking")),
    ], "faculty_schedule")


def _faculty_course_train(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "Show ", _course(rng, "FILTER_COURSE"), " classes taught by ", _faculty(rng),
    ], "faculty_schedule")


def _faculty_course_reordered_train(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        rng.choice(("Does ", "Check whether ", "Tell me if ")), _faculty(rng),
        rng.choice((" teach ", " handle ", " have ")), _course(rng, "FILTER_COURSE"),
        rng.choice(("", " this week", " on the schedule")),
    ], "faculty_schedule")


def _faculty_course_test(rng: random.Random) -> tuple[str, list[dict], str]:
    return _record([
        "Does ", _faculty(rng), " teach ", _course(rng, "FILTER_COURSE"), " on ", _day(rng),
    ], "faculty_schedule")


def _unknown(rng: random.Random) -> tuple[str, list[dict], str]:
    openings = (
        "Can you", "Please", "I need to", "Help me", "Where can I",
        "Is it possible to", "Tell me how to", "I want to", "Could you", "How do I",
    )
    actions = (
        "book a classroom", "check the campus weather", "email my instructor",
        "calculate my GPA", "pay the university fee", "submit an attendance correction",
        "download a transcript", "reserve a library book", "change my password",
        "apply for financial aid", "order food", "print my student card",
        "upload an assignment", "join a society", "report a lost item",
    )
    qualifiers = (
        "today", "tomorrow", "this week", "before lunch", "from my phone",
        "for next semester", "without visiting campus", "right now", "after class",
        "for a friend", "using my student ID", "before the deadline",
    )
    text = f"{rng.choice(openings)} {rng.choice(actions)} {rng.choice(qualifiers)}"
    return text, [], "unknown"


def _unknown_catalog_train(rng: random.Random) -> tuple[str, list[dict], str]:
    """Hard negatives contain catalog words but request unsupported actions."""
    faculty = _faculty(rng).text
    course = _course(rng, "FILTER_COURSE").text
    text = rng.choice((
        f"Email {faculty} about the {course} assignment",
        f"Send a message to {faculty} regarding {course}",
        f"Download the course outline for {course}",
    ))
    return text, [], "unknown"


def _unknown_catalog_validation(rng: random.Random) -> tuple[str, list[dict], str]:
    section = _section(rng, "FILTER_SECTION").text
    day = _day(rng).text
    text = rng.choice((
        f"Reserve a classroom for {section} on {day}",
        f"Mark attendance for {section} this {day}",
        f"Move the {section} exam to {day}",
    ))
    return text, [], "unknown"


def _unknown_catalog_test(rng: random.Random) -> tuple[str, list[dict], str]:
    faculty = _faculty(rng).text
    section = _section(rng, "FILTER_SECTION").text
    course = _course(rng, "FILTER_COURSE").text
    text = rng.choice((
        f"Ask {faculty} to upload marks for {section}",
        f"Can {faculty} share the {course} slides",
        f"Submit an attendance correction for {section} in {course}",
    ))
    return text, [], "unknown"


FAMILIES: dict[str, tuple[str, Builder]] = {
    "base_plain_train": ("train", _base_plain),
    "base_day_train": ("train", _base_day),
    "filter_course_train": ("train", _filter_course),
    "filter_course_validation": ("validation", _filter_course_validation),
    "filter_course_day_test": ("test", _filter_course_day),
    "section_pair_days_validation": ("validation", _section_pair_days),
    "base_add_one_train": ("train", _base_add_one),
    "base_add_one_polite_validation": ("validation", _base_add_one_polite),
    "base_add_two_train": ("train", _base_add_two),
    "base_add_section_first_train": ("train", _base_add_section_first_train),
    "base_add_possessive_train": ("train", _base_add_possessive_train),
    "base_add_section_pairs_train": ("train", _base_add_section_pairs_train),
    "base_add_two_reordered_test": ("test", _base_add_two_reordered),
    "base_exclude_train": ("train", _base_exclude),
    "base_exclude_add_test": ("test", _base_exclude_add),
    "base_exclude_validation": ("validation", _base_exclude_validation),
    "base_exclude_two_train": ("train", _base_exclude_two_train),
    "base_add_then_exclude_train": ("train", _base_add_then_exclude_train),
    "base_exclude_two_reordered_test": ("test", _base_exclude_two_test),
    "availability_train": ("train", _availability),
    "availability_day_train": ("train", _availability_day),
    "availability_validation": ("validation", _availability_validation),
    "availability_two_days_test": ("test", _availability_two_days),
    "availability_two_people_train": ("train", _availability_two_people_train),
    "availability_two_people_reordered_test": ("test", _availability_two_people_test),
    "faculty_schedule_train": ("train", _faculty_schedule),
    "faculty_schedule_day_validation": ("validation", _faculty_schedule_day),
    "faculty_schedule_day_first_train": ("train", _faculty_schedule_day_first_train),
    "availability_day_first_train": ("train", _availability_day_first_train),
    "faculty_schedule_reordered_test": ("test", _faculty_schedule_test),
    "faculty_course_train": ("train", _faculty_course_train),
    "faculty_course_reordered_train": ("train", _faculty_course_reordered_train),
    "faculty_course_reordered_test": ("test", _faculty_course_test),
    "class_type_train": ("train", _class_type),
    "credits_train": ("train", _credits_train),
    "credits_reordered_train": ("train", _credits_reordered_train),
    "credits_validation": ("validation", _credits_validation),
    "credits_reordered_test": ("test", _credits_test),
    "time_filter_train": ("train", _time_filter_train),
    "time_filter_validation": ("validation", _time_filter_validation),
    "time_filter_test": ("test", _time_filter_test),
    "unknown_train": ("train", _unknown),
    "unknown_catalog_train": ("train", _unknown_catalog_train),
    "unknown_validation": ("validation", _unknown),
    "unknown_catalog_validation": ("validation", _unknown_catalog_validation),
    "unknown_test": ("test", _unknown),
    "unknown_catalog_test": ("test", _unknown_catalog_test),
}


def generate_examples(total: int = 18_000, seed: int = 41) -> list[dict]:
    """Create a deterministic, unique corpus with family-isolated splits."""
    if total < len(FAMILIES) * 8:
        raise ValueError(f"total must be at least {len(FAMILIES) * 8}")
    families_by_split = {
        split: [(family, builder) for family, (assigned, builder) in FAMILIES.items() if assigned == split]
        for split in ("train", "validation", "test")
    }
    targets = {
        "train": int(total * 0.78),
        "validation": int(total * 0.11),
    }
    targets["test"] = total - targets["train"] - targets["validation"]

    records: list[dict] = []
    seen: set[str] = set()
    for split, target in targets.items():
        rng = random.Random(f"{seed}:{split}")
        families = families_by_split[split]
        family_index = 0
        attempts = 0
        split_count = 0
        while split_count < target:
            family, builder = families[family_index % len(families)]
            family_index += 1
            text, entities, intent = builder(rng)
            attempts += 1
            key = text.casefold()
            if key in seen:
                if attempts > target * 200:
                    raise RuntimeError(f"Could not generate {target} unique {split} examples")
                continue
            seen.add(key)
            records.append({
                "id": f"nlu-{len(records) + 1:06d}",
                "text": text,
                "intent": intent,
                "entities": entities,
                "family": family,
                "split": split,
            })
            split_count += 1
    random.Random(f"{seed}:shuffle").shuffle(records)
    return records


def write_jsonl(records: Iterable[dict], destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(source: str | Path) -> list[dict]:
    with Path(source).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
