from fastapi import Request

from galaxy.webapps.galaxy.services.authenticate import (
    APIKeyResponse,
    AuthenticationService,
)
from . import (
    depends,
    Router,
)

router = Router(tags=["authenticate"])


@router.get(
    "/api/authenticate/baseauth",
    summary="Returns returns an API key for authenticated user based on BaseAuth headers.",
    operation_id="authenticate__baseauth",
)
def get_api_key(
    request: Request, authentication_service: AuthenticationService = depends(AuthenticationService)
) -> APIKeyResponse:
    authorization = request.headers.get("Authorization")
    auth = {"HTTP_AUTHORIZATION": authorization}
    return authentication_service.get_api_key(auth, request)
