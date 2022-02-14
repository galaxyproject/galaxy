import os
import string
import tempfile
import unittest
from abc import ABC

from cryptography.fernet import InvalidToken

from galaxy.model.unittest_utils.data_app import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.security.vault import (
    InvalidVaultKeyException,
    Vault,
    VaultFactory,
)


class VaultTestBase(ABC):
    vault: Vault

    def test_read_write_secret(self):
        self.vault.write_secret("my/test/secret", "hello world")
        self.assertEqual(self.vault.read_secret("my/test/secret"), "hello world")  # type: ignore

    def test_overwrite_secret(self):
        self.vault.write_secret("my/new/secret", "hello world")
        self.vault.write_secret("my/new/secret", "hello overwritten")
        self.assertEqual(self.vault.read_secret("my/new/secret"), "hello overwritten")  # type: ignore

    def test_valid_paths(self):
        with self.assertRaises(InvalidVaultKeyException):  # type: ignore
            self.vault.write_secret("", "hello world")
        with self.assertRaises(InvalidVaultKeyException):  # type: ignore
            self.vault.write_secret("my//new/secret", "hello world")
        with self.assertRaises(InvalidVaultKeyException):  # type: ignore
            self.vault.write_secret("my/ /new/secret", "hello world")
        # leading and trailing slashes should be ignored
        self.vault.write_secret("/my/new/secret with space/", "hello overwritten")
        self.assertEqual(self.vault.read_secret("my/new/secret with space"), "hello overwritten")  # type: ignore


VAULT_CONF_HASHICORP = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_hashicorp.yml")


@unittest.skipIf(
    not os.environ.get("VAULT_ADDRESS") or not os.environ.get("VAULT_TOKEN"),
    "VAULT_ADDRESS and VAULT_TOKEN env vars not set",
)
class TestHashicorpVault(VaultTestBase, unittest.TestCase):
    def setUp(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", prefix="vault_hashicorp", delete=False) as tempconf, open(
            VAULT_CONF_HASHICORP
        ) as f:
            content = string.Template(f.read()).safe_substitute(
                vault_address=os.environ.get("VAULT_ADDRESS"), vault_token=os.environ.get("VAULT_TOKEN")
            )
            tempconf.write(content)
            self.vault_temp_conf = tempconf.name
        config = GalaxyDataTestConfig(vault_config_file=self.vault_temp_conf)
        app = GalaxyDataTestApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def tearDown(self) -> None:
        os.remove(self.vault_temp_conf)


VAULT_CONF_DATABASE = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database.yml")
VAULT_CONF_DATABASE_ROTATED = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_rotated.yml")
VAULT_CONF_DATABASE_INVALID = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_invalid_keys.yml")


class TestDatabaseVault(VaultTestBase, unittest.TestCase):
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
        app.config.vault_config_file = VAULT_CONF_DATABASE_ROTATED  # type: ignore
        vault = VaultFactory.from_app(app)
        self.assertEqual(vault.read_secret("my/rotated/secret"), "hello rotated")

    def test_wrong_keys(self):
        config = GalaxyDataTestConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = GalaxyDataTestApp(config=config)
        vault = VaultFactory.from_app(app)
        vault.write_secret("my/incorrect/secret", "hello incorrect")

        # should fail because decryption keys are the wrong
        app.config.vault_config_file = VAULT_CONF_DATABASE_INVALID  # type: ignore
        vault = VaultFactory.from_app(app)
        with self.assertRaises(InvalidToken):
            vault.read_secret("my/incorrect/secret")


VAULT_CONF_CUSTOS = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_custos.yml")


@unittest.skipIf(
    not os.environ.get("CUSTOS_CLIENT_ID") or not os.environ.get("CUSTOS_CLIENT_SECRET"),
    "CUSTOS_CLIENT_ID and CUSTOS_CLIENT_SECRET env vars not set",
)
class TestCustosVault(VaultTestBase, unittest.TestCase):
    def setUp(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", prefix="vault_custos", delete=False) as tempconf, open(
            VAULT_CONF_CUSTOS
        ) as f:
            content = string.Template(f.read()).safe_substitute(
                custos_client_id=os.environ.get("CUSTOS_CLIENT_ID"),
                custos_client_secret=os.environ.get("CUSTOS_CLIENT_SECRET"),
            )
            tempconf.write(content)
            self.vault_temp_conf = tempconf.name
        config = GalaxyDataTestConfig(vault_config_file=self.vault_temp_conf)
        app = GalaxyDataTestApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def tearDown(self) -> None:
        os.remove(self.vault_temp_conf)
