"""
Migration script to enhance workflow step usability by adding labels and UUIDs.
"""

import logging

from sqlalchemy import Column, MetaData

from galaxy.model.custom_types import TrimmedString, UUIDType
from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    StepLabel_column = Column("label", TrimmedString(255))
    StepUUID_column = Column("uuid", UUIDType, nullable=True)
    add_column(StepLabel_column, "workflow_step", metadata)
    add_column(StepUUID_column, "workflow_step", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("label", "workflow_step", metadata)
    drop_column("uuid", "workflow_step", metadata)
