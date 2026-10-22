from typing import final

from ._base import CountryRule


# Research §3 CY: EC TIN transcode table (secondary for VAT); no unsourced first-digit or 12-prefix exclusion.
# The control letter is computed for the 6-series too: Cyprus Tax Department notice 04/05/2023,
# OECD TIN sheet 28/04/2023; verified on 24 real VIES-valid numbers on 2026-10-22 (design §9).
@final
class Cyprus(CountryRule):
    PREFIX = "CY"
    LENGTHS = (9,)
    CHARACTERS = r"[0-9]{0,8}[A-Z]?"

    def checksum(self, national: str) -> bool:
        table = [1, 0, 5, 7, 9, 13, 15, 17, 19, 21]
        total = 0
        for i in range(8):
            digit = int(national[i])
            total += table[digit] if i % 2 == 0 else digit
        return chr(65 + total % 26) == national[8]
