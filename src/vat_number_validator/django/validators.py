"""Django validators corresponding to the Laravel VAT rules."""

from typing import TYPE_CHECKING, Any, final

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from .. import CheckStatus, FailureReason, InvalidIdentifierError, VatNumber
from .checkers import get_vat_number_checker

MESSAGES = {
    "invalid_characters": _("This field contains characters that are not allowed in a VAT number."),
    "invalid_length": _("This field does not have the length of a VAT number for this country."),
    "invalid_checksum": _("This field is not a valid VAT number (wrong check digits)."),
    "invalid_structure": _("This field does not have the structure of a VAT number for this country."),
    "unknown_country_prefix": _("This field starts with an unknown country prefix."),
    "missing_country_prefix": _("This field must start with a country prefix, such as FR or DE."),
    "country_mismatch": _("This field does not belong to the selected country."),
    "not_found": _("This VAT number is not registered in VIES."),
    "unavailable": _("This VAT number cannot be verified right now. Please try again later."),
}


def _parse(value: object, country: str | None) -> VatNumber:
    if isinstance(value, VatNumber):
        return value
    if not isinstance(value, str):
        reason = FailureReason.INVALID_CHARACTERS
    else:
        try:
            return VatNumber(value, country=country)
        except InvalidIdentifierError as error:
            reason = error.reason
    raise ValidationError(MESSAGES[reason.value], code=reason.value)


@final
@deconstructible
class VatNumberValidator:
    def __init__(self, country: str | None = None) -> None:
        self.country = country

    if TYPE_CHECKING:

        def deconstruct(self) -> tuple[str, tuple[Any, ...], dict[str, Any]]: ...

    def __call__(self, value: object) -> None:
        _parse(value, self.country)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and isinstance(other, VatNumberValidator) and self.country == other.country


@final
@deconstructible
class VatNumberExistsValidator:
    def __init__(self, country: str | None = None, fail_when_unavailable: bool = False) -> None:
        self.country = country
        self.fail_when_unavailable = fail_when_unavailable

    if TYPE_CHECKING:

        def deconstruct(self) -> tuple[str, tuple[Any, ...], dict[str, Any]]: ...

    def __call__(self, value: object) -> None:
        number = _parse(value, self.country)
        # VatNumberExistsRule.php resolves the shared checker only after format validation.
        status = get_vat_number_checker().check(number).status
        if status is CheckStatus.NOT_FOUND:
            raise ValidationError(MESSAGES["not_found"], code="not_found")
        if status is CheckStatus.UNAVAILABLE and self.fail_when_unavailable:
            raise ValidationError(MESSAGES["unavailable"], code="unavailable")

    def __eq__(self, other: object) -> bool:
        return (
            type(other) is type(self)
            and isinstance(other, VatNumberExistsValidator)
            and self.country == other.country
            and self.fail_when_unavailable == other.fail_when_unavailable
        )
