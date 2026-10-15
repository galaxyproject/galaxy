"""
Unit tests for ``galaxy.web.framework.webapp``
"""

import logging
import re
from typing import (
    cast,
)

import pytest
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient

import galaxy.config
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.structured_app import BasicSharedApp
from galaxy.webapps.base.webapp import (
    GalaxyWebTransaction,
    WebApplication,
)
from galaxy.webapps.galaxy.fast_app import XFrameOptionsMiddleware

log = logging.getLogger(__name__)


class StubGalaxyWebTransaction(GalaxyWebTransaction):
    def _ensure_valid_session(self, session_cookie: str, create: bool = True) -> None:
        pass


class CORSParsingMockConfig(galaxy_mock.MockAppConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allowed_origin_hostnames = self._parse_allowed_origin_hostnames(kwargs)

    @staticmethod
    def _parse_allowed_origin_hostnames(kwargs):
        hostnames = kwargs.get("allowed_origin_hostnames")
        return galaxy.config.Configuration._parse_allowed_origin_hostnames(hostnames)


class TestGalaxyWebTransactionHeaders:
    def _new_trans(self, allowed_origin_hostnames: str | None = None) -> StubGalaxyWebTransaction:
        app = cast(BasicSharedApp, galaxy_mock.MockApp())
        app.config = CORSParsingMockConfig(allowed_origin_hostnames=allowed_origin_hostnames)
        webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
        environ = galaxy_mock.buildMockEnviron()
        trans = StubGalaxyWebTransaction(environ, app, webapp, "session_cookie")
        return trans

    def assert_cors_header_equals(self, headers, should_be):
        assert headers.get("access-control-allow-origin", None) == should_be

    def assert_cors_header_missing(self, headers):
        assert "access-control-allow-origin" not in headers

    def test_parse_allowed_origin_hostnames(self) -> None:
        """Should return a list of (possibly) mixed strings and regexps"""
        config = CORSParsingMockConfig()

        # falsy listify value should return None
        assert config._parse_allowed_origin_hostnames({"allowed_origin_hostnames": ""}) is None

        # should parse regex if using fwd slashes, string otherwise
        hostnames = config._parse_allowed_origin_hostnames(
            {"allowed_origin_hostnames": r"/host\d{2}/,geocities.com,miskatonic.edu"}
        )
        assert isinstance(hostnames[0], re.Pattern)
        assert isinstance(hostnames[1], str)
        assert isinstance(hostnames[2], str)

    def test_default_set_cors_headers(self) -> None:
        """No CORS headers should be set (or even checked) by default"""
        trans = self._new_trans(allowed_origin_hostnames=None)
        assert isinstance(trans, GalaxyWebTransaction)

        trans.request.headers["Origin"] = "http://lisaskelprecipes.pinterest.com?id=kelpcake"
        trans.set_cors_headers()
        self.assert_cors_header_missing(trans.response.headers)

    def test_set_cors_headers(self) -> None:
        """Origin should be echo'd when it matches an allowed hostname"""
        # an asterisk is a special 'allow all' string
        trans = self._new_trans(allowed_origin_hostnames="*,beep.com")
        trans.request.headers["Origin"] = "http://xxdarkhackerxx.disney.com"
        trans.set_cors_headers()
        self.assert_cors_header_equals(trans.response.headers, "http://xxdarkhackerxx.disney.com")

        # subdomains should pass
        trans = self._new_trans(allowed_origin_hostnames=r"something.com,/^[\w\.]*beep\.com/")
        trans.request.headers["Origin"] = "http://boop.beep.com"
        trans.set_cors_headers()
        self.assert_cors_header_equals(trans.response.headers, "http://boop.beep.com")

        # ports should work
        trans = self._new_trans(allowed_origin_hostnames=r"somethingelse.com,/^[\w\.]*beep\.com/")
        trans.request.headers["Origin"] = "http://boop.beep.com:8080"
        trans.set_cors_headers()
        self.assert_cors_header_equals(trans.response.headers, "http://boop.beep.com:8080")

        # localhost should work
        trans = self._new_trans(allowed_origin_hostnames="/localhost/")
        trans.request.headers["Origin"] = "http://localhost:8080"
        trans.set_cors_headers()
        self.assert_cors_header_equals(trans.response.headers, "http://localhost:8080")

        # spoofing shouldn't be easy
        trans.response.headers = {}
        trans.request.headers["Origin"] = "http://localhost.badstuff.tv"
        trans.set_cors_headers()
        self.assert_cors_header_missing(trans.response.headers)

        # unicode should work
        trans = self._new_trans(allowed_origin_hostnames=r"/öbb\.at/")
        trans.request.headers["Origin"] = "http://öbb.at"
        trans.set_cors_headers()
        assert trans.response.headers["access-control-allow-origin"] == "http://öbb.at"


def _frame_headers_client(url_prefix: str, **config) -> tuple[TestClient, str]:
    """Serve transaction headers through the X-Frame-Options middleware, mounted as initialize_fast_app does."""
    app = cast(BasicSharedApp, galaxy_mock.MockApp())
    app.config = galaxy_mock.MockAppConfig(x_frame_options="SAMEORIGIN", **config)
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))

    def wsgi_app(environ, start_response):
        trans = StubGalaxyWebTransaction(environ, app, webapp, "session_cookie")
        start_response("200 OK", list(trans.response.headers.items()))
        return [b""]

    root_path = "" if url_prefix == "/" else url_prefix
    fastapi_app = FastAPI(root_path=root_path)
    fastapi_app.add_middleware(XFrameOptionsMiddleware, x_frame_options="SAMEORIGIN")
    fastapi_app.mount("/", WSGIMiddleware(wsgi_app))  # type: ignore[arg-type]
    if not root_path:
        return TestClient(fastapi_app), root_path
    parent_app = FastAPI()
    parent_app.mount(root_path, app=fastapi_app)
    return TestClient(parent_app), root_path


@pytest.mark.parametrize("url_prefix", ["/", "/galaxy"])
def test_pages_deny_other_origins(url_prefix):
    client, root_path = _frame_headers_client(url_prefix)
    headers = client.get(f"{root_path}/histories/list").headers
    assert set(headers.get_list("X-Frame-Options")) == {"SAMEORIGIN"}
    assert "Content-Security-Policy" not in headers


def test_published_embeds_are_unrestricted():
    client, _ = _frame_headers_client("/")
    headers = client.get("/published/page?id=1&embed=true").headers
    assert "X-Frame-Options" not in headers
    assert "Content-Security-Policy" not in headers


@pytest.mark.parametrize("url_prefix", ["/", "/galaxy"])
def test_widgets_allow_any_origin_by_default(url_prefix):
    client, root_path = _frame_headers_client(url_prefix)
    headers = client.get(f"{root_path}/widgets/histories/1/graph").headers
    assert headers["Content-Security-Policy"] == "frame-ancestors *"
    assert "X-Frame-Options" not in headers


@pytest.mark.parametrize("url_prefix", ["/", "/galaxy"])
def test_widgets_allow_configured_origins(url_prefix):
    client, root_path = _frame_headers_client(
        url_prefix, widgets_allowed_origins="https://a.example.org, https://b.example.org"
    )
    headers = client.get(f"{root_path}/widgets/histories/1/graph").headers
    assert headers["Content-Security-Policy"] == "frame-ancestors 'self' https://a.example.org https://b.example.org"
    assert "X-Frame-Options" not in headers
