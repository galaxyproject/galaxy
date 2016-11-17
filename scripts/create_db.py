"""
Creates the initial galaxy database schema using the settings defined in
config/galaxy.ini.

This script is also wrapped by create_db.sh.

.. note: pass '-c /location/to/your_config.ini' for non-standard ini file
locations.

.. note: if no database_connection is set in galaxy.ini, the default, sqlite
database will be constructed.
    Using the database_file setting in galaxy.ini will create the file at the
    settings location (??)

.. seealso: galaxy.ini, specifically the settings: database_connection and
database file
"""
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.model.migrate.check import create_or_verify_database as create_db
from galaxy.model.orm.scripts import get_config
from galaxy.model.tool_shed_install.migrate.check import create_or_verify_database as create_install_db
from galaxy.webapps.tool_shed.model.migrate.check import create_or_verify_database as create_tool_shed_db


def invoke_create():
    config = get_config(sys.argv)
    if config['database'] == 'galaxy':
        create_db(config['db_url'], config['config_file'])
    elif config['database'] == 'tool_shed':
        create_tool_shed_db(config['db_url'])
    elif config['database'] == 'install':
        create_install_db(config['db_url'])


if __name__ == "__main__":
    invoke_create()
