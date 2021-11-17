class VaultTestBase:

    def test_read_write_secret(self):
        self.assertIsNone(self.vault.read_secret("my/test/secret"), "Vault secret should initially be empty")
        self.vault.write_secret("my/test/secret", {"value": "hello world"})
        self.assertEqual(self.vault.read_secret("my/test/secret"), {"value": "hello world"})
