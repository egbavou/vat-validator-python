import re
from typing import final

from .._checksum import iso7064_mod97_10, weighted_sum
from ._base import CountryRule


# BMF pp.14-17: mod 11 first (remainder 10 rejected), then ISO 7064 MOD 97-10; full alphanumeric/symbol alphabet for
# the latter.
@final
class Netherlands(CountryRule):
    PREFIX = "NL"
    LENGTHS = (12,)
    CHARACTERS = r"[0-9A-Z+*]*"

    def structure(self, national: str) -> bool:
        return re.fullmatch(r"[0-9]+", national[-2:]) is not None and int(national[-2:]) > 0

    def checksum(self, national: str) -> bool:
        if re.fullmatch(r"[0-9]{9}B[0-9]{2}", national) is not None:
            check = weighted_sum(national, [9, 8, 7, 6, 5, 4, 3, 2]) % 11
            if check != 10 and check == int(national[8]):
                return True
        suffix = int(national[-2:])
        return suffix >= 2 and suffix <= 98 and iso7064_mod97_10("NL" + national)
