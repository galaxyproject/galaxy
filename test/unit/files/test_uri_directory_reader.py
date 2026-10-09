import os
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest

from galaxy.files.unittest_utils import stock_file_sources_allowing_loopback
from galaxy.files.uris import UriDirectoryReader
from galaxy.util.unittest_utils.test_http_server import (
    QuietDirectoryRequestHandler,
    serve_directory,
)


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

    class RecordingHandler(QuietDirectoryRequestHandler):
        # Keep connections open so clients can reuse them.
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            client_ports.add(self.client_address[1])
            super().do_GET()

        def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
            # Unlike the default, keep the connection open, as real servers such as S3 do.
            body = b"Not Found"
            self.send_response(code, message)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with serve_directory(served, RecordingHandler) as base_url:
        yield ServedDirectory(served, base_url, client_ports)


def _reader(base_url: str) -> UriDirectoryReader:
    return UriDirectoryReader(f"{base_url}/store", file_sources=stock_file_sources_allowing_loopback())


def test_fetch_all_reuses_connections_and_counts_missing_files(
    served_directory: ServedDirectory, tmp_path: Path
) -> None:
    store = served_directory.served / "store"
    store.mkdir()
    for i in range(20):
        (store / str(i)).write_text(str(i))
    target = tmp_path / "target"
    # Missing files first: an error answer must not close the connection either.
    rel_paths = [f"missing{i}" for i in range(10)] + [str(i) for i in range(20)]

    missing = _reader(served_directory.base_url).fetch_all(rel_paths, str(target), workers=2)

    assert missing == 10
    assert sorted(os.listdir(target)) == sorted(str(i) for i in range(20))
    assert (target / "7").read_text() == "7"
    # Each of the two workers reuses its connection for all its requests.
    assert len(served_directory.client_ports) <= 2


def test_fetch_all_raises_the_first_error(served_directory: ServedDirectory, tmp_path: Path) -> None:
    def rel_paths() -> Iterator[str]:
        yield "a"
        raise ValueError("cannot compute keys")

    with pytest.raises(ValueError, match="cannot compute keys"):
        _reader(served_directory.base_url).fetch_all(rel_paths(), str(tmp_path), workers=2)


def test_fetch_refuses_unsafe_paths(served_directory: ServedDirectory, tmp_path: Path) -> None:
    with pytest.raises(Exception, match="unsafe path"):
        _reader(served_directory.base_url).fetch("../outside", str(tmp_path))
