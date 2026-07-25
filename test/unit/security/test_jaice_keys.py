"""Unit tests for JAICE key generation and the RFC 7748 curve mapping."""

import nacl.bindings
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from galaxy.security.jaice.keys import (
    b64url_decode,
    b64url_encode,
    ED25519_CRV,
    ed25519_seed_to_x25519_private,
    from_jwk,
    generate_job_keypair,
    to_jwk,
    X25519_CRV,
)


def test_b64url_roundtrip():
    raw = bytes(range(256))
    assert b64url_decode(b64url_encode(raw)) == raw


def test_b64url_decode_tolerates_missing_padding():
    assert b64url_decode("AA") == b"\x00"


def test_generate_job_keypair_distinct():
    kp1 = generate_job_keypair("job-1")
    kp2 = generate_job_keypair("job-1")
    assert kp1.ed25519_public_bytes != kp2.ed25519_public_bytes


def test_generate_job_keypair_requires_id():
    with pytest.raises(ValueError):
        generate_job_keypair("")


def test_jwk_roundtrip():
    kp = generate_job_keypair("job-1")
    jwk = to_jwk(kp.ed25519_public_key)
    assert jwk["kty"] == "OKP"
    assert jwk["crv"] == ED25519_CRV
    assert from_jwk(jwk) == kp.ed25519_public_bytes


def test_jwk_accepts_raw_bytes():
    raw = bytes(range(32))
    jwk = to_jwk(raw)
    assert from_jwk(jwk) == raw


def test_jwk_wrong_crv_for_key_type():
    kp = generate_job_keypair("job-1")
    with pytest.raises(ValueError):
        to_jwk(kp.ed25519_public_key, crv=X25519_CRV)


def test_curve_mapping_yields_valid_x25519_keypair():
    """The RFC 7748 map must produce a scalar whose X25519 public key matches."""
    kp = generate_job_keypair("job-1")
    x_sk = kp.x25519_private_bytes
    x_pk = nacl.bindings.crypto_scalarmult_base(x_sk)
    assert x_pk == kp.x25519_public_bytes


def test_curve_mapping_is_deterministic():
    kp = generate_job_keypair("job-1")
    seed = kp.ed25519_seed
    assert ed25519_seed_to_x25519_private(seed) == kp.x25519_private_bytes


def test_curve_mapping_rejects_bad_seed_length():
    with pytest.raises(ValueError):
        ed25519_seed_to_x25519_private(b"short")


def test_x25519_public_jwk_has_correct_crv():
    kp = generate_job_keypair("job-1")
    jwk = kp.x25519_public_jwk
    assert jwk["crv"] == X25519_CRV
    assert from_jwk(jwk) == kp.x25519_public_bytes


def test_ed25519_public_key_object_matches_bytes():
    kp = generate_job_keypair("job-1")
    pub = kp.ed25519_public_key
    assert isinstance(pub, Ed25519PublicKey)
    raw = pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    assert raw == kp.ed25519_public_bytes
