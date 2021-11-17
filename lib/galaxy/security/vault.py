from abc import ABC
import os
import yaml
try:
    import hvac
except ImportError:
    hvac = None


class UnknownVaultTypeException(Exception):
    pass


class Vault(ABC):

    def read_secret(self, path: str) -> dict:
        pass

    def write_secret(self, path: str, value: dict) -> None:
        pass


class HashicorpVault(Vault):

    def __init__(self, config):
        if not hvac:
            raise UnknownVaultTypeException("Hashicorp vault library 'hvac' is not available. Make sure hvac is installed.")
        self.vault_address = config.get('vault_address')
        self.vault_token = config.get('vault_token')
        self.client = hvac.Client(url=self.vault_address, token=self.vault_token)

    def read_secret(self, path: str) -> dict:
        try:
            response = self.client.secrets.kv.read_secret_version(path=path)
            return response['data']['data']
        except hvac.exceptions.InvalidPath:
            return None

    def write_secret(self, path: str, value: dict) -> None:
        self.client.secrets.kv.v2.create_or_update_secret(path=path, secret=value)


class DatabaseVault(Vault):
    pass


class CustosVault(Vault):
    pass


class UserVaultWrapper(Vault):

    def __init__(self, vault: Vault, user):
        self.vault = vault
        self.user = user

    def read_secret(self, path: str) -> dict:
        return self.vault.read_secret(f"user/{self.user.id}/{path}")

    def write_secret(self, path: str, value: dict) -> None:
        return self.vault.write_secret(f"user/{self.user.id}/{path}", value)


class VaultFactory(object):

    @staticmethod
    def load_vault_config(vault_conf_yml):
        if os.path.exists(vault_conf_yml):
            with open(vault_conf_yml) as f:
                return yaml.safe_load(f)
        return None

    @staticmethod
    def from_vault_type(vault_type, cfg):
        if vault_type == "hashicorp":
            return HashicorpVault(cfg)
        elif vault_type == "database":
            return DatabaseVault(cfg)
        elif vault_type == "custos":
            return CustosVault(cfg)
        else:
            raise UnknownVaultTypeException(f"Unknown vault type: {vault_type}")

    @staticmethod
    def from_app_config(config):
        vault_config = VaultFactory.load_vault_config(config.vault_config_file)
        if vault_config:
            return VaultFactory.from_vault_type(vault_config.get('type'), vault_config)
        return None
