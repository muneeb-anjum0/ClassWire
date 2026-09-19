"""Server-side authentication helpers."""

from __future__ import annotations

import hmac
import os
from typing import Any

from flask import current_app, jsonify, request, session


def authenticated_user(store, logger) -> tuple[dict[str, Any] | None, Any, int | None]:
    """Resolve the signed-in user from the Flask session.

    The header fallback exists only for the test suite. Production requests
    never get to choose their identity through a browser-controlled header.
    """
    email = session.get("user_email")
    user_id = session.get("user_id")

    if current_app.testing and not email:
        email = request.headers.get("X-User-Email")

    if not isinstance(email, str) or not email.strip():
        return None, jsonify({"success": False, "error": "Authentication required"}), 401

    normalized_email = email.strip().lower()
    # Both values are written only after a successful OAuth callback and live
    # inside Flask's signed session cookie. Re-querying Firestore on every API
    # call adds latency and a billable read without adding authentication
    # value. The test-only header fallback still resolves through the store.
    if isinstance(user_id, str) and user_id.strip():
        return {"id": user_id, "email": normalized_email}, None, None

    try:
        user = store.get_or_create_user(normalized_email)
    except Exception as error:
        logger.error("Could not resolve authenticated user: %s", error)
        return None, jsonify({"success": False, "error": "User lookup failed"}), 500

    if user_id and user.get("id") != user_id:
        session.clear()
        return None, jsonify({"success": False, "error": "Invalid session"}), 401
    return user, None, None


def is_valid_automation_secret(provided: str) -> bool:
    expected = os.environ.get("AUTOMATION_SECRET", "").strip()
    return bool(expected and provided and hmac.compare_digest(provided, expected))
