"""
Migration script to add the suite column to the tool table.
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
    Tool_table = Table( "tool", metadata, autoload=True )
    c = Column( "suite", Boolean, default=False, index=True )
    try:
        # Create
        c.create( Tool_table )
        assert c is Tool_table.c.suite
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite': 
            default_false = "0"
        elif migrate_engine.name == 'postgres':
            default_false = "false"
        db_session.execute( "UPDATE tool SET suite=%s" % default_false )
    except Exception, e:
        print "Adding suite column to the tool table failed: %s" % str( e )
        log.debug( "Adding suite column to the tool table failed: %s" % str( e ) )
    
def downgrade():
    metadata.reflect()
    # Drop suite column from tool table.
    Tool_table = Table( "tool", metadata, autoload=True )
    try:
        Tool_table.c.suite.drop()
    except Exception, e:
        print "Dropping column suite from the tool table failed: %s" % str( e )
        log.debug( "Dropping column suite from the tool table failed: %s" % str( e ) )
