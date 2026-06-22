"""User-facing data, config, scrape, and automation routes."""

from __future__ import annotations

import os
import re
import threading
import uuid

from flask import Blueprint, jsonify, request

from core.authentication import authenticated_user

from .user_data_support import (
    build_manual_email_message,
    is_authorized_automation,
    merge_daily_email_status,
    timestamp_now,
)


EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def create_user_data_blueprint(*, logger, get_run_once, get_settings, get_store):
    blueprint = Blueprint("user_data", __name__)

    def current_timestamp():
        return timestamp_now()

    def get_user_from_request():
        return authenticated_user(get_store(), logger)

    @blueprint.route("/api/config", methods=["GET"])
    def get_config():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            store = get_store()
            settings = get_settings()
            user_settings = store.get_user_settings(user["id"])
            return jsonify(
                {
                    "gmail_query": user_settings.get("gmail_query_base", settings.gmail_query_base),
                    "semester_filter": user_settings.get("allowed_semesters", settings.allowed_semesters),
                    "personal_email": user_settings.get("personal_email", ""),
                    "daily_email_enabled": user_settings.get(
                        "daily_email_enabled",
                        bool(user_settings.get("personal_email")),
                    ),
                    "daily_email_last_result": user_settings.get("daily_email_last_result"),
                    "schedule_time": f"{settings.check_hour_local:02d}:{settings.check_minute_local:02d}",
                    "timezone": user_settings.get("timezone", settings.tz),
                    "max_results": getattr(settings, "max_results_per_semester", 50),
                }
            )
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

    @blueprint.route("/api/scrape", methods=["POST"])
    def scrape_now():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

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

    @blueprint.route("/api/cache/clear", methods=["POST"])
    def clear_cache():
        try:
            user, error_response, status_code = get_user_from_request()
            if error_response:
                return error_response, status_code

            if not get_store().clear_user_cache(user["id"]):
                return jsonify({"success": False, "message": "Failed to clear cache"}), 500

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
