"""
Add UUID column to dataset table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import UUIDType

log = logging.getLogger( __name__ )
dataset_uuid_column = Column( "uuid", UUIDType, nullable=True )


def display_migration_details():
    print("")
    print("This migration adds uuid column to dataset table")


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the uuid colum to the dataset table
    try:
        dataset_table = Table( "dataset", metadata, autoload=True )
        dataset_uuid_column.create( dataset_table )
        assert dataset_uuid_column is dataset_table.c.uuid
    except Exception as e:
        print(str(e))
        log.error( "Adding column 'uuid' to dataset table failed: %s" % str( e ) )
        return


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the dataset table's uuid column.
    try:
        dataset_table = Table( "dataset", metadata, autoload=True )
        dataset_uuid = dataset_table.c.uuid
        dataset_uuid.drop()
    except Exception as e:
        log.debug( "Dropping 'uuid' column from dataset table failed: %s" % ( str( e ) ) )
