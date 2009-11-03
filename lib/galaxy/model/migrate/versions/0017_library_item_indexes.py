"""
This script adds 3 indexes to table columns: library_folder.name,
library_dataset.name, library_dataset_dataset_association.name.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
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
LibraryFolder_table = Table( "library_folder", metadata, autoload=True )
LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
LibraryDataset_table = Table( "library_dataset", metadata, autoload=True )
          
def display_migration_details():
    print "========================================"
    print "This script adds 3 indexes to table columns: library_folder.name,"
    print "library_dataset.name, library_dataset_dataset_association.name."
    print "========================================"
        
def upgrade():
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    # Add 1 index to the library_folder table
    i = Index( 'ix_library_folder_name', LibraryFolder_table.c.name )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_library_folder_name' to library_folder table failed: %s" % ( str( e ) ) )
    # Add 1 index to the library_dataset_dataset_association table
    i = Index( 'ix_library_dataset_dataset_association_name', LibraryDatasetDatasetAssociation_table.c.name )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_library_dataset_dataset_association_name' to library_dataset_dataset_association table failed: %s" % ( str( e ) ) )
    # Add 1 index to the library_dataset table
    i = Index( 'ix_library_dataset_name', LibraryDataset_table.c.name )
    try:
        i.create()
    except Exception, e:
        log.debug( "Adding index 'ix_library_dataset_name' to library_dataset table failed: %s" % ( str( e ) ) )
def downgrade():
    log.debug( "Downgrade is not possible." )
