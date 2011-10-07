"""
Migration script to add the long_description and times_downloaded columns to the repository table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

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

def upgrade():
    print __doc__
    metadata.reflect()
    # Create and initialize imported column in job table.
    Repository_table = Table( "repository", metadata, autoload=True )
    c = Column( "long_description" , TEXT )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.long_description
    except Exception, e:
        print "Adding long_description column to the repository table failed: %s" % str( e )
        log.debug( "Adding long_description column to the repository table failed: %s" % str( e ) )

    c = Column( "times_downloaded" , Integer )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.times_downloaded
    except Exception, e:
        print "Adding times_downloaded column to the repository table failed: %s" % str( e )
        log.debug( "Adding times_downloaded column to the repository table failed: %s" % str( e ) )

    cmd = "UPDATE repository SET long_description = ''"
    db_session.execute( cmd )
    cmd = "UPDATE repository SET times_downloaded = 0"
    db_session.execute( cmd )
    
def downgrade():
    metadata.reflect()
    # Drop email_alerts column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.long_description.drop()
    except Exception, e:
        print "Dropping column long_description from the repository table failed: %s" % str( e )
        log.debug( "Dropping column long_description from the repository table failed: %s" % str( e ) )
    try:
        Repository_table.c.times_downloaded.drop()
    except Exception, e:
        print "Dropping column times_downloaded from the repository table failed: %s" % str( e )
        log.debug( "Dropping column times_downloaded from the repository table failed: %s" % str( e ) )
