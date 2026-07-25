"""Unit tests for JAICE JWT token construction and verification."""

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from galaxy.security.jaice import (
    build_ce_jwt,
    build_user_jwt,
    from_jwk,
    generate_job_keypair,
    header_jwk,
    verify_jwt,
)
from galaxy.security.jaice.jwt import ALG

JOB_ID = "0123456789abcdef"


@pytest.fixture
def job_kp():
    return generate_job_keypair(JOB_ID)


@pytest.fixture
def esk():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def usk():
    return Ed25519PrivateKey.generate()


def test_ce_jwt_roundtrip(job_kp, esk):
    token = build_ce_jwt(job_kp, esk)
    payload = verify_jwt(token, esk.public_key())
    assert payload["sub"] == JOB_ID
    assert payload["jpk"]  # base64url of JPK


def test_ce_jwt_alg_is_eddsa(job_kp, esk):
    token = build_ce_jwt(job_kp, esk)
    assert jwt.get_unverified_header(token)["alg"] == ALG


def test_ce_jwt_header_carries_epk_by_default(job_kp, esk):
    token = build_ce_jwt(job_kp, esk)
    jwk = header_jwk(token)
    assert jwk is not None
    epk_raw = esk.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    assert from_jwk(jwk) == epk_raw


def test_ce_jwt_epk_can_be_omitted(job_kp, esk):
    token = build_ce_jwt(job_kp, esk, include_epk=False)
    assert header_jwk(token) is None


def test_user_jwt_carries_upk(job_kp, usk):
    token = build_user_jwt(job_kp, usk)
    jwk = header_jwk(token)
    assert jwk is not None
    assert from_jwk(jwk) == usk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    payload = verify_jwt(token, usk.public_key())
    assert payload["sub"] == JOB_ID


def test_user_jwt_verifies_under_user_key_not_ce_key(job_kp, esk, usk):
    """Option A: the user token is signed by USK, not the CE's ESK."""
    user_token = build_user_jwt(job_kp, usk)
    with pytest.raises(jwt.InvalidSignatureError):
        verify_jwt(user_token, esk.public_key())


def test_ce_jwt_verifies_under_ce_key_not_user_key(job_kp, esk, usk):
    ce_token = build_ce_jwt(job_kp, esk)
    with pytest.raises(jwt.InvalidSignatureError):
        verify_jwt(ce_token, usk.public_key())


def test_tampered_payload_rejected(job_kp, esk):
    token = build_ce_jwt(job_kp, esk)
    header, payload_b64, sig = token.split(".")
    # Flip a character in the payload segment.
    tampered_payload = payload_b64[:-1] + ("A" if payload_b64[-1] != "A" else "B")
    tampered = f"{header}.{tampered_payload}.{sig}"
    with pytest.raises(jwt.InvalidSignatureError):
        verify_jwt(tampered, esk.public_key())


def test_wrong_public_key_rejected(job_kp, esk):
    token = build_ce_jwt(job_kp, esk)
    other = Ed25519PrivateKey.generate().public_key()
    with pytest.raises(jwt.InvalidSignatureError):
        verify_jwt(token, other)


def test_verify_jwt_accepts_raw_bytes(job_kp, esk):
    from cryptography.hazmat.primitives import serialization

    token = build_ce_jwt(job_kp, esk)
    raw = esk.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    payload = verify_jwt(token, raw)
    assert payload["sub"] == JOB_ID


def test_token_is_deterministic_across_calls(job_kp, esk):
    """EdDSA signatures are deterministic, so identical inputs yield identical tokens."""
    t1 = build_ce_jwt(job_kp, esk)
    t2 = build_ce_jwt(job_kp, esk)
    assert t1 == t2


def test_jpk_in_payload_matches_job_public_key(job_kp, esk):
    from galaxy.security.jaice.keys import b64url_encode

    token = build_ce_jwt(job_kp, esk)
    payload = verify_jwt(token, esk.public_key())
    assert payload["jpk"] == b64url_encode(job_kp.ed25519_public_bytes)
