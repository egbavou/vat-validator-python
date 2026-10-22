# vat-number-validator (Python) Implementation Plan

> **For the executor (Codex CLI):** execute the tasks you are given, in order, with TDD: write the test, run it and see it fail, implement, run it and see it pass. **Never run `git add`, `git commit` or any git write command** — the owner reviews and commits himself. **Never run `uv sync`, `uv add`, `uv lock`, `pip install` or anything that needs the network** — the sandbox has none; the orchestrator installs dependencies after Task 1. Always run tools as `uv run --no-sync …`. Never call the real VIES service, except from tests marked `live`, which you never run. Code, comments, docstrings, test names, README and messages are in English; the only French text in the repository is `docs/` and the Django French catalogue. Do not modify `tests/fixtures/vies/` (byte-identical copies of the PHP fixtures) nor `docs/`.

**Goal:** Build `vat-number-validator`, a Python 3.11+ library that validates VAT numbers offline (EU-27 + XI with check digits, GB/CH/NO format only) and optionally checks their existence on the EU VIES REST API, with **exactly the same results** as the PHP package `egbavou/vat-validator`, plus optional httpx, Django and Pydantic integrations.

**Architecture:** A frozen slotted dataclass `VatNumber` whose constructor cleans the input, resolves the prefix (aliases, `country=`), and delegates the national part to one private rule class per prefix (`_countries/`), always checking characters → length → structure → checksum. `VatNumberChecker` / `AsyncVatNumberChecker` post to VIES through httpx and map every outcome to a frozen `VatNumberCheckResult` without ever raising; request building and response decoding live in `_vies.py`, shared by both, on top of `_php_json.py`, which reproduces `json_decode($body, true, 512, JSON_THROW_ON_ERROR)`. `vat_number_validator.django` and `vat_number_validator.pydantic` are optional and never imported by the core.

**Tech Stack:** Python 3.11–3.15, uv, hatchling ≥ 1.27, pytest, ruff, mypy `--strict`, httpx ≥ 0.27, Django 5.2/6.0/6.1, Pydantic ≥ 2.0.1, Babel (catalogue compilation), python-stdnum (dev-only oracle), PHP 8.5 + the local PHP package (differential test only), GitHub Actions.

**Sources of truth (read before coding):**
- `docs/plans/2026-10-22-design.md` — the validated design (French). Section numbers below (§…) refer to it.
- The PHP package in `../vat-validator/` (read-only for you): `src/` (**the code is the reference for every rule**), `tests/` (vectors and cases to port), `lang/{en,fr}/validation.php`, `config/vat-validator.php`, `docs/research/2026-10-22-country-rules.md`.
- `tests/fixtures/vies/` — the 66 raw VIES responses, already copied.
- Sibling Python ports for conventions and idioms: `../france-business-id-python/docs/plans/` and `../benin-business-id-python/docs/` (design documents only; their code may not exist yet).

**Conventions:**
- Public names exported from `vat_number_validator/__init__.py`: `VatNumber`, `FailureReason`, `InvalidIdentifierError`, `CheckStatus`, `UnavailableReason`, `VatNumberCheckResult`, `ViesError`, `ViesSettings`, `VatNumberChecker`, `AsyncVatNumberChecker`, `DEFAULT_ENDPOINT`, `DEFAULT_TIMEOUT`. `checkers.py` must not import httpx at module level (only under `TYPE_CHECKING` and lazily inside the constructor), so `import vat_number_validator` works without httpx.
- Private modules start with `_`. Classes are `@final` (from `typing`).
- Exception message: `Invalid VAT number: {reason value}.`
- Every port of a PHP construct carries a one-line comment naming the PHP source when the translation is not obvious (e.g. `# PHP trim(): only " \t\n\r\0\x0B"`).
- Never use `\d`, `\s`, `str.isdigit()`, `str.isspace()`, `str.strip()` without arguments, `str.upper()`, or `re.IGNORECASE` on user input: use explicit ASCII classes (§7.1).
- Async tests run inside `asyncio.run()`; no pytest plugin.
- Verification command after each task: `uv run --no-sync pytest && uv run --no-sync ruff check && uv run --no-sync ruff format --check && uv run --no-sync mypy`.

---

### Task 1: Scaffolding

