"""Firestore persistence for users, OAuth tokens, settings, and timetable cache."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from .defaults import build_default_user_settings
from .token_crypto import decrypt_token_data, encrypt_token_data

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _load_firebase_credentials():
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()

    if service_account_json:
        try:
            return credentials.Certificate(json.loads(service_account_json))
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON must contain valid JSON") from exc

    if service_account_path:
        if not os.path.exists(service_account_path):
            raise ValueError(f"FIREBASE_SERVICE_ACCOUNT_PATH does not exist: {service_account_path}")
        return credentials.Certificate(service_account_path)

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return credentials.ApplicationDefault()

    raise ValueError(
        "Firebase credentials are missing. Set FIREBASE_SERVICE_ACCOUNT_JSON, "
        "FIREBASE_SERVICE_ACCOUNT_PATH, or GOOGLE_APPLICATION_CREDENTIALS."
    )


def _initialize_firestore_client():
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip() or None

    if firebase_admin._apps:
        return firestore.client()

    cred = _load_firebase_credentials()
    app = firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
    return firestore.client(app=app)


class FirestoreStore:
    """Small persistence API consumed by the rest of the backend."""

    def __init__(self) -> None:
        self.client = _initialize_firestore_client()
        self.users = self.client.collection("users")
        self.tokens = self.client.collection("gmail_tokens")
        self.settings = self.client.collection("user_settings")
        self.cache = self.client.collection("timetable_cache")
        logger.info("Firestore client initialized")

    def is_healthy(self) -> bool:
        self.users.limit(1).get()
        return True

    def get_or_create_user(self, email: str) -> Dict[str, Any]:
        normalized_email = email.strip().lower()
        matches = list(self.users.where("email", "==", normalized_email).limit(1).stream())

        if matches:
            payload = matches[0].to_dict() or {}
            payload["id"] = matches[0].id
            return payload

        now = _utc_now()
        user_id = uuid.uuid4().hex
        payload = {
            "id": user_id,
            "email": normalized_email,
            "created_at": now,
            "updated_at": now,
        }
        self.users.document(user_id).set(payload)
        return {**payload, "created_at": _serialize_timestamp(now), "updated_at": _serialize_timestamp(now)}

    def save_user_tokens(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        self.tokens.document(user_id).set(
            {
                "user_id": user_id,
                "encrypted_token_data": encrypt_token_data(token_data),
                "updated_at": _utc_now(),
            }
        )
        return True

    def get_user_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self.tokens.document(user_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        encrypted = payload.get("encrypted_token_data")
        if encrypted:
            return decrypt_token_data(encrypted)

        legacy = payload.get("token_data")
        if legacy:
            self.save_user_tokens(user_id, legacy)
            return legacy
        return None

    def save_timetable_cache(self, user_id: str, cache_data: Dict[str, Any]) -> bool:
        now = _utc_now()
        self.cache.document(user_id).set(
            {
                "user_id": user_id,
                "cache_data": cache_data,
                "updated_at": now,
            }
        )
        return True

    def get_latest_timetable_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self.cache.document(user_id).get()
        if not snapshot.exists:
            return None
        return (snapshot.to_dict() or {}).get("cache_data")

    def clear_user_cache(self, user_id: str) -> bool:
        self.cache.document(user_id).delete()
        return True

    def get_latest_timetable_timestamp(self, user_id: str | None = None) -> Optional[str]:
        if user_id:
            snapshot = self.cache.document(user_id).get()
            if not snapshot.exists:
                return None
            return _serialize_timestamp((snapshot.to_dict() or {}).get("updated_at"))

        docs = list(self.cache.order_by("updated_at", direction=firestore.Query.DESCENDING).limit(1).stream())
        if not docs:
            return None
        return _serialize_timestamp((docs[0].to_dict() or {}).get("updated_at"))

    def save_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        merged = build_default_user_settings(settings)
        self.settings.document(user_id).set(
            {
                "user_id": user_id,
                "settings": merged,
                "updated_at": _utc_now(),
            }
        )
        return True

    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        snapshot = self.settings.document(user_id).get()
        if not snapshot.exists:
            return build_default_user_settings()
        payload = snapshot.to_dict() or {}
        return build_default_user_settings(payload.get("settings") or {})

    def list_users_with_daily_email(self) -> List[Dict[str, Any]]:
        configured_users: List[Dict[str, Any]] = []

        for settings_doc in self.settings.stream():
            payload = settings_doc.to_dict() or {}
            settings = build_default_user_settings(payload.get("settings") or {})
            personal_email = (settings.get("personal_email") or "").strip()
            if not personal_email or not settings.get("daily_email_enabled"):
                continue

            user_id = payload.get("user_id") or settings_doc.id
            user_doc = self.users.document(user_id).get()
            if not user_doc.exists:
                logger.warning("Daily email configured for missing user_id=%s", user_id)
                continue

            user_data = user_doc.to_dict() or {}
            user_data["id"] = user_doc.id
            configured_users.append(
                {
                    "user": user_data,
                    "settings": settings,
                    "personal_email": personal_email,
                }
            )

        return configured_users

    def cleanup_old_cache(self) -> bool:
        cutoff = _utc_now() - timedelta(days=7)
        for cache_doc in self.cache.stream():
            updated_at = (cache_doc.to_dict() or {}).get("updated_at")
            if isinstance(updated_at, datetime) and updated_at < cutoff:
                cache_doc.reference.delete()
        return True


class LazyFirestoreStore:
    """Create the Firestore store only when the app actually needs it."""

    def __init__(self) -> None:
        self._store: FirestoreStore | None = None

    def _get_store(self) -> FirestoreStore:
        if self._store is None:
            self._store = FirestoreStore()
        return self._store

    def is_healthy(self) -> bool:
        try:
            return self._get_store().is_healthy()
        except Exception:
            return False

    def __getattr__(self, name: str):
        return getattr(self._get_store(), name)


data_store = LazyFirestoreStore()
