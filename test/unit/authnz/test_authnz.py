import tempfile
from typing import (
    Any,
    cast,
    Optional,
)
from unittest.mock import (
    MagicMock,
    patch,
)
from urllib.parse import urlencode

import pytest
from social_core.backends.base import BaseAuth
from social_core.exceptions import (
    AuthCanceled,
    AuthForbidden,
    AuthTokenError,
)
from social_core.utils import setting_name
from webob.exc import HTTPFound

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.authnz.managers import AuthnzManager
from galaxy.util import asbool
from galaxy.web.framework import base as web_framework_base
from galaxy.web.framework.base import Response
from galaxy.webapps.base.webapp import WebApplication
from ..webapps.test_webapp_base import (
    CORSParsingMockConfig,
    StubGalaxyWebTransaction,
)


@pytest.fixture
def mock_app():
    yield MagicMock()


OIDC_BACKEND_CONFIG_TEMPLATE = """<?xml version="1.0"?>
<OIDC>
    <provider name="{provider_name}">
        <url>{url}</url>
        <client_id>{client_id}</client_id>
        <client_secret>{client_secret}</client_secret>
        <redirect_uri>$galaxy_url/authnz/keycloak/callback</redirect_uri>
        <enable_idp_logout>{enable_idp_logout}</enable_idp_logout>
        <require_create_confirmation>{require_create_confirmation}</require_create_confirmation>
        <require_session_refresh>{require_session_refresh}</require_session_refresh>
        <accepted_audiences>{accepted_audiences}</accepted_audiences>
        <username_key>{username_key}</username_key>
    </provider>
</OIDC>
"""


OIDC_CONFIG_TEMPLATE = """
<OIDC>
    <Setter Property="VERIFY_SSL" Value="False" Type="bool"/>
    {extra_properties}
</OIDC>
"""


def create_oidc_config(extra_properties: str = "") -> tuple[str, str]:
    contents = OIDC_CONFIG_TEMPLATE.format(extra_properties=extra_properties)
    file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    file.write(contents)
    return contents, file.name


def create_backend_config(
    provider_name="oidc",
    url="https://example.com",
    client_id="client_id",
    client_secret="client_secret",
    enable_idp_logout="true",
    require_create_confirmation="false",
    require_session_refresh="false",
    accepted_audiences="https://audience.example.com",
    username_key="custom_username",
) -> tuple[str, str]:
    contents = OIDC_BACKEND_CONFIG_TEMPLATE.format(
        provider_name=provider_name,
        url=url,
        client_id=client_id,
        client_secret=client_secret,
        enable_idp_logout=enable_idp_logout,
        require_create_confirmation=require_create_confirmation,
        require_session_refresh=require_session_refresh,
        accepted_audiences=accepted_audiences,
        username_key=username_key,
    )
    file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    file.write(contents)
    return contents, file.name


class FakeRefreshBackend:
    refresh_result: bool = False
    refresh_exception: Exception | None = None

    def __init__(self, provider, oidc_config, oidc_backend_config, app_config):
        self.provider = provider
        self.oidc_config = oidc_config
        self.oidc_backend_config = oidc_backend_config
        self.app_config = app_config

    def refresh(self, trans, auth):
        if self.refresh_exception is not None:
            raise self.refresh_exception
        return self.refresh_result


FAKE_SOCIAL_AUTH_BACKEND = cast(BaseAuth, MagicMock())


class AuthenticatedStubGalaxyWebTransaction(StubGalaxyWebTransaction):
    auth_user: model.User | None = None

    def _ensure_valid_session(self, session_cookie: str, create: bool = True) -> None:
        self.user = self.auth_user
        self.galaxy_session = None

    def _authenticate_api(self, session_cookie: str) -> Optional[str]:
        self.user = self.auth_user
        self.galaxy_session = None
        return None


def _make_user_with_social_auth(provider: str = "oidc") -> model.User:
    user = model.User(email="user@example.com", password="password")
    auth = model.UserAuthnzToken(provider=provider, uid="user-1", extra_data={"refresh_token": "refresh"}, user=user)
    user.social_auth.append(auth)
    return user


