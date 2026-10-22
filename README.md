# VAT number validator

Offline VAT number validation for Python 3.11+, with optional VIES existence checks,
Django integration and Pydantic v2 types. MIT licensed. The core has no dependencies.

```sh
pip install vat-number-validator
pip install "vat-number-validator[httpx]"
pip install "vat-number-validator[django,httpx]"
pip install "vat-number-validator[pydantic]"
```

## Offline validation

```python
# Offline example: runs without optional dependencies.
from vat_number_validator import FailureReason, InvalidIdentifierError, VatNumber

assert VatNumber.is_valid("fr 27 552 032 534")
assert VatNumber.try_parse("FR123") is None
vat = VatNumber("27552032534", country="FR")
assert VatNumber.from_siren("552 032 534") == vat
assert (vat.value, vat.prefix, vat.number, vat.country_code) == ("FR27552032534", "FR", "27552032534", "FR")
assert str(vat) == vat.format() == "FR27552032534"

try:
    VatNumber("FR28552032534")
except InvalidIdentifierError as error:
    assert error.reason is FailureReason.INVALID_CHECKSUM
    assert str(error) == "Invalid VAT number: invalid_checksum."
```

`VatNumber` is an immutable, hashable value object. The constructor raises
`InvalidIdentifierError` (a `ValueError`); `try_parse()` returns `None`, and
`is_valid()` returns `False` for invalid strings. Non-string inputs raise `TypeError`
on all three entry points. Checks run in order: characters, length, structure, checksum.

| Reason | Meaning |
|---|---|
| `invalid_characters` | Characters outside the national alphabet |
| `invalid_length` | Wrong national length or empty input |
| `invalid_structure` | Forbidden first digit, suffix, office code or number range |
| `invalid_checksum` | Wrong national check digits |
| `unknown_country_prefix` | Unsupported prefix or country parameter |
| `missing_country_prefix` | National input without a country parameter |
| `country_mismatch` | Input prefix and country parameter disagree |

Coverage includes all EU-27 countries and Northern Ireland (`XI`). Latvian personal
codes, Czech nine-digit VČP starting with `6`, and Bulgarian ten-digit natural-person
numbers use format-only validation. GB, Switzerland and Norway have offline
validation, including documented checksums, but no online existence source.
Passing offline validation does not establish VAT registration.

Normalization removes the 27 documented separators: Unicode category Z, ASCII
TAB through CR, U+0085, dots and hyphens. Only ASCII letters become uppercase;
Unicode lookalikes are rejected. Country parameters accept ISO codes or VAT prefixes
and trim only PHP's ASCII whitespace and NUL. Greek `GR` becomes `EL` (ISO country
`GR`); `XI` has ISO country `GB`. Swiss `CHE` has ISO country `CH`; optional `MWST`,
`TVA` and `IVA` suffixes are removed. Norwegian `MVA` is removed. Legacy nine-digit
Belgian numbers are padded with `0`; Greek eight-digit numbers are rejected.
French alphanumeric keys and Monaco numbers with a `000` SIREN prefix are supported.
`from_siren()` requires nine digits passing Luhn and rejects Monaco numbers. It also
accepts objects whose class defines `__str__`, such as a SIREN value object, while
numbers, booleans, `None`, bytes and bytearrays raise `TypeError`.

See [country algorithms and sources](docs/research/2026-10-22-country-rules.md) and
[changes since 2020](docs/research/2026-10-22-changes-since-2020.md). BMF primary rules
take precedence over conflicting libraries. Where secondary sources disagree
without a primary rule, validation uses the permissive choice and leaves registration
to VIES. The research snapshot of 22 October 2026 records Spain's ministry draft of
23 June 2026 proposing alphanumeric entity NIFs; the port implements the current
Spanish rules in that snapshot, not the proposal.

## VIES checks

Install the `httpx` extra. Synchronous and asynchronous checkers use the official
REST `POST /check-vat-number` endpoint, sending canonical prefix and national part
separately. Each check sends at most one request; there is no retry.

