import threading
import pytest
from minilog.filters import LevelFilter, RateLimitFilter, RegexFilter
from minilog.record import Record


def r(level="info", msg="m"):
    return Record.create(level, msg)


@pytest.mark.parametrize("lvl,ok", [("debug", False), ("info", True), ("error", True)])
def test_level_min(lvl, ok):
    assert LevelFilter("info")(r(lvl)) is ok


def test_level_max():
    f = LevelFilter("info", "warning")
    assert [f(r(x)) for x in ("debug", "info", "warning", "error")] == [False, True, True, False]


def test_level_bad_range():
    with pytest.raises(ValueError):
        LevelFilter("error", "info")


def test_level_bad_name():
    with pytest.raises(ValueError):
        LevelFilter("loud")


def test_regex_match_and_invert():
    assert RegexFilter("^ok")(r(msg="ok go"))
    assert not RegexFilter("^ok")(r(msg="no ok"))
    assert RegexFilter("^ok", invert=True)(r(msg="no ok"))


def test_regex_bad_pattern():
    import re
    with pytest.raises(re.error):
        RegexFilter("(")


def test_regex_unicode():
    assert RegexFilter(r"日本")(r(msg="こんにちは日本"))


def test_ratelimit_basic_window():
    t = [0.0]
    f = RateLimitFilter(2, 1.0, clock=lambda: t[0])
    assert [f(r()) for _ in range(3)] == [True, True, False]
    t[0] = 1.0
    assert f(r())


def test_ratelimit_sliding():
    t = [0.0]
    f = RateLimitFilter(2, 1.0, clock=lambda: t[0])
    f(r()); t[0] = 0.6; f(r()); t[0] = 1.1
    assert f(r()) and not f(r())


@pytest.mark.parametrize("n,w", [(0, 1), (-1, 1), (1, 0), (1, -2)])
def test_ratelimit_invalid(n, w):
    with pytest.raises(ValueError):
        RateLimitFilter(n, w)


def test_ratelimit_threads_never_exceed_limit():
    f = RateLimitFilter(50, 3600)
    results = []
    def work():
        for _ in range(100):
            results.append(f(r()))
    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sum(results) == 50
