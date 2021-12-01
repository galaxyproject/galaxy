import abc
import json
import logging
import os
import re
from typing import Optional

import yaml
from cryptography.fernet import Fernet, MultiFernet

try:
    from custos.clients.resource_secret_management_client import ResourceSecretManagementClient
    from custos.transport.settings import CustosServerClientSettings
    import custos.clients.utils.utilities as custos_util
    custos_sdk_available = True
except ImportError:
    custos_sdk_available = False

try:
    import hvac
except ImportError:
    hvac = None

from galaxy import model

log = logging.getLogger(__name__)

VAULT_KEY_REGEX = re.compile(r"\s\/|\/\s|\/\/")


class UnknownVaultTypeException(Exception):
    pass


class InvalidVaultKeyException(Exception):
    pass


class Vault(abc.ABC):

    def validate_key(self, key):
        if not key:
            return False
        return not VAULT_KEY_REGEX.search(key)

    def normalize_key(self, key):
        # remove leading and trailing slashes
        key = key.strip("/")
        if not self.validate_key(key):
            raise InvalidVaultKeyException(
                f"Vault key: {key} is invalid. Make sure that it is not empty, contains double slashes or contains"
                "whitespace before or after the separator.")
        return key

    @abc.abstractmethod
    def read_secret(self, key: str) -> Optional[str]:
        pass

    @abc.abstractmethod
    def write_secret(self, key: str, value: str) -> None:
        pass


class NullVault(Vault):

    def read_secret(self, key: str) -> Optional[str]:
        raise UnknownVaultTypeException("No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml")

    def write_secret(self, key: str, value: str) -> None:
        raise UnknownVaultTypeException("No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml")


class HashicorpVault(Vault):

    def __init__(self, config):
        if not hvac:
            raise UnknownVaultTypeException("Hashicorp vault library 'hvac' is not available. Make sure hvac is installed.")
        self.vault_address = config.get('vault_address')
        self.vault_token = config.get('vault_token')
        self.client = hvac.Client(url=self.vault_address, token=self.vault_token)

    def read_secret(self, key: str) -> Optional[str]:
        key = self.normalize_key(key)
        try:
            response = self.client.secrets.kv.read_secret_version(path=key)
            return response['data']['data'].get('value')
        except hvac.exceptions.InvalidPath:
            return None

    def write_secret(self, key: str, value: str) -> None:
        key = self.normalize_key(key)
        self.client.secrets.kv.v2.create_or_update_secret(path=key, secret={'value': value})


class DatabaseVault(Vault):

    def __init__(self, sa_session, config):
        self.sa_session = sa_session
        self.encryption_keys = config.get('encryption_keys')
        self.fernet_keys = [Fernet(key.encode('utf-8')) for key in self.encryption_keys]

    def _get_multi_fernet(self) -> MultiFernet:
        return MultiFernet(self.fernet_keys)

    def _update_or_create(self, key: str, value: str):
        vault_entry = self.sa_session.query(model.Vault).filter_by(key=key).first()
        if vault_entry:
            vault_entry.value = value
        else:
            vault_entry = model.Vault(key=key, value=value)
        self.sa_session.merge(vault_entry)
        self.sa_session.flush()

    def read_secret(self, key: str) -> Optional[str]:
        key = self.normalize_key(key)
        key_obj = self.sa_session.query(model.Vault).filter_by(key=key).first()
        if key_obj:
            f = self._get_multi_fernet()
            return f.decrypt(key_obj.value.encode('utf-8')).decode('utf-8')
        return None

    def write_secret(self, key: str, value: str) -> None:
        key = self.normalize_key(key)
        f = self._get_multi_fernet()
        token = f.encrypt(value.encode('utf-8'))
        self._update_or_create(key=key, value=token.decode('utf-8'))


class CustosVault(Vault):

    def __init__(self, config):
        if not custos_sdk_available:
            raise UnknownVaultTypeException("Custos sdk library 'custos-sdk' is not available. Make sure the custos-sdk is installed.")
        self.custos_settings = CustosServerClientSettings(custos_host=config.get('custos_host'),
                                                          custos_port=config.get('custos_port'),
                                                          custos_client_id=config.get('custos_client_id'),
                                                          custos_client_sec=config.get('custos_client_sec'))
        self.b64_encoded_custos_token = custos_util.get_token(custos_settings=self.custos_settings)
        self.client = ResourceSecretManagementClient(self.custos_settings)

    def read_secret(self, key: str) -> Optional[str]:
        key = self.normalize_key(key)
        try:
            response = self.client.get_KV_credential(token=self.b64_encoded_custos_token,
                                                     client_id=self.custos_settings.CUSTOS_CLIENT_ID,
                                                     key=key)
            return json.loads(response).get('value')
        except Exception:
            return None

    def write_secret(self, key: str, value: str) -> None:
        key = self.normalize_key(key)
        if self.read_secret(key):
            self.client.update_KV_credential(token=self.b64_encoded_custos_token,
                                             client_id=self.custos_settings.CUSTOS_CLIENT_ID,
                                             key=key, value=value)
        else:
            self.client.set_KV_credential(token=self.b64_encoded_custos_token,
                                          client_id=self.custos_settings.CUSTOS_CLIENT_ID,
                                          key=key, value=value)


class UserVaultWrapper(Vault):

    def __init__(self, vault: Vault, user):
        self.vault = vault
        self.user = user

    def read_secret(self, key: str) -> Optional[str]:
        return self.vault.read_secret(f"user/{self.user.id}/{key}")

    def write_secret(self, key: str, value: str) -> None:
        return self.vault.write_secret(f"user/{self.user.id}/{key}", value)


class VaultFactory(object):

    @staticmethod
    def load_vault_config(vault_conf_yml: str) -> Optional[dict]:
        if os.path.exists(vault_conf_yml):
            with open(vault_conf_yml) as f:
                return yaml.safe_load(f)
        return None

    @staticmethod
    def from_vault_type(app, vault_type: Optional[str], cfg: dict) -> Vault:
        if vault_type == "hashicorp":
            return HashicorpVault(cfg)
        elif vault_type == "database":
            return DatabaseVault(app.model.context, cfg)
        elif vault_type == "custos":
            return CustosVault(cfg)
        else:
            raise UnknownVaultTypeException(f"Unknown vault type: {vault_type}")

    @staticmethod
    def from_app(app) -> Vault:
        vault_config = VaultFactory.load_vault_config(app.config.vault_config_file)
        if vault_config:
            return VaultFactory.from_vault_type(app, vault_config.get('type', None), vault_config)
        log.warning("No vault configured. We recommend defining the vault_config_file setting in galaxy.yml")
        return NullVault()
