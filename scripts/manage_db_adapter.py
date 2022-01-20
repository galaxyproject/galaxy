"""
This script is intended to be invoked by the legacy manage_db.sh script.
It translates the arguments supplied to manage_db.sh into the format used
by migrate_db.py.

INPUT:                        |   OUTPUT:
----------------------------------------------------------
upgrade --version=foo         |   upgrade foo
upgrade --version foo         |   upgrade foo
upgrade                       |   upgrade gxy@head
upgrade install               |   upgrade tsi@head
upgrade --version=bar install |   upgrade bar
upgrade -c path-to-galaxy.yml |   upgrade --galaxy-config path-to-galaxy.yml gxy@head

The converted sys.argv will include `-c path-to-alembic.ini`.
The optional `-c` argument name is renamed to `--galaxy-config`.
"""

import os
import sys

import alembic.config

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.model.migrations.scripts import (
    add_db_urls_to_command_arguments,
    LegacyScripts,
)


def run():
    ls = LegacyScripts()
    target_database = ls.pop_database_argument(sys.argv)
    ls.rename_config_argument(sys.argv)
    ls.rename_alembic_config_argument(sys.argv)
    ls.convert_version_argument(sys.argv, target_database)
    add_db_urls_to_command_arguments(sys.argv, os.getcwd())
    alembic.config.main()


if __name__ == '__main__':
    run()
