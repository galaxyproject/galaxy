"""
Utilities for encrypting sensitive headers using Galaxy's Vault system.

This module provides functionality to:
1. Identify sensitive headers that should be encrypted
2. Encrypt/decrypt headers using the vault
3. Transform data structures to use vault references for sensitive headers

This can be used for any scenario where HTTP headers containing sensitive information
(like authorization tokens, API keys, etc.) need to be stored securely in the database.
"""

import logging
import re
from typing import (
    Any,
    Optional,
)

from galaxy.security.vault import Vault

# Headers that should always be encrypted when stored in the database
SENSITIVE_HEADER_PATTERNS = [
    # Auth patterns (covers authorization, authentication, auth, oauth, x-auth, etc.)
    re.compile(r".*auth.*", re.IGNORECASE),
    # Key patterns (API-Key, Auth-Key, X-API-Key, etc.)
    re.compile(r".*key$", re.IGNORECASE),
    # Token patterns (Bearer-Token, API-Token, X-TOKEN, etc.)
    re.compile(r".*token$", re.IGNORECASE),
    # Secret patterns (Client-Secret, API-Secret, etc.)
    re.compile(r".*secret$", re.IGNORECASE),
    # Cookie patterns
    re.compile(r".*cookie.*", re.IGNORECASE),
    # Bearer (standalone)
    re.compile(r"^bearer$", re.IGNORECASE),
]

# Default vault key prefix for headers
DEFAULT_VAULT_KEY_PREFIX = "headers"

log = logging.getLogger(__name__)


def is_sensitive_header(header_name: str) -> bool:
    for pattern in SENSITIVE_HEADER_PATTERNS:
        if pattern.match(header_name):
            return True
    return False


def create_vault_key(context_id: str, header_name: str, key_prefix: Optional[str] = None) -> str:
    """
    Create a vault key for storing a header value.

    Args:
        context_id: Unique identifier for the context (e.g., UUID of a request, session ID, etc.)
        header_name: Name of the header (will be normalized to lowercase)
        key_prefix: Optional custom prefix for the vault key. Defaults to DEFAULT_VAULT_KEY_PREFIX

    Returns:
        Vault key path for the header
    """
    if key_prefix is None:
        key_prefix = DEFAULT_VAULT_KEY_PREFIX
    normalized_header = header_name.lower().replace("-", "_")
    return f"{key_prefix}/{context_id}/{normalized_header}"


def create_vault_reference(header_name: str, reference_prefix: str = "VAULT_HEADER") -> str:
    """
    Create a vault reference placeholder that will be stored in data structures.

    Args:
        header_name: Name of the header
        reference_prefix: Prefix for the vault reference. Defaults to "VAULT_HEADER"

    Returns:
        Vault reference string that indicates this value should be decrypted
    """
    return f"__{reference_prefix}_{header_name.upper().replace('-', '_')}__"


