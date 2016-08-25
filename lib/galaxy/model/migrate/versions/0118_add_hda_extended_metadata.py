"""
Add link from history_dataset_association to the extended_metadata table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()
extended_metadata_hda_col = Column( "extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), nullable=True )


def display_migration_details():
    print("This migration script adds a ExtendedMetadata links to HistoryDatasetAssociation tables")


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        extended_metadata_hda_col.create( hda_table )
        assert extended_metadata_hda_col is hda_table.c.extended_metadata_id
    except Exception as e:
        print(str(e))
        log.error( "Adding column 'extended_metadata_id' to history_dataset_association table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the HDA table's extended metadata ID column.
    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        extended_metadata_id = hda_table.c.extended_metadata_id
        extended_metadata_id.drop()
    except Exception as e:
        log.debug( "Dropping 'extended_metadata_id' column from history_dataset_association table failed: %s" % ( str( e ) ) )
