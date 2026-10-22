"""A form field that preserves the core's input semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, final

from django import forms
from django.core.exceptions import ValidationError

from .. import VatNumber
from .._cleanup import php_trim
from .validators import MESSAGES, _parse

if TYPE_CHECKING:
    from django.utils.functional import _StrPromise


@final
class VatNumberField(forms.Field):
    default_error_messages: ClassVar[dict[str, str | _StrPromise]] = dict(MESSAGES)

    def __init__(self, *, country: str | None = None, **kwargs: Any) -> None:
        self.country = country
        super().__init__(**kwargs)

    def to_python(self, value: object) -> VatNumber | None:
        if value is None or (isinstance(value, str) and php_trim(str.__str__(value)) == ""):
            return None
        try:
            return _parse(value, self.country)
        except ValidationError as error:
            code = error.code or "invalid_characters"
            raise ValidationError(self.error_messages[code], code=code) from error

    def has_changed(self, initial: object, data: object) -> bool:
        if self.disabled:
            return False
        try:
            return self.to_python(initial) != self.to_python(data)
        except ValidationError:
            return True

    def prepare_value(self, value: object) -> object:
        return value.format() if isinstance(value, VatNumber) else value
