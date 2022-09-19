import abc
import logging
import os
import re
from typing import (
    List,
    Optional,
)

import yaml
from cryptography.fernet import (
    Fernet,
    MultiFernet,
)

try:
    from custos.clients.resource_secret_management_client import ResourceSecretManagementClient
    from custos.clients.utils.exceptions.CustosExceptions import KeyDoesNotExist
    from custos.transport.settings import CustosServerClientSettings

    logging.getLogger("custos.clients.resource_secret_management_client").setLevel(logging.CRITICAL)

    custos_sdk_available = True
except ImportError:
    custos_sdk_available = False

try:
    import hvac
except ImportError:
    hvac = None

from galaxy import model

log = logging.getLogger(__name__)

VAULT_KEY_INVALID_REGEX = re.compile(r"\s\/|\/\s|\/\/")


class InvalidVaultConfigException(Exception):
    pass


class InvalidVaultKeyException(Exception):
    pass


class Vault(abc.ABC):
    """
    A simple abstraction for reading/writing from external vaults.
    """

    @abc.abstractmethod
    def read_secret(self, key: str) -> Optional[str]:
        """
        Reads a secret from the vault.

        :param key: The key to read. Typically a hierarchical path such as `/galaxy/user/1/preferences/editor`
        :return: The string value stored at the key, such as 'ace_editor'.
        """

    @abc.abstractmethod
    def write_secret(self, key: str, value: str) -> None:
        """
        Write a secret to the vault.

        :param key: The key to write to. Typically a hierarchical path such as `/galaxy/user/1/preferences/editor`
        :param value: The value to write, such as 'vscode'
        :return:
        """

    @abc.abstractmethod
    def list_secrets(self, key: str) -> List[str]:
        """
        Lists secrets at a given path.

        :param key: The key prefix to list. e.g. `/galaxy/user/1/preferences`. A trailing slash is optional.
        :return: The list of subkeys at path. e.g.
                 ['/galaxy/user/1/preferences/editor`, '/galaxy/user/1/preferences/storage`]
                 Note that only immediate subkeys are returned.
        """


