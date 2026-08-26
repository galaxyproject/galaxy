"""Unit tests for the ``root`` controller's ``/login`` entry point.

When a Galaxy instance delegates authentication to a single OIDC provider, ``/login``
bounces the browser straight at that provider. Where the user was originally headed has
to be stashed in the login-next cookie *before* that bounce, because the OIDC callback
has no other way to recover it -- see ``OIDC.callback`` in the ``authnz`` controller.
"""

import pytest

from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.controllers.authnz import LOGIN_NEXT_COOKIE_NAME
from galaxy.webapps.galaxy.controllers.root import RootController

IDP_URL = "https://idp.example.org/authorize?client_id=galaxy"
LANDING_PATH = "/tool_landings/1234-5678?public=true"


class StubTrans:
    """The slice of the transaction interface ``RootController.login`` actually touches."""

    def __init__(self, authenticators=(), oidc_providers=("tapis",)):
        self.cookies: dict[str, str] = {}
        self.redirected_to: str | None = None
        self.app = Bunch(
            config=Bunch(enable_oidc=True, oidc={name: {} for name in oidc_providers}),
            auth_manager=Bunch(authenticators=list(authenticators)),
            authnz_manager=Bunch(authenticate=lambda provider, trans: (True, "", IDP_URL)),
        )
        self.response = Bunch(send_redirect=self._send_redirect)

    def _send_redirect(self, url):
        self.redirected_to = url
        return url

    def set_cookie(self, value, name="galaxysession", **kwd):
        self.cookies[name] = value


def login(trans, **kwd):
    # ``login`` never touches ``self``, so there is no controller to build here.
    return RootController.login(None, trans, **kwd)


def test_single_provider_login_stashes_destination_before_bouncing_to_idp():
    trans = StubTrans()
    login(trans, redirect=LANDING_PATH)
    assert trans.redirected_to == IDP_URL
    assert trans.cookies[LOGIN_NEXT_COOKIE_NAME] == LANDING_PATH


def test_single_provider_login_without_destination_defaults_to_root():
    trans = StubTrans()
    login(trans)
    assert trans.redirected_to == IDP_URL
    assert trans.cookies[LOGIN_NEXT_COOKIE_NAME] == "/"


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
def test_single_provider_login_refuses_offsite_destination(hostile):
    trans = StubTrans()
    login(trans, redirect=hostile)
    assert trans.cookies[LOGIN_NEXT_COOKIE_NAME] == "/"


def test_multiple_providers_fall_through_to_the_login_page(monkeypatch):
    # More than one provider means Galaxy has to ask which one, so no cookie is set here;
    # the client passes the destination along when the user picks a provider.
    monkeypatch.setattr("galaxy.web.url_for", lambda **kwd: f"/login/start?redirect={kwd.get('redirect')}")
    trans = StubTrans(oidc_providers=("tapis", "keycloak"))
    login(trans, redirect=LANDING_PATH)
    assert trans.redirected_to is not None
    assert "login/start" in trans.redirected_to
    assert LOGIN_NEXT_COOKIE_NAME not in trans.cookies
