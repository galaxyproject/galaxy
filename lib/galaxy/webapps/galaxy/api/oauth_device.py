"""API for the OAuth 2.0 device flow (RFC 8628), which lets an external app log in to Galaxy for a user.

These endpoints follow the OAuth specifications rather than Galaxy's API conventions, since
standard OAuth libraries call them: requests are form-encoded and errors use the OAuth shape.
"""

from typing import Any

from fastapi import (
    Form,
    Path,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ObjectNotFound
from galaxy.managers._config_templates import galaxy_url_for_path
from galaxy.managers.oauth_device import (
    DEVICE_CODE_EXPIRES_IN,
    DEVICE_CODE_GRANT_TYPE,
    OAuthDeviceManager,
    OAuthError,
    POLLING_INTERVAL,
)
from galaxy.model import User
from galaxy.schema.oauth import (
    DeviceAuthorizationDecisionPayload,
    DeviceAuthorizationResponse,
    DeviceTokenResponse,
    OAuthErrorCode,
    OAuthErrorResponse,
)
from galaxy.work.context import SessionRequestContext
from . import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

router = Router(tags=["oauth"])

OAUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {400: {"model": OAuthErrorResponse}}


def oauth_error_response(error: OAuthError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=OAuthErrorResponse(error=error.error, error_description=error.description).model_dump(
            exclude_none=True
        ),
    )


def require_device_flow_enabled(config: GalaxyAppConfiguration) -> None:
    if not config.enable_oauth_device_flow:
        raise ObjectNotFound("The OAuth device flow is not enabled on this Galaxy.")


@router.post(
    "/api/oauth/device_authorization",
    summary="Start an OAuth device flow login",
    public=True,
    unstable=True,
    response_model=DeviceAuthorizationResponse,
    responses=OAUTH_ERROR_RESPONSES,
)
def device_authorization(
    request: Request,
    trans: SessionRequestContext = DependsOnTrans,
    # Optional here so a missing value gets an OAuth `invalid_request`, not Galaxy's validation error.
    client_id: str | None = Form(None, description="Required. ID of the app asking for access, e.g. `galaxy-cli`."),
    scope: str | None = Form(None, description="Space-separated scopes the app asks for."),
    manager: OAuthDeviceManager = depends(OAuthDeviceManager),
) -> DeviceAuthorizationResponse | JSONResponse:
    """Start a device login for a known app (RFC 8628 §3.1).

    Returns a secret device code for the app to poll the token endpoint with, and a short
    user code for the user to enter on the verification page.
    """
    require_device_flow_enabled(trans.app.config)
    try:
        if not client_id:
            raise OAuthError(OAuthErrorCode.INVALID_REQUEST, "Missing client_id.")
        started = manager.start_authorization(
            client_id=client_id,
            scope=scope,
            requesting_ip=request.client.host if request.client else None,
        )
    except OAuthError as e:
        return oauth_error_response(e)
    return DeviceAuthorizationResponse(
        device_code=started.device_code,
        user_code=started.authorization.user_code,
        verification_uri=galaxy_url_for_path(trans, "login/device"),
        expires_in=DEVICE_CODE_EXPIRES_IN,
        interval=POLLING_INTERVAL,
    )


@router.put(
    "/api/oauth/device_authorization/{user_code}",
    summary="Approve or deny an OAuth device flow login",
    unstable=True,
    status_code=status.HTTP_204_NO_CONTENT,
)
def decide_device_authorization(
    payload: DeviceAuthorizationDecisionPayload,
    user_code: str = Path(..., description="The code shown in the app's terminal, e.g. `WDJB-MJHT`."),
    trans: SessionRequestContext = DependsOnTrans,
    user: User = DependsOnUser,
    manager: OAuthDeviceManager = depends(OAuthDeviceManager),
) -> Response:
    """Record the logged-in user's approval or denial of a pending device login.

    Called by Galaxy's verification page, so it uses Galaxy's usual errors, not the OAuth shape.
    """
    require_device_flow_enabled(trans.app.config)
    manager.decide(user_code, user, payload.approve)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/oauth/token",
    summary="Get a token for an approved OAuth device flow login",
    public=True,
    unstable=True,
    response_model=DeviceTokenResponse,
    response_model_exclude_none=True,
    responses=OAUTH_ERROR_RESPONSES,
)
def token(
    response: Response,
    trans: SessionRequestContext = DependsOnTrans,
    # Optional here so a missing value gets an OAuth `invalid_request`, not Galaxy's validation error.
    grant_type: str | None = Form(None, description=f"Required. Must be `{DEVICE_CODE_GRANT_TYPE}`."),
    device_code: str | None = Form(None, description="Required. The device code from the device authorization."),
    client_id: str | None = Form(None, description="Required. ID of the app that started the login."),
    manager: OAuthDeviceManager = depends(OAuthDeviceManager),
) -> DeviceTokenResponse | JSONResponse:
    """Poll for the token of a device login (RFC 8628 §3.4).

    Returns `authorization_pending` until the user approves the login, then the token, once.
    """
    require_device_flow_enabled(trans.app.config)
    try:
        if not grant_type or not device_code or not client_id:
            raise OAuthError(OAuthErrorCode.INVALID_REQUEST, "Missing grant_type, device_code or client_id.")
        if grant_type != DEVICE_CODE_GRANT_TYPE:
            raise OAuthError(OAuthErrorCode.UNSUPPORTED_GRANT_TYPE, f"Unsupported grant_type '{grant_type}'.")
        issued = manager.respond_to_poll(client_id, device_code)
    except OAuthError as e:
        return oauth_error_response(e)
    # Token responses must never be cached (RFC 6749 §5.1).
    response.headers["Cache-Control"] = "no-store"
    return DeviceTokenResponse(access_token=issued.access_token, expires_in=issued.expires_in, scope=issued.scope)
