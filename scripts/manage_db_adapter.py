"""
This script is intended to be invoked by the manage_db.sh script.
It translates the arguments supplied to manage_db.sh into the format used
by migrate_db.py.

INPUT:                        |   OUTPUT:
----------------------------------------------------------
upgrade --version=foo         |   upgrade foo
upgrade --version foo         |   upgrade foo
upgrade                       |   upgrade heads (if using a combined db for galaxy and install)
upgrade                       |   upgrade gxy@head (if using separate dbs for galaxy and install)
upgrade install               |   upgrade tsi@head
upgrade --version=bar install |   upgrade bar
upgrade -c path-to-galaxy.yml |   upgrade --galaxy-config path-to-galaxy.yml gxy@head

The converted sys.argv will include `-c path-to-alembic.ini`.
The optional `-c` argument name is renamed to `--galaxy-config`.
"""

import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations.scripts import (
    invoke_alembic,
    LegacyScripts,
    verify_database_is_initialized,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def run():
    ls = LegacyScripts(sys.argv, os.getcwd())
    ls.run()
    db_url = ls.get_db_url()
    verify_database_is_initialized(db_url)
    invoke_alembic()


if __name__ == "__main__":
    run()
