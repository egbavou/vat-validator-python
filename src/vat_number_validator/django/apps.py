from typing import final

from django.apps import AppConfig


@final
class VatNumberValidatorConfig(AppConfig):
    name = "vat_number_validator.django"
    label = "vat_number_validator"
    verbose_name = "VAT number validator"
