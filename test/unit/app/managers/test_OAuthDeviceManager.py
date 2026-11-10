from datetime import timedelta

import pytest
from sqlalchemy import select

from galaxy.exceptions import (
    Conflict,
    ObjectNotFound,
)
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.oauth_device import (
    DEVICE_CODE_EXPIRES_IN,
    generate_user_code,
    hash_device_code,
    normalize_user_code,
    OAuthDeviceManager,
    OAuthError,
    USER_CODE_ALPHABET,
)
from galaxy.model import OAuthDeviceAuthorization
from galaxy.schema.oauth import OAuthErrorCode
from galaxy.util import now
from .base import BaseTestCase

statuses = OAuthDeviceAuthorization.statuses


class TestOAuthDeviceManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.manager = OAuthDeviceManager(self.trans.sa_session, self.app[ApiKeyManager])

    def test_start_authorization(self):
        started = self.manager.start_authorization("galaxy-cli", "histories:read", "203.0.113.7")
        authorization = started.authorization
        assert authorization.status == statuses.PENDING
        assert authorization.client_id == "galaxy-cli"
        assert authorization.scope == "histories:read"
        assert authorization.requesting_ip == "203.0.113.7"
        assert authorization.user is None
        expires_in = (authorization.expires_at - now()).total_seconds()
        assert DEVICE_CODE_EXPIRES_IN - 60 < expires_in <= DEVICE_CODE_EXPIRES_IN

    def test_start_authorization_stores_only_device_code_hash(self):
        started = self.manager.start_authorization("galaxy-cli", None, None)
        assert started.authorization.device_code_hash == hash_device_code(started.device_code)
        assert started.authorization.device_code_hash != started.device_code

    def test_start_authorization_unknown_app(self):
        with pytest.raises(OAuthError) as e:
            self.manager.start_authorization("evil-app", None, None)
        assert e.value.error == OAuthErrorCode.INVALID_CLIENT

    def test_approve(self):
        user_code = self._start()
        self.manager.decide(user_code, self.admin_user, approve=True)
        authorization = self._get(user_code)
        assert authorization.status == statuses.APPROVED
        assert authorization.user == self.admin_user

    def test_deny(self):
        user_code = self._start()
        self.manager.decide(user_code, self.admin_user, approve=False)
        authorization = self._get(user_code)
        assert authorization.status == statuses.DENIED
        assert authorization.user == self.admin_user

    def test_decide_accepts_loosely_typed_code(self):
        user_code = self._start()
        self.manager.decide(user_code.lower().replace("-", " "), self.admin_user, approve=True)
        assert self._get(user_code).status == statuses.APPROVED

    def test_get_pending_unknown_code(self):
        with pytest.raises(ObjectNotFound):
            self.manager.get_pending("BBBB-BBBB")

    def test_get_pending_expired(self):
        user_code = self._start()
        self._get(user_code).expires_at = now() - timedelta(seconds=1)
        self.trans.sa_session.commit()
        with pytest.raises(Conflict, match="expired"):
            self.manager.get_pending(user_code)

    def test_get_pending_already_decided(self):
        user_code = self._start()
        self.manager.decide(user_code, self.admin_user, approve=False)
        with pytest.raises(Conflict, match="already been used"):
            self.manager.decide(user_code, self.admin_user, approve=True)

    def _start(self) -> str:
        return self.manager.start_authorization("galaxy-cli", None, None).authorization.user_code

    def _get(self, user_code: str) -> OAuthDeviceAuthorization:
        stmt = select(OAuthDeviceAuthorization).where(OAuthDeviceAuthorization.user_code == user_code)
        return self.trans.sa_session.scalars(stmt).one()


def test_generate_user_code():
    user_code = generate_user_code()
    assert len(user_code) == 9
    assert user_code[4] == "-"
    assert all(c in USER_CODE_ALPHABET for c in user_code.replace("-", ""))


@pytest.mark.parametrize("typed", ["WDJB-MJHT", "wdjb-mjht", "WDJBMJHT", "wdjb mjht", " WdJb-MjHt "])
def test_normalize_user_code(typed):
    assert normalize_user_code(typed) == "WDJB-MJHT"