**Files:** `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md` (one-line placeholder, written in Task 14), `src/vat_number_validator/__init__.py` (empty for now), `src/vat_number_validator/py.typed`, `tests/__init__.py` and one empty `__init__.py` in each test sub-directory (`core`, `httpx_integration`, `django_integration`, `pydantic_integration`, `live`, `parity`).

1. `pyproject.toml`:
   - `[build-system]`: `hatchling>=1.27`.
   - `[project]`: name `vat-number-validator`, version `0.1.0`, description "Offline VAT number validation (EU-27, XI, GB, CH, NO) with an optional VIES existence check, Django and Pydantic integrations.", `readme = "README.md"`, `license = "MIT"`, `license-files = ["LICENSE"]`, `requires-python = ">=3.11"`, `dependencies = []`, authors `Egbavou`, keywords (`vat`, `vat-number`, `vies`, `tva`, `eu`, `validation`, `django`, `pydantic`), classifiers (Python 3.11–3.15, Django 5.2/6.0/6.1, Pydantic 2, `Typing :: Typed`, natural languages English and French). No project URLs.
   - Extras: `httpx = ["httpx>=0.27"]`, `django = ["Django>=5.2"]`, `pydantic = ["pydantic>=2.0.1,<3"]`.
   - `[dependency-groups]`: `test = ["pytest>=8.3", "python-stdnum>=2.0", "babel>=2.16"]`, `typing = ["mypy>=1.13", "django-stubs>=5.1"]`, `lint = ["ruff>=0.8"]`; `[tool.uv] default-groups = ["test", "typing", "lint"]`.
   - Hatch: wheel `packages = ["src/vat_number_validator"]`; sdist excludes `/docs` and `/.github` (and nothing that would drop `*.mo` or `tests/fixtures`).
   - pytest: `testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "--import-mode=importlib --strict-markers --strict-config -ra -m 'not live and not parity'"`, `markers = ["live: calls the real VIES service (needs VAT_NUMBER_VALIDATOR_LIVE=1)", "parity: differential test against the local PHP package"]`, `xfail_strict = true`, `filterwarnings = ["error"]`.
   - mypy: `strict = true`, `files = ["src", "tests"]`, `python_version = "3.11"`; `plugins = ["mypy_django_plugin.main"]` with `[tool.django-stubs] django_settings_module = "tests.django_integration.settings"` (that module is created in Task 12; until then, leave the plugin out and add it in Task 12).
   - ruff: `target-version = "py311"`, `line-length = 120`, lint `select = ["E", "W", "F", "I", "N", "UP", "B", "A", "C4", "SIM", "PT", "RUF", "RET"]`, formatter on.
2. `.gitignore`: `__pycache__/`, `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`, `/uv.lock`. **Never** ignore `*.mo`.
3. `LICENSE`: the MIT text of `../vat-validator/LICENSE`.
4. `tests/conftest.py`: empty for now.

**Stop after this task.** The orchestrator runs `uv sync --all-extras` and `git init`.

### Task 2: Enums and errors

**Files:** `src/vat_number_validator/_enums.py`, `_errors.py`; `tests/core/test_types.py` (port of `TypesTest.php`).

Tests first:
- `FailureReason`, `CheckStatus`, `UnavailableReason` are `StrEnum`s with UPPER_CASE members and exactly the PHP values **in the PHP order** (§6.1);
- `InvalidIdentifierError(FailureReason.INVALID_STRUCTURE)`: is a `ValueError`; message `Invalid VAT number: invalid_structure.`; `.reason` is the member; assigning `.reason` raises `AttributeError`; `pickle` round trip keeps class, reason and message;
- `ViesError("VIES returned HTTP 503.")`: is a `RuntimeError`; `pickle` round trip keeps class and message.

Implementation: `@final` classes; `reason` property backed by `_reason`; `__reduce__` on both.

### Task 3: Cleanup helpers and checksums

**Files:** `_cleanup.py`, `_checksum.py`; `tests/core/test_cleanup.py`, `tests/core/test_checksum.py` (port of `ChecksumTest.php`).

