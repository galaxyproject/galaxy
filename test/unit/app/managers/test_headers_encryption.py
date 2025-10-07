from typing import Optional

import pytest

from galaxy.config.url_headers import (
    HeaderConfig,
    UrlHeadersConfig,
    UrlPatternConfig,
)
from galaxy.managers.headers_encryption import (
    create_vault_key,
    create_vault_reference,
    decrypt_headers_in_data,
    encrypt_headers_in_data,
    has_sensitive_headers,
)
from galaxy.security.vault import Vault


class MockVault(Vault):
    """Mock vault for testing encryption/decryption."""

    def __init__(self):
        self.storage = {}

    def write_secret(self, key: str, value: str) -> None:
        self.storage[key] = value

    def read_secret(self, key: str) -> Optional[str]:
        return self.storage.get(key)

    def list_secrets(self, key: str) -> list[str]:
        """Mock implementation - not used in header tests."""
        return []


def create_test_url_headers_config():
    config = UrlHeadersConfig()

    # GitHub API pattern - allows auth headers
    github_pattern = UrlPatternConfig(
        url_pattern=r"^https://api\.github\.com/.*",
        headers=[
            HeaderConfig(name="Authorization", sensitive=True),
            HeaderConfig(name="Accept", sensitive=False),
            HeaderConfig(name="Accept-Encoding", sensitive=False),
        ],
    )

    # Generic HTTPS pattern - only basic headers
    https_pattern = UrlPatternConfig(
        url_pattern=r"^https://.*",
        headers=[
            HeaderConfig(name="Accept", sensitive=False),
            HeaderConfig(name="Accept-Language", sensitive=False),
            HeaderConfig(name="Content-Type", sensitive=False),
        ],
    )

    # Test API pattern - for testing sensitive headers
    test_api_pattern = UrlPatternConfig(
        url_pattern=r"^https://api\.example\.com/.*",
        headers=[
            HeaderConfig(name="Authorization", sensitive=True),
            HeaderConfig(name="X-API-Key", sensitive=True),
            HeaderConfig(name="Content-Type", sensitive=False),
            HeaderConfig(name="Accept", sensitive=False),
        ],
    )

    # Set up the patterns in the config
    config._patterns = [github_pattern, test_api_pattern, https_pattern]

    # Set up compiled patterns
    import re

    config._compiled_patterns = [
        (re.compile(github_pattern.url_pattern), github_pattern),
        (re.compile(test_api_pattern.url_pattern), test_api_pattern),
        (re.compile(https_pattern.url_pattern), https_pattern),
    ]

    return config


class TestSensitiveHeaderDetection:
    """Test sensitive header pattern matching using real URL headers configuration."""

    def test_sensitive_headers_detected(self):
        """Test that configured sensitive headers are detected for matching URLs."""
        config = create_test_url_headers_config()

        # Test GitHub API URL - Authorization should be sensitive
        assert config.is_header_sensitive_for_url("Authorization", "https://api.github.com/repos")
        assert not config.is_header_sensitive_for_url("Accept", "https://api.github.com/repos")
        assert not config.is_header_sensitive_for_url("Accept-Encoding", "https://api.github.com/repos")

        # Test API example URL - Authorization and X-API-Key should be sensitive
        assert config.is_header_sensitive_for_url("Authorization", "https://api.example.com/data")
        assert config.is_header_sensitive_for_url("X-API-Key", "https://api.example.com/data")
        assert not config.is_header_sensitive_for_url("Content-Type", "https://api.example.com/data")

    def test_non_sensitive_headers_not_detected(self):
        """Test that non-sensitive headers are not detected."""
        config = create_test_url_headers_config()

        # Test generic HTTPS URL - no sensitive headers configured
        assert not config.is_header_sensitive_for_url("Accept", "https://example.com/data")
        assert not config.is_header_sensitive_for_url("Accept-Language", "https://example.com/data")
        assert not config.is_header_sensitive_for_url("Content-Type", "https://example.com/data")

    def test_headers_not_allowed_for_url(self):
        """Test that headers not in patterns are not considered sensitive."""
        config = create_test_url_headers_config()

        # Header not in any pattern should not be sensitive
        assert not config.is_header_sensitive_for_url("X-Custom-Header", "https://api.github.com/repos")
        assert not config.is_header_sensitive_for_url("X-Custom-Header", "https://example.com/data")


