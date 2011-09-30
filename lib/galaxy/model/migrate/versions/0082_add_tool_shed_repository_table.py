"""
Migration script to add the tool_shed_repository table.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import sys, logging
from galaxy.model.custom_types import *
from sqlalchemy.exc import *
import datetime
now = datetime.datetime.utcnow

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )

# New table to store information about cloned tool shed repositories.
ToolShedRepository_table = Table( "tool_shed_repository", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "tool_shed", TrimmedString( 255 ), index=True ),
    Column( "name", TrimmedString( 255 ), index=True ),
    Column( "description" , TEXT ),
    Column( "owner", TrimmedString( 255 ), index=True ),
    Column( "changeset_revision", TrimmedString( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        ToolShedRepository_table.create()
    except Exception, e:
        log.debug( "Creating tool_shed_repository table failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        ToolShedRepository_table.drop()
    except Exception, e:
        log.debug( "Dropping tool_shed_repository table failed: %s" % str( e ) )
