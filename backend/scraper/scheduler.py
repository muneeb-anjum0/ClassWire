import json
import logging
import os
import sys
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

# Add parent directory to path for absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from dateutil import tz
from google.auth.transport.requests import Request as GoogleAuthRequest

from core.ttl_cache import TTLCache
from core.telemetry import increment, observe

from .gmail_client import (
    build_service,
    get_credentials,
    get_message_html,
    get_message_html_from_message,
    get_messages_batch,
    list_latest_messages_batch,
    list_messages,
)
from .timetable_parser import (
    TIMETABLE_PARSER_VERSION,
    parse_html_with_advanced_pandas,
    parse_html_with_diagnostics,
)

LOGGER = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_GMAIL_IDENTITY_CACHE = TTLCache[str, str](ttl_seconds=3600, max_entries=256)
PUBLIC_ITEM_FIELDS = (
    "row_number",
    "semester",
    "semester_key",
    "semester_display",
    "section",
    "class_section",
    "course",
    "course_title",
    "course_code",
    "course_type",
    "faculty",
    "room",
    "time",
    "campus",
    "schedule_day",
)

def _normalize_subject(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

def _filter_subject_items(items, subject_filters):
    needles = [_normalize_subject(value) for value in subject_filters]
    needles = [value for value in needles if value]
    if not needles:
        return items
    matched = []
    for item in items:
        fields = [item.get("course_code"), item.get("course_title"), item.get("course")]
        normalized_fields = [_normalize_subject(value) for value in fields if value]
        if any(needle in field or field in needle for needle in needles for field in normalized_fields):
            matched.append(item)
    return matched

def _filter_faculty_items(items, faculty_filters):
    needles = [_normalize_subject(value) for value in faculty_filters]
    needles = [value for value in needles if value]
    if not needles:
        return items
    return [
        item for item in items
        if any(needle in _normalize_subject(item.get("faculty")) for needle in needles)
    ]


def _apply_item_filters(items, filter_mode, subject_filters, faculty_filters):
    if filter_mode == "subjects":
        return _filter_subject_items(items, subject_filters)
    if filter_mode == "faculty":
        return _filter_faculty_items(items, faculty_filters)
    return items


def _compact_items(items):
    """Strip parser-only diagnostics before network and Firestore persistence."""
    return [
        {
            field: item[field]
            for field in PUBLIC_ITEM_FIELDS
            if item.get(field) not in (None, "", [])
        }
        for item in items
    ]


def _summarize(items):
    semester_counts = {}
    for item in items:
        semester = item.get("semester_display") or item.get("semester") or "Unknown"
        semester_counts[semester] = semester_counts.get(semester, 0) + 1
    return {
        "total_items": len(items),
        "semester_breakdown": semester_counts,
        "unique_courses": len(
            {item.get("course_code") or item.get("course") for item in items if item.get("course_code") or item.get("course")}
        ),
        "unique_faculty": len({item.get("faculty") for item in items if item.get("faculty")}),
    }


def _items_by_weekday(source: Optional[Dict]) -> Dict[str, list]:
    grouped = {day: [] for day in WEEKDAY_NAMES[:6]}
    for item in (source or {}).get("items", []):
        day = item.get("schedule_day")
        if day in grouped:
            grouped[day].append(dict(item))
    return grouped


def _message_received_at(message: Optional[Dict]) -> Optional[str]:
    value = (message or {}).get("internalDate")
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=tz.UTC).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None

def _target_day_name(now_local: datetime, next_day_available_hour: int = 17) -> str:
    """
    Determine which day's timetable to look for based on current time.
    
    Logic:
    - If it's after the configured hour (default 5 PM/17:00), look for tomorrow's timetable
    - If it's before that hour, look for today's timetable
    
    This is because the next day's timetable becomes available 
    between 5-11 PM on the previous day.
    
    Args:
        now_local: Current local datetime
        next_day_available_hour: Hour when next day's timetable becomes available (24-hour format)
    """
    if now_local.hour >= next_day_available_hour:
        tomorrow = now_local + timedelta(days=1)
        return WEEKDAY_NAMES[tomorrow.weekday()]
    else:
        return WEEKDAY_NAMES[now_local.weekday()]

def _target_date(now_local: datetime, next_day_available_hour: int = 17) -> datetime:
    """
    Get the target date that corresponds to the day we're looking for.
    
    Args:
        now_local: Current local datetime
        next_day_available_hour: Hour when next day's timetable becomes available (24-hour format)
    """
    if now_local.hour >= next_day_available_hour:
        # Target tomorrow's date
        return now_local + timedelta(days=1)
    else:
        # Target today's date
        return now_local

