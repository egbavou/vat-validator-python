import json
import subprocess
import sys

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core import PydanticCustomError

from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber
from vat_number_validator.pydantic import PydanticVatNumber, _validate


class Company(BaseModel):
    vat_number: PydanticVatNumber


@pytest.mark.parametrize("strict", [False, True])
def test_validation_and_serialization(strict: bool) -> None:
    company = Company.model_validate({"vat_number": "fr 27 552 032 534"}, strict=strict)
    assert company.vat_number == VatNumber("FR27552032534")
    assert company.model_dump() == {"vat_number": "FR27552032534"}
    assert json.loads(company.model_dump_json()) == company.model_dump()
    number = VatNumber("FR27552032534")
    assert TypeAdapter(PydanticVatNumber).validate_python(number, strict=strict) is number


@pytest.mark.parametrize("value", [123, True, b"FR27552032534", None, [], object()])
def test_non_strings(value: object) -> None:
    with pytest.raises(ValidationError) as caught:
        TypeAdapter(PydanticVatNumber).validate_python(value)
    error = caught.value.errors()[0]
    assert error["type"] == "vat_number_invalid_characters"
    assert error["ctx"] == {"reason": "invalid_characters"}


@pytest.mark.parametrize("reason", list(FailureReason))
def test_every_error(reason: FailureReason, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(self: VatNumber, value: str) -> None:
        raise InvalidIdentifierError(reason)

    monkeypatch.setattr(VatNumber, "__init__", reject)
    with pytest.raises(PydanticCustomError) as caught:
        _validate("bad")
    error = caught.value
    assert error.type == f"vat_number_{reason.value}"
    assert error.context == {"reason": reason.value}
    assert not str(error).endswith(".")


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("FRIO334175221", "invalid_characters"),
        ("FR123", "invalid_length"),
        ("FR28552032534", "invalid_checksum"),
        ("BE2123456791", "invalid_structure"),
        ("ZZ27552032534", "unknown_country_prefix"),
        ("27552032534", "missing_country_prefix"),
    ],
)
def test_core_errors(value: str, reason: str) -> None:
    with pytest.raises(ValidationError) as caught:
        Company(vat_number=value)  # type: ignore[arg-type]
    assert caught.value.errors()[0]["type"] == f"vat_number_{reason}"


def test_optional_and_schemas() -> None:
    adapter = TypeAdapter(PydanticVatNumber | None)
    assert adapter.validate_python(None) is None
    assert adapter.dump_python(None) is None
    assert adapter.dump_json(None) == b"null"
    number = adapter.validate_json('"fr27552032534"')
    assert adapter.dump_python(number) == "FR27552032534"
    assert adapter.dump_json(number) == b'"FR27552032534"'
    for mode in ("validation", "serialization"):
        schema = adapter.json_schema(mode=mode)
        assert {"type": "null"} in schema["anyOf"]
        string = next(item for item in schema["anyOf"] if item["type"] == "string")
        if mode == "validation":
            assert "pattern" not in string
            assert string["examples"]
        else:
            assert string["pattern"] == "^(?:[A-Z]{2}[0-9A-Z+*]{2,12}|CHE[0-9]{9})$"


def test_import_does_not_load_httpx() -> None:
    subprocess.run(
        [sys.executable, "-c", "import sys; import vat_number_validator.pydantic; assert 'httpx' not in sys.modules"],
        check=True,
    )
