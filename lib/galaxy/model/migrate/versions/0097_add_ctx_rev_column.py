"""
Migration script to add the ctx_rev column to the tool_shed_repository table.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Column, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
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
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    col = Column( "ctx_rev", TrimmedString( 10 ) )
    try:
        col.create( ToolShedRepository_table )
        assert col is ToolShedRepository_table.c.ctx_rev
    except Exception:
        log.exception("Adding ctx_rev column to the tool_shed_repository table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    ToolShedRepository_table = Table( "tool_shed_repository", metadata, autoload=True )
    try:
        ToolShedRepository_table.c.ctx_rev.drop()
    except Exception:
        log.exception("Dropping column ctx_rev from the tool_shed_repository table failed.")
