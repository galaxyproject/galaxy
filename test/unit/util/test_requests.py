import socket
import threading

import pytest
import responses
from requests.adapters import HTTPAdapter

from galaxy.util import requests as galaxy_requests
from galaxy.util.requests import DEFAULT_RETRIES
from galaxy.util.user_agent import get_default_headers

EXPECTED_USER_AGENT = get_default_headers()["user-agent"]


# --- User-Agent header injection ---


@pytest.mark.parametrize("method", ("delete", "get", "head", "options", "patch", "post", "put"))
@responses.activate
def test_user_agent_and_caller_headers_are_set(method: str):
    """All methods inject the Galaxy user-agent and preserve caller-supplied headers."""
    responses.add(getattr(responses, method.upper()), "https://example.com/", status=200)
    getattr(galaxy_requests, method)("https://example.com/", headers={"X-Custom": "value"})
    req_headers = responses.calls[0].request.headers
    assert req_headers["user-agent"] == EXPECTED_USER_AGENT
    assert req_headers["X-Custom"] == "value"


# --- Session factory ---


@pytest.mark.parametrize("method", (galaxy_requests.Session, galaxy_requests.session))
def test_Session_has_user_agent_header(method):
    s: galaxy_requests.Session = method()
    assert s.headers["user-agent"] == EXPECTED_USER_AGENT


def test_Session_has_no_retry_adapter():
    s = galaxy_requests.Session()
    for url in ("https://example.com/", "http://example.com/"):
        adapter = s.get_adapter(url)
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 0  # requests default: no retries


# --- RetrySession ---


def test_RetrySession_has_user_agent_header():
    s = galaxy_requests.RetrySession()
    assert s.headers["user-agent"] == EXPECTED_USER_AGENT


def test_retry_session_has_retry_adapter():
    s = galaxy_requests.RetrySession()
    for url in ("https://example.com/", "http://example.com/"):
        adapter = s.get_adapter(url)
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == DEFAULT_RETRIES


# --- Retry behaviour ---


@pytest.fixture()
def connection_reset_server():
    """A TCP server that accepts connections and immediately closes them."""
    attempts = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(10)
    stop = threading.Event()
    sock.settimeout(0.1)

    def serve():
        nonlocal attempts
        while not stop.is_set():
            try:
                conn, _ = sock.accept()
            except socket.timeout:  # noqa: UP041  # Python <=3.9 support, replace with TimeoutError in Python 3.10+
                continue
            except OSError:
                break
            attempts += 1
            conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", lambda: attempts
    stop.set()
    sock.close()
    thread.join()


@pytest.mark.parametrize("method", ("delete", "get", "head", "options", "put"))
def test_RetrySession_retries_idempotent_methods(method: str, connection_reset_server):
    """RetrySession retries idempotent methods on connection failure."""
    url, get_attempts = connection_reset_server
    with galaxy_requests.RetrySession() as s:
        with pytest.raises(galaxy_requests.exceptions.ConnectionError):
            getattr(s, method)(url)
    assert get_attempts() == 1 + DEFAULT_RETRIES
