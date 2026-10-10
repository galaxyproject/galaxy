"""Pytest fixtures for the files unit test suite."""

import ipaddress
import socket
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


@pytest.fixture
def fake_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve hostnames to a fixed public address instead of querying DNS.

    validate_non_local resolves URLs even when the HTTP request itself is mocked,
    so tests using it would otherwise depend on the runner's DNS. IP literals are
    still resolved normally so private-address checks keep working.
    """
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        try:
            ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", port or 0))]
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
