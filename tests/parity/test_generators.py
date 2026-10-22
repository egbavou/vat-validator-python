"""National generator coverage checks run without PHP or the parity marker."""

import re
from collections import Counter

import pytest

from tests.parity.generators import LENGTHS, families
from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber
from vat_number_validator._countries import prefixes


def outcomes(values: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for value in values:
        try:
            VatNumber(value)
        except InvalidIdentifierError as error:
            counts[error.reason.value] += 1
        else:
            counts["valid"] += 1
    return counts


def test_generated_prefixes_match_registered_prefixes() -> None:
    assert set(LENGTHS) == set(prefixes())


@pytest.mark.parametrize("prefix", prefixes())
def test_national_parts_reach_checksum(prefix: str) -> None:
    values = [case["input"] for case in families()["national_parts"] if case["input"].startswith(prefix)]
    counts = outcomes(values)
    assert counts["valid"] > 0, (prefix, counts)
    assert counts[FailureReason.INVALID_CHECKSUM.value] > 0, (prefix, counts)


@pytest.mark.parametrize(
    "pattern",
    [r"[0-9]{7}[A-W]", r"[0-9]{7}[A-W][A-I]", r"[0-9][A-Z+*][0-9]{5}[A-W]"],
    ids=["eight-character", "nine-character", "old-format"],
)
def test_all_irish_families_reach_checksum(pattern: str) -> None:
    values = [
        case["input"]
        for case in families()["national_parts"]
        if case["input"].startswith("IE") and re.fullmatch(pattern, case["input"][2:])
    ]
    counts = outcomes(values)
    assert counts["valid"] > 0, (pattern, counts)
    assert counts[FailureReason.INVALID_CHECKSUM.value] > 0, (pattern, counts)
