import errno
import logging
import xml.etree.ElementTree
from collections import namedtuple

import galaxy.auth.providers
from galaxy.exceptions import Conflict
from galaxy.security.validate_user_input import validate_publicname
from galaxy.util import plugin_config, string_as_bool


log = logging.getLogger(__name__)

AUTH_CONF_XML = """<?xml version="1.0"?>
<auth>
    <authenticator>
        <type>localdb</type>
        <options>
            <allow-password-change>true</allow-password-change>
        </options>
    </authenticator>
</auth>
"""

Authenticator = namedtuple('Authenticator', ['plugin', 'filter_template', 'options'])


def get_authenticators(auth_config_file, auth_config_file_set):
    __plugins_dict = plugin_config.plugins_dict(galaxy.auth.providers, 'plugin_type')
    # parse XML
    try:
        ct = xml.etree.ElementTree.parse(auth_config_file)
        conf_root = ct.getroot()
    except (OSError, IOError) as exc:
        if exc.errno == errno.ENOENT and not auth_config_file_set:
            conf_root = xml.etree.ElementTree.fromstring(AUTH_CONF_XML)
        else:
            raise

    authenticators = []
    # process authenticators
    for auth_elem in conf_root:
        type_elem = auth_elem.find('type')
        plugin = __plugins_dict.get(type_elem.text)()

        # check filterelem
        filter_elem = auth_elem.find('filter')
        if filter_elem is not None:
            filter_template = str(filter_elem.text)
        else:
            filter_template = None

        # extract options
        options_elem = auth_elem.find('options')
        options = {}
        if options_elem is not None:
            for opt in options_elem:
                options[opt.tag] = opt.text
        authenticator = Authenticator(
            plugin=plugin,
            filter_template=filter_template,
            options=options,
        )
        authenticators.append(authenticator)
    return authenticators


def parse_auth_results(trans, auth_results, options):
    auth_return = {}
    auth_result, auto_email, auto_username = auth_results[:3]
    auto_username = str(auto_username).lower()
    # make username unique
    if validate_publicname(trans, auto_username) != '':
        i = 1
        while i <= 10:  # stop after 10 tries
            if validate_publicname(trans, "%s-%i" % (auto_username, i)) == '':
                auto_username = "%s-%i" % (auto_username, i)
                break
            i += 1
        else:
            raise Conflict("Cannot make unique username")
    log.debug("Email: %s, auto-register with username: %s" % (auto_email, auto_username))
    auth_return["auto_reg"] = string_as_bool(options.get('auto-register', False))
    auth_return["email"] = auto_email
    auth_return["username"] = auto_username
    auth_return["auto_create_roles"] = string_as_bool(options.get('auto-create-roles', False))
    auth_return["auto_create_groups"] = string_as_bool(options.get('auto-create-groups', False))
    auth_return["auto_assign_roles_to_groups_only"] = string_as_bool(
        options.get('auto-assign-roles-to-groups-only', False))

    if len(auth_results) == 4:
        auth_return["attributes"] = auth_results[3]
    return auth_return
