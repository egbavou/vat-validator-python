from collections.abc import Iterator

import pytest

pytest.importorskip("httpx")

from .support import Runner


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def runner(request: pytest.FixtureRequest) -> Iterator[Runner]:
    instance = Runner(asynchronous=bool(request.param))
    try:
        yield instance
    finally:
        instance.close()
