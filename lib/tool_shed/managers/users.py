from typing import List

from sqlalchemy import select

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.base import transaction
from galaxy.security.validate_user_input import (
    validate_email,
    validate_password,
    validate_publicname,
)
from tool_shed.context import ProvidesUserContext
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import User
from tool_shed_client.schema import (
    CreateUserRequest,
    UserV2 as ApiUser,
)


def index(app: ToolShedApp, deleted: bool) -> List[ApiUser]:
    users: List[ApiUser] = []
    for user in get_users_by_deleted(app.model.context, app.model.User, deleted):
        users.append(get_api_user(app, user))
    return users


def create_user(app: ToolShedApp, email: str, username: str, password: str) -> User:
    if username == "repos":
        raise RequestParameterInvalidException("Cannot create a tool shed user with the username repos")
    sa_session = app.model.context
    user = User(email=email)
    user.set_password_cleartext(password)
    user.username = username
    # API was doing this but mypy doesn't think user has an active boolean attribute.
    # if app.config.user_activation_on:
    #    user.active = False
    # else:
    #    user.active = True  # Activation is off, every new user is active by default.
    sa_session.add(user)
    with transaction(sa_session):
        sa_session.commit()
    app.security_agent.create_private_user_role(user)
    return user


def api_create_user(trans: ProvidesUserContext, request: CreateUserRequest) -> ApiUser:
    app = trans.app
    message = _validate(
        trans, email=request.email, password=request.password, confirm=request.password, username=request.username
    )
    if message:
        raise RequestParameterInvalidException(message)
    user = create_user(app, request.email, request.username, request.password)
    return get_api_user(app, user)


def get_api_user(app: ToolShedApp, user: User) -> ApiUser:
    admin = app.config.is_admin_user(user)
    return ApiUser(
        id=app.security.encode_id(user.id),
        username=user.username,
        is_admin=admin,
    )


def _validate(trans: ProvidesUserContext, email: str, password: str, confirm: str, username: str) -> str:
    if username in ["repos"]:
        return f"The term '{username}' is a reserved word in the Tool Shed, so it cannot be used as a public user name."
    message = "\n".join(
        (
            validate_email(trans, email),
            validate_password(trans, password, confirm),
            validate_publicname(trans, username),
        )
    ).rstrip()
    return message


def get_users_by_deleted(session, user_model, deleted):
    stmt = select(user_model).where(user_model.deleted == deleted).order_by(user_model.username)
    return session.scalars(stmt)
