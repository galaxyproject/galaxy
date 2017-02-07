"""
Migration script to create the tool_id_guid_map table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, TEXT

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

ToolIdGuidMap_table = Table( "tool_id_guid_map", metadata,
                             Column( "id", Integer, primary_key=True ),
                             Column( "create_time", DateTime, default=now ),
                             Column( "update_time", DateTime, default=now, onupdate=now ),
                             Column( "tool_id", String( 255 ) ),
                             Column( "tool_version", TEXT ),
                             Column( "tool_shed", TrimmedString( 255 ) ),
                             Column( "repository_owner", TrimmedString( 255 ) ),
                             Column( "repository_name", TrimmedString( 255 ) ),
                             Column( "guid", TEXT, index=True, unique=True ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        ToolIdGuidMap_table.create()
    except Exception:
        log.exception("Creating tool_id_guid_map table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        ToolIdGuidMap_table.drop()
    except Exception:
        log.exception("Dropping tool_id_guid_map table failed.")
