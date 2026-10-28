import math
import re

_WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def _words(s):
    return _WORD_RE.findall(s.casefold())


def word_frequencies(s):
    """Case-insensitive word counts with punctuation stripped."""
    freqs = {}
    for w in _words(s):
        freqs[w] = freqs.get(w, 0) + 1
    return freqs


def top_n(s, n):
    """The n most frequent words as (word, count); ties alphabetical."""
    if n <= 0:
        return []
    items = sorted(word_frequencies(s).items(), key=lambda kv: (-kv[1], kv[0]))
    return items[:n]


def sentence_count(s):
    """Number of non-empty segments split on . ! ?"""
    return sum(1 for part in _SENTENCE_SPLIT_RE.split(s) if part.strip())


def reading_time_minutes(s, wpm=200):
    """Minutes to read, rounded up; at least 1 for non-empty text."""
    if wpm <= 0:
        raise ValueError("wpm must be positive")
    count = len(_words(s))
    if count == 0:
        return 0
    return max(1, math.ceil(count / wpm))


def summarize(s):
    return {
        "word_frequencies": word_frequencies(s),
        "top_n": top_n(s, 5),
        "sentence_count": sentence_count(s),
        "reading_time_minutes": reading_time_minutes(s),
    }
