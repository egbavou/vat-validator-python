import asyncio
import builtins
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from vat_number_validator import (
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT,
    AsyncVatNumberChecker,
    CheckStatus,
    UnavailableReason,
    VatNumber,
    VatNumberChecker,
    ViesSettings,
    _vies,
)

from .support import BrokenStream, Runner, body, fixture


@pytest.mark.parametrize(
    ("value", "prefix", "national"),
    [
        ("GR094014201", "EL", "094014201"),
        ("XI220430231", "XI", "220430231"),
    ],
)
def test_request_bytes_and_headers(runner: Runner, value: str, prefix: str, national: str) -> None:
    runner.transport.responses.append(httpx.Response(200, content=fixture("post-valid-be.json")))
    runner.client.headers["X-Private"] = "default"
    runner.client.params = {"private": "parameter"}
    runner.client.cookies.set("private", "cookie")
    runner.check(value, requester="BE0417497106")
    request = runner.transport.requests[0]
    assert request.method == "POST"
    assert str(request.url) == DEFAULT_ENDPOINT
    assert (
        request.content
        == (
            '{"countryCode":"'
            + prefix
            + '","vatNumber":"'
            + national
            + '","requesterMemberStateCode":"BE","requesterNumber":"0417497106"}'
        ).encode()
    )
    assert dict(request.headers) == {
        "host": "ec.europa.eu",
        "content-length": str(len(request.content)),
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": "egbavou/vat-number-validator (+https://github.com/egbavou/vat-validator-python)",
    }


def test_redirect_is_not_followed(runner: Runner) -> None:
    runner.client.follow_redirects = True
    runner.transport.responses.append(httpx.Response(301, headers={"location": "https://example.invalid/next"}))
    result = runner.check()
    assert result.unavailable_reason is UnavailableReason.HTTP_STATUS
    assert str(result.failure) == "VIES returned HTTP 301."
    assert len(runner.transport.requests) == 1


@pytest.mark.parametrize(
    ("requester", "included"),
    [
        ("BE0417497106", True),
        (" BE0417497106 ", True),
        ("", False),
        (None, False),
        ("FR123", False),
        ("GB220430231", False),
        ("CHE116281710", False),
        ("NO974760673", False),
    ],
)
def test_requester(runner: Runner, requester: str | None, included: bool) -> None:
    runner.transport.responses.append(httpx.Response(200, content=body()))
    runner.check(requester=requester)
    expected = {"countryCode": "BE", "vatNumber": "0417497106"}
    if included:
        expected.update(requesterMemberStateCode="BE", requesterNumber="0417497106")
    assert json.loads(runner.transport.requests[0].content) == expected


@pytest.mark.parametrize("value", [VatNumber("FR27552032534"), "27552032534"])
def test_value_object_and_national_input(runner: Runner, value: VatNumber | str) -> None:
    runner.transport.responses.append(httpx.Response(200, content=body()))
    country = "DE" if isinstance(value, VatNumber) else "FR"
    result = runner.check(value, country=country)
    assert result.status is CheckStatus.FOUND
    assert result.vat_number == VatNumber("FR27552032534")
    if isinstance(value, VatNumber):
        assert result.vat_number is value
    assert json.loads(runner.transport.requests[0].content) == {"countryCode": "FR", "vatNumber": "27552032534"}


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectTimeout("timeout"),
        RuntimeError("request failed"),
        RuntimeError("VAT BE0417497106, name Alice Example, address 123 Private Lane"),
    ],
)
def test_transport_failure(runner: Runner, failure: Exception) -> None:
    runner.transport.responses.append(failure)
    before = datetime.now(UTC)
    result = runner.check()
    assert result.status is CheckStatus.UNAVAILABLE
    assert result.unavailable_reason is UnavailableReason.TRANSPORT
    assert result.failure is failure
    assert str(result.failure) == str(failure)
    assert result.registry_error_code is None
    assert result.vat_number == VatNumber("BE0417497106")
    assert before <= result.checked_at <= datetime.now(UTC)
    assert len(runner.transport.requests) == 1


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("Connection reset while reading response"),
        json.JSONDecodeError("Exception thrown by the stream, before decoding", "", 0),
        ValueError("Stream failure"),
    ],
)
def test_body_read_failure(runner: Runner, failure: Exception) -> None:
    runner.transport.responses.append(httpx.Response(200, stream=BrokenStream(failure)))
    result = runner.check()
    assert result.unavailable_reason is UnavailableReason.TRANSPORT
    assert result.failure is failure
    assert len(runner.transport.requests) == 1


@pytest.mark.parametrize("stage", ["build_request", "build_payload"])
def test_request_construction_failure(runner: Runner, monkeypatch: pytest.MonkeyPatch, stage: str) -> None:
    failure = RuntimeError("request construction failed")

    def fail(*args: object) -> Any:
        raise failure

    monkeypatch.setattr(_vies, stage, fail)
    result = runner.check()
    assert result.unavailable_reason is UnavailableReason.TRANSPORT
    assert result.failure is failure
    assert not runner.transport.requests