def _make_authnz_manager(
    app: Any, provider_name: str = "oidc", require_session_refresh: str = "false"
) -> AuthnzManager:
    _, oidc_path = create_oidc_config()
    _, backend_path = create_backend_config(
        provider_name=provider_name, require_session_refresh=require_session_refresh
    )
    app.config.oidc = {}
    return AuthnzManager(app=app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)


def _make_mock_trans_with_user(user: model.User) -> galaxy_mock.MockTrans:
    app = galaxy_mock.MockApp()
    trans = galaxy_mock.MockTrans(app=app, user=user)
    return trans


def test_parse_backend_config(mock_app):
    config_values = {
        "url": "https://example.com",
        "client_id": "example_app",
        "client_secret": "abcd1234",
        "enable_idp_logout": "true",
        "require_create_confirmation": "false",
        "require_session_refresh": "true",
        "accepted_audiences": "https://audience.example.com",
        "username_key": "custom_username",
    }
    oidc_contents, oidc_path = create_oidc_config()
    backend_contents, backend_path = create_backend_config(provider_name="oidc", **config_values)
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    assert isinstance(manager.oidc_backends_config["oidc"], dict)
    parsed = manager.oidc_backends_config["oidc"]
    assert parsed["url"] == config_values["url"]
    assert parsed["client_id"] == config_values["client_id"]
    assert parsed["client_secret"] == config_values["client_secret"]
    assert parsed["accepted_audiences"] == config_values["accepted_audiences"]
    assert parsed["username_key"] == config_values["username_key"]
    # Boolean values should be parsed into bools
    assert parsed["enable_idp_logout"] == asbool(config_values["enable_idp_logout"])
    assert parsed["require_create_confirmation"] == asbool(config_values["require_create_confirmation"])
    assert parsed["require_session_refresh"] == asbool(config_values["require_session_refresh"])


def test_parse_backend_config_bool_defaults(mock_app):
    # XML config without boolean fields
    config = """<?xml version="1.0"?>
    <OIDC>
        <provider name="oidc">
            <url>https://example.com</url>
            <client_id>abcd1234</client_id>
            <client_secret>abcdef99999</client_secret>
            <redirect_uri>$galaxy_url/authnz/oidc/callback</redirect_uri>
        </provider>
    </OIDC>
    """
    config_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    config_file.write(config)
    config_file.flush()
    config_file.close()
    oidc_contents, oidc_path = create_oidc_config()
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=config_file.name)
    assert isinstance(manager.oidc_backends_config["oidc"], dict)
    parsed = manager.oidc_backends_config["oidc"]
    # Boolean values should be False by default
    assert parsed["enable_idp_logout"] is False
    assert parsed.get("require_create_confirmation", False) is False
    assert parsed.get("require_session_refresh", False) is False


def test_psa_authnz_config(mock_app):
    """
    Test config values are set correctly in PSAAuthnz
    """
    config_values = {
        "url": "https://example.com",
        "client_id": "example_app",
        "client_secret": "abcd1234",
        "enable_idp_logout": "true",
        "require_create_confirmation": "false",
        "accepted_audiences": "https://audience.example.com",
        "username_key": "custom_username",
    }
    oidc_contents, oidc_path = create_oidc_config()
    backend_contents, backend_path = create_backend_config(provider_name="oidc", **config_values)
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    from galaxy.authnz.psa_authnz import PSAAuthnz

    psa_authnz = PSAAuthnz(
        provider="oidc",
        oidc_config=manager.oidc_config,
        oidc_backend_config=manager.oidc_backends_config["oidc"],
        app_config=mock_app.config,
    )
    assert psa_authnz.config[setting_name("USERNAME_KEY")] == config_values["username_key"]


def _create_backend_config_with_idphint(idphint_value: Optional[str] = None) -> tuple[str, str]:
    """Create a Keycloak backend config, optionally including an <idphint> element."""
    idphint_element = f"        <idphint>{idphint_value}</idphint>" if idphint_value else ""
    contents = f"""<?xml version="1.0"?>
<OIDC>
    <provider name="keycloak">
        <url>https://auth.example.org/realms/MyRealm/</url>
        <client_id>galaxy-oidc</client_id>
        <client_secret>secret</client_secret>
        <redirect_uri>https://galaxy.example.org/authnz/keycloak/callback</redirect_uri>
        <enable_idp_logout>true</enable_idp_logout>
{idphint_element}
    </provider>
</OIDC>
"""
    file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml")
    file.write(contents)
    file.flush()
    return contents, file.name


