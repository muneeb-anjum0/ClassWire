"""Encryption for OAuth credentials stored in Firestore."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    secret = os.environ.get("TOKEN_ENCRYPTION_KEY")
    is_production = os.environ.get("PUBLIC_BACKEND_URL", "").strip().startswith("https://")
    if not secret and not is_production:
        secret = os.environ.get("FLASK_SECRET_KEY")
    if not secret:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required to encrypt OAuth tokens")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_token_data(token_data: dict[str, Any]) -> str:
    payload = json.dumps(token_data, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_token_data(payload: str) -> dict[str, Any]:
    try:
        decoded = _fernet().decrypt(payload.encode("ascii"))
        value = json.loads(decoded.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("Stored OAuth credentials could not be decrypted") from error
    if not isinstance(value, dict):
        raise RuntimeError("Stored OAuth credentials have an invalid format")
    return value
