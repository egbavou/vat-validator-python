import asyncio
import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vat_number_validator import (
    AsyncVatNumberChecker,
    CheckStatus,
    UnavailableReason,
    VatNumber,
    VatNumberChecker,
    VatNumberCheckResult,
    ViesError,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "vies"
DATE = "2026-10-22T01:00:38.289Z"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def body(**fields: object) -> bytes:
    return json.dumps({"valid": True, "requestDate": DATE, **fields}, ensure_ascii=True).encode()


class QueueTransport(httpx.MockTransport):
    def __init__(self) -> None:
        self.responses: deque[httpx.Response | BaseException] = deque()
        self.requests: list[httpx.Request] = []
        super().__init__(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self.responses.popleft()
        if isinstance(response, BaseException):
            raise response
        return response


class BrokenStream(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    def __iter__(self) -> "BrokenStream":
        return self

    def __next__(self) -> bytes:
        raise self.failure

    def __aiter__(self) -> "BrokenStream":
        return self

    async def __anext__(self) -> bytes:
        raise self.failure


class Runner:
    def __init__(self, *, asynchronous: bool) -> None:
        self.asynchronous = asynchronous
        self.transport = QueueTransport()
        self.client: httpx.Client | httpx.AsyncClient
        if asynchronous:
            self.client = httpx.AsyncClient(transport=self.transport)
        else:
            self.client = httpx.Client(transport=self.transport)

    def checker(self, requester: str | None = None, **kwargs: object) -> VatNumberChecker | AsyncVatNumberChecker:
        if isinstance(self.client, httpx.AsyncClient):
            return AsyncVatNumberChecker(self.client, requester=requester, **kwargs)  # type: ignore[arg-type]
        return VatNumberChecker(self.client, requester=requester, **kwargs)  # type: ignore[arg-type]

    def check(
        self,
        value: str | VatNumber = "BE0417497106",
        *,
        country: str | None = None,
        requester: str | None = None,
        **kwargs: object,
    ) -> VatNumberCheckResult:
        checker = self.checker(requester, **kwargs)
        if isinstance(checker, AsyncVatNumberChecker):
            return asyncio.run(checker.check(value, country=country))
        return checker.check(value, country=country)

    def close(self) -> None:
        if isinstance(self.client, httpx.AsyncClient):
            asyncio.run(self.client.aclose())
        else:
            self.client.close()


@dataclass(frozen=True, kw_only=True)
class Case:
    label: str
    content: bytes = b""
    input: str = "BE0417497106"
    requester: str | None = None
    status_code: int = 200
    status: CheckStatus = CheckStatus.FOUND
    reason: UnavailableReason | None = None
    message: str | None = None
    name: str | None = None
    address: str | None = None
    reference: str | None = None
    registry_error: str | None = None
    date: str | None = DATE


def cases() -> list[Case]:
    rows: list[Case] = []
    for path in sorted(FIXTURES.glob("post-valid-*.json")):
        data = json.loads(path.read_bytes())
        rows.append(
            Case(
                label=path.name,
                content=path.read_bytes(),
                input=data["countryCode"] + data["vatNumber"],
                date=data["requestDate"],
                name=_identity(data.get("name")),
                address=_identity(data.get("address")),
            )
        )
    for path in sorted(FIXTURES.iterdir()):
        if path.name.startswith(("post-error-", "post-test-service-error-")):
            data = json.loads(path.read_bytes())
            rows.append(
                Case(
                    label=path.name,
                    content=path.read_bytes(),
                    status=CheckStatus.UNAVAILABLE,
                    reason=UnavailableReason.REGISTRY_ERROR,
                    registry_error=data["errorWrappers"][0]["error"],
                    date=None,
                )
            )
        if path.name.startswith("get-error-"):
            rows.append(schema_case(path.name, path.read_bytes(), 'no boolean "valid" field.'))
        if path.name.startswith("post-http") or path.suffix == ".html":
            match = re.search(r"http([0-9]{3})", path.name)
            assert match is not None
            http_status = int(match[1])
            rows.append(
                Case(
                    label=path.name,
                    content=path.read_bytes(),
                    status_code=http_status,
                    status=CheckStatus.UNAVAILABLE,
                    reason=UnavailableReason.HTTP_STATUS,
                    message=f"VIES returned HTTP {http_status}.",
                    date=None,
                )
            )
    for number, file in [
        ("FR44732829320", "post-invalid-fr.json"),
        ("ESA28015865", "post-invalid-es-placeholder-name.json"),
    ]:
        data = json.loads(fixture(file))
        rows.append(
            Case(
                label=file, content=fixture(file), input=number, status=CheckStatus.NOT_FOUND, date=data["requestDate"]
            )
        )
    rows.append(
        Case(
            label="consultation",
            content=fixture("post-valid-with-requester-dk.json"),
            input="DK24256790",
            requester="BE0417497106",
            reference="WAPIAAAAaFhMB-VU",
            date=json.loads(fixture("post-valid-with-requester-dk.json"))["requestDate"],
            name=_identity(json.loads(fixture("post-valid-with-requester-dk.json")).get("name")),
            address=_identity(json.loads(fixture("post-valid-with-requester-dk.json")).get("address")),
        )
    )
    for requester in [None, "", "FR123", "GB220430231", "CHE116281710", "NO974760673"]:
        rows.append(
            Case(
                label=f"hidden-reference-{requester}",
                content=body(requestIdentifier="private-ref"),
                requester=requester,
            )
        )
    for data, message in [
        (b'{"foo":1}', 'no boolean "valid" field.'),
        (b'"text"', "is not a JSON object."),
        (b"null", "is not a JSON object."),
        (b'{"valid":"true"}', 'no boolean "valid" field.'),
        (b'{"valid":true}', 'no valid "requestDate" timestamp.'),
        (
            b'{"valid":true,"requestDate":"bad","vatNumber":"private VAT",'
            b'"name":"private name","address":"private address"}',
            'no valid "requestDate" timestamp.',
        ),
        (b"[]", 'no boolean "valid" field.'),
        (b"[true]", 'no boolean "valid" field.'),
    ]:
        rows.append(schema_case(f"schema-{data!r}", data, message))
    for field in ["name", "address", "requestIdentifier", "countryCode", "vatNumber"]:
        for value in [
            {"private": "VAT BE0417497106, name Alice Example, address 123 Private Lane"},
            [],
            42,
            False,
            None,
        ]:
            for valid in [True, False]:
                rows.append(
                    schema_case(
                        f"{field}-{value!r}-{valid}",
                        body(**{field: value, "valid": valid}),
                        f'no string "{field}" field.',
                    )
                )
    for date in [
        DATE + "\0",
        "2026-02-31T01:00:38.289Z",
        "2026-10-22T25:00:38.289Z",
        "2026-10-22T01:00:60.289Z",
        "0000-10-22T01:00:38.289Z",
    ]:
        rows.append(schema_case(f"date-{date!r}", body(requestDate=date), 'no valid "requestDate" timestamp.'))
    for wrappers, code in [
        (None, None),
        ([], None),
        ([{"error": 5}], None),
        ([["X"]], None),
        ({"0": {"error": "X"}}, "X"),
        ({"00": {"error": "X"}}, None),
        ([{"error": "MS_MAX_CONCURRENT_REQ"}], "MS_MAX_CONCURRENT_REQ"),
    ]:
        rows.append(
            Case(
                label=f"wrappers-{wrappers!r}",
                content=body(valid=False, errorWrappers=wrappers),
                status=CheckStatus.UNAVAILABLE,
                reason=UnavailableReason.REGISTRY_ERROR,
                registry_error=code,
                date=None,
            )
        )
    rows.append(Case(label="nul-key", content=b'{"\\u0000a":1,' + body()[1:]))
    for text, expected in [
        ("  \nFOO  BAR \n\nLINE 2\n", "FOO  BAR\nLINE 2"),
        ("---", None),
        ("", None),
        ("N/A", None),
        ("\0 ---\t", None),
        ("\u00a0", "\u00a0"),
    ]:
        rows.append(
            Case(label=f"text-{text!r}", content=body(name=text, address=text), name=expected, address=expected)
        )
    for separator in ["\v", "\f", "\x85", "\u2028", "\u2029", "\r\n", "\r", "\n"]:
        rows.append(
            Case(
                label=f"line-{separator!r}",
                content=body(name=f" A {separator} B ", address=f" A {separator} B "),
                name="A\nB",
                address="A\nB",
            )
        )
    for data in [
        b"",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"NaN",
        b"Infinity",
        b"-Infinity",
        rb'{"x":"\ud800","x":"ok"}',
        b"[" * 512 + b"0" + b"]" * 512,
        fixture("http404-not-found.html"),
    ]:
        rows.append(
            Case(
                label=f"invalid-json-{data[:40]!r}",
                content=data,
                status=CheckStatus.UNAVAILABLE,
                reason=UnavailableReason.INVALID_JSON,
                date=None,
            )
        )
    for number in ["GB220430231", "CHE116281710", "NO974760673"]:
        rows.append(
            Case(
                label=number,
                input=number,
                status=CheckStatus.UNAVAILABLE,
                reason=UnavailableReason.NO_SOURCE,
                date=None,
            )
        )
    rows.append(Case(label="invalid-format", input="FR123", status=CheckStatus.INVALID_FORMAT, date=None))
    return rows


def _identity(value: str | None) -> str | None:
    # Fixture expectations only: each real fixture uses CR/LF and ordinary spaces.
    if value is None:
        return None
    text = "\n".join(line.strip(" \t\r\n\0\v") for line in value.splitlines() if line.strip(" \t\r\n\0\v"))
    return None if text in ["", "---", "N/A"] else text


def schema_case(label: str, content: bytes, suffix: str) -> Case:
    message = f"VIES response {suffix}" if suffix.startswith("is ") else f"VIES response has {suffix}"
    return Case(
        label=label,
        content=content,
        status=CheckStatus.UNAVAILABLE,
        reason=UnavailableReason.SCHEMA,
        message=message,
        date=None,
    )


CASES = cases()


def run_case(case: Case, *, asynchronous: bool) -> None:
    runner = Runner(asynchronous=asynchronous)
    runner.transport.responses.append(httpx.Response(case.status_code, content=case.content))
    before = datetime.now(UTC)
    try:
        result = runner.check(case.input, requester=case.requester)
        assert result.status is case.status
        assert result.unavailable_reason is case.reason
        assert result.registry_error_code == case.registry_error
        assert result.name == case.name
        assert result.address == case.address
        assert result.reference == case.reference
        if case.status is CheckStatus.INVALID_FORMAT:
            assert result.vat_number is None
        else:
            assert result.vat_number == VatNumber(case.input)
        if case.message is not None:
            assert isinstance(result.failure, ViesError)
            assert str(result.failure) == case.message
        elif case.reason is UnavailableReason.INVALID_JSON:
            assert isinstance(result.failure, (ValueError, UnicodeDecodeError, RecursionError))
        else:
            assert result.failure is None
        if case.date is not None:
            assert result.checked_at == datetime.fromisoformat(case.date.replace("Z", "+00:00"))
            assert result.checked_at.tzinfo is UTC
        else:
            assert before <= result.checked_at <= datetime.now(UTC)
        expected_requests = (
            0 if case.reason is UnavailableReason.NO_SOURCE or case.status is CheckStatus.INVALID_FORMAT else 1
        )
        assert len(runner.transport.requests) == expected_requests
    finally:
        runner.close()
