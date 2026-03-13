"""In-process SFTP server mixin for Selenium integration tests.

Provides :class:`SFTPServerMixin`, a class-level mixin that manages the full
lifecycle of a paramiko-backed SFTP server:

* :meth:`SFTPServerMixin.start_sftp_server` – start the server rooted at a
  given directory and store all state on the class.
* :meth:`SFTPServerMixin.stop_sftp_server` – stop the server and release every
  resource.

The server listens on a random free port on ``127.0.0.1`` so it is always
reachable by the local Galaxy process without any external network access.
"""

import os
import socket
import threading
from dataclasses import dataclass
from typing import IO

import paramiko
import paramiko.common
import paramiko.sftp

# ---------------------------------------------------------------------------
# Default credentials exposed so callers can pass them as template parameters
# ---------------------------------------------------------------------------

SFTP_DEFAULT_USER = "testuser"
SFTP_DEFAULT_PASS = "testpass"


# ---------------------------------------------------------------------------
# Server state container
# ---------------------------------------------------------------------------


@dataclass
class SFTPServerState:
    """All runtime state for a running in-process SFTP server."""

    port: int
    username: str
    password: str
    stop_event: threading.Event
    active_transports: list["paramiko.Transport"]
    srv_sock: socket.socket
    accept_thread: threading.Thread

    def stop(self) -> None:
        """Stop the server and release all resources."""
        self.stop_event.set()
        self.srv_sock.close()
        self.accept_thread.join(timeout=5)
        for transport in self.active_transports:
            transport.close()


# ---------------------------------------------------------------------------
# Internal paramiko server implementation
# ---------------------------------------------------------------------------


class _ServerInterface(paramiko.ServerInterface):
    """Minimal SSH server interface that accepts password auth."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.common.OPEN_SUCCEEDED
        return paramiko.common.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username: str, password: str) -> int:
        if username == self._username and password == self._password:
            return paramiko.common.AUTH_SUCCESSFUL
        return paramiko.common.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"


class _SFTPHandle(paramiko.SFTPHandle):
    readfile: IO[bytes]
    writefile: IO[bytes]

    def stat(self) -> paramiko.SFTPAttributes:
        return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))

    def chattr(self, attr: paramiko.SFTPAttributes) -> int:
        return paramiko.sftp.SFTP_OK


def _errno_to_sftp(errno: int | None) -> int:
    return paramiko.SFTPServer.convert_errno(errno if errno is not None else 5)


def _make_sftp_server_interface(root: str) -> type[paramiko.SFTPServerInterface]:
    """Return a :class:`paramiko.SFTPServerInterface` subclass rooted at *root*."""

    class _SFTPServerInterface(paramiko.SFTPServerInterface):
        def __init__(self, server: paramiko.ServerInterface, *args: object, **kwargs: object) -> None:
            self._root = root
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


# ---------------------------------------------------------------------------
# Public mixin
# ---------------------------------------------------------------------------


class SFTPServerMixin:
    """Class-level mixin that manages an in-process paramiko SFTP server.

    Subclasses must call :meth:`start_sftp_server` (typically from
    ``handle_galaxy_config_kwds``) and :meth:`stop_sftp_server` (typically
    from ``tearDownClass``).

    After :meth:`start_sftp_server` returns, ``cls._sftp_server`` holds an
    :class:`SFTPServerState` with all runtime state (``port``, ``username``,
    ``password``, …).
    """

    _sftp_server: SFTPServerState

    @classmethod
    def start_sftp_server(
        cls,
        root: str,
        username: str = SFTP_DEFAULT_USER,
        password: str = SFTP_DEFAULT_PASS,
    ) -> None:
        """Start the SFTP server rooted at *root* and store state on the class.

        Parameters
        ----------
        root:
            Directory that the SFTP server will expose as its root (``/``).
        username / password:
            Credentials accepted by the server.  Default to
            :data:`SFTP_DEFAULT_USER` / :data:`SFTP_DEFAULT_PASS`.
        """
        sftp_server_interface = _make_sftp_server_interface(root)
        host_key = paramiko.RSAKey.generate(2048)

        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        srv_sock.bind(("127.0.0.1", 0))
        port: int = srv_sock.getsockname()[1]
        srv_sock.listen(10)
        srv_sock.settimeout(5)

        stop_event = threading.Event()
        active_transports: list[paramiko.Transport] = []
        server_interface = _ServerInterface(username, password)

        def _accept_loop() -> None:
            while not stop_event.is_set():
                try:
                    conn, _ = srv_sock.accept()
                except OSError:
                    # socket.timeout (every 5 s) and close/EBADF on teardown are
                    # all OSError subclasses; just loop back and re-check the flag.
                    continue
                try:
                    transport = paramiko.Transport(conn)
                    transport.add_server_key(host_key)
                    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_server_interface)
                    transport.start_server(event=threading.Event(), server=server_interface)
                    active_transports.append(transport)
                except Exception:
                    conn.close()

        accept_thread = threading.Thread(target=_accept_loop, daemon=True)
        accept_thread.start()

        cls._sftp_server = SFTPServerState(
            port=port,
            username=username,
            password=password,
            stop_event=stop_event,
            active_transports=active_transports,
            srv_sock=srv_sock,
            accept_thread=accept_thread,
        )

    @classmethod
    def stop_sftp_server(cls) -> None:
        """Stop the SFTP server and release all resources."""
        if hasattr(cls, "_sftp_server"):
            cls._sftp_server.stop()
