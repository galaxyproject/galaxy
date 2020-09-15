"""
Migration script for collections and workflows connections.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

workflow_invocation_output_dataset_association_table = Table(
    "workflow_invocation_output_dataset_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("dataset_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
    Column("workflow_output_id", Integer, ForeignKey("workflow_output.id")),
)

workflow_invocation_output_dataset_collection_association_table = Table(
    "workflow_invocation_output_dataset_collection_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id", name='fk_wiodca_wii'), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id", name='fk_wiodca_wsi')),
    Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id", name='fk_wiodca_dci'), index=True),
    Column("workflow_output_id", Integer, ForeignKey("workflow_output.id", name='fk_wiodca_woi')),
)

workflow_invocation_step_output_dataset_association_table = Table(
    "workflow_invocation_step_output_dataset_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_step_id", Integer, ForeignKey("workflow_invocation_step.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
    Column("output_name", String(255), nullable=True),
)

workflow_invocation_step_output_dataset_collection_association_table = Table(
    "workflow_invocation_step_output_dataset_collection_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_step_id", Integer, ForeignKey("workflow_invocation_step.id", name='fk_wisodca_wisi'), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id", name='fk_wisodca_wsi')),
    Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id", name='fk_wisodca_dci'), index=True),
    Column("output_name", String(255), nullable=True),
)

implicit_collection_jobs_table = Table(
    "implicit_collection_jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("populated_state", TrimmedString(64), default='new', nullable=False),
)

implicit_collection_jobs_job_association_table = Table(
    "implicit_collection_jobs_job_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), index=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),  # Consider making this nullable...
    Column("order_index", Integer, nullable=False),
)


def get_new_tables():
    # Normally we define this globally in the file, but we need to delay the
    # reading of existing tables because an existing workflow_invocation_step
    # table exists that we want to recreate.
    return [
        workflow_invocation_output_dataset_association_table,
        workflow_invocation_output_dataset_collection_association_table,
        workflow_invocation_step_output_dataset_association_table,
        workflow_invocation_step_output_dataset_collection_association_table,
        implicit_collection_jobs_table,
        implicit_collection_jobs_job_association_table
    ]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in get_new_tables():
        create_table(table)

    # Set default for creation to scheduled, actual mapping has new as default.
    workflow_invocation_step_state_column = Column("state", TrimmedString(64), default="scheduled")
    if migrate_engine.name in ['postgres', 'postgresql']:
        implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), nullable=True)
        job_id_column = Column("job_id", Integer, ForeignKey("job.id"), nullable=True)
    else:
        implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, nullable=True)
        job_id_column = Column("job_id", Integer, nullable=True)
    dataset_collection_element_count_column = Column("element_count", Integer, nullable=True)

    add_column(implicit_collection_jobs_id_column, "history_dataset_collection_association", metadata)
    add_column(job_id_column, "history_dataset_collection_association", metadata)
    add_column(dataset_collection_element_count_column, "dataset_collection", metadata)

    implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), nullable=True)
    add_column(implicit_collection_jobs_id_column, "workflow_invocation_step", metadata)
    add_column(workflow_invocation_step_state_column, "workflow_invocation_step", metadata)

    cmd = \
        "UPDATE dataset_collection SET element_count = " + \
        "(SELECT (CASE WHEN count(*) > 0 THEN count(*) ELSE 0 END) FROM dataset_collection_element WHERE " + \
        "dataset_collection_element.dataset_collection_id = dataset_collection.id)"
    migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("implicit_collection_jobs_id", "history_dataset_collection_association", metadata)
    drop_column("job_id", "history_dataset_collection_association", metadata)
    drop_column("implicit_collection_jobs_id", "workflow_invocation_step", metadata)
    drop_column("state", "workflow_invocation_step", metadata)
    drop_column("element_count", "dataset_collection", metadata)

    for table in reversed(get_new_tables()):
        drop_table(table)
