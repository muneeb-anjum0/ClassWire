"""User-facing data, config, scrape, and automation routes."""

from __future__ import annotations

import os
import re
import threading
import uuid
import time

from flask import Blueprint, current_app, jsonify, request

from core.authentication import authenticated_user
from core.rate_limit import TokenBucketRateLimiter
from core.ttl_cache import TTLCache
from core.telemetry import increment, observe

from .user_data_support import (
    build_manual_email_message,
    is_authorized_automation,
    merge_daily_email_status,
    timestamp_now,
)


EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def create_user_data_blueprint(*, logger, get_run_once, get_settings, get_store):
    blueprint = Blueprint("user_data", __name__)
    # The timetable emails change at most daily. Reuse the fully parsed weekly
    # source for normal searches; users can include "refresh", "latest", or
    # "update" to bypass this cache explicitly.
    search_source_cache = TTLCache[str, dict](ttl_seconds=1800, max_entries=128)
    # Query interpretation is deterministic for a given in-memory weekly
    # source. Reuse repeated searches (including browser retries and restored
    # recent searches) without repeating entity extraction and row matching.
    search_result_cache = TTLCache[tuple[str, str, int, str], dict](
        ttl_seconds=1800,
        max_entries=128,
    )
    refresh_locks = TTLCache[str, threading.Lock](ttl_seconds=3600, max_entries=256)
    refresh_locks_guard = threading.Lock()
    search_limiter = TokenBucketRateLimiter(capacity=10, refill_per_second=2)
    refresh_limiter = TokenBucketRateLimiter(capacity=2, refill_per_second=1 / 15)

    def refresh_lock_for(user_id: str) -> threading.Lock:
        with refresh_locks_guard:
            lock = refresh_locks.get(user_id)
            if lock is None:
                lock = threading.Lock()
                refresh_locks.set(user_id, lock)
            return lock

    def current_timestamp():
        return timestamp_now()

    def has_searchable_items(source) -> bool:
        return isinstance(source, dict) and isinstance(source.get("items"), list) and bool(source["items"])

    def get_user_from_request():
        return authenticated_user(get_store(), logger)

    def config_payload(user_settings):
        settings = get_settings()
        return {
            "gmail_query": user_settings.get("gmail_query_base", settings.gmail_query_base),
            "semester_filter": user_settings.get("allowed_semesters", settings.allowed_semesters),
            "filter_mode": user_settings.get("filter_mode", "semesters"),
            "subject_filters": user_settings.get("subject_filters", []),
            "faculty_filters": user_settings.get("faculty_filters", []),
            "timetable_day": user_settings.get("timetable_day", "Auto"),
            "personal_email": user_settings.get("personal_email", ""),
            "daily_email_enabled": user_settings.get("daily_email_enabled", bool(user_settings.get("personal_email"))),
            "daily_email_last_result": user_settings.get("daily_email_last_result"),
            "schedule_time": f"{settings.check_hour_local:02d}:{settings.check_minute_local:02d}",
            "timezone": user_settings.get("timezone", settings.tz),
            "max_results": getattr(settings, "max_results_per_semester", 50),
        }

    @blueprint.route("/api/config", methods=["GET"])
    def get_config():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            store = get_store()
            user_settings = store.get_user_settings(user["id"])
            return jsonify(config_payload(user_settings))
        except Exception as error:
            logger.error("Error loading config: %s", error)
            return jsonify({"error": str(error)}), 500

    @blueprint.route("/api/config/personal-email", methods=["POST", "OPTIONS"])
    def update_personal_email():
        if request.method == "OPTIONS":
            return "", 200

        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            payload = request.get_json(silent=True) or {}
            personal_email = (payload.get("personal_email") or "").strip()

            if personal_email and not EMAIL_PATTERN.fullmatch(personal_email):
                return jsonify({"success": False, "error": "Please enter a valid email address"}), 400

            store = get_store()
            current_settings = store.get_user_settings(user["id"])
            was_enabled = current_settings.get(
                "daily_email_enabled",
                bool(current_settings.get("personal_email")),
            )
            current_settings["personal_email"] = personal_email
            current_settings["daily_email_enabled"] = bool(personal_email) and bool(was_enabled)

            if not store.save_user_settings(user["id"], current_settings):
                return jsonify({"success": False, "error": "Failed to save personal email"}), 500

            return jsonify(
                {
                    "success": True,
                    "message": "Daily email recipient saved" if personal_email else "Daily email disabled",
                    "personal_email": personal_email,
                    "daily_email_enabled": current_settings["daily_email_enabled"],
                    "timestamp": current_timestamp(),
                }
            )
        except Exception as error:
            logger.error("Error updating personal email: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/config/daily-email-enabled", methods=["POST", "OPTIONS"])
    def update_daily_email_enabled():
        if request.method == "OPTIONS":
            return "", 200

        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            payload = request.get_json(silent=True) or {}
            enabled = bool(payload.get("daily_email_enabled"))
            store = get_store()
            current_settings = store.get_user_settings(user["id"])
            personal_email = (current_settings.get("personal_email") or "").strip()

            if enabled and not personal_email:
                return jsonify(
                    {
                        "success": False,
                        "error": "Save a personal email before enabling daily delivery",
                    }
                ), 400

            current_settings["daily_email_enabled"] = enabled
            if not store.save_user_settings(user["id"], current_settings):
                return jsonify({"success": False, "error": "Failed to update daily email setting"}), 500

            return jsonify(
                {
                    "success": True,
                    "message": "Daily email enabled" if enabled else "Daily email disabled",
                    "personal_email": personal_email,
                    "daily_email_enabled": enabled,
                    "timestamp": current_timestamp(),
                }
            )
        except Exception as error:
            logger.error("Error updating daily email setting: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/config/semesters", methods=["POST", "OPTIONS"])
    def update_semesters():
        if request.method == "OPTIONS":
            return "", 200

        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            payload = request.get_json(silent=True) or {}
            semesters = payload.get("semesters")
            if semesters is None:
                return jsonify({"error": "Missing semesters data"}), 400
            if not isinstance(semesters, list):
                return jsonify({"error": "Semesters must be a list"}), 400

            store = get_store()
            current_settings = store.get_user_settings(user["id"])
            current_settings["allowed_semesters"] = semesters

            if not store.save_user_settings(user["id"], current_settings):
                return jsonify({"error": "Failed to save settings"}), 500

            logger.info("Updated semesters for user %s: %s", user["email"], semesters)
            return jsonify(
                {
                    "success": True,
                    "message": f"Updated {len(semesters)} allowed semesters",
                    "semesters": semesters,
                }
            )
        except Exception as error:
            logger.error("Error updating semesters: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/config/discovery", methods=["POST", "OPTIONS"])
    def update_discovery():
        if request.method == "OPTIONS":
            return "", 200
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code
            payload = request.get_json(silent=True) or {}
            mode = payload.get("filter_mode", "semesters")
            semesters = payload.get("semesters", [])
            subjects = payload.get("subjects", [])
            faculty = payload.get("faculty", [])
            if mode not in {"semesters", "subjects", "faculty"}:
                return jsonify({"success": False, "error": "Invalid discovery mode"}), 400
            if not isinstance(semesters, list) or not isinstance(subjects, list) or not isinstance(faculty, list):
                return jsonify({"success": False, "error": "Filters must be lists"}), 400
            cleaned_semesters = [str(value).strip() for value in semesters if str(value).strip()]
            cleaned_subjects = [str(value).strip() for value in subjects if str(value).strip()]
            cleaned_faculty = [str(value).strip() for value in faculty if str(value).strip()]
            store = get_store()
            current_settings = store.get_user_settings(user["id"])
            current_settings.update({
                "filter_mode": mode,
                "allowed_semesters": cleaned_semesters,
                "subject_filters": cleaned_subjects,
                "faculty_filters": cleaned_faculty,
            })
            if not store.save_user_settings(user["id"], current_settings):
                return jsonify({"success": False, "error": "Failed to save discovery settings"}), 500
            return jsonify({
                "success": True,
                "filter_mode": mode,
                "semesters": cleaned_semesters,
                "subjects": cleaned_subjects,
                "faculty": cleaned_faculty,
                "message": f"Updated {len(cleaned_subjects if mode == 'subjects' else cleaned_faculty if mode == 'faculty' else cleaned_semesters)} filters",
            })
        except Exception as error:
            logger.error("Error updating discovery settings: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/config/timetable-day", methods=["POST", "OPTIONS"])
    def update_timetable_day():
        if request.method == "OPTIONS":
            return "", 200
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code
            day = (request.get_json(silent=True) or {}).get("timetable_day", "")
            allowed_days = {"Auto", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Entire Week"}
            if day not in allowed_days:
                return jsonify({"success": False, "error": "Invalid timetable day"}), 400
            store = get_store()
            current_settings = store.get_user_settings(user["id"])
            current_settings["timetable_day"] = day
            if not store.save_user_settings(user["id"], current_settings):
                return jsonify({"success": False, "error": "Failed to save timetable day"}), 500
            return jsonify({"success": True, "timetable_day": day, "message": f"Timetable day set to {day}"})
        except Exception as error:
            logger.error("Error updating timetable day: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/scrape", methods=["POST"])
    def scrape_now():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            if not current_app.testing and not refresh_limiter.allow(f"scrape:{user['id']}"):
                return jsonify({"success": False, "error": "Please wait before refreshing Gmail again"}), 429

            logger.info("Starting manual scrape for user %s", user["email"])

            force_refresh = request.json.get("force_refresh", False) if request.is_json else False
            if force_refresh:
                get_store().clear_user_cache(user["id"])

            store = get_store()
            result = get_run_once()(
                user_email=user["email"],
                show_table=False,
                user_id=user["id"],
                user_settings=store.get_user_settings(user["id"]),
            )

            if result and result.get("success"):
                search_source_cache.pop(user["id"])
                return jsonify(
                    {
                        "success": True,
                        "message": "Scrape completed successfully",
                        "data": result.get("data", []),
                        "timestamp": current_timestamp(),
                    }
                )

            return jsonify(
                {
                    "success": False,
                    "message": "Scrape failed or no data found",
                    "error": result.get("error") if result else "Unknown error",
                    "timestamp": current_timestamp(),
                }
            ), 400
        except Exception as error:
            logger.error("Error during scrape: %s", error)
            return jsonify(
                {
                    "success": False,
                    "error": str(error),
                    "timestamp": current_timestamp(),
                }
            ), 500

    @blueprint.route("/api/search", methods=["POST"])
    def smart_search():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code
            payload = request.get_json(silent=True) or {}
            query = str(payload.get("query") or "").strip()
            if len(query) < 2:
                return jsonify({"success": False, "error": "Enter a longer timetable question"}), 400
            if len(query) > 500:
                return jsonify({"success": False, "error": "Keep timetable questions under 500 characters"}), 400
            if not current_app.testing and not search_limiter.allow(f"search:{user['id']}"):
                return jsonify({"success": False, "error": "Too many searches; please wait a moment"}), 429

            store = get_store()
            force_source_refresh = bool(payload.get("force_refresh")) or bool(
                re.search(r"\b(?:refresh|latest|update)\b", query, re.IGNORECASE)
            )
            if force_source_refresh and not current_app.testing and not refresh_limiter.allow(f"search-refresh:{user['id']}"):
                return jsonify({"success": False, "error": "Please wait before refreshing Gmail again"}), 429
            cached_source = search_source_cache.get(user["id"])
            source_was_stale = False
            source_tier = "miss"
            if has_searchable_items(cached_source) and not force_source_refresh:
                source = cached_source
                source_tier = "memory"
            else:
                # Collapse simultaneous searches for the same user into one
                # Gmail scrape. Waiters reuse the source produced by the first.
                with refresh_lock_for(user["id"]):
                    cached_source = search_source_cache.get(user["id"])
                    if has_searchable_items(cached_source) and not force_source_refresh:
                        source = cached_source
                        source_tier = "memory_after_wait"
                    else:
                        persisted_source = None
                        if not force_source_refresh:
                            persisted_source = store.get_search_source_cache(user["id"], max_age_seconds=1800)
                        stale_source = persisted_source or store.get_search_source_cache(
                            user["id"],
                            max_age_seconds=None,
                        )
                        if has_searchable_items(persisted_source):
                            source = persisted_source
                            source_tier = "firestore"
                            search_source_cache.set(user["id"], source)
                        else:
                            search_settings = dict(store.get_user_settings(user["id"]))
                            search_settings.update({
                                "filter_mode": "subjects",
                                "subject_filters": [],
                                "timetable_day": "Entire Week",
                                "_save_cache": False,
                                "_previous_source": stale_source,
                            })
                            scrape_result = get_run_once()(
                                user_email=user["email"], user_id=user["id"],
                                user_settings=search_settings, show_table=False,
                            )
                            if not scrape_result or not scrape_result.get("success"):
                                if has_searchable_items(stale_source):
                                    source = stale_source
                                    source_was_stale = True
                                    source_tier = "stale"
                                    search_source_cache.set(user["id"], source)
                                    logger.warning("Using stale timetable source for user %s after Gmail refresh failed", user["id"])
                                else:
                                    detail = (scrape_result or {}).get("error", "Search failed")
                                    if "credential" in detail.lower() or "oauth" in detail.lower() or "decrypt" in detail.lower():
                                        detail = "Gmail authorization could not be read. Sign out, reconnect Gmail, and try again."
                                    return jsonify({"success": False, "error": detail}), 400
                            else:
                                source = scrape_result.get("data") or {}
                                source_tier = "gmail"
                                search_source_cache.set(user["id"], source)
                                if not store.save_search_source_cache(user["id"], source):
                                    logger.warning("Could not persist search source for user %s", user["id"])

            source_items = source.get("items") or []
            if not source_items:
                logger.warning(
                    "No searchable timetable source for user=%s email_domain=%s",
                    user["id"][-6:],
                    str(user.get("email") or "").partition("@")[2] or "unknown",
                )
                return jsonify({
                    "success": False,
                    "error": (
                        f"No timetable is saved for {user['email']}. Sign out and connect the Google "
                        "account that receives your SZABIST class-schedule emails."
                    ),
                    "code": "TIMETABLE_SOURCE_EMPTY",
                    "timestamp": current_timestamp(),
                }), 409

            from scraper.smart_search import PARSER_VERSION, normalize, search_timetable
            normalized_query = normalize(query)
            message_ids = source.get("message_ids") or [source.get("message_id")]
            source_revision = "|".join(str(value) for value in message_ids if value)
            if not source_revision:
                source_revision = f"{source.get('for_date', '')}:{len(source_items)}:{id(source)}"
            result_cache_key = (user["id"], source_revision, PARSER_VERSION, normalized_query)
            cached_search_result = search_result_cache.get(result_cache_key)
            if cached_search_result is not None:
                # The route changes only top-level response metadata, so a
                # shallow copy safely reuses unchanged match lists and avoids
                # duplicating hundreds of row dictionaries in memory.
                search_result = dict(cached_search_result)
                increment("search.result_cache.hit")
            else:
                search_started = time.perf_counter()
                search_result = search_timetable(query, source_items)
                observe("search.parse_and_match", (time.perf_counter() - search_started) * 1000)
                search_result_cache.set(result_cache_key, dict(search_result))
                increment("search.result_cache.miss")
            increment(f"search.source.{source_tier}")
            increment("search.matched_rows", len(search_result.get("items") or []))
            search_result["query"] = query
            search_result["saved_at"] = current_timestamp()
            search_result["source_stale"] = source_was_stale
            search_result["source_item_count"] = len(source_items)
            matched_items = search_result.pop("items")
            logger.info(
                "Smart search user=%s query=%r source_items=%d matched_items=%d recognized=%s entities=%s",
                user["id"][-6:],
                query,
                len(source_items),
                len(matched_items),
                search_result.get("recognized"),
                search_result.get("entities"),
            )
            semesters = {}
            for item in matched_items:
                semester = item.get("semester_display") or item.get("semester") or "Unknown"
                semesters[semester] = semesters.get(semester, 0) + 1
            data = {
                **source,
                "items": matched_items,
                "for_day": "Entire Week" if len(search_result["days"]) == 6 else " / ".join(search_result["days"]),
                "search": search_result,
                "summary": {
                    "total_items": len(matched_items),
                    "semester_breakdown": semesters,
                    "unique_courses": len({item.get("course_code") or item.get("course") for item in matched_items}),
                    "unique_faculty": len({item.get("faculty") for item in matched_items if item.get("faculty")}),
                },
            }
            # The normalized source remains persisted server-side. Search
            # answers are kept in IndexedDB by the browser instead of writing
            # a large Firestore document for every query. This removes a
            # database round trip from the response path and avoids turning a
            # read-only interaction into a billed write.
            message = search_result["answer"]
            if source_was_stale:
                message += " Using your last saved timetable because Gmail refresh is currently unavailable."
            return jsonify({"success": True, "data": data, "message": message, "timestamp": current_timestamp(), "cached": source_was_stale})
        except Exception as error:
            logger.error("Smart timetable search failed: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error), "timestamp": current_timestamp()}), 500

    @blueprint.route("/api/bootstrap", methods=["GET"])
    def bootstrap():
        """Return identity, settings and last result with one browser request."""
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code
            state = get_store().get_bootstrap_data(user["id"])
            return jsonify({
                "success": True,
                "user": {"id": user["id"], "email": user["email"]},
                "config": config_payload(state["settings"]),
                "timetable": state.get("timetable"),
                "last_update": state.get("last_update"),
                "timestamp": current_timestamp(),
            })
        except Exception as error:
            logger.error("Bootstrap failed: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error)}), 500

    @blueprint.route("/api/account", methods=["DELETE"])
    def delete_account():
        """Revoke Gmail access and remove all retained ClassWire data."""
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code
            store = get_store()
            try:
                token_data = store.get_user_tokens(user["id"]) or {}
            except Exception:
                logger.warning("Could not read the Google token before account deletion", exc_info=True)
                token_data = {}
            token = token_data.get("refresh_token") or token_data.get("token")
            if store.delete_user_data(user["id"]) is False:
                raise RuntimeError("Account data store rejected the deletion")
            search_source_cache.pop(user["id"])
            search_result_cache.discard_where(
                lambda cache_key, _result: cache_key[0] == user["id"]
            )
            refresh_locks.pop(user["id"])
            from flask import session
            session.clear()
            if token:
                import requests

                try:
                    requests.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": token},
                        timeout=5,
                    )
                except requests.RequestException:
                    logger.warning("Google token revocation failed during account deletion", exc_info=True)
            return jsonify({"success": True, "message": "Account data deleted"})
        except Exception as error:
            logger.error("Account deletion failed: %s", error, exc_info=True)
            return jsonify({"success": False, "error": "Could not delete account data"}), 500

    @blueprint.route("/api/cache/clear", methods=["POST"])
    def clear_cache():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            if not get_store().clear_user_cache(user["id"]):
                return jsonify({"success": False, "message": "Failed to clear cache"}), 500
            search_source_cache.pop(user["id"])

            return jsonify(
                {
                    "success": True,
                    "message": "Cache cleared successfully",
                    "timestamp": current_timestamp(),
                }
            )
        except Exception as error:
            logger.error("Error clearing cache: %s", error)
            return jsonify({"success": False, "message": "Internal server error"}), 500

    @blueprint.route("/api/automation/send-daily-timetables", methods=["POST"])
    def send_daily_timetables_automation():
        try:
            if not is_authorized_automation(request.headers):
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            from utils.daily_email import send_daily_timetable_emails

            job_id = uuid.uuid4().hex

            # Scheduled callers can wait for completion, which avoids tying
            # correctness to the lifetime of an in-process daemon thread.
            if request.args.get("wait") == "1":
                result = send_daily_timetable_emails()
                return jsonify({
                    **result,
                    "job_id": job_id,
                    "timestamp": current_timestamp(),
                }), 200 if result.get("success") else 500

            def run_daily_email_job():
                try:
                    result = send_daily_timetable_emails()
                    logger.info(
                        "Daily timetable automation job %s finished: success=%s processed=%s failed=%s",
                        job_id,
                        result.get("success"),
                        result.get("processed"),
                        result.get("failed"),
                    )
                except Exception as error:
                    logger.error(
                        "Daily timetable automation job %s failed: %s",
                        job_id,
                        error,
                        exc_info=True,
                    )

            threading.Thread(target=run_daily_email_job, daemon=True).start()
            return jsonify(
                {
                    "success": True,
                    "job_id": job_id,
                    "message": "Daily timetable automation started",
                    "timestamp": current_timestamp(),
                }
            ), 202
        except Exception as error:
            logger.error("Daily timetable automation failed: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error), "timestamp": current_timestamp()}), 500

    @blueprint.route("/api/automation/send-test-timetable-email", methods=["POST", "OPTIONS"])
    def send_test_timetable_email():
        if request.method == "OPTIONS":
            return "", 200

        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            store = get_store()
            user_settings = store.get_user_settings(user["id"])
            personal_email = (user_settings.get("personal_email") or "").strip()
            if not personal_email:
                return jsonify({"success": False, "error": "Save a personal email before sending a test."}), 400

            from utils.daily_email import send_daily_timetable_email_for_user

            job_id = uuid.uuid4().hex

            def save_job_status(update):
                merge_daily_email_status(get_store(), user["id"], job_id, update)

            user_settings["daily_email_last_result"] = {
                "status": "running",
                "success": None,
                "message": "Mail send job is running",
                "job_id": job_id,
                "started_at": current_timestamp(),
            }
            store.save_user_settings(user["id"], user_settings)

            def run_email_job():
                try:
                    result = send_daily_timetable_email_for_user(
                        user,
                        user_settings,
                        status_callback=save_job_status,
                    )
                    save_job_status(
                        {
                            **result,
                            "status": "success" if result.get("success") else "error",
                            "message": build_manual_email_message(result),
                            "finished_at": current_timestamp(),
                        }
                    )
                except Exception as error:
                    logger.error(
                        "Background manual timetable email failed for %s: %s",
                        user.get("email"),
                        error,
                        exc_info=True,
                    )
                    save_job_status(
                        {
                            "status": "error",
                            "success": False,
                            "message": str(error),
                            "error": str(error),
                            "personal_email": personal_email,
                            "finished_at": current_timestamp(),
                        }
                    )

            def mark_timeout_if_still_running():
                try:
                    timeout_seconds = int(os.environ.get("TEST_EMAIL_TIMEOUT_SECONDS", "75"))
                    threading.Event().wait(timeout_seconds)
                    latest_settings = get_store().get_user_settings(user["id"])
                    last_result = latest_settings.get("daily_email_last_result") or {}
                    if last_result.get("job_id") != job_id or last_result.get("status") in {"success", "error"}:
                        return

                    stage = last_result.get("status") or "running"
                    latest_settings["daily_email_last_result"] = {
                        **last_result,
                        "status": "error",
                        "success": False,
                        "message": f"Mail send timed out while {stage}. Check Render logs for the stuck step.",
                        "error": f"Timed out while {stage}",
                        "finished_at": current_timestamp(),
                        "updated_at": current_timestamp(),
                    }
                    get_store().save_user_settings(user["id"], latest_settings)
                    logger.error("Manual timetable email timed out for %s while %s", user.get("email"), stage)
                except Exception as error:
                    logger.error("Could not mark manual timetable email timeout: %s", error, exc_info=True)

            threading.Thread(target=run_email_job, daemon=True).start()
            threading.Thread(target=mark_timeout_if_still_running, daemon=True).start()

            return jsonify(
                {
                    "success": True,
                    "message": "Mail send started. Check your inbox in a minute.",
                    "personal_email": personal_email,
                    "job_id": job_id,
                    "timestamp": current_timestamp(),
                }
            ), 202
        except Exception as error:
            logger.error("Manual timetable email failed: %s", error, exc_info=True)
            return jsonify({"success": False, "error": str(error), "timestamp": current_timestamp()}), 500

    @blueprint.route("/api/timetable", methods=["GET"])
    def get_latest_timetable():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            store = get_store()
            cache_data = store.get_latest_timetable_cache(user["id"])
            latest_timestamp = store.get_latest_timetable_timestamp(user["id"])
            if not cache_data:
                return jsonify(
                    {
                        "success": False,
                        "message": "No cached schedule data found. Run a scrape first.",
                        "timestamp": current_timestamp(),
                    }
                ), 404

            return jsonify(
                {
                    "success": True,
                    "data": cache_data,
                    "timestamp": latest_timestamp or current_timestamp(),
                    "cached": True,
                }
            )
        except Exception as error:
            logger.error("Error reading cached data: %s", error)
            return jsonify({"success": False, "error": str(error), "timestamp": current_timestamp()}), 500

    @blueprint.route("/api/status", methods=["GET"])
    def get_status():
        try:
            user, error_response, status_code = get_user_from_request()
            user_id = user.get("id") if user else None
            if error_response:
                return error_response, status_code

            latest_timestamp = get_store().get_latest_timetable_timestamp(user_id)
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "timestamp": current_timestamp(),
                        "cache_exists": latest_timestamp is not None,
                        "last_update": latest_timestamp,
                        "source": "firestore" if latest_timestamp else "none",
                    },
                    "timestamp": current_timestamp(),
                }
            )
        except Exception as error:
            logger.error("Error getting status: %s", error)
            return jsonify({"success": False, "error": str(error), "timestamp": current_timestamp()}), 500

    return blueprint
