from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import User


def create_user(app: ToolShedApp, email: str, username: str, password: str) -> User:
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
    sa_session.flush()
    app.security_agent.create_private_user_role(user)
    return user
