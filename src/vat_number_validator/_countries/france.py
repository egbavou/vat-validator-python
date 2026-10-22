import re
from typing import final

from .._checksum import luhn
from ._base import CountryRule


# Research §3 FR: INSEE SIREN Luhn; secondary key formulas and permissive Monaco exception.
@final
class France(CountryRule):
    PREFIX = "FR"
    LENGTHS = (11,)

    def characters(self, national: str) -> bool:
        return re.fullmatch(r"[0-9A-HJ-NP-Z]{0,2}[0-9]*", national) is not None

    def checksum(self, national: str) -> bool:
        siren = national[2:]
        if not siren.startswith("000") and not luhn(siren):
            return False
        key = national[:2]
        if re.fullmatch(r"[0-9]+", key):
            return int(key) == (12 + 3 * (int(siren) % 97)) % 97
        alphabet = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        first = alphabet.index(key[0])
        second = alphabet.index(key[1])
        total = first * 24 + second - 10 if "0" <= key[0] <= "9" else first * 34 + second - 100
        # PHP France::checksum(): intdiv truncates toward zero (the sum can be negative).
        quotient = total // 11 if total >= 0 else -(-total // 11)
        return (int(siren) + 1 + quotient) % 11 == total % 11
