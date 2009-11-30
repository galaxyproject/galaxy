"""
This migration script adds the request_event table and 
removes the state field in the request table
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
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
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def display_migration_details():
    print "========================================"
    print "This migration script adds the request_event table and" 
    print "removes the state field in the request table"
    print "========================================"
    
def localtimestamp():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return "LOCALTIMESTAMP"
   elif migrate_engine.name == 'sqlite':
       return "current_date || ' ' || current_time"
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )
   
def nextval( table, col='id' ):
    if migrate_engine.name == 'postgres':
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )


RequestEvent_table = Table('request_event', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ), 
    Column( "state", TrimmedString( 255 ),  index=True ),
    Column( "comment", TEXT ) )

def upgrade():
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    # Add new request_event table
    try:
        RequestEvent_table.create()
    except Exception, e:
        log.debug( "Creating request_event table failed: %s" % str( e ) )
    # move the current state of all existing requests to the request_event table
    cmd = \
        "INSERT INTO request_event " + \
        "SELECT %s AS id," + \
        "%s AS create_time," + \
        "%s AS update_time," + \
        "request.id AS request_id," + \
        "request.state AS state," + \
        "'%s' AS comment " + \
        "FROM request;" 
    cmd = cmd % ( nextval('request_event'), localtimestamp(), localtimestamp(), 'Imported from request table')
    db_session.execute( cmd )
    
    # Delete the state column
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table request" )
    if Request_table:
        try:
            Request_table.c.state.drop()
        except Exception, e:
            log.debug( "Deleting column 'state' to request table failed: %s" % ( str( e ) ) )   
    
def downgrade():
    pass