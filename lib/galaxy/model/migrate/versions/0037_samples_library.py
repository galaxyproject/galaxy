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

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )


def upgrade():
    print __doc__
    # Load existing tables
    metadata.reflect()
    # retuest_type table
    try:
        RequestType_table = Table( "request_type", metadata, autoload=True )
    except NoSuchTableError:
        RequestType_table = None
        log.debug( "Failed loading table request_type" )
    if RequestType_table:
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
    if Request_table:
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
    if Sample_table:
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
        if Library_table:
            # Add the library_id column in 'sample' table
            try:
                col = Column( "library_id", Integer, index=True )
                col.create( Sample_table )
                assert col is Sample_table.c.library_id
            except Exception, e:
                log.debug( "Adding column 'library_id' to sample table failed: %s" % ( str( e ) ) )
            # add the foreign key constraint
            try:
                cons = ForeignKeyConstraint( [Sample_table.c.library_id],
                                             [Library_table.c.id],
                                             name='sample_library_id_fk' )
                # Create the constraint
                cons.create()
            except Exception, e:
                log.debug( "Adding foreign key constraint 'sample_library_id_fk' to table 'library' failed: %s" % ( str( e ) ) )
        # library_folder table
        try:
            LibraryFolder_table = Table( "library_folder", metadata, autoload=True )
        except NoSuchTableError:
            LibraryFolder_table = None
            log.debug( "Failed loading table library_folder" )
        if LibraryFolder_table:
            # Add the library_id column in 'sample' table
            try:
                col = Column( "folder_id", Integer, index=True )
                col.create( Sample_table )
                assert col is Sample_table.c.folder_id
            except Exception, e:
                log.debug( "Adding column 'folder_id' to sample table failed: %s" % ( str( e ) ) )
            # add the foreign key constraint
            try:
                cons = ForeignKeyConstraint( [Sample_table.c.folder_id],
                                             [LibraryFolder_table.c.id],
                                             name='sample_folder_id_fk' )
                # Create the constraint
                cons.create()
            except Exception, e:
                log.debug( "Adding foreign key constraint 'sample_folder_id_fk' to table 'library_folder' failed: %s" % ( str( e ) ) )


def downgrade():
    pass
