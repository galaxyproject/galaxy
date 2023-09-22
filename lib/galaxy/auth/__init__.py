"""
Contains implementations of the authentication logic.
"""
import logging

from galaxy.auth.util import (
    get_authenticators,
    parse_auth_results,
)
from galaxy.exceptions import Conflict
from galaxy.util import string_as_bool

log = logging.getLogger(__name__)


class AuthManager:
    def __init__(self, config):
        self.redact_username_in_logs = config.redact_username_in_logs
        self.authenticators = get_authenticators(config.auth_config_file, config.is_set("auth_config_file"))

    def check_registration_allowed(self, email, username, password, request):
        """Checks if the provided email/username is allowed to register."""
        message = ""
        status = "done"
        for provider, options in self.active_authenticators(email, username, password):
            allow_reg = _get_allow_register(options)
            if allow_reg == "challenge":
                auth_results = provider.authenticate(email, username, password, options, request)
                if auth_results[0] is True:
                    break
                if auth_results[0] is None:
                    message = "Invalid email address/username or password."
                    status = "error"
                    break
            elif allow_reg is True:
                break
            elif allow_reg is False:
                message = "Account registration not required for your account.  Please simply login."
                status = "error"
                break
        return message, status

    def check_auto_registration(self, trans, login, password, no_password_check=False):
        """
        Checks the username/email & password using auth providers in order.
        If a match is found, returns the 'auto-register' option for that provider.
        """
        if "@" in login:
            email = login
            username = None
        else:
            email = None
            username = login
        auth_return = {"auto_reg": False, "email": "", "username": ""}
        for provider, options in self.active_authenticators(email, username, password):
            if provider is None:
                log.debug(f"Unable to find module: {options}")
            else:
                options["no_password_check"] = no_password_check
                auth_results = provider.authenticate(email, username, password, options, trans.request)
                if auth_results[0] is True:
                    try:
                        auth_return = parse_auth_results(trans, auth_results, options)
                    except Conflict as conflict:
                        log.exception(conflict)
                        raise
                    return auth_return
                elif auth_results[0] is None:
                    log.debug("Login: '%s', stopping due to failed non-continue", login)
                    break  # end authentication (skip rest)
        return auth_return

    def check_password(self, user, password, request):
        """Checks the username/email and password using auth providers."""
        for provider, options in self.active_authenticators(user.email, user.username, password):
            if provider is None:
                log.debug(f"Unable to find module: {options}")
            else:
                auth_result = provider.authenticate_user(user, password, options, request)
                if auth_result is True:
                    return True  # accept user
                elif auth_result is None:
                    break  # end authentication (skip rest)
        return False

    def check_change_password(self, user, current_password, request):
        """Checks that auth provider allows password changes and current_password
        matches.
        """
        for provider, options in self.active_authenticators(user.email, user.username, current_password):
            if provider is None:
                log.debug(f"Unable to find module: {options}")
            else:
                auth_result = provider.authenticate_user(user, current_password, options, request)
                if auth_result is True:
                    if string_as_bool(options.get("allow-password-change", False)):
                        return
                    else:
                        return "Password change not supported."
                elif auth_result is None:
                    break  # end authentication (skip rest)
        return "Invalid current password."

    def active_authenticators(self, email, username, password):
        """Yields AuthProvider instances for the provided configfile that match the
        filters.
        """
        try:
            for authenticator in self.authenticators:
                filter_template = authenticator.filter_template
                if filter_template:
                    filter_str = filter_template.format(email=email, username=username, password=password)
                    passed_filter = eval(filter_str, {"__builtins__": None}, {"str": str})
                    if not passed_filter:
                        continue  # skip to next
                options = authenticator.options
                options["redact_username_in_logs"] = self.redact_username_in_logs
                yield authenticator.plugin, options
        except Exception:
            log.exception("Active Authenticators Failure")
            raise


def _get_allow_register(d):
    s = d.get("allow-register", True)
    lower_s = str(s).lower()
    if lower_s == "challenge":
        return lower_s
    else:
        return string_as_bool(s)
