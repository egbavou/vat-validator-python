import re
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# eCH-0108 v6.0.0 §3.1.1: ^CHE[1-9][0-9]{8}$; ESTV suffixes.
# Checksum weights from eCH-0097 v5.2.0 §2.4, abrogated 20/03/2024.
@final
class Switzerland(CountryRule):
    PREFIX = "CHE"
    COUNTRY = "CH"
    VIES = False
    LENGTHS = (9,)

    def normalize(self, national: str) -> str:
        return re.sub(r"(?:MWST|TVA|IVA)\Z", "", national)

    def structure(self, national: str) -> bool:
        return national[0] != "0"

    def checksum(self, national: str) -> bool:
        check = 11 - weighted_sum(national, [5, 4, 3, 2, 7, 6, 5, 4]) % 11
        return check != 10 and check % 11 == int(national[8])