```python
from vat_number_validator import CheckStatus, VatNumberChecker

with VatNumberChecker(requester="BE0417497106") as checker:
    result = checker.check("FR27552032534")
    # Also accepts a VatNumber, or a national string with country="FR".
    if result.status is CheckStatus.FOUND:
        print(result.name, result.address, result.checked_at)
    elif result.status is CheckStatus.UNAVAILABLE:
        print(result.unavailable_reason, result.registry_error_code)
```

```python
import asyncio
from vat_number_validator import AsyncVatNumberChecker


async def main():
    async with AsyncVatNumberChecker() as checker:
        result = await checker.check("FR27552032534")
        print(result.status)


asyncio.run(main())
```

| `CheckStatus` | Meaning |
|---|---|
| `FOUND` | VIES confirms registration |
| `NOT_FOUND` | VIES explicitly reports an invalid registration |
| `INVALID_FORMAT` | Offline validation failed; no request |
| `UNAVAILABLE` | No source, registry error or technical failure |

Results expose `status`, `vat_number` (`None` for invalid format), `checked_at`,
`name`, `address`, `reference`, `unavailable_reason`, `registry_error_code` and
`failure`. `checked_at` is a timezone-aware UTC datetime: VIES's consultation time,
or current UTC time when no registry timestamp is available. Name/address lines
are trimmed, empty lines removed, and internal spaces preserved. `---`, empty
strings and `N/A` become `None`. `name`, `address` and `failure` are omitted from
`repr()`, but remain directly readable.

| `UnavailableReason` | Meaning / `failure` |
|---|---|
| `NO_SOURCE` | GB, CHE or NO; no request; `None` |
| `REGISTRY_ERROR` | Exact VIES code in `registry_error_code`; `None` |
| `TRANSPORT` | Original client or body-reading exception |
| `HTTP_STATUS` | Non-200 response; `ViesError` with HTTP status |
| `INVALID_JSON` | Original decoding exception |
| `SCHEMA` | Unexpected response shape; `ViesError` or original unexpected exception |

An error accompanying a false validity flag is `REGISTRY_ERROR`, not `NOT_FOUND`.
`failure` is `None` for other statuses. Package-authored diagnostics contain no
response body, VAT number, name or address. Transport exception messages come from
the HTTP client and can contain sensitive data; inspect your logging policy before
logging them. Checks return a result for ordinary failures; bad argument types,
`KeyboardInterrupt` and cancellation still propagate.

A valid EU/XI requester enables a consultation receipt in `reference`. Configure
**your company's VAT number**; invalid or non-VIES requesters are ignored. A receipt
proves the consultation, not the requester's identity. Without a retained requester,
references are hidden even if the response includes one. VIES has
[scheduled downtimes](docs/research/2026-10-22-country-rules.md#46-autres-points-utiles-à-limplémentation)
and member states may temporarily refuse checks.

The default timeout is **20 seconds per httpx operation**, not a total deadline.
Configure `timeout=2.5` when constructing a checker. Use `close()` / `aclose()` or
context managers for owned clients. An injected `httpx.Client` / `AsyncClient` remains
the caller's responsibility; configure its timeout there (client plus timeout is an
error). Injected default headers, cookies and query parameters are not applied to
the raw request. Redirects are never followed, even if the client enables them.

## Configuration

```python
from vat_number_validator import VatNumberChecker, ViesSettings

settings = ViesSettings.from_env()
with VatNumberChecker.from_settings(settings) as checker:
    result = checker.check("FR27552032534")
```

`ViesSettings` is a frozen keyword-only dataclass with `timeout=20.0` and
`requester=None`. `from_env()` reads `VAT_VALIDATOR_VIES_TIMEOUT` and
`VAT_VALIDATOR_REQUESTER`; it also accepts a mapping for explicit configuration.
Positive numeric timeouts are retained; invalid or non-positive values use 20 seconds.
Empty/non-string requesters become `None`; other strings are retained untrimmed
and checked by the checker. Environment parsing follows Laravel's reserved
`true`, `false`, `empty`, `null` values (including parentheses, case insensitive)
and surrounding single/double quotes. Plain checker constructors use their own
defaults; call `from_settings()` to use environment configuration.