`_cleanup.py`:
- `SEPARATORS: frozenset[str]`: the 27 code points of §7.1, hard-coded; `remove_separators(text) -> str`;
- `ascii_upper(text) -> str`: maps only `a`–`z` (use `str.translate` with a precomputed table);
- `php_trim(text) -> str`: strips only `" \t\n\r\0\x0b"` at both ends.

`_checksum.py`: `luhn`, `iso7064_mod11_10`, `iso7064_mod97_10` (digit by digit, `+`=36, `*`=37, `A`=10…`Z`=35, result must be 1), `weighted_sum(digits, weights)`, `digit_sum(digits)` — line-by-line ports of `../vat-validator/src/Internal/Checksum.php`.

Tests: every `ChecksumTest.php` row; `SEPARATORS` has 27 members and equals the §7.1 list; `ascii_upper("ßıſﬀabc")` is `"ßıſﬀABC"`; `php_trim` keeps U+00A0 and U+001C, removes NUL and `\x0b`.

### Task 4: Shared test vectors

**File:** `tests/cases.py`.

Port verbatim, keyed by the PHP dataset names:
- `VALID_NUMBERS` (142 rows: input, normalized value), `INVALID_NUMBERS` (107 rows: input, `FailureReason`), `PARSING` (16 rows: input, country, expected value or `FailureReason`) from `../vat-validator/tests/Support/VatCases.php`. The PHP row `"FR27\xff552032534"` becomes `"FR27\udcff552032534"`; `"FR27\u{180E}552032534"` and the other `\u{…}` escapes become Python `\u…` escapes.
- `FAMILIES` (31 rows) and `SE_SUFFIXES` from `CountryFamiliesTest.php`; `UK_VALID`, `UK_CHECKSUM`, `UK_STRUCTURE` national parts from the same file;
- `SIREN_CASES` from `VatNumberTest.php` (the Stringable row becomes an object whose class defines `__str__`);
- `ROUND_TRIPS = ["FRFR552032799", "NLNL0000000B27", "FRSE552032799", "NLBE0000000B48"]`.

Add a test `tests/core/test_cases.py` asserting the row counts (142, 107, 16, 31) so an accidental deletion fails.

### Task 5: Parsing core, registry, FR/BE/CH/NO, `from_siren`

**Files:** `_countries/__init__.py` (registry: `for_prefix`, `prefix_for_country`, `detect_prefix`, `prefixes` — port of `CountryRules.php`, same prefix order), `_countries/_base.py` (port of `CountryRule.php` + `AbstractCountryRule.php`), `_countries/france.py`, `belgium.py`, `switzerland.py`, `norway.py`, `_vat_number.py`; `tests/core/test_vat_number.py` (port of `VatNumberTest.php`).

Port `../vat-validator/src/VatNumber.php` line by line (§6.3, §7.1, §7.2, §7.4):
- `VatNumber.__init__(self, value: str, *, country: str | None = None)`; `try_parse`, `is_valid` (classmethods, same keyword); `from_siren` (classmethod; accepted types per §14.3); `format()`, `__str__`, `__repr__` (`VatNumber('FR27552032534')`), `__eq__`/`__hash__` on `value`;
- `@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)` with `value` as the only init field and `prefix`, `number`, `country_code` as `field(init=False)`; set them with `object.__setattr__`; `dataclasses.replace(vat, value=…)` must re-parse;
- types: `TypeError` when `value` is not a `str` or `country` is neither `str` nor `None` (also in `try_parse`/`is_valid`); normalise `str` subclasses with `str.__str__(value)` first;
- the three branches of `split()` exactly as in PHP, including the alphanumeric-key fallbacks;
- `country`: ignored when `None` or `php_trim(country) == ""`; otherwise `ascii_upper(php_trim(country))` then `prefix_for_country`.

