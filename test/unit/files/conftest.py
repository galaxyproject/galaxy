"""Pytest fixtures for the files unit test suite."""

import os
import shutil
import socket
import tempfile
import threading
from collections.abc import Generator
from dataclasses import dataclass
from typing import IO

import paramiko
import paramiko.common
import paramiko.sftp
import pytest

from galaxy_test.base.mock_http_server import (
    MockHTTPRequestHandler,
    MockHttpServer,
    start_mock_http_server,
)

_SFTP_USER = "testuser"
_SFTP_PASS = "testpass"


@dataclass
class SftpServerInfo:
    host: str
    port: int
    root: str
    user: str
    passwd: str


class _ServerInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.common.OPEN_SUCCEEDED
        return paramiko.common.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username: str, password: str) -> int:
        if username == _SFTP_USER and password == _SFTP_PASS:
            return paramiko.common.AUTH_SUCCESSFUL
        return paramiko.common.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"


class _SFTPHandle(paramiko.SFTPHandle):
    """SFTPHandle with explicit IO attributes so mypy is satisfied."""

    readfile: IO[bytes]
    writefile: IO[bytes]

    def stat(self) -> paramiko.SFTPAttributes:
        return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))

    def chattr(self, attr: paramiko.SFTPAttributes) -> int:
        return paramiko.sftp.SFTP_OK


def _errno_to_sftp(errno: int | None) -> int:
    """Convert an OSError errno to an SFTP error code, treating None as EIO."""
    return paramiko.SFTPServer.convert_errno(errno if errno is not None else 5)


def _make_sftp_server_interface(root_dir: str) -> type[paramiko.SFTPServerInterface]:
    """Return a SFTPServerInterface subclass that serves files from *root_dir*."""

    class _SFTPServerInterface(paramiko.SFTPServerInterface):
        def __init__(self, server: paramiko.ServerInterface, *args: object, **kwargs: object) -> None:
            self._root = root_dir
            super().__init__(server, *args, **kwargs)

        def _realpath(self, path: str) -> str:
            return os.path.join(self._root, path.lstrip("/"))

        def list_folder(self, path: str) -> list[paramiko.SFTPAttributes] | int:
            real = self._realpath(path)
            try:
                entries = []
                for name in os.listdir(real):
                    attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(real, name)))
                    attr.filename = name
                    entries.append(attr)
                return entries
            except OSError as e:
                return _errno_to_sftp(e.errno)

        def stat(self, path: str) -> paramiko.SFTPAttributes | int:
            try:
                return paramiko.SFTPAttributes.from_stat(os.stat(self._realpath(path)))
            except OSError as e:
                return _errno_to_sftp(e.errno)

        def lstat(self, path: str) -> paramiko.SFTPAttributes | int:
            try:
                return paramiko.SFTPAttributes.from_stat(os.lstat(self._realpath(path)))
            except OSError as e:
                return _errno_to_sftp(e.errno)

        def open(self, path: str, flags: int, attr: paramiko.SFTPAttributes) -> _SFTPHandle | int:
            real = self._realpath(path)
            try:
                binary_flags = flags | getattr(os, "O_BINARY", 0)
                fd = os.open(real, binary_flags, 0o666)
                fobj = _SFTPHandle(flags)
                if flags & os.O_WRONLY:
                    fobj.writefile = os.fdopen(fd, "wb")
                elif flags & os.O_RDWR:
                    f = os.fdopen(fd, "r+b")
                    fobj.readfile = f
                    fobj.writefile = f
                else:
                    fobj.readfile = os.fdopen(fd, "rb")
                return fobj
            except OSError as e:
                return _errno_to_sftp(e.errno)

        def remove(self, path: str) -> int:
            try:
                os.remove(self._realpath(path))
            except OSError as e:
                return _errno_to_sftp(e.errno)
            return paramiko.sftp.SFTP_OK

        def rename(self, oldpath: str, newpath: str) -> int:
            try:
                os.rename(self._realpath(oldpath), self._realpath(newpath))
            except OSError as e:
                return _errno_to_sftp(e.errno)
            return paramiko.sftp.SFTP_OK

        def mkdir(self, path: str, attr: paramiko.SFTPAttributes) -> int:
            try:
                os.mkdir(self._realpath(path))
            except OSError as e:
                return _errno_to_sftp(e.errno)
            return paramiko.sftp.SFTP_OK

        def rmdir(self, path: str) -> int:
            try:
                os.rmdir(self._realpath(path))
            except OSError as e:
                return _errno_to_sftp(e.errno)
            return paramiko.sftp.SFTP_OK

        def chattr(self, path: str, attr: paramiko.SFTPAttributes) -> int:
            return paramiko.sftp.SFTP_OK

        def canonicalize(self, path: str) -> str:
            return "/" + os.path.relpath(self._realpath(path), self._root).lstrip(".")

    return _SFTPServerInterface


@pytest.fixture()
def sftp_server() -> Generator[SftpServerInfo, None, None]:
    """Spin up an ephemeral in-process SFTP server backed by a temporary directory.

    The temp directory is pre-populated with a file ``a`` containing ``a\\n``
    so that ``assert_simple_file_realize`` passes out of the box.

    Yields an :class:`SftpServerInfo` with connection details.
    """
    root = tempfile.mkdtemp()
    with open(os.path.join(root, "a"), "w") as fh:
        fh.write("a\n")

    host_key = paramiko.RSAKey.generate(2048)
    sftp_si_class = _make_sftp_server_interface(root)

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    srv_sock.bind(("127.0.0.1", 0))
    port = srv_sock.getsockname()[1]
    srv_sock.listen(10)
    srv_sock.settimeout(5)

    stop_event = threading.Event()
    active_transports: list[paramiko.Transport] = []

    def _accept_loop() -> None:
        while not stop_event.is_set():
            try:
                conn, _ = srv_sock.accept()
            except (socket.timeout, OSError):
                continue
            transport = paramiko.Transport(conn)
            transport.add_server_key(host_key)
            transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_si_class)
            transport.start_server(event=threading.Event(), server=_ServerInterface())
            active_transports.append(transport)

    accept_thread = threading.Thread(target=_accept_loop, daemon=True)
    accept_thread.start()

    yield SftpServerInfo(host="127.0.0.1", port=port, root=root, user=_SFTP_USER, passwd=_SFTP_PASS)

    stop_event.set()
    srv_sock.close()  # unblocks accept() so the loop exits promptly
    accept_thread.join(timeout=5)
    for transport in active_transports:
        transport.close()
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="session")
def mock_http_server() -> Generator[MockHttpServer, None, None]:
    server, base_url = start_mock_http_server()
    try:
        yield MockHttpServer(base_url=base_url, handler_class=MockHTTPRequestHandler, is_remote=False)
    finally:
        server.shutdown()
