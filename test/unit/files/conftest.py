"""Pytest fixtures for the files unit test suite."""

import ipaddress
import socket
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from galaxy_test.base.mock_http_server import (
    MockHTTPRequestHandler,
    MockHttpServer,
    start_mock_http_server,
)


class FtpServerFixture(NamedTuple):
    host: str
    port: int
    root: Path


@pytest.fixture
def ftp_server(tmp_path: Path) -> Iterator[FtpServerFixture]:
    """Serve a temporary directory over FTP on an ephemeral port on localhost.

    Access is anonymous and read-only, so the ftp file source reaches it with its
    default credentials. Tests put the files they expect to read into ``root``.
    """
    root = tmp_path / "ftp_root"
    root.mkdir()

    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(str(root))

    class AnonymousFTPHandler(FTPHandler):
        pass

    AnonymousFTPHandler.authorizer = authorizer

    server = FTPServer(("127.0.0.1", 0), AnonymousFTPHandler)
    host, port = server.address
    stop = threading.Event()

    def serve():
        # The IO loop is driven here instead of through serve_forever() so that the
        # server is torn down from the serving thread. close_all() closes the poller
        # a blocking serve_forever() would still be waiting on.
        try:
            while not stop.is_set():
                server.ioloop.poll(0.1)
                server.ioloop.sched.poll()
        finally:
            server.close_all()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield FtpServerFixture(host=host, port=port, root=root)
    finally:
        stop.set()
        thread.join(timeout=10)


@pytest.fixture(scope="session")
def mock_http_server():
    server, base_url = start_mock_http_server()
    try:
        yield MockHttpServer(base_url=base_url, handler_class=MockHTTPRequestHandler, is_remote=False)
    finally:
        server.shutdown()


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
