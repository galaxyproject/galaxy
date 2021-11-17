from abc import ABC
from cryptography.fernet import Fernet, MultiFernet
import json
import os
import yaml
try:
    import hvac
except ImportError:
    hvac = None

from galaxy import model


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

    def __init__(self, sa_session, config):
        self.sa_session = sa_session
        self.encryption_keys = config.get('encryption_keys')

    def _get_multi_fernet(self) -> MultiFernet:
        fernet_keys = [Fernet(key.encode('utf-8')) for key in self.encryption_keys]
        return MultiFernet(fernet_keys)

    def read_secret(self, path: str) -> dict:
        key_obj = self.sa_session.query(model.Vault).filter_by(key=path).first()
        if key_obj:
            f = self._get_multi_fernet()
            return json.loads(f.decrypt(key_obj.value.encode('utf-8')).decode('utf-8'))
        return None

    def write_secret(self, path: str, value: dict) -> None:
        f = self._get_multi_fernet()
        token = f.encrypt(json.dumps(value).encode('utf-8'))
        vault_entry = model.Vault(key=path, value=token.decode('utf-8'))
        self.sa_session.add(vault_entry)
        self.sa_session.flush()


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
    def from_vault_type(app, vault_type, cfg):
        if vault_type == "hashicorp":
            return HashicorpVault(cfg)
        elif vault_type == "database":
            return DatabaseVault(app.model.context, cfg)
        elif vault_type == "custos":
            return CustosVault(cfg)
        else:
            raise UnknownVaultTypeException(f"Unknown vault type: {vault_type}")

    @staticmethod
    def from_app_config(app):
        vault_config = VaultFactory.load_vault_config(app.config.vault_config_file)
        if vault_config:
            return VaultFactory.from_vault_type(app, vault_config.get('type'), vault_config)
        return None
