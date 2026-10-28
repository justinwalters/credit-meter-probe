"""JSON and key=value formatters.

Field order: timestamp, level, logger, message, then user fields sorted by key.
User fields that collide with a core name are prefixed with ``field_``.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from .record import Record

CORE_KEYS = ("ts", "level", "logger", "msg")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="milliseconds")


def _ordered(record: Record) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = [
        ("ts", _iso(record.timestamp)),
        ("level", record.level_name),
        ("logger", record.logger),
        ("msg", record.message),
    ]
    for key in sorted(record.fields, key=str):
        name = str(key)
        if name in CORE_KEYS:
            name = "field_" + name
        items.append((name, record.fields[key]))
    return items


def _json_default(obj: Any) -> str:
    return repr(obj)


def _sanitize(value: Any) -> Any:
    """Replace non-finite floats so output is strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


class JSONFormatter:
    def __init__(self, ensure_ascii: bool = False, max_message: int | None = None):
        self.ensure_ascii = ensure_ascii
        self.max_message = max_message

    def format(self, record: Record) -> str:
        items = _ordered(record)
        if self.max_message is not None:
            items = [(k, v[: self.max_message] if k == "msg" else v) for k, v in items]
        obj = {k: _sanitize(v) for k, v in items}
        return json.dumps(obj, ensure_ascii=self.ensure_ascii, default=_json_default,
                          allow_nan=False)


_NEEDS_QUOTE = set(' ="\\\n\r\t')


def escape_value(text: str) -> str:
    """Quote and escape a value for key=value output when needed."""
    if text == "" or any(c in _NEEDS_QUOTE or ord(c) < 0x20 or ord(c) == 0x7F for c in text):
        out = []
        for c in text:
            if c == '"':
                out.append('\\"')
            elif c == "\\":
                out.append("\\\\")
            elif c == "\n":
                out.append("\\n")
            elif c == "\r":
                out.append("\\r")
            elif c == "\t":
                out.append("\\t")
            elif ord(c) < 0x20 or ord(c) == 0x7F:
                out.append(f"\\x{ord(c):02x}")
            else:
                out.append(c)
        return '"' + "".join(out) + '"'
    return text


def _escape_key(key: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c in "_.-") else "_" for c in key)
    return cleaned or "_"


class KeyValueFormatter:
    def __init__(self, max_message: int | None = None):
        self.max_message = max_message

    def format(self, record: Record) -> str:
        parts = []
        for key, value in _ordered(record):
            text = value if isinstance(value, str) else str(value)
            if key == "msg" and self.max_message is not None:
                text = text[: self.max_message]
            parts.append(f"{_escape_key(key)}={escape_value(text)}")
        return " ".join(parts)
