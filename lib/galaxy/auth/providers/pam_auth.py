"""
Created on 13/07/2015

Author Peter van Heusden (pvh@sanbi.ac.za)
"""
import logging
import shlex

from galaxy.util import (
    commands,
    string_as_bool,
)
from ..providers import AuthProvider

log = logging.getLogger(__name__)

"""
This module provides an AuthProvider for PAM (pluggable authentication module) authentication.
PAM is the Pluggable Authentication Module system (http://www.linux-pam.org/)
It relies on python-pam (https://pypi.python.org/pypi/python-pam)

Configuration is via config/auth_conf.xml and the following options are supported:
  - auto-register: True/False: automatically register an account for an unknown user. Default: False
  - maildomain: string: all valid users fall within the specified mail domain. Default: None
  - login-use-email: True/False: Parse the email address to get login details. Default: False
  - login-use-username: True/False: Use the username argument for login details. Default: False
                                    Technical note: when a user is not found in the database,
                                    their username is the user part of a user@host email
                                    address. After user creation, however, the username is
                                    the user's public name.
  - pam-service: string: The service name to use for PAM authentication. Default: galaxy
  - use-external-helper: True/False: Run an external helper script as root with sudo to do
                                     authentication. If False authentication is done
                                     by the module directly. Default: False
                                     Technical note: some PAM modules (e.g. pam_unix.so)
                                     require to be run as root to authenticate users.
  - authentication-helper-script: string: Absolute path to helper script to run for authentication. Default: None
                                          There needs to be a config (in /etc/sudoers or /etc/sudoers.d)
                                          that allows the galaxy user to run this as root with no password check
                                          For example:
galaxy	ALL=(root) NOPASSWD: /opt/galaxy/scripts/auth/pam_auth_helper.py


Configuration example (for internal authentication, use email for user details):
<authenticator>
  <type>PAM</type>
  <options>
          <auto-register>True</auto-register>
          <maildomain>example.com</maildomain>
          <login-use-email>True</login-use-email>
          <pam-service>ssh</pam-service>
  </options>
</authenticator>
"""


class PAM(AuthProvider):

    plugin_type = "PAM"

    def authenticate(self, email, username, password, options):
        pam_username = None
        auto_register_username = None
        auto_register_email = None
        force_fail = False
        if not options["redact_username_in_logs"]:
            log.debug(
                f"use username: {options.get('login-use-username')} use email {options.get('login-use-email', False)} email {email} username {username}"
            )
        # check email based login first because if email exists in Galaxy DB
        # we will be given the "public name" as username
        if string_as_bool(options.get("login-use-email", False)) and email is not None:
            if "@" in email:
                (email_user, email_domain) = email.split("@")
                pam_username = email_user
                if email_domain == options.get("maildomain", None):
                    auto_register_email = email
                    if username is not None:
                        auto_register_username = username
                    else:
                        auto_register_username = email_user
                else:
                    log.debug("PAM authenticate: warning: email does not match configured PAM maildomain")
                    # no need to fail: if auto-register is not enabled, this
                    # might still be a valid user
            else:
                log.debug("PAM authenticate: email must be used to login, but no valid email found")
                force_fail = True
        elif string_as_bool(options.get("login-use-username", False)):
            # if we get here via authenticate_user then
            # user will be "public name" and
            # email address will be as per registered user
            if username is not None:
                pam_username = username
                if email is not None:
                    auto_register_email = email
                elif options.get("maildomain", None) is not None:
                    # we can register a user with this username and mail domain
                    # if auto registration is enabled
                    auto_register_email = f"{username}@{options['maildomain']}"
                auto_register_username = username
            else:
                log.debug("PAM authenticate: username login selected but no username provided")
                force_fail = True
        else:
            log.debug("PAM authenticate: could not find username for PAM")
            force_fail = True

        if force_fail:
            return None, "", ""

        pam_service = options.get("pam-service", "galaxy")
        use_helper = string_as_bool(options.get("use-external-helper", False))
        log.debug(f"PAM auth: will use external helper: {use_helper}")
        authenticated = False
        if use_helper:
            authentication_helper = options.get("authentication-helper-script", "/bin/false").strip()
            log.debug(f"PAM auth: external helper script: {authentication_helper}")
            if not authentication_helper.startswith("/"):
                # don't accept relative path
                authenticated = False
            else:
                auth_cmd = shlex.split(f"/usr/bin/sudo -n {authentication_helper}")
                log.debug(f"PAM auth: external helper cmd: {auth_cmd}")
                message = f"{pam_service}\n{pam_username}\n{password}\n"
                try:
                    output = commands.execute(auth_cmd, input=message)
                except commands.CommandLineException as e:
                    if e.stderr != "":
                        log.debug(
                            f"PAM auth: external authentication script had errors: status {e.returncode} error {e.stderr}"
                        )
                    output = e.stdout
                if output.strip() == "True":
                    authenticated = True
                else:
                    authenticated = False
        else:
            try:
                import pam
            except ImportError:
                log.debug("PAM authenticate: could not load pam module, PAM authentication disabled")
                return None, "", ""

            p_auth = pam.pam()
            authenticated = p_auth.authenticate(pam_username, password, service=pam_service)

        if authenticated:
            log.debug(
                f"PAM authentication successful for {'redacted' if options['redact_username_in_logs'] else pam_username}"
            )
            return True, auto_register_email, auto_register_username
        else:
            log.debug(
                f"PAM authentication failed for {'redacted' if options['redact_username_in_logs'] else pam_username}"
            )
            return False, "", ""

    def authenticate_user(self, user, password, options):
        return self.authenticate(user.email, user.username, password, options)[0]


__all__ = ("PAM",)