Tests (port + Python-specific):
- every `PARSING` row: value, `format()`, `str()`, or reason and exact message;
- Swiss prefix vs ISO country; Greek aliases (`GR`→`EL`, `country="GR"`, `country="EL"`); XI → `GB`;
- `from_siren`: every `SIREN_CASES` row; `int`, `float`, `bool`, `None`, `bytes`, `bytearray` raise `TypeError`;
- round trips: `VatNumber(full) == VatNumber(vat.number, country=vat.country_code) == VatNumber(full, country=vat.country_code)`;
- `TypeError` for `int`, `bytes`, `None`, `list` on the three entry points and for a non-`str` `country`;
- `str` subclass overriding `__str__`, `upper`, `translate`: same result, fields are exact `str`;
- frozen (`FrozenInstanceError`), `replace()` (valid re-parses, invalid raises), equality, hash, `repr`, `pickle`, `copy`;
- ASCII upper: `"FR27552032534ß"`, `"ıT00905811006"`, `"ſE556012579001"`, `"ﬀ…"` give `INVALID_CHARACTERS`; lowercase ASCII passes;
- country trim: `" fr "` passes; `" FR"` gives `UNKNOWN_COUNTRY_PREFIX`; `" "` is ignored;
- exhaustive separator test (§13.1): for every code point from U+0000 to U+10FFFF, `VatNumber.is_valid("FR27" + chr(cp) + "552032534")` is true iff `chr(cp)` is in `SEPARATORS` (surrogates included; keep it under ~20 s).

Only the FR, BE, CHE and NO rules exist after this task, and the registry lists only them; Task 6 completes it to the full PHP list, in the PHP order. Tests that need a country added in Task 6 (e.g. the Greek aliases, XI, `NLNL0000000B27`) are written in Task 6.

### Task 6: All remaining countries

**Files:** one module per remaining PHP class in `../vat-validator/src/Internal/Countries/` (`austria.py`, `bulgaria.py`, `croatia.py`, `cyprus.py`, `czechia.py`, `denmark.py`, `estonia.py`, `finland.py`, `germany.py`, `greece.py`, `hungary.py`, `ireland.py`, `italy.py`, `latvia.py`, `lithuania.py`, `luxembourg.py`, `malta.py`, `netherlands.py`, `poland.py`, `portugal.py`, `romania.py`, `slovakia.py`, `slovenia.py`, `spain.py`, `sweden.py`, `united_kingdom.py` with `UnitedKingdom` (GB, not VIES) and `NorthernIreland` (XI) sharing a base); `tests/core/test_countries.py` (port of `CountriesTest.php`), `tests/core/test_country_families.py` (port of `CountryFamiliesTest.php`).

Port each class **line by line** (§7.3). Keep the PHP docblock source notes as comments. Watch the translation traps of §7.3 (`(int) substr`, `checkdate`, `str_pad`, `ord`/`chr`, anchored ASCII regexes).

Tests:
- every `VALID_NUMBERS` row: `is_valid` and normalized value; every `INVALID_NUMBERS` row: `is_valid` false, `try_parse` `None`, exact reason;
- at least two valid and two invalid vectors for every registered prefix;
- every `FAMILIES` row; SE suffix boundaries; GB and XI MOD97/MOD9755/GD/HA/branch families (valid, checksum and structure lists).

### Task 7: Cross-check against python-stdnum

**File:** `tests/core/test_cross_check.py` (replaces `CrossCheckTest.php`).

- Oracle: `stdnum.eu.vat.is_valid` for EU/XI prefixes, `stdnum.gb.vat` for GB, `stdnum.ch.uid` (after removing `MWST`/`TVA`/`IVA`) for CHE, `stdnum.no.orgnr` (after removing `MVA`) for NO, applied to the input with spaces, dots and hyphens removed and uppercased.
- `DOCUMENTED_DIVERGENCES`: exactly these 19 inputs, each with a one-line source-backed reason taken from the design (§13.1), the PHP `CrossCheckTest.php` reasons and the research document: `LV33123456789`, `LV38000000000`, `LV39999999999`, `CZ699004743`, `BG7501011233`, `BG1234567890`, `CY12000000F`, `CZ90177045`, `NLABCDEFGHIJ27`, `NL+*0000000B43`, `SE556012579002`, `EE200070005`, `EL09401924`, `XI010000090`, `XI950000087`, `XI220430231000`, `GB100000047`, `GB010000090`, `GB950000087`.
- For every vector in `VALID_NUMBERS` and `INVALID_NUMBERS`: ours must equal stdnum's verdict, except for the listed divergences, where it must differ.
- Every listed divergence must appear among the vectors.
- `pytest.importorskip("stdnum")` at module level.

### Task 8: `json_decode` equivalent

**Files:** `_php_json.py`; `tests/core/test_php_json.py`.

