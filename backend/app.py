"""Flask backend for ClassWire."""

from __future__ import annotations

import html
import json
import os
import secrets
import urllib.parse
import hmac
from datetime import datetime

from flask import Flask, jsonify, redirect, request, session

from core.authentication import authenticated_user
from core.app_support import (
    TemporaryStateStore,
    configure_app,
    configure_logging,
    ensure_client_secrets_from_env,
    get_google_client_secrets_file,
    get_local_ip,
    get_public_origin,
    get_public_request_url,
    get_redirect_uri,
    validate_frontend_origin,
)
from database.firestore_store import data_store
from routes.user_data import create_user_data_blueprint
from core.telemetry import snapshot as telemetry_snapshot

app = Flask(__name__)
configure_app(app)
logger = configure_logging()
ensure_client_secrets_from_env()

store = data_store
oauth_state_store = TemporaryStateStore()
oauth_handoff_store = TemporaryStateStore(ttl_seconds=120, max_entries=512)

LOCAL_IP = get_local_ip()
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 5174))


def run_once(*args, **kwargs):
    """Load the Gmail/parser stack only when a scrape is actually requested."""
    from scraper.scheduler import run_once as scrape_once

    return scrape_once(*args, **kwargs)


def build_popup_message_page(*, frontend_origin: str, payload: dict, close_delay_ms: int, body_text: str) -> str:
    target_origins = json.dumps(
        [
            frontend_origin,
            f"http://localhost:{FRONTEND_PORT}",
            f"http://127.0.0.1:{FRONTEND_PORT}",
            f"http://{LOCAL_IP}:{FRONTEND_PORT}",
        ]
    )
    message_payload = json.dumps(payload)
    safe_body = html.escape(body_text)
    return f"""
    <html>
    <body>
      <script>
      const targetOrigins = {target_origins};
      const message = {message_payload};
      targetOrigins.forEach(origin => {{
        try {{
          if (window.opener) {{
            window.opener.postMessage(message, origin);
          }}
        }} catch (error) {{
          console.log('Failed to post to:', origin, error);
        }}
      }});
      setTimeout(() => window.close(), {close_delay_ms});
      </script>
      <p>{safe_body}</p>
    </body>
    </html>
    """


def build_auth_handoff_redirect_page(frontend_url: str, params: dict, body_text: str) -> str:
    """Return OAuth results in the URL fragment so secrets do not reach access logs."""
    redirect_url = f"{frontend_url}/#{urllib.parse.urlencode(params)}"
    safe_redirect = html.escape(redirect_url, quote=True)
    safe_body = html.escape(body_text)
    return f"""
    <html>
    <head>
      <meta http-equiv="refresh" content="0; url={safe_redirect}">
    </head>
    <body>
      <script>
        window.location.replace({json.dumps(redirect_url)});
      </script>
      <p>{safe_body}</p>
    </body>
    </html>
    """


def establish_user_session(user_id: str, user_email: str) -> None:
    session.clear()
    session.permanent = True
    session["user_id"] = user_id
    session["user_email"] = user_email.strip().lower()
    session["user_identity_verified"] = True


def resolve_frontend_origin(state_data: dict | None = None) -> str:
    frontend_origin = validate_frontend_origin(
        (state_data or {}).get("frontend_origin") or session.get("frontend_origin")
    )
    if frontend_origin:
        return frontend_origin

    referer = request.headers.get("Referer", "")
    if LOCAL_IP in referer:
        return f"http://{LOCAL_IP}:{FRONTEND_PORT}"
    if f"localhost:{FRONTEND_PORT}" in referer or f"127.0.0.1:{FRONTEND_PORT}" in referer:
        return f"http://localhost:{FRONTEND_PORT}"

    return f"http://{LOCAL_IP}:{FRONTEND_PORT}"


def get_user_from_request():
    """Compatibility helper kept for tests and simple request validation."""
    return authenticated_user(store, logger)


@app.route("/api/auth/session", methods=["GET"])
def auth_session():
    user, error_response, status_code = authenticated_user(store, logger)
    if error_response:
        if status_code == 401:
            return jsonify({"success": True, "authenticated": False, "user": None})
        return error_response, status_code
    return jsonify({
        "success": True,
        "authenticated": True,
        "user": {"id": user["id"], "email": user["email"]},
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/health", methods=["GET"])
def health_check():
    # This endpoint is both Render's liveness probe and the browser's wake-up
    # target. Never put Firestore/Gmail network I/O here: the process is ready
    # as soon as Flask can answer, and downstream dependencies are checked by
    # the authenticated requests that actually use them.
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "config_loaded": True,
            "revision": (os.environ.get("RENDER_GIT_COMMIT") or "local")[:12],
        }
    )


@app.route("/api/metrics", methods=["GET"])
def metrics():
    configured = os.environ.get("AUTOMATION_SECRET", "")
    supplied = request.headers.get("X-Automation-Secret", "")
    if not configured or not hmac.compare_digest(configured, supplied):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({"success": True, "data": telemetry_snapshot()})


