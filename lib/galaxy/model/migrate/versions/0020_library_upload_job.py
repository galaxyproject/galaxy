"""
This script creates a job_to_output_library_dataset table for allowing library
uploads to run as regular jobs.  To support this, a library_folder_id column is
added to the job table, and library_folder/output_library_datasets relations
are added to the Job object.  An index is also added to the dataset.state
column.
"""
from __future__ import print_function

import logging
import sys

from migrate import ForeignKeyConstraint
from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, String, Table
from sqlalchemy.exc import NoSuchTableError

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()

JobToOutputLibraryDatasetAssociation_table = Table("job_to_output_library_dataset", metadata,
                                                   Column("id", Integer, primary_key=True),
                                                   Column("job_id", Integer, ForeignKey("job.id"), index=True),
                                                   Column("ldda_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True),
                                                   Column("name", String(255)))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    # Load existing tables
    metadata.reflect()
    # Create the job_to_output_library_dataset table
    try:
        JobToOutputLibraryDatasetAssociation_table.create()
    except Exception:
        log.exception("Creating job_to_output_library_dataset table failed.")
    # Create the library_folder_id column
    try:
        Job_table = Table("job", metadata, autoload=True)
    except NoSuchTableError:
        Job_table = None
        log.debug("Failed loading table job")
    if Job_table is not None:
        try:
            col = Column("library_folder_id", Integer, index=True)
            col.create(Job_table, index_name='ix_job_library_folder_id')
            assert col is Job_table.c.library_folder_id
        except Exception:
            log.exception("Adding column 'library_folder_id' to job table failed.")
        try:
            LibraryFolder_table = Table("library_folder", metadata, autoload=True)
        except NoSuchTableError:
            LibraryFolder_table = None
            log.debug("Failed loading table library_folder")
        # Add 1 foreign key constraint to the job table
        if migrate_engine.name != 'sqlite':
            # Sqlite can't alter-table-add-foreign-key
            if Job_table is not None and LibraryFolder_table is not None:
                try:
                    cons = ForeignKeyConstraint([Job_table.c.library_folder_id],
                                                [LibraryFolder_table.c.id],
                                                name='job_library_folder_id_fk')
                    # Create the constraint
                    cons.create()
                except Exception:
                    log.exception("Adding foreign key constraint 'job_library_folder_id_fk' to table 'library_folder' failed.")
    # Create the ix_dataset_state index
    try:
        Dataset_table = Table("dataset", metadata, autoload=True)
    except NoSuchTableError:
        Dataset_table = None
        log.debug("Failed loading table dataset")
    i = Index("ix_dataset_state", Dataset_table.c.state)
    try:
        i.create()
    except Exception:
        log.exception("Adding index 'ix_dataset_state' to dataset table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop the library_folder_id column
    try:
        Job_table = Table("job", metadata, autoload=True)
    except NoSuchTableError:
        Job_table = None
        log.debug("Failed loading table job")
    if Job_table is not None:
        try:
            col = Job_table.c.library_folder_id
            col.drop()
        except Exception:
            log.exception("Dropping column 'library_folder_id' from job table failed.")
    # Drop the job_to_output_library_dataset table
    try:
        JobToOutputLibraryDatasetAssociation_table.drop()
    except Exception:
        log.exception("Dropping job_to_output_library_dataset table failed.")
    # Drop the ix_dataset_state index
    try:
        Dataset_table = Table("dataset", metadata, autoload=True)
    except NoSuchTableError:
        Dataset_table = None
        log.debug("Failed loading table dataset")
    i = Index("ix_dataset_state", Dataset_table.c.state)
    try:
        i.drop()
    except Exception:
        log.exception("Dropping index 'ix_dataset_state' from dataset table failed.")