## Django

Install `vat-number-validator[django]`, and add `"vat_number_validator.django"` to
`INSTALLED_APPS` for the French catalogue. Django 5.2, 6.0 and 6.1 are supported.
English source messages and lazy French translations follow the active language;
project catalogues in `LOCALE_PATHS` can override them. Without the app, source
messages stay in English. Existence validation also requires the `httpx` extra.

```python
from django import forms
from django.db import models
from vat_number_validator.django.forms import VatNumberField
from vat_number_validator.django.validators import (
    VatNumberExistsValidator,
    VatNumberValidator,
)


class Company(models.Model):
    vat_number = models.CharField(max_length=15, validators=[VatNumberValidator()])


class CompanyForm(forms.Form):
    vat_number = VatNumberField(country="FR", required=True)
    # Optional online validation:
    verified_number = VatNumberField(validators=[VatNumberExistsValidator(fail_when_unavailable=True)])
```

There is no custom model field. Validators are deconstructible for migrations.
`VatNumberValidator(country=None)` performs only offline validation. Both validators
accept a `VatNumber` unchanged. Non-string values, including `None`, fail direct
validation with `invalid_characters`; errors use the reason value as their Django
`ValidationError.code`. `VatNumberExistsValidator` checks format before resolving
the shared checker, fails with `not_found` for `NOT_FOUND`, and accepts `UNAVAILABLE`
by default. Set `fail_when_unavailable=True` to fail with `unavailable` instead.

`VatNumberField` returns a `VatNumber` in `cleaned_data`, or `None` for empty input.
Empty means `None` or a string empty after PHP's trim (including NUL); `required`
decides whether emptiness is accepted. It passes other strings directly to the core,
normalizes both sides in `has_changed()`, and displays objects using `format()`.
Override messages with `error_messages={"invalid_checksum": "Custom message"}`.
The value can be stored in a model `CharField` through its normalized `str()`.

`get_vat_number_checker()` in `vat_number_validator.django.checkers` returns a lazy
shared checker. The optional Django setting is:

```python
VAT_NUMBER_VALIDATOR = {
    "VIES": {"TIMEOUT": 20, "REQUESTER": "BE0417497106"},
    "CHECKER": None,  # Or a checker instance, e.g. using httpx.MockTransport.
}
```

Missing/`None` timeout and requester entries fall back to `ViesSettings.from_env()`;
present values use the same normalization rules. An injected `CHECKER` is used as
is and is never closed by the package. When `VAT_NUMBER_VALIDATOR` changes via
Django's `setting_changed` signal (including `override_settings`), the shared
checker is forgotten and an owned checker is closed first. This reset is meant for
tests using `override_settings`. Django does not support changing settings at
runtime; changing them while another thread checks a number closes the client
that thread is using.

For a country read from another form field, keep the number as a plain `CharField`:
a `VatNumberField` would validate national input before the country is available.

```python
from django import forms
from django.core.exceptions import ValidationError
from vat_number_validator import VatNumber
from vat_number_validator.django.validators import VatNumberValidator


class CompanyForm(forms.Form):
    vat_country = forms.CharField(required=False)
    vat_number = forms.CharField()

    def clean(self):
        data = super().clean()
        country = data.get("vat_country") or None
        try:
            VatNumberValidator(country=country)(data.get("vat_number"))
        except ValidationError as error:
            self.add_error("vat_number", error)
        else:
            data["vat_number"] = VatNumber(data["vat_number"], country=country)
        return data
```

Laravel parity applies to direct validator calls and the package form field.
Django model `CharField` converts values to strings before validators. An ordinary
`forms.CharField(strip=True)` strips Python whitespace, including U+001C–U+001F,
before validators. Empty values skip ordinary Django validators, like a Laravel
rule without `required`. Use the package field when these input semantics matter.

