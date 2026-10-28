"""Strict config loading. Unknown keys and wrong types are rejected.

Example::

    {"formatter": "json", "level": "INFO",
     "handler": {"type": "file", "path": "app.log", "max_bytes": 1000, "backup_count": 2},
     "filters": {"regex": "^ok", "rate_limit": {"max": 5, "window": 1.0}}}
"""
from __future__ import annotations

import re
import sys
from typing import Any

from .filters import LevelFilter, RateLimitFilter, RegexFilter
from .formatters import JSONFormatter, KeyValueFormatter
from .handlers import RotatingFileHandler, StreamHandler
from .record import level_value


class ConfigError(ValueError):
    pass


def _check_keys(section: str, data: Any, allowed: set[str], required: set[str] = frozenset()) -> None:
    if not isinstance(data, dict):
        raise ConfigError(f"{section}: expected object, got {type(data).__name__}")
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"{section}: unknown keys: {sorted(map(str, unknown))}")
    missing = required - set(data)
    if missing:
        raise ConfigError(f"{section}: missing keys: {sorted(missing)}")


def _int(section: str, key: str, value: Any, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{section}.{key}: expected integer")
    if value < minimum:
        raise ConfigError(f"{section}.{key}: must be >= {minimum}")
    return value


def _num(section: str, key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{section}.{key}: expected number")
    if value != value or value in (float("inf"), float("-inf")) or value <= 0:
        raise ConfigError(f"{section}.{key}: must be a positive finite number")
    return float(value)


def _level(section: str, key: str, value: Any) -> int:
    try:
        return level_value(value)
    except ValueError as e:
        raise ConfigError(f"{section}.{key}: {e}") from None


def validate(config: Any) -> dict:
    """Return a normalized copy of config or raise ConfigError."""
    _check_keys("config", config, {"formatter", "level", "handler", "filters"}, {"handler"})
    out: dict[str, Any] = {}
    fmt = config.get("formatter", "json")
    if fmt not in ("json", "kv"):
        raise ConfigError("config.formatter: must be 'json' or 'kv'")
    out["formatter"] = fmt
    out["level"] = _level("config", "level", config.get("level", "DEBUG"))

    h = config["handler"]
    _check_keys("handler", h, {"type", "path", "max_bytes", "backup_count"}, {"type"})
    htype = h["type"]
    if htype == "stream":
        extra = set(h) - {"type"}
        if extra:
            raise ConfigError(f"handler: keys not valid for stream: {sorted(extra)}")
        out["handler"] = {"type": "stream"}
    elif htype == "file":
        path = h.get("path")
        if not isinstance(path, str) or not path or "\x00" in path:
            raise ConfigError("handler.path: expected non-empty string")
        out["handler"] = {
            "type": "file", "path": path,
            "max_bytes": _int("handler", "max_bytes", h.get("max_bytes", 1_000_000), 1),
            "backup_count": _int("handler", "backup_count", h.get("backup_count", 3), 0),
        }
    else:
        raise ConfigError("handler.type: must be 'stream' or 'file'")

    f = config.get("filters", {})
    _check_keys("filters", f, {"regex", "rate_limit"})
    of: dict[str, Any] = {}
    if "regex" in f:
        if not isinstance(f["regex"], str):
            raise ConfigError("filters.regex: expected string")
        try:
            re.compile(f["regex"])
        except re.error as e:
            raise ConfigError(f"filters.regex: invalid pattern: {e}") from None
        of["regex"] = f["regex"]
    if "rate_limit" in f:
        r = f["rate_limit"]
        _check_keys("filters.rate_limit", r, {"max", "window"}, {"max"})
        of["rate_limit"] = {"max": _int("filters.rate_limit", "max", r["max"], 1),
                            "window": _num("filters.rate_limit", "window", r.get("window", 1.0))}
    out["filters"] = of
    return out


def build_handler(config: dict, stream=None):
    cfg = validate(config)
    formatter = JSONFormatter() if cfg["formatter"] == "json" else KeyValueFormatter()
    filters = [LevelFilter(cfg["level"])]
    if "regex" in cfg["filters"]:
        filters.append(RegexFilter(cfg["filters"]["regex"]))
    if "rate_limit" in cfg["filters"]:
        rl = cfg["filters"]["rate_limit"]
        filters.append(RateLimitFilter(rl["max"], rl["window"]))
    h = cfg["handler"]
    if h["type"] == "stream":
        return StreamHandler(stream or sys.stderr, formatter, filters)
    return RotatingFileHandler(h["path"], formatter, h["max_bytes"], h["backup_count"], filters)
