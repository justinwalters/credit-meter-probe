import json
import os
import pytest
from minilog import JSONFormatter, KeyValueFormatter, Record, RotatingFileHandler


def test_fields_named_like_create_params():
    r = Record.create("info", "m", level="x", message="y", logger="z", timestamp="t")
    assert r.fields == {"level": "x", "message": "y", "logger": "z", "timestamp": "t"}
    assert r.message == "m"


def test_circular_reference_does_not_crash_json():
    d = {}
    d["self"] = d
    out = JSONFormatter().format(Record.create("info", "m", d=d))
    assert json.loads(out)["msg"] == "m"


def test_lone_surrogate_message_written(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), JSONFormatter(), max_bytes=10_000)
    h.handle(Record.create("info", "bad \ud800 char"))
    h.close()
    assert h._size == p.stat().st_size and p.stat().st_size > 0


def test_lone_surrogate_kv(tmp_path):
    h = RotatingFileHandler(str(tmp_path / "a.log"), KeyValueFormatter())
    assert h.handle(Record.create("info", "\udfff"))
    h.close()


def test_handler_usable_after_failed_rotation(tmp_path, monkeypatch):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), KeyValueFormatter(), max_bytes=1, backup_count=1)
    h.handle(Record.create("info", "a"))
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        h.handle(Record.create("info", "b"))
    monkeypatch.setattr(os, "replace", real)
    assert h.handle(Record.create("info", "c"))
    h.close()
