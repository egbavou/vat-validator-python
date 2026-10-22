import gettext
import subprocess
import sys
from pathlib import Path

from django.utils import translation

from tests.django_integration.support import MESSAGES
from vat_number_validator.django.validators import MESSAGES as LAZY_MESSAGES


def test_catalogue_matches_source(tmp_path: Path) -> None:
    locale = Path("src/vat_number_validator/django/locale/fr/LC_MESSAGES")
    output = tmp_path / "django.mo"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "compile",
            "-D",
            "django",
            "-i",
            str(locale / "django.po"),
            "-o",
            str(output),
        ],
        check=True,
    )
    with output.open("rb") as file:
        expected = gettext.GNUTranslations(file)
    with (locale / "django.mo").open("rb") as file:
        actual = gettext.GNUTranslations(file)
    for code, english in MESSAGES["en"].items():
        assert actual.gettext(english) == expected.gettext(english) == MESSAGES["fr"][code]
        for language in ("en", "fr", "en"):
            with translation.override(language):
                assert str(LAZY_MESSAGES[code]) == MESSAGES[language][code]
