"""Integration tests for the CLI shell plugins and runners."""

import html
import os
import re
import subprocess
import tempfile
import time
from string import Template
from typing import (
    ClassVar,
    Union,
)
from unittest.mock import (
    _patch,
    patch,
)
from urllib import parse

from galaxy import model
from galaxy.authnz.psa_authnz import PSAAuthnz
from galaxy.util import requests
from galaxy_test.base.api import ApiTestInteractor
from galaxy_test.driver import integration_util

KEYCLOAK_ADMIN_USERNAME = "admin"
KEYCLOAK_ADMIN_PASSWORD = "admin"
KEYCLOAK_TEST_USERNAME = "gxyuser"
KEYCLOAK_TEST_PASSWORD = "gxypass"
KEYCLOAK_HOST_PORT = 9443
KEYCLOAK_URL = f"https://localhost:{KEYCLOAK_HOST_PORT}/realms/gxyrealm"


# NOTE: redirect_uri has to include the current Galaxy
#   port, so we set it to a dummy value initially
#   and patch it when the tests are running
OIDC_BACKEND_CONFIG_TEMPLATE = f"""<?xml version="1.0"?>
<OIDC>
    <provider name="$provider_name">
        <url>{KEYCLOAK_URL}</url>
        <oidc_endpoint>{KEYCLOAK_URL}</oidc_endpoint>
        <client_id>gxyclient</client_id>
        <client_secret>dummyclientsecret</client_secret>
        <redirect_uri>dummy_url</redirect_uri>
        <enable_idp_logout>true</enable_idp_logout>
        <accepted_audiences>gxyclient</accepted_audiences>
    </provider>
</OIDC>
"""

# Debug authentication pipeline that saves access token data
#   for testing
DEBUG_AUTH_PIPELINE_EXTRA = ("galaxy.authnz.util.debug_access_token_data",)


def wait_till_app_ready(url, timeout=60):
    import time

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, verify=False, timeout=(1, 5))
            if response.status_code in (200, 302):  # allow redirect to login etc.
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"Keycloak did not become ready in {timeout} seconds")


def start_keycloak_docker(container_name, image="keycloak/keycloak:26.2"):
    keycloak_realm_data = os.path.dirname(__file__)
    START_SLURM_DOCKER = [
        "docker",
        "run",
        "-p",
        f"{KEYCLOAK_HOST_PORT}:8443",
        "-d",
        "--name",
        container_name,
        "--rm",
        "-v",
        f"{keycloak_realm_data}:/opt/keycloak/data/import",
        "-e",
        f"KC_BOOTSTRAP_ADMIN_USERNAME={KEYCLOAK_ADMIN_USERNAME}",
        "-e",
        f"KC_BOOTSTRAP_ADMIN_PASSWORD={KEYCLOAK_ADMIN_PASSWORD}",
        "-e",
        "KC_HOSTNAME_STRICT=false",
        image,
        "start",
        "--import-realm",
        "--https-certificate-file=/opt/keycloak/data/import/keycloak-server.crt.pem",
        "--https-certificate-key-file=/opt/keycloak/data/import/keycloak-server.key.pem",
    ]
    subprocess.check_call(START_SLURM_DOCKER)
    wait_till_app_ready(f"{KEYCLOAK_URL}/.well-known/openid-configuration")


def stop_keycloak_docker(container_name):
    subprocess.check_call(["docker", "rm", "-f", container_name])


