"""
Migration script to add a new workflow_invocation_output_parameter table to track output parameters.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
metadata = MetaData()

workflow_invocation_output_parameter_table = Table(
    "workflow_invocation_output_value", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id")),
    Column("workflow_output_id", Integer, ForeignKey("workflow_output.id"), index=True),
    Column("value", JSONType),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        workflow_invocation_output_parameter_table.create()
    except Exception:
        log.exception("Creating workflow_invocation_output_parameter table failed")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        workflow_invocation_output_parameter_table.drop()
    except Exception:
        log.exception("Dropping workflow_invocation_output_parameter table failed")
