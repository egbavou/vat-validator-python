import re
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# BMF pp.8-9,32-33: MOD97/MOD9755 ranges, branches and GD/HA.
class AbstractUnitedKingdom(CountryRule):
    COUNTRY = "GB"
    LENGTHS = (5, 9, 12)

    def characters(self, national: str) -> bool:
        return re.fullmatch(r"(?:[0-9]*|(?:GD|HA)[0-9]*)", national) is not None

    def structure(self, national: str) -> bool:
        if re.fullmatch(r"[0-9]+", national) is None:
            if len(national) != 5:
                return False
            number = int(national[2:])
            return number <= 499 if national.startswith("GD") else number >= 500
        if len(national) == 5 or int(national[:9]) == 0:
            return False
        if len(national) == 12 and national[-3:] == "000":
            return False
        body = int(national[:7])
        total = weighted_sum(national, [8, 7, 6, 5, 4, 3, 2]) + int(national[7:9])
        if total % 97 == 0:
            return not ((body >= 100000 and body <= 999999) or (body >= 9490001 and body <= 9700000) or body >= 9990001)
        return (total + 55) % 97 != 0 or body > 1000000

    def checksum(self, national: str) -> bool:
        if re.fullmatch(r"[0-9]+", national) is None:
            return True
        body = int(national[:7])
        total = weighted_sum(national, [8, 7, 6, 5, 4, 3, 2]) + int(national[7:9])
        mod97_range = not (
            (body >= 100000 and body <= 999999) or (body >= 9490001 and body <= 9700000) or body >= 9990001
        )
        return (total % 97 == 0 and mod97_range) or ((total + 55) % 97 == 0 and body > 1000000)


# BMF pp.8-9,32-33; shared UK rules.
@final
class UnitedKingdom(AbstractUnitedKingdom):
    PREFIX = "GB"
    VIES = False


# BMF pp.8-9,32-33; shared UK rules.
@final
class NorthernIreland(AbstractUnitedKingdom):
    PREFIX = "XI"
