import logging
from urllib.parse import (
    urlencode,
    urljoin,
)

from sqlalchemy import (
    func,
    select,
)

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    InternalServerError,
    RequestParameterInvalidException,
)
from galaxy.security.validate_user_input import (
    validate_email,
    validate_password,
    validate_publicname,
)
from galaxy.util import send_mail
from tool_shed.context import (
    ProvidesUserContext,
    SessionRequestContext,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import (
    PasswordResetToken,
    User,
)
from tool_shed_client.schema import (
    CreateUserRequest,
    UserV2 as ApiUser,
)

log = logging.getLogger(__name__)

RESET_PASSWORD_PATH = "user/reset_password"

PASSWORD_RESET_TEMPLATE = """
To reset your Tool Shed password at %s use the following link, which will
expire %s.

%s

If you did not make this request, no action is necessary on your part, though
you may want to notify an administrator.

If you're having trouble using the link when clicking it from an email client,
you can also copy and paste it into your browser.
"""


def index(app: ToolShedApp, deleted: bool) -> list[ApiUser]:
    users: list[ApiUser] = []
    for user in get_users_by_deleted(app.model.context, User, deleted):
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


def send_password_reset_email(trans: SessionRequestContext, email: str) -> None:
    """Mail a password reset link to ``email``.

    Nothing is raised when no account matches - the caller is anonymous, so
    confirming which addresses are registered would hand out a user list.
    """
    app = trans.app
    if app.config.smtp_server is None:
        raise ConfigDoesNotAllowException(
            "Mail is not configured for this Tool Shed and password reset information cannot be sent. "
            "Please contact an administrator."
        )
    if message := validate_email(trans, email, check_dup=False):
        raise RequestParameterInvalidException(message)
    user = _user_for_password_reset(trans, email)
    if user is None:
        log.warning("Password reset requested for unknown or deleted account.")
        return
    reset_token = PasswordResetToken(user)
    expiration_time = reset_token.expiration_time
    assert expiration_time is not None
    trans.sa_session.add(reset_token)
    trans.sa_session.commit()
    reset_url = f"{urljoin(trans.request.base, RESET_PASSWORD_PATH)}?{urlencode({'token': reset_token.token})}"
    body = PASSWORD_RESET_TEMPLATE % (
        trans.request.host,
        expiration_time.strftime(app.config.pretty_datetime_format),
        reset_url,
    )
    try:
        send_mail(app.config.email_from, email, "Tool Shed Password Reset", body, app.config)
    except Exception:
        # The requester is anonymous, so the mail server's own error text stays in the log.
        log.exception("Failed to send password reset email.")
        raise InternalServerError("Failed to send the password reset email. Please contact an administrator.")
    log.info("Sent a password reset email for user %s.", user.id)


def set_user_password(trans: ProvidesUserContext, user: User, password: str, confirm: str) -> None:
    """Set ``user``'s password without requiring their current one - admin only."""
    if message := validate_password(trans, password, confirm):
        raise RequestParameterInvalidException(message)
    user.set_password_cleartext(password)
    trans.sa_session.add(user)
    trans.sa_session.commit()


def _user_for_password_reset(trans: ProvidesUserContext, email: str) -> User | None:
    session = trans.sa_session
    user = session.scalars(select(User).where(User.email == email)).first()
    if user is None:
        user = session.scalars(select(User).where(func.lower(User.email) == email.lower())).first()
    if user is None or user.deleted:
        return None
    return user


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
            # tool_shed.context.ProvidesUserContext is a structurally analogous but
            # nominally distinct hierarchy from galaxy.managers.context.ProvidesAppContext;
            # trans satisfies everything these helpers actually use (.app, .sa_session).
            validate_email(trans, email),
            validate_password(trans, password, confirm),
            validate_publicname(trans, username),
        )
    ).rstrip()
    return message


def get_users_by_deleted(session, user_model, deleted):
    stmt = select(user_model).where(user_model.deleted == deleted).order_by(user_model.username)
    return session.scalars(stmt)