class TestHasSensitiveHeaders:
    """Test has_sensitive_headers function that recursively checks for sensitive headers."""

    def test_detects_sensitive_headers(self):
        """Test detection of sensitive headers in various structures."""
        config = create_test_url_headers_config()

        # Test with config and URL - should work normally
        data_with_url = {"url": "https://api.github.com/repos", "headers": {"Authorization": "Bearer token"}}
        assert has_sensitive_headers(data_with_url, url_headers_config=config)

        # Test nested structure with URL
        nested_data = {
            "request_json": {
                "targets": [{"elements": [{"url": "https://api.example.com/data", "headers": {"X-API-Key": "secret"}}]}]
            }
        }
        assert has_sensitive_headers(nested_data, url_headers_config=config)

    def test_ignores_non_sensitive_headers(self):
        """Test that non-sensitive headers are ignored when URL is provided."""
        config = create_test_url_headers_config()
        # When URL is provided, pattern-based checking is used
        data = {"url": "https://example.com/api", "headers": {"Content-Type": "application/json"}}
        assert not has_sensitive_headers(data, url_headers_config=config)

    def test_handles_missing_or_invalid_headers(self):
        """Test edge cases with missing or invalid headers."""
        config = create_test_url_headers_config()
        assert not has_sensitive_headers({}, url_headers_config=config)  # Empty data
        assert not has_sensitive_headers({"no_headers": "value"}, url_headers_config=config)  # No headers key
        assert not has_sensitive_headers({"headers": {}}, url_headers_config=config)  # Empty headers (ignored)
        assert not has_sensitive_headers({"headers": "not a dict"}, url_headers_config=config)  # Invalid headers type

    def test_headers_without_url_fail_fast(self):
        """Test that headers without URL fail fast in pattern-based system."""
        config = create_test_url_headers_config()
        # Without URL, headers should fail fast since we can't validate them
        data = {"headers": {"Content-Type": "application/json"}}
        with pytest.raises(ValueError, match="URL is required for header validation"):
            has_sensitive_headers(data, url_headers_config=config)

    def test_fails_without_config(self):
        """Test that function fails fast when no configuration is provided."""

        # Should raise ValueError when headers exist but no config
        with pytest.raises(ValueError, match="Headers are not allowed without proper URL headers configuration"):
            has_sensitive_headers({"headers": {"Authorization": "Bearer token"}})

        # Should raise ValueError for nested headers too
        nested_data = {"request_json": {"targets": [{"elements": [{"headers": {"X-API-Key": "secret"}}]}]}}
        with pytest.raises(ValueError, match="Headers are not allowed without proper URL headers configuration"):
            has_sensitive_headers(nested_data)

        # Should NOT raise error when no headers present
        assert not has_sensitive_headers({})  # Empty data
        assert not has_sensitive_headers({"no_headers": "value"})  # No headers key


class TestVaultKeyAndReference:
    """Test vault key and reference creation."""

    def test_create_vault_key_default_prefix(self):
        """Test vault key creation with default prefix."""
        key = create_vault_key("uuid-123", "Authorization")
        assert key == "headers/uuid-123/authorization"

        key = create_vault_key("uuid-456", "X-API-Key")
        assert key == "headers/uuid-456/x_api_key"

    def test_create_vault_key_custom_prefix(self):
        """Test vault key creation with custom prefix."""
        key = create_vault_key("uuid-123", "Authorization", "custom_prefix")
        assert key == "custom_prefix/uuid-123/authorization"

        key = create_vault_key("uuid-456", "X-API-Key", "landing_request/headers")
        assert key == "landing_request/headers/uuid-456/x_api_key"

    def test_create_vault_reference_default(self):
        """Test vault reference creation with default prefix."""
        ref = create_vault_reference("Authorization")
        assert ref == "__VAULT_HEADER_AUTHORIZATION__"

        ref = create_vault_reference("X-API-Key")
        assert ref == "__VAULT_HEADER_X_API_KEY__"

    def test_create_vault_reference_custom_prefix(self):
        """Test vault reference creation with custom prefix."""
        ref = create_vault_reference("Authorization", "CUSTOM_REF")
        assert ref == "__CUSTOM_REF_AUTHORIZATION__"

        ref = create_vault_reference("X-API-Key", "SESSION_HEADER")
        assert ref == "__SESSION_HEADER_X_API_KEY__"


