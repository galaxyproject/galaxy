"""JAICE key management: Ed25519 job/CE/user keypairs and the RFC 7748 curve
mapping to X25519 for Crypt4GH.

Key types used by the protocol:

* ``ESK``/``EPK`` - Computing Environment signing keypair (Ed25519). Signs
  request JWTs. The EPK is pre-registered at the Repository.
* ``JSK``/``JPK`` - per-job keypair. ``JSK`` signs job data/requests; ``JPK``
  (after curve mapping) is the X25519 recipient key for Crypt4GH containers.
* ``USK``/``UPK`` - user signing keypair (Ed25519). Used only in Option A.

The curve mapping (RFC 7748 section 1) lets the *same* Ed25519 private key
serve as an X25519 private key: hash the 32-byte Ed25519 seed with SHA-512,
clamp it, and take the first 32 bytes. The resulting X25519 public key is what
Crypt4GH encrypts to.

This module uses ``cryptography`` OKP keys (the same objects PyJWT's EdDSA
algorithm consumes) for signing, and ``nacl.bindings`` for the X25519 scalar
multiplication used to derive the Crypt4GH recipient public key.
"""

import hashlib
from dataclasses import dataclass

import nacl.bindings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# JWK curve identifier for Ed25519 keys (RFC 8037).
ED25519_CRV = "Ed25519"
# JWK curve identifier for X25519 keys (RFC 8037).
X25519_CRV = "X25519"


def b64url_encode(data: bytes) -> str:
    """Base64URL-encode without padding (the JWT/JWK convention)."""
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    """Base64URL-decode, tolerating missing padding."""
    import base64

    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def ed25519_seed_to_x25519_private(ed25519_seed: bytes) -> bytes:
    """Map an Ed25519 private seed to an X25519 private key (RFC 7748 sec 1).

    The Ed25519 private key is a 32-byte seed. Hashing it with SHA-512 and
    clamping the first 32 bytes yields a valid X25519 private scalar, so a
    single keypair can be used for both signing (Ed25519) and Crypt4GH
    decryption (X25519).
    """
    if len(ed25519_seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    digest = hashlib.sha512(ed25519_seed).digest()
    scalar = bytearray(digest[:32])
    scalar[0] &= 248
    scalar[31] &= 127
    scalar[31] |= 64
    return bytes(scalar)


def to_jwk(public_key: Ed25519PublicKey | bytes, *, crv: str = ED25519_CRV) -> dict:
    """Serialize an Ed25519/X25519 public key as a JWK ``dict``.

    Accepts either a ``cryptography`` public key object or raw public bytes
    (32 bytes for both Ed25519 and X25519).
    """
    if isinstance(public_key, Ed25519PublicKey):
        if crv != ED25519_CRV:
            raise ValueError(f"Ed25519PublicKey can only be serialized as {ED25519_CRV}")
        raw = public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    else:
        raw = bytes(public_key)
    if len(raw) != 32:
        raise ValueError("public key must be 32 raw bytes")
    return {"kty": "OKP", "crv": crv, "x": b64url_encode(raw)}


def from_jwk(jwk: dict) -> bytes:
    """Return the raw 32-byte public key from an OKP Ed25519/X25519 JWK."""
    if jwk.get("kty") != "OKP":
        raise ValueError("JWK kty must be OKP")
    if jwk.get("crv") not in (ED25519_CRV, X25519_CRV):
        raise ValueError(f"JWK crv must be {ED25519_CRV} or {X25519_CRV}")
    return b64url_decode(jwk["x"])


@dataclass(frozen=True)
class JobKeypair:
    """A per-job JAICE keypair.

    ``signing_key`` is the Ed25519 key used for JWT signing (the ``JSK``).
    The X25519 halves are derived lazily from the same seed and are what
    Crypt4GH encrypts to / the job decrypts with.
    """

    job_id: str
    signing_key: Ed25519PrivateKey

    @property
    def ed25519_seed(self) -> bytes:
        return self.signing_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @property
    def ed25519_public_bytes(self) -> bytes:
        """The Ed25519 public key (``JPK`` for signing)."""
        return self.signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

    @property
    def ed25519_public_key(self) -> Ed25519PublicKey:
        return self.signing_key.public_key()

    @property
    def x25519_private_bytes(self) -> bytes:
        """The X25519 private key for Crypt4GH decryption (RFC 7748 map)."""
        return ed25519_seed_to_x25519_private(self.ed25519_seed)

    @property
    def x25519_public_bytes(self) -> bytes:
        """The X25519 public key Crypt4GH containers are encrypted to."""
        return nacl.bindings.crypto_scalarmult_base(self.x25519_private_bytes)

    @property
    def x25519_public_jwk(self) -> dict:
        return to_jwk(self.x25519_public_bytes, crv=X25519_CRV)


def generate_job_keypair(job_id: str) -> JobKeypair:
    """Generate a fresh Ed25519 keypair for a job.

    ``job_id`` becomes the ``sub`` claim of every JWT issued for this job.
    """
    if not job_id:
        raise ValueError("job_id must be non-empty")
    return JobKeypair(job_id=job_id, signing_key=Ed25519PrivateKey.generate())