def _build_query(base: str, day_name: str, newer_than_days: Optional[int] = None) -> str:
    # Some schedule emails visually contain "for Tuesday", but Gmail's index
    # splits that phrase across HTML nodes. Match the weekday in the subject as
    # the reliable path and retain the body phrase as a fallback.
    age_filter = f" newer_than:{newer_than_days}d" if newer_than_days is not None else ""
    return f'{base} {{subject:{day_name} "for {day_name}"}}{age_filter} -in:trash'


def _build_week_query(base: str, newer_than_days: Optional[int] = None) -> str:
    alternatives = " ".join(
        [*(f"subject:{day}" for day in WEEKDAY_NAMES[:6]), *(f'"for {day}"' for day in WEEKDAY_NAMES[:6])]
    )
    age_filter = f" newer_than:{newer_than_days}d" if newer_than_days is not None else ""
    return f"{base} {{{alternatives}}}{age_filter} -in:trash"


def _latest_messages_by_weekday(
    service,
    user_email: str,
    gmail_query_base: str,
    day_names: Iterable[str],
) -> Dict[str, Dict]:
    """Find each weekday's newest available email in one HTTP batch.

    Gmail returns message searches newest-first. Independent, unbounded
    weekday queries therefore let today's new Monday schedule coexist with
    the latest available Tuesday schedule from an older week, without a
    second round trip or an arbitrary age cut-off.
    """
    days = list(day_names)
    queries = {
        day_name: _build_query(gmail_query_base, day_name)
        for day_name in days
    }
    return list_latest_messages_batch(service, user_email, queries)


def _day_from_subject(subject: str) -> Optional[str]:
    lowered = subject.casefold()
    return next((day for day in WEEKDAY_NAMES[:6] if re.search(rf"\b{day.casefold()}\b", lowered)), None)

def _next_date_for_day(now_local: datetime, day_name: str) -> datetime:
    target_weekday = WEEKDAY_NAMES.index(day_name)
    return now_local + timedelta(days=(target_weekday - now_local.weekday()) % 7)

