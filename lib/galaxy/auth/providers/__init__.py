"""
Created on 15/07/2014

@author: Andrew Robinson
"""
import abc


class AuthProvider(metaclass=abc.ABCMeta):
    """A base class for all Auth Providers."""

    @abc.abstractproperty
    def plugin_type(self):
        """Short string providing labelling this plugin"""

    @abc.abstractmethod
    def authenticate(self, email, username, password, options):
        """
        Check that the user credentials are correct.

        NOTE: Used within auto-registration to check it is ok to register this
        user.

        :param  email: the user's email address
        :type   email: str
        :param  username: the user's username
        :type   username: str
        :param  password: the plain text password they typed
        :type   password: str
        :param  options: options provided in auth_config_file
        :type   options: dict
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers.  str, str are the email and
            username to register with if accepting. The optional dict may
            contain other attributes, e.g. roles to assign when autoregistering.
        :rtype:     (bool, str, str) or (bool, str, str, dict)
        """

    @abc.abstractmethod
    def authenticate_user(self, user, password, options):
        """
        Same as authenticate() method, except an User object is provided instead
        of a username.

        NOTE: used on normal login to check authentication and update user
        details if required.

        :param  user: the user to authenticate
        :type   user: galaxy.model.User
        :param  password: the plain text password they typed
        :type   password: str
        :param  options: options provided in auth_config_file
        :type   options: dict
        :returns:   True: accept user, False: reject user and None: reject user
            and don't try any other providers
        :rtype:     bool
        """
