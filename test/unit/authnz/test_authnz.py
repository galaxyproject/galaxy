import tempfile
from types import SimpleNamespace
from typing import (
    Any,
    cast,
    Optional,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
from social_core.utils import setting_name
from webob.exc import HTTPFound

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.authnz.managers import AuthnzManager
from galaxy.util import asbool
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
        accepted_audiences=accepted_audiences,
        username_key=username_key,
    )
    file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    file.write(contents)
    return contents, file.name


def test_parse_backend_config(mock_app):
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
    _, oidc_path = create_oidc_config()
    _, backend_path = create_backend_config(provider_name="oidc")
    mock_app.config.oidc = {}
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    backend = MagicMock()
    backend.refresh.return_value = True

    user = model.User(email="user@example.com", password="password")
    auth = model.UserAuthnzToken(provider="oidc", uid="user-1", extra_data={"refresh_token": "refresh"}, user=user)
    user.social_auth.append(auth)
    trans = SimpleNamespace(user=user, app=SimpleNamespace(config=SimpleNamespace(oidc_require_refresh=True)))

    with patch.object(manager, "_get_authnz_backend", return_value=(True, None, backend)):
        reauth_provider = manager.refresh_expiring_oidc_tokens(trans)

    assert reauth_provider is None
    backend.refresh.assert_called_once_with(trans, auth)


def test_refresh_expiring_oidc_tokens_returns_provider_on_terminal_refresh_failure(mock_app):
    _, oidc_path = create_oidc_config()
    _, backend_path = create_backend_config(provider_name="oidc")
    mock_app.config.oidc = {}
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)

    class RefreshFailure(Exception):
        def __init__(self):
            self.response = SimpleNamespace(status_code=400)

    backend = MagicMock()
    backend.refresh.side_effect = RefreshFailure()

    user = model.User(email="user@example.com", password="password")
    auth = model.UserAuthnzToken(provider="oidc", uid="user-1", extra_data={"refresh_token": "refresh"}, user=user)
    user.social_auth.append(auth)
    trans = SimpleNamespace(user=user, app=SimpleNamespace(config=SimpleNamespace(oidc_require_refresh=True)))

    with patch.object(manager, "_get_authnz_backend", return_value=(True, None, backend)):
        reauth_provider = manager.refresh_expiring_oidc_tokens(trans)

    assert reauth_provider == "oidc"
    backend.refresh.assert_called_once_with(trans, auth)


def test_redirects_to_oidc_login_on_terminal_refresh_failure() -> None:
    app = cast(Any, galaxy_mock.MockApp())
    app.config = CORSParsingMockConfig(oidc_require_refresh=True)
    app.authnz_manager = MagicMock()
    app.authnz_manager.refresh_expiring_oidc_tokens.return_value = "oidc"
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
    environ = galaxy_mock.buildMockEnviron()

    with patch("galaxy.webapps.base.webapp.url_for", return_value="/authnz/oidc/login?redirect=true&next=%2F"):
        with pytest.raises(HTTPFound) as exc_info:
            StubGalaxyWebTransaction(environ, app, webapp, "session_cookie")

    assert exc_info.value.location == "/authnz/oidc/login?redirect=true&next=%2F"


def test_returns_401_for_api_request_on_terminal_refresh_failure() -> None:
    app = cast(Any, galaxy_mock.MockApp())
    app.config = CORSParsingMockConfig(oidc_require_refresh=True)
    app.authnz_manager = MagicMock()
    app.authnz_manager.refresh_expiring_oidc_tokens.return_value = "oidc"
    webapp = cast(WebApplication, galaxy_mock.MockWebapp(app.security))
    environ = galaxy_mock.buildMockEnviron(PATH_INFO="/api/users/current", is_api_request=True)

    trans = StubGalaxyWebTransaction(environ, app, webapp, "session_cookie")

    assert trans.response.status == 401
    assert trans.error_message == "Authentication session expired. Please log in again."
    assert trans.user is None
    assert trans.galaxy_session is None
