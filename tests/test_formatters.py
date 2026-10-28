import json
import pytest
from minilog.formatters import JSONFormatter, KeyValueFormatter, escape_value
from minilog.record import Record


def rec(msg="hello", **f):
    return Record.create("info", msg, "app", 0.0, **f)


def test_json_field_order():
    out = JSONFormatter().format(rec(z=1, a=2))
    assert list(json.loads(out)) == ["ts", "level", "logger", "msg", "a", "z"]


def test_json_timestamp_iso():
    assert json.loads(JSONFormatter().format(rec()))["ts"] == "1970-01-01T00:00:00.000+00:00"


def test_json_unicode_preserved():
    out = JSONFormatter().format(rec("héllo 日本 😀"))
    assert "日本" in out and json.loads(out)["msg"] == "héllo 日本 😀"


def test_json_ensure_ascii():
    out = JSONFormatter(ensure_ascii=True).format(rec("é"))
    assert out.isascii() and json.loads(out)["msg"] == "é"


def test_json_escapes_control_chars():
    out = JSONFormatter().format(rec('a"b\n\x01'))
    assert "\n" not in out and json.loads(out)["msg"] == 'a"b\n\x01'


def test_json_collision_prefix():
    d = json.loads(JSONFormatter().format(Record(20, "m", "app", 0.0, {"level": "x"})))
    assert d["level"] == "INFO" and d["field_level"] == "x"


def test_json_unserializable_uses_repr():
    d = json.loads(JSONFormatter().format(rec(o=object)))
    assert "object" in d["o"]


@pytest.mark.parametrize("v", [float("nan"), float("inf"), float("-inf")])
def test_json_nonfinite_is_strict(v):
    out = JSONFormatter().format(rec(x=v, n=[v], m={"k": v}))
    json.loads(out, parse_constant=lambda c: pytest.fail("non-strict constant"))


def test_json_huge_message():
    big = "x" * 1_000_000
    assert len(json.loads(JSONFormatter().format(rec(big)))["msg"]) == 1_000_000


def test_json_max_message_truncates():
    assert json.loads(JSONFormatter(max_message=5).format(rec("abcdefgh")))["msg"] == "abcde"


def test_json_non_string_keys():
    d = json.loads(JSONFormatter().format(Record.create("info", "m", "root", 0, **{"k": {1: 2}})))
    assert d["k"] == {"1": 2}


def test_kv_basic_order():
    out = KeyValueFormatter().format(rec(b=2, a=1))
    assert out == "ts=1970-01-01T00:00:00.000+00:00 level=INFO logger=app msg=hello a=1 b=2"


def test_kv_quotes_spaces():
    assert 'msg="hello world"' in KeyValueFormatter().format(rec("hello world"))


@pytest.mark.parametrize("raw,exp", [
    ("plain", "plain"), ("", '""'), ("a b", '"a b"'), ("a=b", '"a=b"'),
    ('q"q', '"q\\"q"'), ("back\\slash", '"back\\\\slash"'), ("l\nl", '"l\\nl"'),
    ("c\rr", '"c\\rr"'), ("t\tt", '"t\\tt"'), ("\x00", '"\\x00"'), ("\x7f", '"\\x7f"'),
    ("日本", "日本"),
])
def test_escape_value(raw, exp):
    assert escape_value(raw) == exp


def test_kv_single_line_for_newlines():
    assert "\n" not in KeyValueFormatter().format(rec("a\nb\r\nc"))


def test_kv_key_sanitized():
    out = KeyValueFormatter().format(rec(**{"bad key=x": 1, "": 2}))
    assert "bad_key_x=1" in out and " _=2" in out


def test_kv_collision_prefix():
    assert "field_msg=x" in KeyValueFormatter().format(Record(20, "m", "app", 0.0, {"msg": "x"}))


def test_kv_max_message():
    assert "msg=abc" in KeyValueFormatter(max_message=3).format(rec("abcdef"))


def test_kv_non_string_values():
    assert "n=5" in KeyValueFormatter().format(rec(n=5))
