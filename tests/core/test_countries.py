import pytest

from tests.cases import INVALID_NUMBERS, VALID_NUMBERS
from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber
from vat_number_validator._countries import for_prefix, prefixes


@pytest.mark.parametrize(("value", "normalized"), VALID_NUMBERS.values(), ids=VALID_NUMBERS)
def test_valid_vectors(value: str, normalized: str) -> None:
    assert VatNumber.is_valid(value)
    assert VatNumber(value).value == normalized


@pytest.mark.parametrize(("value", "reason"), INVALID_NUMBERS.values(), ids=INVALID_NUMBERS)
def test_invalid_vectors(value: str, reason: FailureReason) -> None:
    assert not VatNumber.is_valid(value)
    assert VatNumber.try_parse(value) is None
    with pytest.raises(InvalidIdentifierError) as caught:
        VatNumber(value)
    assert caught.value.reason is reason


def test_registry_order_and_coverage() -> None:
    assert prefixes() == [
        "AT",
        "BE",
        "BG",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "EL",
        "ES",
        "FI",
        "FR",
        "HR",
        "HU",
        "IE",
        "IT",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
        "XI",
        "GB",
        "CHE",
        "NO",
    ]
    for prefix in prefixes():
        assert sum(normalized.startswith(prefix) for _, normalized in VALID_NUMBERS.values()) >= 2, prefix
        assert sum(value.startswith(prefix) for value, _ in INVALID_NUMBERS.values()) >= 2, prefix
        rule = for_prefix(prefix)
        assert rule is not None
        assert rule.prefix() == prefix
        assert rule.covered_by_vies() == (prefix not in {"GB", "CHE", "NO"})
