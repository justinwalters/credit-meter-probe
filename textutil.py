def word_count(s):
    return len(s.split())


def char_count(s):
    return sum(1 for c in s if not c.isspace())


def longest_word(s):
    words = s.split()
    return max(words, key=len) if words else ""
