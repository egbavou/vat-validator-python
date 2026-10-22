"""Differential tests. No network: PHP uses an in-process fake PSR-18 client."""

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.parity.generators import SEED, families
from vat_number_validator import (
    CheckStatus,
    InvalidIdentifierError,
    UnavailableReason,
    VatNumber,
    VatNumberChecker,
    ViesError,
    ViesSettings,
)

pytestmark = pytest.mark.parity
PHP_DIR = Path(os.environ.get("VAT_VALIDATOR_PHP_DIR", "../vat-validator")).resolve()
EMULATED_JSON_ERRORS = {
    "Maximum stack depth exceeded",
    "Single unpaired UTF-16 surrogate in unicode escape",
}


def encoded(value: str) -> str:
    return base64.b64encode(value.encode("utf-8", "surrogateescape")).decode("ascii")


def wire(case: dict[str, Any]) -> dict[str, Any]:
    result = dict(case)
    for key in ("input", "country", "requester"):
        if isinstance(result.get(key), str):
            result[key] = encoded(result[key])
    if "body" in result:
        result["body"] = base64.b64encode(result["body"]).decode("ascii")
    if "env" in result:
        result["env"] = {key: encoded(value) for key, value in result["env"].items()}
    return result


def python_projection(case: dict[str, Any]) -> dict[str, Any]:
    operation = case["op"]
    if operation == "settings":
        settings = ViesSettings.from_env(case["env"])
        return {"timeout": settings.timeout, "requester": settings.requester}
    if operation in ("parse", "from_siren"):
        try:
            number = (
                VatNumber.from_siren(case["input"])
                if operation == "from_siren"
                else VatNumber(case["input"], country=case.get("country"))
            )
        except InvalidIdentifierError as error:
            return {"reason": error.reason.value}
        return {
            "value": number.value,
            "prefix": number.prefix,
            "number": number.number,
            "country_code": number.country_code,
        }
    import httpx

    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(
            {
                "method": request.method,
                "url": str(request.url),
                "body": request.content.decode("ascii"),
                "Content-Type": request.headers["Content-Type"],
                "Accept": request.headers["Accept"],
            }
        )
        if case.get("throw"):
            raise RuntimeError("injected")
        return httpx.Response(case.get("status", 200), content=case["body"])

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = VatNumberChecker(client, requester=case.get("requester")).check(
            case["input"], country=case.get("country")
        )
    failure: object = None
    if isinstance(result.failure, ViesError):
        failure = {"kind": "ViesError", "message": str(result.failure)}
    elif result.failure is not None:
        failure = {"kind": "original"}
        if case.get("throw") or (
            result.unavailable_reason is UnavailableReason.INVALID_JSON and str(result.failure) in EMULATED_JSON_ERRORS
        ):
            failure["message"] = str(result.failure)
    return {
        "status": result.status.value,
        "vat_number": str(result.vat_number) if result.vat_number else None,
        "name": result.name,
        "address": result.address,
        "reference": result.reference,
        "unavailable_reason": result.unavailable_reason,
        "registry_error_code": result.registry_error_code,
        "checked_at": result.checked_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if result.status in (CheckStatus.FOUND, CheckStatus.NOT_FOUND)
        else None,
        "failure": failure,
        "requests": requests,
    }


@pytest.mark.parametrize(("family", "cases"), list(families().items()), ids=list(families()))
def test_php_parity(family: str, cases: list[dict[str, Any]]) -> None:
    if shutil.which("php") is None or not (PHP_DIR / "vendor/autoload.php").exists():
        pytest.skip("PHP and the reference package vendor/autoload.php are required")
    payload = "".join(json.dumps(wire(case), ensure_ascii=True) + "\n" for case in cases)
    process = subprocess.run(
        ["php", str(Path(__file__).with_name("oracle.php"))],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "VAT_VALIDATOR_PHP_DIR": str(PHP_DIR)},
        timeout=120,
    )
    lines = process.stdout.splitlines()
    assert process.returncode == 0, (
        f"seed={SEED} family={family} input={cases[min(len(lines), len(cases) - 1)]!r}\n{process.stderr}"
    )
    assert len(lines) == len(cases), (process.stderr, len(lines), len(cases))
    for index, (case, line) in enumerate(zip(cases, lines, strict=True)):
        expected = json.loads(line)
        actual = python_projection(case)
        # json.loads may report syntax/encoding errors before our emulated checks.
        # Compare messages only when both decoders reached an emulated error.
        if expected.get("unavailable_reason") == actual.get("unavailable_reason") == "invalid_json" and not all(
            projection["failure"].get("message") in EMULATED_JSON_ERRORS for projection in (expected, actual)
        ):
            for projection in (expected, actual):
                projection["failure"].pop("message", None)
        assert actual == expected, (
            f"seed={SEED} family={family} case={index} input={case!r}\nPHP={expected!r}\nPython={actual!r}"
        )
