"""
Created on 16/07/2014

@author: Andrew Robinson
"""

import galaxy.auth.base

class LocalDB(galaxy.auth.base.AuthProvider):
    """Authenticate users against the local Galaxy database (as per usual)."""

    def authenticate(self, username, password, options, debug=False):
        """
        See abstract method documentation.
        """
        return (False, '') # it can never auto-create based of localdb (chicken-egg)

    def authenticateUser(self, user, password, options, debug=False):
        """
        See abstract method documentation.
        """
        user_ok = user.check_password(password)
        if debug:
            print ("User: %s, LOCALDB: %s" % (user.email, user_ok))
        return user_ok
