"""
Migration script to add the dynamic_tool table.
"""
import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, Unicode

from galaxy.model.custom_types import JSONType, UUIDType
from galaxy.model.migrate.versions.util import add_column, create_table, drop_column, drop_table

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


DynamicTool_table = Table(
    "dynamic_tool", metadata,
    Column("id", Integer, primary_key=True),
    Column("uuid", UUIDType()),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("tool_id", Unicode(255)),
    Column("tool_version", Unicode(255)),
    Column("tool_format", Unicode(255)),
    Column("tool_path", Unicode(255)),
    Column("tool_directory", Unicode(255)),
    Column("hidden", Boolean),
    Column("active", Boolean),
    Column("value", JSONType()),
)

TABLES = [
    DynamicTool_table,
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)

    if migrate_engine.name in ['postgres', 'postgresql']:
        workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, ForeignKey("dynamic_tool.id"), nullable=True)
        job_workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, ForeignKey("dynamic_tool.id"), nullable=True)
    else:
        workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, nullable=True)
        job_workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, nullable=True)

    add_column(workflow_dynamic_tool_id_column, "workflow_step", metadata)
    add_column(job_workflow_dynamic_tool_id_column, "job", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("dynamic_tool_id", "workflow_step", metadata)
    drop_column("dynamic_tool_id", "job", metadata)

    for table in TABLES:
        drop_table(table)
