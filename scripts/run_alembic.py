#!/usr/bin/env python

"""
Retrieves relevant configuration values and invokes the Alembic console runner.

Must be executed from Galaxy's root directory.

Use this script if you need to run migration operations on the Tool Shed
Install data model (the *tsi* migration branch), or if you need access to the
full scope of command line options provided by Alembic. For regular migration
tasks, uses the db.sh script.

We use branch labels to distinguish between the galaxy and the tool_shed_install models,
so in most cases you'll need to identify the branch to which your command should be applied.
Use these identifiers: `gxy` for galaxy, and `tsi` for tool_shed_install.

To create a revision for galaxy:
./scripts/run_alembic.py revision --head=gxy@head -m "your description"

To create a revision for tool_shed_install:
./scripts/run_alembic.py revision --head=tsi@head -m "your description"

To upgrade:
./scripts/run_alembic.py upgrade gxy@head  # upgrade gxy to head revision
./scripts/run_alembic.py upgrade gxy@+1  # upgrade gxy to 1 revision above current
./scripts/run_alembic.py upgrade [revision identifier]  # upgrade gxy to a specific revision
./scripts/run_alembic.py upgrade [revision identifier]+1  # upgrade gxy to 1 revision above specific revision
./scripts/run_alembic.py upgrade heads  # upgrade gxy and tsi to head revisions

To downgrade:
./scripts/run_alembic.py downgrade gxy@base  # downgrade gxy to base (database with empty alembic table)
./scripts/run_alembic.py downgrade gxy@-1  # downgrade gxy to 1 revision below current
./scripts/run_alembic.py downgrade [revision identifier]  # downgrade gxy to a specific revision
./scripts/run_alembic.py downgrade [revision identifier]-1  # downgrade gxy to 1 revision below specific revision

To pass a galaxy config file, use `--galaxy-config`

You may also override the galaxy database url and/or the
tool shed install database url, as well as the database_template
and database_encoding configuration options with env vars:
GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-db-url ./scripts/run_alembic.py ...
GALAXY_INSTALL_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-other-db-url ./scripts/run_alembic.py ...

Further information:
Galaxy migration documentation: lib/galaxy/model/migrations/README.md
Alembic documentation: https://alembic.sqlalchemy.org
"""

import logging
import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations.scripts import (
    add_db_urls_to_command_arguments,
    get_configuration,
    invoke_alembic,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

ALEMBIC_CONFIG = "lib/galaxy/model/migrations/alembic.ini"


def run():
    sys.argv.insert(1, "--config")
    sys.argv.insert(2, ALEMBIC_CONFIG)
    gxy_config, tsi_config, _ = get_configuration(sys.argv, os.getcwd())
    add_db_urls_to_command_arguments(sys.argv, gxy_config.url, tsi_config.url)
    invoke_alembic()


if __name__ == "__main__":
    run()
