"""
Migration script to create tables for handling post-job actions.
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

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

PostJobAction_table = Table("post_job_action", metadata,
                            Column("id", Integer, primary_key=True),
                            Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
                            Column("action_type", String(255), nullable=False),
                            Column("output_name", String(255), nullable=True),
                            Column("action_arguments", JSONType, nullable=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    create_table(PostJobAction_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_table(PostJobAction_table)
