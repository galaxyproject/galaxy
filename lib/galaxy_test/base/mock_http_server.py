"""A local mock HTTP server for replacing external test dependencies.

Replaces httpstat.us, usegalaxy.org, and raw.githubusercontent.com URLs
with a local server. Supports configurable status codes, file serving,
HEAD requests, range requests, and response delays.

When targeting a remote Galaxy server (GALAXY_TEST_EXTERNAL), falls back to
the real external URLs with automatic skip-if-down behavior.
"""

import os
import re
import threading
import time
from dataclasses import (
    dataclass,
    field,
)
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import pytest

from galaxy.util.unittest_utils import is_site_up


@dataclass
class Route:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    sleep_ms: int = 0
    method: str = "GET"
    support_head: bool = False
    support_ranges: bool = False


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    routes: dict[str, Route] = {}

    def _handle_request(self) -> None:
        route = self.routes.get(self.path)
        if route is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        is_head = self.command == "HEAD"
        if is_head and not route.support_head:
            self.send_response(405)
            self.end_headers()
            return
        if not is_head and route.method != self.command:
            self.send_response(405)
            self.end_headers()
            return

        if route.sleep_ms > 0:
            time.sleep(route.sleep_ms / 1000.0)

        body = route.body

        # Handle range requests
        range_header = self.headers.get("Range")
        if range_header and route.support_ranges:
            match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else len(body) - 1
                total = len(body)
                body = body[start : end + 1]
                self.send_response(206)
                for key, value in route.headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                if not is_head:
                    self.wfile.write(body)
                return

        self.send_response(route.status)
        for key, value in route.headers.items():
            self.send_header(key, value)
        if route.support_ranges:
            self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not is_head:
            self.wfile.write(body)

    def do_GET(self) -> None:
        self._handle_request()

    def do_HEAD(self) -> None:
        self._handle_request()

    def do_POST(self) -> None:
        self._handle_request()

    def log_message(self, format, *args) -> None:
        pass


class MockHttpServer:
    """A local mock HTTP server with a per-test URL factory.

    When running locally, registers routes on the mock server and returns local URLs.
    When targeting a remote Galaxy (GALAXY_TEST_EXTERNAL), returns the remote URL
    and skips the test if the remote site is down.
    """

    def __init__(
        self,
        base_url: Optional[str],
        handler_class: Optional[type[MockHTTPRequestHandler]],
        is_remote: bool,
    ):
        self.base_url = base_url
        self._handler_class = handler_class
        self.is_remote = is_remote
        self._counter = 0

    def get_url(
        self,
        *,
        remote_url: str,
        status: int = 200,
        body: str | bytes = "",
        file_path: Optional[str] = None,
        content_type: str = "application/octet-stream",
        sleep_ms: int = 0,
        response_headers: Optional[dict[str, str]] = None,
        request_method: str = "GET",
        support_head: bool = False,
        support_ranges: bool = False,
    ) -> str:
        """Register a mock endpoint and return its URL, or return remote_url with skip-if-down.

        Args:
            remote_url: The real URL to use when targeting a remote Galaxy server.
            status: HTTP status code to return.
            body: Response body (string or bytes). Ignored if file_path is set.
            file_path: Path to a file whose contents will be served as the response body.
            content_type: Content-Type header value.
            sleep_ms: Delay in milliseconds before responding.
            response_headers: Additional response headers.
            request_method: HTTP method to match (GET, POST, etc.).
            support_head: Whether to also respond to HEAD requests.
            support_ranges: Whether to support Range request headers (HTTP 206).
        """
        if self.is_remote:
            if not is_site_up(remote_url):
                pytest.skip(f"Remote site {remote_url} is down")
            return remote_url

        assert self._handler_class is not None
        self._counter += 1
        # Include filename in path so tools can sniff file extensions from the URL
        if file_path is not None:
            filename = os.path.basename(file_path)
        else:
            filename = os.path.basename(urlparse(remote_url).path)
        path = f"/mock/{self._counter}/{filename}" if filename else f"/mock/{self._counter}"

        if file_path is not None:
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                # Resolve relative paths from the Galaxy project root
                galaxy_root = Path(__file__).resolve().parents[3]
                file_path_obj = galaxy_root / file_path_obj
            encoded_body = file_path_obj.read_bytes()
        elif isinstance(body, str):
            encoded_body = body.encode()
        else:
            encoded_body = body

        headers = {"Content-Type": content_type}
        if response_headers:
            headers.update(response_headers)
        self._handler_class.routes[path] = Route(
            status=status,
            body=encoded_body,
            headers=headers,
            sleep_ms=sleep_ms,
            method=request_method,
            support_head=support_head,
            support_ranges=support_ranges,
        )
        return f"{self.base_url}{path}"


def start_mock_http_server(host: str = "127.0.0.1", port: int = 0) -> tuple[HTTPServer, str]:
    """Start a mock HTTP server in a daemon thread.

    Args:
        host: Address to bind to. Defaults to 127.0.0.1.
        port: Port to bind to. 0 means OS-assigned.

    Returns:
        Tuple of (server, base_url).
    """
    server = HTTPServer((host, port), MockHTTPRequestHandler)
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://{host}:{actual_port}"
