"""
Migration script to add the tool_shed_repository table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Table, TEXT

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

# New table to store information about cloned tool shed repositories.
ToolShedRepository_table = Table( "tool_shed_repository", metadata,
                                  Column( "id", Integer, primary_key=True ),
                                  Column( "create_time", DateTime, default=now ),
                                  Column( "update_time", DateTime, default=now, onupdate=now ),
                                  Column( "tool_shed", TrimmedString( 255 ), index=True ),
                                  Column( "name", TrimmedString( 255 ), index=True ),
                                  Column( "description", TEXT ),
                                  Column( "owner", TrimmedString( 255 ), index=True ),
                                  Column( "changeset_revision", TrimmedString( 255 ), index=True ),
                                  Column( "deleted", Boolean, index=True, default=False ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        ToolShedRepository_table.create()
    except Exception:
        log.exception("Creating tool_shed_repository table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        ToolShedRepository_table.drop()
    except Exception:
        log.exception("Dropping tool_shed_repository table failed.")
