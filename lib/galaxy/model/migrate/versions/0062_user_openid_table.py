"""
Migration script to create table for associating sessions and users with
OpenIDs.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Table to add

UserOpenID_table = Table( "galaxy_user_openid", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "openid", TEXT, index=True, unique=True ),
    )
    
def upgrade():
    print __doc__
    metadata.reflect()
    
    # Create galaxy_user_openid table
    try:
        UserOpenID_table.create()
    except Exception, e:
        log.debug( "Creating galaxy_user_openid table failed: %s" % str( e ) )
        
def downgrade():
    metadata.reflect()
    
    # Drop galaxy_user_openid table
    try:
        UserOpenID_table.drop()
    except Exception, e:
        log.debug( "Dropping galaxy_user_openid table failed: %s" % str( e ) )
