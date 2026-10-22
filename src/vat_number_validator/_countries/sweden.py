from typing import final

from .._checksum import luhn
from ._base import CountryRule


# BMF p.19: suffix 01-94 takes precedence over Skatteverket 01-only; Luhn on the first ten digits.
@final
class Sweden(CountryRule):
    PREFIX = "SE"
    LENGTHS = (12,)

    def structure(self, national: str) -> bool:
        suffix = int(national[-2:])
        return suffix >= 1 and suffix <= 94

    def checksum(self, national: str) -> bool:
        return luhn(national[:10])
