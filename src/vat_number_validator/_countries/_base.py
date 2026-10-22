"""PHP CountryRule and AbstractCountryRule: ordered national validation."""

import re
from abc import ABC, abstractmethod
from typing import ClassVar

from .._enums import FailureReason


class CountryRule(ABC):
    PREFIX: ClassVar[str] = ""
    COUNTRY: ClassVar[str] = ""
    VIES: ClassVar[bool] = True
    CHARACTERS: ClassVar[str] = r"[0-9]*"
    LENGTHS: ClassVar[tuple[int, ...]] = ()

    def prefix(self) -> str:
        return self.PREFIX

    def country_code(self) -> str:
        return self.COUNTRY if self.COUNTRY != "" else self.PREFIX

    def covered_by_vies(self) -> bool:
        return self.VIES

    def normalize(self, national: str) -> str:
        return national

    def validate(self, national: str) -> FailureReason | None:
        if not self.characters(national):
            return FailureReason.INVALID_CHARACTERS
        if len(national) not in self.LENGTHS:
            return FailureReason.INVALID_LENGTH
        if not self.structure(national):
            return FailureReason.INVALID_STRUCTURE
        return None if self.checksum(national) else FailureReason.INVALID_CHECKSUM

    def characters(self, national: str) -> bool:
        return re.fullmatch(self.CHARACTERS, national) is not None

    def structure(self, national: str) -> bool:
        return True

    @abstractmethod
    def checksum(self, national: str) -> bool:
        pass
