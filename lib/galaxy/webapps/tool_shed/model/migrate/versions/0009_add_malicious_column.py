"""
Migration script to add the malicious column to the repository_metadata table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

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
    Repository_metadata_table = Table( "repository_metadata", metadata, autoload=True )
    c = Column( "malicious", Boolean, default=False, index=True )
    try:
        # Create
        c.create( Repository_metadata_table )
        assert c is Repository_metadata_table.c.malicious
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite': 
            default_false = "0"
        elif migrate_engine.name == 'postgres':
            default_false = "false"
        db_session.execute( "UPDATE repository_metadata SET malicious=%s" % default_false )
    except Exception, e:
        print "Adding malicious column to the repository_metadata table failed: %s" % str( e )
        log.debug( "Adding malicious column to the repository_metadata table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    # Drop malicious column from repository_metadata table.
    Repository_metadata_table = Table( "repository_metadata", metadata, autoload=True )
    try:
        Repository_metadata_table.c.malicious.drop()
    except Exception, e:
        print "Dropping column malicious from the repository_metadata table failed: %s" % str( e )
        log.debug( "Dropping column malicious from the repository_metadata table failed: %s" % str( e ) )
