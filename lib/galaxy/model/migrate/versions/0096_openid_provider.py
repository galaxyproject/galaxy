"""
Migration script to add column to openid table for provider.
Remove any OpenID entries with nonunique GenomeSpace Identifier
"""

BAD_IDENTIFIER = 'https://identity.genomespace.org/identityServer/xrd.jsp'
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import TrimmedString

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    print __doc__
    metadata.reflect()

    try:
        OpenID_table = Table( "galaxy_user_openid", metadata, autoload=True )
        c = Column( "provider", TrimmedString( 255 ) )
        c.create( OpenID_table )
        assert c is OpenID_table.c.provider
    except Exception, e:
        print "Adding provider column to galaxy_user_openid table failed: %s" % str( e )
        log.debug( "Adding provider column to galaxy_user_openid table failed: %s" % str( e ) )
        
    try:
        cmd = "DELETE FROM galaxy_user_openid WHERE openid='%s'" % ( BAD_IDENTIFIER )
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Deleting bad Identifiers from galaxy_user_openid failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        OpenID_table = Table( "galaxy_user_openid", metadata, autoload=True )
        OpenID_table.c.provider.drop()
    except Exception, e:
        print "Dropping provider column from galaxy_user_openid table failed: %s" % str( e )
        log.debug( "Dropping provider column from galaxy_user_openid table failed: %s" % str( e ) )