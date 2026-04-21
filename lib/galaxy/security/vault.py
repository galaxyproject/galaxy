import abc
import logging
import os
import re
from typing import (
    Optional,
)

import yaml
from cryptography.fernet import (
    Fernet,
    MultiFernet,
)
from sqlalchemy import select

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
    def list_secrets(self, key: str) -> list[str]:
        """
        Lists secrets at a given path.

        :param key: The key prefix to list. e.g. `/galaxy/user/1/preferences`. A trailing slash is optional.
        :return: The list of subkeys at path. e.g.
                 ['/galaxy/user/1/preferences/editor`, '/galaxy/user/1/preferences/storage`]
                 Note that only immediate subkeys are returned.
        """

    def delete_secret(self, key: str) -> None:
        """
        Eliminate a secret from the target vault.

        Ideally the entry in the target source if removed, but by default the secret is
        simply overwritten with the empty string as its value.

        :param key: The key to write to. Typically a hierarchical path such as `/galaxy/user/1/preferences/editor`
        :param value: The value to write, such as 'vscode'
        :return:
        """
        self.write_secret(key, "")


class NullVault(Vault):
    def read_secret(self, key: str) -> Optional[str]:
        raise InvalidVaultConfigException(
            "No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml"
        )

    def write_secret(self, key: str, value: str) -> None:
        raise InvalidVaultConfigException(
            "No vault configured. Make sure the vault_config_file setting is defined in galaxy.yml"
        )

    def list_secrets(self, key: str) -> list[str]:
        raise NotImplementedError()


class HashicorpVault(Vault):
    def __init__(self, config, token_renewal_enabled=False):
        if not hvac:
            raise InvalidVaultConfigException(
                "Hashicorp vault library 'hvac' is not available. Make sure hvac is installed."
            )
        self.vault_address = config.get("vault_address")
        self.vault_token = config.get("vault_token")
        self.client = hvac.Client(url=self.vault_address, token=self.vault_token)
        if token_renewal_enabled:
            self._check_token_renewable()

    def _check_token_renewable(self):
        try:
            token_info = self.client.auth.token.lookup_self()
            data = token_info.get("data", {})
            renewable = data.get("renewable", False)
            ttl = data.get("ttl", 0)
            if not renewable:
                log.error(
                    "Hashicorp Vault token is not renewable, but vault_token_renewal_interval is set. "
                    "The token will expire and cannot be renewed. "
                    "Generate a renewable token with: vault token create -policy=<policy> -ttl=1h -explicit-max-ttl=720h -renewable"
                )
            elif ttl > 0:
                log.info("Hashicorp Vault token is renewable (TTL: %ds).", ttl)
            else:
                log.info("Hashicorp Vault token is renewable (no TTL).")
        except Exception:
            log.exception("Failed to look up Hashicorp Vault token info.")

    def renew_token(self):
        """Renew the Vault token. Intended to be called periodically by a Celery Beat task."""
        result = self.client.auth.token.renew_self()
        auth_data = result.get("auth", {})
        new_ttl = auth_data.get("lease_duration", 0)
        renewable = auth_data.get("renewable", False)
        if not renewable:
            log.error(
                "Hashicorp Vault token is no longer renewable (max TTL likely reached). "
                "A new token must be configured."
            )
        else:
            log.debug("Hashicorp Vault token renewed successfully (new TTL: %ds).", new_ttl)

    def read_secret(self, key: str) -> Optional[str]:
        try:
            response = self.client.secrets.kv.read_secret_version(path=key)
            return response["data"]["data"].get("value")
        except hvac.exceptions.InvalidPath:
            return self._read_legacy_and_migrate(key)
        except hvac.exceptions.Forbidden:
            log.error(
                "Permission denied reading secret at key: %s. "
                "The Vault token may have expired. Check token renewal configuration.",
                key,
            )
            return None

    def _read_legacy_and_migrate(self, key: str) -> Optional[str]:
        # Galaxy < 26.x emitted a leading slash in Vault paths, which hvac's
        # format_url turned into a double-slash KV v2 key. Vault 1.x accepted
        # it silently; Vault 2.0 rejects it. Fall back to reading the legacy
        # form and rewrite under the canonical key so the secret survives the
        # Galaxy upgrade. This fallback can be removed after a deprecation
        # window once operators have migrated.
        legacy = f"/{key}"
        try:
            response = self.client.secrets.kv.read_secret_version(path=legacy)
        except (hvac.exceptions.InvalidPath, hvac.exceptions.InvalidRequest):
            log.exception(f"Failed to read secret from Hashicorp Vault at key: {key}")
            return None
        value = response["data"]["data"].get("value")
        if value is not None:
            log.warning("Migrating legacy non-canonical Vault secret to canonical path: %s", key)
            self.client.secrets.kv.v2.create_or_update_secret(path=key, secret={"value": value})
        return value

    def write_secret(self, key: str, value: str) -> None:
        try:
            self.client.secrets.kv.v2.create_or_update_secret(path=key, secret={"value": value})
        except hvac.exceptions.Forbidden:
            log.error(
                "Permission denied writing secret at key: %s. "
                "The Vault token may have expired. Check token renewal configuration.",
                key,
            )
            raise

    def list_secrets(self, key: str) -> list[str]:
        raise NotImplementedError()


