from typing import Optional

from galaxy.managers.headers_encryption import (
    create_vault_key,
    create_vault_reference,
    decrypt_headers_in_data,
    encrypt_headers_in_data,
    has_sensitive_headers,
    is_sensitive_header,
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


class TestSensitiveHeaderDetection:
    """Test sensitive header pattern matching."""

    def test_sensitive_headers_detected(self):
        """Test that known sensitive headers are detected."""
        assert is_sensitive_header("Authorization")
        assert is_sensitive_header("authorization")
        assert is_sensitive_header("Proxy-Authorization")
        assert is_sensitive_header("Authentication")
        assert is_sensitive_header("WWW-Authenticate")
        assert is_sensitive_header("X-API-Key")
        assert is_sensitive_header("x-api-key")
        assert is_sensitive_header("API-Key")
        assert is_sensitive_header("Auth-Key")
        assert is_sensitive_header("Session-Key")
        assert is_sensitive_header("Bearer-Token")
        assert is_sensitive_header("API-Token")
        assert is_sensitive_header("X-TOKEN")
        assert is_sensitive_header("X-Auth-Token")
        assert is_sensitive_header("X-Access-Token")
        assert is_sensitive_header("My-Secret")
        assert is_sensitive_header("Client-Secret")
        assert is_sensitive_header("API-Secret")
        assert is_sensitive_header("Custom-Auth")
        assert is_sensitive_header("Basic-Auth")
        assert is_sensitive_header("X-Auth-Key")
        assert is_sensitive_header("OAuth")
        assert is_sensitive_header("Cookie")
        assert is_sensitive_header("cookie")
        assert is_sensitive_header("Set-Cookie")
        assert is_sensitive_header("Bearer")

    def test_non_sensitive_headers_not_detected(self):
        """Test that non-sensitive headers are not detected."""
        assert not is_sensitive_header("User-Agent")
        assert not is_sensitive_header("Content-Type")
        assert not is_sensitive_header("Accept")
        assert not is_sensitive_header("X-Custom-Header")
        assert not is_sensitive_header("Content-Length")
        assert not is_sensitive_header("Host")
        # Edge cases that contain keywords but aren't auth headers
        assert not is_sensitive_header("Token-Bucket")
        assert not is_sensitive_header("Key-Value")


class TestHasSensitiveHeaders:
    """Test has_sensitive_headers function that recursively checks for sensitive headers."""

    def test_detects_sensitive_headers(self):
        """Test detection of sensitive headers in various structures."""
        assert has_sensitive_headers({"headers": {"Authorization": "Bearer token"}})

        nested_data = {"request_json": {"targets": [{"elements": [{"headers": {"X-API-Key": "secret"}}]}]}}
        assert has_sensitive_headers(nested_data)

    def test_ignores_non_sensitive_headers(self):
        """Test that non-sensitive headers are ignored."""
        data = {"headers": {"Content-Type": "application/json"}}
        assert not has_sensitive_headers(data)

    def test_handles_missing_or_invalid_headers(self):
        """Test edge cases with missing or invalid headers."""
        assert not has_sensitive_headers({})  # Empty data
        assert not has_sensitive_headers({"no_headers": "value"})  # No headers key
        assert not has_sensitive_headers({"headers": {}})  # Empty headers
        assert not has_sensitive_headers({"headers": "not a dict"})  # Invalid headers type


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

        # Simple case with headers at top level
        data = {
            "headers": {
                "Authorization": "Bearer secret-token",
                "X-API-Key": "api-key-123",
                "User-Agent": "Galaxy/1.0",
            }
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault)

        # Check that sensitive values are replaced with vault references
        headers = encrypted["headers"]
        assert headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"
        assert headers["X-API-Key"] == "__VAULT_HEADER_X_API_KEY__"
        assert headers["User-Agent"] == "Galaxy/1.0"  # Non-sensitive unchanged

        # Check vault was written to with new default format
        assert len(vault.storage) == 2
        assert "headers/test-uuid/authorization" in vault.storage
        assert "headers/test-uuid/x_api_key" in vault.storage

        # Decrypt
        decrypted = decrypt_headers_in_data(encrypted, context_id, vault)

        # Check original values are restored
        decrypted_headers = decrypted["headers"]
        assert decrypted_headers["Authorization"] == "Bearer secret-token"
        assert decrypted_headers["X-API-Key"] == "api-key-123"
        assert decrypted_headers["User-Agent"] == "Galaxy/1.0"

    def test_encrypt_decrypt_nested_headers(self):
        """Test encrypting and decrypting headers in a complex nested structure."""
        vault = MockVault()
        context_id = "test-uuid"

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
                                "url": "base64://data",
                                "headers": {
                                    "Authorization": "Bearer secret-token",
                                    "X-API-Key": "api-key-123",
                                    "User-Agent": "Galaxy/1.0",
                                },
                            }
                        ],
                    }
                ]
            },
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault)

        # Check structure is preserved
        assert encrypted["request_version"] == "1"

        # Check headers are encrypted
        headers = encrypted["request_json"]["targets"][0]["elements"][0]["headers"]
        assert headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"
        assert headers["X-API-Key"] == "__VAULT_HEADER_X_API_KEY__"
        assert headers["User-Agent"] == "Galaxy/1.0"

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

        data = {
            "section1": {
                "headers": {
                    "Authorization": "Bearer token1",
                    "User-Agent": "Galaxy/1.0",
                }
            },
            "section2": {
                "data": {
                    "headers": {
                        "X-API-Key": "key123",
                        "Content-Type": "application/json",
                    }
                }
            },
        }

        # Encrypt
        encrypted = encrypt_headers_in_data(data, context_id, vault)

        # Check both sections are encrypted
        section1_headers = encrypted["section1"]["headers"]
        assert section1_headers["Authorization"] == "__VAULT_HEADER_AUTHORIZATION__"
        assert section1_headers["User-Agent"] == "Galaxy/1.0"

        section2_headers = encrypted["section2"]["data"]["headers"]
        assert section2_headers["X-API-Key"] == "__VAULT_HEADER_X_API_KEY__"
        assert section2_headers["Content-Type"] == "application/json"

        # Decrypt
        decrypted = decrypt_headers_in_data(encrypted, context_id, vault)

        # Check original values are restored
        assert decrypted["section1"]["headers"]["Authorization"] == "Bearer token1"
        assert decrypted["section2"]["data"]["headers"]["X-API-Key"] == "key123"
