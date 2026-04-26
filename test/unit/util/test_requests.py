import pytest
import responses

from galaxy.util import requests as galaxy_requests
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
def test_session_has_user_agent_header(method):
    s: galaxy_requests.Session = method()
    assert s.headers["user-agent"] == EXPECTED_USER_AGENT
