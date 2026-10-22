"""Immutable value object ported from PHP VatNumber.php."""

import re
from dataclasses import dataclass, field
from typing import Self, final

from ._checksum import luhn
from ._cleanup import ascii_upper, php_trim, remove_separators
from ._countries import detect_prefix, for_prefix, prefix_for_country
from ._enums import FailureReason
from ._errors import InvalidIdentifierError


@final
@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class VatNumber:
    value: str
    prefix: str = field(init=False)
    number: str = field(init=False)
    country_code: str = field(init=False)

    def __init__(self, value: str, *, country: str | None = None) -> None:
        if not isinstance(value, str):
            raise TypeError("value must be a str")
        if country is not None and not isinstance(country, str):
            raise TypeError("country must be a str or None")
        value = _clean(str.__str__(value))
        expected = None
        if country is not None:
            country = str.__str__(country)
            if php_trim(country) != "":
                expected = prefix_for_country(ascii_upper(php_trim(country)))
                if expected is None:
                    raise InvalidIdentifierError(FailureReason.UNKNOWN_COUNTRY_PREFIX)
        prefix, national = _split(value, expected)
        rule = for_prefix(prefix)
        if rule is None:
            raise InvalidIdentifierError(FailureReason.UNKNOWN_COUNTRY_PREFIX)
        national = rule.normalize(national)
        reason = rule.validate(national)
        if reason is not None:
            raise InvalidIdentifierError(reason)
        object.__setattr__(self, "value", prefix + national)
        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "number", national)
        object.__setattr__(self, "country_code", rule.country_code())

    @classmethod
    def is_valid(cls, value: str, *, country: str | None = None) -> bool:
        return cls.try_parse(value, country=country) is not None

    @classmethod
    def try_parse(cls, value: str, *, country: str | None = None) -> Self | None:
        try:
            return cls(value, country=country)
        except InvalidIdentifierError:
            return None

    @classmethod
    def from_siren(cls, siren: object) -> Self:
        if isinstance(siren, str):
            text = str.__str__(siren)
        elif (
            siren is None or isinstance(siren, (int, float, bytes, bytearray)) or type(siren).__str__ is object.__str__
        ):
            raise TypeError("siren must be a str or an object defining __str__")
        else:
            text = str(siren)
        digits = remove_separators(text)
        if re.fullmatch(r"[0-9]*", digits) is None:
            raise InvalidIdentifierError(FailureReason.INVALID_CHARACTERS)
        if len(digits) != 9:
            raise InvalidIdentifierError(FailureReason.INVALID_LENGTH)
        if digits.startswith("000") or not luhn(digits):
            raise InvalidIdentifierError(FailureReason.INVALID_CHECKSUM)
        key = (12 + 3 * (int(digits) % 97)) % 97
        return cls(f"FR{key:02d}{digits}")

    def format(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"VatNumber({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VatNumber):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


def _clean(value: str) -> str:
    value = ascii_upper(remove_separators(value))
    if value == "":
        raise InvalidIdentifierError(FailureReason.INVALID_LENGTH)
    if re.fullmatch(r"[0-9A-Z+*]+", value) is None:
        raise InvalidIdentifierError(FailureReason.INVALID_CHARACTERS)
    return value


def _split(value: str, expected: str | None) -> tuple[str, str]:
    detected = detect_prefix(value)
    if expected is None:
        if detected is None:
            reason = (
                FailureReason.UNKNOWN_COUNTRY_PREFIX
                if re.match(r"[A-Z]{2}", value)
                else FailureReason.MISSING_COUNTRY_PREFIX
            )
            raise InvalidIdentifierError(reason)
        prefix, length = detected
        return prefix, value[length:]
    if detected is not None and detected[0] == expected:
        national = value[detected[1] :]
        rule = for_prefix(expected)
        # PHP split(): a national alphanumeric key may resemble its own prefix.
        if (
            rule is not None
            and rule.validate(rule.normalize(national)) is not None
            and rule.validate(rule.normalize(value)) is None
        ):
            return expected, value
        return expected, national
    if detected is not None:
        rule = for_prefix(expected)
        # PHP split(): an apparent foreign prefix may be a national alphanumeric key.
        if rule is not None and rule.validate(rule.normalize(value)) is None:
            return expected, value
        raise InvalidIdentifierError(FailureReason.COUNTRY_MISMATCH)
    return expected, value
