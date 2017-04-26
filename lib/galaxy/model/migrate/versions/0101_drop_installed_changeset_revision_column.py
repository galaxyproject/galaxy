"""
Migration script to drop the installed_changeset_revision column from the tool_dependency table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import MetaData, Table
from sqlalchemy.exc import NoSuchTableError

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        ToolDependency_table = Table( "tool_dependency", metadata, autoload=True )
    except NoSuchTableError:
        ToolDependency_table = None
        log.debug( "Failed loading table tool_dependency" )
    if ToolDependency_table is not None:
        try:
            col = ToolDependency_table.c.installed_changeset_revision
            col.drop()
        except Exception:
            log.exception("Dropping column 'installed_changeset_revision' from tool_dependency table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
