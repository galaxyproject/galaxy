"""
Migration script to add the uninstalled and dist_to_shed columns to the tool_shed_repository table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def engine_false(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "FALSE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 0
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    c = Column( "uninstalled", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.uninstalled
        migrate_engine.execute( "UPDATE tool_shed_repository SET uninstalled=%s" % engine_false(migrate_engine) )
    except Exception:
        log.exception("Adding uninstalled column to the tool_shed_repository table failed.")
    c = Column( "dist_to_shed", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.dist_to_shed
        migrate_engine.execute( "UPDATE tool_shed_repository SET dist_to_shed=%s" % engine_false(migrate_engine) )
    except Exception:
        log.exception("Adding dist_to_shed column to the tool_shed_repository table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        try:
            ToolShedRepository_table.c.uninstalled.drop()
        except Exception:
            log.exception("Dropping column uninstalled from the tool_shed_repository table failed.")
        try:
            ToolShedRepository_table.c.dist_to_shed.drop()
        except Exception:
            log.exception("Dropping column dist_to_shed from the tool_shed_repository table failed.")
