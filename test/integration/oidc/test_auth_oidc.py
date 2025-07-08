"""Integration tests for the CLI shell plugins and runners."""

import html
import os
import re
import subprocess
import tempfile
import time
from string import Template
from typing import ClassVar
from urllib import parse

from galaxy import model
from galaxy.util import requests
from galaxy_test.base.api import ApiTestInteractor
from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import attempt_ports

KEYCLOAK_ADMIN_USERNAME = "admin"
KEYCLOAK_ADMIN_PASSWORD = "admin"
KEYCLOAK_TEST_USERNAME = "gxyuser"
KEYCLOAK_TEST_PASSWORD = "gxypass"
KEYCLOAK_HOST_PORT = 9443
KEYCLOAK_URL = f"https://localhost:{KEYCLOAK_HOST_PORT}/realms/gxyrealm"


OIDC_BACKEND_CONFIG_TEMPLATE = f"""<?xml version="1.0"?>
<OIDC>
    <provider name="$provider_name">
        <url>{KEYCLOAK_URL}</url>
        <oidc_endpoint>{KEYCLOAK_URL}</oidc_endpoint>
        <client_id>gxyclient</client_id>
        <client_secret>dummyclientsecret</client_secret>
        <redirect_uri>$galaxy_url/authnz/$provider_name/callback</redirect_uri>
        <enable_idp_logout>true</enable_idp_logout>
        <accepted_audiences>gxyclient</accepted_audiences>
    </provider>
</OIDC>
"""

# Debug authentication pipeline that saves access token data
#   for testing
DEBUG_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "galaxy.authnz.psa_authnz.contains_required_data",
    "galaxy.authnz.psa_authnz.verify",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "galaxy.authnz.psa_authnz.decode_access_token",
    # Debug step saves data to UserAuthnzToken.extra_data
    "galaxy.authnz.util.debug_access_token_data",
    "social_core.pipeline.user.user_details",
)


def wait_till_app_ready(url, timeout=60):
    import time

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, verify=False, timeout=2)
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
        REGEX_KEYCLOAK_LOGIN_ACTION = re.compile(r"action=\"(.*?)\"\s+")
        container_name: ClassVar[str]
        backend_config_file: ClassVar[str]
        provider_name: ClassVar[str]
        saved_oauthlib_insecure_transport: ClassVar[bool]
        _original_env: ClassVar[dict] = {}

        @classmethod
        def setUpClass(cls):
            # Save original environment variables
            for var in ["GALAXY_TEST_PORT", "GALAXY_WEB_PORT", "GALAXY_TEST_PORT_RANDOM"]:
                cls._original_env[var] = os.environ.get(var)

            fixed_port = attempt_ports(port=None, set_galaxy_web_port=False)

            os.environ["GALAXY_TEST_PORT"] = str(fixed_port)
            os.environ["GALAXY_WEB_PORT"] = str(fixed_port)  # Optional, if referenced elsewhere
            if "GALAXY_TEST_PORT_RANDOM" in os.environ:
                os.environ["GALAXY_TEST_PORT_RANDOM"] = "0"

            # By default, the oidc callback must be done over a secure transport, so
            # we forcibly disable it for now
            cls.disableOauthlibHttps()
            cls.container_name = f"{cls.__name__}_container"
            start_keycloak_docker(container_name=cls.container_name)

            super().setUpClass()
            # For the oidc callback to work, we need to know Galaxy's hostname and port.
            # However, we won't know what the host and port are until the Galaxy test driver is started.
            # So let it start, then generate the oidc_backend_config.xml with the correct host and port,
            # and finally restart Galaxy so the OIDC config takes effect.
            cls.configure_oidc_and_restart()

        @classmethod
        def generate_oidc_config_file(cls, server_wrapper, provider_name="keycloak"):
            with tempfile.NamedTemporaryFile("w+t", delete=False) as tmp_file:
                host = server_wrapper.host
                port = server_wrapper.port
                prefix = server_wrapper.prefix or ""
                galaxy_url = f"http://{host}:{port}{prefix.rstrip('/')}"
                data = Template(OIDC_BACKEND_CONFIG_TEMPLATE).safe_substitute(
                    galaxy_url=galaxy_url,
                    provider_name=provider_name,
                )
                tmp_file.write(data)
                return tmp_file.name

        @classmethod
        def configure_oidc_and_restart(cls):
            server_wrapper = cls._test_driver.server_wrappers[0]
            cls.backend_config_file = cls.generate_oidc_config_file(server_wrapper, provider_name=cls.provider_name)
            cls._test_driver.restart(config_object=cls, handle_config=cls.handle_galaxy_oidc_config_kwds)

        @classmethod
        def tearDownClass(cls):
            stop_keycloak_docker(cls.container_name)
            cls.restoreOauthlibHttps()
            os.remove(cls.backend_config_file)

            # Restore original environment variables
            for var, val in cls._original_env.items():
                if val is not None:
                    os.environ[var] = val
                else:
                    os.environ.pop(var, None)

            super().tearDownClass()

        @classmethod
        def disableOauthlibHttps(cls):
            if "OAUTHLIB_INSECURE_TRANSPORT" in os.environ:
                cls.saved_oauthlib_insecure_transport = bool(os.environ["OAUTHLIB_INSECURE_TRANSPORT"])
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"
            os.environ["REQUESTS_CA_BUNDLE"] = os.path.dirname(__file__) + "/keycloak-server.crt.pem"
            os.environ["SSL_CERT_FILE"] = os.path.dirname(__file__) + "/keycloak-server.crt.pem"

        @classmethod
        def restoreOauthlibHttps(cls):
            if getattr(cls, "saved_oauthlib_insecure_transport", None):
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = str(cls.saved_oauthlib_insecure_transport)
            else:
                del os.environ["OAUTHLIB_INSECURE_TRANSPORT"]

        @classmethod
        def handle_galaxy_oidc_config_kwds(cls, config):
            config["enable_oidc"] = True
            config["oidc_config_file"] = os.path.join(os.path.dirname(__file__), "oidc_config.xml")
            config["oidc_backends_config_file"] = cls.backend_config_file

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
    """

    REGEX_GALAXY_CSRF_TOKEN = re.compile(r"session_csrf_token\": \"(.*)\"")
    provider_name = "keycloak"

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


class TestGalaxyOIDCLoginPSA(AbstractTestCases.BaseKeycloakIntegrationTestCase):
    """
    Test the Python Social Auth-based implementation of OIDC.
    """

    provider_name = "oidc"

    @classmethod
    def handle_galaxy_oidc_config_kwds(cls, config):
        # super().handle_galaxy_config_kwds(config)
        config["enable_oidc"] = True
        config["oidc_config_file"] = os.path.join(os.path.dirname(__file__), "oidc_config.xml")
        config["oidc_backends_config_file"] = cls.backend_config_file
        # Use a debug auth pipeline that stores access token data in the user model
        config["oidc_auth_pipeline"] = DEBUG_AUTH_PIPELINE

    def test_oidc_login_decode_access_token(self):
        _, response = self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == "gxyuser@galaxy.org"

        sa_session = self._app.model.session
        user = sa_session.query(model.User).filter_by(email="gxyuser@galaxy.org").one()
        social = next((s for s in user.social_auth if s.provider == "oidc"), None)
        assert social is not None
        extra_data = social.extra_data
        assert extra_data is not None
        assert "access_token_decoded" in extra_data
        assert "realm_access" in extra_data["access_token_decoded"]
