from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from core.ttl_cache import TTLCache
from database.firestore_store import (
    FirestoreStore,
    _cache_content_hash,
    _decode_json_payload,
    _encode_json_payload,
)


def test_firestore_payload_round_trip_is_compact_and_lossless():
    payload = {
        "for_day": "Entire Week",
        "items": [
            {
                "semester_display": "BS(SE)-7A",
                "course_title": "Software Project Management",
                "faculty": "Muhammad Qasim",
            }
            for _ in range(500)
        ],
    }

    compressed = _encode_json_payload(payload)

    assert _decode_json_payload(compressed) == payload
    assert len(compressed) < len(str(payload).encode("utf-8")) / 5


def test_cache_hash_ignores_only_volatile_search_timestamp():
    first = {"items": [{"course": "One"}], "search": {"query": "one", "saved_at": "a"}}
    same_content = {"items": [{"course": "One"}], "search": {"query": "one", "saved_at": "b"}}
    different_query = {"items": [{"course": "One"}], "search": {"query": "two", "saved_at": "b"}}

    assert _cache_content_hash(first) == _cache_content_hash(same_content)
    assert _cache_content_hash(first) != _cache_content_hash(different_query)


def test_stale_source_fallback_reuses_the_first_firestore_read():
    source = {"items": [{"course": "Algorithms"}]}
    snapshot = Mock()
    snapshot.exists = True
    snapshot.to_dict.return_value = {
        "source_gzip": _encode_json_payload(source),
        "updated_at": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    document = Mock()
    document.get.return_value = snapshot
    store = FirestoreStore.__new__(FirestoreStore)
    store.source_cache = Mock()
    store.source_cache.document.return_value = document
    store._source_cache = TTLCache(ttl_seconds=1800, max_entries=4)
    store._source_hashes = TTLCache(ttl_seconds=86400, max_entries=4)

    assert store.get_search_source_cache("student", max_age_seconds=1800) is None
    assert store.get_search_source_cache("student", max_age_seconds=None) == source
    document.get.assert_called_once()