## Pydantic

Install `vat-number-validator[pydantic]` (Pydantic >=2.0.1, <3).

```python
from pydantic import BaseModel
from vat_number_validator import VatNumber
from vat_number_validator.pydantic import PydanticVatNumber


class Company(BaseModel):
    vat_number: PydanticVatNumber


company = Company.model_validate({"vat_number": "fr 27 552 032 534"})
assert isinstance(company.vat_number, VatNumber)
assert company.model_dump() == {"vat_number": "FR27552032534"}
assert company.model_dump_json() == '{"vat_number":"FR27552032534"}'
```

The alias returns a `VatNumber` and serializes as a normalized string in Python and
JSON modes. A `VatNumber` passes through unchanged; other non-string values fail,
also in strict mode. `PydanticVatNumber | None` accepts and serializes `None`.
Errors have types such as `vat_number_invalid_checksum`, with
`ctx={"reason": "invalid_checksum"}` and an English message. The validation schema
is a string with an example and no pattern (separators are accepted); serialization
uses the normalized string pattern. Use `isinstance(value, VatNumber)`:
`isinstance(value, PydanticVatNumber)` raises `TypeError` because it is an alias.

Pydantic performs no VIES work. Input must include its country prefix. If country
is separate, construct the value in a `model_validator`:

```python
from typing import Any
from pydantic import BaseModel, model_validator
from vat_number_validator import VatNumber
from vat_number_validator.pydantic import PydanticVatNumber


class Company(BaseModel):
    country: str
    vat_number: PydanticVatNumber

    @model_validator(mode="before")
    @classmethod
    def resolve_country(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("vat_number"), str) and isinstance(data.get("country"), str):
            data = {**data, "vat_number": VatNumber(data["vat_number"], country=data.get("country"))}
        return data
```

## Differences from the PHP package

Offline rules match `egbavou/vat-validator`; the differential suite compares parsing,
SIRENs, VIES outcomes, exact request bodies and Laravel environment normalization.
Python uses `TypeError` for wrong input types, ASCII-only case conversion, and a
lone surrogate to represent PHP's invalid UTF-8 test byte. httpx timeout semantics,
URL normalization, injected client defaults and User-Agent differ from Guzzle.
Result `repr()` omits identity fields and the failure; `failure` contains Python
exceptions. For `INVALID_JSON`, failure messages differ from PHP when the error
comes from `json.loads` (syntax, encoding, `NaN`). Emulated depth and lone-surrogate
errors keep PHP's messages in document order; a syntax error in the same body can
be reported first by Python. A VIES `requestDate` in year 0000 is `SCHEMA` in Python
because `datetime` cannot represent it; PHP accepts it.

A response interrupted while its body is read gives `TRANSPORT` whatever its HTTP
status: httpx reads the body inside `send()`, like Guzzle, the client wired by the
PHP Laravel provider. With a PSR-18 client that reads the body lazily, PHP would
give `HTTP_STATUS` for a non-200 response.

## Development and scope

```sh
uv sync --all-extras
uv run pytest
uv run pytest -m parity
uv run ruff check
uv run ruff format --check
uv run mypy
uv build
# Opt-in network tests; never run in CI:
VAT_NUMBER_VALIDATOR_LIVE=1 uv run pytest -m live
```

Default tests use recorded fixtures and fake transports and exclude `live` and
`parity`. Parity needs PHP on PATH and `../vat-validator/vendor/autoload.php`, or
`VAT_VALIDATOR_PHP_DIR`; it runs deterministic generated inputs with seed 20261022
and reports the seed and input on a mismatch. Live tests are skipped without the
explicit environment switch; they cover the official test service and real numbers.
CI tests Python 3.11–3.15, Django versions and lowest direct dependencies, builds a
wheel from the sdist, and verifies the installed French catalogue outside the repo.

This package provides no VAT rates, reverse-charge logic, SIRET validation or tax
calculations. See [LICENSE](LICENSE).
