from dataclasses import dataclass, field
from datetime import datetime
from typing import final

from ._enums import CheckStatus, UnavailableReason
from ._vat_number import VatNumber


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class VatNumberCheckResult:
    status: CheckStatus
    checked_at: datetime
    vat_number: VatNumber | None
    name: str | None = field(default=None, repr=False)
    address: str | None = field(default=None, repr=False)
    reference: str | None = None
    unavailable_reason: UnavailableReason | None = None
    registry_error_code: str | None = None
    failure: Exception | None = field(default=None, repr=False)
