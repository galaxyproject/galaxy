"""Tests for the ``require_login`` redirect built by ``GalaxyWebTransaction``.

A deep link into Galaxy has to survive the round trip through the login flow, query
string and all. Landing requests are the motivating case: the destination that matters
is ``/tool_landings/<uuid>?public=true``, and dropping the query string silently
orphans the landing request once the user finally logs in.

This is a unit test rather than an integration test because the integration harness
polls ``/`` for a 200 to decide the server is up, which never happens once
``require_login`` is on.
"""

from typing import cast
from urllib.parse import (
    parse_qs,
    urlparse,
)

import pytest
import webob.exc
from routes import request_config

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.structured_app import BasicSharedApp
from galaxy.util.bunch import Bunch
from galaxy.webapps.base.webapp import (
    GalaxyWebTransaction,
    WebApplication,
)

LANDING_PATH = "/tool_landings/8a7f3c1e-0000-4000-8000-abcdef123456"
LANDING_QUERY = "public=true"


class StubGalaxyWebTransaction(GalaxyWebTransaction):
    def _ensure_valid_session(self, session_cookie: str, create: bool = True) -> None:
        pass


class RoutedWebApplication(WebApplication):
    def _instantiate_controller(self, type, app):
        # Only the route map matters here, so skip building real controllers.
        return object()


def _trans_for(path: str, query_string: str = "") -> StubGalaxyWebTransaction:
    app = cast(BasicSharedApp, galaxy_mock.MockApp())
    app.config.require_login = True
    app.config.show_welcome_with_login = False
    app.config.template_cache_path = "/tmp"
    # The login gate consults these while deciding what bypasses require_login.
    app.datatypes_registry = Bunch(get_display_sites=lambda name: [], display_applications={})

    webapp = RoutedWebApplication(cast(WebApplication, app))
    # The two generic routes url_for resolves against -- see buildapp.app_pair.
    webapp.add_route("/{controller}/{action}", action="index")
    webapp.add_route("/{action}", controller="root", action="index")

    routes_config = request_config()
    routes_config.mapper = webapp.mapper
    routes_config.host = "galaxy.example.org"
    routes_config.protocol = "https"

    environ = galaxy_mock.buildMockEnviron(PATH_INFO=path, QUERY_STRING=query_string)
    trans = StubGalaxyWebTransaction(environ, app, cast(WebApplication, webapp), "galaxysession")
    trans.galaxy_session = Bunch(user=None)
    return trans


def _login_redirect_for(path: str, query_string: str = "") -> str:
    """Run the require_login gate and return where it sent the browser."""
    trans = _trans_for(path, query_string)
    with pytest.raises(webob.exc.HTTPFound) as caught:
        trans._ensure_logged_in_user("galaxysession")
    return caught.value.location


def _redirect_param(location: str) -> str:
    redirect = parse_qs(urlparse(location).query).get("redirect")
    assert redirect, f"no redirect param carried on login redirect: {location}"
    return redirect[0]


def test_login_redirect_preserves_the_query_string():
    location = _login_redirect_for(LANDING_PATH, LANDING_QUERY)
    redirect = _redirect_param(location)
    assert redirect.startswith(LANDING_PATH)
    # The bug: only request.path was forwarded, so "?public=true" never made it here
    # and the landing request was orphaned once the user came back from logging in.
    assert LANDING_QUERY in redirect, f"query string dropped from login redirect: {redirect}"


def test_login_redirect_without_a_query_string_is_unchanged():
    redirect = _redirect_param(_login_redirect_for(LANDING_PATH))
    assert redirect == LANDING_PATH


def test_login_redirect_targets_the_login_entry_point():
    location = _login_redirect_for(LANDING_PATH, LANDING_QUERY)
    assert urlparse(location).path == "/login"


def test_login_route_itself_is_not_gated():
    """Otherwise require_login would bounce the login page to itself."""
    trans = _trans_for("/login", "redirect=%2Ftool_landings%2Fabc")
    # No HTTPFound raised means the request was allowed through.
    trans._ensure_logged_in_user("galaxysession")
