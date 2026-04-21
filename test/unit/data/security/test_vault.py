import os
import string
import tempfile
from unittest.mock import MagicMock

import hvac
import pytest
from cryptography.fernet import InvalidToken

from galaxy.model.unittest_utils.data_app import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.security.vault import (
    _unwrap_vault,
    HashicorpVault,
    InvalidVaultConfigException,
    InvalidVaultKeyException,
    renew_vault_token_if_needed,
    Vault,
    VaultFactory,
    VaultKeyPrefixWrapper,
    VaultKeyValidationWrapper,
)
from galaxy.util.unittest import TestCase


class AbstractTestCases:
    """Test classes that should not be collected.

    Classes derived from unittest.TestCase are collected only if they are at the
    module level: https://stackoverflow.com/a/25695512/4503125

    This workaround is needed because unittest/pytest try to collect test
    classes even if they are abstract, and therefore their tests fails.
    """

    class VaultTestBase(TestCase):
        vault: Vault

        def test_read_write_secret(self):
            self.vault.write_secret("my/test/secret", "hello world")
            assert self.vault.read_secret("my/test/secret") == "hello world"

        def test_overwrite_secret(self):
            self.vault.write_secret("my/new/secret", "hello world")
            self.vault.write_secret("my/new/secret", "hello overwritten")
            assert self.vault.read_secret("my/new/secret") == "hello overwritten"

        def test_valid_paths(self):
            with self.assertRaises(InvalidVaultKeyException):
                self.vault.write_secret("", "hello world")
            with self.assertRaises(InvalidVaultKeyException):
                self.vault.write_secret("my//new/secret", "hello world")
            with self.assertRaises(InvalidVaultKeyException):
                self.vault.write_secret("my/ /new/secret", "hello world")
            # leading and trailing slashes should be ignored
            self.vault.write_secret("/my/new/secret with space/", "hello overwritten")
            assert self.vault.read_secret("my/new/secret with space") == "hello overwritten"


VAULT_CONF_HASHICORP = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_hashicorp.yml")


@pytest.mark.skipif(
    not os.environ.get("VAULT_ADDRESS") or not os.environ.get("VAULT_TOKEN"),
    reason="VAULT_ADDRESS and VAULT_TOKEN env vars not set",
)
class TestHashicorpVault(AbstractTestCases.VaultTestBase):
    def setUp(self) -> None:
        with (
            tempfile.NamedTemporaryFile(mode="w", prefix="vault_hashicorp", delete=False) as tempconf,
            open(VAULT_CONF_HASHICORP) as f,
        ):
            content = string.Template(f.read()).safe_substitute(
                vault_address=os.environ.get("VAULT_ADDRESS"), vault_token=os.environ.get("VAULT_TOKEN")
            )
            tempconf.write(content)
            self.vault_temp_conf = tempconf.name
        config = GalaxyDataTestConfig(vault_config_file=self.vault_temp_conf)
        app = GalaxyDataTestApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def test_renew_token(self):
        """Test that vault token renewal works against a real Hashicorp Vault."""
        inner = _unwrap_vault(self.vault)
        assert isinstance(inner, HashicorpVault), f"Expected HashicorpVault, got {type(inner)}"
        inner.renew_token()

    def test_renew_vault_token_if_needed(self):
        """Test the full renewal path through renew_vault_token_if_needed with a real Vault."""
        renew_vault_token_if_needed(self.vault)

    def tearDown(self) -> None:
        os.remove(self.vault_temp_conf)


VAULT_CONF_DATABASE = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database.yml")
VAULT_CONF_DATABASE_ROTATED = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_rotated.yml")
VAULT_CONF_DATABASE_INVALID = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_invalid_keys.yml")


