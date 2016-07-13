"""
Migration script to add the tool_dependency table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

# New table to store information about cloned tool shed repositories.
ToolDependency_table = Table( "tool_dependency", metadata,
                              Column( "id", Integer, primary_key=True ),
                              Column( "create_time", DateTime, default=now ),
                              Column( "update_time", DateTime, default=now, onupdate=now ),
                              Column( "tool_shed_repository_id", Integer, ForeignKey( "tool_shed_repository.id" ), index=True, nullable=False ),
                              Column( "installed_changeset_revision", TrimmedString( 255 ) ),
                              Column( "name", TrimmedString( 255 ) ),
                              Column( "version", TrimmedString( 40 ) ),
                              Column( "type", TrimmedString( 40 ) ),
                              Column( "uninstalled", Boolean, default=False ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        ToolDependency_table.create()
    except Exception as e:
        log.debug( "Creating tool_dependency table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        ToolDependency_table.drop()
    except Exception as e:
        log.debug( "Dropping tool_dependency table failed: %s" % str( e ) )
