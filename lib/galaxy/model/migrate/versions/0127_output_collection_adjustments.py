"""
Migration script updating collections tables for output collections.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, TEXT, Unicode

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

JobToImplicitOutputDatasetCollectionAssociation_table = Table(
    "job_to_implicit_output_dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True ),
    Column( "name", Unicode(255) )
)


TABLES = [
    JobToImplicitOutputDatasetCollectionAssociation_table,
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    for table in TABLES:
        __create(table)

    try:
        dataset_collection_table = Table( "dataset_collection", metadata, autoload=True )
        # need server_default because column in non-null
        populated_state_column = Column( 'populated_state', TrimmedString( 64 ), default='ok', server_default="ok", nullable=False )
        populated_state_column.create( dataset_collection_table )

        populated_message_column = Column( 'populated_state_message', TEXT, nullable=True )
        populated_message_column.create( dataset_collection_table )
    except Exception as e:
        print(str(e))
        log.exception( "Creating dataset collection populated column failed." )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __drop(table)

    try:
        dataset_collection_table = Table( "dataset_collection", metadata, autoload=True )
        populated_state_column = dataset_collection_table.c.populated_state
        populated_state_column.drop()
        populated_message_column = dataset_collection_table.c.populated_state_message
        populated_message_column.drop()
    except Exception as e:
        print(str(e))
        log.exception( "Dropping dataset collection populated_state/ column failed." )


def __create(table):
    try:
        table.create()
    except Exception as e:
        print(str(e))
        log.exception("Creating %s table failed: %s" % (table.name, str( e ) ) )


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        print(str(e))
        log.exception("Dropping %s table failed: %s" % (table.name, str( e ) ) )
