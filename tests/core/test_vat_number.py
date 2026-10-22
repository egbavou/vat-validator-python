import copy
import pickle
from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from tests.cases import PARSING, SIREN_CASES
from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber
from vat_number_validator._cleanup import SEPARATORS
from vat_number_validator._countries import detect_prefix, for_prefix, prefix_for_country, prefixes


@pytest.mark.parametrize(("value", "country", "expected"), PARSING.values(), ids=PARSING)
def test_parsing(value: str, country: str | None, expected: str | FailureReason) -> None:
    if isinstance(expected, FailureReason):
        with pytest.raises(InvalidIdentifierError) as caught:
            VatNumber(value, country=country)
        assert caught.value.reason is expected
        assert str(caught.value) == f"Invalid VAT number: {expected.value}."
    else:
        vat = VatNumber(value, country=country)
        assert vat.value == expected
        assert vat.format() == expected
        assert str(vat) == expected


def test_swiss_metadata_and_registry() -> None:
    vat = VatNumber("CHE116281710")
    assert (vat.prefix, vat.number, vat.country_code) == ("CHE", "116281710", "CH")
    assert {"BE", "FR", "CHE", "NO"} <= set(prefixes())
    assert for_prefix("FR") is for_prefix("FR")
    assert for_prefix("ZZ") is None
    assert prefix_for_country("CH") == "CHE"
    assert prefix_for_country("ZZ") is None
    assert detect_prefix("CHE116281710") == ("CHE", 3)
    assert detect_prefix("ZZ123") is None


@pytest.mark.parametrize(("value", "expected"), SIREN_CASES)
def test_from_siren(value: object, expected: str | FailureReason) -> None:
    if isinstance(expected, FailureReason):
        with pytest.raises(InvalidIdentifierError) as caught:
            VatNumber.from_siren(value)
        assert caught.value.reason is expected
    else:
        assert VatNumber.from_siren(value).value == expected


@pytest.mark.parametrize("value", [123, 1.5, True, None, b"552032534", bytearray(b"552032534"), object()])
def test_from_siren_types(value: object) -> None:
    with pytest.raises(TypeError):
        VatNumber.from_siren(value)


@pytest.mark.parametrize("entry", [VatNumber, VatNumber.try_parse, VatNumber.is_valid])
@pytest.mark.parametrize("value", [123, b"FR27552032534", None, []])
def test_input_types(entry: Any, value: Any) -> None:
    with pytest.raises(TypeError):
        entry(value)


@pytest.mark.parametrize("entry", [VatNumber, VatNumber.try_parse, VatNumber.is_valid])
@pytest.mark.parametrize("country", [123, b"FR", [], True])
def test_country_types(entry: Any, country: Any) -> None:
    with pytest.raises(TypeError):
        entry("FR27552032534", country=country)


class HostileString(str):
    def __str__(self) -> str:
        return "incorrect"

    def upper(self) -> str:
        return "incorrect"

    def translate(self, table: Any) -> str:
        return "incorrect"


def test_string_subclasses() -> None:
    vat = VatNumber(HostileString("fr 27 552 032 534"), country=HostileString("fr"))
    assert vat.value == "FR27552032534"
    assert all(type(v) is str for v in (vat.value, vat.prefix, vat.number, vat.country_code))
    assert VatNumber.from_siren(HostileString("552032534")) == vat


def test_value_object() -> None:
    vat = VatNumber("FR27552032534")
    with pytest.raises(FrozenInstanceError):
        vat.value = "FR123"  # type: ignore[misc]
    assert not hasattr(vat, "__dict__")
    assert replace(vat, value="BE403170701") == VatNumber("BE0403170701")
    assert replace(vat, value="BE403170701").country_code == "BE"
    with pytest.raises(InvalidIdentifierError):
        replace(vat, value="FR123")
    assert vat == VatNumber("fr 27 552 032 534")
    assert vat != VatNumber("BE0403170701")
    assert vat != "FR27552032534"
    assert len({vat, VatNumber(vat.value)}) == 1
    assert repr(vat) == "VatNumber('FR27552032534')"
    for restored in [pickle.loads(pickle.dumps(vat)), copy.copy(vat), copy.deepcopy(vat)]:
        assert restored == vat
        assert (restored.prefix, restored.number, restored.country_code) == ("FR", "27552032534", "FR")


@pytest.mark.parametrize("value", ["FR27552032534ß", "\u0131T00905811006", "\u017fE556012579001", "ﬀ123"])
def test_non_ascii_upper(value: str) -> None:
    with pytest.raises(InvalidIdentifierError) as caught:
        VatNumber(value)
    assert caught.value.reason is FailureReason.INVALID_CHARACTERS


def test_country_trim_and_tolerant_methods() -> None:
    assert VatNumber("27552032534", country=" fr ").value == "FR27552032534"
    with pytest.raises(InvalidIdentifierError) as caught:
        VatNumber("27552032534", country="\xa0FR")
    assert caught.value.reason is FailureReason.UNKNOWN_COUNTRY_PREFIX
    assert VatNumber("FR27552032534", country=" ").value == "FR27552032534"
    assert VatNumber.try_parse("FR123") is None
    assert not VatNumber.is_valid("FR123")
    assert VatNumber.try_parse("fr27552032534") == VatNumber("FR27552032534")


def test_french_own_prefix_round_trip() -> None:
    vat = VatNumber("FRFR552032799")
    assert VatNumber(vat.number, country=vat.country_code) == vat
    assert VatNumber(vat.value, country=vat.country_code) == vat


def test_every_unicode_code_point_as_separator() -> None:
    for cp in range(0x110000):
        character = chr(cp)
        assert VatNumber.is_valid("FR27" + character + "552032534") == (character in SEPARATORS), hex(cp)
