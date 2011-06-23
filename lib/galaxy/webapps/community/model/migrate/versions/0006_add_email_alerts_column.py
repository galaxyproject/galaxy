"""
Migration script to add the email_alerts column to the repository table.
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
    c = Column( "email_alerts", JSONType, nullable=True )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.email_alerts
    except Exception, e:
        print "Adding email_alerts column to the repository table failed: %s" % str( e )
        log.debug( "Adding email_alerts column to the repository table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    # Drop email_alerts column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.email_alerts.drop()
    except Exception, e:
        print "Dropping column email_alerts from the repository table failed: %s" % str( e )
        log.debug( "Dropping column email_alerts from the repository table failed: %s" % str( e ) )