def encrypt_headers_in_data(
    data: dict, context_id: str, vault: Vault, key_prefix: Optional[str] = None, reference_prefix: str = "VAULT_HEADER"
) -> dict:
    """
    Recursively process data structure to encrypt sensitive headers.

    This function walks through a dictionary structure and:
    1. Identifies elements with headers
    2. Encrypts sensitive headers to the vault
    3. Replaces sensitive header values with vault references

    Args:
        data: The data dictionary structure containing headers
        context_id: Unique identifier for the context (e.g., UUID, session ID, etc.)
        vault: Vault instance for encryption
        key_prefix: Optional custom prefix for vault keys. Defaults to DEFAULT_VAULT_KEY_PREFIX
        reference_prefix: Prefix for vault references. Defaults to "VAULT_HEADER"

    Returns:
        Modified data structure with sensitive headers encrypted
    """
    # Make a deep copy to avoid modifying the original
    encrypted_data: dict[str, Any] = {}

    for key, value in data.items():
        if key == "headers" and isinstance(value, dict):
            encrypted_data[key] = _encrypt_headers_dict(value, context_id, vault, key_prefix, reference_prefix)
        elif isinstance(value, dict):
            encrypted_data[key] = encrypt_headers_in_data(value, context_id, vault, key_prefix, reference_prefix)
        elif isinstance(value, list):
            encrypted_data[key] = [
                (
                    encrypt_headers_in_data(item, context_id, vault, key_prefix, reference_prefix)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        else:
            encrypted_data[key] = value

    return encrypted_data


def decrypt_headers_in_data(
    data: dict, context_id: str, vault: Vault, key_prefix: Optional[str] = None, reference_prefix: str = "VAULT_HEADER"
) -> dict:
    """
    Recursively process data structure to decrypt sensitive headers from vault.

    This function walks through a dictionary structure and:
    1. Identifies vault references in headers
    2. Decrypts the actual header values from the vault
    3. Replaces vault references with actual header values

    Args:
        data: The data dictionary structure with vault references
        context_id: Unique identifier for the context (e.g., UUID, session ID, etc.)
        vault: Vault instance for decryption
        key_prefix: Optional custom prefix for vault keys. Defaults to DEFAULT_VAULT_KEY_PREFIX
        reference_prefix: Prefix for vault references. Defaults to "VAULT_HEADER"

    Returns:
        Modified data structure with actual header values restored
    """
    # Make a deep copy to avoid modifying the original
    decrypted_data: dict[str, Any] = {}

    for key, value in data.items():
        if key == "headers" and isinstance(value, dict):
            decrypted_data[key] = _decrypt_headers_dict(value, context_id, vault, key_prefix, reference_prefix)
        elif isinstance(value, dict):
            decrypted_data[key] = decrypt_headers_in_data(value, context_id, vault, key_prefix, reference_prefix)
        elif isinstance(value, list):
            decrypted_data[key] = [
                (
                    decrypt_headers_in_data(item, context_id, vault, key_prefix, reference_prefix)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        else:
            decrypted_data[key] = value

    return decrypted_data


def _encrypt_headers_dict(
    headers: dict[str, str],
    context_id: str,
    vault: Vault,
    key_prefix: Optional[str] = None,
    reference_prefix: str = "VAULT_HEADER",
) -> dict[str, str]:
    """
    Encrypt sensitive headers in a headers dictionary.

    Args:
        headers: Dictionary of header name -> header value
        context_id: Unique identifier for the context
        vault: Vault instance for encryption
        key_prefix: Optional custom prefix for vault keys
        reference_prefix: Prefix for vault references

    Returns:
        Dictionary with sensitive headers replaced by vault references
    """
    encrypted_headers = {}
    for header_name, header_value in headers.items():
        if is_sensitive_header(header_name):
            # Encrypt sensitive header
            vault_key = create_vault_key(context_id, header_name, key_prefix)
            vault.write_secret(vault_key, header_value)
            encrypted_headers[header_name] = create_vault_reference(header_name, reference_prefix)
        else:
            # Keep non-sensitive headers as-is
            encrypted_headers[header_name] = header_value
    return encrypted_headers


def _decrypt_headers_dict(
    headers: dict[str, str],
    context_id: str,
    vault: Vault,
    key_prefix: Optional[str] = None,
    reference_prefix: str = "VAULT_HEADER",
) -> dict[str, str]:
    """
    Decrypt vault references in a headers dictionary.

    Args:
        headers: Dictionary of header name -> header value (may contain vault references)
        context_id: Unique identifier for the context
        vault: Vault instance for decryption
        key_prefix: Optional custom prefix for vault keys
        reference_prefix: Prefix for vault references

    Returns:
        Dictionary with vault references replaced by actual header values
    """
    decrypted_headers = {}
    for header_name, header_value in headers.items():
        if isinstance(header_value, str) and header_value.startswith(f"__{reference_prefix}_"):
            # Decrypt vault reference
            vault_key = create_vault_key(context_id, header_name, key_prefix)
            decrypted_value = vault.read_secret(vault_key)
            if decrypted_value is not None:
                decrypted_headers[header_name] = decrypted_value
            else:
                # Handle case where vault key doesn't exist (shouldn't happen in normal flow)
                log.warning(
                    f"Vault key not found for header '{header_name}' with key '{vault_key}'. Keeping vault reference as fallback."
                )
                decrypted_headers[header_name] = header_value  # Keep vault reference as fallback
        else:
            # Keep non-vault headers as-is
            decrypted_headers[header_name] = header_value
    return decrypted_headers
