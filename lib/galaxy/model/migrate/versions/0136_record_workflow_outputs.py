"""
Migration script for collections and workflows connections.
"""
from __future__ import print_function

import datetime
import logging

from collections import OrderedDict

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

from galaxy.model.custom_types import TrimmedString


now = datetime.datetime.utcnow

log = logging.getLogger(__name__)
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
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
    Column("workflow_output_id", Integer, ForeignKey("workflow_output.id")),
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
    Column("workflow_invocation_step_id", Integer, ForeignKey("workflow_invocation_step.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
    Column("output_name", String(255), nullable=True),
)

# workflow_invocation_step_table = Table(
#     "workflow_invocation_step", metadata,
#     Column("id", Integer, primary_key=True),
#     Column("create_time", DateTime, default=now),
#     Column("update_time", DateTime, default=now, onupdate=now),
#     Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True, nullable=False),
#     Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
#     Column("action", JSONType, nullable=True),
#     Column("state", TrimmedString(64), default="new"),
# )

# workflow_invocation_step_job_association_table = Table(
#     "workflow_invocation_step_job_association", metadata,
#     Column("id", Integer, primary_key=True),
#     Column("workflow_invocation_step_id", Integer, ForeignKey("workflow_invocation_step.id"), index=True, nullable=False),
#     Column("order_index", Integer, nullable=True),
#     Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False),
# )

implicit_collection_jobs_table = Table(
    "implicit_collection_jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("populated_state", TrimmedString(64), default='new', nullable=False),
)

# implicit_collection_jobs_history_dataset_collection_association_table = Table(
#    "implicit_collection_jobs_dataset_collection_association", metadata,
#    Column("id", Integer, primary_key=True),
#    Column("history_dataset_collection_association_id", Integer, ForeignKey("history_dataset_collection_association_id.id"), index=True, nullable=False),
# )

implicit_collection_jobs_job_association_table = Table(
    "implicit_collection_jobs_job_association", metadata,
    Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), index=True),
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),  # Consider making this nullable...
    Column("order_index", Integer, nullable=False),
)


def get_new_tables():
    # Normally we define this globally in the file, but we need to delay the
    # reading of existing tables because an existing workflow_invocation_step
    # table exists that we want to recreate.

    tables = OrderedDict()
    # tables["workflow_invocation_step"] = workflow_invocation_step_table
    tables["workflow_invocation_output_dataset_association"] = workflow_invocation_output_dataset_association_table
    tables["workflow_invocation_output_dataset_collection_association"] = workflow_invocation_output_dataset_collection_association_table
    tables["workflow_invocation_step_output_dataset_association"] = workflow_invocation_step_output_dataset_association_table
    tables["workflow_invocation_step_output_dataset_collection_association"] = workflow_invocation_step_output_dataset_collection_association_table
    # tables["workflow_invocation_step_job_association"] = workflow_invocation_step_job_association_table
    tables["implicit_collection_jobs"] = implicit_collection_jobs_table
    # tables["implicit_collection_jobs_history_dataset_collection_association"] = implicit_collection_jobs_history_dataset_collection_association_table
    tables["implicit_collection_jobs_job_association"] = implicit_collection_jobs_job_association_table

    return tables


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)

    metadata.reflect()
    tables = get_new_tables()
    for table in tables.values():
        __create(table)

    def nextval(table, col='id'):
        if migrate_engine.name in ['postgres', 'postgresql']:
            return "nextval('%s_%s_seq')" % (table, col)
        elif migrate_engine.name in ['mysql', 'sqlite']:
            return "null"
        else:
            raise Exception("Unhandled database type")

    # Set default for creation to scheduled, actual mapping has new as default.
    workflow_invocation_step_state_column = Column("state", TrimmedString(64), default="scheduled")
    if migrate_engine.name in ['postgres', 'postgresql']:
        implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), nullable=True)
        job_id_column = Column("job_id", Integer, ForeignKey("job.id"), nullable=True)
    else:
        implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, nullable=True)
        job_id_column = Column("job_id", Integer, nullable=True)
    __add_column(implicit_collection_jobs_id_column, "history_dataset_collection_association", metadata)
    __add_column(job_id_column, "history_dataset_collection_association", metadata)

    implicit_collection_jobs_id_column = Column("implicit_collection_jobs_id", Integer, ForeignKey("implicit_collection_jobs.id"), nullable=True)
    __add_column(implicit_collection_jobs_id_column, "workflow_invocation_step", metadata)
    __add_column(workflow_invocation_step_state_column, "workflow_invocation_step", metadata)

    # TODO: matching drop... steal from 0131


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table(table_name, metadata, autoload=True)
        column.create(table, **kwds)
    except Exception:
        log.exception("Adding column %s failed.", column)


def __drop_column(column_name, table_name, metadata):
    try:
        table = Table(table_name, metadata, autoload=True)
        getattr(table.c, column_name).drop()
    except Exception:
        log.exception("Dropping column %s failed.", column_name)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column("implicit_collection_jobs_id", "history_dataset_collection_association", metadata)
    __drop_column("job_id", "history_dataset_collection_association", metadata)
    __drop_column("implicit_collection_jobs_id", "workflow_invocation_step", metadata)
    __drop_column("state", "workflow_invocation_step", metadata)

    tables = get_new_tables()
    for table in reversed(tables.values()):
        __drop(table)


def __create(table):
    try:
        table.create()
    except Exception:
        log.exception("Creating %s table failed.", table.name)


def __drop(table):
    try:
        table.drop()
    except Exception:
        log.exception("Dropping %s table failed.", table.name)
