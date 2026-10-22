from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Finlex decree 288/2001 §3; BMF p.6.
@final
class Finland(CountryRule):
    PREFIX = "FI"
    LENGTHS = (8,)

    def checksum(self, national: str) -> bool:
        check = 11 - weighted_sum(national, [7, 9, 10, 5, 8, 4, 2]) % 11
        return check != 10 and check % 11 == int(national[7])
