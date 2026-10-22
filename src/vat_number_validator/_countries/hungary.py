from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.23; Céginformációs Szolgálat 2018.
@final
class Hungary(CountryRule):
    PREFIX = "HU"
    LENGTHS = (8,)

    def checksum(self, national: str) -> bool:
        return (10 - weighted_sum(national, [9, 7, 3, 1, 9, 7, 3]) % 10) % 10 == int(national[7])
