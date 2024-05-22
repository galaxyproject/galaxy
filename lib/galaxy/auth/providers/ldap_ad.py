"""
Created on 15/07/2014

@author: Andrew Robinson

Modification on 24/10/2022

Addition of LDAP3 auth provider using the ldap3 module. The original LDAP auth provider uses the python-ldap library which
has external dependencies like openldap client libs. ldap3 is a pure Python LDAP v3 client library.

@author: Mahendra Paipuri, CNRS
"""

import logging
from urllib.parse import urlparse

from galaxy.exceptions import ConfigurationError
from galaxy.security.validate_user_input import transform_publicname
from galaxy.util import (
    listify,
    string_as_bool,
    unicodify,
)
from . import AuthProvider

try:
    import ldap
except ImportError as exc:
    ldap = None
    ldap_import_exc = exc

try:
    import ldap3
except ImportError as exc:
    ldap3 = None
    ldap3_import_exc = exc

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
                f"If 'auto-create-roles' or 'auto-create-groups' is True, a '{self.role_search_option}' attribute has to"
                " be provided."
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
                        f"Missing or mismatching LDAP parameters for {self.role_search_option}. Make sure the {self.role_search_attribute} is included in the 'search-fields'."
                    )
                params["dn"] = dn
            except Exception:
                log.exception("LDAP authenticate: search exception")
                return (failure_mode, None)

        return failure_mode, params

    def authenticate(self, email, username, password, options, request):
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

    def authenticate_user(self, user, password, options, request):
        """
        See abstract method documentation.
        """
        return self.authenticate(user.email, user.username, password, options, request)[0]


class LDAP3(LDAP):
    """LDAP auth provider using ldap3 module"""

    plugin_type = "ldap3"

    def __init__(self):
        super().__init__()
        # Initialise server and autobind objects
        self.server = None
        self.auto_bind = None
        # LDAP over TLS bool
        self.ldap_tls = None

    def get_server(self, options, params):
        # Get server URL
        server_url = _get_subs(options, "server", params)
        # Check if server URL has scheme
        # If no scheme is provided, assume it to be ldap
        if "ldap" not in server_url:
            server_url = f"ldaps://{server_url}"
        # Check if TLS is available
        if server_url.startswith("ldaps://"):
            self.ldap_tls = True
        else:
            self.ldap_tls = False
        # Get server address and port
        url_obj = urlparse(server_url)
        server_address = url_obj.hostname
        try:
            server_port = int(url_obj.port)
        except TypeError:
            # If port is not specified use standard port numbers based on TLS
            if self.ldap_tls:
                server_port = 636
            else:
                server_port = 389
        # Create server object
        self.server = ldap3.Server(server_address, port=server_port, use_ssl=self.ldap_tls, get_info=ldap3.ALL)
        # Set auto_bind
        self.auto_bind = ldap3.AUTO_BIND_NO_TLS if self.ldap_tls else ldap3.AUTO_BIND_TLS_BEFORE_BIND

    def ldap_search(self, email, username, options):
        config_ok, failure_mode = self.check_config(username, email, options)
        if ldap3 is None:
            raise RuntimeError("Failed to load LDAP3 module: %s", str(ldap3_import_exc))

        if not config_ok:
            return failure_mode, None

        params = {"email": email, "username": username}

        if "search-fields" in options:
            try:
                # Initialise server object
                self.get_server(options, params)
                if "search-user" in options:
                    conn = ldap3.Connection(
                        self.server,
                        user=_get_subs(options, "search-user", params),
                        password=_get_subs(options, "search-password", params),
                        auto_bind=self.auto_bind,
                    )
                else:
                    conn = ldap3.Connection(self.server, auto_bind=self.auto_bind)
                # Use StartTLS if LDAP connection is not over TLS
                if not self.ldap_tls:
                    conn.start_tls()
                # setup search
                attributes = {_.strip().format(**params) for _ in options["search-fields"].split(",")}
                if "search-memberof-filter" in options:
                    attributes.add("memberOf")
                conn.search(
                    search_base=_get_subs(options, "search-base", params),
                    search_scope=ldap3.SUBTREE,
                    search_filter=_get_subs(options, "search-filter", params),
                    attributes=attributes,
                    time_limit=60,
                    size_limit=1,
                )
                response = conn.response
                # Unbind connection
                conn.unbind()

                # parse results
                if len(response) == 0 or "attributes" not in response[0].keys():
                    log.warning("LDAP3 authenticate: search returned no results")
                    return (failure_mode, None)
                dn = response[0]["dn"]
                attrs = response[0]["attributes"]
                log.debug("LDAP3 authenticate: dn is %s", dn)
                for attr in attributes:
                    attrs[attr] = listify(attrs[attr])
                log.debug("LDAP3 authenticate: search attributes are %s", attrs)
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
                        f"Missing or mismatching LDAP parameters for {self.role_search_option}. Make sure the {self.role_search_attribute} is included in the 'search-fields'."
                    )
                params["dn"] = dn
            except Exception:
                log.exception("LDAP3 authenticate: search exception")
                return (failure_mode, None)

        return failure_mode, params

    def _authenticate(self, params, options):
        """
        Do the actual authentication by binding as the user to check their credentials
        """
        try:
            # Initialise server object
            self.get_server(options, params)
            conn = ldap3.Connection(
                self.server,
                user=_get_subs(options, "bind-user", params),
                password=_get_subs(options, "bind-password", params),
                auto_bind=self.auto_bind,
            )
            # Use StartTLS if LDAP connection is not over TLS
            if not self.ldap_tls:
                conn.start_tls()
            try:
                whoami = conn.extend.standard.who_am_i()
                # Unbind connection
                conn.unbind()
            except ldap3.LDAPExtensionError:
                # The "Who am I?" extended operation is not supported by this LDAP server
                pass
            else:
                if whoami is None:
                    raise RuntimeError("LDAP3 authenticate: anonymous bind")
                if not options["redact_username_in_logs"]:
                    log.debug("LDAP3 authenticate: whoami is %s", whoami)
        except Exception as e:
            log.info("LDAP3 authenticate: bind exception: %s", unicodify(e))
            return False
        log.debug("LDAP3 authentication successful")
        return True


class ActiveDirectory(LDAP):
    """Effectively just an alias for LDAP auth, but may contain active directory specific
    logic in the future."""

    plugin_type = "activedirectory"


__all__ = ("LDAP", "LDAP3", "ActiveDirectory")

if __name__ == "__main__":
    # Instantiate LDAP3 class
    c = LDAP3()
    # Define options
    options = {
        "server": "ipa.demo1.freeipa.org",
        "bind-user": "{dn}",
        "bind-password": "{password}",
        "search-fields": "uid",
        "search-filter": "(uid={username})",
        "search-base": "cn=users,cn=accounts,dc=demo1,dc=freeipa,dc=org",
        "redact_username_in_logs": False,
        "auto-register-username": "{uid}",
        "auto-register-email": "{uid}@example.com",
    }
    # Test method
    print(c.authenticate("admin@example.com", "admin", "Secret123", options, None))
