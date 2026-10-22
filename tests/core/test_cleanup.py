from vat_number_validator._cleanup import SEPARATORS, ascii_upper, php_trim, remove_separators


def test_separators() -> None:
    expected = {
        chr(c)
        for c in [
            *range(9, 14),
            0x20,
            0x2D,
            0x2E,
            0x85,
            0xA0,
            0x1680,
            *range(0x2000, 0x200B),
            0x2028,
            0x2029,
            0x202F,
            0x205F,
            0x3000,
        ]
    }
    assert expected == SEPARATORS
    assert len(SEPARATORS) == 27
    assert isinstance(SEPARATORS, frozenset)
    assert remove_separators("FR" + "".join(expected) + "27552032534") == "FR27552032534"
    assert remove_separators("a\x1c\u180e\u200b\ufeff") == "a\x1c\u180e\u200b\ufeff"


def test_ascii_upper() -> None:
    assert ascii_upper("ß\u0131\u017fﬀabc") == "ß\u0131\u017fﬀABC"


def test_php_trim() -> None:
    assert php_trim(" \t\n\r\0\x0bFR \t\n\r\0\x0b") == "FR"
    assert php_trim("\xa0FR\x1c") == "\xa0FR\x1c"
