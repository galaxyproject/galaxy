from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import sys, logging
from galaxy.model.custom_types import *

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )


def upgrade():
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