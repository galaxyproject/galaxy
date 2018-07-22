"""
Contains implementations of the authentication logic.
"""
import logging
import random
import socket
from datetime import datetime

from markupsafe import escape

from galaxy.auth.util import get_authenticators, parse_auth_results
from galaxy.exceptions import Conflict
from galaxy.managers import users
from galaxy.util import hash_util, restore_text, send_mail, string_as_bool
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
                        return (True, '')  # accept user
                    else:
                        return (False, 'Password change not supported.')
                elif auth_result is None:
                    break  # end authentication (skip rest)
        return (False, 'Invalid current password.')

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

    def register(self, trans, email=None, username=None, password=None, subscribe_checked=False, **kwd):
        """Registers a new user."""
        email = restore_text(email)
        username = restore_text(username)
        status = None
        message = None
        is_admin = trans.user_is_admin()
        user = self.user_manager.create(email=email, username=username, password=password)
        if subscribe_checked:
            # subscribe user to email list
            if trans.app.config.smtp_server is None:
                status = "error"
                message = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed because mail is not configured for this Galaxy instance. <br>Please contact your local Galaxy administrator."
            else:
                body = 'Join Mailing list.\n'
                to = trans.app.config.mailing_join_addr
                frm = email
                subject = 'Join Mailing List'
                try:
                    send_mail(frm, to, subject, body, trans.app.config)
                except Exception:
                    log.exception('Subscribing to the mailing list has failed.')
                    status = "warning"
                    message = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed."
        if status != "error":
            if not is_admin:
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                trans.handle_user_login(user)
                trans.log_event("User created a new account")
                trans.log_event("User logged in")
            if trans.app.config.user_activation_on:
                is_activation_sent = self.send_verification_email(trans, email, username)
                if is_activation_sent:
                    message = 'Now logged in as %s.<br>Verification email has been sent to your email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
                else:
                    status = "error"
                    message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                    if trans.app.config.error_email_to is not None:
                        message += ' Contact: %s' % trans.app.config.error_email_to
        else:
            # User activation is OFF, proceed without sending the activation email.
            message = 'Now logged in as %s.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
        return message, status, user, status is None

    def send_verification_email(self, trans, email, username):
        """
        Send the verification email containing the activation link to the user's email.
        """
        if username is None:
            username = trans.user.username
        activation_link = self.prepare_activation_link(trans, escape(email))

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

    def prepare_activation_link(self, trans, email):
        """
        Prepare the account activation link for the user.
        """
        activation_token = self.get_activation_token(trans, email)
        activation_link = url_for(controller='user', action='activate', activation_token=activation_token, email=email, qualified=True)
        return activation_link

    def get_activation_token(self, trans, email):
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
