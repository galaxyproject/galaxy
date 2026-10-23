import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    NamedTuple,
)

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class FtpServerAddress(NamedTuple):
    host: str
    port: int


@contextmanager
def serve_ftp_directory(root: str) -> Iterator[FtpServerAddress]:
    """Serve a directory over FTP on an ephemeral port on localhost.

    Access is anonymous and read-only, so the ftp file source reaches it with its
    default credentials.
    """
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(root)

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
        yield FtpServerAddress(host=host, port=port)
    finally:
        stop.set()
        thread.join(timeout=10)
