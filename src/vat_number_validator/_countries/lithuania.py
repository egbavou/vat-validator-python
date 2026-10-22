from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.24, both nine- and twelve-digit families.
@final
class Lithuania(CountryRule):
    PREFIX = "LT"
    LENGTHS = (9, 12)

    def structure(self, national: str) -> bool:
        return national[-2:-1] == "1"

    def checksum(self, national: str) -> bool:
        length = len(national) - 1
        weights = []
        fallback = []
        for i in range(length):
            weights.append(i % 9 + 1)
            fallback.append((i + 2) % 9 + 1)
        check = weighted_sum(national, weights) % 11
        if check == 10:
            check = weighted_sum(national, fallback) % 11 % 10
        return check == int(national[-1:])
