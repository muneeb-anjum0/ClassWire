"""Public timetable parsing interface."""

from typing import Dict, List, Optional

from .parser_fields import _semester_matches_filters
from .parser_items import _build_item
from .parser_rows import (
    html_to_text as _html_to_text,
    iter_row_blocks as _iter_row_blocks,
    iter_row_blocks_fallback as _iter_row_blocks_fallback,
    parse_html_table_rows as _parse_html_table_rows,
)

def parse_html_with_advanced_pandas(html: str, allowed_semesters: Optional[List[str]] = None) -> List[Dict]:
    """Parse a timetable email body into structured schedule items.

    The legacy function name is preserved for compatibility with the rest of
    the backend, but the implementation no longer depends on tables or pandas.
    """
    if not html:
        return []

    # Prefer parsing actual HTML tables when present because many emails use
    # table-based layout (cells correspond to columns). This produces robust
    # tab-separated rows which the structured parser can consume reliably.
    table_rows = _parse_html_table_rows(html)
    # Always convert HTML to plain text early; some fallback logic needs it.
    text = _html_to_text(html)
    if table_rows:
        row_blocks = table_rows
    else:
        row_blocks = _iter_row_blocks(text)
    if not row_blocks:
        fallback = _iter_row_blocks_fallback(text)
        if not fallback:
            return []
        row_blocks = fallback
    else:
        if "<table" in html.lower() or "<td" in html.lower():
            fallback = _iter_row_blocks_fallback(text)
            if fallback and len(fallback) > len(row_blocks):
                row_blocks = fallback

    expand_sections = bool(table_rows)
    items: List[Dict] = []
    for serial_no, row_text in row_blocks:
        item = _build_item(serial_no, row_text, expand_sections=expand_sections)
        candidates = item if isinstance(item, list) else [item]
        for cand in candidates:
            if _semester_matches_filters(
                [
                    str(cand.get("semester", "")),
                    str(cand.get("semester_display", "")),
                    str(cand.get("semester_original", "")),
                ],
                allowed_semesters,
            ):
                items.append(cand)

    return items

class AdvancedTableParser:
    """Compatibility wrapper used by older debug helpers.

    The parser no longer extracts HTML tables. It now returns structured row
    dictionaries from the plain-text timetable bulletin.
    """

    def extract_tables_from_html(self, html: str):
        return parse_html_with_advanced_pandas(html)
