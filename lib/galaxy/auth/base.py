"""
Created on 15/07/2014

@author: Andrew Robinson
"""

from yapsy.IPlugin import IPlugin

class AuthProvider(IPlugin):
    """A base class for all Auth Providers."""

    def authenticate(self, username, password, options, debug=False):
        """
        Check that the username and password are correct.

        NOTE: Used within auto-registration to check it is ok to register this
        user.

        :param  username: the users email address
        :type   username: str
        :param  password: the plain text password they typed
        :type   password: str
        :param  options: options provided in auth_config_file
        :type   options: dict
        :param  debug: whether to print debugging info (defaults to False)
        :type   debug: bool
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers.  str is the username to register
            with if accepting
        :rtype:     (bool, str)
        """
        raise NotImplementedError()

    def authenticateUser(self, user, password, options, debug=False):
        """
        Same as authenticate() method, except an User object is provided instead
        of a username.

        NOTE: used on normal login to check authentication and update user
        details if required.

        :param  username: the users email address
        :type   username: str
        :param  password: the plain text password they typed
        :type   password: str
        :param  options: options provided in auth_config_file
        :type   options: dict
        :param  debug: whether to print debugging info (defaults to False)
        :type   debug: bool
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers
        :rtype:     bool
        """
        raise NotImplementedError()
