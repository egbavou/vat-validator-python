import re
from typing import final

from ._base import CountryRule


# BMF p.2; VIES FAQ note 3 permits padding legacy nine-digit inputs.
@final
class Belgium(CountryRule):
    PREFIX = "BE"
    LENGTHS = (10,)

    def normalize(self, national: str) -> str:
        return "0" + national if len(national) == 9 and re.fullmatch(r"[0-9]+", national) else national

    def structure(self, national: str) -> bool:
        return national[0] == "0" or national[0] == "1"

    def checksum(self, national: str) -> bool:
        return int(national[-2:]) == 97 - int(national[:8]) % 97
