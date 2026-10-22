# PHP VatNumber::clean(): PCRE [\p{Z}\x{0009}-\x{000D}\x{0085}.\-]/u.
SEPARATORS: frozenset[str] = frozenset(
    "\u0009\u000a\u000b\u000c\u000d\u0020\u002d\u002e\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_REMOVE_SEPARATORS = dict.fromkeys(map(ord, SEPARATORS))


def remove_separators(text: str) -> str:
    return text.translate(_REMOVE_SEPARATORS)


def ascii_upper(text: str) -> str:
    # PHP strtoupper(): only ASCII letters since PHP 8.2.
    return text.translate(_ASCII_UPPER)


def php_trim(text: str) -> str:
    # PHP trim(): only " \t\n\r\0\x0B".
    return text.strip(" \t\n\r\0\x0b")
