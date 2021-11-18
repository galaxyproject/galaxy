from abc import ABC
import os
import unittest

from galaxy.app_unittest_utils.galaxy_mock import MockApp, MockAppConfig
from galaxy.security import vault


class VaultTestBase(ABC):

    def test_read_write_secret(self):
        self.assertIsNone(self.vault.read_secret("my/test/secret"), "Vault secret should initially be empty")
        self.vault.write_secret("my/test/secret", {"value": "hello world"})
        self.assertEqual(self.vault.read_secret("my/test/secret"), {"value": "hello world"})

    def test_overwrite_secret(self):
        self.vault.write_secret("my/new/secret", {"value": "hello world"})
        self.vault.write_secret("my/new/secret", {"value": "hello overwritten"})
        self.assertEqual(self.vault.read_secret("my/new/secret"), {"value": "hello overwritten"})


VAULT_CONF_HASHICORP = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_hashicorp.yaml")


class TestHashicorpVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        config = MockAppConfig(vault_config_file=VAULT_CONF_HASHICORP)
        app = MockApp(config=config)
        self.vault = vault.VaultFactory.from_app_config(app)


VAULT_CONF_DATABASE = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database.yaml")
VAULT_CONF_DATABASE_ROTATED = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_rotated.yaml")
VAULT_CONF_DATABASE_INVALID = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_database_invalid_keys.yaml")


class TestDatabaseVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = vault.VaultFactory.from_app_config(app)

    def test_rotate_keys(self):
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = vault.VaultFactory.from_app_config(app)
        self.vault.write_secret("my/rotated/secret", {"value": "hello rotated"})

        # should succeed after rotation
        app.config.vault_config_file = VAULT_CONF_DATABASE_ROTATED
        self.vault = vault.VaultFactory.from_app_config(app)
        self.assertEqual(self.vault.read_secret("my/rotated/secret"), {"value": "hello rotated"})
        super().test_read_write_secret()

    def test_wrong_keys(self):
        config = MockAppConfig(vault_config_file=VAULT_CONF_DATABASE)
        app = MockApp(config=config)
        self.vault = vault.VaultFactory.from_app_config(app)
        self.vault.write_secret("my/incorrect/secret", {"value": "hello incorrect"})

        # should fail because decryption keys are the wrong
        app.config.vault_config_file = VAULT_CONF_DATABASE_INVALID
        self.vault = vault.VaultFactory.from_app_config(app)
        with self.assertRaises(Exception):
            self.vault.read_secret("my/incorrect/secret")
