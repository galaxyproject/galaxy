"""
"""
import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, Unicode

from galaxy.model.custom_types import JSONType, UUIDType

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

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
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __create(table)

    if migrate_engine.name in ['postgres', 'postgresql']:
        workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, ForeignKey("dynamic_tool.id"), nullable=True)
        job_workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, ForeignKey("dynamic_tool.id"), nullable=True)
    else:
        workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, nullable=True)
        job_workflow_dynamic_tool_id_column = Column("dynamic_tool_id", Integer, nullable=True)

    __add_column(workflow_dynamic_tool_id_column, "workflow_step", metadata)
    __add_column(job_workflow_dynamic_tool_id_column, "job", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column("dynamic_tool_id", "workflow_step", metadata)
    __drop_column("dynamic_tool_id", "job", metadata)

    for table in TABLES:
        __drop(table)


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table(table_name, metadata, autoload=True)
        column.create(table, **kwds)
    except Exception:
        log.exception("Adding column %s column failed." % column)


def __drop_column(column_name, table_name, metadata):
    try:
        table = Table(table_name, metadata, autoload=True)
        getattr(table.c, column_name).drop()
    except Exception:
        log.exception("Dropping column %s failed." % column_name)


def __create(table):
    try:
        table.create()
    except Exception as e:
        log.exception("Creating %s table failed: %s" % (table.name, str(e)))


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        log.exception("Dropping %s table failed: %s" % (table.name, str(e)))
