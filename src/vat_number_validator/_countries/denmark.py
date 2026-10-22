from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.4; Erhvervsstyrelsen modulus 11.
@final
class Denmark(CountryRule):
    PREFIX = "DK"
    LENGTHS = (8,)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        return weighted_sum(national, [2, 7, 6, 5, 4, 3, 2, 1]) % 11 == 0
