import logging
from typing import (
    List,
    Optional,
)

from fastapi import (
    Body,
    Response,
    status,
)
from pydantic import BaseModel
from sqlalchemy import (
    false,
    true,
    update,
)

import tool_shed.util.shed_util_common as suc
from galaxy.exceptions import (
    InsufficientPermissionsException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.users import UserManager
from galaxy.model.base import transaction
from galaxy.webapps.base.webapp import create_new_session
from tool_shed.context import SessionRequestContext
from tool_shed.managers.users import (
    api_create_user,
    get_api_user,
    index,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import (
    GalaxySession,
    User as SaUser,
)
from tool_shed_client.schema import (
    CreateUserRequest,
    UserV2 as User,
)
from . import (
    depends,
    DependsOnTrans,
    ensure_valid_session,
    Router,
    set_auth_cookie,
    UserIdPathParam,
)

router = Router(tags=["users"])

log = logging.getLogger(__name__)


class UiRegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    bear_field: str


class HasCsrfToken(BaseModel):
    session_csrf_token: str


class UiLoginRequest(HasCsrfToken):
    login: str
    password: str


class UiLogoutRequest(HasCsrfToken):
    logout_all: bool = False


class UiLoginResponse(BaseModel):
    pass


class UiLogoutResponse(BaseModel):
    pass


class UiRegisterResponse(BaseModel):
    email: str
    activation_sent: bool = False
    activation_error: bool = False
    contact_email: Optional[str] = None


class UiChangePasswordRequest(BaseModel):
    current: str
    password: str


INVALID_LOGIN_OR_PASSWORD = "Invalid login or password"


@router.cbv
class FastAPIUsers:
    app: ToolShedApp = depends(ToolShedApp)
    user_manager: UserManager = depends(UserManager)
    api_key_manager: ApiKeyManager = depends(ApiKeyManager)

    @router.get(
        "/api/users",
        description="index users",
        operation_id="users__index",
    )
    def index(self, trans: SessionRequestContext = DependsOnTrans) -> List[User]:
        deleted = False
        return index(trans.app, deleted)

    @router.post(
        "/api/users",
        description="create a user",
        operation_id="users__create",
        require_admin=True,
    )
    def create(self, trans: SessionRequestContext = DependsOnTrans, request: CreateUserRequest = Body(...)) -> User:
        return api_create_user(trans, request)

    @router.get(
        "/api/users/current",
        description="show current user",
        operation_id="users__current",
    )
    def current(self, trans: SessionRequestContext = DependsOnTrans) -> User:
        user = trans.user
        if not user:
            raise ObjectNotFound()

        return get_api_user(trans.app, user)

    @router.get(
        "/api/users/{encoded_user_id}",
        description="show a user",
        operation_id="users__show",
    )
    def show(self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam) -> User:
        user = suc.get_user(trans.app, encoded_user_id)
        if user is None:
            raise ObjectNotFound()
        return get_api_user(trans.app, user)

    @router.get(
        "/api/users/{encoded_user_id}/api_key",
        name="get_or_create_api_key",
        summary="Return the user's API key",
        operation_id="users__get_or_create_api_key",
    )
    def get_or_create_api_key(
        self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam
    ) -> str:
        user = self._get_user(trans, encoded_user_id)
        return self.api_key_manager.get_or_create_api_key(user)

    @router.post(
        "/api/users/{encoded_user_id}/api_key",
        summary="Creates a new API key for the user",
        operation_id="users__create_api_key",
    )
    def create_api_key(
        self, trans: SessionRequestContext = DependsOnTrans, encoded_user_id: str = UserIdPathParam
    ) -> str:
        user = self._get_user(trans, encoded_user_id)
        return self.api_key_manager.create_api_key(user).key

    @router.delete(
        "/api/users/{encoded_user_id}/api_key",
        summary="Delete the current API key of the user",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="users__delete_api_key",
    )
    def delete_api_key(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_user_id: str = UserIdPathParam,
    ):
        user = self._get_user(trans, encoded_user_id)
        self.api_key_manager.delete_api_key(user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def _get_user(self, trans: SessionRequestContext, encoded_user_id: str):
        if encoded_user_id == "current":
            user = trans.user
        else:
            user = suc.get_user(trans.app, encoded_user_id)
        if user is None:
            raise ObjectNotFound()
        if not (trans.user_is_admin or trans.user == user):
            raise InsufficientPermissionsException()
        return user

    @router.post(
        "/api_internal/register",
        description="register a user",
        operation_id="users__internal_register",
    )
    def register(
        self, trans: SessionRequestContext = DependsOnTrans, request: UiRegisterRequest = Body(...)
    ) -> UiRegisterResponse:
        honeypot_field = request.bear_field
        if honeypot_field != "":
            message = "You've been flagged as a possible bot. If you are not, please try registering again and fill the form out carefully."
            raise RequestParameterInvalidException(message)

        username = request.username
        if username == "repos":
            raise RequestParameterInvalidException("Cannot create a user with the username 'repos'")
        self.user_manager.create(email=request.email, username=username, password=request.password)
        if self.app.config.user_activation_on:
            is_activation_sent = self.user_manager.send_activation_email(trans, request.email, username)
            if is_activation_sent:
                return UiRegisterResponse(email=request.email, activation_sent=True)
            else:
                return UiRegisterResponse(
                    email=request.email,
                    activation_sent=False,
                    activation_error=True,
                    contact_email=self.app.config.error_email_to,
                )
        else:
            return UiRegisterResponse(email=request.email)

    @router.put(
        "/api_internal/change_password",
        description="reset a user",
        operation_id="users__internal_change_password",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def change_password(
        self, trans: SessionRequestContext = DependsOnTrans, request: UiChangePasswordRequest = Body(...)
    ):
        password = request.password
        current = request.current
        if trans.user is None:
            raise InsufficientPermissionsException("Must be logged into use this functionality")
        user_id = trans.user.id
        token = None
        user, message = self.user_manager.change_password(
            trans, password=password, current=current, token=token, confirm=password, id=user_id
        )
        if not user:
            raise RequestParameterInvalidException(message)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api_internal/login",
        description="login to web UI",
        operation_id="users__internal_login",
    )
    def internal_login(
        self, trans: SessionRequestContext = DependsOnTrans, request: UiLoginRequest = Body(...)
    ) -> UiLoginResponse:
        log.info(f"top of internal_login {trans.session_csrf_token}")
        ensure_csrf_token(trans, request)
        login = request.login
        password = request.password
        user = self.user_manager.get_user_by_identity(login)
        if user is None:
            raise InsufficientPermissionsException(INVALID_LOGIN_OR_PASSWORD)
        elif user.deleted:
            message = (
                "This account has been marked deleted, contact your local Galaxy administrator to restore the account."
            )
            if trans.app.config.error_email_to is not None:
                message += f" Contact: {trans.app.config.error_email_to}."
            raise InsufficientPermissionsException(message)
        elif not trans.app.auth_manager.check_password(user, password, trans.request):
            raise InsufficientPermissionsException(INVALID_LOGIN_OR_PASSWORD)
        else:
            handle_user_login(trans, user)
        return UiLoginResponse()

    @router.put(
        "/api_internal/logout",
        description="logout of web UI",
        operation_id="users__internal_logout",
    )
    def internal_logout(
        self, trans: SessionRequestContext = DependsOnTrans, request: UiLogoutRequest = Body(...)
    ) -> UiLogoutResponse:
        ensure_csrf_token(trans, request)
        handle_user_logout(trans, logout_all=request.logout_all)
        return UiLogoutResponse()


def ensure_csrf_token(trans: SessionRequestContext, request: HasCsrfToken):
    session_csrf_token = request.session_csrf_token
    if not trans.session_csrf_token:
        ensure_valid_session(trans)
    message = None
    if not session_csrf_token:
        message = "No session token set, denying request."
    elif session_csrf_token != trans.session_csrf_token:
        log.info(f"{session_csrf_token} != {trans.session_csrf_token}")
        message = "Wrong session token found, denying request."
    if message:
        raise InsufficientPermissionsException(message)


def handle_user_login(trans: SessionRequestContext, user: SaUser) -> None:
    trans.app.security_agent.create_user_role(user, trans.app)
    replace_previous_session(trans, user)


def handle_user_logout(trans, logout_all=False):
    """
    Logout the current user:
        - invalidate current session + previous sessions (optional)
        - create a new session with no user associated
    """
    if logout_all:
        prev_session = trans.get_galaxy_session()
        if prev_session and prev_session.user_id:
            invalidate_user_sessions(trans.sa_session, prev_session.user_id)
    replace_previous_session(trans, None)


def replace_previous_session(trans, user):
    prev_galaxy_session = trans.get_galaxy_session()
    # Invalidate previous session
    if prev_galaxy_session:
        prev_galaxy_session.is_valid = False
    # Create new session
    new_session = create_new_session(trans, prev_galaxy_session, user)
    trans.set_galaxy_session(new_session)
    trans.sa_session.add_all((prev_galaxy_session, new_session))
    with transaction(trans.sa_session):
        trans.sa_session.commit()
    set_auth_cookie(trans, new_session)


def invalidate_user_sessions(session, user_id):
    stmt = (
        update(GalaxySession)
        .values(is_valid=false())
        .where(GalaxySession.user_id == user_id)
        .where(GalaxySession.is_valid == true())
    )
    session.execute(stmt)
    with transaction(session):
        session.commit()
