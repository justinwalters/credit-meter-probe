"""Log record dataclass and level definitions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
_NAMES = {v: k for k, v in LEVELS.items()}


def level_value(level: int | str) -> int:
    """Return numeric level for a name or int. Raises ValueError if unknown."""
    if isinstance(level, bool):
        raise ValueError(f"invalid level: {level!r}")
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        try:
            return LEVELS[level.upper()]
        except KeyError:
            pass
    raise ValueError(f"invalid level: {level!r}")


def level_name(value: int) -> str:
    return _NAMES.get(value, f"LEVEL{value}")


@dataclass(frozen=True)
class Record:
    level: int
    message: str
    logger: str = "root"
    timestamp: float = field(default_factory=time.time)
    fields: dict[str, Any] = field(default_factory=dict)

    @property
    def level_name(self) -> str:
        return level_name(self.level)

    @classmethod
    def create(cls, level: int | str, message: str, logger: str = "root",
               timestamp: float | None = None, **fields: Any) -> "Record":
        return cls(
            level=level_value(level),
            message=str(message),
            logger=logger,
            timestamp=time.time() if timestamp is None else timestamp,
            fields=dict(fields),
        )
