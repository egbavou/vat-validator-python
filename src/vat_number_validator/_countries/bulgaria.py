from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 BG: secondary BULSTAT checksum for nine-digit company numbers.
# Design §9 decision of 2026-10-22: ten-digit natural-person numbers are format only,
# including NAP service numbers introduced in 2024 whose construction is unpublished.
@final
class Bulgaria(CountryRule):
    PREFIX = "BG"
    LENGTHS = (9, 10)

    def checksum(self, national: str) -> bool:
        last = int(national[-1:])
        if len(national) == 9:
            check = weighted_sum(national, [1, 2, 3, 4, 5, 6, 7, 8]) % 11
            if check == 10:
                check = weighted_sum(national, [3, 4, 5, 6, 7, 8, 9, 10]) % 11 % 10
            return last == check
        return True