class AbstractTestCases:
    @integration_util.skip_unless_docker()
    class BaseKeycloakIntegrationTestCase(integration_util.IntegrationTestCase):
        # regex to find the action attribute on the HTML login page
        #   returned by Keycloak
        REGEX_KEYCLOAK_LOGIN_ACTION = re.compile(r"action=\"(.*?)\"\s+")
        REGEX_GALAXY_CSRF_TOKEN = re.compile(r"session_csrf_token = \"(.*)\"")
        container_name: ClassVar[str]
        backend_config_file: ClassVar[str]
        provider_name: ClassVar[str]
        saved_env_vars: ClassVar[dict[str, Union[str, None]]]
        config_patcher: ClassVar[_patch]

        @classmethod
        def setUpClass(cls):
            cls.backend_config_file = cls.generate_oidc_config_file(provider_name=cls.provider_name)
            # Patch the OIDC implementation so it can get the
            # current Galaxy port to set the redirect_uri
            cls.patch_oidc_config()

            # By default, the oidc callback must be done over a secure transport, so
            # we forcibly disable it for now
            cls.disableOauthlibHttps()
            cls.container_name = f"{cls.__name__}_container"
            start_keycloak_docker(container_name=cls.container_name)

            super().setUpClass()
            # Restart the test driver to parse the OIDC config file
            cls._test_driver.restart(config_object=cls, handle_config=cls.handle_galaxy_oidc_config_kwds)

        @classmethod
        def patch_oidc_config(cls):
            """
            Define this in subclasses to patch the relevant OIDC implementation:
            need to supply the current host and port for the redirect_uri
            setting
            """
            pass

        @classmethod
        def generate_oidc_config_file(cls, provider_name="keycloak"):
            with tempfile.NamedTemporaryFile("w+t", delete=False) as tmp_file:
                data = Template(OIDC_BACKEND_CONFIG_TEMPLATE).safe_substitute(
                    provider_name=provider_name,
                )
                tmp_file.write(data)
                return tmp_file.name

        @classmethod
        def tearDownClass(cls):
            stop_keycloak_docker(cls.container_name)
            cls.restoreOauthlibHttps()
            os.remove(cls.backend_config_file)

            cls.config_patcher.stop()

            super().tearDownClass()

        @classmethod
        def disableOauthlibHttps(cls):
            env_vars = {
                "OAUTHLIB_INSECURE_TRANSPORT": "true",
                "REQUESTS_CA_BUNDLE": os.path.dirname(__file__) + "/keycloak-server.crt.pem",
                "SSL_CERT_FILE": os.path.dirname(__file__) + "/keycloak-server.crt.pem",
            }
            cls.saved_env_vars = {key: os.environ.get(key) for key in env_vars}
            os.environ.update(env_vars)

        @classmethod
        def restoreOauthlibHttps(cls):
            for key, value in cls.saved_env_vars.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    del os.environ[key]

        @classmethod
        def handle_galaxy_oidc_config_kwds(cls, config):
            config["enable_oidc"] = True
            config["oidc_config_file"] = os.path.join(os.path.dirname(__file__), "oidc_config.xml")
            config["oidc_backends_config_file"] = cls.backend_config_file
            config["oidc_auth_pipeline_extra"] = DEBUG_AUTH_PIPELINE_EXTRA

        def _get_interactor(self, api_key=None, allow_anonymous=False) -> "ApiTestInteractor":
            return super()._get_interactor(api_key=None, allow_anonymous=True)

        def _login_via_keycloak(self, username, password, expected_codes=None, save_cookies=False, session=None):

            if expected_codes is None:
                expected_codes = [200, 404]
            session = session or requests.Session()
            response = session.get(f"{self.url}authnz/{self.provider_name}/login")
            provider_url = response.json()["redirect_uri"]
            response = session.get(provider_url, verify=False)
            matches = self.REGEX_KEYCLOAK_LOGIN_ACTION.search(response.text)
            assert matches
            auth_url = html.unescape(str(matches.group(1)))
            response = session.post(auth_url, data={"username": username, "password": password}, verify=False)
            assert response.status_code in expected_codes, response
            if save_cookies:
                self.galaxy_interactor.cookies = session.cookies
            return session, response


