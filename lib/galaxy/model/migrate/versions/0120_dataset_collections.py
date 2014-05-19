"""
Migration script for tables related to dataset collections.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

DatasetCollection_table = Table( "dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_type", Unicode(255), nullable=False, ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
)

HistoryDatasetCollectionAssociation_table = Table( "history_dataset_collection_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "hid", Integer ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, default=False ),
    Column( "visible", Boolean, default=True ),
    Column( "copied_from_history_dataset_collection_association_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), nullable=True ),
    Column( "implicit_output_name", Unicode(255), nullable=True ),
)

LibraryDatasetCollectionAssociation_table = Table( "library_dataset_collection_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, default=False ),
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
)

DatasetCollectionElement_table = Table( "dataset_collection_element", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True, nullable=False ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "child_collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True, nullable=True ),
    Column( "element_index", Integer, nullable=False ),
    Column( "element_identifier", Unicode(255), nullable=False ),
)

HistoryDatasetCollectionAnnotationAssociation_table = Table( "history_dataset_collection_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT )
)

LibraryDatasetCollectionAnnotationAssociation_table = Table( "library_dataset_collection_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT )
)

HistoryDatasetCollectionRatingAssociation_table = Table( "history_dataset_collection_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True)
)

LibraryDatasetCollectionRatingAssociation_table = Table( "library_dataset_collection_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True)
)

HistoryDatasetCollectionTagAssociation_table = Table( "history_dataset_collection_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True)
)

LibraryDatasetCollectionTagAssociation_table = Table( "library_dataset_collection_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True)
)

JobToInputDatasetCollectionAssociation_table = Table( "job_to_input_dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) )
)

JobToOutputDatasetCollectionAssociation_table = Table( "job_to_output_dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) )
)

ImplicitlyCreatedDatasetCollectionInput_table = Table( "implicitly_created_dataset_collection_inputs", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "input_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) ) )

# TODO: Find a better name for this column...
HiddenBeneathCollection_column = Column( "hidden_beneath_collection_instance_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), nullable=True )


TABLES = [
    DatasetCollection_table,
    HistoryDatasetCollectionAssociation_table,
    LibraryDatasetCollectionAssociation_table,
    DatasetCollectionElement_table,
    JobToInputDatasetCollectionAssociation_table,
    JobToOutputDatasetCollectionAssociation_table,
    ImplicitlyCreatedDatasetCollectionInput_table,
    HistoryDatasetCollectionAnnotationAssociation_table,
    HistoryDatasetCollectionRatingAssociation_table,
    HistoryDatasetCollectionTagAssociation_table,
    LibraryDatasetCollectionAnnotationAssociation_table,
    LibraryDatasetCollectionRatingAssociation_table,
    LibraryDatasetCollectionTagAssociation_table,
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    for table in TABLES:
        __create(table)

    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        HiddenBeneathCollection_column.create( hda_table )
    except Exception as e:
        print str(e)
        log.exception( "Creating HDA column failed." )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __drop(table)

    try:
        hda_table = Table( "history_dataset_association", metadata, autoload=True )
        hidden_beneath_collection_instance_id_col = hda_table.c.hidden_beneath_collection_instance_id
        hidden_beneath_collection_instance_id_col.drop()
    except Exception as e:
        print str(e)
        log.exception( "Dropping HDA column failed." )


def __create(table):
    try:
        table.create()
    except Exception as e:
        print str(e)
        log.exception("Creating %s table failed: %s" % (table.name, str( e ) ) )


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        print str(e)
        log.exception("Dropping %s table failed: %s" % (table.name, str( e ) ) )
