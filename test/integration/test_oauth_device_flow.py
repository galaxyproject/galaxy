"""Integration tests for the OAuth 2.0 device flow endpoints (RFC 8628)."""

from galaxy_test.driver import integration_util


class TestOAuthDeviceFlow(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_oauth_device_flow"] = True

    def test_start_login(self):
        response = self._start_device_authorization(scope="histories:read tools:run")
        self._assert_status_code_is(response, 200)
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

    def test_decide_unknown_code(self):
        response = self._decide_device_authorization("BBBB-BBBB", approve=True)
        self._assert_status_code_is(response, 404)

    def test_decide_requires_login(self):
        user_code = self._start_device_authorization().json()["user_code"]
        response = self._put(f"oauth/device_authorization/{user_code}", data={"approve": True}, anon=True, json=True)
        self._assert_status_code_is(response, 403)

    def _start_device_authorization(self, client_id="galaxy-cli", scope=None):
        data = {"client_id": client_id}
        if scope:
            data["scope"] = scope
        # Form-encoded and without an API key, as an OAuth app sends it.
        return self._post("oauth/device_authorization", data=data, anon=True)

    def _decide_device_authorization(self, user_code, approve):
        return self._put(f"oauth/device_authorization/{user_code}", data={"approve": approve}, json=True)

    def _assert_oauth_error(self, response, error):
        self._assert_status_code_is(response, 400)
        assert response.json()["error"] == error


class TestOAuthDeviceFlowDisabled(integration_util.IntegrationTestCase):
    def test_endpoints_not_found(self):
        response = self._post("oauth/device_authorization", data={"client_id": "galaxy-cli"}, anon=True)
        self._assert_status_code_is(response, 404)
        response = self._put("oauth/device_authorization/BBBB-BBBB", data={"approve": True}, json=True)
        self._assert_status_code_is(response, 404)
