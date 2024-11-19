"""
Contains the user interface in the Universe class
"""

import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from urllib.parse import unquote

from markupsafe import escape
from sqlalchemy.exc import NoResultFound

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import Conflict
from galaxy.managers import users
from galaxy.model.db.user import get_user_by_email
from galaxy.security.validate_user_input import (
    validate_email,
    validate_publicname,
)
from galaxy.structured_app import StructuredApp
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    url_for,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    UsesFormDefinitionsMixin,
)
from ..api import depends

log = logging.getLogger(__name__)


def _filtered_registration_params_dict(payload):
    return {k: v for (k, v) in payload.items() if k in ["email", "username", "password", "confirm", "subscribe"]}


class User(BaseUIController, UsesFormDefinitionsMixin):
    user_manager: users.UserManager = depends(users.UserManager)
    installed_len_files = None

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    def __handle_role_and_group_auto_creation(
        self,
        trans,
        user,
        roles,
        auto_create_roles=False,
        auto_create_groups=False,
        auto_assign_roles_to_groups_only=False,
    ):
        for role_name in roles:
            role = None
            group = None
            if auto_create_roles:
                try:
                    # first try to find the role
                    role = trans.app.security_agent.get_role(role_name)
                except NoResultFound:
                    # or create it
                    role, num_in_groups = trans.app.security_agent.create_role(
                        role_name,
                        "Auto created upon user registration",
                        [],
                        [],
                        create_group_for_role=auto_create_groups,
                    )
                    if auto_create_groups:
                        trans.log_event("Created role and group for auto-registered user.")
                    else:
                        trans.log_event("Created role for auto-registered user.")
            if auto_create_groups:
                # only create a group if not existing yet
                try:
                    group = (
                        self.sa_session.query(trans.app.model.Group)
                        .filter(trans.app.model.Group.name == role_name)
                        .first()
                    )
                except NoResultFound:
                    group = self.model.Group(name=role_name)
                    self.sa_session.add(group)
                trans.app.security_agent.associate_user_group(user, group)

            if auto_assign_roles_to_groups_only and group and role:
                trans.log_event("Assigning role to group only")
                trans.app.security_agent.associate_group_role(group, role)
            elif not auto_assign_roles_to_groups_only and role:
                trans.log_event("Assigning role to newly created user")
                trans.app.security_agent.associate_user_role(user, role)

    def __autoregistration(self, trans, login, password):
        """
        Does the autoregistration if enabled. Returns a message
        """
        try:
            autoreg = trans.app.auth_manager.check_auto_registration(trans, login, password)
        except Conflict as conflict:
            return f"Auto-registration failed, {conflict}", None
        user = None
        if autoreg["auto_reg"]:
            email = autoreg["email"]
            username = autoreg["username"]
            message = " ".join(
                (validate_email(trans, email, allow_empty=True), validate_publicname(trans, username))
            ).rstrip()
            if not message:
                user = self.user_manager.create(email=email, username=username, password="")
                if trans.app.config.user_activation_on:
                    self.user_manager.send_activation_email(trans, email, username)
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                if not trans.user_is_admin:
                    trans.handle_user_login(user)
                    trans.log_event("User (auto) created a new account")
                    trans.log_event("User logged in")
                if "attributes" in autoreg and "roles" in autoreg["attributes"]:
                    self.__handle_role_and_group_auto_creation(
                        trans,
                        user,
                        autoreg["attributes"]["roles"],
                        auto_create_groups=autoreg["auto_create_groups"],
                        auto_create_roles=autoreg["auto_create_roles"],
                        auto_assign_roles_to_groups_only=autoreg["auto_assign_roles_to_groups_only"],
                    )
            else:
                message = f"Auto-registration failed, contact your local Galaxy administrator. {message}"
        else:
            message = "No such user or invalid password."
        return message, user

    @expose_api_anonymous_and_sessionless
    def login(self, trans, payload=None, **kwd):
        payload = payload or {}
        return self.__validate_login(trans, payload, **kwd)

    def __validate_login(self, trans, payload=None, **kwd):
        """Handle Galaxy Log in"""
        if not payload:
            payload = kwd
        message = trans.check_csrf_token(payload)
        if message:
            return self.message_exception(trans, message)
        login = payload.get("login")
        password = payload.get("password")
        redirect = payload.get("redirect")
        status = None
        if not login or not password:
            return self.message_exception(trans, "Please specify a username and password.")
        user = self.user_manager.get_user_by_identity(login)
        log.debug(f"trans.app.config.auth_config_file: {trans.app.config.auth_config_file}")
        if user is None:
            message, user = self.__autoregistration(trans, login, password)
            if message:
                return self.message_exception(trans, message)
        elif user.purged:
            message = "This account has been permanently deleted."
            return self.message_exception(trans, message, sanitize=False)
        elif user.deleted:
            message = (
                "This account has been marked deleted, contact your local Galaxy administrator to restore the account."
            )
            if trans.app.config.error_email_to is not None:
                message += f" Contact: {trans.app.config.error_email_to}."
            return self.message_exception(trans, message, sanitize=False)
        elif user.external:
            message = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
            if trans.app.config.error_email_to is not None:
                message += f" Contact: {trans.app.config.error_email_to}."
            return self.message_exception(trans, message, sanitize=False)
        elif not trans.app.auth_manager.check_password(user, password, trans.request):
            return self.message_exception(trans, "Invalid password.")
        elif trans.app.config.user_activation_on and not user.active:  # activation is ON and the user is INACTIVE
            if trans.app.config.activation_grace_period != 0:  # grace period is ON
                if self.is_outside_grace_period(
                    trans, user.create_time
                ):  # User is outside the grace period. Login is disabled and he will have the activation email resent.
                    message, status = self.resend_activation_email(trans, user.email, user.username)
                    return self.message_exception(trans, message, sanitize=False)
                else:  # User is within the grace period, let him log in.
                    trans.handle_user_login(user)
                    trans.log_event("User logged in")
            else:  # Grace period is off. Login is disabled and user will have the activation email resent.
                message, status = self.resend_activation_email(trans, user.email, user.username)
                return self.message_exception(trans, message, sanitize=False)
        else:  # activation is OFF
            pw_expires = getattr(trans.app.config, "password_expiration_period", None)
            if pw_expires and user.last_password_change < datetime.today() - pw_expires:
                # Password is expired, we don't log them in.
                return {
                    "message": "Your password has expired. Please reset or change it to access Galaxy.",
                    "status": "warning",
                    "expired_user": trans.security.encode_id(user.id),
                }
            trans.handle_user_login(user)
            trans.log_event("User logged in")
            if pw_expires and user.last_password_change < datetime.today() - timedelta(days=pw_expires.days / 10):
                # If password is about to expire, modify message to state that.
                expiredate = datetime.today() - user.last_password_change + pw_expires
                return {"message": f"Your password will expire in {expiredate.days} day(s).", "status": "warning"}
        return {"message": "Success.", "redirect": self.__get_redirect_url(redirect)}

    @web.expose
    def resend_verification(self, trans, **kwargs):
        """
        Exposed function for use outside of the class. E.g. when user click on the resend link in the masthead.
        """
        message, status = self.resend_activation_email(trans, None, None)
        if status:
            return trans.show_ok_message(message)
        else:
            return trans.show_error_message(message)

    def resend_activation_email(self, trans, email, username):
        """
        Function resends the verification email in case user wants to log in with an inactive account or he clicks the resend link.
        """
        if email is None:  # User is coming from outside registration form, load email from trans
            if not trans.user:
                return "No session found, cannot send activation email.", None
            email = trans.user.email
        if username is None:  # User is coming from outside registration form, load email from trans
            username = trans.user.username
        is_activation_sent = self.user_manager.send_activation_email(trans, email, username)
        if is_activation_sent:
            message = f"This account has not been activated yet. The activation link has been sent again. Please check your email address <b>{escape(email)}</b> including the spam/trash folder. <a target=\"_top\" href=\"{url_for('/')}\">Return to the home page</a>."
        else:
            message = f"This account has not been activated yet but we are unable to send the activation link. Please contact your local Galaxy administrator. <a target=\"_top\" href=\"{url_for('/')}\">Return to the home page</a>."
            if trans.app.config.error_email_to is not None:
                message += f" Error contact: {trans.app.config.error_email_to}."
        return message, is_activation_sent

    def is_outside_grace_period(self, trans, create_time):
        """
        Function checks whether the user is outside the config-defined grace period for inactive accounts.
        """
        #  Activation is forced and the user is not active yet. Check the grace period.
        activation_grace_period = trans.app.config.activation_grace_period
        delta = timedelta(hours=int(activation_grace_period))
        time_difference = datetime.now(tz=timezone.utc) - create_time
        return time_difference > delta or activation_grace_period == 0

    @web.expose
    @web.json
    def logout(self, trans, logout_all=False, **kwd):
        if message := trans.check_csrf_token(kwd):
            return self.message_exception(trans, message)
        # Since logging an event requires a session, we'll log prior to ending the session
        trans.log_event("User logged out")
        trans.handle_user_logout(logout_all=logout_all)
        success_response = {"message": "Success."}  # This is a little weird as a response.
        if trans.app.config.use_remote_user and trans.app.config.remote_user_logout_href:
            success_response["redirect_uri"] = trans.app.config.remote_user_logout_href
        return success_response

    @expose_api_anonymous_and_sessionless
    def create(self, trans, payload=None, **kwd):
        if not payload:
            payload = kwd
        message = trans.check_csrf_token(payload)
        if message:
            return self.message_exception(trans, message)
        user, message = self.user_manager.register(trans, **_filtered_registration_params_dict(payload))
        if message:
            return self.message_exception(trans, message, sanitize=False)
        elif user and not trans.user_is_admin:
            trans.handle_user_login(user)
            trans.log_event("User created a new account")
            trans.log_event("User logged in")
        return {"message": "Success."}

    @web.expose
    def activate(self, trans, **kwd):
        """
        Check whether token fits the user and then activate the user's account.
        """
        params = util.Params(kwd, sanitize=False)
        email = params.get("email", None)
        if email is not None:
            email = unquote(email)
        activation_token = params.get("activation_token", None)
        index_url = web.url_for(controller="root", action="index")

        if email is None or activation_token is None:
            #  We don't have the email or activation_token, show error.
            return trans.show_error_message(
                f"You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='{index_url}'>Go to login page.</a>"
            )
        else:
            # Find the user
            user = get_user_by_email(trans.sa_session, email)
            if not user:
                # Probably wrong email address
                return trans.show_error_message(
                    f"You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='{index_url}'>Go to login page.</a>"
                )
            # If the user is active already don't try to activate
            if user.active is True:
                return trans.show_ok_message(
                    f"Your account is already active. Nothing has changed. <br><a href='{index_url}'>Go to login page.</a>"
                )
            if user.activation_token == activation_token[:64]:
                user.activation_token = None
                self.user_manager.activate(user)
                return trans.show_ok_message(
                    f"Your account has been successfully activated! <br><a href='{index_url}'>Go to login page.</a>"
                )
            else:
                #  Tokens don't match. Activation is denied.
                return trans.show_error_message(
                    f"You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='{index_url}'>Go to login page.</a>"
                )

    @expose_api_anonymous_and_sessionless
    def change_password(self, trans, payload=None, **kwd):
        """
        Allows to change own password.

        :type   payload: dict
        :param  payload: dictionary structure containing:
            * id:               encoded user id
            * current:          current user password
            * token:            temporary token to change password (instead of id and current)
            * password:         new password
            * confirm:          new password (confirmation)
        """
        payload = payload or {}
        user, message = self.user_manager.change_password(trans, **payload)
        if user is None:
            return self.message_exception(trans, message)
        trans.handle_user_login(user)
        return {"message": "Password has been changed."}

    @expose_api_anonymous_and_sessionless
    def reset_password(self, trans, payload=None, **kwd):
        """Reset the user's password. Send an email with token that allows a password change."""
        payload = payload or {}
        if message := self.user_manager.send_reset_email(trans, payload):
            return self.message_exception(trans, message)
        return {"message": "If an account exists for this email address a confirmation email will be dispatched."}

    def __get_redirect_url(self, redirect):
        if not redirect or redirect == "None":
            return None
        root_url = url_for("/", qualified=True)
        # compare urls, to prevent a redirect from pointing (directly) outside of galaxy
        # or to enter a logout/login loop
        if not util.compare_urls(root_url, redirect, compare_path=False) or util.compare_urls(
            url_for(controller="user", action="logout", qualified=True), redirect
        ):
            log.warning("Redirect URL is outside of Galaxy, will redirect to Galaxy root instead: %s", redirect)
            redirect = root_url
        elif util.compare_urls(url_for(controller="user", action="logout", qualified=True), redirect):
            redirect = root_url
        return redirect
