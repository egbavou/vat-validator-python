import pickle
from enum import StrEnum

import pytest

from vat_number_validator import CheckStatus, FailureReason, InvalidIdentifierError, UnavailableReason, ViesError


def test_enum_values_and_order() -> None:
    for enum, values in [
        (
            FailureReason,
            [
                "invalid_characters",
                "invalid_length",
                "invalid_checksum",
                "invalid_structure",
                "unknown_country_prefix",
                "missing_country_prefix",
                "country_mismatch",
            ],
        ),
        (CheckStatus, ["found", "not_found", "invalid_format", "unavailable"]),
        (UnavailableReason, ["no_source", "registry_error", "transport", "http_status", "invalid_json", "schema"]),
    ]:
        assert issubclass(enum, StrEnum)
        assert [member.value for member in enum] == values
        assert [member.name for member in enum] == [value.upper() for value in values]


def test_identifier_error() -> None:
    error = InvalidIdentifierError(FailureReason.INVALID_STRUCTURE)
    assert isinstance(error, ValueError)
    assert error.reason is FailureReason.INVALID_STRUCTURE
    assert str(error) == "Invalid VAT number: invalid_structure."
    with pytest.raises(AttributeError):
        error.reason = FailureReason.INVALID_LENGTH  # type: ignore[misc]
    restored = pickle.loads(pickle.dumps(error))
    assert type(restored) is InvalidIdentifierError
    assert restored.reason is error.reason
    assert str(restored) == str(error)


def test_vies_error() -> None:
    error = ViesError("VIES returned HTTP 503.")
    assert isinstance(error, RuntimeError)
    restored = pickle.loads(pickle.dumps(error))
    assert type(restored) is ViesError
    assert str(restored) == str(error)