def test_parse_idphint_from_xml(mock_app):
    """
    Regression test: <idphint> in oidc_backends_config.xml must be parsed into
    the oidc_backend_config dict so that PSAAuthnz can forward it as IDPHINT to
    the Keycloak/CILogon backends (which use it to set kc_idp_hint).

    Previously, _parse_idp_config() had no branch for <idphint>, so the element
    was silently ignored and oidc_backend_config.get("idphint") always returned
    None, causing kc_idp_hint to never be sent to Keycloak.
    """
    _, oidc_path = create_oidc_config()
    _, backend_path = _create_backend_config_with_idphint(idphint_value="my-switch-edu-id")
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    parsed = manager.oidc_backends_config["keycloak"]
    assert "idphint" in parsed, "<idphint> element must be parsed into oidc_backend_config dict"
    assert parsed["idphint"] == "my-switch-edu-id"


def test_idphint_propagated_to_psa_config(mock_app):
    """
    When <idphint> is configured, PSAAuthnz must expose it as IDPHINT in its
    config so the Keycloak/CILogon PSA backend can add kc_idp_hint to the
    authorization URL.
    """
    from galaxy.authnz.psa_authnz import PSAAuthnz

    _, oidc_path = create_oidc_config()
    _, backend_path = _create_backend_config_with_idphint(idphint_value="stage")
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    psa = PSAAuthnz(
        provider="keycloak",
        oidc_config=manager.oidc_config,
        oidc_backend_config=manager.oidc_backends_config["keycloak"],
        app_config=mock_app.config,
    )
    assert psa.config.get("IDPHINT") == "stage", "IDPHINT must be 'stage' when <idphint>stage</idphint> is in XML"


def test_missing_idphint_is_none(mock_app):
    """
    When <idphint> is absent from the XML, IDPHINT must be None (not a hardcoded
    default string like 'oidc'), so the Keycloak backend omits kc_idp_hint
    entirely rather than sending a wrong value.
    """
    from galaxy.authnz.psa_authnz import PSAAuthnz

    _, oidc_path = create_oidc_config()
    _, backend_path = _create_backend_config_with_idphint(idphint_value=None)
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    psa = PSAAuthnz(
        provider="keycloak",
        oidc_config=manager.oidc_config,
        oidc_backend_config=manager.oidc_backends_config["keycloak"],
        app_config=mock_app.config,
    )
    assert psa.config.get("IDPHINT") is None, "IDPHINT must be None when <idphint> is absent from XML"


def test_refresh_expiring_oidc_tokens_returns_none_after_successful_refresh(mock_app):
    user = _make_user_with_social_auth()
    trans = _make_mock_trans_with_user(user)
    manager = _make_authnz_manager(trans.app)
    FakeRefreshBackend.refresh_result = True
    FakeRefreshBackend.refresh_exception = None

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        reauth_provider = manager.refresh_expiring_oidc_tokens(cast(Any, trans))

    assert reauth_provider is None


@pytest.mark.parametrize(
    "refresh_exception",
    [
        AuthTokenError(backend=FAKE_SOCIAL_AUTH_BACKEND),
        AuthCanceled(backend=FAKE_SOCIAL_AUTH_BACKEND),
        AuthForbidden(backend=FAKE_SOCIAL_AUTH_BACKEND),
    ],
)
def test_refresh_expiring_oidc_tokens_returns_provider_on_required_terminal_refresh_failure(
    mock_app, refresh_exception
):
    user = _make_user_with_social_auth()
    trans = _make_mock_trans_with_user(user)
    manager = _make_authnz_manager(trans.app, require_session_refresh="true")
    FakeRefreshBackend.refresh_result = False
    FakeRefreshBackend.refresh_exception = refresh_exception

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        reauth_provider = manager.refresh_expiring_oidc_tokens(cast(Any, trans))

    assert reauth_provider == "oidc"


