"""Versioned label contract shared by dataset and model tooling."""

INTENTS = (
    "schedule",
    "faculty_availability",
    "faculty_schedule",
    "unknown",
)

ENTITY_ROLES = (
    "BASE_SECTION",
    "ADDED_SECTION",
    "ADDED_COURSE",
    "EXCLUDED_COURSE",
    "FILTER_SECTION",
    "FILTER_COURSE",
    "FACULTY",
    "DAY",
    "CLASS_TYPE",
    "CREDIT_HOURS",
    "TIME_RANGE",
)

SLOT_LABELS = ("O",) + tuple(
    label
    for role in ENTITY_ROLES
    for label in (f"B-{role}", f"I-{role}")
)
