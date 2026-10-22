from enum import StrEnum
from typing import final


@final
class FailureReason(StrEnum):
    INVALID_CHARACTERS = "invalid_characters"
    INVALID_LENGTH = "invalid_length"
    INVALID_CHECKSUM = "invalid_checksum"
    INVALID_STRUCTURE = "invalid_structure"
    UNKNOWN_COUNTRY_PREFIX = "unknown_country_prefix"
    MISSING_COUNTRY_PREFIX = "missing_country_prefix"
    COUNTRY_MISMATCH = "country_mismatch"


@final
class CheckStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    INVALID_FORMAT = "invalid_format"
    UNAVAILABLE = "unavailable"


@final
class UnavailableReason(StrEnum):
    NO_SOURCE = "no_source"
    REGISTRY_ERROR = "registry_error"
    TRANSPORT = "transport"
    HTTP_STATUS = "http_status"
    INVALID_JSON = "invalid_json"
    SCHEMA = "schema"
