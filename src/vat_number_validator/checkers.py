"""Optional httpx checkers; importing this module does not load httpx."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Self, final

from . import _vies
from ._enums import UnavailableReason
from ._results import VatNumberCheckResult
from ._settings import DEFAULT_TIMEOUT, ViesSettings
from ._vat_number import VatNumber
from ._vies import DEFAULT_ENDPOINT as DEFAULT_ENDPOINT

if TYPE_CHECKING:
    import httpx


def _validate_timeout(client: object, timeout: float | None) -> None:
    if client is not None and timeout is not None:
        raise ValueError("timeout cannot be supplied with an injected client")
    if timeout is not None and not timeout > 0:
        raise ValueError("timeout must be strictly positive")


@final
class VatNumberChecker:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        requester: str | None = None,
        timeout: float | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
    ) -> None:
        _validate_timeout(client, timeout)
        self._requester = _vies.retain_requester(requester)
        try:
            import httpx
        except ImportError as error:
            raise ImportError("Install vat-number-validator[httpx] to use VIES checkers.") from error
        self._owns_client = client is None
        self._client = (
            httpx.Client(timeout=DEFAULT_TIMEOUT if timeout is None else timeout) if client is None else client
        )
        self._endpoint = endpoint

    @classmethod
    def from_settings(cls, settings: ViesSettings, client: httpx.Client | None = None) -> Self:
        return cls(client, requester=settings.requester, timeout=settings.timeout if client is None else None)

    def check(self, vat_number: str | VatNumber, *, country: str | None = None) -> VatNumberCheckResult:
        number = _vies.prepare_input(vat_number, country)
        if isinstance(number, VatNumberCheckResult):
            return number
        try:
            request = _vies.build_request(self._endpoint, _vies.build_payload(number, self._requester))
            response = self._client.send(request, follow_redirects=False)
            status, content = response.status_code, response.content
        except Exception as failure:
            return _vies.unavailable(number, UnavailableReason.TRANSPORT, failure=failure)
        return _vies.interpret(status, content, number, self._requester is not None)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


@final
class AsyncVatNumberChecker:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        requester: str | None = None,
        timeout: float | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
    ) -> None:
        _validate_timeout(client, timeout)
        self._requester = _vies.retain_requester(requester)
        try:
            import httpx
        except ImportError as error:
            raise ImportError("Install vat-number-validator[httpx] to use VIES checkers.") from error
        self._owns_client = client is None
        self._client = (
            httpx.AsyncClient(timeout=DEFAULT_TIMEOUT if timeout is None else timeout) if client is None else client
        )
        self._endpoint = endpoint

    @classmethod
    def from_settings(cls, settings: ViesSettings, client: httpx.AsyncClient | None = None) -> Self:
        return cls(client, requester=settings.requester, timeout=settings.timeout if client is None else None)

    async def check(self, vat_number: str | VatNumber, *, country: str | None = None) -> VatNumberCheckResult:
        number = _vies.prepare_input(vat_number, country)
        if isinstance(number, VatNumberCheckResult):
            return number
        try:
            request = _vies.build_request(self._endpoint, _vies.build_payload(number, self._requester))
            response = await self._client.send(request, follow_redirects=False)
            status, content = response.status_code, response.content
        except Exception as failure:
            return _vies.unavailable(number, UnavailableReason.TRANSPORT, failure=failure)
        return _vies.interpret(status, content, number, self._requester is not None)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
