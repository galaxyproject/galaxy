"""
Created on 15/07/2014

@author: Andrew Robinson
"""

import traceback
from ..providers import AuthProvider


def _getsubs(d, k, vars, default=''):
    if k in d:
        return str(d[k]).format(**vars)
    return str(default).format(**vars)


class ActiveDirectory(AuthProvider):
    """
    Attempts to authenticate users against an Active Directory server.

    If options include search-fields then it will attempt to search the AD for
    those fields first.  After that it will bind to the AD with the username
    (formatted as specified).
    """
    @property
    def plugin_type(self):
        return 'activedirectory'

    def authenticate(self, username, password, options, debug=False):
        """
        See abstract method documentation.
        """
        if debug:
            print ("Username: %s" % username)
            print ("Options: %s" % options)

        failuremode = False # reject but continue
        if options.get('continue-on-failure', 'False') == 'False':
            failuremode = None # reject and do not continue

        try:
            import ldap
        except:
            if debug:
                print ("User: %s, ACTIVEDIRECTORY: False (no ldap)" % (username))
            return (failuremode, '')

        ## do AD search (if required) ##
        vars = {'username': username, 'password': password}
        if 'search-fields' in options:
            try:
                # setup connection
                ldap.set_option(ldap.OPT_REFERRALS, 0)
                l = ldap.initialize(_getsubs(options, 'server', vars))
                l.protocol_version = 3
                l.simple_bind_s(_getsubs(options, 'search-user', vars), _getsubs(options, 'search-password', vars))
                scope = ldap.SCOPE_SUBTREE

                # setup search
                attributes = map(lambda s: s.strip().format(**vars), options['search-fields'].split(','))
                result = l.search(_getsubs(options, 'search-base', vars), scope, _getsubs(options, 'search-filter', vars), attributes)

                # parse results
                _, suser = l.result(result, 60)
                _, attrs = suser[0]
                if debug:
                    print ("AD Search attributes: %s" % attrs)
                if hasattr(attrs, 'has_key'):
                    for attr in attributes:
                        if attrs.has_key(attr):
                            vars[attr] = str(attrs[attr][0])
                        else:
                            vars[attr] = ""
            except Exception:
                if debug:
                    print('User: %s, ACTIVEDIRECTORY: Search Exception:\n%s' % (username, traceback.format_exc(),))
                return (failuremode, '')
        # end search

        # bind as user to check their credentials
        try:
            # setup connection
            ldap.set_option(ldap.OPT_REFERRALS, 0)
            l = ldap.initialize(_getsubs(options, 'server', vars))
            l.protocol_version = 3
            l.simple_bind_s(_getsubs(options, 'bind-user', vars), _getsubs(options, 'bind-password', vars))
        except Exception:
            if debug:
                print('User: %s, ACTIVEDIRECTORY: Authenticate Exception:\n%s' % (username, traceback.format_exc()))
            return (failuremode, '')

        if debug:
            print "User: %s, ACTIVEDIRECTORY: True" % (username)
        return (True, _getsubs(options, 'auto-register-username', vars))

    def authenticateUser(self, user, password, options, debug=False):
        """
        See abstract method documentation.
        """
        return self.authenticate(user.email, password, options, debug)[0]


__all__ = ['ActiveDirectory']
