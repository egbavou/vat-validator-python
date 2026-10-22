from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.27, weighted modulus 11.
@final
class Poland(CountryRule):
    PREFIX = "PL"
    LENGTHS = (10,)

    def checksum(self, national: str) -> bool:
        return weighted_sum(national, [6, 5, 7, 2, 3, 4, 5, 6, 7]) % 11 == int(national[9])