def test_unexpected_interpretation_failure(runner: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    failure = RuntimeError("decoder failed unexpectedly")

    def fail(content: bytes) -> object:
        raise failure

    monkeypatch.setattr(_vies, "decode", fail)
    runner.transport.responses.append(httpx.Response(200, content=body()))
    result = runner.check()
    assert result.unavailable_reason is UnavailableReason.SCHEMA
    assert result.failure is failure


@pytest.mark.parametrize("failure", [KeyboardInterrupt(), asyncio.CancelledError()])
def test_base_exceptions_propagate(runner: Runner, failure: BaseException) -> None:
    runner.transport.responses.append(failure)
    with pytest.raises(type(failure)):
        runner.check()


@pytest.mark.parametrize(("value", "country"), [(123, None), ("BE0417497106", 123), (VatNumber("BE0417497106"), 123)])
def test_check_types(runner: Runner, value: Any, country: Any) -> None:
    with pytest.raises(TypeError):
        runner.check(value, country=country)
    assert not runner.transport.requests


def test_constructor_conflict_and_types(runner: Runner) -> None:
    with pytest.raises(ValueError, match="timeout"):
        runner.checker(timeout=2.0)
    with pytest.raises(TypeError):
        runner.checker(requester=123)  # type: ignore[arg-type]


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("nan")])
def test_constructor_invalid_timeout(runner: Runner, timeout: float) -> None:
    checker_class = AsyncVatNumberChecker if runner.asynchronous else VatNumberChecker
    with pytest.raises(ValueError, match="timeout"):
        checker_class(timeout=timeout)


def test_injected_client_is_not_closed(runner: Runner) -> None:
    checker = runner.checker()
    if isinstance(checker, AsyncVatNumberChecker):

        async def use() -> None:
            async with checker as entered:
                assert entered is checker
            await checker.aclose()

        asyncio.run(use())
    else:
        with checker as entered:
            assert entered is checker
        checker.close()
    assert not runner.client.is_closed


def test_owned_client_lifecycle_and_settings(runner: Runner) -> None:
    settings = ViesSettings(timeout=2.5, requester="BE0417497106")
    if runner.asynchronous:
        checker = AsyncVatNumberChecker.from_settings(settings)
        assert checker._client.timeout.connect == 2.5

        async def use() -> None:
            async with checker as entered:
                assert entered is checker
            await checker.aclose()

        asyncio.run(use())
        assert checker._client.is_closed
    else:
        sync_checker = VatNumberChecker.from_settings(settings)
        assert sync_checker._client.timeout.connect == 2.5
        with sync_checker as entered:
            assert entered is sync_checker
        sync_checker.close()
        assert sync_checker._client.is_closed


def test_owned_default_timeout(runner: Runner) -> None:
    if runner.asynchronous:
        checker = AsyncVatNumberChecker()
        assert checker._client.timeout.connect == DEFAULT_TIMEOUT
        asyncio.run(checker.aclose())
        assert checker._client.is_closed
    else:
        sync_checker = VatNumberChecker()
        assert sync_checker._client.timeout.connect == DEFAULT_TIMEOUT
        sync_checker.close()
        assert sync_checker._client.is_closed


def test_from_settings_with_injected_client(runner: Runner) -> None:
    settings = ViesSettings(timeout=-1, requester="BE0417497106")
    runner.transport.responses.append(httpx.Response(200, content=body(requestIdentifier="ref")))
    if isinstance(runner.client, httpx.AsyncClient):
        checker = AsyncVatNumberChecker.from_settings(settings, runner.client)
        result = asyncio.run(checker.check("BE0417497106"))
    else:
        result = VatNumberChecker.from_settings(settings, runner.client).check("BE0417497106")
    assert result.reference == "ref"


def test_missing_httpx_message(runner: Runner, monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def import_without_httpx(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "httpx":
            raise ImportError("no httpx")
        return original_import(name, *args, **kwargs)

    checker_class = AsyncVatNumberChecker if runner.asynchronous else VatNumberChecker
    monkeypatch.setattr(builtins, "__import__", import_without_httpx)
    with pytest.raises(ImportError, match=r"vat-number-validator\[httpx\]"):
        checker_class()


def test_result_privacy_immutability(runner: Runner) -> None:
    runner.transport.responses.append(
        httpx.Response(200, content=body(name="Alice Example", address="123 Private Lane"))
    )
    result = runner.check()
    assert result.name == "Alice Example"
    assert result.address == "123 Private Lane"
    assert "Alice Example" not in repr(result)
    assert "123 Private Lane" not in repr(result)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.name = "other"  # type: ignore[misc]