class TestHeaderEncryptionDecryption:
    """Test end-to-end header encryption and decryption."""

    def test_encrypt_decrypt_simple_headers(self):
        """Test encrypting and decrypting a simple headers structure."""
        vault = MockVault()
        context_id = "test-uuid"
        config = create_test_url_headers_config()

        # Simple case with headers at top level and URL for validation
        data = {
            "url": "https://api.example.com/data",
            "headers": {
                "Authorization": "Bearer secret-token",
                "X-API-Key": "api-key-123",
                "Accept": "application/json",
            },
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault, url_headers_config=config)

        # Check that sensitive headers are encrypted
        headers = encrypted["headers"]
        assert headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"  # Encrypted (sensitive)
        assert headers["X-API-Key"] == "__VAULT_HEADER_X_API_KEY__"  # Encrypted (sensitive)
        assert headers["Accept"] == "application/json"  # Not encrypted (not sensitive)

        # Check vault has the encrypted headers
        assert len(vault.storage) == 2
        assert "headers/test-uuid/authorization" in vault.storage
        assert "headers/test-uuid/x_api_key" in vault.storage

        # Decrypt
        decrypted = decrypt_headers_in_data(encrypted, context_id, vault)

        # Check original values are restored
        decrypted_headers = decrypted["headers"]
        assert decrypted_headers["Authorization"] == "Bearer secret-token"
        assert decrypted_headers["X-API-Key"] == "api-key-123"
        assert decrypted_headers["Accept"] == "application/json"

    def test_encrypt_decrypt_nested_headers(self):
        """Test encrypting and decrypting headers in a complex nested structure."""
        vault = MockVault()
        context_id = "test-uuid"
        config = create_test_url_headers_config()

        # Complex nested structure like in the actual data landing request
        data: dict = {
            "request_version": "1",
            "request_json": {
                "targets": [
                    {
                        "destination": {"type": "hdas"},
                        "elements": [
                            {
                                "src": "url",
                                "url": "https://api.github.com/repos/test/repo",
                                "headers": {
                                    "Authorization": "Bearer secret-token",
                                    "Accept": "application/vnd.github.v3+json",
                                    "Accept-Encoding": "gzip, deflate",
                                },
                            }
                        ],
                    }
                ]
            },
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault, url_headers_config=config)

        # Check structure is preserved
        assert encrypted["request_version"] == "1"

        # Check headers are encrypted based on GitHub API pattern
        headers = encrypted["request_json"]["targets"][0]["elements"][0]["headers"]
        assert headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"  # Sensitive for GitHub API
        assert headers["Accept"] == "application/vnd.github.v3+json"  # Not sensitive
        assert headers["Accept-Encoding"] == "gzip, deflate"  # Not sensitive

        # Decrypt
        decrypted = decrypt_headers_in_data(encrypted, context_id, vault)

        # Check original structure and values are restored
        original_headers = data["request_json"]["targets"][0]["elements"][0]["headers"]
        decrypted_headers = decrypted["request_json"]["targets"][0]["elements"][0]["headers"]

        assert decrypted_headers == original_headers

    def test_multiple_headers_sections(self):
        """Test handling multiple headers sections in different parts of the structure."""
        vault = MockVault()
        context_id = "test-uuid"
        config = create_test_url_headers_config()

        # Multiple sections with different URLs
        data = {
            "section1": {
                "url": "https://api.github.com/repos",
                "headers": {
                    "Authorization": "Bearer token1",
                    "Accept": "application/vnd.github.v3+json",
                },
            },
            "section2": {
                "data": {
                    "url": "https://example.com/data",
                    "headers": {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                }
            },
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault, url_headers_config=config)

        # Check section1 (GitHub API pattern - Authorization is sensitive)
        section1_headers = encrypted["section1"]["headers"]
        assert section1_headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"  # Encrypted
        assert section1_headers["Accept"] == "application/vnd.github.v3+json"  # Not encrypted

        # Check section2 (generic HTTPS pattern - no sensitive headers)
        section2_headers = encrypted["section2"]["data"]["headers"]
        assert section2_headers["Accept"] == "application/json"  # Not encrypted
        assert section2_headers["Content-Type"] == "application/json"  # Not encrypted

        # Decrypt
        decrypted = decrypt_headers_in_data(encrypted, context_id, vault)

        # Check original values are preserved
        assert decrypted["section1"]["headers"]["Authorization"] == "Bearer token1"
        assert decrypted["section1"]["headers"]["Accept"] == "application/vnd.github.v3+json"
        assert decrypted["section2"]["data"]["headers"]["Accept"] == "application/json"
        assert decrypted["section2"]["data"]["headers"]["Content-Type"] == "application/json"

    def test_encrypt_fails_without_config(self):
        """Test that encryption fails fast when no configuration is provided."""

        vault = MockVault()
        context_id = "test-uuid"

        data = {
            "headers": {
                "Authorization": "Bearer secret-token",
                "X-API-Key": "api-key-123",
            }
        }

        # Should raise ValueError when trying to encrypt without config
        with pytest.raises(ValueError, match="Headers are not allowed without proper URL headers configuration"):
            encrypt_headers_in_data(data, context_id, vault)

    def test_encrypt_headers_with_url_pattern_checking(self):
        """Test encryption with URL-based pattern checking."""
        vault = MockVault()
        context_id = "test-uuid"
        config = create_test_url_headers_config()

        # Test: Headers WITHOUT URL should fail fast
        data_no_url = {
            "headers": {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        }

        with pytest.raises(ValueError, match="URL is required for header validation"):
            encrypt_headers_in_data(data_no_url, context_id, vault, url_headers_config=config)

        # Test: Headers WITH URL - pattern-based checking works
        vault2 = MockVault()  # Fresh vault for second test
        data_with_url = {
            "url": "https://api.example.com/data",
            "headers": {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        encrypted_with_url = encrypt_headers_in_data(data_with_url, context_id, vault2, url_headers_config=config)
        headers_with_url = encrypted_with_url["headers"]

        # Only sensitive headers encrypted (URL-based pattern matching)
        assert headers_with_url["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"  # Sensitive for api.example.com
        assert headers_with_url["Content-Type"] == "application/json"  # Not sensitive
        assert headers_with_url["Accept-Language"] == "en-US,en;q=0.9"  # Not sensitive

        # Verify vault has the encrypted header
        assert len(vault2.storage) == 1
        assert "headers/test-uuid/authorization" in vault2.storage
