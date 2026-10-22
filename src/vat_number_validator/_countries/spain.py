import re
from typing import final

from .._checksum import digit_sum
from ._base import CountryRule


# Research §3 ES: BOE entity structure; EC TIN DNI; secondary CIF algorithm. Permissively accept a digit or letter
# CIF check for every entity (stdnum; Task 5).
@final
class Spain(CountryRule):
    PREFIX = "ES"
    LENGTHS = (9,)

    def characters(self, national: str) -> bool:
        if re.fullmatch(r"[0-9A-Z]*", national) is None:
            return False
        if len(national) != 9:
            return True
        return (
            re.fullmatch(r"(?:[0-9]{8}[A-Z]|[XYZKLM][0-9]{7}[A-Z]|[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-Z])", national)
            is not None
        )

    def checksum(self, national: str) -> bool:
        first = national[0]
        body = national[1:8]
        if "0" <= first <= "9" or first in "XYZKLM":
            digits = (
                national[:8] if "0" <= first <= "9" else (str("XYZ".index(first)) + body if first in "XYZ" else body)
            )
            return "TRWAGMYFPDXBNJZSQVHLCKE"[int(digits) % 23] == national[8]
        total = 0
        for i in range(7):
            digit = int(body[i])
            total += digit_sum(str(2 * digit)) if i % 2 == 0 else digit
        check = (10 - total % 10) % 10
        return national[8] == str(check) or national[8] == "JABCDEFGHI"[check]
