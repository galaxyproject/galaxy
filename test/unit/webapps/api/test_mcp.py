"""Unit tests for the MCP request/response stubs.

Regression coverage for the bug where MCP tools constructed a bare
``WorkRequestContext`` (no ``.request`` attribute), causing
``HDASerializer.serialize_old_display_applications`` to raise
``AttributeError: 'WorkRequestContext' object has no attribute 'request'``
whenever ``enable_old_display_applications`` was set.
"""

from galaxy.webapps.galaxy.api.mcp import (
    _StaticRequest,
    _StaticResponse,
)
from galaxy.work.context import (
    GalaxyAbstractRequest,
    GalaxyAbstractResponse,
)


def test_static_request_implements_abstract_interface():
    request = _StaticRequest("http://localhost:8080")
    assert isinstance(request, GalaxyAbstractRequest)


def test_static_request_base_always_has_trailing_slash():
    # Matches GalaxyASGIRequest.base shape (Starlette base_url has trailing slash).
    assert _StaticRequest("http://localhost:8080").base == "http://localhost:8080/"
    assert _StaticRequest("http://localhost:8080/").base == "http://localhost:8080/"
    assert _StaticRequest("https://example.org/galaxy").base == "https://example.org/galaxy/"


def test_static_request_host_and_security():
    insecure = _StaticRequest("http://localhost:8080")
    assert insecure.host == "localhost:8080"
    assert insecure.is_secure is False

    secure = _StaticRequest("https://galaxy.example.org")
    assert secure.host == "galaxy.example.org"
    assert secure.is_secure is True


def test_static_request_get_cookie_returns_none():
    assert _StaticRequest("http://localhost:8080").get_cookie("anything") is None


def test_static_response_implements_abstract_interface():
    response = _StaticResponse()
    assert isinstance(response, GalaxyAbstractResponse)
    assert response.headers == {}
    response.set_cookie("k", "v")
