from datetime import timedelta
from unittest.mock import patch

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
    KNOWN_APPS,
    MAX_SCOPE_LENGTH,
    normalize_user_code,
    OAuthDeviceManager,
    OAuthError,
    POLLING_INTERVAL,
    POLLING_TOLERANCE,
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

    def test_start_authorization_scope_too_long(self):
        with pytest.raises(OAuthError) as e:
            self.manager.start_authorization("galaxy-cli", "x" * (MAX_SCOPE_LENGTH + 1), None)
        assert e.value.error == OAuthErrorCode.INVALID_SCOPE
        self.manager.start_authorization("galaxy-cli", "x" * MAX_SCOPE_LENGTH, None)

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
        with pytest.raises(ObjectNotFound) as e:
            self.manager.get_pending("BBBB-BBBB")
        assert e.value.extra_error_info["reason"] == "unknown"

    def test_get_pending_expired(self):
        user_code = self._start()
        self._get(user_code).expires_at = now() - timedelta(seconds=1)
        self.trans.sa_session.commit()
        with pytest.raises(Conflict, match="expired") as e:
            self.manager.get_pending(user_code)
        assert e.value.extra_error_info["reason"] == "expired"

    def test_get_pending_already_decided(self):
        user_code = self._start()
        self.manager.decide(user_code, self.admin_user, approve=False)
        with pytest.raises(Conflict, match="already been used") as e:
            self.manager.decide(user_code, self.admin_user, approve=True)
        assert e.value.extra_error_info["reason"] == "used"

    def test_start_authorization_retries_a_taken_user_code(self):
        taken = self._start()
        with patch("galaxy.managers.oauth_device.generate_user_code", side_effect=[taken, "BBBB-BBBB"]):
            started = self._start_authorization()
        assert started.authorization.user_code == "BBBB-BBBB"
        assert self._get(taken).status == statuses.PENDING

    def test_cleanup_expired_unapproved(self):
        expired_pending, expired_denied, expired_approved, live_pending = (self._start() for _ in range(4))
        self.manager.decide(expired_denied, self.admin_user, approve=False)
        self.manager.decide(expired_approved, self.admin_user, approve=True)
        for user_code in (expired_pending, expired_denied, expired_approved):
            self._get(user_code).expires_at = now() - timedelta(seconds=1)
        self.trans.sa_session.commit()

        assert self.manager.cleanup_expired_unapproved() >= 2

        remaining = set(self.trans.sa_session.scalars(select(OAuthDeviceAuthorization.user_code)))
        assert expired_pending not in remaining
        assert expired_denied not in remaining
        assert {expired_approved, live_pending} <= remaining

    def test_decide_does_not_overwrite_a_concurrent_decision(self):
        user_code = self._start()
        checked = self.manager.get_pending(user_code)
        # Another request approves after this one already checked the code was pending
        self.manager.decide(user_code, self.admin_user, approve=True)
        with patch.object(self.manager, "get_pending", return_value=checked):
            with pytest.raises(Conflict) as e:
                self.manager.decide(user_code, self.admin_user, approve=False)
        assert e.value.extra_error_info["reason"] == "used"
        assert self._get(user_code).status == statuses.APPROVED

    def test_poll_approved(self):
        started = self._start_authorization(scope="histories:read")
        self.manager.decide(started.authorization.user_code, self.admin_user, approve=True)
        token = self.manager.respond_to_poll("galaxy-cli", started.device_code)
        assert token.access_token == self.app[ApiKeyManager].get_or_create_api_key(self.admin_user)
        assert token.scope == "histories:read"
        assert started.authorization.status == statuses.USED

    def test_poll_used_code_refused(self):
        started = self._start_authorization()
        self.manager.decide(started.authorization.user_code, self.admin_user, approve=True)
        self.manager.respond_to_poll("galaxy-cli", started.device_code)
        self._assert_poll_error(started.device_code, OAuthErrorCode.INVALID_GRANT)

    def test_poll_pending(self):
        started = self._start_authorization()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)
        assert started.authorization.last_polled_at is not None

    def test_poll_slow_down(self):
        started = self._start_authorization()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)
        accepted_at = started.authorization.last_polled_at
        self._assert_poll_error(started.device_code, OAuthErrorCode.SLOW_DOWN)
        # A too-fast poll writes nothing, so the wait still counts from the accepted poll
        assert started.authorization.last_polled_at == accepted_at

    def test_poll_slightly_early_is_accepted(self):
        started = self._start_authorization()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)
        # Within the tolerance: still pending, not `slow_down`
        started.authorization.last_polled_at = now() - timedelta(seconds=POLLING_INTERVAL - POLLING_TOLERANCE / 2)
        self.trans.sa_session.commit()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)
        # Earlier than that: `slow_down`
        started.authorization.last_polled_at = now() - timedelta(seconds=POLLING_INTERVAL - POLLING_TOLERANCE * 2)
        self.trans.sa_session.commit()
        self._assert_poll_error(started.device_code, OAuthErrorCode.SLOW_DOWN)

    def test_poll_pending_after_waiting(self):
        started = self._start_authorization()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)
        started.authorization.last_polled_at = now() - timedelta(seconds=POLLING_INTERVAL)
        self.trans.sa_session.commit()
        self._assert_poll_error(started.device_code, OAuthErrorCode.AUTHORIZATION_PENDING)

    def test_poll_denied(self):
        started = self._start_authorization()
        self.manager.decide(started.authorization.user_code, self.admin_user, approve=False)
        self._assert_poll_error(started.device_code, OAuthErrorCode.ACCESS_DENIED)

    def test_poll_expired_even_if_approved(self):
        started = self._start_authorization()
        self.manager.decide(started.authorization.user_code, self.admin_user, approve=True)
        started.authorization.expires_at = now() - timedelta(seconds=1)
        self.trans.sa_session.commit()
        self._assert_poll_error(started.device_code, OAuthErrorCode.EXPIRED_TOKEN)

    def test_poll_unknown_device_code(self):
        self._assert_poll_error("not-a-real-device-code", OAuthErrorCode.INVALID_GRANT)

    def test_poll_unknown_app(self):
        started = self._start_authorization()
        self._assert_poll_error(started.device_code, OAuthErrorCode.INVALID_CLIENT, client_id="evil-app")

    def test_poll_device_code_of_another_app(self):
        started = self._start_authorization()
        with patch.dict(KNOWN_APPS, {"other-app": "Other App"}):
            self._assert_poll_error(started.device_code, OAuthErrorCode.INVALID_GRANT, client_id="other-app")

    def _start(self) -> str:
        return self.manager.start_authorization("galaxy-cli", None, None).authorization.user_code

    def _get(self, user_code: str) -> OAuthDeviceAuthorization:
        stmt = select(OAuthDeviceAuthorization).where(OAuthDeviceAuthorization.user_code == user_code)
        return self.trans.sa_session.scalars(stmt).one()

    def _start_authorization(self, scope=None):
        return self.manager.start_authorization("galaxy-cli", scope, None)

    def _assert_poll_error(self, device_code, error, client_id="galaxy-cli"):
        with pytest.raises(OAuthError) as e:
            self.manager.respond_to_poll(client_id, device_code)
        assert e.value.error == error


def test_generate_user_code():
    user_code = generate_user_code()
    assert len(user_code) == 9
    assert user_code[4] == "-"
    assert all(c in USER_CODE_ALPHABET for c in user_code.replace("-", ""))


@pytest.mark.parametrize("typed", ["WDJB-MJHT", "wdjb-mjht", "WDJBMJHT", "wdjb mjht", " WdJb-MjHt "])
def test_normalize_user_code(typed):
    assert normalize_user_code(typed) == "WDJB-MJHT"