Implement `decode(body: bytes) -> object` exactly as §9.4 (assoc mode):
- strict UTF-8 decode; `json.loads` with `object_pairs_hook` keeping all pairs (internal marker type), `parse_constant` raising, `parse_int` as specified;
- iterative walk over the whole tree including overwritten duplicates: depth > 511 raises `ValueError("Maximum stack depth exceeded")`; a lone surrogate in any string or key raises `ValueError("Single unpaired UTF-16 surrogate in unicode escape")`; NaN/Infinity raise `ValueError("Syntax error")`;
- convert pairs to `dict` (last key wins); JSON arrays stay `list`;
- keys starting with `\u0000` are **accepted** (assoc mode);
- the function raises (`UnicodeDecodeError`, `json.JSONDecodeError`, `RecursionError`, `ValueError`); the caller maps any of them to `INVALID_JSON`.

Tests, one row per rule of the §9.4 table: non-UTF-8 bytes, BOM, `NaN`, 511 vs 512 nested arrays (also nested inside an object, with the object counting as one level), lone `\ud800` including in a value overwritten by a duplicate key, NUL-prefixed key accepted, duplicate keys (last wins), big integers, empty body, HTML body (`tests/fixtures/vies/http404-not-found.html`).

### Task 9: Settings

**Files:** `_settings.py`; `tests/core/test_settings.py` (port of the normalization rows of `ServiceProviderTest.php`).

- `DEFAULT_TIMEOUT = 20.0`; `ViesSettings` frozen slotted kw-only dataclass (`timeout: float = 20.0`, `requester: str | None = None`); `ViesSettings.from_env(environ: Mapping[str, str] | None = None)` (§8).
- Private helpers reused by Django: `_laravel_env(environ, name, default)`, `normalize_timeout(value: object) -> float`, `normalize_requester(value: object) -> str | None`, `_php_is_numeric(value: object) -> bool` (regex of §8; `bool` is not numeric; `int`/`float` are, `nan` then fails `> 0`).
- Tests: timeout rows `[3, 3.0], [2.5, 2.5], ["2.5", 2.5], [0, 20.0], [-1, 20.0], ["0", 20.0], ["garbage", 20.0], [None, 20.0], [False, 20.0]` plus `" 2.5 "`, `"1e3"`, `"1_0"`, `"inf"`, `"nan"`, `"0x1A"`; requester rows `["BE0417497106", kept], ["", None], [None, None], [123, None], ["  ", None], [" BE0417497106 ", kept untrimmed]`; `from_env` with absent variables, `true`, `(false)`, `empty`, `(null)`, quoted `"…"` and `'…'`, multi-line quoted value keeps its quotes, mixed case `TRUE`.

### Task 10: VIES request, decoding, results and checkers

**Files:** `_results.py`, `_vies.py`, `checkers.py`; `tests/httpx_integration/conftest.py` (`pytest.importorskip("httpx")`), `tests/httpx_integration/support.py` (fixture loader returning raw bytes; queue-based `httpx.MockTransport` recording requests, raising queued exceptions — the equivalent of `FakeHttpClient.php`), `test_checker.py` (sync), `test_async_checker.py` (async, same cases through a shared parametrisation), `test_requests.py`.

Implement §6.4, §6.5, §9.2, §9.3, §9.5 by porting `../vat-validator/src/VatNumberChecker.php`:
- `_vies.py`: `build_payload(vat_number, requester) -> bytes`, `build_request(endpoint, body) -> httpx.Request` (headers `Content-Type`, `Accept`, `User-Agent: egbavou/vat-number-validator (+https://github.com/egbavou/vat-validator-python)`), `interpret(status_code, content, vat_number, requester_retained) -> VatNumberCheckResult` (all decoding of §9.4/§9.5, wrapped so that any unexpected `Exception` gives `SCHEMA` with that exception), `normalize_text`. Neither sync nor async logic lives elsewhere: the checkers only send.
- `checkers.py`: constructor rules of §6.5 (lazy httpx import with an `ImportError` naming `vat-number-validator[httpx]`; `ValueError` for client + timeout and for a non-positive timeout; requester retained only if valid and covered by VIES), `from_settings`, `check` (never raises except `TypeError` and non-`Exception` `BaseException`s), `close`/`__enter__`/`__exit__`, `aclose`/`__aenter__`/`__aexit__`; send with `client.send(request, follow_redirects=False)` inside a `try` covering request construction, sending and body reading.
- `VatNumberCheckResult`: frozen slotted kw-only dataclass; `name`, `address`, `failure` with `field(repr=False)`.

