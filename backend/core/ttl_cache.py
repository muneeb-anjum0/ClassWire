"""Small bounded in-process TTL cache used for expensive remote results."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int = 128,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: K) -> Optional[V]:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            created_at, value = entry
            if now - created_at >= self.ttl_seconds:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._entries[key] = (self._clock(), value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def pop(self, key: K) -> Optional[V]:
        now = self._clock()
        with self._lock:
            entry = self._entries.pop(key, None)
            if entry is None:
                return None
            created_at, value = entry
            return value if now - created_at < self.ttl_seconds else None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def discard_where(self, predicate: Callable[[K, V], bool]) -> int:
        """Remove every cached value matching a key-value predicate."""
        with self._lock:
            matching_keys = [
                key
                for key, (_, value) in self._entries.items()
                if predicate(key, value)
            ]
            for key in matching_keys:
                self._entries.pop(key, None)
            return len(matching_keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
