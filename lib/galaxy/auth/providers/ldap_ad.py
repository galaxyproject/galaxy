"""
Created on 15/07/2014

@author: Andrew Robinson
"""

import logging

from galaxy.exceptions import ConfigurationError
from galaxy.security.validate_user_input import transform_publicname
from galaxy.util import (
    string_as_bool,
    unicodify,
)
from ..providers import AuthProvider

try:
    import ldap
except ImportError as exc:
    ldap = None
    ldap_import_exc = exc

log = logging.getLogger(__name__)


def _get_subs(d, k, params):
    if k not in d or not d[k]:
        raise ConfigurationError(f"Missing '{k}' parameter in LDAP options")
    return str(d[k]).format(**params)


def _parse_ldap_options(options_unparsed):
    # Tag is defined in the XML but is empty
    if not options_unparsed:
        return []

    ldap_options = []

    # Valid options must start with this prefix. See help(ldap)
    prefix = "OPT_"

    for opt in options_unparsed.split(","):
        try:
            key, value = opt.split("=")
        except ValueError:
            log.warning(
                "LDAP authenticate: Invalid syntax '%s' inside <ldap-options> element. Syntax should be option1=value1,option2=value2",
                opt,
            )
            continue

        if not key.startswith(prefix):
            log.warning(
                "LDAP authenticate: Invalid LDAP option '%s'. '%s' doesn't start with prefix '%s'", opt, key, prefix
            )
            continue
        try:
            key = getattr(ldap, key)
        except AttributeError:
            log.warning("LDAP authenticate: Invalid LDAP option '%s'. '%s' is not available in module ldap", opt, key)
            continue
        if value.startswith(prefix):
            try:
                value = getattr(ldap, value)
            except AttributeError:
                log.warning(
                    "LDAP authenticate: Invalid LDAP option '%s'. '%s' is not available in module ldap", opt, value
                )
                continue
        pair = (key, value)
        log.debug("LDAP authenticate: Valid LDAP option pair '%s' -> '%s=%s'", opt, *pair)
        ldap_options.append(pair)

    return ldap_options


