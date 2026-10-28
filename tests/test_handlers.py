import io
import os
import threading
import pytest
from minilog.formatters import JSONFormatter, KeyValueFormatter
from minilog.handlers import RotatingFileHandler, StreamHandler
from minilog.filters import LevelFilter
from minilog.record import Record

FMT = KeyValueFormatter()


def r(msg="m", level="info"):
    return Record.create(level, msg, timestamp=0)


def test_stream_writes_line():
    s = io.StringIO()
    assert StreamHandler(s, FMT).handle(r("hi"))
    assert s.getvalue().endswith("msg=hi\n")


def test_stream_filtered():
    s = io.StringIO()
    h = StreamHandler(s, FMT, [LevelFilter("error")])
    assert not h.handle(r()) and s.getvalue() == ""


def test_file_creates_and_appends(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), FMT); h.handle(r("1")); h.close()
    h = RotatingFileHandler(str(p), FMT); h.handle(r("2")); h.close()
    assert len(p.read_text().splitlines()) == 2


def test_file_permissions(tmp_path):
    p = tmp_path / "a.log"
    RotatingFileHandler(str(p), FMT).close()
    assert (os.stat(p).st_mode & 0o777) == 0o600


def test_file_refuses_symlink(tmp_path):
    target = tmp_path / "target"; target.write_text("x")
    link = tmp_path / "link.log"; link.symlink_to(target)
    with pytest.raises(OSError):
        RotatingFileHandler(str(link), FMT)
    assert target.read_text() == "x"


def _line_len(msg="x"):
    return len(FMT.format(r(msg))) + 1


def test_rotation_boundary_exact_fit_no_rotate(tmp_path):
    p = tmp_path / "a.log"; n = _line_len()
    h = RotatingFileHandler(str(p), FMT, max_bytes=2 * n, backup_count=2)
    h.handle(r("x")); h.handle(r("x")); h.close()
    assert not os.path.exists(f"{p}.1") and p.stat().st_size == 2 * n


def test_rotation_boundary_one_over_rotates(tmp_path):
    p = tmp_path / "a.log"; n = _line_len()
    h = RotatingFileHandler(str(p), FMT, max_bytes=2 * n, backup_count=2)
    for _ in range(3):
        h.handle(r("x"))
    h.close()
    assert os.path.exists(f"{p}.1") and p.stat().st_size == n


def test_rotation_keeps_backup_count(tmp_path):
    p = tmp_path / "a.log"; n = _line_len("x")
    h = RotatingFileHandler(str(p), FMT, max_bytes=n, backup_count=2)
    for i in range(6):
        h.handle(r("x"))
    h.close()
    assert sorted(os.listdir(tmp_path)) == ["a.log", "a.log.1", "a.log.2"]


def test_rotation_order_newest_in_dot1(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), FMT, max_bytes=1, backup_count=3)
    for m in "abc":
        h.handle(r(m))
    h.close()
    assert "msg=c" in p.read_text()
    assert "msg=b" in (tmp_path / "a.log.1").read_text()
    assert "msg=a" in (tmp_path / "a.log.2").read_text()


def test_rotation_backup_zero_truncates(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), FMT, max_bytes=1, backup_count=0)
    for m in "abc":
        h.handle(r(m))
    h.close()
    assert os.listdir(tmp_path) == ["a.log"] and "msg=c" in p.read_text()


def test_oversized_line_not_split(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), FMT, max_bytes=50, backup_count=1)
    h.handle(r("y" * 10_000)); h.handle(r("z")); h.close()
    assert len((tmp_path / "a.log.1").read_text().splitlines()) == 1


def test_size_counts_bytes_not_chars(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), JSONFormatter(), max_bytes=10_000)
    h.handle(r("日本語")); h.close()
    assert h._size == p.stat().st_size


def test_resume_size_from_existing_file(tmp_path):
    p = tmp_path / "a.log"; n = _line_len()
    h = RotatingFileHandler(str(p), FMT, max_bytes=2 * n); h.handle(r("x")); h.handle(r("x")); h.close()
    h = RotatingFileHandler(str(p), FMT, max_bytes=2 * n); h.handle(r("x")); h.close()
    assert os.path.exists(f"{p}.1")


def test_write_after_close_raises(tmp_path):
    h = RotatingFileHandler(str(tmp_path / "a.log"), FMT); h.close()
    with pytest.raises(ValueError):
        h.handle(r())


def test_close_idempotent(tmp_path):
    h = RotatingFileHandler(str(tmp_path / "a.log"), FMT); h.close(); h.close()


@pytest.mark.parametrize("kw", [{"max_bytes": 0}, {"backup_count": -1}])
def test_invalid_params(tmp_path, kw):
    with pytest.raises(ValueError):
        RotatingFileHandler(str(tmp_path / "a.log"), FMT, **kw)


def test_concurrent_writers_no_lost_or_torn_lines(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), JSONFormatter(), max_bytes=10**9)
    def work(t):
        for i in range(200):
            h.handle(Record.create("info", f"t{t}-{i}-" + "p" * 200))
    ts = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]; h.close()
    import json
    lines = p.read_text().splitlines()
    assert len(lines) == 1600
    assert len({json.loads(l)["msg"] for l in lines}) == 1600


def test_concurrent_with_rotation_no_loss(tmp_path):
    p = tmp_path / "a.log"
    h = RotatingFileHandler(str(p), FMT, max_bytes=2000, backup_count=500)
    def work(t):
        for i in range(100):
            h.handle(r(f"t{t}i{i}"))
    ts = [threading.Thread(target=work, args=(t,)) for t in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]; h.close()
    total = 0
    for f in os.listdir(tmp_path):
        total += len((tmp_path / f).read_text().splitlines())
    assert total == 600


def test_concurrent_stream_lines_intact():
    s = io.StringIO()
    h = StreamHandler(s, FMT)
    ts = [threading.Thread(target=lambda: [h.handle(r("abc")) for _ in range(300)]) for _ in range(5)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert all(l.endswith("msg=abc") for l in s.getvalue().splitlines())
    assert len(s.getvalue().splitlines()) == 1500
