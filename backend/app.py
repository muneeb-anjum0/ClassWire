"""Flask backend for ClassWire."""

from __future__ import annotations

import html
import json
import os
import sys
import urllib.parse
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
from scraper.config import settings
from scraper.scheduler import run_once

app = Flask(__name__)
configure_app(app)
logger = configure_logging()
ensure_client_secrets_from_env()

store = data_store
oauth_state_store = TemporaryStateStore()

LOCAL_IP = get_local_ip()
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 3000))


def build_popup_message_page(*, frontend_origin: str, payload: dict, close_delay_ms: int, body_text: str) -> str:
    target_origins = json.dumps(
        [
            frontend_origin,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
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


def build_mobile_redirect_page(frontend_url: str, params: dict, body_text: str) -> str:
    redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
    safe_redirect = html.escape(redirect_url, quote=True)
    safe_body = html.escape(body_text)
    return f"""
    <html>
    <head>
      <meta http-equiv="refresh" content="0; url={safe_redirect}">
    </head>
    <body>
      <script>
        window.location.href = {json.dumps(redirect_url)};
      </script>
      <p>{safe_body}</p>
    </body>
    </html>
    """


def is_mobile_request() -> bool:
    user_agent = request.headers.get("User-Agent", "").lower()
    mobile_markers = ["mobile", "android", "iphone", "ipad", "ipod", "blackberry", "opera mini"]
    return any(marker in user_agent for marker in mobile_markers)


def resolve_frontend_origin(state_data: dict | None = None) -> str:
    frontend_origin = validate_frontend_origin(
        (state_data or {}).get("frontend_origin") or session.get("frontend_origin")
    )
    if frontend_origin:
        return frontend_origin

    referer = request.headers.get("Referer", "")
    if LOCAL_IP in referer:
        return f"http://{LOCAL_IP}:{FRONTEND_PORT}"
    if "localhost:3000" in referer or "127.0.0.1:3000" in referer:
        return f"http://localhost:{FRONTEND_PORT}"

    return f"http://{LOCAL_IP}:{FRONTEND_PORT}"


def get_user_from_request():
    """Compatibility helper kept for tests and simple request validation."""
    return authenticated_user(store, logger)


@app.route("/api/auth/session", methods=["GET"])
def auth_session():
    user, error_response, status_code = authenticated_user(store, logger)
    if error_response:
        return error_response, status_code
    return jsonify({"success": True, "user": {"id": user["id"], "email": user["email"]}})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "config_loaded": True,
                "firestore_connected": store.is_healthy(),
            }
        )
    except Exception as error:
        return jsonify(
            {
                "status": "unhealthy",
                "error": "Backend health check failed",
                "timestamp": datetime.now().isoformat(),
            }
        ), 500


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

        try:
            session["auth_state"] = state
            code_verifier = getattr(flow, "code_verifier", None)
            if code_verifier:
                session["code_verifier"] = code_verifier
            oauth_state_store.store(state, code_verifier=code_verifier, frontend_origin=frontend_origin)
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

        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_email"] = user_email.strip().lower()

        frontend_origin = resolve_frontend_origin(state_data)
        if is_mobile_request():
            return build_mobile_redirect_page(
                frontend_origin,
                {"auth": "success", "user_id": user["id"], "email": user_email},
                "Authentication successful! Redirecting...",
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

        if is_mobile_request():
            return build_mobile_redirect_page(
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


app.register_blueprint(
    create_user_data_blueprint(
        logger=logger,
        get_run_once=lambda: run_once,
        get_settings=lambda: settings,
        get_store=lambda: store,
    )
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on 0.0.0.0:{port}")
    print("Access URLs:")
    print(f"  Local: http://localhost:{port}")
    print(f"  Network: http://{LOCAL_IP}:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
