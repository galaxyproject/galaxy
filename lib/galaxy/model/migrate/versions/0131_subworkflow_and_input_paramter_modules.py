"""
Migration script to support subworkflows and workflow request input parameters
"""
import datetime
import logging

from sqlalchemy import Column, Integer, ForeignKey, MetaData, Table

from galaxy.model.custom_types import TrimmedString, UUIDType, JSONType

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

WorkflowInvocationToSubworkflowInvocationAssociation_table = Table(
    "workflow_invocation_to_subworkflow_invocation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True ),
    Column( "subworkflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
)

WorkflowRequestInputStepParmeter_table = Table(
    "workflow_request_input_step_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
    Column( "parameter_value", JSONType ),
)

TABLES = [
    WorkflowInvocationToSubworkflowInvocationAssociation_table,
    WorkflowRequestInputStepParmeter_table,
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    subworkflow_id_column = Column( "subworkflow_id", Integer, ForeignKey("workflow.id"), nullable=True )
    __add_column( subworkflow_id_column, "workflow_step", metadata )

    input_subworkflow_step_id_column = Column( "input_subworkflow_step_id", Integer, ForeignKey("workflow_step.id"), nullable=True )
    __add_column( input_subworkflow_step_id_column, "workflow_step_connection", metadata )

    parent_workflow_id_column = Column( "parent_workflow_id", Integer, ForeignKey("workflow.id"), nullable=True )
    __add_column( parent_workflow_id_column, "workflow", metadata )

    workflow_output_label_column = Column( "label", TrimmedString(255) )
    workflow_output_uuid_column = Column( "uuid", UUIDType, nullable=True )
    __add_column( workflow_output_label_column, "workflow_output", metadata )
    __add_column( workflow_output_uuid_column, "workflow_output", metadata )

    # Make stored_workflow_id nullable, since now workflows can belong to either
    # a stored workflow or a parent workflow.
    __alter_column("workflow", "stored_workflow_id", metadata, nullable=True)

    for table in TABLES:
        __create(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column( "subworkflow_id", "workflow_step", metadata )
    __drop_column( "parent_workflow_id", "workflow_step", metadata )

    __drop_column( "input_subworkflow_step_id", "workflow_step_connection", metadata )

    __drop_column( "label", "workflow_output", metadata )
    __drop_column( "uuid", "workflow_output", metadata )

    __alter_column("workflow", "stored_workflow_id", metadata, nullable=False)

    for table in TABLES:
        __drop(table)


def __alter_column(table_name, column_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).alter(**kwds)
    except Exception as e:
        print str(e)
        log.exception( "Adding column %s failed." % column_name)


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception as e:
        print str(e)
        log.exception( "Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception as e:
        print str(e)
        log.exception( "Dropping column %s failed." % column_name )


def __create(table):
    try:
        table.create()
    except Exception as e:
        print str(e)
        log.exception("Creating %s table failed: %s" % (table.name, str( e ) ) )


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        print str(e)
        log.exception("Dropping %s table failed: %s" % (table.name, str( e ) ) )
