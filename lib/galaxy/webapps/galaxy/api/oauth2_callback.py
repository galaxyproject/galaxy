from typing import Optional

from fastapi import Query
from fastapi.responses import RedirectResponse

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.file_source_instances import FileSourceInstancesManager
from galaxy.schema.schema import OAuth2State
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.work.context import SessionRequestContext

StateQueryParam: str = Query(
    ...,
    title="State information sent with auth request",
    description="Base-64 encoded JSON used to route request within Galaxy.",
)
CodeQueryParam: Optional[str] = Query(
    None,
    title="OAuth2 Authorization Code from remote resource",
)
ErrorQueryParam: Optional[str] = Query(
    None,
    title="OAuth2 Error from remote resource",
)

router = Router(tags=["oauth2"])

ERROR_REDIRECT_PATH = "file_source_instances/create"


@router.cbv
class OAuth2Callback:
    file_source_instances_manager: FileSourceInstancesManager = depends(FileSourceInstancesManager)

    @router.get(
        "/oauth2_callback",
        summary="Callback entry point for remote resource responses with OAuth2 authorization codes",
    )
    def oauth2_callback(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        state: str = StateQueryParam,
        code: Optional[str] = CodeQueryParam,
        error: Optional[str] = ErrorQueryParam,
    ):
        if error:
            return RedirectResponse(f"{trans.request.url_path}{ERROR_REDIRECT_PATH}?error={error}")
        elif not code:
            return RedirectResponse(
                f"{trans.request.url_path}{ERROR_REDIRECT_PATH}?error=No credentials provided, please try again."
            )

        oauth2_state = OAuth2State.decode(state)
        # TODO: save session information in cookie to verify not CSRF with oauth2_state.nonce
        route = oauth2_state.route
        if route.startswith("file_source_instances/"):
            redirect = self.file_source_instances_manager.handle_authorization_code(trans, code, oauth2_state)
        # implement other routes here as needed for other components
        else:
            raise ObjectNotFound(f"Could not find oauth2 callback for route {route}")

        return RedirectResponse(f"{trans.request.url_path}{redirect}")
