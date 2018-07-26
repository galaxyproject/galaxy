"""
Contains implementations of the authentication logic.
"""
import logging
import random
import socket
from datetime import datetime

from markupsafe import escape
from sqlalchemy import and_, true

from galaxy.auth.util import get_authenticators, parse_auth_results
from galaxy.exceptions import Conflict
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_password
from galaxy.util import hash_util, send_mail, string_as_bool
from galaxy.web import url_for

log = logging.getLogger(__name__)


class AuthManager(object):

    def __init__(self, app):
        self.__app = app
        self.redact_username_in_logs = app.config.redact_username_in_logs
        self.authenticators = get_authenticators(app.config.auth_config_file)
        self.user_manager = users.UserManager(app)

    def check_registration_allowed(self, email, username, password):
        """Checks if the provided email/username is allowed to register."""
        message = ''
        status = 'done'
        for provider, options in self.active_authenticators(email, username, password):
            allow_reg = _get_allow_register(options)
            if allow_reg == 'challenge':
                auth_results = provider.authenticate(email, username, password, options)
                if auth_results[0] is True:
                    break
                if auth_results[0] is None:
                    message = 'Invalid email address/username or password.'
                    status = 'error'
                    break
            elif allow_reg is True:
                break
            elif allow_reg is False:
                message = 'Account registration not required for your account.  Please simply login.'
                status = 'error'
                break
        return message, status

    def check_auto_registration(self, trans, login, password, no_password_check=False):
        """
        Checks the username/email & password using auth providers in order.
        If a match is found, returns the 'auto-register' option for that provider.
        """
        if '@' in login:
            email = login
            username = None
        else:
            email = None
            username = login
        auth_return = {
            "auto_reg": False,
            "email": "",
            "username": ""
        }
        for provider, options in self.active_authenticators(email, username, password):
            if provider is None:
                log.debug("Unable to find module: %s" % options)
            else:
                options['no_password_check'] = no_password_check
                auth_results = provider.authenticate(email, username, password, options)
                if auth_results[0] is True:
                    try:
                        auth_return = parse_auth_results(trans, auth_results, options)
                    except Conflict:
                        break
                    return auth_return
                elif auth_results[0] is None:
                    auto_email = str(auth_results[1]).lower()
                    auto_username = str(auth_results[2]).lower()
                    log.debug("Email: %s, Username %s, stopping due to failed non-continue" % (auto_email, auto_username))
                    break  # end authentication (skip rest)
        return auth_return

    def check_password(self, user, password):
        """Checks the username/email and password using auth providers."""
        for provider, options in self.active_authenticators(user.email, user.username, password):
            if provider is None:
                log.debug("Unable to find module: %s" % options)
            else:
                auth_result = provider.authenticate_user(user, password, options)
                if auth_result is True:
                    return True  # accept user
                elif auth_result is None:
                    break  # end authentication (skip rest)
        return False

    def check_change_password(self, user, current_password):
        """Checks that auth provider allows password changes and current_password
        matches.
        """
        for provider, options in self.active_authenticators(user.email, user.username, current_password):
            if provider is None:
                log.debug("Unable to find module: %s" % options)
            else:
                auth_result = provider.authenticate_user(user, current_password, options)
                if auth_result is True:
                    if string_as_bool(options.get("allow-password-change", False)):
                        return
                    else:
                        return 'Password change not supported.'
                elif auth_result is None:
                    break  # end authentication (skip rest)
        return 'Invalid current password.'

    def active_authenticators(self, email, username, password):
        """Yields AuthProvider instances for the provided configfile that match the
        filters.
        """
        try:
            for authenticator in self.authenticators:
                filter_template = authenticator.filter_template
                if filter_template:
                    filter_str = filter_template.format(email=email, username=username, password=password)
                    passed_filter = eval(filter_str, {"__builtins__": None}, {'str': str})
                    if not passed_filter:
                        continue  # skip to next
                options = authenticator.options
                options['redact_username_in_logs'] = self.redact_username_in_logs
                yield authenticator.plugin, options
        except Exception:
            log.exception("Active Authenticators Failure")
            raise

    def change_password(self, trans, password=None, confirm=None, token=None, id=None, user=None, current=None, **kwd):
        """
        Allows to change a user password with a token.
        """
        if not token and not id and not user:
            return None, "Please provide a token or a user and password."
        if token:
            token_result = trans.sa_session.query(trans.app.model.PasswordResetToken).get(token)
            if not token_result or not token_result.expiration_time > datetime.utcnow():
                return None, "Invalid or expired password reset token, please request a new one."
            user = token_result.user
            message = self.__set_password(trans, user, password, confirm)
            if message:
                return None, message
            token_result.expiration_time = datetime.utcnow()
            trans.sa_session.add(token_result)
            return user, "Password has been changed. Token has been invalidated."
        else:
            if not user:
                user = self.user_manager.by_id(trans.app.security.decode_id(id))
            if user:
                message = self.check_change_password(user, current)
                if message:
                    return None, message
                message = self.__set_password(trans, user, password, confirm)
                if message:
                    return None, message
                return user, "Password has been changed."
            else:
                return user, "User not found."

    def __set_password(self, trans, user, password, confirm):
        if not password:
            return "Please provide a new password."
        if user:
            # Validate the new password
            message = validate_password(trans, password, confirm)
            if message:
                return message
            else:
                # Save new password
                user.set_password_cleartext(password)
                # Invalidate all other sessions
                for other_galaxy_session in trans.sa_session.query(trans.app.model.GalaxySession) \
                                                 .filter(and_(trans.app.model.GalaxySession.table.c.user_id == user.id,
                                                              trans.app.model.GalaxySession.table.c.is_valid == true(),
                                                              trans.app.model.GalaxySession.table.c.id != trans.galaxy_session.id)):
                    other_galaxy_session.is_valid = False
                    trans.sa_session.add(other_galaxy_session)
                trans.sa_session.add(user)
                trans.sa_session.flush()
                trans.log_event("User change password")
        else:
            return "Failed to determine user, access denied."

    def send_verification_email(self, trans, email, username):
        """
        Send the verification email containing the activation link to the user's email.
        """
        activation_link = self.__prepare_activation_link(trans, escape(email))
        host = trans.request.host.split(':')[0]
        if host in ['localhost', '127.0.0.1', '0.0.0.0']:
            host = socket.getfqdn()
        body = ("Hello %s,\n\n"
                "In order to complete the activation process for %s begun on %s at %s, please click on the following link to verify your account:\n\n"
                "%s \n\n"
                "By clicking on the above link and opening a Galaxy account you are also confirming that you have read and agreed to Galaxy's Terms and Conditions for use of this service (%s). This includes a quota limit of one account per user. Attempts to subvert this limit by creating multiple accounts or through any other method may result in termination of all associated accounts and data.\n\n"
                "Please contact us if you need help with your account at: %s. You can also browse resources available at: %s. \n\n"
                "More about the Galaxy Project can be found at galaxyproject.org\n\n"
                "Your Galaxy Team" % (escape(username), escape(email),
                                      datetime.utcnow().strftime("%D"),
                                      trans.request.host, activation_link,
                                      trans.app.config.terms_url,
                                      trans.app.config.error_email_to,
                                      trans.app.config.instance_resource_url))
        to = email
        frm = trans.app.config.email_from or 'galaxy-no-reply@' + host
        subject = 'Galaxy Account Activation'
        try:
            send_mail(frm, to, subject, body, trans.app.config)
            return True
        except Exception:
            log.exception('Unable to send the activation email.')
            return False

    def __prepare_activation_link(self, trans, email):
        """
        Prepare the account activation link for the user.
        """
        activation_token = self.__get_activation_token(trans, email)
        activation_link = url_for(controller='user', action='activate', activation_token=activation_token, email=email, qualified=True)
        return activation_link

    def __get_activation_token(self, trans, email):
        """
        Check for the activation token. Create new activation token and store it in the database if no token found.
        """
        user = trans.sa_session.query(trans.app.model.User).filter(trans.app.model.User.table.c.email == email).first()
        activation_token = user.activation_token
        if activation_token is None:
            activation_token = hash_util.new_secure_hash(str(random.getrandbits(256)))
            user.activation_token = activation_token
            trans.sa_session.add(user)
            trans.sa_session.flush()
        return activation_token


def _get_allow_register(d):
    s = d.get('allow-register', True)
    lower_s = str(s).lower()
    if lower_s == 'challenge':
        return lower_s
    else:
        return string_as_bool(s)
