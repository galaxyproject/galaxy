import logging
import os
import string
import tempfile
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
from cryptography.fernet import InvalidToken

from galaxy.model.unittest_utils.data_app import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.security.vault import (
    _unwrap_vault,
    HashicorpVault,
    InvalidVaultKeyException,
    NullVault,
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


@patch("galaxy.security.vault.hvac")
class TestHashicorpVaultTokenRenewal:
    def _make_vault(self, hvac_mock, token_lookup_data=None, token_renewal_enabled=False):
        # Set up real exception classes so except clauses work with the mock
        hvac_mock.exceptions.Forbidden = type("Forbidden", (Exception,), {})
        hvac_mock.exceptions.InvalidPath = type("InvalidPath", (Exception,), {})

        mock_client = MagicMock()
        hvac_mock.Client.return_value = mock_client
        if token_lookup_data is not None:
            mock_client.auth.token.lookup_self.return_value = {"data": token_lookup_data}
        config = {
            "vault_address": "http://localhost:8200",
            "vault_token": "s.test-token",
        }
        vault = HashicorpVault(config, token_renewal_enabled=token_renewal_enabled)
        return vault, mock_client

    def test_startup_errors_non_renewable_token(self, hvac_mock, caplog):
        """When renewal is enabled but the token isn't renewable, log an error."""
        with caplog.at_level(logging.ERROR, logger="galaxy.security.vault"):
            self._make_vault(
                hvac_mock,
                token_lookup_data={"renewable": False, "ttl": 3600},
                token_renewal_enabled=True,
            )
        assert "not renewable" in caplog.text

    def test_startup_skips_check_when_renewal_disabled(self, hvac_mock):
        """No Vault API call when renewal is not configured."""
        vault, mock_client = self._make_vault(
            hvac_mock,
            token_lookup_data={"renewable": False, "ttl": 3600},
            token_renewal_enabled=False,
        )
        mock_client.auth.token.lookup_self.assert_not_called()

    def test_startup_handles_lookup_failure(self, hvac_mock):
        """Vault unreachable at startup should not crash Galaxy."""
        mock_client = MagicMock()
        hvac_mock.Client.return_value = mock_client
        mock_client.auth.token.lookup_self.side_effect = Exception("connection refused")
        config = {
            "vault_address": "http://localhost:8200",
            "vault_token": "s.test-token",
        }
        vault = HashicorpVault(config, token_renewal_enabled=True)
        assert vault.client is mock_client

    def test_renew_vault_token_if_needed_unwraps_decorators(self, hvac_mock):
        vault, mock_client = self._make_vault(
            hvac_mock,
            token_lookup_data={"renewable": True, "ttl": 3600},
        )
        mock_client.auth.token.renew_self.return_value = {"auth": {"lease_duration": 3600, "renewable": True}}
        # Wrap in decorators like VaultFactory does
        wrapped = VaultKeyValidationWrapper(VaultKeyPrefixWrapper(vault, prefix="/galaxy"))
        renew_vault_token_if_needed(wrapped)
        mock_client.auth.token.renew_self.assert_called_once()

    def test_renew_token_propagates_exception_on_failure(self, hvac_mock):
        vault, mock_client = self._make_vault(
            hvac_mock,
            token_lookup_data={"renewable": True, "ttl": 3600},
        )
        mock_client.auth.token.renew_self.side_effect = Exception("Vault sealed")
        with pytest.raises(Exception, match="Vault sealed"):
            vault.renew_token()

    def test_renew_vault_token_if_needed_noop_for_non_hashicorp(self, hvac_mock):
        # Should not raise for non-HashicorpVault
        renew_vault_token_if_needed(NullVault())

    def test_read_secret_forbidden_returns_none(self, hvac_mock):
        vault, mock_client = self._make_vault(hvac_mock)
        mock_client.secrets.kv.read_secret_version.side_effect = hvac_mock.exceptions.Forbidden
        result = vault.read_secret("some/key")
        assert result is None

    def test_write_secret_forbidden_raises(self, hvac_mock):
        vault, mock_client = self._make_vault(hvac_mock)
        mock_client.secrets.kv.v2.create_or_update_secret.side_effect = hvac_mock.exceptions.Forbidden
        with pytest.raises(hvac_mock.exceptions.Forbidden):
            vault.write_secret("some/key", "value")