class NullVault(Vault):
    def read_secret(self, key: str) -> Optional[str]:
        raise InvalidVaultConfigException(
            "No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml"
        )

    def write_secret(self, key: str, value: str) -> None:
        raise InvalidVaultConfigException(
            "No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml"
        )

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class HashicorpVault(Vault):
    def __init__(self, config):
        if not hvac:
            raise InvalidVaultConfigException(
                "Hashicorp vault library 'hvac' is not available. Make sure hvac is installed."
            )
        self.vault_address = config.get("vault_address")
        self.vault_token = config.get("vault_token")
        self.client = hvac.Client(url=self.vault_address, token=self.vault_token)

    def read_secret(self, key: str) -> Optional[str]:
        try:
            response = self.client.secrets.kv.read_secret_version(path=key)
            return response["data"]["data"].get("value")
        except hvac.exceptions.InvalidPath:
            return None

    def write_secret(self, key: str, value: str) -> None:
        self.client.secrets.kv.v2.create_or_update_secret(path=key, secret={"value": value})

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class DatabaseVault(Vault):
    def __init__(self, sa_session, config):
        self.sa_session = sa_session
        self.encryption_keys = config.get("encryption_keys")
        self.fernet_keys = [Fernet(key.encode("utf-8")) for key in self.encryption_keys]

    def _get_multi_fernet(self) -> MultiFernet:
        return MultiFernet(self.fernet_keys)

    def _update_or_create(self, key: str, value: Optional[str]) -> model.Vault:
        vault_entry = self.sa_session.query(model.Vault).filter_by(key=key).first()
        if vault_entry:
            if value:
                vault_entry.value = value
                self.sa_session.merge(vault_entry)
                self.sa_session.flush()
        else:
            # recursively create parent keys
            parent_key, _, _ = key.rpartition("/")
            if parent_key:
                self._update_or_create(parent_key, None)
            vault_entry = model.Vault(key=key, value=value, parent_key=parent_key or None)
            self.sa_session.merge(vault_entry)
            self.sa_session.flush()
        return vault_entry

    def read_secret(self, key: str) -> Optional[str]:
        key_obj = self.sa_session.query(model.Vault).filter_by(key=key).first()
        if key_obj and key_obj.value:
            f = self._get_multi_fernet()
            return f.decrypt(key_obj.value.encode("utf-8")).decode("utf-8")
        return None

    def write_secret(self, key: str, value: str) -> None:
        f = self._get_multi_fernet()
        token = f.encrypt(value.encode("utf-8"))
        self._update_or_create(key=key, value=token.decode("utf-8"))

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class CustosVault(Vault):
    def __init__(self, config):
        if not custos_sdk_available:
            raise InvalidVaultConfigException(
                "Custos sdk library 'custos-sdk' is not available. Make sure the custos-sdk is installed."
            )
        custos_settings = CustosServerClientSettings(
            custos_host=config.get("custos_host"),
            custos_port=config.get("custos_port"),
            custos_client_id=config.get("custos_client_id"),
            custos_client_sec=config.get("custos_client_sec"),
        )
        self.client = ResourceSecretManagementClient(custos_settings)

    def read_secret(self, key: str) -> Optional[str]:
        try:
            response = self.client.get_kv_credential(key=key)
            return response.get("value")
        except KeyDoesNotExist:
            return None

    def write_secret(self, key: str, value: str) -> None:
        self.client.set_kv_credential(key=key, value=value)

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class UserVaultWrapper(Vault):
    def __init__(self, vault: Vault, user):
        self.vault = vault
        self.user = user

    def read_secret(self, key: str) -> Optional[str]:
        return self.vault.read_secret(f"user/{self.user.id}/{key}")

    def write_secret(self, key: str, value: str) -> None:
        return self.vault.write_secret(f"user/{self.user.id}/{key}", value)

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class VaultKeyValidationWrapper(Vault):
    """
    A decorator to standardize and validate vault key paths
    """

    def __init__(self, vault: Vault):
        self.vault = vault

    @staticmethod
    def validate_key(key):
        if not key:
            return False
        return not VAULT_KEY_INVALID_REGEX.search(key)

    def normalize_key(self, key):
        # remove leading and trailing slashes
        key = key.strip("/")
        if not self.validate_key(key):
            raise InvalidVaultKeyException(
                f"Vault key: {key} is invalid. Make sure that it is not empty, contains double slashes or contains"
                "whitespace before or after the separator."
            )
        return key

    def read_secret(self, key: str) -> Optional[str]:
        key = self.normalize_key(key)
        return self.vault.read_secret(key)

    def write_secret(self, key: str, value: str) -> None:
        key = self.normalize_key(key)
        return self.vault.write_secret(key, value)

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class VaultKeyPrefixWrapper(Vault):
    """
    Adds a prefix to all vault keys, such as the galaxy instance id
    """

    def __init__(self, vault: Vault, prefix: str):
        self.vault = vault
        self.prefix = prefix.strip("/")

    def read_secret(self, key: str) -> Optional[str]:
        return self.vault.read_secret(f"/{self.prefix}/{key}")

    def write_secret(self, key: str, value: str) -> None:
        return self.vault.write_secret(f"/{self.prefix}/{key}", value)

    def list_secrets(self, key: str) -> List[str]:
        raise NotImplementedError()


class VaultFactory:
    @staticmethod
    def load_vault_config(vault_conf_yml: str) -> Optional[dict]:
        if os.path.exists(vault_conf_yml):
            with open(vault_conf_yml) as f:
                return yaml.safe_load(f)
        return None

    @staticmethod
    def from_vault_type(app, vault_type: Optional[str], cfg: dict) -> Vault:
        vault: Vault
        if vault_type == "hashicorp":
            vault = HashicorpVault(cfg)
        elif vault_type == "database":
            vault = DatabaseVault(app.model.context, cfg)
        elif vault_type == "custos":
            vault = CustosVault(cfg)
        else:
            raise InvalidVaultConfigException(f"Unknown vault type: {vault_type}")
        vault_prefix = cfg.get("path_prefix") or "/galaxy"
        return VaultKeyValidationWrapper(VaultKeyPrefixWrapper(vault, prefix=vault_prefix))

    @staticmethod
    def from_app(app) -> Vault:
        vault_config = VaultFactory.load_vault_config(app.config.vault_config_file)
        if vault_config:
            return VaultFactory.from_vault_type(app, vault_config.get("type", None), vault_config)
        log.warning("No vault configured. We recommend defining the vault_config_file setting in galaxy.yml")
        return NullVault()
