import re
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Brønnøysundregistrene organization-number modulus 11.
@final
class Norway(CountryRule):
    PREFIX = "NO"
    COUNTRY = "NO"
    VIES = False
    LENGTHS = (9,)

    def normalize(self, national: str) -> str:
        return re.sub(r"(?:MVA)\Z", "", national)

    def checksum(self, national: str) -> bool:
        check = 11 - weighted_sum(national, [3, 2, 7, 6, 5, 4, 3, 2]) % 11
        return check != 10 and check % 11 == int(national[8])
