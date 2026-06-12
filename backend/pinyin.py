from __future__ import annotations


GBK_INITIAL_RANGES = [
    (-20319, "a"),
    (-20283, "b"),
    (-19775, "c"),
    (-19218, "d"),
    (-18710, "e"),
    (-18526, "f"),
    (-18239, "g"),
    (-17922, "h"),
    (-17417, "j"),
    (-16474, "k"),
    (-16212, "l"),
    (-15640, "m"),
    (-15165, "n"),
    (-14922, "o"),
    (-14914, "p"),
    (-14630, "q"),
    (-14149, "r"),
    (-14090, "s"),
    (-13318, "t"),
    (-12838, "w"),
    (-12556, "x"),
    (-11847, "y"),
    (-11055, "z"),
]


PINYIN_INITIAL_OVERRIDES = {
    "泓": "h",
}


def pinyin_initials(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    try:
        from pypinyin import Style, lazy_pinyin

        return "".join(
            lazy_pinyin(
                text,
                style=Style.FIRST_LETTER,
                errors=lambda chars: [fallback_initial(char) for char in chars],
            )
        ).lower()
    except Exception:
        return "".join(fallback_initial(char) for char in text).lower()


def fallback_initial(char: str) -> str:
    if not char:
        return ""
    if char in PINYIN_INITIAL_OVERRIDES:
        return PINYIN_INITIAL_OVERRIDES[char]
    if char.isascii():
        return char.lower() if char.isalnum() else ""
    try:
        encoded = char.encode("gbk")
    except UnicodeEncodeError:
        return ""
    if len(encoded) == 1:
        return char.lower() if char.isalnum() else ""

    code = encoded[0] * 256 + encoded[1] - 65536
    initial = ""
    for start, letter in GBK_INITIAL_RANGES:
        if code >= start:
            initial = letter
        else:
            break
    return initial
