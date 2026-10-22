"""Lazily create and renew the shared synchronous VIES checker."""

from threading import RLock
from typing import Any, cast

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from .. import VatNumberChecker, ViesSettings
from .._settings import normalize_requester, normalize_timeout

_checker: VatNumberChecker | None = None
_owned = False
_lock = RLock()


def get_vat_number_checker() -> VatNumberChecker:
    global _checker, _owned
    with _lock:
        if _checker is None:
            config = getattr(settings, "VAT_NUMBER_VALIDATOR", None) or {}
            injected = config.get("CHECKER")
            if injected is not None:
                _checker = cast(VatNumberChecker, injected)
                _owned = False
            else:
                defaults = ViesSettings.from_env()
                vies = config.get("VIES") or {}
                timeout = vies.get("TIMEOUT")
                requester = vies.get("REQUESTER")
                resolved = ViesSettings(
                    timeout=defaults.timeout if timeout is None else normalize_timeout(timeout),
                    requester=defaults.requester if requester is None else normalize_requester(requester),
                )
                _checker = VatNumberChecker.from_settings(resolved)
                _owned = True
        return _checker


@receiver(setting_changed)
def _reset_checker(*, setting: str, **kwargs: Any) -> None:
    global _checker, _owned
    if setting == "VAT_NUMBER_VALIDATOR":
        with _lock:
            previous, owned = _checker, _owned
            _checker, _owned = None, False
            if previous is not None and owned:
                previous.close()
