"""
Migration script to support subworkflows and workflow request input parameters
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Index, Integer, MetaData, Table

from galaxy.model.custom_types import JSONType, TrimmedString, UUIDType

log = logging.getLogger( __name__ )
metadata = MetaData()

WorkflowInvocationToSubworkflowInvocationAssociation_table = Table(
    "workflow_invocation_to_subworkflow_invocation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_invocation_id", Integer ),
    Column( "subworkflow_invocation_id", Integer ),
    Column( "workflow_step_id", Integer ),
    ForeignKeyConstraint(['workflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfi_swi_wfi'),
    ForeignKeyConstraint(['subworkflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfi_swi_swi'),
    ForeignKeyConstraint(['workflow_step_id'], ['workflow_step.id'], name='fk_wfi_swi_ws')
)

WorkflowRequestInputStepParameter_table = Table(
    "workflow_request_input_step_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_invocation_id", Integer ),
    Column( "workflow_step_id", Integer ),
    Column( "parameter_value", JSONType ),
    ForeignKeyConstraint(['workflow_invocation_id'], ['workflow_invocation.id'], name='fk_wfreq_isp_wfi'),
    ForeignKeyConstraint(['workflow_step_id'], ['workflow_step.id'], name='fk_wfreq_isp_ws')
)

TABLES = [
    WorkflowInvocationToSubworkflowInvocationAssociation_table,
    WorkflowRequestInputStepParameter_table,
]

INDEXES = [
    Index( "ix_wfinv_swfinv_wfi", WorkflowInvocationToSubworkflowInvocationAssociation_table.c.workflow_invocation_id),
    Index( "ix_wfinv_swfinv_swfi", WorkflowInvocationToSubworkflowInvocationAssociation_table.c.subworkflow_invocation_id),
    Index( "ix_wfreq_inputstep_wfi", WorkflowRequestInputStepParameter_table.c.workflow_invocation_id)
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    if migrate_engine.name in ['postgres', 'postgresql']:
        subworkflow_id_column = Column( "subworkflow_id", Integer, ForeignKey("workflow.id"), nullable=True )
        input_subworkflow_step_id_column = Column( "input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), nullable=True )
        parent_workflow_id_column = Column( "parent_workflow_id", Integer, ForeignKey("workflow.id"), nullable=True )
    else:
        subworkflow_id_column = Column( "subworkflow_id", Integer, nullable=True )
        input_subworkflow_step_id_column = Column( "input_subworkflow_step_id", Integer, nullable=True )
        parent_workflow_id_column = Column( "parent_workflow_id", Integer, nullable=True )
    __add_column( subworkflow_id_column, "workflow_step", metadata )
    __add_column( input_subworkflow_step_id_column, "workflow_step_connection", metadata )
    __add_column( parent_workflow_id_column, "workflow", metadata )
    workflow_output_label_column = Column( "label", TrimmedString(255) )
    workflow_output_uuid_column = Column( "uuid", UUIDType, nullable=True )
    __add_column( workflow_output_label_column, "workflow_output", metadata )
    __add_column( workflow_output_uuid_column, "workflow_output", metadata )

    # Make stored_workflow_id nullable, since now workflows can belong to either
    # a stored workflow or a parent workflow.
    __alter_column("workflow", "stored_workflow_id", metadata, nullable=True)

    for table in TABLES:
        # Indexes are automatically created when the tables are.
        __create(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column( "subworkflow_id", "workflow_step", metadata )
    __drop_column( "parent_workflow_id", "workflow", metadata )

    __drop_column( "input_subworkflow_step_id", "workflow_step_connection", metadata )

    __drop_column( "label", "workflow_output", metadata )
    __drop_column( "uuid", "workflow_output", metadata )

    for table in TABLES:
        __drop(table)


def __alter_column(table_name, column_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).alter(**kwds)
    except Exception:
        log.exception("Adding column %s failed." % column_name)


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception:
        log.exception("Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception:
        log.exception("Dropping column %s failed." % column_name)


def __create(table):
    try:
        table.create()
    except Exception:
        log.exception("Creating %s table failed." % table.name)


def __drop(table):
    try:
        table.drop()
    except Exception:
        log.exception("Dropping %s table failed." % table.name)
