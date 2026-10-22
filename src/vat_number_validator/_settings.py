"""Laravel environment parsing and service-provider configuration normalization."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self, final

from ._cleanup import ascii_upper, php_trim

DEFAULT_TIMEOUT = 20.0
_NUMERIC = re.compile(r"[ \t\n\r\v\f]*[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[ \t\n\r\v\f]*")


def _laravel_env(environ: Mapping[str, str], name: str, default: object) -> object:
    if name not in environ:
        return default
    value = environ[name]
    # Illuminate Support Env::getOption(): reserved words precede quote removal.
    reserved = {
        "TRUE": True,
        "(TRUE)": True,
        "FALSE": False,
        "(FALSE)": False,
        "EMPTY": "",
        "(EMPTY)": "",
        "NULL": None,
        "(NULL)": None,
    }
    upper = ascii_upper(value)
    if upper in reserved:
        return reserved[upper]
    match = re.fullmatch(r"(['\"])(.*)\1", value)
    return match[2] if match else value


def _php_is_numeric(value: object) -> bool:
    # VatValidatorServiceProvider.php uses PHP is_numeric(), which excludes booleans.
    return (isinstance(value, (int, float)) and not isinstance(value, bool)) or (
        isinstance(value, str) and _NUMERIC.fullmatch(value) is not None
    )


def normalize_timeout(value: object) -> float:
    if _php_is_numeric(value) and isinstance(value, (str, int, float)):
        timeout = float(value)
        if timeout > 0:
            return timeout
    return DEFAULT_TIMEOUT


def normalize_requester(value: object) -> str | None:
    # VatValidatorServiceProvider.php keeps nonempty strings without trimming them.
    return value if isinstance(value, str) and php_trim(value) != "" else None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ViesSettings:
    timeout: float = DEFAULT_TIMEOUT
    requester: str | None = None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Self:
        source = os.environ if environ is None else environ
        return cls(
            timeout=normalize_timeout(_laravel_env(source, "VAT_VALIDATOR_VIES_TIMEOUT", DEFAULT_TIMEOUT)),
            requester=normalize_requester(_laravel_env(source, "VAT_VALIDATOR_REQUESTER", None)),
        )
