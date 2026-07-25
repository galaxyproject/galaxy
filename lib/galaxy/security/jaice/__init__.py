"""JAICE - Job Authentication in Computation Environment.

Implementation of the cryptographic primitives and JWT token format defined
by the JAICE protocol (see ``doc/source/dev/jaice_design.md`` for the design
and the ``jaice.pdf`` reference document for the full specification).

This module implements the lowest-risk slice: key generation, the RFC 7748
curve mapping that lets a single Ed25519 keypair double as the X25519 key used
for Crypt4GH, JWK (de)serialization, and the compact-JWT tokens for both
authentication options (CE-signed "Option B" and user-co-signed "Option A").

Design notes:

* The protocol document specifies ``alg: "Ed25519"``. That is not a standard
  JWA identifier; the standard algorithm name for Ed25519 signatures in JWTs
  is ``EdDSA`` (RFC 8037 / RFC 8705). We emit ``EdDSA`` for interoperability
  with standard JWT libraries and note the divergence here.
* The protocol reuses one keypair for both Ed25519 signing and X25519
  Crypt4GH decryption via the RFC 7748 Montgomery <-> Twisted-Edwards mapping.
  This module implements that mapping and exposes both key halves. See the
  design doc for the key-separation trade-off discussion.
"""

from galaxy.security.jaice.env_key import (
    EnvironmentKeyError,
    EnvironmentKeypair,
    generate_environment_keypair,
    load_esk_from_file,
    load_esk_from_vault,
    store_esk_to_vault,
)
from galaxy.security.jaice.jwt import (
    build_ce_jwt,
    build_user_jwt,
    header_jwk,
    verify_jwt,
)
from galaxy.security.jaice.keys import (
    ed25519_seed_to_x25519_private,
    from_jwk,
    generate_job_keypair,
    JobKeypair,
    to_jwk,
)

__all__ = (
    "JobKeypair",
    "EnvironmentKeypair",
    "EnvironmentKeyError",
    "ed25519_seed_to_x25519_private",
    "from_jwk",
    "generate_environment_keypair",
    "generate_job_keypair",
    "load_esk_from_file",
    "load_esk_from_vault",
    "store_esk_to_vault",
    "to_jwk",
    "build_ce_jwt",
    "build_user_jwt",
    "header_jwk",
    "verify_jwt",
)
