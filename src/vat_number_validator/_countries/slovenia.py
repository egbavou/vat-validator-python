from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF p.28; FURS modulus 11.
@final
class Slovenia(CountryRule):
    PREFIX = "SI"
    LENGTHS = (8,)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        check = 11 - weighted_sum(national, [8, 7, 6, 5, 4, 3, 2]) % 11
        return check != 11 and (0 if check == 10 else check) == int(national[7])
