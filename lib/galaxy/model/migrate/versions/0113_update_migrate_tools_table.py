"""
Migration script to update the migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate.
"""
from __future__ import print_function

import logging
import sys

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )


def upgrade(migrate_engine):
    print(__doc__)
    # Create the table.
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/galaxy/tool_shed/migrate';"
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Updating migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate failed.")


def downgrade(migrate_engine):
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/galaxy/tool_shed/migrate';"
        migrate_engine.execute( cmd )
    except Exception:
        log.exception("Updating migrate_tools.repository_path column to point to the old location lib/galaxy/tool_shed/migrate failed.")
