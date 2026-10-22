from pathlib import Path

from babel.messages.pofile import read_po

MESSAGES = {
    "en": {
        "invalid_characters": "This field contains characters that are not allowed in a VAT number.",
        "invalid_length": "This field does not have the length of a VAT number for this country.",
        "invalid_checksum": "This field is not a valid VAT number (wrong check digits).",
        "invalid_structure": "This field does not have the structure of a VAT number for this country.",
        "unknown_country_prefix": "This field starts with an unknown country prefix.",
        "missing_country_prefix": "This field must start with a country prefix, such as FR or DE.",
        "country_mismatch": "This field does not belong to the selected country.",
        "not_found": "This VAT number is not registered in VIES.",
        "unavailable": "This VAT number cannot be verified right now. Please try again later.",
    },
}

with Path("src/vat_number_validator/django/locale/fr/LC_MESSAGES/django.po").open("rb") as file:
    catalogue = read_po(file, locale="fr")
MESSAGES["fr"] = {}
for code, english in MESSAGES["en"].items():
    translated = catalogue[english].string
    assert isinstance(translated, str)
    assert translated != english
    MESSAGES["fr"][code] = translated

REASONS = [
    ("FRIO334175221", None, "invalid_characters"),
    ("FR123", None, "invalid_length"),
    ("FR28552032534", None, "invalid_checksum"),
    ("BE2123456791", None, "invalid_structure"),
    ("ZZ27552032534", None, "unknown_country_prefix"),
    ("27552032534", None, "missing_country_prefix"),
    ("BE0403170701", "FR", "country_mismatch"),
]
