from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic


class RateLimitExceeded(RuntimeError):
    pass


class SlidingWindowRateLimiter:
    """Thread-safe, process-wide limiter for upstream API cache misses."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = max(1, int(limit))
        self.window_seconds = float(window_seconds)
        self._events: deque[float] = deque()
        self._lock = Lock()

    def acquire(self) -> None:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            while self._events and self._events[0] <= cutoff:
                self._events.popleft()
            if len(self._events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - self._events[0])))
                raise RateLimitExceeded(f"Market-data request limit reached. Try again in about {retry_after} seconds.")
            self._events.append(now)

    def remaining(self) -> int:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            while self._events and self._events[0] <= cutoff:
                self._events.popleft()
            return max(0, self.limit - len(self._events))
