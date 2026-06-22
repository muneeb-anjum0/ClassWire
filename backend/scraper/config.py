import logging
import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)

# Load only the backend's local file. Deployment variables always take precedence.
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)

def _clean(v: str | None, default: str = "") -> str:
    v = (v or "").strip()
    if not v:
        return default
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v

class Settings(BaseModel):
    tz: str = Field(default_factory=lambda: _clean(os.getenv("TZ"), "Asia/Karachi"))
    gmail_query_base: str = Field(
        default_factory=lambda: _clean(os.getenv("GMAIL_QUERY_BASE"),
                                       'subject:("Class Schedule" OR schedule) in:inbox')
    )
    check_hour_local: int = Field(default_factory=lambda: int(_clean(os.getenv("CHECK_HOUR_LOCAL"), "20")))
    check_minute_local: int = Field(default_factory=lambda: int(_clean(os.getenv("CHECK_MINUTE_LOCAL"), "0")))
    # Hour when next day's timetable becomes available (24-hour format)
    next_day_available_hour: int = Field(default_factory=lambda: int(_clean(os.getenv("NEXT_DAY_AVAILABLE_HOUR"), "17")))
    newer_than_days: int = Field(default_factory=lambda: int(_clean(os.getenv("NEWER_THAN_DAYS"), "2")))
    # Parse semesters directly instead of using validator
    allowed_semesters: List[str] = Field(default_factory=lambda: _parse_semesters_direct())
    # Additional parsing controls
    min_line_length: int = Field(default_factory=lambda: int(_clean(os.getenv("MIN_LINE_LENGTH"), "15")))
    max_results_per_semester: int = Field(default_factory=lambda: int(_clean(os.getenv("MAX_RESULTS_PER_SEMESTER"), "50")))
    debug_parsing: bool = Field(default_factory=lambda: _clean(os.getenv("DEBUG_PARSING"), "false").lower() == "true")

def _parse_semesters_direct():
    """
    Parse semesters from environment variable.
    Supports multiple formats:
    - Single: "BS (SE) - 5C"
    - Multiple: "BS (SE) - 5C, BS (CS) - 7A, MS (CS) - 1B"
    - Mixed: "5C, 7A, BS (SE) - 3B"
    """
    raw = _clean(os.getenv("ALLOWED_SEMESTERS"))
    if not raw:
        LOGGER.warning("No ALLOWED_SEMESTERS configured. Set this in .env file.")
        LOGGER.info("Example: ALLOWED_SEMESTERS=BS (SE) - 5C, BS (CS) - 7A")
        return []
    
    # Split by comma and clean each semester
    semesters = []
    for sem in raw.split(","):
        sem = sem.strip()
        if sem:
            semesters.append(sem)
    
    LOGGER.debug(f"Loaded {len(semesters)} semester filter(s): {semesters}")
    return semesters

settings = Settings()
