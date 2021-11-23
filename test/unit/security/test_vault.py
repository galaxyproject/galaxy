import os
import string
import tempfile
import unittest
from abc import ABC

from cryptography.fernet import InvalidToken

from galaxy.app_unittest_utils.galaxy_mock import MockApp, MockAppConfig
from galaxy.security.vault import NullVault, Vault, VaultFactory


class VaultTestBase(ABC, unittest.TestCase):

    def __init__(self):
        self.vault = NullVault()  # type: Vault

    def test_read_write_secret(self):
        self.vault.write_secret("my/test/secret", "hello world")
        self.assertEqual(self.vault.read_secret("my/test/secret"), "hello world")

    def test_overwrite_secret(self):
        self.vault.write_secret("my/new/secret", "hello world")
        self.vault.write_secret("my/new/secret", "hello overwritten")
        self.assertEqual(self.vault.read_secret("my/new/secret"), "hello overwritten")


VAULT_CONF_HASHICORP = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_hashicorp.yaml")


class TestHashicorpVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        config = MockAppConfig(vault_config_file=VAULT_CONF_HASHICORP)
        app = MockApp(config=config)
        self.vault = VaultFactory.from_app(app)


VAULT_CONF_DATABASE = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database.yaml")
VAULT_CONF_DATABASE_ROTATED = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_rotated.yaml")
VAULT_CONF_DATABASE_INVALID = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_invalid_keys.yaml")


class TestDatabaseVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def test_rotate_keys(self):
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = VaultFactory.from_app(app)
        self.vault.write_secret("my/rotated/secret", "hello rotated")

        # should succeed after rotation
        app.config.vault_config_file = VAULT_CONF_DATABASE_ROTATED
        self.vault = VaultFactory.from_app(app)
        self.assertEqual(self.vault.read_secret("my/rotated/secret"), "hello rotated")

    def test_wrong_keys(self):
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = VaultFactory.from_app(app)
        self.vault.write_secret("my/incorrect/secret", "hello incorrect")

        # should fail because decryption keys are the wrong
        app.config.vault_config_file = VAULT_CONF_DATABASE_INVALID
        self.vault = VaultFactory.from_app(app)
        with self.assertRaises(InvalidToken):
            self.vault.read_secret("my/incorrect/secret")


VAULT_CONF_CUSTOS = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_custos.yaml")


class TestCustosVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", prefix="vault_custos", delete=False) as tempconf, open(VAULT_CONF_CUSTOS) as f:
            content = string.Template(f.read()).safe_substitute(custos_client_id=os.environ.get('CUSTOS_CLIENT_ID'),
                                                                custos_client_secret=os.environ.get('CUSTOS_CLIENT_SECRET'))
            tempconf.write(content)
            self.vault_temp_conf = tempconf.name
        config = MockAppConfig(vault_config_file=self.vault_temp_conf)
        app = MockApp(config=config)
        self.vault = VaultFactory.from_app(app)

    def tearDown(self) -> None:
        os.remove(self.vault_temp_conf)
