"""
Migration script for workflow request tables.
"""
from __future__ import print_function

import datetime
import logging

from collections import OrderedDict

from migrate.changeset.constraint import ForeignKeyConstraint
from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table

from galaxy.model.custom_types import JSONType, TrimmedString


now = datetime.datetime.utcnow

log = logging.getLogger(__name__)
metadata = MetaData()


def get_new_tables():
    # Normally we define this globally in the file, but we need to delay the
    # reading of existing tables because an existing workflow_invocation_step
    # table exists that we want to recreate.

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

    workflow_invocation_step_table = Table(
        "workflow_invocation_step", metadata,
        Column("id", Integer, primary_key=True),
        Column("create_time", DateTime, default=now),
        Column("update_time", DateTime, default=now, onupdate=now),
        Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True, nullable=False),
        Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
        Column("action", JSONType, nullable=True),
        Column("state", TrimmedString(64), default="new"),
    )

    workflow_invocation_step_job_association_table = Table(
        "workflow_invocation_step_job_association", metadata,
        Column("id", Integer, primary_key=True),
        Column("workflow_invocation_step_id", Integer, ForeignKey("workflow_invocation_step.id"), index=True, nullable=False),
        Column("order_index", Integer, nullable=True),
        Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=False),
    )

    tables = OrderedDict()
    tables["workflow_invocation_step"] = workflow_invocation_step_table
    tables["workflow_invocation_output_dataset_association"] = workflow_invocation_output_dataset_association_table
    tables["workflow_invocation_output_dataset_collection_association"] = workflow_invocation_output_dataset_collection_association_table
    tables["workflow_invocation_step_output_dataset_association"] = workflow_invocation_step_output_dataset_association_table
    tables["workflow_invocation_step_output_dataset_collection_association"] = workflow_invocation_step_output_dataset_collection_association_table
    tables["workflow_invocation_step_job_association"] = workflow_invocation_step_job_association_table

    return tables


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)

    LegacyWorkflowInvocationStep_table = Table("workflow_invocation_step", metadata, autoload=True)
    ExistingWorkflowInvocation_table = Table("workflow_invocation", metadata, autoload=True)

    cons = ForeignKeyConstraint([LegacyWorkflowInvocationStep_table.c.workflow_invocation_id], [ExistingWorkflowInvocation_table.c.id])
    cons.drop()

    for index in LegacyWorkflowInvocationStep_table.indexes:
        index.drop()

    LegacyWorkflowInvocationStep_table.rename("workflow_invocation_step_premigrate135")
    # Try to deregister that workflow_invocation_step to work around some caching problems
    # it seems.
    LegacyWorkflowInvocationStep_table.deregister()
    metadata._remove_table("workflow_invocation_step", metadata.schema)

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

    # Skips action - since I can't aggregate (sql needs a RANDOM(col)) that and it is only used by optional
    # beta extensions.
    cmd = \
        "INSERT INTO workflow_invocation_step " + \
        "(id, create_time, update_time, workflow_invocation_id, workflow_step_id, action, state)" + \
        "SELECT " + \
        nextval('workflow_invocation_step') + " AS id, " \
        "MIN(create_time) AS create_time, " + \
        "MAX(update_time) AS update_time, " + \
        "workflow_invocation_step_premigrate135.workflow_invocation_id AS workflow_invocation_id, " +\
        "workflow_invocation_step_premigrate135.workflow_step_id AS workflow_step_id, " + \
        "NULL AS action, " + \
        "'scheduled' AS state " + \
        "FROM workflow_invocation_step_premigrate135 " + \
        "WHERE workflow_invocation_step_premigrate135.workflow_step_id IS NOT NULL AND workflow_invocation_step_premigrate135.workflow_invocation_id IS NOT NULL " +\
        "GROUP BY workflow_invocation_step_premigrate135.workflow_invocation_id, workflow_invocation_step_premigrate135.workflow_step_id " + \
        ""
    migrate_engine.execute(cmd)

    cmd = \
        "INSERT INTO workflow_invocation_step_job_association " + \
        "(id, workflow_invocation_step_id, order_index, job_id) " + \
        "SELECT " + \
        nextval('workflow_invocation_step_job_association') + " AS id, " \
        "workflow_invocation_step.id AS workflow_invocation_step_id, " + \
        "NULL AS order_index, " + \
        "job_id AS job_id " + \
        "FROM workflow_invocation_step_premigrate135 " + \
        "LEFT JOIN workflow_invocation_step on (" + \
        "  workflow_invocation_step.workflow_invocation_id = workflow_invocation_step_premigrate135.workflow_invocation_id " + \
        "  AND workflow_invocation_step.workflow_step_id = workflow_invocation_step_premigrate135.workflow_step_id" + \
        ") " + \
        "WHERE job_id is not NULL "
    migrate_engine.execute(cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    tables = get_new_tables()
    for table in tables.values():
        __drop(table)

    # Drop new workflow invocation step and job association table and restore legacy data.
    LegacyWorkflowInvocationStep_table = Table("workflow_invocation_step_premigrate135", metadata, autoload=True)
    LegacyWorkflowInvocationStep_table.rename("workflow_invocation_step")


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
