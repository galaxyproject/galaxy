"""Tests for ``OIDC.logout`` when third-party login is turned off.

With ``enable_oidc`` disabled the app has no ``authnz_manager``, so the controller has
to answer before it reaches out to one instead of dereferencing ``None``.
"""

from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.controllers.authnz import OIDC

# ``@web.json`` wraps the method; ``_orig`` is the undecorated function.
logout = OIDC.logout._orig


class StubTrans:
    def __init__(self, enable_oidc, authnz_manager):
        self.app = Bunch(
            config=Bunch(enable_oidc=enable_oidc, post_user_logout_href=None),
            authnz_manager=authnz_manager,
        )
        self.logged_out = False

    def handle_user_logout(self):
        self.logged_out = True


def test_logout_reports_when_oidc_is_disabled():
    trans = StubTrans(enable_oidc=False, authnz_manager=None)
    rval = logout(None, trans, "keycloak")
    assert "message" in rval
    assert trans.logged_out is False


def test_logout_delegates_when_oidc_is_enabled():
    manager = Bunch(logout=lambda provider, trans, post_user_logout_href=None: (True, None, "/bye"))
    trans = StubTrans(enable_oidc=True, authnz_manager=manager)
    rval = logout(None, trans, "keycloak")
    assert rval == {"redirect_uri": "/bye"}
    assert trans.logged_out is True
