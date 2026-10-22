from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.22: initial 10 is mandatory even when a different prefix passes the checksum.
@final
class Estonia(CountryRule):
    PREFIX = "EE"
    LENGTHS = (9,)

    def structure(self, national: str) -> bool:
        return national.startswith("10")

    def checksum(self, national: str) -> bool:
        return (10 - weighted_sum(national, [3, 7, 1, 3, 7, 1, 3, 7]) % 10) % 10 == int(national[8])
