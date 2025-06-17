from pathlib import Path
import tempfile
from unittest.mock import MagicMock

import pytest

from galaxy.authnz.managers import AuthnzManager
from galaxy.util import asbool


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

def create_oidc_config(extra_properties: str = '') -> (str, Path):
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
        accepted_audiences="https://audience.example.com",
        username_key="custom_username",
) -> (str, Path):
    contents = OIDC_BACKEND_CONFIG_TEMPLATE.format(
        provider_name=provider_name,
        url=url,
        client_id=client_id,
        client_secret=client_secret,
        enable_idp_logout=enable_idp_logout,
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
        "accepted_audiences": "https://audience.example.com",
        "username_key": "custom_username",
    }
    oidc_contents, oidc_path = create_oidc_config()
    backend_contents, backend_path = create_backend_config(provider_name="oidc", **config_values)
    print(backend_contents)
    manager = AuthnzManager(app=mock_app, oidc_config_file=oidc_path, oidc_backends_config_file=backend_path)
    assert isinstance(manager.oidc_backends_config["oidc"], dict)
    print(manager.oidc_backends_config["oidc"])
    print(mock_app.config.oidc["oidc"])
    parsed = manager.oidc_backends_config["oidc"]
    assert parsed["url"] == config_values["url"]
    assert parsed["client_id"] == config_values["client_id"]
    assert parsed["client_secret"] == config_values["client_secret"]
    assert parsed["enable_idp_logout"] == asbool(config_values["enable_idp_logout"])
    assert parsed["accepted_audiences"] == config_values["accepted_audiences"]
    assert parsed["username_key"] == config_values["username_key"]



