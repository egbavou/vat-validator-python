"""Optional Pydantic v2 validation and string serialization."""

from typing import Annotated

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema
from pydantic_core import PydanticCustomError

from ._enums import FailureReason
from ._errors import InvalidIdentifierError
from ._vat_number import VatNumber

_MESSAGES = {
    FailureReason.INVALID_CHARACTERS: "VAT number contains characters that are not allowed",
    FailureReason.INVALID_LENGTH: "VAT number does not have a valid length for its country",
    FailureReason.INVALID_CHECKSUM: "VAT number has invalid check digits",
    FailureReason.INVALID_STRUCTURE: "VAT number does not have a valid structure for its country",
    FailureReason.UNKNOWN_COUNTRY_PREFIX: "VAT number starts with an unknown country prefix",
    FailureReason.MISSING_COUNTRY_PREFIX: "VAT number must start with a country prefix, such as FR or DE",
    FailureReason.COUNTRY_MISMATCH: "VAT number does not belong to the expected country",
}


def _validate(value: object) -> VatNumber:
    if isinstance(value, VatNumber):
        return value
    reason = FailureReason.INVALID_CHARACTERS
    if isinstance(value, str):
        try:
            return VatNumber(value)
        except InvalidIdentifierError as error:
            reason = error.reason
    raise PydanticCustomError(f"vat_number_{reason.value}", _MESSAGES[reason], {"reason": reason.value})


def _serialize(value: VatNumber) -> str:
    return value.value


PydanticVatNumber = Annotated[
    VatNumber,
    PlainValidator(_validate),
    PlainSerializer(_serialize, return_type=str),
    WithJsonSchema({"type": "string", "examples": ["FR27552032534"]}, mode="validation"),
    WithJsonSchema({"type": "string", "pattern": "^(?:[A-Z]{2}[0-9A-Z+*]{2,12}|CHE[0-9]{9})$"}, mode="serialization"),
]
