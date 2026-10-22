from typing import final

from ._base import CountryRule


# BMF p.13, modulo 89.
@final
class Luxembourg(CountryRule):
    PREFIX = "LU"
    LENGTHS = (8,)

    def checksum(self, national: str) -> bool:
        return int(national[:6]) % 89 == int(national[-2:])
