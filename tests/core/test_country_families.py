import pytest

from tests.cases import FAMILIES, ROUND_TRIPS, SE_SUFFIXES, UK_CHECKSUM, UK_STRUCTURE, UK_VALID
from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber


@pytest.mark.parametrize(("valid", "invalid", "reason"), FAMILIES.values(), ids=FAMILIES)
def test_checksum_families(valid: str, invalid: str, reason: FailureReason) -> None:
    assert VatNumber(valid).value == valid
    assert not VatNumber.is_valid(invalid)
    with pytest.raises(InvalidIdentifierError) as caught:
        VatNumber(invalid)
    assert caught.value.reason is reason


@pytest.mark.parametrize(("suffix", "reason"), SE_SUFFIXES)
def test_swedish_suffixes(suffix: str, reason: FailureReason | None) -> None:
    value = "SE5560125790" + suffix
    if reason is None:
        assert VatNumber(value).value == value
    else:
        with pytest.raises(InvalidIdentifierError) as caught:
            VatNumber(value)
        assert caught.value.reason is reason


@pytest.mark.parametrize("prefix", ["GB", "XI"])
def test_british_families(prefix: str) -> None:
    for national in UK_VALID:
        assert VatNumber.is_valid(prefix + national), national
    for nationals, reason in [
        (UK_CHECKSUM, FailureReason.INVALID_CHECKSUM),
        (UK_STRUCTURE, FailureReason.INVALID_STRUCTURE),
    ]:
        for national in nationals:
            with pytest.raises(InvalidIdentifierError) as caught:
                VatNumber(prefix + national)
            assert caught.value.reason is reason, national


def test_greek_aliases() -> None:
    vat = VatNumber("GR094014201")
    assert (vat.value, vat.prefix, vat.number, vat.country_code) == ("EL094014201", "EL", "094014201", "GR")
    assert VatNumber("094014201", country="GR") == vat
    assert VatNumber("GR094014201", country="EL") == vat


def test_northern_ireland_metadata() -> None:
    vat = VatNumber("XI220430231")
    assert (vat.prefix, vat.country_code) == ("XI", "GB")


@pytest.mark.parametrize("full", ROUND_TRIPS)
def test_alphanumeric_round_trips(full: str) -> None:
    vat = VatNumber(full)
    assert VatNumber(vat.number, country=vat.country_code) == vat
    assert VatNumber(full, country=vat.country_code) == vat
