from typing import final

from .._checksum import luhn
from ._base import CountryRule


# DM 23 December 1976 arts.8-9; BMF p.12 office codes.
@final
class Italy(CountryRule):
    PREFIX = "IT"
    LENGTHS = (11,)

    def structure(self, national: str) -> bool:
        office = int(national[7:10])
        return national[:7] != "0000000" and ((office >= 1 and office <= 100) or office in (120, 121, 888, 999))

    def checksum(self, national: str) -> bool:
        return luhn(national)
