from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 MT: secondary sources disagree; accept the wider stdnum congruence mod 37, including 00 and +37/+74
# controls (Task 6). No unsourced body >100000 restriction.
@final
class Malta(CountryRule):
    PREFIX = "MT"
    LENGTHS = (8,)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        return weighted_sum(national, [3, 4, 6, 7, 8, 9, 10, 1]) % 37 == 0