@app.route("/api/auth/gmail", methods=["GET"])
def gmail_auth():
    try:
        from google_auth_oauthlib.flow import Flow

        if get_public_origin().startswith("http://"):
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        client_secrets_file = get_google_client_secrets_file()
        if not os.path.exists(client_secrets_file):
            return jsonify({"error": "Client secrets file not found"}), 500

        flow = Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid",
            ],
        )

        requested_origin = request.args.get("frontend_origin") or request.headers.get("Origin")
        frontend_origin = validate_frontend_origin(requested_origin)
        if requested_origin and not frontend_origin:
            return jsonify({"error": "Untrusted frontend origin"}), 400
        if frontend_origin:
            try:
                session["frontend_origin"] = frontend_origin
            except Exception as error:
                logger.warning("Could not store frontend origin in session: %s", error)

        flow.redirect_uri = get_redirect_uri()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes=False,
            prompt="consent",
        )

        redirect_mode = request.args.get("redirect") == "1"
        try:
            session["auth_state"] = state
            code_verifier = getattr(flow, "code_verifier", None)
            if code_verifier:
                session["code_verifier"] = code_verifier
            oauth_state_store.store(
                state,
                code_verifier=code_verifier,
                frontend_origin=frontend_origin,
                redirect_mode=redirect_mode,
            )
        except Exception as error:
            logger.warning("Could not store session data for PKCE: %s", error)

        if request.args.get("redirect") == "1":
            return redirect(authorization_url)

        return jsonify({"auth_url": authorization_url, "state": state})
    except Exception as error:
        logger.error("Gmail auth error: %s", error)
        return jsonify({"error": "Could not start Gmail authentication"}), 500


@app.route("/api/auth/gmail/callback", methods=["GET"])
def gmail_callback():
    state_data = None

    try:
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build

        if get_public_origin().startswith("http://"):
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        client_secrets_file = get_google_client_secrets_file()

        flow = Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid",
            ],
        )
        flow.redirect_uri = get_redirect_uri()

        callback_state = request.args.get("state")
        state_data = oauth_state_store.pop(callback_state)
        if not state_data:
            return jsonify({"success": False, "error": "Invalid or expired OAuth state"}), 400
        code_verifier = (state_data or {}).get("code_verifier") or session.get("code_verifier")
        if code_verifier and hasattr(flow, "code_verifier"):
            flow.code_verifier = code_verifier

        # OAuth codes are single-use. Accept Google's scope normalization instead
        # of retrying an exchange that may already have consumed the code.
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(authorization_response=get_public_request_url())

        credentials = flow.credentials

        user_email = None
        try:
            profile = build("gmail", "v1", credentials=credentials).users().getProfile(userId="me").execute()
            user_email = profile["emailAddress"]
        except Exception:
            user_info = build("oauth2", "v2", credentials=credentials).userinfo().get().execute()
            user_email = user_info.get("email")

        if not user_email:
            raise Exception("No user email found in OAuth response")

        user = store.get_or_create_user(user_email)
        store.save_user_tokens(
            user["id"],
            {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            },
        )

        establish_user_session(user["id"], user_email)

        frontend_origin = resolve_frontend_origin(state_data)
        if (state_data or {}).get("redirect_mode"):
            handoff_token = secrets.token_urlsafe(32)
            oauth_handoff_store.store(
                handoff_token,
                user_id=user["id"],
                user_email=user_email.strip().lower(),
            )
            return build_auth_handoff_redirect_page(
                frontend_origin,
                {"auth": "success", "handoff": handoff_token},
                "Authentication successful. Redirecting...",
            )

        return build_popup_message_page(
            frontend_origin=frontend_origin,
            payload={"type": "GMAIL_AUTH_SUCCESS", "user": {"id": user["id"], "email": user_email}},
            close_delay_ms=1000,
            body_text="Authentication successful! This window will close automatically.",
        )
    except Exception as error:
        logger.error("Gmail callback error: %s", error, exc_info=True)
        state_data = state_data or oauth_state_store.pop(request.args.get("state"))
        frontend_origin = resolve_frontend_origin(state_data)

        if (state_data or {}).get("redirect_mode"):
            return build_auth_handoff_redirect_page(
                frontend_origin,
                {"auth": "error"},
                "Authentication failed. Redirecting...",
            )

        return build_popup_message_page(
            frontend_origin=frontend_origin,
            payload={"type": "GMAIL_AUTH_ERROR", "error": "Authentication failed"},
            close_delay_ms=2000,
            body_text="Authentication failed. Close this window and try again.",
        )


@app.route("/api/auth/handoff", methods=["POST"])
def auth_handoff():
    """Exchange a short-lived OAuth result for a first-party signed session."""
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    if not isinstance(token, str) or not token.strip():
        return jsonify({"success": False, "error": "Authentication handoff is required"}), 400

    handoff = oauth_handoff_store.pop(token.strip())
    if not handoff:
        return jsonify({"success": False, "error": "Authentication handoff expired"}), 401

    user_id = str(handoff.get("user_id") or "").strip()
    user_email = str(handoff.get("user_email") or "").strip().lower()
    if not user_id or not user_email:
        return jsonify({"success": False, "error": "Invalid authentication handoff"}), 401

    establish_user_session(user_id, user_email)
    return jsonify({
        "success": True,
        "authenticated": True,
        "user": {"id": user_id, "email": user_email},
    })


app.register_blueprint(
    create_user_data_blueprint(
        logger=logger,
        get_run_once=lambda: run_once,
        get_store=lambda: store,
    )
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on 0.0.0.0:{port}")
    print("Access URLs:")
    print(f"  Local: http://localhost:{port}")
    print(f"  Network: http://{LOCAL_IP}:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
