"""Unit tests for JAICE environment key management."""

import os
import tempfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from galaxy.security.jaice.env_key import (
    DEFAULT_VAULT_KEY_PATH,
    EnvironmentKeyError,
    EnvironmentKeypair,
    generate_environment_keypair,
    load_esk_from_file,
    load_esk_from_vault,
    store_esk_to_vault,
)
from galaxy.security.jaice.jwt import verify_jwt
from galaxy.security.jaice.keys import from_jwk, generate_job_keypair


# ---------------------------------------------------------------------------
# generate_environment_keypair
# ---------------------------------------------------------------------------


def test_generate_produces_valid_keypair():
    env_kp, pem = generate_environment_keypair()
    assert isinstance(env_kp, EnvironmentKeypair)
    assert isinstance(env_kp.signing_key, Ed25519PrivateKey)
    assert isinstance(pem, bytes)
    assert pem.startswith(b"-----BEGIN PRIVATE KEY-----")


def test_generate_is_distinct():
    kp1, _ = generate_environment_keypair()
    kp2, _ = generate_environment_keypair()
    assert kp1.public_bytes != kp2.public_bytes


# ---------------------------------------------------------------------------
# EnvironmentKeypair properties
# ---------------------------------------------------------------------------


def test_epk_jwk_shape():
    env_kp, _ = generate_environment_keypair()
    jwk = env_kp.epk_jwk
    assert jwk["kty"] == "OKP"
    assert jwk["crv"] == "Ed25519"
    assert "x" in jwk


def test_epk_jwk_roundtrip():
    env_kp, _ = generate_environment_keypair()
    jwk = env_kp.epk_jwk
    assert from_jwk(jwk) == env_kp.public_bytes


def test_public_bytes_is_32():
    env_kp, _ = generate_environment_keypair()
    assert len(env_kp.public_bytes) == 32


def test_sign_jwt_roundtrip():
    env_kp, _ = generate_environment_keypair()
    job_kp = generate_job_keypair("job-1")
    token = env_kp.sign_jwt(job_kp)
    payload = verify_jwt(token, env_kp.public_key)
    assert payload["sub"] == "job-1"
    assert payload["jpk"]


def test_sign_jwt_can_omit_epk():
    env_kp, _ = generate_environment_keypair()
    job_kp = generate_job_keypair("job-1")
    token = env_kp.sign_jwt(job_kp, include_epk=False)
    from galaxy.security.jaice.jwt import header_jwk

    assert header_jwk(token) is None
    # Token still verifies.
    payload = verify_jwt(token, env_kp.public_key)
    assert payload["sub"] == "job-1"


def test_private_pem_roundtrip():
    env_kp, _ = generate_environment_keypair()
    pem = env_kp.private_pem()
    assert pem.startswith(b"-----BEGIN PRIVATE KEY-----")
    # Write to temp file and reload.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(pem)
        tmp = f.name
    try:
        reloaded = load_esk_from_file(tmp)
        assert reloaded.public_bytes == env_kp.public_bytes
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# load_esk_from_file
# ---------------------------------------------------------------------------


def test_load_esk_from_file():
    env_kp, pem = generate_environment_keypair()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(pem)
        tmp = f.name
    try:
        loaded = load_esk_from_file(tmp)
        assert loaded.public_bytes == env_kp.public_bytes
    finally:
        os.unlink(tmp)


def test_load_esk_from_file_missing():
    with pytest.raises(EnvironmentKeyError, match="Failed to load ESK"):
        load_esk_from_file("/nonexistent/jaice_esk.pem")


def test_load_esk_from_file_wrong_key_type():
    """If the file contains an RSA key, not Ed25519, raise EnvironmentKeyError."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(65537, 2048)
    rsa_pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(rsa_pem)
        tmp = f.name
    try:
        with pytest.raises(EnvironmentKeyError, match="expected Ed25519"):
            load_esk_from_file(tmp)
    finally:
        os.unlink(tmp)


def test_load_esk_from_file_garbage():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(b"not a key")
        tmp = f.name
    try:
        with pytest.raises(EnvironmentKeyError, match="Failed to load ESK"):
            load_esk_from_file(tmp)
    finally:
        os.unlink(tmp)


def test_load_esk_from_file_pathlib():
    import pathlib

    env_kp, pem = generate_environment_keypair()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(pem)
        tmp = f.name
    try:
        loaded = load_esk_from_file(pathlib.Path(tmp))
        assert loaded.public_bytes == env_kp.public_bytes
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# vault load/store
# ---------------------------------------------------------------------------


class _FakeVault:
    """Minimal in-memory vault for testing vault-based key operations."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def read_secret(self, key: str) -> str | None:
        return self._store.get(key)

    def write_secret(self, key: str, value: str) -> None:
        self._store[key] = value


def test_vault_store_and_load_roundtrip():
    vault = _FakeVault()
    env_kp, _ = generate_environment_keypair()
    store_esk_to_vault(vault, env_kp)
    loaded = load_esk_from_vault(vault)
    assert loaded.public_bytes == env_kp.public_bytes


def test_vault_load_uses_default_path():
    vault = _FakeVault()
    env_kp, _ = generate_environment_keypair()
    vault.write_secret(DEFAULT_VAULT_KEY_PATH, env_kp.private_pem().decode("ascii"))
    loaded = load_esk_from_vault(vault)
    assert loaded.public_bytes == env_kp.public_bytes


def test_vault_load_custom_path():
    vault = _FakeVault()
    env_kp, _ = generate_environment_keypair()
    store_esk_to_vault(vault, env_kp, key_path="custom/esk")
    loaded = load_esk_from_vault(vault, key_path="custom/esk")
    assert loaded.public_bytes == env_kp.public_bytes


def test_vault_load_missing_key():
    vault = _FakeVault()
    with pytest.raises(EnvironmentKeyError, match="No ESK found"):
        load_esk_from_vault(vault)


def test_vault_load_garbage():
    vault = _FakeVault()
    vault.write_secret(DEFAULT_VAULT_KEY_PATH, "not-a-valid-pem")
    with pytest.raises(EnvironmentKeyError, match="Failed to parse ESK"):
        load_esk_from_vault(vault)


# ---------------------------------------------------------------------------
# convenience: sign then verify with loaded key
# ---------------------------------------------------------------------------


def test_sign_with_loaded_key_verifies():
    """End-to-end: generate an env keypair, persist via PEM, reload, sign a
    job JWT, and verify."""
    env_kp, pem = generate_environment_keypair()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as f:
        f.write(pem)
        tmp = f.name
    try:
        reloaded = load_esk_from_file(tmp)
        job_kp = generate_job_keypair("e2e-job")
        token = reloaded.sign_jwt(job_kp)
        payload = verify_jwt(token, reloaded.public_key)
        assert payload["sub"] == "e2e-job"
    finally:
        os.unlink(tmp)
