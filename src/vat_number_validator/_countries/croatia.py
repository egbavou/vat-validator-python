from typing import final

from .._checksum import iso7064_mod11_10
from ._base import CountryRule


# Croatian OIB law NN 60/08 art.3; Pravilnik NN 1/09 art.3(1), ISO 7064 MOD 11,10.
@final
class Croatia(CountryRule):
    PREFIX = "HR"
    LENGTHS = (11,)

    def checksum(self, national: str) -> bool:
        return iso7064_mod11_10(national)
