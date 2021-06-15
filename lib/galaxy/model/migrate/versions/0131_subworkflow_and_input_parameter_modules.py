"""
Migration script to support subworkflows and workflow request input parameters
"""

import logging

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Index, Integer, MetaData, Table

from galaxy.model.custom_types import JSONType, TrimmedString, UUIDType
from galaxy.model.migrate.versions.util import add_column, alter_column, create_table, drop_column, drop_table

log = logging.getLogger(__name__)
metadata = MetaData()

WorkflowInvocationToSubworkflowInvocationAssociation_table = Table(
    "workflow_invocation_to_subworkflow_invocation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer),
    Column("subworkflow_invocation_id", Integer),
    Column("workflow_step_id", Integer),
    ForeignKeyConstraint(['workflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfi_swi_wfi'),
    ForeignKeyConstraint(['subworkflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfi_swi_swi'),
    ForeignKeyConstraint(['workflow_step_id'], ['workflow_step.id'], name='fk_wfi_swi_ws')
)

WorkflowRequestInputStepParameter_table = Table(
    "workflow_request_input_step_parameter", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer),
    Column("workflow_step_id", Integer),
    Column("parameter_value", JSONType),
    ForeignKeyConstraint(['workflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfreq_isp_wfi'),
    ForeignKeyConstraint(['workflow_step_id'], ['workflow_step.id'], name='fk_wfreq_isp_ws')
)

TABLES = [
    WorkflowInvocationToSubworkflowInvocationAssociation_table,
    WorkflowRequestInputStepParameter_table,
]

INDEXES = [
    Index("ix_wfinv_swfinv_wfi", WorkflowInvocationToSubworkflowInvocationAssociation_table.c.workflow_invocation_id),
    Index("ix_wfinv_swfinv_swfi", WorkflowInvocationToSubworkflowInvocationAssociation_table.c.subworkflow_invocation_id),
    Index("ix_wfreq_inputstep_wfi", WorkflowRequestInputStepParameter_table.c.workflow_invocation_id)
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    if migrate_engine.name in ['postgres', 'postgresql']:
        subworkflow_id_column = Column("subworkflow_id", Integer, ForeignKey("workflow.id"), nullable=True)
        input_subworkflow_step_id_column = Column("input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), nullable=True)
        parent_workflow_id_column = Column("parent_workflow_id", Integer, ForeignKey("workflow.id"), nullable=True)
    else:
        subworkflow_id_column = Column("subworkflow_id", Integer, nullable=True)
        input_subworkflow_step_id_column = Column("input_subworkflow_step_id", Integer, nullable=True)
        parent_workflow_id_column = Column("parent_workflow_id", Integer, nullable=True)
    add_column(subworkflow_id_column, "workflow_step", metadata)
    add_column(input_subworkflow_step_id_column, "workflow_step_connection", metadata)
    add_column(parent_workflow_id_column, "workflow", metadata)
    workflow_output_label_column = Column("label", TrimmedString(255))
    workflow_output_uuid_column = Column("uuid", UUIDType, nullable=True)
    add_column(workflow_output_label_column, "workflow_output", metadata)
    add_column(workflow_output_uuid_column, "workflow_output", metadata)

    # Make stored_workflow_id nullable, since now workflows can belong to either
    # a stored workflow or a parent workflow.
    alter_column("stored_workflow_id", "workflow", metadata, nullable=True)

    for table in TABLES:
        # Indexes are automatically created when the tables are.
        create_table(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("subworkflow_id", "workflow_step", metadata)
    drop_column("parent_workflow_id", "workflow", metadata)

    drop_column("input_subworkflow_step_id", "workflow_step_connection", metadata)

    drop_column("label", "workflow_output", metadata)
    drop_column("uuid", "workflow_output", metadata)

    for table in TABLES:
        drop_table(table)
