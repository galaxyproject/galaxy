"""
Migration script to add the new_repo_alert column to the galaxy_user table.
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
    User_table = Table( "galaxy_user", metadata, autoload=True )
    c = Column( "new_repo_alert", Boolean, default=False, index=True )
    try:
        # Create
        c.create( User_table )
        assert c is User_table.c.new_repo_alert
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite': 
            default_false = "0"
        elif migrate_engine.name == 'postgres':
            default_false = "false"
        db_session.execute( "UPDATE galaxy_user SET new_repo_alert=%s" % default_false )
    except Exception, e:
        print "Adding new_repo_alert column to the galaxy_user table failed: %s" % str( e )
        log.debug( "Adding new_repo_alert column to the galaxy_user table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    # Drop new_repo_alert column from galaxy_user table.
    User_table = Table( "galaxy_user", metadata, autoload=True )
    try:
        User_table.c.new_repo_alert.drop()
    except Exception, e:
        print "Dropping column new_repo_alert from the galaxy_user table failed: %s" % str( e )
        log.debug( "Dropping column new_repo_alert from the galaxy_user table failed: %s" % str( e ) )
