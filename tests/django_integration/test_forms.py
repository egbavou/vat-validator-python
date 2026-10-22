import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from tests.django_integration.support import MESSAGES, REASONS
from vat_number_validator import VatNumber
from vat_number_validator.django.forms import VatNumberField


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize(("value", "country", "reason"), REASONS)
def test_reasons(language: str, value: str, country: str | None, reason: str) -> None:
    with translation.override(language), pytest.raises(ValidationError) as caught:
        VatNumberField(country=country).clean(value)
    assert caught.value.code == reason
    with translation.override(language):
        assert caught.value.messages == [MESSAGES[language][reason]]


@pytest.mark.parametrize("value", [None, "", " \t", "\0", "\v\n\r"])
def test_empty(value: object) -> None:
    assert VatNumberField(required=False).clean(value) is None
    with pytest.raises(ValidationError) as caught:
        VatNumberField().clean(value)
    assert caught.value.code == "required"


@pytest.mark.parametrize("value", [123, True, [], object()])
def test_non_string(value: object) -> None:
    with pytest.raises(ValidationError) as caught:
        VatNumberField().clean(value)
    assert caught.value.code == "invalid_characters"


def test_nonbreaking_space_is_not_empty() -> None:
    with pytest.raises(ValidationError) as caught:
        VatNumberField(required=False).clean("\u00a0")
    assert caught.value.code == "invalid_length"


def test_field_behavior() -> None:
    field = VatNumberField(country="FR")
    number = VatNumber("FR27552032534")
    assert field.clean("27 552 032 534") == number
    assert field.to_python(number) is number
    assert field.prepare_value(number) == number.format()
    assert field.prepare_value("raw") == "raw"
    assert not field.has_changed("FR27552032534", "fr 27 552 032 534")
    assert not field.has_changed(number, "27552032534")
    assert not field.has_changed(None, " \t")
    assert field.has_changed(number, "bad")
    assert field.has_changed("bad", number)
    assert VatNumberField(disabled=True).has_changed("bad", "worse") is False
    with pytest.raises(ValidationError, match="custom checksum"):
        VatNumberField(error_messages={"invalid_checksum": "custom checksum"}).clean("FR28552032534")