class TestGalaxyOIDCLoginIntegration(AbstractTestCases.BaseKeycloakIntegrationTestCase):
    """
    Test Galaxy's keycloak-based OIDC login integration.

    This test now uses the unified PSA-based Keycloak backend.
    """

    provider_name = "keycloak"

    @classmethod
    def patch_oidc_config(cls):
        """
        Patch PSAAuthnz to set the redirect_uri dynamically based on the test server port.

        This is necessary because the redirect_uri must match the actual Galaxy URL,
        which is only known at test runtime.
        """
        # Save a reference to the original init function
        psa_authnz_init = PSAAuthnz.__init__

        def patched_psa_authnz_init(self, *args, **kwargs):
            server_wrapper = cls._test_driver.server_wrappers[0]
            psa_authnz_init(self, *args, **kwargs)
            # Only patch if this is the keycloak provider
            if self.config.get("provider") == cls.provider_name:
                self.config["redirect_uri"] = (
                    f"http://{server_wrapper.host}:{server_wrapper.port}/authnz/{cls.provider_name}/callback"
                )

        cls.config_patcher = patch("galaxy.authnz.psa_authnz.PSAAuthnz.__init__", patched_psa_authnz_init)
        cls.config_patcher.start()

    def _get_keycloak_access_token(
        self, client_id="gxyclient", username=KEYCLOAK_TEST_USERNAME, password=KEYCLOAK_TEST_PASSWORD, scopes=None
    ):
        data = {
            "client_id": client_id,
            "client_secret": "dummyclientsecret",
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": scopes or [],
        }
        response = requests.post(f"{KEYCLOAK_URL}/protocol/openid-connect/token", data=data, verify=False)
        return response.json()["access_token"]

    def test_oidc_login_new_user(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)
        # Should have redirected back if auth succeeded
        parsed_url = parse.urlparse(response.url)
        notification = parse.parse_qs(parsed_url.query)["notification"][0]
        assert "Your Keycloak identity has been linked to your Galaxy account." in notification
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser@galaxy.org"

    def test_oidc_login_username_sanitization(self):
        """Test that OIDC usernames with special characters are properly sanitized."""
        _, response = self._login_via_keycloak("rincewind_test", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "rincewind@galaxy.org"

        username = response.json()["username"]
        from galaxy.security.validate_user_input import validate_publicname_str

        error = validate_publicname_str(username)
        assert error == "", f"OIDC-created username '{username}' is invalid: {error}"
        assert "(" not in username, f"Username '{username}' should not contain parentheses"
        assert ")" not in username, f"Username '{username}' should not contain parentheses"
        assert " " not in username, f"Username '{username}' should not contain spaces"
        assert username == username.lower(), f"Username '{username}' should be lowercase"

    def test_oidc_login_repeat_no_notification(self):
        """
        Test that repeat logins do NOT show the 'identity has been linked' notification.
        """
        # If this is the first time gxyuser logs in, it will show notification
        # Otherwise (if test_oidc_login_new_user ran first), it won't
        # Either way, the second login should NOT show notification

        # First login in this test
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # Second login (repeat) - should NOT show notification
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)
        parsed_url = parse.urlparse(response.url)
        query_params = parse.parse_qs(parsed_url.query)
        assert "notification" not in query_params, "Repeat login should not show 'linked' notification"

        # Verify user is still logged in
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser@galaxy.org"

    def test_oidc_login_existing_user(self):
        # pre-create a user account manually
        sa_session = self._app.model.session
        user = model.User(email="gxyuser_existing@galaxy.org", username="precreated_user")
        user.set_password_cleartext("test123")
        sa_session.add(user)
        try:
            sa_session.commit()
        except Exception:
            # User already exists
            pass

        # login with the corresponding OIDC user
        _, response = self._login_via_keycloak("gxyuser_existing", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # Should prompt user to associate accounts
        parsed_url = parse.urlparse(response.url)
        provider = parse.parse_qs(parsed_url.query)["connect_external_provider"][0]
        assert "keycloak" == provider

        # user should not have been logged in
        response = self._get("users/current")
        assert "id" not in response.json()

    def test_oidc_login_decode_access_token(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser@galaxy.org"

        sa_session = self._app.model.session
        user = sa_session.query(model.User).filter_by(email="gxyuser@galaxy.org").one()
        social = next((s for s in user.social_auth if s.provider == "keycloak"), None)
        assert social is not None
        extra_data = social.extra_data
        assert extra_data is not None
        assert "access_token_decoded" in extra_data
        assert "realm_access" in extra_data["access_token_decoded"]

    def test_oidc_login_account_linkup(self):
        # pre-create a user account manually
        sa_session = self._app.model.session
        user = model.User(email="gxyuser_existing@galaxy.org", username="precreated_user")
        user.set_password_cleartext("test123")
        sa_session.add(user)
        try:
            sa_session.commit()
        except Exception:
            # User already exists
            pass

        # establish a web session
        session = requests.Session()
        response = session.get(self._api_url("../login/start"))
        matches = self.REGEX_GALAXY_CSRF_TOKEN.search(response.text)
        assert matches
        session_csrf_token = str(matches.groups(1)[0])
        response = session.post(
            self._api_url("../user/login"),
            data={
                "login": "gxyuser_existing@galaxy.org",
                "password": "test123",
                "session_csrf_token": session_csrf_token,
            },
        )

        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_existing@galaxy.org"
        assert response.json()["username"] == "precreated_user"

        # login with the corresponding OIDC user, while preserving the current session
        _, response = self._login_via_keycloak(
            "gxyuser_existing", KEYCLOAK_TEST_PASSWORD, save_cookies=True, session=session
        )

        # Should now automatically associate account
        parsed_url = parse.urlparse(response.url)
        notification = parse.parse_qs(parsed_url.query)["notification"][0]
        assert "Your Keycloak identity has been linked to your Galaxy account." in notification
        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_existing@galaxy.org"
        assert response.json()["username"] == "precreated_user"

        # Now that the accounts are associated, future logins through OIDC should just work
        session, response = self._login_via_keycloak("gxyuser_existing", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # On repeat login, should NOT show the "linked" notification
        parsed_url = parse.urlparse(response.url)
        query_params = parse.parse_qs(parsed_url.query)
        assert "notification" not in query_params, "Repeat login should not show 'linked' notification"

        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_existing@galaxy.org"
        assert response.json()["username"] == "precreated_user"

    def test_oidc_logout(self):
        # login
        session, _ = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)
        # get the user
        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        # now logout
        response = session.get(self._api_url("../authnz/logout"))
        response = session.get(response.json()["redirect_uri"], verify=False)
        # make sure we can no longer request the user
        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert "email" not in response.json()

    def test_auth_by_access_token_logged_in_once(self):
        # login at least once
        self._login_via_keycloak("gxyuser_logged_in_once", KEYCLOAK_TEST_PASSWORD)
        access_token = self._get_keycloak_access_token(username="gxyuser_logged_in_once")
        response = self._get("whoami", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_logged_in_once@galaxy.org"

    def test_auth_by_access_token_never_logged_in(self):
        # If the user has not previously logged in via OIDC at least once, OIDC API calls are not allowed
        access_token = self._get_keycloak_access_token(username="gxyuser_never_logged_in")
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 401)
        assert "The user should log into Galaxy at least once" in response.json()["err_msg"]

    def test_auth_with_expired_token(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD)
        access_token = self._get_keycloak_access_token()
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 200)
        # token shouldn't expire in 3 seconds, so the call should succeed
        time.sleep(3)
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 200)
        # token should have expired in 7 seconds, so the call should fail
        time.sleep(7)
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 401)

    def test_auth_with_another_authorized_client(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD)
        access_token = self._get_keycloak_access_token(
            client_id="bpaclient", scopes=["https://galaxyproject.org/api:*"]
        )
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser@galaxy.org"

    def test_auth_with_authorized_client_but_unauthorized_audience(self):
        _, response = self._login_via_keycloak("bpaonlyuser", KEYCLOAK_TEST_PASSWORD)
        access_token = self._get_keycloak_access_token(client_id="bpaclient", username="bpaonlyuser")
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 401)
        assert "Invalid access token" in response.json()["err_msg"]

    def test_auth_with_unauthorized_client(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD)
        access_token = self._get_keycloak_access_token(client_id="unauthorizedclient")
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 401)
        assert "Invalid access token" in response.json()["err_msg"]

    def test_auth_without_required_scopes(self):
        access_token = self._get_keycloak_access_token(client_id="bpaclient")
        response = self._get("users/current", headers={"Authorization": f"Bearer {access_token}"})
        self._assert_status_code_is(response, 401)
        assert "Invalid access token" in response.json()["err_msg"]


