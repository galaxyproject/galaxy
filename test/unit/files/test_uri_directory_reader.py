import functools
import os
import threading
from collections.abc import Iterator
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import (
    Any,
    NamedTuple,
)

import pytest

from galaxy.files.unittest_utils import stock_file_sources_allowing_loopback
from galaxy.files.uris import UriDirectoryReader


class ServedDirectory(NamedTuple):
    served: Path
    base_url: str
    client_ports: set[int]


@pytest.fixture
def served_directory(tmp_path: Path) -> Iterator[ServedDirectory]:
    """Serve ``tmp_path / "served"`` over HTTP/1.1, recording the client port of every request."""
    served = tmp_path / "served"
    served.mkdir()
    client_ports: set[int] = set()

    class RecordingHandler(SimpleHTTPRequestHandler):
        # Keep connections open so clients can reuse them.
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            client_ports.add(self.client_address[1])
            super().do_GET()

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(RecordingHandler, directory=str(served)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield ServedDirectory(served, f"http://127.0.0.1:{server.server_address[1]}", client_ports)
    finally:
        server.shutdown()


def _reader(base_url: str) -> UriDirectoryReader:
    return UriDirectoryReader(f"{base_url}/store", file_sources=stock_file_sources_allowing_loopback())


def test_fetch_all_reuses_connections_and_reports_missing_files(
    served_directory: ServedDirectory, tmp_path: Path
) -> None:
    served, base_url, client_ports = served_directory
    (served / "store").mkdir()
    for i in range(20):
        (served / "store" / str(i)).write_text(str(i))
    target = tmp_path / "target"
    target.mkdir()
    rel_paths = [str(i) for i in range(20)] + ["missing"]

    missing = _reader(base_url).fetch_all(((p, str(target / p)) for p in rel_paths), workers=2)

    assert missing == ["missing"]
    assert sorted(os.listdir(target)) == sorted(str(i) for i in range(20))
    assert (target / "7").read_text() == "7"
    # Each of the two workers reuses its connection for all its requests.
    assert len(client_ports) <= 2


def test_fetch_all_raises_the_first_error(served_directory: ServedDirectory, tmp_path: Path) -> None:
    _, base_url, _ = served_directory

    def targets() -> Iterator[tuple[str, str]]:
        yield "a", str(tmp_path / "a")
        raise ValueError("cannot compute keys")

    with pytest.raises(ValueError, match="cannot compute keys"):
        _reader(base_url).fetch_all(targets(), workers=2)
