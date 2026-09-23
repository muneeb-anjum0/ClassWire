import os
from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv

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
    # Hour when next day's timetable becomes available (24-hour format)
    next_day_available_hour: int = Field(default_factory=lambda: int(_clean(os.getenv("NEXT_DAY_AVAILABLE_HOUR"), "17")))

settings = Settings()
