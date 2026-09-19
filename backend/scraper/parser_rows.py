from __future__ import annotations

import html as html_module
import logging
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

ROW_START_RE = re.compile(r"^\s*(\d{1,3})\s+(.+\S)\s*$")
TIME_RE = re.compile(
    r"\b\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\s*-\s*\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\b",
    re.IGNORECASE,
)


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def html_to_text(value: str) -> str:
    if not value:
        return ""

    cleaned = html_module.unescape(value)
    if "<" in cleaned and ">" in cleaned:
        try:
            soup = BeautifulSoup(cleaned, "html.parser")
            cleaned = soup.get_text("\n")
        except Exception:
            LOGGER.debug("Falling back to raw text because BeautifulSoup parsing failed", exc_info=True)

    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")
    return cleaned


def _canonical_header(value: str) -> Optional[str]:
    compact = re.sub(r"[^a-z0-9#]+", "", value.casefold())
    if not compact:
        return None
    if compact in {"#", "no", "sno", "srno", "serial", "serialno", "serialnumber"}:
        return "serial"
    if "department" in compact or compact == "dept":
        return "department"
    if compact in {"program", "programme", "degree"}:
        return "program"
    if "section" in compact or compact in {"semester", "class", "classsection"}:
        return "section"
    if "course" in compact or compact in {"subject", "subjectname"}:
        return "course"
    if any(token in compact for token in ("faculty", "teacher", "instructor")):
        return "faculty"
    if "time" in compact or "timing" in compact:
        return "time"
    if "campus" in compact or compact in {"building", "branch"}:
        return "campus"
    if compact in {"room", "roomno", "venue", "location"}:
        return "room"
    return None


def _table_header_map(rows) -> Tuple[int, Dict[str, int]]:
    best_index = -1
    best_map: Dict[str, int] = {}
    for row_index, tr in enumerate(rows[:12]):
        cells = tr.find_all(["td", "th"], recursive=False)
        if not cells:
            continue
        mapping: Dict[str, int] = {}
        for cell_index, cell in enumerate(cells):
            canonical = _canonical_header(collapse_whitespace(cell.get_text(" ")))
            if canonical and canonical not in mapping:
                mapping[canonical] = cell_index
        if len(mapping) > len(best_map):
            best_index, best_map = row_index, mapping
    return best_index, best_map


def parse_html_table_rows(html: str) -> List[Tuple[int, str]]:
    """Extract and normalize timetable rows from one or more HTML tables.

    Source emails are not consistent about column order, serial-number columns,
    or whether a day is split over multiple tables. Header-driven extraction
    converts those variants into the parser's canonical eight-column layout.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    parsed_rows: List[Tuple[int, str]] = []
    seen_rows = set()
    generated_serial = 1
    canonical_fields = ("department", "program", "section", "course", "faculty", "room", "time", "campus")

    for table in soup.find_all("table"):
        table_rows = table.find_all("tr")
        header_index, header_map = _table_header_map(table_rows)
        has_core_headers = {"section", "course", "time"}.issubset(header_map)

        if has_core_headers:
            candidates = table_rows[header_index + 1:]
        else:
            # Preserve support for older bulletins that have the expected
            # positional columns but slightly unusual header labels.
            header_text = collapse_whitespace(table.get_text(" "))
            if not re.search(r"\b(?:sr\s*\.?\s*no|s\s*\.?\s*no|serial\s*(?:no|number))\b", header_text, re.I):
                continue
            candidates = table_rows

        for tr in candidates:
            cells = [
                collapse_whitespace(cell.get_text(" "))
                for cell in tr.find_all(["td", "th"], recursive=False)
            ]
            if not cells:
                continue

            if has_core_headers:
                values = {
                    field: cells[index] if index < len(cells) else ""
                    for field, index in header_map.items()
                }
                # Headings, slot banners, and footer rows do not satisfy this
                # invariant even when they use a full-width colspan.
                if not values.get("section") or not values.get("course") or not TIME_RE.search(values.get("time", "")):
                    continue
                serial_text = values.get("serial", "")
                serial = int(serial_text) if re.fullmatch(r"\d{1,4}", serial_text) else generated_serial
                row_text = "\t".join(values.get(field, "") for field in canonical_fields)
            else:
                first = cells[0]
                if not re.fullmatch(r"\d{1,4}", first):
                    continue
                serial = int(first)
                row_text = "\t".join(cells[1:])

            identity = collapse_whitespace(row_text).casefold()
            if identity in seen_rows:
                continue
            seen_rows.add(identity)
            parsed_rows.append((serial, row_text))
            generated_serial += 1

    return parsed_rows


def iter_row_blocks(text: str) -> List[Tuple[int, str]]:
    blocks: List[Tuple[int, str]] = []
    current_serial: Optional[int] = None
    current_lines: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = ROW_START_RE.match(line)
        if match:
            if current_serial is not None and current_lines:
                blocks.append((current_serial, "\n".join(current_lines).strip()))
            current_serial = int(match.group(1))
            current_lines = [match.group(2).lstrip()]
            continue

        if current_serial is not None:
            current_lines.append(line)

    if current_serial is not None and current_lines:
        blocks.append((current_serial, "\n".join(current_lines).strip()))

    return blocks


def iter_row_blocks_fallback(text: str) -> List[Tuple[int, str]]:
    """Split freeform text into row-like blocks when serial numbers are missing."""
    blocks: List[Tuple[int, str]] = []
    current_lines: List[str] = []
    serial_counter = 1

    def push_current() -> None:
        nonlocal serial_counter
        if not current_lines:
            return

        joined = "\n".join(current_lines).strip()
        noise_tokens = {"UNIVERSITY", "ISB", "CAMPUS", "SZABIST", "H-8/4", "H-8"}
        tokens = [token.strip().upper().strip(" ,.;:") for token in re.split(r"\s+", joined) if token.strip()]
        if tokens and set(tokens).issubset(noise_tokens):
            current_lines.clear()
            return

        blocks.append((serial_counter, joined))
        serial_counter += 1

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            push_current()
            current_lines = []
            continue

        if "\t" in line or re.search(r"\s{2,}", line):
            if current_lines:
                push_current()
                current_lines = []
            blocks.append((serial_counter, line.strip()))
            serial_counter += 1
            continue

        if TIME_RE.search(line):
            current_lines.append(line.strip())
            push_current()
            current_lines = []
            continue

        current_lines.append(line.strip())

    push_current()
    return blocks