def test_refresh_expiring_oidc_tokens_returns_none_on_optional_terminal_refresh_failure(mock_app):
    user = _make_user_with_social_auth()
    trans = _make_mock_trans_with_user(user)
    manager = _make_authnz_manager(trans.app, require_session_refresh="false")
    FakeRefreshBackend.refresh_result = False
    FakeRefreshBackend.refresh_exception = AuthTokenError(backend=FAKE_SOCIAL_AUTH_BACKEND)

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        reauth_provider = manager.refresh_expiring_oidc_tokens(cast(Any, trans))

    assert reauth_provider is None


def test_refresh_expiring_oidc_tokens_returns_none_on_unexpected_refresh_failure(mock_app):
    user = _make_user_with_social_auth()
    trans = _make_mock_trans_with_user(user)
    manager = _make_authnz_manager(trans.app, require_session_refresh="true")
    FakeRefreshBackend.refresh_result = False
    FakeRefreshBackend.refresh_exception = RuntimeError("unexpected refresh failure")

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        reauth_provider = manager.refresh_expiring_oidc_tokens(cast(Any, trans))

    assert reauth_provider is None


def test_redirects_to_oidc_login_on_terminal_refresh_failure() -> None:
    app = cast(Any, galaxy_mock.MockApp())
    app.config = CORSParsingMockConfig()
    app.authnz_manager = _make_authnz_manager(app, require_session_refresh="true")
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
    environ = galaxy_mock.buildMockEnviron()
    AuthenticatedStubGalaxyWebTransaction.auth_user = _make_user_with_social_auth()
    FakeRefreshBackend.refresh_result = False
    FakeRefreshBackend.refresh_exception = AuthTokenError(backend=FAKE_SOCIAL_AUTH_BACKEND)
    original_send_redirect = Response.send_redirect
    redirect_urls: list[str] = []

    def capture_send_redirect(self, url: str):
        redirect_urls.append(url)
        return original_send_redirect(self, url)

    def build_test_url(path: str, **query_params):
        return f"{path}?{urlencode(query_params)}"

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        with patch.object(web_framework_base.routes, "url_for", side_effect=build_test_url):
            with patch.object(Response, "send_redirect", autospec=True, side_effect=capture_send_redirect):
                with pytest.raises(HTTPFound):
                    AuthenticatedStubGalaxyWebTransaction(environ, app, webapp, "session_cookie")

    assert redirect_urls
    assert "/authnz/oidc/login" in redirect_urls[0]


def test_returns_401_for_api_request_on_terminal_refresh_failure() -> None:
    app = cast(Any, galaxy_mock.MockApp())
    app.config = CORSParsingMockConfig()
    app.authnz_manager = _make_authnz_manager(app, require_session_refresh="true")
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
    environ = galaxy_mock.buildMockEnviron(PATH_INFO="/api/users/current", is_api_request=True)
    AuthenticatedStubGalaxyWebTransaction.auth_user = _make_user_with_social_auth()
    FakeRefreshBackend.refresh_result = False
    FakeRefreshBackend.refresh_exception = AuthTokenError(backend=FAKE_SOCIAL_AUTH_BACKEND)

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        trans = AuthenticatedStubGalaxyWebTransaction(environ, app, webapp, "session_cookie")

    assert trans.response.status == 401
    assert trans.error_message == "Authentication session expired. Please log in again."
    assert trans.user is None
    assert trans.galaxy_session is None


def test_allows_api_request_on_successful_oidc_refresh() -> None:
    """
    Test that API requests proceed when the refresh succeeds.
    """
    app = cast(Any, galaxy_mock.MockApp())
    app.config = CORSParsingMockConfig()
    app.authnz_manager = _make_authnz_manager(app, require_session_refresh="true")
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
    environ = galaxy_mock.buildMockEnviron(PATH_INFO="/api/users/current", is_api_request=True)
    AuthenticatedStubGalaxyWebTransaction.auth_user = _make_user_with_social_auth()
    FakeRefreshBackend.refresh_result = True
    FakeRefreshBackend.refresh_exception = None

    with patch.object(AuthnzManager, "_get_identity_provider_factory", return_value=FakeRefreshBackend):
        trans = AuthenticatedStubGalaxyWebTransaction(environ, app, webapp, "session_cookie")

    assert trans.response.status == 200
    assert trans.error_message is None
    assert trans.galaxy_session is None
