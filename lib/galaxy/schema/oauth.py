"""Models for the OAuth 2.0 device flow endpoints.

Field names follow the OAuth specifications, since standard OAuth libraries read them as is:
- Server metadata: https://datatracker.ietf.org/doc/html/rfc8414#section-2
- Device authorization response: https://datatracker.ietf.org/doc/html/rfc8628#section-3.2
- Token response: https://datatracker.ietf.org/doc/html/rfc6749#section-5.1
- Error response: https://datatracker.ietf.org/doc/html/rfc6749#section-5.2
- Device flow error codes: https://datatracker.ietf.org/doc/html/rfc8628#section-3.5
"""

from datetime import datetime
from enum import Enum
from typing import Literal

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


class AuthorizationServerMetadata(Model):
    """What a standard OAuth app needs to log in to this Galaxy (RFC 8414 §2)."""

    issuer: str = Field(..., description="Base URL of this Galaxy.")
    device_authorization_endpoint: str = Field(..., description="URL to start a device flow login at.")
    token_endpoint: str = Field(..., description="URL to poll for the token at.")
    grant_types_supported: list[str] = Field(..., description="OAuth grant types this Galaxy supports.")
    # Required by RFC 8414, but its values are for browser logins, which Galaxy does not offer (for now?)
    response_types_supported: list[str] = Field([], description="Always empty: only the device flow is supported.")
    token_endpoint_auth_methods_supported: list[str] = Field(
        ["none"], description="Always `none`: apps are public and have no secret."
    )


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


class DeviceTokenResponse(Model):
    """Token issued once the user approves a device flow login (RFC 6749 §5.1)."""

    access_token: str = Field(..., description="Token the app sends with its Galaxy API requests.")
    token_type: Literal["Bearer"] = Field("Bearer", description="Always `Bearer`.")
    expires_in: int | None = Field(None, description="Seconds until the token expires. Left out if it does not expire.")
    scope: str | None = Field(None, description="Space-separated scopes the token grants.")


class OAuthErrorResponse(Model):
    """Error response from an OAuth endpoint (RFC 6749 §5.2)."""

    error: OAuthErrorCode = Field(..., description="OAuth error code, such as `invalid_client`.")
    error_description: str | None = Field(None, description="Human-readable explanation of the error.")


class DeviceAuthorizationDetails(Model):
    """A pending device flow login, as shown to the user before they approve or deny it."""

    user_code: str = Field(..., description="The code the user entered, e.g. `WDJB-MJHT`.")
    client_id: str = Field(..., description="ID of the app asking for access, e.g. `galaxy-cli`.")
    app_name: str = Field(..., description="Display name of the app, e.g. `Galaxy CLI`.")
    scopes: list[str] = Field(..., description="Scopes the app asks for. Empty if it asked for none.")
    requesting_ip: str | None = Field(None, description="IP address the app started the login from.")
    create_time: datetime = Field(..., description="When the app started the login (UTC).")
    expires_at: datetime = Field(..., description="When the code expires (UTC).")


class DeviceAuthorizationDecisionPayload(Model):
    """The user's answer to a pending device flow login."""

    approve: bool = Field(..., description="Whether the user approves the login (`true`) or denies it (`false`).")
