"""Tests for ``User.logout``: the ``logout_all`` query parameter arrives as a string."""

import pytest

from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.controllers.user import User

# ``@web.json`` wraps the method; ``_orig`` is the undecorated function.
logout = User.logout._orig


class StubTrans:
    def __init__(self):
        self.app = Bunch(config=Bunch(use_remote_user=False, remote_user_logout_href=None))
        self.logout_all = None

    def check_csrf_token(self, payload):
        return None

    def log_event(self, message):
        pass

    def handle_user_logout(self, logout_all=False):
        self.logout_all = logout_all


@pytest.mark.parametrize(
    "kwd, expected",
    [
        ({}, False),
        ({"logout_all": "false"}, False),
        ({"logout_all": "False"}, False),
        ({"logout_all": "true"}, True),
        ({"logout_all": True}, True),
    ],
)
def test_logout_parses_logout_all(kwd, expected):
    trans = StubTrans()
    rval = logout(None, trans, session_csrf_token="token", **kwd)
    assert rval == {"message": "Success."}
    assert trans.logout_all is expected
