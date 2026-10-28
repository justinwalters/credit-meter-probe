# minilog self-review

Every file in `minilog/` was read for bugs, races and unsafe file handling.

## Fixed (each has a test in `tests/test_review_fixes.py`)

1. **Rotation failure bricked the handler** (`handlers.py`). If `os.replace` raised mid-rotation, `_fh` stayed `None` and every later write failed with "closed". The file is now reopened in a `finally`.
2. **Lone surrogates crashed emit** (`handlers.py`). `text.encode()` and the file write raised `UnicodeEncodeError` for strings like `"\ud800"`. Size counting and the file now use `backslashreplace`.
3. **Circular or pathological field values crashed JSON formatting** (`formatters.py`). `ValueError` or `RecursionError` escaped to the caller. It now falls back to `repr()` for non-scalar fields.
4. **`Record.create` could not accept fields named `level`, `message`, `logger` or `timestamp`** (`record.py`). They collided with its own parameters. Those parameters are now positional-only.

## Reviewed, not changed (documented limits)

5. Rotation is thread-safe but not multi-process safe. Two processes sharing one path can both rotate. Use one writer per file.
6. `O_NOFOLLOW` only protects the final path component. A symlinked parent directory is still followed.
7. No `fsync`: records can be lost on power failure. This is a deliberate speed trade-off.
8. `RegexFilter` and the config `regex` accept user patterns, so a catastrophic-backtracking pattern can stall logging. Config is trusted input.
9. `RateLimitFilter` rebuilds its list on every call, which is O(max). A `deque` would be better for very large limits.
10. `KeyValueFormatter` key sanitising can merge distinct keys (`"a b"` and `"a_b"`), producing duplicate keys.
11. I/O errors from `emit` (for example a full disk) propagate to the caller. That is intentional, but a wrapper may want to swallow them.
