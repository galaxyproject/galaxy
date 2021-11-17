import os
import unittest

from galaxy.security import vault


class VaultTestBase:

    def test_read_write_secret(self):
        self.assertIsNone(self.vault.read_secret("my/test/secret"), "Vault secret should initially be empty")
        self.vault.write_secret("my/test/secret", {"value": "hello world"})
        self.assertEqual(self.vault.read_secret("my/test/secret"), {"value": "hello world"})


VAULT_CONF_HASHICORP = os.path.join(os.path.dirname(__file__), "fixtures/vault_conf_hashicorp.yaml")


class MockAppConfig:

    def __init__(self, vault_conf_file):
        self.vault_config_file = vault_conf_file


class TestHashicorpVault(VaultTestBase, unittest.TestCase):

    def setUp(self) -> None:
        config = MockAppConfig(vault_conf_file=VAULT_CONF_HASHICORP)
        self.vault = vault.VaultFactory.from_app_config(config)
