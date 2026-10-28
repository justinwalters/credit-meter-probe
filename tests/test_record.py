import pytest
from minilog.record import Record, level_value, level_name


@pytest.mark.parametrize("v,n", [("debug", 10), ("INFO", 20), ("Warning", 30), (45, 45)])
def test_level_value(v, n):
    assert level_value(v) == n


@pytest.mark.parametrize("bad", ["nope", None, 1.5, True, ""])
def test_level_value_invalid(bad):
    with pytest.raises(ValueError):
        level_value(bad)


def test_level_name_known_and_unknown():
    assert level_name(40) == "ERROR"
    assert level_name(33) == "LEVEL33"


def test_create_coerces_message():
    r = Record.create("info", 123, a=1)
    assert r.message == "123" and r.fields == {"a": 1} and r.level == 20


def test_record_frozen():
    r = Record.create("info", "x")
    with pytest.raises(Exception):
        r.message = "y"


def test_create_copies_fields():
    d = {"a": 1}
    r = Record.create("info", "x", **d)
    d["a"] = 2
    assert r.fields["a"] == 1
