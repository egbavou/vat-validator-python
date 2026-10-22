"""Cross-check all PHP research vectors against python-stdnum (development only)."""

import re

import pytest

from tests.cases import INVALID_NUMBERS, VALID_NUMBERS
from vat_number_validator import VatNumber
from vat_number_validator._cleanup import ascii_upper

pytest.importorskip("stdnum")
eu_vat = pytest.importorskip("stdnum.eu.vat")
gb_vat = pytest.importorskip("stdnum.gb.vat")
ch_uid = pytest.importorskip("stdnum.ch.uid")
no_orgnr = pytest.importorskip("stdnum.no.orgnr")

# Sources: design §13.1; PHP CrossCheckTest.php; docs/research/2026-10-22-country-rules.md §3.
# This divergence list is valid for python-stdnum 2.2.
DOCUMENTED_DIVERGENCES: dict[str, str] = {
    "LV33123456789": "LV law art. 6(2), effective 2021-06-28: personal codes 32-39 have no checksum.",
    "LV38000000000": "LV law art. 6(2), effective 2021-06-28: personal codes 32-39 have no checksum.",
    "LV39999999999": "LV law art. 6(2), effective 2021-06-28: personal codes 32-39 have no checksum.",
    "CZ699004743": "PHP design §9 / research CZ: nine-digit VČP starting with 6 have unpublished construction.",
    "BG7501011233": "PHP design §9 / research BG: ten-digit natural-person numbers are format only.",
    "BG1234567890": "PHP design §9 / research BG: ten-digit numbers include unpublished NAP service formats.",
    "CY12000000F": "PHP CrossCheckTest / research CY: the exclusion of prefix 12 has no source.",
    "CZ90177045": "Research CZ / PHP design §9: there is no primary source excluding IČO starting with 9.",
    "NLABCDEFGHIJ27": "BMF pp.14-17 / research NL: MOD97 permits the full alphabet, without mandatory B.",
    "NL+*0000000B43": "BMF pp.14-17 / research NL: MOD97 permits + and *; stdnum requires nine digits.",
    "SE556012579002": "BMF p.19 / research SE: suffix 01-94 takes precedence over Skatteverket's 01-only rule.",
    "EE200070005": "BMF p.22 / PHP CrossCheckTest: initial 10 is required regardless of the checksum.",
    "EL09401924": "Research EL / PHP design §9: nine digits are required; stdnum pads eight-digit inputs.",
    "XI010000090": "BMF pp.8-9 / PHP CrossCheckTest: MOD9755 requires the seven-digit body > 1000000.",
    "XI950000087": "BMF pp.8-9 / PHP CrossCheckTest: MOD97 excludes the body range 9490001-9700000.",
    "XI220430231000": "BMF pp.8-9,32-33 / PHP CrossCheckTest: branch suffix 000 is excluded.",
    "GB100000047": "BMF pp.8-9 / research XI-GB: remainder 55 is not an accepted MOD97/MOD9755 control.",
    "GB010000090": "BMF pp.8-9 / research XI-GB: MOD9755 requires the seven-digit body > 1000000.",
    "GB950000087": "BMF pp.8-9 / research XI-GB: MOD97 excludes the body range 9490001-9700000.",
}

_INPUTS = [row[0] for row in [*VALID_NUMBERS.values(), *INVALID_NUMBERS.values()]]


def _oracle(value: str) -> bool:
    clean = ascii_upper(value.translate(str.maketrans("", "", " .-")))
    if clean.startswith("GB"):
        return bool(gb_vat.is_valid(clean))
    if clean.startswith("CHE"):
        return bool(ch_uid.is_valid(re.sub(r"(?:MWST|TVA|IVA)\Z", "", clean)))
    if clean.startswith("NO"):
        # stdnum.no.orgnr takes a national organization number, without the NO prefix.
        return bool(no_orgnr.is_valid(re.sub(r"MVA\Z", "", clean[2:])))
    return bool(eu_vat.is_valid(clean))


@pytest.mark.parametrize("value", _INPUTS)
def test_cross_check(value: str) -> None:
    ours = VatNumber.is_valid(value)
    theirs = _oracle(value)
    if value in DOCUMENTED_DIVERGENCES:
        assert ours != theirs, DOCUMENTED_DIVERGENCES[value]
    else:
        assert ours == theirs, f"{value} needs a research-backed explanation"


def test_divergences_are_all_exercised() -> None:
    assert len(DOCUMENTED_DIVERGENCES) == 19
    assert DOCUMENTED_DIVERGENCES.keys() <= set(_INPUTS)
    assert all(DOCUMENTED_DIVERGENCES.values())
