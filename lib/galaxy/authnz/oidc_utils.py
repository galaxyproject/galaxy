"""
OIDC-specific utility functions for token handling and verification.

This module contains helper functions that are specific to OpenID Connect (OIDC)
authentication. These should not be used with non-OIDC backends like OAuth2.
"""

import logging
from typing import (
    cast,
    TYPE_CHECKING,
)

import jwt
from social_core.backends.open_id_connect import OpenIdConnectAuth
from typing_extensions import TypeIs

from galaxy.exceptions import MalformedContents

if TYPE_CHECKING:
    from jwt.types import Options
    from social_core.backends.base import BaseAuth

    from galaxy.authnz.psa_authnz import Strategy

log = logging.getLogger(__name__)


def is_oidc_backend(backend: "BaseAuth") -> TypeIs[OpenIdConnectAuth]:
    """
    Check if a PSA backend is OIDC-based.

    :param backend: A PSA backend instance
    :return: True if backend is OpenIdConnectAuth, False otherwise
    """
    return isinstance(backend, OpenIdConnectAuth)


def is_decodable_jwt(token_str: str) -> bool:
    """
    Check if a token string looks like a decodable JWT.

    We assume decodable JWTs are in the format header.payload.signature

    :param token_str: Token string to check
    :return: True if token appears to be JWT format
    """
    if not token_str:
        return False
    components = token_str.split(".")
    return len(components) == 3


def decode_access_token(token_str: str, backend: OpenIdConnectAuth) -> dict:
    """
    Decode and verify an OIDC access token.

    This function verifies:
    - Signature using provider's public keys
    - Token expiration (exp claim)
    - Token not-before time (nbf claim)
    - Token issued-at time (iat claim)
    - Audience (aud claim) matches accepted_audiences
    - Issuer (iss claim) matches expected issuer

    :param token_str: JWT access token string
    :param backend: OpenIdConnectAuth backend instance
    :return: Decoded JWT payload as dict
    :raises InvalidTokenError: If token is invalid or verification fails
    """
    signing_key = backend.find_valid_key(token_str)
    jwk = jwt.PyJWK(signing_key)
    strategy = cast("Strategy", backend.strategy)

    options: Options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_nbf": True,
        "verify_iat": True,
        "verify_aud": bool(strategy.config["accepted_audiences"]),
        "verify_iss": True,
    }
    decoded = jwt.decode(
        token_str,
        key=jwk,
        algorithms=[jwk.algorithm_name],
        audience=strategy.config["accepted_audiences"],
        issuer=backend.id_token_issuer(),
        options=options,
    )
    return decoded


def verify_oidc_response(response: dict) -> None:
    """
    Verify that an OIDC authentication response contains required fields.

    Checks for:
    - id_token presence
    - iat (issued at) claim in id_token

    :param response: OIDC authentication response dict
    :raises MalformedContents: If required fields are missing
    """
    if "id_token" not in response:
        raise MalformedContents("Missing id_token in OIDC response")

    # Decode without verification to check structure
    decoded = jwt.decode(response["id_token"], options={"verify_signature": False})
    if "iat" not in decoded:
        raise MalformedContents("Missing iat claim in id_token")
