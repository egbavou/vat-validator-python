from typing import final

from .._checksum import digit_sum
from ._base import CountryRule


# BMF p.1 (modified Luhn).
@final
class Austria(CountryRule):
    PREFIX = "AT"
    LENGTHS = (9,)
    CHARACTERS = r"U[0-9]*"

    def checksum(self, national: str) -> bool:
        total = 4
        for i in range(1, 8):
            digit = int(national[i])
            total += digit_sum(str(2 * digit)) if i % 2 == 0 else digit
        return (10 - total % 10) % 10 == int(national[8])
