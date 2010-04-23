"""
Migration script to add the request_type_permissions table.
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

RequestTypePermissions_table = Table( "request_type_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        RequestTypePermissions_table.create()
    except Exception, e:
        log.debug( "Creating request_type_permissions table failed: %s" % str( e ) )

def downgrade():
    pass