class TestDatabaseVault(AbstractTestCases.VaultTestBase):
    def setUp(self) -> None:
        config = GalaxyDataTestConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = GalaxyDataTestApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def test_rotate_keys(self):
        config = GalaxyDataTestConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = GalaxyDataTestApp(config=config)
        vault = VaultFactory.from_app(app)
        vault.write_secret("my/rotated/secret", "hello rotated")

        # should succeed after rotation
        app.config.vault_config_file = VAULT_CONF_DATABASE_ROTATED  # type: ignore[attr-defined]
        vault = VaultFactory.from_app(app)
        assert vault.read_secret("my/rotated/secret") == "hello rotated"

    def test_wrong_keys(self):
        config = GalaxyDataTestConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = GalaxyDataTestApp(config=config)
        vault = VaultFactory.from_app(app)
        vault.write_secret("my/incorrect/secret", "hello incorrect")

        # should fail because decryption keys are the wrong
        app.config.vault_config_file = VAULT_CONF_DATABASE_INVALID  # type: ignore[attr-defined]
        vault = VaultFactory.from_app(app)
        with self.assertRaises(InvalidToken):
            vault.read_secret("my/incorrect/secret")


def _make_mocked_hashicorp_vault() -> HashicorpVault:
    inner = HashicorpVault.__new__(HashicorpVault)
    inner.client = MagicMock()
    return inner


@pytest.mark.parametrize("prefix", ["/galaxy", "galaxy", "/galaxy/"])
def test_vault_key_prefix_wrapper_emits_canonical_path(prefix):
    # Admins may write path_prefix with or without surrounding slashes; all
    # canonical spellings must produce the same canonical Vault path. Vault 2.0
    # rejects leading or double slashes in URLs.
    inner = _make_mocked_hashicorp_vault()
    inner.client.secrets.kv.read_secret_version.return_value = {"data": {"data": {"value": "v"}}}
    vault = VaultKeyValidationWrapper(VaultKeyPrefixWrapper(inner, prefix=prefix))

    assert vault.read_secret("user/1/preferences/editor") == "v"
    inner.client.secrets.kv.read_secret_version.assert_called_once_with(path="galaxy/user/1/preferences/editor")

    vault.write_secret("user/1/preferences/editor", "vscode")
    inner.client.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
        path="galaxy/user/1/preferences/editor", secret={"value": "vscode"}
    )


@pytest.mark.parametrize("prefix", ["", "/", "gal//axy", "gal /axy", "gal/ axy"])
def test_vault_key_prefix_wrapper_rejects_invalid_prefix(prefix):
    # Anything that would still produce a non-canonical Vault path after
    # stripping outer slashes must raise at construction time rather than
    # silently getting normalized into something hvac sends on the wire.
    with pytest.raises(InvalidVaultConfigException):
        VaultKeyPrefixWrapper(_make_mocked_hashicorp_vault(), prefix=prefix)


def test_hashicorp_vault_read_migrates_legacy_double_slash_secret():
    inner = _make_mocked_hashicorp_vault()
    # First canonical read raises InvalidPath; legacy read returns a value.
    inner.client.secrets.kv.read_secret_version.side_effect = [
        hvac.exceptions.InvalidPath(),
        {"data": {"data": {"value": "legacy-value"}}},
    ]

    value = inner.read_secret("galaxy/user/1/x")

    assert value == "legacy-value"
    assert inner.client.secrets.kv.read_secret_version.call_args_list[0].kwargs == {"path": "galaxy/user/1/x"}
    assert inner.client.secrets.kv.read_secret_version.call_args_list[1].kwargs == {"path": "/galaxy/user/1/x"}
    inner.client.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
        path="galaxy/user/1/x", secret={"value": "legacy-value"}
    )


def test_hashicorp_vault_read_missing_returns_none_without_rewrite():
    inner = _make_mocked_hashicorp_vault()
    inner.client.secrets.kv.read_secret_version.side_effect = hvac.exceptions.InvalidPath()

    assert inner.read_secret("galaxy/user/1/missing") is None
    inner.client.secrets.kv.v2.create_or_update_secret.assert_not_called()
