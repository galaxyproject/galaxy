"""Models for the OAuth 2.0 device flow endpoints.

Field names follow the OAuth specifications, since standard OAuth libraries read them as is:
- Device authorization response: https://datatracker.ietf.org/doc/html/rfc8628#section-3.2
- Error response: https://datatracker.ietf.org/doc/html/rfc6749#section-5.2
- Device flow error codes: https://datatracker.ietf.org/doc/html/rfc8628#section-3.5
"""

from enum import Enum

from pydantic import Field

from galaxy.schema.schema import Model


class OAuthErrorCode(str, Enum):
    """OAuth error codes Galaxy can return (RFC 6749 §5.2 and RFC 8628 §3.5)."""

    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    AUTHORIZATION_PENDING = "authorization_pending"
    SLOW_DOWN = "slow_down"
    ACCESS_DENIED = "access_denied"
    EXPIRED_TOKEN = "expired_token"


class DeviceAuthorizationResponse(Model):
    """Response to a device authorization request (RFC 8628 §3.2).

    _The optional `verification_uri_complete` is left out on purpose, so the user always types the
    code and can't approve a login from a link someone else sent them (RFC 8628 §5.4)._
    """

    device_code: str = Field(..., description="Secret code the app polls the token endpoint with.")
    user_code: str = Field(..., description="Short code the user enters on the verification page.")
    verification_uri: str = Field(..., description="Page where the user enters the code.")
    expires_in: int = Field(..., description="Seconds until both codes expire.")
    interval: int = Field(..., description="Minimum seconds the app waits between token requests.")


class OAuthErrorResponse(Model):
    """Error response from an OAuth endpoint (RFC 6749 §5.2)."""

    error: OAuthErrorCode = Field(..., description="OAuth error code, such as `invalid_client`.")
    error_description: str | None = Field(None, description="Human-readable explanation of the error.")


class DeviceAuthorizationDecisionPayload(Model):
    """The user's answer to a pending device flow login."""

    approve: bool = Field(..., description="Whether the user approves the login (`true`) or denies it (`false`).")
