"""
Contains implementations of the authentication logic.
"""

import logging

from galaxy.auth.util import get_authenticators, parse_auth_results
from galaxy.exceptions import Conflict
from galaxy.util import string_as_bool

log = logging.getLogger(__name__)


class AuthManager(object):

    def __init__(self, app):
        self.__app = app
        self.redact_username_in_logs = app.config.redact_username_in_logs
        self.authenticators = get_authenticators(app.config.auth_config_file)

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

    def __register(self, trans, cntrller, subscribe_checked, no_redirect=False, **kwd):
        email = util.restore_text(kwd.get('email', ''))
        password = kwd.get('password', '')
        username = util.restore_text(kwd.get('username', ''))
        message = escape(kwd.get('message', ''))
        status = kwd.get('status', 'done')
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        user = self.user_manager.create(email=email, username=username, password=password)
        error = ''
        success = True
        if trans.webapp.name == 'galaxy':
            if subscribe_checked:
                # subscribe user to email list
                if trans.app.config.smtp_server is None:
                    error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed because mail is not configured for this Galaxy instance. <br>Please contact your local Galaxy administrator."
                else:
                    body = 'Join Mailing list.\n'
                    to = trans.app.config.mailing_join_addr
                    frm = email
                    subject = 'Join Mailing List'
                    try:
                        util.send_mail(frm, to, subject, body, trans.app.config)
                    except Exception:
                        log.exception('Subscribing to the mailing list has failed.')
                        error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed."

            if not error and not is_admin:
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                trans.handle_user_login(user)
                trans.log_event("User created a new account")
                trans.log_event("User logged in")
            elif not error and not no_redirect:
                trans.response.send_redirect(web.url_for(controller='admin',
                                                         action='users',
                                                         message='Created new user account (%s)' % user.email,
                                                         status=status))
        if error:
            message = error
            status = 'error'
            success = False
        else:
            if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                is_activation_sent = self.send_verification_email(trans, email, username)
                if is_activation_sent:
                    message = 'Now logged in as %s.<br>Verification email has been sent to your email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
                    success = True
                else:
                    message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                    if trans.app.config.error_email_to is not None:
                        message += ' Contact: %s' % trans.app.config.error_email_to
                    success = False
            else:  # User activation is OFF, proceed without sending the activation email.
                message = 'Now logged in as %s.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
                success = True
        return (message, status, user, success)


def _get_allow_register(d):
    s = d.get('allow-register', True)
    lower_s = str(s).lower()
    if lower_s == 'challenge':
        return lower_s
    else:
        return string_as_bool(s)