class DatabaseVault(Vault):
    def __init__(self, sa_session, config):
        self.sa_session = sa_session
        self.encryption_keys = config.get("encryption_keys")
        self.fernet_keys = [Fernet(key.encode("utf-8")) for key in self.encryption_keys]

    def _get_multi_fernet(self) -> MultiFernet:
        return MultiFernet(self.fernet_keys)

    def _update_or_create(self, key: str, value: Optional[str]) -> model.Vault:
        vault_entry = self._get_vault_value(key)
        if vault_entry:
            if value:
                vault_entry.value = value
                self.sa_session.merge(vault_entry)
                self.sa_session.commit()
        else:
            # recursively create parent keys
            parent_key, _, _ = key.rpartition("/")
            if parent_key:
                self._update_or_create(parent_key, None)
            vault_entry = model.Vault(key=key, value=value, parent_key=parent_key or None)
            self.sa_session.merge(vault_entry)
            self.sa_session.commit()
        return vault_entry

    def read_secret(self, key: str) -> Optional[str]:
        key_obj = self._get_vault_value(key)
        if key_obj and key_obj.value:
            f = self._get_multi_fernet()
            return f.decrypt(key_obj.value.encode("utf-8")).decode("utf-8")
        return None

    def write_secret(self, key: str, value: str) -> None:
        f = self._get_multi_fernet()
        token = f.encrypt(value.encode("utf-8"))
        self._update_or_create(key=key, value=token.decode("utf-8"))

    def delete_secret(self, key: str) -> None:
        vault_entry = self.sa_session.query(model.Vault).filter_by(key=key).first()
        self.sa_session.delete(vault_entry)
        self.sa_session.flush()

    def list_secrets(self, key: str) -> list[str]:
        raise NotImplementedError()

    def _get_vault_value(self, key):
        stmt = select(model.Vault).filter_by(key=key).limit(1)
        return self.sa_session.scalars(stmt).first()


class UserVaultWrapper(Vault):
    def __init__(self, vault: Vault, user):
        self.vault = vault
        self.user = user

    def read_secret(self, key: str) -> Optional[str]:
        if self.user:
            return self.vault.read_secret(f"user/{self.user.id}/{key}")
        else:
            return None

    def write_secret(self, key: str, value: str) -> None:
        return self.vault.write_secret(f"user/{self.user.id}/{key}", value)

    def list_secrets(self, key: str) -> list[str]:
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

    def list_secrets(self, key: str) -> list[str]:
        raise NotImplementedError()


class VaultKeyPrefixWrapper(Vault):
    """
    Adds a prefix to all vault keys, such as the galaxy instance id
    """

    def __init__(self, vault: Vault, prefix: str):
        self.vault = vault
        # Strip conventional outer slashes so admins can write `/galaxy`,
        # `galaxy`, or `/galaxy/` interchangeably in config. Reject anything
        # that would still produce a non-canonical Vault path after stripping.
        stripped = prefix.strip("/")
        if not stripped or VAULT_KEY_INVALID_REGEX.search(stripped):
            raise InvalidVaultConfigException(
                f"Vault path_prefix {prefix!r} is invalid: must be non-empty and must not contain "
                "double slashes or whitespace adjacent to a slash."
            )
        self.prefix = stripped

    def read_secret(self, key: str) -> Optional[str]:
        return self.vault.read_secret(f"{self.prefix}/{key}")

    def write_secret(self, key: str, value: str) -> None:
        return self.vault.write_secret(f"{self.prefix}/{key}", value)

    def list_secrets(self, key: str) -> list[str]:
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
            token_renewal_enabled = app.config.vault_token_renewal_interval > 0
            vault = HashicorpVault(cfg, token_renewal_enabled=token_renewal_enabled)
        elif vault_type == "database":
            vault = DatabaseVault(app.model.context, cfg)
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


def is_vault_configured(vault: Vault) -> bool:
    return not isinstance(vault, NullVault)


def _unwrap_vault(vault: Vault) -> Vault:
    """Unwrap decorator layers to get the underlying vault implementation."""
    while hasattr(vault, "vault"):
        vault = vault.vault
    return vault


def renew_vault_token_if_needed(vault: Vault) -> None:
    """Renew the Hashicorp Vault token if the vault is a HashicorpVault.

    Intended to be called from a Celery Beat periodic task.
    """
    inner = _unwrap_vault(vault)
    if isinstance(inner, HashicorpVault):
        inner.renew_token()
