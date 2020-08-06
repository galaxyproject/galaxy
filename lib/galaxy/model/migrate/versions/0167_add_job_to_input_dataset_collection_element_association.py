"""
Migration script to add a new job_to_input_dataset_collection_element table to track job inputs.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Unicode

log = logging.getLogger(__name__)
metadata = MetaData()

job_to_input_dataset_collection_element_table = Table(
    "job_to_input_dataset_collection_element", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("dataset_collection_element_id", Integer, ForeignKey("dataset_collection_element.id"), index=True),
    Column("name", Unicode(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        job_to_input_dataset_collection_element_table.create()
    except Exception:
        log.exception("Creating job_to_input_dataset_collection_element table failed")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        job_to_input_dataset_collection_element_table.drop()
    except Exception:
        log.exception("Dropping job_to_input_dataset_collection_element table failed")
