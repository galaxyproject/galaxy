"""
This script adds 3 indexes to table columns: library_folder.name,
library_dataset.name, library_dataset_dataset_association.name.
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Index, MetaData, Table

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )
metadata = MetaData()


def display_migration_details():
    print("========================================")
    print("This script adds 3 indexes to table columns: library_folder.name,")
    print("library_dataset.name, library_dataset_dataset_association.name.")
    print("========================================")


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    LibraryFolder_table = Table( "library_folder", metadata, autoload=True )
    LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
    LibraryDataset_table = Table( "library_dataset", metadata, autoload=True )
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    # Add 1 index to the library_folder table
    i = Index( 'ix_library_folder_name', LibraryFolder_table.c.name, mysql_length=200 )
    try:
        i.create()
    except Exception as e:
        log.debug( "Adding index 'ix_library_folder_name' to library_folder table failed: %s" % ( str( e ) ) )
    # Add 1 index to the library_dataset_dataset_association table
    i = Index( 'ix_library_dataset_dataset_association_name', LibraryDatasetDatasetAssociation_table.c.name )
    try:
        i.create()
    except Exception as e:
        log.debug( "Adding index 'ix_library_dataset_dataset_association_name' to library_dataset_dataset_association table failed: %s" % ( str( e ) ) )
    # Add 1 index to the library_dataset table
    i = Index( 'ix_library_dataset_name', LibraryDataset_table.c.name )
    try:
        i.create()
    except Exception as e:
        log.debug( "Adding index 'ix_library_dataset_name' to library_dataset table failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    log.debug( "Downgrade is not possible." )
