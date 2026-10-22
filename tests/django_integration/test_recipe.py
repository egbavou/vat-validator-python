from typing import Any

import pytest
from django import forms
from django.core.exceptions import ValidationError

from vat_number_validator import VatNumber
from vat_number_validator.django.validators import VatNumberValidator


class CompanyForm(forms.Form):
    vat_country = forms.CharField(required=False)
    vat_number = forms.CharField()

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        country = data.get("vat_country") or None
        try:
            VatNumberValidator(country=country)(data.get("vat_number"))
        except ValidationError as error:
            self.add_error("vat_number", error)
        else:
            data["vat_number"] = VatNumber(data["vat_number"], country=country)
        return data


@pytest.mark.parametrize(
    ("country", "number", "reason"),
    [
        ("FR", "27552032534", None),
        ("", "FR27552032534", None),
        ("", "27552032534", "missing_country_prefix"),
        ("FR", "BE0403170701", "country_mismatch"),
        (" ", "27552032534", "missing_country_prefix"),
    ],
)
def test_recipe(country: str, number: str, reason: str | None) -> None:
    form = CompanyForm({"vat_country": country, "vat_number": number})
    assert form.is_valid() is (reason is None)
    if reason is None:
        assert form.cleaned_data["vat_number"] == VatNumber("FR27552032534")
    else:
        assert form.errors.as_data()["vat_number"][0].code == reason
