from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exceptions import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, transactional=False ) )


UserAddress_table = Table( "user_address", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "desc", TEXT),
    Column( "name", TrimmedString( 255 ), nullable=False),
    Column( "institution", TrimmedString( 255 )),
    Column( "address", TrimmedString( 255 ), nullable=False),
    Column( "city", TrimmedString( 255 ), nullable=False),
    Column( "state", TrimmedString( 255 ), nullable=False),
    Column( "postal_code", TrimmedString( 255 ), nullable=False),
    Column( "country", TrimmedString( 255 ), nullable=False),
    Column( "phone", TrimmedString( 255 )),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

#RequestState_table = Table('request_state', metadata,
#    Column( "id", Integer, primary_key=True),
#    Column( "create_time", DateTime, default=now ),
#    Column( "update_time", DateTime, default=now, onupdate=now ),
#    Column( "name", TrimmedString( 255 ), nullable=False ),
#    Column( "desc", TEXT ))

def upgrade():
    # Load existing tables
    metadata.reflect()
    
    # Add all of the new tables above
    try:
        UserAddress_table.create()
    except Exception, e:
        log.debug( "Creating user_address table failed: %s" % str( e ) ) 
#    try:
#        RequestState_table.create()
#    except Exception, e:
#        log.debug( "Creating request_state table failed: %s" % str( e ) ) 

    # Add 1 column to the request_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if RequestType_table:
        try:
            col = Column( "deleted", Boolean, index=True, default=False )
            col.create( RequestType_table )
            assert col is RequestType_table.c.deleted
        except Exception, e:
            log.debug( "Adding column 'deleted' to request_type table failed: %s" % ( str( e ) ) )

    # Delete the submitted column
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table request" )
    if Request_table:
        try:
            Request_table.c.submitted.drop()
        except Exception, e:
            log.debug( "Deleting column 'submitted' to request table failed: %s" % ( str( e ) ) )   
        try:
            col = Column( "state", TrimmedString( 255 ), index=True  )
            col.create( Request_table )
            assert col is Request_table.c.state
        except Exception, e:
            log.debug( "Adding column 'state' to request table failed: %s" % ( str( e ) ) )
#
#        # new column which points to the current state in the request_state table
#        try:
#            col = Column( "request_state_id", Integer, index=True  )
#            col.create( Request_table )
#            assert col is Request_table.c.request_state_id
#        except Exception, e:
#            log.debug( "Adding column 'request_state_id' to request table failed: %s" % ( str( e ) ) )
#    # Add 1 foreign key constraint to the form_definition_current table
#    if RequestState_table and Request_table:
#        try:
#            cons = ForeignKeyConstraint( [Request_table.c.request_state_id],
#                                         [RequestState_table.c.id],
#                                         name='request_request_state_id_fk' )
#            # Create the constraint
#            cons.create()
#        except Exception, e:
#            log.debug( "Adding foreign key constraint 'request_request_state_id_fk' to table 'request' failed: %s" % ( str( e ) ) )
 

def downgrade():
    pass


