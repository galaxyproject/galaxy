"""Pytest fixtures for the files unit test suite."""

import ipaddress
import socket
import time
from collections.abc import (
    Generator,
    Iterator,
)
from pathlib import Path
from typing import NamedTuple

import pytest

from galaxy.files.unittest_utils.ftp_server import serve_ftp_directory
from galaxy.util.unittest_utils.test_http_server import test_http_server  # noqa: F401


class FtpServerFixture(NamedTuple):
    host: str
    port: int
    root: Path


@pytest.fixture
def ftp_server(tmp_path: Path) -> Iterator[FtpServerFixture]:
    """Serve a temporary directory over FTP on an ephemeral port on localhost.

    Tests put the files they expect to read into ``root``.
    """
    root = tmp_path / "ftp_root"
    root.mkdir()
    with serve_ftp_directory(str(root)) as (host, port):
        yield FtpServerFixture(host=host, port=port, root=root)


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
