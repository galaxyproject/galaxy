from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *
import datetime
now = datetime.datetime.utcnow
import sys, logging
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def display_migration_details():
    print "========================================"
    print """This script creates a request.folder_id column which is a foreign
key to the library_folder table. This also adds a 'type' and 'layout' column
to the form_definition table.""" 
    print "========================================"

def upgrade():
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    # Create the folder_id column
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table request" )
    if Request_table:
        try:
            col = Column( "folder_id", Integer, index=True )
            col.create( Request_table )
            assert col is Request_table.c.folder_id
        except Exception, e:
            log.debug( "Adding column 'folder_id' to request table failed: %s" % ( str( e ) ) )
        try:
            LibraryFolder_table = Table( "library_folder", metadata, autoload=True )
        except NoSuchTableError:
            LibraryFolder_table = None
            log.debug( "Failed loading table library_folder" )
        # Add 1 foreign key constraint to the library_folder table
        if Request_table and LibraryFolder_table:
            try:
                cons = ForeignKeyConstraint( [Request_table.c.folder_id],
                                             [LibraryFolder_table.c.id],
                                             name='request_folder_id_fk' )
                # Create the constraint
                cons.create()
            except Exception, e:
                log.debug( "Adding foreign key constraint 'request_folder_id_fk' to table 'library_folder' failed: %s" % ( str( e ) ) )
    # Create the type column in form_definition
    try:
        FormDefinition_table = Table( "form_definition", metadata, autoload=True )
    except NoSuchTableError:
        FormDefinition_table = None
        log.debug( "Failed loading table form_definition" )
    if FormDefinition_table:
        try:
            col = Column( "type", TrimmedString( 255 ), index=True )
            col.create( FormDefinition_table )
            assert col is FormDefinition_table.c.type
        except Exception, e:
            log.debug( "Adding column 'type' to form_definition table failed: %s" % ( str( e ) ) )
        try:
            col = Column( "layout", JSONType()) 
            col.create( FormDefinition_table )
            assert col is FormDefinition_table.c.layout
        except Exception, e:
            log.debug( "Adding column 'layout' to form_definition table failed: %s" % ( str( e ) ) )


def downgrade():
    pass
