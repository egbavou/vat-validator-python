"""Opt-in real service tests; excluded by default and never part of CI."""

import asyncio
import json
import os

import pytest

if os.environ.get("VAT_NUMBER_VALIDATOR_LIVE") != "1":
    pytest.skip("Set VAT_NUMBER_VALIDATOR_LIVE=1 to call VIES", allow_module_level=True)

pytest.importorskip("httpx")
import httpx

from vat_number_validator import (
    AsyncVatNumberChecker,
    CheckStatus,
    UnavailableReason,
    VatNumber,
    VatNumberChecker,
    VatNumberCheckResult,
)
from vat_number_validator._vies import build_payload, build_request, interpret

pytestmark = pytest.mark.live
TEST_ENDPOINT = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-test-service"


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    ("national", "status"),
    [("100", CheckStatus.FOUND), ("200", CheckStatus.NOT_FOUND), ("600", CheckStatus.UNAVAILABLE)],
)
def test_official_service(asynchronous: bool, national: str, status: CheckStatus) -> None:
    number = VatNumber("BE0417497106")
    payload = json.loads(build_payload(number, None))
    payload["vatNumber"] = national
    request = build_request(TEST_ENDPOINT, json.dumps(payload, separators=(",", ":")).encode())

    async def send() -> httpx.Response:
        async with httpx.AsyncClient(timeout=20) as client:
            return await client.send(request, follow_redirects=False)

    if asynchronous:
        response = asyncio.run(send())
    else:
        with httpx.Client(timeout=20) as client:
            response = client.send(request, follow_redirects=False)
    result = interpret(response.status_code, response.content, number, False)
    assert result.status is status
    if status is CheckStatus.UNAVAILABLE:
        assert result.unavailable_reason is UnavailableReason.REGISTRY_ERROR
        assert result.registry_error_code == "MS_MAX_CONCURRENT_REQ"


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    ("number", "status"), [("FR27552032534", CheckStatus.FOUND), ("FR44732829320", CheckStatus.NOT_FOUND)]
)
def test_real_numbers(asynchronous: bool, number: str, status: CheckStatus) -> None:
    async def check() -> VatNumberCheckResult:
        async with AsyncVatNumberChecker() as checker:
            return await checker.check(number)

    if asynchronous:
        result = asyncio.run(check())
    else:
        with VatNumberChecker() as checker:
            result = checker.check(number)
    if result.status is CheckStatus.UNAVAILABLE and result.unavailable_reason is UnavailableReason.REGISTRY_ERROR:
        pytest.skip(f"VIES transient error: {result.registry_error_code}")
    assert result.status is status
