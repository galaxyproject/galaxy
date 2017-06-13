"""
Migration script to add the metadata, update_available and includes_datatypes columns to the tool_shed_repository table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType

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
    c = Column( "metadata", JSONType(), nullable=True )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.metadata
    except Exception:
        log.exception("Adding metadata column to the tool_shed_repository table failed.")
    c = Column( "includes_datatypes", Boolean, index=True, default=False )
    try:
        c.create( ToolShedRepository_table, index_name="ix_tool_shed_repository_includes_datatypes")
        assert c is ToolShedRepository_table.c.includes_datatypes
        migrate_engine.execute( "UPDATE tool_shed_repository SET includes_datatypes=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Adding includes_datatypes column to the tool_shed_repository table failed.")
    c = Column( "update_available", Boolean, default=False )
    try:
        c.create( ToolShedRepository_table )
        assert c is ToolShedRepository_table.c.update_available
        migrate_engine.execute( "UPDATE tool_shed_repository SET update_available=%s" % engine_false(migrate_engine))
    except Exception:
        log.exception("Adding update_available column to the tool_shed_repository table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.metadata.drop()
    except Exception:
        log.exception("Dropping column metadata from the tool_shed_repository table failed.")
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        try:
            ToolShedRepository_table.c.includes_datatypes.drop()
        except Exception:
            log.exception("Dropping column includes_datatypes from the tool_shed_repository table failed.")
        try:
            ToolShedRepository_table.c.update_available.drop()
        except Exception:
            log.exception("Dropping column update_available from the tool_shed_repository table failed.")
