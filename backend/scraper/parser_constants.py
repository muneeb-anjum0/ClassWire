"""Regular expressions and token sets used by timetable parsing."""

import re

COURSE_CODE_TOKEN_RE = re.compile(r"^[A-Z]{2,6}$")

COURSE_CODE_VALUE_RE = re.compile(r"^(?:\d{2,4}[A-Z]?|[A-Z]{1,4}\d{1,4}|\d{3,4})$", re.IGNORECASE)

COURSE_CODE_SINGLE_RE = re.compile(r"^[A-Z]{2,6}\d{2,4}$")

NAME_PREFIXES = {"DR.", "PROF.", "MR.", "MS.", "MRS.", "MISS."}

NAME_TOKEN_RE = re.compile(r"^(?:[A-Z]\.|[A-Z][A-Za-z.'-]*|[A-Z]{2,})$")

NAME_CONNECTORS = {"ul", "al", "bin", "bint", "e"}

NON_PERSON_TOKENS = {
    "ROOM",
    "HALL",
    "LAB",
    "BLOCK",
    "CAMPUS",
    "STUDIO",
    "DIGITAL",
    "MEDIA",
    "MEETING",
    "ADMIN",
    "ORIC",
    "PSY",
}

ROOM_PREFIX_STOPWORDS = {
    "AUDITORIUM",
    "CANCELLED",
    "CANCELED",
    "CONFERENCE",
    "HALL",
    "LAB",
    "MEETING",
    "ONLINE",
    "ROOM",
    "VIRTUAL",
}

FACULTY_KEYWORDS = {"INSTRUCTOR", "INSTRUCTORS", "FACULTY", "PROFESSOR", "PROF", "DOCTOR", "LECTURER", "TRAINER", "TUTOR", "FACILITATOR", "EXTERNAL"}

COURSE_KEYWORDS = {"WORKSHOP", "COURSE", "DEVELOPMENT", "MANAGEMENT", "COMMUNICATION", "TECHNIQUES", "ANALYSIS", "PRACTICE", "RESEARCH", "ELECTIVES", "UNDERSTANDING", "QURAN", "HOLY"}

COURSE_CREDITS_RE = re.compile(r"\s*\(\d+\s*,\s*\d+\)\s*$")

COURSE_CREDITS_SUFFIX_RE = re.compile(r"\s*\(\d+\s*,\s*\d+\)\s*[A-Z]\s*$")

FACULTY_SUFFIX_STOPWORDS = {
    "ACADEMIC",
    "ACCOUNTING",
    "ADVANCED",
    "ANALYTICS",
    "APPLIED",
    "ARCHITECTURE",
    "ART",
    "BUSINESS",
    "CIVIL",
    "COMMERCIAL",
    "COMMUNICATION",
    "COMPUTER",
    "DATA",
    "DEVELOPMENT",
    "DEVELOPMENTAL",
    "DESIGN",
    "DIFFERENTIAL",
    "ECONOMICS",
    "EDUCATION",
    "ENGINEERING",
    "FINANCE",
    "FINANCIAL",
    "FOUNDATIONS",
    "GENERAL",
    "GOVERNANCE",
    "GRAPH",
    "HISTORY",
    "HUMAN",
    "HUMANITIES",
    "INFORMATION",
    "INTERNATIONAL",
    "INTRODUCTION",
    "LAW",
    "LEADERSHIP",
    "MANAGEMENT",
    "MARKETING",
    "MATHEMATICAL",
    "MATHEMATICS",
    "NETWORKS",
    "PHILOSPHY",
    "PHILOSOPHY",
    "PRACTICES",
    "PRACTICE",
    "PROBABILITY",
    "PSYCHOLOGICAL",
    "PSYCHOLOGY",
    "TESTING",
    "RESEARCH",
    "RIGHTS",
    "SCIENCE",
    "SCIENCES",
    "SOCIAL",
    "SOFTWARE",
    "STATISTICS",
    "STUDIES",
    "SYSTEMS",
    "TECHNICAL",
    "TECHNIQUES",
    "THEORY",
    "VISUAL",
}

ROOM_HINT_RE = re.compile(
    r"\b(?:ONLINE|VIRTUAL|LAB|ROOM|HALL|AUDITORIUM|CONFERENCE|MEETING|ADMIN|BLOCK|LIBRARY|STUDIO|ORIC|TV|NB|OB|HB|CB|AIC)\b|\d",
    re.IGNORECASE,
)

SECTION_SUFFIX_PATTERNS = [
    re.compile(r"^[A-Z]{1,8}\s*\([A-Z0-9&/]+\)\s*(?:-\s*)?\d+\s*[A-Z]?$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s*\([A-Z0-9&/]+\)\s+\d+\s*[A-Z]?$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s*\(\d+\)\s*$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,12}\s*-\s*\d+\s*[A-Z]?$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,12}-\d+\s*[A-Z]?$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s+Open(?:\s*/\s*[A-Z]{1,8}\s+Open)*\s*$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s*-\s*[A-Z]{1,8}\s+Open(?:\s*/\s*[A-Z]{1,8}\s*-\s*[A-Z]{1,8}\s+Open)*\s*$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}(?:\s*/\s*[A-Z]{1,8})+\s+Open(?:\s*/\s*[A-Z]{1,8}\s+Open)*\s*$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s+\d+\s*/\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+\d+$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,8}\s+\d+\s*[A-Z]?$", re.IGNORECASE),
]
