"""
Add UUIDs to workflows
"""

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import UUIDType

log = logging.getLogger(__name__)
metadata = MetaData()


"""
Because both workflow and job requests can be determined
based the a fixed data structure, their IDs are based on
hashing the data structure
"""
workflow_uuid_column = Column("uuid", UUIDType, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the uuid colum to the workflow table
    try:
        workflow_table = Table("workflow", metadata, autoload=True)
        workflow_uuid_column.create(workflow_table)
        assert workflow_uuid_column is workflow_table.c.uuid
    except Exception:
        log.exception("Adding column 'uuid' to workflow table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the workflow table's uuid column.
    try:
        workflow_table = Table("workflow", metadata, autoload=True)
        workflow_uuid = workflow_table.c.uuid
        workflow_uuid.drop()
    except Exception:
        log.exception("Dropping 'uuid' column from workflow table failed.")
