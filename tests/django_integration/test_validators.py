from importlib import import_module

import httpx
import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import translation

from tests.django_integration.support import MESSAGES, REASONS
from tests.httpx_integration.support import QueueTransport, fixture
from vat_number_validator import VatNumber, VatNumberChecker
from vat_number_validator.django.validators import VatNumberExistsValidator, VatNumberValidator


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("validator_type", [VatNumberValidator, VatNumberExistsValidator])
@pytest.mark.parametrize(("value", "country", "reason"), REASONS)
def test_every_reason(
    language: str,
    validator_type: type[VatNumberValidator] | type[VatNumberExistsValidator],
    value: str,
    country: str | None,
    reason: str,
) -> None:
    with override_settings(VAT_NUMBER_VALIDATOR={"CHECKER": object()}), translation.override(language):
        with pytest.raises(ValidationError) as caught:
            validator_type(country=country)(value)
        assert caught.value.code == reason
        assert caught.value.messages == [MESSAGES[language][reason]]


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("validator_type", [VatNumberValidator, VatNumberExistsValidator])
@pytest.mark.parametrize("value", [123, True, None, [], object()])
def test_non_string(
    language: str, validator_type: type[VatNumberValidator] | type[VatNumberExistsValidator], value: object
) -> None:
    with translation.override(language), pytest.raises(ValidationError) as caught:
        validator_type()(value)
    assert caught.value.code == "invalid_characters"
    with translation.override(language):
        assert caught.value.messages == [MESSAGES[language]["invalid_characters"]]


@pytest.mark.parametrize(
    ("value", "country"), [("27552032534", "FR"), ("FR27552032534", None), ("FR27552032534", "FR")]
)
def test_format_does_not_resolve_checker(value: str, country: str | None) -> None:
    with override_settings(VAT_NUMBER_VALIDATOR={"CHECKER": object()}):
        VatNumberValidator(country)(value)
        VatNumberValidator(country)(VatNumber("FR27552032534"))


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    ("value", "filename", "reason"),
    [
        ("FR27552032534", "post-valid-fr.json", None),
        ("FR44732829320", "post-invalid-fr.json", "not_found"),
        ("FR27552032534", "post-error-ms-max-concurrent-req-fr.json", "unavailable"),
    ],
)
def test_existence(language: str, strict: bool, value: str, filename: str, reason: str | None) -> None:
    transport = QueueTransport()
    transport.responses.append(httpx.Response(200, content=fixture(filename)))
    with httpx.Client(transport=transport) as client:
        checker = VatNumberChecker(client)
        with override_settings(VAT_NUMBER_VALIDATOR={"CHECKER": checker}), translation.override(language):
            validator = VatNumberExistsValidator(fail_when_unavailable=strict)
            if reason is not None and (reason != "unavailable" or strict):
                with pytest.raises(ValidationError) as caught:
                    validator(value)
                assert caught.value.code == reason
                assert caught.value.messages == [MESSAGES[language][reason]]
            else:
                validator(VatNumber(value))
        assert not client.is_closed
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    "validator",
    [VatNumberValidator(), VatNumberValidator("FR"), VatNumberExistsValidator(), VatNumberExistsValidator("FR", True)],
)
def test_deconstruction_and_equality(validator: VatNumberValidator | VatNumberExistsValidator) -> None:
    path, args, kwargs = validator.deconstruct()
    module, name = path.rsplit(".", 1)
    clone = getattr(import_module(module), name)(*args, **kwargs)
    assert clone == validator
    assert validator != object()
    assert validator != VatNumberValidator("BE")
    assert validator != VatNumberExistsValidator("BE", True)
    assert VatNumberValidator() != VatNumberExistsValidator()
    assert VatNumberExistsValidator() != VatNumberExistsValidator(fail_when_unavailable=True)
