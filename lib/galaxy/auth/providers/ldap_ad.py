"""
Created on 15/07/2014

@author: Andrew Robinson
"""

import logging

from galaxy.exceptions import ConfigurationError
from ..providers import AuthProvider
from galaxy.auth import _get_bool

log = logging.getLogger(__name__)


def _get_subs(d, k, params):
    if k not in d:
        raise ConfigurationError("Missing '%s' parameter in LDAP options" % k)
    return str(d[k]).format(**params)


def _parse_ldap_options(ldap, options_unparsed):
    # Tag is defined in the XML but is empty
    if not options_unparsed:
        return []

    if "=" not in options_unparsed:
        log.error("LDAP authenticate: Invalid syntax in <ldap-options>. Syntax should be option1=value1,option2=value2")
        return []

    ldap_options = []

    # Valid options must start with this prefix. See help(ldap)
    prefix = "OPT_"

    for opt in options_unparsed.split(","):
        key, value = opt.split("=")

        try:
            pair = []
            for n in (key, value):
                if not n.startswith(prefix):
                    raise ValueError

                name = getattr(ldap, n)
                pair.append(name)

        except ValueError:
            log.warning("LDAP authenticate: Invalid parameter pair %s=%s. '%s' doesn't start with prefix %s", key, value, n, prefix)
            continue

        except AttributeError:
            log.warning("LDAP authenticate: Invalid parameter pair %s=%s. '%s' is not available in module ldap", key, value, n)
            continue

        else:
            log.debug("LDAP authenticate: Valid LDAP option pair %s=%s -> %s=%s", key, value, *pair)
            ldap_options.append(pair)

    return ldap_options


class LDAP(AuthProvider):

    """
    Attempts to authenticate users against an LDAP server.

    If options include search-fields then it will attempt to search LDAP for
    those fields first.  After that it will bind to LDAP with the username
    (formatted as specified).
    """
    plugin_type = 'ldap'

    def authenticate(self, email, username, password, options):
        """
        See abstract method documentation.
        """
        log.debug("LDAP authenticate: email is %s" % email)
        log.debug("LDAP authenticate: username is %s" % username)
        log.debug("LDAP authenticate: options are %s" % options)

        failure_mode = False  # reject but continue
        if options.get('continue-on-failure', 'False') == 'False':
            failure_mode = None  # reject and do not continue

        if _get_bool(options, 'login-use-username', False):
            if username is None:
                log.debug('LDAP authenticate: username must be used to login, cannot be None')
                return (failure_mode, '', '')
        else:
            if email is None:
                log.debug('LDAP authenticate: email must be used to login, cannot be None')
                return (failure_mode, '', '')

        try:
            import ldap
        except:
            log.debug('LDAP authenticate: could not load ldap module')
            return (failure_mode, '', '')

        # do LDAP search (if required)
        params = {'email': email, 'username': username, 'password': password}

        try:
            ldap_options_raw = _get_subs(options, 'ldap-options', params)
        except ConfigurationError:
            ldap_options = ()
        else:
            ldap_options = _parse_ldap_options(ldap, ldap_options_raw)

        if 'search-fields' in options:
            try:
                # setup connection
                ldap.set_option(ldap.OPT_REFERRALS, 0)

                for opt in ldap_options:
                    ldap.set_option(*opt)

                l = ldap.initialize(_get_subs(options, 'server', params))
                l.protocol_version = 3

                if 'search-user' in options:
                    l.simple_bind_s(_get_subs(options, 'search-user', params),
                                    _get_subs(options, 'search-password', params))
                else:
                    l.simple_bind_s()

                # setup search
                attributes = [_.strip().format(**params)
                              for _ in options['search-fields'].split(',')]
                suser = l.search_ext_s(_get_subs(options, 'search-base', params),
                    ldap.SCOPE_SUBTREE,
                    _get_subs(options, 'search-filter', params), attributes,
                    timeout=60, sizelimit=1)

                # parse results
                if suser is None or len(suser) == 0:
                    log.warning('LDAP authenticate: search returned no results')
                    return (failure_mode, '', '')
                dn, attrs = suser[0]
                log.debug(("LDAP authenticate: dn is %s" % dn))
                log.debug(("LDAP authenticate: search attributes are %s" % attrs))
                if hasattr(attrs, 'has_key'):
                    for attr in attributes:
                        if attr in attrs:
                            params[attr] = str(attrs[attr][0])
                        else:
                            params[attr] = ""
                params['dn'] = dn
            except Exception:
                log.exception('LDAP authenticate: search exception')
                return (failure_mode, '', '')
        # end search

        # bind as user to check their credentials
        try:
            # setup connection
            ldap.set_option(ldap.OPT_REFERRALS, 0)

            for opt in ldap_options:
                ldap.set_option(*opt)

            l = ldap.initialize(_get_subs(options, 'server', params))
            l.protocol_version = 3
            l.simple_bind_s(_get_subs(
                options, 'bind-user', params), _get_subs(options, 'bind-password', params))
            whoami = l.whoami_s()
            log.debug("LDAP authenticate: whoami is %s", whoami)
            if whoami is None:
                raise RuntimeError('LDAP authenticate: anonymous bind')
        except Exception:
            log.warning('LDAP authenticate: bind exception', exc_info=True)
            return (failure_mode, '', '')

        log.debug('LDAP authentication successful')
        return (True,
                _get_subs(options, 'auto-register-email', params),
                _get_subs(options, 'auto-register-username', params))

    def authenticate_user(self, user, password, options):
        """
        See abstract method documentation.
        """
        return self.authenticate(user.email, user.username, password, options)[0]


class ActiveDirectory(LDAP):
    """ Effectively just an alias for LDAP auth, but may contain active directory specific
    logic in the future. """
    plugin_type = 'activedirectory'

__all__ = ['LDAP', 'ActiveDirectory']