class LDAP(AuthProvider):

    """
    Attempts to authenticate users against an LDAP server.

    If options include search-fields then it will attempt to search LDAP for
    those fields first.  After that it will bind to LDAP with the username
    (formatted as specified).
    """

    plugin_type = "ldap"
    role_search_option = "auto-register-roles"

    def __init__(self):
        super().__init__()
        self.auto_create_roles_or_groups = False
        self.role_search_attribute = None

    def check_config(self, username, email, options):
        ok = True
        if options.get("continue-on-failure", "False") == "False":
            failure_mode = None  # reject and do not continue
        else:
            failure_mode = False  # reject but continue

        if string_as_bool(options.get("login-use-username", False)):
            if not username:
                log.debug("LDAP authenticate: username must be used to login, cannot be None")
                return ok, failure_mode
        else:
            if not email:
                log.debug("LDAP authenticate: email must be used to login, cannot be None")
                return ok, failure_mode

        auto_create_roles = string_as_bool(options.get("auto-create-roles", False))
        auto_create_groups = string_as_bool(options.get("auto-create-groups", False))
        self.auto_create_roles_or_groups = auto_create_roles or auto_create_groups
        auto_assign_roles_to_groups_only = string_as_bool(options.get("auto-assign-roles-to-groups-only", False))
        if auto_assign_roles_to_groups_only and not (auto_create_roles and auto_create_groups):
            raise ConfigurationError(
                "If 'auto-assign-roles-to-groups-only' is True, auto-create-roles and "
                "auto-create-groups have to be True as well."
            )

        self.role_search_attribute = options.get(self.role_search_option)
        if self.auto_create_roles_or_groups and self.role_search_attribute is None:
            raise ConfigurationError(
                "If 'auto-create-roles' or 'auto-create-groups' is True, a '%s' attribute has to"
                " be provided." % self.role_search_option
            )

        return ok, failure_mode

    def ldap_search(self, email, username, options):
        config_ok, failure_mode = self.check_config(username, email, options)
        if ldap is None:
            raise RuntimeError("Failed to load LDAP module: %s", str(ldap_import_exc))

        if not config_ok:
            return failure_mode, None

        params = {"email": email, "username": username}

        try:
            ldap_options_raw = _get_subs(options, "ldap-options", params)
        except ConfigurationError:
            ldap_options = ()
        else:
            ldap_options = _parse_ldap_options(ldap_options_raw)

        try:
            # setup connection
            ldap.set_option(ldap.OPT_REFERRALS, 0)

            for opt in ldap_options:
                ldap.set_option(*opt)
        except Exception:
            log.exception("LDAP authenticate: set_option exception")
            return (failure_mode, None)

        if "search-fields" in options:
            try:
                conn = ldap.initialize(_get_subs(options, "server", params))
                conn.protocol_version = 3

                if "search-user" in options:
                    conn.simple_bind_s(
                        _get_subs(options, "search-user", params), _get_subs(options, "search-password", params)
                    )
                else:
                    conn.simple_bind_s()

                # setup search
                attributes = {_.strip().format(**params) for _ in options["search-fields"].split(",")}
                if "search-memberof-filter" in options:
                    attributes.add("memberOf")
                suser = conn.search_ext_s(
                    _get_subs(options, "search-base", params),
                    ldap.SCOPE_SUBTREE,
                    _get_subs(options, "search-filter", params),
                    attributes,
                    timeout=60,
                    sizelimit=1,
                )

                # parse results
                if suser is None or len(suser) == 0:
                    log.warning("LDAP authenticate: search returned no results")
                    return (failure_mode, None)
                dn, attrs = suser[0]
                log.debug("LDAP authenticate: dn is %s", dn)
                log.debug("LDAP authenticate: search attributes are %s", attrs)
                for attr in attributes:
                    if self.role_search_attribute and attr == self.role_search_attribute[1:-1]:  # strip curly brackets
                        # keep role names as list
                        params[self.role_search_option] = [unicodify(_) for _ in attrs[attr]]
                    elif attr == "memberOf":
                        params[attr] = [unicodify(_) for _ in attrs[attr]]
                    elif attr in attrs:
                        params[attr] = unicodify(attrs[attr][0])
                    else:
                        params[attr] = ""

                if self.auto_create_roles_or_groups and self.role_search_option not in params:
                    raise ConfigurationError(
                        "Missing or mismatching LDAP parameters for %s. Make sure the %s is "
                        "included in the 'search-fields'." % (self.role_search_option, self.role_search_attribute)
                    )
                params["dn"] = dn
            except Exception:
                log.exception("LDAP authenticate: search exception")
                return (failure_mode, None)

        return failure_mode, params

    def authenticate(self, email, username, password, options):
        """
        See abstract method documentation.
        """
        if not options["redact_username_in_logs"]:
            log.debug("LDAP authenticate: email is %s", email)
            log.debug("LDAP authenticate: username is %s", username)

        log.debug("LDAP authenticate: options are %s", options)

        failure_mode, params = self.ldap_search(email, username, options)
        if not params:
            return failure_mode, "", ""

        # allow to skip authentication to allow for pre-populating users
        if not options.get("no_password_check", False):
            params["password"] = password
            if not self._authenticate(params, options):
                return failure_mode, "", ""

        # check whether the user is a member of a specified group/domain/...
        if "search-memberof-filter" in options:
            search_filter = _get_subs(options, "search-memberof-filter", params)
            if not any(search_filter in ad_node_name for ad_node_name in params["memberOf"]):
                return failure_mode, "", ""

        attributes = {}
        if self.auto_create_roles_or_groups:
            attributes["roles"] = params[self.role_search_option]
        return (
            True,
            _get_subs(options, "auto-register-email", params),
            transform_publicname(_get_subs(options, "auto-register-username", params)),
            attributes,
        )

    def _authenticate(self, params, options):
        """
        Do the actual authentication by binding as the user to check their credentials
        """
        try:
            conn = ldap.initialize(_get_subs(options, "server", params))
            conn.protocol_version = 3
            bind_user = _get_subs(options, "bind-user", params)
            bind_password = _get_subs(options, "bind-password", params)
        except Exception:
            log.exception("LDAP authenticate: initialize exception")
            return False
        try:
            conn.simple_bind_s(bind_user, bind_password)
            try:
                whoami = conn.whoami_s()
            except ldap.PROTOCOL_ERROR:
                # The "Who am I?" extended operation is not supported by this LDAP server
                pass
            else:
                if whoami is None:
                    raise RuntimeError("LDAP authenticate: anonymous bind")
                if not options["redact_username_in_logs"]:
                    log.debug("LDAP authenticate: whoami is %s", whoami)
        except Exception as e:
            log.info("LDAP authenticate: bind exception: %s", unicodify(e))
            return False
        log.debug("LDAP authentication successful")
        return True

    def authenticate_user(self, user, password, options):
        """
        See abstract method documentation.
        """
        return self.authenticate(user.email, user.username, password, options)[0]


class ActiveDirectory(LDAP):
    """Effectively just an alias for LDAP auth, but may contain active directory specific
    logic in the future."""

    plugin_type = "activedirectory"


__all__ = ("LDAP", "ActiveDirectory")
