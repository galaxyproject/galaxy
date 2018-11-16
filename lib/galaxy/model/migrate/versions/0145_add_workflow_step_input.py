"""
Migration script for workflow step input table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Table, TEXT

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
metadata = MetaData()


def get_new_tables():

    WorkflowStepInput_table = Table(
        "workflow_step_input", metadata,
        Column("id", Integer, primary_key=True),
        Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
        Column("name", TEXT),
        Column("merge_type", TEXT),
        Column("scatter_type", TEXT),
        Column("value_from", JSONType),
        Column("value_from_type", TEXT),
        Column("default_value", JSONType),
        Column("default_value_set", Boolean, default=False),
        Column("runtime_value", Boolean, default=False),
    )

    WorkflowStepConnection_table = Table(
        "workflow_step_connection", metadata,
        Column("id", Integer, primary_key=True),
        Column("output_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
        Column("input_step_input_id", Integer, ForeignKey("workflow_step_input.id"), index=True),
        Column("output_name", TEXT),
        Column("input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
    )

    return [
        WorkflowStepInput_table, WorkflowStepConnection_table
    ]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    LegacyWorkflowStepConnection_table = Table("workflow_step_connection", metadata, autoload=True)
    for index in LegacyWorkflowStepConnection_table.indexes:
        index.drop()
    LegacyWorkflowStepConnection_table.rename("workflow_step_connection_premigrate145")
    # Try to deregister that table to work around some caching problems it seems.
    LegacyWorkflowStepConnection_table.deregister()
    metadata._remove_table("workflow_step_connection", metadata.schema)

    metadata.reflect()
    tables = get_new_tables()
    for table in tables:
        __create(table)

    insert_step_inputs_cmd = \
        "INSERT INTO workflow_step_input (workflow_step_id, name) " + \
        "SELECT id, input_name FROM workflow_step_connection_premigrate145"

    migrate_engine.execute(insert_step_inputs_cmd)

    # TODO: verify order here.
    insert_step_connections_cmd = \
        "INSERT INTO workflow_step_connection (output_step_id, input_step_input_id, output_name, input_subworkflow_step_id) " + \
        "SELECT wsc.output_step_id, wsi.id, wsc.output_name, wsc.input_subworkflow_step_id " + \
        "FROM workflow_step_connection_premigrate145 AS wsc LEFT OUTER JOIN workflow_step_input AS wsi ON wsc.input_step_id = wsi.workflow_step_id AND wsc.input_name = wsi.name ORDER BY wsc.id"

    migrate_engine.execute(insert_step_connections_cmd)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

    tables = get_new_tables()
    for table in tables:
        __drop(table)

    metadata._remove_table("workflow_step_connection", metadata.schema)
    metadata.reflect()

    # Drop new workflow invocation step and job association table and restore legacy data.
    LegacyWorkflowStepConnection_table = Table("workflow_step_connection_premigrate145", metadata, autoload=True)
    LegacyWorkflowStepConnection_table.rename("workflow_step_connection")


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
