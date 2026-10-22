from datetime import date
from typing import final

from .._checksum import weighted_sum
from ._base import CountryRule


# Research §3 CZ: law 133/2000 §13 for rodné číslo; secondary IČO formula.
# Design §9 decision of 2026-10-22: nine-digit VČP starting with 6 are format only;
# the administration has not published their construction. Allow IČO starting 9 and the old remainder-10 exception
# permissively.
@final
class Czechia(CountryRule):
    PREFIX = "CZ"
    LENGTHS = (8, 9, 10)

    def structure(self, national: str) -> bool:
        length = len(national)
        if length == 8 or (length == 9 and national[0] == "6"):
            return True
        year = int(national[:2])
        month = int(national[2:4])
        if month > 50:
            month -= 50
        if length == 10 and year >= 4 and year < 54 and month > 20:
            month -= 20
        full_year = 1900 + year if length == 9 or year >= 54 else 2000 + year
        # PHP Czechia::structure(): checkdate(month, day, year).
        try:
            date(full_year, month, int(national[4:6]))
        except ValueError:
            return False
        if length == 9:
            return year <= 53
        return True

    def checksum(self, national: str) -> bool:
        length = len(national)
        if length == 8:
            check = 11 - weighted_sum(national, [8, 7, 6, 5, 4, 3, 2]) % 11
            return (1 if check == 11 else (0 if check == 10 else check)) == int(national[7])
        if length == 9:
            return True
        return int(national) % 11 == 0 or (int(national[:9]) % 11 == 10 and national[9] == "0")
