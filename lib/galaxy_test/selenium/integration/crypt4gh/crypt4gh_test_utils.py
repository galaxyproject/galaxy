"""Utilities for Crypt4GH Selenium tests.

Provides key generation, file encryption/decryption, and header manipulation
helpers used by the mock recryptor server and the test framework.
"""

import base64
import io
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
)

import crypt4gh.header
import crypt4gh.lib

DEFAULT_KEYPAIR_ID = "test-compute-keypair-1"
DEFAULT_EXPIRATION_DAYS = 7


@dataclass(frozen=True)
class Crypt4ghTestKeys:
    """Keypairs and metadata for a complete crypt4gh test scenario."""

    # User keypair (encrypts/decrypts the original .c4gh files)
    user_private_key: bytes  # raw X25519 private key bytes
    user_public_key: bytes  # raw X25519 public key bytes

    # Compute keypair (held by the mock recryptor / Service B)
    compute_private_key: bytes
    compute_public_key: bytes
    compute_keypair_id: str
    compute_keypair_expiration_date: str  # ISO 8601


def _generate_x25519_keypair() -> tuple[bytes, bytes]:
    """Generate an X25519 keypair, returning (private_raw_bytes, public_raw_bytes)."""
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_bytes, public_bytes


def generate_test_keys(
    keypair_id: str = DEFAULT_KEYPAIR_ID,
    expiration_days: int = DEFAULT_EXPIRATION_DAYS,
) -> Crypt4ghTestKeys:
    """Generate all keypairs needed for a crypt4gh test scenario."""
    user_priv, user_pub = _generate_x25519_keypair()
    compute_priv, compute_pub = _generate_x25519_keypair()
    expiration = datetime.now(timezone.utc) + timedelta(days=expiration_days)
    return Crypt4ghTestKeys(
        user_private_key=user_priv,
        user_public_key=user_pub,
        compute_private_key=compute_priv,
        compute_public_key=compute_pub,
        compute_keypair_id=keypair_id,
        compute_keypair_expiration_date=expiration.isoformat(),
    )


def format_public_key_pem(public_key_bytes: bytes) -> str:
    """Format raw public key bytes as a PEM-like crypt4gh public key string.

    This matches the format used by Galaxy's ``_format_crypt4gh_public_key``.
    """
    encoded = base64.b64encode(public_key_bytes).decode("ascii")
    return "\n".join(
        [
            "-----BEGIN CRYPT4GH PUBLIC KEY-----",
            encoded,
            "-----END CRYPT4GH PUBLIC KEY-----",
        ]
    )


def parse_public_key_pem(pem_str: str) -> bytes:
    """Parse a PEM-like crypt4gh public key string back to raw bytes."""
    lines = pem_str.strip().splitlines()
    # Strip BEGIN/END markers, base64-decode the middle
    encoded = "".join(line.strip() for line in lines if not line.startswith("-----"))
    return base64.b64decode(encoded)


def encrypt_bytes(
    plaintext: bytes,
    recipient_public_keys: list[bytes],
) -> bytes:
    """Encrypt plaintext bytes and return the encrypted .c4gh bytes."""
    ephemeral_priv = X25519PrivateKey.generate()
    ephemeral_priv_bytes = ephemeral_priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    keys = [(0, ephemeral_priv_bytes, recipient_pub) for recipient_pub in recipient_public_keys]
    infile = io.BytesIO(plaintext)
    outfile = io.BytesIO()
    crypt4gh.lib.encrypt(keys, infile, outfile)
    return outfile.getvalue()


def extract_header_bytes(encrypted_bytes: bytes) -> bytes:
    """Read and return the crypt4gh header bytes from encrypted bytes."""
    stream = io.BytesIO(encrypted_bytes)
    list(crypt4gh.header.parse(stream))
    header_length = stream.tell()
    stream.seek(0)
    return stream.read(header_length)


def reencrypt_header(
    header_bytes: bytes,
    decryptor_private_key: bytes,
    recipient_public_keys: list[bytes],
) -> bytes:
    """Re-encrypt a crypt4gh header for new recipient public keys.

    Uses ``crypt4gh.header.reencrypt`` to decrypt with the holder's private key
    and re-encrypt for the new recipients.
    """
    stream = io.BytesIO(header_bytes)
    packets = list(crypt4gh.header.parse(stream))
    # Decryptor keys: (method, private_key, sender_pubkey)
    keys = [(0, decryptor_private_key, None)]
    # Recipient keys: (method, sender_private_key, recipient_public_key)
    # Generate an ephemeral sender key for each recipient
    recipient_keys = []
    for recipient_pub in recipient_public_keys:
        ephemeral_priv = X25519PrivateKey.generate()
        ephemeral_priv_bytes = ephemeral_priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        recipient_keys.append((0, ephemeral_priv_bytes, recipient_pub))
    new_packets = crypt4gh.header.reencrypt(packets, keys, recipient_keys)
    return crypt4gh.header.serialize(new_packets)


def decrypt_bytes(encrypted_bytes: bytes, private_key: bytes) -> bytes:
    """Decrypt encrypted bytes and return the plaintext."""
    keys = [(0, private_key, None)]
    infile = io.BytesIO(encrypted_bytes)
    outfile = io.BytesIO()
    crypt4gh.lib.decrypt(keys, infile, outfile)
    return outfile.getvalue()


def encode_header_b64(header_bytes: bytes) -> str:
    """Base64-encode header bytes for API payloads."""
    return base64.b64encode(header_bytes).decode("ascii")


def decode_header_b64(encoded: str) -> bytes:
    """Base64-decode a header string from API payloads."""
    return base64.b64decode(encoded)
