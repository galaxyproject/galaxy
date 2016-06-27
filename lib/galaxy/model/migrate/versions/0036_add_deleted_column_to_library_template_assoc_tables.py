"""
Migration script to add a deleted column to the following tables:
library_info_association, library_folder_info_association, library_dataset_dataset_info_association.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()


def get_false_value(migrate_engine):
    if migrate_engine.name == 'sqlite':
        return '0'
    else:
        return 'false'


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    LibraryInfoAssociation_table = Table( "library_info_association", metadata, autoload=True )
    c = Column( "deleted", Boolean, index=True, default=False )
    c.create( LibraryInfoAssociation_table, index_name='ix_library_info_association_deleted')
    assert c is LibraryInfoAssociation_table.c.deleted
    cmd = "UPDATE library_info_association SET deleted = %s" % get_false_value(migrate_engine)
    try:
        migrate_engine.execute( cmd )
    except Exception as e:
        log.debug( "deleted to false in library_info_association failed: %s" % ( str( e ) ) )

    LibraryFolderInfoAssociation_table = Table( "library_folder_info_association", metadata, autoload=True )
    c = Column( "deleted", Boolean, index=True, default=False )
    c.create( LibraryFolderInfoAssociation_table, index_name='ix_library_folder_info_association_deleted')
    assert c is LibraryFolderInfoAssociation_table.c.deleted
    cmd = "UPDATE library_folder_info_association SET deleted = %s" % get_false_value(migrate_engine)
    try:
        migrate_engine.execute( cmd )
    except Exception as e:
        log.debug( "deleted to false in library_folder_info_association failed: %s" % ( str( e ) ) )

    LibraryDatasetDatasetInfoAssociation_table = Table( "library_dataset_dataset_info_association", metadata, autoload=True )
    c = Column( "deleted", Boolean, index=True, default=False )
    c.create( LibraryDatasetDatasetInfoAssociation_table, index_name='ix_library_dataset_dataset_info_association_deleted')
    assert c is LibraryDatasetDatasetInfoAssociation_table.c.deleted
    cmd = "UPDATE library_dataset_dataset_info_association SET deleted = %s" % get_false_value(migrate_engine)
    try:
        migrate_engine.execute( cmd )
    except Exception as e:
        log.debug( "deleted to false in library_dataset_dataset_info_association failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
