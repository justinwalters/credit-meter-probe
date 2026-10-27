from textutil import word_count, char_count, longest_word


def test_wc():
    assert word_count("a b c") == 3


def test_char_count():
    assert char_count("a b\tc\n") == 3
    assert char_count("") == 0


def test_longest_word():
    assert longest_word("a bbb cc ddd") == "bbb"
    assert longest_word("") == ""
