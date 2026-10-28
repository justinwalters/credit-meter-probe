import io
import json
import pytest
from minilog import ConfigError, build_handler, validate
from minilog.handlers import RotatingFileHandler, StreamHandler

OK = {"handler": {"type": "stream"}}


def test_minimal_defaults():
    v = validate(OK)
    assert v["formatter"] == "json" and v["level"] == 10 and v["filters"] == {}


def test_does_not_mutate_input():
    c = {"handler": {"type": "file", "path": "x"}}
    validate(c)
    assert c == {"handler": {"type": "file", "path": "x"}}


@pytest.mark.parametrize("bad", [None, [], "s", 3])
def test_top_level_not_object(bad):
    with pytest.raises(ConfigError):
        validate(bad)


def test_unknown_top_key():
    with pytest.raises(ConfigError, match="unknown"):
        validate({**OK, "extra": 1})


def test_missing_handler():
    with pytest.raises(ConfigError, match="missing"):
        validate({})


def test_unknown_handler_key():
    with pytest.raises(ConfigError, match="unknown"):
        validate({"handler": {"type": "stream", "colour": 1}})


def test_stream_rejects_file_keys():
    with pytest.raises(ConfigError):
        validate({"handler": {"type": "stream", "path": "x"}})


@pytest.mark.parametrize("t", ["socket", None, 1, ""])
def test_bad_handler_type(t):
    with pytest.raises(ConfigError):
        validate({"handler": {"type": t}})


@pytest.mark.parametrize("p", [None, "", 5, "a\x00b"])
def test_bad_path(p):
    with pytest.raises(ConfigError):
        validate({"handler": {"type": "file", "path": p}})


def test_file_missing_path():
    with pytest.raises(ConfigError):
        validate({"handler": {"type": "file"}})


@pytest.mark.parametrize("k,v", [("max_bytes", 0), ("max_bytes", "9"), ("max_bytes", True),
                                 ("max_bytes", 1.5), ("backup_count", -1), ("backup_count", None)])
def test_bad_numbers(k, v):
    with pytest.raises(ConfigError):
        validate({"handler": {"type": "file", "path": "x", k: v}})


@pytest.mark.parametrize("f", ["xml", 1, None])
def test_bad_formatter(f):
    with pytest.raises(ConfigError):
        validate({**OK, "formatter": f})


@pytest.mark.parametrize("lv", ["loud", None, 2.5, True])
def test_bad_level(lv):
    with pytest.raises(ConfigError):
        validate({**OK, "level": lv})


def test_bad_regex():
    with pytest.raises(ConfigError, match="invalid pattern"):
        validate({**OK, "filters": {"regex": "("}})


def test_regex_not_string():
    with pytest.raises(ConfigError):
        validate({**OK, "filters": {"regex": 3}})


def test_unknown_filter_key():
    with pytest.raises(ConfigError):
        validate({**OK, "filters": {"bogus": 1}})


@pytest.mark.parametrize("rl", [{}, {"max": 0}, {"max": 1, "window": 0}, {"max": 1, "window": "1"},
                                {"max": 1, "window": float("nan")}, {"max": 1, "window": float("inf")},
                                {"max": 1, "extra": 1}, 5])
def test_bad_rate_limit(rl):
    with pytest.raises(ConfigError):
        validate({**OK, "filters": {"rate_limit": rl}})


def test_build_stream_end_to_end():
    s = io.StringIO()
    h = build_handler({"formatter": "kv", "level": "warning", "handler": {"type": "stream"}}, stream=s)
    assert isinstance(h, StreamHandler)
    from minilog import Record
    h.handle(Record.create("info", "no")); h.handle(Record.create("error", "yes"))
    assert "msg=yes" in s.getvalue() and "msg=no" not in s.getvalue()


def test_build_file_with_filters(tmp_path):
    from minilog import Record
    h = build_handler({"handler": {"type": "file", "path": str(tmp_path / "l"), "max_bytes": 5000},
                       "filters": {"regex": "^keep", "rate_limit": {"max": 2}}})
    assert isinstance(h, RotatingFileHandler)
    assert [h.handle(Record.create("info", m)) for m in ("keep1", "drop", "keep2", "keep3")] == \
        [True, False, True, False]
    h.close()
    assert len((tmp_path / "l").read_text().splitlines()) == 2
    json.loads((tmp_path / "l").read_text().splitlines()[0])
