from typing import final

from .._checksum import iso7064_mod11_10
from ._base import CountryRule


# BMF p.3, ISO 7064 MOD 11,10.
@final
class Germany(CountryRule):
    PREFIX = "DE"
    LENGTHS = (9,)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        return iso7064_mod11_10(national)
