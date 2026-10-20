"""Tests for how the OIDC callback consumes the login-next cookie.

This is the point where an attacker-supplied value becomes a redirect, so it is where
the destination has to be validated -- doing it here covers every writer of the cookie,
including the ``next`` parameter accepted by ``OIDC.login``.
"""

import json
from typing import Optional

import pytest
from routes import (
    Mapper,
    request_config,
)

from galaxy.util.bunch import Bunch
from galaxy.web import url_for
from galaxy.webapps.galaxy.controllers import authnz as authnz_module
from galaxy.webapps.galaxy.controllers.authnz import (
    LOGIN_NEXT_COOKIE_NAME,
    OIDC,
)

LANDING_PATH = "/tool_landings/1234-5678?public=true"


class StubTrans:
    """The slice of the transaction interface ``OIDC.callback`` touches before it stops."""

    def __init__(self, login_next_cookie: Optional[str], allowed_hosts=()):
        self.user = None
        self._cookies = {LOGIN_NEXT_COOKIE_NAME: login_next_cookie}
        self.login_redirect_url: Optional[str] = None
        self.app = Bunch(
            config=Bunch(allowed_login_redirect_hosts=list(allowed_hosts)),
            authnz_manager=Bunch(callback=self._callback),
        )

    def get_cookie(self, name):
        return self._cookies.get(name)

    def _callback(self, provider, state, code, trans, login_redirect_url=None, idphint=None):
        # Record what the controller decided, then stop the flow.
        self.login_redirect_url = login_redirect_url
        return False, "halt", (None, None)

    def show_error_message(self, message):
        return message


class CompletingTrans(StubTrans):
    """A transaction whose OIDC backend logs the user in and returns the destination it was given."""

    def __init__(self, login_next_cookie: Optional[str], allowed_hosts=()):
        super().__init__(login_next_cookie, allowed_hosts)
        self.app.config.enable_oidc = True
        self.app.authnz_manager.create_user = self._create_user
        self.request = Bunch(method="POST", POST={"confirmation_id": "confirmation"})
        self.response = Bunch(headers={}, set_content_type=lambda content_type: None, send_redirect=lambda url: url)

    def _callback(self, provider, state, code, trans, login_redirect_url=None, idphint=None):
        return True, "", (login_redirect_url, "user")

    def _create_user(self, provider, confirmation_id=None, trans=None, login_redirect_url=None):
        return True, "", (login_redirect_url, "user")

    def set_cookie(self, value, name, **kwargs):
        self._cookies[name] = value

    def handle_user_login(self, user):
        pass

    def check_csrf_token(self, payload):
        return None


@pytest.fixture(autouse=True)
def passthrough_url_for(monkeypatch):
    # url_for needs a live routes config; the decision under test is which value it gets.
    monkeypatch.setattr(authnz_module, "url_for", lambda path: path)


@pytest.fixture
def galaxy_url_prefix(monkeypatch):
    # The real url_for, serving Galaxy under /galaxy.
    monkeypatch.setattr(authnz_module, "url_for", url_for)
    config = request_config()
    config.mapper = Mapper()
    config.environ = {"SCRIPT_NAME": "/galaxy", "HTTP_HOST": "galaxy.example", "wsgi.url_scheme": "https"}
    yield
    for name in ("mapper", "environ", "protocol", "host"):
        delattr(config, name)


def chosen_redirect_for(cookie_value, allowed_hosts=()):
    trans = StubTrans(cookie_value, allowed_hosts)
    OIDC.callback(None, trans, "keycloak", code="auth-code", state="state-token")
    return trans.login_redirect_url


def test_callback_honors_a_relative_destination():
    assert chosen_redirect_for(LANDING_PATH) == LANDING_PATH


@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.example.com/",
        "//evil.example.com/",
        "/\\evil.example.com/",
        "/\t/evil.example.com",
        "not-a-path",
    ],
)
def test_callback_refuses_to_send_the_user_off_site(hostile):
    assert chosen_redirect_for(hostile) == "/"


@pytest.mark.parametrize("empty", [None, "", "None"])
def test_callback_falls_back_to_root_without_a_destination(empty):
    assert chosen_redirect_for(empty) == "/"


@pytest.mark.parametrize(
    "cookie_value, expected",
    [
        (LANDING_PATH, f"/galaxy{LANDING_PATH}"),
        ("/workflows/ü?name=ü", "/galaxy/workflows/%C3%BC?name=%C3%BC"),
        ("/workflows/%C3%BC", "/galaxy/workflows/%C3%BC"),
        ("https://tools.example.org/back", "https://tools.example.org/back"),
        ("https://tools.example.org/ü", "https://tools.example.org/%C3%BC"),
    ],
)
def test_callback_encodes_the_destination_for_url_for(galaxy_url_prefix, cookie_value, expected):
    assert chosen_redirect_for(cookie_value, allowed_hosts=["tools.example.org"]) == expected


@pytest.mark.parametrize("destination", [LANDING_PATH, "https://tools.example.org/back"])
def test_callback_sends_the_user_to_an_allowed_destination(destination):
    trans = CompletingTrans(destination, allowed_hosts=["tools.example.org"])
    assert OIDC.callback(None, trans, "keycloak", code="auth-code", state="state-token") == destination
    assert trans.get_cookie(LOGIN_NEXT_COOKIE_NAME) == "/"


def test_account_confirmation_sends_the_user_to_an_allowed_destination():
    trans = CompletingTrans("https://tools.example.org/back", allowed_hosts=["tools.example.org"])
    response = OIDC.create_user(object.__new__(OIDC), trans, provider="keycloak")
    assert json.loads(response) == {"redirect_uri": "https://tools.example.org/back"}
    assert trans.get_cookie(LOGIN_NEXT_COOKIE_NAME) == "/"
