"""
This migration script removes the library_id & folder_id fields in the 'request' table and
adds the same to the 'sample' table. This also adds a 'datatx' column to request_type table
to store the sequencer login information. Finally, this adds a 'dataset_files' column to
the sample table.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import sys, logging
from galaxy.model.custom_types import *
from sqlalchemy.exc import *
import datetime
now = datetime.datetime.utcnow

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    # Load existing tables
    metadata.reflect()
    # retuest_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if RequestType_table is not None:
        # Add the datatx_info column in 'request_type' table
        try:
            col = Column( "datatx_info", JSONType() )
            col.create( RequestType_table )
            assert col is RequestType_table.c.datatx_info
        except Exception, e:
            log.debug( "Adding column 'datatx_info' to request_type table failed: %s" % ( str( e ) ) )
    # request table
    try:
        Request_table = Table( "request", metadata, autoload=True )
    except NoSuchTableError:
        Request_table = None
        log.debug( "Failed loading table request" )
    if Request_table is not None:
        # Delete library_id & folder_id columns in the table 'request'.
        # if Galaxy is running on sqlite, the delete/recreate the table
        # otherwise remove the specific columns
        if migrate_engine.name == 'sqlite':
            # create a temporary table
            RequestTemp_table = Table( 'request_temp', metadata,
                                        Column( "id", Integer, primary_key=True),
                                        Column( "create_time", DateTime, default=now ),
                                        Column( "update_time", DateTime, default=now, onupdate=now ),
                                        Column( "name", TrimmedString( 255 ), nullable=False ),
                                        Column( "desc", TEXT ),
                                        Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
                                        Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
                                        Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                        Column( "deleted", Boolean, index=True, default=False ) )
            try:
                RequestTemp_table.create()
            except Exception, e:
                log.debug( "Creating request_temp table failed: %s" % str( e ) )
            # insert all the rows from the request table to the request_temp table
            cmd = \
                "INSERT INTO request_temp " + \
                "SELECT id," + \
                    "create_time," + \
                    "update_time," + \
                    "name," + \
                    "desc," + \
                    "form_values_id," + \
                    "request_type_id," + \
                    "user_id," + \
                    "deleted " + \
                "FROM request;"
            migrate_engine.execute( cmd )
            # delete the 'request' table
            try:
                Request_table.drop()
            except Exception, e:
                log.debug( "Dropping request table failed: %s" % str( e ) )
            # rename table request_temp to request
            cmd = "ALTER TABLE request_temp RENAME TO request"
            migrate_engine.execute( cmd )
        else:
            # Delete the library_id column in 'request' table
            try:
                Request_table.c.library_id.drop()
            except Exception, e:
                log.debug( "Deleting column 'library_id' to request table failed: %s" % ( str( e ) ) )
            # Delete the folder_id column in 'request' table
            try:
                Request_table.c.folder_id.drop()
            except Exception, e:
                log.debug( "Deleting column 'folder_id' to request table failed: %s" % ( str( e ) ) )
    # sample table
    try:
        Sample_table = Table( "sample", metadata, autoload=True )
    except NoSuchTableError:
        Sample_table = None
        log.debug( "Failed loading table sample" )
    if Sample_table is not None:
        # Add the dataset_files column in 'sample' table
        try:
            col = Column( "dataset_files", JSONType() )
            col.create( Sample_table )
            assert col is Sample_table.c.dataset_files
        except Exception, e:
            log.debug( "Adding column 'dataset_files' to sample table failed: %s" % ( str( e ) ) )
        # library table
        try:
            Library_table = Table( "library", metadata, autoload=True )
        except NoSuchTableError:
            Library_table = None
            log.debug( "Failed loading table library" )
        if Library_table is not None:
            # Add the library_id column in 'sample' table
            try:
                if migrate_engine.name != 'sqlite':
                    col = Column( "library_id", Integer, ForeignKey( "library.id" ), index=True )
                else:
                    col = Column( "library_id", Integer, index=True )
                col.create( Sample_table, index_name='ix_sample_library_id')
                assert col is Sample_table.c.library_id
            except Exception, e:
                log.debug( "Adding column 'library_id' to sample table failed: %s" % ( str( e ) ) )
        # library_folder table
        try:
            LibraryFolder_table = Table( "library_folder", metadata, autoload=True )
        except NoSuchTableError:
            LibraryFolder_table = None
            log.debug( "Failed loading table library_folder" )
        if LibraryFolder_table is not None:
            # Add the library_id column in 'sample' table
            try:
                if migrate_engine.name != 'sqlite':
                    col = Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True )
                else:
                    col = Column( "folder_id", Integer, index=True )
                col.create( Sample_table, index_name='ix_sample_library_folder_id')
                assert col is Sample_table.c.folder_id
            except Exception, e:
                log.debug( "Adding column 'folder_id' to sample table failed: %s" % ( str( e ) ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
