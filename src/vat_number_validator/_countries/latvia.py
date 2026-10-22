import re
from datetime import date
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 LV: secondary corporate modulus 11; old personal keys lack independent confirmation.
# Fizisko personu reģistra likums art. 6(2), in force 28/06/2021: 3 + random digit 2-9 + nine random digits, without
# a checksum.
@final
class Latvia(CountryRule):
    PREFIX = "LV"
    LENGTHS = (11,)

    def structure(self, national: str) -> bool:
        if int(national[0]) > 3 or re.match(r"3[2-9]", national) is not None:
            return True
        century = int(national[6])
        if century > 2:
            return False
        # PHP Latvia::structure(): checkdate(month, day, year).
        try:
            date(1800 + century * 100 + int(national[4:6]), int(national[2:4]), int(national[:2]))
        except ValueError:
            return False
        return True

    def checksum(self, national: str) -> bool:
        return int(national[0]) <= 3 or weighted_sum(national, [9, 1, 4, 8, 3, 10, 2, 5, 7, 6, 1]) % 11 == 3
