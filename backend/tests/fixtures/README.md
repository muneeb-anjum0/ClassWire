# Timetable fixtures

Fixtures in this directory are intentionally small, anonymized, and reviewable.

`timetable_parser_examples.json` stores source HTML beside the exact normalized rows expected from the parser. It protects field alignment, section identity, faculty extraction, rooms, campuses, times, and parser diagnostics without requiring Gmail or Firestore access.

When adding a fixture:

1. Remove personal email addresses, message identifiers, and unrelated content.
2. Keep the smallest source fragment that reproduces the parser behavior.
3. Include exact expected fields rather than a broad row-count assertion.
4. Give the case a name that explains the layout or failure mode.
5. Add a new case instead of weakening an existing expectation.
