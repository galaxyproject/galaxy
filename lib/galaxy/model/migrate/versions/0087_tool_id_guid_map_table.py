"""
Migration script to create the tool_id_guid_map table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

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

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        ToolIdGuidMap_table.create()
    except Exception, e:
        log.debug( "Creating tool_id_guid_map table failed: %s" % str( e ) )
        
def downgrade():
    metadata.reflect()
    try:
        ToolIdGuidMap_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_id_guid_map table failed: %s" % str( e ) )
