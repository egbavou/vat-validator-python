from typing import final

from ._enums import FailureReason


@final
class InvalidIdentifierError(ValueError):
    def __init__(self, reason: FailureReason) -> None:
        self._reason = reason
        super().__init__(f"Invalid VAT number: {reason.value}.")

    @property
    def reason(self) -> FailureReason:
        return self._reason

    def __reduce__(self) -> tuple[type["InvalidIdentifierError"], tuple[FailureReason]]:
        return type(self), (self.reason,)


@final
class ViesError(RuntimeError):
    def __reduce__(self) -> tuple[type["ViesError"], tuple[str]]:
        return type(self), (str(self),)
