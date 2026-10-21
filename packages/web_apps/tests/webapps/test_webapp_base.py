"""
Unit tests for ``galaxy.web.framework.webapp``
"""

import logging
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import (
    cast,
)

import galaxy.config
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.structured_app import BasicSharedApp
from galaxy.webapps.base import webapp as webapp_module
from galaxy.webapps.base.webapp import (
    GalaxyWebTransaction,
    WebApplication,
)

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


def test_static_dist_falls_back_to_checkout_for_editable_client(monkeypatch, tmp_path):
    static = tmp_path / "static"
    dist = static / "dist"
    dist.mkdir(parents=True)
    asset = dist / "analysis.bundled.js"
    asset.write_text("window.galaxy = {};")
    # An editable galaxy-web-client has no bundled dist directory.
    monkeypatch.setattr(webapp_module, "default_static_dist_dir", None)
    mapping = webapp_module.build_url_map(None, {"static_dir": str(static)})
    assert Path(mapping["/static/dist"].directory) == dist


def test_static_dist_prefers_installed_client_and_allows_override(monkeypatch, tmp_path):
    bundled = tmp_path / "wheel" / "dist"
    bundled.mkdir(parents=True)
    monkeypatch.setattr(webapp_module, "default_static_dist_dir", str(bundled))
    mapping = webapp_module.build_url_map(None, {})
    assert Path(mapping["/static/dist"].directory) == bundled
    custom = tmp_path / "custom"
    custom.mkdir()
    mapping = webapp_module.build_url_map(None, {"static_dist_dir": str(custom)})
    assert Path(mapping["/static/dist"].directory) == custom


def test_editable_client_without_bundled_assets(monkeypatch, tmp_path):
    client = ModuleType("galaxy.web_client")
    client.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.setitem(sys.modules, "galaxy.web_client", client)
    monkeypatch.setattr(galaxy, "web_client", client, raising=False)
    assert webapp_module._web_client_dist_dir() is None
    dist = tmp_path / "dist"
    dist.mkdir()
    assert webapp_module._web_client_dist_dir() == str(dist)
