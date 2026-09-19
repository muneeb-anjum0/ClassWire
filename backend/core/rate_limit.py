"""Small bounded token-bucket limiter for expensive authenticated endpoints."""

from __future__ import annotations

import threading
import time
from typing import Callable

from .ttl_cache import TTLCache


class TokenBucketRateLimiter:
    def __init__(
        self,
        *,
        capacity: float,
        refill_per_second: float,
        max_keys: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill_per_second must be positive")
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._clock = clock
        self._buckets = TTLCache[str, tuple[float, float]](
            ttl_seconds=max(60, capacity / refill_per_second * 4),
            max_entries=max_keys,
            clock=clock,
        )
        self._lock = threading.Lock()

    def allow(self, key: str, *, cost: float = 1) -> bool:
        if cost <= 0:
            return True
        now = self._clock()
        with self._lock:
            previous = self._buckets.get(key)
            if previous is None:
                tokens, last_updated = self.capacity, now
            else:
                tokens, last_updated = previous
                tokens = min(
                    self.capacity,
                    tokens + max(0, now - last_updated) * self.refill_per_second,
                )
            allowed = tokens >= cost
            if allowed:
                tokens -= cost
            self._buckets.set(key, (tokens, now))
            return allowed
