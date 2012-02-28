"""
Migration script to create the migrate_tools table.
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

MigrateTools_table = Table( "migrate_tools", metadata,
    Column( "repository_id", TrimmedString( 255 ) ),
    Column( "repository_path", TEXT ),
    Column( "version", Integer ) )

def upgrade():
    print __doc__
    
    metadata.reflect()
    # Create the table.
    try:
        MigrateTools_table.create()
        cmd = "INSERT INTO migrate_tools VALUES ('GalaxyTools', 'lib/galaxy/tool_shed/migrate', %d)" % 1
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Creating migrate_tools table failed: %s" % str( e ) )
        
def downgrade():
    metadata.reflect()
    try:
        MigrateTools_table.drop()
    except Exception, e:
        log.debug( "Dropping migrate_tools table failed: %s" % str( e ) )
