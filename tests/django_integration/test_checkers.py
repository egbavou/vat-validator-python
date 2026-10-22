import json
from unittest.mock import Mock

import httpx
import pytest
from django.test import override_settings

from tests.httpx_integration.support import QueueTransport, fixture
from vat_number_validator import VatNumberChecker
from vat_number_validator.django.checkers import get_vat_number_checker


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
        (False, 20.0),
        (" 2.5 ", 2.5),
        ("1e3", 1000.0),
        ("1_0", 20.0),
        ("inf", 20.0),
        ("nan", 20.0),
        ("0x1A", 20.0),
    ],
)
def test_timeout(value: object, expected: float, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAT_VALIDATOR_VIES_TIMEOUT", raising=False)
    with override_settings(VAT_NUMBER_VALIDATOR={"VIES": {"TIMEOUT": value}}):
        checker = get_vat_number_checker()
        assert checker._client.timeout.read == expected
        assert get_vat_number_checker() is checker
    assert checker._client.is_closed


@pytest.mark.parametrize(
    ("value", "included"),
    [
        ("BE0417497106", True),
        ("", False),
        (None, False),
        (123, False),
        ("FR123", False),
        ("CHE116281710", False),
        ("  ", False),
        (" BE0417497106 ", True),
    ],
)
def test_requester(value: object, included: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAT_VALIDATOR_REQUESTER", raising=False)
    transport = QueueTransport()
    transport.responses.append(httpx.Response(200, content=fixture("post-valid-be.json")))
    factory = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: factory(transport=transport, **kwargs))
    with override_settings(VAT_NUMBER_VALIDATOR={"VIES": {"REQUESTER": value}}):
        get_vat_number_checker().check("BE0417497106")
    payload = json.loads(transport.requests[0].content)
    assert ("requesterNumber" in payload) is included


@pytest.mark.parametrize("config", [{}, {"VIES": None}, {"VIES": {}}, {"VIES": {"TIMEOUT": None, "REQUESTER": None}}])
def test_environment_fallback(config: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAT_VALIDATOR_VIES_TIMEOUT", "2.5")
    monkeypatch.setenv("VAT_VALIDATOR_REQUESTER", "BE0417497106")
    with override_settings(VAT_NUMBER_VALIDATOR=config):
        checker = get_vat_number_checker()
        assert checker._client.timeout.read == 2.5
        assert str(checker._requester) == "BE0417497106"


def test_reset_and_ownership() -> None:
    with override_settings(VAT_NUMBER_VALIDATOR={}):
        first = get_vat_number_checker()
        with override_settings(VAT_NUMBER_VALIDATOR={"VIES": {"TIMEOUT": 3}}):
            assert first._client.is_closed
            second = get_vat_number_checker()
            assert second is not first
        assert second._client.is_closed
        third = get_vat_number_checker()
        assert third is not first
    assert third._client.is_closed
    checker = Mock(spec=VatNumberChecker)
    with override_settings(VAT_NUMBER_VALIDATOR={"CHECKER": checker}):
        assert get_vat_number_checker() is checker
        assert get_vat_number_checker() is checker
    checker.close.assert_not_called()
