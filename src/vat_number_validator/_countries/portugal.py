from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.18; DL 14/2013 art.4.
@final
class Portugal(CountryRule):
    PREFIX = "PT"
    LENGTHS = (9,)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        check = 11 - weighted_sum(national, [9, 8, 7, 6, 5, 4, 3, 2]) % 11
        return (0 if check >= 10 else check) == int(national[8])
