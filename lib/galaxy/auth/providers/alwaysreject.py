"""
Created on 16/07/2014

@author: Andrew Robinson
"""

from ..providers import AuthProvider

import logging
log = logging.getLogger(__name__)


class AlwaysReject(AuthProvider):
    """A simple authenticator that just accepts users (does not care about their
    password).
    """
    plugin_type = 'alwaysreject'

    def authenticate(self, username, password, options, debug=False):
        """
        See abstract method documentation.
        """
        return (None, '')

    def authenticate_user(self, user, password, options, debug=False):
        """
        See abstract method documentation.
        """
        if debug:
            log.debug("User: %s, ALWAYSREJECT: None" % (user.email))
        return None


__all__ = ['AlwaysReject']
