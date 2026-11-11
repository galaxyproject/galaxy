"""Integration tests for the OAuth 2.0 device flow endpoints (RFC 8628)."""

import time
from unittest.mock import patch
from urllib.parse import urljoin

from authlib.oauth2.rfc8414 import AuthorizationServerMetadata

from galaxy.managers.oauth_device import (
    KNOWN_APPS,
    POLLING_INTERVAL,
)
from galaxy_test.driver import integration_util

# Written out, not imported, so the tests check the exact value RFC 8628 §3.4 requires.
DEVICE_CODE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


class TestOAuthDeviceFlow(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_oauth_device_flow"] = True

    def test_server_metadata(self):
        response = self._get(urljoin(self.url, ".well-known/oauth-authorization-server"), anon=True)
        self._assert_status_code_is(response, 200)
        metadata = response.json()
        assert metadata["grant_types_supported"] == [DEVICE_CODE_GRANT_TYPE]
        assert metadata["response_types_supported"] == []
        # Valid RFC 8414 metadata, apart from the empty `response_types_supported` Authlib rejects.
        AuthorizationServerMetadata({**metadata, "response_types_supported": ["code"]}).validate()

        # The advertised endpoints are the ones that work.
        response = self._post(metadata["device_authorization_endpoint"], data={"client_id": "galaxy-cli"}, anon=True)
        self._assert_status_code_is(response, 200)
        response = self._token(response.json()["device_code"], url=metadata["token_endpoint"])
        self._assert_oauth_error(response, "authorization_pending")

    def test_start_login(self):
        response = self._start_device_authorization(scope="histories:read tools:run")
        self._assert_status_code_is(response, 200)
        assert response.headers["Cache-Control"] == "no-store"
        body = response.json()
        self._assert_has_keys(body, "device_code", "user_code", "verification_uri", "expires_in", "interval")
        assert "verification_uri_complete" not in body
        assert body["verification_uri"].endswith("/login/device")
        assert body["expires_in"] == 900
        assert body["interval"] == 5

    def test_start_login_unknown_app(self):
        response = self._start_device_authorization(client_id="evil-app")
        self._assert_oauth_error(response, "invalid_client")

    def test_start_login_missing_client_id(self):
        response = self._post("oauth/device_authorization", data={}, anon=True)
        self._assert_oauth_error(response, "invalid_request")

    def test_get(self):
        user_code = self._start_device_authorization(scope="histories:read tools:run").json()["user_code"]
        response = self._get(f"oauth/device_authorization/{user_code.lower()}")
        self._assert_status_code_is(response, 200)
        details = response.json()
        assert details["user_code"] == user_code
        assert details["client_id"] == "galaxy-cli"
        assert details["app_name"] == "Galaxy CLI"
        assert details["scopes"] == ["histories:read", "tools:run"]
        self._assert_has_keys(details, "requesting_ip", "create_time", "expires_at")

    def test_get_for_an_app_no_longer_known(self):
        user_code = self._start_device_authorization().json()["user_code"]
        with patch.dict(KNOWN_APPS, clear=True):
            response = self._get(f"oauth/device_authorization/{user_code}")
        self._assert_status_code_is(response, 200)
        assert response.json()["app_name"] == "galaxy-cli"

    def test_get_without_scope(self):
        user_code = self._start_device_authorization().json()["user_code"]
        assert self._get(f"oauth/device_authorization/{user_code}").json()["scopes"] == []

    def test_get_after_decision(self):
        user_code = self._start_device_authorization().json()["user_code"]
        self._decide_device_authorization(user_code, approve=True)
        response = self._get(f"oauth/device_authorization/{user_code}")
        self._assert_status_code_is(response, 409)
        assert response.json()["reason"] == "used"

    def test_get_unknown_code(self):
        response = self._get("oauth/device_authorization/BBBB-BBBB")
        self._assert_status_code_is(response, 404)
        assert response.json()["reason"] == "unknown"

    def test_get_requires_login(self):
        user_code = self._start_device_authorization().json()["user_code"]
        self._assert_status_code_is(self._get(f"oauth/device_authorization/{user_code}", anon=True), 403)

    def test_approve(self):
        user_code = self._start_device_authorization().json()["user_code"]
        response = self._decide_device_authorization(user_code, approve=True)
        self._assert_status_code_is(response, 204)

    def test_deny(self):
        user_code = self._start_device_authorization().json()["user_code"]
        response = self._decide_device_authorization(user_code, approve=False)
        self._assert_status_code_is(response, 204)

    def test_decide_accepts_loosely_typed_code(self):
        user_code = self._start_device_authorization().json()["user_code"]
        response = self._decide_device_authorization(user_code.lower().replace("-", ""), approve=True)
        self._assert_status_code_is(response, 204)

    def test_decide_twice(self):
        user_code = self._start_device_authorization().json()["user_code"]
        self._assert_status_code_is(self._decide_device_authorization(user_code, approve=True), 204)
        response = self._decide_device_authorization(user_code, approve=True)
        self._assert_status_code_is(response, 409)
        assert "already been used" in response.json()["err_msg"]
        assert response.json()["reason"] == "used"

    def test_decide_unknown_code(self):
        response = self._decide_device_authorization("BBBB-BBBB", approve=True)
        self._assert_status_code_is(response, 404)
        assert response.json()["reason"] == "unknown"

    def test_decide_requires_login(self):
        user_code = self._start_device_authorization().json()["user_code"]
        response = self._put(f"oauth/device_authorization/{user_code}", data={"approve": True}, anon=True, json=True)
        self._assert_status_code_is(response, 403)

    def test_token(self):
        started = self._start_device_authorization(scope="histories:read").json()
        self._decide_device_authorization(started["user_code"], approve=True)
        response = self._token(started["device_code"])
        self._assert_status_code_is(response, 200)
        assert response.headers["Cache-Control"] == "no-store"
        body = response.json()
        assert body["token_type"] == "Bearer"
        assert body["scope"] == "histories:read"
        assert "expires_in" not in body

        # The token works with the Galaxy API, as the user who approved the login.
        me = self._get("users/current", key=body["access_token"]).json()
        assert me["id"] == self._get("users/current").json()["id"]

    def test_token_used_twice(self):
        started = self._start_device_authorization().json()
        self._decide_device_authorization(started["user_code"], approve=True)
        self._assert_status_code_is(self._token(started["device_code"]), 200)
        self._assert_oauth_error(self._token(started["device_code"]), "invalid_grant")

    def test_token_pending_then_slow_down(self):
        device_code = self._start_device_authorization().json()["device_code"]
        self._assert_oauth_error(self._token(device_code), "authorization_pending")
        self._assert_oauth_error(self._token(device_code), "slow_down")

    def test_token_polling_until_approved(self):
        # Polls at the given interval, as an app would, while the user takes their time to approve.
        started = self._start_device_authorization().json()
        self._assert_oauth_error(self._token(started["device_code"]), "authorization_pending")
        time.sleep(POLLING_INTERVAL)
        self._assert_oauth_error(self._token(started["device_code"]), "authorization_pending")
        self._decide_device_authorization(started["user_code"], approve=True)
        time.sleep(POLLING_INTERVAL)
        self._assert_status_code_is(self._token(started["device_code"]), 200)

    def test_token_denied(self):
        started = self._start_device_authorization().json()
        self._decide_device_authorization(started["user_code"], approve=False)
        self._assert_oauth_error(self._token(started["device_code"]), "access_denied")

    def test_token_unknown_device_code(self):
        self._assert_oauth_error(self._token("not-a-real-device-code"), "invalid_grant")

    def test_token_unknown_app(self):
        device_code = self._start_device_authorization().json()["device_code"]
        self._assert_oauth_error(self._token(device_code, client_id="evil-app"), "invalid_client")

    def test_token_unsupported_grant_type(self):
        response = self._token("x", grant_type="password")
        self._assert_oauth_error(response, "unsupported_grant_type")

    def test_token_missing_fields(self):
        response = self._post("oauth/token", data={"client_id": "galaxy-cli"}, anon=True)
        self._assert_oauth_error(response, "invalid_request")

    def _start_device_authorization(self, client_id="galaxy-cli", scope=None):
        data = {"client_id": client_id}
        if scope:
            data["scope"] = scope
        # Form-encoded and without an API key, as an OAuth app sends it.
        return self._post("oauth/device_authorization", data=data, anon=True)

    def _decide_device_authorization(self, user_code, approve):
        return self._put(f"oauth/device_authorization/{user_code}", data={"approve": approve}, json=True)

    def _token(self, device_code, client_id="galaxy-cli", grant_type=DEVICE_CODE_GRANT_TYPE, url="oauth/token"):
        data = {"grant_type": grant_type, "device_code": device_code, "client_id": client_id}
        return self._post(url, data=data, anon=True)

    def _assert_oauth_error(self, response, error):
        self._assert_status_code_is(response, 400)
        assert response.json()["error"] == error
        assert response.headers["Cache-Control"] == "no-store"


class TestOAuthDeviceFlowDisabled(integration_util.IntegrationTestCase):
    def test_endpoints_not_found(self):
        response = self._get(urljoin(self.url, ".well-known/oauth-authorization-server"), anon=True)
        self._assert_status_code_is(response, 404)
        response = self._post("oauth/device_authorization", data={"client_id": "galaxy-cli"}, anon=True)
        self._assert_status_code_is(response, 404)
        # Flow off is a 404 without a `reason`, so the page doesn't mistake it for an unknown code.
        response = self._get("oauth/device_authorization/BBBB-BBBB")
        self._assert_status_code_is(response, 404)
        assert "reason" not in response.json()
        response = self._put("oauth/device_authorization/BBBB-BBBB", data={"approve": True}, json=True)
        self._assert_status_code_is(response, 404)
        response = self._post("oauth/token", data={"client_id": "galaxy-cli"}, anon=True)
        self._assert_status_code_is(response, 404)
