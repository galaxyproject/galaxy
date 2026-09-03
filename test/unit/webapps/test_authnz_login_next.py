"""Tests for how the OIDC callback consumes the login-next cookie.

This is the point where an attacker-supplied value becomes a redirect, so it is where
the destination has to be validated -- doing it here covers every writer of the cookie,
including the ``next`` parameter accepted by ``OIDC.login``.
"""

import pytest

from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.controllers import authnz as authnz_module
from galaxy.webapps.galaxy.controllers.authnz import (
    LOGIN_NEXT_COOKIE_NAME,
    OIDC,
)

LANDING_PATH = "/tool_landings/1234-5678?public=true"


class StubTrans:
    """The slice of the transaction interface ``OIDC.callback`` touches before it stops."""

    def __init__(self, login_next_cookie: str | None):
        self.user = None
        self._cookies = {LOGIN_NEXT_COOKIE_NAME: login_next_cookie}
        self.login_redirect_url: str | None = None
        self.app = Bunch(authnz_manager=Bunch(callback=self._callback))

    def get_cookie(self, name):
        return self._cookies.get(name)

    def _callback(self, provider, state, code, trans, login_redirect_url=None, idphint=None):
        # Record what the controller decided, then stop the flow.
        self.login_redirect_url = login_redirect_url
        return False, "halt", (None, None)

    def show_error_message(self, message):
        return message


@pytest.fixture(autouse=True)
def passthrough_url_for(monkeypatch):
    # url_for needs a live routes config; the decision under test is which value it gets.
    monkeypatch.setattr(authnz_module, "url_for", lambda path: path)


def chosen_redirect_for(cookie_value):
    trans = StubTrans(cookie_value)
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
