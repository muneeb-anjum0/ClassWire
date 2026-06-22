"""Shared Flask app setup helpers."""

from __future__ import annotations

import logging
import os
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

LOCAL_ORIGIN_PATTERNS = (
    re.compile(r"^http://localhost:\d+$"),
    re.compile(r"^http://127\.0\.0\.1:\d+$"),
    re.compile(r"^http://192\.168\.\d+\.\d+:\d+$"),
)

LOGGER = logging.getLogger(__name__)
PLACEHOLDER_SECRETS = {"change-me", "change-me-too", "replace-me", "local-development-only"}


def _validate_production_config(is_https: bool, secret_key: str) -> None:
    if not is_https:
        return

    required = {
        "FLASK_SECRET_KEY": secret_key,
        "TOKEN_ENCRYPTION_KEY": os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip(),
        "AUTOMATION_SECRET": os.environ.get("AUTOMATION_SECRET", "").strip(),
        "FRONTEND_ORIGINS": os.environ.get("FRONTEND_ORIGINS", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    weak = [
        name
        for name, value in required.items()
        if name != "FRONTEND_ORIGINS" and value and (len(value) < 32 or value.lower() in PLACEHOLDER_SECRETS)
    ]
    if missing or weak:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if weak:
            details.append(f"weak: {', '.join(weak)}")
        raise RuntimeError("Unsafe production configuration (" + "; ".join(details) + ")")


def configure_app(app: Flask) -> None:
    public_backend_url = os.environ.get("PUBLIC_BACKEND_URL", "").strip()
    is_https = public_backend_url.startswith("https://")
    secret_key = os.environ.get("FLASK_SECRET_KEY", "").strip()
    _validate_production_config(is_https, secret_key)
    if not secret_key:
        if is_https:
            raise RuntimeError("FLASK_SECRET_KEY is required in production")
        secret_key = "local-development-only"
        LOGGER.warning("Using a development-only Flask secret key")

    app.secret_key = secret_key
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_NAME="classwire_session",
        SESSION_COOKIE_SAMESITE="None" if is_https else "Lax",
        SESSION_COOKIE_SECURE=is_https,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )

    allowed_origins = get_allowed_origins()
    CORS(
        app,
        resources={r"/api/.*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    @app.before_request
    def reject_untrusted_browser_mutations():
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        origin = request.headers.get("Origin")
        if origin and not is_allowed_cors_origin(origin):
            return jsonify({"success": False, "error": "Untrusted request origin"}), 403
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'",
        )
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.getLogger("scraper.config").setLevel(logging.WARNING)
    logging.getLogger("database.firestore_store").setLevel(logging.WARNING)
    return logging.getLogger("app")


def get_allowed_origins() -> list[str]:
    configured = [
        origin.strip().rstrip("/")
        for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if os.environ.get("PUBLIC_BACKEND_URL", "").strip().startswith("https://"):
        return configured
    return configured + [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
        r"^http://192\.168\.\d+\.\d+:\d+$",
    ]


def is_allowed_cors_origin(origin: str) -> bool:
    normalized = origin.rstrip("/")
    if not normalized:
        return False
    configured = {
        value.strip().rstrip("/")
        for value in os.environ.get("FRONTEND_ORIGINS", "").split(",")
        if value.strip()
    }
    local_allowed = not os.environ.get("PUBLIC_BACKEND_URL", "").strip().startswith("https://")
    return normalized in configured or (
        local_allowed and any(pattern.fullmatch(normalized) for pattern in LOCAL_ORIGIN_PATTERNS)
    )


def validate_frontend_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    normalized = origin.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        return None
    return normalized if is_allowed_cors_origin(normalized) else None


def local_client_secrets_file() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials", "client_secret.json")


def render_secret_client_secrets_file() -> str:
    return "/etc/secrets/client_secret.json"


def ensure_client_secrets_from_env() -> None:
    client_secrets_env = os.environ.get("CLIENT_SECRET_JSON")
    client_secrets_file = local_client_secrets_file()
    if client_secrets_env and not os.path.exists(client_secrets_file):
        try:
            os.makedirs(os.path.dirname(client_secrets_file), exist_ok=True)
            with open(client_secrets_file, "w", encoding="utf-8") as file_handle:
                file_handle.write(client_secrets_env)
            try:
                os.chmod(client_secrets_file, 0o600)
            except OSError:
                LOGGER.warning("Could not restrict client_secret.json permissions")
            LOGGER.info("Wrote client_secret.json from CLIENT_SECRET_JSON env var")
        except Exception as error:
            LOGGER.error("Failed to write client_secret.json from env: %s", error)


def get_google_client_secrets_file() -> str:
    ensure_client_secrets_from_env()
    local_file = local_client_secrets_file()
    render_secret_file = render_secret_client_secrets_file()

    if os.path.exists(local_file):
        return local_file

    if os.path.exists(render_secret_file):
        return render_secret_file

    return local_file


@dataclass
class TemporaryStateStore:
    ttl_seconds: int = 600
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    def cleanup(self) -> None:
        now_ts = datetime.now().timestamp()
        expired = [
            state
            for state, payload in self.entries.items()
            if now_ts - payload.get("created_at", 0) > self.ttl_seconds
        ]
        for state in expired:
            self.entries.pop(state, None)

    def store(self, state: str, **payload: Any) -> None:
        self.cleanup()
        self.entries[state] = {
            **payload,
            "created_at": datetime.now().timestamp(),
        }

    def pop(self, state: str | None) -> dict[str, Any] | None:
        self.cleanup()
        if not state:
            return None
        return self.entries.pop(state, None)


def get_public_origin() -> str:
    env_origin = os.environ.get("PUBLIC_BACKEND_URL")
    if env_origin:
        return env_origin.rstrip("/")
    return request.host_url.rstrip("/")


def get_redirect_uri() -> str:
    return get_public_origin() + "/api/auth/gmail/callback"


def get_public_request_url() -> str:
    public_origin = get_public_origin()
    suffix = f"?{request.query_string.decode('utf-8')}" if request.query_string else ""
    return public_origin + request.path + suffix


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
