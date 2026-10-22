from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 EL: dragonbe, stdnum and braemoor agree on the key; no eight-digit padding per design §9.
@final
class Greece(CountryRule):
    PREFIX = "EL"
    LENGTHS = (9,)
    COUNTRY = "GR"

    def checksum(self, national: str) -> bool:
        return weighted_sum(national, [256, 128, 64, 32, 16, 8, 4, 2]) % 11 % 10 == int(national[8])