Tests — port **every** case of `CheckerTest.php`, in sync and async:
- valid Belgian response (all fields, `checked_at` `2026-10-22T01:00:38.289000+00:00` in UTC, one request);
- every `post-valid-*.json` decodes to `FOUND` with `checked_at` equal to its `requestDate`;
- absent identity markers and invalid registry responses (DE placeholder, FR invalid, ES placeholder);
- consultation reference with a requester;
- every `post-error-*.json` and `post-test-service-error-*.json` → `REGISTRY_ERROR` with the exact code, `failure` `None`, one request;
- registry errors take precedence over `valid: false`;
- the GET trap fixtures (`get-error-*.json`) → `SCHEMA` with `VIES response has no boolean "valid" field.`;
- every `post-http*.json` and `http*.html` with the status in its file name → `HTTP_STATUS`, `ViesError("VIES returned HTTP {status}.")`, no registry code;
- HTML served in 200 → `INVALID_JSON`;
- the six unexpected-schema bodies with their exact messages;
- transport exceptions (an `httpx.ConnectTimeout`, a plain `RuntimeError`) kept as is in `failure`, `checked_at` between before/after, one request; an exception message containing personal data is kept unchanged (it is the client's);
- body read failure: a response whose stream raises while `send()` reads it (`RuntimeError`, `json.JSONDecodeError`-like `ValueError`) → `TRANSPORT` with that exception;
- GB, CHE and NO → `NO_SOURCE`, no request, `vat_number` set; invalid format → `INVALID_FORMAT`, no request;
- value object or national number with `country`; `country` ignored for a `VatNumber`;
- canonical prefixes and national number only (`GR094014201` → `EL`/`094014201`; `XI220430231`), method `POST`, URL `DEFAULT_ENDPOINT`, headers;
- requester rows `BE0417497106` (sent), `FR123`, `GB220430231`, `CHE116281710`, `None` (not sent); reference hidden without a retained requester (`None`, `""`, `FR123`, `GB220430231`, `CHE116281710`, `NO974760673`);
- text normalization rows (`"  \nFOO  BAR \n\nLINE 2\n"` → `"FOO  BAR\nLINE 2"`, `---`, `""`, `N/A` → `None`) plus `\R` separators (`\x0b`, `\x0c`, `\x85`, ` `, ` `, `\r\n`, `\r`), `"\0 ---\t"` → `None`, U+00A0 kept;
- malformed timestamps (`"…Z\0"`, `2026-02-31`, hour 25, second 60) → `SCHEMA`; year `0000` → `SCHEMA` (documented divergence, §12.2);
- every field × type (object, array, integer, boolean, null) × `valid` true/false → `SCHEMA` with `VIES response has no string "{field}" field.`;
- §9.5 PHP-verified rows: JSON list `[]` and `[true]` → no boolean valid; NUL key accepted; `errorWrappers` `null`, `[]`, `[{"error": 5}]`, `[["X"]]` → code `None`; `{"0": {"error": "X"}}` → `X`; `{"00": …}` → `None`;
- unexpected exception while interpreting a 200 (monkeypatch `_vies` decoding to raise) → `SCHEMA` with that exception;
- `test_requests.py`: exact body bytes `{"countryCode":"EL","vatNumber":"094014201","requesterMemberStateCode":"BE","requesterNumber":"0417497106"}`; exact header set on the wire (`Host`, `Content-Length`, `Content-Type`, `Accept`, `User-Agent` only) even with an injected client that has default headers, params and cookies; a 301 is not followed even with `follow_redirects=True` on the client;
- constructor: `ValueError` for client + timeout, for `0`, `-1`, `nan`; `TypeError` for a non-`str` requester; own client closed by `close()`/`aclose()` and context managers, injected client never closed; `from_settings`;
- `check()` raises `TypeError` for an `int` input or an `int` country; `KeyboardInterrupt` and `asyncio.CancelledError` raised by the transport propagate;
- `repr()` of a result contains neither the name nor the address.

### Task 11: Pydantic integration

**Files:** `pydantic.py`; `tests/pydantic_integration/conftest.py` (`pytest.importorskip("pydantic")`), `test_pydantic.py`.

Implement §10 and §14.6–14.7, mirroring the France design §7: `PydanticVatNumber = Annotated[VatNumber, PlainValidator(...), PlainSerializer(str, return_type=str), WithJsonSchema(...)]` with distinct validation and serialization schemas; `PydanticCustomError(f"vat_number_{reason}", message, {"reason": reason})`; non-`str` non-`VatNumber` inputs → `vat_number_invalid_characters`.

Tests: valid values (attribute is a `VatNumber`, dump in Python and JSON modes), every reason (type, ctx, message), non-strings, object passthrough, strict mode, `PydanticVatNumber | None` (validation, serialization, both schemas), JSON schemas, no network access (no httpx import triggered).

### Task 12: Django integration

**Files:** `django/__init__.py`, `apps.py` (`VatNumberValidatorConfig`, label `vat_number_validator`), `validators.py`, `forms.py`, `checkers.py`, `locale/fr/LC_MESSAGES/django.po` and the compiled `django.mo`; `tests/django_integration/settings.py` (`INSTALLED_APPS = ["django.contrib.contenttypes", "vat_number_validator.django"]`, `USE_I18N = True`, `LANGUAGE_CODE = "en"`, `SECRET_KEY` for tests), `tests/django_integration/conftest.py` (`pytest.importorskip("django")`; `DJANGO_SETTINGS_MODULE` set to that module; `django.setup()`), `test_validators.py`, `test_forms.py`, `test_checkers.py`, `test_catalogue.py`, `test_recipe.py`.

Implement §11 and §14.8–14.9, mirroring the France and Benin designs (§6 and §11 respectively):
- messages of §11.6 with `gettext_lazy`, codes = reason values, `not_found`, `unavailable`;
- `VatNumberValidator(country=None)`, `VatNumberExistsValidator(country=None, fail_when_unavailable=False)`: `@deconstructible`, explicit `__eq__`; the existence validator resolves the checker only after the format passed;
- `VatNumberField(country=None, **kwargs)`: `to_python`, PHP-`trim` emptiness, `has_changed`, `prepare_value`, `error_messages` overrides;
- `get_vat_number_checker()` and the `VAT_NUMBER_VALIDATOR` setting (§11.5), reset on `setting_changed`, closing only a checker it created;
- `.po` written by hand; compile with `uv run --no-sync pybabel compile -D django -d src/vat_number_validator/django/locale` (Babel is in the `test` group).

Tests — port every case of `tests/Laravel/RulesTest.php` and the checker-related cases of `ServiceProviderTest.php`:
- every reason, for both validators and the field, in English and French (`translation.override`);
- non-string values (`123`, `True`, `None`, `[]`, `object()`) → `invalid_characters` in both languages;
- empty values left to `required` (field); `" \t"` and `"\0"` empty, U+00A0 alone not empty (→ `invalid_length`);
- fixed country rows (`country="FR"` with national input; prefixed input with and without country);
- format validation never resolves the checker (setting `CHECKER` to an object that raises when used);
- existence outcomes with an `httpx.MockTransport` checker set through `override_settings(VAT_NUMBER_VALIDATOR={"CHECKER": …})`: found (default and strict) passes, not found fails with `not_found`, `MS_MAX_CONCURRENT_REQ` passes by default and fails with `unavailable` when strict; one request each;
- shared checker: settings and environment fallbacks, normalization rows of Task 9, singleton identity, reset and closing on `override_settings`;
- `deconstruct()` round trip and equality rules;
- catalogue: the `.mo` matches the `.po` (compile to a temporary directory with Babel and compare messages), every code has a French message, language switch after import;
- the §11.4 recipe as a test form: `vat_country="FR"` + national number → `cleaned_data["vat_number"] == VatNumber("FR27552032534")`; empty country → requires a prefix; mismatch → `country_mismatch` on the number field.

### Task 13: Architecture, live and parity tests

**Files:** `tests/core/test_architecture.py`, `tests/live/test_vies.py`, `tests/parity/oracle.php`, `tests/parity/test_parity.py`, `tests/parity/generators.py`.

Architecture (§13.1): in a subprocess, `import vat_number_validator` loads neither `httpx`, `django` nor `pydantic`; static check (AST) that no module outside `pydantic.py` and `django/` imports `django`/`pydantic`, and that `httpx` is imported only under `TYPE_CHECKING` or inside function bodies of `checkers.py`/`_vies.py`.

Live (§13.3): module skipped unless `os.environ.get("VAT_NUMBER_VALIDATOR_LIVE") == "1"`, every test marked `live`, sync and async:
- test service `https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-test-service` through `_vies` with a forced national number and a VIES prefix (e.g. `BE`): `100` → `FOUND`, `200` → `NOT_FOUND`, `600` → `REGISTRY_ERROR` `MS_MAX_CONCURRENT_REQ`;
- `FR27552032534` → `FOUND`; `FR44732829320` → `NOT_FOUND`; on `UNAVAILABLE` + `REGISTRY_ERROR`, `pytest.skip(f"VIES transient error: {code}")`.

Parity (§13.2): skipped unless `php` is on `PATH` and `$VAT_VALIDATOR_PHP_DIR/vendor/autoload.php` exists (default `../vat-validator`); marked `parity`.
- `oracle.php`: reads one JSON request per line on stdin, writes one JSON result per line. Operations `parse`, `from_siren`, `check`, `settings` (§13.2). Strings travel as base64 of their bytes (Python side: `.encode("utf-8", "surrogateescape")`, so a lone `\udcff` becomes the invalid byte `0xFF` in PHP). `check` uses an in-oracle PSR-18 fake client returning the given status and base64 body, or throwing an injected `RuntimeException("injected")`, and reports the request (method, URI, body, `Content-Type`, `Accept`). `settings` sets the variables in `$_SERVER`/`$_ENV` (clearing previous ones), evaluates `../vat-validator/config/vat-validator.php` (which calls `Illuminate\Support\Env`), then applies the two normalization expressions copied verbatim from `VatValidatorServiceProvider::register()`, with a comment pointing to it.
- `generators.py`: seeded generators (seed printed on failure) producing several thousand cases per family as listed in §13.2, excluding the §12.2 cases (requestDate year `0000`).
- `test_parity.py`: one PHP process per family, compares the canonical projection of §13.2 and reports the first mismatches with the seed and the input in `repr`.

### Task 14: README, CI and full verification

**Files:** `README.md`, `.github/workflows/ci.yml`.

README (English), modelled on `../vat-validator/README.md` and adapted to Python: installation with extras; offline validation (fields, reasons table, coverage, normalization rules, sources, Spain note); VIES checks (statuses, unavailability reasons, `failure` rules and the transport-message caveat, requester and its meaning, 20 s timeout per httpx operation, no retry, scheduled downtimes, sync and async examples, closing); configuration (`ViesSettings.from_env`, the two variables); Django (app, validators, field, existence validator, shared checker and setting, the §11.4 recipe, parity limits of §11.7); Pydantic (alias, errors, no country, `isinstance` caveat, no network); differences from the PHP package (§12, short); development commands (`uv run pytest`, `-m parity`, `VAT_NUMBER_VALIDATOR_LIVE=1 uv run pytest -m live`, ruff, mypy, build). Links to `docs/research/` must resolve.

CI (§13.4): jobs `core`, `httpx`, `django`, `pydantic`, `quality`, `lowest` exactly as in the design table, each using `astral-sh/setup-uv`, printing `uv pip list`, setting `VAT_NUMBER_VALIDATOR_LIVE=0`, never running `parity` or `live`. The `quality` job builds the sdist, then the wheel from the sdist, checks that the wheel contains `py.typed`, `django.po` and `django.mo`, installs it in a fresh environment outside the repository and imports the package and the French catalogue.

Final verification (all must pass): `uv run --no-sync pytest`, `uv run --no-sync pytest -m parity` (if PHP is available in your sandbox; otherwise say so), `uv run --no-sync ruff check`, `uv run --no-sync ruff format --check`, `uv run --no-sync mypy`, `uv build --offline` (if it needs the network, say so instead of retrying).
