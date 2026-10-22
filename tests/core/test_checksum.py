import pytest

from vat_number_validator._checksum import digit_sum, iso7064_mod11_10, iso7064_mod97_10, luhn, weighted_sum


@pytest.mark.parametrize(("digits", "valid"), [("79927398713", True), ("79927398710", False), ("552032534", True)])
def test_luhn(digits: str, valid: bool) -> None:
    assert luhn(digits) is valid


@pytest.mark.parametrize(("digits", "valid"), [("129274202", True), ("129274203", False), ("111111125", True)])
def test_mod11_10(digits: str, valid: bool) -> None:
    assert iso7064_mod11_10(digits) is valid


@pytest.mark.parametrize(
    ("value", "valid"),
    [("NL123456789B13", True), ("NL123456789B14", False), ("NL001000000B24", True), ("NL+*0000000B43", True)],
)
def test_mod97_10(value: str, valid: bool) -> None:
    assert iso7064_mod97_10(value) is valid


@pytest.mark.parametrize(("digits", "weights", "total"), [("123", [3, 2, 1], 10), ("9876", [1, 2, 3], 46)])
def test_weighted_sum(digits: str, weights: list[int], total: int) -> None:
    assert weighted_sum(digits, weights) == total


@pytest.mark.parametrize(("digits", "total"), [("1234567890", 45), ("18", 9), ("", 0)])
def test_digit_sum(digits: str, total: int) -> None:
    assert digit_sum(digits) == total
