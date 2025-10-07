"""
Utilities for encrypting sensitive headers using Galaxy's Vault system.

This module provides functionality to:
1. Identify sensitive headers that should be encrypted based on configuration
2. Encrypt/decrypt headers using the vault
3. Transform data structures to use vault references for sensitive headers

This can be used for any scenario where HTTP headers containing sensitive information
(like authorization tokens, API keys, etc.) need to be stored securely in the database.
Header sensitivity is determined by the URL headers configuration file.
"""

import logging
from typing import (
    Any,
    Optional,
)

from galaxy.config.url_headers import UrlHeadersConfig
from galaxy.security.vault import Vault

# Default vault key prefix for headers
DEFAULT_VAULT_KEY_PREFIX = "headers"

log = logging.getLogger(__name__)


def is_sensitive_header(
    header_name: str, url_headers_config: Optional[UrlHeadersConfig] = None, url: Optional[str] = None
) -> bool:
    """
    Check if a header contains sensitive information and should be encrypted.

    Args:
        header_name: The header name to check
        url_headers_config: URL headers configuration. This is required to determine
                           sensitivity as we no longer use hardcoded patterns.
        url: Optional target URL for URL-specific header validation

    Returns:
        True if the header should be encrypted, False otherwise
    """
    if url_headers_config:
        if url:
            return url_headers_config.is_header_sensitive_for_url(header_name, url)
        else:
            # No URL provided - cannot perform URL-specific sensitivity checking
            # In our pattern-based system, headers without URLs cannot be properly validated
            # Default to not sensitive (individual header checking should not fail fast)
            log.debug(f"No URL provided for sensitivity check of header '{header_name}' - defaulting to not sensitive")
            return False

    # No configuration provided - default to not sensitive for security
    # (better to not encrypt than to encrypt everything without knowing)
    log.debug(
        f"No URL headers configuration provided for sensitivity check of header '{header_name}' - defaulting to not sensitive"
    )
    return False


def has_sensitive_headers(
    data: dict, url_headers_config: Optional[UrlHeadersConfig] = None, url: Optional[str] = None
) -> bool:
    """
    Check if the data structure contains any sensitive headers that would require encryption.

    This function recursively searches through a dictionary structure to detect
    if any sensitive headers are present that would need to be encrypted.

    IMPORTANT: This function fails fast if headers are found but no configuration
    is provided.

    Args:
        data: The data dictionary structure to check for sensitive headers
        url_headers_config: URL headers configuration for sensitivity checks (required if headers present)
        url: Optional target URL for URL-specific header validation

    Returns:
        True if sensitive headers are found, False otherwise

    Raises:
        ValueError: If headers are present but no configuration is provided
    """
    if not url_headers_config:
        # Without configuration, headers are not allowed at all
        # Fail fast if any headers are found anywhere in the data structure
        def check_for_headers(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "headers" and isinstance(value, dict) and value:
                        header_names = list(value.keys())
                        raise ValueError(
                            f"Headers are not allowed without proper URL headers configuration. "
                            f"Found headers: {header_names}. "
                            f"Please configure url_headers_config_file in Galaxy configuration to enable header usage."
                        )
                    elif isinstance(value, (dict, list)):
                        check_for_headers(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        check_for_headers(item)

        check_for_headers(data)
        return False

    # Configuration exists - check for sensitive headers recursively
    def check_sensitivity(obj, inherited_url=None):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "headers" and isinstance(value, dict) and value:
                    # Look for a URL at the same level as the headers (e.g., in UrlDataElement)
                    element_url = obj.get("url") if "url" in obj else inherited_url

                    if not element_url:
                        # No URL available - cannot perform URL-specific sensitivity checking
                        # In a pattern-based system, headers without URLs cannot be properly validated
                        # This should fail fast for security
                        header_names = list(value.keys())
                        raise ValueError(
                            f"URL is required for header validation in pattern-based configuration. "
                            f"Found headers: {header_names}. "
                            f"Cannot validate headers without knowing the target URL."
                        )

                    for header_name in value.keys():
                        if is_sensitive_header(header_name, url_headers_config, element_url):
                            return True
                elif isinstance(value, (dict, list)):
                    if check_sensitivity(value, inherited_url):
                        return True
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    if check_sensitivity(item, inherited_url):
                        return True
        return False

    return check_sensitivity(data, url)


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
    data: dict,
    context_id: str,
    vault: Vault,
    key_prefix: Optional[str] = None,
    reference_prefix: str = "VAULT_HEADER",
    url_headers_config: Optional[UrlHeadersConfig] = None,
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
        url_headers_config: Optional URL headers configuration for sensitivity checks

    Returns:
        Modified data structure with sensitive headers encrypted

    Raises:
        ValueError: If headers are present but proper configuration or URL is not provided
    """
    # Validate headers before processing - this will fail fast if headers are found
    # but configuration or URLs are missing
    has_sensitive_headers(data, url_headers_config)

    # Make a deep copy to avoid modifying the original
    encrypted_data: dict[str, Any] = {}

    for key, value in data.items():
        if key == "headers" and isinstance(value, dict):
            # Look for a URL at the same level as the headers (e.g., in UrlDataElement)
            element_url = data.get("url") if "url" in data else None
            encrypted_data[key] = _encrypt_headers_dict(
                value, context_id, vault, key_prefix, reference_prefix, url_headers_config, element_url
            )
        elif isinstance(value, dict):
            encrypted_data[key] = encrypt_headers_in_data(
                value, context_id, vault, key_prefix, reference_prefix, url_headers_config
            )
        elif isinstance(value, list):
            encrypted_data[key] = [
                (
                    encrypt_headers_in_data(item, context_id, vault, key_prefix, reference_prefix, url_headers_config)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        else:
            encrypted_data[key] = value

    return encrypted_data


def decrypt_headers_in_data(
    data: dict,
    context_id: str,
    vault: Vault,
    key_prefix: Optional[str] = None,
    reference_prefix: str = "VAULT_HEADER",
    url_headers_config: Optional[UrlHeadersConfig] = None,
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
        url_headers_config: Optional URL headers configuration for sensitivity checks

    Returns:
        Modified data structure with actual header values restored
    """
    # Make a deep copy to avoid modifying the original
    decrypted_data: dict[str, Any] = {}

    for key, value in data.items():
        if key == "headers" and isinstance(value, dict):
            decrypted_data[key] = _decrypt_headers_dict(value, context_id, vault, key_prefix, reference_prefix)
        elif isinstance(value, dict):
            decrypted_data[key] = decrypt_headers_in_data(
                value, context_id, vault, key_prefix, reference_prefix, url_headers_config
            )
        elif isinstance(value, list):
            decrypted_data[key] = [
                (
                    decrypt_headers_in_data(item, context_id, vault, key_prefix, reference_prefix, url_headers_config)
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
    url_headers_config: Optional[UrlHeadersConfig] = None,
    url: Optional[str] = None,
) -> dict[str, str]:
    """
    Encrypt sensitive headers in a headers dictionary.

    Args:
        headers: Dictionary of header name -> header value
        context_id: Unique identifier for the context
        vault: Vault instance for encryption
        key_prefix: Optional custom prefix for vault keys
        reference_prefix: Prefix for vault references
        url_headers_config: Optional URL headers configuration for sensitivity checks
        url: Optional target URL for URL-specific header validation

    Returns:
        Dictionary with sensitive headers replaced by vault references
    """
    encrypted_headers = {}
    for header_name, header_value in headers.items():
        if is_sensitive_header(header_name, url_headers_config, url):
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
