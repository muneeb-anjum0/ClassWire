"""Public timetable parsing interface."""

import re
from typing import Dict, List, Optional

from .parser_fields import _semester_matches_filters
from .parser_items import _build_item
from .parser_rows import (
    html_to_text as _html_to_text,
    iter_row_blocks as _iter_row_blocks,
    iter_row_blocks_fallback as _iter_row_blocks_fallback,
    parse_html_table_rows as _parse_html_table_rows,
)

TIMETABLE_PARSER_VERSION = 2


def parse_html_with_diagnostics(
    html: str,
    allowed_semesters: Optional[List[str]] = None,
) -> tuple[List[Dict], Dict[str, int]]:
    """Parse a bulletin and return cheap, privacy-safe quality counters.

    The counters deliberately contain no timetable text. They make parser
    regressions observable without logging courses, faculty, or user data.
    """
    diagnostics = {
        "parser_version": TIMETABLE_PARSER_VERSION,
        "candidate_rows": 0,
        "accepted_rows": 0,
        "duplicate_rows": 0,
        "rejected_missing_identity": 0,
        "rejected_missing_time": 0,
        "rejected_semester_filter": 0,
    }
    if not html:
        return [], diagnostics
    items = _parse_html(html, allowed_semesters, diagnostics)
    return items, diagnostics


def parse_html_with_advanced_pandas(html: str, allowed_semesters: Optional[List[str]] = None) -> List[Dict]:
    """Parse a timetable email body into structured schedule items.

    The legacy function name is preserved for compatibility with the rest of
    the backend, but the implementation no longer depends on tables or pandas.
    """
    items, _ = parse_html_with_diagnostics(html, allowed_semesters)
    return items


def _parse_html(html: str, allowed_semesters: Optional[List[str]], diagnostics: Dict[str, int]) -> List[Dict]:

    text = ""
    # Prefer parsing actual HTML tables when present because many emails use
    # table-based layout (cells correspond to columns). This produces robust
    # tab-separated rows which the structured parser can consume reliably.
    table_rows = _parse_html_table_rows(html)
    if table_rows:
        row_blocks = table_rows
    else:
        # BeautifulSoup is comparatively expensive. Only flatten the document
        # when structured table extraction did not already succeed.
        text = _html_to_text(html)
        row_blocks = _iter_row_blocks(text)
    if not row_blocks:
        fallback = _iter_row_blocks_fallback(text)
        if not fallback:
            return []
        row_blocks = fallback
    # Never replace valid structured rows merely because the flattened HTML
    # contains more newline fragments. Those fragments include headings,
    # addresses and footers and were the source of phantom classes.

    expand_sections = bool(table_rows)
    items: List[Dict] = []
    seen = set()
    for serial_no, row_text in row_blocks:
        item = _build_item(serial_no, row_text, expand_sections=expand_sections)
        candidates = item if isinstance(item, list) else [item]
        for cand in candidates:
            diagnostics["candidate_rows"] += 1
            # The heuristic path handles plain-text bulletins. Apply the same
            # minimum class invariant as the structured-table parser so email
            # addresses, campus directions and slot headings cannot leak in.
            if not cand.get("course_title") or not cand.get("semester_display"):
                diagnostics["rejected_missing_identity"] += 1
                continue
            if not re.search(
                r"\b\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\s*-\s*\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\b",
                str(cand.get("time") or ""),
                re.IGNORECASE,
            ):
                diagnostics["rejected_missing_time"] += 1
                continue
            if not cand.get("faculty"):
                cand["faculty"] = "TBD"
                cand["faculty_name"] = "TBD"
            identity = tuple(
                re.sub(r"\s+", " ", str(cand.get(field) or "")).strip().casefold()
                for field in ("semester_display", "course_code", "course_title", "faculty", "room", "time", "campus")
            )
            if identity in seen:
                diagnostics["duplicate_rows"] += 1
                continue
            if _semester_matches_filters(
                [
                    str(cand.get("semester", "")),
                    str(cand.get("semester_display", "")),
                    str(cand.get("semester_original", "")),
                ],
                allowed_semesters,
            ):
                items.append(cand)
                seen.add(identity)
                diagnostics["accepted_rows"] += 1
            else:
                diagnostics["rejected_semester_filter"] += 1

    return items

class AdvancedTableParser:
    """Compatibility wrapper used by older debug helpers.

    The parser no longer extracts HTML tables. It now returns structured row
    dictionaries from the plain-text timetable bulletin.
    """

    def extract_tables_from_html(self, html: str):
        return parse_html_with_advanced_pandas(html)
