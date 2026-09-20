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
    # Existing sessions created before an account migration may contain a
    # validly signed but obsolete user id. Verify that id once per browser
    # session, then retain the no-read fast path for every later request.
    if (
        isinstance(user_id, str)
        and user_id.strip()
        and session.get("user_identity_verified") is True
    ):
        return {"id": user_id, "email": normalized_email}, None, None

    try:
        user = store.get_or_create_user(normalized_email)
    except Exception as error:
        logger.error("Could not resolve authenticated user: %s", error)
        return None, jsonify({"success": False, "error": "User lookup failed"}), 500

    canonical_user_id = str(user.get("id") or "").strip()
    if not canonical_user_id:
        session.clear()
        return None, jsonify({"success": False, "error": "Invalid user account"}), 401

    session["user_id"] = canonical_user_id
    session["user_email"] = normalized_email
    session["user_identity_verified"] = True
    return user, None, None


def is_valid_automation_secret(provided: str) -> bool:
    expected = os.environ.get("AUTOMATION_SECRET", "").strip()
    return bool(expected and provided and hmac.compare_digest(provided, expected))