class TestFixedDelegatedAuthIntegration(AbstractTestCases.BaseKeycloakIntegrationTestCase):
    """
    Integration tests for fixed_delegated_auth functionality.

    Tests the complete authentication flow with different combinations of:
    - User logged in vs not logged in (trans.user)
    - Existing Galaxy user with matching email vs no user
    - fixed_delegated_auth enabled vs disabled
    - require_create_confirmation enabled vs disabled

    This ensures the PSA implementation matches the original custos behavior.
    """

    provider_name = "keycloak"

    @classmethod
    def patch_oidc_config(cls):
        psa_authnz_init = PSAAuthnz.__init__

        def patched_psa_authnz_init(self, *args, **kwargs):
            server_wrapper = cls._test_driver.server_wrappers[0]
            psa_authnz_init(self, *args, **kwargs)
            if self.config.get("provider") == cls.provider_name:
                self.config["redirect_uri"] = (
                    f"http://{server_wrapper.host}:{server_wrapper.port}/authnz/{cls.provider_name}/callback"
                )

        cls.config_patcher = patch("galaxy.authnz.psa_authnz.PSAAuthnz.__init__", patched_psa_authnz_init)
        cls.config_patcher.start()

    @classmethod
    def handle_galaxy_oidc_config_kwds(cls, config):
        config["enable_oidc"] = True
        config["oidc_config_file"] = os.path.join(os.path.dirname(__file__), "oidc_config.xml")
        config["oidc_backends_config_file"] = cls.backend_config_file
        # fixed_delegated_auth will be automatically computed as True when:
        # - There is exactly one OIDC provider (keycloak)
        # - There are no other authenticators configured
        # Use empty auth_config_file to ensure no authenticators are loaded
        config["auth_config_file"] = os.path.join(os.path.dirname(__file__), "auth_conf_empty.xml")

    def test_fixed_delegated_auth_with_existing_user_auto_associates(self):
        """
        Test: fixed_delegated_auth=True, user NOT logged in, existing user with matching email
        Expected: Auto-associate OIDC with existing user, redirect to root (not user/external_ids)

        This matches custos lines 236-237, 268-269:
        - if fixed_delegated_auth: user = existing_user
        - redirect to login_redirect_url (root)
        """
        # Pre-create a Galaxy user with matching email
        sa_session = self._app.model.session
        user = model.User(email="gxyuser_fixed_auth@galaxy.org", username="fixed_auth_user")
        user.set_password_cleartext("test123")
        sa_session.add(user)
        try:
            sa_session.commit()
        except Exception:
            pass

        # Login via OIDC without being logged into Galaxy first
        _, response = self._login_via_keycloak("gxyuser_fixed_auth", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # Should auto-associate and redirect to root (not user/external_ids)
        parsed_url = parse.urlparse(response.url)
        assert "user/external_ids" not in parsed_url.path, "Should redirect to root, not user/external_ids"

        # Should have notification about linking
        notification = parse.parse_qs(parsed_url.query).get("notification", [""])[0]
        assert "Your Keycloak identity has been linked" in notification

        # Verify user is logged in and associated
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_fixed_auth@galaxy.org"
        assert response.json()["username"] == "fixed_auth_user"

    def test_fixed_delegated_auth_with_new_user_creates_account(self):
        """
        Test: fixed_delegated_auth=True, user NOT logged in, NO existing user
        Expected: Create new user, redirect to root

        This matches custos lines 251-254, 268-269:
        - Create user if no existing_user
        - redirect to login_redirect_url (root)
        """
        # Login via OIDC with a new user (no pre-existing Galaxy account)
        _, response = self._login_via_keycloak("gxyuser_brand_new", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # Should create user and redirect to root
        parsed_url = parse.urlparse(response.url)
        assert "user/external_ids" not in parsed_url.path, "Should redirect to root for fixed_delegated_auth"

        # Verify user was created and logged in
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_brand_new@galaxy.org"


class TestWithoutFixedDelegatedAuth(AbstractTestCases.BaseKeycloakIntegrationTestCase):
    """
    Integration tests for behavior WITHOUT fixed_delegated_auth (default).

    This ensures we don't break the existing PSA behavior when fixed_delegated_auth=False.
    """

    provider_name = "keycloak"

    @classmethod
    def patch_oidc_config(cls):
        psa_authnz_init = PSAAuthnz.__init__

        def patched_psa_authnz_init(self, *args, **kwargs):
            server_wrapper = cls._test_driver.server_wrappers[0]
            psa_authnz_init(self, *args, **kwargs)
            if self.config.get("provider") == cls.provider_name:
                self.config["redirect_uri"] = (
                    f"http://{server_wrapper.host}:{server_wrapper.port}/authnz/{cls.provider_name}/callback"
                )

        cls.config_patcher = patch("galaxy.authnz.psa_authnz.PSAAuthnz.__init__", patched_psa_authnz_init)
        cls.config_patcher.start()

    @classmethod
    def handle_galaxy_oidc_config_kwds(cls, config):
        config["enable_oidc"] = True
        config["oidc_config_file"] = os.path.join(os.path.dirname(__file__), "oidc_config.xml")
        config["oidc_backends_config_file"] = cls.backend_config_file
        # To ensure fixed_delegated_auth=False, we configure an additional authenticator
        # fixed_delegated_auth is computed as:
        #   len(oidc_providers) == 1 AND len(other_authenticators) == 0
        # By default, len(other_authenticators) > 1, so fixed_delegated_auth = True

    def test_without_fixed_delegated_auth_prompts_for_login(self):
        """
        Test: fixed_delegated_auth=False, user NOT logged in, existing user with matching email
        Expected: Redirect to login/start with connect_external_provider prompt

        This matches custos lines 238-247:
        - Show prompt to log in and link accounts
        - Redirect to login/start?connect_external_provider=...
        """
        # Pre-create a Galaxy user
        sa_session = self._app.model.session
        user = model.User(email="gxyuser_no_fixed_auth@galaxy.org", username="no_fixed_auth_user")
        user.set_password_cleartext("test123")
        sa_session.add(user)
        try:
            sa_session.commit()
        except Exception:
            pass

        # Try to login via OIDC without being logged into Galaxy
        _, response = self._login_via_keycloak("gxyuser_no_fixed_auth", KEYCLOAK_TEST_PASSWORD, save_cookies=False)

        # Should redirect to login/start with prompt
        parsed_url = parse.urlparse(response.url)
        assert "login/start" in parsed_url.path or "login/start" in response.url

        # Should have connect_external_provider parameters
        query_params = parse.parse_qs(parsed_url.query)
        assert "connect_external_provider" in query_params
        assert query_params["connect_external_provider"][0] == "keycloak"
        assert "connect_external_email" in query_params
        assert "gxyuser_no_fixed_auth@galaxy.org" in query_params["connect_external_email"][0]

        # User should NOT be logged in
        response = self._get("users/current")
        assert "id" not in response.json()

    def test_without_fixed_delegated_auth_redirects_to_external_ids(self):
        """
        Test: fixed_delegated_auth=False, new user created
        Expected: Redirect to user/external_ids with notification

        This matches custos lines 277-282:
        - Default redirect to user/external_ids
        """
        # Login via OIDC with a new user
        _, response = self._login_via_keycloak("gxyuser_new_no_fixed", KEYCLOAK_TEST_PASSWORD, save_cookies=True)

        # Should redirect to user/external_ids
        parsed_url = parse.urlparse(response.url)
        assert "user/external_ids" in parsed_url.path or "user/external_ids" in response.url

        # Should have notification
        query_params = parse.parse_qs(parsed_url.query)
        assert "notification" in query_params
        notification = query_params["notification"][0]
        assert "Your Keycloak identity has been linked" in notification

        # Verify user was created
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser_new_no_fixed@galaxy.org"

    def test_logged_in_user_links_identity_with_different_email(self):
        """
        Test: User is logged in, links OIDC identity with email matching a different user's account
        Expected: Identity linked to logged-in user, redirect includes email_exists parameter

        This tests the scenario where:
        1. User A is logged in
        2. User A links an OIDC identity
        3. The OIDC identity's email matches User B's email (different account)
        4. The identity gets linked to User A anyway (the logged-in user)
        5. The redirect URL includes email_exists parameter to warn the user
        """
        # Create User A manually - will be the logged-in user
        sa_session = self._app.model.session
        user_a = model.User(email="user_a@galaxy.org", username="user_a")
        user_a.set_password_cleartext("test123")
        sa_session.add(user_a)
        sa_session.commit()

        # Create User B manually - has email matching the OIDC identity
        # gxyuser_existing@galaxy.org already exists in Keycloak
        user_b = model.User(email="gxyuser_existing@galaxy.org", username="user_b")
        user_b.set_password_cleartext("test456")
        sa_session.add(user_b)
        sa_session.commit()

        # Establish a web session and log in as User A
        session = requests.Session()
        response = session.get(self._api_url("../login/start"))
        matches = self.REGEX_GALAXY_CSRF_TOKEN.search(response.text)
        assert matches
        session_csrf_token = str(matches.groups(1)[0])
        response = session.post(
            self._api_url("../user/login"),
            data={
                "login": "user_a@galaxy.org",
                "password": "test123",
                "session_csrf_token": session_csrf_token,
            },
        )

        # Verify we're logged in as User A
        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "user_a@galaxy.org"
        assert response.json()["username"] == "user_a"

        # Now User A tries to link an OIDC identity using gxyuser_existing Keycloak account
        # which has email matching User B
        _, response = self._login_via_keycloak(
            "gxyuser_existing",  # This user's email matches user_b
            KEYCLOAK_TEST_PASSWORD,
            save_cookies=False,
            session=session,
        )

        # Should redirect to user/external_ids with both notification and email_exists
        parsed_url = parse.urlparse(response.url)
        assert "user/external_ids" in parsed_url.path or "user/external_ids" in response.url

        # Should have notification
        query_params = parse.parse_qs(parsed_url.query)
        assert "notification" in query_params
        notification = query_params["notification"][0]
        assert "Your Keycloak identity has been linked" in notification

        # Should have email_exists parameter warning about the email conflict
        assert "email_exists" in query_params
        email_exists = query_params["email_exists"][0]
        assert email_exists == "gxyuser_existing@galaxy.org"

        # Verify the identity was linked to User A (not User B)
        response = session.get(self._api_url("users/current"))
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "user_a@galaxy.org"
        assert response.json()["username"] == "user_a"
