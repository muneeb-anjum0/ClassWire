"""Firestore persistence for users, OAuth tokens, settings, and timetable cache."""

from __future__ import annotations

import gzip
import json
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from core.ttl_cache import TTLCache

from .defaults import build_default_user_settings
from .token_crypto import decrypt_token_data, encrypt_token_data

logger = logging.getLogger(__name__)
MAX_FIRESTORE_PAYLOAD_BYTES = 900_000


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


def _encode_json_payload(value: Dict[str, Any]) -> bytes:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return gzip.compress(serialized, compresslevel=6)


def _decode_json_payload(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, (bytes, bytearray)):
        return None
    try:
        decoded = json.loads(gzip.decompress(bytes(value)).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Ignoring an invalid compressed Firestore payload", exc_info=True)
        return None
    return decoded if isinstance(decoded, dict) else None


def _cache_content_hash(cache_data: Dict[str, Any]) -> str:
    stable_payload = dict(cache_data)
    search = stable_payload.get("search")
    if isinstance(search, dict):
        stable_payload["search"] = {key: value for key, value in search.items() if key != "saved_at"}
    return hashlib.sha256(
        json.dumps(stable_payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
        self.source_cache = self.client.collection("timetable_source_cache")
        self._settings_cache = TTLCache[str, Dict[str, Any]](ttl_seconds=300, max_entries=512)
        self._token_cache = TTLCache[str, Dict[str, Any]](ttl_seconds=300, max_entries=512)
        self._timetable_cache = TTLCache[str, tuple[Dict[str, Any], str]](ttl_seconds=60, max_entries=256)
        self._timetable_hashes = TTLCache[str, str](ttl_seconds=86400, max_entries=512)
        self._health_cache = TTLCache[str, bool](ttl_seconds=60, max_entries=1)
        logger.info("Firestore client initialized")

    def is_healthy(self) -> bool:
        cached = self._health_cache.get("firestore")
        if cached is not None:
            return cached
        self.users.limit(1).get()
        self._health_cache.set("firestore", True)
        return True

    def get_or_create_user(self, email: str) -> Dict[str, Any]:
        normalized_email = email.strip().lower()
        matches = list(self.users.where(filter=FieldFilter("email", "==", normalized_email)).limit(1).stream())

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
        self._token_cache.set(user_id, dict(token_data))
        return True

    def get_user_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        cached = self._token_cache.get(user_id)
        if cached is not None:
            return dict(cached)
        snapshot = self.tokens.document(user_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        encrypted = payload.get("encrypted_token_data")
        if encrypted:
            token_data = decrypt_token_data(encrypted)
            self._token_cache.set(user_id, dict(token_data))
            return token_data

        legacy = payload.get("token_data")
        if legacy:
            self.save_user_tokens(user_id, legacy)
            return legacy
        return None

    def save_timetable_cache(self, user_id: str, cache_data: Dict[str, Any]) -> bool:
        content_hash = _cache_content_hash(cache_data)
        if self._timetable_hashes.get(user_id) == content_hash:
            return True
        compressed = _encode_json_payload(cache_data)
        if len(compressed) > MAX_FIRESTORE_PAYLOAD_BYTES:
            logger.error("Timetable cache is too large to persist safely: %s compressed bytes", len(compressed))
            return False
        now = _utc_now()
        self.cache.document(user_id).set(
            {
                "user_id": user_id,
                "cache_gzip": compressed,
                "cache_version": 2,
                "updated_at": now,
            }
        )
        self._timetable_hashes.set(user_id, content_hash)
        self._timetable_cache.set(user_id, (cache_data, _serialize_timestamp(now) or ""))
        return True

    def get_latest_timetable_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        cached = self._timetable_cache.get(user_id)
        if cached is not None:
            return cached[0]
        snapshot = self.cache.document(user_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        cache_data = _decode_json_payload(payload.get("cache_gzip")) or payload.get("cache_data")
        if cache_data:
            self._timetable_hashes.set(user_id, _cache_content_hash(cache_data))
            self._timetable_cache.set(
                user_id,
                (cache_data, _serialize_timestamp(payload.get("updated_at")) or ""),
            )
        return cache_data

    def clear_user_cache(self, user_id: str) -> bool:
        self.cache.document(user_id).delete()
        self.source_cache.document(user_id).delete()
        self._timetable_hashes.pop(user_id)
        self._timetable_cache.pop(user_id)
        return True

    def save_search_source_cache(self, user_id: str, source_data: Dict[str, Any]) -> bool:
        """Persist the compact weekly source so process restarts do not rescrape Gmail."""
        compressed = _encode_json_payload(source_data)
        if len(compressed) > MAX_FIRESTORE_PAYLOAD_BYTES:
            logger.error("Search source is too large to persist safely: %s compressed bytes", len(compressed))
            return False
        self.source_cache.document(user_id).set(
            {
                "user_id": user_id,
                "source_gzip": compressed,
                "cache_version": 2,
                "updated_at": _utc_now(),
            }
        )
        return True

    def get_search_source_cache(
        self,
        user_id: str,
        *,
        max_age_seconds: Optional[int] = 1800,
    ) -> Optional[Dict[str, Any]]:
        snapshot = self.source_cache.document(user_id).get()
        if not snapshot.exists:
            return None
        payload = snapshot.to_dict() or {}
        updated_at = payload.get("updated_at")
        if not isinstance(updated_at, datetime):
            return None
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if max_age_seconds is not None and (_utc_now() - updated_at).total_seconds() > max_age_seconds:
            return None
        source_data = _decode_json_payload(payload.get("source_gzip")) or payload.get("source_data")
        return source_data if isinstance(source_data, dict) else None

    def get_latest_timetable_timestamp(self, user_id: str | None = None) -> Optional[str]:
        if user_id:
            cached = self._timetable_cache.get(user_id)
            if cached is not None:
                return cached[1] or None
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
        self._settings_cache.set(user_id, dict(merged))
        return True

    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        cached = self._settings_cache.get(user_id)
        if cached is not None:
            return dict(cached)
        snapshot = self.settings.document(user_id).get()
        if not snapshot.exists:
            settings = build_default_user_settings()
        else:
            payload = snapshot.to_dict() or {}
            settings = build_default_user_settings(payload.get("settings") or {})
        self._settings_cache.set(user_id, dict(settings))
        return settings

    def list_users_with_daily_email(self) -> List[Dict[str, Any]]:
        configured_settings: Dict[str, tuple[Dict[str, Any], str]] = {}

        for settings_doc in self.settings.stream():
            payload = settings_doc.to_dict() or {}
            settings = build_default_user_settings(payload.get("settings") or {})
            personal_email = (settings.get("personal_email") or "").strip()
            if not personal_email or not settings.get("daily_email_enabled"):
                continue

            user_id = payload.get("user_id") or settings_doc.id
            configured_settings[user_id] = (settings, personal_email)

        if not configured_settings:
            return []

        configured_users: List[Dict[str, Any]] = []
        user_refs = [self.users.document(user_id) for user_id in configured_settings]
        found_user_ids = set()
        for user_doc in self.client.get_all(user_refs):
            if not user_doc.exists:
                continue
            user_id = user_doc.id
            found_user_ids.add(user_id)
            settings, personal_email = configured_settings[user_id]
            user_data = user_doc.to_dict() or {}
            user_data["id"] = user_id
            configured_users.append(
                {
                    "user": user_data,
                    "settings": settings,
                    "personal_email": personal_email,
                }
            )

        for missing_user_id in configured_settings.keys() - found_user_ids:
            logger.warning("Daily email configured for missing user_id=%s", missing_user_id)

        return configured_users

    def cleanup_old_cache(self) -> bool:
        cutoff = _utc_now() - timedelta(days=7)
        batch = self.client.batch()
        pending = 0
        for collection in (self.cache, self.source_cache):
            stale_docs = collection.where(filter=FieldFilter("updated_at", "<", cutoff)).stream()
            for cache_doc in stale_docs:
                batch.delete(cache_doc.reference)
                pending += 1
                if pending == 450:
                    batch.commit()
                    batch = self.client.batch()
                    pending = 0
        if pending:
            batch.commit()
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
