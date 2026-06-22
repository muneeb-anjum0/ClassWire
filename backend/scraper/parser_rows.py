from __future__ import annotations

import html as html_module
import logging
import re
from typing import List, Optional, Tuple

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


def parse_html_table_rows(html: str) -> List[Tuple[int, str]]:
    """Extract rows from the first timetable-like HTML table as tab-separated text."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    for table in soup.find_all("table"):
        text = table.get_text(" ")
        if "Sr No" not in text and "sr no" not in text.lower():
            continue

        rows: List[Tuple[int, str]] = []
        serial = 1
        for tr in table.find_all("tr"):
            cells = [
                collapse_whitespace(cell.get_text(" "))
                for cell in tr.find_all(["td", "th"], recursive=False)
            ]
            if not cells:
                continue

            first = cells[0]
            if re.fullmatch(r"\d{1,4}", first):
                try:
                    serial = int(first)
                except Exception:
                    pass
                row_text = "\t".join(cells[1:])
            else:
                row_text = "\t".join(cells)

            if re.fullmatch(r"(?i)sr\s*no|department|program|section|course|venue|time|campus", first.strip()):
                continue

            rows.append((serial, row_text))
            serial += 1

        if rows:
            return rows

    return []


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
