"""
Contains implementations of the authentication logic.
"""

import logging
import xml.etree.ElementTree
from collections import namedtuple

from galaxy.security.validate_user_input import validate_publicname
from galaxy.util import plugin_config, string_as_bool

log = logging.getLogger(__name__)


class AuthManager(object):

    def __init__(self, app):
        self.__app = app
        import galaxy.auth.providers
        self.__plugins_dict = plugin_config.plugins_dict(galaxy.auth.providers, 'plugin_type')
        auth_config_file = app.config.auth_config_file
        # parse XML
        ct = xml.etree.ElementTree.parse(auth_config_file)
        conf_root = ct.getroot()

        authenticators = []
        # process authenticators
        for auth_elem in conf_root:
            type_elem = auth_elem.find('type')
            plugin = self.__plugins_dict.get(type_elem.text)()

            # check filterelem
            filter_elem = auth_elem.find('filter')
            if filter_elem is not None:
                filter_template = str(filter_elem.text)
            else:
                filter_template = None

            # extract options
            options_elem = auth_elem.find('options')
            options = {}
            if options_elem is not None:
                for opt in options_elem:
                    options[opt.tag] = opt.text
            authenticator = Authenticator(
                plugin=plugin,
                filter_template=filter_template,
                options=options,
            )
            authenticators.append(authenticator)
        self.authenticators = authenticators

    def check_registration_allowed(self, email, username, password):
        """Checks if the provided email/username is allowed to register."""
        message = ''
        status = 'done'
        for provider, options in self.active_authenticators(email, username, password):
            allow_reg = _get_allow_register(options)
            if allow_reg == 'challenge':
                auth_result, msg = provider.authenticate(email, username, password, options)
                if auth_result is True:
                    break
                if auth_result is None:
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

    def check_auto_registration(self, trans, login, password):
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
                auth_results = provider.authenticate(email, username, password, options)
                auth_result, auto_email, auto_username = auth_results[:3]
                auto_email = str(auto_email).lower()
                auto_username = str(auto_username).lower()
                if auth_result is True:
                    # make username unique
                    if validate_publicname(trans, auto_username) != '':
                        i = 1
                        while i <= 10:  # stop after 10 tries
                            if validate_publicname(trans, "%s-%i" % (auto_username, i)) == '':
                                auto_username = "%s-%i" % (auto_username, i)
                                break
                            i += 1
                        else:
                            break  # end for loop if we can't make a unique username
                    log.debug("Email: %s, auto-register with username: %s" % (auto_email, auto_username))
                    auth_return["auto_reg"] = string_as_bool(options.get('auto-register', False))
                    auth_return["email"] = auto_email
                    auth_return["username"] = auto_username
                    if len(auth_results) == 4:
                        auth_return["attributes"] = auth_results[3]
                    return auth_return
                elif auth_result is None:
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
                yield authenticator.plugin, authenticator.options
        except Exception:
            log.exception("Active Authenticators Failure")
            raise


Authenticator = namedtuple('Authenticator', ['plugin', 'filter_template', 'options'])


def _get_allow_register(d):
    s = d.get('allow-register', True)
    lower_s = str(s).lower()
    if lower_s == 'challenge':
        return lower_s
    else:
        return string_as_bool(s)
