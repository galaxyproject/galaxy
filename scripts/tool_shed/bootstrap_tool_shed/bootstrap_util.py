#!/usr/bin/env python

import optparse
import os
import sys
from configparser import ConfigParser

from sqlalchemy import text
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
)

sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "lib"))

import tool_shed.webapp.model.mapping as tool_shed_model
from tool_shed.util import xml_util
from tool_shed.webapp.config import ToolShedAppConfiguration


def check_db(config: ToolShedAppConfiguration):
    dburi = config.database_connection

    sa_session = None

    database_exists_message = (
        "The database configured for this Tool Shed is not new, so bootstrapping is not allowed.  "
    )
    database_exists_message += "Create a new database that has not been migrated before attempting to bootstrap."

    try:
        model = tool_shed_model.init(config.file_path, dburi, engine_options={}, create_tables=False)
        sa_session = model.context.current
        sys.exit(database_exists_message)
    except ProgrammingError:
        pass
    except OperationalError:
        pass

    try:
        if sa_session is not None:
            result = sa_session.execute(text("SELECT version FROM migrate_version")).first()
            if result[0] >= 2:
                sys.exit(database_exists_message)
            else:
                pass
    except ProgrammingError:
        pass

    if config.hgweb_config_dir:
        hgweb_config_parser = ConfigParser()
        hgweb_dir = config.hgweb_config_dir
        hgweb_config_file = os.path.join(hgweb_dir, "hgweb.config")
        if not os.path.exists(hgweb_config_file):
            sys.exit(0)
        hgweb_config_parser.read(hgweb_config_file)
        configured_repos = hgweb_config_parser.items("paths")
        if len(configured_repos) >= 1:
            message = "This Tool Shed's hgweb.config file contains entries, so bootstrapping is not allowed.  Delete"
            message += " the current hgweb.config file along with all associated repositories in the configured "
            message += "location before attempting to boostrap."
            sys.exit(message)
        else:
            sys.exit(0)

    sys.exit(0)


def admin_user_info():
    user_info_config = os.path.abspath(
        os.path.join(os.getcwd(), "scripts/tool_shed/bootstrap_tool_shed", "user_info.xml")
    )
    tree, error_message = xml_util.parse_xml(user_info_config)
    username = None
    email = None
    password = None
    if tree is None:
        email = "admin@test.org"
        password = "testuser"
        username = "admin"
    else:
        root = tree.getroot()
        for elem in root:
            if elem.tag == "email":
                email = elem.text
            elif elem.tag == "password":
                password = elem.text
            elif elem.tag == "username":
                username = elem.text
    return (username, email, password)


def main(args):
    config = ToolShedAppConfiguration(config_file=args.config)

    if args.method == "check_db":
        return check_db(config)
    elif args.method == "admin_user_info":
        (username, email, password) = admin_user_info()
        print(f"{username}__SEP__{email}__SEP__{password}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-c", "--config_file", dest="config", action="store", default="config/tool_shed.yml.sample")
    parser.add_option("-e", "--execute", dest="method", action="store", default="check_db")
    (args, options) = parser.parse_args()
    sys.exit(main(args))
