from dataclasses import FrozenInstanceError

import pytest

from vat_number_validator import DEFAULT_TIMEOUT, ViesSettings
from vat_number_validator._settings import _laravel_env, _php_is_numeric, normalize_requester, normalize_timeout


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (3, 3.0),
        (2.5, 2.5),
        ("2.5", 2.5),
        (0, 20.0),
        (-1, 20.0),
        ("0", 20.0),
        ("garbage", 20.0),
        (None, 20.0),
        (False, 20.0),
        (True, 20.0),
        (" 2.5 ", 2.5),
        ("1e3", 1000.0),
        ("1_0", 20.0),
        ("inf", 20.0),
        ("nan", 20.0),
        ("0x1A", 20.0),
        (float("nan"), 20.0),
        ("\v2.5\f", 2.5),
        ("\0 2.5", 20.0),
        ("+.5", 0.5),
        ("2.", 2.0),
        ("1e999", float("inf")),
        ([], 20.0),
        ({}, 20.0),
        ("\uff12.\uff15", 20.0),
    ],
)
def test_timeout_normalization(value: object, expected: float) -> None:
    assert normalize_timeout(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BE0417497106", "BE0417497106"),
        ("", None),
        (None, None),
        (123, None),
        ("  ", None),
        (" BE0417497106 ", " BE0417497106 "),
        ("\0\v", None),
        ("\u00a0", "\u00a0"),
        (True, None),
        ("FR123", "FR123"),
        ("CHE116281710", "CHE116281710"),
    ],
)
def test_requester_normalization(value: object, expected: str | None) -> None:
    assert normalize_requester(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        ("(TrUe)", True),
        ("false", False),
        ("(false)", False),
        ("empty", ""),
        ("(empty)", ""),
        ("null", None),
        ("(null)", None),
        ('"BE0417497106"', "BE0417497106"),
        ("'BE0417497106'", "BE0417497106"),
        ('"BE\n0417497106"', '"BE\n0417497106"'),
        (" true ", " true "),
        ('"true"', "true"),
    ],
)
def test_laravel_env(value: str, expected: object) -> None:
    assert _laravel_env({"V": value}, "V", 20) == expected


def test_numeric_types() -> None:
    assert _php_is_numeric(float("nan"))
    assert not _php_is_numeric(True)
    assert not _php_is_numeric(b"2.5")


def test_env_defaults_and_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    assert DEFAULT_TIMEOUT == 20.0
    assert ViesSettings.from_env({}) == ViesSettings()
    assert _laravel_env({}, "V", 20) == 20
    for value in ["true", "(false)", "empty", "(null)", "TRUE"]:
        assert (
            ViesSettings.from_env({"VAT_VALIDATOR_VIES_TIMEOUT": value, "VAT_VALIDATOR_REQUESTER": value})
            == ViesSettings()
        )
    assert ViesSettings.from_env(
        {"VAT_VALIDATOR_VIES_TIMEOUT": '"2.5"', "VAT_VALIDATOR_REQUESTER": "' BE0417497106 '"}
    ) == ViesSettings(timeout=2.5, requester=" BE0417497106 ")
    monkeypatch.setenv("VAT_VALIDATOR_VIES_TIMEOUT", "3")
    monkeypatch.setenv("VAT_VALIDATOR_REQUESTER", "BE0417497106")
    assert ViesSettings.from_env() == ViesSettings(timeout=3.0, requester="BE0417497106")


def test_settings_are_frozen_slotted_and_keyword_only() -> None:
    settings = ViesSettings()
    with pytest.raises(FrozenInstanceError):
        settings.timeout = 3  # type: ignore[misc]
    assert not hasattr(settings, "__dict__")
    with pytest.raises(TypeError):
        ViesSettings(3)  # type: ignore[call-arg]
