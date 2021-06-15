"""
Migration script for workflow step input table.
"""

import logging

from migrate import ForeignKeyConstraint as MigrateForeignKeyConstraint
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    TEXT,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_index,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

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
    Index('ix_workflow_step_input_workflow_step_id_name_unique', "workflow_step_id", "name", unique=True, mysql_length={'name': 200}),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    OldWorkflowStepConnection_table = Table("workflow_step_connection", metadata, autoload=True)
    for fkc in OldWorkflowStepConnection_table.foreign_key_constraints:
        mfkc = MigrateForeignKeyConstraint([_.parent for _ in fkc.elements], [_.column for _ in fkc.elements], name=fkc.name)
        try:
            mfkc.drop()
        except Exception:
            log.exception("Dropping foreign key constraint '%s' from table '%s' failed", mfkc.name, OldWorkflowStepConnection_table)

    for index in OldWorkflowStepConnection_table.indexes:
        drop_index(index, OldWorkflowStepConnection_table)
    OldWorkflowStepConnection_table.rename("workflow_step_connection_preupgrade145")
    # Try to deregister that table to work around some caching problems it seems.
    OldWorkflowStepConnection_table.deregister()
    metadata._remove_table("workflow_step_connection", metadata.schema)
    metadata.reflect()

    NewWorkflowStepConnection_table = Table(
        "workflow_step_connection", metadata,
        Column("id", Integer, primary_key=True),
        Column("output_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
        Column("input_step_input_id", Integer, ForeignKey("workflow_step_input.id"), index=True),
        Column("output_name", TEXT),
        Column("input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
    )
    for table in (WorkflowStepInput_table, NewWorkflowStepConnection_table):
        create_table(table)

    insert_step_inputs_cmd = \
        "INSERT INTO workflow_step_input (workflow_step_id, name) " + \
        "SELECT DISTINCT input_step_id, input_name FROM workflow_step_connection_preupgrade145"
    migrate_engine.execute(insert_step_inputs_cmd)

    insert_step_connections_cmd = \
        "INSERT INTO workflow_step_connection (output_step_id, input_step_input_id, output_name, input_subworkflow_step_id) " + \
        "SELECT wsc.output_step_id, wsi.id, wsc.output_name, wsc.input_subworkflow_step_id " + \
        "FROM workflow_step_connection_preupgrade145 AS wsc JOIN workflow_step_input AS wsi ON wsc.input_step_id = wsi.workflow_step_id AND wsc.input_name = wsi.name ORDER BY wsc.id"
    migrate_engine.execute(insert_step_connections_cmd)
    drop_table(OldWorkflowStepConnection_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

    NewWorkflowStepConnection_table = Table("workflow_step_connection", metadata, autoload=True)
    for fkc in NewWorkflowStepConnection_table.foreign_key_constraints:
        mfkc = MigrateForeignKeyConstraint([_.parent for _ in fkc.elements], [_.column for _ in fkc.elements], name=fkc.name)
        try:
            mfkc.drop()
        except Exception:
            log.exception("Dropping foreign key constraint '%s' from table '%s' failed", mfkc.name, NewWorkflowStepConnection_table)

    for index in NewWorkflowStepConnection_table.indexes:
        drop_index(index, NewWorkflowStepConnection_table)
    NewWorkflowStepConnection_table.rename("workflow_step_connection_predowngrade145")
    # Try to deregister that table to work around some caching problems it seems.
    NewWorkflowStepConnection_table.deregister()
    metadata._remove_table("workflow_step_connection", metadata.schema)
    metadata.reflect()

    OldWorkflowStepConnection_table = Table(
        "workflow_step_connection", metadata,
        Column("id", Integer, primary_key=True),
        Column("output_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
        Column("input_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
        Column("output_name", TEXT),
        Column("input_name", TEXT),
        Column("input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
    )
    create_table(OldWorkflowStepConnection_table)

    insert_step_connections_cmd = \
        "INSERT INTO workflow_step_connection (output_step_id, input_step_id, output_name, input_name, input_subworkflow_step_id) " + \
        "SELECT wsc.output_step_id, wsi.workflow_step_id, wsc.output_name, wsi.name, wsc.input_subworkflow_step_id " + \
        "FROM workflow_step_connection_predowngrade145 AS wsc JOIN workflow_step_input AS wsi ON wsc.input_step_input_id = wsi.id ORDER BY wsc.id"
    migrate_engine.execute(insert_step_connections_cmd)

    for table in (NewWorkflowStepConnection_table, WorkflowStepInput_table):
        drop_table(table)
