#!/usr/bin/python
from __future__ import print_function

import optparse
import os
import sys

from six.moves.configparser import ConfigParser
from sqlalchemy.exc import OperationalError, ProgrammingError

sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'lib'))

import galaxy.webapps.tool_shed.model.mapping as tool_shed_model
from tool_shed.util import xml_util


def check_db(config_parser):
    dburi = None

    if config_parser.has_option('app:main', 'database_connection'):
        dburi = config_parser.get('app:main', 'database_connection')
    elif config_parser.has_option('app:main', 'database_file'):
        db_file = config_parser.get('app:main', 'database_file')
        dburi = "sqlite:///%s?isolation_level=IMMEDIATE" % db_file
    else:
        sys.exit('The database configuration setting is missing from the tool_shed.ini file.  Add this setting before attempting to bootstrap.')

    sa_session = None

    database_exists_message = 'The database configured for this Tool Shed is not new, so bootstrapping is not allowed.  '
    database_exists_message += 'Create a new database that has not been migrated before attempting to bootstrap.'

    try:
        model = tool_shed_model.init(config_parser.get('app:main', 'file_path'), dburi, engine_options={}, create_tables=False)
        sa_session = model.context.current
        sys.exit(database_exists_message)
    except ProgrammingError:
        pass
    except OperationalError:
        pass

    try:
        if sa_session is not None:
            result = sa_session.execute('SELECT version FROM migrate_version').first()
            if result[0] >= 2:
                sys.exit(database_exists_message)
            else:
                pass
    except ProgrammingError:
        pass

    if config_parser.has_option('app:main', 'hgweb_config_dir'):
        hgweb_config_parser = ConfigParser()
        hgweb_dir = config_parser.get('app:main', 'hgweb_config_dir')
        hgweb_config_file = os.path.join(hgweb_dir, 'hgweb.config')
        if not os.path.exists(hgweb_config_file):
            sys.exit(0)
        hgweb_config_parser.read(hgweb_config_file)
        configured_repos = hgweb_config_parser.items('paths')
        if len(configured_repos) >= 1:
            message = "This Tool Shed's hgweb.config file contains entries, so bootstrapping is not allowed.  Delete"
            message += " the current hgweb.config file along with all associated repositories in the configured "
            message += "location before attempting to boostrap."
            sys.exit(message)
        else:
            sys.exit(0)
    else:
        sys.exit(0)

    sys.exit(0)


def admin_user_info():
    user_info_config = os.path.abspath(os.path.join(os.getcwd(), 'scripts/tool_shed/bootstrap_tool_shed', 'user_info.xml'))
    tree, error_message = xml_util.parse_xml(user_info_config)
    username = None
    email = None
    password = None
    if tree is None:
        print("The XML file ", user_info_config, " seems to be invalid, using defaults.")
        email = 'admin@test.org'
        password = 'testuser'
        username = 'admin'
    else:
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'email':
                email = elem.text
            elif elem.tag == 'password':
                password = elem.text
            elif elem.tag == 'username':
                username = elem.text
    return (username, email, password)


def get_local_tool_shed_url(config_parser):
    port = '9009'
    if config_parser.has_section('server:main'):
        if config_parser.has_option('server:main', 'port'):
            port = config_parser.get('server:main', 'port')
    host = '127.0.0.1'
    print('http://%s:%s' % (host, port))
    return 0


def main(args):
    config_parser = ConfigParser()

    if os.path.exists(args.config):
        config_parser.read(args.config)
    else:
        return 1

    if args.method == 'check_db':
        return check_db(config_parser)
    elif args.method == 'admin_user_info':
        (username, email, password) = admin_user_info()
        print('%s__SEP__%s__SEP__%s' % (username, email, password))
        return 0
    elif args.method == 'get_url':
        return get_local_tool_shed_url(config_parser)
    else:
        return 1


parser = optparse.OptionParser()
parser.add_option('-c', '--config_file', dest='config', action='store', default='config/tool_shed.yml.sample')
parser.add_option('-e', '--execute', dest='method', action='store', default='check_db')
(args, options) = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
