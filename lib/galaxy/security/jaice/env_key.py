"""JAICE environment key (ESK/EPK) management.

The Computing Environment (CE) holds an Ed25519 keypair whose public half (EPK)
is pre-registered at the Repository. The private half (ESK) signs every Option B
(CE-signed) request JWT and MUST be protected: ESK compromise = full CE
impersonation.

This module handles:

* Generating a fresh environment keypair (for initial setup by an admin).
* Loading ESK from a PEM file on disk (``load_esk_from_file``).
* Loading/storing ESK via Galaxy's vault abstraction
  (``load_esk_from_vault`` / ``store_esk_to_vault``).
* Exposing EPK as a JWK for embedding in JWT headers.

The recommended production pattern is:

1. Generate the keypair with ``generate_environment_keypair``.
2. Store the PEM in the configured vault under a well-known path
   (default: ``jaice/environment_key``).
3. Set ``jaice_environment_key_vault_path`` in ``galaxy.yml`` to that path.
4. The EPK JWK is exposed at ``/api/jaice/epk`` so operators can register it
   at the Repository out-of-band.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from galaxy.security.jaice.keys import ED25519_CRV, to_jwk
from galaxy.security.jaice.jwt import build_ce_jwt

if TYPE_CHECKING:
    from galaxy.security.jaice.keys import JobKeypair
    from galaxy.security.vault import Vault

# Default vault path where the ESK PEM is stored when using the vault backend.
DEFAULT_VAULT_KEY_PATH = "jaice/environment_key"


class EnvironmentKeyError(Exception):
    """Raised when the environment key cannot be loaded."""


@dataclass(frozen=True)
class EnvironmentKeypair:
    """CE environment keypair.

    ``signing_key`` is the Ed25519 private key (ESK). The public half (EPK) is
    derived from it and exposed as a JWK for embedding in JWT headers.
    """

    signing_key: Ed25519PrivateKey

    @property
    def public_key(self) -> Ed25519PublicKey:
        """The EPK as a ``cryptography`` public key object."""
        return self.signing_key.public_key()

    @property
    def public_bytes(self) -> bytes:
        """Raw 32-byte EPK."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def epk_jwk(self) -> dict:
        """EPK serialized as a JWK (``kty:OKP, crv:Ed25519``)."""
        return to_jwk(self.public_key)

    def sign_jwt(
        self,
        job_keypair: JobKeypair,
        *,
        include_epk: bool = True,
    ) -> str:
        """Sign an Option B (CE-signed) JWT for *job_keypair*.

        This is a convenience wrapper around :func:`~.jwt.build_ce_jwt`.
        """
        return build_ce_jwt(job_keypair, self.signing_key, include_epk=include_epk)

    def private_pem(self) -> bytes:
        """Export ESK as unencrypted PKCS#8 PEM bytes.

        **Handle with care** — this is the ESK in the clear.
        """
        return self.signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )


def generate_environment_keypair() -> tuple[EnvironmentKeypair, bytes]:
    """Generate a fresh ESK/EPK and return the keypair and its PEM encoding.

    Returns a ``(EnvironmentKeypair, pem_bytes)`` tuple. The caller is
    responsible for storing the PEM securely (vault or file).
    """
    esk = Ed25519PrivateKey.generate()
    keypair = EnvironmentKeypair(signing_key=esk)
    return keypair, keypair.private_pem()


def load_esk_from_file(path: str | os.PathLike) -> EnvironmentKeypair:
    """Load ESK from a PEM-encoded PKCS#8 Ed25519 private-key file.

    Parameters
    ----------
    path:
        Filesystem path to the PEM file.

    Returns
    -------
    EnvironmentKeypair
        The loaded environment keypair.

    Raises
    ------
    EnvironmentKeyError
        If the file cannot be read or does not contain a valid Ed25519 key.
    """
    path = os.fspath(path)
    try:
        with open(path, "rb") as fh:
            key = serialization.load_pem_private_key(fh.read(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise EnvironmentKeyError(
            f"Failed to load ESK from {path!r}: {exc}"
        ) from exc

    if not isinstance(key, Ed25519PrivateKey):
        raise EnvironmentKeyError(
            f"Key in {path!r} is {type(key).__name__}, expected Ed25519PrivateKey"
        )
    return EnvironmentKeypair(signing_key=key)


def load_esk_from_vault(
    vault: Vault,
    key_path: str = DEFAULT_VAULT_KEY_PATH,
) -> EnvironmentKeypair:
    """Load ESK from the Galaxy vault.

    Parameters
    ----------
    vault:
        The Galaxy vault instance (``app.vault``).
    key_path:
        Vault key where the PEM-encoded ESK is stored.

    Returns
    -------
    EnvironmentKeypair
        The loaded environment keypair.

    Raises
    ------
    EnvironmentKeyError
        If no key is found at *key_path* or the stored data is not a valid
        Ed25519 private key.
    """
    pem_data = vault.read_secret(key_path)
    if not pem_data:
        raise EnvironmentKeyError(
            f"No ESK found in vault at {key_path!r}"
        )
    try:
        key = serialization.load_pem_private_key(
            pem_data.encode("utf-8"), password=None
        )
    except (ValueError, TypeError) as exc:
        raise EnvironmentKeyError(
            f"Failed to parse ESK from vault key {key_path!r}: {exc}"
        ) from exc

    if not isinstance(key, Ed25519PrivateKey):
        raise EnvironmentKeyError(
            f"Vault key {key_path!r} does not contain an Ed25519 key"
        )
    return EnvironmentKeypair(signing_key=key)


def store_esk_to_vault(
    vault: Vault,
    keypair: EnvironmentKeypair,
    key_path: str = DEFAULT_VAULT_KEY_PATH,
) -> None:
    """Store ESK PEM in the Galaxy vault.

    Parameters
    ----------
    vault:
        The Galaxy vault instance.
    keypair:
        The environment keypair to store.
    key_path:
        Vault key path to write to.
    """
    vault.write_secret(key_path, keypair.private_pem().decode("ascii"))
