import re
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF pp.10-11: old and new formats, C9 restricted to A-I.
@final
class Ireland(CountryRule):
    PREFIX = "IE"
    LENGTHS = (8, 9)

    def characters(self, national: str) -> bool:
        if len(national) not in (8, 9):
            return re.fullmatch(r"[0-9A-Z+*]*", national) is not None
        return re.fullmatch(r"(?:[0-9]{7}[A-W][A-I]?|[0-9][A-Z+*][0-9]{5}[A-W])", national) is not None

    def checksum(self, national: str) -> bool:
        old = not ("0" <= national[1] <= "9")
        digits = "0" + national[2:7] + national[0] if old else national[:7]
        total = weighted_sum(digits, [8, 7, 6, 5, 4, 3, 2])
        if len(national) == 9:
            total += 9 * (ord(national[8]) - 64)
        return "WABCDEFGHIJKLMNOPQRSTUV"[total % 23] == national[7]
