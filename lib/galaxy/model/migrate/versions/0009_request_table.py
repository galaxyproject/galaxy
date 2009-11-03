"""
This migration script adds a new column to 2 tables:
1) a new boolean type column named 'submitted' to the 'request' table
2) a new string type column named 'bar_code' to the 'sample' table
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import sys, logging
from galaxy.model.custom_types import *
from sqlalchemy.exc import *

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )

def display_migration_details():
    print "========================================"
    print "This migration script adds a new column to 2 tables:"
    print "1) a new boolean type column named 'submitted' to the 'request' table"
    print "2) a new string type column named 'bar_code' to the 'sample' table"
    print "========================================"

def upgrade():
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    # Add 1 column to the request table
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table request" )
    if Request_table:
        try:
            col = Column( "submitted", Boolean, index=True, default=False )
            col.create( Request_table )
            assert col is Request_table.c.submitted
        except Exception, e:
            log.debug( "Adding column 'submitted' to request table failed: %s" % ( str( e ) ) )
    # Add 1 column to the sample table
    try:
        Sample_table = Table( "sample", metadata, autoload=True )
    except NoSuchTableError:
        Sample_table = None
        log.debug( "Failed loading table sample" )
    if Sample_table:
        try:
            col = Column( "bar_code", TrimmedString( 255 ), index=True )
            col.create( Sample_table )
            assert col is Sample_table.c.bar_code
        except Exception, e:
            log.debug( "Adding column 'bar_code' to sample table failed: %s" % ( str( e ) ) )

def downgrade():
    pass
