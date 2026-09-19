from database.firestore_store import (
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
