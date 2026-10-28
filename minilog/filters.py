"""Level, regex and rate-limit filters. A filter is a callable Record -> bool."""
from __future__ import annotations

import re
import threading
import time
from typing import Callable

from .record import Record, level_value


class LevelFilter:
    def __init__(self, min_level: int | str = "DEBUG", max_level: int | str | None = None):
        self.min_level = level_value(min_level)
        self.max_level = None if max_level is None else level_value(max_level)
        if self.max_level is not None and self.max_level < self.min_level:
            raise ValueError("max_level below min_level")

    def __call__(self, record: Record) -> bool:
        if record.level < self.min_level:
            return False
        return self.max_level is None or record.level <= self.max_level


class RegexFilter:
    """Passes records whose message matches (or, with ``invert``, does not)."""

    def __init__(self, pattern: str, invert: bool = False):
        self.pattern = re.compile(pattern)
        self.invert = invert

    def __call__(self, record: Record) -> bool:
        matched = self.pattern.search(record.message) is not None
        return matched != self.invert


class RateLimitFilter:
    """Allow at most ``max_per_window`` records per ``window`` seconds (sliding)."""

    def __init__(self, max_per_window: int, window: float = 1.0,
                 clock: Callable[[], float] = time.monotonic):
        if max_per_window < 1:
            raise ValueError("max_per_window must be >= 1")
        if window <= 0:
            raise ValueError("window must be > 0")
        self.max = max_per_window
        self.window = window
        self._clock = clock
        self._lock = threading.Lock()
        self._stamps: list[float] = []

    def __call__(self, record: Record) -> bool:
        now = self._clock()
        with self._lock:
            cutoff = now - self.window
            self._stamps = [t for t in self._stamps if t > cutoff]
            if len(self._stamps) >= self.max:
                return False
            self._stamps.append(now)
            return True