def _save_json(doc: Dict, folder: str = "data/cache") -> str:
    """Legacy function - still used for backward compatibility"""
    os.makedirs(folder, exist_ok=True)
    date_str = doc.get("for_date") or datetime.now().date().isoformat()
    path = os.path.join(folder, f"schedule_{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    meta_path = os.path.join(folder, "last_checked.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_message_id": doc.get("message_id"),
                "last_run_at": datetime.utcnow().isoformat() + "Z",
                "query_used": doc.get("query"),
                "for_day": doc.get("for_day"),
                "for_date": doc.get("for_date"),
                "items_found": len(doc.get("items", [])),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return path

def run_once(user_email: str = "me", show_table: bool = False, user_id: Optional[str] = None, user_settings: Optional[Dict] = None) -> Dict:
    """
    Run the scraper once for a specific user.
    
    Args:
        user_email: Gmail user email (for Gmail API)
        show_table: Kept for legacy callers; the web app uses JSON responses.
        user_id: Firestore user ID for storing results
        user_settings: User-specific settings (overrides global settings)
    """
    from .config import settings
    
    try:
        allowed_semesters = user_settings.get('allowed_semesters', settings.allowed_semesters) if user_settings else settings.allowed_semesters
        filter_mode = user_settings.get('filter_mode', 'semesters') if user_settings else 'semesters'
        subject_filters = user_settings.get('subject_filters', []) if user_settings else []
        faculty_filters = user_settings.get('faculty_filters', []) if user_settings else []
        parser_semesters = allowed_semesters if filter_mode == 'semesters' else None
        gmail_query_base = user_settings.get('gmail_query_base', settings.gmail_query_base) if user_settings else settings.gmail_query_base
        timezone = user_settings.get('timezone', settings.tz) if user_settings else settings.tz
        next_day_available_hour = user_settings.get('next_day_available_hour', settings.next_day_available_hour) if user_settings else settings.next_day_available_hour
        timetable_day = user_settings.get('timetable_day', 'Auto') if user_settings else 'Auto'
        should_save_cache = user_settings.get('_save_cache', True) if user_settings else True
        previous_source = user_settings.get('_previous_source') if user_settings else None
        
        local_tz = tz.gettz(timezone)
        now_local = datetime.now(tz=local_tz)
        automatic_day = _target_day_name(now_local, next_day_available_hour)
        for_day_name = automatic_day if timetable_day == 'Auto' else timetable_day
        target_date = _target_date(now_local, next_day_available_hour) if timetable_day == 'Auto' else now_local
        if timetable_day not in ('Auto', 'Entire Week'):
            target_date = _next_date_for_day(now_local, timetable_day)

        query = (_build_query(gmail_query_base, for_day_name)
                 if timetable_day != 'Entire Week' else
                 _build_week_query(gmail_query_base))

        LOGGER.info("Looking for: %s  (local: %s)", for_day_name, now_local.strftime("%Y-%m-%d %H:%M"))
        LOGGER.info("Gmail query: %s", query)

        if user_id:
            try:
                from database.firestore_store import data_store
                token_data = data_store.get_user_tokens(user_id)
                if token_data:
                    from google.oauth2.credentials import Credentials
                    
                    expiry = None
                    if token_data.get('expiry'):
                        try:
                            expiry = datetime.fromisoformat(token_data['expiry'].replace('Z', '+00:00'))
                        except Exception:
                            expiry = None
                    
                    creds = Credentials(
                        token=token_data.get('token'),
                        refresh_token=token_data.get('refresh_token'),
                        token_uri=token_data.get('token_uri'),
                        client_id=token_data.get('client_id'),
                        client_secret=token_data.get('client_secret'),
                        scopes=token_data.get('scopes'),
                        expiry=expiry
                    )
                    # google-api-python-client refreshes expired access tokens
                    # in memory, but does not persist the replacement. Without
                    # this, every later scrape refreshes the same stale token.
                    if creds.expired and creds.refresh_token:
                        creds.refresh(GoogleAuthRequest())
                        data_store.save_user_tokens(
                            user_id,
                            {
                                "token": creds.token,
                                "refresh_token": creds.refresh_token,
                                "token_uri": creds.token_uri,
                                "client_id": creds.client_id,
                                "client_secret": creds.client_secret,
                                "scopes": creds.scopes,
                                "expiry": creds.expiry.isoformat() if creds.expiry else None,
                            },
                        )
                else:
                    raise RuntimeError(
                        f"Gmail authorization is missing for {user_email}. "
                        "Sign out, then sign in with that Google account again."
                    )
            except RuntimeError:
                raise
            except Exception as error:
                raise RuntimeError(
                    f"Could not load Gmail authorization for {user_email}. "
                    "Sign out, then reconnect that Google account."
                ) from error
        else:
            creds = get_credentials()

        service = build_service(creds)
        if user_id and user_email and user_email != "me":
            authorized_email = _GMAIL_IDENTITY_CACHE.get(user_id)
            if authorized_email is None:
                profile = service.users().getProfile(userId="me").execute()
                authorized_email = str(profile.get("emailAddress") or "").strip().lower()
                _GMAIL_IDENTITY_CACHE.set(user_id, authorized_email)
            expected_email = str(user_email).strip().lower()
            if authorized_email != expected_email:
                raise RuntimeError(
                    f"Gmail authorization belongs to {authorized_email or 'another account'}, "
                    f"not {expected_email}. Sign out and reconnect {expected_email}."
                )
        if timetable_day == 'Entire Week':
            items = []
            message_ids = []
            latest_by_day = _latest_messages_by_weekday(
                service,
                user_email,
                gmail_query_base,
                WEEKDAY_NAMES[:6],
            )
            previous_ids = (previous_source or {}).get("message_ids_by_day") or {}
            previous_items = _items_by_weekday(previous_source)
            can_reuse_previous = (
                isinstance(previous_source, dict)
                and previous_source.get("parser_version") == TIMETABLE_PARSER_VERSION
            )
            changed_days = [
                day for day in WEEKDAY_NAMES[:6]
                if (latest_by_day.get(day) or {}).get("id")
                and (
                    not can_reuse_previous
                    or previous_ids.get(day) != (latest_by_day.get(day) or {}).get("id")
                )
            ]
            candidate_ids = [
                (latest_by_day.get(day) or {}).get("id")
                for day in changed_days
                if (latest_by_day.get(day) or {}).get("id")
            ]
            fetched = get_messages_batch(service, user_email, candidate_ids)
            increment("gmail.messages_fetched", len(candidate_ids))
            message_ids_by_day = {}
            received_at_by_day = dict((previous_source or {}).get("source_received_at_by_day") or {})
            parser_diagnostics = {}

            for day_name in WEEKDAY_NAMES[:6]:
                selected = latest_by_day.get(day_name) or {}
                message_id = selected.get("id")
                if not message_id:
                    continue
                message_ids.append(message_id)
                message_ids_by_day[day_name] = message_id
                if can_reuse_previous and previous_ids.get(day_name) == message_id:
                    day_items = previous_items.get(day_name, [])
                    parser_diagnostics[day_name] = {
                        "parser_version": TIMETABLE_PARSER_VERSION,
                        "accepted_rows": len(day_items),
                        "reused": True,
                    }
                else:
                    message = fetched.get(message_id)
                    if not message:
                        continue
                    received_at_by_day[day_name] = _message_received_at(message)
                    html = get_message_html_from_message(message) or ""
                    parser_started = time.perf_counter()
                    day_items, diagnostics = parse_html_with_diagnostics(html, parser_semesters)
                    observe("parser.timetable", (time.perf_counter() - parser_started) * 1000)
                    increment("parser.rows_accepted", diagnostics.get("accepted_rows", 0))
                    increment(
                        "parser.rows_rejected",
                        diagnostics.get("rejected_missing_identity", 0)
                        + diagnostics.get("rejected_missing_time", 0),
                    )
                    day_items = _apply_item_filters(day_items, filter_mode, subject_filters, faculty_filters)
                    parser_diagnostics[day_name] = {**diagnostics, "reused": False}
                for item in day_items:
                    item["schedule_day"] = day_name
                items.extend(day_items)

            items = _compact_items(items)
            doc = {
                "for_day": "Entire Week", "for_date": now_local.date().isoformat(),
                "query": query, "message_id": message_ids[0] if message_ids else None,
                "message_ids": message_ids, "items": items, "semesters": allowed_semesters,
                "message_ids_by_day": message_ids_by_day,
                "source_received_at_by_day": received_at_by_day,
                "parser_version": TIMETABLE_PARSER_VERSION,
                "parser_diagnostics": parser_diagnostics,
                "refresh": {
                    "changed_days": changed_days,
                    "reused_days": [day for day in message_ids_by_day if day not in changed_days],
                    "fetched_messages": len(candidate_ids),
                },
                "summary": _summarize(items),
            }
            if user_id and should_save_cache:
                from database.firestore_store import data_store
                data_store.save_timetable_cache(user_id, doc)
            elif not user_id and should_save_cache:
                _save_json(doc)
            return {"success": True, "data": doc, "message": f"Successfully found {len(items)} items for the week"}

        msgs = list_messages(service, user_id=user_email, query=query, max_results=1)
        
        if not msgs:
            LOGGER.warning("No messages found for target date")
            doc = {
                "for_day": for_day_name,
                "for_date": target_date.date().isoformat(),
                "query": query,
                "message_id": None,
                "items": [],
                "semesters": allowed_semesters,
                "summary": {
                    "total_items": 0,
                    "semester_breakdown": {},
                    "unique_courses": 0,
                    "unique_faculty": 0,
                }
            }
            
            # Save to Firestore if user_id provided, otherwise use local storage
            if user_id and should_save_cache:
                from database.firestore_store import data_store
                data_store.save_timetable_cache(user_id, doc)
            elif not user_id and should_save_cache:
                _save_json(doc)
                
            return {"success": True, "data": doc, "message": "No messages found for today"}

        msg_id = msgs[0]["id"]
        html = get_message_html(service, user_id=user_email, msg_id=msg_id) or ""
        
        items = _compact_items(
            _apply_item_filters(
                parse_html_with_advanced_pandas(html, parser_semesters),
                filter_mode,
                subject_filters,
                faculty_filters,
            )
        )

        doc = {
            "for_day": for_day_name,
            "for_date": target_date.date().isoformat(),
            "query": query,
            "message_id": msg_id,
            "items": items,
            "semesters": allowed_semesters,
            "summary": _summarize(items),
        }
        
        if user_id and should_save_cache:
            from database.firestore_store import data_store
            data_store.save_timetable_cache(user_id, doc)
        elif not user_id and should_save_cache:
            _save_json(doc)
        
        summary = doc.get("summary", {})
        LOGGER.info(f"Successfully parsed {summary['total_items']} items for date {target_date.date()}")
        
        return {"success": True, "data": doc, "message": f"Successfully found {len(items)} items"}
    
    except Exception as e:
        LOGGER.error(f"Scraper error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
