from abc import ABC
import os
import yaml


class UnknownVaultTypeException(Exception):
    pass


class Vault(ABC):

    def read_secret(self, path: str) -> dict:
        pass

    def write_secret(self, path: str, value: dict) -> None:
        pass


class HashicorpVault(Vault):
    pass


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
