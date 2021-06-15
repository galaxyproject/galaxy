"""
Migration script for tables related to dataset collections.
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT,
    Unicode
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

DatasetCollection_table = Table("dataset_collection", metadata,
                                Column("id", Integer, primary_key=True),
                                Column("collection_type", Unicode(255), nullable=False, ),
                                Column("create_time", DateTime, default=now),
                                Column("update_time", DateTime, default=now, onupdate=now))

HistoryDatasetCollectionAssociation_table = Table("history_dataset_collection_association", metadata,
                                                  Column("id", Integer, primary_key=True),
                                                  Column("collection_id", Integer, ForeignKey("dataset_collection.id"), index=True),
                                                  Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                                  Column("hid", Integer),
                                                  Column("name", TrimmedString(255)),
                                                  Column("deleted", Boolean, default=False),
                                                  Column("visible", Boolean, default=True),
                                                  Column("copied_from_history_dataset_collection_association_id", Integer, ForeignKey("history_dataset_collection_association.id"), nullable=True),
                                                  Column("implicit_output_name", Unicode(255), nullable=True))

LibraryDatasetCollectionAssociation_table = Table("library_dataset_collection_association", metadata,
                                                  Column("id", Integer, primary_key=True),
                                                  Column("collection_id", Integer, ForeignKey("dataset_collection.id"), index=True),
                                                  Column("name", TrimmedString(255)),
                                                  Column("deleted", Boolean, default=False),
                                                  Column("folder_id", Integer, ForeignKey("library_folder.id"), index=True))

DatasetCollectionElement_table = Table("dataset_collection_element", metadata,
                                       Column("id", Integer, primary_key=True),
                                       Column("dataset_collection_id", Integer, ForeignKey("dataset_collection.id"), index=True, nullable=False),
                                       Column("hda_id", Integer, ForeignKey("history_dataset_association.id"), index=True, nullable=True),
                                       Column("ldda_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True),
                                       Column("child_collection_id", Integer, ForeignKey("dataset_collection.id"), index=True, nullable=True),
                                       Column("element_index", Integer, nullable=False),
                                       Column("element_identifier", Unicode(255), nullable=False))

HistoryDatasetCollectionAnnotationAssociation_table = Table("history_dataset_collection_annotation_association", metadata,
                                                            Column("id", Integer, primary_key=True),
                                                            Column("history_dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                            Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                            Column("annotation", TEXT))

LibraryDatasetCollectionAnnotationAssociation_table = Table("library_dataset_collection_annotation_association", metadata,
                                                            Column("id", Integer, primary_key=True),
                                                            Column("library_dataset_collection_id", Integer, ForeignKey("library_dataset_collection_association.id"), index=True),
                                                            Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                            Column("annotation", TEXT))

HistoryDatasetCollectionRatingAssociation_table = Table("history_dataset_collection_rating_association", metadata,
                                                        Column("id", Integer, primary_key=True),
                                                        Column("history_dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                        Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                        Column("rating", Integer, index=True))

LibraryDatasetCollectionRatingAssociation_table = Table("library_dataset_collection_rating_association", metadata,
                                                        Column("id", Integer, primary_key=True),
                                                        Column("library_dataset_collection_id", Integer, ForeignKey("library_dataset_collection_association.id"), index=True),
                                                        Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                        Column("rating", Integer, index=True))

HistoryDatasetCollectionTagAssociation_table = Table("history_dataset_collection_tag_association", metadata,
                                                     Column("id", Integer, primary_key=True),
                                                     Column("history_dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                     Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                                     Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                     Column("user_tname", Unicode(255), index=True),
                                                     Column("value", Unicode(255), index=True),
                                                     Column("user_value", Unicode(255), index=True))

LibraryDatasetCollectionTagAssociation_table = Table("library_dataset_collection_tag_association", metadata,
                                                     Column("id", Integer, primary_key=True),
                                                     Column("library_dataset_collection_id", Integer, ForeignKey("library_dataset_collection_association.id"), index=True),
                                                     Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                                     Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                     Column("user_tname", Unicode(255), index=True),
                                                     Column("value", Unicode(255), index=True),
                                                     Column("user_value", Unicode(255), index=True))

JobToInputDatasetCollectionAssociation_table = Table("job_to_input_dataset_collection", metadata,
                                                     Column("id", Integer, primary_key=True),
                                                     Column("job_id", Integer, ForeignKey("job.id"), index=True),
                                                     Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                     Column("name", Unicode(255)))

JobToOutputDatasetCollectionAssociation_table = Table("job_to_output_dataset_collection", metadata,
                                                      Column("id", Integer, primary_key=True),
                                                      Column("job_id", Integer, ForeignKey("job.id"), index=True),
                                                      Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                      Column("name", Unicode(255)))

ImplicitlyCreatedDatasetCollectionInput_table = Table("implicitly_created_dataset_collection_inputs", metadata,
                                                      Column("id", Integer, primary_key=True),
                                                      Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                      Column("input_dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
                                                      Column("name", Unicode(255)))


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
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)

    # TODO: Find a better name for this column...
    HiddenBeneathCollection_column = Column("hidden_beneath_collection_instance_id", Integer, ForeignKey("history_dataset_collection_association.id"), nullable=True)
    add_column(HiddenBeneathCollection_column, 'history_dataset_association', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('hidden_beneath_collection_instance_id', 'history_dataset_association', metadata)

    for table in reversed(TABLES):
        drop_table(table)
