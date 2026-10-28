import pytest

from textstats import (
    reading_time_minutes,
    sentence_count,
    summarize,
    top_n,
    word_frequencies,
)


def test_freq_basic():
    assert word_frequencies("a b a") == {"a": 2, "b": 1}


def test_freq_case_insensitive():
    assert word_frequencies("The the THE") == {"the": 3}


def test_freq_punctuation_stripped():
    assert word_frequencies("Hello, world! Hello.") == {"hello": 2, "world": 1}


def test_freq_empty():
    assert word_frequencies("") == {}
    assert word_frequencies("  ...  ") == {}


def test_freq_unicode():
    assert word_frequencies("Élan élan naïve 日本語") == {"élan": 2, "naïve": 1, "日本語": 1}


def test_freq_apostrophe():
    assert word_frequencies("don't Don't") == {"don't": 2}


def test_top_n_order_and_ties():
    assert top_n("b a c a b", 3) == [("a", 2), ("b", 2), ("c", 1)]


def test_top_n_larger_than_vocab():
    assert top_n("x y", 10) == [("x", 1), ("y", 1)]


def test_top_n_zero_negative_empty():
    assert top_n("a b", 0) == []
    assert top_n("a b", -1) == []
    assert top_n("", 3) == []


def test_sentence_count_basic():
    assert sentence_count("One. Two! Three?") == 3


def test_sentence_count_repeated_punctuation():
    assert sentence_count("What?!?! Really... Yes.") == 3


def test_sentence_count_empty_and_blank():
    assert sentence_count("") == 0
    assert sentence_count(" . ! ? ") == 0


def test_sentence_count_no_terminator():
    assert sentence_count("no ending") == 1


def test_reading_time_min_one():
    assert reading_time_minutes("hi") == 1


def test_reading_time_empty():
    assert reading_time_minutes("") == 0
    assert reading_time_minutes("...") == 0


def test_reading_time_rounds_up():
    assert reading_time_minutes("w " * 200) == 1
    assert reading_time_minutes("w " * 201) == 2


def test_reading_time_custom_wpm():
    assert reading_time_minutes("w " * 10, wpm=5) == 2


def test_reading_time_bad_wpm():
    with pytest.raises(ValueError):
        reading_time_minutes("hi", wpm=0)


def test_large_input():
    text = "alpha beta. " * 50000
    assert word_frequencies(text) == {"alpha": 50000, "beta": 50000}
    assert sentence_count(text) == 50000
    assert reading_time_minutes(text) == 500


def test_summarize():
    s = summarize("Hi there. Hi!")
    assert s == {
        "word_frequencies": {"hi": 2, "there": 1},
        "top_n": [("hi", 2), ("there", 1)],
        "sentence_count": 2,
        "reading_time_minutes": 1,
    }


def test_summarize_empty():
    assert summarize("") == {
        "word_frequencies": {},
        "top_n": [],
        "sentence_count": 0,
        "reading_time_minutes": 0,
    }
