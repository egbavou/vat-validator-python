"""Shared request construction and the PHP VatNumberChecker response pipeline."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ._cleanup import php_trim
from ._countries import for_prefix
from ._enums import CheckStatus, UnavailableReason
from ._errors import ViesError
from ._php_json import decode
from ._results import VatNumberCheckResult
from ._vat_number import VatNumber

if TYPE_CHECKING:
    import httpx

DEFAULT_ENDPOINT = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "egbavou/vat-number-validator (+https://github.com/egbavou/vat-validator-python)",
}
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")


def unavailable(
    vat_number: VatNumber,
    reason: UnavailableReason,
    *,
    registry_error_code: str | None = None,
    failure: Exception | None = None,
) -> VatNumberCheckResult:
    return VatNumberCheckResult(
        status=CheckStatus.UNAVAILABLE,
        checked_at=datetime.now(UTC),
        vat_number=vat_number,
        unavailable_reason=reason,
        registry_error_code=registry_error_code,
        failure=failure,
    )


def covered_by_vies(vat_number: VatNumber) -> bool:
    rule = for_prefix(vat_number.prefix)
    return rule is not None and rule.covered_by_vies()


def retain_requester(requester: str | None) -> VatNumber | None:
    if requester is not None and not isinstance(requester, str):
        raise TypeError("requester must be a str or None")
    candidate = None if requester is None else VatNumber.try_parse(requester)
    return candidate if candidate is not None and covered_by_vies(candidate) else None


def prepare_input(value: str | VatNumber, country: str | None) -> VatNumber | VatNumberCheckResult:
    if not isinstance(value, (str, VatNumber)):
        raise TypeError("vat_number must be a str or VatNumber")
    if country is not None and not isinstance(country, str):
        raise TypeError("country must be a str or None")
    number = value if isinstance(value, VatNumber) else VatNumber.try_parse(value, country=country)
    if number is None:
        return VatNumberCheckResult(status=CheckStatus.INVALID_FORMAT, checked_at=datetime.now(UTC), vat_number=None)
    if not covered_by_vies(number):
        return unavailable(number, UnavailableReason.NO_SOURCE)
    return number


def build_payload(vat_number: VatNumber, requester: VatNumber | None) -> bytes:
    # VatNumberChecker.php payload(): canonical prefix and national part only, in this order.
    payload = {"countryCode": vat_number.prefix, "vatNumber": vat_number.number}
    if requester is not None:
        payload["requesterMemberStateCode"] = requester.prefix
        payload["requesterNumber"] = requester.number
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def build_request(endpoint: str, body: bytes) -> httpx.Request:
    import httpx

    return httpx.Request("POST", endpoint, headers=_HEADERS, content=body)


def normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    # VatNumberChecker.php text(): PCRE \R/u, followed by PHP trim() on each line.
    lines = [php_trim(line) for line in re.split(r"\r\n|[\n\v\f\r\x85\u2028\u2029]", value)]
    text = "\n".join(line for line in lines if line != "")
    return None if text in ("---", "", "N/A") else text


def _request_date(value: object) -> datetime:
    if isinstance(value, str) and _TIMESTAMP.fullmatch(value):
        try:
            return datetime(
                int(value[0:4]),
                int(value[5:7]),
                int(value[8:10]),
                int(value[11:13]),
                int(value[14:16]),
                int(value[17:19]),
                int(value[20:23]) * 1000,
                tzinfo=UTC,
            )
        except ValueError:
            pass
    raise ViesError('VIES response has no valid "requestDate" timestamp.')


def interpret(
    status_code: int,
    content: bytes,
    vat_number: VatNumber,
    requester_retained: bool,
) -> VatNumberCheckResult:
    if status_code != 200:
        return unavailable(
            vat_number, UnavailableReason.HTTP_STATUS, failure=ViesError(f"VIES returned HTTP {status_code}.")
        )
    try:
        try:
            data = decode(content)
        except (ValueError, RecursionError) as failure:
            return unavailable(vat_number, UnavailableReason.INVALID_JSON, failure=failure)
        if not isinstance(data, (dict, list)):
            raise ViesError("VIES response is not a JSON object.")
        # PHP is_array() accepts JSON lists, which have none of the named fields.
        fields = data if isinstance(data, dict) else {}
        if "errorWrappers" in fields:
            wrappers = fields["errorWrappers"]
            first = wrappers[0] if isinstance(wrappers, list) and wrappers else None
            if isinstance(wrappers, dict):
                # PHP converts the canonical object key "0" to integer 0, but not "00".
                first = wrappers.get("0")
            code = first.get("error") if isinstance(first, dict) else None
            return unavailable(
                vat_number,
                UnavailableReason.REGISTRY_ERROR,
                registry_error_code=code if isinstance(code, str) else None,
            )
        if type(fields.get("valid")) is not bool:
            raise ViesError('VIES response has no boolean "valid" field.')
        for name in ("name", "address", "requestIdentifier", "countryCode", "vatNumber"):
            if name in fields and not isinstance(fields[name], str):
                raise ViesError(f'VIES response has no string "{name}" field.')
        checked_at = _request_date(fields.get("requestDate"))
        reference = fields.get("requestIdentifier")
        return VatNumberCheckResult(
            status=CheckStatus.FOUND if fields["valid"] else CheckStatus.NOT_FOUND,
            checked_at=checked_at,
            vat_number=vat_number,
            name=normalize_text(fields.get("name")),
            address=normalize_text(fields.get("address")),
            reference=reference if requester_retained and isinstance(reference, str) and reference != "" else None,
        )
    except Exception as failure:
        return unavailable(vat_number, UnavailableReason.SCHEMA, failure=failure)
