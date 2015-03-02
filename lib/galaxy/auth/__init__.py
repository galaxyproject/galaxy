"""
Contains implementations of the authentication logic.
"""

from collections import namedtuple
import traceback
import xml.etree.ElementTree

from galaxy.security.validate_user_input import validate_publicname

from galaxy.util import (
    string_as_bool,
    string_as_bool_or_none,
)

from galaxy.util import plugin_config


import logging
log = logging.getLogger(__name__)

# <auth>
#     <authenticator>
#         <type>activedirectory</type>
#         <filter>'[username]'.endswith('@students.latrobe.edu.au')</filter>
#         <options>
#             <auto-register>True</auto-register>
#             <server>ldap://STUDENTS.ltu.edu.au</server>
#             [<search-filter>(&amp;(objectClass=user)(mail={username}))</search-filter>
#             <search-base>dc=STUDENTS,dc=ltu,dc=edu,dc=au</search-base>
#             <search-user>jsmith</search-user>
#             <search-password>mysecret</search-password>
#             <search-fields>sAMAccountName</search-fields>]
#             <bind-user>{sAMAccountName}@STUDENTS.ltu.edu.au</bind-user>
#             <bind-password>{password}</bind-password>
#             <auto-register-username>{sAMAccountName}</auto-register-username>
#         </options>
#     </authenticator>
#     ...
# </auth>


class AuthManager(object):

    def __init__(self, app):
        self.__app = app
        import galaxy.auth.providers
        self.__plugins_dict = plugin_config.plugins_dict( galaxy.auth.providers, 'plugin_type' )
        auth_config_file = app.config.auth_config_file
        self.__init_authenticators(auth_config_file)
        self.debug = getattr(app.config, 'auth_debug', False)

    def __init_authenticators(self, auth_config_file):
        # parse XML
        ct = xml.etree.ElementTree.parse(auth_config_file)
        conf_root = ct.getroot()

        authenticators = []
        # process authenticators
        for auth_elem in conf_root.getchildren():
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

    def check_registration_allowed(self, email, password):
        """Checks if the provided email is allowed to register."""
        message = ''
        status = 'done'
        for provider, options in self.active_authenticators(email, password):
            allow_reg = _get_tri_state(options, 'allow-register', True)
            if allow_reg is None:  # i.e. challenge
                auth_result, msg = provider.authenticate(email, password, options)
                if auth_result is True:
                    break
                if auth_result is None:
                    message = 'Invalid email address or password'
                    status = 'error'
                    break
            elif allow_reg is True:
                break
            elif allow_reg is False:
                message = 'Account registration not required for your account.  Please simply login.'
                status = 'error'
                break
        return message, status

    def check_auto_registration(self, trans, email, password, debug=False):
        """
        Checks the email/password using auth providers in order. If a match is
        found, returns the 'auto-register' option for that provider.
        """
        for provider, options in self.active_authenticators(email, password, debug):
            if provider is None:
                if debug:
                    log.debug( "Unable to find module: %s" % options )
            else:
                auth_result, auto_username = provider.authenticate(email, password, options, debug)
                auto_username = str(auto_username).lower()
                if auth_result is True:
                    # make username unique
                    if validate_publicname( trans, auto_username ) != '':
                        i = 1
                        while i <= 10:  # stop after 10 tries
                            if validate_publicname( trans, "%s-%i" % (auto_username, i) ) == '':
                                auto_username = "%s-%i" % (auto_username, i)
                                break
                            i += 1
                        else:
                            break  # end for loop if we can't make a unique username
                    if debug:
                        log.debug( "Email: %s, auto-register with username: %s" % (email, auto_username) )
                    return (_get_bool(options, 'auto-register', False), auto_username)
                elif auth_result is None:
                    log.debug( "Email: %s, stopping due to failed non-continue" % (email) )
                    break  # end authentication (skip rest)
        return (False, '')

    def check_password(self, user, password):
        """Checks the email/password using auth providers."""
        for provider, options in self.active_authenticators(user.email, password):
            if provider is None:
                if self.debug:
                    log.debug( "Unable to find module: %s" % options )
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
        for provider, options in self.active_authenticators(user.email, current_password):
            if provider is None:
                if self.debug:
                    log.debug( "Unable to find module: %s" % options )
            else:
                if _get_bool(options, "allow-password-change", False):
                    auth_result = provider.authenticate_user(user, current_password, options)
                    if auth_result is True:
                        return (True, '')  # accept user
                    elif auth_result is None:
                        break  # end authentication (skip rest)
                else:
                    return (False, 'Password change not supported')
        return (False, 'Invalid current password')

    def active_authenticators(self, username, password):
        """Yields AuthProvider instances for the provided configfile that match the
        filters.
        """
        try:
            for authenticator in self.authenticators:
                filter_template = authenticator.filter_template
                if filter_template:
                    filter_str = filter_template.format(username=username, password=password)
                    passed_filter = eval(filter_str, {"__builtins__": None}, {'str': str})
                    if not passed_filter:
                        continue  # skip to next
                yield authenticator.plugin, authenticator.options
        except Exception:
            if self.debug:
                log.debug( ('Auth: Exception:\n%s' % (traceback.format_exc(),)) )
            raise

Authenticator = namedtuple('Authenticator', ['plugin', 'filter_template', 'options'])


def _get_bool(d, k, o):
    if k in d:
        return string_as_bool(d[k])
    else:
        return o


def _get_tri_state(d, k, o):
    if k in d:
        return string_as_bool_or_none(d[k])
    else:
        return o
