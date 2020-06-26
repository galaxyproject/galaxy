"""
This script creates a job_to_output_library_dataset table for allowing library
uploads to run as regular jobs.  To support this, a library_folder_id column is
added to the job table, and library_folder/output_library_datasets relations
are added to the Job object.  An index is also added to the dataset.state
column.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table
)

from galaxy.model.migrate.versions.util import (
    add_column,
    add_index,
    create_table,
    drop_column,
    drop_index,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

JobToOutputLibraryDataset_table = Table("job_to_output_library_dataset", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("ldda_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True),
    Column("name", String(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create the job_to_output_library_dataset table
    create_table(JobToOutputLibraryDataset_table)

    # Create the library_folder_id column
    col = Column("library_folder_id", Integer, ForeignKey('library_folder.id', name='job_library_folder_id_fk'), index=True)
    add_column(col, 'job', metadata, index_name='ix_job_library_folder_id')

    # Create the ix_dataset_state index
    add_index('ix_dataset_state', 'dataset', 'state', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the ix_dataset_state index
    drop_index('ix_dataset_state', 'dataset', 'state', metadata)

    # Drop the library_folder_id column
    drop_column('library_folder_id', 'job', metadata)

    # Drop the job_to_output_library_dataset table
    drop_table(JobToOutputLibraryDataset_table)
