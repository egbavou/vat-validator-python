from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 RO: BMF forbids leading zeros since 5/12/2007; secondary weighted checksum.
@final
class Romania(CountryRule):
    PREFIX = "RO"
    LENGTHS = (2, 3, 4, 5, 6, 7, 8, 9, 10)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        # PHP Romania::checksum(): str_pad(..., 9, '0', STR_PAD_LEFT).
        body = national[:-1].rjust(9, "0")
        check = 10 * weighted_sum(body, [7, 5, 3, 2, 1, 7, 5, 3, 2]) % 11
        return (0 if check == 10 else check) == int(national[-1:])
