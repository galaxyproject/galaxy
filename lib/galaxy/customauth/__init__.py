"""
Contains implementations of custom auth logic.
"""

import traceback
import xml.etree.ElementTree
from yapsy.PluginManager import PluginManager

from galaxy.security.validate_user_input import validate_publicname

import logging
logging.basicConfig(level=logging.DEBUG)

# <customauth>
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
# </customauth>

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
    """Checks the email/password using custom auth providers and if matches
    returns the 'auto-register' option for that provider.
    """
    for provider, options in activeAuthProviderGenerator(email, password, configfile, debug):
        if provider is None:
            if debug:
                print "Unable to find module: %s" % options
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
                    print "Email: %s, auto-register with username: %s" % (email, autousername)
                return (_getBool(options, 'auto-register', False), autousername)
            elif authresult is None:
                print "Email: %s, stopping due to failed non-continue" % (email)
                break # end authentication (skip rest)
    return (False, '')

def check_password(user, password, configfile, debug=False):
    """Checks the email/password using custom auth providers."""
    if debug:
        print ("Checking with CustomAuth")

    for provider, options in activeAuthProviderGenerator(user.email, password, configfile, debug):
        if provider is None:
            if debug:
                print "Unable to find module: %s" % options
        else:
            authresult = provider.authenticateUser(user, password, options, debug)
            if authresult is True:
                return True # accept user
            elif authresult is None:
                break # end authentication (skip rest)
    return False

def check_change_password(user, current_password, configfile, debug=False):
    """Checks that provider allows password changes and current_password
    matches.
    """
    if debug:
        print ("Checking password change with CustomAuth")
    for provider, options in activeAuthProviderGenerator(user.email, current_password, configfile, debug):
        if provider is None:
            if debug:
                print "Unable to find module: %s" % options
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
    """Yields CustomAuthProvider instances for the provided configfile that
    match the filters.
    """
    try:
        # load the yapsy plugins
        manager = PluginManager()
        manager.setPluginPlaces(["lib/galaxy/customauth/providers"])
        manager.collectPlugins()

        if debug:
            print ("Plugins found:")
            for plugin in manager.getAllPlugins():
                print ("- %s" % (plugin.path))

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
                    print ("Filter: %s == %s" % (filterstr, eval(filterstr, {"__builtins__":None},{'str':str})))
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
            print ('CustomAuth: Exception:\n%s' % (traceback.format_exc(),))

def _getBool(d, k, o):
    if k in d:
        if d[k] in ('True', 'true', 'Yes', 'yes', '1', 1, True):
            return True
        else:
            return False
    else:
        return o

def _getTriState(d, k, o):
    if k in d:
        if d[k] in ('True', 'true', 'Yes', 'yes', '1', 1, True):
            return True
        elif d[k] in ('False', 'false', 'No', 'no', '0', 0, False):
            return False
        else:
            return None
    else:
        return o

def _getChildElement(parent, childname):
    try:
        return parent.iter(childname).next()
    except StopIteration:
        return None
