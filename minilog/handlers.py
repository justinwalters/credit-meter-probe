"""Stream and size-rotating file handlers."""
from __future__ import annotations

import os
import threading
from typing import IO, Callable, Iterable

from .record import Record


class Handler:
    def __init__(self, formatter, filters: Iterable[Callable[[Record], bool]] = ()):
        self.formatter = formatter
        self.filters = list(filters)
        self._lock = threading.RLock()

    def handle(self, record: Record) -> bool:
        if not all(f(record) for f in self.filters):
            return False
        line = self.formatter.format(record)
        with self._lock:
            self.emit(line + "\n")
        return True

    def emit(self, text: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:
        pass


class StreamHandler(Handler):
    def __init__(self, stream: IO[str], formatter, filters=()):
        super().__init__(formatter, filters)
        self.stream = stream

    def emit(self, text: str) -> None:
        self.stream.write(text)
        self.stream.flush()


class RotatingFileHandler(Handler):
    """Appends to ``path``; rotates to path.1 .. path.N when size would exceed max_bytes.

    A single line larger than max_bytes is written to a fresh file on its own
    (never split), so the limit is soft for oversized lines.
    """

    def __init__(self, path: str, formatter, max_bytes: int = 1_000_000,
                 backup_count: int = 3, filters=(), encoding: str = "utf-8"):
        super().__init__(formatter, filters)
        if max_bytes < 1:
            raise ValueError("max_bytes must be >= 1")
        if backup_count < 0:
            raise ValueError("backup_count must be >= 0")
        self.path = os.fspath(path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding
        self._fh: IO[str] | None = None
        self._size = 0
        self._open()

    def _open(self) -> None:
        # O_NOFOLLOW refuses to write through a symlink planted at the log path.
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        self._fh = os.fdopen(fd, "a", encoding=self.encoding, newline="")
        self._size = os.fstat(fd).st_size

    def _rotate(self) -> None:
        assert self._fh is not None
        self._fh.close()
        self._fh = None
        if self.backup_count == 0:
            os.remove(self.path)
        else:
            for i in range(self.backup_count - 1, 0, -1):
                src, dst = f"{self.path}.{i}", f"{self.path}.{i + 1}"
                if os.path.exists(src):
                    os.replace(src, dst)
            os.replace(self.path, f"{self.path}.1")
        self._open()

    def emit(self, text: str) -> None:
        if self._fh is None:
            raise ValueError("handler is closed")
        n = len(text.encode(self.encoding))
        if self._size > 0 and self._size + n > self.max_bytes:
            self._rotate()
        self._fh.write(text)
        self._fh.flush()
        self._size += n

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None
