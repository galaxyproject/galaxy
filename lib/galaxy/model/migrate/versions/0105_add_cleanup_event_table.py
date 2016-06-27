"""
Migration script to add the cleanup_event* tables.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

# New table to log cleanup events
CleanupEvent_table = Table( "cleanup_event", metadata,
                            Column( "id", Integer, primary_key=True ),
                            Column( "create_time", DateTime, default=now ),
                            Column( "message", TrimmedString( 1024 ) ) )

CleanupEventDatasetAssociation_table = Table( "cleanup_event_dataset_association", metadata,
                                              Column( "id", Integer, primary_key=True ),
                                              Column( "create_time", DateTime, default=now ),
                                              Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                              Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ) )

CleanupEventMetadataFileAssociation_table = Table( "cleanup_event_metadata_file_association", metadata,
                                                   Column( "id", Integer, primary_key=True ),
                                                   Column( "create_time", DateTime, default=now ),
                                                   Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                   Column( "metadata_file_id", Integer, ForeignKey( "metadata_file.id" ), index=True ) )

CleanupEventHistoryAssociation_table = Table( "cleanup_event_history_association", metadata,
                                              Column( "id", Integer, primary_key=True ),
                                              Column( "create_time", DateTime, default=now ),
                                              Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                              Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ) )

CleanupEventHistoryDatasetAssociationAssociation_table = Table( "cleanup_event_hda_association", metadata,
                                                                Column( "id", Integer, primary_key=True ),
                                                                Column( "create_time", DateTime, default=now ),
                                                                Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                                Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ) )

CleanupEventLibraryAssociation_table = Table( "cleanup_event_library_association", metadata,
                                              Column( "id", Integer, primary_key=True ),
                                              Column( "create_time", DateTime, default=now ),
                                              Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                              Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ) )

CleanupEventLibraryFolderAssociation_table = Table( "cleanup_event_library_folder_association", metadata,
                                                    Column( "id", Integer, primary_key=True ),
                                                    Column( "create_time", DateTime, default=now ),
                                                    Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ) )

CleanupEventLibraryDatasetAssociation_table = Table( "cleanup_event_library_dataset_association", metadata,
                                                     Column( "id", Integer, primary_key=True ),
                                                     Column( "create_time", DateTime, default=now ),
                                                     Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                     Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), index=True ) )

CleanupEventLibraryDatasetDatasetAssociationAssociation_table = Table( "cleanup_event_ldda_association", metadata,
                                                                       Column( "id", Integer, primary_key=True ),
                                                                       Column( "create_time", DateTime, default=now ),
                                                                       Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                                       Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ) )

CleanupEventImplicitlyConvertedDatasetAssociationAssociation_table = Table( "cleanup_event_icda_association", metadata,
                                                                            Column( "id", Integer, primary_key=True ),
                                                                            Column( "create_time", DateTime, default=now ),
                                                                            Column( "cleanup_event_id", Integer, ForeignKey( "cleanup_event.id" ), index=True, nullable=True ),
                                                                            Column( "icda_id", Integer, ForeignKey( "implicitly_converted_dataset_association.id" ), index=True ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        CleanupEvent_table.create()
        CleanupEventDatasetAssociation_table.create()
        CleanupEventMetadataFileAssociation_table.create()
        CleanupEventHistoryAssociation_table.create()
        CleanupEventHistoryDatasetAssociationAssociation_table.create()
        CleanupEventLibraryAssociation_table.create()
        CleanupEventLibraryFolderAssociation_table.create()
        CleanupEventLibraryDatasetAssociation_table.create()
        CleanupEventLibraryDatasetDatasetAssociationAssociation_table.create()
        CleanupEventImplicitlyConvertedDatasetAssociationAssociation_table.create()
    except Exception as e:
        log.debug( "Creating table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        CleanupEventImplicitlyConvertedDatasetAssociationAssociation_table.drop()
        CleanupEventLibraryDatasetDatasetAssociationAssociation_table.drop()
        CleanupEventLibraryDatasetAssociation_table.drop()
        CleanupEventLibraryFolderAssociation_table.drop()
        CleanupEventLibraryAssociation_table.drop()
        CleanupEventHistoryDatasetAssociationAssociation_table.drop()
        CleanupEventHistoryAssociation_table.drop()
        CleanupEventMetadataFileAssociation_table.drop()
        CleanupEventDatasetAssociation_table.drop()
        CleanupEvent_table.drop()
    except Exception as e:
        log.debug( "Dropping table failed: %s" % str( e ) )
