"""Tiny in-memory LRU+TTL cache for hot pipeline results."""
from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Generic, Hashable, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, max_size: int = 128, ttl_seconds: float = 300.0) -> None:
        self._max_size = max(1, max_size)
        self._ttl = max(0.0, ttl_seconds)
        self._store: "OrderedDict[Hashable, tuple[T, float]]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: Hashable) -> T | None:
        now = time.monotonic()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at < now:
                self._store.pop(key, None)
                return None
            # mark as recently used
            self._store.move_to_end(key)
            return value

    def set(self, key: Hashable, value: T) -> None:
        expires_at = time.monotonic() + self._ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"size": len(self._store), "max_size": self._max_size, "ttl_seconds": self._ttl}
