"""A local mock HTTP server for replacing external test dependencies like httpstat.us and usegalaxy.org.

Provides a lightweight HTTP server using Python stdlib that can be configured
per-test with custom status codes, response bodies, headers, and delays.
When targeting a remote Galaxy server (GALAXY_TEST_EXTERNAL), falls back to
the real external URLs with automatic skip-if-down behavior.
"""

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
from typing import Optional

import pytest

from galaxy.util.unittest_utils import is_site_up


@dataclass
class Route:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    sleep_ms: int = 0
    method: str = "GET"


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    routes: dict[str, Route] = {}

    def _handle_request(self) -> None:
        route = self.routes.get(self.path)
        if route is None or route.method != self.command:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        if route.sleep_ms > 0:
            time.sleep(route.sleep_ms / 1000.0)
        self.send_response(route.status)
        for key, value in route.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(route.body)

    def do_GET(self) -> None:
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
        content_type: str = "text/plain",
        sleep_ms: int = 0,
        response_headers: Optional[dict[str, str]] = None,
        request_method: str = "GET",
    ) -> str:
        """Register a mock endpoint and return its URL, or return remote_url with skip-if-down."""
        if self.is_remote:
            if not is_site_up(remote_url):
                pytest.skip(f"Remote site {remote_url} is down")
            return remote_url

        assert self._handler_class is not None
        self._counter += 1
        path = f"/mock/{self._counter}"
        encoded_body = body.encode() if isinstance(body, str) else body
        headers = {"Content-Type": content_type}
        if response_headers:
            headers.update(response_headers)
        self._handler_class.routes[path] = Route(
            status=status,
            body=encoded_body,
            headers=headers,
            sleep_ms=sleep_ms,
            method=request_method,
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
