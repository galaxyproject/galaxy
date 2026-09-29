"""Pytest fixtures for the files unit test suite."""

import time
from collections.abc import Generator

import pytest

from galaxy.util.unittest_utils.mock_http_server import (
    MockHTTPRequestHandler,
    MockHttpServer,
    start_mock_http_server,
)


@pytest.fixture(scope="session")
def mock_http_server() -> Generator[MockHttpServer, None, None]:
    server, base_url = start_mock_http_server()
    try:
        yield MockHttpServer(base_url=base_url, handler_class=MockHTTPRequestHandler, is_remote=False)
    finally:
        server.shutdown()


@pytest.fixture
def non_utc_local_time(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    with monkeypatch.context() as patch:
        patch.setenv("TZ", "Asia/Tokyo")
        time.tzset()
        yield
    time.tzset()
