"""
Created on 16/07/2014

@author: Andrew Robinson
"""
import logging

from ..providers import AuthProvider

log = logging.getLogger(__name__)


class AlwaysReject(AuthProvider):
    """A simple authenticator that just accepts users (does not care about their
    password).
    """
    plugin_type = 'alwaysreject'

    def authenticate(self, email, username, password, options):
        """
        See abstract method documentation.
        """
        return (None, '', '')

    def authenticate_user(self, user, password, options):
        """
        See abstract method documentation.
        """
        log.debug("User: %s, ALWAYSREJECT: None" % (user.id if options['redact_username_in_logs'] else user.email))
        return None


__all__ = ('AlwaysReject', )
