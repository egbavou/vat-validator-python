from typing import final

from ._base import CountryRule


# BMF p.29: permitted third digits and divisibility by 11.
@final
class Slovakia(CountryRule):
    PREFIX = "SK"
    LENGTHS = (10,)

    def structure(self, national: str) -> bool:
        return national[0] != "0" and national[2] in "234789"

    def checksum(self, national: str) -> bool:
        return int(national) % 11 == 0
