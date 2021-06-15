"""
Migration script to create tables for adding explicit workflow outputs.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

WorkflowOutput_table = Table("workflow_output", metadata,
                             Column("id", Integer, primary_key=True),
                             Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
                             Column("output_name", String(255), nullable=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    create_table(WorkflowOutput_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_table(WorkflowOutput_table)
