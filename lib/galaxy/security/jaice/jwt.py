"""JAICE JWT token construction and verification.

Two token flavors, matching the protocol's two authentication options:

* **Option B (CE-signed)** - ``build_ce_jwt``. The Computing Environment signs
  the token with its ``ESK``. The header carries the ``EPK`` as a ``jwk`` so
  the Repository can identify the CE before verifying.
* **Option A (user-signed)** - ``build_user_jwt``. The user signs the *same*
  payload with their ``USK``; the header carries the ``UPK``. The CE forwards
  both tokens so the Repository can confirm a real user authorized the job.

Both use the standard ``EdDSA`` JWA algorithm (Ed25519). The protocol document
writes ``alg: "Ed25519"``; that is not a standard JWA identifier, so we emit
``EdDSA`` for interoperability with standard JWT libraries. ``Ed25519`` is
reflected in the JWK ``crv`` field, which is the correct place for it.

Signatures are produced with PyJWT's registered ``EdDSA`` algorithm, which
consumes ``cryptography`` OKP key objects.
"""

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def _as_public_key(public_key: Ed25519PublicKey | bytes) -> Ed25519PublicKey:
    """Coerce a public key into a ``cryptography`` key object.

    PyJWT's ``EdDSA`` verifier accepts ``cryptography`` key objects but not raw
    bytes (it attempts PEM decoding on bytes), so raw 32-byte keys must be
    wrapped first.
    """
    if isinstance(public_key, Ed25519PublicKey):
        return public_key
    if isinstance(public_key, bytes | bytearray):
        return Ed25519PublicKey.from_public_bytes(bytes(public_key))
    raise TypeError("public_key must be an Ed25519PublicKey or 32 raw bytes")


from galaxy.security.jaice.keys import (
    b64url_encode,
    JobKeypair,
    to_jwk,
)

# Standard JWA algorithm name for Ed25519 signatures (RFC 8037 / RFC 8705).
# The JAICE document uses the non-standard literal "Ed25519" here; the curve
# name belongs in the JWK `crv`, not the `alg`.
ALG = "EdDSA"


def _build_header(public_key: Ed25519PublicKey, include_jwk: bool) -> dict:
    header = {"typ": "JWT", "alg": ALG}
    if include_jwk:
        header["jwk"] = to_jwk(public_key)
    return header


def _build_payload(job_keypair: JobKeypair) -> dict:
    return {
        "sub": job_keypair.job_id,
        "jpk": b64url_encode(job_keypair.ed25519_public_bytes),
    }


def build_ce_jwt(
    job_keypair: JobKeypair,
    esk: Ed25519PrivateKey,
    *,
    include_epk: bool = True,
) -> str:
    """Option B: build a CE-signed JWT for a data request.

    ``esk`` is the Computing Environment's signing key. By default the EPK is
    embedded in the header ``jwk`` so the Repository can identify the CE
    without an out-of-band channel; set ``include_epk=False`` to omit it (the
    Repository then identifies the CE by other means, e.g. IP).
    """
    header = _build_header(esk.public_key(), include_epk)
    payload = _build_payload(job_keypair)
    return jwt.encode(payload, esk, algorithm=ALG, headers=header)


def build_user_jwt(
    job_keypair: JobKeypair,
    usk: Ed25519PrivateKey,
) -> str:
    """Option A: build a user-signed JWT authorizing a data request.

    ``usk`` is the user's signing key; the UPK is always embedded in the
    header ``jwk`` so the Repository can match it against its user registry.
    """
    header = _build_header(usk.public_key(), include_jwk=True)
    payload = _build_payload(job_keypair)
    return jwt.encode(payload, usk, algorithm=ALG, headers=header)


def verify_jwt(token: str, public_key: Ed25519PublicKey | bytes) -> dict:
    """Verify a JAICE JWT signature and return the decoded payload.

    ``public_key`` is the key the caller has resolved for this token: the CE's
    pre-registered ``EPK`` for an Option B token, or the user's ``UPK`` for an
    Option A token (looked up by matching the header ``jwk`` against a user
    registry). Accepts a ``cryptography`` public key or raw 32 bytes.
    """
    decoded = jwt.decode(token, _as_public_key(public_key), algorithms=[ALG])
    return decoded


def header_jwk(token: str) -> dict | None:
    """Return the ``jwk`` from a token's header, or ``None`` if absent.

    Useful for Option A verification: extract the UPK the user claimed, then
    match it against the user registry before verifying.
    """
    header = jwt.get_unverified_header(token)
    return header.get("jwk")
