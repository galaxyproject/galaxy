"""
Created on 15/07/2014

@author: Andrew Robinson
"""

import abc


class AuthProvider(object):
    """A base class for all Auth Providers."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def plugin_type(self):
        """ Short string providing labelling this plugin """

    @abc.abstractmethod
    def authenticate(self, login, password, options):
        """
        Check that the username and password are correct.

        NOTE: Used within auto-registration to check it is ok to register this
        user.

        :param  login: the users email address
        :type   login: str
        :param  password: the plain text password they typed
        :type   password: str
        :param  options: options provided in auth_config_file
        :type   options: dict
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers.  str, str is the email and
            username to register with if accepting
        :rtype:     (bool, str, str)
        """

    @abc.abstractmethod
    def authenticate_user(self, user, password, options):
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
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers
        :rtype:     bool
        """
