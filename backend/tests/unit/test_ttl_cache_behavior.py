import pytest

from core.ttl_cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_ttl_cache_expires_entries_without_sleeping():
    clock = FakeClock()
    cache = TTLCache[str, int](ttl_seconds=10, max_entries=2, clock=clock)
    cache.set("answer", 42)

    clock.now = 9.99
    assert cache.get("answer") == 42
    clock.now = 10
    assert cache.get("answer") is None


def test_ttl_cache_is_bounded_and_refreshes_recently_read_keys():
    clock = FakeClock()
    cache = TTLCache[str, int](ttl_seconds=10, max_entries=2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


def test_ttl_cache_rejects_invalid_limits():
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=1, max_entries=0)


def test_pop_does_not_return_expired_values():
    clock = FakeClock()
    cache = TTLCache[str, int](ttl_seconds=2, clock=clock)
    cache.set("state", 1)
    clock.now = 2

    assert cache.pop("state") is None
