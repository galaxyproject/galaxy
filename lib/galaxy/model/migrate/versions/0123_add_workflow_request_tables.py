"""
Migration script for workflow request tables.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    TEXT,
    Unicode
)

from galaxy.model.custom_types import (
    JSONType,
    TrimmedString,
    UUIDType
)
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()


WorkflowRequestInputParameter_table = Table(
    "workflow_request_input_parameters", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id", onupdate="CASCADE", ondelete="CASCADE")),
    Column("name", Unicode(255)),
    Column("type", Unicode(255)),
    Column("value", TEXT),
)


WorkflowRequestStepState_table = Table(
    "workflow_request_step_states", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id", onupdate="CASCADE", ondelete="CASCADE")),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("value", JSONType),
)


WorkflowRequestToInputDatasetAssociation_table = Table(
    "workflow_request_to_input_dataset", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255)),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("dataset_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
)


WorkflowRequestToInputDatasetCollectionAssociation_table = Table(
    "workflow_request_to_input_collection_dataset", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255)),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("dataset_collection_id", Integer, ForeignKey("history_dataset_collection_association.id"), index=True),
)


TABLES = [
    WorkflowRequestInputParameter_table,
    WorkflowRequestStepState_table,
    WorkflowRequestToInputDatasetAssociation_table,
    WorkflowRequestToInputDatasetCollectionAssociation_table,
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)

    History_column = Column("history_id", Integer, ForeignKey("history.id"), nullable=True)
    State_column = Column("state", TrimmedString(64))

    # TODO: Handle indexes correctly
    SchedulerId_column = Column("scheduler", TrimmedString(255))
    HandlerId_column = Column("handler", TrimmedString(255))
    WorkflowUUID_column = Column("uuid", UUIDType, nullable=True)
    add_column(History_column, "workflow_invocation", metadata)
    add_column(State_column, "workflow_invocation", metadata)
    add_column(SchedulerId_column, "workflow_invocation", metadata, index_nane="id_workflow_invocation_scheduler")
    add_column(HandlerId_column, "workflow_invocation", metadata, index_name="id_workflow_invocation_handler")
    add_column(WorkflowUUID_column, "workflow_invocation", metadata)

    # All previous invocations have been scheduled...
    cmd = "UPDATE workflow_invocation SET state = 'scheduled'"
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("failed to update past workflow invocation states.")

    WorkflowInvocationStepAction_column = Column("action", JSONType, nullable=True)
    add_column(WorkflowInvocationStepAction_column, "workflow_invocation_step", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        drop_table(table)

    drop_column("state", "workflow_invocation", metadata)
    drop_column("scheduler", "workflow_invocation", metadata)
    drop_column("uuid", "workflow_invocation", metadata)
    drop_column("history_id", "workflow_invocation", metadata)
    drop_column("handler", "workflow_invocation", metadata)
    drop_column("action", "workflow_invocation_step", metadata)
