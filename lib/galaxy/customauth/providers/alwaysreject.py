"""
Created on 16/07/2014

@author: Andrew Robinson
"""

import galaxy.customauth.base

class AlwaysReject(galaxy.customauth.base.CustomAuthProvider):
    """A simple authenticator that just accepts users (does not care about their
    password).
    """

    def authenticate(self, username, password, options, debug=False):
        """
        See abstract method documentation.
        """
        return (None, '')

    def authenticateUser(self, user, password, options, debug=False):
        """
        See abstract method documentation.
        """
        if debug:
            print ("User: %s, ALWAYSREJECT: None" % (user.email))
        return None
