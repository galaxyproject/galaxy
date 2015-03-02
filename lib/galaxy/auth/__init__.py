"""
Contains implementations of the authentication logic.
"""

import traceback
import xml.etree.ElementTree
from yapsy.PluginManager import PluginManager

from galaxy.security.validate_user_input import validate_publicname

from galaxy.util import (
    string_as_bool,
    string_as_bool_or_none,
)

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

def check_registration_allowed(email, password, configfile, debug=False):
    """Checks if the provided email is allowed to register."""
    message = ''
    status = 'done'
    for provider, options in activeAuthProviderGenerator(email, password, configfile, debug):
        allowreg = _getTriState(options, 'allow-register', True)
        if allowreg is None: # i.e. challenge
            authresult, msg = provider.authenticate(email, password, options, debug)
            if authresult == True:
                break
            if authresult is None:
                message = 'Invalid email address or password'
                status = 'error'
                break
        elif allowreg is True:
            break
        elif allowreg is False:
            message = 'Account registration not required for your account.  Please simply login.'
            status = 'error'
            break
    return message, status

def check_auto_registration(trans, email, password, configfile, debug=False):
    """
    Checks the email/password using auth providers in order. If a match is
    found, returns the 'auto-register' option for that provider.
    """
    for provider, options in activeAuthProviderGenerator(email, password, configfile, debug):
        if provider is None:
            if debug:
                log.debug( "Unable to find module: %s" % options )
        else:
            authresult, autousername = provider.authenticate(email, password, options, debug)
            autousername = str(autousername).lower()
            if authresult is True:
                # make username unique
                if validate_publicname( trans, autousername ) != '':
                    i = 1
                    while i <= 10: # stop after 10 tries
                        if validate_publicname( trans, "%s-%i" % (autousername, i) ) == '':
                            autousername = "%s-%i" % (autousername, i)
                            break
                        i += 1
                    else:
                        break # end for loop if we can't make a unique username
                if debug:
                    log.debug( "Email: %s, auto-register with username: %s" % (email, autousername) )
                return (_getBool(options, 'auto-register', False), autousername)
            elif authresult is None:
                log.debug( "Email: %s, stopping due to failed non-continue" % (email) )
                break # end authentication (skip rest)
    return (False, '')

def check_password(user, password, configfile, debug=False):
    """Checks the email/password using auth providers."""
    for provider, options in activeAuthProviderGenerator(user.email, password, configfile, debug):
        if provider is None:
            if debug:
                log.debug( "Unable to find module: %s" % options )
        else:
            authresult = provider.authenticateUser(user, password, options, debug)
            if authresult is True:
                return True # accept user
            elif authresult is None:
                break # end authentication (skip rest)
    return False

def check_change_password(user, current_password, configfile, debug=False):
    """Checks that auth provider allows password changes and current_password
    matches.
    """
    for provider, options in activeAuthProviderGenerator(user.email, current_password, configfile, debug):
        if provider is None:
            if debug:
                log.debug( "Unable to find module: %s" % options )
        else:
            if _getBool(options, "allow-password-change", False):
                authresult = provider.authenticateUser(user, current_password, options, debug)
                if authresult is True:
                    return (True, '') # accept user
                elif authresult is None:
                    break # end authentication (skip rest)
            else:
                return (False, 'Password change not supported')
    return (False, 'Invalid current password')

def activeAuthProviderGenerator(username, password, configfile, debug):
    """Yields AuthProvider instances for the provided configfile that match the
    filters.
    """
    try:
        # load the yapsy plugins
        manager = PluginManager()
        manager.setPluginPlaces(["lib/galaxy/auth/providers"])
        manager.collectPlugins()

        if debug:
            log.debug( ("Plugins found:") )
            for plugin in manager.getAllPlugins():
                log.debug( ("- %s" % (plugin.path)) )

        # parse XML
        ct = xml.etree.ElementTree.parse(configfile)
        confroot = ct.getroot()

        # process authenticators
        for authelem in confroot.getchildren():
            typeelem = authelem.iter('type').next()

            # check filterelem
            filterelem = _getChildElement(authelem, 'filter')
            if filterelem is not None:
                filterstr = str(filterelem.text).format(username=username, password=password)
                if debug:
                    log.debug( ("Filter: %s == %s" % (filterstr, eval(filterstr, {"__builtins__":None},{'str':str}))) )
                if not eval(filterstr, {"__builtins__":None},{'str':str}):
                    continue # skip to next

            # extract options
            optionselem = _getChildElement(authelem, 'options')
            options = {}
            if optionselem is not None:
                for opt in optionselem:
                    options[opt.tag] = opt.text

            # get the instance
            plugin = manager.getPluginByName(typeelem.text)
            yield (plugin.plugin_object, options)  # excepts if type is spelled incorrectly
    except GeneratorExit:
        return
    except:
        if debug:
            log.debug( ('Auth: Exception:\n%s' % (traceback.format_exc(),)) )

def _getBool(d, k, o):
    if k in d:
        return string_as_bool(d[k])
    else:
        return o

def _getTriState(d, k, o):
    if k in d:
        return string_as_bool_or_none(d[k])
    else:
        return o

def _getChildElement(parent, childname):
    try:
        return parent.iter(childname).next()
    except StopIteration:
        return None
